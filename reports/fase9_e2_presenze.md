# Fase 9 / Blocco E2 — le presenze

> Generato da `scripts/run_fase9_e2.py` il 2026-08-07.
> Nessuna richiesta di rete.

**Il limite che non si aggira, e che vale per ogni numero di questo report: gli
infortuni non sono nei dati.** Sono la componente piu' grossa dell'assenza e
questo blocco non li prevede. Non e' una nota a pie' di pagina: e' la ragione per
cui il tetto raggiungibile qui e' molto piu' basso del divario oracolo.

## In breve

Il blocco produce **tre risultati negativi e due positivi**, e i negativi sono il
contenuto.

| | esito |
|---|---|
| squalifiche come sottrazione di presenze | **−1,9%** del divario oracolo: peggiorano |
| predittori d'impiego da dati evento | **+0,20%** del divario, sotto l'MDE di 1,53% |
| numero di maglia | **nessun contributo** distinguibile, e la versione utile non e' costruibile |
| il cartellino come **predittore** (coda §4) | **±0,03%** del divario, con MDE 0,04-0,12%: confutato |
| la **quotazione QI** come predittore (§5) | **+1.49%** del divario, t = 2.91: **il primo che passa** |
| la regola delle squalifiche in se' | **verificata**, accordo 96-99% contro baseline 13-16% |
| il pavimento di esposizione a zero | **confermato da una misura**, non da un'opinione |

## 1. Le squalifiche, che non si stimano

Regola deterministica dai cartellini, con tre assunzioni dichiarate: cinque
ammonizioni una giornata col contatore che riparte; l'ammonizione del doppio
giallo non entra nel cumulo; **l'espulsione vale una giornata, ed e' un limite
inferiore** — la durata vera la decide il giudice sportivo e non e' nei dati.

Il taglio sui destinatari **non e' quello dei minuti**: le 85 espulsioni del
2025-26 danno 65 uomini tolti dal campo, ma per le squalifiche contano tutte
quelle a **giocatori**, panchinari compresi. Il numero giusto e' **68**.

| stagione | squalifiche | cumulo_gialli | doppio_giallo | rosso_diretto | giornate_totali | giocatori_colpiti | maturate_non_scontate |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2021-2022 | 233 | 142 | 46 | 45 | 233 | 176 | 7 |
| 2022-2023 | 202 | 138 | 26 | 38 | 202 | 154 | 12 |
| 2023-2024 | 217 | 150 | 33 | 34 | 217 | 180 | 1 |
| 2024-2025 | 181 | 107 | 34 | 40 | 181 | 154 | 10 |
| 2025-2026 | 164 | 101 | 22 | 41 | 164 | 140 | 9 |

### La verifica, che non passa da nessun modello

Se la regola dice che un giocatore salta la partita successiva della sua squadra,
quel giocatore non deve comparire fra i convocati. E' falsificabile e si controlla
riga per riga.

| stagione | squalifiche_scontate | accordo | accordo_calendario_intero | baseline_assenza | errori | errori_su_squadra_bucata | quota_righe_squadra_bucata |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2021-2022 | 233 | 0.914 | 0.977 | 0.145 | 20 | 17 | 0.429 |
| 2022-2023 | 202 | 0.936 | 0.962 | 0.136 | 13 | 8 | 0.351 |
| 2023-2024 | 217 | 0.963 | 0.963 | 0.126 | 8 | 0 | 0.000 |
| 2024-2025 | 181 | 0.994 | 0.994 | 0.156 | 1 | 0 | 0.000 |
| 2025-2026 | 164 | 0.988 | 0.988 | 0.141 | 2 | 0 | 0.000 |

**Il baseline e' il punto** (vincolo 6): le stesse persone, nelle giornate in cui
**non** sono squalificate, mancano dalla distinta il **13-16%** delle volte. Il
96-99% di accordo va letto contro quello, non contro zero.

