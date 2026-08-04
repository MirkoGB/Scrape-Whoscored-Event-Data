"""Fase 9 / Blocco E0 — le tabelle di Fase 1 su tutte e cinque le stagioni.

Nessuna richiesta di rete: e' calcolo sui 1.889 CSV gia' acquisiti. Nessun
modello di previsione — con **una** eccezione dichiarata, che e' il motivo per
cui questo modulo ha una tabella di diagnostica:

    I CINQUE FIT DI xG SONO STIME
    -----------------------------
    `aggregate.build_shots` chiama `xg.fit_predict_xg`, che stima una logistica
    cross-fitted a 5 fold raggruppati per partita. Girando la Fase 1 una volta
    per stagione si ottengono **cinque fit indipendenti**, ed e' il
    comportamento voluto: CLAUDE.md vieta di stimare l'xG interno su piu'
    stagioni insieme perche' i suoi ingressi derivano (`shotCounter` 3.4% ->
    7.7% dei tentativi, `shotOpenPlay` -7.5 punti fra 2021-22 e 2025-26).

    Ma cinque fit indipendenti vogliono dire **cinque scale**, e "E0 non produce
    stime" sarebbe falso. Quindi ognuno riporta log-loss, AUC e calibrazione
    aggregata, affiancati (`diagnostica_xg`). Cinque righe accostate sono di per
    se' una misura di quanto la scala si muove, ed e' la cosa che l'etichetta
    `xg_fit` serve a proteggere.

LA DERIVA RESTA NEL DERIVATO
----------------------------
`team_match` e `player_match` conservano le **unita' grezze**. La comparabilita'
fra stagioni e' un fatto dello strato feature (blocco E1), non del derivato:
normalizzare qui cancellerebbe un fatto misurato, ed e' il vincolo 4.

Cio' che questo modulo aggiunge e' il **riferimento** con cui lo strato feature
potra' standardizzare: `medie_campionato()`, una tabella `stagione x grandezza`.
Non e' una colonna ripetuta su ogni riga perche' una media di campionato e' un
fatto **di stagione**, non di riga.

I DENOMINATORI SI PRENDONO DAI DATI
-----------------------------------
Mai assunti a 38, e **nemmeno presi dal calendario**. `partite_per_squadra()` li
conta, e non sono uniformi: 35 per l'Atalanta nel 2021-22 e nel 2022-23, perche'
WhoScored non ha quelle partite.

La seconda meta' della regola e' quella che si sbaglia piu' facilmente. Spezia e
Verona hanno **giocato** 39 partite nel 2022-23 (38 piu' il playout, che e' una
partita vera e non va scartata), ma i CSV acquisiti sono **37 e 38**: di quelle
39, WhoScored non ha rispettivamente 2 e 1. Nessuna squadra arriva a 39 nei dati.
Correggere 38 in 39 a mano per le due squadre del playout — la correzione ovvia —
sostituirebbe un errore con un altro.

Le 12 partite assenti alla fonte **non sono casuali rispetto alla squadra**
(l'Atalanta ne perde 6 contro un'attesa di 1,2), quindi entrano in ogni tasso per
90 e in ogni conteggio di presenze.
"""

from __future__ import annotations

import pandas as pd

from . import aggancio as AG, aggregate, config, xg as xg_mod

STAGIONI = config.SEASONS_STORICHE

# Grandezze di cui si pubblica la media di campionato, per unita' di misura.
# L'elenco e' **esplicito** e non "tutte le colonne numeriche": la media di
# `matchId` o di `is_home` non significa niente, e una tabella di riferimento
# che contiene voci prive di senso invita a usarle.
GRANDEZZE_SQUADRA_PARTITA = (
    "shots", "sot", "goals", "xg", "xg_per_shot", "big_chances",
    "mean_shot_distance", "possession", "field_tilt", "box_touches",
    "ppda", "def_actions",
    "shots_conceded", "sot_conceded", "xg_conceded",
)

# Grandezze di giocatore, come tasso di campionato per 90 minuti: il totale di
# campionato diviso i minuti di campionato. E' il riferimento giusto per una
# feature per-90 di giocatore — la media delle medie individuali non lo e',
# perche' pesa uguale chi ha giocato 90 minuti e chi ne ha giocati 3.000.
GRANDEZZE_PER_90 = ("shots", "sot", "goals", "xg")


