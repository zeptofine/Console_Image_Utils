import os
import glob
import shutil
from tqdm import tqdm
import argparse
from multiprocessing import Pool
import cv2

parser=argparse.ArgumentParser()
parser.add_argument('-i','--input',help='input directory',required=True)
parser.add_argument('-x','--scale',help='scale',type=int, required=True)
parser.add_argument('-d','--duplicate', help='duplicate [0],1 ([copy] / link) copying is better since it naturally error checks', 
                    type=int, default=1, required=False)
parser.add_argument('-r','--no_recursive', help='disables recursive', action='store_true', required=False)
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
# for every recursive directory in the input directory, create a folder in HR and Lr
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
    img=cv2.imread(i)
    height, width, channels = img.shape
    if not height%args.scale==0 and width%args.scale==0:
        return
    if not os.path.exists(HRFolder+file):
        IntoHR(i, HRFolder+file)
    if not os.path.exists(LRFolder+file):
        intoLR(i, LRFolder+file)
    # replace new creation time with old modification time if it is not already the same
    if os.path.getmtime(i) != os.path.getmtime(HRFolder+file):
        os.utime(HRFolder+file, (os.path.getmtime(i), os.path.getmtime(i)))

# run through import_list
with Pool(os.cpu_count()) as p:
    r = list(tqdm(p.imap(inputparse,import_list),total=len(import_list)))

# find empty folders in HR and Lr
for i in glob.glob(HRFolder+'/*', recursive=True):
    if not os.listdir(i):
        print("removing empty folder:", i)
        shutil.rmtree(i)
for i in glob.glob(LRFolder+'/*', recursive=True):
    if not os.listdir(i):
        print("removing empty folder:", i)
        shutil.rmtree(i)
