# Fase 7 — Ricognizione di fattibilita' sulla fonte `fantacalcio.it`

## Esito in una riga

**NON PRATICABILE** allo stato attuale, per **due motivi indipendenti, ciascuno
dei quali basta da solo**: (1) l'art. 3.3(a) dei Termini di Utilizzo vieta
**esplicitamente e nominatamente** lo scraping senza autorizzazione scritta, e
l'art. 8.3 limita l'uso consentito a "personale e non commerciale"; (2) **i
minuti giocati non esistono su `fantacalcio.it`** — in nessuna delle tre viste
verificate — e i minuti sono un requisito dichiarato della Fase 8.

Il secondo motivo e' quello che conta di piu' per il seguito del lavoro:
**anche se domani arrivasse un'autorizzazione scritta, la fonte non
conterrebbe comunque il dato dei minuti.** Un'eventuale richiesta di
autorizzazione va quindi posta sapendo che risolve meta' del problema.

> **Aggiornamento del 2026-07-31, dopo la stesura.** L'utente dichiara di
> **avere ottenuto l'autorizzazione**, estesa esplicitamente allo scraping dei
> voti: **il motivo (1) cade**. Il motivo (2) resta, ed e' un fatto sulla
> fonte, non un permesso: i minuti verranno da WhoScored. L'esito aggiornato e
> le sue conseguenze stanno in `docs/regole_fantacalcio.md` §7.1; la verifica
> diretta dell'export e' nell'addendum in fondo a questo file.
> Questo paragrafo, che prevedeva il caso, e' quello che si e' verificato.

---

## Metodo e data della verifica

Ricognizione **documentale**, condotta il **2026-07-31**. Nessuno scraper e'
stato scritto, nessun dato e' stato scaricato, nessuna dipendenza aggiunta.
Le pagine sono state lette una per una in sola lettura.

Pagine consultate direttamente:

| URL | cosa si e' accertato |
|---|---|
| `https://www.fantacalcio.it/robots.txt` | contenuto integrale |
| `https://www.fantacalcio.it/termini-e-condizioni` | artt. 3 e 8, letti due volte |
| `https://www.fantacalcio.it/voti-fantacalcio-serie-a` | colonne, selettori, download |
| `https://www.fantacalcio.it/voti-fantacalcio-serie-a/2021-22/1` | accessibilita' stagione 2021/22 |
| `https://www.fantacalcio.it/statistiche-serie-a` | colonne delle statistiche stagionali |
| `https://www.fantacalcio.it/quotazioni-fantacalcio` | listone, Classic/Mantra, download |
| `https://www.fantacalcio.it/regolamenti/fantacalcio` | criterio s.v., scale di voto, bonus/malus |
| pagina profilo giocatore (`/serie-a/squadre/.../<id>`) | statistiche per giornata |
| `https://www.fanta.soccer/it/archiviovoti/` | fonte alternativa |

> **Avvertenza sulla data.** I termini di un sito cambiano. Il documento letto
> riporta **"Giugno 2026"** come aggiornamento: e' recente, ma una verifica ha
> sempre una data e questa e' il 2026-07-31. Qualunque decisione presa fra sei
> mesi va rifatta partendo da qui, non da questo file.

**Marcatori usati in tutto il documento:**

- `[verificato]` — letto direttamente sulla pagina citata, con URL.
- `[riportato da terzi]` — affermato da una fonte diversa da `fantacalcio.it`,
  non confermato sulla fonte primaria.
- `[inferito]` — deduzione mia da fatti verificati; non e' scritto da nessuna parte.
- `[non verificato]` — non sono riuscito ad accertarlo, e sotto e' spiegato perche'.

---

## 1. Esiste un export ufficiale? (la domanda piu' importante)

**Si', esistono pulsanti di download ufficiali — ma non sono un'API pubblica e
non sono documentati.** `[verificato]`

Su tre pagine distinte e' presente un pulsante con etichetta letterale
**"Scarica"** che punta a endpoint interni della forma `/api/v1/Excel/...`:

| pagina | endpoint del pulsante "Scarica" |
|---|---|
| voti, stagione 2025/26, giornata 38 | `/api/v1/Excel/votes/20/38` |
| voti, stagione 2021/22, giornata 1 | `/api/v1/Excel/votes/16/1` |
| statistiche stagionali | `/api/v1/Excel/stats/20/1` |
| quotazioni / listone | `/api/v1/Excel/prices/20/1` |

Osservazioni:

- Lo schema e' `/<risorsa>/<idStagione>/<giornata>`, con **idStagione 16 =
  2021/22 e 20 = 2025/26** `[verificato]`, da cui 17 = 2022/23, 18 = 2023/24,
  19 = 2024/25 `[inferito]`.
  > **Corretto dall'addendum in fondo**: lo schema vale solo per `votes`; i tre
  > idStagione intermedi non sono piu' inferiti ma verificati.
- **Non e' un'API pubblica documentata.** La ricerca non ha trovato alcuna
  documentazione ufficiale per sviluppatori ne' termini d'uso specifici per
  questi endpoint `[verificato: assenza di risultati]`. Sono gli endpoint
  interni che alimentano un bottone dell'interfaccia.
