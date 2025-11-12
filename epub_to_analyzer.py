#!/usr/bin/env python3
"""
EPUB → Chess RAG System Analyzer Bridge
Extracts text from EPUB files and analyzes them using chess_rag_system components.
"""

import sys
from pathlib import Path
from typing import Tuple, Optional, List, Dict
import ebooklib
from ebooklib import epub
from bs4 import BeautifulSoup

# Import chess_rag_system components
from chess_rag_system.analysis.instructional_detector import InstructionalLanguageDetector, detect_instructional
from chess_rag_system.analysis.semantic_analyzer import ChessSemanticAnalyzer
from chess_rag_system.scoring.rag_evaluator import RAGFitnessEvaluator
from chess_rag_system.core.models import SemanticAnalysisResult, RAGFitnessResult


def extract_epub_sections(epub_path: str) -> Tuple[List[Dict], Optional[str]]:
    """
    Extract structured sections (text + headings) from an EPUB.

    Returns:
        tuple: (sections, error_message)
        sections is a list of dicts with text, chapter_title, section_path, html_document
    """
    try:
        book = epub.read_epub(epub_path)
        sections: List[Dict] = []

        for item in book.get_items():
            if item.get_type() != ebooklib.ITEM_DOCUMENT:
                continue

            try:
                content = item.get_content().decode('utf-8', errors='ignore')
            except Exception:
                content = item.get_content()

            soup = BeautifulSoup(content, 'html.parser')
            text = soup.get_text(separator='\n', strip=True)
            if not text:
                continue

            heading = None
            for level in ['h1', 'h2', 'h3', 'h4']:
                tag = soup.find(level)
                if tag:
                    heading = tag.get_text(" ", strip=True)
                    break

            if not heading:
                first_para = soup.find('p')
                if first_para and first_para.get_text(strip=True):
                    heading = first_para.get_text(" ", strip=True)[:120]

            if not heading:
                heading = Path(item.get_name()).stem.replace('_', ' ').title()

            sections.append({
                'text': text,
                'chapter_title': heading[:200],
                'section_path': heading[:200],
                'html_document': item.get_name()
            })

        if not sections:
            return [], "No text content found in EPUB"

        return sections, None

    except FileNotFoundError:
        return [], f"File not found: {epub_path}"
    except Exception as e:
        return [], f"EPUB extraction error: {str(e)}"


