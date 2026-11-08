# Rose e configurazioni delle cinque leghe

## Stato attuale — eventi e filtro aggiornati l’8 ottobre 2026

È disponibile il [report di convenienza](../reports/fantacalcio_scambi/convenienza/scambi_convenienza.md)
per tutte le cinque leghe, compresa fantamassa con gli undici moduli Mantra
confermati dall'utente. La dashboard mostra shortlist, beneficio per entrambe
le squadre, formazioni prima/dopo e scenari. Il simulatore ora **calcola anche
nuovi scambi proposti 1×1 e 2×2**, usando il medesimo modello della graduatoria.
È una **valutazione condizionata ai dati G1–G5**,
non una graduatoria aggiornata a notizie mediche o mercato.

Nuovo filtro dei consigli: **almeno +3 punti nelle prossime 5 giornate**,
minimo positivo negli scenari ordinari e vantaggio oltre due errori Monte Carlo
(solo controllo numerico, non confidenza predittiva). La dashboard permette di
cambiare soglia e richiedere vantaggio robusto anche per la controparte.

Aggiunte **26 statistiche sugli eventi**: dodici metriche in totale e per 90
minuti, più minuti e partite coperti. Comprendono tocchi in area, xT interno dei
passaggi, progressivi, ingressi nell'ultimo terzo e in area, grandi occasioni e
tiri non su rigore. Sono confrontabili anche con il 2025/26 nelle schede.
Il candidato che usa queste metriche per correggere voto e bonus è verificato
su tre stagioni: migliora due e peggiora una per entrambe le fonti, quindi
**non è attivo nei punti attesi**. Metriche descrittive e correzione predittiva
restano distinguibili; dettagli e risultati nel [protocollo](protocollo_convenienza.md).

```powershell
./.venv/Scripts/python.exe scripts/run_fantacalcio_regole.py
./.venv/Scripts/python.exe scripts/calcola_convenienza_scambi.py
./.venv/Scripts/python.exe scripts/run_fantacalcio_fase_e.py
```

La ricerca enumera 31.846 scambi singoli, valuta in screening 4.397 doppi
preselezionati e approfondisce 89 operazioni negli scenari finali. I doppi
non sono esaustivi. Il guadagno confronta il contributo schierato prima/dopo
su cinque giornate, inclusi sostituzioni, difesa e capitano. Le previsioni
individuali sono ricalibrate separatamente per Redazione e Statistico.
Il [protocollo](protocollo_convenienza.md) specifica politica di formazione,
limiti, campioni separati e stress di indisponibilità.

`regole_in_revisione.json` è ora usato **da questo calcolo condizionato**:
contiene le precisazioni confermate. Il precedente `leghe.json` e gli output
storici A–D rimangono conservati, con i loro stati originari. Le sezioni sotto
descrivono quei passaggi: le indicazioni di motore o shortlist assenti sono
superate dal presente aggiornamento, non descrivono il nuovo report.

Restano aperti: categorie osservate del Quality Assist (ora scenari +0,5/+1/+1,5),
36 giocatori senza previsione, aggiornamento delle disponibilità, gestione
speciale di s.v./voti politici e regole amministrative su crediti/reintegri.
In fantazavomerda va distinto il numero esatto dal limite massimo di 29.
Il ranking non ha un proprio backtest storico; i test individuali della fase C
non ne dimostrano l'accuratezza. C/D sono quindi operative nel perimetro
condizionato documentato, non concluse in ogni componente del piano.

Output: `reports/fantacalcio_scambi/convenienza/risultati.json`, file per lega,
report Markdown e snapshot con hash di dati, regole e codice. La generazione
della dashboard rifiuta risultati obsoleti o diversi dallo snapshot.

Verifica del motore: `tests/test_fantacalcio_convenienza.py`; verifica di
integrazione e identità dei risultati tra graduatoria, simulatore ed export:
`tests/check_fantacalcio_dashboard_browser.py`.

### Scambi proposti e statistiche estese

