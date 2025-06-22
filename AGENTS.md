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

All long-running or blocking operations are executed off the GUI thread using the `Worker` and `PreviewLoader` utilities in `utils/workers.py`. This keeps the UI responsive and avoids Qt’s “Timers cannot be stopped from another thread” and “QThread: Destroyed while thread '' is still running” warnings.

### Core Pattern

```python
from utils.workers import Worker
from PySide6.QtCore import QThread, Qt

# 1. Instantiate your worker, passing in the callable and any arguments.
worker = Worker(task_func, items)

# 2. Create a QThread, then move the worker into it.
thread = QThread()
worker.moveToThread(thread)

# 3. Wire up signals, using QueuedConnection for cross-thread emissions.
thread.started.connect(worker.run, Qt.QueuedConnection)
worker.finished.connect(thread.quit, Qt.QueuedConnection)
worker.finished.connect(worker.deleteLater, Qt.QueuedConnection)
thread.finished.connect(thread.deleteLater, Qt.QueuedConnection)

# 4. Start the thread.
thread.start()


QObject affinity
All child QObjects (e.g. QTimer, network requests, temporary QObject parents) must be created inside worker.run() (i.e. after moveToThread()) so they belong to the correct thread. Creating or stopping a QTimer from the main thread will trigger QObject::killTimer errors.

QueuedConnection
Always specify Qt.QueuedConnection for cross-thread signals to ensure the slot runs in the target’s thread.

Clean shutdown
To cancel mid-flight (for instance on window close or user cancellation):

python
Copy
Edit
worker.stop()            # implement in your worker to set a “should_stop” flag
if thread.isRunning():
    thread.quit()        # exits the thread’s event loop
    thread.wait(2000)    # block up to 2s for clean shutdown
This prevents “Destroyed while thread is still running” when Python tears down the QThread object.

MainWindow Shutdown (closeEvent)
In MainWindow.closeEvent() (lines 1224–1241), ensure each active worker thread is stopped and waited on:

python
Copy
Edit
# pseudo-code from MainWindow.closeEvent
for thread, worker in self.active_workers:
    worker.stop()
    if thread.isRunning():
        thread.quit()
        thread.wait(2000)
This guarantees no timers or event loops linger into interpreter shutdown.

Preview Image Loading
Preview images are loaded via PreviewLoader in utils/workers.py, using the same threading pattern:

python
Copy
Edit
from utils.workers import PreviewLoader
from PySide6.QtCore import QThread, Qt

loader = PreviewLoader(file_path, size)
thread = QThread()
loader.moveToThread(thread)

thread.started.connect(loader.load, Qt.QueuedConnection)
loader.finished.connect(self.on_preview_ready, Qt.QueuedConnection)
loader.finished.connect(thread.quit, Qt.QueuedConnection)
thread.finished.connect(thread.deleteLater)

thread.start()
Because all QPixmap/QImage and QPainter calls happen inside loader.load(), they run in the correct thread and avoid cross-thread issues.


## Miscellaneous
- Configuration files are stored in a user directory (`RENAMER_CONFIG_DIR` overrides the location). See README lines 19–24 for details.
- Default settings include accepted file extensions, compression options and toolbar style.
- No binary artifacts should be committed and unit tests should not be generated automatically.