- **Non ho scaricato nessuno di questi file**, per il vincolo 2 del mandato.
  Di conseguenza: se il download richieda registrazione, abbonamento o sia
  soggetto a limiti, e quali colonne contenga il file, e' `[non verificato]`.
  > **Aggiornato dall'addendum in fondo**: su autorizzazione dell'utente gli
  > endpoint sono stati interrogati. Rispondono **401 Unauthorized** a corpo
  > vuoto: la registrazione serve, il contenuto resta `[non verificato]`.

**Il punto giuridico che conta.** L'esistenza di un pulsante "Scarica" rende
lecito **il click manuale di un utente**, per uso personale, entro l'art. 8.3.
Non rende lecito il **recupero automatizzato e sistematico** dei 5 x 38 = 190
file voti piu' i listoni: quello ricade in pieno nell'art. 3.3(a), che vieta
"programmi software o altri meccanismi automatici **o manuali** per copiare o
accedere alle pagine della Piattaforma **o al loro Contenuto**". La formula
copre esplicitamente anche il meccanismo manuale e il Contenuto, non solo le
pagine. `[verificato — citazione integrale al punto 2]`

> Non propongo alcun modo di aggirare questo, come da vincolo 3 del mandato.
> La via lecita, se la si vuole percorrere, e' **una sola**: chiedere
> l'autorizzazione scritta ed espressa prevista dallo stesso art. 3.3(a).
> Il titolare e' **Fantacalcio S.r.l., P.IVA 10938501219, Via G. Porzio,
> Centro Direzionale Is. F4, 80143 Napoli** `[verificato]`.

---

## 2. Termini d'uso — cosa dicono esplicitamente

Fonte: `https://www.fantacalcio.it/termini-e-condizioni`, consultato 2026-07-31,
aggiornamento dichiarato **Giugno 2026**. `[verificato]`

### Articolo 3 — Navigazione

**3.1** — citazione:

> "La Navigazione nell'Ecosistema è consentita liberamente a chiunque."

**3.2** — l'Utente deve rispettare le normative vigenti e i diritti di
Fantacalcio e dei terzi; la Societa' "si riserva di perseguire qualsiasi uso
non autorizzato".

**3.3** — "L'Utente dovrà astenersi da", lettere rilevanti, citate testualmente:

> **(a)** "usare programmi software o altri meccanismi automatici o manuali per
> copiare o accedere alle pagine della Piattaforma o al loro Contenuto (ivi
> compresi sistemi atti a effettuare il c.d. scraping) senza una autorizzazione
> scritta ed espressa"

> **(b)** "copiare, riprodurre, alterare, modificare, elaborare, vendere o
> comunque divulgare i Contenuti senza espressa autorizzazione scritta di
> Fantacalcio"

> **(c)** "compiere azioni che possano causare un irragionevole sovraccarico di
> attività delle infrastrutture tecnologiche della Piattaforma"

> **(d)** "usare meccanismi, software o procedimenti che possano interferire con
> il corretto funzionamento della Piattaforma"

> **(e)** "aggirare gli strumenti approntati per l'esclusione dei sistemi
> automatici dei motori di ricerca (robot)"

### Articolo 8 — Proprieta' Intellettuale

**8.2** — citazione:

> "La pubblicazione, la distribuzione, la visualizzazione, la modifica, la
> creazione di lavori derivati e la manipolazione dei Contenuti o della
> Proprietà Intellettuale, in qualsiasi forma siano esse compiute, sono
> rigorosamente vietate senza una autorizzazione scritta"

**8.3** — l'Utente puo' visualizzare e conservare **copia personale e non
commerciale** dei Contenuti, a condizione che indichi i diritti d'autore e
**impedisca a programmi installati di recuperare i Contenuti senza
autorizzazione**.

**8.4** — i testi e le immagini di terzi in licenza restano "di esclusiva
proprietà dei rispettivi titolari".

### Lettura

- Lo scraping e' vietato **per nome**, non per interpretazione estensiva. Non
  c'e' margine di ambiguita' su cui appoggiarsi.
- L'art. 8.3 non salva il progetto: la Fase 8 e' un modello per l'asta, e la
  "creazione di lavori derivati" e' vietata dall'8.2 a prescindere dal fine.
  Se poi l'uso fosse commerciale, cade anche l'eccezione dell'8.3.
- L'art. 8.3 contiene una clausola **specificamente diretta al caso nostro**:
  l'obbligo di impedire ai programmi installati di recuperare i Contenuti.

> **Nota di accuratezza.** Ho letto l'articolo 3 due volte con prompt diversi.
> La prima lettura ha numerato la clausola sullo scraping come **3.1.a**, la
> seconda — piu' completa, che ha restituito l'articolo per intero — come
> **3.3(a)**. Il **testo della clausola e' identico nelle due letture**; e'
> incerta solo la numerazione. Uso 3.3(a) perche' viene dalla lettura integrale,
> ma chi citasse il passaggio in una comunicazione formale **verifichi il numero
> sulla pagina** `[parzialmente verificato]`.

---

## 3. `robots.txt`

`https://www.fantacalcio.it/robots.txt`, consultato 2026-07-31. Contenuto
integrale `[verificato]`:

```
User-agent: ia_archiver
Disallow: /

User-agent: *
Disallow: */preview/
Disallow: /test/
Disallow: /Test/
Disallow: /TEST/
Disallow: /ricerca
Disallow: /probabiliformazioniseriea
Disallow: /homesheet

Sitemap: https://www.fantacalcio.it/sitemap-index.xml
```

