#!/usr/bin/env python3
"""
Fast EPUB Analyzer for Chess Books
Performance target: 1-2 seconds per book
Based on 3 AI partner consensus (Gemini, ChatGPT, Grok)
"""

import sys
import re
import time
import shutil
from pathlib import Path
from typing import Tuple, Optional, Dict
import ebooklib
from ebooklib import epub
from bs4 import BeautifulSoup
import mobi


# Known high-quality chess authors
RENOWNED_AUTHORS = {
    'aagaard', 'dvoretsky', 'silman', 'kasparov', 'karpov', 'seirawan',
    'nunn', 'watson', 'lakdawala', 'kotronias', 'marin', 'grivas',
    'gelfand', 'smyslov', 'reshevsky', 'bronstein', 'botvinnik',
    'tal', 'petrosian', 'timman', 'polgar', 'kramnik', 'anand',
    'shirov', 'giri', 'caruana', 'nakamura', 'So', 'kaufman',
    'avrukh', 'schandorff', 'negi', 'bologan', 'mikhalchishin'
}

# Instructional keywords (weighted)
INSTRUCTIONAL_KEYWORDS = {
    # High value (3 points each)
    'strategy': 3, 'tactics': 3, 'principle': 3, 'exercise': 3,
    'technique': 3, 'concept': 3, 'lesson': 3, 'training': 3,

    # Medium value (2 points each)
    'practice': 2, 'study': 2, 'understand': 2, 'learn': 2,
    'improve': 2, 'master': 2, 'guide': 2, 'explain': 2,
    'analyze': 2, 'demonstrate': 2, 'illustrate': 2,

    # Low value (1 point each)
    'example': 1, 'position': 1, 'move': 1, 'plan': 1,
    'attack': 1, 'defense': 1, 'endgame': 1, 'opening': 1,
    'middlegame': 1, 'variation': 1
}


