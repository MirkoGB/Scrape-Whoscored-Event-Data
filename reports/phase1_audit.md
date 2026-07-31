# Fase 1 — audit e aggregazione

Eventi letti: 562,672 da 380 partite.

## Controllo di sanita'

| Voce | Riferimento | Ottenuto | Scarto |
|---|---|---|---|
| media di campionato | 4.03 | 4.034 | +0.10% |
| media in casa | 4.43 | 4.432 | +0.04% |
| media in trasferta | 3.63 | 3.637 | +0.19% |
| media del Como | 5.11 | 5.105 | -0.09% |
| partite | 380.0 | 380.000 | +0.00% |

Esito: **superato** (soglia 5%).

## Ricostruzione dei minuti

Squadra-partita riconciliate esattamente: **760/760**.
Minuti totali: 817,374. Giocatori con almeno un minuto: 586.

## xG interno

- tiri 9,359, gol 900
- somma xG 900.6 contro 900 gol
- log-loss 0.2431 contro 0.3166 del tasso base
- AUC 0.811

Non e' xG di un fornitore: e' stimato in casa, cross-fitted a 5 fold raggruppati per partita.

## Tabelle prodotte

- `team_match.parquet` — 760 righe, 24 colonne
- `player_match.parquet` — 17774 righe, 17 colonne
- `shots.parquet` — 9359 tiri