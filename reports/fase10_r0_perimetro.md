# Fase 10 / Blocco R0 — il perimetro di cio' che e' validabile

> Generato da `scripts/run_fase10_r0.py` il 2026-08-07.
> **Nessuna richiesta di rete. Nessuna stima**: nessun fit, nessun bersaglio,
> nessun iperparametro. Questo blocco *conta*.

Il blocco risponde a una domanda sola, e la risposta decide quanto ha senso
spendere sui blocchi successivi: **di quante partite esiste davvero una
distribuzione del risultato**, e con quante realizzazioni si potrebbe validare
ciascuna affermazione che R2 e R3 vorrebbero fare.

---

## 1. La cascata: dove si perdono le partite

**1889 acquisite → 1739 con previsione → 1638 validabili.**
Il 13.3% si perde, e si perde per **due**
ragioni diverse che non vanno sommate come se fossero la stessa.

| stagione | acquisite | senza_training | con_previsione | perse_burnin | validabili |
|---|---:|---:|---:|---:|---:|
| 2021-2022 | 374 | 30 | 344 | 21 | 323 |
| 2022-2023 | 375 | 30 | 345 | 20 | 325 |
| 2023-2024 | 380 | 30 | 350 | 20 | 330 |
| 2024-2025 | 380 | 30 | 350 | 20 | 330 |
| 2025-2026 | 380 | 30 | 350 | 20 | 330 |

- **`senza_training` (150 partite, 30 per stagione).**
  `validate.date_splits` pretende 30 partite di training prima di produrre una
  previsione: con dieci partite per turno sono **le prime tre giornate**, che nel
  derivato di E3 non compaiono affatto. Non e' una perdita di dati, e' l'assenza
  di un passato da cui prevedere.
- **`perse_burnin` (101 partite).** Hanno una previsione ma non
  sono `eligible`: sono le giornate 4 e 5. La soglia e' **`team_match_idx >= 6`**,
  e la relazione e' verificata invece che assunta — `verifica_soglia_eligible()`
  ritorna `coincide=True`, 0 discordanti su
  3478 righe.

**L'universo acquisito si conta, non si assume a 380.** Il 2022-23 ne ha 375
perche' il calendario ne ha 381 (il playout) e WhoScored ne ha perse 6; il
2021-22 ne ha 374. Sono due scarti di segno opposto e nessuno dei due sarebbe
stato ipotizzabile.

---

## 2. `eligible` e' una proprieta' della SQUADRA, non della partita

Ne segue che una partita puo' avere un lato eligible e l'altro no. **Succede due
volte, ed entrambe nel 2021-22:**

| stagione | data | giornata | casa | trasferta | idx_casa | idx_trasferta | in_ritardo |
|---|---|---:|---|---|---:|---:|---|
| 2021-2022 | 2021-09-25 | 6 | Inter | Atalanta | 6 | 5 | Atalanta |
| 2021-2022 | 2021-09-26 | 6 | Sassuolo | Salernitana | 6 | 5 | Salernitana |

Non e' una curiosita'. `team_match_idx` numera le partite **presenti nei dati**,
quindi su una squadra a cui la fonte ne ha perse alcune scorre indietro: alla sua
sesta partita vera l'Atalanta e' all'indice 5. **E' lo stesso difetto
dell'indice che E2 aveva trovato sulle squalifiche.**

**E il lato in ritardo e' una squadra con perdite alla fonte in entrambi i casi,
verificato e non addotto**: nel 2021-22 l'Atalanta ha 35 partite acquisite su 38
e la Salernitana 37. Sono le due che stanno all'indice 5 mentre l'avversario e'
gia' al 6. Il difetto cade quindi **dove la perdita alla fonte e' gia' dichiarata
non casuale** — l'Atalanta ne perde sei in due stagioni contro un'attesa di 1,2,
p corretto 1,1% — e non a caso fra le venti squadre.

Per una previsione 1X2 **servono entrambi i lati**: un esito non e' meta'
previsto. Le due partite escono, ed e' il motivo per cui il 2021-22 ne perde 21 e
non 20.

