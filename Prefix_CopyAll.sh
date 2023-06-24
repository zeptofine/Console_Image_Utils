#!/bin/bash
IFS=$'\n'
echo -e "\033[1;37m   Hi! this script was made to copy thousands of files to another folder.
you can use command line arguments! use the -h flag for more context. most of my scripts use the same arguments, with a few exceptions.\033[0m

---------------------------------------------------------------------"

# check for arguments
while getopts "hs:i:l:" opt; do
   case $opt in
   h)
      echo ""
      help=1
      break
      ;;
   s)
      substring="$OPTARG"
      echo "substring=$substring"
      ;;
   i)
      input="$OPTARG"
      echo "Folder=$input"
      ;;
   l)
      link="$OPTARG"
      echo "Link=$link"
      ;;
   *) echo "invalid option: $OPTARG" ;;
   esac
done

# echo help dialog
if [[ $help = 1 ]]; then
   echo -e "These arguments are optional. They can be used to speed up the process *very* slightly.
         -h:        display this help!
         -s:        substring to search for in file names
         -l         link / copy to another folder
         -i:        input folder, skip prompt"
   exit 1
fi

# folder prompt
if [[ -z "$input" ]]; then
   echo -e "Enter the folder you want to create: "
   read -r input
fi
if [ -z "$input" ]; then
   echo "No folder entered, exiting"
   exit 1
fi

# substring prompt
if [[ -z "$substring" ]]; then
   echo -e "Enter the substring you want to search for: "
   read -r substring
fi
if [ -z "$substring" ]; then
   echo "No substring entered, exiting..."
   exit 1
fi

# link / copy prompt

echo -e "Do you want to link or copy? (l/c): "
read -r -n 1 link
if [ -z "$link" ]; then
   echo "No link option entered, defaulting to link..."
   link="l"
fi

cd "$input" || exit
nameshort=${input%*/}
convertedfolder=$nameshort-Copied-$substring
mkdir "$convertedfolder" >/dev/null 2>&1
echo -e "\n$convertedfolder/"
export convertedfolder input link

function ffmpegconv() {
   file="$1"
   filext=.${file##*.}
   filefolder=$(dirname "$file")
   filename=$(basename "$file")
   filename=${filename%.*}
   subfolder=$(basename "$filefolder")
   # get file age then replace whitespace with underscore
   fileAge=$(stat -c %y "$file")
   fileAge=${fileAge// /_}
   fileAge=${fileAge:0:19}
   if [[ ! -d "$convertedfolder/$subfolder" ]]; then mkdir "$convertedfolder/$subfolder"; fi
   convertedfile="$convertedfolder/$subfolder/$filename$filext"
   if [[ ! -f "$convertedfile" ]]; then if [[ $link = "l" ]]; then
      ln -s "$file" "$convertedfile"
   else
      cp "$file" "$convertedfile"
   fi; fi
}
export -f ffmpegconv
cd "$input" || exit
for i in $(locate "substring"); do
   ffmpegconv "$i"
done
cd "$OLDPWD" || exit
