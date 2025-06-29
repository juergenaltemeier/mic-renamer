from __future__ import annotations

import json
import os
from pathlib import Path
from importlib import resources


from .. import config_manager
from ..utils.path_utils import get_config_dir

# Fallback tags used when the bundled JSON file cannot be located. This is
# primarily for cases where PyInstaller is executed without including the data
# files.
BUNDLED_TAGS_JSON = """{  "AU": {"en": "Autoclave", "de": "Autoclave"},
  "AU_DO": {"en": "Autoclave door", "de": "Autoclave door"},
  "AU_INS": {"en": "Autoclave insulation", "de": "Autoclave insulation"},
  "BO": {"en": "Bogie, trolley, drive", "de": "Bogie, trolley, drive"},
  "BR": {"en": "Bridge ( rail / air caster)", "de": "Bridge ( rail / air caster)"},
  "CS": {"en": "Cooling system ; cooling tower etc.", "de": "Cooling system ; cooling tower etc."},
  "CTR": {"en": "Control system general", "de": "Control system general"},
  "CTR_AU": {"en": "Control autoclave ; door", "de": "Control autoclave ; door"},
  "CTR_CU": {"en": "Control collecting unit", "de": "Control collecting unit"},
  "CTR_FU": {"en": "Control feeding unit (pit box)", "de": "Control feeding unit (pit box)"},
  "CTR_VU": {"en": "Control vacuum unit", "de": "Control vacuum unit"},
  "CU": {"en": "Collecting unit", "de": "Collecting unit"},
  "CU_VU": {"en": "Collecting & vacuum unit assembled and shown in total on the picture", "de": "Collecting & vacuum unit assembled and shown in total on the picture"},
  "DU": {"en": "Distillation unit", "de": "Distillation unit"},
  "EXP": {"en": "Expansion tank", "de": "Expansion tank"},
  "FU": {"en": "Feeding unit", "de": "Feeding unit"},
  "HS": {"en": "Heating system ( central)", "de": "Heating system ( central)"},
  "HU_AU": {"en": "Heating unit for autoclave", "de": "Heating unit for autoclave"},
  "HU_FU": {"en": "Heating unit for feeding unit", "de": "Heating unit for feeding unit"},
  "HYD": {"en": "Hydraulic", "de": "Hydraulic"},
  "INS": {"en": "Instruments", "de": "Instruments"},
  "ISO": {"en": "Iso static press", "de": "Iso static press"},
  "JET": {"en": "JET evaporator", "de": "JET evaporator"},
  "N2": {"en": "Nitrogen", "de": "Nitrogen"},
  "PG": {"en": "piping general, vacuum , solvent, air, N2, water , brine, oil,", "de": "piping general, vacuum , solvent, air, N2, water , brine, oil,"},  "PH": {"en": "Piping heating only for heat carrier oil circuit", "de": "Piping heating only for heat carrier oil circuit"},
  "PIT": {"en": "Pit & foundation", "de": "Pit & foundation"},
  "PLANT": {"en": "General plant overview pictures", "de": "General plant overview pictures"},
  "SITE": {"en": "General site pictures showing also surrounding of plant, especially before installation", "de": "General site pictures showing also surrounding of plant, especially before installation"},
  "SS": {"en": "Storage system, solvent, water, oil,", "de": "Storage system, solvent, water, oil,"},  "STAFF": {"en": "Staff pictures", "de": "Staff pictures"},
  "ST_PL": {"en": "Stairs, ladders & platforms", "de": "Stairs, ladders & platforms"},
  "TOOL": {"en": "Tools for ISO press", "de": "Tools for ISO press"},
  "VC": {"en": "Vacuum connection", "de": "Vacuum connection"},
  "VU": {"en": "Vacuum unit", "de": "Vacuum unit"},
  "WIRE": {"en": "wiring and pneumatic", "de": "wiring and pneumatic"}
} """


DEFAULT_TAGS_FILE = Path(get_config_dir()) / "tags.json"
BUNDLED_TAGS_FILE = resources.files("mic_renamer.config") / "tags.json"

def get_config_tags_file():
    return config_manager.get("tags_file")

ENV_TAGS_FILE = "RENAMER_TAGS_FILE"


def _load_raw(file_path: str | None = None) -> dict:
    """Internal helper returning the raw tag dictionary."""
    if file_path is None:
        file_path = os.environ.get(ENV_TAGS_FILE) or get_config_tags_file() or DEFAULT_TAGS_FILE
    path = Path(file_path)
    if not path.is_absolute():
        path = Path(get_config_dir()) / path
    if not path.is_file():
        if path == DEFAULT_TAGS_FILE:
            try:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(BUNDLED_TAGS_FILE.read_text(), encoding="utf-8")
            except Exception:
                pass
    if path.is_file():
        try:
            with path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                return data
        except Exception:
            pass
    # Fallback to bundled file within the package or the built-in JSON string
    try:
        data = json.loads(BUNDLED_TAGS_FILE.read_text())
    except Exception:
        try:
            data = json.loads(BUNDLED_TAGS_JSON)
        except Exception:
            data = {}
    return data if isinstance(data, dict) else {}

def load_tags(file_path: str | None = None, language: str | None = None) -> dict:
    """Return tags for the requested language.

    If the file contains translations for multiple languages the appropriate
    entry is returned. When only a plain string is present, it is used for all
    languages.
    """
    raw = _load_raw(file_path)
    lang = language or config_manager.get("language", "en")
    result = {}
    for code, value in raw.items():
        if isinstance(value, str):
            result[code] = value
        elif isinstance(value, dict):
            result[code] = value.get(lang) or next(iter(value.values()), "")
    return result


def load_tags_multilang(file_path: str | None = None) -> dict:
    """Return the raw tag dictionary with translations."""
    return _load_raw(file_path)


def restore_default_tags() -> None:
    """Reset the user's tags.json to the bundled defaults."""
    try:
        DEFAULT_TAGS_FILE.parent.mkdir(parents=True, exist_ok=True)
        DEFAULT_TAGS_FILE.write_text(BUNDLED_TAGS_FILE.read_text(), encoding="utf-8")
    except Exception:
        try:
            DEFAULT_TAGS_FILE.write_text(BUNDLED_TAGS_JSON, encoding="utf-8")
        except Exception:
            pass


