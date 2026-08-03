# Blocco 0 — Ricognizione dei dati

Generato da `scripts/run_blocco0.py` il 2026-08-03.
Nessun modello e' stato scritto, niente e' stato scaricato, niente e' stato
imputato. Tutte le tabelle di questo documento si rigenerano con un comando.

---

## Esito in una riga

**Il Blocco 0 si chiude su una delle due fonti e non sull'altra.** WhoScored e'
sul disco e misurato (1.889 partite su 1.901 di calendario,
2.839.231 eventi, cinque stagioni) — con **cinque problemi che vanno
conosciuti prima di modellare**, elencati sotto. **I voti fantacalcio non
esistono nel repository**: non un file, non una riga. Ne segue che 0.2
(aggancio delle identita'), 0.3 (stabilita' del criterio di voto) e il tasso
d'errore di 0.4 **non sono calcolabili**, e non sono stati simulati.

I cinque problemi lato WhoScored, in ordine di quanto costano se scoperti dopo:

1. **72 delle 259 colonne non sono mai valorizzate**, e fra queste ci sono
   tutte le `cleanSheet*` e le `goalConcededByTeam*` — cioe' esattamente quelle
   a cui il blocco P8 (portieri) allungherebbe la mano per prime. §1.4
2. **Il criterio descrittivo degli eventi si muove fra stagioni**, e si muove
   proprio sulle grandezze che servono al voto base (P2): `Clearance`
   +48%, `BallRecovery` -26%,
   `Error` +162% fra la prima stagione e l'ultima. §1.5
3. **Due etichette di qualifier cambiano significato fra stagioni**
   (`StandingSave`, `OtherBodyPart`), e l'id numerico che permetterebbe di
   disambiguarle **e' scartato in acquisizione**. §1.6
4. **La giornata di campionato non esiste nei dati**, e non e' ricostruibile
   dall'ordine di `matches.json`, che e' cronologico e non per turno. Il
   bersaglio di P1 e' definito "alla giornata g". §1.7
5. **La chiave `(matchId, teamId, eventId)` ha una collisione** nel 2025-26,
   mentre il repository la documenta come unica. §1.8

Il resto del documento riporta i numeri. Le domande sono in fondo (§7), come da
modo di lavorare concordato.

---

## 1. (0.1) WhoScored — che cosa c'e' davvero sul disco

### 1.1 Sintesi per stagione

| stagione | file | eventi | eventi_per_partita | squadre | giocatori | prima | ultima | GB | zero_eventi |
|---|---|---|---|---|---|---|---|---|---|
| 2021-2022 | 374 | 576.928 | 1543 | 20 | 609 | 2021-08-21 | 2022-05-22 | 1.04 | 0 |
| 2022-2023 | 375 | 574.779 | 1533 | 20 | 577 | 2022-08-13 | 2023-06-11 | 1.04 | 0 |
| 2023-2024 | 380 | 568.200 | 1495 | 20 | 593 | 2023-08-19 | 2024-06-02 | 1.03 | 0 |
| 2024-2025 | 380 | 556.652 | 1465 | 20 | 600 | 2024-08-17 | 2025-05-25 | 1.01 | 0 |
| 2025-2026 | 380 | 562.672 | 1481 | 20 | 586 | 2025-08-23 | 2026-05-24 | 1.01 | 0 |