In **Simulatore**, scegliere controparte e giocatori ceduti/ricevuti, poi
**Calcola la convenienza**. Il calcolo avviene nel browser, funziona anche
offline e non modifica le rose originali. La selezione resta modificabile
durante il calcolo; un risultato relativo a una selezione precedente non
viene mostrato dopo un cambio di giocatori o lega.

Risultato: guadagno delle due squadre su cinque giornate, scenari di impiego
e assist, stress di indisponibilità, formazioni e scomposizione in titolari,
riserve, difesa e capitano. Mostra anche copertura media dell'undici, frequenza
simulata di undici voti e numero di moduli schierabili. Queste frequenze sono
diagnostiche del modello, non probabilità calibrate.

Le schede e il confronto dei giocatori selezionati espongono **65 statistiche
osservate** in cinque gruppi: impiego, voti/regolarità, bonus/malus, tiri,
pericolosità e progressione.
Includono mediana e dispersione del voto, sufficienze, tassi per 90 minuti,
rigori, cartellini e porte inviolate. Si può confrontare G1–G5 con il 2025/26;
fonte voto, finestre e denominatori rimangono espliciti. Le previsioni di lega
sono mostrate separatamente. La fonte Statistico è applicata dove prevista.

I giocatori scambiati senza previsione e le violazioni dei vincoli espliciti
bloccano il giudizio numerico, con motivazione; nessuno zero viene inventato.
Non sono ancora abilitati 2×1, reintegri o trasferimenti di crediti.

`convenienza.js` replica il motore Python con assegnamento e generatore casuale
deterministici condivisi. I parametri pubblicati usano distribuzioni riutilizzate
senza arrotondamenti. Per verificare la parità numerica su tutte le 89 operazioni:

```powershell
node tests/check_fantacalcio_convenienza.cjs
```

Verifiche dell'estensione eventi: **51 test Python**, **89 scambi** con parità
numerica Python/JavaScript entro 1e-7, **123 casi strutturali**, **45 operazioni
invalide respinte** e **74 controlli browser**. Questi verificano il software,
non dimostrano l'accuratezza delle raccomandazioni future. Il filtro lascia
14 proposte (3/3/3/3/2 nelle cinque leghe); una sola di queste mantiene vantaggio
positivo per entrambe le squadre in tutti gli scenari ordinari.

## Cronologia delle fasi e degli snapshot precedenti

La Fase A importa gli XLSX originali, conserva provenienza e costi, assegna
gli ID Fantacalcio dal listone 2026/27 e collega gli ID WhoScored disponibili.
Non valuta ancora gli scambi.

```powershell
./.venv/Scripts/python.exe scripts/run_fantacalcio_fase_a.py
```

Il comando è locale. Se manca il listone, acquisirlo esplicitamente:

```powershell
./.venv/Scripts/python.exe -m acquisition.fantacalcio.scrape_quote --season 2026-2027
```

`audit_fantacalcio_rose.py` rimane un alias del comando consolidato. Tenere un
solo XLSX attivo per lega: se ce ne sono più di uno il comando segnala il
conflitto e non sceglie silenziosamente quale usare. I fogli vengono individuati
per nome e relationship XLSX, non per ordine nel file ZIP.

## Configurazione

`leghe.json` contiene cinque configurazioni indipendenti. Le dichiarazioni
dell'utente restano distinte dalle regole complete utilizzabili nei calcoli.
`null` significa non ancora specificato, mai zero o regola standard.

Registrato il 6 ottobre 2026:

| Media difesa | fantagas / fantamassa / fantaonlyfans | fantaunipd | fantazavomerda |
|---|---:|---:|---:|
| sotto 5,50 | da specificare | da specificare | −1,5 |
| 5,50–<5,75 | da specificare | da specificare | −1 |
| 5,75–<6,00 | da specificare | da specificare | 0 |
| 6,00–<6,25 | +1 | +1 | 0 |
| 6,25–<6,50 | +1 | +1,5 | +1 |
| 6,50–<6,75 | +3 | +2 | +2 |
| 6,75–<7,00 | +3 | +2,5 | +3 |
| 7,00–<7,25 | +6 | +3 | +3,5 |
| 7,25–<7,50 | +6 | +4 | +3,5 |
| da 7,50 | +6 | +5 | +3,5 |

