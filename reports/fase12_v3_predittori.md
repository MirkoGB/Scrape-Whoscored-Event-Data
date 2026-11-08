# Fase 12 / Blocco V3 — i predittori, ritestati sui tentativi

> Generato da `scripts/run_fase12_v3.py` il 2026-08-14.
> **Non tocca la rete.** Unica scrittura sotto `data/`: la cache
> `fase12_v3_predittori.parquet`, rigenerabile con `--force`.

## 0. Che cosa fa questo blocco, e perche' non ha un modulo

Gli **stessi otto candidati** di `walkforward.CANDIDATES` — possesso, field
tilt, PPDA (due lati), tocchi in area, distanza media di tiro, xG per tiro (due
lati) — furono scartati **sui tiri in porta** dalla Fase 2 e riesaminati dalla
6D, che ne dichiaro' la potenza: **28% nel regime maturo, 11% nell'acerbo**.

Qui si rifa' lo stesso test su un **bersaglio diverso** e su un perimetro **cinque
volte piu' grande**. `sot/predictor_power.py` e' stato parametrizzato su
`target`: V3 **non ha un modulo proprio**, ed e' un'eccezione dichiarata alla
regola «1 blocco = 1 modulo» — duplicare quel modulo violerebbe «una definizione
in un posto solo», che e' la ragione per cui `shots.py` e `perimetro.py`
esistono.

**Il default non si e' mosso**: `confronto(prev, r)` e
`confronto(prev, r, target="sot")` danno la stessa tabella bit per bit, e i
numeri di `reports/phase6_predittori.csv` si riproducono a 1e-12
(`poss_att` maturo, t = 1.4200797158768528). Due test lo bloccano.

> **Il difetto che la parametrizzazione poteva introdurre**, e che un test
> blocca: `_fit` costruiva `TeamModel` **senza** `target`. Siccome `y_in` era
> gia' del bersaglio giusto, il parametro sarebbe *sembrato* funzionare mentre
> il modello veniva stimato su `sot` e valutato sui tentativi. Il test pretende
> che la verosimiglianza in campione **cambi** al cambiare del target.

## 1. Il perimetro, e il guadagno di potenza

I predittori sono costruiti **una stagione per volta**. Sul concatenato
`pre_match_ewm` raggruppa per `team`, che e' un nome e si ripete fra stagioni:
la prima giornata di settembre 2023 riceverebbe una media a decadimento
dominata da maggio 2023 (peso 0,57 a 110 giorni), cioe' da una rosa che non
esiste piu'. E' l'argomento di E3 sul walk-forward, applicato un livello piu' in
basso. La firma e' verificabile e un test la usa: **la prima partita di ogni
stagione deve avere predittori nulli**.

| regime | righe nella 6D | righe qui | fattore |
|---|---:|---:|---:|
| maturo | 660 | 3278 | **5.0x** |
| acerbo | 100 | 500 | **5.0x** |
| acerbo disgiunto | 40 | 200 | **5.0x** |

**Il regime «acerbo disgiunto» era il risultato negativo piu' debole del
progetto** — 40 righe, MDE enorme — ed e' quello che questo blocco puo'
finalmente attaccare.

## 2. Il risultato: nessuno passa, in nessun regime

