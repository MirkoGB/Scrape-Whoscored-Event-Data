# Fase 9 / E1 — la regola delle feature, e dove non basta

Generato da `scripts/run_fase9_e1.py` il 2026-08-03.
**Nessuna richiesta di rete, niente scritto sotto `data/raw/`, nessuna stima.**

## Esito in una riga

La regola e' scritta, e' eseguibile ed e' **misurata**: su
19 candidate, 8 possono entrare in unita' grezze
perche' non si muovono, 6 sono risolte dalla standardizzazione, e
**5 non lo sono** — per quelle la stagione deve entrare come effetto
esplicito, che e' l'uscita che la regola stessa prevedeva.

Il risultato che non era scontato e' il **perche'**: la standardizzazione toglie
il *livello* di campionato e non puo' toccare la *forma* della distribuzione. Su
**8 candidate su 19** dividere per la media di
campionato **aggiunge** deriva invece di toglierla, per due meccanismi distinti e
misurati in §4. E' il motivo per cui la regola non e' "standardizza tutto per
riflesso": la guardia **misura** invece di fidarsi del nome della colonna.

## 1. La regola

> Nessuna feature da dati evento entra in un modello multi-stagione in **unita'
> grezze**. Ogni feature entra come **scarto relativo alla media di campionato
> della propria stagione**:
>
> ```
> x_rel = x / m_s - 1
> ```
>
> Dove questo non basta, la stagione entra come **effetto esplicito**.

E' la stessa forma che `CLAUDE.md` prescrive per `rho` — "eccessi relativi alla
media di campionato della stagione, non scarti assoluti" — e nasce dalle stesse
misure: fra le cinque stagioni i tiri in porta per squadra-partita si sono mossi
del 9,2% **per ragioni di gioco**, `Clearance` +48%, `BallRecovery` -26%,
`Error` +162%, `shotCounter` da 3,4% a 7,7% dei tentativi.

**Non e' uno z-score, e la differenza conta.** Dividere anche per la deviazione
standard di stagione normalizzerebbe via la **dispersione**, che e' cio' che
distingue i giocatori, cioe' il segnale. Qui si toglie il livello e si lascia la
scala.

**La regola vive nello strato feature, non nel derivato.** `player_match` e
`team_match` restano in unita' grezze; un test verifica che nessuna colonna `_rel`
sia scesa li'. E la standardizzazione non cancella niente, perche' e' invertibile:
`x = (x_rel + 1) * m_s`, con `m_s` in tabella e un test che ricostruisce le
colonne grezze a meno del floating point. Cancellare la deriva **dentro** il
derivato sarebbe cancellare un fatto misurato in un posto da cui non si recupera
piu' — il vincolo 4.

### Ogni feature e' un rapporto dichiarato, non una colonna

Ogni candidata e' definita come **numeratore su denominatore**, e il riferimento
di campionato e' `somma(num) / somma(den)` su tutte le righe della stagione. Non
e' pedanteria: e' cio' che rende il riferimento **la stessa grandezza** del
valore del singolo. La media delle medie individuali — la scorciatoia — peserebbe
uguale chi ha giocato 90 minuti e chi ne ha giocati 3.000, e un test verifica che
i due numeri siano davvero diversi invece di assumerlo.

## 2. Le 19 candidate

Una riga e' la tripla `(stagione, playerId, teamId)`, cioe' **la stessa
granularita' dell'aggancio di E0**: chi cambia squadra a gennaio ha due righe,
perche' i suoi minuti sono di due squadre diverse. Sono
3972 righe su cinque stagioni.

