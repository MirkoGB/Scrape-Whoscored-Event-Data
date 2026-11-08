# Fase 12 / Blocco V0 — il perimetro del bersaglio

> Generato da `scripts/run_fase12_v0.py` il 2026-08-13.
> **Non tocca la rete e non scrive niente sotto `data/`.** Legge `team_match`
> delle cinque stagioni, che esiste dalla Fase 1 e dal blocco E0.
> **Non stima nessun modello predittivo**: conta, misura, e decide la forma di
> V1 e V2. E' l'analogo di R0 per questa fase.

## 0. Che cosa questo blocco decide

La Fase 12 modella i **tentativi** (`team_match.shots`), non i tiri in porta, e
per **qualsiasi** squadra. Il disegno e' gerarchico:

```
strato 1 (volume)      shots_ij ~ NB2(lambda_ij, r)
strato 2 (precisione)  sot_ij | shots_ij ~ Binomiale(shots_ij, p_ij)
```

V0 risponde a una domanda sola: **`p_ij` varia davvero fra squadre, o e' un
numero solo piu' rumore binomiale?** Se non varia, lo strato 2 collassa a
`sot = shots * p_lega`, la composizione diventa esatta e il modello ha meno
parti — che non e' un fallimento, e' un risultato piu' parsimonioso.

Il criterio e' stato scritto **prima** di guardare i numeri:

> lo strato 2 si STIMA solo se (a) almeno uno dei tre lati rifiuta alla soglia di Sidak per k=3 con il nullo SIMULATO, e (b) il tau stimato supera il proprio MDE all'80%. Altrimenti p = p_lega stimata sul solo passato, lo strato 2 e' UN NUMERO, e la marginale di sot e' NB2(lambda*p_lega, r) in forma chiusa.

## 1. L'universo, e le verifiche che non passano da nessun modello

| controllo | valore | atteso | passa |
|---|---:|---:|---|
| righe totali | 3778 |  | si |
| sot > shots (impossibile) | 0 | 0 | si |
| shots negativi | 0 | 0 | si |
| shots nulli (NaN) | 0 | 0 | si |
| righe a zero tentativi | 2 |  | si |
| quota definita dove shots > 0 | 3776 | 3776 | si |
| quota NaN dove shots == 0 | 2 | 2 | si |
| stagioni | 5 | 5 | si |
| squadre-stagione | 100 |  | si |
| partite | 1889 |  | si |

**`sot <= shots` su tutte e 3778 le righe.** Non e' pedanteria: se cadesse,
la binomiale dello strato 2 sarebbe *impossibile*, non malamente specificata.

**Le 2 righe a zero tentativi esistono e restano**: entrano nei livelli e non
nei rapporti, dove la quota e' `NaN` e non zero. Uno zero le farebbe entrare
nelle medie come squadre che non hanno mai centrato la porta.

**`matchId` e' unico fra le cinque stagioni** (1889 distinti,
0 collisioni). Serve a V1 e non a V0, ed e' il motivo per cui
sta qui: `build_predictors` aggancia il lato difensivo con
`merge(on=["matchId", "opponent"])`, e un `matchId` ripetuto farebbe arrivare il
predittore dell'avversario **da un'altra stagione** senza che nulla lo dica.
Nessuno l'aveva verificato.

## 2. Il livello si muove, ed e' il motivo del disegno di V1

| stagione | n | shots | shots_sd | sot | quota_in_porta | var_su_media | deriva_pct |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2021-2022 | 748 | 13.032 | 5.800 | 4.441 | 0.3408 | 2.581 | 0.00 |
| 2022-2023 | 750 | 12.679 | 5.008 | 4.123 | 0.3252 | 1.978 | -2.71 |
| 2023-2024 | 760 | 12.764 | 4.866 | 4.149 | 0.3250 | 1.855 | -2.05 |
| 2024-2025 | 760 | 12.122 | 5.056 | 4.033 | 0.3327 | 2.109 | -6.98 |
| 2025-2026 | 760 | 12.314 | 5.262 | 4.034 | 0.3276 | 2.249 | -5.51 |

