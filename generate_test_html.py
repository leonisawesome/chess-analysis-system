#!/usr/bin/env python3
"""
Generate HTML test files to validate query responses without API calls.
"""

import json
import sys

def generate_test_html(query, expected_diagrams, output_file):
    """Generate HTML file showing expected response."""
    
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Test: {query}</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            max-width: 800px;
            margin: 40px auto;
            padding: 20px;
            background: #f5f5f5;
        }}
        .test-case {{
            background: white;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .query {{
            font-size: 18px;
            font-weight: bold;
            color: #333;
            margin-bottom: 15px;
        }}
        .expected {{
            background: #e8f5e9;
            padding: 15px;
            border-left: 4px solid #4caf50;
            margin: 10px 0;
        }}
        .diagram {{
            background: #f5f5f5;
            padding: 10px;
            margin: 10px 0;
            font-family: monospace;
            border-left: 4px solid #2196f3;
        }}
        .pass {{
            color: #4caf50;
            font-weight: bold;
        }}
        .fail {{
            color: #f44336;
            font-weight: bold;
        }}
        .validation {{
            margin-top: 20px;
            padding: 15px;
            background: #fff3e0;
            border-left: 4px solid #ff9800;
        }}
    </style>
</head>
<body>
    <h1>🧪 Test Validation: ITEM-014</h1>
    
    <div class="test-case">
        <div class="query">Query: "{query}"</div>
        
        <div class="expected">
            <h3>✅ Expected Behavior:</h3>
            <p>The response should contain {len(expected_diagrams)} DIFFERENT diagrams:</p>
            <ul>
"""
    
    for i, diag in enumerate(expected_diagrams, 1):
        html += f"                <li><strong>Diagram {i}:</strong> {diag['description']}</li>\n"
    
    html += """            </ul>
        </div>
        
        <h3>Expected Diagram FENs:</h3>
"""
    
    for i, diag in enumerate(expected_diagrams, 1):
        html += f"""        <div class="diagram">
            <strong>Diagram {i}:</strong><br>
            FEN: <code>{diag['fen']}</code><br>
            Description: {diag['description']}
        </div>
"""
    
    html += """        
        <div class="validation">
            <h3>📋 Manual Validation Checklist:</h3>
            <p>When you run the actual query, verify:</p>
            <ol>
                <li>✅ Response contains multiple diagrams (not just 1)</li>
                <li>✅ Each diagram has a DIFFERENT FEN string</li>
                <li>✅ Diagrams show progression/variations (not repetition)</li>
                <li>✅ FENs match the middlegame concept (not opening positions)</li>
                <li>✅ No Sicilian contamination (1.e4 c5 patterns)</li>
            </ol>
            <p><strong>If all checks pass:</strong> <span class="pass">ITEM-014 SUCCESS ✅</span></p>
            <p><strong>If any check fails:</strong> <span class="fail">ITEM-014 FAILED ❌</span></p>
        </div>
    </div>
    
    <div class="test-case">
        <h3>🔧 How to Test:</h3>
        <ol>
            <li>Start Flask: <code>python3 app.py</code></li>
            <li>Open: <a href="http://127.0.0.1:5001/">http://127.0.0.1:5001/</a></li>
            <li>Submit query: <strong>"{query}"</strong></li>
            <li>Compare actual response to expected diagrams above</li>
            <li>Verify each diagram has DIFFERENT FEN</li>
        </ol>
    </div>
</body>
</html>"""
    
    with open(output_file, 'w') as f:
        f.write(html)
    
    print(f"✅ Generated: {output_file}")
    print(f"   Open in browser to see expected behavior")

# Test case 1: Bad bishop vs good knight
test1_diagrams = [
    {
        "fen": "8/5pkp/6p1/4P3/1P3N2/6P1/6KP/8 w - - 0 1",
        "description": "Canonical position - knight vs bad bishop"
    },
    {
        "fen": "8/5pkp/6p1/4PK2/1P3N2/6P1/7P/8 b - - 1 1",
        "description": "After Kg5 - king advances toward black pawns"
    },
    {
        "fen": "8/5pkp/6p1/4P3/1P3NP1/8/6KP/8 b - - 0 1",
        "description": "After g4 - preparing pawn breakthrough"
    },
    {
        "fen": "8/5p1p/5kp1/4P3/1P3NP1/8/6KP/8 w - - 2 2",
        "description": "Black king moves, knight dominates"
    }
]

generate_test_html(
    "explain to me the difference between a bad bishop vs a good knight",
    test1_diagrams,
    "test_html/bad_bishop_vs_knight_EXPECTED.html"
)

# Test case 2: Minority attack
test2_diagrams = [
    {
        "fen": "r2q1rk1/pp1nbppp/2pb1n2/8/2PPPN2/2N1B3/PP3PPP/R2Q1RK1 w - - 0 9",
        "description": "Canonical position - minority attack setup"
    },
    {
        "fen": "r2q1rk1/pp1nbppp/2pb1n2/8/PbPPPN2/2N1B3/1P3PPP/R2Q1RK1 w - - 1 10",
        "description": "After b4 - minority attack begins"
    },
    {
        "fen": "r2q1rk1/pp1nbppp/2pb1n2/8/P1PPPN2/2N1B3/5PPP/R2Q1RK1 b - - 0 10",
        "description": "After b5 - attacking black's pawn chain"
    },
    {
        "fen": "r2q1rk1/p2nbppp/1ppb1n2/8/P1PPPN2/2N1B3/5PPP/R2Q1RK1 w - - 0 11",
        "description": "Black responds, white continues pressure"
    }
]

generate_test_html(
    "Explain the minority attack",
    test2_diagrams,
    "test_html/minority_attack_EXPECTED.html"
)

print("\n" + "="*70)
print("HTML TEST FILES GENERATED")
print("="*70)
print("\nOpen these files in your browser:")
print("  1. test_html/bad_bishop_vs_knight_EXPECTED.html")
print("  2. test_html/minority_attack_EXPECTED.html")
print("\nThese show what the responses SHOULD look like.")
print("Run actual queries and compare to validate ITEM-014 works.")
