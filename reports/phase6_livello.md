# Fase 6A — da dove viene il livello della proiezione

Ricostruzione della catena aritmetica che porta dal rating del modello al numero pubblicato. Nessuna moltiplicazione implicita. **Nessun numero pubblicato viene cambiato da questo blocco**: `alpha`, `tau` e i rating restano quelli delle Fasi 2-5.

## Esito in breve

1. **Il livello pubblicato non contiene il modello di squadra.** Il contesto si semplifica algebricamente dentro `monte_carlo`, e la prova numerica e' nella sezione 3: moltiplicando il contesto del Como per 1.5 il numero pubblicato non cambia di un bit (scarto massimo fra le due simulazioni: 0.0). Rating, `alpha` e vantaggio del campo decidono **come** il lambda si ripartisce fra i giocatori, non **quanto** vale.
2. **4.90 e' un valore fornito, non ricostruibile da questi dati.** E' `config.REF_TOPDOWN_PER_MATCH`, dichiarato come modello di persistenza su 21 stagioni: quelle stagioni non sono nel repository e il calcolo non esiste in nessun modulo. Inventario dei suoi usi nella sezione 2.
3. **Il salto da 4.95 a 5.03 e' tutto Monte Carlo**: fattore 1.0155, mai documentato prima. Con `sources=()` la simulazione restituisce esattamente l'ancora 4.9497. E' convessita', non un ingrediente del modello. Ecco perche' 4.90 x 1.010 faceva 4.95 e non 5.03.
4. **Il rating di `fig5` non e' a campo neutro**: e' il valore in trasferta. Il Como fa 4.343 in trasferta, 5.287 in casa, 4.815 di media su 19 + 19. La definizione **non e' stata cambiata**: portarla al punto medio geometrico sposterebbe 4.34 verso 4.79, cioe' verso 4.90, ed e' esattamente il modo di far tornare i numeri che il progetto vieta.
5. **La ridge comprime con pendenza 0.760 (+- 0.018)** rispetto ai tassi grezzi, e il livello usato **de-comprime meno** di quanto la pendenza giustifichi (1.109 contro 1.316). Sulla scala di calendario il rating de-compresso vale 5.062 contro il 4.9 usato: 0.16 tiri in porta a partita, 6 in stagione, cioe' 4.90 sta fra il rating del modello e il rating de-compresso, piu' vicino al primo.

---

## 1. Le due catene

Sono due, e **non si toccano**. Il ramo del modello e' quello che questi dati sanno dire; il ramo pubblicato e' quello che finisce nel README.

### Ramo A — il modello di squadra

| passo                                                           |   valore_partenza |   fattore |   valore_risultante | modulo                | funzione                                        | natura                                               |
|:----------------------------------------------------------------|------------------:|----------:|--------------------:|:----------------------|:------------------------------------------------|:-----------------------------------------------------|
| rating Como contro difesa media, in trasferta                   |          nan      |  nan      |              4.3433 | scripts/run_phase5.py | ratings_neutri -> level_chain.ratings_per_campo | stimato dal modello                                  |
| vantaggio del campo, partite in casa                            |            4.3433 |    1.2173 |              5.2872 | sot/model_team.py     | TeamModel.home_advantage                        | stimato dal modello                                  |
| media di calendario (19 in casa + 19 in trasferta)              |            4.3433 |    1.1087 |              4.8152 | sot/level_chain.py    | ratings_per_campo                               | aritmetica, esplicitata qui per la prima volta       |
| calendario reale: avversari effettivi e pesi di decadimento     |            4.8152 |    1.0185 |              4.9041 | sot/project_2627.py   | como_context                                    | stimato dal modello                                  |
| scarto in campione fra modello e osservato (compressione ridge) |            4.9041 |    1.041  |              5.1053 | -                     | -                                               | NON e' un fattore applicato: e' il residuo che resta |

L'ultima riga non e' un fattore applicato da nessuno: e' quanto resta fra la previsione in campione del modello e il tasso davvero realizzato dal Como. Il modello sta sotto del 3.9% **sulla stagione che ha usato per stimare**, che e' il ritorno alla media della ridge visto da vicino (sezione 4).

