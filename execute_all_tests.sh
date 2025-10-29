#!/bin/bash
set -e

echo "═══════════════════════════════════════════════════════"
echo "🧪 CHESS RAG SYSTEM - 10 QUERY VALIDATION TEST"
echo "   Testing GPT-4-Turbo Model"
echo "═══════════════════════════════════════════════════════"
echo ""

PROJECT_DIR="/Users/leon/Downloads/python/chess-analysis-system"
RESULTS_DIR="$PROJECT_DIR/test_results_gpt4turbo"
TEST_REPORT="$PROJECT_DIR/test_report_gpt4turbo.txt"
API_URL="http://127.0.0.1:5001/query"

cd "$PROJECT_DIR"

# Verify Flask
echo "🔍 Verifying Flask is running..."
if ! curl -s "http://127.0.0.1:5001" > /dev/null 2>&1; then
    echo "❌ ERROR: Flask is NOT running"
    exit 1
fi
echo "✅ Flask is running (GPT-4-Turbo)"

# Create results directory
mkdir -p "$RESULTS_DIR"

# Initialize report
cat > "$TEST_REPORT" << EOF
═══════════════════════════════════════════════════════
CHESS RAG SYSTEM - AUTOMATED TEST REPORT (GPT-4-TURBO)
Test Date: $(date)
Model: gpt-4-turbo
═══════════════════════════════════════════════════════

EOF

echo ""
echo "🎯 EXECUTING ALL 10 TEST QUERIES"
echo "═══════════════════════════════════════════════════════"

queries=(
    "tell me about the Italian Game"
    "tell me about the Ruy Lopez"
    "tell me about the King's Indian Defense"
    "tell me about the Caro-Kann Defense"
    "tell me about the Sicilian Defense"
    "explain the Najdorf variation of the Sicilian Defense"
    "compare the Najdorf and Dragon variations"
    "compare the Queen's Gambit Accepted and Declined"
    "explain the Winawer variation of the French Defense"
    "tell me about the French Defense"
)

phases=("Phase1" "Phase1" "Phase1" "Phase1" "Phase2" "Phase2" "Phase2" "Phase2" "Phase2" "Phase2")
filenames=("01_Italian" "02_Ruy_Lopez" "03_Kings_Indian" "04_Caro_Kann" "05_Sicilian" "06_Najdorf" "07_Compare_ND" "08_QG_Compare" "09_Winawer" "10_French")

phase1_pass=0
phase1_fail=0
phase2_pass=0
phase2_fail=0

for i in "${!queries[@]}"; do
    query="${queries[$i]}"
    phase="${phases[$i]}"
    filename="${filenames[$i]}"
    query_num=$((i+1))
    
    echo ""
    echo "───────────────────────────────────────────────────────"
    echo "Query $query_num/10 [$phase]: $query"
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
        
        # Check for Sicilian contamination
        sicilian_found=0
        if grep -q "diagram_positions" "$response_file"; then
            if grep -iE "1\\.\\s*e4\\s+c5" "$response_file" > /dev/null 2>&1; then
                sicilian_found=1
            fi
            diagram_count=$(grep -o "\"fen\":" "$response_file" | wc -l | tr -d ' ')
            echo "   Diagrams: $diagram_count"
        else
            diagram_count=0
        fi
        
        # Determine result
        if [ "$phase" = "Phase1" ]; then
            if [ $sicilian_found -eq 0 ]; then
                result="PASS"
                phase1_pass=$((phase1_pass + 1))
                echo "   ✅ PASS - No Sicilian contamination"
            else
                result="FAIL"
                phase1_fail=$((phase1_fail + 1))
                echo "   ❌ FAIL - Sicilian contamination!"
            fi
        else
            if [ $diagram_count -gt 0 ]; then
                result="PASS"
                phase2_pass=$((phase2_pass + 1))
                echo "   ✅ PASS"
            else
                result="FAIL"
                phase2_fail=$((phase2_fail + 1))
                echo "   ❌ FAIL - No diagrams"
            fi
        fi
        
        echo "QUERY $query_num: $query" >> "$TEST_REPORT"
        echo "Phase: $phase | Result: $result | Diagrams: $diagram_count" >> "$TEST_REPORT"
        echo "" >> "$TEST_REPORT"
    else
        echo "❌ HTTP $http_code"
        [ "$phase" = "Phase1" ] && phase1_fail=$((phase1_fail + 1)) || phase2_fail=$((phase2_fail + 1))
        echo "QUERY $query_num: ERROR (HTTP $http_code)" >> "$TEST_REPORT"
        echo "" >> "$TEST_REPORT"
    fi
    
    [ $i -lt 9 ] && sleep 5
done

# Calculate results
phase1_total=$((phase1_pass + phase1_fail))
phase2_total=$((phase2_pass + phase2_fail))
overall_pass=$((phase1_pass + phase2_pass))
overall_pct=$((overall_pass * 100 / 10))
phase1_pct=$((phase1_pass * 100 / phase1_total))
phase2_pct=$((phase2_pass * 100 / phase2_total))

cat >> "$TEST_REPORT" << EOF
═══════════════════════════════════════════════════════
TEST SUMMARY
═══════════════════════════════════════════════════════
Phase 1: $phase1_pass/$phase1_total ($phase1_pct%)
Phase 2: $phase2_pass/$phase2_total ($phase2_pct%)
Overall: $overall_pass/10 ($overall_pct%)

SUCCESS CRITERIA:
- Overall ≥90% (9/10): $([ $overall_pct -ge 90 ] && echo 'MET ✅' || echo 'NOT MET ❌')
- Phase 1 ≥75% (3/4): $([ $phase1_pct -ge 75 ] && echo 'MET ✅' || echo 'NOT MET ❌')
- Phase 2 =100% (6/6): $([ $phase2_pct -eq 100 ] && echo 'MET ✅' || echo 'NOT MET ❌')

═══════════════════════════════════════════════════════
COMPARISON WITH GPT-4o BASELINE
═══════════════════════════════════════════════════════
GPT-4o Baseline:
  - Phase 1: 0/4 (0%)
  - Phase 2: 6/6 (100%)
  - Overall: 6/10 (60%)

GPT-4-Turbo Results:
  - Phase 1: $phase1_pass/$phase1_total ($phase1_pct%)
  - Phase 2: $phase2_pass/$phase2_total ($phase2_pct%)
  - Overall: $overall_pass/10 ($overall_pct%)

Improvement: $((overall_pct - 60))% (from 60% to $overall_pct%)
EOF

echo ""
echo "═══════════════════════════════════════════════════════"
echo "✅ TESTING COMPLETE"
echo "═══════════════════════════════════════════════════════"
echo ""
echo "📊 RESULTS:"
echo "   Phase 1: $phase1_pass/$phase1_total ($phase1_pct%)"
echo "   Phase 2: $phase2_pass/$phase2_total ($phase2_pct%)"
echo "   Overall: $overall_pass/10 ($overall_pct%)"
echo ""
echo "📄 Full report saved to: $TEST_REPORT"