| regime | predittore | n | d_riga | se_riga | t | mde_riga | tenuto |
|---|---|---:|---:|---:|---:|---:|---|
| acerbo | tilt_att | 500 | 0.00408 | 0.00645 | 0.633 | 0.01831 | no |
| acerbo | poss_att | 500 | 0.00232 | 0.00640 | 0.362 | 0.01818 | no |
| acerbo | box_att | 500 | 0.00204 | 0.00778 | 0.262 | 0.02212 | no |
| acerbo | dist_att | 500 | 0.00092 | 0.00606 | 0.151 | 0.01723 | no |
| acerbo | ppda_def | 500 | -0.00063 | 0.00914 | -0.069 | 0.02596 | no |
| acerbo | xgps_att | 500 | -0.00101 | 0.00836 | -0.121 | 0.02377 | no |
| acerbo | ppda_att | 500 | -0.00631 | 0.00591 | -1.068 | 0.01679 | no |
| acerbo | xgps_def | 500 | -0.00772 | 0.00698 | -1.107 | 0.01983 | no |
| maturo | poss_att | 3278 | 0.00284 | 0.00191 | 1.485 | 0.00543 | no |
| maturo | tilt_att | 3278 | 0.00246 | 0.00192 | 1.286 | 0.00544 | no |
| maturo | box_att | 3278 | -0.00038 | 0.00186 | -0.204 | 0.00528 | no |
| maturo | ppda_att | 3278 | -0.00084 | 0.00161 | -0.523 | 0.00458 | no |
| maturo | xgps_att | 3278 | -0.00106 | 0.00190 | -0.555 | 0.00540 | no |
| maturo | xgps_def | 3278 | -0.00081 | 0.00110 | -0.743 | 0.00312 | no |
| maturo | dist_att | 3278 | -0.00123 | 0.00144 | -0.856 | 0.00409 | no |
| maturo | ppda_def | 3278 | -0.00353 | 0.00186 | -1.902 | 0.00527 | no |
| acerbo disgiunto | xgps_att | 200 | 0.00747 | 0.01267 | 0.589 | 0.03600 | no |
| acerbo disgiunto | dist_att | 200 | 0.00034 | 0.00817 | 0.042 | 0.02322 | no |
| acerbo disgiunto | ppda_def | 200 | 0.00019 | 0.01474 | 0.013 | 0.04189 | no |
| acerbo disgiunto | xgps_def | 200 | -0.00703 | 0.01472 | -0.478 | 0.04183 | no |
| acerbo disgiunto | ppda_att | 200 | -0.00537 | 0.01116 | -0.481 | 0.03171 | no |
| acerbo disgiunto | box_att | 200 | -0.01027 | 0.01072 | -0.958 | 0.03045 | no |
| acerbo disgiunto | poss_att | 200 | -0.01565 | 0.00779 | -2.009 | 0.02214 | no |
| acerbo disgiunto | tilt_att | 200 | -0.01408 | 0.00567 | -2.484 | 0.01611 | no |

**Zero candidati tenuti su 24 combinazioni.** E' il terzo test indipendente
con lo stesso esito — Fase 2 sui tiri in porta, 6D nei regimi acerbi, V3 sui
tentativi — e stavolta il MDE e' molto piu' stretto.

Nel regime maturo il massimo vale **t = 1.485** (poss_att),
e su otto candidati un massimo del genere ha `p = 0.435`: e' quanto ci si
aspetta sotto l'ipotesi nulla. **`t_atteso_massimo(8)` vale
1.4236**, cioe' il massimo osservato e' *sotto* il valore atteso
del massimo di otto normali standard.

## 3. La potenza, dichiarata — e un errore di lettura corretto per strada

| regime | MDE per riga | potenza contro l'alternativa 0.00284 |
|---|---:|---:|
| acerbo | 0.01679 | 6% |
| maturo | 0.00312 | 72% |
| acerbo disgiunto | 0.01611 | 7% |

L'alternativa e' **l'effetto per riga piu' grande mai prodotto dagli otto
candidati in questo blocco** (0.00284, poss_att nel
maturo), con l'errore standard piu' favorevole di ciascun regime. E' la stessa
costruzione della 6D: non la media degli otto, che sarebbe dominata dai
candidati a varianza minuscola e descriverebbe un test mai fatto.

### I MDE di due bersagli diversi non sono confrontabili in unita' assolute

Questo blocco era partito dall'aspettativa che cinque volte le righe dessero un
MDE piu' stretto. **E' falso in unita' assolute**, e va detto:

| regime | MDE 6D (tiri in porta) | MDE V3 (tentativi) |
|---|---:|---:|
| maturo | 0,00282 | 0.00312 |
| acerbo | 0,00668 | 0.01679 |
| acerbo disgiunto | 0,00483 | 0.01611 |

Il MDE **peggiora**, nonostante le righe siano cinque volte tante. Il motivo e'
la scala del bersaglio: la log-verosimiglianza Poisson di un conteggio con media
12,6 ha una varianza per riga molto maggiore di uno con media 4,0, e il
guadagno di `sqrt(5)` non la compensa.

**L'unita' confrontabile e' adimensionale**: quanto vale il MDE rispetto a cio'
che il modello guadagna sul baseline migliore, **nella stessa unita'** di
log-verosimiglianza per riga. Un MDE pari al 10% di quel guadagno significa che
il test vede un predittore che valga un decimo del modello intero.

| regime | n | mde_riga | guadagno_modello_su_baseline | mde_in_quota_del_guadagno |
|---|---:|---:|---:|---:|
| acerbo | 500 | 0.01679 | 0.12680 | 0.1325 |
| maturo | 3278 | 0.00312 | 0.13616 | 0.0229 |
| acerbo disgiunto | 200 | 0.01611 | 0.15701 | 0.1026 |

