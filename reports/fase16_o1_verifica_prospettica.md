# Fase 16 / Blocco O1 — la verifica prospettica delle prime due giornate

_Generato da `scripts/run_fase16_o1.py` — 2026-09-04 08:14_

**La prima verifica del progetto in cui la previsione e' stata scritta prima e
l'esito letto dopo.** Tutto il resto — il walk-forward di V1, il prior di A2 su
venti transizioni concluse, la trasferibilita' di F13 — e' within-season o
retrospettivo. Qui no, e non perche' si sia simulato qualcosa: **l'esclusione
era gia' avvenuta**.

---

## 1. Il registro, e perche' l'anteriorita' non chiede di fidarsi di un orologio

Le previsioni stanno su disco dal **2026-08-30**; il primo CSV di evento
della 2026-2027 e' arrivato **3.9
giorni dopo** il piu' stretto dei cinque.

| campionato | righe | byte | previsioni_scritte | primo_evento_stagione | anteriore | giorni_di_anticipo |
|---|---:|---:|---|---|---|---:|
| ITA-serie-a | 760 | 238 729 | 2026-08-30 13:47:48.493523598 | 2026-09-03 16:33:41.194449186 | si | 4.12 |
| ENG-premier-league | 760 | 247 616 | 2026-08-30 13:47:48.463821888 | 2026-09-03 12:33:57.435889482 | si | 3.95 |
| ESP-la-liga | 760 | 242 588 | 2026-08-30 13:47:48.471818686 | 2026-09-03 12:41:19.355830431 | si | 3.95 |
| GER-bundesliga | 612 | 199 024 | 2026-08-30 13:47:48.486148119 | 2026-09-03 13:09:12.440522432 | si | 3.97 |
| FRA-ligue-1 | 612 | 190 646 | 2026-08-30 13:47:48.478157520 | 2026-09-03 12:56:53.320906639 | si | 3.96 |

Il `mtime` da solo sarebbe un argomento debole — un timestamp si cambia. Quello
che regge il blocco e' il secondo controllo:

| campionato | anteriore_al_primo_evento | scarto_max_shots | scarto_max_sot | riprodotto | supera |
|---|---|---:|---:|---|---|
| ITA-serie-a | si | 1.17e-08 | 3.13e-09 | si | si |
| ENG-premier-league | si | 1.35e-08 | 1.03e-07 | si | si |
| ESP-la-liga | si | 2.25e-07 | 4.27e-07 | si | si |
| GER-bundesliga | si | 1.84e-08 | 1.21e-08 | si | si |
| FRA-ligue-1 | si | 1.01e-08 | 1.76e-07 | si | si |

> **Le previsioni congelate si riproducono da `prior_stagione.lam_dal_prior`
> applicato al fit della sola stagione precedente.** Ne segue che sono una
> funzione di dati che finiscono a maggio 2026, e quindi **non possono
> contenere informazione sulle giornate 1-2 qualunque sia la data in cui il
> file e' stato scritto**. E' l'argomento che non passa da nessun orologio.

**La riproduzione non e' bit-per-bit, e la ragione e' misurata**: dentro un solo
processo il re-fit da' scarto **0,0 esatto**; fra due processi resta un residuo
di ~1e-7 relativo, che e' esattamente l'ordine che `L-BFGS-B` con
`ftol = 1e-12` dichiara (`sqrt(ftol)` sui parametri). La tolleranza
(`TOLL_RIPRODUZIONE = 1e-05`) e' **derivata da li'**, non
scelta guardando lo scarto osservato.

E le previsioni congelate **sono** `modello prec`, cioe' esattamente cio' che
`prior_stagione.REGOLA_DUE_REGIMI` prescrive sotto
`config.BURN_IN_ROUND = 6`: si valuta la regola dichiarata,
non una variante costruita per l'occasione.

---

## 2. Il perimetro, e la giornata come grandezza da accertare

Il perimetro e' `team_match_idx <= 2`, cioe' le prime due
partite di ogni squadra. **Non e' la giornata**, ed e' una grandezza diversa
(vincolo 7): la giornata vera vive nella seconda fonte, che e' completa e sana
su un campionato solo.

| campionato | n_righe | n_partite | fonte_completa | verificabile | n_note | n_assenti_dalla_fonte | n_ambigue | n_discordi | accordo |
|---|---:|---:|---|---|---:|---:|---:|---:|---:|
| ITA-serie-a | 40 | 20 | si | si | 20 | 0 | 0 | 0 | 1.000 |
| ENG-premier-league | 40 | 20 | no | si | 16 | 4 | 0 | 0 | 1.000 |
| ESP-la-liga | 40 | 20 | no | si | 16 | 4 | 0 | 0 | 1.000 |
| GER-bundesliga | 14 | 7 | no | no | 0 | 0 | 0 | 0 | - |
| FRA-ligue-1 | 36 | 18 | no | si | 15 | 2 | 1 | 0 | 1.000 |

