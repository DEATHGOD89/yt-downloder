@echo off
setlocal
cd /d "%~dp0"

set "EXE_PATH=%~dp0dist\YouTube_Downloader\YouTube_Downloader.exe"
if exist "%EXE_PATH%" (
    start "" "%EXE_PATH%"
    exit /b 0
)

rem Dynamic pythonw search avoiding WindowsApps alias
set "PY_EXE=%LOCALAPPDATA%\Programs\Python\Python313\pythonw.exe"
if not exist "%PY_EXE%" (
    for /f "delims=" %%I in ('where pythonw.exe 2^>nul ^| findstr /i /v "WindowsApps"') do (
        set "PY_EXE=%%I"
        goto :launch
    )
)

:launch
if exist "%PY_EXE%" (
    start "" "%PY_EXE%" "%~dp0app.py"
    exit /b 0
)

start "" python "%~dp0app.py"
exit /b 0
