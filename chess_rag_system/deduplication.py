"""Hash-based deduplication system for chess PGN files."""

import chess.pgn
import hashlib
import psycopg2
from psycopg2.extras import execute_values
from io import StringIO
import concurrent.futures
from typing import Dict, List, Optional, Tuple

class ChessDeduplicator:
    """Handles deduplication of chess games using normalized move sequences."""

    def __init__(self, db_config: Dict[str, str]):
        """Initialize with database configuration."""
        self.conn = psycopg2.connect(**db_config)
        self.init_db()

    def init_db(self):
        """Create deduplication table if not exists."""
        with self.conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS game_hashes (
                    hash VARCHAR(64) PRIMARY KEY,
                    bundle_path TEXT,
                    created_at TIMESTAMP DEFAULT NOW()
                )
            """)
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_game_hashes_created
                ON game_hashes(created_at DESC)
            """)
            self.conn.commit()

    def normalize_game(self, pgn_text: str) -> Optional[str]:
        """
        Normalize PGN to UCI move sequence for consistent hashing.

        Args:
            pgn_text: Raw PGN text

        Returns:
            Space-separated UCI move sequence or None if parsing fails
        """
        try:
            game = chess.pgn.read_game(StringIO(pgn_text))
            if not game:
                return None

            # Generate UCI moves (unambiguous format)
            moves = []
            board = game.board()
            for move in game.mainline_moves():
                moves.append(move.uci())
                board.push(move)

            move_sequence = " ".join(moves)
            # Return None if no moves found (empty or malformed game)
            return move_sequence if move_sequence.strip() else None
        except Exception:
            return None

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

        with self.conn.cursor() as cur:
            cur.execute(
                "SELECT 1 FROM game_hashes WHERE hash = %s",
                (game_hash,)
            )

            if cur.fetchone():
                return game_hash, 'duplicate'
            else:
                cur.execute(
                    "INSERT INTO game_hashes (hash) VALUES (%s)",
                    (game_hash,)
                )
                self.conn.commit()
                return game_hash, 'new'

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
                execute_values(
                    cur,
                    "INSERT INTO game_hashes (hash, bundle_path) VALUES %s",
                    new_games
                )
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
        self.conn.close()