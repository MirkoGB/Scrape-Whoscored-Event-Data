# Tiri e tiri in porta 2026/2027: previsioni salvate contro risultati locali


Dati locali dal 15/08/2026 al 15/09/2026. 197 partite; 105 con previsione pre-partita verificabile rispetto alle date dichiarate negli archivi. Nessun nuovo fit e nessuno scaricamento.


## Copertura e selezione delle previsioni


| campionato         |   partite | prima_data   | ultima_data   |   pre_partita |   archivio_non_anteriore |   senza_previsione | dati_pagina_al   |   partite_training_pagina |
|:-------------------|----------:|:-------------|:--------------|--------------:|-------------------------:|-------------------:|:-----------------|--------------------------:|
| ITA-serie-a        |        40 | 2026-08-22   | 2026-09-14    |            22 |                       12 |                  6 | 2026-08-31       |                        20 |
| ENG-premier-league |        40 | 2026-08-21   | 2026-09-14    |            21 |                       14 |                  5 | 2026-08-31       |                        20 |
| ESP-la-liga        |        54 | 2026-08-15   | 2026-09-15    |            26 |                       20 |                  8 | 2026-08-31       |                        30 |
| GER-bundesliga     |        27 | 2026-08-28   | 2026-09-13    |            18 |                        6 |                  3 | 2026-08-30       |                         7 |
| FRA-ligue-1        |        36 | 2026-08-21   | 2026-09-13    |            18 |                       14 |                  4 | 2026-08-30       |                        18 |

Si usa l'ultima previsione salvata prima del giorno della partita: pagina del 03/09/2026 19:46, oppure CSV congelati del 30/08. La stessa data non prova l'anteriorità senza kickoff: si ripiega sull'archivio precedente, se disponibile. Il campione principale richiede anche dati di training anteriori alla gara. Le date di pubblicazione sono metadati locali, non una certificazione esterna. Gli hash dei CSV coincidono con il registro originale.


I CSV riportano stagione 2025-2026 perché descrivono il fit storico; sono applicati agli accoppiamenti 2026-2027. La pagina contiene anche le neopromosse. Le previsioni archiviate restano fisse: queste metriche non valutano eventuali aggiornamenti mai salvati. La Liga include anche la sesta partita di alcune squadre: lo snapshot precedente resta una previsione valida, ma non documenta il successivo passaggio al modello within-season.


## Lettura dei risultati


Nel campione pre-partita, per squadra, i tiri previsti sono 12.60 contro 13.87 osservati; i tiri in porta 4.34 contro 4.91. Il modello sottostima entrambi. La Serie A presenta gli errori assoluti medi più elevati su entrambi i bersagli; la Premier League i più bassi. Sono confronti descrittivi su partite e scale diverse.


Rispetto al baseline, la riduzione del CRPS complessivo è 1.93% sui tiri e 0.65% sui tiri in porta. Entrambi gli intervalli del delta comprendono zero: il vantaggio complessivo non è conclusivo. Per i tiri in porta il modello è peggiore del baseline in Liga e Serie A sul campione osservato. La Bundesliga mostra un vantaggio con intervallo puntuale sotto zero, ma su poche gare e senza correzione per confronti multipli.


I dati indicano di monitorare soprattutto il livello previsto in Serie A e Bundesliga. Un eventuale aggiustamento va verificato su nuove partite: correggere e rivalutare sugli stessi esiti non misurerebbe un miglioramento fuori campione.


## Risultati principali per squadra-partita


MAE = errore assoluto medio; bias = previsto meno osservato (negativo: sottostima). Il CRPS valuta la distribuzione NB2, usando la dispersione pubblicata; più basso è meglio. Copertura80 indica la frequenza dentro l'intervallo centrale nominale all'80%; sui conteggi la discrezione può produrre coperture maggiori.


### Tiri


| campionato         |   partite |   previsto |   osservato |   mae |   rmse |   bias |   crps |   copertura80 |
|:-------------------|----------:|-----------:|------------:|------:|-------:|-------:|-------:|--------------:|
| TUTTI              |       105 |     12.598 |      13.871 | 4.326 |  5.566 | -1.273 |  3.121 |         0.762 |
| ENG-premier-league |        21 |     12.565 |      13.048 | 3.422 |  4.430 | -0.483 |  2.459 |         0.881 |
| ESP-la-liga        |        26 |     12.441 |      12.769 | 4.076 |  5.066 | -0.328 |  2.893 |         0.788 |
| FRA-ligue-1        |        18 |     12.493 |      13.917 | 3.900 |  5.153 | -1.424 |  2.910 |         0.694 |
| GER-bundesliga     |        18 |     13.405 |      15.500 | 4.739 |  5.889 | -2.095 |  3.455 |         0.750 |
| ITA-serie-a        |        22 |     12.243 |      14.591 | 5.493 |  6.979 | -2.348 |  3.923 |         0.682 |

