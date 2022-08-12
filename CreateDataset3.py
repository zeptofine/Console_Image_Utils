
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


def progressBar(iteration: int, total: int, length: int = os.get_terminal_size()[0]//2,
                Print=False, fill="#", nullp="-", corner="[]", color=True,
                end="\r", pref='', suff=''):
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
    command = f"\033[K{color2}{corner[0]}{color1}{bar}{color2}{corner[1]}\033[0m" if color else f"<{bar}>"
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


def multiprocessing_status(pid, item, extra="", extraSize=0):
    """Displays a status line for a specified process.
    pid: process id
    item: long text to display
    extra: extra text to display before listed item, such as 'Processing' or 'Thinking'
    """
    command = f"\033[K# {str(pid).rjust(3)}: {str(extra).center(extraSize)} | {item}"
    command = ("\n"*pid) + command + ("\033[A"*pid)
    print(command, end="\r")


if sys.platform == "win32":
    print("This application was made for linux/wsl. either use wsl or linux or this will not work. you have been warned.")
    progressEvent(10, length=20)


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


def multiprocessing_status(pid, item, extra="", extraSize=30):
    """Displays a status line for a specified process.
    pid: process id
    item: long text to display
    extra: extra text to display before listed item, such as 'Processing' or 'Thinking'
    """
    command = f"\033[K# {str(pid).rjust(3)}: {str(extra).center(extraSize)} | {item}"
    command = ("\n"*pid) + command + ("\033[A"*pid)
    print(command, end="\r")


class os_path():
    def basename(path):
        return path.rsplit(os.sep, 1)[-1]

    def basestname(path):
        return path.rsplit(os.sep, 1)[-1].rsplit(".", 1)[0]

    def dirname(path):
        return path.rsplit(os.sep, 1)[0]

    def extension(path):
        return path.rsplit(".", 1)[-1]


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
    existList1 = sorted([os_path.basestname(f)
                         for f in get_files(HRFolder + "**/*")])
    existList2 = sorted([os_path.basestname(f)
                         for f in get_files(LRFolder + "**/*")])

    def nextStep(index, text):
        print("\033[K"+str(index)+".", text, end="\n\033[K")

    def filterSaved(index):
        pid = getpid()
        multiprocessing_status(pid, os_path.basename(
            importList[index]),
            extra=progressBar(index, len(importList), 16, suff=f" {index}/{len(importList)}"))
        name = os_path.basestname(importList[index])
        if name not in existList1 and name not in existList2:
            return importList[index]

    def gatherPaths(index):
        pid = getpid() - args.power
        ext = f".{str(args.extension if customExtension else os_path.extension(importList[index]))}"
        res = quickResolution(importList[index])
        multiprocessing_status(pid, os_path.basename(importList[index]),
                               extra=progressBar(index, len(importList), 16, suff=f" {index}/{len(importList)}"))
        return {'index': index, 'path': importList[index],
                'HR': os.path.join(HRFolder, os_path.basestname(importList[index])+ext),
                'LR': os.path.join(LRFolder, os_path.basestname(importList[index])+ext),
                'res': res}

    def filterImages(index):
        pid = getpid() - args.power*2
        multiprocessing_status(
            pid, item=os_path.basename(importDict[index]['path']),
            extra=progressBar(index, len(importDict), 16, suff=f" {index}/{len(importDict)}"))
        width, height = importDict[index]['res']
        if width % args.scale and width % args.scale:
            if width >= args.minsize and height >= args.minsize:
                return importDict[index]

    nextStep(1, "Attempting to filter files that already exist in LRFolder")
    with Pool(processes=args.power) as p:
        maxlist = len(importList)
        importList = p.map(filterSaved, range(len(importList)))
        importList = [i for i in importList if i is not None]
        nextStep(
            "2a", f"{maxlist-len(importList)} existing files, {len(importList)} possible files")

    maxlist = len(importList)
    nextStep(2, "Gathering image information")
    with Pool(processes=args.power) as p:
        importDict = list(p.map(gatherPaths, range(len(importList))))
        importList = [i for i in importList if i is not None]

    nextStep(3, f"Filtering out bad images ( too small, not /{args.scale} )")
    with Pool(processes=args.power) as p:
        importList = p.map(filterImages, range(len(importDict)))
        importList = [i for i in importList if i is not None]

    importList = [i for i in importList if i is not None]
    nextStep(
        "3a", f"{maxlist-len(importList)} discarded files, {len(importList)} new files")
    progressEvent(duration=3)

    if args.purge:
        print("purging all existing files in output directories...")
        for index in sorted(glob.glob(HRFolder + "*")+glob.glob(LRFolder + "*")):
            os.remove(index)


# image processing backends
if args.backend.lower() in ['cv2', 'opencv', 'opencv2', 'opencv-python']:

    def fileConvert(pid, path, HR, LR):
        image = cv2.imread(path)
        printPath = os_path.basename(path)
        time = os.path.getmtime(path)
        if not os.path.exists(HR):
            multiprocessing_status(pid, printPath, extra=progressBar(1, 2, 6))
            cv2.imwrite(HR, image)
            os.utime(HR, (time, time))
        if not os.path.exists(LR):
            multiprocessing_status(pid, printPath, extra=progressBar(2, 2, 6))
            lowRes = cv2.resize(
                image, (0, 0), fx=1/args.scale, fy=1/args.scale)
            cv2.imwrite(LR, lowRes)
            os.utime(LR, (time, time))
elif args.backend.lower() in ['pil', 'pillow']:

    def fileConvert(pid, path, HR, LR):
        image = Image.open(path)
        printPath = os_path.basename(path)
        time = os.path.getmtime(path)
        if not os.path.exists(HR):
            multiprocessing_status(pid, printPath, extra=progressBar(1, 2, 6))
            image.save(HR)
            os.utime(HR, (time, time))
        if not os.path.exists(LR):
            multiprocessing_status(pid, printPath, extra=progressBar(2, 2, 6))
            image.resize((int(image.width / args.scale),
                          int(image.height / args.scale))).save(LR)
            os.utime(LR, (time, time))


def fileparse(imagedict):
    pid = getpid() - args.power*3
    multiprocessing_status(pid, os_path.basename(
        imagedict['path']), extra=progressBar(0, 2, 6))
    if not os.path.exists(imagedict['HR']) or not os.path.exists(imagedict['LR']):
        fileConvert(pid, path=imagedict['path'],
                    HR=imagedict['HR'], LR=imagedict['LR'])


if __name__ == "__main__":
    try:
        nextStep(4, "Processing...")
        with Pool(processes=args.power) as p:
            imdict = p.map(fileparse, importList)
        p.close()
        p.join()
    except KeyboardInterrupt:
        p.close()
        p.join()
        print("\n"*args.power+"Conversion cancelled")
    print("\nDone!")
