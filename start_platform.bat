@echo off
setlocal

echo.
echo  🚀 BuildFlow Secure AI - Local Startup Script
echo  ============================================
echo.

:: Check for Docker
docker --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Docker is not installed or not in PATH.
    echo Please install Docker Desktop to run BuildFlow with all services.
    pause
    exit /b 1
)

:: Check for backend/.env
if not exist "backend\.env" (
    echo [INFO] backend/.env not found. Creating from .env.example...
    copy "backend\.env.example" "backend\.env"
    echo [WARNING] Please edit backend/.env and add your API keys (Gemini/OpenAI).
)

:: Ask how to run
echo How would you like to start the platform?
echo [1] Docker Compose (Recommended - includes Redis)
echo [2] Individual Processes (Manual - requires Python/Node installed)
set /p choice="Enter choice [1-2]: "

if "%choice%"=="1" (
    echo.
    echo [INFO] Starting BuildFlow via Docker Compose...
    docker-compose up --build
) else if "%choice%"=="2" (
    echo.
    echo [INFO] Starting Backend...
    start "BuildFlow Backend" cmd /c "cd backend && pip install -r requirements.txt && python main.py"
    
    echo [INFO] Starting Frontend...
    start "BuildFlow Frontend" cmd /c "cd frontend && npm install && npm run dev"
    
    echo.
    echo [SUCCESS] Processes started in new windows.
    echo Backend: http://localhost:8000
    echo Frontend: http://localhost:5173
) else (
    echo Invalid choice.
)

pause