Convenzione esplicita: limite inferiore incluso, superiore escluso; ultima
fascia aperta verso l'alto. Le fasce finite hanno ampiezza 0,25, come indicato
dall'utente. Capitano attivo in fantagas, fantamassa e fantaonlyfans; formula
non ancora comunicata. Per le altre due leghe non è stato specificato.

Restano da completare formato Classic/Mantra, fonte voto, moduli, vincoli rosa,
bonus/malus ordinari, criteri del modificatore (composizione della media,
attivazione e s.v.), sostituzioni, scambi e crediti. La stagione 2026/27 è
quella di lavoro; `stagione_confermata` distingue l'ipotesi dalla conferma.
`regole_confermate` non viene attivato dall'importatore.

Per ogni regola facoltativa assente usare una dichiarazione esplicita
`{"attivo": false}`. Per una regola attiva indicare tutti i parametri,
senza lasciare valori nulli. `sot.rose.require_rules()` impedisce l'uso dei
regolamenti incompleti. È un controllo di completezza, non sostituisce la
validazione matematica del futuro motore di punteggio.

## Identità

`alias_giocatori.json` conserva solo corrispondenze verificate, qualora servano.
Ogni voce richiede `stagione`, `nome_export`, `giocatore_id_fc`, `fonte` e
`motivo`; può includere `playerId_ws`. Non accetta ID non presenti nelle fonti.
Al momento tutti i nomi delle rose trovano l'ID Fantacalcio senza alias manuali.

WhoScored è collegato tramite ponte storico per ID o corrispondenza univoca
di nome, iniziali e club corrente. Portieri e giocatori di movimento non
vengono confusi anche se hanno lo stesso cognome. Ambiguità, conflitti e
assenze di copertura restano espliciti; un'assenza non viene trasformata in
zero minuti. I ruoli sono quelli del listone corrente, non colori XLSX o
posizioni tattiche WhoScored.

## Output

I risultati vengono generati in `reports/fantacalcio_scambi/`:

- `fase_a.md`: stato della fase e dati mancanti.
- `rose_normalizzate.csv`: 46 rose, ID, ruoli, costi, cella e hash dell'export.
- `rose_per_lega.json`: rose raggruppate per lega e squadra.
- `identita_giocatori.csv` e `.json`: ID, metodo di collegamento e validità stagionale.
- `identita_da_verificare.csv`: collegamenti che richiedono ancora verifica.
- `listone_2026_2027.csv`: copia elaborata separata dallo storico.
- `audit.json`: controlli, configurazioni, hash delle sorgenti e del codice.
- `snapshots/`: versioni conservate per ogni insieme di input e codice.

Gli XLSX, il grezzo acquisito e le tabelle storiche non vengono riscritti.
Un nuovo aggiornamento del listone deve avere uno snapshot grezzo distinto:
la cache attuale non si sovrascrive implicitamente.

## Fase B — Voti G1–G5 e schede comparative

Implementata il 6 ottobre 2026. Il blocco descrittivo confronta le giornate
1–5 del 2026/27 (cutoff statistico 20 settembre) con l'intero 2025/26.
Le rose e il listone restano quelli correnti alla raccolta: non è un backtest.

Acquisizione esplicita, ripartibile, senza sovrascrivere i grezzi:

```powershell
./.venv/Scripts/python.exe scripts/acquisisci_fonti_fase_b.py
```

Rigenerazione locale dopo la Fase A:

```powershell
./.venv/Scripts/python.exe scripts/run_fantacalcio_fase_b.py
```

