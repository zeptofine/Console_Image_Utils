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
if not exist "%appdata%\ffmpeg-release-essentials" (
    Powershell -Command "Invoke-WebRequest -Uri "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip" -OutFile "%appdata%\ffmpeg-release-essentials.zip"
    Powershell -Command "Expand-Archive -LiteralPath %appdata%/ffmpeg-release-essentials.zip" -DestinationPath "%appdata%\ffmpeg-release-essentials"
    )
    set Ffmpegpath=%appdata%\ffmpeg-release-essentials\ffmpeg-4.4-essentials_build\bin\ffmpeg.exe
if not exist %~pd0\FFmpegConvertImage.bat (
    ( echo %%appdata%%\ffmpeg-release-essentials\ffmpeg-4.4-essentials_build\bin\ffmpeg.exe -i %%1 -n -compression_level %%2 -vf "scale='min(1024,iw)':-1" %%3 
      echo exit
    ) >> %~pd0\FFmpegConvertImage.bat
    )
set sourcemod=%source2: =-%
if not exist "%sourcemod%-Converted" mkdir "%sourcemod%-Converted"
set convertedfolder=%sourcemod%-Converted
for /f "tokens=*" %%i in ('dir/s/b/a-d "!source2!" ^| find /v /c "::"') do set totalfilecount=%%i
for /r %%i in (*) do (
    set file=%%i
    set filename=%%~nxi
    set outfile=!filename: =-!
    set filerel=!file:%source2%=!
    set filepath=!filerel:%%~nxi=!
    set filepath=!filepath: =-!
    if not exist "%convertedfolder%\!filepath!" mkdir "%convertedfolder%\!filepath!"
    set outputview=%convertedfolder%!filepath!!outfile!
    if not exist "%convertedfolder%\!filepath!\!outfile!" (
        if !timer! GTR 12 (
            set wait=/WAIT
            set timer=0
        )
        if %%~xi==.jpg start !wait! /MIN /I /ABOVENORMAL %~pd0\FFmpegConvertImage.bat "%%i" 80 "%convertedfolder%\!filepath!\!outfile!"
        if %%~xi==.png start !wait! /MIN /I /ABOVENORMAL %~pd0\FFmpegConvertImage.bat "%%i" 90 "%convertedfolder%\!filepath!\!outfile!"
        if %%~xi==.webm copy "%%i" "%convertedfolder%\!filepath!\!outfile!"  > NUL
        if %%~xi==.gif copy "%%i" "%convertedfolder%\!filepath!\!outfile!"  > NUL 
        if %%~xi==.swf copy "%%i" "%convertedfolder%\!filepath!\!outfile!"  > NUL 
        
        echo [ !finishedcount!/%totalfilecount% - !percentview! ]      !filepath! !outputview:~-37! !wait!
        set /a timer+=1
        set /a convertedcount+=1
    ) else (
        echo [ !finishedcount!/%totalfilecount% - !percentview! ] skip !filepath! !outputview:~-37!
        set /a skippedcount+=1
    )
    set wait=
    set /a finishedcount+=1
    set /a Percent="((finishedcount*100)/totalfilecount)"
    set percentview=000!percent!
    set percentview=!percentview:~-3!%%
)

set /a missing=totalfilecount-finishedcount
echo !percentview! !finishedcount!/%totalfilecount%
echo !convertedcount! files processed
echo !skippedcount! files already processed
echo !missing! files unknown
exit /b