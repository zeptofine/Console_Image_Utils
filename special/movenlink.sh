#!/bin/bash
echo -e "Move'n'Link"
echo -e "movenlink.sh moves a directory to a new location and links it to the old location.\n"
IFS=$'\n'
# get -i and -o with getopts
while getopts "i:o:" opt; do
  case $opt in
    i)in="$OPTARG";;
    o)out="$OPTARG";;
    \?)
      echo "Invalid option: -$OPTARG" >&2
      ;;
  esac
done
# check if -i and -o are set
if [ -z "$in" ] || [ -z "$out" ]; then
  echo -e "Usage: movenlink.sh -i <input> -o <output>"
  exit 1
fi
# functions from pure-sh-bible
    lstrip() {
        printf '%s\n' "${1##"$2"}"
    }
#check if output contains files
if [ -d "$out" ]; then
    mkdir "$out"
  fi

# cd to input directory
    cd "$in" || exit 1
# move input directory to output directory
    echo -e "Moving directory..."
    cp -r "$in" "$out"
# link output directory to input directory
    echo -e "Linking directory..."
    ln -s "$out" "${in%/*}"