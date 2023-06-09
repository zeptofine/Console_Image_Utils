from abc import abstractmethod
from typing import TYPE_CHECKING

from polars import DataFrame, Expr, PolarsDataType

if TYPE_CHECKING:
    from pathlib import Path


class Comparable:
    @abstractmethod
    def compare(self, lst: list, cols: DataFrame) -> list:
        """Uses collected data to return a new list of only valid images, depending on what the filter does."""
        raise NotImplementedError


class FastComparable:
    @abstractmethod
    def fast_comp(self) -> Expr | bool:
        """Returns an Expr that can be used to filter more efficiently, in Rust"""
        raise NotImplementedError


# pylint: disable=unused-argument
class DataFilter:
    """An abstract DataFilter format, for use in DatasetBuilder."""

    def __init__(self) -> None:
        self.is_fast = False
        self.origin = None
        self.filedict: dict[str, Path] = {}  # used for certain filters, like Existing
        self.column_schema: dict[str, PolarsDataType] = {}
        self.build_schema: dict[str, Expr] | None = None

    def set_origin(self, value: str) -> None:
        """sets the filter's origin."""
        self.origin = value

    def __repr__(self) -> str:
        attrlist = [
            f"{key}=..."
            if hasattr(val, "__iter__") and not isinstance(val, str)
            else f"{key}={val}"
            for key, val in self.__dict__.items()
        ]
        return f"{self.__class__.__name__}({', '.join(attrlist)})"

    def __str__(self) -> str:
        return self.__class__.__name__
