import ast
import difflib
from pathlib import Path

import typer
from rich import print as rprint


def mogrify_ast_python(files: list[Path]):
    """
    Convert a Python file to an AST.
    """
    for path in files:
        with path.open() as f:
            source = f.read()

        module = ast.parse(source)
        new = ast.unparse(module).splitlines()
        # get the diff between ast.unparse and original
        diff = difflib.unified_diff(source.splitlines(), new)
        for line in diff:
            if line.startswith("+"):
                rprint(f"[green]{line}[/green]")
            elif line.startswith("-"):
                rprint(f"[red]{line}[/red]")


if __name__ == "__main__":
    typer.run(mogrify_ast_python)
