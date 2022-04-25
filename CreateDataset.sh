#!/bin/bash
# formatting help
# https://gist.github.com/fnky/458719343aabd01cfb17a3a4f7296797#file-ansi-md
IFS=$'\n'
   white='\033[1;37m'; yellow='\033[1;33m'; red='\033[0;31m'; green='\033[1;32m'; lightblue='\033[1;34m'; brown='\033[0;33m'; cyan='\033[0;36m'
   bold='\e[1m'; italic='\e[3m'; underline='\e[4m'; strike='\e[9m'; default='\e[0m'
   export white yellow red green cyan lightblue brown bold italic underline strike default 
echo -e "${white}${bold}Hi! this script was made to create a dataset out of a folder of images.${default}
Oh, also they can't be videos or gifs or swfs or anything like that. pngs, and jpegs are the only ones converted so far. the rest will be ignored.
${underline}you can also use command line arguments!${default} use the -h flag for more context.
I reccomend using the ramdisk script in the same folder as this script to speed up the process. ${red}(make a dedicated folder for it)${default}
---------------------------------------------------------------------"
echo -e "\n\n\n\n${red}${bold}This script is broken at the moment and I do not have any plan to fix it due to pythons options.${default}"
echo -e "${white}${bold}Use the python script in the same folder to create a dataset instead.${default}"
exit
# check for arguments
while getopts "hi:o:t:x:c:m:z" opt; do
   case $opt in
   h) echo -e "These arguments are optional. They can be used to automate the process so you don't have to input them every time.
   ${bold}${underline}${white}
prefix | default |description          ${default}${white}
 -h               display current help         
 -i               input folder, skip prompt
 -o   (scale)xHR  output folder
 -t   default     tmpdir for parallel processing
 -x   1,2,[4],8   scale factor, skip prompt
 -m               minimum image size
 -c   [y]/n       convert files, skip prompt${default}
 -z               simulate, create list"; exit 0;;
   i) input="$OPTARG";; o) output="$OPTARG";; t) tmpdir="$OPTARG";;
   x) scale="$OPTARG";; c) convert="$OPTARG";; m) minres="$OPTARG" ;; 
   z) simulate="true";;
   \?) echo "Invalid option -$OPTARG" >&2;;
esac; done
#check if imagemagick & pngcheck is a valid command
   
   if ! command -v pngcheck >/dev/null 2>&1;then echo "pngcheck is not installed, checking corrupt pngs will not work properly"; fi
   if ! command -v jpeginfo >/dev/null 2>&1;then echo "jpeginfo is not installed, checking corrupt jpegs will not work properly"; fi
   

   if ! command -v magick >/dev/null 2>&1;then echo "imagemagick is not installed, identify & convert will not work properly"; exit 127; fi
   if ! command -v parallel >/dev/null 2>&1;then echo "parallel is not installed, this script will not work properly"; exit 127; fi
