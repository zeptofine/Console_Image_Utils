#!/bin/bash
echo -e "\033[1;37mHi! this script was made to convert thousands of files to another format.
Oh, also they can't be videos or gifs or swfs or anything like that. pngs, and jpegs are the only ones converted so far. the rest will be copied.
If you want to change that to allow bmps or smth, around line 82 is where the extension check occurs. simply add || [[ $filext =~ .??? ]] to the end before ';then'.
you can also use command line arguments! use the -h flag for more context. most of my scripts use the same arguments, with a few exceptions.\033[0m

---------------------------------------------------------------------"


# check for arguments
   while getopts ":hs:i:p:q:Q:" opt; do
      case $opt in
         h) echo ""; help=1; break;;
         s) sort=$OPTARG; if [[ $sort = 1 ]]; then echo "sorting by age";elif [[ $sort = 2 ]]; then echo "sorting by name";fi ;;
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

# parallel prompt
   if [[ -z "$parallel" ]]; then
      echo -e "Do you want to enable parallel processing or stick to individual files? ([0],1)"
      echo -e "parallel processing:([0],1):"; read -r parallel; fi
   if [ -z "$parallel" ]; then echo "No parallel entered, default is 0"; parallel=0; fi

   cd "$input" || exit
   nameshort=${input%*/}
   convertedfolder=$nameshort-Converted-Jpg; mkdir "$convertedfolder" > /dev/null 2>&1
   echo "$convertedfolder/"
   export convertedfolder
   export input
#check if ffmpeg is a valid command
   Ffmpegcheck=$(command -v ffmpeg)
   if [ -z "$Ffmpegcheck" ];
      then echo "ffmpeg is not installed, exiting"; exit 1;fi

#get list of files
   if [[ -z "$sort" ]]; then
      echo -e "Sort by age or name? [1]age [2]name: "; read -r sort; fi
      if [ -z "$sort" ]; then 
         echo "No sort entered, defaulting to age"; sort=1; fi



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
   convertedfile="$convertedfolder/$subfolder/$filename.jpg"
   convertedcopy="$convertedfolder/$subfolder/$filename$filext"
   paddi="$(echo "$i" | sed -e :a -e 's/^.\{1,4\}$/_&/;ta')"
   if [[ "$filext" == ".jpg" ]] || [[ "$filext" == ".jpeg" ]] || [[ "$filext" == ".png" ]] || [[ "$filext" == ".PNG" ]]; then
      if [[ ! -f "$convertedfile" ]]; then
         ffmpeg -y -i "$file" -compression_level 80 -vf "scale='min(2048,iw)':-1" -pix_fmt yuv420p "$convertedfile" > /dev/null 2>&1
         echo -e "${white} ${fileAge} |${green} conv ---- ---- ${white}| ${brown}$convertedfile"
         else
            echo -e "${white} ${fileAge} |${yellow} ---- ---- skip ${white}| ${brown}$convertedfile"
            fi
      else
         if [[ ! -f "$convertedcopy" ]]; then
            cp "$file" "$convertedcopy" > /dev/null 2>&1
            echo -e "${white} ${fileAge} |${red} ---- copy ---- ${white}| ${brown}$convertedcopy"
            else 
               echo -e "${white} ${fileAge} |${yellow} ---- ---- skip ${white}| ${brown}$convertedcopy"
            fi
      fi
}
export -f ffmpegconv

if [[ $parallel = 0 ]]; then (
   OLDIFS=$IFS; IFS=$'\n'
   if [[ $sort = 1 ]]; then 
      find "$input" -type f -printf "%T+,%p\n" | sort -r | cut -d, -f2 | parallel ffmpegconv
      elif [[ $sort = 2 ]]; then 
         find "$input" -type f -printf "%p,%T+\n" | sort | cut -d, -f1 | parallel ffmpegconv 
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
      convertedfile="$convertedfolder/$subfolder/$filename.jpg"
      convertedcopy="$convertedfolder/$subfolder/$filename$filext"
      paddi="$(echo "$i" | sed -e :a -e 's/^.\{1,4\}$/_&/;ta')"
      if [[ "$filext" == ".jpg" ]] || [[ "$filext" == ".jpeg" ]] || [[ "$filext" == ".png" ]] || [[ "$filext" == ".PNG" ]]; then
         if [[ ! -f "$convertedfile" ]]; then
            ffmpeg -y -i "$file" -compression_level 80 -vf "scale='min(2048,iw)':-1" -pix_fmt yuv420p "$convertedfile" > /dev/null 2>&1
            echo -e "${white} ${ArrayAge[$i]%.*} |${lightblue} $paddi ${white}|${green} conv ---- ---- ${white}| ${brown}$convertedfile"
            else
               echo -e "${white} ${ArrayAge[$i]%.*} |${lightblue} $paddi ${white}|${yellow} ---- ---- skip ${white}| ${brown}$convertedfile"
               fi
         else
            if [[ ! -f "$convertedcopy" ]]; then
               cp "$file" "$convertedcopy" > /dev/null 2>&1
               echo -e "${white} ${ArrayAge[$i]%.*} |${lightblue} $paddi ${white}|${red} ---- copy ---- ${white}| ${brown}$convertedcopy"
               else 
                  echo -e "${white} ${ArrayAge[$i]%.*} |${lightblue} $paddi ${white}|${yellow} ---- ---- skip ${white}| ${brown}$convertedcopy"
               fi
         fi
   ) done
) else ( echo parallel is not set to [0] or 1; exit 1; ) fi 
exit 1