def extract_mobi_text_and_html(mobi_path: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """
    Extract text and HTML from MOBI.

    Returns:
        tuple: (text, html, error_message)
    """
    try:
        # Extract MOBI to temporary directory
        tempdir, filepath = mobi.extract(mobi_path)

        # Read the HTML content
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            html = f.read()

        # Parse with BeautifulSoup
        soup = BeautifulSoup(html, 'html.parser')
        text = soup.get_text(separator='\n', strip=True)

        # Cleanup temp directory
        shutil.rmtree(tempdir)

        if not text:
            return None, None, "No text content found in MOBI"

        return text, html, None

    except Exception as e:
        return None, None, f"MOBI extraction error: {str(e)}"


def extract_epub_text_and_html(epub_path: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """
    Extract text and HTML from EPUB.

    Returns:
        tuple: (text, html, error_message)
    """
    try:
        book = epub.read_epub(epub_path)

        chapters_text = []
        chapters_html = []

        for item in book.get_items():
            if item.get_type() == ebooklib.ITEM_DOCUMENT:
                html_content = item.get_content()
                soup = BeautifulSoup(html_content, 'html.parser')

                # Keep HTML for structure analysis
                chapters_html.append(str(html_content))

                # Extract text
                text = soup.get_text(separator='\n', strip=True)
                if text:
                    chapters_text.append(text)

        if not chapters_text:
            return None, None, "No text content found in EPUB"

        full_text = '\n\n'.join(chapters_text)
        full_html = '\n\n'.join(chapters_html)

        return full_text, full_html, None

    except Exception as e:
        return None, None, f"EPUB extraction error: {str(e)}"


def extract_ebook_text_and_html(ebook_path: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """
    Universal ebook extractor - supports both EPUB and MOBI.

    Returns:
        tuple: (text, html, error_message)
    """
    file_ext = Path(ebook_path).suffix.lower()

    if file_ext == '.epub':
        return extract_epub_text_and_html(ebook_path)
    elif file_ext == '.mobi':
        return extract_mobi_text_and_html(ebook_path)
    else:
        return None, None, f"Unsupported format: {file_ext}"


def count_chess_notation(text: str) -> int:
    """Count chess moves in algebraic notation."""
    # Pattern for chess moves: 1. e4, Nf3, Bxc6+, O-O, etc.
    patterns = [
        r'\b[KQRBN]?[a-h]?[1-8]?x?[a-h][1-8][+#]?\b',  # Standard moves
        r'\bO-O(-O)?\b',  # Castling
        r'\b\d+\.\s*[a-zA-Z]',  # Move numbers with moves
    ]

    total = 0
    for pattern in patterns:
        total += len(re.findall(pattern, text))

    return total


def calculate_prose_to_notation_ratio(text: str, notation_count: int) -> Tuple[float, int]:
    """
    Calculate prose-to-notation ratio.
    Returns: (score 0-20, ratio_percentage)
    """
    word_count = len(text.split())

    if word_count == 0:
        return 0, 0

    # Ratio: notation / total_words
    ratio = (notation_count / word_count) * 100

    # Optimal range: 5-20% notation
    # Too low (<2%): pure prose, not chess-focused
    # Too high (>40%): database dump
    # Sweet spot: 5-20% = instructional with analysis

    if ratio < 2:
        score = 5  # Too little chess content
    elif 2 <= ratio < 5:
        score = 10 + (ratio - 2) * 2  # Gradually better
    elif 5 <= ratio <= 20:
        score = 20  # Perfect range
    elif 20 < ratio <= 30:
        score = 15  # Good but heavy on moves
    elif 30 < ratio <= 40:
        score = 10  # Getting too notation-heavy
    else:
        score = 5  # Database dump territory

    return score, int(ratio)


def calculate_word_count_score(word_count: int) -> int:
    """
    Score based on word count quality (0-15 points).
    Optimal: 20K-100K words
    """
    if word_count < 5000:
        return 3  # Too short
    elif 5000 <= word_count < 10000:
        return 6
    elif 10000 <= word_count < 20000:
        return 10
    elif 20000 <= word_count <= 100000:
        return 15  # Perfect range
    elif 100000 < word_count <= 150000:
        return 12  # Long but acceptable
    else:
        return 8  # Too long, may be database


def count_diagrams(html: str) -> int:
    """Count chess diagram images."""
    # Count <img> tags
    return len(re.findall(r'<img[^>]*>', html, re.IGNORECASE))


def calculate_diagram_score(diagram_count: int, word_count: int) -> int:
    """
    Score based on diagram density (0-10 points).
    Optimal: 1 diagram per 500-1000 words
    """
    if word_count == 0:
        return 0

    # Diagrams per 1000 words
    density = (diagram_count / word_count) * 1000

    if density < 0.5:
        return 3  # Too few diagrams
    elif 0.5 <= density < 1:
        return 6
    elif 1 <= density <= 3:
        return 10  # Perfect range
    elif 3 < density <= 5:
        return 7
    else:
        return 4  # Too many diagrams


def analyze_structure(text: str, html: str) -> Tuple[int, Dict[str, int]]:
    """
    Analyze document structure (0-15 points).
    Returns: (score, stats_dict)
    """
    stats = {}

    # Count headings
    h1_count = len(re.findall(r'<h1[^>]*>', html, re.IGNORECASE))
    h2_count = len(re.findall(r'<h2[^>]*>', html, re.IGNORECASE))
    h3_count = len(re.findall(r'<h3[^>]*>', html, re.IGNORECASE))

    stats['h1_count'] = h1_count
    stats['h2_count'] = h2_count
    stats['h3_count'] = h3_count

    # Detect TOC (Table of Contents)
    toc_patterns = [
        r'\bcontents?\b',
        r'\bchapter\s+\d+',
        r'\bpart\s+\d+',
        r'\bsection\s+\d+'
    ]

    toc_score = 0
    for pattern in toc_patterns:
        if re.search(pattern, text[:5000], re.IGNORECASE):
            toc_score += 2
            break

    stats['has_toc'] = toc_score > 0

    # Calculate structure score
    score = 0

    # Points for TOC
    score += min(toc_score, 4)

    # Points for heading hierarchy
    if h1_count > 0:
        score += 3
    if h2_count >= 5:
        score += 4
    elif h2_count >= 2:
        score += 2

    if h3_count >= 10:
        score += 4
    elif h3_count >= 3:
        score += 2

    return min(score, 15), stats


def calculate_instructional_score(text: str) -> Tuple[int, Dict[str, int]]:
    """
    Score based on instructional keywords (0-15 points).
    Returns: (score, keyword_counts)
    """
    text_lower = text.lower()

    keyword_hits = {}
    total_weight = 0

    for keyword, weight in INSTRUCTIONAL_KEYWORDS.items():
        count = len(re.findall(r'\b' + re.escape(keyword) + r'\b', text_lower))
        if count > 0:
            keyword_hits[keyword] = count
            total_weight += min(count * weight, weight * 10)  # Cap per keyword

    # Normalize to 0-15 scale
    # Target: ~100 weighted hits for max score
    score = min(int((total_weight / 100) * 15), 15)

    return score, keyword_hits


def check_author_reputation(filename: str) -> int:
    """
    Check if filename contains renowned author (0-10 points).
    """
    filename_lower = filename.lower()

    for author in RENOWNED_AUTHORS:
        if author in filename_lower:
            return 10

    return 0


def calculate_text_quality_score(text: str) -> int:
    """
    Basic text quality heuristics (0-15 points).
    """
    score = 0

    # Average word length (good English prose: 4-6 chars)
    words = text.split()
    if words:
        avg_word_len = sum(len(w) for w in words) / len(words)
        if 4 <= avg_word_len <= 6:
            score += 5
        elif 3 <= avg_word_len < 4 or 6 < avg_word_len <= 7:
            score += 3

    # Sentence structure (periods, questions, exclamations)
    sentences = len(re.findall(r'[.!?]', text))
    if sentences > 0:
        words_per_sentence = len(words) / sentences
        if 10 <= words_per_sentence <= 25:
            score += 5  # Good sentence length
        elif 8 <= words_per_sentence < 10 or 25 < words_per_sentence <= 30:
            score += 3

    # Paragraph structure (newlines)
    paragraphs = len(re.findall(r'\n\n+', text))
    if paragraphs > 10:
        score += 5
    elif paragraphs > 5:
        score += 3

    return min(score, 15)


def analyze_epub_fast(epub_path: str, verbose: bool = True) -> Dict:
    """
    Fast EPUB analysis with 6 core metrics.
    Target: <2 seconds per book
    """
    start_time = time.time()

    if verbose:
        print(f"\n{'='*80}")
        print(f"📖 Analyzing: {Path(epub_path).name}")
        print(f"{'='*80}\n")

    # Extract text and HTML (supports both EPUB and MOBI)
    text, html, error = extract_ebook_text_and_html(epub_path)

    if error:
        return {
            'success': False,
            'error': error,
            'file': epub_path,
            'processing_time': time.time() - start_time
        }

    # Basic stats
    word_count = len(text.split())
    char_count = len(text)

    if verbose:
        print(f"📊 Basic Stats:")
        print(f"   Words: {word_count:,}")
        print(f"   Characters: {char_count:,}\n")

    # Metric 1: Prose-to-notation ratio (20 pts)
    notation_count = count_chess_notation(text)
    prose_notation_score, notation_ratio = calculate_prose_to_notation_ratio(text, notation_count)

    # Metric 2: Word count quality (15 pts)
    word_count_score = calculate_word_count_score(word_count)

    # Metric 3: Diagram count (10 pts)
    diagram_count = count_diagrams(html)
    diagram_score = calculate_diagram_score(diagram_count, word_count)

    # Metric 4: Structure (15 pts)
    structure_score, structure_stats = analyze_structure(text, html)

    # Metric 5: Instructional keywords (15 pts)
    instructional_score, keyword_hits = calculate_instructional_score(text)

    # Metric 6: Author reputation (10 pts)
    author_score = check_author_reputation(Path(epub_path).name)

    # Metric 7: Text quality (15 pts)
    text_quality_score = calculate_text_quality_score(text)

    # Calculate total score
    total_score = (
        prose_notation_score +
        word_count_score +
        diagram_score +
        structure_score +
        instructional_score +
        author_score +
        text_quality_score
    )

    # Determine tier
    if total_score >= 70:
        tier = "HIGH"
    elif total_score >= 45:
        tier = "MEDIUM"
    else:
        tier = "LOW"

    processing_time = time.time() - start_time

    # Display results
    if verbose:
        print(f"⚡ Score Breakdown (Total: {total_score}/100):")
        print(f"   1. Prose-to-Notation Ratio:  {prose_notation_score:2d}/20  (ratio: {notation_ratio}%)")
        print(f"   2. Word Count Quality:       {word_count_score:2d}/15  ({word_count:,} words)")
        print(f"   3. Diagram Quality:          {diagram_score:2d}/10  ({diagram_count} diagrams)")
        print(f"   4. Structure:                {structure_score:2d}/15  (H1:{structure_stats['h1_count']}, H2:{structure_stats['h2_count']}, TOC:{structure_stats['has_toc']})")
        print(f"   5. Instructional Keywords:   {instructional_score:2d}/15  ({len(keyword_hits)} unique)")
        print(f"   6. Author Reputation:        {author_score:2d}/10")
        print(f"   7. Text Quality:             {text_quality_score:2d}/15\n")

        print(f"🎯 Final Score: {total_score}/100")
        print(f"📊 Tier: {tier}")
        print(f"⏱️  Processing Time: {processing_time:.2f} seconds\n")

        if keyword_hits:
            top_keywords = sorted(keyword_hits.items(), key=lambda x: x[1], reverse=True)[:5]
            print(f"🔑 Top Instructional Keywords:")
            for keyword, count in top_keywords:
                print(f"   - {keyword}: {count}")
            print()

    return {
        'success': True,
        'file': epub_path,
        'total_score': total_score,
        'tier': tier,
        'processing_time': processing_time,
        'metrics': {
            'prose_notation_score': prose_notation_score,
            'notation_ratio': notation_ratio,
            'word_count_score': word_count_score,
            'word_count': word_count,
            'diagram_score': diagram_score,
            'diagram_count': diagram_count,
            'structure_score': structure_score,
            'structure_stats': structure_stats,
            'instructional_score': instructional_score,
            'keyword_hits': keyword_hits,
            'author_score': author_score,
            'text_quality_score': text_quality_score
        }
    }


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python analyze_chess_books.py <book_file1> [book_file2] ...")
        print("\nSupports: .epub and .mobi files")
        print("\nExample:")
        print('  python analyze_chess_books.py "/Volumes/T7 Shield/epub/aagaard*.epub"')
        print('  python analyze_chess_books.py "/path/to/book.mobi"')
        sys.exit(1)

    results = []
    for epub_path in sys.argv[1:]:
        result = analyze_epub_fast(epub_path, verbose=True)
        results.append(result)

    # Summary for multiple files
    if len(results) > 1:
        print(f"\n{'='*80}")
        print("SUMMARY")
        print(f"{'='*80}\n")

        successful = [r for r in results if r['success']]
        failed = [r for r in results if not r['success']]

        print(f"✅ Successfully analyzed: {len(successful)}")
        print(f"❌ Failed: {len(failed)}")
        print(f"⏱️  Average processing time: {sum(r['processing_time'] for r in successful) / len(successful):.2f}s\n")

        if successful:
            print("Scores by Tier:")
            for tier in ['HIGH', 'MEDIUM', 'LOW']:
                tier_results = [r for r in successful if r['tier'] == tier]
                if tier_results:
                    print(f"\n{tier} ({len(tier_results)} books):")
                    for r in sorted(tier_results, key=lambda x: x['total_score'], reverse=True):
                        filename = Path(r['file']).name[:60]
                        print(f"  {r['total_score']:3d} - {filename}")


if __name__ == '__main__':
    main()
