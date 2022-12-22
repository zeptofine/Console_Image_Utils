import importlib
import io
import sys
from subprocess import PIPE, Popen


def is_installed(package_name):
    try:
        importlib.import_module(package_name)
    except ImportError:
        return False
    return True


def ensureinstall():
    try_install("", post=["ensurepip", "--upgrade"])
    try_install("pip", post=["pip", "install", "--upgrade"])



def try_install(package, post=['pip', 'install', '--upgrade']):
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
