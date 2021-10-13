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
set sourcemod=%source2: =-%
set /p prefix="prefix?:"
if "%prefix%"=="" (
    echo no prefix detected^^!
    goto prefix 
    )
if not exist "%source2%-%prefix%" mkdir "%source2%-%prefix%"
set convertedfolder=%source2%-%prefix%
for /f "tokens=*" %%i in ('dir/s/b/a-d "!source2!" ^| find /v /c "::"') do set totalfilecount=%%i
set /a totalfilecount-=1
for /r %%i in (*%prefix%*) do (
    set file=%%i
    set filename=%%~nxi
    set outfile=!filename: =-!
    set filerel=!file:%source2%=!
    set filepath=!filerel:%%~nxi=!
    set filepath=!filepath: =-!
    if not exist "%convertedfolder%\!filepath!" mkdir "%convertedfolder%\!filepath!"
    set outputview=%convertedfolder%!filepath!!outfile!
    if not exist "%convertedfolder%\!filepath!\!outfile!" (
        copy "%%i" "%convertedfolder%\!filepath!\!outfile!" > NUL
        echo [ !finishedcount!/%totalfilecount% - !percentview! ]      !filepath! !outputview:~-37! !wait!
        set /a convertedcount+=1
    ) else (
        echo [ !finishedcount!/%totalfilecount% - !percentview! ] skip !filepath! !outputview:~-37!
        set /a skippedcount+=1
    )
    set /a finishedcount+=1
    set /a Percent="((finishedcount*100)/totalfilecount)"
    set percentview=000!percent!
    set percentview=!percentview:~-3!%%
)
set /a convertedcount-=1
set /a missing=totalfilecount-finishedcount
echo !convertedcount! files processed
echo !skippedcount! files already processed
echo !missing! without prefix
exit /b