Le unita', che i nomi delle colonne non dicono: le coordinate `x`/`y`/`endX`/
`endY` sono **Opta 0-100 su entrambi gli assi** (non metri) e tutte le squadre
attaccano verso `x = 100`; `minute` e' il minuto di gioco, `expandedMinute`
include il recupero ed e' quello su cui il repository calcola i minuti, per cui
una partita dura 94-99 e non 90; `startDate` e' **solo la data**, senza orario
(`startTime` e' una colonna separata).

`squadre` e `giocatori` sono conteggi di identita' **WhoScored**: `teamId` e
`playerId`. I nomi delle squadre non stanno nei CSV — solo `teamId` — e si
ricavano incrociando `matchId` e casa/trasferta con `matches.json`.

### 1.2 Copertura

| stagione | calendario | file_su_disco | mancanti | su_disco_non_in_calendario | file_con_zero_eventi | copertura |
|---|---|---|---|---|---|---|
| 2021-2022 | 380 | 374 | 6 | 0 | 0 | 98.4% |
| 2022-2023 | 381 | 375 | 6 | 0 | 0 | 98.4% |
| 2023-2024 | 380 | 380 | 0 | 0 | 0 | 100.0% |
| 2024-2025 | 380 | 380 | 0 | 0 | 0 | 100.0% |
| 2025-2026 | 380 | 380 | 0 | 0 | 0 | 100.0% |

Nessun file contiene zero eventi, e nessun file sul disco e' fuori calendario.

### 1.3 Le 12 partite mancanti, e i denominatori che non sono 38

| stagione | matchId | casa | ospite | risultato |
|---|---|---|---|---|
| 2021-2022 | 1575817 | Salernitana | Atalanta | 0:1 |
| 2021-2022 | 1575876 | Napoli | Bologna | 3:0 |
| 2021-2022 | 1575881 | Atalanta | Lazio | 2:2 |
| 2021-2022 | 1575891 | Cagliari | Atalanta | 1:2 |
| 2021-2022 | 1575896 | Napoli | Verona | 1:1 |
| 2021-2022 | 1575889 | Sassuolo | Empoli | 1:2 |
| 2022-2023 | 1651789 | Napoli | Spezia | 1:0 |
| 2022-2023 | 1651493 | Empoli | Atalanta | 0:2 |
| 2022-2023 | 1651573 | Cremonese | Monza | 2:3 |
| 2022-2023 | 1651673 | Cremonese | Atalanta | 1:3 |
| 2022-2023 | 1651695 | Verona | Sassuolo | 2:1 |
| 2022-2023 | 1651772 | Atalanta | Spezia | 3:2 |

**La perdita non e' casuale rispetto alla squadra.** L'Atalanta ne perde 6 su
12, tre per stagione nelle due stagioni interessate:

| stagione | squadra | calendario | presenti | mancanti |
|---|---|---|---|---|
| 2021-2022 | Atalanta | 38 | 35 | 3 |
| 2021-2022 | Bologna | 38 | 37 | 1 |
| 2021-2022 | Cagliari | 38 | 37 | 1 |
| 2021-2022 | Empoli | 38 | 37 | 1 |
| 2021-2022 | Lazio | 38 | 37 | 1 |
| 2021-2022 | Napoli | 38 | 36 | 2 |
| 2021-2022 | Salernitana | 38 | 37 | 1 |
| 2021-2022 | Sassuolo | 38 | 37 | 1 |
| 2021-2022 | Verona | 38 | 37 | 1 |
| 2022-2023 | Atalanta | 38 | 35 | 3 |
| 2022-2023 | Cremonese | 38 | 36 | 2 |
| 2022-2023 | Empoli | 38 | 37 | 1 |
| 2022-2023 | Monza | 38 | 37 | 1 |
| 2022-2023 | Napoli | 38 | 37 | 1 |
| 2022-2023 | Sassuolo | 38 | 37 | 1 |
| 2022-2023 | Spezia | 39 | 37 | 2 |
| 2022-2023 | Verona | 39 | 38 | 1 |

E i denominatori non sono tutti 38, perche' il 2022-23 ha 381 partite in
calendario — c'e' il playout, che e' una partita vera:

| stagione | squadra | calendario | presenti | mancanti |
|---|---|---|---|---|
| 2022-2023 | Spezia | 39 | 37 | 2 |
| 2022-2023 | Verona | 39 | 38 | 1 |

> **Conseguenza operativa per ogni tasso per 90 delle fasi P.** Il denominatore
> di una squadra-stagione va **preso dai dati**, mai scritto 38. Per l'Atalanta
> 2021-22 e 2022-23 vale 35, per lo Spezia 2022-23 vale 39. Un tasso costruito
> su 38 sbaglia dell'8,6% sull'Atalanta, sempre nello stesso verso.

Le dodici assenze sono gia' accertate come **assenti alla fonte**
(`matchCentreData: null`), registrate in `data/raw/manifest.json` sotto
`assenti_alla_fonte`: non sono un difetto dell'acquisizione e non si recuperano.

### 1.4 Schema: 259 colonne, 187 vive

Lo schema e' **stabile in senso stretto**: 259 colonne in tutte e cinque le
stagioni, nessuna che compaia o sparisca. L'unica non emessa in ogni file e'
`isOwnGoal`, che e' la trappola nota (pandas la omette quando nella partita non
ci sono autogol: 5.8%–9.7% dei file per stagione).

**Ma "presente" non vuol dire "valorizzata", e la differenza qui e' enorme:
72 colonne su 259 non contengono un solo valore in nessuna delle
cinque stagioni.** Sono presenti nell'intestazione e sempre vuote.

> **Nota di misura, ed e' il motivo per cui questo numero non era mai emerso.**
> Lo scraper scrive il literal `False` dove il campo Opta e' assente. Contare
> `notna()` e chiamarlo copertura fa risultare `cardType` "valorizzata al 100%"
> quando lo e' solo sui cartellini. La colonna `quota_valorizzata` di
> `blocco0_colonne.csv` conta i valori **ne' nulli ne' `False`**, ed e' quella
> da leggere.

Le 72 colonne morte, per famiglia:

- **`cleanSheet*` (17)** — porta inviolata per posizione in campo.
- **`goalConcededByTeam*` (17)** e
  **`goalScoredByTeam*` (17)** — gol subiti e segnati per
  posizione in campo.
- **`penaltyShootout*` (5)** — vuote **attese**: in campionato
  non ci sono i rigori di fine partita. Sono l'unica famiglia la cui assenza non
  e' una notizia.
- le altre 16: `aerialSuccess`, `dribbleLastman`, `etScore`, `goalConcededOutsideBoxGoalkeeper`, `keeperClaimHighLost`, `keeperClaimLost`, `keeperClaimWon`, `keeperOneToOneWon`, `passAccuracy`, `passThroughBallInacurate`, `saveHighCentre`, `saveHighLeft`, `saveHighRight`, `saveLowCentre`, `saveLowLeft`, `saveLowRight`.

`passThroughBallInacurate` e' un refuso di WhoScored, e accanto c'e' la forma
corretta `passThroughBallInaccurate`, che invece e' valorizzata: sono due
colonne distinte nello schema, una viva e una morta.

