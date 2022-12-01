"""Conversion script from folder to hr/lr pair.

@author xpsyc
@version 11-15-22-0
"""


import argparse
import datetime
import glob
import importlib
import importlib
import multiprocessing
import os
import shutil
import subprocess
import sys
import time
from multiprocessing import Pool
from pathlib import Path

from special.misc_utils import next_step, p_bar, thread_status
from special.ConfigParser import ConfigParser

CPU_COUNT: int = os.cpu_count()  # type: ignore

if sys.platform == "win32":
    print("This application was not made for windows. Try Using WSL2 (untested)")
    time.sleep(3)

try:
    from rich_argparse import ArgumentDefaultsRichHelpFormatter
except (ModuleNotFoundError, ImportError):
    ArgumentDefaultsRichHelpFormatter = argparse.ArgumentDefaultsHelpFormatter

parser = argparse.ArgumentParser(
    formatter_class=ArgumentDefaultsRichHelpFormatter,
    description="""Hi! this script converts thousands of files to
another format in a High-res/Low-res pair.""")
parser.add_argument("--parse_error", action="store_true",
                    help=argparse.SUPPRESS)
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
p_mods.add_argument("--threads", type=int, default=int((CPU_COUNT / 4) * 3),
                    help="number of total threads.")
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
p_sort.add_argument("--sort", choices=["name", "ext", "len", "full"], default="full",
                    help="sorting method.")
p_sort.add_argument("--reverse", action="store_true",
                    help="reverses the sorting direction.")

p_thresh = parser.add_argument_group("Thresholds")
p_thresh.add_argument("--no_mod", action="store_true",
                      help="disables the modulo check for if the file is divisible by scale. May encounter errors later on.")
p_thresh.add_argument("--minsize", type=int, metavar="MIN",
                      help="smallest available image")
p_thresh.add_argument("--maxsize", type=int, metavar="MAX",
                      help="largest allowed image.")
p_thresh.add_argument("--after", type=str,
                      help="Only uses files modified after a given date."
                      "ex. '2020', or '2009 sept 16th'")
p_thresh.add_argument("--before", type=str,
                      help="Only uses before a given date. ex. 'Wed Jun 9 04:26:40', or 'Jun 9'")
cparser = ConfigParser(parser, "config.json", exit_on_change=True)
args = cparser.parse_args()


def try_import(package) -> int | str:
    try:
        spec = importlib.util.find_spec(package)
        if spec is not None:
            module = importlib.util.module_from_spec(spec)
            sys.modules[module] = package
            importlib.import_module(package)
            return spec
        else:
            return None
    except ModuleNotFoundError:
        return None


packages = {
    'rich':            "rich",
    'opencv-python':   "cv2",
    'python-dateutil': "dateutil",
    'imagesize':       "imagesize",
    'pillow':          "PIL",
    'rich-argparse':   "rich_argparse",
}

try:
    import dateutil.parser
    import cv2
    from imagesize import get as imagesize_get
    from rich_argparse import ArgumentDefaultsRichHelpFormatter
    from PIL import Image

    from rich import print as rprint
    from rich.traceback import install
    install()

except (ImportError, ModuleNotFoundError):
    try:
        import_failed = False
        for package in packages.keys():
            if try_import(packages[package]) is None:
                import_failed = True
                print("-"*os.get_terminal_size().columns +
                      f"\n{package} not detected. Attempting to install...\n")
                with subprocess.Popen([sys.executable, '-m', 'pip', 'install', package],
                                      stdout=subprocess.PIPE, stderr=subprocess.PIPE) as importproc:
                    while importproc.poll() is None:
                        if importproc.stdout is not None:
                            importproc_string = importproc.stdout.readline().decode('UTF-8').strip()
                            if importproc_string != "":
                                print(f'({package}) : {importproc_string}')
                        time.sleep(0.05)
                print()
                if try_import(packages[package]) is None:
                    raise ModuleNotFoundError(f"Failed to install '{package}'.")
        if import_failed and not args.parse_error:
            os.execv(sys.executable, ['python'] + sys.argv + ['--parse_error'])
        elif args.parse_error:
            raise ModuleNotFoundError(
                f'Packages not found after relaunching. Please properly install {"".join(packages.keys())}')
    except (subprocess.SubprocessError, ModuleNotFoundError) as err2:
        print(f"{type(err2).__name__}: {err2}")
        sys.exit(127)  # command not found


