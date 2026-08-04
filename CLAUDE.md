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

Stato: **fasi 0-5 completate, tutti i blocchi della Fase 6 (6A-6F), il blocco
7A, l'acquisizione WhoScored 2021-2026, la verifica di stabilita' del criterio
di rilevazione, il Blocco 0 della Fase 8 (ricognizione), l'acquisizione dei
voti fantacalcio 2021-2026 e i blocchi E0, E1, E2 (con la sua coda) ed E3 della
Fase 9.** Dettaglio ed esiti nella sezione "Le fasi e i
risultati raggiunti" piu' sotto. Il deliverable e' `README.md`. La Fase 6 e'
descritta in `docs/prompt_fase6.md`, la Fase 7 in `docs/prompt_fase7.md`, la
Fase 9 in `docs/prompt_fase9.md` (che contiene anche la specifica di E2, dall'utente
il 2026-08-04); il seguito del lavoro e' il piano dati
prodotto da 6F (`reports/phase6_piano_dati.md`), che **richiede dati non
presenti nel repository** ed e' cio' che la Fase 7 va a prendere.

### Due rami aperti, non una coda

Decisione dell'utente del 2026-08-03: il lavoro **non e' una fila**. Ci sono due
rami che non si toccano, e si sceglie a ogni giro quale blocco fare.

| ramo | bersaglio | prossimo blocco | fonte |
|---|---|---|---|
| **Fase 7** (7B → 7C → 7D) | `rho` e l'ancora 4.90, cioe' il **livello** della proiezione SoT di squadra (D1, D2, D5) | **7B** | football-data.co.uk, **da acquisire** |
| **Fase 9** (E0 → E1 → E2 → E3 → E4) | punti stagionali del **giocatore**: impiego, portieri, modificatore | **E4** (E0 ✅, E1 ✅, E2 ✅, E3 ✅) | WhoScored + voti + listoni, **gia' in casa** |

**Nessuno dei due produce ingressi dell'altro**, ed e' il motivo per cui sono
paralleli: 7B porta una colonna SoT a granularita' squadra-partita con una
definizione **non Opta**, che il vincolo 7 obbliga a tenere separata; la Fase 9
lavora su player-match Opta, gia' verificati identici al flag nativo su tutte e
cinque le stagioni. Tirare la fonte tabellare dentro il ramo giocatore
aprirebbe l'obbligo di riconciliazione di 7C senza aggiungere capacita'.

Le tre direzioni **G1-G3** in fondo a `docs/prompt_fase9.md` (risultato, altri
campionati, scouting) **non sono aperte**: vanno rimesse in fila e se ne sceglie
una, non prima che la Fase 9 abbia dei blocchi chiusi. **Erano quattro**: la
direzione su `rho` e l'ancora 4.90 e' stata tolta dalla Fase 9 il 2026-08-03
perche' **e' la Fase 7**, e tenerla in due posti sarebbe stato un modo di fare
la stessa domanda due volte — con la differenza che di qua i dati per
rispondere non ci sono.

**Della Fase 8 sono chiusi**: i voti (D1), le quotazioni (D2), la giornata di
campionato (D6), l'aggancio fra le due fonti, la regola dell'80' misurata, il
modello per l'asta validato su quattro transizioni, **il modificatore di difesa**
e una **lista d'asta provvisoria** su listone surrogato. **Tutte e cinque le
decisioni di §0 sono prese** (`sot/lega.py`). Restano aperte le domande non
bloccanti D7-D9 del Blocco 0. Nomenclatura adottata: **Fase 8** come contenitore, blocchi
`T1-T5` (squadra), `P1-P9` (giocatore), `F1-F5` (fantacalcio) — dove `8A = P2`
(voto base) e `8D = F3` (modificatore).

## Comandi

