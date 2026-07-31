# Fase 7 — Strato di acquisizione multi-campionato e multi-stagione

Leggi CLAUDE.md e docs/regole_fantacalcio.md.

Lancia un sub-agent ricognitore con questo compito, e non scaricare né scrivere nessuno scraper: è solo una verifica di fattibilità.

Per la fonte indicata nella sezione 4 del documento, riporta:

termini d'uso e cosa dicono esplicitamente sull'accesso automatizzato;
contenuto di robots.txt per i percorsi che servirebbero;
se esiste un export ufficiale (file scaricabile, area riservata, API) che eviti del tutto lo scraping — questa è la domanda più importante;
quali stagioni fra 2021/22 e 2025/26 sono effettivamente accessibili;
se i minuti giocati sono presenti o solo il voto;
come viene marcato l's.v. e a quale soglia di minuti;
se il provider dei voti è dichiarato e se è lo stesso su tutte e cinque le stagioni;
dove stanno le quotazioni del listone e in che formato.

Se i termini d'uso vietano l'uso che serve qui, fermati e dillo: non proporre aggiramenti, elenca invece le fonti alternative che hai trovato.

Output: reports/phase7_fattibilita_fonte.md. Poi fermati.

Questa fase ne aggiunge tre, e sono il motivo per
cui esiste:

7. **Mai mescolare due definizioni della stessa grandezza senza averle prima
   misurate una contro l'altra.** Un "tiro in porta" preso da una fonte diversa
   da Opta non è la stessa grandezza finché non è dimostrato che lo sia. Se
   divergono, si tengono in due colonne separate: non si converte, non si
   sceglie la più comoda.
8. **Ogni riga scaricata porta con sé la sua provenienza**: fonte, URL, data di
   download, hash del file, e la definizione della metrica *in quella fonte*.
   Una riga senza provenienza non entra nel dataset.
9. **Ogni download è idempotente e ripartibile.** Un file già scaricato e con
   hash invariato non si riscarica. Nessuna esecuzione deve poter cancellare o
   sovrascrivere dati grezzi già acquisiti.

**Nessun numero delle Fasi 1-6 cambia in questa fase.** Se qualcosa cambia, è
un difetto: fermati e riferisci invece di aggiornare il README.

Procedi un blocco alla volta. **Alla fine di ogni blocco fermati e riferisci
prima di proseguire.** Non passare al blocco successivo di tua iniziativa.
Test nuovi per ogni blocco.

---

## Perché questa fase esiste

Il progetto si estende da una squadra a tutte e venti. Il livello della
proiezione del Como poggia su `REF_TOPDOWN_PER_MATCH = 4.90`, che la Fase 6A ha
stabilito essere **un valore fornito, non ricostruibile da questi dati**. Per
le altre diciannove squadre quel valore non esiste.

Ne segue che **ρ, la persistenza fra stagioni dell'eccesso di una squadra sulla
media di campionato, passa da assunzione dichiarata a parametro bloccante**.
Oggi vale 0.808 per costruzione e la griglia 0.50-0.95 sposta la proiezione di
19 tiri di stagione. Non è più accettabile a scala di campionato.

L'obiettivo di questa fase è quindi preciso: **portare in casa i dati che
chiudono D1, D2 e D5** del piano in `reports/phase6_piano_dati.md`, alla
granularità minima che li chiude e non a una più fine.

---

## 7A — Consolidare prima di moltiplicare

La radice del repository contiene oggi tre punti d'ingresso di scraping
(`main.py`, `Scrape matches.py`, `scrape_serie_a_2025_2026.py`), residui del
fork (`EPV_grid.csv`, `linecollection.py`, `visuals.py`, `utils.py`,
`tutorial.ipynb`, `logo.jpg`), un `events.csv` che è una partita di Women's
Super League, un `serie_a_2025_2026_events.csv` da 1 GB che è la
concatenazione di dati già presenti, e un `test.py` che non sta in `tests/`.

Moltiplicare questo per trenta stagioni-campionato è il modo sicuro di rendere
il repository ingestibile. **Non scaricare niente in questo blocco.**

1. Proponi — e fermati per l'approvazione, non eseguire — una riorganizzazione:
   cosa va in `acquisition/`, cosa in `legacy/`, cosa si cancella perché è
   rigenerabile, cosa resta in radice. Motiva ogni spostamento.
2. `data/` deve diventare consapevole di campionato e stagione. Proponi un
   layout esplicito, con la stagione in formato non ambiguo, e verifica che i
   percorsi in `config.py` continuino a risolversi per la Serie A 2025-26.
