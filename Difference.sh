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
    if [[ ! -f "$origin${nameshort/$origin}-Converted-Jpg" ]]
        then
        mkdir $origin${nameshort/$origin}-Converted-Jpg > /dev/null 2>&1 
        fi
    convertedfolder=$origin${nameshort/$origin}-Converted-Jpg
    echo $convertedfolder/

#check if ffmpeg is a valid command, if not install ffmpeg
    Ffmpegcheck=$(command -v ffmpeg)
    if [ -z "$Ffmpegcheck" ];
        then pacman -S ffmpeg
    else (
    echo $NAME
    )
    fi
#Run the commands
    cd $NAME

# save and change IFS
OLDIFS=$IFS
IFS=$'\n'
 
# read all file name into an array
fileArray=($(find $NAME -type f))
 
# restore it
IFS=$OLDIFS
 
# get length of an array
tLen=${#fileArray[@]}
 
# use for loop read all filenames
for (( i=0; i<${tLen}; i++ ));
do (
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
            #echo $convertfolder/$filefolder/$filenam$filext
        #Execute ffmpeg

            #ffmpeg -y -i $NAME/$filefoldernoper$filename$filext -compression_level 80 -vf "scale='min(3840,iw)':-1" -pix_fmt yuv420p $convertedfolder$filefoldernoper$filename.jpg > /dev/null 2>&1 &
        
            if [ ! "$filext" == ".jpg" ];
            then (
                if [ ! "$filext" == ".png" ];
                then (
                    if [[ ! -f "$convertedfilenoconv" ]];
                    then 
                    echo $convertedfilenoconv
                    cp "$originalfile" "$convertedfilenoconv" > /dev/null 2>&1
                    fi
                )
                else (
                    if [[ ! -f "$convertedfile" ]];
                    then
                    ffmpeg -y -i "$originalfile" -compression_level 80 -vf "scale='min(2560,iw)':-1" -pix_fmt yuv420p "$convertedfile" > /dev/null 2>&1 &
                    echo $convertedfile
                    fi
                )
                fi
            )
            else (
                    if [[ ! -f "$convertedfile" ]];
                    then
                    ffmpeg -y -i "$originalfile" -compression_level 80 -vf "scale='min(2560,iw)':-1" -pix_fmt yuv420p "$convertedfile" > /dev/null 2>&1 &
                    echo $convertedfile
                    fi
            )
            fi
    )
    done
    #  /dev/null 2>&1 