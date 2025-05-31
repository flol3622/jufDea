@echo off
chcp 65001>nul
setlocal

goto :main_menu

:main_menu
call :print_header "[1;36m   🚀 jufDeaSoftware Main Menu 🚀"

call :color_echo "[1;33m   1. Run jufDeaSoftware"
call :color_echo "[1;33m   2. Install/Update Required Software"
echo.
set /p "CHOICE=[1;37mEnter your choice (1-2): [0m"

if "%CHOICE%"=="1" goto :run_script
if "%CHOICE%"=="2" goto :install_software

call :color_error "❌ Invalid choice. Please try again."
pause
goto :main_menu

:install_software
call :print_header "[1;36m   🛠️  Installing Required Software 🛠️"

REM Step 1: Install or update uv
call :color_echo "[1;34m[1/2] Installing / updating UV from Astral.sh..."
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
echo.

REM Step 2: Install git
call :color_echo "[1;34m[2/2] Installing / updating Git..."
winget install --id Git.Git -e --source winget
echo.
goto :main_menu

:run_script
call :print_header "[1;36m   🚀 Running jufDeaSoftware 🚀"
call :color_echo "[1;34mRunning jufDeaSoftware, installing dependencies if needed..."
uvx --from git+https://github.com/flol3622/jufDea.git@uvx jufDea
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
