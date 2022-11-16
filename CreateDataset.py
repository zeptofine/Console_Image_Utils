"""
    Conversion script from folder to hr/lr pair
    @author xpsyc
    @version 11-15-22-0
"""
import argparse
import datetime
import glob
import multiprocessing
import os
import shutil
import sys
import time
from multiprocessing import Pool
from pathlib import Path
# from pprint import pprint
from random import shuffle

from misc_utils import ConfigParser, next_step, p_bar, thread_status

try:
    from rich import print as rprint
    from rich.traceback import install
    install()
except ImportError:
    rprint = print

try:
    import cv2
    import dateutil.parser as timeparser
    import imagesize
    from dateutil.parser import ParserError
    from PIL import Image
except ImportError as err:
    print("Please run: 'pip install opencv-python python-dateutil imagesize pillow rich-argparse")
    print(err)
    sys.exit(1)

if sys.platform == "win32":
    print("This application was not made for windows and its compatibility is not guaranteed.")
    time.sleep(3)

CPU_COUNT: int = os.cpu_count()  # type: ignore

PARSER_TEXT = """Hi! this script converts thousands of files to
another format in a High-res/Low-res pair."""
try:
    import rich_argparse
    parser = argparse.ArgumentParser(
        formatter_class=rich_argparse.ArgumentDefaultsRichHelpFormatter,
        description=PARSER_TEXT)
except ImportError:
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        description=PARSER_TEXT)

p_req = parser.add_argument_group("Runtime options")
p_req.add_argument("-i", "--input",
                   help="Input folder.")
p_req.add_argument("-x", "--scale", type=int, default=4,
                   help="scale to downscale LR images")

p_req.add_argument("-e", "--extension", metavar="EXT", default=None,
                   help="export extension.")
p_req.add_argument("-r", "--recursive", action="store_true", default=False,
                   help="preserves the tree hierarchy.")

p_mods = parser.add_argument_group("Modifiers")
p_mods.add_argument("-p", "--power", type=int, default=int((CPU_COUNT/4)*3),
                    help="number of cores to use.")
p_mods.add_argument("--image_limit", type=int, default=None, metavar="MAX",
                    help="only gathers a given number of images. None if disabled.")
p_mods.add_argument("--anonymous", action="store_true",
                    help="hides path names in progress. Doesn't affect the result.")
p_mods.add_argument("--simulate", action="store_true",
                    help="skips the conversion step.")
p_mods.add_argument("--purge", action="store_true",
                    help="Clears every output before converting.")

p_filters = parser.add_argument_group("Filters")
p_filters.add_argument("--whitelist", type=str, metavar="INCLUDE",
                       help="only allows paths with the given string.")
p_filters.add_argument("--blacklist", type=str, metavar="EXCLUDE",
                       help="strips paths with the given string.")

p_sort = parser.add_argument_group("Sorting")
p_sort.add_argument("--sort", choices=["full", "name", "ext", "len"], default="name",
                    help="sorting method.")
p_sort.add_argument("--reverse", action="store_true",
                    help="reverses the sorting direction.")

p_thresh = parser.add_argument_group("Thresholds")
p_thresh.add_argument("--minsize", type=int, metavar="MIN",
                      help="smallest available image")
p_thresh.add_argument("--maxsize", type=int, metavar="MAX",
                      help="largest allowed image.")
p_thresh.add_argument("--after", type=str,
                      help="Only uses files modified after a given date."
                      + "ex. '2020', or '2009 sept 16th'")
p_thresh.add_argument("--before", type=str,
                      help="Only uses before a given date. ex. 'Wed Jun 9 04:26:40', or 'Jun 9'")


cparser = ConfigParser(parser, "config.json", exit_on_change=True)
args = cparser.parse_args()


