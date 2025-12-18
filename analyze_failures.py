import re

# Parse the error log from ingestion output
errors = """
  - 02a Teoria de Londres vs Ad6.pgn game 3: push() expects move to be pseudo-legal, but got f3d4 in rnbqkbnr/pp1ppppp/8/8/3P4/8/PPPnPPPP/R1BQKBNR
  - Chess Strategy Simplified.pgn game 3: push() expects move to be pseudo-legal, but got a5a6 in rnbqkbnr/ppppppp1/4p3/1R6/8/8/PPPPPP2/RNBQKBN1
  - Chess Strategy Simplified.pgn game 4: push() expects move to be pseudo-legal, but got g3g4 in rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR
  - Chess Strategy Simplified.pgn game 5: push() expects move to be pseudo-legal, but got f3c6 in rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR
  - Chess Strategy Simplified.pgn game 6: push() expects move to be pseudo-legal, but got d4d5 in rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR
  - Chess Strategy Simplified.pgn game 7: push() expects move to be pseudo-legal, but got g6g5 in rnbqk2r/1ppp2p1/4np2/1PP5/4N2p/5P2/3P2PP/RNBQK2R
  - Chess Strategy Simplified.pgn game 13: push() expects move to be pseudo-legal, but got h8g8 in rnbq1rk1/pppppppp/8/8/8/8/PPPP1PPP/RN1QKBNB
  - Chess Strategy Simplified.pgn game 14: push() expects move to be pseudo-legal, but got a3b5 in rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR
  - Chess Strategy Simplified.pgn game 16: push() expects move to be pseudo-legal, but got c5d4 in rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR
  - Chess Strategy Simplified.pgn game 20: push() expects move to be pseudo-legal, but got e6e5 in rnbqkbnr/pppppppp/8/8/5B2/8/PPPPPPPP/RN1QKBNB
"""

file_counts = {}
for line in errors.strip().split('\n'):
    if 'pgn game' in line:
        match = re.search(r'- ([^:]+\.pgn)', line)
        if match:
            filename = match.group(1)
            file_counts[filename] = file_counts.get(filename, 0) + 1

print("Files with illegal move errors (sample of 10 shown):")
for filename, count in sorted(file_counts.items(), key=lambda x: x[1], reverse=True):
    print(f"  {filename}: {count} errors")

print(f"\nTotal files affected: {len(file_counts)}")
print(f"Total errors shown: {sum(file_counts.values())}")
print(f"\nNote: Only showing first 10 errors, actual total: 412 errors")
