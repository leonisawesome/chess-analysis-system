#!/usr/bin/env python3
"""
PGN Quality Analyzer

Scores PGN files before ingestion so we can reject noisy datasets.
Writes per-file summaries into SQLite (pgn_analysis.db) and optional JSON.
"""

import argparse
import json
import re
import sqlite3
import sys
import time
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from statistics import median
from typing import Dict, List, Optional

import chess.pgn


REQUIRED_HEADERS = ["Event", "Site", "Date", "Round", "White", "Black", "Result"]
EDU_KEYWORDS = [
    r"\bplan\b",
    r"\bidea\b",
    r"\bstrategy\b",
    r"\bconcept\b",
    r"\bweak(?:ness)?\b",
    r"\bstrong\b",
    r"\btypical\b",
    r"\bshould\b",
    r"\bneeds to\b",
    r"\btarget\b",
    r"\binitiative\b",
]

ANNOTATION_PATTERN = re.compile(r"[!?]{1,2}")
COMMENT_PATTERN = re.compile(r"\{([^}]*)\}")
VARIATION_PATTERN = re.compile(r"\(([^)]*)\)")
NAG_PATTERN = re.compile(r"\$\d+")
RESULT_PATTERN = re.compile(r"\b(1-0|0-1|1/2-1/2)\b")


@dataclass
class GameScore:
    evs: float
    structure: float
    annotations: float
    humanness: float
    educational: float
    total_moves: int
    annotation_density: float
    comment_words: int
    has_variations: bool
    game_type: str


@dataclass
class FileSummary:
    filename: str
    full_path: str
    total_games: int
    high_quality: int
    medium_quality: int
    low_quality: int
    avg_evs: float
    median_evs: float
    avg_annotation_density: float
    avg_moves: float
    last_analyzed: str


