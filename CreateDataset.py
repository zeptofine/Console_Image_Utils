import argparse
import datetime
import glob
import json
import multiprocessing
import os
import pathlib
import shutil
import sys
import time
from multiprocessing import Pool
from pathlib import Path
from pprint import pprint
from random import shuffle

from misc_utils import nextStep, numFmt, pBar, thread_status

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
defaultCfg = {'input': None,
              'scale': 4, 'power': (CPU_COUNT//4)*3,
              'minsize': None, 'maxsize': None, 'maxmethod': "skip",
              'extension': None, 'backend': "cv2",
              'purge': False, 'simulate': False,
              'before': None, 'after': None,
              'anonymous': False, 'no_notifs': False,
              'no_color': False, 'recursive': False}
cfgPath = pathlib.Path(__file__).parent / "config.json"


def setCfgDefaults(inpath: pathlib.Path, cfgDict: dict):
    if not inpath.exists():
        open(inpath, "w", encoding="utf-8").write(json.dumps({}))
    with open(inpath, "r", encoding="utf-8") as cfgP:
        cfgJson = json.loads(cfgP.read())
        cfgP.close()
    if cfgJson:
        for i in cfgJson.keys():
            cfgDict[i] = cfgJson[i]
    return cfgDict, cfgJson


parserCfg, cfgJson = setCfgDefaults(cfgPath, defaultCfg)

parser = argparse.ArgumentParser()
runOptions = parser.add_mutually_exclusive_group()
runOptions.add_argument("-i", "--input",
                        default=parserCfg['input'])
runOptions.add_argument("--set",
                        help="change a default argument's option.",
                        nargs=2)
runOptions.add_argument("--reset",
                        help="removes a changed option.")
runOptions.add_argument("--config",
                        help="returns the file config.",
                        action="store_true")

parser.add_argument("-x", "--scale",
                    type=int, default=parserCfg['scale'])
parser.add_argument("-e", "--extension",
                    help="export extension.", default=parserCfg['extension'])
parser.add_argument("-r", "--recursive", help="preserves the tree hierarchy.",
                    action="store_true", default=parserCfg['recursive'])

parser.add_argument("--minsize", help="smallest available image",
                    type=int, default=parserCfg['minsize'])
parser.add_argument("--maxsize", help="largest allowed image.",
                    type=int, default=parserCfg['maxsize'])

parser.add_argument("--after",
                    help="Only uses files modified after a given date.  ex. '2020', or '2009 sept 16th'",
                    default=parserCfg['after'])
parser.add_argument("--before",
                    help="Only uses before a given date. ex. 'Wed Jun 9 04:26:40 2018', or 'Jun 9'",
                    default=parserCfg['before'])
parser.add_argument("--within", help="Only convert items modified within a timeframe. use None if unspecified. ex. 'None' 'Wed Jun 9'",
                    nargs=2, metavar=('AFTER', 'BEFORE'))

parser.add_argument("--power", help="number of cores to use.",
                    type=int, default=parserCfg['power'])
parser.add_argument("--anonymous", help="hides path names in progress. Doesn't affect the result.",
                    action="store_true", default=parserCfg['anonymous'])
parser.add_argument("--simulate", help="skips the conversion step.",
                    action="store_true", default=parserCfg['simulate'])
parser.add_argument("--purge", help="Clears every output before converting.",
                    action="store_true", default=parserCfg['purge'])
args = parser.parse_args()

if args.set or args.reset:
    if args.set:
        if args.set[1] in ["True", "False"]:
            args.set[1] = map(lambda ele: ele == "True", args.set[1])
        elif args.set[1].isdigit():
            args.set[1] = int(args.set[1])
        rprint(f"Setting: '{args.set[0]}' => {args.set[1]} ...")
        if args.set[0] not in defaultCfg.keys():
            print("This key isn't available, so results may vary")
        cfgJson[args.set[0]] = args.set[1]
    elif args.reset:
        if (args.reset == 'all'):
            rprint(f"clearing {cfgPath} ...")
            cfgJson = {}
        else:
            if args.reset not in defaultCfg.keys():
                rprint("key is not visible from editable defaults!")
            if args.reset in cfgJson.keys():
                rprint(f"resetting {args.reset} ...")
                cfgJson.pop(args.reset)

    with open(cfgPath, "w", encoding="utf-8") as cfgWrite:
        cfgWrite.write(json.dumps(cfgJson, indent=4))
        cfgWrite.close()
    sys.exit("Config updated! restart to use the new options.")


beforeTime, afterTime = None, None
if args.within:
    args.after, args.before = args.within
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


def getFileList(*args):
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
    nextStep(0, "Gathering paths ...")
    args.input = Path(args.input)
    imageList = getFileList(args.input/"**"/"*.png",
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
        for i in getFileList(str(HRFolder/"**/*"),
                             str(LRFolder/"**/*")):
            if i.is_dir():
                shutil.rmtree(i)
            elif i.is_file():
                os.remove(i)
        nextStep(0, "Purged.")

    HRFiles = [f.stem for f in getFileList(str((HRFolder / "*")))]
    LRFiles = [f.stem for f in getFileList(str((LRFolder / "*")))]
    existList = [i for i in HRFiles if i in LRFiles]
    nextStep(0, f"(source, existed): ({len(imageList)}, {len(existList)})")
    imageList = [i for i in imageList if i.stem not in existList]
    nextStep(0, f"new list: {len(imageList)}")
    nextStep(0, f"Scale: ({args.scale})")
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
    if args.config:
        rprint(cfgJson)
        sys.exit()
    main()
