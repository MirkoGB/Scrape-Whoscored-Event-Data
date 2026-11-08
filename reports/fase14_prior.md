# Fase 14 / A2 — il prior dalla stagione precedente

_Generato da `scripts/run_fase14_prior.py` — 2026-08-30 15:39_

## Il criterio, scritto prima dei numeri

```
il prior si adotta se, sulle righe di avvio (team_match_idx <= 5) e sulle sole transizioni TARATE: (a) batte «media squadra prec» in log-verosimiglianza per riga con t appaiato per cluster di partita sopra 2, e (b) il segno del margine e' positivo in almeno 3 campionati su 5. Altrimenti non si adotta e la previsione sotto la 6a giornata resta dichiarata non disponibile.
```

Righe di avvio: `team_match_idx <= 5`. Controllo: da 6 a 12.

I cinque candidati: `con prior` · `senza prior` · `modello prec` · `media squadra prec` · `media campionato prec`.

La riga `due regimi` non e' un sesto modello: e' la composizione di due candidati gia' dichiarati a una soglia dichiarata **altrove** (`config.BURN_IN_ROUND`, Fase 2). Regola: team_match_idx < 6: `modello prec`; team_match_idx >= 6: `con prior`. La soglia e' `config.BURN_IN_ROUND`, dichiarata dalla Fase 2 e non scelta qui.

## Bersaglio `shots`

**Il criterio scritto prima: NON adottato** — t = 0.40 (serve > 2) e 3/5 campionati positivi (ne servono 3)

### Poolato sulle transizioni tarate — righe di avvio

| candidato | n | mae | bias | loglik_per_riga |
|---|---|---|---|---|
| con prior | 1386 | 4.0174 | -0.1327 | -3.1753 |
| senza prior | 1386 | 4.2515 | -0.0663 | -3.3214 |
| modello prec | 1386 | 3.8559 | -0.1958 | -3.0958 |
| media squadra prec | 1386 | 4.0773 | 0.1646 | -3.1864 |
| media campionato prec | 1386 | 4.2161 | -0.0878 | -3.2705 |
| due regimi | 1386 | 3.8559 | -0.1958 | -3.0958 |

#### `con prior` contro gli altri

| soggetto | avversario | n | delta_loglik_per_riga | t_riga | t_cluster | vince_il_soggetto | riferimento |
|---|---|---|---|---|---|---|---|
| con prior | modello prec | 1386 | -0.0795 | -3.4818 | -3.3253 | False | False |
| con prior | due regimi | 1386 | -0.0795 | -3.4818 | -3.3253 | False | False |
| con prior | media squadra prec | 1386 | 0.0111 | 0.3985 | 0.3976 | True | True |
| con prior | media campionato prec | 1386 | 0.0952 | 3.0242 | 2.8434 | True | False |
| con prior | senza prior | 1386 | 0.1461 | 5.6209 | 4.9976 | True | False |

MDE contro il riferimento: delta 0.0108, MDE 0.0759, **delta/MDE 0.14** su 697 partite.

