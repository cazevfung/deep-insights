#!/bin/bash
# Cross-platform dependency installer wrapper for Unix (macOS/Linux)
# This script calls the Python installer script

echo "============================================================="
echo "Research Tool - Dependency Installer (Unix)"
echo "============================================================="
echo ""

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    if ! command -v python &> /dev/null; then
        echo "ERROR: Python not found!"
        echo "Please install Python 3.9+ from https://www.python.org/"
        exit 1
    else
        PYTHON_CMD="python"
    fi
else
    PYTHON_CMD="python3"
fi

# Make script executable
chmod +x install_dependencies.py

# Run the Python installer with all arguments passed through
echo ""
echo "Note: Use --restart-backend to restart the backend server"
echo "      Example: ./install_dependencies.sh --start --restart-backend"
echo ""
$PYTHON_CMD install_dependencies.py "$@"

# Exit with the same code
exit $?

