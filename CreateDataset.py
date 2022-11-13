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
from pprint import pprint

from misc_utils import configParser, nextStep, numFmt, pBar, thread_status

try:
    from rich import print as rprint
    from rich.traceback import install
    install(show_locals=False)
except ImportError:
    rprint = print

try:
    import cv2
    import dateutil.parser as timeparser
    import imagesize
    from dateutil.parser import ParserError
    from PIL import Image
except ImportError:
    print("Please run: 'pip install opencv-python python-dateutil imagesize pillow")
    sys.exit(1)

if sys.platform == "win32":
    print("This application was not made for windows and its compatibility is not guaranteed.")
    time.sleep(3)

try:
    CPU_COUNT: int = os.cpu_count()  # type: ignore
except:
    CPU_COUNT = 4


try:
    import rich_argparse
    parser = argparse.ArgumentParser(
        formatter_class=rich_argparse.RichHelpFormatter)
except:
    parser = argparse.ArgumentParser()
parser.add_argument("-i", "--input",
                    help="Input folder.")
parser.add_argument("-x", "--scale", type=int, default=4)
parser.add_argument("-e", "--extension", metavar="EXT", default="webp",
                    help="export extension.")
parser.add_argument("-r", "--recursive", action="store_true", default=False,
                    help="preserves the tree hierarchy.")
parser.add_argument("--power", type=int, default=int((CPU_COUNT/4)*3),
                    help="number of cores to use.")
parser.add_argument("--anonymous", action="store_true",
                    help="hides path names in progress. Doesn't affect the result.")
parser.add_argument("--simulate", action="store_true",
                    help="skips the conversion step.")
parser.add_argument("--purge", action="store_true",
                    help="Clears every output before converting.")
parser.add_argument("--sort", choices=["path", "basename", "extension"],
                    help="sorting method.")


p_size = parser.add_argument_group("Resolution thresholds")
p_size.add_argument("--minsize", type=int,
                    help="smallest available image")
p_size.add_argument("--maxsize", type=int,
                    help="largest allowed image.")


p_time = parser.add_argument_group("Time thresholds")
p_time.add_argument("--after",
                    help="Only uses files modified after a given date.  ex. '2020', or '2009 sept 16th'")
p_time.add_argument("--before",
                    help="Only uses before a given date.               ex. 'Wed Jun 9 04:26:40 2018', or 'Jun 9'")


cparser = configParser(parser, "config.json", exit_on_change=True)
args = cparser.parse_args()


beforeTime, afterTime = None, None
if args.after or args.before:
    try:
        if args.after:
            args.after = str(args.after)
            afterTime = timeparser.parse(args.after,
                                         fuzzy=True)
        if args.before:
            args.before = str(args.before)
            beforeTime = timeparser.parse(args.before,
                                          fuzzy=True)
    except ParserError as pe:
        rprint("Given time is invalid!")
        sys.exit(str(pe))
    if args.after and args.before:
        if (args.after < args.before):
            sys.exit(f"{beforeTime} is older than {afterTime}!")


def getpid() -> int:
    pid = multiprocessing.current_process()
    return int(pid.name.rsplit("-", 1)[-1])


def get_file_list(*args) -> list[Path]:
    globlist = [glob.glob(str(p), recursive=True)
                for p in args]  # get list of lists of paths
    return [Path(y) for x in globlist for y in x]  # combine them into a list


def quickResolution(file) -> tuple:
    try:
        return imagesize.get(file)
    except:
        return Image.open(file).size


def to_recursive(path) -> Path:
    return Path(str(path).replace(os.sep, "_"))


