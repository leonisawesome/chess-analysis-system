#!/bin/bash
# ITEM-010: Test middlegame queries with existing Flask system

echo "═══════════════════════════════════════════════════════"
echo "MIDDLEGAME QUERY TEST - FLASK API"
echo "═══════════════════════════════════════════════════════"
echo ""

# Verify Flask is running
if ! curl -s http://127.0.0.1:5001 > /dev/null 2>&1; then
    echo "❌ Flask is not running - please start Flask first"
    exit 1
fi
echo "✅ Flask is running on port 5001"
echo ""

# Create output directory
mkdir -p middlegame_test_results
cd middlegame_test_results

echo "🎯 GENERATING RESPONSES FOR 10 MIDDLEGAME QUERIES"
echo "This will take approximately 15-20 minutes..."
echo ""

query_num=1
while IFS= read -r query; do
    [ -z "$query" ] && continue
    
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "Query $query_num/10: $query"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    filename=$(printf "%02d" $query_num)_$(echo "$query" | tr '[:upper:]' '[:lower:]' | tr ' ' '_' | cut -c1-30)
    
    echo "📤 Submitting query..."
    START_TIME=$(date +%s)
    
    curl -s -X POST "http://127.0.0.1:5001/query" \
        -H "Content-Type: application/json" \
        -d "{\"query\": \"$query\"}" \
        -o "${filename}_response.json"
    
    END_TIME=$(date +%s)
    DURATION=$((END_TIME - START_TIME))
    
    if [ -f "${filename}_response.json" ]; then
        # Analyze response
        diagram_count=$(grep -o "\"fen\":" "${filename}_response.json" | wc -l | tr -d ' ')
        answer_length=$(python3 << PYEOF
import json
try:
    with open("${filename}_response.json") as f:
        data = json.load(f)
    print(len(data.get("answer", "")))
except:
    print(0)
PYEOF
)
        
        echo "✅ Response received in ${DURATION}s"
        echo "   Answer length: ${answer_length} characters"
        echo "   Diagrams: ${diagram_count}"
        echo "   Saved: ${filename}_response.json"
    else
        echo "❌ No response received"
    fi
    
    echo ""
    query_num=$((query_num + 1))
    sleep 2
done < ../middlegame_test_queries.txt

cd ..

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ TEST COMPLETE"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📊 RESULTS SAVED TO: middlegame_test_results/"
echo ""
echo "📋 NEXT STEPS:"
echo "   1. Generate HTML files from JSON responses (if desired)"
echo "   2. Manual validation - check each response for:"
echo "      • Content accuracy"
echo "      • Diagram relevance"
echo "      • Contamination (wrong concepts/openings)"
echo "      • Quality vs openings baseline"
echo ""
echo "   3. Decide what (if anything) needs fixing"
echo "═══════════════════════════════════════════════════════"
