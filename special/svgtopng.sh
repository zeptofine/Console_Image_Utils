#!/bin/bash
# parse arguments, input, resolution
while getopts ":i:r:h" opt; do
  case $opt in
    i)
      input=$OPTARG
      ;;
    r)
      resolution=$OPTARG
      ;;
    \?)
      echo "Invalid option: -$OPTARG" >&2
      exit 1
      ;;
    :)
      echo "Option -$OPTARG requires an argument." >&2
      exit 1
      ;;
    h)
      echo "Usage: svgtopng.sh -i <input> -r <resolution>"
      exit 0
      ;;
  esac
done
# check if any arguments are missing
if [ -z "$input" ] || [ -z "$resolution" ]; then
  echo "Missing arguments"
  echo "Usage: svgtopng.sh -i <input> -r <resolution>"
  exit 1
fi
if [ -z "$resolution" ]; then
  echo "Missing resolution"
  echo "Usage: svgtopng.sh -i <input> -r <resolution>"
  exit 1
fi

cd "$input" || exit

mapfile -t svglist < <(find . -name "*.svg")


echo -e "\nConverting SVG to PNG; res:$resolution; number: ${#svglist[@]}\n"
# gnu parallel through svg list
function convert_svg_to_png {
    # echo -e "Converting $1 of ${#svglist[@]} files"
    if [ ! -f "${1%.*}.png" ]; then
        inkscape -z -o "${svglist[i]%.svg}.png" -w 2400 -h 2400 "$1" >> /dev/null 2>&1
    fi
}; export -f convert_svg_to_png
find . -name "*.svg" | parallel --progress "convert_svg_to_png {}"
# for i in "${!svglist[@]}"; do
#     echo -e "\033[1AConverting $i of ${#svglist[@]} files"
#     if [ ! -f "${svglist[$i]%.*}.png" ]; then
#         inkscape -z -o "${svglist[i]%.svg}.png" -w "$resolution" -h "$resolution" "${svglist[i]}" > /dev/null 2>&1
#     fi
    
#     done