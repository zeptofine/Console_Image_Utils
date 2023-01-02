"""Conversion script from folder to hr/lr pair.

@author zeptofine
"""
import argparse
import datetime
import glob
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

from ConfigArgParser import ConfigParser
from util.iterable_starmap import poolmap
from util.pip_helpers import PipInstaller
from util.process_funcs import is_subprocess

# from tqdm import tqdm


CPU_COUNT: int = os.cpu_count()  # type: ignore


if sys.platform == "win32":
    print("This application was not made for windows. Try Using WSL2")
    time.sleep(3)

try:
    from rich_argparse import ArgumentDefaultsRichHelpFormatter
except (ModuleNotFoundError, ImportError):
    ArgumentDefaultsRichHelpFormatter = argparse.ArgumentDefaultsHelpFormatter

packages = {'rich':            "rich",
            'opencv-python':   "cv2",
            'python-dateutil': "dateutil",
            'imagesize':       "imagesize",
            'rich-argparse':   "rich_argparse",
            'tqdm':            "tqdm",
            'shtab':           "shtab"}

with PipInstaller() as p:
    try:
        for package in packages:
            if not p.available(packages[package]):
                raise ImportError

    except (ImportError, ModuleNotFoundError):
        try:
            for package in packages:
                if not p.available(packages[package]):
                    import_failed = True
                    columns = os.get_terminal_size().columns
                    print(
                        f"{'-'*columns}\n" + str(f"{package} not detected. Attempting to install...").center(columns))
                    p.install(package)
                    if not p.available(packages[package]):
                        raise ModuleNotFoundError(
                            f"Failed to install '{package}'.")
            if not is_subprocess():
                os.execv(sys.executable, ['python', *sys.argv])

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


def main_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
            formatter_class=ArgumentDefaultsRichHelpFormatter,
            description="""Hi! this script converts thousands of files to
	another format in a High-res/Low-res pairs for data science.""")

    import shtab
    shtab.add_argument_to(parser)

    p_req = parser.add_argument_group("Runtime")
    p_req.add_argument("-i", "--input",
                       help="Input folder.")
    p_req.add_argument("-x", "--scale", type=int, default=4,
                       help="scale to downscale LR images")
    p_req.add_argument("-e", "--extension", metavar="EXT", default=None,
                       help="export extension.")
    p_req.add_argument("-r", "--recursive", action="store_true", default=False,
                       help="preserves the tree hierarchy.")
    # by default, images in subfolders will be saved as hr/path_to_image.png if the name was input/path/to/image.png. This stops that.

    p_mods = parser.add_argument_group("Modifiers")
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
    p_mods.add_argument("--sort", choices=["name", "ext", "len", "res", "time", "size"], default="res",
                        help="sorting method.")
    p_mods.add_argument("--reverse", action="store_true",
                                            help="reverses the sorting direction. it turns smallest-> largest to largest -> smallest")
    # certain criteria that images must meet in order to be included in the processing.
    p_filters = parser.add_argument_group("Filters")
    p_filters.add_argument("--whitelist", type=str, metavar="INCLUDE",
                           help="only allows paths with the given string.")
    p_filters.add_argument("--list-filter-mode",
                           choices=["str", "list"], default="list")
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


def next_step(order, *args) -> None:
    orderd = {-1: "[yellow]INFO[/yellow]",
              -2: "[orange]WARNING[/orange]",
              -3: "[grey]DEBUG[/grey]",
              -9: "[red]ERROR[/red]",
              }
    output = [f" {str(orderd.get(order, order))}: {text}" for text in args]
    rprint("\n".join(output), end="\n\033[K")


def get_file_list(*folders: Path) -> list[Path]:
    globlist = [glob.glob(str(p), recursive=True)
                for p in folders]
    return [Path(y) for x in globlist for y in x]


def get_existing_files(hr_folder, lr_folder):
    h = {f.relative_to(hr_folder).with_suffix("")
         for f in get_file_list((hr_folder / "**" / "*"))}
    l = {f.relative_to(lr_folder).with_suffix("")
         for f in get_file_list((lr_folder / "**" / "*"))}
    return h, l


def to_recursive(path: Path, recursive: bool) -> Path:
    return path if recursive else Path(str(path).replace(os.sep, "_"))