Risultato: **50 partite**, **1.590 righe giocatore**, 100 righe allenatore
escluse dalle medie, nessuno scarto nella ricostruzione del FV Redazione.
**384 schede** coprono tutte le rose: 348 hanno righe FC correnti, 367
osservazioni WS correnti, 58 anche storico estero sul medesimo ID verificato.
Lo storico è disponibile in Serie A per 281 giocatori, solo all'estero per 41;
per 62 rimane non disponibile, senza stime sostitutive o zeri inventati.

Output in `reports/fantacalcio_scambi/`:

- [fase_b.md](../reports/fantacalcio_scambi/fase_b.md): indice con le cinque
  rose dell'utente, link a tutte le schede, metodo e limiti.
- `schede/<id_fc>.md`: scheda leggibile di ciascun giocatore, impiego,
  voto e FM della fonte, bonus/malus, tiri/SoT, totali e tassi con denominatori,
  confronto dei club e dei ruoli Classic/Mantra, contesto del club e G6–G10.
- `schede_comparative.json` e `.csv`: confronto elaborabile; JSON conserva
  anche appartenenze alle leghe, campionati esteri separati e calendario.
- `voti_2026_2027_g1_g5.parquet` e `.csv`: tre scale, bonus, s.v. e provenienza.
- `partite_g1_g5_verificate.csv`: join uno-a-uno FC/WS con giornata ufficiale,
  date effettive e risultati verificati. I risultati includono le autoreti,
  diversamente dai gol da tiro di `team_match`.
- `audit_fase_b.json` e `snapshots/fase_b_<hash>.json`: hash delle fonti e
  del codice, copertura per campionato, schede e dati congelati dello snapshot.

Il calendario ufficiale è trascritto in `calendario_ufficiale_2026_2027.csv`,
con documenti e data di verifica in `calendario_fonti.json`. G1–G5 non sono
dedotte prendendo le prime cinque partite per squadra. G6–G10 sono il
programma ufficiale verificato al 6 ottobre, da aggiornare esplicitamente
se cambia. Le statistiche restano congelate a G5.

Voto base, FV della fonte e FV di lega sono distinti: quello di lega rimane
nullo finché i regolamenti non sono completi. La scala Redazione nelle
schede è descrittiva, non conferma il provider delle singole leghe.
Gli xG sono interni, con `xg_fit` conservato: nessun delta tra fit diversi
senza validazione; xA provider non disponibile. Nessuna notizia su infortuni
o gerarchie è stata acquisita in questo blocco.

Le schede descrittive non assegnano un valore di scambio. Le stime del
successivo blocco C sono separate, come descritto sotto.

## Fase C — Stime dopo G5 e valore schierabile

Il 6 ottobre 2026 è stata implementata la parte **indipendente dai regolamenti**:
348 giocatori con stime sulla scala Redazione della fonte, su 384 schede.
I 36 senza righe FC G1–G5 restano fuori dal perimetro validato, con previsione
nulla (non zero). Gli orizzonti sono G6–G10, G6–G13 e G6–G38.

```powershell
./.venv/Scripts/python.exe scripts/run_fantacalcio_fase_c.py
```

Il [protocollo](protocollo_fase_c.md) è stato scritto prima del confronto.
Separazione delle componenti: probabilità media di ricevere voto, voto
condizionato e bonus del provider condizionato. Tre confronti: storico,
recente e combinazione regolarizzata; pesi calibrati su sole stagioni concluse.
Le prove su 2023/24, 2024/25 e 2025/26 usano universi e ruoli osservati a G5,
senza quotazioni o ruoli futuri. Nessun modello estero viene tradotto in voti.

| Orizzonte | MAE punti storico | MAE recente | MAE combinato |
|---|---:|---:|---:|
| 5 giornate | 9,87 | 8,48 | 8,25 |
| 8 giornate | 14,73 | 13,01 | 12,21 |
| 33 giornate | 52,60 | 53,22 | 44,97 |

