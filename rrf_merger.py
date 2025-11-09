"""
RRF Merger Module - Reciprocal Rank Fusion

Handles:
- Reciprocal Rank Fusion algorithm for merging ranked lists
- Collection-specific weight application
- Source attribution tracking
- Tie-breaking with best rank and similarity scores

Phase 5.1 Implementation
"""

from typing import List, Dict, Any
from collections import defaultdict


def reciprocal_rank_fusion(
    results_lists: List[List[Dict[str, Any]]],
    k: int = 60,
    source_weights: Dict[str, float] = None
) -> List[Dict[str, Any]]:
    """
    Merge ranked lists using Reciprocal Rank Fusion.

    Args:
        results_lists: List of ranked result lists from different collections
        k: RRF constant (default 60, standard from literature)
        source_weights: Dict mapping collection name to weight multiplier
                       e.g., {'EPUB': 1.0, 'PGN': 1.3}

    Returns:
        Merged list sorted by RRF score (descending)

    Algorithm:
        For each result across all lists:
            RRF_score = Σ weight × (1 / (k + rank))

        Results are then sorted by:
            1. RRF score (descending)
            2. Best rank across all lists (ascending)
            3. Max similarity score (descending)
    """
    if source_weights is None:
        source_weights = {}

    fused_scores = {}

    for results in results_lists:
        for rank, result in enumerate(results, start=1):
            result_id = result['id']
            collection = result.get('collection', 'unknown')
            weight = source_weights.get(collection, 1.0)

            # RRF formula with collection weight
            rrf_contribution = weight * (1.0 / (k + rank))

            if result_id in fused_scores:
                fused_scores[result_id]['rrf_score'] += rrf_contribution
                fused_scores[result_id]['sources'].append({
                    'collection': collection,
                    'rank': rank,
                    'similarity': result.get('score', 0.0)
                })
            else:
                fused_scores[result_id] = {
                    'rrf_score': rrf_contribution,
                    'best_rank': rank,
                    'max_similarity': result.get('score', 0.0),
                    'result': result,
                    'sources': [{
                        'collection': collection,
                        'rank': rank,
                        'similarity': result.get('score', 0.0)
                    }]
                }

            # Track best rank and max similarity for tie-breaking
            fused_scores[result_id]['best_rank'] = min(
                fused_scores[result_id]['best_rank'],
                rank
            )
            fused_scores[result_id]['max_similarity'] = max(
                fused_scores[result_id]['max_similarity'],
                result.get('score', 0.0)
            )

    # Sort by RRF score (desc), then best rank (asc), then max similarity (desc)
    merged = sorted(
        fused_scores.values(),
        key=lambda x: (-x['rrf_score'], x['best_rank'], -x['max_similarity'])
    )

    # Return results with RRF metadata attached
    return [
        {
            **m['result'],
            'rrf_score': m['rrf_score'],
            'best_rank': m['best_rank'],
            'max_similarity': m['max_similarity'],
            'fusion_sources': m['sources']
        }
        for m in merged
    ]


def merge_collections(
    epub_results: List[Dict[str, Any]],
    pgn_results: List[Dict[str, Any]],
    query_type: str = 'mixed',
    k: int = 60
) -> List[Dict[str, Any]]:
    """
    Convenience function to merge EPUB and PGN results with appropriate weights.

    Args:
        epub_results: Results from chess_production collection
        pgn_results: Results from chess_pgn_repertoire collection
        query_type: Type of query - 'opening', 'concept', or 'mixed'
        k: RRF constant

    Returns:
        Merged and ranked results
    """
    # Determine weights based on query type
    if query_type == 'opening':
        # Opening queries favor PGN (specific lines)
        weights = {'chess_production': 1.0, 'chess_pgn_repertoire': 1.3}
    elif query_type == 'concept':
        # Concept queries favor EPUB (strategic explanations)
        weights = {'chess_production': 1.3, 'chess_pgn_repertoire': 1.0}
    else:
        # Mixed or ambiguous - no bias
        weights = {'chess_production': 1.0, 'chess_pgn_repertoire': 1.0}

    # Tag results with collection name if not already present
    for result in epub_results:
        if 'collection' not in result:
            result['collection'] = 'chess_production'

    for result in pgn_results:
        if 'collection' not in result:
            result['collection'] = 'chess_pgn_repertoire'

    # Apply RRF
    merged = reciprocal_rank_fusion(
        [epub_results, pgn_results],
        k=k,
        source_weights=weights
    )

    return merged