**Cosa copre, rispetto ai percorsi che servirebbero:**

| percorso necessario | stato in robots.txt |
|---|---|
| `/voti-fantacalcio-serie-a` | **non** disallowed |
| `/statistiche-serie-a` | **non** disallowed |
| `/quotazioni-fantacalcio` | **non** disallowed |
| `/api/v1/Excel/...` | **non** disallowed |
| `/regolamenti/...` | **non** disallowed |

- **Nessun `Crawl-delay`**, nessuna regola `Allow`, nessuna regola per
  user-agent specifici oltre a `ia_archiver` (Internet Archive), che e'
  escluso da tutto il sito. `[verificato]`
- Il solo `Disallow` tematicamente vicino e' `/probabiliformazioniseriea`, che
  **non serve** a questo progetto.

**Cosa NON copre, ed e' il punto.** `robots.txt` e' permissivo sui percorsi che
servirebbero, ma **non autorizza nulla**: e' un protocollo di cortesia per i
crawler, non una licenza. I Termini di Utilizzo sono l'atto vincolante e dicono
il contrario. **Il permesso in `robots.txt` non supera il divieto dell'art.
3.3(a)** `[inferito, ma e' la lettura standard del rapporto fra i due]`. Il
fatto che l'esclusione di `ia_archiver` esista dimostra semmai che il sito usa
`robots.txt` in modo selettivo e consapevole.

---

## 4. Limiti di frequenza dichiarati

- **Nessun `Crawl-delay` in `robots.txt`** `[verificato]`.
- **Nessun rate limit numerico dichiarato nei Termini** `[verificato]`. C'e'
  pero' l'art. 3.3(c), che vieta in termini qualitativi le azioni che causino
  "un irragionevole sovraccarico di attività delle infrastrutture tecnologiche
  della Piattaforma" — un limite senza soglia, valutato dal titolare.
- L'art. 3.3(e) vieta di aggirare gli strumenti anti-bot, il che **presuppone
  che tali strumenti esistano**, ma non ne dichiara la natura `[inferito]`.
- **Presenza e configurazione di WAF/Cloudflare: `[non verificato]`.** Non ho
  ispezionato header o comportamento sotto carico, perche' avrebbe significato
  sondare le difese di un sito che mi vieta l'accesso automatizzato. Tutte le
  pagine richieste sono state servite regolarmente in lettura singola: **nessun
  403, nessun blocco, nessun captcha** `[verificato]`.

---

## 5. Stagioni accessibili (2021/22 → 2025/26)

Il selettore di stagione presente sulle pagine voti, statistiche e quotazioni
elenca **dalla 2015/16 alla 2026/27** `[verificato]`. Le cinque stagioni
richieste sono quindi tutte comprese, con margine.

| stagione | voti | statistiche | quotazioni | accesso |
|---|---|---|---|---|
| 2021/22 | si' `[verificato]` | si' `[inferito dal selettore]` | si' `[inferito dal selettore]` | **pubblico, senza login** `[verificato]` |
| 2022/23 | si' `[inferito]` | si' `[inferito]` | si' `[inferito]` | `[non verificato]` |
| 2023/24 | si' `[inferito]` | si' `[inferito]` | si' `[inferito]` | `[non verificato]` |
| 2024/25 | si' `[inferito]` | si' `[inferito]` | si' `[inferito]` | `[non verificato]` |
| 2025/26 | si' `[verificato]` | si' `[verificato]` | si' `[verificato]` | **pubblico, senza login** `[verificato]` |

- Ho verificato **direttamente i due estremi**: la 2025/26 (giornata 38,
  22-24 maggio 2026, stagione conclusa come atteso al 2026-07-31) e la 2021/22
  (giornata 1, 21-23 agosto 2021). Entrambe **pubblicamente accessibili senza
  login**, con i voti visibili in pagina. Le tre stagioni intermedie sono
  `[inferito]` per continuita' del selettore: non le ho aperte una per una.
- La stagione **2026/27 e' gia' nel selettore** ma non e' iniziata: attendersi
  pagine vuote o parziali `[inferito]`.
- **Non ho trovato nessun paywall sui dati storici** `[verificato per le due
  stagioni aperte]`. Esistono "Login" e "Registrati" nel menu, e una sezione
  abbonamenti per funzioni premium `[riportato da terzi]`, ma i voti in se'
  erano visibili senza autenticazione.

---

## 6. Minuti giocati: presenti o solo il voto?

**Questo e' il risultato piu' importante della ricognizione dopo i termini.**

**I minuti giocati non compaiono in nessuna delle tre viste verificate.**
`[verificato]`

| vista | cosa mostra | minuti? |
|---|---|---|
| **voti per giornata** | nome, **V** (voto), **FV** (fantavoto), icone di subentro/sostituzione | **NO** |
| **statistiche stagionali** | Calciatore, Sq, **PV**, MV, FM, Gol, GS, Rig, RP, Ass, Amm, Esp | **NO** |
| **profilo giocatore** | Partite a voto, Gol, Assist, Amm, Esp, Autoreti, MV, FM, Quotazione, FVM; tabella "Per Giornata" con avversario, voto, fantavoto, "Entrato/Uscito", bonus/malus | **NO** |

