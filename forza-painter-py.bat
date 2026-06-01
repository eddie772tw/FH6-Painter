@echo off
chcp 65001 >nul
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

:: 校驗 Python 版本
"!PY_EXE!" -c "import sys; sys.exit(0 if sys.version_info.major == 3 and sys.version_info.minor in (13, 14) else 1)" >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] 本專案要求 Python 3.13 或 Python 3.14 
    echo [ERROR] 當前系統中的 Python 版本不相容 
    echo 請安裝相容的 Python 3.13/3.14 版本後再重新運行本腳本
    pause
    exit /b 1
)

:: 檢查是否存在 .venv 或 venv 虛擬環境目錄
set "VENV_DIR=%~dp0.venv"
if not exist "%VENV_DIR%" (
    if exist "%~dp0venv" (
        set "VENV_DIR=%~dp0venv"
    )
)

:: 如果虛擬環境中的 python 存在，則跳過建立步驟
if exist "%VENV_DIR%\Scripts\python.exe" goto :venv_exists

echo [INFO] 找不到虛擬環境，正在目錄中建立虛擬環境 (.venv)...
set "VENV_DIR=%~dp0.venv"
"!PY_EXE!" -m venv "%~dp0.venv"
if errorlevel 1 (
    echo [ERROR] 建立虛擬環境失敗。
    pause
    exit /b 1
)

:venv_exists
:: 將 PY_EXE 切換為虛擬環境中的 Python 執行檔
set "PY_EXE=%VENV_DIR%\Scripts\python.exe"

:: 檢查是否缺少基礎依賴庫 (嘗試載入 pillow/PIL、numpy、numba 和 taichi)
"!PY_EXE!" -c "import PIL, numpy, numba, taichi" >nul 2>nul
if %errorlevel% equ 0 goto :dependencies_ok

echo [INFO] 偵測到缺少依賴套件或首次啟動。正在安裝依賴套件...
"!PY_EXE!" -m pip install --upgrade pip
"!PY_EXE!" -m pip install -r "%~dp0requirements.txt"
if errorlevel 1 (
    echo [ERROR] 安裝依賴套件失敗。
    pause
    exit /b 1
)

:dependencies_ok

:: 啟動應用程式
if "%~1" == "" (
    "!PY_EXE!" fh6_painter_studio_gui.py
) else (
    if "%~2" == "" (
        "!PY_EXE!" fh6_painter_studio_gui.py "%~1"
    ) else (
        "!PY_EXE!" fh6_painter_launcher.py %*
    )
)


