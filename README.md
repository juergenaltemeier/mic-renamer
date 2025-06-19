# Photo/Video Renamer

A desktop application to rename photos and videos using project numbers, tags and optional suffixes.

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

Configuration files are stored in the user specific configuration directory
(e.g. `~/.config/mic_renamer` on Linux). Set the `RENAMER_CONFIG_DIR`
environment variable to override this location. Defaults are bundled in
`mic_renamer/config/defaults.yaml` and will be merged with your custom
configuration at startup. A default `tags.json` file containing available tag
codes is copied to the configuration directory on first run if it does not
already exist. The application also remembers the last used project number so it
is restored on the next launch.

Tag usage statistics are written to ``tag_usage.json`` in the same
configuration directory. You can discover the full path programmatically:

```python
from mic_renamer.logic.tag_usage import get_usage_path
print(get_usage_path())
```

## Building a Standalone Executable


You can bundle the application into a single executable using
[PyInstaller](https://pyinstaller.org/). The provided ``mic_renamer.spec`` file
ensures that required data files like ``defaults.yaml`` and ``tags.json`` are
included in the build:

```bash
pip install pyinstaller

pyinstaller --onefile mic_renamer.spec    
or
pyinstaller mic_renamer.spec 

```

The resulting build directory is written to ``dist/mic-renamer``.

If you prefer a single-file executable, run PyInstaller directly on the entry
module or use the provided ``mic_renamer_onefile.spec``:

```bash
pyinstaller --onefile mic_renamer/__main__.py
# or
pyinstaller mic_renamer_onefile.spec
```

### Custom Executable Icon

Place a ``favicon.ico`` next to the spec file if you want the generated
executable to use a custom icon. You can convert any PNG image to ICO using
Pillow:

```bash
from PIL import Image
Image.open("my_icon.png").save("favicon.ico")
pyinstaller --icon favicon.ico mic_renamer.spec
```

Alternatively, pass ``--icon`` when invoking PyInstaller directly.

Some antivirus tools flag UPX-compressed executables. If this occurs, disable
compression by passing ``--noupx`` or editing the spec files to set
``upx=False``.
