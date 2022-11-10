import argparse
import datetime
import glob
import json
import multiprocessing
import os
import shutil
import sys
import time
from multiprocessing import Pool
from pathlib import Path
from pprint import pprint

from misc_utils import nextStep, numFmt, pBar, thread_status, configParser

try:
    from rich import print as rprint
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
    exit(1)

if sys.platform == "win32":
    print("This application was not made for windows and its compatibility is not guaranteed.")
    time.sleep(5)
try:
    CPU_COUNT: int = os.cpu_count()  # type: ignore
except:
    CPU_COUNT = 4

parser = argparse.ArgumentParser()
parser.add_argument("-i", "--input")
parser.add_argument("-x", "--scale", type=int, default=4)
parser.add_argument("-e", "--extension",
                    help="export extension.", default="webp")
parser.add_argument("-r", "--recursive", help="preserves the tree hierarchy.",
                    action="store_true")

parser.add_argument("--minsize", help="smallest available image",
                    type=int)
parser.add_argument("--maxsize", help="largest allowed image.",
                    type=int)

parser.add_argument(
    "--after", help="Only uses files modified after a given date.  ex. '2020', or '2009 sept 16th'")
parser.add_argument(
    "--before", help="Only uses before a given date. ex. 'Wed Jun 9 04:26:40 2018', or 'Jun 9'")

parser.add_argument("--power", help="number of cores to use.",
                    type=int, default=int((CPU_COUNT/4)*3))
parser.add_argument("--anonymous", help="hides path names in progress. Doesn't affect the result.",
                    action="store_true")
parser.add_argument("--simulate", help="skips the conversion step.",
                    action="store_true")
parser.add_argument("--purge", help="Clears every output before converting.",
                    action="store_true")


cparser = configParser(parser, "config.json")
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
    except ParserError as pe:
        rprint("Given time is invalid!")
        sys.exit(str(pe))
    if args.after and args.before:
        if (args.after < args.before):
            sys.exit(f"{beforeTime} is older than {afterTime}!")


def getpid():
    pid = multiprocessing.current_process()
    return int(pid.name.rsplit("-", 1)[-1])


def get_file_list(*args):
    globlist = [glob.glob(str(p), recursive=True)
                for p in args]  # get list of lists of paths
    return [Path(y) for x in globlist for y in x]  # combine them into a list


def quickResolution(file):
    try:
        return imagesize.get(file)
    except:
        return Image.open(file).size


def gatherInfo(inumerated):
    index, ptotal, inpath = inumerated
    thread_status(getpid(), inpath.name, anonymous=args.anonymous,
                  extra=f"{pBar(index, ptotal)} {index}/{ptotal}")
    return (inpath, quickResolution(str(inpath)))


def filterImages(inumerated):
    index, ptotal, inpath, res = inumerated
    thread_status(getpid()-args.power, inpath.name, anonymous=args.anonymous,
                  extra=f"{pBar(index, ptotal)} {index}/{ptotal}")
    filestat = inpath.stat()
    filestime = filestat.st_mtime
    if beforeTime or afterTime:
        filetime = datetime.datetime.fromtimestamp(filestime)
        if (beforeTime) and (filetime > beforeTime):
            return
        if (afterTime) and (filetime < afterTime):
            return
    width, height = res
    if args.minsize and ((width < args.minsize) or (height < args.minsize)):
        return
    if args.maxsize and ((width > args.maxsize) or (height > args.maxsize)):
        return
    if (width % args.scale != 0) or (height % args.scale != 0):
        return
    return (inpath, filestat)


