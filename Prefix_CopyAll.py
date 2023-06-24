import shutil
from enum import Enum
from pathlib import Path
from typing import Optional

import typer
from tqdm import tqdm


class CopyType(str, Enum):
    copy = "copy"
    link = "link"


def main(
    copy_from: Path,
    prefix: str,
    copy_to: Optional[Path] = None,
    copy_type: CopyType = CopyType.copy,
):
    if copy_to is None:
        copy_to = copy_from.parent / copy_from.with_name(f"{copy_from.name}-copied-{prefix}")
    file_lst = list(tqdm(copy_from.rglob("*"), "getting files..."))
    with tqdm(file_lst) as t:
        copied = 0
        ignored = 0
        for file in t:
            file: Path = file.relative_to(copy_from)
            out_file = copy_to / file
            if prefix in str(file) and not out_file.exists():
                out_file.parent.mkdir(parents=True, exist_ok=True)
                match copy_type:
                    case CopyType.copy:
                        shutil.copy(copy_from / file, copy_to / file)
                    case CopyType.link:
                        (copy_to / file).symlink_to(copy_from / file)
                copied += 1
            else:
                ignored += 1
            t.set_description_str(
                f"{'copied' if copy_type == CopyType.copy else 'linked'}: {copied}, {ignored = }", refresh=False
            )


if __name__ == "__main__":
    typer.run(main)