> **Il controllo positivo passa**: accordo totale dove la fonte e' completa (ITA-serie-a); 0 discordi dove e' parziale, contati e dichiarati. Su
> **67 partite** in cui entrambe le fonti parlano senza
> ambiguita', i disaccordi sono **0**.

Tre esiti restano separati, perche' confonderli produce un disaccordo inventato:
una partita **assente** dalla seconda fonte non dice niente sul ripiego (e'
incompletezza della pagina); una **ambigua** e' un rinvio che la fonte elenca a
due giornate diverse, e si tolgono tutte le copie come fa gia' `calendario.py`;
solo una partita elencata **senza ambiguita'** a una giornata sopra la soglia e'
un disaccordo vero.

> **La prima stesura di questa verifica ha sbagliato proprio qui**, e vale la
> pena scriverlo: costruiva un dizionario `coppia -> giornata` in cui l'ultima
> scrittura vinceva, e su `Paris FC-Nizza` — che Wikipedia elenca **alla 2 e
> alla 7** — teneva la 7. Ne usciva un disaccordo che era suo, non del ripiego.

### Le neopromosse: due perimetri, entrambi in tabella

| campionato | bersaglio | n_righe | n_congelate | n_neopromossa | scarto_max | coincidono |
|---|---|---:|---:|---:|---:|---|
| ITA-serie-a | shots | 40 | 28 | 12 | 1.17e-08 | si |
| ENG-premier-league | shots | 40 | 30 | 10 | 1.35e-08 | si |
| ESP-la-liga | shots | 40 | 30 | 10 | 2.25e-07 | si |
| GER-bundesliga | shots | 14 | 10 | 4 | 1.84e-08 | si |
| FRA-ligue-1 | shots | 36 | 28 | 8 | 1.01e-08 | si |
| ITA-serie-a | sot | 40 | 28 | 12 | 3.13e-09 | si |
| ENG-premier-league | sot | 40 | 30 | 10 | 1.03e-07 | si |
| ESP-la-liga | sot | 40 | 30 | 10 | 4.27e-07 | si |
| GER-bundesliga | sot | 14 | 10 | 4 | 1.21e-08 | si |
| FRA-ligue-1 | sot | 36 | 28 | 8 | 1.76e-07 | si |

Il file congelato contiene **solo le squadre della stagione precedente**, quindi
una riga che coinvolga una neopromossa non ha previsione documentale. La
previsione esiste lo stesso — `lam_dal_prior` da' coefficiente 0 a una squadra
sconosciuta — ma **e' un default, non una stima**: la media di campionato
dell'anno scorso. E' una quota grande, ed e' gia' di per se' un risultato: al
giorno 1 di una stagione nuova una riga su tre riguarda squadre che il modello
non ha mai visto.

---

## 3. La metrica, dichiarata prima

**CRPS su conteggi**, `somma_k (F(k) - 1[y <= k])^2`, in unita'
del bersaglio. E' propria, e' **ordinale** (sbagliare di 8 costa piu' che
sbagliare di 1, che la log score non distingue), e' robusta alle code — con
poche decine di righe una sola osservazione estrema deciderebbe il verdetto — ed
e' la stessa scelta che R2 ha fatto preferendo l'RPS alla log-loss sull'esito
1X2, su un bersaglio con piu' classi.

Le altre stanno **accanto**, mai al posto: log score (l'unita' di A2, per essere
confrontabili con `fase14_prior.md`), Brier sulle linee dichiarate, MAE e bias,
PIT e copertura. **Due metriche del repository NON si usano qui**: la
scomposizione di Murphy vuole otto fasce e a questo `n` il termine di binning
non e' trascurabile, e la pendenza di calibrazione ha un errore standard che la
rende non interpretabile — lo stesso `nan` dichiarato di `media campionato` in
Fase 4.

Ogni candidato si compone con la **stessa** NB2 e la **stessa** `r`: e' la
regola di R2. `r` e' quella **pubblicata**, mai ristimata — valutare con una
dispersione migliore misurerebbe un modello che nessuno ha mai pubblicato.


### Bersaglio `shots` — tiri

| candidato | n | n_partite | crps | log_score | mae | bias | sharpness | n_comuni | crps_righe_comuni |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| con prior | 170 | 85 | 3.0390 | 3.1642 | 4.222 | -0.907 | 3.627 | 152 | 3.1408 |
| senza prior | 152 | 76 | 3.3762 | 3.3722 | 4.652 | -0.909 | 3.603 | 152 | 3.3762 |
| modello prec | 170 | 85 | 2.8260 | 3.0152 | 3.899 | -1.033 | 2.558 | 152 | 2.9026 |
| media squadra prec | 170 | 85 | 2.9765 | 3.0769 | 4.167 | -0.773 | 1.914 | 152 | 3.0033 |
| media campionato prec | 170 | 85 | 3.1889 | 3.1475 | 4.431 | -1.094 | 0.239 | 152 | 3.2054 |
| oracolo di livello | 170 | 85 | 2.7245 | 2.9600 | 3.886 | -0.000 | 3.013 | 152 | 2.7781 |

