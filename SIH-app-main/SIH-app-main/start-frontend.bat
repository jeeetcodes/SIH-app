@echo off
title Label Police - Expo Frontend
echo ============================================
echo   Label Police Frontend (Expo)
echo ============================================
echo.

cd /d "%~dp0mobile"

where node >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Node.js not found. Install it from https://nodejs.org/
    pause
    exit /b 1
)

if not exist "node_modules" (
    echo node_modules not found. Installing dependencies...
    call npm install
    echo.
)

echo Starting Expo dev server...
echo Scan the QR code with Expo Go on your phone.
echo Press Ctrl+C to stop.
echo ============================================
echo.
call npx expo start --tunnel

pause
