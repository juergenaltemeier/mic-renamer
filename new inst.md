## 1. Project Overview

**mic-renamer-hub** is a modular Qt Quick application written in C++17, consisting of:
- A central **Hub App** (dashboard with a collapsible sidebar).
- Individual **modules** (e.g., RenamerModule, InventoryModule) that are loaded dynamically and expose their UI via QML pages.

---

## 2. Code Structure

```
mic-renamer-hub/
├── CMakeLists.txt                  # Main CMake configuration
├── src/
│   ├── main.cpp                    # Application entry point
│   ├── ModuleManager.cpp/.h       # Manages registration and loading of modules
│   ├── IModule.h                   # Interface for all modules
│   └── modules/
│       ├── RenamerModule.cpp/.h    # Initial module: Image Renamer
│       └── …                        # Additional modules
├── qml/
│   ├── Main.qml                    # ApplicationWindow + Sidebar
│   ├── Sidebar.qml                 # Collapsible sidebar
│   ├── RenamerPage.qml             # QML UI for the RenamerModule
│       └── …                       # QML pages for other modules
├── resources/
│   └── translations/
│       ├── en.ts                   # English translation source
│       └── de.ts                   # German translation source
└── tests/                          # Unit tests (Qt Test)
```

---

## 3. Naming & Style Conventions

**C++**
- **Filenames & Classes**: `PascalCase` (e.g., `RenamerModule.h`).
- **Member variables**: `m_` prefix (e.g., `m_engine`).
- **Methods & Functions**: `camelCase` (e.g., `registerModule()`).
- **Headers**: Use `#pragma once`.
- **Signals/Slots**: Use `Q_OBJECT` macro, `signals:` section.

**QML**
- **Files & Components**: `PascalCase.qml` (e.g., `RenamerPage.qml`).
- **Properties**: `camelCase`.
- **Imports**:
  ```qml
  import QtQuick 2.15
  import QtQuick.Controls 2.15
  import Hub 1.0    // for ModuleManager
  ```
- **Strings**: Always use `qsTr("...")` for translation.

**Translations**
- Use `lupdate` and `lrelease` to manage `.ts` and `.qm` files.
- Place translation sources under `resources/translations/`.

---

## 4. Build & Run Instructions

### Local Development
```bash
mkdir build && cd build
cmake .. -DCMAKE_BUILD_TYPE=Debug
cmake --build . --config Debug

# Run the application
./mic-renamer-hub           # Linux/macOS
mic-renamer-hub.exe         # Windows

# For QML live reload (UI only):
qmlscene ../qml/Main.qml
```

### Release Build
```bash
cd build
cmake .. -DCMAKE_BUILD_TYPE=Release
cmake --build . --config Release
# Bundle the app
macOS:   macdeployqt mic-renamer-hub.app
Windows: windeployqt mic-renamer-hub.exe
```

---

## 5. Pull Request Guidelines

When generating a PR via Code CLI:
1. Provide a clear PR title and description.
2. Reference related issues (`Fixes #123`).
3. Ensure all tests pass (`ctest`).
4. Format code with `clang-format`.
5. Update translation files if any strings changed.
6. Update this AGENTS.md if new modules or conventions are introduced.

---

## 6. Scaffolding New Modules with Code CLI

Use the OpenAI Code CLI to generate a new module:
```bash
openai code generate \
  --name MyNewModule \
  --template cpp \
  --output src/modules/MyNewModule.cpp,src/modules/MyNewModule.h \
  --stub 'class MyNewModule : public IModule { /* override id(), name(), qmlSource() */ };'
```

After generation:
1. Create the QML page at `qml/MyNewModulePage.qml`.
2. Register the new module in `ModuleManager` (in C++).
3. Test with:
   ```bash
   openai code run -- cmake --build build
   ```