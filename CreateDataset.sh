#!/bin/bash
echo -e "\033[1;37mHi! this script was made to convert thousands of files to another format.
Oh, also they can't be videos or gifs or swfs or anything like that. pngs, and jpegs are the only ones converted so far. the rest will be copied.
If you want to change that to allow bmps or smth, around line 82 is where the extension check occurs. simply add || [[ $filext =~ .??? ]] to the end before ';then'.
you can also use command line arguments! use the -h flag for more context. most of my scripts use the same arguments, with a few exceptions.\033[0m
requirements: imagemagick, and a folder with the files you want to convert.
I reccomend using the ramdisk script in the same folder as this script to speed up the process.
---------------------------------------------------------------------"


# check for arguments
   while getopts ":hs:i:p:t:o:" opt; do
      case $opt in
         h) echo ""; help=1; break;;
         s) sort=$OPTARG; if [[ $sort = 1 ]]; then echo "sorting by age";elif [[ $sort = 2 ]]; then echo "sorting by name";fi ;;
         i) input="$OPTARG"; echo "Folder=$input";;
         p) parallel="$OPTARG"; echo "parallel=$parallel";;
         t) tmpdir="$OPTARG"; echo "tmpdir=$tmpdir";;
         o) output="$OPTARG"; echo "output=$output";;
         *) echo "invalid option: $OPTARG";;
      esac
      done
#check if ffmpeg is a valid command
   Ffmpegcheck=$(command -v ffmpeg)
   if [ -z "$Ffmpegcheck" ];
      then echo "ffmpeg is not installed, exiting"; exit 1;fi
#check if ffmpeg is a valid command
   Ffmpegcheck=$(command -v identify)
   if [ -z "$Ffmpegcheck" ];
      then echo "imagemagick is not installed, imagemagick identify will not work properly"; exit 1;fi


