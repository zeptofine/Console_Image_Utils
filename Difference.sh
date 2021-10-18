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
#Run the commands
    cd $NAME
    
    for file in $(find)
    do (
        #if picture folder doesn't exist, create folder
            filefolder=${file%/*}
            filefoldernoper=${filefolder#.*} 
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
            originalfile=$NAME/$filefoldernoper$filename$filext
            convertedfile=$convertedfolder$filefoldernoper$filename.jpg
            convertedfilenoconv=$convertedfolder$filefoldernoper$filename$filext
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
                    ffmpeg -y -i $originalfile -compression_level 80 -vf "scale='min(2560,iw)':-1" -pix_fmt yuv420p $convertedfile > /dev/null 2>&1 &
                    echo $convertedfile
                    fi
                )
                fi
            )
            else (
                    if [[ ! -f "$convertedfile" ]];
                    then
                    ffmpeg -y -i $originalfile -compression_level 80 -vf "scale='min(2560,iw)':-1" -pix_fmt yuv420p $convertedfile > /dev/null 2>&1 &
                    echo $convertedfile
                    fi
            )
            fi
    )
    done