# Fase 9 — i dati evento come predittori, e cosa c'è oltre il fantacalcio

> Prompt per Claude Code, da incollare in una sessione aperta sul repository.
> Sostituisce i due file precedenti (`prompt_claude_code_fantacalcio.md` e
> l'addendum sui dati): erano scritti senza conoscere `CLAUDE.md` e proponevano
> in gran parte cose già fatte, spesso meglio.

---

## Premessa che vincola tutto quello che segue

Ho letto `CLAUDE.md`. Il progetto ha già: modello di squadra validato (Fasi 2-4),
xG interno cross-fitted, verifica di stabilità del criterio su cinque stagioni,
voti e quotazioni acquisiti, aggancio delle due fonti, regola dell'80' misurata,
modello per l'asta con walk-forward su quattro transizioni, modificatore
simulato per giornata e per modulo.

**Tre risultati già stabiliti condizionano questa fase e non vanno rimessi in
discussione per comodità:**

1. **Gli otto predittori da dati evento sono stati scartati due volte** (Fase 2,
   Fase 6D), con la potenza dichiarata. Erano **medie mobili di squadra contro un
   target di squadra già coperto dagli effetti attacco/difesa con decadimento**.
   Quella conclusione resta valida **per quel test**. Non è una prova su un
   target diverso, e questa fase riguarda un target diverso: i punti stagionali
   del singolo giocatore. Il vincolo di `CLAUDE.md` — «non reintrodurli senza
   nuove prove» — si soddisfa così: nuovo bersaglio, nuovo livello di
   aggregazione, potenza dichiarata **prima** di guardare l'esito.

2. **Il 91% dell'errore del modello d'asta sta nelle presenze**: MAE 61.4 → 5.6
   con le presenze note, contro 52.5 con i bonus noti. Quindi i dati evento vanno
   puntati sull'**impiego**, non sui bonus. Chi parte dai bonus lavora sul 9%
   residuo del problema.

3. **Sui portieri il modello fa Spearman 0 perché non guarda la squadra.** Il
   modello di squadra validato esiste già: va collegato. È il difetto con la
   causa più chiara di tutto il progetto.

**Ordine.** `CLAUDE.md` dice che il blocco successivo è **7B**. Prima di
cominciare, dimmi come questa fase si colloca rispetto a 7B: se lo precede, se lo
segue, o se una parte di E0 è di fatto un pezzo di 7B. Non decidere tu.

**Valgono tutti i vincoli 1-9**, le convenzioni, `./.venv/Scripts/python.exe`,
nessun percorso scritto a mano, un report per blocco, e **ci si ferma alla fine
di ogni blocco**.

---

## Blocco E0 — ricostruzione multi-stagione. È il prerequisito, e oggi è un blocco duro

Nome per esteso: **`player_match` 2021-2025 + estensione dell'aggancio giocatori
alle altre quattro stagioni**. Nessuna richiesta di rete: è calcolo sui 1.889 CSV
già acquisiti. Chiude il limite dichiarato in fondo alla sezione «aggancio delle
due fonti» di `CLAUDE.md`.

`player_match.parquet` esiste **per la sola 2025-2026**, e per la stessa ragione
l'aggancio dei giocatori copre una stagione sola. Con una stagione non esiste
walk-forward: il modello d'asta gira su quattro transizioni e un predittore che
esiste su una sola non è testabile. **Finché E0 non è chiuso, tutto il resto di
questa fase non è eseguibile**, e va detto adesso invece di scoprirlo a metà.

Cosa serve:

- **`player_match` su tutte e cinque le stagioni**, dai 1.889 CSV. Le trappole
  note valgono tutte: `isOwnGoal` assente in gran parte dei file e da forzare a
  `False`, `(matchId, teamId, eventId)` non unica, `maxMinute` a volte minore
  dell'ultimo evento, `role_code = 5` che significa panchina, rigori
  riconoscibili solo da `penaltyScored | penaltyMissed`.
- **Aggancio dei giocatori esteso alle cinque stagioni**, con il tasso riportato
  **per stagione**. Il 609/609 della 2025-26 non è una previsione sulle altre:
  più stagioni significano più omonimi, più prestiti, più giocatori con poche
  presenze. Il residuo si mostra, non si risolve d'ufficio.
- **Denominatori dai dati, mai assunti a 38**: 35 per l'Atalanta nelle due
  stagioni bucate, 39 per Spezia e Verona nel 2022-23. Le 12 partite assenti alla
  fonte **non sono casuali rispetto alla squadra** e questo entra in ogni tasso
  per 90 e in ogni conteggio di presenze.

**Deliverable:** `reports/fase9_e0_player_match_5_stagioni.md` + i Parquet.
Poi ti fermi.

---

## Blocco E1 — regola di costruzione delle feature. Va scritta una volta e imposta

Questo blocco non produce modelli: produce il vincolo che tutti gli altri
rispettano, e nasce direttamente dalla verifica di stabilità già fatta.

Sappiamo che fra le cinque stagioni: `shotCounter` passa da 3.4% a 7.7%,
`shotOpenPlay` scende di 7.5 punti, `Clearance` +48%, `BallRecovery` −26%,
`Error` +162%, `StandingSave` è **la stessa etichetta su id diversi** in due
versioni del dizionario della fonte. Sono esattamente le grandezze da cui
verrebbero le feature del voto base.

**Ne segue una regola, non un suggerimento:**

> Nessuna feature da dati evento entra in un modello multi-stagione **in unità
> grezze**. Ogni feature entra come **scarto relativo alla media di campionato
> della propria stagione** — la stessa forma che `CLAUDE.md` prescrive per `rho`
> («eccessi relativi alla media di campionato della stagione, non scarti
> assoluti»). Dove la standardizzazione non basta, la stagione entra come effetto
> esplicito.

**La regola vive nello strato feature, non nel derivato.** `player_match` resta
fedele: unità grezze, più la media di campionato della stagione **come colonna
accanto**. La deriva si porta avanti, non si normalizza via — cancellarla dentro
il derivato sarebbe cancellare un fatto misurato, ed è il vincolo 4. La
standardizzazione avviene al momento in cui la feature entra in un modello
multi-stagione, dove il derivato resta ricostruibile all'indietro.

Corollari da implementare come test, non come buone intenzioni:

- **Nessuna feature costruita sul nome di un qualifier** senza aver verificato la
  sua frequenza nelle cinque stagioni. `StandingSave` è la dimostrazione che il
  nome non è un identificatore.
- **Un test che fallisce** se una colonna di feature multi-stagione ha una media
  di stagione che si muove oltre una soglia dichiarata senza essere stata
  standardizzata.
- Le **72 colonne mai valorizzate** restano fuori. Porta inviolata, gol subiti e
  precisione dei passaggi **si derivano**, e la misura giusta di presenza è «né
  nullo né `False`», non `notna()`.

**Deliverable:** `sot/features_giocatore.py` con la standardizzazione dentro, e
`reports/fase9_e1_stabilita_feature.md` che mostra per ogni feature candidata la
sua deriva fra stagioni **prima e dopo**.

---

## Blocco E2 — le presenze. È qui che il 91% dell'errore aspetta

> Specifica completa, dall'utente il 2026-08-04 (era
> `docs/specifiche/spec_e2_presenze.md`). Sostituisce lo stub che stava qui: quello elencava
> i candidati, questa aggiunge l'ordine di esecuzione, i predittori di distinta e
> il criterio di valutazione.