### Tiri in porta


| campionato         |   partite |   previsto |   osservato |   mae |   rmse |   bias |   crps |   copertura80 |
|:-------------------|----------:|-----------:|------------:|------:|-------:|-------:|-------:|--------------:|
| TUTTI              |       105 |      4.342 |       4.914 | 1.990 |  2.559 | -0.572 |  1.432 |         0.819 |
| ENG-premier-league |        21 |      4.207 |       4.310 | 1.765 |  2.108 | -0.103 |  1.207 |         0.881 |
| ESP-la-liga        |        26 |      4.351 |       4.615 | 1.996 |  2.598 | -0.265 |  1.418 |         0.808 |
| FRA-ligue-1        |        18 |      4.374 |       4.944 | 1.836 |  2.518 | -0.570 |  1.360 |         0.889 |
| GER-bundesliga     |        18 |      4.860 |       5.361 | 2.145 |  2.689 | -0.501 |  1.578 |         0.722 |
| ITA-serie-a        |        22 |      4.013 |       5.455 | 2.196 |  2.819 | -1.442 |  1.600 |         0.795 |

## Confronto con la media della squadra nella stagione precedente


Baseline calcolato solo sul 2025-2026; per le neopromosse si usa la media del campionato. Il confronto usa esattamente le stesse righe e la stessa dispersione. Intervalli al 95% da bootstrap per partita, stratificato per campionato (5.000 repliche). Delta negativo favorisce il modello. Gli intervalli sono puntuali, senza correzione per confronti multipli, e non modellano dipendenze persistenti fra gare della stessa squadra.


| campionato         | bersaglio   |   partite |   crps |   crps_baseline |   miglioramento_crps_pct |   delta_crps |   delta_ci95_low |   delta_ci95_high |
|:-------------------|:------------|----------:|-------:|----------------:|-------------------------:|-------------:|-----------------:|------------------:|
| TUTTI              | shots       |       105 |  3.121 |           3.182 |                    1.927 |       -0.061 |           -0.232 |             0.108 |
| TUTTI              | sot         |       105 |  1.432 |           1.441 |                    0.655 |       -0.009 |           -0.069 |             0.049 |
| ENG-premier-league | shots       |        21 |  2.459 |           2.484 |                    1.003 |       -0.025 |           -0.348 |             0.314 |
| ENG-premier-league | sot         |        21 |  1.207 |           1.270 |                    4.893 |       -0.062 |           -0.160 |             0.029 |
| ESP-la-liga        | shots       |        26 |  2.893 |           2.873 |                   -0.699 |        0.020 |           -0.340 |             0.382 |
| ESP-la-liga        | sot         |        26 |  1.418 |           1.311 |                   -8.152 |        0.107 |           -0.026 |             0.259 |
| FRA-ligue-1        | shots       |        18 |  2.910 |           3.144 |                    7.452 |       -0.234 |           -0.556 |             0.086 |
| FRA-ligue-1        | sot         |        18 |  1.360 |           1.369 |                    0.665 |       -0.009 |           -0.109 |             0.084 |
| GER-bundesliga     | shots       |        18 |  3.455 |           3.532 |                    2.177 |       -0.077 |           -0.392 |             0.247 |
| GER-bundesliga     | sot         |        18 |  1.578 |           1.762 |                   10.425 |       -0.184 |           -0.331 |            -0.050 |
| ITA-serie-a        | shots       |        22 |  3.923 |           3.961 |                    0.958 |       -0.038 |           -0.498 |             0.424 |
| ITA-serie-a        | sot         |        22 |  1.600 |           1.554 |                   -2.940 |        0.046 |           -0.085 |             0.184 |

## Probabilità di superamento delle linee


Probabilità ricostruite dai parametri salvati, mantenendo gli arrotondamenti della pagina (lambda a 4 decimali, dispersione a 3). Ogni riga è una squadra-partita. La frequenza osservata è descrittiva, non un baseline utilizzabile prima degli esiti.


