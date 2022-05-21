import argparse
import glob
import os
from multiprocessing import Pool
emptymodules= []
try:
    from PIL import Image
except ImportError:
    emptymodules.append("PIL")
USE_CUSTOM_BAR = False
try:
    from tqdm import tqdm
except ImportError:
    print("tqdm not found, using custom progress bar...")
    USE_CUSTOM_BAR = True
try:
    import cv2
    from cv2 import cv2
except ImportError:
    emptymodules.append("cv2")

if not emptymodules == []:
    print("The following modules are not installed:")
    for i in emptymodules:
        print("    "+i)
    exit()

useExt = "same"
parser = argparse.ArgumentParser()
parser.add_argument(
    "-i", "--input", 
    help="input directory", 
    required=True
)
parser.add_argument(
    "-x", "--scale", 
    help="scale", 
    type=int, 
    required=True
    )
parser.add_argument(
    "-d", "--duplicate",
    help="duplicate [0],1 ([copy] / link) copying is better since it naturally error checks",
    type=int,
    default=1,
    required=False,
)
parser.add_argument(
    "-r", "--no_recursive",
    help="disables recursive",
    action="store_true",
    required=False,
)
parser.add_argument(
    "-p", "--power",
    help="number of cores to use. default is 'os.cpu_count()'.",
    type=int,
    default=12,
    required=False,
)
parser.add_argument(
    "-m", "--minsize", 
    help="minimum size of image", 
    type=int, 
    default=0, 
    required=False
)
parser.add_argument(
    "-b", "--bar",
    help="show custom progress bar. Already enabled if tqdm is not found.",
    action="store_true",
    required=False,
)
parser.add_argument(
    "-e", "--extension",
    help="extension of files to import. [same], jpeg, png, webp, etc.",
    default="same",
    required=False,
)
parser.add_argument(
    "-s", "--simulate",
    help="simulate running wihtout actually doing anything",
    action="store_true",
    required=False,
)
args = parser.parse_args()
if args.bar:
    USE_CUSTOM_BAR = True
if args.duplicate == 0:
    def IntoHR(i, o): os.link(i, o)
elif args.duplicate == 1:
    def IntoHR(i, o): cv2.imwrite(o, i)


if args.extension:
    if not args.extension == "same":
        # strip period if exists
        if args.extension[0] == ".":
            args.extension = args.extension[1:]
        useExt = args.extension
        print(f"extension: .{useExt}")


def intoLR(i, o):
    cv2.imwrite(o, cv2.resize(i, (0, 0), fx=1 / args.scale, fy=1 / args.scale))

