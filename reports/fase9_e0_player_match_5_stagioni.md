# Fase 9 / E0 — `player_match` sulle cinque stagioni, e l'aggancio esteso

Generato da `scripts/run_fase9_e0.py` il 2026-08-04.
**Nessuna richiesta di rete, niente scritto sotto `data/raw/`.**

## Esito in una riga

Le tabelle di Fase 1 esistono ora per tutte e cinque le stagioni —
**87.449 righe giocatore-partita** su 1.889 partite — e
l'aggancio dei giocatori copre **3.081 triple
`(stagione, squadra, giocatore)`** con **8
irrisolti**, tutti dichiarati. Il prerequisito della Fase 9 e' chiuso: da qui in
poi esiste un walk-forward.

Il controllo che una stagione sola non poteva fare — **lo stesso giocatore deve
prendere lo stesso `playerId` in ogni stagione** — passa su
**1.544 confronti indipendenti con zero
discordanze**, in entrambi i versi.

## 1. Le cinque stagioni

| stagione | partite | squadra_partita | giocatore_partita | tiri | tiri_in_porta | giocatori | sot_per_squadra_partita |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2021-2022 | 374 | 748 | 16666 | 9748 | 3322 | 608 | 4.441 |
| 2022-2023 | 375 | 750 | 17606 | 9509 | 3092 | 577 | 4.123 |
| 2023-2024 | 380 | 760 | 17698 | 9701 | 3153 | 590 | 4.149 |
| 2024-2025 | 380 | 760 | 17705 | 9213 | 3065 | 599 | 4.033 |
| 2025-2026 | 380 | 760 | 17774 | 9359 | 3066 | 586 | 4.034 |

**I tiri in porta per squadra-partita scendono del 9,2% fra la prima e
l'ultima stagione**, ed e' il fatto gia' misurato dalla verifica di stabilita':
il *criterio di rilevazione* e' fermo — la definizione coincide con il flag Opta
nativo in tutte e cinque, zero discordanze su 47.530 tentativi — ma il *livello*
si muove. Si tira di meno, non si conta diversamente.

Ne segue la ragione per cui questo blocco produce una tabella di riferimento
invece che tabelle gia' normalizzate: +1 tiro di eccesso non significa la stessa
cosa nel 2021-22 e nel 2025-26.

## 2. I denominatori si contano, non si assumono

| stagione | team | partite | sot | sot_per_partita |
|---|---|---:|---:|---:|
| 2021-2022 | Atalanta | 35 | 163 | 4.657 |
| 2021-2022 | Bologna | 37 | 148 | 4.000 |
| 2021-2022 | Cagliari | 37 | 123 | 3.324 |
| 2021-2022 | Empoli | 37 | 158 | 4.270 |
| 2021-2022 | Lazio | 37 | 190 | 5.135 |
| 2021-2022 | Napoli | 36 | 194 | 5.389 |
| 2021-2022 | Salernitana | 37 | 139 | 3.757 |
| 2021-2022 | Sassuolo | 37 | 208 | 5.622 |
| 2021-2022 | Verona | 37 | 157 | 4.243 |
| 2022-2023 | Atalanta | 35 | 162 | 4.629 |
| 2022-2023 | Cremonese | 36 | 121 | 3.361 |
| 2022-2023 | Empoli | 37 | 128 | 3.459 |
| 2022-2023 | Monza | 37 | 142 | 3.838 |
| 2022-2023 | Napoli | 37 | 217 | 5.865 |
| 2022-2023 | Sassuolo | 37 | 166 | 4.486 |
| 2022-2023 | Spezia | 37 | 130 | 3.514 |

Sono **16 righe su 100** in cui il denominatore non e'
38, e nessuna e' un difetto di questo blocco:

- l'**Atalanta** ha 35 partite nel 2021-22 e nel 2022-23 perche' **WhoScored non
  ha quei dati** (`matchCentreData: null`, verificato pagina per pagina in fase
  di acquisizione). Delle 12 partite mancanti ne perde 6 contro un'attesa di 1,2:
  la perdita **non e' casuale rispetto alla squadra**, ed e' il motivo per cui
  dividere per 38 sbaglierebbe proprio dove sbagliare costa di piu'.

