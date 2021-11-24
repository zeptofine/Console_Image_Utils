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
    echo getting files...
    OLDIFS=$IFS
    IFS=$'\n'
    FileArray=($(find $NAME -type f))
    if [ -d "$convertedfolder" ]; then
        FileArrayExclude=($(find $convertedfolder -type f))
        else
        mkdir $convertedfolder
        fi
    IFS=$OLDIFS
#change file arrays to relative paths, Make new array for new extension
    echo converting paths relative...
    echo 
    for ((i=0; i<${#FileArray[@]}; i++)); do
        file="${FileArray[$i]}"; filenam=${file%.*}; filenam=${filenam##*/}
        filext=.${file##*.}; filefolder=${file%/*}; filefolder=${filefolder##*/}
        FileArray[$i]=.${FileArray[$i]/$NAME/}
            
            if [ ! "$filext" == ".jpg" ]||[ ! "$filext" == ".jpeg" ]; then
                extnew=$filext; else extnew=.jpg; fi
            if [ "$filext" == ".png" ]||[ "$filext" == ".PNG" ]; then
                extnew=.jpg; fi

        FileArrayNewExt[$i]=${FileArray[$i]/$filext/}$extnew
        echo -e '\e[1A\e[K'${FileArray[$i]} $filext \>\>\> $extnew
        
        done
    for ((i=0; i<${#FileArrayExclude[@]}; i++)); do
        file="${FileArrayExclude[$i]}"; filenam=${file%.*}; filenam=${filenam##*/}
        filext=.${file##*.}; filefolder=${file%/*}; filefolder=${filefolder##*/}
        FileArrayExclude[$i]=.${FileArrayExclude[$i]/$convertedfolder/}
            
            if [ ! "$filext" == ".jpg" ]||[ ! "$filext" == ".jpeg" ]; then
                extnew=$filext; else extnew=.jpg; fi
            if [ "$filext" == ".png" ]||[ "$filext" == ".PNG" ]; then
                extnew=.jpg; fi

        echo -e '\e[1A\e[K'${FileArrayExclude[$i]}
        done

# make convert list from FileArray
echo -e '\e[1A\e[K'create convert list...
echo
    for ((i=0; i<${#FileArray[@]}; i++)); do
        file=${FileArrayNewExt[$i]}
        if [[ ! "${FileArrayExclude[@]}" =~ "${file}" ]]; then
            FileArrayConvert[$i]=$file
            echo -e '\e[1A\e[K'$convcount/$filecount new ${FileArrayConvert[$i]}
            convcount=$((convcount+1))
            else 
            echo -e '\e[1A\e[K'$convcount/$filecount old $file
            fi
            filecount=$((filecount+1))
        done
        #-e '\e[1A\e[K'
    echo separating convert files and copy files
for i in ${!FileArrayConvert[@]}; do
    file=${FileArray[$i]}
    if [[ ! "$file" =~ ".jpg" ]]; then 
        if [[ ! "$file" =~ ".png" ]]; then
            FileArrayCopy[$i]=$file
            #else echo $i not jpg but png $file
            fi
        #else echo jpg $file
        fi
    done
for i in ${!FileArrayConvert[@]}; do
    file=${FileArrayConvert[$i]}
    if [[ ! "${FileArrayCopy[@]}" =~ "${file}" ]]; then
        FileArrayConv[$i]=$file
        echo -e '\e[1A\e[K'$convcount/$filecount Convert ${FileArrayConvert[$i]}
        convcount=$((convcount+1))
        else
        FileArrayCoppie[$i]=$file
        echo -e '\e[1A\e[K'$convcount/$filecount Copy ${FileArrayConvert[$i]}
        fi
        filecount=$((filecount+1))
    done
    echo
            #FileArrayNewExt
            #FileArray
            #FileArrayExclude
#echo ${FileArrayConvert[@]}
# convert files

for i in ${!FileArrayCoppie[@]}; do
    file=${FileArray[$i]}
    convertedfile=${FileArrayNewExt[$i]#.*}
        filefolder=${file%/*}
    filefolder=${filefolder##*/}
    if  [[ ! -d "$convertedfolder/$filefolder" ]]
        then 
            mkdir "$convertedfolder/$filefolder"
        fi
    echo -e '\e[1A\e[K'$convedcount/$convcount copying ${FileArray[$i]} 
    cp "$file" "$convertedfolder/$convertedfile"
    convedcount=$((convedcount+1))
done




echo converting files...
echo
for i in ${!FileArrayConv[@]}; do
    file=${FileArray[$i]}
    convertedfile=${FileArrayNewExt[$i]#.*}
    filext=.${file##*.}
    filefolder=${file%/*}
    filefolder=${filefolder##*/}
    if  [[ ! -d "$convertedfolder/$filefolder" ]]
        then 
            mkdir "$convertedfolder/$filefolder"
        fi

    echo -e '\e[1A\e[K'$convedcount/$convcount converting ${FileArray[$i]}
    convedcount=$((convedcount+1))
    if [ $timer == 2 ]; then
        ffmpeg -y -i "$file" -compression_level 80 -vf "scale='min(2048,iw)':-1" -pix_fmt yuv420p "$convertedfolder$convertedfile" > /dev/null 2>&1 
        timer=0
        else 
        ffmpeg -y -i "$file" -compression_level 80 -vf "scale='min(2048,iw)':-1" -pix_fmt yuv420p "$convertedfolder$convertedfile" > /dev/null 2>&1 &
        fi
    #ffmpeg -y -i "$file" -compression_level 80 -vf "scale='min(2048,iw)':-1" -pix_fmt yuv420p "$convertedfolder$convertedfile" > /dev/null 2>&1 &
    #echo "${FileArray[$i]}" "${FileArrayNewExt[$i]}"
    timer=$((timer+1))
done


exit
