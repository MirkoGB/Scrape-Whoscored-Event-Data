# Fase 15 / Blocco T1 - il totale di partita

Generato il 2026-09-04 da `scripts/run_fase15_totale.py`.
Non tocca la rete, non scrive niente sotto `data/`.

## 0. Che cosa fa questo blocco

Chiude la domanda aperta n. 3 di V1 e n. 3 di V4, che erano la stessa domanda:

> il totale di partita e' la linea di mercato piu' comune e `lam_subiti` e' gia'
> nella cache, ma la correlazione negativa misurata da V0 dice che **non e' la
> somma di due indipendenti**: serve la congiunta, che sui tentativi non e'
> misurata.

La risposta e' che **la congiunta non serve**:

```
lambda_tot = lambda_casa + lambda_trasferta      esatto, qualunque dipendenza
y_tot      ~ NB2(lambda_tot, r_tot)              r_tot STIMATA sui totali
```

`E[X+Y] = E[X]+E[Y]` non richiede ipotesi: la media del totale e' esatta. Cio'
che la dipendenza rompe e' la **dispersione**, e `r_tot` stimata sui totali
osservati la assorbe per misura invece che per assunzione.

## 1. Il perimetro: la riga e' la PARTITA

| stagione | partite | validabili | nessun_lato | un_lato_solo | quota_validabile |
|---|---:|---:|---:|---:|---:|
| 2021-2022 | 344 | 323 | 19 | 2 | 0.939 |
| 2022-2023 | 345 | 325 | 20 | 0 | 0.942 |
| 2023-2024 | 350 | 330 | 20 | 0 | 0.943 |
| 2024-2025 | 350 | 330 | 20 | 0 | 0.943 |
| 2025-2026 | 350 | 330 | 20 | 0 | 0.943 |
| TOTALE | 1739 | 1638 | 99 | 2 | 0.942 |

**1638 partite validabili**, che e' esattamente il numero che R0 conto' sui gol
sullo stesso universo - il controllo interno piu' forte disponibile. E le **2
partite con un lato solo stanno entrambe nel 2021-2022**, come R0 aveva
documentato: `eligible` e' una proprieta' della squadra, non della partita, e
cade dove WhoScored ha perso partite.

| affermazione | unita | n | blocco |
|---|---|---:|---|
| MAE e calibrazione sul totale | partita | 1638 | T1 |
| Over/Under sul totale, per linea | partita | 1638 | T1 |
| lo stesso, per squadra-partita | squadra-partita | 3276 | V1 |
| il segno del margine per stagione | stagione | 5 | T1 |

> Le righe si dimezzano rispetto a V1 e **non e' una perdita di dati**: e' un
> cambio di unita'. Ne segue che il `t` per cluster di partita diventa
> **degenere** - una riga *e'* una partita - e coincide col `t` per riga per
> costruzione. Si riporta lo stesso, in coppia, invece di farlo dedurre.

## 2. La dipendenza fra i due lati, misurata su questo perimetro

| stagione | partite | corr | sd_totale_osservata | sd_se_indipendenti | rapporto_sd |
|---|---:|---:|---:|---:|---:|
| 2021-2022 | 323 | -0.369 | 6.532 | 8.217 | 0.795 |
| 2022-2023 | 325 | -0.331 | 5.662 | 6.916 | 0.819 |
| 2023-2024 | 330 | -0.285 | 5.564 | 6.557 | 0.849 |
| 2024-2025 | 330 | -0.342 | 5.578 | 6.851 | 0.814 |
| 2025-2026 | 330 | -0.397 | 5.682 | 7.280 | 0.780 |

La correlazione e' **negativa in tutte e cinque le stagioni** (il possesso e' a
somma costante: chi domina tira molto e lascia tirare poco). Sul perimetro
validabile la sd osservata del totale vale **5.848** contro i
**7.194** che due lati indipendenti darebbero: **18.7%
in meno**.

### `r_tot` non si eredita, ed e' falsificato

| | |
|---|---:|
| `r` per lato | 20.00 |
| **`r` del totale** | **83.97** |
| rapporto | **4.20** |
| IC95 bootstrap (1000 repliche sulle partite) | [3.40, 5.61] |
| l'IC contiene 1? | **no** |

