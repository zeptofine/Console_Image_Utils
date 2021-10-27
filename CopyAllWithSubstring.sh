#create .sh path
    parent_path=$( cd "$(dirname "${BASH_SOURCE[0]}")" ; pwd -P )
    cd "$parent_path"


#set workspace folder
    echo Folder?
    read NAME
    echo Prefix?
    read PREFIX
    if [ -z "$NAME" ];
        then (
        echo Name not detected!
        exit
        )
        fi
    if [ -z "$PREFIX" ];
        then (
        echo Name not detected!
        exit
        )
        fi 
    cd $NAME
    cd ..
    origin=$PWD
    nameshort=${NAME%*/}

    mkdir $origin${nameshort/$origin}-Converted-$PREFIX > /dev/null 2>&1
    convertedfolder=$origin${nameshort/$origin}-Converted-$PREFIX
    echo $convertedfolder/
    cd $NAME
# save and change IFS
OLDIFS=$IFS
IFS=$'\n'
# read all file name into an array
fileArray=($(find $NAME -type f -name "*$PREFIX*"))
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
            convertedfilenoconv=$convertedfolder/$filefolder/$filename$filext
            if [[ ! -f "$convertedfilenoconv" ]];
            then 
            cp "$originalfile" "$convertedfilenoconv" &
            echo $filename$filext
            fi
    )
    done
    #  /dev/null 2>&1 
