"""Main application window for the prompt explorer."""
from __future__ import annotations

import os
from pathlib import Path
from typing import List, Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTextEdit,
    QToolButton,
    QVBoxLayout,
    QWidget,
    QComboBox,
    QButtonGroup,
)

from ..config_manager import ConfigManager
from ..models import PromptEntry
from ..services.cache import PromptMetadataCache
from ..services.directory_scanner import DirectoryScanner
from .filters import SearchMode, ThumbnailFilterProxyModel
from .thumbnail_model import ThumbnailModel
from .thumbnail_view import ThumbnailListView
from .workers import ScanWorker, ThumbnailWorker, run_in_threadpool


class PromptExplorerWindow(QMainWindow):
    """Qt window that provides thumbnail browsing and prompt search."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("NAI Prompt Explorer")
        self.resize(1280, 720)

        project_root = Path(__file__).resolve().parents[3]
        self._config_path = project_root / "config" / "settings.json"
        self._cache_path = project_root / "config" / "prompt_cache.sqlite3"
        self._config = ConfigManager(self._config_path)
        self._cache = PromptMetadataCache(self._cache_path)
        self._scanner = DirectoryScanner(self._cache)

        self._current_folder: Optional[str] = None
        self._entries: List[PromptEntry] = []
        self._thumbnail_jobs: set[str] = set()
        self._active_workers: list[ScanWorker | ThumbnailWorker] = []
        self._current_entry: Optional[PromptEntry] = None

        self._thumbnail_model = ThumbnailModel(self)
        self._filter_proxy = ThumbnailFilterProxyModel(self)
        self._filter_proxy.setSourceModel(self._thumbnail_model)

        self._build_ui()
        self._connect_signals()
        self._populate_presets()
        self._load_initial_folder()

    # ------------------------------------------------------------------ UI construction
    def _build_ui(self) -> None:
        central = QWidget(self)
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        self.folder_edit = QLineEdit(self)
        self.folder_browse_button = QPushButton("Browse…", self)
        self.folder_refresh_button = QPushButton("Rescan", self)

        folder_row = QHBoxLayout()
        folder_row.addWidget(QLabel("Folder:", self))
        folder_row.addWidget(self.folder_edit, stretch=1)
        folder_row.addWidget(self.folder_browse_button)
        folder_row.addWidget(self.folder_refresh_button)

        self.preset_combo = QComboBox(self)
        self.save_preset_button = QPushButton("Save preset", self)
        self.delete_preset_button = QPushButton("Delete preset", self)
        self.set_default_button = QPushButton("Set as default", self)

        preset_row = QHBoxLayout()
        preset_row.addWidget(QLabel("Presets:", self))
        preset_row.addWidget(self.preset_combo, stretch=1)
        preset_row.addWidget(self.save_preset_button)
        preset_row.addWidget(self.delete_preset_button)
        preset_row.addWidget(self.set_default_button)

        self.search_edit = QLineEdit(self)
        self.search_edit.setPlaceholderText("Search prompts…")

        self.mode_exact_button = QToolButton(self)
        self.mode_exact_button.setText("Exact sequence")
        self.mode_exact_button.setCheckable(True)
        self.mode_and_button = QToolButton(self)
        self.mode_and_button.setText("AND terms")
        self.mode_and_button.setCheckable(True)
        self.mode_and_button.setChecked(True)

        self.search_mode_group = QButtonGroup(self)
        self.search_mode_group.setExclusive(True)
        self.search_mode_group.addButton(self.mode_exact_button)
        self.search_mode_group.addButton(self.mode_and_button)

        self.hit_count_label = QLabel("Hits: 0", self)
        self.reset_button = QPushButton("Reset", self)

        search_row = QHBoxLayout()
        search_row.addWidget(QLabel("Search:", self))
        search_row.addWidget(self.search_edit, stretch=1)
        search_row.addWidget(self.mode_exact_button)
        search_row.addWidget(self.mode_and_button)
        search_row.addWidget(self.hit_count_label)
        search_row.addWidget(self.reset_button)

        layout.addLayout(folder_row)
        layout.addLayout(preset_row)
        layout.addLayout(search_row)

        self.thumbnail_view = ThumbnailListView(self)
        self.thumbnail_view.setModel(self._filter_proxy)

        self.prompt_display = QTextEdit(self)
        self.prompt_display.setReadOnly(True)
        self.prompt_display.setPlaceholderText("Select an image to view its prompt metadata…")
        self.export_prompt_button = QPushButton("Export prompt…", self)
        self.export_prompt_button.setEnabled(False)

        prompt_panel = QWidget(self)
        prompt_layout = QVBoxLayout(prompt_panel)
        prompt_layout.addWidget(QLabel("Prompt metadata", self))
        prompt_layout.addWidget(self.prompt_display, stretch=1)
        prompt_layout.addWidget(self.export_prompt_button)

        splitter = QSplitter(Qt.Horizontal, self)
        splitter.addWidget(self.thumbnail_view)
        splitter.addWidget(prompt_panel)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)

        layout.addWidget(splitter, stretch=1)

    def _connect_signals(self) -> None:
        self.folder_browse_button.clicked.connect(self._browse_for_folder)
        self.folder_refresh_button.clicked.connect(self.trigger_scan)
        self.folder_edit.returnPressed.connect(self.trigger_scan)

        self.preset_combo.currentTextChanged.connect(self._on_preset_selected)
        self.save_preset_button.clicked.connect(self._on_save_preset)
        self.delete_preset_button.clicked.connect(self._on_delete_preset)
        self.set_default_button.clicked.connect(self._on_set_default)

        self.search_edit.textChanged.connect(self._on_search_text_changed)
        self.mode_exact_button.toggled.connect(self._on_search_mode_toggled)
        self.mode_and_button.toggled.connect(self._on_search_mode_toggled)
        self.reset_button.clicked.connect(self._on_reset_controls)

        self.thumbnail_view.selectionModel().selectionChanged.connect(self._on_selection_changed)
        self.thumbnail_view.scaleChanged.connect(self._on_scale_changed)

        self.export_prompt_button.clicked.connect(self._export_prompt)

        self._filter_proxy.modelReset.connect(self._update_hit_count)
        self._filter_proxy.rowsInserted.connect(self._update_hit_count)
        self._filter_proxy.rowsRemoved.connect(self._update_hit_count)

    # ------------------------------------------------------------------ Configuration helpers
    def _populate_presets(self) -> None:
        self.preset_combo.clear()
        self.preset_combo.addItem("", "")
        for preset in self._config.list_presets():
            self.preset_combo.addItem(preset["name"], preset["path"])

    def _load_initial_folder(self) -> None:
        default_folder = self._config.get_default_folder()
        if default_folder and os.path.isdir(default_folder):
            self.folder_edit.setText(default_folder)
            self.trigger_scan()

    # ------------------------------------------------------------------ Event handlers
    def _browse_for_folder(self) -> None:
        start_dir = self.folder_edit.text() or self._config.get_default_folder()
        folder = QFileDialog.getExistingDirectory(self, "Select image folder", start_dir)
        if folder:
            self.folder_edit.setText(folder)
            self.trigger_scan()

    def _on_preset_selected(self, _name: str) -> None:
        path = self.preset_combo.currentData()
        if path:
            self.folder_edit.setText(path)
            self.trigger_scan()

    def _on_save_preset(self) -> None:
        folder = self.folder_edit.text().strip()
        if not folder:
            QMessageBox.warning(self, "No folder", "Choose a folder before saving a preset.")
            return
        if not os.path.isdir(folder):
            QMessageBox.warning(self, "Invalid folder", "The selected folder does not exist.")
            return
        name, ok = QInputDialog.getText(self, "Preset name", "Enter a name for this preset:")
        if ok and name:
            try:
                self._config.save_preset(name, folder)
            except ValueError as exc:
                QMessageBox.warning(self, "Preset error", str(exc))
            else:
                self._populate_presets()
                index = self.preset_combo.findText(name)
                if index >= 0:
                    self.preset_combo.setCurrentIndex(index)

    def _on_delete_preset(self) -> None:
        name = self.preset_combo.currentText()
        if not name:
            return
        self._config.delete_preset(name)
        self._populate_presets()

    def _on_set_default(self) -> None:
        folder = self.folder_edit.text().strip()
        if not folder:
            QMessageBox.warning(self, "No folder", "Cannot set an empty folder as default.")
            return
        self._config.set_default_folder(folder)
        self.statusBar().showMessage(f"Default folder set to {folder}", 5000)

    def _on_search_text_changed(self, text: str) -> None:
        self._filter_proxy.set_search_text(text)
        self._update_hit_count()

    def _on_search_mode_toggled(self, checked: bool) -> None:
        if not checked:
            return
        if self.sender() is self.mode_exact_button:
            self._filter_proxy.set_search_mode(SearchMode.EXACT)
        else:
            self._filter_proxy.set_search_mode(SearchMode.AND)
        self._update_hit_count()

    def _on_reset_controls(self) -> None:
        self.search_edit.clear()
        self.mode_and_button.setChecked(True)
        self.thumbnail_view.reset_zoom()
        self._update_hit_count()

    def _on_selection_changed(self, selected, _deselected) -> None:
        indexes = selected.indexes()
        if not indexes:
            self.prompt_display.clear()
            self.export_prompt_button.setEnabled(False)
            self._current_entry = None
            return
        index = indexes[0]
        source_index = self._filter_proxy.mapToSource(index)
        entry = self._thumbnail_model.entry_at(source_index)
        if entry:
            self.prompt_display.setPlainText(entry.prompt)
            self.export_prompt_button.setEnabled(True)
            self._current_entry = entry
        else:
            self.prompt_display.clear()
            self.export_prompt_button.setEnabled(False)
            self._current_entry = None

    def _on_scale_changed(self, size: int) -> None:
        if not self._entries:
            return
        self._thumbnail_model.clear_thumbnails()
        self._thumbnail_jobs.clear()
        for entry in self._entries:
            self._queue_thumbnail(entry, size)

    def trigger_scan(self) -> None:
        folder = self.folder_edit.text().strip()
        if not folder:
            QMessageBox.warning(self, "No folder", "Enter a folder to scan.")
            return
        if not os.path.isdir(folder):
            QMessageBox.warning(self, "Invalid folder", "The folder does not exist.")
            return
        self.statusBar().showMessage(f"Scanning {folder}…")
        worker = ScanWorker(self._scanner, folder)
        worker.signals.result.connect(self._on_scan_result)
        worker.signals.error.connect(self._on_worker_error)
        worker.signals.finished.connect(lambda: self.statusBar().clearMessage())
        self._start_worker(worker)

    def _on_scan_result(self, entries: List[PromptEntry]) -> None:
        self._entries = entries
        self._thumbnail_model.set_entries(entries)
        self._update_hit_count()
        self._current_folder = self.folder_edit.text().strip()
        self._current_entry = None
        self.prompt_display.clear()
        self.export_prompt_button.setEnabled(False)
        self._thumbnail_jobs.clear()
        scale = self.thumbnail_view.current_scale()
        for entry in entries:
            self._queue_thumbnail(entry, scale)

    def _queue_thumbnail(self, entry: PromptEntry, size: int) -> None:
        key = str(entry.path)
        if key in self._thumbnail_jobs:
            return
        self._thumbnail_jobs.add(key)
        worker = ThumbnailWorker(entry.path, size)
        worker.signals.result.connect(self._on_thumbnail_loaded)
        worker.signals.error.connect(self._on_worker_error)
        worker.signals.finished.connect(lambda key=key: self._thumbnail_jobs.discard(key))
        self._start_worker(worker)

    def _on_thumbnail_loaded(self, payload) -> None:
        path, pixmap = payload
        self._thumbnail_model.set_thumbnail(str(path), pixmap)

    def _on_worker_error(self, message: str) -> None:
        self.statusBar().showMessage(message, 5000)

    def _start_worker(self, worker: ScanWorker | ThumbnailWorker) -> None:
        self._active_workers.append(worker)
        worker.signals.finished.connect(lambda w=worker: self._active_workers.remove(w) if w in self._active_workers else None)
        run_in_threadpool(worker)

    def _update_hit_count(self) -> None:
        count = self._filter_proxy.rowCount()
        self.hit_count_label.setText(f"Hits: {count}")

    def _export_prompt(self) -> None:
        if self._current_entry is None:
            return
        entry = self._current_entry
        default_path = entry.path.with_suffix(".txt")
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export prompt",
            str(default_path),
            "Text files (*.txt)",
        )
        if not file_path:
            return
        try:
            with open(file_path, "w", encoding="utf-8") as fh:
                fh.write(entry.prompt)
        except OSError as exc:
            QMessageBox.critical(self, "Export failed", f"Could not write file: {exc}")
        else:
            self.statusBar().showMessage(f"Prompt exported to {file_path}", 5000)

