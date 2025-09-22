"""Application entry point for the NAI Prompt Explorer."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication

from prompt_explorer.ui.main_window import PromptExplorerWindow


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Browse Stable Diffusion PNG prompts")
    parser.add_argument("folder", nargs="?", help="Optional folder to load at startup")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    app = QApplication(sys.argv)
    window = PromptExplorerWindow()
    window.show()
    if args.folder:
        folder = Path(args.folder).expanduser()
        if folder.exists():
            window.folder_edit.setText(str(folder))
            window.trigger_scan()
    return app.exec()


if __name__ == "__main__":  # pragma: no cover - manual execution entrypoint
    raise SystemExit(main())

