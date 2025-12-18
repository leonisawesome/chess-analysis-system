#!/usr/bin/env python3
"""
Detect languages in PGN files and report non-English/Spanish files.

Uses langdetect library to analyze text content in PGN files,
particularly focusing on comments and annotations.
"""

import os
import sys
import argparse
import csv
import re
from pathlib import Path
from typing import List, Tuple, Optional
from collections import Counter

try:
    from langdetect import detect, DetectorFactory, LangDetectException
    # Set seed for consistent results
    DetectorFactory.seed = 0
except ImportError:
    print("Error: langdetect library not found. Install with: pip install langdetect")
    sys.exit(1)


def extract_text_from_pgn(file_path: str) -> str:
    """
    Extract textual content from PGN file for language detection.
    Focuses on comments (in curly braces) and annotations.
    """
    text_parts = []

    # Try multiple encodings
    for encoding in ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']:
        try:
            with open(file_path, 'r', encoding=encoding) as f:
                content = f.read()

                # Extract comments in curly braces {like this}
                comments = re.findall(r'\{([^}]+)\}', content)
                text_parts.extend(comments)

                # Extract header values (which may contain language-specific text)
                headers = re.findall(r'\[(\w+)\s+"([^"]+)"\]', content)
                for header_name, header_value in headers:
                    if header_name in ['Event', 'Site', 'White', 'Black', 'Annotator']:
                        text_parts.append(header_value)

                # Extract text annotations (like !?, !, ??, etc. with text)
                # Look for lines that start with non-move text
                lines = content.split('\n')
                for line in lines:
                    # Skip header lines and move lines
                    if not line.startswith('[') and not re.match(r'^\s*\d+\.', line):
                        # Check if line has substantial text (not just moves)
                        text_content = re.sub(r'[NBRQK]?[a-h]?[1-8]?x?[a-h][1-8][+#]?', '', line)
                        text_content = re.sub(r'[O0]-[O0](-[O0])?', '', text_content)
                        text_content = text_content.strip()
                        if len(text_content) > 20:  # Substantial text
                            text_parts.append(text_content)

                break  # Successfully read file

        except (UnicodeDecodeError, LookupError):
            continue
        except Exception as e:
            return ""

    return ' '.join(text_parts)


def detect_language(text: str, min_length: int = 50) -> Optional[str]:
    """
    Detect language of text. Returns ISO 639-1 language code or None.
    """
    if not text or len(text) < min_length:
        return None

    try:
        # Clean up text - remove chess notation artifacts
        text = re.sub(r'[!?+#=]', '', text)
        text = re.sub(r'\d+\.+', '', text)
        text = ' '.join(text.split())  # Normalize whitespace

        if len(text) < min_length:
            return None

        lang = detect(text)
        return lang
    except LangDetectException:
        return None
    except Exception as e:
        return None


def analyze_pgn_file(file_path: str) -> Tuple[str, Optional[str], int]:
    """
    Analyze a single PGN file for language.

    Returns:
        (file_path, detected_language, text_length)
    """
    text = extract_text_from_pgn(file_path)
    text_len = len(text)
    lang = detect_language(text)
    return (file_path, lang, text_len)


def find_non_english_spanish_pgns(
    root_dir: str,
    output_csv: str,
    log_every: int = 100
) -> Tuple[int, List[Tuple[str, str, int]]]:
    """
    Find all PGN files that are not in English or Spanish.

    Returns:
        (total_files, non_en_es_files)
    """
    print(f"🔍 Scanning for PGN files in: {root_dir}")

    pgn_files = []
    root_path = Path(root_dir)
    for file_path in root_path.rglob("*.pgn"):
        if file_path.is_file() and not file_path.name.startswith("._"):
            pgn_files.append(str(file_path))

    pgn_files = sorted(pgn_files)
    total_files = len(pgn_files)

    print(f"📊 Found {total_files} PGN files")
    print(f"🔍 Analyzing languages...")
    print()

    non_en_es_files = []
    language_stats = Counter()
    no_detection_count = 0

    for idx, pgn_path in enumerate(pgn_files, 1):
        if idx % log_every == 0:
            print(f"[progress] Analyzed {idx}/{total_files} files "
                  f"({len(non_en_es_files)} non-EN/ES found)")

        file_path, lang, text_len = analyze_pgn_file(pgn_path)

        if lang:
            language_stats[lang] += 1

            # Check if language is NOT English or Spanish
            if lang not in ['en', 'es']:
                non_en_es_files.append((file_path, lang, text_len))
                print(f"  🌍 Found {lang.upper()}: {Path(file_path).name}")
        else:
            no_detection_count += 1

    print()
    print(f"[progress] Analyzed {total_files}/{total_files} files "
          f"({len(non_en_es_files)} non-EN/ES found)")
    print()

    # Write results to CSV
    print(f"📋 Writing results to: {output_csv}")
    with open(output_csv, 'w', newline='', encoding='utf-8') as csv_f:
        writer = csv.writer(csv_f)
        writer.writerow(['file_path', 'detected_language', 'text_length'])
        writer.writerows(non_en_es_files)

    # Print statistics
    print()
    print("=" * 80)
    print("LANGUAGE STATISTICS")
    print("=" * 80)
    print(f"Total files analyzed: {total_files}")
    print(f"Files with detected language: {total_files - no_detection_count}")
    print(f"Files with no text/detection: {no_detection_count}")
    print()
    print("Language distribution:")
    for lang, count in language_stats.most_common():
        lang_name = {
            'en': 'English',
            'es': 'Spanish',
            'de': 'German',
            'fr': 'French',
            'pt': 'Portuguese',
            'it': 'Italian',
            'ru': 'Russian',
            'nl': 'Dutch',
            'pl': 'Polish',
            'sv': 'Swedish',
            'da': 'Danish',
            'no': 'Norwegian',
        }.get(lang, lang.upper())
        print(f"  {lang_name:20s} ({lang}): {count:4d} files")

    print()
    print("=" * 80)
    print(f"✅ Non-English/Spanish files found: {len(non_en_es_files)}")
    print("=" * 80)

    return total_files, non_en_es_files


def main():
    parser = argparse.ArgumentParser(
        description='Detect non-English/Spanish PGN files',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Example:
  python detect_pgn_languages.py \\
      --root "/Volumes/chess/1Chessable" \\
      --output "non_english_spanish_pgns.csv" \\
      --log-every 100
        """
    )

    parser.add_argument(
        '--root',
        required=True,
        help='Root directory to scan for PGN files'
    )
    parser.add_argument(
        '--output',
        required=True,
        help='Output CSV file for non-English/Spanish PGNs'
    )
    parser.add_argument(
        '--log-every',
        type=int,
        default=100,
        help='Progress logging interval (default: 100)'
    )

    args = parser.parse_args()

    print("=" * 80)
    print("PGN LANGUAGE DETECTOR")
    print("=" * 80)
    print(f"Root directory: {args.root}")
    print(f"Output CSV: {args.output}")
    print(f"Target: Find files NOT in English or Spanish")
    print("=" * 80)
    print()

    try:
        total, non_en_es = find_non_english_spanish_pgns(
            args.root,
            args.output,
            args.log_every
        )

        if non_en_es:
            print(f"\n📋 Results saved to: {args.output}")
            print(f"\nSample of non-English/Spanish files:")
            for file_path, lang, text_len in non_en_es[:5]:
                print(f"  {lang.upper():4s} - {Path(file_path).name}")

        return 0

    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
