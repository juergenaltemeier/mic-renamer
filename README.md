# Photo/Video Renamer

A desktop application to rename photos and videos using project numbers, tags and optional suffixes.

## Setup

1. Install Python 3.8+.
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
environment variable to override this location.
