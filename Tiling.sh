#create .sh path
    parent_path=$( cd "$(dirname "${BASH_SOURCE[0]}")" ; pwd -P )
    cd "$parent_path"

    echo You need Ffmpeg \(splitting\) and Imagemagick \(merging\) before you run this.
    echo To do: add a check for Ffmpeg and Imagemagick.
    echo also, Actually make a padding option, because currently it\'s just placeholder.
#Setup main variables
    read -p "Input:" file
    # ${file/$(basename $file)}
    xres=$(ffprobe -v error -select_streams v:0 -show_entries stream=width -of default=nw=1:nk=1 $file)
    yres=$(ffprobe -v error -select_streams v:0 -show_entries stream=height -of default=nw=1:nk=1 $file)
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
echo -ne "░\u0020"
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
    if [ "$Padding" == 0 ]; then
        for y in $(seq "$ytile"); do 
                for x in $(seq "$xtile"); do
                xcrop=$(expr $xres / $xtile)
                ycrop=$(expr $yres / $ytile)
                xoffset=$(expr $xcrop \* $(expr $x - 1 ))
                yoffset=$(expr $ycrop \* $(expr $y - 1 ))
                ffmpeg -y -i $file -filter:v "crop=$xcrop:$ycrop:$xoffset:$yoffset" -hide_banner -loglevel error ${file/$(basename $file)}/Output/$(basename $file).$y,$x.png &
                #This worked for some reason. I don't know why.
                echo -ne "█\u0020"
                if [ "$x" == "$xtile" ]; then
                echo
                echo
                fi
            done
        done
    fi
fi
#⎕█░▒▓
#merge tiles
if [ "$Workspace" == "1" ]; then
    echo merging tiles...
montage -mode concatenate ${file/$(basename $file)}/Output/*.png ${file/$(basename $file)}/merge.png

fi