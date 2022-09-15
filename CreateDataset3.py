import argparse
import datetime
import glob
import multiprocessing
import os
import sys
import time
from multiprocessing import Pool
from random import shuffle
from rich import print as rprint
try: 
    import cv2
    import dateutil.parser as timeparser
    import imagesize
    from PIL import Image
except:
    print("Please run: 'pip install opencv-python python-dateutil imagesize pillow")

parser = argparse.ArgumentParser()
parser.add_argument("-i", "--input",     help="input directory",                                                                      required=True)
parser.add_argument("-x", "--scale",     help="scale",                                                                      type=int, required=True)
parser.add_argument("-p", "--power",     help="number of cores to use. default is 'os.cpu_count()'.", type=int, default=int(((os.cpu_count()/4)*3)))
parser.add_argument("--msize",           help="minimum size of image.",                                                         type=int, default=0)
parser.add_argument("-e", "--extension", help="extension of files to export. jpeg, png, webp, etc.")
parser.add_argument("--backend",         help="backend to use for resizing. [cv2], PIL. cv2 is safer but slower in my experience.",   default="cv2")
parser.add_argument("--purge",           help="purge all existing files in output directories before processing",               action="store_true")
parser.add_argument("--simulate",        help="Doesn't convert at the end.",                                                    action="store_true")
parser.add_argument("--before",          help="Only converts files modified before a given date. ex. 'Wed Jun 9 04:26:40 2018', or 'Jun 9'",       )
parser.add_argument("--after",           help="Only converts files modified after a given date.  ex. '2020', or '2009 sept 16th'",                 )
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
    print(('\n'*pid)+f"\033[K {str(pid).ljust(3)} | {str(extra).center(extraSize)} | {item}"+('\033[A'*pid), end="\r")

def quickResolution(file):
    try: return imagesize.get(file)
    except: return Image.open(file).size

class opath():
    def basename(path): return path.rsplit(os.sep, 1)[-1]
    def extension(path): return path.rsplit(".", 1)[-1]
    def basename_(path): return path.rsplit(os.sep, 1)[-1].rsplit(".", 1)[0]
    def dirname(path): return path.rsplit(os.sep, 1)[0]
    def join(*args): return os.sep.join([i for i in args])

