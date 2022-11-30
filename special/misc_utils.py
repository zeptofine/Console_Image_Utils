'''misc_utils, mainly for CreateDataset'''
import argparse
import json
import os
import re
import sys

try:
    from rich import print as rprint
except ImportError:
    rprint = print

ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')


def p_bar(iteration: int, total: int, length=20,
          fill="#", nullp="-", corner="[]", pref='', suff='') -> str:
    """returns a colored progress bar"""
    color1, color2 = (
        "\033[93m", "\033[92m")
    filledLength = (length * iteration) // total
    #    [############################# --------------------------------]
    pbar = (fill*length)[:filledLength] + (nullp*(length - filledLength))
    command = f"{color2}{corner[0]}{color1}{pbar}{color2}{corner[1]}\033[0m"
    command = str(pref)+command+str(suff)
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


def next_step(order, text) -> None:
    rprint(" "+f"{str(order)}: {text}", end="\n\033[K")


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
            # 1000000 / (10**3)**2
            for fmt in enumerate(self.iec):
                num = self.amount / (2**10)**fmt[0]
                if (num <= (2**10) and (num >= 1)):
                    return (num, fmt[1])
            return (-1, "NaN")

        def fmt_metric(self) -> tuple:
            for fmt in enumerate(self.metric):
                num = self.amount / (10**3)**fmt[0]
                if (num < (10**3)) and (num >= 1):
                    return (num, fmt[1])
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
            # 1000000 / (10**3)**2
            for fmt in enumerate(self.iec):
                num = self.amount / (2**10)**fmt[0]
                if (num <= (2**10) and (num >= 1)):
                    return (num, fmt[1])
            return (-1, "NaN")

        def fmt_metric(self) -> tuple:
            for fmt in enumerate(self.metric):
                num = self.amount / (10**3)**fmt[0]
                if (num < (10**3)) and (num >= 1):
                    return (num, fmt[1])
            return (-1, "NaN")

        def __str__(self):
            return str(self.amount)

        def to_bits(self):
            return numFmt.Bit(self.amount * 8)

        def dict(self):
            return self.__dict__


if __name__ == "__main__":
    machinesize = numFmt.Byte(1000000)
    # machinesizeByte = machinesize.to_bytes()
    rprint(machinesize.dict())
    rprint(machinesize)
    rprint(machinesize.fmt_iec())
    rprint(machinesize.fmt_metric())
    machinesize = numFmt.Bit(1000000)
    rprint(machinesize.dict())
    rprint(machinesize)
    rprint(machinesize.fmt_iec())
    rprint(machinesize.fmt_metric())
