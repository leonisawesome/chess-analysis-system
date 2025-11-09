"""
Evaluation Metrics Module

Implements standard Information Retrieval metrics for validating RAG system performance:
- MRR (Mean Reciprocal Rank)
- NDCG (Normalized Discounted Cumulative Gain)
- Precision@K
- Recall@K
- F1@K

Used for Phase 5.2 validation of RRF multi-collection merge.
"""

import math
from typing import List, Dict, Any, Optional


def mean_reciprocal_rank(results: List[Dict[str, Any]], relevant_threshold: float = 7.0) -> float:
    """
    Calculate Mean Reciprocal Rank (MRR).

    MRR = 1 / rank of first relevant result

    Args:
        results: List of ranked results with 'score' field (GPT-5 relevance 0-10)
        relevant_threshold: Minimum score to consider result relevant (default: 7.0)

    Returns:
        MRR score (0.0-1.0)
        - 1.0: First result is relevant
        - 0.5: Second result is first relevant
        - 0.0: No relevant results found

    Example:
        results = [{'score': 5.0}, {'score': 8.5}, {'score': 9.0}]
        mrr = mean_reciprocal_rank(results, relevant_threshold=7.0)
        # Returns 0.5 (second result is first relevant, rank=2, 1/2=0.5)
    """
    for rank, result in enumerate(results, start=1):
        score = result.get('score', 0.0)
        if score >= relevant_threshold:
            return 1.0 / rank

    return 0.0  # No relevant results found


def dcg_at_k(results: List[Dict[str, Any]], k: int = 10) -> float:
    """
    Calculate Discounted Cumulative Gain (DCG) at position k.

    DCG@k = Σ (rel_i / log2(i+1)) for i=1 to k

    Uses GPT-5 relevance scores (0-10) as relevance values.

    Args:
        results: List of ranked results with 'score' field
        k: Number of top results to consider (default: 10)

    Returns:
        DCG score (higher is better)
    """
    dcg = 0.0
    for i, result in enumerate(results[:k], start=1):
        relevance = result.get('score', 0.0)
        dcg += relevance / math.log2(i + 1)

    return dcg


def ndcg_at_k(results: List[Dict[str, Any]], k: int = 10) -> float:
    """
    Calculate Normalized Discounted Cumulative Gain (NDCG) at position k.

    NDCG@k = DCG@k / IDCG@k

    IDCG (Ideal DCG) is DCG of perfectly ranked results (sorted by relevance).

    Args:
        results: List of ranked results with 'score' field
        k: Number of top results to consider (default: 10)

    Returns:
        NDCG score (0.0-1.0)
        - 1.0: Perfect ranking
        - 0.0: Worst possible ranking

    Example:
        results = [{'score': 9.0}, {'score': 8.5}, {'score': 7.0}]
        ndcg = ndcg_at_k(results, k=3)
        # Returns 1.0 (already perfectly ranked)
    """
    # Calculate DCG for actual ranking
    actual_dcg = dcg_at_k(results, k)

    # Calculate IDCG (ideal ranking - sorted by score descending)
    ideal_results = sorted(results[:k], key=lambda x: x.get('score', 0.0), reverse=True)
    ideal_dcg = dcg_at_k(ideal_results, k)

    # Normalize
    if ideal_dcg == 0.0:
        return 0.0

    return actual_dcg / ideal_dcg


def precision_at_k(results: List[Dict[str, Any]], k: int = 5, relevant_threshold: float = 7.0) -> float:
    """
    Calculate Precision@K.

    Precision@K = (# relevant results in top K) / K

    Args:
        results: List of ranked results with 'score' field
        k: Number of top results to consider (default: 5)
        relevant_threshold: Minimum score to consider relevant (default: 7.0)

    Returns:
        Precision score (0.0-1.0)
        - 1.0: All top-K results are relevant
        - 0.0: No top-K results are relevant

    Example:
        results = [{'score': 9.0}, {'score': 6.0}, {'score': 8.0}, {'score': 5.0}, {'score': 7.5}]
        precision = precision_at_k(results, k=5, relevant_threshold=7.0)
        # Returns 0.6 (3 out of 5 results are relevant: 9.0, 8.0, 7.5)
    """
    if k == 0 or len(results) == 0:
        return 0.0

    relevant_count = sum(
        1 for result in results[:k]
        if result.get('score', 0.0) >= relevant_threshold
    )

    return relevant_count / k


def recall_at_k(results: List[Dict[str, Any]], k: int = 10, relevant_threshold: float = 7.0) -> float:
    """
    Calculate Recall@K.

    Recall@K = (# relevant results in top K) / (total # relevant results)

    Args:
        results: List of ALL ranked results with 'score' field
        k: Number of top results to consider (default: 10)
        relevant_threshold: Minimum score to consider relevant (default: 7.0)

    Returns:
        Recall score (0.0-1.0)
        - 1.0: All relevant results are in top-K
        - 0.0: No relevant results in top-K

    Example:
        results = [
            {'score': 9.0}, {'score': 6.0}, {'score': 8.0},  # top-3
            {'score': 5.0}, {'score': 7.5}  # positions 4-5
        ]
        recall = recall_at_k(results, k=3, relevant_threshold=7.0)
        # Returns 0.67 (2 of 3 relevant results in top-3: 9.0, 8.0 found, 7.5 missed)
    """
    # Count total relevant results across all positions
    total_relevant = sum(
        1 for result in results
        if result.get('score', 0.0) >= relevant_threshold
    )

    if total_relevant == 0:
        return 0.0

    # Count relevant results in top-K
    relevant_in_k = sum(
        1 for result in results[:k]
        if result.get('score', 0.0) >= relevant_threshold
    )

    return relevant_in_k / total_relevant