| feature | famiglia | unita | num / den | descrizione |
|---|---|---|---|---|
| quota_minuti_squadra | esposizione | quota | minuti / minuti_squadra | minuti del giocatore sui minuti-giocatore della sua squadra |
| quota_presenze | esposizione | quota | presenze / partite_squadra | partite giocate sulle partite ACQUISITE della sua squadra |
| quota_titolare | esposizione | quota | da_titolare / partite_squadra | partite da titolare sulle partite acquisite della squadra |
| minuto_medio_ingresso | esposizione | minuto | somma_ingresso / ingressi | minuto espanso medio d'ingresso, sui soli subentri |
| minuto_medio_uscita | esposizione | minuto | somma_uscita / da_titolare | minuto medio di uscita, sulle sole partite da titolare |
| tiri_per_90 | produzione | per_90 | tiri / novantesimi | tentativi per 90 minuti |
| sot_per_90 | produzione | per_90 | sot / novantesimi | tiri in porta per 90 minuti |
| gol_per_90 | produzione | per_90 | gol / novantesimi | gol per 90 minuti |
| xg_per_90 | produzione | per_90 | xg / novantesimi | xG interno per 90 minuti |
| tocchi_per_90 | coinvolgimento | per_90 | tocchi / novantesimi | tocchi per 90 minuti: quanto la squadra passa da lui |
| passaggi_per_90 | coinvolgimento | per_90 | passaggi / novantesimi | passaggi tentati per 90 minuti |
| precisione_passaggi | coinvolgimento | quota | passaggi_riusciti / passaggi | quota di passaggi riusciti |
| quota_tocchi_area | coinvolgimento | quota | tocchi_area / tocchi | quota dei tocchi dentro l'area avversaria |
| x_medio | coinvolgimento | coordinata | somma_x / tocchi | ascissa media dei tocchi, in coordinate Opta 0-100 |
| azioni_difensive_per_90 | difesa | per_90 | azioni_difensive / novantesimi | contrasti, intercetti e respinte per 90 minuti |
| falli_per_90 | difesa | per_90 | falli / novantesimi | falli commessi per 90 minuti, come predittore dei cartellini |
| ammonizioni_per_90 | difesa | per_90 | ammonizioni / novantesimi | cartellini gialli per 90 minuti |
| quota_porta_inviolata | difesa | quota | partite_porta_inviolata / presenze | quota delle sue partite chiuse senza subire gol |
| gol_subiti_per_partita | difesa | gol_partita | gol_subiti_pesati / minuti | gol subiti dalla squadra nelle sue partite, pesati sui suoi minuti |

I denominatori di squadra **si contano, non si assumono**, ed e' la lezione di E0
propagata qui: l'Atalanta ha 35 partite nel 2021-22 e nel 2022-23, e un test lo
verifica. Con 38 al denominatore ogni quota di esposizione sarebbe sbagliata
proprio dove sbagliare costa di piu', perche' la perdita alla fonte **non e'
casuale rispetto alla squadra**.

## 3. La deriva, prima e dopo

Le due colonne sono confrontabili perche' sono nella stessa unita': entrambe sono
escursioni **relative** della media di stagione. La soglia dichiarata e'
**5,0%**.

