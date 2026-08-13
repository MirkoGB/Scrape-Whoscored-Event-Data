# Fase 11 / Blocco S1 — le soglie di tiri in porta del Como 2026-27

> Generato da `scripts/run_fase11_s1.py` il 2026-08-12.
> **Non tocca la rete e non scrive niente sotto `data/`.** L'unica informazione
> esterna sono i nomi delle tre promosse; le tre retrocesse che le accompagnano
> sono verificate contro la classifica ricostruita dai dati.
> Tabella completa (38 partite x 6 linee): `fase11_s1_soglie_como.csv`.
> **Pagina locale interattiva**: `fase11_s1_simulatore.html` — si apre con un doppio clic,
> funziona offline, e permette di far variare linea, quota e puntata e di
> incollare le quote vere riga per riga.

## 0. La domanda, e che cosa si puo' onestamente risponderle

La domanda era: **1 EUR su ogni partita del Como 2026-27, per ogni fascia di over
tiri in porta da 2.5 a 7.5, guadagno atteso** — con una stima della quota
probabile in base all'avversaria.

Il guadagno atteso di 1 EUR e' `P x quota - 1`. Di quei due fattori questo
progetto puo' produrre **il primo e non il secondo**: nel repository non
esistono prezzi di mercato. L'unico artefatto che ne porta
(`data/external/quote/como_tiri_in_porta_2025-2026.xlsx`) li deriva dalla `P` di
questo stesso modello piu' un margine ipotizzato, ed e' esattamente cio' che fa
il codice archiviato in `legacy/`, che `legacy/README.md` descrive come
«circolare e privo di significato».

`[DECISO 2026-08-12]` dall'utente: si pubblica **`P` e la quota di
pareggio `1/P`**, e il guadagno atteso come **funzione della quota fornita**. Il
caso «quota generata dal modello» resta, in §6, **per essere squalificato**.

**Che cosa e' nuovo qui.** `project_2627.monte_carlo` produceva solo il totale
stagionale, con un lambda costante sulle 38 giornate, senza avversario e senza
campo. Il ponte `lambda(Como, avversario, campo)` per il 2026-27 **non esisteva**
ed e' il contenuto del blocco.

---

## 1. Le squadre 2026-27, e l'unica verifica possibile sulla fonte

| voce | valore |
|---|---|
| retrocesse dai dati (classifica ricostruita) | Cremonese, Pisa, Verona |
| retrocesse dichiarate dalla fonte | Cremonese, Pisa, Verona |
| promosse dichiarate dalla fonte (NON verificabile in casa) | Venezia, Frosinone, Monza |

Le promosse sono **informazione esterna** e non sono verificabili in casa: la
Serie B non e' in questo repository. Le retrocesse arrivano dalla **stessa
pagina**, e quelle si': `calendar_2627.retrocesse()` le ricostruisce dai gol
delle righe partita, senza sapere niente della fonte. **Le due strade coincidono**,
e se non lo facessero anche le promosse andrebbero rimesse in discussione.

**Il calendario giornata per giornata c'e', ed e' costato quattro fonti.**
`verifica_calendario` ne ha **rifiutate tre**: elencavano il Como fra i propri
avversari, oppure la stessa squadra tre volte, oppure due volte in casa. La
quarta ha una struttura perfetta — 19 avversari, ognuno due volte, ognuno una
volta per campo — ma dava **37 righe su 38**.

**La riga mancante non e' stata indovinata: e' determinata.** Napoli compariva
solo in trasferta, quindi l'unica partita compatibile con la struttura e'
`Como-Napoli in casa`; delle 38 righe, l'unica cosa presa da fuori e' la sua
**giornata** (la 21a), che concorda su due fonti indipendenti. Una
corroborazione esterna che non e' stata usata per costruirlo: **le prime tre
giornate sono tutte in trasferta**, ed e' cio' che le fonti riportano a parte
per i lavori al Sinigaglia.

