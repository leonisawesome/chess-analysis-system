#!/usr/bin/env python3
"""
PGN Game Analysis and Chunking Script

Parses PGN files containing chess games and creates chunks suitable for RAG.
Implements the unanimous baseline approach from 4-AI consultation:
- Full game chunks with rich metadata
- Preserve course hierarchy (when available)
- Minimal filtering
- Include all variations

Usage:
    python analyze_pgn_games.py <pgn_directory> [--output chunks.json]
    python analyze_pgn_games.py /Users/leon/Downloads/ZListo --output pgn_chunks.json
"""

import chess.pgn
import json
import argparse
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import io


class PGNAnalyzer:
    """Analyzes PGN files and creates RAG-ready chunks."""

    def __init__(self):
        self.stats = {
            "files_processed": 0,
            "files_failed": 0,
            "games_processed": 0,
            "games_failed": 0,
            "chunks_created": 0,
            "total_tokens_estimated": 0,
            "source_types": {},
            "errors": []
        }

    def parse_directory(self, directory: Path) -> List[Dict]:
        """Parse all PGN files in a directory."""
        chunks = []
        pgn_files = sorted(directory.glob("*.pgn"))

        print(f"\n{'='*80}")
        print(f"Parsing {len(pgn_files)} PGN files from: {directory}")
        print(f"{'='*80}\n")

        for pgn_file in pgn_files:
            print(f"Processing: {pgn_file.name}")
            file_chunks = self._parse_file(pgn_file)
            chunks.extend(file_chunks)
            print(f"  → {len(file_chunks)} games extracted\n")

        return chunks

    def _parse_file(self, filepath: Path) -> List[Dict]:
        """Parse a single PGN file."""
        chunks = []

        # Try different encodings
        encodings = ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']
        content = None

        for encoding in encodings:
            try:
                with open(filepath, 'r', encoding=encoding) as f:
                    content = f.read()
                break
            except UnicodeDecodeError:
                continue

        if content is None:
            self.stats["files_failed"] += 1
            self.stats["errors"].append(f"Could not decode {filepath.name}")
            return chunks

        # Parse games from the file content
        pgn_io = io.StringIO(content)
        game_num = 0

        while True:
            try:
                game = chess.pgn.read_game(pgn_io)
                if game is None:
                    break

                game_num += 1
                chunk = self._create_chunk(game, filepath.name, game_num)

                if chunk:
                    chunks.append(chunk)
                    self.stats["games_processed"] += 1
                    self.stats["chunks_created"] += 1
                else:
                    self.stats["games_failed"] += 1

            except Exception as e:
                self.stats["games_failed"] += 1
                # Don't stop on individual game errors, continue parsing
                continue

        self.stats["files_processed"] += 1
        return chunks

    def _create_chunk(self, game: chess.pgn.Game, filename: str, game_num: int) -> Optional[Dict]:
        """Create a RAG chunk from a PGN game."""

        # Extract metadata
        metadata = self._extract_metadata(game, filename, game_num)

        # Create chunk text with breadcrumb header
        chunk_text = self._create_chunk_text(game, metadata)

        # Estimate tokens (rough: 1 token ≈ 4 characters)
        token_estimate = len(chunk_text) // 4
        self.stats["total_tokens_estimated"] += token_estimate

        # Track source types
        source_type = metadata.get("source_type", "unknown")
        self.stats["source_types"][source_type] = self.stats["source_types"].get(source_type, 0) + 1

        return {
            "chunk_id": f"{Path(filename).stem}_game_{game_num}",
            "text": chunk_text,
            "metadata": metadata,
            "token_estimate": token_estimate
        }

    def _extract_metadata(self, game: chess.pgn.Game, filename: str, game_num: int) -> Dict:
        """Extract metadata from PGN headers."""
        headers = game.headers

        # Detect source type from Event header or filename
        event = headers.get("Event", "")
        source_type = self._detect_source_type(event, filename)

        # Extract course structure (Modern Chess format uses White/Black for chapters)
        course_name = event if event else filename.replace(".pgn", "")
        chapter = headers.get("White", "")
        section = headers.get("Black", "")

        # Determine game role
        game_role = self._determine_game_role(chapter, section, game)

        metadata = {
            # Source identification (for audit trail)
            "source_type": source_type,
            "source_file": filename,
            "game_number": game_num,  # Game number within the file
            "course_name": course_name,

            # Course hierarchy (if applicable)
            "chapter": chapter if chapter and chapter not in ["?", "Introduction"] else None,
            "section": section if section and section not in ["?"] else None,
            "game_role": game_role,

            # Standard game metadata
            "event": event,
            "site": headers.get("Site"),
            "date": headers.get("Date"),
            "round": headers.get("Round"),
            "white": headers.get("White"),
            "black": headers.get("Black"),
            "result": headers.get("Result"),
            "white_elo": headers.get("WhiteElo"),
            "black_elo": headers.get("BlackElo"),

            # Opening information
            "eco": headers.get("ECO"),
            "opening": headers.get("Opening"),

            # Custom headers (course-specific)
            "annotator": headers.get("Annotator"),
            "game_id": headers.get("GameId"),
            "source_version_date": headers.get("SourceVersionDate"),

            # Content flags
            "has_annotations": self._has_annotations(game),
            "has_variations": self._has_variations(game),
        }

        # Remove None values
        metadata = {k: v for k, v in metadata.items() if v is not None}

        return metadata

    def _detect_source_type(self, event: str, filename: str) -> str:
        """Detect source type from event name or filename."""
        text = (event + " " + filename).lower()

        if "modern chess" in text or "mcm" in text:
            return "modern_chess_course"
        elif "chessable" in text:
            return "chessable_course"
        elif "mega" in text and "database" in text:
            return "mega_database"
        elif "powerbase" in text:
            return "powerbase"
        elif "magazine" in text or "cbm" in text:
            return "chessbase_magazine"
        elif "theory" in text and "update" in text:
            return "theory_update"
        else:
            return "course_material"  # Generic course

    def _determine_game_role(self, chapter: str, section: str, game: chess.pgn.Game) -> str:
        """Determine the role of this game in the course."""
        # Check if it's an introduction/overview
        if any(x in (chapter + section).lower() for x in ["introduction", "welcome", "quickstart"]):
            return "introduction"

        # Check if heavily annotated
        if self._has_annotations(game):
            # Count comment depth
            comment_count = str(game).count("{")
            if comment_count > 10:
                return "key_annotated"

        # Default to model game
        return "model_game"

    def _has_annotations(self, game: chess.pgn.Game) -> bool:
        """Check if game has annotations/comments."""
        return "{" in str(game)

    def _has_variations(self, game: chess.pgn.Game) -> bool:
        """Check if game has variations."""
        return "(" in str(game)

    def _create_chunk_text(self, game: chess.pgn.Game, metadata: Dict) -> str:
        """Create the chunk text with breadcrumb header and full PGN."""
        lines = []

        # Breadcrumb header (for embedding)
        breadcrumb = self._create_breadcrumb(metadata)
        lines.append(breadcrumb)
        lines.append("")

        # Game summary
        summary = self._create_summary(metadata, game)
        lines.append(summary)
        lines.append("")

        # Full PGN with moves and annotations
        lines.append("PGN:")
        lines.append(str(game))

        return "\n".join(lines)

    def _create_breadcrumb(self, metadata: Dict) -> str:
        """Create breadcrumb navigation string."""
        parts = []

        # Source type
        source_type = metadata.get("source_type", "").replace("_", " ").title()
        parts.append(f"Source: {source_type}")

        # Course name
        if metadata.get("course_name"):
            parts.append(f"Course: {metadata['course_name']}")

        # Chapter
        if metadata.get("chapter"):
            parts.append(f"Chapter: {metadata['chapter']}")

        # Section
        if metadata.get("section"):
            parts.append(f"Section: {metadata['section']}")

        # Role
        if metadata.get("game_role"):
            role = metadata['game_role'].replace("_", " ").title()
            parts.append(f"Role: {role}")

        return " ▸ ".join(parts)

    def _create_summary(self, metadata: Dict, game: chess.pgn.Game) -> str:
        """Create summary line with key game info."""
        parts = []

        # Players (if actual players, not chapter names)
        white = metadata.get("white", "")
        black = metadata.get("black", "")

        # Only include player names if they look like real names (not chapters)
        if white and black and not any(x in white.lower() for x in ["chapter", "introduction", "line"]):
            white_elo = f" ({metadata.get('white_elo')})" if metadata.get('white_elo') else ""
            black_elo = f" ({metadata.get('black_elo')})" if metadata.get('black_elo') else ""
            parts.append(f"Game: {white}{white_elo} vs {black}{black_elo}")

        # Opening
        if metadata.get("eco") or metadata.get("opening"):
            eco = metadata.get("eco", "")
            opening = metadata.get("opening", "")
            parts.append(f"Opening: {eco} {opening}".strip())

        # Event (if different from course name)
        event = metadata.get("event", "")
        course = metadata.get("course_name", "")
        if event and event != course:
            parts.append(f"Event: {event}")

        # Date
        if metadata.get("date"):
            parts.append(f"Date: {metadata['date']}")

        # Result
        if metadata.get("result"):
            parts.append(f"Result: {metadata['result']}")

        # Content flags
        flags = []
        if metadata.get("has_annotations"):
            flags.append("annotated")
        if metadata.get("has_variations"):
            flags.append("variations")
        if flags:
            parts.append(f"Content: {', '.join(flags)}")

        return " | ".join(parts) if parts else "Game details not available"

    def print_stats(self):
        """Print processing statistics."""
        print(f"\n{'='*80}")
        print("PROCESSING STATISTICS")
        print(f"{'='*80}")
        print(f"Files processed: {self.stats['files_processed']}")
        print(f"Files failed: {self.stats['files_failed']}")
        print(f"Games processed: {self.stats['games_processed']}")
        print(f"Games failed: {self.stats['games_failed']}")
        print(f"Chunks created: {self.stats['chunks_created']}")
        print(f"Estimated tokens: {self.stats['total_tokens_estimated']:,}")
        print(f"Estimated cost: ${self.stats['total_tokens_estimated'] * 0.02 / 1_000_000:.4f}")

        if self.stats["source_types"]:
            print(f"\nSource type distribution:")
            for source_type, count in sorted(self.stats["source_types"].items(), key=lambda x: x[1], reverse=True):
                print(f"  {source_type}: {count}")

        if self.stats["errors"]:
            print(f"\nErrors ({len(self.stats['errors'])}):")
            for error in self.stats["errors"][:10]:  # Show first 10
                print(f"  - {error}")

        print(f"{'='*80}\n")


