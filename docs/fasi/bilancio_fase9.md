# Bilancio della Fase 9

> Scritto a chiusura di E4, il 2026-08-07, su richiesta dell'utente: un bilancio,
> non un elenco di blocchi chiusi. Ogni numero citato qui e' pubblicato in un
> report di blocco e verificato rieseguendo; le fonti sono indicate riga per riga.

---

## Il bilancio in un numero

**61,42 → 60,59.**

E' il MAE del modello d'asta prima e dopo tutto cio' che la Fase 9 ha prodotto,
sulle stesse quattro transizioni e sulle stesse 2.678 righe. La fase ha comprato
**0,83 punti**, cioe' l'**1,4%** dell'errore.

Il resto — cinque blocchi, quattro code, **185 test** — e' **esclusione**: aver
dimostrato, con potenza dichiarata, che sette strade non portano da nessuna parte.
Non e' un modo diplomatico di dire che e' andata male. Una mappa che segna sette
vicoli ciechi e una strada e' piu' utile di otto strade da provare, e il costo di
provarle era gia' stato pagato — la differenza e' che ora e' pagato **una volta**.

---

## 1. Cosa ha funzionato — una cosa sola, e si sa perche'

**La quotazione iniziale QI, in percentile dentro il ruolo, come predittore di
presenze** (Blocco E2, sezione (b); `reports/fase9_e2_presenze.md`).

| | |
|---|---:|
| quota del divario delle presenze chiusa | **+1,49%** |
| t appaiato | **+2,91** |
| MDE a potenza 80% | 1,25% |
| soglia di Bonferroni su 4 varianti | \|t\| > 2,50 |
| MAE presenze | 9,906 → **9,744** |
| correlazione con le presenze vere | 0,461 → **0,481** |

Passa il proprio MDE e passa la molteplicita'. E migliora **il passaggio giusto**:
non solo il MAE finale sui punti, ma le presenze, che sono la grandezza che si
voleva prevedere — un predittore che migliorasse i punti senza migliorare le
presenze avrebbe migliorato per caso.

**Perche' funziona, ed e' strutturale.** Tutte le feature della Fase 9 vengono da
`t-1`, perche' i dati evento di `t` non esistono ancora. QI viene da **`t`**: e' un
prezzo della stagione bersaglio, pubblicato prima che cominci. E' l'unica cosa nel
repository che guardi `t` senza guardarne l'esito. La ridondanza e' misurata: meta'
di QI e' gia' nel set (R² 0,47 sulle quote di esposizione), quindi il guadagno
viene dall'**altra meta'** — mercato estivo e gerarchia dichiarata dai club, che e'
esattamente cio' che nessun dato evento puo' contenere.

**Tre limiti, che vanno letti insieme al numero.**

1. **E' un complemento, non un sostituto.** QI da solo fa **−0,18%**, cioe' peggio
   del modello d'asta. Chi ne ricavasse «all'asta guarda solo il prezzo»
   leggerebbe il contrario di quel che c'e' scritto.
2. **Dipende dalla forma, ed e' la forma dichiarata prima.** Il prezzo grezzo non
   passa (t = 0,77, sotto il proprio MDE); il percentile di ruolo si'. E il gate di
   E1 le separa da solo: il grezzo deriva del 10,9%, il percentile dell'1,4%.
3. **E' positivo e piccolo, e le due parole vanno tenute insieme.** L'1,5% di un
   divario che gli infortuni chiudono per la maggior parte non e' una soluzione
   delle presenze.

> **QI sui bonus e sul voto e' un'altra domanda, ed e' rimasta aperta come nota.**
> In E4, QI da solo chiude il 10,5% del divario dei bonus con t = 2,31: passa il
> 5% a due code e **non** passa Bonferroni su sei varianti (serve \|t\| > 2,64).
> Resta **suggestivo, non promosso a feature attiva** — stessa disciplina applicata
> a QI in (b), dove il numero invece passava.

---

## 2. Cosa e' stato escluso, e con che forza

Un'esclusione vale quanto la sua potenza. Le sette non sono equivalenti: due sono
strette, tre escludono solo effetti grandi, due sono qualitative.