> **Il calendario resta un comodo, non una dipendenza, e un test lo blocca**:
> con e senza giornate i lambda e le probabilita' sono gli stessi. L'ordine non
> entra in nessuna somma — ogni avversario si gioca una volta per campo, quindi
> le 38 righe erano gia' determinate dalla sola lista delle venti squadre. Il
> calendario aggiunge **quando**, e serve a leggere la tabella per partita.
>
> Le **date** restano nulle: le fonti discordano, e qui non servono.

---

## 2. Il ponte: lambda per partita

**La struttura relativa viene dal modello, il livello dall'ancora.** E' la
lezione della Fase 6A: il livello pubblicato non contiene il modello di squadra,
quindi il modello dice *chi e' l'avversario e se si gioca in casa*, e l'ancora
dice *quanto vale la media*.

    lam_i = lam_modello_i / media(lam_modello) x ancora

Ancora = 4.9 x 1.01014 = 4.9497 (4.90 x rapporto compositivo), e la media dei 38 lambda
vale **4.949682**, cioe' l'ancora a precisione macchina. Un test lo
blocca: e' cio' che rende questa tabella coerente con la proiezione gia'
pubblicata invece di essere una seconda proiezione che le somiglia.

Le sei partite estreme:

| avversario | campo | promossa | exp_difesa | lam |
|---|---|---:|---:|---:|
| Juventus | trasferta | no | 0.7910 | 3.467 |
| Inter | trasferta | no | 0.8164 | 3.579 |
| Napoli | trasferta | no | 0.8447 | 3.703 |
| Sassuolo | casa | no | 1.1754 | 6.272 |
| Venezia | casa | si | 1.1277 | 6.018 |
| Monza | casa | si | 1.1277 | 6.018 |

> **Lo scenario sulle promosse NON sposta il livello**, e va detto prima che
> qualcuno lo scopra leggendo §7: la media delle 38 righe e' l'ancora per
> costruzione, qualunque difesa si assegni a Venezia, Frosinone e Monza. Muove
> solo **come** il livello si distribuisce fra le partite. E' la decisione della
> Fase 6E — applicare il fattore di calendario all'ancora sarebbe un doppio
> conteggio, perche' 4.90 esce da 21 stagioni che contengono gia' 21 ricambi di
> neopromosse.

---

## 3. Le sei soglie