### Bersaglio

Le **presenze fantacalcistiche** della stagione t+1, come distribuzione e non
come numero. Tre stati, tenuti separati: disponibile / impiegato / presenza
valida secondo la regola dell'80'.

Qui aspetta il 91% dell'errore del modello d'asta: MAE 61.4 → 5.6 con le
presenze note.

### Ordine di esecuzione. Non è indifferente

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

### Predittori di distinta — la parte nuova

Ho tre script R miei, scritti a suo tempo su una forma diversa dei dati.
**Non sono codice da portare dentro**: due dei tre sono informazione, uno è da
scartare. Ti dico quale è quale e perché, così non lo riscopri.

#### 1. Numero di maglia — è il predittore nuovo, ed è quello che vale

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

#### 2. Ruolo — conferma un codebook che era stato ricavato empiricamente

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

#### 3. Minuti — questo va scartato, e vale la pena sapere perché

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

### Gli altri predittori

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

### Valutazione

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

---

## Blocco E3 — collegare il modello di squadra: portieri, gol subiti, modificatore

È il difetto con la causa più identificata del progetto, e la strada è già scritta
nella trappola in fondo alla sezione del modello d'asta.

- **Estendi il modello di squadra dai tiri in porta ai gol subiti.** Stessa
  specificazione (`mu + attacco_i + difesa_j + gamma*casa`, ridge, decadimento),
  bersaglio diverso. **Rivalidalo per conto suo**: che sia calibrato sui SoT non
  dice niente sui gol, e mescolare le due validazioni sarebbe il vincolo 7 letto
  male. Baseline accanto, come sempre.