E' la stessa forma con cui `precisione.rapporto_dispersioni()` aveva falsificato
l'ereditarieta' fra `r_shots` e `r_sot`. Qui l'IC **non contiene 1** e sta tutto
sopra: il totale e' molto meno disperso di quanto `r` per lato implicherebbe, che
e' esattamente il segno della covarianza negativa.

## 3. L'alternativa scartata, calcolata e messa accanto

Convoluzione di due NB2 **indipendenti** per lato, con la stessa `r`
walk-forward, contro la NB2 diretta sul totale:

| linea | tasso_base | p_nb2_diretta | p_indipendenza | errore_diretta | errore_indipendenza | brier_diretta | brier_indipendenza | diretta_piu_vicina |
|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 20.5 | 0.780 | 0.776 | 0.746 | -0.0041 | -0.0334 | 0.1670 | 0.1681 | si |
| 22.5 | 0.655 | 0.657 | 0.634 | 0.0019 | -0.0207 | 0.2186 | 0.2186 | si |
| 24.5 | 0.520 | 0.526 | 0.515 | 0.0057 | -0.0050 | 0.2413 | 0.2405 | no |
| 26.5 | 0.373 | 0.397 | 0.399 | 0.0237 | 0.0265 | 0.2262 | 0.2255 | si |
| 28.5 | 0.261 | 0.282 | 0.296 | 0.0206 | 0.0347 | 0.1887 | 0.1887 | si |

**L'indipendenza ingrassa entrambe le code**, che e' il segno previsto prima di
guardare: sotto la linea piu' bassa sbaglia di -0,033 e sopra la piu' alta di
+0,035, contro -0,004 e +0,021 della diretta.

> **Due avvertenze che il confronto impone.** (1) Sulla linea centrale
> l'indipendenza e' leggermente **piu' vicina** (-0,005 contro +0,006): il
> vantaggio della diretta e' sulle **code**, che e' dove le due ipotesi
> differiscono, e va detto invece di riportare cinque vittorie su cinque. (2) Il
> **Brier non distingue le due**: le differenze sono in quarta cifra. Cio' che si
> guadagna e' calibrazione della coda, non capacita' di ordinare le partite.

## 4. Contro i baseline (vincolo 6)

| modello | n | mae | rmse | bias | corr | sharpness | calib_slope | calib_se | calib_z_vs_1 | loglik_poisson | loglik_nb2 | brier | brier_base | ece | base_rate |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Poisson ridge att/dif/casa (somma dei due lati) | 1638 | 4.5157 | 5.7129 | 0.1738 | 0.2390 | 2.0128 | 0.7029 | 0.0622 | -4.78 | -5191.2 | -5164.2 | 0.2413 | 0.2504 | 0.0297 | 0.5404 |
| media squadra + campo | 1638 | 5.0637 | 6.3661 | 0.2280 | 0.0941 | 3.1192 | 0.1796 | 0.0400 | -20.53 | -5442.6 | -5356.5 | 0.2741 | 0.2504 | 0.1284 | 0.5404 |
| media squadra | 1638 | 5.0637 | 6.3661 | 0.2280 | 0.0941 | 3.1192 | 0.1796 | 0.0400 | -20.53 | -5442.6 | -5356.5 | 0.2741 | 0.2504 | 0.1284 | 0.5404 |
| media casa/trasferta | 1638 | 4.6257 | 5.8338 | 0.2172 | 0.0770 | 0.5289 | 0.8650 | 0.2360 | -0.57 | -5237.1 | -5199.5 | 0.2498 | 0.2504 | 0.0156 | 0.5404 |
| media campionato | 1638 | 4.6257 | 5.8338 | 0.2172 | 0.0770 | 0.5289 | 0.8650 | 0.2360 | -0.57 | -5237.1 | -5199.5 | 0.2498 | 0.2504 | 0.0156 | 0.5404 |

