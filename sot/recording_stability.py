# -*- coding: utf-8 -*-
"""Stabilita' del criterio di rilevazione fra le cinque stagioni acquisite.

LA DOMANDA
----------
L'acquisizione WhoScored 2021-2026 ha portato in casa 1.889 partite su cinque
stagioni e ha dichiarato un limite: *"nessuna verifica di stabilita' del
criterio di rilevazione fra stagioni. Schema identico non implica annotazione
identica."* Questo modulo e' quella verifica, e gira interamente su dati gia'
sul disco: **non scarica niente**.

Perche' prima di stimare `rho` su cinque stagioni: se il criterio Opta si e'
spostato fra il 2021-22 e il 2025-26, l'eccesso di una squadra sulla media di
campionato contiene anche lo spostamento, e la persistenza stimata misura in
parte la fonte invece della squadra.

CALCIO O ANNOTAZIONE: COME SI DISTINGUONO
-----------------------------------------
Una discontinuita' nella media di tiri in porta puo' essere calcio vero
(mercato, regolamenti, stili) oppure un cambio di criterio di rilevazione. Le
due cose lasciano firme diverse, e il modulo le cerca tutte e tre:

1. **I rapporti sono piu' diagnostici dei livelli.** Un cambio di criterio
   sposta la ripartizione fra categorie lasciando il totale quasi fermo: se
   `in porta / tentativi` salta mentre `tentativi per squadra-partita` resta
   dov'era, non e' calcio. Le quattro categorie qui sono una **partizione**
   dei tentativi (in porta, respinto da un difensore, palo, fuori), quindi i
   rapporti si leggono insieme: quello che una categoria guadagna un'altra lo
   perde, e da quale coppia si scambia il flusso si capisce quale confine si e'
   spostato.
2. **Il profilo temporale discrimina.** Un cambio di annotazione e' un
   **gradino** al confine di stagione; la deriva calcistica e' **graduale**.
   Per questo l'aggregazione minima e' il mese, non la stagione: aggregando per
   stagione qualunque deriva continua *sembra* una successione di gradini.
   `scansione_rottura` cerca il punto di rottura in tutti i confini di mese
   possibili e guarda dove cade, invece di assumere che cada a luglio.
3. **Le frequenze dei qualifier.** 259 colonne in tutte e cinque le stagioni
   non dice niente sulla distribuzione dei valori. Un qualifier che compare o
   sparisce, o la cui frequenza salta, e' il segnale piu' diretto: e' l'atto di
   annotazione stesso, non una sua conseguenza a valle.

I BASELINE
----------
Il vincolo 6 del progetto vale anche qui, e in questo blocco e' particolarmente
facile sbagliare: con 47.000 tiri ogni differenza fra stagioni e' "visibile", e
quasi tutte sono rumore di campionamento. Accanto a ogni stima ci sono quindi:

* **il numero unico** — un solo tasso per tutte e cinque le stagioni (il
  modello M0), che e' il baseline stupido per eccellenza;
* **la deviazione standard attesa sotto quel numero unico**, binomiale sui
  denominatori veri. Uno scarto fra stagioni si legge in unita' di quella;
* **la sovradispersione osservata** `phi`, stimata sulle unita'
  squadra-partita: senza correggerla ogni test su 3.778 unita' rifiuta tutto.
  I confronti fra modelli sono quasi-verosimiglianza, non verosimiglianza;
* **la distribuzione del massimo sotto l'ipotesi nulla**, simulata, per la
  scansione del punto di rottura: scegliere il confine migliore fra i cinquanta
  possibili e poi testarlo come se fosse stato scelto in anticipo e' il modo
  standard di trovare gradini che non ci sono.

COSA QUESTO MODULO NON PUO' FARE
--------------------------------
Non puo' separare "il criterio e' cambiato" da "il calcio e' cambiato in modo
brusco esattamente a fine giugno". Nessun dato interno alla fonte puo' farlo:
la firma delle due ipotesi e' la stessa. Puo' pero' dire quale delle due
sarebbe la spiegazione piu' economica, e soprattutto puo' **escludere** il
problema quando non c'e' — che e' l'esito utile per la Fase 7B.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from . import config, io_events, shots as SH

# --------------------------------------------------------------------------
# Estrazione
# --------------------------------------------------------------------------

# I quattro tipi evento che WhoScored usa per una conclusione. `SavedShot`
# copre sia le parate sia i blocchi di un difensore: `shotBlocked` e' l'unico
# discriminante (vedi `sot/shots.py`, che resta l'unica definizione di SoT).
TIPI_TIRO = ("Goal", "SavedShot", "MissedShots", "ShotOnPost")

# Le categorie sono una partizione dei tentativi, ed e' cio' che le rende
# diagnostiche: la somma delle quattro e' il totale, quindi ogni spostamento di
# confine si vede come travaso fra due di esse.
CATEGORIE = ("in_porta", "bloccato", "palo", "fuori")

# Le booleane che il modello usa davvero: sono gli ingressi dell'xG interno
# (`sot/xg.py`), tutte derivate da `satisfiedEventsTypes`. Se il criterio con
# cui la fonte le assegna si sposta fra stagioni, l'xG stimato su piu' stagioni
# mescola due definizioni — che e' il vincolo 7 della Fase 7 applicato dentro
# casa invece che a una fonte esterna.
FLAG_MODELLO = ("shotOpenPlay", "shotCounter", "shotSetPiece",
                "shotDirectCorner", "bigChanceMissed", "bigChanceScored")

COLONNE_UTILI = [
    "matchId", "teamId", "h_a", "type", "period", "minute", "expandedMinute",
    "isShot", "isGoal", "isOwnGoal", "shotBlocked", "shotOnTarget",
    "shotOffTarget", "shotsTotal", "x", "y", "situation", "shotBodyType",
    "startDate", "qualifiers", *FLAG_MODELLO,
]

_BOOL = ("isShot", "isGoal", "isOwnGoal", "shotBlocked", "shotOnTarget",
         "shotOffTarget", "shotsTotal", *FLAG_MODELLO)


def _leggi_partita(path: Path) -> tuple[pd.DataFrame, dict]:
    """Legge un CSV partita e ne estrae i soli eventi di tiro.

    Ritorna anche la presenza delle colonne **in quel file**: una booleana
    derivata da `satisfiedEventsTypes` viene emessa da pandas solo se in quella
    partita si e' verificata almeno una volta (e' la trappola di `isOwnGoal`,
    assente in 358 file su 380). Una colonna assente in *tutti* i file di una
    stagione e' un'altra cosa, ed e' esattamente il segnale che cerchiamo:
    per distinguerle serve il conteggio file per file, non l'unione.
    """
    header = pd.read_csv(path, nrows=0).columns
    use = [c for c in COLONNE_UTILI if c in header]
    df = pd.read_csv(path, usecols=use, low_memory=False)

    for col in COLONNE_UTILI:
        if col not in df.columns:
            df[col] = False if col in _BOOL else np.nan
    for col in _BOOL:
        df[col] = df[col].astype("boolean").fillna(False).astype(bool)

    tiri = df.loc[df["isShot"] | df["type"].isin(TIPI_TIRO)].copy()

    # Le due squadre si prendono da **tutti** gli eventi, non dai tiri: nel
    # campione esistono squadre-partita con zero tentativi (Pisa-Cremonese
    # 2026-05-10, 0 tiri) e ricostruire l'universo dai soli tiri le farebbe
    # sparire dal denominatore. I denominatori si prendono dai dati.
    lato = df.dropna(subset=["teamId"]).groupby("h_a")["teamId"].first()
    meta = {"matchId": int(df["matchId"].iloc[0]),
            "n_eventi": int(len(df)),
            "n_colonne": int(len(header)),
            "teamId_h": int(lato["h"]) if "h" in lato.index else -1,
            "teamId_a": int(lato["a"]) if "a" in lato.index else -1,
            "startDate": df["startDate"].dropna().iloc[0] if
            df["startDate"].notna().any() else None}
    meta.update({f"col_{c}": (c in header) for c in header})
    return tiri, meta


def costruisci_cache(force: bool = False, stagioni=None) -> None:
    """Estrae i tiri delle stagioni storiche e li mette in cache.

    ~1.900 file, un paio di minuti la prima volta. Il grezzo non viene toccato
    in nessun modo: si legge e basta.
    """
    if (config.SHOTS_ALL_SEASONS.exists()
            and config.FILES_ALL_SEASONS.exists() and not force):
        return

    stagioni = tuple(config.SEASONS_STORICHE if stagioni is None else stagioni)
    tiri_parts, meta_parts = [], []
    for season in stagioni:
        cartella = config.raw_dir("whoscored", season=season) / "events"
        files = sorted(cartella.glob("*.csv"))
        if not files:
            raise FileNotFoundError(f"nessun CSV in {cartella}")
        for f in files:
            t, m = _leggi_partita(f)
            t["stagione"] = season
            m["stagione"] = season
            tiri_parts.append(t)
            meta_parts.append(m)

    tiri = pd.concat(tiri_parts, ignore_index=True)
    tiri["startDate"] = pd.to_datetime(tiri["startDate"])
    tiri["matchId"] = tiri["matchId"].astype("int64")
    tiri["teamId"] = tiri["teamId"].astype("int64")
    for col in ("type", "h_a", "situation", "shotBodyType", "qualifiers"):
        tiri[col] = tiri[col].map(lambda v: v if isinstance(v, str) else pd.NA)
        tiri[col] = tiri[col].astype("string")

    meta = pd.DataFrame(meta_parts)
    for c in meta.columns:
        if c.startswith("col_"):
            meta[c] = meta[c].fillna(False).astype(bool)
    meta["startDate"] = pd.to_datetime(meta["startDate"])

    tiri.to_parquet(config.SHOTS_ALL_SEASONS, index=False)
    meta.to_parquet(config.FILES_ALL_SEASONS, index=False)


def carica_tiri(force: bool = False) -> pd.DataFrame:
    """Tiri delle cinque stagioni, con categoria e mese gia' calcolati."""
    costruisci_cache(force=force)
    tiri = pd.read_parquet(config.SHOTS_ALL_SEASONS)
    tiri["categoria"] = categoria(tiri)
    tiri["mese"] = tiri["startDate"].dt.to_period("M").astype(str)
    return tiri


