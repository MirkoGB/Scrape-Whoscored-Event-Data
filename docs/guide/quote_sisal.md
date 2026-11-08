# Raccolta automatica delle quote Sisal

È disponibile anche l'[estensione Chrome locale](estensione_sisal.md): raccoglie
le quote nelle pagine aperte normalmente e le esporta senza un nuovo accesso
Selenium al sito. L'importazione usa gli stessi controlli del raccoglitore.

## Uso

Eseguire dalla radice del progetto:

```powershell
.\.venv\Scripts\python.exe scripts/raccogli_quote_sisal.py
```

Oppure aprire `scripts/raccogli_quote_sisal.cmd` con doppio clic. Il comando
cerca i link alle partite del catalogo di previsioni nelle pagine pubbliche
Sisal, legge i mercati riconoscibili, archivia le prove e rigenera
`reports/analisi_2627_prestazioni.html`. Chrome lavora senza finestra e si chiude
al termine. Non vengono installati servizi o attività pianificate.

Se il calendario pubblico non espone i link, si possono indicare le pagine
delle partite, lasciando automatica tutta l'acquisizione dei mercati:

```powershell
.\.venv\Scripts\python.exe scripts/raccogli_quote_sisal.py --event-url "URL_SISAL_DELLA_PARTITA"
```

`--event-url` è ripetibile. `--headed` mostra Chrome; `--max-events` limita le
pagine partita (default 50), `--timeout` il caricamento (default 25 secondi).
`--driver` permette di indicare un chromedriver locale; altrimenti viene usato
Selenium Manager. Il browser usa un profilo temporaneo, senza credenziali del
profilo personale. Non effettua accessi al conto, prenotazioni o giocate.

## Stato della verifica

Il 17 settembre 2026 la pagina pubblica non è stata caricata nell'ambiente di
esecuzione: Chrome ha restituito `ERR_HTTP2_PROTOCOL_ERROR`, HTTP/1.1 e la lettura
HTTPS diretta sono andati in timeout. Nessuna quota reale è stata acquisita
in quel tentativo, conservato nel registro.

