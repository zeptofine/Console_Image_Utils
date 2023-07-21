import multiprocessing
import sys


def get_base_prefix_compat() -> str | None:
    """Get base/real prefix, or sys.prefix if there is none."""
    return (
        getattr(sys, "base_prefix", None)
        or getattr(sys, "real_prefix", None)
        or sys.prefix
    )


def in_virtualenv() -> bool:
    return get_base_prefix_compat() != sys.prefix


def assert_virtualenv(errstring: str = "Not in virtualenv") -> None:
    if not in_virtualenv():
        raise AssertionError(errstring)


def is_subprocess() -> bool:
    return multiprocessing.current_process().name != "MainProcess"


def get_pid() -> int:
    """Get the current process PID."""
    return int(multiprocessing.current_process().name.rsplit("-", 1)[-1])
