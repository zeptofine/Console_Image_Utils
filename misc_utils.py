'''misc_utils, mainly for CreateDataset'''
try:
    from rich import print as rprint
except ImportError:
    rprint = print
import argparse
import json
import os
import subprocess
import sys


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
    output = f"\033[K {pid:03} | {str(extra).center(extraSize)}"
    output += f" | {item}" if not anonymous else ""
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


class configParser:
    '''Creates an easy argparse config utility. It saves arguments given to it. 
    TODO: I haven't tested keys with lists as inputs or anything similar.
    '''

    def __init__(self, parser: argparse.ArgumentParser, config_path, autofill=False, exit_on_change=False):
        '''
        parser: argparse function. initialize before parse_args()

        config_path: a path to the supposed json file

        autofill: when creating the json, fill it with the initial default values.
        Otherwise, it will only contain edited defaults.
        '''
        self.config_path = config_path
        self.parser: argparse.ArgumentParser = parser
        self.config_option_group = self.parser.add_argument_group(
            'Config options')

        # Add config options
        self.run_options = self.config_option_group.add_mutually_exclusive_group()
        self.run_options.add_argument(
            "--set", help="change a default argument's options.", nargs="+", metavar=('KEY', 'VALUE'))
        self.run_options.add_argument(
            "--reset", help="removes a changed option.", metavar='VALUE')

        self.parsed_args = self.parser.parse_args()
        # (key, value) to dict
        self.kwargs = {i[0]: i[1] for i in self.parsed_args._get_kwargs()}
        
        # exclude set, reset from config
        if "set" in self.kwargs.keys():
            self.kwargs.pop('set')
        if 'reset' in self.kwargs.keys():
            self.kwargs.pop('reset')

        # If config doesn't exist, create an empty/filled version
        if not os.path.exists(config_path):
            with open(config_path, "w") as config_file:
                if autofill:
                    config_file.write(json.dumps(self.kwargs, indent=4))
                else:
                    config_file.write(json.dumps({}))
                config_file.close()

        # Read config file
        with open(config_path, "r") as config_file:
            self.edited_keys = json.loads(config_file.read())
            config_file.close()

        # set defaults
        if self.parsed_args.set or self.parsed_args.reset:
            if self.parsed_args.set:
                potential_args = self.parsed_args.set
                # convert to different types
                if potential_args[1].lower() in ["true", "talse"]:
                    if potential_args[1].lower() == "true":
                        potential_args[1] = True
                    else:
                        potential_args[1] = False
                elif potential_args[1].isdigit():
                    potential_args[1] = int(potential_args[1])

                self.edited_keys[potential_args[0]] = potential_args[1]
            elif self.parsed_args.reset:
                if self.parsed_args.reset == 'all':
                    self.edited_keys = {}
                else:
                    self.edited_keys.pop(self.parsed_args.reset)
            with open(config_path, "w") as config_file:
                config_file.write(json.dumps(self.edited_keys, indent=4))
                config_file.close()
            if exit_on_change:
                sys.exit()

        # create exec command to change ArgumentParser defaults
        key_command = []
        for key in self.edited_keys.keys():
            if isinstance(self.edited_keys[key], str):
                key_command.append(f"{key}='{self.edited_keys[key]}'")
                exec(
                    f"self.parser.set_defaults({key}='{self.edited_keys[key]}')")
            else:
                key_command.append(f"{key}={self.edited_keys[key]}")

        # Change ArgumentParser defaults
        exec(f"self.parser.set_defaults({', '.join(key_command)})")

    def parse_args(self):
        '''parse_args passthrough to simplify integration'''
        return self.parser.parse_args()

    def config(self):
        '''returns a dictionary of all the edited options'''
        return self.edited_keys


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
