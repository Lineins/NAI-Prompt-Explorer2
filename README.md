# NAI Prompt Explorer

A desktop utility for browsing Stable Diffusion PNG images, extracting their embedded prompt metadata, and organizing commonly used search presets.

## Prerequisites

- **Python:** 3.9 or newer. The project relies on modern type annotations introduced in Python 3.9.
- **Pip:** Ensure `pip` is available for the same Python interpreter you plan to use.
- **Qt dependencies:** The UI is built with [PySide6](https://doc.qt.io/qtforpython/) (Qt for Python). On Linux you may need system packages that provide an X11/Wayland GUI stack and OpenGL drivers; Windows and macOS ship the required Qt libraries with the wheel.

Creating and activating an isolated virtual environment is strongly recommended so that the project’s dependencies do not interfere with other Python software on your machine.

## Environment setup and installation

1. **Clone the repository** (or download a release archive) and open a terminal in the project root.
2. **Create a virtual environment** (choose one of the following commands):

   ```bash
   # macOS / Linux
   python3 -m venv .venv

   # Windows (Command Prompt)
   py -3 -m venv .venv
   ```

3. **Activate the environment:**

   ```bash
   # macOS / Linux
   source .venv/bin/activate

   # Windows (Command Prompt)
   .venv\Scripts\activate

   # Windows (PowerShell)
   .venv\Scripts\Activate.ps1
   ```

4. **Upgrade pip (optional but encouraged):**

   ```bash
   python -m pip install --upgrade pip
   ```

5. **Install Python dependencies:**

   ```bash
   pip install -r requirements.txt
   ```

   The current application depends on `PySide6` for the Qt widgets and `Pillow` for reading PNG metadata. Installing from `requirements.txt` ensures both are present.

## Configuration

Application configuration is stored in `config/settings.json`. The file is created automatically with sensible defaults the first time you start the application, but you can edit it manually to customize the behaviour:

```json
{
  "default_folder": "", 
  "presets": []
}
```

- `default_folder`: Absolute path to the image directory that should load when the application starts. Leave it empty to choose a folder manually each time.
- `presets`: A list of preset definitions, each containing a `name` and `path`. Presets appear in the **Presets** drop-down in the UI and allow one-click switching between frequently used directories. Example:

  ```json
  {
    "presets": [
      { "name": "Portraits", "path": "D:/Art/Portraits" },
      { "name": "Landscapes", "path": "/home/user/images/landscapes" }
    ]
  }
  ```

The application also maintains a SQLite cache at `config/prompt_cache.sqlite3` to speed up rescans. It is regenerated automatically if deleted.

## Running the desktop client

From the repository root, make sure your virtual environment is active and run the application module with the project on the Python path:

```bash
# macOS / Linux
export PYTHONPATH=src
python -m app [optional/path/to/images]

# Windows (PowerShell)
$env:PYTHONPATH = "src"
python -m app [optional\\path\\to\\images]

# Windows (Command Prompt)
set PYTHONPATH=src
python -m app [optional\path\to\images]
```

Passing an optional folder argument pre-populates the UI with that directory. If you omit it, the app uses the `default_folder` from `config/settings.json` or prompts you to choose a location.

PySide6 opens a native desktop window. On Wayland-based Linux distributions you may need to set `QT_QPA_PLATFORM=wayland` (or `xcb` for X11) if the default display backend does not match your environment.

## Troubleshooting

- **Missing Qt platform plugin:** Ensure that the necessary GUI libraries are available on your system. On headless Linux servers you may need to install packages such as `libxcb` and run the application within a desktop session.
- **Permission errors writing to `config/`:** The application needs write access to the `config` directory to update presets and the prompt cache. If you cloned the repository into a protected location, run the app with appropriate permissions or move it to a user-writable directory.