def hrlr_pair(path, hr_folder, lr_folder, recursive=False, ext=None):
    hr_path = hr_folder / to_recursive(path, recursive)
    lr_path = lr_folder / to_recursive(path, recursive)
    hr_path.parent.mkdir(parents=True, exist_ok=True)
    lr_path.parent.mkdir(parents=True, exist_ok=True)
    if ext:
        hr_path = hr_path.with_suffix(f".{ext}")
        lr_path = lr_path.with_suffix(f".{ext}")
    return hr_path, lr_path


def within_time(inpath, before_time, after_time) -> tuple:
    mtime = inpath.stat().st_mtime
    filetime = datetime.datetime.fromtimestamp(mtime)
    if before_time and (before_time < filetime) \
            or after_time and (after_time > filetime):
        return (False, mtime)
    return (True, mtime)


def within_res(inpath, minsize, maxsize, scale, crop_mod) -> tuple:
    res = imagesize.get(inpath)
    width, height = res
    if crop_mod:
        width, height = (width//scale)*scale, (height//scale)*scale
    elif (width % scale != 0 or height % scale != 0) \
            or (minsize and (width < minsize or height < minsize)) \
            or (maxsize and (width > maxsize or height > maxsize)):
        return (False, res)
    return (True, (width, height))


def fileparse(inpath, source, mtime, scale,
              hr_folder, lr_folder, recursive, crop_mod, ext=None):

    hr_path, lr_path = hrlr_pair(inpath, hr_folder, lr_folder, recursive, ext)
    image = cv2.imread(source)  # type: ignore
    width, height, _ = image.shape

    if crop_mod and (width % scale != 0 or height % scale != 0):
        image = image[0:(width//scale)*scale, 0:(height//scale)*scale]
    cv2.imwrite(str(hr_path), image)  # type: ignore
    cv2.imwrite(str(lr_path), cv2.resize(  # type: ignore
        image, (0, 0), fx=1 / scale, fy=1 / scale))

    os.utime(str(hr_path), (mtime, mtime))
    os.utime(str(lr_path), (mtime, mtime))
    return inpath


if __name__ == "__main__":

    parser = main_parser()

    cparser = ConfigParser(parser, "config.json", exit_on_change=True)
    args = cparser.parse_args()

    if not args.input:
        sys.exit("Please specify an input directory.")

    next_step(0,
              f"(input: {args.input})",
              f"(scale: {args.scale})",
              f"(threads: {args.threads})",
              f"(recursive: {args.recursive})",
              f"(extension: {args.extension})",
              f"(anonymous: {args.anonymous})",
              f"(sort: {args.sort}) (reverse: {args.reverse})\n")

    before_time, after_time = None, None
    if args.after or args.before:
        try:
            if args.after:
                after_time = timeparser.parse(str(args.after))
            if args.before:
                before_time = timeparser.parse(str(args.before))
            if args.after and args.before and args.after > args.before:
                raise timeparser.ParserError(
                    f"{before_time} (--before) is older than {after_time} (--after)!")
        except timeparser.ParserError as err:
            next_step(-9, err)

    next_step(1, "Gathering images...")
    args.input = Path(args.input).resolve()
    image_list = get_file_list(args.input / "**" / "*.png",
                               args.input / "**" / "*.jpg",
                               args.input / "**" / "*.webp")

    if args.image_limit and args.limit_mode == "before":  # limit image number
        image_list = image_list[:args.image_limit]

    next_step(1, f"(images: {len(image_list)})")
    # filter out blackisted/whitelisted items
    for f, j in [("whitelist", True), ("blacklist", False)]:
        if i := getattr(args, f):
            i = i.split(" ") if args.list_filter_mode == "list" else [i]
            # iterate through each given whitelist item
            for v, l in enumerate(i):

                image_list = [i for i in image_list if (l in str(i)) == j]
                next_step(1, f"{f} {v}: ({l}): {len(image_list)}")

    next_step(1, "Resolving...")
    original_total = len(image_list)
    # vv This naturally removes the possibility of multiple files pointing to the same image
    image_list = {i.resolve(): i.relative_to(args.input)
                  for i in image_list}.values()

    if len(image_list) is not original_total:
        next_step(1, f"Discarded {original_total - len(image_list)} links")

    if args.extension and args.extension.startswith("."):
        args.extension = args.extension[1:]

    hr_folder = args.input.parent / f"{str(args.scale)}xHR"
    lr_folder = args.input.parent / f"{str(args.scale)}xLR"
    if ext := args.extension:
        hr_folder = Path(f"{str(hr_folder)}-{ext}")
        lr_folder = Path(f"{str(lr_folder)}-{ext}")
    hr_folder.parent.mkdir(parents=True, exist_ok=True)
    lr_folder.parent.mkdir(parents=True, exist_ok=True)

    # Gather a list of exi sting images and remove them
    if args.purge:
        next_step(1, "Purging...")
        for path in image_list:
            hr_path, lr_path = hrlr_pair(
                path, hr_folder, lr_folder, args.recursive, args.extension)
            if hr_path.exists():
                hr_path.unlink()
            if lr_path.exists():
                lr_path.unlink()
        next_step(1, "Purged.")
    # get files that were already converted
    next_step(1, "removing existing...")

    h, l = get_existing_files(hr_folder, lr_folder)
    exist_list = h.intersection(l)

    image_list = [i for i in image_list
                  if to_recursive(i, args.recursive).with_suffix("") not in exist_list]

    next_step(1, f"Discarded: {original_total-len(image_list)} images")
    print()
    if not image_list:
        next_step(-1, "No images left to process")
        sys.exit(-1)

    next_step(2, "Filtering images outside of range: "
              f"({after_time}<=x<={before_time})")
    original_total = len(image_list)
    mtimes = poolmap(args.threads, within_time, [
        (args.input / i, before_time, after_time) for i in image_list],
        chunksize=10, use_tqdm=True)
    image_list = [image_list[i]
                  for i in range(len(image_list)) if mtimes[i][0]]
    # filter based on v, and make dictionary for sorting
    mtimes = {image_list[i]: m for i, (v, m) in enumerate(mtimes) if v}

    next_step(
        2, "Filtering images by resolution: "
        f"({args.minsize} <= x <= {args.maxsize}) % {args.scale}")
    if args.crop_mod:
        next_step(
            -1, "cropping mode on!")
    elif not cparser.file.get("cropped_before", False):
        next_step(-1, "Try the cropping mode! It crops the image instead of outright ignoring it.")
        cparser.file.update({"cropped_before": True})
        cparser.file.save()
    pargs = [(args.input / i, args.minsize, args.maxsize,
              args.scale, args.crop_mod) for i in image_list]
    mres = poolmap(args.threads, within_res, pargs, use_tqdm=True)
    # magic
    image_list = [image_list[i]
                  for i, _ in enumerate(image_list) if mres[i][0]]
    mres = [m for v, m in mres if v]
    mres = {image_list[i]: v for i, v in enumerate(mres)}

    next_step(2, f"Discarded {original_total - len(image_list)} images")

    if args.simulate:
        next_step(3, "Simulated")
        sys.exit(-1)
    elif not image_list:
        next_step(-1, "No images left to process")
        sys.exit(-1)

    next_step(3, "Sorting...")
    # Sort files based on different attributes
    sorting_methods = {"name": lambda x: x,
                       "ext": lambda x: x.suffix,
                       "len": lambda x: len(str(x)),
                       "res": lambda x: mres[x][0] * mres[x][1],
                       "time": lambda x: mtimes[x],
                       "size": lambda x: (args.input / x).stat().st_size}
    image_list = sorted(
        image_list,
        key=sorting_methods[args.sort], reverse=args.reverse)

    if args.image_limit and args.limit_mode == "after":
        image_list = set(image_list[: args.image_limit])

    next_step(3, f"Processing {len(image_list)} images...")
    try:
        pargs = [(v, str(args.input / v),
                  mtimes[v], args.scale,
                  hr_folder, lr_folder,
                  args.recursive, args.crop_mod, args.extension)
                 for v in image_list]
        image_list = poolmap(args.threads, fileparse, pargs,
                             chunksize=2,
                             just=max([len(str(x)) for x in image_list]),
                             postfix=not args.anonymous,
                             use_tqdm=True)
    except KeyboardInterrupt:
        next_step(-1, "KeyboardInterrupt")
    next_step(-1, "Done")
    sys.exit()