# --------------------------------------------------------------------------
# Costruzione
# --------------------------------------------------------------------------

def costruisci(stagioni=STAGIONI, force: bool = False) -> pd.DataFrame:
    """Fa girare la Fase 1 su ogni stagione. Ritorna il riepilogo per stagione.

    Idempotente nel senso che conta: non tocca `data/raw/` e riscrive solo
    Parquet rigenerabili. `force` rilegge i CSV invece della cache degli eventi.
    """
    righe = []
    for st in stagioni:
        out = aggregate.run(force=force, season=st)
        team, player, shots = out["team_match"], out["player_match"], out["shots"]
        righe.append({
            "stagione": st,
            "partite": int(team["matchId"].nunique()),
            "squadra_partita": int(len(team)),
            "giocatore_partita": int(len(player)),
            "tiri": int(len(shots)),
            "tiri_in_porta": int(team["sot"].sum()),
            "giocatori": int(player.loc[player["minutes"] > 0, "playerId"].nunique()),
            "sot_per_squadra_partita": float(team["sot"].mean()),
        })
    return pd.DataFrame(righe)


def carica(tabella: str, stagioni=STAGIONI) -> pd.DataFrame:
    """Concatena una delle tabelle di Fase 1 sulle stagioni richieste.

    `tabella` e' "team_match", "player_match" o "shots". Il risultato porta
    sempre `stagione`: e' la colonna senza la quale un `groupby` mescola cinque
    regimi di annotazione diversi.
    """
    percorso = {"team_match": config.team_match,
                "player_match": config.player_match,
                "shots": config.shots_parquet}[tabella]
    parti = []
    for st in stagioni:
        df = pd.read_parquet(percorso(season=st))
        if "stagione" not in df.columns:
            df = df.assign(stagione=st)
        parti.append(df)
    return pd.concat(parti, ignore_index=True)


# --------------------------------------------------------------------------
# Il riferimento per lo strato feature
# --------------------------------------------------------------------------

def medie_campionato(stagioni=STAGIONI) -> pd.DataFrame:
    """Media di campionato per stagione e grandezza. Forma lunga.

    Colonne: `stagione`, `grandezza`, `unita`, `media`, `n`.

    Forma lunga e non larga perche' le grandezze cambiano fra blocchi: E1 ne
    aggiungera' di sue, e una tabella larga andrebbe migrata a ogni giro. In
    forma lunga si aggiungono righe.
    """
    righe = []

    team = carica("team_match", stagioni)
    for st, blocco in team.groupby("stagione", sort=True):
        for g in GRANDEZZE_SQUADRA_PARTITA:
            v = blocco[g].dropna()
            righe.append({"stagione": st, "grandezza": g,
                          "unita": "squadra_partita",
                          "media": float(v.mean()), "n": int(len(v))})

    player = carica("player_match", stagioni)
    for st, blocco in player.groupby("stagione", sort=True):
        minuti = float(blocco["minutes"].sum())
        for g in GRANDEZZE_PER_90:
            righe.append({"stagione": st, "grandezza": g, "unita": "per_90",
                          "media": float(blocco[g].sum()) / minuti * 90.0,
                          "n": int((blocco["minutes"] > 0).sum())})
        righe.append({"stagione": st, "grandezza": "minutes",
                      "unita": "giocatore_partita",
                      "media": float(blocco["minutes"].mean()),
                      "n": int(len(blocco))})

    tiri = carica("shots", stagioni)
    for st, blocco in tiri.groupby("stagione", sort=True):
        righe.append({"stagione": st, "grandezza": "xg", "unita": "tiro",
                      "media": float(blocco["xg"].mean()), "n": int(len(blocco))})
        righe.append({"stagione": st, "grandezza": "quota_in_porta",
                      "unita": "tiro",
                      "media": float(blocco["is_sot"].mean()), "n": int(len(blocco))})

    return pd.DataFrame(righe).sort_values(
        ["grandezza", "unita", "stagione"]).reset_index(drop=True)


