# Fase 10 / Blocco R2-bis — la sotto-sicurezza su 1X2: da dove viene, e se si toglie

> Generato da `scripts/run_fase10_r2bis.py` il 2026-08-08.
> **Nessuna richiesta di rete.** A differenza di R2, **questo blocco stima**: la
> ricalibrazione ha parametri, e sono walk-forward.

---

## 0. Perche' adesso, e non dopo R3

R2 ha misurato che il modello e' **sotto-sicuro** su 1X2 — pendenza 1,223 sulla
classe `1` e 1,324 sulla `2`, cioe' sopra 1.0 — e ha lasciato la spiegazione
come domanda aperta n. 1, indicando la **compressione della ridge** della Fase 6A
come ipotesi compatibile e non misurata.

**Su una partita sola un errore di calibrazione resta piccolo e locale. R3 lo
propaga.** Una simulazione di stagione somma le stesse probabilita' su 38 turni,
e cio' che esce non e' una previsione di partita ma una distribuzione di scudetto
e di retrocessione — cioe' due **code**. Un errore sistematico nel verso della
compressione non si annulla sommandosi: sposta tutta la distribuzione simulata
verso il centro, ed e' esattamente il punto in cui R3 pubblica.

Il blocco tiene separate due domande che e' facile confondere:

| | domanda | risposta |
|---|---|---|
| **§2** | la sotto-sicurezza **viene** dalla compressione della ridge? | **no**: il controllo diretto la rifiuta a otto errori standard |
| **§3** | si **toglie** con una ricalibrazione walk-forward? | **si', con Platt**, e senza peggiorare l'RPS |
| **§4** | dopo la ricalibrazione, R3 e' al sicuro? | **no**, e §4 dice di quanto |

> **Che §3 funzioni non e' una conferma di §2.** Una ricalibrazione corregge il
> sintomo qualunque sia la causa: e' una mappa monotona stimata sull'errore
> osservato, e non sa da dove l'errore venga. Le due sezioni possono dare — e
> danno — esiti opposti.

---

## 1. La de-compressione, e perche' e' *quella* trasformazione

L'ipotesi della Fase 6A dice una cosa precisa: la penalita' ridge comprime
`attacco` e `difesa` verso zero e **non tocca `mu`**. Quello che risulta
compresso e' il **divario** fra le due squadre, non il livello del campionato.
L'inverso esatto e' quindi

```
d  = log(lam_casa) - log(lam_trasferta)        il divario
d' = k * d                                     k > 1 allarga
```

con i due lambda ricostruiti in modo che il **prodotto resti invariato**. Le tre
identita' sono verificate e non lasciate all'intenzione
(`verifica_decompressione`): `k = 1` e' l'identita' (True),
il divario e' scalato per `k` esatto (True), il
prodotto non si muove (True, scarto massimo
3.6e-15).

La de-compressione passa poi per la **stessa** `risultato.congiunta` di R2 con lo
stesso `rho = 0`: cambia il lambda e nient'altro, altrimenti si misurerebbe la
composizione. A `k = 1` le probabilita' coincidono con le `modello|p*` di R2 a
ogni cifra, e un test lo pretende.

**Il riferimento della 6A e' dichiarato per quello che e'**: pendenza 0,760, cioe'
`k = 1.316`. E' misurata sui **tiri in porta del 2025-26**, non
sui gol delle cinque stagioni: entra come ordine di grandezza dell'ipotesi, non
come misura di questo modello.

---

## 2. L'ipotesi: il verso e' giusto, e proprio per questo si vede che e' sbagliata

### 2.1 La de-compressione che calibra il 1X2 e' quasi quella che la 6A prevede

