# Fase 10 / Blocco R1 — la distribuzione congiunta del risultato

> Generato da `scripts/run_fase10_r1.py` il 2026-08-07.
> **Nessuna richiesta di rete.** Si stima **un parametro solo**, `rho`, a
> marginali fissate: i lambda di E3.1 entrano come dati e non vengono ristimati.

---

## 1. Precondizione — le partite che mancano alla fonte sono a caso rispetto al risultato?

> Richiesto dall'utente il 2026-08-07, **prima** della congiunta e non dopo: se
> il bersaglio ha un buco non casuale su due squadre, ogni numero che segue lo
> eredita.

**Non e' la domanda a cui l'acquisizione ha gia' risposto.** Li' si chiedeva se
le partite mancassero a caso rispetto alla **squadra**, e la risposta era no —
l'Atalanta ne perde sei contro un'attesa di 1,2, p corretto 1,1%. Qui si chiede,
**data** la squadra, se manchino a caso rispetto all'**esito**.

La domanda e' rispondibile per una ragione sola: di una partita che WhoScored non
ha, **il risultato ce l'abbiamo lo stesso**, dalla fonte dei voti, che ha tutte
e 380 le partite di ogni stagione con i gol mai nulli.

| stagione | giornata | casa | trasferta | gol_casa | gol_trasferta |
|---|---:|---|---|---:|---:|
| 2021-2022 | 4 | Salernitana | Atalanta | 0 | 1 |
| 2021-2022 | 10 | Napoli | Bologna | 3 | 0 |
| 2021-2022 | 11 | Atalanta | Lazio | 2 | 2 |
| 2021-2022 | 11 | Sassuolo | Empoli | 1 | 2 |
| 2021-2022 | 12 | Cagliari | Atalanta | 1 | 2 |
| 2021-2022 | 12 | Napoli | Verona | 1 | 1 |
| 2022-2023 | 6 | Napoli | Spezia | 1 | 0 |
| 2022-2023 | 12 | Empoli | Atalanta | 0 | 2 |
| 2022-2023 | 18 | Cremonese | Monza | 2 | 3 |
| 2022-2023 | 28 | Cremonese | Atalanta | 1 | 3 |
| 2022-2023 | 29 | Verona | Sassuolo | 2 | 1 |
| 2022-2023 | 33 | Atalanta | Spezia | 3 | 2 |

Il test e' una **permutazione esatta a due code**: sotto il nullo le mancanti
sono un campione casuale senza reinserimento delle partite che quella squadra ha
giocato in quelle stagioni. Due code perche' il verso non era previsto.

| squadra | mancanti | record | punti_oss | punti_atteso | punti_p | gf_p | gs_p | casa_p |
|---|---:|---|---:|---:|---:|---:|---:|---:|
| Atalanta | 6 | V5P1S0 | 2.67 | 1.62 | 0.0554 | 0.481 | 0.536 | 0.437 |
| Napoli | 3 | V2P1S0 | 2.33 | 2.22 | 1.0000 | 0.827 | 0.541 | 0.241 |
| Cremonese | 2 | V0P0S2 | 0.00 | 0.71 | 0.5482 | 0.431 | 0.247 | 0.487 |
| Empoli | 2 | V1P0S1 | 1.50 | 1.11 | 0.9036 | 1.000 | 1.000 | 1.000 |
| Sassuolo | 2 | V0P0S2 | 0.00 | 1.25 | 0.2672 | 0.768 | 0.746 | 1.000 |
| Spezia | 2 | V0P0S2 | 0.00 | 0.82 | 0.3754 | 1.000 | 0.738 | 0.489 |
| Verona | 2 | V1P1S0 | 2.00 | 1.11 | 0.4245 | 1.000 | 0.547 | 1.000 |

**Sui punti l'Atalanta e' anomala: V5P1S0 in sei partite**, cioe'
2.67 punti a partita contro 1.62 attesi,
p = 0.0554 grezzo. **Non sopravvive alla molteplicita'**: sono
7 squadre testate, la soglia di Bonferroni vale 0.0071 e il p
corretto e' circa 0.39.

**Ma la grandezza che conta qui non sono i punti, sono i gol** — R1 compone una
distribuzione di **gol**, e il modello di E3.1 e' stimato sui gol. Li' non c'e'
niente:

| grandezza | osservata | attesa | p (2 code) |
|---|---:|---:|---:|
| punti | 2.67 | 1.62 | **0.0554** |
| gol fatti | 2.17 | 1.72 | 0.481 |
| gol subiti | 1.00 | 1.26 | 0.536 |
| quota in casa | 0.33 | 0.50 | 0.437 |

**E il meccanismo che spiega la divergenza e' aritmetico, non statistico.** I
punti sono una funzione **a gradini** dei gol: vincere 5 partite su 6 segnando
2.17 gol e subendone 1.00 e' del tutto ordinario in
gol e straordinario in punti. Il vantaggio nei gol e' modesto (+1.17
di differenza reti a partita) e la soglia lo amplifica.

