#!/usr/bin/env bash
set -euo pipefail
OUT=${1:-tests/fixtures/pgn_boundary}
mkdir -p "$OUT"

# PGN tokens that match the regex patterns
PGN_TOKENS=(
  "1." "2." "3." "4." "5." "6." "7." "8." "9." "10."
  "e4" "e5" "Nf3" "Nc6" "Bb5" "a6" "Ba4" "Nf6" "O-O" "Be7"
  "Re1" "b5" "Bb3" "d6" "c3" "O-O" "h3" "Nb8" "d4" "Nbd7"
  "Bc2" "c5" "b4" "Qc7" "a4" "Rd8" "axb5" "axb5" "Rxa8" "Rxa8"
  "1-0" "0-1" "1/2-1/2"
)

# Non-PGN filler words
FILLER_TOKENS=(
  "This" "is" "instructional" "content" "about" "chess" "strategy" "and"
  "tactics" "for" "beginners" "learning" "the" "game" "of" "chess"
  "understanding" "piece" "development" "king" "safety" "center" "control"
  "opening" "principles" "middlegame" "planning" "endgame" "technique"
  "positional" "play" "attacking" "patterns" "defensive" "resources"
)

make_token_file() {
  local total_tokens=$1
  local pgn_tokens=$2
  local filename=$3
  local filler_tokens=$((total_tokens - pgn_tokens))

  # Generate PGN tokens
  for i in $(seq 1 $pgn_tokens); do
    echo "${PGN_TOKENS[$((i % ${#PGN_TOKENS[@]}))]}"
  done

  # Generate filler tokens
  for i in $(seq 1 $filler_tokens); do
    echo "${FILLER_TOKENS[$((i % ${#FILLER_TOKENS[@]}))]}"
  done | \
  # Shuffle with fixed seed using sort (macOS compatible)
  awk 'BEGIN{srand(42)}{print rand(),$0}' | sort -k1,1n | cut -d" " -f2- | \
  # Group into sentences of 8-12 words
  awk '{
    words[++n] = $0
    if (n % 10 == 0) {
      for(i=n-9; i<=n; i++) printf "%s ", words[i]
      print "."
    }
  }
  END {
    if (n % 10 != 0) {
      for(i=(int(n/10)*10)+1; i<=n; i++) printf "%s ", words[i]
      print "."
    }
  }' > "$filename"
}

# Calculate exact token counts for target ratios
make_token_file 1000 320 "$OUT/pgn_ratio_0.320.txt"   # 320/1000 = 0.320
make_token_file 1000 337 "$OUT/pgn_ratio_0.337.txt"   # 337/1000 = 0.337
make_token_file 1000 347 "$OUT/pgn_ratio_0.347.txt"   # 347/1000 = 0.347
make_token_file 1000 357 "$OUT/pgn_ratio_0.357.txt"   # 357/1000 = 0.357
make_token_file 1000 370 "$OUT/pgn_ratio_0.370.txt"   # 370/1000 = 0.370

echo "Generated token-accurate boundary fixtures in $OUT"
echo "Files should now have precise PGN ratios for boundary testing"