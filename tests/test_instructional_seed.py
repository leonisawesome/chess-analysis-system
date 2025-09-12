import csv
from pathlib import Path

from chess_rag_system.analysis.instructional_detector import detect_instructional

SEED = Path("data/labels/instructional_seed.csv")


def test_instructional_seed_behaves():
    assert SEED.exists(), "Missing data/labels/instructional_seed.csv"
    with SEED.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader, 1):
            text = row["text"]
            expected = row["label"].strip().lower() == "instructional"
            got = detect_instructional(text)
            assert got is expected, f"row {i} misclassified: {text[:80]!r}"