#check if any inputs are unnacounted for
   if [ -z "$input" ]; then echo -e "Folder:"; read -r input; fi
   if [ -z "$input" ]; then echo "No folder entered, exiting"; exit 1; fi
   if [ -z "$scale" ]; then echo -e "Enter the scale factor:"; read -r -n 1 scale; export scale; fi
   if [ -z "$scale" ]; then echo "No scale entered, default is 4"; scale=4; fi
      cd "$input" || exit;
   if [[ -z $output ]]; then HRFolder=${input%/*}/${scale}xHR; output=$HRFolder; else HRFolder=$output; fi
      mkdir "$HRFolder" >/dev/null 2>&1
      LRfolder=$(dirname "$input")/${scale}xLR
   if [[ -z $tmpdir ]]; then tmpdir=${0%/*}; fi
   if [[ -z $minres ]]; then minres=0; fi
declare -x HRFolder input scale tmpdir minres LRfolder
echo -e "Gathering lists...\n"

function ffmpegconv {
   file="$1"; filext=.${file##*.}
   if [[ $filext =~ .jpg ]] || [[ $filext =~ .png ]] || [[ $filext =~ .jpeg ]] || [[ $filext =~ .PNG ]]; then { # if input is an image
      if [[ ! -e "$HRFolder/${file##*/}" ]]; then { # if image has not been created
         # check if image is corrupt with pngcheck and jpeginfo
         if [[ $filext =~ .jpg ]] || [[ $filext =~ .jpeg ]]; then {
            if ! jpeginfo "$file" >> /dev/null; then echo "jpeginfo:$file"; return; fi
         } elif [[ $filext =~ .png ]] || [[ $filext =~ .PNG ]]; then {
            if ! pngcheck "$file" >> /dev/null; then echo "pngcheck:$file"; return; fi
         } fi;
         imagewidtheight=$(identify -strip -ping -format "%wx%h" "$file")
         if [[ ${imagewidtheight#*x} -lt $minres ]]||[[ ${imagewidtheight%x*} -lt $minres ]]; then { # if image is smaller than chosen minres
            echo "small:$minres>$imagewidtheight:${file}"; return
         } else {
            if (( ${imagewidtheight#*x} % scale == 0 )) && (( ${imagewidtheight%x*} % scale == 0 )); then # if all is well, link and convert
            echo "link:$file"
            
            fi
            } fi
         }; fi
      }; fi; }; export -f ffmpegconv
if [ ! -f "$(dirname "$input")/${scale}xHR.txt" ]; then
mapfile -t wksp < <(
find "$input" -type f,l -printf "%T+,%p\n" | sort -r | cut -d, -f2 | parallel --bar --tmpdir "$tmpdir" ffmpegconv {}
)
if [ -n "$simulate" ] ; then
for i in "${wksp[@]}"; do echo "$i" >> "$(dirname "$input")/${scale}xHR.txt"; done
fi
else 
echo "$(dirname "$input")/${scale}xHR.txt found! skipping list creation."
mapfile -t wksp < <(cat "$(dirname "$input")/${scale}xHR.txt")
fi

# functions from: https://github.com/dylanaraps/pure-sh-bible
   # https://github.com/dylanaraps/pure-sh-bible#get-the-directory-name-of-a-file-path
      dirname() {
         dir=${1:-.}
         dir=${dir%%"${dir##*[!/]}"}
         [ "${dir##*/*}" ] && dir=.
         dir=${dir%/*}
         dir=${dir%%"${dir##*[!/]}"}
         printf '%s\n' "${dir:-/}"
      }
export -f dirname


if [ -f "$(dirname "$input")/${scale}xHR_link.txt" ]; then rm "$(dirname "$input")/${scale}xHR_link.txt"; fi
if [ -f "$(dirname "$input")/${scale}xHR_convert.txt" ]; then rm "$(dirname "$input")/${scale}xHR_convert.txt"; fi
if [ -f "$(dirname "$input")/${scale}xHR_error.txt" ]; then rm "$(dirname "$input")/${scale}xHR_error.txt"; fi

echo -e "${white}sorting....${default}"
printf '%s\n' "${wksp[@]}" | grep -v -E "link" | sort >> "$(dirname "$input")/${scale}xHR_error.txt"
printf '%s\n' "${wksp[@]}" | grep "link" | sort | uniq >> "$(dirname "$input")/${scale}xHR_link.txt"
echo -e "${white}finding missing converted images...${default}"

function linkconv {
   file="$1"
   if [[ ! -e "$LRfolder/${file#*/}" ]]; then
   imagewidtheight=$(identify -strip -ping -format "%wx%h" "$file")
   echo "convert:$(( ${imagewidtheight%x*} / scale ))x$(( ${imagewidtheight#*x} / scale )):$file"
   fi
}; export -f linkconv
mapfile -t missing < <(
find "$HRFolder" -type f,l | sort | parallel --bar --tmpdir "$tmpdir" linkconv {} 
)
printf '%s\n' "${missing[@]}" | sort | uniq >> "$(dirname "$input")/${scale}xHR_convert.txt"

echo "list of errors saved at: $(dirname "$input")/${scale}xHR_error.txt"
# print error types
cut -d: -f1 < "$(dirname "$input")/${scale}xHR_error.txt" | uniq -c


# link files
if [ -f "$(dirname "$input")/${scale}xHR_link.txt" ]; then 
   echo -e "${green}linking...${default}"
   < "$(dirname "$input")/${scale}xHR_link.txt" sort -r | uniq | cut -d: -f2- | parallel --tmpdir "$tmpdir" ln -s {} "$HRFolder/{/}" &> /dev/null
   else echo -e "${yellow} all images have been linked beforehand!${default}"; fi

# convert prompt
if [ -z "$convert" ]; then read -r -n 1 -p "would you like to check the converted files for conversion? ([y]/n): " convert; fi
convert=${convert:-y}


# convert files
if [[ $convert == y ]]; then {
   
   export LRfolder
   if [ ! -d "$LRfolder" ]; then mkdir "$LRfolder"; fi
if [[ -f "$(dirname "$input")/${scale}xHR_convert.txt" ]]; then
# if Input and output folders are the same size in terms of files
if [ ! "$(find "$input" -type f,l | wc -l)" -eq "$(find "$LRfolder" -type f | wc -l)" ]; then
      mapfile -t convlist < <(cat "$(dirname "$input")/${scale}xHR_convert.txt")
      convertimages() {
         file="$(echo "$1" | cut -d: -f3-)"
         if [ ! -f "$LRfolder/${file##*/}" ]; then
         ratio="$(echo "$1" | cut -d: -f2 | tr ':' 'x')";
         convert -strip "$file" -resize "$ratio" "$LRfolder/${file##*/}" &>> "$(dirname "$input")/${scale}xHR_error.txt"
         fi
      }; export -f convertimages
      parallel --bar convertimages ::: "${convlist[@]}"
   else echo -e "${yellow} all images have been converted beforehand!${default}"; fi
   fi
} else echo -e "${white}${italic}skipping conversion...${default}"
fi

python "$(dirname "$0")/imgcheck.py" --rootdir "$LRfolder"
rm -r "$LRfolder"
mv "$(dirname "$input")/newLR" "$LRfolder"
python "$(dirname "$0")/imgcheck.py" --rootdir "$HRFolder"
rm -r "$HRFolder"
mv "$(dirname "$input")/newLR"   "$HRFolder"

# finishup
echo -e "${white}${italic}done!${default}\n"
if [ -f "$(dirname "$input")/${scale}xHR_link.txt" ]; then rm "$(dirname "$input")/${scale}xHR_link.txt"
fi
if [ -f "$(dirname "$input")/${scale}xHR_convert.txt" ]; then rm "$(dirname "$input")/${scale}xHR_convert.txt"
fi
