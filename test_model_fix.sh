#!/bin/bash
set +e  # Don't exit on error

echo "Testing synthesis with corrected model name (gpt-5-2025-08-07)..."
echo ""

# Submit query
echo "Submitting query..."
curl -s -X POST "http://127.0.0.1:5001/query" \
    -H "Content-Type: application/json" \
    -d '{"query": "tell me about the Italian Game"}' \
    -o test_gpt5_fixed.json

if [ $? -ne 0 ]; then
    echo "❌ FAIL: curl command failed"
    exit 1
fi

echo "Response received"
echo ""

# Check file size
filesize=$(wc -c < test_gpt5_fixed.json | tr -d ' ')
echo "Response size: $filesize bytes"

if [ $filesize -lt 100 ]; then
    echo "❌ FAIL: Response too small"
    cat test_gpt5_fixed.json
    exit 1
fi

# Check for diagrams
if grep -q '"diagram_positions"' test_gpt5_fixed.json; then
    diagram_count=$(grep -o '"fen":' test_gpt5_fixed.json | wc -l | tr -d ' ')
    echo "✅ Diagrams generated: $diagram_count"
    
    # Check for Sicilian contamination
    if grep -iq "sicilian" test_gpt5_fixed.json || grep -iE "1\.\\s*e4\\s+c5" test_gpt5_fixed.json; then
        echo "⚠️  WARNING: Sicilian contamination detected"
    else
        echo "✅ No Sicilian contamination"
    fi
    
    echo ""
    echo "✅ SUCCESS: Synthesis working with correct model!"
else
    echo "❌ FAIL: No diagrams in response (synthesis still broken)"
    echo ""
    echo "Sample response:"
    head -20 test_gpt5_fixed.json
fi
