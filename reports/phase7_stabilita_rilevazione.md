# Fase 7 — stabilita' del criterio di rilevazione fra stagioni

L'acquisizione WhoScored 2021-2026 si e' chiusa con un limite dichiarato: *"nessuna verifica di stabilita' del criterio di rilevazione fra stagioni. Schema identico non implica annotazione identica: da misurare prima di stimare `rho` su cinque stagioni."* Questo blocco e' quella misura. **Non e' stato scaricato niente**: gira sui 1.889 CSV gia' su disco.

## Esito in breve

1. **La definizione di tiro in porta e' stabile su tutte e cinque le stagioni, e non e' un giudizio: e' un'identita' esatta.** La regola del repository e il flag Opta nativo `shotOnTarget` coincidono **evento per evento**, con **zero** discordanze in ciascuna delle cinque stagioni. La Fase 0 lo aveva verificato sul solo 2025-26 (3066 = 3066); ora vale su 47.530 tentativi.
2. **I rapporti fra le quattro categorie non si muovono.** La quota di tentativi che finisce in porta sta fra 0.3250 e 0.3408; contro il numero unico (0.3303) nessuna stagione supera 2.3 deviazioni standard binomiali, e con la sovradispersione osservata (`phi` = 1.101) il gradino di stagione non batte il baseline costante (F = 1.75, p = 0.135).
3. **Il livello invece si muove, e si muove come si muove il calcio.** I tentativi per squadra-partita scendono da 13.03 a 12.12 e i tiri in porta da 4.441 a 4.033: **-9.2%** in cinque stagioni. Ma la **ripartizione** fra le categorie resta ferma, ed e' la firma di "si tira di meno", non di "si conta diversamente".
4. **Gli ingressi dell'xG interno, invece, non sono stabili — ed e' il risultato che il blocco non si aspettava.** `shotCounter` passa dal 3.4% al 7.7% dei tentativi, `shotOpenPlay` dal 69.3% al 61.8%. Sono le colonne che `sot/xg.py` usa come predittori. **La definizione di SoT e' salva, quella del contesto del tiro no.**
5. **Un qualifier sparisce, e sparisce per pagina intera.** `StandingSave` sta sull'82% dei tentativi nelle prime quattro stagioni e sul 2.4% nel 2025-26, con **11 partite su 380** che lo conservano e le altre a zero esatto. Non e' un travaso graduale: e' una proprieta' della singola pagina della fonte. Non tocca niente di cio' che il modello usa, ma dice che **il livello dei qualifier non e' garantito stabile** e che le colonne da esso derivate vanno verificate una per una prima dell'uso, non assunte.
6. **Il risultato negativo ha la sua potenza dichiarata.** Un gradino al confine di stagione sulla quota di tiri in porta verrebbe visto se valesse almeno **0.20 tiri in porta per squadra-partita** (80% di potenza, 5%). Sotto quella soglia questo blocco non lo distingue dal rumore. Che la macchina abbia sensibilita' non e' un'assunzione: **la stessa macchina, sulle stesse unita', trova la deriva di `shotCounter` con F = 215**.

> **Per la Fase 7B/7D**: `rho` puo' essere stimato sulle cinque stagioni **sui tiri in porta**, ma sugli **eccessi relativi** (rapporto alla media di campionato della stagione), non sugli scarti assoluti — la media di campionato si e' mossa del 10.1% per ragioni di gioco, e uno scarto assoluto di +1 tiro non significa la stessa cosa nel 2021-22 e nel 2025-26. Quello che **non** si puo' fare senza altri controlli e' stimare l'xG interno su piu' stagioni insieme.

---

## 1. Su cosa gira

| stagione   |   file |   eventi |   colonne_min |   colonne_max |
|:-----------|-------:|---------:|--------------:|--------------:|
| 2021-2022  |    374 |   576928 |           258 |           259 |
| 2022-2023  |    375 |   574779 |           258 |           259 |
| 2023-2024  |    380 |   568200 |           258 |           259 |
| 2024-2025  |    380 |   556652 |           258 |           259 |
| 2025-2026  |    380 |   562672 |           258 |           259 |

Le 12 partite che WhoScored non ha (`manifest.json`, `assenti_alla_fonte`) restano fuori, e la loro assenza **non e' casuale rispetto alla squadra** (6 all'Atalanta). Per questo blocco il rischio e' contenuto: tutte le grandezze qui sono rapporti o medie su decine di migliaia di tiri, e sei partite di una squadra su 1.889 non spostano una quota. Sarebbe un problema serio per una stima **per squadra**, che qui non si fa.

Le unita' sono **squadra-partita**, non tiri: i tiri della stessa squadra nella stessa partita non sono indipendenti. Sono 3.778 righe, ricostruite dalle due squadre di ogni file e non dai tiri, perche' 2 squadre-partita nel campione hanno **zero tentativi** (Pisa-Cremonese del 2026-05-10 e una del 2021-22) e ricostruendo dai tiri sparirebbero dal denominatore.

### Le quattro categorie

Sono una **partizione** dei tentativi, verificata riga per riga: `in porta + respinto da un difensore + palo + fuori = tentativi`, sempre. E' cio' che le rende diagnostiche: un confine che si sposta si vede come travaso fra due categorie, a totale fermo.

---

## 2. I livelli: qui qualcosa si muove

| stagione   |   partite |   squadra_partita |   tentativi |   tentativi_per_sp |   in_porta_per_sp |   bloccato_per_sp |   palo_per_sp |   fuori_per_sp |
|:-----------|----------:|------------------:|------------:|-------------------:|------------------:|------------------:|--------------:|---------------:|
| 2021-2022  |       374 |               748 |        9748 |            13.0321 |            4.4412 |            3.4586 |        0.2527 |         4.8797 |
| 2022-2023  |       375 |               750 |        9509 |            12.6787 |            4.1227 |            3.4107 |        0.232  |         4.9133 |
| 2023-2024  |       380 |               760 |        9701 |            12.7645 |            4.1487 |            3.4434 |        0.2645 |         4.9079 |
| 2024-2025  |       380 |               760 |        9213 |            12.1224 |            4.0329 |            3.3053 |        0.2447 |         4.5395 |
| 2025-2026  |       380 |               760 |        9359 |            12.3145 |            4.0342 |            3.3658 |        0.2355 |         4.6789 |

