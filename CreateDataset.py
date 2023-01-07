"""Conversion script from folder to hr/lr pair.

@author zeptofine
"""
import argparse
import datetime
import glob
import os
import subprocess
import sys
import time
from pathlib import Path

from ConfigArgParser import ConfigParser
from util.pip_helpers import PipInstaller
from util.print_funcs import p_bar_stat
from util.process_funcs import is_subprocess

CPU_COUNT: int = os.cpu_count()  # type: ignore


if sys.platform == "win32":
    print("This application was not made for windows. Try Using WSL2")
    time.sleep(3)

packages = {'rich':            "rich",
            'opencv-python':   "cv2",
            'python-dateutil': "dateutil",
            'imagesize':       "imagesize",
            'rich-argparse':   "rich_argparse",
            'tqdm':            "tqdm",
            'shtab':           "shtab"}

with PipInstaller() as p:
    try:
        # loop import packages
        for i, package in enumerate(packages):
            print(f"{p_bar_stat(i, len(packages))}", end="\r")
            if not p.available(packages[package]):
                raise ImportError

    except (ImportError, ModuleNotFoundError):
        # Try to install packages and restart
        try:
            for i, package in enumerate(packages):
                if not p.available(packages[package]):
                    print(f"{p_bar_stat(i, len(packages))}")
                    columns = os.get_terminal_size().columns
                    print(
                        f"{'-'*columns}\n" + str(f"{package} not detected. Attempting to install...").center(columns))
                    p.install(package)
                    if not p.available(packages[package]):
                        raise ModuleNotFoundError(
                            f"Failed to install '{package}'.")
            if not is_subprocess():
                os.execv(sys.executable, ['python', *sys.argv])
            else:
                raise subprocess.SubprocessError("Failed to install packages.")
        except (subprocess.SubprocessError, ModuleNotFoundError) as err2:
            print(f"{type(err2).__name__}: {err2}")
            sys.exit(127)  # command not found

    finally:
        from rich import print as rprint
        from rich.traceback import install
        install()

        import cv2
        import dateutil.parser as timeparser
        import imagesize
        from rich_argparse import ArgumentDefaultsRichHelpFormatter
        from tqdm import tqdm

        from util.iterable_starmap import poolmap


def main_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
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
                        help="number of total threads.")  # used for multiprocessing
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
    p_mods.add_argument("--purge_only", action="store_true",
                        help="--purge, but finishes afterwards.")
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
    p_filters.add_argument("--list-filter-whole", action="store_true",
                           help="treats the whole whitelist as a single string. By default it separates it by spaces and only allows files that accept every criteria.")
    p_filters.add_argument("--blacklist", type=str, metavar="EXCLUDE",
                           help="excludes paths with the given string.")
    # ^^ used for restricting the names allowed in the paths.

    p_filters.add_argument("--minsize", type=int, metavar="MIN", default=128,
                           help="smallest available image")
    p_filters.add_argument("--maxsize", type=int, metavar="MAX",
                           help="largest allowed image.")
    p_filters.add_argument("--crop_mod", type=bool, default=False,
                           help="changes mod mode so that it crops the image to an image that actually is divisible by scale, typically by a few px")
    # ^^ used for filtering out too small or too big images.
    p_filters.add_argument("--after", type=str,
                           help="Only uses files modified after a given date."
                           "ex. '2020', or '2009 Sept 16th'")
    p_filters.add_argument("--before", type=str,
                           help="Only uses before a given date. ex. 'Wed Jun 9 04:26:40', or 'Jun 9'")
    # ^^ Used for filtering out too old or too new images.
    return parser


def next_step(order, *args) -> None:
    orderd = {-1: "[yellow]INFO[/yellow]",
              -2: "[orange]WARNING[/orange]",
              -3: "[grey]DEBUG[/grey]",
              -9: "[red]ERROR[/red]",
              }
    output = orderd.get(order, f"[blue]{order}[/blue]")
    output = [f" {output}: {text}" for text in args]
    rprint("\n".join(output), end="\n\033[K")