### Ramo B — il numero pubblicato

| passo                                                   |   valore_partenza |   fattore |   valore_risultante | modulo              | funzione                                 | natura                                                      |
|:--------------------------------------------------------|------------------:|----------:|--------------------:|:--------------------|:-----------------------------------------|:------------------------------------------------------------|
| riferimento dall'alto 2026-27                           |          nan      |  nan      |              4.9    | sot/config.py       | REF_TOPDOWN_PER_MATCH                    | valore fornito dall'utente, NON calcolato da questi dati    |
| rapporto compositivo (ricambio di rosa + minuti)        |            4.9    |    1.0101 |              4.9497 | sot/project_2627.py | build_projection -> monte_carlo (anchor) | stimato dai dati per giocatore                              |
| convessita' del Monte Carlo (mediana simulata / ancora) |            4.9497 |    1.0155 |              5.0263 | sot/project_2627.py | monte_carlo                              | artefatto numerico della simulazione, mai documentato prima |
| conversione in stagione                                 |            5.0263 |   38      |            191      | sot/squad_2627.py   | N_MATCHES                                | aritmetica                                                  |

### Ramo C — la ricomposizione per giocatore, che si semplifica

- contesto di squadra del Como (media delle 38 previsioni): **4.9041**
- ricomposizione dal basso della rosa 2025-26 con i minuti reali: **4.7262** (-3.6% rispetto al contesto: lo shrinkage al ruolo perde qualcosa per strada)
- ricomposizione della rosa 2026-27 con i minuti proiettati: **4.7741**
- rapporto = **1.010139**

Il contesto compare a numeratore e denominatore del rapporto e si semplifica: e' per questo che il ramo C entra nel ramo B solo con il rapporto, mai con un livello.

---

## 2. Da dove nasce 4.90

**Non e' una stima di questo modello e non e' ricostruibile qui.** In `sot/config.py` e' dichiarato come proiezione top-down di riferimento, da un modello di persistenza su 21 stagioni con coefficienti 0.591 sull'ultima stagione e 0.247 sulla penultima. Quelle stagioni non esistono nel repository — i dati sono la sola 2025-26 — e nessun modulo contiene quel calcolo. Chi volesse verificarlo non puo' farlo con questo codice.

Ogni punto in cui il riferimento entra nei calcoli:

| punto                                 | cosa                                                     | come viene usato                                                     |
|:--------------------------------------|:---------------------------------------------------------|:---------------------------------------------------------------------|
| sot/config.py                         | REF_TOPDOWN_PER_MATCH = 4.90                             | valore fornito dall'utente, non calcolato qui                        |
| sot/config.py                         | REF_TOPDOWN_SEASON = 186 / REF_TOPDOWN_PI80 = (152, 222) | idem, e l'intervallo alimenta le deviazioni standard qui sotto       |
| sot/project_2627.py:46                | TOPDOWN_SEASON_SD dall'IC80% del riferimento             | l'ampiezza dell'intervallo pubblicato e' ereditata, non stimata      |
| sot/project_2627.py:50-51             | TEAM_SHOCK_SD_LOG, LEAGUE_SD_LOG                         | shock di squadra 65% e livello di campionato 6%: quote assunte       |
| sot/project_2627.py:157               | anchor = ratio * REF_TOPDOWN_PER_MATCH                   | QUI il livello pubblicato viene fissato dal riferimento              |
| scripts/run_phase3.py:64-65           | riga 'riferimento dall'alto' del report                  | citato come riferimento, uso corretto                                |
| scripts/run_phase5.py:113-114,136-138 | fig6 e tabella del deliverable                           | citato come riferimento, uso corretto                                |
| sot/level_chain.py                    | default di `livello_usato` in compressione_ratings       | e' il livello di cui si misura la de-compressione                    |
| sot/level_chain.py                    | default di `livello_usato` in rho_implicito              | da qui si ricava il rho implicito nella proiezione pubblicata (6C)   |
| sot/project_2627.py:monte_carlo       | livello_dall_alto=None -> riferimento                    | il livello resta quello pubblicato finche' non lo si fa variare (6C) |
| scripts/run_phase6a.py                | report di Fase 6A                                        | citato come riferimento, uso corretto                                |
| scripts/run_phase6c.py                | griglia di rho e figura della sensibilita'               | citato come riferimento, uso corretto                                |