**E non basta sostituire 38 col numero di calendario**, che era la correzione
ovvia e sarebbe sbagliata a sua volta. Spezia e Verona hanno *giocato* 39 partite
nel 2022-23 — 38 piu' il **playout**, che e' una partita vera — ma i CSV
acquisiti sono **37 e 38**: di quelle 39, WhoScored non ha rispettivamente 2 e 1.
**Nessuna squadra arriva a 39 nei dati.** Chi avesse messo 39 a mano per le due
squadre del playout avrebbe introdotto un errore nuovo al posto di quello
vecchio.

L'unica procedura che regge e' contare, ed e' quello che fa
`partite_per_squadra()`. Chi calcola un tasso per 90 o un conteggio di presenze
parte da qui.

## 3. L'unica stima del blocco: i cinque fit di xG

«E0 non produce stime» sarebbe falso, quindi la stima si dichiara.
`aggregate.build_shots` stima una logistica cross-fitted a 5 fold raggruppati per
partita, e girando la Fase 1 una volta per stagione i fit sono **cinque
indipendenti**. E' il comportamento voluto — CLAUDE.md vieta di stimare l'xG
interno su piu' stagioni insieme perche' i suoi ingressi derivano — ma vuol dire
**cinque scale**, e le cinque righe accostate sono di per se' la misura di quanto
si muovono.

| stagione | tiri | gol | tasso_base | logloss | logloss_base | auc | somma_xg | calibrazione_pct | rigori |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 2021-2022 | 9748 | 1037 | 0.1064 | 0.2550 | 0.3389 | 0.816 | 1037.2 | 0.02 | 139 |
| 2022-2023 | 9509 | 927 | 0.0975 | 0.2450 | 0.3195 | 0.809 | 927.3 | 0.04 | 106 |
| 2023-2024 | 9701 | 968 | 0.0998 | 0.2512 | 0.3246 | 0.807 | 968.8 | 0.08 | 131 |
| 2024-2025 | 9213 | 936 | 0.1016 | 0.2574 | 0.3286 | 0.809 | 935.2 | -0.09 | 104 |
| 2025-2026 | 9359 | 900 | 0.0962 | 0.2431 | 0.3166 | 0.811 | 900.6 | 0.07 | 106 |

Il baseline e' il tasso base della **stessa** stagione (vincolo 6): un log-loss
di 0,24 non dice niente finche' non si sa che il tasso base ne fa 0,32.

La riga 2025-26 riproduce la Fase 1 — log-loss 0,243, AUC 0,811, calibrazione
+0,07% — ed e' il controllo che la parametrizzazione non ha spostato niente.

**La colonna `xg_fit` esiste per questo.** `shots`, `team_match` e `player_match`
la portano, e dice quale fit ha prodotto quella `xg`. Non e' una conversione: non
esiste, e non va costruita, una colonna `xg` confrontabile fra stagioni dentro il
derivato. La comparabilita' e' un fatto dello strato feature (E1). Qui la deriva
si porta avanti; normalizzarla via cancellerebbe un fatto misurato.

## 4. Lo stato di impiego — coda del blocco, e non aggiunge dati

`player_match` ha una colonna `stato`. **Non e' un'estrazione nuova**: i
convocati non impiegati erano nella tabella fin dalla Fase 1, perche'
`minutes.squads()` legge l'intera rosa da `InvolvedPlayers` del `FormationSet`,
dove i panchinari stanno con `role_code = 5`. Sono
**28.472 righe a zero minuti, il
32.6% della tabella**.

Erano pero' leggibili solo da chi sapesse che `minutes == 0` significa
"convocato e mai entrato" e non "dato mancante" — e quella e' la distinzione che
un modello dell'impiego (E2) non puo' permettersi di sbagliare.

| stato | 2021-2022 | 2022-2023 | 2023-2024 | 2024-2025 | 2025-2026 |
|---|---:|---:|---:|---:|---:|
| titolare | 8228 | 8250 | 8360 | 8360 | 8360 |
| subentrato | 3299 | 3474 | 3550 | 3528 | 3568 |
| panchina | 5139 | 5882 | 5788 | 5817 | 5846 |

