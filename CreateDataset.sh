echo folder?
read folder
    if [ -z "$folder" ];
        then (
        echo folder not detected!
        exit 1
        )
        fi
cd $folder; cd ..
origin=$PWD
echo $CWD
echo copying $folder into HR...
mkdir ./Dataset
mkdir ./Dataset/HR
mkdir ./Dataset/LR
ORIGINFOLDER=$origin/Dataset
fileArray=($(find $folder -type f -printf "%T+,%p\n" | sort -r | cut -d, -f2 ))
ArrayAge=($(find $folder -type f -printf "%T+,%p\n" | sort -r | cut -d, -f1 ))
tLen=${#fileArray[@]}
for (( i=0; i<${tLen}; i++ )); do 
    file="${fileArray[$i]}"
    filext=.${file##*.}
    filefolder=${file%/*}
    filefolder=${filefolder##*/}
    filenam=${file%.*}
    filenam=${filenam##*/}
    filename=${filenam/$filefolder}
    filename=${filename#.*}
    if [[ ! -f "./Dataset/HR/$filename$filext" ]]; then
            if [[ $filext =~ .jpg ]] || [[ $filext =~ .png ]] || [[ $filext =~ .jpeg ]] || [[ $filext =~ .PNG ]]; then
                cp $file ./Dataset/HR/$filename$filext
                echo ./Dataset/HR/$filename$filext
                fi
        fi
done



LRFOLDER=$origin/Dataset/LR
HRFOLDER=$origin/Dataset/HR
echo $LRFOLDER
echo $HRFOLDER
cd $HRFOLDER
HRfileArray=($(find $HRFOLDER -type f -printf "%T+,%p\n" | cut -d, -f2 ))
HRArrayAge=($(find $HRFOLDER -type f -printf "%T+,%p\n" | cut -d, -f1 ))
LRfileArray=($(find $LRFOLDER -type f -printf "%T+,%p\n" | cut -d, -f2 ))
LRArrayAge=($(find $LRFOLDER -type f -printf "%T+,%p\n" | cut -d, -f1 ))
HRTLen=${#HRfileArray[@]}
# use for loop read all filefolders

for (( i=0; i<${HRTLen}; i++ ));
do (
            file="${HRfileArray[$i]}"
            filefolder=${file%/*}
            filefolder=${filefolder##*/}
        #separate the folder, folder, and extension
            filenam=${file%.*}
            filenam=${filenam##*/}
            filename=${filenam/$filefolder}
            filename=${filename#.*}
            filext=${file##*.}
            filext=.$filext
            convertedfile=$LRFOLDER/$filename.jpg
            if [[ ! -f "$convertedfile" ]];
                    then
                    ffmpeg -y -i "$file" -compression_level 80 -vf "scale=iw/4:-1" -pix_fmt yuv420p "$convertedfile" > /dev/null 2>&1
                    echo ${ArrayAge[$i]} \| $i \| $filename$filext
                    fi
    )
    done
    #  /dev/null 2>&1 