| strada | esito | MDE | forza dell'esclusione |
|---|---:|---:|---|
| il cartellino come **predittore** d'impiego | ±0,03% | **0,04-0,12%** | **la piu' stretta della fase** |
| **squalifiche** sottratte alle presenze | **−1,9%** | — | meccanismo misurato, non solo segno |
| feature d'impiego da **dati evento** | +0,20% | 1,53% | esclude effetti grandi |
| **numero di maglia** | ~0 | 1,53% | **la feature utile non e' costruibile** |
| feature evento su **bonus e voto** (E4) | −1,6% / −6,0% | 11-14% | esclude effetti grandi su un divario piccolo |
| **autogol**, effetto individuale | 0,000 | — | fuori campione, contro il tasso di ruolo |
| **collegare la difesa** ai portieri (E3) | 0,465 → 0,435 | — | e la **spiegazione** e' esclusa a sua volta |

**Le due esclusioni forti**, cioe' quelle in cui il test vedrebbe anche un effetto
piccolo:

- **il cartellino come predittore d'impiego** (coda di E2). Il confronto e'
  appaiato contro un modello che differisce per **una colonna**, quindi la varianza
  della differenza e' minuscola e l'MDE scende a 0,04-0,12% — il test vedrebbe
  effetti **dieci volte piu' piccoli** di quelli che E2.4 poteva vedere, e non ne
  trova nessuno. E il nulla non e' ridondanza: il **tasso** di cartellini ha R²
  0,021 sul set, cioe' porta informazione che il set non ha e **non serve lo
  stesso**. E' la distinzione che rende una confutazione tale invece che ambigua.
- **le squalifiche**, dove l'esclusione non e' un `t` ma un **meccanismo**: chi
  prende cartellini e' chi gioca, e su quei giocatori il modello **gia'** sottostima
  le presenze di 6,0 (21,2 attese contro 27,2 osservate). Togliere altre giornate a
  una previsione gia' troppo bassa allontana. Con la causa misurata, il segno non e'
  un caso da ritoccare.

**Le tre che escludono solo effetti grandi** — dati evento sull'impiego, maglia,
dati evento sui bonus — vanno lette per quello che sono: `t` piccoli con MDE
grandi. Non dimostrano che l'effetto sia zero; dimostrano che non e' grande. Vale
la pena dirlo perche' e' l'errore che la Fase 6D ha insegnato a non fare.

**Due casi in cui l'esclusione e' qualitativa e vale di piu' di un numero:**

- **il numero di maglia**: la versione interessante — il numero d'agosto, noto
  anche per chi al nuovo club non ha storia, che era *tutto* l'argomento — **non e'
  costruibile con i dati in casa**, perche' la nostra unica fonte del numero e' la
  distinta di una partita e chi non viene mai convocato non ha nessuna distinta.
  Fra i quotati con una distinta in `t+1` le presenze medie sono 19,1-19,3; fra
  quelli senza, 0,0-0,3. **La sola disponibilita' della feature e' la risposta.**
- **il FVM come ingresso**: squalificato **da una misura, non da cautela**. Il FVM
  della pagina archiviata sta sull'orologio di QA, cioe' si muove durante la
  stagione: `FVM − QI` predice l'esito di quella stagione quanto `QA − QI` e in tre
  casi su quattro di piu'. Resta usabile come descrizione, mai come concorrente
  fuori campione. Ne discende che due numeri gia' pubblicati erano contaminati e
  sono stati corretti e barrati, non cancellati.

---

## 3. Quattro strumenti che funzionano, e che restano

Non tutto cio' che non ha risolto il problema e' inutile. E3 ha consegnato quattro
cose valide **indipendentemente** dall'esito negativo della verifica che le aveva
motivate, e restano disponibili:

| strumento | come si giustifica |
|---|---|
| modello di squadra sui **gol**, rivalidato per conto suo | batte il baseline migliore per **t = 5,52** (sui tiri in porta valeva 1,86) |
| **porta inviolata** come probabilita' | pendenza di calibrazione **1,044 ± 0,083**, Brier 0,1899 contro 0,1992 |
| **voto della linea** condizionato alla forza difensiva | −0,243 di voto dal p10 al p90, **t = −22,5** |
| **correlazione dentro la linea** | 0,261, genuina co-variazione di giornata (0,263 → 0,261 al netto del giocatore) |

Il piu' istruttivo e' il quarto: l'effetto della correlazione sul bonus atteso
**cambia segno** intorno a 6,7 di voto medio di linea, perche' le fasce sono
convesse crescenti e la varianza aiuta finche' non si e' dentro l'ultima. Cercarlo
solo sotto le soglie avrebbe dato la conclusione opposta.

---

## 4. Il tetto dichiarato adesso