| regime | quota nella 6D | quota qui | |
|---|---:|---:|---|
| maturo | 0,118 | **0.023** | **5x piu' sensibile** |
| acerbo | 0,159 | **0.132** | poco meglio |
| acerbo disgiunto | 0,057 | **0.103** | **peggio** |

**Nel regime maturo il guadagno di potenza c'e' ed e' grande**: il test vede
predittori che valgono il 2,3% del modello intero, contro l'11,8% della 6D.
**Nel regime acerbo disgiunto no**, ed e' l'opposto di cio' che ci si aspettava:
li' il modello stacca i baseline **piu'** che nel maturo (0.157
contro 0.136), quindi il
denominatore cresce piu' del numeratore.

**Resta la lettura della 6D, e va ripetuta**: un test negativo esclude effetti
grandi, non effetti piccoli. Che nessun candidato passi non dimostra che il loro
effetto sia zero — dimostra che se c'e', e' sotto il MDE dichiarato.

## 4. Due candidati PEGGIORANO, e nel regime dove ci si aspettava il contrario

| regime | predittore | n | d_riga | t | mde_riga |
|---|---|---:|---:|---:|---:|
| acerbo disgiunto | poss_att | 200 | -0.01565 | -2.009 | 0.02214 |
| acerbo disgiunto | tilt_att | 200 | -0.01408 | -2.484 | 0.01611 |

Nel regime **acerbo disgiunto** — le primissime giornate, dove l'effetto attacco
e' piu' debolmente identificato e dove un predittore incrementale avrebbe *piu'*
spazio — `tilt_att` e `poss_att` non solo non aiutano: **danneggiano oltre la
soglia**, con `t` sotto −2.

E' l'osservazione piu' interessante del blocco, e la 6D non poteva farla: con 40
righe l'errore standard era tre volte piu' grande e quei `t` sarebbero stati
attorno a −0,8. La direzione e' coerente con il meccanismo che la Fase 2 aveva
dedotto e che la 6D ha reso visibile nei due termini dell'obiettivo: **un
predittore collineare con l'effetto attacco compra una riduzione della penalita'
ridge e paga in adattamento**. Dove l'effetto attacco e' acerbo, la sostituzione
e' peggiore.

Nel regime **maturo** invece nessun candidato scende sotto −2 (il piu' negativo e' ppda_def a t = -1.902).

## 5. Il contesto: il modello contro i baseline, dentro ogni regime

| regime | modello | n | mae | ll_per_riga | delta_vs_modello | delta_ll_vs_modello |
|---|---|---:|---:|---:|---:|---:|
| acerbo | Poisson ridge att/dif/casa | 500 | 3.6610 | -3.027460151723254 | 0.0000 | 0.0 |
| acerbo | media squadra + campo | 500 | 3.9320 | -3.1542583933295263 | 0.2710 | 0.1267982416062723 |
| acerbo | media squadra | 500 | 3.9270 | -3.14143853227202 | 0.2660 | 0.11397838054876619 |
| acerbo | media casa/trasferta | 500 | 3.9362 | -3.1236650359865177 | 0.2752 | 0.09620488426326368 |
| acerbo | media campionato | 500 | 3.8512 | -3.0905197170118037 | 0.1902 | 0.06305956528854972 |
| maturo | Poisson ridge att/dif/casa | 3278 | 3.5733 | -2.9641821954799696 | 0.0000 | 0.0 |
| maturo | media squadra + campo | 3278 | 3.8634 | -3.1003427721677626 | 0.2901 | 0.1361605766877929 |
| maturo | media squadra | 3278 | 3.9755 | -3.152441145061463 | 0.4021 | 0.18825894958149325 |
| maturo | media casa/trasferta | 3278 | 4.0132 | -3.168635600354574 | 0.4398 | 0.2044534048746045 |
| maturo | media campionato | 3278 | 4.1129 | -3.2205864938352966 | 0.5395 | 0.25640429835532697 |
| acerbo disgiunto | Poisson ridge att/dif/casa | 200 | 3.5196 | -2.9766453699251794 | 0.0000 | 0.0 |
| acerbo disgiunto | media squadra + campo | 200 | 3.8684 | -3.133660344398088 | 0.3488 | 0.1570149744729088 |
| acerbo disgiunto | media squadra | 200 | 3.7612 | -3.081747515521401 | 0.2417 | 0.10510214559622177 |
| acerbo disgiunto | media casa/trasferta | 200 | 3.7998 | -3.056903481663771 | 0.2802 | 0.08025811173859143 |
| acerbo disgiunto | media campionato | 200 | 3.6507 | -2.967785886297092 | 0.1311 | -0.008859483628087528 |

