@echo off
cd /d "%~dp0"
if exist Scripts\activate.bat call Scripts\activate.bat
python server.py
pause