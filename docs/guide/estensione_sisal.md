# Estensione Chrome: quote Sisal locali

## Aggiornare alla versione 0.3.0

In `chrome://extensions`, sulla scheda **Quote Sisal — raccolta locale**, premere
**Ricarica** (freccia circolare) e verificare la versione **0.3.0**. Se l'estensione
era stata copiata altrove, usare la cartella aggiornata `extensions/sisal-quotes`
di questo progetto. Riaprire il popup dalla scheda Sisal e premere
**Leggi questa pagina**. Se Chrome richiede di abilitare i permessi aggiornati,
confermare l'accesso alla pagina Sisal per usare il pulsante.

La versione 0.3 ricollega il lettore quando si preme il pulsante, anche per
schede aperte prima dell'installazione o del ricaricamento dell'estensione.
Il messaggio **Pagina salvata nell'archivio** compare solo dopo la conferma
del salvataggio. Gli errori mostrano il dettaglio invece di attribuire ogni
problema al caricamento del sito. Il conteggio si aggiorna anche durante la
raccolta automatica; leggere di nuovo la stessa pagina aggiorna una voce,
non aumenta il numero di pagine archiviate.

Correzioni della 0.3, verificate il 20 settembre:

- Il cambio partita dentro Sisal può mantenere in Chrome l'URL iniziale del
  documento. Il salvataggio verifica ora l'URL attuale dello stesso documento,
  senza confondere quote di pagine diverse.
- Il layout desktop inserisce i limiti di puntata sotto il nome del mercato:
  il lettore distingue l'etichetta dai limiti e riconosce anche gli Over delle
  singole squadre. Su Frosinone–Como la prova reale è passata da 27 a **75 linee**,
  corrispondenti a tutte le linee supportate presenti nella pagina acquisita.
- L'anteprima mostra tutte le linee salvate in un elenco scorrevole, anziché
  limitarsi alle prime otto.

La copertura riguarda gli Over tiri e tiri in porta di squadra e partita.
Mercati giocatore, 1X2, combo e singoli tempi restano fuori dal modello.
I gruppi chiusi o non caricati non sono leggibili: aprire quelli desiderati
prima di premere **Leggi questa pagina**.

