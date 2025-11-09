#!/usr/bin/env python3
"""
Remove batch 2 of low-quality books and duplicates
"""

import sys
import shutil
from pathlib import Path
from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue

# Book IDs to remove
BOOK_IDS_TO_REMOVE = [
    ("book_0f56dfe4dd16", "How To Play Chess (53 diagrams)"),
    ("book_aee798f2844b", "A History of Chess (42 diagrams)"),
    ("book_ba02c116f920", "Chess Opening For Beginners (35 diagrams)"),
    ("book_6420e06da869", "Chess For Beginners - Fabiano (63 diagrams)"),
    ("book_380e3b10b9ea", "Chess Queens (62 diagrams)"),
    ("book_a02f51ac184b", "How to Reassess Your Chess - DUPLICATE (875 diagrams)"),
    ("book_525b3ec84add", "Paul Morphy: The Pride and Sorrow (49 diagrams)"),
    ("book_722dfb21df8b", "Chess for Beginners - Samuel (30 diagrams)"),
]

EPUB_FILES_TO_REMOVE = [
    "samuel_0000_chess_for_beginners_the_original_stepbystep_guide_to_learn_everything_about_chess.epub",
    "chester_0000_chess_opening_for_beginners_the_complete_guide_to_chess_openings_tactics_and_strategies_to_become_a_grandmaster_of_chess.epub",
    "averbakh_2012_a_history_of_chess_from_chaturanga_to_the_present_day_russell.epub",
    "lawson_2014_paul_morphy_the_pride_and_sorrow_of_chess_university_of_louisiana_at_lafayette_press.epub",
    "alexander_0000_how_to_play_chess_the_effective_winning_guide.epub",
    "jennifer_2022_chess_queens_hodder_stoughton.epub",
    "fabiano_0000_chess_for_beginners_a_complete_guide_to_lead_you_to_victory_chess_fundamentals_rules_strategies_and_secrets_for_the_success_of_every_game.epub",
    "jeremy_2010_how_to_reassess_your_chess_fourth_edition_siles_press.epub"
]

EPUB_DIR = Path("/Volumes/T7 Shield/books/epub")
IMAGES_DIR = Path("/Volumes/T7 Shield/books/images")

def remove_from_qdrant():
    """Remove chunks from Qdrant for specified book IDs."""
    print("🗑️  Removing chunks from Qdrant...\n")

    client = QdrantClient(host="localhost", port=6333)
    collection_name = "chess_production"

    total_deleted = 0

    for book_id, title in BOOK_IDS_TO_REMOVE:
        # Count chunks first
        try:
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
                print(f"✅ Deleted {chunks_count} chunks for: {title}")
                total_deleted += chunks_count
            else:
                print(f"⚠️  No chunks found for: {title}")
        except Exception as e:
            print(f"❌ Error processing {book_id}: {e}")

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

    for book_id, title in BOOK_IDS_TO_REMOVE:
        dir_path = IMAGES_DIR / book_id

        if dir_path.exists():
            shutil.rmtree(dir_path)
            print(f"✅ Removed: {title}")
            removed_count += 1
        else:
            print(f"⚠️  Not found: {book_id}")

    print(f"\n📊 Total image directories removed: {removed_count}\n")
    return removed_count

def main():
    print("="*80)
    print("REMOVING BATCH 2: LOW-QUALITY BOOKS + DUPLICATE")
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
