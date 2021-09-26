@echo off
setlocal enabledelayedexpansion 
set /p source2="Folder:"
cd /d %source2%
cd ..\
set origin=%CD%
echo %origin%
cd %source2%
set originname=!source2:%origin%=!
echo %originname%
cd %source2%
set /p video="Video or Images or all? [v/i/a]:"
if not exist "%appdata%\ffmpeg-release-essentials" (
    Powershell -Command "Invoke-WebRequest -Uri "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip" -OutFile "%appdata%\ffmpeg-release-essentials.zip"
    Powershell -Command "Expand-Archive -LiteralPath %appdata%/ffmpeg-release-essentials.zip" -DestinationPath "%appdata%\ffmpeg-release-essentials"
    )
    set Ffmpegpath=%appdata%\ffmpeg-release-essentials\ffmpeg-4.4-essentials_build\bin\ffmpeg.exe
    if not exist %~pd0\FFmpegConvertImage.bat (
    ( echo %%appdata%%\ffmpeg-release-essentials\ffmpeg-4.4-essentials_build\bin\ffmpeg.exe -hide_banner -loglevel quiet -i "%%1" -n -compression_level %%2 -vf "scale=iw/2:ih/2" "%%3" 
      echo exit
    ) >> %~pd0\FFmpegConvertImage.bat
    )
if %video%==v goto VideoCopy 
for /f "tokens=*" %%i in ('dir/s/b/a-d "!source2!" ^| find /v /c "::"') do set totalfilecount=%%i
for /r %%i in (*.bak) do del %%i
for /r %%i in (*.jpg *.png *.webm *.gif) do (
    set path=%%~dpi
    set path=!path:%CD%=!
    set file=%%~nxi
    set path=!path: =-!
    set file=!file: =-!
    if not exist "%origin%\%originname%-Converted\!path!\!file!" (
            if !timer! GTR 12 set wait=/WAIT
        if not %%~nxi==!file! rename "%%i" "!file!" 
        if not exist "%origin%\%originname%-Converted\!path!\" mkdir "%origin%\%originname%-Converted\!path!\"
        echo [Conv ] [ !finishedcount!/!totalfilecount!--!percentview!%% ] [ %origin%\%originname%-Converted\!path!\%%~nxi ]
        if %%~xi==.jpg start !wait! /MIN /I /ABOVENORMAL %~pd0\FFmpegConvertImage.bat %%i 80 "%origin%\%originname%-Converted\!path!\!file!"
        if %%~xi==.png start !wait! /MIN /I /ABOVENORMAL %~pd0\FFmpegConvertImage.bat %%i 100 "%origin%\%originname%-Converted\!path!\!file!"
        if !timer! GTR 12 (
            echo [wait^^!]
            set timer=0
            )
        set /a timer+=1
        set wait=
    ) else ( echo [skip ] [ !finishedcount!/%totalfilecount%--!percentview!%% ] [ %origin%\%originname%-Converted\!path!\%%~nxi ])
    set /a finishedcount+=1
    set /a Percent="((finishedcount*100)/totalfilecount)"
    set percentview=000!percent!
    set percentview=!percentview:~-3!
)
:VideoCopy
for /r %%i in (*.webm *.gif *swf) do (
    if not exist "%origin%\%originname%-Converted\!path!\%%~nxi" (
    set path=%%~dpi
    set path=!path:%CD%=!
    set path=!path: =-!
    set file=%%~nxi
    set file=!file: =-!
    if %%~xi==.webm copy "%%i" "%origin%\%originname%-Converted\!path!\%%~nxi" > NUL
    if %%~xi==.gif copy "%%i" "%origin%\%originname%-Converted\!path!\%%~nxi" > NUL 
    if %%~xi==.swf copy "%%i" "%origin%\%originname%-Converted\!path!\%%~nxi" > NUL 
    echo [copy ] [ %origin%\%originname%-Converted\!path!\%%~nxi ]
    )
)
exit /b

for /d %%i in (*) do (
    set foldername=%%i
    for %%r in (*!foldername!*) do (
        move "%%r" "%CD%\!foldername!" > NUL
        echo !foldername! %%r
    )
)
exit /b