---

## 3. La giornata vera, e perche' R3 non puo' usare `team_match_idx`

`team_match_idx` **non e' la giornata** — lo dice gia' il Blocco 0 — e per una
metrica per partita non importa. Per una **classifica** importa: un indice che
salta i recuperi mette la stessa squadra in due turni diversi. La giornata vera
arriva dall'aggancio della Fase 8, che ha chiuso la D6, ed e' disponibile su
**1738 partite su 1739**.

| stagione | giornate_con_previsione | giornate_piene | prima_piena | non_piene |
|---|---:|---:|---:|---|
| 2021-2022 | 35 | 29 | 7 | 4, 5, 6, 10, 11, 12 |
| 2022-2023 | 35 | 27 | 7 | 4, 5, 6, 12, 18, 28, 29, 33 |
| 2023-2024 | 35 | 33 | 6 | 4, 5 |
| 2024-2025 | 35 | 33 | 6 | 4, 5 |
| 2025-2026 | 35 | 33 | 6 | 4, 5 |

- **Una giornata "piena" ha tutte e dieci le partite validabili**, ed e' l'unita'
  che R3 userebbe. Sono **155 su 175**.
- Le giornate non piene **oltre il burn-in** sono esattamente le 12 partite che
  WhoScored non ha: 2021-22 giornate 10-12, 2022-23 giornate 12, 18, 28, 29, 33.
- **La prima giornata piena e' la 6a o la 7a**, mai prima. Ne segue il fatto che
  R3 deve dichiarare in specifica invece di scoprire: **non si simula una
  stagione da zero.** Non esiste una probabilita' di scudetto alla prima
  giornata, perche' prima della sesta il modello non ha previsioni. Si simula il
  **resto** di una stagione a partire dalla giornata k, data la classifica a k.

**L'unica partita senza giornata** e' lo spareggio Spezia-Verona del 2022-23: e'
il residuo gia' dichiarato dall'aggancio — l'unica coppia ordinata che si ripete,
che senza accorgersene si sarebbe agganciata ai voti della giornata 25.

---

## 4. Il bersaglio di R2 regge a due derivazioni indipendenti (vincolo 7)

L'esito osservato viene da due fonti che non si sono mai parlate: i gol
ricomposti dagli eventi WhoScored (con gli autogol riattribuiti, che
`shots_mask` esclude — verificati 3.778/3.778 contro `matches.json` in E3) e il
punteggio della fonte dei voti, che non ha mai visto un evento.

| | |
|---|---:|
| partite confrontabili | 1738 |
| **punteggio identico** | **1738** |
| punteggio discorde | 0 |
| **esito 1X2 identico** | **1738** |
| esito 1X2 discorde | 0 |

**Zero discordanze in entrambi i versi.** Non passa da nessun modello, ed e' la
verifica piu' forte che R0 poteva fare a costo zero: il bersaglio che R2
userebbe non dipende da quale delle due fonti lo fornisce.

Distribuzione osservata dell'esito sulle 1638 partite validabili:

| esito | quota |
|---|---:|
| 1 | 0.4048 |
| X | 0.2674 |
| 2 | 0.3278 |

E' anche il **baseline piu' stupido di R2** (vincolo 6), e va battuto prima di
qualunque altra affermazione.

---

## 5. Quante realizzazioni ha ciascuna affermazione

E' la tabella che decide l'ordine fra G1 e G2, e sta nel codice
(`perimetro.realizzazioni()`) perche' e' un conteggio e non un'opinione.

| affermazione | unita | n | blocco |
|---|---|---:|---|
| 1X2 (RPS, log-loss, calibrazione) | partita | 1638 | R2 |
| over/under sulla linea dei gol | partita | 1638 | R2 |
| classifica: scudetto, Europa, retrocessione | **stagione** | 5 | R3 |
| generalizzazione fra campionati | campionato | 1 | G2 |

