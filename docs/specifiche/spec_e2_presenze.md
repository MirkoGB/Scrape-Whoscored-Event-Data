# Fase 9 — Blocco E2: le presenze

> Da integrare in `docs/fasi/prompt_fase9.md` come specifica di E2. **Non
> sovrascrivere il file**: la tua copia è divergente dalla mia (G3 rimosso, E0
> ed E1 chiusi, sezioni aggiunte). Inserisci, non rimpiazzare.

---

## Bersaglio

Le **presenze fantacalcistiche** della stagione t+1, come distribuzione e non
come numero. Tre stati, tenuti separati: disponibile / impiegato / presenza
valida secondo la regola dell'80'.

Qui aspetta il 91% dell'errore del modello d'asta: MAE 61.4 → 5.6 con le
presenze note.

---

## Ordine di esecuzione. Non è indifferente

**Prima le squalifiche, che non si stimano.** Sono deterministiche dai
cartellini: cinque ammonizioni una giornata, l'espulsione una o più. Tenendo
conto del fatto già misurato che **85 espulsioni ma solo 65 tolgono un uomo dal
campo** — le altre sono ad allenatore o staff.

Misura quanta parte del divario oracolo si chiude **con quelle soltanto**, prima
che entri un solo predittore stimato. È il pezzo gratis e va speso per primo,
perché altrimenti finirà attribuito a qualche modello che non l'ha prodotto.

**Poi il prerequisito ancora aperto:** lo stato di convocazione. Se la coda di E0
non l'ha aggiunto, E2 non può partire — «convocato e non impiegato» è uno dei
tre stati del bersaglio e non esiste nel derivato finché i panchinari a zero
minuti non ci entrano.

---

## Predittori di distinta — la parte nuova

Ho tre script R miei, scritti a suo tempo su una forma diversa dei dati.
**Non sono codice da portare dentro**: due dei tre sono informazione, uno è da
scartare. Ti dico quale è quale e perché, così non lo riscopri.

### 1. Numero di maglia — è il predittore nuovo, ed è quello che vale

`Jersey_Modifier.R` estrae `JerseyNumber` dai qualifier della distinta, in
parallelo a `InvolvedPlayers`, esattamente come `PlayerPosition`.

**Perché lo voglio, ed è un argomento diverso dagli altri predittori:** il numero
di maglia è **assegnato prima che la stagione cominci**. Ogni altro predittore
d'impiego richiede che si sia già giocato. Questo è disponibile al momento della
previsione anche per un giocatore appena arrivato, che al nuovo club non ha
storia — cioè proprio il caso in cui E2 è più cieco. È la dichiarazione con cui
il club annuncia dove colloca quel giocatore nella gerarchia, e la fa in agosto.

Costruzione:

- chiave **(stagione, playerId, teamId)**, non (playerId, squadra). Il numero
  cambia fra stagioni e fra club: aggregare alla moda su più stagioni, come fa
  lo script R quando fonde col file esistente, distrugge esattamente il segnale
  che serve;
- **`teamName` non esiste nei nostri CSV**, c'è solo `teamId`: lo script R era
  scritto su una forma dei dati che aveva il nome. Ogni join va rifatto su
  `teamId`;
- **verifica se costa quasi zero.** Se `load_lineup_events` già parsa
  `PlayerPosition` dai qualifier del `FormationSet`, `JerseyNumber` è nella
  stessa lista: un campo in più da una struttura già attraversata. Se è così, non
  ha il costo di rilettura dei 1.889 CSV che hanno i piazzati in E4 — e va detto,
  perché cambia se questo predittore è economico o caro.

Come feature, e qui serve disciplina perché la tentazione di leggerlo come
ordinale è forte:

- **non è una scala.** Il 10 non è «meglio» del 30 lungo un continuo. Fasce
  dichiarate prima (1/12/22 portiere, cifra singola, 10, 11-25, 26-45, oltre) o
  effetto stimato per fascia, con la partizione fissata **prima** di guardare i
  risultati — vale il divieto di `argmax` e `quantile` che E1 ha già messo a
  test;
- **è confuso con ruolo ed età.** Un numero alto è spesso un giovane, e un
  giovane gioca poco per ragioni sue. Il test è **al netto di ruolo ed età**, non
  marginale, o misuri l'età e la chiami maglia;
- **il cambio di numero fra stagioni nello stesso club è una feature a sé**, e
  probabilmente più informativa del livello: prendere la 10, o passare dalla 7
  alla 47, è un fatto sulla gerarchia che il livello da solo non dice;
