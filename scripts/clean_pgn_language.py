#!/usr/bin/env python3
"""
Strip duplicate German prose from ChessBase PGN comments.

Many ChessBase Magazine games embed back-to-back English + German sentences
inside the same comment block. Downstream RAG consumers only need the English
text, so this utility keeps English sentences (plus metadata tokens like
[%eval …]) while dropping the German translation.

Usage:
    python scripts/clean_pgn_language.py --source /path/to/input.pgn \
        --output /path/to/output_english_only.pgn
"""

from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional, Sequence, Tuple

from langdetect import DetectorFactory, LangDetectException, detect
import logging

try:
    from spacy.lang.de.stop_words import STOP_WORDS as SPACY_STOPWORDS
except Exception:
    SPACY_STOPWORDS = set()

DetectorFactory.seed = 0
logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?:])\s+")
TOKEN_RE = re.compile(r"\[%.*?\]")
COMMENT_RE = re.compile(r"\{([^{}]*)\}")
WORD_RE = re.compile(r"[A-Za-zÄÖÜäöüß]+")
GERMAN_CHARS = set("äöüßÄÖÜß")

GERMAN_STOPWORDS = {
    "aber",
    "abzugeben",
    "als",
    "auch",
    "auf",
    "aus",
    "bald",
    "besser",
    "bevor",
    "bewegt",
    "bewegen",
    "bewegt",
    "bewertung",
    "bevor",
    "bis",
    "blieb",
    "bleibt",
    "bringen",
    "bringe",
    "bringt",
    "dabei",
    "dadurch",
    "dafür",
    "dagegen",
    "daher",
    "damals",
    "damit",
    "danach",
    "dann",
    "darauf",
    "darum",
    "das",
    "dass",
    "deckt",
    "den",
    "denn",
    "der",
    "des",
    "dessen",
    "deswegen",
    "die",
    "dies",
    "diese",
    "diesem",
    "diesen",
    "dieser",
    "dieses",
    "doch",
    "dort",
    "drauf",
    "drängt",
    "drei",
    "dunkel",
    "durch",
    "eben",
    "ebenfalls",
    "eher",
    "eigentlich",
    "ein",
    "eine",
    "einem",
    "einen",
    "einer",
    "einfach",
    "einige",
    "einiger",
    "einmal",
    "ende",
    "entscheiden",
    "er",
    "erst",
    "erstens",
    "etwas",
    "falls",
    "fast",
    "feld",
    "figur",
    "fiel",
    "finden",
    "findet",
    "folglich",
    "fort",
    "fragen",
    "freut",
    "früh",
    "für",
    "gegen",
    "gegner",
    "geht",
    "gekommen",
    "gelungen",
    "genau",
    "gerade",
    "gern",
    "geschäft",
    "gesehen",
    "gestern",
    "gewesen",
    "geht",
    "gibt",
    "gilt",
    "gute",
    "guter",
    "gut",
    "habe",
    "haben",
    "hält",
    "halten",
    "hätte",
    "hat",
    "hatte",
    "her",
    "herausholen",
    "hier",
    "hingegen",
    "hinüber",
    "hinweg",
    "hinzu",
    "hoch",
    "ich",
    "ihm",
    "ihn",
    "ihr",
    "ihre",
    "ihren",
    "immer",
    "ist",
    "kam",
    "kamp",
    "kann",
    "kannst",
    "käme",
    "kämpft",
    "keine",
    "kein",
    "klein",
    "klingt",
    "kommt",
    "konnten",
    "konnte",
    "kurz",
    "lang",
    "lassen",
    "läuft",
    "leicht",
    "leider",
    "letztlich",
    "lief",
    "liegt",
    "linie",
    "machen",
    "macht",
    "macht",
    "man",
    "manchmal",
    "mehr",
    "mein",
    "meine",
    "meist",
    "mich",
    "mir",
    "möglich",
    "muss",
    "müssen",
    "nach",
    "nahm",
    "natürlich",
    "noch",
    "nun",
    "nur",
    "obwohl",
    "oder",
    "offen",
    "oft",
    "ohne",
    "paar",
    "partie",
    "passiert",
    "plötzlich",
    "position",
    "richtig",
    "rochieren",
    "ruck",
    "sagt",
    "sagte",
    "sah",
    "samt",
    "schlecht",
    "schlimm",
    "schlug",
    "schön",
    "schwarz",
    "sehr",
    "sei",
    "sein",
    "seine",
    "seiner",
    "seinem",
    "seit",
    "seiten",
    "selbst",
    "sicher",
    "sind",
    "sofort",
    "solange",
    "solche",
    "solcher",
    "sowie",
    "später",
    "springer",
    "stattdessen",
    "steht",
    "stehen",
    "stieg",
    "stünde",
    "stürzen",
    "tatsächlich",
    "trotzdem",
    "turm",
    "über",
    "übrig",
    "um",
    "unbedingt",
    "und",
    "unser",
    "unten",
    "untersucht",
    "viel",
    "viele",
    "vielen",
    "vielleicht",
    "voll",
    "vor",
    "wann",
    "war",
    "waren",
    "warum",
    "weg",
    "weil",
    "weiter",
    "welche",
    "welcher",
    "wem",
    "weniger",
    "werden",
    "werde",
    "werdenden",
    "werdenden",
    "werde",
    "wird",
    "wirklich",
    "wobei",
    "wohl",
    "wollte",
    "worden",
    "während",
    "währenddessen",
    "zeit",
    "ziemlich",
    "zug",
    "zugleich",
    "zunächst",
    "zurück",
    "zwischen",
}

