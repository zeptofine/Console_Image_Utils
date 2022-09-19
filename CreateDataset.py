import argparse
import datetime
import glob
import json
import multiprocessing
import os
import pathlib
import subprocess
import sys
import time
from multiprocessing import Pool
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
    print("Please run: 'pip install opencv-python python-dateutil imagesize pillow plyer")

# class opath(): # people have told me it's a bad practice to overwrite a packages' functions lol smh
def stem(path): return path.rsplit(os.sep, 1)[-1].rsplit(".", 1)[0]

#get config file
cfgPath = pathlib.Path(__file__).parent / "config.json"
parserCfg = {'input': None,
    'scale': 4, 'power': (os.cpu_count()//4)*3,
             'minsize': 0, 'maxsize': None,
             'extension': None, 'backend': "cv2",
             'purge': False, 'simulate': False,
             'before': None, 'after': None,
             'anonymous': False, 'no_notifs': False}
if not os.path.exists(cfgPath): 
    open(cfgPath, "w").write(json.dumps(parserCfg))
with open(cfgPath, "r") as cfgP:
    cfgJson = json.loads(cfgP.read())
if cfgJson:
    for i in cfgJson.keys():
        parserCfg[i] = cfgJson[i]

parser = argparse.ArgumentParser()
#set mode
runParams = parser.add_mutually_exclusive_group()
runParams.add_argument("-i", "--input",  help="input directory",                                                                                        default=parserCfg['input'])
runParams.add_argument("--set",          help="change a settings default parameter. call the options like ex. --set backend PIl, or --set minsize 128",   nargs=2)
runParams.add_argument("--reset",        help="change a settings default parameter. will reset everything if given 'all'.")
parser.add_argument("-x", "--scale",     help="scale",                                                                             type=int,            default=parserCfg['scale'])
parser.add_argument("-p",                help="number of cores to use. default is 3/4 of 'os.cpu_count()'.",          dest="power",type=int,            default=parserCfg['power'])
parser.add_argument("--minsize",     help="minimum size of image.",                                                            type=int,                default=parserCfg['minsize'])
parser.add_argument("--maxsize",     help="maximum size of image.",                                                            type=int,                default=parserCfg['maxsize'])
parser.add_argument("-e", "--extension", help="extension of files to export. jpeg, png, webp, etc.",                                                    default=parserCfg['extension'])
parser.add_argument("-b", "--backend",   help="backend to use for resizing. [cv2], PIL.",                     default=parserCfg['backend'])
parser.add_argument("--purge",           help="purge all existing files in output directories before processing",                  action="store_true", default=parserCfg['purge'])
parser.add_argument("--simulate",        help="Doesn't convert at the end.",                                                       action="store_true", default=parserCfg['simulate'])
parser.add_argument("--before",          help="Only converts files modified before a given date. ex. 'Wed Jun 9 04:26:40 2018', or 'Jun 9'",            default=parserCfg['before'])
parser.add_argument("--after",           help="Only converts files modified after a given date.  ex. '2020', or '2009 sept 16th'",                      default=parserCfg['after'])
parser.add_argument("--within",          help="Only convert items modified within a timeframe. use None if unspecified. ex. 'None' 'Wed Jun 9'", 
                                         nargs=2, metavar=('AFTER', 'BEFORE'),                                                                      )
parser.add_argument("--anonymous",       help="replaces the labels in the progress bar with '...'",                                action="store_true", default=parserCfg['anonymous'])
parser.add_argument("--no_notifs",        help="disables the notifications at the end.",                                           action="store_true", default=parserCfg['no_notifs'])
parser.add_argument("--config",          help="Prints the items in the config file.",                                              action="store_true")

args = parser.parse_args()


def pBar(iteration: int, total: int, length=10,
         fill="#", nullp="-", corner="[]", pref='', suff=''):
    # custom progress bar (greatly modified) [https://stackoverflow.com/questions/3173320/text-progress-bar-in-the-console]
    color1, color2 = "\033[93m", "\033[92m"
    filledLength = (length * iteration) // total
    #    [############################# --------------------------------]
    bar = (fill*length)[:filledLength] + (nullp*(length - filledLength))
    command = f"{color2}{corner[0]}{color1}{bar}{color2}{corner[1]}\033[0m"
    command = str(pref)+command+str(suff)
    return command

def pEvent(total, length=0, fill="#", nullp="-", corner="[]", pref=''):
    if length == 0: length = total
    for sec in range(1, total):
        print(pBar(sec, total, length, fill, nullp, corner, pref, f" {sec} / {total} "), end="\r")
        time.sleep(1)

def threadStatus(pid, item="", extra="", extraSize=8):
    print(('\n'*pid)+f"\033[K {str(pid).ljust(3)} | {str(extra).center(extraSize)} | {item if not args.anonymous else '...'}"+('\033[A'*pid), end="\r")

def quickResolution(file):
    try: return imagesize.get(file)
    except: return Image.open(file).size


class imgBackend:  # * image processing 
    def cv2(pid, pth, HR, LR, imtime, suffix):
        image, ppath = cv2.imread(str(pth)), pth.name
        threadStatus(pid, ppath,extra=f"{pBar(1, 2, 2)} {suffix}")
        cv2.imwrite(HR, image)
        threadStatus(pid, ppath,extra=f"{pBar(2, 2, 2)} {suffix}")
        cv2.imwrite(LR, cv2.resize(image, (0, 0), fx=1/args.scale, fy=1/args.scale))
        os.utime(LR, (imtime, imtime))
        os.utime(HR, (imtime, imtime))
    def image(pid, pth, HR, LR, imtime, suffix):
        image, ppath = Image.open(str(pth)), pth.name
        threadStatus(pid, ppath,extra=f"{pBar(1, 2, 2)} {suffix}")
        image.save(HR)
        threadStatus(pid, ppath,extra=f"{pBar(2, 2, 2)} {suffix}")
        image.resize((image.width // args.scale, image.height // args.scale)).save(LR)
        os.utime(LR, (imtime, imtime))
        os.utime(HR, (imtime, imtime))


if __name__ == "__main__":

    if sys.platform == "win32":
        print("This application was made for linux/wsl. either use wsl2 or linux or this will not work.")
        pEvent(5, length=20)

    # run glob.glob repeatedly and concatenate to one list
    def getFiles(*args):
        fileList = []
        for i in enumerate(args):
            print(pBar(i[0], len(args), len(args)), end="\r")
            fileList+=[pathlib.Path(i) for i in (glob.glob(i[1], recursive=True))]
        return fileList

    def getpid(): return int(multiprocessing.current_process().name.rsplit("-", 1)[-1])
    def nextStep(order, text): rprint(" "+f"{str(order)}. {text}", end="\n\033[K")
    def stripNone(inlist: list): return [i for i in inlist if i is not None]

    # * args.set, args.reset, args.config
    if args.set or args.reset:
        if (args.reset == 'all'):
            rprint(f"removing {cfgPath} ...")
            os.remove(cfgPath)
            cfgJson = {}
        else:
            if args.reset:
                if args.reset in cfgJson.keys():
                    cfgJson.pop(args.reset)
                else:
                    print("Given argument isn't in the config.")
                    exit(0)
        if args.set:
            if args.set[1] in ["True", "False"]: args.set[1] = bool(args.set[1])
            elif args.set[1].isdigit(): args.set[1] = int(args.set[1])
            rprint(f"Setting: '{args.set[0]}' => {args.set[1]}...")
            cfgJson[args.set[0]] = args.set[1]
        with open(cfgPath, "w") as cfgWrite:
            cfgWrite.write(json.dumps(cfgJson, indent=4))
        print("Config updated! restart the script to start with your new options.")
        exit()
    elif not args.input:
        rprint("Please specify an input directory.")
        exit(1)
    if args.config:
        rprint(cfgJson)
        exit(0)
    


    
    # Get backend to use for conversion
    backend = None
    if args.backend.lower() in ['cv2', 'opencv', 'opencv2', 'opencv-python']: backend = imgBackend.cv2
    elif args.backend.lower() in ['pil', 'pillow', 'image']:                  backend = imgBackend.image
    assert backend, "Invalid backend chosen. Please write 'cv2', or 'pil'."


    # Handle arguments
    # * args.input
    if args.input.endswith(os.sep): args.input = args.input[:-1]
    # * args.Extension
    if args.extension:
        if args.extension.startswith("."): args.extension = args.extension[1:]
        if args.extension != "same": nextStep(0, f"applying extension: .{args.extension}")


    # * args.input
    HRFolder = pathlib.Path(args.input).parent / (str(args.scale)+"x" + "HR")
    LRFolder = pathlib.Path(args.input).parent / (str(args.scale)+"x" + "LR")
    if args.extension:
        HRFolder = HRFolder.with_name(HRFolder.name+"-"+args.extension)
        LRFolder = LRFolder.with_name(LRFolder.name+"-"+args.extension)
    if not os.path.exists(HRFolder): os.makedirs(HRFolder)
    if not os.path.exists(LRFolder): os.makedirs(LRFolder)
    if args.purge:
        nextStep(0, "purging output directories...")
        for i in getFiles(str(HRFolder / "*"),
                          str(LRFolder / "*")): os.remove(i)
    nextStep(0, "Getting images")
    imgList = getFiles(args.input+"/**/*.png",
                       args.input+"/**/*.jpg",
                       args.input+"/**/*.webp")
    HRList = [f.stem for f in getFiles(str((HRFolder / "*")))]
    LRList = [f.stem for f in getFiles(str((LRFolder / "*")))]
    existList = [i for i in HRList if i in LRList]
    nextStep(0, f"Source: {args.input}")
    nextStep(0, f"({len(imgList)}, {len(existList)}): original, overlap")
    # * args.scale
    assert int(args.scale), "Please give the required argument: scale"
    nextStep(0, f"Scale: {args.scale}")
    nextStep(0, f"Size threshold: ({args.minsize}<=x<={args.maxsize})")
    
    # * args.before & args.after
    beforTime, afterTime = None, None
    if args.within:
        args.after, args.before = args.within

    if args.before or args.after:
        if args.before:
            args.before = str(args.before) 
            beforTime = timeparser.parse(args.before)
        if args.after:  
            args.after = str(args.after)
            afterTime = timeparser.parse(args.after)
        if (args.before) and (args.after):
            if args.after > args.before:
                nextStep("\033[31mError\033[0m", f"{beforTime} is greater than {afterTime}!")
                exit(1)
    nextStep(0, f"Time threshold: ({args.after}<=x<={args.before})")
    
    # I'm honestly not sure if i'll remember anything these functions do in a day
    def indexSet(inlist, indMax):
        indSet = set([stem(i)[:indMax] for i in inlist])
        return {f[:indMax]: [i for i in inlist if i[:indMax] == f[:indMax]] for f in indSet}
    
    def getIndexedList(inlist, maxind=18):
        shuffle(inlist)
        smalList = inlist[:500]
        minList = min(min([len(i) for i in smalList]), maxind+1)
        setList = []
        for h in range(1, minList):
            setList.append((h, indexSet(smalList, h)))
        indTups = [(i[0], len(i[1].keys())) for i in setList]       # [(1, 1) ... (18, 20)]
        indAvg = sum([i[1] for i in indTups])/len(indTups)          # 13.16666
        indClosest = min(indTups, key=lambda x: abs(x[1]-indAvg))   # (9, 13)
        return (indClosest[0], indexSet(inlist, indClosest[0]))

    indexedEList = (6, indexSet(existList, 4))
    if len(existList) != 0:
        indexedEList = getIndexedList(existList)
    nextStep(0, f"Indexed: set to ({indexedEList[0]})")
    # End Handle arguments

    # indexing # to index the input as keys for first 4 characters of every string
    # newlist = {f[:4]: [i for i in oldlist if i[:4] == f[:4]] for f in set([g[:4] for g in oldlist])}
    
    # * Pool functions

    def gatherInfo(inumerated):
        index, item = inumerated
        itemBname = item.stem
        if itemBname[:indexedEList[0]] in indexedEList[1].keys():
            if itemBname in indexedEList[1][itemBname[:indexedEList[0]]]: return
        ext = f".{str(args.extension if args.extension else item.suffix)}"
        threadStatus(getpid(), item.name, 
                     extra=f"{pBar(index, len(imgList))} {index}/{len(imgList)}")
        return {'path': item, 'res': quickResolution(str(item)), 'time': item.stat().st_mtime, 
                'HR': HRFolder / (itemBname+ext), 'LR': LRFolder / (itemBname+ext)}

    def filterImages(inumerated):
        index, item = inumerated
        threadStatus(getpid() - args.power, item['path'].name, extra=f"{pBar(index, len(imgDicts))} {index}/{len(imgList)}")
        if beforTime or afterTime:
            filetime = datetime.datetime.fromtimestamp(item['time'])
            if (beforTime) and (filetime > beforTime): return
            if (afterTime) and (filetime < afterTime): return
        width, height = item['res']
        if args.minsize and ((width < args.minsize) or (height < args.minsize)): return 
        if args.maxsize and ((width > args.maxsize) or (height > args.maxsize)): return 
        if ((width % args.scale) + (height % args.scale) != 0): return
        return item

    def fileparse(imgDict):
        index, imgDict, method = (imgDict[0], imgDict[1][0], imgDict[1][1])
        method(pid=getpid() - args.power*2, pth=imgDict['path'], HR=str(imgDict['HR']), LR=str(imgDict['LR']),
               imtime=imgDict['time'], suffix=str(index))


    nextStep(1, "Gathering image information")
    with Pool(args.power) as p:
        imgDicts = list(p.map(gatherInfo, enumerate(imgList)))
        imgDicts = stripNone(imgDicts)
        nextStep("2a", f"({len(imgDicts)}, {len(imgList)-len(imgDicts)}): possible, discarded")

    # exit()
    nextStep(2, f"Filtering out bad images")
    with Pool(args.power) as p:
        imgList = p.map(filterImages, enumerate(imgDicts))
        imgList = stripNone(imgList)
    nextStep("2a", f"({len(imgList)}, {len(imgDicts)-len(imgList)}): possible, discarded")

    # if len(imgList) == 0:
    #     exit(print("No images left to process"))

    if args.simulate: exit()

    nextStep(3, "Processing...")
    result = "Failed"
    try:
        with Pool(args.power) as p:
            imdict = p.map(fileparse, enumerate([(i, backend) for i in imgList]))
        p.close()
        print("\nDone!")
        result = "Finished"

    except KeyboardInterrupt:
        p.close()
        p.join()
        print("\n"*(args.power*2)+"Conversion cancelled")

    if not args.no_notifs:
        subpReturn = subprocess.Popen(["notify-send",
                            "-a", "Dataset Generator", '-w',
                            '-t', '4000',
                            f"The generator has {result}!"])
