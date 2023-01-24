"""Conversion script from folder to hr/lr pair.

@author zeptofine
"""
import os
import sys
from argparse import ArgumentParser
from datetime import datetime
from functools import lru_cache
from glob import glob
from pathlib import Path
from subprocess import SubprocessError

from ConfigArgParser import ConfigParser
from util.pip_helpers import PipInstaller
from util.print_funcs import ipbar, Timer  # trunk-ignore(flake8/F401)
from util.process_funcs import is_subprocess

CPU_COUNT: int = os.cpu_count()

if sys.platform == "win32":
    print("This application was not made for windows. Try Using WSL2")
    from time import sleep
    sleep(3)

with PipInstaller() as p:
    packages = {'rich':            "rich",
                'opencv-python':   "cv2",
                'python-dateutil': "dateutil",
                'imagesize':       "imagesize",
                'rich-argparse':   "rich_argparse",
                'tqdm':            "tqdm",
                'shtab':           "shtab"}

    try:
        # loop import packages
        for i, package in enumerate(ipbar(packages, clear=True)):
            # print(f"{p_bar_stat(i, len(packages))}", end="\r")
            if not p.available(packages[package]):
                print(f"\033[2K !!! {packages[package]} failed to import !!!")
                raise ImportError

    except (ImportError, ModuleNotFoundError):
        # Try to install packages
        try:
            for i, package in enumerate(ipbar(packages)):
                if not p.available(packages[package]):
                    columns = os.get_terminal_size().columns
                    print(
                        f"{package} not detected. Attempting to install...".ljust(columns, '-'))
                    p.install(package)
                    print()
                    if not p.available(packages[package]):
                        raise ModuleNotFoundError(
                            f"Failed to install '{package}'.")
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
        import imagesize
        from rich import print as rprint  # trunk-ignore(flake8/F401)
        from rich.traceback import install
        from rich_argparse import ArgumentDefaultsRichHelpFormatter
        from tqdm import tqdm  # trunk-ignore(flake8/F401)

        from util.iterable_starmap import poolmap
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
    p_mods = parser.add_argument_group("Modifiers")
    p_mods.add_argument("-r", "--recursive", action="store_true", default=False,
                        help="preserves the tree hierarchy.")
    p_mods.add_argument("-t", "--threads", type=int, default=int((CPU_COUNT / 4) * 3),
                        help="number of total threads used for multiprocessing.")
    p_mods.add_argument("--image_limit", type=int, default=None, metavar="MAX",
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
    p_mods.add_argument("--sort", choices=["name", "ext", "len", "res", "time", "size"], default="res",
                        help="sorting method.")
    p_mods.add_argument("--reverse", action="store_true",
                        help="reverses the sorting direction. it turns smallest-> largest to largest -> smallest")
    p_mods.add_argument("--overwrite", action="store_true",
                        help="Skips checking for existing files, and by proxy, overwrites existing files.")
    # certain criteria that images must meet in order to be included in the processing.
    p_filters = parser.add_argument_group("Filters")
    p_filters.add_argument("--whitelist", type=str, metavar="INCLUDE",
                           help="only allows paths with the given string.")
    p_filters.add_argument("--blacklist", type=str, metavar="EXCLUDE",
                           help="excludes paths with the given string.")
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
    # ^^ Used for filtering out too old or too new images.
    return parser


@lru_cache
def get_resolution(path: Path):
    """
    Args    path: The path to the image file.
    Returns tuple[width, height]."""
    return imagesize.get(path) or cv2.imread(path).shape[:2]


def get_file_list(*folders: Path) -> list[Path]:
    """
    Args    folders: One or more folder paths.
    Returns list[Path]: paths in the specified folders."""
    i = ipbar(folders, clear=True) if len(folders) > 1 else folders
    globlist = (glob(str(p), recursive=True) for p in i)
    return [Path(y) for x in globlist for y in x]


def get_existing(*folders: list[Path]) -> set[Path]:
    """
    Returns the files that already exist in the specified folders.
    Args    *: folders to be searched & compared.
    Returns tuple[set[Path], set[Path]]: HR and LR file paths in sets.
    """
    sets = ({file.relative_to(folder).with_suffix('')
            for file in get_file_list((folder / "**" / "*"))}
            for folder in folders)
    outset = set.intersection(*sets)
    return outset


def has_links(paths):
    return any(i for i in paths if i is not i.resolve())


def to_recursive(path: Path, recursive: bool) -> Path:
    """Convert the file path to a recursive path if recursive is False
    Ex: i/path/to/image.png => i/path_to_image.png"""
    return path if recursive else Path(str(path).replace(os.sep, "_"))


def whitelist(imglist, whitelist):
    return {j for i in whitelist for j in imglist if i in str(j)}


def blacklist(imglist, blacklist):
    imglist_with_blacklist = whitelist(imglist, blacklist)
    return set(imglist).difference(imglist_with_blacklist)


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


def within_time_and_res(img_path, before, after, minsize, maxsize, scale, crop_mod) -> tuple[bool, tuple, tuple]:
    # filter images that are too young or too old
    mstat = img_path.stat()
    filetime = datetime.fromtimestamp(mstat.st_mtime)
    if before or after and (before and (before < filetime)) or (after and (after > filetime)):
        return False, 0, 0

    # filter images that are too small or too big, or not divisible by scale
    res = get_resolution(img_path)
    if crop_mod:
        res = (res[0] // scale) * scale, (res[1] // scale) * scale
    if not (res[0] % scale == 0 and res[1] % scale == 0) or (
            minsize and (res[0] < minsize or res[1] < minsize)) or (
            maxsize and (res[0] > maxsize or res[1] > maxsize)):
        return False, 0, 0

    return True, mstat, res


def fileparse(inpath: Path, source: Path, mtime, scale: int,
              hr_folder: Path, lr_folder: Path,
              recursive: bool, ext=None) -> Path:
    """
    Converts an image file to HR and LR versions and saves them to the specified folders.
    Returns tuple[Path, tuple[...]]: solely for printing.
    """
    # Generate the HR & LR file paths
    hr_path, lr_path = hrlr_pair(inpath, hr_folder, lr_folder, recursive, ext)

    # Read the image file
    image = cv2.imread(source, cv2.IMREAD_UNCHANGED)
    image = image[0:(image.shape[0] // scale) * scale,
                  0:(image.shape[1] // scale) * scale]

    # Save the HR / LR version of the image
    cv2.imwrite(str(hr_path), image)
    cv2.imwrite(str(lr_path), cv2.resize(
        image, (0, 0), fx=1 / scale, fy=1 / scale))

    # Set the modification time of the HR and LR image files to the original image's modification time
    os.utime(str(hr_path), (mtime, mtime))
    os.utime(str(lr_path), (mtime, mtime))

    # Return the input path of the image file
    return inpath


def main():
    cparser = ConfigParser(main_parser(), "config.json", exit_on_change=True)
    args = cparser.parse_args()

    s = RichStepper(loglevel=1, step=-1)

    def check_for_images(image_list) -> None:
        if not list(image_list):
            s.print(-1, "No images left to process")
            sys.exit(0)

# Make sure given args are valid
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

    s.next("Settings: ")
    s.print(f"input: {args.input}",
            f"scale: {args.scale}",
            f"threads: {args.threads}",
            f"extension: {args.extension}",
            f"recursive: {args.recursive}",
            f"anonymous: {args.anonymous}",
            f"crop_mod: {args.crop_mod}",
            f"sort: {args.sort}")

# Gather images
    s.next("Gathering images...")
    args.input = Path(args.input)
    image_list = get_file_list(args.input / "**" / "*.png",
                               args.input / "**" / "*.jpg",
                               args.input / "**" / "*.webp")
    if args.image_limit and args.limit_mode == "before":  # limit image number
        image_list = image_list[:args.image_limit]
    s.print(f"Gathered {len(image_list)} images")

# Filter blacklisted/whitelisted items
    if args.whitelist:
        args.whitelist = args.whitelist.split(" ")
        image_list = whitelist(image_list, args.whitelist)
        s.print(f"whitelist {args.whitelist}: {len(image_list)}")
    if args.blacklist:
        args.blacklist = args.blacklist.split(" ")
        image_list = blacklist(image_list, args.blacklist)
        s.print(f"blacklist {args.blacklist}: {len(image_list)}")

# Discard symbolic duplicates
    original_total = len(image_list)
    if has_links(image_list):
        # vv This naturally removes the possibility of multiple files pointing to the same image
        image_list = {i.resolve(): i.relative_to(args.input)
                      for i in ipbar(image_list, clear=True)}.values()
        if len(image_list) != original_total:
            s.print(
                f"Discarded {original_total - len(image_list)} symbolic links")

# Get hr / lr folders
    hr_folder = args.input.parent / f"{str(args.scale)}xHR"
    lr_folder = args.input.parent / f"{str(args.scale)}xLR"
    if args.extension:
        hr_folder = Path(f"{str(hr_folder)}-{args.extension}")
        lr_folder = Path(f"{str(lr_folder)}-{args.extension}")
    hr_folder.parent.mkdir(parents=True, exist_ok=True)
    lr_folder.parent.mkdir(parents=True, exist_ok=True)

# Purge existing images
    if args.purge:
        s.next("Purging...")
        for path in ipbar(image_list):
            hr_path, lr_path = hrlr_pair(path, hr_folder, lr_folder,
                                         args.recursive, args.extension)
            hr_path.unlink(missing_ok=True)
            lr_path.unlink(missing_ok=True)

        s.print("Purged.")

# Get files that were already converted
    original_total = len(image_list)
    if not args.overwrite:
        s.next("Removing existing")
        exist_list = get_existing(hr_folder, lr_folder)
        image_list = [i for i in ipbar(image_list, clear=True)
                      if to_recursive(i, args.recursive).with_suffix("") not in exist_list]
    if len(image_list) != original_total:
        s.print(f"Discarded {original_total-len(image_list)} existing images")

    check_for_images(image_list)

# Remove files based on resolution and time
    s.next("Filtering images...")
    original_total = len(image_list)
    if args.before or args.after:
        s.print(f"Filtering by time ({args.before}<=x<={args.after})")
    if args.minsize or args.maxsize:
        s.print(f"Filtering by size ({args.minsize}<=x<={args.maxsize})")

    pargs = [(args.input / i,
              args.before, args.after,
              args.minsize, args.maxsize,
              args.scale, args.crop_mod) for i in image_list]
    image_list = zip(image_list,
                     poolmap(args.threads,
                             within_time_and_res,
                             pargs, postfix=False,
                             desc="Filtering"))
# Filter images based on data
    # separate the paths and the data, and only accept based on boolean
    image_list, image_data = zip(*filter(lambda x: x[1][0], image_list))
    # remove the boolean from the tuple
    image_data = map(lambda x: x[1:], image_data)
    # turn the data into a dict
    image_data = {image_list[i]: v for i, v in enumerate(image_data)}

    # image_list, mstat, mres = filter_images(args, image_list, cparser)
    s.print(f"Discarded {original_total - len(image_list)} images\n")

    # Notify about the crop_mod feature
    if not (cparser.file.get("cropped_before", False) or args.crop_mod):
        s.print(-1, "Try the cropping mode! It crops the image instead of outright ignoring it.(--crop_mod)")
        cparser.file.update({"cropped_before": True}).save()

    if args.simulate:
        s.next("Simulated")
        return 0

# Sort files based on attributes
    s.print("Sorting...\n")
    sorting_methods = {"name": lambda x: x,
                       "ext": lambda x: x.suffix,
                       "len": lambda x: len(str(x)),
                       "res": lambda x: image_data[x][1][0] * image_data[x][1][1],
                       "time": lambda x: image_data[x][0].st_mtime,
                       "size": lambda x: image_data[x][0].st_size}
    image_list = sorted(image_list,
                        key=sorting_methods[args.sort], reverse=args.reverse)

    if args.image_limit and args.limit_mode == "after":  # limit image number
        image_list = set(image_list[:args.image_limit])

# create hr/lr pairs from list of valid images
    s.next(f"{len(image_list)} images in queue")
    try:
        pargs = [(v, str(args.input / v), image_data[v][0].st_mtime, args.scale,
                  hr_folder, lr_folder,
                  args.recursive, args.extension)
                 for v in image_list]
        image_list = poolmap(args.threads, fileparse, pargs,
                             chunksize=2,
                             postfix=not args.anonymous,
                             use_tqdm=True)
    except KeyboardInterrupt:
        s.print(-1, "KeyboardInterrupt")
    s.next("Done")
    return 0


if __name__ == "__main__":
    sys.exit(main())
