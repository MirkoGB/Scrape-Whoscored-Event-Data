# Fase 9 / Blocco E4 — voto base e bonus

> Rigenerato da `scripts/run_fase9_e4.py` il 2026-08-07. Nessuna richiesta di rete.


## In una riga

**Il margine di E4 non era 8,9 punti: e' 2,5, e la correzione e' il risultato
piu' importante del blocco.** Sul denominatore corretto nessuna feature da dati
evento aggiunge niente al modello d'asta — tre varianti su tre sono negative,
tutte dentro il rumore — e l'unica cosa che si muove e' la quotazione QI da
sola, che chiude il 10,5% con `t = 2,31` e **non sopravvive alla correzione per
molteplicita'**. Lungo la strada, due colonne della fonte si sono rivelate non
essere cio' che il loro nome dice.


## 0. Il divario di E4 non e' quello che credevamo


La priorita' di E4 poggiava su un numero pubblicato — «con i bonus noti il MAE
scende da 61,4 a 52,5», cioe' **8,9 punti** — che questo blocco ha dovuto
misurare per costruirci sopra il proprio denominatore. Misurandolo l'ha corretto,
e i difetti sono due, indipendenti.

**Primo, e piu' grande: il campione cambia.** «Bonus noti» gira su **2.204
righe** e non 2.678. Chi non ha mai giocato in `t` non ha un tasso osservato, e
quelle 474 righe cadono — ma sono **le peggiori**, quelle in cui il modello
predice punti a chi ne fara' zero. Sulle stesse 2.204 righe il modello completo
fa **55,01**, non 61,42.

**Secondo: «bonus noti» non era il bonus.** Era costruito per differenza come
`punti/presenze - voto_atteso`, che e' l'intero **tasso per presenza**, voto
compreso. Si vede da un'identita' che la vecchia tabella non poteva mostrare
perche' aveva una riga sola: costruendo allo stesso modo l'oracolo del *voto* si
ottiene lo stesso identico numero. Le due componenti sono osservate separatamente
in `fantapunti.per_giocatore_stagione`, e da li' ora si prendono.

| variante | righe | mae | mae_stesse_righe | guadagno_vero |
|---|---:|---:|---:|---:|
| modello completo | 2678 | 61.420 | 61.420 | 0 |
| presenze note | 2678 | 5.560 | 61.420 | 55.860 |
| voto noto | 2204 | 53.770 | 55.010 | 1.240 |
| bonus noti | 2204 | 53.570 | 55.010 | 1.440 |
| tasso per presenza noto (era "bonus noti") | 2204 | 52.500 | 55.010 | 2.510 |

La colonna `mae_stesse_righe` e' nuova ed e' il rimedio strutturale: porta il MAE
del modello completo **sul campione di quella riga**, cosi' che il confronto sia
sempre orizzontale. `guadagno_vero` e' la differenza che conta.

**Il fatto di fondo non cambia, anzi si rafforza: le presenze sono il problema,
i bonus no.** 55,86 punti contro 2,51. Cambia la taglia del pezzo su cui E4
lavora — il **4%** dell'errore, non il 14,5% — e cambia quindi come si leggono i
suoi numeri: una variante che chiude il 5% di 2,5 punti sposta il MAE di un
decimo.


## 1. E4.0 — i piazzati, e due colonne che non sono cio' che dicono


### `passFreekick` non contiene le punizioni

E' la trappola del blocco, ed e' della stessa famiglia di `StandingSave` un piano
piu' su: li' il nome di un **qualifier** non era un identificatore, qui non lo e'
il nome di una **colonna**.

| confronto | eventi | a | b | in_comune | identiche |
|---|---:|---:|---:|---:|---:|
| passFreekick == passCorner (riga per riga) | 43176 | 296 | 296 | 296 | si |
| passFreekick vs qualifier FreekickTaken | 43176 | 296 | 813 | 0 | no |
| passCorner vs qualifier CornerTaken | 43176 | 296 | 296 | 296 | si |

La colonna `passFreekick` e' identica riga per riga a `passCorner`, coincide con
i `CornerTaken` e ha intersezione **vuota** con gli 813 `FreekickTaken` veri. Chi
l'avesse usata avrebbe ottenuto una tabella di battitori di punizioni
perfettamente plausibile — ordine di grandezza giusto, nessun conteggio assurdo —
in cui ogni riga era un battitore di corner.