def carica_file(force: bool = False) -> pd.DataFrame:
    """Una riga per file acquisito: eventi, colonne presenti, data."""
    costruisci_cache(force=force)
    return pd.read_parquet(config.FILES_ALL_SEASONS)


# --------------------------------------------------------------------------
# Categorie
# --------------------------------------------------------------------------
def categoria(tiri: pd.DataFrame) -> pd.Series:
    """Partizione dei tentativi nelle quattro categorie.

    `in_porta` e' la maschera di `sot/shots.py`, importata e non riscritta:
    duplicare la definizione di tiro in porta e' esattamente cio' che il
    progetto vieta. Le altre tre sono definite per differenza sui tipi evento,
    e `altro` esiste per non nascondere sotto il tappeto un tipo inatteso.
    """
    sot = SH.shots_on_target_mask(tiri)
    tipo = tiri["type"].astype("string")
    blocked = tiri["shotBlocked"].astype("boolean").fillna(False).to_numpy()

    cat = pd.Series("altro", index=tiri.index, dtype="object")
    cat[(tipo == "MissedShots").to_numpy()] = "fuori"
    cat[(tipo == "ShotOnPost").to_numpy()] = "palo"
    cat[((tipo == "SavedShot").to_numpy() & blocked)] = "bloccato"
    cat[sot.to_numpy()] = "in_porta"
    return cat


