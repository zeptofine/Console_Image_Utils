from __future__ import annotations

import os
from abc import abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Callable

import imagehash
import imagesize
import polars as pl
from PIL import Image
from polars import DataFrame, Expr, PolarsDataType

from util.file_list import get_file_list, to_recursive


class Comparable:
    @abstractmethod
    def compare(self, lst, cols: DataFrame) -> list:
        """Uses collected data to return a new list of only valid images, depending on what the filter does."""
        raise NotImplementedError


class FastComparable:
    @abstractmethod
    def fast_comp(self) -> Expr:
        """Returns an Expr that can be used to filter more efficiently, in Rust"""
        raise NotImplementedError


# pylint: disable=unused-argument
class DataFilter:
    """An abstract DataFilter format, for use in DatasetBuilder."""

    def __init__(self):
        self.is_fast = False
        self.origin = None
        self.filedict: dict[str, Path] = {}  # used for certain filters, like Existing
        self.column_schema: dict[str, PolarsDataType] = {}
        self.build_schema: dict[str, Expr] | None = None

    def set_origin(self, value):
        """sets the filter's origin."""
        self.origin = value

    def __repr__(self):
        attrlist = [
            f"{key}=..." if hasattr(val, "__iter__") and not isinstance(val, str) else f"{key}={val}"
            for key, val in self.__dict__.items()
        ]
        return f"{self.__class__.__name__}({', '.join(attrlist)})"

    def __str__(self) -> str:
        return self.__class__.__name__


class StatFilter(DataFilter, FastComparable):
    def __init__(self, beforetime: datetime | None, aftertime: datetime | None):
        super().__init__()
        self.before: datetime | None = beforetime
        self.after: datetime | None = aftertime
        self.column_schema = {"modifiedtime": pl.Datetime}
        self.build_schema: dict[str, Expr] = {
            "modifiedtime": pl.col("path").apply(lambda x: datetime.fromtimestamp(os.stat(str(x)).st_mtime))
        }

    def fast_comp(self) -> Expr:
        return pl.when(bool(self.after)).then(self.after < pl.col("modifiedtime")).otherwise(True) & pl.when(
            bool(self.before)
        ).then(self.before > pl.col("modifiedtime")).otherwise(True)