Precisazioni:

- **`PV` significa "Partite a voto", non "partite giocate".** E' esattamente la
  **presenza fantacalcistica** che il progetto tiene distinta dai minuti. La
  fonte offre il numeratore sbagliato per il fine voluto.
- Il massimo che la fonte concede sul tempo di gioco e' **binario e ordinale**:
  le icone "subentrato / sostituito" nella vista voti e la colonna
  "Entrato/Uscito" nel profilo `[verificato]`. Dicono *se* un giocatore e'
  entrato o uscito, **non a che minuto**. Non e' un sostituto dei minuti e non
  permette di ricostruirli.
- **In nessuna vista i minuti ci sono e in un'altra no**: sono assenti ovunque.
  Non c'e' una vista privilegiata da preferire.
- `[non verificato]`: se i file Excel scaricabili contengano una colonna minuti
  assente dall'HTML. Non li ho aperti (vincolo 2). E' **l'unica via residua**
  per cui la conclusione di questo paragrafo potrebbe cambiare, ed e' la prima
  cosa da controllare se si procede.

> **Conseguenza per la Fase 8.** Il progetto dichiara che servono **entrambi**,
> presenza e minuti, e che i minuti sono il **predittore** della presenza, non
> un suo sostituto. Con questa fonte si ottiene solo la variabile da predire,
> mai il predittore. **I minuti vanno presi altrove in ogni scenario**, anche
> con autorizzazione concessa. Vedi "Fonti alternative".

---

## 7. Marcatura dell's.v. e soglia di minuti

Fonte primaria: `https://www.fantacalcio.it/regolamenti/fantacalcio`,
consultato 2026-07-31.

**La soglia non esiste, e il sito lo dichiara esplicitamente.** `[verificato]`
Citazione dal regolamento:

> "Non esiste, e mai esisterà, una regola che prevede che il voto venga dato a
> chi gioca un numero minimo di minuti"

Il regolamento aggiunge che la decisione spetta al redattore, in base al fatto
che il giocatore abbia inciso o meno sulla partita, e porta come esempi un
giocatore che prende voto dopo 5 minuti e uno che ne gioca 20 senza prenderlo.

**Questo e' molto piu' forte di "la soglia non e' dichiarata": e' una
dichiarazione positiva che una soglia non c'e'.** Vale per la scala
**Redazione Fantacalcio**.

- Per la scala **Voto Statistico (Alvin482)** e' `[riportato da terzi]` — e
  **solo da terzi** — che chi gioca almeno 10 minuti riceve un voto e sotto i
  10 minuti prende s.v. automaticamente. **Non l'ho trovato affermato sul
  regolamento di `fantacalcio.it`** e quindi non lo considero accertato. Se
  fosse vero sarebbe rilevante: renderebbe la scala statistica l'unica con un
  criterio s.v. **deterministico e riproducibile**.
- Per la scala **Voto Italia**: nessun criterio s.v. dichiarato `[non
  verificato]`.

> **Conseguenza per il modello.** Sulla scala Redazione, l's.v. e' una decisione
> editoriale **senza regola**, quindi non e' una funzione dei minuti e **non e'
> riproducibile da nessuna feature**. Un modello che tenti di predire l's.v. da
> minuti su quella scala sta modellando rumore editoriale. E' un limite che va
> scritto accanto al numero, non in fondo — nello spirito del vincolo 5 del
> progetto.

---

## 8. Provider dei voti e continuita' fra stagioni

Il sito offre **tre scale distinte**, presenti contemporaneamente sulla stessa
pagina e distinte da icone `[verificato]`:

| scala | chi la produce | natura |
|---|---|---|
| **Redazione Fantacalcio** | redazione interna di pagellisti | soggettiva; **unica con voti live** |
| **Voto Statistico** | algoritmo **Alvin482** | oggettiva, algoritmica |
| **Voto Italia** | sintesi/media di piu' fonti editoriali sportive italiane | derivata; **non puo' avere voti live** |

`[verificato sul regolamento]` per la descrizione delle tre; i nomi dei
pagellisti (Trevisani, Pardo, Di Marzio, Giunta, Zille) sono
`[verificato sul regolamento]`.

**Continuita' sulle cinque stagioni:**

- **Tutte e tre le scale sono presenti sia sulla 2025/26 sia sulla 2021/22**
  `[verificato — le icone delle tre scale compaiono su entrambe le pagine]`.
  Sulle tre stagioni intermedie e' `[inferito]`.
- Il Voto Statistico Alvin482 e' stato introdotto **dalla stagione 2017/18**
  `[riportato da terzi]`, quindi **precede tutte e cinque** le stagioni
  richieste: su questo asse non c'e' discontinuita' dentro la finestra.
- **`[non verificato]`, e va detto chiaramente:** non ho potuto accertare se il
  **criterio editoriale** della Redazione o la **composizione del paniere** di
  Voto Italia siano rimasti invariati dal 2021/22 al 2025/26. Un cambio di
  paniere in Voto Italia, o un cambio di capo-redazione nella scala soggettiva,
  non e' annunciato in modo visibile e produrrebbe una **discontinuita' di
  livello non osservabile dai dati** — esattamente il tipo di rottura che il
  progetto tratta come rilevante. Il sito **non pubblica un changelog** dei
  criteri di voto per quanto ho potuto vedere.
