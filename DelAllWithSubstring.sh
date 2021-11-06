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
            rm ${fileArray[$i]}
            echo ${fileArray[$i]}
    )
    done
    #  /dev/null 2>&1 
