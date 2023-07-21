import importlib
import io
from os import get_terminal_size
from subprocess import PIPE, Popen, SubprocessError
from sys import executable
from typing import Self


class PipInstaller:
    def __init__(self, check_for_pip: bool = False) -> None:
        self.pip_functions = False
        self.check_for_pip = check_for_pip

    def __enter__(self) -> Self:
        return self

    def __exit__(self, type: None, value: None, traceback: None) -> None:
        del self

    def available(self, package_name: str) -> bool:
        try:
            importlib.import_module(package_name)
        except ImportError:
            if not self.pip_functions and self.check_for_pip:
                self.ensure()
            return False
        return True

    def install(self, *packages: str, post: list[str] | None = None) -> int:
        if post is None:
            post = ["pip", "install"]
        subprocess_input = (
            [executable, "-m", *post, *packages]
            if packages
            else [executable, "-m", *post]
        )
        with Popen(subprocess_input, stdout=PIPE, stderr=PIPE) as import_proc:
            output = []
            try:
                for line in io.TextIOWrapper(import_proc.stdout):  # type: ignore
                    print(
                        f"\033[2K<{set(packages)}> {line.strip()}"[
                            : get_terminal_size().columns - 1
                        ],
                        end="\r",
                    )
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