GERMAN_HARD_MARKERS = {
    "aber",
    "den",
    "dem",
    "der",
    "des",
    "die",
    "doch",
    "dort",
    "dass",
    "das",
    "denn",
    "ich",
    "mir",
    "mich",
    "noch",
    "nun",
    "oder",
    "seh",
    "sein",
    "seine",
    "seiner",
    "und",
    "weil",
    "wenn",
    "wie",
    "wir",
    "wird",
    "würde",
}


@dataclass
class CommentStats:
    total_comments: int = 0
    modified_comments: int = 0
    sentences_dropped: int = 0


def normalize_word(word: str) -> str:
    word = word.lower().replace("ß", "ss")
    return "".join(ch for ch in word if ch.isalpha())


if SPACY_STOPWORDS:
    GERMAN_STOPWORDS.update(
        normalize_word(word) for word in SPACY_STOPWORDS if normalize_word(word)
    )


def german_ratio(text: str) -> float:
    raw_words = WORD_RE.findall(text)
    if not raw_words:
        return 0.0
    hits = sum(1 for word in raw_words if is_germanish_word(word))
    return hits / len(raw_words)


def detect_language(text: str) -> str:
    cleaned = text.strip()
    if not cleaned:
        return "unknown"
    alpha = re.sub(r"[^A-Za-zÄÖÜäöüß]", "", cleaned)
    if len(alpha) < 12:
        return "unknown"
    try:
        return detect(cleaned)
    except LangDetectException:
        return "unknown"


def is_germanish_word(word: str) -> bool:
    token = normalize_word(word)
    if not token:
        return False
    if token in GERMAN_STOPWORDS:
        return True
    if any(ch in word for ch in GERMAN_CHARS):
        return True
    for suffix in ("e", "en", "er", "es", "em", "n", "s"):
        if token.endswith(suffix) and token[: -len(suffix)] in GERMAN_STOPWORDS:
            return True
    return False


def detect_german_break(tokens: Sequence[str]) -> Optional[int]:
    german_run = 0
    english_seen = 0
    for idx, raw_token in enumerate(tokens):
        token = normalize_word(raw_token)
        if not token:
            continue
        if is_germanish_word(raw_token):
            german_run += 1
            if token in GERMAN_HARD_MARKERS and english_seen >= 2:
                return idx
            if german_run >= 2 and english_seen >= 4:
                return idx - german_run + 1
        else:
            english_seen += 1
            german_run = 0
    return None


def split_sentences(text: str) -> Iterable[str]:
    for candidate in SENTENCE_SPLIT_RE.split(text.strip()):
        snippet = candidate.strip()
        if snippet:
            yield snippet


