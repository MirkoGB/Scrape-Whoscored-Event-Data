# Fase 10 / Blocco R3 — la classifica: simulare il resto di una stagione

> Generato da `scripts/run_fase10_r3.py` il 2026-08-08.
> **Nessuna richiesta di rete. Nessun parametro nuovo**: i lambda vengono da
> E3.1, le probabilita' ricalibrate da R2-bis, il calendario dalla fonte dei
> voti. Questo blocco **simula**.

---

## 0. Il vincolo che struttura il blocco, e che viene da R0

**Non si simula una stagione da zero.** Le prime tre giornate non hanno alcuna
previsione — il walk-forward di E3 pretende 30 partite di training — la 4a e la
5a ne hanno una ma non sono `eligible`, e la prima giornata piena e' **la sesta o
la settima, mai prima**. Non esiste una probabilita' di scudetto alla prima
giornata, e il blocco non finge che esista: **simula il resto di una stagione
dalla giornata `k`, data la classifica vera a `k`**.

Le giornate di partenza sono **dichiarate e non scelte guardando i risultati**:
10a, 19a, 28a, cioe' un quarto, il giro di
boa e tre quarti di stagione.

**E R0 dice anche quanto poco si potra' concludere.** Una probabilita' di
scudetto ha **una realizzazione per stagione**, e previsioni fatte a giornate
diverse della stessa stagione condividono l'esito. Ne segue la scelta che governa
tutto il blocco:

> **La validazione di R3 sono i PUNTI FINALI di ogni squadra, non le probabilita'
> di scudetto.** I primi hanno venti realizzazioni per stagione, le seconde una.
> §5 misura i punti; §6 riporta le probabilita' di classifica come
> **descrizione**, con il proprio limite scritto accanto e non in fondo.

---

## 1. Gli ingressi, e dove il buco di WhoScored non morde

| ingresso | fonte |
|---|---|
| classifica vera a `k`, risultati veri | **calendario completo della fonte dei voti**: 380 partite per stagione, gol mai nulli |
| probabilita' 1X2 | R2-bis, **Platt walk-forward** dove esiste un passato su cui stimarlo |
| punteggio (per la differenza reti) | congiunta di R1 **condizionata all'esito ricalibrato** |

**La classifica non ha buchi**, ed e' il punto che R1 aveva anticipato: delle 12
partite che WhoScored non ha, il **risultato** si legge lo stesso dall'altra
fonte. Il buco sta negli **ingressi** della previsione, non nel bersaglio.

Il calendario regge le identita' che una stagione deve rispettare — falsificabili
e senza modelli di mezzo:

| stagione | partite | squadre | 38 partite a testa | 19 in casa a testa | punti totali | attesi (3n - pareggi) | identita' dei punti |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2021-2022 | 380 | 20 | si | si | 1042 | 1042 | si |
| 2022-2023 | 380 | 20 | si | si | 1040 | 1040 | si |
| 2023-2024 | 380 | 20 | si | si | 1028 | 1028 | si |
| 2024-2025 | 380 | 20 | si | si | 1032 | 1032 | si |
| 2025-2026 | 380 | 20 | si | si | 1041 | 1041 | si |

**Le partite del futuro senza previsione ricevono un ripiego dichiarato** — i
lambda medi di casa e trasferta della loro stagione, cioe' il candidato meno
informativo del repository — e **si contano**:

| stagione | partite | con previsione | ripiego dopo la 10a | ripiego dopo la 19a | ripiego dopo la 28a |
|---|---:|---:|---:|---:|---:|
| 2021-2022 | 380 | 323 | 4 | 0 | 0 |
| 2022-2023 | 380 | 324 | 5 | 3 | 2 |
| 2023-2024 | 380 | 330 | 0 | 0 | 0 |
| 2024-2025 | 380 | 330 | 0 | 0 | 0 |
| 2025-2026 | 380 | 330 | 0 | 0 | 0 |

Sono al massimo cinque per stagione e stanno tutte nelle due annate a cui
WhoScored ha perso partite. Non e' una scelta di modellazione: e' il modo di non
far sparire una partita dalla classifica.

