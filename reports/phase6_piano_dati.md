# Fase 6F — piano dati, senza scaricare niente

Che cosa servirebbe davvero per chiudere le domande che le Fasi 6A-6E hanno lasciato aperte. **Non e' stato scaricato niente, non e' stata aggiunta nessuna dipendenza e nessun numero pubblicato cambia**: la proiezione resta 5.03 a partita, 191 in stagione, IC80% [151, 240]. L'unica cosa calcolata qui e' la simulazione sui sei nuovi arrivi, che la specifica del blocco chiede di fare adesso.

Prima di tutto il resto, il fatto di stato: **i blocchi 6A, 6B, 6C, 6D e 6E sono stati eseguiti** e i loro report esistono (`phase6_livello.md`, `phase6_compositivo.md`, `phase6_rho.md`, `phase6_predittori.md`, `phase6_calendario.md`). Questo piano riassume cosa hanno trovato, non cosa avrebbero potuto trovare.

## Esito in breve

1. **Sette domande aperte su otto non richiedono dati evento.** Il criterio non e' una preferenza: segue da dove i blocchi precedenti hanno localizzato l'incertezza. La Fase 6A ha mostrato che il livello pubblicato **non contiene il modello di squadra** — il contesto si semplifica dentro `monte_carlo` — quindi tutto cio' che riguarda il livello vive su totali di squadra per stagione, la granularita' piu' grossolana che esista.
2. **La domanda piu' grande e' anche la piu' economica.** `rho`, la persistenza fra stagioni, sposta la proiezione di 19 tiri (21% dell'IC80%) e si risponde con un numero per squadra per stagione su 10+ stagioni: una tabella che si scrive a mano.
3. **La domanda piu' cara e' quella con il valore atteso piu' basso.** Il blocco 6D avrebbe bisogno di **13.5 stagioni-campionato di eventi grezzi** per portare il test acerbo a potenza 80%, e 4.0 per quello maturo — contro un esito gia' negativo in tre regimi. Una stagione-campionato intera qui vale ~1 GB e 562.672 eventi.
4. **I sei nuovi arrivi sono il limite piu' vistoso e valgono meno di tutti.** Valgono il 18% dei minuti proiettati e il 13% del lambda, ma avere per ciascuno un tasso individuale stringerebbe la deviazione standard della proiezione di **1.0% nel caso migliore** (89 tiri di IC80% che diventano 87), e **di niente** all'estremo superiore dell'incertezza di trasferimento. La simulazione e' nella sezione 3.

---

## 1. Le quattro granularita'

Sono una scala: ogni livello contiene i precedenti. Il piano indica per ogni domanda il **minimo** che basta, non il massimo che si vorrebbe — chiedere una granularita' piu' fine del necessario e' il modo piu' comune di rendere un piano dati irrealizzabile.

| livello   | nome                           | contenuto                                                                                                        |   costo |
|:----------|:-------------------------------|:-----------------------------------------------------------------------------------------------------------------|--------:|
| G1        | totali di squadra per stagione | tiri in porta fatti e concessi, per squadra e per stagione                                                       |       1 |
| G2        | totali di squadra per partita  | una riga per squadra-partita: tiri in porta, avversario, casa, data                                              |       2 |
| G3        | tassi per 90 per giocatore     | minuti e tiri in porta per giocatore-stagione, con la squadra                                                    |       3 |
| G4        | eventi grezzi                  | flusso eventi Opta/WhoScored, l'unico da cui si ricavano possesso, field tilt, PPDA, tocchi in area e xG interno |       4 |

---

## 2. Le domande aperte, una per una