- **Il sito era precedentemente noto come Fantagazzetta** `[riportato da
  terzi]`. Se il rebranding cade dentro la finestra 2021-2026 — cosa che
  **non ho verificato** — sarebbe un candidato ovvio a discontinuita'.

> **Raccomandazione tecnica, non decisione.** Se si procedesse, la scala
> **Voto Statistico** e' quella con la minore esposizione a discontinuita'
> editoriale, perche' e' generata da un algoritmo, e — se il criterio dei 10
> minuti fosse confermato — l'unica con un s.v. deterministico. Ma e' anche la
> meno usata nelle leghe reali, quindi la scelta dipende da quale asta si vuole
> modellare. Non la decido io.

---

## 9. Quotazioni del listone

`https://www.fantacalcio.it/quotazioni-fantacalcio` `[verificato]`

**Colonne**, in due blocchi paralleli — uno **Classic**, uno **Mantra**:

- comuni: **Calciatore**, **Sq** (squadra), **Ruolo**
- per ciascuna modalita': **QI** (quotazione iniziale), **QA** (quotazione
  attuale), **FVM / 1000** (Fanta Valore di Mercato)

Quindi, punto per punto rispetto a quanto chiesto:

- **Dove stanno**: pagina dedicata `/quotazioni-fantacalcio`.
- **Formato**: pagina **HTML**, piu' un pulsante **"Scarica"** verso
  `/api/v1/Excel/prices/20/1`, cioe' **Excel** `[verificato come link; il file
  non e' stato scaricato]`. Nessun PDF osservato.
- **Storicizzate?** **Si'**: il selettore di stagione va dalla 2015/16 alla
  2026/27, quindi le stagioni passate sono selezionabili `[verificato per il
  selettore]`. Che ciascuna stagione passata restituisca effettivamente il
  proprio listone e' `[inferito]`, non aperto una per una.
- **Iniziali vs aggiornate**: **la distinzione esiste ed e' esplicita**, ed e'
  la coppia **QI / QA** `[verificato]`. Nota importante: QA e' **un unico valore
  corrente**, non una serie storica — non ho visto da nessuna parte lo
  **storico infrastagionale** degli aggiornamenti di quotazione `[verificato in
  negativo per la vista pubblica]`. Per una stagione conclusa, QA sara'
  presumibilmente il valore di fine stagione `[inferito]`.
- **Classic vs Mantra**: **distinti**, sia nei ruoli (Classic: P/D/C/A; Mantra:
  posizioni piu' specifiche) sia nelle quotazioni, con colonne parallele
  `[verificato]`.

Per l'asta, che e' il fine della Fase 8, **QI e' la variabile pertinente** (il
prezzo di partenza), e c'e'. Il fatto che manchi lo storico intra-stagionale di
QA e' un limite solo se si volesse modellare la dinamica dei prezzi, non l'asta
iniziale `[inferito]`.

---

## Tabella riassuntiva delle nove domande

| # | domanda | esito | evidenza |
|---|---|---|---|
| 1 | export ufficiale | **Parziale** — pulsanti "Scarica" verso `/api/v1/Excel/{votes,stats,prices}/...`; **nessuna API pubblica documentata**; login/abbonamento non accertati | `[verificato]` i link; `[non verificato]` il contenuto e i requisiti d'accesso |
| 2 | termini d'uso | **BLOCCANTE** — art. 3.3(a) vieta lo scraping per nome; 8.2 vieta i lavori derivati; 8.3 limita a uso personale non commerciale | `[verificato]`, citazioni integrali |
| 3 | `robots.txt` | **Permissivo** sui percorsi utili; nessun `Crawl-delay`; solo `ia_archiver` escluso da tutto — ma **non autorizza nulla** | `[verificato]` il file; `[inferito]` la subordinazione ai Termini |
| 4 | limiti di frequenza | **Nessun limite numerico dichiarato**; divieto qualitativo di sovraccarico (3.3(c)); WAF non ispezionato | `[verificato]` l'assenza; `[non verificato]` le difese |
| 5 | stagioni 21/22 → 25/26 | **Tutte e cinque presenti**; i due estremi verificati pubblici senza login | `[verificato]` 21/22 e 25/26; `[inferito]` le tre intermedie |
| 6 | minuti giocati | **ASSENTI ovunque** — voti, statistiche e profilo giocatore. Solo `PV` (partite a voto) e "Entrato/Uscito" | `[verificato]` su tre viste |
| 7 | s.v. e soglia minuti | **Nessuna soglia, e il sito lo dichiara**: "Non esiste, e mai esisterà..." — s.v. discrezionale sulla scala Redazione | `[verificato]`; il criterio 10 min di Alvin482 e' `[riportato da terzi]` |
| 8 | provider dei voti | **Tre scale** (Redazione / Statistico Alvin482 / Italia), tutte e tre presenti sia in 21/22 sia in 25/26 | `[verificato]` la presenza; **continuita' del criterio `[non verificato]`** |
| 9 | quotazioni listone | **Presenti e complete**: QI/QA/FVM x Classic/Mantra, storicizzate per stagione, HTML + Excel. Manca lo storico intra-stagionale di QA | `[verificato]` |

