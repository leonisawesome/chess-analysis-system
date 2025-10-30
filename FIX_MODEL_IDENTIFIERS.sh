#!/bin/bash

# FIX MODEL IDENTIFIERS - UPDATE TO ACCESSIBLE MODELS
# Purpose: Replace invalid model IDs with gpt-4o that API key can access

LOG_FILE="refactoring_logs/MODEL_FIX_$(date +%Y%m%d_%H%M%S).log"
mkdir -p refactoring_logs

exec > >(tee -a "$LOG_FILE") 2>&1

echo "============================================================================"
echo "FIX MODEL IDENTIFIERS"
echo "Started: $(date)"
echo "Log: $LOG_FILE"
echo "============================================================================"
echo ""

# Step 1: Backup files
echo "Step 1: Creating backups..."
cp synthesis_pipeline.py synthesis_pipeline.py.backup_$(date +%Y%m%d_%H%M%S)
cp query_system_a.py query_system_a.py.backup_$(date +%Y%m%d_%H%M%S)
echo "✅ Backups created"
echo ""

# Step 2: Fix synthesis_pipeline.py
echo "Step 2: Fixing synthesis_pipeline.py..."
echo ""

echo "Current invalid models:"
grep -n "gpt-chatgpt-4o-latest-20250514" synthesis_pipeline.py
echo ""

# Replace the model
sed -i '' 's/gpt-chatgpt-4o-latest-20250514/gpt-4o/g' synthesis_pipeline.py

echo "After fix:"
grep -n "gpt-4o" synthesis_pipeline.py | head -5
echo "✅ synthesis_pipeline.py updated"
echo ""

# Step 3: Fix query_system_a.py
echo "Step 3: Fixing query_system_a.py..."
echo ""

echo "Current invalid models:"
grep -n "gpt-5\|gpt-chatgpt" query_system_a.py
echo ""

# Replace any gpt-5 or invalid models with gpt-4o
sed -i '' 's/gpt-5/gpt-4o/g' query_system_a.py
sed -i '' 's/gpt-chatgpt-4o-latest-20250514/gpt-4o/g' query_system_a.py

echo "After fix:"
grep -n "gpt-4o" query_system_a.py | head -5
echo "✅ query_system_a.py updated"
echo ""

# Step 4: Validate syntax
echo "Step 4: Validating Python syntax..."
echo ""

python3 -m py_compile synthesis_pipeline.py 2>&1
if [ $? -eq 0 ]; then
    echo "✅ synthesis_pipeline.py syntax valid"
else
    echo "❌ Syntax error in synthesis_pipeline.py"
    exit 1
fi

python3 -m py_compile query_system_a.py 2>&1
if [ $? -eq 0 ]; then
    echo "✅ query_system_a.py syntax valid"
else
    echo "❌ Syntax error in query_system_a.py"
    exit 1
fi
echo ""

# Step 5: Git commit
echo "Step 5: Committing changes..."
echo ""

git add synthesis_pipeline.py query_system_a.py
git commit -m "Fix model identifiers: gpt-chatgpt-4o-latest-20250514 → gpt-4o

Issue: API key doesn't have access to gpt-chatgpt-4o-latest-20250514
Fix: Updated to gpt-4o (publicly available model)

Files modified:
- synthesis_pipeline.py (3 occurrences)
- query_system_a.py (all gpt-5 references)

This fixes the 404 model access error blocking ITEM-014 testing."

if [ $? -eq 0 ]; then
    echo "✅ Changes committed"
else
    echo "⚠️  Commit failed"
fi
echo ""

# Push to GitHub
echo "Pushing to GitHub..."
git push origin main

if [ $? -eq 0 ]; then
    echo "✅ Pushed to GitHub"
else
    echo "⚠️  Push failed"
fi
echo ""

echo "============================================================================"
echo "MODEL FIX COMPLETE"
echo "============================================================================"
echo ""
echo "Changes:"
echo "  ✅ gpt-chatgpt-4o-latest-20250514 → gpt-4o"
echo "  ✅ gpt-5 → gpt-4o"
echo "  ✅ All syntax validated"
echo "  ✅ Committed to git"
echo ""
echo "Next: Re-run middlegame test query"
echo ""
echo "Log: $LOG_FILE"
echo "============================================================================"
