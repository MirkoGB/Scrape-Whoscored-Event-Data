# Fase 12 / Blocco V2 — la precisione, e la composizione

> Generato da `scripts/run_fase12_v2.py` il 2026-08-14.
> **Non tocca la rete.** Unica scrittura sotto `data/`: la cache
> `fase12_strato2.parquet`, rigenerabile con `--force`.

## 0. Le due domande, che e' facile confondere

```
strato 2   sot_ij | shots_ij ~ Binomiale(shots_ij, p_ij)
           logit(p_ij) = mu_p + a_i + d_j + g_p * casa
```

1. **La quota e' prevedibile meglio di un numero unico?** (§2) Si misura
   condizionando su `shots` osservati — e **non e' una previsione di `sot`**,
   perche' quando si prevede i tentativi non sono ancora stati tirati.
2. **La marginale composta batte il modello diretto sui tiri in porta?** (§4)
   Questa e' la previsione vera, e il concorrente non e' un baseline stupido: e'
   il modello che la Fase 2 ha gia' pubblicato.

Il criterio e' stato scritto **prima** di guardare i numeri:

> la gerarchia si adotta al posto del modello DIRETTO sui tiri in porta solo se (a) la marginale composta non perde in MAE appaiato oltre il proprio MDE, e (b) il segno del margine e' lo stesso in almeno 4 stagioni su 5. A parita' si tiene il modello diretto, che ha meno parti.

## 1. I lati: decisione dell'utente, non esito del criterio

`[DECISO 2026-08-13]` dall'utente: **la difesa entra nello strato 2**.

Il criterio di V0, applicato meccanicamente, diceva *solo attacco*: sul lato
difensivo il test di dispersione rifiuta (z = +2,51) ma `tau` resta **sotto il
proprio MDE tarato** (1,39 contro 1,59 punti). **Il criterio non e' stato
riscritto** e `tentativi.verdetto_strato2()` continua a rispondere
`['attacco']`.

La decisione aveva un argomento — la seconda strada, indipendente e piu'
potente, rifiuta nettamente (GLM, F = 2,83, p = 2,3e-06) — e aveva un costo
dichiarato. **Questo blocco lo misura invece di assumerlo**, ed e' §3.

## 2. La quota, condizionata su `shots` osservati

| modello | n | ll_per_riga | mae_quota | brier_quota | corr | guadagno_per_riga | t_vs_lega |
|---|---:|---:|---:|---:|---:|---:|---:|
| strato 2 (attacco+difesa) | 3276 | -7.97980 | 0.12167 | 0.02435 | 0.0880 | -0.01483 | -2.81 |
| strato 2 (solo attacco) | 3276 | -7.97132 | 0.12056 | 0.02409 | 0.0717 | -0.00635 | -1.64 |
| p_lega (walk-forward) | 3276 | -7.96497 | 0.11996 | 0.02389 | -0.0064 | 0.00000 |  |

**Il risultato e' negativo, e va letto per quello che e': l'eterogeneita' che V0
ha trovato esiste, ma NON e' predittiva.**

V0 aveva misurato una `tau` di 2,12 punti di quota fra squadre, con z = +5,91 e
un nullo simulato: quel risultato **non e' smentito**. Ma era una misura
*descrittiva*, su squadre-stagione complete (~475 tentativi ciascuna). Qui il
modello deve dire la quota di **una** squadra-partita (~12,6 tentativi) prima
che si giochi, e li' il segnale non sopravvive al rumore: il modello ha
correlazione positiva con la quota vera (+0.0880 e
+0.0717 contro -0.0064 del baseline) e
**verosimiglianza peggiore**, cioe' e' troppo estremo per quanto poco sa.

E' la stessa forma del risultato della Fase 2 sugli otto predittori: un effetto
reale in campione che fuori campione non paga.

## 3. Il costo della decisione sulla difesa, misurato

