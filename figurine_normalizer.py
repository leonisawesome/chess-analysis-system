#!/usr/bin/env python3
"""
Chess Figurine Normalization Module
Converts Unicode chess figurines to algebraic notation.
"""

FIGURINE_MAP = {
    # White pieces
    '♔': 'K', '♕': 'Q', '♖': 'R', '♗': 'B', '♘': 'N', '♙': 'P',
    # Black pieces
    '♚': 'K', '♛': 'Q', '♜': 'R', '♝': 'B', '♞': 'N', '♟': 'P'
}


def normalize_figurines(text: str) -> str:
    """
    Convert chess figurines to algebraic notation.

    Args:
        text: Text containing chess figurines

    Returns:
        Text with figurines replaced by letters

    Example:
        >>> normalize_figurines("1. ♘f3 ♞c6")
        "1. Nf3 Nc6"
    """
    for figurine, letter in FIGURINE_MAP.items():
        text = text.replace(figurine, letter)
    return text


def has_figurines(text: str) -> bool:
    """Check if text contains chess figurines."""
    return any(figurine in text for figurine in FIGURINE_MAP.keys())


def count_figurines(text: str) -> dict:
    """Count occurrences of each figurine type."""
    counts = {}
    for figurine, letter in FIGURINE_MAP.items():
        count = text.count(figurine)
        if count > 0:
            counts[figurine] = count
    return counts


if __name__ == '__main__':
    # Test cases
    test_text = "1. ♘f3 ♞c6 2. ♗b5 ♝g4 3. ♔e1"
    print(f"Original: {test_text}")
    print(f"Normalized: {normalize_figurines(test_text)}")
    print(f"Has figurines: {has_figurines(test_text)}")
    print(f"Figurine counts: {count_figurines(test_text)}")
