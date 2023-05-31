import argparse
from multiprocessing import Pool
from pathlib import Path

import imagehash
from PIL import Image
from rich import print as rprint
from tqdm import tqdm

# import os

IMHASH_TYPES = {
    'average': imagehash.average_hash,
    'crop_resistant': imagehash.crop_resistant_hash,
    'color': imagehash.colorhash,
    'dhash': imagehash.dhash,
    'dhash_vertical': imagehash.dhash_vertical,
    'phash': imagehash.phash,
    'phash_simple': imagehash.phash_simple,
    'whash': imagehash.whash
}


def get_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument('-i', '--input', help='folder to scan', required=True)
    parser.add_argument('--power', help='number of threads used to hash', type=int, default=9)
    parser.add_argument('type', choices=IMHASH_TYPES.keys(), default='average')
    return parser


def hash_img(img_hasher):
    return str(img_hasher[1](Image.open(img_hasher[0])))


if __name__ == "__main__":
    args = get_parser().parse_args()
    hasher = IMHASH_TYPES[args.type]

    folder = Path(args.input)
    new_folder = folder.parent / 'linked'
    for file in new_folder.rglob("*"):
        file.unlink()
    new_folder.mkdir(exist_ok=True)

    exts = ['.jpg', '.jpeg', '.png', '.webp']
    files = list(i for i in folder.rglob("*") if i.suffix in exts)

    with Pool(args.power) as p:
        hashes = {}
        try:
            for p, h in tqdm(zip(files, p.imap(hash_img, zip(files, [hasher]*len(files)))), total=len(files)):
                hashes[p] = h
        except KeyboardInterrupt:
            print("Interrupted hashing. trying to run with given hashes")
    sorted_hashes = dict(sorted(hashes.items(), key=lambda x: x[::-1]))

    for (path, hash) in tqdm(sorted_hashes.items()):
        new_path: Path = new_folder / hash
        new_path = new_path.with_name(f"{new_path.name}_{path.stem}").with_suffix(path.suffix)
        new_path.symlink_to(path)
        print(new_path)
