"""
This module provides utility functions for extracting relevant information, such as tags
and custom suffixes, from file names. These functions are crucial for parsing existing
file names and applying renaming logic based on predefined rules and modes.
"""
from __future__ import annotations

import os
import re
import logging
from typing import Iterable

logger = logging.getLogger(__name__)


def extract_tags_from_name(name: str, valid_tags: Iterable[str]) -> set[str]:
    """
    Extracts known tag codes from a given file name.

    The function first extracts the base name (without extension), then splits it into
    alphanumeric tokens. It then checks these tokens against a collection of valid tags
    (case-insensitive).

    Args:
        name (str): The file name or full path to analyze.
        valid_tags (Iterable[str]): A collection (e.g., list, set) of valid tag codes.

    Returns:
        set[str]: A set of tags found in the `name` that are present in `valid_tags`.
                  The returned tags are in uppercase.
    """
    if not isinstance(name, str) or not name:
        logger.warning(f"Invalid input 'name' for extract_tags_from_name: {name}")
        return set()

    # Extract the base name without the directory path or file extension.
    base = os.path.basename(name)
    base, _ = os.path.splitext(base)
    
    # Split the base name into alphanumeric tokens using non-alphanumeric characters as delimiters.
    # This helps in isolating potential tag codes.
    tokens = re.split(r"[^A-Za-z0-9]+", base)
    
    # Convert valid tags to a set of uppercase for efficient case-insensitive lookup.
    codes = {t.upper() for t in valid_tags}
    
    # Filter tokens: keep only those that, when uppercased, are present in the set of valid codes.
    return {t.upper() for t in tokens if t.upper() in codes}


def _find_date_index(tokens: list[str]) -> int | None:
    """
    Helper function to find the index of the first 6-digit date string (YYMMDD) in a list of tokens.

    Args:
        tokens (list[str]): A list of string tokens from a file name.

    Returns:
        int | None: The index of the first date token, or None if no date token is found.
    """
    for i, tok in enumerate(tokens):
        if re.fullmatch(r"\d{6}", tok):
            return i
    return None


def _strip_numeric_tokens(tokens: list[str], from_start: bool = False) -> list[str]:
    """
    Helper function to strip purely numeric tokens from the start or end of a list.

    Args:
        tokens (list[str]): The list of tokens to process.
        from_start (bool): If True, strip from the beginning; otherwise, strip from the end.

    Returns:
        list[str]: The list of tokens with numeric tokens stripped.
    """
    processed_tokens = list(tokens) # Work on a copy
    if from_start:
        while processed_tokens and processed_tokens[0].isdigit():
            processed_tokens.pop(0)
    else:
        while processed_tokens and processed_tokens[-1].isdigit():
            processed_tokens.pop()
    return processed_tokens


def extract_suffix_from_name(name: str, valid_tags: Iterable[str], mode: str = "normal") -> str:
    """
    Extracts a custom suffix from a file name based on the specified renaming mode.

    The suffix is typically defined as alphanumeric tokens appearing after a date segment
    (YYMMDD) in the filename, excluding any trailing numeric indices or known tags.

    Args:
        name (str): The file name or full path to analyze.
        valid_tags (Iterable[str]): A collection of valid tag codes, used to avoid
                                    misinterpreting a single tag as a suffix.
        mode (str): The renaming mode, which dictates the suffix extraction logic.
                    Supported modes: "normal", "pos", "pa_mat". Defaults to "normal".

    Returns:
        str: The extracted suffix. Returns an empty string if no valid suffix is found
             or if the extracted suffix is a known tag.
    """
    if not isinstance(name, str) or not name:
        logger.warning(f"Invalid input 'name' for extract_suffix_from_name: {name}")
        return ""

    # Extract the base name without the directory path or file extension.
    base = os.path.basename(name)
    base, _ = os.path.splitext(base)
    # Split the base name into alphanumeric tokens, filtering out empty strings.
    tokens = [t for t in re.split(r"[^A-Za-z0-9]+", base) if t]
    
    if not tokens:
        return ""

    # Convert valid tags to a set of uppercase for efficient case-insensitive lookup.
    codes = {t.upper() for t in valid_tags}

    if mode == "pos":
        # In 'pos' mode, the suffix is considered the last purely numeric token.
        # This is typically used for position-based naming where the suffix is an index.
        for token in reversed(tokens):
            if token.isdigit():
                logger.debug(f"Extracted position suffix '{token}' from {name}")
                return token
        logger.debug(f"No position suffix found in {name}")
        return ""

    elif mode == "pa_mat":
        # In 'pa_mat' mode, the suffix is everything after the date, excluding trailing numbers.
        date_index = _find_date_index(tokens)
        if date_index is None:
            logger.debug(f"No date found in {name} for pa_mat suffix extraction.")
            return ""

        # Collect tokens that appear after the date.
        suffix_tokens = tokens[date_index + 1 :]
        if not suffix_tokens:
            logger.debug(f"No tokens after date in {name} for pa_mat suffix extraction.")
            return ""

        # Remove any purely numeric tokens from the end (e.g., index counters).
        suffix_tokens = _strip_numeric_tokens(suffix_tokens, from_start=False)
        
        suffix = "_".join(suffix_tokens)
        logger.debug(f"Extracted pa_mat suffix '{suffix}' from {name}")
        return suffix

    else: # Default to "normal" mode
        # In "normal" mode, the suffix is everything after the date, excluding leading/trailing numbers
        # and ensuring it's not a single known tag.
        date_index = _find_date_index(tokens)
        if date_index is None:
            logger.debug(f"No date found in {name} for normal suffix extraction.")
            return ""

        # Collect tokens that appear after the date.
        suffix_tokens = tokens[date_index + 1 :]
        if not suffix_tokens:
            logger.debug(f"No tokens after date in {name} for normal suffix extraction.")
            return ""

        # Remove any purely numeric tokens from the start and end.
        suffix_tokens = _strip_numeric_tokens(suffix_tokens, from_start=True)
        suffix_tokens = _strip_numeric_tokens(suffix_tokens, from_start=False)

        if not suffix_tokens:
            logger.debug(f"Suffix tokens became empty after stripping numbers in {name}.")
            return ""
        
        # Join remaining tokens to form the potential suffix.
        suffix = "_".join(suffix_tokens)
        
        # If the resulting suffix consists of a single token that is a known tag code,
        # it's not considered a custom suffix.
        if len(suffix_tokens) == 1 and suffix.upper() in codes:
            logger.debug(f"Suffix '{suffix}' is a known tag, ignoring as custom suffix for {name}.")
            return ""
        
        logger.debug(f"Extracted normal suffix '{suffix}' from {name}")
        return suffix