> **Questo tocca P8 direttamente.** La porta inviolata e i gol subiti del
> portiere **non si leggono**: `cleanSheetGK` e `goalConcededByTeamGK` sono
> vuote. Vanno derivati dagli eventi `Goal` per squadra-partita, che e' cio'
> che `sot/aggregate.py` gia' fa. Lo stesso vale per la precisione dei passaggi
> (`passAccuracy` vuota, si ricava da `passAccurate`/`passInaccurate`) e per le
> parate per zona, che non esistono affatto.

Un solo tipo si muove fra stagioni, ed e' l'artefatto di cui sopra:

| colonna | 2021-2022 | 2022-2023 | 2023-2024 | 2024-2025 | 2025-2026 |
|---|---|---|---|---|---|
| cardType | str | bool\|str | bool\|str | bool\|str | bool\|str |

`cardType` e' stringa pura in tutti i 374 file del 2021-22 e mista
booleana/stringa nelle altre quattro: nelle prime non c'e' una sola partita
senza cartellini, nelle altre si'. E' una proprieta' del calcio che si e'
travestita da proprieta' dello schema.

### 1.5 Tipi di evento: 39, tutti presenti in tutte le stagioni — ma non alle stesse frequenze

Nessun tipo di evento compare o sparisce. **Le frequenze pero' si muovono, e si
muovono proprio dove serve al voto base.** Frequenza per 1.000 eventi
(normalizzata: le stagioni hanno un numero diverso di partite acquisite):

| type | 2021-2022 | 2022-2023 | 2023-2024 | 2024-2025 | 2025-2026 | rapporto | totale |
|---|---|---|---|---|---|---|---|
| Error | 0.33 | 0.31 | 0.38 | 0.75 | 0.87 | 2.82 | 1492 |
| KeeperSweeper | 0.35 | 0.44 | 0.36 | 0.59 | 0.69 | 1.95 | 1382 |
| ShieldBallOpp | 0.6 | 0.72 | 0.77 | 0.94 | 0.83 | 1.55 | 2188 |
| FormationChange | 1.38 | 1.26 | 1.2 | 1.85 | 1.86 | 1.55 | 4277 |
| Claim | 0.81 | 0.83 | 0.9 | 1.08 | 1.21 | 1.5 | 2743 |
| Clearance | 22.14 | 22.98 | 24.67 | 30.38 | 32.85 | 1.48 | 75391 |
| BallRecovery | 69.54 | 68.54 | 59.9 | 52.32 | 51.72 | 1.34 | 171773 |
| Challenge | 11.02 | 9.99 | 9.29 | 8.68 | 8.35 | 1.32 | 26905 |
| Punch | 0.42 | 0.47 | 0.48 | 0.55 | 0.54 | 1.29 | 1396 |
| Interception | 12.46 | 10.97 | 9.84 | 10.05 | 10.31 | 1.27 | 30476 |
| Card | 3.24 | 3.16 | 3.1 | 2.89 | 2.71 | 1.2 | 8580 |
| Goal | 1.86 | 1.67 | 1.75 | 1.75 | 1.64 | 1.14 | 4918 |
| BlockedPass | 9.65 | 9.79 | 9.7 | 8.91 | 8.76 | 1.12 | 26593 |
| TakeOn | 21.68 | 23.87 | 22.41 | 21.69 | 21.5 | 1.11 | 63129 |

`rapporto` e' max/min fra le cinque stagioni. Le voci in cima sono tutte
azioni **difensive e di errore**, cioe' le feature naturali di P2 per difensori
e centrocampisti.

> **Non e' possibile dire da questi dati se sia calcio o annotazione**, ed e' la
> stessa impossibilita' gia' dichiarata in `reports/phase7_stabilita_rilevazione.md`:
> le due ipotesi lasciano la stessa firma. Quel che si puo' dire e' la
> **grandezza**, e a queste grandezze una regressione del voto base addestrata
> sul 2021-22 e applicata al 2025-26 sta usando due strati descrittivi diversi.
> La verifica di stabilita' gia' fatta riguardava **la definizione di tiro in
> porta**, che risulta stabile (identita' esatta col flag Opta su tutte e cinque
> le stagioni): non copre queste colonne, che nessuno aveva ancora guardato.

### 1.6 Qualifier: 114 etichette, e due che cambiano significato

Nessun qualifier con almeno 200 occorrenze e' assente da una stagione. Ma due
cambiano frequenza in modo che non e' deriva:

| qualifier | 2021-2022 | 2022-2023 | 2023-2024 | 2024-2025 | 2025-2026 | min | max | rapporto |
|---|---|---|---|---|---|---|---|---|
| OtherBodyPart | 0.0097 | 0.0103 | 0.0094 | 0.0084 | 0.0003 | 0.0003 | 0.0103 | 30.0579 |
| StandingSave | 0.7069 | 0.7091 | 0.7205 | 0.7261 | 0.0428 | 0.0428 | 0.7261 | 16.9735 |
| ThrowinSetPiece | 0.0001 | 0.0001 | 0.0002 | 0.0004 | 0.0006 | 0.0001 | 0.0006 | 4.9062 |
| AerialFoul | 0.0005 | 0.0002 | 0.001 | 0.0011 | 0.001 | 0.0002 | 0.0011 | 4.8546 |
| LeadingToAttempt | 0.0002 | 0.0002 | 0.0002 | 0.0005 | 0.0006 | 0.0002 | 0.0006 | 3.3222 |
| LastMan | 0.0003 | 0.0002 | 0.0003 | 0.0005 | 0.0006 | 0.0002 | 0.0006 | 2.5031 |
| FastBreak | 0.0007 | 0.0008 | 0.0008 | 0.0013 | 0.0014 | 0.0007 | 0.0014 | 2.1798 |
| OneOnOne | 0.0001 | 0.0001 | 0.0002 | 0.0003 | 0.0003 | 0.0001 | 0.0003 | 2.1174 |

