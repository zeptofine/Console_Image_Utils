from pathlib import Path
from glob import glob
from os import sep


def get_file_list(*folders: Path) -> list[Path]:
    """
    Args    folders: One or more folder paths.
    Returns list[Path]: paths in the specified folders."""

    return {
        Path(y) for x in (
            glob(str(p), recursive=True)
            for p in folders
        )
        for y in x
    }


def to_recursive(path, recursive) -> Path:
    """Convert the file path to a recursive path if recursive is False
    Ex: i/path/to/image.png => i/path_to_image.png"""
    return Path(path) if recursive else Path(str(path).replace(sep, "_"))
