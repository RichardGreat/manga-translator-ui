@echo off
setlocal EnableDelayedExpansion

REM ============================================================
REM  Manga Translator UI - installer for
REM    Windows 10 | Intel i5-10400 | 16 GB RAM | AMD RX 580 2048SP (4 GB)
REM
REM  What it does:
REM    1. checks Windows (64-bit, Windows 10 1903 / build 18362+ for DirectML)
REM       and warns about project paths that often break Python packages
REM    2. installs the Visual C++ runtime if it is missing (needed by PyTorch)
REM    3. installs uv (Python package manager) if it is missing
REM    4. creates .venv with Python 3.12 and installs the "directml" group:
REM       CPU PyTorch + onnxruntime-directml (ONNX models run on the RX 580)
REM    5. checks the installation and offers to start the app
REM
REM  Run it again at any time to repair the environment or after "git pull".
REM  Do NOT use Win-Install-or-Update.bat or the in-app updater on this branch:
REM  they switch the code to the "main" branch.
REM
REM  Options:  --no-start   do not offer to start the app at the end
REM ============================================================

set "PYTHONUTF8=1"
set "UV_LINK_MODE=copy"
cd /d "%~dp0"
set "MT_DIR=%CD%"
title Manga Translator UI - install (RX 580 / Windows 10)

echo ============================================================
echo  Manga Translator UI - install for RX 580 (DirectML)
echo ============================================================
echo.

REM ---------- 1) Windows and project path ----------
echo [1/5] Checking Windows...
set "ARCH=%PROCESSOR_ARCHITECTURE%"
if defined PROCESSOR_ARCHITEW6432 set "ARCH=%PROCESSOR_ARCHITEW6432%"
if /I not "%ARCH%"=="AMD64" (
    echo [ERROR] 64-bit Windows is required, this system reports "%ARCH%".
    goto :fail
)

set "WINBUILD="
for /f "usebackq delims=" %%i in (`powershell -NoProfile -Command "(Get-CimInstance Win32_OperatingSystem).BuildNumber"`) do set "WINBUILD=%%i"
if not defined WINBUILD (
    echo [WARN] Could not detect the Windows build number, continuing.
    goto :path_check
)
echo       Windows build: !WINBUILD!
if !WINBUILD! LSS 18362 (
    echo [ERROR] DirectML needs Windows 10 version 1903 ^(build 18362^) or newer.
    echo         Please run Windows Update and try again.
    goto :fail
)

:path_check
powershell -NoProfile -Command "if ($env:MT_DIR -match '[^\x00-\x7F]') { exit 1 } else { exit 0 }" >nul 2>&1
if errorlevel 1 (
    echo [WARN] The project path contains non-English characters:
    echo          !MT_DIR!
    echo        Some Python packages fail in such paths. If the install or the app
    echo        fails, move the folder to a short English path such as C:\manga-translator-ui
)
powershell -NoProfile -Command "$lp=(Get-ItemProperty 'HKLM:\SYSTEM\CurrentControlSet\Control\FileSystem' -ErrorAction SilentlyContinue).LongPathsEnabled; if ($env:MT_DIR.Length -gt 80 -and $lp -ne 1) { exit 1 } else { exit 0 }" >nul 2>&1
if errorlevel 1 (
    echo [WARN] The project path is long and Windows long paths are disabled.
    echo        PyTorch has deep file paths and may fail to install. Move the folder to
    echo        a short path such as C:\manga-translator-ui
)

REM ---------- 2) Visual C++ runtime ----------
echo [2/5] Checking Visual C++ runtime...
if exist "%SystemRoot%\System32\vcruntime140_1.dll" if exist "%SystemRoot%\System32\msvcp140.dll" (
    echo       Already installed.
    goto :uv
)
echo       Not found. Downloading Microsoft Visual C++ Redistributable ^(x64^)...
set "VCREDIST=%TEMP%\vc_redist.x64.exe"
powershell -NoProfile -Command "[Net.ServicePointManager]::SecurityProtocol=[Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -UseBasicParsing -Uri 'https://aka.ms/vs/17/release/vc_redist.x64.exe' -OutFile $env:VCREDIST"
if errorlevel 1 (
    echo [ERROR] Download failed. Install it manually from:
    echo         https://aka.ms/vs/17/release/vc_redist.x64.exe
    goto :fail
)
echo       Installing ^(accept the administrator prompt^)...
"%VCREDIST%" /install /passive /norestart
set "RC=!ERRORLEVEL!"
REM 0 = installed, 1638 = a newer version is already installed, 3010 = restart required
if "!RC!"=="3010" echo [INFO] Restart Windows after this installer finishes.
if not "!RC!"=="0" if not "!RC!"=="1638" if not "!RC!"=="3010" (
    echo [ERROR] Visual C++ runtime installation failed ^(code !RC!^).
    goto :fail
)

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
echo [5/5] Verifying the installation...
powershell -NoProfile -Command "Get-CimInstance Win32_VideoController | ForEach-Object { '      GPU: ' + $_.Name + ' - driver ' + $_.DriverVersion }"
".venv\Scripts\python.exe" -c "import torch, onnxruntime as o; p=o.get_available_providers(); print('      torch', torch.__version__, '| onnxruntime', o.__version__); print('      ONNX providers:', ', '.join(p)); raise SystemExit(0 if 'DmlExecutionProvider' in p else 3)"
set "RC=!ERRORLEVEL!"
if "!RC!"=="3" (
    echo [WARN] onnxruntime-directml is not active, ONNX models will run on the CPU.
    echo        Run this file again to repair the environment.
    goto :done
)
if not "!RC!"=="0" (
    echo [ERROR] PyTorch or ONNX Runtime failed to load ^(code !RC!^).
    echo         Restart Windows if the Visual C++ runtime was just installed, then run
    echo         this file again. Manual runtime download:
    echo         https://aka.ms/vs/17/release/vc_redist.x64.exe
    goto :fail
)
echo       DirectML is installed. The app log shows "ONNX Runtime is using DirectML"
echo       when a model really runs on the GPU; otherwise it falls back to the CPU.
echo       Keep the AMD Radeon driver up to date for DirectX 12 / DirectML.

:done
echo.
echo ============================================================
echo  Done. Start the app with Win10-RX580-Start.bat
echo ============================================================
if /I "%~1"=="--no-start" goto :end
echo.
choice /C YN /N /T 30 /D Y /M "Start the app now? [Y/N] (Y in 30 s): "
if errorlevel 2 goto :end
call "%~dp0Win10-RX580-Start.bat"
exit /b !ERRORLEVEL!

:end
pause
exit /b 0

:fail
echo.
echo Installation did not finish.
pause
exit /b 1