**La domanda aperta n. 4 di R0 ha una misura.** Era «non e' verificato che
l'ordine per data basti a ricostruire la classifica progressiva in presenza di
recuperi». Qui `k` e' **ordinale**: «dopo la giornata `k`» significa «tutte le
partite con `giornata <= k`», anche quelle rinviate e giocate dopo. Le due
letture divergono su:

| stagione | partite | fuori ordine | quota |
|---|---:|---:|---:|
| 2021-2022 | 380 | 5 | 0.0132 |
| 2022-2023 | 380 | 0 | 0.0000 |
| 2023-2024 | 380 | 5 | 0.0132 |
| 2024-2025 | 380 | 4 | 0.0105 |
| 2025-2026 | 380 | 5 | 0.0132 |

Circa l'1,3% delle partite si gioca dopo che la giornata successiva e'
cominciata. **La convenzione ordinale e' dichiarata, non dimostrata equivalente**:
un osservatore in tempo reale vedrebbe squadre con partite da recuperare, e per
quelle quattro o cinque partite per stagione la classifica di partenza di questo
blocco e' piu' informata della sua.

---

## 2. Come si simula, e perche' cosi'

La classifica a `k` entra come **costante**: e' la storia, non una previsione, e
simularla sarebbe simulare cio' che si sa gia'. Delle partite rimanenti si estrae
prima l'**esito** con la probabilita' ricalibrata di R2-bis, poi il **punteggio**
dentro la classe estratta, con `P(gol_casa, gol_trasferta | esito)` presa dalla
congiunta di R1.

> **E' la costruzione che tiene insieme la ricalibrazione e la differenza reti.**
> R2-bis aveva dichiarato il prezzo di Platt: le tre probabilita' 1X2 non escono
> piu' dalla stessa congiunta che produce l'over/under. Condizionando il
> punteggio all'esito quel prezzo non si paga sui punti — la probabilita'
> dell'esito e' quella adottata, e il punteggio resta coerente con essa.

**Lo scioglimento dei pari merito e' una semplificazione dichiarata**: punti,
poi differenza reti, poi gol fatti, poi estrazione col seme del progetto. La
Serie A userebbe gli **scontri diretti**. Quanto spesso la scelta decide una
soglia, misurato sulla stagione vetrina:

| soglia | repliche in cui c'e' un pari merito al confine |
|---|---:|
| scudetto | 3.4% |
| top 4 | 13.9% |
| retrocessione | 15.6% |

**Non e' trascurabile al confine dell'Europa e della retrocessione**, ed e' il
motivo per cui sta in tabella invece che in una nota.

---

## 3. La stagione vetrina: 2025-2026 dalla 19a giornata

| squadra | punti a k | punti attesi | scudetto | top 4 | retrocessione | punti finali veri | posizione vera |
|---|---:|---:|---:|---:|---:|---:|---:|
| Inter | 45 | 84.7 | 0.877 | 0.998 | 0.000 | 87 | 1 |
| Milan | 42 | 74.7 | 0.075 | 0.863 | 0.000 | 70 | 5 |
| Napoli | 39 | 70.8 | 0.020 | 0.642 | 0.000 | 76 | 2 |
| Juventus | 36 | 70.2 | 0.015 | 0.610 | 0.000 | 69 | 6 |
| Como | 33 | 67.9 | 0.006 | 0.449 | 0.000 | 71 | 4 |
| Roma | 36 | 67.7 | 0.005 | 0.400 | 0.000 | 73 | 3 |
| Atalanta | 28 | 58.0 | 0.000 | 0.026 | 0.000 | 59 | 7 |
| Bologna | 29 | 55.3 | 0.000 | 0.010 | 0.000 | 56 | 8 |
| Lazio | 25 | 50.9 | 0.000 | 0.001 | 0.001 | 54 | 9 |
| Udinese | 25 | 48.6 | 0.000 | 0.000 | 0.005 | 50 | 10 |
| Sassuolo | 23 | 47.4 | 0.000 | 0.000 | 0.007 | 49 | 11 |
| Torino | 23 | 43.4 | 0.000 | 0.000 | 0.040 | 45 | 13 |
| Cagliari | 19 | 41.4 | 0.000 | 0.000 | 0.077 | 43 | 14 |
| Cremonese | 22 | 41.2 | 0.000 | 0.000 | 0.078 | 34 | 18 |
| Genoa | 16 | 39.6 | 0.000 | 0.000 | 0.141 | 41 | 16 |
| Parma | 19 | 39.3 | 0.000 | 0.000 | 0.147 | 45 | 12 |
| Fiorentina | 13 | 36.0 | 0.000 | 0.000 | 0.340 | 42 | 15 |
| Lecce | 17 | 35.8 | 0.000 | 0.000 | 0.401 | 38 | 17 |
| Verona | 13 | 28.8 | 0.000 | 0.000 | 0.877 | 21 | 19 |
| Pisa | 12 | 28.4 | 0.000 | 0.000 | 0.886 | 18 | 20 |

