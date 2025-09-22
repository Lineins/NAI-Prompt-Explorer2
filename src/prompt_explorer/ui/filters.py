"""Filtering logic for thumbnail search."""
from __future__ import annotations

from enum import Enum

from PySide6.QtCore import QSortFilterProxyModel, Qt

from .thumbnail_model import ThumbnailModel


class SearchMode(Enum):
    EXACT = "exact"
    AND = "and"


class ThumbnailFilterProxyModel(QSortFilterProxyModel):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._mode = SearchMode.AND
        self._pattern = ""
        self.setFilterCaseSensitivity(Qt.CaseInsensitive)

    def set_search_text(self, text: str) -> None:
        self._pattern = text.strip()
        self.invalidateFilter()

    def set_search_mode(self, mode: SearchMode) -> None:
        if self._mode != mode:
            self._mode = mode
            self.invalidateFilter()

    def filterAcceptsRow(self, source_row: int, source_parent) -> bool:  # noqa: N802 - Qt API
        if not self._pattern:
            return True
        index = self.sourceModel().index(source_row, 0, source_parent)
        prompt = self.sourceModel().data(index, ThumbnailModel.PROMPT_ROLE) or ""
        filename = self.sourceModel().data(index, Qt.DisplayRole) or ""
        haystack = f"{filename}\n{prompt}".lower()
        if self._mode is SearchMode.EXACT:
            return self._pattern.lower() in haystack
        terms = [term for term in self._pattern.lower().split() if term]
        return all(term in haystack for term in terms)

    def rowCount(self, parent=None):  # noqa: N802 - Qt API
        return super().rowCount(parent)