def universo_squadra_partita(meta: pd.DataFrame) -> pd.DataFrame:
    """Le 2 x N righe squadra-partita che *devono* esistere, dai file.

    Costruito dai metadati di ogni file e non dai tiri, perche' una squadra con
    zero tentativi non compare fra i tiri e sparirebbe dal denominatore.
    """
    parti = [meta[["stagione", "matchId", "startDate"]].assign(
        teamId=meta[f"teamId_{lato}"].to_numpy(), h_a=lato)
        for lato in ("h", "a")]
    u = pd.concat(parti, ignore_index=True).rename(columns={"startDate": "data"})
    return u[u["teamId"] > 0].reset_index(drop=True)


def unita_squadra_partita(tiri: pd.DataFrame,
                          meta: pd.DataFrame | None = None) -> pd.DataFrame:
    """Una riga per squadra-partita: e' l'unita' di tutti i modelli.

    Non il singolo tiro: i tiri della stessa squadra nella stessa partita non
    sono indipendenti, ed e' da li' che viene la sovradispersione. Modellare
    sui tiri darebbe intervalli falsamente stretti.
    """
    meta = carica_file() if meta is None else meta
    out = universo_squadra_partita(meta)

    t = tiri[SH.shots_mask(tiri).to_numpy()].copy()
    chiave = ["stagione", "matchId", "teamId"]
    conteggi = t.groupby(chiave, as_index=False).size().rename(
        columns={"size": "tentativi"})
    out = out.merge(conteggi, on=chiave, how="left")
    for c in CATEGORIE:
        n = (t.assign(f=(t["categoria"] == c).astype(int))
               .groupby(chiave, as_index=False)["f"].sum())
        out = out.merge(n.rename(columns={"f": c}), on=chiave, how="left")
    # Anche gli ingressi dell'xG: sono conteggi sugli stessi tentativi, quindi
    # passano dalla stessa macchina di confronto fra modelli.
    out = out.merge(t.groupby(chiave, as_index=False)[list(FLAG_MODELLO)].sum(),
                    on=chiave, how="left")
    for c in ("tentativi",) + CATEGORIE + FLAG_MODELLO:
        out[c] = out[c].fillna(0).astype(int)

    out["mese"] = out["data"].dt.to_period("M").astype(str)
    out["giorno"] = (out["data"] - out["data"].min()).dt.days.astype(float)
    return out.sort_values(["data", "matchId", "h_a"]).reset_index(drop=True)


# --------------------------------------------------------------------------
# Livelli e rapporti, con i baseline accanto
# --------------------------------------------------------------------------
def per_stagione(unita: pd.DataFrame) -> pd.DataFrame:
    """Totali, livelli e rapporti per stagione."""
    g = unita.groupby("stagione")
    out = pd.DataFrame({
        "squadra_partita": g.size(),
        "tentativi": g["tentativi"].sum(),
        **{c: g[c].sum() for c in CATEGORIE},
    })
    out["partite"] = g["matchId"].nunique()
    out["tentativi_per_sp"] = out["tentativi"] / out["squadra_partita"]
    for c in CATEGORIE:
        out[f"{c}_per_sp"] = out[c] / out["squadra_partita"]
        out[f"q_{c}"] = out[c] / out["tentativi"]
    return out.reset_index()


def per_mese(unita: pd.DataFrame) -> pd.DataFrame:
    """Stessa cosa per mese di calendario: e' la scala su cui un gradino di
    annotazione si distingue da una deriva."""
    g = unita.groupby(["stagione", "mese"])
    out = pd.DataFrame({
        "squadra_partita": g.size(),
        "tentativi": g["tentativi"].sum(),
        **{c: g[c].sum() for c in CATEGORIE},
    }).reset_index()
    out["tentativi_per_sp"] = out["tentativi"] / out["squadra_partita"]
    for c in CATEGORIE:
        out[f"q_{c}"] = out[c] / out["tentativi"]
    return out.sort_values("mese").reset_index(drop=True)


def scarti_dal_numero_unico(stag: pd.DataFrame, categoria_: str) -> pd.DataFrame:
    """Ogni stagione contro il baseline stupido: **un numero solo per tutte**.

    Lo scarto si legge in unita' della deviazione standard attesa sotto quel
    numero unico, non in punti percentuali: con denominatori da 9.000 tiri
    mezzo punto percentuale e' enorme, con denominatori da 200 e' niente.
    La colonna `z_binomiale` **sottostima** l'incertezza perche' ignora la
    sovradispersione — accanto c'e' `z_corretto`, che la include.
    """
    p0 = stag[categoria_].sum() / stag["tentativi"].sum()
    n = stag["tentativi"].to_numpy(float)
    p = stag[categoria_].to_numpy(float) / n
    sd = np.sqrt(p0 * (1 - p0) / n)
    return pd.DataFrame({
        "stagione": stag["stagione"].to_numpy(),
        "n": n.astype(int),
        "quota": p,
        "baseline_unico": p0,
        "scarto": p - p0,
        "sd_binomiale": sd,
        "z_binomiale": (p - p0) / sd,
    })