beforeTime, afterTime = None, None
if args.after or args.before:
    try:
        if args.after:
            args.after = str(args.after)
            afterTime = timeparser.parse(args.after, fuzzy=True)
        if args.before:
            args.before = str(args.before)
            beforeTime = timeparser.parse(args.before, fuzzy=True)
        if args.after and args.before:
            if args.after < args.before:
                sys.exit(f"{beforeTime} is older than {afterTime}!")
    except ParserError as err:
        rprint("Given time is invalid!")
        sys.exit(str(err))


def getpid() -> int:
    return int(multiprocessing.current_process().name.rsplit("-", 1)[-1])


def get_file_list(*paths) -> list[Path]:
    globlist = [glob.glob(str(p), recursive=True)
                for p in paths]  # get list of lists of paths
    return [Path(y) for x in globlist for y in x]


def q_res(file) -> tuple:
    try:
        return imagesize.get(file)
    except ValueError:
        return Image.open(file).size


def to_recursive(path) -> Path:
    return Path(str(path).replace(os.sep, "_"))


def filter_imgs(inumerated) -> tuple[Path, os.stat_result] | None:
    index, ptotal, inpath = inumerated
    thread_status(getpid(), inpath, anonymous=args.anonymous,
                  extra=f"{index}/{ptotal} {p_bar(index, ptotal, 20)}")
    filestat = (args.input / inpath).stat()
    if beforeTime or afterTime:
        filetime = datetime.datetime.fromtimestamp(filestat.st_mtime)
        if beforeTime and (filetime > beforeTime):
            return
        if afterTime and (filetime < afterTime):
            return
    width, height = q_res(str(args.input / inpath))
    if args.minsize and ((width < args.minsize) or (height < args.minsize)):
        return
    if args.maxsize and ((width > args.maxsize) or (height > args.maxsize)):
        return
    if (width % args.scale != 0) or (height % args.scale != 0):
        return
    return (inpath, filestat)


def fileparse(inumerated) -> None:
    index, ptotal, inpath, filestat, hr_folder, lr_folder = inumerated
    filestime = filestat.st_mtime
    pid = getpid() - args.power

    if args.recursive:
        hr_path = Path(hr_folder / inpath)
        lr_path = Path(lr_folder / inpath)
    else:
        hr_path = Path(hr_folder / to_recursive(inpath))
        lr_path = Path(lr_folder / to_recursive(inpath))
    os.makedirs(hr_path.parent, exist_ok=True)
    os.makedirs(lr_path.parent, exist_ok=True)

    if args.extension not in [None, 'None']:
        hr_path = hr_path.with_suffix("."+args.extension)
        lr_path = lr_path.with_suffix("."+args.extension)

    image = cv2.imread(str(args.input / inpath))
    thread_status(pid, inpath, anonymous=args.anonymous,
                  extra=f"{index}/{ptotal} {p_bar(index, ptotal, 14)}{p_bar(1, 2, 4)}")
    cv2.imwrite(str(hr_path), image)  # type: ignore
    thread_status(pid, inpath, anonymous=args.anonymous,
                  extra=f"{index}/{ptotal} {p_bar(index, ptotal, 14)}{p_bar(2, 2, 4)}")
    cv2.imwrite(str(lr_path), cv2.resize(  # type: ignore
        image, (0, 0), fx=1/args.scale, fy=1/args.scale))
    os.utime(str(hr_path), (filestime, filestime))
    os.utime(str(lr_path), (filestime, filestime))


