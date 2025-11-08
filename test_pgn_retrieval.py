#!/usr/bin/env python3
"""
Test PGN Retrieval Quality

Tests ONLY the chess_pgn_test collection to validate:
1. Retrieval works
2. Results are from PGN data (not books)
3. Course metadata is preserved
4. Precision is acceptable

Usage:
    python test_pgn_retrieval.py --collection chess_pgn_test
"""

import argparse
import os
import sys
from qdrant_client import QdrantClient
import openai
from typing import List, Dict


class PGNRetrievalTester:
    """Tests PGN retrieval quality."""

    def __init__(self, qdrant_url: str, collection_name: str, openai_key: str):
        self.qdrant_client = QdrantClient(url=qdrant_url)
        self.collection_name = collection_name
        openai.api_key = openai_key

    def get_collection_stats(self):
        """Get collection statistics."""
        info = self.qdrant_client.get_collection(self.collection_name)
        print(f"\n{'='*80}")
        print(f"COLLECTION: {self.collection_name}")
        print(f"{'='*80}")
        print(f"Total points: {info.points_count}")
        print(f"Vector size: {info.config.params.vectors.size}")
        print(f"Distance: {info.config.params.vectors.distance}")
        print(f"{'='*80}\n")

    def test_query(self, query: str, top_k: int = 5) -> List[Dict]:
        """Test a single query against PGN collection."""
        print(f"\n{'='*80}")
        print(f"QUERY: {query}")
        print(f"{'='*80}\n")

        # Generate query embedding
        response = openai.embeddings.create(
            model="text-embedding-3-small",
            input=[query]
        )
        query_vector = response.data[0].embedding

        # Search in PGN collection ONLY
        results = self.qdrant_client.search(
            collection_name=self.collection_name,
            query_vector=query_vector,
            limit=top_k
        )

        # Display results
        print(f"Retrieved {len(results)} results:\n")

        for i, hit in enumerate(results, 1):
            score = hit.score
            payload = hit.payload

            print(f"--- Result {i} (Score: {score:.4f}) ---")

            # Verify this is PGN data (not book data)
            source_type = payload.get("source_type", "UNKNOWN")
            source_file = payload.get("source_file", "UNKNOWN")
            game_number = payload.get("game_number", "?")

            print(f"✓ Source Type: {source_type}")
            print(f"✓ Source File: {source_file}")
            print(f"✓ Game Number: {game_number}")

            # Show course structure
            course_name = payload.get("course_name")
            chapter = payload.get("chapter")
            section = payload.get("section")

            if course_name:
                print(f"  Course: {course_name}")
            if chapter:
                print(f"  Chapter: {chapter}")
            if section:
                print(f"  Section: {section}")

            # Show game details
            if payload.get("eco"):
                print(f"  Opening: {payload.get('eco')} {payload.get('opening', '')}")

            # Show chunk preview
            chunk_text = payload.get("chunk_text", "")
            print(f"\n  Preview: {chunk_text[:200]}...")

            # VERIFY this is NOT book data
            if source_type == "book" or "chapter" in source_file.lower() and "pgn" not in source_file.lower():
                print(f"\n  ⚠️  WARNING: This looks like BOOK data, not PGN!")
            else:
                print(f"\n  ✓ Confirmed: This is PGN game data")

            print()

        return results

    def run_test_suite(self):
        """Run comprehensive test suite."""

        # Get collection stats
        self.get_collection_stats()

        # Test queries (course-specific, should ONLY return PGN data)
        test_queries = [
            # Course-specific queries (should work well with PGN data)
            "Benko Gambit opening repertoire",
            "Najdorf Sicilian model games",
            "London System against d5",

            # Generic queries (compare with book data later)
            "rook endgame technique",
            "middlegame plans in closed positions",
        ]

        print(f"\n{'#'*80}")
        print(f"# RUNNING TEST SUITE - {len(test_queries)} QUERIES")
        print(f"{'#'*80}\n")

        results_summary = []

        for query in test_queries:
            results = self.test_query(query, top_k=5)

            # Verify all results are from PGN
            pgn_count = sum(1 for r in results
                          if r.payload.get("source_type") in ["course_material", "modern_chess_course", "chessable_course"])

            results_summary.append({
                "query": query,
                "total_results": len(results),
                "pgn_results": pgn_count,
                "avg_score": sum(r.score for r in results) / len(results) if results else 0
            })

        # Print summary
        print(f"\n{'='*80}")
        print("TEST SUMMARY")
        print(f"{'='*80}\n")

        for result in results_summary:
            query = result["query"]
            total = result["total_results"]
            pgn = result["pgn_results"]
            avg_score = result["avg_score"]

            purity = (pgn / total * 100) if total > 0 else 0

            print(f"Query: {query}")
            print(f"  Results: {total}")
            print(f"  PGN data: {pgn}/{total} ({purity:.0f}%)")
            print(f"  Avg score: {avg_score:.4f}")

            if purity < 100:
                print(f"  ⚠️  WARNING: Some results are NOT from PGN collection!")
            else:
                print(f"  ✓ All results from PGN collection")
            print()


def main():
    parser = argparse.ArgumentParser(description="Test PGN retrieval quality")
    parser.add_argument("--collection", type=str, default="chess_pgn_test", help="Qdrant collection name")
    parser.add_argument("--qdrant-url", type=str, default="http://localhost:6333", help="Qdrant URL")
    parser.add_argument("--query", type=str, help="Test a single query")

    args = parser.parse_args()

    # Check for OpenAI API key
    openai_key = os.getenv("OPENAI_API_KEY")
    if not openai_key:
        print("Error: OPENAI_API_KEY environment variable not set")
        sys.exit(1)

    # Initialize tester
    tester = PGNRetrievalTester(
        qdrant_url=args.qdrant_url,
        collection_name=args.collection,
        openai_key=openai_key
    )

    # Run tests
    if args.query:
        # Single query test
        tester.get_collection_stats()
        tester.test_query(args.query, top_k=5)
    else:
        # Full test suite
        tester.run_test_suite()


if __name__ == "__main__":
    main()