| feature | famiglia | prima | ultima | deriva_grezza | deriva_std | verdetto |
|---|---|---:|---:|---:|---:|---|
| quota_porta_inviolata | difesa | 0.246 | 0.328 | 0.290 | 0.023 | standardizzata |
| ammonizioni_per_90 | difesa | 0.202 | 0.164 | 0.207 | 0.034 | standardizzata |
| gol_subiti_per_partita | difesa | 1.407 | 1.211 | 0.152 | 0.016 | standardizzata |
| azioni_difensive_per_90 | difesa | 3.545 | 3.768 | 0.139 | 0.044 | standardizzata |
| falli_per_90 | difesa | 1.191 | 1.130 | 0.114 | 0.031 | standardizzata |
| xg_per_90 | produzione | 0.117 | 0.105 | 0.106 | 0.075 | serve effetto di stagione |
| quota_tocchi_area | coinvolgimento | 0.041 | 0.045 | 0.102 | 0.139 | serve effetto di stagione |
| gol_per_90 | produzione | 0.112 | 0.102 | 0.091 | 0.093 | serve effetto di stagione |
| tiri_per_90 | produzione | 1.123 | 1.107 | 0.057 | 0.059 | serve effetto di stagione |
| passaggi_per_90 | coinvolgimento | 36.801 | 34.819 | 0.056 | 0.018 | standardizzata |
| sot_per_90 | produzione | 0.378 | 0.361 | 0.052 | 0.065 | serve effetto di stagione |
| tocchi_per_90 | coinvolgimento | 52.966 | 50.609 | 0.047 | 0.013 | grezza ammessa |
| quota_presenze | esposizione | 0.652 | 0.654 | 0.032 | 0.092 | grezza ammessa |
| quota_minuti_squadra | esposizione | 0.044 | 0.043 | 0.026 | 0.113 | grezza ammessa |
| precisione_passaggi | coinvolgimento | 0.793 | 0.809 | 0.025 | 0.006 | grezza ammessa |
| minuto_medio_ingresso | esposizione | 67.464 | 68.591 | 0.025 | 0.008 | grezza ammessa |
| quota_titolare | esposizione | 0.490 | 0.480 | 0.024 | 0.122 | grezza ammessa |
| x_medio | coinvolgimento | 47.861 | 48.719 | 0.018 | 0.022 | grezza ammessa |
| minuto_medio_uscita | esposizione | 84.081 | 83.921 | 0.012 | 0.006 | grezza ammessa |

**La soglia e' dichiarata prima, non ricavata dopo** (vincolo 1 applicato a una
soglia, come gia' fatto per l'80'): 5,0% sta **sotto** la piu'
piccola deriva reale gia' misurata nel repository — i tiri in porta per
squadra-partita, -9,2% — e **molto sopra** l'errore di campionamento di una media
di campionato su 17.000 righe. Un test verifica che sia una costante letterale e
che nel modulo non compaiano `argmax`, `idxmax` o `quantile`.

Le medie di stagione si misurano sulle righe con almeno
**450 minuti** (96,7% dei minuti totali, e
poco piu' della meta' delle righe). Il **riferimento** invece usa tutto: il
riferimento e' il campionato, non i titolari. Senza il pavimento la media di
stagione di un tasso per 90 sarebbe dominata dagli spezzoni di tre minuti, dove
il denominatore e' minuscolo.

### I tre verdetti

- **grezza ammessa** (8): non si muove oltre la soglia. Puo' entrare
  cosi' com'e', e per alcune standardizzarla sarebbe **dannoso** — vedi §4.
- **standardizzata** (6): la regola fa il suo lavoro. Il caso migliore e'
  `quota_porta_inviolata`, che passa da
  29,0% a
  2,3%: le porte inviolate
  sono aumentate del 29% fra le cinque stagioni — si segna meno — e in unita'
  grezze un difensore del 2021-22 e uno del 2025-26 non sarebbero confrontabili.
- **serve effetto di stagione** (5): `xg_per_90`, `quota_tocchi_area`, `gol_per_90`, `tiri_per_90`, `sot_per_90`.
  La standardizzazione non basta, e non e' un fallimento del calcolo: e' il caso
  che la regola prevede. Chi le usa in un modello multi-stagione deve portarsi
  dietro un effetto di stagione, e puo' chiederlo al codice
  (`richiede_effetto_stagione`) invece di leggerlo qui.

**Sono quasi tutte della famiglia produzione**, e la coincidenza non e' tale:
tiri, tiri in porta, gol, xG e tocchi in area sono le grandezze **concentrate su
pochi giocatori**, cioe' quelle in cui la forma della distribuzione pesa piu' del
livello.

## 4. Perche' a volte non basta, e a volte peggiora

E' la parte del blocco che non era prevista, e il meccanismo si misura invece di
raccontarlo. Due grandezze, tenute separate:

- **`deriva_riferimento`** — di quanto si muove la media di campionato pesata,
  cioe' il **livello**. E' esattamente cio' che la standardizzazione toglie;
- **`deriva_popolazione`** — di quanto si muove la media non pesata fra i
  giocatori sopra il pavimento, cioe' la **forma** e la composizione di chi gioca.

