@echo off
setlocal enabledelayedexpansion

:: Check Python 3.13 standard location
set "PY_EXE=%USERPROFILE%\AppData\Local\Programs\Python\Python313\python.exe"
if exist "!PY_EXE!" (
    goto :run
)

:: Check Python 3.14 standard location
set "PY_EXE=%USERPROFILE%\AppData\Local\Programs\Python\Python314\python.exe"
if exist "!PY_EXE!" (
    goto :run
)

:: Check uv-managed Python 3.13 location
set "PY_EXE=%USERPROFILE%\.local\bin\python3.13.exe"
if exist "!PY_EXE!" (
    goto :run
)

:: Check uv-managed Python 3.14 location
set "PY_EXE=%USERPROFILE%\.local\bin\python3.14.exe"
if exist "!PY_EXE!" (
    goto :run
)

:: Check other potential versions in AppData
for /d %%d in ("%USERPROFILE%\AppData\Local\Programs\Python\Python*") do (
    if exist "%%d\python.exe" (
        set "PY_EXE=%%d\python.exe"
    )
)
if exist "!PY_EXE!" (
    goto :run
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

:: Validate Python Version
"!PY_EXE!" -c "import sys; sys.exit(0 if sys.version_info.major == 3 and sys.version_info.minor in (13, 14) else 1)" >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] Project requires Python 3.13 or 3.14
    echo [ERROR] Current Python version is incompatible.
    pause
    exit /b 1
)

:: Check if virtual environment exists
set "VENV_DIR=%~dp0.venv"
if not exist "%VENV_DIR%" (
    if exist "%~dp0venv" (
        set "VENV_DIR=%~dp0venv"
    )
)

if exist "%VENV_DIR%\Scripts\python.exe" goto :venv_exists

echo [INFO] Virtual environment not found, creating .venv ...
set "VENV_DIR=%~dp0.venv"
"!PY_EXE!" -m venv "%~dp0.venv"
if errorlevel 1 (
    echo [ERROR] Failed to create virtual environment.
    pause
    exit /b 1
)

:venv_exists
:: Set PY_EXE to the virtual environment's python.exe
set "PY_EXE=%VENV_DIR%\Scripts\python.exe"

:: Check for basic dependencies
"!PY_EXE!" -c "import PIL, numpy, numba, taichi" >nul 2>nul
if %errorlevel% equ 0 goto :dependencies_ok

echo [INFO] Installing dependencies into the virtual environment...
"!PY_EXE!" -m pip install --upgrade pip
"!PY_EXE!" -m pip install -r "%~dp0requirements.txt"
"!PY_EXE!" -m pip install -r "%~dp0backend\requirements.txt"
if errorlevel 1 (
    echo [ERROR] Failed to install dependencies.
    pause
    exit /b 1
)

:dependencies_ok

:: Run Ruff if available
if exist "%VENV_DIR%\Scripts\ruff.exe" (
    echo [INFO] Running Ruff...
    "%VENV_DIR%\Scripts\ruff.exe" check . --fix
    "%VENV_DIR%\Scripts\ruff.exe" format .
)

:: Start Tauri Sidecar Architecture
echo [INFO] Starting Python WebSocket Backend...
start "FH6 Painter Backend" "!PY_EXE!" backend\server.py

echo [INFO] Checking and installing frontend dependencies...
cd /D "%~dp0frontend"
call npm install

where cargo >nul 2>nul
if %errorlevel% equ 0 (
    echo [INFO] Rust environment detected. Starting native Tauri app...
    call npm run tauri dev
) else (
    echo [INFO] Rust not detected. Falling back to Vite Web Server...
    start http://localhost:1420
    call npm run dev
)
