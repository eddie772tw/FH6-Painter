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

:: ?⊿? Python ?
"!PY_EXE!" -c "import sys; sys.exit(0 if sys.version_info.major == 3 and sys.version_info.minor in (13, 14) else 1)" >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] ?砍?獢?瘙?Python 3.13 ??Python 3.14 
    echo [ERROR] ?嗅?蝟餌絞銝剔? Python ?銝摰?
    echo 隢?鋆摰寧? Python 3.13/3.14 ?敺?????祈??    pause
    exit /b 1
)

:: 瑼Ｘ?臬摮 .venv ??venv ??啣??桅?
set "VENV_DIR=%~dp0.venv"
if not exist "%VENV_DIR%" (
    if exist "%~dp0venv" (
        set "VENV_DIR=%~dp0venv"
    )
)

:: 憒???啣?銝剔? python 摮嚗?頝喲?撱箇?甇仿?
if exist "%VENV_DIR%\Scripts\python.exe" goto :venv_exists

echo [INFO] ?曆??啗??祉憓?甇??桅?銝剖遣蝡??祉憓?(.venv)...
set "VENV_DIR=%~dp0.venv"
"!PY_EXE!" -m venv "%~dp0.venv"
if errorlevel 1 (
    echo [ERROR] 撱箇???啣?憭望???    pause
    exit /b 1
)

:venv_exists
:: 撠?PY_EXE ???箄??祉憓葉??Python ?瑁?瑼?set "PY_EXE=%VENV_DIR%\Scripts\python.exe"

:: 瑼Ｘ?臬蝻箏??箇?靘陷摨?(?岫頛 pillow/PIL?umpy?umba ??taichi)
"!PY_EXE!" -c "import PIL, numpy, numba, taichi" >nul 2>nul
if %errorlevel% equ 0 goto :dependencies_ok

echo [INFO] ?菜葫?啁撩撠?鞈游?隞嗆?擐活???迤?典?鋆?鞈游?隞?..
"!PY_EXE!" -m pip install --upgrade pip
"!PY_EXE!" -m pip install -r "%~dp0requirements.txt"
"!PY_EXE!" -m pip install -r "%~dp0backend\requirements.txt"
if errorlevel 1 (
    echo [ERROR] 摰?靘陷憟辣憭望???    pause
    exit /b 1
)

:dependencies_ok

:: ?瑁? Ruff 蝔?蝣潸??????瑼Ｘ
if exist "%VENV_DIR%\Scripts\ruff.exe" (
    echo [INFO] 甇??? Ruff ?脰?蝔?蝣澆?鞈芣撽??芸???...
    "%VENV_DIR%\Scripts\ruff.exe" check . --fix
    "%VENV_DIR%\Scripts\ruff.exe" format .
)

:: ???蝔? (Tauri Sidecar ?嗆?)
echo [INFO] ?? Python WebSocket 敺垢隡箸???..
start "FH6 Painter Backend" "!PY_EXE!" backend\server.py

echo [INFO] 瑼Ｘ銝血?鋆?蝡臭?鞈?..
cd /D "%~dp0frontend"
call npm install

where cargo >nul 2>nul
if %errorlevel% equ 0 (
    echo [INFO] ?菜葫??Rust ?啣?嚗???Tauri 獢蝡舀??函?撘?..
    call npm run tauri dev
) else (
    echo [INFO] ?芸皜砍 Rust (Cargo)嚗?箏???Web ?汗?冽芋撘脰?皜祈岫...
    start http://localhost:1420
    call npm run dev
)