| | |
|---|---:|
| guadagno in log-verosimiglianza per riga | **-0.00849** |
| MDE a potenza 80% | 0.01089 |
| `t` per cluster | **-2.21** |
| MAE della composta, solo attacco | 1.70788 |
| MAE della composta, attacco + difesa | 1.71572 |
| la difesa paga | **no** |

**La difesa non paga: costa.** Il guadagno e' negativo e il `t` supera la soglia
**nella direzione sbagliata** (-2.21), cioe' il peggioramento non e'
rumore. Sulla marginale composta il MAE peggiora di
0.00784 (-1.43).

Questo era il rischio dichiarato prima di eseguire — «un effetto sotto il MDE
del test primario puo' valere zero fuori campione» — e la misura dice che vale
**meno** di zero. Il meccanismo e' leggibile: venti coefficienti difensivi in
piu' stimati su un segnale che il test primario non riusciva a risolvere sono
venti modi di adattarsi al rumore.

**Il criterio di V0 aveva ragione**, e lo si sa adesso che e' misurato.

## 4. La marginale composta contro il modello diretto

| modello | n | mae | bias | corr | calib_slope | calib_z_vs_1 | brier |
|---|---:|---:|---:|---:|---:|---:|---:|
| gerarchia (composta) | 3276 | 1.7157 | -0.0071 | 0.3947 | 0.9083 | -2.58 | 0.2131 |
| gerarchia (solo attacco) | 3276 | 1.7079 | -0.0061 | 0.3992 | 0.9751 | -0.66 | 0.2127 |
| gerarchia con p_lega | 3276 | 1.7176 | 0.0082 | 0.3941 | 1.0758 | 1.80 | 0.2141 |
| modello DIRETTO su sot | 3276 | 1.7181 | -0.0053 | 0.3888 | 0.9886 | -0.29 | 0.2140 |

| variante | mae | mae_diretto | delta_mae | t_per_cluster | mde | batte_il_diretto | dentro_il_mde |
|---|---:|---:|---:|---:|---:|---|---|
| gerarchia (composta) | 1.71572 | 1.71814 | 0.00242 | 0.599 | 0.00996 | no | si |
| gerarchia (solo attacco) | 1.70788 | 1.71814 | 0.01026 | 1.689 | 0.01735 | no | si |
| gerarchia con p_lega | 1.71756 | 1.71814 | 0.00058 | 0.046 | 0.02258 | no | si |

| stagione | n | mae_gerarchia | mae_diretto | delta | gerarchia_vince |
|---|---:|---:|---:|---:|---|
| 2021-2022 | 647 | 1.8212 | 1.8266 | 0.0054 | si |
| 2022-2023 | 650 | 1.6687 | 1.6588 | -0.0099 | no |
| 2023-2024 | 660 | 1.6884 | 1.7042 | 0.0158 | si |
| 2024-2025 | 660 | 1.6667 | 1.6659 | -0.0007 | no |
| 2025-2026 | 659 | 1.7350 | 1.7365 | 0.0015 | si |

**Nessuna variante batte il modello diretto.** La migliore e' `solo attacco`
(delta MAE +0.01026, t = 1.69), che
resta sotto la soglia e **dentro il proprio MDE**: il test esclude differenze
grandi, non differenze piccole.

E il segno **non e' stabile**: la gerarchia vince in
3 stagioni su 5, e il criterio ne chiedeva almeno 4.

## 5. La composizione, verificata dove la risposta e' nota

| verifica | esito |
|---|---|
| forma chiusa `== NB2(lam*p, r)` | passa |
| la PMF chiusa somma a 1 | 1.0000000000 |
| convoluzione a `rho -> 0` coincide con la chiusa | passa (max scarto 6.4e-07) |
| a `rho = 0,05` la convoluzione **diverge** dalla chiusa | passa |
| la convoluzione conserva la media | 4.1250 contro 4.1250 |

**Una precisazione a V0.** Il report di V0 diceva che «la forma chiusa del
thinning non e' valida cosi' com'e', perche' `p` varia fra squadre». **E'
impreciso**: la forma chiusa vale **riga per riga** anche quando `p` cambia fra
righe, purche' dentro la riga sia un numero e non una variabile aleatoria — che
e' il caso di un `p_ij` prodotto da un modello.

