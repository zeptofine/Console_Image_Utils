import os, glob, argparse
from tqdm import tqdm
from multiprocessing import Pool
import cv2
parser=argparse.ArgumentParser()
parser.add_argument('-i','--input',help='input directory',required=True)
parser.add_argument('-x','--scale',help='scale',type=int, required=True)
parser.add_argument('-d','--duplicate', help='duplicate [0],1 ([copy] / link) copying is better since it naturally error checks', 
                    type=int, default=1, required=False)
parser.add_argument('-r','--no_recursive', help='disables recursive', action='store_true', required=False)
parser.add_argument('-p','--power', help='cpucount/power; 2 = half of the cores, 4 = a quarter', type=int, default=1, required=False)
parser.add_argument('-m', '--minsize', help='minimum size of image', type=int, default=0, required=False)
args=parser.parse_args()

# make a function whether to copy or link
if args.duplicate==0:
    def IntoHR(i, o):
        os.link(i, o)
elif args.duplicate==1:
    def IntoHR(i, o):
        cv2.imwrite(o, cv2.imread(i))

HRFolder=os.path.dirname(args.input)+'/'+str(args.scale)+'xHR'
LRFolder=os.path.dirname(args.input)+'/'+str(args.scale)+'xLR'
if not os.path.exists(HRFolder):
    os.makedirs(HRFolder)
if not os.path.exists(LRFolder):
    os.makedirs(LRFolder)

# for every recursive directory in the input directory, create a folder in HR and Lr
# unless no_recursive is set
if not args.no_recursive:
    for i in tqdm(glob.glob(args.input+'**/*', recursive=True)):
        if os.path.isdir(i):
            if not os.path.exists(HRFolder+str.replace(i, args.input, '')):
                os.makedirs(HRFolder+str.replace(i, args.input, ''))
            if not os.path.exists(LRFolder+str.replace(i, args.input, '')):
                os.makedirs(LRFolder+str.replace(i, args.input, ''))

import_list = glob.glob(args.input+'/**/*.png', recursive=True)
import_list+= glob.glob(args.input+'/**/*.jpg', recursive=True)
import_list = sorted(import_list)
def intoLR(i, o):
    # downscale by args.scale
    cv2.imwrite(o, cv2.resize(cv2.imread(i), (0,0), fx=1/args.scale, fy=1/args.scale))
def inputparse(i):
    file=str.replace(i, args.input, '')
    if args.no_recursive:
        filepath=file.split('/')[-1]
        filepath='/'+filepath
    else:
        filepath=file
    if not os.path.exists(HRFolder+filepath) or not os.path.exists(LRFolder+filepath):
        img=cv2.imread(i)
        height, width, channels = img.shape
        if not height%args.scale==0 or not width%args.scale==0: return
        if height>=args.minsize and width>=args.minsize:
            IntoHR(i, HRFolder+filepath)
            if not os.path.exists(LRFolder+filepath):
                intoLR(i, LRFolder+filepath)
        else: return
    # replace new creation time with old modification time if it is not already the same.
    time=os.path.getmtime(i)
    if time != os.path.getmtime(HRFolder+filepath):
        os.utime(HRFolder+filepath, (time, time))
    if time != os.path.getmtime(LRFolder+filepath):
        os.utime(LRFolder+filepath, (time, time))

print('Starting')
# run through import_list
with Pool(int(os.cpu_count()/args.power)) as p:
    r = list(tqdm(p.imap(inputparse,import_list),total=len(import_list)))

# find empty folders in HR and Lr
if not args.no_recursive:
    print("Removing empty folders in HR and Lr...")
    for i in tqdm(glob.glob(HRFolder+'/*', recursive=True)):
        if not os.listdir(i):
            os.rmdir(i)
    for i in tqdm(glob.glob(LRFolder+'/*', recursive=True)):
        if not os.listdir(i):
            os.rmdir(i)
print("Done!")