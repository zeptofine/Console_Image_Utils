%appdata%\ffmpeg-release-essentials\ffmpeg-4.4-essentials_build\bin\ffmpeg.exe -hide_banner -loglevel quiet -i %1 -n -compression_level %2 -vf "scale=iw/2:ih/2" "%3" 
exit