Il livello dei tentativi scende del **5.5%**
fra la prima e l'ultima stagione, non monotono. La quota in porta invece **non
si muove** (0.3250-0.3408),
coerente con quanto la Fase 7 aveva gia' misurato sulle categorie di tiro.

**Ne segue il disegno di V1: walk-forward DENTRO la stagione**, con le sole
righe valutate impilate. Cosi' `mu` assorbe il livello di quella stagione per
costruzione, e non servono ne' un effetto di stagione ne' la standardizzazione
di E1 — che governa il confronto fra unita' grezze di stagioni diverse, cosa
che qui non avviene mai. E' la stessa scelta di E3 sui gol, per la stessa
ragione.

## 3. Il cluster di partita — quanto valgono davvero 3.778 righe

| stagione | partite | corr | ic95_basso | ic95_alto | fattore_se |
|---|---:|---:|---:|---:|---:|
| 2021-2022 | 374 | -0.3763 | -0.4601 | -0.2858 | 0.7898 |
| 2022-2023 | 375 | -0.3391 | -0.4257 | -0.2463 | 0.8130 |
| 2023-2024 | 380 | -0.3089 | -0.3971 | -0.2149 | 0.8313 |
| 2024-2025 | 380 | -0.3156 | -0.4034 | -0.2220 | 0.8273 |
| 2025-2026 | 380 | -0.4036 | -0.4845 | -0.3158 | 0.7723 |

**Il segno e' NEGATIVO, e non era l'attesa.** Si temeva una correlazione
positiva — ritmo, punteggio e arbitro condivisi — che avrebbe gonfiato ogni `t`
appaiato di questa fase. Misurata, vale **-0.349**, con lo
stesso segno in tutte e cinque le stagioni e intervalli che non contengono lo
zero.

Il meccanismo e' piu' forte di quello atteso: **il possesso e' a somma
costante**. Chi domina tira molto e lascia tirare poco, quindi i tentativi dei
due lati si sottraggono invece di sommarsi.

La conseguenza va nel verso **favorevole** —
`sqrt(1 - 0.349) = 0.807`, cioe' gli errori
standard appaiati sono piu' **piccoli** del nominale — e va applicata lo stesso:
un fattore favorevole non dichiarato resta un numero sbagliato. V1 riportera'
entrambi i `t`, per riga e per cluster.

## 4. Le linee, dichiarate prima

> multipli interi + 0,5 (convenzione di mercato), passo 2, centrati sul multiplo di 2 piu' vicino alla media pubblicata di tentativi per squadra-partita delle cinque stagioni (12,58); estesi finche' il tasso base resta dentro [0,10 - 0,90].

| linea | tasso_base | sd_dalla_media | dentro_regola |
|---:|---:|---:|---|
| 8.5 | 0.7721 | -0.7826 | si |
| 10.5 | 0.6220 | -0.3990 | si |
| 12.5 | 0.4590 | -0.0155 | si |
| 14.5 | 0.3216 | 0.3681 | si |
| 16.5 | 0.2065 | 0.7516 | si |

| bersaglio | media | sd | linea | sd_dalla_media |
|---|---:|---:|---:|---:|
| tiri in porta | 4.155 | 2.350 | 2.5 | -0.704 |
| tiri in porta | 4.155 | 2.350 | 3.5 | -0.279 |
| tiri in porta | 4.155 | 2.350 | 4.5 | 0.147 |
| tiri in porta | 4.155 | 2.350 | 5.5 | 0.572 |
| tentativi | 12.581 | 5.215 | 8.5 | -0.783 |
| tentativi | 12.581 | 5.215 | 10.5 | -0.399 |
| tentativi | 12.581 | 5.215 | 12.5 | -0.015 |
| tentativi | 12.581 | 5.215 | 14.5 | 0.368 |
| tentativi | 12.581 | 5.215 | 16.5 | 0.752 |

Le linee dei tentativi coprono **lo stesso intervallo** in deviazioni standard
che `validate.LINES` copre sui tiri in porta (circa da -0,8 a +0,8): e' lo
**stesso esperimento** su un bersaglio riscalato, che e' la sola forma in cui i
numeri della Fase 12 e della Fase 4 si possano mettere accanto. Non sono
identiche riga per riga — le linee di mercato sono mezzi interi e la scala e'
diversa — ma la copertura si', ed e' quella che conta. Un passo di 1 tiro invece
di 2 darebbe cinque linee a 0,19 sd l'una dall'altra, cioe' cinque volte lo
stesso test.

