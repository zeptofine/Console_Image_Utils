#create .sh path
    parent_path=$( cd "$(dirname "${BASH_SOURCE[0]}")" ; pwd -P )
    cd "$parent_path"


#set workspace folder
    echo Hello, who am I speaking to?
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
    if [[ -f $origin${nameshort/$origin}-Converted-Jpg ]]
        then
        mkdir $origin${nameshort/$origin}-Converted-Jpg
        fi
    convertedfolder=$origin${nameshort/$origin}-Converted-Jpg
    echo $convertedfolder

#check if ffmpeg is a valid command, if not install ffmpeg
    Ffmpegcheck=$(command -v ffmpeg)
    if [ -z "$Ffmpegcheck" ];
        then pacman -S ffmpeg
    else (
    echo $NAME
    )
    fi
#create ffmpeg executable
    if [ -e "$parent_path/FFmpegjpg.sh" ];
    then ( rm "$parent_path/FFmpegjpg.sh"
    echo deleted FFmpegjpg.sh )
    fi
    (   echo echo ffmpeg -n -i \$1 -compression_level \$2 -vf "scale='min(3840,iw)':-1" \$3
        echo ffmpeg -n -i \$1 -compression_level \$2 -vf "scale='min(3840,iw)':-1" \$3
    ) > $parent_path/FFmpegjpg.sh
#Run the commands
    cd $NAME
    
    for file in $(find)
    do (
        
        filefolder=${file%/*}
        filefoldernoper=${filefolder#.*}
            #if picture folder doesn't exist, create folder
        if  [[ ! -d $convertedfolder$filefoldernoper ]]
        then (
            echo $convertedfolder/$filefoldernoper
            mkdir $convertedfolder$filefoldernoper
            )
        fi
            #separate the folder, name, and extension
        filenam=${file%.*}
        filename=${filenam/$filefoldernoper}
        filename=${filename#.*}
        filext=${file/$filenam}

            #Execute ffmpeg
            
        if [[ ! -e $convertedfolder$filefoldernoper$filename.jpg ]]
        then (
            cp "$NAME/$filefoldernoper$filename$filext" "$convertedfolder$filefoldernoper$filename$filext"
        ffmpeg -y -i $NAME/$filefoldernoper$filename$filext -compression_level 80 -vf "scale='min(3840,iw)':-1" $convertedfolder$filefoldernoper$filename.jpg &
        )
        fi
    )
    done
sleep 10