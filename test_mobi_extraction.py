#!/usr/bin/env python3
"""
Test MOBI extraction on 5 sample files
"""

import mobi
from pathlib import Path
from typing import Tuple, Optional

# Test files
TEST_FILES = {
    'seirawan': '/Volumes/T7 Shield/epub/unknown_author_2003_winning_chess_strategies_yasser_seirawan_jeremy_silman_everyman_chess_tls.mobi',
    'match_century': '/Volumes/T7 Shield/epub/unknown_author_0000_the_match_of_the_century_ussr_vs_the_world_tigran_petrosian_and_aleksandar_matanović.mobi',
    'bronstein': '/Volumes/T7 Shield/epub/bronstein_1953_zurich_international_chess_tournament.mobi',
    'heisman': '/Volumes/T7 Shield/epub/heisman_0000_maximize_your_chess_potential.mobi',
    'tal': '/Volumes/T7 Shield/epub/koblenz_0000_mikhail_tal_the_streetfighting_years.mobi'
}


def extract_mobi_text(mobi_path: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Extract text from MOBI file using mobi library.

    Args:
        mobi_path: Path to the MOBI file

    Returns:
        tuple: (text, error_message)
        - text is None if extraction failed
        - error_message explains why extraction failed
    """
    try:
        # Extract using mobi library
        tempdir, filepath = mobi.extract(mobi_path)

        # Read the extracted HTML/text
        html_file = Path(tempdir) / "mobi7" / "book.html"
        if not html_file.exists():
            # Try alternative path
            html_file = Path(tempdir) / "book.html"

        if not html_file.exists():
            return None, "No HTML content found after extraction"

        # Read and parse HTML
        from bs4 import BeautifulSoup
        with open(html_file, 'r', encoding='utf-8', errors='ignore') as f:
            html_content = f.read()

        soup = BeautifulSoup(html_content, 'html.parser')
        text = soup.get_text(separator='\n', strip=True)

        # Clean up temp directory
        import shutil
        shutil.rmtree(tempdir, ignore_errors=True)

        # Basic quality check
        word_count = len(text.split())
        if word_count < 500:
            return None, f"Insufficient text: {word_count} words"

        return text, None

    except FileNotFoundError:
        return None, f"File not found: {mobi_path}"
    except Exception as e:
        return None, f"MOBI extraction error: {str(e)}"


def analyze_text_quality(text: str, name: str) -> dict:
    """Analyze extraction quality."""
    # Count words
    word_count = len(text.split())

    # Check for chess notation
    chess_symbols = {
        '♔': text.count('♔'),
        '♕': text.count('♕'),
        '♖': text.count('♖'),
        '♗': text.count('♗'),
        '♘': text.count('♘'),
        '♙': text.count('♙'),
        '±': text.count('±'),
        '∓': text.count('∓'),
        '≤': text.count('≤'),
        '≥': text.count('≥'),
    }

    # Check for algebraic notation patterns
    import re
    move_patterns = len(re.findall(r'\b[KQRBN]?[a-h]?[1-8]?x?[a-h][1-8][+#]?\b', text))

    # Check for encoding errors
    encoding_errors = text.count('�') + text.count('�')

    return {
        'name': name,
        'word_count': word_count,
        'chess_symbols': chess_symbols,
        'move_patterns': move_patterns,
        'encoding_errors': encoding_errors,
        'first_500_chars': text[:500],
    }


def main():
    """Test MOBI extraction on 5 files."""
    print("=" * 80)
    print("MOBI EXTRACTION TEST - 5 FILES")
    print("=" * 80)

    results = []

    for name, filepath in TEST_FILES.items():
        print(f"\n📖 Testing: {name}")
        print(f"   Path: {Path(filepath).name}")

        # Extract text
        text, error = extract_mobi_text(filepath)

        if error:
            print(f"   ❌ Error: {error}")
            results.append({'name': name, 'error': error})
            continue

        # Analyze quality
        analysis = analyze_text_quality(text, name)
        results.append(analysis)

        # Save to file
        output_file = f"test_extractions/{name}.txt"
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(text)
        print(f"   ✅ Saved to: {output_file}")
        print(f"   Words: {analysis['word_count']:,}")

    # Summary report
    print("\n" + "=" * 80)
    print("EXTRACTION QUALITY REPORT")
    print("=" * 80)

    for result in results:
        if 'error' in result:
            print(f"\n❌ {result['name']}: FAILED")
            print(f"   Error: {result['error']}")
            continue

        print(f"\n✅ {result['name']}:")
        print(f"   Word count: {result['word_count']:,}")
        print(f"   Encoding errors: {result['encoding_errors']}")
        print(f"   Move patterns found: {result['move_patterns']}")

        # Chess symbols
        symbols_found = {k: v for k, v in result['chess_symbols'].items() if v > 0}
        if symbols_found:
            print(f"   Chess symbols: {symbols_found}")
        else:
            print(f"   Chess symbols: None found")

        print(f"\n   First 500 characters:")
        print(f"   {'-' * 76}")
        print(f"   {result['first_500_chars']}")
        print(f"   {'-' * 76}")

    print("\n" + "=" * 80)
    print("TEST COMPLETE")
    print("=" * 80)
    print(f"Extracted files saved to: test_extractions/")
    print(f"Ready for manual review.")


if __name__ == '__main__':
    main()