3. **La suite deve restare verde e i numeri identici** dopo la
   riorganizzazione. È il controllo che il refactor non abbia toccato niente
   di sostanziale.

---

## 7B — Acquisizione G1/G2 da fonte tabellare

Granularità G2 del piano: una riga per squadra-partita, con tiri in porta,
avversario, campo e **data**. Da lì G1 si aggrega.

Fonte: `football-data.co.uk`, file CSV per campionato-stagione. La Serie A è
`I1`. Colonne rilevanti: `Date`, `HomeTeam`, `AwayTeam`, `HS`/`AS` (tiri),
`HST`/`AST` (tiri in porta), più le quote, che servono al blocco 7F e vanno
conservate anche se qui non si usano.

1. Modulo `acquisition/tabular.py`: scarica, verifica, scrive in `data/raw/`
   **senza trasformare niente**. Il grezzo resta grezzo; la normalizzazione è
   un passo separato e reversibile.
2. **Manifest obbligatorio** (`data/raw/manifest.json` o equivalente): per ogni
   file, URL, data di download, dimensione, hash. Una seconda esecuzione con
   hash invariato non riscarica e lo dice. Un hash cambiato è un evento da
   segnalare, non da assorbire in silenzio.
3. **Sii educato con la fonte**: una richiesta alla volta, pausa fra le
   richieste, `User-Agent` identificabile, rispetto di `robots.txt`, e
   nessuna riesecuzione automatica in caso di errore oltre un tetto dichiarato.
   Verifica i termini d'uso del sito e riportali nel report: se vietano l'uso
   che ne vogliamo fare, **fermati e dillo** invece di procedere.
4. Ampiezza: **Serie A, tutte le stagioni disponibili** in cui `HST` esiste
   davvero. Poi Premier League, Liga, Bundesliga e Ligue 1 **solo** per il
   controllo di robustezza di ρ del blocco 7D — non per mescolarle alla Serie A.
5. Non tutte le colonne esistono in tutte le stagioni. **Rileva la
   disponibilità invece di assumerla**, e produci una tabella
   campionato × stagione × colonna che dica cosa c'è davvero. È da lì che si
   decide quante stagioni sono utilizzabili, non da un numero deciso a priori.

---

## 7C — Riconciliazione delle definizioni

**È il blocco critico. Se salta questo, tutto il resto è aria.**

La fonte tabellare compila i risultati da aggregatori (Xscores, Sportinglife,
BBC, ESPN, Flashscore), non da Opta. La nostra definizione di tiro in porta
esclude pali e tiri respinti da un difensore e coincide esattamente col flag
Opta `shotOnTarget`. **Non c'è alcuna garanzia che l'altra faccia lo stesso**,
e includere i pali sposta la media di campionato da 4.03 a 4.27.

C'è un punto di sovrapposizione perfetto: la **Serie A 2025-26**, che esiste in
entrambe le fonti e dove la nostra media è 4.034.

1. Confronta le due serie sulla stagione condivisa, a tre livelli: media di
   campionato, media per squadra, e **partita per partita** sulle 380 partite
   appaiate. La terza è quella che conta: due medie possono coincidere con
   definizioni diverse.
2. Riporta scarto medio, dispersione dello scarto, e quante partite differiscono
   di 0, 1, 2, 3+ tiri. Se la differenza è sistematica e costante è una cosa; se
   è rumore di rilevazione è un'altra; se è entrambe è un'altra ancora.
3. Prova a **spiegare** la differenza, se c'è, con le grandezze che già abbiamo:
   pali (`ShotOnPost`) e tiri respinti (`shotBlocked`) sono in `shots.parquet`.
   Sommandoli alla nostra definizione, la divergenza si chiude? Questo
   identifica *quale* definizione usa l'altra fonte, invece di limitarsi a
   misurare che è diversa.
4. **Non allineare, non convertire, non scegliere.** Le due colonne restano
   distinte e nominate in modo che sia impossibile confonderle. Se il blocco
   7D dovrà usare quella esterna, lo farà sapendo cosa sta usando.
5. Se la divergenza è tale da rendere le due serie non commensurabili, **è un
   risultato e va scritto**: significa che ρ stimato sulla fonte esterna
   descrive la sua definizione, non la nostra, e va etichettato così ovunque
   compaia.

---

## 7D — Il primo uso vero: D1, D2, D5

Non un blocco di analisi generale: le tre domande che la Fase 6 ha lasciato
aperte e che questa fase esisteva per chiudere. Tutti i vincoli soliti, in
particolare i **baseline stupidi accanto a ogni stima**.