def get_resolution(path: Path):
    """path: The path to the image file.

    Returns the resolution of the image file as a tuple of (width, height).
    """
    return imagesize.get(path)


def get_file_list(*folders: Path) -> list[Path]:
    """folders: One or more folder paths.
    Returns a list of file paths in the specified folders.
    """
    globlist = [glob.glob(str(p), recursive=True)
                for p in folders]
    return [Path(y) for x in globlist for y in x]


def get_existing_files(hr_folder, lr_folder) -> tuple[set[Path], set[Path]]:
    """Returns the HR and LR files that already exist in the specified folders.
    Args:
        hr_folder: The folder where the HR files are stored.
        lr_folder: The folder where the LR files are stored.
    Returns a tuple of sets of HR and LR file paths.
    """
    hfiles = {f.relative_to(hr_folder).with_suffix("")
              for f in get_file_list((hr_folder / "**" / "*"))}
    lfiles = {f.relative_to(lr_folder).with_suffix("")
              for f in get_file_list((lr_folder / "**" / "*"))}
    return hfiles, lfiles


def to_recursive(path: Path, recursive: bool) -> Path:
    """ Convert the file path to a recursive path if recursive is False
    Ex: i/path/to/image.png => i/path_to_image.png"""
    return path if recursive else Path(str(path).replace(os.sep, "_"))


def check_for_images(image_list) -> None:
    if not list(image_list):
        next_step(-1, "No images left to process")
        sys.exit(0)


def hrlr_pair(path: Path, hr_folder: Path, lr_folder: Path,
              recursive: bool = False, ext=None) -> tuple[Path, Path]:
    hr_path = hr_folder / to_recursive(path, recursive)
    lr_path = lr_folder / to_recursive(path, recursive)
    # Create the HR and LR folders if they do not exist
    hr_path.parent.mkdir(parents=True, exist_ok=True)
    lr_path.parent.mkdir(parents=True, exist_ok=True)
    # If an extension is provided, append it to the HR and LR file paths
    if ext and path.is_file():
        hr_path = hr_path.with_suffix(f".{ext}")
        lr_path = lr_path.with_suffix(f".{ext}")
    return hr_path, lr_path


def within_time(inpath, before_time, after_time) -> tuple[bool, float]:
    """Checks if an image is within specified time limits.
        inpath: the path to the image file.
        before_time: the image must be before this time.
        after_time: the image must be after this time.
    Returns:
        A tuple of (success, modification time).
    """
    mstat = inpath.stat()
    filetime = datetime.datetime.fromtimestamp(mstat.st_mtime)
    # compare the file time to given threshold
    if (before_time and (before_time < filetime)) or (after_time and (after_time > filetime)):
        return (False, mstat)
    return (True, mstat)


