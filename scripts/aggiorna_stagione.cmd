@echo off
REM ---------------------------------------------------------------------
REM Fase 14 / A1 - aggiornamento settimanale della stagione in corso.
REM
REM Scarica i dati evento nuovi dei cinque campionati, rigenera i Parquet,
REM aggiorna il manifest e rifa' la pagina delle previsioni.
REM
REM DUE MODI DI USARLO, ed e' voluto che siano lo stesso file:
REM   - a mano, quando si vuole:      scripts\aggiorna_stagione.cmd
REM   - dall'attivita' pianificata del martedi' (scripts\attivita_martedi.xml)
REM
REM E' SICURO rilanciarlo quante volte si vuole. Lo scraper e' idempotente
REM (vincolo 9): una partita gia' su disco viene saltata e mai riscritta, e i
REM derivati si ricostruiscono solo se un CSV e' piu' recente dei Parquet.
REM Se non c'e' niente di nuovo, finisce in pochi secondi senza toccare nulla.
REM
REM Per registrare l'attivita' pianificata:
REM   schtasks /Create /TN "Calcio-aggiorna-martedi" /XML "scripts\attivita_martedi.xml"
REM Per toglierla:
REM   schtasks /Delete /TN "Calcio-aggiorna-martedi" /F
REM ---------------------------------------------------------------------
cd /d "C:\Users\mirk5\manimations\Scrape-Whoscored-Event-Data"

set "LOG=reports\aggiornamento_auto.log"
if not exist reports mkdir reports

echo. >> "%LOG%"
echo ================================================== >> "%LOG%"
echo [%date% %time%] AVVIO aggiornamento settimanale >> "%LOG%"

".venv\Scripts\python.exe" "scripts\aggiorna_stagione.py" %* >> "%LOG%" 2>&1
set RC=%ERRORLEVEL%

echo [%date% %time%] FINE (codice %RC%) >> "%LOG%"
exit /b %RC%
