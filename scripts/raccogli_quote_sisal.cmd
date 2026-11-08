@echo off
cd /d "%~dp0.."
".venv\Scripts\python.exe" "scripts\raccogli_quote_sisal.py" %*
set "SISAL_EXIT=%ERRORLEVEL%"
echo.
echo Raccolta conclusa. Consulta reports\analisi_2627_prestazioni.html
pause
exit /b %SISAL_EXIT%