`p_puntuale` tratta il livello 2026-27 come noto; `p_integrata` lo tratta come
incerto e media sulla distribuzione del Monte Carlo della proiezione (di cui lo
shock di squadra e' il 65%).

| linea | p_media | p_min | p_max | p_media_integrata | quota_pareggio_stagione | quota_pareggio_stagione_integrata | attese_su_38 |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 2.5 | 0.8353 | 0.6558 | 0.9299 | 0.8343 | 1.197 | 1.199 | 31.7 |
| 3.5 | 0.6908 | 0.4499 | 0.8426 | 0.6952 | 1.448 | 1.438 | 26.3 |
| 4.5 | 0.5284 | 0.2742 | 0.7197 | 0.5406 | 1.893 | 1.850 | 20.1 |
| 5.5 | 0.3749 | 0.1502 | 0.5763 | 0.3941 | 2.667 | 2.537 | 14.2 |
| 6.5 | 0.2482 | 0.0747 | 0.4323 | 0.2711 | 4.029 | 3.688 | 9.4 |
| 7.5 | 0.1542 | 0.0342 | 0.3043 | 0.1772 | 6.484 | 5.643 | 5.9 |

- **La colonna da leggere e' `quota_pareggio_stagione`**: e' la quota fissa a cui
  1 EUR su ogni partita della stagione va esattamente in pari. Sopra quel numero
  il guadagno atteso e' positivo, sotto e' negativo.
- **L'integrazione ingrassa le code nel verso previsto**, dichiarato prima di
  guardare i numeri: sulla 7.5 la probabilita' sale da
  0.1542 a
  0.1772, sulla 2.5
  scende da 0.8353 a
  0.8343. Non sapere
  quanto tirera' il Como **non e' neutro**: rende gli estremi piu' probabili.
- **Si integra solo l'incertezza di livello, mai il campionamento**: quest'ultimo
  e' gia' dentro `p_over`, e tenerlo acceso conterebbe le code due volte. Un test
  lo pretende.

### La dispersione fra le partite non e' un dettaglio

Sulla 4.5 la probabilita' va da **0.274**
(la partita piu' difficile) a **0.720**
(la piu' facile). Una quota unica per tutta la stagione sarebbe conveniente su
alcune partite e non su altre: e' il motivo per cui il CSV esce a 38 righe per
linea e non solo come media.

### `r` non e' stimata qui, e sulle code conta

| linea | r=13.7 | r=26 | r=111.8 | escursione |
|---:|---:|---:|---:|---:|
| 2.5 | 0.8171 | 0.8353 | 0.8520 | 0.0349 |
| 3.5 | 0.6731 | 0.6908 | 0.7079 | 0.0347 |
| 4.5 | 0.5177 | 0.5284 | 0.5389 | 0.0212 |
| 5.5 | 0.3737 | 0.3749 | 0.3758 | 0.0022 |
| 6.5 | 0.2548 | 0.2482 | 0.2410 | 0.0137 |
| 7.5 | 0.1652 | 0.1542 | 0.1429 | 0.0223 |

`r = 26.0` viene dalla Fase 2, con IC95% di profilo (13.7, 111.8). **L'effetto
non e' uniforme**: sulla 4.5 l'escursione e' piccola, sulla 7.5 vale una frazione
molto piu' grande della probabilita' stessa. Le due linee estreme sono quelle in
cui un'assunzione non stimata pesa di piu'.

---

## 4. Il guadagno atteso — 1 EUR su ognuna delle 38 partite

Ogni cella e' la **somma sulle 38 partite** di `p_i x q - 1`, cioe' cio' che si
attende chi mette 1 EUR su ogni partita a quella quota fissa. **Le quote sono
un'ipotesi di lettura, non prezzi osservati**: nessuno di questi numeri viene da
un mercato, e la griglia e' dichiarata in `soglie_2627.GRIGLIA_QUOTE`.

Su `p_puntuale`:

| linea | p_media | quota_pareggio_stagione | q=1.20 | q=1.50 | q=1.80 | q=2.00 | q=2.50 | q=3.00 | q=4.00 | q=6.00 | q=10.00 |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 2.5 | 0.8353 | 1.197 | 0.09 | 9.61 | 19.13 | 25.48 | 41.35 | 57.22 | 88.97 | 152.45 | 279.42 |
| 3.5 | 0.6908 | 1.448 | -6.50 | 1.38 | 9.25 | 14.50 | 27.63 | 40.75 | 67.00 | 119.50 | 224.50 |
| 4.5 | 0.5284 | 1.893 | -13.91 | -7.88 | -1.86 | 2.16 | 12.20 | 22.24 | 42.31 | 82.47 | 162.79 |
| 5.5 | 0.3749 | 2.667 | -20.90 | -16.63 | -12.36 | -9.51 | -2.38 | 4.74 | 18.99 | 47.48 | 104.47 |
| 6.5 | 0.2482 | 4.029 | -26.68 | -23.85 | -21.02 | -19.14 | -14.42 | -9.71 | -0.28 | 18.59 | 56.31 |
| 7.5 | 0.1542 | 6.484 | -30.97 | -29.21 | -27.45 | -26.28 | -23.35 | -20.42 | -14.56 | -2.84 | 20.61 |

Su `p_integrata` (la stessa cosa, con l'incertezza di livello dentro):

| linea | p_media | quota_pareggio_stagione | q=1.20 | q=1.50 | q=1.80 | q=2.00 | q=2.50 | q=3.00 | q=4.00 | q=6.00 | q=10.00 |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 2.5 | 0.8343 | 1.199 | 0.04 | 9.55 | 19.06 | 25.40 | 41.26 | 57.11 | 88.81 | 152.21 | 279.02 |
| 3.5 | 0.6952 | 1.438 | -6.30 | 1.63 | 9.55 | 14.84 | 28.05 | 41.25 | 67.67 | 120.51 | 226.18 |
| 4.5 | 0.5406 | 1.850 | -13.35 | -7.18 | -1.02 | 3.09 | 13.36 | 23.63 | 44.18 | 85.26 | 167.44 |
| 5.5 | 0.3941 | 2.537 | -20.03 | -15.53 | -11.04 | -8.05 | -0.56 | 6.93 | 21.91 | 51.86 | 111.77 |
| 6.5 | 0.2711 | 3.688 | -25.64 | -22.55 | -19.45 | -17.39 | -12.24 | -7.09 | 3.21 | 23.82 | 65.03 |
| 7.5 | 0.1772 | 5.643 | -29.92 | -27.90 | -25.88 | -24.53 | -21.17 | -17.80 | -11.06 | 2.40 | 29.34 |

**Come si legge.** Si prende la riga della linea che interessa e si cerca la
colonna della quota che il mercato offre davvero: quel numero e' il guadagno
atteso in euro su 38 euro puntati. Il segno cambia esattamente alla
`quota_pareggio_stagione`.

**Le due tabelle non danno la stessa risposta sulle linee estreme**, ed e' il
motivo per cui ci sono entrambe: sulla 7.5 l'integrazione sposta la quota di
pareggio da 6.48 a
5.64.

---

## 5. Regge, questo macchinario? La verifica sul 2025-26

Senza questa sezione le tabelle sopra sarebbero numeri senza garanzia. Si usano i
lambda **walk-forward** della Fase 2 — non un fit sull'intera stagione, che
sarebbe in campione — e la `r` ricostruita riga per riga sul solo passato.
Baseline: il tasso base walk-forward di ciascuna linea.

| linea | n | eventi_osservati | p_media | frequenza_osservata | brier_modello | brier_tasso_base | differenza | mde_brier |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 2.5 | 33 | 27 | 0.8074 | 0.8182 | 0.1368 | 0.1541 | -0.0173 | 0.0388 |
| 3.5 | 33 | 22 | 0.6505 | 0.6667 | 0.2308 | 0.2450 | -0.0142 | 0.0764 |
| 4.5 | 33 | 18 | 0.4823 | 0.5455 | 0.2572 | 0.2852 | -0.0279 | 0.0728 |
| 5.5 | 33 | 16 | 0.3306 | 0.4848 | 0.2723 | 0.3150 | -0.0427 | 0.0655 |
| 6.5 | 33 | 11 | 0.2109 | 0.3333 | 0.2245 | 0.2633 | -0.0387 | 0.0527 |
| 7.5 | 33 | 4 | 0.1262 | 0.1212 | 0.1109 | 0.1153 | -0.0043 | 0.0277 |

Pendenza di calibrazione sulle sole partite del Como:
**0.602 ± 0.516** (z = -0.77 contro 1.0),
su n = 33.

> **Il limite sta qui e non in fondo: sono 33 partite di una squadra sola.**
> La colonna `mde_brier` dice quanta differenza servirebbe per distinguere il
> modello dal tasso base: su questa numerosita' **esclude divari grandi e non
> divari piccoli**. E' la lezione della 6D applicata a questo blocco.
>
> **Le linee 6.5 e 7.5 sono un'estrapolazione dichiarata.** `validate.LINES` si
> ferma a 5.5: il Brier pubblicato dalle Fasi 2 e 4 non e' mai stato misurato
> oltre. Su quelle due linee gli eventi sono pochi e la sensibilita' a `r` e'
> massima (§3). Vanno lette come le meno solide delle sei, e un test verifica che
> la costante `LINEE` porti questa avvertenza accanto a se'.

---

## 6. Se la quota la genera il modello — l'identita' che squalifica il conto

E' la risposta letterale alla domanda «stima la quota probabile e calcola il
guadagno», e sta qui **per essere squalificata**, non letta.

| overround | linea | guadagno_proporzionale_per_partita | dispersione_proporzionale | guadagno_potenza_per_partita | dispersione_potenza | guadagno_proporzionale_su_38 |
|---:|---:|---:|---:|---:|---:|---:|
| 1.05 | 2.5 | -0.047619 | 0.000000 | -0.0186 | 0.0047 | -1.8095 |
| 1.05 | 3.5 | -0.047619 | 0.000000 | -0.0295 | 0.0088 | -1.8095 |
| 1.05 | 4.5 | -0.047619 | 0.000000 | -0.0474 | 0.0175 | -1.8095 |
| 1.05 | 5.5 | -0.047619 | 0.000000 | -0.0788 | 0.0350 | -1.8095 |
| 1.05 | 6.5 | -0.047619 | 0.000000 | -0.1335 | 0.0667 | -1.8095 |
| 1.05 | 7.5 | -0.047619 | 0.000000 | -0.2229 | 0.1130 | -1.8095 |
| 1.07 | 2.5 | -0.065421 | 0.000000 | -0.0253 | 0.0066 | -2.4860 |
| 1.07 | 3.5 | -0.065421 | 0.000000 | -0.0405 | 0.0121 | -2.4860 |
| 1.07 | 4.5 | -0.065421 | 0.000000 | -0.0650 | 0.0237 | -2.4860 |
| 1.07 | 5.5 | -0.065421 | 0.000000 | -0.1068 | 0.0458 | -2.4860 |
| 1.07 | 6.5 | -0.065421 | 0.000000 | -0.1766 | 0.0825 | -2.4860 |
| 1.07 | 7.5 | -0.065421 | 0.000000 | -0.2835 | 0.1289 | -2.4860 |
| 1.10 | 2.5 | -0.090909 | 0.000000 | -0.0345 | 0.0096 | -3.4545 |
| 1.10 | 3.5 | -0.090909 | 0.000000 | -0.0561 | 0.0170 | -3.4545 |
| 1.10 | 4.5 | -0.090909 | 0.000000 | -0.0900 | 0.0321 | -3.4545 |
| 1.10 | 5.5 | -0.090909 | 0.000000 | -0.1455 | 0.0592 | -3.4545 |
| 1.10 | 6.5 | -0.090909 | 0.000000 | -0.2332 | 0.0994 | -3.4545 |
| 1.10 | 7.5 | -0.090909 | 0.000000 | -0.3574 | 0.1418 | -3.4545 |

- **Con margine proporzionale il guadagno atteso vale `1/overround - 1`, lo
  stesso numero su ogni partita e su ogni linea, con dispersione zero.** Non
  contiene una sola informazione sul Como: e' il margine, scritto al contrario.
  Un test lo verifica a precisione macchina.
- **Con margine a potenza (Buchdahl) il guadagno varia con `p`, e varia molto**:
  a overround fissato passa da -0.0186 sulla 2.5 a -0.2229 sulla 7.5,
  cioe' un fattore 12, mentre fra i tre overround a linea fissata
  cambia meno del doppio. **La linea conta piu' del margine, ed e' proprio questo
  che rende la tabella ingannevole**: sembra che il modello stia dicendo che
  l'Over 7.5 e' un pessimo affare, e invece `p^(1-1/k) - 1` e' una funzione della
  sola `p` — la trasformazione a potenza penalizza le probabilita' piccole, e di
  Como li' dentro non c'e' niente.
- **Il segno dipende da come il margine viene applicato, non da quanto il modello
  sia buono.** Qui e' negativo ovunque perche' il margine e' messo *a favore del
  banco*, che e' la convenzione onesta; applicandolo dall'altra parte
  diventerebbe positivo ovunque, con la stessa identica `P`. E' precisamente cio'
  che `legacy/README.md` descrive: «qualunque regola sistematica risulta
  redditizia per costruzione: il margine e' l'unica cosa che separa le due parti,
  e il segno del risultato dipende solo da come e' stato applicato».

> **Quindi: quanto si guadagna davvero non e' rispondibile con i dati in casa.**
> Non per prudenza — per assenza del secondo fattore. §3 e §4 danno tutto cio'
> che serve per rispondere nel momento in cui un prezzo vero esiste.

---

## 7. Gli scenari sulle promosse

| scenario | natura | media_lambda | sd_fra_partite | p_over_4.5_media | lambda_vs_promossa_casa |
|---|---|---:|---:|---:|---:|
| media di campionato | estremo: promosse forti come una squadra qualunque | 4.949682 | 0.7058 | 0.5289 | 5.479 |
| peggiore difesa 2025-26 | estremo: tutte e tre porose come la piu' battuta | 4.949682 | 0.7807 | 0.5274 | 6.320 |
| come le retrocesse | status quo: e' cio' che il codice assume oggi | 4.949682 | 0.7370 | 0.5284 | 6.018 |
| coorte promossa 2025-26 | riferimento empirico, UNA coorte sola | 4.949682 | 0.7647 | 0.5278 | 6.222 |

La colonna `media_lambda` e' **costante per costruzione** (§2). Cio' che si muove
e' `sd_fra_partite` e il lambda contro una promossa in casa, che va da
5.48 a 6.32
a seconda di quanto si assume porose le tre neopromosse. **Su `P(Over 4.5)` media
l'effetto e' minuscolo** (0.5274 –
0.5289): lo scenario ridistribuisce, non aggiunge.

**Perche' non si prendono le loro stagioni storiche.** Monza, Venezia e Frosinone
hanno righe nelle cinque stagioni gia' in casa. Usarle vorrebbe dire due cose che
il progetto ha gia' escluso: confrontare unita' grezze fra stagioni in cui la
media di campionato si e' mossa del 10,1% (regola di E1), e trattare una rosa di
due o quattro anni fa come una stima di quella di oggi. Lo scenario e' meno
preciso e non e' sbagliato.

---

## 8. Domande aperte

1. **I prezzi di mercato reali restano l'unica cosa che manca** per rispondere
   alla domanda come e' stata posta. Sono un blocco di acquisizione a se', con i
   vincoli 7-8-9 e una decisione dell'utente sulla fonte — e servirebbero
   **quote di chiusura pre-partita**, non quote correnti, altrimenti il confronto
   eredita lo stesso difetto di orologio che ha squalificato il FVM.
2. **Il calendario vero non e' stato acquisito.** Non serve a queste tabelle, ma
   servirebbe a due cose che qui non ci sono: la sequenza cronologica, e le
   giornate dopo un turno di Champions — dove `calendar_2627.LIMITE_CONGESTIONE`
   dichiara un effetto di **segno noto e negativo**, mai stimato, che su quelle
   partite rende queste probabilita' ottimistiche.
3. **La difesa delle promosse resta uno scenario e non una stima.** E' la stessa
   domanda aperta della Fase 6E, e qui pesa meno di quanto si temesse (§7).
4. **Le linee 6.5 e 7.5 non hanno una validazione propria**: sono fuori dal
   perimetro su cui il Brier e' stato misurato, e su di esse `r` conta il doppio.
   Validarle vorrebbe piu' stagioni, cioe' la stessa massa che R2 e R3 chiedevano.
5. **La guardia del vincolo 3 di R2/R2-bis/R3 e' latentemente sbagliata**, e lo
   si e' scoperto scrivendo quella di questo blocco: cerca sottostringhe, quindi
   `roi` scatta dentro `proiezione` e `bankroll` **non** scatta dentro
   `calcola_bankroll`. Qui e' corretta con un confine di lettera e un test che
   verifica entrambe le direzioni; **nei tre moduli di Fase 10 non e' stata
   toccata**, perche' cambiare un test che oggi passa non era in questo blocco.