La combinazione migliora entrambi i baseline anche in ciascuna delle tre
stagioni, superando il criterio operativo prefissato. Non è una prova del
beneficio causale di uno scambio. Gli intervalli empirici nominali 80% sui
punti hanno copertura 78,67%, 78,22% e 76,67% nel test 2025/26: non sono
garanzie sul singolo giocatore. Gli scenari di impiego ±20% sono separati.

Output in `reports/fantacalcio_scambi/`:

- [fase_c.md](../reports/fantacalcio_scambi/fase_c.md): risultati, limiti,
  riepilogo delle cinque rose e link alle 384 schede di valutazione.
- `valutazioni/<id_fc>.md`: stime, intervalli e sensibilità all'impiego.
- `valutazioni_giocatori.json` e `.csv`: valori separati dalla Fase B.
- `fase_c_backtest.csv`, `fase_c_metriche.csv`, `fase_c_metriche_per_ruolo.csv`
  e `fase_c_copertura_intervalli.csv`: previsioni storiche, errori, Brier delle
  presenze e copertura osservata.
- `audit_fase_c.json`: fonti, hash, selezioni dei pesi e finestre di training;
  `snapshots/fase_c_<hash>.json` conserva il risultato e il backtest.
- `valutazioni_per_lega.json`: appartenenze separate e campi ancora bloccati.

**La Fase C non è ancora chiusa per lega.** Mancano regole per calcolare
formazioni legali, sostituzioni, modificatori, punteggio del capitano e valore
marginale rispetto al sostituto della stessa rosa. Questi risultati rimangono
nulli: i punti del provider non vengono chiamati punti schierabili.
Disponibilità medica e gerarchie aggiornate non sono stimate dalle assenze.
Le stime non correggono per avversario e non producono un modello dei minuti.
La parte strutturale della Fase D è stata successivamente implementata,
come descritto sotto; la graduatoria dipende ancora da questi calcoli.

## Fase D — Catalogo e simulazioni di scambio

Implementati il 6 ottobre 2026 il catalogo completo delle operazioni 1×1 e
2×2 e il simulatore strutturale per le cinque leghe. Le 46 rose comprendono
**41 controparti** reali della squadra utente: **31.846** combinazioni 1×1 e
**6.188.345** combinazioni 2×2. Sono operazioni potenziali, non scambi
convenienti o già verificati rispetto al regolamento.

```powershell
./.venv/Scripts/python.exe scripts/run_fantacalcio_fase_d.py
```

Il catalogo contiene tutti i pacchetti singoli e doppi per squadra. Il loro
prodotto cartesiano ricostruisce ogni scambio, senza materializzare milioni
di righe ripetute. `sot.rose_scambi.iter_candidates` offre la stessa
enumerazione in modo incrementale, senza tagli o filtri impliciti di ruolo.
I giocatori senza stima restano presenti e segnalati.

Per una simulazione manuale aggiungere `--lega`, `--controparte`, `--cedi`
e `--ricevi`, usando uno o due ID Fantacalcio per lato dal catalogo. Senza
pacchetti si controlla lo scambio nullo; esempio eseguibile:

```powershell
./.venv/Scripts/python.exe scripts/run_fantacalcio_fase_d.py --lega fantagas2020 --controparte "AS RosaSpina"
```

Il simulatore verifica le proprietà nella stessa lega, la reversibilità e
la conservazione del numero di giocatori. Mostra ID delle rose prima/dopo,
conteggi dei ruoli e copertura delle stime per entrambe le squadre. Gli
XLSX e le assegnazioni originali restano invariati. I costi rimangono quelli
dell'export di origine: non sono prezzi di scambio o crediti trasferiti.
Per lo scambio nullo il beneficio è zero per identità; negli altri casi il
beneficio rimane nullo finché non esiste una valutazione schierabile.

Output in `reports/fantacalcio_scambi/`:

- [fase_d.md](../reports/fantacalcio_scambi/fase_d.md): stato delle cinque
  leghe, copertura delle rose dell'utente e blocchi residui.
- `catalogo_scambi.json`: pacchetti completi, ID, ruoli e proprietari.
- `fase_d_controparti.csv`: conteggi esatti per controparte e formato,
  numero di combinazioni con stime individuali e firme Classic invariate.