| id   | domanda                                                                                                                            | granularita   | granularita_nome               | sblocca   | eventi   |
|:-----|:-----------------------------------------------------------------------------------------------------------------------------------|:--------------|:-------------------------------|:----------|:---------|
| D1   | rho, la persistenza fra stagioni dell'eccesso di una squadra sulla media di campionato                                             | G1            | totali di squadra per stagione | 6C        | False    |
| D2   | l'ancora 4.90 e' ricostruibile? il modello di persistenza su 21 stagioni che la produce non esiste nel repository                  | G1            | totali di squadra per stagione | 6A        | False    |
| D3   | la de-compressione implicita nel livello usato (x1.109) e' della misura giusta? la pendenza della ridge ne giustificherebbe x1.316 | G2            | totali di squadra per partita  | 6A        | False    |
| D4   | l'estimatore compositivo (quello pubblicato) aggiunge o toglie qualcosa?                                                           | G3            | tassi per 90 per giocatore     | 6B        | False    |
| D5   | quanto concedono le neopromosse, come prior e non come coorte singola                                                              | G1            | totali di squadra per stagione | 6E        | False    |
| D6   | la congestione infrasettimanale abbassa il lambda di squadra a parita' di undici schierato?                                        | G2            | totali di squadra per partita  | 6E        | False    |
| D7   | un tasso individuale per i sei nuovi arrivi, al posto della sola media di ruolo                                                    | G3            | tassi per 90 per giocatore     | 6B        | False    |
| D8   | i predittori da dati evento pagano dove l'effetto attacco e' acerbo?                                                               | G4            | eventi grezzi                  | 6D        | True     |

### Perche' ciascuna e' aperta, e cosa costa

**D1 — rho, la persistenza fra stagioni dell'eccesso di una squadra sulla media di campionato** (G1, sblocca 6C, eventi grezzi: no)

- *perche' e' aperta*: con una stagione sola non esiste il campione su cui stimarla; alpha e il test 1o/2o tempo sono limiti superiori, non stime (Fase 6C)
- *ampiezza minima*: Serie A, 10+ stagioni consecutive (20 squadre x stagione); altri campionati solo per verificare che rho non sia specifico dell'Italia
- *quanto pesa*: 19 tiri di stagione sulla griglia 0.50-0.95, cioe' 21% dell'ampiezza dell'IC80%: la piu' grande assunzione non stimabile del progetto

**D2 — l'ancora 4.90 e' ricostruibile? il modello di persistenza su 21 stagioni che la produce non esiste nel repository** (G1, sblocca 6A, eventi grezzi: no)

- *perche' e' aperta*: e' un valore fornito, dichiarato con coefficienti 0.591 e 0.247, e nessun modulo contiene quel calcolo (Fase 6A)
- *ampiezza minima*: le stesse 21 stagioni di Serie A dichiarate dal riferimento, per la sola squadra proiettata e per la media di campionato
- *quanto pesa*: il livello pubblicato **e'** questo numero: se e' sbagliato lo e' tutta la proiezione, e niente nel repository se ne accorgerebbe

**D3 — la de-compressione implicita nel livello usato (x1.109) e' della misura giusta? la pendenza della ridge ne giustificherebbe x1.316** (G2, sblocca 6A, eventi grezzi: no)

- *perche' e' aperta*: la pendenza 0.760 e' misurata in campione su una stagione: dice quanto la ridge comprime, non quanto una squadra tirera' l'anno dopo (Fase 6A)
- *ampiezza minima*: Serie A, 3+ stagioni consecutive: servono le righe partita per rifittare la ridge, e almeno una transizione di stagione per separare compressione da ritorno alla media
- *quanto pesa*: 0.16 tiri a partita, 6 in stagione, fra livello usato e livello de-compresso

**D4 — l'estimatore compositivo (quello pubblicato) aggiunge o toglie qualcosa?** (G3, sblocca 6B, eventi grezzi: no)

- *perche' e' aperta*: il test 1o/2o tempo e' quasi vuoto per costruzione: MDE 0.0394 contro un intervento medio di 0.0414, e fra due meta' di stagione si libera il 3.9% dei minuti contro il 16.9% fra due estati (Fase 6B)
- *ampiezza minima*: 2+ stagioni consecutive, tutte e 20 le squadre, minuti e tiri in porta per giocatore-stagione piu' i totali di squadra per il contesto; con 20 righe per transizione servono 4-5 transizioni per uscire dalla zona cieca
- *quanto pesa*: e' l'unico limite del README che dice che il metodo pubblicato non e' mai stato validato

**D5 — quanto concedono le neopromosse, come prior e non come coorte singola** (G1, sblocca 6E, eventi grezzi: no)

