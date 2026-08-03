# Aggancio delle due fonti, e la regola dell'80' misurata

Generato da `scripts/run_aggancio.py` il 2026-08-03.
Nessuna richiesta di rete, niente scritto sotto `data/raw/`.

## Esito in una riga

Le due fonti sono agganciate su **1.888 partite** di cinque
stagioni e su **609 giocatori su 609**
della 2025-26, senza nessun caso irrisolto; e la regola dell'80' — decisa
dall'utente e marcata `[DA MISURARE]` in `docs/regole_fantacalcio.md` §1.2 —
**concorda con l's.v. osservato sul 97.84% delle righe,
contro il 90.45% del baseline che non prevede nessun s.v.**

## 1. La chiave e' diversa ai due livelli, e non era ovvio

| livello | chiave | verifica |
|---|---|---|
| squadra | l'insieme delle 38 coppie `(data, in casa)` | il nome |
| partita | `(stagione, casa, trasferta)` | la data |
| giocatore | il **cognome** dentro la squadra, con le iniziali a disambiguare | il calendario |

**Al livello di squadra il nome non e' una chiave**: la fonte degli eventi dice
`AC Milan`, `Parma Calcio 1913`, `Hellas Verona`; quella dei voti dice `Milan`,
`Parma`, `Verona`. Il calendario invece lo e', ed e' esatto:

| stagione | squadre | margine_min | in_comune_min |
|---|---:|---:|---:|
| 2021-2022 | 20 | 19 | 35 |
| 2022-2023 | 20 | 23 | 35 |
| 2023-2024 | 20 | 25 | 37 |
| 2024-2025 | 20 | 22 | 37 |
| 2025-2026 | 20 | 24 | 38 |

`margine` e' di quante partite il primo candidato batte il secondo. Sta fra 19 e
29 su 38: non e' un aggancio che regge per poco.

**Al livello di giocatore vale l'esatto contrario, e questa e' la cosa che ho
dovuto misurare invece di assumerla.** La prima versione agganciava i giocatori
per insieme di presenze, per simmetria con le squadre. **Non funziona**, e il
motivo e' strutturale: l'insieme delle partite di una *squadra* e' 38 su 380 —
sparso, quindi discriminante — mentre quello di un *giocatore* dentro la sua
squadra e' 35 su 38, cioe' quasi pieno. Due titolari qualsiasi della stessa
squadra hanno fra loro un Jaccard di ~0,85, e il margine sul secondo candidato
scendeva **sotto 0,03 su meta' della rosa**. Al livello di giocatore il
calendario non e' un'impronta: e' rumore.

## 2. Partite: 1.888 agganciate, e i residui si dichiarano

| stagione | agganciate | scarto_max | voti_senza_eventi | eventi_senza_voti |
|---|---:|---:|---:|---:|
| 2021-2022 | 374 | 0 | 6 | 0 |
| 2022-2023 | 374 | 0 | 6 | 1 |
| 2023-2024 | 380 | 11 | 0 | 0 |
| 2024-2025 | 380 | 67 | 0 | 0 |
| 2025-2026 | 380 | 0 | 0 | 0 |

- **12 partite hanno i voti e non gli eventi**, tutte nel 2021-22 e
  2022-23: sono esattamente le **12 che WhoScored non ha**, con
  `matchCentreData: null`, verificate una per una durante l'acquisizione. Non
  sono un difetto dell'aggancio e non si recuperano.
- **1 partita ha gli eventi e non i voti**: lo **spareggio salvezza
  Spezia-Verona dell'11 giugno 2023**. E' l'unica coppia ordinata che si ripete
  in una stagione, e le pagine dei voti — organizzate per giornata — non la
  contengono. Senza accorgersene, si sarebbe agganciata ai voti della **giornata
  25**, mettendo una partita di giugno sotto i voti di marzo.
- **Due partite hanno le due fonti in disaccordo sulla data**, ed entrambe hanno
  una ragione: Udinese-Roma 2023-24 (11 giorni) e Fiorentina-Inter 2024-25 (67
  giorni) sono le due partite **interrotte e riprese** in un'altra data. I voti
  le datano alla giornata, gli eventi al completamento. L'aggancio e' giusto, la
  data no — e va scelta quella che serve, non mediata.

