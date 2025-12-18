#!/bin/bash
echo "Extracting beginner book data..."
grep -i "beginner" extraction_full.log | grep "Processing:" | while read line; do
    filename=$(echo "$line" | sed 's/.*Processing: //')
    # Get the next 10 lines after this processing line and find "Extracted X diagrams"
    grep -A 10 "Processing: $filename" extraction_full.log | grep "Extracted.*diagrams" | head -1 | sed "s/^/$filename|/"
done | sed 's/INFO - //' | sed 's/Extracted //' | sed 's/ diagrams.*//' | sed 's/ to \/.*$//'
