# Configurazione del progetto Fantacalcio

Documento di configurazione della lega. È l'input di tutta la Fase 8 e va letto
prima di qualsiasi blocco del modello fantacalcio.

**Regola d'uso per Claude Code:** ogni voce marcata `[DA DECIDERE]` è una
decisione dell'utente non ancora presa. Se un blocco ne incontra una, **si
ferma e la chiede**. Non si sceglie un valore plausibile, non si assume un
default, non si prosegue con un segnaposto.

---

## 0. Decisioni ancora aperte

| # | decisione | stato |
|---|---|---|
| 0.1 | soglie delle fasce del modificatore | **`[DECISO 2026-08-03]`** — tre fasce, 6.00 / 6.50 / 7.00, bonus +1 / +3 / +6 |
| 0.2 | numero di difensori che concorrono al modificatore | **`[DECISO 2026-08-03]`** — **dipende dal modulo schierato** |
| 0.3 | trattamento dell's.v. dentro la linea difensiva | **`[DECISO 2026-08-03]`** — **`escludi`**: esce dalla media e la linea si accorcia |
| 0.4 | comportamento sotto la soglia minima | **`[DECISO]`** — malus −1 |
| 0.5 | formato della lega | **`[DECISO 2026-08-03]`** — 8 squadre, budget 1000, rosa 3/8/8/6, i sette moduli di §3.2 |

Le decisioni prese vivono in **`sot/lega.py`**, separate dal codice come §6
richiede, con i loro invarianti verificati da `tests/test_modello_asta.py`.

**Tutte e cinque sono chiuse.** `sot/lega.gestione_sv()` continua a sollevare
`DecisioneMancante` se la costante torna a `None`: il meccanismo resta in piedi
per la prossima voce `[DA DECIDERE]`, e un test lo verifica.

`escludi` **non è neutro**, e va saputo leggendo i numeri: la media si ricalcola
su meno elementi, quindi diventa più variabile. Su una linea di tre da 7 e uno da
4, se il quarto prende voto la media è 6,25 (fascia +1); se non lo prende è 7,0
(fascia +6). **Cinque punti di differenza per giornata dal solo fatto che il
peggiore non è stato giudicato** — ed è il motivo per cui il modificatore si
simula per giornata e non si applica alle medie di stagione.

---

## 1. Regolamento della lega

### 1.1 Bonus e malus

| Evento | Ruolo | Bonus/Malus |
| --- | --- | ---: |
| Gol segnato | Portiere | +3 |
| Gol segnato | Difensore | +3 |
| Gol segnato | Centrocampista | +3 |
| Gol segnato | Attaccante | +3 |
| Assist | Tutti i ruoli | +1 |
| Ammonizione | Tutti i ruoli | −0,5 |
| Espulsione | Tutti i ruoli | −1 |
| Rigore segnato | Tutti i ruoli | +3 |
| Rigore sbagliato | Tutti i ruoli | −3 |
| Rigore parato | Portiere | +3 |
| Autogol | Tutti i ruoli | −2 |
| Gol subito | Portiere | −1 per ogni gol |
| Porta inviolata | Portiere | +1 |

Il fantavoto si calcola partendo dal voto assegnato dal provider e applicando i
bonus e i malus maturati nella partita.

### 1.2 Definizione di presenza

**Non tutte le partite giocate producono fantavoto.** Un giocatore che entra
tardi riceve **s.v.** (senza voto) e in quella giornata non contribuisce, né in
positivo né in negativo.

Ne segue una distinzione che il modello deve tenere separata, perché sono due
grandezze diverse:

| grandezza | definizione | dove sta |
| --- | --- | --- |
| **presenza fantacalcistica** | giornate in cui il giocatore riceve un voto numerico | `sot/presenza.py`, dal 2026-08-03 |
| minuti giocati | minuti effettivi in campo | `sot/minutes.py` |

Le due stanno sulla stessa riga solo per la 2025/26, l'unica stagione con
entrambe le fonti: `data/processed/ITA-serie-a/presenza_2025-2026.parquet`.

**Il bersaglio del modello A è la presenza fantacalcistica**, non i minuti. I
minuti restano un predittore della presenza, non un sostituto.

`[ACCERTATO — 2026-07-31, ricognizione della fonte]` **la soglia non esiste.**
Il regolamento della fonte lo dichiara alla lettera:

> "Non esiste, e mai esisterà, una regola che prevede che il voto venga dato a
> chi gioca un numero minimo di minuti."

Sulla scala Redazione l's.v. è **discrezionale**, deciso partita per partita da
chi assegna i voti. Non c'è nessun minutaggio da leggere, quindi la domanda
"quale soglia, e se costante" non ha una risposta numerica da accertare:
la risposta è che il criterio non è meccanico. Dettaglio in
`reports/phase7_fattibilita_fonte.md` §7.

**Ne segue una separazione che va tenuta ferma**, perché sono due cose diverse
e mescolarle sarebbe il vincolo 7 della Fase 7 violato alla prima riga:

| | cos'è | dove vive |
| --- | --- | --- |
| **s.v. osservato** | il dato pubblicato, stagioni 2021/22–2025/26 | si legge dalla fonte, **non si imputa mai** |
| **s.v. proiettato** | la regola dell'80' scelta dall'utente, per il 2026/27 | assunzione di modello, dichiarata |

`[DECISO dall'utente]` per la **proiezione** si assume s.v. a chi entra al
minuto **≥ 80'**, su `expandedMinute` come tutto il repository — quindi contro
una partita che dura 94-99', non 90 — e la regola è **la stessa su tutte e
cinque le stagioni**, senza varianti per stagione.

`[MISURATO — 2026-08-03]` esito in `reports/aggancio.md` §4, da
`scripts/run_aggancio.py`. Su **11.926 righe giocatore-partita** della 2025/26,
l'unica stagione in cui coesistono i minuti WhoScored e l's.v. osservato:

| | |
|---|---:|
| accordo della regola dell'80' | **97,84%** |
| accordo del baseline «nessun s.v.» | 90,45% |
| **falsi s.v.** (entra ≥ 80' e il voto lo prende) | **142** = 12,2% dei proiettati s.v. |
| **s.v. mancati** (entra prima e il voto non lo prende) | **116** = 1,08% dei proiettati a voto |

Tre cose che la misura ha aggiunto e che vanno lette insieme al numero:

1. **L'80' cade sul massimo della griglia 60-95**, e non perché sia stato scelto
   lì: era deciso prima. A 75' l'accordo scende a 95,3%, a 85' a 95,4%.
2. **La regola non può vedere il titolare che esce presto.** Tutti e 18 gli s.v.
   dei titolari sono usciti prima del 30'; nessun titolare oltre il 20' ha mai
   preso s.v. È un verso d'errore **strutturale**, non fra i due che questa
   sezione chiedeva.
3. **Sopra i 30 minuti giocati non esiste un solo s.v. su 8.552 righe.** La
   regola formale non c'è — la fonte lo dichiara — ma la pratica editoriale è
   quasi deterministica. Riscrivere la regola sui *minuti giocati* invece che
   sul minuto d'ingresso è stato provato e **non migliora**: 97,83% contro
   97,84%. Cambia il mix degli errori, non la loro quantità.

Nessuna correzione automatica: **la regola resta quella dell'utente**, ora con
il suo tasso d'errore accanto.

---

## 2. Modificatore di difesa

Il modificatore è **attivo**. Con un bonus che arriva a +6 — il valore di due
gol — i difensori sono centrali nella valutazione, e `difesa_j` del modello di
squadra è una componente fondamentale della proiezione, non un accessorio.

Il modificatore si calcola sulla media del **voto base** del portiere e dei
migliori difensori schierati, **esclusi bonus e malus**. Il modello del voto
base (blocco 8A) è quindi un ingresso diretto del modificatore, non solo un
addendo del fantavoto.

### 2.1 Le fasce

**Le fasce dichiarate finora hanno tre difetti che le rendono non
implementabili.** Vanno risolti prima di scrivere codice:

1. **Sovrapposizione**: 6.75 appartiene sia alla fascia 6.50–6.75 sia alla
   6.75–6.99.
2. **Buco**: la quarta fascia finisce a 6.99 e la quinta parte da *maggiore di*
   7.00. Una media esattamente 7.00 non ricade in nessuna fascia.
3. **Fasce duplicate**: le cinque fasce dichiarate danno bonus +1, +1, +3, +3,
   +6, cioè sono **tre fasce effettive**. O è voluto, o due valori sono errati.

`[DECISO 0.1 — 2026-08-03]` tre fasce, soglie **6.00 / 6.50 / 7.00**, bonus
**+1 / +3 / +6**. `[DECISO 0.4]` sotto 6.00 il malus è **−1**.

Implementate in `sot/lega.FASCE` con intervalli semiaperti, e un test verifica
su tutta la retta reale che ogni media cada in **una e una sola** fascia.

Forma da usare, con **intervalli semiaperti** `[min, max)`: nessuna
sovrapposizione possibile, nessun buco possibile.

```yaml
modificatore_difesa:
  attivo: true

  # [DECISO 0.2 — 2026-08-03] concorrono TUTTI i difensori schierati, quindi
  # n dipende dal modulo: 3 nel 3-5-2, 4 nel 4-4-2, 5 nel 5-3-2.
  n_difensori: dal_modulo

  # [DECISO 0.3 — 2026-08-03] difensore senza voto dentro la linea
  gestione_sv: escludi           # "escludi" | "sostituisci_con_panchina" | "annulla_modificatore"

  # [DECISO 0.4] media difensiva sotto la soglia minima
  sotto_soglia_minima: -1   # bonus 0, oppure un malus

  # [DECISO 0.1] soglie e bonus — intervalli [min, max)
  fasce:
    - {min: 6.00, max: 6.50, bonus: 1}
    - {min: 6.50, max: 7.00, bonus: 3}
    - {min: 7.00, max: null, bonus: 6}
```

Un test deve verificare che le fasce **coprano l'intera retta reale senza
sovrapposizioni**: è un invariante, non un controllo di stile.

### 2.2 Il modificatore non è una proprietà del giocatore

**È il punto che cambia la forma del prodotto e va letto prima di progettare
l'output.**

Il modificatore dipende dalla **media della linea difensiva schierata**, quindi
il contributo di un singolo difensore dipende da chi altro c'è in quella linea.
Poiché le fasce sono a scalini, lo stesso difensore da 6.30 di media vale molto
se completa una linea che senza di lui starebbe appena sotto una soglia, e vale
quasi nulla se la linea è già ben dentro una fascia o è irrecuperabile.

**Non è decomponibile per giocatore.** Un numero "contributo al modificatore"
assegnato al singolo, calcolato in isolamento, non significa niente.

Formulazione da adottare:

> Il contributo al modificatore si stima come **valore marginale atteso
> rispetto a una linea difensiva di riferimento dichiarata**, e va **simulato
> per giornata**, non calcolato dalle medie di stagione.

Due conseguenze operative:

- **La simulazione è obbligatoria, la media stagionale è sbagliata.** Le fasce
  sono una funzione non lineare della media difensiva: applicarle alla media di
  stagione non dà lo stesso risultato che mediare i bonus ottenuti giornata per
  giornata. È lo stesso fenomeno di convessità già misurato in Fase 6A
  (`reports/phase6_livello.md`, sezione 3), dove il Monte Carlo alzava il centro
  dell'1.55%: qui il segno può andare in entrambe le direzioni e va misurato.
- **L'ottimo d'asta è combinatorio, non un ordinamento.** Per i difensori la
  domanda non è "chi è il migliore" ma "quale insieme massimizza il valore dato
  il budget". Il modello produce l'ingresso di quel problema, non la sua
  soluzione. La soluzione, se serve, è un blocco a sé.

La linea di riferimento va dichiarata esplicitamente nella configurazione e
citata accanto a ogni numero di contributo marginale: **lo stesso giocatore ha
contributi diversi rispetto a linee diverse**, e un numero senza la sua linea di
riferimento è incompleto.

---

## 3. Prodotto da sviluppare

### 3.1 Scelta

**Prodotto selezionato: ASTA.**

Proiezione stagionale per circa 500 giocatori di Serie A. Motivazione:

- riusa direttamente il lavoro della Fase 3;
- non richiede, in prima versione, la previsione delle formazioni settimanali;
- ha una verifica naturale nel confronto con la quotazione ufficiale.

La formazione settimanale resta un prodotto separato, successivo.

### 3.2 Formato della lega

`[DECISO 0.5 — 2026-08-03]` i valori qui sotto sono quelli **veri** della lega,
non segnaposto. Vivono in `sot/lega.LEGA`.

```yaml
lega:
  n_squadre: 8
  budget_asta: 1000           # crediti a disposizione
  rosa:
    portieri: 3
    difensori: 8
    centrocampisti: 8
    attaccanti: 6
  formazione_schierata:
    modulo_o_moduli: 3-4-3, 3-5-2, 4-3-3, 4-4-2, 4-5-1, 5-3-2, 5-4-1     # es. 3-4-3, oppure elenco dei moduli ammessi
```

Il numero di difensori schierati vincola `modificatore_difesa.n_difensori`
(decisione 0.2): le due voci devono essere coerenti e un test lo verifica.

### 3.3 Output richiesti per giocatore

Per ciascun giocatore, con intervallo di incertezza e non solo il valore
puntuale:

- presenze fantacalcistiche previste (§1.2), non solo minuti;
- minuti previsti;
- voto base medio previsto;
- gol, assist previsti;
- ammonizioni ed espulsioni previste;
- rigori segnati e sbagliati previsti;
- autogol previsti;
- per i portieri: gol subiti, rigori parati, probabilità di porta inviolata;
- fantamedia prevista;
- punti fantacalcio totali attesi di stagione;
- **per i difensori e i portieri**: contributo marginale atteso al modificatore
  **rispetto alla linea di riferimento dichiarata** (§2.2), mai in isolamento;
- quotazione ufficiale;
- differenza fra valore stimato e quotazione.

**La fantamedia non è la grandezza su cui si compra.** Un giocatore con
fantamedia alta e poche presenze vale meno di uno con fantamedia media e
trentotto presenze. La grandezza da ordinare è il **totale stagionale atteso**;
la fantamedia si riporta accanto, come diagnostica.

---

## 4. Fonte dei voti e dei dati dei giocatori

Fonte candidata: `https://www.fantacalcio.it/voti-fantacalcio-serie-a`.

### 4.1 Verifica di fattibilità — precede tutto il resto

`[FATTA — 2026-07-31]` esito in `reports/phase7_fattibilita_fonte.md`,
decisioni conseguenti in §7.1. In sintesi: nessun export utilizzabile senza
credenziali (401), **nessun minuto nella fonte** in nessuna delle tre viste,
cinque stagioni accessibili, scala Redazione presente e con markup identico dal
2021/22. Il vincolo dei termini d'uso è stato rimosso dall'autorizzazione.

**Questa verifica viene prima di qualsiasi altra attività della Fase 7-8**, non
insieme all'implementazione. È l'unico elemento che può invalidare l'intero
piano dati: se la fonte non è utilizzabile, cambia la fonte e cambia tutto ciò
che sta a valle.

Da accertare, in quest'ordine:

1. **Esiste un export ufficiale** — file scaricabile, area riservata, API — che
   eviti del tutto lo scraping? È la domanda più importante: uno scraper è la
   strada più fragile e va scelta solo in assenza di alternative.
2. Termini d'uso, e cosa dicono esplicitamente sull'accesso automatizzato.
3. `robots.txt` per i percorsi che servirebbero.
4. Eventuali limiti di frequenza dichiarati.
5. Quali stagioni fra 2021/22 e 2025/26 sono effettivamente accessibili.
6. Presenza dei **minuti giocati**, non solo del voto.
7. Come è marcato l'**s.v.** e a quale soglia di minuti (§1.2).
8. Provider dei voti dichiarato, e se è lo stesso su tutte e cinque le stagioni.
9. Dove stanno le **quotazioni** del listone e in che formato.

**Se i termini d'uso vietano l'uso che serve qui, ci si ferma e lo si dichiara.**
Non si progettano aggiramenti: si elencano le fonti alternative.

### 4.2 Requisiti dell'acquisizione, se praticabile

`[SODDISFATTI — 2026-08-03]`, uno per uno e con il posto in cui vivono:

| requisito | dove |
| --- | --- |
| frequenza limitata e dichiarata | `scrape_voti.py --sleep`, default 3 s |
| `User-Agent` identificabile | `target.USER_AGENT`, e **non finge di essere un browser** |
| cache locale, nessuna pagina scaricata due volte | `scarica_giornata`, `is_file()` **prima** del `get` |
| manifest con URL, data di acquisizione e hash | `manifest.registra_fantacalcio`, **due** hash: del `.gz` e dell'HTML servito |
| grezzo separato dagli elaborati, mai trasformato | `data/raw/fantacalcio/...`, gzip senza perdita |
| cambiamenti di struttura segnalati, non assorbiti | `pagina.MarkupInatteso`, e la pagina non entra in `raw/` |
| ogni voto conserva stagione, giornata e provider | colonne della tabella; tutte e tre le scale affiancate |

---

## 5. Periodo storico

Prima stagione: **2021/2022**. Stagioni previste: 2021/22, 2022/23, 2023/24,
2024/25, 2025/26 — cinque complete.

La disponibilità non è l'unico criterio: va verificata la **stabilità del
criterio di voto**. Per ogni stagione:

- voto medio complessivo e per ruolo;
- deviazione standard dei voti;
- percentuale di giocatori senza voto;
- distribuzione dei voti;
- fantamedia media per ruolo;
- frequenza di bonus e malus;
- minuti medi giocati;
- provider dichiarato.

Una discontinuità netta fra due stagioni indica un cambio di criterio
editoriale. In quel caso **le stagioni precedenti non si usano senza
normalizzazione**, e la normalizzazione va documentata e misurata, non applicata
in silenzio.

Nota sul confronto fra stagioni: la 2021/22 è la prima stagione di ritorno del
pubblico dopo le restrizioni. Il vantaggio del campo di quel periodo non è
confrontabile con quello delle stagioni successive, e va dichiarato accanto a
ogni stima che lo attraversi.

---

## 6. Impatto sul modello

La configurazione della lega è **separata dal codice**: bonus, malus, fasce e
formato si modificano senza riscrivere né riaddestrare la pipeline.

### 6.1 La formula di valutazione

Il valore stagionale di un giocatore è:

```text
punti_stagione(giocatore) =
    Σ_giornate  P(riceve voto alla giornata g)
              × [ E(voto base | riceve voto)
                  + E(bonus − malus | riceve voto) ]

  + valore_marginale_modificatore(giocatore | linea di riferimento)
```

Tre note su come è scritta, perché la versione precedente aveva tre difetti:

- **I minuti non compaiono come fattore moltiplicativo.** Entrano come
  predittore di `P(riceve voto)`, che li incorpora già. Moltiplicare per i
  minuti *e* per una probabilità d'impiego conta due volte la stessa cosa.
- **Il voto base è nella formula.** È il termine dominante per difensori e
  centrocampisti, e nella versione precedente non c'era.
- **Il modificatore è fuori dalla sommatoria** e dipende dalla linea, non dal
  giocatore (§2.2).

### 6.2 Perché un difensore "noioso" può valere di più

Con il modificatore attivo, un difensore con pochi gol e assist ma con voto
medio alto, alta continuità di impiego, bassa frequenza di insufficienze e una
squadra difensivamente solida può valere all'asta più di un difensore offensivo
ma incostante. È la conseguenza diretta del fatto che il modificatore usa il
**voto base** e non il fantavoto: i bonus del difensore offensivo non entrano
nel modificatore, la sua insufficienza sì.

Questo è anche il punto in cui il modello di squadra si intreccia davvero:
`difesa_j` predice i gol subiti — porte inviolate e malus del portiere — mentre
`attacco_i` predice il monte gol da ripartire fra i giocatori. Sono lo stesso
modello letto nei due versi.

---

## 7. Decisioni prese

| Elemento | Decisione |
| --- | --- |
| Primo prodotto | Modello per l'asta |
| Numero indicativo di giocatori | Circa 500 |
| Grandezza da ordinare | Punti totali attesi di stagione, non la fantamedia |
| Modificatore di difesa | Attivo, su voto base, simulato per giornata |
| Contributo del modificatore | Marginale rispetto a una linea dichiarata |
| Fonte candidata | Fantacalcio.it — **subordinata alla verifica §4.1** |
| Metodo di acquisizione | Export ufficiale se esiste, scraping solo in alternativa |
| Prima stagione inclusa | 2021/2022 |
| Periodo iniziale | Cinque stagioni |
| Verifica principale | Confronto con la quotazione |

### 7.1 Decisioni della Fase 7 (2026-07-31)

Prese dall'utente dopo `reports/phase7_fattibilita_fonte.md`, che aveva chiuso
la verifica §4.1 con esito **non praticabile** per due motivi indipendenti.

| # | decisione | effetto |
| --- | --- | --- |
| 1 | **autorizzazione concessa** da Fantacalcio S.r.l., estesa esplicitamente allo scraping dei voti | **rimuove il primo motivo**: l'art. 3.3(a) è soddisfatto per la via che lo stesso articolo prevede |
| 2 | i **minuti** vengono da **WhoScored**, non dalla fonte | **aggira il secondo motivo**, che resta un fatto: i minuti nella fonte non ci sono |
| 3 | perimetro **2021/22 → 2025/26**, cinque stagioni | WhoScored va esteso a **tutte e cinque**, non a quattro — vedi sotto |
| 4 | **s.v. proiettato all'80'**, costante sulle stagioni | assunzione di modello, §1.2, da misurare sulla 2025/26 |
| 5 | scala **Redazione** | fissa il bersaglio; le altre due arrivano nella stessa riga e si scartano in lettura |
| 6 | export ufficiale: **verificato irraggiungibile** senza credenziali (401) | il metodo di acquisizione resta da chiudere: export con login, o vista HTML |

**Tre conseguenze che non erano nella richiesta e che valgono per i blocchi
successivi:**

1. **WhoScored serve su cinque stagioni, non su quattro.** La regola dell'80'
   ha bisogno del **minuto di ingresso**, e la fonte dei voti marca il subentro
   con un'icona binaria senza minuto (verificato nel markup). Quindi anche la
   2025/26, che i voti coprono, richiede i minuti da WhoScored.
2. **La 2025/26 è l'unica stagione con entrambe le fonti**, ed è perciò
   l'**unica stagione di misura**: è lì che la regola dell'80' si confronta con
   l's.v. osservato, e lì soltanto.
3. ~~**I termini d'uso di WhoScored sono una verifica a parte, mai fatta.**~~
   `[RISOLTO — 2026-07-31]` **autorizzazione WhoScored dichiarata dall'utente**,
   distinta da quella di Fantacalcio.it e non derivata da essa. È il presupposto
   su cui è partita l'acquisizione delle cinque stagioni; come per
   l'autorizzazione Fantacalcio (decisione 1), il repository ne registra la
   dichiarazione, non ne conserva il documento.

   **Il dominio a cui lo scraper si rivolge è `1xbet.whoscored.com`**, un mirror
   di affiliazione fissato in `acquisition/whoscored/main.py:60` e ereditato dal
   fork — non `www.whoscored.com`. È un fatto rilevato eseguendo lo scraper e
   riportato qui perché un'autorizzazione riguarda un soggetto: se quella
   ottenuta copre WhoScored ma non il mirror, il dominio va cambiato.

~~`[NON DECISO]` da quale delle due vie si acquisisce~~
`[DECISO dall'utente — 2026-08-03]` **vista HTML pubblica.** L'export Excel
resta inutilizzabile senza credenziali (401) e le sue colonne restano
`[non verificato]`: nessun download manuale da loggato e' stato fatto, e la
domanda "l'Excel contiene i minuti?" resta aperta — ma non e' piu' bloccante,
perche' i minuti vengono da WhoScored in ogni scenario (decisione 2).

Esito in `reports/voti_fantacalcio.md`. **190 pagine, cinque stagioni, tutte e
tre le scale**; il codice sta in `acquisition/fantacalcio/`.

Tre fatti nuovi sulla fonte, emersi acquisendo e non leggendo:

1. **Il `FV` della fonte NON e' il fantavoto di questa lega.** Il barema della
   fonte e' stato ricavato per differenza e verificato riga per riga: torna
   esatto **senza** il +1 di porta inviolata di §1.1. Quindi la porta inviolata
   la fonte non la applica, il fantavoto di lega va **ricalcolato dai bonus**, e
   la porta inviolata va **derivata** (`ruolo == "p"` e `gol_subiti == 0`), mai
   letta. Leggere `FV` e chiamarlo fantavoto costerebbe un punto per ogni
   clean sheet.
2. **I cartellini non sono una colonna.** Ammonizione ed espulsione non stanno
   fra le otto voci di bonus della fonte: stanno come **classe CSS sullo span
   del voto**. Chi legge solo i bonus li perde in silenzio, e valgono −0,5 e −1.
3. **Il gol su rigore non e' anche in "gol segnati"**: sta solo in "rigori
   segnati" e vale +3 una volta sola. Sommare le due colonne, come la lettura
   ingenua di §1.1 suggerirebbe, conterebbe due volte lo stesso gol.

Decisioni ancora aperte: vedi sezione 0. **Le quotazioni del listone non sono
state acquisite** (pagina diversa, `/quotazioni-fantacalcio`): la D2 del
Blocco 0 resta aperta ed e' la verifica principale del progetto.
