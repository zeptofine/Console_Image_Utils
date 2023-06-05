from __future__ import annotations

import multiprocessing.pool as mpp
import os
from argparse import ArgumentParser
from dataclasses import dataclass
from multiprocessing import Pool  # , Process, Queue, current_process
from multiprocessing import freeze_support
from pathlib import Path

import cv2
import dateutil.parser as timeparser
from cfg_argparser import ConfigArgParser
from rich.traceback import install
from rich_argparse import ArgumentDefaultsRichHelpFormatter
# from tqdm.rich import tqdm as rtqdm
from tqdm import tqdm
from dataset_filters.data_filters import (
    BlacknWhitelistFilter,
    ExistingFilter,
    HashFilter,
    ResFilter,
    StatFilter
)
from dataset_filters.dataset_builder import DatasetBuilder
from util.file_list import get_file_list, to_recursive
from util.print_funcs import ipbar  # , Timer
from util.print_funcs import RichStepper

CPU_COUNT: int = os.cpu_count()  # type: ignore
install()


def main_parser() -> ArgumentParser:
    parser = ArgumentParser(
        prog="CreateDataset.py",
        formatter_class=ArgumentDefaultsRichHelpFormatter,
        description="""Hi! this script converts thousands of files to
    another format in a High-res/Low-res pairs for data science.
    @ is available to follow a file.""",
        fromfile_prefix_chars="@")

    import shtab
    shtab.add_argument_to(parser)

    p_reqs = parser.add_argument_group("Runtime")
    p_reqs.add_argument("-i", "--input",
                        help="Input folder.", required=True)
    p_reqs.add_argument("-x", "--scale", type=int, default=4,
                        help="scale to downscale LR images")
    p_reqs.add_argument("-e", "--extension", metavar="EXT", default=None,
                        help="export extension.")
    p_reqs.add_argument("--exts", default="png webp jpg",
                        help="extensions to search for. Only images work currently.")
    p_mods = parser.add_argument_group("Modifiers")
    p_mods.add_argument("-r", "--recursive", action="store_true", default=False,
                        help="preserves the tree hierarchy.")
    p_mods.add_argument("-t", "--threads", type=int, default=int((CPU_COUNT / 4) * 3),
                        help="number of total threads used for multiprocessing.")
    p_mods.add_argument("-l", "--image_limit", type=int, default=None, metavar="MAX",
                        help="only gathers a given number of images. None disables it entirely.")  # max numbers to be given to the filters
    p_mods.add_argument("--limit_mode", choices=["before", "after"], default="before",
                        help="Changes the order of the limiter. By default, it happens before filtering out bad images.")
    # ^^ this choice is for if you want to convert n images, or only search n images.
    p_mods.add_argument("--simulate", action="store_true",
                        help="skips the conversion step. Used for debugging.")
    p_mods.add_argument("--purge", action="store_true",
                        help="deletes the output files corresponding to the input files.")
    p_mods.add_argument("--purge_all", action="store_true",
                        help="deletes *every* file in the output directories.")

    p_mods.add_argument("--reverse", action="store_true",
                        help="reverses the sorting direction. it turns smallest-> largest to largest -> smallest")
    p_mods.add_argument("--overwrite", action="store_true",
                        help="Skips checking for existing files, and by proxy, overwrites existing files.")
    p_mods.add_argument("--perfdump", action="store_true",
                        help="Dumps performance information for reading with snakeviz or others.")
    # certain criteria that images must meet in order to be included in the processing.
    p_filters = parser.add_argument_group("Filters")
    p_filters.add_argument("-w", "--whitelist", type=str, metavar="INCLUDE",
                           help="only allows paths with the given string.")
    p_filters.add_argument("-b", "--blacklist", type=str, metavar="EXCLUDE",
                           help="excludes paths with the given string.")
    p_filters.add_argument("--list_separator", default=" ",
                           help="separator for the white/blacklist.")
    # ^^ used for restricting the names allowed in the paths.

    p_filters.add_argument("--minsize", type=int, metavar="MIN", default=128,
                           help="smallest available image")
    p_filters.add_argument("--maxsize", type=int, metavar="MAX",
                           help="largest allowed image.")
    p_filters.add_argument("--crop_mod", action="store_true",
                           help="changes mod mode so that it crops the image to an image that actually is divisible by scale, typically by a few px")
    # ^^ used for filtering out too small or too big images.
    p_filters.add_argument("--after", type=str,
                           help="Only uses files modified after a given date."
                           "ex. '2020', or '2009 Sept 16th'")
    p_filters.add_argument("--before", type=str,
                           help="Only uses before a given date. ex. 'Wed Jun 9 04:26:40', or 'Jun 9'")
    p_filters.add_argument("--keep_links", action="store_true",
                           help="Keeps links in the file list. Is useful if the dataset is messy regarding sym/hardlinks.")

    p_filters.add_argument("--hash", action="store_true",
                           help="Removes similar images. is better for perceptually similar images.")
    p_filters.add_argument("--hash-type", type=str, choices=["average", "crop_resistant", "color", "dhash", "dhash_vertical",
                                                             "phash", "phash_simple", "whash"], default="average",
                           help="type of image hasher to use for the slow method. read https://github.com/JohannesBuchner/imagehash for more info")
    p_filters.add_argument("--hash-choice", type=str, choices=["ignore_all", "newest", "oldest", "size"],
                           default='size', help="At the chance of a hash conflict, this will decide which to keep.")
    # # ^^ Used for filtering out too old or too new images.
    # p_filters.add_argument("--print-filtered", action="store_true",
    #                        help="prints all images that were removed because of filters.")
    return parser