| k | pendenza 1 | z 1 | pendenza X | z X | pendenza 2 | z 2 | P(X) media | RPS | log-loss | Brier O2.5 | pendenza gol | z gol |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 0.7000 | 1.759 | 5.544 | 1.241 | 0.616 | 1.907 | 6.251 | 0.260 | 0.2078 | 1.0191 | 0.2524 | 1.051 | 0.775 |
| 0.8500 | 1.446 | 3.957 | 1.124 | 0.359 | 1.566 | 4.747 | 0.256 | 0.2055 | 1.0123 | 0.2526 | 0.977 | -0.400 |
| 1.0000 | 1.223 | 2.333 | 0.966 | -0.113 | 1.324 | 3.207 | 0.251 | 0.2041 | 1.0081 | 0.2529 | 0.898 | -1.966 |
| 1.1500 | 1.055 | 0.670 | 0.805 | -0.767 | 1.143 | 1.632 | 0.245 | 0.2035 | 1.0067 | 0.2534 | 0.823 | -3.791 |
| 1.3158 | 0.912 | -1.223 | 0.648 | -1.669 | 0.988 | -0.153 | 0.239 | 0.2036 | 1.0081 | 0.2544 | 0.749 | -6.008 |
| 1.4500 | 0.819 | -2.802 | 0.543 | -2.520 | 0.888 | -1.633 | 0.233 | 0.2042 | 1.0116 | 0.2554 | 0.695 | -7.908 |
| 1.6000 | 0.732 | -4.625 | 0.448 | -3.592 | 0.795 | -3.330 | 0.227 | 0.2053 | 1.0181 | 0.2570 | 0.642 | -10.112 |
| 1.8000 | 0.637 | -7.165 | 0.350 | -5.216 | 0.694 | -5.667 | 0.218 | 0.2075 | 1.0310 | 0.2596 | 0.581 | -13.142 |

Il `k` che porta ciascuna classe esattamente a 1.0, cercato come **radice** e non
letto dal minimo di una griglia — un `argmin` su una griglia dichiarata
restituirebbe un punto della griglia e farebbe sembrare una coincidenza cio' che
e' solo la spaziatura scelta:

| classe | k |
|---|---:|
| 1 | 1.2093 |
| X | 0.9692 |
| 2 | 1.3018 |

**La `1` chiede 1.209 e la `2` chiede 1.302, contro i
1.316 che l'ipotesi prevede.** Verso giusto, taglia quasi
giusta: se ci si fermasse qui, l'ipotesi della compressione sarebbe confermata.

La `X` chiede 0.969, cioe' di **stringere** invece che di allargare, ma va
detto per quello che e': a `k = 1` la sua pendenza vale 0,966 con
z = −0,11, cioe' **non e' distinguibile da calibrata**, e allargare non la rompe
in modo leggibile (z = -1.67
al `k` del riferimento). Che i tre `k` non coincidano e' **coerente** con «non e'
una compressione sola», non e' una prova.

**La conclusione non dipende da quale pezzo della de-compressione si applica**, ed
e' il controllo che rende la sezione qualcosa di piu' di una parametrizzazione
fortunata. Il modo semplice scala anche il **vantaggio del campo**, che sta dentro
il divario e non e' un effetto di squadra compresso dalla ridge; il modo `pieno`
e' invece l'inverso **letterale** della penalita' — allarga lo scarto di ciascun
lato dal `mu` stimato sul solo passato, cioe' anche la somma dei due lati:

| modo | k che calibra 1 | k che calibra X | k che calibra 2 | pendenza gol a quel k | z gol |
|---|---:|---:|---:|---:|---:|
| divario | 1.2093 | 0.9692 | 1.3018 | 0.755 | -5.81 |
| divario_netto | 1.2120 | 0.9605 | 1.3075 | 0.771 | -5.34 |
| pieno | 1.2147 | 0.9763 | 1.3047 | 0.698 | -7.54 |

### 2.2 Il controllo diretto, che viene da E3 e non da qui, la esclude

C'e' un numero che misura la compressione **senza passare dall'esito**, e nessuno
lo aveva messo accanto alla pendenza 1X2: la pendenza di calibrazione **sui gol**.
La relazione e' esatta — se i lambda fossero compressi di un fattore `c`, quella
pendenza varrebbe `1/c` — quindi l'ipotesi della 6A non prevede genericamente
«sopra 1»: prevede **1.316**.

| voce | valore | errore standard | z |
|---|---:|---:|---:|
| pendenza sui gol, osservata | 0.8982 | 0.0518 | -1.97 |
| pendenza che l'ipotesi 6A prevede (1 / 0,760) | 1.3158 | — | -8.07 |
| compressione minima visibile a potenza 80% | 0.8733 | — | — |

