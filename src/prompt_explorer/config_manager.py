"""Configuration management utilities for the prompt explorer application."""
from __future__ import annotations

import json
import os
from pathlib import Path
from threading import Lock
from typing import Dict, List, Optional


class ConfigManager:
    """Loads and stores application configuration in a JSON file."""

    def __init__(self, config_path: os.PathLike[str] | str) -> None:
        self._config_file = Path(config_path)
        self._lock = Lock()
        self._config_file.parent.mkdir(parents=True, exist_ok=True)
        if not self._config_file.exists():
            self._write({"default_folder": "", "presets": []})

    def _read(self) -> Dict[str, object]:
        with self._config_file.open("r", encoding="utf-8") as fh:
            return json.load(fh)

    def _write(self, data: Dict[str, object]) -> None:
        tmp_path = self._config_file.with_suffix(".tmp")
        with tmp_path.open("w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2)
        tmp_path.replace(self._config_file)

    def get_default_folder(self) -> str:
        with self._lock:
            return str(self._read().get("default_folder", ""))

    def set_default_folder(self, folder: str) -> None:
        folder = os.path.abspath(folder) if folder else ""
        with self._lock:
            data = self._read()
            data["default_folder"] = folder
            self._write(data)

    def list_presets(self) -> List[Dict[str, str]]:
        with self._lock:
            data = self._read()
        presets = data.get("presets", [])
        if isinstance(presets, list):
            cleaned: List[Dict[str, str]] = []
            for entry in presets:
                if isinstance(entry, dict) and "name" in entry and "path" in entry:
                    cleaned.append({"name": str(entry["name"]), "path": str(entry["path"])})
            return cleaned
        return []

    def save_preset(self, name: str, path: str) -> None:
        name = name.strip()
        if not name:
            raise ValueError("Preset name cannot be empty")
        normalized = os.path.abspath(path)
        with self._lock:
            data = self._read()
            presets: List[Dict[str, str]] = []
            for entry in data.get("presets", []):
                if isinstance(entry, dict) and entry.get("name") != name:
                    presets.append({"name": str(entry.get("name", "")), "path": str(entry.get("path", ""))})
            presets.append({"name": name, "path": normalized})
            data["presets"] = presets
            self._write(data)

    def delete_preset(self, name: str) -> None:
        with self._lock:
            data = self._read()
            presets = [entry for entry in data.get("presets", []) if isinstance(entry, dict) and entry.get("name") != name]
            data["presets"] = presets
            self._write(data)

    def get_preset_path(self, name: str) -> Optional[str]:
        for entry in self.list_presets():
            if entry["name"] == name:
                return entry["path"]
        return None

