@echo off
echo ===============================
echo   Setup Virtual Environment
echo ===============================

REM Se non esiste .venv lo crea
IF NOT EXIST .venv (
    echo Creating virtual environment...
    py -m venv .venv
)

REM Attiva il venv
call .venv\Scripts\activate

echo.
echo Upgrading pip...
py -m pip install --upgrade pip

echo.
echo Installing requirements...
py -m pip install -r requirements.txt

echo.
echo Done!
pause