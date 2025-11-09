#!/usr/bin/env python3
"""
Phase 5.2 Validation Framework

Validates RRF multi-collection merge performance by running test queries through:
1. EPUB-only collection (/query endpoint, but we'll use direct RAG calls)
2. PGN-only collection (/query_pgn endpoint, or direct calls)
3. RRF-merged (/query_merged endpoint, or direct calls)

Generates comprehensive metrics comparison and saves results.

IMPORTANT: This is PRELIMINARY validation with 1,778 PGN games (0.5% of final corpus).
Must re-run when PGN collection scales to 1M games (74% of final corpus).

Usage:
    # Quick test (first 10 queries)
    python phase5_validation.py --quick

    # Full test (all 50 queries)
    python phase5_validation.py

    # Specific category only
    python phase5_validation.py --category opening

    # Custom test suite file
    python phase5_validation.py --test-suite custom_suite.json
"""

import os
import sys
import json
import time
import argparse
from datetime import datetime
from typing import List, Dict, Any, Tuple

# Import our modules
from openai import OpenAI
from qdrant_client import QdrantClient
from query_system_a import embed_query, semantic_search, gpt5_rerank
from rrf_merger import merge_collections
from evaluation_metrics import calculate_all_metrics, compare_approaches, determine_winner


# ============================================================================
# CONFIGURATION
# ============================================================================

QDRANT_MODE = os.getenv('QDRANT_MODE', 'docker')
QDRANT_URL = os.getenv('QDRANT_URL', 'http://localhost:6333')
QDRANT_PATH = './qdrant_production_db'

COLLECTION_EPUB = 'chess_production'
COLLECTION_PGN = 'chess_pgn_repertoire'

TOP_K_CANDIDATES = 100  # Candidates for reranking
TOP_N_RESULTS = 10      # Final results after reranking

# Metrics configuration
K_VALUES = [5, 10]
RELEVANT_THRESHOLD = 7.0  # GPT-5 scores >=7.0 considered relevant


# ============================================================================
# QUERY EXECUTION
# ============================================================================

def execute_query_epub_only(
    openai_client: OpenAI,
    qdrant_client: QdrantClient,
    query_text: str
) -> List[Tuple[Any, float]]:
    """
    Execute query against EPUB collection only.

    Returns:
        List of (candidate, score) tuples from GPT-5 reranking
    """
    # 1. Embed query
    query_vector = embed_query(openai_client, query_text)

    # 2. Search EPUB collection
    candidates = semantic_search(
        qdrant_client,
        query_vector,
        top_k=TOP_K_CANDIDATES,
        collection_name=COLLECTION_EPUB
    )

    # 3. Rerank with GPT-5
    ranked_results = gpt5_rerank(
        openai_client,
        query_text,
        candidates,
        top_k=TOP_N_RESULTS
    )

    return ranked_results


def execute_query_pgn_only(
    openai_client: OpenAI,
    qdrant_client: QdrantClient,
    query_text: str
) -> List[Tuple[Any, float]]:
    """
    Execute query against PGN collection only.

    Returns:
        List of (candidate, score) tuples from GPT-5 reranking
    """
    # 1. Embed query
    query_vector = embed_query(openai_client, query_text)

    # 2. Search PGN collection
    candidates = semantic_search(
        qdrant_client,
        query_vector,
        top_k=TOP_K_CANDIDATES,
        collection_name=COLLECTION_PGN
    )

    # 3. Rerank with GPT-5
    ranked_results = gpt5_rerank(
        openai_client,
        query_text,
        candidates,
        top_k=TOP_N_RESULTS
    )

    return ranked_results


