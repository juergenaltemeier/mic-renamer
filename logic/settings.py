# logic/settings.py

import os

class ItemSettings:
    ACCEPT_EXTENSIONS = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.mp4', '.avi', '.mov', '.mkv']

    def __init__(self, original_path: str):
        self.original_path = original_path
        self.tags = set()
        self.suffix = ""

    def build_new_name(self, project: str, index: int, date_str: str, ordered_tags: list[str]) -> str:
        parts = [project] + ordered_tags + [date_str, f"{index:03d}"]
        base = "_".join(parts)
        if self.suffix:
            base += f"_{self.suffix}"
        ext = os.path.splitext(self.original_path)[1]
        return base + ext
