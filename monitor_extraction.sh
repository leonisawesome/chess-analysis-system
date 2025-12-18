#!/bin/bash
# Monitor EPUB diagram extraction progress

echo "📊 EPUB Diagram Extraction Monitor"
echo "===================================="
echo ""

while true; do
    clear
    echo "📊 EPUB Diagram Extraction Monitor"
    echo "===================================="
    echo ""

    # Check if process is running
    if ps aux | grep -v grep | grep "extract_epub_diagrams.py" > /dev/null; then
        echo "✅ Status: RUNNING"
    else
        echo "⏹️  Status: STOPPED or COMPLETE"
    fi

    echo ""
    echo "📈 Progress:"
    tail -1 extraction_full.log | grep -o "Extracting diagrams:.*" || echo "Initializing..."

    echo ""
    echo "📁 Books Processed:"
    book_count=$(ls "/Volumes/T7 Shield/rag/books/images" 2>/dev/null | wc -l | tr -d ' ')
    echo "   $book_count book directories created"

    echo ""
    echo "💾 Storage Used:"
    du -sh "/Volumes/T7 Shield/rag/books/images" 2>/dev/null || echo "   Calculating..."

    echo ""
    echo "🔄 Latest Activity:"
    tail -5 extraction_full.log | grep -E "INFO - Processing:|INFO -   Extracted"

    echo ""
    echo "Press Ctrl+C to exit monitor (extraction continues in background)"
    echo "-------------------------------------------------------------------"

    sleep 5
done
