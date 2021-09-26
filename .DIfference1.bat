@echo off
setlocal enabledelayedexpansion 
set /p source2="Folder:" || set source2=%~pd0
cd /d %source2%
cd ..\
set origin=%CD%
echo %origin%
cd %source2%
echo %source2%
for /f "useback tokens=*" %%a in ('%source2%') do set source2=%%~a
echo %source2%
set /p video="Video or Images or all? [v/i/a]:"
if not exist "%appdata%\ffmpeg-release-essentials" (
    Powershell -Command "Invoke-WebRequest -Uri "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip" -OutFile "%appdata%\ffmpeg-release-essentials.zip"
    Powershell -Command "Expand-Archive -LiteralPath %appdata%/ffmpeg-release-essentials.zip" -DestinationPath "%appdata%\ffmpeg-release-essentials"
    )
    set Ffmpegpath=%appdata%\ffmpeg-release-essentials\ffmpeg-4.4-essentials_build\bin\ffmpeg.exe
if not exist %~pd0\FFmpegConvertImage.bat (
    ( echo %%appdata%%\ffmpeg-release-essentials\ffmpeg-4.4-essentials_build\bin\ffmpeg.exe -i %%1 -n -compression_level %%2 -vf "scale='min(1920,iw)':-1" %%3 
      echo exit
    ) >> %~pd0\FFmpegConvertImage.bat
    )
set sourcemod=%source2: =-%
if not exist "%sourcemod%-Converted" mkdir "%sourcemod%-Converted"
set convertedfolder=%sourcemod%-Converted
if %video%==v goto VideoCopy
for /d %%i in (*) do (
    set path=%%i
    echo !path!
    set path=!path:%source2%=!
    set path=!path: =-!
    echo !path!
    if not exist "%convertedfolder%\!path!" mkdir "%convertedfolder%\!path!"
    cd "%source2%\%%i"
    for /r %%a in (*) do (
        set file=%%~nxa
        set file=!file: =-!
        set file2=%%~nxa
        set file2=!file2: =%%20!
        if not exist "%convertedfolder%\!path!\!file!" (
        if !timer! GTR 12 set wait=/WAIT
        echo !path! !wait! "%source2%\%%i\%%~nxa"
        if %%~xa==.jpg start !wait! /MIN /I /ABOVENORMAL %~pd0\FFmpegConvertImage.bat "%source2%\%%i\%%~nxa" 80 "%convertedfolder%\!path!\!file!"
        if %%~xa==.png start !wait! /MIN /I /ABOVENORMAL %~pd0\FFmpegConvertImage.bat "%source2%\%%i\%%~nxa" 100 "%convertedfolder%\!path!\!file!" 
        if %%~xi==.webm copy "%%a" "%convertedfolder%\!path!\!file!"  > NUL
        if %%~xi==.gif copy "%%a" "%convertedfolder%\!path!\!file!"  > NUL 
        if %%~xi==.swf copy "%%a" "%convertedfolder%\!path!\!file!"  > NUL 
        if !timer! GTR 12 set timer=0
        set /a timer+=1
        set wait=
        ) else ( echo !path! skip %%a )
        )
    )
    for %%i in (*) do (
        if %%~xi==.jpg start /MIN /I /ABOVENORMAL %~pd0\FFmpegConvertImage.bat %%i 80 "%convertedfolder%\%%i"
        if %%~xi==.png start /MIN /I /ABOVENORMAL %~pd0\FFmpegConvertImage.bat %%i 100 "%convertedfolder%\%%i"
        )
exit /b
for /r %%i in (*.jpg *.png) do (
    set file=%%~nxi
    set path=%%~dpi
    set path=!path:%source2%=!
    set path=!path: =-!
    set file=!file: =-!
    echo !path! !file!

    )
exit /b
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
for /d %%i in (*) do (
        set path=%%i
        set path=!path:%source2%=!
        set path=!path: =-!
        echo !path!
        if not !path!==%%i (
            echo different^^! !path!
        )
    )
for /r %%i in (*.jpg *.png) do (
    set file=%%~nxi
    set path=!path: =-!
    set file=!file: =-!
    if not !file!==%%~nxi (
        echo file with dashes !file!
        )
    )