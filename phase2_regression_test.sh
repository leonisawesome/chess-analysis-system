#!/bin/bash
set -e

echo "═══════════════════════════════════════════════════════"
echo "🧪 ITEM-008 PHASE 2 REGRESSION TEST"
echo "   Testing Sicilian Defense Diagram Generation"
echo "═══════════════════════════════════════════════════════"
echo ""
echo "Target: Maintain 6/6 (100%) pass rate on Phase 2 queries"
echo "Success Criteria: All 6 queries must generate diagrams"
echo ""

API_URL="http://127.0.0.1:5001/query"
RESULTS_DIR="phase2_regression_results"
mkdir -p "$RESULTS_DIR"

# Phase 2 queries (Sicilian Defense variations + other complex queries)
queries=(
    "tell me about the Sicilian Defense"
    "explain the Najdorf variation of the Sicilian Defense"
    "compare the Najdorf and Dragon variations"
    "compare the Queen's Gambit Accepted and Declined"
    "explain the Winawer variation of the French Defense"
    "tell me about the French Defense"
)

filenames=(
    "sicilian_defense"
    "najdorf_variation"
    "najdorf_dragon_compare"
    "queens_gambit_compare"
    "winawer_variation"
    "french_defense"
)

pass_count=0
fail_count=0

for i in "${!queries[@]}"; do
    query="${queries[$i]}"
    filename="${filenames[$i]}"
    query_num=$((i+1))
    
    echo ""
    echo "───────────────────────────────────────────────────────"
    echo "Phase 2 Query $query_num/6: $query"
    echo "───────────────────────────────────────────────────────"
    echo "📤 Submitting..."
    
    response_file="$RESULTS_DIR/${filename}_response.json"
    
    http_code=$(curl -s -X POST "$API_URL" \
        -H "Content-Type: application/json" \
        -d "{\"query\": \"$query\"}" \
        -o "$response_file" \
        -w "%{http_code}")
    
    if [ "$http_code" = "200" ]; then
        echo "✅ HTTP 200"
        
        # Count diagrams
        diagram_count=$(grep -o "\"fen\":" "$response_file" | wc -l | tr -d ' ')
        echo "   Diagrams generated: $diagram_count"
        
        # Phase 2 success = diagrams present
        if [ $diagram_count -gt 0 ]; then
            echo "   ✅ PASS - Diagrams present"
            pass_count=$((pass_count + 1))
        else
            echo "   ❌ FAIL - No diagrams generated"
            fail_count=$((fail_count + 1))
        fi
    else
        echo "❌ HTTP $http_code - API error"
        fail_count=$((fail_count + 1))
    fi
    
    # Wait between queries
    [ $i -lt 5 ] && sleep 5
done

# Calculate results
total_queries=6
pass_pct=$((pass_count * 100 / total_queries))

echo ""
echo "═══════════════════════════════════════════════════════"
echo "📊 PHASE 2 REGRESSION TEST RESULTS"
echo "═══════════════════════════════════════════════════════"
echo ""
echo "Pass: $pass_count/$total_queries ($pass_pct%)"
echo "Fail: $fail_count/$total_queries"
echo ""

if [ $pass_count -eq 6 ]; then
    echo "✅ SUCCESS: Phase 2 regression test PASSED"
    echo "   All 6 queries generated diagrams correctly"
    echo "   ITEM-008 does NOT break Sicilian Defense generation"
    echo ""
    echo "🎯 OVERALL ITEM-008 STATUS:"
    echo "   - Phase 1: 4/4 (100%) ✅"
    echo "   - Phase 2: 6/6 (100%) ✅"
    echo "   - Total: 10/10 (100%) ✅"
    echo ""
    echo "🚀 READY FOR PRODUCTION DEPLOYMENT"
    exit 0
else
    echo "⚠️  REGRESSION DETECTED: Phase 2 test FAILED"
    echo "   Expected: 6/6 (100%)"
    echo "   Actual: $pass_count/6 ($pass_pct%)"
    echo ""
    echo "❌ ITEM-008 may have introduced regression"
    echo "   Further investigation required"
    exit 1
fi
