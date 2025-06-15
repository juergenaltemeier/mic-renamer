# Photo/Video Renamer

A desktop application to rename photos and videos using project numbers, tags and optional suffixes. The code base is organised into dedicated packages for configuration, UI panels, logic services and utilities.

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
(e.g. `~/.config/mic-renamer` on Linux). Set the `RENAMER_CONFIG_DIR`
environment variable to override this location. Default values are bundled in
`mic_renamer/config/defaults.yaml` and are loaded on first start. The *Settings*
dialog lets you change the path of the configuration file or reset all
settings to these defaults.

## Theming

Colors for the user interface can be customised via the `theme` section of the
configuration file. The application validates color values before applying them
and falls back to safe defaults if a value is invalid. Use the *Settings* dialog
to reload the configuration and reapply the theme at runtime.