def f1_at_k(results: List[Dict[str, Any]], k: int = 5, relevant_threshold: float = 7.0) -> float:
    """
    Calculate F1 score at K (harmonic mean of Precision@K and Recall@K).

    F1@K = 2 * (Precision@K * Recall@K) / (Precision@K + Recall@K)

    Args:
        results: List of ranked results with 'score' field
        k: Number of top results to consider (default: 5)
        relevant_threshold: Minimum score to consider relevant (default: 7.0)

    Returns:
        F1 score (0.0-1.0)
    """
    precision = precision_at_k(results, k, relevant_threshold)
    recall = recall_at_k(results, k, relevant_threshold)

    if precision + recall == 0.0:
        return 0.0

    return 2 * (precision * recall) / (precision + recall)


def calculate_all_metrics(
    results: List[Dict[str, Any]],
    k_values: List[int] = [5, 10],
    relevant_threshold: float = 7.0
) -> Dict[str, float]:
    """
    Calculate all evaluation metrics for a set of results.

    Args:
        results: List of ranked results with 'score' field (GPT-5 relevance 0-10)
        k_values: List of K values for Precision/Recall/NDCG (default: [5, 10])
        relevant_threshold: Minimum score to consider relevant (default: 7.0)

    Returns:
        Dictionary with all metric values

    Example:
        results = [{'score': 9.0}, {'score': 8.5}, {'score': 7.0}, ...]
        metrics = calculate_all_metrics(results, k_values=[5, 10], relevant_threshold=7.0)
        # Returns:
        # {
        #     'mrr': 1.0,
        #     'ndcg@5': 0.95,
        #     'ndcg@10': 0.92,
        #     'precision@5': 0.8,
        #     'precision@10': 0.7,
        #     'recall@5': 0.5,
        #     'recall@10': 0.8,
        #     'f1@5': 0.62,
        #     'f1@10': 0.75
        # }
    """
    metrics = {}

    # MRR (single value, not dependent on K)
    metrics['mrr'] = mean_reciprocal_rank(results, relevant_threshold)

    # Metrics for each K value
    for k in k_values:
        metrics[f'ndcg@{k}'] = ndcg_at_k(results, k)
        metrics[f'precision@{k}'] = precision_at_k(results, k, relevant_threshold)
        metrics[f'recall@{k}'] = recall_at_k(results, k, relevant_threshold)
        metrics[f'f1@{k}'] = f1_at_k(results, k, relevant_threshold)

    return metrics


def compare_approaches(
    epub_results: List[Dict[str, Any]],
    pgn_results: List[Dict[str, Any]],
    rrf_results: List[Dict[str, Any]],
    k_values: List[int] = [5, 10],
    relevant_threshold: float = 7.0
) -> Dict[str, Dict[str, float]]:
    """
    Compare metrics across three approaches: EPUB-only, PGN-only, RRF-merged.

    Args:
        epub_results: Results from EPUB-only collection
        pgn_results: Results from PGN-only collection
        rrf_results: Results from RRF multi-collection merge
        k_values: K values for metrics (default: [5, 10])
        relevant_threshold: Relevance threshold (default: 7.0)

    Returns:
        Dictionary with metrics for each approach

    Example:
        comparison = compare_approaches(epub_results, pgn_results, rrf_results)
        # Returns:
        # {
        #     'epub': {'mrr': 0.5, 'ndcg@5': 0.8, ...},
        #     'pgn': {'mrr': 1.0, 'ndcg@5': 0.9, ...},
        #     'rrf': {'mrr': 1.0, 'ndcg@5': 0.95, ...}
        # }
    """
    return {
        'epub': calculate_all_metrics(epub_results, k_values, relevant_threshold),
        'pgn': calculate_all_metrics(pgn_results, k_values, relevant_threshold),
        'rrf': calculate_all_metrics(rrf_results, k_values, relevant_threshold)
    }


def determine_winner(
    epub_metrics: Dict[str, float],
    pgn_metrics: Dict[str, float],
    rrf_metrics: Dict[str, float],
    primary_metric: str = 'ndcg@10'
) -> str:
    """
    Determine which approach performed best based on primary metric.

    Args:
        epub_metrics: Metrics from EPUB-only approach
        pgn_metrics: Metrics from PGN-only approach
        rrf_metrics: Metrics from RRF-merged approach
        primary_metric: Metric to use for comparison (default: 'ndcg@10')

    Returns:
        Winner name: 'epub', 'pgn', or 'rrf'
    """
    scores = {
        'epub': epub_metrics.get(primary_metric, 0.0),
        'pgn': pgn_metrics.get(primary_metric, 0.0),
        'rrf': rrf_metrics.get(primary_metric, 0.0)
    }

    return max(scores, key=scores.get)
