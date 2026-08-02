# legacy/ — codice escluso dalla pipeline

Questi file **non fanno parte** del modello in `sot/` e non vanno riusati come
sono. Sono conservati perche' documentano il lavoro precedente, non perche'
siano validi.

**Due cose diverse, e il divieto di riuso vale solo per la prima:**

| | cos'e' | riuso |
| --- | --- | --- |
| `legacy/*` (questa cartella) | il backtest circolare e il modello che lo alimenta | **vietato in ogni caso** |
| `legacy/fork/` | materiale d'origine del fork, conservato per attribuzione | non serve al modello, ma non e' sbagliato: e' di un altro progetto |

## Perche' sono qui

### `analisi_over55_como.py` + `como_tip_quote_2526.csv` + `dettaglio_scommesse_over55_como.csv` + `risultato_over55_como.png`

Simulano una strategia di scommesse Over 5.5 tiri in porta sul Como, ma le
quote contro cui scommettono (`como_tip_quote_2526.csv`) **sono generate dal
modello stesso**: `Modello tiri in porta.py` calcola una probabilita', la
converte in quota applicando un margine Buchdahl del 7%, e `analisi_over55_como.py`
poi "scommette" contro quella quota.

Il backtest e' quindi circolare e privo di significato. Il mercato contro cui
si scommette e' lo stesso modello che produce la previsione, quindi qualunque
regola sistematica risulta redditizia per costruzione: il margine e' l'unica
cosa che separa le due parti, e il segno del risultato dipende solo da come e'
stato applicato. Non misura alcuna capacita' predittiva.

Per una valutazione sensata servono **prezzi di mercato reali**, raccolti in
tempo pre-partita da un operatore. Finche' non ci sono, questa parte resta
disattivata.

### `Modello tiri in porta.py`

Modello Poisson ridge con effetti attacco/difesa, decadimento esponenziale e
sovradispersione NB2. L'impianto statistico e' corretto ed e' stato ripreso in
`sot/model_team.py`, ma questo script:

* legge `sa_2425.csv` e `sa_2526.csv`, file in stile football-data.co.uk che
  **non esistono nel repository** — quindi cosi' com'e' non gira;
* usa aggregati (`HST`/`AST`) e non tocca i dati evento, che sono il motivo per
  cui questo progetto esiste;
* produce le quote alla base del backtest circolare descritto sopra.

> **Nota per il blocco 7B.** `Modello tiri in porta.py` legge file in stile
> `football-data.co.uk`, che e' esattamente la fonte del blocco 7B. Il fatto che
> quel codice sia archiviato **non** dice niente sulla fonte: e' archiviato per
> la circolarita' del backtest, non per la provenienza dei dati. Resta comunque
> vietato riusarlo — 7B scrive il proprio acquisitore da zero.

## `legacy/fork/` — materiale d'origine, conservato per attribuzione

Residui del repository da cui questo nasce
([Scrape-Whoscored-Event-Data](https://github.com/Ali-Hasan-Khan/Scrape-Whoscored-Event-Data)
di Ali Hasan Khan). Spostati qui dalla radice nella Fase 7A: non servono al
modello, ma cancellarli toglierebbe la traccia di che cosa e' stato ereditato.

| file | cos'e' | perche' non serve |
| --- | --- | --- |
| `EPV_grid.csv` | griglia Expected Possession Value di Laurie Shaw | letta solo da `addEpvToDataFrame` in `acquisition/whoscored/main.py`, che nessuna fase chiama |
| `linecollection.py` | copia di un modulo di mplsoccer | nessun import nel repository |
| `visuals.py` | visualizzazioni del fork | `sot/figures.py` e' ridisegnato da zero e non lo importa |
| `tutorial.ipynb` | notebook dimostrativo (1 MB) | nessun riferimento |
| `logo.jpg` | logo del fork | — |
| `collaudo_fork_manuale.py` | ex `test.py` in radice | **non e' un test pytest**: vedi sotto |

`collaudo_fork_manuale.py` e' un collaudo manuale dello scraper del fork, non un
test automatico, e metterlo sotto `tests/` avrebbe rotto la suite:

* importa `from env.main import ...`, e il modulo `env` **non esiste** nel
  repository — errore gia' in fase di raccolta;
* apre Chrome con `webdriver.Chrome('drivers/chromedriver.exe')`, percorso
  inesistente, e richiede rete;
* asserisce sulla Premier League 2019/2020 (`len(match_urls) == 380`,
  `events_df.shape[1] == 259`), cioe' su dati che questo progetto non usa.

Il rinomino da `test.py` serve anche a togliergli il prefisso `test_`/`test.py`,
cosi' che pytest non lo raccolga nemmeno se un domani `legacy/` finisse dentro
il perimetro di raccolta.

## Cosa e' rimasto fuori da qui

`Como_tiri_in_porta_quote_2025-26.xlsx` **non e' in `legacy/`**: la Fase 7A lo
ha spostato in `data/external/quote/como_tiri_in_porta_2025-2026.xlsx`, perche'
non e' codice archiviato ma un dato fornito a mano di cui non si conosce
l'origine. Non e' prodotto da nessuno script del repository, quindi non e'
chiaro se sia un derivato di questa pipeline o un file compilato a mano: **e' il
blocco 7F a doverlo accertare e documentare.**