| feature | deriva_riferimento | deriva_popolazione | stesso_verso |
|---|---:|---:|---:|
| quota_porta_inviolata | 0.272 | 0.290 | si |
| ammonizioni_per_90 | 0.239 | 0.207 | si |
| gol_per_90 | 0.175 | 0.091 | si |
| xg_per_90 | 0.175 | 0.106 | si |
| gol_subiti_per_partita | 0.157 | 0.152 | si |
| azioni_difensive_per_90 | 0.155 | 0.139 | si |
| falli_per_90 | 0.119 | 0.114 | si |
| sot_per_90 | 0.113 | 0.052 | si |
| tiri_per_90 | 0.080 | 0.057 | si |
| quota_presenze | 0.074 | 0.032 | si |
| quota_titolare | 0.065 | 0.024 | no |
| quota_minuti_squadra | 0.065 | 0.026 | no |
| quota_tocchi_area | 0.056 | 0.102 | no |
| passaggi_per_90 | 0.041 | 0.056 | si |
| tocchi_per_90 | 0.040 | 0.047 | si |
| precisione_passaggi | 0.023 | 0.025 | si |
| minuto_medio_ingresso | 0.017 | 0.025 | si |
| minuto_medio_uscita | 0.011 | 0.012 | no |
| x_medio | 0.011 | 0.018 | no |

Se le due coincidono, dividere per il riferimento azzera la deriva. Se divergono
resta un residuo, e i due modi in cui divergono danno due esiti diversi.

**Primo meccanismo — sovracorrezione**, e riguarda
`gol_per_90`, `sot_per_90`, `tiri_per_90`. Le due derive vanno nello stesso
verso ma con ampiezze diverse. Su `sot_per_90` il livello di campionato scende del
11,3% mentre il tasso del
giocatore tipico scende del
5,2%: dividere per il primo toglie
piu' di quanto ce ne sia nel secondo, e il residuo cambia segno. Detto altrimenti,
**la caduta dei tiri in porta non e' distribuita uniformemente sui giocatori**, ed
e' un fatto sul gioco, non un difetto del conto. Stesso schema su `gol_per_90`
(17,5% contro
9,1%) e su `xg_per_90`.

**Secondo meccanismo — versi opposti**, e riguarda
`quota_tocchi_area`, `x_medio`. Su `quota_tocchi_area` il
riferimento **scende** mentre la media fra i giocatori **sale** del
10,2%, e la deriva passa da
10,2% grezza a
13,9% standardizzata: si tocca
**meno** in area per tocco a livello di campionato e **piu'** per giocatore che
gioca, il che vuol dire che i tocchi in area si stanno concentrando.

Il verso opposto **non basta da solo** a peggiorare le cose: `minuto_medio_uscita`
va in verso opposto e migliora lo stesso, perche' il suo riferimento si sposta
dell'1,1%, e un verso contrario su un movimento che non c'e' non sposta niente.
Serve che il riferimento si muova davvero — ed e' la condizione doppia che un test
verifica.

**Il terzo caso non e' un meccanismo, e' un errore di grandezza**, e riguarda le
tre quote di esposizione (`quota_minuti_squadra`, `quota_presenze`, `quota_titolare`), di cui
3 peggiorano standardizzate. La causa e' identificata e non
e' il verso: per queste `somma(num)/somma(den)` **non e' "la quota del giocatore
tipico"**, e' la quota media su **tutta la rosa convocata**, panchinari compresi —
per `quota_titolare` vale esattamente `11 / ampiezza della rosa`. E' un fatto sulle
**rose**, non sui giocatori. Si vede a occhio nudo — riferimento
0,272 contro media fra i
giocatori 0,490: due numeri che
non possono essere la stessa grandezza. Standardizzare importa nella feature la
deriva delle rose, e `quota_titolare` passa da
2,4% grezza a
12,2% standardizzata.
**Restano grezze**, e possono: la loro deriva grezza sta sotto la soglia.

