# create .sh path
    parent_path=$( cd "$(dirname "${BASH_SOURCE[0]}")" ; pwd -P )
    cd "$parent_path"

    echo for the record, I don\'t necessarily think this version is the best, but I like to keep it around to learn from.
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
    FileArray=($(find $NAME -type f -printf "%T+,%p\n" | sort -r | cut -d, -f2 ))
    ArrayAge=($(find $NAME -type f -printf "%T+,%p\n" | sort -r | cut -d, -f1 ))
   
    if [ -d "$convertedfolder" ]; then
        FileArrayExclude=($(find $convertedfolder -type f -printf "%T+,%p\n" | sort -r | cut -d, -f2 ))
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
        for ((i=0; i<${#FileArray[@]}; i++)); do
            file=${FileArrayNewExt[$i]}
            filename=${FileArray[$i]##*/}
            filefolder=${FileArray[$i]%/*}
            if [[ ! "${FileArrayExclude[@]}" =~ "${file}" ]]; then
                FileArrayConvert[$i]=$file
                convcount=$((convcount+1))
                fi
                filecount=$((filecount+1))
                printf "\r%-8s : %s : %-30s : %-80s : %-10s" "$convcount/$filecount" "${ArrayAge[$i]}" "$filefolder" "$filename"
            done
            #-e '\e[1A\e[K'
    echo
    echo separating convert files and copy files...
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
filecount=${#FileArrayConvert[@]}
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
# convert files
convcount=${#FileArrayCoppie[@]}
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
    printf "%-8s : copying : %-30s : %-80s:\r" "$convedcount/$convcount" "$filefolder" "$filename"
    cp "$file" "$convertedfolder/$convertedfile"
    convedcount=$((convedcount+1))
done
echo converting files...
echo
convcount=${#FileArrayConv[@]}
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
        ffmpeg -y -i "$file" -compression_level 80 -vf "scale=min(2048,iw):-1" -pix_fmt yuv420p "$convertedfolder$convertedfile" > /dev/null 2>&1 
    #ffmpeg -y -i "$file" -compression_level 80 -vf "scale='min(2048,iw)':-1" -pix_fmt yuv420p "$convertedfolder$convertedfile" > /dev/null 2>&1 &
    #echo "${FileArray[$i]}" "${FileArrayNewExt[$i]}"
done


exit
