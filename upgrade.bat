@echo off
echo ===============================
echo   Installing requirements
echo ===============================

REM Attiva venv se esiste
IF EXIST .venv\Scripts\activate (
    call .venv\Scripts\activate
)

echo.
echo Installing from requirements.txt ...
pip install -r requirements.txt

IF %ERRORLEVEL% NEQ 0 (
    echo.
    echo ERROR during installation!
    pause
    exit /b
)

echo.
echo Installation completed successfully!
pause