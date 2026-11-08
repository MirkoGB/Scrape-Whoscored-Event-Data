# Over: registro prospettico e simulazione senza denaro

Il report è `reports/analisi_2627_prestazioni.html`, sezione **Over · verifica economica**.
La diagnostica completa è `reports/over_2627_verifica.md`.

## Suggeritore automatico nel report HTML

Il riquadro **Suggeritore di schedina** permette di scegliere da 1 a 10 eventi,
mercato (tiri / tiri in porta, squadra / totale), campionato e data. Con
**Trova la schedina** restituisce esattamente il numero richiesto, scegliendo
la combinazione con il massimo prodotto delle probabilità. Mostra partita,
squadra o totale, linea Over, probabilità individuale e data della previsione;
**Scarica le selezioni** esporta un riepilogo leggibile con gli ID di origine.

La ricerca è esatta sul catalogo filtrato, senza limitare il pool ai primi N:
massimizza la somma dei logaritmi delle probabilità con branch-and-bound.
Si mantiene la previsione più recente di ciascun mercato e la selezione più
probabile per partita, perché tutte le selezioni di quella gara hanno gli
stessi conflitti. Sono vietate partite o squadre ripetute nella schedina.
Non vengono imposti eventi aggiuntivi se non esiste una combinazione ammissibile.

La probabilità di prenderli tutti è **uno scenario di indipendenza**, non una
probabilità congiunta validata. Sono visibili probabilità di perdere, quota di
pareggio, limiti di Fréchet a marginali date e sensibilità a −5 punti sulle
singole probabilità. Gli ultimi due non sono intervalli di confidenza.
Il criterio favorisce gli Over più bassi; non ottimizza il profitto. Le linee
devono essere effettivamente disponibili presso il bookmaker: il suggeritore
non le presenta come mercati verificati e non inventa quote o rendimento atteso.

I filtri sono indipendenti da quelli del report storico. “Tutte le date future”
può combinare giorni diversi; scegliere una data per restare nello stesso giorno.
Il catalogo è una copia statica delle previsioni, non un collegamento in diretta.
Si escludono gare già giocate, gare di oggi senza kickoff verificato, previsioni
con timestamp futuro e allenamento non anteriore alla partita. La data è quella
del dispositivo nel fuso Europe/Rome, ricontrollata al calcolo e all’esportazione.
Se il catalogo scade, si mostra **nessuna giocata**, senza riciclare gare passate.
Per aggiornarlo, eseguire `scripts/paper_over.py snapshot`,
`scripts/paper_over.py report` e `scripts/pagina_analisi_2627.py` con Python della
`.venv`. Il protocollo congelato e il confronto economico da 1 a 5 eventi
rimangono separati dal suggeritore esplorativo da 1 a 10: nessuna sua selezione
diventa automaticamente una decisione nel registro.

Verifica del motore: `node --test tests/test_suggestion_engine.cjs`.

È ora disponibile anche il raccoglitore automatico Sisal e il filtro sulle sue
quote recenti: [istruzioni e stato della verifica](quote_sisal.md). Il primo
tentativo reale è fallito per accesso al sito; il parser non è ancora convalidato
sulle pagine effettive del sito. Le osservazioni raccolte restano distinte dalle quote ammesse
al protocollo economico finché le regole di liquidazione non sono riconciliate.

Non abbiamo quote storiche reali e verificabili per le 105 partite valutate.
Le quote Como nell'Excel sono formule delle probabilità del modello e di un
margine ipotizzato. Non sono ammesse come prezzi di mercato.

## Protocollo e separazione temporale

`data/external/paper_over/protocol.json` è congelato, con hash e data. Le 105 gare
sono sviluppo/diagnosi: erano già state viste. Il test della strategia parte
dalla data `test_from`, su decisioni archiviate prima delle gare. Non si sceglie
la taglia vincente o si cambia la soglia in base ai risultati del test. Un
eventuale protocollo nuovo richiede una nuova versione e un nuovo periodo di
test, mantenendo i risultati della versione precedente.

