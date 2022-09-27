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

try:
    from rich import print as rprint
except:
    rprint = print
try:
    import cv2
    import dateutil.parser as timeparser
    import imagesize
    from PIL import Image
except:
    print("Please run: 'pip install opencv-python python-dateutil imagesize pillow")
    exit(1)

if sys.platform == "win32":
    print("This application was not made for windows and its compatibility is not guaranteed.")
    time.sleep(5)

defaultCfg = {'input': None,
    'scale': 4, 'power': (os.cpu_count()//4)*3,
             'minsize': None, 'maxsize': None, 'maxmethod': "skip",
             'extension': None, 'backend': "cv2",
             'purge': False, 'simulate': False,
             'before': None, 'after': None,
             'anonymous': False, 'no_notifs': False,
             'no_color': False, 'recursive':False}
cfgPath = pathlib.Path(__file__).parent / "config.json"
def setCfgDefaults(inpath: pathlib.Path, cfgDict: dict):
    if not inpath.exists():
        open(inpath, "w").write(json.dumps({}))
    with open(inpath, "r") as cfgP:
        cfgJson = json.loads(cfgP.read())
        cfgP.close()
    if cfgJson:
        for i in cfgJson.keys():
            cfgDict[i] = cfgJson[i]
    return cfgDict, cfgJson
parserCfg, cfgJson = setCfgDefaults(cfgPath, defaultCfg)

parser = argparse.ArgumentParser()
runOptions = parser.add_mutually_exclusive_group()
runOptions.add_argument("-i", "--input", default=parserCfg['input'])
runOptions.add_argument("--set", help="change a default argument's option.", nargs=2)
runOptions.add_argument("--reset", help="removes a changed option.")
runOptions.add_argument("--config", help="returns the file config.", action="store_true")

parser.add_argument("-x", "--scale", default=parserCfg['scale'])
parser.add_argument("-e", "--extension", help="export extension.", default=parserCfg['extension'])
parser.add_argument("-r", "--recursive", help="preserves the tree hierarchy.", action="store_true", default=defaultCfg['recursive'])

parser.add_argument("--minsize", help="smallest available image", type=int,   default=defaultCfg['minsize'])
parser.add_argument("--maxsize", help="largest allowed image.",   type=int,   default=parserCfg['maxsize'])

parser.add_argument("--after", help="Only uses files modified after a given date.  ex. '2020', or '2009 sept 16th'", default=parserCfg['after'])
parser.add_argument("--before", help="Only uses before a given date. ex. 'Wed Jun 9 04:26:40 2018', or 'Jun 9'", default=parserCfg['before'])
parser.add_argument("--within", help="Only convert items modified within a timeframe. use None if unspecified. ex. 'None' 'Wed Jun 9'", nargs=2, metavar=('AFTER', 'BEFORE'))

parser.add_argument("--power", help="number of cores to use.",     type=int,         default=parserCfg['power'])
parser.add_argument("--anonymous", help="hides path names in progress.",   action="store_true", default=parserCfg['anonymous'])
parser.add_argument("--no_color", help="Disables color output from rich (if installed).", action="store_true", default=parserCfg['no_color'])
parser.add_argument("--simulate", help="skips the conversion step.", action="store_true", default=parserCfg['simulate'])
parser.add_argument("--purge",    help="Clears every output before converting.", action="store_true", default=parserCfg['purge'])
args = parser.parse_args()

if args.no_color: rprint = print

if args.set or args.reset:
    if args.set:
        if args.set[1] in ["True", "False"]: args.set[1] = eval(args.set[1])
        elif args.set[1].isdigit(): args.set[1] = int(args.set[1])
        rprint(f"Setting: '{args.set[0]}' => {args.set[1]} ...")
        if args.set[0] not in defaultCfg.keys(): print("This key isn't available, so results may vary")
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
            
    with open(cfgPath, "w") as cfgWrite:
        cfgWrite.write(json.dumps(cfgJson, indent=4))
        cfgWrite.close()
    rprint("Config updated! restart to use the new options.")
    exit()


beforeTime, afterTime = None, None
if args.within:
    args.after, args.before = args.within
if args.after or args.before:    
    if args.after:
        args.after = str(args.after)
        afterTime = timeparser.parse(args.after, fuzzy=True)
    if args.before:
        args.before = str(args.before)
        beforeTime = timeparser.parse(args.before, fuzzy=True)
    if args.after and args.before:
        assert args.after < args.before, f"{beforeTime} is older than {afterTime}!"

def pBar(iteration: int, total: int, length=10,
         fill="#", nullp="-", corner="[]", pref='', suff=''):
    color1, color2 = ("\033[93m", "\033[92m") if not args.no_color else ("", "")
    filledLength = (length * iteration) // total
    #    [############################# --------------------------------]
    bar = (fill*length)[:filledLength] + (nullp*(length - filledLength))
    command = f"{color2}{corner[0]}{color1}{bar}{color2}{corner[1]}\033[0m"
    command = str(pref)+command+str(suff)
    return command

def threadStatus(pid, item="", extra="", extraSize=8):
    print(('\n'*pid)+f"\033[K {str(pid).ljust(3)} | {str(extra).center(extraSize)} | {item if not args.anonymous else '...'}"+('\033[A'*pid), end="\r")

def byteFormat(size: str|int):
    size = int("".join([num for num in str(size) if num.isnumeric()]))
    if (size > 0):
        for unit in ['', 'Ki', 'Mi', 'Gi', 'Ti']:
            if abs(size) < 2**10: return f"{size:.2f} {unit}B"
            size /= 2**10
        return f"{size:.2f} {unit}B"
    else: return f"N/A B"

def getpid(): return int(multiprocessing.current_process().name.rsplit("-", 1)[-1])
def nextStep(order, text): rprint(" "+f"{str(order)}. {text}", end="\n\033[K")
def stripNone(inlist: list): return [i for i in inlist if i is not None]

def getFileList(*args): 
    return [Path(y) for x in [glob.glob(str(p), recursive=True) for p in args] for y in x]

def quickResolution(file):
    try: return imagesize.get(file)
    except: return Image.open(file).size


def gatherInfo(inumerated):
    index, ptotal, inpath = inumerated
    basePath = inpath.stem
    ext = f".{str(args.extension if args.extension else inpath.suffix)}"
    threadStatus(getpid(), inpath.name, extra=f"{pBar(index, ptotal)}")
    return (inpath, quickResolution(str(inpath)))

def filterImages(inumerated):
    index, ptotal, inpath, res = inumerated
    threadStatus(getpid()-args.power, inpath.name,
                 extra=f"{pBar(index, ptotal)} {index}/{ptotal}")
    filestime = inpath.stat().st_mtime
    if beforeTime or afterTime:
        filetime = datetime.datetime.fromtimestamp(filestime)
        if (beforeTime) and (filetime > beforeTime): return
        if (afterTime) and  (filetime < afterTime):  return
    width, height = res
    if args.minsize and ((width < args.minsize) or (height < args.minsize)): return
    if args.maxsize and ((width > args.maxsize) or (height > args.maxsize)): return
    if (width % args.scale != 0)  or (height % args.scale != 0): return
    return (inpath, res, filestime)

def fileparse(inumerated):
    index, inpath, res, filestime, HRFolder, LRFolder = inumerated
    inpath: Path = inpath
    relPath = Path(inpath.relative_to(args.input))
    if args.recursive:
        HRPath: Path = HRFolder / relPath
        LRPath: Path = LRFolder / relPath
        try:
            if not LRPath.parent.exists(): os.makedirs(HRPath.parent)
        except: pass
        try: 
            if not LRPath.parent.exists(): os.makedirs(LRPath.parent)
        except: pass
    else:
        HRPath = HRFolder / inpath.name
        LRPath = LRFolder / inpath.name
    if args.extension:
        HRPath = HRPath.with_suffix("."+args.extension)
        LRPath = LRPath.with_suffix("."+args.extension)
    pid = getpid() - args.power*2
    image = cv2.imread(str(inpath))
    threadStatus(pid, relPath, extra=pBar(1, 2, 2))
    cv2.imwrite(str(HRPath), image)
    threadStatus(pid, relPath, extra=pBar(2, 2, 2))
    cv2.imwrite(str(LRPath), cv2.resize(image, (0, 0), fx=1/args.scale, fy=1/args.scale))
    os.utime(str(HRPath), (filestime, filestime))
    os.utime(str(LRPath), (filestime, filestime))


def main():
    
    assert args.input, "Please specify an input directory."
    nextStep(0, f"Input: {args.input}")
    args.input = Path(args.input)
    imageList = getFileList(args.input/"**"/"*.png",
                            args.input/"**"/"*.jpg",
                            args.input/"**"/"*.webp")

    if (args.extension) and (args.extension.startswith(".")): args.extension = args.extension[1:]

    HRFolder = args.input.parent / (str(args.scale)+"xHR")
    LRFolder = args.input.parent / (str(args.scale)+"xLR")
    if args.extension:
        HRFolder = Path(str(HRFolder)+f"-{args.extension}")
        LRFolder = Path(str(LRFolder)+f"-{args.extension}")
    if not HRFolder.exists(): os.makedirs(HRFolder)
    if not LRFolder.exists(): os.makedirs(LRFolder)

    if args.purge:
        nextStep(0, "Purging output ...")
        for i in getFileList(str(HRFolder/"**/*"),
                             str(LRFolder/"**/*")): 
            if i.is_dir(): shutil.rmtree(i)
            elif i.is_file(): os.remove(i)

    HRFiles = [f.stem for f in getFileList(str((HRFolder / "*")))]
    LRFiles = [f.stem for f in getFileList(str((LRFolder / "*")))]
    existList = [i for i in HRFiles if i in LRFiles]
    imageList = [i for i in imageList if i.stem not in existList]
    
    nextStep(0, f"(source, existed): ({len(imageList)}, {len(existList)})")
    nextStep(0, f"list sizes:        ({byteFormat(sys.getsizeof(imageList))}, {byteFormat(sys.getsizeof(existList))})")
    nextStep(0, f"Scale:             ({args.scale})")
    nextStep(0, f"Size threshold:    ({args.minsize}<=x<={args.maxsize})")
    nextStep(0, f"Time threshold:    ({afterTime}<=x<={beforeTime})")
    
    
    
    nextStep(1, "Gathering image information")
    with Pool(args.power) as p:
        imageTuples = list(p.map(gatherInfo, [(i[0], len(imageList), i[1]) for i in enumerate(imageList)]))

    nextStep(1, f"Images:            ({len(imageTuples)}, {byteFormat(sys.getsizeof(imageTuples))})")
    nextStep(2, "Filtering out bad images")
    with Pool(args.power) as p:
        imageFiltered = list(p.map(filterImages, [(i[0], len(imageList), 
                                                   i[1][0], i[1][1]) for i in enumerate(imageTuples)]))
    imageFiltered = stripNone(imageFiltered)
    nextStep(2, f"Images:            ({len(imageFiltered)}, {byteFormat(sys.getsizeof(imageFiltered))})")

    if args.simulate: return 
    
    if len(imageFiltered) == 0: 
        nextStep(3, "No images left to process")
        exit()
    nextStep(3, "Processing ...")
    with Pool(args.power) as p:
        shuffle(imageFiltered)
        newImages = list(p.imap(fileparse, [(i[0], i[1][0], i[1][1], i[1][2], 
                                             HRFolder, LRFolder) for i in enumerate(imageFiltered)]))
    
if __name__=="__main__":
    if args.config:
        rprint(cfgJson)
        exit()
    main()