- `profili_rose_fase_d.json`: tutte le rose con ruoli e dati mancanti.
- `scambi_per_lega.json`: stato esplicito e `shortlist: null` per ogni lega.
- `esposizione_mie_rose.json`: concentrazione degli stessi giocatori nelle
  leghe dell'utente, senza aggregare i costi di leghe diverse.
- `simulazioni/`: report Markdown/JSON delle operazioni richieste.
- `audit_fase_d.json` e `snapshots/fase_d_<hash>.json`: integrità delle
  sorgenti A/B/C, catalogo e risultati conservati per snapshot.

**La Fase D resta parziale.** La graduatoria, il beneficio per entrambe le
squadre, le formazioni ottimali, la robustezza e le alternative meno costose
richiedono i regolamenti completi e il valutatore schierabile della Fase C.
Una rosa che mantiene gli stessi ruoli Classic non è automaticamente legale,
e le etichette Mantra non vengono interpretate senza moduli e vincoli.
Compilare le regole non attiva da solo un motore di punteggio ancora assente.
La shortlist nulla significa valutazione non eseguita, non «nessuno scambio
convincente». Operazioni 2×1 non abilitate senza regole e reintegri espliciti.

## Fase E — Dashboard operativa

Implementata il 7 ottobre 2026 su snapshot congelati delle fasi A–D.
Dashboard pubblicata con accesso privato:
https://fantacalcio-rose-scambi.daniela-marzan622457.chatgpt.site

Per generare o aggiornare esplicitamente la versione locale:

```powershell
./.venv/Scripts/python.exe scripts/run_fantacalcio_fase_e.py
```

Aprire [la dashboard locale](../reports/fantacalcio_dashboard_site/dist/index.html).
Funziona anche senza server e senza dipendenze esterne; mantenere i file della
cartella `dist` insieme. Sorgenti in `fantacalcio_rose/dashboard/`.

- Panoramica delle cinque leghe, copertura della propria rosa ed esposizione
  dei giocatori condivisi fra le proprie squadre.
- Rose proprie e avversarie con ricerca, filtri ruolo/copertura/minuti,
  ordinamento per rendimento e dettagli giocatore con confronto 2025/26.
- Stime individuali G6–G10, G6–G13 e G6–G38 con intervalli e limiti; dati
  mancanti distinti da zero, medie con denominatori e storico estero separato.
- Catalogo per controparte; stato esplicito «valutazione non ancora eseguita»
  per gli scambi consigliati, senza ranking basato su somme del provider.
- Simulatore strutturale 1×1/2×2, rose e ruoli prima/dopo, controlli di proprietà,
  reversibilità ed esportazione JSON con identificativi degli snapshot.
- Fonti, regole già registrate e bozze per lega conservate nel browser ed
  esportabili. Le bozze **non applicano** regole o punteggi automaticamente.

Il simulatore browser è un adattamento del contratto di `sot.rose_scambi`:
123 casi (nullo/1×1/2×2 per tutte le 41 controparti) producono risultati
identici, compreso l'ID dello scambio; 45 operazioni invalide sono respinte.
È obbligatorio mantenere questa parità quando cambia il motore Python.
Formazioni ottimali, legalità regolamentare e benefici sportivi rimangono
nulli. Non sono stati acquisiti aggiornamenti medici.

La generazione verifica la catena A–D e gli hash dei file effettivamente letti,
anche usando `--source`. Produce `audit_fase_e.json`, vettori di parità in
`fase_e_fixtures.json` e snapshot conservati in `snapshots/fase_e_<hash>.json`.
Non modifica export, regole, voti o risultati A–D.

Verifiche eseguite: 123 simulazioni di parità, 45 casi invalidi, tre test di
integrità e 41 controlli browser desktop/mobile (filtri, cambi lega, dettagli,
orizzonti, scambi, esportazioni, focus tastiera e assenza di overflow pagina).

