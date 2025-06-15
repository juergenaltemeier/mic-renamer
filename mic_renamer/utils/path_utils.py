from __future__ import annotations

from pathlib import Path

from appdirs import user_config_dir


def user_config_path(app_name: str, filename: str) -> Path:
    dir_ = Path(user_config_dir(app_name))
    return dir_ / filename

