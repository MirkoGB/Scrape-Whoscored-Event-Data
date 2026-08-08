# Fase 10 / Blocco R2 — 1X2 e over/under, valutati

> Generato da `scripts/run_fase10_r2.py` il 2026-08-08.
> **Nessuna richiesta di rete. Nessun parametro nuovo**: `rho = 0` arriva da R1,
> i lambda da E3.1. Questo blocco misura.

---

## 0. Due decisioni ereditate, dichiarate qui

1. **Il burn-in NON e' stato allineato alla giornata.** R0 aveva trovato due
   partite con un lato solo eligible (Inter-Atalanta e Sassuolo-Salernitana,
   2021-22) e lasciato aperta la scelta. `[DECISO 2026-08-08]` dall'utente:
   **restano fuori**. Due partite su 1638 non giustificano il rischio di
   spostare una definizione che E3 ha gia' pubblicato.
2. **`rho = 0`**, dall'esito misurato di R1 e non come default comodo: MLE
   −0,0087 con potenza dell'80% a 0,09.

> **Vincolo 3, e non e' aggirabile.** Qui non si valuta nessuna scommessa. Non
> ci sono quote di mercato nel repository, e le uniche ottenibili sarebbero
> generate da questo stesso modello: confrontarcisi e' circolare, ed e' il codice
> che sta in `legacy/`. Si misura **quanto la previsione e' buona**, non quanto
> varrebbe puntarci. Un test vieta che una quota compaia in `sot/esiti.py`.

---

## 1. Come si misura, e perche' cosi'

**La metrica principale e' l'RPS, non la log-loss.** L'esito 1X2 e' **ordinale**:
fra `1` e `2` c'e' `X`, e sbagliare dando probabilita' al pareggio e' un errore
piu' piccolo che darla alla vittoria opposta. La log-loss tratta le tre classi
come etichette scambiabili e non lo sa; sta accanto, non al posto.

**Il confronto e' a composizione fissata** (vincolo 6): ogni baseline e' una
coppia di lambda e viene composta con la **stessa** `risultato.congiunta` del
modello. Se il modello passasse per la congiunta e i baseline per una regola
diversa, si misurerebbe la composizione invece del lambda.

**Il pavimento sui lambda e' dichiarato** (`PAVIMENTO_LAMBDA` = 0.05).
Un lambda esattamente zero e' un estimatore **degenere**: su una riga del
campione `media squadra` lo produce **mentre quella squadra segna davvero**, e
senza pavimento la log-loss di quel baseline sarebbe infinita — un artefatto, non
un risultato. E' lo stesso caso della frequenza storica grezza di E3 e si tratta
allo stesso modo: si smorza, si dichiara, si conta quante righe tocca.

| candidato | righe_pavimentate |
|---|---:|
| media campionato | 0 |
| media casa/trasferta | 0 |
| media squadra | 1 |
| media squadra + campo | 0 |
| modello | 0 |

**Un difetto trovato e corretto prima di pubblicare**: il tasso base dell'over
era stimato sull'**intero campione** mentre quello 1X2 era gia' walk-forward.
Dava a ogni partita la conoscenza di quanti gol si sarebbero segnati nel resto
della stagione — vincolo 1. Ora entrambi usano il solo passato, con la stessa
soglia di 30 partite del walk-forward di E3.

---

## 2. Il quadro completo

| candidato | RPS | log-loss | Brier O1.5 | Brier O2.5 | Brier O3.5 |
|---|---:|---:|---:|---:|---:|
| modello | 0.2041 | 1.0081 | 0.1962 | 0.2529 | 0.1924 |
| media campionato | 0.2322 | 1.0888 | 0.1926 | 0.2509 | 0.1915 |
| media casa/trasferta | 0.2316 | 1.0874 | 0.1926 | 0.2509 | 0.1915 |
| media squadra | 0.2067 | 1.0161 | 0.2065 | 0.2672 | 0.2009 |
| media squadra + campo | 0.2057 | 1.0141 | 0.2065 | 0.2672 | 0.2009 |
| tasso base 1X2 | 0.2328 | 1.0954 | 0.1995 | 0.2513 | 0.1946 |

