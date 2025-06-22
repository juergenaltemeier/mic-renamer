# Mic Renamer Guidelines

This repository contains a cross-platform photo/video renaming tool built with PySide6. The package layout already follows a modular structure and new code should continue to respect it.

## Project Structure
- **Entry point**: `mic_renamer/__main__.py` which instantiates `Application` from `app.py` and calls `run()`.
- **Configuration**: handled via `mic_renamer/config/config_manager.py` which loads defaults from `config/defaults.yaml` and writes user settings under a config directory. See lines 1–34 in that file for the default keys.
- **State**: `StateManager` in `mic_renamer/utils/state_manager.py` stores UI state in `state.json` next to the user config.
- **UI**: widgets and dialogs live under `mic_renamer/ui/` with each panel in `ui/panels/`. The main window class is `RenamerApp` in `main_window.py`.
- **Business logic**: resides under `mic_renamer/logic/` (e.g. `renamer.py`, `image_compressor.py`).
- **Utilities**: helper modules are located in `mic_renamer/utils/` including `workers.py` for background tasks.
- **Tests**: located in `tests/` but running them requires PySide6 and system OpenGL libraries as noted in `README.md` lines 35–51.

Dependencies are listed in `requirements.txt`:
```
PySide6>=6.0.0
appdirs>=1.4
PyYAML>=5.3
Pillow>=9.0
pillow-heif>=0.14
```

## Coding Conventions
- Follow PEP8 naming and formatting.
- Keep UI code separate from business logic. Panels or dialogs should each live in their own module.
- Use object-oriented design. Configuration is accessed through `ConfigManager`, UI state through `StateManager`.
- Handle configuration errors gracefully by falling back to defaults.
- Persist window size and splitter positions using `StateManager` on close.
- When adding features, strive for small, single-purpose functions and avoid monolithic files.
- New modules must contain docstrings explaining their purpose and public APIs.

## Threading and Workers
Long running tasks are executed in background threads using the utilities from `utils/workers.py`. The pattern looks like this:
```
worker = Worker(task_func, items)
thread = QThread()
worker.moveToThread(thread)
thread.started.connect(worker.run)
worker.finished.connect(thread.quit)
thread.finished.connect(thread.deleteLater)
```
Signals should use `Qt.QueuedConnection` when crossing threads. Cancel operations should call `worker.stop()` and wait for the thread to finish, as done in `MainWindow.closeEvent()` lines 1224–1241 and in `CompressionDialog` lines 93–111.

Always clean up running threads on application shutdown to avoid dangling workers. Preview image loading follows the same pattern using `PreviewLoader` in `utils/workers.py`.

## Miscellaneous
- Configuration files are stored in a user directory (`RENAMER_CONFIG_DIR` overrides the location). See README lines 19–24 for details.
- Default settings include accepted file extensions, compression options and toolbar style.
- No binary artifacts should be committed and unit tests should not be generated automatically.