- **Osservata 0.898 ± 0.052**,
  cioe' z = -1.97 contro 1.0: se mai, i lambda sono un po'
  troppo **estremi**, che e' il verso opposto alla compressione.
- **Contro il valore che l'ipotesi prevede, z = -8.07.**
  Non e' un negativo debole: e' un rifiuto a otto errori standard.
- **E non e' mancanza di potenza** (lezione della 6D): una compressione fino a
  0.873 — cioe' del 13% —
  sarebbe stata vista con probabilita' 80%. La 6A ne dichiara una del 24%.

**Ne segue il fatto centrale della sezione: la stessa trasformazione che calibra
l'esito scalibra la grandezza da cui l'esito e' costruito.** Al `k` del
riferimento la pendenza sui gol scende da 0.898
(z = -1.97) a 0.749
(z = -6.01). Non e' un pareggio fra due diagnostiche: e' una
che si sistema e una che si rompe.

> **L'ipotesi della compressione della ridge e' quindi da abbandonare come
> *causa*, pur restando una buona *descrizione* del sintomo.** E' una distinzione
> che questo progetto ha gia' incontrato: coincidere in taglia non e' spiegare.
> La coincidenza fra `k = 1.316` e il `k` che calibra il 1X2 va
> registrata come tale, come la 6A ha registrato che `como_context` valesse 4,9041
> contro un'ancora di 4,90 senza che le due grandezze avessero un legame.

### 2.3 Cosa c'e' al posto: il deficit di pareggi

La colonna `P(X) media` della griglia dice dove finisce la massa quando si
allarga il divario, e la risposta e' **i pareggi**, che gia' scarseggiano:

| stagione | n | P(X) dichiarata | X osservati | deficit | se binomiale | pareggi mancanti |
|---|---:|---:|---:|---:|---:|---:|
| 2021-2022 | 323 | 0.2317 | 0.2632 | 0.0314 | 0.0245 | 10.1 |
| 2022-2023 | 325 | 0.2537 | 0.2492 | -0.0045 | 0.0240 | -1.5 |
| 2023-2024 | 330 | 0.2515 | 0.2970 | 0.0454 | 0.0252 | 15.0 |
| 2024-2025 | 330 | 0.2475 | 0.2697 | 0.0222 | 0.0244 | 7.3 |
| 2025-2026 | 330 | 0.2687 | 0.2576 | -0.0112 | 0.0241 | -3.7 |
| **tutte** | 1638 | 0.2507 | 0.2674 | 0.0167 | 0.0109 | 27.3 |

Il modello dichiara 0.2507 di pareggi
contro 0.2674 osservati:
**27 pareggi
mancanti** su 1,638 partite.
**E' la firma della composizione, non del lambda**: due Poisson indipendenti
producono meno pareggi di quanti se ne osservino, ed e' la ragione per cui la
correzione di Dixon-Coles esiste.

> **Il deficit da solo non e' significativo, e va scritto cosi'.**
> 0.0167 contro un errore
> standard binomiale di 0.0109
> fa 1,5 errori standard, e il segno cambia in due stagioni su cinque. **Non e'
> la prova di un difetto della composizione**: e' la direzione in cui la
> ricalibrazione di §3 si muove — dove il segnale si accumula su quattro
> stagioni di addestramento — e vale come indizio coerente, non come misura.

> **E qui R1 aveva gia' detto la sua**, e le due letture si incastrano. R1 ha
> misurato `rho = 0` e — questo e' il punto — che lo scostamento presente ha la
> forma «**meno 0-0 e piu' 1-1**», che **nessun valore di `rho` puo' produrre**,
> perche' un `rho` solo lega quelle due celle allo stesso verso. Il deficit di
> pareggi resta li', non e' un problema di livello dei lambda, e la forma di
> Dixon-Coles non e' lo strumento per toglierlo. **Non e' stato tolto**:
> inventare qui una seconda forma di dipendenza su 1.638 partite sarebbe
> adattarsi al rumore, ed e' la domanda aperta n. 2 di R1 — quella per cui G2
> avrebbe la massa.

---

