# Fase 12 / Blocco V4 — il ponte `previsione(squadra, avversario, campo)`

> Generato da `scripts/run_fase12_v4.py` il 2026-09-04.
> **Non tocca la rete e non scrive niente sotto `data/`.**

## 0. Che cosa questo blocco consegna

**E' la risposta alla domanda dell'utente**: dato in ingresso una squadra, un
avversario e il campo, la distribuzione del numero di tiri.

```python
from sot import previsione as P
p = P.previsione("Como", "Inter", "casa")
p["lambda_tentativi"]   # 12.852
p["p_over"]             # P(Over) per le cinque linee, con la quota di pareggio
p["intervalli"]         # 50 / 80 / 95%
```

Prima di V4 il progetto **non aveva** una funzione del genere per una squadra
qualsiasi: `soglie_2627` la aveva per il **solo Como** e per il **solo 2026-27**,
ancorata a un livello fornito dall'utente che per le altre diciannove squadre non
esiste. Qui il livello non serve, perche' la previsione e' **within-season**: il
modello sa gia' quanto tira ciascuna squadra perche' gliel'hanno detto le partite
precedenti. Ed e' l'unica forma **validabile** — V1 la misura su 3.278 righe.

## 1. La dispersione fra le coppie, che e' il motivo per cui il ponte serve

| | squadra | avversario | campo | tiri attesi |
|---|---|---|---|---:|
| minimo | Cremonese | Como | trasferta | **6.55** |
| massimo | Juventus | Cremonese | casa | **21.42** |

**Un fattore 3.27 fra la coppia piu' bassa e la piu' alta**, contro una
media di campionato di 12.31. Un numero unico per
squadra non basta, e nemmeno un numero per squadra piu' il campo: l'avversario
sposta il lambda quanto il campo.

## 2. Le venti squadre, medie sui diciannove avversari

| squadra | casa | trasferta | divario |
|---|---:|---:|---:|
| Juventus | 18.21 | 14.46 | 1.259 |
| Inter | 17.87 | 14.18 | 1.260 |
| Atalanta | 16.23 | 12.88 | 1.260 |
| Como | 15.92 | 12.63 | 1.260 |
| Roma | 14.56 | 11.56 | 1.260 |
| Napoli | 14.46 | 11.48 | 1.260 |
| AC Milan | 14.35 | 11.39 | 1.260 |
| Bologna | 14.06 | 11.16 | 1.260 |
| Fiorentina | 13.86 | 11.00 | 1.260 |
| Torino | 13.15 | 10.44 | 1.260 |
| Udinese | 12.91 | 10.25 | 1.260 |
| Cagliari | 12.90 | 10.24 | 1.260 |
| Genoa | 12.85 | 10.20 | 1.260 |
| Verona | 12.52 | 9.93 | 1.261 |
| Lazio | 12.34 | 9.80 | 1.259 |
| Sassuolo | 12.18 | 9.67 | 1.260 |
| Parma Calcio 1913 | 11.96 | 9.49 | 1.260 |
| Lecce | 11.39 | 9.04 | 1.260 |
| Pisa | 10.94 | 8.68 | 1.260 |
| Cremonese | 10.83 | 8.60 | 1.259 |

Il **divario casa/trasferta** e' quasi costante fra squadre ed e' il vantaggio
del campo del modello (x1.260):
il modello lo stima **una volta sola** per tutto il campionato, quindi le
differenze residue vengono solo dal fatto che ogni squadra affronta un insieme
diverso di avversari.

## 3. Un esempio letto per intero — Como contro l'Inter, in casa

| | |
|---|---:|
| tiri attesi | **12.852** |
| di cui in porta | 4.362 |
| precisione implicita | 33.9% |
| `r` (NB2) | 20.02 |
| stimato su | 380 partite, al 2026-05-24 |
| alpha | 25.0 |

| linea | p_over | quota_pareggio |
|---:|---:|---:|
| 8.5 | 0.8286 | 1.207 |
| 10.5 | 0.6739 | 1.484 |
| 12.5 | 0.4974 | 2.011 |
| 14.5 | 0.3332 | 3.001 |
| 16.5 | 0.2036 | 4.912 |

| livello | basso | alto |
|---:|---:|---:|
| 0.50 | 10 | 16 |
| 0.80 | 7 | 19 |
| 0.95 | 5 | 23 |

**L'intervallo all'80% e' largo 12 tiri**, ed e' il numero
che va guardato insieme al lambda: il modello prevede bene la *distribuzione* e
male il *numero*, ed e' esattamente cio' che V1 misura (MAE 3,57).

## 4. Como contro tutti, in casa e in trasferta