---

## Fonti alternative

Elenco dovuto, essendo l'esito bloccante. **Non ho verificato in profondita' i
termini d'uso di nessuna di queste**: sono candidate da istruire, non fonti
approvate. Chiunque le usi deve rifare su ciascuna la verifica fatta qui sopra
per `fantacalcio.it` — a partire dai termini.

### Per i minuti giocati (necessari in ogni scenario)

| fonte | copre | stagioni | export/API | termini |
|---|---|---|---|---|
| **Il repository stesso** | eventi WhoScored Serie A, minuti gia' derivati e **riconciliati esattamente su 760/760 partite** da `sot/minutes.py` | **solo 2025/26** | gia' in `data/`, Parquet | gia' in uso nel progetto |
| **FBref** | statistiche per giocatore/partita, inclusi i minuti | Serie A, copertura ampia | nessuna API ufficiale; scraper di terzi | `[non verificato]` — da leggere prima di tutto |
| **Understat** | dati per giocatore con campo `time`, piu' xG e dati per tiro | Big 5 dal 2014, quindi tutte e cinque | nessuna API ufficiale documentata | `[non verificato]` |
| **football-data.org** | API ufficiale con risorsa Match per competizione/stagione/giornata | Serie A | **API ufficiale e documentata**, piano gratuito | `[non verificato]`, ma **e' l'unica del gruppo con termini pensati per l'accesso programmatico** |
| **`soccerdata`** (probberechts, GitHub) | libreria che unifica FBref, Understat, Sofascore, WhoScored, Football-Data.co.uk | varie | libreria Python | **non risolve il problema legale**: sposta solo lo scraping dentro una dipendenza, e i termini restano quelli del sito a monte |

**La nota piu' utile del gruppo**: il progetto ha **gia'** i minuti 2025/26,
riconciliati e validati. Il fabbisogno reale e' quindi **quattro stagioni**
(2021/22-2024/25), non cinque — e la strada di estendere all'indietro lo
scraper WhoScored gia' presente nel repository e' un'opzione che **non era
stata considerata nel mandato** ma che merita di stare sul tavolo, con i suoi
termini d'uso da verificare a parte.

### Per voti / fantavoto / quotazioni

| fonte | copre | stagioni | export/API | termini |
|---|---|---|---|---|
| **fanta.soccer** | archivio voti e archivio quotazioni, con selettore stagione/serie; testo "Scarica i voti della Serie A" | `[non verificato]` | download dichiarato, formato `[non verificato]` | ha **tre documenti distinti** — "Termini e condizioni di utilizzo dei servizi", "Privacy", "Note Legali" `[verificato che esistono]`, contenuto `[non verificato]` |
| **fantacalcio-online.com** | voti Serie A per giornata, piu' scale (Gazzetta, Corriere, statistici) | 2024/25 e 2025/26 osservate | `[non verificato]` | `[non verificato]` |
| **fantapiu3.com** | archivio voti storico Serie A | `[non verificato]` | `[non verificato]` | `[non verificato]` |
| **pianetafanta.it** | statistiche giocatori dal 2002 | ampia | `[non verificato]` | `[non verificato]` |
| **FIUH.it** | archivio statistiche stagioni passate, file PDF ed Excel di fine stagione | `[non verificato]` | download dichiarato | `[non verificato]` |
| **fantagiaveno.it** | archivio storico voti e prestazioni | `[non verificato]` | `[non verificato]` | `[non verificato]` |

**Avvertenza sostanziale su tutte queste.** I voti del fantacalcio sono un
**contenuto editoriale con un titolare**, non un fatto oggettivo come il
risultato di una partita. I siti aggregatori qui sopra ridistribuiscono in
larga parte voti prodotti da redazioni terze (Gazzetta, Fantacalcio.it/ex
Fantagazzetta, Alvin482). **Cambiare aggregatore non cambia il titolare del
diritto**: si sposta il problema, non lo si risolve. L'unica alternativa
davvero pulita e' una fonte che produca i voti in proprio con licenza esplicita,
oppure l'autorizzazione scritta prevista dall'art. 3.3(a).

---

## Limiti della ricognizione

Quello che **non** ho potuto verificare, e perche':

1. **Contenuto dei file Excel** (`/api/v1/Excel/...`): il vincolo 2 del mandato
   vieta di scaricare dati. Restano ignoti: le colonne effettive, l'eventuale
   presenza dei minuti, il formato. **E' la lacuna piu' importante**, perche' e'
   l'unica che potrebbe ribaltare la conclusione del punto 6.
2. **Requisiti di accesso agli export**: se servano registrazione gratuita,
   abbonamento a pagamento o nessuna delle due. Discende dal punto precedente.
3. **Stagioni 2022/23, 2023/24, 2024/25**: dedotte dal selettore, non aperte una
   per una. Ho verificato i due estremi della finestra.
4. **Continuita' del criterio editoriale fra stagioni** (punto 8): non esiste un
   changelog pubblico che abbia trovato. E' un rischio **non misurabile
   dall'esterno**.
5. **Criterio s.v. di Alvin482** (10 minuti): trovato solo su fonti terze, mai
   sul regolamento ufficiale. Non lo do per accertato.
