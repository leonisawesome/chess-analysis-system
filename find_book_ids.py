#!/usr/bin/env python3
import hashlib

files_to_delete = [
    "pavlovic_2017_reloaded_weapons_in_the_benoni_thinkers.epub",
    "tan_0000_1e4_the_chess_bible.epub"
]

for filename in files_to_delete:
    book_id = f"book_{hashlib.md5(filename.encode()).hexdigest()[:12]}"
    print(f"{filename}")
    print(f"  book_id: {book_id}")
    print()
