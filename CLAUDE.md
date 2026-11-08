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

Stato: dalla richiesta dell'utente del **2026-09-03** c'e' la **Fase 16 /
Blocco O1**, cioe' **la prima verifica del progetto in cui la previsione e'
stata scritta prima e l'esito letto dopo**. Non e' una simulazione:
`reports/previsioni_*.csv` sono del 2026-08-30 e il primo dato della 2026-2027 e'
arrivato quattro giorni dopo. **Esito, e le due meta' vanno tenute insieme**: le
previsioni congelate hanno il **CRPS migliore di ogni baseline reale** su
entrambi i bersagli, ma **nessun confronto raggiunge il proprio MDE** su 85
partite tranne quello contro la media di campionato; e la taratura sulle venti
transizioni passate dice che il CRPS assoluto e' **fuori** dall'intervallo
storico mentre il **vantaggio sul baseline e' ordinario** — cioe' l'avvio
2026-27 e' piu' difficile del solito, non e' il modello a essersi degradato.
Prima di quella, dalla richiesta del **2026-08-30**, c'e' **tutta la
Fase 14** — A0, A1, A2, A3, A4 — cioe' **l'aggiornamento automatico della
stagione in corso sui cinque campionati e la previsione di tiri e tiri in porta
su una partita futura**. Il deliverable e' `reports/previsioni.html`; il comando
settimanale e' `scripts/aggiorna_stagione.py`. **A2 ha un esito che va letto
prima di riaprirlo**: la miscela fra prior e partite nuove NON supera il criterio
scritto in anticipo, e cio' che vince sulle prime giornate e' il modello
dell'anno scorso applicato tale e quale. Prima di quella: **fasi 0-5 completate, tutti i blocchi della Fase 6 (6A-6F), il blocco
7A, l'acquisizione WhoScored 2021-2026, la verifica di stabilita' del criterio
di rilevazione, il Blocco 0 della Fase 8 (ricognizione), l'acquisizione dei
voti fantacalcio 2021-2026 e i blocchi E0, E1, E2, E3 (entrambi con la loro coda)
ed E4 della Fase 9 — cioe' **la Fase 9 e' chiusa** — e **tutta la Fase 10**:
R0, R1, R2, la coda R2-bis (calibrazione) e R3. **Il ramo G1 e' chiuso.** Dalla
richiesta dell'utente del 2026-08-11 c'e' anche il **blocco S1 della Fase 11**
(le soglie di tiri in porta del Como 2026-27 partita per partita), e dalla
richiesta del 2026-08-13 **tutta la Fase 12** — V0, V1, V2, V3 e V4 — cioe' il
modello dei TIRI (tentativi totali) per QUALSIASI squadra. **V1 e' il modello che
risponde a quella domanda e batte il baseline migliore per t = 9,63**, il margine
piu' netto che il progetto abbia prodotto; **V4 e' il ponte
`previsione(squadra, avversario, campo)`**, che prima non esisteva per una
squadra qualsiasi. V2 ha provato la gerarchia volume × precisione e **non la
adotta**; V3 ha ritestato gli otto predittori da dati evento e li **scarta per la
terza volta**. Dettaglio ed esiti nella
sezione "Le fasi e i
risultati raggiunti" piu' sotto. Il deliverable e' `README.md`. La Fase 6 e'
descritta in `docs/fasi/prompt_fase6.md`, la Fase 7 in `docs/fasi/prompt_fase7.md`, la
Fase 9 in `docs/fasi/prompt_fase9.md` (che contiene anche le specifiche di E2,
dall'utente il 2026-08-04, e di E4, dall'utente il 2026-08-07).

> **Prima di scegliere dove andare, si legge `docs/fasi/bilancio_fase9.md`.** E' il
> bilancio della fase in una pagina, richiesto dall'utente a chiusura di E4, e
> non e' un elenco di blocchi chiusi: dice che cosa ha funzionato (**una** cosa,
> QI sulle presenze, +1,49%), che cosa e' stato escluso e **con quanta potenza**,
> e qual e' il tetto — 61,42 → 60,59 e' tutto cio' che la Fase 9 ha comprato,
> **il 98,5% del divario delle presenze resta non attaccato e le fonti gia' in
> casa sono esaurite**. Chi riparte da qui senza averlo letto rischia di
> riprovare una delle sette strade gia' escluse.

Il seguito del lavoro e' il piano dati
prodotto da 6F (`reports/phase6_piano_dati.md`), che **richiede dati non
presenti nel repository** ed e' cio' che la Fase 7 va a prendere.

### Due rami aperti, non una coda

Decisione dell'utente del 2026-08-03: il lavoro **non e' una fila**. Ci sono due
rami che non si toccano, e si sceglie a ogni giro quale blocco fare.

| ramo | bersaglio | prossimo blocco | fonte |
|---|---|---|---|
| **Fase 7** (7B → 7C → 7D) | `rho` e l'ancora 4.90, cioe' il **livello** della proiezione SoT di squadra (D1, D2, D5) | **7B** | football-data.co.uk, **da acquisire** |
| **Fase 9** (E0 → E1 → E2 → E3 → E4) | punti stagionali del **giocatore**: impiego, portieri, modificatore | **chiusa** (E0 ✅, E1 ✅, E2 ✅, E3 ✅, E4 ✅). Resta la domanda su **un valore pre-stagione dalla fonte**, che ora sono **tre appaiate**: maglia d'agosto, FVM pulito, rating WhoScored | WhoScored + voti + listoni, **gia' in casa** |
| **Fase 10** (R0 → R1 → R2 → R2-bis → R3) = **G1** | la **distribuzione del risultato**: 1X2, over/under, classifica. Poggia sul modello dei gol di E3.1 | **chiusa** (R0 ✅, R1 ✅, R2 ✅, R2-bis ✅, R3 ✅) | E3 + aggancio Fase 8, **gia' in casa** |
| **Fase 12** (V0 → V1 → V2 → V3 → V4) | i **TIRI** (tentativi totali) per **qualsiasi** squadra, within-season, in due strati (volume + precisione) | **chiusa** (V0 ✅, V1 ✅, V2 ✅, V3 ✅, V4 ✅) | `team_match` delle cinque stagioni, **gia' in casa** |
| **Fase 13 = G2** (terne ✅ → M1 ✅ → acquisizione ✅ → modello ✅) | i **GOL** sui **cinque** campionati top europei, piu' le metriche avanzate da dati evento | **chiusa nei quattro blocchi**: 8.884 partite acquisite, 25 tabelle costruite, **il modello dei gol TRASFERISCE** (t 3,1-5,4 in 4 campionati su 5) | WhoScored 5 campionati x 5 stagioni, **gia' in casa** |
| **Fase 14** (A0 → A1 → A2 → A3 → A4) | la **stagione IN CORSO**: aggiornamento settimanale automatico dei cinque campionati, e previsione di **tiri e tiri in porta** su una partita futura a scelta | **chiusa** (A0 ✅, A1 ✅, A2 ✅, A3 ✅, A4 ✅). Il deliverable e' `reports/previsioni.html` | WhoScored 2026-2027, **da acquisire ogni martedi'** |
| **Fase 15** (T1 → C1 → P1) | il **totale di partita**, il **calendario** della stagione in corso e la pagina a giornata | **chiusa** (T1 ✅, C1 ✅, P1 ✅). Il deliverable e' `reports/previsioni.html` | walk-forward di V1 **gia' in casa**; il calendario da **WhoScored + Wikipedia**, acquisito |
| **Fase 16** (O1) | la **verifica prospettica**: previsione scritta prima, esito letto dopo, sulle prime due giornate 2026-27 dei cinque campionati | **chiusa** (O1 ✅). Il deliverable e' `reports/fase16_o1_verifica_prospettica.md` | le previsioni **congelate il 2026-08-30** + i dati arrivati il 2026-09-03, **gia' in casa** |

**La Fase 10 e' il ramo G1, aperto dall'utente il 2026-08-07** con l'ordine
dichiarato **G1 prima di G2**, per tre ragioni di costo: (a) G2 senza G1
comprerebbe dati per un test che non e' ancora stato scritto; (b) il costo di G2
e' sottostimato — tutti e quattro gli altri campionati hanno `whoscored: None` e
`main.py` e' gia' il collo di bottiglia dichiarato; (c) G1 riusa il derivato di
E3, dove `lam_subiti` e' gia' a terra. **La famiglia dell'acquisizione (rating
WhoScored, FVM e maglia d'agosto) e' rimandata, non esclusa.**

**Nessuno dei due produce ingressi dell'altro**, ed e' il motivo per cui sono
paralleli: 7B porta una colonna SoT a granularita' squadra-partita con una
definizione **non Opta**, che il vincolo 7 obbliga a tenere separata; la Fase 9
lavora su player-match Opta, gia' verificati identici al flag nativo su tutte e
cinque le stagioni. Tirare la fonte tabellare dentro il ramo giocatore
aprirebbe l'obbligo di riconciliazione di 7C senza aggiungere capacita'.

Le tre direzioni **G1-G3** in fondo a `docs/fasi/prompt_fase9.md` (risultato, altri
campionati, scouting) chiedevano che la Fase 9 avesse dei blocchi chiusi: con E4
la Fase 9 **e' chiusa**, quindi la condizione e' soddisfatta. **`[SCELTO
2026-08-07]` l'utente ha aperto G1**, cioe' la Fase 10, con l'ordine dichiarato
G1 → G2; **G2 non e' aperta** e ha una condizione bloccante di autorizzazione
(vedi la sezione R0). **Attenzione a G3 (scouting)**: la sua condizione era «il modello
batte il FVM», e quel confronto e' stato **squalificato** dall'orologio delle
quotazioni — il concorrente leale e' QI, contro cui il verdetto e' misto. La
condizione va riscritta prima di poterla dichiarare soddisfatta. **Erano
quattro**: la
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

./.venv/Scripts/python.exe -m pytest tests/ -q      # 1.119 test, ~790 s
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
# stesse quattro transizioni del modello d'asta, la coda sul cartellino come
# predittore e il blocco (b) sulla quotazione QI (~4 min). NON tocca la rete.
./.venv/Scripts/python.exe scripts/run_fase9_e2.py

# Fase 9 / Blocco E3: il modello di squadra sui GOL (rivalidato per conto suo),
# la porta inviolata come probabilita', il voto della linea condizionato alla
# forza difensiva, la correlazione dentro la linea, la verifica sui portieri e la
# coda E3.5 sulla compensazione voto/malus
# (~2 min da cache; con --force rifa' il walk-forward dei gol, ~25 s in piu').
# NON tocca la rete.
./.venv/Scripts/python.exe scripts/run_fase9_e3.py

# Fase 9 / Blocco E4: il derivato dei piazzati dai qualifier, npxG e xA, la
# verifica dei cinque fit di xG, il voto base, i bonus, i rigori come
# assegnazione discreta e QI (~35 s da cache; con --force rilegge i 1.889 CSV
# per rifare i piazzati, ~2 min in piu'). NON tocca la rete.
./.venv/Scripts/python.exe scripts/run_fase9_e4.py

# Fase 10 / Blocco R0: il perimetro di cio' che e' validabile. Ruota il
# walk-forward dei gol di E3 da squadra-partita a PARTITA e conta (~5 s, tutto
# da cache). NON tocca la rete e NON stima niente.
./.venv/Scripts/python.exe scripts/run_fase10_r0.py

# Fase 10 / Blocco R1: la congiunta del risultato. Si apre con il controllo di
# casualita' delle partite mancanti alla fonte, poi stima `rho` (dipendenza fra
# i due lati) a marginali FISSATE e ne dichiara la potenza (~1 min; con
# --repliche si cambia la precisione della potenza). NON tocca la rete.
./.venv/Scripts/python.exe scripts/run_fase10_r1.py

# Fase 10 / Blocco R2: 1X2 e over/under, valutati. RPS, log-loss, Brier per
# soglia, calibrazione, contro cinque baseline composti con la STESSA congiunta
# (~1 min). NON stima nessun parametro nuovo e NON tocca la rete.
./.venv/Scripts/python.exe scripts/run_fase10_r2.py

# Fase 10 / coda R2-bis: la calibrazione su 1X2. De-compressione del divario come
# parametro, controllo diretto sui gol, ricalibrazione walk-forward (temperatura,
# Platt, isotonica) e l'identita' di dispersione della classifica (~1 min).
# A differenza di R2 questo blocco STIMA. NON tocca la rete.
./.venv/Scripts/python.exe scripts/run_fase10_r2bis.py

# Fase 11 / Blocco S1: le soglie di tiri in porta del Como 2026-27, partita per
# partita. Il ponte `lambda(Como, avversario, campo)` che non esisteva, P(Over)
# per sei linee, quota di pareggio e guadagno atteso come FUNZIONE della quota.
# Scrive anche reports/fase11_s1_simulatore.html, la pagina locale interattiva
# (~2 min). NON tocca la rete.
./.venv/Scripts/python.exe scripts/run_fase11_s1.py

# Fase 12 / Blocco V1: lo strato del VOLUME. Walk-forward dentro la stagione sui
# tentativi, validazione rifatta da capo contro i quattro baseline, r NB2, PIT,
# copertura, Brier sulle cinque linee, segmenti (~30 s da cache; con --force
# rifa' il walk-forward, ~50 s). NON tocca la rete.
./.venv/Scripts/python.exe scripts/run_fase12_v1.py

# Fase 12 / Blocco V2: lo strato della PRECISIONE e la composizione. Il modello
# binomiale della quota, la marginale composta contro il modello DIRETTO sui
# tiri in porta, il rapporto delle dispersioni (~40 s da cache). NON tocca la rete.
./.venv/Scripts/python.exe scripts/run_fase12_v2.py

# Fase 12 / Blocco V3: gli otto predittori da dati evento, ritestati sui
# tentativi e sulle cinque stagioni. NON ha un modulo proprio: parametrizza
# `predictor_power` su `target` (~10 s da cache; con --force rifa' nove
# walk-forward per cinque stagioni, ~5 min). NON tocca la rete.
./.venv/Scripts/python.exe scripts/run_fase12_v3.py

# Fase 12 / Blocco V4: IL PONTE `previsione(squadra, avversario, campo)`, che e'
# cio' che l'utente ha chiesto. Scrive anche reports/fase12_v4_simulatore.html,
# la pagina locale interattiva per tutte e venti le squadre (~20 s).
# NON tocca la rete.
./.venv/Scripts/python.exe scripts/run_fase12_v4.py

# Fase 12 / Blocco V0: il perimetro del bersaglio TIRI (tentativi totali) e
# l'identita' di dispersione che decide se lo strato della precisione si stima o
# collassa a un numero. NON stima nessun modello predittivo (~1 min; con
# --repliche e --repliche-taratura si cambia la precisione del nullo simulato).
# NON tocca la rete.
./.venv/Scripts/python.exe scripts/run_fase12_v0.py

# Fase 10 / Blocco R3: la classifica. Simula il RESTO di una stagione dalla
# giornata k, data la classifica vera a k — non si simula da zero (R0). Copertura
# e PIT sui punti finali, quattro varianti a confronto (~5 min, Monte Carlo).
# NON stima nessun parametro nuovo e NON tocca la rete.
./.venv/Scripts/python.exe scripts/run_fase10_r3.py

# Fase 13 — accerta le terne (regione, torneo, slug) di WhoScored invece di
# ricavarle a memoria. Porta un controllo positivo (Serie A, gia' accertata) e
# due negativi (nome sbagliato, id inesistenti): senza, un "confermata" non
# significa niente. Usa CHROME, non Firefox. `--dry-run` non tocca la rete.
./.venv/Scripts/python.exe acquisition/whoscored/verifica_terne.py --dry-run
./.venv/Scripts/python.exe acquisition/whoscored/verifica_terne.py

# Fase 13 — il modello dei GOL sui cinque campionati, un fit per campionato e
# MAI poolati (§7.2). Riporta t per riga E per cluster di partita, piu' il MDE
# che distingue "non c'e' effetto" da "non lo vedo" (~2 min). NON tocca la rete.
./.venv/Scripts/python.exe scripts/run_fase13_gol.py

# ---------------------------------------------------------------------------
# Fase 14 — LA STAGIONE IN CORSO. E' l'unico gruppo di comandi che TOCCA LA RETE.
# ---------------------------------------------------------------------------

# L'aggiornamento settimanale: scarica le partite nuove dei cinque campionati,
# raccoglie il CALENDARIO delle partite future (--calendario), rinfresca la
# seconda fonte (Wikipedia, che porta la giornata),
# rigenera i Parquet, aggiorna il manifest e rifa' la pagina delle previsioni.
# `--dry-run` NON apre il browser e NON tocca la rete. Rilanciarlo e' sicuro:
# una partita gia' su disco viene saltata e i derivati si rifanno solo se un CSV
# e' piu' recente dei Parquet.
./.venv/Scripts/python.exe scripts/aggiorna_stagione.py --dry-run
./.venv/Scripts/python.exe scripts/aggiorna_stagione.py
./.venv/Scripts/python.exe scripts/aggiorna_stagione.py --league ITA-serie-a
./.venv/Scripts/python.exe scripts/aggiorna_stagione.py --solo-derivati

# Lo stesso, dal .cmd: e' cio' che lancia l'attivita' pianificata del martedi'
# e anche il modo di lanciarlo a mano. Logga in reports/aggiornamento_auto.log.
scripts\aggiorna_stagione.cmd

# La pianificazione. GIA' REGISTRATA il 2026-08-31: martedi' alle 21:00,
# prima esecuzione il 2026-09-01, stato Ready. Il comando serve a rifarla
# da capo (/F sovrascrive) o su un'altra macchina. Per lo stato:
#   schtasks /Query /TN "Calcio-aggiorna-martedi" /V /FO LIST
# per lanciarla subito: schtasks /Run /TN "Calcio-aggiorna-martedi"
# per toglierla:        schtasks /Delete /TN "Calcio-aggiorna-martedi" /F
schtasks /Create /TN "Calcio-aggiorna-martedi" /XML "scripts\attivita_martedi.xml"

# Fase 14 / A2: il prior dalla stagione precedente, MISURATO su 20 transizioni
# (5 campionati x 4) e due bersagli. ~4 min a --force, secondi dalla cache.
# NON tocca la rete.
./.venv/Scripts/python.exe scripts/run_fase14_prior.py
./.venv/Scripts/python.exe scripts/run_fase14_prior.py --force

# Fase 15 / T1: il TOTALE di partita (la somma delle due squadre). Ruota il
# walk-forward di V1 da squadra-partita a PARTITA e stima `r_tot` sui totali
# osservati (~6 s). NON tocca la rete e NON scrive niente sotto data/.
./.venv/Scripts/python.exe scripts/run_fase15_totale.py

# Fase 15 / C1 — IL CALENDARIO DELLE PARTITE FUTURE. Tocca la rete.
# Prima si ACCERTA che si possa leggere, poi lo si raccoglie: la verifica porta
# un controllo positivo (30 righe di stagione conclusa, tutte gia' su disco) e
# uno negativo (30 righe future, nessuna su disco). Senza, "ho trovato delle
# partite" non significa niente. `--dry-run` non tocca la rete.
./.venv/Scripts/python.exe acquisition/whoscored/verifica_calendario.py --dry-run
./.venv/Scripts/python.exe acquisition/whoscored/verifica_calendario.py

# Il calendario da WhoScored: naviga IN AVANTI e scrive calendario.json, che e'
# un file SEPARATO da matches.json (~4 min per campionato).
./.venv/Scripts/python.exe acquisition/whoscored/scrape_season.py     --season 2026-2027 --league ITA-serie-a --solo-calendario

# La SECONDA fonte: Wikipedia, che porta la GIORNATA — che WhoScored non ha.
# Una richiesta per campionato, cinque in tutto.
./.venv/Scripts/python.exe -m acquisition.wikipedia.scrape_calendario --dry-run
./.venv/Scripts/python.exe -m acquisition.wikipedia.scrape_calendario

# Fase 15 / P1 (era A4): le previsioni dei cinque campionati e la pagina
# autonoma reports/previsioni.html, ora A GIORNATA — si sceglie una partita
# vera dal calendario e si legge il TOTALE delle due squadre (~15 s).
# NON tocca la rete e NON scrive sotto data/. Con --csv esce anche un CSV
# del calendario per campionato, oltre a quello delle coppie.
./.venv/Scripts/python.exe scripts/run_previsioni.py
./.venv/Scripts/python.exe scripts/run_previsioni.py --csv

