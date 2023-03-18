
import json
import os
from argparse import ArgumentParser, Namespace
from sys import exit as sys_exit


class CfgDict(dict):
    def __init__(self, cfg_path, config: dict = {}):
        super().__init__()
        self.cfg_path = cfg_path
        self.load()
        self.update(config)

    def set_path(self, path):
        self.cfg_path = path
        self.load()
        return self

    def save(self, out_dict=None, indent=4):
        if not isinstance(out_dict, dict):
            out_dict = self
        with open(self.cfg_path, 'w+') as f:
            f.write(json.dumps(out_dict, indent=indent))
        print("saved")
        return self

    def update(self, *args, **kwargs):
        super().update(*args, **kwargs)
        return self

    def pop(self, *args, **kwargs):
        super().pop(*args, **kwargs)
        return self

    def clear(self):
        super().clear()
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

    def __init__(self, parser: ArgumentParser,
                 config_path, cfgObject: CfgDict = None, autofill: bool = False, exit_on_change: bool = False, rewrite_help: bool = True) -> None:
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
        self.file = cfgObject or CfgDict(config_path)
        # self._remove_help()

        # set up subparser
        self.parser = ArgumentParser(
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
        self.config_options.add_argument(self.default_prefix*2+"set", nargs=2, metavar=('KEY', 'VAL'),
                                         help="change a default argument's options")
        self.config_options.add_argument(self.default_prefix*2+"reset", metavar='VALUE', nargs="*",
                                         help="removes a changed option.")
        self.config_options.add_argument(self.default_prefix*2+"reset_all", action="store_true",
                                         help="resets every option.")

        # get defaults from the actions
        self.kwargs = {action.dest: action.default for action in self._parent._actions}

        for i in ['set', 'reset', 'reset_all', 'help']:
            self.kwargs.pop(i, None)

        self.file.load()

        if self.autofill:
            if any(arg not in self.file for arg in self.kwargs):  # To avoid saving every time the parser is run
                for arg in self.kwargs:
                    if arg not in self.file:
                        self.file.update({arg: self.kwargs[arg]})
                self.file.save()

        self.parser.set_defaults(**self.file)

    def parse_args(self, **kwargs) -> Namespace:
        '''args.set, reset, reset_all logic '''

        # Disable every required item so if it was set in the config, it isn't required to add again
        required = {}

        for action in self._parent._actions:
            if action.required:
                required[action.dest] = True
                action.required = False

        self.parsed_args, _ = self.parser.parse_known_args(**kwargs)

        # set defaults
        if self.parsed_args.set or self.parsed_args.reset or self.parsed_args.reset_all:
            if self.parsed_args.set:
                potential_args = self.parsed_args.set
                # convert potential_args to respective types
                potential_args = self._convert_type(potential_args)
                if not potential_args[0] in self.kwargs:
                    sys_exit("Given key not found")

                self.file.update({potential_args[0]: potential_args[1]})
            elif self.parsed_args.reset:
                for arg in self.parsed_args.reset:
                    self.file.pop(arg, None)
            elif self.parsed_args.reset_all:
                self.file.clear()
            self.file.save()

            self.parser.set_defaults(**self.file)

            if self.exit_on_change:
                sys_exit()

        # self._add_help()

        # reenable every required item that wasn't in the file
        for action in self._parent._actions:
            if action.dest not in self.file and action.dest in required:
                action.required = True

        return self.parser.parse_args()

    def _convert_type(self, potential_args: list):
        arg_replacements = {"true": True, "false": False,
                            "none": None, "null": None}
        potential_args[1] = arg_replacements.get(
            potential_args[1].lower(), potential_args[1])
        if str(potential_args[1]).isdigit():
            potential_args[1] = int(potential_args[1])
        return potential_args
