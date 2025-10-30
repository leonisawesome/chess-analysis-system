#!/bin/bash

# START FLASK AND TEST MIDDLEGAME QUERY
# Purpose: Start Flask server and test ITEM-014 with a middlegame query

LOG_FILE="refactoring_logs/MIDDLEGAME_TEST_$(date +%Y%m%d_%H%M%S).log"
mkdir -p refactoring_logs

exec > >(tee -a "$LOG_FILE") 2>&1

echo "============================================================================"
echo "MIDDLEGAME QUERY TEST (ITEM-014 VALIDATION)"
echo "Started: $(date)"
echo "Log: $LOG_FILE"
echo "============================================================================"
echo ""

# Set API key
export OPENAI_API_KEY='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'

# Step 1: Start Flask server
echo "Step 1: Starting Flask server..."
echo ""

python3 app.py > flask_middlegame_test.log 2>&1 &
FLASK_PID=$!
echo "Flask PID: $FLASK_PID"
echo ""

# Wait for Flask to start
echo "Waiting for Flask to initialize..."
for i in {1..30}; do
    sleep 1
    if curl -s http://127.0.0.1:5001/ > /dev/null 2>&1; then
        echo "✅ Flask server ready (${i}s)"
        break
    fi
    if [ $i -eq 30 ]; then
        echo "❌ Flask failed to start after 30s"
        echo ""
        echo "Flask log (last 20 lines):"
        tail -20 flask_middlegame_test.log
        exit 1
    fi
done
echo ""

# Step 2: Test middlegame query
echo "Step 2: Testing middlegame query: 'Explain the minority attack'"
echo ""
echo "This query should:"
echo "  - Use canonical FEN from canonical_fens.json"
echo "  - Generate diagrams from the canonical position"
echo "  - NOT use opening move sequences"
echo ""

START_TIME=$(date +%s)

curl -X POST http://127.0.0.1:5001/query \
    -H "Content-Type: application/json" \
    -d '{"query": "Explain the minority attack"}' \
    -o middlegame_test_response.json \
    2>&1

END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))

echo ""
echo "⏱  Query completed in ${DURATION}s"
echo ""

# Step 3: Analyze response
echo "Step 3: Analyzing response..."
echo ""

if [ ! -f "middlegame_test_response.json" ]; then
    echo "❌ No response file generated"
    exit 1
fi

# Check if valid JSON
if ! python3 -c "import json; json.load(open('middlegame_test_response.json'))" 2>/dev/null; then
    echo "❌ Invalid JSON response"
    echo ""
    echo "Response content:"
    cat middlegame_test_response.json
    exit 1
fi

echo "✅ Valid JSON response"
echo ""

# Check for error
if grep -q '"error"' middlegame_test_response.json; then
    ERROR=$(python3 -c "import json; print(json.load(open('middlegame_test_response.json')).get('error', 'Unknown'))" 2>/dev/null)
    echo "❌ Error in response: $ERROR"
    exit 1
fi

echo "✅ No errors in response"
echo ""

# Check for answer
if ! grep -q '"answer"' middlegame_test_response.json; then
    echo "❌ No answer field in response"
    exit 1
fi

ANSWER=$(python3 -c "import json; print(json.load(open('middlegame_test_response.json')).get('answer', ''))" 2>/dev/null)
ANSWER_LENGTH=${#ANSWER}

echo "✅ Answer field present (${ANSWER_LENGTH} characters)"
echo ""

# Check for diagram markers
DIAGRAM_COUNT=$(echo "$ANSWER" | grep -o '\[DIAGRAM:' | wc -l | tr -d ' ')

if [ "$DIAGRAM_COUNT" -gt 0 ]; then
    echo "✅ Found $DIAGRAM_COUNT diagram markers"
    echo ""
    echo "Diagram markers:"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "$ANSWER" | grep -o '\[DIAGRAM:[^]]*\]' | head -5
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
else
    echo "❌ No diagram markers found"
    echo ""
    echo "ITEM-014 MAY NOT BE WORKING CORRECTLY"
fi
echo ""

# Check for canonical FEN
CANONICAL_FEN=$(python3 -c "import json; data=json.load(open('canonical_fens.json')); print(data.get('minority_attack', ''))" 2>/dev/null)

if [ -n "$CANONICAL_FEN" ]; then
    echo "Expected canonical FEN for minority_attack:"
    echo "  $CANONICAL_FEN"
    echo ""

    # Check if canonical FEN appears in diagrams
    if echo "$ANSWER" | grep -q "$CANONICAL_FEN"; then
        echo "✅ Canonical FEN found in response"
        echo "   ITEM-014 IS WORKING!"
    else
        echo "⚠️  Canonical FEN NOT found in response"
        echo "   ITEM-014 may not be using canonical positions"
    fi
fi
echo ""

# Save first 500 chars of answer
echo "Answer preview (first 500 chars):"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "$ANSWER" | head -c 500
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Step 4: Stop Flask
echo "Step 4: Stopping Flask server (PID: $FLASK_PID)..."
kill $FLASK_PID 2>/dev/null
wait $FLASK_PID 2>/dev/null
echo "✅ Flask stopped"
echo ""

# Summary
echo "============================================================================"
echo "MIDDLEGAME QUERY TEST COMPLETE"
echo "============================================================================"
echo ""
echo "Query: 'Explain the minority attack'"
echo "Duration: ${DURATION}s"
echo "Diagram count: $DIAGRAM_COUNT"
echo ""

if [ "$DIAGRAM_COUNT" -gt 0 ]; then
    echo "✅ SUCCESS: Diagrams generated for middlegame query"
    echo ""
    echo "ITEM-014 validation: PASSED"
    echo ""
    echo "The system now generates diagrams for middlegame concepts!"
else
    echo "❌ FAILURE: No diagrams generated"
    echo ""
    echo "ITEM-014 validation: FAILED"
    echo ""
    echo "Troubleshooting needed - check flask_middlegame_test.log"
fi
echo ""

echo "Files generated:"
echo "  - middlegame_test_response.json (full response)"
echo "  - flask_middlegame_test.log (Flask output)"
echo ""

echo "Log: $LOG_FILE"
echo "============================================================================"
