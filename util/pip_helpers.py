import importlib
import io
from sys import executable
from subprocess import PIPE, Popen, SubprocessError
from os import get_terminal_size


class PipInstaller:
    def __init__(self):
        self.pip_functions = False

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        del self

    def available(self, package_name) -> bool:
        try:
            importlib.import_module(package_name)
        except ImportError:
            if not self.pip_functions:
                self.ensure()
            return False
        return True

    def install(self, *packages, post=None) -> int:
        if post is None:
            post = ['pip', 'install']
        subprocess_input = [executable, '-m', *post, *packages] if packages else [executable, '-m', *post]
        with Popen(subprocess_input,
                   stdout=PIPE, stderr=PIPE) as import_proc:
            output = []
            try:
                for line in io.TextIOWrapper(import_proc.stdout):  # type: ignore
                    print(f'\033[2K<{set(packages)}> {line.strip()}'[:get_terminal_size().columns - 1], end="\r")
                    output.append(line.strip())
            except (KeyboardInterrupt, SubprocessError):
                import_proc.kill()
                import_proc.terminate()
                print("\n".join(output[-10:]))
        return import_proc.returncode

    def ensure(self) -> None:
        self.install("", post=["ensurepip", "--upgrade"])
        self.install("pip", post=["pip", "install", "--upgrade"])
        self.pip_functions = True
