@echo off
setlocal enabledelayedexpansion

:: Check standard AppData location
set "PY_EXE=%USERPROFILE%\AppData\Local\Programs\Python\Python312\python.exe"
if exist "!PY_EXE!" (
    goto :run
)

:: Check other potential versions in AppData
for /d %%d in ("%USERPROFILE%\AppData\Local\Programs\Python\Python*") do (
    if exist "%%d\python.exe" (
        set "PY_EXE=%%d\python.exe"
        goto :run
    )
)

:: Check default path
where python >nul 2>nul
if %errorlevel% equ 0 (
    set "PY_EXE=python"
    goto :run
)

echo ERROR: Python not found in AppData or PATH.
echo Please install Python 3 or add it to your environment variables.
pause
exit /b 1

:run
cd /D "%~dp0"
"!PY_EXE!" fh6_painter_launcher.py %*
