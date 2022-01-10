#!/bin/bash
echo -e "\033[1;37mHi! this script was made to mount the ram to the drive.
Please, enter the folder you want to mount the ram to.
Make sure this folder is empty.\033[0m
---------------------------------------------------------------------"
   while getopts ":hp:s:" opt; do
      case $opt in
         h) echo ""; help=1; break;;
         p) path="$OPTARG";;
         s) size="$OPTARG";;
         *) echo "invalid option: $OPTARG";;
      esac
      done
   if [[ $help = 1 ]]; then
      echo -e "These arguments are optional. They can be used to speed up the process *very* slightly.
         -h:        display this help!
         -p:        input folder, skip prompt
         -s:        size of the ram drive in GB, skip prompt"
         exit 1
      fi
# test if path was given
if [[ -z $path ]]; then
    read -r -p "Enter the path: " path
   else 
    echo "folder=$path"
fi
if [[ -z $size ]]; then
    read -r -p "Enter the size of the ram drive in GB:" size
   else 
    echo "size=$size"
fi

sudo mount -t tmpfs -o size="$size"g tmpfs "$path"
echo -e "\033[1;37mmounted to $path. Continue to unmount.\033[0m"
read -n 1 -s -r -p "Press any key to continue"
sudo umount "$path"

exit
