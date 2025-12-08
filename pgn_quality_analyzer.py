#!/usr/bin/env python3
"""
PGN Quality Analyzer

Scores PGN files before ingestion so we can reject noisy datasets.
Writes per-file summaries into SQLite (pgn_analysis.db) and optional JSON.
"""

import argparse
import csv
import io
import json
import re
import sqlite3
import sys
import time
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from statistics import median
from typing import Dict, List, Optional, Tuple, Set

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

# Lightweight stopword lists (keeps us offline and deterministic)
EN_STOP = {
    "the", "a", "an", "and", "or", "but", "if", "then", "else", "of", "in", "on", "for", "to",
    "with", "is", "are", "was", "were", "be", "been", "being", "by", "as", "at", "it", "that",
    "this", "these", "those", "from", "up", "down", "out", "about", "after", "before", "over",
    "under"
}
ES_STOP = {
    "el", "la", "los", "las", "un", "una", "unos", "unas", "y", "o", "pero", "si", "entonces",
    "de", "en", "por", "para", "con", "es", "son", "fue", "eran", "ser", "ha", "han", "haber",
    "como", "que", "este", "estos", "esta", "estas", "ese", "esos", "esa", "esas", "del", "al"
}
DE_STOP = {
    "der", "die", "das", "ein", "eine", "einen", "und", "oder", "aber", "wenn", "dann", "von",
    "im", "in", "am", "an", "auf", "ist", "sind", "war", "waren", "sein", "mit", "als", "zu",
    "zum", "zur", "des", "den", "dem"
}

ENGINE_NOISE = [
    re.compile(r"\b[-+]?\d+\.\d{1,2}\b"),         # numeric evals like +1.23
    re.compile(r"\bcp\s*[-+]?\d+\b", re.I),
    re.compile(r"\bdepth\s*\d+\b", re.I),
    re.compile(r"\bnodes\s*\d+\b", re.I),
    re.compile(r"\bnps\s*\d+\b", re.I),
    re.compile(r"\btime\s*\d+\b", re.I),
]

try:
    from langdetect import detect, DetectorFactory, LangDetectException  # type: ignore
    DetectorFactory.seed = 0
    _HAS_LANGDETECT = True
except Exception:  # pragma: no cover - optional dependency
    _HAS_LANGDETECT = False


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
    language: Optional[str] = None
    dropped_reason: Optional[str] = None
    raw_game: Optional[str] = None
    variation_moves: int = 0
    mainline_moves: int = 0


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


def _extract_header(raw_game: str, tag: str) -> str:
    match = re.search(rf'\[{tag}\s+"([^"]*)"\]', raw_game)
    return match.group(1).strip() if match else "Unknown"


