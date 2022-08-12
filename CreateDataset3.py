
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
import rich
from PIL import Image
from tqdm import tqdm

parser = argparse.ArgumentParser()
parser.add_argument("-i", "--input", help="input directory", required=True)
parser.add_argument("-x", "--scale", help="scale", type=int, required=True)
parser.add_argument("-p", "--power", help="number of cores to use. default is 'os.cpu_count()'.",
                    type=int, default=int(((os.cpu_count()/4)*3)), required=False)
parser.add_argument("--minsize", help="minimum size of image",
                    type=int, default=0, required=False)
parser.add_argument("-e", "--extension", help="extension of files to export. jpeg, png, webp, etc. it's the same as input by default.",
                    default="same", required=False)
parser.add_argument("--backend", help="backend to use for resizing. [cv2], PIL. cv2 is safer but slower in my experience.",
                    default="cv2", required=False)
parser.add_argument("--purge", help="purge all existing files in output directories before processing",
                    default=False, action="store_true", required=False)
args = parser.parse_args()


if args.input[-1] == "/":  # strip slash from end of path if exists
    args.input = args.input[:-1]


def multiprocessing_status(pid, item, extra=""):
    """Displays a status line for a specified process.
    pid: process id
    item: long text to display
    extra: extra text to display before listed item, such as 'Processing' or 'Thinking'
    """
    command = f"\033[K# {str(pid).rjust(len(str(args.power)))}: {str(extra).center(25)} | {item}"
    command = ("\n"*pid) + command + ("\033[A"*pid)
    print(command, end="\r")