**La riga da guardare e' `project_2627.py:157`**: li' il livello della proiezione viene fissato dal riferimento, e le due righe 50-51 fanno lo stesso con l'ampiezza dell'intervallo. Non c'e' niente di sbagliato nell'usare un'ancora esterna — quello che mancava era dichiararlo accanto al numero.

Coincidenza da segnalare, perche' e' probabilmente il motivo per cui nessuno si e' accorto che la catena non era chiusa: il contesto del Como calcolato dal modello vale **4.9041**, cioe' 4.9 a due decimali. Le due grandezze si somigliano ma non hanno alcun legame: una e' la media delle 38 previsioni in campione del 2025-26, l'altra e' una previsione esterna per il 2026-27. L'uguaglianza e' un caso.

---

## 3. Il gonfiamento del Monte Carlo, fonte per fonte

| fonte                        |   per_partita |   ancora |   fattore |
|:-----------------------------|--------------:|---------:|----------:|
| nessuna (sources=())         |       4.94968 |  4.94968 |   1       |
| player_rates                 |       5.06514 |  4.94968 |   1.02333 |
| new_signings                 |       4.98192 |  4.94968 |   1.00651 |
| minutes                      |       4.86989 |  4.94968 |   0.98388 |
| team_shock                   |       4.94868 |  4.94968 |   0.9998  |
| league_level                 |       4.94938 |  4.94968 |   0.99994 |
| sampling                     |       4.94737 |  4.94968 |   0.99953 |
| TUTTE (il numero pubblicato) |       5.02632 |  4.94968 |   1.01548 |

La prima riga e' il controllo che conta: senza nessuna fonte accesa la simulazione restituisce l'ancora esatta (4.9497), quindi non ci sono altri fattori nascosti oltre a quelli qui elencati.

Il gonfiamento totale vale **1.0155** e non e' uniforme fra le fonti. L'incertezza sui tassi individuali pesa +2.33% e i nuovi arrivi +0.65%: sono perturbazioni dentro una somma di esponenziali, quindi ne alzano il centro (disuguaglianza di Jensen). L'incertezza sui minuti va invece **nell'altro verso**, -1.61%: ridistribuire i minuti verso la rosa allargata li toglie a chi tira di piu', e il Como ha un tiratore che da solo vale il 21% del lambda. Gli shock lognormali e il campionamento hanno mediana centrata e non spostano (-0.02%, -0.01%, -0.05%). Le fonti non sono esattamente moltiplicative: accese insieme interagiscono.

### Il contesto si semplifica: verifica numerica

- mediana con il contesto originale: **191.0**
- mediana con il contesto moltiplicato per 1.5: **191.0**
- scarto massimo fra le due simulazioni, simulazione per simulazione: **0.0**

Se il livello pubblicato dipendesse dal modello di squadra, moltiplicare il contesto per 1.5 lo cambierebbe del 50%. Non lo cambia affatto.

---

## 4. Quanto comprime la ridge

Regressione dei 20 rating sui tassi grezzi di stagione, riportati sulla stessa scala di campo (i grezzi vivono sulla scala di calendario, i rating su quella di trasferta: si divide per (1 + 1.2173) / 2 = 1.1087). **Descrittiva e in campione**: misura quanto la ridge comprime, non prevede niente.

| grandezza | valore |
|---|---|
| pendenza | **0.7601** +- 0.0184 |
| intercetta | 0.8307 |
| R2 | 0.9896 |

La pendenza sotto 1.0 e' il fenomeno: un tiro in porta di eccesso grezzo diventa meno di un tiro di eccesso nel rating. **La ridge minimizza l'errore predittivo, non stima livelli senza distorsione**; l'errore quadratico si riduce tirando tutti verso il centro, e chi sta in alto e' chi paga. E' lo stesso fenomeno del terzile alto di lambda (Fase 4) e del danno sopra 4.5 SoT (Fase 3): tre misure diverse dello stesso effetto, tutte con lo stesso segno.