class PGNQualityAnalyzer:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._init_db()
        # Allowed language combinations
        self.allowed_langs = {"en", "es"}

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

    def _score_annotations(self, density: float, comment_words: int, unique_exp_hits: float) -> float:
        # Prose-first scoring per Grok guidance
        density_bonus = min(density * 70, 18.0)
        length_bonus = min(comment_words / 22.0, 14.0)
        explanatory_bonus = min(unique_exp_hits * 1.95, 13.0)
        return density_bonus + length_bonus + explanatory_bonus

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

    def _detect_language(self, comments: List[str], headers: Dict[str, str]) -> Tuple[Optional[str], Set[str]]:
        # concatenate comments + a few free-text headers to feed LID
        text_parts = comments[:]
        for key in ("Event", "Site", "Annotator"):
            val = headers.get(key)
            if val:
                text_parts.append(val)
        blob = " ".join(text_parts).strip()
        if not blob or len(blob) < 30:
            return None, set()  # too short; caller can fall back to quality

        if _HAS_LANGDETECT:
            try:
                lang = detect(blob)
                return lang, {lang}
            except LangDetectException:
                return None, set()
            except Exception:
                return None, set()

        # Fallback heuristic using stopwords/umlauts/accents
        blob_lower = blob.lower()
        langs = set()
        if any(ch in blob_lower for ch in ("ä", "ö", "ü", "ß")):
            langs.add("de")
        if any(ch in blob_lower for ch in ("á", "é", "í", "ó", "ú", "ñ")):
            langs.add("es")
        # Stopword hits
        def score_hits(stopset):
            return sum(1 for w in blob_lower.split() if w in stopset)
        hits = {"en": score_hits(EN_STOP), "es": score_hits(ES_STOP), "de": score_hits(DE_STOP)}
        top = max(hits, key=hits.get)
        if hits[top] > 3:
            langs.add(top)
        return (next(iter(langs)) if langs else None, langs)

    def _engine_noise_penalty(self, comments: List[str], total_moves: int, comment_words: int, density: float) -> float:
        all_comments = " ".join(comments)
        penalty = 0.0

        # [%eval ...] heavy vs light
        eval_matches = len(re.findall(r"\[%eval [+-]?\d+\.\d+", all_comments))
        if eval_matches:
            if eval_matches >= 8 or (total_moves and eval_matches / total_moves > 0.4):
                penalty += 5.0
            else:
                penalty += 2.0

        # Engine names
        engine_tags = len(re.findall(r"\b(Stockfish|Leela|Lc0|Komodo|AlphaZero)\b", all_comments, re.I))
        if engine_tags >= 3:
            penalty += 4.0
        elif engine_tags > 0:
            penalty += 1.5

        # Classic numeric patterns
        for c in comments:
            for pat in ENGINE_NOISE:
                if pat.search(c):
                    penalty += 0.5

        # Additional engine-output patterns
        extra_patterns = [
            re.compile(r"\bdepth\s+\d+", re.I),
            re.compile(r"\bnodes\b", re.I),
            re.compile(r"\bnps\b", re.I),
            re.compile(r"\btbhits\b", re.I),
            re.compile(r"\btb hits\b", re.I),
            re.compile(r"\bmultipv\b", re.I),
            re.compile(r"\bscore cp\b", re.I),
            re.compile(r"\btime\s+\d+", re.I),
        ]
        for pat in extra_patterns:
            if pat.search(all_comments):
                penalty += 0.5

        # Softening with prose
        if comment_words >= 120 or density >= 0.18:
            penalty *= 0.20
        elif comment_words >= 70 or density >= 0.12:
            penalty *= 0.45
        return penalty

    def _content_signal(self, comments: List[str]) -> Tuple[int, int, float, float]:
        # returns total_words, content_words, unique_ratio, avg_len
        words = []
        for c in comments:
            words.extend(c.split())
        total = len(words)
        if total == 0:
            return 0, 0, 0.0, 0.0
        content = [w for w in words if w.lower() not in EN_STOP | ES_STOP | DE_STOP]
        unique_ratio = len(set(w.lower() for w in content)) / max(len(content), 1)
        avg_len = sum(len(w) for w in words) / total
        return total, len(content), unique_ratio, avg_len

    def _count_variation_moves(self, game: chess.pgn.Game) -> Tuple[int, int]:
        mainline_moves = len(list(game.mainline_moves()))
        variation_moves = 0
        # count all moves in non-mainline branches
        def walk_variation(node: chess.pgn.ChildNode) -> int:
            count = 1 if node.move is not None else 0
            for var in node.variations:
                count += walk_variation(var)
            return count
        for node in game.mainline():
            if node.variations:
                # skip mainline child (first)
                for var in node.variations[1:]:
                    variation_moves += walk_variation(var)
        return variation_moves, mainline_moves

    def _has_comment_in_variation(self, node: chess.pgn.ChildNode) -> bool:
        if node.comment and node.comment.strip():
            return True
        for var in node.variations:
            if self._has_comment_in_variation(var):
                return True
        return False

    def _strip_empty_variations(self, game: chess.pgn.Game):
        for node in game.mainline():
            kept = []
            if node.variations:
                main_child = node.variations[0]
                for var in node.variations[1:]:
                    if var.comment and var.comment.strip():
                        self._strip_empty_variations_from_node(var)
                        kept.append(var)
                    elif self._has_comment_in_variation(var):
                        self._strip_empty_variations_from_node(var)
                        kept.append(var)
                node.variations = [main_child] + kept

    def _strip_empty_variations_from_node(self, node: chess.pgn.ChildNode):
        # recurse and strip empty variations from a given node
        if not node.variations:
            return
        kept = []
        main_child = node.variations[0]
        for var in node.variations[1:]:
            if var.comment and var.comment.strip():
                self._strip_empty_variations_from_node(var)
                kept.append(var)
            elif self._has_comment_in_variation(var):
                self._strip_empty_variations_from_node(var)
                kept.append(var)
        node.variations = [main_child] + kept

    def score_game(
        self,
        game: chess.pgn.Game,
        *,
        file_name: str = "",
        game_index: int = 0,
        raw_text: Optional[str] = None,
    ) -> Optional[GameScore]:
        if game is None:
            return None
        try:
            headers = dict(game.headers)
            self._strip_empty_variations(game)
            text = str(game)
            total_moves = len(list(game.mainline_moves()))
            if total_moves == 0:
                return None

            annotation_count = len(ANNOTATION_PATTERN.findall(text)) + len(NAG_PATTERN.findall(text))
            annotation_density = annotation_count / max(total_moves, 1)
            comments = COMMENT_PATTERN.findall(text)
            comment_words = sum(len(comment.split()) for comment in comments)
            has_variations = bool(VARIATION_PATTERN.search(text))
            has_result = bool(RESULT_PATTERN.search(text))

            # Language gate per game (allow EN, ES, or EN+DE; otherwise drop)
            lang, lang_set = self._detect_language(comments, headers)
            allowed_lang = (
                (lang in self.allowed_langs)
                or (lang is None and not lang_set)  # unknown => let other signals decide
                or (("en" in lang_set) and ("de" in lang_set))
            )
            if lang and lang not in self.allowed_langs and not (("en" in lang_set) and ("de" in lang_set)):
                return None

            # Comment-first signals
            total_comment_words, content_words, unique_ratio, avg_word_len = self._content_signal(comments)
            words_per_100_moves = (total_comment_words / max(total_moves, 1)) * 100
            has_instruction = any(re.search(p, " ".join(comments), re.IGNORECASE) for p in EDU_KEYWORDS)
            # Explanatory keyword hits (unique presence)
            all_comments_lower = " ".join(comments).lower()
            unique_exp_hits = 0.0
            seen = set()
            for word, weight in (
                # tier 1
                [(w, 1.0) for w in [
                    "plan", "plans", "planned", "planning",
                    "idea", "ideas",
                    "intention", "intentions",
                    "prepare", "preparing", "prepares", "prepared", "preparation",
                    "prophylaxis", "prophylactic",
                    "prevent", "prevents", "preventing",
                    "threat", "threats", "threaten", "threatening", "threatened",
                    "force", "forces", "forced", "forcing",
                    "sacrifice", "sacrifices", "sacrificial", "sacrificed", "sac", "sacs",
                    "compensation", "compensated",
                    "initiative",
                    "pressure",
                    "attack", "attacks", "attacking", "attacker", "attackers",
                    "defend", "defends", "defending", "defence", "defense",
                    "weakness", "weaknesses", "weak",
                    "hole", "holes",
                    "outpost", "outposts",
                    "advantage", "advantages",
                    "drawback", "drawbacks",
                    "punish", "punishes", "punished", "punishing",
                    "refute", "refutes", "refuted", "refutation",
                ]] +
                # tier 2
                [(w, 0.7) for w in [
                    "should", "could", "would", "instead", "alternative", "alternatives",
                    "interesting", "typical", "typically", "standard",
                    "manoeuvre", "manoeuvres", "maneuver", "maneuvers",
                    "breakthrough", "breakthroughs",
                    "blockade", "blockades",
                    "zugzwang",
                    "domination", "dominates", "dominating",
                    "the point", "now white", "now black", "with the idea", "in order to", "aiming",
                    "targeting", "target", "targets", "targeted",
                ]] +
                # tier 3
                [(w, 0.5) for w in [
                    "because", "since", "as", "leads", "results", "followed", "threatening",
                    "meanwhile", "at the same time", "why", "how", "what happens", "however", "but",
                    "therefore", "thus", "so", "then",
                ]]
            ):
                if word in seen:
                    continue
                if re.search(rf"\\b{re.escape(word)}\\b", all_comments_lower):
                    unique_exp_hits += weight
                    seen.add(word)

            structure = self._score_structure(headers, total_moves, has_result)
            annotation_score = self._score_annotations(annotation_density, comment_words, unique_exp_hits)
            humanness = self._score_humanness(headers, total_moves)
            educational = self._score_educational(comments)
            engine_penalty = self._engine_noise_penalty(comments, total_moves, comment_words, annotation_density)

            variation_moves, mainline_moves = self._count_variation_moves(game)
            var_penalty = 0.0
            if mainline_moves > 0:
                ratio = variation_moves / mainline_moves
                if ratio > 1.0 and comment_words < 110:
                    var_penalty = min((ratio - 1.0) * 10.0, 10.0)

            evs = structure + annotation_score + humanness + educational + 25
            evs = max(evs - engine_penalty - var_penalty, 0)
            if total_moves < 10:
                evs = max(evs - 10, 0)
            evs = min(evs, 100)

            # Hard 80+ gate: require some prose/density
            if comment_words < 65 and annotation_density < 0.22:
                evs = min(evs, 79)

            # Simple game_type heuristic with comment bias
            if comment_words < 5:
                game_type = "database_dump"
            elif annotation_density >= 0.2 or comment_words > 150:
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
                language=lang,
                raw_game=text,
                variation_moves=variation_moves,
                mainline_moves=mainline_moves,
            )
        except Exception as exc:
            # Skip games that blow up parsing (e.g., bad FEN)
            event = game.headers.get("Event", "Unknown")
            site = game.headers.get("Site", "Unknown")
            date = game.headers.get("Date", "Unknown")
            print(
                f"   ⚠️  {file_name} Game #{game_index} [Event: {event} | Site: {site} | Date: {date}] failed: {exc}",
                file=sys.stderr,
            )
            return None

    def _iter_streaming_games(self, filepath: Path):
        """
        Yields raw PGN text for giant multi-game files without loading everything
        into memory. ChessBase/HIARCS style dumps always start each game with an
        [Event ...] header, so we split on that sentinel.
        """
        buffer: List[str] = []
        try:
            handle = open(filepath, "r", encoding="utf-8", errors="ignore")
        except FileNotFoundError as exc:
            print(f"   ⚠️  Missing file while streaming games: {filepath} ({exc})")
            return

        with handle:
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

    def _log_faulty_game(
        self,
        filename: str,
        game_index: int,
        event: str,
        site: str,
        date: str,
        reason: str,
        snippet: str,
    ):
        print(
            f"   ⚠️  {filename} Game #{game_index} "
            f"[Event: {event} | Site: {site} | Date: {date}] failed: {reason}",
            file=sys.stderr,
        )
        clean_snippet = snippet.replace("\n", " ")[:140]
        print(f"      Snippet: {clean_snippet}", file=sys.stderr)

    def analyze_file(
        self,
        filepath: Path,
        keep_thresholds: List[float],
        out_handles: Dict[float, any],
        kept_writer: Optional[csv.writer] = None,
    ) -> Optional[FileSummary]:
        scores: List[GameScore] = []
        if not filepath.exists():
            print(f"   ⚠️  Missing file on disk, skipping: {filepath}")
            return None
        skipped_games = 0

        for idx, raw_game in enumerate(self._iter_streaming_games(filepath), start=1):
            if not raw_game:
                continue
            event = _extract_header(raw_game, "Event")
            site = _extract_header(raw_game, "Site")
            date = _extract_header(raw_game, "Date")
            try:
                game = chess.pgn.read_game(io.StringIO(raw_game + "\n\n"))
            except Exception as exc:  # pylint: disable=broad-exception-caught
                skipped_games += 1
                self._log_faulty_game(
                    filepath.name,
                    idx,
                    event,
                    site,
                    date,
                    f"Parser error: {exc}",
                    raw_game,
                )
                continue

            if game is None:
                skipped_games += 1
                self._log_faulty_game(
                    filepath.name,
                    idx,
                    event,
                    site,
                    date,
                    "Parser returned None",
                    raw_game,
                )
                continue

            scored = self.score_game(game, file_name=filepath.name, game_index=idx, raw_text=raw_game)
            if scored:
                scores.append(scored)
                for t, handle in out_handles.items():
                    if scored.evs >= t:
                        handle.write((scored.raw_game or raw_game) + "\n\n")
                if kept_writer and scored.evs >= min(keep_thresholds):
                    kept_writer.writerow(
                        [
                            filepath.name,
                            idx,
                            _extract_header(raw_game, "Event"),
                            _extract_header(raw_game, "Site"),
                            _extract_header(raw_game, "Date"),
                            f"{scored.evs:.2f}",
                            scored.language or "",
                            scored.game_type,
                            scored.total_moves,
                            f"{scored.annotation_density:.4f}",
                            scored.comment_words,
                        ]
                    )
            else:
                skipped_games += 1
                self._log_faulty_game(
                    filepath.name,
                    idx,
                    event,
                    site,
                    date,
                    "Scoring skipped (see earlier warnings)",
                    raw_game,
                )

        if not scores:
            return None

        if skipped_games:
            print(f"   ⚠️  {skipped_games} games skipped (see log for details)")

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
    if path.is_file() and path.suffix.lower() == ".pgn" and not path.name.startswith("._"):
        return [path]
    if path.is_dir():
        return sorted(p for p in path.rglob("*.pgn") if p.is_file() and not p.name.startswith("._"))
    return []