## 3. La ricalibrazione: si toglie, e con che cosa

**Il criterio di adozione e' scritto prima di guardare i numeri**, in
`CRITERIO_ADOZIONE`, e `verdetto()` lo applica meccanicamente — un criterio
dichiarato che poi si applica a occhio non e' un criterio dichiarato:

> (a) porta |z vs 1.0| sotto 2 su TUTTE E TRE le classi; (b) non peggiora l'RPS oltre il rumore (differenza appaiata sotto il proprio MDE); a parita', il piu' semplice secondo l'ordine di METODI

**La stima e' walk-forward** (vincolo 1): il mappatore della stagione `s` si
addestra su tutte le partite delle stagioni precedenti e su nient'altro. La
**2021-2022 non ha un passato** e resta non ricalibrata — non si riempie con il
mappatore di un'altra stagione e non si toglie dal campione: si marca, e il
confronto gira sulle 1315 righe marcate. Due test guastano i
dati per verificarlo: rovesciare l'ultima stagione non deve muovere **nessun**
parametro, rovesciare la prima deve muovere i successivi.

| metodo | n | pendenza 1 | z 1 | pendenza X | z X | pendenza 2 | z 2 | RPS | log-loss | delta RPS | t | MDE (80%) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| modello (R2, non ricalibrato) | 1315 | 1.210 | 1.98 | 0.994 | -0.02 | 1.393 | 3.42 | 0.2030 | 1.0047 | 0.00000 | — | — |
| temperatura | 1315 | 1.189 | 1.81 | 0.975 | -0.07 | 1.362 | 3.23 | 0.2027 | 1.0041 | -0.00025 | -2.27 | 0.00031 |
| platt | 1315 | 1.028 | 0.31 | 0.743 | -0.89 | 1.186 | 1.89 | 0.2021 | 1.0020 | -0.00090 | -1.79 | 0.00141 |
| isotonica | 1315 | 0.655 | -4.63 | — | — | 0.854 | -1.77 | 0.2038 | 1.0324 | 0.00079 | 0.77 | 0.00287 |

| metodo | pendenza ok | RPS non peggiorato | adottabile |
|---|---:|---:|---:|
| temperatura | no | si | no |
| platt | si | si | si |
| isotonica | no | si | no |

**Adottato: `platt`.**

- **La temperatura non basta.** Un parametro solo, stimato fra
  323 e 1,308 partite di
  passato, vale `T` fra 0,93 e 1,02: affila appena, e lascia la classe `2` a
  z = +3.23. **Ed e' il secondo argomento contro
  l'ipotesi di §2**: se il difetto fosse «tutte le probabilita' troppo vicine al
  centro», una manopola che le allarga tutte insieme lo toglierebbe. Non lo
  toglie, perche' il difetto non e' simmetrico fra le tre classi.
- **Platt per classe funziona**, e si vede *cosa* fa dai coefficienti stimati:
  l'intercetta sulla `X` e' **positiva in tre stagioni su quattro**, cioe' il
  mappatore passa il suo tempo ad **aggiungere pareggi** — che e' §2.3 letto
  dall'altro lato.
- **L'isotonica sovra-corregge** (z = -4.63 sulla
  classe `1`) e **peggiora** l'RPS. Sulla `X` la sua pendenza non e' nemmeno
  identificata: la mappa monotona collassa quasi a una costante e il logit non
  ha piu' varianza su cui stimare — lo stesso `nan` dichiarato che R2 e la
  Fase 4 restituiscono su `media campionato`, e per la stessa ragione. E' cio'
  che ci si aspetta da tre gradi di liberta' liberi su qualche centinaio di
  righe, ed e' il motivo per cui l'ordine di semplicita' era dichiarato prima.
- **L'RPS non peggiora, e nemmeno migliora in modo leggibile**: Platt lo sposta
  di -0.00090 con t = -1.79
  contro un MDE di 0.00141. **La ricalibrazione
  compra calibrazione, non accuratezza**, ed e' cio' che ci si deve aspettare da
  una mappa monotona: non riordina niente.

I coefficienti stimati, stagione per stagione:

| stagione | n_training | parametro |
|---|---:|---|
| 2021-2022 | 0 | — (senza passato sufficiente) |
| 2022-2023 | 323 | 1: a=-0.048 b=1.278 · X: a=+0.454 b=1.239 · 2: a=+0.024 b=1.079 |
| 2023-2024 | 648 | 1: a=-0.068 b=1.167 · X: a=-0.102 b=0.847 · 2: a=+0.137 b=1.128 |
| 2024-2025 | 978 | 1: a=-0.073 b=1.191 · X: a=+0.137 b=1.009 · 2: a=+0.175 b=1.244 |
| 2025-2026 | 1308 | 1: a=-0.039 b=1.212 · X: a=+0.290 b=1.149 · 2: a=+0.165 b=1.279 |

---

## 4. Quanto costa a R3, misurato al livello di R3

Una pendenza di calibrazione e' una diagnostica **per partita**. La domanda che
ha motivato il blocco e' un'altra — **la classifica simulata si disperde quanto
il modello dice?** — e ha una forma falsificabile:

```
var(punti osservati fra le squadre) = var(punti ATTESI) + media(varianza di campionamento)
```

Il primo termine e' quanto il modello crede che le squadre differiscano; il
secondo e' quanta fortuna il modello stesso ammette. Se la somma sta **sotto**
l'osservato, il modello sotto-dichiara la separazione, e una classifica simulata
esce **troppo corta**.

| stagione | squadre | var osservata | var attesa | var campionamento | attesa + campionamento | rapporto |
|---|---:|---:|---:|---:|---:|---:|
| 2021-2022 | 20 | 0.2155 | 0.0795 | 0.0494 | 0.1289 | 1.672 |
| 2022-2023 | 20 | 0.2253 | 0.0793 | 0.0466 | 0.1259 | 1.790 |
| 2023-2024 | 20 | 0.2503 | 0.0765 | 0.0463 | 0.1228 | 2.038 |
| 2024-2025 | 20 | 0.2958 | 0.0881 | 0.0465 | 0.1346 | 2.197 |
| 2025-2026 | 20 | 0.2257 | 0.0539 | 0.0473 | 0.1012 | 2.230 |

**Il rapporto vale 1.99 in media e sta sopra 1 in tutte
e cinque le stagioni.** In unita' leggibili: la deviazione standard dei punti per
partita fra le venti squadre e' 0.492
osservata contro 0.350 dichiarata
— su 38 giornate, circa **19 punti
di dispersione contro 13**.

> **La misura e' stata verificata su dati in cui la risposta e' nota**, ed e'
> l'unico modo di distinguere un difetto del modello da un difetto della misura:
> generando gli esiti **dalle probabilita' del modello** — dove per costruzione
> il modello e' perfettamente calibrato — il rapporto torna attorno a 1. Un test
> lo pretende.

**Il burn-in ne spiega una parte, e non tutta.** I lambda sono walk-forward:
alla settima giornata il modello sa poco, e una previsione onestamente incerta
abbassa la dispersione dei punti attesi senza che nulla sia mal calibrato. R3
pero' simula **il resto** di una stagione da una giornata avanzata, quindi cio'
che conta e' la seconda meta':

| perimetro | partite | stagioni | var osservata | var attesa + camp. | rapporto medio | stagioni con rapporto > 1 |
|---|---:|---:|---:|---:|---:|---:|
| 1a meta' (giornata <= 19) | 690 | 5 | 0.3316 | 0.1767 | 1.873 | 5 |
| 2a meta' (giornata > 19) | 947 | 5 | 0.2489 | 0.1751 | 1.419 | 5 |

Scende da 1.87 a
1.42 e **non si chiude**: la parte che
resta e' una proprieta' del modello, e R3 la eredita.

**E la ricalibrazione la riduce senza chiuderla:**

| variante | stagioni | var osservata | var attesa + camp. | rapporto medio | stagioni con rapporto > 1 |
|---|---:|---:|---:|---:|---:|
| modello (R2) | 4 | 0.2493 | 0.1211 | 2.064 | 4 |
| temperatura | 4 | 0.2493 | 0.1241 | 2.007 | 4 |
| platt | 4 | 0.2493 | 0.1396 | 1.787 | 4 |
| isotonica | 4 | 0.2493 | 0.1591 | 1.570 | 4 |