**E' la premessa del blocco, verificata invece che assunta.** Se nel regime
acerbo il modello non staccasse i baseline, un predittore incrementale avrebbe
piu' spazio per esistere — ed e' proprio l'ipotesi da testare. I baseline
vengono dal walk-forward di V1, gia' calcolati per stagione, invece di essere
ricalcolati poolando.

## 6. La consistenza fra stagioni

| predittore | 2021-2022 | 2022-2023 | 2023-2024 | 2024-2025 | 2025-2026 | positivi | max_assoluto |
|---|---:|---:|---:|---:|---:|---:|---:|
| box_att | -2.593 | -0.055 | -0.572 | 1.001 | 0.423 | 2 | 2.593 |
| dist_att | -1.745 | -0.106 | 0.242 | -0.185 | -0.196 | 1 | 1.745 |
| poss_att | -1.726 | -0.328 | 1.376 | 2.042 | 1.190 | 3 | 2.042 |
| ppda_att | -2.344 | 1.022 | 0.689 | 0.607 | -1.025 | 3 | 2.344 |
| ppda_def | -3.317 | -0.733 | -0.840 | -0.452 | -0.957 | 0 | 3.317 |
| tilt_att | -1.202 | 1.357 | 0.571 | 1.645 | 0.411 | 4 | 1.645 |
| xgps_att | -1.395 | -0.181 | -0.397 | 0.930 | 1.509 | 2 | 1.509 |
| xgps_def | 0.066 | -0.105 | -2.146 | 0.570 | -1.721 | 2 | 2.146 |

Cinque `t` con lo stesso segno sarebbero un'evidenza diversa da un `t` pooled
dello stesso valore. **Nessun candidato ha cinque segni positivi**, il che
toglie l'ultima lettura possibile di un pooled vicino a zero — che qualche
stagione nasconda un effetto reale annullato dalle altre.

## 7. Che cosa V3 conclude

**Gli otto predittori da dati evento non aggiungono niente al modello di
squadra, nemmeno sul bersaglio che li favorisce di piu'.** I tentativi sono la
grandezza piu' vicina a cio' che possesso e field tilt misurano — molto piu' dei
tiri in porta — e nemmeno li' passano.

Il meccanismo resta quello della Fase 2, ora misurato su tre bersagli: **gli
effetti attacco/difesa con decadimento assorbono gia' tutto cio' che una media
mobile di squadra puo' portare**. Un predittore che dice «questa squadra ha
avuto molto possesso nelle ultime partite» sta dicendo, con piu' rumore, «questa
squadra e' forte», che il coefficiente d'attacco gia' sa.

> **Trappola per le sessioni future.** Questo e' il **terzo** esito negativo
> sullo stesso insieme di candidati, e il piu' potente dei tre. Non va
> "sistemato" reintroducendone uno perche' il suo `t` e' il piu' alto: su otto
> candidati un massimo di 1.48 e' esattamente quanto ci si aspetta sotto
> l'ipotesi nulla, e il blocco lo calcola invece di lasciarlo intuire.

## 8. Domande aperte

1. **Il tetto in campione non e' stato rifatto multi-stagione.** `confronto` e'
   chiamato con `df=None`: la versione con i due numeri in campione della 6D
   richiederebbe un fit poolato che attraversa l'estate, cioe' esattamente cio'
   che V1 ha deciso di non fare. Il tetto della 6D vale per un altro bersaglio e
   **non si eredita**.
2. **Perche' `tilt_att` e `poss_att` danneggino nel regime acerbo** e' coerente
   col meccanismo della sostituzione ridge, ma non e' stato misurato **qui** nei
   due termini dell'obiettivo: `PP.penalita` lo farebbe, e vorrebbe lo stesso fit
   in campione del punto 1.
3. **I candidati sono gli otto dichiarati, e non e' stato allargato l'insieme**
   (decisione dell'utente). Candidati mirati al **volume** invece che alla
   qualita' — ritmo di gioco, corner, recuperi alti, stato del punteggio — non
   sono stati provati, e sarebbero un blocco a se' con la propria famiglia da
   correggere.
4. **La precisione potrebbe avere un predittore anche se il volume non ce l'ha**
   (domanda aperta di V2): `xg_per_shot` e' gia' fra gli otto e sul volume non
   passa, ma non e' stato testato sul **logit della quota**, che e' un altro
   bersaglio.
