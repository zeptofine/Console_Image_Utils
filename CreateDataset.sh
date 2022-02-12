#!/bin/bash
# formatting help
   white='\033[1;37m'; yellow='\033[1;33m'; red='\033[0;31m'; green='\033[1;32m'; lightblue='\033[1;34m'; brown='\033[0;33m'; cyan='\033[0;36m'
   bold='\e[1m'; italic='\e[3m'; underline='\e[4m'; strike='\e[9m'; default='\e[0m'
   export white yellow red green cyan lightblue brown bold italic underline strike default 
echo -e "${white}${bold}Hi! this script was made to convert thousands of files to another format.${default}
Oh, also they can't be videos or gifs or swfs or anything like that. pngs, and jpegs are the only ones converted so far. the rest will be ignored.
${underline}you can also use command line arguments!${default} use the -h flag for more context.
${brown}requirements: Imagemagick, GNU parallel.${default}
I reccomend using the ramdisk script in the same folder as this script to speed up the process. ${red}(make a dedicated folder for it)${default}
---------------------------------------------------------------------"

# check for arguments
while getopts "hi:o:t:x:c:d:" opt; do
   case $opt in
   h) echo -e "These arguments are optional. They can be used to automate the process so you don't have to input them every time.${bold}${underline}${white}
prefix   defaults               description          ${default}${white}
${white}|${default} -h  ${white}|${default}             ${white}|${default}display current help         
${white}|${default} -i  ${white}|${default}             ${white}|${default}input folder, skip prompt
${white}|${default} -o  ${white}|${default} (scale)xHR  ${white}|${default}output folder
${white}|${default} -t  ${white}|${default} default     ${white}|${default}tmpdir for parallel processing
${white}|${default} -x  ${white}|${default} 1,2,[4],8   ${white}|${default}scale factor, skip prompt
${white}|${default} -d  ${white}|${default} [y]/n       ${white}|${default}delete corrupted files, skip prompt
${white}|${default} -c  ${white}|${default} [y]/n       ${white}|${default}convert files, skip prompt${default}"; exit 0;;
   i) input="$OPTARG";; o) output="$OPTARG";; t) tmpdir="$OPTARG";; d) corrupt="$OPTARG";;
   x) scale="$OPTARG";; c) convert="$OPTARG";; \?) echo "Invalid option -$OPTARG" >&2;;
esac; done
#check if imagemagick & pngcheck is a valid command
   if ! command -v magick >/dev/null 2>&1;then echo "imagemagick is not installed, identify & convert will not work properly"; exit 127; fi
   if ! command -v pngcheck >/dev/null 2>&1;then echo "pngcheck is not installed, checking corrupt pngs will not work properly"; fi
   if ! command -v parallel >/dev/null 2>&1;then echo "parallel is not installed, this script will not work properly"; exit 127; fi
#check if any inputs are unnacounted for
   if [ -z "$input" ]; then echo -e "Folder:"; read -r input; fi
   if [ -z "$input" ]; then echo "No folder entered, exiting"; exit 1; fi
   if [ -z "$scale" ]; then echo -e "Enter the scale factor:"; read -r -n 1 scale; export scale; fi
   if [ -z "$scale" ]; then echo "No scale entered, default is 4"; scale=4; fi
      cd "$input" || exit; nameshort=$(dirname "$input")
   if [[ -z $output ]]; then convertedfolder=$nameshort/${scale}xHR; output=$convertedfolder; else convertedfolder=$output; fi
      mkdir "$convertedfolder" >/dev/null 2>&1
   if [[ -z $tmpdir ]]; then tmpdir=$(dirname "$0"); fi
