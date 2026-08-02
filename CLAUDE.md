# CLAUDE.md

Contesto di progetto per Claude Code. Il repository nasce come fork di uno
scraper WhoScored ed e' diventato un progetto di modellazione statistica.

## Obiettivo

Modello predittivo dei **tiri in porta (SoT) per squadra-partita** in Serie A,
in due strati:

1. **within-season** — tasso atteso di una squadra contro un avversario
   specifico, dai dati evento 2025-26;
2. **proiezione 2026-27 dal basso** — ricostruzione del tasso di squadra a
   partire dai contributi dei singoli giocatori e dalla rosa prevista, per il
   **Como**.

Il lavoro procede per fasi. **Alla fine di ogni fase ci si ferma e si riferisce
all'utente prima di proseguire.** Non passare alla fase successiva di propria
iniziativa.

Stato: **fasi 0-5 completate, tutti i blocchi della Fase 6 (6A-6F), e il
blocco 7A.** Dettaglio ed esiti nella sezione "Le fasi e i risultati
raggiunti" piu' sotto. Il deliverable e' `README.md`. La Fase 6 e' descritta in
`docs/prompt_fase6.md`, la Fase 7 in `docs/prompt_fase7.md`; il seguito del
lavoro e' il piano dati prodotto da 6F (`reports/phase6_piano_dati.md`), che
**richiede dati non presenti nel repository** ed e' cio' che la Fase 7 va a
prendere. Il blocco successivo da fare e' **7B**.

## Comandi

```bash
# ambiente (gia' creato)
./.venv/Scripts/python.exe -m pip install -r requirements.txt

./.venv/Scripts/python.exe -m pytest tests/ -q      # 206 test, ~8 s
./.venv/Scripts/python.exe scripts/run_phase1.py    # tabelle + audit
./.venv/Scripts/python.exe scripts/run_phase2.py    # modello + predittori (~5 min)
./.venv/Scripts/python.exe scripts/run_phase3.py    # proiezione + Monte Carlo
./.venv/Scripts/python.exe scripts/run_phase4.py    # validazione consolidata (~1 min)
./.venv/Scripts/python.exe scripts/run_phase5.py    # figure + deliverable (~2 min)
./.venv/Scripts/python.exe scripts/run_phase6a.py   # catena del livello (~1 min)
./.venv/Scripts/python.exe scripts/run_phase6b.py   # i due estimatori (~1 min)
./.venv/Scripts/python.exe scripts/run_phase6c.py   # sensibilita' a rho (~2 min)
./.venv/Scripts/python.exe scripts/run_phase6d.py   # predittori acerbi (~5 min)
./.venv/Scripts/python.exe scripts/run_phase6e.py   # calendario 26-27 (~1 min)
./.venv/Scripts/python.exe scripts/run_phase6f.py   # piano dati (~1 min)

# acquisizione WhoScored — parametrizzata su campionato e stagione
./.venv/Scripts/python.exe acquisition/whoscored/scrape_season.py --dry-run
./.venv/Scripts/python.exe acquisition/whoscored/scrape_season.py --season 2021-2022
```

`scrape_season.py` **senza argomenti scarica tutte e cinque le stagioni** di
`config.SEASONS_STORICHE`. `--dry-run` stampa bersagli, percorsi e stato di
avanzamento **senza aprire il browser e senza toccare la rete**: e' l'unico modo
di verificare la parametrizzazione finche' i termini d'uso di WhoScored non sono
accertati. Una partita gia' su disco viene saltata, mai riscaricata e mai
sovrascritta; la concatenazione dei CSV si scrive solo con `--merge`.

`run_phase6d.py` mette in cache i nove walk-forward in
`data/processed/phase6d_predittori.parquet`: senza `--force` le riesegue in
pochi secondi.

