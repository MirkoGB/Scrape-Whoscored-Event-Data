# Fase 6E — il calendario 2026-27 non e' quello 2025-26

La proiezione parla del Como contro "una difesa media". Nel 2026-27 tre promosse sostituiscono tre retrocesse, e delle promosse questi dati non sanno niente. Prima di stimare qualunque cosa: **che cosa fa il codice oggi?**

## Esito in breve

1. **Il codice contiene tutte e due le convenzioni, e nessuna delle due entra nel livello pubblicato.** `ratings_per_campo` usa l'avversario medio (e' `fig5`), `como_context` usa l'insieme reale 2025-26 — ma dalla Fase 6A sappiamo che il contesto di squadra si semplifica dentro `monte_carlo`. L'insieme di avversari entra per una terza via, implicita: `rho` ancora il livello al **tasso grezzo del Como 2025-26**, che e' un numero ottenuto contro l'insieme 2025-26. **Il calendario 2026-27 non compare in nessun punto del codice.**
2. **Lo status quo non e' "avversario medio": e' "le promosse difendono come le retrocesse"**, e sotto quell'ipotesi il fattore di calendario vale 1 esattamente. Le tre retrocesse (Cremonese, Verona, Pisa) hanno concesso in media 4.693 tiri in porta a partita contro 4.034 di campionato: **il trio che esce e' gia' fra i piu' battuti**, quindi il segno dell'effetto non e' nemmeno determinato.
3. **L'intervallo dichiarato sposta la proiezione fra 186 e 195 tiri di stagione** (fattore da 0.9745 a 1.0180), contro i 191 pubblicati e un intervallo di credibilita' largo 89. E' 10% di quell'ampiezza, e meno della meta' di quanto vale la griglia di `rho` (19 tiri). Il riferimento empirico — l'unica coorte di neopromosse osservabile, quella del 2025-26 — vale 192-193.
4. **Nessuna correzione e' stata applicata**, e non per prudenza: sarebbe un doppio conteggio. 4.90 esce da un modello di persistenza su 21 stagioni, e in 21 stagioni ci sono 21 ricambi di neopromosse — quel livello contiene gia' un calendario che cambia tre squadre l'anno. La correzione legittima sarebbe solo lo scarto fra il trio 2026-27 e un trio *tipico*, e con una coorte sola un trio tipico non e' caratterizzabile.
5. **La congestione infrasettimanale e' un limite, non un numero.** Oggi la Champions e' modellata solo sui minuti; l'effetto sul lambda di squadra manca del tutto. Non e' stimato qui — il Como 2025-26 non giocava le coppe, quindi il campione non contiene una sola sua partita congestionata — e il segno atteso e' **negativo**: su questo asse la proiezione e' ottimistica.

---

## 1. Quale insieme di avversari usa il codice

| modulo | funzione | insieme | dove finisce |
|---|---|---|---|
| `sot/level_chain.py` | `ratings_per_campo` | avversario medio (media dei 20 coefficienti di difesa) | fig5 e phase5_ratings.csv; NON entra nel livello pubblicato |
| `sot/project_2627.py` | `como_context` | insieme reale 2025-26 (le 38 righe vere del Como) | summary['context_como']; si semplifica nel Monte Carlo (Fase 6A) |
| `sot/model_team.py` | `TeamModel.predict` | insieme reale, avversario per avversario | walk-forward within-season; non riguarda il 2026-27 |
| `sot/level_chain.py` | `rho_implicito / livello_da_rho` | insieme reale 2025-26, implicito nel tasso grezzo del Como | QUI l'insieme di avversari entra davvero nel livello pubblicato |
| `sot/project_2627.py` | `monte_carlo` | nessuno: l'ancora e' il riferimento esterno 4.90 | il calendario 2026-27 non compare in nessun punto del codice |

Le prime due righe sono le due convenzioni possibili, entrambe presenti. La quarta e' quella che conta davvero, ed e' la meno visibile: nessuno sceglie un insieme di avversari, ma il livello e' ancorato a un tasso grezzo che quell'insieme lo ha gia' incorporato. La quinta e' il fatto negativo del blocco — **non esiste, in nessun modulo, il calendario 2026-27**.

---

## 2. Chi esce e chi entra

Le tre retrocesse si ricavano dai dati (punti dai gol delle righe partita, nessuna informazione esterna). Ultime sei posizioni:

|   posizione | team      |   punti |   gf |   gs |   dr |
|------------:|:----------|--------:|-----:|-----:|-----:|
|          15 | Torino    |      43 |   42 |   63 |  -21 |
|          16 | Genoa     |      42 |   41 |   49 |   -8 |
|          17 | Lecce     |      39 |   28 |   49 |  -21 |
|          18 | Cremonese |      34 |   32 |   55 |  -23 |
|          19 | Verona    |      25 |   24 |   57 |  -33 |
|          20 | Pisa      |      17 |   25 |   70 |  -45 |