| avversario | campo | lambda_tentativi | lambda_sot | p_over_8.5 | p_over_10.5 | p_over_12.5 | p_over_14.5 | p_over_16.5 |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| Cremonese | casa | 18.61 | 5.95 | 0.972 | 0.927 | 0.850 | 0.741 | 0.611 |
| Sassuolo | casa | 18.14 | 5.86 | 0.967 | 0.917 | 0.832 | 0.716 | 0.581 |
| Parma Calcio 1913 | casa | 17.60 | 5.34 | 0.961 | 0.903 | 0.810 | 0.685 | 0.545 |
| Torino | casa | 17.50 | 5.64 | 0.960 | 0.901 | 0.805 | 0.679 | 0.538 |
| Fiorentina | casa | 17.48 | 5.67 | 0.960 | 0.900 | 0.804 | 0.678 | 0.537 |
| Pisa | casa | 17.37 | 5.76 | 0.958 | 0.897 | 0.800 | 0.672 | 0.530 |
| Verona | casa | 17.06 | 5.29 | 0.954 | 0.888 | 0.785 | 0.652 | 0.508 |
| Udinese | casa | 16.97 | 5.04 | 0.952 | 0.885 | 0.780 | 0.646 | 0.501 |
| Lazio | casa | 16.67 | 5.27 | 0.948 | 0.876 | 0.765 | 0.627 | 0.480 |
| Cagliari | casa | 16.16 | 5.53 | 0.938 | 0.857 | 0.737 | 0.592 | 0.443 |
| Genoa | casa | 16.14 | 5.33 | 0.938 | 0.857 | 0.736 | 0.591 | 0.441 |
| Lecce | casa | 15.99 | 5.30 | 0.935 | 0.851 | 0.728 | 0.580 | 0.430 |

*(prime dodici righe; la tabella completa delle 760 coppie e' in
`fase12_v4_tiri_attesi.csv`)*

## 5. Le guardie, esercitate

| guardia | solleva | messaggio |
|---|---|---|
| squadra non in stagione | si | squadre non presenti in 2025-2026: ['Venezia']. Presenti: ['AC M… |
| squadra == avversario | si | squadra e avversario coincidono: 'Como'… |
| campo non ammesso | si | campo 'fuori' non ammesso: usare uno di ('casa', 'trasferta'). U… |

**La guardia sulla squadra sconosciuta sta a due livelli, e servono entrambi.**
`verifica_squadre` protegge l'API; `TeamModel(strict_teams=True)` protegge il
modello, perche' una guardia sola all'ingresso si aggira chiamando il modello
direttamente — che e' il buco che `soglie_2627.difese_avversari` tappa per il
solo Como.

**Il difetto e' silenzioso**, ed e' la ragione per cui la guardia esiste:
`df["team"].map(idx)` da' `NaN`, la maschera salta la riga e la dummy resta a
zero, cioe' la squadra viene trattata **come esattamente media**, senza errore
ne' avviso. Il caso realistico non e' la squadra inventata: e' chiedere
**Como-Venezia nel 2025-2026**, dove il Venezia non c'era.

**`strict_teams` ha default `False`** e un test verifica che con quel default le
previsioni siano identiche bit per bit: dentro il walk-forward il coefficiente
zero e' il comportamento *giusto* — una squadra alla sua prima apparizione in un
training parziale — e sollevare romperebbe la Fase 2, E3 e R0-R3.

**`campo` e' una stringa e non un booleano**: un `0/1` si scambierebbe senza
rumore, e la differenza fra casa e trasferta vale un quarto del livello.

## 6. La pagina locale

`reports/fase12_v4_simulatore.html` — si sceglie squadra, avversario e campo e si
leggono lambda, precisione implicita, `P(Over)` per le cinque linee e la quota di
pareggio.

**E' autonoma**: nessun CDN, nessun font remoto, nessuna richiesta di rete, e un
test lo pretende — «pagina locale» vuol dire che funziona offline.

**Nessuna quota** (vincolo 3): la pagina mostra la quota di **pareggio**
(`1/p`), che e' il punto in cui il guadagno sarebbe zero, e lo dichiara come tale
invece di presentarlo come una previsione di prezzo. Non propone quote e non
calcola guadagni.

## 7. I limiti, accanto ai numeri

1. MAE 3,57 tiri per squadra-partita (V1, su 3.278 righe walk-forward): il numero puntuale non e' preciso, la distribuzione si'
2. sotto la 6a giornata la previsione e' dominata dall'intercetta e V1 non la valuta (burn-in dichiarato)
3. `r` e' assunta costante fra squadre e stagioni (domanda aperta di V1)
4. i tiri in porta vengono dal modello DIRETTO: V2 ha misurato la gerarchia volume x precisione e non l'ha adottata
5. nessuna quota e nessuna valutazione di scommessa (vincolo 3): nel repository non ci sono prezzi di mercato reali

## 8. Domande aperte

1. **`al` e' esposto ma il report non lo usa**: tutte le tabelle qui sono alla
   fine della stagione, quindi `dentro_campione` e' `True` per le coppie gia'
   giocate. Per una previsione vera va passato `al` con la data della giornata,
   e la funzione lo dichiara. Non e' stato costruito un esempio giornata per
   giornata: sarebbe la naturale coda del blocco.
2. **La stagione e' una sola** (`2025-2026`). Il ponte accetta le altre quattro,
   ma i ratings di una stagione passata servono a poco se non per verifica.
3. ~~**Il totale di partita non e' esposto.**~~ `[CHIUSA - Fase 15 / T1]` Non
   serviva la congiunta: `sot/totale.py` somma i due lambda (esatto) e stima
   `r_tot` sui totali. **Con un limite dichiarato**: sul totale il lambda e'
   sotto-calibrato (pendenza 0,63 contro 1,008 per lato), perche' il modello
   crede i due lati piu' anti-correlati di quanto siano.
4. **Nessun prezzo di mercato**: finche' non ci sono quote di chiusura reali,
   «il modello e' meglio del mercato» non e' una frase che questo progetto possa
   pronunciare.