**La giornata di campionato adesso c'e'.** Chiude la **D6** del Blocco 0 per la
via (b): non si stima e non si sostituisce con l'indice cronologico di squadra,
**si legge dalla fonte dei voti** e arriva sulle partite WhoScored attraverso
questo aggancio. `team_match_idx` resta cio' che era — un indice — e le due
grandezze divergono sui recuperi, che e' il motivo per cui serviva quella vera.

## 3. Giocatori: 609 su 609, e il residuo e' zero

| risolto_da | giocatori |
|---|---:|
| cognome | 605 |
| cognome + iniziali | 2 |
| calendario | 1 |
| cognome parziale | 1 |

Il lato WhoScored e' ristretto a chi ha **almeno un minuto**: sono 609, gli
stessi 609 dei voti. `player_match` ne contiene 803, ma 194 sono panchinari mai
entrati, che i voti giustamente non elencano.

**La verifica e' il calendario, e passa**: il Jaccard fra i due insiemi di
presenze ha media **0.9999** e minimo **0.9444**.
Le due fonti sono d'accordo su chi e' sceso in campo, partita per partita.

I 23 casi su 609 che il cognome grezzo sbaglia sono tutti e soli di due specie,
e **nessuna delle due e' un'omonimia**:

- **lettere che l'ASCII non piega**: `Højlund`, `Østigård`, `Grønbæk`, `Løvik`,
  `Sørensen`. La decomposizione Unicode non le tocca — `ø` non e' una `o` con un
  segno sopra, e' un'altra lettera — e servono a mano;
- **le iniziali del nome proprio**, che la fonte dei voti aggiunge **solo quando
  servono**: `Martinez L.` contro `Martinez Jo.`, `Pellegrini Lu.` contro
  `Pellegrini Lo.`, `Esposito F.P.` contro `Esposito Se.`. Sono l'informazione
  che risolve i due unici cognomi ambigui della stagione, quindi **si usano, non
  si tolgono** — buttarle via creava le ambiguita' da risolvere.

Un caso solo ha richiesto il ripiego sull'ultimo pezzo del cognome:
**`Zambo Anguissa` contro `Frank Anguissa`**, dove `Zambo` e' patronimico per una
fonte e nome proprio per l'altra. 18 presenze da entrambe le parti.

### Il ruolo NON e' la stessa grandezza nelle due fonti

