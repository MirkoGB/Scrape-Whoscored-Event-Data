# Fase 12 / Blocco V1 — lo strato del volume

> Generato da `scripts/run_fase12_v1.py` il 2026-08-13.
> **Non tocca la rete.** Unica scrittura sotto `data/`: la cache
> `fase12_walkforward_tiri.parquet`, rigenerabile con `--force`.

## 0. Che cosa fa questo blocco

```
shots_ij ~ NB2(lambda_ij, r)
log(lambda_ij) = mu + attacco_i + difesa_j + gamma * casa
```

**Stessa specificazione della Fase 2, bersaglio diverso.** E' voluto: se la
specificazione cambiasse insieme al bersaglio non si saprebbe a quale delle due
cose attribuire la differenza. E' la disciplina con cui E3 ha portato
`TeamModel` sui gol.

**La validazione non si eredita, ed e' rifatta da capo.** `r`, il tasso base, la
pendenza e il PIT sono ricostruiti sul solo passato, perche' entrano nelle
metriche e un parametro stimato sull'intero campione non e' fuori campione.

## 1. Il perimetro

| stagione | righe_universo | con_previsione | senza_previsione | valutabili | perse_burnin | quota_valutabile |
|---|---:|---:|---:|---:|---:|---:|
| 2021-2022 | 748 | 688 | 60 | 648 | 40 | 0.8663 |
| 2022-2023 | 750 | 690 | 60 | 650 | 40 | 0.8667 |
| 2023-2024 | 760 | 700 | 60 | 660 | 40 | 0.8684 |
| 2024-2025 | 760 | 700 | 60 | 660 | 40 | 0.8684 |
| 2025-2026 | 760 | 700 | 60 | 660 | 40 | 0.8684 |
| TOTALE | 3778 | 3478 | 300 | 3278 | 200 | 0.8677 |

**I cold start sono cinque, non uno**, ed e' il costo del perimetro
multi-stagione: le prime tre giornate di ogni stagione non hanno previsione
(`date_splits` pretende 30 partite di training) e il burn-in ne toglie altre
due. Le due cause **non si sommano** e sono in colonne separate.

Le 3278 righe valutabili sono le stesse di E3 sui gol, ed e'
un controllo di coerenza: due bersagli diversi sullo stesso universo devono
produrre lo stesso perimetro.

## 2. Il modello contro i quattro baseline (vincolo 6)

| modello | n | mae | bias | corr | sharpness | calib_slope | calib_se | calib_z_vs_1 | brier | brier_base |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Poisson ridge att/dif/casa | 3278 | 3.5733 | 0.0864 | 0.4937 | 2.5703 | 1.0075 | 0.0245 | 0.31 | 0.2084 | 0.2482 |
| media squadra + campo | 3278 | 3.8634 | 0.1128 | 0.3605 | 2.4549 | 0.7553 | 0.0254 | -9.62 | 0.2300 | 0.2482 |
| media squadra | 3278 | 3.9755 | 0.1117 | 0.2909 | 2.2179 | 0.6816 | 0.0282 | -11.30 | 0.2381 | 0.2482 |
| media casa/trasferta | 3278 | 4.0132 | 0.1066 | 0.2225 | 1.1312 | 1.0378 | 0.0553 | 0.68 | 0.2408 | 0.2482 |
| media campionato | 3278 | 4.1129 | 0.1056 | 0.0443 | 0.2647 | 0.8880 | 0.2357 | -0.48 | 0.2482 | 0.2482 |

## 3. Il margine, e il suo `t` — per riga E per cluster

| baseline | mae_baseline | mae_modello | delta_mae | t_per_riga | t_per_cluster | rapporto |
|---|---:|---:|---:|---:|---:|---:|
| media squadra + campo | 3.8634 | 3.5733 | 0.2901 | 9.69 | 9.63 | 0.994 |
| media squadra | 3.9755 | 3.5733 | 0.4021 | 11.76 | 11.57 | 0.984 |
| media casa/trasferta | 4.0132 | 3.5733 | 0.4398 | 12.55 | 11.74 | 0.936 |
| media campionato | 4.1129 | 3.5733 | 0.5395 | 14.08 | 13.02 | 0.925 |

**Questo e' il risultato del blocco: sui tentativi il modello si giustifica
anche sull'ACCURATEZZA, e sui tiri in porta non ci riusciva.**

| bersaglio | fase | `t` contro `media squadra + campo` |
|---|---|---:|
| tiri in porta | Fase 2 / Fase 4 | **1,86** — dentro il rumore |
| gol | Fase 9 / E3.1 | **5,52** |
| **tentativi** | **Fase 12 / V1** | **9.63** |

Non e' un modello migliore: e' un **bersaglio piu' facile da distinguere**. I
tentativi sono tre volte piu' numerosi dei tiri in porta, quindi il rumore
relativo e' minore, e dipendono dal dominio territoriale, che e' la cosa piu'
persistente che una squadra abbia. Il tiro in porta aggiunge a quel volume un
passaggio di precisione che V2 modella a parte — ed e' proprio quel passaggio a
rendere i SoT piu' rumorosi.

