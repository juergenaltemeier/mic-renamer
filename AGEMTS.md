This document provides a high-level overview of the `mic-renamer` codebase.

### Project Purpose

`mic-renamer` is a desktop application for renaming image and video files. It allows users to construct new filenames using a project number, descriptive tags, and optional suffixes. The application provides a graphical user interface for selecting files, managing tags, and previewing changes before renaming.

### Key Technologies

- **Language:** Python 3
- **UI Framework:** PySide6 (the official Python bindings for Qt)
- **Dependencies:**
    - `PySide6`: For the graphical user interface.
    - `appdirs`: To manage user-specific configuration file locations.
    - `PyYAML`: For reading and writing configuration files.
    - `Pillow`: For image manipulation, including creating `.ico` files.
    - `pillow-heif`: To add support for HEIC images.

### Codebase Structure

The codebase is organized into several packages and modules:

- **`mic_renamer/`**: The main application package.
    - **`__main__.py`**: The entry point for the application. It initializes and runs the `Application` class.
    - **`app.py`**: Contains the `Application` class, which bootstraps the Qt application, sets up the main window, and manages application-level state.
    - **`config/`**: Manages application configuration, including default settings (`defaults.yaml`) and user-specific settings.
    - **`logic/`**: Contains the core business logic of the application.
        - `renamer.py`: Implements the file renaming logic.
        - `settings.py`: Defines data structures for item settings and rename configurations.
        - `image_compressor.py`: Handles image compression.
        - `heic_converter.py`: Converts HEIC files to JPEG.
        - `tag_service.py`: Manages tags and their descriptions.
        - `undo_manager.py`: Implements undo functionality for rename operations.
    - **`ui/`**: Contains all user interface components.
        - `main_window.py`: The main application window (`RenamerApp`), which brings together all UI elements.
        - `panels/`: UI panels for specific functions, such as the file table, image preview, and tag selection.
        - `dialogs/`: Various dialog windows used in the application.
    - **`utils/`**: Utility modules for file operations, internationalization (i18n), metadata extraction, and more.
- **`tests/`**: Contains unit and integration tests for the application.
- **`requirements.txt`**: Lists the Python dependencies for the project.
- **`README.md`**: Provides instructions for setting up, running, testing, and building the application.

### Additional instructions
- on every visible UI text element be aware of the changable language of the UI  and that you have to add new text to the correct files in both languages.
- icon color should be #009ee0
- be aware of the Pylance and lint your code always to minimize errors and typos


### How to Run

1.  Create and activate a virtual environment.
2.  Install dependencies: `pip install -r requirements.txt`
3.  Run the application: `python -m mic_renamer`

### How to Run Tests

1.  Install PySide6 and system OpenGL libraries (e.g., `libegl1` on Debian/Ubuntu).
2.  Run the tests using `pytest`.
