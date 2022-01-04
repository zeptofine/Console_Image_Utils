#!/bin/bash
# formatting help
   white='\033[1;37m'; yellow='\033[1;33m'; red='\033[0;31m'; green='\033[1;32m'; lightblue='\033[1;34m'; brown='\033[0;33m'; cyan='\033[0;36m'
   bold='\e[1m'; italic='\e[3m'; underline='\e[4m'; strike='\e[9m'; default='\e[0m'
   export white yellow red green cyan lightblue brown bold italic underline strike default 
echo -e "${white}${bold}Hi! this script was made to convert thousands of files to another format.${default}
Oh, also they can't be videos or gifs or swfs or anything like that. pngs, and jpegs are the only ones converted so far. the rest will be ignored.
${underline}you can also use command line arguments!${default} use the -h flag for more context.
${brown}requirements: Imagemagick, GNU parallel.${default}
I reccomend using the ramdisk script in the same folder as this script to speed up the process.
---------------------------------------------------------------------"

# check for arguments
while getopts "hi:o:s:t:x:c:" opt; do
   case $opt in
   h) echo -e "These arguments are optional. They can be used to automate the process so you don't have to input them every time.
${bold}${underline}${white}     commands       defaults               description          ${default}${white}
${white}|${default} -h  ${white}▏${default}             ${white}▏${default}display this help!              
${white}|${default} -i  ${white}▏${default}             ${white}▏${default}input folder, skip prompt
${white}|${default} -o  ${white}▏${default} (scale)xHR  ${white}▏${default}output folder
${white}|${default} -s  ${white}▏${default} [1],2       ${white}▏${default}sort by age/name, skip prompt
${white}|${default} -t  ${white}▏${default} default     ${white}▏${default}tmpdir for parallel processing
${white}|${default} -x  ${white}▏${default} 1,2,[4],8   ${white}▏${default}scale factor, skip prompt
${white}|${default} -c  ${white}▏${default} [y]/n       ${white}▏${default}convert files, skip prompt${default}"; exit 0;;
   i) input="$OPTARG";; o) output="$OPTARG";; s) sort="$OPTARG";; t) tmpdir="$OPTARG";;
   x) scale="$OPTARG";; c) convert="$OPTARG";; \?) echo "Invalid option -$OPTARG" >&2;;
  esac
done
# parameter prompt
function echoargs {
echo -ne "\e[7A\033[2K${white}${bold}input folder: ${default}${lightblue}${input}${default}
${white}${bold}output folder: ${default}${lightblue}${output}${default}
${white}${bold}sort by: ${default}${lightblue}${sort}${default}
${white}${bold}tmpdir: ${default}${lightblue}${tmpdir}${default}
${white}${bold}scale factor: ${default}${lightblue}${scale}${default}
${white}${bold}convert files: ${default}${lightblue}${convert}${default}\n"
}; export -f echoargs
#check if imagemagick & pngcheck is a valid command
   if ! magick >/dev/null 2>&1; then echo "imagemagick is not installed, imagemagick identify & convert will not work properly"; exit 1; fi
   if ! pngcheck >/dev/null 2>&1; then echo "pngcheck is not installed, checking corrupt files will not work properly"; fi
   if [ -z "$input" ]||[ -z "$sort" ]||[ -z "$scale" ]; then echo -e "\n\n\n\n\n\n\n"; fi
   if [ -z "$input" ]; then echoargs; echo -ne "Folder:\n"; read -r input; echoargs; fi
   if [ -z "$input" ]; then echo "No folder entered, exiting"; exit 1; fi
   if [ -z "$scale" ]; then echoargs; echo -ne "Enter the scale factor:\n"; read -r -n 1 scale; echoargs; export scale; fi
   if [ -z "$scale" ]; then echo "No scale entered, default is 4"; scale=4; fi
		cd "$input" || exit; nameshort=$(dirname "$input")
		if [[ -z $output ]]; then convertedfolder=$nameshort/${scale}xHR; output=$convertedfolder; else convertedfolder=$output; fi
		mkdir "$convertedfolder" >/dev/null 2>&1
   if [ -z "$sort" ]; then echo -ne "Sort by age or name? [1]age [2]name:\n"; read -r -n 1 sort; echoargs; fi
   if [ -z "$sort" ]; then echo "No sort entered, defaulting to age"; sort=1; fi
# create ffmpegconv command (btw it doesnt use ffmpeg lol)
declare -x convertedfolder input scale