def deriva(medie: pd.DataFrame) -> pd.DataFrame:
    """Di quanto si muove ogni grandezza fra la prima e l'ultima stagione.

    E' la lettura che rende la tabella precedente un risultato invece di un
    elenco: dice quali grandezze **non** si possono usare in unita' grezze in un
    modello multi-stagione. Non decide niente — la regola e' del blocco E1.
    """
    p = medie.pivot_table(index=["grandezza", "unita"], columns="stagione",
                          values="media")
    prima, ultima = p.columns[0], p.columns[-1]
    out = pd.DataFrame({
        "grandezza": [i[0] for i in p.index],
        "unita": [i[1] for i in p.index],
        "prima": p[prima].to_numpy(),
        "ultima": p[ultima].to_numpy(),
        "min": p.min(axis=1).to_numpy(),
        "max": p.max(axis=1).to_numpy(),
    })
    out["deriva_pct"] = (out["ultima"] - out["prima"]) / out["prima"] * 100.0
    out["ampiezza_pct"] = (out["max"] - out["min"]) / out["min"] * 100.0
    return out.sort_values("ampiezza_pct", ascending=False).reset_index(drop=True)


# --------------------------------------------------------------------------
# L'unica stima del blocco, dichiarata
# --------------------------------------------------------------------------

def diagnostica_xg(stagioni=STAGIONI) -> pd.DataFrame:
    """Log-loss, AUC e calibrazione aggregata di ciascuno dei cinque fit.

    Il baseline e' il tasso base della **stessa** stagione (vincolo 6): un
    log-loss di 0,24 non significa niente finche' non si sa che il tasso base ne
    fa 0,32.

    La calibrazione aggregata e' `somma(xG) / gol - 1`. Essendo cross-fitted,
    non e' garantita a zero: e' una verifica, non un'identita'.
    """
    righe = []
    for st in stagioni:
        sh = pd.read_parquet(config.shots_parquet(season=st))
        d = xg_mod.evaluate(sh, sh["xg"])
        righe.append({
            "stagione": st,
            "tiri": d["n_shots"],
            "gol": d["n_goals"],
            "tasso_base": d["base_rate"],
            "logloss": d["logloss_model"],
            "logloss_base": d["logloss_base"],
            "auc": d["auc"],
            "somma_xg": d["xg_sum"],
            "calibrazione_pct": (d["xg_sum"] - d["goals"]) / d["goals"] * 100.0,
            "rigori": int((sh["xg_source"] == "penalty_rate").sum()),
        })
    return pd.DataFrame(righe)


# --------------------------------------------------------------------------
# Denominatori
# --------------------------------------------------------------------------

def partite_per_squadra(stagioni=STAGIONI) -> pd.DataFrame:
    """Quante partite di ogni squadra **ci sono nei dati**, per stagione.

    Si contano, non si assumono: chi divide per 38 sbaglia per l'Atalanta, che
    ne ha 35 nel 2021-22 e nel 2022-23. E non e' il numero di *calendario* —
    Spezia e Verona hanno giocato 39 partite nel 2022-23 ma qui ne risultano 37 e
    38, perche' la perdita alla fonte colpisce anche loro. Il nome della colonna
    e' `partite` e significa "acquisite", che e' l'unica cosa su cui si possa
    dividere.
    """
    team = carica("team_match", stagioni)
    out = (team.groupby(["stagione", "team"])
           .agg(partite=("matchId", "nunique"),
                sot=("sot", "sum"), gol=("goals", "sum"))
           .reset_index())
    out["sot_per_partita"] = out["sot"] / out["partite"]
    return out


def denominatori_anomali(stagioni=STAGIONI) -> pd.DataFrame:
    """Le sole righe in cui il denominatore non e' 38."""
    p = partite_per_squadra(stagioni)
    return p[p["partite"] != 38].sort_values(
        ["stagione", "team"]).reset_index(drop=True)


# --------------------------------------------------------------------------
# Aggancio dei giocatori sulle cinque stagioni
# --------------------------------------------------------------------------

