@echo off
if "%~1"=="" (
  echo Trascina su questo file il JSON esportato dall'estensione Chrome.
  pause
  exit /b 2
)
cd /d "%~dp0.."
".venv\Scripts\python.exe" "scripts\raccogli_quote_sisal.py" --import-extension "%~f1"
set "SISAL_IMPORT_EXIT=%ERRORLEVEL%"
echo.
echo Consulta reports\analisi_2627_prestazioni.html per lo stato delle quote.
pause
exit /b %SISAL_IMPORT_EXIT%
