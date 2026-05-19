@echo off
title Forza Painter - Python Migration Launcher
setlocal enabledelayedexpansion

set "PYTHON_EXE=%~dp0.venv\Scripts\python.exe"

if not exist "!PYTHON_EXE!" (
    set "PYTHON_EXE=python"
)

"!PYTHON_EXE!" "%~dp0python_painter\main.py" %*

if %ERRORLEVEL% neq 0 (
    echo.
    echo [Launcher] Python script exited with code %ERRORLEVEL%
    pause
)
