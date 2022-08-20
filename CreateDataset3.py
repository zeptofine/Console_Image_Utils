
import argparse
import glob
import multiprocessing
import os
import sys
import time
from multiprocessing import Pool
from pprint import pprint
# import rich

import cv2
import imagesize
from PIL import Image


def progressBar(iteration: int, total: int, length: int = max(os.get_terminal_size()[0]//6, 10),
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
    if length == 0:
        length = duration
    for second in range(1, duration):
        if suff != "":
            suff = f" {second} / {duration} "
        progressBar(second, duration, length, fill=fill, nullp=nullp,
                    corner=corner, color=True,
                    end=end, pref=pref, suff=f" {second} / {duration} ")
        time.sleep(1)


def multiprocessing_status(pid, item, extra="", extraSize=8):
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


if args.input[-1] == os.sep:  # strip slash from end of path if exists
    args.input = args.input[:-1]


class ospath():
    def basename(path):
        return path.rsplit(os.sep, 1)[-1]

    def basestname(path):
        return path.rsplit(os.sep, 1)[-1].rsplit(".", 1)[0]

    def dirname(path):
        return path.rsplit(os.sep, 1)[0]

    def extension(path):
        return path.rsplit(".", 1)[-1]

    def join(*args):
        pathlist = []
        for i in args:
            pathlist.append(i)
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


if __name__ == "__main__":
    print(f"using {args.power} threads")
    if args.extension[0] == ".":
        args.extension = args.extension[1:]
    if args.extension != "same":
        print(f"applying extension: .{args.extension}")
        customExtension = True
    else:
        customExtension = False

    def nextStep(index, text):
        print("\033[K"+str(index)+".", text, end="\n\033[K")

    def get_files(*args):
        fileList = []
        for path in args:
            fileList += glob.glob(path, recursive=True)
        return fileList

    importList = sorted(get_files(args.input+"/**/*.png",
                                  args.input+"/**/*.jpg",
                                  args.input+"/**/*.webp"))
    HRFolder = os.path.join(os.path.dirname(
        args.input), str(args.scale)+"x") + "HR"
    LRFolder = os.path.join(os.path.dirname(
        args.input), str(args.scale)+"x") + "LR"
    if customExtension:
        HRFolder += "-"+args.extension
        LRFolder += "-"+args.extension
    if not os.path.exists(HRFolder):
        os.makedirs(HRFolder)
    if not os.path.exists(LRFolder):
        os.makedirs(LRFolder)
    existList1 = sorted([ospath.basestname(f)
                         for f in get_files(HRFolder + "**/*")])
    existList2 = sorted([ospath.basestname(f)
                         for f in get_files(LRFolder + "**/*")])
# indexing
    # existList_1 = {f[:4]: [i for i in existList1 if i[:4] == f[:4]]
    #                for f in existList1}
    # existList_2 = {f[:4]: [i for i in existList2 if i[:4] == f[:4]]
    #                for f in existList2}
    # exit()

    def filterSaved(index):
        pid = getpid()
        multiprocessing_status(pid, ospath.basename(importList[index]),
                               progressBar(index, len(importList), suff=f" {index}/{len(importList)}"))
        name = ospath.basestname(importList[index])
        if name not in existList1 and name not in existList2:
            return importList[index]

    def gatherPaths(index):
        pid = getpid() - args.power
        item = importList[index]
        ext = f".{str(args.extension if customExtension else ospath.extension(item))}"
        multiprocessing_status(pid, ospath.basename(importList[index]),
                               extra=progressBar(index, len(importList), suff=f" {index}/{len(importList)}"))
        return {'index': index, 'path': item,
                'HR': ospath.join(HRFolder, ospath.basestname(item)+ext),
                'LR': ospath.join(LRFolder, ospath.basestname(item)+ext),
                'res': quickResolution(item)}

    def filterImages(index):
        pid = getpid() - args.power*2
        multiprocessing_status(
            pid, item=ospath.basename(importDict[index]['path']),
            extra=progressBar(index, len(importDict), suff=f" {index}/{len(importDict)}"))
        width, height = importDict[index]['res']
        if width % args.scale == 0 and height % args.scale == 0:
            if width >= args.minsize and height >= args.minsize:
                return importDict[index]

    nextStep(1, "Attempting to filter files that already exist in LRFolder")
    with Pool(processes=args.power) as p:
        maxlist = len(importList)
        importList = p.map(filterSaved, range(len(importList)))
        importList = [i for i in importList if i is not None]
        nextStep(
            "1a", f"{maxlist-len(importList)} existing files, {len(importList)} possible files")

    maxlist = len(importList)
    nextStep(2, "Gathering image information")
    with Pool(processes=args.power) as p:
        importDict = list(p.map(gatherPaths, range(len(importList))))

    nextStep(3, f"Filtering out bad images ( too small, not /{args.scale} )")
    with Pool(processes=args.power) as p:
        importList = p.map(filterImages, range(len(importDict)))
        importList = [i for i in importList if i is not None]

    nextStep(
        "3a", f"{maxlist-len(importList)} discarded files, {len(importList)} new files")
    progressEvent(duration=3)

    if args.purge:
        print("purging all existing files in output directories...")
        for index in sorted(glob.glob(HRFolder + "*")+glob.glob(LRFolder + "*")):
            os.remove(index)

    # print(importList)
# image processing backends
if args.backend.lower() in ['cv2', 'opencv', 'opencv2', 'opencv-python']:

    def fileConvert(pid, path, HR, LR, suffix):
        image = cv2.imread(path)
        printPath = ospath.basename(path)
        time = os.path.getmtime(path)
        if not os.path.exists(HR):
            multiprocessing_status(
                pid, printPath, extra=progressBar(1, 2, 2, suff=suffix))
            cv2.imwrite(HR, image)
            os.utime(HR, (time, time))
        if not os.path.exists(LR):
            multiprocessing_status(
                pid, printPath, extra=progressBar(2, 2, 2, suff=suffix))
            lowRes = cv2.resize(
                image, (0, 0), fx=1/args.scale, fy=1/args.scale)
            cv2.imwrite(LR, lowRes)
            os.utime(LR, (time, time))
elif args.backend.lower() in ['pil', 'pillow']:

    def fileConvert(pid, path, HR, LR, suffix):
        image = Image.open(path)
        printPath = ospath.basename(path)
        time = os.path.getmtime(path)
        if not os.path.exists(HR):
            multiprocessing_status(
                pid, printPath, extra=progressBar(1, 2, 2, suff=suffix))
            image.save(HR)
            os.utime(HR, (time, time))
        if not os.path.exists(LR):
            multiprocessing_status(
                pid, printPath, extra=progressBar(2, 2, 2, suff=suffix))
            image.resize((int(image.width / args.scale),
                          int(image.height / args.scale))).save(LR)
            os.utime(LR, (time, time))


def fileparse(imagedict):
    pid = getpid() - args.power*3
    suffix = f" {str(imagedict['index']).rjust(len(str(len(importList))))}"
    if not os.path.exists(imagedict['HR']) or not os.path.exists(imagedict['LR']):
        fileConvert(pid, path=imagedict['path'],
                    HR=imagedict['HR'], LR=imagedict['LR'], suffix=suffix)


if __name__ == "__main__":
    try:
        nextStep(4, "Processing...")
        with Pool(processes=args.power) as p:
            imdict = p.map(fileparse, importList)
        p.close()
    except KeyboardInterrupt:
        p.close()
        p.join()
        print("\n"*args.power+"Conversion cancelled")
    print("\nDone!")
