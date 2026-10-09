@echo off
cd /d "%~dp0"
set PY=pythonw
if exist Scripts\pythonw.exe set PY=Scripts\pythonw.exe
start "" /B %PY% server.py >> server.log 2>&1
echo दृष्टि-IO is running in the background. Open http://localhost:5000/dashboard . Logs: server.log
echo To stop it, run stop_bg.bat