Il campione diagnostico è anch'esso congelato, con hash, in
`data/external/paper_over/development/development_v1.json`. Aggiornare i risultati
locali non aggiunge silenziosamente gare del test futuro alla calibrazione di
sviluppo. Le prestazioni economiche crescono esclusivamente dal registro delle
decisioni e delle liquidazioni.

In assenza di indicazioni personali, i valori sono **solo virtuali**:

- 100 unità iniziali per ognuna delle cinque strategie; massimo 1 unità per data
  di gioco, per strategia. Una singola oppure una multipla da 2, 3, 4 o 5 eventi.
- Il budget è identico come tetto. In assenza di occasioni resta non impiegato:
  confrontare profitto, ROI ed esposizione effettiva, senza forzare giocate.
- Stop a 20 unità di drawdown; nessuna nuova puntata con una precedente da
  liquidare, né con capitale insufficiente.
- Soglia EV prudente 5%; marginali diminuite di 5 punti percentuali e scenario
  aggiuntivo −10 punti. **Sono stress dichiarati, non IC delle probabilità.**
- Fréchet prudente `max(0, somma(p_stressate) − N + 1)`: non richiede
  indipendenza, ma è valido solo se le marginali stressate sono limiti adeguati.
  Non protegge da errori del modello maggiori dello stress scelto.
- Il prodotto delle probabilità resta uno scenario etichettato. Niente
  selezioni della stessa partita o squadre ripetute; stesso bookmaker.
- Pool: migliori 18 selezioni per valore marginale stressato; quota corrente
  più recente per bookmaker/mercato. Non si cerca il prezzo migliore a
  posteriori. Ogni multipla richiede anche la sua quota complessiva documentata.
- Le quote devono avere meno di 60 minuti al momento della decisione. Il
  prezzo può comunque cambiare: una simulazione non prova l'eseguibilità reale.

## 1. Congelare le previsioni future

```powershell
.\.venv\Scripts\python.exe scripts/paper_over.py snapshot
```

Usa il modello di produzione e i soli risultati con data precedente a oggi.
Registra nuove previsioni per le gare dei prossimi 15 giorni, escludendo oggi
perché il calendario non certifica il kickoff. Il modello storico, le sue
regole e gli archivi del 30 agosto / 3 settembre non sono sovrascritti.

Gli snapshot sono in `data/external/paper_over/predictions/`. I parametri non
vengono ottimizzati per il profitto. I regimi prior/within-season restano quelli
esistenti. Il catalogo corrente è `reports/over_2627_catalogo_quote.csv`.

## 2. Registrare prezzi reali

Nel report scegli evento e quota, apri **Registra una quota per il test
prospettico**, inserisci bookmaker, kickoff, URL, regole e percorso di una prova
salvata (screenshot o documento). Esporta il JSON. Il file esportato è una
**bozza**, non una rilevazione già registrata.

```powershell
.\.venv\Scripts\python.exe scripts/paper_over.py quote percorso/rilevazione_over.json
```

Il comando valida i tempi, aggiunge l'orario UTC attuale, copia la prova in un
archivio per hash e salva un nuovo record. Non accetta una data di registrazione
fornita dal chiamante. Deve valere:

`pubblicazione previsione <= rilevazione quota <= acquisizione < kickoff`.

È richiesta la conferma della stessa definizione del modello: statistiche Opta,
90 minuti + recupero, linea a mezzo punto. Per altri criteri o linee intere non
si applica automaticamente questo motore. La quota Under della stessa linea,
se disponibile, permette il confronto Brier con il mercato normalizzato senza
margine: `(1/Over) / (1/Over + 1/Under)`. Non è una probabilità vera certificata.

L'inserimento delle quote ammesse al protocollo resta documentato. Il
[raccoglitore Sisal](quote_sisal.md) automatizza i tentativi di lettura e gli
abbinamenti riconoscibili, ma deve ancora essere convalidato sul sito reale.
Non confondere il mercato standard `totals` sui gol con i totali dei tiri.

I documenti restano locali; nessun upload. Hash e date impediscono riscritture
accidentali ma non costituiscono una certificazione esterna dell'anteriorità.

