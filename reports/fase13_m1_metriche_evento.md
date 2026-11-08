# Fase 13 / Blocco M1 — metriche avanzate da dati evento

Modulo `sot/metriche_evento.py`, test `tests/test_fase13_m1.py` (23).
**Nessuna richiesta di rete. Nessuna stima**: il blocco conta e misura, come R0
e V0. **Nessun numero pubblicato e' cambiato.**

Chiesto dall'utente il 2026-08-14 insieme all'apertura di G2: tocchi per zona
(campo in cinque zone, aree di rigore incluse) e passaggi progressivi.

---

## 1. Le cinque zone sono una partizione, e la prova non passa dai dati veri

    area_dif     x <= 15.71  e  20.35 <= y <= 79.65
    terzo_dif    x <  33.33  e  non area_dif
    terzo_medio  33.33 <= x < 66.67
    terzo_off    x >= 66.67  e  non area_off
    area_off     x >= 84.29  e  20.35 <= y <= 79.65

La verifica gira su una **griglia fitta che copre tutto il campo**, non sui
tocchi osservati: un buco in un angolo che la Serie A 2025-26 non ha mai
visitato resterebbe invisibile sui dati veri e comparirebbe su un altro
campionato — cioe' esattamente dove la Fase 13 sta andando.

Sui dati veri: **468.883 tocchi, zero senza zona**, quote che sommano a 1 con
scarto massimo **2,2e-16** (precisione macchina).

| zona | tocchi/squadra-partita | quota |
|---|---:|---:|
| `area_dif` | 63,6 | 0,1091 |
| `terzo_dif` | 133,8 | 0,2214 |
| `terzo_medio` | 276,6 | 0,4430 |
| `terzo_off` | 121,6 | 0,1926 |
| `area_off` | 21,3 | 0,0339 |

**La geometria non e' duplicata**: `BOX_X`, `BOX_Y_LO`, `BOX_Y_HI` e
`FINAL_THIRD_X` si **importano** da `features.py`, e un test verifica che non
siano state ridefinite. L'area di rigore del progetto e' una sola, per la stessa
ragione per cui la definizione di tiro in porta sta solo in `shots.py`.

---

## 2. Il vincolo 7 dentro una fonte sola: "passaggio riuscito" ha due derivazioni

Misurato sulla 2025-26, su 357.679 passaggi:

| | |
|---|---:|
| `passAccurate = True` ma **non** `Successful` | **0** |
| `Successful` ma **non** `passAccurate` | **17.440** |
| senza **nessuno** dei due flag | **29.741 (8,3%)** |
| lunghezza media **con** flag | 18,0 m |
| lunghezza media **senza** flag | **22,2 m** |

`passAccurate` e' un sottoinsieme **stretto** di `Successful`: annidato, non
discordante. Ma l'8,3% non marcato e' **piu' lungo**, coerente col fatto che
Opta classifichi cross, lanci e piazzati in flag separati che
`io_events.BOOL_COLS` non conserva.

> **Si usa `outcomeType`.** Usare `passAccurate` scarterebbe in silenzio il 6%
> dei passaggi riusciti **sbilanciato verso i lunghi**, cioe' esattamente la
> popolazione che definisce un progressivo. Sarebbe un errore **sistematico**,
> non rumore. Un test pretende che l'annidamento regga: se
> `accurate_ma_non_successful` smettesse di essere zero, la scelta andrebbe
> rifatta.

---

## 3. I progressivi: tre letture, tenute separate

`[DECISO dall'utente — 2026-08-14]` il progressivo e' **avanzamento in x >= 10 m
E riuscito**. Le altre due letture restano **colonne affiancate e mai fuse**
(vincolo 7): sono tre grandezze diverse, e quale sia «il» progressivo e' una
decisione, non una misura.

| colonna | definizione | per squadra-partita |
|---|---|---:|
| `prog_tentati` | avanzamento in x >= 10 m | 137,8 |
| **`prog_riusciti`** | ...**e riuscito** — **la scelta** | **88,9** |
| `prog_per_distanza` | lunghezza >= 10 m e diretto in avanti | 231,6 |

**Nessuna delle tre coincide con i "progressive passes" dei fornitori standard**
(~40-50 per squadra-partita), che usano l'avanzamento **relativo alla distanza
dalla porta**. Non e' un difetto: e' una definizione diversa, dichiarata invece
che presentata come la stessa cosa.

**I 10 metri sono una soglia NOMINALE** (vincolo 5, accanto al numero e non in
fondo): valgono 9,52 unita' di `x` e poggiano sul campo regolamentare 105 x 68 m
gia' assunto da `features.py`. La norma FIFA ammette 100-110 x 64-75, e gli
stadi veri variano.

