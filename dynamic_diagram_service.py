#!/usr/bin/env python3
"""
Dynamic Diagram Service

Generates SVG chess diagrams from FEN strings and caches them for reuse.
Used when no static EPUB diagram is available for a chunk.
"""

from __future__ import annotations

import hashlib
import json
import logging
import threading
import time
from pathlib import Path
from typing import Dict, Optional

import chess
import chess.svg

logger = logging.getLogger(__name__)

CACHE_DIR = Path("static/dynamic_diagrams")
MANIFEST_PATH = CACHE_DIR / "manifest.json"


def _ensure_cache_dir() -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)


class DynamicDiagramService:
    """Simple cache + renderer for dynamic SVG diagrams."""

    def __init__(self) -> None:
        _ensure_cache_dir()
        self.cache_dir = CACHE_DIR
        self.manifest_path = MANIFEST_PATH
        self._lock = threading.Lock()
        self.manifest: Dict[str, Dict] = {}
        self._load_manifest()

    def _load_manifest(self) -> None:
        if not self.manifest_path.exists():
            self.manifest = {}
            return
        try:
            self.manifest = json.loads(self.manifest_path.read_text())
        except Exception as exc:
            logger.warning("⚠️  Failed to load dynamic diagram manifest: %s", exc)
            self.manifest = {}

    def _save_manifest(self) -> None:
        try:
            self.manifest_path.write_text(json.dumps(self.manifest, indent=2))
        except Exception as exc:
            logger.warning("⚠️  Failed to write dynamic diagram manifest: %s", exc)

    @staticmethod
    def _normalize_fen(fen: str) -> str:
        board = chess.Board(fen)
        # Use canonical FEN string from python-chess for cache consistency
        return board.fen()

    @staticmethod
    def _diagram_id(fen: str) -> str:
        digest = hashlib.sha1(fen.encode("utf-8")).hexdigest()[:12]
        return f"dyn_{digest}"

    def get_or_create_diagram(
        self,
        fen: str,
        caption: Optional[str] = None,
        book_title: Optional[str] = None
    ) -> Dict:
        normalized_fen = self._normalize_fen(fen)
        diagram_id = self._diagram_id(normalized_fen)
        file_path = self.cache_dir / f"{diagram_id}.svg"

        with self._lock:
            created = False
            if not file_path.exists():
                board = chess.Board(normalized_fen)
                svg_markup = chess.svg.board(board, size=420)
                file_path.write_text(svg_markup, encoding="utf-8")
                created = True

            meta = self.manifest.get(diagram_id, {
                "created_at": time.time(),
                "hits": 0,
            })
            meta.update({
                "fen": normalized_fen,
                "caption": caption,
                "book_title": book_title,
                "file_path": str(file_path),
                "last_used": time.time(),
                "hits": meta.get("hits", 0) + 1,
            })
            self.manifest[diagram_id] = meta
            self._save_manifest()

        if created:
            logger.info("🎨 Generated dynamic diagram %s (%s)", diagram_id, book_title or "unknown source")

        return {
            "id": diagram_id,
            "url": f"/dynamic_diagrams/{diagram_id}",
            "caption": caption or "Dynamic chess diagram",
            "book_title": book_title or "Dynamic Diagram",
            "book_name": book_title or "Dynamic Diagram",
            "source": "dynamic",
            "fen": normalized_fen
        }

    def get_diagram_path(self, diagram_id: str) -> Optional[Path]:
        file_path = self.cache_dir / f"{diagram_id}.svg"
        if file_path.exists():
            return file_path
        return None

    def get_metadata(self, diagram_id: str) -> Optional[Dict]:
        return self.manifest.get(diagram_id)


dynamic_diagram_service = DynamicDiagramService()


def create_dynamic_diagram(fen: str, caption: Optional[str] = None, book_title: Optional[str] = None) -> Dict:
    """Public helper for creating/retrieving a cached dynamic diagram."""
    return dynamic_diagram_service.get_or_create_diagram(fen, caption, book_title)


def get_dynamic_diagram_path(diagram_id: str) -> Optional[Path]:
    """Return SVG path for a cached diagram (if it exists)."""
    return dynamic_diagram_service.get_diagram_path(diagram_id)
