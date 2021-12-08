#!/bin/bash
#create .sh path
    parent_path=$( cd "$(dirname "${BASH_SOURCE[0]}")" || exit ; pwd -P )
    cd "$parent_path" || exit

    echo You need Imagemagick before you run this.
    echo To do: add a check for Imagemagick.
    echo also, Actually make a padding option, because currently it\'s just placeholder.
#Setup main variables
    read -p "Input:" file
    read -p "Individual or parallel? ([0],1)" Parallel
    if [ -z "$Parallel" ]; then Parallel=0; fi
    # ${file/$(basename $file)}
    xres=$(identify -ping -format "%w" $file)
    yres=$(identify -ping -format "%h" $file)
    echo $xres:$yres
    read -p "Tiling format (4:3 for 4 horizontal tiles, 3 vertical tiles.):" Tile
    read -p "Padding? ([0] for disabled):" Padding
    if [ -z "$Padding" ]; then Padding=0; fi
    read -p "Split or merge? ([0],1):" Workspace
    if [ -z "$Workspace" ]; then Workspace=0; fi
#fucky wucky tile math
    ytile=${Tile##*:}
    xtile=${Tile/${Tile##*:}}
    xtile=${xtile%?}
    echo $ytile x $xtile $Padding px
#tiles visualisation
for y in $(seq "$ytile"); do 
for x in $(seq "$xtile"); do
echo -ne "░░\u0020\u0020"
if [ "$x" == "$xtile" ]; then
echo
echo
fi
done
done
#create tiles
if [ "$Workspace" == "0" ]; then
echo creating tiles...
mkdir ${file/$(basename $file)}/Output
cd ${file/$(basename $file)}/Output || exit
    if [ "$Padding" == "0" ]; then
        for y in $(seq "$ytile"); do 
                for x in $(seq "$xtile"); do
                xcrop=$(expr $xres / $xtile)
                ycrop=$(expr $yres / $ytile)
                xoffset=$(expr $xcrop \* $(expr $x - 1 ))
                yoffset=$(expr $ycrop \* $(expr $y - 1 ))
                convert $file -ping -crop $(echo $xcrop)x$ycrop+$xoffset+$yoffset $(echo $y | awk '{printf "%03d\n", $0;}'),$(echo $x | awk '{printf "%03d\n", $0;}').png
                #This worked out for some reason. I don't know why.
                echo -ne "██\u0020\u0020"
                if [ "$x" == "$xtile" ]; then
                echo
                echo
                fi
            done
        done
        echo finished creating tiles.
        echo $(expr $ytile \* $xtile) tiles created. x:$xtile y:$ytile
    fi
fi
##⎕█░▒▓
##merge tiles
if [ "$Workspace" == "1" ]; then
    echo merging tiles...
montage -mode concatenate -tile $(echo $xtile)x$ytile -tile-offset $xtile ${file/$(basename $file)}/Output/*.png ${file/$(basename $file)}/merge.png

fi
exit