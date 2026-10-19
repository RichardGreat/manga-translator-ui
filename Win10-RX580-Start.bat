@echo off
setlocal EnableDelayedExpansion

REM ============================================================
REM  Manga Translator UI - launcher for
REM    Windows 10 | Intel i5-10400 | 16 GB RAM | AMD RX 580 2048SP (4 GB)
REM  Run Win10-RX580-Install.bat first.
REM  Do not use the in-app updater on this branch: it switches the code to "main".
REM ============================================================

set "PYTHONUTF8=1"
cd /d "%~dp0"
title Manga Translator UI (RX 580 / DirectML)

REM Let ONNX models use the RX 580 through DirectML (falls back to CPU if unavailable).
REM To force ONNX onto the CPU, set MT_ONNX_DIRECTML=0 before running this file.
if not defined MT_ONNX_DIRECTML set "MT_ONNX_DIRECTML=1"

if not exist ".venv\Scripts\python.exe" (
    echo [ERROR] Environment not found. Run Win10-RX580-Install.bat first.
    pause
    exit /b 1
)

echo Starting...
echo ========================================
echo.
".venv\Scripts\python.exe" desktop_qt_ui\main.py
set "EXITCODE=%ERRORLEVEL%"

if not "%EXITCODE%"=="0" (
    echo.
    echo [ERROR] Application exited with code %EXITCODE%
    echo.
    echo Try running Win10-RX580-Install.bat again to repair the environment.
    echo If it still fails, take a screenshot of this window and report it via GitHub Issues.
    echo.
    pause
    exit /b %EXITCODE%
)

echo.
echo Application closed.
pause
exit /b 0
