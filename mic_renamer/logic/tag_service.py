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

    suffix_tokens = tokens[date_index + 1 :]
    if not suffix_tokens:
        return ""
    if suffix_tokens[-1].isdigit():
        suffix_tokens = suffix_tokens[:-1]
    if not suffix_tokens:
        return ""

    suffix = "_".join(suffix_tokens)
    codes = set(valid_tags)
    if len(suffix_tokens) == 1 and suffix in codes:
        return ""
    return suffix
