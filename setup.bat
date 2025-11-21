@echo off
echo Setting up OBS Trojan Windows Client...

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo Python is not installed or not in PATH
    echo Please install Python 3.8+ from https://python.org
    pause
    exit /b 1
)

REM Check if Redis is installed
redis-server --version >nul 2>&1
if errorlevel 1 (
    echo Redis is not installed
    echo Installing Redis using Chocolatey...
    
    REM Check if Chocolatey is installed
    choco --version >nul 2>&1
    if errorlevel 1 (
        echo Chocolatey is not installed
        echo Installing Chocolatey...
        powershell -Command "Set-ExecutionPolicy Bypass -Scope Process -Force; [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072; iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))"
    )
    
    REM Install Redis
    choco install redis-64 -y
)

REM Install Python dependencies
echo Installing Python dependencies...
pip install -r requirements.txt

REM Start Redis server
echo Starting Redis server...
start "Redis Server" redis-server

REM Wait a moment for Redis to start
timeout /t 3 /nobreak >nul

echo Setup complete!
echo.
echo To run the client:
echo   python client.py
echo.
echo Redis server is running in a separate window
echo Default connection: localhost:6379
echo.
pause
