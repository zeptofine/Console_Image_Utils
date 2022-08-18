#!/bin/bash
# check if there are no arguments
if [ $# -eq 0 ]; then 
  echo -e "No arguments supplied\nUsage: ./val_timelapse.sh <path to convert>"; exit 1
fi
# check if magick is installed
if ! [ -x "$(command -v convert)" ]; then nullprogs=("${nullprogs[@]}" "imagemagick"); fi
if ! [ -x "$(command -v ffmpeg)" ]; then nullprogs=("${nullprogs[@]}" "ffmpeg"); fi
if ! [ -x "$(command -v parallel)" ]; then nullprogs=("${nullprogs[@]}" "parallel"); fi
if [ ${#nullprogs[@]} -gt 0 ]; then
  echo "The following programs are not executable:"
  for i in "${nullprogs[@]}"; do echo "$i"; done
  echo "Please install them before running this script."
  exit 1
fi
IFS=$'\n'
input="$*"
# if so, turn relative path into absolute path
input=$(realpath "$input")
# strip the last slash if it exists
if [ "${input: -1}" == "/" ]
then
  input="${input::-1}"
fi
cd "$input" || exit
mapfile -t array < <(find "$input" -type f,l)
dirsource="${input%/*}"; export dirsource
echo "$input"
echo "Found ${#array[@]} files"

echo "Copying files to /tmp/${input##*/}"
  if [ -d "/tmp/${input##*/}" ]; then rm -rf "/tmp/${input##*/}"; fi
    cp -r "$input" "/tmp/${input##*/}"
    cd "/tmp/${input##*/}" || exit
    tmpinput="/tmp/${input##*/}"
    #find files, and check if there are more than one type of file 
    if [ "$(find "$tmpinput" -type f,l | awk -F . '{print $NF}' | sort | uniq -c | awk '{print $2,$1}' | wc -l)" -gt 1 ]; then {
      echo "Found more than one type of file, converting to webp as a fallback"
      function extcheck() {
        tmpfilext="${1##*.}"
        tmpfile="$1"
        desiredext="webp"
        if [ ! "$tmpfilext" == "$desiredext" ]; then
          convert "$tmpfile" -quality 100 "${tmpfile%.*}.$desiredext"
          rm "$1"
        fi
      }; export -f extcheck
      find "$tmpinput" -type f,l | parallel --bar extcheck
    }; fi
echo arranging files...
  if [ -f "$tmpinput/${input##*/}_mylist.txt" ]; then rm "$tmpinput/${input##*/}_mylist.txt"; fi
      function echolist() {
          file="${*#"$dirsource"}"; file=${file##*/}
          echo "$( echo "${file%.*}" | sed -e :a -e 's/^.\{1,6\}$/0&/;ta'):file $*"
      }; export -f echolist
  find "$tmpinput" -type f,l | parallel echolist {} | sort -n | cut -d: -f2 >> "$tmpinput/${input##*/}_mylist.txt"
  grep -v ".txt" "$tmpinput/${input##*/}_mylist.txt" > "$tmpinput/${input##*/}_mylist.txt.tmp"
  mv "$tmpinput/${input##*/}_mylist.txt.tmp" "$tmpinput/${input##*/}_mylist.txt"
echo converting with ffmpeg...
  ffmpeg -progress -hide_banner -safe 0 -loglevel error -stats -r 12 -f concat -i "$tmpinput/${input##*/}_mylist.txt" "$tmpinput/${input##*/}_temp.mkv"
  ffmpeg -hide_banner -loglevel panic -stats -i "$tmpinput/${input##*/}_temp.mkv" -vf minterpolate=fps=48:mi_mode=blend -vcodec libx264 -crf 16 -pix_fmt yuv420p "${input%/*}/$(date "+%D+%T"| tr "/" ":")_${input##*/}.mp4"
echo removing temporary files...
rm -rf "$tmpinput"