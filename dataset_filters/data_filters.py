from __future__ import annotations

from datetime import datetime
from pathlib import Path

import polars as pl
from polars import DataFrame, Expr

from util.file_list import get_file_list, to_recursive

from .base_filters import DataFilter, FastComparable


class StatFilter(DataFilter, FastComparable):
    def __init__(self, beforetime: datetime | None, aftertime: datetime | None) -> None:
        super().__init__()
        self.before: datetime | None = beforetime
        self.after: datetime | None = aftertime
        self.column_schema = {"modifiedtime": pl.Datetime}
        self.build_schema: dict[str, Expr] = {
            "modifiedtime": pl.col("path").apply(StatFilter.get_modified_time),
        }

    @staticmethod
    def get_modified_time(path: str) -> datetime:
        path = Path(path)
        return datetime.fromtimestamp(path.stat().st_mtime)

    def fast_comp(self) -> Expr | bool:
        param: Expr | bool = True
        if self.after:
            param = param & (self.after < pl.col("modifiedtime)"))
        if self.before:
            param = param & (self.before > pl.col("modifiedtime"))
        return param


class BlacknWhitelistFilter(DataFilter, FastComparable):
    def __init__(
        self,
        whitelist: list[str] | None = None,
        blacklist: list[str] | None = None,
    ) -> None:
        super().__init__()
        self.whitelist: list[str] = whitelist or []
        self.blacklist: list[str] = blacklist or []

    def compare(self, lst: list[str], _: DataFrame) -> set:
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

    def _whitelist(self, imglist: list[str], whitelist: list[str]) -> filter:
        return filter(lambda x: any(x in white for white in whitelist), imglist)

    def _blacklist(self, imglist: list[str], blacklist: list[str]) -> filter:
        return filter(lambda x: all(x not in black for black in blacklist), imglist)


class ExistingFilter(DataFilter, FastComparable):
    def __init__(self, hr_folder: str, lr_folder: str, recursive: bool = True) -> None:
        super().__init__()
        self.existing_list = ExistingFilter._get_existing(hr_folder, lr_folder)
        # print(self.existing_list)
        self.recursive = recursive

    def fast_comp(self) -> Expr | bool:
        return pl.col("path").apply(
            lambda x: to_recursive(self.filedict[str(x)], self.recursive).with_suffix(
                "",
            )
            not in self.existing_list,
        )

    @staticmethod
    def _get_existing(*folders: Path) -> set:
        return set.intersection(
            *(
                {
                    file.relative_to(folder).with_suffix("")
                    for file in get_file_list(folder / "**" / "*")
                }
                for folder in folders
            ),
        )
