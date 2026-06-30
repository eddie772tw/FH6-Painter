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
    where pyinstaller >nul 2>nul
    if !errorlevel! equ 0 (
        set "PYINSTALLER_EXE=pyinstaller"
    ) else (
        echo [INFO] PyInstaller not found in virtual environment, checking global Python...
        if exist "%PY_EXE%" (
            "%PY_EXE%" -m pip install pyinstaller
            if errorlevel 1 (
                echo [ERROR] Failed to install PyInstaller in virtual environment.
                if not "%GITHUB_ACTIONS%" == "true" pause
                exit /b 1
            )
        ) else (
            where python >nul 2>nul
            if !errorlevel! equ 0 (
                set "PY_EXE=python"
                "!PY_EXE!" -m pip install pyinstaller
                set "PYINSTALLER_EXE=pyinstaller"
            ) else (
                echo [ERROR] No valid Python virtual environment or global Python environment found.
                if not "%GITHUB_ACTIONS%" == "true" pause
                exit /b 1
            )
        )
    )
)

:: 2. Run Tauri Build
echo [INFO] Running Tauri Build...
echo --------------------------------------------------------------------
cd "%~dp0frontend"
call npm install || exit /b 1
call npm run tauri build || exit /b 1

if errorlevel 1 (
    echo.
    echo [ERROR] Tauri Build encountered an error!
    if not "%GITHUB_ACTIONS%" == "true" pause
    exit /b 1
)
echo [SUCCESS] Tauri Frontend built successfully.
echo.
cd "%~dp0"

:: 3. Build Final Executable with PyInstaller
echo [INFO] Running PyInstaller to create final standalone executable...
echo --------------------------------------------------------------------
if not exist "%~dp0dist" mkdir "%~dp0dist"

"%PYINSTALLER_EXE%" ^
    --noconfirm ^
    --onefile ^
    --windowed ^
    --noupx ^
    --icon="%~dp0app_icon.ico" ^
    --distpath "%~dp0dist" ^
    --name "FH6_Painter_Studio" ^
    --paths "%~dp0." ^
    --add-data "%~dp0frontend\src-tauri\target\release\frontend.exe;." ^
    --collect-all "taichi" ^
    --collect-all "numba" ^
    --collect-all "llvmlite" ^
    --exclude-module "PIL._imagingcms" ^
    --exclude-module "PIL.ImageCms" ^
    --exclude-module "PIL._webp" ^
    --exclude-module "PIL._imagingtk" ^
    --exclude-module "PIL.ImageTk" ^
    --exclude-module "PIL._imagingmorph" ^
    --hidden-import "utils" ^
    --hidden-import "evaluators.numba_kernels" ^
    --hidden-import "evaluators.numba_evaluator" ^
    --hidden-import "evaluators.taichi_evaluator" ^
    --hidden-import "evaluators.go_opencl_evaluator" ^
    --hidden-import "tools.fh6_import_layer_table" ^
    --hidden-import "tools.fh6_painter_generator" ^
    --add-data "tools\bin\*;tools\bin" ^
    --add-data "tools\fh6-heuristics.json;tools" ^
    --add-data "settings\*;settings" ^
    "%~dp0backend\server.py"

echo --------------------------------------------------------------------

if errorlevel 1 (
    echo.
    echo [ERROR] PyInstaller bundling encountered an error!
    if not "%GITHUB_ACTIONS%" == "true" pause
    exit /b 1
)
echo [SUCCESS] Standalone executable created successfully.
echo.

:: 4. Success screen
echo ====================================================================
echo      FH6 Painter standalone bundle created successfully
echo ====================================================================
echo  Distribution Executable Path:
echo  %~dp0dist\FH6_Painter_Studio.exe
echo.
if not "%GITHUB_ACTIONS%" == "true" pause
exit /b 0