def istarmap(self, func, iterable, chunksize=1):
    """starmap-version of imap
    """
    self._check_running()  # type: ignore
    if chunksize < 1:
        raise ValueError(
            "Chunksize must be 1+, not {0:n}".format(
                chunksize))

    task_batches = mpp.Pool._get_tasks(  # type: ignore
        func, iterable, chunksize)
    result = mpp.IMapIterator(self)
    self._taskqueue.put(  # type: ignore
        (
            self._guarded_task_generation(result._job,  # type: ignore
                                          mpp.starmapstar,  # type: ignore
                                          task_batches),
            result._set_length  # type: ignore
        ))
    return (item for chunk in result for item in chunk)


@dataclass
class DatasetFile:
    path: Path
    hr_path: Path
    lr_path: Path


def hrlr_pair(path: Path, hr_folder: Path, lr_folder: Path,
              recursive: bool = False, ext=None) -> tuple[Path, Path]:
    """
    gets the HR and LR file paths for a given file or directory path.
    Args    recursive (bool): Whether to search for the file in subdirectories.
            ext (str): The file extension to append to the file name.
    Returns tuple[Path, Path]: HR and LR file paths.
    """
    hr_path = hr_folder / to_recursive(path, recursive)
    lr_path = lr_folder / to_recursive(path, recursive)
    # Create the HR and LR folders if they do not exist
    hr_path.parent.mkdir(parents=True, exist_ok=True)
    lr_path.parent.mkdir(parents=True, exist_ok=True)
    # If an extension is provided, append it to the HR and LR file paths
    if ext:
        hr_path = hr_path.with_suffix(f".{ext}")
        lr_path = lr_path.with_suffix(f".{ext}")
    return hr_path, lr_path


