from collections.abc import Callable, Iterable
from pathlib import Path

import imagehash
import imagesize
import polars as pl
from PIL import Image
from polars import DataFrame, Expr

from .base_filters import Comparable, DataFilter, FastComparable


class ResFilter(DataFilter, FastComparable):
    def __init__(
        self,
        minsize: int | None,
        maxsize: int | None,
        crop_mod: bool,
        scale: int,
    ) -> None:
        super().__init__()
        self.min: int | None = minsize
        self.max: int | None = maxsize
        self.crop: bool = crop_mod
        self.scale: int = scale
        self.column_schema = {"resolution": pl.List(int)}
        self.build_schema = {"resolution": pl.col("path").apply(imagesize.get)}

    def fast_comp(self) -> Expr | bool:
        if self.crop:
            return pl.col("resolution").apply(
                lambda lst: self.is_valid(map(self.resize, lst)),
            )
        return pl.col("resolution").apply(
            lambda lst: all(dim % self.scale == 0 for dim in lst)
            and self.is_valid(lst),
        )

    def is_valid(self, lst: Iterable[int]) -> bool:
        lst = set(lst)
        return not (
            (self.min and min(lst) < self.min) or (self.max and max(lst) > self.max)
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

        self.hasher: Callable[[Image.Image], imagehash.ImageHash] = IMHASH_TYPES[
            hash_choice
        ]
        self.resolver: Callable[[], Expr | bool] = imhash_resolvers[resolver]
        self.column_schema = {"hash": str, "modifiedtime": pl.Datetime}  # type: ignore
        self.build_schema: dict[str, Expr] = {
            "hash": pl.col("path").apply(self._hash_img),
        }

    def compare(self, lst: Iterable[str], cols: DataFrame) -> set[str]:
        applied: DataFrame = (
            cols.filter(
                pl.col("hash").is_in(
                    cols.filter(pl.col("path").is_in(lst))
                    .select(pl.col("hash"))
                    .unique()
                    .to_series(),
                ),
            )
            .groupby("hash")
            .apply(lambda df: df.filter(self.resolver()) if len(df) > 1 else df)
        )

        return set(applied.select(pl.col("path")).to_series())

    def _hash_img(self, pth: str) -> str:
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
        sizes: Expr = pl.col("path").apply(lambda p: Path(p).stat().st_size)
        return sizes == sizes.max()
