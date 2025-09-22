"""Utilities for extracting textual prompts from PNG files."""
from __future__ import annotations

from pathlib import Path
from typing import Iterable

from PIL import Image


class PngPromptExtractor:
    """Extracts prompt text from PNG metadata using Pillow."""

    _LIKELY_KEYS = {
        "parameters",
        "prompt",
        "description",
        "comment",
        "user_comment",
        "software",
        "title",
    }

    def extract_prompt(self, file_path: str | Path) -> str:
        path = Path(file_path)
        chunks: list[str] = []
        try:
            with Image.open(path) as img:
                info = getattr(img, "info", {}) or {}
                chunks.extend(self._iter_text_chunks(info))
                text_attr = getattr(img, "text", None)
                if text_attr:
                    chunks.extend(self._iter_text_chunks(text_attr))
        except Exception as exc:  # pragma: no cover - safety net for unforeseen metadata issues
            chunks.append(f"<error extracting prompt: {exc}>")
        normalized = self._normalize_chunks(chunks)
        return "\n".join(normalized).strip()

    def _iter_text_chunks(self, data: object) -> Iterable[str]:
        if isinstance(data, dict):
            for key, value in data.items():
                if not isinstance(value, (str, bytes)):
                    continue
                if isinstance(value, bytes):
                    try:
                        value = value.decode("utf-8", errors="replace")
                    except Exception:
                        continue
                if str(key).lower() in self._LIKELY_KEYS or value.strip():
                    yield value
        elif isinstance(data, Iterable) and not isinstance(data, (str, bytes)):
            for item in data:
                if isinstance(item, tuple) and len(item) == 2:
                    _, value = item
                    if isinstance(value, bytes):
                        value = value.decode("utf-8", errors="replace")
                    if isinstance(value, str):
                        yield value

    def _normalize_chunks(self, chunks: Iterable[str]) -> list[str]:
        normalized: list[str] = []
        seen: set[str] = set()
        for chunk in chunks:
            text = chunk.strip()
            if not text or text.lower() in seen:
                continue
            seen.add(text.lower())
            normalized.append(text)
        if not normalized:
            normalized.append("<no prompt metadata found>")
        return normalized