> **Questo non e' un difetto di calibrazione, ed e' importante non chiamarlo
> cosi'.** Lo scarto e' la parte delle differenze **vere** fra squadre che il
> modello non ha catturato — piu' qualunque shock che duri piu' di una partita e
> che quindi si correli lungo la stagione, che l'identita' assume assente. Una
> mappa monotona sulle probabilita' di partita non puo' restituirla: sposta la
> massa dentro ogni riga, non aggiunge separazione fra le squadre.

---

## 5. Cosa consegna a R3

1. **Le probabilita' ricalibrate con Platt walk-forward** sono la previsione da
   propagare: `ricalibrazione.walkforward_ricalibrazione(metodo="platt")`. La
   2021-2022 resta non ricalibrata e va contata come tale, non riempita.

   > **Il prezzo, dichiarato: dopo Platt il modello non e' piu' internamente
   > coerente.** Le tre probabilita' 1X2 non escono piu' dalla **stessa**
   > congiunta che produce l'over/under — una mappa per classe piu' una
   > rinormalizzazione non corrisponde a nessuna distribuzione sui punteggi. R3
   > usa solo l'esito e quindi non lo paga; **un blocco che volesse 1X2 e
   > over/under insieme lo pagherebbe**, e non deve prendere la ricalibrazione
   > per buona senza rifare la domanda. E' la ragione per cui `esiti.py` resta
   > com'e' e la ricalibrazione vive in un modulo suo.
2. **La sotto-dispersione della classifica va DICHIARATA e, se possibile,
   modellata.** Simulare la stagione con le sole probabilita' di partita — anche
   ricalibrate — produce una classifica troppo corta di circa un terzo in
   varianza: campioni troppo deboli, ultime troppo forti, code delle
   distribuzioni di scudetto e retrocessione troppo grasse. **E' un limite da
   scrivere accanto ai numeri (vincolo 5), non in fondo.**
3. **Cio' che NON va fatto** e' correggere lo shrinkage finche' la pendenza torna
   a 1.0. §2 mostra che la de-compressione paga la calibrazione dell'esito con
   quella dei gol e con i pareggi; sarebbe far tornare un numero cambiando la
   definizione (vincolo 2).

---

## 6. Domande aperte

1. **Da dove venga la sotto-sicurezza resta senza una causa misurata.**
   Sull'ipotesi della ridge la risposta e' netta e negativa (§2.2, z = −8,1
   contro il valore che prevede, con la potenza dichiarata). Cio' che il blocco
   propone al suo posto — il deficit di pareggi — **e' un indizio e non una
   misura**: 1,5 errori standard, segno che cambia in due stagioni su cinque. E
   non avrebbe comunque una correzione disponibile: la forma di Dixon-Coles e'
   gia' stata provata da R1 e non e' quella giusta. **La domanda aperta n. 1 di
   R2 e' cambiata, non chiusa**: non e' piu' «e' la ridge?» — non lo e' — ma
   «quale forma di dipendenza produce meno `0-0` e piu' `1-1`», che su 1.638
   partite non si puo' cercare senza adattarsi al rumore.
2. **La sotto-dispersione della classifica non e' spiegata**, ed e' piu' grande
   di quanto la calibrazione per partita lasciasse prevedere. Le due candidate —
   varianza vera fra squadre non catturata dal modello, e shock correlati lungo
   la stagione — **non sono state separate**, e separarle vuole un modello con
   un effetto di squadra persistente, cioe' un blocco a se'.
3. **Il criterio di adozione ha una potenza dichiarata e piccola.** L'MDE su RPS
   vale 0.00141: la condizione «non peggiora
   l'RPS» esclude peggioramenti grandi, non peggioramenti piccoli. Va letta come
   il negativo che e'.
4. **La ricalibrazione e' stimata su tre stagioni di passato al massimo**, e la
   sua granularita' e' la stagione. Rifittarla per giornata userebbe piu' dati e
   sarebbe un secondo modello che si muove sopra al primo: non e' stato fatto, e
   non e' stato misurato quanto costi non farlo.
