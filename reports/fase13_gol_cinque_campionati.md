# Fase 13 / G2 — il modello dei GOL sui cinque campionati

`scripts/run_fase13_gol.py` + `reports/fase13_gol_campionati.csv`. **Nessuna
richiesta di rete. Nessun modello nuovo**: e' `TeamModel(target="gol_fatti")` di
E3.1 applicato a campionati diversi. La domanda del blocco non e' «funziona»,
e' **«trasferisce»**.

**I cinque campionati NON sono poolati**, ed e' la regola di E1 che R0 aveva
gia' scritto in anticipo proprio su G2. Un fit per campionato; dentro ciascuno
il walk-forward e' **dentro la stagione**, come E3.1.

---

## 1. L'esito: trasferisce in quattro campionati su cinque

| campionato | partite | n | MAE | pendenza | z vs 1 | delta | **t (cluster)** | MDE | delta/MDE |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Serie A | 1.640 | 3.278 | 0,8720 | 0,898 | −1,98 | 0,0302 | **5,40** | 0,0159 | **1,90** |
| Premier League | 1.649 | 3.294 | 0,9554 | 0,929 | −1,41 | 0,0271 | **4,80** | 0,0160 | **1,69** |
| Liga | 1.654 | 3.298 | 0,8634 | 0,947 | −1,01 | 0,0198 | **3,56** | 0,0158 | **1,25** |
| Ligue 1 | 1.439 | 2.872 | 0,9498 | 0,868 | −2,25 | 0,0190 | **3,09** | 0,0175 | **1,09** |
| Bundesliga | 1.303 | 2.606 | 1,0040 | 0,887 | −2,14 | 0,0102 | **1,44** | 0,0201 | **0,51** |

Il baseline e' sempre **`media squadra + campo`**, cioe' il piu' difficile da
battere (vincolo 6). Il `t` e' per **cluster di partita**: vedi §3.

**Il 5,52 della Serie A riproduce E3.1 a ogni cifra** — e' il controllo che la
parametrizzazione per campionato non abbia spostato il numero gia' pubblicato,
e vale piu' del risultato nuovo.

La **forma** della distribuzione regge ovunque, non solo la media: PIT p fra
0,17 e 0,77, e gli zeri osservati coincidono con gli attesi (0,2241 contro
0,2246 in Bundesliga, 0,2773 contro 0,2886 in Serie A). Gli zeri sono la porta
inviolata, cioe' il controllo che conta su questo bersaglio.

---

## 2. La Bundesliga non e' un nullo: e' un test senza potenza

**Ed e' la differenza che il MDE serve a rendere visibile** (lezione della 6D).

| | |
|---|---:|
| delta osservato | 0,0102 |
| MDE a potenza 80% | **0,0201** |
| delta / MDE | **0,51** |

L'effetto osservato e' **circa la meta' del minimo rilevabile**: con queste
righe il test non avrebbe visto nemmeno un effetto grande il doppio di quello
che ha misurato. Dire «in Bundesliga il modello non batte il baseline» sarebbe
scorretto; l'affermazione difendibile e' **«qui il confronto non conclude»**.

Tre ragioni concorrono, tutte misurate:

1. **meno righe** — 2.606 contro 3.278: 18 squadre, quindi 306 partite per
   stagione invece di 380;
2. **bersaglio piu' rumoroso** — 1,51-1,59 gol per squadra-partita contro
   1,18-1,32 della Serie A. Su conteggi la varianza cresce con la media, e
   infatti il MAE e' il piu' alto di tutti (1,0040);
3. **il delta e' comunque positivo** (0,0102), cioe' il segno e' quello giusto.

**Non va "sistemato".** Un modello ritoccato finche' il `t` della Bundesliga
supera 2 sarebbe adattamento al campione su cui poi lo si valuta.

---

## 3. Il `t` per cluster non cambia niente, e non era ovvio

La riga e' la squadra-partita, ma l'unita' indipendente e' la **partita**: le
due righe condividono l'esito. V0 aveva misurato che i due lati sono
**fortemente correlati** nei valori (−0,349, il possesso a somma costante).

| campionato | t per riga | t per cluster |
|---|---:|---:|
| Serie A | 5,52 | 5,40 |
| Premier League | 4,79 | 4,80 |
| Liga | 3,72 | 3,56 |
| Ligue 1 | 3,16 | 3,09 |
| Bundesliga | 1,43 | 1,44 |

**Lo scarto e' sotto il 5% ovunque**, e in un caso il cluster va nel verso
opposto. E' la **replica di un fatto che V1 aveva gia' trovato sui tentativi**:
la correlazione forte e' fra i **valori** dei due lati, non fra gli **errori**,
e sono due cose diverse. Il fattore di cluster di V0 (0,807) descrive la prima e
**non** questo confronto — citarlo qui sarebbe sbagliato.

Perche' gli errori si correlino cosi' poco resta **non spiegato**, ed e' la
stessa domanda aperta che V1 aveva lasciato.

---

## 4. Perche' il pooling e' vietato, in un numero

| campionato | gol per squadra-partita |
|---|---:|
| Bundesliga | 1,51 — 1,59 |
| Premier League | 1,32 — 1,58 |
| Ligue 1 | 1,31 — 1,45 |
| Serie A | 1,18 — 1,39 |
| Liga | 1,22 — 1,32 |

Fra Bundesliga e Liga corrono **oltre 25 punti percentuali** di livello. Un fit
unico attribuirebbe quella differenza ai coefficienti di attacco e difesa
**delle squadre**, cioe' misurerebbe il contesto e lo chiamerebbe forza.

E il livello si muove anche **dentro** un campionato: la Premier va da 1,32 a
1,58 fra due stagioni. E' il motivo per cui il walk-forward resta dentro la
stagione e per cui `xg_fit` porta ora `campionato/stagione` — **venticinque
fit, non cinque**.

---

## 5. Domande aperte

1. **La Bundesliga vuole piu' righe, non un modello diverso.** Per portare
   delta/MDE sopra 1 servirebbero circa quattro volte le partite: dieci
   stagioni, oppure il bersaglio piu' informativo dei **tentativi** (V1 ha
   mostrato t = 9,63 sui tiri contro 1,86 sui tiri in porta).
2. **La pendenza di calibrazione e' sotto 1 in tutti e cinque** (0,868-0,947),
   con z fra −1,0 e −2,2. E' lo shrinkage della ridge, gia' misurato cinque
   volte (Fase 3, 4, 6A, R3, V1). **Non va corretto**: e' la sesta.
3. **La correlazione degli errori fra i due lati** resta non spiegata (§3).
4. **Non c'e' nessun confronto FRA campionati**, ed e' voluto: i modelli sono
   cinque, e mettere a confronto i loro coefficienti vorrebbe una scala comune
   che non esiste.
