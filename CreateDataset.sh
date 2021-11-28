echo folder?
read folder
    if [ -z "$folder" ];
        then (
        echo folder not detected!
        exit 1
        )
        fi
cd $folder; cd ..
origin=$PWD
echo $CWD
echo copying $folder into HR...
mkdir ./HR
ORIGINFOLDER=$origin/Dataset
OLDIFS=$IFS
IFS=$'\n'
fileArray=($(find $folder -type f -printf "%T+,%p\n" | sort -r | cut -d, -f2 ))
ArrayAge=($(find $folder -type f -printf "%T+,%p\n" | sort -r | cut -d, -f1 ))
IFS=$OLDIFS
tLen=${#fileArray[@]}
for (( i=0; i<${tLen}; i++ )); do 
    file="${fileArray[$i]}"; filext=.${file##*.}; filefolder=${file%/*}; filefolder=${filefolder##*/}; filenam=${file%.*} 
    filenam=${filenam##*/}; filename=${filenam/$filefolder}; filename=${filename#.*}
    if [[ $filext =~ .jpg ]] || [[ $filext =~ .png ]] || [[ $filext =~ .jpeg ]] || [[ $filext =~ .PNG ]]; then
        if [[ ! -f "./HR/$filename$filext" ]]; then
                imagewidth=$(identify -ping -format "%w" "$file"); imageheight=$(identify -ping -format "%h" "$file")
                if ! (( $imagewidth % 4 )); then
                        if ! (( $imageheight % 4 )); then
                                cp $file ./HR/$filename$filext
                                echo -e "\033[1;37m${ArrayAge[$i]%.*} |\033[1;36m $(echo $i | sed -e :a -e 's/^.\{1,4\}$/_&/;ta') \033[1;37m|\033[0;34m $(echo $imagewidth | sed -e :a -e 's/^.\{1,4\}$/_&/;ta') $(echo $imageheight | sed -e :a -e 's/^.\{1,4\}$/_&/;ta') \033[1;37m|\033[0;36m $file" 
                        else 
                        echo -e "\033[1;37m${ArrayAge[$i]%.*} |\033[1;36m $(echo $i | sed -e :a -e 's/^.\{1,4\}$/_&/;ta') \033[1;37m|\033[1;33m -/%4- ----- \033[1;37m|\033[1;33m $file"
                        fi
                else
                echo -e "\033[1;37m${ArrayAge[$i]%.*} |\033[1;36m $(echo $i | sed -e :a -e 's/^.\{1,4\}$/_&/;ta') \033[1;37m|\033[1;33m -/%4- ----- \033[1;37m|\033[1;33m $file"
                fi
        else 
        echo -e "\033[1;37m${ArrayAge[$i]%.*} |\033[1;36m $(echo $i | sed -e :a -e 's/^.\{1,4\}$/_&/;ta') \033[1;37m|\033[1;33m ----- exist \033[1;37m|\033[1;33m $file"
        fi
fi
done
exit