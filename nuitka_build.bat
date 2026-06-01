@echo off
setlocal enabledelayedexpansion

echo ====================================================================
echo      FH6 Painter - Nuitka Native Executable Compiler
echo ====================================================================
echo.

:: 1. Check virtual environment
set "VENV_DIR=%~dp0.venv"
set "NUITKA_EXE=%VENV_DIR%\Scripts\nuitka.bat"
if not exist "%NUITKA_EXE%" (
    set "NUITKA_EXE=%VENV_DIR%\Scripts\nuitka.exe"
)
if not exist "%NUITKA_EXE%" (
    set "NUITKA_EXE=%VENV_DIR%\Scripts\nuitka.cmd"
)

if not exist "%NUITKA_EXE%" (
    echo [ERROR] Nuitka executable not found in virtual environment.
    echo Please run: pip install nuitka
    pause
    exit /b 1
)

:: 2. Clean previous build folders
echo [INFO] Cleaning up previous Nuitka build directories...
if exist "%~dp0nuitka_dist" rd /s /q "%~dp0nuitka_dist"
echo [SUCCESS] Cleanup completed.
echo.

:: 3. Run Nuitka Build
echo [INFO] Compiling using Nuitka (Standalone + Zig C Compiler)...
echo This might take a few minutes as it compiles Python bytecode to C++ and compiles to native code...
echo --------------------------------------------------------------------
"%NUITKA_EXE%" ^
    --standalone ^
    --zig ^
    --jobs=%NUMBER_OF_PROCESSORS% ^
    --assume-yes-for-downloads ^
    --nofollow-import-to=unittest ^
    --nofollow-import-to=pydoc ^
    --nofollow-import-to=doctest ^
    --nofollow-import-to=xmlrpc ^
    --nofollow-import-to=ftplib ^
    --nofollow-import-to=email ^
    --nofollow-import-to=html ^
    --nofollow-import-to=http ^
    --nofollow-import-to=numba ^
    --nofollow-import-to=llvmlite ^
    --disable-console ^
    --enable-plugins=tk-inter ^
    --include-package=taichi ^
    --include-data-dir="%~dp0evaluators=evaluators" ^
    --include-data-dir="%~dp0tools=tools" ^
    --company-name="FH6-Painter Open Source" ^
    --product-name="Forza Horizon 6 Painter Studio" ^
    --file-version="1.2.6.0" ^
    --product-version="1.2.6.0" ^
    --file-description="Forza Horizon 6 Painter Studio" ^
    --copyright="Copyright (c) 2026 eddie772tw. Licensed under MIT." ^
    --windows-icon-from-ico="%~dp0icon.ico" ^
    --output-dir="%~dp0nuitka_dist" ^
    "%~dp0fh6_painter_studio_gui.py"
echo --------------------------------------------------------------------

if errorlevel 1 (
    echo.
    echo [ERROR] Nuitka compilation encountered an error!
    pause
    exit /b 1
)

echo [SUCCESS] Nuitka compilation completed successfully.
echo Output directory: %~dp0nuitka_dist\fh6_painter_studio_gui.dist
echo.

:: Copy editable configuration resources to output root
echo [INFO] Copying editable preset assets...
set "DIST_DIR=%~dp0nuitka_dist\fh6_painter_studio_gui.dist"
if exist "%~dp0settings" (
    xcopy /E /I /Y "%~dp0settings" "%DIST_DIR%\settings" >nul
    echo [SUCCESS] Copied "settings" preset folder.
)
if exist "%~dp0optimization_settings.json" (
    copy /Y "%~dp0optimization_settings.json" "%DIST_DIR%" >nul
    echo [SUCCESS] Copied "optimization_settings.json" configuration file.
)

echo ====================================================================
echo      FH6 Painter Nuitka native build created successfully
echo ====================================================================
pause
exit /b 0
