"""Data models for the prompt explorer."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class PromptEntry:
    """Metadata for a prompt-bearing image file."""

    path: Path
    prompt: str
    width: int
    height: int
    modified_ts: float
    file_size: int

    @property
    def filename(self) -> str:
        return self.path.name

    @property
    def directory(self) -> Path:
        return self.path.parent

