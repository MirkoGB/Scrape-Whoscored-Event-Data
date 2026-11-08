# Over 2026/27: calibrazione e protocollo di paper trading

**Profitto non dimostrato: zero quote storiche reali e verificabili per il perimetro.** Nessun ROI storico viene inventato.

Le 105 gare erano già state analizzate: sviluppo e diagnosi, non test intoccato della strategia. Il test economico comincia dopo il congelamento del protocollo.

## Quote escluse

Il foglio Excel Como 2025/26 genera i prezzi dalle probabilità (`1/(p^(1/k))`) con un margine ipotizzato. Non contiene un prezzo di mercato utilizzabile per un backtest. Il CSV legacy manca di bookmaker e timestamp. Non è stato riusato il codice legacy.

## Calibrazione delle linee

Squadre: 105 partite / 210 lati. Totali: 98 partite con probabilità salvate nella pagina pre-partita; le altre 7 non hanno una distribuzione totale archiviata. Le probabilità di squadra sono ricostruite dai parametri salvati, con i loro arrotondamenti. Baseline: frequenza 2025/26 del rispettivo campionato e mercato, disponibile prima delle gare.

| league   | scope   | target   |    line |   n |   matches |   dates |   predicted |   observed |   calibration_gap |   gap_low |   gap_high |   brier |   brier_baseline |   brier_skill |   logloss |
|:---------|:--------|:---------|--------:|----:|----------:|--------:|------------:|-----------:|------------------:|----------:|-----------:|--------:|-----------------:|--------------:|----------:|
| TUTTI    | team    | shots    |  8.5000 | 210 |       105 |      11 |      0.7787 |     0.7905 |            0.0117 |   -0.0174 |     0.0475 |  0.1579 |           0.1653 |        0.0448 |    0.4832 |
| TUTTI    | team    | shots    | 10.5000 | 210 |       105 |      11 |      0.6234 |     0.6952 |            0.0718 |    0.0317 |     0.0969 |  0.1984 |           0.2164 |        0.0835 |    0.5797 |
| TUTTI    | team    | shots    | 12.5000 | 210 |       105 |      11 |      0.4623 |     0.5524 |            0.0901 |    0.0434 |     0.1577 |  0.2238 |           0.2542 |        0.1197 |    0.6391 |
| TUTTI    | team    | shots    | 14.5000 | 210 |       105 |      11 |      0.3197 |     0.4190 |            0.0993 |    0.0578 |     0.1568 |  0.2314 |           0.2520 |        0.0818 |    0.6667 |
| TUTTI    | team    | shots    | 16.5000 | 210 |       105 |      11 |      0.2079 |     0.2905 |            0.0826 |    0.0380 |     0.1462 |  0.1914 |           0.2102 |        0.0891 |    0.5698 |
| TUTTI    | team    | sot      |  2.5000 | 210 |       105 |      11 |      0.7696 |     0.8190 |            0.0495 |   -0.0018 |     0.0974 |  0.1462 |           0.1549 |        0.0561 |    0.4636 |
| TUTTI    | team    | sot      |  3.5000 | 210 |       105 |      11 |      0.5991 |     0.6571 |            0.0581 |   -0.0129 |     0.1045 |  0.2101 |           0.2296 |        0.0850 |    0.6090 |
| TUTTI    | team    | sot      |  4.5000 | 210 |       105 |      11 |      0.4275 |     0.5524 |            0.1249 |    0.0689 |     0.1867 |  0.2398 |           0.2643 |        0.0926 |    0.6726 |
| TUTTI    | team    | sot      |  5.5000 | 210 |       105 |      11 |      0.2818 |     0.3667 |            0.0849 |    0.0321 |     0.1574 |  0.2193 |           0.2384 |        0.0803 |    0.6283 |
| TUTTI    | total   | shots    | 20.5000 |  98 |        98 |       9 |      0.7823 |     0.8980 |            0.1156 |    0.0590 |     0.1657 |  0.1111 |           0.1019 |       -0.0902 |    0.3857 |
| TUTTI    | total   | shots    | 22.5000 |  98 |        98 |       9 |      0.6650 |     0.8163 |            0.1514 |    0.0724 |     0.2179 |  0.1861 |           0.1632 |       -0.1405 |    0.5594 |
| TUTTI    | total   | shots    | 24.5000 |  98 |        98 |       9 |      0.5339 |     0.6837 |            0.1497 |    0.0620 |     0.2539 |  0.2391 |           0.2387 |       -0.0016 |    0.6740 |
| TUTTI    | total   | shots    | 26.5000 |  98 |        98 |       9 |      0.4037 |     0.5204 |            0.1167 |    0.0472 |     0.2533 |  0.2488 |           0.2675 |        0.0699 |    0.6906 |
| TUTTI    | total   | shots    | 28.5000 |  98 |        98 |       9 |      0.2870 |     0.4388 |            0.1517 |    0.0740 |     0.3011 |  0.2592 |           0.2687 |        0.0355 |    0.7236 |
| TUTTI    | total   | sot      |  6.5000 |  98 |        98 |       9 |      0.7457 |     0.8265 |            0.0809 |    0.0282 |     0.1286 |  0.1476 |           0.1511 |        0.0233 |    0.4732 |
| TUTTI    | total   | sot      |  7.5000 |  98 |        98 |       9 |      0.6259 |     0.7041 |            0.0782 |   -0.0046 |     0.1942 |  0.2131 |           0.2139 |        0.0037 |    0.6190 |
| TUTTI    | total   | sot      |  8.5000 |  98 |        98 |       9 |      0.4991 |     0.6224 |            0.1234 |    0.0490 |     0.2442 |  0.2459 |           0.2519 |        0.0239 |    0.6852 |
| TUTTI    | total   | sot      |  9.5000 |  98 |        98 |       9 |      0.3777 |     0.5612 |            0.1836 |    0.1126 |     0.3254 |  0.2803 |           0.2877 |        0.0257 |    0.7590 |