- *perche' e' aperta*: l'unica coorte osservabile e' quella del 2025-26: tre squadre, una stagione, identita' presa da fuori (Fase 6E)
- *ampiezza minima*: Serie A, 10+ stagioni, tiri in porta concessi per squadra con l'indicazione di chi era neopromossa: 30+ squadre promosse, abbastanza per una media e una dispersione
- *quanto pesa*: 9 tiri di stagione, 0.20 sulla scala di rho: la piu' piccola delle assunzioni non stimabili

**D6 — la congestione infrasettimanale abbassa il lambda di squadra a parita' di undici schierato?** (G2, sblocca 6E, eventi grezzi: no)

- *perche' e' aperta*: il Como 2025-26 non giocava le coppe: zero partite congestionate nel campione, quindi il fattore non e' stimabile qui (Fase 6E)
- *ampiezza minima*: le squadre italiane impegnate in Europa, 3+ stagioni, righe partita con **la data**; il calendario europeo serve solo per marcare quali partite seguono un turno infrasettimanale
- *quanto pesa*: segno atteso negativo e oggi assente dal modello: su questo asse la proiezione e' ottimistica di una quantita' ignota

**D7 — un tasso individuale per i sei nuovi arrivi, al posto della sola media di ruolo** (G3, sblocca 6B, eventi grezzi: no)

- *perche' e' aperta*: del loro campionato di provenienza non abbiamo niente: valgono il 18% dei minuti proiettati e il 13% del lambda su prior di ruolo (Fase 3)
- *ampiezza minima*: una stagione sola, ma del campionato **giusto** per ciascuno, piu' i totali di squadra del loro club per la correzione di contesto; il campionato di provenienza non e' registrato nel repository
- *quanto pesa*: quantificato per simulazione in questo blocco: e' il tetto dell'1.4% di varianza che i nuovi arrivi pesano oggi

**D8 — i predittori da dati evento pagano dove l'effetto attacco e' acerbo?** (G4, sblocca 6D, eventi grezzi: si)

- *perche' e' aperta*: il test acerbo ha potenza 11% e il maturo 28%: nessuno dei due e' sensibile, e cio' che conclude e' un test in campione, che vale solo come limite superiore (Fase 6D)
- *ampiezza minima*: vedi `righe_per_potenza`: e' l'unica domanda che richiede eventi grezzi, e ne richiede molti
- *quanto pesa*: nessun predittore e' passato in tre regimi; il valore atteso di questa raccolta e' il piu' basso di tutte