**Il residuo ha una causa, ed e' stata cercata invece che addotta.** L'accordo
grezzo scende al 91,4% nel 2021-22, e non perche' la regola funzioni peggio: **17
errori su 20** cadono su squadre a cui WhoScored manca almeno una partita, mentre
quelle squadre sono solo il 42,9% delle righe. `team_match_idx` numera le partite
**presenti nei dati**, quindi se la successiva al cartellino e' fra le 12 assenti
alla fonte, `idx + 1` e' la partita dopo — in cui il giocatore e' gia' rientrato.
E' un difetto dell'indice, non della regola: sulle squadre col calendario intero
l'accordo sta fra **96,2% e 99,4%** ovunque.

### Le due fonti dei cartellini, una contro l'altra (vincolo 7)

La fonte dei voti porta `ammonizioni` ed `espulsioni` per conto suo. Non si
sceglie la comoda: si misurano.

| stagione | righe | gialli_ws | gialli_fc | accordo_gialli | esp_ws | esp_fc | accordo_espulsioni |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2021-2022 | 467 | 1668 | 1717 | 0.874 | 90 | 90 | 0.987 |
| 2022-2023 | 454 | 1637 | 1704 | 0.852 | 69 | 67 | 0.987 |
| 2023-2024 | 432 | 1567 | 1609 | 0.931 | 67 | 65 | 0.981 |
| 2024-2025 | 449 | 1399 | 1430 | 0.929 | 80 | 83 | 0.984 |
| 2025-2026 | 441 | 1366 | 1397 | 0.923 | 68 | 68 | 0.991 |

**Le espulsioni concordano** (98-99%), le **ammonizioni no** (85-93%), e la fonte
dei voti ne conta sistematicamente **di piu'**. L'accordo e' peggiore proprio
nelle due stagioni con partite mancanti, quindi una parte e' il buco
dell'archivio — ma **non tutto**: nel 2023-24, che e' completo, restano 42
ammonizioni di scarto. **La causa residua non e' identificata e non e' stata
ipotizzata.**

### Quanto vale l'assunzione piu' fragile

| giornate_per_rosso | giornate_totali | per_stagione |
|---:|---:|---:|
| 1 | 997 | 199.4 |
| 2 | 1356 | 271.2 |
| 3 | 1715 | 343.0 |

### E ora il numero per cui il blocco esisteva

| variante | righe | mae | divario_chiuso_pct |
|---|---:|---:|---:|
| modello completo | 2678 | 61.42 | 0.00 |
| meno squalifiche attese (dal solo passato) | 2678 | 61.45 | -0.05 |
| meno squalifiche note (ORACOLO dei cartellini) | 2678 | 62.50 | -1.92 |
| presenze note (ORACOLO, il pavimento) | 2678 | 5.56 | 100.00 |

**Le squalifiche non chiudono niente del divario: lo allargano.** Anche
nell'oracolo, cioe' conoscendo i cartellini della stagione bersaglio, sottrarre le
giornate di squalifica **peggiora** il MAE dell'1,9%.

**Il perche' e' misurato, non addotto:**

| gruppo | righe | presenze_attese | presenze_osservate | bias |
|---|---:|---:|---:|---:|
| squalificato almeno una volta | 647 | 21.22 | 27.20 | -5.98 |
| mai squalificato | 2031 | 18.46 | 12.55 | 5.91 |

Chi prende squalifiche e' chi gioca — cinque ammonizioni non le accumula un
panchinaro — e su quei giocatori il modello d'asta **gia' sottostima** le presenze
di sei, perche' lo shrinkage al ruolo tira verso il basso chi sta in alto.
Togliere altre giornate a una previsione gia' troppo bassa allontana.

> **L'inversione che il meccanismo suggerisce: il cartellino non e' una presenza
> in meno, e' il segnale che quel giocatore gioca.** Come sottrazione e' dannoso;
> come predittore d'impiego avrebbe il segno opposto — **ed e' stata provata in
> quella forma nella coda §4, dove non regge.** La lettura del meccanismo resta
> valida; la sua conseguenza operativa no.

## 2. Lo strato distinta

