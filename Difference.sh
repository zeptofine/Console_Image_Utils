#!/bin/bash
   white='\033[1;37m'; yellow='\033[1;33m'; red='\033[0;31m'; green='\033[1;32m'; lightblue='\033[1;34m'; brown='\033[0;33m'; cyan='\033[0;36m'
   bold='\e[1m'; italic='\e[3m'; underline='\e[4m'; strike='\e[9m'; default='\e[0m'
   export white yellow red green cyan lightblue brown bold italic underline strike default 
echo -e "${white}Hi! this script was made to convert thousands of files to another format.
Oh, also they can't be videos or gifs or swfs or anything like that. pngs, and jpegs are the only ones converted so far. the rest will be copied.
If you want to change that to allow bmps or smth, around line 82 is where the extension check occurs. simply add || [[ $filext =~ .??? ]] to the end before ';then'.
you can also use command line arguments! use the -h flag for more context. most of my scripts use the same arguments, with a few exceptions.${default}

---------------------------------------------------------------------"
      while getopts "hi:o:t:l:" opt; do
   case $opt in
   h) echo -e "These arguments are optional. They can be used to automate the process so you don't have to input them every time.${bold}${underline}${white}
prefix   defaults               description          ${default}${white}
${white}|${default} -h  ${white}|${default}             ${white}|${default}display current help         
${white}|${default} -i  ${white}|${default}             ${white}|${default}input folder, skip prompt
${white}|${default} -o  ${white}|${default} (scale)xHR  ${white}|${default}output folder
${white}|${default} -l  ${white}|${default} [l]/c       ${white}|${default}link or copy, skip prompt
${white}|${default} -t  ${white}|${default} default     ${white}|${default}tmpdir for parallel processing${default}"; exit 0;;
   i) input="$OPTARG";; o) output="$OPTARG";; t) tmpdir="$OPTARG";; l) link="$OPTARG";; \?) echo "Invalid option -$OPTARG" >&2;;
esac; done

#check if imagemagick & pngcheck is a valid command
   if ! command -v magick >/dev/null 2>&1;then echo "imagemagick is not installed, identify & convert will not work properly"; exit 127; fi
   if ! command -v ffmpeg >/dev/null 2>&1;then echo "ffmpeg is not installed, conversion will not work properly"; fi
   if ! command -v parallel >/dev/null 2>&1;then echo "parallel is not installed, this script will not work properly"; exit 127; fi
#check if any inputs are unnacounted for
   if [ -z "$input" ]; then echo -e "Folder:"; read -r input; fi
   if [ -z "$input" ]; then echo "No folder entered, exiting"; exit 1; fi
      cd "$input" || exit
   if [[ -z $output ]]; then convertedfolder=$(dirname "$input")/$(basename "$input")-converted-Jpg; output=$convertedfolder; else convertedfolder=$output; fi
      mkdir "$convertedfolder" >/dev/null 2>&1
         echo "$convertedfolder/"
   if [[ -z $tmpdir ]]; then tmpdir=$(dirname "$0"); fi
   if [ -z "$link" ]; then echo -e "Do you want to link or copy? ([l]/c): "; read -r -n 1 link; fi
   if [ -z "$link" ]; then echo "No link option entered, defaulting to link..."; link="l"; fi
declare -x convertedfolder input tmpdir link