def aggancio_giocatori(stagioni=STAGIONI) -> dict:
    """L'aggancio, stagione per stagione, con il tasso riportato per stagione.

    Il 609/609 della 2025-26 **non e' una previsione sulle altre**: piu'
    stagioni significano piu' omonimi, piu' prestiti e piu' giocatori con poche
    presenze. Il residuo si mostra, non si risolve d'ufficio.

    **Una riga e' una tripla `(stagione, squadra, giocatore)`, non un
    giocatore.** Chi cambia squadra a gennaio compare due volte, da entrambi i
    lati, ed e' giusto cosi': i suoi minuti sono di due squadre diverse. Nel
    2025-26 sono 609 righe per 586 giocatori distinti.

    Il residuo si conta **nei due versi**, perche' non sono lo stesso numero:
    `irrisolti` sono giocatori dei voti a cui non si e' trovato un WhoScored;
    `ws_non_agganciati` sono giocatori WhoScored con almeno un minuto che
    nessuna riga dei voti ha reclamato — cioe' il "terzo stato" gia' visto nella
    2025-26, chi gioca e che la fonte dei voti non elenca affatto.
    """
    mappe, irrisolti, tassi = [], [], []
    for st in stagioni:
        g = AG.mappa_giocatori(st)
        m, irr = g["mappa"], g["irrisolti"]
        mappe.append(m)
        if len(irr):
            irrisolti.append(irr)
        tot = len(m) + len(irr)

        pm = pd.read_parquet(config.player_match(season=st))
        ws_ids = set(pm.loc[pm["minutes"] > 0, "playerId"].dropna().astype(int))
        agganciati_ws = set(m["playerId_ws"].astype(int)) if len(m) else set()

        tassi.append({
            "stagione": st,
            "righe": len(m),
            "irrisolti": len(irr),
            "totale_fc": tot,
            "tasso": len(m) / tot if tot else float("nan"),
            "giocatori_fc": int(m["giocatore_id_fc"].nunique()) if len(m) else 0,
            "giocatori_ws": len(ws_ids),
            "ws_non_agganciati": len(ws_ids - agganciati_ws),
            "jaccard_medio": float(m["jaccard"].mean()) if len(m) else float("nan"),
            "jaccard_min": float(m["jaccard"].min()) if len(m) else float("nan"),
        })

    mappa = pd.concat(mappe, ignore_index=True) if mappe else pd.DataFrame()
    irr = pd.concat(irrisolti, ignore_index=True) if irrisolti else pd.DataFrame()
    return {"mappa": mappa, "irrisolti": irr, "tasso": pd.DataFrame(tassi)}


def residuo_whoscored(stagioni=STAGIONI, mappa: pd.DataFrame = None) -> pd.DataFrame:
    """Il residuo dal lato WhoScored, con **identita' e minuti**.

    `aggancio_giocatori()` conta i `ws_non_agganciati` ma non dice **chi** sono.
    Finche' il residuo e' un numero lo si legge come "quattro comparse" e si va
    avanti; e' esattamente cio' che era successo. Guardando i minuti si vede che
    non e' vero: nel 2023-24 il piu' grosso ne ha **2.145**, cioe' circa 24
    partite intere, e nel 2024-25 ce n'e' uno da 1.178.

    Perche' conta, e perche' e' coda di E0 e non parte di E2: queste sono righe
    di `player_match` **senza bersaglio**. Un modello dell'impiego che si
    costruisse il campione unendo le due fonti se le perderebbe in silenzio, e le
    perderebbe nella classe che deve indovinare. E' un difetto del derivato, che
    si mostra prima di modellare — lo stesso principio con cui E0 ha messo gli 8
    irrisolti in tabella invece di risolverli d'ufficio.

    LA GRANULARITA' E' LA COPPIA, E IL CONTEGGIO PUBBLICATO SOTTOSTIMA
    ------------------------------------------------------------------
    La colonna `ws_non_agganciati` di `aggancio_giocatori()` sottrae insiemi di
    `playerId` **ignorando la squadra**; qui il residuo si calcola sulla coppia
    `(squadra, giocatore)`, che e' la riga di `player_match`. Non e' una
    sfumatura di conteggio: chi cambia squadra a gennaio ha **due** righe, e
    basta che una delle due sia agganciata perche' il conteggio pubblicato lo
    dichiari agganciato **anche dove non lo e'**.

    Succede, e nel caso peggiore possibile. `Maxime Lopez` nel 2023-24 gioca 2
    partite al Sassuolo e 19 alla Fiorentina. Al Sassuolo l'aggancio riesce; alla
    Fiorentina no, perche' e' li' che avviene la collisione con `Arthur Melo`.
    Il conteggio pubblicato lo assorbe via il Sassuolo e **nasconde 884 minuti e
    19 presenze** dietro un aggancio fatto su 2. Da qui `ws_non_agganciati` = 5
    contro le 6 coppie vere del 2023-24.

    Le due letture rispondono a due domande — "quante persone non sono mai state
    reclamate da nessuna parte" contro "quante righe restano senza bersaglio" — e
    per E2 serve la seconda. La colonna pubblicata **non si tocca**: si dichiara
    che sottostima, e un test blocca la relazione nel verso giusto (le coppie non
    possono mai essere meno delle persone) invece di pretendere un'uguaglianza
    che e' falsa.

    Il residuo si **mostra**, non si risolve: non c'e' nessun tentativo di
    riagganciarlo con una regola piu' larga, che sarebbe scegliere.
    """
    if mappa is None:
        mappa = aggancio_giocatori(stagioni)["mappa"]

    righe = []
    for st in stagioni:
        pm = pd.read_parquet(config.player_match(season=st))
        pm = pm[pm["minutes"] > 0]
        m = mappa[mappa["stagione"] == st]
        agganciate = set(zip(m["teamId_ws"].astype(int),
                             m["playerId_ws"].astype(int)))

        tot_min_stagione = float(pm["minutes"].sum())
        g = (pm.groupby(["teamId", "team", "playerId", "playerName"])
             .agg(minuti=("minutes", "sum"),
                  presenze=("matchId", "nunique"),
                  da_titolare=("is_starter", "sum"))
             .reset_index())
        g["stagione"] = st
        g["agganciato"] = [(int(t), int(p)) in agganciate
                           for t, p in zip(g["teamId"], g["playerId"])]
        res = g[~g["agganciato"]].drop(columns=["agganciato"]).copy()
        res["quota_minuti_stagione"] = res["minuti"] / tot_min_stagione
        righe.append(res)

    out = pd.concat(righe, ignore_index=True) if righe else pd.DataFrame()
    if not len(out):
        return out
    cols = ["stagione", "teamId", "team", "playerId", "playerName",
            "minuti", "presenze", "da_titolare", "quota_minuti_stagione"]
    return out[cols].sort_values(["stagione", "minuti"],
                                 ascending=[True, False]).reset_index(drop=True)