| baseline | mae_baseline | mae_modello | delta_mae | t_per_riga | t_per_cluster | cluster_degenere |
|---|---:|---:|---:|---:|---:|---|
| media squadra + campo | 5.0637 | 4.5157 | 0.5480 | 8.333 | 8.333 | si |
| media squadra | 5.0637 | 4.5157 | 0.5480 | 8.333 | 8.333 | si |
| media casa/trasferta | 4.6257 | 4.5157 | 0.1100 | 2.491 | 2.491 | si |
| media campionato | 4.6257 | 4.5157 | 0.1100 | 2.491 | 2.491 | si |

**Il modello vince, e con margine**: 0.548 di MAE su
`media squadra + campo` con t = 8.33.

> **I quattro baseline sono in realta' DUE, e va detto.** Dopo la rotazione
> `media squadra + campo` e' **identica** a `media squadra` sul totale (a 7e-15),
> e `media casa/trasferta` e' identica a `media campionato`. Il motivo e'
> aritmetico e non un difetto: il termine di campo aggiunge alla squadra di casa
> quello che toglie a quella di trasferta, quindi **si cancella nella somma**.
> Per lato le quattro colonne differiscono eccome (fino a 1,83 tiri). Il vincolo
> 6 e' rispettato, ma con due concorrenti distinti, non quattro.

| stagione | n | media_osservata | mae | mae_relativo | bias | corr | delta_su_baseline | t | vince |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 2021-2022 | 323 | 25.978 | 4.9016 | 0.1887 | -0.0582 | 0.3063 | 0.7725 | 4.512 | si |
| 2022-2023 | 325 | 25.194 | 4.4161 | 0.1753 | 0.3210 | 0.2308 | 0.5379 | 3.754 | si |
| 2023-2024 | 330 | 25.603 | 4.2512 | 0.1660 | -0.3382 | 0.2300 | 0.3940 | 3.123 | si |
| 2024-2025 | 330 | 24.021 | 4.5083 | 0.1877 | 0.7271 | 0.1403 | 0.4607 | 3.065 | si |
| 2025-2026 | 330 | 24.539 | 4.5081 | 0.1837 | 0.2147 | 0.1571 | 0.5793 | 4.090 | si |

## 5. Brier per linea, su entrambi i bersagli

Totale dei **tiri**:

| linea | tasso_base | dentro_regola | brier_modello | brier_baseline | brier_tasso_base | vince_su_baseline | vince_su_tasso_base |
|---:|---:|---|---:|---:|---:|---|---|
| 20.5 | 0.7796 | si | 0.1670 | 0.1832 | 0.1728 | si | si |
| 22.5 | 0.6551 | si | 0.2186 | 0.2451 | 0.2275 | si | si |
| 24.5 | 0.5201 | si | 0.2413 | 0.2741 | 0.2504 | si | si |
| 26.5 | 0.3730 | si | 0.2262 | 0.2570 | 0.2354 | si | si |
| 28.5 | 0.2613 | si | 0.1887 | 0.2138 | 0.1945 | si | si |

Totale dei **tiri in porta**:

| linea | tasso_base | dentro_regola | brier_modello | brier_baseline | brier_tasso_base | vince_su_baseline | vince_su_tasso_base |
|---:|---:|---|---:|---:|---:|---|---|
| 6.5 | 0.7051 | si | 0.2078 | 0.2166 | 0.2091 | si | si |
| 7.5 | 0.5830 | si | 0.2398 | 0.2483 | 0.2443 | si | si |
| 8.5 | 0.4505 | si | 0.2442 | 0.2541 | 0.2484 | si | si |
| 9.5 | 0.3223 | si | 0.2147 | 0.2298 | 0.2191 | si | si |

Tutte le linee stanno dentro `tentativi.BASE_RATE_AMMESSO`, applicato
meccanicamente e non a occhio, e il modello batte **sia** il baseline migliore
**sia** il tasso base su ognuna.

## 6. La forma della predittiva

PIT randomizzato: chi2 = 9.18 su 9 gdl,
**p = 0.421**. `r_tot` mediana walk-forward 83.5.

| livello | copertura | ampiezza_media |
|---:|---:|---:|
| 0.5 | 0.567 | 8.73 |
| 0.8 | 0.831 | 15.69 |
| 0.95 | 0.958 | 23.47 |