def main():
    if not args.input:
        sys.exit("Please specify an input directory.")

    next_step(0, f"(Input: {args.input}) (Recursive: {args.recursive})")
    next_step(0, f"(Scale: {args.scale}) (Threads: {args.power})")
    next_step(0, f"(Extension: {args.extension})")
    next_step(0, f"(anonymous: {args.anonymous})")
    next_step(0, f"Size threshold: ({args.minsize} <= x <= {args.maxsize})")
    next_step(0, f"Time threshold: ({afterTime} <= x <= {beforeTime})")
    next_step(0, f"(sort: {args.sort}) (reverse: {args.reverse})")
    print()

    args.input = Path(args.input)
    image_list = get_file_list(args.input / "**" / "*.png",
                               args.input / "**" / "*.jpg",
                               args.input / "**" / "*.webp")
    if args.image_limit is not None:
        image_list = image_list[:args.image_limit]

    next_step(1, f"images: {len(image_list)}")

    # filter out blackisted/whitelisted items
    if args.whitelist:
        next_step(1, f"(whitelist: {args.whitelist})")
        image_list = [i for i in image_list if args.whitelist in str(i)]
    if args.blacklist:
        next_step(1, f"(blacklist: {args.blacklist})")
        image_list = [i for i in image_list if args.blacklist not in str(i)]

    image_list = [i.relative_to(args.input) for i in image_list]
    if (args.extension) and (args.extension.startswith(".")):
        args.extension = args.extension[1:]

    hr_folder = args.input.parent / (str(args.scale)+"xHR")
    lr_folder = args.input.parent / (str(args.scale)+"xLR")
    if args.extension:
        hr_folder = Path(str(hr_folder) + f"-{args.extension}")
        lr_folder = Path(str(lr_folder) + f"-{args.extension}")
    os.makedirs(hr_folder, exist_ok=True)
    os.makedirs(lr_folder, exist_ok=True)

    if args.purge:
        next_step(1, f"purge: {args.purge}")
        for i in get_file_list(str(hr_folder / "**" / "*"),
                               str(lr_folder / "**" / "*")):
            if i.is_dir():
                shutil.rmtree(i)
            elif i.is_file():
                os.remove(i)
        next_step(1, "Purged.")

    # get files that were already converted
    next_step(1, "Filtering files ...")
    hr_files = set([f.relative_to(hr_folder).with_suffix("") for f in get_file_list(
        str((hr_folder / "**" / "*"))) if not f.is_dir()])
    lr_files = set([f.relative_to(lr_folder).with_suffix("") for f in get_file_list(
        str((lr_folder / "**" / "*"))) if not f.is_dir()])
    exist_list = set([i for i in hr_files if i in lr_files])
    unfiltered_len = len(image_list)
    image_list = [i for i in image_list
                  if i.with_suffix("") not in exist_list]
    image_list = [i for i in image_list
                  if to_recursive(i).with_suffix("") not in exist_list]
    next_step(1,
              f"(existing: {len(exist_list)}) (discarded: {unfiltered_len-len(image_list)})")
    next_step(1, f"images: {len(image_list)}")

    # Sort files based on different attributes
    if args.sort:
        next_step(1, f"Sorting...")
        sorting_methods = {
            "name": lambda x: x.stem,
            "ext": lambda x: x.suffix,
            "len": lambda x: len(str(x)),
            "full": lambda x: x
        }
        image_list = sorted(image_list, key=sorting_methods[args.sort])
    if args.reverse:
        image_list = image_list[::-1]
    print()

    # Remove files that hit the arg limits
    next_step(2, "Filtering bad images ...")
    with Pool(args.power) as p:
        intuple = [(i[0], len(image_list), i[1])
                   for i in enumerate(image_list)]
        imgs_filtered = list(p.map(filter_imgs, intuple))
    imgs_filtered = [i for i in imgs_filtered if i is not None]
    next_step(2, f"discarded {len(intuple)-len(imgs_filtered)} images")
    print()

    # exit if args.simulate
    if args.simulate:
        next_step(3, "Simulate == True")
        return

    # Process images
    if len(imgs_filtered) == 0:
        rprint("No images left to process")
        sys.exit(0)
    next_step(3, f"processing: {len(imgs_filtered)} images...")
    with Pool(args.power) as p:
        intuple = [(i[0], len(imgs_filtered))+i[1]
                   for i in enumerate(imgs_filtered)]
        intuple = [i+(hr_folder, lr_folder) for i in intuple]
        p.map(fileparse, intuple)


if __name__ == "__main__":
    main()