def riepilogo_residuo_whoscored(res: pd.DataFrame,
                                stagioni=STAGIONI) -> pd.DataFrame:
    """Una riga per stagione: quante coppie, quanti minuti, il massimo.

    Il **massimo** e' la colonna che conta, non la mediana: dice se il residuo e'
    fatto di comparse o contiene un giocatore da rotazione piena.
    """
    righe = []
    for st in stagioni:
        r = res[res["stagione"] == st] if len(res) else res
        righe.append({
            "stagione": st,
            "coppie": len(r),
            "giocatori": int(r["playerId"].nunique()) if len(r) else 0,
            "minuti_totali": int(r["minuti"].sum()) if len(r) else 0,
            "minuti_mediana": float(r["minuti"].median()) if len(r) else float("nan"),
            "minuti_max": int(r["minuti"].max()) if len(r) else 0,
            "quota_minuti_pct": (100 * float(r["quota_minuti_stagione"].sum())
                                 if len(r) else 0.0),
        })
    return pd.DataFrame(righe)


def corrispondenza_residui(irrisolti: pd.DataFrame,
                           residuo_ws: pd.DataFrame) -> pd.DataFrame:
    """I due residui sono **la stessa gente vista da due lati**? MISURA, non risolve.

    Emergenza della coda di E0, e non era prevista. Messi i due residui uno
    accanto all'altro si vede che non sono indipendenti: ogni irrisolto dei voti
    ha, **nella stessa squadra e nella stessa stagione**, una riga WhoScored non
    agganciata con **lo stesso identico numero di presenze**. `Stryger Larsen`
    (11) sta di fronte a `Jens Stryger` (11), `Arthur Melo` (33) di fronte ad
    `Arthur` (33), `Kasa` (8) di fronte a `Lior Kassa` (8).

    NON SI RISOLVE QUI, E LA RAGIONE E' MISURATA
    --------------------------------------------
    La tentazione e' chiudere l'aggancio con la regola "stessa squadra, stesse
    presenze". **Non e' unica**: `Akinsamiro` (1 presenza) trova DUE candidati a
    1 presenza nell'Inter 2023-24 — `Ebenezer Akinsanmiro` e `Lucien Agoume`. Su
    otto casi la regola ne lascia ambiguo uno, quindi non e' una chiave: e'
    un'euristica con un tasso d'errore da dichiarare. Chiuderla d'ufficio qui
    sarebbe **scegliere**, ed e' cio' che E0 ha deciso di non fare con gli
    irrisolti.

    Quello che la misura fa e' cambiare la natura della domanda aperta: non e'
    piu' "chi sono questi otto", e' "quale regola si adotta, e con quale tasso
    d'errore". Il conto sta nel report; la decisione e' dell'utente.

    Ritorna una riga per **ogni** accoppiamento candidato, non per irrisolto:
    dove i candidati sono due, le righe sono due, e la colonna `unico` lo dice.
    """
    if not len(irrisolti) or not len(residuo_ws):
        return pd.DataFrame()

    j = irrisolti.merge(
        residuo_ws, left_on=["stagione", "teamId_ws"],
        right_on=["stagione", "teamId"], how="left", suffixes=("", "_ws"))
    j = j[j["presenze_fc"] == j["presenze"]].copy()
    n_cand = j.groupby(["stagione", "giocatore_id_fc"])["playerId"].transform("size")
    j["unico"] = n_cand == 1
    cols = ["stagione", "team", "nome_fc", "presenze_fc", "playerName",
            "presenze", "minuti", "unico", "motivo"]
    return j[cols].sort_values(["stagione", "minuti"],
                               ascending=[True, False]).reset_index(drop=True)