timeparser = dateutil.parser


before_time, after_time = None, None
if args.after or args.before:
    try:
        if args.after:
            args.after = str(args.after)
            after_time = timeparser.parse(args.after, fuzzy=True)
        if args.before:
            args.before = str(args.before)
            before_time = timeparser.parse(args.before, fuzzy=True)
        if args.after and args.before:
            if args.after < args.before:
                sys.exit(f"{before_time} is older than {after_time}!")
    except timeparser.ParserError as err:
        rprint("Given time is invalid!")
        sys.exit(str(err))


def getpid() -> int:
    return int(multiprocessing.current_process().name.rsplit("-", 1)[-1])


def intersect_lists(x: list | tuple, y: list | tuple) -> list:
    outlist = []
    for i in x:
        if i in y:
            outlist.append(i)
            y.remove(i)
    return outlist


def get_file_list(*paths) -> list[Path]:
    globlist = [glob.glob(str(p), recursive=True)
                for p in paths]  # get list of lists of paths
    return [Path(y) for x in globlist for y in x]


def q_res(file) -> tuple:
    try:
        return imagesize_get(file)
    except ValueError:
        return Image.open(file).size


def to_recursive(path) -> Path:
    return Path(str(path).replace(os.sep, "_"))


def filter_imgs(inumerated) -> tuple[Path, os.stat_result] | None:
    index, ptotal, inpath = inumerated
    thread_status(getpid(), inpath, anonymous=args.anonymous,
                  extra=f"{index}/{ptotal} {p_bar(index, ptotal, 10)}")
    filestat = (args.input / inpath).stat()
    if before_time or after_time:
        filetime = datetime.datetime.fromtimestamp(filestat.st_mtime)
        if before_time and (filetime > before_time):
            return
        if after_time and (filetime < after_time):
            return
    width, height = q_res(str(args.input / inpath))
    if args.minsize and ((width < args.minsize) or (height < args.minsize)):
        return
    if args.maxsize and ((width > args.maxsize) or (height > args.maxsize)):
        return
    if not args.no_mod:
        if (width % args.scale != 0 or height % args.scale != 0):
            return

    return (inpath, filestat)


def fileparse(inumerated) -> None:
    index, ptotal, inpath, filestat, hr_folder, lr_folder = inumerated
    filestime = filestat.st_mtime
    pid = getpid() - args.threads

    if args.recursive:
        hr_path = Path(hr_folder / inpath)
        lr_path = Path(lr_folder / inpath)
    else:
        hr_path = Path(hr_folder / to_recursive(inpath))
        lr_path = Path(lr_folder / to_recursive(inpath))
    os.makedirs(hr_path.parent, exist_ok=True)
    os.makedirs(lr_path.parent, exist_ok=True)

    if args.extension not in [None, 'None']:
        hr_path = hr_path.with_suffix("." + args.extension)
        lr_path = lr_path.with_suffix("." + args.extension)

    image = cv2.imread(str(args.input / inpath))
    thread_status(pid, inpath, anonymous=args.anonymous,
                  extra=f"{index}/{ptotal} {p_bar(index, ptotal, 6)}{p_bar(1, 2, 2)}")
    cv2.imwrite(str(hr_path), image)  # type: ignore
    thread_status(pid, inpath, anonymous=args.anonymous,
                  extra=f"{index}/{ptotal} {p_bar(index, ptotal, 6)}{p_bar(2, 2, 2)}")
    cv2.imwrite(str(lr_path), cv2.resize(  # type: ignore
        image, (0, 0), fx=1 / args.scale, fy=1 / args.scale))
    os.utime(str(hr_path), (filestime, filestime))
    os.utime(str(lr_path), (filestime, filestime))


