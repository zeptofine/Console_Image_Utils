import shutil
from enum import Enum
from pathlib import Path
from typing import Annotated, Optional

import typer
from tqdm import tqdm
from typer import Argument, Option


class CopyType(str, Enum):
    copy = "copy"
    link = "link"


def main(
    copy_from: Annotated[Path, Argument(help="The path to copy from")],
    prefix: Annotated[str, Argument(help="the string to search for")],
    copy_to: Annotated[Path | None, Option(help="If present, the files will be copied to this specific folder")] = None,
    copy_type: Annotated[CopyType, Option(help="whether to copy or link the files to the output")] = CopyType.copy,
) -> None:
    if copy_to is None:
        copy_to = copy_from.parent / copy_from.with_name(f"{copy_from.name}-copied-{prefix}")
    file_lst = list(tqdm(copy_from.rglob("*"), "getting files..."))
    with tqdm(file_lst) as t:
        copied = 0
        ignored = 0
        for file in t:
            file: Path = file.relative_to(copy_from)
            out_file: Path = copy_to / file
            if prefix in str(file) and not out_file.exists():
                out_file.parent.mkdir(parents=True, exist_ok=True)

                match copy_type:
                    case CopyType.copy:
                        if (copy_from / file).resolve().is_dir():
                            shutil.copytree(copy_from / file, copy_to / file)
                        else:
                            shutil.copy(copy_from / file, copy_to / file)

                    case CopyType.link:
                        (copy_to / file).symlink_to(copy_from / file)
                copied += 1
            else:
                ignored += 1
            t.set_description_str(
                f"{'copied' if copy_type == CopyType.copy else 'linked'}: {copied}, {ignored = }",
                refresh=False,
            )


if __name__ == "__main__":
    typer.run(main)