**Le presenze restano il problema, e la correzione di E4 lo rafforza invece di
indebolirlo.**

| componente | divario oracolo | quota |
|---|---:|---:|
| **presenze** | **55,86** | **91%** |
| voto base | 1,24 | 2% |
| bonus | 1,44 | 2% |

I due divari di destra erano pubblicati come **8,9 punti** e non lo erano: quel
numero metteva insieme un guadagno vero (2,51) e un cambio di campione (~6,4), e la
grandezza che chiamava «bonus» era in realta' l'intero tasso per presenza. La
correzione **non cambia la direzione, la rende piu' netta**: cio' che resta fuori
dalle presenze vale il 4% dell'errore, non il 14,5%.

**Dentro le presenze, il limite ha un nome e non e' misurabile qui.**

Gli infortuni non sono in **nessuna** delle due fonti acquisite — ne' WhoScored, ne'
la fonte dei voti. Sono la componente piu' grossa dell'assenza. **Quanto del 55,86
sia attribuibile a loro non e' stato stimato, e con i dati in casa non e'
stimabile**: non c'e' una colonna che distingua «infortunato» da «fuori scelta
tecnica» da «ceduto». Va detto cosi' invece di mettere un numero plausibile accanto
a una cosa che nessuno ha misurato.

**Cio' che la fase ha provato dentro le presenze, e che quindi non va rifatto:**