> **La lezione per E2 ed E4**: la standardizzazione non e' gratis e non e' un
> riflesso. Va applicata dove la deriva e' di livello, e la guardia serve proprio
> a distinguere i due casi **misurando**, invece di fidarsi del suffisso nel nome
> della colonna.

### Il verdetto dipende dal pavimento di esposizione?

`MIN_MINUTI_DERIVA` e' una scelta dichiarata, quindi si mostra quanto il
risultato le deve, su quattro pavimenti (3, 5, 10 e 20 partite intere).

| feature | 270' | 450' | 900' | 1800' |
|---|---|---|---|---|
| ammonizioni_per_90 | serve effetto di stagione | standardizzata | standardizzata | standardizzata |
| azioni_difensive_per_90 | standardizzata | standardizzata | standardizzata | serve effetto di stagione |
| falli_per_90 | standardizzata | standardizzata | standardizzata | standardizzata |
| gol_per_90 | serve effetto di stagione | serve effetto di stagione | serve effetto di stagione | serve effetto di stagione |
| gol_subiti_per_partita | standardizzata | standardizzata | standardizzata | standardizzata |
| minuto_medio_ingresso | grezza ammessa | grezza ammessa | grezza ammessa | grezza ammessa |
| minuto_medio_uscita | grezza ammessa | grezza ammessa | grezza ammessa | grezza ammessa |
| passaggi_per_90 | standardizzata | standardizzata | grezza ammessa | grezza ammessa |
| precisione_passaggi | grezza ammessa | grezza ammessa | grezza ammessa | grezza ammessa |
| quota_minuti_squadra | grezza ammessa | grezza ammessa | grezza ammessa | grezza ammessa |
| quota_porta_inviolata | standardizzata | standardizzata | standardizzata | standardizzata |
| quota_presenze | grezza ammessa | grezza ammessa | grezza ammessa | grezza ammessa |
| quota_titolare | grezza ammessa | grezza ammessa | grezza ammessa | grezza ammessa |
| quota_tocchi_area | serve effetto di stagione | serve effetto di stagione | serve effetto di stagione | serve effetto di stagione |
| sot_per_90 | serve effetto di stagione | serve effetto di stagione | standardizzata | serve effetto di stagione |
| tiri_per_90 | grezza ammessa | serve effetto di stagione | standardizzata | serve effetto di stagione |
| tocchi_per_90 | standardizzata | grezza ammessa | grezza ammessa | grezza ammessa |
| x_medio | grezza ammessa | grezza ammessa | grezza ammessa | grezza ammessa |
| xg_per_90 | serve effetto di stagione | serve effetto di stagione | serve effetto di stagione | serve effetto di stagione |

**3 candidate stanno oltre la soglia a ogni pavimento**
(`gol_per_90`, `quota_tocchi_area`, `xg_per_90`): quello e' un risultato che il pavimento
non decide. Le altre due non risolte a 450' — `sot_per_90`, `tiri_per_90` — cambiano verdetto al variare del pavimento, e vanno trattate come **non risolte** lo stesso: e' il verso prudente.

In totale **6 candidate su 19 cambiano verdetto**
fra i quattro pavimenti (`ammonizioni_per_90`, `azioni_difensive_per_90`, `passaggi_per_90`, `sot_per_90`, `tiri_per_90`, `tocchi_per_90`), e il movimento
va in entrambe le direzioni: `ammonizioni_per_90` peggiora abbassando il pavimento,
`azioni_difensive_per_90` peggiora alzandolo. Il pavimento non e' un dettaglio di
implementazione, ed e' meglio saperlo adesso che scoprirlo in E2 quando cambiera'
per un'altra ragione.

## 5. Corollario 1 — nessuna feature sul nome di un qualifier senza verifica

`StandingSave` e' la dimostrazione che **il nome di un qualifier non e' un
identificatore**: sta sul 71% di tutti gli eventi nelle prime quattro stagioni e
sul 4% nel 2025-26, a schema, conteggio colonne e numero di eventi invariati.
Non e' una parata che sparisce, e' la stessa etichetta su id diversi — due
versioni del dizionario della fonte.