```powershell
./.venv/Scripts/python.exe -m pytest tests/test_fantacalcio_fase_e.py -q
node tests/check_fantacalcio_dashboard_engine.cjs
./.venv/Scripts/python.exe tests/check_fantacalcio_dashboard_browser.py
```

Il test browser usa Selenium e i binari Chrome/ChromeDriver già presenti in
`reports/_chrome_for_extension_test/`; screenshot e risultati sono in
`reports/fantacalcio_scambi/qa_fase_e/`.

Per completare **C e D**, fornire i regolamenti completi o le impostazioni
delle leghe seguendo [l'elenco e il modello di risposta](regole_da_completare.md).
Le fasce difensive già raccolte sono riportate lì. Dopo la conferma resta da
implementare il motore schierabile e poi la graduatoria, non soltanto compilare
la configurazione. La verifica finale F e gli aggiornamenti restano aperti
per le parti dipendenti da C/D.

## Regole ricevute — verifica del 7 ottobre 2026

Acquisite le risposte nel file compilato dall'utente. La versione strutturata
è [regole_in_revisione.json](regole_in_revisione.json); il
[riepilogo delle conferme e discrepanze](verifica_regole.md) distingue le
informazioni certe dalle regole ancora ambigue. Per ripetere il controllo:

```powershell
./.venv/Scripts/python.exe scripts/run_fantacalcio_regole.py
```

Confermati stagione 2026/27, quattro leghe Classic, `fantamassa21` Mantra,
voti Statistico per `fantazavomerda` e Redazione per le altre. Registrati
vincoli di rosa, assenza del capitano in fantaunipd/fantazavo e restrizione
Pc/A in fantamassa, senza inventare formule o valori standard.

Le 26 rose delle tre leghe con vincoli 3P–8D–8C–6A sono coerenti. Il limite
Mantra è stato corretto dall'utente in **massimo 35 giocatori**: tutte le otto
rose, incluse quelle da 32 giocatori, lo rispettano. Due rose fantazavo hanno
27 e 26 giocatori contro i 29 dichiarati. Servono chiarimenti sul significato
del limite. I bonus/malus sono stati successivamente comunicati e registrati
in `precisazioni_regole.json`. Anche la formula del capitano è confermata:
modificatore aggiuntivo pari a voto base − 6, dove il capitano è attivo,
conservando l'esclusione dei ruoli Pc/A in fantamassa.

`regole_in_revisione.json` **non è una configurazione attiva**. `leghe.json`,
snapshot e dashboard pubblicata mantengono la configurazione precedente,
finché i punti aperti non vengono risolti e la catena non viene rigenerata.
Le stime attuali Redazione non possono essere rietichettate Statistico:
fantazavomerda richiederà calibrazione separata prima di completare C/D.

Precisazioni successive registrate in `precisazioni_regole.json`: difesa zero
sotto 6 nelle prime quattro leghe, migliori quattro voti del gruppo
portiere/difensori, nessun modificatore con meno di quattro voti utili dopo
i cambi. Panchina 1P–2D–2C–2A per fantagas2020 e fantaonlyfans, libera nelle
altre tre. Sostituzioni nello stesso ruolo anche in Mantra, senza adattamenti
e senza tetto numerico ai cambi, entro la disponibilità della panchina.
Precedenza fra riserve dello stesso ruolo ancora da specificare.
La versione in revisione e il report sono stati rigenerati; 18 test di
acquisizione e controllo delle regole passano.

Bonus/malus registrati per tutte le leghe, con rigori +2/−2 per fantazavomerda
e +3/−3 nelle altre. Quality Assist (+0,5/+1/+1,5) in fantamassa, fantaunipd e
fantazavomerda; assist fisso +1 in fantagas2020 e fantaonlyfans. La tabella voti
G1–G5 importata contiene solo il conteggio aggregato degli assist: le fasce
Quality richiedono integrazione dei dati correnti e storici, senza sostituirle
con un bonus fisso. La configurazione in revisione conserva questa distinzione.
