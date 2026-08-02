# Acquisizione WhoScored — cinque stagioni di Serie A

Esito dello scaricamento richiesto dall'utente dopo la parametrizzazione di
`scrape_season.py`. **Autorizzazione WhoScored dichiarata dall'utente**,
distinta da quella Fantacalcio.it e registrata in `docs/regole_fantacalcio.md`
§7.1.

**Nessun numero delle Fasi 1-6 è cambiato**: la 2025-2026 era già in casa e la
guardia di idempotenza l'ha saltata senza toccarne un file — verificato dal
manifest, che le assegna la data di download originale (2026-07-29) e non
quella di queste esecuzioni.

---

## 1. Cosa c'è adesso

| stagione | CSV | calendario | mancanti | |
|---|---:|---:|---:|---|
| 2021-2022 | **374** | 380 | 6 | |
| 2022-2023 | **375** | **381** | 6 | 381 = 380 + playout |
| 2023-2024 | **380** | 380 | 0 | ✅ |
| 2024-2025 | **380** | 380 | 0 | ✅ |
| 2025-2026 | **380** | 380 | 0 | ✅ già presente |
| | **1.889** | 1.901 | **12** | 4,8 GB |

**Copertura 99,4%.** Due stagioni complete si aggiungono alle due che c'erano;
due sono complete al 98,4%.

### Controlli di integrità

| controllo | esito |
|---|---|
| file vuoti o troncati | **0** — il più piccolo è 2,17 MB |
| schema | **259 colonne** su tutte e cinque le stagioni |
| squadre per stagione | **20** in tutte |
| hash distinti | **1.889 su 1.889** |
| URL di provenienza | presente su tutte le voci |

Lo schema regge senza sorprese. L'unica differenza fra stagioni è `isOwnGoal`,
che compare solo nelle partite con un autogol: è la trappola già documentata in
`CLAUDE.md`, vale per tutte le booleane derivate da `satisfiedEventsTypes`, e
`sot/io_events.py` le forza già a `False`. **Non è una divergenza fra stagioni.**

L'unicità degli hash non è un dettaglio: due file identici avrebbero significato
la stessa pagina salvata due volte, tipicamente una pagina d'errore scritta al
posto dei dati.

---

## 2. Le 12 partite non acquisite, e perché la perdita non è neutra

**Accertato: WhoScored non ha i dati evento di quelle partite.** Non è un
difetto dello scraper, e non si recuperano.

Le dodici sono state riaperte **una per una** e ispezionate. In tutte e dodici
lo script della pagina è identico — 5.079 caratteri contro il ~1 MB di una
pagina con i dati — e contiene:

```js
matchCentreData: null
```

Il parser di `main.py` muore lì: `metadata.index('{')` su `'matchCentreData:
null'` solleva `ValueError: substring not found`. **Il messaggio descriveva
l'incidente meccanico e nascondeva il fatto**, ed è costato tempo: manda a
cercare un difetto nel codice — indentazione, tag sbagliato, pagina non caricata
— quando la verità è che la fonte non ha quei dati. Due ipotesi di questo tipo
sono state formulate e scartate con la misura prima di arrivare alla causa.

Correzione in `acquisition/whoscored/pagina.py`: la diagnosi distingue **dati
assenti alla fonte** da **pagina inattesa**, e sono due cose con azioni opposte
— la seconda si ritenta, la prima si dichiara. Il riepilogo dello scraper ora le
conta separatamente e dice esplicitamente che le prime non si recuperano
rilanciando. Le dodici sono registrate in `data/raw/manifest.json` sotto
`assenti_alla_fonte`, con URL, risultato e data di verifica: **è provenienza
dell'assenza**, e senza di essa la prossima sessione vede 374 su 380, non sa
perché, e ritenta.