## 3. Documentare la quota della multipla

Registra prima le singole e copia gli ID restituiti. Un file JSON per una multipla:

```json
{
  "quote_ids": ["ID_QUOTA_1", "ID_QUOTA_2"],
  "bookmaker": "NOME_REALE",
  "odds": 0,
  "observed_at": "TIMESTAMP_ISO_CON_FUSO",
  "source_url": "URL_DELLA_SCHEDINA",
  "evidence_path": "PERCORSO_PROVA_SALVATA"
}
```

Sostituire tutti i segnaposto: `0` non è una quota valida.

```powershell
.\.venv\Scripts\python.exe scripts/paper_over.py combined percorso/multipla.json
```

Il prodotto delle singole da solo non permette di congelare una multipla:
potrebbero esistere esclusioni, limiti o prezzi diversi. Nel laboratorio HTML
è visibile solo come riferimento ipotetico, senza entrare nel rendimento.

## 4. Congelare la decisione

```powershell
.\.venv\Scripts\python.exe scripts/paper_over.py plan AAAA-MM-GG
```

Una sola decisione immutabile per data di gioco. Le cinque strategie vedono
lo stesso insieme di quote, registrate prima del piano. Nessun esito entra
nella funzione di selezione. Non si aggiungono eventi quando sono troppo pochi
o il vantaggio non passa il criterio. La decisione può essere “nessuna giocata”.

Le date devono avanzare; non si ricostruiscono schedine vincenti a posteriori.
Il registro non effettua scommesse reali e non si collega a conti di gioco.

## 5. Liquidare gli esiti documentati

JSON per ciascuna quota utilizzata:

```json
{
  "quote_id": "ID_QUOTA",
  "result": "won",
  "observed_count": 0,
  "source_url": "URL_ESITO",
  "evidence_path": "PERCORSO_PROVA_ESITO"
}
```

Inserire il conteggio effettivo e `won`, `lost` o `void`. Il conteggio viene
controllato contro la linea. La fonte di liquidazione deve essere coerente con
quella del bookmaker: i conteggi WhoScored, da soli, non provano la liquidazione.

```powershell
.\.venv\Scripts\python.exe scripts/paper_over.py settle percorso/esito.json
.\.venv\Scripts\python.exe scripts/paper_over.py report
```

Una singola annullata restituisce la puntata. Una multipla con un evento
annullato rimane **da liquidare**: non si inventa la quota ridotta, specialmente
in presenza di bonus. Serve la liquidazione complessiva documentata prima di
includerla nel profitto.

Per chiudere questo caso, dopo aver registrato gli esiti di tutte le selezioni,
creare un JSON con `decision_id`, `size`, `gross_return` (ritorno lordo nella
stessa unità virtuale della puntata), `source_url` ed `evidence_path`, quindi:

```powershell
.\.venv\Scripts\python.exe scripts/paper_over.py settle-slip percorso/liquidazione_multipla.json
```

Il comando non accetta una seconda liquidazione della stessa schedina e non
usa una quota ridotta dedotta dal modello.

## Misure e limiti

Il report distingue quote, probabilità, scenari e risultati liquidati. Riporta
profitto netto, ROI sul capitale effettivamente puntato e liquidato, frequenza
di perdite, massima serie di schedine perdenti e massimo calo dal picco.

Gli scenari Monte Carlo usano le sole schedine congelate (5.000 percorsi, seed
42): esiti giornalieri indipendenti, probabilità congiunta indipendente oppure
limite prudente stressato. Misurano sensibilità, non un rendimento osservato o
una probabilità validata di successo futuro. Nessuno scenario viene inventato
quando mancano le quote. Il resoconto parte da “nessuna giocata”.

Fonti metodologiche consultate: [snapshot e copertura delle quote storiche](https://the-odds-api.com/historical-odds-data/),
[rispetto delle regole pubblicate di liquidazione](https://www.gamblingcommission.gov.uk/licensees-and-businesses/page/settling-bets-in-accordance-with-published-rules).
