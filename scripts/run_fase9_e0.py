# -*- coding: utf-8 -*-
"""Fase 9 / Blocco E0 — `player_match` sulle cinque stagioni + aggancio esteso.

    ./.venv/Scripts/python.exe scripts/run_fase9_e0.py [--force]

**Non tocca la rete e non scrive niente sotto `data/raw/`.** Legge i 1.889 CSV
gia' acquisiti, costruisce `shots` / `team_match` / `player_match` per ognuna
delle cinque stagioni, la tabella delle medie di campionato, la diagnostica dei
cinque fit di xG, ed estende l'aggancio dei giocatori a tutte e cinque.

`--force` rilegge i CSV grezzi invece della cache degli eventi (~3 min in piu').
"""

from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sot import aggancio as AG, aggregate, config, multistagione as MS  # noqa: E402

OUT_MD = config.REPORTS / "fase9_e0_player_match_5_stagioni.md"


def _tab(df: pd.DataFrame, dec: dict[str, int] | None = None) -> str:
    """Tabella markdown. **Nessun separatore delle migliaia**, di proposito.

    La prima versione ne metteva uno all'italiana, e nella stessa tabella
    finivano `16.666` (sedicimila righe) e `4.441` (quattro tiri e mezzo): due
    numeri con lo stesso punto e due significati. Su `1037.2` produceva
    addirittura `1.037.2`. Un separatore che rende un numero ambiguo e' peggio
    di nessun separatore.
    """
    dec = dec or {}
    num = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]

    def cella(c, v) -> str:
        if pd.isna(v):
            return ""
        if c in dec:
            return f"{v:.{dec[c]}f}"
        if c in num and float(v) == int(v):
            return str(int(v))
        if c in num:
            return f"{v:.3f}"
        return str(v).replace("|", r"\|")

    testa = "| " + " | ".join(str(c) for c in df.columns) + " |"
    sep = "|" + "|".join("---:" if c in num else "---" for c in df.columns) + "|"
    righe = ["| " + " | ".join(cella(c, v) for c, v in zip(df.columns, r)) + " |"
             for r in df.itertuples(index=False)]
    return "\n".join([testa, sep, *righe])