def fileparse(inumerated):
    index, ptotal, inpath, filestat, HRFolder, LRFolder = inumerated
    filestime = filestat.st_mtime
    inpath: Path = inpath
    relPath = Path(inpath.relative_to(args.input))
    if args.recursive:
        HRPath: Path = HRFolder / relPath
        LRPath: Path = LRFolder / relPath
        try:
            if not HRPath.parent.exists():
                os.makedirs(HRPath.parent)
        except OSError:
            pass
        try:
            if not LRPath.parent.exists():
                os.makedirs(LRPath.parent)
        except OSError:
            pass
    else:
        HRPath = HRFolder / inpath.name
        LRPath = LRFolder / inpath.name
    if args.extension:
        HRPath = HRPath.with_suffix("."+args.extension)
        LRPath = LRPath.with_suffix("."+args.extension)
    pid = getpid() - args.power*2
    thread_status(pid, str(relPath), anonymous=args.anonymous,
                  extra=f"{pBar(1, 2, 2)} {index}/{ptotal}")
    image = cv2.imread(str(inpath))  # type: ignore
    cv2.imwrite(str(HRPath), image)  # type: ignore
    thread_status(pid, str(relPath), anonymous=args.anonymous,
                  extra=f"{pBar(2, 2, 2)} {index}/{ptotal}")
    cv2.imwrite(str(LRPath), cv2.resize(  # type: ignore
        image, (0, 0), fx=1/args.scale, fy=1/args.scale))
    os.utime(str(HRPath), (filestime, filestime))
    os.utime(str(LRPath), (filestime, filestime))


def main():

    if not (args.input):
        sys.exit("Please specify an input directory.")
    nextStep(0, f"Input: {args.input}")
    nextStep(0, f"Threads: {args.power}")
    nextStep(0, "Gathering paths ...")
    args.input = Path(args.input)
    imageList = get_file_list(args.input/"**"/"*.png",
                              args.input/"**"/"*.jpg",
                              args.input/"**"/"*.webp")

    if (args.extension) and (args.extension.startswith(".")):
        args.extension = args.extension[1:]

    HRFolder = args.input.parent / (str(args.scale)+"xHR")
    LRFolder = args.input.parent / (str(args.scale)+"xLR")
    if args.extension:
        HRFolder = Path(str(HRFolder)+f"-{args.extension}")
        LRFolder = Path(str(LRFolder)+f"-{args.extension}")
    if not HRFolder.exists():
        os.makedirs(HRFolder)
    if not LRFolder.exists():
        os.makedirs(LRFolder)

    if args.purge:
        nextStep(0, "Purging output ...")
        for i in get_file_list(str(HRFolder/"**/*"),
                               str(LRFolder/"**/*")):
            if i.is_dir():
                shutil.rmtree(i)
            elif i.is_file():
                os.remove(i)
        nextStep(0, "Purged.")

    hr_files = [f.stem for f in get_file_list(str((HRFolder / "*")))]
    lr_files = [f.stem for f in get_file_list(str((LRFolder / "*")))]
    existList = [i for i in hr_files if i in lr_files]
    nextStep(0, f"(source, existed): ({len(imageList)}, {len(existList)})")
    nextStep(0, f"Stripping existing files...")
    imageList = [i for i in imageList if i.stem not in existList]
    nextStep(0, f"new list: {len(imageList)}")
    nextStep(0, f"Scale: {args.scale}")
    nextStep(0, f"Size threshold: ({args.minsize}<=x<={args.maxsize})")
    nextStep(0, f"Time threshold: ({afterTime}<=x<={beforeTime})")

    nextStep(1, "Gathering info")
    with Pool(args.power) as pool:
        # (index, total, data)
        intuple = [(i[0], len(imageList), i[1]) for i in enumerate(imageList)]
        imgTuples = list(pool.map(gatherInfo, intuple))

    nextStep(2, "Filtering bad images")
    with Pool(args.power) as pool:
        intuple = [(i[0], len(imageList))+i[1] for i in enumerate(imgTuples)]
        imgsFiltered = list(pool.map(filterImages, intuple))
    imgsFiltered: list = [i for i in imgsFiltered if i is not None]
    nextStep(2, f"New images: {len(imgsFiltered)}")

    if args.simulate:
        return

    if (len(imgsFiltered) == 0):
        rprint("No images left to process")
        sys.exit(0)
    nextStep(3, "Processing ...")
    with Pool(args.power) as p:
        # add index and total
        intuple = [(i[0], len(imgsFiltered))+i[1]
                   for i in enumerate(imgsFiltered)]
        # append HRFolder and LRFolder
        intuple = [i+(HRFolder, LRFolder) for i in intuple]
        imgs = p.map(fileparse, intuple)


if __name__ == "__main__":
    main()