Contro il baseline stupido — **una media sola per tutte e cinque le stagioni** — con l'errore standard campionario vero:

**Tentativi per squadra-partita**

| stagione   |   squadra_partita |   media |   baseline_unico |   scarto |   sd_media |       z |
|:-----------|------------------:|--------:|-----------------:|---------:|-----------:|--------:|
| 2021-2022  |               748 | 13.0321 |          12.5807 |   0.4514 |     0.1907 |  2.3673 |
| 2022-2023  |               750 | 12.6787 |          12.5807 |   0.0979 |     0.1904 |  0.5143 |
| 2023-2024  |               760 | 12.7645 |          12.5807 |   0.1837 |     0.1892 |  0.9714 |
| 2024-2025  |               760 | 12.1224 |          12.5807 |  -0.4584 |     0.1892 | -2.4232 |
| 2025-2026  |               760 | 12.3145 |          12.5807 |  -0.2663 |     0.1892 | -1.4076 |

**Tiri in porta per squadra-partita**

| stagione   |   squadra_partita |   media |   baseline_unico |   scarto |   sd_media |       z |
|:-----------|------------------:|--------:|-----------------:|---------:|-----------:|--------:|
| 2021-2022  |               748 |  4.4412 |           4.1551 |   0.2861 |     0.0859 |  3.3294 |
| 2022-2023  |               750 |  4.1227 |           4.1551 |  -0.0324 |     0.0858 | -0.3781 |
| 2023-2024  |               760 |  4.1487 |           4.1551 |  -0.0064 |     0.0852 | -0.0754 |
| 2024-2025  |               760 |  4.0329 |           4.1551 |  -0.1222 |     0.0852 | -1.4338 |
| 2025-2026  |               760 |  4.0342 |           4.1551 |  -0.1209 |     0.0852 | -1.4183 |

Il 2021-22 sta 3.33 errori standard sopra la media unica e il 2024-25 1.43 sotto. **Questo movimento e' vero**, ed e' il primo motivo per cui il blocco non poteva fermarsi ai livelli: un livello che si muove non dice da solo se a muoversi e' il calcio o il righello.

Effetto minimo rilevabile sui livelli, per confronto:

| confine   |   n_prima |   n_dopo |   sd_differenza |    mde |   mde_relativo |
|:----------|----------:|---------:|----------------:|-------:|---------------:|
| 2022-2023 |       748 |     3030 |          0.0959 | 0.2688 |         0.0647 |
| 2023-2024 |      1498 |     2280 |          0.0782 | 0.219  |         0.0527 |
| 2024-2025 |      2258 |     1520 |          0.078  | 0.2184 |         0.0526 |
| 2025-2026 |      3018 |      760 |          0.0954 | 0.2672 |         0.0643 |

Il 2025-26 e' la stagione su cui poggiano tutte le Fasi 0-6, e il suo livello (4.0342) riproduce esattamente il valore di riferimento della Fase 0 (4.034 contro 4.03 fornito): la catena di lettura di questo blocco e' la stessa del resto del repository, e su una stagione lo si vede.

### Casa e trasferta

| stagione   |   trasferta |   casa |   vantaggio |
|:-----------|------------:|-------:|------------:|
| 2021-2022  |      4.1791 | 4.7032 |      1.1254 |
| 2022-2023  |      3.8347 | 4.4107 |      1.1502 |
| 2023-2024  |      3.6711 | 4.6263 |      1.2602 |
| 2024-2025  |      3.7632 | 4.3026 |      1.1433 |
| 2025-2026  |      3.6368 | 4.4316 |      1.2185 |

Il 2021-22 e' la prima stagione col pubblico tornato (`config.SEASONS_STORICHE` lo dichiara): il vantaggio del campo di quella stagione non e' confrontabile con le successive, ed e' un limite gia' registrato, non una scoperta di questo blocco.

---

## 3. I rapporti: qui non si muove niente

**E' la misura che discrimina.** Un cambio di criterio sposta la ripartizione fra categorie lasciando il totale quasi fermo; una variazione di gioco sposta il totale lasciando la ripartizione ferma. Quello che si osserva e' il secondo caso.

| stagione   |   tentativi |   q_in_porta |   q_bloccato |   q_palo |   q_fuori |
|:-----------|------------:|-------------:|-------------:|---------:|----------:|
| 2021-2022  |        9748 |       0.3408 |       0.2654 |   0.0194 |    0.3744 |
| 2022-2023  |        9509 |       0.3252 |       0.269  |   0.0183 |    0.3875 |
| 2023-2024  |        9701 |       0.325  |       0.2698 |   0.0207 |    0.3845 |
| 2024-2025  |        9213 |       0.3327 |       0.2727 |   0.0202 |    0.3745 |
| 2025-2026  |        9359 |       0.3276 |       0.2733 |   0.0191 |    0.38   |

**in_porta** — contro il numero unico:

| stagione   |    n |   quota |   baseline_unico |   scarto |   sd_binomiale |   z_binomiale |
|:-----------|-----:|--------:|-----------------:|---------:|---------------:|--------------:|
| 2021-2022  | 9748 | 0.34079 |          0.33028 |  0.01051 |        0.00476 |       2.20682 |
| 2022-2023  | 9509 | 0.32517 |          0.33028 | -0.00511 |        0.00482 |      -1.0595  |
| 2023-2024  | 9701 | 0.32502 |          0.33028 | -0.00526 |        0.00478 |      -1.10105 |
| 2024-2025  | 9213 | 0.33268 |          0.33028 |  0.00241 |        0.0049  |       0.49113 |
| 2025-2026  | 9359 | 0.3276  |          0.33028 | -0.00268 |        0.00486 |      -0.55055 |

**bloccato** — contro il numero unico:

| stagione   |    n |   quota |   baseline_unico |   scarto |   sd_binomiale |   z_binomiale |
|:-----------|-----:|--------:|-----------------:|---------:|---------------:|--------------:|
| 2021-2022  | 9748 | 0.26539 |          0.26998 | -0.00459 |        0.0045  |      -1.02059 |
| 2022-2023  | 9509 | 0.26901 |          0.26998 | -0.00097 |        0.00455 |      -0.21274 |
| 2023-2024  | 9701 | 0.26977 |          0.26998 | -0.00021 |        0.00451 |      -0.04678 |
| 2024-2025  | 9213 | 0.27266 |          0.26998 |  0.00268 |        0.00463 |       0.57972 |
| 2025-2026  | 9359 | 0.27332 |          0.26998 |  0.00334 |        0.00459 |       0.72847 |

**palo** — contro il numero unico:

| stagione   |    n |   quota |   baseline_unico |   scarto |   sd_binomiale |   z_binomiale |
|:-----------|-----:|--------:|-----------------:|---------:|---------------:|--------------:|
| 2021-2022  | 9748 | 0.01939 |          0.01955 | -0.00016 |        0.0014  |      -0.11194 |
| 2022-2023  | 9509 | 0.0183  |          0.01955 | -0.00125 |        0.00142 |      -0.87848 |
| 2023-2024  | 9701 | 0.02072 |          0.01955 |  0.00117 |        0.00141 |       0.83527 |
| 2024-2025  | 9213 | 0.02019 |          0.01955 |  0.00064 |        0.00144 |       0.44605 |
| 2025-2026  | 9359 | 0.01913 |          0.01955 | -0.00042 |        0.00143 |      -0.29322 |

**fuori** — contro il numero unico:

| stagione   |    n |   quota |   baseline_unico |   scarto |   sd_binomiale |   z_binomiale |
|:-----------|-----:|--------:|-----------------:|---------:|---------------:|--------------:|
| 2021-2022  | 9748 | 0.37444 |           0.3802 | -0.00577 |        0.00492 |      -1.17278 |
| 2022-2023  | 9509 | 0.38753 |           0.3802 |  0.00733 |        0.00498 |       1.47157 |
| 2023-2024  | 9701 | 0.3845  |           0.3802 |  0.00429 |        0.00493 |       0.87133 |
| 2024-2025  | 9213 | 0.37447 |           0.3802 | -0.00573 |        0.00506 |      -1.1332  |
| 2025-2026  | 9359 | 0.37996 |           0.3802 | -0.00025 |        0.00502 |      -0.0492  |

Nessuno `z` binomiale arriva a 2.5, e lo `z` binomiale e' gia' la versione **ottimistica**: ignora che i tiri della stessa partita sono correlati. Con la sovradispersione dentro, i valori si dividono per circa `sqrt(phi)`.

---

## 4. Gradino o deriva

Quattro modelli sulla stessa quantita', tutti sulle stesse unita' squadra-partita, confrontati in **quasi-verosimiglianza** con `phi` stimato dal modello piu' ricco (cella stagione x mese):

| modello | cosa afferma |
|---|---|
| M0 costante | il baseline stupido: un tasso solo, sempre |
| M1 gradino di stagione | il criterio cambia **solo** ai confini di stagione |
| M2 deriva continua | il tasso si muove piano, nel logit, lungo il tempo |
| M3 mese di calendario | e' stagionalita' calcistica, uguale ogni anno |

M1 contro M2 e' il confronto che decide e **non e' annidato**: si legge sulla QAIC, non su un test. M3 esiste perche' senza di lui un effetto di calendario che si ripete ogni anno — inverno, fatica, campi pesanti — verrebbe letto come gradino.

### in_porta

| modello                |   parametri |   devianza |    QAIC |   dQAIC |   phi |
|:-----------------------|------------:|-----------:|--------:|--------:|------:|
| M0 costante            |           1 |    4405.84 | 4002.85 |   0     | 1.101 |
| M1 gradino di stagione |           5 |    4398.11 | 4003.83 |   0.981 | 1.101 |
| M2 deriva continua     |           2 |    4404.67 | 4003.79 |   0.943 | 1.101 |
| M3 mese di calendario  |          11 |    4393.05 | 4011.23 |   8.386 | 1.101 |

| contro M0              |   gdl |   riduzione_devianza |      F |      p |    phi |
|:-----------------------|------:|---------------------:|-------:|-------:|-------:|
| M1 gradino di stagione |     4 |               7.73   | 1.7549 | 0.1351 | 1.1012 |
| M2 deriva continua     |     1 |               1.1642 | 1.0572 | 0.3039 | 1.1012 |
| M3 mese di calendario  |    10 |              12.7891 | 1.1614 | 0.3122 | 1.1012 |

### bloccato

| modello                |   parametri |   devianza |    QAIC |   dQAIC |   phi |
|:-----------------------|------------:|-----------:|--------:|--------:|------:|
| M0 costante            |           1 |    4311.77 | 4183.18 |   0     | 1.031 |
| M1 gradino di stagione |           5 |    4309.81 | 4189.28 |   6.102 | 1.031 |
| M2 deriva continua     |           2 |    4309.78 | 4183.25 |   0.07  | 1.031 |
| M3 mese di calendario  |          11 |    4293.98 | 4185.93 |   2.749 | 1.031 |

| contro M0              |   gdl |   riduzione_devianza |      F |      p |    phi |
|:-----------------------|------:|---------------------:|-------:|-------:|-------:|
| M1 gradino di stagione |     4 |               1.9575 | 0.4746 | 0.7545 | 1.0312 |
| M2 deriva continua     |     1 |               1.9905 | 1.9302 | 0.1648 | 1.0312 |
| M3 mese di calendario  |    10 |              17.7899 | 1.7251 | 0.0694 | 1.0312 |

### palo

| modello                |   parametri |   devianza |    QAIC |   dQAIC |   phi |
|:-----------------------|------------:|-----------:|--------:|--------:|------:|
| M0 costante            |           1 |    2878.9  | 2779.55 |   0     | 1.036 |
| M1 gradino di stagione |           5 |    2877.14 | 2785.85 |   6.294 | 1.036 |
| M2 deriva continua     |           2 |    2878.9  | 2781.55 |   2     | 1.036 |
| M3 mese di calendario  |          11 |    2869.99 | 2790.96 |  11.403 | 1.036 |

