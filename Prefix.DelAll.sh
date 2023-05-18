#!/bin/bash\

while getopts ":hs:i:" opt; do
   case $opt in
   h)
      echo ""
      help=1
      break
      ;;
   s)
      sort=$OPTARG
      if [[ $sort = 1 ]]; then echo "sorting by age"; elif [[ $sort = 2 ]]; then
         echo "sorting by name"
         files
      fi
      ;;
   i)
      folder="$OPTARG"
      echo "Folder=$folder"
      ;;
   *) echo "invalid option: $OPTARG" ;;
   esac
done
# echo help dialog
if [[ $help = 1 ]]; then
   echo -e "These arguments are optional. They can be used to speed up the process *very* slightly.
         -h:        display this help!
         -s: [1],2  sort by age or name, skip prompt
         -i:        input folder, skip prompt"
   exit 1
fi

if [[ -z $input ]]; then
   echo "Folder to copy from: "
   read -r input
   if [[ -z $input ]]; then
      echo "No input folder given, exiting..."
      exit 1
   fi
fi
if [[ -z $substring ]]; then
   echo "Substring to look for: "
   read -r substring
   if [[ -z $substring ]]; then
      echo "No prefix given, exiting..."
      exit 1
   fi
fi
cd "$input" || exit
nameshort=${input%*/}
convertedfolder=$nameshort-Copied-$substring
mkdir "$convertedfolder" >/dev/null 2>&1
echo "$convertedfolder/"

OLDIFS=$IFS
IFS=$'\n'
if [[ -z "$sort" ]]; then
   echo -e "Sort by age or name? [1]age [2]name: "
   read -r sort
fi
if [ -z "$sort" ]; then
   echo "No sort entered, defaulting to age"
   sort=1
fi
if [[ $sort = 1 ]]; then
   mapfile -t fileArray < <(find "$folder" -type f -printf "%T+,%p\n" -name "*$PREFIX*" | sort -r | cut -d, -f2) && mapfile -t ArrayAge < <(find "$folder" -type f -printf "%T+,%p\n" -name "*$PREFIX*" | sort -r | cut -d, -f1) # create array of files and array of ages in order of age
elif [[ $sort = 2 ]]; then
   mapfile -t fileArray < <(find "$folder" -type f -printf "%p,%T+\n" -name "*$PREFIX*" | sort | cut -d, -f1) && mapfile -t ArrayAge < <(find "$folder" -type f -printf "%p,%T+\n" -name "*$PREFIX*" | sort | cut -d, -f2)
   file # create array of files and array of ages in order of name
fi
IFS=$OLDIFS

white='\033[1;37m'
lightblue='\033[1;34m'
green='\033[1;32m'

for ((i = 0; i < ${#fileArray[@]}; i++)); do
   (
      file="${fileArray[$i]}"
      rm "$file"
      paddi=$(echo "$i" | sed -e :a -e 's/^.\{1,4\}$/_&/;ta')
      echo -e "${white}${ArrayAge[$i]%.*} |${lightblue} $paddi ${white}|${green} $file"
   )
done
#  /dev/null 2>&1