- **Porta inviolata** come `P(Poisson(lambda_subiti) = 0)` per partita, non come
  frequenza storica.
- **Malus del portiere** dalla stessa distribuzione, non dal conteggio dell'anno
  prima.
- **Voto base della linea difensiva** condizionato alla forza difensiva della
  squadra: è l'ingresso del modificatore (§2.2), che vale fino a +6 ed è quindi
  la leva più alta del prodotto.

**Verifica dedicata:** lo Spearman sui **portieri**, oggi 0 contro 0.667 del FVM.
È il numero che dice se il collegamento è servito. Riportalo separato, non
annegato nella metrica complessiva.

**Un limite già noto da non perdere**: la simulazione del modificatore assume i
membri della linea indipendenti, e una difesa che prende tre gol prende voti bassi
*insieme*. Collegare il modello di squadra è anche l'occasione per introdurre
quella correlazione — ma solo se la si misura, e con fasce a scalini il segno
dell'effetto non è ovvio.

---

## Blocco E4 — voto base e bonus

> Specifica completa, dall'utente il 2026-08-07 (era `docs/specifiche/spec_e4_voto_bonus.md`).
> Sostituisce lo stub che stava qui: quello dava la cornice e i candidati, questa
> aggiunge l'ordine di esecuzione, il costo della rilettura, il criterio di
> valutazione e i gate ereditati. **Cosa lo stub diceva e questa non ripete** —
> due candidati che restano validi: *posizione media e tocchi in area*, per il
> ruolo offensivo effettivo contro quello di listone, sapendo che **il ruolo
> diverge già oggi fra le due fonti** su 133 giocatori su 609 e che restano due
> colonne (vincolo 7); e *falli commessi per 90* come predittore dei cartellini,
> che E4.4 riprende senza nominare la posizione media.
>
> Legge come prerequisito tutto ciò che E1, E2, E3 e (b) hanno già stabilito — in
> particolare il gate di E1 e il gate del FVM in `sot/quotazioni.py`.

### Cornice

Con i bonus noti il MAE scende da 61,4 a 52,5: il margine qui è di ~9 punti,
contro i ~56 delle presenze. È l'ultimo blocco di modellazione prima che il
tetto — gli infortuni, non nei dati — diventi il limite dichiarato del
progetto invece che un limite fra altri.

**Dichiara potenza e MDE prima di guardare l'esito**, come per QI in (b) e come
per 6D. Il test appaiato con MDE resta lo standard: un t che non supera il
proprio MDE non è un nulla, è un test cieco a quella dimensione, e va scritto
così.

### E4.0 — la rilettura dei CSV. Prerequisito, costo già noto

`events_slim` non porta `qualifiers`, quindi non c'è incarico sui piazzati senza
riattraversare i 1.889 CSV grezzi. Costo già misurato: ~4 minuti a freddo, poi
cache — la stessa cifra con cui si è deciso di scartare i piazzati da E1.

Estrai, per (stagione, matchId, teamId, playerId): chi ha battuto un rigore
(convertito o no), chi ha battuto un corner, chi ha battuto una punizione
diretta o indiretta. Salva come derivato a sé, non dentro `player_match` —
è dati grezzi riletti per uno scopo specifico, non una ricostruzione
strutturale come `player_match` è stata in E0.

**Test di quadratura**: il numero di rigoristi distinti per squadra-stagione
dev'essere piccolo (1-2 nella grande maggioranza dei casi) — se ne escono
cinque per una squadra in una stagione, il parsing ha un problema, non la
squadra ha davvero cinque rigoristi.

### E4.1 — voto base

Regressione del voto Redazione su feature evento per ruolo, sul rating
WhoScored, sul risultato di partita e sulla forza relativa delle due squadre —
com'era già previsto. Il voto Redazione **non è** il rating WhoScored: la
mappatura si calibra, non si assume.

Passa dal registro di E1: ogni candidata grezza standardizzata secondo il suo
verdetto già misurato, le cinque irriducibili con l'effetto di stagione
esplicito. Non riaprire il gate — è già chiuso, si applica.

Stima l'effetto giocatore con shrinkage e riporta la varianza residua: è la
parte di voto che nessun modello prende, e va dichiarata come tale, non
nascosta migliorando l'R² con più parametri.

### E4.2 — gol e assist

npxG e xA per 90 dagli eventi tiro e dai passaggi chiave, moltiplicati per la
quota di minuti e corretti per la forza offensiva di squadra (E3.1, già
rivalidato sui gol). La conversione sopra o sotto attese è quasi tutta rumore:
shrinkala pesantemente e dillo — non è un'assunzione nuova, è la stessa lezione
di E2 sulle presenze applicata alla finalizzazione.

