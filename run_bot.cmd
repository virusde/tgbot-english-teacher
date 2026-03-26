@echo off
setlocal

set "PROJECT_ROOT=%~dp0"
set "PORTABLE_PYTHON=%PROJECT_ROOT%tools\python312\python.exe"
set "MAIN_FILE=%PROJECT_ROOT%main.py"

if exist "%PORTABLE_PYTHON%" (
    "%PORTABLE_PYTHON%" "%MAIN_FILE%"
    exit /b %ERRORLEVEL%
)

where python >nul 2>nul
if %ERRORLEVEL%==0 (
    python "%MAIN_FILE%"
    exit /b %ERRORLEVEL%
)

echo Python not found. Install Python or place portable Python at tools\python312\python.exe
exit /b 1
