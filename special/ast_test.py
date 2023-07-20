import ast
import shutil
import sys
import warnings
from pathlib import Path

import cv2
import numpy as np
from rich import print as rprint


def pre_call_hook(module: ast.Module):
    module.body[:0] = ast.parse(
        """
import time
_ast_tracker_file = open("ast_tracker.log", "w")
""",
        mode="exec",
    ).body


def post_call_callback(module: ast.Module):
    module.body.extend(
        ast.parse(
            """
_ast_tracker_file.close()
""",
            mode="exec",
        ).body
    )


def call_hook(node: ast.Call):
    return ast.parse(
        f"""
_ast_tracker_file.write(
    str(time.perf_counter())
    + ":({",".join(map(str, [node.lineno, node.col_offset, node.end_lineno, node.end_col_offset]))})\\n")""",
        mode="eval",
    ).body


def replace_call(node: ast.Call):
    new = ast.Expression(
        body=ast.Subscript(
            value=ast.Tuple(
                elts=[
                    node,
                    call_hook(node),
                ],
                ctx=ast.Load(),
            ),
            slice=ast.Constant(value=0),
            ctx=ast.Load(),
        ),
    )
    new = ast.copy_location(new, node)
    return new.body


def find_calls(node: ast.AST):
    return (child for child in ast.walk(node) if isinstance(child, ast.Call))


def get_replacement_calls(node: ast.AST) -> dict:
    return {child: replace_call(child) for child in find_calls(node)}


def set_parents(node: ast.AST, parent: ast.AST | None = None):
    if parent is not None:
        node._parent = parent  # type: ignore
    for child in ast.iter_child_nodes(node):
        set_parents(child, node)


def replace_from_parents(calls: dict[ast.AST, ast.AST]):
    for old, new in list(calls.items()):
        parent = old._parent  # type: ignore
        added = False
        for field, value in ast.iter_fields(parent):
            if isinstance(value, list) and old in value:
                value[value.index(old)] = new
                added = True
                break
            elif value == old:
                setattr(parent, field, new)
                added = True
                break
        if added:
            calls.pop(old)


def main(file):
    with open(file) as f:
        data = f.read()

    height = len(data.splitlines())
    width = max(len(line) for line in data.splitlines())
    module = ast.parse(data)

    calls = get_replacement_calls(module)
    set_parents(module)
    replace_from_parents(calls)
    pre_call_hook(module)
    post_call_callback(module)
    if calls:
        warnings.warn(f"Some calls remain unnacounted for: {calls}")

    shutil.copy(file, Path(file).with_suffix(".bak"))
    with open(file, "w") as txtfile:
        txtfile.write(ast.unparse(module))
    try:
        print("running...")
        import subprocess

        subprocess.run([sys.executable, file, *sys.argv[2:]])
    except KeyboardInterrupt as exc:
        shutil.move(Path(file).with_suffix(".bak"), file)
        # raise exc
    else:
        shutil.move(Path(file).with_suffix(".bak"), file)

    print("reading ast_tracker.log...")
    with open("ast_tracker.log") as ast_tracker:
        dct: dict[float, tuple[int, int, int, int]] = {}
        for line in ast_tracker:
            time_dims: list[str] = line.strip().split(":", 1)
            time_: float = float(time_dims[0])
            dims: tuple[int, int, int, int] = ast.literal_eval(time_dims[1])
            dct[time_] = dims

        box = np.zeros(
            (
                height,
                width,
            )
        )
        from PIL import Image, ImageDraw, ImageFont

        lines = data.splitlines()
        size = 6
        font = ImageFont.truetype("/usr/share/fonts/TTF/CascadiaCode.ttf", size)
        fontwidth = font.getlength("a")
        pimage = Image.new("L", (int(width * fontwidth), int(height * size)))
        draw = ImageDraw.Draw(pimage)
        for idx, line in enumerate(lines):
            draw.text((0, idx * size), line, fill="white", font=font)

        # start preview and wait for key input
        cv2.imshow("drawn", np.asarray(pimage))
        cv2.waitKey(0)

        lst = list(dct.items())

        for idx, (perf, selection) in enumerate(lst):
            rprint(
                perf,
                selection,
                f"{lines[selection[0] - 1][: selection[1]]}[yellow]{lines[selection[0] - 1][selection[1]:selection[3]]}[/yellow]{lines[selection[0] - 1][selection[3]:].strip()}",
            )
            box = np.clip(box - ((1 / 60) * 4), 0, None)
            box[selection[0] - 1 : selection[2], selection[1] : selection[3]] = 1
            resized: np.ndarray = cv2.resize(
                box, (int(width * fontwidth), int(height * size)), interpolation=cv2.INTER_NEAREST
            )
            newimg = (np.asarray(pimage) / 255) + (resized)

            cv2.imshow("drawn", newimg)
            cv2.waitKey(1000 // 120)
        cv2.waitKey(0)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Please give a file to track")
        sys.exit(1)
    main(sys.argv[1])