Cio' che la romperebbe e' la variabilita' di `p` **dentro** la squadra-partita,
cioe' la sovradispersione residua che V0 ha misurato (`rho` intraclasse 0,0083)
e che nessun effetto di squadra cattura. `pmf_composta(rho > 0)` e' quella
strada, e si rifiuta di usare la scorciatoia.

## 6. Il rapporto delle dispersioni — la coerenza, falsificata

| | |
|---|---:|
| `r` su **tentativi** | 20.275 |
| `r` su **tiri in porta** | 33.130 |
| rapporto | **1.634** |
| IC95 bootstrap | [1.157, 2.759] |
| compatibile con 1 | **no** |

**Sotto il thinning le due `r` dovrebbero essere uguali, e non lo sono.**
L'intervallo non contiene 1, quindi la coerenza interna della gerarchia e'
**falsificata** — ed e' un risultato, non un difetto di stima.

Il segno e' quello **opposto** a quello che l'eterogeneita' della quota
prevedrebbe: `r_sot > r_shots` significa che i tiri in porta sono **meno**
sovradispersi di quanto il thinning imponga, non piu'. Una variabilita' extra
della quota li renderebbe piu' dispersi, quindi non e' quella la causa.

**Non e' stata spiegata**, ed e' la prima domanda aperta. Il candidato piu'
economico e' che il thinning non sia indipendente dal volume — chi tira molto
tira anche da posizioni diverse — ma misurarlo e' un altro blocco.

Ne segue una conseguenza operativa gia' applicata: `marginale_composta` usa `r`
**ricostruito walk-forward su `sot`** e non ereditato dallo strato 1. Ereditarlo
sarebbe piu' coerente con la gerarchia, ma imporrebbe una predittiva troppo
larga sulle code e farebbe apparire la gerarchia peggiore per una ragione che
non e' il suo lambda.

## 7. Il verdetto, applicato meccanicamente

**MODELLO DIRETTO (MENO PARTI)**

| condizione | valore | soddisfatta |
|---|---:|---|
| non perde oltre il MDE | delta +0.00242 contro MDE 0.00996 | si |
| segno stabile (>= 4 stagioni su 5) | 3/5 | no |
| **adotta la gerarchia** | | **no** |

**La gerarchia non si adotta, e non perche' sia peggiore: perche' non e'
migliore.** A parita' si tiene il modello con meno parti, ed e' la regola scritta
prima. Il modello diretto sui tiri in porta resta quello che V4 usera' per `sot`.

**Cio' che V1 ha prodotto resta intatto e non dipende da questo esito**: lo
strato del volume batte il baseline migliore per t = 9,63 ed e' il modello che
risponde alla domanda dell'utente. La gerarchia era il tentativo di ottenere
*anche* i tiri in porta dallo stesso oggetto, e il tentativo dice di no.

## 8. Domande aperte

1. **Il rapporto delle dispersioni (1,63) non e' spiegato**, ed e' il numero piu'
   interessante del blocco: dice che la composizione non e' internamente
   coerente, nel verso opposto a quello che l'eterogeneita' della quota
   prevedrebbe.
2. **La quota potrebbe essere prevedibile da altro che dall'identita' della
   squadra** — posizione dei tiri, tipo di azione, xG per tiro. `xg_per_shot` e'
   gia' in `team_match` ed e' fra gli otto candidati di V3: se la precisione ha
   un predittore, e' li' che si vedrebbe.
3. **`alpha` dello strato 2 e' dichiarato (6.0), non scelto.** La sensibilita' e'
   riportata da `sensibilita_alpha()` e non e' stata usata per ottimizzare:
   sceglierlo sul bersaglio sarebbe il vincolo 1 violato.
4. **Il ramo `rho > 0` della composizione non e' mai stato usato in previsione.**
   Esiste, e' verificato, e servirebbe se un blocco futuro volesse la predittiva
   completa di `sot` invece del solo lambda.