I titolari sono **11 per squadra-partita in ogni partita di ogni stagione**, e un
test lo verifica: e' il controllo che `InvolvedPlayers` e' stato letto bene, non
una curiosita'.

**Il quarto stato e' l'assenza della riga.** Chi non e' stato convocato affatto —
fuori lista, infortunato, squalificato, ceduto — non compare, e non ha
un'etichetta perche' non ha una riga a cui attaccarla. Chi ricostruisce l'impiego
deve costruirsi il denominatore della rosa **da fuori**, invece di contare le
righe: WhoScored registra i convocati, non i tesserati. E' un limite del
derivato, non un difetto, e va portato in E2 esplicitamente.

La rosa convocata sta fra 16 e
28 giocatori, mediana 23.
Un solo caso su 3.778 sta sotto i 18 convocati.

## 5. Le medie di campionato, `stagione x grandezza`

`data/processed/ITA-serie-a/fase9_medie_campionato.parquet`, forma lunga
(`stagione`, `grandezza`, `unita`, `media`, `n`). **Non e' una colonna ripetuta
su ogni riga di `player_match`**: una media di campionato e' un fatto *di
stagione*, non *di riga*. Forma lunga e non larga perche' E1 aggiungera' le sue
grandezze, e una tabella larga andrebbe migrata a ogni giro.

Le grandezze che si muovono di piu':

| grandezza | unita | prima | ultima | deriva_pct | ampiezza_pct |
|---|---|---:|---:|---:|---:|
| goals | per_90 | 0.118 | 0.099 | -15.8 | 18.7 |
| xg | per_90 | 0.118 | 0.099 | -15.7 | 18.7 |
| big_chances | squadra_partita | 1.896 | 2.032 | 7.2 | 17.4 |
| goals | squadra_partita | 1.386 | 1.184 | -14.6 | 17.1 |
| xg | squadra_partita | 1.387 | 1.185 | -14.5 | 17.0 |
| xg_conceded | squadra_partita | 1.387 | 1.185 | -14.5 | 17.0 |
| ppda | squadra_partita | 15.208 | 16.782 | 10.4 | 15.4 |
| def_actions | squadra_partita | 23.630 | 21.254 | -10.1 | 14.6 |

Le piu' ferme:

| grandezza | unita | prima | ultima | deriva_pct | ampiezza_pct |
|---|---|---:|---:|---:|---:|
| quota_in_porta | tiro | 0.341 | 0.328 | -3.9 | 4.9 |
| minutes | giocatore_partita | 47.595 | 45.987 | -3.4 | 3.9 |
| mean_shot_distance | squadra_partita | 17.699 | 17.695 | -0.0 | 1.6 |
| field_tilt | squadra_partita | 0.500 | 0.500 | 0.0 | 0.0 |
| possession | squadra_partita | 0.500 | 0.500 | 0.0 | 0.0 |

**Le ultime due righe non sono un risultato, e vanno lette come tali.**
`possession` e `field_tilt` sono **quote**: le due squadre di una partita si
dividono 1, quindi la loro media di campionato vale 0,500 per costruzione in
qualunque stagione. Una media che non puo' muoversi non dice niente sulla
stabilita' della grandezza sottostante — la sua **dispersione** si', ma non e'
questa tabella. Chi cerchera' feature stabili in fondo a questo elenco le
trovera' per il motivo sbagliato.

Nella direzione opposta, `xg` e `xg_conceded` per squadra-partita coincidono a
ogni cifra in tutte e cinque le stagioni (1,387 e 1,185 agli estremi), e **quello
si' e' un controllo**: l'xG prodotto da una squadra e' l'xG concesso da
un'altra, quindi le due medie devono essere identiche. Lo sono.

Questa tabella **non decide niente**: la regola su cosa si puo' usare in unita'
grezze e' del blocco E1. Qui si misura e basta.

## 6. L'aggancio dei giocatori, con il tasso per stagione