def _mila(n) -> str:
    return f"{int(n):,}".replace(",", ".")


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--force", action="store_true",
                   help="rilegge i 1.889 CSV grezzi invece della cache")
    args = p.parse_args(argv)

    print("costruzione delle cinque stagioni (puo' richiedere qualche minuto)...")
    riepilogo = MS.costruisci(force=args.force)
    for r in riepilogo.itertuples(index=False):
        print(f"  {r.stagione}  {r.partite:3d} partite  "
              f"{r.giocatore_partita:6d} righe giocatore  SoT/partita {r.sot_per_squadra_partita:.3f}")

    print("stato di impiego...")
    pm = MS.carica("player_match")
    stati = (pm.pivot_table(index="stato", columns="stagione",
                            values="playerId", aggfunc="size")
             .reindex(list(aggregate.STATI_IMPIEGO)).reset_index())
    rosa = (pm.groupby(["stagione", "matchId", "teamId"]).size()
            .rename("convocati").reset_index())

    print("medie di campionato...")
    medie = MS.medie_campionato()
    der = MS.deriva(medie)
    medie.to_parquet(config.MEDIE_STAGIONE, index=False)

    print("diagnostica dei cinque fit di xG...")
    dxg = MS.diagnostica_xg()
    dxg.to_parquet(config.XG_DIAGNOSTICA, index=False)

    print("denominatori...")
    per_squadra = MS.partite_per_squadra()
    anomali = MS.denominatori_anomali()

    print("aggancio dei giocatori sulle cinque stagioni...")
    agg = MS.aggancio_giocatori()
    coer = MS.coerenza_fra_stagioni(agg["mappa"])
    riep_coer = MS.riepilogo_coerenza(agg["mappa"], coer)

    # Coda di E0: il residuo nell'altro verso, con identita' e minuti. Finche'
    # era un conteggio si leggeva come "quattro comparse"; il massimo dice altro.
    residuo_ws = MS.residuo_whoscored(mappa=agg["mappa"])
    riep_res_ws = MS.riepilogo_residuo_whoscored(residuo_ws)
    corr_res = MS.corrispondenza_residui(agg["irrisolti"], residuo_ws)

    AG.MAPPING_DIR.mkdir(parents=True, exist_ok=True)
    agg["mappa"].to_csv(AG.GIOCATORI_CSV, index=False)
    if len(agg["irrisolti"]):
        agg["irrisolti"].to_csv(AG.IRRISOLTI_CSV, index=False)
    elif AG.IRRISOLTI_CSV.is_file():
        AG.IRRISOLTI_CSV.unlink()
    if len(residuo_ws):
        residuo_ws.to_csv(AG.RESIDUO_WS_CSV, index=False)
    elif AG.RESIDUO_WS_CSV.is_file():
        AG.RESIDUO_WS_CSV.unlink()

    for nome, df in (("fase9_e0_riepilogo", riepilogo),
                     ("fase9_e0_medie_campionato", medie),
                     ("fase9_e0_deriva", der),
                     ("fase9_e0_xg_diagnostica", dxg),
                     ("fase9_e0_partite_per_squadra", per_squadra),
                     ("fase9_e0_aggancio_tasso", agg["tasso"]),
                     ("fase9_e0_coerenza_discordi", coer["discordi_fc"]),
                     ("fase9_e0_residuo_ws", residuo_ws),
                     ("fase9_e0_residuo_ws_riepilogo", riep_res_ws),
                     ("fase9_e0_corrispondenza_residui", corr_res)):
        df.to_csv(config.REPORTS / f"{nome}.csv", index=False)

    tasso = agg["tasso"]
    rc = riep_coer.iloc[0]
    tot_pm = int(riepilogo["giocatore_partita"].sum())
    tot_csv = int(riepilogo["partite"].sum())

    der_cols = ["grandezza", "unita", "prima", "ultima", "deriva_pct", "ampiezza_pct"]
    der_dec = {"prima": 3, "ultima": 3, "deriva_pct": 1, "ampiezza_pct": 1}

    # Le tabelle si compongono qui e non dentro l'f-string: un dict letterale
    # dentro un'espressione di f-string va scritto con graffe singole, mentre il
    # testo attorno ne vuole di doppie. Tenere le due cose separate e' meno
    # elegante e molto meno facile da sbagliare.
    t_riepilogo = _tab(riepilogo, {"sot_per_squadra_partita": 3})
    t_anomali = _tab(anomali[["stagione", "team", "partite", "sot", "sot_per_partita"]],
                     {"sot_per_partita": 3})
    t_dxg = _tab(dxg, {"tasso_base": 4, "logloss": 4, "logloss_base": 4, "auc": 3,
                       "somma_xg": 1, "calibrazione_pct": 2})
    t_der_alta = _tab(der.head(8)[der_cols], der_dec)
    t_der_bassa = _tab(der.tail(5)[der_cols], der_dec)
    t_tasso = _tab(tasso, {"tasso": 4, "jaccard_medio": 4, "jaccard_min": 3})
    t_res_ws = _tab(riep_res_ws, {"minuti_mediana": 1, "quota_minuti_pct": 3})
    t_res_ws_righe = _tab(
        residuo_ws.reindex(columns=["stagione", "team", "playerName", "minuti",
                                    "presenze", "da_titolare"]), {})
    t_corr_res = _tab(corr_res.reindex(
        columns=["stagione", "team", "nome_fc", "presenze_fc", "playerName",
                 "minuti", "unico"]), {})
    n_irr_tot = int(tasso["irrisolti"].sum())
    n_corr_unici = int(corr_res["unico"].sum()) if len(corr_res) else 0
    n_corr_coperti = (int(corr_res.groupby(["stagione", "nome_fc"]).ngroups)
                      if len(corr_res) else 0)

    # Gli irrisolti col loro percentile nella distribuzione degli agganciati:
    # e' la lettura che dice se il residuo sta tutto sui giocatori rari.
    irr = agg["irrisolti"].reindex(
        columns=["stagione", "nome_fc", "presenze_fc", "motivo", "nomi_candidati"])
    pres_ok = agg["mappa"]["presenze_fc"]
    irr = irr.sort_values("presenze_fc").copy()
    irr["percentile"] = [f"{(pres_ok < v).mean():.0%}" for v in irr["presenze_fc"]]
    irr = irr[["stagione", "nome_fc", "presenze_fc", "percentile", "motivo",
               "nomi_candidati"]]
    t_irr = _tab(irr)
    t_stati = _tab(stati)

    testo = f"""# Fase 9 / E0 — `player_match` sulle cinque stagioni, e l'aggancio esteso

Generato da `scripts/run_fase9_e0.py` il {date.today().isoformat()}.
**Nessuna richiesta di rete, niente scritto sotto `data/raw/`.**

## Esito in una riga

Le tabelle di Fase 1 esistono ora per tutte e cinque le stagioni —
**{_mila(tot_pm)} righe giocatore-partita** su {_mila(tot_csv)} partite — e
l'aggancio dei giocatori copre **{_mila(int(tasso['righe'].sum()))} triple
`(stagione, squadra, giocatore)`** con **{int(tasso['irrisolti'].sum())}
irrisolti**, tutti dichiarati. Il prerequisito della Fase 9 e' chiuso: da qui in
poi esiste un walk-forward.

Il controllo che una stagione sola non poteva fare — **lo stesso giocatore deve
prendere lo stesso `playerId` in ogni stagione** — passa su
**{_mila(rc['controlli_incrociati'])} confronti indipendenti con zero
discordanze**, in entrambi i versi.

## 1. Le cinque stagioni

{t_riepilogo}

**I tiri in porta per squadra-partita scendono del 9,2% fra la prima e
l'ultima stagione**, ed e' il fatto gia' misurato dalla verifica di stabilita':
il *criterio di rilevazione* e' fermo — la definizione coincide con il flag Opta
nativo in tutte e cinque, zero discordanze su 47.530 tentativi — ma il *livello*
si muove. Si tira di meno, non si conta diversamente.

Ne segue la ragione per cui questo blocco produce una tabella di riferimento
invece che tabelle gia' normalizzate: +1 tiro di eccesso non significa la stessa
cosa nel 2021-22 e nel 2025-26.

## 2. I denominatori si contano, non si assumono

{t_anomali}

Sono **{len(anomali)} righe su {len(per_squadra)}** in cui il denominatore non e'
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

{t_dxg}

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
**{_mila(int((pm['stato'] == 'panchina').sum()))} righe a zero minuti, il
{(pm['stato'] == 'panchina').mean():.1%} della tabella**.

Erano pero' leggibili solo da chi sapesse che `minutes == 0` significa
"convocato e mai entrato" e non "dato mancante" — e quella e' la distinzione che
un modello dell'impiego (E2) non puo' permettersi di sbagliare.

{t_stati}

I titolari sono **11 per squadra-partita in ogni partita di ogni stagione**, e un
test lo verifica: e' il controllo che `InvolvedPlayers` e' stato letto bene, non
una curiosita'.

**Il quarto stato e' l'assenza della riga.** Chi non e' stato convocato affatto —
fuori lista, infortunato, squalificato, ceduto — non compare, e non ha
un'etichetta perche' non ha una riga a cui attaccarla. Chi ricostruisce l'impiego
deve costruirsi il denominatore della rosa **da fuori**, invece di contare le
righe: WhoScored registra i convocati, non i tesserati. E' un limite del
derivato, non un difetto, e va portato in E2 esplicitamente.

La rosa convocata sta fra {int(rosa['convocati'].min())} e
{int(rosa['convocati'].max())} giocatori, mediana {rosa['convocati'].median():.0f}.
Un solo caso su {_mila(len(rosa))} sta sotto i 18 convocati.

## 5. Le medie di campionato, `stagione x grandezza`

`data/processed/ITA-serie-a/fase9_medie_campionato.parquet`, forma lunga
(`stagione`, `grandezza`, `unita`, `media`, `n`). **Non e' una colonna ripetuta
su ogni riga di `player_match`**: una media di campionato e' un fatto *di
stagione*, non *di riga*. Forma lunga e non larga perche' E1 aggiungera' le sue
grandezze, e una tabella larga andrebbe migrata a ogni giro.

Le grandezze che si muovono di piu':

{t_der_alta}

Le piu' ferme:

{t_der_bassa}

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

{t_tasso}

**Una riga e' una tripla `(stagione, squadra, giocatore)`, non un giocatore.**
Chi cambia squadra a gennaio compare due volte da entrambi i lati, ed e' giusto:
i suoi minuti appartengono a due squadre diverse. Nel 2025-26 sono
**609 righe per 586 giocatori distinti**, e il 609 e' lo stesso numero che il
report dell'aggancio riportava per la stagione singola.

**Il 609/609 della 2025-26 non era una previsione sulle altre**, e infatti il
tasso non e' identico — sta fra {tasso['tasso'].min():.4f} e 1,0000. Il residuo
si mostra, non si risolve d'ufficio, ed e' piccolo abbastanza da stare in una
tabella:

{t_irr}

Sono **{int(tasso['irrisolti'].sum())} righe su {_mila(int(tasso['righe'].sum()))}**, e ricadono nelle categorie gia' note:
omonimi veri che le iniziali non separano (`Andrea` contro `Filippo Ranocchia`),
giocatori con **una** presenza che il cognome non aggancia, e due casi in cui due
nomi dei voti puntano allo stesso WhoScored — dove si tolgono **entrambi**,
perche' tenere "il migliore" significherebbe scegliere.

### Il residuo sta sui giocatori rari? In parte, e la parte che manca conta

La domanda non e' oziosa: i giocatori con poche presenze sono **esattamente la
categoria che un modello dell'impiego deve prevedere**, quindi un aggancio che
fallisse li' fallirebbe dove serve.

La risposta e' **si', ma debolmente, e con due meccanismi diversi**. La mediana
degli irrisolti e' {irr['presenze_fc'].median():.1f} presenze contro
{pres_ok.median():.1f} degli agganciati, e 6 su 8 stanno sotto la mediana. Ma la
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
un titolare, non una comparsa. Con 8 casi su {_mila(int(tasso['righe'].sum()))}
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

{t_res_ws}

**Il massimo del 2023-24 vale {int(riep_res_ws['minuti_max'].max()):,} minuti**,
cioe' circa {int(riep_res_ws['minuti_max'].max() / 90)} partite intere — un
giocatore da rotazione piena, non una comparsa. Nel 2024-25 ce n'e' un altro da
oltre mille. La mediana dice il contrario del massimo, ed e' il motivo per cui
qui vanno riportati entrambi.

{t_res_ws_righe}

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

{t_corr_res}

**{n_corr_coperti} irrisolti su {n_irr_tot}** trovano cosi' un candidato, e il
numero di presenze coincide **esattamente**, non approssimativamente. Il caso
`Arthur Melo` (33) / `Lopez M.` (19) — quello che l'aggancio aveva buttato via
perche' due nomi dei voti puntavano allo stesso WhoScored — si separa da solo:
33 va su `Arthur`, 19 va su `Maxime Lopez`, ed erano due persone diverse.

**Non e' stato risolto qui, e la ragione e' misurata invece che addotta.** La
regola "stessa squadra, stesse presenze" **non e' una chiave**: `Akinsamiro`
(1 presenza) trova **due** candidati a 1 presenza nell'Inter 2023-24,
`Ebenezer Akinsanmiro` e `Lucien Agoume`. Su otto casi ne lascia ambiguo uno —
{n_corr_unici} accoppiamenti su {len(corr_res)} sono unici — quindi non e' una
chiave, e' un'euristica con un tasso d'errore. Applicarla d'ufficio sarebbe
**scegliere**, che e' esattamente cio' che questo blocco ha deciso di non fare.

**Cio' che la misura cambia e' la domanda aperta.** Non e' piu' «chi sono questi
otto»: e' «quale regola si adotta, e con quale tasso d'errore». La differenza e'
che ora si sa che l'informazione **c'e'**, ed e' una decisione, non un limite dei
dati. Le {len(residuo_ws) - n_corr_coperti} righe WhoScored che restano senza
controparte sono il terzo stato vero — chi ha giocato e che la fonte dei voti non
elenca affatto — e quelle non si chiudono con nessuna regola.

Il **Jaccard** resta la verifica, non la chiave: e' l'accordo fra i due insiemi
di presenze una volta che l'aggancio e' stato deciso dal cognome.

Il minimo scende a {tasso['jaccard_min'].min():.3f} nel 2022-23 contro
{tasso.set_index('stagione').loc['2025-2026', 'jaccard_min']:.3f} nel 2025-26, e
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
| giocatori distinti | {_mila(rc['giocatori_distinti'])} |
| presenti in piu' di una stagione | {_mila(rc['presenti_in_piu_stagioni'])} |
| **controlli incrociati indipendenti** | **{_mila(rc['controlli_incrociati'])}** |
| un `giocatore_id` su piu' `playerId` | {rc['discordi_fc']} |
| piu' `giocatore_id` sullo stesso `playerId` | {rc['discordi_ws']} |

Cambiare squadra **non** conta come discordanza: si guarda la coppia
`(giocatore_id, playerId)`, non la squadra.

## Cosa e' stato prodotto

| | |
|---|---|
| `data/processed/ITA-serie-a/<stagione>/{{shots,team_match,player_match}}.parquet` | 5 stagioni x 3 tabelle |
| `data/processed/ITA-serie-a/fase9_medie_campionato.parquet` | {len(medie)} righe |
| `data/processed/ITA-serie-a/fase9_xg_diagnostica.parquet` | 5 righe |
| `data/mapping/aggancio_giocatori.csv` | {_mila(len(agg['mappa']))} righe, 5 stagioni |
| `data/mapping/aggancio_ws_non_agganciati.csv` | {len(residuo_ws)} righe, il residuo nell'altro verso |
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
"""

    OUT_MD.write_text(testo, encoding="utf-8")
    print(f"\n-> {OUT_MD}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