def execute_query_rrf_merged(
    openai_client: OpenAI,
    qdrant_client: QdrantClient,
    query_text: str
) -> List[Tuple[Any, float]]:
    """
    Execute query with RRF multi-collection merge.

    Returns:
        List of (candidate, score) tuples from GPT-5 reranking
    """
    # 1. Embed query (once, shared across both collections)
    query_vector = embed_query(openai_client, query_text)

    # 2. Search both collections
    epub_candidates = semantic_search(
        qdrant_client,
        query_vector,
        top_k=TOP_K_CANDIDATES,
        collection_name=COLLECTION_EPUB
    )

    pgn_candidates = semantic_search(
        qdrant_client,
        query_vector,
        top_k=TOP_K_CANDIDATES,
        collection_name=COLLECTION_PGN
    )

    # 3. Rerank both collections
    epub_ranked = gpt5_rerank(openai_client, query_text, epub_candidates, top_k=TOP_K_CANDIDATES)
    pgn_ranked = gpt5_rerank(openai_client, query_text, pgn_candidates, top_k=TOP_K_CANDIDATES)

    # 4. Merge with RRF
    merged_results = merge_collections(
        epub_results=epub_ranked,
        pgn_results=pgn_ranked,
        top_n=TOP_N_RESULTS,
        k=60,  # RRF k-parameter
        weights={'epub': 1.0, 'pgn': 1.0}  # Equal weights for now
    )

    # Convert merged results to (candidate, score) tuples
    # Use max_similarity (GPT-5 reranking score) as the score
    ranked_tuples = []
    for merged_item in merged_results:
        # merged_item has the candidate and metadata
        # We need to extract the candidate object and use max_similarity as score
        candidate = merged_item  # The merged result contains all the original data
        score = merged_item.get('max_similarity', 0.0)
        ranked_tuples.append((candidate, score))

    return ranked_tuples


# ============================================================================
# RESULTS FORMATTING
# ============================================================================

def format_results_for_metrics(ranked_results: List[Tuple[Any, float]]) -> List[Dict[str, Any]]:
    """
    Convert ranked results to format expected by evaluation metrics.

    Args:
        ranked_results: List of (candidate, score) tuples

    Returns:
        List of {'score': float} dictionaries for metrics calculation
    """
    formatted = []
    for candidate, score in ranked_results:
        formatted.append({'score': score})
    return formatted


# ============================================================================
# VALIDATION EXECUTION
# ============================================================================

