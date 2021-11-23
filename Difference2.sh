# create .sh path
    parent_path=$( cd "$(dirname "${BASH_SOURCE[0]}")" ; pwd -P )
    cd "$parent_path"


# set workspace folder
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
    cd $NAME
# install ffmpeg if not installed
    Ffmpegcheck=$(command -v ffmpeg)
    if [ -z "$Ffmpegcheck" ];
        then pacman -S ffmpeg
    fi

# Get file array and exclusion array
    echo getting new files and old files...
    OLDIFS=$IFS
    IFS=$'\n'
    FileArray=($(find $NAME -type f))
    if [ -d "$convertedfolder" ]; then
        FileArrayExc=($(find $convertedfolder -type f))
        else
        FileArrayExc=()
        fi
    IFS=$OLDIFS
#change file arrays to relative paths
    echo making paths relative...
    for ((i=0; i<${#FileArray[@]}; i++)); do
        FileArray[$i]=${FileArray[$i]/$NAME/}
        done
    for ((i=0; i<${#FileArrayExc[@]}; i++)); do
        FileArrayExc[$i]=${FileArrayExc[$i]/$convertedfolder/}
        done
# make converted list from FileArray
    echo making predicted convert list...
    for ((i=0; i<${#FileArray[@]}; i++)); do
        file="${FileArray[$i]}"; filenam=${file%.*}; filenam=${filenam##*/}
        filext=.${file##*.}; filefolder=${file%/*}; filefolder=${filefolder##*/}
        if [ ! "$filext" == ".jpg" ]||[ ! "$filext" == ".jpeg" ]; then
                extnew=$filext; else extnew=.jpg; fi
        if [ "$filext" == ".png" ]||[ "$filext" == ".PNG" ]; then
                extnew=.jpg; fi
        FileArrayConv[$i]=.$filefolder/$filenam$extnew
       done

#get list of new files in folders, excluding FileArrayExc
for ((i=0; i<${#FileArrayConv[@]}; i++)); do
    file=${FileArrayConv[$i]}
    #???
echo $file #????
done