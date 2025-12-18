#!/usr/bin/env python3
"""
Convenience wrapper for the game-level deduper in `chess_rag_system`.

Usage:
  python scripts/pgn/dedupe_massive_pgn.py /path/to/big.pgn --output-dir dedup_chunks
"""

from __future__ import annotations

from chess_rag_system.dedupe_massive_pgn import main


if __name__ == "__main__":
    raise SystemExit(main())