**E il gate non l'avrebbe fermata**: `passFreekick` passa a pieni voti, perche'
un gate misura se una colonna si e' mossa fra le stagioni, non se si chiama come
cio' che contiene.

| colonna | 2021-2022 | 2022-2023 | 2023-2024 | 2024-2025 | 2025-2026 | stagioni | min | max | rapporto | passa_il_gate |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| passCorner | 0.006 | 0.006 | 0.006 | 0.006 | 0.006 | 5 | 0.006 | 0.006 | 1.084 | si |
| passFreekick | 0.006 | 0.006 | 0.006 | 0.006 | 0.006 | 5 | 0.006 | 0.006 | 1.084 | si |
| penaltyScored | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 5 | 0.000 | 0.000 | 1.290 | si |
| penaltyMissed | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 5 | 0.000 | 0.000 | 1.386 | si |

Ne segue la scelta del blocco: **i piazzati si contano dai qualifier**, che sono
la strada gia' istruita e gia' misurata da E1. Il gate rifatto sui qualifier
effettivamente usati:

| qualifier | 2021-2022 | 2022-2023 | 2023-2024 | 2024-2025 | 2025-2026 | stagioni | min | max | rapporto | ammesso |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| CornerTaken | 0.00623 | 0.00613 | 0.00645 | 0.00636 | 0.00595 | 5.00000 | 0.00595 | 0.00645 | 1.08371 | si |
| FreekickTaken | 0.01866 | 0.01746 | 0.01739 | 0.01842 | 0.01849 | 5.00000 | 0.01739 | 0.01866 | 1.07340 | si |
| DirectFreekick | 0.00059 | 0.00058 | 0.00055 | 0.00055 | 0.00050 | 5.00000 | 0.00050 | 0.00059 | 1.18354 | si |
| IndirectFreekickTaken | 0.00267 | 0.00243 | 0.00255 | 0.00239 | 0.00241 | 5.00000 | 0.00239 | 0.00267 | 1.11324 | si |
| Penalty | 0.00100 | 0.00077 | 0.00095 | 0.00078 | 0.00079 | 5.00000 | 0.00077 | 0.00100 | 1.30352 | si |
| KeyPass | 0.01255 | 0.01246 | 0.01289 | 0.01240 | 0.01239 | 5.00000 | 0.01239 | 0.01289 | 1.03998 | si |
| Assisted | 0.01255 | 0.01246 | 0.01289 | 0.01240 | 0.01239 | 5.00000 | 0.01239 | 0.01289 | 1.04013 | si |

E la guardia che rende sicura la ricerca per sottostringa — senza l'apice di
chiusura nel pattern, `FreekickTaken` matcherebbe dentro `IndirectFreekickTaken`:

| etichetta | qualifier | presente_nei_dati | identificati | collisioni |
|---|---|---:|---:|---|
| corner | CornerTaken | si | 1 |  |
| punizione | FreekickTaken | si | 1 |  |
| punizione_diretta | DirectFreekick | si | 1 |  |
| punizione_indiretta | IndirectFreekickTaken | si | 1 |  |
| rigore | Penalty | si | 1 |  |
| passaggio_chiave | KeyPass | si | 1 |  |
| tiro_assistito | Assisted | si | 1 |  |

### Il qualifier `Penalty` non marca il rigorista


Seconda trappola, indipendente dalla prima. Il qualifier `Penalty` sta su **tutto
cio' che riguarda il rigore**: il fallo di chi l'ha concesso, il `PenaltyFaced`
del portiere, la parata. Solo un quarto dei suoi eventi e' il tiro. Contarlo nudo
avrebbe attribuito «rigori battuti» al difensore che ha commesso il fallo.

Ristretto a `isShot` coincide **riga per riga** con `penaltyScored |
penaltyMissed`, che e' una derivazione indipendente gia' in `events_slim`:

| stagione | da_qualifier | da_booleane | qualifier_senza_isShot | segnati | sbagliati | scarto | conversione |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2021-2022 | 139 | 139 | 536 | 107 | 32 | 0 | 0.7698 |
| 2022-2023 | 106 | 106 | 412 | 83 | 23 | 0 | 0.7830 |
| 2023-2024 | 131 | 131 | 503 | 102 | 29 | 0 | 0.7786 |
| 2024-2025 | 104 | 104 | 401 | 80 | 24 | 0 | 0.7692 |
| 2025-2026 | 106 | 106 | 407 | 81 | 25 | 0 | 0.7642 |

