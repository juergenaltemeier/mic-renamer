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
