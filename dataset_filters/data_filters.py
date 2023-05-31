import os
from datetime import datetime
from pathlib import Path

import imagehash
import imagesize
import polars as pl
from PIL import Image
from polars import DataFrame, Expr

from util.file_list import get_file_list, to_recursive


class DataFilter:
    '''An abstract DataFilter format, for use in DatasetBuilder.
    '''

    def __init__(self):
        self.mergeable = False
        self.origin = None
        self.filedict = {}  # used for certain filters, like Existing
        self.column_schema = {}
        self.build_schema: dict[str, Expr] | None = None

    def set_origin(self, value):
        self.origin = value

    def compare(self, lst, cols: DataFrame) -> list:
        raise NotImplementedError

    def fast_comp(self) -> Expr:
        raise NotImplementedError

    def __repr__(self):
        attrlist = [
            f"{key}=..." if hasattr(val, "__iter__") and not isinstance(val, str) else f"{key}={val}"
            for key, val in self.__dict__.items()
        ]
        return f"{self.__class__.__name__}({', '.join(attrlist)})"

    def __str__(self):
        return self.__class__.__name__


class StatFilter(DataFilter):
    def __init__(self, beforetime: datetime | None, aftertime: datetime | None):
        super().__init__()
        self.mergeable = True
        self.before = beforetime
        self.after = aftertime
        self.column_schema = {'modifiedtime': pl.Datetime}
        self.build_schema: dict[str, Expr] = {
            'modifiedtime': pl.col('path').apply(lambda x: datetime.fromtimestamp(os.stat(x).st_mtime))  # type: ignore
        }

    def compare(self, lst, cols: DataFrame) -> set:

        files = cols.filter(pl.col('path').is_in(lst))
        files = files.filter(self.fast_comp())

        return set(files.select('path').to_series())

    def fast_comp(self) -> Expr:
        return (
            pl.when(bool(self.after)).then(
                self.after < pl.col('modifiedtime')
            ).otherwise(True)
            & pl.when(bool(self.before)).then(
                self.before > pl.col('modifiedtime')
            ).otherwise(True)
        )


