# Repository Guidelines

## Project Structure & Module Organization
- `mic_renamer/`: application package
  - `config/`: defaults (`defaults.yaml`), `tags.json`, config loader
  - `logic/`: core rename/compression/tag services
  - `ui/`: PySide6 widgets, dialogs, and styles
  - `utils/`: helpers (i18n, file/meta/path/state)
  - `app.py`, `__main__.py`: entry points
- `tests/`: pytest test suite (`test_*.py`)
- `mic_renamer.spec`, `mic_renamer_onefile.spec`: PyInstaller builds
- `dist/`, `build/`: generated artifacts (ignored in changes)

## Build, Test, and Development Commands
- Setup: `python -m venv venv && source venv/bin/activate` (Windows: `./venv/Scripts/activate`) then `pip install -r requirements.txt`.
- Run app: `python -m mic_renamer` (respects `RENAMER_CONFIG_DIR` for config location).
- Tests: `pytest -q` or filter with `pytest -k renamer`.
- Build (folder): `pyinstaller mic_renamer.spec` → `dist/mic-renamer/`.
- Build (one file): `pyinstaller mic_renamer_onefile.spec`.
- FFmpeg: ensure `ffmpeg` is on `PATH` or placed at `mic_renamer/resources/ffmpeg/<platform>/ffmpeg(.exe)` for video thumbnails.

## Coding Style & Naming Conventions
- Python 3.10+; 4-space indentation; keep lines readable.
- Naming: modules/files `snake_case.py`; functions/variables `snake_case`; classes `PascalCase`; constants `UPPER_SNAKE`.
- Prefer type hints and short, focused functions; add minimal docstrings where helpful.
- Imports: standard lib → third-party → local; avoid wildcard imports.

## Testing Guidelines
- Framework: `pytest` (+ `pytest-qt` for Qt widgets).
- Location/pattern: `tests/test_*.py`; mirror module names when possible.
- Environment: Qt/OpenGL must initialize; headless runs may need Xvfb (Linux) or platform GPU drivers.
- Aim to cover rename logic, tag handling, and state persistence with deterministic inputs.

## Commit & Pull Request Guidelines
- Commits: imperative mood, concise subject (e.g., `fix: handle PA_MAT underscore`); include scope when useful (`feat`, `fix`, `refactor`).
- Reference issues in body (`Fixes #123`) and explain behavior changes briefly.
- PRs: clear description, steps to test, screenshots for UI changes, and note OS/FFmpeg implications when applicable.
- Keep diffs focused; update README/config examples when user-facing behavior changes.

## Security & Configuration Tips
- Do not commit private keys or `.pfx` files; keep credentials out of code.
- User config lives under platform config dir by default; override with `RENAMER_CONFIG_DIR`.
- For Windows signing, follow README “Code Signing” steps outside of version control.

