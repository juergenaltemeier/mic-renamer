# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Running the Application
```bash
# Install dependencies
pip install -r requirements.txt

# Run the application
python -m mic_renamer
```

### Testing
```bash
# Install test dependencies (PySide6 must be installed)
pip install PySide6

# Run tests (requires system OpenGL libraries like libegl1 on Linux)
python -m pytest tests/
```

### Building Executables
```bash
# Install PyInstaller
pip install pyinstaller

# Build folder distribution
pyinstaller mic_renamer.spec

# Build single-file executable
pyinstaller mic_renamer_onefile.spec
```

## Architecture Overview

This is a PySide6-based desktop application for batch renaming photos and videos using project numbers, tag codes, and suffixes.

### Core Components

- **`mic_renamer/app.py`**: Application bootstrapper that sets up Qt application, dark theme, and main window
- **`mic_renamer/ui/main_window.py`**: Main UI (`RenamerApp` class) with three-panel layout (file table, image preview, tag panel)
- **`mic_renamer/logic/renamer.py`**: Core renaming logic with support for multiple modes (normal, position, pa_mat)
- **`mic_renamer/config/config_manager.py`**: Configuration management system with YAML defaults

### Key Architecture Patterns

- **State Management**: Uses `StateManager` class to persist UI state (window size, splitter positions, etc.)
- **Undo System**: `UndoManager` tracks rename operations for reversal
- **Threading**: Uses `QThread` for background operations (file preview loading, rename operations)
- **Configuration**: YAML-based config with user-specific overrides in `~/.config/mic_renamer/`

### Directory Structure

- `ui/`: All PySide6 UI components and dialogs
- `ui/panels/`: Modular UI panels (file table, image preview, tag panel, etc.)
- `logic/`: Business logic (renaming, image compression, tag management, etc.)
- `config/`: Configuration management and default settings
- `utils/`: Utility modules (file operations, i18n, workers, etc.)
- `resources/`: Static assets (icons, images)

### Rename Modes

The application supports three rename modes:
- **Normal**: Uses project number + tags + optional suffix
- **Position**: Uses project number + position number + optional suffix  
- **PA_MAT**: Uses project number + "PA_MAT" + number + optional suffix

### Configuration System

- Default settings in `mic_renamer/config/defaults.yaml`
- User config stored in platform-specific config directory
- `tags.json` contains tag definitions and codes
- `tag_usage.json` tracks tag usage statistics