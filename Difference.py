from pathlib import Path

import cv2
import typer


def main(dir_in: Path, dir_out: Path, file_type: str = "png", scale: int = 0):
    in_list = list(Path(dir_in).rglob("*"))
    for file in in_list:
        file = file.relative_to(dir_in)
        if not (dir_in / file).is_dir():
            img = cv2.imread(str(dir_in / file))
            y, x = img.shape[0], img.shape[1]
            if scale and (y > scale or x > scale):
                ratio = scale / max(x, y)
                img = cv2.resize(img, (int(ratio * x), int(ratio * y)))
            (dir_out / file.parent).mkdir(parents=True, exist_ok=True)
            cv2.imwrite(str(dir_out / file.with_suffix(f".{file_type}")), img)


if __name__ == "__main__":
    typer.run(main)