**Se npxG interno entra qui, il problema dei cinque fit non è chiuso da E3.**
E3.1 non usa l'xG interno; questo blocco sì. Verifica se la differenza fra i
cinque fit di E0/E1 è di sola intercetta prima di sommarli attraverso le
stagioni — è la stessa verifica rimandata due volte, va fatta qui perché qui è
la prima volta che serve davvero.

### E4.3 — rigori. Assegnazione discreta, non tasso

Un rigorista designato vale +3 per rigore segnato e −3 per uno sbagliato: poca
massa, alta leva, dipende da un'assegnazione discreta. Modello: rigori attesi
della squadra (da E3.1) × P(è lui il designato, da E4.0) × tasso di
realizzazione fortemente shrinkato verso la media di lega.

Il designato 2026/27 è un input, non una stima: parametrizzalo con la
possibilità di impostarlo a mano, e mostra la sensibilità del totale a quel
singolo switch — è la stessa istruzione della specifica originale, non è
cambiata.

### E4.4 — cartellini e autogol

Cartellini: tasso di ammonizioni per 90 su falli commessi (da E4.0 se
disponibili, altrimenti da `events_slim`), ruolo, posizione media. Le
espulsioni sono rare: tasso di lega per ruolo, shrinkage quasi totale.

**Attenzione alla fonte del malus**: il gate di E2 ha già stabilito che è la
fonte dei voti ad alimentare i punti, non WhoScored — WhoScored resta un
predittore, mai il bersaglio. Non invertirlo qui per comodità di join.

Autogol: tasso base per ruolo, nessun effetto individuale. Non c'è segnale, e
il test lo verifica confrontando un modello con effetto individuale contro
quello senza: se il primo non batte il secondo fuori campione, resta il
secondo.

### E4.5 — QI come candidato, con lo stesso avvertimento di (b)

Il prezzo può contenere informazione sul rendimento atteso, non solo sulla
presenza — è plausibile quanto lo era per l'impiego. Provalo come candidata sul
voto base e sui bonus, con lo stesso protocollo di (b): potenza dichiarata
prima, forma scelta come ipotesi e non dopo aver visto i numeri, R² contro il
resto del set misurato per isolare quanto è già spiegato da altro.

**Il rifiuto che (b) ha già scritto vale anche qui, esplicitamente**: un
risultato positivo su QI-per-l'impiego non è licenza per assumere che QI aiuti
anche qui. Si misura di nuovo, da zero, sullo stesso standard.

Il FVM resta squalificato per l'intera Fase 9 — il gate in `sot/quotazioni.py`
non si riapre per questo blocco.

### Valutazione

Le stesse quattro transizioni, gli stessi quattro baseline, la stessa
metrica di E2: quota del divario oracolo chiusa (55,8 punti di MAE), non il
MAE grezzo da solo — qui il divario di riferimento è quello dei bonus, 61,4 →
52,5, cioè 8,9 punti. Riporta la percentuale di *quello* divario chiusa,
accanto al MAE assoluto.

Separata per ruolo: un rigorista sbagliato pesa diversamente da un difensore
mediocre, e mediare le nasconde entrambe.

**Il test sui portieri non si ripete qui** — è già chiuso in E3 con la sua
propria domanda aperta. Se E4 tocca il voto base dei portieri per coerenza di
pipeline, non ne trarre conclusioni nuove sul divario coi probabili titolari:
quella domanda resta dove E3 l'ha lasciata.

### Chiusura

`reports/fase9_e4_voto_bonus.md`, test dedicati, `CLAUDE.md` aggiornato.
Rieseguire `run_phase1.py` e `run_phase5.py`, confermare gli stessi numeri
pubblicati o dichiarare la rottura. Domande aperte in fondo, comprese quelle
ereditate e non risolte (numero di maglia e FVM d'agosto, appaiate; la domanda
sui portieri probabili titolari).

Se npxG, rigori, cartellini o QI non aggiungono nulla sopra il gate, è un
risultato negativo e si scrive come tale — il progetto ne ha già tre e sono il
suo contenuto migliore.

Fermati a fine blocco.

**L'xG interno non si stima su più stagioni insieme** senza effetto di stagione:
è già misurato che i suoi ingressi derivano.

---

## Oltre il fantacalcio — tre direzioni, in ordine di valore

Non le faccio tutte adesso. Voglio che tu me le rimetta in fila con il tuo
giudizio, e poi ne scelgo una.