Sul Como, tutto sulla scala di trasferta (media di campionato 3.6388):

| livello | valore | eccesso sulla media |
|---|---|---|
| rating del modello | 4.3433 | 0.7045 |
| livello usato (4.90) | 4.4198 | 0.7809 |
| grezzo 2025-26 | 4.6049 | 0.9661 |

- de-compressione implicita nel livello usato: **1.1086**
- de-compressione che la pendenza giustificherebbe (1 / pendenza): **1.3156**
- livello del Como de-compresso dalla pendenza, riportato su scala di calendario: **5.062** contro 4.815 del modello, 4.9 usato e 5.105 grezzo

Quindi il livello usato **de-comprime meno** di quanto la pendenza giustifichi (1.109 contro 1.316). Sulla scala di calendario il rating de-compresso vale 5.062 contro il 4.9 usato: 0.16 tiri in porta a partita, 6 in stagione, cioe' 4.90 sta fra il rating del modello e il rating de-compresso, piu' vicino al primo. 
Il gap fra il rating e il livello usato non e' un errore di nessuno dei due: e' la distanza fra una stima costruita per minimizzare l'errore sulla prossima partita e un livello, che sono due obiettivi diversi. La de-compressione implicita in 4.90 va nella direzione giusta; se sia della misura giusta, con una stagione sola, questi dati non lo possono dire — e' il tema del blocco 6C.

---

## 5. Le tre scale di campo, per tutte le squadre

| team              |   neutro |   casa |   media_calendario |
|:------------------|---------:|-------:|-------------------:|
| Inter             |    4.994 |  6.08  |              5.537 |
| Juventus          |    4.969 |  6.049 |              5.509 |
| Como              |    4.343 |  5.287 |              4.815 |
| Roma              |    4.076 |  4.962 |              4.519 |
| Atalanta          |    4.041 |  4.919 |              4.48  |
| Napoli            |    3.999 |  4.868 |              4.433 |
| AC Milan          |    3.726 |  4.536 |              4.131 |
| Lazio             |    3.71  |  4.517 |              4.114 |
| Udinese           |    3.523 |  4.288 |              3.905 |
| Torino            |    3.443 |  4.192 |              3.818 |
| Sassuolo          |    3.404 |  4.144 |              3.774 |
| Bologna           |    3.38  |  4.115 |              3.748 |
| Genoa             |    3.322 |  4.044 |              3.683 |
| Cagliari          |    3.281 |  3.994 |              3.637 |
| Verona            |    3.261 |  3.97  |              3.615 |
| Fiorentina        |    3.193 |  3.887 |              3.54  |
| Cremonese         |    3.14  |  3.822 |              3.481 |
| Pisa              |    2.806 |  3.416 |              3.111 |
| Parma Calcio 1913 |    2.676 |  3.258 |              2.967 |
| Lecce             |    2.643 |  3.217 |              2.93  |

`neutro` e' il nome storico della colonna disegnata in `fig5` ed e' il valore **in trasferta**; `casa` = `neutro` x 1.2173; `media_calendario` e' la media su 19 + 19, che e' la scala su cui si leggono i tassi grezzi di stagione e il livello 4.90. Il nome della colonna non e' stato cambiato perche' e' un numero gia' pubblicato: si documenta la scala, non si sposta il valore.

---

## Limiti di questo blocco

- La regressione della sezione 4 e' **in campione su una stagione**: quantifica la compressione della ridge su questi 20 punti, non identifica il livello corretto per il 2026-27.
- L'origine di 4.90 e' **dichiarata dall'utente e non verificabile qui**: se quel numero e' sbagliato, tutta la proiezione lo e', e niente in questo repository se ne accorgerebbe.
- Le quote 65% / 6% da cui escono `TEAM_SHOCK_SD_LOG` e `LEAGUE_SD_LOG` sono **assunzioni ereditate** dallo stesso riferimento, non stime: l'intervallo pubblicato e' largo quanto il riferimento ha deciso che fosse.
- `tau` = 3.0 e `r` = 26.0 sono quelli delle fasi precedenti, non ristimati qui.