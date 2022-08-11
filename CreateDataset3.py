
import argparse
import glob
import multiprocessing
import os
import sys
from multiprocessing import Pool
from pprint import pprint

import cv2
from PIL import Image

parser = argparse.ArgumentParser()
parser.add_argument("-i", "--input", help="input directory", required=True)
parser.add_argument("-x", "--scale", help="scale", type=int, required=True)
parser.add_argument("-p", "--power", help="number of cores to use. default is 'os.cpu_count()'.",
                    type=int, default=int((os.cpu_count()/2)), required=False)
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
    listnum: list index
    inlist: list of items processing
    extra: extra text to display before listed item, such as 'Processing' or 'Thinking'
    """
    extra = extra.ljust(12)

    command = f"\033[K"+str(pid)+" : # "
    print(command)
    command += f": {extra} | "
    path = item
    command += f"...{path[-os.get_terminal_size().columns+len(command)+5:]}" if len(
        path) > os.get_terminal_size().columns-5 else path
    if sys.platform == "linux":
        command = "\r"+("\033[A"*pid) + command + ("\n"*pid)+"\r"
    print(command, end="\r")


class path():
    def basename(path):
        return path.rsplit(os.sep, 1)[-1]

    def dirname(path):
        return path.rsplit(os.sep, 1)[0]


def quickResolution(path):
    image = Image.open(path)
    return image.size


if __name__ == "__main__":
    print(f"using {args.power} threads")
    if args.extension[0] == ".":
        args.extension = args.extension[1:]
    if args.extension != "same":
        print(f"applying extension: .{args.extension}")
        custom_extension = True
    else:
        custom_extension = False

    def get_files(path):
        return glob.glob(path, recursive=True)

    importList = [i[1] for i in sorted(
        [(f.rsplit(os.sep, 1)[-1], f) for f in sorted(get_files(args.input + "/**/*.png")
                                                      + get_files(args.input + "/**/*.jpg")
                                                      + get_files(args.input + "/**/*.webp"))], reverse=True)]
    print(os.path.dirname(args.input), args.scale, args.extension)
    print(os.path.join(os.path.dirname(args.input), str(args.scale)+"x"))
    HRFolder = os.path.join(os.path.dirname(
        args.input), str(args.scale)+"x") + "HR"
    LRFolder = os.path.join(os.path.dirname(
        args.input), str(args.scale)+"x") + "LR"
    if custom_extension:
        HRFolder += "-"+args.extension
        LRFolder += "-"+args.extension
    for file in range(len(importList)):
        importList[file] = {'index': file,
                            'path': importList[file],
                            'HR': os.path.join(HRFolder, path.basename(importList[file])),
                            'LR': os.path.join(LRFolder, path.basename(importList[file])),
                            'res': quickResolution(importList[file])}
    pprint(importList)
    if not os.path.exists(HRFolder):
        os.makedirs(HRFolder)
    if not os.path.exists(LRFolder):
        os.makedirs(LRFolder)
    if args.purge:
        print("purging all existing files in output directories...")
        for i in glob.glob(HRFolder + "*"):
            os.remove(i)
        for i in glob.glob(LRFolder + "*"):
            os.remove(i)

    # pprint(import_list)

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
                cv2.imwrite(HR, image)
            if not os.path.exists(LR):
                lowRes = cv2.resize(
                    image, (0, 0), fx=1/args.scale, fy=1/args.scale)
                cv2.imwrite(LR, lowRes)
            time = os.path.getmtime(path)
            os.utime(HR, (time, time))
            os.utime(LR, (time, time))
            multiprocessing_status(pid, path)

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
                image.save(HR)
            if not os.path.exists(LR):
                image.resize((int(image.width / args.scale),
                              int(image.height / args.scale))).save(LR)
            multiprocessing_status(pid, path)


def fileparse(imagedict):
    if not os.path.exists(imagedict['HR']) or not os.path.exists(imagedict['LR']):
        # get image resolution
        if imagedict['res'] is None:
            image = imageHandler.read(imagedict['path'])
            width, height = imageHandler.resolution(image)
        else:
            image = None
            width, height = imagedict['res']
        width, height = int(width), int(height)
        # check if it's large enough
        if height >= args.minsize and width >= args.minsize:
            if image is None:
                image = imageHandler.read(imagedict['path'])
            pid = int(
                multiprocessing.current_process().name.rsplit("-", 1)[-1])
            if not width % args.scale == 0 or not height % args.scale == 0:
                width = width - (width % args.scale)
                height = height - (height % args.scale)
                if not height >= args.minsize or width >= args.minsize:
                    return
                image = imageHandler.cropImage(image, width, height)
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