def printProgressBar(printing=True, iteration=0, total=1000, length=100, fill="#", nullp="-", corner="[]", color=True, end="\r", pref='', suff=''):
    """iteration   - Required  : current iteration (Int)
    total       - Required  : total iterations (Int)
    length      - Optional  : character length of bar (Int)
    fill        - Optional  : bar fill character (Str)"""
    # custom progress bar (slightly modified) [https://stackoverflow.com/questions/3173320/text-progress-bar-in-the-console]
    color1 = "\033[93m"
    color2 = "\033[92m"
    filledLength = int(length * iteration // total)
    fill = (fill*length)[:filledLength]
    nullp = (nullp*(length - filledLength))
    bar = fill + nullp
    command = f"{color2}{corner[0]}{color1}{bar}{color2}{corner[1]}\033[0m" if color else f"<{bar}>"
    command = pref+command+suff
    if printing:
        print(command, end=end)
    if iteration == total:
        print()
    return command


def progressEvent(duration, length=0, fill="#", nullp="-", corner="[]", color=True, end="\r", pref='', suff=''):
    if length == 0:
        length = duration+2
    for i in range(1, duration):
        printProgressBar(iteration=i, length=length, total=duration, fill=fill, nullp=nullp,
                         corner=corner, color=True, end=end, pref=pref, suff=f" {i} / {duration} ")
        time.sleep(1)


class path():
    def basename(path):
        return path.rsplit(os.sep, 1)[-1]

    def basestname(path):
        return path.rsplit(os.sep, 1)[-1].rsplit(".", 1)[0]

    def dirname(path):
        return path.rsplit(os.sep, 1)[0]

    def extension(path):
        return path.rsplit(".", 1)[-1]


def quickResolution(file):
    return imagesize.get(file)  # (width, height)


if __name__ == "__main__":
    print(f"using {args.power} threads")
    if args.extension[0] == ".":
        args.extension = args.extension[1:]
    if args.extension != "same":
        print(f"applying extension: .{args.extension}")
        customExtension = True
    else:
        customExtension = False

    def get_files(path):
        return glob.glob(path, recursive=True)

    importList = sorted(get_files(args.input + "/**/*.png")
                        + get_files(args.input + "/**/*.jpg")
                        + get_files(args.input + "/**/*.webp"))
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
    existList1 = sorted([path.basestname(f)
                         for f in get_files(HRFolder + "**/*")])
    existedList2 = sorted([path.basestname(f)
                           for f in get_files(LRFolder + "**/*")])

    print("attempting to filter files that already exist in LRFolder")
    for i in importList:
        name = path.basestname(i)
        if name in existList1 and name in existedList2:
            importList.remove(i)
    importList.sort()

    def getpid():
        return int(multiprocessing.current_process().name.rsplit("-", 1)[-1])

    def gatherPaths(index):
        ext = f".{str(args.extension if customExtension else path.extension(importList[index]))}"
        res = quickResolution(importList[index])
        pid = getpid()
        # printProgressBar(iteration=index, total=len(importList),
        #                  corner="[]", length=48,
        #                  suff=f" {index}/{len(importList)}")
        extra = printProgressBar(iteration=index, total=len(importList),
                                 printing=False, corner="[]", length=16,
                                 suff=f" {index}/{len(importList)}")
        multiprocessing_status(pid, path.basename(
            importList[index]), extra=extra)
        return {'index': index, 'path': importList[index],
                'HR': os.path.join(HRFolder, path.basestname(importList[index])+ext),
                'LR': os.path.join(LRFolder, path.basestname(importList[index])+ext),
                'res': res}

    def filterImages(index):
        pid = getpid()-args.power
        extra = printProgressBar(iteration=index, total=len(importDict),
                                 printing=False, corner="[]", length=16,
                                 suff=f" {index}/{len(importDict)}")
        multiprocessing_status(
            pid, item=path.basename(importDict[index]['path']), extra=extra)
        width, height = importDict[index]['res']
        if width % args.scale and width % args.scale:
            if width >= args.minsize and height >= args.minsize:
                return importDict[index]

    def nextStep(index, text):
        print("\033[K"+str(index)+".", text, end="\n\033[K")
    nextStep(1, "Gathering image information")
    with Pool(processes=args.power) as p:
        importDict = list(p.map(gatherPaths, range(len(importList))))
    importList.clear()

    nextStep(2, f"Filtering out bad images ( too small, not /{args.scale} )")
    with Pool(processes=args.power) as p:
        importList = p.map(filterImages, range(len(importDict)))
        p.close()
        p.join()
    maxlist = len(importList)
    importList = [i for i in importList if i is not None]
    nextStep(
        "2a", f"{maxlist-len(importList)} invalid files, {len(importList)} valid files")
    progressEvent(duration=3)

    if args.purge:
        print("purging all existing files in output directories...")
        for i in sorted(glob.glob(HRFolder + "*")+glob.glob(LRFolder + "*")):
            os.remove(i)


# image processing backends
if args.backend.lower() in ['cv2', 'opencv', 'opencv2', 'opencv-python']:

    class imageHandler():
        def read(image):
            return cv2.imread(image)

        def resolution(image):
            height, width, color = image.shape
            return (width, height)

        def cropImage(image, x, y):
            return image[0:y, 0:x]

        def convert(image, imagedict, pid):
            path = imagedict['path']
            HR = imagedict['HR']
            LR = imagedict['LR']
            if not os.path.exists(HR):
                extra = printProgressBar(
                    printing=False, iteration=1, total=3, length=12)
                multiprocessing_status(pid, path, extra=extra)
                cv2.imwrite(HR, image)
            if not os.path.exists(LR):
                extra = printProgressBar(
                    printing=False, iteration=2, total=3, length=12)
                multiprocessing_status(pid, path, extra=extra)
                lowRes = cv2.resize(
                    image, (0, 0), fx=1/args.scale, fy=1/args.scale)
                cv2.imwrite(LR, lowRes)
            extra = printProgressBar(
                printing=False, iteration=3, total=3, length=12)
            multiprocessing_status(pid, path, extra=extra)
            time = os.path.getmtime(path)
            os.utime(HR, (time, time))
            os.utime(LR, (time, time))


elif args.backend.lower() in ['pil', 'pillow']:

    class imageHandler():
        def read(image):
            return Image.open(image)

        def resolution(image):
            return (image.size)  # (width, height)

        def cropImage(image, x, y):
            return image.crop((x, y, x+i.width, y+i.height))

        def convert(image, imagedict, pid):
            HR = imagedict['HR']
            LR = imagedict['LR']
            path = imagedict['path']
            if not os.path.exists(HR):
                extra = printProgressBar(
                    printing=False, iteration=1, total=3, length=12)
                multiprocessing_status(pid, path, extra=extra)
                image.save(HR)
            if not os.path.exists(LR):
                extra = printProgressBar(
                    printing=False, iteration=2, total=3, length=12)
                multiprocessing_status(pid, path, extra=extra)
                image.resize((int(image.width / args.scale),
                              int(image.height / args.scale))).save(LR)
            extra = printProgressBar(
                printing=False, iteration=3, total=3, length=12)
            multiprocessing_status(pid, path, extra=extra)


def fileparse(imagedict):
    pid = getpid()-args.power*2
    if not os.path.exists(imagedict['HR']) or not os.path.exists(imagedict['LR']):
        image = imageHandler.read(imagedict['path'])
        imageHandler.convert(image, imagedict, pid)


if __name__ == "__main__":
    try:
        with Pool(processes=args.power) as p:
            imdict = p.map(fileparse, importList)
    except KeyboardInterrupt:
        p.close()
        p.terminate()
        p.join()
        print("Conversion cancelled")
        # p.close()

        print("\nDone!")
