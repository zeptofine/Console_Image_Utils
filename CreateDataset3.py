import argparse
import datetime
import glob
import multiprocessing
import os
import sys
import time
from multiprocessing import Pool
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
class timer:  # timer setup ####
    def start():
        '''start the timer'''
        timer.timer_start_time = time.perf_counter()

    def print(instr, end='\n'):
        '''print and restart the timer'''

        now = time.perf_counter()
        try:
            diff = (now - timer.timer_start_time) * 1000
            timer.timer_start_time = now
            print(f"{instr}: ms{diff:.4f}", end=end)
            return diff
        except:
            timer.start()
            print(instr, end=end)

    def poll(instr, end='\n'):
        '''print without restarting the timer'''
        now = time.perf_counter()
        print(f"{instr}: ms{(now - timer.timer_start_time) * 1000:.4f}", end=end)

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
        print(pBar(sec, total, length, fill=fill, nullp=nullp, corner=corner, pref=pref, suff=f" {sec} / {total} "), end="\r")
        time.sleep(1)


def threadStatus(pid, item="", extra="", extraSize=8):
    command = ("\n"*pid) + f"\033[K {str(pid).ljust(3)}| {str(extra).center(extraSize)} | {item}" + ("\033[A"*pid)
    print(command, end="\r")
class opath():
    def basename(path): return path.rsplit(os.sep, 1)[-1]
    def extension(path): return path.rsplit(".", 1)[-1]
    def basename_(path): return path.rsplit(os.sep, 1)[-1].rsplit(".", 1)[0]
    def dirname(path): return path.rsplit(os.sep, 1)[0]
    def join(*args): return os.sep.join([i for i in args])

def quickResolution(file):
    try:
        return imagesize.get(file)
    except:
        return Image.open(file).size


class imgBackend:  # * image processing backends
    def cv2(pid, pth, HR, LR, imtime, suffix):
        image, ppath, = cv2.imread(pth), opath.basename(pth)
        threadStatus(pid, ppath,extra=pBar(1, 2, 2, suff=suffix))
        cv2.imwrite(HR, image)
        threadStatus(pid, ppath,extra=pBar(2, 2, 2, suff=suffix))
        cv2.imwrite(LR, cv2.resize(image, (0, 0), fx=1/args.scale, fy=1/args.scale))
        os.utime(LR, (imtime, imtime))
        os.utime(HR, (imtime, imtime))
    def image(pid, pth, HR, LR, imtime, suffix):
        image, ppath = Image.open(pth), opath.basename(pth)
        threadStatus(pid, ppath,extra=pBar(1, 2, 2, suff=suffix))
        image.save(HR)
        threadStatus(pid, ppath,extra=pBar(2, 2, 2, suff=suffix))
        image.resize((image.width // args.scale, image.height // args.scale)).save(LR)
        os.utime(LR, (imtime, imtime))
        os.utime(HR, (imtime, imtime))






if __name__ == "__main__":

    if sys.platform == "win32":
        print("This application was made for linux/wsl. either use wsl2 or linux or this will not work.")
        pEvent(5, length=20)

    def getpid(): return int(multiprocessing.current_process().name.rsplit("-", 1)[-1])
    def nextStep(order, text): print(" "+f"\033[K{str(order)}. {text}", end="\n\033[K")
    # run glob.glob repeatedly and concatenate to one list
    def get_files(*args): return [y for x in [glob.glob(i, recursive=True) for i in args] for y in x]

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
    if args.extension != "same":
        print(f"applying extension: .{args.extension}")

    # * args.before & args.after
    beforTime, afterTime = None, None
    if args.before: beforTime = timeparser.parse(args.before)
    if args.after:  afterTime = timeparser.parse(args.after)
    if args.before or args.after: nextStep("0c", f"using: ({beforTime}, {afterTime})")
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
        print("purging all existing files in output directories...")
        for index in sorted(get_files(opath.join(HRFolder, "*"), opath.join(LRFolder, "*"))): os.remove(index)

    nextStep(0, "Getting images")
    imgList = get_files(args.input+"/**/*.png",args.input+"/**/*.jpg",args.input+"/**/*.webp")
    HRList = [opath.basename_(f) for f in get_files(HRFolder + "/*")]
    LRList = [opath.basename_(f) for f in get_files(LRFolder + "/*")]
    existList = [i for i in HRList if i in LRList]
    indSet = set([opath.basename_(i)[:4] for i in imgList])
    indexedEList = {f[:4]: [i for i in existList if i[:4] == f[:4]] for f in indSet}
    nextStep("0a", f"({len(imgList)}): original")
    nextStep("0b", f"({len(existList)}, {len(HRList)}, {len(LRList)}): overlapping, HR, LR")
        
    # End Handle arguments


    # indexing # to index the input as keys for first 4 characters of every string
    # HRIndexed = {f[:4]: [i for i in HRList if i[:4] == f[:4]] for f in set([i[:4] for i in HRList])}
    # LRIndexed = {f[:4]: [i for i in LRList if i[:4] == f[:4]] for f in set([i[:4] for i in LRList])}

    # * Pool functions

    def gatherInfo(inumerated):
        index, item = inumerated
        itemBname = opath.basename_(item)
        ext = f".{str(args.extension if args.extension else opath.extension(item))}"
        threadStatus(getpid(), opath.basename(item),
                     extra=pBar(index, len(imgList), suff=f" {index}/{len(imgList)}"))
        if itemBname in indexedEList[itemBname[:4]]: return
        return {'path': item, 'res': quickResolution(item),
                'HR': opath.join(HRFolder, itemBname+ext),
                'LR': opath.join(LRFolder, itemBname+ext),
                'time': os.path.getmtime(item)}

    def filterImages(inumerated):
        index, item = inumerated
        threadStatus(getpid() - args.power, item=opath.basename(item['path']),
                     extra=pBar(index, len(imgDict), suff=f" {index}/{len(imgList)}"))
        width, height = item['res']
        if beforTime or afterTime:
            filetime = datetime.datetime.fromtimestamp(item['time'])
            if (beforTime) and (filetime > beforTime): return
            if (afterTime) and (filetime < afterTime): return
        if (width < args.msize) or (height < args.msize) or ((width % args.scale) + (height % args.scale) != 0): return
        return item

    def fileparse(imgDict):
        index, imgDict, method = (imgDict[0], imgDict[1][0], imgDict[1][1])
        method(pid=getpid() - args.power*2, pth=imgDict['path'], 
               HR=imgDict['HR'], LR=imgDict['LR'], 
               imtime=imgDict['time'], suffix=" "+str(index))

    
    nextStep(1, "Gathering image information")
    with Pool(args.power) as p:
        imgDict = list(p.map(gatherInfo, enumerate(imgList)))
        imgDict = [i for i in imgDict if i is not None]
        nextStep("2a", f"({len(imgDict)}, {len(imgList)-len(imgDict)}): possible, discarded")
    nextStep(2, f"Filtering out bad images")
    with Pool(args.power) as p:
        imgList = p.map(filterImages, enumerate(imgDict))
        imgList = [i for i in imgList if i is not None]
    nextStep("2a", f"({len(imgList)}, {len(imgDict)-len(imgList)}): possible, discarded")

    if len(imgList) == 0: 
        print("No images left to process")
        exit()

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
