parent_path=$( cd "$(dirname "${BASH_SOURCE[0]}")" ; pwd -P )
cd "$parent_path"
echo Hello, who am I speaking to?
read NAME
Ffmpegcheck=$(command -v ffmpeg)
if [ -z "$Ffmpegcheck" ];
then pacman -S ffmpeg
fi
if [ -z "$NAME" ];
then (
echo Name not detected!
exit
)
else (
echo $NAME
)
fi
if [ -e "$parent_path/hello.sh" ];
then ( rm "$parent_path/hello.sh"
echo deleted hello.sh )
fi
(echo echo hello
 echo echo hello again
) > $parent_path/hello.sh
echo created hello.sh
konsole -e sh $parent_path/hello.sh
cd $NAME

if [ -e "$parent_path/list.txt" ];
then ( rm "$parent_path/list.txt"
echo deleted list.txt )
fi
find -name '* *' > $parent_path/list.txt
echo created list.txt
