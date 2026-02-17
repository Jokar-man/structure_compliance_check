@echo off
REM IFC Reinforcement Analysis - Quick Launch Script
REM This script launches the Gradio application

echo ================================================================================
echo IFC Reinforcement Analysis Application
echo ================================================================================
echo.
echo Starting the application...
echo.
echo The application will open in your default web browser at:
echo http://127.0.0.1:7860
echo.
echo Press Ctrl+C to stop the server when you're done.
echo ================================================================================
echo.

REM Try python3 first, then python
python3 app.py 2>nul
if errorlevel 1 (
    python app.py 2>nul
    if errorlevel 1 (
        echo ERROR: Python is not installed or not in PATH
        echo.
        echo Please install Python 3.8 or higher from https://www.python.org/
        echo.
        pause
        exit /b 1
    )
)

pause