def run_validation(
    test_suite: Dict[str, Any],
    openai_client: OpenAI,
    qdrant_client: QdrantClient,
    quick_mode: bool = False,
    category_filter: str = None
) -> Dict[str, Any]:
    """
    Run validation across all test queries.

    Args:
        test_suite: Loaded test suite JSON
        openai_client: OpenAI client instance
        qdrant_client: Qdrant client instance
        quick_mode: If True, only run first 10 queries
        category_filter: If set, only run queries from this category

    Returns:
        Validation results dictionary
    """
    queries = test_suite['queries']

    # Apply filters
    if category_filter:
        queries = [q for q in queries if q['category'] == category_filter]
        print(f"📂 Filtering to category: {category_filter} ({len(queries)} queries)")

    if quick_mode:
        queries = queries[:10]
        print(f"⚡ Quick mode: Testing first {len(queries)} queries")

    print(f"🧪 Running validation on {len(queries)} queries...")
    print(f"   Approaches: EPUB-only, PGN-only, RRF-merged")
    print(f"   Metrics: MRR, NDCG@5, NDCG@10, Precision@5/10")
    print()

    results = {
        'metadata': {
            'timestamp': datetime.now().isoformat(),
            'corpus_state': test_suite['metadata']['corpus_state'],
            'total_queries_run': len(queries),
            'quick_mode': quick_mode,
            'category_filter': category_filter
        },
        'query_results': [],
        'aggregate_metrics': {
            'epub': {},
            'pgn': {},
            'rrf': {}
        },
        'category_breakdown': {}
    }

    # Run each query through all 3 approaches
    for idx, query_data in enumerate(queries, start=1):
        query_id = query_data['id']
        query_text = query_data['query']
        category = query_data['category']
        expected_best = query_data['expected_best']

        print(f"[{idx}/{len(queries)}] Query #{query_id}: \"{query_text}\"")
        print(f"            Category: {category}, Expected best: {expected_best}")

        query_result = {
            'id': query_id,
            'query': query_text,
            'category': category,
            'expected_best': expected_best,
            'timing': {},
            'metrics': {},
            'winner': None
        }

        try:
            # EPUB-only
            print(f"            Running EPUB-only...")
            start = time.time()
            epub_ranked = execute_query_epub_only(openai_client, qdrant_client, query_text)
            epub_results = format_results_for_metrics(epub_ranked)
            query_result['timing']['epub'] = round(time.time() - start, 2)
            query_result['metrics']['epub'] = calculate_all_metrics(epub_results, K_VALUES, RELEVANT_THRESHOLD)
            print(f"               ✓ EPUB: {query_result['timing']['epub']}s, NDCG@10={query_result['metrics']['epub']['ndcg@10']:.3f}")

            # PGN-only
            print(f"            Running PGN-only...")
            start = time.time()
            pgn_ranked = execute_query_pgn_only(openai_client, qdrant_client, query_text)
            pgn_results = format_results_for_metrics(pgn_ranked)
            query_result['timing']['pgn'] = round(time.time() - start, 2)
            query_result['metrics']['pgn'] = calculate_all_metrics(pgn_results, K_VALUES, RELEVANT_THRESHOLD)
            print(f"               ✓ PGN: {query_result['timing']['pgn']}s, NDCG@10={query_result['metrics']['pgn']['ndcg@10']:.3f}")

            # RRF-merged
            print(f"            Running RRF-merged...")
            start = time.time()
            rrf_ranked = execute_query_rrf_merged(openai_client, qdrant_client, query_text)
            rrf_results = format_results_for_metrics(rrf_ranked)
            query_result['timing']['rrf'] = round(time.time() - start, 2)
            query_result['metrics']['rrf'] = calculate_all_metrics(rrf_results, K_VALUES, RELEVANT_THRESHOLD)
            print(f"               ✓ RRF: {query_result['timing']['rrf']}s, NDCG@10={query_result['metrics']['rrf']['ndcg@10']:.3f}")

            # Determine winner
            query_result['winner'] = determine_winner(
                query_result['metrics']['epub'],
                query_result['metrics']['pgn'],
                query_result['metrics']['rrf'],
                primary_metric='ndcg@10'
            )
            print(f"            🏆 Winner: {query_result['winner'].upper()}")

        except Exception as e:
            print(f"            ❌ Error: {e}")
            query_result['error'] = str(e)

        results['query_results'].append(query_result)
        print()

    # Calculate aggregate metrics
    print("📊 Calculating aggregate metrics...")
    aggregate_metrics_per_approach(results)
    print()

    return results


def aggregate_metrics_per_approach(results: Dict[str, Any]):
    """
    Calculate average metrics across all queries for each approach.

    Modifies results dictionary in-place to add aggregate metrics.
    """
    query_results = results['query_results']

    # Initialize accumulators
    metrics_sum = {
        'epub': {},
        'pgn': {},
        'rrf': {}
    }

    # Sum up metrics across all queries
    for query_result in query_results:
        if 'error' in query_result:
            continue

        for approach in ['epub', 'pgn', 'rrf']:
            for metric_name, metric_value in query_result['metrics'][approach].items():
                if metric_name not in metrics_sum[approach]:
                    metrics_sum[approach][metric_name] = 0.0
                metrics_sum[approach][metric_name] += metric_value

    # Calculate averages
    num_queries = len([q for q in query_results if 'error' not in q])

    for approach in ['epub', 'pgn', 'rrf']:
        results['aggregate_metrics'][approach] = {
            metric_name: round(total_value / num_queries, 4)
            for metric_name, total_value in metrics_sum[approach].items()
        }


# ============================================================================
# RESULTS DISPLAY
# ============================================================================

