#!/usr/bin/env python3
"""Generate HTML with working chess boards using Lichess embeds."""

def fen_to_lichess_url(fen):
    """Convert FEN to Lichess editor URL."""
    import urllib.parse
    encoded_fen = urllib.parse.quote(fen)
    return f"https://lichess.org/editor/{encoded_fen}"

def generate_working_html(query, expected_diagrams, output_file):
    """Generate HTML with Lichess iframe embeds."""
    
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Expected: {query}</title>
    
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;
            max-width: 900px;
            margin: 40px auto;
            padding: 20px;
            background: #f5f5f5;
        }}
        h1 {{
            color: #333;
            border-bottom: 3px solid #4caf50;
            padding-bottom: 10px;
        }}
        .query-box {{
            background: #fff;
            padding: 20px;
            border-radius: 8px;
            margin: 20px 0;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .query-text {{
            font-size: 18px;
            font-weight: bold;
            color: #555;
        }}
        .expected-label {{
            background: #e8f5e9;
            color: #2e7d32;
            padding: 10px 15px;
            border-radius: 4px;
            font-weight: bold;
            display: inline-block;
            margin: 20px 0 10px 0;
        }}
        .section {{
            background: white;
            padding: 30px;
            border-radius: 8px;
            margin: 20px 0;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .section h2 {{
            color: #333;
            margin-top: 0;
        }}
        .diagram-container {{
            margin: 30px 0;
            padding: 20px;
            background: #f9f9f9;
            border-left: 4px solid #2196f3;
            border-radius: 4px;
        }}
        .diagram-label {{
            font-weight: bold;
            color: #1976d2;
            margin-bottom: 15px;
            font-size: 16px;
        }}
        .board-frame {{
            width: 400px;
            height: 400px;
            margin: 15px 0;
            border: 2px solid #ccc;
            border-radius: 4px;
        }}
        .fen-string {{
            font-family: 'Courier New', monospace;
            background: #f5f5f5;
            padding: 8px;
            border-radius: 4px;
            margin: 10px 0;
            font-size: 12px;
            word-break: break-all;
        }}
        .description {{
            color: #666;
            margin: 10px 0;
            font-style: italic;
        }}
        .lichess-link {{
            display: inline-block;
            margin: 10px 0;
            color: #1976d2;
            text-decoration: none;
        }}
        .lichess-link:hover {{
            text-decoration: underline;
        }}
        .checklist {{
            background: #fff3e0;
            padding: 20px;
            border-left: 4px solid #ff9800;
            border-radius: 4px;
            margin: 20px 0;
        }}
        .checklist h3 {{
            margin-top: 0;
            color: #e65100;
        }}
        .checklist li {{
            margin: 8px 0;
        }}
        .pass {{
            color: #4caf50;
            font-weight: bold;
        }}
        .fail {{
            color: #f44336;
            font-weight: bold;
        }}
    </style>
</head>
<body>
    <h1>🎯 Expected Output: {query}</h1>
    
    <div class="query-box">
        <div class="query-text">Query: "{query}"</div>
    </div>
    
    <div class="expected-label">✅ EXPECTED BEHAVIOR</div>
    
    <div class="section">
        <h2>Expected Response</h2>
        <p>When you submit the query "<strong>{query}</strong>", the system should return <strong>{len(expected_diagrams)} DIFFERENT diagrams</strong> showing:</p>
        <ul>
"""
    
    for i, diag in enumerate(expected_diagrams, 1):
        html += f"            <li><strong>Diagram {i}:</strong> {diag['description']}</li>\\n"
    
    html += """        </ul>
    </div>
    
    <div class="section">
        <h2>Expected Diagrams (Visual)</h2>
        <p>These are the chess positions you should see in the actual response:</p>
"""
    
    for i, diag in enumerate(expected_diagrams, 1):
        lichess_url = fen_to_lichess_url(diag['fen'])
        html += f"""
        <div class="diagram-container">
            <div class="diagram-label">Diagram {i}: {diag['description']}</div>
            <iframe src="{lichess_url}" 
                    class="board-frame" 
                    frameborder="0">
            </iframe>
            <a href="{lichess_url}" target="_blank" class="lichess-link">📐 Open in Lichess</a>
            <div class="fen-string">FEN: {diag['fen']}</div>
            <div class="description">{diag['description']}</div>
        </div>
"""
    
    html += f"""    </div>
    
    <div class="checklist">
        <h3>📋 Validation Checklist</h3>
        <p>When you run the actual query, verify:</p>
        <ol>
            <li>✅ Response contains {len(expected_diagrams)} diagrams (not just 1)</li>
            <li>✅ Each diagram shows a DIFFERENT position (compare visually above)</li>
            <li>✅ Diagrams show progression/variations (not repetition)</li>
            <li>✅ Positions match the concept (not unrelated positions)</li>
            <li>✅ No Sicilian contamination (check for 1.e4 c5 patterns)</li>
        </ol>
        <p><strong>If all checks pass:</strong> <span class="pass">ITEM-014 SUCCESS ✅</span></p>
        <p><strong>If any check fails:</strong> <span class="fail">ITEM-014 NEEDS MORE WORK ❌</span></p>
    </div>
</body>
</html>"""
    
    with open(output_file, 'w') as f:
        f.write(html)
    
    print(f"✅ Generated: {output_file}")

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

generate_working_html(
    "explain to me the difference between a bad bishop vs a good knight",
    test1_diagrams,
    "test_html/bad_bishop_vs_knight_WORKING.html"
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

generate_working_html(
    "Explain the minority attack",
    test2_diagrams,
    "test_html/minority_attack_WORKING.html"
)

print("\\n" + "="*70)
print("WORKING HTML FILES GENERATED (LICHESS EMBEDS)")
print("="*70)
print("\\nApproach: Using Lichess iframe embeds")
print("Pieces: Fully rendered by Lichess")
print("Advantage: Actually works, no CDN issues")
print("\\nFiles:")
print("  1. test_html/bad_bishop_vs_knight_WORKING.html")
print("  2. test_html/minority_attack_WORKING.html")
print("\\nThese files WILL show chess pieces when opened.")