class imgBackend:  # * image processing 
    def cv2(pid, pth, HR, LR, imtime, suffix):
        image, ppath = cv2.imread(pth), opath.basename(pth)
        threadStatus(pid, ppath,extra=f"{pBar(1, 2, 2)} {suffix}")
        cv2.imwrite(HR, image)
        threadStatus(pid, ppath,extra=f"{pBar(2, 2, 2)} {suffix}")
        cv2.imwrite(LR, cv2.resize(image, (0, 0), fx=1/args.scale, fy=1/args.scale))
        os.utime(LR, (imtime, imtime))
        os.utime(HR, (imtime, imtime))
    def image(pid, pth, HR, LR, imtime, suffix):
        image, ppath = Image.open(pth), opath.basename(pth)
        threadStatus(pid, ppath,extra=f"{pBar(1, 2, 2)} {suffix}")
        image.save(HR)
        threadStatus(pid, ppath,extra=f"{pBar(2, 2, 2)} {suffix}")
        image.resize((image.width // args.scale, image.height // args.scale)).save(LR)
        os.utime(LR, (imtime, imtime)),
        os.utime(HR, (imtime, imtime))


if __name__ == "__main__":

    if sys.platform == "win32":
        print("This application was made for linux/wsl. either use wsl2 or linux or this will not work.")
        pEvent(5, length=20)

    # run glob.glob repeatedly and concatenate to one list
    def getFiles(*args): return [y for x in [glob.glob(i, recursive=True) for i in args] for y in x]
    def getpid(): return int(multiprocessing.current_process().name.rsplit("-", 1)[-1])
    def nextStep(order, text): print(" "+f"\033[K{str(order)}. {text}", end="\n\033[K")
    def stripNone(inlist: list): return [i for i in inlist if i is not None]

    # Get backend to use for conversion
    backend = None
    if args.backend.lower() in ['cv2', 'opencv', 'opencv2', 'opencv-python']: backend = imgBackend.cv2
    elif args.backend.lower() in ['pil', 'pillow', 'image']:                  backend = imgBackend.image
    assert backend, "Invalid backend chosen. Please write 'cv2', or 'pil'."


    # Handle arguments

    # * args.input
    if args.input.endswith(os.sep): args.input = args.input[:-1]

    # * args.Extension
    print(f"using {args.power} threads")
    if args.extension.startswith("."): args.extension = args.extension[1:]
    if args.extension != "same": print(f"applying extension: .{args.extension}")

    # * args.before & args.after
    beforTime, afterTime = None, None
    if args.before or args.after:
        if args.before: beforTime = timeparser.parse(args.before)
        if args.after:  afterTime = timeparser.parse(args.after)
        nextStep("0c", f"using: ({beforTime}, {afterTime})")
    if (args.before) and (args.after) and (args.before < args.after):
        nextStep("\033[31mError\033[0m", f"{beforTime} is greater than {afterTime}!")
        exit(1)

    # * args.input
    HRFolder = opath.join(opath.dirname(args.input), str(args.scale)+"x") + "HR"
    LRFolder = opath.join(opath.dirname(args.input), str(args.scale)+"x") + "LR"
    if args.extension:
        HRFolder += "-"+args.extension
        LRFolder += "-"+args.extension
    if not os.path.exists(HRFolder): os.makedirs(HRFolder)
    if not os.path.exists(LRFolder): os.makedirs(LRFolder)
    if args.purge:
        print("purging output directories...")
        for i in sorted(getFiles(opath.join(HRFolder, "*"),
                                 opath.join(LRFolder, "*"))): os.remove(i)

    nextStep(0, "Getting images")
    imgList = getFiles(args.input+"/**/*.png",
                       args.input+"/**/*.jpg",
                       args.input+"/**/*.webp")

    HRList = [opath.basename_(f) for f in getFiles(HRFolder + "/*")]
    LRList = [opath.basename_(f) for f in getFiles(LRFolder + "/*")]
    existList = [i for i in HRList if i in LRList]
    nextStep("0a", f"({len(imgList)}): original")
    nextStep("0b", f"({len(existList)}, {len(HRList)}, {len(LRList)}): overlapping, HR, LR")
    
    nextStep("0c", f"Indexing overlapping")
    
    def indexSet(inlist, indMax):
        indSet = set([opath.basename_(i)[:indMax] for i in inlist])
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


    indexedEList = (4, indexSet(existList, 4))
    if len(existList) != 0:
        indexedEList = getIndexedList(existList)
    nextStep("0ca", f"Indexing finished: set to ({indexedEList[0]})")
    # End Handle arguments

    # indexing # to index the input as keys for first 4 characters of every string
    # newlist = {f[:4]: [i for i in oldlist if i[:4] == f[:4]] for f in set([g[:4] for g in oldlist])}
    # * Pool functions

    def gatherInfo(inumerated):
        index, item = inumerated
        itemBname = opath.basename_(item)
        if itemBname[:indexedEList[0]] in indexedEList[1].keys():
            if itemBname in indexedEList[1][itemBname[:indexedEList[0]]]: return
        ext = f".{str(args.extension if args.extension else opath.extension(item))}"
        threadStatus(getpid(), opath.basename(item), 
                     extra=f"{pBar(index, len(imgList))} {index}/{len(imgList)}")
        return {'path': item, 'res': quickResolution(item), 'time': os.path.getmtime(item),
                'HR': opath.join(HRFolder, itemBname+ext), 'LR': opath.join(LRFolder, itemBname+ext)}

    def filterImages(inumerated):
        index, item = inumerated
        threadStatus(getpid() - args.power, opath.basename(item['path']), extra=f"{pBar(index, len(imgDicts))} {index}/{len(imgList)}")
        if beforTime or afterTime:
            filetime = datetime.datetime.fromtimestamp(item['time'])
            if (beforTime) and (filetime > beforTime): return
            if (afterTime) and (filetime < afterTime): return
        width, height = item['res']
        if (width < args.msize) or (height < args.msize) or ((width % args.scale) + (height % args.scale) != 0): return
        return item

    def fileparse(imgDict):
        index, imgDict, method = (imgDict[0], imgDict[1][0], imgDict[1][1])
        method(pid=getpid() - args.power*2, pth=imgDict['path'], HR=imgDict['HR'], LR=imgDict['LR'],
               imtime=imgDict['time'], suffix=str(index))


    nextStep(1, "Gathering image information")
    with Pool(args.power) as p:
        imgDicts = list(p.map(gatherInfo, enumerate(imgList)))
        imgDicts = stripNone(imgDicts)
        nextStep("2a", f"({len(imgDicts)}, {len(imgList)-len(imgDicts)}): possible, discarded")

    nextStep(2, f"Filtering out bad images")
    with Pool(args.power) as p:
        imgList = p.map(filterImages, enumerate(imgDicts))
        imgList = stripNone(imgList)
    nextStep("2a", f"({len(imgList)}, {len(imgDicts)-len(imgList)}): possible, discarded")

    imgDicts = sorted(imgDicts, key=lambda x: x['res']) # sort by resolution
    if len(imgList) == 0: 
        exit(print("No images left to process"))

    if args.simulate: exit()

    nextStep(3, "Processing...")
    try:
        with Pool(args.power) as p:
            imdict = p.map(fileparse, enumerate([(i, backend) for i in imgList]))
        p.close()
        print("\nDone!")
    except KeyboardInterrupt:
        p.close()
        p.join()
        print("\n"*args.power+"Conversion cancelled")