**La potenza e' dichiarata, ed e' il punto piu' importante della sezione** (e' la
lezione della 6D): con **sei** partite il test vede pochissimo.

| grandezza | scarto rilevabile (MDE, 2 code 5%) | scarto osservato |
|---|---:|---:|
| gol fatti | +1.28 a partita | +0.44 |
| punti | +1.05 a partita | +1.05 |

Sui punti **l'osservato coincide con la soglia a ogni cifra**
(1.0482 contro 1.0482): l'effetto sta esattamente
sul limite di rilevabilita', ed e' un altro modo di leggere il p = 0.055.
Sui gol servirebbe uno scarto di +1.28 gol a partita per essere
visto, e ce n'e' +0.44.

> **Verdetto, e va letto per intero.** Sul bersaglio che R1 usa — i **gol** — non
> c'e' nessuna non-casualita' dimostrata, e su nessuna delle sette squadre
> testate. Sui **punti** l'Atalanta ha un punto stimato anomalo che **non
> sopravvive alla correzione per molteplicita'** e che sta esattamente sul limite
> di rilevabilita' del test. **Non e' un via libera e non e' un allarme**: e' un
> segnale in una direzione coerente, su sei partite, che i dati non permettono di
> confermare ne' di escludere. **R1 procede, e il limite resta dichiarato qui.**
>
> **Una cosa che il buco NON tocca**: l'esito di R3. La classifica finale si
> ricostruisce dal calendario completo della fonte dei voti, che non ha buchi.
> Il buco e' nell'**ingresso** del modello, non nel bersaglio contro cui lo si
> misurerebbe.

---

## 2. Perche' serve un parametro in piu'

E3.1 consegna due **marginali**: il lambda dei gol di ciascun lato. Un esito 1X2
non e' una marginale — e' una funzione della **congiunta**, e **le marginali non
determinano la congiunta**. Moltiplicarle e' gia' una scelta: e' l'ipotesi di
indipendenza, presa senza dichiararla. Questo blocco la rende un parametro.

