"""
This module defines the `RenameConfig` class, which serves as a data container
for various configuration parameters used when constructing new file names
during the renaming process.
"""

class RenameConfig:
    """
    Configuration for building new file names.

    Attributes:
        date_format (str): The format string for dates used in file names (e.g., "%y%m%d" for YYMMDD).
        index_padding (int): The number of digits to pad the sequential index with (e.g., 3 for 001, 010).
        separator (str): The character or string used to separate components in the new file name (e.g., "_").
        start_index (int): The starting number for sequential indexing when multiple files share a base name.
    """

    date_format: str = "%y%m%d"
    index_padding: int = 3
    separator: str = "_"
    start_index: int = 1
