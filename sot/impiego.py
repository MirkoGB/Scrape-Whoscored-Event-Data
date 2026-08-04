# -*- coding: utf-8 -*-
"""Fase 9 / Blocco E2 — il modello d'impiego, e la sua valutazione.

Bersaglio: le **presenze fantacalcistiche** della stagione t+1. E' dove aspetta
il 91% dell'errore del modello d'asta (MAE 61,4 -> 5,6 con le presenze note), e la
metrica non e' il MAE ma la **quota dei 55,8 punti di divario oracolo** che si
chiude. Un guadagno del 3% e' un risultato piccolo e va detto piccolo.

LA MAGLIA DELLA STAGIONE BERSAGLIO NON SI PUO' USARE, E IL MOTIVO E' MISURATO
-----------------------------------------------------------------------------
E' il risultato metodologico del blocco, ed e' controintuitivo perche' colpisce
proprio l'argomento che rendeva il numero di maglia attraente.

Il numero e' assegnato in **agosto**, quindi in teoria e' noto al momento della
previsione anche per chi al nuovo club non ha storia. Ma la nostra **unica fonte
del numero e' la distinta di una partita**: un giocatore che non viene mai
convocato non ha nessuna distinta, quindi non ha nessun numero. Ne segue che la
sola *esistenza* della feature nella stagione bersaglio e' gia' la risposta.

Misurato sulle quattro transizioni: fra i quotati con una distinta in t+1 le
presenze medie sono **19,1-19,3**; fra quelli senza sono **0,0-0,3**. Un
predittore la cui disponibilita' separa cosi' non e' un predittore, e' il
bersaglio scritto in un'altra colonna.

**Quindi si usa il numero della stagione precedente**, come il capitano, e per la
stessa ragione. Il costo e' reale e va dichiarato: chi cambia club perde
esattamente cio' che rendeva la feature interessante, cioe' il caso del giocatore
appena arrivato. **Il numero d'agosto sarebbe acquisibile** — e' pubblicato dai
club e sta nei listoni — ma non e' nel repository, ed e' una domanda aperta con
una risposta nota, non un limite dei dati evento.

TUTTO CIO' CHE SI STIMA, SI STIMA SUL SOLO PASSATO
--------------------------------------------------
I coefficienti si adattano sulle stagioni **precedenti** a quella prevista, con la
stessa griglia di transizioni del modello d'asta. Un test guasta una stagione di
mezzo e pretende che le previsioni precedenti non cambino e le successive si'.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from . import config, distinta as D, multistagione as MS

#: **La fonte dei cartellini per questa feature e' quella dei VOTI**, non
#: WhoScored, e la scelta e' dichiarata perche' le due divergono (vincolo 7: le
#: ammonizioni concordano solo all'85-93%). Due ragioni, nessuna delle quali e' la
#: comodita': per i punti fantacalcio la fonte dei voti e' **definitoria** — e'
#: quella che ha prodotto il malus dentro `punti_osservati`, cioe' il bersaglio —
#: e sta gia' sulla chiave `giocatore_id`, senza aggancio di mezzo e senza
#: residuo. WhoScored resta il controllo indipendente di `squalifiche.py`.
FONTE_CARTELLINI = "voti"

#: Il pavimento di esposizione e' un **parametro di E2**, non un'eredita' di E1.
#: In E1 valeva 450 minuti perche' li' il pavimento proteggeva le medie; qui il
#: bersaglio sono le presenze, e i giocatori con pochi minuti non sono la coda del
#: campione — **sono la parte che il modello deve indovinare**. Un pavimento alto
#: rende E1 pulito ed E2 cieco dove serve.
PAVIMENTO = 0
PAVIMENTI_ACCANTO = (0, 450, 900, 1800)

#: Le fasce di minutaggio su cui l'errore si riporta separato. L'errore su un
#: titolare fisso e su una riserva sono problemi diversi e mediarli li nasconde
#: entrambi. Dichiarate, mai ricavate da quantili del campione.
FASCE_MINUTI = ((0, 1), (1, 450), (450, 1350), (1350, 2250), (2250, 10**9))
NOMI_FASCE_MINUTI = ("mai in campo", "sotto 5 partite", "5-15", "15-25", "oltre 25")


def fascia_minuti(m) -> str:
    if m is None or (isinstance(m, float) and np.isnan(m)):
        return "ignoto"
    for (lo, hi), nome in zip(FASCE_MINUTI, NOMI_FASCE_MINUTI):
        if lo <= m < hi:
            return nome
    return "ignoto"


def _ponte(stagioni=None) -> pd.DataFrame:
    """Da `(stagione, teamId, playerId)` di WhoScored a `giocatore_id` dei voti.

    E' l'aggancio di E0, usato e non rifatto. Il residuo dei due versi resta cio'
    che e': le righe che non agganciano **escono**, e quante sono si conta invece
    di lasciarle sparire — e' il difetto che la coda di E0 ha reso visibile.
    """
    m = MS.aggancio_giocatori(
        stagioni or config.SEASONS_STORICHE)["mappa"]
    return m[["stagione", "teamId_ws", "playerId_ws", "giocatore_id_fc"]].rename(
        columns={"teamId_ws": "teamId", "playerId_ws": "playerId",
                 "giocatore_id_fc": "giocatore_id"})


def feature_stagione(stagioni=None) -> pd.DataFrame:
    """Lo strato feature per `(stagione, giocatore_id)`, in unita' della stagione.

    Non standardizza: la standardizzazione e' di E1 e si applica a valle, dove le
    feature entrano in un modello multi-stagione. Qui si costruisce solo la
    tabella, e le colonne che E1 dichiara stabili in unita' grezze restano tali.
    """
    stagioni = list(config.SEASONS_STORICHE if stagioni is None else stagioni)
    nm = D.numero_maglia_multi(stagioni)
    ponte = _ponte(stagioni)

    pezzi = []
    for st in stagioni:
        pm = pd.read_parquet(config.player_match(season=st))
        n_squadra = pm.groupby("teamId")["team_match_idx"].max()
        g = (pm.groupby(["teamId", "playerId"])
             .agg(minuti=("minutes", "sum"),
                  convocazioni=("matchId", "nunique"),
                  da_titolare=("is_starter", "sum"),
                  tocchi=("touches", "sum") if "touches" in pm.columns
                  else ("minutes", "size"))
             .reset_index())
        g["stagione"] = st
        g["partite_squadra"] = g["teamId"].map(n_squadra)
        g["quota_minuti"] = g["minuti"] / (g["partite_squadra"] * 95.0)
        g["quota_titolare"] = g["da_titolare"] / g["partite_squadra"]
        g["quota_convocato"] = g["convocazioni"] / g["partite_squadra"]
        pezzi.append(g)

    base = pd.concat(pezzi, ignore_index=True)
    rs = pd.concat([D.ruolo_serie(st) for st in stagioni], ignore_index=True)

    n = len(base)
    out = base.merge(nm, on=["stagione", "teamId", "playerId"], how="left")
    out = out.merge(rs, on=["stagione", "teamId", "playerId"], how="left")
    assert len(out) == n, "un join dello strato feature ha moltiplicato le righe"

    n = len(out)
    out = out.merge(ponte, on=["stagione", "teamId", "playerId"], how="inner")
    out.attrs["righe_perse_nel_ponte"] = n - len(out)
    return out


def tabella_predittori(stagioni=None) -> pd.DataFrame:
    """Per ogni `(stagione bersaglio, giocatore_id)`, le feature di **t-1**.

    Lo sfasamento e' costruito qui, in un punto solo, cosi' che nessuna colonna
    possa entrare in contemporanea per distrazione. Un test verifica che tutte le
    colonne predittive portino il suffisso `_prec`.
    """
    f = feature_stagione(stagioni)
    stagioni = sorted(f["stagione"].unique())
    pos = {s: i for i, s in enumerate(stagioni)}

    colonne = ["quota_minuti", "quota_titolare", "quota_convocato", "minuti",
               "jersey", "e_capitano", "ruolo_instabile", "ruoli_distinti",
               "ruolo_modale"]
    prec = f[["stagione", "giocatore_id", "teamId"] + colonne].copy()
    prec["stagione_succ"] = [stagioni[pos[s] + 1] if pos[s] + 1 < len(stagioni)
                             else None for s in prec["stagione"]]
    prec = prec.dropna(subset=["stagione_succ"])
    prec = prec.rename(columns={c: f"{c}_prec" for c in colonne})
    prec = prec.drop(columns=["stagione"]).rename(
        columns={"stagione_succ": "stagione", "teamId": "teamId_prec"})

    # Un giocatore puo' avere due righe in t-1 (due club): si tiene quella con
    # piu' minuti, dichiarato. Aggregare alla media mescolerebbe due gerarchie.
    prec = (prec.sort_values("minuti_prec", ascending=False)
            .groupby(["stagione", "giocatore_id"], as_index=False).first())
    prec["fascia_maglia_prec"] = [D.fascia_maglia(v) for v in prec["jersey_prec"]]

    n = len(prec)
    prec = prec.merge(cartellini_precedenti(), on=["stagione", "giocatore_id"],
                      how="left")
    assert len(prec) == n, "il join dei cartellini ha moltiplicato le righe"
    return prec


# --------------------------------------------------------------------------
# Coda di E2 — il cartellino come PREDITTORE, non come sottrazione
#
# `squalifiche.perche_peggiora` ha misurato che sottrarre le giornate di
# squalifica peggiora il MAE, e ha consegnato un'inversione: **chi prende
# cartellini e' chi gioca**, quindi il cartellino ha valore col segno opposto.
# Quella forma NON era nel set di E2.4 — `FEATURE` sono cinque colonne e nessuna
# e' un cartellino — quindi l'inversione non era ne' confermata ne' confutata:
# era **non provata**, ed e' la ragione per cui questa coda esiste invece di
# aspettare due blocchi.
#
# DUE FORME, PERCHE' SONO DUE IPOTESI DIVERSE
# -------------------------------------------
# * **il conteggio** `amm + esp` di t-1 e' l'inversione detta alla lettera: il
#   cartellino come *marcatore di esposizione*, che cresce con le partite giocate;
# * **il tasso** `(amm + esp) / presenze` e' la propensione disciplinare **al
#   netto** del minutaggio.
#
# Sono l'una il contrario dell'altra rispetto a cio' che si vuole misurare, e
# provarne una sola avrebbe lasciato aperta l'altra. Il conteggio e' quello su cui
# l'inversione si gioca; il tasso e' il controllo.
#
# LA STANDARDIZZAZIONE SEGUE LA REGOLA DI E1, E NON E' UN RIFLESSO
# ----------------------------------------------------------------
# Ogni forma e' un rapporto `num/den` dichiarato, quindi il riferimento di
# campionato e' `somma(num)/somma(den)` — la stessa grandezza del valore
# individuale — e la trasformazione e' `x_rel = x / m_s - 1`. Ma E1 ha anche
# mostrato che standardizzare **peggiora** la deriva su 8 candidate su 19, quindi
# la deriva si **misura** (`deriva_cartellini`) e la colonna `_rel` si usa solo se
# la grezza non passa. Guardare il suffisso invece della misura e' esattamente
# l'errore che `verifica_standardizzazione` esiste per impedire.
# --------------------------------------------------------------------------

def cartellini_precedenti(stagioni=None, per_stagione: pd.DataFrame = None
                          ) -> pd.DataFrame:
    """I cartellini di **t-1** per `(stagione bersaglio, giocatore_id)`.

    Lo sfasamento e' costruito qui come per le altre feature: le colonne portano
    il suffisso `_prec` e un test lo pretende. Le presenze al denominatore sono
    anch'esse di t-1, quindi nessuna quantita' della stagione bersaglio entra.
    """
    from . import fantapunti as FP
    ps = FP.per_giocatore_stagione() if per_stagione is None else per_stagione
    stagioni = sorted(config.SEASONS_STORICHE if stagioni is None else stagioni)
    pos = {s: i for i, s in enumerate(stagioni)}

    c = ps[ps["stagione"].isin(stagioni)][
        ["stagione", "giocatore_id", "ammonizioni", "espulsioni", "presenze"]].copy()
    c["cartellini"] = c["ammonizioni"].astype(float) + c["espulsioni"].astype(float)
    # Chi non ha presenze non ha un tasso: NaN, non zero. Uno zero direbbe
    # "disciplinatissimo" di chi non e' mai sceso in campo.
    c["tasso_cartellini"] = c["cartellini"] / c["presenze"].replace(0, np.nan)

    # I riferimenti di campionato, uno per stagione, nella forma somma/somma.
    #
    # **Il conteggio non e' un rapporto**, e la conseguenza va detta invece che
    # nascosta: il suo unico denominatore possibile e' il numero di giocatori,
    # quindi il riferimento coincide con la media fra i giocatori e la sua `_rel`
    # ha media **esattamente zero in ogni stagione, per costruzione**. Su quella
    # colonna la deriva della media non e' una misura degenere per caso: e' zero
    # perche' la si e' resa tale, e `deriva_cartellini` lo dichiara invece di
    # spacciarlo per una candidata che passa il gate.
    rif = c.groupby("stagione").agg(
        m_cartellini=("cartellini", "mean"),
        n_cart=("cartellini", "sum"), n_pres=("presenze", "sum"))
    rif["m_tasso"] = rif["n_cart"] / rif["n_pres"]

    c["cartellini_rel"] = c["cartellini"] / c["stagione"].map(rif["m_cartellini"]) - 1
    c["tasso_cartellini_rel"] = c["tasso_cartellini"] / c["stagione"].map(rif["m_tasso"]) - 1

    colonne = ["cartellini", "tasso_cartellini", "cartellini_rel",
               "tasso_cartellini_rel"]
    out = c[["stagione", "giocatore_id"] + colonne].copy()
    out["stagione_succ"] = [stagioni[pos[s] + 1] if pos[s] + 1 < len(stagioni)
                            else None for s in out["stagione"]]
    out = out.dropna(subset=["stagione_succ"]).drop(columns=["stagione"])
    out = out.rename(columns={c_: f"{c_}_prec" for c_ in colonne})
    return out.rename(columns={"stagione_succ": "stagione"})


def deriva_cartellini(per_stagione: pd.DataFrame = None) -> pd.DataFrame:
    """La deriva fra stagioni delle due forme, grezza e standardizzata.

    E' il gate di E1 applicato a una candidata nuova: `SOGLIA_DERIVA` vale 5% e la
    colonna standardizzata si usa **solo se** la grezza non passa e la `_rel` si',
    che e' una misura e non il suffisso.
    """
    from . import fantapunti as FP, features_giocatore as FG
    ps = FP.per_giocatore_stagione() if per_stagione is None else per_stagione
    # Si legge sulle stagioni di ORIGINE, non su quelle bersaglio: lo sfasamento
    # di `cartellini_precedenti` butta via l'ultima, e una deriva misurata su
    # quattro stagioni su cinque non e' la deriva.
    c = cartellini_precedenti(per_stagione=ps).rename(
        columns={"stagione": "stagione_bersaglio"})
    stagioni = sorted(ps["stagione"].unique())
    pos = {s: i for i, s in enumerate(stagioni)}
    c["stagione"] = [stagioni[pos[s] - 1] for s in c["stagione_bersaglio"]]

    def _deriva(m: pd.Series) -> float:
        base = m.abs().max()
        return float((m.max() - m.min()) / base) if base else float("nan")

    righe = []
    for nome in ("cartellini", "tasso_cartellini"):
        grezza = c.groupby("stagione")[f"{nome}_prec"].mean().dropna()
        rel = c.groupby("stagione")[f"{nome}_rel_prec"].mean().dropna()
        # Il riferimento si ricostruisce dalla definizione: `x_rel = x/m_s - 1`,
        # quindi `m_s = media(x) / (media(x_rel) + 1)` dove il denominatore non
        # e' nullo. E' l'unico modo di leggerlo senza duplicare qui il calcolo
        # che `cartellini_precedenti` ha gia' fatto.
        rif = grezza / (rel + 1)
        # Degenere quando il riferimento **e'** la media fra i giocatori: la `_rel`
        # e' allora centrata a zero per costruzione e la sua deriva non e' una
        # misura di niente. E' il caso del conteggio, ed e' dichiarato, non nascosto.
        degenere = bool(np.allclose(rif.to_numpy(), grezza.to_numpy(), rtol=1e-9))

        righe.append({"candidata": nome, "forma": "grezza",
                      "min": float(grezza.min()), "max": float(grezza.max()),
                      "deriva_riferimento": _deriva(rif), "deriva": _deriva(grezza),
                      "passa": bool(_deriva(grezza) < FG.SOGLIA_DERIVA),
                      "degenere": False})
        # La deriva della `_rel` si legge su `rel + 1 = media(x) / m_s`, non su
        # `rel`. Non e' un trucco di scala: `(max-min)/|max|` su una serie
        # centrata vicino allo zero e' dominata dal denominatore e restituisce
        # numeri come 115% dove la deriva vera e' 7%. `rel + 1` e' esattamente
        # «quanto la popolazione si muove rispetto al proprio riferimento», che e'
        # la quantita' che il gate vuole.
        residua = _deriva(rel + 1)
        righe.append({"candidata": nome, "forma": "_rel",
                      "min": float(rel.min()), "max": float(rel.max()),
                      "deriva_riferimento": _deriva(rif),
                      "deriva": float("nan") if degenere else residua,
                      "passa": False if degenere
                               else bool(residua < FG.SOGLIA_DERIVA),
                      "degenere": degenere})
    return pd.DataFrame(righe)


# `FEATURE_CARTELLINI` e `contributo_cartellini` stanno in fondo al modulo,
# dopo la definizione di `FEATURE` da cui derivano.


# --------------------------------------------------------------------------
# Il modello d'impiego e la valutazione
#
# Specificazione deliberatamente povera: minimi quadrati regolarizzati sulle
# feature di t-1, stimati sulle sole stagioni precedenti a quella prevista. Non
# c'e' selezione di modello e non c'e' ricerca di iperparametri: `ALPHA` e'
# dichiarato, e un test vieta argmax/quantile in questo modulo.
#
# La ragione della poverta' e' la 6D: con quattro transizioni e ~600 righe per
# stagione, una ricerca sarebbe soprattutto adattamento, e il progetto ha gia'
# tre risultati negativi che dimostrano quanto costa non saperlo.
# --------------------------------------------------------------------------

#: Regolarizzazione della ridge sulle feature standardizzate. DICHIARATA.
ALPHA = 10.0

#: Le feature del modello completo. `_prec` ovunque: un test lo pretende.
FEATURE = ("quota_minuti_prec", "quota_titolare_prec", "quota_convocato_prec",
           "e_capitano_prec", "ruolo_instabile_prec")

#: Le stesse piu' la maglia, per isolare il contributo del predittore nuovo.
FEATURE_CON_MAGLIA = FEATURE + ("fascia_maglia_prec",)


def _disegno(d: pd.DataFrame, feature) -> tuple:
    """Matrice del disegno: le categoriche diventano indicatrici, mai ordinali.

    `fascia_maglia_prec` entra come **insieme di indicatrici**, non come numero:
    il 10 non e' "meglio" del 30 lungo un continuo, ed e' la disciplina 1 di
    `distinta.py` applicata al punto in cui conterebbe sbagliarla.
    """
    pezzi, nomi = [], []
    for f in feature:
        # Non `dtype == object`: pandas usa dtype `string` (Arrow) per le colonne
        # testuali di questo progetto, e il confronto con `object` le manca.
        if not pd.api.types.is_numeric_dtype(d[f]):
            ind = pd.get_dummies(d[f], prefix=f, drop_first=True).astype(float)
            pezzi.append(ind.to_numpy())
            nomi += list(ind.columns)
        else:
            pezzi.append(d[[f]].astype(float).fillna(0.0).to_numpy())
            nomi.append(f)
    return np.hstack(pezzi), nomi


def previsione_presenze(stagione: str, tab: pd.DataFrame, oss: pd.DataFrame,
                        feature=FEATURE, alpha: float = ALPHA,
                        pavimento: int = PAVIMENTO) -> pd.Series:
    """Presenze previste per `stagione`, stimando sul **solo passato**.

    Il pavimento filtra le righe di **addestramento**, non quelle di valutazione:
    escludere dalla valutazione i giocatori con pochi minuti sarebbe togliere dal
    campione proprio la parte che il modello deve indovinare.
    """
    storia = tab[tab["stagione"] < stagione]
    if pavimento:
        storia = storia[storia["minuti_prec"].fillna(0) >= pavimento]
    storia = storia.merge(oss, on=["stagione", "giocatore_id"], how="inner")
    if len(storia) < 50:
        return pd.Series(np.nan, index=tab.index[tab["stagione"] == stagione])

    ora = tab[tab["stagione"] == stagione]
    tutte = pd.concat([storia[list(feature)], ora[list(feature)]], ignore_index=True)
    X_all, _ = _disegno(tutte, feature)
    n_st = len(storia)
    X, Xn = X_all[:n_st], X_all[n_st:]
    y = storia["presenze"].to_numpy(dtype=float)

    mu, sd = X.mean(0), X.std(0)
    sd[sd == 0] = 1.0
    Xs, Xns = (X - mu) / sd, (Xn - mu) / sd
    A = Xs.T @ Xs + alpha * np.eye(Xs.shape[1])
    beta = np.linalg.solve(A, Xs.T @ (y - y.mean()))
    return pd.Series(np.clip(y.mean() + Xns @ beta, 0, 38), index=ora.index)


def valutazione(pavimento: int = PAVIMENTO, alpha: float = ALPHA) -> dict:
    """La quota del divario oracolo, sulle stesse quattro transizioni del modello d'asta.

    Riporta il MAE **sui punti**, non sulle presenze: e' il divario che il
    progetto ha gia' misurato (61,4 -> 5,6) e cambiarne l'unita' renderebbe la
    percentuale non confrontabile con niente.
    """
    from . import fantapunti as FP, modello_asta as MA

    ps = FP.per_giocatore_stagione()
    oss = ps[["stagione", "giocatore_id", "presenze"]]
    tab = tabella_predittori()
    wf = MA.walkforward(per_stagione=ps)

    prev = {}
    for nome, feat in (("impiego (senza maglia)", FEATURE),
                       ("impiego + maglia", FEATURE_CON_MAGLIA)):
        pezzi = []
        for st in MA.STAGIONI_VALUTABILI:
            p = previsione_presenze(st, tab, oss, feat, alpha, pavimento)
            pezzi.append(tab.loc[p.index, ["stagione", "giocatore_id"]].assign(pred=p))
        prev[nome] = pd.concat(pezzi, ignore_index=True)

    d = wf.copy()
    tasso = d["voto_atteso"] + d["bonus_per_presenza_atteso"]
    varianti = {"modello completo": d["punti_previsti"]}
    for nome, p in prev.items():
        k = p.set_index(["stagione", "giocatore_id"])["pred"]
        pres = pd.Series([k.get((s, g), np.nan) for s, g
                          in zip(d["stagione_prevista"], d["giocatore_id"])],
                         index=d.index)
        # Chi non ha riga di predittori non ha giocato in t-1: le sue presenze
        # attese restano quelle del modello d'asta, non diventano NaN. Sostituire
        # solo dove la feature esiste, e dichiararlo, e' l'unico modo di non
        # cambiare campione fra le varianti.
        d[f"pres_{nome}"] = pres.fillna(d["presenze_attese"])
        varianti[nome] = d[f"pres_{nome}"] * tasso
    varianti["presenze note (ORACOLO, il pavimento)"] = d["presenze_osservate"] * tasso

    righe = []
    for nome, x in varianti.items():
        ok = x.notna()
        righe.append({"variante": nome, "righe": int(ok.sum()),
                      "mae": float((x[ok] - d["punti_osservati"][ok]).abs().mean())})
    out = pd.DataFrame(righe)
    completo = float(out["mae"].iloc[0])
    pavim = float(out["mae"].iloc[-1])
    out["divario_chiuso_pct"] = 100 * (completo - out["mae"]) / (completo - pavim)
    return {"tabella": out, "dettaglio": d, "pavimento": pavimento}


def sensibilita_pavimento(pavimenti=PAVIMENTI_ACCANTO) -> pd.DataFrame:
    """Lo stesso risultato ai quattro pavimenti. Sei candidate su 19 cambiavano
    verdetto in E1: qui si mostra invece di ereditare."""
    righe = []
    for p in pavimenti:
        t = valutazione(pavimento=p)["tabella"]
        for _, r in t.iterrows():
            if r["variante"] == "modello completo":
                continue
            righe.append({"pavimento": p, "variante": r["variante"],
                          "mae": r["mae"], "divario_chiuso_pct": r["divario_chiuso_pct"]})
    return pd.DataFrame(righe)


# --------------------------------------------------------------------------
# Potenza e MDE — dichiarati PRIMA di leggere l'esito, come in 6D
#
# La lezione della Fase 6D e' che un risultato negativo senza potenza dichiarata
# non e' un risultato: «nessuno passa» puo' voler dire «gli effetti sono piccoli»
# oppure «il test non vede niente», e sono due conclusioni diverse.
# --------------------------------------------------------------------------

def potenza_mde(d: pd.DataFrame, colonna: str,
                riferimento: str = "presenze_attese") -> dict:
    """MDE sulla differenza appaiata di MAE dei punti, a potenza 80%.

    Appaiata perche' le due varianti girano sulle **stesse righe**: la varianza
    della differenza e' molto minore di quella dei due MAE separati, ed e' il
    confronto giusto.
    """
    tasso = d["voto_atteso"] + d["bonus_per_presenza_atteso"]
    a = (d[riferimento] * tasso - d["punti_osservati"]).abs()
    b = (d[colonna] * tasso - d["punti_osservati"]).abs()
    diff = (a - b).dropna()
    n = len(diff)
    se = float(diff.std(ddof=1) / np.sqrt(n)) if n > 1 else float("nan")
    # z a due code 0.975 piu' z a una coda 0.80.
    mde = (1.959964 + 0.841621) * se
    return {"righe": n, "delta_mae": float(diff.mean()), "se": se,
            "t": float(diff.mean() / se) if se else float("nan"),
            "mde_mae": mde, "mde_quota_divario_pct": 100 * mde / 55.86}


def per_segmento(d: pd.DataFrame, colonna: str) -> pd.DataFrame:
    """L'errore separato per ruolo e per fascia di minutaggio di t-1.

    Mediare un titolare fisso e una riserva nasconde entrambi: sono due problemi
    diversi, e il modello puo' benissimo migliorare uno e peggiorare l'altro.
    """
    tasso = d["voto_atteso"] + d["bonus_per_presenza_atteso"]
    x = d.copy()
    x["err_base"] = (x["presenze_attese"] * tasso - x["punti_osservati"]).abs()
    x["err_nuovo"] = (x[colonna] * tasso - x["punti_osservati"]).abs()

    righe = []
    for chiave, etichetta in (("ruolo", "ruolo"),):
        for v, sub in x.groupby(chiave):
            righe.append({"segmento": f"{etichetta}={v}", "righe": len(sub),
                          "mae_base": float(sub["err_base"].mean()),
                          "mae_nuovo": float(sub["err_nuovo"].mean()),
                          "delta": float((sub["err_base"] - sub["err_nuovo"]).mean())})
    return pd.DataFrame(righe)


def maglia_sul_primo_anno(pavimento: int = PAVIMENTO) -> pd.DataFrame:
    """La maglia dove dovrebbe servire: chi e' al **primo anno in un club**.

    E' la valutazione che la specifica chiede a parte, e la ragione e' che li'
    nessun altro predittore d'impiego esiste — non c'e' storia in quel club. Se
    la maglia serve, serve li'; se non serve nemmeno li', non serve.

    ATTENZIONE AL LIMITE, CHE QUI MORDE PIU' CHE ALTROVE
    ----------------------------------------------------
    Usando il numero della **stagione precedente** (obbligatorio, vedi il
    docstring del modulo), per chi cambia club quel numero e' quello del club
    vecchio. Il caso che si voleva coprire — il nuovo arrivato — e' proprio
    quello in cui la feature disponibile e' la meno pertinente. Il test si fa lo
    stesso, e il risultato va letto con questo davanti.
    """
    from . import fantapunti as FP, modello_asta as MA
    ps = FP.per_giocatore_stagione()
    oss = ps[["stagione", "giocatore_id", "presenze"]]
    tab = tabella_predittori()
    wf = MA.walkforward(per_stagione=ps)

    # Chi in t-1 stava in un club diverso da quello di t. Il club di t si prende
    # dai voti (`squadra_id`), che e' l'unica fonte che ce l'ha per la stagione
    # bersaglio senza passare dalle distinte.
    sq = ps[["stagione", "giocatore_id", "squadra_id"]]
    prec_sq = sq.copy()
    stagioni = sorted(ps["stagione"].unique())
    pos = {s: i for i, s in enumerate(stagioni)}
    prec_sq["stagione"] = [stagioni[pos[s] + 1] if pos[s] + 1 < len(stagioni) else None
                           for s in prec_sq["stagione"]]
    prec_sq = prec_sq.dropna(subset=["stagione"]).rename(
        columns={"squadra_id": "squadra_prec"})
    m = sq.merge(prec_sq, on=["stagione", "giocatore_id"], how="left")
    m["primo_anno"] = m["squadra_prec"].isna() | (m["squadra_prec"] != m["squadra_id"])

    righe = []
    for nome, feat in (("senza maglia", FEATURE), ("con maglia", FEATURE_CON_MAGLIA)):
        pezzi = []
        for st in MA.STAGIONI_VALUTABILI:
            p = previsione_presenze(st, tab, oss, feat, ALPHA, pavimento)
            pezzi.append(tab.loc[p.index, ["stagione", "giocatore_id"]].assign(pred=p))
        pr = pd.concat(pezzi, ignore_index=True).set_index(["stagione", "giocatore_id"])["pred"]

        d = wf.copy()
        tasso = d["voto_atteso"] + d["bonus_per_presenza_atteso"]
        pres = pd.Series([pr.get((s, g), np.nan) for s, g
                          in zip(d["stagione_prevista"], d["giocatore_id"])],
                         index=d.index).fillna(d["presenze_attese"])
        d["err"] = (pres * tasso - d["punti_osservati"]).abs()
        d = d.merge(m.rename(columns={"stagione": "stagione_prevista"}),
                    on=["stagione_prevista", "giocatore_id"], how="left")
        # `fillna(True)`: chi non ha riga in t-1 non era in quel club, quindi e'
        # al primo anno. Il cast a bool e' necessario perche' la colonna arriva
        # nullable e `~` su un nullable non e' la negazione logica.
        primo = d["primo_anno"].fillna(True).astype(bool)
        for lab, sub in (("primo anno nel club", d[primo]),
                         ("gia' nel club", d[~primo])):
            righe.append({"variante": nome, "gruppo": lab, "righe": len(sub),
                          "mae": float(sub["err"].mean())})
    return pd.DataFrame(righe)


#: Le varianti della coda. Il conteggio e' l'inversione alla lettera, il tasso e'
#: il controllo, la terza le mette insieme perche' non sono ridondanti fra loro.
#:
#: **Le ultime due esistono perche' il gate di E1 non si chiude** (vedi
#: `deriva_cartellini`: 17,0% e 12,4% grezze, 7,2% la `_rel` del tasso, contro una
#: soglia del 5%). Nessuna delle due forme e' quella «giusta», quindi si provano
#: entrambe: se l'esito coincide, la conclusione non dipende da una scelta di
#: standardizzazione che i dati non giustificano. Se divergesse, sarebbe la
#: standardizzazione il risultato e non il cartellino.
FEATURE_CARTELLINI = {
    "impiego + cartellini (conteggio)": FEATURE + ("cartellini_prec",),
    "impiego + cartellini (tasso)": FEATURE + ("tasso_cartellini_prec",),
    "impiego + cartellini (entrambi)": FEATURE + ("cartellini_prec",
                                                  "tasso_cartellini_prec"),
    "impiego + cartellini (conteggio, _rel)": FEATURE + ("cartellini_rel_prec",),
    "impiego + cartellini (tasso, _rel)": FEATURE + ("tasso_cartellini_rel_prec",),
}


def ridondanza_cartellini(tab: pd.DataFrame = None) -> pd.DataFrame:
    """Quanta parte di ogni forma e' gia' dentro il set di E2.4.

    E' cio' che distingue una confutazione da un'ambiguita'. Un predittore che non
    aggiunge niente puo' non aggiungere per due ragioni opposte — **e' gia' li'**
    oppure **non c'e' segnale** — e senza questa misura le due sono
    indistinguibili. Si regredisce ogni forma sulle tre quote di esposizione e si
    legge l'R2: alto = ridondante, basso = informazione nuova che comunque non
    serve, che e' il risultato piu' forte dei due.
    """
    tab = tabella_predittori() if tab is None else tab
    quote = ["quota_minuti_prec", "quota_titolare_prec", "quota_convocato_prec"]
    X = tab[quote].astype(float).fillna(0.0).to_numpy()
    X = np.hstack([np.ones((len(X), 1)), X])

    righe = []
    for col in ("cartellini_prec", "tasso_cartellini_prec"):
        y = tab[col].astype(float).fillna(0.0).to_numpy()
        b, *_ = np.linalg.lstsq(X, y, rcond=None)
        r2 = 1 - ((y - X @ b) ** 2).sum() / ((y - y.mean()) ** 2).sum()
        righe.append({
            "forma": col, "r2_sul_set_e2_4": float(r2),
            "corr_quota_minuti": float(tab[col].astype(float).corr(
                tab["quota_minuti_prec"].astype(float))),
            "corr_quota_titolare": float(tab[col].astype(float).corr(
                tab["quota_titolare_prec"].astype(float))),
            "lettura": "gia' nel set" if r2 > 0.25 else "informazione nuova",
        })
    return pd.DataFrame(righe)


def contributo_cartellini(pavimento: int = PAVIMENTO, alpha: float = ALPHA,
                          varianti=None) -> dict:
    """Il contributo **individuale** del cartellino come predittore d'impiego.

    Stesse quattro transizioni, stesse righe e stesso divario oracolo di E2.4. Il
    confronto e' contro `impiego (senza maglia)` e non contro il modello d'asta,
    perche' la domanda non e' «il cartellino predice le presenze» — lo fa di
    sicuro, chi gioca di piu' ne prende di piu' — ma **«aggiunge qualcosa al set
    gia' provato»**, che e' l'unica versione falsificabile dell'inversione.

    Riporta il MAE sui punti *e* quello sulle presenze. Sono due domande diverse:
    un predittore d'impiego puo' migliorare le presenze e perdersi nella
    moltiplicazione per il tasso, e leggerne una sola nasconderebbe quale dei due
    passaggi non funziona.
    """
    from . import fantapunti as FP, modello_asta as MA

    ps = FP.per_giocatore_stagione()
    oss = ps[["stagione", "giocatore_id", "presenze"]]
    tab = tabella_predittori()
    wf = MA.walkforward(per_stagione=ps)

    d = wf.copy()
    tasso = d["voto_atteso"] + d["bonus_per_presenza_atteso"]
    varianti = {"impiego (senza maglia)": FEATURE,
                **(FEATURE_CARTELLINI if varianti is None else varianti)}

    righe = []
    for nome, feat in varianti.items():
        pezzi = []
        for st in MA.STAGIONI_VALUTABILI:
            p = previsione_presenze(st, tab, oss, feat, alpha, pavimento)
            pezzi.append(tab.loc[p.index, ["stagione", "giocatore_id"]].assign(pred=p))
        k = (pd.concat(pezzi, ignore_index=True)
             .set_index(["stagione", "giocatore_id"])["pred"])
        pres = pd.Series([k.get((s, g), np.nan) for s, g
                          in zip(d["stagione_prevista"], d["giocatore_id"])],
                         index=d.index).fillna(d["presenze_attese"])
        d[f"pres_{nome}"] = pres
        punti = pres * tasso
        ok = punti.notna()
        righe.append({
            "variante": nome, "righe": int(ok.sum()),
            "mae_punti": float((punti[ok] - d["punti_osservati"][ok]).abs().mean()),
            "mae_presenze": float((pres - d["presenze_osservate"]).abs().mean()),
            "corr_presenze": float(pres.corr(d["presenze_osservate"])),
        })

    out = pd.DataFrame(righe)
    # Il divario e' quello gia' pubblicato: 61,42 del modello d'asta completo
    # contro 5,56 dell'oracolo. Ricalcolarlo su un altro campione renderebbe le
    # percentuali non confrontabili con la tabella di E2.4.
    completo = float((d["punti_previsti"] - d["punti_osservati"]).abs().mean())
    pavim = float((d["presenze_osservate"] * tasso - d["punti_osservati"]).abs().mean())
    out["divario_chiuso_pct"] = 100 * (completo - out["mae_punti"]) / (completo - pavim)

    base = "pres_impiego (senza maglia)"
    mde = pd.DataFrame([{"variante": nome,
                         **potenza_mde(d, f"pres_{nome}", riferimento=base)}
                        for nome in varianti if nome != "impiego (senza maglia)"])
    return {"tabella": out, "mde": mde, "dettaglio": d}
