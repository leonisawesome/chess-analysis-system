#!/bin/bash
echo "════════════════════════════════════════════════════════════════════════════"
echo "EMERGENCY DIAGNOSTIC - Why No Diagrams Rendered"
echo "════════════════════════════════════════════════════════════════════════════"

echo ""
echo "1. Checking if tactical detection worked..."
echo "─────────────────────────────────────────────────────────"
if grep -q "TACTICAL QUERY DETECTED" flask_emergency_fix.log 2>/dev/null; then
    echo "✅ Tactical detection IS working"
    grep "TACTICAL QUERY DETECTED" flask_emergency_fix.log | tail -5
else
    echo "❌ No tactical detection logs found"
    echo "   This means queries aren't being recognized as tactical"
fi

echo ""
echo "2. Checking canonical diagram injection..."
echo "─────────────────────────────────────────────────────────"
if grep -q "Injected.*canonical diagram" flask_emergency_fix.log 2>/dev/null; then
    echo "✅ Canonical injection IS working"
    grep "Injected.*canonical diagram" flask_emergency_fix.log | tail -5
else
    echo "❌ No injection logs found"
    echo "   This means inject_canonical_diagrams() returned empty or wasn't called"
fi

echo ""
echo "3. Testing tactical_query_detector.py directly..."
echo "─────────────────────────────────────────────────────────"
python3 << 'PYEOF'
from tactical_query_detector import is_tactical_query, inject_canonical_diagrams
import json

# Test detection
query = "show me 5 examples of pins"
is_tactical = is_tactical_query(query)
print(f"Query: '{query}'")
print(f"Detected as tactical: {is_tactical}")

# Test injection
try:
    with open('canonical_positions.json', 'r') as f:
        canonical_positions = json.load(f)
    
    diagrams = inject_canonical_diagrams(query, canonical_positions)
    print(f"Diagrams injected: {len(diagrams)}")
    
    if diagrams:
        print(f"First diagram FEN: {diagrams[0].get('fen', 'N/A')}")
        print(f"First diagram category: {diagrams[0].get('category', 'N/A')}")
    else:
        print("❌ PROBLEM: inject_canonical_diagrams() returned empty list!")
        
except Exception as e:
    print(f"❌ ERROR during injection test: {e}")
PYEOF

echo ""
echo "4. Checking for SVG generation..."
echo "─────────────────────────────────────────────────────────"
if grep -q "svg" flask_emergency_fix.log 2>/dev/null; then
    echo "✅ SVG generation logs found"
    grep -i "svg" flask_emergency_fix.log | tail -3
else
    echo "⚠️  No SVG generation logs found"
fi

echo ""
echo "5. Checking response structure..."
echo "─────────────────────────────────────────────────────────"
if [ -f test_pins_query.json ]; then
    echo "Found test_pins_query.json, analyzing..."
    python3 << 'PYEOF'
import json

with open('test_pins_query.json', 'r') as f:
    response = json.load(f)

print(f"Response keys: {list(response.keys())}")
print(f"Has diagram_positions: {'diagram_positions' in response}")

if 'diagram_positions' in response:
    diagrams = response['diagram_positions']
    print(f"Number of diagrams: {len(diagrams)}")
    
    if diagrams:
        first = diagrams[0]
        print(f"First diagram keys: {list(first.keys())}")
        print(f"First diagram has FEN: {'fen' in first}")
        print(f"First diagram has SVG: {'svg' in first}")
        if 'svg' in first:
            svg_length = len(first['svg']) if first['svg'] else 0
            print(f"SVG length: {svg_length} chars")
    else:
        print("❌ PROBLEM: diagram_positions is empty array!")
else:
    print("❌ PROBLEM: No diagram_positions key in response!")
    
print(f"\nEmergency fix applied: {response.get('emergency_fix_applied', False)}")
PYEOF
else
    echo "⚠️  No test_pins_query.json found - test query hasn't been submitted yet"
fi

echo ""
echo "════════════════════════════════════════════════════════════════════════════"
echo "DIAGNOSTIC COMPLETE - Analyze Output Above"
echo "════════════════════════════════════════════════════════════════════════════"
echo ""
echo "Common failure modes:"
echo "  1. Detection works but injection returns empty (category mismatch)"
echo "  2. Diagrams injected but SVG generation fails"
echo "  3. Everything works but frontend doesn't receive data (response format)"
echo "  4. Flask logs show errors during canonical loading"
