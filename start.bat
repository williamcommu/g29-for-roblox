@echo off
echo Starting G29 to Roblox Interface...
echo.
echo New Features:
echo - Mouse Steering (Smooth analog input)
echo - Virtual Xbox Controller support
echo - Multiple control modes
echo - Enhanced configuration options
echo.
echo Make sure your wheel is connected!
echo.
pause
cd /d "%~dp0"
.venv\Scripts\python.exe main.py
pause