**Le linee dei tiri in porta NON si toccano**: la marginale composta di V2 si
valuta su `validate.LINES` inalterata. Inventarne di nuove renderebbe questa
fase non confrontabile con la Fase 4.

## 5. Perche' `phi = 1,101` non risponde alla domanda

E' l'errore che questo blocco esiste per non commettere. `recording_stability`
ha misurato che la quota in porta e' stabile *fra stagioni e fra mesi*, e ha
riportato `phi = 1,101`. Ma quel `phi` e' la sovradispersione delle unita'
**squadra-partita**: contiene rumore di partita, effetto squadra ed effetto
avversario tutti insieme, e non li separa. «La quota di campionato non si muove
fra stagioni» e «la quota non varia fra squadre» sono **due nulli diversi**, e
il secondo non era mai stato testato.

| livello | unita | gdl | n_medio | sd_binomiale_quota | phi_osservato | tau_mde | tau_mde_punti |
|---|---:|---:|---:|---:|---:|---:|---:|
| squadra-partita | 3776 | 3771 | 12.59 | 0.13256 | 1.0958 | 0.03172 | 3.17 |
| squadra-stagione | 100 | 95 | 475.30 | 0.02157 | 2.1327 | 0.01296 | 1.30 |

A ~12,6 tentativi la deviazione standard binomiale della quota vale
**13.3 punti**: una differenza fra squadre di 2-3
punti ci sparisce dentro, e `phi = 1,10` **e' quel rumore**. A ~475 tentativi
scende a **2.2 punti** e la componente di squadra emerge.
Il livello sbagliato ha un MDE **2.4 volte peggiore**.

## 6. Il nullo va generato, non letto da una tabella

Il `chi2` teorico assume binomialita' **esatta** dentro la squadra-stagione. Ma
la sovradispersione di partita esiste — `phi = 1.0958`,
cioe' correlazione intraclasse **0.00827** — e un test che
la ignorasse la scambierebbe per eterogeneita' di squadra: sarebbe **garantito
di rifiutare**. Il nullo giusto e' «`p` non varia fra squadre, ma varia da
partita a partita quanto gia' sappiamo», realizzato come beta-binomiale a
livello squadra-partita e poi aggregato.

Che la differenza non sia accademica si legge nella tabella qui sotto: il `p`
del chi-quadro teorico e quello simulato non si somigliano.

## 7. Il test, e la sua taratura

| lato | unita | gdl | phi_osservato | phi0_simulato | z | soglia_sidak | rifiuta | p_simulato | p_chi2_teorico | tau_punti | tau_mde_analitico | tau_mde_punti | supera_mde |
|---|---:|---:|---:|---:|---:|---:|---|---:|---:|---:|---:|---:|---|
| attacco | 100 | 95 | 2.133 | 1.165 | 5.91 | 2.121 | si | 0.0005 | 0.000000 | 2.12 | 0.0138 | 1.61 | si |
| difesa | 100 | 95 | 1.574 | 1.161 | 2.51 | 2.121 | si | 0.0100 | 0.000306 | 1.39 | 0.0138 | 1.59 | no |
| campo | 10 | 5 | 1.659 | 2.222 | -0.57 | 2.121 | no | 0.6862 | 0.140736 | 0.00 | 0.0107 | 1.08 | no |

**La taratura e' cio' che rende leggibile il risultato**, ed e' l'unico modo di
distinguere «il test ha trovato eterogeneita'» da «il test rifiuta sempre».
Attese dichiarate prima: ~5% alla riga `tau = 0` (che e' la **dimensione**, non
zero), ~80% al MDE, monotona in mezzo.

