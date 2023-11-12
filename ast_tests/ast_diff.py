import ast
import subprocess
import sys
from collections import defaultdict
from collections.abc import Generator
from pathlib import Path
from typing import TypedDict

import typer
from rich import print as rprint
from tqdm import tqdm

try:
    import simdjson as json
except ImportError:
    import json


class IssueLocation(TypedDict):
    column: int
    row: int


class Issue(TypedDict):
    code: str
    location: IssueLocation
    end_location: IssueLocation
    filename: str
    message: str
    noqa_row: int
    url: str


def batched(lst, count):
    batch = []
    for item in lst:
        batch.append(item)
        if len(batch) == count:
            yield batch
            batch = []
    if batch:
        yield batch


def reparse(source):
    return ast.unparse(ast.parse(source))


def expand_dirs(paths: list[Path]) -> Generator[Path, None, None]:
    for path in tqdm(paths):
        if path.is_dir():
            yield from tqdm(
                file
                for file in tqdm(path.glob("**/*.py"))
                if all(not (str(part).startswith(".") or str(part).startswith("venv")) for part in file.parts)
            )
        else:
            yield path


def reparse_python(files: list[Path], show_diff: bool = False):
    actual_files = set(expand_dirs(files))

    thread = subprocess.Popen(
        [sys.executable, "-m", "ruff", "--format=json", *map(str, actual_files)],
        stdout=subprocess.PIPE,
    )
    errors: dict[Path, dict[str, list[Issue]]] = defaultdict(lambda: defaultdict(list))
    data = thread.stdout.read()
    if not data:
        return

    errorlist: list[Issue] = json.loads(data)  # type: ignore
    for error in errorlist:  # type: ignore
        errors[Path(error["filename"])][error["code"]].append(error)

    for file, codes in errors.items():
        rprint(f"[blue]{file}:[/blue] [red]{len(codes)}[/red] unique issue{'s' if len(codes) > 1 else ''}")
        for code, issues in codes.items():
            str_issues = [f'({issue["location"]["row"]}, {issue["location"]["column"]})' for issue in issues]
            rprint(
                f"  [white]{code} [yellow]{issues[0]['url'].rsplit('rules/', 1)[-1]}:[/][red]"
                + ", ".join(str_issues)
                + "[/]"
            )
    return
    for path in tqdm(list(expand_dirs(files))):
        print(path)

        continue
        with path.open() as f:
            try:
                f.read()
            except Exception as e:
                rprint(f"[red]Failed to read {path}: {e}[/red]")
                continue
        # new = reparse(source)
        # if show_diff:
        #     import difflib

        #     # get the diff between ast.unparse and original
        #     for line in difflib.unified_diff(source.splitlines(), new.splitlines()):
        #         if line.startswith("+"):
        #             rprint(f"[green]{line}[/]")
        #         elif line.startswith("-"):
        #             rprint(f"[red]{line}[/]")
        #         else:
        #             rprint(f"[black]{line}[/]")
        #        else:

        #            print(new)


if __name__ == "__main__":
    typer.run(reparse_python)
