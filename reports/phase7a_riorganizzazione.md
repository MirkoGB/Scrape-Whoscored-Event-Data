# Fase 7A — Consolidare prima di moltiplicare

> **ESEGUITO** dopo l'approvazione, sul commit `728a782`. Le sezioni 1-7 sono
> la proposta come è stata approvata e restano invariate; l'esito, le cinque
> deviazioni e le verifiche stanno in **§8**, in fondo.

**Proposta. Niente è stato spostato, rinominato o cancellato.** Questo documento
è l'oggetto dell'approvazione richiesta dal punto 1 del blocco; l'esecuzione
avviene solo dopo, e solo sulle voci approvate.

Nessun download è stato fatto, come da specifica del blocco.

**Controllo di partenza**, preso prima di scrivere questa proposta:

```
./.venv/Scripts/python.exe -m pytest tests/ -q   →   184 passed in 9.98s
```

---

## 1. Cosa c'è oggi in radice

Diciotto voci più sei cartelle. Colonna `git`: `T` tracciato dal fork,
`M` tracciato e modificato, `?` non tracciato, `ign` escluso da `.gitignore`.

| voce | byte | git | cos'è davvero |
|---|---:|:---:|---|
| `main.py` | 23.633 | T | scraper WhoScored del fork; `getMatchData`, `createEventsDF` |
| `Scrape matches.py` | 13.400 | ? | wrapper del fork con il fix `playerId`; **lo spazio nel nome impedisce l'import** |
| `scrape_serie_a_2025_2026.py` | 22.177 | ? | lo scraper che ha prodotto i 380 CSV |
| `utils.py` | 2.117 | T | rilevamento della versione di Chrome, usato solo dallo scraper |
| `tiri_in_porta.py` | 10.163 | ? | CLI diagnostica; importa `sot.shots` (unica definizione) |
| `test.py` | 2.658 | M | **non è un test pytest**: vedi §2.3 |
| `EPV_grid.csv` | 11.232 | T | griglia EPV di Laurie Shaw, usata solo da `main.py:517` |
| `linecollection.py` | 11.535 | T | copia di un modulo mplsoccer |
| `visuals.py` | 31.619 | T | visualizzazioni del fork |
| `tutorial.ipynb` | 1.039.368 | T | notebook del fork |
| `logo.jpg` | 12.541 | T | logo del fork |
| `events.csv` | 2.865.809 | ign | **1 partita**, 2026-05-03, BetWright Stadium → Women's Super League |
| `serie_a_2025_2026_events.csv` | 1.008.691.338 | ign | concatenazione dei 380 CSV |
| `Como.png` | 56.516 | ? | output di `tiri_in_porta.py --out` |
| `Como_tiri_in_porta_quote_2025-26.xlsx` | 35.790 | ? | quote, **provenienza non documentata** |
| `CLAUDE.md` `README.md` `LICENSE` `requirements.txt` `.gitignore` | — | T/? | documenti di progetto |
| `data/events.csv` | 13.593.833 | ign | **5 partite di Liga**, ago-set 2022 (Camp Nou, Reale Arena, Sánchez-Pizjuán, Nuevo Mirandilla) |

