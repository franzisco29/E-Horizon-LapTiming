@echo off
title LapTimingPython - START
cd /d "%~dp0"

echo Attivazione ambiente virtuale...
call .venv\Scripts\activate

echo.
echo Python usato:
where python
python -V

echo.
echo Avvio applicazione...
python main.py

echo.
echo Applicazione terminata.
pause
