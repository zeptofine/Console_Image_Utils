'''print_utils, mainly for CreateDataset'''
try:
    from rich import print as rprint
except ImportError:
    rprint = print
import os
import sys
import subprocess


def pBar(iteration: int, total: int, length=10,
         fill="#", nullp="-", corner="[]", pref='', suff=''):
    color1, color2 = (
        "\033[93m", "\033[92m")
    filledLength = (length * iteration) // total
    #    [############################# --------------------------------]
    bar = (fill*length)[:filledLength] + (nullp*(length - filledLength))
    command = f"{color2}{corner[0]}{color1}{bar}{color2}{corner[1]}\033[0m"
    command = str(pref)+command+str(suff)
    return command


def thread_status(pid, item="", extra="", anonymous=False, extraSize=8):
    output = f"\033[K {str(pid).ljust(3)} | {str(extra).center(extraSize)}"
    output += f" | {item}" if not anonymous else " | ..."
    output = ('\n'*pid) + output + ('\033[A'*pid)
    print(output, end="\r")


def nextStep(order, text):
    '''prints the steps in accord to CreateDataset'''
    rprint(" "+f"{str(order)}. {text}", end="\n\033[K")


def getPackages(pip=''):
    '''Gets every package available to a given python installation.
        Use a table for the pip argument if it contains multiple commands.'''
    command = [sys.executable, '-m', 'pip']
    if pip:
        if isinstance(pip, list):
            command = pip  # [python -m pip]
    command += ['list', '--format=json']
    x0 = subprocess.check_output(command).decode('UTF-8')
    x1 = eval(x0)
    x2 = {i['name']: i['version'] for i in x1}
    return x2


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
    packages = getPackages()
    # rprint(packages)
    # rprint(f"{len(packages.keys())} individual packages")
