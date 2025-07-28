"""
This module is responsible for loading and managing tags used within the mic-renamer application.
It provides a robust mechanism to load tags from various sources, including user-defined
configuration files, bundled application resources, and a hardcoded fallback. It also supports
multi-language tag definitions.
"""

from __future__ import annotations

import json
import os
import logging
from pathlib import Path
from importlib import resources

from .. import config_manager
from ..utils.path_utils import get_config_dir

logger = logging.getLogger(__name__)

# Fallback tags used when external or bundled JSON files cannot be located or parsed.
# This is primarily for cases where PyInstaller is executed without including the data files
# or if there are issues with file system access.
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
  "WIRE": {"en": "wiring and pneumatic", "de": "wiring and pneumatic"},
  "FOUND": {"en": "Foundations", "de": "Fundamente"}
} """

# Define default paths for tags.json files.
# DEFAULT_TAGS_FILE points to the user's configuration directory.
DEFAULT_TAGS_FILE = Path(get_config_dir()) / "tags.json"
# BUNDLED_TAGS_FILE points to the tags.json file included within the application package.
BUNDLED_TAGS_FILE = resources.files("mic_renamer.config") / "tags.json"

def get_config_tags_file() -> str | None:
    """
    Retrieves the configured tags file path from the application's configuration manager.

    Returns:
        str | None: The path to the tags file as configured, or None if not set.
    """
    return config_manager.get("tags_file")

# Environment variable name that can override the tags file path.
ENV_TAGS_FILE = "RENAMER_TAGS_FILE"


def _load_raw(file_path: str | None = None) -> dict:
    """
    Internal helper function to load the raw tag dictionary from various sources.
    It attempts to load tags in a specific order of precedence:
    1.  Explicitly provided `file_path`.
    2.  Environment variable `RENAMER_TAGS_FILE`.
    3.  Path from `config_manager`.
    4.  Default user configuration file (`DEFAULT_TAGS_FILE`). If this file doesn't exist,
        it attempts to create it by copying from the bundled tags.
    5.  Bundled tags file within the application package (`BUNDLED_TAGS_FILE`).
    6.  Hardcoded `BUNDLED_TAGS_JSON` string as a last resort.

    Args:
        file_path (str | None): An optional explicit path to a tags JSON file.

    Returns:
        dict: The raw tag dictionary. Returns an empty dictionary if all loading attempts fail.
    """
    # Determine the effective file path based on precedence.
    effective_file_path = file_path or os.environ.get(ENV_TAGS_FILE) or get_config_tags_file()
    
    # Attempt to load from the effective file path if it exists.
    if effective_file_path:
        path = Path(effective_file_path)
        # Ensure the path is absolute.
        if not path.is_absolute():
            path = Path(get_config_dir()) / path

        # If the path points to the default config file and it doesn't exist, try to create it
        # by copying from the bundled resources.
        if path == DEFAULT_TAGS_FILE and not path.is_file():
            logger.info(f"Default tags file not found at {path}. Attempting to create from bundled resources.")
            try:
                path.parent.mkdir(parents=True, exist_ok=True)
                # Read from bundled resource and write to the default config location.
                path.write_text(BUNDLED_TAGS_FILE.read_text(encoding="utf-8"), encoding="utf-8")
                logger.info(f"Successfully created default tags file at {path}.")
            except (OSError, FileNotFoundError, AttributeError) as e:
                logger.error(f"Failed to create default tags file at {path} from bundled resources: {e}")
            except Exception as e:
                logger.error(f"An unexpected error occurred while creating default tags file: {e}")

        # Attempt to load tags from the determined file path.
        if path.is_file():
            try:
                with path.open("r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, dict):
                    logger.info(f"Successfully loaded tags from {path}.")
                    return data
                else:
                    logger.warning(f"Tags file {path} contains invalid JSON format (not a dictionary).")
            except FileNotFoundError:
                logger.warning(f"Tags file not found at {path}. Trying next fallback.")
            except json.JSONDecodeError as e:
                logger.error(f"Error decoding JSON from tags file {path}: {e}. Trying next fallback.")
            except OSError as e:
                logger.error(f"OS error reading tags file {path}: {e}. Trying next fallback.")
            except Exception as e:
                logger.error(f"An unexpected error occurred while reading tags file {path}: {e}. Trying next fallback.")

    # Fallback to bundled file within the package.
    try:
        # Read text from the bundled resource.
        data = json.loads(BUNDLED_TAGS_FILE.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            logger.info("Successfully loaded tags from bundled resources.")
            return data
        else:
            logger.warning("Bundled tags file contains invalid JSON format (not a dictionary).")
    except FileNotFoundError:
        logger.warning(f"Bundled tags file not found at {BUNDLED_TAGS_FILE}. Trying hardcoded fallback.")
    except json.JSONDecodeError as e:
        logger.error(f"Error decoding JSON from bundled tags file {BUNDLED_TAGS_FILE}: {e}. Trying hardcoded fallback.")
    except Exception as e:
        logger.error(f"An unexpected error occurred while reading bundled tags file: {e}. Trying hardcoded fallback.")

    # Final fallback to the hardcoded JSON string.
    try:
        data = json.loads(BUNDLED_TAGS_JSON)
        if isinstance(data, dict):
            logger.info("Successfully loaded tags from hardcoded fallback JSON.")
            return data
        else:
            logger.warning("Hardcoded BUNDLED_TAGS_JSON contains invalid JSON format (not a dictionary).")
    except json.JSONDecodeError as e:
        logger.error(f"Error decoding JSON from hardcoded BUNDLED_TAGS_JSON: {e}. Returning empty tags.")
    except Exception as e:
        logger.error(f"An unexpected error occurred while loading from hardcoded BUNDLED_TAGS_JSON: {e}. Returning empty tags.")

    logger.error("All attempts to load tags failed. Returning empty dictionary.")
    return {}

def load_tags(file_path: str | None = None, language: str | None = None) -> dict:
    """
    Loads tags for the specified language.

    If the tags file contains translations for multiple languages, the appropriate
    entry for the requested language is returned. If only a plain string is present
    for a tag, it is used for all languages.

    Args:
        file_path (str | None): Optional. An explicit path to a tags JSON file.
        language (str | None): Optional. The target language code (e.g., "en", "de").
                               If None, the language from `config_manager` is used.

    Returns:
        dict: A dictionary where keys are uppercase tag codes and values are the
              translated tag descriptions for the requested language.
    """
    raw = _load_raw(file_path)
    lang = language or config_manager.get("language", "en")
    result = {}
    for code, value in raw.items():
        upper_code = code.upper()
        if isinstance(value, str):
            # If the value is a plain string, use it directly.
            result[upper_code] = value
        elif isinstance(value, dict):
            # If the value is a dictionary (translations), try to get the specific language.
            # Fallback to the first available translation if the requested language is not found.
            result[upper_code] = value.get(lang) or next(iter(value.values()), "")
    return result


def load_tags_multilang(file_path: str | None = None) -> dict:
    """
    Loads and returns the raw tag dictionary, including all available translations.

    Args:
        file_path (str | None): Optional. An explicit path to a tags JSON file.

    Returns:
        dict: The raw tag dictionary, where values can be strings or dictionaries
              of language-specific translations.
    """
    return _load_raw(file_path)


def restore_default_tags() -> None:
    """
    Resets the user's `tags.json` file to the bundled default tags.

    This function attempts to copy the `tags.json` from the application's bundled
    resources to the user's configuration directory. If the bundled file is not
    accessible, it falls back to writing the hardcoded `BUNDLED_TAGS_JSON`.
    Error logging is included for all file operations.
    """
    try:
        # Ensure the parent directory for the default tags file exists.
        DEFAULT_TAGS_FILE.parent.mkdir(parents=True, exist_ok=True)
        # Attempt to write the bundled tags content to the default user config file.
        DEFAULT_TAGS_FILE.write_text(BUNDLED_TAGS_FILE.read_text(encoding="utf-8"), encoding="utf-8")
        logger.info(f"Successfully restored default tags to {DEFAULT_TAGS_FILE}.")
    except (OSError, FileNotFoundError, AttributeError) as e:
        logger.error(f"Failed to restore default tags from bundled resources to {DEFAULT_TAGS_FILE}: {e}")
        try:
            # Fallback to hardcoded JSON if bundled file is inaccessible.
            DEFAULT_TAGS_FILE.write_text(BUNDLED_TAGS_JSON, encoding="utf-8")
            logger.info(f"Successfully restored default tags from hardcoded JSON to {DEFAULT_TAGS_FILE}.")
        except (OSError, FileNotFoundError) as e_fallback:
            logger.error(f"Failed to restore default tags from hardcoded JSON to {DEFAULT_TAGS_FILE}: {e_fallback}")
        except Exception as e_unexpected:
            logger.error(f"An unexpected error occurred during fallback restore of default tags: {e_unexpected}")
    except Exception as e:
        logger.error(f"An unexpected error occurred while restoring default tags: {e}")