def fileparse(dfile: DatasetFile, scale):
    """Converts an image file to HR and LR versions and saves them to the specified folders.
    """
    # Read the image file
    image = cv2.imread(str(dfile.path), cv2.IMREAD_UNCHANGED)
    image = image[0:(image.shape[0] // scale) * scale,
                  0:(image.shape[1] // scale) * scale]
    # Save the HR / LR version of the image
    cv2.imwrite(str(dfile.hr_path), image)
    cv2.imwrite(str(dfile.lr_path), cv2.resize(image, (0, 0),
                                               fx=1 / scale, fy=1 / scale))  # type: ignore

    # Set the modification time of the HR and LR image files to the original image's modification time
    mtime = dfile.path.stat().st_mtime
    os.utime(str(dfile.hr_path), (mtime, mtime))
    os.utime(str(dfile.lr_path), (mtime, mtime))
    return dfile.path


def main(args):

    s = RichStepper(loglevel=1, step=-1)
    s.next("Settings: ")

    args.input = Path(args.input)

    df = DatasetBuilder(
        s,
        origin=str(args.input),
        processes=args.threads
    )

    def check_for_images(image_list) -> bool:
        if not image_list:
            s.print(-1, "No images left to process")
            return False
        return True

# * Make sure given args are valid
    if args.extension:
        if args.extension.startswith("."):
            args.extension = args.extension[1:]
        if args.extension.lower() in ["self", "none", "same", ""]:
            args.extension = None
    if args.after or args.before:
        try:
            if args.after:
                args.after = timeparser.parse(str(args.after))
            if args.before:
                args.before = timeparser.parse(str(args.before))
            if args.after and args.before and args.after > args.before:
                raise timeparser.ParserError(
                    f"{args.before} (--before) is older than {args.after} (--after)!")
        except timeparser.ParserError as err:
            s.set(-9).print(str(err))
            return 1

        df.add_filters(StatFilter(args.before, args.after))

    args.minsize = args.minsize if args.minsize != -1 else None
    args.maxsize = args.maxsize if args.maxsize != -1 else None
    df.add_filters(ResFilter(args.minsize, args.maxsize, args.crop_mod, args.scale))

    if args.before or args.after:
        s.print(f"Filtering by time ({args.before} <= x <= {args.after})")
    if args.minsize or args.maxsize:
        s.print(f"Filtering by size ({args.minsize} <= x <= {args.maxsize})")

    args.input = Path(args.input)


# * Get hr / lr folders
    hr_folder = args.input.parent / f"{str(args.scale)}xHR"
    lr_folder = args.input.parent / f"{str(args.scale)}xLR"
    if args.extension:
        hr_folder = Path(f"{str(hr_folder)}-{args.extension}")
        lr_folder = Path(f"{str(lr_folder)}-{args.extension}")
    hr_folder.parent.mkdir(parents=True, exist_ok=True)
    lr_folder.parent.mkdir(parents=True, exist_ok=True)

# * Gather images
    s.next("Gathering images...")
    args.exts = args.exts.split(" ")
    s.print(f"Searching extensions: {args.exts}")
    file_list = get_file_list(*[args.input / "**" / f"*.{ext}" for ext in args.exts])
    image_list = set(map(lambda x: x.relative_to(args.input), sorted(file_list)))
    if args.image_limit and args.limit_mode == "before":  # limit image number
        image_list = set(list(image_list)[:args.image_limit])

    s.print(f"Gathered {len(image_list)} images")

# * Hashing option
    if args.hash:
        df.add_filters(HashFilter(args.hash_type, args.hash_choice))

# * white / blacklist option
    if args.whitelist or args.blacklist:
        whitelist = []
        blacklist = []
        if args.whitelist:
            whitelist = args.whitelist.split(args.list_separator)
        if args.blacklist:
            blacklist = args.blacklist.split(args.list_separator)
        df.add_filters(BlacknWhitelistFilter(whitelist, blacklist))


# * Purge existing images
    if args.purge_all:
        lst = get_file_list(hr_folder / "**" / "*",
                            lr_folder / "**" / "*")
        if lst:
            s.next("Purging...")
            for file in ipbar(lst):
                if file.is_file():
                    file.unlink()
            for folder in ipbar(lst):
                if folder.is_dir():
                    folder.rmdir()
            s.print("Purged.")
    elif args.purge:
        s.next("Purging...")
        for path in ipbar(image_list):
            hr_path, lr_path = hrlr_pair(path, hr_folder, lr_folder, args.recursive, args.extension)
            hr_path.unlink(missing_ok=True)
            lr_path.unlink(missing_ok=True)
        s.print("Purged.")

    if not args.overwrite:
        df.add_filters(ExistingFilter(hr_folder, lr_folder, args.recursive))


# * Run filters
    s.next("Populating df...")
    df.populate_df(image_list)

    s.next("Filtering using:")
    if df.filters:
        s.print(
            *[f' - {str(filter)}' for filter in df.filters]
        )
        image_list = set(df.filter(image_list, sort_col="hash"))

    if not check_for_images(image_list):
        return 0

    if args.image_limit and args.limit_mode == "after":
        image_list = set(list(image_list)[:args.image_limit])

    if args.simulate:
        s.next(f"Simulated. {len(image_list)} images remain.")
        return 0


# * convert files. Finally!
    s.next("Converting...")
    image_list: set[Path] = set(map(Path, image_list))  # {Path(p) for p in image_list}
    try:
        pargs = [
            (DatasetFile(
                args.input / v,
                *hrlr_pair(v, hr_folder, lr_folder, args.recursive, args.extension)
            ),
                args.scale)
            for v in image_list
        ]
        print(len(pargs))
        with Pool(args.threads) as p:
            with tqdm(istarmap(p, fileparse, pargs, chunksize=1), total=len(image_list)) as t:
                for pth in t:
                    pass
    except KeyboardInterrupt:
        s.print(-1, "KeyboardInterrupt")


def wrap_profiler(func, filename):
    import cProfile
    import pstats

    def _wrapped(*args, **kwargs):
        with cProfile.Profile() as pr:
            func(*args, **kwargs)
        stats = pstats.Stats(pr)
        stats.sort_stats(pstats.SortKey.TIME)
        stats.dump_stats(filename=filename)
        print("Performance dumped.")
    return _wrapped


if __name__ == "__main__":
    freeze_support()
    cparser = ConfigArgParser(main_parser(), "config.json", exit_on_change=True)
    args = cparser.parse_args()
    if args.perfdump:
        main = wrap_profiler(main, filename='CreateDataset.prof')

    main(args)