6. **WAF / rate limit effettivi**: non sondati deliberatamente. Sondare le
   difese di un sito che vieta l'accesso automatizzato sarebbe stato
   incoerente con il mandato.
7. **Numerazione esatta dell'articolo sullo scraping**: 3.3(a) secondo la
   lettura integrale, 3.1(a) secondo la prima lettura parziale. Testo identico,
   numero da confermare a vista.
8. **Termini d'uso di tutte le fonti alternative**: elencate come candidate, non
   istruite.
9. **Se il rebranding Fantagazzetta → Fantacalcio.it** cada dentro la finestra
   2021-2026: non verificato, ed e' un candidato a discontinuita'.

---

## Cosa resta da decidere all'utente

Espongo le opzioni senza sceglierne una.

1. **Se chiedere l'autorizzazione scritta** prevista dall'art. 3.3(a) a
   Fantacalcio S.r.l. E' la sola via lecita per usare questa fonte. Da decidere
   sapendo che: (a) risolve il problema legale ma **non** quello dei minuti;
   (b) ha tempi e esito incerti; (c) l'uso previsto (modello per l'asta) va
   dichiarato onestamente nella richiesta, incluso se sia commerciale.

2. **Se aprire i file Excel** per chiudere il limite 1. E' l'unica verifica che
   puo' cambiare la conclusione sui minuti. **Esce dal mandato di questa
   ricognizione** (vincolo 2) e va autorizzata esplicitamente. Anche pochi
   download manuali per ispezione sono un'attivita' diversa dalla raccolta
   sistematica, ma la distinzione va fatta consapevolmente, non per comodita'.

3. **Da dove prendere i minuti**, che servono comunque. Le opzioni sul tavolo:
   estendere all'indietro lo scraper WhoScored gia' nel repository (che
   coprirebbe 4 stagioni e riuserebbe `sot/minutes.py`, gia' validato
   esattamente su 760/760 partite); oppure una fonte con API ufficiale come
   football-data.org; oppure FBref/Understat, con i loro termini da verificare.

4. **Quale scala di voti** modellare: Redazione (la piu' usata nelle leghe, ma
   con s.v. dichiaratamente discrezionale e quindi non predicibile), Statistico
   Alvin482 (riproducibile, forse con soglia deterministica a 10 minuti, ma meno
   diffusa), o Italia. **La scelta cambia la definizione del target**, quindi va
   fatta prima di raccogliere, non dopo.

5. **Se ridurre l'ambito temporale.** Con la sola 2025/26 il repository ha gia'
   i minuti riconciliati. Quattro stagioni in piu' costano quattro raccolte e
   introducono il rischio di discontinuita' editoriale del punto 8. Se il
   guadagno statistico valga quel costo e quel rischio e' una decisione di
   progetto, non tecnica — ed e' lo stesso tipo di ragionamento costi/benefici
   che la Fase 6F ha applicato al piano dati.

6. **Se accettare che l's.v. non sia modellabile** sulla scala Redazione, e
   dichiararlo come limite accanto ai numeri (vincolo 5 del progetto), invece di
   cercare feature che lo predicano. Alla luce del punto 7, un modello dell's.v.
   su quella scala starebbe adattandosi a discrezionalita' editoriale.

---

*Ricognizione documentale del 2026-07-31. Nessuno scraper scritto, nessun dato
scaricato, nessuna dipendenza aggiunta. L'unico file prodotto e' questo.*

---

# Addendum — verifica diretta dell'export (2026-07-31)

Su via esplicita dell'utente ("procedi con l'apertura dei file dell'export"),
che revoca per questo solo punto il vincolo 2 del mandato. Restano in vigore
tutti gli altri: nessuno scraper, nessun aggiramento, nessuna dipendenza.

## Esito in una riga

**I file dell'export non si sono potuti aprire: tutti gli endpoint rispondono
`401 Unauthorized` con corpo vuoto.** Servono le credenziali di un account.
La domanda piu' importante del report — *cosa c'e' dentro quei file, e in
particolare se contengano i minuti* — **resta senza risposta**, e non per
scelta.

## Cosa e' stato fatto

Quindici richieste HTTP in tutto, nessun file di contenuto acquisito
(0 byte scaricati dagli endpoint di export). Le tre pagine HTML pubbliche sono
state salvate nella cartella temporanea di sessione, non nel repository, e
lette come **markup** invece che come pagina resa: e' l'unico modo di
distinguere un dato assente da un dato che l'interfaccia non mostra.

| verifica | esito |
|---|---|
| `GET /api/v1/Excel/votes/20/38` | **401**, `Content-Length: 0` |
| `GET /api/v1/Excel/votes/16/1` | **401** |
| `GET /api/v1/Excel/stats/20/1` · `stats/16/1` | **401** |
| `GET /api/v1/Excel/prices/20/1` · `prices/20/38` | **401** |
| pagina `/voti-fantacalcio-serie-a` | **200**, 1.24 MB |
| stessa richiesta con cookie di sessione anonima + `Referer` + `X-Requested-With` | **401** |

La sessione anonima non basta: il sito rilascia solo i cookie di bilanciamento
`AWSALB`/`AWSALBCORS`, che non autenticano. Il gate e' sull'account, non sulla
provenienza della richiesta.