Retrocedono **Cremonese, Verona, Pisa**. Nessuna coppia in zona retrocessione e' a pari punti, quindi l'ordinamento non dipende dai criteri di spareggio.

Chi entra non e' deducibile da questi dati: la Serie B non e' nel repository. Quello che serve non e' comunque l'identita' delle promosse ma il loro **livello difensivo**, che e' la grandezza su cui si dichiara l'intervallo.

### I livelli difensivi delle venti squadre 2025-26

Due scale affiancate, e nessuna delle due e' la risposta da sola: i coefficienti del modello sono quelli che entrano davvero nel lambda ma la ridge li comprime (pendenza 0.760 sui livelli, Fase 6A), quindi **sottostimano** qualunque ricambio; i tiri concessi grezzi non sono compressi ma dentro hanno anche chi la squadra ha affrontato.

| team              |   modello |   grezzo |
|:------------------|----------:|---------:|
| Juventus          |    0.791  |   2.8158 |
| Inter             |    0.8164 |   2.9211 |
| Napoli            |    0.8447 |   3.0263 |
| Como              |    0.8006 |   3.1053 |
| Roma              |    0.929  |   3.6316 |
| AC Milan          |    0.9759 |   3.6842 |
| Bologna           |    0.928  |   3.7105 |
| Udinese           |    0.9791 |   3.8947 |
| Atalanta          |    1.0137 |   4      |
| Lazio             |    1.0343 |   4.2105 |
| Verona            |    1.0353 |   4.2105 |
| Lecce             |    1.0377 |   4.2632 |
| Genoa             |    1.0491 |   4.2632 |
| Parma Calcio 1913 |    1.048  |   4.3158 |
| Torino            |    1.123  |   4.5263 |
| Cagliari          |    1.095  |   4.6316 |
| Fiorentina        |    1.1275 |   4.6579 |
| Pisa              |    1.1508 |   4.7105 |
| Sassuolo          |    1.1754 |   4.9474 |
| Cremonese         |    1.197  |   5.1579 |

---

## 3. Quanto vale il ricambio

Il Como affronta 19 avversari, ciascuno una volta in casa e una in trasferta. La difesa entra moltiplicativamente nel lambda, quindi il fattore di calendario e' un rapporto fra somme:

```
F = [ somma sui 16 che restano + 3 x c_promossa ] / [ somma sui 19 del 25-26 ]
```

Il termine di campo compare identico sopra e sotto e si semplifica: `F` non dipende dalla scala di campo, e un test lo verifica. Gli scenari sono dichiarati in anticipo (`calendar_2627.SCENARI`): i primi due sono gli **estremi dell'intervallo**, il terzo lo status quo, il quarto un riferimento empirico.

| scala   | scenario                |   c_promossa |   fattore |   livello_implicato |   stagione |   q10 |   q90 |   equiv_rho |
|:--------|:------------------------|-------------:|----------:|--------------------:|-----------:|------:|------:|------------:|
| modello | media di campionato     |       1.0076 |    0.9814 |              4.8088 |        188 |   149 |   235 |     -0.0852 |
| modello | peggiore difesa 2025-26 |       1.197  |    1.0108 |              4.9527 |        193 |   153 |   242 |      0.0492 |
| modello | come le retrocesse      |       1.1277 |    1      |              4.9    |        191 |   151 |   240 |      0      |
| modello | coorte promossa 2025-26 |       1.1744 |    1.0072 |              4.9355 |        192 |   152 |   242 |      0.0331 |
| grezzo  | media di campionato     |       4.0342 |    0.9745 |              4.7752 |        186 |   147 |   233 |     -0.1165 |
| grezzo  | peggiore difesa 2025-26 |       5.1579 |    1.018  |              4.9881 |        195 |   154 |   244 |      0.0822 |
| grezzo  | come le retrocesse      |       4.693  |    1      |              4.9    |        191 |   151 |   240 |      0      |
| grezzo  | coorte promossa 2025-26 |       4.9386 |    1.0095 |              4.9465 |        193 |   153 |   242 |      0.0435 |

Come leggerla:

- **`come le retrocesse` da' fattore 1.0000 per costruzione**, ed e' l'ipotesi che il codice fa oggi senza dichiararla. Non e' un'ipotesi neutra: e' l'ipotesi che le promosse siano porose quanto le tre squadre peggiori del campionato precedente. Le sue due righe riproducono esattamente la proiezione pubblicata (191, [151, 240]): e' il controllo che il resto della tabella esca dalla stessa macchina e non da un calcolo parallelo.
- **`media di campionato` e' l'unico scenario che abbassa la proiezione**, e lo fa perche' assume promosse forti come una squadra qualunque di Serie A. Storicamente le neopromosse stanno sotto la media, quindi e' un limite dell'intervallo, non uno scenario plausibile.
- **Il riferimento empirico sta dalla parte opposta**: la coorte promossa nel 2025-26 (Sassuolo, Pisa, Cremonese) ha concesso piu' delle retrocesse, quindi il fattore sale sopra 1. **E' una coorte sola** e la sua identita' e' informazione esterna, dichiarata in `PROMOSSE_2526`: non e' una stima di come difenderanno le promosse del 2026-27.
- **La scala grezza da' sempre un effetto piu' grande di quella del modello**, in tutti e quattro gli scenari. E' la compressione della ridge vista da un'altra angolazione: gli stessi coefficienti che schiacciano le squadre di vertice verso la media schiacciano anche le difese peggiori, e quindi riducono lo scarto fra chi esce e chi entra.
- **L'ultima colonna mette il calendario sulla scala di `rho`**: l'intero intervallo vale 0.199 di `rho`, contro i 0.45 della griglia dichiarata in Fase 6C. **Il calendario e' la piu' piccola delle assunzioni non stimabili del progetto**, non la piu' grande.

---

## 4. Perche' il numero pubblicato non e' stato corretto

Non per prudenza: **sarebbe un doppio conteggio**. Il livello 4.90 esce da un modello di persistenza su 21 stagioni (`config.py`), e in 21 stagioni ci sono 21 ricambi di neopromosse: quella media storica contiene gia' un calendario che cambia tre squadre l'anno. L'unica correzione legittima sarebbe lo scarto fra il trio 2026-27 e un trio **tipico** — e per caratterizzare un trio tipico serve piu' di una coorte, che e' esattamente quello che qui manca.

`effetto_su_proiezione` esiste per quantificare il limite e **non e' chiamata da nessuno script della proiezione**: `run_phase3.py` e `run_phase5.py` continuano a stampare 191 tiri di stagione, IC80% [151, 240].

---

## 5. La congestione infrasettimanale: limite, non numero

| voce | contenuto |
|---|---|
| che_cosa | congestione da impegni infrasettimanali (Champions League) |
| cosa_e_modellato_oggi | solo i minuti: ROTATION_DEFAULT 0.15, variato 0.05-0.25 nel Monte Carlo |
| cosa_manca | l'effetto sul lambda di squadra, che agisce anche a parita' di undici schierato (recupero incompleto, gestione del ritmo, meno transizioni ad alta intensita') |
| segno_atteso | -1 |
| lettura | la proiezione, su questo asse, e' ottimistica |
| stimabile_da_questi_dati | False |
| perche_no | il Como 2025-26 non giocava le coppe: zero partite congestionate |
| dove_entrerebbe | un fattore moltiplicativo sull'ancora del livello, cioe' lo stesso ingresso di rho (Fase 6A/6C) |

La rotazione per la Champions e' modellata sui **minuti** — chi scende in campo, con `ROTATION_DEFAULT` 0.15 variato fra 0.05 e 0.25 nel Monte Carlo. Ma la congestione agisce anche a **parita' di undici schierato**: recupero incompleto, gestione del ritmo, meno transizioni ad alta intensita'. Quell'effetto oggi nel modello non c'e' per niente.

**Non e' stimato qui, ed e' una scelta dichiarata**: il Como 2025-26 non giocava le coppe europee, quindi in questo campione non esiste una sola partita del Como dopo un turno infrasettimanale. Stimarlo dalle altre squadre italiane impegnate in Europa e' un'altra domanda, con un altro disegno, e va al piano dati (blocco 6F) — non a questo blocco.

**Il segno atteso e' negativo**: a parita' di tutto il resto una squadra che gioca infrasettimanale produce meno, non di piu'. Quindi la proiezione, su questo asse, e' **ottimistica**. Se un giorno il fattore venisse stimato entrerebbe come moltiplicatore sull'ancora del livello, cioe' dallo stesso ingresso di `rho`: e' l'unico punto da cui il livello si muove (Fase 6A).

---

## Limiti di questo blocco

- **L'intervallo sulle promosse e' dichiarato, non stimato.** I due estremi sono calcolati da questi dati ma *scelti* come estremi: nessuno dei due e' escluso, e nessuno dei due ha una probabilita' attaccata.
- **Il riferimento empirico e' una coorte sola.** Tre squadre, una stagione, e la loro identita' e' informazione esterna al repository.
- **Il fattore assume che l'attacco del Como non cambi** in funzione dell'avversario oltre a quanto il modello moltiplicativo prevede: nessuna interazione fra forza dell'attacco e forza della difesa e' stimata, e con una stagione sola non sarebbe identificabile.
- **La scala del modello e' compressa.** La colonna `modello` sottostima il ricambio di un fattore che la Fase 6A ha misurato sui livelli d'attacco (pendenza 0.760) ma **non** sulle difese: qui non e' stata rimisurata, e il divario fra le due scale va letto come un intervallo, non come un errore dell'una o dell'altra.
- `tau` = 3, `alpha` = 12.0, `r` = 26.0 e `rho` = 0.808 sono quelli delle fasi precedenti, non ristimati qui.