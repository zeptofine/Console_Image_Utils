import argparse
import glob
import multiprocessing
import os
import time
import warnings
from multiprocessing import Pool
import cv2
import pymage_size
from PIL import Image

try:
    from tqdm import tqdm
    USE_CUSTOM_BAR = False
except ImportError:
    print("tqdm not found, it will not be available")
    USE_CUSTOM_BAR = True

parser = argparse.ArgumentParser()
parser.add_argument("-i", "--input", help="input directory",
                    required=True)
parser.add_argument("-x", "--scale", help="scale",
                    type=int, required=True)
parser.add_argument("-r", "--no_recursive", help="disables recursive",
                    action="store_true", required=False)
parser.add_argument("-p", "--power", help="number of cores to use. default is 'os.cpu_count()'.",
                    type=int, default=int(os.cpu_count()/4*3), required=False)
parser.add_argument("--minsize", help="minimum size of image",
                    type=int, default=0, required=False)
parser.add_argument("--tqdm_bar", help="use tqdm progress bar. glitchy.",
                    action="store_false", required=False)
parser.add_argument("-e", "--extension", help="extension of files to export. jpeg, png, webp, etc. it's the same as input by default.",
                    default="same", required=False)
parser.add_argument("--backend", help="backend to use for resizing. [cv2], PIL. cv2 is safer but slower in my experience.",
                    default="cv2", required=False)
parser.add_argument("--purge", help="purge all existing files in output directories before processing",
                    default=False, action="store_true", required=False)
args = parser.parse_args()


if args.power == os.cpu_count()/4*3:
    print("using default number of processes: "+str(int(os.cpu_count()/4*3)))
else:
    print(f"using {args.power} simultaneous processes")
if args.anonymous:
    import random
    import string
if args.extension:  # strip period if exists
    if args.extension[0] == ".":
        args.extension = args.extension[1:]
    print(f"applying extension: .{args.extension}")

# strip slash from end of path if exists
if args.input[-1] == "/":
    args.input = args.input[:-1]

if args.tqdm_bar:
    USE_CUSTOM_BAR = True

HRFolder = os.path.dirname(args.input) + "/" + str(args.scale) + \
    "xHR" + ("-."+args.extension if args.extension else "") + "/"
LRFolder = os.path.dirname(args.input) + "/" + str(args.scale) + \
    "xLR" + ("-."+args.extension if args.extension else "") + "/"
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

def get_files(path):
    return glob.glob(path, recursive=True) 

# for every recursive directory in the input directory, create a folder in HR and Lr
print("gathering files...")

import_list = [i[1] for i in sorted(
    [(f.rsplit("/", 1)[-1], f) for f in sorted(get_files(args.input + "/**/*.png")
                                             + get_files(args.input + "/**/*.jpg")
                                             + get_files(args.input + "/**/*.webp"))], reverse=True)]
print("attempting to filter files that already exist in LRFolder...")
existed_list1 = sorted([f.rsplit("/", 1)[-1].rsplit(".", 1)[0]
                        for f in get_files(HRFolder + "**/*")])
existed_list2 = sorted([f.rsplit("/", 1)[-1].rsplit(".", 1)[0]
                        for f in get_files(LRFolder + "**/*")])
existed_list = []
# loop through both, and if the file name is in both, add it to existed_list
for i in tqdm(existed_list1):
    if i in existed_list2:
        existed_list.append(i)
import_list = [i for i in tqdm(import_list) if not i.rsplit(
    "/", 1)[-1].rsplit(".", 1)[0] in existed_list]
if not args.no_recursive:
    for i in get_files(args.input + "**/*"):
        if os.path.isdir(i):
            if not os.path.exists(HRFolder + str.replace(i, args.input, "")):
                os.makedirs(HRFolder + str.replace(i, args.input, ""))
            if not os.path.exists(LRFolder + str.replace(i, args.input, "")):
                os.makedirs(LRFolder + str.replace(i, args.input, ""))


def multiprocessing_status(pid, listnum=0, inlist=["0"], extra=""):
    """Displays a status line for a specified process.
    pid: process id 
    listnum: list index 
    inlist: list of items processing
    extra: extra text to display before listed item, such as 'Processing' or 'Thinking'
    """
    extra = extra.ljust(12)
    statusimage = inlist[listnum]
    command = f"\033[K"+str(pid), " "+": # " \
        + f"{str(listnum).rjust(len(str(len(inlist))), ' ')}"                                   # process number
    if extra != "":
        # extra text
        command += f" : {extra} | "
    # use original path
    path = statusimage
    command += f"...{path[-os.get_terminal_size().columns+len(command)+5:]}" if len(
        path) > os.get_terminal_size().columns-5 else path                                      # display path
    command = "\r"+("\033[A"*pid) + command + ("\n"*pid)+"\r"
    print(command, end="\r")


