import importlib
import io
from pkgutil import find_loader
import sys
from subprocess import PIPE, Popen

def is_installed(package_name) -> bool:
    loader = find_loader(package_name)
    return loader is not None


def ensureinstall():
    try_install("", post=["ensurepip", "--upgrade"])
    try_install("pip", post=["pip", "install", "--upgrade"])


def try_install(package, post=['pip', 'install']):
    subprocess_input = [sys.executable, '-m', *post,
                        package] if package else [sys.executable, '-m', *post]
    output = []
    with Popen(subprocess_input,
               stdout=PIPE, stderr=PIPE) as import_proc:
        for line in io.TextIOWrapper(import_proc.stdout,  # type: ignore
                                     encoding="utf-8"):
            print(f'<{package.ljust(10)}> {line.strip()}')
            output.append(line)
    return output


class PipInstaller:
    def __init__(self):
        self.pip_functions = False
        self.failed_once = False

    def available(self, package_name):
        if self.failed_once:
            self.ensure()
        try:
            importlib.import_module(package_name)
        except ImportError:
            self.failed_once = True
            return False
        return True

    def install(self, package, post=['pip', 'install']):
        subprocess_input = [sys.executable, '-m', *post,
                            package] if package else [sys.executable, '-m', *post]
        output = []
        with Popen(subprocess_input,
                   stdout=PIPE, stderr=PIPE) as import_proc:
            for line in io.TextIOWrapper(import_proc.stdout,  # type: ignore
                                         encoding="utf-8"):
                print(f'<{package.ljust(10)}> {line.strip()}')
                output.append(line)
            return import_proc.pid

    def ensure(self):
        if not self.pip_functions:
            self.install("", post=["ensurepip", "--upgrade"])
            self.pip_functions = True
            self.install("pip", post=["pip", "install", "--upgrade"])
