#!/bin/bash
echo -e "\033[1;37mHi! this script was made to help me create large folder thousands of images. They needed to be divisible by 8 because the project i was working on needed even dimensions for accuracy. 
it's not div 4 or 2 because when i set them to be div 4 or 2 I still got the errors for \033[1;33m'images not divisible by 4. resizing blah blah blah.'\033[1;37m sorry about that.
Oh, also they can't be videos or gifs or swfs or anything like that. pngs, and jpegs are the only ones allowed so far.
If you want to change that to allow bmps or smth, around line 53 is where the extension check occurs. simply add || [[ $filext =~ .??? ]] to the end before ';then'.
you can also use command line arguments! use the -h flag for more context.

---------------------------------------------------------------------"
#check for command line arguments
   while getopts ":hs:i:" opt; do
      case $opt in
         h) echo ""; help=1; break;;
         s) sort=$OPTARG; if [[ $sort = 1 ]]; then echo "sorting by age";elif [[ $sort = 2 ]]; then echo "sorting by name";fi ;;
         i) input="$OPTARG"; echo "Folder=$input";;
         *) echo "invalid option: $OPTARG";;
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
# folder prompt
   if [[ -z "$input" ]]; then
      echo -e "Enter the folder you want to create: "; read -r folder
      else folder=$input; fi
   if [ -z "$folder" ]; then echo "No folder entered, exiting"; exit 1; fi

# set sort and arrange arrays
   OLDIFS=$IFS; IFS=$'\n'
   if [[ -z "$sort" ]]; then
      echo -e "Sort by age or name? [1]age [2]name: "; read -r sort; fi
      if [ -z "$sort" ]; then 
         echo "No sort entered, defaulting to age"; sort=1; fi
   if [[ $sort = 1 ]]; then 
      mapfile -t fileArray < <(find "$folder" -type f -printf "%T+,%p\n" | sort -r | cut -d, -f2 ) && mapfile -t ArrayAge < <(find "$folder" -type f -printf "%T+,%p\n" | sort -r | cut -d, -f1 ) # create array of files and array of ages in order of age
      elif [[ $sort = 2 ]]; then 
         mapfile -t fileArray < <(find "$folder" -type f -printf "%p,%T+\n" | sort | cut -d, -f1 ) && mapfile -t ArrayAge < <(find "$folder" -type f -printf "%p,%T+\n" | sort | cut -d, -f2 ); file # create array of files and array of ages in order of name
      fi 
   IFS=$OLDIFS

   cd "$folder" || return ; cd ..; echo "$CWD"; echo "copying $folder into HR..."; mkdir ./HR
white='\033[1;37m'; yellow='\033[1;33m'; green='\033[1;32m'; lightblue='\033[1;34m'; red='\033[1;31m';


for (( i=0; i<${#fileArray[@]}; i++ )); do 
   file="${fileArray[$i]}"; filext=.${file##*.}; filefolder=${file%/*}; filefolder=${filefolder##*/}; filenam=${file%.*} 
   filenam=${filenam##*/}; filename=${filenam/$filefolder}; filename=${filename#.*}
   if [[ $filext =~ .jpg ]] || [[ $filext =~ .png ]] || [[ $filext =~ .jpeg ]] || [[ $filext =~ .PNG ]]; then
      if [[ ! -f "./HR/$filename$filext" ]]; then
         paddi=$(echo "$i" | sed -e :a -e 's/^.\{1,4\}$/_&/;ta')
         imagewidth=$(identify -ping -format "%w" "$file") && imageheight=$(identify -ping -format "%h" "$file")
         if ! (( imagewidth % 8 )); then
            if ! (( imageheight % 8 )); then
               imagepaddi="$(echo "$imagewidth" |sed -e :a -e 's/^.\{1,4\}$/_&/;ta') $(echo "$imageheight" | sed -e :a -e 's/^.\{1,4\}$/_&/;ta')"
               cp "$file" "./HR/$filename$filext"
               echo -e "${white}${ArrayAge[$i]%.*} |${lightblue} $paddi ${white}|${green} $imagepaddi ${white}|${green} $file"
               else echo -e "${white}${ArrayAge[$i]%.*} |${lightblue} $paddi ${white}|${yellow} -/%8- ----- ${white}|${red} $file"; fi
            else echo -e "${white}${ArrayAge[$i]%.*} |${lightblue} $paddi ${white}|${yellow} -/%8- ----- ${white}|${red} $file"; fi
         else echo -e "${white}${ArrayAge[$i]%.*} |${lightblue} $paddi ${white}|${yellow} ----- exist ${white}|${yellow} $file"; fi; fi
   done
exit
