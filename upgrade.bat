@echo off
echo ===============================
echo   Installing requirements
echo ===============================

REM Attiva venv se esiste
IF EXIST .venv\Scripts\activate (
    call .venv\Scripts\activate
)

py -m pip --version
py -m pip install -r requirements.txt

echo.
echo Installation completed successfully!
pause