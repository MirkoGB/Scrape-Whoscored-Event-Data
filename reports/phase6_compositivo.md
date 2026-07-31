# Fase 6B — il test giusto per il bottom-up compositivo

Fino alla Fase 5 "dal basso" era un nome solo per due stimatori diversi, e il test di mezza stagione bocciava quello che la proiezione **non** usa. Qui i due sono separati nel codice (`project_2627.stima_livello_dai_giocatori` e `project_2627.stima_compositiva`) e testati ciascuno contro il proprio baseline. **Nessun numero pubblicato cambia**: il rapporto compositivo resta 1.0101 e la proiezione resta quella della Fase 3.

## Esito in breve

1. **Il risultato negativo della Fase 3 resta, e resta dov'era**: l'estimatore A (livello deciso dai giocatori) fa MAE 0.4823 contro 0.4158 del tasso di squadra, differenza appaiata -0.0665 (t = -1.33). Nessuna correzione: era gia' il risultato giusto sull'estimatore sbagliato.
2. **L'estimatore B non e' mai stato validato, e questo test non lo valida.** MAE 0.4154 contro 0.4158 del suo baseline corretto ("nessun aggiustamento di rosa", cioe' rapporto identicamente 1.0): differenza +0.0004, t = +0.03. **Non e' una conferma: e' mancanza di potenza**, e il punto 3 dice quanta.
3. **Il test di B e' quasi vuoto per costruzione.** L'effetto minimo rilevabile su questo confronto vale 0.0394 di MAE; l'aggiustamento compositivo sposta le previsioni di 0.0414 in media (massimo 0.2007). Il guadagno massimo **concepibile** — ogni aggiustamento nel verso giusto e per intero — vale quindi 0.0414, cioe' 1.05 volte la soglia. Perche' il test distinguesse B dal proprio baseline, l'aggiustamento dovrebbe essere praticamente perfetto: a qualunque efficacia parziale il test e' cieco.
4. **Perche' e' vuoto**: fra i due tempi di una stessa stagione la rosa quasi non cambia. Si libera in media il 3.9% dei minuti (mediana 3.0%), contro il 16.9% che cambia fra un'estate e l'altra nel caso Como. I rapporti restano fra 0.9838 e 1.0450.

---

## 1. I due estimatori

| | chi decide il livello | chi decide la ripartizione | dove sta |
|---|---|---|---|
| **A — livello dai giocatori** | i giocatori | i giocatori | `stima_livello_dai_giocatori` |
| **B — compositivo** | l'ancora dall'alto (4.90) | i giocatori, via rapporto di rosa | `stima_compositiva` |

La differenza non e' di sfumatura: B e' **invariante** rispetto al contesto di squadra (compare a numeratore e denominatore del rapporto e si semplifica), A no. E' la stessa invarianza dimostrata in Fase 6A sul numero pubblicato, e un test la verifica su entrambi.

Baseline corretto per ciascuno:

- **A** fissa un livello, quindi va confrontato con un altro livello: il tasso di squadra del primo tempo.
- **B** non fissa nessun livello: prende quello dall'alto e lo moltiplica per il rapporto di rosa. Il suo baseline e' **lo stesso livello con rapporto identicamente 1.0**, cioe' "nessun aggiustamento di rosa". Nel test di mezza stagione il livello dall'alto e' il tasso di squadra del primo tempo, quindi le due colonne di baseline coincidono numericamente — ma la domanda che pongono e' diversa.

---

## 2. Il test 1o/2o tempo su entrambi

Stima sulle prime 19 partite di ogni squadra, previsione della media di tiri in porta delle 19 successive. 20 squadre.

| stimatore                                               |    MAE |   RMSE |   bias |     corr |
|:--------------------------------------------------------|-------:|-------:|-------:|---------:|
| nessun aggiustamento di rosa (= media squadra 1o tempo) | 0.4158 | 0.561  | 0.0526 |   0.8386 |
| A — livello dai giocatori                               | 0.4823 | 0.6163 | 0.0466 |   0.7979 |
| B — compositivo (quello pubblicato)                     | 0.4154 | 0.5599 | 0.0788 |   0.8418 |
| baseline: media di campionato                           | 0.8216 | 1.0206 | 0.0526 | nan      |

Confronti appaiati, con l'effetto minimo che il test potrebbe distinguere (potenza 80%, alpha 5%):

| confronto                                   |   d MAE |       t |   sd differenze |   MDE 80% |
|:--------------------------------------------|--------:|--------:|----------------:|----------:|
| A contro il suo baseline (media squadra)    | -0.0665 | -1.3287 |          0.2238 |    0.1478 |
| B contro il suo baseline (rapporto = 1.0)   |  0.0004 |  0.0321 |          0.0596 |    0.0394 |
| baseline di squadra contro media campionato |  0.4058 |  2.6388 |          0.6877 |    0.4542 |

Sul confronto che conta per la proiezione — la riga B — la differenza osservata (+0.0004) e' 1% dell'effetto minimo rilevabile (0.0394). Un t di +0.03 qui non significa "il metodo non funziona" e nemmeno "funziona": significa che questo test non e' in grado di vederlo.

### Dettaglio per squadra

| team              |   topdown |   livello_dai_giocatori |   compositivo |   rapporto |   actual_h2 |
|:------------------|----------:|------------------------:|--------------:|-----------:|------------:|
| AC Milan          |    4.7895 |                  4.698  |        4.7774 |     0.9975 |      3.9474 |
| Atalanta          |    4.2632 |                  4.5114 |        4.2598 |     0.9992 |      4.9474 |
| Bologna           |    4.1053 |                  3.7192 |        4.0998 |     0.9987 |      3.5263 |
| Cagliari          |    3.4737 |                  3.2246 |        3.4891 |     1.0044 |      3.4737 |
| Como              |    4.8947 |                  4.3595 |        4.8954 |     1.0001 |      5.3158 |
| Cremonese         |    3.2105 |                  3.2608 |        3.1722 |     0.9881 |      3.3684 |
| Fiorentina        |    3.4211 |                  3.7081 |        3.5749 |     1.045  |      3.4737 |
| Genoa             |    3.8421 |                  3.7427 |        3.8459 |     1.001  |      3.6842 |
| Inter             |    5.7895 |                  5.491  |        5.7991 |     1.0017 |      6.2632 |
| Juventus          |    5.6842 |                  5.4823 |        5.8849 |     1.0353 |      6.2632 |
| Lazio             |    4.1579 |                  4.2766 |        4.0906 |     0.9838 |      4      |
| Lecce             |    2.5789 |                  2.4196 |        2.5924 |     1.0052 |      2.5263 |
| Napoli            |    4.7368 |                  4.572  |        4.7882 |     1.0108 |      4.6842 |
| Parma Calcio 1913 |    2.8947 |                  3.2424 |        2.9814 |     1.0299 |      2.5789 |
| Pisa              |    2.2632 |                  2.567  |        2.2666 |     1.0015 |      3.3158 |
| Roma              |    4.7895 |                  4.9527 |        4.8095 |     1.0042 |      4.5789 |
| Sassuolo          |    3.6842 |                  3.9755 |        3.7503 |     1.0179 |      3.7895 |
| Torino            |    4.5789 |                  4.7258 |        4.6293 |     1.011  |      3.3684 |
| Udinese           |    3.7895 |                  3.8076 |        3.7642 |     0.9933 |      3.8947 |
| Verona            |    4.2632 |                  4.353  |        4.2633 |     1      |      3.1579 |

---

## 3. Quanto ricambio c'e' davvero fra i due tempi

| team              |   usciti |   nuovi |   minuti_liberati |   quota_liberata |
|:------------------|---------:|--------:|------------------:|-----------------:|
| Fiorentina        |        9 |       7 |              2394 |           0.1265 |
| Lazio             |        2 |       4 |              2319 |           0.1245 |
| Pisa              |        6 |       6 |              2075 |           0.1122 |
| Torino            |        3 |       5 |              1511 |           0.081  |
| Lecce             |        5 |       4 |              1264 |           0.0678 |
| Genoa             |        5 |       8 |               829 |           0.0444 |
| Sassuolo          |        4 |       8 |               740 |           0.0395 |
| Roma              |        2 |       5 |               662 |           0.0354 |
| Parma Calcio 1913 |        3 |       6 |               617 |           0.0331 |
| Juventus          |        3 |       3 |               607 |           0.0325 |
| Atalanta          |        2 |       3 |               518 |           0.0281 |
| Cremonese         |        3 |       5 |               230 |           0.0122 |
| AC Milan          |        4 |       0 |               192 |           0.0103 |
| Napoli            |        2 |       4 |               192 |           0.0102 |
| Udinese           |        1 |       3 |               136 |           0.0073 |
| Cagliari          |        2 |       5 |               134 |           0.0072 |
| Inter             |        2 |       4 |               104 |           0.0056 |
| Bologna           |        1 |       3 |                61 |           0.0033 |
| Verona            |        2 |       8 |                26 |           0.0014 |
| Como              |        1 |       0 |                 4 |           0.0002 |

Media 3.9%, mediana 3.0%, massimo 12.6% (Fiorentina). Il Como e' il caso limite in senso opposto: 0.02% dei minuti liberati, cioe' la sua riga del test non contiene alcuna informazione sull'estimatore compositivo — ed e' proprio la squadra che la proiezione riguarda.

Nel passaggio vero, 2025-26 -> 2026-27, se ne liberano 16.9%: un ordine di grandezza diverso. Il test sottopone l'estimatore a una perturbazione che e' una frazione di quella su cui poi lo si usa.

---

## 4. Cosa questo test puo' e non puo' dire

**Puo' dire** che fissare il livello dai giocatori peggiora la previsione: l'estimatore A perde contro il tasso di squadra, il segno e' stabile e la causa (doppia compressione, danno concentrato sulle squadre di vertice) e' documentata in Fase 3 e confermata come pendenza in Fase 6A.

**Non puo' dire** se l'aggiustamento compositivo aggiunga o tolga qualcosa. Tre ragioni, tutte strutturali e nessuna risolvibile con questi dati:

1. **Non c'e' ricambio di rosa vero** fra i due tempi di una stessa stagione: la sessione di gennaio muove una frazione dei minuti che cambiano fra un'estate e l'altra.
2. **Venti righe**, una per squadra, e non indipendenti fra loro (la stessa partita compare in due righe con segni opposti sul calendario).
3. **La rosa del secondo tempo e' nota al test.** Per proiettare i minuti bisogna sapere chi c'e': si usa la composizione reale della rosa del secondo tempo — identita' e ruolo, mai tiri o minuti. E' l'analogo della proiezione vera, dove la rosa 2026-27 e' nota, ma resta informazione che viene dal periodo bersaglio e **favorisce** l'estimatore B. Anche cosi' favorito non si distingue dal baseline.

Se un domani qualcuno leggesse `t = +0.03` come "il metodo compositivo e' convalidato", starebbe leggendo rumore. La riga da citare e' l'altra: MDE 0.0394 contro un intervento medio di 0.0414, cioe' un test che vedrebbe qualcosa solo se l'aggiustamento fosse perfetto.

---

## Limiti di questo blocco

- `tau` = 3 e la scelta di `alpha` = 12.0 sono quelli delle fasi precedenti: questo blocco non ristima niente.
- La rotazione nella proiezione dei minuti del secondo tempo e' posta a **zero**: dentro la stagione non c'e' l'analogo della rotazione Champions. Nella proiezione vera vale 0.15, fatta variare fra 0.05 e 0.25.
- Il rapporto compositivo del test usa **una riga per giocatore** su entrambi i lati (ruolo in cui ha giocato piu' minuti), altrimenti il quoziente conterrebbe anche la differenza di convenzione. L'estimatore A resta sulla convenzione precedente, per non spostare un numero gia' pubblicato.
- **Una sola stagione**: il test e' interno alla stagione e la persistenza dentro la stagione e' piu' alta di quella fra stagioni. Vale per il livello (blocco 6C) come per il rapporto.