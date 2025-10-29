#!/usr/bin/env python3
"""Collect baseline EVS scores from good files for calibration."""

import sys
import json
import statistics as st
from pathlib import Path

# Add chess system to path
sys.path.insert(0, '/Users/leon/Downloads/python/chess-analysis-system')

from chess_rag_system.scoring.integration_scorer import IntegrationScorer
from chess_rag_system.analysis.semantic_analyzer import ChessSemanticAnalyzer
from chess_rag_system.analysis.pgn_detector import AdvancedPGNDetector
from chess_rag_system.core.models import AnalysisRequest

def main():
    # Read manifest
    manifest_file = 'eval/good733.tsv'  # Test fix with 5 files
    with open(manifest_file) as f:
        paths = [line.strip() for line in f if line.strip()]

    print(f"Processing {len(paths)} files...")

    # Initialize components
    semantic_analyzer = ChessSemanticAnalyzer()
    pgn_detector = AdvancedPGNDetector()
    scorer = IntegrationScorer()

    scores = []
    errors = 0

    for i, path in enumerate(paths):
        if i % 50 == 0:
            print(f"Progress: {i}/{len(paths)}")

        try:
            # Read file
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()

            # Create analysis request
            request = AnalysisRequest(
                text=content[:2000],  # Limit for performance
                file_path=path,
                surrounding_text=content[:1000]
            )

            # Perform semantic analysis
            semantic_result = semantic_analyzer.analyze_chess_content(request)

            # Perform PGN analysis
            pgn_result = pgn_detector.analyze_pgn_content(content, content[:1000])

            # Calculate final EVS score (0-100 range)
            evs_score = scorer.calculate_final_evs_score(semantic_result, pgn_result)
            scores.append(evs_score)

        except Exception as e:
            print(f"Error processing {path}: {e}")
            errors += 1

    # Calculate statistics
    scores.sort()

    def percentile(scores, p):
        idx = int(p * (len(scores) - 1))
        return scores[idx]

    dist = {
        "n": len(scores),
        "errors": errors,
        "min": min(scores) if scores else 0,
        "p25": percentile(scores, 0.25) if scores else 0,
        "p50": percentile(scores, 0.50) if scores else 0,
        "p75": percentile(scores, 0.75) if scores else 0,
        "p90": percentile(scores, 0.90) if scores else 0,
        "p95": percentile(scores, 0.95) if scores else 0,
        "p99": percentile(scores, 0.99) if scores else 0,
        "max": max(scores) if scores else 0,
        "mean": st.mean(scores) if scores else 0,
        "stdev": st.stdev(scores) if len(scores) > 1 else 0
    }

    # Save results
    Path('eval/out').mkdir(parents=True, exist_ok=True)

    # Save distribution
    with open('eval/out/evs_baseline_good733.json', 'w') as f:
        json.dump(dist, f, indent=2)

    # Save all scores
    with open('eval/out/evs_scores_good733.csv', 'w') as f:
        f.write("file_path,evs_score\n")
        for path, score in zip(paths[:len(scores)], scores):
            f.write(f"{path},{score}\n")

    # Print summary
    print("\n" + "="*60)
    print("EVS BASELINE DISTRIBUTION")
    print("="*60)
    print(json.dumps(dist, indent=2))

    return dist

if __name__ == "__main__":
    main()