#!/bin/bash

echo "════════════════════════════════════════════════════════════════════════════"
echo "CLEAN ITEM-014 TEST"
echo "════════════════════════════════════════════════════════════════════════════"
echo ""

# Set API key (latest from user)
if [ -f .env ]; then
    set -a
    source .env
    set +a
fi
: "${OPENAI_API_KEY:?Set OPENAI_API_KEY (or create .env)}"

# Ensure no Flask is running
echo "1. Cleaning up any existing processes..."
pkill -9 -f "python3 app.py" 2>/dev/null
sleep 2

# Verify port is free
if lsof -i :5001 >/dev/null 2>&1; then
    echo "   ❌ ERROR: Port 5001 still in use!"
    lsof -i :5001
    exit 1
fi
echo "   ✅ Port 5001 is free"

# Start Flask
echo ""
echo "2. Starting Flask server..."
python3 app.py > flask_clean_test.log 2>&1 &
FLASK_PID=$!
echo "   Flask PID: $FLASK_PID"

# Wait for Flask to initialize
echo "   Waiting for Flask to initialize..."
for i in {1..30}; do
    if curl -s -f http://127.0.0.1:5001/test >/dev/null 2>&1; then
        echo "   ✅ Flask ready (${i}s)"
        break
    fi
    if [ $i -eq 30 ]; then
        echo "   ❌ Flask failed to start!"
        cat flask_clean_test.log
        kill -9 $FLASK_PID 2>/dev/null
        exit 1
    fi
    sleep 1
done

# Send test query
echo ""
echo "3. Testing: 'Explain the minority attack'"
echo ""

START_TIME=$(date +%s)

curl -s -X POST "http://127.0.0.1:5001/query" \
    -H "Content-Type: application/json" \
    -d '{"query": "Explain the minority attack"}' \
    -o clean_test_response.json

END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))

echo "   ⏱ Completed in ${DURATION}s"
echo ""

# Kill Flask
kill -9 $FLASK_PID 2>/dev/null
sleep 1

# Analyze results
echo "════════════════════════════════════════════════════════════════════════════"
echo "RESULTS"
echo "════════════════════════════════════════════════════════════════════════════"

if [ ! -f clean_test_response.json ]; then
    echo "❌ FAILURE: No response file generated!"
    echo ""
    echo "Flask log:"
    cat flask_clean_test.log
    exit 1
fi

# Parse response
python3 << 'ANALYSIS'
import json
import re
import sys

try:
    with open("clean_test_response.json", "r") as f:
        data = json.load(f)

    answer = data.get("answer", "")
    diagrams = data.get("diagram_positions", [])

    print(f"Answer length:   {len(answer):,} characters")
    print(f"Diagram count:   {len(diagrams)}")
    print()

    # Check for errors
    if "Error code: 404" in answer or "model_not_found" in answer:
        print("❌ FAILURE: Model not found error still present!")
        print()
        print("Error in answer:")
        # Find and print the error
        error_match = re.search(r'\[Error.*?\]', answer, re.DOTALL)
        if error_match:
            print(error_match.group(0)[:500])
        sys.exit(1)

    # Check for diagrams
    if len(diagrams) == 0:
        print("❌ FAILURE: No diagrams generated!")
        print()
        print("Answer preview:")
        print(answer[:500])
        sys.exit(1)

    # Success - check if canonical FEN was used
    print("✅ SUCCESS: Diagrams generated!")
    print()
    print("Diagram captions:")
    for i, diag in enumerate(diagrams[:3], 1):
        caption = diag.get("caption", "")
        print(f"{i}. {caption[:100]}...")

    # Check if canonical FEN appears
    canonical_fen = "r2q1rk1/pp1nbppp/2pb1n2/8/2PPPN2/2N1B3/PP3PPP/R2Q1RK1"
    if canonical_fen in str(diagrams):
        print()
        print("✅ Canonical FEN detected in diagrams (ITEM-014 working!)")

    print()
    print("════════════════════════════════════════════════════════════════════════════")
    print("✅ ITEM-014 TEST PASSED")
    print("════════════════════════════════════════════════════════════════════════════")

except Exception as e:
    print(f"❌ FAILURE: Error analyzing response: {e}")
    sys.exit(1)

ANALYSIS
