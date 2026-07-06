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

:: 1.5. Scan for unregistered directories (not ignored and not packaged)
echo [INFO] Scanning for unregistered resource directories...
echo --------------------------------------------------------------------
set "HAS_UNREGISTERED=false"

for /d %%D in ("%~dp0*") do (
    set "DIR_NAME=%%~nxD"
    set "IS_IGNORED=false"
    
    :: Check if directory is listed in .pkgdirignore
    if exist "%~dp0.pkgdirignore" (
        for /f "usebackq tokens=* eol=#" %%I in ("%~dp0.pkgdirignore") do (
            if /i "%%~nxD" == "%%I" set "IS_IGNORED=true"
        )
    )
    
    if "!IS_IGNORED!" == "false" (
        :: Check if it's already packaged in this script by searching for its name
        findstr /I /C:"%%~nxD" "%~dp0build_release.bat" >nul
        if errorlevel 1 (
            echo.
            echo [WARNING] Found directory '%%~nxD' that is neither ignored nor packaged.
            if "%GITHUB_ACTIONS%" == "true" (
                echo [ERROR] Unregistered directory '%%~nxD' found in CI. Terminating.
                exit /b 1
            )
            choice /C YN /T 10 /D N /M "Would you like to add '%%~nxD' to .pkgdirignore?"
            if !errorlevel! equ 1 (
                echo [INFO] Adding '%%~nxD' to .pkgdirignore...
                echo.>> "%~dp0.pkgdirignore"
                echo %%~nxD>> "%~dp0.pkgdirignore"
                echo [SUCCESS] Added '%%~nxD' to .pkgdirignore.
            ) else (
                echo.
                echo [IMPORTANT] Please add '%%~nxD' to build_release.bat packaging options or .pkgdirignore.
                echo [INFO] Building process will now terminate.
                pause
                exit /b 1
            )
        )
    )
)
echo [SUCCESS] No unregistered resource directories found.
echo.

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
    --name "FH6-Painter" ^
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
    --add-data "lang\*;lang" ^
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
echo  %~dp0dist\FH6-Painter.exe
echo.
if not "%GITHUB_ACTIONS%" == "true" pause
exit /b 0