Le colonne `punti finali veri` e `posizione vera` sono **l'esito**, non un
ingresso: la simulazione non le vede.

**Le tre retrocesse e la probabilita' che avevano alla 19a giornata**:
**Pisa** 89%, **Verona** 88%, **Cremonese** 8%.
Due su tre erano le due piu' alte della colonna; **la terza no**, ed e' il modo
onesto di leggere la tabella — la squadra con la terza probabilita' piu' alta
(Lecce, 40%) si e'
salvata. Il Como, che e' la squadra del progetto, aveva
45% di finire nei primi 4 ed e' arrivato
4o.

---

## 4. Il danno che R2-bis prevedeva e' molto piu' piccolo, e il perche' si misura

R2-bis aveva misurato che la classifica e' **sotto-dispersa di un fattore 2,0**
sulle probabilita' di partita, e ne aveva tratto che le code di R3 sarebbero
uscite troppo grasse. **Sui punti finali quel fattore quasi sparisce**, e la
ragione e' che la simulazione **parte dalla classifica vera**:

| k | rapporto sd medio | sd punti veri | sd punti attesi |
|---:|---:|---:|---:|
| 10 | 1.270 | 18.55 | 14.64 |
| 19 | 1.122 | 18.55 | 16.54 |
| 28 | 1.047 | 18.55 | 17.77 |

Il rapporto scende da 1,27 alla 10a a 1,05 alla 28a. **Il meccanismo e'
aritmetico e non una scusa**: la classifica a `k` porta dentro la separazione
**vera** fra le squadre, quella osservata e non quella dichiarata dal modello, e
la compressione tocca solo la parte ancora da giocare. Piu' `k` avanza, meno
resta da comprimere.

> **Ne segue una correzione della lettura di R2-bis, non dei suoi numeri.** Il
> 2,0 e' giusto e riguarda cio' che il modello *dichiara per partita*; la sua
> conseguenza su R3 e' molto piu' piccola di quanto R2-bis lasciasse prevedere,
> **perche' R3 non simula una stagione intera**. Se qualcuno un giorno volesse
> simulare da giornata zero — cosa che R0 vieta per un'altra ragione — quel 2,0
> tornerebbe intero.

Il dettaglio per stagione alla 19a giornata:

| stagione | sd punti veri | sd punti attesi | sd dentro una squadra | primo vero | primo atteso | ultimo vero | ultimo atteso | rapporto sd |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 2021-2022 | 18.46 | 16.34 | 5.46 | 86 | 83.4 | 27 | 27.4 | 1.130 |
| 2022-2023 | 18.43 | 17.01 | 5.22 | 90 | 89.8 | 19 | 24.7 | 1.084 |
| 2023-2024 | 18.70 | 16.63 | 5.26 | 94 | 89.6 | 17 | 27.7 | 1.124 |
| 2024-2025 | 18.92 | 16.41 | 5.23 | 82 | 78.9 | 18 | 27.0 | 1.153 |
| 2025-2026 | 18.26 | 16.34 | 5.18 | 87 | 84.7 | 18 | 28.4 | 1.118 |

**Dove la compressione si vede ancora e' agli estremi**: l'ultima in classifica
fa in media 20 punti veri contro
27 attesi. Il modello non crede che una
squadra possa andare cosi' male, ed e' lo stesso segno che la Fase 3 e la Fase 4
avevano trovato sul terzile alto di lambda e sulle squadre di vertice.

---

## 5. La validazione: i punti finali