Altre colonne del blocco: `ingressi_area` (9,5 — arriva in area **partendo da
fuori**, altrimenti ogni scarico interno conterebbe), `metri_progressione`
(931,1 — progressione **netta**, i passaggi all'indietro entrano col segno) e
`completamenti_profondi_cross_inclusi` (10,3).

> **Quel nome lungo e' il punto.** La *deep completion* standard **esclude i
> cross**, e in `events_slim` **non c'e' nessun flag di cross**. Chiamarla
> `deep_completions` avrebbe prodotto una tabella dell'ordine di grandezza
> giusto e del contenuto sbagliato — che e' esattamente cio' che `passFreekick`
> ha fatto in E4. Il flag sta nei `qualifiers`, che costano una rilettura dei
> 1.889 CSV.

---

## 4. Il gate di deriva di E1, sulle cinque stagioni

3.778 squadre-partita. Soglia dichiarata: **5%**.

| colonna | deriva | |
|---|---:|---|
| `metri_progressione` | 23,62% | oltre |
| `metri_per_passaggio` | 19,88% | oltre |
| `completamenti_profondi_cross_inclusi` | 14,16% | oltre |
| `ingressi_area` | 11,84% | oltre |
| `tocchi_area_off` | 8,40% | oltre |
| `tocchi_terzo_off` | 7,26% | oltre |
| **`prog_tentati`** | **6,81%** | **oltre** |
| `quota_tocchi_area_off` | 5,06% | oltre |
| `tocchi_terzo_dif` | 4,94% | passa |
| **`prog_riusciti`** | **4,56%** | **passa** |
| `quota_tocchi_terzo_off` | 4,34% | passa |
| `prog_per_distanza` | 3,22% | passa |
| `tocchi_terzo_medio` | 3,01% | passa |
| `lunghezza_media_m` | 2,82% | passa |
| `quota_prog_riusciti` | 2,15% | passa |
| `quota_passaggi_riusciti` · `precisione_progressivi` | 2,09% | passa |
| `quota_tocchi_terzo_medio` | 1,81% | passa |
| `tocchi_area_dif` | 1,40% | passa |

**Due letture, e la prima non era prevista.**

1. **La definizione scelta dall'utente passa il gate, quella senza il filtro
   no**: `prog_riusciti` 4,56% contro `prog_tentati` 6,81%. Il filtro sulla
   riuscita non e' solo una preferenza — **stabilizza la grandezza fra
   stagioni**. La decisione del 2026-08-14 risulta la piu' robusta delle tre
   *dopo* averla presa, non prima, e questo va detto in quest'ordine.
2. **Le quote passano sistematicamente dove i conteggi falliscono**, che e'
   esattamente cio' che la regola di E1 prevede: il livello se ne va, la
   dispersione fra squadre resta.

`prog_riusciti` scende da 92,8 (2021-22) a 88,9 (2025-26), monotona salvo
l'ultimo anno. **E' coerente con la caduta gia' documentata dei tentativi**
(13,03 → 12,31, −5,5%, verifica di stabilita' del criterio): si gioca piu'
corto, non si annota diversamente.

> **Conseguenza operativa per la Fase 13.** Le otto colonne oltre soglia **non
> entrano grezze** in un modello che attraversa stagioni — e a maggior ragione
> in uno che attraversa **campionati**, dove non c'e' ragione di aspettarsi una
> deriva minore. Entrano in forma `_rel = x/m_s - 1`, oppure si usa la loro
> versione in quota, che il gate ammette gia'.

---

## 5. Cio' che questo blocco NON ha fatto

**Non ha testato se queste metriche predicano qualcosa.** E' un altro blocco, e
va disegnato con la **potenza dichiarata prima**: i predittori da dati evento
sono gia' stati scartati **tre volte** (Fase 2 sui tiri in porta, 6D nei regimi
acerbi, V3 sui tentativi — il piu' potente in termini relativi). Un quarto
negativo cieco non aggiungerebbe niente.

Due ragioni per aspettarsi comunque un esito diverso, entrambe da mettere alla
prova e non da assumere: il **bersaglio e' nuovo** (i gol, dove E3 ha mostrato
che l'avversario conta molto di piu' che sui tiri), e **cinque campionati
moltiplicano le righe per cinque** — anche se V3 ha gia' mostrato che in unita'
assolute questo **peggiora** il MDE invece di migliorarlo, e che l'unita' da
guardare e' il MDE **relativo al guadagno del modello sul baseline**.

**`tocchi_area_off` non e' una candidata nuova**: e' `box_touches`, gia' fra le
otto bocciate. Sta qui perche' completa la partizione, non perche' meriti un
quarto test.

---

## 6. Domande aperte

1. **Il flag di cross** sta nei `qualifiers` e costerebbe una rilettura dei
   1.889 CSV. Finche' non c'e', la deep completion resta dichiarata diversa
   dallo standard e non confrontabile con numeri pubblicati altrove.
2. **Le dimensioni vere degli stadi** non sono nel repository: la soglia dei
   10 m e' nominale, e l'errore che ne segue non e' stato quantificato.
3. **I *carry* progressivi non ci sono.** Richiedono di ricostruire il legame
   fra eventi consecutivi dello stesso giocatore, che e' la stessa ricostruzione
   dichiarata di E4 sul legame passaggio chiave -> tiro: fattibile, ma e' una
   scelta di modellazione e non una lettura.
4. **La deriva e' misurata fra stagioni della SERIE A**, non fra campionati.
   Quella misura si potra' fare solo quando i dati di G2 saranno in casa, ed e'
   la prima cosa da guardare quando ci saranno.