def main():
    parser = argparse.ArgumentParser(description="Parse PGN files and create RAG chunks")
    parser.add_argument("directory", type=str, help="Directory containing PGN files")
    parser.add_argument("--output", type=str, default="pgn_chunks.json", help="Output JSON file")
    parser.add_argument("--sample", type=int, help="Only show sample chunks (don't save)")

    args = parser.parse_args()

    # Validate directory
    directory = Path(args.directory)
    if not directory.exists() or not directory.is_dir():
        print(f"Error: {args.directory} is not a valid directory")
        sys.exit(1)

    # Parse PGN files
    analyzer = PGNAnalyzer()
    chunks = analyzer.parse_directory(directory)

    # Print statistics
    analyzer.print_stats()

    # Show sample chunks
    if args.sample and chunks:
        print(f"\n{'='*80}")
        print(f"SAMPLE CHUNKS (showing first {min(args.sample, len(chunks))})")
        print(f"{'='*80}\n")

        for i, chunk in enumerate(chunks[:args.sample], 1):
            print(f"--- Chunk {i} ---")
            print(f"ID: {chunk['chunk_id']}")
            print(f"Tokens: ~{chunk['token_estimate']}")
            print(f"\nText preview (first 500 chars):")
            print(chunk['text'][:500])
            print("...\n")
            print(f"Metadata: {json.dumps(chunk['metadata'], indent=2)}\n")

    # Save output
    if not args.sample:
        output_file = Path(args.output)
        with open(output_file, 'w') as f:
            json.dump({
                "chunks": chunks,
                "stats": analyzer.stats,
                "created_at": datetime.now().isoformat()
            }, f, indent=2)

        print(f"✅ Saved {len(chunks)} chunks to: {output_file}")
        print(f"   Total size: {output_file.stat().st_size / 1024 / 1024:.2f} MB")


if __name__ == "__main__":
    main()
