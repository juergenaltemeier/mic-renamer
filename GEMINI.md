# Gemini Refactoring Tasks for mic-renamer

This document outlines the refactoring tasks to improve the `mic-renamer` program's readability, maintainability, error handling, and robustness, especially for Windows 11 machines.

## Overall Goals:
- Ensure every function, class, and significant code block is well-commented.
- Implement robust error handling and crash recovery mechanisms.
- Review and potentially rewrite architecture for better maintainability and Windows 11 compatibility.
- Make the program "rock solid" on Windows 11.

## Task List:

### Phase 1: Initial Assessment & Core Logic Refinement
1.  **Review `mic_renamer/logic/` files:**
    *   `renamer.py`: Core renaming logic, error handling, path validation.
    *   `heic_converter.py`: External tool integration, error handling for conversions.
    *   `image_compressor.py`: Image processing, error handling.
    *   `tag_loader.py`, `tag_service.py`, `tag_usage.py`: Tag management, data integrity, file I/O.
    *   `undo_manager.py`: Undo/redo functionality, state management, error handling.
    *   `rename_config.py`, `settings.py`: Configuration loading/saving, validation.
2.  **Review `mic_renamer/utils/` files:**
    *   `file_utils.py`, `path_utils.py`, `media_utils.py`, `meta_utils.py`: File system interactions, metadata handling, robust path operations.
    *   `i18n.py`: Internationalization, error handling for missing translations.
    *   `state_manager.py`: Application state persistence, error handling.
    *   `workers.py`: Threading/multiprocessing, error handling for background tasks.

### Phase 2: UI Layer & Configuration Refinement
1.  **Review `mic_renamer/ui/` files:**
    *   `main_window.py`: Main application flow, event handling, UI responsiveness.
    *   `components.py`, `dialogs/`, `panels/`: UI elements, input validation, user feedback on errors.
    *   `theme.py`, `styles/`: Styling, ensuring consistent look and feel.
2.  **Review `mic_renamer/config/` files:**
    *   `config_manager.py`: Configuration loading/saving, default values, schema validation.
    *   `defaults.yaml`, `tags.json`: Data integrity, error handling for malformed files.

### Phase 3: Cross-Cutting Concerns & Final Polish
1.  **Global Error Handling:** Implement a centralized error logging and reporting mechanism.
2.  **Resource Management:** Ensure proper closing of file handles, network connections, etc.
3.  **Performance Optimization:** Identify and optimize any performance bottlenecks, especially for large file operations.
4.  **Testing:** Ensure existing tests are robust and consider adding new tests for critical error handling paths.

## Current Focus:
Starting with `mic_renamer/logic/renamer.py` to enhance comments and error handling.