# echo help dialog
   if [[ $help = 1 ]]; then
      echo -e "These arguments are optional. They can be used to speed up the process *very* slightly.
         -h:        display this help!
         -s: [1],2  sort by age or name, skip prompt
         -i:        input folder, skip prompt
         -p: [0],1  enable parallel processing, skip prompt. (parallel is *much* faster, and it's my focus right now)
         -t:        tmpdir for parallel processing, skip prompt
         -o:        output folder, instead of HR"
         exit 1
      fi

# folder prompt
   if [[ -z "$input" ]]; then
      echo -e "Enter the folder you want to create: "; read -r input; fi
   if [ -z "$input" ]; then echo "No folder entered, exiting"; exit 1; fi
# parallel prompt
   if [[ -z "$parallel" ]]; then
      echo -e "Do you want to enable parallel processing or stick to individual files? ([0],1)"
      echo -e "parallel processing:([0],1):"; read -r parallel; fi
   if [ -z "$parallel" ]; then echo "No parallel entered, default is 0"; parallel=0; fi

   
   cd "$input" || exit
   nameshort=${input%*/}
   nameshort=$(dirname "$nameshort")
   echo "$nameshort"

   #output prompt
   if [[ -z "$output" ]]; then
      convertedfolder=$nameshort/HR; else convertedfolder=$output; fi
   mkdir "$convertedfolder"> /dev/null 2>&1
   echo "$convertedfolder/"
   export convertedfolder
   export input
   if [[ -z "$sort" ]]; then
      echo -e "Sort by age or name? [1]age [2]name: "; read -r sort; fi
      if [ -z "$sort" ]; then 
         echo "No sort entered, defaulting to age"; sort=1; fi

white='\033[1;37m'; yellow='\033[1;33m'; red='\033[0;31m'; green='\033[1;32m'; lightblue='\033[1;34m'; brown='\033[0;33m'
export white; export yellow; export red; export green; export lightblue; export brown





function ffmpegconv() {
   file="$1"; filext=.${file##*.}
   filefolder=$(dirname "$file")
   filename=$(basename "$file")
   filename=${filename%.*}
   subfolder=$(basename "$filefolder")
   fileAge=$(stat -c %y "$file")
   fileAge=${fileAge:0:19}
   paddi="$(echo "$i" | sed -e :a -e 's/^.\{1,4\}$/_&/;ta')"
   if [[ $filext =~ .jpg ]] || [[ $filext =~ .png ]] || [[ $filext =~ .jpeg ]] || [[ $filext =~ .PNG ]]; then
      if [[ ! -f "$convertedfolder/$filename$filext" ]]; then
         imagewidth=$(identify -ping -format "%w" "$file") && imageheight=$(identify -ping -format "%h" "$file")
         if ! (( imagewidth % 4 )); then
            if ! (( imageheight % 4 )); then
               #imagepaddi="$(echo "$imagewidth" |sed -e :a -e 's/^.\{1,3\}$/_&/;ta') $(echo "$imageheight" | sed -e :a -e 's/^.\{1,3\}$/_&/;ta')"
               magick convert "$file" -strip -alpha off -define png:color-type=2 "$convertedfolder/$filename$filext" > /dev/null 2>&1
               echo -e "${white}${fileAge} |${green} ---- conv ${white}|${green} ./$filename$filext"
               else echo -e "${white}${fileAge} |${yellow} -/%8 ---- ${white}|${yellow} ./$filename$filext"; fi
            else echo -e "${white}${fileAge} |${yellow} -/%8 ---- ${white}|${yellow} ./$filename$filext"; fi
         else echo -e "${white}${fileAge} |${yellow} exis ---- ${white}|${red} ./$filename$filext"; fi; 
         else echo -e "${white}${fileAge} |${yellow} /img ---- ${white}|${red} ./$filename$filext";fi
}; export -f ffmpegconv

if [[ $parallel = 0 ]]; then (
   # check if tmpdir is set
   if [[ -z "$tmpdir" ]]; then
      echo -e "Enter a temporary folder to use for parallelization: "; read -r tmpdir; fi
   if [ -z "$tmpdir" ]; then echo "No tmpdir entered, continuing with caution..."; fi
   if [ ! -d "$tmpdir" ]; then echo "tmpdir does not exist, exiting"; exit 1; fi
   export tmpdir

   OLDIFS=$IFS; IFS=$'\n'
   if [[ $sort = 1 ]]; then 
      if [[ -z "$tmpdir" ]]; then
      find "$input" -type f -printf "%T+,%p\n" | sort -r | cut -d, -f2 | parallel ffmpegconv
      else
      find "$input" -type f -printf "%T+,%p\n" | sort -r | cut -d, -f2 | parallel --tmpdir "$tmpdir" ffmpegconv 
      fi
      elif [[ $sort = 2 ]]; then 
      if [[ -z "$tmpdir" ]]; then
         find "$input" -type f -printf "%p,%T+\n" | sort | cut -d, -f1 | parallel ffmpegconv 
         else 
         find "$input" -type f -printf "%p,%T+\n" | sort | cut -d, -f1 | parallel --tmpdir "$tmpdir" ffmpegconv 
         fi
      fi 
   IFS=$OLDIFS
) elif [[ $parallel = 1 ]]; then (
OLDIFS=$IFS; IFS=$'\n'
   if [[ $sort = 1 ]]; then 
      mapfile -t fileArray < <(find "$input" -type f -printf "%T+,%p\n" | sort -r | cut -d, -f2 ) && mapfile -t ArrayAge < <(find "$input" -type f -printf "%T+,%p\n" | sort -r | cut -d, -f1 ) # create array of files and array of ages in order of age
      elif [[ $sort = 2 ]]; then 
         mapfile -t fileArray < <(find "$input" -type f -printf "%p,%T+\n" | sort | cut -d, -f1 ) && mapfile -t ArrayAge < <(find "$input" -type f -printf "%p,%T+\n" | sort | cut -d, -f2 ); # create array of files and array of ages in order of name
      fi 
IFS=$OLDIFS
   for (( i=0; i<${#fileArray[@]}; i++ )); do (
      file="${fileArray[$i]}"; filext=.${file##*.}
      filefolder=$(dirname "$file")
      filename=$(basename "$file")
      filename=${filename%.*}
      subfolder=$(basename "$filefolder")
      if  [[ ! -d "$convertedfolder/$subfolder" ]]; then mkdir "$convertedfolder/$subfolder"; fi
      paddi="$(echo "$i" | sed -e :a -e 's/^.\{1,4\}$/_&/;ta')"
   if [[ $filext =~ .jpg ]] || [[ $filext =~ .png ]] || [[ $filext =~ .jpeg ]] || [[ $filext =~ .PNG ]]; then
      if [[ ! -f "./HR/$filename$filext" ]]; then
         paddi=$(echo "$i" | sed -e :a -e 's/^.\{1,4\}$/_&/;ta')
         imagewidth=$(identify -ping -format "%w" "$file") && imageheight=$(identify -ping -format "%h" "$file")
         if ! (( imagewidth % 8 )); then
            if ! (( imageheight % 8 )); then
               imagepaddi="$(echo "$imagewidth" |sed -e :a -e 's/^.\{1,4\}$/_&/;ta') $(echo "$imageheight" | sed -e :a -e 's/^.\{1,4\}$/_&/;ta')"
               magick convert "$file" -strip -alpha off -define png:color-type=2 "$convertedfolder/$filename$filext" > /dev/null 2>&1
               echo -e "${white}${ArrayAge[$i]%.*} |${lightblue} $paddi ${white}|${green} $imagepaddi ${white}|${green} ./$filename$filext"
               else echo -e "${white}${ArrayAge[$i]%.*} |${lightblue} $paddi ${white}|${yellow} -/%8- ----- ${white}|${red} ./$filename$filext"; fi
            else echo -e "${white}${ArrayAge[$i]%.*} |${lightblue} $paddi ${white}|${yellow} -/%8- ----- ${white}|${red} ./$filename$filext"; fi
         else echo -e "${white}${ArrayAge[$i]%.*} |${lightblue} $paddi ${white}|${yellow} ----- exist ${white}|${yellow} ./$filename$filext"; fi; fi
   ) done
) else ( echo parallel is not set to [0] or 1); fi 
exit