
import argparse
import glob
import multiprocessing
import os
import sys
import time
from multiprocessing import Pool
from pprint import pprint

import cv2
import imagesize
from PIL import Image


def pBar(iteration: int, total: int, length: int = max(os.get_terminal_size()[0]//6, 10),
         Print=False, fill="#", nullp="-", corner="[]", color=True,
         end="\r", pref='', suff=''):
    # custom progress bar (slightly modified) [https://stackoverflow.com/questions/3173320/text-progress-bar-in-the-console]
    color1, color2 = "\033[93m", "\033[92m"
    filledLength = length * iteration // total

    #    [############################# --------------------------------]
    bar = (fill*length)[:filledLength] + (nullp*(length - filledLength))
    command = f"\033[K{color2}{corner[0]}{color1}{bar}{color2}{corner[1]}\033[0m" if color else f"{corner[0]}{bar}{corner[1]}"
    command = pref+command+suff
    if Print:
        print(command, end=end)
    return command


def progressEvent(duration, length=0, fill="#", nullp="-", corner="[]", color=True, end="\r", pref='', suff=''):
    if length == 0: length = duration
    for second in range(1, duration):
        if suff != "": suff = f" {second} / {duration} "
        pBar(second, duration, length, fill=fill, nullp=nullp,
             corner=corner, color=True, end=end, pref=pref, suff=suff)
        time.sleep(1)


def thread_status(pid, item, extra="", extraSize=8):
    """Displays a status line for a specified process.
    pid: process id
    item: long text to display
    extra: extra text to display before listed item, such as 'Processing' or 'Thinking'
    """
    command = f"\033[K {str(pid).ljust(3)}| {str(extra).center(extraSize)} | {item}"
    command = ("\n"*pid) + command + ("\033[A"*pid)
    print(command, end="\r")


if sys.platform == "win32":
    print("This application was made for linux/wsl. either use wsl2 or linux or this will not work. you have been warned.")
    progressEvent(10, length=20)


parser = argparse.ArgumentParser()
parser.add_argument("-i", "--input", help="input directory", required=True)
parser.add_argument("-x", "--scale", help="scale", type=int, required=True)
parser.add_argument("-p", "--power", help="number of cores to use. default is 'os.cpu_count()'.",
                    type=int, default=int(((os.cpu_count()/4)*3)), required=False)
parser.add_argument("--minsize", help="minimum size of image",
                    type=int, default=0, required=False)
parser.add_argument("-e", "--extension", help="extension of files to export. [same], jpeg, png, webp, etc.",
                    default="same", required=False)
parser.add_argument("--backend", help="backend to use for resizing. [cv2], PIL. cv2 is safer but slower in my experience.",
                    default="cv2", required=False)
parser.add_argument("--purge", help="purge all existing files in output directories before processing",
                    default=False, action="store_true", required=False)
args = parser.parse_args()


if args.input.endswith(os.sep):  # strip slash from end of path if exists
    args.input = args.input[:-1]


class ospath():
    def basename(path):
        return path.rsplit(os.sep, 1)[-1]

    def extension(path):
        return path.rsplit(".", 1)[-1]

    def basename_(path):
        return path.rsplit(os.sep, 1)[-1].rsplit(".", 1)[0]

    def dirname(path):
        return path.rsplit(os.sep, 1)[0]

    def join(*args):
        pathlist = []
        for i in args: pathlist.append(i)
        return os.sep.join(pathlist)


def quickResolution(file):
    try:
        return imagesize.get(file)
    except:
        try:
            return Image.open(file).size
        except:
            height, width, color = cv2.imread(file).shape
            return width, height


def getpid():
    return int(multiprocessing.current_process().name.rsplit("-", 1)[-1])


class imgBackend:  # * image processing backends
    def cv2(pid, path, HR, LR, suffix):
        image = cv2.imread(path)
        printPath = ospath.basename(path)
        time = os.path.getmtime(path)
        if not os.path.exists(HR):
            thread_status(pid, printPath, extra=pBar(1, 2, 2, suff=suffix))
            cv2.imwrite(HR, image)
            os.utime(HR, (time, time))
        if not os.path.exists(LR):
            thread_status(pid, printPath,extra=pBar(2, 2, 2, suff=suffix))
            lowRes = cv2.resize(
                image, (0, 0), fx=1/args.scale, fy=1/args.scale)
            cv2.imwrite(LR, lowRes)
            os.utime(LR, (time, time))

    def image(pid, path, HR, LR, suffix):
        image = Image.open(path)
        printPath = ospath.basename(path)
        time = os.path.getmtime(path)
        if not os.path.exists(HR):
            thread_status(pid, printPath,
                          extra=pBar(1, 2, 2,
                                     suff=suffix))
            image.save(HR)
            os.utime(HR, (time, time))
        if not os.path.exists(LR):
            thread_status(pid, printPath,
                          extra=pBar(2, 2, 2,
                                     suff=suffix))
            image.resize((int(image.width / args.scale),
                          int(image.height / args.scale))).save(LR)
            os.utime(LR, (time, time))


if __name__ == "__main__":
    # Get backend to use for converting
    backend = None
    if args.backend.lower() in ['cv2', 'opencv', 'opencv2', 'opencv-python']: backend = imgBackend.cv2
    if args.backend.lower() in ['pil', 'pillow', 'image']: backend = imgBackend.image
    assert backend, "Invalid backend chosen. Please write 'cv2', or 'pil'."

    # Handle arguments
    # * args.Extension
    print(f"using {args.power} threads")
    if args.extension.startswith("."): args.extension = args.extension[1:]
    if args.extension != "same":
        print(f"applying extension: .{args.extension}")
        customExtension = True
    else:
        customExtension = False

    def nextStep(index, text):
        print(f"\033[K{str(index)}. {text}", end="\n\033[K")

    def get_files(*args):  # run glob.glob multiple times and return them all in a single list
        fileList = []
        for path in args: fileList += glob.glob(path, recursive=True)
        return fileList

    # * args.input
    imgList = sorted(get_files(args.input+"/**/*.png", args.input+"/**/*.jpg", args.input+"/**/*.webp"))
    HRFolder = os.path.join(os.path.dirname(args.input), str(args.scale)+"x") + "HR"
    LRFolder = os.path.join(os.path.dirname(args.input), str(args.scale)+"x") + "LR"
    if customExtension:
        HRFolder += "-"+args.extension
        LRFolder += "-"+args.extension
    if not os.path.exists(HRFolder): os.makedirs(HRFolder)
    if not os.path.exists(LRFolder): os.makedirs(LRFolder)
    if args.purge:
        print("purging all existing files in output directories...")
        for index in sorted(get_files(HRFolder+"*", LRFolder+"*")): os.remove(index)
    
    # End Handle arguments


    HRList = sorted([ospath.basename_(f) for f in get_files(HRFolder + "**/*")])
    LRList = sorted([ospath.basename_(f) for f in get_files(LRFolder + "**/*")])
    # indexing # to index the input as keys for first 4 characters of every string
    # HRIndexed = {f[:4]: [i for i in HRList if i[:4] == f[:4]] for f in set([i[:4] for i in HRList])}
    # LRIndexed = {f[:4]: [i for i in LRList if i[:4] == f[:4]] for f in set([i[:4] for i in LRList])}
    
    def filterSaved(i):
        index, item = i
        pid = getpid()
        thread_status(pid, ospath.basename(item), pBar(index, len(imgList), suff=f" {index}/{len(imgList)}"))
        name = ospath.basename_(item)
        if name not in HRList and name not in LRList: return item

    def gatherPaths(i):
        index, item = i
        pid = getpid() - args.power
        ext = f".{str(args.extension if customExtension else ospath.extension(item))}"
        thread_status(pid, ospath.basename(item),
                      extra=pBar(index, len(imgList), suff=f" {index}/{len(imgList)}"))
        return {'index': index, 'path': item, 'res': quickResolution(item),
                'HR': ospath.join(HRFolder, ospath.basename_(item)+ext),
                'LR': ospath.join(LRFolder, ospath.basename_(item)+ext)}

    def filterImages(i):
        index, item = i
        pid = getpid() - args.power*2
        thread_status(
            pid, item=ospath.basename(item['path']),
            extra=pBar(index, len(importDict), suff=f" {index}/{len(importDict)}"))
        width, height = item['res']
        if width % args.scale == 0 and height % args.scale == 0:
            if width >= args.minsize and height >= args.minsize:
                return importDict[index]

    def fileparse(imagedict):
        imagedict, method = imagedict
        pid = getpid() - args.power*3
        suffix = f" {str(imagedict['index']).rjust(len(str(len(imgList))))}"
        if not os.path.exists(imagedict['HR']) or not os.path.exists(imagedict['LR']):
            method(pid, path=imagedict['path'], HR=imagedict['HR'], LR=imagedict['LR'], suffix=suffix)

    nextStep(1, "Attempting to filter files that already exist in LRFolder")
    with Pool(processes=args.power) as p:
        maxlist = len(imgList)
        imgList = p.map(filterSaved, enumerate(imgList))
        imgList = [i for i in imgList if i is not None]
    nextStep("1a", f"{maxlist-len(imgList)} existing files, {len(imgList)} possible files")
    maxlist = len(imgList)
    nextStep(2, "Gathering image information")
    with Pool(processes=args.power) as p:
        importDict = list(p.map(gatherPaths, enumerate(imgList)))

    nextStep(3, f"Filtering out bad images ( too small, not /{args.scale} )")
    with Pool(processes=args.power) as p:
        imgList = p.map(filterImages, enumerate(importDict))
        imgList = [i for i in imgList if i is not None]

    nextStep("3a", f"{maxlist-len(imgList)} discarded files, {len(imgList)} new files")
    progressEvent(duration=3)

    try:
        nextStep(4, "Processing...")
        with Pool(processes=args.power) as p:
            imdict = p.map(fileparse, [(i, backend) for i in imgList])
        p.close()
    except KeyboardInterrupt:
        p.close()
        p.join()
        print("\n"*args.power+"Conversion cancelled")
    print("\nDone!")
