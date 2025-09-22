"""Model and proxy model for thumbnail display."""
from __future__ import annotations

from typing import List

from PySide6.QtCore import QAbstractListModel, QModelIndex, QObject, Qt
from PySide6.QtGui import QPixmap

from ..models import PromptEntry


class ThumbnailModel(QAbstractListModel):
    PATH_ROLE = Qt.UserRole + 1
    PROMPT_ROLE = Qt.UserRole + 2

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._entries: list[PromptEntry] = []
        self._pixmaps: dict[str, QPixmap] = {}

    def rowCount(self, parent: QModelIndex | None = None) -> int:  # noqa: N802 - Qt API
        return 0 if parent and parent.isValid() else len(self._entries)

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole):  # noqa: D401 - Qt signature
        if not index.isValid():
            return None
        entry = self._entries[index.row()]
        if role == Qt.DisplayRole:
            return entry.filename
        if role == Qt.DecorationRole:
            pixmap = self._pixmaps.get(str(entry.path))
            if pixmap:
                return pixmap
        if role == Qt.ToolTipRole:
            return entry.prompt
        if role == self.PATH_ROLE:
            return str(entry.path)
        if role == self.PROMPT_ROLE:
            return entry.prompt
        return None

    def set_entries(self, entries: List[PromptEntry]) -> None:
        self.beginResetModel()
        self._entries = list(entries)
        self._pixmaps.clear()
        self.endResetModel()

    def entry_at(self, index: QModelIndex) -> PromptEntry | None:
        if not index.isValid():
            return None
        row = index.row()
        if 0 <= row < len(self._entries):
            return self._entries[row]
        return None

    def set_thumbnail(self, path: str, pixmap: QPixmap) -> None:
        key = str(path)
        self._pixmaps[key] = pixmap
        for row, entry in enumerate(self._entries):
            if str(entry.path) == key:
                idx = self.index(row)
                self.dataChanged.emit(idx, idx, [Qt.DecorationRole])
                break

    def clear_thumbnails(self) -> None:
        self._pixmaps.clear()