> Sotto 1 in valore assoluto il test **non conclude**: e' diverso da dire che l'effetto non c'e' (lezione di 6D, unita' di V3).

#### `modello prec` contro gli altri

_L'anno scorso applicato tale e quale, senza guardare una sola partita nuova. Era il **diagnostico** del blocco, non il candidato da adottare._

| soggetto | avversario | n | delta_loglik_per_riga | t_riga | t_cluster | vince_il_soggetto | riferimento |
|---|---|---|---|---|---|---|---|
| modello prec | due regimi | 1386 | 0.0000 |  |  | False | False |
| modello prec | con prior | 1386 | 0.0795 | 3.4818 | 3.3253 | True | False |
| modello prec | media squadra prec | 1386 | 0.0906 | 4.2508 | 4.3640 | True | True |
| modello prec | media campionato prec | 1386 | 0.1747 | 6.9195 | 6.3875 | True | False |
| modello prec | senza prior | 1386 | 0.2256 | 6.0822 | 5.4071 | True | False |

MDE: delta 0.0901, MDE 0.0579, **delta/MDE 1.56**.

Soglia di Sidak su 5 candidati dichiarati: |t| > 2.32.

### Controllo — righe gia' coperte dal within-season

| candidato | n | mae | bias | loglik_per_riga |
|---|---|---|---|---|
| con prior | 2016 | 3.6194 | 0.1098 | -2.9879 |
| senza prior | 2016 | 3.6527 | 0.1077 | -3.0037 |
| modello prec | 2016 | 3.6730 | -0.0759 | -3.0171 |
| media squadra prec | 2016 | 4.0336 | 0.3055 | -3.1718 |
| media campionato prec | 2016 | 4.1282 | 0.0319 | -3.2275 |
| due regimi | 2016 | 3.6194 | 0.1098 | -2.9879 |

#### `con prior` contro gli altri, sul controllo

| soggetto | avversario | n | delta_loglik_per_riga | t_riga | t_cluster | vince_il_soggetto | riferimento |
|---|---|---|---|---|---|---|---|
| con prior | due regimi | 2016 | 0.0000 |  |  | False | False |
| con prior | senza prior | 2016 | 0.0157 | 1.6772 | 1.6595 | True | False |
| con prior | modello prec | 2016 | 0.0291 | 2.0959 | 2.0212 | True | False |
| con prior | media squadra prec | 2016 | 0.1839 | 9.0470 | 8.8917 | True | True |
| con prior | media campionato prec | 2016 | 0.2395 | 9.9486 | 9.1523 | True | False |

### Dove i due regimi si scambiano

_Descrizione, non scelta: dice se la soglia gia' dichiarata dal repository cade dove i dati la metterebbero._

| team_match_idx | con prior | senza prior | modello prec | media squadra prec | media campionato prec | due regimi | n | migliore |
|---|---|---|---|---|---|---|---|---|
| 1 | -3.4322 | -4.0195 | -3.0128 | -3.0864 | -3.1708 | -3.0128 | 234 | modello prec |
| 2 | -3.1304 | -3.2307 | -3.0454 | -3.1350 | -3.2384 | -3.0454 | 288 | modello prec |
| 3 | -3.1471 | -3.2062 | -3.1112 | -3.1905 | -3.2977 | -3.1112 | 288 | modello prec |
| 4 | -3.0917 | -3.1322 | -3.1535 | -3.2723 | -3.3148 | -3.1535 | 288 | con prior |
| 5 | -3.1234 | -3.1493 | -3.1406 | -3.2291 | -3.3121 | -3.1406 | 288 | con prior |
| 6 | -3.0825 | -3.0879 | -3.1006 | -3.2250 | -3.3038 | -3.0825 | 288 | con prior |
| 7 | -2.9480 | -2.9599 | -3.0112 | -3.1721 | -3.2178 | -2.9480 | 288 | con prior |
| 8 | -3.0523 | -3.0706 | -3.0302 | -3.1830 | -3.1970 | -3.0523 | 288 | modello prec |
| 9 | -2.9973 | -3.0475 | -2.9931 | -3.1689 | -3.2607 | -2.9973 | 288 | modello prec |
| 10 | -3.0048 | -3.0035 | -3.0111 | -3.1491 | -3.1472 | -3.0048 | 288 | senza prior |
| 11 | -2.9071 | -2.9132 | -2.9812 | -3.1042 | -3.1744 | -2.9071 | 288 | con prior |
| 12 | -2.9236 | -2.9430 | -2.9924 | -3.2004 | -3.2915 | -2.9236 | 288 | con prior |

### Per campionato e transizione

| campionato | stagione | tarata | alpha_prior | sul_bordo | n | ll_con prior | ll_senza prior | ll_modello prec | ll_media squadra prec | ll_media campionato prec | delta_vs_media_squadra | t_cluster | delta_su_mde |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ENG-premier-league | 2022-2023 | False | 12.0000 | False | 98 | -2.9853 | -3.1090 | -2.9368 | -3.0853 | -3.2167 | 0.1000 | 0.8006 | 0.2858 |
| ENG-premier-league | 2023-2024 | True | 50.0000 | False | 98 | -3.0830 | -3.4728 | -3.0687 | -3.2305 | -3.3342 | 0.1475 | 1.2746 | 0.4549 |
| ENG-premier-league | 2024-2025 | True | 50.0000 | False | 98 | -3.2592 | -3.2298 | -3.2863 | -3.3000 | -3.3097 | 0.0408 | 0.3787 | 0.1352 |
| ENG-premier-league | 2025-2026 | True | 25.0000 | False | 98 | -3.0199 | -3.2084 | -3.0091 | -3.2191 | -3.1780 | 0.1992 | 1.8439 | 0.6582 |
| ESP-la-liga | 2022-2023 | False | 12.0000 | False | 98 | -2.8000 | -2.9399 | -2.9031 | -2.9219 | -3.1024 | 0.1219 | 1.2131 | 0.4330 |
| ESP-la-liga | 2023-2024 | True | 12.0000 | False | 96 | -2.9988 | -3.0279 | -2.8220 | -2.9071 | -3.0447 | -0.0917 | -1.0606 | -0.3786 |
| ESP-la-liga | 2024-2025 | True | 25.0000 | False | 96 | -3.1152 | -3.2167 | -3.1414 | -3.1587 | -3.3189 | 0.0435 | 0.5884 | 0.2100 |
| ESP-la-liga | 2025-2026 | True | 25.0000 | False | 96 | -3.1044 | -3.3001 | -3.1155 | -3.2355 | -3.4808 | 0.1311 | 1.5817 | 0.5646 |
| FRA-ligue-1 | 2022-2023 | False | 12.0000 | False | 98 | -3.2093 | -3.2991 | -3.0531 | -3.0320 | -3.1657 | -0.1772 | -1.7006 | -0.6070 |
| FRA-ligue-1 | 2023-2024 | True | 12.0000 | False | 88 | -3.3200 | -3.4738 | -3.2530 | -3.2924 | -3.4695 | -0.0276 | -0.3236 | -0.1155 |
| FRA-ligue-1 | 2024-2025 | True | 25.0000 | False | 88 | -3.2665 | -3.3089 | -3.0660 | -3.1572 | -3.2038 | -0.1093 | -0.8685 | -0.3100 |
| FRA-ligue-1 | 2025-2026 | True | 50.0000 | False | 88 | -3.3614 | -3.5258 | -3.1131 | -3.2232 | -3.3092 | -0.1381 | -1.3687 | -0.4885 |
| GER-bundesliga | 2022-2023 | False | 12.0000 | False | 88 | -3.5688 | -3.8865 | -3.1563 | -3.3083 | -3.5115 | -0.2604 | -1.4891 | -0.5315 |
| GER-bundesliga | 2023-2024 | True | 200.0000 | True | 88 | -3.4292 | -4.0168 | -3.1515 | -3.3433 | -3.4232 | -0.0859 | -0.6187 | -0.2208 |
| GER-bundesliga | 2024-2025 | True | 200.0000 | True | 88 | -3.5061 | -3.6451 | -3.3982 | -3.4343 | -3.4847 | -0.0718 | -0.6214 | -0.2218 |
| GER-bundesliga | 2025-2026 | True | 50.0000 | False | 88 | -3.0100 | -3.1115 | -2.9391 | -2.9600 | -3.0253 | -0.0500 | -0.6082 | -0.2171 |
| ITA-serie-a | 2022-2023 | False | 12.0000 | False | 92 | -2.8887 | -3.0345 | -2.9286 | -2.9845 | -3.1461 | 0.0958 | 1.1711 | 0.4180 |
| ITA-serie-a | 2023-2024 | True | 25.0000 | False | 92 | -3.0220 | -3.0932 | -2.9613 | -3.1866 | -3.2067 | 0.1645 | 1.9171 | 0.6843 |
| ITA-serie-a | 2024-2025 | True | 50.0000 | False | 92 | -3.1638 | -3.1824 | -3.1756 | -3.2149 | -3.2479 | 0.0512 | 0.4636 | 0.1655 |
| ITA-serie-a | 2025-2026 | True | 25.0000 | False | 92 | -3.0312 | -3.0801 | -2.9556 | -2.9454 | -3.0314 | -0.0858 | -0.9287 | -0.3315 |

### Segno del margine per campionato

| campionato | delta_vs_media_squadra |
|---|---|
| ENG-premier-league | 0.1292 |
| ESP-la-liga | 0.0276 |
| FRA-ligue-1 | -0.0917 |
| GER-bundesliga | -0.0692 |
| ITA-serie-a | 0.0433 |

## Bersaglio `sot`

**Il criterio scritto prima: NON adottato** — t = -2.82 (serve > 2) e 0/5 campionati positivi (ne servono 3)

### Poolato sulle transizioni tarate — righe di avvio

| candidato | n | mae | bias | loglik_per_riga |
|---|---|---|---|---|
| con prior | 1386 | 1.9637 | -0.1396 | -2.3360 |
| senza prior | 1386 | 2.0951 | -0.0748 | -2.4355 |
| modello prec | 1386 | 1.8638 | -0.0366 | -2.2235 |
| media squadra prec | 1386 | 1.9403 | 0.1149 | -2.2658 |
| media campionato prec | 1386 | 1.9853 | -0.0096 | -2.3123 |
| due regimi | 1386 | 1.8638 | -0.0366 | -2.2235 |

#### `con prior` contro gli altri

| soggetto | avversario | n | delta_loglik_per_riga | t_riga | t_cluster | vince_il_soggetto | riferimento |
|---|---|---|---|---|---|---|---|
| con prior | modello prec | 1386 | -0.1125 | -4.9933 | -4.7333 | False | False |
| con prior | due regimi | 1386 | -0.1125 | -4.9933 | -4.7333 | False | False |
| con prior | media squadra prec | 1386 | -0.0702 | -2.9689 | -2.8249 | False | True |
| con prior | media campionato prec | 1386 | -0.0237 | -0.9669 | -0.9130 | False | False |
| con prior | senza prior | 1386 | 0.0995 | 7.2589 | 6.6914 | True | False |

MDE contro il riferimento: delta -0.0695, MDE 0.0689, **delta/MDE -1.01** su 697 partite.

> Sotto 1 in valore assoluto il test **non conclude**: e' diverso da dire che l'effetto non c'e' (lezione di 6D, unita' di V3).

#### `modello prec` contro gli altri

_L'anno scorso applicato tale e quale, senza guardare una sola partita nuova. Era il **diagnostico** del blocco, non il candidato da adottare._

| soggetto | avversario | n | delta_loglik_per_riga | t_riga | t_cluster | vince_il_soggetto | riferimento |
|---|---|---|---|---|---|---|---|
| modello prec | due regimi | 1386 | 0.0000 |  |  | False | False |
| modello prec | media squadra prec | 1386 | 0.0423 | 4.3065 | 4.2488 | True | True |
| modello prec | media campionato prec | 1386 | 0.0888 | 7.2629 | 7.0023 | True | False |
| modello prec | con prior | 1386 | 0.1125 | 4.9933 | 4.7333 | True | False |
| modello prec | senza prior | 1386 | 0.2120 | 7.0580 | 6.2349 | True | False |

MDE: delta 0.0418, MDE 0.0276, **delta/MDE 1.52**.

Soglia di Sidak su 5 candidati dichiarati: |t| > 2.32.

### Controllo — righe gia' coperte dal within-season

| candidato | n | mae | bias | loglik_per_riga |
|---|---|---|---|---|
| con prior | 2016 | 1.7542 | 0.0671 | -2.1650 |
| senza prior | 2016 | 1.8086 | 0.0668 | -2.1941 |
| modello prec | 2016 | 1.7853 | 0.0437 | -2.1856 |
| media squadra prec | 2016 | 1.8849 | 0.2008 | -2.2404 |
| media campionato prec | 2016 | 1.9318 | 0.0683 | -2.2796 |
| due regimi | 2016 | 1.7542 | 0.0671 | -2.1650 |

#### `con prior` contro gli altri, sul controllo

| soggetto | avversario | n | delta_loglik_per_riga | t_riga | t_cluster | vince_il_soggetto | riferimento |
|---|---|---|---|---|---|---|---|
| con prior | due regimi | 2016 | 0.0000 |  |  | False | False |
| con prior | modello prec | 2016 | 0.0205 | 2.5480 | 2.5468 | True | False |
| con prior | senza prior | 2016 | 0.0290 | 4.9940 | 4.9693 | True | False |
| con prior | media squadra prec | 2016 | 0.0754 | 7.0295 | 6.9100 | True | True |
| con prior | media campionato prec | 2016 | 0.1145 | 8.6057 | 8.2765 | True | False |

### Dove i due regimi si scambiano

_Descrizione, non scelta: dice se la soglia gia' dichiarata dal repository cade dove i dati la metterebbero._

| team_match_idx | con prior | senza prior | modello prec | media squadra prec | media campionato prec | due regimi | n | migliore |
|---|---|---|---|---|---|---|---|---|
| 1 | -2.7601 | -3.0618 | -2.1596 | -2.1844 | -2.1865 | -2.1596 | 234 | modello prec |
| 2 | -2.2309 | -2.3300 | -2.1827 | -2.2484 | -2.3085 | -2.1827 | 288 | modello prec |
| 3 | -2.3000 | -2.3460 | -2.2862 | -2.3365 | -2.3603 | -2.2862 | 288 | modello prec |
| 4 | -2.1869 | -2.2262 | -2.1997 | -2.2215 | -2.2869 | -2.1997 | 288 | con prior |
| 5 | -2.2815 | -2.3308 | -2.2771 | -2.3229 | -2.3956 | -2.2771 | 288 | modello prec |
| 6 | -2.2396 | -2.2726 | -2.2497 | -2.2672 | -2.3202 | -2.2396 | 288 | con prior |
| 7 | -2.2073 | -2.2500 | -2.2222 | -2.2922 | -2.3306 | -2.2073 | 288 | con prior |
| 8 | -2.1034 | -2.1294 | -2.1224 | -2.1723 | -2.1947 | -2.1034 | 288 | con prior |
| 9 | -2.2245 | -2.2678 | -2.2631 | -2.3351 | -2.3891 | -2.2245 | 288 | con prior |
| 10 | -2.1420 | -2.1531 | -2.1586 | -2.2228 | -2.2398 | -2.1420 | 288 | con prior |
| 11 | -2.1070 | -2.1409 | -2.1526 | -2.2112 | -2.2626 | -2.1070 | 288 | con prior |
| 12 | -2.1315 | -2.1446 | -2.1302 | -2.1824 | -2.2199 | -2.1315 | 288 | modello prec |

### Per campionato e transizione

| campionato | stagione | tarata | alpha_prior | sul_bordo | n | ll_con prior | ll_senza prior | ll_modello prec | ll_media squadra prec | ll_media campionato prec | delta_vs_media_squadra | t_cluster | delta_su_mde |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ENG-premier-league | 2022-2023 | False | 12.0000 | False | 98 | -2.2140 | -2.3023 | -2.1312 | -2.1986 | -2.2402 | -0.0154 | -0.2241 | -0.0800 |
| ENG-premier-league | 2023-2024 | True | 12.0000 | False | 98 | -2.7959 | -3.0811 | -2.3860 | -2.4253 | -2.5352 | -0.3706 | -1.7471 | -0.6236 |
| ENG-premier-league | 2024-2025 | True | 25.0000 | False | 98 | -2.2178 | -2.2637 | -2.1663 | -2.1834 | -2.2274 | -0.0344 | -0.7208 | -0.2573 |
| ENG-premier-league | 2025-2026 | True | 25.0000 | False | 98 | -1.9932 | -2.0605 | -2.0216 | -2.1243 | -2.0815 | 0.1311 | 2.0208 | 0.7213 |
| ESP-la-liga | 2022-2023 | False | 12.0000 | False | 98 | -2.2299 | -2.3706 | -2.2406 | -2.1815 | -2.3675 | -0.0484 | -0.9289 | -0.3316 |
| ESP-la-liga | 2023-2024 | True | 12.0000 | False | 96 | -2.3565 | -2.4046 | -2.3112 | -2.3103 | -2.4060 | -0.0462 | -0.8703 | -0.3106 |
| ESP-la-liga | 2024-2025 | True | 25.0000 | False | 96 | -2.1867 | -2.2887 | -2.1823 | -2.2493 | -2.3329 | 0.0626 | 1.3785 | 0.4921 |
| ESP-la-liga | 2025-2026 | True | 12.0000 | False | 96 | -2.1839 | -2.2667 | -2.1298 | -2.1430 | -2.2393 | -0.0409 | -1.1349 | -0.4051 |
| FRA-ligue-1 | 2022-2023 | False | 12.0000 | False | 98 | -2.4547 | -2.5941 | -2.4484 | -2.4292 | -2.5485 | -0.0255 | -0.1918 | -0.0684 |
| FRA-ligue-1 | 2023-2024 | True | 12.0000 | False | 88 | -2.3271 | -2.3595 | -2.2538 | -2.2559 | -2.2968 | -0.0712 | -1.3670 | -0.4879 |
| FRA-ligue-1 | 2024-2025 | True | 12.0000 | False | 88 | -2.4716 | -2.5082 | -2.3374 | -2.3906 | -2.4209 | -0.0809 | -0.9515 | -0.3396 |
| FRA-ligue-1 | 2025-2026 | True | 25.0000 | False | 88 | -2.3023 | -2.3416 | -2.2114 | -2.3172 | -2.2943 | 0.0149 | 0.1598 | 0.0570 |
| GER-bundesliga | 2022-2023 | False | 12.0000 | False | 88 | -2.4433 | -2.7097 | -2.3473 | -2.3760 | -2.5343 | -0.0673 | -0.8718 | -0.3112 |
| GER-bundesliga | 2023-2024 | True | 25.0000 | False | 88 | -2.7433 | -3.0106 | -2.4311 | -2.5245 | -2.5795 | -0.2188 | -1.2627 | -0.4507 |
| GER-bundesliga | 2024-2025 | True | 25.0000 | False | 88 | -2.4526 | -2.5490 | -2.3233 | -2.3236 | -2.3576 | -0.1290 | -1.5210 | -0.5429 |
| GER-bundesliga | 2025-2026 | True | 25.0000 | False | 88 | -2.5202 | -2.8167 | -2.2374 | -2.2344 | -2.3685 | -0.2858 | -2.4738 | -0.8830 |
| ITA-serie-a | 2022-2023 | False | 12.0000 | False | 92 | -2.1801 | -2.2765 | -2.1716 | -2.2060 | -2.2968 | 0.0259 | 0.6624 | 0.2364 |
| ITA-serie-a | 2023-2024 | True | 25.0000 | False | 92 | -2.1338 | -2.1748 | -2.1036 | -2.1690 | -2.1954 | 0.0352 | 0.7686 | 0.2743 |
| ITA-serie-a | 2024-2025 | True | 12.0000 | False | 92 | -2.2116 | -2.2444 | -2.1586 | -2.1864 | -2.2241 | -0.0252 | -0.4624 | -0.1651 |
| ITA-serie-a | 2025-2026 | True | 25.0000 | False | 92 | -2.1902 | -2.2128 | -2.1261 | -2.1774 | -2.1480 | -0.0128 | -0.2283 | -0.0815 |

### Segno del margine per campionato

| campionato | delta_vs_media_squadra |
|---|---|
| ENG-premier-league | -0.0913 |
| ESP-la-liga | -0.0081 |
| FRA-ligue-1 | -0.0458 |
| GER-bundesliga | -0.2112 |
| ITA-serie-a | -0.0009 |