def parse_thresholds(thr_str: str) -> List[float]:
    vals = []
    for part in thr_str.split(","):
        part = part.strip()
        if not part:
            continue
        try:
            vals.append(float(part))
        except ValueError:
            pass
    return vals or [70.0]


def main():
    parser = argparse.ArgumentParser(description="Analyze PGN quality before ingestion")
    parser.add_argument("pgn_path", nargs="+", help="PGN file(s) or directory/ies")
    parser.add_argument("--db", default="pgn_analysis.db", help="SQLite database path")
    parser.add_argument("--json", help="Optional JSON output file")
    parser.add_argument("--limit", type=int, help="Only analyze first N files")
    parser.add_argument("--print-summary", action="store_true", help="Print per-file summary table (sorted by avg EVS)")
    parser.add_argument("--summary-csv", help="Optional CSV path for per-file summaries")
    parser.add_argument("--worst", type=int, help="Limit summary output to the lowest N avg EVS files")
    parser.add_argument("--output-pgn", help="Optional output PGN file containing kept games (single threshold)")
    parser.add_argument("--output-dir", help="Directory to place thresholded PGNs (when multiple thresholds)")
    parser.add_argument("--kept-csv", help="Optional CSV with per-game scores for kept games")
    parser.add_argument("--thresholds", default="70", help="Comma-separated EVS thresholds (default: 70)")
    parser.add_argument("--append", action="store_true", help="Append to existing output files instead of overwriting")
    args = parser.parse_args()

    thresholds = sorted(set(parse_thresholds(args.thresholds)))

    all_files: List[Path] = []
    for p in args.pgn_path:
        all_files.extend(iter_pgn_files(Path(p)))
    # filter out AppleDouble/hidden and hash-prefixed
    all_files = [p for p in all_files if not (p.name.startswith("._") or p.name.startswith("#") or p.name.startswith("."))]
    if not all_files:
        print(f"No .pgn files found in given paths: {args.pgn_path}")
        sys.exit(1)
    if args.limit:
        all_files = all_files[: args.limit]

    analyzer = PGNQualityAnalyzer(Path(args.db))
    summaries: List[Dict] = []

    # Prepare output PGN handles keyed by threshold
    out_handles: Dict[float, any] = {}
    if len(thresholds) == 1:
        target_path = Path(args.output_pgn) if args.output_pgn else Path(args.output_dir or ".") / f"high_quality_{int(thresholds[0])}.pgn"
        target_path.parent.mkdir(parents=True, exist_ok=True)
        mode = "a" if args.append else "w"
        out_handles[thresholds[0]] = target_path.open(mode, encoding="utf-8")
    else:
        if not args.output_dir:
            print("When using multiple thresholds, provide --output-dir.")
            sys.exit(1)
        base = Path(args.output_dir)
        base.mkdir(parents=True, exist_ok=True)
        mode = "a" if args.append else "w"
        for t in thresholds:
            path = base / f"high_quality_{int(t)}.pgn"
            out_handles[t] = path.open(mode, encoding="utf-8")

    kept_csv_writer = None
    kept_csv_handle = None
    if args.kept_csv:
        kept_csv_path = Path(args.kept_csv)
        kept_csv_path.parent.mkdir(parents=True, exist_ok=True)
        mode = "a" if args.append else "w"
        kept_csv_handle = kept_csv_path.open(mode, encoding="utf-8", newline="")
        kept_csv_writer = csv.writer(kept_csv_handle)
        if kept_csv_path.stat().st_size == 0:
            kept_csv_writer.writerow(
                ["file", "game_index", "event", "site", "date", "evs", "language", "game_type", "total_moves", "annotation_density", "comment_words"]
            )

    print(f"\nAnalyzing {len(all_files)} PGN file(s)...\n")
    start = time.time()

    for idx, file in enumerate(all_files, start=1):
        print(f"[{idx}/{len(all_files)}] {file.name}")
        summary = analyzer.analyze_file(
            file,
            keep_thresholds=thresholds,
            out_handles=out_handles,
            kept_writer=kept_csv_writer,
        )
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

    if (args.print_summary or args.summary_csv) and summaries:
        ordered = sorted(summaries, key=lambda s: s["avg_evs"])
        if args.worst:
            ordered = ordered[: args.worst]
        if args.print_summary:
            header = f"{'AVG':>6} {'MED':>6} {'HQ':>5} {'MQ':>5} {'LQ':>5} {'MOVES':>7}  Filename"
            print("\nPer-file summary (lowest avg EVS first):")
            print(header)
            print("-" * len(header))
            for summary in ordered:
                print(
                    f"{summary['avg_evs']:6.2f} "
                    f"{summary['median_evs']:6.2f} "
                    f"{summary['high_quality']:5d} "
                    f"{summary['medium_quality']:5d} "
                    f"{summary['low_quality']:5d} "
                    f"{summary['avg_moves']:7.1f}  "
                    f"{summary['filename']}"
                )
        if args.summary_csv:
            out_csv = Path(args.summary_csv)
            out_csv.parent.mkdir(parents=True, exist_ok=True)
            with open(out_csv, "w", encoding="utf-8", newline="") as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(
                    [
                        "filename",
                        "total_games",
                        "high_quality",
                        "medium_quality",
                        "low_quality",
                        "avg_evs",
                        "median_evs",
                        "avg_annotation_density",
                        "avg_moves",
                    ]
                )
                for summary in ordered:
                    writer.writerow(
                        [
                            summary["filename"],
                            summary["total_games"],
                            summary["high_quality"],
                            summary["medium_quality"],
                            summary["low_quality"],
                            summary["avg_evs"],
                            summary["median_evs"],
                            summary["avg_annotation_density"],
                            summary["avg_moves"],
                        ]
                    )
            print(f"Summary CSV written to {out_csv}")

    for h in out_handles.values():
        h.close()
    if kept_csv_handle:
        kept_csv_handle.close()
if __name__ == "__main__":
    main()