La forma e' quella di Dixon-Coles: `tau` vale 1 ovunque tranne nelle quattro
celle dei punteggi bassi, dove sta il fenomeno noto (due squadre sullo 0-0
all'80' non giocano come sullo 0-0 al 10'). **`rho = 0` e' l'indipendenza**, ed e'
il nullo di ogni test qui.

**La verifica falsificabile del blocco**: le marginali della congiunta devono
restare le due Poisson di partenza, a `rho` qualsiasi.

| | |
|---|---:|
| scarto sulla marginale di casa | 5.55e-17 |
| scarto sulla marginale di trasferta | 0.00e+00 |
| massa persa dal troncamento a 12 gol (max sui lambda veri) | 2.91e-05 |
| la stessa, in media sulle partite | 2.37e-07 |

**Zero a ogni cifra, ed e' algebra e non fortuna numerica**: sulla riga `x = 0` la
variazione delle due celle toccate e'
`P(0;c)P(0;t)·(−c·t·rho) + P(0;c)P(1;t)·(c·rho)`, e con `P(1;t) = t·P(0;t)` i due
termini si cancellano. La forma di Dixon-Coles e' costruita per spostare massa
**dentro** l'angolo senza toccare i totali di riga e colonna.

> La docstring di `verifica_marginali` affermava il contrario — che restasse un
> residuo dell'ordine di `rho·lam` — finche' la funzione non l'ha misurato e non
> ha restituito zero. **E' la verifica che ha corretto la prosa**, ed e' il motivo
> per cui e' scritta come misura e non come commento.

---

## 3. La dipendenza misurata, per tre strade indipendenti

| strada | stima | statistica | p |
|---|---:|---:|---:|
| MLE su `rho` (verosimiglianza) | -0.0087 | LR = 0.077 | 0.781 |
| frequenza delle 4 celle (senza modelli) | — | chi2 = 6.35 su 4 gdl | 0.175 |
| correlazione dei residui (senza `tau`) | +0.0263 | — | 0.288 |

**Nessuna delle tre trova niente**, e non misurano la stessa cosa per strade
equivalenti: la seconda non passa da nessuna ottimizzazione, la terza non usa
nemmeno la forma di Dixon-Coles.

Le cinque stagioni, separate — cinque stime indipendenti che **cambiano segno**:

| stagione | n | rho | lr | p_lr |
|---|---:|---:|---:|---:|
| 2021-2022 | 323 | -0.0629 | 0.960 | 0.327 |
| 2022-2023 | 325 | 0.0643 | 0.734 | 0.391 |
| 2023-2024 | 330 | -0.0275 | 0.147 | 0.701 |
| 2024-2025 | 330 | -0.0304 | 0.196 | 0.658 |
| 2025-2026 | 330 | 0.0383 | 0.262 | 0.608 |

---

## 4. Lo scostamento che c'e' non ha la forma di Dixon-Coles

E' il risultato che il blocco non cercava, e spiega **perche'** l'MLE cade a zero
invece di limitarsi a dire che ci cade.

| cella | osservate | attese | z | verso osservato | verso di Dixon-Coles (rho>0) |
|---|---:|---:|---:|---|---|
| 0-0 | 110 | 128.5 | -1.71 | giu | giu |
| 0-1 | 139 | 146.7 | -0.67 | giu | su |
| 1-0 | 176 | 170.9 | 0.41 | su | su |
| 1-1 | 211 | 189.4 | 1.67 | su | giu |

**2 celle su 4 vanno nel verso opposto a quello che Dixon-Coles impone.**
Con un `rho` solo, la forma classica lega le quattro celle: `(0,0)` e `(1,1)` si
muovono **insieme**, e qui vanno in direzioni opposte — meno 0-0 e piu' 1-1 del
previsto. **Nessun valore di `rho` puo' produrre quel disegno**, quindi l'MLE non
ha modo di allontanarsi da zero: lo scostamento presente e' **ortogonale** a cio'
che il parametro sa esprimere.

E lo scostamento, di suo, **non e' significativo**: chi2 = 6.35 su 4 gdl,
p = 0.175. Quindi non e' che ci sia una dipendenza di forma diversa e noi
usiamo il modello sbagliato: e' che con 1638 partite non si distingue niente
dall'indipendenza, **in nessuna delle due forme**.

---

## 5. La potenza, che e' cio' che rende il negativo leggibile

Un `rho` non distinguibile da zero non dice che la dipendenza sia zero, finche'
non si sa quanto grande dovesse essere per essere vista. Simulando risultati
**dalla congiunta con `rho` vero** e contando i rifiuti:

| rho_vero | potenza | repliche |
|---:|---:|---:|
| 0.020 | 0.110 | 200 |
| 0.050 | 0.355 | 200 |
| 0.080 | 0.720 | 200 |
| 0.120 | 0.990 | 200 |
| 0.200 | 1.000 | 200 |

**La potenza dell'80% cade intorno a `rho` = 0,09**, e a 0,12 il test rifiuta
quasi sempre. Il campione **non e'** cieco: esclude dipendenze di taglia media,
non solo enormi. Cio' che non escluderebbe e' un `rho` sotto 0,05, dove la
potenza e' del 36%.

---

## 6. Cosa consegna R1 a R2

**`rho = 0`, cioe' l'indipendenza condizionata ai lambda** — non come default
comodo ma come esito misurato, con la potenza dichiarata sopra.

Distribuzione degli esiti, osservata contro modello a `rho = 0`, sulle 1638
partite validabili:

| esito | osservata | modello (rho=0) |
|---|---:|---:|
| 1 | 0.4048 | 0.4233 |
| X | 0.2674 | 0.2507 |
| 2 | 0.3278 | 0.3260 |

E' la prima volta che il modello dei gol viene letto come previsione di
**risultato**, ed e' il materiale su cui R2 calcolera' RPS e log-loss contro i
baseline. **Qui non c'e' nessuna valutazione fuori campione**: questa e' una
media in campione, serve a mostrare che la composizione non e' sbilanciata, e
**non va citata come un risultato di accuratezza**.

> **Vincolo 1, per chi in futuro volesse un `rho` diverso da zero.** `rho` qui e'
> stimato **in campione**, ed e' lecito perche' e' usato come **limite
> superiore** — la direzione in cui 6D ha usato lo stesso genere di test. Se un
> blocco futuro volesse *usarlo* in previsione, va ristimato sul solo passato,
> come `walkforward_r` fa per `r`. Usare questo numero sarebbe stimare su dati
> che seguono il bersaglio.

---

## 7. Domande aperte

1. **Il buco dell'Atalanta resta non risolto, e non e' risolvibile qui.** Sei
   partite non bastano, e non ne arriveranno altre: la fonte non le ha. L'unica
   strada sarebbe un'altra fonte di dati evento per quelle sei, che e'
   un'acquisizione e non un'analisi.
2. **La dipendenza e' stata cercata solo nella forma di Dixon-Coles.** Lo
   scostamento osservato (meno 0-0, piu' 1-1) suggerisce una forma diversa, ma
   non e' significativo e inseguirlo su 1638 partite sarebbe adattarsi al
   rumore. Se G2 portasse altri campionati, e' la prima cosa che avrebbe massa
   per essere guardata.
3. **`rho` e' assunto costante fra partite.** Potrebbe dipendere dal divario di
   forza — le partite squilibrate non hanno la fase di studio che il meccanismo
   presuppone — e questo blocco non l'ha guardato.
4. **La correzione di Dixon-Coles originale ha un decadimento temporale**, qui
   assente perche' i lambda di E3.1 ce l'hanno gia' dentro. Che i due decadimenti
   debbano essere lo stesso non e' ovvio e non e' stato verificato.
