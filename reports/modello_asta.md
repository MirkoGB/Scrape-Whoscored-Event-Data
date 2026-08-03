# Modello per l'asta — punti totali attesi di stagione

Generato da `scripts/run_modello_asta.py` il 2026-08-03.
Nessuna richiesta di rete.

## Esito in una riga

**Il modello batte l'ignoranza e non batte il mercato.** Su quattro transizioni
di stagione e 2678 righe giocatore-stagione, ordina meglio di una media di
ruolo (precisione sui primi N **0.177**
contro **0.065**)
ma **perde contro il FVM della fonte** (0.811 di Spearman contro
0.452, precisione **0.518**).
Allo stato attuale, **all'asta conviene guardare il FVM piu' che questo modello**,
e la cosa onesta e' scriverlo.

## 1. Il fantavoto di lega non e' quello della fonte, e si vede

Ricalcolato dai bonus col barema di §1.1. Diverge dalla colonna della fonte su
**1092 righe su 57574**, e la
divergenza e' **esattamente** quella prevista:

| | |
|---|---|
| scarti distinti osservati | `[np.float64(1.0)]` |
| ruoli coinvolti | `['p']` |
| tutte con porta inviolata | `True` |

Un solo valore, `+1`, su soli portieri, tutti con `gol_subiti == 0`. **Se
divergesse altrove sarebbe un difetto**; divergendo solo qui, e' la conferma che
il barema di lega e quello della fonte differiscono per la voce che sapevamo — la
porta inviolata — e per nient'altro.

## 2. Cosa si prevede, e su cosa

L'universo e' **il listone**, non chi ha poi giocato: e' l'insieme su cui si fa
l'asta. Restringerlo a posteriori a chi ha giocato sarebbe guardare il risultato.

| stagione | quotati | con_almeno_una_presenza | quotati_senza_presenze | con_voti_non_quotati |
|---|---:|---:|---:|---:|
| 2021-2022 | 675 | 578 | 97 | 29 |
| 2022-2023 | 672 | 562 | 110 | 15 |
| 2023-2024 | 664 | 563 | 101 | 24 |
| 2024-2025 | 679 | 583 | 96 | 15 |
| 2025-2026 | 663 | 562 | 101 | 24 |

- **~100 quotati per stagione non scendono mai in campo.** Non sono dati
  mancanti: valgono **zero punti**, ed e' il rischio che l'asta paga. Il modello
  li deve prevedere, non escludere.
- **15-29 giocatori per stagione prendono voti senza essere nel listone
  iniziale**: mercato di gennaio e promossi dalla Primavera. Non sono
  acquistabili all'asta e non entrano nella valutazione.

La forma e' quella di §6.1, con i tre fattori stimati separatamente:

```
punti_stagione = presenze_attese x [ voto_base_atteso + bonus_per_presenza_atteso ]
```

**Tutto cio' che entra viene da stagioni precedenti a quella prevista** — medie
di ruolo, pesi di shrinkage, storia del singolo. Le transizioni valutabili sono
quattro, ed e' esattamente il numero che il piano dati della Fase 6F stimava
necessario per la sua domanda D4.

`QI` **non e' leakage**: la quotazione iniziale e' pubblicata prima dell'asta,
quindi e' informazione disponibile al momento della decisione.

## 3. La validazione, coi baseline accanto (vincolo 6)

| candidato | righe | mae | bias | pearson | spearman |
|---|---:|---:|---:|---:|---:|
| modello | 2678 | 61.42 | 18.42 | 0.4692 | 0.4523 |
| media di ruolo | 2678 | 69.99 | 10.05 | 0.2096 | 0.1555 |
| persistenza (anno prima) | 2678 | 62.59 | 22.52 | 0.4636 | 0.451 |
| quotazione iniziale QI | 2678 |  |  | 0.5288 | 0.6056 |
| FVM della fonte | 2678 |  |  | 0.506 | 0.811 |

`MAE` e `bias` sono in punti di fantacalcio; **per `QI` e `FVM` restano vuoti
perche' sono su un'altra scala** (crediti), e un MAE fra grandezze diverse
sarebbe un numero senza significato. Le correlazioni invece sono confrontabili,
e sono quelle che contano per un'asta.

Precisione sui primi N, dove N e' **la rosa di questa lega**
({'p': 3, 'd': 8, 'c': 8, 'a': 6}) e non una soglia inventata:

| candidato | precisione_media |
|---|---:|
| FVM della fonte | 0.518 |
| persistenza (anno prima) | 0.211 |
| modello | 0.177 |
| quotazione iniziale QI | 0.162 |
| media di ruolo | 0.065 |

| candidato | a | c | d | p |
|---|---:|---:|---:|---:|
| FVM della fonte | 0.5 | 0.562 | 0.344 | 0.667 |
| media di ruolo | 0.167 | 0.094 | 0.0 | 0.0 |
| modello | 0.209 | 0.281 | 0.219 | 0.0 |
| persistenza (anno prima) | 0.208 | 0.281 | 0.188 | 0.166 |
| quotazione iniziale QI | 0.209 | 0.281 | 0.156 | 0.0 |

**Tre letture, e nessuna e' comoda:**

1. **Il modello supera la media di ruolo di tre volte** (0.177
   contro 0.065):
   c'e' segnale, e non e' zero.