class ResFilter(DataFilter, FastComparable):
    def __init__(self, minsize: int | None, maxsize: int | None, crop_mod: bool, scale: int):
        super().__init__()
        self.min: int | None = minsize
        self.max: int | None = maxsize
        self.crop: bool = crop_mod
        self.scale: int = scale
        self.column_schema = {"resolution": pl.List(int)}
        self.build_schema = {"resolution": pl.col("path").apply(imagesize.get)}

    def fast_comp(self) -> Expr:
        if self.crop:
            return pl.col("resolution").apply(
                lambda lst: self.resize(min(lst)) >= self.min if self.min else True
            ) & pl.col("resolution").apply(lambda lst: self.resize(max(lst)) <= self.max if self.max else True)

        return (
            pl.col("resolution").apply(lambda lst: all(dim % self.scale == 0 for dim in lst))
            & pl.col("resolution").apply(lambda lst: min(lst) >= self.min if self.min else True)
            & pl.col("resolution").apply(lambda lst: max(lst) <= self.max if self.max else True)
        )

    def resize(self, i: int) -> int:
        return (i // self.scale) * self.scale


IMHASH_TYPES: dict[str, Callable] = {
    "average": imagehash.average_hash,
    "crop_resistant": imagehash.crop_resistant_hash,
    "color": imagehash.colorhash,
    "dhash": imagehash.dhash,
    "dhash_vertical": imagehash.dhash_vertical,
    "phash": imagehash.phash,
    "phash_simple": imagehash.phash_simple,
    "whash": imagehash.whash,
    "whash-db4": lambda img: imagehash.whash(img, mode="db4"),
}


class HashFilter(DataFilter, Comparable):
    def __init__(
        self,
        hash_choice: str = "average",
        resolver: str = "newest",
    ):
        super().__init__()

        imhash_resolvers: dict[str, Callable] = {
            "ignore_all": HashFilter._ignore_all,
            "newest": HashFilter._accept_newest,
            "oldest": HashFilter._accept_oldest,
            "size": HashFilter._accept_biggest,
        }

        if hash_choice not in IMHASH_TYPES:
            raise KeyError(f"{hash_choice} is not in IMHASH_TYPES")
        if resolver not in imhash_resolvers:
            raise KeyError(f"{resolver} is not in IMHASH_RESOLVERS")

        self.hasher: Callable[[Image.Image], imagehash.ImageHash] = IMHASH_TYPES[hash_choice]
        self.resolver: Callable[[], Expr | bool] = imhash_resolvers[resolver]
        self.column_schema = {"hash": str, "modifiedtime": pl.Datetime}  # type: ignore
        self.build_schema: dict[str, Expr] = {"hash": pl.col("path").apply(self._hash_img)}

    def compare(self, lst, cols: DataFrame) -> set:
        filtered = cols.filter(
            pl.col("hash").is_in(cols.filter(pl.col("path").is_in(lst)).select(pl.col("hash")).unique().to_series())
        )
        applied = filtered.groupby("hash").apply(lambda df: df.filter(self.resolver()) if len(df) > 1 else df)

        resolved_paths = set(applied.select(pl.col("path")).to_series())
        return resolved_paths

    def _hash_img(self, pth):
        return str(self.hasher(Image.open(pth)))

    @staticmethod
    def _ignore_all() -> Expr | bool:
        return False

    @staticmethod
    def _accept_newest() -> Expr:
        return pl.col("modifiedtime") == pl.col("modifiedtime").max()

    @staticmethod
    def _accept_oldest() -> Expr:
        return pl.col("modifiedtime") == pl.col("modifiedtime").min()

    @staticmethod
    def _accept_biggest() -> Expr:
        sizes: Expr = pl.col("path").apply(lambda p: os.stat(str(p)).st_size)
        return sizes == sizes.max()


class BlacknWhitelistFilter(DataFilter, FastComparable):
    def __init__(self, whitelist: list[str] | None = None, blacklist: list[str] | None = None):
        super().__init__()
        self.whitelist: list[str] = whitelist or []
        self.blacklist: list[str] = blacklist or []

    def compare(self, lst, cols: DataFrame) -> set:
        out = lst
        if self.whitelist:
            out = self._whitelist(out, self.whitelist)
        if self.blacklist:
            out = self._blacklist(out, self.blacklist)
        return set(out)

    def fast_comp(self) -> Expr | bool:
        args: Expr | bool = True
        if self.whitelist:
            for item in self.whitelist:
                args = args & pl.col("path").str.contains(item)

        if self.blacklist:
            for item in self.blacklist:
                args = args & pl.col("path").str.contains(item).is_not()
        return args

    def _whitelist(self, imglist, whitelist) -> filter:
        return filter(lambda x: any(x in white for white in whitelist), imglist)

    def _blacklist(self, imglist, blacklist) -> filter:
        return filter(lambda x: all(x not in black for black in blacklist), imglist)


class ExistingFilter(DataFilter, FastComparable):
    def __init__(self, hr_folder, lr_folder, recursive=True):
        super().__init__()
        self.existing_list = ExistingFilter._get_existing(hr_folder, lr_folder)
        # print(self.existing_list)
        self.recursive = recursive

    def fast_comp(self) -> Expr:
        return pl.col("path").apply(
            lambda x: to_recursive(self.filedict[str(x)], self.recursive).with_suffix("") not in self.existing_list
        )

    @staticmethod
    def _get_existing(*folders: Path) -> set:
        return set.intersection(
            *(
                {file.relative_to(folder).with_suffix("") for file in get_file_list((folder / "**" / "*"))}
                for folder in folders
            )
        )
