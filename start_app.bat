@echo off
title LapTimingPython - START

echo Attivazione ambiente virtuale...
call .venv\Scripts\activate

echo.
echo Avvio applicazione...
python main.py

echo.
echo Applicazione terminata.
pause