**Le due righe di R2 sono abbondanti.** 1638 partite sono due volte e mezzo
le 660 righe su cui le Fasi 2 e 4 hanno concluso, e su un bersaglio — l'esito —
che E3 ha gia' mostrato essere **piu' facile da distinguere** dei tiri in porta
(t = 5,52 contro 1,86 sullo stesso confronto). Il burn-in **non** e' un problema
per R2: era la preoccupazione che ha motivato questo blocco, ed e' infondata.

**La riga di R3 e' il problema, ed e' quantificato.** Una probabilita' di
scudetto ha **una realizzazione per stagione**: cinque stagioni sono cinque
estrazioni. Nessun RPS calcolato su cinque punti separa un modello da un altro.
E le previsioni fatte a giornate diverse **della stessa stagione non sono
indipendenti**: condividono l'esito, quindi 155 giornate piene non sono 155
osservazioni ma cinque, guardate piu' volte.

---

## 6. La dipendenza da G2, dichiarata prima e non scoperta a meta'

| affermazione | G2 la cambia? | perche' |
|---|---|---|
| calibrazione dei parametri | **no** | poolare i campionati e' l'errore che E1 vieta e che E4 ha quantificato (livello dei fit +15,8% fra stagioni; fra campionati di piu'). G2 da' fit **paralleli**, non un fit italiano piu' grande |
| R2 — 1X2, over/under | **no** | 1638 partite bastano; G2 aggiungerebbe generalizzazione, che e' una domanda di G2 |
| **R3 — classifica** | **si', ed e' l'unico punto** | da 5 realizzazioni a 25. **Sottile, non sufficiente** |

**Ne segue che la dipendenza non impone G2 prima.** Impone che R3 dichiari il
proprio limite invece di fabbricare una validazione, che e' il vincolo 5. Se G2
si facesse, porterebbe la classifica da *invalidabile* a *debolmente validabile*:
va detto adesso perche' nessuno se lo aspetti come una soluzione.

---

## 7. Condizione bloccante su G2 — autorizzazione

**Registrata qui come condizione, non come dettaglio tecnico**, su richiesta
dell'utente del 2026-08-07.

L'autorizzazione dichiarata in `regole_fantacalcio.md` §7.1 riguarda **WhoScored
per la Serie A**, via il mirror `1xbet.whoscored.com` fissato in
`acquisition/whoscored/main.py:60`. **Estenderla a quattro campionati e' una
decisione dell'utente, che verra' presa se e quando si arriva a G2, e non
prima.** Nessun blocco della Fase 10 la presuppone.

Accanto, e indipendente: tutti e quattro gli altri campionati hanno
`whoscored: None` in `config.LEAGUE_CODES`. La terna `(regione, torneo, slug)`
**non e' accertata per nessuno**, e `target.py:63` solleva un'eccezione invece di
inventare un URL. «Lo scraper e' gia' parametrizzato» e' vero e non basta.

---

## 8. Domande aperte

1. **La forma della dipendenza fra i due lati non e' stata guardata**, ed e' di
   proposito: R0 non stima. Che i due lambda di una partita vengano dallo stesso
   modello non implica che i gol siano indipendenti dati i lambda, ed e' la
   domanda di R1. Qui c'e' solo l'universo su cui la si misurera'.
2. **Le due partite disallineate potrebbero essere recuperate**, allineando il
   burn-in alla **giornata** invece che a `team_match_idx`. Non e' stato fatto:
   cambierebbe la definizione di `eligible` che E3 ha gia' pubblicato, e due
   partite su 1.638 non giustificano il rischio di spostare un numero altrove.
   Va deciso in R2 **se** si tocca, non qui.
3. **Il playout Spezia-Verona resta fuori** per mancanza di giornata. E' una
   partita vera e non va scartata in silenzio: se R3 la vuole, va deciso a quale
   turno appartenga, e non c'e' una risposta ovvia.
4. **Non e' stato verificato che l'ordine di `p['data']` sia sufficiente a
   ricostruire la classifica progressiva** in presenza di recuperi. R3 ne ha
   bisogno e questo blocco non gliel'ha dato.
