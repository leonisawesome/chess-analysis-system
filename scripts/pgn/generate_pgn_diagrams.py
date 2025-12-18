#!/usr/bin/env python3
"""
Generate static diagram images from annotated PGN files.

The script scans PGN comments/NAGs for instructional keywords, snapshots the
board as SVG, and emits diagram metadata compatible with `diagram_service.py`.

Example:
python scripts/generate_pgn_diagrams.py \\
    --input "/Volumes/chess/1Modern Chess/modern.pgn" \\
    --image-dir "/Volumes/T7 Shield/rag/databases/pgn/images" \\
    --metadata-output "diagram_metadata_pgn.json" \\
    --limit-per-game 4
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import re
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Set, Tuple

import chess
import chess.pgn
import chess.svg

from pgn_quality_analyzer import PGNQualityAnalyzer

try:
    from diagram_service import detect_opening_tags
except ImportError:
    # Lightweight fallback (avoids importing optional Pillow dependency when running tests)
    OPENING_PATTERN = re.compile(r'\b([A-E][0-9]{2}|sicilian|najdorf|dragon|italian|spanish|ruy|slav|catalan)\b', re.IGNORECASE)

    def detect_opening_tags(text: str) -> Tuple[Set[str], Set[str]]:  # type: ignore
        """
        Fallback tagger that only extracts ECO codes and a few openings.
        """
        tags = set()
        ecos = set()
        if not text:
            return tags, ecos
        for match in OPENING_PATTERN.finditer(text):
            value = match.group(1).lower()
            if len(value) == 3 and value[0].isalpha():
                ecos.add(value.upper())
            else:
                tags.add(value)
        return tags, ecos


KEYWORD_TAGS: Dict[str, Sequence[str]] = {
    "prophylaxis": [r"\bprophylaxis\b", r"\bprophylactic\b"],
    "isolated_queen_pawn": [r"\biqp\b", r"\bisolated queen pawn\b"],
    "backward_pawn": [r"\bbackward pawn\b"],
    "passed_pawn": [r"\bpassed pawn\b"],
    "exchange_sacrifice": [r"\bexchange sac", r"\bexchange sacrifice\b"],
    "sacrifice": [r"\bsacrifice\b", r"\bsac\b"],
    "king_attack": [r"\bking attack\b", r"\battack the king\b", r"\bmates?\b"],
    "defense": [r"\bdefen[cs]e\b", r"\bneutralize\b"],
    "tactical_motif": [
        r"\bzwischenzug\b",
        r"\boverloaded\b",
        r"\bclearance\b",
        r"\bdeflection\b",
        r"\bremoval of the defender\b",
        r"\btactic",
    ],
    "structure": [
        r"\bpawn structure\b",
        r"\bpawn majority\b",
        r"\bpawn minority\b",
        r"\bdoubled pawns\b",
        r"\bisolated pawn\b",
        r"\bweak square\b",
        r"\boutpost\b",
    ],
    "endgame": [
        r"\bendgame\b",
        r"\bking and pawn\b",
        r"\brook endgame\b",
        r"\bopposition\b",
        r"\bzugzwang\b",
        r"\btriangulation\b",
    ],
    "initiative": [r"\binitiative\b", r"\bpressure\b"],
    "counterplay": [r"\bcounterplay\b", r"\bcounter-attack\b"],
}

NAG_TAGS = {
    chess.pgn.NAG_BLUNDER: "blunder",
    chess.pgn.NAG_MISTAKE: "mistake",
    chess.pgn.NAG_DUBIOUS_MOVE: "dubious",
    chess.pgn.NAG_GOOD_MOVE: "good_move",
    chess.pgn.NAG_BRILLIANT_MOVE: "brilliant",
    chess.pgn.NAG_SPECULATIVE_MOVE: "speculative",
    chess.pgn.NAG_FORCED_MOVE: "only_move",
    44: "compensation",  # NAG_WITH_COMPENSATION (not in all chess.pgn versions)
    chess.pgn.NAG_UNCLEAR_POSITION: "unclear",
    chess.pgn.NAG_QUIET_POSITION: "equal",  # Using NAG_QUIET_POSITION instead of missing NAG_EVEN_POSITION
    chess.pgn.NAG_WHITE_SLIGHT_ADVANTAGE: "edge_white",
    chess.pgn.NAG_BLACK_SLIGHT_ADVANTAGE: "edge_black",
    chess.pgn.NAG_WHITE_DECISIVE_ADVANTAGE: "winning_white",
    chess.pgn.NAG_BLACK_DECISIVE_ADVANTAGE: "winning_black",
    chess.pgn.NAG_WHITE_ZUGZWANG: "zugzwang",
    chess.pgn.NAG_BLACK_ZUGZWANG: "zugzwang",
    chess.pgn.NAG_DRAWISH_POSITION: "drawish",
}


def iter_raw_games(filepath: Path) -> Iterable[str]:
    """Stream PGN text one game at a time without loading the entire file into memory."""
    with filepath.open("r", encoding="utf-8", errors="ignore") as handle:
        buffer: List[str] = []
        for line in handle:
            stripped = line.lstrip()
            if stripped.startswith("[Event "):
                if buffer:
                    yield "".join(buffer).strip()
                    buffer = [line]
                else:
                    buffer.append(line)
            else:
                buffer.append(line)
        if buffer:
            yield "".join(buffer).strip()


def md5(text: str) -> str:
    return hashlib.md5(text.encode("utf-8", errors="ignore")).hexdigest()


def normalize_comment(comment: str) -> str:
    comment = (comment or "").strip()
    comment = re.sub(r"\s+", " ", comment)
    return comment


def detect_keywords(comment: str) -> Set[str]:
    if not comment:
        return set()
    text = comment.lower()
    tags: Set[str] = set()
    for tag, patterns in KEYWORD_TAGS.items():
        for pattern in patterns:
            if re.search(pattern, text):
                tags.add(tag)
                break
    return tags


def summarize_headers(headers: Dict[str, str]) -> str:
    event = headers.get("Event", "Unknown Event")
    site = headers.get("Site", "Unknown Site")
    date = headers.get("Date", "????.??.??")
    return f"{event} ({site}, {date})"


def make_book_id(source_path: Path) -> str:
    digest = hashlib.md5(str(source_path).encode("utf-8")).hexdigest()[:12]
    return f"pgn_{digest}"


def make_diagram_id(book_id: str, game_idx: int, ply: int) -> str:
    return f"{book_id}_{game_idx:05d}_{ply:04d}"


@dataclass
class DiagramRecord:
    diagram_id: str
    book_id: str
    book_title: str
    file_path: str
    format: str
    size_bytes: int
    source_file: str
    source_type: str
    game_number: int
    event: str
    white: str
    black: str
    result: str
    eco: str
    opening: str
    move_number: int
    ply_index: int
    san: str
    fen: str
    tags: List[str]
    comment: str
    caption: str
    context_before: str
    context_after: str
    concept_text: str
    evs: Optional[float]
    quality_bucket: str
    position_in_document: int

    def to_dict(self) -> Dict:
        return {
            "diagram_id": self.diagram_id,
            "book_id": self.book_id,
            "book_title": self.book_title,
            "file_path": self.file_path,
            "format": self.format,
            "size_bytes": self.size_bytes,
            "source_file": self.source_file,
            "source_type": self.source_type,
            "game_number": self.game_number,
            "event": self.event,
            "white": self.white,
            "black": self.black,
            "result": self.result,
            "eco": self.eco,
            "opening": self.opening,
            "move_number": self.move_number,
            "ply_index": self.ply_index,
            "san": self.san,
            "fen": self.fen,
            "tags": self.tags,
            "comment": self.comment,
            "caption": self.caption,
            "context_before": self.context_before,
            "context_after": self.context_after,
            "concept_text": self.concept_text,
            "evs": self.evs,
            "quality_bucket": self.quality_bucket,
            "position_in_document": self.position_in_document,
        }


def extract_diagram_candidates(
    game: chess.pgn.Game,
    *,
    source_file: Path,
    game_index: int,
    analyzer: PGNQualityAnalyzer,
    limit_per_game: int,
    min_comment_words: int,
    board_size: int,
    image_dir: Path,
    default_caption_prefix: str,
) -> List[DiagramRecord]:

    scored = analyzer.score_game(game, file_name=source_file.name, game_index=game_index)
    evs = scored.evs if scored else None
    if evs is None:
        return []

    if evs >= 70:
        bucket = "high"
    elif evs >= 45:
        bucket = "medium"
    else:
        bucket = "low"

    board = game.board()
    headers = dict(game.headers)
    book_id = make_book_id(source_file)
    book_title = f"{source_file.stem} (PGN)"
    opening_header = headers.get("Opening", "")
    eco_header = headers.get("ECO", "")
    event_summary = summarize_headers(headers)
    results: List[DiagramRecord] = []
    captured = 0

    running_comment = ""
    last_comment = ""

    for ply_index, node in enumerate(game.mainline(), start=1):
        move = node.move
        if move is None:
            continue
        san = node.san()
        board.push(move)
        comment = normalize_comment(node.comment)
        if comment:
            running_comment = comment
            last_comment = comment

        tags = set()
        tags |= detect_keywords(comment)
        if opening_header:
            opening_tags, ecos = detect_opening_tags(opening_header)
            tags |= {f"opening:{tag}" for tag in opening_tags}
            tags |= {f"eco:{eco}" for eco in ecos}
        if eco_header:
            tags.add(f"eco:{eco_header}")
        if comment:
            comment_opening_tags, comment_ecos = detect_opening_tags(comment)
            tags |= {f"opening:{tag}" for tag in comment_opening_tags}
            tags |= {f"eco:{eco}" for eco in comment_ecos}

        for nag in node.nags:
            nag_tag = NAG_TAGS.get(nag)
            if nag_tag:
                tags.add(f"nag:{nag_tag}")

        evs_tag = "evs:high" if evs >= 70 else "evs:medium" if evs >= 45 else "evs:low"
        tags.add(evs_tag)

        comment_word_count = len(comment.split()) if comment else 0
        keyword_candidates = {
            t for t in tags
            if not t.startswith("eco:")
            and not t.startswith("evs:")
        }
        has_keyword = bool(keyword_candidates)
        if not has_keyword and comment_word_count < min_comment_words:
            continue

        if limit_per_game and captured >= limit_per_game:
            break

        fen = board.fen()
        diagram_id = make_diagram_id(book_id, game_index, ply_index)
        rel_dir = image_dir / book_id
        rel_dir.mkdir(parents=True, exist_ok=True)
        svg_path = rel_dir / f"{diagram_id}.svg"
        try:
            svg_data = chess.svg.board(board, size=board_size, lastmove=move, coordinates=True)
            svg_path.write_text(svg_data, encoding="utf-8")
        except Exception as exc:  # noqa: BLE001
            print(f"   ⚠️  Failed to render SVG for {source_file.name} game #{game_index}: {exc}")
            continue

        size_bytes = svg_path.stat().st_size
        move_number = board.fullmove_number - (0 if board.turn == chess.BLACK else 1)
        caption = f"{default_caption_prefix} — {san}"
        if comment:
            caption = f"{caption}: {comment[:180]}"

        record = DiagramRecord(
            diagram_id=diagram_id,
            book_id=book_id,
            book_title=book_title,
            file_path=str(svg_path),
            format="svg",
            size_bytes=size_bytes,
            source_file=str(source_file),
            source_type="pgn",
            game_number=game_index,
            event=headers.get("Event", "Unknown Event"),
            white=headers.get("White", "White"),
            black=headers.get("Black", "Black"),
            result=headers.get("Result", "*"),
            eco=headers.get("ECO", ""),
            opening=opening_header,
            move_number=move_number,
            ply_index=ply_index,
            san=san,
            fen=fen,
            tags=sorted(tags),
            comment=comment,
            caption=caption,
            context_before=last_comment,
            context_after=event_summary,
            concept_text=running_comment or caption,
            evs=evs,
            quality_bucket=bucket,
            position_in_document=game_index * 1000 + ply_index,
        )
        results.append(record)
        captured += 1

    return results


def gather_pgn_files(input_path: Path) -> List[Path]:
    if input_path.is_file():
        return [input_path]
    return sorted(p for p in input_path.rglob("*.pgn") if p.is_file())


def run_pipeline(
    pgn_paths: List[Path],
    image_dir: Path,
    metadata_path: Path,
    limit_per_game: int,
    min_comment_words: int,
    board_size: int,
    max_games: Optional[int],
    heartbeat: int,
    shard_size: int,
    shard_dir: Optional[Path],
) -> Dict:
    analyzer = PGNQualityAnalyzer(Path(":memory:"))
    metadata: List[Dict] = []
    shard_buffer: List[Dict] = []
    shard_counter = 0

    stats = {
        "files": 0,
        "games": 0,
        "diagrams": 0,
        "skipped_games": 0,
        "files_failed": 0,
        "start_time": time.time(),
    }

    def flush_shard(force: bool = False):
        nonlocal shard_counter
        if not shard_dir or not shard_buffer:
            return
        if not force and len(shard_buffer) < shard_size:
            return
        shard_counter += 1
        shard_dir.mkdir(parents=True, exist_ok=True)
        shard_data = list(shard_buffer)
        shard_payload = {
            "stats": {
                "source": "pgn",
                "generated_at": datetime.utcnow().isoformat(),
                "shard_index": shard_counter,
                "diagrams_in_shard": len(shard_data),
                "files_processed": stats["files"],
                "games_processed": stats["games"],
            },
            "diagrams": shard_data,
        }
        shard_path = shard_dir / f"{metadata_path.stem}_shard_{shard_counter:04d}.json"
        shard_path.write_text(json.dumps(shard_payload, indent=2), encoding="utf-8")
        print(f"[shard] Wrote {len(shard_data)} diagrams → {shard_path}")
        shard_buffer.clear()

    processed_games = 0
    for file_idx, pgn_file in enumerate(pgn_paths, start=1):
        stats["files"] += 1
        print(f"[info] ({file_idx}/{len(pgn_paths)}) {pgn_file}")
        try:
            raw_games = iter_raw_games(pgn_file)
        except Exception as exc:  # noqa: BLE001
            stats["files_failed"] += 1
            print(f"   ⚠️  Failed to stream {pgn_file}: {exc}")
            continue

        for game_text in raw_games:
            if max_games and processed_games >= max_games:
                break
            if not game_text.strip():
                continue
            processed_games += 1
            if heartbeat and processed_games % heartbeat == 0:
                elapsed = time.time() - stats["start_time"]
                print(
                    f"[heartbeat] {processed_games:,} games | "
                    f"{stats['diagrams']:,} diagrams | elapsed {elapsed/60:.1f} min"
                )
            try:
                game = chess.pgn.read_game(io.StringIO(game_text + "\n\n"))
            except Exception as exc:  # noqa: BLE001
                stats["skipped_games"] += 1
                print(f"   ⚠️  Skipping game #{processed_games}: parse error {exc}")
                continue

            diagrams = extract_diagram_candidates(
                game,
                source_file=pgn_file,
                game_index=processed_games,
                analyzer=analyzer,
                limit_per_game=limit_per_game,
                min_comment_words=min_comment_words,
                board_size=board_size,
                image_dir=image_dir,
                default_caption_prefix=f"{game.headers.get('White', 'White')} vs {game.headers.get('Black', 'Black')}",
            )
            if diagrams:
                stats["diagrams"] += len(diagrams)
                for record in diagrams:
                    record_dict = record.to_dict()
                    metadata.append(record_dict)
                    shard_buffer.append(record_dict)
                    if shard_size > 0:
                        flush_shard()

            stats["games"] += 1

        if max_games and processed_games >= max_games:
            break

    flush_shard(force=True)
    image_dir.mkdir(parents=True, exist_ok=True)
    metadata_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "stats": {
            "source": "pgn",
            "generated_at": datetime.utcnow().isoformat(),
            "files_processed": stats["files"],
            "files_failed": stats["files_failed"],
            "games_processed": stats["games"],
            "diagrams_emitted": stats["diagrams"],
            "runtime_seconds": round(time.time() - stats["start_time"], 2),
            "shards_written": shard_counter,
        },
        "diagrams": metadata,
    }
    metadata_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"✅ Wrote {stats['diagrams']:,} diagrams to {metadata_path}")
    return stats


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate PGN-based diagrams and metadata.")
    parser.add_argument("--input", required=True, help="PGN file or directory to scan.")
    parser.add_argument("--image-dir", required=True, help="Directory to store generated SVG diagrams.")
    parser.add_argument("--metadata-output", required=True, help="Path to write diagram metadata JSON.")
    parser.add_argument("--limit-per-game", type=int, default=4, help="Maximum diagrams per game.")
    parser.add_argument("--min-comment-words", type=int, default=12, help="Minimum words in comment when no keyword matches.")
    parser.add_argument("--board-size", type=int, default=420, help="SVG size in pixels.")
    parser.add_argument("--max-games", type=int, help="Optional cap for number of games (useful for testing).")
    parser.add_argument("--heartbeat", type=int, default=500, help="Heartbeat interval in games.")
    parser.add_argument("--shard-size", type=int, default=25000, help="Number of diagrams per metadata shard (0 disables shard output).")
    parser.add_argument("--shard-dir", help="Directory for metadata shard files (default: <metadata-output>_shards).")
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    input_path = Path(args.input).expanduser()
    if not input_path.exists():
        raise FileNotFoundError(f"Input path not found: {input_path}")
    image_dir = Path(args.image_dir).expanduser()
    metadata_path = Path(args.metadata_output).expanduser()

    pgn_files = gather_pgn_files(input_path)
    if not pgn_files:
        raise RuntimeError(f"No PGN files found under {input_path}")

    shard_dir = Path(args.shard_dir).expanduser() if args.shard_dir else metadata_path.parent / f"{metadata_path.stem}_shards"

    run_pipeline(
        pgn_files,
        image_dir=image_dir,
        metadata_path=metadata_path,
        limit_per_game=args.limit_per_game,
        min_comment_words=args.min_comment_words,
        board_size=args.board_size,
        max_games=args.max_games,
        heartbeat=args.heartbeat,
        shard_size=max(0, args.shard_size),
        shard_dir=shard_dir if args.shard_size > 0 else None,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