**133 giocatori su 609 hanno ruoli discordanti**, e non e' un errore
di aggancio: e' il vincolo 7 in azione. Il ruolo dei voti e' quello del
fantacalcio Classic (P/D/C/A, un'etichetta di *lega*); quello di WhoScored e'
posizionale. Un esterno di centrocampo e' `d` per il fantacalcio e `MID` per
WhoScored, e nessuno dei due ha torto.

| ruolo_fc | DEF | FWD | GK | MID | UNK |
|---|---:|---:|---:|---:|---:|
| p | 4 | 0 | 42 | 0 | 0 |
| d | 149 | 4 | 0 | 59 | 0 |
| c | 5 | 46 | 0 | 170 | 0 |
| a | 1 | 115 | 0 | 13 | 1 |

**Le due colonne restano separate** nella tabella prodotta (`ruolo_fc`,
`ruolo_ws`). Non si convertono e non si sceglie la piu' comoda: per il modello
del fantacalcio conta il ruolo di lega, perche' e' quello che determina bonus e
modificatore.

## 4. La regola dell'80', misurata — §1.2 `[DA MISURARE]`, chiuso

Universo: **11.926 righe giocatore-partita** della 2025-26,
cioe' chi e' sceso in campo. Su tutte c'e' sia il voto sia il minuto d'ingresso.

> WhoScored ne conta **11.928** con almeno un minuto, e
> le due che mancano non sono un difetto dell'aggancio: la fonte dei voti **non
> elenca affatto** Estevez (entrato al 90', 7 minuti) e Folino (all'88', 10
> minuti). Non gli da' s.v.: non gli da' riga. E' un terzo stato oltre "voto" e
> "s.v.", che per il modello ricade nel secondo, ma che dice una cosa
> sull'universo: quello dei voti e' *quasi* — non *esattamente* — chi e' sceso
> in campo.

| regola | sv_proiettati | concordi | quota_concordi | falsi_sv | sv_mancati | richiamo |
|---|---:|---:|---:|---:|---:|---:|
| regola 80' (utente) | 1165.0 | 11668.0 | 0.9784 | 142.0 | 116.0 | 0.8982 |
| baseline: nessun s.v. | 0.0 | 10787.0 | 0.9045 | 0.0 | 1139.0 | 0.0 |
| baseline: s.v. a ogni subentrato | 3566.0 | 9463.0 | 0.7935 | 2445.0 | 18.0 | 0.9842 |

**L'accordo del 97.84% va letto accanto al baseline, non
da solo** (vincolo 6). Dire *"nessuno prende s.v."* ne azzecca gia' il
90.45%, perche' l's.v. e' raro. Il guadagno vero della
regola e' di **7.4
punti**, non di 98.

I due versi che §1.2 chiede, separati:

- **falsi s.v.**: 142 righe — entra al ≥ 80' e il voto
  invece lo prende. Sono il **12.2%** di chi la regola
  dichiara senza voto;
- **s.v. mancati**: 116 righe — entra prima e il voto non
  lo prende. Sono il **1.08%** di chi la regola
  dichiara a voto.

### La soglia e' scelta, non stimata — e cade sul massimo

| soglia | sv_proiettati | concordi | quota_concordi | falsi_sv | sv_mancati | richiamo |
|---:|---:|---:|---:|---:|---:|---:|
| 60 | 2942.0 | 10083.0 | 0.8455 | 1823.0 | 20.0 | 0.9824 |
| 65 | 2545.0 | 10480.0 | 0.8788 | 1426.0 | 20.0 | 0.9824 |
| 70 | 2072.0 | 10953.0 | 0.9184 | 953.0 | 20.0 | 0.9824 |
| 75 | 1658.0 | 11367.0 | 0.9531 | 539.0 | 20.0 | 0.9824 |
| 80 | 1165.0 | 11668.0 | 0.9784 | 142.0 | 116.0 | 0.8982 |
| 85 | 664.0 | 11381.0 | 0.9543 | 35.0 | 510.0 | 0.5522 |
| 90 | 248.0 | 11019.0 | 0.9239 | 8.0 | 899.0 | 0.2107 |
| 95 | 38.0 | 10825.0 | 0.9077 | 0.0 | 1101.0 | 0.0334 |

**L'80' e' il massimo della griglia**, e va detto con l'avvertenza giusta: non e'
stato scelto guardando questa tabella. E' una decisione dell'utente presa prima,
dichiarata in `regole_fantacalcio.md` §1.2, e **qui viene solo verificata**. Se
fosse stato scelto qui sarebbe un iperparametro adattato al campione, cioe' il
vincolo 1 violato; scelto prima e trovato al massimo, e' una conferma.

Attorno la superficie e' ripida: a 75' l'accordo scende a
0.9531 e a 85' a
0.9543. Il Blocco 0
aveva gia' misurato che l'80' cade nel punto di **massima densita' degli
ingressi**: e' la posizione in cui la regola e' piu' sensibile alla propria
scelta, e questa tabella dice di quanto.

### Il verso d'errore che la regola non puo' vedere

| uscito_prima_del | titolari | di_cui_sv | quota_sv |
|---:|---:|---:|---:|
| 10 | 11 | 8 | 0.7273 |
| 20 | 28 | 18 | 0.6429 |
| 30 | 56 | 18 | 0.3214 |

Un titolare uscito al 15' per infortunio o espulsione puo' prendere s.v., e la
regola — che guarda il minuto d'**ingresso** — non lo vedra' mai. Non e' errore
di campionamento, e' una **classe di casi fuori dal dominio della regola**;
§1.2 non la elenca fra i due versi da misurare. **Tutti e 18
gli s.v. dei titolari sono di questa specie**: nessun titolare che abbia superato
il 20' ha mai preso s.v. nella stagione.

### Il fatto che la misura ha portato a galla

| scaglione | righe | sv | quota_sv |
|---|---:|---:|---:|
| [0, 10) | 326 | 316 | 0.9693 |
| [10, 20) | 1004 | 789 | 0.7859 |
| [20, 30) | 945 | 34 | 0.036 |
| [30, 40) | 808 | 0 | 0.0 |
| [40, 50) | 596 | 0 | 0.0 |
| [50, 60) | 460 | 0 | 0.0 |
| [60, 70) | 904 | 0 | 0.0 |
| [70, 80) | 934 | 0 | 0.0 |
| [80, 90) | 934 | 0 | 0.0 |
| [90, 100) | 3916 | 0 | 0.0 |

**Sopra i 30 minuti giocati non c'e' un solo s.v. su 8.552 righe.** Il crollo e'
fra i 20 e i 30 minuti, e la transizione e' netta: 78,6% a [10,20), 3,6% a
[20,30), zero esatto sopra.

Questo **non contraddice** la dichiarazione della fonte — "non esiste, e mai
esisterà, una regola che prevede che il voto venga dato a chi gioca un numero
minimo di minuti" — ma la mette in prospettiva: la regola formale non c'e', la
*pratica* editoriale e' quasi deterministica. Un modello che predica l's.v. dai
minuti non sta adattandosi a rumore quanto §7 della ricognizione temeva.

**Il sospetto conseguente e' stato misurato, ed e' risultato infondato:**

| soglia_minuti | sv_proiettati | concordi | quota_concordi | falsi_sv | sv_mancati | richiamo |
|---:|---:|---:|---:|---:|---:|---:|
| 10 | 326.0 | 11093.0 | 0.9302 | 10.0 | 823.0 | 0.2774 |
| 15 | 793.0 | 11496.0 | 0.9639 | 42.0 | 388.0 | 0.6594 |
| 20 | 1330.0 | 11667.0 | 0.9783 | 225.0 | 34.0 | 0.9701 |
| 25 | 1795.0 | 11266.0 | 0.9447 | 658.0 | 2.0 | 0.9982 |
| 30 | 2275.0 | 10790.0 | 0.9047 | 1136.0 | 0.0 | 1.0 |
| 35 | 2679.0 | 10386.0 | 0.8709 | 1540.0 | 0.0 | 1.0 |
| 40 | 3083.0 | 9982.0 | 0.837 | 1944.0 | 0.0 | 1.0 |

Al suo optimum (20 minuti giocati) la regola alternativa fa **0,9783** contro
**0,9784** della regola dell'utente. **Sono la stessa cosa.** Cambia il *mix*
degli errori, non la loro quantita': la forma sui minuti prende quasi tutti gli
s.v. veri (richiamo 0,97 contro 0,90) e in cambio ne inventa di piu' (225 falsi
contro 142). Quale dei due errori pesi di piu' e' una domanda di prodotto, e non
la decido io. **La regola resta quella di §1.2.**

