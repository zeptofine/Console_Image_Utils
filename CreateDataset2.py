import os
import os
import glob
import argparse
use_custom_bar = False
try:
    from tqdm import tqdm
except:
    print('tqdm not found, using custom progress bar...')
    use_custom_bar=True
from multiprocessing import Pool
try:
    import cv2
except:
    print('OpenCV is not installed. Please install it first.')
    exit()
usext = 'same'
parser=argparse.ArgumentParser()
parser.add_argument('-i','--input',help='input directory',required=True)
parser.add_argument('-x','--scale',help='scale',type=int, required=True)
parser.add_argument('-d','--duplicate', help='duplicate [0],1 ([copy] / link) copying is better since it naturally error checks', type=int, default=1, required=False)
parser.add_argument('-r','--no_recursive', help='disables recursive', action='store_true', required=False)
parser.add_argument('-p','--power', help='number of cores to use. default is \'os.cpu_count()\'.', type=int, default=12, required=False)
parser.add_argument('-m', '--minsize', help='minimum size of image', type=int, default=0, required=False)
parser.add_argument('-b', '--bar', help='show custom progress bar. Already enabled if tqdm is not found.', action='store_true', required=False)
parser.add_argument('-e', '--extension', help='extension of files to import. [same], jpeg, png, webp, etc.', default='same', required=False)
args=parser.parse_args()
if args.bar:
    use_custom_bar=True
if args.duplicate==0:
    def IntoHR(i, o):
        os.link(i, o)
elif args.duplicate==1:
    def IntoHR(i, o):
        cv2.imwrite(o, cv2.imread(i))
if args.extension:
    if not args.extension=='same':
        # strip period if exists
        if args.extension[0]=='.':
            args.extension=args.extension[1:]
        usext = args.extension
print(f"extension: .{usext}")
def intoLR(i, o):
    # downscale by args.scale
    cv2.imwrite(o, cv2.resize(cv2.imread(i), (0,0), fx=1/args.scale, fy=1/args.scale))
#custom progress bar (slightly modified) [https://stackoverflow.com/questions/3173320/text-progress-bar-in-the-console]
def printProgressBar (iteration, total, length = 100, fill = '#', printEnd = "\r"):
    """
    Call in a loop to create terminal progress bar
    @params:
        iteration   - Required  : current iteration (Int)
        total       - Required  : total iterations (Int)
        length      - Optional  : character length of bar (Int)
        fill        - Optional  : bar fill character (Str)
        printEnd    - Optional  : end character (e.g. "\r", "\r\n") (Str)
    """
    filledLength = int(length * iteration // total)
    bar = fill * filledLength + '-' * (length - filledLength)
    print(f'\r\033[92m<\033[93m{bar}\033[92m>\033[0m', end = printEnd)
    # Print New Line on Complete
    if iteration == total: 
        print()

HRFolder=os.path.dirname(args.input)+'/'+str(args.scale)+'xHR'
LRFolder=os.path.dirname(args.input)+'/'+str(args.scale)+'xLR'
if not usext=='same':
    HRFolder=HRFolder+'-.'+usext
    LRFolder=LRFolder+'-.'+usext
HRFolder=HRFolder+'/'
LRFolder=LRFolder+'/'
if not os.path.exists(HRFolder):
    os.makedirs(HRFolder)
if not os.path.exists(LRFolder):
    os.makedirs(LRFolder)

# for every recursive directory in the input directory, create a folder in HR and Lr
# unless no_recursive is set
print('gathering files...')
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
import_list2=[]
for f in import_list:
    fname=f.rsplit('/', 1)
    import_list2.insert(0, (fname[-1], fname[0]))
import_list2=sorted(import_list2)
import_list=[]
for f in import_list2:
    import_list.insert(0, f[1]+'/'+f[0])


def inputparse(f):
# for f in import_list:
    # parse f 
    file = f.rsplit('/', 1)
    filename = file[-1]
    filename = filename.rsplit('.', 1)
    filext = filename[-1]
    filename = filename[0]
    relpath = str.replace(f, args.input, '')
    if not usext=='same':
        filext = usext
    if not args.no_recursive:
        HRout = HRFolder+relpath
        LRout = LRFolder+relpath
    else: 
        HRout = HRFolder+filename
        LRout = LRFolder+filename
    HRout = HRout+'.'+filext
    LRout = LRout+'.'+filext
    if not os.path.exists(HRout) or not os.path.exists(LRout):
        
        image = cv2.imread(f)
        width, height, channels = image.shape
        if height%args.scale==0 and width%args.scale==0:
            if height>=args.minsize and width>=args.minsize:
                time=os.path.getmtime(f)
                IntoHR(f, HRout)
                intoLR(f, LRout)
                os.utime(HRout, (time, time))
                os.utime(LRout, (time, time))
            else:
                return
        else:
            return
    
        if use_custom_bar:
            index=import_list.index(f)
            divitimput=str(index)+'/'+str(len(import_list))
            # percent of progress, with 1 decimal
            divitimputpercent=str(round(index/len(import_list)*100, 1))+'%'
            terminalsize=os.get_terminal_size()
            termwidth=int(terminalsize.columns/5*4)
            HRFolderandpath=HRout
            if len(divitimput+' '+divitimputpercent+' '+HRFolderandpath+' ')>termwidth:
                difference=len(divitimput+' '+divitimputpercent+' '+HRFolderandpath+' ')-termwidth
                HRFolderandpath='...'+HRout[difference:]
            # print progress with bar 
            print(f'\033[2A\033[2K{divitimput} {divitimputpercent} {HRFolderandpath}\n\033[2K', end = '')
            printProgressBar(index, len(import_list), length = termwidth)
            print("")
            # print("\033[1A\033[2K", divitimput, divitimputpercent, '->', HRFolderandpath)

print('Starting...')
# run through import_list unless backspace is pressed
try:
    with Pool(args.power) as p:
        if use_custom_bar:
            r = list(p.imap(inputparse,import_list))
        else:
            r = list(tqdm(p.imap(inputparse,import_list),total=len(import_list)))
except KeyboardInterrupt:
    print("\nKeyboardInterrupt detected, skipping...\n  \033[0;93m\033[1mwarning: some images may be corrupted. check the newest files in the HR and LR folders\n   ( the modified times should be the same, but the creation times aren't transfered )\033[0m")
# find empty folders in HR and Lr
if not args.no_recursive:
    print("Removing empty folders in HR and Lr...")
    for i in glob.glob(HRFolder+'/*', recursive=True):
        if not os.listdir(i):
            os.rmdir(i)
    for i in glob.glob(LRFolder+'/*', recursive=True):
        if not os.listdir(i):
            os.rmdir(i)
print("\n\nDone!")