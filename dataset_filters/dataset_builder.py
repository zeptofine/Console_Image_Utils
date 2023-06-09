import os
from collections.abc import Iterable
from datetime import datetime
from pathlib import Path

import polars as pl
from cfg_argparser import CfgDict
from polars import DataFrame, Expr, PolarsDataType
from rich import print as rprint
from tqdm import tqdm

from util.print_funcs import byte_format

from .base_filters import Comparable, DataFilter, FastComparable


def current_time() -> datetime:
    return datetime.now().replace(microsecond=0)
    # return datetime.fromtimestamp(time.time())


class DatasetBuilder:
    def __init__(self, origin: str, processes=1):
        super().__init__()
        self.filters: list[DataFilter] = []
        self.power: int = processes
        self.origin: str = origin  # necessary for certain filters to work

        self.config = CfgDict(
            "database_config.json",
            {
                "trim": True,
                "trim_age_limit": 60 * 60 * 24 * 7,
                "trim_check_exists": True,
                "save_interval": 500,
                "chunksize": 100,
                "filepath": "filedb.feather",
            },
            autofill=True,
        )
        self.filepath: str = self.config["filepath"]
        self.time_threshold: int = self.config["trim_age_limit"]

        self.basic_schema = {"path": str, "checkedtime": pl.Datetime}
        self.build_schema: dict[str, Expr] = {}  # {col: how to build it}
        if os.path.exists(self.filepath):
            print("Reading database...")
            self.df = pl.read_ipc(self.config["filepath"], use_pyarrow=True)
            print("Finished.")
        else:
            self.df = DataFrame(schema=self.basic_schema)

    def add_filters(self, *filters: DataFilter) -> None:
        """Adds filters to the filter list."""
        for filter_ in filters:
            filter_.set_origin(self.origin)
            self.filters.append(filter_)
            if filter_.build_schema:
                if any(col not in self.build_schema for col in filter_.build_schema):
                    self.add_schema_from_filter(filter_)

    def add_schema_from_filter(self, filter_: DataFilter, overwrite=False):
        assert filter_.build_schema, f"{filter_} has no build_schema"
        if not overwrite:
            assert all(
                key not in self.build_schema for key in filter_.build_schema.keys()
            ), f"Schema is already in build_schema: {self.build_schema}"
        self.build_schema.update(filter_.build_schema)

    def add_optional_from_filter(self, filter_: DataFilter):
        assert filter_.build_schema, f"{filter_} has no build_schema"
        self.build_schema.update(filter_.build_schema)

    def populate_df(self, lst: Iterable[Path]):
        from_full_to_relative: dict[str, Path] = self.absolute_dict(lst)
        abs_paths: set[str] = set(from_full_to_relative.keys())

        # add new paths to the dataframe with missing data
        existing_paths = set(self.df.select(pl.col("path")).to_series())
        new_paths: list[str] = [path for path in abs_paths if path not in existing_paths]
        if new_paths:
            self.df = pl.concat(
                [self.df, DataFrame({"path": new_paths, "checkedtime": [current_time()] * len(new_paths)})],
                how="diagonal",
            )

        modified_schema: dict[str, PolarsDataType] = dict(self.df.schema).copy()
        for filter_ in self.filters:
            filter_.filedict = from_full_to_relative
            schemas: dict[str, PolarsDataType] = filter_.column_schema
            modified_schema.update({schema: value for schema, value in schemas.items() if schema not in self.df.schema})

        full_build_expr: dict[str, Expr] = {
            col: pl.when(pl.col(col).is_null()).then(expr).otherwise(pl.col(col))
            for col, expr in self.build_schema.items()
            if col in self.df.columns or col in modified_schema
        }

        # get paths with missing data
        self.df: DataFrame = DatasetBuilder._make_schema_compliant(self.df, modified_schema)

        print("finding unfinished...")
        unfinished: DataFrame = self.df.filter(pl.any(pl.col(col).is_null() for col in self.df.columns))
        # print(unfinished)
        # print(self.build_schema)
        # print(modified_schema)

        # print(full_build_expr)
        # print(self.filters)

        if len(unfinished):
            print("Gathering...")
            try:
                old_db_size: str = byte_format(self.get_db_disk_size())
                with tqdm(desc="Gathering file info...", total=len(unfinished)) as t:
                    chunksize: int = self.config["chunksize"]
                    save_timer = 0
                    collected_data = DataFrame(schema=modified_schema)  # type: ignore
                    for group in (
                        unfinished.with_row_count("idx").with_columns(pl.col("idx") // chunksize).partition_by("idx")
                    ):
                        group.drop_in_place("idx")
                        new_data: DataFrame = group.with_columns(**full_build_expr)
                        collected_data.vstack(new_data, in_place=True)
                        t.update(len(group))

                        save_timer += len(group)
                        if save_timer > self.config["save_interval"]:
                            self.df = self.df.update(collected_data, on="path")
                            self.save_df()
                            t.set_postfix_str(f"Autosaved at {current_time()}")
                            collected_data: DataFrame = collected_data.clear()
                            save_timer = 0

                    self.df = self.df.update(collected_data, on="path").rechunk()
                    self.save_df()
                    rprint(f"old DB size: [bold red]{old_db_size}[/bold red]")
                    rprint(f"new DB size: [bold yellow]{byte_format(self.get_db_disk_size())}[/bold yellow]")
            except KeyboardInterrupt as exc:
                print("KeyboardInterrupt detected! attempting to save dataframe...")
                self.save_df()
                print("Saved.")
                raise exc

        return

    def filter(self, lst, sort_col="path") -> list[Path]:
        assert (
            sort_col in self.df.columns
        ), f"the column '{sort_col}' is not in the database. Available columns: {self.df.columns}"
        from_full_to_relative: dict[str, Path] = self.absolute_dict(lst)
        paths: set[str] = set(from_full_to_relative.keys())
        with tqdm(self.filters, "Running full filters...") as t:
            vdf: DataFrame = self.df.filter(pl.col("path").is_in(paths)).rechunk()
            count = 0
            for dfilter in self.filters:
                if len(vdf) == 0:
                    break
                if isinstance(dfilter, FastComparable):
                    vdf = vdf.filter(dfilter.fast_comp())
                elif isinstance(dfilter, Comparable):
                    vdf = vdf.filter(
                        pl.col("path").is_in(
                            dfilter.compare(
                                set(vdf.select(pl.col("path")).to_series()),
                                self.df.select(pl.col("path"), *[pl.col(col) for col in dfilter.column_schema]),
                            )
                        )
                    )
                t.update(count + 1)
                count = 0
            t.update(count)
        return [from_full_to_relative[p] for p in vdf.sort(sort_col).select(pl.col("path")).to_series()]

    def get_db_disk_size(self) -> int:
        """gets the database size on disk."""
        if not os.path.exists(self.config["filepath"]):
            return 0
        return os.stat(self.config["filepath"]).st_size

    def save_df(self) -> None:
        """saves the dataframe to self.filepath"""
        self.df.write_ipc(self.filepath)

    def absolute_dict(self, lst: Iterable[Path]) -> dict[str, Path]:
        return {(str((self.origin / pth).resolve())): pth for pth in lst}

    @staticmethod
    def _make_schema_compliant(data_frame: DataFrame, schema) -> DataFrame:
        """adds columns from the schema to the dataframe. (not in-place)"""
        return pl.concat([data_frame, DataFrame(schema=schema)], how="diagonal")

    def __enter__(self, *args, **kwargs):
        self.__init__(*args, **kwargs)
        return self

    def __exit__(self, exc_type, exc_value, exc_traceback):
        pass