| contro M0              |   gdl |   riduzione_devianza |      F |      p |    phi |
|:-----------------------|------:|---------------------:|-------:|-------:|-------:|
| M1 gradino di stagione |     4 |               1.7687 | 0.4266 | 0.7895 | 1.0365 |
| M2 deriva continua     |     1 |               0      | 0      | 0.9953 | 1.0365 |
| M3 mese di calendario  |    10 |               8.9109 | 0.8597 | 0.5708 | 1.0365 |

### fuori

| modello                |   parametri |   devianza |    QAIC |   dQAIC |   phi |
|:-----------------------|------------:|-----------:|--------:|--------:|------:|
| M0 costante            |           1 |    4166.4  | 4038.71 |   0     | 1.032 |
| M1 gradino di stagione |           5 |    4160.82 | 4041.3  |   2.588 | 1.032 |
| M2 deriva continua     |           2 |    4166.34 | 4040.65 |   1.941 | 1.032 |
| M3 mese di calendario  |          11 |    4154.45 | 4047.12 |   8.417 | 1.032 |

| contro M0              |   gdl |   riduzione_devianza |      F |      p |    phi |
|:-----------------------|------:|---------------------:|-------:|-------:|-------:|
| M1 gradino di stagione |     4 |               5.5856 | 1.3529 | 0.2478 | 1.0321 |
| M2 deriva continua     |     1 |               0.0608 | 0.0589 | 0.8082 | 1.0321 |
| M3 mese di calendario  |    10 |              11.9556 | 1.1583 | 0.3143 | 1.0321 |

**Su tutte e quattro le categorie nessun modello batte il baseline costante.** La lettura non e' l'ordinamento nudo — un parametro in piu' arriva primo per caso circa una volta su sei — ma la distanza in QAIC, la cui soglia convenzionale e' 2. Il caso meno tranquillo e' `in_porta`, dove M1 e M2 stanno a meno di un punto dal baseline: non e' preferenza per il gradino, e' indifferenza.

---

## 5. Dove cadrebbe il gradino, se ci fosse

Un gradino solo, provato in **tutti** i confini di mese. Il punto non e' se esista un confine che migliora l'adattamento — ne esiste sempre uno, e' il massimo di 50 numeri positivi — ma **dove cade** e **quanto vale rispetto al massimo che il caso produce**.

I sei confini migliori per `in_porta`:

| prima_di   |   riduzione_devianza | confine_di_stagione   |
|:-----------|---------------------:|:----------------------|
| 2022-08    |                6.103 | True                  |
| 2022-09    |                4.344 | False                 |
| 2022-10    |                4.206 | False                 |
| 2022-03    |                3.846 | False                 |
| 2022-04    |                3.492 | False                 |
| 2022-11    |                3.099 | False                 |

Il massimo cade a **2022-08**, cioe' esattamente al passaggio 2021-22 -> 2022-23. Ma la sua altezza va confrontata con la distribuzione del massimo **sotto l'ipotesi che non ci sia nessun gradino**, simulata con i denominatori veri e la sovradispersione osservata (2.000 repliche beta-binomiali):

| categoria   | ipotesi                  |   candidati | confine_migliore   |   riduzione_osservata |   mediana_nulla |   q95_nulla |   p_max |   quota_nulla_su_confine_stagione |
|:------------|:-------------------------|------------:|:-------------------|----------------------:|----------------:|------------:|--------:|----------------------------------:|
| in_porta    | tutti i confini di mese  |          50 | 2022-08            |                6.1027 |          4.1673 |     10.1712 |  0.2349 |                            0.0405 |
| in_porta    | solo confini di stagione |           4 | 2022-08            |                6.1027 |          1.8542 |      6.5708 |  0.065  |                            1      |
| bloccato    | tutti i confini di mese  |          50 | 2026-05            |                4.3992 |          3.6877 |      9.1975 |  0.3923 |                            0.0515 |
| bloccato    | solo confini di stagione |           4 | 2024-08            |                1.4045 |          1.6503 |      6.4336 |  0.5647 |                            1      |
| palo        | tutti i confini di mese  |          50 | 2025-04            |                2.0794 |          3.8417 |      9.1574 |  0.8591 |                            0.0455 |
| palo        | solo confini di stagione |           4 | 2023-08            |                0.8198 |          1.6557 |      6.321  |  0.7741 |                            1      |
| fuori       | tutti i confini di mese  |          50 | 2021-09            |                2.592  |          3.8062 |      8.881  |  0.7461 |                            0.046  |
| fuori       | solo confini di stagione |           4 | 2022-08            |                1.7328 |          1.6427 |      6.0146 |  0.4778 |                            1      |

Due letture, e vanno tenute insieme:

- **cercando ovunque** il massimo osservato su `in_porta` non e' raro (p = 0.23): il caso produce spesso di meglio;
- **cercando solo dove l'ipotesi lo prevede** — i quattro confini di stagione, dichiarati in anticipo — il test guadagna potenza e `in_porta` arriva a **p = 0.065**, che e' al limite. Non e' corretto per aver provato quattro categorie: con Bonferroni vale 0.26, e non passa.

Sotto l'ipotesi nulla il massimo cade su un confine di stagione solo nel 5% delle repliche: che il migliore osservato ci cada e' un indizio, non una prova, e riguarda **il passaggio 2021-22 -> 2022-23** — cioe' l'uscita dalla stagione che il progetto gia' dichiara non confrontabile per il ritorno del pubblico. La spiegazione piu' economica non e' un cambio di criterio.

---

## 6. La potenza del risultato negativo

Un risultato negativo senza potenza dichiarata non e' un risultato — e' la lezione della Fase 6D, e qui vale identica. Effetto minimo rilevabile di un gradino sulla quota di tiri in porta, a ciascun confine di stagione, con l'80% di potenza al 5%:

| confine   |   n_prima |   n_dopo |   sd_differenza |   mde_quota |   mde_relativo |   mde_in_tiri_per_sp |
|:----------|----------:|---------:|----------------:|------------:|---------------:|---------------------:|
| 2022-2023 |      9748 |    37782 |         0.00561 |     0.01571 |        0.04756 |              0.19772 |
| 2023-2024 |     19257 |    28273 |         0.00461 |     0.01292 |        0.03912 |              0.16262 |
| 2024-2025 |     28958 |    18572 |         0.00464 |     0.013   |        0.03936 |              0.16362 |
| 2025-2026 |     38171 |     9359 |         0.00569 |     0.01595 |        0.04829 |              0.20076 |

**Un gradino di annotazione piu' piccolo di ~0.20 tiri in porta per squadra-partita passerebbe inosservato.** E' il 4-5% del livello: non e' una sensibilita' eccezionale, ed e' il limite principale di questo blocco. Va confrontato con cio' che deve sopportare: l'eccesso del Como sulla media di campionato vale 1.07 tiri, quindi un gradino non rilevabile arriva al 19% dell'eccesso di una squadra di vertice.

**Il controllo positivo.** Che la macchina abbia sensibilita' non e' un'assunzione: la stessa procedura, sulle stesse 3.776 unita', vede senza sforzo la deriva di `shotCounter` (paragrafo 8). Se non ci fosse sensibilita' non vedrebbe nemmeno quella.

---

## 7. L'identita' con il flag Opta nativo

**E' il risultato piu' forte del blocco, perche' non passa da nessun modello.** La regola del repository (`isShot AND ((SavedShot AND NOT shotBlocked) OR (Goal AND NOT isOwnGoal))`) viene confrontata evento per evento con il flag Opta `shotOnTarget` presente nei dati:

| stagione   |   tentativi |   regola |   flag_opta |   solo_regola |   solo_flag | identiche   |
|:-----------|------------:|---------:|------------:|--------------:|------------:|:------------|
| 2021-2022  |        9748 |     3322 |        3322 |             0 |           0 | True        |
| 2022-2023  |        9509 |     3092 |        3092 |             0 |           0 | True        |
| 2023-2024  |        9701 |     3153 |        3153 |             0 |           0 | True        |
| 2024-2025  |        9213 |     3065 |        3065 |             0 |           0 | True        |
| 2025-2026  |        9359 |     3066 |        3066 |             0 |           0 | True        |

Zero discordanze in entrambe le direzioni, in tutte e cinque le stagioni. Qualunque cosa sia cambiata nel feed, **non e' cambiato il rapporto fra la nostra definizione e quella della fonte**.

---

## 8. Gli ingressi dell'xG interno: qui il criterio si muove

Le colonne booleane che `sot/xg.py` usa come predittori sono derivate da `satisfiedEventsTypes`, cioe' dallo stesso strato di annotazione dei qualifier. Quota sui tentativi, per stagione:

| flag             |   2021-2022 |   2022-2023 |   2023-2024 |   2024-2025 |   2025-2026 |
|:-----------------|------------:|------------:|------------:|------------:|------------:|
| bigChanceMissed  |      0.0811 |      0.0798 |      0.0897 |      0.1012 |      0.1032 |
| bigChanceScored  |      0.0643 |      0.0567 |      0.0591 |      0.0609 |      0.0618 |
| shotCounter      |      0.0335 |      0.0395 |      0.0437 |      0.0706 |      0.077  |
| shotDirectCorner |      0.0002 |      0      |      0      |      0.0001 |      0      |
| shotOpenPlay     |      0.6934 |      0.6865 |      0.6698 |      0.644  |      0.618  |
| shotSetPiece     |      0.2588 |      0.2628 |      0.273  |      0.2742 |      0.2936 |

Lo stesso in deviazioni standard binomiali dal numero unico:

| flag             |   2021-2022 |   2022-2023 |   2023-2024 |   2024-2025 |   2025-2026 |
|:-----------------|------------:|------------:|------------:|------------:|------------:|
| bigChanceMissed  |       -3.33 |       -3.74 |       -0.4  |        3.44 |        4.16 |
| bigChanceScored  |        1.56 |       -1.58 |       -0.61 |        0.14 |        0.49 |
| shotCounter      |       -8.41 |       -5.69 |       -3.91 |        7.74 |       10.61 |
| shotDirectCorner |        1.77 |       -0.77 |       -0.78 |        0.55 |       -0.77 |
| shotOpenPlay     |        6.39 |        4.89 |        1.47 |       -3.82 |       -9.16 |
| shotSetPiece     |       -3    |       -2.09 |        0.14 |        0.4  |        4.63 |

`shotDirectCorner` e' praticamente sempre falsa (poche unita' in tutta la storia) e non entra nei confronti che seguono.

### shotOpenPlay

| modello                |   parametri |   devianza |    QAIC |   dQAIC |   phi |
|:-----------------------|------------:|-----------:|--------:|--------:|------:|
| M0 costante            |           1 |    5314.37 | 4277.37 |  135.48 |  1.24 |
| M1 gradino di stagione |           5 |    5149.79 | 4152.97 |   11.08 |  1.24 |
| M2 deriva continua     |           2 |    5143.47 | 4141.89 |    0    |  1.24 |
| M3 mese di calendario  |          11 |    5282.6  | 4271.82 |  129.93 |  1.24 |

| contro M0              |   gdl |   riduzione_devianza |        F |      p |   phi |
|:-----------------------|------:|---------------------:|---------:|-------:|------:|
| M1 gradino di stagione |     4 |             164.581  |  33.101  | 0      | 1.243 |
| M2 deriva continua     |     1 |             170.892  | 137.481  | 0      | 1.243 |
| M3 mese di calendario  |    10 |              31.7638 |   2.5554 | 0.0045 | 1.243 |

### shotCounter