**Costa quasi zero, e non e' un'aspettativa ma una misura**: `JerseyNumber` e
`CaptainPlayerId` stanno nella stessa lista di qualifier da cui `minutes.squads()`
gia' estrae `PlayerPosition`. Presenti sul **100%** delle 3.778 righe
`FormationSet` di tutte e cinque le stagioni, lunghezze sempre allineate a
`InvolvedPlayers`, **estrazione in 0,3 secondi** dai Parquet gia' in cache. I
piazzati di E4, che vogliono `qualifiers` sugli eventi normali, costerebbero
invece una rilettura dei 1.889 CSV.

Le triple sono **3972**, la stessa granularita' di E1. **11** hanno piu' di un
numero nella stessa stagione e si risolvono con la **prima distinta**, non con la
moda pesata sui minuti: la moda userebbe i minuti della stagione per costruire un
predittore il cui unico pregio e' di esistere **prima** che quei minuti siano
giocati. Eccole tutte:

| stagione | teamId | playerId | jersey | n_numeri |
|---|---:|---:|---:|---:|
| 2021-2022 | 71 | 414264 | 6 | 2 |
| 2021-2022 | 72 | 431666 | 21 | 2 |
| 2021-2022 | 73 | 428502 | 19 | 2 |
| 2021-2022 | 85 | 423858 | 23 | 2 |
| 2021-2022 | 86 | 145940 | 14 | 2 |
| 2021-2022 | 2889 | 389954 | 30 | 2 |
| 2022-2023 | 80 | 17949 | 83 | 2 |
| 2022-2023 | 87 | 469594 | 55 | 2 |
| 2023-2024 | 75 | 388505 | 34 | 2 |
| 2024-2025 | 73 | 536868 | 27 | 2 |
| 2024-2025 | 278 | 91169 | 1 | 2 |

Il numero cambia in **250** casi su **1421** permanenze nello stesso club.

### La fascia dei portieri non e' quella dei portieri

Era la verifica richiesta: la fascia `1/12/22` duplica il `role_code`?

| fascia_maglia | righe | ruolo_dominante | quota_dominante |
|---|---:|---|---:|
| cifra_singola | 691 | CEN | 0.440 |
| dieci | 91 | ATT | 0.516 |
| oltre_45 | 456 | CEN | 0.452 |
| portiere_classico | 174 | GK | 0.460 |
| undici_25 | 931 | CEN | 0.422 |
| ventisei_45 | 616 | CEN | 0.427 |

Il ruolo dominante di `portiere_classico` e' GK al **46%**, cioe' non domina
affatto. Il dettaglio dice perche':

| jersey | righe | GK | DIF | CEN | ATT |
|---:|---:|---:|---:|---:|---:|
| 1 | 69 | 1.000 | 0.000 | 0.000 | 0.000 |
| 12 | 28 | 0.179 | 0.286 | 0.464 | 0.071 |
| 22 | 77 | 0.078 | 0.390 | 0.364 | 0.169 |
| 10 | 91 | 0.000 | 0.000 | 0.484 | 0.516 |

**La 1 e' portiere nel 100% dei casi; la 12 nel 18% e la 22 nell'8%.** Il folklore
«1/12/22 sono i tre portieri» e' falso in questi dati. E solo il 35% dei portieri
porta uno di quei tre numeri.

**La fascia non e' stata ridefinita**, ed e' il punto: si e' scoperto *dopo* aver
dichiarato la partizione, e cambiarla adesso sarebbe adattarla al campione su cui
poi la si valuta. La sua **eterogeneita' e' il risultato**.

### Dove il ruolo tace, il numero c'e'

**1013 triple su 3972** (25.5%) non hanno **nessun**
ruolo: sono i convocati che non sono mai scesi in campo, `role_code == 5` in ogni
distinta. Per loro il ruolo non esiste — e **tutte e 1013 hanno un numero di
maglia**. E' l'argomento a favore della feature detto nel modo piu' stretto
possibile.

## 3. Il modello d'impiego

### Prima, il difetto che rende inutilizzabile la versione interessante della maglia

