@echo off
title Label Police - Backend Server
echo ============================================
echo   Label Police Backend (FastAPI + Uvicorn)
echo ============================================
echo.

cd /d "%~dp0backend"

if not exist "venv\Scripts\activate.bat" (
    echo [ERROR] Virtual environment not found at backend\venv
    echo Run:  cd backend ^&^& python -m venv venv ^&^& venv\Scripts\activate ^&^& pip install -r requirements.txt
    pause
    exit /b 1
)

echo Activating virtual environment...
call venv\Scripts\activate.bat

echo Installing/updating dependencies...
pip install -r requirements.txt --quiet

echo.
echo Starting backend on http://0.0.0.0:8000
echo Docs at       http://localhost:8000/docs
echo Health check  http://localhost:8000/api/v1/health
echo.
echo Press Ctrl+C to stop.
echo ============================================
uvicorn main:app --host 0.0.0.0 --port 8000 --reload

pause