| modello                |   parametri |   devianza |    QAIC |   dQAIC |   phi |
|:-----------------------|------------:|-----------:|--------:|--------:|------:|
| M0 costante            |           1 |    5069.55 | 3816.66 |  212.55 |  1.33 |
| M1 gradino di stagione |           5 |    4783.93 | 3609.74 |    5.62 |  1.33 |
| M2 deriva continua     |           2 |    4784.43 | 3604.11 |    0    |  1.33 |
| M3 mese di calendario  |          11 |    5036.98 | 3812.15 |  208.03 |  1.33 |

| contro M0              |   gdl |   riduzione_devianza |        F |      p |   phi |
|:-----------------------|------:|---------------------:|---------:|-------:|------:|
| M1 gradino di stagione |     4 |             285.624  |  53.7304 | 0      | 1.329 |
| M2 deriva continua     |     1 |             285.123  | 214.545  | 0      | 1.329 |
| M3 mese di calendario  |    10 |              32.5731 |   2.451  | 0.0065 | 1.329 |

### shotSetPiece

| modello                |   parametri |   devianza |    QAIC |   dQAIC |   phi |
|:-----------------------|------------:|-----------:|--------:|--------:|------:|
| M0 costante            |           1 |    5299.95 | 4240.62 |   26.07 |  1.25 |
| M1 gradino di stagione |           5 |    5265.24 | 4220.86 |    6.31 |  1.25 |
| M2 deriva continua     |           2 |    5264.85 | 4214.55 |    0    |  1.25 |
| M3 mese di calendario  |          11 |    5274.12 | 4239.96 |   25.41 |  1.25 |

| contro M0              |   gdl |   riduzione_devianza |       F |      p |    phi |
|:-----------------------|------:|---------------------:|--------:|-------:|-------:|
| M1 gradino di stagione |     4 |              34.7121 |  6.9402 | 0      | 1.2504 |
| M2 deriva continua     |     1 |              35.0992 | 28.0705 | 0      | 1.2504 |
| M3 mese di calendario  |    10 |              25.829  |  2.0657 | 0.0239 | 1.2504 |

### bigChanceMissed

| modello                |   parametri |   devianza |    QAIC |   dQAIC |   phi |
|:-----------------------|------------:|-----------:|--------:|--------:|------:|
| M0 costante            |           1 |    4853.97 | 4286.41 |   40.07 |  1.13 |
| M1 gradino di stagione |           5 |    4799.62 | 4246.44 |    0.1  |  1.13 |
| M2 deriva continua     |           2 |    4806.31 | 4246.34 |    0    |  1.13 |
| M3 mese di calendario  |          11 |    4848.42 | 4301.51 |   55.17 |  1.13 |

| contro M0              |   gdl |   riduzione_devianza |       F |      p |    phi |
|:-----------------------|------:|---------------------:|--------:|-------:|-------:|
| M1 gradino di stagione |     4 |              54.3495 | 11.993  | 0      | 1.1329 |
| M2 deriva continua     |     1 |              47.6634 | 42.0706 | 0      | 1.1329 |
| M3 mese di calendario  |    10 |               5.551  |  0.49   | 0.8976 | 1.1329 |

### bigChanceScored

| modello                |   parametri |   devianza |    QAIC |   dQAIC |   phi |
|:-----------------------|------------:|-----------:|--------:|--------:|------:|
| M0 costante            |           1 |    4311.07 | 3963.07 |    0    |  1.09 |
| M1 gradino di stagione |           5 |    4305.49 | 3965.94 |    2.87 |  1.09 |
| M2 deriva continua     |           2 |    4311    | 3965.01 |    1.94 |  1.09 |
| M3 mese di calendario  |          11 |    4306.43 | 3978.81 |   15.74 |  1.09 |

| contro M0              |   gdl |   riduzione_devianza |      F |      p |    phi |
|:-----------------------|------:|---------------------:|-------:|-------:|-------:|
| M1 gradino di stagione |     4 |               5.5781 | 1.2813 | 0.2749 | 1.0884 |
| M2 deriva continua     |     1 |               0.063  | 0.0579 | 0.8099 | 1.0884 |
| M3 mese di calendario  |    10 |               4.6393 | 0.4263 | 0.9346 | 1.0884 |

Massimo gradino ai soli confini di stagione, contro il nullo simulato:

| categoria       | confine_migliore   |   riduzione_osservata |   mediana_nulla |   q95_nulla |   p_max |
|:----------------|:-------------------|----------------------:|----------------:|------------:|--------:|
| shotOpenPlay    | 2024-08            |               138.009 |           2.07  |       7.478 |   0     |
| shotCounter     | 2024-08            |               269.06  |           2.285 |       7.957 |   0     |
| shotSetPiece    | 2025-08            |                26.338 |           2.082 |       7.765 |   0     |
| bigChanceMissed | 2024-08            |                46.979 |           1.905 |       6.814 |   0     |
| bigChanceScored | 2022-08            |                 3.021 |           1.738 |       6.357 |   0.276 |

Effetto minimo rilevabile, per capire quanto sono grandi questi movimenti rispetto a cio' che il blocco riesce a vedere:

| flag            | confine   |   mde_relativo |
|:----------------|:----------|---------------:|
| shotOpenPlay    | 2022-2023 |         0.0253 |
| shotOpenPlay    | 2023-2024 |         0.0208 |
| shotOpenPlay    | 2024-2025 |         0.0209 |
| shotOpenPlay    | 2025-2026 |         0.0257 |
| shotCounter     | 2022-2023 |         0.1558 |
| shotCounter     | 2023-2024 |         0.1281 |
| shotCounter     | 2024-2025 |         0.1289 |
| shotCounter     | 2025-2026 |         0.1582 |
| shotSetPiece    | 2022-2023 |         0.0582 |
| shotSetPiece    | 2023-2024 |         0.0478 |
| shotSetPiece    | 2024-2025 |         0.0481 |
| shotSetPiece    | 2025-2026 |         0.0591 |
| bigChanceMissed | 2022-2023 |         0.1072 |
| bigChanceMissed | 2023-2024 |         0.0881 |
| bigChanceMissed | 2024-2025 |         0.0887 |
| bigChanceMissed | 2025-2026 |         0.1088 |
| bigChanceScored | 2022-2023 |         0.1308 |
| bigChanceScored | 2023-2024 |         0.1076 |
| bigChanceScored | 2024-2025 |         0.1082 |
| bigChanceScored | 2025-2026 |         0.1328 |

