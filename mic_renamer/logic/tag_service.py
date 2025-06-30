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
    codes = {t.upper() for t in valid_tags}
    return {t.upper() for t in tokens if t.upper() in codes}


def extract_suffix_from_name(name: str, valid_tags: Iterable[str]) -> str:
    """Return custom suffix tokens appearing after the first date segment.

    The file name is split into alphanumeric tokens. All tokens appearing
    after the first ``YYMMDD`` date token are collected.  If the last of these
    tokens is a purely numeric index it is ignored.  Remaining tokens are
    joined with underscores and returned.  When the resulting suffix consists
    of a single known tag code from ``valid_tags``, an empty string is
    returned.

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

    date_index = None
    for i, tok in enumerate(tokens):
        if re.fullmatch(r"\d{6}", tok):
            date_index = i
            break
    if date_index is None:
        return ""

    # All tokens after the first date token are potential suffix parts
    suffix_tokens = tokens[date_index + 1 :]
    if not suffix_tokens:
        return ""
    # Drop any numeric tokens at the start or end (index counters or stray numbers)
    while suffix_tokens and suffix_tokens[0].isdigit():
        suffix_tokens.pop(0)
    while suffix_tokens and suffix_tokens[-1].isdigit():
        suffix_tokens.pop()
    if not suffix_tokens:
        return ""
    # Join remaining tokens as suffix
    suffix = "_".join(suffix_tokens)
    # If the suffix is exactly a known tag code, treat as no suffix
    codes = {t.upper() for t in valid_tags}
    if len(suffix_tokens) == 1 and suffix.upper() in codes:
        return ""
    return suffix