def within_res(inpath, minsize, maxsize, scale, crop_mod) -> tuple[bool, tuple]:
    """Checks if an image is within specified resolution limits.
        inpath: The path to the image file.
        minsize: The minimum allowed resolution for the image.
        maxsize: The maximum allowed resolution for the image.
        scale: The scale factor to use when checking the resolution.
        crop_mod: A boolean value indicating whether to crop the image to the nearest multiple of the scale factor.
    Returns A tuple of (success, resolution).
    """

    # Get the resolution of the image
    res: tuple = get_resolution(inpath)  # => (width, height)
    width, height = res

    if crop_mod:
        # crop the image to the nearest multiple of the scale factor
        width, height = (width // scale) * scale, (height // scale) * scale
    elif (width % scale != 0 or height % scale != 0):
        return (False, res)
    if (minsize and (width < minsize or height < minsize)) \
            or (maxsize and (width > maxsize or height > maxsize)):
        return (False, res)
    return (True, (width, height))


def fileparse(inpath: Path, source: Path, mtime, scale: int,
              hr_folder: Path, lr_folder: Path,
              recursive: bool, crop_mod: bool, ext=None):
    """Converts an image file to HR and LR versions and saves them to the specified folders.
    Returns:
        The input path of the image file, to be printed.
    """
    # Generate the HR & LR file paths
    hr_path, lr_path = hrlr_pair(inpath, hr_folder, lr_folder, recursive, ext)

    # Read the image file
    image = cv2.imread(source, cv2.IMREAD_UNCHANGED)  # type: ignore
    imshape = image.shape

    if crop_mod:
        # crop the image
        image = image[0:(imshape[0] // scale) * scale,
                      0:(imshape[1] // scale) * scale]

    # Save the HR / LR version of the image
    cv2.imwrite(str(hr_path), image)  # type: ignore
    cv2.imwrite(str(lr_path), cv2.resize(  # type: ignore
        image, (0, 0), fx=1 / scale, fy=1 / scale))

    # Set the modification time of the HR and LR image files to the original image's modification time
    os.utime(str(hr_path), (mtime, mtime))
    os.utime(str(lr_path), (mtime, mtime))

    # Return the input path of the image file
    return inpath, imshape


def white_black_list(args, imglist):
    for f, j in [("whitelist", True), ("blacklist", False)]:
        # get the whitelist or blacklist from args
        if i := getattr(args, f):
            # if filter is not considered whole, use every element separated by spaces
            i = i.split(" ") if not args.list_filter_whole else [i]
            imglist = [k for k in imglist if
                       (any(i in str(k) for i in i)) == j]
            next_step(1, f"{f} {i}: {len(imglist)}")
    return imglist


def filter_images(args, imglist, cparser: ConfigParser):
    # filter images that are too young or too old
    pargs = [(args.input / i, args.before, args.after) for i in imglist]
    mstat = poolmap(args.threads, within_time, pargs,
                    desc=f"Filtering by time ({args.before}<=x<={args.after})",
                    postfix=False)
    mstat = filter(lambda x: x[1][0], zip(imglist, mstat))
    imglist, mstat = zip(*mstat)
    mstat = {imglist[i]: mstat[i][1] for i in range(len(imglist))}
    check_for_images(mstat)

    # Make a tooltip to the user if not cropped_before
    if not (cparser.file.get("cropped_before", False) and args.crop_mod):
        next_step(-1, "Try the cropping mode! It crops the image instead of outright ignoring it.")
        cparser.file.update({"cropped_before": True}).save()

    # filter images that are too small or too big, or not divisible by scale
    pargs = [(args.input / i, args.minsize, args.maxsize,
              args.scale, args.crop_mod) for i in imglist]
    mres = poolmap(args.threads, within_res, pargs,
                   desc=f"Filtering by resolution ({args.minsize} <= x <= {args.maxsize}) % {args.scale}",
                   postfix=not args.anonymous)
    mres = list(filter(lambda x: x[1][0], zip(imglist, mres)))
    check_for_images(mres)
    imglist, mres = zip(*mres)
    mres = {imglist[i]: mres[i][1] for i in range(len(imglist))}

    return imglist, mstat, mres


def main():
    parser = main_parser()

    cparser = ConfigParser(parser, "config.json", exit_on_change=True)
    args = cparser.parse_args()

    if not (args.input):
        sys.exit("Please specify an input directory.")

    next_step(0,
              f"input: {args.input}", f"scale: {args.scale}",
              f"threads: {args.threads}", f"extension: {args.extension}",
              f"recursive: {args.recursive}",
              f"anonymous: {args.anonymous}",
              f"crop_mod: {args.crop_mod}",
              f"sort: {args.sort}, reverse: {args.reverse}\n")

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
            next_step(-9, err)

    next_step(1, "Gathering images...")
    args.input = Path(args.input).resolve()
    image_list = get_file_list(args.input / "**" / "*.png",
                               args.input / "**" / "*.jpg",
                               args.input / "**" / "*.webp")
    if args.image_limit and args.limit_mode == "before":  # limit image number
        image_list = image_list[:args.image_limit]
    next_step(1, f"Gathered {len(image_list)} images")

    # filter out blackisted/whitelisted items
    image_list = white_black_list(args, image_list)

    original_total = len(image_list)
    # vv This naturally removes the possibility of multiple files pointing to the same image
    image_list = {i.resolve(): i.relative_to(args.input)
                  for i in tqdm(image_list, desc="Resolving")}.values()
    if len(image_list) != original_total:
        next_step(
            1, f"Discarded {original_total - len(image_list)} symbolic links")

    if args.extension and args.extension.startswith("."):
        args.extension = args.extension[1:]

    # get hr and lr folders
    hr_folder = args.input.parent / f"{str(args.scale)}xHR"
    lr_folder = args.input.parent / f"{str(args.scale)}xLR"
    if ext := args.extension:
        hr_folder = Path(f"{str(hr_folder)}-{ext}")
        lr_folder = Path(f"{str(lr_folder)}-{ext}")
    hr_folder.parent.mkdir(parents=True, exist_ok=True)
    lr_folder.parent.mkdir(parents=True, exist_ok=True)

    # Purge existing images with respect to the filter
    if args.purge or args.purge_only:
        next_step(1, "Purging...")
        count = 0
        for path in image_list:
            hr_path, lr_path = hrlr_pair(path, hr_folder, lr_folder,
                                         args.recursive, args.extension)
            if hr_path.exists() or lr_path.exists():
                count+=1
                hr_path.unlink(missing_ok=True)
                lr_path.unlink(missing_ok=True)
        # return
        next_step(1, f"Purged {count} images.")
    if args.purge_only:
        return 0
    if not args.overwrite:
        # get files that were already converted
        hfiles, lfiles = get_existing_files(hr_folder, lr_folder)
        exist_list = hfiles.intersection(lfiles)
        image_list = [i for i in tqdm(image_list, desc="Removing existing")
                      if to_recursive(i, args.recursive).with_suffix("") not in exist_list]

    next_step(
        1, f"Discarded {original_total-len(image_list)} images which already exist\n")
    check_for_images(image_list)

    # remove files based on resolution and time
    original_total = len(image_list)
    image_list, mstat, mres = filter_images(args, image_list, cparser)
    next_step(2, f"Discarded {original_total - len(image_list)} images\n")

    if args.simulate:
        next_step(3, "Simulated")
        return 0

    # Sort files based on different attributes
    next_step(3, "Sorting...\n")
    sorting_methods = {"name": lambda x: x,
                       "ext": lambda x: x.suffix,
                       "len": lambda x: len(str(x)),
                       "res": lambda x: mres[x][0] * mres[x][1],
                       "time": lambda x: mstat[x].st_mtime,
                       "size": lambda x: mstat[x].st_size}
    image_list = sorted(
        image_list, key=sorting_methods[args.sort], reverse=args.reverse)

    if args.image_limit and args.limit_mode == "after":
        image_list = set(image_list[: args.image_limit])

    # create hr/lr pairs from list of valid images
    next_step(4, f"{len(image_list)} images in queue")
    try:
        pargs = [(v, str(args.input / v), mstat[v].st_mtime, args.scale,
                  hr_folder, lr_folder,
                  args.recursive, args.crop_mod, args.extension)
                 for v in image_list]
        image_list = poolmap(args.threads, fileparse, pargs,
                             chunksize=2,
                             postfix=not args.anonymous,
                             use_tqdm=True)
    except KeyboardInterrupt:
        next_step(-1, "KeyboardInterrupt")
    next_step(-1, "Done")
    return 0


if __name__ == "__main__":
    sys.exit(main())