def filterImages(inumerated) -> tuple[Path, os.stat_result] | None:
    index, ptotal, inpath = inumerated
    thread_status(getpid(), inpath.name, anonymous=args.anonymous,
                  extra=f"{pBar(index, ptotal, 20)} {index}/{ptotal}")
    filestat = (args.input / inpath).stat()
    if beforeTime or afterTime:
        filetime = datetime.datetime.fromtimestamp(filestat.st_mtime)
        if (beforeTime) and (filetime > beforeTime):
            return
        if (afterTime) and (filetime < afterTime):
            return
    width, height = quickResolution(str(args.input / inpath))
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
    if args.extension:
        hr_path = hr_path.with_suffix("."+args.extension)
        lr_path = lr_path.with_suffix("."+args.extension)

    image = cv2.imread(str(args.input / inpath))  # type: ignore
    thread_status(pid, inpath, anonymous=args.anonymous,
                  extra=f"{pBar(1, 2, 2)} {index}/{ptotal}")
    cv2.imwrite(str(hr_path), image)  # type: ignore
    thread_status(pid, inpath, anonymous=args.anonymous,
                  extra=f"{pBar(2, 2, 2)} {index}/{ptotal}")
    cv2.imwrite(str(lr_path), cv2.resize(  # type: ignore
        image, (0, 0), fx=1/args.scale, fy=1/args.scale))
    os.utime(str(hr_path), (filestime, filestime))
    os.utime(str(lr_path), (filestime, filestime))


def main():
    if not (args.input):
        sys.exit("Please specify an input directory.")
    nextStep(0, f"Input: {args.input}")
    nextStep(0, f"Threads: {args.power}")
    nextStep(0, "Gathering paths ...")
    args.input = Path(args.input)
    image_list = get_file_list(args.input/"**"/"*.png",
                               args.input/"**"/"*.jpg",
                               args.input/"**"/"*.webp")

    nextStep(0, f"Getting relative paths...")
    image_list = [i.relative_to(args.input) for i in image_list]

    if (args.extension) and (args.extension.startswith(".")):
        args.extension = args.extension[1:]

    hr_folder = args.input.parent / (str(args.scale)+"xHR")
    lr_folder = args.input.parent / (str(args.scale)+"xLR")
    if args.extension:
        hr_folder = Path(str(hr_folder)+f"-{args.extension}")
        lr_folder = Path(str(lr_folder)+f"-{args.extension}")
    os.makedirs(hr_folder, exist_ok=True)
    os.makedirs(lr_folder, exist_ok=True)

    if args.purge:
        nextStep(0, "Purging output ...")
        for i in get_file_list(str(hr_folder/"**"/"*"),
                               str(lr_folder/"**"/"*")):
            if i.is_dir():
                shutil.rmtree(i)
            elif i.is_file():
                os.remove(i)
        nextStep(0, "Purged.")

    hr_files = [f.stem for f in get_file_list(str((hr_folder / "*")))]
    lr_files = [f.stem for f in get_file_list(str((lr_folder / "*")))]
    existList = [i for i in hr_files if i in lr_files]

    nextStep(0, f"(source, existed): ({len(image_list)}, {len(existList)})")
    nextStep(0, f"Filtering out existing files...")
    image_list = [i for i in image_list
                  if i.stem not in existList]
    image_list = [i for i in image_list
                  if to_recursive(i).stem not in existList]

    nextStep(0, f"Sorting...")
    if args.sort == "basename":
        image_list = sorted(image_list, key=lambda x: x.stem, reverse=True)
    elif args.sort == "extension":
        image_list = sorted(image_list, key=lambda x: x.suffix)
    else:
        image_list = sorted(image_list)

    nextStep(0, f"Files: {len(image_list)}")
    nextStep(0, f"Scale: {args.scale}")
    nextStep(0, f"Size threshold: ({args.minsize}<=x<={args.maxsize})")
    nextStep(0, f"Time threshold: ({afterTime}<=x<={beforeTime})")

    nextStep(1, "Filtering bad images")
    with Pool(args.power) as pool:
        intuple = [(i[0], len(image_list), i[1])
                   for i in enumerate(image_list)]
        imgs_filtered = list(pool.map(filterImages, intuple))
    imgs_filtered = [i for i in imgs_filtered if i is not None]
    nextStep(1, f"New images: {len(imgs_filtered)}")

    if args.simulate:
        return

    if (len(imgs_filtered) == 0):
        rprint("No images left to process")
        sys.exit(0)
    nextStep(2, "Processing ...")
    with Pool(args.power) as p:
        # add index and total
        intuple = [(i[0], len(imgs_filtered))+i[1]
                   for i in enumerate(imgs_filtered)]
        # append HRFolder and LRFolder
        intuple = [i+(hr_folder, lr_folder) for i in intuple]
        imgs = p.map(fileparse, intuple)


if __name__ == "__main__":
    main()