| stagione | righe | irrisolti | totale_fc | tasso | giocatori_fc | giocatori_ws | ws_non_agganciati | jaccard_medio | jaccard_min |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 2021-2022 | 629 | 2 | 631 | 0.9968 | 605 | 608 | 3 | 0.9989 | 0.800 |
| 2022-2023 | 602 | 1 | 603 | 0.9983 | 576 | 577 | 1 | 0.9962 | 0.778 |
| 2023-2024 | 610 | 3 | 613 | 0.9951 | 585 | 590 | 5 | 0.9998 | 0.923 |
| 2024-2025 | 631 | 2 | 633 | 0.9968 | 596 | 599 | 3 | 0.9999 | 0.933 |
| 2025-2026 | 609 | 0 | 609 | 1.0000 | 586 | 586 | 0 | 0.9999 | 0.944 |

**Una riga e' una tripla `(stagione, squadra, giocatore)`, non un giocatore.**
Chi cambia squadra a gennaio compare due volte da entrambi i lati, ed e' giusto:
i suoi minuti appartengono a due squadre diverse. Nel 2025-26 sono
**609 righe per 586 giocatori distinti**, e il 609 e' lo stesso numero che il
report dell'aggancio riportava per la stagione singola.

**Il 609/609 della 2025-26 non era una previsione sulle altre**, e infatti il
tasso non e' identico — sta fra 0.9951 e 1,0000. Il residuo
si mostra, non si risolve d'ufficio, ed e' piccolo abbastanza da stare in una
tabella:

| stagione | nome_fc | presenze_fc | percentile | motivo | nomi_candidati |
|---|---|---:|---|---|---|
| 2021-2022 | Supryaga | 1 | 0% | nessun candidato |  |
| 2022-2023 | Ranocchia | 1 | 0% | cognome ambiguo | Andrea Ranocchia; Filippo Ranocchia |
| 2023-2024 | Akinsamiro | 1 | 0% | nessun candidato |  |
| 2024-2025 | Kasa | 8 | 23% | nessun candidato |  |
| 2021-2022 | Stryger Larsen | 11 | 30% | nessun candidato |  |
| 2023-2024 | Lopez M. | 19 | 48% | due giocatori dei voti sullo stesso WhoScored |  |
| 2024-2025 | Obert | 21 | 52% | cognome ambiguo | Roberto Piccoli; Adam Obert |
| 2023-2024 | Arthur Melo | 33 | 84% | due giocatori dei voti sullo stesso WhoScored |  |

Sono **8 righe su 3.081**, e ricadono nelle categorie gia' note:
omonimi veri che le iniziali non separano (`Andrea` contro `Filippo Ranocchia`),
giocatori con **una** presenza che il cognome non aggancia, e due casi in cui due
nomi dei voti puntano allo stesso WhoScored — dove si tolgono **entrambi**,
perche' tenere "il migliore" significherebbe scegliere.

### Il residuo sta sui giocatori rari? In parte, e la parte che manca conta

La domanda non e' oziosa: i giocatori con poche presenze sono **esattamente la
categoria che un modello dell'impiego deve prevedere**, quindi un aggancio che
fallisse li' fallirebbe dove serve.

La risposta e' **si', ma debolmente, e con due meccanismi diversi**. La mediana
degli irrisolti e' 9.5 presenze contro
20.0 degli agganciati, e 6 su 8 stanno sotto la mediana. Ma la
colonna `percentile` mostra che non e' una concentrazione pulita:

- **sotto il 30° percentile** (1, 1, 1, 8, 11 presenze) il motivo e' sempre
  *nessun candidato* o un cognome che non risolve. Qui il fallimento **e'** un
  effetto della rarita': poche presenze, poche occasioni di comparire con una
  grafia agganciabile;
