import logging
from pathlib import Path

from ..config.config_manager import config_manager


def init_logging() -> None:
    cfg_dir = config_manager.config_dir
    log_file = Path(cfg_dir) / "app.log"
    cfg_dir.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(),
        ],
    )

