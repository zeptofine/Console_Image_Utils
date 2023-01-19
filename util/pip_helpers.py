import importlib
import io
from sys import executable
from subprocess import PIPE, Popen


class PipInstaller:
    def __init__(self, debug=False):
        self.pip_functions = False
        self.debug_mode = debug

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        del self

    def available(self, package_name) -> bool:
        if self.debug_mode:
            return False
        try:
            importlib.import_module(package_name)
        except ImportError:
            if not self.pip_functions:
                self.ensure()
            return False
        return True

    def install(self, package, post=['pip', 'install']) -> int:
        subprocess_input = [executable, '-m', *post,
                            package] if package else [executable, '-m', *post]
        with Popen(subprocess_input,
                   stdout=PIPE, stderr=PIPE) as import_proc:
            for line in io.TextIOWrapper(import_proc.stdout):  # type: ignore
                print(f'<{package.ljust(10)}> {line}')
            return import_proc.returncode

    def ensure(self) -> None:
        self.install("", post=["ensurepip", "--upgrade"])
        self.install("pip", post=["pip", "install", "--upgrade"])
        self.pip_functions = True
