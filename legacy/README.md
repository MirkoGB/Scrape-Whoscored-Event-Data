# legacy/ — codice escluso dalla pipeline

Questi file **non fanno parte** del modello in `sot/` e non vanno riusati come
sono. Sono conservati perche' documentano il lavoro precedente, non perche'
siano validi.

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

## Cosa e' rimasto fuori da qui

`Como_tiri_in_porta_quote_2025-26.xlsx` e' rimasto nella cartella principale:
non e' prodotto da nessuno degli script del repository, quindi non e' chiaro
se sia un derivato di questa pipeline o un file compilato a mano.
