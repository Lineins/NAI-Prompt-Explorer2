"""Thumbnail list view with zoom support."""
from __future__ import annotations

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtWidgets import QListView


class ThumbnailListView(QListView):
    scaleChanged = Signal(int)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._icon_size = 150
        self.setViewMode(QListView.IconMode)
        self.setResizeMode(QListView.Adjust)
        self.setUniformItemSizes(False)
        self.setWrapping(True)
        self.setSpacing(8)
        self._apply_icon_size(self._icon_size)
        self.setSelectionMode(QListView.SingleSelection)
        self.setMovement(QListView.Static)

    def _apply_icon_size(self, size: int) -> None:
        self.setIconSize(QSize(size, size))
        self.setGridSize(QSize(size + 16, size + 40))
        self.scaleChanged.emit(size)

    def set_icon_scale(self, size: int) -> None:
        size = max(48, min(size, 512))
        if size == self._icon_size:
            return
        self._icon_size = size
        self._apply_icon_size(self._icon_size)

    def wheelEvent(self, event):  # noqa: D401 - Qt API override
        if event.modifiers() & Qt.ControlModifier:
            delta = event.angleDelta().y()
            step = 20 if delta > 0 else -20
            self.set_icon_scale(self._icon_size + step)
            event.accept()
            return
        super().wheelEvent(event)

    def reset_zoom(self) -> None:
        self.set_icon_scale(150)

    def current_scale(self) -> int:
        return self._icon_size