Il gap è osservato meno previsto. IC95 bootstrap per data (2.000 repliche, seed 42); preserva i lati e le gare dello stesso giorno. Poche date: intervalli esplorativi, senza correzione multipla. Le fasce di affidabilità sono fisse: 0–20–40–60–80–100%, separate per linea.

## Dipendenza

| league   | pair                       |   n |   correlation |
|:---------|:---------------------------|----:|--------------:|
| TUTTI    | tiri casa / tiri trasferta | 105 |        -0.138 |
| TUTTI    | SoT casa / SoT trasferta   | 105 |         0.102 |
| TUTTI    | tiri / SoT casa            | 105 |         0.595 |
| TUTTI    | tiri / SoT trasferta       | 105 |         0.643 |

Correlazioni descrittive dei residui, non un modello congiunto validato. Sono vietate selezioni della stessa partita e squadre ripetute. Per gare diverse si mostra il prodotto delle probabilità solo come scenario di indipendenza e l'intervallo di Fréchet `[max(0,sum(p)-n+1), min(p)]`, valido senza assumere indipendenza a marginali date.

## Regole congelate prima del test futuro

{
  "version": 1,
  "mode": "paper_only",
  "bankroll": 100.0,
  "daily_budget": 1.0,
  "stop_drawdown": 20.0,
  "probability_stress": 0.05,
  "extra_stress": 0.1,
  "min_robust_ev": 0.05,
  "max_quote_age_minutes": 60,
  "pool_limit": 18,
  "sizes": [
    1,
    2,
    3,
    4,
    5
  ],
  "selection": "massimo EV al limite inferiore Frechet con p ridotta di 5 punti; astensione se EV < 5%",
  "same_match": "vietato",
  "shared_team": "vietato",
  "same_bookmaker": true,
  "multiple_price": "quota complessiva esplicitamente documentata; prodotto quote solo indicativo",
  "settlement": "90 minuti + recupero; linee .5; vittoria/perdita/annullata; fonte e regole documentate",
  "holdout": "solo decisioni registrate dopo il congelamento, prima delle gare; nessun tuning sul test",
  "budget_note": "100 unita virtuali; massimo 1 unita per strategia e data delle gare; non spesa in caso di astensione",
  "frozen_at": "2026-09-16T13:08:28.915682+00:00",
  "test_from": "2026-09-17",
  "sha256": "c456affb2d311439db7011c0f643b3a7d55c2482a940faae4a8c2590ae76aced"
}

Il taglio di 5 punti percentuali (e lo stress a 10) è un'ipotesi prudente, non un intervallo di confidenza individuale e non una garanzia. Nessuna ricalibrazione verso l'alto basata sugli esiti già visti. Prezzi delle multiple richiesti esplicitamente: il prodotto delle quote singole non prova che quella schedina sia disponibile.

Ogni strategia dispone di 100 unità iniziali e al massimo 1 unità per data di gioco. Se non gioca, mantiene il capitale: riportare anche l'esposizione effettiva. Stop a 20 unità di drawdown e nessun nuovo piano finché una puntata precedente è da liquidare. Pool: migliori 18 selezioni per EV marginale stressato, una selezione per bookmaker/mercato; stessa regola per tutte le taglie.

## Rendimento osservato

|   size |   bets |   abstentions |   pending |   staked_settled | profit   | roi   |   bankroll | loss_rate   | max_losing_streak   | max_drawdown   |
|-------:|-------:|--------------:|----------:|-----------------:|:---------|:------|-----------:|:------------|:--------------------|:---------------|
|      1 |      0 |             0 |         0 |            0.000 |          |       |    100.000 |             |                     |                |
|      2 |      0 |             0 |         0 |            0.000 |          |       |    100.000 |             |                     |                |
|      3 |      0 |             0 |         0 |            0.000 |          |       |    100.000 |             |                     |                |
|      4 |      0 |             0 |         0 |            0.000 |          |       |    100.000 |             |                     |                |
|      5 |      0 |             0 |         0 |            0.000 |          |       |    100.000 |             |                     |                |

Valori assenti indicano non misurabile, non profitto zero. Gli scenari di perdita del capitale si attivano solo con schedine congelate: 5.000 percorsi, giorni indipendenti, scenario indipendente e stress prudente; non sono risultati di backtest.

## Raccolta e uso
Vedi `docs/guide/paper_over.md` e `docs/guide/quote_sisal.md`. Il raccoglitore Sisal registra automaticamente tentativi e osservazioni riconoscibili; la verifica sul sito reale è ancora bloccata dall'accesso. Le osservazioni restano separate dal protocollo economico finché le regole non sono riconciliate. Nessun account collegato o giocata reale; il protocollo usa solo unità virtuali.