## Cosa e' stato prodotto

| | |
|---|---|
| `data/mapping/aggancio_squadre.csv` | 100 righe, 20 per stagione |
| `data/mapping/aggancio_partite.csv` | 1.888 righe, con giornata e `matchId` |
| `data/mapping/aggancio_giocatori.csv` | 609 righe, 2025-26 |
| `data/processed/ITA-serie-a/presenza_2025-2026.parquet` | voti **e** minuti sulla stessa riga |
| `reports/presenza_*.csv` | le quattro tavole di questa sezione |

## Limiti dichiarati

1. **L'aggancio dei giocatori copre solo la 2025-2026.** Ha bisogno delle
   presenze partita per partita dal lato WhoScored, che oggi esistono solo per la
   stagione pubblicata (`player_match.parquet`). Estenderlo alle altre quattro
   vuol dire far girare l'aggregazione della Fase 1 su 1.509 CSV in piu': e'
   fattibile e non e' stato fatto qui.
2. **La regola dell'80' e' misurata su una stagione e non puo' esserlo su
   altre.** 11.926 righe sono tante, ma sono un anno solo di una redazione sola.
   Se il criterio editoriale cambiasse, questo numero non se ne accorgerebbe.
3. **`expandedMinute` non e' il minuto di gioco.** La partita dura 94-99', quindi
   l'80' della regola non e' l'80' dell'orologio: chi entra all'80' espanso gioca
   fino a 25 minuti, mediana 12. La regola e' **piu' permissiva** di quanto "80'"
   suggerisca, ed e' una conseguenza della scelta — coerente con tutto il
   repository — di usare `expandedMinute`.
4. **Il ruolo di lega e quello posizionale restano due colonne.** Vedi §3.