def scarti_livello(stag: pd.DataFrame, colonna: str, unita: pd.DataFrame,
                   categoria_: str) -> pd.DataFrame:
    """Come sopra ma per un livello (per squadra-partita), dove il baseline e'
    la media unica e la deviazione standard e' quella campionaria vera, non
    binomiale: sui conteggi per partita la varianza non e' `p(1-p)`."""
    m0 = unita[categoria_].mean()
    sd_unit = unita[categoria_].std(ddof=1)
    n = stag["squadra_partita"].to_numpy(float)
    m = stag[colonna].to_numpy(float)
    sd = sd_unit / np.sqrt(n)
    return pd.DataFrame({
        "stagione": stag["stagione"].to_numpy(),
        "squadra_partita": n.astype(int),
        "media": m,
        "baseline_unico": m0,
        "scarto": m - m0,
        "sd_media": sd,
        "z": (m - m0) / sd,
    })


# --------------------------------------------------------------------------
# Modelli: costante, gradino di stagione, deriva, stagionalita' di calendario
# --------------------------------------------------------------------------
def _devianza(k: np.ndarray, n: np.ndarray, p: np.ndarray) -> float:
    """Devianza binomiale, con 0*log(0) = 0.

    Le unita' con zero tentativi contribuiscono zero e vanno tolte prima della
    divisione, non dopo: esistono davvero (una squadra puo' non tirare) e
    lasciarle dentro produrrebbe 0/0.
    """
    k, n, p = np.asarray(k, float), np.asarray(n, float), np.asarray(p, float)
    vive = n > 0
    k, n, p = k[vive], n[vive], np.clip(p[vive], 1e-12, 1 - 1e-12)
    a = np.where(k > 0, k * np.log(np.where(k > 0, k, 1.0) / (n * p)), 0.0)
    b = np.where(n - k > 0,
                 (n - k) * np.log(np.where(n - k > 0, n - k, 1.0) / (n * (1 - p))), 0.0)
    return float(2.0 * np.sum(a + b))


def _p_per_gruppo(k: np.ndarray, n: np.ndarray, gruppo: np.ndarray) -> np.ndarray:
    """Stime di massima verosimiglianza di un modello a sole dummy: sono le
    proporzioni di gruppo, in forma chiusa. Nessun IRLS serve, ed e' cio' che
    rende la scansione del punto di rottura e la simulazione praticabili."""
    df = pd.DataFrame({"k": k, "n": n, "g": gruppo})
    tot = df.groupby("g")[["k", "n"]].sum()
    p = (tot["k"] / tot["n"]).to_dict()
    return np.array([p[g] for g in gruppo], float)


def _logistica_pesata(X: np.ndarray, k: np.ndarray, n: np.ndarray,
                      n_iter: int = 100, tol: float = 1e-11) -> np.ndarray:
    """IRLS per la binomiale con `n` prove per riga. Serve solo al modello di
    deriva continua, l'unico non riducibile a proporzioni di gruppo."""
    beta = np.zeros(X.shape[1])
    p0 = k.sum() / n.sum()
    beta[0] = np.log(p0 / (1 - p0))
    for _ in range(n_iter):
        eta = X @ beta
        p = 1.0 / (1.0 + np.exp(-eta))
        w = np.maximum(n * p * (1 - p), 1e-10)
        z = eta + (k - n * p) / w
        XW = X * w[:, None]
        nuovo = np.linalg.solve(XW.T @ X + 1e-9 * np.eye(X.shape[1]), XW.T @ z)
        if np.max(np.abs(nuovo - beta)) < tol:
            return nuovo
        beta = nuovo
    return beta


def unita_valide(unita: pd.DataFrame) -> pd.DataFrame:
    """Le squadre-partita con almeno un tentativo.

    Sono quelle che portano informazione su un **rapporto**: un'unita' con zero
    tiri non dice niente su quale quota finisca in porta. Vanno tolte qui e non
    dai livelli, dove invece contano eccome — sono partite vere, non dati
    mancanti.
    """
    return unita[unita["tentativi"] > 0].reset_index(drop=True)


def dispersione(unita: pd.DataFrame, categoria_: str) -> float:
    """`phi` di quasi-verosimiglianza, dal modello piu' ricco (cella
    stagione x mese) sulle unita' squadra-partita.

    E' il numero che rende onesti tutti i confronti successivi. Senza, con
    3.778 unita' e denominatori a due cifre, qualunque differenza fra stagioni
    risulta significativa.
    """
    unita = unita_valide(unita)
    k = unita[categoria_].to_numpy(float)
    n = unita["tentativi"].to_numpy(float)
    cella = (unita["stagione"] + "|" + unita["mese"]).to_numpy()
    p = _p_per_gruppo(k, n, cella)
    pearson = np.sum((k - n * p) ** 2 / np.maximum(n * p * (1 - p), 1e-12))
    gdl = len(k) - len(np.unique(cella))
    return float(pearson / gdl)