# custom progress bar (slightly modified) [https://stackoverflow.com/questions/3173320/text-progress-bar-in-the-console]
def printProgressBar(
    iteration, total, length=100, fill="#", color1="\033[93m", color2="\033[92m"
):
    """
    iteration   - Required  : current iteration (Int)
    total       - Required  : total iterations (Int)
    length      - Optional  : character length of bar (Int)
    fill        - Optional  : bar fill character (Str)
    """
    filledLength = int(length * iteration // total)
    bar = fill * filledLength + "-" * (length - filledLength)
    print(f"\r{color2}<{color1}{bar}{color2}>\033[0m", end="\r")
    # Print New Line on Complete
    if iteration == total:
        print()


HRFolder = os.path.dirname(args.input) + "/" + str(args.scale) + "xHR"
LRFolder = os.path.dirname(args.input) + "/" + str(args.scale) + "xLR"
if not useExt == "same":
    HRFolder = HRFolder + "-." + useExt
    LRFolder = LRFolder + "-." + useExt
HRFolder = HRFolder + "/"
LRFolder = LRFolder + "/"
if not os.path.exists(HRFolder):
    os.makedirs(HRFolder)
if not os.path.exists(LRFolder):
    os.makedirs(LRFolder)


# for every recursive directory in the input directory, create a folder in HR and Lr
print("gathering files...")
# unless no_recursive is set
if not args.no_recursive:
    for i in tqdm(glob.glob(args.input + "**/*", recursive=True)):
        if os.path.isdir(i):
            if not os.path.exists(HRFolder + str.replace(i, args.input, "")):
                os.makedirs(HRFolder + str.replace(i, args.input, ""))
            if not os.path.exists(LRFolder + str.replace(i, args.input, "")):
                os.makedirs(LRFolder + str.replace(i, args.input, ""))

import_list = sorted(glob.glob(args.input + "/**/*.png", recursive=True) 
                    + glob.glob(args.input + "/**/*.jpg", recursive=True))
import_list = [
    i[1] for i in sorted(
        [(f.rsplit("/", 1)[-1], f) for f in sorted(
                glob.glob(args.input + "/**/*.png", recursive=True) 
                + glob.glob(args.input + "/**/*.jpg", recursive=True)
            )],
        reverse=True)]
# print(list(set([type(i) for i in import_list])))
#print(import_list)
#exit()
def inputparse(f):
    # for f in import_list:
    # parse file path
    filename = f.rsplit("/", 1)[-1]
    filename = filename.rsplit(".", 1)
    filext = filename[-1]
    filename = filename[0]
    relpath = f.replace(args.input, "")
    if args.simulate:
        image = Image.open(f)
        if image.size[0] < args.minsize or image.size[1] < args.minsize:
            image.small = str(args.minsize) + "> "
        else:
            image.small = str(args.minsize) + "< "
        print(f"{image.small}{image.size[0]:05}:{image.size[1]:05} : {f}")
    else:
        if not useExt == "same":
            filext = useExt
        if not args.no_recursive:
            HRout = HRFolder + relpath
            LRout = LRFolder + relpath
        else:
            HRout = HRFolder + filename
            LRout = LRFolder + filename
        HRout += "." + filext
        LRout += "." + filext
        if not os.path.exists(HRout) or not os.path.exists(LRout):
            imagepil = Image.open(f)
            width, height = imagepil.size
            # check if width and height is divisible by scale
            if width % args.scale == 0 and height % args.scale == 0:
                # check if image is large enough
                if height >= args.minsize and width >= args.minsize:
                    image = cv2.imread(f)
                    time = os.path.getmtime(f)
                    IntoHR(image, HRout)
                    intoLR(image, LRout)
                    os.utime(HRout, (time, time))
                    os.utime(LRout, (time, time))

                    if USE_CUSTOM_BAR:
                        index = import_list.index(f)
                        divitimput = str(index) + "/" + str(len(import_list))
                        # percent of progress, with 1 decimal
                        divitimputpercent = str(
                            round(index / len(import_list) * 100, 1)) + "%"
                        terminalsize = os.get_terminal_size()
                        termwidth = int(terminalsize.columns / 5 * 4)
                        HRFolderandpath = HRout
                        if (
                            len(
                                divitimput
                                + divitimputpercent
                                + HRFolderandpath
                                + '   '
                            )
                            > termwidth
                        ):
                            difference = (
                                len(
                                    divitimput
                                    + divitimputpercent
                                    + HRFolderandpath
                                    +'   '
                                    ) 
                                    - termwidth
                                    )
                            HRFolderandpath = "..." + HRout[difference:]
                        # print progress bar
                        print(f"\033[2A\033[2K{divitimput} {divitimputpercent} {HRFolderandpath}\n\033[2K",end="")
                        printProgressBar(index, len(import_list), length=termwidth)
                        print("")
                        # print("\033[1A\033[2K", divitimput, divitimputpercent, '->', HRFolderandpath)


print("Starting...\n\n")
# run through import_list unless backspace is pressed
try:
    with Pool(args.power) as p:
        if USE_CUSTOM_BAR:
            r = list(p.imap(inputparse, import_list))
        else:
            r = list(tqdm(p.imap(inputparse, import_list), total=len(import_list)))
except KeyboardInterrupt:
    print("\nKeyboardInterrupt detected, skipping...")
    print("\033[0;93m\033[1mWARNING: SOME IMAGES MAY BE CORRUPTED. check the newest files in the HR and LR folders")
    print("( the modified times should be the same, but the creation times aren't transfered )\033[0m")
# find empty folders in HR and Lr
if not args.no_recursive:
    print("Removing empty folders in HR and Lr...")
    for i in glob.glob(HRFolder + "/*", recursive=True):
        if not os.listdir(i):
            os.rmdir(i)
    for i in glob.glob(LRFolder + "/*", recursive=True):
        if not os.listdir(i):
            os.rmdir(i)
print("\n\nDone!")
