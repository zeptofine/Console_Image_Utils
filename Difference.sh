#create .sh path
    parent_path=$( cd "$(dirname "${BASH_SOURCE[0]}")" ; pwd -P )
    cd "$parent_path"


#set workspace folder
    echo Folder?
    read NAME
    if [ -z "$NAME" ];
        then (
        echo Name not detected!
        exit
        )
        fi
    cd $NAME
    cd ..
    origin=$PWD
    nameshort=${NAME%*/}
    convertedfolder=$origin${nameshort/$origin}-Converted-Jpg
    echo $convertedfolder/
#check if ffmpeg is a valid command, if not install ffmpeg
    Ffmpegcheck=$(command -v ffmpeg)
    if [ -z "$Ffmpegcheck" ];
        then pacman -S ffmpeg
    fi
#Run the commands
    cd $NAME

# save and change IFS
OLDIFS=$IFS
IFS=$'\n'
fileArray=($(find $NAME -type f))
if [ -d "$convertedfolder" ]; then
oldFileArray=($(find $convertedfolder -type f))
else
    oldFileArray=0
fi

IFS=$OLDIFS
tLen=${#fileArray[@]}
toldLen=${#oldFileArray[@]}
if [ -d "$convertedfolder/" ]; then
   echo estimating image ratio...
echo $toldLen/$tLen $(awk 'BEGIN {print ('$toldLen'/'$tLen')*100}' | cut -c -5)%
oldFileArray=( "${oldFileArray[@]/$convertedfolder/$NAME}" )
echo collecting images...
echo 
newcount=0; totalcount=0
for i in ${fileArray[@]}; do
            if [[ ! "${oldFileArray[@]}" =~ "${i%.*}" ]]; then
                newFileArray+=( "$i" )
                newcount=($(($newcount+1)))
            fi
        totalcount=($(($totalcount+1)))
    echo -e '\e[2A\e[K'$(awk 'BEGIN {print ('$totalcount'/'$tLen')*100}' | cut -c -5)% \| collecting new images... 
    echo -e $(awk 'BEGIN {print (('$totalcount'-'$newcount')/'$totalcount')*100}' | cut -c -5)% \| $(($totalcount-$newcount))/$totalcount 
    done
else
mkdir $convertedfolder
fi
tnewLen=${#newFileArray[@]}
echo

convcount=1
# use for loop read all filenames
for (( i=0; i<$tLen; i++ ));
do
    
        #if picture folder doesn't exist, create folder
            file="${fileArray[$i]}"
            filefolder=${file%/*}
            filefolder=${filefolder##*/}
            convertfolder=${convertedfolder%*/}
            if  [[ ! -d "$convertfolder/$filefolder" ]]
            then (
                mkdir "$convertfolder/$filefolder"
                )
            fi
        #separate the folder, name, and extension
            filenam=${file%.*}
            filenam=${filenam##*/}
            filename=${filenam/$filefolder}
            filename=${filename#.*}
            filext=${file##*.}
            filext=.$filext
            originalfile=$NAME/$filefolder/$filename$filext
            convertedfile=$convertedfolder/$filefolder/$filename.jpg
            convertedfilenoconv=$convertedfolder/$filefolder/$filename$filext
            if [ ! "$filext" == ".jpg" ];
            then (
                if [ ! "$filext" == ".png" ];
                then (
                    if [[ ! -f "$convertedfilenoconv" ]];
                    then 
                    echo -e '\e[1A\e[K'$displays $display copy $filefolder / ${filename: -10}$filext
                    cp "$originalfile" "$convertedfilenoconv" > /dev/null 2>&1
                    fi
                )
                else (
                    if [[ ! -f "$convertedfile" ]];
                    then
                    ffmpeg -y -i "$originalfile" -compression_level 80 -vf "scale='min(2048,iw)':-1" -pix_fmt yuv420p "$convertedfile" > /dev/null 2>&1 &
                    echo -e '\e[1A\e[K'$displays $display convert $filefolder / ${filename: -10}$filext
                    fi
                )
                fi
            )
            else (
                    if [[ ! -f "$convertedfile" ]];
                    then
                    ffmpeg -y -i "$originalfile" -compression_level 80 -vf "scale='min(2048,iw)':-1" -pix_fmt yuv420p "$convertedfile" > /dev/null 2>&1 &
                    echo -e '\e[1A\e[K'$displays $display convert $filefolder / ${filename: -10}$filext
                    fi
            )
            fi
    convcount=($((convcount+1)))
    displays=$convcount/$tLen
    display=$(awk 'BEGIN {print ('$convcount'/'$tLen')*100}' | cut -c -5)%
    done
    echo Done.
    #  /dev/null 2>&1 