def confronto_modelli(unita: pd.DataFrame, categoria_: str) -> pd.DataFrame:
    """Quattro modelli sulla stessa quantita', confrontati in
    quasi-verosimiglianza.

    | modello | cosa dice |
    |---|---|
    | M0 costante | il baseline stupido: un tasso solo, sempre |
    | M1 gradino di stagione | il criterio cambia solo ai confini di stagione |
    | M2 deriva continua | il tasso si muove piano, nel logit, lungo il tempo |
    | M3 mese di calendario | e' stagionalita' calcistica, uguale in ogni anno |

    M1 contro M2 e' il confronto che decide, e non e' annidato: si legge sulla
    QAIC, non su un test. M3 esiste perche' senza di lui un effetto di
    calendario che si ripete ogni anno verrebbe letto come gradino.
    """
    unita = unita_valide(unita)
    k = unita[categoria_].to_numpy(float)
    n = unita["tentativi"].to_numpy(float)
    phi = dispersione(unita, categoria_)

    mese_cal = pd.to_datetime(unita["data"]).dt.month.astype(str).to_numpy()
    t = unita["giorno"].to_numpy(float)
    t = (t - t.mean()) / t.std(ddof=0)

    fit = {
        "M0 costante": (np.full(len(k), k.sum() / n.sum()), 1),
        "M1 gradino di stagione": (
            _p_per_gruppo(k, n, unita["stagione"].to_numpy()),
            unita["stagione"].nunique()),
        "M3 mese di calendario": (
            _p_per_gruppo(k, n, mese_cal), len(np.unique(mese_cal))),
    }
    X = np.column_stack([np.ones(len(k)), t])
    beta = _logistica_pesata(X, k, n)
    fit["M2 deriva continua"] = (1.0 / (1.0 + np.exp(-(X @ beta))), 2)

    righe = []
    for nome in ("M0 costante", "M1 gradino di stagione", "M2 deriva continua",
                 "M3 mese di calendario"):
        p, npar = fit[nome]
        dev = _devianza(k, n, p)
        righe.append({"modello": nome, "parametri": npar, "devianza": dev,
                      "QAIC": dev / phi + 2 * npar})
    out = pd.DataFrame(righe)
    out["dQAIC"] = out["QAIC"] - out["QAIC"].min()
    out["phi"] = phi
    return out


def test_annidati(unita: pd.DataFrame, categoria_: str) -> pd.DataFrame:
    """M1 e M2 contro il baseline costante, in quasi-verosimiglianza (test F).

    Con `phi` intorno a 1.1-1.3 la differenza fra questo e un chi-2 ingenuo e'
    di un fattore su tutte le statistiche: e' la differenza fra "nove
    differenze significative" e "nessuna".
    """
    from scipy import stats

    unita = unita_valide(unita)
    k = unita[categoria_].to_numpy(float)
    n = unita["tentativi"].to_numpy(float)
    phi = dispersione(unita, categoria_)
    gdl_res = len(k) - (unita["stagione"] + "|" + unita["mese"]).nunique()

    d0 = _devianza(k, n, np.full(len(k), k.sum() / n.sum()))
    t = unita["giorno"].to_numpy(float)
    t = (t - t.mean()) / t.std(ddof=0)
    X = np.column_stack([np.ones(len(k)), t])
    p2 = 1.0 / (1.0 + np.exp(-(X @ _logistica_pesata(X, k, n))))
    mese_cal = pd.to_datetime(unita["data"]).dt.month.astype(str).to_numpy()

    prove = [
        ("M1 gradino di stagione", _p_per_gruppo(k, n, unita["stagione"].to_numpy()),
         unita["stagione"].nunique() - 1),
        ("M2 deriva continua", p2, 1),
        ("M3 mese di calendario", _p_per_gruppo(k, n, mese_cal),
         len(np.unique(mese_cal)) - 1),
    ]
    righe = []
    for nome, p, gdl in prove:
        d = _devianza(k, n, p)
        F = ((d0 - d) / gdl) / phi
        righe.append({"contro M0": nome, "gdl": gdl, "riduzione_devianza": d0 - d,
                      "F": F, "p": float(stats.f.sf(F, gdl, gdl_res)), "phi": phi})
    return pd.DataFrame(righe)


def mde_gradino(unita: pd.DataFrame, categoria_: str, potenza: float = 0.80,
                alpha: float = 0.05) -> pd.DataFrame:
    """Effetto minimo rilevabile di un gradino, a ciascun confine di stagione.

    Un risultato negativo senza potenza dichiarata non e' un risultato: e' la
    lezione della Fase 6D, e qui vale identica. Si riporta di quanto dovrebbe
    spostarsi la quota perche' questo blocco la vedesse, e la stessa cosa
    tradotta in tiri in porta per squadra-partita — che e' l'unita' in cui il
    resto del progetto ragiona.
    """
    from scipy import stats

    u = unita_valide(unita)
    phi = dispersione(u, categoria_)
    z = stats.norm.ppf(1 - alpha / 2) + stats.norm.ppf(potenza)
    p0 = u[categoria_].sum() / u["tentativi"].sum()
    tent_medi = u["tentativi"].mean()

    stagioni = sorted(u["stagione"].unique())
    righe = []
    for i in range(len(stagioni) - 1):
        pre = u["stagione"] <= stagioni[i]
        n1 = float(u.loc[pre, "tentativi"].sum())
        n2 = float(u.loc[~pre, "tentativi"].sum())
        sd = np.sqrt(phi * p0 * (1 - p0) * (1 / n1 + 1 / n2))
        righe.append({"confine": stagioni[i + 1], "n_prima": int(n1),
                      "n_dopo": int(n2), "sd_differenza": sd,
                      "mde_quota": z * sd,
                      "mde_relativo": z * sd / p0,
                      "mde_in_tiri_per_sp": z * sd * tent_medi})
    return pd.DataFrame(righe)