**D1 — ρ.** Stima la persistenza fra stagioni dell'eccesso di una squadra sulla
media di campionato: regressione dell'eccesso in stagione *t+1* sull'eccesso in
*t*, su tutte le squadre e tutte le transizioni disponibili. Riporta la
pendenza con l'errore standard e confrontala con **0.808**, il valore implicito
nel numero oggi pubblicato. Attenzione a tre cose: le squadre retrocesse
escono dal campione e questo seleziona (dichiara la selezione, non correggerla
di nascosto); le stagioni senza pubblico non sono confrontabili sul vantaggio
del campo; e ρ va stimato **anche sugli altri quattro campionati separatamente**,
non per mediarli ma per vedere se il valore italiano è un'eccezione.

**D2 — l'ancora 4.90.** Il riferimento è dichiarato come modello di persistenza
con coefficienti 0.591 sull'ultima stagione e 0.247 sulla penultima. Se la
forma è lineare negli eccessi, è invertibile: `4.034 + 0.591×1.071 + 0.247×e`
uguale a 4.90 implica un eccesso del Como nel 2024-25 di circa **+0.94**. Il
Como 2024-25 era alla prima stagione in Serie A dopo ventun anni, chiusa al
decimo posto. **Verifica quel numero** con i dati appena scaricati. Se torna,
D2 si chiude. Se non torna, la forma funzionale non è quella dichiarata, e
anche questo è un risultato. Non aggiustare 4.90 in nessun caso: il numero
pubblicato resta finché non lo decide l'utente.

**D5 — il prior delle neopromosse.** Tiri in porta concessi dalle squadre
neopromosse, su tutte le coorti disponibili: media e dispersione, non un punto.
Confrontalo con la coorte 2025-26, che è l'unica su cui il progetto ha finora
poggiato.

Report in `reports/phase7_persistenza.md`. **Non aggiornare la proiezione del
Como.** Questo blocco produce stime, non le applica: applicarle è una decisione
dell'utente e sarà semmai una fase a sé.

---

## 7E — G3, i giocatori: decidere prima di scaricare

I tassi per 90 per giocatore (D4, D7) **non sono in questa fonte** e le
alternative hanno vincoli molto diversi fra loro per copertura, termini d'uso,
limiti di frequenza e stabilità nel tempo.

**Non scaricare niente e non scegliere.** Produci
`reports/phase7_opzioni_giocatori.md` che confronti le opzioni realistiche su:
campionati e stagioni coperti, granularità effettiva, presenza dei minuti
(senza minuti un tasso per 90 non esiste), termini d'uso, fragilità
dell'accesso, e **cosa sblocca esattamente** fra D4 e D7. Includi l'opzione
"nessuna delle precedenti, si resta senza dati giocatore" con le sue
conseguenze.

Poi fermati. La scelta è dell'utente.

---

## 7F — Le quote (solo inventario, non usare)

`CLAUDE.md` vieta i backtest su quote generate dal modello perché sono
circolari, e dichiara che servirebbero **prezzi di mercato reali**. La fonte del
blocco 7B contiene quote di mercato storiche, e in radice c'è un file
`Como_tiri_in_porta_quote_2025-....xlsx` di provenienza non documentata.

1. Inventaria che quote sono arrivate con 7B: quali bookmaker, quali mercati,
   quali stagioni, e se esistono mercati sui tiri in porta o solo su esiti e
   gol. Verifica la provenienza del file in radice e **documentala**; se non è
   ricostruibile, dillo.
2. **Non costruire nessun backtest in questo blocco.** L'uso legittimo di
   prezzi di mercato reali qui è come *baseline*: il mercato è il concorrente
   più forte che un modello di previsione possa avere, ed è la risposta alla
   domanda "il modello sa qualcosa che il prezzo non sa già". Ma è una fase a
   sé, con i suoi vincoli, e va aperta solo quando l'inventario dice che i dati
   ci sono davvero.
3. Il divieto su `legacy/` resta: quel codice non si riusa in nessun caso.

---

## Limiti da dichiarare nel report finale della fase

- La fonte tabellare **non è Opta**: ogni stima che ne esce descrive la sua
  definizione di tiro in porta, misurata contro la nostra in 7C.
- ρ stimato su dati storici assume che la persistenza sia **stabile nel tempo**.
  Non lo è necessariamente: mercato, regolamenti e stili cambiano.
- Le stagioni senza pubblico sono un regime diverso sul vantaggio del campo.
- Le squadre retrocesse **escono dal campione** delle transizioni: la stima di ρ
  è condizionata alla permanenza, e la selezione va dichiarata.