#!/bin/bash
IFS=$'\n'
cd "${*%/*}" || exit
mapfile -t array < <(find "$@" -type f,l)
dirsource="${*%/*}"; export dirsource
echo "Found ${#array[@]} files"
echo arranging files...
if [ -f "$dirsource/${*##*/}_mylist.txt" ]; then rm "$dirsource/${*##*/}_mylist.txt"; fi
    function echolist() {
        file="${*#"$dirsource"}"; file=${file##*/}
        echo "$( echo "${file%.*}" | sed -e :a -e 's/^.\{1,6\}$/0&/;ta'):file $*"
    }; export -f echolist
    find "$@" -type f,l | parallel echolist {} | sort -n | cut -d: -f2  >> "$dirsource/${*##*/}_mylist.txt"
echo converting with ffmpeg...
ffmpeg -y -hide_banner -safe 0 -loglevel error -stats -r 24 -f concat -i "$dirsource/${*##*/}_mylist.txt" "${*%/*}/${*##*/}_temp.mkv"
ffmpeg -y -hide_banner -loglevel error -stats -i "${*%/*}/${*##*/}_temp.mkv" -vf minterpolate=fps=48:mi_mode=blend -vcodec libx264 -crf 25 -pix_fmt yuv420p "${*%/*}/$(date "+%D+%T"| tr "/" ":")_${*##*/}.mp4"
rm "$dirsource/${*##*/}_mylist.txt" "${*%/*}/${*##*/}_temp.mkv"
echo removing temporary files...