def extract_epub_text(epub_path: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Extract text from EPUB using ebooklib + BeautifulSoup4.

    Args:
        epub_path: Path to the EPUB file

    Returns:
        tuple: (text, error_message)
        - text is None if extraction failed
        - error_message explains why extraction failed
    """
    try:
        sections, error = extract_epub_sections(epub_path)
        if error:
            return None, error

        full_text = '\n\n'.join(section['text'] for section in sections)

        # Basic quality check
        word_count = len(full_text.split())
        if word_count < 500:
            return None, f"Insufficient text: {word_count} words"

        return full_text, None

    except FileNotFoundError:
        return None, f"File not found: {epub_path}"
    except Exception as e:
        return None, f"EPUB extraction error: {str(e)}"


def analyze_epub(epub_path: str, verbose: bool = True, max_chars: int = 50000) -> dict:
    """
    Analyze an EPUB file using chess_rag_system components.

    Args:
        epub_path: Path to the EPUB file
        verbose: Print detailed output
        max_chars: Maximum characters to analyze (default 50000 for performance)

    Returns:
        dict with analysis results
    """
    if verbose:
        print(f"\n{'='*80}")
        print(f"Analyzing: {Path(epub_path).name}")
        print(f"{'='*80}\n")

    # Extract text
    text, error = extract_epub_text(epub_path)

    if error:
        return {
            'success': False,
            'error': error,
            'file': epub_path
        }

    # Limit text size for performance
    full_text_length = len(text)
    if len(text) > max_chars:
        text = text[:max_chars]
        if verbose:
            print(f"⚠️  Text truncated to {max_chars:,} characters for performance\n")

    # Show text sample
    if verbose:
        print("📄 Text Sample (first 300 chars):")
        print(f"{text[:300]}...\n")
        print(f"📊 Full text length: {full_text_length:,} characters")
        print(f"📊 Analyzing: {len(text):,} characters")
        print(f"📊 Word count: {len(text.split()):,} words\n")

    # Initialize analyzers
    instructional_detector = InstructionalLanguageDetector()
    semantic_analyzer = ChessSemanticAnalyzer()
    rag_evaluator = RAGFitnessEvaluator()

    # Get filename for context
    filename = Path(epub_path).name

    try:
        # Run instructional detection
        if verbose:
            print("🔄 Running instructional detection...")
        is_instructional = detect_instructional(text)
        instructional_result = instructional_detector.analyze(text)
        if verbose:
            print("   ✓ Instructional detection complete\n")

        # Run semantic analysis
        if verbose:
            print("🔄 Running semantic analysis...")
        semantic_result = semantic_analyzer.analyze(
            text=text,
            filename=filename
        )
        if verbose:
            print("   ✓ Semantic analysis complete\n")

        # Run RAG fitness evaluation (EVS scoring)
        if verbose:
            print("🔄 Running RAG fitness evaluation...")
        rag_result = rag_evaluator.evaluate_rag_fitness(
            text=text,
            title=filename,
            semantic_result=semantic_result
        )
        if verbose:
            print("   ✓ RAG fitness evaluation complete\n")

        # Display results
        if verbose:
            print("🎯 EVS Score (Educational Value Score):")
            print(f"   Overall RAG Fitness: {rag_result.overall_rag_fitness:.2f}/100")
            print(f"   EVS Score: {rag_result.evs_score:.2f}/100")
            print(f"   PGN Game Type: {rag_result.pgn_game_type}\n")

            print("📚 Component Scores:")
            print(f"   Chunkability: {rag_result.chunkability_score:.2f}")
            print(f"   Answerability: {rag_result.answerability_score:.2f}")
            print(f"   Factual Density: {rag_result.factual_density_score:.2f}")
            print(f"   Retrieval Friendliness: {rag_result.retrieval_friendliness_score:.2f}\n")

            print("🔍 Semantic Analysis:")
            print(f"   Content Quality: {semantic_result.content_quality_score:.2f}")
            print(f"   Chess Domain Relevance: {semantic_result.chess_domain_relevance:.2f}")
            print(f"   Instructional Value: {semantic_result.instructional_value:.2f}")
            print(f"   Concept Density: {semantic_result.concept_density:.2f}\n")

            print("📖 Instructional Vocabulary:")
            print(f"   Total Hits: {instructional_result.get('total_hits', 0)}")
            if 'category_hits' in instructional_result:
                print(f"   Category Breakdown:")
                for cat, count in sorted(
                    instructional_result['category_hits'].items(),
                    key=lambda x: x[1],
                    reverse=True
                )[:5]:  # Top 5 categories
                    print(f"      {cat}: {count}")
            print()

            if semantic_result.top_concepts:
                print(f"🎓 Top Concepts Detected:")
                for concept in semantic_result.top_concepts[:10]:
                    print(f"   - {concept}")
                print()

            print(f"💡 Fitness Reasoning: {rag_result.fitness_reasoning}\n")

        return {
            'success': True,
            'file': epub_path,
            'evs_score': rag_result.evs_score,
            'rag_fitness': rag_result.overall_rag_fitness,
            'instructional_hits': instructional_result.get('total_hits', 0),
            'instructional_result': instructional_result,
            'semantic_result': semantic_result,
            'rag_result': rag_result,
            'text_length': len(text),
            'word_count': len(text.split())
        }

    except Exception as e:
        return {
            'success': False,
            'error': f"Analysis error: {str(e)}",
            'file': epub_path
        }


def main():
    """Main entry point for command-line usage."""
    if len(sys.argv) < 2:
        print("Usage: python epub_to_analyzer.py <epub_file1> [epub_file2] ...")
        print("\nExample:")
        print('  python epub_to_analyzer.py "/Volumes/T7 Shield/epub/aagaard_2014_*.epub"')
        sys.exit(1)

    results = []
    for epub_path in sys.argv[1:]:
        result = analyze_epub(epub_path, verbose=True)
        results.append(result)

    # Summary
    if len(results) > 1:
        print(f"\n{'='*80}")
        print("SUMMARY")
        print(f"{'='*80}\n")

        successful = [r for r in results if r['success']]
        failed = [r for r in results if not r['success']]

        print(f"✅ Successfully analyzed: {len(successful)}")
        print(f"❌ Failed: {len(failed)}\n")

        if successful:
            print("EVS Scores:")
            for r in sorted(successful, key=lambda x: x['evs_score'], reverse=True):
                filename = Path(r['file']).name
                print(f"  {r['evs_score']:5.1f} - {filename}")


if __name__ == '__main__':
    main()
