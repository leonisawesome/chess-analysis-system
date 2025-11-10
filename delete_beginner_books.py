#!/usr/bin/env python3
"""
Delete all beginner books from disk, images, and Qdrant.
"""
import hashlib
import subprocess
from pathlib import Path
from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue

# Books to delete
books_to_delete = [
    "alberston_2007_51_chess_openings_for_beginners_cardoza.epub",
    "cicero_2017_checkmate_exercises_for_beginners_sampler_edition.epub",
    "cicero_2018_checkmate_exercises_from_beginner_to_winner1.epub",
    "cicero_2019_checkmate_exercises_from_beginner_to_winner2.epub",
    "curtis_0000_chess_4_books_in_1_getting_started_from_a_beginner_learn_successful_openings_develop_advanced_strategy_and_win_your_games.epub",
    "geller_2000_check_and_mate_a_beginners_guide_with_examples.epub",
    "ingram_2016_chess_the_complete_beginner_s_guide_createspace_independent.epub",
    "jack_0000_chess_for_beginners_learn_the_wonderful_game_of_the_chess_board_with_strategies_rules_and_techniques_to_win_easily.epub",
    "lars_0000_chess_for_beginners_the_ultimate_guide_to_understanding_chess.epub",
    "levy_2023_how_to_win_at_chess_the_ultimate_guide_for_beginners_and_beyond_ten_speed_press.epub",
    "srokovski_0000_chess_training_for_postbeginners.epub",
    "tommy_0000_chess_openings_for_beginners_the_complete_manual_to_learn_the_fundamentals_the_strategy_and_the_best_moves_at_the_start_of_the_game.epub",
    "unknown_author_0000_chess_exercises_for_beginners_the_tactics_workbook_that_explains.epub",
    "unknown_author_0000_chess_the_ultimate_guide_for_beginners_a_comprehensive_and_simplified.epub",
    "unknown_author_0000_henry_bird_edward_lasker_josé_raul_capablanca_chess_strategy_a_complete_guide_for_beginners_to_chess_fundamentals.epub",
]

epub_dir = Path("/Volumes/T7 Shield/books/epub")
images_dir = Path("/Volumes/T7 Shield/books/images")

print("=" * 80)
print("DELETING BEGINNER BOOKS")
print("=" * 80)
print(f"Total books to delete: {len(books_to_delete)}\n")

# Connect to Qdrant with longer timeout
client = QdrantClient(host="localhost", port=6333, timeout=300)

total_epub_deleted = 0
total_images_deleted = 0
total_chunks_deleted = 0

for i, filename in enumerate(books_to_delete, 1):
    print(f"\n[{i}/{len(books_to_delete)}] {filename}")

    # Generate book_id
    book_id = f"book_{hashlib.md5(filename.encode()).hexdigest()[:12]}"

    # 1. Delete EPUB file
    epub_path = epub_dir / filename
    if epub_path.exists():
        epub_path.unlink()
        print(f"  ✓ Deleted EPUB")
        total_epub_deleted += 1
    else:
        print(f"  ℹ EPUB not found")

    # 2. Delete image directory
    image_path = images_dir / book_id
    if image_path.exists():
        subprocess.run(['rm', '-rf', str(image_path)], check=True)
        print(f"  ✓ Deleted images ({book_id})")
        total_images_deleted += 1
    else:
        print(f"  ℹ No image directory")

    # 3. Delete from Qdrant
    try:
        count_result = client.count(
            collection_name="chess_production",
            count_filter=Filter(
                must=[FieldCondition(key="book_name", match=MatchValue(value=filename))]
            )
        )

        if count_result.count > 0:
            print(f"  Deleting {count_result.count} chunks from Qdrant...")
            client.delete(
                collection_name="chess_production",
                points_selector=Filter(
                    must=[FieldCondition(key="book_name", match=MatchValue(value=filename))]
                )
            )

            # Verify
            verify = client.count(
                collection_name="chess_production",
                count_filter=Filter(
                    must=[FieldCondition(key="book_name", match=MatchValue(value=filename))]
                )
            )

            if verify.count == 0:
                print(f"  ✓ Deleted {count_result.count} chunks (verified)")
                total_chunks_deleted += count_result.count
            else:
                print(f"  ⚠ WARNING: {verify.count} chunks still remain!")
        else:
            print(f"  ℹ No Qdrant chunks")
    except Exception as e:
        print(f"  ✗ Qdrant error: {e}")

print(f"\n{'=' * 80}")
print(f"DELETION SUMMARY")
print(f"{'=' * 80}")
print(f"EPUB files deleted: {total_epub_deleted}")
print(f"Image directories deleted: {total_images_deleted}")
print(f"Qdrant chunks deleted: {total_chunks_deleted}")

# Get final counts
try:
    final_count = client.count(collection_name="chess_production")
    print(f"\nFinal Qdrant collection size: {final_count.count:,} chunks")
except Exception as e:
    print(f"Could not get final count: {e}")

# Count remaining EPUBs
remaining_epubs = len(list(epub_dir.glob("*.epub")))
print(f"Remaining EPUB files: {remaining_epubs}")