| k | stagioni | n | copertura 50% | copertura 80% | copertura 95% | MAE punti | bias punti | sd simulata | sd osservata | chi2 PIT (9 gdl) |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 10 | 5 | 100 | 0.57 | 0.85 | 0.96 | 4.792 | -0.033 | 14.64 | 18.55 | 12.4 |
| 19 | 5 | 100 | 0.62 | 0.86 | 0.97 | 3.798 | 0.044 | 16.54 | 18.55 | 23.4 |
| 28 | 5 | 100 | 0.65 | 0.89 | 0.98 | 2.729 | 0.023 | 17.77 | 18.55 | 10.0 |

- **La copertura non e' sotto il nominale: e' sopra.**
  62% / 86% / 97%
  contro 50 / 80 / 95 alla 19a. Gli intervalli sono se mai **troppo
  larghi**, non troppo stretti — cioe' l'opposto di cio' che la sotto-dispersione
  faceva temere. Le due cose convivono ed e' la firma dello shrinkage: previsioni
  tirate verso il centro **e** incertezza abbondante attorno a ciascuna.
- **Il bias e' praticamente nullo** (+0.044 punti su una
  stagione intera) e il MAE cala con `k` come deve: 4,8 punti dalla 10a,
  3.8 dalla 19a, 2,7 dalla 28a.
- **Il chi2 sulla PIT non e' un test qui, ed e' importante dirlo**: venti squadre
  di una stessa stagione si dividono un monte punti quasi fisso, quindi le cento
  righe sono **correlate per costruzione** e il `p` nominale sopravvaluta la
  significativita'. Si riporta come descrizione. La forma:

| fascia | osservate | attese |
|---|---:|---:|
| 0.0-0.1 | 13 | 10.0 |
| 0.1-0.2 | 7 | 10.0 |
| 0.2-0.3 | 7 | 10.0 |
| 0.3-0.4 | 7 | 10.0 |
| 0.4-0.5 | 7 | 10.0 |
| 0.5-0.6 | 13 | 10.0 |
| 0.6-0.7 | 19 | 10.0 |
| 0.7-0.8 | 11 | 10.0 |
| 0.8-0.9 | 13 | 10.0 |
| 0.9-1.0 | 3 | 10.0 |

  Non e' ne' una `U` (intervalli stretti) ne' una campana pulita: e' rumorosa,
  con la fascia alta piu' magra dell'attesa, cioe' qualche squadra che finisce
  sotto la coda superiore della propria distribuzione. Con cento righe correlate
  non si conclude altro.

**Contro i baseline, con la stessa procedura di simulazione** (vincolo 6):

| variante | k | n | MAE punti | bias punti | copertura 50% | copertura 80% | copertura 95% | sd simulata | sd osservata |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| modello | 19 | 100 | 3.798 | 0.044 | 0.62 | 0.86 | 0.97 | 16.54 | 18.55 |
| modello grezzo | 19 | 100 | 3.963 | 0.238 | 0.63 | 0.86 | 0.96 | 15.95 | 18.55 |
| media squadra + campo | 19 | 100 | 4.580 | 0.192 | 0.56 | 0.76 | 0.92 | 15.68 | 18.55 |
| media campionato | 19 | 100 | 7.555 | 0.114 | 0.33 | 0.57 | 0.79 | 10.42 | 18.55 |

| baseline | MAE modello | MAE baseline | differenza | t (squadra-stagione, n=100) | t (stagione, n=5) | p (stagione) | modello vince |
|---|---:|---:|---:|---:|---:|---:|---:|
| modello grezzo | 3.798 | 3.963 | -0.165 | -2.35 | -2.41 | 0.0739 | si |
| media squadra + campo | 3.798 | 4.580 | -0.782 | -3.97 | -3.21 | 0.0325 | si |
| media campionato | 3.798 | 7.555 | -3.757 | -8.59 | -12.27 | 0.0003 | si |

- **Qui il modello batte il baseline migliore, e su 1X2 non lo faceva.** Contro
  `media squadra + campo` la differenza vale
  -0.782 punti di MAE con
  t = -3.21 sull'unita'
  onesta (la stagione, n = 5, p = 0.032).
  Su una singola partita il margine valeva t = −1,10 e stava dentro il rumore;
  **su diciannove giornate lo stesso margine si accumula**, ed e' l'unico posto
  della Fase 10 in cui il modello si distingue da un baseline informativo.
