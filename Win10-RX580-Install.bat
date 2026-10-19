@echo off
setlocal EnableDelayedExpansion

REM ============================================================
REM  Manga Translator UI - installer for
REM    Windows 10 | Intel i5-10400 | 16 GB RAM | AMD RX 580 2048SP (4 GB)
REM
REM  What it does:
REM    1. checks Windows 10 version (DirectML needs 1903 / build 18362+)
REM    2. installs the Visual C++ runtime if it is missing (needed by PyTorch)
REM    3. installs uv (Python package manager) if it is missing
REM    4. creates .venv with Python 3.12 and installs the "directml" group:
REM       CPU PyTorch + onnxruntime-directml (ONNX models run on the RX 580)
REM    5. checks that DirectML is visible to ONNX Runtime
REM
REM  Run it again at any time to repair or update the environment.
REM  Start the app afterwards with Win10-RX580-Start.bat
REM ============================================================

set "PYTHONUTF8=1"
cd /d "%~dp0"
title Manga Translator UI - install (RX 580 / Windows 10)

echo ============================================================
echo  Manga Translator UI - install for RX 580 (DirectML)
echo ============================================================
echo.

REM ---------- 1) Windows version ----------
echo [1/5] Checking Windows version...
set "WINBUILD="
for /f "usebackq delims=" %%i in (`powershell -NoProfile -Command "(Get-CimInstance Win32_OperatingSystem).BuildNumber"`) do set "WINBUILD=%%i"
if not defined WINBUILD (
    echo [WARN] Could not detect the Windows build number, continuing.
    goto :vcredist
)
echo       Windows build: !WINBUILD!
if !WINBUILD! LSS 18362 (
    echo [ERROR] DirectML needs Windows 10 version 1903 ^(build 18362^) or newer.
    echo         Please run Windows Update and try again.
    goto :fail
)

REM ---------- 2) Visual C++ runtime ----------
:vcredist
echo [2/5] Checking Visual C++ runtime...
reg query "HKLM\SOFTWARE\Microsoft\VisualStudio\14.0\VC\Runtimes\X64" /v Installed >nul 2>&1
if not errorlevel 1 (
    echo       Already installed.
    goto :uv
)
echo       Not found. Downloading Microsoft Visual C++ Redistributable ^(x64^)...
set "VCREDIST=%TEMP%\vc_redist.x64.exe"
powershell -NoProfile -Command "[Net.ServicePointManager]::SecurityProtocol=[Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -UseBasicParsing -Uri 'https://aka.ms/vs/17/release/vc_redist.x64.exe' -OutFile '%VCREDIST%'"
if errorlevel 1 (
    echo [ERROR] Download failed. Install it manually from:
    echo         https://aka.ms/vs/17/release/vc_redist.x64.exe
    goto :fail
)
echo       Installing ^(accept the administrator prompt^)...
"%VCREDIST%" /install /passive /norestart
if errorlevel 1 if not "!ERRORLEVEL!"=="3010" (
    echo [ERROR] Visual C++ runtime installation failed ^(code !ERRORLEVEL!^).
    goto :fail
)
if "!ERRORLEVEL!"=="3010" echo [INFO] A restart may be needed after the installation finishes.

REM ---------- 3) uv ----------
:uv
echo [3/5] Checking uv...
set "UV="
where uv >nul 2>&1
if not errorlevel 1 set "UV=uv"
if not defined UV if exist "%USERPROFILE%\.local\bin\uv.exe" set "UV=%USERPROFILE%\.local\bin\uv.exe"
if not defined UV if exist "%USERPROFILE%\.cargo\bin\uv.exe" set "UV=%USERPROFILE%\.cargo\bin\uv.exe"
if defined UV goto :uv_ready

echo       Not found. Installing uv with the official installer ^(https://astral.sh/uv^)...
powershell -NoProfile -ExecutionPolicy Bypass -Command "[Net.ServicePointManager]::SecurityProtocol=[Net.SecurityProtocolType]::Tls12; irm https://astral.sh/uv/install.ps1 | iex"
if exist "%USERPROFILE%\.local\bin\uv.exe" set "UV=%USERPROFILE%\.local\bin\uv.exe"
if not defined UV if exist "%USERPROFILE%\.cargo\bin\uv.exe" set "UV=%USERPROFILE%\.cargo\bin\uv.exe"
if not defined UV (
    echo [ERROR] uv installation failed. See https://docs.astral.sh/uv/getting-started/installation/
    goto :fail
)

:uv_ready
echo       Using: !UV!

REM ---------- 4) Python 3.12 + dependencies ----------
echo [4/5] Installing Python 3.12 and dependencies ^(first run downloads about 1-2 GB^)...
"!UV!" python install 3.12
if errorlevel 1 (
    echo [ERROR] Could not install Python 3.12.
    goto :fail
)
"!UV!" sync --locked --no-default-groups --group directml
if errorlevel 1 (
    echo [ERROR] Dependency installation failed. Check your internet connection and run this file again.
    goto :fail
)

REM ---------- 5) Verify ----------
echo [5/5] Verifying PyTorch and DirectML...
".venv\Scripts\python.exe" -c "import torch, onnxruntime as o; p=o.get_available_providers(); print('       torch', torch.__version__, '| onnxruntime', o.__version__); print('       providers:', p); raise SystemExit(0 if 'DmlExecutionProvider' in p else 3)"
if errorlevel 3 (
    echo.
    echo [WARN] DirectML is not visible to ONNX Runtime. The app will still work, but
    echo        ONNX models will run on the CPU. Update the AMD Radeon driver and make
    echo        sure the card supports DirectX 12, then run this file again.
    goto :done
)
if errorlevel 1 (
    echo [ERROR] Verification failed. Run this file again; if it persists, install the
    echo         Visual C++ runtime manually: https://aka.ms/vs/17/release/vc_redist.x64.exe
    goto :fail
)

:done
echo.
echo ============================================================
echo  Done. Start the app with Win10-RX580-Start.bat
echo ============================================================
pause
exit /b 0

:fail
echo.
echo Installation did not finish.
pause
exit /b 1