**Scarto zero in tutte e cinque le stagioni.** La colonna
`qualifier_senza_isShot` e' li' per far vedere quanto sarebbe stato l'errore: un
fattore quattro. La conversione 76,4-78,3% riproduce il 76,4% della Fase 1.

Sui corner le due strade coincidono, ed e' cio' che rende il disaccordo sulle
punizioni attribuibile alla colonna e non ai qualifier:

| stagione | da_qualifier | da_colonna | punizioni_da_qualifier | punizioni_da_colonna | scarto_corner | scarto_punizioni |
|---|---:|---:|---:|---:|---:|---:|
| 2021-2022 | 3595 | 3595 | 10767 | 3595 | 0 | 7172 |
| 2022-2023 | 3521 | 3521 | 10035 | 3521 | 0 | 6514 |
| 2023-2024 | 3665 | 3665 | 9879 | 3665 | 0 | 6214 |
| 2024-2025 | 3541 | 3541 | 10251 | 3541 | 0 | 6710 |
| 2025-2026 | 3349 | 3349 | 10402 | 3349 | 0 | 7053 |

### Il test di quadratura non passa alla lettera, e la diagnosi e' misurata


La specifica si aspettava 1-2 rigoristi distinti per squadra-stagione «nella
grande maggioranza dei casi». Contando chiunque abbia battuto **almeno un**
rigore, si osserva:

| rigoristi | squadre_stagione | quota |
|---:|---:|---:|
| 1 | 9 | 0.090 |
| 2 | 38 | 0.380 |
| 3 | 25 | 0.250 |
| 4 | 23 | 0.230 |
| 5 | 2 | 0.020 |
| 6 | 3 | 0.030 |

Che non sia il parsing lo dice `coerenza_rigori`, che e' un controllo **piu'
forte** di questo: due derivazioni indipendenti con scarto zero non possono
sbagliare nello stesso modo. Cio' che si rompe e' la **premessa**. Contando solo
chi ne ha battuti almeno due, l'attesa torna:

| rigoristi | squadre_stagione | quota |
|---:|---:|---:|
| 1 | 46 | 0.529 |
| 2 | 33 | 0.379 |
| 3 | 8 | 0.092 |

E la concentrazione dice quanto «battitore designato» sia un concetto solido:

| squadre_stagione | rigori_mediani | battitori_mediani | quota_primo_mediana | quota_primi_due_mediana | quota_primo_sopra_50pct | primi_due_sopra_80pct |
|---:|---:|---:|---:|---:|---:|---:|
| 86.000 | 6.000 | 3.000 | 0.577 | 0.833 | 0.744 | 0.686 |

**Il battitore principale mediano prende il 57,7% dei rigori della sua squadra**,
i primi due l'83,3%. Un modello che desse tutti i rigori al primo sbaglierebbe di
quasi la meta': e' il numero che E4.3 usa al posto di un'assegnazione secca.


### Il legame passaggio chiave -> tiro


Il legame **non e' nei dati**: la fonte marca il tiro con `Assisted` e il
passaggio con `KeyPass`, ma non dice quale appartenga a quale. Si ricostruisce
con la regola piu' stretta possibile — il passaggio chiave piu' vicino che
precede, della stessa squadra, entro tre eventi — e la quota che resta senza
legame si conta invece di sparire:

| stagione | tiri_assistiti | legati | quota_legata |
|---|---:|---:|---:|
| 2021-2022 | 7228 | 7170 | 0.9920 |
| 2022-2023 | 7157 | 7100 | 0.9920 |
| 2023-2024 | 7321 | 7252 | 0.9906 |
| 2024-2025 | 6889 | 6831 | 0.9916 |
| 2025-2026 | 6956 | 6878 | 0.9888 |

## 2. E4.2 — i cinque fit di xG: la verifica rimandata due volte


E0 l'aveva dichiarata necessaria, E3 aveva potuto evitarla perche' il modello dei
gol non usa l'xG. Qui l'xG attraversa le stagioni sommato, quindi va fatta.

**La forma dei cinque fit e' la stessa.** Un modello poolato con interazioni
stagione x feature **non batte** quello con la sola intercetta di stagione, fuori
campione e con i fold raggruppati per partita:

| disegno | parametri | logloss_fuori_campione | tiri | guadagno_su_intercetta |
|---|---:|---:|---:|---:|
| senza stagione (baseline) | 14 | 0.24634 | 46944 | -0.00013 |
| solo intercetta di stagione | 18 | 0.24622 | 46944 | 0.00000 |
| interazioni stagione x feature | 74 | 0.24671 | 46944 | -0.00050 |

**Il livello no, e la differenza e' grande.** Applicando i cinque fit agli
**stessi** tiri — che e' la domanda letterale, perche' cio' che il progetto usa
sono cinque fit separati:

| fit_della_stagione | tiri_del_fit | xg_medio_sui_tiri_comuni | sd_sui_tiri_comuni | corr_col_primo_fit | scarto_dal_tasso_vero | escursione_relativa |
|---|---:|---:|---:|---:|---:|---:|
| 2021-2022 | 9609.00000 | 0.09843 | 0.13293 | 1.00000 | 0.00651 | 0.15778 |
| 2022-2023 | 9403.00000 | 0.09531 | 0.13102 | 0.98963 | 0.00339 | 0.15778 |
| 2023-2024 | 9570.00000 | 0.09222 | 0.12084 | 0.98627 | 0.00030 | 0.15778 |
| 2024-2025 | 9109.00000 | 0.09023 | 0.11717 | 0.99178 | -0.00169 | 0.15778 |
| 2025-2026 | 9253.00000 | 0.08391 | 0.11611 | 0.98812 | -0.00801 | 0.15778 |

I cinque ordinano i tiri quasi allo stesso modo — correlazione **0,986-1,000**,
che e' "quasi" e non "uguale", e il residuo di forma e' proprio cio' che il test
fuori campione qui sopra dichiara inutile a prevedere. Ma il **livello** si
muove del **15,8%**, monotono e discendente: tre volte la soglia del 5% di E1.

**La risposta alla domanda e' quindi: si', la differenza fra i cinque fit e' di
sola intercetta — e l'intercetta vale il 15,8%.** Ne segue che npxG **non si
somma fra stagioni in unita' grezze**, e che la regola di E1 e' esattamente il
rimedio giusto: dividere per il riferimento di stagione toglie il livello, e la
forma stabile garantisce che non resti altro di rilevante. E' anche il *perche'*
di un verdetto che E1 aveva misurato senza potersi dare una spiegazione:
`xg_per_90` era fra le cinque irriducibili.


## 3. Lo strato feature, e il gate di E1 sulle candidate nuove


Le candidate di E4 sono nuove — npxG, xA, i piazzati — quindi il loro verdetto
non esiste e non si eredita: si misura, con la stessa soglia e la stessa
macchina.

| candidata | prima | ultima | deriva_grezza | deriva_std | verdetto |
|---|---:|---:|---:|---:|---|
| punizioni_dirette_per_90 | 0.0372 | 0.0304 | 0.3544 | 0.1912 | serve effetto di stagione |
| ammonizioni_per_90 | 0.2039 | 0.1642 | 0.2166 | 0.0248 | standardizzata |
| xa_per_90 | 0.0819 | 0.0706 | 0.1492 | 0.0357 | standardizzata |
| rigori_per_90 | 0.0130 | 0.0116 | 0.1469 | 0.1764 | serve effetto di stagione |
| falli_per_90 | 1.1947 | 1.1252 | 0.1182 | 0.0214 | standardizzata |
| npxg_per_90 | 0.1074 | 0.0958 | 0.1143 | 0.0607 | serve effetto di stagione |
| quota_tocchi_area | 0.0410 | 0.0455 | 0.1057 | 0.1150 | serve effetto di stagione |
| gol_per_90 | 0.1120 | 0.1020 | 0.0933 | 0.0996 | serve effetto di stagione |
| passaggi_chiave_per_90 | 0.8414 | 0.7962 | 0.0565 | 0.0189 | standardizzata |
| corner_per_90 | 0.4130 | 0.4081 | 0.0500 | 0.0879 | serve effetto di stagione |

Cinque passano standardizzate, **cinque restano irriducibili** — e npxG e' fra
queste, con la spiegazione appena data. Un effetto di stagione esplicito pero'
**non e' usabile fuori campione**: la stagione bersaglio non e' fra quelle su cui
si e' stimato. Entrano quindi in forma `_rel`, che e' cio' che si puo' fare, e la
conseguenza si misura: la variante «E4 senza le irriducibili» rifa' tutto senza
di loro, e la conclusione non cambia.

