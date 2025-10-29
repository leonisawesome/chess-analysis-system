#!/usr/bin/env python3
import sys
import csv
sys.path.insert(0, '/Users/leon/Downloads/python/chess-analysis-system')
from chess_rag_system.evs_calibration import calibrate_evs

# Read original scores
scores = []
with open('eval/out/evs_scores_good733.csv') as f:
    lines = f.readlines()[1:]  # Skip header
    for line in lines:
        line = line.strip()
        # Split on last comma to handle filenames with commas
        last_comma = line.rfind(',')
        filepath = line[:last_comma]
        score = float(line[last_comma+1:])
        scores.append((filepath, score))

# Apply calibration
calibrated = [(path, calibrate_evs(score)) for path, score in scores]

# Calculate distribution
tier3 = sum(1 for _, s in calibrated if s >= 80) / len(calibrated) * 100
tier2 = sum(1 for _, s in calibrated if s >= 90) / len(calibrated) * 100
tier1 = sum(1 for _, s in calibrated if s >= 95) / len(calibrated) * 100

print(f"Tier 3 (80+): {tier3:.1f}%")
print(f"Tier 2 (90+): {tier2:.1f}%")
print(f"Tier 1 (95+): {tier1:.1f}%")

# Check ordering preserved
original_order = [s for _, s in scores]
calibrated_order = [s for _, s in calibrated]
preserved = all(
    (o1 < o2) == (c1 < c2)
    for o1, c1 in zip(original_order, calibrated_order)
    for o2, c2 in zip(original_order, calibrated_order)
)
print(f"\nOrdering preserved: {preserved}")