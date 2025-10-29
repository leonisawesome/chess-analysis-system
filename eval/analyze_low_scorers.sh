#!/bin/bash
# Analyze the lowest scoring files to understand why they score lower

echo "Analyzing bottom 10 lowest-scoring files..."
echo "=========================================="
echo

# Get the bottom 10 files
tail -n +2 eval/out/evs_scores_good733.csv | sort -t',' -k2 -n | head -10 | while IFS='' read -r line; do
    # Split on last comma to handle filenames with commas
    filepath="${line%,*}"
    score="${line##*,}"

    filename=$(basename "$filepath")
    echo "File: $filename"
    echo "CSV Score: $score"

    # Run EVS test and extract key metrics
    python3 -m chess_rag_system --test-evs-integration "$filepath" 2>/dev/null | grep -E "Instructional Value:|Base EVS Score:|Content Type:|Game Type:|Final EVS Score:" | sed 's/^/  /'

    echo "---"
    echo
done