La copertura e' **sopra** il nominale, com'e' strutturale sui conteggi: e' la
stessa firma conservativa gia' misurata in Fase 4 e in V1, non un difetto nuovo.

## 7. Il risultato che non era previsto: il totale e' SOTTO-CALIBRATO

Per **lato** il modello e' calibrato a 1,008 (z = +0,33), cioe' il numero di V1
riprodotto. Sul **totale** la pendenza crolla:

| bersaglio | pendenza grezza | z | pendenza ricalibrata | z |
|---|---:|---:|---:|---:|
| tiri | 0.6334 | -4.82 | 0.8120 | -1.91 |
| tiri in porta | 0.4796 | -4.87 | 0.6436 | -2.44 |

**Le due cose non si contraddicono, e il meccanismo e' misurato**: sommando, la
parte di segnale che i due lati hanno in comune si cancella, e sopravvive
proporzionalmente piu' rumore. Il numero che lo dice e' che **il modello crede i
due lati molto piu' anti-correlati di quanto siano**:

| stagione | partite | corr_lambda | corr_osservata | sd_lam_totale | sd_y_totale | il_modello_anticorrela_di_piu |
|---|---:|---:|---:|---:|---:|---|
| 2021-2022 | 323 | -0.6400 | -0.3694 | 2.518 | 6.532 | si |
| 2022-2023 | 325 | -0.6035 | -0.3309 | 1.944 | 5.662 | si |
| 2023-2024 | 330 | -0.4750 | -0.2851 | 1.662 | 5.564 | si |
| 2024-2025 | 330 | -0.6690 | -0.3419 | 1.794 | 5.578 | si |
| 2025-2026 | 330 | -0.7486 | -0.3970 | 1.801 | 5.682 | si |

Sui tiri in porta il divario e' anche piu' largo - nel 2023-2024 il modello
crede -0,40 dove l'osservato e' **+0,007**, cioe' nessuna dipendenza affatto:

| stagione | partite | corr_lambda | corr_osservata | sd_lam_totale | sd_y_totale | il_modello_anticorrela_di_piu |
|---|---:|---:|---:|---:|---:|---|
| 2021-2022 | 323 | -0.5817 | -0.1865 | 0.843 | 3.295 | si |
| 2022-2023 | 325 | -0.6889 | -0.2155 | 0.691 | 2.871 | si |
| 2023-2024 | 330 | -0.3983 | 0.0066 | 0.765 | 3.149 | si |
| 2024-2025 | 330 | -0.5577 | -0.1745 | 0.785 | 2.882 | si |
| 2025-2026 | 330 | -0.6917 | -0.2651 | 0.702 | 2.804 | si |

### Il verdetto sulla correzione, applicato meccanicamente

Criterio scritto **prima** di misurare (`totale.CRITERIO_ADOZIONE`):

> si adotta se, walk-forward: (1) |pendenza - 1| < 2 errori standard, (2) il MAE non peggiora oltre l'errore standard della differenza appaiata, (3) il segno regge in almeno 4 stagioni su 5.

| | tiri | tiri in porta |
|---|---|---|
| (1) pendenza entro 2 e.s. | si | **no** |
| (2) il MAE non peggiora | si | si |
| (3) segno concorde | si (4/4) | si (4/4) |
| **adottata** | **SI** | **NO** |

**Il verdetto e' diviso, e non e' stato aggiustato per farlo tornare uguale.**
Sui tiri la correzione si adotta - ma z passa a -1.91,
cioe' **appena dentro** la soglia, e va letto cosi'. Sui tiri in porta cade il
solo criterio (1): la pendenza resta a 0.64 con
z = -2.44, fuori da 2 errori standard.

> Il criterio diceva "4 stagioni su 5": le stagioni ricalibrabili sono **4**,
> perche' la piu' vecchia non ha un passato e resta marcata come non
> ricalibrata - lo stesso trattamento della 2021-2022 in R2-bis. Il conteggio e'
> quindi 4 su 4, e la soglia e' stata letta come "tutte quelle disponibili"
> invece di essere abbassata.

## 7-bis. Trasferisce? Lo stesso blocco sui cinque campionati

Un fit per campionato, **mai poolati** (regola di E1, riscritta da R0 su G2).
E' la domanda che la Fase 13 pose ai gol, applicata qui.