- **al 48°, 52° e 84° percentile** ci sono `Lopez M.` (19), `Obert` (21) e
  `Arthur Melo` (33, cioe' un titolare). Il loro motivo e' un altro: **collisione
  di nomi**, non rarita'. `Arthur Melo` e `Lopez M.` sono i due casi in cui due
  nomi dei voti puntano allo stesso WhoScored.

**Ne segue che il punto debole dell'aggancio non e' solo "i giocatori rari": e'
la collisione di nomi, che colpisce chiunque.** Sono due difetti con due
rimedi diversi, e per E2 il secondo e' il piu' fastidioso — toglie dal campione
un titolare, non una comparsa. Con 8 casi su 3.081
non sposta nessuna stima; e' registrato perche' se un domani il numero crescesse,
la lettura da fare e' questa e non "aggiungiamo stagioni".

**Il residuo esiste anche nel verso opposto**, e non e' lo stesso numero:
`ws_non_agganciati` conta i giocatori con almeno un minuto che **nessuna riga dei
voti reclama**. E' il "terzo stato" gia' incontrato nella 2025-26 — chi gioca e
che la fonte dei voti non elenca affatto — e va tenuto d'occhio in E2, dove
l'assenza di riga e l's.v. non sono la stessa cosa.

### Il residuo lato WhoScored, con i minuti — coda del blocco

Nella prima versione di questo report il verso opposto era **solo un conteggio**,
e un conteggio di 0-5 si legge come "quattro comparse". **Non e' vero, e i minuti
lo dicono subito:**

| stagione | coppie | giocatori | minuti_totali | minuti_mediana | minuti_max | quota_minuti_pct |
|---|---:|---:|---:|---:|---:|---:|
| 2021-2022 | 3 | 3 | 759 | 28.0 | 726 | 0.096 |
| 2022-2023 | 1 | 1 | 51 | 51.0 | 51 | 0.006 |
| 2023-2024 | 6 | 6 | 3125 | 37.5 | 2145 | 0.380 |
| 2024-2025 | 3 | 3 | 1452 | 261.0 | 1178 | 0.179 |
| 2025-2026 | 0 | 0 | 0 |  | 0 | 0.000 |

**Il massimo del 2023-24 vale 2,145 minuti**,
cioe' circa 23 partite intere — un
giocatore da rotazione piena, non una comparsa. Nel 2024-25 ce n'e' un altro da
oltre mille. La mediana dice il contrario del massimo, ed e' il motivo per cui
qui vanno riportati entrambi.

| stagione | team | playerName | minuti | presenze | da_titolare |
|---|---|---|---:|---:|---:|
| 2021-2022 | Udinese | Jens Stryger | 726 | 11 | 8 |
| 2021-2022 | Sampdoria | Vladyslav Supriaha | 28 | 1 | 0 |
| 2021-2022 | Venezia | Bjarki Bjarkason | 5 | 1 | 0 |
| 2022-2023 | Monza | Andrea Ranocchia | 51 | 1 | 1 |
| 2023-2024 | Fiorentina | Arthur | 2145 | 33 | 23 |
| 2023-2024 | Fiorentina | Maxime Lopez | 884 | 19 | 7 |
| 2023-2024 | Genoa | Seydou Fini | 51 | 3 | 0 |
| 2023-2024 | Genoa | Pablo Galdames | 24 | 2 | 0 |
| 2023-2024 | Inter | Ebenezer Akinsanmiro | 15 | 1 | 0 |
| 2023-2024 | Inter | Lucien Agoumé | 6 | 1 | 0 |
| 2024-2025 | Cagliari | Adam Obert | 1178 | 21 | 13 |
| 2024-2025 | Genoa | Lior Kassa | 261 | 8 | 2 |
| 2024-2025 | Fiorentina | Tommaso Rubino | 13 | 1 | 0 |

In quota dei minuti di stagione il residuo resta sotto lo **0,4%** ovunque,
quindi **non sposta nessuna media** — ed e' esattamente per questo che era
passato inosservato. Ma E2 non stima una media: stima **chi gioca**. Queste sono
righe di `player_match` **senza bersaglio**, e un campione costruito unendo le
due fonti se le perderebbe in silenzio, nella classe che il modello deve
indovinare.

**Perche' sta qui e non in E2**: e' un difetto del derivato, e vale il principio
che questo blocco ha gia' applicato agli 8 irrisolti — il residuo si mostra, non
si risolve d'ufficio. Non c'e' nessun tentativo di riagganciarlo con una regola
piu' larga, che sarebbe scegliere. La 2025-26 e' l'unica stagione a zero in
entrambi i versi.

> **E la colonna `ws_non_agganciati` gia' pubblicata sottostima**, il che e'
> stato scoperto da un test che pretendeva l'uguaglianza fra i due conteggi e
> non l'ha ottenuta. La colonna sottrae insiemi di `playerId` **ignorando la
> squadra**: chi e' agganciato in un club risulta agganciato ovunque, anche dove
> l'aggancio e' fallito.
>
> Succede nel caso peggiore possibile. **`Maxime Lopez` nel 2023-24 gioca 2
> partite al Sassuolo e 19 alla Fiorentina.** Al Sassuolo l'aggancio riesce; alla
> Fiorentina no, perche' e' li' che avviene la collisione con `Arthur Melo`. Il
> conteggio pubblicato lo assorbe via il Sassuolo e **nasconde 884 minuti e 19
> presenze dietro un aggancio fatto su 2**. Da qui il 5 pubblicato contro le 6
> coppie vere.
>
> La colonna non e' stata toccata — risponde a una domanda coerente, "quante
> persone non sono mai state reclamate da nessuna parte" — ma per E2 serve
> l'altra, "quante righe restano senza bersaglio". Il test ora blocca la
> disuguaglianza nel verso giusto invece di un'uguaglianza falsa, e un secondo
> test pretende che **tutto** lo scarto si spieghi con il cambio di squadra: se
> comparisse un caso senza quella spiegazione, ci sarebbe un secondo meccanismo
> da cercare.

### I due residui non sono indipendenti — e questa non era prevista

Messi uno accanto all'altro, i due residui si rivelano **la stessa gente vista da
due lati**. Ogni irrisolto dei voti ha, nella **stessa squadra e stessa
stagione**, una riga WhoScored non agganciata con **lo stesso identico numero di
presenze**:

| stagione | team | nome_fc | presenze_fc | playerName | minuti | unico |
|---|---|---|---:|---|---:|---:|
| 2021-2022 | Udinese | Stryger Larsen | 11 | Jens Stryger | 726 | 1 |
| 2021-2022 | Sampdoria | Supryaga | 1 | Vladyslav Supriaha | 28 | 1 |
| 2022-2023 | Monza | Ranocchia | 1 | Andrea Ranocchia | 51 | 1 |
| 2023-2024 | Fiorentina | Arthur Melo | 33 | Arthur | 2145 | 1 |
| 2023-2024 | Fiorentina | Lopez M. | 19 | Maxime Lopez | 884 | 1 |
| 2023-2024 | Inter | Akinsamiro | 1 | Ebenezer Akinsanmiro | 15 | 0 |
| 2023-2024 | Inter | Akinsamiro | 1 | Lucien Agoumé | 6 | 0 |
| 2024-2025 | Cagliari | Obert | 21 | Adam Obert | 1178 | 1 |
| 2024-2025 | Genoa | Kasa | 8 | Lior Kassa | 261 | 1 |

**8 irrisolti su 8** trovano cosi' un candidato, e il
numero di presenze coincide **esattamente**, non approssimativamente. Il caso
`Arthur Melo` (33) / `Lopez M.` (19) — quello che l'aggancio aveva buttato via
perche' due nomi dei voti puntavano allo stesso WhoScored — si separa da solo:
33 va su `Arthur`, 19 va su `Maxime Lopez`, ed erano due persone diverse.

**Non e' stato risolto qui, e la ragione e' misurata invece che addotta.** La
regola "stessa squadra, stesse presenze" **non e' una chiave**: `Akinsamiro`
(1 presenza) trova **due** candidati a 1 presenza nell'Inter 2023-24,
`Ebenezer Akinsanmiro` e `Lucien Agoume`. Su otto casi ne lascia ambiguo uno —
7 accoppiamenti su 9 sono unici — quindi non e' una
chiave, e' un'euristica con un tasso d'errore. Applicarla d'ufficio sarebbe
**scegliere**, che e' esattamente cio' che questo blocco ha deciso di non fare.

**Cio' che la misura cambia e' la domanda aperta.** Non e' piu' «chi sono questi
otto»: e' «quale regola si adotta, e con quale tasso d'errore». La differenza e'
che ora si sa che l'informazione **c'e'**, ed e' una decisione, non un limite dei
dati. Le 5 righe WhoScored che restano senza
controparte sono il terzo stato vero — chi ha giocato e che la fonte dei voti non
elenca affatto — e quelle non si chiudono con nessuna regola.

Il **Jaccard** resta la verifica, non la chiave: e' l'accordo fra i due insiemi
di presenze una volta che l'aggancio e' stato deciso dal cognome.

Il minimo scende a 0.778 nel 2022-23 contro
0.944 nel 2025-26, e
**la causa e' stata cercata invece che attribuita alle 12 partite mancanti** —
che sarebbe stata la spiegazione comoda, ed e' sbagliata nel verso: quelle
tolgono presenze dal lato WhoScored, mentre qui il lato WhoScored ne ha *di
piu'*. Sono due cose, entrambe verificate:

- **lo spareggio Spezia-Verona**, l'unica partita con gli eventi e senza i voti.
  Il minimo assoluto della stagione e' un giocatore dello Spezia, e **14 dei suoi
  34 compagni hanno esattamente +1 presenza** dal lato WhoScored. Non spiega
  tutto: dei quattro Jaccard piu' bassi del 2022-23 solo due sono dello Spezia,
  e gli altri due ricadono nella causa qui sotto;
- **l'aritmetica degli insiemi piccoli**: chi ha 4 presenze su un lato e 5
  sull'altro fa 0,800 di Jaccard con **una** partita di scarto. Non e' un
  aggancio debole, e' un denominatore piccolo. Tutti i minimi stanno su giocatori
  con meno di 12 presenze.

### La verifica che una stagione sola non poteva fare

`giocatore_id` di fantacalcio viene dall'URL del profilo ed e' **stabile fra
stagioni**; `playerId` di WhoScored e' anch'esso un identificatore di persona.
Quindi cinque agganci **indipendenti** devono concordare — e dove non concordano,
almeno uno dei due e' sbagliato. Il pregio del controllo e' che **non passa dal
nome**, cioe' non e' circolare rispetto alla regola che l'aggancio usa per
decidere.

| | |
|---|---:|
| giocatori distinti | 1.404 |
| presenti in piu' di una stagione | 752 |
| **controlli incrociati indipendenti** | **1.544** |
| un `giocatore_id` su piu' `playerId` | 0 |
| piu' `giocatore_id` sullo stesso `playerId` | 0 |

Cambiare squadra **non** conta come discordanza: si guarda la coppia
`(giocatore_id, playerId)`, non la squadra.

## Cosa e' stato prodotto

| | |
|---|---|
| `data/processed/ITA-serie-a/<stagione>/{shots,team_match,player_match}.parquet` | 5 stagioni x 3 tabelle |
| `data/processed/ITA-serie-a/fase9_medie_campionato.parquet` | 110 righe |
| `data/processed/ITA-serie-a/fase9_xg_diagnostica.parquet` | 5 righe |
| `data/mapping/aggancio_giocatori.csv` | 3.081 righe, 5 stagioni |
| `data/mapping/aggancio_ws_non_agganciati.csv` | 13 righe, il residuo nell'altro verso |
| `reports/fase9_e0_*.csv` | le tavole di questo report |

## Domande aperte

1. **Il ruolo di stagione e' ricalcolato dentro ogni stagione**, quindi lo stesso
   giocatore puo' avere ruoli diversi in stagioni diverse. E' corretto — i ruoli
   cambiano davvero — ma vuol dire che `role` non e' una chiave stabile, e un
   modello che lo usa come fattore deve dire quale stagione sta guardando.
2. **`team_match_idx` non e' la giornata**, e su cinque stagioni la divergenza
   cresce: i recuperi non sono gli stessi ovunque. La giornata vera arriva
   dall'aggancio delle partite, gia' disponibile.
3. **L'aggancio copre chi ha giocato almeno un minuto**, e resta cosi': i voti
   non elencano chi non e' entrato, quindi non c'e' niente da agganciare. Ma il
   *dato* c'e' — `stato == "panchina"` in `player_match`, §4 — e per E2 la
   giuntura fra le due fonti va fatta su `player_match`, non sulla mappa.
   **Restano fuori i non convocati**, che non hanno riga da nessuna delle due
   parti.
4. **Gli infortuni non sono nei dati**, e restano la componente piu' grossa
   dell'assenza. Non e' una domanda che E0 puo' aprire o chiudere: va scritta
   accanto a ogni numero di E2.