**7 domande su 8 si chiudono senza un solo evento grezzo**, e le due che spostano di piu' la proiezione (D1 e D2) stanno entrambe sulla granularita' piu' grossolana. Non e' una comodita': e' la conseguenza diretta della Fase 6A, che ha mostrato che il livello pubblicato e' `4.90 x rapporto x convessita'` e che rating, `alpha` e vantaggio del campo decidono come il lambda si ripartisce, non quanto vale.

---

## 3. I sei nuovi arrivi: quanto varrebbe avere i loro dati

Sono 6 giocatori di movimento senza una riga in questi dati: valgono il **18.3% dei minuti proiettati** e il **12.6% del lambda**, oggi interamente sulla media del proprio ruolo.

### Che dati servirebbero, per ciascuno

Non uno, **tre**, e la terza e' quella che di solito manca:

1. minuti e tiri in porta della stagione 2025-26 nel campionato giocato
2. totali per partita del club di provenienza, per la correzione di contesto
3. media di campionato di quel torneo, per riportare il tasso su scala Serie A

La seconda e la terza non sono zelo: `v_p` e' definito **al netto del contesto di squadra** (`model_player`), quindi un tasso grezzo preso da un altro campionato non e' la stessa grandezza. Senza la correzione si sovrastima chi arriva da una squadra dominante — che e' esattamente l'errore che il contesto esiste per evitare.

**Il campionato-stagione di provenienza non e' nel repository.** `squad_2627.NEW_SIGNINGS` registra nome e ruolo e basta: la rosa e' stata ricostruita dal web senza la storia dei trasferimenti. Non viene inventato qui — la colonna lo dichiara, e va letto dal registro trasferimenti come si e' fatto per la rosa.

Esposizione di riferimento della tabella: 1800 minuti, cioe' una stagione da titolare.

| name            | role   |   minutes_proj |   quota_lambda |   rate_per90_prior_ruolo |   sot_attesi_nel_dato |   se_oggi_tetto_modello |   se_con_dati | campionato_provenienza        |
|:----------------|:-------|---------------:|---------------:|-------------------------:|----------------------:|------------------------:|--------------:|:------------------------------|
| Luis Milla      | MID    |        1131.35 |         0.0258 |                   0.3064 |                6.1286 |                  0.4082 |        0.2871 | non registrato nel repository |
| Mattia Liberali | MID    |        1131.35 |         0.0258 |                   0.3064 |                6.1286 |                  0.4082 |        0.2871 | non registrato nel repository |
| Kaiki Bruno     | DEF    |        1131.35 |         0.0111 |                   0.132  |                2.6399 |                  0.4082 |        0.3402 | non registrato nel repository |
| Fabio Rispoli   | MID    |        1131.35 |         0.0258 |                   0.3064 |                6.1286 |                  0.4082 |        0.2871 | non registrato nel repository |
| Adrian Lahdo    | MID    |        1131.35 |         0.0258 |                   0.3064 |                6.1286 |                  0.4082 |        0.2871 | non registrato nel repository |
| Andres Cuenca   | DEF    |        1131.35 |         0.0111 |                   0.132  |                2.6399 |                  0.4082 |        0.3402 | non registrato nel repository |

`se_oggi_tetto_modello` = `1/sqrt(2 tau)` = 0.4082 e' quello che il modello assegnerebbe a un giocatore senza esposizione. **Il prior pubblicato dei nuovi arrivi vale 0.3654** (`1.5 x` la dispersione fra giocatori), cioe' e' **piu' stretto** del tetto del modello, non piu' largo. Il prior chiamato "gonfiato" gonfia rispetto alla dispersione fra giocatori, non rispetto all'ignoranza: la differenza non era mai stata scritta.

### La simulazione: di quanto si stringe l'intervallo

Cambia **solo** la deviazione standard del prior dei nuovi arrivi. Ancora del livello, rapporto compositivo, seed, fonti e numero di simulazioni (200 mila per riga) restano quelli pubblicati. La griglia e' dichiarata in `data_plan.MINUTI_GRID` e `data_plan.MULT_TRASFERIMENTO`.

`mult_trasferimento` e' l'incertezza di trasporto fra campionati, come multiplo della dispersione fra giocatori. **E' parametrizzata, non stimata**: questi dati contengono un campionato solo. Lo `0.0` e' il limite ottimistico (il tasso si trasporta intatto); l'`1.0` e' il limite superiore ed e' li' apposta — se la verita' e' li', il dato individuale non aggiunge niente e il calcolo lo deve poter dire.

| stato                |   minuti |   mult_trasferimento |   sd_media_nuovi |   stagione |   q10 |   q90 |   ampiezza |   sd_stagione |   riduzione_sd |   d_stagione |
|:---------------------|---------:|---------------------:|-----------------:|-----------:|------:|------:|-----------:|--------------:|---------------:|-------------:|
| pubblicato           |      nan |                nan   |         nan      |        191 |   151 |   240 |         89 |       34.9477 |         0      |            0 |
| con dati individuali |        0 |                  0   |           0.4082 |        191 |   151 |   240 |         89 |       35.0597 |        -0.0032 |            0 |
| con dati individuali |      450 |                  0   |           0.3721 |        191 |   151 |   240 |         89 |       34.9422 |         0.0002 |            0 |
| con dati individuali |      900 |                  0   |           0.3446 |        191 |   151 |   239 |         88 |       34.8163 |         0.0038 |            0 |
| con dati individuali |     1350 |                  0   |           0.3228 |        190 |   151 |   239 |         88 |       34.7265 |         0.0063 |           -1 |
| con dati individuali |     1800 |                  0   |           0.3048 |        190 |   151 |   239 |         88 |       34.7518 |         0.0056 |           -1 |
| con dati individuali |     2400 |                  0   |           0.2851 |        190 |   151 |   238 |         87 |       34.6063 |         0.0098 |           -1 |
| con dati individuali |     3000 |                  0   |           0.2689 |        190 |   151 |   238 |         87 |       34.6008 |         0.0099 |           -1 |
| con dati individuali |        0 |                  0.5 |           0.426  |        192 |   152 |   240 |         88 |       35.1207 |        -0.005  |            1 |
| con dati individuali |      450 |                  0.5 |           0.3915 |        191 |   151 |   240 |         89 |       35.0219 |        -0.0021 |            0 |
| con dati individuali |      900 |                  0.5 |           0.3656 |        191 |   151 |   239 |         88 |       34.8689 |         0.0023 |            0 |
| con dati individuali |     1350 |                  0.5 |           0.3451 |        191 |   151 |   239 |         88 |       34.7939 |         0.0044 |            0 |
| con dati individuali |     1800 |                  0.5 |           0.3284 |        190 |   151 |   239 |         88 |       34.7715 |         0.005  |           -1 |
| con dati individuali |     2400 |                  0.5 |           0.3102 |        190 |   151 |   239 |         88 |       34.7834 |         0.0047 |           -1 |
| con dati individuali |     3000 |                  0.5 |           0.2955 |        190 |   151 |   238 |         87 |       34.6858 |         0.0075 |           -1 |
| con dati individuali |        0 |                  1   |           0.4754 |        192 |   152 |   242 |         90 |       35.3716 |        -0.0121 |            1 |
| con dati individuali |      450 |                  1   |           0.4448 |        192 |   152 |   241 |         89 |       35.1852 |        -0.0068 |            1 |
| con dati individuali |      900 |                  1   |           0.4222 |        191 |   151 |   240 |         89 |       35.1294 |        -0.0052 |            0 |
| con dati individuali |     1350 |                  1   |           0.4046 |        191 |   151 |   240 |         89 |       35.0482 |        -0.0029 |            0 |
| con dati individuali |     1800 |                  1   |           0.3905 |        191 |   151 |   240 |         89 |       34.9451 |         0.0001 |            0 |
| con dati individuali |     2400 |                  1   |           0.3754 |        191 |   151 |   240 |         89 |       34.9486 |        -0      |            0 |
| con dati individuali |     3000 |                  1   |           0.3634 |        191 |   151 |   239 |         88 |       34.9226 |         0.0007 |            0 |

Come leggerla:

- **La colonna da guardare e' `sd_stagione`, non `ampiezza`.** Il totale stagionale simulato e' un intero, quindi i suoi percentili si muovono a scalini da 1 e un effetto piu' piccolo di un tiro non e' leggibile nell'ampiezza. `ampiezza` resta in tabella perche' e' la grandezza che il README pubblica.
- **Caso migliore: 0.99% di deviazione standard**, cioe' l'IC80% passa da 89 a 87 tiri. Serve trasporto perfetto fra campionati e 3000 minuti a testa, cioe' l'angolo piu' favorevole della griglia.
- **All'estremo superiore non si stringe niente**: con `mult_trasferimento = 1.0` la riduzione va da -1.21% a +0.07%, cioe' comprende lo zero e i valori negativi. Un dato individuale che non si trasporta e' rumore in piu', non informazione.
- **Il centro si sposta quanto l'intervallo si stringe**: da 191 a 190 tiri di stagione. E' il gonfiamento di Jensen misurato in Fase 6A (+0.65% dai nuovi arrivi) che si sgonfia quando il prior si stringe. Chi raccogliesse quei dati aspettandosi un intervallo piu' stretto otterrebbe soprattutto una proiezione leggermente piu' bassa.
- **Le righe a `minuti = 0` allargano.** Sostituire il prior pubblicato (0.3654) col tetto del modello a esposizione nulla (0.4082) peggiora, ed e' il controllo che la simulazione stia facendo quello che dice: senza dati, essere onesti sull'ignoranza costa.

### La stessa cosa sulla sola fonte `new_signings`

Sul totale il guadagno e' diluito, perche' i nuovi arrivi pesano 1.4% della varianza. Accendendo la sola fonte si vede quanto vale **la fonte**, che e' la grandezza da citare per decidere se la raccolta ha senso:

| stato                |   minuti |   mult_trasferimento |   varianza_fonte |   quota_sul_totale |   riduzione_fonte |
|:---------------------|---------:|---------------------:|-----------------:|-------------------:|------------------:|
| pubblicato           |      nan |                nan   |         16.8709  |            0.01381 |           0       |
| con dati individuali |        0 |                  0   |         22.1434  |            0.01813 |          -0.31252 |
| con dati individuali |      450 |                  0   |         16.981   |            0.0139  |          -0.00652 |
| con dati individuali |      900 |                  0   |         13.7827  |            0.01128 |           0.18305 |
| con dati individuali |     1350 |                  0   |         11.6055  |            0.0095  |           0.3121  |
| con dati individuali |     1800 |                  0   |         10.0267  |            0.00821 |           0.40568 |
| con dati individuali |     2400 |                  0   |          8.49097 |            0.00695 |           0.49671 |
| con dati individuali |     3000 |                  0   |          7.36561 |            0.00603 |           0.56341 |
| con dati individuali |        0 |                  0.5 |         24.6652  |            0.0202  |          -0.46199 |
| con dati individuali |      450 |                  0.5 |         19.2874  |            0.01579 |          -0.14323 |
| con dati individuali |      900 |                  0.5 |         15.9537  |            0.01306 |           0.05436 |
| con dati individuali |     1350 |                  0.5 |         13.6836  |            0.0112  |           0.18893 |
| con dati individuali |     1800 |                  0.5 |         12.0368  |            0.00986 |           0.28654 |
| con dati individuali |     2400 |                  0.5 |         10.4345  |            0.00854 |           0.38151 |
| con dati individuali |     3000 |                  0.5 |          9.26008 |            0.00758 |           0.45112 |
| con dati individuali |        0 |                  1   |         32.8691  |            0.02691 |          -0.94827 |
| con dati individuali |      450 |                  1   |         26.7997  |            0.02194 |          -0.58851 |
| con dati individuali |      900 |                  1   |         23.0316  |            0.01886 |          -0.36516 |
| con dati individuali |     1350 |                  1   |         20.4626  |            0.01675 |          -0.21289 |
| con dati individuali |     1800 |                  1   |         18.5976  |            0.01523 |          -0.10235 |
| con dati individuali |     2400 |                  1   |         16.7816  |            0.01374 |           0.0053  |
| con dati individuali |     3000 |                  1   |         15.4496  |            0.01265 |           0.08425 |

Nel caso migliore la varianza della fonte scende da 16.9 a 7.4 (**56%**), ma la fonte vale l'1.4% del totale. Controllo d'ordine di grandezza: se le fonti fossero additive in varianza la sd totale scenderebbe a 34.81 contro i 34.60 simulati e i 34.95 pubblicati. Non coincidono perche' **le fonti interagiscono**, come gia' documentato in Fase 6A: l'approssimazione additiva vale come controllo, non come risultato.

**Conclusione operativa: D7 e' l'ultima voce della lista, non la prima.** E' il limite piu' visibile del README — sei giocatori su media di ruolo — ma sposta l'incertezza pubblicata meno di ogni altra domanda del piano. Se si raccoglie, si raccolga perche' rende la ripartizione fra giocatori piu' credibile (`fig7`), non perche' stringa l'intervallo.

---

## 4. Il blocco 6D: l'unico che vuole eventi grezzi

Quante righe servirebbero perche' il test dei predittori avesse potenza 80% contro l'alternativa dichiarata dalla Fase 6D — l'effetto per riga piu' grande che gli otto candidati abbiano mai prodotto (`poss_att` nel regime maturo). L'errore standard scala come `1/sqrt(n)`, quindi le righe crescono col quadrato del rapporto fra il `t` che serve e quello che si ha. `righe_per_stagione` e' quante ne produce **una** stagione di Serie A in quel regime.

| regime           |   righe_per_stagione |   t_ora |   potenza_ora |   righe_servite |   stagioni_campionato |
|:-----------------|---------------------:|--------:|--------------:|----------------:|----------------------:|
| maturo           |                  660 |  1.4201 |        0.281  |        2642.72  |                4.0041 |
| acerbo           |                  100 |  0.7722 |        0.1098 |        1354.11  |               13.5411 |
| acerbo disgiunto |                   40 |  1.1295 |        0.192  |         253.153 |                6.3288 |

- **`t_ora` riproduce esattamente il `t` di Fase 6D** (1.4201 contro 1.4201 nel regime maturo). Non e' un controllo indipendente — e' lo stesso rapporto `d_riga / se_riga`, ricalcolato dalle stesse colonne — ma conferma che il conto delle righe parte dalla parametrizzazione che la Fase 6D ha davvero usato, e non da una reinterpretazione dei suoi numeri.
- **Il regime acerbo, che e' quello dell'ipotesi da testare, chiede 13.5 stagioni-campionato** di eventi grezzi. Possono essere campionati diversi nello stesso anno — 3 stagioni per 5 campionati vanno bene quanto 14 anni di Serie A.
- **Ma non servono stagioni intere, e questo cambia il conto.** Il regime acerbo vive sulle prime 8 giornate: ne bastano ~10 per campionato-stagione, contando le 30 partite che `date_splits` pretende come storia, cioe' 1354 partite invece di 1522. A ~2.6 MB per partita fanno **3.6 GB contro 4.0 GB** del regime maturo, che di stagioni intere ha bisogno. I due sono dello stesso ordine, e sopra a entrambi vanno comunque ricalcolati field tilt, PPDA, tocchi in area e xG interno, che nessun fornitore pubblica come totali.
- **E' l'unica domanda del piano che richiede eventi**, ed e' anche quella con il valore atteso piu' basso: tre regimi, otto candidati, nessuno che passi, e un test in campione — il piu' favorevole concepibile — che non rifiuta. Il piano la mette per ultima e la motivazione e' questa, non il costo.
- **Attenzione all'assunzione**: il conto suppone che la variabilita' per riga resti quella misurata, mentre la Fase 6D ha trovato che nel regime acerbo e' **piu' piccola** (MDE x1.8 contro un x2.6 giustificato dalle sole righe perse). Vale come ordine di grandezza.

---

## 5. In che ordine

Non e' una classifica di importanza scientifica: e' tiri in porta di incertezza spostati per unita' di dato raccolto.

| ordine | domande | granularita' | perche' prima |
|---|---|---|---|
| 1 | D1, D2, D5 | G1, totali di squadra per stagione | sono le tre che toccano il **livello**, cioe' l'unica cosa che sposta la proiezione (Fase 6A), e stanno tutte sulla granularita' piu' grossolana. D1 vale 19 tiri, D5 ne vale 9, D2 e' la verifica dell'ancora da cui dipende tutto |
| 2 | D3, D6 | G2, totali di squadra per partita | un livello di granularita' in piu' per due domande piu' piccole: la misura della de-compressione (6 tiri) e il segno della congestione, che oggi manca del tutto |
| 3 | D4 | G3, tassi per 90 per giocatore | valida l'estimatore **pubblicato**, che non e' mai stato validato: costa una stagione di dati per giocatore per ogni transizione, e ne servono 4-5 |
| 4 | D7 | G3, tassi per 90 per giocatore | il limite piu' visibile e il guadagno piu' piccolo, quantificato nella sezione 3 |
| 5 | D8 | G4, eventi grezzi | l'unica che richiede eventi, la piu' cara, e l'unica il cui esito e' gia' stato misurato tre volte |

---

## Limiti di questo blocco

- **E' un piano, non un risultato.** Le uniche cifre calcolate qui sono quelle della sezione 3 e il conto delle righe della sezione 4; tutto il resto e' un inventario di cio' che i blocchi 6A-6E hanno gia' trovato.
- **L'incertezza di trasferimento fra campionati non e' stimata.** E' una griglia dichiarata, e il caso migliore della sezione 3 e' il suo estremo ottimistico: va citato come limite superiore del guadagno, non come previsione.
- **La simulazione tiene ferma la rosa.** Il mercato chiude il 1 settembre 2026 e la rosa cambiera': se cambiano i nuovi arrivi cambia anche quanto varrebbe conoscerli.
- **Il campionato di provenienza dei sei nuovi arrivi non e' nel repository** e non e' stato ipotizzato. Senza quello, la sezione 3 dice quanto varrebbe il dato, non dove prenderlo.
- **Le ampiezze richieste (10+ stagioni, 4-5 transizioni) sono ordini di grandezza**, non calcoli di potenza. L'unico conto di potenza vero e' quello della sezione 4, che riguarda il blocco 6D.
- `tau` = 3, `alpha` = 12.0 e `r` = 26.0 sono quelli delle fasi precedenti, non ristimati qui.