import importlib
import io
import sys
from pkgutil import find_loader
from subprocess import PIPE, Popen


def is_installed(package_name) -> bool:
    loader = find_loader(package_name)
    return loader is not None


class PipInstaller:
    def __init__(self):
        self.pip_functions = False
        self.failed_once = False

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        del self

    def available(self, package_name) -> bool:
        if self.failed_once:
            self.ensure()
            self.failed_once = False
        try:
            importlib.import_module(package_name)
        except ImportError:
            self.failed_once = True
            return False
        return True

    def install(self, package, post=['pip', 'install']) -> int:
        subprocess_input = [sys.executable, '-m', *post,
                            package] if package else [sys.executable, '-m', *post]
        output = []
        with Popen(subprocess_input,
                   stdout=PIPE, stderr=PIPE) as import_proc:
            for line in io.TextIOWrapper(import_proc.stdout,  # type: ignore
                                         encoding="utf-8"):
                print(f'<{package.ljust(10)}> {line.strip()}')
                output.append(line)
            return import_proc.returncode

    def ensure(self) -> None:
        self.install("", post=["ensurepip", "--upgrade"])
        self.install("pip", post=["pip", "install", "--upgrade"])