**Nessun tentativo e' stato fatto di procurarsi una sessione autenticata** —
non indovinando credenziali, non forgiando cookie, non cercando endpoint
alternativi che eludano il controllo. Il vincolo 3 del mandato vieta di
proporre aggiramenti; a maggior ragione vieta di eseguirli.

## Account gratuito o abbonamento?

Il pulsante porta la classe CSS **`only-for-logged`** — e' nascosto a chi non
ha fatto login, ed e' l'unica condizione che il markup esprime. Su tutte e tre
le pagine:

| classe di gating | voti | statistiche | quotazioni |
|---|---|---|---|
| `only-for-logged` (sul bottone "Scarica") | si' | si' | si' |
| `premium` / `abbonat*` / `paywall` / `locked` | **0 occorrenze** | **0** | **0** |

Il menu utente offre `/login` e `/registrazione`, entrambi liberi.

> **Da qui a "basta un account gratuito" c'e' un salto che non faccio.**
> L'assenza di una classe di paywall nel markup dice che *questa pagina* non
> distingue i livelli di account; non dice che il **server** non li distingua
> quando serve il file. La differenza si vede solo dall'interno di una sessione
> autenticata. Stato: `[non verificato]`.

## Correzioni al corpo del report

1. **Lo schema `/<risorsa>/<idStagione>/<giornata>` vale solo per `votes`.**
   Per `stats` e `prices` il secondo parametro e' `1` mentre la pagina dichiara
   in commento `<!-- Last Matchweek: 38 -->`: non e' una giornata. Cosa sia
   — tipo di lega, listone, o costante — e' `[non verificato]`. Per `votes`
   l'identita' col numero di giornata e' invece confermata su tre casi
   (`votes/20/38` sulla pagina della 38a, `votes/20/1` e `votes/16/1` sulle
   prime giornate).

2. **I tre idStagione intermedi non sono piu' inferiti.** Le pagine per
   stagione seguono lo schema `/voti-fantacalcio-serie-a/<AAAA-AA>/<giornata>`
   e ciascuna espone nell'`href` del proprio bottone l'id corrispondente:

   | stagione | pagina | idStagione |
   |---|---|---|
   | 2021/22 | 200 | **16** |
   | 2022/23 | 200 | **17** |
   | 2023/24 | 200 | **18** |
   | 2024/25 | 200 | **19** |
   | 2025/26 | 200 | **20** |

   Tutte e cinque le stagioni del perimetro sono raggiungibili **senza login**
   nella vista HTML. `[verificato]`

## Conferme dal markup (prima erano letture dell'interfaccia)

- **I minuti non ci sono, e ora lo si sa dal sorgente.** Il subentrato e'
  marcato `<img ... title="Subentrato">`, il sostituito `title="Sostituito"`.
  Nella riga del giocatore non compare nessun numero di minuto, in nessun
  attributo. Non e' l'interfaccia che li nasconde: **non sono nel dato**.
  Questo tiene ferma la decisione gia' presa dall'utente — i minuti vengono da
  WhoScored — e la estende, come gia' riferito, a tutte e cinque le stagioni.
- **Le tre scale stanno affiancate nella stessa riga**, in ordine fisso
  Redazione / Statistico / Italia, ciascuna con voto e fantavoto in
  `data-value`. Prendere la scala Redazione non costa una richiesta in piu':
  arriva insieme alle altre due, che si scartano in lettura.
- **Bonus e malus sono gia' strutturati**, un attributo per voce: gol segnati,
  gol subiti, autoreti, rigori segnati, rigori sbagliati, rigori parati,
  assist, *player of the match*. Nessun parsing di testo libero.
- **Il link del giocatore porta un id numerico stabile e la stagione**
  (`/serie-a/squadre/<squadra>/<nome>/554/2025-26`): e' la chiave con cui
  ricucire l'identita' fra stagioni, che altrimenti sarebbe da fare sui nomi.
- **Il markup della 2021/22 e' identico a quello della 2025/26**: stessi titoli
  delle tre scale, stessi marcatori di subentro. Un parser solo copre le cinque
  stagioni.
  > Questa e' continuita' **strutturale**, non editoriale. Non e' una prova che
  > il criterio di voto sia lo stesso: quella resta la verifica di §5 di
  > `docs/regole_fantacalcio.md`, da fare sui numeri.

## Cosa cambia per la decisione

La decisione 2 di "Cosa resta da decidere all'utente" e' **eseguita e chiusa
senza risposta**: non richiede piu' un via, richiede delle credenziali.
Le vie che restano, senza sceglierne una:

- **Un download manuale da parte dell'utente**, loggato, di *un solo* file per
  risorsa. Chiude in un minuto la domanda sulle colonne — inclusa quella sui
  minuti, che il markup HTML dice assenti ma che nell'Excel potrebbero esserci.
  E' un click, non una raccolta.
- **La vista HTML come fonte**, che e' pubblica su tutte e cinque le stagioni e
  contiene tutto cio' che serve tranne i minuti. Resta pero' soggetta **agli
  stessi termini d'uso** dell'export: la portata dell'autorizzazione che
  l'utente dichiara di avere va verificata su questo punto, perche' e' quella
  che rende lecita o illecita la raccolta, non il formato del file.

*Addendum del 2026-07-31. Nessun byte di contenuto acquisito, nessun file
scritto nel repository fuori da questo report, nessuna dipendenza aggiunta.*
