import importlib
import io
from sys import executable
from subprocess import PIPE, Popen, SubprocessError
from os import get_terminal_size

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
            output = []
            try:
                for line in io.TextIOWrapper(import_proc.stdout):  # type: ignore
                    print(f'\033[2K<{package.ljust(10)}> {line.strip()}'[:get_terminal_size().columns-1], end="\r")
                    output.append(line.strip())
                return import_proc.returncode
            except (KeyboardInterrupt, SubprocessError):
                import_proc.kill()
                import_proc.terminate()
                print("\n".join(output[-10:]))

    def ensure(self) -> None:
        self.install("", post=["ensurepip", "--upgrade"])
        self.install("pip", post=["pip", "install", "--upgrade"])
        self.pip_functions = True