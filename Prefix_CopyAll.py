import shutil
import typer
from pathlib import Path

def main(copy_from: Path, copy_to: Path, prefix: str=""):
    in_list = list(copy_from.rglob("*"))
    for file in in_list:
        file = file.relative_to(copy_from)
        
        if prefix in str(file):        
            (copy_to / file.parent).mkdir(parents=True, exist_ok=True)
            shutil.copy(copy_from / file, copy_to / file)

if __name__ == "__main__":
    typer.run(main)