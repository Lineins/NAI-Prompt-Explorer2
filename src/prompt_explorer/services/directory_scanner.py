"""Directory scanning service for prompt metadata."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Iterable, List

from PIL import Image

from ..models import PromptEntry
from .cache import PromptMetadataCache
from .png_prompt_extractor import PngPromptExtractor


class DirectoryScanner:
    """Scans image folders and caches prompt metadata."""

    def __init__(self, cache: PromptMetadataCache, extractor: PngPromptExtractor | None = None) -> None:
        self._cache = cache
        self._extractor = extractor or PngPromptExtractor()

    def scan(self, folder: os.PathLike[str] | str) -> List[PromptEntry]:
        base_path = Path(folder)
        if not base_path.exists():
            return []
        png_paths = self._collect_pngs(base_path)
        entries: list[PromptEntry] = []
        for path in png_paths:
            stat_info = path.stat()
            cached = self._cache.get(path, stat_info.st_mtime, stat_info.st_size)
            if cached:
                entries.append(cached)
                continue
            prompt = self._extractor.extract_prompt(path)
            width, height = self._image_dimensions(path)
            entry = PromptEntry(
                path=path,
                prompt=prompt,
                width=width,
                height=height,
                modified_ts=stat_info.st_mtime,
                file_size=stat_info.st_size,
            )
            self._cache.put(entry)
            entries.append(entry)
        self._cache.prune_missing(path for path in png_paths)
        return entries

    def _collect_pngs(self, base_path: Path) -> List[Path]:
        paths: list[Path] = []
        for root, _, files in os.walk(base_path):
            for name in files:
                if name.lower().endswith(".png"):
                    paths.append(Path(root) / name)
        paths.sort()
        return paths

    def _image_dimensions(self, path: Path) -> tuple[int, int]:
        try:
            with Image.open(path) as img:
                return img.width, img.height
        except Exception:  # pragma: no cover - fallback when image can't be read
            return 0, 0