| campionato   | bersaglio   |   linea |   n |   p_media |   frequenza |   brier |
|:-------------|:------------|--------:|----:|----------:|------------:|--------:|
| TUTTI        | shots       |   8.500 | 210 |     0.779 |       0.790 |   0.158 |
| TUTTI        | shots       |  10.500 | 210 |     0.623 |       0.695 |   0.198 |
| TUTTI        | shots       |  12.500 | 210 |     0.462 |       0.552 |   0.224 |
| TUTTI        | shots       |  14.500 | 210 |     0.320 |       0.419 |   0.231 |
| TUTTI        | shots       |  16.500 | 210 |     0.208 |       0.290 |   0.191 |
| TUTTI        | sot         |   2.500 | 210 |     0.770 |       0.819 |   0.146 |
| TUTTI        | sot         |   3.500 | 210 |     0.599 |       0.657 |   0.210 |
| TUTTI        | sot         |   4.500 | 210 |     0.427 |       0.552 |   0.240 |
| TUTTI        | sot         |   5.500 | 210 |     0.282 |       0.367 |   0.219 |

## Totali delle due squadre per partita


| campionato         | bersaglio   |   partite |   previsto |   osservato |   mae |   bias |
|:-------------------|:------------|----------:|-----------:|------------:|------:|-------:|
| TUTTI              | shots       |       105 |     25.197 |      27.743 | 5.586 | -2.546 |
| TUTTI              | sot         |       105 |      8.685 |       9.829 | 3.147 | -1.144 |
| ENG-premier-league | shots       |        21 |     25.129 |      26.095 | 3.793 | -0.966 |
| ENG-premier-league | sot         |        21 |      8.414 |       8.619 | 2.967 | -0.205 |
| ESP-la-liga        | shots       |        26 |     24.882 |      25.538 | 5.531 | -0.656 |
| ESP-la-liga        | sot         |        26 |      8.702 |       9.231 | 3.511 | -0.529 |
| FRA-ligue-1        | shots       |        18 |     24.986 |      27.833 | 5.895 | -2.848 |
| FRA-ligue-1        | sot         |        18 |      8.748 |       9.889 | 2.970 | -1.141 |
| GER-bundesliga     | shots       |        18 |     26.811 |      31.000 | 5.798 | -4.189 |
| GER-bundesliga     | sot         |        18 |      9.720 |      10.722 | 2.373 | -1.003 |
| ITA-serie-a        | shots       |        22 |     24.486 |      29.182 | 6.937 | -4.696 |
| ITA-serie-a        | sot         |        22 |      8.026 |      10.909 | 3.665 | -2.883 |

## Errori maggiori nel campione pre-partita


### shots


| campionato     | date                | team             | opponent   |   is_home |   previsto_shots |   shots |   errore_shots |
|:---------------|:--------------------|:-----------------|:-----------|----------:|-----------------:|--------:|---------------:|
| ITA-serie-a    | 2026-09-05 00:00:00 | Roma             | Atalanta   |         1 |           14.077 |      39 |        -24.923 |
| ITA-serie-a    | 2026-09-12 00:00:00 | Frosinone        | Genoa      |         0 |           11.027 |      26 |        -14.973 |
| GER-bundesliga | 2026-09-12 00:00:00 | Bayer Leverkusen | Augsburg   |         0 |           15.349 |      30 |        -14.651 |
| ITA-serie-a    | 2026-09-05 00:00:00 | Inter            | Napoli     |         1 |           15.108 |      29 |        -13.892 |
| ESP-la-liga    | 2026-09-14 00:00:00 | Real Betis       | Villarreal |         0 |           12.251 |      26 |        -13.749 |
| FRA-ligue-1    | 2026-09-03 00:00:00 | Toulouse         | Lille      |         1 |           10.731 |      24 |        -13.269 |
| FRA-ligue-1    | 2026-09-06 00:00:00 | Troyes           | Strasbourg |         1 |           14.431 |      27 |        -12.569 |
| GER-bundesliga | 2026-09-13 00:00:00 | Bayern Munich    | Elversberg |         0 |           16.035 |      28 |        -11.965 |

### sot


| campionato     | date                | team       | opponent     |   is_home |   previsto_sot |   sot |   errore_sot |
|:---------------|:--------------------|:-----------|:-------------|----------:|---------------:|------:|-------------:|
| ESP-la-liga    | 2026-09-14 00:00:00 | Real Betis | Villarreal   |         0 |          3.795 |    12 |       -8.205 |
| FRA-ligue-1    | 2026-09-06 00:00:00 | Strasbourg | Troyes       |         0 |          4.121 |    12 |       -7.879 |
| ITA-serie-a    | 2026-09-13 00:00:00 | Monza      | Lecce        |         0 |          3.683 |    11 |       -7.317 |
| ITA-serie-a    | 2026-09-11 00:00:00 | Fiorentina | Venezia      |         0 |          3.276 |    10 |       -6.724 |
| ITA-serie-a    | 2026-09-14 00:00:00 | Inter      | Udinese      |         1 |          5.687 |    12 |       -6.313 |
| GER-bundesliga | 2026-09-11 00:00:00 | Schalke 04 | Union Berlin |         0 |          3.879 |    10 |       -6.121 |
| FRA-ligue-1    | 2026-09-03 00:00:00 | Toulouse   | Lille        |         1 |          4.083 |    10 |       -5.917 |
| FRA-ligue-1    | 2026-09-05 00:00:00 | Brest      | Le Havre     |         0 |          3.529 |     9 |       -5.471 |