| lato | tau_punti | phi_medio | potenza |
|---|---:|---:|---:|
| attacco | 0.00 | 1.169 | 0.028 |
| attacco | 0.50 | 1.218 | 0.048 |
| attacco | 1.00 | 1.406 | 0.275 |
| attacco | 1.30 | 1.548 | 0.528 |
| attacco | 1.50 | 1.668 | 0.710 |
| attacco | 1.75 | 1.861 | 0.920 |
| attacco | 2.00 | 2.081 | 0.979 |
| attacco | 2.50 | 2.589 | 1.000 |
| attacco | 3.00 | 3.198 | 1.000 |
| difesa | 0.00 | 1.170 | 0.021 |
| difesa | 0.50 | 1.220 | 0.053 |
| difesa | 1.00 | 1.399 | 0.283 |
| difesa | 1.30 | 1.545 | 0.522 |
| difesa | 1.50 | 1.670 | 0.735 |
| difesa | 1.75 | 1.865 | 0.925 |
| difesa | 2.00 | 2.082 | 0.981 |
| difesa | 2.50 | 2.587 | 1.000 |
| difesa | 3.00 | 3.184 | 1.000 |
| campo | 0.00 | 2.224 | 0.039 |
| campo | 0.50 | 3.260 | 0.216 |
| campo | 1.00 | 6.472 | 0.760 |
| campo | 1.30 | 9.401 | 0.912 |
| campo | 1.50 | 11.929 | 0.962 |
| campo | 1.75 | 14.922 | 0.982 |
| campo | 2.00 | 19.320 | 0.998 |
| campo | 2.50 | 28.784 | 0.999 |
| campo | 3.00 | 40.844 | 0.999 |

**La taratura ha corretto il MDE, ed e' il motivo per cui esiste.** Il MDE
analitico vale 1.38 punti, ma a quel `tau` la potenza
**vera** e' ~53%, non 80%: la formula assume `phi` normale con deviazione
standard costante, mentre sotto l'alternativa la sd cresce. Il MDE pubblicato e'
quello **tarato** (1.61 punti), che e' un terzo piu' grande.
Un MDE sbagliato nella direzione comoda e' peggio che non averlo.

A `tau = 0` la frequenza di rifiuto vale 0.021-0.039,
sotto il 5% nominale e coerente con la soglia di Sidak per `k = 3` (~1,7% per
test singolo): **il test non e' liberale**.

## 8. La strada di controllo, indipendente dalla prima

| confronto | gdl_num | gdl_den | delta_devianza | phi | F | p |
|---|---:|---:|---:|---:|---:|---:|
| solo stagione -> + campo | 1 | 3718 | 3.25 | 1.0722 | 3.028 | 0.081904 |
| + campo -> + attacco | 26 | 3718 | 85.82 | 1.0722 | 3.078 | 0.000000 |
| + attacco -> + difesa | 26 | 3718 | 78.98 | 1.0722 | 2.833 | 0.000002 |

Due strade che concordano sono un risultato; una sola e' un'asserzione. La GLM
binomiale in quasi-verosimiglianza stima `p` come **coefficienti** invece che
come dispersione, quindi ha piu' potenza — ed e' la ragione per cui sul lato
difesa rifiuta mentre il test di dispersione mette l'effetto sotto il proprio
MDE. Le due cose non sono in contraddizione: l'effetto difensivo **c'e' ed e'
piccolo**, e il test di dispersione dichiara di non poterlo risolvere.

**Sul lato campo il disegno iniziale era sbagliato**, e l'esecuzione lo ha
corretto: si era scritto che il campo fosse «il piu' potente dei tre» perche' ha
un `n` enorme per cella. Ha pero' **10 unita' e 5 gradi di liberta'**, quindi il
test di dispersione li' e' quasi cieco. La strada buona per il campo e' il test
F, che infatti lo misura: F = 3.03, p = 0.0819.

## 9. Il thinning — la premessa della gerarchia, verificata dove la risposta e' nota

Se `N ~ NB2(lambda, r)` e `S | N ~ Bin(N, p)` con `p` costante, allora
`S ~ NB2(lambda*p, r)`: **stesso `r`**, media scalata. E' la proprieta' su cui
poggia tutta la gerarchia — senza, la marginale dei tiri in porta non avrebbe
forma chiusa e V2 dovrebbe convolvere numericamente.

Verificata su 200,000 estrazioni generate, con `dispersion.fit_r` del
progetto e non con una formula scritta apposta: media attesa
4.1552 contro osservata 4.1592
(+0.098%), `r` vera 30 contro stimata
31.13 (+3.8%).