2. **Ma non supera la persistenza** (0.211),
   cioe' "l'anno prossimo come l'anno scorso". Tutto il macchinario dei tre
   fattori con shrinkage non aggiunge niente a una copia dell'anno prima.
3. **E perde di larghissimo margine contro il FVM.** Non e' un riferimento: e'
   una stima di valore fatta da qualcun altro con informazioni che questo modello
   non ha — mercato in corso, gerarchie di rosa, infortuni noti. Se non lo si
   batte, comprare al listino e' la scelta razionale.

> Sui **portieri** il modello fa precisione 0 e il FVM 0,667. Con tre portieri
> per rosa su ~75 quotati il campione e' minuscolo, ma il segno e' netto e la
> causa e' identificabile: i punti di un portiere dipendono da porte inviolate e
> gol subiti, cioe' dalla **difesa della sua squadra**, e questo modello non
> guarda la squadra affatto.

## 4. Dove sta l'errore: nelle presenze, e non c'e' gara

| variante | righe | mae |
|---|---:|---:|
| modello completo | 2678 | 61.42 |
| presenze note | 2678 | 5.56 |
| bonus noti | 2204 | 52.5 |

**Se le presenze fossero note, il MAE crollerebbe da
61.4 a
5.6**, cioe' del
91%.
Conoscere i bonus invece lo abbassa solo a
52.5.

E' il risultato piu' utile del blocco, perche' dice **dove lavorare**: il voto
base e i bonus sono quasi risolti, il problema e' prevedere **quante partite un
giocatore giochera'**. E quello dipende da cose che nessuna delle tabelle
acquisite contiene: minutaggio atteso, gerarchia in rosa, mercato, infortuni.
Non e' un difetto di stima, e' un'assenza di dati.

La scomposizione **non e' esatta** — i tre fattori si moltiplicano, quindi gli
effetti non sono additivi — ed e' riportata come diagnostica.

## 5. I primi quindici della 2025-2026, con l'osservato accanto

| giocatore | ruolo | QI | presenze_attese | voto_atteso | punti_previsti | punti_osservati |
|---|---|---:|---:|---:|---:|---:|
| Martinez L. | a | 34 | 30.91 | 6.41 | 250.09 | 247.5 |
| Leao | a | 24 | 31.12 | 6.42 | 234.89 | 192.0 |
| Pulisic | c | 28 | 30.71 | 6.35 | 229.75 | 191.0 |
| Thuram | a | 29 | 29.02 | 6.44 | 225.57 | 230.5 |
| Barella | c | 14 | 32.73 | 6.35 | 220.44 | 228.0 |
| Lookman | a | 29 | 27.67 | 6.41 | 216.48 | 64.0 |
| Pinamonti | a | 16 | 32.39 | 5.93 | 216.37 | 225.0 |
| Vlahovic | a | 24 | 27.74 | 6.21 | 211.8 | 131.5 |
| McTominay | c | 26 | 27.66 | 6.55 | 211.26 | 239.5 |
| Di Lorenzo | d | 14 | 33.07 | 6.17 | 210.94 | 164.5 |
| Calhanoglu | c | 23 | 29.56 | 6.38 | 210.93 | 168.0 |
| Lukaku | a | 31 | 28.21 | 6.21 | 210.54 | 9.5 |
| Zaccagni | c | 26 | 29.78 | 6.34 | 210.06 | 155.0 |
| Immobile | a | 19 | 26.87 | 6.25 | 207.78 | 33.0 |
| Pasalic | c | 9 | 30.62 | 6.08 | 206.67 | 194.5 |

## Limiti dichiarati

1. **Il modificatore di difesa non c'e'.** Non e' decomponibile per giocatore
   (§2.2) ed e' fermo sulla decisione **0.3** — come si tratta un difensore senza
   voto dentro la linea. `sot/lega.gestione_sv()` solleva `DecisioneMancante`
   invece di scegliere un default. I punti qui sono **al netto** del
   modificatore, per tutti i ruoli: per portieri e difensori vanno letti
   sapendolo, perche' il bonus arriva a +6.
2. **Il listone 2026-27 non esiste ancora.** Verificato il 2026-08-03: la pagina
   c'e' e dichiara "Dati non disponibili". Quindi **la lista d'asta vera non e'
   producibile oggi** — il modello si applica a un listone, e quel listone
   uscira' a fine agosto. Lo scraper distingue questo caso da un cambio di
   markup e non manda la pagina in quarantena.
3. **Quattro transizioni sono poche.** Con quattro stagioni valutabili, la
   differenza fra modello e persistenza (0,03 di precisione) non e'
   distinguibile dal rumore. Il segno e' contrario al modello, ed e' l'unica
   cosa che si puo' dire.
4. **Il modello non guarda la squadra.** Ne' l'attacco, ne' la difesa, ne' il
   calendario. Il repository ha un modello di squadra validato (Fasi 2-4) e
   questo blocco **non lo usa**: e' la prima cosa da collegare, e sui portieri
   e' quasi certamente dove sta la differenza col FVM.
5. **Nessuna correzione e' stata applicata per far salire i numeri.** Il
   risultato negativo contro FVM e persistenza e' il risultato.