Fasi 4 e 5 riusano `walkforward_base.parquet` scritto dalla Fase 2; se manca
ricalcolano il walk-forward (~40 s in piu'). La Fase 5 ha bisogno anche di
`reports/phase2_predittori.csv`, scritto dalla Fase 2: senza, salta la figura
dei predittori invece di inventarsela.

Usare **sempre** `./.venv/Scripts/python.exe`, non `python`: il Python di
sistema non ha pyarrow e non scrive Parquet.

I test girano dalla cache Parquet e sono veloci. `run_phase1.py --force`
rilegge i 380 CSV (~20 s).

## Vincoli non negoziabili

Sono richieste esplicite dell'utente, non preferenze:

1. **Mai stimare su dati che seguono il target.** Vale per i parametri, per gli
   iperparametri (alpha, tau), per le medie mobili e per i baseline. Se un
   numero sembra troppo buono, controllare qui per primo.
   `tests/test_leakage.py` lo verifica meccanicamente.
2. **Mai allineare i numeri a un riferimento cambiando la definizione.** Se
   divergono, la divergenza e' il risultato.
3. **Nessun backtest su quote generate dal modello.** Sarebbe circolare. Il
   codice che lo faceva e' in `legacy/` con la spiegazione. Servono prezzi di
   mercato reali.
4. **Ogni scelta di pulizia dati va documentata**, mai fatta in silenzio.
5. **Limiti dichiarati accanto ai numeri**, non in fondo. Una stima che poggia
   su 300 minuti va etichettata come tale nella stessa riga.
6. **Baseline stupidi accanto a ogni metrica.** "R2 0.6" non e' un risultato
   finche' non si sa cosa fa la media semplice.

Dalla Fase 7, tre in piu', e sono il motivo per cui quella fase esiste:

7. **Mai mescolare due definizioni della stessa grandezza senza averle prima
   misurate una contro l'altra.** Un "tiro in porta" preso da una fonte diversa
   da Opta non e' la stessa grandezza finche' non e' dimostrato che lo sia. Se
   divergono, si tengono in due colonne separate: non si converte, non si
   sceglie la piu' comoda.
8. **Ogni riga scaricata porta con se' la sua provenienza**: fonte, URL, data di
   download, hash del file, e la definizione della metrica *in quella fonte*.
   Una riga senza provenienza non entra nel dataset.
9. **Ogni download e' idempotente e ripartibile.** Un file gia' scaricato e con
   hash invariato non si riscarica. Nessuna esecuzione deve poter cancellare o
   sovrascrivere dati grezzi gia' acquisiti.

## Architettura

```
sot/
  config.py        seed 42, percorsi, emivita 150 gg, valori di riferimento
  io_events.py     lettura 380 CSV -> Parquet
  shots.py         UNICA definizione di tiro in porta di tutto il repo
  minutes.py       minuti, ruoli, espulsioni, durata reale
  xg.py            xG interno cross-fitted per partita
  features.py      possesso, field tilt, PPDA, tocchi in area, distanza tiro
  aggregate.py     team_match / player_match Parquet
  model_team.py    Poisson ridge attacco/difesa/casa + decadimento
  baselines.py     4 baseline, tutti stimati solo sul passato
  walkforward.py   split per data + predittori pre-partita
  validate.py      walk-forward, MAE/bias/corr/calibrazione/Brier/affidabilita',
                   Murphy, PIT randomizzato, copertura, confronti appaiati,
                   `r` e tasso base stimati sul solo passato
  dispersion.py    NB2 condizionata a lambda
  model_player.py  Poisson gerarchico, shrinkage al ruolo
  squad_2627.py    rosa Como 2026-27 + proiezione minuti
  project_2627.py  ricomposizione, Monte Carlo, test 1o/2o tempo
  figures.py       le otto figure del README, ridisegnate da zero
  level_chain.py   catena del livello, scale di campo, compressione della ridge,
                   rho e sensibilita' del livello
  predictor_power.py  regimi di valutazione, potenza e MDE del test dei
                   predittori, molteplicita', penalita' contro adattamento
  calendar_2627.py insieme degli avversari, classifica, fattore di calendario,
                   scenari sulle promosse, limite della congestione
  data_plan.py     inventario delle domande aperte, granularita' minime,
                   simulazione sui nuovi arrivi, righe di eventi per il 6D
acquisition/       cio' che porta dati dentro il repository (Fase 7A)
  whoscored/       gli script del fork: main.py, scrape_matches.py,
                   scrape_season.py, utils.py. Sono SCRIPT, non moduli: si
                   eseguono, non si importano, e non c'e' __init__.py li' dentro
    target.py      l'eccezione: risoluzione campionato+stagione, percorsi e CLI.
                   NON importa selenium, ed e' percio' l'unica parte
                   dell'acquisizione verificabile dai test senza browser
scripts/  run_phase1..5.py, run_phase6a.py .. run_phase6f.py, tiri_in_porta.py
tests/    conftest + 15 moduli
legacy/   backtest circolare archiviato (NON riusare)
  fork/            materiale d'origine del fork, conservato per attribuzione:
                   EPV_grid.csv, linecollection.py, visuals.py, tutorial.ipynb,
                   logo.jpg, collaudo_fork_manuale.py (ex test.py in radice —
                   NON e' un test pytest, vedi legacy/README.md)
reports/  output rigenerabili
data/
  raw/             grezzo. Non si trasforma e non si sovrascrive mai.
    whoscored/ITA-serie-a/2025-2026/{events/*.csv, matches.json}
    manifest.json  provenienza di ogni file acquisito. E' l'UNICA cosa sotto
                   data/ che sta in git.
  processed/ITA-serie-a/2025-2026/*.parquet    rigenerabile
  external/quote/                              fornito a mano, provenienza da
                                               accertare (blocco 7F)
```

## Dati

380 CSV per-partita in `config.RAW_MATCH_DIR`
(`data/raw/whoscored/ITA-serie-a/2025-2026/events/`, ~1 GB, uno per `matchId`),
562.672 eventi, schema **WhoScored/Opta appiattito** da `createEventsDF` in
`acquisition/whoscored/main.py`.

**Mai scrivere un percorso a mano.** Campionato e stagione hanno un nome in un
posto solo, `sot/config.py`: `LEAGUE`, `SEASON`, `LEAGUE_CODES`, `raw_dir()`,
`processed_dir()`. La stagione e' `2025-2026`, non `2025-26` (ambiguo) ne'
`2526` (e' la forma di football-data.co.uk, cioe' la convenzione di una fonte);
il campionato e' `ITA-serie-a`, non `I1`, per la stessa ragione. I codici delle
fonti stanno in `LEAGUE_CODES` e si leggono al punto d'uso.
`tests/test_layout.py` blocca il ritorno di un percorso scritto a mano.

I tre file demo che stavano in radice — `events.csv` (una partita di Women's
Super League), `data/events.csv` (cinque partite di Liga 2022) e
`serie_a_2025_2026_events.csv` (1 GB, concatenazione dei 380) — **sono stati
cancellati dalla Fase 7A**. Erano trappole di lettura, non dati.

### Trappole che sono gia' costate tempo

- `isOwnGoal` **manca in 358 file su 380**: pandas la emette solo se in quella
  partita c'e' stato un autogol. Vale per tutte le booleane derivate da
  `satisfiedEventsTypes`. Forzarle a `False`.
- **30 `id` evento duplicati che NON sono duplicati**: ogni collisione accoppia
  un `OffsideGiven` con un evento normale di minuto e squadra diversi. Non
  deduplicare. La chiave unica e' `(matchId, teamId, eventId)`; `eventId` da
  solo no, e' numerato per squadra.
- `qualifiers` e `satisfiedEventsTypes` sono **repr Python** con apici singoli:
  serve `ast.literal_eval`, `json.loads` fallisce.
- `maxMinute` a volte e' **minore** dell'ultimo evento. Usare
  `minutes.match_duration()`, che prende il massimo fra i due.
- **I rigori non sono marcati da `situation`**, che resta nulla su tutti e 106.
  Identificarli con `penaltyScored | penaltyMissed` (unione = qualifier
  `Penalty`, e non rivela l'esito).
- `role_code = 5` nel `FormationSet` significa **"sostituto"**, non una
  posizione: i panchinari non hanno ruolo. Usare `minutes.season_roles()`.
- **85 espulsioni, ma solo 65 tolgono un uomo dal campo**: 17 sono ad
  allenatore/staff (`playerId` nullo), le altre a giocatori gia' usciti o in
  panchina.
- I nomi delle squadre **non esistono nei CSV**: solo `teamId`. Vanno presi da
  `data/serie_a_2025_2026_matches.json` incrociando `matchId` + casa/trasferta.
- **Niente xG nei dati.** Quello che usiamo e' stimato in casa
  (`sot/xg.py`), cross-fitted a 5 fold **raggruppati per partita**. Va sempre
  chiamato "xG interno", mai xG del fornitore.

## Definizione di tiro in porta

Una sola, in `sot/shots.py`. Non duplicarla: `scripts/tiri_in_porta.py` la
importa.

```
isShot AND ( (type=='SavedShot' AND NOT shotBlocked) OR (type=='Goal' AND NOT isOwnGoal) )
```

Esclude `MissedShots`, **pali** (`ShotOnPost`) e **tiri respinti da un
difensore** — WhoScored usa `SavedShot` sia per le parate sia per i blocchi,
`shotBlocked` e' il discriminante. Coincide esattamente con il flag Opta
`shotOnTarget` (3066 = 3066).

## Valori di riferimento (forniti dall'utente, in `config.py`)

Controllo di sanita' 2025-26 — **superato senza aggiustamenti**:
media 4.03 (ottenuto 4.034) · casa/trasferta 4.43/3.63 (4.432/3.637) ·
Como 5.11 (5.105) · 380 partite. Soglia 5%.

Validazione: MAE 1.69 · bias +0.01 · correlazione 0.41 · pendenza di
calibrazione 1.05 · Brier 0.211 contro 0.238 del tasso base (soglia Over 4.5).

Proiezione top-down 2026-27: 4.90 a partita, 186 in stagione, IC80% [152, 222].
Scomposizione della varianza: 65% shock di squadra, 29% campionamento, 6%
livello di campionato, 0.4% coefficienti.

## Le fasi e i risultati raggiunti

### Fase 0 — Audit dei dati ✅

380/380 partite, 562.672 eventi, 20 squadre, 2025-08-23 → 2026-05-24. Schema
WhoScored/Opta appiattito. Coordinate Opta 0-100, attacco sempre verso x = 100
(x medio dei tiri 85.2; 39 tiri su 9381 con x < 50).

**Controllo di sanita' superato senza aggiustamenti**, scarto massimo +0.19%:

| Voce | Riferimento | Ottenuto |
|---|---|---|
| media di campionato | 4.03 | 4.034 |
| casa / trasferta | 4.43 / 3.63 | 4.432 / 3.637 |
| Como | 5.11 | 5.105 (194 stagionali) |
| partite | 380 | 380 |

Le quattro definizioni candidate di SoT sono state calcolate **in parallelo**,
non per tentativi successivi finche' una combaciava. Includere i pali darebbe
4.27, fuori riferimento.

Disponibilita': xG **assente**; minuti non memorizzati ma derivabili;
sostituzioni presenti; formazioni solo nei qualifier di `FormationSet`.

Decisioni prese con l'utente: xG interno cross-fitted; rosa 2026-27 recuperata
dal web; nuovi arrivi con prior di ruolo e varianza gonfiata; backtest
circolare archiviato in `legacy/`.

### Fase 1 — Aggregazione ✅

| Tabella | Righe | |
|---|---|---|
| `team_match.parquet` | 760 | 24 colonne |
| `player_match.parquet` | 17.774 | 17 colonne |
| `shots.parquet` | 9.359 | tiri con geometria e xG |

- **Riconciliazione giocatori → squadra esatta su 760/760** partite, tolleranza
  zero, per SoT, tiri, gol e xG.
- **Minuti riconciliati esattamente su 760/760** contro
  `11 x durata - minuti persi per inferiorita' numerica`.
- **xG interno**: log-loss 0.243 contro 0.317 del tasso base, AUC 0.811, somma
  900.6 contro 900 gol (calibrazione aggregata allo 0.07%). 106 rigori
  modellati a parte, conversione 76.4%.
- Base per la Fase 3: 152 giocatori su 586 sotto i 500 minuti — 26% delle
  teste ma solo **3.1% dei minuti e 3.9% dei SoT**.

### Fase 2 — Modello within-season ✅

`log(lambda) = mu + attacco_i + difesa_j + gamma*casa`, ridge, emivita 150 gg,
alpha scelto in walk-forward. 660 righe valutate, burn-in dalla 6a giornata.

| Metrica | Riferimento | Ottenuto |
|---|---|---|
| MAE | 1.69 | 1.740 |
| bias | +0.01 | +0.034 |
| correlazione | 0.41 | 0.394 |
| pendenza di calibrazione | 1.05 | 0.965 ± 0.083 (z = -0.42) |
| Brier Over 4.5 | 0.211 vs 0.238 | 0.2127 vs 0.2374 |

**Tutti e otto i predittori da dati evento sono stati scartati.** Nessuno
supera il rumore fuori campione; il migliore (possesso) ha t = 1.42, e su 8
candidati un massimo del genere e' quanto ci si aspetta sotto l'ipotesi nulla.
`xg_per_shot` — proprio il predittore "qualita' contro volume" — **peggiora**
la previsione (-1.08). Causa: gli effetti attacco/difesa con decadimento
assorbono gia' tutto cio' che una media mobile di squadra puo' portare.
Non reintrodurli senza nuove prove. **Da leggere con la Fase 6D**, che rifa' lo
stesso test dove l'effetto attacco e' acerbo (esito uguale), misura la potenza
di entrambi i test (28% qui, 11% li') e mostra la sostituzione nei due termini
dell'obiettivo penalizzato.

**Sovradispersione**: r NB2 = 26.0, IC95% profilo [13.7, 111.8] — l'atteso 40
e' dentro l'intervallo, e siamo ben sopra la soglia d'allarme di 10.
var/media grezzo 1.363 → **condizionato a lambda 1.156**: il 57% dell'eccesso
e' variazione sistematica di lambda che il modello spiega.

**Contro i baseline** (stesse 660 righe): il modello vince su ogni metrica, ma
il margine sul migliore ("media squadra + campo") vale t = 1.86; contro la
media di squadra t = 2.82, contro la media di campionato t = 5.15. Quasi tutto
il valore sta nel sapere quanto tira la squadra e se gioca in casa.

Ratings a campo neutro: Inter 4.99, Juventus 4.97, **Como 4.34**, Lecce 2.64.
Vantaggio del campo x1.217.

### Fase 3 — Proiezione 2026-27 ✅

| | Per partita | Stagione | IC 80% |
|---|---|---|---|
| Bottom-up | 5.03 | 191 | [151, 240] |
| Top-down (riferimento) | 4.90 | 186 | [152, 222] |

Rapporto compositivo (ricambio di rosa + minuti): **+1.0%**. Chi esce vale il
15% dei minuti ma solo il 9% dei SoT; tutti i tiratori restano.

**Il metodo dal basso non si giustifica.** Due prove indipendenti. (Da leggere
con la Fase 6B: riguardano l'estimatore che **fissa il livello** dai giocatori,
non quello compositivo che la proiezione pubblica.)

1. Test 1o/2o tempo di stagione (stima su 19 partite, previsione delle 19
   successive): MAE **0.482 dal basso contro 0.416 dall'alto**, correlazione
   0.798 contro 0.839. Differenza appaiata t = -1.33.
2. Lo shock di squadra **non e' stato ridotto**: la sua varianza assoluta (512)
   resta quella ereditata dal riferimento. La quota scende dal 65% al 42.3%
   solo perche' il totale e' cresciuto del 63%. Il metodo per giocatore
   *sostituisce* lo 0.4% dei coefficienti con il 29.7% di incertezza su minuti
   (18.1%), tassi individuali (10.2%) e nuovi arrivi (1.4%). Ne segue un
   intervallo **piu' largo**, non piu' stretto.

**Causa: doppia compressione.** Lo shrinkage per giocatore verso la media di
ruolo si somma a quello gia' applicato dalla ridge di squadra. Pendenza della
regressione dal-basso su dall-alto **0.875**; correlazione fra livello della
squadra e compressione aggiuntiva **-0.466**. Squadre sopra 4.5 SoT: MAE 0.541
dall'alto contro 0.729 dal basso. Sotto 4.5: 0.348 contro 0.349, identiche.
Il danno e' concentrato **solo sulle squadre di vertice**.

**Sul Como**: la scomposizione per giocatore **peggiora** la conservativita'
invece di correggerla, ed e' il caso peggiore di tutti e venti. Nel test di
mezza stagione il Como realizza 5.316; dall'alto si prevede 4.895 (errore
-0.421), dal basso 4.359 (errore **-0.956**). Nessuna correzione arbitraria e'
stata applicata, come richiesto.

Limiti dichiarati: rosa provvisoria (mercato aperto al 1 settembre 2026);
6 nuovi arrivi di movimento senza dati = **18% dei minuti proiettati e 13% del
lambda** su sola media di ruolo; rotazione Champions e' un'assunzione non
stimabile da questi dati (variata fra 5% e 25% nel Monte Carlo).

Nico Paz vale da solo il 21% del lambda proiettato; il suo grezzo 1.39 SoT/90
diventa 0.98 in contesto neutro — e' la correzione di contesto che rende il
numero portabile fra club.

### Fase 4 — Validazione ✅

`reports/phase4_validation.md`, da `scripts/run_phase4.py`. Nessun modello
nuovo: gli stessi delle Fasi 2 e 3, tutti sulle **stesse 660 righe**.

**Il risultato principale e' che il modello si giustifica per la calibrazione,
non per l'accuratezza.** Le due cose erano state misurate separatamente e
lette come se dicessero la stessa cosa; affiancate dicono il contrario.

| modello | pendenza | z vs 1.0 | MAE | Brier |
|---|---|---|---|---|
| Poisson ridge att/dif/casa | 0.965 ± 0.083 | **-0.42** | 1.740 | 0.2129 |
| media squadra + campo | 0.785 ± 0.075 | **-2.86** | 1.785 | 0.2193 |
| media squadra | 0.747 ± 0.080 | **-3.15** | 1.812 | 0.2225 |
| media casa/trasferta | 0.955 ± 0.197 | -0.23 | 1.880 | 0.2352 |
| media campionato | non identificata | — | 1.877 | 0.2380 |

Sul MAE il modello batte il baseline migliore per t = 1.95, cioe' dentro il
rumore — come gia' in Fase 2. Sulla **pendenza** la differenza e' netta: i due
baseline informativi sono sotto 1.0 di tre e quasi tre errori standard, cioe'
danno previsioni **troppo estreme**, perche' una media campionaria non
regredisce verso il centro. La ridge corregge esattamente quello. Se in futuro
si deve difendere il modello, l'argomento e' questo, non l'accuratezza.

La pendenza di `media campionato` **non e' interpretabile**: il suo
`log(lambda)` e' quasi costante (sharpness 0.05), l'errore standard vale 1.56.
`calibration_slope` ora ritorna `nan` sul caso esattamente costante invece di
un numero uscito da una matrice singolare.

**Cosa la Fase 2 non aveva controllato, e ora si', con esito positivo:**

- **`r` e tasso base erano stimati sull'intero campione valutato.** Non entrano
  nella previsione puntuale, ma entrano nel Brier: quel Brier non era, in senso
  stretto, fuori campione. Ricostruiti riga per riga sul solo passato
  (`walkforward_r`, `walkforward_base_rate`, minimo 60 righe di storia) il
  Brier si sposta di **+0.0002** e il suo tasso base di +0.0016. La scorciatoia
  non cambiava le conclusioni — ma questo si sa **adesso** che e' misurato.
  I numeri da citare sono 0.2129 contro 0.2390.
- **Forma dell'intera distribuzione predittiva**, non solo la media: PIT
  randomizzato per conteggi, chi2 = 6.03 su 9 gdl (p = 0.737). E' il controllo
  che la pendenza di calibrazione non fa. Copertura degli intervalli 62/87/98%
  sul nominale 50/80/95%: conservativa, com'e' strutturale sui conteggi.
- **Brier su quattro soglie** (Over 2.5/3.5/4.5/5.5), non su una sola: il
  modello vince su tutte, con margine dello stesso ordine ovunque.
- **Scomposizione di Murphy**: la risoluzione del modello e' 0.0244 contro
  0.0228 del baseline migliore e 0.0005 della media di campionato;
  l'affidabilita' e' 0.0009 contro 0.0039, cioe' la ricalibrazione avrebbe
  poco da togliere al modello e parecchio ai baseline.
- **Segmentazione** per campo, terzile di lambda previsto e meta' di stagione,
  col baseline affiancato in ogni segmento. Il modello ha Brier migliore in
  **6 segmenti su 7**.

**L'unico segmento in cui perde e' il terzile alto di lambda** (+0.0031 di
Brier). E' lo stesso punto in cui la Fase 3 aveva trovato il danno maggiore
della scomposizione per giocatore, e la causa e' la stessa: la ridge e' un
ritorno alla media, e le squadre che tirano molto sono quelle che il ritorno
alla media penalizza. Il segno e' coerente fra le due fasi e non e' un caso.

Altre due letture dalle tabelle per segmento: il MAE cresce con lambda (1.50
nel terzile basso, 2.01 nell'alto) ed e' atteso, perche' su conteggi la
varianza cresce con la media; il bias e' concentrato in trasferta (+0.077
contro -0.009 in casa) **anche per il baseline** (+0.082), quindi e' una
proprieta' dei dati e non del modello.

**La `r` dei baseline e' diagnostica**: 10.5 per la media di campionato contro
26.0 del modello. Non sono dati piu' dispersi — e' la variazione di lambda che
il baseline non spiega e che finisce nella dispersione perche' non ha altro
posto dove andare. La soglia di sospetto di 10 in `dispersion.py` va letta cosi'.

**Fase 3 rivalidata con i baseline accanto**, ed emerge un fatto che il report
di Fase 3 non diceva: **"dall'alto" e' esattamente il baseline "media
squadra"** calcolato sulla prima meta' di stagione. Il metodo per giocatore
(MAE 0.482) non batte il piu' banale baseline di squadra che esista (0.416);
la media di campionato fa 0.822. Con 20 righe nulla e' significativo, ma il
segno resta contrario al metodo piu' complesso. (Vale per l'estimatore A: dalla
Fase 6B il report contiene anche la riga del compositivo, con l'avvertenza che
il confronto non ha potenza.)

`tests/test_validate.py` (21 test) verifica le metriche su dati simulati in cui
la risposta e' nota — pendenza che torna 1.0 su dati generati dal modello e si
sposta nei due sensi giusti quando si comprime o si dilata lambda; identita' di
Murphy; PIT che rifiuta una predittiva troppo stretta **mentre la pendenza di
calibrazione non se ne accorge**; e due test di leakage su `walkforward_r`, che
guastano una data di meta' stagione e pretendono che le date precedenti non
cambino e le successive si'. Validare le metriche sui risultati del progetto
sarebbe stato circolare.

### Fase 5 — Deliverable ✅

- **`README.md` riscritto** come documento del progetto: definizione di SoT,
  predittori scartati con le motivazioni, tutte le metriche di validazione,
  proiezione con intervalli, limiti. Il README del fork e' conservato come
  sezione finale di attribuzione — lo scraper resta la fonte dei dati.
- **`sot/figures.py` + `scripts/run_phase5.py`**: sette figure ridisegnate da
  zero a ogni esecuzione, piu' `phase5_ratings.csv`,
  `phase5_proiezione_como_2627.{md,csv}`.
- **`.gitignore`**: `reports/` resta escluso ma `reports/figures/*.png` no,
  altrimenti le immagini del README non esisterebbero per chi clona.

**Due difetti reali trovati mentre si rendeva tutto riproducibile.** Sono il
motivo per cui questa fase non era solo cosmetica:

1. **`tau` era scelto su due griglie diverse.** `MP.TAU_GRID` valeva
   `(2.0 … 160.0)` e `run_phase3.py` passava a `select_tau` la propria
   `(0.5 … 15.0)`. La Fase 3 sceglieva 3.0, la Fase 4 sceglieva **2.0, cioe'
   l'estremo della griglia** — che non e' una scelta, e' l'esaurimento delle
   opzioni. Ora la griglia e' una sola, in `MP.TAU_GRID`, ed e' quella che
   contiene l'ottimo al proprio interno. Con la correzione la Fase 5 riproduce
   esattamente i numeri della Fase 3 (5.03 a partita, 191 in stagione,
   IC80% [151, 240]). Due test lo bloccano in
   `tests/test_figures.py`: uno vieta griglie di tau negli script, l'altro
   verifica che l'ottimo non stia sul bordo.
2. **La griglia delle figure si accendeva quando la si spegneva.** Passare le
   proprieta' di linea insieme a `False` fa disegnare la griglia a matplotlib.

Le figure e cosa affermano — nessuna e' decorativa, ognuna corrisponde a
un'affermazione del README:

| figura | afferma |
|---|---|
| `fig1_calibrazione` | il modello e' l'unico candidato informativo compatibile con 1.0 |
| `fig2_affidabilita` | le probabilita' dichiarate reggono, fascia per fascia |
| `fig3_predittori` | nessuno degli otto predittori supera la soglia |
| `fig4_vantaggio` | sul MAE il margine sul baseline migliore tocca lo zero |
| `fig5_ratings` | forza offensiva a campo neutro, Como evidenziato |
| `fig6_proiezione` | l'intervallo dal basso e' piu' largo del riferimento |
| `fig7_giocatori` | il 21% del lambda e' Nico Paz; i nuovi arrivi sono distinti |

Convenzioni grafiche adottate (in `figures.py`, con il perche'): forma prima
del colore; **enfasi** — un elemento a colore e il resto in grigio — quando la
storia e' un solo soggetto; punti con intervallo e mai barre per le stime con
incertezza; nessun asse doppio; griglia a filo di capello e mai tratteggiata,
col tratteggio riservato alle soglie. I colori sono i primi tre slot della
palette di riferimento, gia' validati per CVD anche a coppie tutte contro
tutte; non ne sono stati inventati di nuovi. Ogni figura ha comunque la sua
tabella numerica nel README: il colore non e' mai l'unico canale.

`fig1` esclude `media campionato` perche' la sua pendenza **non e'
identificata** (lambda quasi costante, errore standard 1.56): tenerla
dilaterebbe l'asse di un fattore cinque e schiaccerebbe contro il bordo tutte
le stime che significano qualcosa. L'esclusione e' scritta nel sottotitolo
della figura, non fatta di nascosto — e un test lo verifica.

### Fase 6A — da dove viene il livello della proiezione ✅

`reports/phase6_livello.md`, da `scripts/run_phase6a.py`; il modulo e'
`sot/level_chain.py`, i test `tests/test_level_chain.py` (12). **Nessun numero
pubblicato e' cambiato**: `run_phase5.py` continua a stampare Como 4.34 e
5.03 / 191 / [151, 240].

**Il fatto centrale: il livello pubblicato non contiene il modello di
squadra.** In `monte_carlo` la riga `lam = lam / lambda_bottomup_2627 * anchor`
normalizza via il contesto, che compare anche a numeratore; si semplifica anche
nel rapporto compositivo, che e' il quoziente di due ricomposizioni con lo
stesso contesto. Moltiplicando `context_como` per 1.5 il numero pubblicato non
cambia di un bit — verificato, con un test che lo blocca. Rating, `alpha`,
attacco/difesa e vantaggio del campo decidono **come** il lambda si ripartisce
fra i giocatori, non **quanto** vale.

Le due catene, che non si toccano:

| ramo | catena |
|---|---|
| modello | 4.3433 (trasferta) ×1.2173 = 5.2872 (casa) → 4.8152 media di calendario → ×1.0185 calendario reale = 4.9041 contesto → osservato 5.1053 |
| pubblicato | **4.90 fornito** ×1.0101 rapporto = 4.9497 ancora ×1.0155 convessita' MC = 5.0263 ×38 = **191** |

- **4.90 e' `config.REF_TOPDOWN_PER_MATCH`, un valore fornito**, dichiarato
  come persistenza su 21 stagioni: quelle stagioni non sono nel repository e
  nessun modulo contiene il calcolo. **Non e' ricostruibile.** Entra come
  ancora del livello a `project_2627.py:157` e, via `REF_TOPDOWN_PI80`, anche
  nell'ampiezza dell'intervallo (righe 46, 50-51). Inventario completo in
  `LC.USI_DEL_RIFERIMENTO`, con un test che fallisce se qualcuno aggiunge un
  uso senza dichiararlo.
- **Coincidenza che ha nascosto il problema**: `como_context` vale 4.9041, cioe'
  4.90 a due decimali. Nessun legame fra le due grandezze — una e' la media
  delle 38 previsioni in campione, l'altra una previsione esterna.
- **Il +1.55% mancante e' il Monte Carlo**, mai documentato prima: tassi
  individuali +2.33%, nuovi arrivi +0.65%, minuti **−1.61%** (ridistribuire
  verso la rosa allargata toglie minuti a chi tira di piu'). Con `sources=()`
  la simulazione restituisce l'ancora esatta: se un domani non lo facesse,
  ci sarebbe un fattore in piu' non dichiarato.
- **`fig5` non e' a campo neutro: e' la trasferta.** `exp(mu + att + difesa
  media)` con `is_home` dummy 0/1. Como 4.343 trasferta / 5.287 casa / 4.815
  media di calendario. **Documentato, non corretto**: portarlo al punto medio
  geometrico darebbe 4.79, cioe' piu' vicino a 4.90 — sarebbe far tornare i
  numeri. `run_phase5.ratings_neutri` ora delega a `LC.ratings_per_campo`
  (definizione unica) e il CSV guadagna le colonne `casa` e `media_calendario`.
- **Compressione della ridge quantificata per la prima volta**: pendenza
  **0.760 ± 0.018** dei rating sui grezzi (stessa scala di campo), R² 0.99.
  La ridge minimizza l'errore predittivo, **non stima livelli senza
  distorsione**. E' la terza misura dello stesso effetto, con lo stesso segno,
  dopo il terzile alto di lambda (Fase 4) e il danno sopra 4.5 SoT (Fase 3).
- **Esito del confronto richiesto: non torna, e va detto cosi'.** Il livello
  usato de-comprime di ×1.109, la pendenza ne giustificherebbe ×1.316. Sulla
  scala di calendario: modello 4.815, usato 4.90, de-compresso 5.062, grezzo
  5.105. 4.90 sta fra il rating e il rating de-compresso, piu' vicino al primo.
  Direzione giusta, misura non verificabile con una stagione sola — e' il tema
  di 6C.

> **Trappola per le sessioni future**: cambiare `alpha`, i rating o la scala di
> `fig5` non sposta di un millimetro la proiezione pubblicata. Chi volesse
> spostarla deve toccare `REF_TOPDOWN_PER_MATCH` — o, dalla Fase 6C, `rho`, che
> e' la stessa cosa riparametrizzata — cioe' un valore fornito dall'utente, non
> un parametro del modello.

### Fase 6B — il test giusto per il bottom-up compositivo ✅

`reports/phase6_compositivo.md`, da `scripts/run_phase6b.py`; test in
`tests/test_stimatori.py` (13). **Nessun numero pubblicato e' cambiato.**

**"Dal basso" erano due stimatori con un nome solo, e il test bocciava quello
sbagliato.** Ora hanno due nomi in `project_2627.py`:

| | livello | ripartizione | dove |
|---|---|---|---|
| **A** | dai giocatori | dai giocatori | `stima_livello_dai_giocatori` |
| **B** | dall'ancora 4.90 | dai giocatori, via rapporto di rosa | `stima_compositiva` |

La proiezione pubblica **B**; il test 1o/2o tempo bocciava **A**. Le colonne di
`first_half_test` sono `topdown`, `livello_dai_giocatori` (era `bottomup`),
`compositivo`, `rapporto`.

| stimatore | MAE | RMSE | corr |
|---|---|---|---|
| nessun aggiustamento di rosa (= media squadra 1a meta') | 0.4158 | 0.561 | 0.839 |
| A — livello dai giocatori | 0.4823 | 0.616 | 0.798 |
| B — compositivo (pubblicato) | 0.4154 | 0.560 | 0.842 |
| media di campionato | 0.8216 | 1.021 | n.d. |

- **Su A il risultato negativo resta**: -0.0665 di MAE appaiata, t = -1.33.
  Non e' stato "sistemato" e non va sistemato.
- **Su B il test non dice niente**: +0.0004, t = +0.03. **Non e' una conferma,
  e' mancanza di potenza**, e adesso la mancanza e' quantificata: MDE 0.0394 di
  MAE contro un intervento medio di 0.0414. Il test vedrebbe qualcosa solo se
  ogni aggiustamento fosse perfetto e nel verso giusto.
- **Perche'**: fra due meta' della stessa stagione si libera in media il 3.9%
  dei minuti (Como **0.02%**, ed e' la squadra della proiezione) contro il
  16.9% fra un'estate e l'altra. Il test perturba l'estimatore con una frazione
  di quello su cui poi lo si usa.
- Il test **conosce la rosa del secondo tempo** (identita' e ruolo, mai tiri o
  minuti): e' l'analogo della proiezione vera, dove la rosa 26-27 e' nota, ma
  **favorisce** B. Anche cosi' favorito, non si distingue.
- `squad_2627.quote_minuti` e' ora l'unica procedura di proiezione dei minuti,
  condivisa fra la proiezione vera e il test (rotation 0 dentro la stagione).
- **Limite nuovo nel README**: la versione compositiva, cioe' quella
  pubblicata, **non e' mai stata validata**.

### Fase 6C — shrinkage entro stagione contro shrinkage fra stagioni ✅

`reports/phase6_rho.md` + `reports/figures/fig8_rho.png`, da
`scripts/run_phase6c.py`; test in `tests/test_rho.py` (9). **Nessun numero
pubblicato e' cambiato**: alla rho implicita la proiezione resta 191.

```
livello = media_lega + rho * (grezzo della squadra - media_lega)
        = 4.0342     + rho * 1.0711
```

- **rho implicito = 0.8084**, *ricavato* dalla Fase 6A (eccesso usato 0.7809
  contro eccesso grezzo 0.9661) e non ipotizzato: `livello_da_rho(0.808354)`
  restituisce 4.90 esatto, e un test lo blocca. Invariante rispetto alla scala
  di campo, verificato.
- **Ogni 0.05 di rho vale ~2 tiri in porta di stagione**: 2.09 sull'ancora
  (esatto, il livello entra per moltiplicazione), 2.15 sulla mediana simulata
  (che e' un intero e si muove a scalini). Griglia dichiarata 0.50-0.95 in
  `LC.RHO_GRID`: la proiezione va da **178 a 197**, cioe' 19 tiri = 21%
  dell'ampiezza dell'IC80% [151, 240].
- **rho non e' stimabile con una stagione sola e non e' stato stimato.** Ne'
  `alpha` (persistenza fra partite) ne' il test 1o/2o tempo (persistenza fra
  meta' di stagione, corr 0.839) sono sue stime: sono limiti superiori.
- I coefficienti dichiarati del riferimento (0.591 + 0.247 = 0.838) stanno
  vicino a 0.808, ma **non e' una conferma**: quel calcolo non esiste nel
  repository. Segnalato, non usato.
- `monte_carlo(..., livello_dall_alto=None)` e' l'unico ingresso da cui il
  livello si sposta; `None` = comportamento pubblicato.

### Fase 6D — i predittori nel regime a bassa informazione ✅

`reports/phase6_predittori.md` + `reports/phase6_predittori.csv`, da
`scripts/run_phase6d.py`; modulo `sot/predictor_power.py`, test
`tests/test_predictor_power.py` (15). **Nessun numero pubblicato e' cambiato**,
e la proiezione non e' stata toccata: il blocco riguarda solo il test dei
predittori. Il regime maturo ricalcolato riproduce `phase2_predittori.csv` con
scarto 5.6e-17 sul `t`.

**Esito: nessun predittore passa in nessun regime — ma il `t` acerbo non era in
grado di dirlo, e quello che lo dice e' un altro test.**

| regime | `team_match_idx` | righe | `t` max | tenuti | potenza |
|---|---|---|---|---|---|
| maturo | 6-38 | 660 | +1.42 | nessuno | 28% |
| acerbo | 1-8 (valutabili 4-8) | 100 | +0.88 | nessuno | **11%** |
| acerbo disgiunto | 1-5 (valutabili 4-5) | 40 | +1.45 | nessuno | 19% |

- **Il regime acerbo e' troncato**: le prime 3 partite non hanno previsione
  perche' `date_splits` pretende 30 partite di training. "Prime 8" significa in
  pratica 4-8. E acerbo e maturo **si sovrappongono** su 6-8 (60 righe su 100):
  il terzo regime esiste per avere un confronto disgiunto.
- **La potenza e' calcolata contro un'alternativa dichiarata**: l'effetto per
  riga piu' grande mai prodotto dagli otto candidati (`poss_att` nel maturo,
  +0.00579 di log-verosimiglianza per riga), con l'errore standard **di quel
  predittore** in ciascun regime — non la media degli otto, che sarebbe
  dominata dai candidati a varianza minuscola e descriverebbe un test mai
  fatto. Pavimento del test a una coda con soglia 2.0: 2.3%.
- **Ricaduta all'indietro sulla Fase 2**: anche quel test aveva **28%** di
  potenza contro il migliore dei propri effetti — che e' un altro modo di
  scrivere t = 1.42. Il "nessuno passa" resta corretto, ma la sua forza viene
  dalla piccolezza degli effetti, non dalla sensibilita' del test. Questo
  corregge la **lettura**, non il risultato.
- **Quello che conclude e' il test in campione** sulle sole righe del regime
  (coefficienti stimati guardando proprio quelle partite, il massimo favore
  possibile): minimo p = 0.093 nell'acerbo → **0.54** sugli otto candidati;
  0.034 nel disgiunto (`xgps_att`) → **0.24**. Non esiste un test piu'
  sensibile dentro questa specificazione. E' in campione, quindi un suo
  rifiuto non avrebbe dimostrato valore predittivo — vale solo come limite
  superiore, che e' la direzione in cui e' stato usato.
- **La premessa del blocco e' stata verificata, non assunta.** Per riga il
  modello stacca `media campionato` di +0.0395 nell'acerbo contro +0.1047 nel
  maturo, e sulle sole partite 4-5 fa **-0.0737**: li' e' peggio di un numero
  unico per tutti. Contro `media squadra + campo` invece sta **meglio** da
  acerbo (+0.0419 contro +0.0239), perche' con tre partite la media di squadra
  e' pessima e lo shrinkage vale molto. I due confronti misurano cose diverse e
  vanno riportati entrambi.
- **Scoperta collaterale, e non e' un bug**: nel regime maturo `d_ins_regime`
  e' negativo per 6 candidati su 8. Cio' che il modello minimizza non e' la
  verosimiglianza ma verosimiglianza pesata **piu' la penalita' ridge**:
  aggiungendo `poss_att` la penalita' scende da 10.54 a 5.91 e la
  verosimiglianza grezza peggiora. **E' la sostituzione che la Fase 2 aveva
  dedotto dal risultato fuori campione, qui visibile nei due termini**
  (`PP.penalita`, con un test che la blocca). Ne segue che `p_lr` e'
  approssimato — un rapporto di verosimiglianza penalizzato non e' un chi-2 a
  1 gdl — ma a questi valori la differenza non conta.
- `T_KEEP` e' ora **una sola**, in `predictor_power`; `run_phase2.py` la
  importa e un test verifica che non ne esista una copia.
- **`xg_per_shot` resta scartato.** Cambia segno (+0.86 acerbo contro -0.82
  maturo) ma non si avvicina alla soglia. E' il caso piu' vicino a qualcosa in
  tutto il blocco: p in campione 0.034 sulle 40 righe del disgiunto, che
  corretto sugli otto candidati vale 0.24. Riportato perche' e' il risultato.

> I risultati negativi delle Fasi 2 e 3 sono stati ottenuti correttamente e
> sono il contenuto informativo del lavoro. **Non vanno "sistemati".** Se una
> sessione futura e' tentata di reintrodurre `xg_per_shot` o di togliere lo
> shrinkage finche' il numero non torna gradevole, sta rifacendo l'errore che
> questi test servivano a escludere.

### Fase 6E — il calendario 2026-27 non e' quello 2025-26 ✅

`reports/phase6_calendario.md`, da `scripts/run_phase6e.py`; modulo
`sot/calendar_2627.py`, test `tests/test_calendario.py` (17). **Nessun numero
pubblicato e' cambiato**: `run_phase5.py` continua a stampare Como 4.34 e
5.03 / 191 / [151, 240], verificato rieseguendolo.

**Nel codice ci sono entrambe le convenzioni, e nessuna delle due entra nel
livello pubblicato.** `level_chain.ratings_per_campo` usa l'**avversario
medio** (media dei 20 coefficienti di difesa, e' `fig5`);
`project_2627.como_context` usa l'**insieme reale 2025-26** (le 38 righe vere
del Como). Ma il contesto si semplifica (Fase 6A), quindi l'insieme di
avversari entra per una terza via, mai scritta prima: **`rho` ancora il livello
al tasso grezzo del Como 2025-26**, che e' un numero ottenuto contro l'insieme
2025-26. Inventario in `CAL.INSIEMI_AVVERSARI`, con un test che verifica che le
funzioni dichiarate esistano davvero. **Il calendario 2026-27 non compare in
nessun punto del codice.**

**Lo status quo non e' "avversario medio": e' "le promosse difendono come le
retrocesse"**, e sotto quell'ipotesi il fattore di calendario vale 1 esatto —
ecco perche' non era mai stato notato. Non e' neutra: le retrocesse
(**Cremonese, Verona, Pisa**, ricavate dai gol delle righe partita, non da
fuori) hanno concesso 4.693 contro 4.034 di campionato, quindi **il trio che
esce e' gia' fra i piu' battuti e il segno dell'effetto non e' determinato**.

| difesa assunta per ciascuna promossa | fattore | stagione |
|---|---|---|
| media di campionato (estremo) | 0.974-0.981 | 186-188 |
| **come le retrocesse (status quo)** | **1.000** | **191** |
| coorte promossa 25-26 (empirico, **una coorte sola**) | 1.007-1.010 | 192-193 |
| peggiore difesa 25-26 (estremo) | 1.011-1.018 | 193-195 |

- Ogni riga e' un intervallo perche' il calcolo gira su **due scale
  affiancate**: `exp(difesa)` del modello, che la ridge comprime e che quindi
  **sottostima** il ricambio in tutti e quattro gli scenari (un test blocca il
  segno), e i tiri concessi grezzi, non compressi ma piu' rumorosi.
- `F = [somma sui 16 che restano + 3 x c_promossa] / [somma sui 19 del 25-26]`.
  Il termine di campo si semplifica: **`F` non dipende dalla scala di campo**,
  verificato.
- L'identita' della coorte promossa nel 2025-26 (Sassuolo, Pisa, Cremonese) e'
  **informazione esterna**, dichiarata in `CAL.PROMOSSE_2526` come lo e' la
  rosa: la Serie B non e' nel repository. E' una coorte sola, quindi e' un
  riferimento, non una stima.
- **Sulla scala di `rho` l'intero intervallo vale 0.20**, contro i 0.45 della
  griglia di Fase 6C e 9 tiri contro gli 89 di ampiezza dell'IC80%: il
  calendario e' la **piu' piccola** delle assunzioni non stimabili, non la piu'
  grande.
- **Non corretto, e non per prudenza: sarebbe un doppio conteggio.** 4.90 esce
  da un modello di persistenza su 21 stagioni, che contengono gia' 21 ricambi
  di neopromosse. La correzione legittima sarebbe solo lo scarto fra il trio
  2026-27 e un trio *tipico*, e con una coorte sola un trio tipico non e'
  caratterizzabile. `effetto_su_proiezione` misura il limite e **nessuno script
  della proiezione importa il modulo** — un test lo blocca sull'import.
- **Congestione infrasettimanale: limite dichiarato, non stimato**, come da
  specifica del blocco. Oggi la Champions entra **solo dai minuti**
  (`ROTATION_DEFAULT` 0.15, variato 0.05-0.25); l'effetto sul lambda a parita'
  di undici schierato non c'e' affatto. **Segno atteso negativo**, quindi su
  quell'asse la proiezione e' ottimistica. Non stimabile qui perche' il Como
  2025-26 non giocava le coppe: zero partite congestionate nel campione.
  Dichiarato in `CAL.LIMITE_CONGESTIONE`, con un test che pretende il segno e
  verifica che nessun modulo introduca un fattore di congestione. Stimarlo
  dalle altre italiane impegnate in Europa e' un'altra domanda, con un altro
  disegno: va al piano dati (6F).

### Fase 6F — piano dati, senza scaricare niente ✅

`reports/phase6_piano_dati.md` + `reports/phase6_piano_dati.csv`, da
`scripts/run_phase6f.py`; modulo `sot/data_plan.py`, test
`tests/test_data_plan.py` (24). **Niente e' stato scaricato, nessuna dipendenza
aggiunta, nessun numero pubblicato cambiato**: `run_phase5.py` continua a
stampare Como 4.34 e 5.03 / 191 / [151, 240], verificato rieseguendolo.

**Otto domande aperte, e sette si chiudono senza un solo evento grezzo.** Non
e' una comodita': segue dalla Fase 6A. Se il livello pubblicato non contiene il
modello di squadra, tutto cio' che lo sposta vive su totali di squadra per
stagione — la granularita' piu' grossolana che esista.

| | domande | granularita' minima | perche' in quest'ordine |
|---|---|---|---|
| 1 | D1 `rho`, D2 l'ancora 4.90, D5 prior neopromosse | G1, totali di squadra per stagione | toccano il **livello**, l'unica cosa che sposta la proiezione. D1 vale 19 tiri, D5 ne vale 9 |
| 2 | D3 de-compressione, D6 congestione | G2, totali di squadra per partita | 6 tiri la prima; la seconda oggi manca del tutto e ha segno noto |
| 3 | D4 validazione del compositivo | G3, tassi per 90 per giocatore | valida l'estimatore **pubblicato**: 4-5 transizioni di stagione |
| 4 | D7 i sei nuovi arrivi | G3, tassi per 90 per giocatore | il limite piu' visibile, il guadagno piu' piccolo |
| 5 | D8 i predittori da eventi | G4, eventi grezzi | l'unica che richiede eventi, la piu' cara, gia' negativa tre volte |

- **La domanda piu' grande e' la piu' economica.** `rho` sposta la proiezione
  di 19 tiri (21% dell'IC80%) e si risponde con un numero per squadra per
  stagione su 10+ stagioni: una tabella che si scrive a mano.
- **I sei nuovi arrivi valgono meno di tutti, ed e' il risultato che questo
  blocco calcola invece di assumere.** Valgono il 18.3% dei minuti proiettati e
  il 12.6% del lambda, ma avere per ciascuno un tasso individuale stringe la
  deviazione standard della proiezione dello **0.99% nel caso migliore**
  (IC80% da 89 a 87 tiri) e **di niente** all'estremo superiore dell'incertezza
  di trasferimento fra campionati, dove la riduzione va da -1.2% a +0.1%.
  `MULT_TRASFERIMENTO` e' dichiarata, non stimata, e il suo estremo `1.0` e' li'
  apposta: se la verita' e' li', la raccolta e' inutile e il conto lo dice.
- **Il centro si sposta quanto l'intervallo si stringe**, 191 → 190: e' il
  gonfiamento di Jensen dei nuovi arrivi (+0.65%, Fase 6A) che si sgonfia. Chi
  raccogliesse quei dati aspettandosi un intervallo piu' stretto otterrebbe
  soprattutto una proiezione piu' bassa. La colonna da leggere e'
  `sd_stagione`, non `ampiezza`: il totale simulato e' un intero e i suoi
  percentili si muovono a scalini da 1.
- **Il prior "gonfiato" dei nuovi arrivi non gonfia.** Vale 0.3654 (`1.5 x` la
  dispersione fra giocatori) contro il tetto `1/sqrt(2 tau)` = 0.4082 che il
  modello assegnerebbe a chi non ha esposizione: e' piu' **stretto**
  dell'ignoranza, non piu' largo. Mai scritto prima, con un test che lo blocca.
- **Un tasso individuale da un altro campionato non basta da solo.** `v_p` e'
  definito al netto del contesto di squadra, quindi servono tre cose e non una:
  minuti e SoT del giocatore, i totali per partita del suo club, e la media di
  quel campionato. **Il campionato di provenienza non e' nel repository** —
  `NEW_SIGNINGS` registra nome e ruolo e basta — e non e' stato ipotizzato; un
  test verifica che resti cosi'.
- **6D e' l'unico che vuole eventi, e ne vuole molti**: 13.5 stagioni-campionato
  per portare il test acerbo a potenza 80%, 4.0 per il maturo. In volume sono
  3.6 GB contro 4.0 GB — l'acerbo vive sulle prime giornate, quindi non servono
  stagioni intere. `t_ora` riproduce esattamente l'1.4201 di Fase 6D, che non e'
  un controllo indipendente ma conferma la parametrizzazione.
- `monte_carlo` ha un parametro nuovo, `sd_nuovi`, unico ingresso della
  simulazione; `None` = comportamento pubblicato, e un test verifica
  l'uguaglianza bit per bit. Nessuno script della proiezione importa
  `data_plan`, e un test lo blocca.

### Fase 7A — consolidare prima di moltiplicare ✅

`reports/phase7a_riorganizzazione.md` (la proposta approvata) e questa sezione.
**Nessun numero e' cambiato, ed e' stato verificato invece che assunto**:
`run_phase1.py --force` rilegge i 380 CSV dai percorsi nuovi e ridà
4.034 / 4.432 / 3.637 / 5.105 su 562.672 eventi; `run_phase5.py` ridà Como 4.34
e 5.03 / 191 / [151, 240]; i quattro report rigenerati e **tutte e otto le
figure** sono byte a byte identici alla copia presa prima del refactor.
La suite passa da 184 a 206 test in ~8 s — invariato il tempo, quindi nessun
Parquet e' stato ricalcolato.

**Il punto del blocco: la radice conteneva tre punti d'ingresso di scraping,
sei residui del fork, due `events.csv` di altri campionati e 1 GB di dati
duplicati. Moltiplicare quello per trenta stagioni-campionato era il modo
sicuro di rendere il repository ingestibile.**

- **`acquisition/whoscored/`**: `main.py`, `scrape_matches.py` (era
  `Scrape matches.py` — lo spazio nel nome costringeva a caricarlo per percorso
  con `importlib`; il rinomino ha **eliminato** l'aggiramento, non trasportato),
  `scrape_season.py` (era `scrape_serie_a_2025_2026.py`), `utils.py`.
- **`data/{raw,processed,external}`** con `ITA-serie-a/2025-2026`. **Solo
  `config.py` e' cambiato**: i nomi delle costanti sono gli stessi dalla Fase 0,
  cambia il valore. Nessun modulo fuori da `config.py` costruisce percorsi a
  mano — verificato prima del refactor, ed e' la ragione per cui i numeri non
  potevano muoversi.
- **1,02 GB cancellati**: `serie_a_2025_2026_events.csv` (concatenazione dei 380
  CSV, che restano), `data/events.csv` (**5 partite di Liga 2022** — trappola
  che nessun documento segnalava, trovata in questo blocco), `events.csv`
  (1 partita di Women's Super League).
- **`test.py` non e' finito in `tests/`**, benche' la specifica del blocco lo
  suggerisse: importa `env.main`, modulo che non esiste, apre Chrome e asserisce
  sulla Premier 2019/20. Sotto `tests/` avrebbe rotto la raccolta di pytest. E'
  in `legacy/fork/collaudo_fork_manuale.py`, che e' quello che e'.
- **`data/raw/manifest.json` e' l'unica cosa sotto `data/` che sta in git**: una
  provenienza senza storia non e' verificabile (vincolo 8).
- **`tests/test_layout.py`** (22 test): i percorsi si risolvono e contengono 380
  CSV; `2025-26`, `2526` e `2025/2026` sono rifiutati con eccezione invece di
  creare in silenzio una cartella accanto a quella giusta; nessun percorso con
  stagione scritto a mano fuori da `config.py`; il modello non scrive mai sotto
  `raw/`; la radice non riaccoglie scraper o residui del fork.

**Una cosa dichiarata e non risolta, di proposito:** **`main.py` resta 23 KB di
codice del fork** con `sys.modules["env.main"]` iniettato a mano, Selenium e
nessun test. Spostarlo lo mette al posto giusto, non lo rende affidabile: a
cinque stagioni per cinque campionati e' il collo di bottiglia, e va detto
adesso invece di scoprirlo dopo.

### Fase 7A-bis — `scrape_season.py` parametrizzato ✅

Richiesta dall'utente subito dopo 7A, e chiude il primo dei due punti lasciati
aperti sopra. **Nessun numero pubblicato e' cambiato** (verificato rieseguendo
`run_phase5.py`), e **niente e' stato scaricato**: WhoScored non e' stato
contattato una sola volta.

- **`acquisition/whoscored/target.py`**, che **non importa selenium**. E' la
  scelta strutturale del blocco: la parametrizzazione e' cosi' verificabile dai
  test senza browser e senza rete — e senza rete *deve* essere, perche' i
  termini d'uso di WhoScored restano non accertati. Se la logica stesse dentro
  lo scraper, l'unico modo di provarla sarebbe eseguirlo.
- **`Target(league, season)` immutabile** ha sostituito cinque variabili globali
  (`SEASON`, `COMPETITION_URL`, `MATCHES_DIR`, `URLS_CACHE`, `OUTPUT_FILE`).
  Erano quelle a rendere impossibile piu' di una stagione per esecuzione.
- **CLI**: `--season` (una o piu'), `--league`, `--dry-run`, `--refresh-urls`,
  `--merge`, `--sleep`. **Senza argomenti sono tutte e cinque le stagioni** di
  `config.SEASONS_STORICHE`, non quella corrente.
- **Le due forme di stagione restano separate**: `2025-2026` e' la tassonomia,
  `2025/2026` e' il menu a tendina del sito. La conversione sta in `target.py`,
  **non** in `config.py`, e va in un verso solo — un test verifica che
  `2025/2026` sia rifiutata in ingresso. Far entrare la forma della fonte nei
  nomi di cartella e' esattamente cio' che la 7A ha evitato con `ITA-serie-a`.
- **Due cambi di comportamento**, entrambi voluti: la concatenazione dei CSV
  ora si scrive **solo con `--merge`** (su cinque stagioni sarebbero cinque
  copie da 1 GB di dati gia' presenti, cioe' cio' che la 7A ha cancellato), e
  una stagione che fallisce non ferma le altre.
- **`tests/test_acquisizione_target.py`** (34 test): percorsi distinti per le
  cinque stagioni, default che coincide con `config.RAW_MATCH_DIR`, rifiuto di
  stagioni mal formate e di campionati senza codici verificati, e la guardia di
  idempotenza — un test controlla che nel sorgente `if out_path.exists()`
  preceda `to_csv`.

> **Due trappole trovate rendendolo eseguibile, nessuna delle due introdotta
> qui.** (1) `main_url` in `main.py` vale `https://1xbet.whoscored.com/`, un
> mirror di affiliazione, **non** `www.whoscored.com`: e' il dominio a cui ogni
> richiesta andrebbe, e la verifica dei termini d'uso riguarda quello.
> (2) `selenium` era in `requirements.txt` ma non installato nel `.venv` — ora
> lo e', altrimenti nemmeno `--dry-run` partiva.

---

### Acquisizione WhoScored 2021-2026 ✅

`reports/phase7_acquisizione_whoscored.md`. **1.889 CSV, 4,8 GB, copertura
99,4%**; autorizzazione WhoScored dichiarata dall'utente (§7.1 di
`regole_fantacalcio.md`). **Nessun numero delle Fasi 1-6 e' cambiato**: la
2025-26 era gia' in casa ed e' stata saltata dalla guardia di idempotenza.

| stagione | CSV / calendario |
|---|---|
| 2021-2022 | 374 / 380 |
| 2022-2023 | 375 / **381** (380 + playout) |
| 2023-2024 · 2024-2025 · 2025-2026 | 380 / 380 |

**Le trappole di questa acquisizione, che non sono nei dati ma nel loro
essere incompleti in modo non uniforme:**

- **12 partite non acquisite perche' WHOSCORED NON HA I DATI.** Accertato
  riaprendo le pagine una per una: tutte e dodici hanno `matchCentreData: null`
  e uno script di 5.079 caratteri contro il ~1 MB di una pagina buona.
  **Non e' un difetto dello scraper e non si recuperano: non ritentarle.**
  Sono registrate in `data/raw/manifest.json` sotto `assenti_alla_fonte`.
  Il messaggio `substring not found` che si legge nei log vecchi e' il parser
  di `main.py` che muore su `metadata.index('{')` con valore `null`: descrive
  l'incidente e nasconde il fatto. `acquisition/whoscored/pagina.py` ora
  distingue **dati assenti** (si dichiara) da **pagina inattesa** (si ritenta).
- **La perdita NON e' casuale rispetto alla squadra.** L'**Atalanta ne perde 6**
  (35/38 nel 2021-22 e nel 2022-23) contro un'attesa di 1.2; p = 0.054% grezzo,
  **1.1% corretto** per aver scelto il massimo di venti. Non e' una prova, e' un
  segnale da dichiarare. Il buco e' nell'archivio della fonte, non
  nell'acquisizione; perche' riguardi proprio l'Atalanta resta aperto e con
  dodici eventi non e' rispondibile.
- **I denominatori si prendono dai dati, mai assunti a 38**: 35 per l'Atalanta,
  **39 per Spezia e Verona nel 2022-23** (playout, che e' una partita vera e non
  va scartata), 38 altrove.
- Lo schema regge su tutte e cinque le stagioni (259 colonne); l'unica
  differenza e' `isOwnGoal`, cioe' la trappola gia' nota, non una divergenza.
- **Nessuna verifica di stabilita' del criterio di rilevazione fra stagioni.**
  Schema identico non implica annotazione identica: da misurare prima di
  stimare `rho` su cinque stagioni.

**Due difetti trovati solo eseguendo**, entrambi corretti con test:
(1) un banner sopra `<select id="stages">` sollevava
`ElementClickInterceptedException`, non intercettata: **costava l'intera
2022-2023**. Ha retto invece la scelta di non far fermare le altre stagioni.
(2) `report_completeness` confrontava con `!= expected`, quindi dichiarava
**incompleto** un calendario a 381 partite. Spostata in `target.py`, dove e'
verificabile senza browser — che e' il motivo per cui il difetto era arrivato
fin li'.

**`acquisition/manifest.py` + `data/raw/manifest.json`** (851 KB, in git)
chiudono il vincolo 8: fonte, URL, `matchId`, data di download reale (dal
`mtime`, non dall'istante di registrazione), byte, SHA-256, piu' la definizione
della metrica *nella fonte*. Non scarica, non tocca `raw/`, e un hash cambiato
lo segnala conservando la revisione precedente invece di assorbirla.

---

## Convenzioni

- Codice e docstring in **italiano**, come il resto del progetto.
- Coordinate Opta 0-100, tutte le squadre attaccano verso x = 100. Nessun
  ribaltamento necessario.
- Seed unico in `config.SEED`.
- I minuti si calcolano su `expandedMinute`, quindi una partita dura 94-99
  minuti, non 90. E' voluto: evita di gonfiare i tassi per 90.
- Ogni scelta non ovvia va spiegata nella docstring del modulo, con il
  **perche'**, non solo il cosa.
