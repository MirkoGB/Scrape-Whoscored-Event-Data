@echo off
REM ---------------------------------------------------------------------
REM Fase 13 / G2 - ripresa automatica dell'acquisizione WhoScored.
REM
REM Registrato come attivita' pianificata al logon (2026-08-24) su richiesta
REM dell'utente, che spegne il PC durante l'acquisizione: ~2.500 partite
REM residue non stanno in una sessione sola.
REM
REM E' SICURO rilanciarlo quante volte si vuole: lo scraper e' idempotente
REM (vincolo 9), una partita gia' su disco viene saltata e mai riscritta.
REM Se non c'e' nulla da fare, ogni campionato finisce in pochi secondi.
REM
REM I campionati gia' chiusi NON sono elencati: la Serie A e la Premier sono
REM complete, e rimetterle qui farebbe ritentare a ogni accensione le 3
REM partite che WhoScored non ha - richieste inutili verso la fonte.
REM
REM Per disattivare:  schtasks /Delete /TN "Whoscored-riprendi" /F
REM ---------------------------------------------------------------------
cd /d "C:\Users\mirk5\manimations\Scrape-Whoscored-Event-Data"

set "LOG=reports\acquisizione_auto.log"
if not exist reports mkdir reports

echo. >> "%LOG%"
echo ================================================== >> "%LOG%"
echo [%date% %time%] AVVIO ripresa automatica >> "%LOG%"

for %%L in (ESP-la-liga GER-bundesliga FRA-ligue-1) do (
    echo [%date% %time%] --- %%L --- >> "%LOG%"
    ".venv\Scripts\python.exe" "acquisition\whoscored\scrape_season.py" --league %%L >> "%LOG%" 2>&1
)

echo [%date% %time%] FINE >> "%LOG%"