## Archivio non anteriore: solo confronto descrittivo


Le partite seguenti hanno una previsione nel CSV, ma la partita precede o coincide con il giorno di congelamento. Il modello usa lo storico precedente, ma questo non dimostra che il pronostico sia stato pubblicato prima della gara. Non sono incluse nel risultato principale. Le partite senza previsione valutabile rimangono nei CSV di dettaglio con valori previsti vuoti.


| bersaglio   | campionato         |   partite |   previsto |   osservato |   mae |   rmse |   bias |   crps |   copertura80 |
|:------------|:-------------------|----------:|-----------:|------------:|------:|-------:|-------:|-------:|--------------:|
| shots       | TUTTI              |        66 |     12.598 |      14.008 | 3.817 |  4.991 | -1.410 |  2.779 |         0.856 |
| sot         | TUTTI              |        66 |      4.346 |       4.614 | 1.733 |  2.125 | -0.268 |  1.208 |         0.886 |
| shots       | ENG-premier-league |        14 |     12.650 |      14.321 | 3.943 |  5.393 | -1.672 |  2.947 |         0.857 |
| sot         | ENG-premier-league |        14 |      4.213 |       4.464 | 1.743 |  2.140 | -0.252 |  1.238 |         0.821 |
| shots       | ESP-la-liga        |        20 |     12.591 |      12.825 | 3.751 |  4.466 | -0.234 |  2.575 |         0.850 |
| sot         | ESP-la-liga        |        20 |      4.405 |       4.675 | 1.968 |  2.312 | -0.270 |  1.314 |         0.875 |
| shots       | FRA-ligue-1        |        14 |     12.463 |      13.929 | 3.731 |  4.931 | -1.465 |  2.741 |         0.821 |
| sot         | FRA-ligue-1        |        14 |      4.395 |       4.571 | 1.680 |  1.996 | -0.176 |  1.148 |         0.964 |
| shots       | GER-bundesliga     |         6 |     13.329 |      16.000 | 3.472 |  4.019 | -2.671 |  2.399 |         1.000 |
| sot         | GER-bundesliga     |         6 |      4.920 |       5.750 | 1.247 |  1.940 | -0.830 |  1.038 |         0.917 |
| shots       | ITA-serie-a        |        12 |     12.341 |      14.708 | 4.053 |  5.777 | -2.367 |  3.158 |         0.833 |
| sot         | ITA-serie-a        |        12 |      4.059 |       4.167 | 1.636 |  2.011 | -0.108 |  1.155 |         0.875 |

## Artefatti e riproduzione


- `analisi_2627_partite.csv`: tutte le gare, tiri e SoT previsti/osservati casa, trasferta e totale.
- `analisi_2627_squadra_partita.csv`: errori, fonte, data di pubblicazione e ammissibilità per lato.
- `analisi_2627_metriche.csv`, `analisi_2627_brier.csv`, `analisi_2627_totali.csv`: misure aggregate.
- `analisi_2627_copertura.csv`, `analisi_2627_provenienza.json`, `analisi_2627_pagina_snapshot.json`: audit.
- Riproduzione: `.venv/Scripts/python.exe scripts/analizza_previsioni_2627.py`.


La vecchia verifica sulle prime due partite per squadra ha un perimetro diverso: i suoi risultati non sono direttamente confrontabili con questi. Nessuna conclusione sulla stagione intera o sulla redditività delle scommesse deriva da questo campione.


## Controlli eseguiti in questa analisi

Audit indipendente superato: chiavi uniche, due lati per gara, anteriorit? della previsione, conteggi, somme e metriche riconciliati. Gli hash dei cinque archivi congelati coincidono con il registro.

Test esistenti di validate e fase16_o1: 60 superati, 1 fallito. Il test `test_una_coppia_ambigua_non_diventa_un_disaccordo` richiede un caso ambiguo nel calendario francese che non esiste pi? nella fonte locale aggiornata; questa analisi non usa l?assegnazione della giornata. Nessun modulo del modello ? stato modificato.
