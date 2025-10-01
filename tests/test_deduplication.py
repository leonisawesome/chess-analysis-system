"""Tests for the chess deduplication system."""

import unittest
from unittest.mock import MagicMock, patch
from io import StringIO
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from chess_rag_system.deduplication import ChessDeduplicator


class TestChessDeduplicator(unittest.TestCase):
    """Test cases for ChessDeduplicator."""

    def setUp(self):
        """Set up test fixtures."""
        # Sample PGN games
        self.pgn_simple = """
[Event "Test"]
[White "Player1"]
[Black "Player2"]

1. e4 e5 2. Nf3 Nc6 3. Bb5 a6 *
"""

        self.pgn_duplicate = """
[Event "Different Event"]
[White "Different"]
[Black "Players"]

1. e4 e5 2. Nf3 Nc6 3. Bb5 a6 *
"""

        self.pgn_different = """
[Event "Test"]
[White "Player1"]
[Black "Player2"]

1. d4 d5 2. c4 e6 3. Nc3 Nf6 *
"""

        self.pgn_malformed = """
This is not a valid PGN file at all
Random text that cannot be parsed
No moves here
"""

    @patch('psycopg2.connect')
    def test_normalize_game(self, mock_connect):
        """Test PGN normalization to UCI."""
        mock_conn = MagicMock()
        mock_connect.return_value = mock_conn

        dedup = ChessDeduplicator({'host': 'localhost'})

        # Test valid PGN
        normalized = dedup.normalize_game(self.pgn_simple)
        self.assertIsNotNone(normalized)
        self.assertIn('e2e4', normalized)  # UCI format
        self.assertIn('e7e5', normalized)

        # Test malformed PGN
        normalized = dedup.normalize_game(self.pgn_malformed)
        self.assertIsNone(normalized)

    @patch('psycopg2.connect')
    def test_duplicate_detection(self, mock_connect):
        """Test that duplicate games produce same hash."""
        mock_conn = MagicMock()
        mock_connect.return_value = mock_conn

        dedup = ChessDeduplicator({'host': 'localhost'})

        # Same moves should produce same normalized form
        norm1 = dedup.normalize_game(self.pgn_simple)
        norm2 = dedup.normalize_game(self.pgn_duplicate)

        self.assertEqual(norm1, norm2)

        # Same normalized form should produce same hash
        hash1 = dedup.compute_hash(norm1)
        hash2 = dedup.compute_hash(norm2)

        self.assertEqual(hash1, hash2)

    @patch('psycopg2.connect')
    def test_different_games(self, mock_connect):
        """Test that different games produce different hashes."""
        mock_conn = MagicMock()
        mock_connect.return_value = mock_conn

        dedup = ChessDeduplicator({'host': 'localhost'})

        norm1 = dedup.normalize_game(self.pgn_simple)
        norm2 = dedup.normalize_game(self.pgn_different)

        self.assertNotEqual(norm1, norm2)

        hash1 = dedup.compute_hash(norm1)
        hash2 = dedup.compute_hash(norm2)

        self.assertNotEqual(hash1, hash2)

    @patch('psycopg2.connect')
    def test_batch_processing_logic(self, mock_connect):
        """Test batch processing logic without database operations."""
        mock_conn = MagicMock()
        mock_connect.return_value = mock_conn

        dedup = ChessDeduplicator({'host': 'localhost'})

        # Test individual normalization
        games = [self.pgn_simple, self.pgn_duplicate, self.pgn_different, self.pgn_malformed]

        # Test that games normalize correctly
        norm1 = dedup.normalize_game(self.pgn_simple)
        norm2 = dedup.normalize_game(self.pgn_duplicate)
        norm3 = dedup.normalize_game(self.pgn_different)
        norm4 = dedup.normalize_game(self.pgn_malformed)

        # First two should be identical (same moves)
        self.assertEqual(norm1, norm2)
        # Third should be different
        self.assertNotEqual(norm1, norm3)
        # Fourth should be None (malformed)
        self.assertIsNone(norm4)


if __name__ == '__main__':
    unittest.main()