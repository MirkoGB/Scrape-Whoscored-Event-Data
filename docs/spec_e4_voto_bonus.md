# Fase 9 — Blocco E4: voto base e bonus

> Da inserire in `docs/prompt_fase9.md` come specifica di E4, senza sovrascrivere
> il resto. Legge come prerequisito tutto ciò che E1, E2, E3 e (b) hanno già
> stabilito — in particolare il gate di E1 e il gate del FVM in
> `sot/quotazioni.py`.

---

## Cornice

Con i bonus noti il MAE scende da 61,4 a 52,5: il margine qui è di ~9 punti,
contro i ~56 delle presenze. È l'ultimo blocco di modellazione prima che il
tetto — gli infortuni, non nei dati — diventi il limite dichiarato del
progetto invece che un limite fra altri.

**Dichiara potenza e MDE prima di guardare l'esito**, come per QI in (b) e come
per 6D. Il test appaiato con MDE resta lo standard: un t che non supera il
proprio MDE non è un nulla, è un test cieco a quella dimensione, e va scritto
così.

---

## E4.0 — la rilettura dei CSV. Prerequisito, costo già noto

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

---

## E4.1 — voto base

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

---

## E4.2 — gol e assist

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

---

## E4.3 — rigori. Assegnazione discreta, non tasso

Un rigorista designato vale +3 per rigore segnato e −3 per uno sbagliato: poca
massa, alta leva, dipende da un'assegnazione discreta. Modello: rigori attesi
della squadra (da E3.1) × P(è lui il designato, da E4.0) × tasso di
realizzazione fortemente shrinkato verso la media di lega.

Il designato 2026/27 è un input, non una stima: parametrizzalo con la
possibilità di impostarlo a mano, e mostra la sensibilità del totale a quel
singolo switch — è la stessa istruzione della specifica originale, non è
cambiata.

---

## E4.4 — cartellini e autogol

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

---

## E4.5 — QI come candidato, con lo stesso avvertimento di (b)

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

---

## Valutazione

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

---

## Chiusura

`reports/fase9_e4_voto_bonus.md`, test dedicati, `CLAUDE.md` aggiornato.
Rieseguire `run_phase1.py` e `run_phase5.py`, confermare gli stessi numeri
pubblicati o dichiarare la rottura. Domande aperte in fondo, comprese quelle
ereditate e non risolte (numero di maglia e FVM d'agosto, appaiate; la domanda
sui portieri probabili titolari).

Se npxG, rigori, cartellini o QI non aggiungono nulla sopra il gate, è un
risultato negativo e si scrive come tale — il progetto ne ha già tre e sono il
suo contenuto migliore.

Fermati a fine blocco.