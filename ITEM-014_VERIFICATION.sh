#!/bin/bash

# VERIFY ITEM-014 IMPLEMENTATION
# Purpose: Check if ITEM-014 changes were actually made and prove it with evidence

LOG_FILE="refactoring_logs/ITEM_014_VERIFICATION_$(date +%Y%m%d_%H%M%S).log"
mkdir -p refactoring_logs

exec > >(tee -a "$LOG_FILE") 2>&1

echo "============================================================================"
echo "ITEM-014 IMPLEMENTATION VERIFICATION"
echo "Started: $(date)"
echo "Log: $LOG_FILE"
echo "============================================================================"
echo ""

# Step 1: Check if ITEM-014 log exists
echo "Step 1: Looking for ITEM-014 execution log..."
ITEM_014_LOG=$(ls -t refactoring_logs/ITEM_014_MIDDLEGAME_SOLUTION_*.log 2>/dev/null | head -1)

if [ -n "$ITEM_014_LOG" ]; then
    echo "✅ Found: $ITEM_014_LOG"
    echo ""
    echo "Last 50 lines of execution log:"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    tail -50 "$ITEM_014_LOG"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
else
    echo "❌ No ITEM-014 execution log found"
    echo "This means ITEM-014 may not have been executed"
fi
echo ""

# Step 2: Check synthesis_pipeline.py for canonical_fen
echo "Step 2: Checking synthesis_pipeline.py for canonical_fen modifications..."
echo ""

if grep -q "canonical_fen" synthesis_pipeline.py; then
    echo "✅ Found 'canonical_fen' in synthesis_pipeline.py"
    echo ""
    echo "Lines containing canonical_fen:"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    grep -n "canonical_fen" synthesis_pipeline.py
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
else
    echo "❌ 'canonical_fen' NOT found in synthesis_pipeline.py"
    echo "ITEM-014 modifications NOT applied"
fi
echo ""

# Step 3: Check for CANONICAL POSITION in system prompts
echo "Step 3: Checking for CANONICAL POSITION instructions..."
echo ""

if grep -q "CANONICAL POSITION" synthesis_pipeline.py; then
    echo "✅ Found CANONICAL POSITION instructions"
    echo ""
    echo "Context around CANONICAL POSITION:"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    grep -A 5 -B 2 "CANONICAL POSITION" synthesis_pipeline.py
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
else
    echo "❌ CANONICAL POSITION instructions NOT found"
    echo "System prompts were NOT updated"
fi
echo ""

# Step 4: Check synthesize_answer function signature
echo "Step 4: Checking synthesize_answer function signature..."
echo ""

echo "Function signature:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
grep -A 3 "def synthesize_answer" synthesis_pipeline.py
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Step 5: Check stage2_expand_sections function signature
echo "Step 5: Checking stage2_expand_sections function signature..."
echo ""

echo "Function signature:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
grep -A 3 "def stage2_expand_sections" synthesis_pipeline.py
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Step 6: Check app.py for canonical_fen usage
echo "Step 6: Checking app.py for canonical_fen in synthesize_answer call..."
echo ""

if grep -q "synthesize_answer.*canonical_fen" app.py; then
    echo "✅ app.py passes canonical_fen to synthesize_answer"
    echo ""
    echo "synthesize_answer call:"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    grep -A 2 -B 2 "synthesize_answer" app.py | grep -A 2 -B 2 "canonical_fen"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
else
    echo "❌ app.py does NOT pass canonical_fen to synthesize_answer"
    echo "Integration NOT complete"
fi
echo ""

# Step 7: Check git commits
echo "Step 7: Checking recent git commits for ITEM-014..."
echo ""

echo "Recent commits mentioning ITEM-014 or middlegame:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
git log --oneline --grep="ITEM-014\|middlegame" -10 2>/dev/null || git log --oneline -5
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Step 8: Check canonical_fens.json
echo "Step 8: Checking canonical_fens.json..."
echo ""

if [ -f "canonical_fens.json" ]; then
    echo "✅ canonical_fens.json exists"
    echo ""
    echo "Contents:"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    cat canonical_fens.json
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
else
    echo "❌ canonical_fens.json NOT found"
fi
echo ""

# Step 9: Test syntax validation
echo "Step 9: Validating Python syntax..."
echo ""

echo "Checking synthesis_pipeline.py..."
python3 -m py_compile synthesis_pipeline.py 2>&1
if [ $? -eq 0 ]; then
    echo "✅ synthesis_pipeline.py syntax valid"
else
    echo "❌ synthesis_pipeline.py has syntax errors"
fi

echo ""
echo "Checking app.py..."
python3 -m py_compile app.py 2>&1
if [ $? -eq 0 ]; then
    echo "✅ app.py syntax valid"
else
    echo "❌ app.py has syntax errors"
fi
echo ""

# Step 10: Summary
echo "============================================================================"
echo "VERIFICATION SUMMARY"
echo "============================================================================"
echo ""

CHECKS_PASSED=0
CHECKS_TOTAL=8

# Check results
grep -q "canonical_fen" synthesis_pipeline.py && ((CHECKS_PASSED++))
grep -q "CANONICAL POSITION" synthesis_pipeline.py && ((CHECKS_PASSED++))
grep -q "def synthesize_answer.*canonical_fen" synthesis_pipeline.py && ((CHECKS_PASSED++))
grep -q "def stage2_expand_sections.*canonical_fen" synthesis_pipeline.py && ((CHECKS_PASSED++))
grep -q "synthesize_answer.*canonical_fen" app.py && ((CHECKS_PASSED++))
[ -f "canonical_fens.json" ] && ((CHECKS_PASSED++))
python3 -m py_compile synthesis_pipeline.py 2>/dev/null && ((CHECKS_PASSED++))
python3 -m py_compile app.py 2>/dev/null && ((CHECKS_PASSED++))

echo "Checks passed: $CHECKS_PASSED/$CHECKS_TOTAL"
echo ""

if [ $CHECKS_PASSED -eq $CHECKS_TOTAL ]; then
    echo "✅ ITEM-014 IMPLEMENTATION VERIFIED"
    echo ""
    echo "All required changes are present:"
    echo "  ✅ canonical_fen parameter added to functions"
    echo "  ✅ CANONICAL POSITION instructions in prompts"
    echo "  ✅ app.py integration complete"
    echo "  ✅ canonical_fens.json present"
    echo "  ✅ All syntax valid"
    echo ""
    echo "Status: READY FOR TESTING"
elif [ $CHECKS_PASSED -ge 6 ]; then
    echo "⚠️  ITEM-014 PARTIALLY IMPLEMENTED"
    echo ""
    echo "Most changes present but some missing"
    echo "Review verification details above"
else
    echo "❌ ITEM-014 NOT IMPLEMENTED"
    echo ""
    echo "Required changes are missing"
    echo "ITEM-014 script may not have run successfully"
fi
echo ""

echo "Next Steps:"
echo "  1. Review this verification log"
echo "  2. If verified: Test with middlegame query"
echo "  3. If not verified: Re-run ITEM-014 implementation script"
echo ""
echo "Log: $LOG_FILE"
echo "============================================================================"