if args.backend.lower() in ["cv2", "opencv", "opencv2", "opencv-python"]:
    """Image Parser: cv2 edition"""
    class Imparser():
        def Imageread(i):
            return cv2.imread(i)

        def ConvertImages(i, Ho, Lo, original_path, index, total_list, pid):
            if not os.path.exists(Ho):
                multiprocessing_status(
                    pid=pid, listnum=index, inlist=total_list, extra="HR")
                cv2.imwrite(Ho, i)
            difference = ""
            if not os.path.exists(Lo):
                multiprocessing_status(
                    pid=pid, listnum=index, inlist=total_list, extra="LR")
                LoRes = cv2.resize(i, (0, 0), fx=1/args.scale, fy=1/args.scale)
                cv2.imwrite(Lo, LoRes)
                # get difference between original and resized
                LoRes = cv2.resize(LoRes, (0, 0), fx=args.scale, fy=args.scale)

            time = os.path.getmtime(original_path)
            os.utime(Ho, (time, time))
            os.utime(Lo, (time, time))

        def CropImage(i, x, y):
            return i[0:y, 0:x]

elif args.backend.lower() in ["pil", "pillow"]:
    """Image parser: Pillow edition"""
    class Imparser():
        def Imageread(i):
            return Image.open(i)

        def ConvertImages(i, Ho, Lo, original_path, index, total_list, pid):
            if not os.path.exists(Ho):
                multiprocessing_status(
                    pid=pid, listnum=index, inlist=total_list, extra="HR")
                i.save(Ho)
            if not os.path.exists(Lo):
                multiprocessing_status(
                    pid=pid, listnum=index, inlist=total_list, extra="LR")
                i.resize((int(i.width / args.scale),
                          int(i.height / args.scale))).save(Lo)
            time = os.path.getmtime(original_path)
            os.utime(Ho, (time, time))
            os.utime(Lo, (time, time))

        def CropImage(i, x, y):
            return i.crop((x, y, x+i.width, y+i.height))


def GetFileResolution(i):
    img_size = pymage_size.get_image_size(i).get_dimensions()
    return img_size[0], img_size[1]


print("Starting...")
if not args.no_status:
    print("\nSkipping files...", "\n"*(args.power-1),
          end="")


def inputparse(index):
    f = import_list[index]

    filename = {"name": f.rsplit("/", 1)[-1].rsplit(".", 1)[0],
        "ext": args.extension if args.extension else f.rsplit("/", 1)[-1].rsplit(".", 1)[-1],
        "relpath": f.replace(args.input, "")}
    HRout = (HRFolder + filename["relpath"] if not args.no_recursive else HRFolder +
             filename["name"]) + "." + filename["ext"]
    LRout = (LRFolder + filename["relpath"] if not args.no_recursive else LRFolder +
             filename["name"]) + "." + filename["ext"]
    difference = ""
    if not os.path.exists(HRout) or not os.path.exists(LRout):  # check if file exists
        width, height = GetFileResolution(f)
        width, height = int(width), int(height)
        if height >= args.minsize and width >= args.minsize:

            process_id = int(
                multiprocessing.current_process().name.rsplit("-", 1)[-1])
            if not width % args.scale == 0 or not height % args.scale == 0:
                width, height = width - (width % args.scale), height - (height % args.scale)
                if not height >= args.minsize or width >= args.minsize:
                    return
                image = Imparser.Imageread(f)
                image = Imparser.CropImage(image, width, height)
            else:
                image = Imparser.Imageread(f)
            if image is None:
                return
            Imparser.ConvertImages(
                image, HRout, LRout, f, index, import_list,
                process_id)

    if USE_CUSTOM_BAR:
        if index != 0:  # index / total, %, elapsed, eta, average per second
            time_elapsed = time.time() - start_time
            eta = (time_elapsed / index) * (len(import_list) - index)
            average_per_second = index / time_elapsed
            print(f"\033[K~{str(index).rjust(len(str(len(import_list))), ' ')}/{str(len(import_list))}:",  # index / total
                  f": {str((index/len(import_list))*100)[:6]}%",  # percentage
                  f": {str(time_elapsed)[:6]}"  # elapsed time
                  + f"/{str(eta)[:6]} s/eta",  # eta
                  f": {str(average_per_second)[:6]}it/s" if average_per_second > 1 else f" : {str(time_elapsed / index)[:6]}s/it",
                  end="\r")  # average per second


start_time = time.time()
with Pool(args.power) as pool:
    try:
        if USE_CUSTOM_BAR:
            poolThreads = list(pool.imap(inputparse, range(len(import_list))))
        else:
            poolThreads = list(tqdm(pool.imap(inputparse, range(len(import_list))),
                          ncols=0,
                          total=len(import_list),
                          desc="Progress",
                          unit=" images"))
    except KeyboardInterrupt:
        pool.close()
        pool.terminate()
        pool.join()
        print("\nKeyboardInterrupt detected, skipping...")
        print("\033[0;93m\033[1mWARNING: SOME IMAGES MAY BE CORRUPTED. check the newest files in the HR and LR folders")
if not args.no_recursive: # find empty folders in HR and Lr
    print("Removing empty folders in HR and Lr...")
    for i in get_files(HRFolder + "/*"):
        if not os.listdir(i):
            os.rmdir(i)
    for i in get_files(LRFolder + "/*"):
        if not os.listdir(i):
            os.rmdir(i)
print("\nDone!")