L'ultima riga è un fatto nuovo: `CLAUDE.md` documenta la trappola di
`events.csv` in radice (Women's Super League) ma **non** quella di
`data/events.csv`, che è un secondo file demo, di un altro campionato e di
un'altra stagione, con lo stesso schema appiattito. Due file omonimi, nessuno
dei due Serie A, entrambi in posizione da essere letti per sbaglio.

**Nota sullo stato del repository, non richiesta ma bloccante per il seguito.**
`sot/`, `scripts/`, `tests/`, `docs/`, `legacy/`, `CLAUDE.md` e i tre script di
scraping usati **non sono tracciati da git**: l'ultimo commit (`1bdabe5`) è
ancora quello del fork. Tutto il lavoro delle Fasi 0-6 esiste solo come file su
disco. Ne segue che (a) `git mv` non conserva storia perché storia non ce n'è,
e (b) **non c'è nessun punto di ripristino** se una riorganizzazione va storta.
Vedi §6.1.

---

## 2. Proposta A — dove va ciascuna cosa

### 2.1 Il criterio

Quattro destinazioni, e il criterio è *a cosa serve il file oggi*, non da dove
viene:

| destinazione | criterio |
|---|---|
| `acquisition/` | codice che **porta dati dentro** il repository, da qualunque fonte |
| `legacy/` | codice del fork che non serve al modello e **non va riusato** |
| cancellato | file **rigenerabili in locale** o demo di altri campionati |
| radice | documenti di progetto e configurazione |

`sot/` non si tocca: è il pacchetto di modellazione e non c'entra con
l'acquisizione. `scripts/` resta il posto dei punti d'ingresso eseguibili.

### 2.2 Spostamenti

```
acquisition/
  __init__.py
  whoscored/
    __init__.py
    main.py             ← main.py
    scrape_matches.py   ← "Scrape matches.py"      (rinominato: niente spazi)
    scrape_season.py    ← scrape_serie_a_2025_2026.py
    utils.py            ← utils.py
```

| da | a | perché |
|---|---|---|
| `main.py` | `acquisition/whoscored/main.py` | è lo scraper della fonte, e la fonte diventerà una fra diverse |
| `Scrape matches.py` | `acquisition/whoscored/scrape_matches.py` | lo spazio nel nome costringe `scrape_serie_a_2025_2026.py:81` a caricarlo per percorso con `importlib`. Rinominare elimina l'aggiramento invece di trasportarlo |
| `scrape_serie_a_2025_2026.py` | `acquisition/whoscored/scrape_season.py` | il nome codifica campionato e stagione in un file che dovrà servirne cinque per cinque (`regole_fantacalcio.md` §7.1: WhoScored serve su tutte e cinque le stagioni). **La parametrizzazione non è di questo blocco**: qui si sposta e si rinomina soltanto |
| `utils.py` | `acquisition/whoscored/utils.py` | dipendenza solo di `main.py`; in radice sembra un'utilità di progetto e non lo è |
| `tiri_in_porta.py` | `scripts/tiri_in_porta.py` | è una CLI che importa `sot.shots`, esattamente come i `run_phase*.py` |
| `Como.png` | `reports/figures/como_tiri_in_porta.png` | è un output rigenerabile con `scripts/tiri_in_porta.py Como --out`; sta con le altre figure o si cancella, non in radice |
| `Como_tiri_in_porta_quote_2025-26.xlsx` | `data/external/quote/como_tiri_in_porta_2025-2026.xlsx` | **non si cancella**: è l'unico file di quote in casa e il blocco 7F deve documentarne la provenienza. `data/external/` è la cartella dei dati forniti a mano, con provenienza da accertare |

```
legacy/fork/
  EPV_grid.csv  linecollection.py  visuals.py  tutorial.ipynb  logo.jpg
  test_fork_manuale.py   ← test.py
```

| da | a | perché |
|---|---|---|
| `EPV_grid.csv` | `legacy/fork/` | letto solo da `main.py:517` (`addEpvToDataFrame`), che nessuna fase usa. Resta perché `main.py` continua a offrire quella funzione |
| `linecollection.py` | `legacy/fork/` | copia di `mplsoccer.linecollection`, nessun import nel repository |
| `visuals.py` | `legacy/fork/` | `sot/figures.py` è ridisegnato da zero e non lo importa |
| `tutorial.ipynb` | `legacy/fork/` | 1 MB di notebook del fork, nessun riferimento |
| `logo.jpg` | `legacy/fork/` | logo del fork |

`legacy/README.md` va esteso: oggi spiega solo il backtest circolare. Serve una
seconda sezione che dica che `legacy/fork/` è **materiale d'origine conservato
per attribuzione**, non codice morto da riesumare — e che il divieto di riuso
del blocco 7F (`legacy/` non si riusa in nessun caso) riguarda il backtest, non
l'attribuzione del fork.

### 2.3 `test.py` — deviazione motivata dal testo del blocco

Il blocco lo elenca come «un `test.py` che non sta in `tests/`». **Proposta:
non spostarlo in `tests/`, ma in `legacy/fork/test_fork_manuale.py`.**

Non è un test automatico e metterlo sotto `tests/` romperebbe la suite:

- importa `from env.main import ...`, e **il modulo `env` non esiste** nel
  repository — errore già in fase di raccolta di pytest;
- apre Chrome con `webdriver.Chrome('drivers/chromedriver.exe')`, percorso
  inesistente;
- richiede rete e scarica da WhoScored;
- asserisce sulla Premier League 2019/2020 (`len(match_urls) == 380`,
  `events_df.shape[1] == 259`), cioè su dati che questo progetto non usa.

È un collaudo manuale dello scraper del fork. Sta con lo scraper del fork.
Il rinomino a `test_fork_manuale.py` serve a impedire che pytest lo raccolga se
un domani `legacy/` finisse dentro il perimetro di raccolta — `test_*.py` è il
pattern di default, `test_fork_manuale.py` lo soddisfa comunque, quindi in
alternativa: `collaudo_fork_manuale.py`. **Preferisco quest'ultimo**, ed è la
forma che eseguirei salvo indicazione contraria.

### 2.4 Cancellazioni — 1,02 GB

Le tre sono tutte già in `.gitignore`, quindi non c'è storia da perdere.

| file | byte | come si rigenera | costo |
|---|---:|---|---|
| `serie_a_2025_2026_events.csv` | 1.008.691.338 | `pd.concat` dei 380 CSV **che restano su disco** | secondi, nessuna rete |
| `data/events.csv` | 13.593.833 | ri-scraping di 5 partite di Liga 2022 | non serve a niente in questo progetto |
| `events.csv` | 2.865.809 | ri-scraping di 1 partita di WSL | idem |

Il primo è la voce che conta: 1 GB che nessun modulo legge — `sot/io_events.py`
lo dichiara esplicitamente al punto 3 della sua docstring — e che è la
concatenazione di dati già presenti in `data/serie_a_2025_2026/` (963 MB).
Tenerlo significa il doppio del disco per zero informazione, e a scala di
trenta stagioni-campionato il pattern è insostenibile.

Gli altri due sono demo di altri campionati che stanno lì solo perché il
progetto li ha ereditati, e sono **trappole documentate**: la loro presenza in
posizione leggibile è il rischio, non la loro dimensione.

**Alternativa, se la cancellazione non convince:** spostarli in
`data/external/demo_fork/` invece di cancellarli. Costa 16 MB e li toglie
comunque dalla portata di un `glob`. Per il file da 1 GB l'alternativa non ha
senso: o si cancella o resta dov'è.

### 2.5 Modifiche di codice richieste dagli spostamenti

Sono quattro, tutte meccaniche, tutte **fuori** da `sot/`. Nessuna tocca il
modello.

| file | riga | oggi | dopo |
|---|---|---|---|
| `scrape_season.py` | 60 | `BASE_DIR = Path(__file__).resolve().parent` | `BASE_DIR = Path(__file__).resolve().parents[2]` — altrimenti scriverebbe in `acquisition/whoscored/data/` |
| `scrape_season.py` | 81 | `path = BASE_DIR / 'Scrape matches.py'` | `from . import scrape_matches`, e via l'intera `_load_scrape_matches_module()` |
| `scrape_season.py` | 63-65 | percorsi `data/serie_a_2025_2026*` scritti a mano | importati da `sot.config` (§3.4) |
| `scripts/tiri_in_porta.py` | 30-33 | `BASE = Path(__file__).parent` | `sys.path.insert(...)` come i `run_phase*.py`, e percorsi da `sot.config` |

`Scrape matches.py:56` (`Path(__file__).parent / "main.py"`) continua a
funzionare senza modifiche perché `main.py` si sposta nella **stessa** cartella.
Il blocco `sys.modules["env.main"]` resta com'è: è brutto, ma è la ragione per
cui `main.py` è importabile, e riscriverlo non è di questo blocco.

**Il README va aggiornato in due punti**: la sezione «Struttura» (righe 606-626)
e l'attribuzione al fork (righe 634-636), che nomina i tre file per il loro
percorso attuale.

---

## 3. Proposta B — `data/` consapevole di campionato e stagione

### 3.1 Il problema

Oggi `data/` contiene una cartella il cui nome è `serie_a_2025_2026`, cioè
campionato e stagione incollati nel nome di una directory, e due file demo di
altri campionati alla pari con essa. Non c'è nessun posto dove mettere la Liga
2022-23 che non sia inventare un secondo nome con la stessa convenzione
implicita.

### 3.2 Formato della stagione — `2025-2026`

Tre candidati, e la scelta non è cosmetica perché la Fase 7 acquisirà da fonti
con convenzioni diverse fra loro:

| forma | pro | contro |
|---|---|---|
| `2025-26` | compatto, è la forma usata nel testo dei report | il secondo anno è a due cifre: ambiguo a cavallo di secolo, e non ordinabile fuori dal 21° secolo |
| `2526` | è la forma di `football-data.co.uk` negli URL | illeggibile, e adottarla significherebbe far entrare la convenzione di **una** fonte nella struttura di tutte |
| **`2025-2026`** | **non ambiguo, ordinabile lessicograficamente, indipendente dalla fonte** | tre caratteri in più |

**Proposta: `2025-2026`.** La forma della fonte (`2526`) resta dov'è legittima,
cioè nel nome del file scaricato dentro `raw/`, che non si tocca mai.

### 3.3 Codice del campionato — `ITA-serie-a`

`football-data.co.uk` chiama la Serie A `I1`, la Premier `E0`. Usare quei codici
come nomi di cartella farebbe entrare la tassonomia di una fonte nella
struttura del repository, e i vincoli 7 e 8 di questa fase vanno nella
direzione opposta: la provenienza si dichiara, non si eredita in silenzio.

Proposta: `ISO-3166 alfa-3` più slug del campionato.

| cartella | football-data | WhoScored |
|---|---|---|
| `ITA-serie-a` | `I1` | regione 108, torneo 5 |
| `ENG-premier-league` | `E0` | |
| `ESP-la-liga` | `SP1` | |
| `GER-bundesliga` | `D1` | |
| `FRA-ligue-1` | `F1` | |

La corrispondenza vive in **un solo dizionario** in `sot/config.py`, ed è lì che
il blocco 7B andrà a leggerla.

### 3.4 L'albero

```
data/
  raw/                          ← grezzo. Non si trasforma, non si sovrascrive.
    manifest.json               ← provenienza di ogni file (vincoli 8 e 9). VERSIONATO.
    whoscored/
      ITA-serie-a/2025-2026/
        events/1901061.csv …    ← i 380 file, invariati
        matches.json            ← ex data/serie_a_2025_2026_matches.json
    football-data/              ← creata dal blocco 7B, vuota oggi
      ITA-serie-a/2025-2026/I1.csv
  processed/                    ← rigenerabile, cancellabile senza perdita
    ITA-serie-a/2025-2026/
      events_slim.parquet  lineup_events.parquet
      team_match.parquet   player_match.parquet  shots.parquet
      walkforward_base.parquet  phase6d_predittori.parquet
  external/                     ← fornito a mano, provenienza da accertare
    quote/como_tiri_in_porta_2025-2026.xlsx
```

Tre separazioni, e ognuna corrisponde a una regola diversa:

- **`raw/` non si trasforma mai** (vincolo 9 della fase: nessuna esecuzione può
  cancellare o sovrascrivere grezzo già acquisito);
- **`processed/` è interamente rigenerabile** e per questo resta in `.gitignore`
  senza eccezioni;
- **`external/` è ciò che non ha una catena di acquisizione**: oggi solo il file
  delle quote, ed è esattamente il caso che 7F deve documentare.

### 3.5 `.gitignore`

```diff
-data/serie_a_2025_2026/
-data/processed/
-serie_a_2025_2026_events.csv
-events.csv
-data/events.csv
+# Grezzo ed elaborato: GB di dati, rigenerabili. Il manifest no: è la
+# provenienza (vincolo 8) e senza storia in git non è verificabile.
+data/raw/**
+!data/raw/
+!data/raw/manifest.json
+data/processed/
+data/external/
```

Il punto che cambia rispetto a oggi: **`data/raw/manifest.json` è versionato.**
Una riga senza provenienza non entra nel dataset, e una provenienza senza storia
non è controllabile: il manifest è piccolo, testuale e diffabile, ed è l'unico
artefatto di `data/` che deve stare in git.

`data/external/` è escluso: contiene file forniti a mano di provenienza non
accertata, e finché 7F non la documenta non ha titolo per entrare nel
repository.

### 3.6 Che cosa cambia in `config.py` — e perché i numeri non possono muoversi

**Cambia solo `sot/config.py`.** Nessun altro modulo di `sot/` e nessuno
script tocca percorsi a mano: la verifica è fatta, tutti passano per
`config.RAW_MATCH_DIR`, `config.MATCHES_JSON`, `config.PROCESSED`,
`config.TEAM_MATCH`, `config.PLAYER_MATCH`, `config.SHOTS_PARQUET`,
`config.EVENTS_SLIM`. I dieci punti in cui gli script costruiscono
`config.PROCESSED / "walkforward_base.parquet"` e simili restano validi per
costruzione.

```python
# Tassonomia: un solo posto in cui campionato e stagione hanno un nome.
LEAGUE_CODES = {"ITA-serie-a": {"football_data": "I1", "whoscored": (108, 5)}, ...}
SEASON_RE = r"^\d{4}-\d{4}$"

LEAGUE  = "ITA-serie-a"      # perimetro pubblicato delle Fasi 0-6
SEASON  = "2025-2026"

RAW      = DATA / "raw"
MANIFEST = RAW / "manifest.json"
EXTERNAL = DATA / "external"

def raw_dir(fonte, league=LEAGUE, season=SEASON):
    return RAW / fonte / league / season

def processed_dir(league=LEAGUE, season=SEASON):
    return DATA / "processed" / league / season

# I nomi restano identici: è ciò che rende il refactor invisibile a valle.
RAW_MATCH_DIR = raw_dir("whoscored") / "events"
MATCHES_JSON  = raw_dir("whoscored") / "matches.json"
PROCESSED     = processed_dir()
```

I nomi delle costanti **non cambiano**, cambia solo il loro valore. Ne segue che
il refactor non può alterare nessun numero: le stesse 380 righe di CSV entrano
negli stessi lettori e producono gli stessi Parquet. Se un numero si muove,
è un difetto e il blocco si ferma, come prescritto.

Lo spostamento dei dati è un `mv` sullo stesso volume — istantaneo anche per i
963 MB — e i Parquet di `processed/` si spostano con essi, quindi la suite
resta veloce e **non** ricalcola nulla.

Restano **fuori dalla tassonomia**, per ora: `reports/` e `reports/figures/`.
Il deliverable pubblicato è Serie A / Como, i nomi dei file di report sono già
prefissati per fase, e scoparli per campionato oggi sarebbe struttura senza
contenuto. Da rivedere quando 7D produrrà output sui cinque campionati.

---

## 4. Il controllo: suite verde e numeri identici

Il punto 3 del blocco. Protocollo che eseguirei, in quest'ordine:

1. **Prima**: copiare `reports/` in una cartella di lavoro fuori dal repository
   (è la fotografia di controllo; `reports/` è in `.gitignore`, non c'è git a
   fare da rete).
2. **Prima**: `pytest tests/ -q` → atteso `184 passed`. *Già eseguito: 184.*
3. Eseguire gli spostamenti e le modifiche approvate.
4. **Dopo**: `pytest tests/ -q` → deve dare di nuovo 184, **senza** ricalcolare
   i Parquet (se i tempi salgono da ~10 s a ~1 min, i dati non si sono spostati
   dove config li cerca).
5. **Dopo**: `run_phase5.py` (~2 min) e confronto **byte a byte** dei file
   rigenerati contro la copia del punto 1, escluse le sole righe di data/ora.
   I numeri da vedere invariati sono quelli dichiarati in `CLAUDE.md`:
   Como 4.34 · 5.03 a partita · 191 di stagione · IC80% [151, 240].
6. Se un solo numero diverge: **fermarsi e riferire**, senza aggiustare niente.

Un `run_phase1.py --force` completo (~20 s, rilegge i 380 CSV) è il controllo
che chiude il cerchio sui percorsi grezzi, ed è l'unico modo di verificare che
`RAW_MATCH_DIR` punti davvero ai file spostati e non a una cache.

---

## 5. Test nuovi del blocco — `tests/test_layout.py`

Il blocco chiede test nuovi. Sono invarianti di struttura, non controlli di
stile, e servono a impedire che la tassonomia si sfaldi al primo campionato in
più:

1. `RAW_MATCH_DIR`, `MATCHES_JSON`, `PROCESSED` **esistono** e contengono
   rispettivamente 380 CSV, un JSON leggibile, e i Parquet attesi.
2. `SEASON` rispetta `SEASON_RE`: quattro cifre, trattino, quattro cifre.
   Blocca il ritorno di `2025-26` e di `2526`.
3. `LEAGUE` è una chiave di `LEAGUE_CODES`, e ogni valore di `LEAGUE_CODES`
   dichiara il codice della fonte tabellare: la corrispondenza non si inventa
   al punto d'uso.
4. **Nessun modulo di `sot/` o `scripts/` contiene la stringa
   `serie_a_2025_2026`** né un letterale di stagione fuori da `config.py`.
   È il test che tiene il refactor: senza, la prima fretta rimette un percorso
   a mano.
5. Nessun modulo legge `serie_a_2025_2026_events.csv` (oggi vero, e va
   conservato dopo la cancellazione del file).
6. `raw_dir` e `processed_dir` rifiutano una stagione mal formata invece di
   costruire un percorso silenziosamente sbagliato.
7. `data/raw/` non è scrivibile dai moduli di `sot/`: nessuno di essi apre un
   percorso sotto `RAW` in scrittura (vincolo 9, verificato per grep sul
   sorgente — un test grossolano, ma è il vincolo che costa di più se salta).

---

## 6. Rischi, e cosa non faccio

### 6.1 Il rischio vero non è il refactor: è che non ci sia un commit

Le Fasi 0-6 non sono in git (§1). Un `mv` di 963 MB e la cancellazione di 1 GB
avvengono quindi **senza rete di sicurezza**, su un albero di lavoro che è
l'unica copia esistente di tutto il lavoro.

**Raccomandazione, e la considero la decisione più importante di questo blocco:
committare lo stato attuale prima di spostare qualsiasi cosa.** Un solo commit
sullo stato di fine Fase 6, così che il refactor sia un diff revisionabile e
reversibile invece di una modifica irreversibile del disco. Non lo faccio senza
richiesta esplicita — il commit è una tua decisione — ma spostare 1 GB di dati e
riscrivere i percorsi su un albero non versionato è il punto in cui questo
blocco può fare danno.

### 6.2 Cose che questa proposta **non** fa, di proposito

- **Non parametrizza lo scraper WhoScored** per campionato e stagione, benché
  `regole_fantacalcio.md` §7.1 lo richieda su cinque stagioni. Qui si sposta e
  si rinomina; parametrizzare è lavoro di modello di acquisizione, non di
  riorganizzazione, e mescolarlo renderebbe impossibile dire se un numero è
  cambiato per il refactor o per lo scraper.
- **Non scrive `acquisition/tabular.py`**, che è il blocco 7B.
- **Non scarica niente**, come da specifica.
- **Non tocca `sot/`** oltre a `config.py`, né `legacy/` oltre ad aggiungere
  `legacy/fork/` e una sezione al suo README.
- **Non verifica i termini d'uso di WhoScored**, che `regole_fantacalcio.md`
  §7.1 punto 3 dichiara mai fatti. È una verifica dovuta *prima* di estendere
  lo scraper all'indietro, non prima di spostarne il file.

### 6.3 Un rischio che resta anche dopo

`acquisition/whoscored/` erediterà `main.py` così com'è: 23 KB di codice del
fork con `sys.modules["env.main"]` iniettato a mano, Selenium e nessun test.
Spostarlo lo mette al posto giusto, non lo rende affidabile. A cinque stagioni
per cinque campionati quel codice diventa il collo di bottiglia, e va detto
adesso invece di scoprirlo in 7B.

---

## 7. Cosa serve approvare

Sono sette decisioni indipendenti: si può approvarne una parte.

| # | decisione | mia raccomandazione |
|---|---|---|
| 1 | commit dello stato di fine Fase 6 **prima** di toccare qualsiasi cosa (§6.1) | **sì, e prima di tutto il resto** |
| 2 | `acquisition/whoscored/` con i quattro file dello scraper, rinominati (§2.2) | sì |
| 3 | `legacy/fork/` con i sei residui del fork, `test.py` incluso (§2.2, §2.3) | sì, e `test.py` → `collaudo_fork_manuale.py`, non in `tests/` |
| 4 | cancellare 1,02 GB: i due `events.csv` demo e il concatenato (§2.4) | sì; alternativa non distruttiva in §2.4 |
| 5 | layout `data/{raw,processed,external}` con `ITA-serie-a` / `2025-2026` (§3) | sì |
| 6 | `data/raw/manifest.json` **versionato**, tutto il resto di `data/` no (§3.5) | sì |
| 7 | `tiri_in_porta.py` → `scripts/`, `Como.png` → `reports/figures/`, quote → `data/external/quote/` (§2.2) | sì |

Alla tua approvazione eseguo, nell'ordine, gli spostamenti, le quattro modifiche
di §2.5, `config.py` di §3.6, `tests/test_layout.py` di §5, e il protocollo di
verifica di §4 — e riferisco l'esito prima di aprire 7B.

---

## 8. Esito dell'esecuzione

Tutte e sette le decisioni sono state approvate ed eseguite. Il commit di
partenza è `728a782`; ogni spostamento è un `git mv`, quindi git riconosce le
rinomine (`R` in `git status`) e la storia non si spezza.

### 8.1 Il controllo — nessun numero si è mosso, ed è verificato

Il punto 3 del blocco, eseguito secondo il protocollo di §4.

| controllo | prima | dopo |
|---|---|---|
| `pytest tests/ -q` | 184 passed, 9.98 s | **206 passed, 7.55 s** (22 nuovi) |
| `run_phase1.py --force` (rilegge i 380 CSV) | — | 562.672 eventi, 380 partite, **4.034 / 4.432 / 3.637 / 5.105**, minuti 760/760 |
| `run_phase5.py` | — | Como **4.34** · **5.03**/partita · **191** stagione · IC80% **[151, 240]** |
| `phase1_audit.md` | | **identico** byte a byte |
| `phase5_proiezione_como_2627.{md,csv}` | | **identico** byte a byte |
| `phase5_ratings.csv` | | **identico** byte a byte |
| `fig1..fig8.png` | | **identiche** byte a byte, tutte e otto |

Due letture che il semplice "verde" non darebbe:

- **Il tempo della suite non è salito** (9.98 → 7.55 s con 22 test in più). Se i
  Parquet non fossero stati dove `config` li cerca, `conftest.py` li avrebbe
  ricalcolati e il tempo sarebbe passato a ~1 minuto. Il tempo è il controllo
  che la cache si è spostata insieme ai dati.
- **`run_phase1.py --force` è l'unico controllo che chiude il cerchio sul
  grezzo**: rilegge i 380 CSV dal percorso nuovo invece di fidarsi della cache.
  Senza quello, «verde» avrebbe significato solo «i Parquet esistono ancora».

### 8.2 Cinque deviazioni dalla proposta

Nessuna cambia un numero; tre sono correzioni della proposta stessa.

**1. `data/external/` non è escluso da `.gitignore`, contro §3.5.** Il file
delle quote risultava già tracciato nel commit `728a782`. Escludere una cartella
il cui unico file è tracciato non ha effetto e descrive male ciò che accade:
`.gitignore` avrebbe detto una cosa e il repository ne avrebbe fatta un'altra.
La regola è stata tolta, con la motivazione scritta nel file — ed è la scelta
più coerente col vincolo 8: i dati forniti a mano sono piccoli e la loro
provenienza non è ricostruibile da nessuna catena, quindi la storia in git è
l'unica traccia che ne resta.

**2. Nessun `acquisition/whoscored/__init__.py`.** §2.2 lo prevedeva. Quei
quattro file sono script: fanno import relativi alla propria cartella
(`from main import ...`, `import scrape_matches`) e si eseguono, non si
importano. Un `__init__.py` li dichiarerebbe importabili come pacchetto, cosa
che non funziona. La ragione è scritta in `acquisition/__init__.py`.

**3. `OUTPUT_FILE` di `scrape_season.py` è stato ripuntato**, non solo
riadattato. Scriveva in radice il CSV concatenato da 1 GB che questo blocco ha
cancellato: lasciarlo lì avrebbe fatto ricomparire alla prima riesecuzione
esattamente ciò che si è tolto. Ora va sotto `processed/`, che è l'albero
rigenerabile — non sotto `raw/`, che non ospita derivati.

**4. Due docstring corrette in `sot/io_events.py` e `scripts/run_phase6f.py`**,
che nominavano ancora `data/serie_a_2025_2026/`. Non erano nell'elenco di §2.5
perché la ricognizione aveva cercato percorsi *usati*, non percorsi *citati*.
Le ha trovate il test 4 di §5, che è precisamente il suo mestiere.

**5. Il test «nessun letterale di stagione fuori da `config.py`» è stato
ristretto ai percorsi.** Nella forma di §5 falliva su decine di righe di prosa:
i report parlano di «2025-26» e «2026-27» in continuazione, ed è corretto che lo
facciano. Vietare la parola avrebbe reso il test rumore e lo avrebbe fatto
disattivare al primo fastidio. Ora richiede che il letterale contenga anche un
separatore o un'estensione — cioè che sia un percorso. Il difetto da bloccare è
il percorso scritto a mano, non la parola.

### 8.3 Fatto in più, perché il resto sarebbe rimasto inconsistente

- **`CLAUDE.md`**: la sezione «Dati» indicava `data/serie_a_2025_2026/` e le
  trappole dei due `events.csv`, entrambe ora false. Aggiunti i vincoli **7, 8 e
  9** della Fase 7 accanto ai sei esistenti, l'albero di `data/`, e la sezione
  di fase 7A. Un diario che indica percorsi inesistenti è peggio di un diario
  assente: la prossima sessione ci si fida.
- **`README.md`**: sezione «Struttura» e attribuzione al fork, che nominava i
  tre script per il loro percorso di prima.
- **`legacy/README.md`**: sezione su `legacy/fork/`, e la distinzione fra i due
  divieti — `legacy/*` non si riusa **in nessun caso** (backtest circolare),
  `legacy/fork/` semplicemente non serve. Annotato lì anche che
  `Modello tiri in porta.py` legge file in stile `football-data.co.uk`, cioè la
  fonte del blocco 7B: è archiviato per la circolarità del backtest, non per la
  provenienza dei dati, e il divieto di riuso resta comunque.

### 8.4 Quello che resta aperto per 7B

- ~~`scrape_season.py` ha ancora `SEASON` e `COMPETITION_URL` scritti a mano~~
  **→ chiuso subito dopo, su richiesta**: `acquisition/whoscored/target.py`,
  `Target(league, season)` immutabile al posto di cinque globali, CLI con
  `--season`/`--dry-run`, e le cinque stagioni di `config.SEASONS_STORICHE` come
  default. 34 test in `tests/test_acquisizione_target.py`, che girano **senza
  selenium**: la logica sta in un modulo che non lo importa, proprio perché la
  fonte non è ancora contattabile. Dettaglio in `CLAUDE.md`, sezione 7A-bis.
- **`main_url` in `main.py` vale `https://1xbet.whoscored.com/`**, un mirror di
  affiliazione, non `www.whoscored.com`. È il dominio a cui ogni richiesta
  andrebbe: la verifica dei termini d'uso riguarda quello, non whoscored.com.
  Trovato eseguendo `--dry-run`, non modificato — cambiare il dominio dello
  scraper del fork è una decisione, non una correzione.
- **I termini d'uso di WhoScored non sono mai stati verificati**
  (`regole_fantacalcio.md` §7.1, terza conseguenza). L'autorizzazione ottenuta
  riguarda Fantacalcio.it e non si estende a una fonte diversa. Va accertato
  **prima** di estendere lo scraper all'indietro, non prima di spostarne il file
  — che è ciò che questo blocco ha fatto.
- **`data/raw/manifest.json` non esiste ancora**: la regola di `.gitignore` che
  lo versiona è stata verificata con `git check-ignore` su un file di prova, poi
  rimosso. Il file lo scrive 7B, che è il primo blocco ad acquisire qualcosa.
- **Lo scraper WhoScored non era eseguibile in questo `.venv`**: `selenium`,
  `mplsoccer` e `seaborn` erano in `requirements.txt` ma non installati. Era
  **preesistente** — l'ambiente era stato costruito per la modellazione, non per
  l'acquisizione — e non causato dagli spostamenti: i quattro file compilavano
  (`py_compile`), a fallire era l'`import selenium`, non un percorso.
  **`selenium` è stato installato** durante la parametrizzazione, altrimenti
  nemmeno `--dry-run` sarebbe partito. `mplsoccer` e `seaborn` restano fuori:
  servivano solo a `legacy/fork/visuals.py`.
