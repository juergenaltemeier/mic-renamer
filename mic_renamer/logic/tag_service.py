"""Utility functions around tag operations."""
from __future__ import annotations

import os
import re
from typing import Iterable


def extract_tags_from_name(name: str, valid_tags: Iterable[str]) -> set[str]:
    """Extract known tag codes from a file name.

    Parameters
    ----------
    name: str
        File name or path to analyze.
    valid_tags: Iterable[str]
        Collection of valid tag codes.

    Returns
    -------
    set[str]
        Tags found in ``name`` that are present in ``valid_tags``.
    """
    base = os.path.basename(name)
    base, _ = os.path.splitext(base)
    tokens = re.split(r"[^A-Za-z0-9]+", base)
    codes = set(valid_tags)
    return {t for t in tokens if t in codes}


def extract_suffix_from_name(name: str, valid_tags: Iterable[str]) -> str:
    """Return the trailing token from ``name`` if it represents a custom suffix.

    The file name is split into alphanumeric tokens. The last token is returned
    unless it matches one of the following patterns:

    * a 6 digit date in ``YYMMDD`` format
    * a purely numeric index
    * a known tag code from ``valid_tags``

    Parameters
    ----------
    name: str
        File name or path to analyze.
    valid_tags: Iterable[str]
        Collection of valid tag codes.

    Returns
    -------
    str
        The extracted suffix or an empty string if none was found.
    """
    base = os.path.basename(name)
    base, _ = os.path.splitext(base)
    tokens = [t for t in re.split(r"[^A-Za-z0-9]+", base) if t]
    if not tokens:
        return ""
    candidate = tokens[-1]
    codes = set(valid_tags)
    if candidate in codes:
        return ""
    if re.fullmatch(r"\d{6}", candidate):
        return ""
    if candidate.isdigit():
        return ""
    return candidate