Il gate (`verifica_qualifier`) chiede due cose: presenza in **tutte e cinque** le
stagioni, e rapporto fra frequenza massima e minima per evento sotto
**1.5**.

| qualifier | stagioni | min | max | rapporto | ammesso |
|---|---:|---:|---:|---:|---:|
| CornerTaken | 5 | 0.00595 | 0.00645 | 1.08 | si |
| FreekickTaken | 5 | 0.01739 | 0.01866 | 1.07 | si |
| Penalty | 5 | 0.00077 | 0.00100 | 1.30 | si |
| ThrowIn | 5 | 0.02434 | 0.02669 | 1.10 | si |
| BigChance | 5 | 0.00226 | 0.00274 | 1.22 | si |
| KeyPass | 5 | 0.01239 | 0.01289 | 1.04 | si |
| StandingSave | 5 | 0.04278 | 0.72609 | 16.97 | no |
| OtherBodyPart | 5 | 0.00034 | 0.01031 | 30.06 | no |

La soglia e' scelta cosi': 1.5 e' il punto oltre il quale il
movimento non e' piu' compatibile con cio' che il **gioco** ha fatto — la deriva
piu' grande mai misurata su un tipo di evento e' `Clearance` +48%. I due casi noti
di dizionario cambiato stanno a
17x e
30x, cioe' un ordine di grandezza oltre:
**non e' un numero delicato**, e non e' stato scelto per far passare qualcuno.

**Il gate e' necessario e non sufficiente**, e va detto: un qualifier che lo passa
non e' *dimostrato* essere la stessa cosa in tutte le stagioni. L'unico controllo
sufficiente sarebbe l'**id numerico**, che `acquisition/whoscored/main.py:432`
butta via tenendo solo il `displayName`. Il gate esclude i casi in cui il nome ha
cambiato significato in modo **visibile**.

**Nessuna candidata di oggi usa qualifier**, e non per virtu': `events_slim` non
porta la colonna `qualifiers` — la tiene solo per i cinque tipi di evento di
formazione — quindi una feature sui piazzati vuole una rilettura dei 1.889 CSV, ed
e' un costo che paga E4. La guardia esiste lo stesso, e un test costruisce una
candidata finta che dichiara `StandingSave` e pretende che venga fermata: senza
quella prova, "nessuna candidata usa qualifier" potrebbe voler dire "la guardia
non guarda niente".

## 6. Corollario 3 — le 72 colonne mai valorizzate, e cosa si deriva

Sono **72**, misurate col criterio giusto: **"ne' nullo ne' `False`"**, non
`notna()`. Lo scraper del fork scrive il literal `False` dove il campo della fonte
e' assente, quindi `notna()` dichiarerebbe valorizzate al 100% circa 200 colonne
su 259 che valorizzate non sono — un test verifica che la differenza fra le due
misure esista davvero sui dati, invece di ripeterla a parole.

| grandezza | colonna_della_fonte | derivazione | feature |
|---|---|---|---|
| porta inviolata | cleanSheet* (17 colonne) | gol dell'avversario nella stessa partita == 0 | quota_porta_inviolata |
| gol subiti | goalConcededByTeam* (17 colonne) | `goals` della riga avversaria di `team_match` | gol_subiti_per_partita |
| precisione dei passaggi | passAccuracy | passAccurate / (passAccurate + passInaccurate) | precisione_passaggi |

Le tre grandezze che qualcuno cercherebbe li' — **porta inviolata, gol subiti,
precisione dei passaggi** — sono esattamente quelle che servono al voto base e al
modificatore, ed esistono nello schema con un nome invitante e nessun valore.
Si derivano.

**La garanzia piu' forte non e' la disciplina, e' l'impossibilita'**: `io_events`
tiene ~60 colonne su 259 e **nessuna delle 72 e' fra quelle**, quindi una feature
non puo' leggerle nemmeno per errore. Un test lo verifica sull'elenco delle
colonne caricate, cosi' che allargarlo un domani faccia scattare la guardia.

