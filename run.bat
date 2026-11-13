@echo off
title Teleport Hole - Drill Machine VFX
cd /d "%~dp0"

echo =====================================================================
echo    TELEPORT HOLE - DRILL MACHINE EDITION (HOLLYWOOD REAL-TIME VFX)
echo =====================================================================
echo.
echo Starting Python script...
echo.

python teleport_portal.py %*

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] Script encountered an error.
    pause
)