| stagione | partite |
|---|---|
| 2021-2022 | Salernitana-Atalanta · Napoli-Bologna · Atalanta-Lazio · Cagliari-Atalanta · Napoli-Verona · Sassuolo-Empoli |
| 2022-2023 | Napoli-Spezia · Empoli-Atalanta · Cremonese-Monza · Cremonese-Atalanta · Verona-Sassuolo · Atalanta-Spezia |

### La perdita non è distribuita a caso fra le squadre

**È il punto che conta, ed è il motivo per cui questa sezione esiste.**

| squadra | partite perse | |
|---|---:|---|
| **Atalanta** | **6** | 35/38 nel 2021-22 **e** 35/38 nel 2022-23 |
| Napoli | 3 | 36/38 e 37/38 |
| Verona, Sassuolo, Empoli, Spezia, Cremonese | 2 | |
| Salernitana, Bologna, Lazio, Cagliari, Monza | 1 | |

Se le dodici perdite si distribuissero a caso, l'attesa per una singola squadra
sarebbe **1,2**. L'Atalanta ne ha sei.

Sotto `Binom(12, 0.1)` la probabilità di arrivare a sei o più è **0,054%**. Ma
l'Atalanta è stata scelta *perché* è il massimo di venti squadre, e la
correzione per quella scelta va fatta: **1,1%**. Con l'approssimazione di
Poisson, 3,0%. In entrambi i casi è piccola, ma non trascurabile, e il campione
è di dodici eventi — **non è una prova, è un segnale che va dichiarato.**

**Non ne conosco la causa e non la invento.** Due ipotesi controllate e
scartate: il raggruppamento temporale (nel 2021-22 cinque perdite su sei stanno
in dieci giorni, il che spiegherebbe due delle sei dell'Atalanta, ma nel 2022-23
non c'è alcun raggruppamento) e un difetto del nostro parser (escluso: la causa
è `matchCentreData: null`, §2 sopra).

Quello che ora si sa con certezza è **dove sta il buco**: nell'archivio di
WhoScored, non nella nostra acquisizione. Perché quell'archivio manchi proprio
di sei partite dell'Atalanta resta aperto, e con dodici eventi non è
rispondibile da qui.

### La conseguenza operativa, che vale a valle

I dati mancanti **non lo sono a caso rispetto alla squadra**. Ne seguono due
regole per chi aggregherà:

1. **I denominatori si prendono dai dati, non si assumono a 38.** Valgono 35
   per l'Atalanta in due stagioni, 39 per Spezia e Verona nel 2022-23 (playout),
   38 altrove.
2. **Il deficit dell'Atalanta va dichiarato accanto a ogni numero
   dell'Atalanta**, come vuole il vincolo 5 — nella stessa riga, non in fondo.
   Un tasso per partita su 35 partite non è meno valido di uno su 38, ma se le
   tre partite perse non fossero rappresentative della sua stagione, lo scarto
   finirebbe dentro la stima di ρ senza lasciare traccia.

---

## 3. Due difetti del codice, trovati eseguendolo

Nessuno dei due era visibile senza scaricare davvero.

### 3.1 Un banner pubblicitario è costato un'intera stagione

Il primo giro ha perso **tutta la 2022-2023**:

```
<select id="stages"> is not clickable at point (584,173)
because another element <div class="…"> obscures it
```

È lo stesso identico problema che il codice del fork **già documentava** per il
bottone "giorno precedente", dove era risolto con un click via JavaScript. Sul
menu `stages` la stessa gestione non c'era, e il `try/except` intorno
intercettava `NoSuchElementException` e `TimeoutException` ma **non**
`ElementClickInterceptedException`: invece di ripiegare sulla lettura del
calendario visibile, ha abortito la stagione.

Corretto con `_select_stage()`, stesso ripiego, più l'evento `change` esplicito
— senza il quale la pagina resterebbe sullo stage precedente e si rileggerebbero
le stesse partite.