# Fase 16 / O1 — LA VERIFICA PROSPETTICA. Confronta le previsioni CONGELATE il
# 2026-08-30 con cio' che e' successo nelle prime due giornate. Si apre con una
# GUARDIA: se le previsioni non risultano anteriori ai dati E riproducibili da
# un modello che finisce a maggio 2026, lo script esce con 1 invece di
# pubblicare (~1 min). NON tocca la rete e NON scrive sotto data/.
#
# ATTENZIONE: `run_previsioni.py --csv` riscrive `reports/previsioni_<L>.csv`
# sovrascrivendo e SENZA data nel nome. Le copie datate
# `reports/fase16_o1_congelate_*.csv` sono l'unico artefatto non rigenerabile
# del progetto, e stanno in git per questo.
./.venv/Scripts/python.exe scripts/run_fase16_o1.py

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
                   `r` e tasso base stimati sul solo passato. Dalla Fase 16
                   contiene anche `crps_conteggi`, **l'unica regola di punteggio
                   PROPRIA sui conteggi** del repository: il Brier guarda una
                   linea alla volta, la log-verosimiglianza solo `P(Y = y)`, e
                   l'RPS di `esiti.py` vive sulle tre classi dell'1X2. Sta qui e
                   non nel modulo che la usa perche' una metrica ha un posto
                   solo. `crps_k_max` rende il troncamento un numero
                   **dichiarato** invece di una costante scelta a occhio
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
  quotazioni.py    il listone, e **l'orologio delle sue colonne**. QI e' il prezzo
                   d'asta ed e' il concorrente LEALE; il FVM **non lo e'** — sta
                   sull'orologio di QA, cioe' si muove durante la stagione, e per
                   una stagione passata ne conosce l'esito. `orologio()` e
                   `scarti_di_pagina()` lo misurano con due controlli dichiarati
                   dalla fonte; `COLONNE_PULITE`/`COLONNE_CONTAMINATE` stanno qui
                   e non al punto d'uso perche' e' una proprieta' della FONTE
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
                   ne' False"). **Il gate misura se una colonna si MUOVE, non se
                   corrisponde al proprio nome**: sono due proprieta' diverse e
                   ne controlla una sola. La regola e la prova (`passFreekick`,
                   E4) stanno nella sezione E1
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
                   il risultato: vedi la sezione di E3. Contiene anche la **coda
                   E3.5**: `componenti_portiere` separa voto e malus, e
                   `correlazione_componenti` porta la colonna `corr_totali`
                   apposta per squalificarla — sui totali le due componenti si
                   correlano **attraverso le presenze** e sembrerebbero
                   compensarsi
  impiego.py       Fase 9 / E2 e (b). Il modello d'impiego e la sua valutazione sulle
                   stesse quattro transizioni del modello d'asta. Il pavimento di
                   esposizione e' **zero** ed e' un parametro di E2, non
                   un'eredita' di E1: qui i pochi minuti sono il bersaglio.
                   Contiene anche la **coda**: `contributo_cartellini` prova
                   l'inversione di E2.1 in due forme per due standardizzazioni, e
                   `ridondanza_cartellini` e' cio' che distingue «e' gia' nel
                   set» da «non c'e' segnale» — senza, un nulla e' ambiguo.
                   Contiene anche **(b)**: `quotazione_asta` e `contributo_qi`, la
                   quotazione QI come predittore di presenza. E' l'unica feature
                   del progetto che venga da **t** e non da t-1, ed e' lecito
                   perche' il listone esce prima dell'asta: la guardia e'
                   `COLONNE_LISTONE_AMMESSE`, non il suffisso `_asta`
  voto_bonus.py    Fase 9 / E4. I piazzati **dai qualifier e non dalle colonne
                   omonime**: `passFreekick` e' identica a `passCorner` e non
                   contiene nessuna punizione, e il gate non l'avrebbe fermata —
                   un gate misura se una colonna si e' mossa, non se si chiama
                   come cio' che contiene. Contiene anche `scale_dei_fit`, che
                   chiude la verifica sui cinque fit di xG rimandata due volte
                   (stessa forma, livello che si muove del 15,8%), e i due
                   oracoli separati che hanno corretto il divario dei bonus
  perimetro.py     Fase 10 / R0. **LA DEFINIZIONE DI «PARTITA VALIDABILE», e sta
                   in un posto solo** perche' R1, R2 e R3 la useranno tutti e
                   tre — stessa ragione per cui la definizione di tiro in porta
                   sta in `shots.py`. Non stima niente: ruota il walk-forward dei
                   gol da squadra-partita a **partita** e conta. La condizione e'
                   `elig_casa AND elig_trasferta`, non `or`: un esito 1X2 non e'
                   meta' previsto. Contiene `verifica_esito()`, che mette il
                   punteggio ricomposto da WhoScored contro quello della fonte
                   dei voti (vincolo 7, zero discordanze), e `realizzazioni()`,
                   che e' l'argomento sull'ordine G1/G2 messo in codice invece
                   che solo in prosa: e' un conteggio, non un'opinione.
                   Da R1 contiene anche `casualita_mancanti()`, che chiede se le
                   partite che la fonte non ha manchino a caso rispetto
                   all'ESITO — domanda diversa da quella dell'acquisizione, che
                   riguardava la squadra. Sta qui e non in `risultato.py` perche'
                   e' una proprieta' del perimetro
  risultato.py     Fase 10 / R1. Dalla coppia di lambda alla **congiunta**. Le
                   marginali non determinano la congiunta: moltiplicarle e' gia'
                   l'ipotesi di indipendenza, presa senza dichiararla, e questo
                   modulo la rende un parametro (`rho`, forma di Dixon-Coles,
                   `rho = 0` = indipendenza). **I lambda di E3.1 NON si
                   ristimano**: entrano come dati, altrimenti la validazione di
                   E3 non varrebbe piu' per il modello che R2 usa — un test lo
                   blocca. `verifica_marginali()` e' la verifica falsificabile
                   del blocco, e ha corretto la docstring che la descriveva
  esiti.py         Fase 10 / R2. 1X2 e over/under **valutati**. Non stima niente:
                   `rho = 0` viene da R1, i lambda da E3.1. **La metrica
                   principale e' l'RPS e non la log-loss** perche' l'esito e'
                   ORDINALE — fra `1` e `2` c'e' `X` — e un test lo dimostra su
                   due previsioni che la log-loss non sa distinguere. Ogni
                   baseline e' composto con la **stessa** `risultato.congiunta`
                   del modello: comporre diversamente misurerebbe la
                   composizione invece del lambda. `PAVIMENTO_LAMBDA` e'
                   dichiarato e tocca **una** riga — senza, la log-loss di
                   `media squadra` sarebbe infinita. `dispersione_somma()` e'
                   la misura che ha corretto la spiegazione dell'over/under
  ricalibrazione.py Fase 10 / R2-bis. **L'UNICO modulo della Fase 10 che stima**,
                   e sta separato da `esiti.py` per questo: li' un test vieta
                   `minimize`. Tiene separate due domande che e' facile
                   confondere — **da dove viene** la sotto-sicurezza
                   (de-compressione del divario come parametro `k`, in tre modi
                   dichiarati) e **se si toglie** (ricalibrazione walk-forward).
                   Che la seconda funzioni **non e' una conferma della prima**.
                   Il criterio di adozione (`CRITERIO_ADOZIONE`) e' scritto prima
                   di guardare i numeri e `verdetto()` lo applica meccanicamente.
                   `identita_punti()` porta la domanda al livello di R3 — la
                   classifica si disperde quanto il modello dice? — ed e'
                   verificata su esiti **generati dal modello**, dove la risposta
                   e' nota
  classifica.py    Fase 10 / R3. Simula il **resto** di una stagione dalla
                   giornata k: R0 vieta di simularne una da zero, e la classifica
                   a k entra come **costante** perche' e' la storia. Si estrae
                   prima l'esito con la probabilita' ricalibrata di R2-bis, poi il
                   punteggio **dentro la classe estratta** — e' cosi' che il
                   prezzo di Platt non si paga sui punti. La validazione sono i
                   **punti finali** (venti realizzazioni per stagione), non le
                   probabilita' di scudetto (una). `affidabilita_claim()` porta
                   apposta la colonna `media dichiarata` per squalificarla: e'
                   uguale alla frequenza vera **per costruzione**
  soglie_2627.py   Fase 11 / S1. **IL PONTE `lambda(Como, avversario, campo)` PER
                   IL 2026-27**, che non esisteva: `monte_carlo` dava solo il
                   totale stagionale, con un lambda costante sulle 38 giornate,
                   senza avversario e senza campo. La struttura relativa viene dal
                   modello di squadra, il **livello dall'ancora** (Fase 6A), e la
                   media dei 38 vale l'ancora a precisione macchina — da cui segue
                   che lo **scenario sulle promosse non sposta il livello**, solo
                   la distribuzione fra le partite. `difese_avversari()`
                   **solleva** su una squadra sconosciuta invece di lasciarla
                   scivolare a coefficiente 0 come farebbe `model_team._design`.
                   `verifica_calendario()` e' la guardia che ha **rifiutato** il
                   calendario raccolto dal web, che elencava il Como fra i propri
                   avversari. `identita_circolare()` sta qui per essere
                   **squalificata**: con margine proporzionale il guadagno atteso
                   vale `1/overround - 1` identicamente, su ogni partita e ogni
                   linea, e non contiene una sola informazione sul Como
  volume.py        Fase 12 / V1 (+ la parte che calcola di V3). Lo strato del
                   VOLUME: `TeamModel(target="shots")`, walk-forward **dentro** la
                   stagione come E3, validazione rifatta da capo. E' il modello che
                   risponde alla domanda dell'utente, e **batte il baseline
                   migliore per t = 9,63** — sui tiri in porta valeva 1,86.
                   `predittori_per_stagione()` costruisce le EWM **una stagione
                   per volta**: sul concatenato settembre 2023 userebbe maggio 2023
                   con peso 0,57. `confronto_predittori()` passa `df=None` di
                   proposito — il tetto in campione multi-stagione vorrebbe un fit
                   poolato attraverso l'estate, cioe' cio' che V1 rifiuta
  precisione.py    Fase 12 / V2. Lo strato della PRECISIONE e la composizione.
                   **NON riusa `TeamModel`** ed e' dichiarato: li' la
                   verosimiglianza e' Poisson-log su un conteggio, qui binomiale-
                   logit su `k` successi in `n` prove. `pmf_composta` ha **due
                   strade** — forma chiusa a `rho = 0` e convoluzione
                   beta-binomiale a `rho > 0` — e si rifiuta di usare la
                   scorciatoia dove non vale. `rapporto_dispersioni()` e' la
                   coerenza della gerarchia resa un numero, e la **falsifica**
                   (1,63, IC95 che non contiene 1). Esito del blocco: **la
                   gerarchia non si adotta**
  previsione.py    Fase 12 / V4. **IL PONTE `previsione(squadra, avversario,
                   campo)`**, cioe' cio' che l'utente ha chiesto. Prima non
                   esisteva per una squadra qualsiasi: `soglie_2627` lo aveva per
                   il **solo Como** e il **solo 2026-27**, ancorato a un livello
                   fornito. Qui il livello non serve — la previsione e'
                   **within-season** ed e' l'unica forma validabile.
                   `verifica_squadre()` + `TeamModel(strict_teams=True)` sono la
                   guardia **a due livelli**: una sola all'ingresso si aggira
                   chiamando il modello direttamente. `campo` e' una **stringa**
                   e non un booleano, perche' uno `0/1` si scambia senza rumore.
                   `quota_pareggio` si **importa** da `soglie_2627`, mai
                   riscritta. Da P1 contiene anche **il ponte sul
                   CALENDARIO**: `tabella_calendario()` risponde su una
                   partita vera invece che su una coppia, e ne da' il
                   **totale**. `_r_tot_corrente` e' `_r_corrente` ruotata a
                   partita, con lo stesso vincolo 1; e
                   `RICALIBRAZIONE_IN_PAGINA = False` e' una **decisione
                   dichiarata col suo perche'**, non un'omissione
  tentativi.py     Fase 12 / V0. **IL PERIMETRO DEL BERSAGLIO `shots`** (tentativi
                   totali) e l'identita' che decide lo strato della precisione.
                   Non stima nessun modello predittivo: conta e misura, come R0.
                   `LINEE_TIRI` e `CRITERIO_STRATO2` sono dichiarate prima, e un
                   test vieta `argmax`/`idxmax`/**`quantile`** nel CODICE del
                   modulo — il terzo divieto e' una regola NUOVA e piu' severa di
                   quella di S1. `livello_sbagliato()` sta qui per essere citata
                   contro se stessa: mette a verbale che il `phi = 1,101` gia'
                   pubblicato NON risponde alla domanda dello strato 2, perche' e'
                   la dispersione a livello squadra-PARTITA e mescola rumore di
                   partita, squadra e avversario. `nullo_simulato()` genera il
                   nullo con la sovradispersione di partita dentro: senza, il test
                   sarebbe **garantito di rifiutare**. `taratura_test()` +
                   `mde_da_taratura()` sono cio' che rende leggibile il risultato,
                   e hanno **corretto il MDE** (quello analitico e' ottimistico di
                   un terzo)
  calendario.py    Fase 15 / C1. **IL CALENDARIO DELLA STAGIONE IN CORSO, DA DUE
                   FONTI**, che non sono ridondanti: WhoScored porta URL e
                   `matchId` ma **non la giornata** (si naviga per GIORNO, e la
                   giornata non compare da nessuna parte); Wikipedia porta la
                   giornata ma non gli URL. `mappa_squadre()` riconcilia i nomi
                   in tre passi — esatto, contenimento **se unico**, e poi
                   pretende una **biiezione su tutte** le squadre: una mappa
                   parziale farebbe sparire in silenzio le partite di una
                   squadra intera. Al livello di squadra il nome **non e' una
                   chiave** (Fase 8): `AC Milan` contro `Milan`, `Parma Calcio
                   1913` contro `Parma`. **Non sceglie fra le due fonti dove
                   divergono**: `divergenze()` le mette a verbale (vincolo 7).
                   Da P1 contiene anche **il TURNO**: `data()` legge la data
                   nella forma **accertata** della fonte (italiana, `dic` e
                   non `dec`) e `con_turno()` raggruppa in tre passi
                   dichiarati — la giornata vera, il **contenimento nella
                   finestra di date se e solo se e' unico**, i blocchi di
                   date. La **capienza `squadre/2` e' strutturale e non una
                   soglia**: senza, la Ligue 1 usciva con una «5a giornata»
                   da 12 partite su 18 squadre, perche' i rinvii hanno una
                   data che cade nella finestra di un altro turno. **La
                   deduzione non diventa mai la giornata della riga**:
                   `fonte_giornata` resta `assente` e cambia solo il turno
                   in cui la riga e' mostrata
  totale.py        Fase 15 / T1. **IL TOTALE DI PARTITA**, cioe' la somma delle due
                   squadre, che era la domanda aperta n. 3 di V1 e di V4. La
                   risposta e' che **la congiunta non serve**: `E[X+Y]=E[X]+E[Y]`
                   non richiede ipotesi, quindi `lambda_tot` e' esatto, e cio' che
                   la dipendenza rompe e' la dispersione — assorbita stimando
                   `r_tot` sui totali OSSERVATI invece di ereditarla (83,97 contro
                   20,00 per lato, IC95 del rapporto [3,46, 5,66]).
                   `confronto_indipendenza()` **resta nel modulo** e calcola la
                   convoluzione delle due NB2 per lato: e' l'alternativa scartata,
                   e cancellarla renderebbe la scelta un'asserzione.
                   La rotazione a partita e' quella di `perimetro.partite()`, con
                   la stessa verifica gratuita via `lam_subiti`. **Non scrive
                   niente** (`SCRIVE_SU_DISCO = False`) e un test lo pretende
  prior_stagione.py Fase 14 / A2. **IL PONTE FRA UNA STAGIONE E LA SUCCESSIVA**,
                   che il repository rifiutava per costruzione: tutto e'
                   within-season perche' le squadre cambiano, e la conseguenza e'
                   che a settembre non c'e' niente su cui stimare. Qui il centro
                   della penalita' ridge si sposta dai coefficienti nulli (media
                   di campionato) a quelli di **fine stagione precedente**. Il
                   prior **si scioglie da solo** — la verosimiglianza cresce con
                   `n`, la penalita' no — quindi non c'e' nessun decadimento da
                   sintonizzare, e porta la forza **relativa** e non il livello,
                   perche' `mu` e `gamma` restano non penalizzati. `centra()` non
                   e' cosmesi: senza, lo zero di una neopromossa non sarebbe la
                   media delle altre. **L'esito e' misurato e non e' quello
                   atteso**: la miscela perde, e cio' che vince e' l'anno scorso
                   applicato **tale e quale** (`modello prec`, che era il
                   DIAGNOSTICO del blocco e non il candidato da adottare). Vedi
                   la sezione di A2
  verifica_prospettica.py  Fase 16 / O1. **LA PRIMA VERIFICA DEL PROGETTO IN CUI
                   LA PREVISIONE E' STATA SCRITTA PRIMA E L'ESITO LETTO DOPO.**
                   Non stima nessun modello predittivo: legge le previsioni
                   congelate il 2026-08-30, le rimette accanto ai candidati di
                   A2 e misura. **L'anteriorita' non poggia su un orologio**:
                   `verifica_anteriorita` pretende sia il `mtime` sia che le
                   colonne si RIPRODUCANO da `PS.lam_dal_prior` sul fit della
                   sola stagione precedente — una previsione riproducibile da
                   dati che finiscono a maggio 2026 non puo' contenere
                   informazione sulle giornate 1-2 qualunque sia la data del
                   file. `TOLL_RIPRODUZIONE` e' **derivata dalla `ftol` di
                   L-BFGS-B**, non scelta guardando lo scarto: dentro un
                   processo il re-fit e' bit-identico, fra processi resta
                   `sqrt(ftol)`. `verifica_giornata` tiene separati **tre**
                   esiti che e' facile confondere — assente dalla fonte,
                   **ambigua** (un rinvio elencato a due giornate) e discorde —
                   e solo il terzo e' un disaccordo: tenerne una a caso inventa
                   un errore che e' del codice, ed e' l'errore che la prima
                   stesura ha davvero commesso su `Paris FC-Nizza`.
                   `ripiego_ammesso` non ha una soglia sull'accordo medio
                   (si sceglierebbe dopo aver visto gli scarti): pretende
                   accordo **totale dove la seconda fonte si dichiara completa**
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
  wikipedia/       la SECONDA fonte del calendario, quella che porta la
                   **giornata**. Pacchetto vero come `fantacalcio`.
    target.py      titoli di pagina ACCERTATI (la Liga sta sotto `Primera
                   Division ... (Spagna)`, fuori dallo schema degli altri
                   quattro) e percorsi. NON importa requests
    pagina.py      il parser, funzione pura. Contiene le due trappole di questa
                   fonte: la cella della partita e' TESTO e non due link, quindi
                   `dividi()` prova ogni trattino e tiene solo lo split in cui
                   **entrambe** le meta' sono squadre note (in Ligue 1 c'e'
                   Saint-Etienne); e una partita da giocare mostra l'**orario**
                   dove una giocata mostra il risultato — il discriminante e'
                   il separatore, ed e' **diverso** da quello di WhoScored
    scrape_calendario.py  una sola richiesta per campionato, con attesa
                   crescente sul 429
scripts/  run_phase1..5.py, run_phase6a.py .. run_phase6f.py,
          run_phase7_stabilita.py, run_blocco0.py, run_voti_fantacalcio.py,
          run_aggancio.py, run_modello_asta.py, run_asta_2627.py,
          run_fase9_e0.py, run_fase9_e1.py, run_fase9_e2.py, run_fase9_e3.py,
          run_fase9_e4.py, run_fase10_r0.py, run_fase10_r1.py,
          run_fase10_r2.py, run_fase13_gol.py,
          aggiorna_stagione.py + aggiorna_stagione.cmd + attivita_martedi.xml,
          run_fase14_prior.py, run_previsioni.py + pagina_previsioni.py,
          run_fase15_totale.py, run_fase16_o1.py,
          tiri_in_porta.py
tests/    conftest + 45 moduli
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
  processed/ITA-serie-a/fase9_e4_piazzati.parquet         3.099 righe, la tripla
                   `(stagione, playerId, teamId)` con corner, punizioni, rigori
                   e passaggi chiave **contati dai qualifier**. E' un derivato a
                   se' e non una colonna di `player_match`: sono dati grezzi
                   riletti per uno scopo, non una ricostruzione strutturale
  processed/ITA-serie-a/fase9_e4_assist_tiro.parquet     35.231 righe, il legame
                   passaggio chiave -> tiro. **Il legame non e' nei dati** e
                   questa e' la sua ricostruzione dichiarata (98,9-99,2% dei tiri
                   assistiti); `fase9_e4_assist_qualita.parquet` ne porta il
                   denominatore, contato nella stessa passata invece che in una
                   seconda rilettura dei 1.889 CSV
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
  dell'utente precedente al repository (`scripts/r/Role Modifier.R:5`), scritto su una
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

**Esito del modello: batte l'ignoranza, perde contro QI — e il verdetto e' misto.**

> **CORREZIONE del 2026-08-05.** Questa sezione diceva **«batte l'ignoranza, non
> batte il mercato»**, e il mercato era il FVM. **Quel confronto era con un
> concorrente contaminato** (vedi «L'orologio delle quotazioni» piu' sotto): il
> FVM della pagina archiviata si muove *durante* la stagione. I numeri **restano
> in tabella, marcati** — e' un errore di questo progetto e non si cancella — ma
> il concorrente leale e' **QI**.

| candidato | Spearman | precisione sui primi N |
|---|---:|---:|
| ~~FVM della fonte~~ **CONTAMINATO** | ~~0.811~~ | ~~0.518~~ |
| **quotazione iniziale QI** (concorrente leale) | **0.606** | **0.162** |
| persistenza (anno prima) | 0.451 | 0.211 |
| **modello** | 0.452 | 0.177 |
| media di ruolo | 0.156 | 0.065 |

- **Contro QI il verdetto e' misto, e va riportato misto**: sullo Spearman QI
  vince (0.606 contro 0.452), sulla **precisione sui primi N** vince il modello
  (0.177 contro 0.162). Le due metriche non misurano la stessa cosa — tutto
  l'ordine contro la sola testa, che e' cio' che si compra — e citarne una sola
  darebbe un verdetto netto che i dati non danno.
- **Il modello non supera nemmeno la persistenza** ("l'anno prossimo come
  l'anno scorso"). Tutto il macchinario dei tre fattori con shrinkage non
  aggiunge niente. Con quattro transizioni la differenza non e' distinguibile dal
  rumore, ma il segno e' contrario al modello.
- **Sui portieri**: il modello fa precisione 0 e il FVM contaminato 0.667, ma
  **con QI quel divario non e' misurabile** — QI fa 0.000 o 0.083 a seconda di
  come si sciolgono i pari merito (prezzo intero, pari merito al confine dei primi
  tre in due stagioni su quattro; con 3 posti per 4 stagioni la metrica ha passi
  da 1/12). Sullo **Spearman** il divario invece regge: QI 0.730 contro 0.465.
  La causa che questa sezione dava per identificata — *i punti di un portiere
  dipendono dalla difesa della sua squadra e il modello non la guarda* — **e'
  stata provata da E3 e non regge**.

**Il risultato piu' utile e' dove sta l'errore**: con le presenze note il MAE
crolla da **61.4 a 5.6** (−91%); con i bonus noti scende solo a 52.5. Il voto
base e i bonus sono quasi risolti; il problema e' prevedere **quante partite un
giocatore giochera'**, e quello dipende da cose che nessuna tabella acquisita
contiene — minutaggio atteso, gerarchia di rosa, mercato, infortuni. **Non e' un
difetto di stima, e' un'assenza di dati.**

> **CORREZIONE del 2026-08-07 (Blocco E4).** Il **52.5 e' su un altro campione**,
> e la conclusione che se ne traeva era giusta per la ragione sbagliata. «Bonus
> noti» gira su **2.204 righe** e non 2.678: chi non ha mai giocato in `t` non ha
> un tasso osservato, e quelle 474 righe — **le peggiori**, dove il modello
> predice punti a chi ne fara' zero — cadono. Sulle stesse 2.204 righe il modello
> completo fa **55.01**. E «bonus noti» **non era il bonus**: costruito per
> differenza come `punti/presenze - voto_atteso`, e' l'intero *tasso per
> presenza*, voto compreso — si vede dal fatto che costruendo allo stesso modo
> l'oracolo del voto si ottiene lo stesso identico numero.
>
> I divari veri, con le componenti prese separate e a campione fisso: **voto 1.24
> · bonus 1.44 · entrambi 2.51** contro i **55.86** delle presenze. Il numero
> pubblicato resta riproducibile e resta in tabella con il nome che dice cos'era
> (`tasso per presenza noto`); `scomposizione_errore` ha ora la colonna
> `mae_stesse_righe`, che rende il confronto orizzontale e non verticale.
> **La lettura non cambia — le presenze sono il problema, i bonus no — ma il
> margine di E4 e' il 4% dell'errore, non il 14.5%.**

**Un difetto trovato dai test, e non era piccolo**: `precisione_top` scioglieva i
pari merito nell'ordine della tabella, e il listone arriva ordinato per `QI`
decrescente. Il baseline "media di ruolo" — costante dentro un ruolo — sceglieva
cosi' i giocatori piu' cari e otteneva 0.182 invece di 0.065: **il confronto era
falsato in favore dell'ignoranza**. Ora i pari merito si sciolgono col seme del
progetto.

**Il listone 2026-27 non esiste ancora** (verificato il 2026-08-03: la pagina
dichiara "Dati non disponibili"), quindi **la lista d'asta vera non e'
producibile oggi**. Lo scraper distingue questo caso da un cambio di markup.

> **Trappola per le sessioni future.** Il modello perde contro QI e persistenza,
> e questo e' il contenuto informativo del blocco. **Non va "sistemato"**
> ritoccando lo shrinkage finche' il numero non supera il concorrente: e' lo
> stesso errore che le Fasi 2 e 3 servivano a escludere. Il FVM e' stato tolto dal
> ruolo di concorrente **perche' contaminato, non perche' scomodo** — la misura e'
> riproducibile e vale per chiunque. La strada indicata dai dati resta: attaccare
> le **presenze**, non i bonus. (Collegare il **modello di squadra**, che questa
> sezione indicava come prima cosa da fare, e' stato fatto in E3 e **non funziona
> sui portieri**.)

### L'orologio delle quotazioni — quale colonna e' nota PRIMA della stagione ✅

`quotazioni.orologio()`, `orologio_sintesi()`, `scarti_di_pagina()`,
`COLONNE_PULITE` / `COLONNE_CONTAMINATE`; test in `tests/test_modello_asta.py`.
Sezione 3-bis di `reports/modello_asta.md`. **Nessuna richiesta di rete.**

E' il **gate** da superare prima di usare una quotazione come **ingresso** di un
modello, e non solo come baseline. I cinque listoni sono stati scaricati **tutti
nell'agosto 2026**, una pagina per stagione: quella pagina porta i valori di
agosto di quella stagione, o l'ultimo stato al momento del prelievo?

**Il disegno e' due controlli noti e un soggetto**, e senza i controlli la
domanda non avrebbe risposta: sulla stessa pagina `QI` e' dichiarata dalla fonte
*iniziale* e `QA` *attuale* («un unico valore corrente, non una serie»); il `FVM`
non ha una data dichiarata da nessuna parte. La domanda non e' «il FVM e'
pulito?» ma **«a quale dei due somiglia?»**.

| colonna | listone di t | listone di t−1 | vantaggio di essere di t |
|---|---:|---:|---:|
| `fvm_classic` (SOGGETTO) | **0.804** | 0.441 | **+0.363** |
| `qa_classic` (contaminata, controllo) | 0.802 | 0.430 | +0.372 |
| `qi_classic` (pulita, controllo) | 0.536 | 0.349 | +0.187 |

- **Il vantaggio di essere della pagina di t non e' zero nemmeno per una colonna
  pulita**, ed e' il motivo per cui servono i controlli: la pagina di t conosce il
  **mercato estivo**, quella di t−1 no. Il confronto e' fra colonne, non con lo
  zero. Un test lo blocca, altrimenti «vantaggio > 0» sembrerebbe di per se' una
  prova di leakage.
- **Il secondo taglio non e' confuso dalla qualita' intrinseca delle colonne**,
  perche' entrambi gli scarti sono presi rispetto allo **stesso QI**, sulla stessa
  pagina e sulla stessa popolazione: `FVM − QI` predice l'esito di quella stagione
  a 0.242-0.371 contro 0.206-0.328 di `QA − QI`, cioe' **quanto QA e in tre casi
  su quattro di piu'**. E il FVM assomiglia a QA (0.80-0.90) piu' che a QI
  (0.64-0.75).
- **Cosa e' dimostrato**: non che il FVM sia un valore di fine stagione, ma che
  **non e' uno snapshot pre-stagione**. E' coerente col fatto che un "Fanta Valore
  di Mercato" sia per costruzione ricalcolato in continuo — non un incidente del
  prelievo, ma **cosa la grandezza e'**.
- **Su QI il verdetto e' sostenuto, non provato**: l'unica prova sarebbe una
  pagina scaricata prima dell'inizio di una stagione, e non ne esiste una nel
  repository. Le tre firme concordano, e QI e' comunque la sola quotazione
  davvero disponibile al momento in cui si fa l'asta.
- **Il FVM non esiste affatto per la 2021-2022** (0 valori non nulli): sono quattro
  stagioni, non cinque.

> **Trappola per le sessioni future.** Il FVM **non e' un concorrente leale** in
> nessun confronto fuori campione, e non va rimesso in quel ruolo. Resta
> utilizzabile come descrizione e come baseline **dichiarato contaminato**, ed e'
> per questo che ovunque si chiama `FVM della fonte (CONTAMINATO)`: un test
> pretende che il nome nudo non ricompaia.

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

  > **REGOLA, e vale per ogni blocco futuro: il gate misura se una colonna si
  > MUOVE, non se corrisponde al proprio nome.** Sono due proprieta' diverse e il
  > gate ne controlla una sola. **La prova e' `passFreekick`** (Blocco E4): e'
  > valorizzata in tutte e cinque le stagioni, ha rapporto max/min 1,08 — passa il
  > gate a pieni voti — ed e' **identica a `passCorner` riga per riga**, con
  > intersezione vuota con i `FreekickTaken` veri. Non contiene una sola
  > punizione. Un blocco che si fosse fidato del gate avrebbe pubblicato una
  > tabella di battitori di punizioni dell'ordine di grandezza giusto in cui ogni
  > riga era un battitore di corner, e nessun controllo di quadratura se ne
  > sarebbe accorto.
  >
  > Ne segue che **una colonna nuova va confrontata con una derivazione
  > indipendente della stessa grandezza prima di usarla**, non solo passata al
  > gate. In E4 le derivazioni indipendenti erano i qualifier (`CornerTaken`,
  > `FreekickTaken`) e le booleane dei rigori, e hanno trovato entrambe le
  > trappole: la collisione di `passFreekick` e il fatto che il qualifier
  > `Penalty` marca il rigore e non il rigorista. **E' il vincolo 7 applicato
  > dentro una fonte sola**: due nomi per la stessa grandezza non sono la stessa
  > grandezza finche' non e' misurato che lo siano.
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

> Il numero d'agosto **sarebbe acquisibile** — lo pubblicano i club — ma non e'
> nel repository. E' una domanda aperta **con una risposta nota**, non un limite
> dei dati evento.
>
> **CORREZIONE del 2026-08-07: "e sta nei listoni" era falso, ed e' stato tolto.**
> Verificato decomprimendo il listone 2025-26: **zero** occorrenze di
> `maglia`/`numero`/`shirt`/`number`, e le uniche colonne che la pagina espone
> sono `sq`, `c_qi`, `c_qa`, `c_fvm` e le tre `m_*`. Idem nelle pagine dei voti.
> Il numero **non sta in nessuna delle due pagine gia' acquisite**: la fonte
> sarebbe una terza pagina (le rose di club) che non e' stata individuata. La
> domanda resta aperta e il suo costo e' piu' alto di quanto questa riga
> lasciasse credere.

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

### Fase 9 — (b): la quotazione QI come predittore di presenza ✅ (il primo che passa)

Sezione 5 di `reports/fase9_e2_presenze.md`, da `impiego.quotazione_asta`,
`con_quotazione`, `ridondanza_qi`, `deriva_qi` e `contributo_qi`; 7 test nuovi in
`tests/test_fase9_e2.py`. **Nessuna richiesta di rete, nessun numero pubblicato
cambiato** — un test pretende che il riferimento di E2.4 resti 61,315 e 0,196%.

**E' il primo predittore di presenze del progetto che superi il rumore**, e la
ragione e' strutturale: tutte le feature di E2 vengono da **t-1**, perche' i dati
evento di t non esistono ancora. **QI viene da t** — un prezzo della stagione
bersaglio, pubblicato prima che cominci. E' l'unica cosa nel repository che guardi
t senza guardarne l'esito. Il **FVM e' fuori** perche' sta sull'orologio di QA
(vedi «L'orologio delle quotazioni»), e la guardia e' su `COLONNE_LISTONE_AMMESSE`
e non sul suffisso `_asta`: un nome che dice "noto all'asta" resterebbe vero anche
mettendoci QA, e sarebbe falso.

| variante | divario chiuso | t appaiato | MDE |
|---|---:|---:|---:|
| impiego (E2.4, riferimento) | 0,196% | — | — |
| + QI prezzo **grezzo** | 0,45% | +0,77 | 0,91% |
| + QI **percentile di ruolo** | **1,49%** | **+2,91** | 1,25% |
| + percentile + indicatrice | 1,46% | +2,88 | 1,23% |
| **SOLO** QI, senza feature evento | **−0,18%** | −0,61 | 1,72% |

- **1,49% contro 0,196%**, cioe' **otto volte** quello che i dati evento avevano
  prodotto, con t = 2,91 sopra il proprio MDE (1,25%) e sopra la soglia di
  Bonferroni per quattro varianti (|t| > 2,50). Migliora anche il **passaggio
  giusto**: MAE presenze 9,906 → 9,744, correlazione 0,461 → 0,481.
- **Resta piccolo in assoluto**: MAE punti 61,32 → 60,59, sette decimi su
  sessantuno. Le presenze restano il 91% dell'errore e **gli infortuni continuano
  a non essere nei dati**: quello e' il tetto vero.
- **Il prezzo grezzo NON passa** (t = 0,77, sotto il suo MDE), quindi la
  conclusione **dipende dalla forma** — ed e' la forma dichiarata in anticipo come
  l'ipotesi vera (la gerarchia dentro il ruolo), non scelta dopo. **Il gate di E1
  le separa da solo**: il grezzo deriva del 10,9% e non passa la soglia del 5%, il
  percentile dell'1,4% e passa. La forma che funziona e' l'unica che non deriva.
- **QI da solo e' PEGGIO del modello d'asta** (−0,18%): **e' un complemento, non
  un sostituto**, e chi ne ricavasse «all'asta guarda solo il prezzo» leggerebbe
  il contrario. Un test lo blocca.
- **Meta' di QI e' gia' nel set** (R² 0,47 sulle tre quote di esposizione, corr
  0,68 con `quota_minuti_prec`): il guadagno viene dall'altra meta', che e'
  esattamente cio' che nessun dato evento puo' contenere — mercato estivo e
  gerarchia dichiarata. Un test pretende `0,25 < R² < 0,75`, cioe' vieta **tutte e
  due** le letture sbagliate.
- **L'indicatrice `senza_quotazione_asta` non aggiunge niente, e il motivo e'
  strutturale**: il 31,2% delle righe di `tabella_predittori` non ha QI (chi ha
  giocato in t-1 e ha lasciato il campionato), ma la valutazione gira sul listone,
  quindi **tutte e 2.678 le righe valutate hanno un QI** e la mancanza tocca solo
  l'addestramento. Qui non e' *misurabile*, che e' un'altra cosa da «non e'
  informativa».

> **Trappola per le sessioni future.** Questo e' un risultato **positivo e
> piccolo**, e le due parole vanno tenute insieme. Non va gonfiato — l'1,5% di un
> divario che gli infortuni chiudono per la maggior parte non e' una soluzione
> delle presenze — e non va esteso al FVM «visto che QI funziona»: il FVM e'
> squalificato per una misura, non per cautela.

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

| soglia presenze attese | portieri | mai in campo | modello | + difesa E3 | sole presenze | **QI** | ~~FVM~~ |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 0 | 258 | 40% | 0.536 | 0.507 | 0.534 | **0.740** | ~~0.831~~ |
| 15 | 177 | 37% | 0.720 | 0.623 | 0.714 | **0.798** | ~~0.869~~ |
| 20 | 63 | 2% | **0.073** | −0.027 | −0.011 | **0.273** | ~~0.700~~ |

1. **La premessa del blocco era falsa per la popolazione che conta.** «Un portiere
   titolare gioca quasi tutto» e' vero per il titolare e falso per i **quotati**: il
   **40%** dei portieri a listino non gioca nemmeno una partita. Fra tutti i
   quotati, ordinare per **sole presenze attese** da' 0.534 contro 0.536 del modello
   intero — **sui portieri il modello e' gia' quasi solo un modello di presenze**.
2. **Fra i probabili titolari non funziona piu' niente**: il modello crolla a 0.073,
   le sole presenze a −0.011, la difesa di E3 a −0.027.
3. **La quotazione non crolla come il resto, e quella che conta e' QI**: fra i
   probabili titolari fa **0.273**, l'unica cosa sopra lo zero li' dentro, ed e'
   informazione disponibile **prima dell'asta**. Il vantaggio della quotazione sui
   portieri **non e' sapere chi gioca** (sopravvive dove le presenze sono note) e
   **non e' la forza difensiva della squadra** (e' quello che E3 ha provato).

> **CORREZIONE del 2026-08-05 — il 0.700 era contaminato.** Questa sezione diceva
> «ma il FVM non crolla: 0.700, ed e' il numero decisivo», e ne ricavava che il FVM
> sapesse qualcosa di ignoto sui portieri. Il FVM della pagina archiviata **si muove
> durante la stagione** (vedi «L'orologio delle quotazioni»). Il numero resta in
> tabella, barrato: e' un errore di questo progetto e non si cancella.
>
> **Rifatto con QI, che e' pulito, il vantaggio regge ma si riduce di molto**: 0.273
> invece di 0.700. E' la risposta alla domanda aperta n. 1, e sta in mezzo alle due
> che ci si aspettava: **non era solo «sapeva come era andata la stagione»** — una
> quotazione che non puo' saperlo sta comunque a 0.273 dove tutto il nostro sta a
> zero — **ma la maggior parte di quel 0.700 era esattamente quello**. Un test
> pretende entrambe le cose, cosi' che non si racconti solo la meta' comoda.

> **Precisazione sui numeri di riferimento**: il «0 contro 0,667» del modello
> d'asta e' la **precisione sui primi N**, non lo Spearman. Lo Spearman sui portieri
> non era mai stato pubblicato e vale **0.465**. Su quella metrica il divario con
> QI **non e' misurabile**: QI fa 0.000 o 0.083 a seconda di come si sciolgono i
> pari merito — e' un prezzo intero, in due stagioni su quattro ci sono pari merito
> al confine dei primi tre, e con 3 posti per 4 stagioni la metrica ha passi da
> 1/12. Le due implementazioni del repository danno i due valori per quella
> ragione, ed e' **la risoluzione della metrica, non un risultato**.

> **Trappola per le sessioni future.** La verifica negativa **non va "sistemata"**.
> Il segno e' spiegato da un meccanismo misurato — le presenze dominano
> l'ordinamento, e dove non dominano non c'e' segnale nei nostri candidati — e
> ritoccare la sostituzione finche' lo Spearman supera 0.465 cancellerebbe la
> spiegazione invece di trovarne una. **I quattro strumenti restano validi**: non
> dipendono dall'esito della verifica, e sono cio' che il blocco consegna.

**Cinque domande aperte**: (1) **che cosa sa la QUOTAZIONE sui portieri** — era
formulata sul FVM, vale **0.273 e non 0.700**, e resta la domanda piu' stretta che
il progetto abbia: non e' ne' le presenze ne' la difesa; (2) il voto del portiere
modellato sui **tiri affrontati** e non solo sui gol subiti (`sot_conceded` c'e'
gia'); (3) il modificatore con `rho` acceso, che **non e' stato ricalcolato** sulla
lista d'asta — `run_asta_2627.py` gira ancora a `rho = 0`; (4) la forza difensiva
delle **neopromosse**, che resta senza stima; (5) **un valore pre-stagione dalla
fonte, per il FVM e per il numero di maglia insieme.** Sono la **stessa domanda**,
non due — stessa forma, stessa fonte probabile, un valore d'agosto che i club e i
listoni pubblicano e che il repository non ha: il FVM pulito renderebbe leale un
concorrente oggi squalificato, il numero di maglia d'agosto proverebbe l'argomento
per cui quella feature di E2 esisteva. **Vanno tenute appaiate**: se un giorno si
risponde a una si risponde all'altra.

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

### Fase 9 — coda di E3: la compensazione voto/malus, provata e confutata ✅

Sezione 5-bis di `reports/fase9_e3_difesa.md`, da `difesa.componenti_portiere`,
`pendenza_componenti`, `correlazione_componenti`, `pendenza_voto_dal_passato`,
`collegamento_due_lati` e `qualita_componente_difensiva`; 7 test nuovi in
`tests/test_fase9_e3.py` (34 in tutto). **Nessuna richiesta di
rete, nessun numero pubblicato cambiato**, verificato rieseguendo: `run_phase1.py`
ridà 4.034 / 4.432 / 3.637 / 5.105, `run_phase5.py` ridà Como 4.34 e
5.03 / 191 / [151, 240], e tutti i numeri di E3 (5.52, 1.044, +0.0795, −0.2481,
0.261, 0.465) sono invariati.

**L'ipotesi era: dietro una difesa debole il portiere para di piu' e il voto sale,
il malus scende, le due voci si compensano, il netto e' quasi piatto — e
collegare la difesa a un lato solo peggiora.** Tre conseguenze misurate separate,
con la soglia della seconda **dichiarata prima**: compensazione completa se nel
netto sopravvive meno di **un terzo** del malus.

| conseguenza | esito |
|---|---|
| 1. pendenza del voto positiva sul portiere | **regge** (+0.0795, t = +3.44, riprodotta da E3.3) |
| 2. il netto e' quasi piatto | **cade**: sopravvive il **92,9%** del malus |
| 3. componenti correlate negativamente fra portieri | **cade**: −0.003 e −0.012, cioe' scorrelate |
| conseguenza operativa: collegare entrambi i lati | **non recupera**, nemmeno con la pendenza oracolo |
| la difesa di E3 come stimatore | **e' il migliore dei due**, ed e' l'esclusione che la coda aggiunge |

- **La compensazione esiste e vale il 7% del malus, non i due terzi che
  servivano.** Malus −1.1153 per unita' di gol attesi, voto base +0.0795, netto
  **−1.0357 con t = −14.0**. Dal p10 al p90 della forza difensiva attesa un
  portiere perde 1.01 punti **per partita**: una trentina su una stagione da
  titolare. Il netto non e' piatto, e' quasi tutto il malus.
- **Meta' della risposta e' nel regolamento, non nei dati**: per il difensore
  `comp_bonus` e' zero **per regolamento** (`lega.SOLO_PORTIERE`). Il difensore ha
  **un canale**, il portiere **due**, e i due hanno segno opposto — che e' il modo
  piu' stretto di dire cosa E3.3 aveva trovato.
- **`corr_totali` sta in tabella per essere squalificata, non letta.** Sui totali
  di stagione le due componenti fanno −0.380 e sembrerebbero la conferma cercata:
  ma il totale del voto **cresce** con le presenze e quello del bonus **cala**,
  quindi i totali si correlano **attraverso le presenze** anche se le componenti
  fossero indipendenti. Sulle medie per presenza la correlazione svanisce. Un test
  pretende **entrambe** le cose, cosi' che citare la prima da sola sia visibile.
- **Nemmeno la pendenza ORACOLO recupera** (0.507 contro 0.536 del modello che non
  collega nulla): la questione non e' la qualita' della stima della pendenza.
- **L'esclusione, ed e' il contributo positivo della coda**: contro il bonus
  difensivo per presenza realmente realizzato, la difesa di E3 fa **MAE 0.322 e
  corr +0.500** contro 0.378 e +0.346 del bonus storico del portiere. **E' lo
  stimatore migliore della cosa che stima, e sostituirla peggiora l'ordinamento lo
  stesso.** Quindi «la difesa e' stimata male» e' falso.
- **Due denominatori diversi, ed e' voluto** (difetto trovato e corretto in
  stesura): la qualita' si misura sugli 85 portieri con abbastanza presenze da
  avere un tasso, la `corr_con_presenze` su **tutti** i 258, che sono la
  popolazione su cui la Spearman e' calcolata. Restringerla ai titolari
  **rovesciava il segno**, perche' troncava proprio la variabile in questione.
  Nel verso giusto vale +0.104 contro +0.035: coerente col meccanismo e **troppo
  piccola per spiegare qualcosa**.
- **Il malus lo alimenta la fonte dei VOTI** (`difesa.FONTE_MALUS`), non i gol
  ricomposti da WhoScored. Non e' formalita': `voti_difensori` **sovrascrive**
  `gol_subiti` con i gol di squadra (autogol compresi), le due colonne hanno lo
  stesso nome e differiscono su **32 righe su 3.307**, sempre con WhoScored che ne
  conta di piu'.

> **Trappola per le sessioni future.** L'ipotesi della compensazione e' **chiusa**
> e non va riaperta. Cio' che resta vero di E3.3 e' che il voto del portiere e'
> giudicato **rispetto all'attesa**; cio' che e' falso e' che questo basti a
> spiegare l'esito negativo di E3. **Perche' collegare la difesa peggiori
> l'ordinamento dei portieri resta senza spiegazione misurata** — e ora si sa che
> non e' perche' la difesa sia stimata male.

### Fase 9 — Blocco E4: voto base e bonus ✅ (il divario da attaccare non era quello)

`reports/fase9_e4_voto_bonus.md`, da `scripts/run_fase9_e4.py`; modulo
`sot/voto_bonus.py`, test `tests/test_fase9_e4.py` (34). **Nessuna richiesta di
rete.** **Nessun numero pubblicato e' cambiato**, verificato rieseguendo:
`run_phase1.py` ridà 4.034 / 4.432 / 3.637 / 5.105 su 562.672 eventi,
`run_phase5.py` ridà Como 4.34 e 5.03 / 191 / [151, 240]. Chiude la Fase 9.

| | esito |
|---|---|
| **il divario dei bonus** | **non e' 8,9 punti: e' 2,5**, ed e' la correzione piu' importante del blocco |
| E4.0 `passFreekick` | **non contiene le punizioni**: e' `passCorner`, riga per riga |
| E4.0 il qualifier `Penalty` | **non marca il rigorista**: marca il rigore, fallo compreso |
| E4.2 i cinque fit di xG | **forma stabile, livello che si muove del 15,8%** — verifica chiusa |
| E4.1 · E4.2 · E4.3 · E4.4 | **niente**: tre varianti su tre negative, dentro il rumore |
| E4.5 QI da solo | **10,5% con t = 2,31** — l'unico che si muove, e **non passa Bonferroni** |
| E4.4 autogol | **nessun effetto individuale**, verificato invece che assunto |

**Il divario su cui E4 poggiava era sbagliato, e i difetti sono due.** Il numero
pubblicato — «con i bonus noti il MAE scende da 61,4 a 52,5» — e' stato misurato
per costruirci sopra il denominatore del blocco, e misurandolo si e' rotto:

1. **il campione cambia.** «Bonus noti» gira su **2.204 righe** e non 2.678, e le
   474 che cadono sono **le peggiori** — chi non ha mai giocato, dove il modello
   predice punti a chi ne fara' zero. Sulle stesse 2.204 righe il modello completo
   fa **55,01**;
2. **«bonus noti» non era il bonus.** Costruito per differenza come
   `punti/presenze - voto_atteso`, e' l'intero **tasso per presenza**, voto
   compreso. Lo si e' scoperto da un'identita': costruendo allo stesso modo
   l'oracolo del *voto* si ottiene lo stesso identico numero.

Divari veri, componenti separate e campione fisso: **voto 1,24 · bonus 1,44 ·
entrambi 2,51** contro i **55,86** delle presenze. **La lettura non cambia — le
presenze sono il problema, i bonus no — e anzi si rafforza**; cambia la taglia del
pezzo, che e' il **4%** dell'errore e non il 14,5%. `scomposizione_errore` ha ora
la colonna `mae_stesse_righe`, che rende il confronto orizzontale invece che
verticale, e la vecchia riga resta col nome che dice cos'era.

**`passFreekick` e' la lezione di `StandingSave` un piano piu' su.** Li' il nome
di un *qualifier* non era un identificatore; qui non lo e' il nome di una
*colonna*. Misurato su 43.176 eventi: i 296 `True` di `passFreekick` coincidono
riga per riga con `passCorner` e con i `CornerTaken`, e hanno intersezione
**vuota** con gli 813 `FreekickTaken` veri. Chi l'avesse usata avrebbe ottenuto
una tabella di battitori di punizioni dell'ordine di grandezza giusto in cui ogni
riga era un battitore di corner. **E il gate non l'avrebbe fermata**: `passFreekick`
lo passa a pieni voti, perche' un gate misura se una colonna si e' mossa fra le
stagioni, non se si chiama come cio' che contiene. I piazzati si contano quindi
**dai qualifier**, che E1 aveva gia' istruito e gia' ammesso (1,07-1,08).

- **Il qualifier `Penalty` non marca il rigorista**, ed e' una seconda trappola
  indipendente: sta sul `Foul` di chi il rigore l'ha concesso, sul `PenaltyFaced`
  del portiere e sulla parata. Solo un quarto dei suoi eventi e' il tiro.
  Ristretto a `isShot` coincide **riga per riga** con `penaltyScored |
  penaltyMissed`, e la verifica passa con **scarto zero su tutte e cinque le
  stagioni** — due derivazioni indipendenti che concordano. La conversione
  76,4-78,3% riproduce il 76,4% della Fase 1.
- **La ricerca per sottostringa e' protetta dalla forma completa** `'type': 'X'`:
  col nome nudo, `FreekickTaken` matcherebbe dentro `IndirectFreekickTaken`.
  `verifica_pattern` lo misura contro l'elenco vero dei qualifier del Blocco 0.
- **Il test di quadratura dei rigoristi NON passa alla lettera**, e la diagnosi e'
  misurata invece che addotta. La specifica si aspettava 1-2 rigoristi per
  squadra-stagione nella grande maggioranza; contando chiunque ne abbia battuto
  almeno uno sono 1-2 nel **47%** dei casi. Che non sia il parsing lo dice
  `coerenza_rigori`, che e' un controllo **piu' forte**. Cio' che si rompe e' la
  premessa: contando solo chi ne ha battuti almeno due l'attesa torna (91%), e la
  **concentrazione** dice quanto «designato» sia solido — il primo battitore
  mediano prende il **57,7%** dei rigori della sua squadra, i primi due l'83,3%.
- **Il legame passaggio chiave → tiro non e' nei dati** e questa e' la sua
  ricostruzione dichiarata: il `KeyPass` piu' vicino che precede un tiro
  `Assisted` della stessa squadra, entro tre eventi. Lega il **98,9-99,2%**, e la
  quota si conta invece di sparire.

**I cinque fit di xG: la verifica rimandata due volte e' chiusa, e la risposta e'
«si', ed e' grande».** E0 l'aveva dichiarata necessaria, E3 aveva potuto evitarla
perche' il modello dei gol non usa l'xG; qui l'xG attraversa le stagioni sommato.
Due misure che si completano:

- **la forma e' la stessa**: un modello poolato con interazioni stagione × feature
  **non batte** quello con la sola intercetta, fuori campione e coi fold
  raggruppati per partita (0,24671 contro 0,24622). Correlazione fra i cinque
  0,986-1,000 sugli stessi tiri;
- **il livello no**: applicati agli **stessi** tiri i cinque fit danno xG medio da
  0,0839 a 0,0984, cioe' **15,8% di escursione**, monotona e discendente — tre
  volte la soglia del 5% di E1.

Ne segue che **npxG non si somma fra stagioni in unita' grezze**, e che la regola
di E1 e' esattamente il rimedio giusto. Ed e' anche il *perche'* di un verdetto
che E1 aveva misurato senza potersi dare una spiegazione: `xg_per_90` era fra le
cinque irriducibili.

**Il gate di E1 rifatto sulle candidate nuove** (npxG, xA, piazzati: il loro
verdetto non esisteva e non si eredita) ne separa cinque standardizzabili — `xa_per_90`
3,6%, `passaggi_chiave_per_90` 1,9% — da cinque irriducibili, fra cui npxG. Ma
**un effetto di stagione esplicito non e' usabile fuori campione**: la stagione
bersaglio non e' fra quelle su cui si e' stimato. Entrano quindi in forma `_rel` e
la conseguenza si **misura**: la variante «senza le irriducibili» rifa' tutto
senza di loro e la conclusione non cambia.

**La valutazione, sulle stesse quattro transizioni e sulle stesse 2.678 righe**
(61,42 riprodotto, quindi campione identico):

| variante | MAE punti | quota del divario | t appaiato | MDE |
|---|---:|---:|---:|---:|
| modello d'asta | 61,4246 | — | — | — |
| E4 voto base | 61,4862 | **−6,00%** | −1,55 | 10,9% |
| E4 bonus | 61,4434 | **−1,58%** | −0,31 | 14,3% |
| E4 voto + bonus | 61,5192 | **−4,57%** | −1,09 | 11,8% |
| E4 + QI | 61,3843 | +1,95% | +0,49 | 11,1% |
| **SOLO QI**, senza feature evento | **61,2082** | **+10,46%** | **+2,31** | 12,7% |

- **Le feature da dati evento non aggiungono niente e sono negative in tutte e tre
  le varianti.** Nessuna si avvicina alla propria soglia. Il test **non** avrebbe
  visto un effetto sotto l'11-14% di un divario gia' piccolo, e va letto cosi': non
  dimostra che l'effetto sia zero.
- **QI da solo e' l'unica cosa che si muove**, e le due parole vanno tenute
  insieme: passa la soglia a due code del 5% e **non** passa Bonferroni su sei
  varianti (serve |t| > 2,64). Suggestivo, non un risultato.
- **Il contrasto con (b) e' il fatto piu' interessante.** Li' QI da solo era
  *peggio* del modello completo (−0,18%) ed era un **complemento**; qui QI da solo
  e' *meglio* di QI piu' le feature evento (10,5% contro 2,0%). **Le feature
  evento non sono neutre: peggiorano.**
- La conclusione **non dipende dal pavimento** di addestramento: stessa a 0, 5, 10
  e 20 presenze.

**E4.1 — il tetto del voto base e' dichiarato, e sta molto in basso.** In campione
e al livello giocatore-stagione i regressori arrivano a R² 0,409; ma alla riga
giocatore-partita **solo l'11-13% della varianza del voto sta FRA i giocatori**, e
l'87-89% sta dentro lo stesso giocatore — la partita, l'avversario, la giornata.
Nessun numero per giocatore puo' prenderla. E' la varianza residua che la specifica
chiedeva di dichiarare, e sta accanto al numero e non in fondo.

> **Il risultato di partita non e' un predittore, ed e' una questione di orologio.**
> La specifica lo chiedeva fra i regressori del voto, ed e' giusto per la domanda
> «quanto e' spiegabile»; ma il risultato di una partita di `t` non e' noto
> all'asta. Entra nella tabella in campione e **non** in `FEATURE_VOTO`. La forza
> di squadra e' il modo in cui quella stessa informazione entra legittimamente.

**E4.3 — sul singolo giocatore l'assegnazione discreta vale piu' di tutto il
resto del blocco.** Spostare il rigorista designato dal primo al secondo vale fino
a **15 punti di stagione**, contro i 2,5 punti di MAE su cui E4 lavora in media.
Il designato 2026-27 **e' un input**, non una stima: `punti_rigori(designato={...})`
lo impone a mano. **I rigori attesi non vengono da E3.1**, e la precisazione non e'
pedanteria: E3.1 modella i gol, i rigori assegnati sono un'altra grandezza (~0,28
per partita contro ~1,4), e prenderli in prestito da li' sarebbe prendere in
prestito la sua validazione.

**E4.4 — gli autogol non hanno effetto individuale**, e il modello con l'effetto
individuale non batte quello col solo tasso di ruolo (guadagno −0,0000). La fonte
del malus resta quella dei **voti**, come gia' stabilito da E2 e E3: e' definitoria
perche' e' quella che ha prodotto i `punti_osservati`. WhoScored resta predittore
(`falli_per_90`), mai bersaglio.

**Il ponte a `giocatore_id` perde il 22% delle righe e lo 0,13% dei minuti**: 878
su 891 sono convocati mai scesi in campo, che la fonte dei voti non elenca perche'
non hanno preso nessun voto. E' il quarto stato di E0 visto dall'altro lato.

> **Trappola per le sessioni future.** I risultati negativi di E4 **non vanno
> "sistemati"**, e in particolare non va gonfiato QI: l'unico numero positivo del
> blocco non sopravvive alla correzione per molteplicita', ed e' stato scritto
> cosi' apposta. **`[DECISO 2026-08-07]` QI sui bonus resta una NOTA, non una
> feature attiva**: non entra in nessun modello pubblicato, e promuoverlo
> vorrebbe una misura nuova, non una rilettura di questa. E' la stessa disciplina
> gia' applicata a QI in (b), dove pero' il numero passava. Non va nemmeno riaperto il FVM «visto che QI fa qualcosa»: resta
> squalificato per l'intera Fase 9 da una misura, non da una cautela. E **il
> divario dei bonus non va ricitato come 8,9 punti**: quel numero e' riproducibile
> ma misura un'altra cosa.

**Cinque domande aperte**: (1) **il rating WhoScored non e' nel repository** —
nessuna delle 259 colonne lo contiene e le pagine grezze non sono state
conservate — ed e' la **terza** della stessa famiglia, da tenere appaiata al
**numero di maglia d'agosto** (E2) e al **FVM pre-stagione** (E3): tre valori che
la fonte pubblica, che si acquisirebbero, e che il repository non ha; (2) **perche'
le feature evento peggiorino invece di essere neutre** non ha una spiegazione
misurata — il sospetto e' la ridondanza col modello d'asta, ma qui, a differenza
delle code di E2, non e' stata misurata; (3) **il divario corretto va riportato
all'indietro** nei punti in cui il 61,4 → 52,5 e' citato come divario dei bonus;
(4) **il designato dei rigori per il 2026-27**, che nessuna fonte acquisita
contiene e che vale fino a 15 punti sul singolo; (5) **gli infortuni**, che dopo E4
sono il limite dichiarato del progetto invece che uno fra tanti.

### Fase 10 — Blocco R0: il perimetro di cio' che e' validabile ✅

`reports/fase10_r0_perimetro.md`, da `scripts/run_fase10_r0.py`; modulo
`sot/perimetro.py`, test `tests/test_fase10_r0.py` (20). **Nessuna richiesta di
rete. Nessuna stima**: nessun fit, nessun bersaglio, nessun iperparametro — il
blocco *conta*. **Nessun numero pubblicato e' cambiato**, verificato
rieseguendo: `run_phase1.py` ridà 4.034 / 4.432 / 3.637 / 5.105 su 562.672
eventi, `run_phase5.py` ridà Como 4.34 e 5.03 / 191 / [151, 240].

**Apre la Fase 10 (G1), scelta dall'utente il 2026-08-07 con l'ordine G1 → G2.**

**1.889 acquisite → 1.739 con previsione → 1.638 validabili**, e il 13,3% si
perde per **due** ragioni che non vanno sommate:

| gradino | quante | causa |
|---|---:|---|
| `senza_training` | 150 | `date_splits` pretende 30 partite di training: sono **le prime tre giornate**, che nel derivato di E3 non esistono affatto |
| `perse_burnin` | 101 | hanno una previsione ma non sono `eligible`: le giornate 4 e 5 |

- **`eligible` equivale a `team_match_idx >= 6`**, ed e' **verificato e
  falsificabile**, non assunto: zero discordanti su 3.478 righe, e un test
  guasta una riga e pretende che la verifica lo veda.
- **`eligible` e' una proprieta' della SQUADRA, non della partita**, quindi una
  partita puo' averne un lato solo. **Succede due volte, entrambe nel 2021-22**,
  ed entrambe coinvolgono squadre a cui WhoScored ha perso partite: alla sua
  sesta partita vera l'Atalanta e' all'indice 5. **E' lo stesso difetto
  dell'indice che E2 aveva trovato sulle squalifiche**, e cade di nuovo dove la
  perdita alla fonte e' gia' dichiarata non casuale. La condizione e'
  `elig_casa AND elig_trasferta`, con un test che vieta la disgiunzione: **un
  esito 1X2 non e' meta' previsto.**
- **Il bersaglio di R2 regge a due derivazioni indipendenti (vincolo 7), a costo
  zero**: il punteggio ricomposto dagli eventi WhoScored (autogol riattribuiti)
  contro quello della fonte dei voti, **1.738 su 1.738 identici, zero
  discordanze**, sia sul punteggio sia sull'esito 1X2. Non passa da nessun
  modello.
- **La giornata vera c'e'** (D6, chiusa in Fase 8) e **`team_match_idx` non e'
  la giornata**: per una metrica per partita non importa, per una **classifica**
  si', perche' un indice che salta i recuperi mette la stessa squadra in due
  turni diversi. Un test vieta di concluderne che coincidano.
- **Giornate piene (10 partite su 10 validabili): 155 su 175**, e **la prima e'
  la 6a o la 7a, mai prima.** Ne segue il vincolo che R3 dichiara in specifica
  invece di scoprire a meta': **non si simula una stagione da zero.** Non esiste
  una probabilita' di scudetto alla prima giornata. Si simula il **resto** di una
  stagione dalla giornata k, data la classifica a k.

**Il risultato che decide l'ordine, ed e' un conteggio e non un'opinione**
(`perimetro.realizzazioni()`):

| affermazione | unita' | n |
|---|---|---:|
| 1X2, over/under | partita | **1.638** |
| **classifica** | **stagione** | **5** |

- **R2 e' abbondante**: 1.638 partite sono due volte e mezzo le 660 righe su cui
  le Fasi 2 e 4 hanno concluso, su un bersaglio che E3 ha gia' mostrato piu'
  facile da distinguere (t = 5,52 contro 1,86). **Il burn-in non e' un problema
  per R2**: era la preoccupazione che ha motivato il blocco, ed e' infondata.
- **R3 lo e'.** Una probabilita' di scudetto ha **una realizzazione per
  stagione**, e previsioni fatte a giornate diverse della stessa stagione **non
  sono indipendenti**: condividono l'esito. 155 giornate piene non sono 155
  osservazioni, sono cinque guardate piu' volte.

> **La dipendenza da G2, dichiarata prima e non scoperta a meta'** (era la
> domanda dell'utente): G2 **non** cambia la calibrazione — poolare i campionati
> e' l'errore che E1 vieta e che E4 ha quantificato — e **non** cambia R2. Cambia
> **solo R3**, da 5 realizzazioni a 25: **sottile, non sufficiente**. Ne segue che
> la dipendenza **non impone G2 prima**; impone che R3 dichiari il limite invece
> di fabbricare una validazione, che e' il vincolo 5.

> **CONDIZIONE BLOCCANTE SU G2 — autorizzazione.** Registrata su richiesta
> dell'utente del 2026-08-07 come condizione e **non come dettaglio tecnico**.
> L'autorizzazione di `regole_fantacalcio.md` §7.1 riguarda **WhoScored per la
> Serie A**, via il mirror `1xbet.whoscored.com`. **Estenderla a quattro
> campionati e' una decisione dell'utente, che verra' presa se e quando si arriva
> a G2, e non prima.** Nessun blocco della Fase 10 la presuppone. Accanto, e
> indipendente: tutti e quattro gli altri campionati hanno `whoscored: None` in
> `config.LEAGUE_CODES` — la terna `(regione, torneo, slug)` non e' accertata per
> nessuno, e `target.py:63` solleva invece di inventare un URL. «Lo scraper e'
> gia' parametrizzato» e' vero e non basta.

**Quattro domande aperte**: (1) la **forma della dipendenza fra i due lati** non
e' stata guardata, ed e' di proposito — due lambda dallo stesso modello non
implicano gol indipendenti dati i lambda, ed e' la domanda di R1; (2) le **due
partite disallineate** sarebbero recuperabili allineando il burn-in alla
giornata invece che a `team_match_idx`, ma cambierebbe una definizione che E3 ha
gia' pubblicato: si decide in R2 **se** toccarla; (3) **il playout Spezia-Verona
resta fuori** per mancanza di giornata — e' l'unica partita senza, ed e' il
residuo gia' dichiarato dall'aggancio; (4) **non e' verificato che l'ordine per
data basti a ricostruire la classifica progressiva** in presenza di recuperi, e
R3 ne ha bisogno.

### Fase 10 — Blocco R1: la congiunta del risultato ✅

`reports/fase10_r1_congiunta.md`, da `scripts/run_fase10_r1.py`; modulo
`sot/risultato.py`, test `tests/test_fase10_r1.py` (23). **Nessuna richiesta di
rete.** Si stima **un parametro solo**, `rho`, a marginali fissate. **Nessun
numero pubblicato e' cambiato**, verificato rieseguendo.

**§1 — la precondizione, chiesta dall'utente prima della congiunta.** Le partite
che WhoScored non ha mancano a caso **rispetto al risultato**? Non e' la domanda
dell'acquisizione, che riguardava la **squadra**. E' rispondibile perche' di una
partita che manca **il risultato ce l'abbiamo lo stesso**, dalla fonte dei voti
(380 partite per stagione, gol mai nulli). Permutazione esatta a due code.

| | |
|---|---|
| Atalanta, 6 mancanti | **V5 P1 S0**, 2,67 punti/partita contro 1,62 attesi |
| p sui **punti** | **0,055** grezzo — **non passa Bonferroni** su 7 squadre (soglia 0,0071) |
| p sui **gol fatti / subiti / casa** | 0,48 / 0,54 / 0,44 — **niente** |
| MDE con n = 6 | **±1,28 gol** a partita (osservato +0,44) |

- **La grandezza che conta e' il gol, non il punto**: R1 compone una
  distribuzione di gol e E3.1 e' stimato sui gol. Li' non c'e' niente.
- **Il meccanismo della divergenza e' aritmetico**: i punti sono una funzione **a
  gradini** dei gol, quindi vincere 5 su 6 con 2,17 gol fatti e 1,00 subiti e'
  ordinario in gol e straordinario in punti.
- **Sui punti l'osservato coincide con la soglia di rilevabilita' a ogni cifra**
  (1,048 contro 1,048): l'effetto sta esattamente sul limite del test.
- **Verdetto**: nessuna non-casualita' dimostrata sul bersaglio che R1 usa; sui
  punti un segnale coerente che non sopravvive alla molteplicita' e che con sei
  partite non e' ne' confermabile ne' escludibile. **Dichiarato, non liquidato.**
- **Il buco non tocca R3**: la classifica finale si ricostruisce dal calendario
  completo della fonte dei voti. E' nell'**ingresso**, non nel bersaglio.

**§2-§6 — la congiunta.** Le marginali **non determinano** la congiunta:
moltiplicarle e' gia' l'ipotesi di indipendenza, presa senza dichiararla.

- **Le marginali si conservano ESATTAMENTE a `rho` qualsiasi**, ed e' algebra e
  non fortuna numerica (i due termini della riga si cancellano via
  `P(1;t) = t·P(0;t)`). **La verifica ha corretto la docstring che la
  descriveva**, che affermava un residuo dell'ordine di `rho·lam`.
- **Nessuna delle tre strade indipendenti trova dipendenza**: MLE `rho` =
  **−0,0087** (LR 0,077, p 0,78); frequenza delle quattro celle chi2 = 6,35 su 4
  gdl (p 0,17), che non passa da nessuna ottimizzazione; correlazione dei residui
  +0,026 (p 0,29), che non usa nemmeno `tau`. Le cinque stagioni separate danno
  cinque stime che **cambiano segno**.
- **Lo scostamento presente non ha la forma di Dixon-Coles**, ed e' il risultato
  non cercato del blocco: si osserva **meno 0-0 e piu' 1-1**, mentre un `rho` solo
  lega quelle due celle allo **stesso** verso. **Nessun valore di `rho` puo'
  produrre quel disegno**, e per questo l'MLE cade a zero invece di limitarsi a
  starci vicino. Lo scostamento di suo non e' significativo.
- **La potenza e' dichiarata** ed e' cio' che rende leggibile il negativo: 80% a
  `rho` = 0,09, 99% a 0,12. Il campione **non e' cieco** — esclude dipendenze di
  taglia media, non solo enormi. Sotto 0,05 la potenza e' 36%.
- **R1 consegna a R2 `rho = 0`**, come esito misurato e non come default comodo.

> **Vincolo 1, per chi volesse un `rho` diverso da zero.** Qui e' stimato **in
> campione** ed e' lecito perche' usato come **limite superiore** — la direzione
> in cui 6D ha usato lo stesso genere di test. Usarlo *in previsione* vuole una
> ristima sul solo passato, come `walkforward_r` fa per `r`.

**Quattro domande aperte**: (1) il buco dell'Atalanta **non e' risolvibile qui** —
sei partite non bastano e altre non ne arriveranno, servirebbe un'altra fonte di
dati evento; (2) la dipendenza e' stata cercata **solo** nella forma di
Dixon-Coles, e lo scostamento osservato ne suggerisce un'altra che su 1.638
partite sarebbe adattarsi al rumore — e' la prima cosa che G2 avrebbe la massa per
guardare; (3) **`rho` e' assunto costante fra partite** e potrebbe dipendere dal
divario di forza; (4) la correzione originale ha un **decadimento temporale**, qui
assente perche' i lambda di E3.1 ce l'hanno gia' dentro, e che i due debbano
essere lo stesso non e' ovvio ne' verificato.

### Fase 10 — Blocco R2: 1X2 e over/under, valutati ✅

`reports/fase10_r2_esiti.md`, da `scripts/run_fase10_r2.py`; modulo
`sot/esiti.py`, test `tests/test_fase10_r2.py` (28). **Nessuna richiesta di rete.
Nessun parametro nuovo**: `rho = 0` da R1, i lambda da E3.1. **Nessun numero
pubblicato e' cambiato**, verificato rieseguendo.

`[DECISO 2026-08-08]` dall'utente: **il burn-in NON si allinea alla giornata**,
le due partite disallineate di R0 restano fuori. Il perimetro resta **1.638**.

| | esito |
|---|---|
| 1X2 contro i baseline **non informativi** | **vince**, t fra −10,4 e −10,9 |
| 1X2 contro **`media squadra + campo`** | **t = −1,10, dentro il rumore** (MDE 0,00424) |
| over/under contro la **media di campionato** | **perde** (t = +0,90, non distinguibile) |
| over/under contro i **baseline di squadra** | **vince**, t = −4,38 |
| calibrazione su 1X2 | **sotto-sicuro**: pendenza 1,22 e 1,32, z +2,3 e +3,2 |

- **Il vantaggio misurato sui gol NON sopravvive alla proiezione su 1X2.** E3
  batteva il baseline migliore per t = 5,52; qui vale t = −1,10. Due cause che si
  sommano: le righe passano da 3.278 a 1.638 (una partita, non due
  squadre-partita) e l'esito a tre classi **butta via** informazione — 3-0 e 1-0
  sono lo stesso `1`. **E' la stessa forma delle Fasi 2 e 4** (t = 1,86 sui tiri).
- **Su over/under l'ordine dei baseline si ROVESCIA**, ed e' il risultato non
  previsto: un 1X2 dipende dalla **differenza** dei lambda, un over/under dalla
  loro **somma**. I baseline di squadra sono forti sulla prima e pessimi sulla
  seconda; la media di campionato l'opposto.
- **Il fatto che spiega il rovesciamento e' stato misurato dopo aver scritto una
  spiegazione sbagliata**: la frase «le medie di squadra sommate disperdono piu'
  del vero» e' **falsa** (0,691 contro 1,569 dell'osservato).
  `dispersione_somma()` dice la cosa vera, ed e' piu' forte: **il totale di gol
  di una partita e' quasi imprevedibile per tutti** — la correlazione migliore
  fra somma prevista e totale vero e' **0,099**, ed e' del modello. Con un legame
  cosi' debole ogni dispersione in piu' e' varianza pagata a vuoto, e su una
  metrica quadratica vince chi ne mette meno.
- **Il modello e' l'unico candidato decente su ENTRAMBE le domande**, e questo —
  non l'accuratezza su una metrica sola — e' l'argomento con cui si giustifica.
  E' la stessa forma dell'argomento della Fase 4 sulla calibrazione. Un test lo
  blocca: nessun baseline deve essere vicino al modello su RPS **e** su O2.5.
- **Sulla calibrazione il segno e' OPPOSTO a quello della Fase 4.** Li' i
  baseline informativi erano sotto 1.0 (troppo estremi) e il modello era l'unico
  compatibile con 1.0; qui il modello e' **sopra** 1.0 (sotto-sicuro) e
  `media squadra + campo` e' meglio calibrato di lui. La spiegazione compatibile
  e' la compressione della ridge quantificata dalla 6A (pendenza 0,760), ma
  **non e' stata misurata** ed e' la prima domanda aperta. `media campionato`
  non e' identificata, come in Fase 4 e per la stessa ragione.
- **Un difetto trovato e corretto prima di pubblicare**: il tasso base dell'over
  era stimato sull'intero campione mentre quello 1X2 era gia' walk-forward —
  vincolo 1. Ora entrambi usano il solo passato, e due test di leakage lo
  bloccano guastando la coda della stagione.
- **Il pavimento sui lambda e' dichiarato** e tocca **una riga**: `media squadra`
  predice esattamente 0 mentre quella squadra segna, e senza pavimento la sua
  log-loss sarebbe infinita. Stesso caso della frequenza storica grezza di E3,
  stesso trattamento.

> **Vincolo 3.** Nessuna valutazione di scommessa e nessuna quota: non ci sono
> prezzi di mercato nel repository, e le uniche ottenibili sarebbero generate da
> questo stesso modello. Un test vieta che una quota compaia in `sot/esiti.py`.
> Finche' non ci sono quote di chiusura reali, **«il modello e' meglio del
> mercato» non e' una frase che questo progetto possa pronunciare.**

**Quattro domande aperte**: (1) la **sotto-sicurezza su 1X2 non e' spiegata**, e
il legame con la compressione della ridge e' compatibile ma non misurato —
**non va "sistemata" ritoccando lo shrinkage finche' la pendenza torna a 1.0**;
(2) il confronto con `media squadra + campo` **e' senza potenza**: servirebbero
circa 10.700 partite per distinguerli, cioe' **la prima domanda del progetto in
cui G2 avrebbe un uso diretto e quantificato**; (3) nessuna valutazione di valore
atteso e' possibile senza quote reali; (4) le due partite disallineate restano
fuori per decisione dell'utente.


### Fase 10 — coda R2-bis: la calibrazione, prima di R3 ✅ (l'ipotesi cade, il sintomo si toglie)

`reports/fase10_r2bis_calibrazione.md`, da `scripts/run_fase10_r2bis.py`; modulo
`sot/ricalibrazione.py`, test `tests/test_fase10_r2bis.py` (36). **Nessuna
richiesta di rete.** **A differenza di R2 questo blocco STIMA** — la
ricalibrazione ha parametri, e sono walk-forward. **Nessun numero pubblicato e'
cambiato**, verificato rieseguendo: `run_phase1.py` ridà 4.034 / 4.432 / 3.637 /
5.105 su 562.672 eventi, `run_phase5.py` ridà Como 4.34 e 5.03 / 191 / [151, 240],
e R2 resta 1.638 partite, RPS 0,2041, pendenza 1,223.

**Fatto prima di R3 su richiesta dell'utente, e la ragione e' l'accumulo**: un
errore di calibrazione su una partita sola resta locale, ma R3 somma le stesse
probabilita' su 38 turni e pubblica due **code** — scudetto e retrocessione.

| | esito |
|---|---|
| il `k` che calibra 1X2 | **1,209 e 1,302**, contro gli **1,316** che l'ipotesi prevede: verso giusto, taglia quasi giusta |
| il controllo diretto **sui gol** | **rifiuta l'ipotesi a z = −8,07**, e non per mancanza di potenza |
| ricalibrazione **Platt** walk-forward | **adottata**: z da +3,42 a +1,89 sulla `2`, RPS non peggiora |
| temperatura · isotonica | **bocciate** dal criterio dichiarato prima |
| la classifica al livello di R3 | **sotto-dispersa di un fattore 2,0**, e la ricalibrazione **non** la chiude |

**Il blocco tiene separate due domande che e' facile confondere, ed e' il suo
contenuto metodologico**: «da dove viene» (§2) e «se si toglie» (§3). **Che la
ricalibrazione funzioni non e' una conferma dell'ipotesi** — una mappa monotona
corregge il sintomo qualunque sia la causa, e non sa da dove l'errore venga.

- **La de-compressione e' costruita come l'inverso della ridge, in tre modi
  dichiarati**, e conserva `lam_c * lam_t` a ogni cifra nel modo primario: la
  penalita' comprime `attacco` e `difesa` e **non tocca `mu`**. Tre identita'
  esatte la verificano (`k = 1` e' l'identita', il divario e' scalato per `k`
  esatto, il prodotto non si muove). **La conclusione non dipende da quale pezzo
  si applica**: `divario`, `divario_netto` (che lascia fermo il vantaggio del
  campo) e `pieno` (l'inverso **letterale**, che allarga anche la somma dei due
  lati) danno lo stesso `k` entro 0,03.
- **La meta' del risultato va A FAVORE dell'ipotesi e va detta**: il `k` che
  calibra le classi `1` e `2` — cercato come **radice**, non letto dal minimo di
  una griglia — vale 1,209 e 1,302 contro l'1,316 della 6A. **Fermandosi qui
  l'ipotesi sarebbe confermata.**
- **Il controllo che la esclude viene da E3 e non da qui**, ed e' la pendenza di
  calibrazione **sui gol**: la relazione e' esatta — lambda compressi di `c`
  danno pendenza `1/c` — quindi l'ipotesi non prevede genericamente «sopra 1»,
  prevede **1,316**. Si osserva **0,898 ± 0,052**, cioe' z = −1,97 contro 1.0 (se
  mai, i lambda sono troppo **estremi**) e **z = −8,07 contro il valore che
  l'ipotesi prevede**. **Non e' mancanza di potenza**: una compressione fino a
  0,873 sarebbe stata vista con probabilita' 80%, e la 6A ne dichiara una del 24%.
- **La stessa trasformazione che calibra l'esito scalibra la grandezza da cui
  l'esito e' costruito**: al `k` del riferimento la pendenza sui gol passa da
  0,898 (z = −1,97) a 0,749 (z = −6,01). Non e' un pareggio fra due
  diagnostiche: e' una che si sistema e una che si rompe. **L'ipotesi della
  compressione va abbandonata come CAUSA, pur restando una buona descrizione del
  sintomo** — coincidere in taglia non e' spiegare.
- **Cio' che il blocco propone al suo posto e' un indizio, non una misura**: il
  modello dichiara 0,2507 di pareggi contro 0,2674 osservati, cioe' 27 pareggi
  mancanti — ma sono **1,5 errori standard** e il segno cambia in due stagioni su
  cinque. E' la firma della composizione (due Poisson indipendenti fanno pochi
  pareggi) e **si incastra con R1**, che aveva misurato `rho = 0` e uno
  scostamento di forma «meno 0-0 e piu' 1-1» che **nessun `rho` puo' produrre**.
  Non e' stato corretto: inventare qui una seconda forma di dipendenza su 1.638
  partite sarebbe adattarsi al rumore.
- **La ricalibrazione e' walk-forward** (vincolo 1): il mappatore della stagione
  `s` si addestra sulle stagioni precedenti e su nient'altro. La **2021-2022 non
  ha un passato e resta non ricalibrata**, marcata e non riempita — il confronto
  gira sulle **1.315** righe marcate. Due test guastano i dati: rovesciare
  l'ultima stagione non deve muovere **nessun** parametro, rovesciare la prima
  deve muovere i successivi.
- **Il criterio di adozione e' scritto PRIMA di guardare i numeri**
  (`CRITERIO_ADOZIONE`) e `verdetto()` lo applica meccanicamente. **Platt e'
  l'unico che passa**: z 0,31 / −0,89 / 1,89, RPS −0,00090 con t = −1,79 contro
  un MDE di 0,00141. **La temperatura non basta** (z 2 resta a +3,23) — ed e' il
  secondo argomento contro §2: se il difetto fosse «tutte le probabilita' troppo
  vicine al centro», una manopola che le allarga tutte insieme lo toglierebbe.
  **L'isotonica sovra-corregge** (z 1 = −4,63) e peggiora l'RPS; sulla `X` la sua
  pendenza **non e' nemmeno identificata**, lo stesso `nan` dichiarato di
  `media campionato`.
- **Cosa fa Platt, si legge dai coefficienti**: l'intercetta sulla `X` e'
  **positiva in tre stagioni su quattro**, cioe' il mappatore passa il tempo ad
  **aggiungere pareggi** — §2.3 letto dall'altro lato. E **compra calibrazione,
  non accuratezza**: una mappa monotona non riordina niente.

**§4 — la misura al livello di R3, ed e' il numero piu' importante del blocco.**
La domanda non e' la pendenza per partita ma «**la classifica simulata si
disperde quanto il modello dice?**», in forma falsificabile:
`var(punti osservati fra le squadre) = var(punti ATTESI) + media(varianza di
campionamento)`.

| | |
|---|---|
| rapporto `osservata / (attesa + campionamento)` | **1,99 in media, sopra 1 in tutte e cinque le stagioni** |
| in unita' leggibili | **19 punti** di dispersione su 38 giornate contro **13** dichiarati |
| solo 2a meta' (dove R3 lavora) | scende a **1,42** e **non si chiude** |
| dopo Platt | da 2,06 a **1,79**: riduce, non chiude |

- **La misura e' verificata su dati in cui la risposta e' nota**: generando gli
  esiti **dalle probabilita' del modello** — dove per costruzione e' calibrato —
  il rapporto torna attorno a 1. E' l'unico modo di distinguere un difetto del
  modello da un difetto della misura, e un test lo pretende.
- **Il burn-in ne spiega una parte e non tutta**, ed e' il controllo che impedisce
  di attribuire alla calibrazione cio' che e' apprendimento mancante.
- **Non e' un difetto di calibrazione e non va chiamato cosi'**: e' la parte
  delle differenze **vere** fra squadre che il modello non ha catturato, piu'
  qualunque shock che duri piu' di una partita. Una mappa monotona sulle
  probabilita' di partita non puo' restituirla — sposta massa dentro ogni riga,
  non aggiunge separazione fra le squadre.

**Cosa consegna a R3**: (1) le probabilita' **ricalibrate con Platt**, con la
2021-2022 contata come non ricalibrata; (2) **il prezzo dichiarato** — dopo Platt
le tre probabilita' 1X2 non escono piu' dalla **stessa** congiunta che produce
l'over/under, quindi il modello **non e' piu' internamente coerente** fra le due
domande: R3 usa solo l'esito e non lo paga, un blocco che volesse entrambe si';
(3) **la sotto-dispersione della classifica va DICHIARATA accanto ai numeri**
(vincolo 5), perche' senza, le code di scudetto e retrocessione escono troppo
grasse.

> **Trappola per le sessioni future.** L'ipotesi della compressione della ridge e'
> **chiusa in negativo** e non va riaperta ritoccando lo shrinkage finche' la
> pendenza torna a 1.0: §2 mostra che quella strada paga la calibrazione
> dell'esito con quella dei gol. E la ricalibrazione **non** va venduta come
> spiegazione: corregge il sintomo e non sa da dove venga.

**Quattro domande aperte**: (1) **la causa della sotto-sicurezza resta ignota** —
la domanda n. 1 di R2 e' **cambiata, non chiusa**: non e' piu' «e' la ridge?» ma
«quale forma di dipendenza produce meno 0-0 e piu' 1-1», che su 1.638 partite non
si cerca senza adattarsi al rumore (e' la n. 2 di R1, quella per cui G2 avrebbe la
massa); (2) **la sotto-dispersione della classifica non e' spiegata** e le due
candidate — varianza vera fra squadre non catturata, shock correlati lungo la
stagione — non sono state separate, il che vuole un modello con un effetto di
squadra persistente; (3) il criterio «non peggiora l'RPS» ha **MDE 0,00141**,
cioe' esclude peggioramenti grandi e non piccoli; (4) la ricalibrazione ha
granularita' **di stagione** e non e' stato misurato quanto costi non rifittarla
per giornata.


### Fase 10 — Blocco R3: la classifica ✅ (e il modello, qui, batte il baseline)

`reports/fase10_r3_classifica.md`, da `scripts/run_fase10_r3.py`; modulo
`sot/classifica.py`, test `tests/test_fase10_r3.py` (25). **Nessuna richiesta di
rete. Nessun parametro nuovo**: i lambda vengono da E3.1, le probabilita'
ricalibrate da R2-bis, il calendario dalla fonte dei voti. Questo blocco
**simula**. **Nessun numero pubblicato e' cambiato.** Chiude la Fase 10.

**Il vincolo che struttura il blocco viene da R0 e non si aggira: non si simula
una stagione da zero.** La prima giornata piena e' la sesta o la settima, mai
prima. Si simula il **resto** di una stagione dalla giornata `k`, **data la
classifica vera a `k`**. Giornate di partenza dichiarate: **10a, 19a, 28a**.

| | esito |
|---|---|
| MAE sui punti finali dalla 19a | **3,8 punti** su una stagione intera, bias +0,04 |
| copertura 50/80/95% | **62 / 86 / 97** — **sopra** il nominale, non sotto |
| contro `media squadra + campo` | **il modello vince**: −0,78 punti, t = −3,21 per stagione (p = 0,033) |
| contro il modello **non ricalibrato** | −0,16 punti, t = −2,4 per stagione: R2-bis paga |
| la sotto-dispersione di R2-bis | **1,27 → 1,12 → 1,05** al crescere di `k`, non 2,0 |
| probabilita' di scudetto | **non validate, e non validabili**: cinque realizzazioni |

**Il risultato che conta e' il primo del genere nella Fase 10: sulla classifica
il modello si distingue da un baseline informativo, e su 1X2 non ci riusciva.**
Su una partita sola il margine su `media squadra + campo` valeva t = −1,10, cioe'
dentro il rumore; **su diciannove giornate lo stesso margine si accumula** e
diventa 0,78 punti di MAE con t = −3,21 sull'unita' onesta. **I due `t` si
riportano sempre in coppia**: quello su squadra-stagione (n = 100) e' ottimista
perche' venti squadre si dividono un monte punti quasi fisso, quello per stagione
(n = 5) e' onesto e quasi cieco.

- **La costruzione che tiene insieme R2-bis e la differenza reti**: si estrae
  prima l'**esito** con la probabilita' ricalibrata, poi il **punteggio** dentro
  la classe estratta, con `P(gc, gt | esito)` dalla congiunta di R1. Cosi' il
  prezzo dichiarato da R2-bis — dopo Platt le 1X2 non escono piu' dalla stessa
  congiunta — **non si paga sui punti**. Un test verifica che le tre condizionali
  vivano davvero dentro la propria classe.
- **La classifica non ha buchi**, ed e' il punto che R1 aveva anticipato: delle
  12 partite che WhoScored non ha, il risultato si legge dall'altra fonte. Il
  buco sta negli **ingressi**, non nel bersaglio. Le partite del futuro senza
  previsione (**al massimo 5 per stagione**, tutte nelle due annate bucate)
  ricevono un **ripiego dichiarato e contato**: i lambda medi della loro
  stagione.
- **La domanda aperta n. 4 di R0 ha una misura**: `k` e' **ordinale** («tutte le
  partite con `giornata <= k`»), e **l'1,3% delle partite si gioca dopo che la
  giornata successiva e' cominciata**. La convenzione e' dichiarata, non
  dimostrata equivalente alla lettura in tempo reale.
- **Le identita' del calendario sono falsificabili e passano**: 380 partite, 20
  squadre, 38 partite a testa di cui 19 in casa, e la somma dei punti che vale
  `3n − pareggi`. I test le pretendono **in ogni replica** e non in media: ogni
  replica distribuisce fra 760×2 e 760×3 punti, e `gf − gs` sommato sulle venti
  squadre fa zero.
- **Il caso limite in cui la risposta e' nota**: simulando dalla 38a, cioe' senza
  partite da giocare, la simulazione **deve** restituire la classifica finale
  vera a ogni cifra. Un test lo pretende.
- **Lo scioglimento dei pari merito e' una semplificazione dichiarata** (punti,
  differenza reti, gol fatti, estrazione col seme) contro gli **scontri diretti**
  del regolamento vero, e **non e' trascurabile**: un pari merito compare al
  confine dell'Europa nel **13,9%** delle repliche e a quello della retrocessione
  nel **15,6%**. Misurato, non dichiarato irrilevante.

**§4 — il danno che R2-bis prevedeva e' molto piu' piccolo, e il perche' si
misura.** R2-bis aveva trovato la classifica sotto-dispersa di un fattore **2,0**
sulle probabilita' di partita e ne aveva tratto code troppo grasse. Sui punti
finali il rapporto vale **1,27 alla 10a, 1,12 alla 19a, 1,05 alla 28a**. **Il
meccanismo e' aritmetico**: la classifica a `k` porta dentro la separazione
**vera** fra le squadre, e la compressione tocca solo la parte ancora da giocare.
**E' una correzione della lettura di R2-bis, non dei suoi numeri** — il 2,0
tornerebbe intero a chi simulasse da giornata zero, che e' cio' che R0 vieta per
un'altra ragione.

- **Dove la compressione sopravvive e' agli estremi**: l'ultima in classifica fa
  in media **20 punti veri contro 27 attesi**. Stesso segno gia' misurato in Fase
  3, Fase 4 e 6A, e **non va corretto ritoccando lo shrinkage**.
- **La copertura e' SOPRA il nominale, non sotto**, cioe' l'opposto di cio' che
  la sotto-dispersione faceva temere. Le due cose convivono ed e' la firma dello
  shrinkage: previsioni tirate verso il centro **e** incertezza abbondante
  attorno a ciascuna.
- **Il chi2 sulla PIT non e' un test qui**, e il report lo dice invece di
  stamparne il `p`: venti squadre di una stagione si dividono un monte punti
  quasi fisso, quindi le cento righe sono correlate per costruzione. Si riporta la
  **forma** delle dieci fasce, che e' rumorosa e non permette di concludere.
- **`media campionato` si rompe sulla calibrazione e non solo sull'accuratezza**:
  copertura 33 / 57 / 79 contro il nominale, MAE 7,55. Non sapendo distinguere le
  squadre, sottostima quanto la classifica possa allontanarsi dalla sua previsione
  piatta.

**§6 — le probabilita' di classifica sono una DESCRIZIONE e non una
validazione**, ed e' R0 a imporlo: uno scudetto ha **una realizzazione per
stagione**. Il Brier batte il tasso base su tutte e tre le affermazioni e a tutte
e tre le giornate, ed e' l'unica colonna che dica qualcosa.

> **`media dichiarata` = `frequenza vera` e' un'IDENTITA', non calibrazione.** In
> ogni replica c'e' esattamente un campione, quattro squadre nei primi quattro
> posti e tre retrocesse: le probabilita' sommano a quei numeri **per
> costruzione**. Chi leggesse quella colonna come «il modello e' calibrato»
> leggerebbe un vincolo contabile, e un test blocca il fatto perche' resti
> leggibile come tale.

**La stagione vetrina (2025-26 dalla 19a) letta onestamente**: Inter 88% di
scudetto e ha vinto; le retrocesse vere avevano **89%, 88% e 8%** — due su tre
erano le piu' alte, **la terza no**, e la squadra con la terza probabilita' piu'
alta (Lecce, 40%) si e' salvata. Il **Como** aveva **45%** di finire nei primi
quattro ed e' arrivato quarto, con 67,9 punti attesi contro 71 veri.

> **Trappola per le sessioni future.** Le probabilita' di scudetto **non sono
> validate** e nessuna quantita' di repliche Monte Carlo puo' validarle: le
> realizzazioni sono cinque. G2 le porterebbe a 25 — **sottile, non
> sufficiente**, come R0 aveva gia' scritto. E la compressione agli estremi non
> va "sistemata": sarebbe la quarta volta che il progetto rifiuta quella strada.

**Quattro domande aperte**: (1) le **probabilita' di classifica restano non
validate**, e chi volesse validarle deve portare campionati, non repliche;
(2) gli **scontri diretti non sono simulati** e la semplificazione tocca il
13-16% delle repliche al confine — il costo **non e' stato misurato**, servirebbe
tenere la matrice degli incroci in ogni replica; (3) **la compressione agli
estremi resta**, ed e' l'unica parte della sotto-dispersione di R2-bis che
sopravvive alla partenza dalla classifica vera; (4) **la convenzione ordinale su
`k`** e' dichiarata e non dimostrata equivalente alla lettura in tempo reale.


### Fase 11 — Blocco S1: le soglie del Como 2026-27, partita per partita ✅

`reports/fase11_s1_soglie_como.md` + `reports/fase11_s1_soglie_como.csv` (228
righe: 38 partite x 6 linee) + **`reports/fase11_s1_simulatore.html`**, da
`scripts/run_fase11_s1.py` (+ `scripts/pagina_s1.py` per la sola pagina); modulo
`sot/soglie_2627.py`, test `tests/test_fase11_s1.py` (45). **Nessuna richiesta di
rete** dal codice. **Nessun numero pubblicato e' cambiato**, verificato
rieseguendo: `run_phase1.py` ridà 4.034 / 4.432 / 3.637 / 5.105 su 562.672
eventi, `run_phase5.py` ridà Como 4.34 e 5.03 / 191 / [151, 240].

**Richiesto dall'utente il 2026-08-11**: 1 EUR su ogni partita del Como 2026-27,
per ogni fascia di over tiri in porta da 2.5 a 7.5, guadagno atteso.

**Il guadagno atteso e' `P x quota - 1`, e di quei due fattori il repository puo'
produrre solo il primo.** `[DECISO 2026-08-11]` dall'utente: si pubblica `P` e la
**quota di pareggio** `1/P`, e il guadagno come **funzione della quota fornita**.

| | esito |
|---|---|
| il ponte `lambda(Como, avversario, campo)` | **costruito**: non esisteva |
| `P(Over)` per sei linee, due forme | 0.835 (2.5) → 0.154 (7.5) |
| quota di pareggio di stagione | **1.20 · 1.45 · 1.89 · 2.67 · 4.03 · 6.48** |
| validazione sul 2025-26 | il modello **batte il tasso base su tutte e sei**, tutte **dentro l'MDE** |
| la quota generata dal modello | **identita' contabile**, non una misura |

- **Che cosa mancava**: `project_2627.monte_carlo` produce **solo il totale
  stagionale**, con un `lam` costante sulle 38 giornate, senza avversario e senza
  campo. Il ponte per partita non c'era.
- **La struttura relativa viene dal modello, il livello dall'ancora** (Fase 6A):
  `lam_i = lam_modello_i / media(lam_modello) x ancora`, con
  `ancora = 4.90 x 1.01014 = 4.9497`. La media dei 38 vale l'ancora **a
  precisione macchina**, e un test lo blocca: e' cio' che rende la tabella
  coerente con la proiezione pubblicata invece di essere una seconda proiezione
  che le somiglia. Da 3.467 (Juventus in trasferta) a 6.272 (Sassuolo in casa).
- **Ne segue che lo scenario sulle promosse NON sposta il livello**, solo la
  distribuzione fra le partite — coerente con la decisione della 6E, dove
  applicare il fattore di calendario all'ancora sarebbe un doppio conteggio. Su
  `P(Over 4.5)` media i quattro scenari stanno in **0.5274-0.5289**, mentre il
  lambda contro una promossa in casa va da 5.48 a 6.32: **lo scenario
  ridistribuisce, non aggiunge**.
- **La fonte esterna e' verificata per la meta' verificabile**: le tre promosse
  (Venezia, Frosinone, Monza) non sono controllabili in casa, ma le tre
  retrocesse arrivano dalla **stessa pagina** e coincidono con quelle che
  `calendar_2627.retrocesse()` ricava dai gol. Se divergessero, anche le promosse
  andrebbero rimesse in discussione.
- **Il calendario vero c'e', ed e' costato quattro fonti.**
  `verifica_calendario` ne ha **rifiutate tre** (il Como fra i propri avversari;
  la stessa squadra tre volte; due volte in casa). La quarta — ESPN — ha
  struttura perfetta ma dava **37 righe su 38**. **La riga mancante non e' stata
  indovinata: e' determinata** — Napoli compariva solo in trasferta, quindi
  l'unica partita compatibile e' `Como-Napoli in casa`; l'unica cosa presa da
  fuori e' la sua **giornata** (la 21a), che concorda su due fonti indipendenti.
  Corroborazione non usata per costruirlo: **le prime tre giornate sono tutte in
  trasferta**, ed e' cio' che le fonti riportano a parte per i lavori al
  Sinigaglia. `CALENDARIO_2627` e `NOMI_FONTE` sono dichiarati nel modulo — al
  livello di squadra **il nome non e' una chiave** (Fase 8), e una mappa
  incompleta solleva invece di produrre un `NaN`.
- **Il calendario resta un comodo, non una dipendenza, e un test lo blocca**: con
  e senza giornate i lambda e le probabilita' sono gli stessi, perche' l'ordine
  non entra in nessuna somma. Le **date** restano nulle: le fonti discordano.
- **L'integrazione sull'incertezza di livello ingrassa le code nel verso
  dichiarato prima**: sulla 7.5 `P` sale da 0.1542 a 0.1772, sulla 2.5 scende da
  0.8353 a 0.8343. **Non sapere quanto tirera' il Como non e' neutro: rende gli
  estremi piu' probabili**, e la quota di pareggio sulla 7.5 passa da 6.48 a 5.64.
- **Si integra SOLO il livello, mai il campionamento**: `sampling` e' gia' dentro
  `p_over`, e tenerlo acceso conterebbe le code **due volte**, in silenzio. Un
  test lo pretende.
- **La dispersione fra le partite non e' un dettaglio**: sulla 4.5 `P` va da
  0.274 a 0.720. Una quota unica per la stagione conviene su alcune partite e non
  su altre — per questo il CSV esce a 38 righe per linea e non come media.
- **La validazione e' walk-forward** (vincolo 1) sulle 33 partite valutabili del
  Como 2025-26: il modello batte il tasso base su tutte e sei le linee
  (differenze da −0.004 a −0.043), ma **tutte dentro il proprio MDE**. Esclude
  divari grandi, non divari piccoli — lezione della 6D. Pendenza di calibrazione
  0.602 ± 0.516 (z = −0.77): compatibile con 1.0, e con una squadra sola vuol dire
  poco.
- **Le linee 6.5 e 7.5 sono un'estrapolazione dichiarata**: `validate.LINES` si
  ferma a 5.5, e su quelle due `r` conta molto di piu' (sensibilita' relativa
  all'IC95% di profilo). Un test pretende che l'avvertenza stia accanto alla
  costante `LINEE`.

**L'appendice che squalifica il conto letterale** (`identita_circolare`): se la
quota la genera il modello stesso con margine **proporzionale**, il guadagno
atteso vale `1/overround - 1` — **lo stesso numero su ogni partita e su ogni
linea, dispersione zero**. Non contiene una sola informazione sul Como: e' il
margine scritto al contrario, e un test lo verifica a precisione macchina. Col
margine a **potenza** varia con `p` e sembra una misura, ma varia **dodici volte
di piu' fra le linee che fra gli overround**, perche' `p^(1-1/k) - 1` e' funzione
della sola `p`: la trasformazione penalizza le probabilita' piccole, e di Como li'
dentro non c'e' niente.

**La pagina locale** (`reports/fase11_s1_simulatore.html`, generata da
`scripts/pagina_s1.py`): linea, quota, puntata e forma della `P` sono comandi;
le 38 quote sono **modificabili riga per riga**, per incollarci i prezzi veri
quando ci saranno. E' **autonoma** — nessun CDN, nessun font remoto, nessuna
richiesta di rete — e un test lo pretende, perche' «pagina locale» vuol dire che
funziona offline. **La quota e' un ingresso dell'utente, mai un output**: il
default dello slider e' la quota di **pareggio**, cioe' il punto in cui il
guadagno e' zero, che e' il default piu' neutro possibile e non una previsione di
prezzo. I numeri della pagina coincidono con quelli del report (a `q = 3.00`
sulla 4.5 entrambi danno **+22.24**).

> **Trappola per le sessioni future.** «Quanto si guadagna» **non e' rispondibile
> con i dati in casa**, e non per prudenza: manca il secondo fattore. §3 e §4 del
> report danno tutto il necessario per rispondere nel momento in cui esiste un
> prezzo vero. **Non si ricostruisca una quota dal modello per chiudere il
> cerchio**: e' il codice in `legacy/`, ed e' archiviato per questo — e la pagina
> non deve iniziare a proporne una.

**Un difetto latente trovato di rimbalzo, e non e' stato corretto dove sta**: la
guardia del vincolo 3 di `tests/test_fase10_r2.py:275` (e delle gemelle in R2-bis
e R3) cerca **sottostringhe**, quindi `roi` scatta dentro `proiezione` e
`bankroll` **non** scatta dentro `calcola_bankroll` — falsi positivi e falsi
negativi insieme. In `tests/test_fase11_s1.py` e' corretta con un confine di
**lettera** (non `\b`, perche' `_` e' un carattere di parola) e un test che
verifica entrambe le direzioni. **Nei tre moduli di Fase 10 non e' stata
toccata**: cambiare un test che oggi passa non era in questo blocco.

**Cinque domande aperte**: (1) i **prezzi di mercato reali** restano l'unica cosa
che manca, e servirebbero **quote di chiusura pre-partita** — quote correnti
erediterebbero lo stesso difetto di orologio che ha squalificato il FVM; (2) il
**calendario vero** non serve a queste tabelle ma servirebbe alle giornate dopo un
turno di Champions, dove `CAL.LIMITE_CONGESTIONE` dichiara un effetto di segno
noto e negativo mai stimato — su quelle partite queste probabilita' sono
**ottimistiche**; (3) la difesa delle promosse resta uno **scenario**, e qui pesa
meno di quanto si temesse; (4) la 6.5 e la 7.5 non hanno una validazione propria;
(5) la guardia del vincolo 3 di Fase 10, sopra.

### Fase 12 — Blocco V0: il perimetro del bersaglio TIRI ✅

`reports/fase12_v0_perimetro.md` + cinque CSV, da `scripts/run_fase12_v0.py`;
modulo `sot/tentativi.py`, test `tests/test_fase12_v0.py` (34). **Nessuna
richiesta di rete. Nessuna stima predittiva**: nessun walk-forward, nessun
iperparametro — il blocco *conta e misura*, ed e' l'analogo di R0. **Nessun
numero pubblicato e' cambiato**, verificato rieseguendo: `run_phase1.py` ridà
4.034 / 4.432 / 3.637 / 5.105 su 562.672 eventi, `run_phase5.py` ridà Como 4.34 e
5.03 / 191 / [151, 240].

**Apre la Fase 12, chiesta dall'utente il 2026-08-13**: il modello dei **tiri**
(tentativi totali) per **qualsiasi** squadra, non piu' i soli tiri in porta del
Como. Quattro decisioni dell'utente: bersaglio **`shots` e `sot` gerarchici**,
perimetro **cinque stagioni**, uso **within-season** (l'unica forma validabile —
la pre-stagione vorrebbe un'ancora che per le altre 19 squadre non esiste),
predittori **gli stessi otto**, ritestati.

```
strato 1 (volume)      shots_ij ~ NB2(lambda_ij, r)
strato 2 (precisione)  sot_ij | shots_ij ~ Binomiale(shots_ij, p_ij)
```

| | esito |
|---|---|
| `sot <= shots` su 3.778 righe | **0 violazioni** — se cadesse, la binomiale sarebbe *impossibile* |
| `matchId` unico fra le cinque stagioni | **sì**, e nessuno l'aveva verificato: e' la sicurezza del join di `build_predictors` |
| livello dei tentativi | 13,03 → 12,31 (**−5,5%**), quota in porta **ferma** (0,3250-0,3408) |
| correlazione fra i due lati | **−0,349**, e il segno **non era l'attesa** |
| eterogeneita' della precisione | **attacco sì** (tau 2,12 punti, MDE 1,61, z +5,91) · **difesa no** · **campo no** |
| thinning NB2 | **esatto** su 200.000 estrazioni (media +0,10%, `r` +3,8%) |

**Il verdetto: lo strato 2 si stima, ma con il solo lato ATTACCO.** La precisione
e' una proprieta' di chi tira, non di chi difende e non del campo.

- **`phi = 1,101` non rispondeva alla domanda, ed e' l'errore che il blocco esiste
  per non commettere.** Il numero gia' pubblicato e' la dispersione a livello
  **squadra-partita** e mescola rumore di partita, effetto squadra ed effetto
  avversario. «La quota di campionato non si muove fra stagioni» e «la quota non
  varia fra squadre» sono **due nulli diversi**, e il secondo non era mai stato
  testato. A ~12,6 tentativi la sd binomiale della quota vale **13,3 punti** e una
  differenza fra squadre di 2-3 punti ci sparisce dentro; a ~475 scende a **2,2**.
  Il livello sbagliato ha un MDE **2,4 volte peggiore**, e `livello_sbagliato()`
  lo mette in tabella apposta.
- **Il nullo e' generato, non letto da una tabella.** Il `chi2` teorico assume
  binomialita' esatta; con la sovradispersione di partita dentro (`rho` intraclasse
  **0,00827**) il nullo sta a `phi0 ~ 1,17`, non a 1. Un test che la ignorasse
  sarebbe **garantito di rifiutare**, scambiando il rumore di partita per
  eterogeneita' di squadra.
- **La taratura ha CORRETTO il MDE, ed e' il motivo per cui esiste.** Il MDE
  analitico vale 1,38 punti, ma a quel `tau` la potenza **vera** e' **53%**, non
  80%: la formula assume `phi` normale a sd costante, mentre sotto l'alternativa
  la sd cresce. Il MDE pubblicato e' quello **tarato** (1,61), un terzo piu'
  grande. **Ed e' cio' che tiene fuori il lato difesa** (tau 1,39 contro 1,59). Un
  MDE sbagliato nella direzione comoda e' peggio che non averlo.
- **A `tau = 0` la frequenza di rifiuto vale 0,021-0,039**, sotto il 5% nominale e
  coerente con Sidak per k = 3 (~1,7%): **il test non e' liberale**. Senza questa
  riga, «il test ha trovato eterogeneita'» e «il test rifiuta sempre» darebbero lo
  stesso verdetto.
- **La correlazione fra i due lati e' NEGATIVA (−0,349), e l'attesa era il
  contrario.** Si temeva positiva — ritmo, punteggio e arbitro condivisi — il che
  avrebbe gonfiato ogni `t` di questa fase. Il meccanismo vero e' piu' forte: **il
  possesso e' a somma costante**, chi domina tira molto e lascia tirare poco. La
  conseguenza va nel verso **favorevole** (fattore 0,807 sugli errori standard
  appaiati) e va applicata lo stesso: un fattore favorevole non dichiarato resta un
  numero sbagliato.
- **Un difetto vero, trovato perche' due lati diversi davano lo stesso identico
  `phi`**: `sot_conceded` sulla riga `(i, j)` sono i tiri in porta di `j`, quindi
  aggregarli sotto la chiave `j` ricostruisce **l'attacco di `j`**. La chiave della
  difesa e' `team`, non `opponent`. Con una chiave sbagliata ma non degenere sarebbe
  passato.
- **Il disegno sul lato `campo` era sbagliato e l'esecuzione l'ha corretto**: si era
  scritto che fosse «il piu' potente dei tre» per via dell'`n` per cella. Ha **10
  unita' e 5 gradi di liberta'**, quindi li' il test di dispersione e' quasi cieco.
  La strada buona per il campo e' il test F della GLM.
- **Le due strade concordano sull'attacco e non sulla difesa, e non e' una
  contraddizione**: la GLM stima coefficienti invece di dispersione, quindi ha piu'
  potenza e sulla difesa rifiuta (F = 2,83, p = 2,3e-06) mentre il test di
  dispersione dichiara di **non poterla risolvere**. L'effetto difensivo c'e' ed e'
  piccolo.
- **Le linee sono dichiarate prima** (`LINEE_TIRI = (8.5, 10.5, 12.5, 14.5, 16.5)`,
  tassi base 0,77-0,21) e coprono lo **stesso intervallo in deviazioni standard**
  che `validate.LINES` copre sui tiri in porta. **Le linee di `sot` non si
  toccano**: inventarne di nuove renderebbe la Fase 12 non confrontabile con la
  Fase 4.
- **La guardia delle soglie guarda il CODICE, non la prosa.** Le guardie a
  sottostringa di questo repository hanno gia' sbagliato due volte (i voti
  fantacalcio, il `roi` dentro `proiezione` di S1): qui il sorgente e' tokenizzato e
  commenti e stringhe sono esclusi, cosi' che una docstring che spiega **perche' una
  cosa non si fa** non venga punita. Un meta-test verifica entrambe le direzioni.

**Cosa V0 consegna**: a **V1**, il walk-forward **dentro** la stagione (cosi' `mu`
assorbe il livello e non serve un effetto di stagione), `build_predictors` **per
stagione separatamente** (sul concatenato settembre 2023 userebbe maggio 2023 con
peso 0,57), il fattore di cluster **0,807** da applicare a ogni errore standard
appaiato; a **V2**, che lo strato 2 **si stima** col solo attacco, e che **la forma
chiusa del thinning non e' valida cosi' com'e'** — servono entrambe le strade,
chiusa e convoluzione numerica.

**Quattro domande aperte**: (1) il lato **difesa e' al limite** e le due strade lo
trattano diversamente — V2 deve decidere se includerlo **prima** di guardarne
l'effetto predittivo, altrimenti e' un iperparametro scelto sul bersaglio; (2) la
correlazione negativa fra i lati e' **misurata e non spiegata** (il possesso a somma
costante e' compatibile, non verificato); (3) `tau` e' **assunto costante fra
stagioni**, e con 100 unita' non se ne possono stimare cinque; (4) il **totale di
partita** e' la linea di mercato piu' comune e la correlazione negativa dice che
**non e' la somma di due indipendenti** — serve la congiunta, che sui tentativi non
e' misurata.

### Fase 12 — Blocco V1: lo strato del volume ✅ (e qui il modello VINCE)

`reports/fase12_v1_volume.md` + sei CSV, da `scripts/run_fase12_v1.py`; modulo
`sot/volume.py`, test `tests/test_fase12_v1.py` (27). **Nessuna richiesta di
rete.** Unica scrittura sotto `data/`: la cache `fase12_walkforward_tiri.parquet`.
**Nessun numero pubblicato e' cambiato.**

**E' il modello che risponde alla domanda dell'utente**, e il suo risultato e' il
piu' netto che il progetto abbia prodotto su un confronto con i baseline.

| bersaglio | fase | `t` contro `media squadra + campo` |
|---|---|---:|
| tiri in porta | Fase 2 / Fase 4 | 1,86 — dentro il rumore |
| gol | Fase 9 / E3.1 | 5,52 |
| **tentativi** | **Fase 12 / V1** | **9,63** |

**Non e' un modello migliore: e' un bersaglio piu' facile da distinguere.** I
tentativi sono tre volte piu' numerosi dei tiri in porta, quindi il rumore
relativo e' minore, e dipendono dal dominio territoriale, che e' la cosa piu'
persistente che una squadra abbia. Il tiro in porta aggiunge a quel volume un
passaggio di precisione — ed e' proprio quello a renderli piu' rumorosi (V2).

- **3.278 righe valutabili su 3.778**, le stesse di E3 sui gol: due bersagli
  diversi sullo stesso universo devono dare lo stesso perimetro, e un test lo
  pretende. **I cold start sono cinque, non uno** (60 righe senza previsione + 40
  perse per burn-in, per stagione), e sono in colonne separate perche' le due
  cause non si sommano.
- **MAE 3,573 · bias +0,086 · corr 0,494 · pendenza 1,0075 ± 0,0245 (z +0,31)**.
  Il modello e' l'unico candidato informativo compatibile con 1.0; `media squadra
  + campo` e `media squadra` stanno a 0,755 e 0,682 con z −9,6 e −11,3. E' la
  stessa forma dell'argomento della Fase 4, molto piu' netta.
- **Vince in tutte e cinque le stagioni** (t per cluster 3,3-5,5), **su tutte e
  cinque le linee** Brier e **in tutti e sette i segmenti**.
- **Il terzile alto non si inverte, ma si attenua** (delta +0,154 contro +0,362
  del basso). Sui tiri in porta la Fase 4 trovava che li' il modello **perde**:
  e' la stessa firma dello shrinkage — la quinta misura dello stesso effetto dopo
  Fase 3, Fase 4, 6A e R3 — che su un bersaglio piu' informativo non arriva a
  rovesciare il confronto. **Non va corretta.**
- **`r` NB2 = 20,02** contro i 26,0 dei tiri in porta: i tentativi sono
  sovradispersi e la Poisson pura sarebbe sbagliata. Condizionare a lambda porta
  var/media da 2,18 a 1,61, cioe' il modello spiega una parte importante ma non
  tutta. **PIT p = 0,90**, copertura 57,6/84,1/96,4 sul nominale 50/80/95
  (conservativa, com'e' strutturale sui conteggi).
- **`validate.paired_t` ha ora un parametro `cluster`**, con default `None`
  identico bit per bit a prima (un test lo blocca su 1e-12). Serve perche' la riga
  e' la squadra-partita ma l'unita' indipendente e' la **partita**.
- **La previsione di V0 sul fattore di cluster (0,807) NON descrive il confronto
  appaiato**: l'osservato e' 0,92-0,99. Quel fattore riguardava la correlazione
  fra i **valori** dei due lati (forte e negativa); qui conta quella fra gli
  **errori**, che e' debole. La conclusione non cambia, ma il numero di V0 non va
  citato come se descrivesse questo.
- **Vantaggio del campo x1,260** sui tentativi (contro x1,217 sui tiri in porta).
  I ratings sono **una descrizione, non una previsione** (fit su tutta la
  stagione) e stanno sulla scala di `fig5`, cioe' **avversario medio in
  trasferta** e non campo neutro — dichiarato subito invece di doverlo scoprire
  dopo come in 6A. Juventus 14,24 → Cremonese 8,61 nel 2025-26.

> **Una guardia riscritta a fine fase, e il motivo e' generale.**
> `test_v1_scrive_una_sola_cache` contava un letterale (`to_parquet` una volta
> sola) ed e' diventata rossa quando **V3** ha aggiunto `CACHE_PRED` allo stesso
> modulo — cioe' segnalava un fatto **innocuo** invece del fatto che deve
> sorvegliare (il vincolo 9: mai scrivere sotto `raw/`). Ora e' legata alle
> costanti **dichiarate**: pretende che ogni `to_parquet` corrisponda a una
> `CACHE*` e che ognuna stia sotto `processed/`. E' la terza volta che in questo
> repository una guardia scritta su una **forma** invece che su una **proprieta'**
> da' un falso positivo — dopo il gate sui qualifier e le guardie a sottostringa
> del vincolo 3.

**Quattro domande aperte**: (1) perche' la correlazione degli **errori** fra i due
lati sia molto piu' debole di quella dei valori; (2) `r` e' assunto costante fra
squadre e stagioni; (3) il **totale di partita** vuole la congiunta, che sui
tentativi non e' misurata (`lam_subiti` e' gia' nella cache); (4) il `gamma` della
2021-22 non e' confrontabile (ritorno del pubblico).

### Fase 12 — Blocco V2: la precisione ✅ (la gerarchia NON si adotta)

`reports/fase12_v2_precisione.md` + quattro CSV, da `scripts/run_fase12_v2.py`;
modulo `sot/precisione.py`, test `tests/test_fase12_v2.py` (26). **Nessuna
richiesta di rete.** **Nessun numero pubblicato e' cambiato.**

| | esito |
|---|---|
| la quota e' prevedibile meglio di un numero unico? | **no**: lo strato 2 perde contro `p_lega` |
| la difesa (voluta dall'utente) paga? | **no, COSTA**: t = −2,21 |
| la marginale composta batte il modello diretto? | **no**: delta +0,0024, t = 0,60, dentro il MDE |
| il segno e' stabile fra stagioni? | **no**: 3 su 5, il criterio ne chiedeva 4 |
| la composizione e' internamente coerente? | **no**: `r_sot/r_shots` = 1,63, IC95 [1,15, 2,80] |
| **verdetto** | **modello diretto (meno parti)** |

- **L'eterogeneita' che V0 ha trovato e' reale ma NON e' predittiva**, e le due
  cose non si contraddicono. V0 misurava `tau` su squadre-stagione complete (~475
  tentativi); qui il modello deve dire la quota di **una** squadra-partita (~12,6
  tentativi) prima che si giochi, e li' il segnale non sopravvive al rumore. Il
  modello ha correlazione **positiva** con la quota vera (+0,072) e
  verosimiglianza **peggiore**: e' troppo estremo per quanto poco sa. **E' la
  stessa forma del risultato della Fase 2 sugli otto predittori.**
- **`[DECISO 2026-08-13]` l'utente ha voluto la difesa nello strato 2**, contro il
  criterio di V0 che la escludeva (sotto il MDE tarato). **Il criterio non e' stato
  riscritto** e `verdetto_strato2()` continua a rispondere `['attacco']`. Il costo
  e' stato **misurato invece che assunto**: guadagno −0,0085 di log-verosimiglianza
  per riga, t = **−2,21**, cioe' il peggioramento **non e' rumore**. Venti
  coefficienti difensivi stimati su un segnale che il test primario non riusciva a
  risolvere sono venti modi di adattarsi al rumore. **Il criterio di V0 aveva
  ragione, e lo si sa adesso che e' misurato.**
- **Una precisazione a V0**: il report di V0 diceva che la forma chiusa del
  thinning «non e' valida cosi' com'e' perche' `p` varia fra squadre». E'
  **impreciso** — la forma chiusa vale **riga per riga** anche con `p` diverso fra
  righe, purche' dentro la riga sia un numero e non una variabile aleatoria. Cio'
  che la romperebbe e' la variabilita' **dentro** la squadra-partita, cioe' la
  sovradispersione residua (`rho` 0,0083). `pmf_composta(rho > 0)` e' quella
  strada, e le due coincidono a `rho = 0` (verificato a 1e-6).
- **Il rapporto delle dispersioni falsifica la coerenza della gerarchia**, ed e' il
  numero piu' interessante del blocco: sotto il thinning `r_sot` e `r_shots`
  devono essere **uguali**, e l'IC95 non contiene 1. Il verso e' l'**opposto** di
  quello che l'eterogeneita' della quota prevedrebbe (`r_sot > r_shots` = **meno**
  sovradispersione). **Non e' spiegato.**
- **La gerarchia non si adotta, e non perche' sia peggiore: perche' non e'
  migliore.** A parita' si tiene il modello con meno parti, ed e' la regola scritta
  prima. **Cio' che V1 ha prodotto resta intatto e non dipende da questo esito**:
  la gerarchia era il tentativo di ottenere *anche* i tiri in porta dallo stesso
  oggetto, e il tentativo dice di no.

> **Trappola per le sessioni future.** I tre risultati negativi di V2 sono il
> contenuto del blocco. In particolare **non va ritoccato lo strato 2 finche' non
> batte `p_lega`**, e non va tolta la difesa dalla tabella per far tornare il
> conto: la decisione dell'utente e' registrata, il suo costo e' misurato, e le
> due cose vanno lette insieme.

### Fase 12 — Blocco V3: i predittori, ritestati ✅ (terzo negativo, il piu' potente)

`reports/fase12_v3_predittori.md` + tre CSV, da `scripts/run_fase12_v3.py`. **V3
non ha un modulo proprio**: parametrizza `sot/predictor_power.py` su `target`,
eccezione dichiarata alla regola «1 blocco = 1 modulo» perche' duplicarlo
violerebbe «una definizione in un posto solo». Test in `tests/test_fase12_v3.py`
(16). **Nessuna richiesta di rete. Nessun numero pubblicato e' cambiato.**

**Esito: zero candidati tenuti su 24 combinazioni** (8 candidati x 3 regimi). E'
il **terzo** test indipendente con lo stesso risultato — Fase 2 sui tiri in
porta, 6D nei regimi acerbi, V3 sui tentativi.

- **Il default e' identico bit per bit**: `confronto(prev, r)` e
  `confronto(prev, r, target="sot")` danno la stessa tabella, e i numeri di
  `phase6_predittori.csv` si riproducono a 1e-12 (`poss_att` maturo,
  t = 1.4200797158768528). Due test lo bloccano.
- **Il difetto che la parametrizzazione poteva introdurre**, e che un test
  blocca: `_fit` costruiva `TeamModel` **senza** `target`. Siccome `y_in` era gia'
  del bersaglio giusto, il parametro sarebbe *sembrato* funzionare mentre il
  modello veniva stimato su `sot` e valutato sui tentativi.
- **I predittori si costruiscono per stagione**, mai sul concatenato: li'
  `pre_match_ewm` raggruppa per `team`, che e' un nome e si ripete, quindi
  settembre 2023 userebbe maggio 2023 con peso 0,57. La firma verificabile e' che
  **la prima partita di ogni stagione abbia predittori nulli**, e un test la usa.
- **Un errore di lettura corretto per strada, ed e' istruttivo.** Il blocco era
  partito dall'aspettativa che cinque volte le righe dessero un MDE piu' stretto.
  **In unita' assolute e' falso**: il MDE **peggiora** (maturo 0,00282 → 0,00312;
  acerbo disgiunto 0,00483 → 0,01611), perche' la log-verosimiglianza Poisson di
  un conteggio con media 12,6 ha varianza per riga molto maggiore di uno con media
  4,0, e `sqrt(5)` non la compensa. **I MDE di due bersagli diversi non sono
  confrontabili in unita' assolute**, e `mde_relativo()` porta l'unita' che lo e':
  il MDE in **quota del guadagno del modello sul baseline migliore**. Li' il
  maturo passa da 0,118 a **0,023** (5x piu' sensibile), l'acerbo disgiunto da
  0,057 a 0,103 (**peggio**, perche' li' il modello stacca i baseline di piu' e il
  denominatore cresce piu' del numeratore).
- **Due candidati PEGGIORANO oltre la soglia** nel regime acerbo disgiunto —
  `tilt_att` t = −2,48 e `poss_att` t = −2,01 — e la 6D non poteva vederlo: con 40
  righe quei `t` sarebbero stati attorno a −0,8. E' coerente col meccanismo che la
  6D ha reso visibile nei due termini dell'obiettivo: un predittore collineare con
  l'effetto attacco compra riduzione di penalita' ridge e paga in adattamento, e
  **dove l'effetto attacco e' acerbo la sostituzione e' peggiore**.
- **Nessun candidato ha cinque segni positivi** fra le stagioni, il che toglie
  l'ultima lettura possibile di un pooled vicino a zero.
- Nel maturo il massimo vale t = 1,485 con `p = 0,435` su otto candidati, **sotto**
  il valore atteso del massimo di otto normali standard (1,4236).

> **Trappola per le sessioni future.** Terzo esito negativo sullo stesso insieme,
> e il piu' potente in termini relativi. Non va "sistemato" reintroducendo il
> candidato col `t` piu' alto: su otto candidati un massimo di 1,49 e' esattamente
> quanto ci si aspetta sotto il nullo, e il blocco lo **calcola** invece di
> lasciarlo intuire.

### Fase 12 — Blocco V4: il ponte ✅ — **e' cio' che l'utente ha chiesto**

`reports/fase12_v4_ponte.md` + `fase12_v4_tiri_attesi.csv` (760 righe) +
**`reports/fase12_v4_simulatore.html`**, da `scripts/run_fase12_v4.py`
(+ `scripts/pagina_v4.py`); modulo `sot/previsione.py`, test
`tests/test_fase12_v4.py` (29). **Nessuna richiesta di rete, nessuna scrittura
sotto `data/`. Nessun numero pubblicato e' cambiato.** Chiude la Fase 12.

```python
from sot import previsione as P
p = P.previsione("Como", "Inter", "casa")
p["lambda_tentativi"]   # 12.852
p["p_over"]             # P(Over) per le cinque linee + quota di pareggio
p["intervalli"]         # 50 / 80 / 95%
```

- **Prima non esisteva.** `soglie_2627` aveva il ponte per il **solo Como** e il
  **solo 2026-27**, ancorato a un livello **fornito dall'utente** che per le altre
  diciannove squadre non esiste. Qui il livello non serve: la previsione e'
  **within-season**, il modello sa gia' quanto tira ciascuna squadra. Ed e'
  l'unica forma **validabile** — V1 la misura su 3.278 righe.
- **760 coppie**, da **6,55** (Cremonese-Como in trasferta) a **21,42**
  (Juventus-Cremonese in casa): **un fattore 3,27**, contro una media di
  campionato di 12,31. Un numero unico per squadra non basta, e nemmeno un numero
  per squadra piu' il campo: **l'avversario sposta il lambda quanto il campo**.
- **La guardia sulla squadra sconosciuta sta a DUE livelli, e servono entrambi**:
  `verifica_squadre` all'API e `TeamModel(strict_teams=True)` nel modello — una
  guardia sola all'ingresso si aggira chiamando il modello direttamente. Il
  difetto e' **silenzioso**: la dummy resta a zero e la squadra viene trattata
  **come esattamente media**, senza errore ne' avviso. Il caso realistico non e' la
  squadra inventata: e' chiedere **Como-Venezia nel 2025-26**.
- **`strict_teams` ha default `False`** e un test verifica l'identita' **bit per
  bit**: dentro il walk-forward il coefficiente zero e' il comportamento *giusto*
  (una squadra alla sua prima apparizione in un training parziale), e sollevare
  romperebbe Fase 2, E3 e R0-R3.
- **`campo` e' una stringa e non un booleano**: uno `0/1` si scambierebbe senza
  rumore, e la differenza casa/trasferta vale un quarto del livello.
- **`al` non e' cosmetico**: e' la data a cui ci si mette, e `dentro_campione`
  **dichiara** se la partita chiesta e' gia' nella storia usata invece di lasciar
  credere che sia una previsione.
- **I tiri in porta vengono dal modello DIRETTO**, non dalla gerarchia: V2 l'ha
  misurata e non l'ha adottata.
- **La pagina locale e' autonoma** — nessun CDN, nessun font remoto, nessuna
  richiesta di rete, e un test lo pretende. **Nessuna quota** (vincolo 3): mostra
  la quota di **pareggio** (`1/p`), dichiarata come il punto in cui il guadagno
  sarebbe zero, non come una previsione di prezzo.

**Quattro domande aperte**: (1) `al` e' esposto ma il report non lo esercita
giornata per giornata — sarebbe la coda naturale del blocco; (2) la stagione e'
una sola; (3) **il totale di partita non e' esposto** ed e' la linea di mercato
piu' comune: serve la congiunta, che V0 ha mostrato **non** essere quella di due
indipendenti (correlazione −0,35); (4) senza prezzi di mercato reali «il modello
e' meglio del mercato» resta una frase che questo progetto non puo' pronunciare.

### Fase 13 / G2 — i cinque campionati, bersaglio GOL ⏳ (aperta, M1 chiuso)

Aperta dall'utente il **2026-08-14**. Sblocca il ramo **G2**, che la Fase 10
teneva chiuso dietro una condizione di autorizzazione. Decisioni in
`docs/regole_fantacalcio.md` **§7.2**, che e' il posto dove stanno e non questo.

| # | decisione dell'utente |
|---|---|
| 1 | **autorizzazione WhoScored estesa** a Premier League, Liga, Bundesliga, Ligue 1 |
| 2 | perimetro **cinque stagioni per campionato** (~7.000 partite, ~18 GB) |
| 3 | bersaglio **gol segnati** |
| 4 | **progressivo** = avanzamento in x >= 10 m **e riuscito** |
| 5 | metriche nuove: **tocchi per zona** (5 zone) e famiglia dei progressivi |

#### Le terne WhoScored sono ACCERTATE, non ricavate a memoria ✅

`acquisition/whoscored/verifica_terne.py` +
`reports/fase13_terne_whoscored.json`. `config.LEAGUE_CODES` non ha piu' nessun
`whoscored: None`.

Il disegno e' una **falsificazione**: si dichiara una terna candidata, si carica
la pagina e si pretende che il **`canonical` della fonte** rimandi indietro gli
**stessi id** e lo slug atteso. Tre controlli la rendono leggibile — la Serie A
(gia' accertata) **deve passare**, un nome sbagliato e una coppia di id
inesistenti **devono fallire**. Con id inesistenti il sito **non ripiega su una
competizione a caso**: cade sulla homepage senza `canonical`, quindi «il
canonical contiene i miei id» non e' una tautologia.

| campionato | regione | torneo | slug |
|---|---:|---:|---|
| ENG-premier-league | 252 | 2 | `england-premier-league` |
| ESP-la-liga | 206 | 4 | `spain-laliga` |
| GER-bundesliga | 81 | 3 | `germany-bundesliga` |
| FRA-ligue-1 | 74 | 22 | `france-ligue-1` |

> **La prima stesura della verifica ha sbagliato in due modi opposti insieme**,
> ed e' la lezione del blocco. Cercava il paese in **inglese** dentro un **blob
> concatenato** di tutti i campi: il sito serve la localizzazione italiana
> (`it.whoscored.com`, «Italia/Inghilterra/Spagna/Germania/Francia»), quindi
> quattro terne giuste sono state **rifiutate**; e la Ligue 1 e' stata
> **confermata da "Coupe de France"**, che e' un'altra competizione elencata nel
> breadcrumb. **Un criterio su un testo unito produce falsi positivi e falsi
> negativi nello stesso momento.** Ogni controllo va cercato nel campo in cui
> significa qualcosa. Il controllo positivo ha impedito il danno: fallendo lui,
> lo script si e' rifiutato di dichiarare qualsiasi terna.

**Due fatti nuovi sull'acquisizione, rilevati e non assunti:**

1. **Il mirror `1xbet.whoscored.com` non esiste piu'**: risponde **301** verso
   `www.whoscored.com` (2026-08-14). La domanda di §7.1 decisione 3 — «se
   l'autorizzazione copre WhoScored ma non il mirror» — si e' risolta da se'.
   `main.py:60` punta ancora al vecchio dominio e segue il redirect.
2. **`main.py` istanzia `webdriver.Firefox()` in tre punti (66, 121, 240) e
   Firefox NON e' installato su questa macchina.** C'e' Chrome 151 e Edge 151.
   **L'acquisizione dei quattro campionati non partirebbe cosi' com'e'**, ed e'
   un blocco indipendente dalle terne. `verifica_terne.py` usa Chrome e prova
   che la strada del browser funziona, ma **non tocca `main.py`**: il difetto
   resta dichiarato, non aggirato di nascosto.

#### Blocco M1 — le metriche avanzate ✅

`reports/fase13_m1_metriche_evento.md`, modulo `sot/metriche_evento.py`, test
`tests/test_fase13_m1.py` (23). **Nessuna richiesta di rete, nessuna stima**:
conta e misura, come R0 e V0. Suite a **961 test**, tutti verdi.

**Le cinque zone sono una partizione, e la prova non passa dai dati veri**: gira
su una griglia fitta che copre tutto il campo, perche' un buco in un angolo che
la Serie A non ha mai visitato comparirebbe su un altro campionato — cioe'
proprio dove la fase sta andando. Sui dati veri 468.883 tocchi, **zero senza
zona**, quote che sommano a 1 con scarto **2,2e-16**. **La geometria si importa
da `features.py`**, non si riscrive, e un test verifica che non sia ridefinita.

**Il vincolo 7 dentro una fonte sola — «passaggio riuscito» ha due
derivazioni.** `passAccurate = True` implica **sempre** `Successful` (zero
contraddizioni su 273.027), ma **l'8,3% dei passaggi non ha nessuno dei due
flag** e fra questi 17.440 sono riusciti. I non marcati sono **piu' lunghi**
(22,2 m contro 18,0). **Si usa `outcomeType`**: `passAccurate` scarterebbe in
silenzio il 6% dei riusciti **sbilanciato verso i lunghi**, cioe' esattamente la
popolazione che definisce un progressivo — un errore **sistematico**, non rumore.

**Le tre letture del progressivo restano colonne separate** (vincolo 7):
`prog_tentati` 137,8 · **`prog_riusciti` 88,9 (la scelta)** ·
`prog_per_distanza` 231,6 per squadra-partita. **Nessuna coincide con i
"progressive passes" dei fornitori standard** (~40-50), che usano l'avanzamento
relativo alla distanza dalla porta: e' una definizione diversa, dichiarata.
**I 10 m sono una soglia NOMINALE** — 9,52 unita' di `x` sul campo 105x68
assunto da `features.py`, mentre la norma FIFA ammette 100-110 x 64-75.

> **`completamenti_profondi_cross_inclusi` ha quel nome lungo apposta.** La
> *deep completion* standard **esclude i cross**, e in `events_slim` **non c'e'
> nessun flag di cross**. Chiamarla `deep_completions` avrebbe prodotto una
> tabella dell'ordine di grandezza giusto e del contenuto sbagliato: e'
> `passFreekick` (E4) evitato in anticipo.

**Il gate di deriva di E1 sulle cinque stagioni separa nettamente**, e la prima
lettura non era prevista:

- **`prog_riusciti` passa (4,56%), `prog_tentati` no (6,81%)**: il filtro sulla
  riuscita **stabilizza la grandezza fra stagioni**. La decisione dell'utente
  risulta la piu' robusta delle tre *dopo* averla presa, non prima.
- **Le quote passano sistematicamente dove i conteggi falliscono**, che e'
  esattamente cio' che la regola di E1 prevede.
- Oltre soglia: `metri_progressione` **23,6%**, `metri_per_passaggio` 19,9%,
  `completamenti_profondi` 14,2%, `ingressi_area` 11,8%, `tocchi_area_off`
  8,4%, `tocchi_terzo_off` 7,3%, `prog_tentati` 6,8%, `quota_tocchi_area_off`
  5,1%. **Non entrano grezze** in un modello multi-stagione, tanto meno
  multi-campionato.
- `prog_riusciti` scende 92,8 → 88,9, **coerente con la caduta gia' documentata
  dei tentativi** (13,03 → 12,31): si gioca piu' corto, non si annota diverso.

> **Trappola per le sessioni future.** M1 **non ha testato se queste metriche
> predicano qualcosa**, ed e' voluto. I predittori da dati evento sono gia'
> stati scartati **tre volte** (Fase 2, 6D, V3): il quarto test va disegnato con
> la **potenza dichiarata prima**, e in **MDE relativo** al guadagno del modello
> sul baseline — V3 ha mostrato che in unita' assolute piu' righe **peggiorano**
> il MDE. E **`tocchi_area_off` non e' una candidata nuova**: e' `box_touches`,
> gia' fra le otto bocciate. Sta li' perche' completa la partizione.

#### Acquisizione ✅ — 8.884 partite, 23 GB, copertura 100% della fonte

| campionato | acquisite | attese | assenti alla fonte |
|---|---:|---:|---:|
| Serie A | 1.889 | 1.901 | 12 |
| Premier League | 1.897 | 1.900 | 3 |
| Liga | 1.899 | 1.900 | 1 |
| Bundesliga | 1.528 | 1.530 | 2 |
| Ligue 1 | 1.671 | 1.678 | 7 |

**Le 25 mancanti sono TUTTE `matchCentreData: null` alla fonte**, accertate da
una passata di chiusura e non assunte: non si recuperano e non vanno ritentate.
**Integrita' verificata**: 8.884 CSV, zero vuoti, zero troncati — nonostante
molti spegnimenti del PC a scaricamento in corso.

**Le assenze sono casuali rispetto alla squadra in QUATTRO campionati su
cinque.** L'eccezione e' la sola Serie A: l'**Atalanta** ne perde 6 contro
un'attesa di 1,2, p grezzo 0,0014 e **0,038 corretto** per aver scelto il
massimo fra le squadre. Negli altri quattro il massimo e' 1-2 partite per
squadra (p corretto 0,93-1,00). **L'anomalia e' dell'archivio Serie A, non una
proprieta' di WhoScored.**

> **Tre difetti trovati eseguendo, tutti gia' costati dati.** (1) Un **banner**
> sopra `<select id="seasons">` sollevava `ElementClickInterceptedException` e
> **costava un'intera stagione in silenzio** — era lo STESSO difetto gia' pagato
> dalla Serie A e corretto allora sul solo menu `stages`, cioe' sul punto d'uso
> invece che sulla classe: il ripiego ora sta in `_seleziona_con_ripiego`, in un
> posto solo. (2) `scarica()` restituiva **meta' del risultato** (`failed` senza
> `senza_dati`): il riepilogo andava in errore **solo a copertura piena** e con
> esattamente due fallimenti avrebbe mentito in silenzio — ed e' la correzione
> che ha reso possibile classificare le 25. (3) Un **browser morto** faceva
> ciclare lo scraper sul resto della stagione marcando ritentabili centinaia di
> partite mai tentate (236 sulla Ligue 1): ora `_driver_morto` interrompe la
> stagione. **L'acquisizione NON era bloccata da Firefox**: Selenium Manager lo
> risolve da se', e la diagnosi contraria era sbagliata.

#### Il modello dei GOL sui cinque campionati ✅ — **trasferisce**

`reports/fase13_gol_cinque_campionati.md`, da `scripts/run_fase13_gol.py`.
**Nessun modello nuovo**: e' `TeamModel(target="gol_fatti")` di E3.1 su
campionati diversi. **Un fit per campionato, mai poolati** (§7.2, conseguenza 3).

| campionato | n | MAE | pendenza | delta | **t (cluster)** | MDE | delta/MDE |
|---|---:|---:|---:|---:|---:|---:|---:|
| Serie A | 3.278 | 0,8720 | 0,898 | 0,0302 | **5,40** | 0,0159 | 1,90 |
| Premier League | 3.294 | 0,9554 | 0,929 | 0,0271 | **4,80** | 0,0160 | 1,69 |
| Liga | 3.298 | 0,8634 | 0,947 | 0,0198 | **3,56** | 0,0158 | 1,25 |
| Ligue 1 | 2.872 | 0,9498 | 0,868 | 0,0190 | **3,09** | 0,0175 | 1,09 |
| Bundesliga | 2.606 | 1,0040 | 0,887 | 0,0102 | **1,44** | 0,0201 | **0,51** |

- **Il vantaggio sul baseline migliore regge in quattro campionati su cinque**,
  t fra 3,1 e 5,4. Non era scontato: poteva essere una proprieta' della Serie A.
- **Il 5,52 della Serie A riproduce E3.1 a ogni cifra**, ed e' il controllo che
  vale piu' del risultato nuovo.
- **La Bundesliga non e' un nullo: e' un test senza potenza.** delta/MDE =
  **0,51**, cioe' l'effetto osservato e' meta' del minimo rilevabile. «Qui il
  confronto non conclude» e' l'affermazione difendibile; «non funziona» no.
  Cause misurate: 18 squadre (2.606 righe contro 3.278) e piu' gol (1,51-1,59
  contro 1,18-1,32), quindi bersaglio piu' rumoroso.
- **Il `t` per cluster di partita non cambia niente** (scarto < 5% ovunque), ed
  e' la **replica di V1**: la correlazione forte misurata da V0 (−0,349) e' fra
  i **valori** dei due lati, non fra gli **errori**. Il fattore 0,807 di V0 non
  descrive questo confronto.
- **PIT p fra 0,17 e 0,77** e zeri osservati ~ attesi in tutti e cinque: regge
  la forma, non solo la media.
- **Il livello varia del 25% fra campionati** (Bundesliga 1,51-1,59 contro Liga
  1,22-1,32): un fit unico avrebbe attribuito il contesto ai coefficienti di
  squadra. E' la regola di E1 resa un numero.

> La **pendenza e' sotto 1 in tutti e cinque** (0,868-0,947): e' lo shrinkage
> della ridge, la **sesta** misura dello stesso effetto dopo Fase 3, 4, 6A, R3 e
> V1. Non va corretta.

**I cinque campionati non si poolano** (§7.2, conseguenza 3): e' la regola di E1
e R0 l'aveva gia' scritta in anticipo proprio su G2. O cinque fit separati, o il
campionato come **effetto esplicito**. E **il calendario non e' 380 partite per
tutti**: Bundesliga ha 18 squadre e Ligue 1 e' passata a 18 dalla 2023-24 — i
denominatori si **contano**, mai si assumono.

### Fase 14 — la stagione IN CORSO ✅

Aperta dall'utente il **2026-08-30**. Due richieste: un aggiornamento automatico
dei dati evento dei cinque campionati per la stagione nuova, e una previsione di
**tiri e tiri in porta** su una partita futura a scelta. Decisioni dell'utente:
prior dalla stagione precedente per coprire l'avvio · **nessuno scraping delle
partite future** (la partita si sceglie per nome) · l'interfaccia e' la **pagina
HTML autonoma** · aggiornamento **il martedi' alle 21:00** (ora decisa
dall'utente il 2026-08-31), con recupero al primo momento utile se il PC era
spento, piu' il lancio su richiesta.

**Nessun numero pubblicato e' cambiato**, verificato rieseguendo: `run_phase1.py`
ridà 4.034 / 4.432 / 3.637 / 5.105 su 562.672 eventi, `run_phase5.py` ridà Como
4.34 e 5.03 / 191 / [151, 240], `run_fase12_v4.py` ridà 12,85 · 6,55 · 21,42,
`run_fase13_gol.py` ridà t = 5,40 sulla Serie A. Suite a **1.019 test**.

#### A0 — la catena era cablata sulla Serie A senza dirlo

`multistagione.carica` chiamava `config.team_match(season=…)` **senza
campionato**, quindi tutto cio' che sta a valle — `tentativi.universo`, `volume`,
`previsione` — rispondeva con numeri italiani a qualunque campionato le si
chiedesse. E' lo stesso difetto che E0 aveva trovato in `aggancio.mappa_giocatori`
(`stagione` nella firma, `config.PLAYER_MATCH` nel corpo). Ora `league=None`
attraversa la catena e un test pretende l'identita' **bit per bit** col default.

- **`config.SEASON_CORRENTE` NON entra in `SEASONS_STORICHE`**, ed e' l'invariante
  che tiene in piedi la fase: quella tupla e' il default di mezzo repository
  (`previsione` ne prende l'ultimo elemento, `universo` e `walkforward_tiri` la
  usano quando `stagioni is None`), e allungarla sposterebbe in silenzio ogni
  numero validato dalle Fasi 0-13 senza che un solo test se ne accorga.
- **Le cache diventano una per campionato**, e la Serie A resta **dove era**:
  cambia la cartella, non il nome del file, perche' `processed_league_dir` gia'
  separa i campionati.
- **Un difetto latente corretto**: `walkforward_tiri` leggeva la cache
  **qualunque** cosa fosse passata in `stagioni`, quindi chiedere una stagione
  sola restituiva in silenzio il walk-forward di tutte e cinque.

#### A1 — l'aggiornamento settimanale

**Una stagione in corso e' incompleta per definizione**, e il criterio di arresto
dello scraper (`report_completeness`) non lo sa: ogni esecuzione avrebbe pagato
`MAX_URL_PASSES = 4` navigazioni complete del calendario per cercare partite non
ancora giocate. Il flag `--in-corso` cambia due cose e nessuna e' cosmetica —
**una passata sola**, e la **cache degli URL sempre rinfrescata** (li' una cache
completa e' la risposta definitiva, qui e' vecchia di sette giorni per
costruzione). Le partite gia' in cache non si perdono mai.

- **`avanzamento()` non e' `report_completeness` con un flag**, ed e' voluto:
  quella ritorna un **booleano** che lo scraper usa come criterio di arresto,
  questa una **misura**. Farle dire `True` significherebbe far dire «completo» a
  un calendario che non lo e'. Il denominatore si deduce dalle squadre viste, mai
  assunto a 38 — la Bundesliga e la Ligue 1 ne hanno 34.
- **La navigazione all'indietro basta**, e le partite future **non** si scaricano
  (decisione 2): se entrassero in `matches.json` lo scraper proverebbe a
  scaricarne gli eventi a ogni giro, fallendo ogni volta.
- **`build_cache` e' idempotente per ESISTENZA del file**: con CSV nuovi e
  `force=False` restituirebbe il Parquet della settimana prima. `aggiorna_stagione`
  forza **se e solo se** almeno un CSV e' piu' recente dei Parquet.
- **Sotto `xg.N_FOLDS` partite i derivati si saltano**, non si costruiscono a
  meta': il `GroupKFold` dell'xG non ha abbastanza gruppi. La soglia non e'
  scelta, e' imposta dalla procedura.
- **L'attivita' pianificata e' un XML e non una riga di `schtasks /SC WEEKLY`**
  per una voce sola: `StartWhenAvailable`, che fa partire l'aggiornamento al
  primo momento utile se il martedi' il PC era spento. `schtasks` da riga di
  comando non la espone. **Registrata il 2026-08-31**, martedi' 21:00, stato
  `Ready`, prima esecuzione 2026-09-01: e' quella che fara' il primo
  scaricamento della 2026-2027, che fino a li' non e' mai stato lanciato.
- **Provenienza falsa corretta**: `manifest.DEFINIZIONI` dichiarava ancora
  `1xbet.whoscored.com` come dominio contattato, mentre `main.py` punta a `www`
  dal 2026-08-14. Il mirror resta **citato** — i file vecchi ci sono passati — ma
  non come dominio corrente.

#### A2 — il prior: l'ipotesi cade, e cio' che vince e' il diagnostico ⚠️

`TeamModel` guadagna `prior` e `alpha_prior`: il centro della penalita' ridge si
sposta da zero (media di campionato) ai coefficienti di **fine stagione
precedente**. `prior=None` e' identico bit per bit, con un test che lo blocca.

**Il criterio di adozione era scritto prima** (`CRITERIO_ADOZIONE`) e
`verdetto()` lo applica meccanicamente. **NON e' soddisfatto su nessuno dei due
bersagli**: sui tentativi t = 0,40 (ne serviva > 2) e 3 campionati su 5 positivi;
sui tiri in porta t = **−2,82**, cioe' la miscela e' **significativamente
peggiore** del baseline «media squadra dell'anno scorso».

**Cio' che vince e' `modello prec`** — la stagione precedente applicata **tale e
quale**, senza guardare una sola partita nuova, cioe' il caso limite
`alpha_prior → ∞`. Era il **diagnostico** del blocco, messo li' apposta perche'
senza di lui un negativo sarebbe stato ambiguo (non si saprebbe se a non
funzionare fosse il *prior* o la *miscela*). Poolato sulle transizioni tarate,
righe di avvio (`team_match_idx ≤ 5`), 1.386 righe e 697 partite:

| bersaglio | `modello prec` batte «media squadra prec» | delta/MDE | batte la miscela |
|---|---:|---:|---:|
| tentativi | +0,0906 · **t 4,36** | 1,56 | t 3,33 |
| tiri in porta | +0,0423 · **t 4,25** | 1,52 | t 4,73 |

Soglia di Sidak su cinque candidati dichiarati: |t| > 2,32. Entrambi la passano.

**Sul controllo il quadro si rovescia**, ed e' cio' che rende la lettura
coerente invece che contraddittoria: da `team_match_idx` 6 in poi vince la
**miscela** (t 2,02 sui tentativi e 2,55 sui tiri in porta contro `modello prec`;
4,97 contro il within-season puro sui tiri in porta). Le poche partite di
settembre non aiutano; dalla sesta in poi si'.

Ne segue la **regola a due regimi** (`REGOLA_DUE_REGIMI`), che **non e' un terzo
modello**: e' la composizione di due candidati gia' dichiarati a una soglia
dichiarata **altrove** — `config.BURN_IN_ROUND`, che la Fase 2 ha fissato e che
tutto il repository usa. La stessa disciplina con cui la Fase 8 ha tenuto l'80'
invece di leggerlo da un `argmax`.

- **Lo scambio vero cade attorno alla 4a giornata, non alla 6a**, e il fatto e'
  **scritto, non usato**: spostare la soglia li' sarebbe sceglierla guardando il
  campione su cui poi la si valuta. Il costo e' piccolo e sta in tabella.
- **`alpha_prior` si sceglie sul solo passato**: per valutare la transizione
  verso `s` si usa la migliore delle transizioni precedenti, e la prima resta
  **marcata come non tarata** — la stessa forma della 2021-2022 non ricalibrata
  di R2-bis. Gli ottimi cadono all'interno della griglia tranne che sulla
  Bundesliga, dove il report lo segnala.
- **Il prior si scioglie da solo**, e non c'e' nessun decadimento da
  sintonizzare: la verosimiglianza cresce con `n` e la penalita' no.
- **Il prior porta la forza RELATIVA, non il livello** (`mu` e `gamma` non sono
  penalizzati). E' cio' che evita il difetto gia' misurato in E4 sui cinque fit
  di xG e in V0 sui tentativi: forma stabile, livello che si muove.
- **Le neopromosse non hanno prior e prendono centro zero**, cioe' la media di
  campionato dell'anno scorso. E' l'unico default onesto, ed e' il motivo per cui
  il prior va **centrato**: senza, quello zero sarebbe un punto arbitrario
  accanto alla media e le tre promosse finirebbero tutte dalla stessa parte per
  un motivo aritmetico. Vengono **contate** e dichiarate, mai lasciate sparire.

> **Trappola per le sessioni future.** Il criterio scritto prima **non e' stato
> riscritto per farlo tornare**, ed e' la stessa disciplina di `LATI_STRATO2` in
> V2: `verdetto()` continua a rispondere «non adottato» per la miscela sulle
> righe di avvio. Cio' che si adotta e' `modello prec` sotto il burn-in, che e'
> un candidato **dichiarato prima** e che passa la correzione per molteplicita'.
> **Non va ritoccato `alpha_prior` finche' la miscela supera il baseline**: il
> segno e' spiegato da un meccanismo misurato — con quattro-otto partite le
> nuove informazioni sono meno del rumore che introducono — e cambiarlo
> cancellerebbe la spiegazione.

#### A3 — i tiri in porta accanto ai tiri

`previsione()` restituiva `lambda_sot` ma **nessuna probabilita' Over** per i
tiri in porta. Ora ci sono, su **`validate.LINES` invariate** (2,5-5,5):
`tentativi.LINEE_SOT_INVARIATE` lo prescrive, perche' linee nuove renderebbero
questi numeri non confrontabili con la Fase 4.

- **Una `r` per bersaglio e per campionato**: ~20 sui tentativi, **31,6** sui
  tiri in porta. Non si eredita, e `volume.walkforward_tiri` e' parametrizzata su
  `target` con una cache separata perche' altrimenti la seconda sovrascriverebbe
  la prima.
- **`quota_pareggio` ora si IMPORTA davvero da `soglie_2627`.** La docstring di
  `previsione.py` lo dichiarava dalla Fase 12 e il codice riscriveva `1.0/p` a
  mano: due copie che coincidevano per caso, e il test verificava l'uguaglianza
  **numerica** invece dell'unicita' della definizione.

#### A4 — la pagina

`reports/previsioni.html`, autonoma (nessun CDN, nessun font remoto, nessuna
richiesta di rete) e con quattro selettori: **campionato**, squadra, avversario,
campo. Per ogni coppia: λ tiri, λ tiri in porta, precisione implicita, P(Over) e
quota di **pareggio** su entrambe le famiglie di linee. **Nessuna quota**
(vincolo 3).

- **Il regime e' dichiarato riga per riga**, accanto al numero e non in fondo:
  sotto il burn-in la pagina scrive che quel numero viene dalla stagione
  precedente, e conta le squadre che il prior non conosce.
- **Le squadre non si ereditano dal prior**, mai: prenderle da li' rimetterebbe
  dentro le **retrocesse**. Si prendono dalle partite viste in questa stagione, e
  alla prima giornata sono percio' meno di venti — il conteggio lo dichiara.
- **Il ripiego di stagione e' dichiarato**: se la stagione chiesta non ha ancora
  dati si scende alla piu' recente che ne ha e **lo si scrive**. Mostrare i
  numeri dell'anno scorso credendo che siano di quest'anno e' il difetto peggiore
  che questa pagina possa avere.
- **Il generatore non calcola niente**, come `pagina_v4`: serializza una tabella
  gia' prodotta da `previsione`. Un solo conto qui e pagina e modello potrebbero
  divergere senza che nessuno se ne accorga — un test lo blocca.

#### Due guardie di E0 corrette, e sorvegliavano un formato invece di una proprieta'

Trovate rieseguendo `run_phase1.py`, che e' un passo di **verifica** prescritto
da questo documento: rigenerando il Parquet della 2025-2026 sono diventate rosse
due guardie che passavano solo perche' i dati su disco erano **piu' vecchi del
codice**.

1. **`test_xg_fit_dichiara_la_stagione`** pretendeva `xg_fit == stagione`, cioe'
   la forma che `etichetta_fit` aveva **fino alla Fase 13**: da li' e'
   `campionato/stagione`, perche' con cinque campionati i fit sono venticinque e
   `"2025-2026"` ne identificherebbe cinque. Ora verifica la **proprieta'** — un
   valore solo, che contiene la stagione, e se contiene anche il campionato deve
   essere quello dichiarato da `etichetta_fit`.
2. **`test_le_medie_non_stanno_dentro_player_match`** cercava `"campionato" not
   in c` e puniva la colonna `campionato`, che e' legittima e sta nella lista
   dichiarata di `build_player_match`. Ora cerca `media_campionato`, con un
   controllo positivo che pretende la colonna vera.

> **E' la quinta volta** che in questo repository una guardia scritta su una
> **forma** invece che su una **proprieta'** da' un falso positivo — dopo il gate
> sui qualifier (E1), le guardie a sottostringa del vincolo 3 (S1), la cache di
> V1 e il `--league` di questa stessa fase. Il fatto che i Parquet fossero
> stantii e' un secondo avviso: **un test che sorveglia un formato dichiara verde
> una cache vecchia**.

**Cinque domande aperte**: (1) **lo scambio dei due regimi cade alla 4a e la
soglia usata e' la 6a**, per disciplina: misurare quanto costi vorrebbe una
soglia scelta fuori campione, cioe' altri campionati o altre stagioni; (2) perche'
le partite di settembre **peggiorino** invece di essere neutre non ha una
spiegazione misurata — il sospetto e' `mu` e `gamma` ristimati su 4-8 partite, ma
non e' stato separato; (3) **il calendario 2026-27 non e' nel repository**, quindi
la partita si nomina a mano: scaricarlo vorrebbe la navigazione in avanti e un
modo **misurato** di distinguere una partita non giocata (l'orario `20:45` si
legge come punteggio `20:45`); (4) `alpha_prior` e' assunto costante dentro una
stagione, mentre il peso giusto del prior cala giornata dopo giornata; (5) senza
prezzi di mercato reali «il modello e' meglio del mercato» resta una frase che
questo progetto non puo' pronunciare.

### Fase 15 / Blocco C1 - il calendario della stagione in corso ✅ (due fonti)

`acquisition/whoscored/verifica_calendario.py` (il verbale
`reports/fase15_calendario_verifica.json`), l'estensione di
`acquisition/whoscored/scrape_season.py`, il pacchetto nuovo
`acquisition/wikipedia/`, il modulo `sot/calendario.py` e i test
`tests/test_fase15_calendario.py` (35). **Tocca la rete**, ed e' il primo blocco
dopo la Fase 14 che lo faccia.

**Il blocco comincia da una verifica falsificabile, non dallo scraper**, perche'
poggiava su un'ipotesi mai osservata: che WhoScored avesse una navigazione in
avanti. `dayChangeBtn-next` **non compariva in nessun punto del repository**.

| controllo | esito |
|---|---|
| `dayChangeBtn-next` esiste e **muove** la pagina | **si** |
| positivo: 30 righe di stagione conclusa | **30/30 giocate, 30/30 gia' su disco** |
| negativo: 30 righe future | **0/30 giocate, 0/30 su disco** |
| i due criteri indipendenti discordano? | **0 volte** |

**Cio' che si e' accertato, e che era congettura:** una partita da giocare ha
**`/show/`** nell'href — non `/preview/`, che era l'ipotesi — e mostra **`-:-`**
al posto del punteggio. Ne segue che la domanda aperta n. 3 della Fase 14
(«l'orario `20:45` si legge come punteggio `20:45`») **su WhoScored non si pone**.
Si pone eccome su **Wikipedia**, dove l'orario sta davvero nella cella del
risultato: due fonti, due discriminanti, e non si scambiano (vincolo 7).

**Il calendario futuro va in un file SEPARATO** (`calendario.json`), e la ragione
e' misurabile, non organizzativa: `matches.json` e' il criterio di arresto dello
scraper (`report_completeness`) e il denominatore di `avanzamento`. Mescolarci le
partite da giocare manderebbe la quota a **1,00 dal giorno zero** e farebbe
ritentare ogni settimana lo scarico di partite non ancora giocate.

**Serie A 2026-2027: 360 partite da giocare + 20 gia' giocate = 380.** Nessuna
violazione di struttura, 360 accoppiamenti unici, 20 squadre — e le promosse
sono **Frosinone, Monza, Venezia**, cioe' esattamente quelle che la Fase 11
aveva dichiarato da fonte esterna: corroborazione indipendente, non usata per
costruirle.

#### La seconda fonte: Wikipedia, perche' la giornata a WhoScored NON c'e'

Le due fonti **non sono ridondanti**:

| | WhoScored | Wikipedia |
|---|---|---|
| URL e `matchId` | **si** | no |
| **giornata di campionato** | **NO** | **si** |
| copertura 2026-2027 | completa | variabile per campionato |

Sulla Serie A Wikipedia da' **380/380 partite su 38 giornate, completo e senza
violazioni**, e le sue 20 giocate coincidono con i 20 CSV su disco. La
riconciliazione (`sot/calendario.py`) aggancia **20 squadre su 20** con due soli
nomi diversi (`Milan` → `AC Milan`, `Parma` → `Parma Calcio 1913`), e il
confronto incrociato torna esatto: **360 comuni, 0 solo-WhoScored**, e le 20
solo-Wikipedia sono le gia' giocate, che il calendario futuro esclude per
costruzione.

Sugli altri quattro campionati la pagina italiana e' **parziale o incoerente** e
il blocco lo **dichiara** invece di forzarla: Premier 303/380 e Bundesliga 32/306
(pulite ma incomplete), Liga 35/380, Ligue 1 272/306 con accoppiamenti ripetuti
che sono **rinvii veri** della fonte. `completezza()` e' tenuta separata da
`verifica()` per questo: una stagione in corso e' incompleta per definizione, non
storta — la stessa distinzione che `scrape_quote.py` fa fra «listone non ancora
pubblicato» e «markup cambiato».

**La riconciliazione dei nomi funziona su tutti i campionati raccolti**, con tre
livelli e una verifica: esonimi **dichiarati**, aggancio esatto, contenimento su
nomi **senza accenti**. La normalizzazione degli accenti e' una regola generale
(`Alavés` = `Alaves`); gli esonimi sono informazione esterna e stanno scritti in
`calendario.NOMI_FONTE`, dove si vedono. **Non c'e' un tetto al loro numero**: in
Bundesliga ne servono **undici**, perche' Wikipedia italiana traduce quasi ogni
citta' tedesca (`Amburgo`, `Magonza`, `Stoccarda`), ed e' una proprieta'
dell'accoppiata di fonti, non una regola mancante. Cio' che un test **vieta** e'
un esonimo che accento e contenimento risolverebbero da soli: quello si', sarebbe
il sintomo di una regola rotta.

> **Un difetto della prima stesura, che il blocco ha corretto**: la mappa
> confrontava le squadre **viste nelle righe**, e su una pagina parziale sono
> meno di venti — Premier e Liga fallivano con "numero diverso di squadre" su una
> fonte che invece le ha tutte. Si usa l'elenco dei **partecipanti**, che c'e'
> anche quando il calendario e' scritto a meta'.

Il calendario, raccolto su tutti e cinque (2026-2027):

| campionato | giocate | da giocare | totale | con giornata |
|---|---:|---:|---:|---:|
| Serie A | 20 | 360 | **380** | **360** |
| Premier League | 21 | 360 | 381 (vedi difetto 3) | 287 |
| Liga | 30 | 350 | **380** | 11 |
| Bundesliga | 9 | 297 | **306** | 24 |
| Ligue 1 | 18 | 288 | **306** | 251 |

I totali tornano al calendario vero di ogni campionato — 380 a venti squadre,
306 a diciotto — e i denominatori si **contano**, mai si assumono. La giornata
arriva dove Wikipedia ha scritto; le mancanti non si inventano e
`fonte_giornata` dice `assente`.

> **La guardia sui doppioni e' stata resa selettiva, e la prima versione costava
> cara.** Una coppia `(casa, trasferta)` dovrebbe essere unica in una stagione,
> ma la Ligue 1 elenca le partite **rinviate** sia alla giornata originale sia a
> quella di recupero. La prima stesura, trovando un solo doppione, saltava
> **l'intero aggancio**: 0 giornate su 288. Ora si tolgono le **sole** coppie
> ambigue — tutte le loro copie, perche' non c'e' modo di sapere quale sia la
> buona — e se ne conta il numero (6). Una guardia troppo grossolana costa
> quanto una assente.

> **Trappola per le sessioni future.** La divisione in «Girone di andata / di
> ritorno» e' una convenzione della **pagina italiana della Serie A**: Premier e
> Bundesliga non ce l'hanno affatto. La prima stesura chiedeva quelle sezioni per
> indice e falliva su tre campionati su cinque; ora si legge la pagina **intera**
> con una sola richiesta, il che risolve anche il **429** che la fonte restituisce
> se la si interroga troppo in fretta.

#### Quattro difetti trovati eseguendo, tutti gia' attivi

1. **Il confronto degli URL non trovava niente su 30 partite che erano tutte gia'
   su disco.** Il sito serve la localizzazione italiana (`it.whoscored.com`) e il
   mio criterio sottraeva la stringa `www.whoscored.com`. Si confronta il
   **percorso**, non una sottostringa dell'URL. E' la **sesta** volta che in
   questo repository un criterio scritto su una FORMA invece che su una
   PROPRIETA' da' un falso esito.
2. **`--solo-calendario` produceva zero partite**, e non era la navigazione: quel
   ramo salta `load_match_urls`, che e' l'unico posto in cui qualcuno apriva la
   pagina — lo scraper leggeva `about:blank` senza accorgersene. L'apertura sta
   ora in `_apri_calendario`, **una sola** per i due chiamanti.
3. **`'live'` sta dentro `'liverpool'`, e sporcava `matches.json`.** Il criterio
   storico cercava la **sottostringa nuda** `'live'` nell'href
   (`scrape_season.py`, e ancora `main.py:356`). Su
   `/matches/1983580/show/...-ipswich-liverpool` fa match dentro il nome della
   squadra, quindi **ogni partita del Liverpool passava come giocata anche se non
   lo era**: `Ipswich-Liverpool` e' finita in `matches.json` con punteggio
   `-:-`, e lo scraper prova a scaricarne gli eventi a ogni giro. Il criterio
   accertato (`'/live/'`, con le barre) non ci cade. **Le righe gia' scritte
   restano**: la cache si rinfresca sommando, non sostituendo, quindi la Premier
   2026-2027 conta 21 partite giocate contro 20 CSV, e `coerenza_fonti()` lo
   dichiara invece di lasciarlo passare. E' il difetto **piu' vecchio** che il
   blocco abbia trovato, e non lo si sarebbe visto senza una seconda lista con
   cui incrociare.
4. **L'aggiornamento del martedi' riportava da settimane un errore inesistente**:
   `object of type 'int' has no len()` su tutti e cinque i campionati, attribuito
   ai **derivati**, che erano riusciti. La riga colpevole era il riepilogo del
   manifest (`len()` su `nuovi`, che e' un contatore intero). I due passi hanno
   ora due `try` separati: con uno solo, un guasto **vero** dei derivati era
   indistinguibile da quello cosmetico.

#### Due test-fotografia della Fase 14, riscritti come proprieta'

Sono diventati rossi **da soli**, senza che nessuno li toccasse: a romperli e'
stata la prima esecuzione dell'attivita' pianificata, che ha dato dei dati alla
2026-2027.

1. `test_stato_su_una_stagione_mai_scaricata_non_solleva` asseriva `csv == 0` e
   `in_calendario is None` — vero solo finche' quella stagione non esisteva su
   disco. Ora verifica la **coerenza col disco**, che e' la proprieta' che il
   test voleva davvero.
2. `test_la_pagina_contiene_i_numeri_della_previsione` confrontava la pagina con
   `P.previsione(...)` chiamata **senza `contesto`**: sotto il burn-in la pagina
   usa il **prior** e il test il within-season, quindi 14,56 contro 12,85. Ora
   riusa `run_previsioni.blocco()`, cioe' la stessa funzione della pagina, e
   verifica anche il **regime**. Rifare qui la costruzione del contesto sarebbe
   stata una seconda copia della stessa regola.

E' la stessa lezione delle guardie di forma, applicata al **tempo** invece che
alla sintassi: un test che descrive uno stato transitorio invece di una
proprieta' invecchia da solo.

**Tre domande aperte**: (1) il calendario degli altri quattro campionati e'
raccolto da WhoScored ma **la giornata manca dove Wikipedia e' parziale**, e non
va inventata; (2) i **rinvii** della Ligue 1 sono una proprieta' della fonte che
la guardia coglie ma che nessuno ha ancora deciso come trattare; (3) `data_fonte`
di Wikipedia e' `None` dove la pagina usa un `rowspan`, e **non viene ereditata**
dalla riga precedente: sarebbe una ricostruzione non verificabile, e la data vera
ce l'ha gia' l'altra fonte.

### Fase 15 / Blocco T1 - il totale di partita ✅ (chiude due domande aperte)

`reports/fase15_totale.md` + otto CSV, da `scripts/run_fase15_totale.py`;
modulo `sot/totale.py`, test `tests/test_fase15_totale.py` (27). **Nessuna
richiesta di rete e nessuna scrittura sotto `data/`**: il modulo legge il
walk-forward gia' prodotto da V1 e lo **ruota** da squadra-partita a partita.
**Nessun numero pubblicato e' cambiato**, verificato rieseguendo:
`run_phase1.py` ridà 4.034 / 4.432 / 3.637 / 5.105 su 562.672 eventi,
`run_phase5.py` ridà Como 4.34 e 5.03 / 191 / [151, 240],
`run_fase12_v4.py` ridà 12,85 · 6,55 · 21,42, `run_fase13_gol.py` ridà
t = 5,40 sulla Serie A. Suite a **1.046 test**.

Aperto dalla richiesta dell'utente del **2026-08-31**: la stima della **somma
delle due squadre** per una partita. Chiude la domanda aperta **n. 3 di V1** e
**n. 3 di V4**, che erano la stessa domanda scritta due volte.

**La risposta e' che la congiunta NON serve**, ed e' il contenuto del blocco:

```
lambda_tot = lambda_casa + lambda_trasferta      esatto, qualunque dipendenza
y_tot      ~ NB2(lambda_tot, r_tot)              r_tot STIMATA sui totali
```

`E[X+Y] = E[X] + E[Y]` non richiede ipotesi. Cio' che la dipendenza rompe e' la
**dispersione**, e `r_tot` stimata sui totali osservati la assorbe per misura
invece che per assunzione.

| | esito |
|---|---|
| il perimetro | **1.638 partite**, lo stesso numero che R0 conto' sui gol |
| `r_tot` si eredita da `r` per lato? | **no**: 83,97 contro 20,00, IC95 del rapporto [3,46, 5,66] |
| la NB2 diretta batte l'indipendenza? | **si sulle code**, fino a 3,4 punti percentuali |
| il modello batte i baseline? | **si**: +0,548 di MAE, **t = 8,33** |
| il totale e' calibrato? | **NO**: pendenza 0,633 contro 1,008 per lato |
| la correzione si adotta? | **si sui tiri, no sui tiri in porta** |

- **Il perimetro riproduce R0 a ogni cifra**, ed e' il controllo interno piu'
  forte disponibile: 1.739 partite con previsione, **1.638 validabili**, e le **2
  partite con un lato solo stanno entrambe nel 2021-2022**, esattamente dove R0
  le aveva trovate sui gol. `eligible` e' una proprieta' della **squadra**, e
  cade dove WhoScored ha perso partite.
- **La rotazione e' quella di `perimetro.partite()`**, ripetuta nei suoi due
  controlli (due lati per partita, esattamente un lato di casa) e nella sua
  **verifica gratuita via `lam_subiti`**. Un test guasta una riga sola e pretende
  che la verifica lo veda: senza, "la verifica passa" e "la verifica non
  controlla niente" sarebbero indistinguibili.
- **La dipendenza e' negativa in tutte e cinque le stagioni** (-0,285 a -0,397).
  Sul perimetro validabile la sd del totale vale **5,85** contro i **7,29** che
  due lati indipendenti darebbero: **20% in meno**.
- **`r_tot` non si eredita, ed e' falsificato** con la stessa forma che
  `precisione.rapporto_dispersioni()` uso' per rifiutare l'ereditarieta' fra
  `r_shots` e `r_sot`: rapporto **4,20**, IC95 [3,46, 5,66], che non contiene 1 e
  sta tutto sopra.
- **L'alternativa scartata resta nel modulo.** `confronto_indipendenza()`
  calcola la convoluzione delle due NB2 per lato: l'indipendenza **ingrassa
  entrambe le code** (-0,033 sotto la linea piu' bassa, +0,035 sopra la piu'
  alta) contro -0,004 e +0,021 della diretta. **Due avvertenze**: sulla linea
  centrale l'indipendenza e' leggermente piu' vicina, e **il Brier non distingue
  le due** — si guadagna calibrazione della coda, non capacita' di ordinare.

**I quattro baseline diventano DUE sul totale, ed e' aritmetica.** Dopo la
rotazione `media squadra + campo` e' **identica** a `media squadra` (a 7e-15) e
`media casa/trasferta` a `media campionato`: il termine di campo aggiunge alla
squadra di casa quello che toglie alla trasferta, quindi **si cancella nella
somma**. Per lato le colonne differiscono fino a 1,83 tiri. Il vincolo 6 e'
rispettato, ma con **due** concorrenti distinti e non quattro, e un test fissa il
fatto perche' non sparisca.

**Il risultato che non era previsto: il totale e' SOTTO-CALIBRATO.** Per lato il
modello sta a **1,008** (z = +0,33, cioe' il numero di V1 riprodotto); sul totale
la pendenza crolla a **0,633** (z = -4,82) sui tiri e a **0,480** (z = -4,87) sui
tiri in porta. **Le due cose non si contraddicono, e il meccanismo e' misurato**:
il modello crede i due lati molto piu' anti-correlati di quanto siano — da -0,40
a -0,75 contro un osservato da -0,29 a -0,40, e sui tiri in porta il divario e'
anche piu' largo (nel 2023-2024 il modello crede -0,398 dove l'osservato e'
**+0,007**, cioe' nessuna dipendenza affatto). Sommando, la parte di segnale che
i due lati hanno in comune si **cancella**, e sopravvive proporzionalmente piu'
rumore.

**Il verdetto sulla correzione e' DIVISO, e non e' stato aggiustato per farlo
tornare uguale.** `CRITERIO_ADOZIONE` e' scritto prima di misurare e `verdetto()`
lo applica meccanicamente, come in R2-bis:

| | tiri | tiri in porta |
|---|---|---|
| pendenza dopo la correzione | 0,812 (z = **-1,91**) | 0,644 (z = -2,44) |
| (1) entro 2 errori standard | si | **no** |
| (2) il MAE non peggiora | si | si |
| (3) segno concorde | si (4/4) | si (4/4) |
| **adottata** | **SI** | **NO** |

Sui tiri passa ma **appena**: z = -1,91 contro una soglia di 2, e va letto cosi'.
La ricalibrazione e' **walk-forward** e la stagione piu' vecchia **resta non
ricalibrata**, marcata invece che riempita — lo stesso trattamento della
2021-2022 in R2-bis.

**Le tre firme TRASFERISCONO su tutti e cinque i campionati**, un fit per
campionato e mai poolati — la domanda che la Fase 13 pose ai gol, applicata qui.
In tutte e dieci le righe `(campionato, bersaglio)`: la correlazione fra i lati e'
**negativa** (da -0,11 a -0,41), **`r_tot` sta fra 2,3 e 5,8 volte `r` per lato**,
e la pendenza del totale sta **sotto 1** (z da -2,37 a -7,01). Non e'
un'idiosincrasia italiana.

> **Conseguenza operativa**: `r_tot` va presa **da quel campionato**, mai da un
> altro. Fra Bundesliga e Liga sui tiri in porta vale 190,6 contro 70,5, cioe' un
> fattore 2,7: un `r_tot` preso in prestito sbaglierebbe le code grossolanamente.

> **Trappola per le sessioni future.** La sotto-calibrazione del totale **non va
> "sistemata" ritoccando lo shrinkage** finche' la pendenza torna a 1,0: sarebbe
> la settima volta che il progetto rifiuta quella strada, e per giunta il modello
> per lato e' **gia' calibrato** — toccarlo romperebbe V1 per aggiustare T1. E la
> ricalibrazione **non e' una spiegazione**: corregge il sintomo e non sa da dove
> venga, che e' la lezione di R2-bis parola per parola.

**Quattro domande aperte**: (1) **perche' il modello anti-correli i due lati piu'
del vero** e' misurato ma non spiegato — il sospetto e' che attacco e difesa
della stessa partita condividano coefficienti stimati sulle stesse righe, quindi
l'errore di stima entri con segno opposto nei due lati, ma separarlo vuole un
disegno apposito; (2) la correzione e' **una trasformazione monotona sul
lambda** e non sa da dove venga l'errore; (3) `r_tot` e' assunta costante fra
squadre e stagioni, come `r` in V1; (4) senza prezzi di mercato reali nessuna
valutazione di scommessa e' possibile (vincolo 3).

### Fase 15 / Blocco P1 - la pagina a giornata, e il totale in scheda ✅

`reports/previsioni.html`, da `scripts/run_previsioni.py` +
`scripts/pagina_previsioni.py` (riscritto); il ponte sta in `sot/previsione.py`
e il turno in `sot/calendario.py`; test `tests/test_fase15_pagina.py` (28); suite a **1.119 test**, tutti verdi.
**Nessuna richiesta di rete e nessuna scrittura sotto `data/`.** **Nessun numero
pubblicato e' cambiato**, verificato rieseguendo: `run_phase1.py` ridà
4.034 / 4.432 / 3.637 / 5.105, `run_phase5.py` ridà Como 4.34 e
5.03 / 191 / [151, 240], `run_fase12_v4.py` ridà 12,85 · 6,55 · 21,42,
`run_fase13_gol.py` ridà t = 5,40 sulla Serie A. **Chiude la Fase 15.**

E' cio' che l'utente aveva chiesto il 2026-08-31: si sceglie una **partita vera**
dal calendario della stagione in corso e si legge la **stima della somma delle
due squadre**. Le tre cose che mancavano — il totale (T1), il calendario (C1) e
la giornata (C1, seconda fonte) — sono arrivate nei due blocchi precedenti; qui
si mettono insieme.

`[DECISO 2026-09-03]` dall'utente: **raggruppamento per giornata**. La decisione
6 del piano (blocchi di date) era vincolata da un limite che Wikipedia ha tolto,
e **resta come ripiego** dove la giornata non c'e'.

| | esito |
|---|---|
| Serie A | **36 turni da 10 partite**, tutti con la giornata della fonte |
| Premier | 39 turni: 33 giornate vere, 3 dedotte, 3 blocchi di date |
| Liga · Bundesliga | quasi tutti **blocchi di date**: li' Wikipedia e' parziale |
| Ligue 1 | 51 turni, e i 19 blocchi sono i **rinvii** gia' dichiarati da C1 |
| partite senza numeri | **zero** su tutti e cinque |

**Il turno si costruisce in tre passi dichiarati, e il secondo e' quello che
rende leggibile il risultato** (`calendario.con_turno`):

1. **la giornata della fonte**, dove c'e';
2. **il contenimento nella finestra di date di una giornata, se e solo se e'
   unico** — la stessa disciplina di `mappa_squadre`. Serve perche' Wikipedia
   copre una giornata *in parte*: in Premier League ne arrivano 8 righe su 10, e
   senza questo passo le altre due finivano in un turno separato lo stesso
   weekend. Sono **70 turni contro 39**;
3. **i blocchi di date** per cio' che resta.

- **La deduzione non diventa MAI la giornata della riga.** `fonte_giornata`
  resta `assente` e cambia solo il turno in cui la riga e' mostrata. Scrivere
  quel numero nella colonna della giornata sarebbe inventarla, ed e' il difetto
  che C1 aveva rifiutato di commettere. Un test lo blocca.
- **La capienza `squadre/2` e' strutturale, non una soglia.** Senza, la Ligue 1
  usciva con una «5a giornata» da **12 partite su 18 squadre**: i rinvii hanno
  una data che cade nella finestra di un altro turno e il contenimento li tirava
  dentro. E dove i candidati sono troppi **si rifiutano tutti**, non i primi che
  ci stanno: quale sia la partita di troppo non e' sapibile. Lo stesso vincolo
  chiude i blocchi di date, che altrimenti si concatenavano — la Liga usciva con
  **un blocco solo da 29 partite** su dieci giorni, cioe' tre giornate insieme.
- **La data della fonte e' testo italiano** (`venerdi, set 04 2026`), e la forma
  e' **accertata su tutte le righe di tutti e cinque i calendari**: zero non
  conformi. Nove mesi su dodici sono osservati; i tre che mancano (`giu lug
  ago`) sono completamento della serie e stanno in `MESI_OSSERVATI` per non
  perdere la distinzione. `data()` **ritorna `None` invece di sollevare**: una
  cella storta e' un limite di quella riga, non la fine del calendario di un
  campionato.
- **I nomi dei giorni e dei mesi si costruiscono a mano**, non con `strftime`:
  quelli di `strftime` dipendono dal `locale` della macchina, e la stessa pagina
  uscirebbe in inglese su un PC configurato diversamente.

**Il totale e' la somma esatta, e la pagina non mostra altro** (`p1` =
`previsione.tabella_calendario`). `E[X+Y] = E[X] + E[Y]` non richiede nessuna
ipotesi sulla dipendenza; cio' che la dipendenza rompe e' la dispersione, ed e'
il motivo per cui `r_tot` si **stima sui totali osservati di quel campionato**.
Un test pretende `lam_totale == lam_casa + lam_trasferta` su tutte le righe e su
tutti i campionati, in tabella **e** nel blob della pagina.

> **La ricalibrazione di T1 NON si applica in pagina**
> (`previsione.RICALIBRAZIONE_IN_PAGINA = False`), ed e' una decisione
> dichiarata col suo perche' invece di un'omissione. T1 l'aveva adottata col
> criterio scritto in anticipo, ma l'adozione e' **per (campionato, bersaglio)**
> e vale in **3 celle su 10**: applicarla dove passa e non dove non passa
> renderebbe i cinque campionati non confrontabili fra loro — che e' cio' che la
> regola di E1 vieta, e la pagina li mostra uno accanto all'altro. In piu' la
> correzione e' validata **dentro** il walk-forward delle cinque stagioni
> storiche, e portarla sulla 2026-2027 e' un passo che nessuno ha misurato.
> **Quello che si fa invece e' il vincolo 5**: la pendenza di quel campionato
> sta nella stessa riga della probabilita' — 0,63 in Serie A, 0,65 in Premier,
> 0,87 in Liga — con scritto che le `P(Over)` sono piu' affidabili al centro che
> sulle code.

**Il turno zero funziona, ed e' la decisione dell'utente messa in codice.** In
Bundesliga **quattro squadre su diciotto non hanno ancora giocato**: il modello
within-season non le conosce affatto, e senza la strada del prior sarebbero
sparite **122 partite su 297**. Le squadre vengono dal **calendario**, i numeri
dal **prior**, e la squadra si **conta** (`squadre_non_viste`) invece di essere
trattata come media in silenzio. Se nemmeno il prior c'e', la partita esce e
finisce in `attrs["scartate"]` — una riga senza numeri e' meglio di una riga con
un numero inventato. **Le due guardie di V4 non sono state allentate**:
`verifica_squadre` e `TeamModel(strict_teams=True)` restano dove sono, e P1
aggiunge un regime, non toglie una guardia.

- **Il calendario non e' una dipendenza**: se la stagione mostrata non e' quella
  chiesta, il calendario **non si attacca** e la pagina ripiega sulla sola
  modalita' a coppia libera, dichiarandolo. Partite di un'annata accostate ai
  numeri di un'altra sarebbero una divergenza silenziosa fra la riga e il suo
  contenuto.
- **La modalita' a coppia libera resta**, come secondo pannello: toglierla
  avrebbe fatto sparire una risposta che il repository sa gia' dare e che il
  calendario non copre (una coppia che non si gioca).
- **Il generatore continua a non calcolare niente**: serializza una tabella
  gia' prodotta da `previsione`, e un test lo pretende. Le tabelle per lato del
  dettaglio si **cercano** fra le coppie gia' in pagina invece di essere
  serializzate una seconda volta; dove non ci sono — perche' una squadra non ha
  ancora giocato — la pagina lo **scrive** invece di mostrare un vuoto.

**Due guardie corrette, e sono la settima e l'ottava volta.**

1. **`test_il_generatore_della_pagina_non_calcola_niente` cercava sottostringhe
   nel sorgente intero**, e ha dichiarato colpevole la docstring che dice «questo
   modulo non calcola: un test vieta `TeamModel` nel sorgente». Ora usa il
   `_codice()` tokenizzato di V0 — riusato, non riscritto — con un meta-test
   bidirezionale.
2. **`_codice()` stesso non toglieva le f-string.** Da Python 3.12 un'f-string
   non e' piu' un unico token `STRING`: viene spezzata in `FSTRING_START` /
   `FSTRING_MIDDLE` / `FSTRING_END`, e il testo letterale sopravviveva alla
   setacciatura — il nome di colonna `f"p_over_{ln}"` faceva scattare il divieto
   di `p_over` su un modulo che quel conto non lo fa affatto. Corretto
   **nell'helper condiviso**, che e' il posto dove vale per tutti.

> **Trappola per le sessioni future.** La sotto-calibrazione del totale e'
> **dichiarata e non corretta**, e non va «sistemata» applicando la
> ricalibrazione in pagina finche' la pendenza torna a 1,0: sarebbe l'ottava
> volta che il progetto rifiuta quella strada, e per giunta il modello **per
> lato e' gia' calibrato** (1,008) — toccarlo romperebbe V1 per aggiustare la
> pagina. E il **blocco di date non e' una giornata**: la pagina lo scrive sotto
> la griglia, e quella riga non va tolta perche' «tanto si capisce».

**Quattro domande aperte**: (1) sui campionati dove Wikipedia e' parziale il
turno resta in gran parte un blocco di date, e l'unico rimedio e' una fonte
migliore della giornata — non una regola piu' aggressiva; (2) i **rinvii** della
Ligue 1 restano dichiarati e non trattati, ed e' la domanda aperta n. 2 di C1;
(3) la pagina mostra il totale **atteso** e le sue `P(Over)`, ma non e' mai stata
misurata la calibrazione del totale **fuori dalle cinque stagioni storiche**;
(4) senza prezzi di mercato reali «il modello e' meglio del mercato» resta una
frase che questo progetto non puo' pronunciare (vincolo 3).

### Fase 16 / Blocco O1 - la verifica prospettica ✅ (previsione prima, esito dopo)

`reports/fase16_o1_verifica_prospettica.md` + 12 CSV, da
`scripts/run_fase16_o1.py`; modulo `sot/verifica_prospettica.py`, metrica nuova
`validate.crps_conteggi`, test `tests/test_fase16_o1.py` (34) + 6 in
`tests/test_validate.py`. **Nessuna richiesta di rete. Nessun modello predittivo
nuovo. Nessuna scrittura sotto `data/`.**

Chiesta dall'utente il **2026-09-03**. Tutto cio' che il repository aveva
validato era **within-season** o **retrospettivo** — il walk-forward di V1, il
prior di A2 su venti transizioni concluse, la trasferibilita' di F13. Il
deliverable operativo della Fase 14 non aveva **nessuna** misura di quanto
sbagliasse.

**Non c'e' stato bisogno di simulare l'esclusione: era gia' avvenuta.**

| | |
|---|---|
| previsioni congelate | `reports/previsioni_*.csv`, **2026-08-30 13:47 UTC** |
| primo CSV di evento 2026-2027 | **2026-09-03 12:33 UTC** |
| anticipo minimo sui cinque | **3,95 giorni** |

#### L'anteriorita' non poggia su un orologio, ed e' il punto metodologico

Il `mtime` e' un argomento **debole**: un timestamp si cambia. Quello che regge
il blocco e' il secondo controllo, che non chiede di fidarsi di niente:

> **Le previsioni congelate si riproducono da `PS.lam_dal_prior` applicato al
> fit della sola stagione precedente.** Sono percio' una funzione di dati che
> finiscono a maggio 2026, e **non possono contenere informazione sulle
> giornate 1-2 qualunque sia la data in cui il file e' stato scritto.**

E sono **`modello prec`**, cioe' esattamente il candidato che
`PS.REGOLA_DUE_REGIMI` prescrive sotto `config.BURN_IN_ROUND`: si misura la
regola dichiarata, non una variante costruita per l'occasione.

**La riproduzione non e' bit-per-bit, e la ragione e' misurata invece che
aggirata**: dentro un solo processo il re-fit da' scarto **0,0 esatto**; fra due
processi resta ~1e-7 relativo, che e' l'ordine che L-BFGS-B con `ftol = 1e-12`
dichiara (`sqrt(ftol)` sui parametri; l'ordine delle somme in BLAS multithread
sposta il punto di arresto dentro quella tolleranza). `TOLL_RIPRODUZIONE` e'
**derivata da li'**, non scelta guardando lo scarto osservato — che sarebbe far
tornare un numero — e un test la lega alla `ftol` scritta in `model_team.py`.

#### La metrica: CRPS su conteggi, dichiarata prima

`crps_conteggi(y, lam, r) = somma_k (F(k) - 1[y <= k])^2`, in **unita' di tiri**.
E' propria, e' **ordinale** (sbagliare di 8 costa piu' che sbagliare di 1, cosa
che la log score non distingue), ed e' robusta alle code — con 170 righe una sola
osservazione estrema deciderebbe il verdetto. **E' la stessa scelta che R2 ha
fatto preferendo l'RPS alla log-loss sull'1X2**, su un bersaglio con piu' classi:
non una metrica nuova nel progetto, la stessa rifatta dove mancava.

Accanto, mai al posto: log score (l'unita' di A2, per essere confrontabili con
`fase14_prior.md`), Brier sulle linee dichiarate, MAE, bias, PIT e copertura.
**Due metriche del repository NON si usano, e il perche' e' scritto**: la
scomposizione di Murphy vuole otto fasce e a questo `n` il termine di binning
non e' trascurabile; la pendenza di calibrazione ha un errore standard che la
rende non interpretabile, lo stesso `nan` dichiarato di `media campionato` in
Fase 4.

`r` e' quella **PUBBLICATA**, mai ristimata: valutare con una dispersione
migliore misurerebbe un modello che nessuno ha mai pubblicato. Un test lega il
divieto alle **funzioni** che valutano e non al file, perche' il diagnostico
`dispersione_di_avvio` deve stimarla.

#### Il perimetro, e la giornata come grandezza da ACCERTARE

`team_match_idx <= 2` — le prime due partite di ogni squadra. **170 righe / 85
partite**: ITA 40 · ENG 40 · ESP 40 · FRA 36 · GER 14 (li' 7 partite su 9
giocate hanno gli eventi su disco).

«Giornata» e «prime due partite di squadra» sono **due grandezze diverse**
(vincolo 7), e la giornata vera e' accertabile solo dove la seconda fonte e'
sana. **La Serie A e' il controllo positivo** (Wikipedia 380/380): li' l'accordo
e' **20 su 20**. Su tutti i campionati insieme, dove entrambe le fonti parlano
senza ambiguita', sono **67 confronti e zero discordi**.

> **Tre esiti restano separati, e confonderli inventa un disaccordo.** Una
> partita **assente** dalla seconda fonte dice solo che la pagina e' parziale;
> una **ambigua** e' un rinvio che la fonte elenca a due giornate diverse, e si
> tolgono **tutte** le copie come fa gia' `calendario.py`; solo una elencata
> **senza ambiguita'** sopra la soglia e' un disaccordo. **La prima stesura ha
> sbagliato proprio qui**: costruiva `coppia -> giornata` con l'ultima scrittura
> che vinceva e su `Paris FC-Nizza` (elencata **alla 2 e alla 7**) teneva la 7,
> attribuendo al ripiego un errore che era suo.

`ripiego_ammesso` **non ha una soglia sull'accordo medio** — si sceglierebbe
dopo aver visto gli scarti — ma una condizione sulla fonte: accordo **totale
dove la seconda fonte si dichiara completa**. Un test pretende che sappia dire
anche di no.

#### Le neopromosse: al giorno 1 una riga su quattro non ha previsione documentale

Il file congelato contiene **solo le squadre della stagione precedente**, quindi
una riga che coinvolga una neopromossa non ha un numero scritto prima:
**126 righe su 170 (74,1%) sono documentali**, le altre 44 no. La previsione
esiste lo stesso — `lam_dal_prior` da' coefficiente 0 a una squadra sconosciuta
— ma **e' un DEFAULT, non una stima**: la media di campionato dell'anno scorso.
Tutte le tabelle escono in due versioni, perimetro pieno e sole congelate, e la
conclusione non cambia fra le due.

#### L'esito: le due meta' vanno tenute insieme

**Le previsioni congelate hanno il CRPS migliore di ogni baseline reale su
entrambi i bersagli.** Solo l'`oracolo di livello` — che usa la media vera delle
giornate 1-2, cioe' un numero che il 30 agosto non esisteva — fa meglio.

| bersaglio | `modello prec` | `media squadra prec` | `media campionato prec` | `con prior` | oracolo |
|---|---:|---:|---:|---:|---:|
| tiri | **2,8260** | 2,9765 | 3,1889 | 3,0390 | 2,7245 |
| tiri in porta | **1,1991** | 1,2735 | 1,3851 | 1,2926 | 1,1813 |

**Ma quasi nessun confronto raggiunge il proprio MDE**, ed era dichiarato prima:

| bersaglio | contro | delta CRPS | t (cluster) | delta/MDE | conclude |
|---|---|---:|---:|---:|---|
| tiri | `media squadra prec` | -0,1505 | -1,63 | 0,58 | **no** |
| tiri | `media campionato prec` | -0,3628 | -3,13 | **1,12** | **si** |
| tiri in porta | `media squadra prec` | -0,0744 | -2,53 | 0,90 | **no** |
| tiri in porta | `senza prior` | -0,2707 | -3,96 | **1,41** | **si** |
| tiri in porta | `media campionato prec` | -0,1860 | -4,57 | **1,63** | **si** |

> Con 85 partite il test **esclude divari grandi, non divari piccoli**. Il
> `t = -2,53` sui tiri in porta passa la soglia a due code del 5% e persino
> quella di Sidak, ma **non** il criterio dichiarato `delta/MDE >= 1`, che chiede
> `|t| >= 2,80`: significativo non e' la stessa cosa di «il test aveva la potenza
> per vederlo», e il criterio scritto prima non e' stato riscritto per farlo
> tornare.

**A2 e' confermata prospetticamente**: `con prior` — la miscela fra prior e
partite nuove — **perde** contro `modello prec` su entrambi i bersagli
(-0,213 e -0,093). E' la stessa conclusione che A2 aveva tratto su venti
transizioni passate, ora su dati che A2 non aveva.

#### La taratura storica: senza, un CRPS e' un numero e non un risultato

La **stessa identica procedura** sulle prime due partite di ogni squadra nelle
20 transizioni gia' concluse (4 per campionato), aggregando **allo stesso modo
sui due lati** — pesata per righe, per stagione. E' il gemello di
`tentativi.taratura_test()` e del nullo simulato di V0.

| bersaglio | grandezza | 2026-27 | intervallo storico | dentro |
|---|---|---:|---|---|
| tiri | CRPS assoluto | **2,826** | [2,618 · 2,660] | **no, peggiore di tutte** |
| tiri | delta sul baseline | -0,150 | [-0,212 · -0,073] | si (rango 2 su 5) |
| tiri | scarto di livello | **+8,2%** | [-3,8% · +6,1%] | **no** |
| tiri in porta | CRPS assoluto | 1,199 | [1,117 · 1,368] | si (rango 2 su 5) |
| tiri in porta | delta sul baseline | **-0,074** | [-0,049 · -0,014] | **no, il migliore di tutte** |
| tiri in porta | scarto di livello | **+3,6%** | [-9,7% · +3,1%] | **no** |

> **E' la taratura a rendere leggibile il risultato, e senza si sarebbe letto al
> contrario.** Sui tiri il CRPS assoluto e' il peggiore dei cinque avvii, ma il
> **vantaggio sul baseline e' ordinario**: non e' il modello a essersi
> degradato, e' l'avvio 2026-27 a essere piu' difficile. La causa e' misurata e
> sta nella stessa riga: **il livello e' fuori dall'intervallo storico su
> entrambi i bersagli**, e la scomposizione dice che vale il **3,6%** del CRPS
> sui tiri. Il resto e' rumore di partita, che nessun modello puo' prendere.

Si riporta il **rango**, non un p-value: venti transizioni danno una scala di
riferimento, non un campione da cui estrarre una probabilita'.

#### La dispersione di avvio - DIAGNOSTICO, non adozione

**L'attesa era dichiarata prima**: `r` viene dal walk-forward **within-season**,
dove i lambda sono piu' accurati di quelli cross-stagione di `modello prec`,
quindi la predittiva pubblicata dovrebbe essere **troppo stretta** all'avvio.

Misurata sulle transizioni storiche: `r_avvio` **16,3 contro 20,2** pubblicata
sui tiri (rapporto 0,805, IC95 **[0,649 · 1,078]**) e **22,5 contro 31,0** sui
tiri in porta (0,727, IC95 [0,448 · 2,038]). **Il segno e' quello atteso ma
l'IC95 contiene 1 su entrambi**: l'attesa non e' confermata ne' esclusa. IC da
bootstrap **sui cluster**, la stessa forma con cui
`precisione.rapporto_dispersioni()` ha falsificato l'ereditarieta' fra
`r_shots` e `r_sot`. **Questo blocco non ricalibra niente.**

#### Il totale di partita - secondario, e non conclude

`lam_tot = lam_casa + lam_trasferta` e' esatto (T1), `r_tot` **non si eredita** e
viene da quella gia' stimata sulle stagioni storiche di ogni campionato. CRPS
3,687 sui tiri e 1,748 sui tiri in porta, bias -2,49 e -0,61. T1 aveva gia'
misurato la sotto-calibrazione del totale su 1.638 partite; qui i cluster sono
85 e ci si aspettava di non concludere. **Non si adotta niente.**

#### Il registro e' l'unico artefatto non rigenerabile del progetto

`run_previsioni.py --csv` riscrive `reports/previsioni_<L>.csv` **sovrascrivendo
e senza data nel nome**, e l'attivita' pianificata del martedi' e' attiva: una
sola esecuzione avrebbe cancellato l'evidenza. Le copie
`reports/fase16_o1_congelate_*.csv` conservano il `mtime` (`shutil.copy2`) e
stanno in **git** come eccezione dichiarata in `.gitignore`, con la stessa
motivazione gia' scritta per `data/raw/manifest.json`.

> **Il commit non prova la data**: la storia in git comincia dopo i fatti. A
> provare che quei numeri non guardano le giornate 1-2 e' la **riproducibilita'**
> da dati che finiscono a maggio 2026, non il timestamp. E' scritto nel
> `.gitignore` accanto all'eccezione, perche' e' li' che qualcuno lo leggera'.

> **Trappola per le sessioni future.** Il risultato **non va gonfiato**: «le
> previsioni battono tutti i baseline» e' vero e vale poco da solo, perche' su 85
> partite quattro confronti su cinque non raggiungono il proprio MDE. E **non va
> sminuito**: il segno e' coerente su entrambi i bersagli, su tutti i confronti,
> e concorda con la taratura. Le due meta' si citano insieme. In particolare
> **non si riapra `alpha_prior`** perche' `con prior` perde: e' la conferma
> prospettica di A2, non una sorpresa da sistemare.

**Quattro domande aperte**: (1) **85 partite sono poche, e l'unico rimedio e' il
tempo** — il blocco si rifa' identico fra qualche giornata, ma allora il regime
non sara' piu' `modello prec` e si misurera' un'altra cosa; (2) **perche' il
livello 2026-27 sia fuori dall'intervallo storico** e' misurato e non spiegato,
e con due giornate non e' distinguibile da un avvio anomalo; (3) la dispersione
di avvio ha il segno atteso e un IC che contiene 1: serve piu' storia, non piu'
repliche; (4) senza prezzi di mercato reali «il modello e' meglio del mercato»
resta una frase che questo progetto non puo' pronunciare (vincolo 3).


## Convenzioni

- Codice e docstring in **italiano**, come il resto del progetto.
- Coordinate Opta 0-100, tutte le squadre attaccano verso x = 100. Nessun
  ribaltamento necessario.
- Seed unico in `config.SEED`.
- I minuti si calcolano su `expandedMinute`, quindi una partita dura 94-99
  minuti, non 90. E' voluto: evita di gonfiare i tassi per 90.
- Ogni scelta non ovvia va spiegata nella docstring del modulo, con il
  **perche'**, non solo il cosa.
