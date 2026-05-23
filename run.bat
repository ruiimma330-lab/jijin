@echo off
setlocal
cd /d "%~dp0"

echo.
echo   ======================================
echo     Fund/Stock Investment Platform
echo   ======================================
echo.

rem -- Check uv -----------------------------------------------
where uv >nul 2>&1
if errorlevel 1 (
    echo   [ERROR] uv not found. Install: pip install uv
    echo.
    pause
    exit /b 1
)

rem -- Check venv ---------------------------------------------
if not exist ".venv\Scripts\python.exe" (
    echo   [INFO] First run, installing dependencies...
    uv sync
    if errorlevel 1 (
        echo   [ERROR] Dependency install failed
        pause
        exit /b 1
    )
    echo   [OK] Dependencies installed
)

rem -- Launch -------------------------------------------------
echo   [INFO] Starting Streamlit...
echo   [URL]  http://localhost:8501
echo.

start "" http://localhost:8501

".venv\Scripts\python.exe" -m streamlit run app/app.py

echo.
echo   [INFO] Server stopped
pause >nul
