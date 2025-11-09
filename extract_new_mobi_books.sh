#!/bin/bash
# Extract diagrams from 41 newly converted EPUB files

EPUB_DIR="/Volumes/T7 Shield/books/epub"
TEMP_DIR="/tmp/mobi_converted_epubs"
OUTPUT_DIR="/Volumes/T7 Shield/books/images"
LIST_FILE="mobi_converted_epubs.txt"

echo "Creating temp directory..."
mkdir -p "$TEMP_DIR"

echo "Copying 41 EPUB files..."
count=0
while IFS= read -r epub_filename; do
    if [ -f "$EPUB_DIR/$epub_filename" ]; then
        cp "$EPUB_DIR/$epub_filename" "$TEMP_DIR/"
        ((count++))
        echo "  Copied ($count): $epub_filename"
    else
        echo "  NOT FOUND: $epub_filename"
    fi
done < "$LIST_FILE"

echo ""
echo "Total files copied: $count"
echo ""

if [ $count -gt 0 ]; then
    echo "Starting diagram extraction..."
    python3 extract_epub_diagrams.py \
        --epub-dir "$TEMP_DIR" \
        --output-dir "$OUTPUT_DIR" \
        --metadata-file diagram_metadata_full.json

    echo ""
    echo "Cleaning up temp directory..."
    rm -rf "$TEMP_DIR"
    echo "Done!"
else
    echo "No files to process!"
fi