```bash
# ambiente (gia' creato)
./.venv/Scripts/python.exe -m pip install -r requirements.txt

./.venv/Scripts/python.exe -m pytest tests/ -q      # 570 test, ~142 s
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

# stabilita' del criterio di rilevazione fra le cinque stagioni (~3 min; con
# --force rilegge i 1.889 CSV, ~90 s in piu'). Non tocca la rete.
./.venv/Scripts/python.exe scripts/run_phase7_stabilita.py

# Fase 8 — Blocco 0, ricognizione. ~5 s da cache; con --force rilegge i 1.889
# CSV con TUTTE le 259 colonne (~3 min). Non tocca la rete.
./.venv/Scripts/python.exe scripts/run_blocco0.py

# Voti fantacalcio: dai 190 HTML gia' su disco ai due Parquet, al manifest e al
# report (~20 s). NON tocca la rete.
./.venv/Scripts/python.exe scripts/run_voti_fantacalcio.py

# Aggancio delle due fonti + misura della regola dell'80' (~1 min; --force
# ricalcola i minuti dai 380 CSV, ~40 s in piu'). NON tocca la rete.
./.venv/Scripts/python.exe scripts/run_aggancio.py

# Modello per l'asta: fantavoto di lega, walk-forward su 4 transizioni,
# 4 baseline, report (~30 s). NON tocca la rete.
./.venv/Scripts/python.exe scripts/run_modello_asta.py

# Lista d'asta 2026-27 su listone SURROGATO (il vero non esiste ancora) +
# modificatore simulato per giornata e per modulo (~2 min). NON tocca la rete.
./.venv/Scripts/python.exe scripts/run_asta_2627.py

# Fase 9 / Blocco E0: shots + team_match + player_match per TUTTE E CINQUE le
# stagioni, medie di campionato, diagnostica dei cinque fit di xG e aggancio
# giocatori esteso (~1 min da cache; con --force rilegge i 1.889 CSV, ~4 min).
# NON tocca la rete.
./.venv/Scripts/python.exe scripts/run_fase9_e0.py

# Fase 9 / Blocco E1: lo strato feature del giocatore, la deriva di ogni
# candidata prima e dopo la standardizzazione, il gate sui qualifier (~5 s da
# cache; con --force ricalcola dagli eventi, ~30 s). NON tocca la rete e NON
# stima niente.
./.venv/Scripts/python.exe scripts/run_fase9_e1.py

# Fase 9 / Blocco E2: le squalifiche (che non si stimano), lo strato distinta
# (maglia, capitano, ruolo come serie), il modello d'impiego valutato sulle
# stesse quattro transizioni del modello d'asta e la coda sul cartellino come
# predittore (~3 min). NON tocca la rete.
./.venv/Scripts/python.exe scripts/run_fase9_e2.py

# Fase 9 / Blocco E3: il modello di squadra sui GOL (rivalidato per conto suo),
# la porta inviolata come probabilita', il voto della linea condizionato alla
# forza difensiva, la correlazione dentro la linea e la verifica sui portieri
# (~1 min da cache; con --force rifa' il walk-forward dei gol, ~25 s in piu').
# NON tocca la rete.
./.venv/Scripts/python.exe scripts/run_fase9_e3.py

# acquisizione dei listoni (quotazioni) — una pagina per stagione, 5 richieste
./.venv/Scripts/python.exe -m acquisition.fantacalcio.scrape_quote --dry-run
./.venv/Scripts/python.exe -m acquisition.fantacalcio.scrape_quote

# acquisizione WhoScored — parametrizzata su campionato e stagione
./.venv/Scripts/python.exe acquisition/whoscored/scrape_season.py --dry-run
./.venv/Scripts/python.exe acquisition/whoscored/scrape_season.py --season 2021-2022

# acquisizione dei voti fantacalcio — 5 stagioni x 38 giornate, ~12 min a 3 s
# di pausa. Una pagina gia' su disco viene saltata, mai riscaricata.
./.venv/Scripts/python.exe -m acquisition.fantacalcio.scrape_voti --dry-run
./.venv/Scripts/python.exe -m acquisition.fantacalcio.scrape_voti
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
  recording_stability.py  categorie di tiro come partizione, quasi-verosimiglianza
                   con phi, scansione del punto di rottura col nullo simulato,
                   MDE, frequenze dei qualifier. **Multi-stagione**: e' l'unico
                   modulo che legge tutte e cinque le stagioni
  voti.py          dai 190 HTML di fantacalcio.it alla tabella giocatore-partita.
                   Non scarica. Contiene la riconciliazione FV = V + bonus, che
                   e' la verifica piu' forte di quell'acquisizione perche' non
                   passa da nessun modello
  aggancio.py      la corrispondenza fra WhoScored e fantacalcio. **La chiave e'
                   diversa ai due livelli**: per le squadre il calendario, per i
                   giocatori il cognome. Non e' simmetrico ed e' misurato, non
                   assunto
  presenza.py      presenza fantacalcistica e regola dell'80' misurata nei due
                   versi. E' il bersaglio del modello P1
  lega.py          LA CONFIGURAZIONE DELLA LEGA, separata dal codice (§6): bonus,
                   fasce del modificatore, formato. Non legge dati e non stima
                   niente. `gestione_sv()` solleva DecisioneMancante finche' la
                   0.3 non e' decisa, invece di scegliere un default
  quotazioni.py    il listone. QI e' il prezzo d'asta, FVM e' un CONCORRENTE del
                   modello e non un riferimento
  fantapunti.py    il fantavoto DI QUESTA LEGA, ricalcolato dai bonus. Diverge da
                   quello della fonte solo sulle porte inviolate, e lo verifica
  modello_asta.py  punti totali attesi di stagione. Walk-forward su 4 transizioni
                   contro 4 baseline, di cui due (QI, FVM) sono concorrenti veri
  modificatore.py  il modificatore di difesa, SIMULATO per giornata e per modulo.
                   Mai applicato alle medie di stagione: la scorciatoia sbaglia
                   di -20 o +50 punti a seconda della linea di riferimento
  multistagione.py Fase 9 / E0. Le tabelle di Fase 1 sulle CINQUE stagioni, le
                   medie di campionato come tabella `stagione x grandezza`, la
                   diagnostica dei cinque fit di xG e l'aggancio esteso con la
                   coerenza incrociata. Non normalizza niente: la deriva resta
                   nel derivato, la standardizzazione e' dello strato feature (E1)
  features_giocatore.py  Fase 9 / E1. **LO STRATO FEATURE, e la regola che lo
                   governa.** Non stima niente. Ogni candidata e' un rapporto
                   `num/den` dichiarato — e' cio' che rende il riferimento di
                   campionato la STESSA grandezza del valore del singolo — e
                   ognuna esce in due colonne, grezza e `_rel = x/m_s - 1`.
                   Contiene le tre guardie: `verifica_standardizzazione` (che
                   MISURA, non guarda il suffisso), `verifica_qualifier` (il
                   nome di un qualifier non e' un identificatore) e
                   `colonne_mai_valorizzate` (le 72, col criterio "ne' nullo
                   ne' False")
  squalifiche.py   Fase 9 / E2. **NON STIMA NIENTE**: una regola di conteggio sui
                   cartellini, con tre assunzioni dichiarate. Il taglio sui
                   destinatari **non e' quello dei minuti** — un espulso dalla
                   panchina e' squalificato lo stesso, quindi il numero e' 68 e
                   non 65. Contiene `verifica()`, che e' falsificabile e non passa
                   da nessun modello, e `confronto_fonti()`, che mette i
                   cartellini di WhoScored contro quelli dei voti (vincolo 7)
  distinta.py      Fase 9 / E2. Maglia, capitano e ruolo **come serie** dai
                   qualifier gia' in `lineup_events`. Costa 0,3 s, non una
                   rilettura dei CSV. Le fasce della maglia sono dichiarate
                   PRIMA e non vengono ridefinite quando si scopre che sono
                   eterogenee: l'eterogeneita' e' il risultato
  difesa.py        Fase 9 / E3. I gol ricomposti col punteggio VERO (gli autogol,
                   che `shots_mask` esclude), il modello di squadra sui gol
                   **rivalidato per conto suo**, la porta inviolata come
                   probabilita', la pendenza del voto sulla forza difensiva e la
                   correlazione dentro la linea. `verifica_punteggio()` e'
                   falsificabile contro `matches.json` e non passa da nessun
                   modello. **La verifica finale sui portieri e' negativa** ed e'
                   il risultato: vedi la sezione di E3
  impiego.py       Fase 9 / E2. Il modello d'impiego e la sua valutazione sulle
                   stesse quattro transizioni del modello d'asta. Il pavimento di
                   esposizione e' **zero** ed e' un parametro di E2, non
                   un'eredita' di E1: qui i pochi minuti sono il bersaglio.
                   Contiene anche la **coda**: `contributo_cartellini` prova
                   l'inversione di E2.1 in due forme per due standardizzazioni, e
                   `ridondanza_cartellini` e' cio' che distingue «e' gia' nel
                   set» da «non c'e' segnale» — senza, un nulla e' ambiguo
acquisition/       cio' che porta dati dentro il repository (Fase 7A)
  whoscored/       gli script del fork: main.py, scrape_matches.py,
                   scrape_season.py, utils.py. Sono SCRIPT, non moduli: si
                   eseguono, non si importano, e non c'e' __init__.py li' dentro
    target.py      l'eccezione: risoluzione campionato+stagione, percorsi e CLI.
                   NON importa selenium, ed e' percio' l'unica parte
                   dell'acquisizione verificabile dai test senza browser
  fantacalcio/     i voti. **E' un pacchetto vero**, non una cartella di script:
                   `acquisition.fantacalcio`. La cartella whoscored espone gia'
                   i nomi `target` e `pagina` e i test la mettono in sys.path —
                   due moduli `target` importabili per nome nudo sarebbero lo
                   stesso oggetto in sys.modules
    target.py      bersagli, URL, percorsi, User-Agent. NON importa requests
    pagina.py      il parser. Funzione pura da byte HTML a righe: tutta la
                   conoscenza del markup della fonte sta qui
    scrape_voti.py i voti: 38 pagine per stagione
    scrape_quote.py il listone: una pagina per stagione. Distingue "listone non
                   ancora pubblicato" da "markup cambiato" — la 2026-27 e' il
                   primo caso, e mandarla in quarantena sarebbe stato sbagliato
scripts/  run_phase1..5.py, run_phase6a.py .. run_phase6f.py,
          run_phase7_stabilita.py, run_blocco0.py, run_voti_fantacalcio.py,
          run_aggancio.py, run_modello_asta.py, run_asta_2627.py,
          run_fase9_e0.py, run_fase9_e1.py, run_fase9_e2.py, run_fase9_e3.py,
          tiri_in_porta.py
tests/    conftest + 27 moduli
legacy/   backtest circolare archiviato (NON riusare)
  fork/            materiale d'origine del fork, conservato per attribuzione:
                   EPV_grid.csv, linecollection.py, visuals.py, tutorial.ipynb,
                   logo.jpg, collaudo_fork_manuale.py (ex test.py in radice —
                   NON e' un test pytest, vedi legacy/README.md)
reports/  output rigenerabili
data/
  raw/             grezzo. Non si trasforma e non si sovrascrive mai.
    whoscored/ITA-serie-a/2025-2026/{events/*.csv, matches.json}
    fantacalcio/ITA-serie-a/<stagione>/voti/<gg>.html.gz   190 pagine, 8,3 MB.
                   gzip con mtime=0: senza perdita, quindi resta grezzo, e
                   deterministico, quindi l'hash del manifest significa qualcosa
    manifest.json  provenienza di ogni file acquisito. E' l'UNICA cosa sotto
                   data/ che sta in git.
  processed/ITA-serie-a/<stagione>/*.parquet   rigenerabile. Dal blocco E0 della
                   Fase 9 le cartelle sono CINQUE, non una: `events_slim`,
                   `lineup_events`, `shots`, `team_match`, `player_match` per
                   ognuna delle stagioni storiche (73 MB in tutto)
  processed/ITA-serie-a/phase7_*.parquet       cache che ATTRAVERSA le stagioni
                   (`config.processed_league_dir`): non sta dentro nessuna
                   cartella di stagione perche' non appartiene a nessuna
  processed/ITA-serie-a/fase9_medie_campionato.parquet   110 righe, forma lunga
                   `stagione x grandezza x unita -> media`. E' il RIFERIMENTO con
                   cui lo strato feature standardizzera' (E1), e sta qui e non
                   dentro `player_match` perche' una media di campionato e' un
                   fatto DI STAGIONE, non di riga
  processed/ITA-serie-a/fase9_xg_diagnostica.parquet     5 righe, una per fit
  processed/ITA-serie-a/fase9_e3_walkforward_gol.parquet 3.478 righe, il
                   walk-forward dei GOL delle cinque stagioni con i quattro
                   baseline e `lam_subiti` (il lambda dell'avversario nella stessa
                   partita). Cache rigenerabile con `run_fase9_e3.py --force`
  processed/ITA-serie-a/fase9_feature_giocatore.parquet  3.972 righe, la tripla
                   `(stagione, playerId, teamId)`. Ogni candidata c'e' DUE volte,
                   grezza e `_rel`: la grezza resta perche' senza non si potrebbe
                   piu' misurare la deriva
  processed/ITA-serie-a/fase9_feature_riferimenti.parquet  95 righe, **lo stesso
                   schema** di `fase9_medie_campionato`. File separato per una
                   ragione operativa e non concettuale: `run_fase9_e0.py`
                   riscrive il proprio Parquet per intero, quindi righe di E1
                   appese li' sparirebbero al primo rilancio di E0
  processed/ITA-serie-a/fantacalcio_{voti,partite}.{parquet,csv}
                   i voti delle cinque stagioni, in due forme. **Il Parquet e'
                   quello giusto**: il CSV perde i tipi, e `giocatore_id` (Int64
                   con i nulli degli allenatori) riletto da CSV torna `4431.0`.
                   Il CSV serve ad aprire la tabella fuori dal repository
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
  deduplicare. `eventId` da solo non e' una chiave, e' numerato per squadra.
  **`(matchId, teamId, eventId)` non e' unica** (corretto dal Blocco 0, che l'ha
  misurata su tutte e cinque le stagioni): ha **una** collisione, nella partita
  `1901279` del 2025-26, dove l'`eventId` 838 della squadra 75 sta su un `Save`
  a 84:29 e su un `BallRecovery` a 84:32. Una riga su 2,8 milioni non sposta
  nessuna stima, ma **nessuna delle chiavi disponibili e' unica**: verificare la
  cardinalita' dopo ogni join invece di fidarsi.
- `qualifiers` e `satisfiedEventsTypes` sono **repr Python** con apici singoli:
  serve `ast.literal_eval`, `json.loads` fallisce.
- `maxMinute` a volte e' **minore** dell'ultimo evento. Usare
  `minutes.match_duration()`, che prende il massimo fra i due.
- **I rigori non sono marcati da `situation`**, che resta nulla su tutti e 106.
  Identificarli con `penaltyScored | penaltyMissed` (unione = qualifier
  `Penalty`, e non rivela l'esito).
- `role_code = 5` nel `FormationSet` significa **"sostituto"**, non una
  posizione: i panchinari non hanno ruolo. Usare `minutes.season_roles()`.

  **Codebook della fonte per `PlayerPosition`** (qualifier del `FormationSet`),
  **confermato da due strade indipendenti**: `1 = portiere, 2 = difensore,
  3 = centrocampista, 4 = attaccante, 5 = panchina/ignoto`. Il repository ci era
  arrivato **empiricamente** (`sot/minutes.py`: una sola occorrenza di `1` per
  squadra-partita, e x medio dei tocchi monotono nel codice — 11.2 / 39.6 /
  52.4 / 62.3); la codifica e' **dichiarata** come codifica Opta da uno script R
  dell'utente precedente al repository (`Role Modifier.R:5`), scritto su una
  forma diversa dei dati. Due derivazioni indipendenti che concordano, quindi il
  codebook non e' piu' un'inferenza. Verificato sulle cinque stagioni: i valori
  osservati sono **esattamente** `{1,2,3,4,5}` e i `1` sono 3.778, cioe' uno per
  squadra-partita su 1.889 partite.

  **Nello stesso qualifier c'e' anche `JerseyNumber`**, allineato posizionalmente
  a `InvolvedPlayers` come `PlayerPosition`, e c'e' `CaptainPlayerId`. Sono in
  `lineup_events.parquet`, che conserva la stringa `qualifiers` grezza: estrarli
  **non costa una rilettura dei CSV**.
- **85 espulsioni, ma solo 65 tolgono un uomo dal campo**: 17 sono ad
  allenatore/staff (`playerId` nullo), le altre a giocatori gia' usciti o in
  panchina.
- I nomi delle squadre **non esistono nei CSV**: solo `teamId`. Vanno presi da
  `data/serie_a_2025_2026_matches.json` incrociando `matchId` + casa/trasferta.
- **Niente xG nei dati.** Quello che usiamo e' stimato in casa
  (`sot/xg.py`), cross-fitted a 5 fold **raggruppati per partita**. Va sempre
  chiamato "xG interno", mai xG del fornitore.

Trappole che compaiono solo guardando **piu' stagioni insieme** (verifica di
stabilita' del criterio, sezione piu' sotto):

- **Esistono squadre-partita con zero tiri** (Pisa-Cremonese del 2026-05-10, e
  una nel 2021-22). Ricostruire l'universo squadra-partita dai soli tiri le fa
  sparire dal denominatore: si prende dalle due squadre di ogni file.
- **Gli ingressi dell'xG si muovono fra stagioni**: `shotCounter` raddoppia
  (3.4% → 7.7% dei tentativi), `shotOpenPlay` scende di 7.5 punti. **Non
  stimare l'xG interno su piu' stagioni insieme** senza un effetto di stagione.
- **Un qualifier puo' sparire senza che nulla se ne accorga**: `StandingSave`
  c'e' su ~81% dei tiri nelle prime quattro stagioni e su ~2% nel 2025-26, a
  schema, conteggio colonne e numero di eventi invariati.
- **Il nome di un qualifier NON e' un identificatore stabile** (Blocco 0).
  Misurato su **tutti** gli eventi e non sui soli tiri, `StandingSave` sta sul
  **71% di tutti gli eventi** nelle prime quattro stagioni — 683 occorrenze su
  885 stanno su eventi `Pass` — e nel 2025-26 sta su ~30 eventi per partita e
  solo su `Tackle`/`Foul`/`Save`. Non e' una parata che sparisce: e' **la stessa
  etichetta su id diversi**, cioe' due versioni del dizionario della fonte.
  `OtherBodyPart` fa lo stesso e **nelle stesse partite** (91 su 92).
  **L'id numerico non e' recuperabile dai dati in casa**:
  `acquisition/whoscored/main.py:432` lo butta via tenendo solo il `displayName`.
- **72 delle 259 colonne non sono valorizzate in nessuna stagione** (Blocco 0).
  Fra queste **tutte** le `cleanSheet*`, `goalConcededByTeam*`,
  `goalScoredByTeam*`, le `save*` per settore di porta e `passAccuracy`: porta
  inviolata, gol subiti e precisione dei passaggi **si derivano, non si
  leggono**. Attenzione a `notna()`: lo scraper scrive `False` dove il campo e'
  assente, quindi la misura giusta e' "ne' nullo ne' `False`".
- **Le frequenze dei tipi di evento derivano fra stagioni** (Blocco 0), e
  derivano sulle grandezze che servono al voto base: `Clearance` +48%,
  `BallRecovery` −26%, `Error` +162% fra 2021-22 e 2025-26. Nessun tipo compare
  o sparisce; sono le frequenze a muoversi.
- **La giornata di campionato non esiste nei dati.** `matches.json` e' ordinato
  **per data**, non per turno (blocchi di dieci coerenti solo 5 volte su 38).
  Il sostituto e' l'indice cronologico di squadra (`team_match_idx`), che non e'
  la giornata quando ci sono recuperi.
- **`isOwnGoal` e' l'unica colonna non sempre presente**, e lo e' in tutte e
  cinque le stagioni allo stesso modo: la trappola nota, non una divergenza.

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
| `team_match.parquet` | 760 | 26 colonne (erano 24 prima di E0) |
| `player_match.parquet` | 17.774 | 20 colonne (erano 17 prima di E0) |
| `shots.parquet` | 9.359 | tiri con geometria e xG |

> Le **righe non sono cambiate**; le colonne si'. `stagione` e `xg_fit` su
> entrambe le tabelle, piu' `stato` su `player_match`, tutte dal blocco E0 della
> Fase 9. Vedi quella sezione per il perche' `xg_fit` non e' ridondante rispetto
> a `stagione`, e perche' `stato` non aggiunge dati.

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

### Stabilita' del criterio di rilevazione fra stagioni ✅

`reports/phase7_stabilita_rilevazione.md`, da `scripts/run_phase7_stabilita.py`;
modulo `sot/recording_stability.py`, test `tests/test_stabilita_rilevazione.py`
(36). **Chiude il limite dichiarato dall'acquisizione** ed e' il prerequisito di
7B: se il criterio si fosse spostato, `rho` stimato su cinque stagioni
misurerebbe anche lo spostamento. **Non e' stato scaricato niente** e **nessun
numero e' cambiato**, verificato rieseguendo: `run_phase1.py` ridà
4.034 / 4.432 / 3.637 / 5.105 su 562.672 eventi, `run_phase5.py` ridà Como 4.34
e 5.03 / 191 / [151, 240].

**Esito: la definizione di tiro in porta e' stabile, il contesto del tiro no.**

- **Identita' esatta con il flag Opta nativo in tutte e cinque le stagioni**:
  zero discordanze in entrambe le direzioni su 47.530 tentativi. E' il
  risultato piu' forte del blocco perche' non passa da nessun modello. La
  Fase 0 lo aveva verificato sul solo 2025-26.
- **Le quattro categorie sono una partizione** (in porta + respinto + palo +
  fuori = tentativi, verificato riga per riga) e **le loro quote non si
  muovono**: `q_in_porta` fra 0.3250 e 0.3408, nessuno `z` binomiale sopra 2.3,
  e col `phi` osservato (1.101) il gradino di stagione non batte il baseline
  costante (F = 1.75, p = 0.135). **Il livello invece si muove**: tentativi per
  squadra-partita da 13.03 a 12.12, tiri in porta da 4.441 a 4.033 (-9.2%).
  Totale che scende a ripartizione ferma = si tira di meno, non si conta
  diversamente.
- **Gli ingressi dell'xG interno non sono stabili, ed e' il risultato che il
  blocco non cercava.** `shotCounter` 3.4% → 7.7% dei tentativi, `shotOpenPlay`
  69.3% → 61.8%, `bigChanceMissed` 8.1% → 10.3%; sono le colonne di
  `sot/xg.py`. La deriva continua batte il gradino di stagione sulla QAIC (e'
  graduale, non un salto), ma il singolo confine peggiore cade a **2024-08** per
  tre flag su quattro. **Un xG stimato su piu' stagioni insieme mescola due
  definizioni**: o si stima per stagione o la stagione entra come effetto
  esplicito. `bigChanceScored` resta fermo, ed e' il controllo interno.
- **`StandingSave` sparisce, e sparisce per pagina intera**: su ~81% dei
  tentativi in ogni partita delle prime quattro stagioni (1.507 su 1.509), su 11
  partite su 380 nel 2025-26 e **zero esatto** nelle altre. Non tocca niente di
  cio' che il modello usa. Due spiegazioni compatibili — archivio della fonte
  oppure momento del prelievo — e **i dati in casa non le separano**:
  l'esperimento e' un solo GET su una partita gia' scaricata, da fare al primo
  blocco che tocca la rete.
- **Il risultato negativo ha la sua potenza dichiarata** (lezione della 6D): un
  gradino sotto **0.20 tiri in porta per squadra-partita** non verrebbe visto,
  cioe' il 19% dell'eccesso del Como. Che la macchina sia sensibile non e'
  assunto: **la stessa procedura vede la deriva di `shotCounter` con F = 215**.
- Il punto di rottura non e' assunto a luglio, e' **cercato**: massimo su tutti
  i confini di mese, con la distribuzione del massimo simulata sotto il nullo
  (beta-binomiale con il `phi` vero, 2.000 repliche). Cercando ovunque
  p = 0.23; cercando solo sui quattro confini di stagione — ipotesi dichiarata
  in anticipo, quindi piu' potente — p = 0.065, che con Bonferroni sulle
  quattro categorie vale 0.26 e non passa. E cade al passaggio
  2021-22 → 2022-23, cioe' l'uscita dalla stagione **gia' dichiarata non
  confrontabile** per il ritorno del pubblico.
- Nessuna colonna compare o sparisce fra stagioni: l'unica non sempre presente
  e' `isOwnGoal`, che e' la trappola nota (6-10% dei file, cioe' la frequenza
  degli autogol). `situation` nulla passa dal 5.5% al 12.3% — campo che il
  progetto non usa, ma e' un altro pezzo dello strato descrittivo che si muove.

> **Per 7D**: `rho` si puo' stimare sui tiri in porta delle cinque stagioni, ma
> sugli **eccessi relativi** alla media di campionato della stagione, non sugli
> scarti assoluti — la media di campionato si e' mossa del 10.1% per ragioni di
> gioco, e +1 tiro di eccesso non significa la stessa cosa nel 2021-22 e nel
> 2025-26.

---

### Acquisizione dei voti fantacalcio 2021-2026 ✅

`reports/voti_fantacalcio.md`, da `acquisition/fantacalcio/` +
`scripts/run_voti_fantacalcio.py`; modulo di lettura `sot/voti.py`, test
`tests/test_acquisizione_fantacalcio.py` (37). **Chiude la D1 del Blocco 0 e il
`[NON DECISO]` di `regole_fantacalcio.md` §7.1** (via scelta: **vista HTML
pubblica**; l'export Excel resta a 401). **Nessun numero delle Fasi 1-6 e'
cambiato**, verificato rieseguendo: `run_phase1.py` ridà 4.034 / 4.432 / 3.637 /
5.105, `run_phase5.py` ridà Como 4.34 e 5.03 / 191 / [151, 240], e le otto
figure sono byte a byte identiche.

**190 pagine, 63.105 righe giocatore-partita, 8,3 MB di grezzo**; 380 partite e
20 squadre in ognuna delle cinque stagioni, nessun buco. Autorizzazione
Fantacalcio S.r.l. dichiarata dall'utente (§7.1, decisione 1).

**Il risultato che conta e' la riconciliazione: 57.574 righe su 57.574.** La
fonte pubblica il voto, il fantavoto **e** separatamente le otto voci di bonus:
le due strade devono chiudere, e non passano da nessun modello. Il barema e'
stato **ricavato per differenza**, non dichiarato dalla fonte. Cosa ne e' uscito:

- **I cartellini non sono una colonna di bonus.** Stanno come **classe CSS sullo
  span del voto** (`player-grade yellow-card`, `red-card`). Chi legge solo
  `data-value` perde in silenzio 7.884 ammonizioni e 432 espulsioni, che valgono
  −0,5 e −1.
- **Il gol su rigore non e' anche in "gol segnati".** Sta solo in "rigori
  segnati" e vale +3 una volta sola. Sommare le due colonne, come la lettura
  ingenua di §1.1 delle regole suggerirebbe, conterebbe due volte lo stesso gol.
- **`player of the match` ha una colonna e non entra nel fantavoto.**
- **Il `FV` della fonte NON e' il fantavoto della lega.** Il barema di §1.1
  contiene **+1 di porta inviolata**, che la fonte non applica — e si vede dal
  fatto che la riconciliazione torna esatta *senza*. Il fantavoto di lega va
  ricalcolato dai bonus e la porta inviolata **derivata** (`ruolo == "p"` e
  `gol_subiti == 0`). Un test lo blocca.

**L'errore che questa acquisizione ha commesso, corretto prima di pubblicare i
numeri e riportato perche' e' istruttivo:** la soglia che riconosce le
sentinelle di s.v. (`55`, `56`) era applicata **anche al fantavoto**. Un voto sta
in 0-10 (osservato 3,0-9,5); un fantavoto no — Simeone, 9 con quattro gol, fa
**21**. Cosi' ~1.000 fantavoti veri diventavano codici inesistenti, e quelle
righe — diventate nulle — **uscivano dalla riconciliazione senza far rumore**,
perche' un residuo nullo si filtra da solo. La verifica dichiarava 53.775/53.775
saltando proprio le righe dei marcatori, cioe' le uniche in cui il barema dei gol
veniva messo alla prova. Ora il denominatore e' "righe con un voto" e una riga
col voto e senza fantavoto conta come fuori registro.

**Le trappole di questa fonte** (dettaglio in `acquisition/fantacalcio/pagina.py`):

- **Le venti tabelle sono in ordine alfabetico, non appaiate per partita.**
  L'avversario si prende dal calendario in cima alla pagina, via
  `data-teams-id`. Chi assumesse "due tabelle consecutive = una partita"
  otterrebbe voti giusti e avversari sbagliati per tutte e dieci le partite.
- **Venti righe per giornata sono allenatori** (`ruolo == "all"`, nessun link,
  `giocatore_id` nullo) e prendono un voto come i giocatori. Da filtrare da
  qualunque media, o dentro c'e' il giudizio sul tecnico.
- **In tabella ci sono solo i giocatori scesi in campo**, non la rosa. La
  presenza fantacalcistica e' un sottoinsieme ancora piu' piccolo: le righe con
  un voto **numerico**.
- **`55` non e' un voto, e' l's.v.**: 15.397 occorrenze, mai su un titolare.
  `56` esiste, 10 volte, e **mai sulla scala Redazione**. Sono conservati in una
  colonna a parte. Dove il voto e' `56`, il fantavoto e' reso `0`: quello zero e'
  l'assenza scritta a numero, non un fantavoto.
- **`giocatore_id` viene dall'URL del profilo ed e' stabile fra stagioni.** E' la
  chiave con cui ricucire l'identita' senza passare dai nomi, che la fonte
  abbrevia e disambigua a mano (`Ivanovic M.`).

**L's.v. osservato sta quasi tutto sui subentrati**: 30-33% di loro contro lo
0,2% dei titolari, stabile su tutte e cinque le stagioni. Non e' una conferma
della regola dell'80': la fonte **dichiara che una soglia di minuti non esiste**,
quindi l's.v. non e' una funzione dei minuti e la regola resta cio' che §1.2 dice
che sia — un'assunzione di modello, falsificabile solo sulla 2025-26.

**Il confronto fra stagioni e' descrittivo e non chiude la §5 delle regole.**
Voto medio 6.002 → 5.981, quota s.v. 9,0% → 9,6%: si muove poco. Ma il *livello*
non e' il *criterio editoriale*, e il test formale di rottura — punto di rottura
**cercato** e non assunto, potenza dichiarata, come `recording_stability.py` fa
sui tiri — **non e' stato rifatto sui voti**.

**Un difetto latente trovato di rimbalzo**, in `tests/test_stabilita_rilevazione.py`:
la guardia "nessuno script delle Fasi 1-6 importa questo modulo" cercava il nome
del modulo **ovunque nel file**, quindi bastava *nominarlo* in prosa per essere
dichiarati colpevoli — ed e' successo a `run_voti_fantacalcio.py`, che lo cita
proprio per dire che non lo usa. Ora cerca una riga di `import`.

**Cosa NON e' stato preso: le quotazioni del listone** (`/quotazioni-fantacalcio`).
Non erano nella richiesta, e sono la **verifica principale del progetto** (F5,
D2 del Blocco 0).

---

### Fase 8 — aggancio delle due fonti e regola dell'80' ✅

`reports/aggancio.md`, da `scripts/run_aggancio.py`; moduli `sot/aggancio.py` e
`sot/presenza.py`, test `tests/test_aggancio.py` (38). E' il prerequisito di
tutto il resto della Fase 8: il Blocco 0 non poteva farlo perche' aveva un lato
solo. **Chiude la D6** (la giornata di campionato) e il `[DA MISURARE]` di
`regole_fantacalcio.md` §1.2. Nessuna richiesta di rete.

**La chiave e' diversa ai due livelli, ed e' il risultato del blocco:**

| livello | chiave | verifica | esito |
|---|---|---|---|
| squadra | insieme delle 38 coppie `(data, in casa)` | il nome | 100/100, margine 19-29 su 38 |
| partita | `(stagione, casa, trasferta)` | la data | **1.888** agganciate |
| giocatore | il **cognome** dentro la squadra + iniziali | il calendario | **609 su 609**, zero irrisolti |

- **Al livello di squadra il nome non e' una chiave** (`AC Milan` contro `Milan`,
  `Parma Calcio 1913` contro `Parma`), il calendario si'.
- **Al livello di giocatore vale l'esatto contrario, e l'ho scoperto
  sbagliando.** La prima versione agganciava per insieme di presenze, per
  simmetria. Non funziona, e il motivo e' strutturale: l'insieme delle partite di
  una *squadra* e' 38 su 380 — sparso — quello di un *giocatore* dentro la sua
  squadra e' 35 su 38, quasi pieno. Due titolari qualsiasi hanno fra loro
  Jaccard ~0.85 e il margine scendeva sotto 0.03 su meta' rosa. **Il calendario,
  li', e' rumore.** Ora e' la verifica: Jaccard medio **0.9999**, minimo 0.944.
- I 23 casi su 609 che il cognome grezzo sbaglia sono di due specie sole:
  **lettere che l'ASCII non piega** (`Højlund`, `Østigård`, `Grønbæk` — `ø` non
  e' una `o` con un segno sopra) e **le iniziali** che la fonte aggiunge solo
  quando servono (`Martinez L.` contro `Martinez Jo.`). Le iniziali **si usano,
  non si tolgono**: buttarle via creava l'ambiguita' da risolvere.
- **Residui, tutti dichiarati**: 12 partite hanno i voti e non gli eventi (le
  `matchCentreData: null` gia' note); **1 ha gli eventi e non i voti** — lo
  spareggio Spezia-Verona, l'unica coppia ordinata che si ripete, che senza
  accorgersene si sarebbe agganciata ai voti della **giornata 25**; 2 partite
  hanno date discordi e sono le due **interrotte e riprese**.
- **Il ruolo NON e' la stessa grandezza nelle due fonti**: 133 giocatori su 609
  discordano. Quello dei voti e' un'etichetta di *lega* (P/D/C/A), quello di
  WhoScored e' posizionale. **Restano due colonne** (vincolo 7).

**La regola dell'80' misurata** — 11.926 righe della 2025-26:

| | |
|---|---:|
| accordo | **97,84%** |
| baseline «nessun s.v.» | **90,45%** |
| falsi s.v. | 142 (12,2% dei proiettati s.v.) |
| s.v. mancati | 116 (1,08%) |

- **Il baseline e' il punto** (vincolo 6): il 97,8% da solo sembra un risultato,
  ma dire «nessuno prende s.v.» ne fa gia' 90,5. Il guadagno vero e' 7,4 punti.
- **L'80' cade sul massimo della griglia 60-95**, e non perche' sia stato scelto
  li': era deciso prima, in `regole_fantacalcio.md` §1.2. Scelto qui sarebbe un
  iperparametro adattato al campione su cui poi lo si valuta — vincolo 1. Un
  test blocca la costante e vieta che qualcuno la ricavi da un `argmax`.
- **Sopra i 30 minuti giocati non c'e' un solo s.v. su 8.552 righe.** La fonte
  dichiara che nessuna soglia esiste, e formalmente e' vero; la *pratica*
  editoriale e' quasi deterministica. Riscrivere la regola sui minuti giocati e'
  stato provato e **non migliora**: 97,83% contro 97,84%, cambia il mix degli
  errori e non la loro quantita'.
- **Un verso d'errore strutturale che §1.2 non elencava**: tutti e 18 gli s.v.
  dei titolari sono usciti prima del 30'. La regola guarda l'**ingresso** e non
  li vedra' mai.
- **La fonte dei voti non elenca due giocatori che hanno giocato** (7 e 10
  minuti). Non da' s.v.: non da' riga. Terzo stato oltre «voto» e «s.v.».

**Limite dichiarato**: l'aggancio dei **giocatori** copre la sola 2025-2026,
perche' ha bisogno delle presenze partita per partita dal lato WhoScored e
`player_match.parquet` esiste per la sola stagione pubblicata. Squadre e partite
coprono tutte e cinque.

---

### Fase 8 — modello per l'asta ✅ (con esito negativo, che e' il risultato)

`reports/modello_asta.md`, da `scripts/run_modello_asta.py`; moduli
`sot/lega.py`, `sot/quotazioni.py`, `sot/fantapunti.py`, `sot/modello_asta.py`,
test `tests/test_modello_asta.py` (24). Nessuna richiesta di rete nel modello;
i cinque listoni sono stati acquisiti a parte.

**Decisioni di lega prese dall'utente il 2026-08-03** e messe in `sot/lega.py`,
separate dal codice come §6 chiede: `0.1` tre fasce 6.00/6.50/7.00 con
+1/+3/+6, `0.4` malus −1 sotto soglia, `0.2` **`n_difensori` dipende dal
modulo** (era la contraddizione 2 del Blocco 0: con `n` fisso il test di
coerenza di §3.2 era insoddisfacibile per costruzione), `0.5` 8 squadre, budget
1000, rosa 3/8/8/6. **La `0.3` resta aperta** ed e' l'unica: `gestione_sv()`
solleva `DecisioneMancante` invece di scegliere un default.

**Il fantavoto di lega non e' quello della fonte, e la divergenza e' esatta**:
1.092 righe su 57.574, **tutte di scarto +1, tutte portieri, tutte con
`gol_subiti == 0`**. E' la porta inviolata, che il barema della fonte non
applica. Se divergesse altrove sarebbe un difetto; divergendo solo li', e' la
conferma.

**Esito del modello: batte l'ignoranza, non batte il mercato.**

| candidato | Spearman | precisione sui primi N |
|---|---:|---:|
| **FVM della fonte** | **0.811** | **0.518** |
| quotazione iniziale QI | 0.606 | 0.162 |
| persistenza (anno prima) | 0.451 | 0.211 |
| **modello** | 0.452 | 0.177 |
| media di ruolo | 0.156 | 0.065 |

- **Il FVM e' un concorrente, non un riferimento**: e' una stima di valore fatta
  da altri, con informazioni che il modello non ha. Se non lo si batte, comprare
  al listino e' la scelta razionale — e va scritto, non aggirato.
- **Il modello non supera nemmeno la persistenza** ("l'anno prossimo come
  l'anno scorso"). Tutto il macchinario dei tre fattori con shrinkage non
  aggiunge niente. Con quattro transizioni la differenza non e' distinguibile dal
  rumore, ma il segno e' contrario al modello.
- **Sui portieri il modello fa 0 e il FVM 0.667**, e la causa e' identificabile:
  i punti di un portiere dipendono dalla difesa della sua squadra, e **questo
  modello non guarda la squadra affatto**.

**Il risultato piu' utile e' dove sta l'errore**: con le presenze note il MAE
crolla da **61.4 a 5.6** (−91%); con i bonus noti scende solo a 52.5. Il voto
base e i bonus sono quasi risolti; il problema e' prevedere **quante partite un
giocatore giochera'**, e quello dipende da cose che nessuna tabella acquisita
contiene — minutaggio atteso, gerarchia di rosa, mercato, infortuni. **Non e' un
difetto di stima, e' un'assenza di dati.**

**Un difetto trovato dai test, e non era piccolo**: `precisione_top` scioglieva i
pari merito nell'ordine della tabella, e il listone arriva ordinato per `QI`
decrescente. Il baseline "media di ruolo" — costante dentro un ruolo — sceglieva
cosi' i giocatori piu' cari e otteneva 0.182 invece di 0.065: **il confronto era
falsato in favore dell'ignoranza**. Ora i pari merito si sciolgono col seme del
progetto.

**Il listone 2026-27 non esiste ancora** (verificato il 2026-08-03: la pagina
dichiara "Dati non disponibili"), quindi **la lista d'asta vera non e'
producibile oggi**. Lo scraper distingue questo caso da un cambio di markup.

> **Trappola per le sessioni future.** Il modello perde contro FVM e persistenza,
> e questo e' il contenuto informativo del blocco. **Non va "sistemato"**
> ritoccando lo shrinkage finche' il numero non supera il concorrente: e' lo
> stesso errore che le Fasi 2 e 3 servivano a escludere. La strada indicata dai
> dati e' un'altra ed e' scritta sopra: collegare il **modello di squadra** gia'
> validato (Fasi 2-4) e attaccare le **presenze**, non i bonus.

---

### Fase 8 — modificatore di difesa e lista d'asta provvisoria ✅

`reports/asta_2627.md`, da `scripts/run_asta_2627.py`; modulo
`sot/modificatore.py`, test dentro `tests/test_modello_asta.py` (38 in tutto).
`[DECISO 0.3 — 2026-08-03]` **`escludi`**: un difensore senza voto esce dalla
media e la linea si accorcia.

**Il risultato del blocco e' che la scorciatoia vietata da §2.2 sbaglia davvero,
e in entrambe le direzioni.** Applicare le fasce alla media di stagione invece di
simulare per giornata costa:

| linea di riferimento | media attesa | fasce sulla media | simulato | scarto di stagione |
|---|---:|---:|---:|---:|
| schierabili (i migliori 8xN) | 6.04 | **+1** | +0.49 | **−20** |
| mediano di tutti i quotati | 5.93 | **−1** | +0.34 | **+51** |

Lo stesso errore metodologico sbaglia di 20 punti in un verso o di 50 nell'altro
**a seconda della linea**. §2.2 diceva "il segno puo' andare in entrambe le
direzioni e va misurato": va in entrambe.

- **La linea di riferimento va dichiarata, e la prima versione l'aveva sbagliata.**
  Usava il mediano di *tutti* i quotati — che e' un panchinaro, con media
  difensiva attesa sotto 6,00 — e ogni contributo marginale misurato contro
  quella linea risultava gonfiato. Ora il default e' `schierabili` e l'altro
  universo resta disponibile, perche' §2.2 chiede proprio di far vedere che lo
  stesso giocatore vale diversamente contro linee diverse.
- **Un contributo esiste per modulo, non in assoluto** (decisione 0.2): lo stesso
  difensore ha tre valori a 3, 4 e 5 difensori, e non vengono mai schiacciati in
  una media. Dimarco vale +10.5 punti di stagione a 4 difensori; il portiere
  mediano vale −2.1.
- **`escludi` non e' neutro**: su una linea di tre da 7 e uno da 4, se il quarto
  prende voto la media e' 6,25 (+1), se non lo prende e' 7,0 (+6). **Cinque punti
  per giornata dal solo fatto che il peggiore non e' stato giudicato.**

**La lista d'asta 2026-27 e' provvisoria e su listone surrogato**, perche' quello
vero non esiste ancora: l'universo e' quello della 2025-26, cioe' gli stessi nomi
dell'anno scorso. Mancano **le tre promosse** (~15% del listone vero), ci sono
**le tre retrocesse** — Cremonese, Verona, Pisa, ricavate dalla classifica e non
scritte a mano — che sono **marcate in tabella, non tolte**, e `QI`/`FVM` sono
dell'anno prima: come ordine informativi, come prezzo no.

**Non c'e' nessuna colonna di crediti, ed e' voluto**: convertire punti attesi in
prezzo d'asta e' un problema di allocazione con budget, non una proporzione
(§2.2). Una divisione plausibile sarebbe un segnaposto travestito da risultato.

**Limite della simulazione, dichiarato**: i membri della linea sono indipendenti.
Una difesa che prende tre gol prende voti bassi *insieme*, quindi la variabilita'
della media di linea e' sottostimata. Con fasce a scalini il segno dell'effetto
sul bonus atteso non e' ovvio, e non e' stato corretto a occhio.

---

### Fase 9 — Blocco E0: `player_match` sulle cinque stagioni ✅

`reports/fase9_e0_player_match_5_stagioni.md`, da `scripts/run_fase9_e0.py`;
modulo `sot/multistagione.py`, test `tests/test_fase9_e0.py` (40). **Nessuna
richiesta di rete.** **Nessun numero pubblicato e' cambiato**, verificato
rieseguendo: `run_phase1.py` ridà 4.034 / 4.432 / 3.637 / 5.105 su 562.672
eventi, `run_phase5.py` ridà Como 4.34 e 5.03 / 191 / [151, 240].

**Chiude il prerequisito della Fase 9**: senza storia player-match non esiste
walk-forward, e un predittore che vive su una stagione sola non e' testabile.
87.449 righe giocatore-partita su 1.889 partite.

**La catena di Fase 1 non era parametrizzata sulla stagione**, e non era una
svista: `io_events` e `aggregate` leggevano le costanti di modulo
(`config.EVENTS_SLIM`, `RAW_MATCH_DIR`, `PLAYER_MATCH`…), tutte calcolate una
volta da `config.SEASON`. Con una stagione sola costante e parametro
coincidono. Ora `config` espone `player_match(season=…)` e compagne, le costanti
storiche valgono `funzione(SEASON)` **e un test lo blocca**.

**Il difetto che una stagione sola nascondeva**: `aggancio.mappa_giocatori`
aveva `stagione` nella firma ma leggeva `config.PLAYER_MATCH`, cioe' **sempre la
stagione pubblicata**, qualunque stagione le si chiedesse.

| stagione | partite | righe giocatore | SoT/squadra-partita | aggancio | irrisolti |
|---|---|---|---|---|---|
| 2021-2022 | 374 | 16.666 | 4.441 | 629 | 2 |
| 2022-2023 | 375 | 17.606 | 4.123 | 602 | 1 |
| 2023-2024 | 380 | 17.698 | 4.149 | 610 | 3 |
| 2024-2025 | 380 | 17.705 | 4.033 | 631 | 2 |
| 2025-2026 | 380 | 17.774 | 4.034 | 609 | 0 |

- **`xg_fit` non e' ridondante rispetto a `stagione`.** L'xG interno si stima una
  stagione per volta, quindi i fit sono **cinque** e `xg` sta su **cinque
  scale**. L'etichetta dice quale fit ha prodotto quel valore. **Non esiste e non
  va costruita una colonna `xg` confrontabile fra stagioni dentro il derivato**:
  la comparabilita' e' dello strato feature (E1), e un test vieta `xg_std`,
  `xg_rel` e simili dentro `aggregate`.
- **I cinque fit sono l'unica stima del blocco e sono dichiarati**, con log-loss,
  AUC e calibrazione affiancati: AUC 0.807-0.816, calibrazione fra -0.09% e
  +0.08%. La riga 2025-26 riproduce la Fase 1 (0.243 / 0.811 / +0.07%), che e' il
  controllo che la parametrizzazione non ha spostato niente.
- **Le medie di campionato sono una tabella `stagione x grandezza`**, non colonne
  ripetute su 87.449 righe: una media di campionato e' un fatto **di stagione**.
  Forma lunga perche' E1 aggiungera' le sue grandezze.
- **Il denominatore non e' 38, e non e' nemmeno il calendario.** L'Atalanta ne ha
  35 nelle due stagioni bucate. E **nessuna squadra arriva a 39** nel 2022-23,
  benche' Spezia e Verona abbiano *giocato* 39 partite (38 + playout): di quelle,
  WhoScored non ha 2 e 1. La correzione ovvia — mettere 39 a mano per le due
  squadre del playout — avrebbe sostituito un errore con un altro. **Trovato da un
  test**, non a occhio: il report affermava 39 e i dati dicono 37 e 38.
- **La coerenza fra stagioni passa su 1.544 controlli incrociati indipendenti,
  zero discordanze in entrambi i versi.** E' la verifica che una stagione sola
  non poteva fare: `giocatore_id` e `playerId` sono entrambi stabili fra
  stagioni, quindi cinque agganci indipendenti devono concordare — e il controllo
  **non passa dal nome**, cioe' non e' circolare rispetto alla regola che
  l'aggancio usa. Un test guasta un aggancio e pretende che il controllo lo veda,
  perche' «zero discordanze» non deve poter voler dire «non guarda niente».
- **Gli 8 irrisolti sono in tabella, non risolti d'ufficio**: omonimi veri
  (`Andrea` contro `Filippo Ranocchia`), giocatori con **una** presenza, e due
  casi in cui due nomi dei voti puntano allo stesso WhoScored — dove si tolgono
  entrambi. Il residuo esiste anche nel verso opposto (`ws_non_agganciati`, 0-5
  per stagione): chi gioca e che la fonte dei voti non elenca affatto.
- **Il residuo NON sta tutto sui giocatori rari, e la parte che manca conta.**
  Mediana 9,5 presenze contro 20 degli agganciati, 6 su 8 sotto la mediana — ma
  tre casi stanno al 48°, 52° e **84° percentile** (`Arthur Melo`, 33 presenze,
  cioe' un titolare), e il loro motivo non e' la rarita': e' la **collisione di
  nomi**. Sono due difetti con due rimedi diversi, e per E2 il secondo e' il piu'
  fastidioso perche' toglie dal campione un titolare, non una comparsa.

**Coda del blocco — `player_match.stato`** (titolare / subentrato / panchina).
**Non aggiunge dati**: i convocati non impiegati erano nella tabella fin dalla
Fase 1, perche' `minutes.squads()` legge l'intera rosa da `InvolvedPlayers` del
`FormationSet`, dove i panchinari stanno con `role_code = 5`. Sono **28.472
righe a zero minuti, il 32,6% della tabella**. Erano pero' leggibili solo da chi
sapesse che `minutes == 0` vuol dire "convocato e mai entrato" e non "dato
mancante" — la distinzione che il bersaglio di E2 non puo' sbagliare. I tre stati
sono una **partizione** e i titolari sono **11 per squadra-partita ovunque**, con
test su entrambe le cose.

> **Il quarto stato e' l'assenza della riga**, e non ha un'etichetta perche' non
> ha una riga. Chi non e' stato convocato — fuori lista, infortunato,
> squalificato, ceduto — non compare: WhoScored registra i convocati, non i
> tesserati. Chi ricostruisce l'impiego deve procurarsi il denominatore della rosa
> **da fuori** invece di contare le righe.
- **Il Jaccard minimo (0.778) e' stato spiegato, non attribuito.** La spiegazione
  comoda — «mancano 12 partite» — e' sbagliata nel verso: quelle tolgono presenze
  dal lato WhoScored, e li' il lato WhoScored ne ha *di piu'*. Le cause vere sono
  lo **spareggio Spezia-Verona** (14 giocatori dello Spezia con esattamente +1
  presenza) e l'aritmetica degli insiemi piccoli (4 contro 5 fa 0.800).
- **`possession` e `field_tilt` hanno media 0.500 in ogni stagione per
  costruzione** — sono quote e le due squadre si dividono 1. Stanno in fondo alla
  classifica di stabilita' per il motivo sbagliato, e il report lo dice. Per
  contro `xg` e `xg_conceded` coincidono a ogni cifra, e **quello si' e' un
  controllo** che passa.

> **Trappola per le sessioni future.** `run_aggancio.py` e `run_fase9_e0.py`
> scrivono **lo stesso** `data/mapping/aggancio_giocatori.csv`. Il primo lo
> produceva per la sola 2025-26 e avrebbe cancellato le altre quattro: ora usa
> `multistagione.aggancio_giocatori()` e filtra alla 2025-26 solo per la
> narrazione del proprio report. E' una mappa sola, non due.

### Fase 9 — Blocco E1: la regola delle feature, e dove non basta ✅

`reports/fase9_e1_stabilita_feature.md`, da `scripts/run_fase9_e1.py`; modulo
`sot/features_giocatore.py`, test `tests/test_fase9_e1.py` (32). **Nessuna
richiesta di rete, nessuna stima** — niente fit, niente bersaglio, niente
iperparametri. **Nessun numero pubblicato e' cambiato**, verificato rieseguendo:
`run_phase1.py` ridà 4.034 / 4.432 / 3.637 / 5.105 su 562.672 eventi,
`run_phase5.py` ridà Como 4.34 e 5.03 / 191 / [151, 240].

**La regola, che e' il deliverable:**

```
x_rel = x / m_s - 1        m_s = media di campionato della stagione s
```

Nessuna feature da dati evento entra in un modello multi-stagione in unita'
grezze. **Non e' uno z-score**: dividere anche per la deviazione standard di
stagione normalizzerebbe via la *dispersione*, che e' cio' che distingue i
giocatori, cioe' il segnale. Si toglie il livello, si lascia la scala. E la
regola vive **nello strato feature**: `player_match` e `team_match` restano
grezzi, la trasformazione e' invertibile (`x = (x_rel + 1) * m_s`, con un test
che ricostruisce), e un test verifica che nessuna colonna `_rel` sia scesa nel
derivato.

**Esito su 19 candidate: 8 grezze ammesse, 6 risolte dalla standardizzazione,
5 no.** Per le ultime cinque — `xg_per_90`, `quota_tocchi_area`, `gol_per_90`,
`tiri_per_90`, `sot_per_90` — la stagione deve entrare come **effetto
esplicito**, che e' l'uscita che la regola stessa prevede.
`richiede_effetto_stagione()` le ritorna: E2 ed E4 lo chiedono al codice, non al
markdown.

**Il risultato che non era previsto: la standardizzazione peggiora la deriva su
8 candidate su 19**, e i meccanismi sono tre, tutti misurati
(`scomposizione_deriva`, che affianca la deriva del **livello** — la media
pesata di campionato — e quella della **popolazione** — la media non pesata fra
i giocatori sopra il pavimento):

1. **sovracorrezione**: `sot_per_90` ha un livello di campionato che scende
   dell'11,3% e un giocatore tipico che scende del 5,2%. Dividere per il primo
   toglie piu' di quanto ce ne sia nel secondo. **La caduta dei tiri in porta non
   e' distribuita uniformemente sui giocatori**, ed e' un fatto sul gioco.
2. **versi opposti**: su `quota_tocchi_area` il riferimento scende e la media fra
   i giocatori sale del 10,2% — la deriva va da 10,2% a 13,9%. Il verso opposto
   pero' **non basta da solo**: `minuto_medio_uscita` va in verso opposto e
   migliora, perche' il suo riferimento si sposta dell'1,1%. Serve la condizione
   **doppia**, e un test la verifica.
3. **errore di grandezza**, ed e' il caso piu' istruttivo. Per le tre quote di
   esposizione `somma(num)/somma(den)` **non e' "la quota del giocatore tipico"**:
   e' la quota media su tutta la **rosa convocata**, cioe' `11/rosa` per
   `quota_titolare` — 0,272 contro 0,490 di media fra i giocatori. Standardizzare
   importa nella feature la deriva delle **rose**: `quota_titolare` passa da 2,4%
   grezza a 12,2% standardizzata. Restano grezze, e possono.

> **Ne segue la lezione operativa: standardizzare non e' gratis e non e' un
> riflesso.** La guardia `verifica_standardizzazione(feat, colonne)` **misura** e
> non guarda il suffisso — una grezza ferma passa, una `_rel` che si muove viene
> fermata — e un test le inietta un gradino del 20% in una colonna `_rel` sana per
> dimostrare che se ne accorge.

**Le due soglie sono dichiarate prima, non ricavate dopo** (vincolo 1 applicato a
una soglia, come gia' fatto per l'80'; un test vieta `argmax`/`idxmax`/`quantile`
nel modulo e pretende che siano costanti letterali):

- **`SOGLIA_DERIVA = 5%`** — sotto la piu' piccola deriva reale gia' misurata nel
  repository (i tiri in porta per squadra-partita, -9,2%) e molto sopra l'errore
  di campionamento di una media di campionato su 17.000 righe.
- **`SOGLIA_QUALIFIER = 1,5`** sul rapporto max/min della frequenza per evento —
  oltre il quale il movimento non e' piu' compatibile con cio' che il *gioco* ha
  fatto (`Clearance` +48% e' il massimo mai misurato). I due casi noti di
  dizionario cambiato stanno a 17x (`StandingSave`) e 30x (`OtherBodyPart`):
  **non e' un numero delicato**.
- **`MIN_MINUTI_DERIVA = 450`** (cinque partite) e' il pavimento di esposizione
  delle **medie**, non del riferimento, che usa tutto. Non e' un dettaglio: **6
  candidate su 19 cambiano verdetto** fra i quattro pavimenti provati, in
  entrambe le direzioni. Solo `gol_per_90`, `xg_per_90` e `quota_tocchi_area`
  stanno oltre la soglia ovunque; `sot_per_90` e `tiri_per_90` ballano e restano
  **non risolte** per prudenza.

**I tre corollari sono test, non buone intenzioni:**

- **Il gate sui qualifier** (`verifica_qualifier`) chiede presenza in tutte e
  cinque le stagioni e rapporto sotto soglia. **E' necessario e non
  sufficiente**: il controllo sufficiente sarebbe l'id numerico, che
  `acquisition/whoscored/main.py:432` butta via. **Nessuna candidata di oggi usa
  qualifier**, e non per virtu': `events_slim` non porta `qualifiers`, quindi una
  feature sui piazzati vuole una rilettura dei 1.889 CSV — costo di E4. Un test
  costruisce una candidata finta che dichiara `StandingSave` e pretende che venga
  fermata, perche' altrimenti "nessuna usa qualifier" potrebbe voler dire "la
  guardia non guarda niente". `CornerTaken` (1,08) e `FreekickTaken` (1,07)
  passano: la macchina sa dire anche di si'.
- **Le 72 colonne mai valorizzate** restano fuori, e **la garanzia non e' la
  disciplina ma l'impossibilita'**: `io_events` tiene ~60 colonne su 259 e
  nessuna delle 72 e' fra quelle. Un test lo verifica su `ALL_COLS`, cosi' che
  allargarlo faccia scattare la guardia. **Porta inviolata, gol subiti e
  precisione dei passaggi si derivano** (`derivazioni()`), e la misura di presenza
  e' "ne' nullo ne' `False`": un test verifica che sui dati veri `notna()` dica il
  contrario del vero.
- **La guardia sulla deriva** e' descritta sopra.

Altre due cose che il blocco porta con se':

- **Ogni candidata e' un rapporto `num/den` dichiarato**, non una colonna. E' cio'
  che rende il riferimento di campionato la **stessa grandezza** del valore
  individuale: `somma(num)/somma(den)`, non la media delle medie individuali, che
  peserebbe uguale chi ha giocato 90 minuti e chi ne ha giocati 3.000. Un test
  verifica che i due numeri siano davvero diversi invece di assumerlo.
- **La riga e' la tripla `(stagione, playerId, teamId)`**, la stessa granularita'
  dell'aggancio di E0. I denominatori di squadra si **contano** (l'Atalanta ha 35
  partite, e un test lo pretende): con 38 ogni quota di esposizione sarebbe
  sbagliata proprio dove la perdita alla fonte non e' casuale.

**Cinque cose lasciate aperte di proposito**, in fondo al report: il riferimento
giusto per le quote di esposizione; il fatto che `xg_per_90` abbia un problema in
piu' degli altri quattro (**cinque fit sono cinque modelli, non cinque livelli**,
e un effetto di stagione lo copre solo se la differenza e' un'intercetta — non
verificato); la stabilita' della posizione, che non e' un rapporto e vuole
un'altra forma; il passaggio da `playerId` a `giocatore_id`, che e' una decisione
di E2; e `quota_presenze`, che ha il calendario intero al denominatore anche per
chi arriva a gennaio.

### Fase 9 — coda di E0: il residuo lato WhoScored ha nomi e minuti ✅

`data/mapping/aggancio_ws_non_agganciati.csv` + due sezioni nuove del report di
E0, da `multistagione.residuo_whoscored()` e `corrispondenza_residui()`.

**Finche' `ws_non_agganciati` era un conteggio (0-5 per stagione) si leggeva come
"quattro comparse". I minuti dicono altro**: nel 2023-24 il piu' grosso ne ha
**2.145**, cioe' circa 24 partite intere, e nel 2024-25 ce n'e' uno da 1.178. In
quota dei minuti di stagione il residuo resta sotto lo **0,4%** ovunque — non
sposta nessuna media, ed e' per questo che era passato inosservato — ma sono
righe di `player_match` **senza bersaglio**, cioe' il difetto che E2 avrebbe
subito in silenzio.

- **La colonna `ws_non_agganciati` gia' pubblicata SOTTOSTIMA**, trovato da un
  test che pretendeva l'uguaglianza fra i due conteggi. Sottrae insiemi di
  `playerId` **ignorando la squadra**: `Maxime Lopez` nel 2023-24 gioca 2 partite
  al Sassuolo (agganciato) e 19 alla Fiorentina (non agganciato — e' li' che
  avviene la collisione con `Arthur Melo`), quindi il Sassuolo lo assorbe e
  **nasconde 884 minuti dietro un aggancio fatto su 2**. La colonna non e' stata
  toccata: risponde a "quante persone", E2 ha bisogno di "quante righe". Il test
  ora blocca la disuguaglianza nel verso giusto, e un secondo test pretende che
  **tutto** lo scarto si spieghi col cambio di squadra.
- **I due residui non sono indipendenti, e non era previsto.** Ogni irrisolto dei
  voti ha, nella stessa squadra e stagione, una riga WhoScored non agganciata con
  **lo stesso identico numero di presenze**: `Stryger Larsen` (11) contro
  `Jens Stryger` (11), `Arthur Melo` (33) contro `Arthur` (33), `Kasa` (8) contro
  `Lior Kassa` (8). **8 su 8.**
- **Non risolto, e la ragione e' misurata.** La regola "stessa squadra, stesse
  presenze" **non e' una chiave**: `Akinsamiro` trova **due** candidati a 1
  presenza nell'Inter 2023-24. Sette accoppiamenti su nove sono unici. Applicarla
  d'ufficio sarebbe scegliere, che e' cio' che E0 ha deciso di non fare. **Cio'
  che cambia e' la domanda aperta**: non e' piu' «chi sono questi otto» ma «quale
  regola si adotta, e con quale tasso d'errore».

### Fase 9 — Blocco E2: le presenze ✅ (tre risultati negativi, che sono il contenuto)

`reports/fase9_e2_presenze.md`, da `scripts/run_fase9_e2.py`; moduli
`sot/squalifiche.py`, `sot/distinta.py`, `sot/impiego.py`, test
`tests/test_fase9_e2.py` (29, di cui 5 sono la coda). **Nessuna richiesta di rete.** **Nessun numero
pubblicato e' cambiato**, verificato rieseguendo: `run_phase1.py` ridà
4.034 / 4.432 / 3.637 / 5.105 su 562.672 eventi, `run_phase5.py` ridà Como 4.34 e
5.03 / 191 / [151, 240].

> **Il limite vale per ogni numero del blocco: gli infortuni non sono nei dati.**
> Sono la componente piu' grossa dell'assenza, e il tetto raggiungibile qui e'
> percio' molto piu' basso del divario oracolo.

| | esito |
|---|---|
| squalifiche come sottrazione di presenze | **−1,9%** del divario oracolo: **peggiorano** |
| predittori d'impiego da dati evento | **+0,20%**, sotto l'MDE di **1,53%** |
| numero di maglia | nessun contributo, e la versione utile **non e' costruibile** |
| il cartellino come **predittore** (coda) | **±0,03%** con MDE **0,04-0,12%**: **confutato** |
| la regola delle squalifiche in se' | **verificata**: 96-99% contro baseline 13-16% |
| pavimento di esposizione a zero | **confermato da una misura**, non da un'opinione |

**Le squalifiche non chiudono il divario: lo allargano, e anche da oracolo.**
Conoscendo i cartellini della stagione bersaglio, sottrarre le giornate peggiora
il MAE dell'1,9%. **Il perche' e' misurato**: chi prende squalifiche e' chi gioca
— cinque ammonizioni non le accumula un panchinaro — e su quei giocatori il
modello d'asta **gia' sottostima** le presenze di 6,0 (21,2 attese contro 27,2
osservate), mentre sovrastima di 5,9 chi non ne prende. Togliere altre giornate a
una previsione gia' troppo bassa allontana.

> **L'inversione che il meccanismo suggeriva — il cartellino non e' una presenza
> in meno, e' il segnale che quel giocatore gioca — E' STATA PROVATA E NON
> REGGE.** Vedi la coda qui sotto. La lettura del meccanismo resta valida; la sua
> conseguenza operativa no, e **non e' una pista aperta in nessun blocco**.

- **La regola in se' regge, ed e' falsificabile senza modelli**: se un giocatore
  e' squalificato non deve comparire fra i convocati. Accordo **96,2-99,4%** sulle
  squadre col calendario intero, contro un baseline — le stesse persone nelle
  giornate in cui **non** sono squalificate — del **12,6-15,6%**.
- **Il residuo ha una causa cercata, non addotta**: l'accordo grezzo scende al
  91,4% nel 2021-22, e **17 errori su 20** cadono su squadre a cui mancano
  partite, che sono solo il 42,9% delle righe. `team_match_idx` numera le partite
  **presenti nei dati**, quindi `idx + 1` scavalca la giornata di squalifica.
  Difetto dell'indice, non della regola.
- **Il taglio delle squalifiche NON e' quello dei minuti.** Le 85 espulsioni del
  2025-26 tolgono 65 uomini dal campo, ma per le squalifiche contano tutte quelle
  a **giocatori**, panchinari inclusi: il numero e' **68**. Un test lo blocca.
- **Due fonti per i cartellini, misurate una contro l'altra** (vincolo 7): le
  **espulsioni concordano al 98-99%**, le **ammonizioni solo all'85-93%** e la
  fonte dei voti ne conta sistematicamente di piu'. Parte e' il buco
  dell'archivio WhoScored — l'accordo e' peggiore nelle due stagioni incomplete —
  ma **non tutto**: nel 2023-24, che e' completo, restano 42 ammonizioni di
  scarto. **Causa residua non identificata e non ipotizzata.**
- **La durata dell'espulsione non e' nei dati**: vale 1 giornata come **limite
  inferiore**, con gli scenari a 2 e 3 riportati accanto (997 / 1.356 / 1.715
  giornate in tutto).

**Lo strato distinta costa 0,3 secondi**, ed e' misurato e non sperato:
`JerseyNumber` e `CaptainPlayerId` stanno nella **stessa lista di qualifier** da
cui `minutes.squads()` gia' estrae `PlayerPosition`, presenti sul **100%** delle
3.778 righe `FormationSet` di tutte e cinque le stagioni, con lunghezza sempre
allineata a `InvolvedPlayers`. I piazzati di E4, che vogliono `qualifiers` sugli
eventi normali, costerebbero invece una rilettura dei 1.889 CSV.

- **Le 11 triple con due numeri si risolvono con la PRIMA DISTINTA**, non con la
  moda pesata sui minuti: la moda userebbe i minuti della stagione per costruire
  un predittore il cui unico pregio e' di esistere **prima** che quei minuti siano
  giocati. Sarebbe il vincolo 1 violato nel punto esatto in cui la feature vale.
- **La fascia `1/12/22` non e' la fascia dei portieri.** La **1** e' portiere nel
  **100%** dei casi, la **12** nel **18%**, la **22** nell'**8%**; e solo il 35%
  dei portieri porta uno di quei tre numeri. **La fascia non e' stata
  ridefinita** — lo si e' scoperto *dopo* aver dichiarato la partizione, e
  cambiarla adesso sarebbe adattarla al campione su cui poi la si valuta.
  **L'eterogeneita' e' il risultato**, e un test blocca sia il fatto sia la
  partizione.
- **1.013 triple su 3.972 (25,5%) non hanno NESSUN ruolo**: sono i convocati mai
  scesi in campo, `role_code == 5` in ogni distinta. **Tutte e 1.013 hanno un
  numero di maglia.** E' l'argomento a favore della feature detto nel modo piu'
  stretto possibile.
- **Il capitano e' sfasato di una stagione**, e lo sfasamento e' **parte della
  definizione**: la fascia di t contro le presenze di t misurerebbe una
  conseguenza del giocare e la chiamerebbe causa.

**Il difetto che rende inutilizzabile la versione interessante della maglia, ed
e' il risultato metodologico del blocco.** Il numero e' assegnato in agosto,
quindi in teoria e' noto anche per chi al nuovo club non ha storia — ed era tutto
l'argomento. Ma **la nostra unica fonte del numero e' la distinta di una
partita**: chi non viene mai convocato non ha nessuna distinta. Misurato sulle
quattro transizioni, fra i quotati con una distinta in t+1 le presenze medie sono
**19,1-19,3**, fra quelli senza **0,0-0,3**. **La sola disponibilita' della
feature e' la risposta.** Si usa quindi il numero di t-1, e il costo cade proprio
sul caso che si voleva coprire. Un test blocca il leakage.

> Il numero d'agosto **sarebbe acquisibile** — lo pubblicano i club e sta nei
> listoni — ma non e' nel repository. E' una domanda aperta **con una risposta
> nota**, non un limite dei dati evento.

**La valutazione, sulle stesse quattro transizioni e sulle stesse 2.678 righe del
modello d'asta** — 61,42 e 5,56 riprodotti, quindi il campione e' lo stesso:

| variante | MAE | quota del divario |
|---|---:|---:|
| modello completo | 61,42 | 0,00% |
| impiego (senza maglia) | 61,32 | **+0,20%** |
| impiego + maglia | 61,32 | +0,19% |
| presenze note (oracolo) | 5,56 | 100% |

- **La potenza e' dichiarata**, come in 6D: differenza appaiata 0,110 di MAE,
  errore standard 0,306, **t = 0,36**, MDE a potenza 80% pari al **1,53% del
  divario**. Il test **non** avrebbe visto un effetto sotto l'1,5%: esclude
  effetti grandi, non effetti piccoli, e va letto cosi'.
- **Perche' non aiuta e' leggibile**: il modello d'asta usa gia' le presenze
  passate del giocatore, e `quota_titolare`, `quota_convocato`, capitano e ruolo
  instabile sono un altro modo di dire la stessa cosa. E' il meccanismo della
  Fase 2 — i predittori evento gia' coperti dagli effetti attacco/difesa — su un
  bersaglio diverso. Sulle presenze il MAE e' 9,906 contro 9,904, cioe' identico;
  la correlazione sale da 0,438 a 0,461 e non basta.
- **Il pavimento di esposizione a zero e' confermato da una misura**, ed e'
  monotona: **+0,20% a zero, −0,83% a 450, −1,15% a 900, −5,07% a 1.800**.
  Addestrare sui soli giocatori con molti minuti rende il modello peggiore
  proprio dove il bersaglio vive. In E1 il pavimento proteggeva le medie; qui i
  pochi minuti **sono** il bersaglio, non la coda.
- **La maglia dove dovrebbe servire**: sui giocatori al primo anno nel club
  migliora di 0,03 di MAE, su chi era gia' nel club **peggiora** di 0,06. Segno
  previsto, grandezza indistinguibile da zero, entrambi molto sotto l'MDE.
  **Coerente con l'ipotesi e non una conferma.**

> **Trappola per le sessioni future.** I tre risultati negativi sono il contenuto
> del blocco e **non vanno "sistemati"**. In particolare non va ritoccata la
> sottrazione delle squalifiche finche' il numero diventa positivo: il segno e'
> spiegato da un meccanismo misurato, e cambiarlo cancellerebbe la spiegazione.
> La strada che i dati indicano e' l'inversione scritta sopra.

**Quattro domande aperte** (erano cinque: il cartellino come predittore e' stato
chiuso dalla coda), in fondo al report: il numero di maglia **d'agosto** dalla
fonte giusta (unico modo di provare l'argomento per cui la feature esisteva); le
42 ammonizioni di scarto del 2023-24 — **per i punti fantacalcio la fonte dei voti
e' definitoria e non una candidata**, quindi lo scarto e' un problema di WhoScored
da spiegare, non una scelta da fare; la durata vera delle espulsioni; gli
infortuni, che non sono in nessuna delle due fonti acquisite.

### Fase 9 — coda di E2: l'inversione del cartellino, provata e confutata ✅

Quarta sezione di `reports/fase9_e2_presenze.md`, da `impiego.contributo_cartellini`,
`deriva_cartellini` e `ridondanza_cartellini`; 5 test nuovi in
`tests/test_fase9_e2.py` (29 in tutto). **Nessuna richiesta di rete, nessun numero
pubblicato cambiato** — un test verifica che il 61,32 e lo 0,196% di E2.4 non si
muovano, cioe' che il join delle colonne nuove non abbia perso o moltiplicato righe.

**`tasso_cartellini` NON era nel set di E2.4**: `FEATURE` sono cinque colonne e
nessuna e' un cartellino. L'inversione non era ne' confermata ne' confutata, era
**non provata** — ed e' il motivo per cui la coda si e' fatta subito invece di
aspettare E3/E4, dove per giunta non c'entrava: e' un predittore di **presenze**,
e E3 riguarda portieri e difese.

| variante | divario chiuso | t appaiato | MDE |
|---|---:|---:|---:|
| impiego (E2.4, riferimento) | 0,196% | — | — |
| + cartellini (conteggio) | 0,194% | −0,10 | 0,074% |
| + cartellini (tasso) | 0,193% | −0,25 | 0,040% |
| + cartellini (entrambi) | 0,220% | +0,56 | 0,120% |
| + conteggio `_rel` | 0,193% | −0,13 | 0,079% |
| + tasso `_rel` | 0,204% | +0,22 | 0,099% |

- **La potenza qui non e' una scusa, e' l'argomento.** In E2.4 l'MDE valeva
  l'1,53% del divario e il negativo escludeva solo effetti grandi. Qui il
  confronto e' **appaiato contro un modello quasi identico** — cambia una colonna
  — quindi la varianza della differenza e' minuscola e l'MDE scende a
  **0,04-0,12%**. Il test vedrebbe effetti **dieci volte piu' piccoli** di quelli
  che E2.4 poteva vedere, e non ne trova nessuno.
- **Il nulla non e' ridondanza, ed e' la misura che rende la confutazione forte
  invece che ambigua** (`ridondanza_cartellini`). Il **conteggio** e' in buona
  parte gia' nel set (R² **0,41** sulle tre quote, corr 0,64 con
  `quota_minuti_prec`): da solo, il suo nulla si spiegherebbe con la ridondanza,
  che e' il meccanismo della Fase 2. Il **tasso** no: R² **0,021**, quasi
  ortogonale. Porta informazione che il set non ha, e non serve lo stesso.
- **Il gate di E1 non si chiude e non e' stato aggirato**: deriva 17,0% e 12,4%
  grezze, 7,2% la `_rel` del tasso, contro una soglia del 5%. Quindi si sono
  provate **entrambe le forme**, e l'esito coincide: la conclusione non dipende da
  una scelta di standardizzazione che i dati non giustificano.
- **Il conteggio non e' un rapporto**, e la conseguenza e' dichiarata invece che
  nascosta: il suo unico denominatore possibile e' il numero di giocatori, quindi
  il riferimento coincide con la media fra i giocatori e la sua `_rel` ha media
  **esattamente zero per costruzione**. Non e' una candidata che passa il gate,
  e' una colonna resa degenere — con un test che lo blocca.
- **La deriva di una `_rel` si legge su `rel + 1`, non su `rel`.** Su una serie
  centrata vicino allo zero `(max-min)/|max|` e' dominata dal denominatore e
  restituisce 115% dove la deriva vera e' 7,2%. Trappola trovata qui.
- **La fonte dei cartellini e' quella dei VOTI, dichiarata** (`FONTE_CARTELLINI`):
  per i punti fantacalcio e' **definitoria** — ha prodotto il malus dentro il
  bersaglio — e sta gia' su `giocatore_id` senza aggancio di mezzo. WhoScored
  resta il controllo indipendente di `squalifiche.py` (vincolo 7).

> **Trappola per le sessioni future.** L'inversione e' **chiusa**, non aperta. Non
> va riaperta in E3 ne' in E4, e non va "sistemata" ritoccando la forma della
> feature finche' un `t` supera 2: sarebbe la ricerca sugli otto predittori della
> Fase 2 rifatta su un altro bersaglio, e con un MDE dello 0,04% il margine per
> illudersi non c'e'. Cio' che resta vero di E2.1 e' il **meccanismo** (chi prende
> cartellini gioca di piu', e per questo la sottrazione allontana), non la sua
> conseguenza operativa.

### Fase 9 — Blocco E3: la difesa ✅ (quattro strumenti che funzionano, una verifica che li boccia)

`reports/fase9_e3_difesa.md`, da `scripts/run_fase9_e3.py`; modulo `sot/difesa.py`,
test `tests/test_fase9_e3.py` (27). **Nessuna richiesta di rete.** **Nessun numero
pubblicato e' cambiato**, verificato rieseguendo: `run_phase1.py` ridà
4.034 / 4.432 / 3.637 / 5.105 su 562.672 eventi, `run_phase5.py` ridà Como 4.34 e
5.03 / 191 / [151, 240].

| | esito |
|---|---|
| E3.1 modello di squadra sui **gol** | **funziona**: batte il baseline migliore per **t = 5.52** |
| E3.2 porta inviolata come probabilita' | **funziona**: pendenza **1.044 ± 0.083**, Brier 0.1899 vs 0.1992 |
| E3.3 voto della linea condizionato | **effetto reale**: −0.243 di voto sui difensori (p10→p90), t = −22.5 |
| E3.3 sui **portieri** | **segno OPPOSTO** (+0.0795, t = +3.44), e non era previsto |
| E3.4 correlazione dentro la linea | misurata: **0.261**, e il segno del suo effetto **si inverte** |
| **verifica sui portieri** | **FALLISCE**: 0.465 → 0.435, precisione resta **0** |

**Il risultato del blocco e' che la causa data per identificata non regge.** Il
blocco del modello d'asta scriveva che i punti di un portiere dipendono dalla
difesa della sua squadra e che quel modello non la guarda. **La prima meta' e'
vera** — E3.2 e E3.3 la misurano — **ma la seconda non e' la spiegazione**: dare al
modello la difesa della squadra, con un modello di squadra validato per conto suo,
**peggiora** l'ordinamento dei portieri.

- **Gli autogol: `team_match.goals` NON e' il punteggio.** `shots.shots_mask` li
  esclude dai tiri (giusto per i tiri in porta, sbagliato per i gol subiti), quindi
  un autogol non compare da nessuna parte. L'attribuzione e' **verificata, non
  assunta**: l'evento `Goal` con `isOwnGoal` porta il `teamId` di chi lo **subisce**.
  Ricomposto cosi', il punteggio coincide con `matches.json` su **3.778/3.778** in
  entrambe le direzioni, contro 3.628 ignorando gli autogol. `matches.json` porta il
  punteggio **dichiarato**, non ricostruito: e' cio' che rende la verifica una
  verifica. Un test blocca sia l'accordo sia il fatto che senza autogol non torni.
- **Sui gol il modello si giustifica anche sull'accuratezza, e sui tiri no.**
  t = 5.52 contro il baseline migliore; nella Fase 2, stesso confronto e stessa
  procedura, valeva t = 1.86. **Non e' un modello migliore: e' un bersaglio piu'
  facile da distinguere** — i gol dipendono dall'avversario molto piu' dei tiri in
  porta, che sono in gran parte "quanto tira questa squadra". La lezione sulla
  calibrazione della Fase 4 si ripete piu' netta: i baseline informativi stanno a
  0.553 e 0.535 con z sotto −11.
- **La validazione NON e' stata ereditata**, ed e' il punto metodologico: media tre
  volte piu' bassa, 28% di zeri, dispersione diversa. PIT p = 0.773, zeri osservati
  27.7% contro 28.9% attesi (ed e' il controllo che conta, perche' la porta
  inviolata **e'** lo zero). **I gol non sono sovradispersi** (var/media 1.03, `r`
  NB2 al massimo): per questo Poisson e NB2 danno lo stesso numero, **misurato**.
- **Il walk-forward e' dentro la stagione, non attraverso**: le squadre cambiano, e
  un'emivita di 150 giorni attraverso l'estate darebbe a settembre un training
  fatto di maggio.
- **Il voto del portiere e' relativo all'ATTESA**, ed e' il fatto non previsto del
  blocco: su una difesa attesa **debole** il portiere prende un voto base piu'
  **alto** (para di piu'), ma a **gol subiti osservati** il voto scende
  (−0.141, t = −18.7). I due segni opposti sono la firma di quel meccanismo, e un
  test li pretende entrambi cosi' che non se ne possa "correggere" uno solo.
- **La correlazione dentro la linea e' 0.261 ed e' genuina co-variazione di
  giornata**: al netto del giocatore passa da 0.263 a 0.261, cioe' non si muove. Se
  fosse "le difese forti hanno difensori bravi" sarebbe crollata, perche' quella
  parte e' gia' dentro `mu` e verrebbe contata due volte.
- **Il segno dell'effetto della correlazione SI INVERTE**, e cercarlo solo sotto le
  soglie avrebbe dato la conclusione sbagliata: sotto 6,60 di voto medio di linea
  aumenta il bonus atteso (fino a +6 punti di stagione), sopra 6,90 lo riduce (fino
  a **−8,8**). Il meccanismo e' la forma della scala: le fasce sono convesse
  crescenti (−1/+1/+3/+6), quindi la varianza aiuta **finche' non si e' dentro
  l'ultima**, che non ha nulla sopra di se'. Inversione intorno a 6,7. Un test
  pretende **entrambi** i segni.
- **La frequenza storica grezza e' un estimatore degenere** e sta in tabella per
  mostrarlo: `p = 0` esatto per chi non ha ancora tenuto la porta inviolata, log-loss
  1.189 contro 0.606 della versione smorzata, pendenza non identificabile. Il
  baseline del confronto e' quello **smorzato**, perche' il vincolo 6 chiede un
  avversario serio: batterne uno degenere non dimostrerebbe niente.
- **`paired_t` ritorna `(somma, t)`, non `(t, p)`.** Scambiarli e' silenzioso e
  produce "p" sopra 1. Trappola incontrata qui.

**Perche' la verifica fallisce, ed e' la cosa piu' utile del blocco:**

| soglia presenze attese | portieri | mai in campo | modello | + difesa E3 | sole presenze | **FVM** |
|---:|---:|---:|---:|---:|---:|---:|
| 0 | 258 | 40% | 0.536 | 0.507 | 0.534 | 0.831 |
| 15 | 177 | 37% | 0.720 | 0.623 | 0.714 | 0.869 |
| 20 | 63 | 2% | **0.073** | −0.027 | −0.011 | **0.700** |

1. **La premessa del blocco era falsa per la popolazione che conta.** «Un portiere
   titolare gioca quasi tutto» e' vero per il titolare e falso per i **quotati**: il
   **40%** dei portieri a listino non gioca nemmeno una partita. Fra tutti i
   quotati, ordinare per **sole presenze attese** da' 0.534 contro 0.536 del modello
   intero — **sui portieri il modello e' gia' quasi solo un modello di presenze**.
2. **Fra i probabili titolari non funziona piu' niente**: il modello crolla a 0.073,
   le sole presenze a −0.011, la difesa di E3 a −0.027.
3. **Ma il FVM non crolla: 0.700.** E' il numero decisivo. Il vantaggio del FVM sui
   portieri **non e' sapere chi gioca** (sopravvive dove le presenze sono note) e
   **non e' la forza difensiva della squadra** (e' quello che E3 ha provato).

> **Precisazione sui numeri di riferimento**: il «0 contro 0,667» del modello
> d'asta e' la **precisione sui primi N**, non lo Spearman. Lo Spearman sui portieri
> non era mai stato pubblicato e vale **0.465**. Un test riproduce entrambi i numeri
> pubblicati, cosi' che il confronto non sia con quantita' ricalcolate diversamente.

> **Trappola per le sessioni future.** La verifica negativa **non va "sistemata"**.
> Il segno e' spiegato da un meccanismo misurato — le presenze dominano
> l'ordinamento, e dove non dominano non c'e' segnale nei nostri candidati — e
> ritoccare la sostituzione finche' lo Spearman supera 0.465 cancellerebbe la
> spiegazione invece di trovarne una. **I quattro strumenti restano validi**: non
> dipendono dall'esito della verifica, e sono cio' che il blocco consegna.

**Quattro domande aperte**: (1) **che cosa sa il FVM sui portieri** — la domanda
piu' stretta che il progetto abbia adesso, e non e' ne' le presenze ne' la difesa;
(2) il voto del portiere modellato sui **tiri affrontati** e non solo sui gol
subiti (`sot_conceded` c'e' gia'); (3) il modificatore con `rho` acceso, che **non
e' stato ricalcolato** sulla lista d'asta — `run_asta_2627.py` gira ancora a
`rho = 0`; (4) la forza difensiva delle **neopromosse**, che resta senza stima.

**Due cose portate dentro, e chiuse:** (1) **l'xG non entra nel modello dei gol**,
quindi il problema dei cinque fit non si pone — la parola non compare in
`sot/difesa.py`, e se un blocco futuro volesse metterlo, la verifica che la
differenza fra i cinque fit sia di sola **intercetta** va fatta prima e resta da
fare; (2) **il malus dei cartellini e' alimentato dalla fonte dei VOTI ed e'
definitorio** — `fantapunti.con_fantavoto_lega` lo calcola dalle colonne
`ammonizione`/`espulsione` dei voti, che sono quelle che producono i
`punti_osservati`. **WhoScored non tocca i punti in nessun punto della catena**,
quindi le 42 ammonizioni di scarto del 2023-24 non sono una scelta fra due
candidate ma un difetto di WhoScored da spiegare.

> **Parametrizzazione condivisa**: `TeamModel`, `baselines.*` e
> `validate.walkforward_predict/baselines` hanno ora un parametro `target` con
> default `"sot"`. Le Fasi 1-6 non lo passano e ottengono cio' che ottenevano
> prima; `modificatore.simula_linea` ha `rho` con default `0.0`, **identico bit per
> bit** alla versione precedente. Tre test bloccano i default.

## Convenzioni

- Codice e docstring in **italiano**, come il resto del progetto.
- Coordinate Opta 0-100, tutte le squadre attaccano verso x = 100. Nessun
  ribaltamento necessario.
- Seed unico in `config.SEED`.
- I minuti si calcolano su `expandedMinute`, quindi una partita dura 94-99
  minuti, non 90. E' voluto: evita di gonfiare i tassi per 90.
- Ogni scelta non ovvia va spiegata nella docstring del modulo, con il
  **perche'**, non solo il cosa.
