import time
from collections.abc import Callable, Generator, Iterable
from os import get_terminal_size
from typing import Self, TypeVar

from rich import print as rprint


def byte_format(size, leading: int = 3, trailing: int = 4, suffix: str = "B") -> str:
    """modified version of: https://stackoverflow.com/a/1094933"""
    if isinstance(size, str):
        size = "".join([val for val in size if val.isnumeric()])
    if size := str(size):
        size = int(size)
        unit = ""
        for unit in [unit, "Ki", "Mi", "Gi", "Ti"]:
            if abs(size) < 2**10:
                return f"{size:{leading + trailing + 1}.{trailing}f}{unit}{suffix}"
            size /= 2**10
        return f"{size:3.1f}{unit}{suffix}"
    return f"N/A{suffix}"


def pbar(
    iteration: int,
    total: int,
    length: int = 20,
    fill: str = "#",
    nullp: str = "-",
    corner: str = "[]",
    pref: str = "",
    suff: str = "",
) -> str:
    filled: int = (length * iteration) // total
    #    [#############################]
    c1, c2 = "\033[92m", "\033[93m"
    return f"{pref}{c1}{corner[0]}{c2}{(fill*length)[:filled]:{nullp}<{length}}{c1}{corner[1]}\033[0m{suff}"


def isbar(iteration: int, total: int, suff: str = "", **kwargs) -> str:
    return f"{pbar(iteration, total, **kwargs)} {iteration:{len(str(total))}}/{total} {suff}"


T = TypeVar("T")


def ipbar(
    iterable: Iterable[T],
    total: int = 100,
    refresh_interval: float = 0.25,
    end: str = "\r",
    very_end: str = "\n",
    clear: bool = False,
    print_item: bool = False,
    **kwargs,
) -> Generator[T, None, None]:
    _time: float = time.time()
    for i, obj in enumerate(iterable):
        yield obj
        newtime = time.time()
        if newtime - _time > refresh_interval:  # refresh interval
            output = isbar(i + 1, total, **kwargs)
            if print_item:
                output += f" {obj!s}"
            print(f"\033[K{output}", end=end)
            _time = newtime
    print(isbar(total, total, **kwargs), end="\033[2K\r" if clear else very_end)


def thread_status(pid: int, item: str = "", extra: str = "", item_size: int | None = None) -> None:
    """I don't know whether I should keep this or not. Don't really need it anymore"""
    item_size = item_size or get_terminal_size().columns
    message = f"{pid}: {item}".ljust(item_size)[: item_size - len(extra)] + extra
    print(("\n" * pid) + message + ("\033[A" * pid), end="\r")


PRINT_MODES: dict[str, tuple[str, str]] = {"newline": ("", "\n"), "sameline": ("\033[2K", ""), "append": ("", "")}


class Stepper:
    def __init__(self, step: int = 0, print_mode: str = "newline", print_method: Callable = print) -> None:
        self.step = step
        self.print_mode: tuple[str, str] = PRINT_MODES[print_mode]
        self.printer = print_method

    def next(self, s: str | None = None, **kwargs) -> Self:
        self.step += 1
        if s:
            self._print(s, **kwargs)
        return self

    def print(self, *lines: str, **kwargs) -> Self:
        for line in [f" {self.step}:{s}" for s in lines]:
            self._print(line, **kwargs)
        return self

    # override for print_modes
    def _print(self, *args, **kwargs) -> None:
        args = self.print_mode[0] + args[0], *args[1:]
        self.printer(*args, end=self.print_mode[1], **kwargs)


class RichStepper(Stepper):
    def __init__(self, *args, loglevel: int = 0, stepcolor: str = "cyan", pstepcolor: str = "blue", **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.printer = rprint
        self.loglevel = loglevel
        self.stepcolor = stepcolor
        self.pstepcolor = pstepcolor

    def set(self, n: int) -> Self:
        self.step = n
        return self

    def next(self, s: str | None = None, **kwargs) -> Self:
        self.step += 1
        if s:
            self._print(f"\n[{self.stepcolor}]{self.step}:[/{self.stepcolor}] {s}", **kwargs)
        else:
            self._print(f"\n[{self.stepcolor}]{self.step}:[/{self.stepcolor}]", **kwargs)
        return self

    def print(self, *lines: str, **kwargs) -> Self:
        if isinstance(lines[0], int) or str(lines[0]).isdigit():
            level = int(lines[0])
            lines = lines[1:]
        else:
            level = 0
        printed_output = {
            0: "[bold yellow]INFO[/bold yellow]",
            1: "[bold orange]WARNING[/bold orange]",
            -1: "[bold grey]DEBUG[/bold grey]",
            2: "[bold red]ERROR[/bold red]",
            3: "[bold white]CRITICAL[/bold white]",
        }.get(level, f"[{self.pstepcolor}]{level}:[/{self.pstepcolor}]")
        prefix = f" [{self.pstepcolor}]{self.step}:[/{self.pstepcolor}]"
        if self.loglevel <= level:
            prefix += f"{printed_output}:"
        for line in lines:
            self._print(f"{prefix} {line}")
        return self


class Timer:
    def __init__(self, timestamp: int | None = None) -> None:
        self.time = timestamp or time.perf_counter()

    def print(self, msg: str) -> float:
        """print and resets time"""
        return self.poll(msg).reset()

    def poll(self, msg: str = "") -> Self:
        """print without resetting time"""
        print(f"{time.perf_counter() - self.time}: {msg}")
        return self

    def reset(self) -> float:
        """resets time"""
        self.time = time.perf_counter()
        return self.time

    def __str__(self) -> str:
        return self.__repr__()

    def __repr__(self) -> str:
        return str((time.perf_counter()) - self.time)
