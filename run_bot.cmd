@echo off
setlocal

<<<<<<< codex/rules-command
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
=======
set "SCRIPT_DIR=%~dp0"
set "SCRIPT_DIR=%SCRIPT_DIR:\\?\=%"
pushd "%SCRIPT_DIR%" >nul 2>nul
if errorlevel 1 (
    echo Failed to change directory to "%SCRIPT_DIR%"
    exit /b 1
)

set "PORTABLE_PYTHON=%CD%\tools\python312\python.exe"
set "MAIN_FILE=%CD%\main.py"

if exist "%PORTABLE_PYTHON%" (
    "%PORTABLE_PYTHON%" "%MAIN_FILE%"
    exit /b %errorlevel%
)

where python >nul 2>nul
if %errorlevel%==0 (
    python "%MAIN_FILE%"
    exit /b %errorlevel%
>>>>>>> main
)

echo Python not found. Install Python or place portable Python at tools\python312\python.exe
exit /b 1
