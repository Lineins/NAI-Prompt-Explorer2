"""Threaded worker helpers for the Qt UI."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QObject, QRunnable, Qt, QThreadPool, Signal
from PySide6.QtGui import QImage, QPixmap

from ..services.directory_scanner import DirectoryScanner


class WorkerSignals(QObject):
    finished = Signal()
    error = Signal(str)
    result = Signal(object)
    progress = Signal(int)


class ScanWorker(QRunnable):
    """Background worker that performs a directory scan."""

    def __init__(self, scanner: DirectoryScanner, folder: str) -> None:
        super().__init__()
        self.signals = WorkerSignals()
        self._scanner = scanner
        self._folder = folder

    def run(self) -> None:  # pragma: no cover - Qt threads are not easily tested in isolation
        try:
            entries = self._scanner.scan(self._folder)
        except Exception as exc:  # noqa: BLE001 - provide feedback to UI
            self.signals.error.emit(str(exc))
        else:
            self.signals.result.emit(entries)
        finally:
            self.signals.finished.emit()


class ThumbnailWorker(QRunnable):
    """Loads and scales thumbnails off the GUI thread."""

    def __init__(self, path: Path, target_size: int) -> None:
        super().__init__()
        self.signals = WorkerSignals()
        self._path = path
        self._target = target_size

    def run(self) -> None:  # pragma: no cover - Qt threads are not easily tested in isolation
        try:
            image = QImage(str(self._path))
            if image.isNull():
                raise ValueError("Unable to load image")
            pixmap = QPixmap.fromImage(image)
            if self._target:
                pixmap = pixmap.scaled(
                    self._target,
                    self._target,
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation,
                )
        except Exception as exc:  # noqa: BLE001
            self.signals.error.emit(f"Failed to load {self._path.name}: {exc}")
        else:
            self.signals.result.emit((self._path, pixmap))
        finally:
            self.signals.finished.emit()


def run_in_threadpool(task: QRunnable) -> None:
    """Convenience helper to queue a worker into the global thread pool."""
    QThreadPool.globalInstance().start(task)