Il permesso `scripting`, insieme ad `activeTab`, serve a collegare il lettore
alla scheda su cui si è aperta l'estensione. Il codice verifica dominio e
percorso Sisal prima di eseguirlo. Riferimento: [API scripting di Chrome](https://developer.chrome.com/docs/extensions/reference/api/scripting).

## Caricamento nel proprio Chrome

1. Aprire `chrome://extensions` e attivare **Modalità sviluppatore**.
2. Scegliere **Carica estensione non pacchettizzata**.
3. Selezionare la cartella `extensions/sisal-quotes` di questo progetto,
   quella che contiene `manifest.json`.
4. Dal pulsante Estensioni di Chrome, fissare **Quote Sisal — raccolta locale**.
5. Aprire una partita ancora in palinsesto e scegliere **STATS MATCH**:
   qui vengono caricati i mercati tiri e tiri in porta. Se l'estensione è stata
   caricata dopo la pagina, ricaricare la pagina.

L'estensione legge automaticamente i mercati caricati. Il badge indica il
numero di blocchi riconosciuti, non il numero di quote già convalidate.
Cliccando l'icona si apre un'anteprima; **Leggi questa pagina** forza una nuova
lettura e salva anche se la raccolta automatica è in pausa. Il selettore
permette di mettere in pausa soltanto la raccolta automatica.

Non occorre un altro browser, né Selenium. L'estensione funziona nelle schede
Sisal aperte normalmente dal proprietario del browser. Non carica pagine da
sola e non può leggere un sito che non si apre nel browser.

## Dal browser al report

1. Nel popup scegliere **Esporta per il report**.
2. Trascinare il JSON scaricato su `scripts/importa_quote_sisal.cmd`.
3. Ricaricare `reports/analisi_2627_prestazioni.html` e usare **Solo quote Sisal
   raccolte da meno di 60 minuti**.

In alternativa:

```powershell
.\.venv\Scripts\python.exe scripts/raccogli_quote_sisal.py --import-extension "percorso\sisal_quote_DATA.json"
```

La raccolta nel browser è automatica; esportazione e importazione richiedono
questi due gesti. Nessun servizio resta in ascolto sul computer.

## Cosa viene conservato

Solo metadati della partita e dei mercati: pagina, orario della lettura, nomi
delle squadre e kickoff se disponibili, etichette, linee, quote e stato disabilitato.
Non vengono esportati testo completo della pagina, cookie, credenziali, saldo,
cronologia del browser o richieste di rete. Non esistono invii a server esterni.

L'archivio locale conserva l'ultima lettura di ciascuna pagina, fino a 50 pagine.
Aprire insieme i mercati che si vogliono conservare: chiudendoli, una nuova
lettura può sostituire quella precedente con meno mercati. Una pagina vuota
non riutilizza silenziosamente quote lette in precedenza.
**Svuota archivio** cancella soltanto i dati dell'estensione e mette in pausa
la raccolta; non elimina il registro Python.

All'importazione restano validi i controlli su partita, linea esatta, previsione
anteriore, kickoff futuro e rilevazione entro 60 minuti. La data di registrazione
viene aggiunta dal programma, non fornita dal file. Timestamp del browser e hash
non sono una certificazione esterna dell'anteriorità. Le osservazioni mantengono
`economic_eligible: false` finché le regole Sisal non sono riconciliate con il
protocollo del modello. Nessuna selezione viene inviata al bookmaker.

## Limiti dell'estrattore

Il parser riconosce le etichette esplicite già supportate dal raccoglitore;
formati differenti e iframe su altri domini possono richiedere un adattamento.
Una lettura con zero mercati è esportabile per la diagnosi e non genera quote.
Non promette copertura di tutti i mercati Sisal o disponibilità continua.

## Prova reale del 19 settembre 2026

L'estensione è stata caricata e provata in **Chrome for Testing 153**, in un
profilo separato. Non è stata installata nel profilo Chrome personale: per
quello seguire i passaggi iniziali.

Su [Fiorentina–Napoli](https://www.sisal.it/scommesse-matchpoint/evento/calcio/serie-a/fiorentina-napoli)
la scheda STATS MATCH ha fornito **81 linee Over leggibili**; **27 quote** sono
state abbinate alle esatte linee delle previsioni precedenti e importate nel
report. Le altre 54 linee non avevano una previsione corrispondente.
Il kickoff letto è il 20 settembre alle 12:30 italiane. Il formato JSON-LD
locale viene interpretato in Europe/Rome e confrontato con squadre, data e
ora visibili: non si usa il fuso orario del computer.

La pagina Monza–Sassuolo si apre ma mostra **Nessuna Scommessa Quotata**.
Il risultato positivo riguarda il formato osservato su Fiorentina–Napoli,
non certifica la copertura di ogni campionato o formato futuro.
Le quote scadono nel suggeritore dopo 60 minuti: ripetere la raccolta per
ottenere prezzi aggiornati.

Sono stati verificati in Chrome aggiornamenti delle quote, esiti sospesi,
pausa/ripresa, esportazione JSON e svuotamento dell'archivio. I test su dati
sintetici sono separati dalle quote reali del registro.

Per rigenerare `reader.js` dopo modifiche all'estrattore comune:
`python scripts/prepara_estensione_sisal.py`, poi **Ricarica** in
`chrome://extensions` e ricaricare la pagina Sisal.

Documentazione di riferimento: [installazione locale](https://developer.chrome.com/docs/extensions/get-started/tutorial/hello-world),
[content script](https://developer.chrome.com/docs/extensions/develop/concepts/content-scripts).
