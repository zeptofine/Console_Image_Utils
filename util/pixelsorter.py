import os
from glob import glob
from pathlib import Path

import cv2
import numpy as np
from tqdm import tqdm
from iterable_starmap import CustomPool


def get_file_list(*folders: Path) -> list[Path]:
    """
    Args    folders: One or more folder paths.
    Returns list[Path]: paths in the specified folders."""
    return [Path(y) for x in (glob(str(p), recursive=True) for p in folders) for y in x]


def pix_to_luma(pix):
    B, G, R = pix[0, 0]
    return (0.299*R + 0.587*G + 0.114*B)


def pixelsort(img: np.ndarray, diff: int, preview=False, use_tqdm=False, preview_scale=512):
    edges = cv2.GaussianBlur(img, (3, 3), 0)
    edges = cv2.Canny(edges, diff, diff)
    edges = edges != 0

    if preview:
        # resize to a 512 x 512 image for preview
        scale = preview_scale * (1/max(edges.shape))
        cv2.imshow('edges', cv2.resize(np.array(edges, dtype=np.uint8) * 255, (0, 0), fx=scale, fy=scale))

    cv2.waitKey(1)

    img_h = img
    # img_h = np.clip((img - 50), a_min=1, a_max=255)
    row_sets = []
    iter_obj = range(img.shape[0])
    if use_tqdm:
        iter_obj = tqdm(iter_obj)
    for row in iter_obj:

        given_col = img[row:row + 1]
        pivot = 0
        pix_sets = []
        # sample_luma = pix_to_luma(sample)
        for col in range(img.shape[1]):

            # * this is used for comparing pixels on the fly
            # new_sample = given_col[:, col:col + 1]
            # new_sample_luma = pix_to_luma(new_sample)
            # newdiff = abs(new_sample_luma - sample_luma)
            # print(edges[row:row + 1, col:col+1])
            # if newdiff > diff:

            # a pixel will end a set and start the new set
            if edges[row:row + 1, col:col + 1][0, 0]:
                pix_sets.append(np.sort(given_col[:, pivot:col], axis=1))
                pivot = col
        pix_sets.append(np.sort(given_col[:, pivot:], axis=1))
        row_sets.append(np.concatenate((pix_sets), axis=1))

    img_h = np.concatenate(row_sets, axis=0)
    return img_h


def sort_and_write(img, out, diff, preview, horiz, vertical, axes):
    img = cv2.imread(str(img))

    if vertical and horiz:
        img = img[::-1, ::-1]
    if vertical:
        img = img[::-1]
    if horiz:
        img = img[:, ::-1]
    if axes:
        img = img.swapaxes(0, 1)
    img = pixelsort(img, diff, preview=preview)
    if axes:
        img = img.swapaxes(0, 1)
    if vertical and horiz:
        img = img[::-1, ::-1]
    if vertical:
        img = img[::-1]
    if horiz:
        img = img[:, ::-1]

    cv2.imwrite(out, img)


if __name__ == "__main__":

    # User choice for files
    path = Path("/mnt/Toshiba/GitHub/Console_Image_Utils/sequence/*")
    images = sorted(get_file_list(path))

    # whitelist = ['safe']
    # images = {j for i in whitelist for j in images if i in str(j)}

    out = path.parent.with_name(f"{path.parent.name}-pixelsorted")
    out.mkdir(exist_ok=True)

    # changes which direction the sorters will go
    swap_horizontal = False
    swap_vertical = True
    swap_axes = True
    # sensitivity of Canny edge detection
    diff = 32
    preview = True

    argtuples = [(img, str(out/img.name), diff, preview, swap_horizontal, swap_vertical, swap_axes)
                 for img in images]

    threads = int(os.cpu_count() / 4 * 3)
    # threads = 4
    with CustomPool(threads) as p:
        out = list(tqdm(p.istarmap(sort_and_write, argtuples), total=len(images)))

    cv2.destroyAllWindows()