class PGNQualityAnalyzer:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS pgn_analysis (
                    filename TEXT PRIMARY KEY,
                    full_path TEXT,
                    total_games INTEGER,
                    high_quality_games INTEGER,
                    medium_quality_games INTEGER,
                    low_quality_games INTEGER,
                    avg_evs REAL,
                    median_evs REAL,
                    avg_annotation_density REAL,
                    avg_moves REAL,
                    last_analyzed TEXT
                )
                """
            )

    def _score_structure(self, headers: Dict[str, str], moves: int, has_result: bool) -> float:
        header_hits = sum(1 for field in REQUIRED_HEADERS if headers.get(field))
        header_score = min(header_hits * 2.0, 12.0)
        result_bonus = 4.0 if has_result else 0.0
        length_bonus = min(moves / 40.0 * 4, 4.0)
        return min(header_score + result_bonus + length_bonus, 20.0)

    def _score_annotations(self, density: float, comment_words: int, has_variations: bool) -> float:
        density_score = min(density * 40, 10.0)
        comment_score = min(comment_words / 50.0, 6.0)
        variation_score = 4.0 if has_variations else 0.0
        return min(density_score + comment_score + variation_score, 20.0)

    def _score_humanness(self, headers: Dict[str, str], moves: int) -> float:
        elo_hits = sum(1 for tag in ("WhiteElo", "BlackElo") if headers.get(tag))
        event_bonus = 4.0 if headers.get("Event") else 0.0
        year = headers.get("Date", "")[:4]
        modern_bonus = 3.0 if year.isdigit() and int(year) >= 1980 else 0.0
        length_bonus = min(moves / 60.0 * 5, 5.0)
        return min(elo_hits * 3 + event_bonus + modern_bonus + length_bonus, 20.0)

    def _score_educational(self, comments: List[str]) -> float:
        text = " ".join(comments).lower()
        cues = sum(1 for pattern in EDU_KEYWORDS if re.search(pattern, text))
        return min(cues * 2.5, 15.0)

    def score_game(self, game: chess.pgn.Game) -> Optional[GameScore]:
        if game is None:
            return None
        headers = dict(game.headers)
        total_moves = len(list(game.mainline_moves()))
        if total_moves == 0:
            return None

        text = str(game)
        annotation_count = len(ANNOTATION_PATTERN.findall(text)) + len(NAG_PATTERN.findall(text))
        annotation_density = annotation_count / max(total_moves, 1)
        comments = COMMENT_PATTERN.findall(text)
        comment_words = sum(len(comment.split()) for comment in comments)
        has_variations = bool(VARIATION_PATTERN.search(text))
        has_result = bool(RESULT_PATTERN.search(text))

        structure = self._score_structure(headers, total_moves, has_result)
        annotation_score = self._score_annotations(annotation_density, comment_words, has_variations)
        humanness = self._score_humanness(headers, total_moves)
        educational = self._score_educational(comments)

        evs = min(25 + structure + annotation_score + humanness + educational, 100)
        if total_moves < 10:
            evs = max(evs - 10, 0)

        if annotation_density < 0.02 and comment_words < 20:
            game_type = "database_dump"
        elif annotation_density >= 0.25 or comment_words > 200:
            game_type = "annotated_game"
        elif total_moves < 20:
            game_type = "position_study"
        else:
            game_type = "complete_game"

        return GameScore(
            evs=evs,
            structure=structure,
            annotations=annotation_score,
            humanness=humanness,
            educational=educational,
            total_moves=total_moves,
            annotation_density=annotation_density,
            comment_words=comment_words,
            has_variations=has_variations,
            game_type=game_type,
        )

    def analyze_file(self, filepath: Path) -> Optional[FileSummary]:
        scores: List[GameScore] = []
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            while True:
                game = chess.pgn.read_game(f)
                if game is None:
                    break
                scored = self.score_game(game)
                if scored:
                    scores.append(scored)

        if not scores:
            return None

        evs_scores = [g.evs for g in scores]
        total_games = len(scores)
        high = sum(1 for g in scores if g.evs >= 70)
        medium = sum(1 for g in scores if 45 <= g.evs < 70)
        low = total_games - high - medium

        avg_evs = sum(evs_scores) / total_games
        med_evs = median(evs_scores)
        avg_density = sum(g.annotation_density for g in scores) / total_games
        avg_moves = sum(g.total_moves for g in scores) / total_games

        summary = FileSummary(
            filename=filepath.name,
            full_path=str(filepath),
            total_games=total_games,
            high_quality=high,
            medium_quality=medium,
            low_quality=low,
            avg_evs=round(avg_evs, 2),
            median_evs=round(med_evs, 2),
            avg_annotation_density=round(avg_density, 3),
            avg_moves=round(avg_moves, 1),
            last_analyzed=datetime.utcnow().isoformat(),
        )

        self.write_summary(summary)
        return summary

    def write_summary(self, summary: FileSummary):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO pgn_analysis (
                    filename, full_path, total_games,
                    high_quality_games, medium_quality_games, low_quality_games,
                    avg_evs, median_evs, avg_annotation_density, avg_moves, last_analyzed
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    summary.filename,
                    summary.full_path,
                    summary.total_games,
                    summary.high_quality,
                    summary.medium_quality,
                    summary.low_quality,
                    summary.avg_evs,
                    summary.median_evs,
                    summary.avg_annotation_density,
                    summary.avg_moves,
                    summary.last_analyzed,
                ),
            )


def iter_pgn_files(path: Path) -> List[Path]:
    if path.is_file() and path.suffix.lower() == ".pgn":
        return [path]
    if path.is_dir():
        return sorted(path.glob("*.pgn"))
    return []


def main():
    parser = argparse.ArgumentParser(description="Analyze PGN quality before ingestion")
    parser.add_argument("pgn_path", help="PGN file or directory")
    parser.add_argument("--db", default="pgn_analysis.db", help="SQLite database path")
    parser.add_argument("--json", help="Optional JSON output file")
    parser.add_argument("--limit", type=int, help="Only analyze first N files")
    args = parser.parse_args()

    files = iter_pgn_files(Path(args.pgn_path))
    if not files:
        print(f"No .pgn files found at {args.pgn_path}")
        sys.exit(1)
    if args.limit:
        files = files[: args.limit]

    analyzer = PGNQualityAnalyzer(Path(args.db))
    summaries: List[Dict] = []

    print(f"\nAnalyzing {len(files)} PGN file(s)...\n")
    start = time.time()

    for idx, file in enumerate(files, start=1):
        print(f"[{idx}/{len(files)}] {file.name}")
        summary = analyzer.analyze_file(file)
        if summary:
            summaries.append(asdict(summary))
            print(
                f"   Games: {summary.total_games}, "
                f"Avg EVS: {summary.avg_evs}, "
                f"High-quality: {summary.high_quality}, "
                f"Annotation density: {summary.avg_annotation_density}"
            )
        else:
            print("   ⚠️  No valid games parsed (skipped)")

    elapsed = time.time() - start
    print(f"\nCompleted in {elapsed/60:.1f} minutes.")

    if args.json and summaries:
        out_path = Path(args.json)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump({"summaries": summaries}, f, indent=2)
        print(f"JSON summary written to {out_path}")


if __name__ == "__main__":
    main()