def coerenza_fra_stagioni(mappa: pd.DataFrame) -> dict:
    """Lo stesso giocatore deve prendere lo stesso `playerId` in ogni stagione.

    E' la verifica che una stagione sola non poteva fare, e non costa niente:
    `giocatore_id` di fantacalcio viene dall'URL del profilo ed e' **stabile fra
    stagioni**; `playerId` di WhoScored e' anch'esso un identificatore di
    persona. Quindi cinque agganci indipendenti devono concordare, e dove non
    concordano **almeno uno dei due e' sbagliato**.

    Il pregio del controllo e' che non passa dal nome, cioe' non e' circolare
    rispetto alla regola che l'aggancio usa per decidere.

    Cambiare squadra e' legittimo e non conta come discordanza: si guarda la
    coppia `(giocatore_id_fc, playerId_ws)`, non la squadra. Ritorna tabelle da
    **leggere**, non un'asserzione: e' il committente a decidere cosa farne.
    """
    if mappa.empty:
        vuoto = pd.DataFrame()
        return {"per_giocatore": vuoto, "discordi_fc": vuoto, "discordi_ws": vuoto}

    per_g = (mappa.groupby("giocatore_id_fc")
             .agg(stagioni=("stagione", "nunique"),
                  playerId_distinti=("playerId_ws", "nunique"),
                  nomi_fc=("nome_fc", lambda s: "; ".join(sorted(set(s)))),
                  nomi_ws=("nome_ws", lambda s: "; ".join(sorted(set(s)))))
             .reset_index())

    per_w = (mappa.groupby("playerId_ws")
             .agg(stagioni=("stagione", "nunique"),
                  giocatori_fc_distinti=("giocatore_id_fc", "nunique"),
                  nomi_fc=("nome_fc", lambda s: "; ".join(sorted(set(s)))),
                  nomi_ws=("nome_ws", lambda s: "; ".join(sorted(set(s)))))
             .reset_index())

    return {
        "per_giocatore": per_g,
        # Un `giocatore_id` dei voti su due `playerId` diversi.
        "discordi_fc": per_g[per_g["playerId_distinti"] > 1].reset_index(drop=True),
        # Due `giocatore_id` dei voti sullo stesso `playerId`.
        "discordi_ws": per_w[per_w["giocatori_fc_distinti"] > 1].reset_index(drop=True),
    }


def riepilogo_coerenza(mappa: pd.DataFrame, coerenza: dict) -> pd.DataFrame:
    """Una riga: quanti controlli incrociati esistono e quanti ne falliscono."""
    per_g = coerenza["per_giocatore"]
    multi = per_g[per_g["stagioni"] > 1]
    return pd.DataFrame([{
        "giocatori_distinti": int(len(per_g)),
        "presenti_in_piu_stagioni": int(len(multi)),
        # Ogni stagione oltre la prima e' un controllo indipendente.
        "controlli_incrociati": int((multi["stagioni"] - 1).sum()),
        "discordi_fc": int(len(coerenza["discordi_fc"])),
        "discordi_ws": int(len(coerenza["discordi_ws"])),
        "righe_mappa": int(len(mappa)),
    }])
