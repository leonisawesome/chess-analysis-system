"""Hash-based deduplication system for chess PGN files."""

import chess.pgn
import hashlib
import os
import sqlite3
from io import StringIO
import concurrent.futures
from typing import Dict, List, Optional, Tuple


try:  # Optional dependency: Postgres backend
    import psycopg2  # type: ignore
    from psycopg2.extras import execute_values  # type: ignore

    _HAS_PSYCOPG2 = True
except Exception:  # pragma: no cover
    psycopg2 = None  # type: ignore
    execute_values = None  # type: ignore
    _HAS_PSYCOPG2 = False


class ChessDeduplicator:
    """Handles deduplication of chess games using normalized move sequences."""

    def __init__(self, db_config: Dict[str, str]):
        """Initialize with database configuration."""
        backend = os.environ.get("CHESS_DEDUP_BACKEND", "auto").strip().lower()
        sqlite_path = os.environ.get("CHESS_DEDUP_SQLITE_PATH", "dedup_hashes.sqlite3").strip()

        if backend not in {"auto", "postgres", "sqlite"}:
            raise ValueError("CHESS_DEDUP_BACKEND must be one of: auto, postgres, sqlite")

        self._backend = "postgres"
        self._sqlite_commit_every = int(os.environ.get("CHESS_DEDUP_SQLITE_COMMIT_EVERY", "5000"))
        self._sqlite_pending = 0

        if backend == "sqlite" or (backend == "auto" and not _HAS_PSYCOPG2):
            self._init_sqlite(sqlite_path)
            return

        if not _HAS_PSYCOPG2:
            raise ImportError("psycopg2 is required for CHESS_DEDUP_BACKEND=postgres")

        try:
            self.conn = psycopg2.connect(**db_config)  # type: ignore[misc]
            self.init_db()
        except Exception:
            if backend == "postgres":
                raise
            self._init_sqlite(sqlite_path)

    def _init_sqlite(self, sqlite_path: str) -> None:
        self._backend = "sqlite"
        self.conn = sqlite3.connect(sqlite_path)
        # Speed/safety tradeoff: WAL + NORMAL is fine for a long-running ingest.
        self.conn.execute("PRAGMA journal_mode=WAL;")
        self.conn.execute("PRAGMA synchronous=NORMAL;")
        self.conn.execute("PRAGMA temp_store=MEMORY;")
        self.conn.execute("PRAGMA foreign_keys=ON;")
        self.init_db()

    def init_db(self):
        """Create deduplication table if not exists."""
        if self._backend == "postgres":
            with self.conn.cursor() as cur:
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS game_hashes (
                        hash VARCHAR(64) PRIMARY KEY,
                        bundle_path TEXT,
                        created_at TIMESTAMP DEFAULT NOW()
                    )
                    """
                )
                cur.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_game_hashes_created
                    ON game_hashes(created_at DESC)
                    """
                )
                self.conn.commit()
            return

        cur = self.conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS game_hashes (
                hash TEXT PRIMARY KEY,
                bundle_path TEXT,
                created_at TEXT DEFAULT (datetime('now'))
            )
            """
        )
        cur.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_game_hashes_created
            ON game_hashes(created_at DESC)
            """
        )
        self.conn.commit()

    def normalize_game(self, pgn_text: str) -> Optional[str]:
        """
        Conservative normalization that preserves games with different annotations.

        Args:
            pgn_text: Raw PGN text

        Returns:
            Hash of entire PGN content (preserving all annotations) or None if parsing fails
        """
        normalized_pgn = pgn_text.strip()
        if not normalized_pgn:
            return None

        # Best-effort parse: if python-chess considers the moves illegal, it may
        # fail or warn; we still want to keep these games for ChessBase parity.
        # We only use parsing to filter out truly empty/no-move "games".
        try:
            game = chess.pgn.read_game(StringIO(pgn_text))
            if game:
                moves = list(game.mainline_moves())
                if not moves:
                    return None
        except Exception:
            pass

        # Use the ENTIRE raw PGN text as the basis for deduplication.
        # Only normalize insignificant whitespace while preserving all content.
        lines: list[str] = []
        for line in normalized_pgn.split("\n"):
            line = line.strip()
            if line:
                lines.append(line)
        return "\n".join(lines) if lines else None

    def compute_hash(self, normalized_moves: str) -> str:
        """Compute SHA256 hash of normalized moves."""
        return hashlib.sha256(normalized_moves.encode()).hexdigest()

    def check_duplicate(self, pgn_text: str) -> Tuple[Optional[str], str]:
        """
        Check if a single game is duplicate.

        Returns:
            (hash, status) where status is 'new', 'duplicate', or 'error'
        """
        normalized = self.normalize_game(pgn_text)
        if not normalized:
            return None, 'error'

        game_hash = self.compute_hash(normalized)

        if self._backend == "postgres":
            with self.conn.cursor() as cur:
                cur.execute("SELECT 1 FROM game_hashes WHERE hash = %s", (game_hash,))
                if cur.fetchone():
                    return game_hash, "duplicate"
                cur.execute("INSERT INTO game_hashes (hash) VALUES (%s)", (game_hash,))
                self.conn.commit()
                return game_hash, "new"

        cur = self.conn.cursor()
        cur.execute("INSERT OR IGNORE INTO game_hashes (hash) VALUES (?)", (game_hash,))
        is_new = cur.rowcount == 1
        self._sqlite_pending += 1
        if self._sqlite_commit_every and self._sqlite_pending >= self._sqlite_commit_every:
            self.conn.commit()
            self._sqlite_pending = 0
        return game_hash, ("new" if is_new else "duplicate")

    def process_batch(
        self,
        pgn_texts: List[str],
        bundle_path: Optional[str] = None
    ) -> Dict[str, List[str]]:
        """
        Process multiple PGNs efficiently in batch.

        Returns:
            Dictionary with 'new', 'duplicate', and 'error' lists
        """
        results = {'new': [], 'duplicate': [], 'error': []}

        if self._backend != "postgres":
            for pgn_text in pgn_texts:
                _, status = self.check_duplicate(pgn_text)
                if status == "new":
                    results["new"].append(pgn_text)
                elif status == "duplicate":
                    results["duplicate"].append(pgn_text)
                else:
                    results["error"].append(pgn_text)
            return results

        # Normalize all games in parallel
        game_data = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
            futures = {
                executor.submit(self.normalize_game, pgn): pgn
                for pgn in pgn_texts
            }

            for future in concurrent.futures.as_completed(futures):
                pgn_text = futures[future]
                normalized = future.result()

                if not normalized:
                    results['error'].append(pgn_text)
                    continue

                game_hash = self.compute_hash(normalized)
                game_data.append((game_hash, bundle_path, pgn_text))

        if not game_data:
            return results

        # Check all hashes in single query
        hashes_to_check = [h for h, _, _ in game_data]

        with self.conn.cursor() as cur:
            cur.execute(
                "SELECT hash FROM game_hashes WHERE hash = ANY(%s)",
                (hashes_to_check,)
            )
            existing_hashes = {row[0] for row in cur.fetchall()}

            # Insert new games
            new_games = [
                (h, b) for h, b, _ in game_data
                if h not in existing_hashes
            ]

            if new_games:
                assert execute_values is not None
                execute_values(cur, "INSERT INTO game_hashes (hash, bundle_path) VALUES %s", new_games)
                self.conn.commit()

            # Categorize results
            for hash_val, _, pgn in game_data:
                if hash_val in existing_hashes:
                    results['duplicate'].append(pgn)
                else:
                    results['new'].append(pgn)

        return results

    def close(self):
        """Close database connection."""
        try:
            if self._backend == "sqlite" and self._sqlite_pending:
                self.conn.commit()
        except Exception:
            pass
        self.conn.close()