# create ffmpegconv command (it doesnt use ffmpeg lol, i just havent change the name yet)
declare -x convertedfolder input scale
echo -e "Linking to HR...\n"
function ffmpegconv {
   file="$1"; filext=.${file##*.}; basename=$(basename "$file")
   if [[ $filext =~ .jpg ]] || [[ $filext =~ .png ]] || [[ $filext =~ .jpeg ]] || [[ $filext =~ .PNG ]]; then
   if [[ ! -f "$convertedfolder/$basename" ]]; then imagewidtheight=$(identify -ping -format "%w:%h" "$file")
   if ! ((${imagewidtheight##*:} % scale)) || ! ((${imagewidtheight%%:*} % scale)); then
   ln -s "$file" "$convertedfolder/$basename" >/dev/null 2>&1
   fi; fi; fi;}; export -f ffmpegconv

IFS=$'\n'
#run copy function through input
   find "$input" -type f,l -printf "%T+,%p\n" | sort -r | cut -d, -f2 | parallel --bar --tmpdir "$tmpdir" ffmpegconv {}
if [ -z "$convert" ]; then echo -e "${default}would you like to check the converted files for conversion? ([y]/n)"; read -r -n 1 convert; fi
if [ -z "$convert" ]; then echo -e "\e[1A\033[2KNothing entered, default is y"; convert=y; fi

if [[ $convert == y ]]; then {
LRfolder="$(dirname "$input")/${scale}xLR"; export LRfolder

# find images that are corrupt
   function checkfilespng { file="$2"; if [[ ! -f "$LRfolder/$(basename "$file")" ]]
   then { pngcheck "$file" >> "$1/.png.tmp";};fi }; export -f checkfilespng
   function checkfilesmagick { file="$2"; if [[ ! -f "$LRfolder/$(basename "$file")" ]]
   then { identify "$file" >> "$1/.identify.tmp";};fi }; export -f checkfilesmagick

   echo -e "${white}${italic}checking files using pngcheck...${default}"
   if [ -f "$tmpdir/.png.tmp" ]; then rm "$tmpdir/.png.tmp"; fi
   find "$convertedfolder" -type f,l | grep .png | sort -r | parallel --bar --tmpdir "$tmpdir" checkfilespng "$tmpdir" {}
   echo -e "${white}${italic}checking files using imagemagick...${default}"
   if [ -f "$tmpdir/.identify.tmp" ]; then rm "$tmpdir/.identify.tmp"; fi
   find "$convertedfolder" -type f,l | sort -r | parallel --bar --tmpdir "$tmpdir" checkfilesmagick "$tmpdir" {}

# sort corrupted files
   echo -e "${white}${italic}sorting...${default}"
   if [ -f "$tmpdir/.png_errors.tmp" ]; then rm "$tmpdir/.png_errors.tmp"; fi
   if [ -f "$tmpdir/.identify_errors.tmp" ]; then rm "$tmpdir/.identify_errors.tmp"; fi
   if [ -f "$tmpdir/.png.tmp" ]; then < "$tmpdir/.png.tmp" grep ERROR | uniq | cut -d: -f2 | cut -c2- >> "$tmpdir/.png_errors.tmp"; fi
   if [ -f "$tmpdir/.identify.tmp" ]; then < "$tmpdir/.identify.tmp" grep warning | uniq | cut -d\` -f2 | cut -d\' -f1 >> "$tmpdir/.identify_errors.tmp"; fi
   if [ -f "$tmpdir/.errors.tmp" ]; then rm "$tmpdir/.errors.tmp"; fi
   cat "$tmpdir/.png_errors.tmp" "$tmpdir/.identify_errors.tmp" | sort -r | uniq > "$tmpdir/.errors.tmp"

# delete corrupted files
   if [ -f "$tmpdir/.readlink.tmp" ]; then rm "$tmpdir/.readlink.tmp"; fi
   function readlinkfunc { file=$(readlink "$2"); echo "${file#"$input"}" >> "$1/.readlink.tmp" ;}; export -f readlinkfunc
   if [ -f "$tmpdir/.errors.tmp" ]; then < "$tmpdir/.errors.tmp" parallel --tmpdir "$tmpdir" readlinkfunc "$tmpdir" {}; fi
   echo -e "${white} here's where all the corrupted files came from:${default}\n"
   < "$tmpdir/.readlink.tmp" rev | cut -d/ -f2- | rev | sort | uniq -c

if [ -z "$corrupt" ]; then echo -ne "${default}would you like to delete the corrupted files? ([y]/n)"; read -r -n 1 corrupt; fi
if [ -z "$corrupt" ]; then echo -e "\e[1A\033[2KNothing entered, default is y"; corrupt=y; fi
if [[ "$corrupt" == y ]]; then { echo -e "\n${white}${italic}deleting corrupted files... ${default}\n"
      function delete { rm "$1";}; export -f delete
      < "$tmpdir/.errors.tmp" parallel --tmpdir "$tmpdir" delete {}
   } else { echo -ne "\n${white}${italic}skipping...${default}\n";}; fi
      function readlinkfull { file=$(readlink "$2"); echo "${file}" >> "$1/.readlinkfull.tmp" ;}; export -f readlinkfull
      if [ -f "$tmpdir/.readlinkfull.tmp" ]; then rm "$tmpdir/.readlinkfull.tmp"; fi
      if [ -f "$(dirname "$input")/corrupted_files.txt" ]; then rm "$(dirname "$input")/corrupted_files.txt"; fi
         if [ -f "$tmpdir/.errors.tmp" ]; then < "$tmpdir/.errors.tmp" parallel --tmpdir "$tmpdir" readlinkfull "$tmpdir" {}; fi
         < "$tmpdir/.readlinkfull.tmp" sort | uniq> "$(dirname "$input")/corrupted_files.txt"
         echo -e "${white}${italic}corrupted files list saved to $(dirname "$input")/corrupted_files.txt${default}"

# Find files that do not have an LR version
   echo -e "\nChecking for missing LR files...\n"
   function findisolated { File=$(basename "$2"); if [[ ! -f "$LRfolder/$File" ]]; then echo -e "$2" >> "$1/.isolated.tmp"; fi; }; export -f findisolated
   if [ -f "$tmpdir/.isolated.tmp" ]; then rm "$tmpdir/.isolated.tmp"; fi
   if [ -d "$LRfolder" ]; then find "$convertedfolder" -type f,l | sort -r | parallel --bar --tmpdir "$tmpdir" findisolated "$tmpdir" {}
      else echo -e "${white}${italic}LRFolder doesn't exist, skipping..\n"; find "$convertedfolder" -type f,l | sort -r >> "$tmpdir/.isolated.tmp"
      fi
# delete tmp files
if [ -f "$tmpdir/.readlink.tmp" ]; then rm "$tmpdir/.readlink.tmp"; fi
if [ -f "$tmpdir/.readlinkfull.tmp" ]; then rm "$tmpdir/.readlinkfull.tmp"; fi
if [ -f "$tmpdir/.png.tmp" ]; then rm "$tmpdir/.png.tmp"; fi
if [ -f "$tmpdir/.identify.tmp" ]; then rm "$tmpdir/.identify.tmp"; fi
if [ -f "$tmpdir/.png_errors.tmp" ]; then rm "$tmpdir/.png_errors.tmp"; fi
if [ -f "$tmpdir/.identify_errors.tmp" ]; then rm "$tmpdir/.identify_errors.tmp"; fi
if [ -f "$tmpdir/.errors.tmp" ]; then rm "$tmpdir/.errors.tmp"; fi
echo -e "\n${white}${italic}converting clean files...${default}\n"

scaled=$(bc -l <<< 100/$scale | sed -e 's/[0]*//g' | sed 's/\.$//')%; export scaled
function convertfunc { file=$(basename "$2"); magick convert "$2" -strip -resize "$scaled" "$LRfolder/$file"; }; export -f convertfunc
mkdir "$(dirname "$input")/${scale}xLR" >/dev/null 2>&1
< "$tmpdir/.isolated.tmp" sort -r | parallel --bar --tmpdir "$tmpdir" convertfunc "$tmpdir" {}
if [ -f "$tmpdir/.isolated.tmp" ]; then rm "$tmpdir/.isolated.tmp"; fi

} else echo -e "${white}${italic}skipping conversion...${default}"; fi
echo -e "\n${white}${italic}done!${default}\n"

exit