- i dati evento (esposizione, titolarita', ingressi, tocchi) — esclusi;
- lo strato distinta (maglia, capitano, ruolo come serie) — escluso, e la versione
  utile non e' costruibile;
- le squalifiche, sia come sottrazione sia come predittore invertito — escluse, la
  seconda con l'MDE piu' stretto della fase;
- la quotazione — **l'unica che da' qualcosa, e da' l'1,5%**.

> **Ne segue il vero risultato della fase: il 98,5% del divario delle presenze
> resta non attaccato, e le fonti gia' in casa sono state esaurite.** Non e' un
> fallimento ed e' importante che sia scritto in positivo: significa che il
> prossimo guadagno su quel divario **non puo' venire da un modello migliore sui
> dati che abbiamo**, ma solo da dati che non abbiamo.

---

## 5. Che cosa la fase ha costruito, oltre ai risultati

Il bilancio sarebbe incompleto senza la parte strutturale, che non e' un risultato
ma e' la ragione per cui i risultati sono stati ottenibili:

- **`player_match` su cinque stagioni** (87.449 righe) invece di una: senza, non
  esiste walk-forward e un predittore non e' testabile;
- **l'aggancio giocatori esteso**, con 1.544 controlli incrociati indipendenti e
  zero discordanze, e il residuo dichiarato invece che risolto d'ufficio;
- **la regola delle feature** (E1) — `x_rel = x/m_s − 1` — con tre guardie che
  sono test e non buone intenzioni, e la scoperta che **standardizzare non e'
  gratis**: peggiora la deriva su 8 candidate su 19, con tre meccanismi misurati;
- **il derivato dei piazzati** dai qualifier, e con esso due trappole della fonte
  che nessun gate avrebbe fermato (`passFreekick`, il perimetro di `Penalty`);
- **la verifica sui cinque fit di xG**, rimandata due volte e chiusa: forma
  stabile, livello che si muove del 15,8%.

---

## 6. Che cosa questo bilancio implica per la scelta successiva

Non e' una raccomandazione — la scelta e' dell'utente — ma un bilancio che non
dicesse dove i suoi numeri puntano sarebbe reticente.

- **Le tre domande appaiate** (rating WhoScored, numero di maglia d'agosto, FVM
  pre-stagione) sono l'unica direzione che **aggiunga una fonte** invece di
  spremere ancora le stesse, e due delle tre toccano le **presenze** e il
  concorrente, cioe' il 91%. Sono la stessa domanda per *tipo* — un valore noto
  prima della stagione, che la fonte pubblica e che noi non abbiamo — **ma non
  per costo ne' per tempi**, e la differenza e' stata accertata il 2026-08-07
  (vedi sotto). Restano una sola voce nelle decisioni; non sono un solo prezzo.

### 6-bis. Il costo di verificare la famiglia, accertato senza toccare la rete

Richiesto dall'utente prima di scegliere il ramo. **Nessuna richiesta di rete e'
stata fatta**: quello che segue e' cio' che si e' potuto accertare dal codice e
dal grezzo gia' su disco, piu' la stima di cio' che resterebbe da fare.

| domanda | costo della **verifica** | acquisibile |
|---|---|---|
| rating WhoScored | **una richiesta** su una partita | **all'indietro** |
| FVM pre-stagione | **una richiesta**, e la finestra e' adesso | **solo in avanti** |
| numero di maglia d'agosto | prima va **individuata la pagina**: la premessa era falsa | **solo in avanti** |

- **Rating WhoScored.** `getMatchData` costruisce l'intero `match_data`, cioe'
  tutto `matchCentreData`, e `createEventsDF` legge **solo** `data['events']`:
  quello che manca era gia' stato scaricato e buttato via **nella
  trasformazione**, non e' un problema di accesso ne' di autorizzazione (stesso
  dominio, stessa pagina che lo scraper gia' visita). Che i ratings ci siano **non
  e' affermabile dal repository** — nessuna pagina grezza e' conservata — ed e'
  esattamente cio' che una singola pagina accerterebbe. Se la verifica fosse
  positiva, la raccolta costa 380 pagine Selenium per una stagione di prova e
  1.889 per tutte e cinque, ed e' li' che sta il costo vero: `main.py` e' gia'
  dichiarato il collo di bottiglia.
- **FVM pre-stagione.** Tutti e cinque i listoni sono stati scaricati **nell'agosto
  2026**, in un'unica esecuzione: per le quattro stagioni passate quel FVM e'
  contaminato e recuperarne uno pulito vorrebbe un archivio esterno, con esito non
  garantito. **Per la 2026-27 non serve nessun archivio**: basta archiviare la
  pagina *prima* che la stagione cominci. Il 2026-08-03 il listone 2026-27 non
  esisteva ("Dati non disponibili"); `scrape_quote` distingue gia' quel caso da un
  cambio di markup, quindi verificarlo costa una richiesta. **E' l'unica delle tre
  con una scadenza.**
- **Numero di maglia d'agosto.** La premessa pubblicata — «sta nei listoni» — **e'
  stata falsificata**: il listone 2025-26 non ha nessuna colonna di maglia (le
  sole esposte sono `sq`, `c_qi`, `c_qa`, `c_fvm`, `m_*`), e nemmeno le pagine dei
  voti. La fonte sarebbe una **terza** pagina, le rose di club, che non e' stata
  individuata; va anche verificato che il numero sia in HTML statico e non reso da
  JS, che e' la differenza fra `requests` e Selenium. E' la piu' cara delle tre a
  verificare, non la piu' economica come la riga corretta lasciava credere.

> **L'asimmetria che conta, e che la parola "appaiate" nasconde**: il rating e'
> acquisibile **all'indietro**, perche' le pagine partita restano disponibili, e
> quindi entrerebbe **subito nelle quattro transizioni** del walk-forward. FVM
> pulito e numero d'agosto sono acquisibili **solo in avanti**: darebbero **una**
> transizione fra due anni, non quattro adesso. Sul pezzo che conta — le presenze,
> il 91% — le due che lo toccano sono proprio quelle che non danno storia, e il
> rating agisce sul voto, cioe' sul 4%. **Nessuna delle tre e' insieme economica,
> retroattiva e puntata sul 91%**, e chi sceglie deve sapere che sta scegliendo
> quale di quelle tre proprieta' rinunciare.
- **G2 (altri campionati)** sblocca tre domande ferme (potenza del test dei
  predittori, traduzione per i nuovi arrivi, massa per `rho`), ma **non tocca le
  presenze in Serie A**: darebbe piu' righe dello stesso tipo di dato che la Fase 9
  ha appena escluso.
- **G3 (scouting)** ha la **condizione rotta**: era «ha senso solo dopo che il
  modello batte il FVM», e il FVM e' stato squalificato. Contro il concorrente
  leale — QI — il verdetto e' **misto** (Spearman 0,606 contro 0,452, precisione
  sui primi N 0,162 contro 0,177). La condizione va riscritta prima di poterla
  dichiarare soddisfatta.
- **7B** e' l'altro ramo e riguarda un'altra grandezza: il livello della proiezione
  SoT di squadra, dove la domanda singola piu' grande (`rho`, 19 tiri, il 21%
  dell'IC80%) e' anche la piu' economica.
- **Nessuno dei rami tocca gli infortuni**, che sono il tetto. Se un giorno si
  vuole attaccare il 91%, quella e' l'acquisizione, e oggi non e' in nessun piano.