**I due `t` si riportano in coppia**, e il rapporto e' la misura che rende
leggibile la correzione. V0 aveva previsto un fattore **0,807** dalla
correlazione fra i due lati (-0,349); l'osservato sul confronto appaiato vale
**0.925-0.994**, cioe' molto piu' vicino a 1.

**La previsione di V0 era approssimativa e va corretta**: quel fattore riguarda
la correlazione dei **valori**, mentre qui conta la correlazione degli **errori**
del confronto appaiato, che e' molto piu' debole. Le due squadre di una partita
si sottraggono i tentativi, ma il modello non sbaglia sull'una perche' ha
sbagliato sull'altra. La conclusione non cambia — il `t` per cluster resta
l'unita' onesta e resta enorme — ma il numero di V0 non va citato come se
descrivesse questo.

## 4. La calibrazione, e perche' e' l'argomento piu' forte

Il modello ha pendenza **1.0075 ± 0.0245**
(z = +0.31), cioe' compatibile con 1.0. I due baseline
informativi stanno a 0.755 e 0.682
con z -9.6 e -11.3: danno
previsioni **troppo estreme**, perche' una media campionaria non regredisce
verso il centro. La ridge corregge esattamente quello.

E' la stessa forma dell'argomento della Fase 4, molto piu' netta. `media
campionato` non e' identificata (errore standard 0.236 su un
lambda quasi costante), come in Fase 4 e per la stessa ragione.

## 5. Cinque quasi-repliche invece di un numero solo

| stagione | n | media_osservata | mae | mae_relativo | bias | corr | delta_su_baseline | t_per_cluster | vince |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 2021-2022 | 648 | 13.005 | 3.8157 | 0.2934 | -0.0312 | 0.5340 | 0.4746 | 5.51 | si |
| 2022-2023 | 650 | 12.597 | 3.4780 | 0.2761 | 0.1605 | 0.4875 | 0.2730 | 4.21 | si |
| 2023-2024 | 660 | 12.802 | 3.4350 | 0.2683 | -0.1691 | 0.4342 | 0.1829 | 3.32 | si |
| 2024-2025 | 660 | 12.011 | 3.5542 | 0.2959 | 0.3636 | 0.4675 | 0.2689 | 4.21 | si |
| 2025-2026 | 660 | 12.270 | 3.5867 | 0.2923 | 0.1073 | 0.5058 | 0.2543 | 4.05 | si |

**Vince in tutte e cinque**, con `t` per cluster fra 3.3 e
5.5. Cinque segni concordi sono un'evidenza diversa da un `t`
pooled dello stesso valore, e la seconda non si legge dalla prima.

**Il MAE assoluto non e' confrontabile fra stagioni** — il livello si muove del
5,5%, quindi un MAE piu' basso puo' voler dire solo che si tirava di meno. La
colonna da leggere in orizzontale e' `mae_relativo`, che resta fra
0.268 e 0.296: la difficolta' del problema non
cambia fra stagioni.

## 6. La dispersione, e la forma della predittiva

| | |
|---|---:|
| var/media **grezzo** | 2.1806 |
| dispersione di Pearson, **condizionata a lambda** | 1.6138 |
| `r` NB2 | **20.02** |
| sospetto (`r < 10`) | no |

I tentativi **sono sovradispersi**: `r = 20.0` contro i 26,0 dei tiri in
porta. Condizionare a lambda toglie gran parte dell'eccesso
(2.18 -> 1.61), cioe' il modello
spiega una parte importante della variazione — ma non tutta, e la Poisson pura
sarebbe sbagliata su questo bersaglio. `r` entra nel Brier e negli intervalli
**ricostruita walk-forward**, mai stimata sull'intero campione.

**PIT randomizzato: chi2 = 4.12 su 9 gdl,
p = 0.9035.** E' il controllo che la pendenza di calibrazione
non fa: la forma dell'intera distribuzione predittiva regge, non solo la media.

| livello | copertura | ampiezza_media |
|---:|---:|---:|
| 0.50 | 0.5760 | 7.095 |
| 0.80 | 0.8408 | 12.572 |
| 0.95 | 0.9640 | 18.720 |

La copertura e' **conservativa**, com'e' strutturale sui conteggi (la
discretezza impedisce di centrare il nominale) e come gia' osservato in Fase 4.

## 7. Le cinque linee, tutte

| linea | tasso_base | brier_modello | brier_baseline | brier_tasso_base | vince_su_baseline | vince_su_tasso_base |
|---:|---:|---:|---:|---:|---|---|
| 8.5 | 0.7678 | 0.1579 | 0.1710 | 0.1787 | si | si |
| 10.5 | 0.6196 | 0.2037 | 0.2205 | 0.2360 | si | si |
| 12.5 | 0.4536 | 0.2084 | 0.2300 | 0.2482 | si | si |
| 14.5 | 0.3194 | 0.1817 | 0.1993 | 0.2178 | si | si |
| 16.5 | 0.2023 | 0.1385 | 0.1508 | 0.1616 | si | si |

**Vince su tutte e cinque**, contro il baseline migliore e contro il tasso base.
Una linea sola sarebbe un risultato scelto: e' la lezione della Fase 4, che
misuro' su quattro soglie invece che su una.

## 8. I segmenti, e il terzile alto

| segmento | valore | n | mae_modello | mae_baseline | delta | bias | vince |
|---|---|---:|---:|---:|---:|---:|---|
| campo | casa | 1640 | 3.7878 | 4.0122 | 0.2243 | -0.0491 | si |
| campo | trasferta | 1638 | 3.3586 | 3.7146 | 0.3560 | 0.2221 | si |
| terzile lambda | basso | 1093 | 3.1111 | 3.4731 | 0.3620 | 0.0978 | si |
| terzile lambda | medio | 1092 | 3.4167 | 3.7708 | 0.3541 | 0.1627 | si |
| terzile lambda | alto | 1093 | 4.1921 | 4.3463 | 0.1543 | -0.0012 | si |
| meta' stagione | 1a meta' | 1400 | 3.5827 | 3.8989 | 0.3163 | 0.1713 | si |
| meta' stagione | 2a meta' | 1878 | 3.5664 | 3.8370 | 0.2706 | 0.0231 | si |

**Vince in tutti e sette**, e il terzile alto e' la riga interessante. Sui tiri
in porta la Fase 4 aveva trovato che il modello **perde** li' (+0,0031 di
Brier), ed era lo shrinkage: le squadre che tirano molto sono quelle che il
ritorno alla media penalizza. Sui tentativi il margine si **attenua**
(0.1543 contro
0.3620 nel terzile basso) ma **non si
inverte**.

E' la stessa firma, piu' debole: la compressione della ridge esiste anche qui —
e' la quinta misura dello stesso effetto dopo Fase 3, Fase 4, 6A e R3 — ma su un
bersaglio piu' informativo non arriva a rovesciare il confronto. **Non va
"corretta"**: sarebbe la quinta volta che il progetto rifiuta quella strada.

Il MAE cresce col lambda (terzile basso 3.111,
alto 4.192) ed e' atteso: su conteggi
la varianza cresce con la media.

## 9. I ratings — una descrizione, non una previsione

| team | attack | defence | tentativi_attesi_trasferta |
|---|---:|---:|---:|
| Juventus | 0.2902 | -0.1347 | 14.236 |
| Inter | 0.2686 | -0.1928 | 13.932 |
| Atalanta | 0.1808 | -0.0161 | 12.761 |
| Como | 0.1496 | -0.2727 | 12.369 |
| Roma | 0.0639 | -0.1939 | 11.353 |
| Napoli | 0.0588 | -0.1500 | 11.296 |
| AC Milan | 0.0575 | -0.0170 | 11.281 |
| Bologna | 0.0304 | -0.1515 | 10.979 |
| Fiorentina | 0.0296 | 0.1146 | 10.970 |
| Torino | -0.0225 | 0.1159 | 10.413 |

*(prime dieci; la tabella intera e' in `fase12_v1_ratings.csv`)*

**Il fit usa tutta la stagione**, quindi serve a leggere il modello e non a
validarlo. La scala e' quella di `fig5` — **avversario medio in trasferta**, non
campo neutro: la Fase 6A dovette documentarlo dopo averlo scoperto, e qui si
dichiara subito. Vantaggio del campo **x1.260**.
Il **Como** sta a 12.37 tentativi attesi (posizione 4 su 20).

## 10. Che cosa V1 consegna

1. **A V2**: la cache `fase12_walkforward_tiri.parquet` con `lam` e, accanto,
   `sot` e `shots` osservati — cosi' V2 non deve rifare nessun join. E `r` dello
   strato 1, che la composizione riusa invece di ristimare.
2. **A V3**: lo stesso perimetro e gli stessi baseline, su cui i predittori da
   dati evento vanno testati con la potenza dichiarata.
3. **A V4**: il modello che il ponte `previsione(squadra, avversario, campo)`
   interroghera'.

## 11. Domande aperte

1. **Il fattore di cluster previsto da V0 (0,807) non descrive il confronto
   appaiato** (0.925-0.994 osservato). La correlazione
   fra i **valori** dei due lati e' forte e negativa; quella fra gli **errori**
   e' debole. Perche' lo sia non e' stato misurato.
2. **`r` e' assunto costante fra squadre e fra stagioni.** La sovradispersione
   potrebbe dipendere dal livello — le squadre che tirano molto potrebbero
   essere anche piu' variabili — e non e' stato guardato.
3. **Il totale di partita** e' la linea di mercato piu' comune e `lam_subiti` e'
   gia' nella cache, ma la correlazione negativa misurata da V0 dice che **non
   e' la somma di due indipendenti**: serve la congiunta, che sui tentativi non
   e' misurata. E' la stessa domanda che R1 ha risolto sui gol.
4. **Il `gamma` della 2021-22 non e' confrontabile** con gli altri quattro (e' la
   prima stagione di ritorno del pubblico). Dentro stagione non fa danno; una
   media dei cinque sarebbe una media di due regimi.