Come leggerli:

- **si muovono 4 flag su 5**: `shotOpenPlay`, `shotCounter`, `shotSetPiece`, `bigChanceMissed`. Sull'unico che resta fermo (`bigChanceScored`) vince il baseline costante, ed e' il controllo interno che non e' la procedura a vedere gradini ovunque;
- **la deriva vince sul gradino** su 4 dei 4 che si muovono: M2 batte M1 sulla QAIC pur avendo tre parametri in meno, quindi il movimento e' **graduale** e distribuito su cinque stagioni, non un salto a una data precisa. E' la firma che questo modulo attribuisce al calcio, non all'annotazione;
- **ma e' un movimento enorme.** `shotCounter` piu' che raddoppia (3.4% -> 7.7%), contro un effetto minimo rilevabile del 13% relativo. `shotOpenPlay` scende di 7.5 punti. Che sia gioco davvero cambiato o criterio scivolato, **l'effetto sul modello e' lo stesso**: un xG stimato su cinque stagioni insieme impara un predittore che non significa la stessa cosa alle due estremita' del campione;
- **il singolo confine peggiore cade a 2024-08 per 3 flag su 4**, e li' il gradino non e' rumore. Chi volesse usare gli eventi di piu' stagioni ha due strade: stimare l'xG **per stagione** (costoso in dati, ma non mescola definizioni) oppure tenere la stagione come effetto esplicito nel modello. Non c'e' una terza strada che consista nel non accorgersene.

---

## 9. I qualifier, uno per uno

Presenza per tiro, per stagione, su 58 qualifier distinti. Si conta la **presenza sul tiro**, non le occorrenze: cosi' la grandezza e' una proporzione con denominatore noto e la variabilita' attesa sotto stabilita' e' calcolabile.

Quelli che compaiono, spariscono, o saltano di piu' di 6 deviazioni standard fra stagioni adiacenti:

| qualifier             | da        | a         |   quota_da |   quota_a |   delta |   sd_attesa |         z | compare_o_sparisce   |
|:----------------------|:----------|:----------|-----------:|----------:|--------:|------------:|----------:|:---------------------|
| StandingSave          | 2024-2025 | 2025-2026 |     0.8167 |    0.0228 | -0.7939 |      0.0072 | -109.728  | False                |
| IndividualPlay        | 2023-2024 | 2024-2025 |     0.4659 |    0.3711 | -0.0948 |      0.0072 |  -13.2081 | False                |
| FastBreak             | 2023-2024 | 2024-2025 |     0.0437 |    0.0706 |  0.0268 |      0.0034 |    7.974  | False                |
| ThrowinSetPiece       | 2023-2024 | 2024-2025 |     0.0098 |    0.0213 |  0.0115 |      0.0018 |    6.4125 | False                |
| DirectCorner          | 2021-2022 | 2022-2023 |     0.0002 |    0      | -0.0002 |      0.0001 |   -1.3968 | True                 |
| DirectCorner          | 2023-2024 | 2024-2025 |     0      |    0.0001 |  0.0001 |      0.0001 |    1.0262 | True                 |
| IntentionalGoalAssist | 2024-2025 | 2025-2026 |     0.0001 |    0      | -0.0001 |      0.0001 |   -1.0079 | True                 |
| DirectCorner          | 2024-2025 | 2025-2026 |     0.0001 |    0      | -0.0001 |      0.0001 |   -1.0079 | True                 |
| IntentionalGoalAssist | 2022-2023 | 2023-2024 |     0      |    0.0001 |  0.0001 |      0.0001 |    0.9901 | True                 |
| IntentionalGoalAssist | 2021-2022 | 2022-2023 |     0.0001 |    0      | -0.0001 |      0.0001 |   -0.9877 | True                 |

La soglia e' alta di proposito: con novemila tiri per stagione uno `z` di 3 lo produce qualunque fluttuazione reale di stile di gioco, e la domanda qui non e' se il calcio sia cambiato.

### `StandingSave`: il caso che vale la pena guardare

| stagione   |   partite |   con_qualifier |   quota_media |
|:-----------|----------:|----------------:|--------------:|
| 2021-2022  |       374 |             373 |        0.816  |
| 2022-2023  |       375 |             375 |        0.8105 |
| 2023-2024  |       380 |             380 |        0.8047 |
| 2024-2025  |       380 |             379 |        0.8183 |
| 2025-2026  |       380 |              11 |        0.0243 |

**Non e' un travaso graduale: e' una proprieta' della singola pagina.** Nelle prime quattro stagioni il qualifier sta su piu' della meta' dei tiri in **ogni** partita (1.507 partite su 1.509); nel 2025-26 lo conservano 11 partite su 380 e le altre lo hanno a **zero esatto**, non a un valore basso. Il profilo per mese di partita attorno al passaggio (nelle stagioni precedenti ogni mese sta fra 0.785 e 0.854):

| mese    |   quota_media |   partite |
|:--------|--------------:|----------:|
| 2024-08 |        0.8018 |        26 |
| 2024-09 |        0.8105 |        34 |
| 2024-10 |        0.8255 |        39 |
| 2024-11 |        0.7971 |        34 |
| 2024-12 |        0.8429 |        45 |
| 2025-01 |        0.8157 |        41 |
| 2025-02 |        0.7954 |        42 |
| 2025-03 |        0.8344 |        39 |
| 2025-04 |        0.8282 |        40 |
| 2025-05 |        0.8196 |        40 |
| 2025-08 |        0.0947 |        20 |
| 2025-09 |        0.052  |        30 |
| 2025-10 |        0.02   |        40 |
| 2025-11 |        0.1095 |        39 |
| 2025-12 |        0.0187 |        37 |
| 2026-01 |        0      |        58 |
| 2026-02 |        0      |        40 |
| 2026-03 |        0      |        36 |
| 2026-04 |        0      |        40 |
| 2026-05 |        0      |        40 |

