"""Conversion script from folder to hr/lr pair.

@author zeptofine
"""
import os
import sys
from argparse import ArgumentParser
from datetime import datetime
from glob import glob
from pathlib import Path
# from random import random
from subprocess import SubprocessError
# trunk-ignore(flake8/F401)
from multiprocessing import Process, current_process, Pool, Queue
import multiprocessing.pool as mpp
from typing import Type
# trunk-ignore(flake8/F401)
import time

from util.pip_helpers import PipInstaller
from util.print_funcs import Timer, ipbar  # trunk-ignore(flake8/F401)
from util.process_funcs import is_subprocess

CPU_COUNT: int = os.cpu_count()  # type: ignore

if sys.platform == "win32":
    print("This application was not made for windows. Try Using WSL2")
    from time import sleep
    sleep(3)

with PipInstaller() as p:
    packages = {
        'opencv-python':   "cv2",
        'python-dateutil': "dateutil",
        'imagehash':       "imagehash",
        'imagesize':       "imagesize",
        'pillow':          "PIL",
        'rich':            "rich",
        'rich-argparse':   "rich_argparse",
        'shtab':           "shtab",
        'tqdm':            "tqdm",
        'cfg-argparser':   "cfg_argparser"
    }

    try:
        # loop import packages
        for i, package in enumerate(ipbar(packages, clear=True, print_item=True)):
            if not p.available(packages[package]):
                print(f"\033[2K !!! {packages[package]} failed to import !!!")
                raise ImportError

    except (ImportError, ModuleNotFoundError):
        response = input(
            "A package failed to import. Would you like to try and install required packages? y/N: ")
        if response.lower() not in ["y", "yes"] or not response:
            print("Please inspect the requirements.txt file.")
            sys.exit()
        # Try to install packages
        try:
            for i, package in enumerate(ipbar(packages)):
                if not p.available(packages[package]):
                    columns = os.get_terminal_size().columns
                    print(f"{package} not detected. Attempting to install...".ljust(columns, '-'))
                    p.install(package)
                    print()
                    if not p.available(packages[package]):
                        raise ModuleNotFoundError(f"Failed to install '{package}'.")
            # restart process once installing required packages is complete
            if not is_subprocess():
                os.execv(sys.executable, ['python', *sys.argv])
            else:  # process failed even after installation, so something may be wrong with perms idk
                raise SubprocessError("Failed to install packages.")
        except (SubprocessError, ModuleNotFoundError) as err2:
            print(f"{type(err2).__name__}: {err2}")
            sys.exit(127)  # command not found

    else:
        print("\033[2K", end="")
        import cv2
        import dateutil.parser as timeparser
        import imagehash
        import imagesize
        from PIL import Image
        # from rich import print as rprint
        from rich.traceback import install
        from rich_argparse import ArgumentDefaultsRichHelpFormatter
        from tqdm import tqdm
        from cfg_argparser import ConfigArgParser

        from util.print_funcs import RichStepper
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
                        help="Input folder.")
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
    p_mods.add_argument("--anonymous", action="store_true",
                        help="hides path names in progress. Doesn't affect the result.")
    p_mods.add_argument("--simulate", action="store_true",
                        help="skips the conversion step. Used for debugging.")
    p_mods.add_argument("--purge", action="store_true",
                        help="Clears the output folder before running.")
    p_mods.add_argument("--reverse", action="store_true",
                        help="reverses the sorting direction. it turns smallest-> largest to largest -> smallest")
    p_mods.add_argument("--overwrite", action="store_true",
                        help="Skips checking for existing files, and by proxy, overwrites existing files.")

    # certain criteria that images must meet in order to be included in the processing.
    p_filters = parser.add_argument_group("Filters")
    p_filters.add_argument("-w", "--whitelist", type=str, metavar="INCLUDE",
                           help="only allows paths with the given string.")
    p_filters.add_argument("-b", "--blacklist", type=str, metavar="EXCLUDE",
                           help="excludes paths with the given string.")
    p_filters.add_argument("--list-separator", default=" ",
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
    # p_filters.add_argument("--hash", action="store_true",
    #                        help="Removes similar images. is better for perceptually similar images.")
    # p_filters.add_argument("--hash-type", type=str, choices=["average", "crop_resistant", "color", "dhash", "dhash_vertical",
    #                                                          "phash", "phash_simple", "whash"], default="average",
    #                        help="type of image hasher to use for the slow method. read https://github.com/JohannesBuchner/imagehash for more info")
    # p_filters.add_argument("--hash-choice", type=str, choices=["name", "ext", "len",  "res", "time", "size", "random"],
    #                        default='res', help="At the chance of a hash conflict, this will decide which to keep.")
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


def get_file_list(*folders: Path) -> list[Path]:
    """
    Args    folders: One or more folder paths.
    Returns list[Path]: paths in the specified folders."""
    i = ipbar(folders, clear=True) if len(folders) > 1 else folders
    return [Path(y) for x in (glob(str(p), recursive=True) for p in i) for y in x]


def get_existing(*folders: Path) -> set:
    """
    Returns the files that already exist in the specified folders.
    Args    *: folders to be searched & compared.
    Returns tuple[set[Path], set[Path]]: HR and LR file paths in sets.
    """
    return set.intersection(*({file.relative_to(folder).with_suffix('')
                               for file in get_file_list((folder / "**" / "*"))}
                              for folder in folders))


def has_links(paths) -> bool:
    return any(i for i in paths if i is not i.resolve())


def to_recursive(path, recursive) -> Path:
    """Convert the file path to a recursive path if recursive is False
    Ex: i/path/to/image.png => i/path_to_image.png"""
    return Path(path) if recursive else Path(str(path).replace(os.sep, "_"))


def whitelist(imglist, whitelist) -> set:
    return {j for i in whitelist for j in imglist if i in str(j)}


def blacklist(imglist, blacklist) -> set:
    return set(imglist).difference(whitelist(imglist, blacklist))


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


def get_imghash(path, hasher): return IMHASH_TYPES[hasher](Image.open(path))


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


def within_time_and_res(img_path,
                        before, after,
                        minsize, maxsize,
                        scale, crop_mod) -> tuple[bool, os.stat_result, tuple]:
    # filter images that are too young or too old
    mstat = img_path.stat()
    filetime = datetime.fromtimestamp(mstat.st_mtime)
    sbool = not ((before and (before < filetime))
                 or (after and (after > filetime)))

    # filter images that are too small or too big, or not divisible by scale
    res = imagesize.get(img_path)
    if crop_mod:
        res = (res[0] // scale) * scale, (res[1] // scale) * scale
    minsize, maxsize = minsize or min(res), maxsize or max(res)
    rbool = all(dim % scale == 0 and minsize <= dim <= maxsize for dim in res)

    return (sbool and rbool), mstat, res


class DatasetBuilder:
    def __init__(self, rich_stepper_object, processes=1):
        super().__init__()
        self.filters: list[Type[DataFilter]] = [
        ]
        self.power = processes
        self.stepper = rich_stepper_object

    def add_filters(self, *filters):
        for filter in filters:
            filter.set_parent(self)
            self.filters.append(filter)

    def run_filters(self, x):
        return all(filter.compare(x) for filter in self.filters)

    def filter(self, filelist):
        with Pool(self.power) as p:
            for result, file in zip(tqdm(p.imap(self.run_filters, filelist), total=len(filelist)), filelist):

                if result:
                    yield file

    def _apply(self, filter_filelist):
        filter, filelist = filter_filelist
        return filter.apply(filelist)

    def apply(self, filelist):
        with Pool(self.power) as p:
            # return set.intersection(
            #     tqdm(p.imap)
            # )
            outcomes = []

            for outcome in tqdm(p.imap(self._apply, zip(self.filters, [filelist]*len(self.filters))), total=len(self.filters)):
                outcomes.append(set(outcome))
            outset = set.intersection(*outcomes)
        return outset

    def get_data(self):
        return {filter: filter.data for filter in self.filters}

    def __enter__(self):
        self.__init__()
        return self

    def __exit__(self, exc_type, exc_value, exc_traceback):
        self.filters.clear()
        del self.filters
        pass


class DataFilter:
    def __init__(self):
        # Attributes will be added by the filters
        self.data = dict()
        # Boolean if it should be applied to the whole list at once
        self.all = False
        self.parent = None
        pass

    def set_parent(self, parent: DatasetBuilder):
        self.parent = parent

    def compare(self, file: Path) -> tuple[bool, dict | None]:
        return True

    def update(self, other: dict):
        self.data.update(other)

    def reason(self, x):
        if x in self.data:
            return f"{self.data[x]}"

    def __repr__(self):
        attrlist = []
        for key, val in self.__dict__.items():
            if hasattr(val, "__iter__") and not isinstance(val, str):
                attrlist.append(f"{key}=...")
            else:
                attrlist.append(f"{key}={val}")
        out = ", ".join(attrlist)
        return f"{self.__class__.__name__}({out})"

    def __str__(self):
        return self.__class__.__name__


class DataFilterStat(DataFilter):
    def __init__(self, beforetime: datetime | None, aftertime: datetime | None):
        super().__init__()
        self.before = beforetime
        self.after = aftertime

    def compare(self, file: Path) -> tuple[bool, int]:
        st_mtime = datetime.fromtimestamp(file.stat().st_mtime)

        return not ((self.after and self.after < st_mtime) or (self.before and self.before > st_mtime))


class DataFilterRes(DataFilter):
    def __init__(self, minsize: int | None, maxsize: int | None, crop_mod: bool, scale: int):
        super().__init__()
        self.min: int | None = minsize
        self.max: int | None = maxsize
        self.crop: bool = crop_mod
        self.scale: int = scale

    def compare(self, file: Path) -> tuple[bool, tuple[int, int]]:
        # setattr(file, "res", imagesize.get(file.path))
        res = imagesize.get(file)
        if self.crop:
            res = (res[0] // self.scale) * self.scale, (res[1] // self.scale) * self.scale
        minsize, maxsize = self.min or min(res), self.max or max(res)

        return all(dim % self.scale == 0 and minsize <= dim <= maxsize for dim in res)


# class DataFilterHash(DataFilter):
#     IMHASH_TYPES = {
#         'average': imagehash.average_hash,
#         'crop_resistant': imagehash.crop_resistant_hash,
#         'color': imagehash.colorhash,
#         'dhash': imagehash.dhash,
#         'dhash_vertical': imagehash.dhash_vertical,
#         'phash': imagehash.phash,
#         'phash_simple': imagehash.phash_simple,
#         'whash': imagehash.whash
#     }

#     def __init__(self, hasher: str, hash_choice: str):
#         super().__init__()
#         if hasher not in IMHASH_TYPES:
#             raise KeyError(f"{hasher} is not in IMHASH_TYPES")
#         self.hasher = IMHASH_TYPES[hasher]
#         self.conflict_resolution = hash_choice

#     def compare(self, file: Path) -> tuple[bool, dict]:
#         hash = str(self.hasher(Image.open(file)))
#         return (True, hash)


def fileparse(inpath: Path, source: Path, scale: int,
              hr_folder: Path, lr_folder: Path,
              recursive: bool, ext=None) -> Path:
    """
    Converts an image file to HR and LR versions and saves them to the specified folders.
    Returns tuple[Path, tuple[...]]: solely for printing.
    """
    # Generate the HR & LR file paths
    hr_path, lr_path = hrlr_pair(inpath, hr_folder, lr_folder, recursive, ext)

    # Read the image file
    image = cv2.imread(str(source), cv2.IMREAD_UNCHANGED)
    image = image[0:(image.shape[0] // scale) * scale,
                  0:(image.shape[1] // scale) * scale]
    # Save the HR / LR version of the image
    cv2.imwrite(str(hr_path), image)
    cv2.imwrite(str(lr_path), cv2.resize(image, (0, 0),
                fx=1 / scale, fy=1 / scale))  # type: ignore

    # Set the modification time of the HR and LR image files to the original image's modification time
    mtime = source.stat().st_mtime
    os.utime(str(hr_path), (mtime, mtime))
    os.utime(str(lr_path), (mtime, mtime))

    # Return the input path of the image file
    return inpath


def main():
    cparser = ConfigArgParser(main_parser(), "config.json", exit_on_change=True)
    args = cparser.parse_args()

    s = RichStepper(loglevel=1, step=-1)
    s.next("Settings: ")

    df = DatasetBuilder(s, args.threads)

    def check_for_images(image_list) -> None:
        if not image_list:
            s.print(-1, "No images left to process")
            sys.exit(0)

# * Make sure given args are valid
    if not args.input:
        s.print("Please specify an input directory.")
        return 1
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

        df.add_filters(DataFilterStat(args.before, args.after))

    args.minsize = args.minsize if args.minsize != -1 else None
    args.maxsize = args.maxsize if args.maxsize != -1 else None
    df.add_filters(DataFilterRes(args.minsize, args.maxsize, args.crop_mod, args.scale))

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

    # s.print(
    #     f"input: {args.input}",
    #     f"hr: {hr_folder}",
    #     f"lr: {lr_folder}",
    #     f"scale: {args.scale}",
    #     f"threads: {args.threads}",
    #     f"extension: {args.extension}",
    #     f"recursive: {args.recursive}",
    #     f"anonymous: {args.anonymous}",
    #     f"crop_mod: {args.crop_mod}",
    # )

# * Gather images
    s.next("Gathering images...")
    args.exts = args.exts.split(" ")
    s.print(f"Searched extensions: {args.exts}")
    file_list = get_file_list(*[args.input / "**" / f"*.{ext}" for ext in args.exts])
    image_list = sorted(file_list)
    if args.image_limit and args.limit_mode == "before":  # limit image number
        image_list = image_list[:args.image_limit]
    s.print(f"Gathered {len(image_list)} images")

    if args.whitelist:
        args.whitelist = args.whitelist.split(args.list_separator)
        image_list = whitelist(image_list, args.whitelist)
        s.print(f"whitelist {args.whitelist}: {len(image_list)}")
    if args.blacklist:
        args.blacklist = args.blacklist.split(args.list_separator)
        image_list = blacklist(image_list, args.blacklist)
        s.print(f"blacklist {args.blacklist}: {len(image_list)}")

    s.next()

# # * hashing option
#     if args.hash:
#         df.add_filters(DataFilterHash(args.hash_type, args.hash_choice))

# * Run filters
    s.print(
        "Filtering using: ",
        *[f" - {str(filter)}" for filter in df.filters]
    )

    image_list = set(df.filter(image_list))
    # rprint(image_list)
    check_for_images(image_list)

# * Discard symbolic duplicates
    original_total = len(image_list)
    if has_links(image_list):
        # vv This naturally removes the possibility of multiple files pointing to the same image
        image_list = set({i.resolve(): i.relative_to(args.input)
                          for i in ipbar(image_list, clear=True)}.values())
        if len(image_list) != original_total:
            s.print(f"Discarded {original_total - len(image_list)} symbolic links")

# * Purge existing images
    if args.purge:
        s.next("Purging...")
        for path in ipbar(image_list):
            hr_path, lr_path = hrlr_pair(path, hr_folder, lr_folder, args.recursive, args.extension)
            hr_path.unlink(missing_ok=True)
            lr_path.unlink(missing_ok=True)

        s.print("Purged.")

# * Get files that were already converted
    original_total = len(image_list)
    if not args.overwrite:
        s.next("Removing existing")
        exist_list = get_existing(hr_folder, lr_folder)
        image_list = {i for i in ipbar(image_list, clear=True)
                      if to_recursive(i, args.recursive).with_suffix("") not in exist_list}

    if len(image_list) != original_total:
        s.print(f"Discarded {original_total-len(image_list)} existing images")
    else:
        s.print("None found")
    check_for_images(image_list)

    if args.image_limit and args.limit_mode == "after":
        image_list = set(image_list[:args.image_limit])

    if args.simulate:
        s.next(f"Simulated. {len(image_list)} images remain.")
        return 0

    try:
        pargs = [(v, args.input / v, args.scale, hr_folder, lr_folder, args.recursive, args.extension)
                 for v in image_list]
        with Pool(args.threads) as p:
            for _ in tqdm(istarmap(p, fileparse, pargs), total=len(image_list)):
                pass
    except KeyboardInterrupt:
        s.print(-1, "KeyboardInterrupt")

    exit()

# * filter by image hashes
    # if args.hash:
    #     s.next("Getting hashes...")
    #     s.print(f"Hash type: {args.hash_type}")
    #     original_total = len(image_list)

    #     pargs = [(args.input / i, args.hash_type) for i in file_list]
    #     # match each hash to the respective image
    #     image_hashes: dict = {}
    #     for index, file_hash in enumerate(poolmap(args.threads, get_imghash, pargs, postfix=False)):
    #         file = file_list[index].relative_to(args.input)
    #         file_hash = str(file_hash)
    #         if file_hash in image_hashes:
    #             image_hashes[file_hash].append(file)
    #         else:
    #             image_hashes[file_hash] = [file]

    #     s.print(f"Comparing images (Conflict resolution: {args.hash_choice})...")

    #     # hashes that belong to multiple images
    #     conflicting_hashes: dict[str, list[Path]] = {}
    #     # hashes that belong to a single image
    #     final_hashes: dict[str, Path] = {}
    #     for filehash, filelist in image_hashes.items():
    #         if len(filelist) > 1:
    #             conflicting_hashes.update({filehash: filelist})

    #         if len(filelist) == 1:
    #             final_hashes.update({filehash: filelist[0]})

    #     for filehash, filelist in conflicting_hashes.items():
    #         conflicting_hashes[filehash] = [file for file in filelist if file in image_data]
    #         if len(filelist) == 1:
    #             final_hashes.update({filehash: filelist[0]})

    #     conflicting_hashes = {key: val for key, val in conflicting_hashes.items() if len(val) > 1}
    #     # conflicting hashes now are all still valid but now a single image must be chosen to keep
    #     for filehash, filelist in conflicting_hashes.items():
    #         # choose based on sorting method (args.hash_choice)
    #         chosen_file = sorted(filelist, key=sorting_methods[args.hash_choice])[-1]
    #         final_hashes.update({filehash: chosen_file})
    #         if args.print_filtered:
    #             rprint(f'[yellow]"{filehash}"[/yellow]: ')
    #             for file in filelist:
    #                 rprint(
    #                     (f'[bold   green]  \u2713 "{args.input / file}"[/bold   green]'  # ✓
    #                      if file == chosen_file else
    #                      f'[bright_black]  \u2717 "{args.input / file}"[/bright_black]')  # ✗
    #                     + f' : {image_data[file][1]}'
    #                 )

    #             if any(file.with_suffix("") == i.with_suffix("") and file is not i
    #                    for i in filelist
    #                    for file in filelist):
    #                 rprint(" [red]Warning: some of these images have very similar paths.")

    #     image_list = set(image_list).intersection(final_hashes.values())
    #     s.print(f"Discarded {original_total - len(image_list)} images via imagehash.{args.hash_choice}")
    #     check_for_images(image_list)


if __name__ == "__main__":
    sys.exit(main())