function ffmpegconv() {
file="$1"; filext=.${file##*.}
filename=$(basename "$file"); filename=${filename%.*}
fileAge=$(find "$1" -printf '%T+')
if [[ $filext =~ .jpg ]] || [[ $filext =~ .png ]] || [[ $filext =~ .jpeg ]] || [[ $filext =~ .PNG ]]
   then if [[ ! -f "$convertedfolder/$filename.png" ]]; then
   imagewidth=$(identify -ping -format "%w" "$file") && imageheight=$(identify -ping -format "%h" "$file")
      if ! ((imagewidth % scale)); then if ! ((imageheight % scale)); then
            echo -e "${white}▏${fileAge} ▏${green} ---- conv ${white}▏${green} ./$filename$filext${red}"
            magick convert "$file" -strip -alpha off -define png:color-type=2 "$convertedfolder/$filename.png" 
         else echo -e "${white}▏${fileAge} ▏${yellow} -/%$scale ---- ${white}▏${yellow} ./$filename$filext"; fi
      else echo -e "${white}▏${fileAge} ▏${yellow} -/%$scale ---- ${white}▏${yellow} ./$filename$filext"; fi
   else echo -e "${white}▏${fileAge} ▏${yellow} exis ---- ${white}▏${cyan} ./$filename$filext"; fi
else echo -e "${white}▏${fileAge} ▏${yellow} /img ---- ${white}▏${red} ./$filename$filext"; fi
}; export -f ffmpegconv

# processing
IFS=$OLDIFS; OLDIFS=$IFS; IFS=$'\n'
if [[ $sort == 1 ]]; then   # sort by age
   if [[ -z $tmpdir ]]; then find "$input" -type f -printf "%T+,%p\n" | sort -r | cut -d, -f2 | parallel ffmpegconv
   else find "$input" -type f -printf "%T+,%p\n" | sort -r | cut -d, -f2 | parallel --tmpdir "$tmpdir" ffmpegconv; fi
elif [[ $sort == 2 ]]; then   # sort by full name
   if [[ -z $tmpdir ]]; then find "$input" -type f -printf "%p,%T+\n" | sort | cut -d, -f1 | parallel ffmpegconv
   else find "$input" -type f -printf "%p,%T+\n" | sort | cut -d, -f1 | parallel --tmpdir "$tmpdir" ffmpegconv; fi
   fi
if [[ -z "$convert" ]]; then echo -ne "${default}would you like to check the converted files for convertion? ([y]/n)"; read -r -n 1 convert; fi
if [ -z "$convert" ]; then echo -e "\e[1A\033[2KNothing entered, default is y"; convert=y; fi
echo
if [ -f "$(dirname "$0")/.yes.tmp" ]; then rm "$(dirname "$0")/.yes.tmp"; fi
if [ -f "$(dirname "$0")/.yes2.tmp" ]; then rm "$(dirname "$0")/.yes2.tmp"; fi

if [[ $convert == y ]]; then
mkdir "$(dirname "$input")/${scale}xLR" >/dev/null 2>&1


function checkfiles {
      file="$2"; filext=.${file##*.}
filename=$(basename "$file"); filename=${filename%.*}
if [[ ! -f "$LRfolder/$filename$filext" ]]; then
if pngcheck "$file" >/dev/null 2>&1; then
     echo -e "${lightblue} pngcheck | conv  ${white}| $LRfolder/$filename$filext"
   echo conv : "$file" >> "$1/.yes.tmp"
else
           echo -e "${red} pngcheck | del   ${white}| $LRfolder/$filename$filext"
   echo del   : "$file" >> "$1/.yes.tmp"; return; fi
if identify "$file" >/dev/null 2>&1; then
     echo -e "${lightblue} magick   | conv  ${white}| $LRfolder/$filename$filext"
   echo conv : "$file" >> "$1/.yes.tmp"
else
           echo -e "${red} magick   | del   ${white}| $LRfolder/$filename$filext"
   echo del   : "$file" >> "$1/.yes.tmp"; fi
else echo -e "${lightblue} skip     | skip  ${white}| $LRfolder/$filename$filext"; fi
}; export -f checkfiles

   LRfolder=$(dirname "$input")/${scale}xLR; export LRfolder
   basedir=$(dirname "$0")
   echo -e "${white}${italic}checking files using pngcheck and imagemagick...${default}\n"
   if [[ -z $tmpdir ]]; then find "$convertedfolder" -type f | sort -r | parallel checkfiles "$basedir" {}
   else find "$convertedfolder" -type f | sort -r | parallel --tmpdir "$tmpdir" checkfiles "$basedir" {}; fi
   find "$convertedfolder" -type f | sort -r | parallel checkfiles "$basedir" {}
   OLDIFS=$IFS; IFS=$'\n'
   < "$basedir/.yes.tmp" sort -r | uniq > "$basedir/.yes2.tmp"
   echo -e "${white}${italic}processsing files with list...${default}\n"

   function processconv {
      file="$(echo "$1" | cut -d: -f2)"; file=${file:1} 
	      if [[ $1 =~ .*conv.* ]]; then
         scaled=$(bc -l <<< 100/$scale | sed -e 's/[0]*//g')%
            echo -e "${green}${italic}$scaled converting ${file}${default}"
			   magick convert "$file" -strip -alpha off -define png:color-type=2 -resize "$scaled" "$LRfolder/$(basename "$file")"
		   elif [[ $1 =~ .*del.* ]]; then
			   echo -e "${red} deleting ${file}"
			   rm "$file"
		      fi
   }; export -f processconv


if [[ -z $tmpdir ]]; then < "$basedir/.yes2.tmp" parallel processconv
else < "$basedir/.yes2.tmp" parallel --tmpdir "$tmpdir" processconv {}; fi
#if temp files exist, delete them
if [ -f "$basedir/.yes.tmp" ]; then rm "$basedir/.yes.tmp"; fi
if [ -f "$basedir/.yes2.tmp" ]; then rm "$basedir/.yes2.tmp"; fi
else echo -e "${white}${italic}skipping conversion...${default}"; fi
echo -e '\ndone'