Il **19 settembre 2026**, usando l'estensione in un profilo separato di Chrome
for Testing, la lettura reale è riuscita: **81 linee Over** di Fiorentina–Napoli,
**27 quote abbinate** a previsioni precedenti e importate nel report. Il formato
STATS MATCH è stato verificato sul DOM reale. Monza–Sassuolo si apre ma mostra
“Nessuna Scommessa Quotata”. Vedere la [guida all'estensione](estensione_sisal.md).

I test automatici usano fixture sintetiche dichiarate, separate dalla prova
reale. Se il sito presenta un formato diverso da quelli riconoscibili,
il comando lo segnala e non inventa abbinamenti. Il registro dei tentativi
permette di distinguere errori di accesso, link non riconosciuti, identità della
partita non verificata e assenza di mercati leggibili. La verifica su una partita
non attesta la copertura di tutti i formati o la disponibilità continua.

## Cosa viene riconosciuto automaticamente

- Etichette esplicite U/O tiri totali e tiri in porta: casa, ospite o totale.
- Quote decimali visibili con linea a mezzo punto indicata nell'esito o nel
  titolo. Celle disabilitate, linee implicite, prezzi discordanti e formati
  ambigui vengono esclusi.
- Identità casa/ospite e kickoff letti da `SportsEvent` JSON-LD, oppure titolo
  esatto delle squadre e un unico elemento `time` con data, ora e fuso.
  Il formato locale Sisal viene interpretato in Europe/Rome solo con riscontro
  esatto nelle squadre, nella data e nell'ora visibili della pagina.
- Abbinamento esatto a una previsione anteriore per quella gara e linea.
  Le differenze nei nomi non vengono risolte con corrispondenze approssimative.

Mercati giocatore, primo/secondo tempo, supplementari, live e linee non previste
sono esclusi. La disponibilità è quella osservata alla raccolta: non prova che
la quota sia ancora accettabile nel momento di una successiva giocata.

## Registro e report

Le rilevazioni e i tentativi sono append-only in
`data/external/paper_over/sisal/observations` e `sisal/runs`. Ogni pagina letta
ha un JSON della lettura DOM, timestamp, URL e hash in `sisal/evidence`;
il raccoglitore Selenium aggiunge uno screenshot, l'estensione esporta solo
i metadati pubblici previsti. Non si archiviano cookie, intestazioni di autenticazione o
credenziali. I file storici non vengono sovrascritti.

Nel suggeritore, **Solo quote Sisal raccolte da meno di 60 minuti** limita la
ricerca agli esiti dell'ultima raccolta, ancora anteriori al kickoff. Una nuova
raccolta fallita non riattiva quote vecchie. Senza esiti sufficienti viene
mostrato “nessuna giocata”. La scheda mostra la quota singola e il momento della
rilevazione. Per una singola l'EV è un'ipotesi di equivalenza delle regole;
per una multipla la quota complessiva non viene inventata moltiplicando i prezzi.
Il report è statico: dopo la raccolta va ricaricato nel browser.

## Soglia minima e “Giocare bene”

Il suggeritore richiede sempre una quota Sisal recente **strettamente superiore
a 1,05 per ogni evento**: 1,05 esatto e quote mancanti sono esclusi. La soglia
si riferisce al prezzo offerto, non alla quota teorica del modello.

Attivando **Giocare bene**, l'utente sceglie il **vantaggio atteso minimo (%)**:
non c'è un valore preimpostato. Senza un margine valido, non viene proposta
alcuna schedina. Il filtro applica a ogni selezione la formula
`probabilità del modello × quota Sisal − 1 ≥ margine scelto`.
Per esempio, probabilità 70% e quota 1,50 danno un rendimento atteso del 5%
per unità puntata, assumendo probabilità corrette e regole equivalenti.
Non è un distacco di 5 punti percentuali di probabilità.

Il margine del bookmaker è già nel prezzo offerto: la soglia scelta è un
ulteriore requisito dell'utente, non una seconda commissione da sottrarre.
La tabella mostra le linee che superano il filtro, quota di pareggio, distacco
`p − 1/quota`, EV e sensibilità abbassando `p` di 5 punti percentuali.
Questa sensibilità non è un intervallo di confidenza.

Fra le linee ammesse viene massimizzata la probabilità combinata, con una sola
selezione per partita. Se non bastano le partite, resta **nessuna giocata**.
La quota complessiva di una multipla deve essere rilevata separatamente.
I filtri esplorativi non modificano il protocollo economico congelato e non
trasformano le osservazioni Sisal in quote ammesse al test di profitto.

Le osservazioni **non vengono inserite automaticamente nel registro economico
`quotes`**: quest'ultimo richiede la regola `opta_90min_halfline`, mentre Sisal
prevede nei mercati consultati dati ufficiali dell'organizzatore e Opta in loro
assenza. L'equivalenza delle definizioni va verificata prima di ammetterle al
test economico. Il raccoglitore dichiara la regola distinta
`sisal_official_opta_fallback_90min_halfline` e `economic_eligible: false`.
Non si modifica il protocollo congelato né si registrano decisioni di puntata.

Fonti: [palinsesto calcio](https://www.sisal.it/scommesse-matchpoint/sport/calcio),
[regolamento calcio](https://www.sisal.it/content/dam/new-dam/italy/canali/sisal-it/doc-pdf/scommesse/info-scommesse/calcio.pdf),
[fogli quote ufficiali](https://www.sisal.it/scommesse-matchpoint/foglio-quote).

Per aggiornare un catalogo di previsioni scaduto, prima eseguire
`scripts/paper_over.py snapshot` con Python della `.venv`.
Verifiche locali: `python -m pytest tests/test_sisal.py` e
`node --test tests/test_suggestion_engine.cjs`.