def print_summary(results: Dict[str, Any]):
    """
    Print validation summary to console.
    """
    print("=" * 80)
    print("PHASE 5.2 VALIDATION SUMMARY")
    print("=" * 80)
    print()

    # Metadata
    print(f"Timestamp: {results['metadata']['timestamp']}")
    print(f"Corpus State: {results['metadata']['corpus_state']}")
    print(f"Total Queries: {results['metadata']['total_queries_run']}")
    if results['metadata']['quick_mode']:
        print("Mode: QUICK (first 10 queries only)")
    if results['metadata']['category_filter']:
        print(f"Category Filter: {results['metadata']['category_filter']}")
    print()

    # Aggregate metrics
    print("Aggregate Metrics (averaged across all queries):")
    print()
    print(f"{'Metric':<15} {'EPUB-only':<12} {'PGN-only':<12} {'RRF-merged':<12} {'Winner':<10}")
    print("-" * 80)

    epub_metrics = results['aggregate_metrics']['epub']
    pgn_metrics = results['aggregate_metrics']['pgn']
    rrf_metrics = results['aggregate_metrics']['rrf']

    for metric_name in ['mrr', 'ndcg@5', 'ndcg@10', 'precision@5', 'precision@10']:
        epub_val = epub_metrics.get(metric_name, 0.0)
        pgn_val = pgn_metrics.get(metric_name, 0.0)
        rrf_val = rrf_metrics.get(metric_name, 0.0)

        # Determine winner for this metric
        winner = max(
            [('EPUB', epub_val), ('PGN', pgn_val), ('RRF', rrf_val)],
            key=lambda x: x[1]
        )[0]

        print(f"{metric_name:<15} {epub_val:<12.4f} {pgn_val:<12.4f} {rrf_val:<12.4f} {winner:<10}")

    print()

    # Per-query winner breakdown
    winners_count = {'epub': 0, 'pgn': 0, 'rrf': 0}
    for query_result in results['query_results']:
        if 'winner' in query_result:
            winners_count[query_result['winner']] += 1

    print("Per-Query Winners (based on NDCG@10):")
    total = sum(winners_count.values())
    for approach, count in winners_count.items():
        percentage = (count / total * 100) if total > 0 else 0
        print(f"  {approach.upper()}: {count}/{total} ({percentage:.1f}%)")
    print()

    print("=" * 80)


def save_results(results: Dict[str, Any], output_file: str = "validation_results.json"):
    """
    Save validation results to JSON file.
    """
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"💾 Results saved to: {output_file}")


# ============================================================================
# MAIN
# ============================================================================

def main():
    parser = argparse.ArgumentParser(description="Phase 5.2 RRF Validation")
    parser.add_argument('--test-suite', default='validation_test_suite.json', help='Test suite JSON file')
    parser.add_argument('--quick', action='store_true', help='Quick mode: only first 10 queries')
    parser.add_argument('--category', choices=['opening', 'concept', 'mixed'], help='Filter to specific category')
    parser.add_argument('--output', default='validation_results.json', help='Output JSON file')

    args = parser.parse_args()

    # Load test suite
    print(f"📖 Loading test suite: {args.test_suite}")
    with open(args.test_suite, 'r') as f:
        test_suite = json.load(f)
    print(f"   Loaded {len(test_suite['queries'])} queries")
    print()

    # Initialize clients
    print("🔧 Initializing OpenAI and Qdrant clients...")
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        print("❌ Error: OPENAI_API_KEY environment variable not set!")
        sys.exit(1)

    openai_client = OpenAI(api_key=api_key)

    if QDRANT_MODE == 'docker':
        qdrant_client = QdrantClient(url=QDRANT_URL)
        print(f"   Using Docker Qdrant at {QDRANT_URL}")
    else:
        qdrant_client = QdrantClient(path=QDRANT_PATH)
        print(f"   Using local Qdrant at {QDRANT_PATH}")
    print()

    # Run validation
    results = run_validation(
        test_suite,
        openai_client,
        qdrant_client,
        quick_mode=args.quick,
        category_filter=args.category
    )

    # Print summary
    print_summary(results)

    # Save results
    save_results(results, args.output)


if __name__ == '__main__':
    main()