Il numero e' assegnato **in agosto**, e questo era l'argomento: e' noto al momento
della previsione anche per chi al nuovo club non ha storia. Ma la nostra **unica
fonte del numero e' la distinta di una partita**. Chi non viene mai convocato non
ha nessuna distinta, quindi non ha nessun numero.

Misurato sulle quattro transizioni: fra i quotati con una distinta nella stagione
bersaglio le presenze medie sono **19,1-19,3**; fra quelli senza sono **0,0-0,3**.
**La sola disponibilita' della feature e' la risposta.** Si usa quindi il numero
della **stagione precedente**, come il capitano — e il costo e' esattamente il
caso che si voleva coprire: per chi cambia club, il numero disponibile e' quello
del club vecchio.

> Il numero d'agosto **sarebbe acquisibile** — lo pubblicano i club e sta nei
> listoni — ma non e' nel repository. E' una domanda aperta con una risposta nota,
> non un limite dei dati evento.

### La valutazione, sulle stesse quattro transizioni del modello d'asta

| variante | righe | mae | divario_chiuso_pct |
|---|---:|---:|---:|
| modello completo | 2678 | 61.42 | 0.00 |
| impiego (senza maglia) | 2678 | 61.32 | 0.20 |
| impiego + maglia | 2678 | 61.32 | 0.19 |
| presenze note (ORACOLO, il pavimento) | 2678 | 5.56 | 100.00 |

