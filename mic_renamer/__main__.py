"""Application entry point for running as a script or packaged executable."""

# Use an absolute import so the module works when executed directly
# (e.g. when bundled with PyInstaller).
import sys
try:
    from mic_renamer.app import Application
except ModuleNotFoundError as e:
    missing = e.name if hasattr(e, 'name') else str(e)
    sys.stderr.write(
        f"Error: missing required module '{missing}'.\n"
        "Please install dependencies with 'pip install -r requirements.txt'\n"
    )
    sys.exit(1)


def main() -> int:
    app = Application()
    return app.run()


if __name__ == "__main__":
    raise SystemExit(main())