| campionato | bersaglio | partite | media_totale | corr_lati | r_lato | r_totale | pendenza_totale | z_vs_1 | rapporto_r |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| ENG-premier-league | tiri | 1645 | 25.919 | -0.413 | 19.48 | 90.88 | 0.630 | -6.79 | 4.66 |
| ENG-premier-league | tiri in porta | 1645 | 9.050 | -0.222 | 28.66 | 164.83 | 0.483 | -7.01 | 5.75 |
| ESP-la-liga | tiri | 1644 | 24.319 | -0.296 | 20.17 | 108.49 | 0.871 | -2.37 | 5.38 |
| ESP-la-liga | tiri in porta | 1644 | 8.367 | -0.106 | 30.68 | 70.45 | 0.642 | -5.39 | 2.30 |
| FRA-ligue-1 | tiri | 1433 | 24.672 | -0.302 | 20.69 | 91.18 | 0.746 | -3.73 | 4.41 |
| FRA-ligue-1 | tiri in porta | 1433 | 8.854 | -0.121 | 27.69 | 70.53 | 0.646 | -4.82 | 2.55 |
| GER-bundesliga | tiri | 1303 | 26.217 | -0.296 | 20.77 | 82.54 | 0.726 | -3.96 | 3.97 |
| GER-bundesliga | tiri in porta | 1303 | 9.312 | -0.197 | 33.09 | 190.60 | 0.622 | -4.25 | 5.76 |
| ITA-serie-a | tiri | 1638 | 25.063 | -0.342 | 20.00 | 83.97 | 0.703 | -4.78 | 4.20 |
| ITA-serie-a | tiri in porta | 1638 | 8.297 | -0.166 | 31.39 | 111.88 | 0.621 | -4.24 | 3.56 |

**Le tre firme del blocco reggono in tutte e dieci le righe**, e nessuna e'
un'idiosincrasia italiana:

- la correlazione fra i due lati e' **negativa ovunque** (da -0,11 a -0,41);
- **`r_tot` e' fra 2,3 e 5,8 volte `r` per lato** ovunque, cioe' il totale e'
  sempre molto meno disperso di quanto l'indipendenza implicherebbe;
- la pendenza del totale sta **sotto 1 ovunque**, con z da -2,37 a -7,01: la
  sotto-calibrazione non e' un accidente della Serie A.

> **Ne segue una conseguenza operativa per la pagina**: `r_tot` va presa **da
> quel campionato**, mai da un altro. Fra Bundesliga e Liga sui tiri in porta
> vale 190,6 contro 70,5, cioe' un fattore 2,7 - un `r_tot` preso in prestito
> sbaglierebbe le code in modo grossolano.

## 8. Che cosa T1 consegna

- `lambda_totale = lambda_casa + lambda_trasferta`, **esatto**, per qualunque
  coppia che il modello sappia prevedere;
- `r_tot` **stimata sui totali** e walk-forward, con la prova che non si eredita;
- le linee del totale, dichiarate prima e dentro la regola dei tassi base;
- **il limite piu' importante**: sul totale il lambda e' sotto-calibrato, sui
  tiri in porta lo resta anche dopo la correzione. Va scritto **accanto** ai
  numeri della pagina, non in fondo (vincolo 5).

## 9. Domande aperte

1. **Perche' il modello anti-correli i due lati piu' del vero** e' misurato ma
   non spiegato. Il sospetto e' che attacco e difesa della stessa partita
   condividano i coefficienti stimati sulle stesse righe, quindi l'errore di
   stima entri con segno opposto nei due lati; separarlo vuole un disegno
   apposito, non una rilettura di questo.
2. **La correzione e' una sola trasformazione monotona sul lambda**: sistema il
   sintomo e non sa da dove venga. E' la lezione di R2-bis, e vale qui identica -
   che funzioni non conferma nessuna spiegazione.
3. **`r_tot` e' assunta costante fra squadre e stagioni**, come `r` in V1.
4. **Senza prezzi di mercato reali** nessuna valutazione di scommessa e'
   possibile (vincolo 3), e questo blocco non ne apre la strada.