**`StandingSave` non e' una parata.** Nelle prime quattro stagioni compare su
circa il **71% di tutti gli eventi**, e su una partita presa a caso 683 delle
885 occorrenze stanno su eventi `Pass`. Un'etichetta che sta su due terzi dei
passaggi non sta descrivendo un portiere fermo sulla linea. Nel 2025-26 la
stessa etichetta compare su ~30 eventi per partita e **solo** su `Tackle`,
`Foul` e `Save` — cioe' su qualcosa di compatibile col nome.

**`OtherBodyPart` si comporta allo stesso modo, e nelle stesse partite.** Nel
2025-26 sopravvive in 92 partite su 380, e le 12 partite che
conservano il regime vecchio di `StandingSave` (piu' di un evento su quattro,
come nelle prime quattro stagioni, invece di ~30 per partita) sono fra queste.
La sovrapposizione e' quasi esatta: **91 delle 92**.

> **La spiegazione economica e' una sola: due versioni del dizionario
> qualifier della fonte, e 12 pagine del 2025-26 servite dalla versione
> vecchia.** Non e' un cambio di criterio di annotazione — e' la stessa
> etichetta appiccicata a id diversi.
>
> **E non e' disambiguabile dai dati in casa.** `acquisition/whoscored/main.py:432`
> fa `row[irow]['type'] = row[irow]['type']['displayName']`: **l'id numerico del
> qualifier viene buttato via** e resta solo il nome. Per sciogliere il nodo
> servirebbe riacquisire conservando l'id, il che tocca la rete e va deciso.
>
> Questo **precisa e in parte corregge** quanto sta in `CLAUDE.md` ("`StandingSave`
> c'e' su ~81% dei tiri nelle prime quattro stagioni e su ~2% nel 2025-26, [...]
> su 11 partite su 380 nel 2025-26 e zero esatto nelle altre"): misurato sui
> **tiri** e' cosi', misurato su **tutti gli eventi** l'etichetta e' viva in
> **377 partite su 380**, a un trentesimo del tasso. Il fatto nuovo e'
> che sta per due terzi sui passaggi, che e' quello che ne rivela la natura.
>
> **Nessuna colonna usata dalle Fasi 1-6 dipende da questi due qualifier**, quindi
> nessun numero pubblicato si muove. Il rischio e' a valle, sulle feature di P2.

### 1.7 La giornata di campionato non c'e'

Nessun CSV e nessun `matches.json` contiene il numero di turno. `matches.json`
**e' ordinato per data, non per giornata**: spezzandolo in blocchi di dieci,
un blocco che fosse una giornata conterrebbe venti squadre distinte, e invece:

| stagione | n_blocchi | blocchi_anomali | date_vuote | quota_ordine_cronologico |
|---|---|---|---|---|
| 2021-2022 | 38 | 33 | 23 | 98.6% |
| 2022-2023 | 39 | 35 | 33 | 98.4% |
| 2023-2024 | 38 | 30 | 8 | 99.5% |
| 2024-2025 | 38 | 30 | 7 | 99.7% |
| 2025-2026 | 38 | 29 | 15 | 99.5% |

**L'ordine e' cronologico**, non per turno: le date crescono nel
98.4%-99.7% dei passi
consecutivi, e i turni rinviati bastano a mescolare i blocchi di dieci. Le date
testuali del JSON sono per giunta vuote su 7-33 voci per stagione — quelle
vere si prendono da `startDate` nei CSV.

> **Sostituto usato, e va dichiarato in ogni blocco che ne dipenda**: l'**indice
> cronologico di squadra** (l'ennesima partita di quella squadra in quella
> stagione), che e' completo — 38 per tutte le squadre in tre stagioni, 35-38
> nelle due con partite mancanti — ed e' la stessa grandezza che le Fasi 2-6
> chiamano `team_match_idx`. **Non e' la giornata**: per una squadra che ha
> giocato un recupero, indice e giornata divergono. Il bersaglio di P1 e'
> scritto "P(riceve voto alla giornata g)": se la giornata vera serve davvero,
> va presa da fuori. E' una domanda aperta (§7).

### 1.8 La chiave unica ha una collisione

Il repository documenta `(matchId, teamId, eventId)` come chiave unica con zero
duplicati. **Ce n'e' uno**, e sta nel 2025-26:

| stagione | duplicati su `(matchId, teamId, eventId)` | duplicati su `id` |
|---|---:|---:|
| 2021-2022 | 0 | 37 |
| 2022-2023 | 0 | 40 |
| 2023-2024 | 0 | 36 |
| 2024-2025 | 0 | 23 |
| 2025-2026 | 1 | 30 |

Nella partita `1901279` (2026-04-26) l'`eventId` 838 della squadra 75 sta su due
eventi diversi: un `Save` a 84:29 e un `BallRecovery` a 84:32, giocatori
diversi. Non sono righe duplicate — sono due eventi veri con lo stesso numero,
esattamente come le 30 collisioni note su `id`, che restano (23-40 per stagione).

> **Perche' conta:** un `merge` su quella chiave duplica silenziosamente una
> riga. Su 2,8 milioni di eventi una riga non sposta nessuna stima, ma
> l'invariante va scritto giusto: **nessuna delle chiavi disponibili e' unica**,
> e l'unica difesa e' verificare la cardinalita' dopo ogni join invece di
> fidarsi. `blocco0_sintesi_stagioni.csv` porta le due colonne.

---

## 2. (0.1) I voti fantacalcio — accertamento di assenza

Il Blocco 0 chiede la ricognizione di **due** fonti. La seconda non c'e'. Non e'
un'impressione: sono i percorsi guardati, dalla tassonomia gia' fissata in
`sot/config.py`.

| percorso | esiste | file_presenti |
|---|---|---|
| data/raw/fantacalcio/ITA-serie-a/2021-2022 | False | 0 |
| data/raw/fantacalcio/ITA-serie-a/2022-2023 | False | 0 |
| data/raw/fantacalcio/ITA-serie-a/2023-2024 | False | 0 |
| data/raw/fantacalcio/ITA-serie-a/2024-2025 | False | 0 |
| data/raw/fantacalcio/ITA-serie-a/2025-2026 | False | 0 |
| data/external/voti | False | 0 |
| data/external/quote | True | 1 |

L'unico file in `data/external/` e' `quote/como_tiri_in_porta_2025-2026.xlsx`,
che riguarda i tiri in porta del Como e **non e' un listone di quotazioni**.

Ne segue, meccanicamente:

| punto del Blocco 0 | stato | perche' |
|---|---|---|
| 0.1 lato WhoScored | **chiuso** | §1 |
| 0.1 lato voti | **non calcolabile** | nessun dato |
| 0.2 corrispondenza giocatori e squadre | **non calcolabile** | una corrispondenza ha due lati; c'e' solo il sinistro (§3) |
| 0.3 stabilita' del criterio di voto | **non calcolabile** | tutte e otto le grandezze di §5 delle regole vivono nei voti |
| 0.4 tasso d'errore della regola dell'80' | **non calcolabile** | serve l's.v. **osservato**; c'e' solo il proiettato (§5) |

Lo stato dell'acquisizione, dai report esistenti e non da una nuova verifica:
`reports/phase7_fattibilita_fonte.md` ha accertato che gli endpoint di export
rispondono **401** senza credenziali, che la vista HTML e' pubblica su tutte e
cinque le stagioni, e che **i minuti nella fonte non ci sono** (per questo i
minuti vengono da WhoScored). `docs/regole_fantacalcio.md` §7.1 registra
l'autorizzazione dichiarata dall'utente e lascia **`[NON DECISO]`** da quale
delle due vie si acquisisce. **Finche' quella decisione non e' presa, non c'e'
niente da scaricare e il Blocco 0 non si puo' chiudere.**

---

## 3. (0.2) Identita': c'e' solo il lato WhoScored, ed e' scritto

Le tabelle di corrispondenza non esistono e **non sono state create vuote**: un
file con la colonna dei voti a `NA` verrebbe letto a valle come "aggancio
fallito" invece che "aggancio mai tentato", e sarebbe il segnaposto che la
regola di condotta 1 vieta. Un test lo blocca
(`test_mapping_non_contiene_colonne_di_voto`).

Cio' che c'e' e' l'**anagrafica WhoScored**, che e' il lato sinistro di
entrambe le corrispondenze e serve comunque:

- `data/mapping/whoscored_squadre.csv`
- `data/mapping/whoscored_giocatori.csv`
- `data/mapping/whoscored_anomalie_omonimi.csv`
- `data/mapping/whoscored_anomalie_multisquadra.csv`
- `data/mapping/whoscored_anomalie_multigrafia.csv`
- `data/mapping/whoscored_anomalie_nome_singolo.csv`
- `data/mapping/whoscored_anomalie_nome_non_ascii.csv`

**Squadre**: 27 nomi distinti su cinque stagioni, 20 per stagione.
Il `partite` e' il numero di partite **con un CSV sul disco**, non quelle di
calendario (§1.3).

| nome_whoscored | 2021-2022 | 2022-2023 | 2023-2024 | 2024-2025 | 2025-2026 |
|---|---|---|---|---|---|
| AC Milan | 38 | 38 | 38 | 38 | 38 |
| Atalanta | 35 | 35 | 38 | 38 | 38 |
| Bologna | 37 | 38 | 38 | 38 | 38 |
| Cagliari | 37 | 0 | 38 | 38 | 38 |
| Como | 0 | 0 | 0 | 38 | 38 |
| Cremonese | 0 | 36 | 0 | 0 | 38 |
| Empoli | 37 | 37 | 38 | 38 | 0 |
| Fiorentina | 38 | 38 | 38 | 38 | 38 |
| Frosinone | 0 | 0 | 38 | 0 | 0 |
| Genoa | 38 | 0 | 38 | 38 | 38 |
| Inter | 38 | 38 | 38 | 38 | 38 |
| Juventus | 38 | 38 | 38 | 38 | 38 |
| Lazio | 37 | 38 | 38 | 38 | 38 |
| Lecce | 0 | 38 | 38 | 38 | 38 |
| Monza | 0 | 37 | 38 | 38 | 0 |
| Napoli | 36 | 37 | 38 | 38 | 38 |
| Parma Calcio 1913 | 0 | 0 | 0 | 38 | 38 |
| Pisa | 0 | 0 | 0 | 0 | 38 |
| Roma | 38 | 38 | 38 | 38 | 38 |
| Salernitana | 37 | 38 | 38 | 0 | 0 |
| Sampdoria | 38 | 38 | 0 | 0 | 0 |
| Sassuolo | 37 | 37 | 38 | 0 | 38 |
| Spezia | 38 | 37 | 0 | 0 | 0 |
| Torino | 38 | 38 | 38 | 38 | 38 |
| Udinese | 38 | 38 | 38 | 38 | 38 |
| Venezia | 38 | 0 | 0 | 38 | 0 |
| Verona | 37 | 38 | 38 | 38 | 38 |

> Gia' visibile senza il lato destro: **`Parma Calcio 1913`** e' la forma
> WhoScored, e nessuna fonte italiana di voti la scrive cosi'. Le squadre sono
> 27 in tutto e la corrispondenza si fa a mano in dieci minuti — **e va fatta a
> mano**, perche' un fuzzy su 27 nomi non ha alcun vantaggio e ha il rischio di
> agganciare `Verona` a `Venezia`.

**Giocatori**: 1.411 `playerId` distinti su cinque stagioni,
577-609 per stagione. I casi che il Blocco 0
chiede di gestire esplicitamente, contati **dentro WhoScored** (il conteggio
sul lato voti sara' diverso, e la loro intersezione e' il rischio vero):

| caso | righe giocatore-stagione | lettura |
|---|---:|---|
| omonimi (stesso nome, `playerId` diversi, stessa stagione) | 0 | **nessuno**: WhoScored non ha omonimi interni. Non dice niente sul lato voti, dove i cognomi sono spesso soli |
| piu' grafie dello stesso `playerId` | 0 | **nessuna**: WhoScored e' internamente coerente sulla grafia |
| piu' squadre nella stessa stagione (mercato di gennaio, prestiti) | 134 | ~27 per stagione, il 4.5% delle righe |
| nome di un solo token | 60 | brasiliani e portoghesi (`Dalbert`, `Bremer`, `Beto`, `Danilo`) |
| nome con caratteri non ASCII | 426 | il 14% delle righe: `Ribéry`, `Kjær`, `Tolói`, `Mäenpää` |

I file `whoscored_anomalie_*.csv` in `data/mapping/` contengono gli elenchi
completi, che sono il materiale da rivedere a mano quando il lato destro
arrivera'.

> **Il tasso di aggancio richiesto (soglia 98%) non e' misurabile e non e'
> stimabile.** Il rischio non e' distribuito uniformemente: si concentra sui
> 426 nomi non ASCII, sui 60 a
> token singolo e sui 134 con due squadre — dove
> l'aggancio va fatto **per stagione e per squadra**, non per nome, altrimenti un
> giocatore ceduto a gennaio si aggancia alla squadra sbagliata per meta'
> stagione senza che niente lo segnali.

---

## 4. (0.3) Stabilita' del criterio di voto — non calcolabile

Le otto grandezze chieste da `docs/regole_fantacalcio.md` §5 (voto medio
complessivo e per ruolo, deviazione standard, percentuale di s.v.,
distribuzione dei voti, fantamedia per ruolo, frequenza di bonus e malus,
provider dichiarato) **vivono tutte nei voti**. Nessuna e' derivabile dagli
eventi. Non e' stata calcolata nessuna approssimazione.

I minuti medi giocati — l'unica delle otto che sta in WhoScored — sono gia'
riconciliati esattamente su 760/760 squadra-partita per il 2025-26
(`reports/phase1_audit.md`). **Per le altre quattro stagioni la catena dei
minuti non e' ancora costruita**: `sot/minutes.py` gira sulla stagione di
`config.SEASON`. E' lavoro noto e non bloccante, ma va contato.

---

## 5. (0.4) La regola dell'80' — c'e' il denominatore, non il tasso d'errore

`docs/regole_fantacalcio.md` §1.2 chiede il tasso d'errore **nei due versi**:
chi entra dopo l'80' e un voto lo prende, chi entra prima e non lo prende.
**Tutti e due hanno bisogno dell's.v. osservato**, che sta nei voti. Non
calcolato, non stimato.

Cio' che si puo' misurare e' **quanta massa la regola sposta**, sul 2025-26:

| grandezza | valore |
|---|---:|
| righe giocatore-partita con almeno un minuto giocato | 11.928 |
| di cui titolari | 8.360 |
| di cui subentrati | 3.568 |
| marcate **s.v. proiettato** dalla regola (ingresso ≥ 80' su `expandedMinute`) | **1.167** |
| quota sul totale di chi e' sceso in campo | 9.8% |
| quota fra i soli subentrati | 32.7% |

Tre fatti che la regola porta con se', e che vanno accanto a ogni numero che vi
poggi:

1. **La soglia cade nel punto di massima densita' degli ingressi.** Lo scaglione
   [75, 80) contiene 493 ingressi e lo scaglione [80, 85) ne contiene
   501: **spostare la soglia di cinque minuti sposta ~493 righe**, cioe'
   il 4.1% di tutte le righe. La regola e' nel punto in cui e' piu'
   sensibile alla propria posizione. Distribuzione completa in
   `blocco0_ingressi_per_minuto.csv`.
2. **Su `expandedMinute` l'80' non e' l'80'.** La partita dura 94-99 minuti,
   quindi chi entra all'80' espanso gioca fino a 25 minuti
   (mediana 12), e **397 delle 1167 righe marcate s.v.
   hanno almeno 15 minuti giocati**. La scelta di `expandedMinute` e'
   dell'utente ed e' coerente con tutto il repository; la conseguenza, che va
   detta accanto, e' che la regola e' **piu' permissiva** di quanto "80'"
   suggerisca, non meno.
3. **La regola non copre il titolare che esce presto.** Nel 2025-26 ci sono
   11 titolari usciti prima del 10' e 28 prima del 20' —
   infortuni ed espulsioni. Se la scala Redazione da' loro s.v., la regola non
   lo prevede: e' un verso d'errore **strutturale**, non campionario, e non e'
   fra i due che §1.2 chiede di misurare.

---

## 6. Le quattro contraddizioni sciolte prima di scrivere codice

Come richiesto, con la mia lettura di ciascuna. **Nessuna e' stata risolta da
me**: sono in §7 come domande.

**(1) La sezione 0 dichiara aperte decisioni che gli YAML piu' avanti hanno gia'
un valore.** La mia lettura: **gli YAML sono segnaposto illustrativi, la sezione
0 e' aggiornata**, e non il contrario. Tre indizi. `0.1` e' seguita nel testo da
`[DA DECIDERE 0.1] — le fasce sono 3` (una decisione presa) *e* da un blocco
YAML con tre fasce che porta ancora il marcatore `[DA DECIDERE 0.1]` sopra le
soglie: il numero di fasce e' deciso, le **soglie** no. Stessa forma per `0.4`,
dove `— malus di -1` e' deciso e `sotto_soglia_minima: -1` lo riflette. Per
`0.2` (`n_difensori: 4`) e `0.5` non c'e' nessuna riga di decisione nel testo,
solo lo YAML: quelli sono i due davvero aperti. Il commento `# tipicamente 3 o 4`
accanto a `n_difensori: 4` e' scritto da chi propone, non da chi decide.

**(2) `n_difensori: 4` e' incompatibile con i moduli ammessi, e §3.2 pretende un
test di coerenza che fallirebbe sempre.** La mia lettura: **`n_difensori` non
puo' essere una costante**. I sette moduli ammessi schierano 3, 4 o 5
difensori; con `n_difensori` fisso a 4 il test di §3.2 e' insoddisfacibile per
costruzione. Le letture possibili sono due e danno codice diverso:
(a) il modificatore usa il portiere **piu' i migliori `n` difensori schierati**
con `n` che dipende dal modulo — allora la simulazione F2 deve girare **per
modulo** e il contributo marginale di §2.2 e' relativo a una linea *e* a un
modulo; (b) il regolamento fissa un `n` unico (tipicamente 4) **indipendente**
dal modulo, prendendo i migliori 4 fra i difensori schierati e ignorando il
quinto, il che rende il 5-3-2 diverso dal 3-5-2 nel valore dei difensori.
Sono le due letture piu' comuni nelle leghe reali e **non si distinguono dal
documento**. Non ho scelto.

**(3) La copertura dei voti e' dichiarata in due modi diversi.** §1.2 da' l's.v.
osservato su 2021/22-2025/26; §7.1 punto 2 dice che la 2025/26 e' l'unica con
entrambe le fonti. La mia lettura: **non sono in contraddizione, dicono due cose
diverse** — la prima e' la copertura dei *voti*, la seconda la copertura di
*voti* **e** *minuti* insieme. Il fatto misurato sul disco e' pero' un terzo:
**nessuna delle due e' verificabile, perche' i voti non ci sono in nessuna
stagione** (§2). Sul disco la copertura dei voti e' zero su cinque; quella dei
minuti e' cinque su cinque, ma la catena dei minuti e' costruita per una sola
(§4).

**(4) Nomenclatura.** Il repository numera per **fase** (`Fase 0`…`Fase 7`,
report `phaseN_*.md`) e `docs/regole_fantacalcio.md` chiama gia' `8A` il voto
base e `8D` il modificatore, cioe' **Fase 8 = fantacalcio**. Il prompt usa
`Blocco 0`, `T1-T5`, `P1-P9`, `F1-F5`. Cio' che ho adottato, e che si puo'
cambiare con una riga: **`Fase 8` come contenitore**, e **i nomi `T`/`P`/`F` del
prompt per i blocchi**, perche' sono piu' fini di `8A`/`8D` e mappano uno a uno
sui moduli. Il deliverable resta `reports/blocco0_ricognizione.md`, che e' il
nome che il prompt chiede esplicitamente, **e questa e' l'unica incoerenza con
`phaseN_*`**: la segnalo invece di rinominare di mia iniziativa. La
corrispondenza con i nomi gia' scritti nelle regole e' `8A = P2` (voto base) e
`8D = F3` (modificatore).

---

## 7. Domande aperte — qui il blocco si ferma

**Bloccanti: senza queste non si scrive una riga di modello.**

**D1. I voti fantacalcio: dove sono?** Il prompt dice "ho i voti fantacalcio
della stessa finestra", il disco dice di no (§2). Le possibilita' sono che
esistano fuori dal repository, oppure che vadano ancora acquisiti. Se vanno
acquisiti, resta aperto **da quale via** — `docs/regole_fantacalcio.md` §7.1 la
lascia `[NON DECISO]` fra export Excel da sessione autenticata (serve che tu
faccia login: gli endpoint danno 401) e vista HTML pubblica. **Non procedo su
nessuna delle due senza che tu scelga**, ed entrambe toccano la rete.

**D2. Le quotazioni del listone, idem.** Non sono sul disco. Sono la **terza
baseline obbligatoria** della sezione di validazione e l'oggetto di F5, cioe'
la verifica principale del progetto. Senza, F5 non esiste e le altre due
baseline non bastano a dire se il modello ha valore d'uso.

**D3. `n_difensori` e' fisso o dipende dal modulo?** (contraddizione 2). Cambia
la forma della simulazione F2 e del contributo marginale F3, quindi va deciso
prima di scriverli, non dopo.

**D4. Le soglie delle fasce del modificatore** restano `[DA DECIDERE 0.1]` anche
nella lettura piu' generosa (§6.1): il numero di fasce e' deciso (tre), i valori
6.00 / 6.50 / 7.00 dello YAML no. Confermi quelli o sono illustrativi?

**D5. Il formato della lega** (`[DA DECIDERE 0.5]`): 8 squadre, budget 1000,
rosa 3/8/8/6 sono valori reali o segnaposto? Il budget in particolare — senza,
il confronto valore/quotazione non e' definibile.

**Non bloccanti, ma da decidere prima del blocco che le usa.**

**D6. La giornata di campionato** (§1.7). Il bersaglio di P1 e' scritto "alla
giornata g", e la giornata non e' nei dati. Tre vie: (a) usare l'indice
cronologico di squadra e riscrivere il bersaglio di conseguenza — costa zero e
diverge dalla giornata vera solo sui recuperi; (b) prendere la giornata dalla
fonte dei voti, che l'ha di sicuro, ma la lega a un aggancio che non esiste
ancora; (c) prenderla da una terza fonte. La (a) e' quella che consiglierei,
dichiarando la divergenza.

**D7. I due qualifier con l'id buttato via** (§1.6). Se le feature di P2 devono
usare i qualifier, l'id numerico serve, e per riaverlo bisogna riacquisire.
**Non lo faccio senza un tuo via**, perche' tocca la rete e perche' riacquisire
sovrascriverebbe — che il vincolo 9 vieta. La domanda vera e' se P2 possa
vivere sui **tipi di evento** e sulle colonne booleane, che sono stabili nello
schema, invece che sui qualifier.

**D8. La deriva delle frequenze degli eventi** (§1.5). `Clearance` +48% e
`BallRecovery` −26% fra il 2021-22 e il 2025-26. Tre opzioni: stimare P2 per
stagione con un effetto di stagione esplicito; restringere il perimetro alle
stagioni piu' recenti; oppure normalizzare per stagione ciascuna feature — che
e' l'unica delle tre che *cambia il dato*, e che secondo il vincolo di §5 delle
regole va documentata e misurata, non applicata in silenzio. **Come per la
normalizzazione del criterio di voto: la scelgo io o la scegli tu?** Il
documento dice che la normalizzazione la decidi tu.

**D9. Perimetro temporale.** La 2021-22 e' gia' dichiarata non confrontabile sul
vantaggio del campo (ritorno del pubblico), ed e' anche l'estremo di quasi tutte
le derive di §1.5, e una delle due che perdono partite. Vale la pena tenerla?
E' una domanda di costi e benefici come quella che la Fase 6F si e' posta sul
piano dati, non una questione tecnica.

---

## Cosa e' stato prodotto

| | |
|---|---|
| `sot/ricognizione.py` | il modulo di misura, 187 colonne vive su 259 misurate su 1.889 file |
| `scripts/run_blocco0.py` | rigenera tutto con un comando |
| `tests/test_ricognizione.py` | invarianti, compresi quelli che **vietano il segnaposto** sui voti |
| `reports/blocco0_ricognizione.md` | questo documento |
| `reports/blocco0_*.csv` | 11 tabelle |
| `data/mapping/whoscored_*.csv` | anagrafiche e anomalie, **solo lato WhoScored** |
| `data/processed/ITA-serie-a/blocco0_*.parquet` | cache della scansione, rigenerabile con `--force` |

Nessun modello, nessuna stima, nessuna riga scritta sotto `data/raw/`, nessuna
richiesta di rete, nessuna dipendenza aggiunta.