## 7. La guardia, che e' il deliverable vero

```python
FG.verifica_standardizzazione(feat, colonne_che_sto_per_usare)
```

Va chiamata da chiunque faccia entrare colonne di questa tabella in un modello
che attraversa le stagioni. Solleva `FeatureNonStandardizzata` elencando le
colonne colpevoli con la loro deriva.

**Non distingue "grezza" da "standardizzata" guardando il nome: misura.** Una
colonna grezza che non si muove passa — e ce ne sono 8 — e una colonna
`_rel` che si muove lo stesso viene fermata. Quest'ultimo e' il caso
interessante, perche' e' quello che il suffisso da solo nasconderebbe, e un test
lo verifica iniettando un gradino del 20% in una colonna `_rel` sana e
pretendendo che la guardia lo veda.

## 8. Cosa e' stato prodotto

| | |
|---|---|
| `sot/features_giocatore.py` | il registro, la standardizzazione, il gate e la guardia |
| `data/processed/ITA-serie-a/fase9_feature_giocatore.parquet` | 3972 righe x 70 colonne |
| `data/processed/ITA-serie-a/fase9_feature_riferimenti.parquet` | 95 righe, **stesso schema** di `fase9_medie_campionato` |
| `reports/fase9_e1_*.csv` | le tavole di questo report |
| `tests/test_fase9_e1.py` | i tre corollari come test |

I riferimenti hanno lo stesso schema delle medie di campionato di E0 e stanno in
un **file separato** per una ragione operativa e non concettuale:
`run_fase9_e0.py` riscrive il proprio Parquet per intero a ogni esecuzione,
quindi righe di E1 appese li' sparirebbero al primo rilancio di E0 senza che
nessuno se ne accorga.

## Domande aperte

1. **Il riferimento giusto per le quote di esposizione non e' quello di
   campionato**, ed e' §4: per `quota_titolare` la media pesata vale `11/rosa`.
   Oggi restano grezze perche' la loro deriva grezza e' sotto soglia, e va bene;
   ma se un domani l'ampiezza delle rose si muovesse davvero, servirebbe un
   riferimento diverso — la media fra i giocatori sopra un pavimento — e quella
   scelta dipenderebbe dal pavimento. Non e' stata presa qui.
2. **`xg_per_90` ha un problema in piu' degli altri quattro.** I cinque fit di xG
   sono **cinque modelli**, non cinque livelli: la standardizzazione ne toglie il
   livello e lascia intatto il resto. Un effetto di stagione lo copre solo se la
   differenza fra i fit e' un'intercetta, e questo non e' stato verificato.
3. **La stabilita' della posizione media in campo** — uno dei candidati di E2 —
   non e' un rapporto e quindi non entra in questo registro, che e' costruito su
   rapporti perche' e' cio' che rende il riferimento la stessa grandezza. Una
   dispersione vuole un'altra forma di standardizzazione, e va decisa in E2.
4. **La riga e' `(stagione, playerId, teamId)` e il modello d'asta lavora su
   `giocatore_id`.** Portare la tabella al livello del modello vuole una
   decisione — sommare le due meta' di stagione di chi si trasferisce, oppure
   tenere la squadra principale — che cambia il significato di ogni quota di
   esposizione. E' lavoro di E2, non di questo blocco.
5. **`quota_presenze` ha il calendario intero al denominatore anche per chi
   arriva a gennaio**, quindi sottostima l'impiego dei nuovi arrivati. Il rimedio
   sarebbe restringere il denominatore alla finestra di permanenza, che i dati
   non registrano direttamente.
6. **Le squalifiche non sono ancora qui.** `ammonizioni_per_90` e' l'ingresso, ma
   la regola delle cinque ammonizioni e' **deterministica** e va applicata alla
   sequenza dentro la stagione, non a un tasso. E' il pezzo gratis di E2.