- passa dal registro di E1 come tutte le altre. La distribuzione dei numeri può
  derivare fra stagioni; se deriva, la regola vale anche qui.

### 2. Ruolo — conferma un codebook che era stato ricavato empiricamente

`Role_Modifier.R` dichiara la codifica Opta: **1 = portiere, 2 = difensore,
3 = centrocampista, 4 = attaccante, 5 = panchina**. Il repository era arrivato
allo stesso `role_code = 5` per la panchina osservando i dati. Registra la
corrispondenza in `CLAUDE.md` come codebook della fonte, con la nota che è
confermato da due strade indipendenti.

Due limiti dello script che **non** vanno importati:

- prende solo `FormationSet` e ignora `FormationChange`, quindi perde i cambi di
  ruolo a partita in corso;
- `distinct(playerId, .keep_all = TRUE)` tiene la prima occorrenza, cioè
  costringe il ruolo a essere una costante di partita. E2 vuole il ruolo come
  serie: chi cambia ruolo cambia rotazione, ed è un predittore d'impiego.

Ricorda che il ruolo **diverge già oggi fra le due fonti** su 133 giocatori su
609, e che restano due colonne (vincolo 7). Non riconciliarle qui.

### 3. Minuti — questo va scartato, e vale la pena sapere perché

`Minutes_Modifier.R` **calcola minuti sbagliati per quasi tutti i giocatori**.
`.extract_starters` prende tutti gli `InvolvedPlayers` del `PreMatch` — che sono
la rosa intera, panchina inclusa, come dimostrano i `PlayerPosition` con codice
5 — e assegna `start_sec = 0` a ciascuno. Poi `players_all` fonde titolari e
subentrati con `min(start_sec)`: chi entra al 70' ottiene `min(0, 4200) = 0`.

Ne segue che chi subentra risulta con la partita intera, e chi non è mai entrato
pure. Gli unici corretti sono i titolari sostituiti. Manca inoltre l'espulsione,
che non è un `SubstitutionOff` e lascia il giocatore in campo fino alla fine.

`sot/minutes.py` è validato e resta. Lo script serve solo come promemoria di due
casi limite da verificare esplicitamente nei test di E2: **il subentrato e
l'espulso**.

Un terzo difetto è comune a tutti e tre gli script e vale come avvertimento
generale: il fallback di join sul solo `playerId`, quando la chiave completa
fallisce, **moltiplica le righe** se quel `playerId` compare con due squadre. Un
invariante sul conteggio righe dopo ogni join lo intercetta.

---

## Gli altri predittori

Tutti standardizzati secondo il verdetto di E1 — e le cinque che richiedono
l'effetto di stagione entrano come tali, non escluse:

quota dei minuti di squadra e la sua traiettoria dentro la stagione; frequenza di
titolarità dal `role_code`; minuto medio di ingresso e di uscita; tocchi per 90
come misura di coinvolgimento; stabilità della posizione media in campo; tasso di
cartellini; età; cambio di squadra; e il terzo stato trovato dall'aggancio, i
giocatori che hanno giocato e che la fonte dei voti non elenca.

**Il pavimento di esposizione è un parametro di E2, non un dettaglio ereditato da
E1.** Sei candidate su 19 cambiavano verdetto fra i quattro pavimenti provati. Ma
qui il bersaglio sono le presenze, e i giocatori con pochi minuti non sono la
coda del campione: sono la parte che il modello deve indovinare. Un pavimento
alto rende E1 pulito e E2 cieco dove serve. Dichiara quello che usi e mostra i
risultati con gli altri tre accanto.

**Il limite che non si aggira:** gli infortuni non sono nei dati. Sono la
componente più grossa dell'assenza e questo blocco non li prevede. Va scritto
accanto a ogni numero, non in fondo al report.

---

## Valutazione

**La metrica è la quota del divario oracolo chiusa, non il MAE.** Il divario è
61.4 → 5.6, cioè 55.8 punti. Riporta la percentuale accanto al MAE grezzo, con i
quattro baseline già in uso e sulle stesse quattro transizioni del modello
d'asta. Separata per ruolo e per fascia di minutaggio: l'errore su un titolare
fisso e su una riserva sono problemi diversi, e mediarli li nasconde entrambi.

**Il numero di maglia va valutato due volte:** dentro il modello completo, e da
solo contro il baseline sul sottoinsieme che conta — i giocatori al primo anno in
un club, dove nessun altro predittore d'impiego esiste. Se serve, serve lì.

Se il risultato è che questi predittori non aiutano, quello è il risultato del
blocco e si scrive. Il progetto ha già tre risultati negativi ottenuti
correttamente e sono il suo contenuto migliore.