- **La ricalibrazione di R2-bis paga**, e questo e' il ritorno del blocco
  precedente: -0.165 punti di MAE contro il
  modello non ricalibrato, t = -2.41
  per stagione (p = 0.074). Piccolo e nella
  direzione giusta — **non e' una prova**, con cinque stagioni.
- **`media campionato` e' il candidato che si rompe sulla calibrazione**, non solo
  sull'accuratezza: copertura 33 / 57 / 79 contro il nominale 50 / 80 / 95. Non
  sapendo distinguere le squadre, sottostima quanto la classifica finale possa
  allontanarsi dalla propria previsione piatta.
- **I due `t` vanno letti insieme e non se ne sceglie uno.** Quello su cento
  righe e' ottimista perche' le squadre di una stagione si dividono un monte
  punti quasi fisso; quello su cinque stagioni e' onesto e quasi cieco.

---

## 6. Le probabilita' di classifica: descrizione, non validazione

| k | affermazione | n | media dichiarata | frequenza vera | Brier | Brier tasso base |
|---:|---|---:|---:|---:|---:|---:|
| 10 | scudetto | 100 | 0.050 | 0.050 | 0.0161 | 0.0475 |
| 10 | top 4 | 100 | 0.200 | 0.200 | 0.0484 | 0.1600 |
| 10 | retrocessione | 100 | 0.150 | 0.150 | 0.0889 | 0.1275 |
| 19 | scudetto | 100 | 0.050 | 0.050 | 0.0212 | 0.0475 |
| 19 | top 4 | 100 | 0.200 | 0.200 | 0.0480 | 0.1600 |
| 19 | retrocessione | 100 | 0.150 | 0.150 | 0.0712 | 0.1275 |
| 28 | scudetto | 100 | 0.050 | 0.050 | 0.0121 | 0.0475 |
| 28 | top 4 | 100 | 0.200 | 0.200 | 0.0388 | 0.1600 |
| 28 | retrocessione | 100 | 0.150 | 0.150 | 0.0443 | 0.1275 |

> **`media dichiarata` = `frequenza vera` e' un'IDENTITA', non un risultato.**
> In ogni replica c'e' esattamente un campione, quattro squadre nei primi quattro
> posti e tre retrocesse: le probabilita' sommano a quei numeri per costruzione,
> e la frequenza vera anche. Chi leggesse quella colonna come «il modello e'
> calibrato» leggerebbe un vincolo contabile. **La colonna che dice qualcosa e' il
> Brier accanto al tasso base**, ed e' migliore su tutte e tre le affermazioni e
> a tutte e tre le giornate.
>
> **E resta una descrizione.** Uno scudetto ha cinque realizzazioni in tutto, e
> le cento righe della tabella ne contengono cinque di indipendenti. Il vincolo di
> R0 e' questo, non e' aggirabile con piu' repliche Monte Carlo, e G2 lo
> porterebbe da 5 a 25 — **sottile, non sufficiente**, come R0 aveva gia' scritto.

---

## 7. Domande aperte

1. **Le probabilita' di classifica restano non validate**, e non per una
   mancanza di questo blocco: cinque realizzazioni non separano un modello da un
   altro. Chi volesse validarle deve portare campionati, non repliche.
2. **Gli scontri diretti non sono simulati.** Al confine dell'Europa e della
   retrocessione un pari merito compare nel 14% e nel
   16% delle repliche, quindi la semplificazione tocca una
   frazione non trascurabile dei casi. Il costo **non e' stato misurato**: per
   farlo servirebbe tenere la matrice degli incroci in ogni replica.
3. **La compressione agli estremi resta**, ed e' l'unica parte della
   sotto-dispersione di R2-bis che sopravvive alla partenza dalla classifica
   vera: l'ultima in classifica e' prevista troppo forte di una decina di punti.
   E' lo stesso segno gia' misurato in Fase 3, Fase 4 e 6A, e **non va corretto
   ritoccando lo shrinkage** — sarebbe la quarta volta che il progetto rifiuta
   quella strada.
4. **La convenzione ordinale su `k`** e' dichiarata e non dimostrata equivalente
   alla lettura in tempo reale: l'1,3% delle partite si gioca fuori dall'ordine
   della propria giornata, e per quelle la classifica di partenza usata qui e'
   piu' informata di quanto un osservatore alla giornata `k` avrebbe.
