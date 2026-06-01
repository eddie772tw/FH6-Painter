@echo off
setlocal enabledelayedexpansion

echo ====================================================================
echo      FH6 Painter - Standalone Release Bundler
echo ====================================================================
echo.

:: 1. Check and locate virtual environment and PyInstaller
set "VENV_DIR=%~dp0.venv"
set "PY_EXE=%VENV_DIR%\Scripts\python.exe"
set "PYINSTALLER_EXE=%VENV_DIR%\Scripts\pyinstaller.exe"

if not exist "%PYINSTALLER_EXE%" (
    echo [ERROR] PyInstaller executable not found in virtual environment.
    echo Make sure you have run "forza-painter-py.bat" to set up the environment.
    echo Trying to install PyInstaller package...
    if exist "%PY_EXE%" (
        "%PY_EXE%" -m pip install pyinstaller
        if errorlevel 1 (
            echo [ERROR] Failed to install PyInstaller. Please run: pip install pyinstaller
            pause
            exit /b 1
        )
    ) else (
        echo [ERROR] No valid Python virtual environment found. Run "forza-painter-py.bat" first.
        pause
        exit /b 1
    )
)

:: 2. Clean previous build folders
echo [INFO] Cleaning up previous build directories (build, dist)...
if exist "%~dp0build" rd /s /q "%~dp0build"
if exist "%~dp0dist" rd /s /q "%~dp0dist"
if exist "%~dp0FH6_Painter_Studio.spec" del /q "%~dp0FH6_Painter_Studio.spec"
echo [SUCCESS] Cleanup completed.
echo.

:: 3. Run PyInstaller build
echo [INFO] Running PyInstaller to compile binaries...
echo --------------------------------------------------------------------
"%PYINSTALLER_EXE%" ^
    --noconfirm ^
    --name "FH6_Painter_Studio" ^
    --windowed ^
    --noupx ^
    --version-file "%~dp0file_version_info.txt" ^
    --icon "%~dp0icon.ico" ^
    --collect-all "taichi" ^
    --add-data "evaluators\*;evaluators" ^
    --add-data "tools\*;tools" ^
    --exclude-module unittest ^
    --exclude-module pydoc ^
    --exclude-module doctest ^
    --exclude-module xmlrpc ^
    --exclude-module ftplib ^
    --exclude-module html ^
    --exclude-module http.server ^
    "%~dp0fh6_painter_studio_gui.py"
echo --------------------------------------------------------------------

if errorlevel 1 (
    echo.
    echo [ERROR] PyInstaller bundling encountered an error!
    pause
    exit /b 1
)
echo [SUCCESS] Core binary bundled successfully.
echo.

:: 4. Copy editable configuration resources to output root
echo [INFO] Copying editable assets (settings, json) to distribution folder...
set "DIST_DIR=%~dp0dist\FH6_Painter_Studio"

if not exist "%DIST_DIR%" (
    echo [ERROR] Distribution directory not found: %DIST_DIR%
    pause
    exit /b 1
)

:: Copy settings directory
if exist "%~dp0settings" (
    xcopy /E /I /Y "%~dp0settings" "%DIST_DIR%\settings" >nul
    if errorlevel 1 (
        echo [WARNING] Encountered minor warning when copying settings folder.
    ) else (
        echo [SUCCESS] Copied "settings" preset folder.
    )
)

:: 5. Compress output package automatically
echo [INFO] Compressing output package...
where 7z >nul 2>nul
if %errorlevel% equ 0 (
    echo [INFO] Found 7-Zip, compressing to .7z archive...
    if exist "%~dp0dist\FH6_Painter_Studio.7z" del /q "%~dp0dist\FH6_Painter_Studio.7z"
    7z a -r "%~dp0dist\FH6_Painter_Studio.7z" "%DIST_DIR%" >nul
    if errorlevel 1 (
        echo [WARNING] Failed to compress using 7-Zip.
    ) else (
        echo [SUCCESS] Compressed successfully: FH6_Painter_Studio.7z
        set "ARCHIVE_FILE=FH6_Painter_Studio.7z"
    )
) else (
    echo [INFO] 7-Zip not found in PATH, using PowerShell Compress-Archive...
    if exist "%~dp0dist\FH6_Painter_Studio.zip" del /q "%~dp0dist\FH6_Painter_Studio.zip"
    powershell -NoProfile -Command "Compress-Archive -Path '%DIST_DIR%' -DestinationPath '%~dp0dist\FH6_Painter_Studio.zip' -Force"
    if errorlevel 1 (
        echo [WARNING] Failed to compress using PowerShell.
    ) else (
        echo [SUCCESS] Compressed successfully: FH6_Painter_Studio.zip
        set "ARCHIVE_FILE=FH6_Painter_Studio.zip"
    )
)
echo.

:: 6. Success screen
echo ====================================================================
echo      FH6 Painter standalone bundle created successfully
echo ====================================================================
echo  Distribution Folder Path:
echo  %DIST_DIR%
echo.
echo  Executable Program Location:
echo  %DIST_DIR%\FH6_Painter_Studio.exe
if not "!ARCHIVE_FILE!"=="" (
    echo.
    echo  Compressed Distribution Archive:
    echo  %~dp0dist\!ARCHIVE_FILE!
)
echo ====================================================================
echo.
echo TIP: You can distribute the generated archive to other players
echo      as a portable standalone tool!
echo.
pause
exit /b 0