Su **tutte** le metriche piu' basso e' meglio.

---

## 3. Su 1X2 il modello batte l'ignoranza, non batte la forza di squadra

| baseline | differenza | errore standard | t | MDE (80%) | modello vince | oltre il rumore |
|---|---:|---:|---:|---:|---:|---:|
| media campionato | -0.02808 | 0.00271 | -10.37 | 0.00759 | si | si |
| media casa/trasferta | -0.02753 | 0.00256 | -10.75 | 0.00718 | si | si |
| media squadra | -0.00262 | 0.00188 | -1.39 | 0.00528 | si | no |
| media squadra + campo | -0.00166 | 0.00151 | -1.10 | 0.00424 | si | no |
| tasso base 1X2 | -0.02874 | 0.00265 | -10.86 | 0.00741 | si | si |

- Contro i tre candidati non informativi il margine e' **enorme e ben oltre il
  rumore**: t fra −10,4 e −10,9.
- Contro **`media squadra + campo`** — «quanti gol fa in media questa squadra, e
  gioca in casa?» — il margine vale **t = -1.10**,
  con una differenza di -0.00166
  contro un MDE di 0.00424:
  **dentro il rumore.**

**E' esattamente la forma che le Fasi 2 e 4 avevano trovato sui tiri in porta**
(t = 1,86 sullo stesso confronto), e va detto perche' e' un contrasto con E3: li'
il modello dei gol batteva il baseline migliore per **t = 5,52**. **Il vantaggio
misurato sui gol non sopravvive alla proiezione su 1X2**, e le cause sono due e
si sommano: le righe passano da 3.278 a 1,638 (una partita, non due
squadre-partita), e l'esito a tre classi **butta via** informazione che i gol
avevano — 3-0 e 1-0 sono lo stesso `1`.

La log-loss dice la stessa cosa con numeri diversi
(t = -1.09
contro lo stesso baseline), il che e' un controllo: se le due metriche avessero
dato verdetti opposti, ci sarebbe da spiegare quale delle due si stava leggendo.

---

## 4. Su over/under l'ordine si ROVESCIA, ed e' il risultato non previsto

| baseline | differenza | errore standard | t | MDE (80%) | modello vince | oltre il rumore |
|---|---:|---:|---:|---:|---:|---:|
| media campionato | 0.00192 | 0.00214 | 0.90 | 0.00599 | no | no |
| media casa/trasferta | 0.00192 | 0.00214 | 0.90 | 0.00599 | no | no |
| media squadra | -0.01433 | 0.00327 | -4.38 | 0.00917 | si | si |
| media squadra + campo | -0.01432 | 0.00327 | -4.38 | 0.00916 | si | si |
| tasso base 1X2 | 0.00159 | 0.00236 | 0.68 | 0.00661 | no | no |

**Sui gol totali il modello perde contro la media di campionato**
(t = +0.90, sotto il proprio MDE quindi non
distinguibile) **e batte nettamente i baseline di squadra**
(t = -4.38, ben oltre il rumore). Sul
1X2 valeva l'opposto: li' i baseline di squadra erano forti e la media di
campionato inutile.

**Il meccanismo e' misurato, non addotto.** Un esito 1X2 dipende dalla
**differenza** fra i due lambda — chi e' piu' forte — mentre un over/under
dipende dalla loro **somma**. Ecco come i candidati trattano la somma:

| candidato | media | sd | corr con il totale vero |
|---|---:|---:|---:|
| **osservato** | 2.597 | 1.569 |  |
| modello | 2.626 | 0.422 | 0.0989 |
| media campionato | 2.634 | 0.231 | 0.0673 |
| media casa/trasferta | 2.634 | 0.231 | 0.0673 |
| media squadra | 2.636 | 0.691 | 0.0833 |
| media squadra + campo | 2.636 | 0.691 | 0.0834 |