class ResFilter(DataFilter):
    def __init__(self, minsize: int | None, maxsize: int | None, crop_mod: bool, scale: int):
        super().__init__()
        self.mergeable = True
        self.min: int | None = minsize
        self.max: int | None = maxsize
        self.crop: bool = crop_mod
        self.scale: int = scale
        self.column_schema = {'resolution': pl.List(int)}
        self.build_schema = {'resolution': pl.col('path').apply(lambda x: imagesize.get(x))}

    def compare(self, lst, cols: DataFrame) -> set:
        files = cols.filter(pl.col('path').is_in(lst))
        files = files.filter(self.fast_comp())
        return set(files.select(pl.col('path')).to_series())

    def fast_comp(self) -> Expr:
        if self.crop:
            return (
                pl.when(bool(self.min)).then(
                    pl.col('resolution').apply(lambda l: (min(l) // self.scale) * self.scale >= self.min)
                ).otherwise(True)
                & pl.when(bool(self.max)).then(
                    pl.col('resolution').apply(lambda l: (max(l) // self.scale) * self.scale <= self.max)
                ).otherwise(True)
            )
        else:
            return (
                pl.col('resolution').apply(lambda l: all(dim % self.scale == 0 for dim in l)).all()
                & pl.when(bool(self.min)).then(
                    pl.col('resolution').apply(lambda l: min(l) >= self.min)
                ).otherwise(True)
                & pl.when(bool(self.max)).then(
                    pl.col('resolution').apply(lambda l: max(l) <= self.max)
                ).otherwise(True)
            )


IMHASH_TYPES = {
    'average': imagehash.average_hash,
    'crop_resistant': imagehash.crop_resistant_hash,
    'color': imagehash.colorhash,
    'dhash': imagehash.dhash,
    'dhash_vertical': imagehash.dhash_vertical,
    'phash': imagehash.phash,
    'phash_simple': imagehash.phash_simple,
    'whash': imagehash.whash
}


class HashFilter(DataFilter):
    def __init__(self, hash_choice, resolver='newest'):
        super().__init__()

        IMHASH_RESOLVERS = {
            'ignore_all': self._ignore_all,
            'newest': self._accept_newest,
            'oldest': self._accept_oldest,
            'size': self._accept_biggest
        }
        if hash_choice not in IMHASH_TYPES:
            raise KeyError(f"{hash_choice} is not in IMHASH_TYPES")
        if resolver not in IMHASH_RESOLVERS:
            raise KeyError(f"{resolver} is not in IMHASH_RESOLVERS")
        self.hasher = IMHASH_TYPES[hash_choice]
        self.resolver = IMHASH_RESOLVERS[resolver]
        self.column_schema = {'hash': str, 'modifiedtime': pl.Datetime}
        self.build_schema: dict[str, Expr] = {
            'hash': pl.col('path').apply(self._hash_img)
        }
        self.data = None

    def compare(self, lst, cols: DataFrame) -> set:
        applied = (
            cols
            # get all of the files with hashes that correspond to a file in lst
            # how though
            .filter(
                pl.col('hash').is_in(
                    cols.filter(
                        pl.col('path').is_in(lst)
                    ).select(pl.col("hash")).unique().to_series()
                )
            )
            # resolve hash conflicts
            .groupby('hash')
            .apply(
                lambda df: df.filter(self.resolver()) if len(df) > 1 else df
            )
        )

        resolved_paths = set(applied.select(pl.col('path')).to_series())
        return resolved_paths

    # def fast_comp(self) -> Expr:
    #     return (
    #         df

    #         .groupby('hash')
    #         .apply(
    #             lambda df: df.filter(self.resolver()) if len(df) > 1 else df
    #         )
    #     )

    def _hash_img(self, pth):
        return str(self.hasher(Image.open(pth)))

    def _ignore_all(self) -> Expr | bool:
        return False

    def _accept_newest(self) -> Expr:
        return (
            pl.col('modifiedtime') == pl.col('modifiedtime').max()
        )

    def _accept_oldest(self) -> Expr:
        return (
            pl.col('modifiedtime') == pl.col('modifiedtime').min()
        )

    def _accept_biggest(self) -> Expr:
        sizes = pl.col("path").apply(lambda p: os.stat(str(p)).st_size)
        return (sizes == sizes.max())


class BlacknWhitelistFilter(DataFilter):
    def __init__(self, whitelist=[], blacklist=[]):
        super().__init__()
        self.mergeable = True
        self.whitelist = whitelist
        self.blacklist = blacklist

    def compare(self, lst, cols: DataFrame) -> set:
        out = lst
        if self.whitelist:
            out = self._whitelist(out, self.whitelist)
        if self.blacklist:
            out = self._blacklist(out, self.blacklist)
        return out

    def fast_comp(self) -> Expr | bool:
        args = True
        if self.whitelist:
            for item in self.whitelist:
                args = args & pl.col('path').str.contains(item)

        if self.blacklist:
            for item in self.blacklist:
                args = args & pl.col('path').str.contains(item).is_not()
        return args

    def _whitelist(self, imglist, whitelist) -> set:
        return {j for i in whitelist for j in imglist if i in str(j)}

    def _blacklist(self, imglist, blacklist) -> set:
        return set(imglist).difference(self._whitelist(imglist, blacklist))


class ExistingFilter(DataFilter):
    def __init__(self, hr_folder, lr_folder, recursive=True):
        super().__init__()
        self.mergeable = True
        self.existing_list = ExistingFilter._get_existing(hr_folder, lr_folder)
        # print(self.existing_list)
        self.recursive = recursive

    def compare(self, lst, cols: DataFrame) -> list:
        print("Exist")
        for i in lst:
            print(to_recursive(self.filedict[i], self.recursive).with_suffix(""))
        return [
            i
            for i in lst
            if to_recursive(self.filedict[i], self.recursive).with_suffix("") not in self.existing_list
        ]

    def fast_comp(self) -> Expr:
        return (
            pl.col('path').apply(
                lambda p: to_recursive(self.filedict[p], self.recursive).with_suffix("") not in self.existing_list
            )
        )

    @ staticmethod
    def _get_existing(*folders: Path) -> set:
        return set.intersection(*(
            {
                file.relative_to(folder).with_suffix('')
                for file in get_file_list((folder / "**" / "*"))
            }
            for folder in folders
        ))
