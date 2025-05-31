@echo off
chcp 65001>nul
setlocal

call :print_header "[1;36m   🚀 Running jufDeaSoftware 🚀"
 
REM Check and install uv if not available
where uvx >nul 2>&1
if errorlevel 1 (
    call :color_echo "[1;34mInstalling/updating UV from Astral.sh..."
    powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
) else (
    call :color_echo "[1;32mUV is already installed, skipping..."
)
echo.
 
REM Check and install git if not available
where git >nul 2>&1
if errorlevel 1 (
    call :color_echo "[1;34mInstalling/updating Git..."
    winget install --id Git.Git -e --source winget
) else (
    call :color_echo "[1;32mGit is already installed, skipping..."
)
echo.
 
call :color_echo "[1;34mRunning jufDeaSoftware, installing dependencies if needed..."
uvx --from git+https://github.com/flol3622/jufDea.git@uvx jufDea
if errorlevel 1 (
    call :color_error "uvx did not work. Please restart the script to use the new tools."
    pause
    exit /b
)
echo.

REM --- Helper subroutines ---
:print_header
cls
call :color_echo "[1;35m==========================================="
call :color_echo "%~1"
call :color_echo "[1;35m==========================================="
echo.
exit /b

REM --- Color echo functions ---
:color_echo
powershell -Command "Write-Host '%~1'"
exit /b
:color_success
powershell -Command "Write-Host '%~1' -ForegroundColor Green"
exit /b
:color_error
powershell -Command "Write-Host '%~1' -ForegroundColor Red"
exit /b
:color_warn
powershell -Command "Write-Host '%~1' -ForegroundColor Yellow"
exit /b
