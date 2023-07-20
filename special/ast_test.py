import ast
import shutil
import sys
import warnings
from ast import AST, Call, Module, expr
from collections import defaultdict
from collections.abc import Generator
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from rich import print as rprint
from tqdm import tqdm

FONT_PATH = "/usr/share/fonts/TTF/CascadiaCode.ttf"


def round_partial(value, resolution):
    return round(value / resolution) * resolution


def pre_call_hook(module: Module) -> None:
    module.body[:0] = ast.parse(
        """
import time
_ast_tracker_file = open("ast_tracker.log", "w")
""",
        mode="exec",
    ).body


def post_call_callback(module: Module) -> None:
    module.body.extend(
        ast.parse(
            """
_ast_tracker_file.close()
""",
            mode="exec",
        ).body,
    )


def hook_expr(node: AST) -> expr:
    return ast.parse(
        f"""
_ast_tracker_file.write(
    str(time.perf_counter())
    + ":({",".join(map(str, [node.lineno, node.col_offset, node.end_lineno, node.end_col_offset]))})\\n")""",
        mode="eval",
    ).body


def hook_node(node: AST) -> expr:
    new = ast.Expression(
        body=ast.Subscript(
            value=ast.Tuple(
                elts=[
                    node,
                    hook_expr(node),
                ],
                ctx=ast.Load(),
            ),
            slice=ast.Constant(value=0),
            ctx=ast.Load(),
        ),
    )
    new = ast.copy_location(new, node)
    return new.body


def get_tracked_nodes(node: AST) -> Generator[AST, None, None]:
    return (
        child for child in ast.walk(node) if isinstance(child, (ast.Compare, ast.BoolOp, ast.BinOp, ast.UnaryOp, Call))
    )


def get_replacements(node: AST) -> dict:
    return {child: hook_node(child) for child in get_tracked_nodes(node)}


def set_parents(node: AST, parent: AST | None = None) -> None:
    if parent is not None:
        node._parent = parent  # type: ignore
    for child in ast.iter_child_nodes(node):
        set_parents(child, node)


def replace_from_parents(calls: dict[AST, AST]) -> None:
    for old, new in list(calls.items()):
        parent = old._parent  # type: ignore
        added = False
        for field, value in ast.iter_fields(parent):
            if isinstance(value, list) and old in value:
                value[value.index(old)] = new
                added = True
                break
            if value == old:
                setattr(parent, field, new)
                added = True
                break
        if added:
            calls.pop(old)


def main(file: Path) -> None:
    data = file.read_text()
    height = len(data.splitlines())
    width = max(len(line) for line in data.splitlines())
    module = ast.parse(data)

    calls = get_replacements(module)
    set_parents(module)
    replace_from_parents(calls)
    pre_call_hook(module)
    post_call_callback(module)
    if calls:
        warnings.warn(f"Some calls remain unnacounted for: {calls}", stacklevel=2)

    shutil.copy(file, file.with_suffix(".bak"))
    with file.open("w") as txtfile:
        txtfile.write(ast.unparse(module))
    try:
        print("running...")
        import subprocess

        subprocess.run([sys.executable, file, *sys.argv[2:]])
    except KeyboardInterrupt:
        shutil.move(file.with_suffix(".bak"), file)
        # raise exc
    else:
        shutil.move(file.with_suffix(".bak"), file)

    # Run the animation
    box = np.zeros(
        (
            height,
            width,
        ),
    )
    lines: list[str] = data.splitlines()

    size = 12

    font = ImageFont.truetype(FONT_PATH, size)
    fontwidth = font.getlength("a")
    pimage: Image.Image = Image.new("L", (int(width * fontwidth), int(height * size)))
    draw: ImageDraw.ImageDraw = ImageDraw.Draw(pimage)
    for idx, line in enumerate(lines):
        draw.text((0, idx * size), line, fill="white", font=font)

    # start preview and wait for key input
    cv2.imshow("drawn", np.asarray(pimage))
    cv2.waitKey(0)

    print("reading ast_tracker.log...")
    with Path("ast_tracker.log").open() as ast_tracker:
        evaluated: Generator[tuple[float, tuple[int, int, int, int]], None, None] = (
            (float(line[0]), ast.literal_eval(line[1])) for line in (line.strip().split(":", 1) for line in ast_tracker)
        )

        single_call_duration = 0.5  # secs (hopefully)
        fps = 30
        timescale = 10  # 1/n time

        first_dur, firstplace = next(evaluated)
        timings = defaultdict(set)
        timings[0.0].add(firstplace)
        for duration, rect in evaluated:
            timings[round_partial((duration - first_dur) * timescale, 1 / fps)].add(rect)
        print("finished sorting")

        with tqdm(
            np.arange(
                0,
                max(timings.keys()) + (single_call_duration),
                (1 / fps),
            )
        ) as t:
            for f in t:
                box = np.clip(box - ((1 / fps) / single_call_duration), 0, None)
                if f in timings:
                    rprint(f"{timings[f]}")
                    for selection in timings[f]:
                        box[selection[0] - 1 : selection[2], selection[1] : selection[3]] = 1
                    t.set_description_str(str(f))
                resized: np.ndarray = cv2.resize(
                    box,
                    (int(width * fontwidth), int(height * size)),
                    interpolation=cv2.INTER_NEAREST,
                )
                newimg = abs((np.asarray(pimage) / 255) - resized)

                cv2.imshow("drawn", newimg)
                cv2.waitKey(1000 // fps)
            print("Done")
            cv2.waitKey(0)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Please give a file to track")
        sys.exit(1)
    main(Path(sys.argv[1]))