Il ponte a `giocatore_id` lascia indietro il 22% delle righe e lo **0,13% dei
minuti**: sono i convocati mai scesi in campo, che la fonte dei voti non elenca
perche' non hanno preso nessun voto.

| righe_totali | righe_perse | quota_righe | quota_minuti | perse_a_zero_minuti | perse_sopra_450_minuti | minuti_massimi_persi |
|---:|---:|---:|---:|---:|---:|---:|
| 3972 | 891 | 0.2243 | 0.00133 | 878 | 4 | 2145 |

## 4. E4.1 — quanto del voto base e' spiegabile, e quanto prevedibile


Sono due domande diverse, e confonderle e' il modo piu' facile di far sembrare
utile un modello che non lo e'. **In campione**, al livello giocatore-stagione:

| modello | parametri | righe | r2_in_campione | sd_residua | sd_totale |
|---|---:|---:|---:|---:|---:|
| intercetta (media di campionato) | 1 | 2388 | 0.0000 | 0.2183 | 0.2183 |
| + ruolo | 4 | 2388 | 0.1161 | 0.2052 | 0.2183 |
| + feature evento | 9 | 2388 | 0.3096 | 0.1814 | 0.2183 |
| + forza di squadra | 11 | 2388 | 0.4085 | 0.1679 | 0.2183 |

Il 41% della varianza del voto medio di stagione si lascia descrivere — ma e' un
**limite superiore**, come il test in campione della Fase 6D, e comprende la
forza di squadra osservata di quella stessa stagione.

**Il tetto vero sta piu' in basso**, e si legge alla riga giocatore-partita:

| raggruppamento | unita | sd_totale | sd_fra | sd_entro | quota_fra |
|---|---:|---:|---:|---:|---:|
| giocatore | 1097.0000 | 0.6037 | 0.2019 | 0.5689 | 0.1118 |
| giocatore-stagione | 2392.0000 | 0.6037 | 0.2183 | 0.5629 | 0.1307 |

**Solo l'11-13% della varianza del voto sta FRA i giocatori**; l'87-89% sta
dentro lo stesso giocatore, cioe' e' la partita, l'avversario, la giornata.
Nessun modello che assegni un numero a un giocatore puo' prenderla. E' la parte
di voto che nessun modello prende, ed e' dichiarata qui accanto al numero e non
in fondo.

Il **risultato di partita**, che la specifica chiedeva fra i regressori, entra in
questa tabella e **non** nel modello predittivo, per una ragione di orologio: il
risultato di una partita di `t` non e' noto all'asta. La forza di squadra e' il
modo in cui quella stessa informazione entra legittimamente — e' cio' che del
risultato si sa prima.


## 5. E4.3 — i rigori, dove l'assegnazione discreta vale piu' di tutto


Un rigorista vale +3 per rigore segnato e -3 per uno sbagliato. Il modello e'
`rigori attesi della squadra x P(e' lui il designato) x tasso di realizzazione`,
con la conversione **quasi interamente shrinkata** verso la media di lega: un
rigorista batte 5-6 rigori in stagione, quindi la sua conversione osservata ha un
errore standard di ~0,18, piu' grande di qualunque differenza vera fra rigoristi.

**I rigori attesi non vengono da E3.1**, e la precisazione non e' pedanteria:
E3.1 modella i gol, e i rigori assegnati sono un'altra grandezza (~0,28 per
partita contro ~1,4 gol). Attribuire a un modello validato una stima che non ha
prodotto sarebbe prendere in prestito la sua validazione.

**Quanto vale spostare il designato**, cioe' l'unico interruttore che all'asta si
gira davvero — le cinque squadre-stagione in cui pesa di piu':

| stagione | teamId | primo | quota_primo | punti_primo_naturale | punti_secondo_se_designato | spostamento |
|---|---:|---:|---:|---:|---:|---:|
| 2024-2025 | 75 | 2194 | 0.714 | 16.65 | 20.05 | 15.75 |
| 2022-2023 | 77 | 785 | 1.000 | 14.49 | 14.46 | 14.46 |
| 2022-2023 | 73 | 2841 | 0.500 | 5.24 | 18.91 | 14.18 |
| 2024-2025 | 84 | 309 | 0.583 | 11.49 | 18.73 | 14.05 |
| 2023-2024 | 2889 | 531 | 0.800 | 12.77 | 15.44 | 13.90 |

