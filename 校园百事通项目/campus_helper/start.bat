@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo ==========================================
echo    Campus Helper - Start Script
echo ==========================================
echo.

:: Activate virtual environment
if exist venv\Scripts\activate (
    call venv\Scripts\activate
) else (
    echo [Warning] venv not found, using system Python
    echo.
)

:: Create necessary directories
if not exist data\raw_docs mkdir data\raw_docs
if not exist data\knowledge_base mkdir data\knowledge_base
if not exist logs mkdir logs

echo [1/2] Starting backend service...
echo       API Docs: http://localhost:8000/docs
echo.

:: Start backend
start "Campus Helper Backend" cmd /k "python backend\main.py"

:: Wait for backend to start
timeout /t 5 /nobreak >nul

echo [2/2] Opening frontend...
echo.

:: Open frontend
start "" "frontend\index.html"

echo ==========================================
echo    Started!
echo    Backend: http://localhost:8000
echo    Frontend: frontend/index.html
echo ==========================================
echo.
pause
