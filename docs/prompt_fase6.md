# Fase 6 — Riconciliazione del livello e validazione della proiezione

Leggi `CLAUDE.md` prima di toccare qualsiasi cosa. Valgono tutti i vincoli non
negoziabili già scritti lì, in particolare: mai stimare su dati che seguono il
target, mai allineare i numeri a un riferimento cambiando la definizione,
baseline stupidi accanto a ogni metrica, limiti dichiarati sulla stessa riga
del numero.

**I risultati negativi delle Fasi 2 e 3 non vanno sistemati.** Questa fase non
serve a farli tornare gradevoli: serve a controllare che misurino quello che
diciamo che misurino. Se un controllo conferma il risultato negativo, il
risultato negativo resta e si documenta meglio.

Procedi un blocco alla volta. **Alla fine di ogni blocco fermati e riferisci
prima di proseguire.** Non passare al blocco successivo di tua iniziativa.
Nuovi test per ogni blocco, nella cartella `tests/`.

---

## 6A — Da dove viene il livello della proiezione

È il blocco più importante. Fallo per primo e non anticipare gli altri.

`fig5` dà il Como a **4.34** tiri in porta a campo neutro. Con vantaggio del
campo ×1.217 e metà partite in casa, quel rating implica circa **4.36 a
partita** su un calendario medio. La proiezione riporta **4.90 dall'alto** e
**5.03 dal basso**. Il README non riconcilia le due cose, e 4.90 × 1.01 fa
4.95, non 5.03.

1. Ricostruisci nel codice, passaggio per passaggio, la catena aritmetica che
   porta dal rating del modello al numero pubblicato. Scrivila in
   `reports/phase6_livello.md` come tabella: valore di partenza, ogni fattore
   applicato, il modulo e la funzione che lo applica, valore risultante.
   Voglio vedere ogni moltiplicazione, nessuna implicita.
2. Stabilisci **da dove nasce 4.90**. Se è un valore di riferimento fornito
   dall'utente e non calcolato dal modello, dillo esplicitamente e cerca nel
   repository ogni punto in cui viene usato come se fosse una stima del
   modello. Non inventare una derivazione che non esiste: se non è
   ricostruibile, scrivi che non lo è.
3. Il gap fra 4.36 e il livello usato ha una giustificazione statistica che il
   progetto già conosce ma non ha mai messo per iscritto: **la ridge minimizza
   l'errore predittivo, non stima livelli senza distorsione, e comprime
   sistematicamente le squadre di vertice** — è lo stesso fenomeno documentato
   in "dove il modello è storto" (terzile alto di lambda) e in Fase 3 (danno
   concentrato sopra 4.5 SoT). Quantifica quella compressione: regredisci i
   rating a campo neutro delle 20 squadre sui rispettivi tassi grezzi corretti
   per il campo, riporta pendenza e intercetta, e mostra che la de-compressione
   implicita nel livello usato è coerente con quella pendenza — **oppure che
   non lo è**. Entrambi gli esiti sono pubblicabili.
4. Aggiorna il README con la catena esplicita e con la spiegazione del punto 3.

**Vincolo:** non toccare `alpha`, `tau` né i rating per far tornare i numeri.
Se non tornano, il fatto che non tornino è il risultato di questo blocco.

---

## 6B — Il test giusto per il bottom-up compositivo

Nella proiezione il contributo per giocatore è **compositivo**: il livello
resta dall'alto, il bottom-up fornisce solo il rapporto (+1.0%). Ma il test
1º/2º tempo di stagione confronta un bottom-up che **fissa anche il livello**
(MAE 0.482) contro il top-down (0.416). Il test boccia un estimatore diverso da
quello effettivamente in uso.

1. In `project_2627.py`, separa nettamente due stimatori e dai loro due nomi
   distinti nel codice: quello che fissa il livello dai giocatori e quello
   puramente compositivo che prende il livello dall'alto e applica solo il
   rapporto di rosa.
2. Rifai il test 1º/2º tempo su **entrambi**, con gli stessi baseline
   affiancati di adesso. Il compositivo va confrontato contro il baseline
   corretto, che è "nessun aggiustamento di rosa", cioè rapporto ≡ 1.0.
3. Documenta onestamente cosa quel test può e non può dire: con una stagione
   sola non c'è ricambio di rosa vero fra le due metà, quindi il test del
   compositivo **è quasi vuoto per costruzione**. Se il risultato è
   indistinguibile da 1.0 non è una conferma del metodo: è mancanza di potenza.
   Scrivilo così.
4. Correggi il README: il risultato negativo attuale riguarda il bottom-up che
   fissa il livello. La versione compositiva usata nella proiezione **non è mai
   stata validata**, e questo è un limite che oggi manca dalla lista.

---

## 6C — Shrinkage entro stagione contro shrinkage fra stagioni

