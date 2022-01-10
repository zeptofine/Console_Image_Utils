#!/bin/sh
white='\033[1;37m'; default='\e[0m'
echo -e "${white}Hello! this script was made to create a download list for imgbrd-grabber. make sure you have a list of prefixes in a text file called prefixes.txt next to this script.
prefixes.txt should contain a list of prefixes, one per line.
you can also run this with a list of prefixes in the dialog. this is not advised since it will consider each prefix individual.
execute this script with the -s flag to sort the prefixes by name.
Edit the script to change the generation, mostly straightforward${default}"

   # To do
   # Introduce automatically downloading images from list gathered
   # Add cli arguments instead of relying on an external prefixes.txt
   
while getopts "s" opt; do
   case $opt in
      s) sort="sort";;
      \?) echo "Invalid option -$OPTARG" >&2 ;;
   esac; done
if [[ ! -f $(dirname "$0")/prefixes.txt ]]; then echo -ne "no prefixes.txt detected!"; exit 1
else echo "prefixes.txt detected."; fi
{
echo "{
    \"batchs\": ["
} > "$(dirname "$0")/Imgbrd-grabbergen.igl"
OLDIFS=$IFS
IFS=$'\n'
if [[ -z $sort ]]; then file=$(cat "$(dirname "$0")/prefixes.txt")
else file=$(< "$(dirname "$0")/prefixes.txt" $sort); fi
for i in $file; do { 
echo -ne ",
        {
            \"filename\": \"%search%-%websitename%/%date:format=yyyy-MM-dd-hh-mm-ss%_%rating%_%md5%.%ext%\",
            \"galleriesCountAsOne\": true,
            \"getBlacklisted\": false,
            \"page\": 1,
            \"path\": \"EnterPathHere\",
            \"perpage\": 60,
            \"postFiltering\": [
                \"-grabber:downloaded\"
            ],
            \"query\": {
                \"tags\": [
                    \"$i\"
                ]
            },
            \"site\": \"EnterSiteHere\",
            \"total\": 2000
        }"
} >> "$(dirname "$0")/Imgbrd-grabbergen.igl"
done

IFS=$OLDIFS

sed -i '3d' "$(dirname "$0")/Imgbrd-grabbergen.igl"
{
echo -ne "
    ],
    \"uniques\": [
    ],
    \"version\": 3
}"
} >> "$(dirname "$0")/Imgbrd-grabbergen.igl"
echo done.