**Ha funzionato ciò che era stato progettato per questo**: una stagione che
fallisce non ferma le altre. La 2023-2024 è partita lo stesso ed è completa.
Senza quella scelta, il primo giro avrebbe prodotto una stagione invece di tre.

### 3.2 Il controllo di completezza chiamava "incompleto" un calendario completo

La 2022-2023 ha **due stage**: `Serie A` e `Serie A Relegation Playoff`. Quindi
381 partite, e due squadre a 39.

`report_completeness` confrontava con `!= expected`, così le squadre a **39**
finivano nell'elenco intitolato *"squadre con **meno** di 38 partite"*. Due
conseguenze: quattro passate di navigazione buttate a cercare partite già
presenti, e un messaggio che diceva il falso.

Corretto separando i due casi. **Il playout non viene scartato**: è una partita
di Serie A davvero giocata. Viene segnalato, perché rende il conteggio di quelle
due squadre diverso dalle altre diciotto.

La funzione è stata **spostata in `target.py`**, che non importa selenium: è
logica pura su una lista di dizionari, e dentro lo scraper era verificabile solo
eseguendolo — che è esattamente il motivo per cui il difetto è arrivato fin qui.

---

## 4. Provenienza — vincolo 8

`data/raw/manifest.json`, 851 KB, **versionato in git**: è l'unica cosa sotto
`data/` che ci sta, perché una provenienza senza storia non è verificabile.

Per ciascuno dei 1.889 file: fonte, campionato, stagione, `matchId`, **URL**,
data di download, byte, **SHA-256**. Più la **definizione della metrica nella
fonte**, che è la metà del vincolo 8 che si dimentica: non basta sapere da dove
viene un numero, serve sapere cosa significa *lì*.

Tre proprietà, tutte con un test:

- **`acquisition/manifest.py` non scarica**: registra ciò che è già su disco.
  Tenere separate acquisizione e registrazione significa che il manifest si può
  ricostruire senza rifare i download.
- **Non tocca `raw/`**: l'unico file che scrive è il manifest.
- **Un hash cambiato è un evento, non un aggiornamento**: la revisione
  precedente viene conservata e la modifica segnalata. È il caso che il vincolo
  9 vuole rendere visibile — la fonte che cambia i dati sotto di noi.

Le date di download sono prese dal `mtime` dei file, non dall'istante di
registrazione: **datarli tutti allo stesso momento sarebbe stata una provenienza
comoda e falsa.** Si leggono tre giornate distinte — 380 file il 29 luglio
(la 2025-26 preesistente), 1.122 il 31 luglio, 387 il 1° agosto.

---

## 5. Limiti da portare a valle

- **La fonte non è Opta direttamente**: è la chalkboard di WhoScored, e il
  dominio contattato è **`1xbet.whoscored.com`**, un mirror di affiliazione
  fissato in `acquisition/whoscored/main.py:60` ed ereditato dal fork — non
  `www.whoscored.com`. Registrato nel manifest. Se l'autorizzazione ottenuta
  copre WhoScored ma non il mirror, il dominio va cambiato.
- **12 partite mancanti, non a caso rispetto alla squadra** (§2).
- **Le stagioni non hanno tutte lo stesso numero di partite**: 374 acquisite su
  380 nel 2021-22, 375 su 381 nel 2022-23, 380 nelle altre tre.
- **La 2021-22 è la prima stagione di ritorno del pubblico** dopo le
  restrizioni: il vantaggio del campo di quel periodo non è confrontabile con
  quello delle successive (`docs/regole_fantacalcio.md` §5). Vale per ogni
  stima che attraversi quella stagione, ρ compreso.
- **Nessuna verifica di stabilità del criterio di rilevazione fra stagioni.**
  Lo schema è identico, il che non implica che il *modo* di annotare gli eventi
  lo sia. È una cosa da misurare prima di stimare ρ su cinque stagioni, non da
  assumere — e non è stata fatta qui.
