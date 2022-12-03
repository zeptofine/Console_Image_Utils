import argparse
import os
import json
from sys import exit as sys_exit


class ConfigParser:
    '''Creates an easy argparse config utility. It saves arguments given to it to a path.'''

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

        # remove --help from parser
        if self._parent.add_help & rewrite_help:
            self._parent._actions.pop(0)
            self._parent._option_string_actions.pop(self.default_prefix+'h')
            self._parent._option_string_actions.pop(
                self.default_prefix*2+'help')

        # set up child parser
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
            f'Config options')
        self.config_options = self.config_option_group.add_mutually_exclusive_group()
        self.config_option_group.add_argument(self.default_prefix*2+"config_path", type=str,
                                              default=self.config_path, metavar="PATH",
                                              help="select a config to read from.")
        self.config_options.add_argument(self.default_prefix*2+"set",
                                         nargs=2, metavar=('KEY', 'VAL'),
                                         help="change a default argument's options")
        self.config_options.add_argument(self.default_prefix*2+"reset", metavar='VALUE',
                                         help="removes a changed option.")
        self.config_options.add_argument(self.default_prefix*2+"reset_all", action="store_true",
                                         help="resets every option.")

        self.parsed_args, _ = self.parser.parse_known_args()
        self.kwargs = {i[0]: i[1] for i in self.parsed_args._get_kwargs()}
        self.config_path = self.kwargs['config_path']

        # exclude set, reset from config
        self.kwargs.pop('set', None)
        self.kwargs.pop('reset', None)
        self.kwargs.pop('reset_all', None)

        # If config doesn't exist, create an empty/filled version
        if not os.path.exists(self.config_path):
            with open(self.config_path, "w", encoding='utf-8') as config_file:
                if autofill:
                    config_file.write(json.dumps(self.kwargs, indent=4))
                else:
                    config_file.write(json.dumps({}))
                config_file.close()

        # Read config file
        with open(self.config_path, "r", encoding='utf-8') as config_file:
            self.edited_keys = json.loads(config_file.read())
            config_file.close()

        # set defaults
        if self.parsed_args.set or \
                self.parsed_args.reset or \
                self.parsed_args.reset_all:
            if self.parsed_args.set:
                potential_args = self.parsed_args.set
                # convert to different types
                if potential_args[1].lower() in ["true", "false"]:
                    if potential_args[1].lower() == "true":
                        potential_args[1] = True
                    else:
                        potential_args[1] = False
                elif potential_args[1].lower() in ["none", "null"]:
                    potential_args[1] = None
                elif potential_args[1].isdigit():
                    potential_args[1] = int(potential_args[1])

                if not potential_args[0] in self.kwargs.keys():
                    sys_exit("Given key not found")

                self.edited_keys[potential_args[0]] = potential_args[1]
            elif self.parsed_args.reset:
                self.edited_keys.pop(self.parsed_args.reset, None)
            elif self.parsed_args.reset_all:
                self.edited_keys = {}

            with open(self.config_path, "w", encoding='utf-8') as config_file:
                config_file.write(json.dumps(self.edited_keys, indent=4))
                config_file.close()
            if exit_on_change:
                sys_exit()

        # modified from argparse.py ( self.set_defaults(**kwargs) )
        self.parser._defaults.update(self.edited_keys)
        for action in self.parser._actions:
            if action.dest in self.edited_keys:
                action.default = self.edited_keys[action.dest]

        # Add --help back in
        if self._parent.add_help and rewrite_help:
            self.parser.add_argument(
                self.parser.prefix_chars+"h", self.parser.prefix_chars*2+"help",
                action='help', default=argparse.SUPPRESS,
                help=('show this help message and exit'))

    def parse_args(self):
        '''parse_args passthrough to simplify integration'''
        return self.parser.parse_args()

    def config(self):
        '''returns a dictionary of all the edited options'''
        return self.edited_keys
