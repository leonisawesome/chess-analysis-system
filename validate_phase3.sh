#!/bin/bash

# ITEM-011 Phase 3 Validation Script
# Purpose: Verify opening_validator.py extraction completed successfully
# Expected: opening_validator.py exists, app.py reduced, system functional

LOG_FILE="refactoring_logs/PHASE_3_VALIDATION_$(date +%Y%m%d_%H%M%S).log"
mkdir -p refactoring_logs

exec > >(tee -a "$LOG_FILE") 2>&1

echo "============================================================================"
echo "ITEM-011 PHASE 3: VALIDATION CHECK"
echo "Started: $(date)"
echo "Log: $LOG_FILE"
echo "============================================================================"
echo ""

# Step 1: Check if opening_validator.py exists
echo "Step 1: Checking if opening_validator.py exists..."
if [ -f "opening_validator.py" ]; then
    LINES=$(wc -l < opening_validator.py)
    echo "✅ opening_validator.py exists ($LINES lines)"
else
    echo "❌ opening_validator.py NOT FOUND"
    echo "VALIDATION FAILED: Phase 3 extraction did not complete"
    exit 1
fi
echo ""

# Step 2: Check app.py line count
echo "Step 2: Checking app.py line count..."
if [ -f "app.py" ]; then
    APP_LINES=$(wc -l < app.py)
    echo "Current app.py: $APP_LINES lines"
    echo "(Expected: ~600-700 lines after Phase 3)"
    if [ "$APP_LINES" -gt 800 ]; then
        echo "⚠️  WARNING: app.py still has $APP_LINES lines (expected <800)"
    else
        echo "✅ app.py line count looks reasonable"
    fi
else
    echo "❌ app.py NOT FOUND"
    exit 1
fi
echo ""

# Step 3: Check that extracted functions are in opening_validator.py
echo "Step 3: Verifying extracted functions..."
REQUIRED_FUNCTIONS=(
    "validate_stage2_diagrams"
    "validate_and_fix_diagrams"
    "extract_contamination_details"
    "generate_section_with_retry"
)

for func in "${REQUIRED_FUNCTIONS[@]}"; do
    if grep -q "def $func" opening_validator.py; then
        echo "✅ Found: $func()"
    else
        echo "❌ MISSING: $func()"
        echo "VALIDATION FAILED: Required function not in opening_validator.py"
        exit 1
    fi
done
echo ""

# Step 4: Check imports in app.py
echo "Step 4: Verifying app.py imports opening_validator..."
if grep -q "from opening_validator import" app.py || grep -q "import opening_validator" app.py; then
    echo "✅ app.py imports opening_validator"
    grep "from opening_validator import\|import opening_validator" app.py | head -1
else
    echo "❌ app.py does NOT import opening_validator"
    echo "VALIDATION FAILED: Import statement missing"
    exit 1
fi
echo ""

# Step 5: Syntax check
echo "Step 5: Python syntax validation..."
python3 -m py_compile opening_validator.py 2>&1
if [ $? -eq 0 ]; then
    echo "✅ opening_validator.py syntax valid"
else
    echo "❌ opening_validator.py has syntax errors"
    exit 1
fi

python3 -m py_compile app.py 2>&1
if [ $? -eq 0 ]; then
    echo "✅ app.py syntax valid"
else
    echo "❌ app.py has syntax errors"
    exit 1
fi
echo ""

# Step 6: Check for module dependencies
echo "Step 6: Checking opening_validator.py dependencies..."
echo "Imports found in opening_validator.py:"
grep "^import \|^from " opening_validator.py | head -10
echo ""

echo "============================================================================"
echo "PHASE 3 VALIDATION SUMMARY"
echo "============================================================================"
echo "Module Status:"
echo "  opening_validator.py: ✅ EXISTS ($LINES lines)"
echo "  app.py: ✅ EXISTS ($APP_LINES lines)"
echo ""
echo "Functions Extracted:"
for func in "${REQUIRED_FUNCTIONS[@]}"; do
    echo "  - $func(): ✅"
done
echo ""
echo "Tests:"
echo "  ✅ Python syntax valid"
echo "  ✅ Module structure correct"
echo "  ✅ Import statements present"
echo ""
echo "Reduction Progress:"
echo "  Phase 1: 1,474 → 1,194 lines (-280, -19.0%)"
echo "  Phase 2: 1,194 → 1,025 lines (-169, -14.2%)"
echo "  Phase 3: 1,025 → $APP_LINES lines (-$((1025 - APP_LINES)), -$(awk "BEGIN {printf \"%.1f\", (1025-$APP_LINES)/1025*100}")%)"
echo "  Total:   1,474 → $APP_LINES lines (-$((1474 - APP_LINES)), -$(awk "BEGIN {printf \"%.1f\", (1474-$APP_LINES)/1474*100}")%)"
echo ""
echo "✅ PHASE 3 VALIDATION COMPLETE"
echo "Full logs: $LOG_FILE"
echo "============================================================================"