**Il fatto centrale non e' la dispersione di un candidato: e' che il totale di
gol di una partita e' quasi imprevedibile per tutti.** La correlazione migliore
fra somma prevista e totale vero e' 0.099, ed e' del modello. Con un
legame cosi' debole, ogni unita' di dispersione in piu' e' quasi tutta varianza
pagata a vuoto, e su una metrica quadratica **vince chi ne mette meno**: la media
di campionato disperde 0.231, il modello 0.422, le medie di
squadra 0.691. L'ordine del Brier e' esattamente quello, al contrario.

> Questa sezione affermava che «due medie di squadra sommate danno un totale piu'
> disperso del vero». **La misura l'ha corretta**: la dispersione delle medie di
> squadra (0,691) e' ben *sotto* quella del totale osservato (1,569), e il
> problema non e' disperdere troppo in assoluto — e' disperdere senza
> correlazione. `dispersione_somma()` esiste perche' quella frase era
> un'affermazione e non un numero.

**Il modello e' l'unico candidato decente su entrambe le domande**, e questo —
non l'accuratezza su una metrica sola — e' l'argomento con cui si giustifica.

E' la stessa forma dell'argomento della Fase 4, dove il modello si giustificava
per la **calibrazione** e non per l'accuratezza: la virtu' non e' essere il
migliore da qualche parte, e' non essere pessimo da nessuna.

Le altre due linee dicono lo stesso (O1.5:
t = +2.49 contro la
media di campionato; O3.5:
t = +0.56).

---

## 5. La calibrazione, e qui il segno e' OPPOSTO a quello della Fase 4

| candidato | classe | pendenza | errore standard | z vs 1.0 |
|---|---|---:|---:|---:|
| modello | 1 | 1.223 | 0.095 | 2.33 |
| modello | X | 0.966 | 0.299 | -0.11 |
| modello | 2 | 1.324 | 0.101 | 3.21 |
| media squadra + campo | 1 | 1.060 | 0.088 | 0.68 |
| media squadra + campo | X | 0.970 | 0.211 | -0.14 |
| media squadra + campo | 2 | 1.112 | 0.089 | 1.25 |
| media campionato | 1 | 0.240 | 1.837 | -0.41 |
| media campionato | X | 0.112 | 0.839 | -1.06 |
| media campionato | 2 | -0.004 | 1.921 | -0.52 |

- **Il modello e' sotto-sicuro**: pendenza 1.223 sulla classe `1`
  (z = +2.33) e 1.324 sulla `2`
  (z = +3.21), cioe' **sopra 1.0**: le sue probabilita'
  sono troppo vicine al centro e andrebbero allargate.
- **`media squadra + campo` e' meglio calibrato del modello**
  (1.060, z = +0.68).
- **`media campionato` non e' identificata** (errori standard sopra 0,8): e'
  esattamente cio' che la Fase 4 aveva trovato, e per la stessa ragione — il suo
  logit e' quasi costante.

**Nella Fase 4 i baseline informativi erano sotto 1.0** (troppo estremi, perche'
una media campionaria non regredisce) **e il modello era l'unico compatibile con
1.0**. Qui il modello sta dall'altra parte. La spiegazione compatibile e' la
**compressione della ridge** che la Fase 6A ha quantificato (pendenza 0,760 dei
rating sui grezzi): lo shrinkage che sui tiri correggeva l'eccesso, sui gol
proiettati su 1X2 **corregge troppo**. Non e' stato aggiustato — sarebbe far
tornare un numero cambiando la definizione (vincolo 2) — ed e' dichiarato qui
accanto alla metrica, non in fondo.

Affidabilita' del modello sulla classe `1`, fascia per fascia:

| fascia | n | dichiarata | osservata |
|---|---:|---:|---:|
| 0.0-0.1 | 1 | 0.088 | 1.000 |
| 0.1-0.2 | 80 | 0.164 | 0.062 |
| 0.2-0.3 | 251 | 0.257 | 0.211 |
| 0.3-0.4 | 426 | 0.352 | 0.300 |
| 0.4-0.5 | 409 | 0.451 | 0.472 |
| 0.5-0.6 | 276 | 0.545 | 0.558 |
| 0.6-0.7 | 136 | 0.640 | 0.647 |
| 0.7-0.8 | 51 | 0.737 | 0.725 |
| 0.8-0.9 | 8 | 0.825 | 0.500 |

Le due fasce estreme hanno n = 1 e n = 8 e **non vanno lette**: sono riportate
per non selezionare le fasce comode.

---

## 6. Per segmento

| segmento | n | RPS modello | RPS baseline | differenza |
|---|---:|---:|---:|---:|
| equilibrate | 546 | 0.2244 | 0.2236 | 0.0008 |
| medie | 546 | 0.2142 | 0.2190 | -0.0049 |
| squilibrate | 546 | 0.1737 | 0.1745 | -0.0008 |
| 1a meta' | 691 | 0.2074 | 0.2054 | 0.0020 |
| 2a meta' | 947 | 0.2017 | 0.2060 | -0.0043 |

Il modello vince nelle partite **medie** e nella **seconda meta'** di stagione,
e perde di pochissimo nelle **equilibrate** e nella prima meta'. Tutte le
differenze sono molto sotto l'MDE del confronto complessivo: la tabella serve a
mostrare che il vantaggio non e' concentrato in un angolo, non a concludere
qualcosa su ciascun segmento.

Le **squilibrate** meritano una riga in piu' perche' sono il punto in cui R1 ha
dichiarato l'assunzione piu' fragile (`rho` costante fra partite, domanda aperta
3): li' il modello sta -0.00084
contro il baseline, cioe' non peggio che altrove. **Non e' una verifica di quella
domanda** — servirebbe stimare `rho` per fascia di squilibrio — ma se l'assunzione
facesse danno, questo e' il segmento in cui si vedrebbe per primo.

---

## 7. Distribuzione degli esiti

| esito | osservata | modello (media) |
|---|---:|---:|
| 1 | 0.4048 | 0.4233 |
| X | 0.2674 | 0.2507 |
| 2 | 0.3278 | 0.3260 |

Media in campione delle probabilita' dichiarate contro la frequenza osservata.
**Non e' una metrica di accuratezza** e non va citata come tale: serve a mostrare
che la composizione non e' sbilanciata su una classe.

---

## 8. Domande aperte

1. **La sotto-sicurezza del modello su 1X2 non e' stata corretta e non e' stata
   spiegata fino in fondo.** Il legame con la compressione della ridge (Fase 6A)
   e' compatibile ma non e' stato misurato: servirebbe rifare la composizione con
   i lambda de-compressi e vedere se la pendenza va a 1.0. E' un blocco a se',
   e **non va fatto ritoccando lo shrinkage finche' il numero torna gradevole**.
2. **Il confronto con `media squadra + campo` non e' concluso, e' senza potenza.**
   L'MDE su RPS vale 0.00424 contro
   una differenza osservata di 0.00166:
   servirebbero circa 10,711 partite
   per distinguerli, cioe' molte piu' di quante una Serie A ne produca. **E' la
   prima domanda del progetto in cui G2 avrebbe un uso diretto e quantificato.**
3. **Nessuna valutazione di valore atteso e' possibile** senza quote di chiusura
   reali (vincolo 3), e non sono nel repository. Finche' non ci sono, «il modello
   e' meglio del mercato» non e' una frase che questo progetto possa pronunciare.
4. **Le due partite disallineate restano fuori** per decisione dell'utente. Sono
   1638 contro le 1.640 che si avrebbero allineando il burn-in alla giornata.
