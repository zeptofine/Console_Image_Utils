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
:prefix
set /p prefix="prefix?:"
if "%prefix%"=="" (
    echo no prefix detected^^!
    goto prefix 
    )
for /r %%i in (*%prefix%*) do (
    del "%%i"
)