def mde_livello(unita: pd.DataFrame, colonna: str, potenza: float = 0.80,
                alpha: float = 0.05) -> pd.DataFrame:
    """Come sopra ma su un livello per squadra-partita, dove la dispersione
    e' quella empirica: sui conteggi la varianza non e' `p(1-p)` e usarla
    darebbe una potenza inventata."""
    from scipy import stats

    z = stats.norm.ppf(1 - alpha / 2) + stats.norm.ppf(potenza)
    sd_unit = float(unita[colonna].std(ddof=1))
    stagioni = sorted(unita["stagione"].unique())
    righe = []
    for i in range(len(stagioni) - 1):
        pre = unita["stagione"] <= stagioni[i]
        n1, n2 = float(pre.sum()), float((~pre).sum())
        sd = sd_unit * np.sqrt(1 / n1 + 1 / n2)
        righe.append({"confine": stagioni[i + 1], "n_prima": int(n1),
                      "n_dopo": int(n2), "sd_differenza": sd,
                      "mde": z * sd,
                      "mde_relativo": z * sd / float(unita[colonna].mean())})
    return pd.DataFrame(righe)


# --------------------------------------------------------------------------
# Dove cade il gradino
# --------------------------------------------------------------------------
def _scan(k: np.ndarray, n: np.ndarray, ord_mese: np.ndarray,
          n_mesi: int) -> np.ndarray:
    """Riduzione di devianza di un modello a un solo gradino, per ogni confine
    di mese. Tutto in forma chiusa: due proporzioni, prima e dopo."""
    ks = np.array([k[ord_mese == i].sum() for i in range(n_mesi)], float)
    ns = np.array([n[ord_mese == i].sum() for i in range(n_mesi)], float)
    d0 = _devianza(k, n, np.full(len(k), k.sum() / n.sum()))
    out = np.full(n_mesi - 1, np.nan)
    for b in range(n_mesi - 1):
        pre = ord_mese <= b
        p = np.where(pre, ks[:b + 1].sum() / ns[:b + 1].sum(),
                     ks[b + 1:].sum() / ns[b + 1:].sum())
        out[b] = d0 - _devianza(k, n, p)
    return out


def scansione_rottura(unita: pd.DataFrame, categoria_: str) -> pd.DataFrame:
    """Un gradino solo, provato in tutti i confini di mese.

    Il punto non e' *se* esiste un confine che migliora l'adattamento — ne
    esiste sempre uno, e' il massimo di una cinquantina di numeri positivi — ma
    **dove cade**. Se il criterio di annotazione fosse cambiato, cadrebbe fra
    maggio e agosto. Se cade a novembre, quello che si e' trovato e' rumore o
    calcio.
    """
    unita = unita_valide(unita)
    mesi = np.sort(unita["mese"].unique())
    idx = {m: i for i, m in enumerate(mesi)}
    ordine = unita["mese"].map(idx).to_numpy()
    riduz = _scan(unita[categoria_].to_numpy(float),
                  unita["tentativi"].to_numpy(float), ordine, len(mesi))
    out = pd.DataFrame({"prima_di": mesi[1:], "riduzione_devianza": riduz})
    out["confine_di_stagione"] = [_e_confine_di_stagione(m) for m in out["prima_di"]]
    return out


def _e_confine_di_stagione(mese: str) -> bool:
    """Un confine e' "di stagione" se separa la fine di un campionato
    dall'inizio del successivo. In Serie A si gioca da agosto a maggio: i mesi
    che aprono una stagione sono luglio e agosto."""
    return mese.endswith("-07") or mese.endswith("-08")


def prova_rottura(unita: pd.DataFrame, categoria_: str, n_sim: int = 1000,
                  seed: int | None = None, solo_stagione: bool = False) -> dict:
    """Il massimo della scansione contro la sua distribuzione sotto M0.

    Il baseline e' generato, non assunto: si simula sotto "un tasso solo,
    sempre" con i **denominatori veri** e la **sovradispersione osservata**
    (beta-binomiale con la stessa `phi`), si rifa' la scansione su ogni
    replica, e si guarda quanto spesso il massimo simulato supera quello vero.
    Senza questo passaggio la scansione trova un gradino in qualunque serie.

    Due versioni, e vanno lette insieme:

    * `solo_stagione=False` — il massimo su tutti i confini di mese. Risponde a
      "esiste un gradino da qualche parte?", ed e' il test onesto ma debole:
      paga la ricerca su una cinquantina di candidati;
    * `solo_stagione=True` — il massimo sui soli confini di stagione. E'
      l'ipotesi **dichiarata in anticipo** ("se il criterio e' cambiato, e'
      cambiato fra due campionati") e per questo ha molta piu' potenza: cerca
      su 4 candidati invece che su una cinquantina.
    """
    rng = np.random.default_rng(config.SEED if seed is None else seed)
    unita = unita_valide(unita)
    k = unita[categoria_].to_numpy(float)
    n = unita["tentativi"].to_numpy(float)
    mesi = np.sort(unita["mese"].unique())
    idx = {m: i for i, m in enumerate(mesi)}
    ordine = unita["mese"].map(idx).to_numpy()

    ammessi = np.array([_e_confine_di_stagione(m) for m in mesi[1:]]) \
        if solo_stagione else np.ones(len(mesi) - 1, dtype=bool)

    def _massimo(riduz):
        r = np.where(ammessi, riduz, -np.inf)
        i = int(np.nanargmax(r))
        return float(r[i]), i

    oss_tutti = _scan(k, n, ordine, len(mesi))
    oss, b_oss = _massimo(oss_tutti)

    p0 = k.sum() / n.sum()
    phi = dispersione(unita, categoria_)
    n_medio = n.mean()
    # phi = 1 + (n_medio - 1) * rho_ic  ->  rho_ic; sotto n medio 1 o phi <= 1
    # la beta-binomiale degenera nella binomiale, ed e' il caso giusto.
    rho_ic = max((phi - 1.0) / max(n_medio - 1.0, 1e-9), 0.0)

    massimi = np.empty(n_sim)
    posizioni = np.empty(n_sim, dtype=int)
    for s in range(n_sim):
        if rho_ic > 0:
            a = p0 * (1 - rho_ic) / rho_ic
            b = (1 - p0) * (1 - rho_ic) / rho_ic
            pi = rng.beta(a, b, size=len(n))
        else:
            pi = np.full(len(n), p0)
        ks = rng.binomial(n.astype(int), pi).astype(float)
        massimi[s], posizioni[s] = _massimo(_scan(ks, n, ordine, len(mesi)))

    return {
        "categoria": categoria_,
        "candidati": int(ammessi.sum()),
        "confine_migliore": mesi[b_oss + 1],
        "riduzione_osservata": oss,
        "e_confine_di_stagione": _e_confine_di_stagione(mesi[b_oss + 1]),
        "mediana_nulla": float(np.median(massimi)),
        "q95_nulla": float(np.quantile(massimi, 0.95)),
        "p_max": float((np.sum(massimi >= oss) + 1) / (n_sim + 1)),
        "quota_nulla_su_confine_stagione": float(np.mean(
            [_e_confine_di_stagione(mesi[i + 1]) for i in posizioni])),
        "phi": phi, "n_sim": n_sim,
    }


