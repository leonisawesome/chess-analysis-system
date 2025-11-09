#!/bin/bash
# Convert .mobi files to EPUB format using Calibre

MOBI_DIR="/Volumes/T7 Shield/books/epub"
LOG_FILE="mobi_conversion.log"

echo "🔄 MOBI → EPUB Batch Conversion" | tee "$LOG_FILE"
echo "================================" | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"

# Count total files first
total=$(find "$MOBI_DIR" -name "*.mobi" -type f ! -name "._*" 2>/dev/null | wc -l | tr -d ' ')
success_count=0
fail_count=0

echo "📊 Found $total .mobi files to convert" | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"

# Use while read to handle spaces in filenames
find "$MOBI_DIR" -name "*.mobi" -type f ! -name "._*" 2>/dev/null | while IFS= read -r mobi_file; do
    # Generate EPUB filename (same name, different extension)
    epub_file="${mobi_file%.mobi}.epub"

    # Skip if EPUB already exists
    if [ -f "$epub_file" ]; then
        echo "⏭️  Skipping (EPUB exists): $(basename "$mobi_file")" | tee -a "$LOG_FILE"
        ((success_count++))
        continue
    fi

    echo "🔄 Converting ($((success_count + fail_count + 1))/$total): $(basename "$mobi_file")" | tee -a "$LOG_FILE"

    # Convert using ebook-convert
    if ebook-convert "$mobi_file" "$epub_file" >> "$LOG_FILE" 2>&1; then
        echo "✅ Success: $(basename "$epub_file")" | tee -a "$LOG_FILE"
        ((success_count++))
    else
        echo "❌ Failed: $(basename "$mobi_file")" | tee -a "$LOG_FILE"
        ((fail_count++))
    fi

    echo "" | tee -a "$LOG_FILE"
done

echo "================================" | tee -a "$LOG_FILE"
echo "📊 CONVERSION SUMMARY" | tee -a "$LOG_FILE"
echo "================================" | tee -a "$LOG_FILE"
echo "Total files: $total" | tee -a "$LOG_FILE"
echo "Successful: $success_count" | tee -a "$LOG_FILE"
echo "Failed: $fail_count" | tee -a "$LOG_FILE"
echo "================================" | tee -a "$LOG_FILE"