**Fino a 15 punti di stagione da un singolo switch.** E' piu' di tutto il divario
medio su cui E4 lavora (2,5 punti di MAE), e va letto cosi': sul singolo
giocatore l'assegnazione del rigorista e' la decisione piu' pesante del blocco,
anche se sulla media di 2.678 righe non si vede. Per il 2026-27 il designato **e'
un input**, non una stima: `punti_rigori(designato={...})` lo impone a mano.


## 6. E4.4 — gli autogol non hanno un effetto individuale

| modello | righe | mae_autogol | guadagno |
|---|---:|---:|---:|
| solo tasso di ruolo | 1066 | 0.1000 | 0.0000 |
| ruolo + effetto individuale | 1066 | 0.1001 | -0.0000 |

Il modello con l'effetto individuale non batte quello col solo tasso di ruolo:
resta il secondo, che e' quello che la specifica prevedeva — **verificato invece
che assunto**.

Sui cartellini, la fonte del malus resta quella dei **voti** e non WhoScored: e'
gia' stabilito da E2 e da E3, ed e' definitoria perche' e' quella che ha prodotto
i `punti_osservati`. WhoScored resta un predittore (`falli_per_90`), mai il
bersaglio.


## 7. La valutazione, sulle stesse quattro transizioni

| variante | componente | righe | mae_punti | divario_chiuso_pct |
|---|---|---:|---:|---:|
| modello d'asta (riferimento) | - | 2678 | 61.4246 | 0.00 |
| E4 voto base | voto | 2678 | 61.4862 | -6.00 |
| E4 bonus | bonus | 2678 | 61.4434 | -1.58 |
| E4 voto + bonus | entrambi | 2678 | 61.5192 | -4.57 |
| E4 senza le irriducibili | entrambi | 2678 | 61.5056 | -3.91 |
| E4 + QI | entrambi | 2678 | 61.3843 | 1.95 |
| SOLO QI, senza le feature evento | entrambi | 2678 | 61.2082 | 10.46 |
| ORACOLO voto noto | voto | 2678 | 60.3989 | 100.00 |
| ORACOLO bonus noto | bonus | 2678 | 60.2385 | 100.00 |
| ORACOLO entrambi noto | entrambi | 2678 | 59.3558 | 100.00 |

Potenza e MDE, dichiarati con lo stesso disegno appaiato di (b):

| variante | righe | delta_mae | se | t | mde_mae | mde_quota_divario_pct |
|---|---:|---:|---:|---:|---:|---:|
| E4 voto base | 2678 | -0.0616 | 0.0398 | -1.546 | 0.1116 | 10.88 |
| E4 bonus | 2678 | -0.0187 | 0.0607 | -0.308 | 0.1702 | 14.35 |
| E4 voto + bonus | 2678 | -0.0946 | 0.0870 | -1.087 | 0.2438 | 11.78 |
| E4 senza le irriducibili | 2678 | -0.0809 | 0.0876 | -0.924 | 0.2453 | 11.86 |
| E4 + QI | 2678 | 0.0404 | 0.0820 | 0.492 | 0.2296 | 11.10 |
| SOLO QI, senza le feature evento | 2678 | 0.2165 | 0.0935 | 2.315 | 0.2620 | 12.66 |

Divari sul campione **fisso** di 2.678 righe: voto 1.026 ·
bonus 1.186 · entrambi 2.069
punti di MAE.

**Le feature da dati evento non aggiungono niente, e sono negative in tutte e tre
le varianti.** Nessuna si avvicina alla propria soglia: |t| massimo 1,55 contro
un MDE dell'11-14% del divario. Il test **non** avrebbe visto un effetto sotto
quella taglia, e va letto cosi' — esclude effetti grandi su un divario che e'
gia' piccolo, non dimostra che l'effetto sia zero.

**L'unica cosa che si muove e' QI da solo**: 10,5% del divario, `t = 2,31`.
Passa la soglia a due code del 5% (1,96) e **non passa Bonferroni** su sei
varianti, che chiede |t| > 2,64. Va riportato come suggestivo e non come
risultato, ed e' esattamente lo standard che (b) ha fissato per se stesso.