# --------------------------------------------------------------------------
# Qualifier
# --------------------------------------------------------------------------
def frequenze_qualifier(tiri: pd.DataFrame) -> pd.DataFrame:
    """Quota di tiri che portano ciascun qualifier, per stagione.

    Si conta la **presenza** sul tiro, non le occorrenze: cosi' la grandezza e'
    una proporzione con denominatore noto, e la variabilita' attesa sotto
    stabilita' e' calcolabile. Il parser e' quello di `io_events`
    (`ast.literal_eval`: i qualifier sono repr Python, non JSON).
    """
    t = tiri[SH.shots_mask(tiri).to_numpy()]
    righe = []
    for stagione, sub in t.groupby("stagione"):
        conteggio: dict[str, int] = {}
        for raw in sub["qualifiers"].fillna(""):
            for q in io_events.parse_qualifiers(raw):
                conteggio[q] = conteggio.get(q, 0) + 1
        n = len(sub)
        for q, c in conteggio.items():
            righe.append({"stagione": stagione, "qualifier": q,
                          "tiri": n, "presenze": c, "quota": c / n})
    out = pd.DataFrame(righe)
    return out.pivot(index="qualifier", columns="stagione",
                     values="quota").fillna(0.0)


def presenza_per_partita(tiri: pd.DataFrame, qualifier: str) -> pd.DataFrame:
    """Quota di tentativi che portano un qualifier, **partita per partita**.

    E' la domanda che distingue un cambio di criterio da un cambio di fornitura
    del dato: se un qualifier sparisce in modo graduale su tutte le partite,
    e' un criterio che si sposta; se sparisce per pagine intere — o c'e' su
    quasi tutti i tiri della partita, o su nessuno — e' una proprieta' della
    pagina, cioe' qualcosa che e' successo a quel documento, non al calcio.
    """
    t = tiri[SH.shots_mask(tiri).to_numpy()].copy()
    presente = [qualifier in io_events.parse_qualifiers(q)
                for q in t["qualifiers"].fillna("")]
    t = t.assign(_p=presente)
    return (t.groupby(["stagione", "matchId"])["_p"].mean()
             .reset_index().rename(columns={"_p": "quota"}))


def qualifier_instabili(tiri: pd.DataFrame, freq: pd.DataFrame,
                        soglia_z: float = 6.0) -> pd.DataFrame:
    """I qualifier che compaiono, spariscono o saltano fra stagioni adiacenti.

    Il salto e' standardizzato sulla deviazione standard binomiale attesa sotto
    quota costante: e' il baseline. La soglia e' alta di proposito — con 9.000
    tiri per stagione un `z` di 3 lo produce qualunque fluttuazione reale di
    stile di gioco, e la domanda qui non e' se il calcio sia cambiato.
    """
    n_stag = (tiri[SH.shots_mask(tiri).to_numpy()]
              .groupby("stagione").size().reindex(freq.columns))
    righe = []
    cols = list(freq.columns)
    for q, r in freq.iterrows():
        for i in range(len(cols) - 1):
            a, b = cols[i], cols[i + 1]
            na, nb = float(n_stag[a]), float(n_stag[b])
            pa, pb = float(r[a]), float(r[b])
            pool = (pa * na + pb * nb) / (na + nb)
            sd = np.sqrt(max(pool * (1 - pool), 1e-12) * (1 / na + 1 / nb))
            z = (pb - pa) / sd
            comparsa = (pa == 0) != (pb == 0)
            if abs(z) >= soglia_z or comparsa:
                righe.append({"qualifier": q, "da": a, "a": b,
                              "quota_da": pa, "quota_a": pb, "delta": pb - pa,
                              "sd_attesa": sd, "z": z,
                              "compare_o_sparisce": comparsa})
    out = pd.DataFrame(righe)
    if out.empty:
        return out
    return out.reindex(out["z"].abs().sort_values(ascending=False).index)