**Solo sulle righe con previsione DOCUMENTALE** (entrambe le squadre note al
2025-2026, cioe' un numero scritto su disco prima dei fatti):

| candidato | n | n_partite | crps | log_score | mae | bias | sharpness | n_comuni | crps_righe_comuni |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| con prior | 126 | 63 | 2.8779 | 3.0539 | 4.016 | -0.969 | 3.510 | 112 | 2.9672 |
| senza prior | 112 | 56 | 3.1065 | 3.1853 | 4.328 | -0.894 | 3.398 | 112 | 3.1065 |
| modello prec | 126 | 63 | 2.7750 | 3.0095 | 3.815 | -1.114 | 2.644 | 112 | 2.8514 |
| media squadra prec | 126 | 63 | 2.9115 | 3.0623 | 4.085 | -0.808 | 2.028 | 112 | 2.9666 |
| media campionato prec | 126 | 63 | 3.0995 | 3.1163 | 4.345 | -1.165 | 0.235 | 112 | 3.1355 |
| oracolo di livello | 126 | 63 | 2.6702 | 2.9529 | 3.776 | -0.108 | 3.050 | 112 | 2.7384 |

#### Il soggetto contro ogni altro candidato

| soggetto | avversario | n | n_cluster | crps_soggetto | crps_avversario | delta_crps | t_cluster | mde | delta_su_mde | conclude | vince_il_soggetto |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---|
| modello prec | con prior | 170 | 85 | 2.8260 | 3.0390 | -0.2129 | -1.86 | 0.3213 | 0.66 | no | si |
| modello prec | senza prior | 152 | 76 | 2.9026 | 3.3762 | -0.4736 | -2.46 | 0.5401 | 0.88 | no | si |
| modello prec | media squadra prec | 170 | 85 | 2.8260 | 2.9765 | -0.1505 | -1.63 | 0.2587 | 0.58 | no | si |
| modello prec | media campionato prec | 170 | 85 | 2.8260 | 3.1889 | -0.3628 | -3.13 | 0.3248 | 1.12 | si | si |
| modello prec | oracolo di livello | 170 | 85 | 2.8260 | 2.7245 | 0.1016 | 1.81 | 0.1571 | 0.65 | no | no |

> **Verdetto contro `media squadra prec`**: delta -0.1505,
> t -1.63, MDE 0.2587, **delta/MDE
> 0.58** su 85 partite —
> **il test NON conclude**.
> delta sotto il proprio MDE: il test NON conclude, che non e' «l'effetto non c'e'»

#### Il livello del campionato nuovo, separato dall'ordinamento

| | |
|---|---:|
| media prevista | 12.556 |
| media osservata | 13.588 |
| scarto di livello | +8.2% |
| CRPS `modello prec` | 2.8264 |
| CRPS `oracolo di livello` | 2.7251 |
| **quota del CRPS attribuibile al solo livello** | **3.6%** |

#### Brier sulle linee dichiarate

| linea | n | tasso_base_osservato | p_media_dichiarata | brier | brier_tasso_base_oracolo | vince_sul_tasso_base |
|---:|---:|---:|---:|---:|---:|---|
| 8.500 | 170 | 0.812 | 0.773 | 0.1374 | 0.1528 | si |
| 10.500 | 170 | 0.706 | 0.616 | 0.1822 | 0.2076 | si |
| 12.500 | 170 | 0.518 | 0.456 | 0.2087 | 0.2497 | si |
| 14.500 | 170 | 0.400 | 0.316 | 0.2229 | 0.2400 | si |
| 16.500 | 170 | 0.282 | 0.206 | 0.1814 | 0.2026 | si |



### Bersaglio `sot` — tiri in porta

| candidato | n | n_partite | crps | log_score | mae | bias | sharpness | n_comuni | crps_righe_comuni |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| con prior | 170 | 85 | 1.2926 | 2.2454 | 1.842 | -0.194 | 1.251 | 152 | 1.3441 |
| senza prior | 152 | 76 | 1.5102 | 2.4326 | 2.146 | -0.105 | 1.499 | 152 | 1.5102 |
| modello prec | 170 | 85 | 1.1991 | 2.1583 | 1.709 | -0.166 | 0.850 | 152 | 1.2395 |
| media squadra prec | 170 | 85 | 1.2735 | 2.2165 | 1.852 | -0.080 | 0.874 | 152 | 1.3049 |
| media campionato prec | 170 | 85 | 1.3851 | 2.2956 | 1.994 | -0.202 | 0.193 | 152 | 1.4014 |
| oracolo di livello | 170 | 85 | 1.1813 | 2.1456 | 1.709 | -0.000 | 1.024 | 152 | 1.2156 |

**Solo sulle righe con previsione DOCUMENTALE** (entrambe le squadre note al
2025-2026, cioe' un numero scritto su disco prima dei fatti):

| candidato | n | n_partite | crps | log_score | mae | bias | sharpness | n_comuni | crps_righe_comuni |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| con prior | 126 | 63 | 1.2559 | 2.2146 | 1.799 | -0.172 | 1.199 | 112 | 1.3008 |
| senza prior | 112 | 56 | 1.4746 | 2.3997 | 2.098 | -0.087 | 1.403 | 112 | 1.4746 |
| modello prec | 126 | 63 | 1.1955 | 2.1614 | 1.716 | -0.136 | 0.880 | 112 | 1.2329 |
| media squadra prec | 126 | 63 | 1.2799 | 2.2245 | 1.863 | -0.048 | 0.929 | 112 | 1.3148 |
| media campionato prec | 126 | 63 | 1.4148 | 2.3173 | 2.044 | -0.187 | 0.189 | 112 | 1.4316 |
| oracolo di livello | 126 | 63 | 1.1855 | 2.1563 | 1.724 | 0.025 | 1.052 | 112 | 1.2172 |

#### Il soggetto contro ogni altro candidato

| soggetto | avversario | n | n_cluster | crps_soggetto | crps_avversario | delta_crps | t_cluster | mde | delta_su_mde | conclude | vince_il_soggetto |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---|
| modello prec | con prior | 170 | 85 | 1.1991 | 1.2926 | -0.0935 | -2.51 | 0.1045 | 0.89 | no | si |
| modello prec | senza prior | 152 | 76 | 1.2395 | 1.5102 | -0.2707 | -3.96 | 0.1915 | 1.41 | si | si |
| modello prec | media squadra prec | 170 | 85 | 1.1991 | 1.2735 | -0.0744 | -2.53 | 0.0824 | 0.90 | no | si |
| modello prec | media campionato prec | 170 | 85 | 1.1991 | 1.3851 | -0.1860 | -4.57 | 0.1139 | 1.63 | si | si |
| modello prec | oracolo di livello | 170 | 85 | 1.1991 | 1.1813 | 0.0179 | 1.16 | 0.0433 | 0.41 | no | no |

> **Verdetto contro `media squadra prec`**: delta -0.0744,
> t -2.53, MDE 0.0824, **delta/MDE
> 0.90** su 85 partite —
> **il test NON conclude**.
> delta sotto il proprio MDE: il test NON conclude, che non e' «l'effetto non c'e'»

#### Il livello del campionato nuovo, separato dall'ordinamento

| | |
|---|---:|
| media prevista | 4.299 |
| media osservata | 4.465 |
| scarto di livello | +3.9% |
| CRPS `modello prec` | 1.1991 |
| CRPS `oracolo di livello` | 1.1812 |
| **quota del CRPS attribuibile al solo livello** | **1.5%** |

#### Brier sulle linee dichiarate

| linea | n | tasso_base_osservato | p_media_dichiarata | brier | brier_tasso_base_oracolo | vince_sul_tasso_base |
|---:|---:|---:|---:|---:|---:|---|
| 2.500 | 170 | 0.765 | 0.764 | 0.1730 | 0.1799 | si |
| 3.500 | 170 | 0.606 | 0.591 | 0.2104 | 0.2388 | si |
| 4.500 | 170 | 0.447 | 0.419 | 0.2044 | 0.2472 | si |
| 5.500 | 170 | 0.324 | 0.274 | 0.1815 | 0.2189 | si |



---

## 4. Per campionato

| campionato | bersaglio | n | n_partite | r | crps_modello_prec | crps_media_squadra_prec | delta_crps | mae | bias | media_osservata | scarto_di_livello_pct | quota_congelate |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| ITA-serie-a | shots | 40 | 20 | 20.02 | 2.9059 | 2.8773 | 0.0287 | 3.843 | -1.898 | 14.20 | 15.43 | 0.700 |
| ENG-premier-league | shots | 40 | 20 | 19.37 | 3.1205 | 3.2785 | -0.1580 | 4.343 | -1.075 | 13.70 | 8.52 | 0.750 |
| ESP-la-liga | shots | 40 | 20 | 20.23 | 2.3365 | 2.5966 | -0.2601 | 3.384 | 0.841 | 11.62 | -6.74 | 0.750 |
| GER-bundesliga | shots | 14 | 7 | 20.77 | 2.8246 | 3.3662 | -0.5416 | 4.117 | -2.577 | 16.14 | 19.00 | 0.714 |
| FRA-ligue-1 | shots | 36 | 18 | 20.68 | 2.9545 | 3.0219 | -0.0674 | 3.955 | -1.505 | 13.97 | 12.07 | 0.778 |
| ITA-serie-a | sot | 40 | 20 | 31.61 | 1.0797 | 1.1100 | -0.0304 | 1.500 | -0.225 | 4.25 | 5.58 | 0.700 |
| ENG-premier-league | sot | 40 | 20 | 28.76 | 1.2425 | 1.2843 | -0.0418 | 1.764 | -0.060 | 4.28 | 1.43 | 0.750 |
| ESP-la-liga | sot | 40 | 20 | 30.97 | 1.2215 | 1.2219 | -0.0004 | 1.848 | 0.182 | 4.17 | -4.19 | 0.750 |
| GER-bundesliga | sot | 14 | 7 | 33.09 | 1.3729 | 1.7622 | -0.3893 | 1.639 | -1.244 | 6.21 | 25.02 | 0.714 |
| FRA-ligue-1 | sot | 36 | 18 | 27.81 | 1.1912 | 1.3104 | -0.1193 | 1.752 | -0.187 | 4.56 | 4.27 | 0.778 |

---

## 5. La forma della predittiva

| bersaglio | n | r | pit_chi2 | pit_p | pit_media | pit_sd | copertura_50 | copertura_80 | copertura_95 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| shots | 170 | 20.02 | 6.59 | 0.680 | 0.553 | 0.292 | 0.541 | 0.841 | 0.929 |
| sot | 170 | 31.61 | 6.71 | 0.668 | 0.523 | 0.286 | 0.612 | 0.894 | 0.982 |

> Su questo perimetro il PIT e' **debole** — dieci fasce su poche decine di
> righe — e va letto come indizio, non come test. E' una delle ragioni per cui
> la taratura del §6 non e' un ornamento.

---

## 6. La taratura storica — senza, un CRPS e' un numero e non un risultato

La **stessa identica procedura** sulle prime due partite di ogni squadra nelle
transizioni gia' concluse, dove l'esito e' noto. E' il gemello di
`tentativi.taratura_test()` e del nullo simulato di V0: la differenza fra «il
test ha trovato qualcosa» e «il test rifiuta sempre» si vede solo mettendo
accanto il caso in cui la risposta si conosce.

| campionato | stagione | bersaglio | n_partite | crps_modello_prec | crps_media_squadra_prec | delta_crps | t_cluster | bias | scarto_di_livello_pct |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|
| ITA-serie-a | 2022-2023 | shots | 20 | 3.1442 | 3.0567 | 0.0875 | 0.49 | -0.658 | 5.05 |
| ITA-serie-a | 2023-2024 | shots | 20 | 2.6248 | 3.0812 | -0.4564 | -3.00 | -0.186 | 1.50 |
| ITA-serie-a | 2024-2025 | shots | 20 | 2.7521 | 2.8653 | -0.1132 | -0.62 | -0.211 | 1.67 |
| ITA-serie-a | 2025-2026 | shots | 20 | 2.4734 | 2.6431 | -0.1698 | -1.28 | -0.174 | 1.45 |
| ENG-premier-league | 2022-2023 | shots | 20 | 2.1783 | 2.5906 | -0.4123 | -2.21 | 0.345 | -2.73 |
| ENG-premier-league | 2023-2024 | shots | 21 | 2.8081 | 3.0073 | -0.1993 | -1.02 | -1.772 | 14.12 |
| ENG-premier-league | 2024-2025 | shots | 20 | 2.6743 | 2.7615 | -0.0872 | -0.41 | 1.542 | -11.12 |
| ENG-premier-league | 2025-2026 | shots | 20 | 2.4600 | 2.5998 | -0.1398 | -0.87 | 1.225 | -9.65 |
| ESP-la-liga | 2022-2023 | shots | 20 | 2.4357 | 2.5886 | -0.1529 | -0.73 | -0.622 | 5.38 |
| ESP-la-liga | 2023-2024 | shots | 20 | 2.4870 | 2.5786 | -0.0916 | -0.52 | -0.012 | 0.10 |
| ESP-la-liga | 2024-2025 | shots | 20 | 2.1335 | 2.0922 | 0.0412 | 0.28 | 0.727 | -6.04 |
| ESP-la-liga | 2025-2026 | shots | 20 | 2.7038 | 2.8846 | -0.1808 | -1.13 | -0.349 | 2.96 |
| GER-bundesliga | 2022-2023 | shots | 18 | 3.0313 | 3.2513 | -0.2200 | -1.33 | -0.676 | 5.23 |
| GER-bundesliga | 2023-2024 | shots | 18 | 2.7539 | 3.1096 | -0.3558 | -2.29 | -1.891 | 14.93 |
| GER-bundesliga | 2024-2025 | shots | 18 | 2.7024 | 2.7523 | -0.0499 | -0.26 | 0.396 | -2.85 |
| GER-bundesliga | 2025-2026 | shots | 18 | 2.7011 | 2.5279 | 0.1732 | 0.90 | 0.009 | -0.07 |
| FRA-ligue-1 | 2022-2023 | shots | 21 | 2.5180 | 2.5277 | -0.0097 | -0.02 | -0.760 | 6.27 |
| FRA-ligue-1 | 2023-2024 | shots | 19 | 2.6352 | 2.5786 | 0.0566 | 0.30 | -0.036 | 0.29 |
| FRA-ligue-1 | 2024-2025 | shots | 18 | 2.8585 | 3.0203 | -0.1618 | -0.86 | 0.022 | -0.18 |
| FRA-ligue-1 | 2025-2026 | shots | 18 | 2.8160 | 2.8417 | -0.0257 | -0.16 | 0.239 | -1.95 |
| ITA-serie-a | 2022-2023 | sot | 20 | 1.3739 | 1.3180 | 0.0559 | 1.00 | 0.361 | -8.01 |
| ITA-serie-a | 2023-2024 | sot | 20 | 1.0064 | 1.0384 | -0.0319 | -0.79 | 0.125 | -3.08 |
| ITA-serie-a | 2024-2025 | sot | 20 | 1.1750 | 1.1749 | 0.0000 | 0.00 | -0.277 | 6.72 |
| ITA-serie-a | 2025-2026 | sot | 20 | 1.0215 | 1.1000 | -0.0785 | -1.82 | 0.244 | -6.06 |
| ENG-premier-league | 2022-2023 | sot | 20 | 1.0651 | 1.2803 | -0.2152 | -3.37 | 0.449 | -10.14 |
| ENG-premier-league | 2023-2024 | sot | 21 | 1.5384 | 1.6617 | -0.1234 | -1.54 | -0.444 | 10.01 |
| ENG-premier-league | 2024-2025 | sot | 20 | 1.1715 | 1.2380 | -0.0665 | -0.86 | 0.816 | -16.43 |
| ENG-premier-league | 2025-2026 | sot | 20 | 1.0053 | 1.0831 | -0.0778 | -1.98 | 0.872 | -19.50 |
| ESP-la-liga | 2022-2023 | sot | 20 | 1.2964 | 1.2029 | 0.0936 | 1.40 | -0.170 | 4.35 |
| ESP-la-liga | 2023-2024 | sot | 20 | 1.4280 | 1.4205 | 0.0075 | 0.09 | 0.212 | -5.16 |
| ESP-la-liga | 2024-2025 | sot | 20 | 1.0287 | 1.1313 | -0.1026 | -1.99 | 0.452 | -10.64 |
| ESP-la-liga | 2025-2026 | sot | 20 | 1.1668 | 1.1179 | 0.0489 | 0.62 | -0.080 | 1.95 |
| GER-bundesliga | 2022-2023 | sot | 18 | 1.4671 | 1.4754 | -0.0084 | -0.11 | -0.525 | 11.31 |
| GER-bundesliga | 2023-2024 | sot | 18 | 1.6631 | 1.7516 | -0.0885 | -0.81 | -0.519 | 11.23 |
| GER-bundesliga | 2024-2025 | sot | 18 | 1.4270 | 1.4057 | 0.0213 | 0.22 | -0.016 | 0.34 |
| GER-bundesliga | 2025-2026 | sot | 18 | 1.0779 | 1.0249 | 0.0531 | 1.02 | 0.126 | -2.77 |
| FRA-ligue-1 | 2022-2023 | sot | 21 | 1.3599 | 1.3554 | 0.0046 | 0.12 | -0.792 | 18.70 |
| FRA-ligue-1 | 2023-2024 | sot | 19 | 1.2211 | 1.2284 | -0.0074 | -0.01 | -0.032 | 0.69 |
| FRA-ligue-1 | 2024-2025 | sot | 18 | 1.3622 | 1.3906 | -0.0284 | -0.43 | -0.217 | 4.81 |
| FRA-ligue-1 | 2025-2026 | sot | 18 | 1.3302 | 1.4916 | -0.1614 | -2.21 | 1.043 | -22.54 |

### Dove cade la stagione nuova

| bersaglio | grandezza | confronto | n_storiche | osservato | mediana_storica | minimo_storico | massimo_storico | rango | quota_peggiori | dentro_l_intervallo_storico |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| shots | crps_modello_prec | 5 campionati insieme, per stagione | 4 | 2.8260 | 2.6397 | 2.6176 | 2.6604 | 5 | 0.000 | no |
| shots | delta_crps | 5 campionati insieme, per stagione | 4 | -0.1505 | -0.1072 | -0.2118 | -0.0728 | 2 | 0.750 | si |
| shots | scarto_di_livello_pct | 5 campionati insieme, per stagione | 4 | 8.1682 | 1.1705 | -3.7948 | 6.1280 | 5 | 1.000 | no |
| shots | crps_modello_prec | ITA-serie-a | 4 | 2.9059 | 2.6885 | 2.4734 | 3.1442 | 4 | 0.250 | si |
| shots | scarto_di_livello_pct | ITA-serie-a | 4 | 15.4283 | 1.5843 | 1.4509 | 5.0452 | 5 | 1.000 | no |
| shots | crps_modello_prec | ENG-premier-league | 4 | 3.1205 | 2.5671 | 2.1783 | 2.8081 | 5 | 0.000 | no |
| shots | scarto_di_livello_pct | ENG-premier-league | 4 | 8.5169 | -6.1875 | -11.1175 | 14.1168 | 4 | 0.750 | si |
| shots | crps_modello_prec | ESP-la-liga | 4 | 2.3365 | 2.4614 | 2.1335 | 2.7038 | 2 | 0.750 | si |
| shots | scarto_di_livello_pct | ESP-la-liga | 4 | -6.7438 | 1.5295 | -6.0446 | 5.3830 | 1 | 0.000 | no |
| shots | crps_modello_prec | GER-bundesliga | 4 | 2.8246 | 2.7281 | 2.7011 | 3.0313 | 4 | 0.250 | si |
| shots | scarto_di_livello_pct | GER-bundesliga | 4 | 18.9971 | 2.5779 | -2.8502 | 14.9323 | 5 | 1.000 | no |
| shots | crps_modello_prec | FRA-ligue-1 | 4 | 2.9545 | 2.7256 | 2.5180 | 2.8585 | 5 | 0.000 | no |
| shots | scarto_di_livello_pct | FRA-ligue-1 | 4 | 12.0717 | 0.0549 | -1.9494 | 6.2727 | 5 | 1.000 | no |
| sot | crps_modello_prec | 5 campionati insieme, per stagione | 4 | 1.1991 | 1.2677 | 1.1168 | 1.3685 | 2 | 0.750 | si |
| sot | delta_crps | 5 campionati insieme, per stagione | 4 | -0.0744 | -0.0396 | -0.0488 | -0.0140 | 1 | 1.000 | no |
| sot | scarto_di_livello_pct | 5 campionati insieme, per stagione | 4 | 3.6292 | -0.3350 | -9.6646 | 3.0782 | 5 | 1.000 | no |
| sot | crps_modello_prec | ITA-serie-a | 4 | 1.0797 | 1.0982 | 1.0064 | 1.3739 | 3 | 0.500 | si |
| sot | scarto_di_livello_pct | ITA-serie-a | 4 | 5.5840 | -4.5711 | -8.0052 | 6.7153 | 4 | 0.750 | si |
| sot | crps_modello_prec | ENG-premier-league | 4 | 1.2425 | 1.1183 | 1.0053 | 1.5384 | 4 | 0.250 | si |
| sot | scarto_di_livello_pct | ENG-premier-league | 4 | 1.4285 | -13.2867 | -19.5006 | 10.0140 | 4 | 0.750 | si |
| sot | crps_modello_prec | ESP-la-liga | 4 | 1.2215 | 1.2316 | 1.0287 | 1.4280 | 3 | 0.500 | si |
| sot | scarto_di_livello_pct | ESP-la-liga | 4 | -4.1878 | -1.6045 | -10.6364 | 4.3450 | 3 | 0.500 | si |
| sot | crps_modello_prec | GER-bundesliga | 4 | 1.3729 | 1.4470 | 1.0779 | 1.6631 | 2 | 0.750 | si |
| sot | scarto_di_livello_pct | GER-bundesliga | 4 | 25.0169 | 5.7846 | -2.7664 | 11.3147 | 5 | 1.000 | no |
| sot | crps_modello_prec | FRA-ligue-1 | 4 | 1.1912 | 1.3451 | 1.2211 | 1.3622 | 1 | 1.000 | no |
| sot | scarto_di_livello_pct | FRA-ligue-1 | 4 | 4.2707 | 2.7484 | -22.5410 | 18.7030 | 3 | 0.500 | si |

> Si riporta il **rango**, non un p-value: venti transizioni non sono un
> campione da cui estrarre una probabilita', e chiamarla tale sarebbe fabbricare
> precisione.

---

## 7. La dispersione di avvio — DIAGNOSTICO, non adozione

**L'attesa era dichiarata prima**: `r` viene dal walk-forward **within-season**,
dove i lambda sono piu' accurati di quelli cross-stagione di `modello prec`, e
una previsione peggiore ha residui piu' dispersi. Se e' cosi', la predittiva
pubblicata e' **troppo stretta** all'avvio.

| bersaglio | n | n_cluster | r_avvio | r_pubblicata | rapporto | compatibili | predittiva_troppo_stretta |
|---|---:|---:|---:|---:|---:|---|---|
| shots | 772 | 389 | 16.28 | 20.23 | 0.805 | si | no |
| sot | 772 | 389 | 22.53 | 30.97 | 0.727 | si | no |

IC95 del rapporto da bootstrap **sui cluster** (la partita, non la riga), la
stessa forma con cui `precisione.rapporto_dispersioni()` ha falsificato
l'ereditarieta' fra `r_shots` e `r_sot` e con cui T1 ha rifiutato di ereditare
`r_tot`: shots: [0.649, 1.078]; sot: [0.448, 2.038].

> **Questo blocco non ricalibra niente.** Adottare una `r` diversa vorrebbe un
> criterio scritto prima e una valutazione fuori campione sua, che qui non c'e'.

---

## 8. Il totale di partita — secondario, e ci si aspetta di non concludere

`E[X+Y] = E[X] + E[Y]` e' esatto qualunque sia la dipendenza fra i due lati
(T1), quindi `lam_tot` non richiede ipotesi; `r_tot` **non si eredita** e viene
da quella gia' stimata sulle stagioni storiche di ogni campionato.

| bersaglio | candidato | n_partite | crps | mae | bias |
|---|---|---:|---:|---:|---:|
| shots | con prior | 85 | 3.6116 | 5.046 | -2.054 |
| shots | media campionato prec | 85 | 3.7516 | 5.278 | -2.674 |
| shots | media squadra prec | 85 | 3.7912 | 5.356 | -2.003 |
| shots | modello prec | 85 | 3.6873 | 5.209 | -2.486 |
| shots | oracolo di livello | 85 | 3.1197 | 4.427 | -0.000 |
| shots | senza prior | 76 | 3.4133 | 4.817 | -1.614 |
| sot | con prior | 85 | 1.7407 | 2.450 | -0.584 |
| sot | media campionato prec | 85 | 1.8545 | 2.605 | -0.727 |
| sot | media squadra prec | 85 | 1.8595 | 2.597 | -0.451 |
| sot | modello prec | 85 | 1.7481 | 2.423 | -0.613 |
| sot | oracolo di livello | 85 | 1.6428 | 2.415 | -0.000 |
| sot | senza prior | 76 | 1.8753 | 2.699 | -0.128 |

T1 ha gia' misurato che il totale e' **sotto-calibrato** (pendenza 0,633 su
1.638 partite); qui i cluster sono poche decine. Si riporta se il segno e'
coerente con T1, **non si adotta niente**.

---

## 9. Limiti, accanto ai numeri e non in fondo

- Il campione e' di poche decine di partite: quasi ogni confronto sta sotto il proprio MDE. Il blocco esclude divari grandi, non divari piccoli — e' la lezione di 6D, V3 e A2.
- Le neopromosse non hanno previsione congelata: `PS.lam_dal_prior` da' loro coefficiente 0, cioe' la media di campionato dell'anno scorso. E' un DEFAULT dichiarato, non una stima, ed e' contato riga per riga.
- La giornata vera e' accertata solo dove la seconda fonte e' sana; altrove il perimetro e' `team_match_idx <= 2`, che e' una grandezza diversa (vincolo 7). Quale delle due si e' usata e' scritto per campionato.
- Un campionato entra con i dati che ha: dove mancano CSV di evento di partite gia' giocate, il perimetro e' piu' corto e lo dichiara.
- `r` e' quella PUBBLICATA, non ristimata: valutare con una dispersione migliore misurerebbe un modello che nessuno ha mai pubblicato.
- Vincolo 3: nessuna quota, nessun valore atteso, nessuna valutazione di scommessa. Non ci sono prezzi di mercato reali nel repository, e le uniche ottenibili sarebbero generate da questo stesso modello.
- La taratura storica e' una scala di riferimento, non un test: venti transizioni danno un rango, non una probabilita'.

---

## 10. Il criterio, scritto prima

```
un confronto CONCLUDE solo se |delta| / MDE >= 1, con il MDE clusterizzato per partita e a due code (la stessa forma di PS.mde_relativo, cioe' quella con cui A2 ha giudicato le stesse righe di avvio). Sotto 1 il blocco dichiara «il test non conclude», che NON e' «l'effetto non c'e'».
```

| bersaglio | delta CRPS | t | delta/MDE | conclude |
|---|---:|---:|---:|---|
| tiri | -0.1505 | -1.63 | 0.58 | no |
| tiri in porta | -0.0744 | -2.53 | 0.90 | no |

> **«Significativo» e «il test aveva la potenza per vederlo» non sono la stessa
> cosa, e qui le due letture divergono.** Il criterio `delta/MDE >= 1` equivale
> a `|t| >= 2.80`, perche' il MDE e' calcolato a due code e a potenza
> 80%. La soglia di Sidak su 5 confronti dichiarati vale invece
> `|t| > 2.32`, e quella di significativita' a due code 1,96.
>
> Sui **tiri in porta** il `t = -2.53` contro
> `media squadra prec` passa entrambe le soglie piu' basse e **non** il criterio
> dichiarato. Non e' un cavillo: vuol dire che l'effetto osservato e' piu'
> piccolo del piu' piccolo che questo campione fosse attrezzato a rilevare, e
> chiamarlo «dimostrato» sarebbe leggere un test che non aveva la potenza per
> dirlo. **Il criterio era scritto prima e non e' stato riscritto per farlo
> tornare** — la stessa disciplina di `LATI_STRATO2` in V2 e di
> `CRITERIO_ADOZIONE` in A2.