def main() -> None:
    if not args.input:
        sys.exit("Please specify an input directory.")

    next_step(0, f"(input: {args.input})")
    next_step(0, f"(scale: {args.scale})"
              f" (threads: {args.threads})"
              f" (recursive: {args.recursive})")
    next_step(0, f"(extension: {args.extension})"
              f" (anonymous: {args.anonymous})")
    next_step(0, f"Size threshold: ({args.minsize} <= x <= {args.maxsize})")
    next_step(0, f"Time threshold: ({after_time} <= x <= {before_time})")
    next_step(0, f"(sort: {args.sort}) (reverse: {args.reverse})")
    print()

    next_step(1, "gathering images")
    args.input = Path(args.input)
    image_list = get_file_list(args.input / "**" / "*.png",
                               args.input / "**" / "*.jpg",
                               args.input / "**" / "*.webp")
    if args.image_limit is not None:
        image_list = image_list[:args.image_limit]

    next_step(1, f"images: {len(image_list)}")

    # filter out blackisted/whitelisted items
    if args.whitelist:
        image_list = [i for i in image_list if args.whitelist in str(i)]
        next_step(1, f"(whitelist: {args.whitelist}): {len(image_list)}")
    if args.blacklist:
        image_list = [i for i in image_list if args.blacklist not in str(i)]
        next_step(1, f"(blacklist: {args.blacklist}): {len(image_list)}")

    image_list = [i.relative_to(args.input) for i in image_list]
    if (args.extension) and (args.extension.startswith(".")):
        args.extension = args.extension[1:]

    hr_folder = args.input.parent / (str(args.scale) + "xHR")
    lr_folder = args.input.parent / (str(args.scale) + "xLR")
    if args.extension:
        hr_folder = Path(str(hr_folder) + f"-{args.extension}")
        lr_folder = Path(str(lr_folder) + f"-{args.extension}")
    os.makedirs(hr_folder, exist_ok=True)
    os.makedirs(lr_folder, exist_ok=True)

    if args.purge:
        next_step(1, "purging...")
        for i in get_file_list(str(hr_folder / "**" / "*"),
                               str(lr_folder / "**" / "*")):
            if i.is_dir():
                shutil.rmtree(i)
            elif i.is_file():
                os.remove(i)
        next_step(1, "purged.")

    # get files that were already converted
    next_step(1, "filtering existing ...")
    hr_files = set([f.relative_to(hr_folder).with_suffix("") for f in get_file_list(
        str((hr_folder / "**" / "*"))) if not f.is_dir()])
    lr_files = set([f.relative_to(lr_folder).with_suffix("") for f in get_file_list(
        str((lr_folder / "**" / "*"))) if not f.is_dir()])
    exist_list = set(intersect_lists(hr_files, lr_files))
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
        next_step(1, "Sorting...")
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
    with Pool(args.threads) as p:
        intuple = [(i[0], len(image_list), i[1])
                   for i in enumerate(image_list)]
        imgs_filtered = list(p.map(filter_imgs, intuple, chunksize=256))
    imgs_filtered = [i for i in imgs_filtered if i is not None]
    next_step(2, f"discarded {len(intuple)-len(imgs_filtered)} images")
    print()

    # exit if args.simulate
    if args.simulate:
        next_step(3, "Simulate == True")
        return

    # Process images
    if len(imgs_filtered) == 0:
        next_step(-1, "No images left to process")
        sys.exit(-1)
    next_step(3, f"processing: {len(imgs_filtered)} images...")
    with Pool(args.threads) as p:
        intuple = [(i[0], len(imgs_filtered)) + i[1]
                   for i in enumerate(imgs_filtered)]
        intuple = [i + (hr_folder, lr_folder) for i in intuple]
        p.map(fileparse, intuple, chunksize=256)


if __name__ == "__main__":
    main()