def colonne_per_stagione(meta: pd.DataFrame) -> pd.DataFrame:
    """In quanti file di ciascuna stagione compare ogni colonna.

    Una colonna al 100% ovunque e' stabile; una al 5% in una stagione e allo 0%
    in un'altra e' la trappola di `isOwnGoal`, non un cambio di criterio; una al
    100% in quattro stagioni e allo 0% nella quinta lo sarebbe.
    """
    cols = [c for c in meta.columns if c.startswith("col_")]
    q = meta.groupby("stagione")[cols].mean().T
    q.index = [c[len("col_"):] for c in q.index]
    q.index.name = "colonna"
    return q


def colonne_instabili(quote: pd.DataFrame) -> pd.DataFrame:
    """Le sole colonne che non sono presenti in tutti i file di tutte le
    stagioni, con la distinzione che conta: assente **in tutta** una stagione
    (segnale) oppure sporadica ovunque (trappola nota)."""
    inst = quote[(quote < 1.0).any(axis=1)].copy()
    inst["assente_in_una_stagione_intera"] = (inst == 0.0).any(axis=1) & (inst > 0).any(axis=1)
    inst["sporadica_ovunque"] = ((inst[quote.columns] > 0) & (inst[quote.columns] < 1)).all(axis=1)
    return inst.sort_values("assente_in_una_stagione_intera", ascending=False)


# --------------------------------------------------------------------------
# Coerenza interna della definizione
# --------------------------------------------------------------------------
def coerenza_flag_opta(tiri: pd.DataFrame) -> pd.DataFrame:
    """La regola del repository contro il flag Opta nativo `shotOnTarget`.

    La Fase 0 ha verificato l'identita' sul 2025-26 (3066 = 3066). Se in una
    stagione precedente le due divergessero, il criterio *e'* cambiato — o e'
    cambiato il modo in cui lo scraper appiattisce `satisfiedEventsTypes` — e
    sarebbe il segnale piu' forte che questo modulo puo' produrre, perche' non
    passa da nessun modello.
    """
    t = tiri[SH.shots_mask(tiri).to_numpy()].copy()
    t["regola"] = SH.shots_on_target_mask(t).to_numpy()
    t["flag"] = t["shotOnTarget"].astype("boolean").fillna(False).to_numpy()
    g = t.groupby("stagione")
    out = pd.DataFrame({
        "tentativi": g.size(),
        "regola": g["regola"].sum(),
        "flag_opta": g["flag"].sum(),
        "solo_regola": g.apply(lambda d: int((d["regola"] & ~d["flag"]).sum()),
                               include_groups=False),
        "solo_flag": g.apply(lambda d: int((~d["regola"] & d["flag"]).sum()),
                             include_groups=False),
    }).reset_index()
    out["identiche"] = (out["solo_regola"] == 0) & (out["solo_flag"] == 0)
    return out


def flag_del_modello(tiri: pd.DataFrame) -> pd.DataFrame:
    """Gli ingressi dell'xG interno, stagione per stagione, col baseline unico.

    E' la parte del blocco che guarda **cio' che il modello usa davvero**, non
    la definizione di SoT: se `shotCounter` passa dal 3% al 7% dei tentativi, un
    xG stimato su cinque stagioni impara un contromisura che nelle prime non
    esisteva. Lo `z` e' binomiale sui tentativi della stagione contro la quota
    unica, e come sempre **sottostima** l'incertezza perche' i tiri della stessa
    partita non sono indipendenti.
    """
    t = tiri[SH.shots_mask(tiri).to_numpy()]
    n = t.groupby("stagione").size()
    righe = []
    for flag in FLAG_MODELLO:
        q = t.groupby("stagione")[flag].mean()
        p0 = float(t[flag].mean())
        sd = np.sqrt(p0 * (1 - p0) / n)
        for s in q.index:
            righe.append({"flag": flag, "stagione": s, "quota": float(q[s]),
                          "baseline_unico": p0, "sd_binomiale": float(sd[s]),
                          "z": float((q[s] - p0) / sd[s])})
    return pd.DataFrame(righe)


def igiene_annotazione(tiri: pd.DataFrame) -> pd.DataFrame:
    """Indicatori che non c'entrano con la definizione di SoT ma che si
    muovono quando cambia chi annota: coordinate mancanti, tiri annotati
    nella propria meta' campo, `situation` nulla, tipo evento senza `isShot`."""
    t = tiri.copy()
    tent = SH.shots_mask(t).to_numpy()
    t = t[tent | t["type"].isin(TIPI_TIRO).to_numpy()]
    g = t.groupby("stagione")
    return pd.DataFrame({
        "eventi_di_tiro": g.size(),
        "x_mancante": g["x"].apply(lambda s: float(s.isna().mean())),
        "x_sotto_50": g["x"].apply(lambda s: float((s < 50).mean())),
        "situation_nulla": g["situation"].apply(lambda s: float(s.isna().mean())),
        "tipo_tiro_senza_isShot": g.apply(
            lambda d: float((d["type"].isin(TIPI_TIRO) & ~d["isShot"]).mean()),
            include_groups=False),
        "isShot_senza_tipo_tiro": g.apply(
            lambda d: float((d["isShot"] & ~d["type"].isin(TIPI_TIRO)).mean()),
            include_groups=False),
        "x_medio": g["x"].mean(),
    }).reset_index()
