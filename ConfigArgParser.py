import argparse
import os
import json
from sys import exit as sys_exit


class CfgDict(dict):
    def __init__(self, cfg_path, config: dict = {}):
        self.cfg_path = cfg_path
        self.load()
        self.update(config)

    def set_path(self, path):
        self.cfg_path = path
        self.load()
        return self

    def save(self, outdict=None, indent=4):
        if not outdict:
            outdict = self
        with open(self.cfg_path, 'w+') as f:
            f.write(json.dumps(outdict, indent=indent))
        self.load()
        return self

    def load(self):
        if os.path.exists(self.cfg_path):
            with open(self.cfg_path, 'r', encoding='utf-8') as config_file:
                try:
                    self.update(json.load(config_file))
                except (json.decoder.JSONDecodeError, TypeError):
                    print(
                        f'[!] failed to load config.json from {self.cfg_path}, making an empty one')
                    self.save({})
        else:
            self.save({})
        return self


class ConfigParser:
    '''Creates an easy argparse config utility. 
    It saves given args to a path, and returns them when args are parsed again.'''

    def __init__(self, parser: argparse.ArgumentParser,
                 config_path, autofill: bool = False, exit_on_change: bool = False, rewrite_help: bool = True) -> None:
        '''
        parser: argparse function.
        config_path: a path to the supposed json file
        autofill: when creating the json, fill it with the initial default values.
        Otherwise, it will only contain edited defaults.
        exit_on_change: when commands set and reset are passed, exit once finished.
        rewrite_help: remove and readd help argument to properly write defaults.
        '''

        # parent parser
        self._parent = parser
        self.config_path = config_path
        self.default_prefix = '-' if '-' in self._parent.prefix_chars else self._parent.prefix_chars[0]
        self.exit_on_change = exit_on_change
        self.rewrite_help = rewrite_help
        self.autofill = autofill
        self.file = CfgDict(config_path).save()

        self._remove_help()

        # set up subparser
        self.parser = argparse.ArgumentParser(
            prog=self._parent.prog,
            usage=self._parent.usage,
            description=self._parent.description,
            epilog=self._parent.epilog,
            parents=[self._parent],
            formatter_class=self._parent.formatter_class,
            prefix_chars=self._parent.prefix_chars,
            fromfile_prefix_chars=self._parent.fromfile_prefix_chars,
            argument_default=self._parent.argument_default,
            conflict_handler=self._parent.conflict_handler,
            add_help=False,
            allow_abbrev=self._parent.allow_abbrev,
            exit_on_error=True
        )

        # Add config options
        self.config_option_group = self.parser.add_argument_group(
            'Config options')
        self.config_options = self.config_option_group.add_mutually_exclusive_group()
        setattr(self.config_option_group, "config_path", self.config_path)
        self.config_option_group.add_argument(self.default_prefix*2+"config_path", type=str,
                                              default=self.config_path, metavar="PATH",
                                              help="select a config to read from.")
        self.config_options.add_argument(self.default_prefix*2+"set", nargs=2, metavar=('KEY', 'VAL'),
                                         help="change a default argument's options")
        self.config_options.add_argument(self.default_prefix*2+"reset", metavar='VALUE', nargs="*",
                                         help="removes a changed option.")
        self.config_options.add_argument(self.default_prefix*2+"reset_all", action="store_true",
                                         help="resets every option.")
        # get args without triggering help
        self.parsed_args, _ = self.parser.parse_known_args()
        # Add flags
        self.kwargs = {i[0]: i[1] for i in self.parsed_args._get_kwargs()}
        self.config_path = self.kwargs['config_path']

        # exclude set, reset from config
        for i in ['set', 'reset', 'reset_all']:
            self.kwargs.pop(i, None)

        # get args from config_path
        self.file.load()

        self.set_defaults(self.file)

    # modified from argparse.py ( self.set_defaults(**kwargs) )

    def set_defaults(self, argdict: dict):
        self.parser._defaults.update(argdict)
        for action in self.parser._actions:
            if action.dest in argdict:
                action.default = argdict[action.dest]
        self.file.save(self.parser._defaults)

    def parse_args(self, **kwargs) -> argparse.Namespace:
        '''args.set, reset, reset_all logic '''
        self.parsed_args, _ = self.parser.parse_known_args(**kwargs)
        # set defaults
        if self.parsed_args.set or \
                self.parsed_args.reset or \
                self.parsed_args.reset_all:
            if self.parsed_args.set:
                potential_args = self.parsed_args.set
                # convert potential_args to respective types
                potential_args = self._convert_type(potential_args)

                if not potential_args[0] in self.kwargs:
                    sys_exit("Given key not found")

                self.file[potential_args[0]] = potential_args[1]
            elif self.parsed_args.reset:
                for arg in self.parsed_args.reset:
                    self.file.pop(arg, None)
            elif self.parsed_args.reset_all:
                self.file = {}

            self.set_defaults(self.file)

            if self.exit_on_change:
                sys_exit()

        self._add_help()

        return self.parser.parse_args()

    def _convert_type(self, potential_args: list):
        if potential_args[1].lower() in ["true", "false"]:
            if potential_args[1].lower() == "true":
                potential_args[1] = True
            else:
                potential_args[1] = False
        elif potential_args[1].lower() in ["none", "null"]:
            potential_args[1] = None
        elif potential_args[1].isdigit():
            potential_args[1] = int(potential_args[1])
        return potential_args

    def _remove_help(self):
        if self._parent.add_help and self.rewrite_help:
            self._parent._actions.pop(0)
            self._parent._option_string_actions.pop(f'{self.default_prefix}h')
            self._parent._option_string_actions.pop(
                f'{self.default_prefix*2}help')

    def _add_help(self):
        if self._parent.add_help and self.rewrite_help:
            self.parser.add_argument(
                f"{self.parser.prefix_chars}h",
                f"{self.parser.prefix_chars*2}help",
                action='help', default=argparse.SUPPRESS,
                help=('show this help message and exit')
            )
