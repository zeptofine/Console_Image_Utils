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
for /r %%i in (*) do (
    move "%%i" "%CD%"
)
timeout -1
for /d %%i in (*) do (
    set foldername=%%i
        for %%r in (*!foldername!*) do (
            move "%%r" "%CD%\!foldername!" > NUL
            echo !foldername! %%r
        )
)