#!/bin/bash
# IFC Reinforcement Analysis - Quick Launch Script
# This script launches the Gradio application

echo "================================================================================"
echo "🏗️  IFC Reinforcement Analysis Application"
echo "================================================================================"
echo ""
echo "Starting the application..."
echo ""
echo "The application will open in your default web browser at:"
echo "http://127.0.0.1:7860"
echo ""
echo "Press Ctrl+C to stop the server when you're done."
echo "================================================================================"
echo ""

# Try python3 first, then python
if command -v python3 &> /dev/null; then
    python3 app.py
elif command -v python &> /dev/null; then
    python app.py
else
    echo "❌ ERROR: Python is not installed or not in PATH"
    echo ""
    echo "Please install Python 3.8 or higher"
    echo ""
    exit 1
fi