> **Erano quattro.** La quarta era `rho` e l'ancora 4.90 — la domanda singola
> piu' grande sulla proiezione, 19 tiri e il 21% dell'IC80% — ed **e' stata
> tolta da qui perche' e' gia' la Fase 7**, cioe' il ramo `7B → 7C → 7D`
> descritto in `docs/fasi/prompt_fase7.md`. Due rami che convergono sulla stessa
> domanda sono un modo di farla due volte, e il secondo modo sarebbe stato
> quello senza i dati: la Fase 7 va a prendere la fonte tabellare che serve,
> questa fase non ha niente con cui rispondere. **Non e' rinviata, e' altrove.**

**G1 — dalla proiezione al risultato.** Il modello di squadra sui gol (E3) porta
naturalmente alla distribuzione del risultato, quindi a 1X2, over/under, e alla
simulazione della classifica: probabilità di scudetto, di Europa, di
retrocessione. È il prodotto più ampio e riusa quasi tutto ciò che esiste.
**Con un vincolo che non si aggira**: il vincolo 3 vieta il backtest su quote
generate dal modello, e il codice che lo faceva è già in `legacy/`. Senza prezzi
di mercato reali si può valutare la previsione con RPS e log-loss contro i
baseline, ma **non si può affermare niente sul valore scommesso**. Se serve
quello, prima servono le quote di chiusura, ed è un'altra acquisizione.

**G2 — altri campionati.** Lo scraper è già parametrizzato su campionato e
stagione, quindi il costo è basso. E risolve **tre domande aperte in un colpo**:
la potenza del test dei predittori (servono 13.5 stagioni-campionato per l'80%,
e una sola Serie A non le darà mai), la traduzione fra campionati per i nuovi
arrivi (D7, oggi non stimabile perché il campionato di provenienza non è nel
repository), e più massa per `rho`. **A mio giudizio è la direzione con il
rapporto valore/costo migliore**, ed è anche l'unica che sblocca cose già
bloccate.

**G3 — valutazione e scouting.** Il residuo fra proiezione e quotazione è già il
prodotto del modello d'asta; generalizzato con G2 diventa individuazione di
giocatori sottovalutati fra campionati.

> **CONDIZIONE RISCRITTA il 2026-08-07.** Diceva: «ha senso solo dopo che il
> modello batte il FVM, e oggi non lo batte: Spearman 0.452 contro 0.811».
> **Quella condizione non significa più niente**, e non perché sia stata
> soddisfatta: il FVM è stato **squalificato**, non battuto. `quotazioni.orologio()`
> ha misurato che il FVM della pagina archiviata sta sull'orologio di `QA`, cioè
> si muove *durante* la stagione, quindi per una stagione passata ne conosce
> l'esito. Lo 0.811 era un concorrente contaminato, e un modello che lo
> "battesse" non avrebbe dimostrato niente.
>
> **La condizione vera è contro `QI`**, che è l'unica quotazione davvero nota al
> momento dell'asta — e contro QI il verdetto **non è "perde": è misto**, e le due
> metriche non dicono la stessa cosa:
>
> | metrica | QI | modello | chi vince |
> |---|---:|---:|---|
> | Spearman (tutto l'ordine) | **0.606** | 0.452 | QI |
> | precisione sui primi N (la testa) | 0.162 | **0.177** | il modello |
>
> Ne segue che **G3 non è né sbloccata né bloccata: la sua condizione va decisa,
> non verificata.** Chi la riprende deve dire quale delle due metriche conta per
> lo scouting — verosimilmente la testa, perché è ciò che si compra — e allora la
> condizione è già soddisfatta; se conta tutto l'ordine, non lo è. **Non si
> rimetta il FVM in quel ruolo per far tornare il confronto**: è squalificato da
> una misura riproducibile, e un test pretende che il nome nudo non ricompaia.

---

## Come si chiude ogni blocco

Codice, test, report in italiano, e **le domande aperte in fondo**. Poi ti fermi.

Due cose che non voglio vedere:

- **numeri pubblicati che cambiano senza che sia stato verificato**: ogni blocco
  riesegue `run_phase1.py` e `run_phase5.py` e dichiara che Como 4.34 e
  5.03 / 191 / [151, 240] sono ancora quelli, oppure spiega perché no;
- **un risultato negativo sistemato.** Se i predittori evento non aiutano nemmeno
  sulle presenze, quello è il risultato del blocco e si scrive. Il progetto ha già
  tre risultati negativi ottenuti correttamente e sono il suo contenuto migliore.

Comincia da **E0**, e prima dimmi come si colloca rispetto a 7B.