Due spiegazioni sono compatibili con questo, e **i dati in casa non le separano**:

1. **l'archivio della fonte**: le pagine della stagione 2025-26 sono annotate diversamente da quelle delle stagioni chiuse;
2. **il momento del prelievo**: le pagine vengono arricchite dopo qualche tempo, e la 2025-26 e' stata scaricata piu' vicino alle partite.

La seconda **non e' esclusa dai tempi di download** — i file delle cinque stagioni hanno `mtime` fra il 29 luglio e il 1 agosto 2026, ma quello del 2025-26 potrebbe essere stato riscritto dallo spostamento della 7A. **L'esperimento che le separa e' un solo GET** su una partita 2025-26 gia' in casa, confrontando il qualifier: non e' stato fatto perche' questo blocco non scarica. Va messo in conto al primo blocco che tocca la rete.

**Non tocca niente di cio' che il modello usa** — `StandingSave` non compare in nessuna colonna di `io_events.BOOL_COLS` ne' in `shots.py`. Conta come avvertimento: il livello dei qualifier **non e' garantito stabile**, e ogni colonna da esso derivata va verificata prima dell'uso invece che assunta. Le tre di cui sopra lo erano gia'.

### Le colonne dei CSV

Presenza per stagione, frazione dei file. Su 259 colonne una sola non e' presente ovunque:

| colonna   |   2021-2022 |   2022-2023 |   2023-2024 |   2024-2025 |   2025-2026 | assente_in_una_stagione_intera   | sporadica_ovunque   |
|:----------|------------:|------------:|------------:|------------:|------------:|:---------------------------------|:--------------------|
| isOwnGoal |      0.0909 |      0.0827 |      0.0605 |      0.0974 |      0.0579 | False                            | True                |

Ed e' **la trappola gia' nota**: pandas emette `isOwnGoal` solo se in quella partita c'e' stato un autogol. La quota per stagione (6-10%) e' la frequenza degli autogol, non un cambio di schema. Nessuna colonna compare o sparisce fra stagioni.

### Igiene dell'annotazione

| stagione   |   eventi_di_tiro |   x_mancante |   x_sotto_50 |   situation_nulla |   tipo_tiro_senza_isShot |   isShot_senza_tipo_tiro |   x_medio |
|:-----------|-----------------:|-------------:|-------------:|------------------:|-------------------------:|-------------------------:|----------:|
| 2021-2022  |             9784 |            0 |      0.0045  |           0.05468 |                        0 |                        0 |   85.0713 |
| 2022-2023  |             9540 |            0 |      0.00461 |           0.05786 |                        0 |                        0 |   84.8893 |
| 2023-2024  |             9725 |            0 |      0.00391 |           0.06694 |                        0 |                        0 |   84.9741 |
| 2024-2025  |             9250 |            0 |      0.00541 |           0.10281 |                        0 |                        0 |   85.0478 |
| 2025-2026  |             9381 |            0 |      0.00416 |           0.12344 |                        0 |                        0 |   85.1901 |

`x_medio` e `x_sotto_50` confermano su tutte e cinque le stagioni l'orientamento delle coordinate accertato nella Fase 0 (si attacca sempre verso x = 100). `situation_nulla` **raddoppia** fra la prima e l'ultima stagione: e' un campo che il progetto non usa — i rigori si identificano da `penaltyScored | penaltyMissed` proprio perche' `situation` e' inutilizzabile — ma e' un altro segnale che lo strato descrittivo della fonte si e' mosso mentre quello strutturale no.

---

## 10. Cosa ne segue, operativamente

| domanda | risposta di questo blocco |
|---|---|
| Si puo' stimare `rho` sui tiri in porta delle cinque stagioni? | **Si'**, sulla definizione: e' identica al flag della fonte in tutte e cinque, e le quote fra categorie non si muovono. |
| Sugli scarti assoluti dalla media di campionato? | **No.** La media di campionato si e' mossa del 10.1% per ragioni di gioco: +1 tiro di eccesso nel 2021-22 e nel 2025-26 non sono la stessa cosa. Usare eccessi **relativi**. |
| Si puo' stimare l'xG interno su piu' stagioni insieme? | **No, non senza un termine di stagione**: `shotOpenPlay` e `shotCounter` si muovono di molto piu' del rilevabile, e il singolo salto piu' grande cade fra 2023-24 e 2024-25. |
| Si possono usare i qualifier come predittori multi-stagione? | **Uno alla volta e solo dopo averlo verificato.** `StandingSave` mostra che un qualifier puo' sparire per intero senza che schema, conteggio colonne o numero di eventi se ne accorgano. |
| Il 2021-22 e' confrontabile con le altre? | Sul criterio si'. Sul **vantaggio del campo** no, ed era gia' dichiarato: e' la prima stagione col pubblico tornato. |

---

## Limiti di questo blocco

- **La sensibilita' e' quella che e'**: un gradino sotto ~0.20 tiri in porta per squadra-partita non verrebbe visto. Il blocco esclude un cambio di criterio **grande**, non un cambio di criterio.
- **Non separa "il criterio e' cambiato" da "il calcio e' cambiato bruscamente a fine giugno".** Nessun dato interno alla fonte puo' farlo: la firma delle due ipotesi e' la stessa. Il blocco dice quale sia la spiegazione piu' economica, non quale sia vera.
- **Una fonte sola.** Tutto qui dentro e' WhoScored contro WhoScored. Il confronto con una definizione **esterna** e' un'altra cosa ed e' il blocco 7C.
- **Non e' una verifica per squadra.** Le 12 partite mancanti sono concentrate su una squadra (6 all'Atalanta): irrilevante per le quote di campionato calcolate qui, non irrilevante per una stima per squadra.
- **`StandingSave` resta senza spiegazione accertata**, e l'esperimento che la darebbe richiede una richiesta di rete che questo blocco non fa.
- **Niente di questo blocco entra nel modello.** Nessuno script delle Fasi 1-6 importa `recording_stability`, e i numeri pubblicati sono stati rieseguiti dopo: invariati.