def strip_german_tail(sentence: str) -> str:
    tokens = sentence.split()
    break_at = detect_german_break(tokens)
    if break_at is None:
        break_at = detect_language_switch(tokens)
    if break_at is None:
        return sentence.strip()
    return " ".join(tokens[:break_at]).strip()


def detect_language_switch(tokens: Sequence[str]) -> Optional[int]:
    if len(tokens) < 6:
        return None
    for idx in range(3, len(tokens) - 2):
        prefix = " ".join(tokens[:idx])
        suffix = " ".join(tokens[idx:])
        if classify_sentence(suffix) == "de" and classify_sentence(prefix) == "en":
            return idx
    return None


def classify_sentence(text: str) -> str:
    lang = detect_language(text)
    if lang == "unknown":
        ratio = german_ratio(text)
        if ratio >= 0.45:
            return "de"
        return "en"
    return lang


def clean_comment(comment: str) -> Tuple[str, int]:
    parts: List[str] = []
    index = 0
    dropped_sentences = 0

    while index < len(comment):
        if comment.startswith("[%", index):
            end = comment.find("]", index)
            if end == -1:
                parts.append(comment[index:].strip())
                break
            token = comment[index : end + 1]
            parts.append(clean_metadata_token(token))
            index = end + 1
            continue

        next_token = comment.find("[%", index)
        chunk_end = next_token if next_token != -1 else len(comment)
        chunk = comment[index:chunk_end]
        sentences = []
        if chunk.strip():
            sentences.extend(split_sentences(chunk))
        for sentence in sentences:
            candidate = strip_german_tail(sentence)
            if not candidate:
                continue
            lang = classify_sentence(candidate)
            if lang == "de":
                dropped_sentences += 1
                continue
            if german_ratio(candidate) >= 0.45:
                dropped_sentences += 1
                continue
            parts.append(candidate.strip())
        index = chunk_end
    cleaned = " ".join(p for p in parts if p.strip())
    return cleaned.strip(), dropped_sentences


def clean_metadata_token(token: str) -> str:
    token = token.strip()
    if not token.endswith("]"):
        return token
    if ',"De",' in token:
        token = token.split(',"De",', 1)[0] + "]"
    return token
def clean_pgn_text(text: str, stats: CommentStats) -> str:
    logger.info("Beginning comment cleanup pass...")
    def repl(match: re.Match[str]) -> str:
        original = match.group(1)
        stats.total_comments += 1
        cleaned, dropped = clean_comment(original)
        if dropped:
            stats.sentences_dropped += dropped
        changed = cleaned != original.strip()
        if changed:
            stats.modified_comments += 1
        if stats.total_comments % 1000 == 0:
            logger.info(
                "Processed %s comments (%s modified so far)",
                stats.total_comments,
                stats.modified_comments,
            )
        payload = cleaned if cleaned else ""
        payload = payload.strip()
        if not payload:
            return ""
        return "{ " + payload + " }"

    return COMMENT_RE.sub(repl, text)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Remove duplicate German sentences from PGN comments."
    )
    parser.add_argument(
        "--source",
        required=True,
        type=Path,
        help="Path to the ChessBase PGN file to clean.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Destination file for the cleaned PGN (defaults to '<source>_english.pgn').",
    )
    return parser


def main() -> int:
    parser = build_arg_parser()
    args = parser.parse_args()
    source: Path = args.source
    if not source.exists():
        parser.error(f"PGN file not found: {source}")

    output = args.output or source.with_name(f"{source.stem}_english{source.suffix}")

    stats = CommentStats()
    logger.info("Cleaning PGN language: source=%s destination=%s", source, output)
    data = source.read_bytes()
    if data.startswith(b"\xef\xbb\xbf"):
        data = data[3:]
    text = data.decode("utf-8", errors="ignore")
    cleaned_text = clean_pgn_text(text, stats)
    output.write_text(cleaned_text, encoding="utf-8")
    if stats.total_comments == 0:
        logger.warning("No PGN comments found inside %s", source)
    logger.info(
        "Cleaned PGN written to %s (%s/%s comments updated, %s German sentences removed).",
        output,
        stats.modified_comments,
        stats.total_comments,
        stats.sentences_dropped,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
