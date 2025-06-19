# Mic Renamer

A cross-platform desktop tool to rename photos and videos using project numbers, tag codes and optional suffixes. The UI is built with PySide6.

## Setup

1. Install Python 3.10 or newer.
2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # on Windows use .\venv\Scripts\activate
   pip install -r requirements.txt
   ```
3. Start the application:
   ```bash
   python -m mic_renamer
   ```

Configuration files are stored in a user specific directory (for example
`~/.config/mic_renamer` on Linux). Set the `RENAMER_CONFIG_DIR` environment
variable if you want them somewhere else, e.g. on your `D:` drive. Defaults
ship with the project in `mic_renamer/config/defaults.yaml` and are merged with
your configuration on start. A `tags.json` file is copied to the configuration
folder the first time the program runs so you can adapt it to your needs. The
application also remembers the last used project number.

Tag usage statistics are written to ``tag_usage.json`` in the same
configuration directory. You can discover the full path programmatically:

```python
from mic_renamer.logic.tag_usage import get_usage_path
print(get_usage_path())
```

## Building a Standalone Executable

The repository contains three spec files for [PyInstaller](https://pyinstaller.org/):

* ``mic_renamer.spec`` – builds a folder style distribution in ``dist/mic-renamer``.
  The resulting ``mic-renamer.exe`` runs without opening a console and includes
  the icon if ``favicon.png``/``favicon.ico`` are present.
* ``mic_renamer_onefile.spec`` – like above but produces a single file executable.
* ``mic-renamer.spec`` – a minimal spec kept for reference. You normally do not
  need this one.

Use one of the first two spec files from the repository root:

```bash
pip install pyinstaller

# folder build
pyinstaller mic_renamer.spec

# single file build
pyinstaller mic_renamer_onefile.spec

```

The resulting build directory is written to ``dist/mic-renamer``. If you prefer
a single-file executable you can call PyInstaller directly on the entry module
and pass ``--onefile``.

### Custom Executable Icon

To give the application and generated executable a custom icon, create your own
``favicon.png`` and place it inside the ``mic_renamer`` package directory.
Optionally create a matching ``favicon.ico`` next to the spec file. You can
convert any PNG image to ICO using Pillow:

```bash
from PIL import Image
Image.open("my_icon.png").save("favicon.png")
Image.open("my_icon.png").save("favicon.ico")
```

After placing the icons, build the executable. The spec files automatically
pick up ``favicon.ico`` when present. You can also pass ``--icon`` manually:

```bash
pyinstaller --icon favicon.ico mic_renamer.spec
```

If you run PyInstaller directly on the entry module, pass ``--noconsole`` to
avoid an extra terminal window:

```bash
pyinstaller --noconsole --icon favicon.ico mic_renamer/__main__.py
```

Some antivirus tools flag UPX-compressed executables. If this occurs, disable
compression by passing ``--noupx`` or editing the spec files to set
``upx=False``.
