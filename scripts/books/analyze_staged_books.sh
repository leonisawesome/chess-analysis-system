#!/usr/bin/env bash
# Run the canonical EPUB analyzer against the staging directory.
# Ensures every file in /Volumes/T7 Shield/rag/books/epub/1new ends up in epub_analysis.db.

set -euo pipefail

STAGING_DIR="/Volumes/T7 Shield/rag/books/epub/1new"
DB_PATH="epub_analysis.db"

if [[ ! -d "$STAGING_DIR" ]]; then
  echo "❌ Staging directory not found: $STAGING_DIR"
  exit 1
fi

echo "📚 Running analyzer on staged books..."
echo "   Source : $STAGING_DIR"
echo "   DB     : $DB_PATH"

python batch_process_epubs.py "$STAGING_DIR" "$DB_PATH"

echo "✅ Analyzer complete. Review scores in $DB_PATH (table: epub_analysis)."
