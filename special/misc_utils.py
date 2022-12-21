'''misc_utils, mainly for CreateDataset'''
import json
import multiprocessing.pool as mpp
import os
import re
import sys
from multiprocessing import Pool

from tqdm import tqdm

# from multiprocessing import Pool, Queue


def get_base_prefix_compat():
    """Get base/real prefix, or sys.prefix if there is none."""
    return getattr(sys, "base_prefix", None) or getattr(sys, "real_prefix", None) or sys.prefix


def in_virtualenv() -> bool:
    return get_base_prefix_compat() != sys.prefix


def assert_virtualenv(errstring: str = "Not in virtualenv") -> None:
    if not in_virtualenv():
        raise AssertionError(errstring)


# Stolen from: https://stackoverflow.com/a/57364423
# istarmap.py for Python 3.8+
def istarmap(self, func, iterable, chunksize=1):
    """starmap-version of imap
    """
    self._check_running()
    if chunksize < 1:
        raise ValueError(
            "Chunksize must be 1+, not {0:n}".format(
                chunksize))

    task_batches = mpp.Pool._get_tasks(  # type: ignore
        func, iterable, chunksize)
    result = mpp.IMapIterator(self)
    self._taskqueue.put(
        (
            self._guarded_task_generation(result._job,  # type: ignore
                                          mpp.starmapstar,  # type: ignore
                                          task_batches),
            result._set_length  # type: ignore
        ))
    return (item for chunk in result for item in chunk)


mpp.Pool.istarmap = istarmap  # type: ignore


def poolmap(threads, func, iterable, use_tqdm, chunksize=1, refresh=False, **tqargs) -> list:
    with Pool(threads) as pool:
        output = [None]*len(iterable)
        if use_tqdm:
            itqdm = tqdm(total=len(iterable), **tqargs)
            for result in pool.istarmap(  # type: ignore
                    func, iterable, chunksize=chunksize):
                # itqdm.write(str(result))
                itqdm.set_description_str(str(result), refresh=False)
                output.append(result)
                itqdm.update()
                if refresh:
                    itqdm.refresh()
        else:
            for result in pool.istarmap(func,  # type: ignore
                                        iterable, total=len(iterable)):
                output.append(result)
    return [i for i in output if i is not None]


try:
    from rich import print as rprint
except ImportError:
    rprint = print

ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')


def p_bar(iteration: int, total: int, length=20,
          fill="#", nullp="-", corner="[]", pref='', suff='') -> str:
    """
    Print a progress bar.

    :param iteration: Current iteration.
    :param total: Total iterations.
    :param length: Progress bar length.
    :param fill: Progress bar fill character."""
    color1, color2 = (
        "\033[93m", "\033[92m")
    filledLength = (length * iteration) // total
    #    [#############################]
    pbar = (fill*length)[:filledLength] + (nullp*(length - filledLength))
    command = f"{str(pref)}{color2}{corner[0]}{color1}{pbar}{color2}{corner[1]}\033[0m{str(suff)}"
    return command


def thread_status(pid: int, item: str = "", extra: str = "", anonymous: bool = False,
                  item_size=None) -> None:
    len_extra = len(ansi_escape.sub('', extra))
    item_size = item_size if item_size else os.get_terminal_size().columns
    output = f"{pid}: "
    output += f"{item}" if not anonymous else ""
    output = output[:item_size-len_extra-2]
    output += (" "*item_size + extra)[len(output)+len_extra+1:]
    output = ('\n'*pid) + output + ('\033[A'*pid)
    print(output, end="\r")


class numFmt:
    # '''classes of bits and bytes to assist conversion'''
    class Bit:
        #     '''Bits to assist conversion between:
        #         - metric (MBit, etc.),
        #         - iec (Mibit, etc.)'''
        def __init__(self, amount):
            self.amount = amount
            # * IEC
            self.iec = ['bit', 'Kibit', 'Mibit',
                        'Gibit', 'Tibit', 'Pibit',
                        'Eibit', 'Zibit', 'Yibit']
            # * Metric
            self.metric = ['bit', 'kbit', 'Mbit',
                           'Gbit', 'Tbit', 'Pbit',
                           'Ebit', 'Zbit', 'Ybit']

        def fmt_iec(self) -> tuple:
            for count, fmt in enumerate(self.iec):
                num = self.amount / (2**10)**count
                if (num <= (2**10) and (num >= 1)):
                    return (num, fmt)
            return (-1, "NaN")

        def fmt_metric(self) -> tuple:
            for count,  fmt in enumerate(self.metric):
                num = self.amount / (10**3)**count
                if (num < (10**3)) and (num >= 1):
                    return (num, fmt)
            return (-1, "NaN")

        def to_bytes(self):
            return numFmt.Byte(self.amount / 8)

        def __str__(self):
            return str(self.amount)

        def dict(self):
            return self.__dict__

    class Byte:
        '''Bytes to assist conversion between:
            - metric (MB, etc.),
            - iec (Mib, etc.)'''

        def __init__(self, amount):
            self.amount = amount
            # * IEC
            self.iec = ['B', 'KiB', 'MiB',
                        'GiB', 'TiB', 'PiB',
                        'EiB', 'ZiB', 'YiB']
            # * Metric
            self.metric = ['B', 'kB', 'MB',
                           'GB', 'TB', 'PB',
                           'EB', 'ZB', 'YB']

        def fmt_iec(self) -> tuple:
            for count, fmt in enumerate(self.iec):
                num = self.amount / (2**10)**count
                if (num <= (2**10) and (num >= 1)):
                    return (num, fmt)
            return (-1, "NaN")

        def fmt_metric(self) -> tuple:
            for count, fmt in enumerate(self.metric):
                num = self.amount / (10**3)**count
                if (num < (10**3)) and (num >= 1):
                    return (num, fmt)
            return (-1, "NaN")

        def __str__(self):
            return str(self.amount)

        def to_bits(self):
            return numFmt.Bit(self.amount * 8)

        def dict(self):
            return self.__dict__


if __name__ == "__main__":
    machinesize = numFmt.Byte(1000000)
    rprint(machinesize.dict())
    rprint(machinesize)
    rprint(machinesize.fmt_iec())
    rprint(machinesize.fmt_metric())
    machinesize = numFmt.Bit(1000000)
    rprint(machinesize.dict())
    rprint(machinesize)
    rprint(machinesize.fmt_iec())
    rprint(machinesize.fmt_metric())
