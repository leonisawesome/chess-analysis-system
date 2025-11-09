#!/usr/bin/env python3
"""
Remove low-quality books (with few diagrams) from the system.
- Deletes chunks from Qdrant
- Removes EPUB files
- Removes extracted diagram directories
"""

import sys
from pathlib import Path
from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue

# Book IDs to remove
BOOK_IDS_TO_REMOVE = [
    "book_8b3491e03ca7",  # arthur - UNKNOWN (16 diagrams)
    "book_54c6e4396c84",  # The Grandmaster (7 diagrams)
    "book_49ab5147b8c2",  # The KGB Plays Chess (20 diagrams)
    "book_3cf933618961",  # Deep Thinking (5 diagrams)
    "book_d97ab51fc39f",  # The Death of Dr. Alekhine (2 diagrams)
    "book_282f553f6bed",  # Birth of the Chess Queen (29 diagrams)
    "book_6446f2f841cf",  # The Moves That Matter (1 diagram)
    "book_a0779640f628",  # The KGB Plays Chess #2 (19 diagrams)
    "book_253564c88323",  # Chess for Educators (12 diagrams)
]

EPUB_FILES_TO_REMOVE = [
    "unknown_author_0000_the_moves_that_matter_a_chess_grandmaster.epub",
    "toon_2013_the_death_of_dr_alekhine_authorhouse.epub",
    "kasparov_0000_deep_thinking.epub",
    "brinjonathan_0000_the_grandmaster_magnus_carlsen_and_the_match_that_made_chess_great_again.epub",
    "unknown_author_2021_karel_van_delft_chess_for_educators_how_to_organize_and_promote_a_meaningful_chess_teaching_program_new_in_chess.epub",
    "arthur_0000_chess_for_beginners_the_complete_guide_to_learn_the_rules_and_how_to_apply_the_right_strategiesit_includes_strong_openings_and_powerful_tactics.epub",
    "unknown_author_2010_boris_gulko_yuri_felshtinsky_vladimir_popov_viktor_kortschnoi_the_kgb_plays_chess_the_soviet_secret_police_and_the_fight_for_the_world_chess_crown_russell_enterprises_inc.epub",
    "felshtinsky_0000_the_kgb_plays_chess.epub",
    "unknown_author_0000_birth_of_the_chess_queen.epub"
]

EPUB_DIR = Path("/Volumes/T7 Shield/books/epub")
IMAGES_DIR = Path("/Volumes/T7 Shield/books/images")

def remove_from_qdrant():
    """Remove chunks from Qdrant for specified book IDs."""
    print("🗑️  Removing chunks from Qdrant...\n")

    client = QdrantClient(host="localhost", port=6333)
    collection_name = "chess_production"

    total_deleted = 0

    for book_id in BOOK_IDS_TO_REMOVE:
        # Count chunks first
        count_result = client.count(
            collection_name=collection_name,
            count_filter=Filter(
                must=[FieldCondition(key="book_id", match=MatchValue(value=book_id))]
            )
        )

        chunks_count = count_result.count

        if chunks_count > 0:
            # Delete chunks
            client.delete(
                collection_name=collection_name,
                points_selector=Filter(
                    must=[FieldCondition(key="book_id", match=MatchValue(value=book_id))]
                )
            )
            print(f"✅ Deleted {chunks_count} chunks for book_id: {book_id}")
            total_deleted += chunks_count
        else:
            print(f"⚠️  No chunks found for book_id: {book_id}")

    print(f"\n📊 Total chunks deleted from Qdrant: {total_deleted}\n")
    return total_deleted

def remove_epub_files():
    """Remove EPUB files from disk."""
    print("🗑️  Removing EPUB files...\n")

    removed_count = 0

    for filename in EPUB_FILES_TO_REMOVE:
        file_path = EPUB_DIR / filename

        if file_path.exists():
            file_path.unlink()
            print(f"✅ Removed: {filename}")
            removed_count += 1
        else:
            print(f"⚠️  Not found: {filename}")

    print(f"\n📊 Total EPUB files removed: {removed_count}\n")
    return removed_count

def remove_image_directories():
    """Remove extracted diagram directories."""
    print("🗑️  Removing extracted diagram directories...\n")

    removed_count = 0

    for book_id in BOOK_IDS_TO_REMOVE:
        dir_path = IMAGES_DIR / book_id

        if dir_path.exists():
            import shutil
            shutil.rmtree(dir_path)
            print(f"✅ Removed directory: {book_id}")
            removed_count += 1
        else:
            print(f"⚠️  Directory not found: {book_id}")

    print(f"\n📊 Total image directories removed: {removed_count}\n")
    return removed_count

def main():
    print("="*80)
    print("REMOVING LOW-QUALITY BOOKS")
    print("="*80)
    print(f"Books to remove: {len(BOOK_IDS_TO_REMOVE)}\n")

    # Step 1: Remove from Qdrant
    chunks_deleted = remove_from_qdrant()

    # Step 2: Remove EPUB files
    epubs_removed = remove_epub_files()

    # Step 3: Remove image directories
    dirs_removed = remove_image_directories()

    # Summary
    print("="*80)
    print("REMOVAL COMPLETE")
    print("="*80)
    print(f"Qdrant chunks deleted: {chunks_deleted}")
    print(f"EPUB files removed: {epubs_removed}")
    print(f"Image directories removed: {dirs_removed}")
    print("="*80)

if __name__ == "__main__":
    main()