function convlist() {
   file="$1"; filext=.${file##*.}
   filefolder=${file%/*}
   basename=${file##*/}
   subfolder=${filefolder#"$input"}
   if  [[ ! -d "$convertedfolder/$subfolder" ]]; then mkdir "$convertedfolder/$subfolder"; fi
   if [[ $filext =~ .jpg ]] || [[ $filext =~ .png ]] || [[ $filext =~ .jpeg ]] || [[ $filext =~ .PNG ]]; then
         echo -e "conv:$subfolder/$basename"
   else  echo -e "copy:$subfolder/$basename"
      fi
}; export -f convlist
if [[ $link =~ [lL] ]]; then
copyjob() { 
      file=${*}; file=${file:5}
      # echo -e "$file\n"
      echo ln -s "$input$file" "$convertedfolder$file"
   }; export -f copyjob
else
copyjob() { 
      file=${*%:*};
      echo cp "$input$file" "$convertedfolder$file"
   }; export -f copyjob
fi
convertjob() {
      file=${*##*:}
      filext=.${file##*.}
      filefolder=${file%/*}
      basename=${file##*/}
      subfolder=${filefolder#"$input"}
      magick "$input$file" -resize "${2}x" "$convertedfolder/$subfolder/$basename"

         cp "$input$file" "$convertedfolder/$subfolder/$basename"
   }; export -f convertjob 
IFS=$'\n'
#find "$input" -type f,l -printf "%T+,%p\n" | sort -r | cut -d, -f2 | parallel --bar --tmpdir "$tmpdir" convlist {} >> "$tmpdir/convlist.txt"
< "$tmpdir/convlist.txt" grep "copy:"| parallel --bar --tmpdir "$tmpdir" copyjob {} 
#read -r -d '' -a convarray < <(find "$input" -type f,l -printf "%T+,%p\n" | sort -r | cut -d, -f2 | parallel --bar --tmpdir "$tmpdir" convlist {})
#echo "${convarray[*]}" | grep copy | parallel --bar --tmpdir "$tmpdir" copyjob {}

exit
# exit
# if [[ $parallel = 0 ]]; then (
#    OLDIFS=$IFS; IFS=$'\n'
#    if [[ $sort = 1 ]]; then 
#       find "$input" -type f -printf "%T+,%p\n" | sort -r | cut -d, -f2 | parallel ffmpegconv
#       elif [[ $sort = 2 ]]; then 
#          find "$input" -type f -printf "%p,%T+\n" | sort | cut -d, -f1 | parallel ffmpegconv 
#       fi 
#    IFS=$OLDIFS
# ) elif [[ $parallel = 1 ]]; then (
# OLDIFS=$IFS; IFS=$'\n'
#    if [[ $sort = 1 ]]; then 
#       mapfile -t fileArray < <(find "$input" -type f -printf "%T+,%p\n" | sort -r | cut -d, -f2 ) && mapfile -t ArrayAge < <(find "$input" -type f -printf "%T+,%p\n" | sort -r | cut -d, -f1 ) # create array of files and array of ages in order of age
#       elif [[ $sort = 2 ]]; then 
#          mapfile -t fileArray < <(find "$input" -type f -printf "%p,%T+\n" | sort | cut -d, -f1 ) && mapfile -t ArrayAge < <(find "$input" -type f -printf "%p,%T+\n" | sort | cut -d, -f2 ); # create array of files and array of ages in order of name
#       fi 
# IFS=$OLDIFS
#    for (( i=0; i<${#fileArray[@]}; i++ )); do (
#       file="${fileArray[$i]}"; filext=.${file##*.}
#       filefolder=$(dirname "$file")
#       filename=$(basename "$file")
#       filename=${filename%.*}
#       subfolder=$(basename "$filefolder")
#       if  [[ ! -d "$convertedfolder/$subfolder" ]]; then mkdir "$convertedfolder/$subfolder"; fi
#       convertedfile="$convertedfolder/$subfolder/$filename.jpg"
#       convertedcopy="$convertedfolder/$subfolder/$filename$filext"
#       paddi="$(echo "$i" | sed -e :a -e 's/^.\{1,4\}$/_&/;ta')"
#       if [[ "$filext" == ".jpg" ]] || [[ "$filext" == ".jpeg" ]] || [[ "$filext" == ".png" ]] || [[ "$filext" == ".PNG" ]]; then
#          if [[ ! -f "$convertedfile" ]]; then
#             ffmpeg -y -i "$file" -compression_level 80 -vf "scale='min(2048,iw)':-1" -pix_fmt yuv420p "$convertedfile" > /dev/null 2>&1
#             echo -e "${white} ${ArrayAge[$i]%.*} |${lightblue} $paddi ${white}|${green} conv ---- ---- ${white}| ${brown}$convertedfile"
#             else
#                echo -e "${white} ${ArrayAge[$i]%.*} |${lightblue} $paddi ${white}|${yellow} ---- ---- skip ${white}| ${brown}$convertedfile"
#                fi
#          else
#             if [[ ! -f "$convertedcopy" ]]; then
#                cp "$file" "$convertedcopy" > /dev/null 2>&1
#                echo -e "${white} ${ArrayAge[$i]%.*} |${lightblue} $paddi ${white}|${red} ---- copy ---- ${white}| ${brown}$convertedcopy"
#                else 
#                   echo -e "${white} ${ArrayAge[$i]%.*} |${lightblue} $paddi ${white}|${yellow} ---- ---- skip ${white}| ${brown}$convertedcopy"
#                fi
#          fi
#    ) done
# ) else ( echo parallel is not set to [0] or 1; exit 1; ) fi 
# exit 1