`alpha` è selezionato in walk-forward per prevedere la partita t+1 date le
partite precedenti. La proiezione fa una cosa diversa: prevedere la stagione
2026-27 data la 2025-26. La persistenza fra stagioni è più bassa, quindi lo
shrinkage corretto per il secondo compito è più forte. Anche il test 1º/2º
tempo è *dentro* la stagione e sovrastima la persistenza per costruzione.

Con una stagione sola il coefficiente giusto **non è stimabile**. Non provarci.
Fai invece l'analisi di sensibilità:

1. Parametrizza esplicitamente la quota di eccesso sulla media di campionato
   che la squadra trattiene passando da una stagione all'altra (chiamala `rho`,
   default = il valore implicito nella proiezione attuale, che va ricavato dal
   blocco 6A e non ipotizzato).
2. Fai variare `rho` su una griglia dichiarata, indicativamente 0.50-0.95, e
   ricalcola la proiezione Como per ogni valore, con l'intervallo Monte Carlo.
3. Nuova figura: proiezione stagionale in funzione di `rho`, con il valore
   attualmente implicito evidenziato e il resto in grigio. Convenzioni grafiche
   di `figures.py`, punti con intervallo e mai barre.
4. Nel README, una riga sola e chiara: quanti tiri in porta di stagione si
   spostano per ogni 0.05 di `rho`, e il fatto che il valore corretto non è
   determinabile senza altre stagioni.

---

## 6D — I predittori nel regime a bassa informazione

Gli otto predittori sono stati testati come valore incrementale marginale
contro un effetto attacco con oltre trenta giornate di storia. Sono medie
mobili della stessa squadra: sono collineari con l'effetto attacco, e la
conclusione "ripetono l'informazione invece di aggiungerla" è corretta **in
quel regime**. L'ipotesi diversa, mai testata, è che paghino dove l'effetto
attacco è debolmente identificato.

1. Rifai il test dei predittori restringendo la valutazione alle **prime 8
   partite di ciascuna squadra** — cioè in gran parte le righe oggi escluse dal
   burn-in. Stessi predittori, stessa soglia dichiarata in anticipo,
   stessa correzione per la molteplicità di otto candidati.
2. Riporta i risultati **accanto** a quelli attuali sull'intero campione, non al
   loro posto. Se anche lì nessuno passa, il risultato negativo diventa più
   forte e va detto: non è che i predittori non servono a modello maturo, è che
   non servono neanche a modello acerbo.
3. La potenza su poche righe è bassa. Riporta la potenza effettiva insieme al
   `t`, altrimenti un non-rifiuto si legge come conferma.

**Vincolo:** `xg_per_shot` resta scartato. Questo blocco non lo reintroduce,
lo testa in un regime diverso e riporta il risultato qualunque sia.

---

## 6E — Il calendario 2026-27 non è quello 2025-26

1. La proiezione contro "una difesa media" assume implicitamente lo stesso
   insieme di avversari. Nel 2026-27 tre promosse sostituiscono tre
   retrocesse, e le promosse non hanno un rating stimabile da questi dati.
   Verifica se il codice usa un avversario medio o l'insieme reale, documenta
   quale, e stima quanto vale la differenza usando un intervallo plausibile per
   la difesa delle promosse invece di un punto singolo.
2. La rotazione per le coppe è modellata sui **minuti**. La congestione
   infrasettimanale però agisce anche sul lambda di squadra, non solo su chi
   scende in campo, e quell'effetto oggi non c'è. Non stimarlo da questi dati —
   il Como 2025-26 non giocava le coppe — ma aggiungilo alla lista dei limiti
   con il segno atteso.

---

## 6F — Piano dati, senza scaricare niente

Non scaricare nulla in questo blocco. Produci `reports/phase6_piano_dati.md`
che, per ciascuna delle domande aperte dalle fasi precedenti, dica: quale
domanda, quale granularità minima serve davvero (totali di squadra per
stagione, tassi per 90 per giocatore, oppure eventi grezzi), quante
stagioni o campionati, e quale blocco fra 6A-6E si sblocca.

Il criterio guida: **la maggior parte delle domande aperte non richiede dati
evento.** Il coefficiente di persistenza fra stagioni, il prior per le
neopromosse e la validazione fuori campione della proiezione si rispondono con
totali aggregati per stagione. Gli eventi servono solo se si vuole ricalcolare
field tilt, PPDA e xG interno su altre stagioni, cioè solo per il blocco 6D.

Segnala esplicitamente il caso dei sei nuovi arrivi senza dati (18% dei minuti
proiettati, 13% del lambda su sola media di ruolo): indica per ciascuno quali
dati minimi servirebbero e da quale campionato-stagione, e stima di quanto si
stringerebbe l'intervallo sostituendo la media di ruolo con un tasso
individuale. Quella stima si può fare adesso, per simulazione, senza scaricare
niente.