**Il contrasto con (b) e' il fatto piu' interessante della sezione.** Li' QI da
solo era *peggio* del modello completo (-0,18%) ed era un complemento; qui QI da
solo e' *meglio* di QI piu' le feature evento (10,5% contro 2,0%). Le feature
evento non sono neutre: peggiorano.


L'errore separato per ruolo, con la variante «E4 voto + bonus»:

| ruolo | righe | mae_base | mae_nuovo | delta |
|---|---:|---:|---:|---:|
| a | 535 | 68.008 | 67.776 | 0.2322 |
| c | 898 | 61.261 | 61.328 | -0.0664 |
| d | 939 | 59.201 | 59.313 | -0.1111 |
| p | 306 | 57.215 | 57.913 | -0.6979 |

E la sensibilita' al pavimento di addestramento, che e' dichiarato e non stimato:

| min_presenze | variante | mae_punti | divario_chiuso_pct |
|---:|---|---:|---:|
| 0 | E4 voto base | 61.4889 | -6.26 |
| 0 | E4 bonus | 61.4501 | -2.14 |
| 0 | E4 voto + bonus | 61.5306 | -5.12 |
| 0 | E4 senza le irriducibili | 61.5175 | -4.49 |
| 0 | E4 + QI | 61.3980 | 1.29 |
| 0 | SOLO QI, senza le feature evento | 61.2124 | 10.26 |
| 5 | E4 voto base | 61.4862 | -6.00 |
| 5 | E4 bonus | 61.4434 | -1.58 |
| 5 | E4 voto + bonus | 61.5192 | -4.57 |
| 5 | E4 senza le irriducibili | 61.5056 | -3.91 |
| 5 | E4 + QI | 61.3843 | 1.95 |
| 5 | SOLO QI, senza le feature evento | 61.2082 | 10.46 |
| 10 | E4 voto base | 61.4874 | -6.12 |
| 10 | E4 bonus | 61.4471 | -1.90 |
| 10 | E4 voto + bonus | 61.5229 | -4.75 |
| 10 | E4 senza le irriducibili | 61.5092 | -4.09 |
| 10 | E4 + QI | 61.3780 | 2.26 |
| 10 | SOLO QI, senza le feature evento | 61.1633 | 12.63 |
| 20 | E4 voto base | 61.4888 | -6.26 |
| 20 | E4 bonus | 61.4415 | -1.42 |
| 20 | E4 voto + bonus | 61.5181 | -4.52 |
| 20 | E4 senza le irriducibili | 61.5030 | -3.79 |
| 20 | E4 + QI | 61.3687 | 2.71 |
| 20 | SOLO QI, senza le feature evento | 61.1284 | 14.32 |

## 8. Domande aperte


1. **Il rating WhoScored non e' nel repository.** La specifica di E4.1 lo chiedeva
   come regressore e non c'e': nessuna delle 259 colonne lo contiene, e le pagine
   grezze non sono state conservate — `createEventsDF` tiene solo gli eventi. E'
   la **terza** domanda della stessa famiglia, e va tenuta appaiata alle altre
   due: **numero di maglia d'agosto** (E2) e **FVM pre-stagione** (E3). Sono tre
   valori che la fonte pubblica, che si acquisirebbero, e che il repository non
   ha; se un giorno si risponde a una si risponde a tutte e tre.
2. **Perche' le feature evento peggiorino invece di essere neutre** non ha una
   spiegazione misurata. Il sospetto e' la solita ridondanza — il modello d'asta
   usa gia' la storia del giocatore, e npxG di t-1 e' un altro modo di dirla — ma
   qui, a differenza delle code di E2, la ridondanza non e' stata misurata contro
   il set del modello d'asta. E' il controllo che manca.
3. **Il divario corretto va riportato all'indietro.** `CLAUDE.md` e i report del
   modello d'asta e di E2 citano il 61,4 -> 52,5 come divario dei bonus. Il numero
   e' riproducibile e resta in tabella, ma la sua **lettura** cambia, e i punti in
   cui e' citato andrebbero rivisti insieme.
4. **Il designato dei rigori per il 2026-27** e' un input che nessuna fonte
   acquisita contiene, e vale fino a 15 punti sul singolo giocatore.
5. **Gli infortuni**, che restano fuori da entrambe le fonti e che dopo E4 sono il
   limite dichiarato del progetto invece che uno fra tanti.