## 10. Il verdetto, applicato meccanicamente

**MODELLO DI PRECISIONE** — lati adottati: **attacco**.

| lato | rifiuta | supera il MDE | adottato |
|---|---|---|---|
| attacco | si | si | **si** |
| difesa | si | no | no |
| campo | no | no | no |

**La precisione e' una proprieta' di chi tira, non di chi difende e non del
campo.** Il lato attacco ha `tau = 2.12` punti di quota contro un
MDE tarato di 1.61, con z = +5.91 e p simulato
0.0005. Il lato difesa rifiuta il test ma **resta sotto il proprio
MDE** (1.39 contro 1.59): l'effetto c'e', il GLM
lo vede, e questo test dichiara di non poterlo risolvere. Il campo non rifiuta.

Le cinque squadre-stagione piu' e meno precise, per dare la scala di cio' di cui
si parla:

| stagione | chiave | n | k | p_hat | p_stagione | residuo_pearson |
|---|---|---:|---:|---:|---:|---:|
| 2021-2022 | Lazio | 446 | 190 | 0.4260 | 0.3408 | 3.80 |
| 2024-2025 | Fiorentina | 447 | 175 | 0.3915 | 0.3327 | 2.64 |
| 2022-2023 | Lazio | 438 | 170 | 0.3881 | 0.3252 | 2.81 |
| 2023-2024 | AC Milan | 562 | 214 | 0.3808 | 0.3250 | 2.82 |
| 2023-2024 | Atalanta | 544 | 207 | 0.3805 | 0.3250 | 2.76 |
| 2022-2023 | Lecce | 418 | 113 | 0.2703 | 0.3252 | -2.39 |
| 2025-2026 | Fiorentina | 489 | 131 | 0.2679 | 0.3276 | -2.81 |
| 2024-2025 | Verona | 375 | 99 | 0.2640 | 0.3327 | -2.82 |
| 2025-2026 | Lecce | 373 | 97 | 0.2601 | 0.3276 | -2.78 |
| 2025-2026 | Parma Calcio 1913 | 407 | 104 | 0.2555 | 0.3276 | -3.10 |

### Che cosa V0 consegna a V1 e V2

1. **A V1**: il walk-forward va **dentro la stagione**; `build_predictors` va
   eseguito **per stagione separatamente** (sul concatenato, settembre 2023
   userebbe maggio 2023 con peso 0,57); `matchId` e' unico, quindi il join del
   lato difensivo e' sicuro; il fattore di cluster vale
   **0.807** e va applicato a ogni errore standard appaiato;
   le linee sono `(8.5, 10.5, 12.5, 14.5, 16.5)`.
2. **A V2**: **lo strato 2 si stima**, ma con **il solo lato attacco**. La forma
   chiusa del thinning **non e' valida** cosi' com'e', perche' `p` varia fra
   squadre: V2 deve avere entrambe le strade — chiusa e convoluzione numerica —
   e un test che le fa coincidere dove `p` e' costante.

## 11. Domande aperte

1. **Il lato difesa e' al limite** (1.39 punti contro un MDE di
   1.59) e le due strade lo trattano diversamente. V2 lo
   includera' o no: la decisione va presa **prima** di guardarne l'effetto
   predittivo, altrimenti e' un iperparametro scelto sul bersaglio.
2. **La correlazione negativa fra i due lati non e' stata spiegata, solo
   misurata.** Il possesso a somma costante e' la spiegazione compatibile piu'
   economica, ma non e' stata verificata — servirebbe rifare la misura
   condizionando sul possesso, e non e' in questo blocco.
3. **`tau` e' assunto costante fra stagioni.** Con 100 unita' complessive
   stimarne cinque separati non e' possibile, ed e' la stessa forma del limite
   che R1 dichiara su `rho`.
4. **Il totale di partita** (`lambda_casa + lambda_trasferta`) e' la linea di
   mercato piu' comune, e la correlazione negativa misurata qui dice che **non
   e' la somma di due indipendenti**. Serve la congiunta, che sui tentativi non
   e' misurata. E' una domanda per V1, o un blocco a se'.
