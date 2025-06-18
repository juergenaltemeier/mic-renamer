"""Application entry point for running as a script or packaged executable."""

# Use an absolute import so the module works when executed directly
# (e.g. when bundled with PyInstaller).
from mic_renamer.app import Application


def main() -> int:
    app = Application()
    return app.run()


if __name__ == "__main__":
    raise SystemExit(main())
