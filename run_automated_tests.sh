#!/bin/bash
set -e

echo "═══════════════════════════════════════════════════════"
echo "🧪 CHESS RAG SYSTEM - 10 QUERY VALIDATION TEST"
echo "═══════════════════════════════════════════════════════"
echo ""

# Define paths
PROJECT_DIR="/Users/leon/Downloads/python/chess-analysis-system"
LOG_FILE="$PROJECT_DIR/flask_full.log"
LOG_BACKUP="$PROJECT_DIR/flask_full.log.old"
RESULTS_DIR="$PROJECT_DIR/test_results_automated"
TEST_REPORT="$PROJECT_DIR/test_report.txt"
API_URL="http://127.0.0.1:5001/query"

cd "$PROJECT_DIR"

# Step 1: Rotate log file
echo "📋 Step 1: Rotating log file..."
if [ -f "$LOG_FILE" ]; then
    mv "$LOG_FILE" "$LOG_BACKUP"
    echo "✅ Log rotated: flask_full.log → flask_full.log.old"
else
    echo "⚠️  No existing log file found"
fi

# Step 2: Verify Flask is running
echo ""
echo "🔍 Step 2: Verifying Flask is running..."
if curl -s "http://127.0.0.1:5001" > /dev/null 2>&1; then
    echo "✅ Flask is running on port 5001"
else
    echo "❌ ERROR: Flask is NOT running on port 5001"
    exit 1
fi

# Step 3: Create results directory
echo ""
echo "📁 Step 3: Creating results directory..."
mkdir -p "$RESULTS_DIR"
echo "✅ Results directory ready: $RESULTS_DIR"

# Initialize test report
echo "═══════════════════════════════════════════════════════" > "$TEST_REPORT"
echo "CHESS RAG SYSTEM - AUTOMATED TEST REPORT" >> "$TEST_REPORT"
echo "Test Date: $(date)" >> "$TEST_REPORT"
echo "═══════════════════════════════════════════════════════" >> "$TEST_REPORT"
echo "" >> "$TEST_REPORT"

echo ""
echo "═══════════════════════════════════════════════════════"
echo "🎯 SUBMITTING ALL 10 TEST QUERIES"
echo "═══════════════════════════════════════════════════════"

declare -a queries=(
    "tell me about the Italian Game"
    "tell me about the Ruy Lopez"
    "tell me about the King's Indian Defense"
    "tell me about the Caro-Kann Defense"
    "tell me about the Sicilian Defense"
    "explain the Najdorf variation of the Sicilian Defense"
    "compare the Najdorf and Dragon variations"
    "compare the Queen's Gambit Accepted and Declined"
    "explain the Winawer variation of the French Defense"
    "tell me about the French Defense"
)

declare -a phases=(
    "Phase1"
    "Phase1"
    "Phase1"
    "Phase1"
    "Phase2"
    "Phase2"
    "Phase2"
    "Phase2"
    "Phase2"
    "Phase2"
)

declare -a filenames=(
    "01_Italian_Game"
    "02_Ruy_Lopez"
    "03_Kings_Indian_Defense"
    "04_Caro_Kann_Defense"
    "05_Sicilian_Defense"
    "06_Najdorf_Variation"
    "07_Najdorf_vs_Dragon"
    "08_Queens_Gambit_AvD"
    "09_Winawer_Variation"
    "10_French_Defense"
)

phase1_pass=0
phase1_fail=0
phase2_pass=0
phase2_fail=0

for i in "${!queries[@]}"; do
    query="${queries[$i]}"
    phase="${phases[$i]}"
    filename="${filenames[$i]}"
    query_num=$((i+1))
    
    echo ""
    echo "───────────────────────────────────────────────────────"
    echo "Query $query_num/10 [$phase]: $query"
    echo "───────────────────────────────────────────────────────"
    echo "📤 Submitting query..."
    
    response_file="$RESULTS_DIR/${filename}_response.json"
    
    http_code=$(curl -s -X POST "$API_URL" \
        -H "Content-Type: application/json" \
        -d "{\"query\": \"$query\"}" \
        -o "$response_file" \
        -w "%{http_code}")
    
    if [ "$http_code" = "200" ]; then
        echo "✅ API response received"
        
        # Wait for processing to complete (check log for completion)
        echo "⏳ Waiting for processing..."
        sleep 90
        
        echo "QUERY $query_num: $query" >> "$TEST_REPORT"
        echo "Phase: $phase" >> "$TEST_REPORT"
        echo "Result: Submitted (validation in logs)" >> "$TEST_REPORT"
        echo "Response File: $response_file" >> "$TEST_REPORT"
        echo "" >> "$TEST_REPORT"
        
    else
        echo "❌ FAILED with HTTP code: $http_code"
        
        echo "QUERY $query_num: $query" >> "$TEST_REPORT"
        echo "Phase: $phase" >> "$TEST_REPORT"
        echo "Result: ERROR (HTTP $http_code)" >> "$TEST_REPORT"
        echo "" >> "$TEST_REPORT"
    fi
done

echo ""
echo "✅ All queries submitted"
echo "⏳ Processing complete - check logs for validation results"