**Lo 0,20% del divario oracolo**, e la maglia non aggiunge niente (0,19%, cioe'
un'inezia peggio). Sulle presenze il MAE e' 9,906 contro 9,904 del modello d'asta:
identico. La correlazione sale da 0,438 a 0,461, e non basta.

**La potenza e' dichiarata**, come in 6D: differenza appaiata 0.110 di MAE,
errore standard 0.306, **t = 0.36**. L'MDE a potenza 80% vale 0.857 di MAE,
cioe' il **1.53%** del divario. Quindi il test **non** avrebbe visto un
effetto sotto l'1,5%: il risultato negativo esclude effetti grandi, non effetti
piccoli, e va letto cosi'.

**Perche' non aiuta e' leggibile**: il modello d'asta usa gia' le presenze passate
del giocatore, e `quota_titolare`, `quota_convocato`, capitano e ruolo instabile
sono un altro modo di dire la stessa cosa. E' lo stesso meccanismo della Fase 2 —
i predittori evento erano gia' coperti dagli effetti attacco/difesa — su un
bersaglio diverso.

### Il pavimento di esposizione: la decisione era giusta, e adesso c'e' il numero

| pavimento | variante | mae | divario_chiuso_pct |
|---:|---|---:|---:|
| 0 | impiego (senza maglia) | 61.315 | 0.196 |
| 0 | impiego + maglia | 61.321 | 0.186 |
| 450 | impiego (senza maglia) | 61.887 | -0.827 |
| 450 | impiego + maglia | 61.924 | -0.895 |
| 900 | impiego (senza maglia) | 62.069 | -1.154 |
| 900 | impiego + maglia | 62.134 | -1.269 |
| 1800 | impiego (senza maglia) | 64.255 | -5.066 |
| 1800 | impiego + maglia | 64.337 | -5.213 |

**Il pavimento distrugge il risultato in modo monotono**: +0,20% a zero, −0,83% a
450, −1,15% a 900, **−5,07% a 1.800**. Addestrare sui soli giocatori con molti
minuti rende il modello peggiore proprio dove il bersaglio vive. In E1 il
pavimento proteggeva le medie; qui i pochi minuti **sono** il bersaglio, non la
coda, e questa tabella e' la misura di quella differenza.

### La maglia dove dovrebbe servire

| variante | gruppo | righe | mae |
|---|---|---:|---:|
| senza maglia | primo anno nel club | 1652 | 68.50 |
| senza maglia | gia' nel club | 1026 | 49.75 |
| con maglia | primo anno nel club | 1652 | 68.47 |
| con maglia | gia' nel club | 1026 | 49.81 |

Sui giocatori al **primo anno nel club** la maglia migliora di 0,03 di MAE; su chi
era gia' nel club **peggiora** di 0,06. Il segno e' quello previsto e la grandezza
e' indistinguibile da zero — entrambe molto sotto l'MDE. **E' coerente con
l'ipotesi e non la conferma**, ed e' la lettura corretta di due numeri cosi'
piccoli.

## 4. Coda — il cartellino come predittore, e la fine dell'inversione

§1 aveva consegnato un'inversione: **il cartellino non e' una presenza in meno,
e' il segnale che quel giocatore gioca.** Era una lettura del meccanismo, non un
risultato: `tasso_cartellini` **non era nel set di E2.4** — `FEATURE` sono cinque
colonne e nessuna e' un cartellino — quindi l'inversione non era ne' confermata
ne' confutata. **Era non provata**, ed e' la ragione per cui questa coda si fa
qui e non fra due blocchi.

**La fonte e' quella dei voti, ed e' una scelta dichiarata** (vincolo 7: le due
divergono, le ammonizioni concordano solo all'85-93%). Per i punti fantacalcio la
fonte dei voti e' **definitoria** — e' quella che ha prodotto il malus dentro
`punti_osservati`, cioe' il bersaglio — e sta gia' sulla chiave `giocatore_id`
senza aggancio di mezzo. WhoScored resta il controllo indipendente di §1.

### Due forme, perche' sono due ipotesi diverse

Il **conteggio** `amm + esp` di t-1 e' l'inversione detta alla lettera: il
cartellino come marcatore di esposizione. Il **tasso** `(amm+esp)/presenze` e' la
propensione disciplinare **al netto** del minutaggio. Provarne una sola avrebbe
lasciato aperta l'altra.

### Il gate di E1 non si chiude, e non e' stato aggirato

| candidata | forma | min | max | deriva_riferimento | deriva | passa | degenere |
|---|---|---:|---:|---:|---:|---:|---:|
| cartellini | grezza | 2.4582 | 2.9601 | 0.170 | 0.170 | no | no |
| cartellini | _rel | -0.0000 | 0.0000 | 0.170 |  | no | si |
| tasso_cartellini | grezza | 0.1384 | 0.1581 | 0.175 | 0.124 | no | no |
| tasso_cartellini | _rel | -0.0627 | 0.0095 | 0.175 | 0.071 | no | no |

**Nessuna delle due forme passa la soglia del 5%**, ne' grezza ne' standardizzata.
E il conteggio **non e' un rapporto**: il suo unico denominatore possibile e' il
numero di giocatori, quindi il riferimento coincide con la media fra i giocatori e
la sua `_rel` ha media esattamente zero in ogni stagione **per costruzione**. Non
e' una candidata che passa il gate, e' una colonna resa degenere — dichiarato qui
invece che nascosto dentro un numero.

Ne segue che si provano **entrambe le forme**: se l'esito coincide, la conclusione
non dipende da una scelta di standardizzazione che i dati non giustificano.

### Il risultato

| variante | righe | mae_punti | mae_presenze | corr_presenze | divario_chiuso_pct |
|---|---:|---:|---:|---:|---:|
| impiego (senza maglia) | 2678 | 61.315 | 9.906 | 0.461 | 0.196 |
| impiego + cartellini (conteggio) | 2678 | 61.316 | 9.905 | 0.461 | 0.194 |
| impiego + cartellini (tasso) | 2678 | 61.317 | 9.906 | 0.461 | 0.193 |
| impiego + cartellini (entrambi) | 2678 | 61.302 | 9.902 | 0.461 | 0.220 |
| impiego + cartellini (conteggio, _rel) | 2678 | 61.317 | 9.905 | 0.461 | 0.193 |
| impiego + cartellini (tasso, _rel) | 2678 | 61.311 | 9.905 | 0.461 | 0.204 |

**Niente, in tutte e cinque le varianti.** Il divario chiuso resta lo 0,19-0,22%
contro lo 0,196% del set di E2.4, cioe' si muove di **tre centesimi di punto
percentuale**; il MAE sulle presenze sta a 9,902-9,906 contro 9,906; la
correlazione non si muove dalla terza cifra. Grezza o `_rel`, conteggio o tasso.

| variante | righe | delta_mae | se | t | mde_mae | mde_quota_divario_pct |
|---|---:|---:|---:|---:|---:|---:|
| impiego + cartellini (conteggio) | 2678 | -0.0015 | 0.0148 | -0.099 | 0.0415 | 0.074 |
| impiego + cartellini (tasso) | 2678 | -0.0020 | 0.0080 | -0.254 | 0.0225 | 0.040 |
| impiego + cartellini (entrambi) | 2678 | 0.0134 | 0.0239 | 0.559 | 0.0669 | 0.120 |
| impiego + cartellini (conteggio, _rel) | 2678 | -0.0020 | 0.0158 | -0.126 | 0.0442 | 0.079 |
| impiego + cartellini (tasso, _rel) | 2678 | 0.0043 | 0.0198 | 0.216 | 0.0554 | 0.099 |

**E qui la potenza non e' una scusa, e' l'argomento.** In E2.4 l'MDE valeva
l'1,53% del divario e il risultato negativo escludeva solo effetti grandi. Qui il
confronto e' **appaiato contro un modello quasi identico** — cambia una colonna —
quindi la varianza della differenza e' minuscola e l'MDE scende a **0,04-0,12%**
del divario. **Il test vedrebbe effetti dieci volte piu' piccoli di quelli che
E2.4 poteva vedere, e non ne trova nessuno.** Tutti i `t` stanno sotto 0,56 in
valore assoluto.

### Perche' il nulla non e' ridondanza

| forma | r2_sul_set_e2_4 | corr_quota_minuti | corr_quota_titolare | lettura |
|---|---:|---:|---:|---|
| cartellini_prec | 0.414 | 0.641 | 0.642 | gia' nel set |
| tasso_cartellini_prec | 0.021 | 0.079 | 0.086 | informazione nuova |

E' la misura che distingue una confutazione da un'ambiguita'. Un predittore che
non aggiunge niente puo' non aggiungere per due ragioni **opposte**: perche' e'
gia' dentro, o perche' non c'e' segnale.

* **Il conteggio e' in buona parte gia' nel set** (R2 0,41 sulle tre quote,
  correlazione 0,64 con `quota_minuti_prec`). Da solo, il suo nulla si
  spiegherebbe con la ridondanza — ed e' esattamente il meccanismo della Fase 2,
  dove i predittori evento erano gia' coperti dagli effetti attacco/difesa.
* **Il tasso no: R2 0,021, cioe' quasi ortogonale.** Porta informazione che il set
  di E2.4 **non ha**, e non serve lo stesso.

> **L'inversione e' confutata, e non resta una pista aperta in nessun blocco.**
> Il cartellino come sottrazione peggiora (§1); come predittore d'impiego non
> aggiunge niente, con un test che avrebbe visto lo 0,12% del divario. Le due
> letture sono state provate entrambe, in due forme ciascuna, e il meccanismo del
> nulla e' identificato per tutte e due. **Non va riaperta in E3 ne' in E4**, e
> non va "sistemata" ritoccando la forma della feature finche' un `t` supera 2:
> sarebbe la ricerca sugli otto predittori della Fase 2 rifatta su un bersaglio
> diverso, e con un MDE cosi' basso il margine per illudersi non c'e'.

**Cio' che resta vero di §1 e' il meccanismo, non la sua conseguenza operativa**:
chi prende cartellini gioca di piu', il modello d'asta gia' sottostima quei
giocatori, e per questo la sottrazione allontana. Il fatto e' misurato e non
cambia. Ma la quantita' che lo esprime era gia' nel modello sotto un altro nome.

## 5. (b) — la quotazione QI come predittore di presenza

**E' il primo predittore di presenze del progetto che superi il rumore**, e vale
la pena dire subito perche' puo' riuscire dove le feature evento hanno fallito:
tutte quelle vengono da **t-1**, perche' i dati evento di t non esistono ancora.
**QI viene da t** — e' un prezzo della stagione bersaglio, pubblicato prima che
cominci. E' l'unica cosa nel repository che guardi t senza guardarne l'esito.

**Il FVM e' fuori, e non per prudenza**: sta sull'orologio di QA, cioe' si muove
durante la stagione (§3-bis di `modello_asta.md`). QI e' la quotazione iniziale.
Un test verifica che nessuna colonna contaminata entri qui, e la guardia e'
sull'**elenco delle colonne ammesse**, non sul nome del suffisso.

### Due forme, e il gate di E1 le separa da solo

| colonna | stagioni | min | max | deriva | passa |
|---|---:|---:|---:|---:|---:|
| qi_asta | 4 | 7.9057 | 8.8768 | 0.1094 | no |
| qi_pct_ruolo_asta | 4 | 0.5756 | 0.5834 | 0.0135 | si |

Il **prezzo grezzo deriva dell'10.9%** fra le quattro stagioni e non passa la
soglia del 5%; il **percentile dentro `(stagione, ruolo)` deriva dell'1.3%** e
passa — com'e' giusto, perche' un rango dentro la stagione e' piatto per
costruzione, ed e' anche il modo di far vedere che la guardia sa dire di si'.

Le due forme sono **due ipotesi diverse**, non due parametrizzazioni: il grezzo
dice quanto vale un giocatore in assoluto, il percentile dice dove sta nella
gerarchia del suo ruolo. La seconda e' l'ipotesi vera — la gerarchia dichiarata
dai club e' cio' che si suppone il mercato sappia e i dati evento no — e le scale
dei ruoli sono incomparabili (un portiere costa 16, un attaccante 44) mentre il
modello non ha un termine di ruolo.

### Il risultato

| variante | righe | mae_punti | mae_presenze | corr_presenze | divario_chiuso_pct |
|---|---:|---:|---:|---:|---:|
| impiego (senza maglia) | 2678 | 61.3150 | 9.9055 | 0.4613 | 0.1962 |
| impiego + QI (prezzo grezzo) | 2678 | 61.1757 | 9.8352 | 0.4701 | 0.4457 |
| impiego + QI (percentile di ruolo) | 2678 | 60.5923 | 9.7438 | 0.4805 | 1.4898 |
| impiego + QI (percentile + indicatrice) | 2678 | 60.6115 | 9.7474 | 0.4810 | 1.4554 |
| SOLO QI, senza le feature evento | 2678 | 61.5233 | 9.8882 | 0.4664 | -0.1766 |

| variante | righe | delta_mae | se | t | mde_mae | mde_quota_divario_pct |
|---|---:|---:|---:|---:|---:|---:|
| impiego + QI (prezzo grezzo) | 2678 | 0.1393 | 0.1813 | 0.77 | 0.5079 | 0.9092 |
| impiego + QI (percentile di ruolo) | 2678 | 0.7227 | 0.2485 | 2.91 | 0.6962 | 1.2464 |
| impiego + QI (percentile + indicatrice) | 2678 | 0.7035 | 0.2444 | 2.88 | 0.6846 | 1.2256 |
| SOLO QI, senza le feature evento | 2678 | -0.2083 | 0.3432 | -0.61 | 0.9616 | 1.7214 |

**Il percentile di ruolo chiude l'1.49% del divario oracolo**, contro lo
**0.196%** del set di E2.4 — cioe' **8 volte** quello che le feature da dati evento
avevano prodotto. La differenza appaiata vale **t = 2.91**, contro un MDE del
1.25% del divario: **e' il primo predittore d'impiego di questo progetto
che stia sopra la propria soglia di rilevabilita'.** Con quattro varianti provate,
la soglia di Bonferroni a due code sarebbe |t| > 2.50, e 2.91 la supera.

Sul MAE delle presenze si passa da 9.906 a 9.744 e la correlazione da
0.461 a 0.481: si muove il passaggio giusto, non solo il prodotto finale.

**Tre cose che ridimensionano il risultato, e vanno lette insieme al numero:**

1. **L'1.5% resta piccolo in assoluto.** Il MAE sui punti va da 61.32 a
   60.59: sette decimi di punto su sessantuno. Le presenze restano il 91%
   dell'errore, e questo ne intacca una frazione. **Gli infortuni continuano a non
   essere nei dati**, e sono il tetto vero.
2. **Il prezzo grezzo da solo NON passa** (0.45%, t = 0.77, sotto il proprio
   MDE del 0.91%). Le due forme danno risposte diverse, quindi **la
   conclusione dipende dalla forma** — ed e' la forma dichiarata in anticipo come
   l'ipotesi vera, non quella scelta dopo aver visto i numeri. La coincidenza col
   gate di E1 e' un argomento in piu': la forma che funziona e' anche l'unica che
   non deriva.
3. **QI da solo e' PEGGIO del modello d'asta** (-0.18%): senza le feature evento la
   quotazione non basta. **E' un complemento, non un sostituto**, e chi ne
   ricavasse "all'asta guarda solo il prezzo" leggerebbe il contrario di quello
   che c'e' scritto.

### Il nulla non e' ridondanza, e qui nemmeno il positivo lo e'

| colonna | righe | r2_sulle_quote | corr_quota_minuti |
|---|---:|---:|---:|
| qi_asta | 1625 | 0.2845 | 0.5093 |
| qi_pct_ruolo_asta | 1625 | 0.4744 | 0.6833 |

QI e' **in buona parte gia' nel set**: il percentile ha R² 0.47 sulle tre quote di
esposizione di t-1 e correla 0.68 con `quota_minuti_prec`. Circa meta' di cio' che
il prezzo dice e' "ha giocato molto l'anno scorso", e quello lo sapevamo. **Il
guadagno viene dall'altra meta'** — ed e' esattamente la parte che nessun dato
evento puo' contenere, perche' e' il mercato estivo e la gerarchia dichiarata.

### L'indicatrice, e perche' non aggiunge niente

Il **31,2%** delle righe di `tabella_predittori` non ha QI: sono giocatori che
hanno giocato in t-1 e non sono nel listone di t, cioe' hanno lasciato il
campionato. Il riempimento a zero direbbe "il piu' economico", che e' un'altra
cosa da "non c'e'", quindi `senza_quotazione_asta` esiste come indicatrice
esplicita invece di lasciare che il riempimento decida in silenzio.

Non cambia niente (1.46% contro 1.49%), **e il motivo e' strutturale**: la
valutazione gira sul listone, quindi **tutte e 2678 le righe valutate hanno un
QI** e la mancanza tocca solo l'addestramento. Riportarlo evita che qualcuno
concluda che la mancanza non e' informativa: qui non e' *misurabile*, che e'
un'altra cosa.

## Domande aperte

1. **Il numero di maglia d'agosto**, dalla fonte giusta invece che dalla distinta.
   E' l'unico modo di provare l'argomento per cui la feature esisteva, e la fonte
   e' nota.
2. **Le 42 ammonizioni di scarto del 2023-24** fra le due fonti, in una stagione
   senza partite mancanti. Non identificate. **Per i punti fantacalcio la fonte
   dei voti e' definitoria e non una candidata**: e' quella che alimenta il malus,
   e lo scarto e' un problema di WhoScored da spiegare, non una scelta da fare.
3. **La durata vera delle espulsioni**, che il giudice sportivo pubblica e i dati
   evento non contengono: oggi tutte valgono una giornata come limite inferiore.
4. **Gli infortuni**, che restano la componente piu' grossa e non sono in nessuna
   delle due fonti acquisite.

> Il **cartellino come predittore d'impiego** era la terza domanda aperta di
> questo elenco. **E' chiusa dalla coda §4**, con esito negativo e potenza
> dichiarata, e per questo non compare piu' qui.
