#create .sh path
    parent_path=$( cd "$(dirname "${BASH_SOURCE[0]}")" ; pwd -P )
    cd "$parent_path"


#set workspace folder
    echo Folder?
    read NAME
        if [ -z "$NAME" ];
        then (
        echo Name not detected! defaulting to working directory... $OLDPWD
        echo cd $OLDPWD/
        )
        else (
        cd $NAME
        )
        fi
    echo Prefix?
    read PREFIX
    if [ -z "$PREFIX" ];
        then (
        echo Prefix not detected!
        exit
        )
        fi 
        echo $PWD
# save and change IFS
OLDIFS=$IFS
IFS=$'\n'
# read all file name into an array
if [ -z "$NAME" ]; then
    fileArray=($(find $OLDPWD -type f -name "*$PREFIX*"))
else 
    fileArray=($(find $NAME -type f -name "*$PREFIX*"))
fi

# restore it
IFS=$OLDIFS
# get length of an array
tLen=${#fileArray[@]}
# use for loop read all filenames
for (( i=0; i<${tLen}; i++ ));
do (
            rm "${fileArray[$i]}"
            echo ${fileArray[$i]}
    )
    done
    #  /dev/null 2>&1 
