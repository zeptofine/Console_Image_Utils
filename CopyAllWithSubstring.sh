#!/bin/bash
echo -e "\033[1;37mHi! this script was made to convert thousands of files to another format.
Oh, also they can't be videos or gifs or swfs or anything like that. pngs, and jpegs are the only ones converted so far. the rest will be copied.
If you want to change that to allow bmps or smth, around line 82 is where the extension check occurs. simply add || [[ $filext =~ .??? ]] to the end before ';then'.
you can also use command line arguments! use the -h flag for more context. most of my scripts use the same arguments, with a few exceptions.\033[0m

---------------------------------------------------------------------"

# check for arguments
   while getopts ":hS:s:i:p:q:Q:" opt; do
      case $opt in
         h) echo ""; help=1; break;;
         S) sort=$OPTARG; if [[ $sort = 1 ]]; then echo "sorting by age";elif [[ $sort = 2 ]]; then echo "sorting by name";fi ;;
         s) substring="$OPTARG"; echo "substring=$substring";;
         i) input="$OPTARG"; echo "Folder=$input";;
         p) parallel="$OPTARG"; echo "parallel=$parallel";;
         *) echo "invalid option: $OPTARG";;
      esac
      done

# echo help dialog
   if [[ $help = 1 ]]; then
      echo -e "These arguments are optional. They can be used to speed up the process *very* slightly.
         -h:        display this help!
         -s: [1],2  sort by age or name, skip prompt
         -i:        input folder, skip prompt
         -p: [0],1  enable parallel processing, skip prompt. (parallel is *much* faster, but i haven't tested it as much)"
         exit 1
      fi

# folder prompt
   if [[ -z "$input" ]]; then
      echo -e "Enter the folder you want to create: "; read -r input; fi
   if [ -z "$input" ]; then echo "No folder entered, exiting"; exit 1; fi

# substring prompt
   if [[ -z "$substring" ]]; then
      echo -e "Enter the substring you want to search for: "; read -r substring; fi
   if [ -z "$substring" ]; then echo "No substring entered, exiting..."; exit 1; fi

# sort prompt
   if [[ -z "$sort" ]]; then
      echo -e "Sort by age or name? [1]age [2]name: "; read -r sort; fi
      if [ -z "$sort" ]; then 
         echo "No sort entered, defaulting to age"; sort=1; fi

# parallel prompt
   if [[ -z "$parallel" ]]; then
      echo -e "Do you want to enable parallel processing or stick to individual files? ([0],1)"
      echo -e "parallel processing:([0],1):"; read -r parallel; fi
   if [ -z "$parallel" ]; then echo "No parallel entered, default is 0"; parallel=0; fi

   cd "$input" || exit
   nameshort=${input%*/}
   convertedfolder=$nameshort-Copied-$substring; mkdir "$convertedfolder" > /dev/null 2>&1
   echo "$convertedfolder/"
   export convertedfolder
   export input

white='\033[1;37m'; yellow='\033[1;33m'; red='\033[0;34m'; green='\033[1;32m'; lightblue='\033[1;34m'; brown='\033[0;33m'
export white; export yellow; export red; export green; export lightblue; export brown

function ffmpegconv() {
      file="$1"; filext=.${file##*.}
      filefolder=$(dirname "$file")
      filename=$(basename "$file")
      filename=${filename%.*}
      subfolder=$(basename "$filefolder")
      fileAge=$(stat -c %y "$file")
      fileAge=${fileAge:0:19}
      if  [[ ! -d "$convertedfolder/$subfolder" ]]; then mkdir "$convertedfolder/$subfolder"; fi
      convertedfile="$convertedfolder/$subfolder/$filename$filext"
      paddi="$(echo "$i" | sed -e :a -e 's/^.\{1,4\}$/_&/;ta')"
         if [[ ! -f "$convertedfile" ]]; then
            cp "$file" "$convertedfile" > /dev/null 2>&1
            echo -e "${white} ${fileAge} ${white}|${green} copy ---- ${white}|${green} $convertedfile"
            else
               echo -e "${white} ${fileAge} ${white}|${yellow} ---- skip ${white}|${yellow} $convertedfile"
            fi
}
export -f ffmpegconv

if [[ $parallel = 0 ]]; then (
   OLDIFS=$IFS; IFS=$'\n'
   if [[ $sort = 1 ]]; then 
      find "$input" -type f -name "*$substring*" -printf "%T+,%p\n" | sort -r | cut -d, -f2 | parallel ffmpegconv
      elif [[ $sort = 2 ]]; then 
         find "$input" -type f -name "*$substring*" -printf "%p,%T+\n" | sort | cut -d, -f1 | parallel ffmpegconv 
      fi 
   IFS=$OLDIFS
) elif [[ $parallel = 1 ]]; then (
OLDIFS=$IFS; IFS=$'\n'
   if [[ $sort = 1 ]]; then 
      mapfile -t fileArray < <(find "$input" -type f -name "*$substring*" -printf "%T+,%p\n" | sort -r | cut -d, -f2 ) && mapfile -t ArrayAge < <(find "$input" -type f -name "*$substring*" -printf "%T+,%p\n" | sort -r | cut -d, -f1 ) # create array of files and array of ages in order of age
      elif [[ $sort = 2 ]]; then 
         mapfile -t fileArray < <(find "$input" -type f -name "*$substring*" -printf "%p,%T+\n" | sort | cut -d, -f1 ) && mapfile -t ArrayAge < <(find "$input" -type f -name "*$substring*" -printf "%p,%T+\n" | sort | cut -d, -f2 ); # create array of files and array of ages in order of name
      fi 
IFS=$OLDIFS
   for (( i=0; i<${#fileArray[@]}; i++ )); do (
      file="${fileArray[$i]}"; filext=.${file##*.}
      filefolder=$(dirname "$file")
      filename=$(basename "$file")
      filename=${filename%.*}
      subfolder=$(basename "$filefolder")
      if  [[ ! -d "$convertedfolder/$subfolder" ]]; then mkdir "$convertedfolder/$subfolder"; fi
      convertedfile="$convertedfolder/$subfolder/$filename$filext"
      paddi="$(echo "$i" | sed -e :a -e 's/^.\{1,4\}$/_&/;ta')"
         if [[ ! -f "$convertedfile" ]]; then
            cp "$file" "$convertedfile" > /dev/null 2>&1
            echo -e "${white} ${ArrayAge[$i]%.*} |${lightblue} $paddi ${white}|${green} copy ---- ${white}|${green} $convertedfile"
            else
               echo -e "${white} ${ArrayAge[$i]%.*} |${lightblue} $paddi ${white}|${yellow} ---- skip ${white}|${yellow} $convertedfile"
            fi
   ) done
) else ( echo parallel is not set to [0] or 1; exit 1; ) fi 
exit 1