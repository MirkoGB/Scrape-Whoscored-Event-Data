# -*- coding: utf-8 -*-
"""Blocco 0 — ricognizione di cio' che sta davvero sul disco.

COSA FA, E COSA DELIBERATAMENTE NON FA
--------------------------------------
Legge i 1.889 CSV WhoScored delle cinque stagioni e ne misura schema,
copertura, tipi di evento, qualifier e anagrafiche. **Non stima niente, non
imputa niente, non scrive sotto `raw/`.** E' il blocco che precede qualunque
modello (regola di condotta 5 del prompt di Fase 8).

Il modulo copre **una sola delle due fonti richieste dal Blocco 0**. I voti
fantacalcio non sono sul disco — vedi `stato_fonte_voti()`, che lo accerta
invece di assumerlo — quindi 0.2 (aggancio delle identita'), 0.3 (stabilita'
del criterio di voto) e la meta' misurabile di 0.4 (tasso d'errore della
regola dell'80') non sono calcolabili e **non vengono simulate**.

PERCHE' UN MODULO NUOVO INVECE DI RIUSARE `io_events`
-----------------------------------------------------
`io_events.build_cache` legge **una** stagione (quella di `config.SEASON`) e
tiene solo ~60 colonne su 258, perche' e' la lettura che serve al modello dei
tiri. La ricognizione ha il requisito opposto: deve vedere **tutte** le
colonne di **tutte** le stagioni, comprese quelle che il modello non usa,
perche' il suo scopo e' proprio accorgersi di cosa compare e cosa sparisce.
Allargare `io_events` avrebbe fatto pagare 258 colonne a tutte le Fasi 1-6.

TRE TRAPPOLE GIA' NOTE CHE QUI VANNO TRATTATE, NON EVITATE
-----------------------------------------------------------
1. **Una colonna assente non e' una colonna vuota.** `isOwnGoal` manca dal file
   quando in quella partita non ci sono autogol: pandas non la emette affatto.
   Distinguere "assente dal file" da "presente e tutta nulla" e' l'intero punto
   di 0.1, quindi le due grandezze si contano separate
   (`file_con_colonna` contro `non_nulli`) e mai sommate.
2. **`eventId` non e' una chiave.** E' numerato per squadra; `id` ha 30
   collisioni genuine. La chiave e' `(matchId, teamId, eventId)`.
3. **I qualifier sono repr Python, non JSON.** Qui pero' non serve
   `ast.literal_eval` su 2,8 milioni di righe: per contare i *tipi* basta una
   regex sul testo, che e' due ordini di grandezza piu' veloce e da' lo stesso
   conteggio. `io_events.parse_qualifiers` resta l'unico parser quando servono
   anche i *valori*.

LA GIORNATA NON C'E'
--------------------
Nessun CSV e `matches.json` contengono il numero di giornata. `matches.json` e'
ordinato a blocchi di dieci, ma l'ordine **non e' affidabile in coda** (vedi
`indice_giornata`), quindi la giornata di calendario si dichiara **non
ricostruibile dalla fonte** e al suo posto si usa l'indice cronologico di
squadra — la stessa grandezza che le Fasi 2-6 chiamano `team_match_idx`.
E' un fatto che il Blocco P1 deve conoscere prima di scegliere il bersaglio,
perche' quel bersaglio e' definito "alla giornata g".
"""

from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
import pandas as pd

from . import config

# --------------------------------------------------------------------------
# Percorsi della cache. Attraversano le stagioni, quindi stanno nella cartella
# di campionato e non dentro nessuna cartella di stagione (`config.py`).
# --------------------------------------------------------------------------
_DIR = config.processed_league_dir()
CACHE = {
    "file": _DIR / "blocco0_file.parquet",
    "colonne": _DIR / "blocco0_colonne.parquet",
    "eventi": _DIR / "blocco0_tipi_evento.parquet",
    "qualifier": _DIR / "blocco0_qualifier.parquet",
    "giocatori": _DIR / "blocco0_giocatori.parquet",
}

# `{'type': 'StandingSave'}` / `{'type': 'Length', 'value': '15.9'}`.
_RE_QUALIFIER = re.compile(r"'type':\s*'([A-Za-z0-9_]+)'")

MAPPING_DIR = config.DATA / "mapping"


# --------------------------------------------------------------------------
# 0.1 — scansione dei file
# --------------------------------------------------------------------------

def _scansiona_file(path: Path, stagione: str) -> dict:
    """Misure di un singolo CSV partita. Legge **tutte** le colonne."""
    df = pd.read_csv(path, low_memory=False)

    # Conteggi per colonna. TRE grandezze, non una, e servono tutte e tre:
    #
    #   presenza nel file  -> `isOwnGoal` manca dal file quando non ci sono
    #                         autogol (trappola 1);
    #   non nulli          -> la misura ingenua, e da sola e' fuorviante;
    #   non falsi          -> la misura che serve. Lo scraper del fork scrive
    #                         il literal `False` dove il campo Opta e' assente,
    #                         quindi `cardType` risulta "non nulla al 100%" pur
    #                         essendo valorizzata solo sui cartellini. Contare
    #                         `notna()` e chiamarlo "copertura" direbbe il
    #                         contrario del vero su 200 colonne su 259.
    #
    # Per una booleana genuina (`isShot`) i non falsi sono i tiri, che e'
    # esattamente la lettura utile; per una stringa e' il numero di valori veri.
    non_nulli, non_falsi, dtipi = {}, {}, {}
    for c in df.columns:
        col = df[c]
        non_nulli[c] = int(col.notna().sum())
        non_falsi[c] = int((col.notna() & (col != False)).sum())  # noqa: E712
        dtipi[c] = str(col.dtype)

    tipi = (df.groupby(["type", "outcomeType"], dropna=False).size()
            if "type" in df.columns else pd.Series(dtype=int))

    qual = Counter()
    if "qualifiers" in df.columns:
        for s in df["qualifiers"].astype(str).to_numpy():
            qual.update(_RE_QUALIFIER.findall(s))

    giocatori = pd.DataFrame(columns=["playerId", "playerName", "teamId"])
    if {"playerId", "playerName", "teamId"} <= set(df.columns):
        giocatori = (df.loc[df["playerId"].notna(),
                            ["playerId", "playerName", "teamId"]]
                     .groupby(["playerId", "playerName", "teamId"], dropna=False)
                     .size().rename("n_eventi").reset_index())

    date = pd.to_datetime(df["startDate"], errors="coerce").dropna()
    teams = sorted(df["teamId"].dropna().unique().tolist()) if "teamId" in df else []

    return {
        "riga": {
            "stagione": stagione,
            "matchId": int(path.stem),
            "byte": path.stat().st_size,
            "n_eventi": int(len(df)),
            "n_colonne": int(df.shape[1]),
            "data": date.iloc[0] if len(date) else pd.NaT,
            "maxMinute": float(df["maxMinute"].max()) if "maxMinute" in df else np.nan,
            "ultimo_expanded": (float(df["expandedMinute"].max())
                                if "expandedMinute" in df else np.nan),
            "teamId_casa": (int(df.loc[df["h_a"] == "h", "teamId"].iloc[0])
                            if "h_a" in df and (df["h_a"] == "h").any() else -1),
            "teamId_ospite": (int(df.loc[df["h_a"] == "a", "teamId"].iloc[0])
                              if "h_a" in df and (df["h_a"] == "a").any() else -1),
            "n_teamId": len(teams),
            # Chiave unica dichiarata dal repository: si verifica, non si assume.
            "dup_chiave": (int(df.duplicated(["matchId", "teamId", "eventId"]).sum())
                           if {"matchId", "teamId", "eventId"} <= set(df.columns)
                           else -1),
            "dup_id": (int(df.duplicated(["id"]).sum())
                       if "id" in df.columns else -1),
        },
        "colonne": non_nulli,
        "colonne_non_falsi": non_falsi,
        "colonne_dtype": dtipi,
        "tipi": tipi,
        "qualifier": qual,
        "giocatori": giocatori,
    }


def scansione(force: bool = False, stagioni: tuple[str, ...] | None = None
              ) -> dict[str, pd.DataFrame]:
    """Scansione completa delle cinque stagioni, con cache su Parquet.

    Idempotente: senza `force` rilegge dalla cache. La scansione da zero costa
    ~10 minuti perche' apre 4,8 GB di CSV con tutte le colonne.
    """
    if not force and all(p.exists() for p in CACHE.values()):
        return {k: pd.read_parquet(p) for k, p in CACHE.items()}

    stagioni = stagioni or config.SEASONS_STORICHE

    righe: list[dict] = []
    col_non_nulli: dict[tuple[str, str], int] = defaultdict(int)
    col_non_falsi: dict[tuple[str, str], int] = defaultdict(int)
    col_file: dict[tuple[str, str], int] = defaultdict(int)
    col_righe: dict[tuple[str, str], int] = defaultdict(int)
    col_dtype: dict[tuple[str, str], set] = defaultdict(set)
    tipi: dict[tuple[str, str, str], int] = defaultdict(int)
    qual: dict[tuple[str, str], int] = defaultdict(int)
    gioc: list[pd.DataFrame] = []

    for stagione in stagioni:
        d = config.raw_dir("whoscored", season=stagione) / "events"
        files = sorted(d.glob("*.csv"))
        if not files:
            raise FileNotFoundError(f"nessun CSV in {d}")
        for f in files:
            r = _scansiona_file(f, stagione)
            righe.append(r["riga"])
            n = r["riga"]["n_eventi"]
            for c, nn in r["colonne"].items():
                col_non_nulli[(stagione, c)] += nn
                col_non_falsi[(stagione, c)] += r["colonne_non_falsi"][c]
                col_file[(stagione, c)] += 1
                col_righe[(stagione, c)] += n
                col_dtype[(stagione, c)].add(r["colonne_dtype"][c])
            for (t, o), k in r["tipi"].items():
                tipi[(stagione, str(t), str(o))] += int(k)
            for q, k in r["qualifier"].items():
                qual[(stagione, q)] += int(k)
            g = r["giocatori"]
            if len(g):
                g = g.copy()
                g["stagione"] = stagione
                gioc.append(g)

    file_df = pd.DataFrame(righe)

    n_file = file_df.groupby("stagione").size().to_dict()
    colonne_df = pd.DataFrame(
        [{"stagione": s, "colonna": c,
          "file_con_colonna": col_file[(s, c)],
          "file_totali": n_file[s],
          "righe_coperte": col_righe[(s, c)],
          "non_nulli": col_non_nulli[(s, c)],
          "non_falsi": col_non_falsi[(s, c)],
          "dtype": "|".join(sorted(col_dtype[(s, c)]))}
         for (s, c) in sorted(col_file)]
    )
    colonne_df["quota_file"] = colonne_df["file_con_colonna"] / colonne_df["file_totali"]
    colonne_df["quota_non_nulli"] = np.where(
        colonne_df["righe_coperte"] > 0,
        colonne_df["non_nulli"] / colonne_df["righe_coperte"], np.nan)
    colonne_df["quota_valorizzata"] = np.where(
        colonne_df["righe_coperte"] > 0,
        colonne_df["non_falsi"] / colonne_df["righe_coperte"], np.nan)

    eventi_df = pd.DataFrame(
        [{"stagione": s, "type": t, "outcomeType": o, "n": k}
         for (s, t, o), k in sorted(tipi.items())])
    qual_df = pd.DataFrame(
        [{"stagione": s, "qualifier": q, "n": k}
         for (s, q), k in sorted(qual.items())])

    gioc_df = (pd.concat(gioc, ignore_index=True)
               .groupby(["stagione", "playerId", "playerName", "teamId"],
                        as_index=False)["n_eventi"].sum())
    gioc_df["playerId"] = gioc_df["playerId"].astype("int64")
    gioc_df["teamId"] = gioc_df["teamId"].astype("int64")

    out = {"file": file_df, "colonne": colonne_df, "eventi": eventi_df,
           "qualifier": qual_df, "giocatori": gioc_df}
    for k, df in out.items():
        df.to_parquet(CACHE[k], index=False)
    return out


# --------------------------------------------------------------------------
# 0.1 — copertura
# --------------------------------------------------------------------------

def calendario(stagione: str) -> pd.DataFrame:
    """Il calendario dichiarato da `matches.json`, con `matchId` estratto dall'URL."""
    p = config.raw_dir("whoscored", season=stagione) / "matches.json"
    raw = json.loads(p.read_text(encoding="utf-8"))
    return pd.DataFrame([
        {"stagione": stagione,
         "ordine": i,
         "matchId": int(m["url"].split("/")[2]),
         "casa": m["home"], "ospite": m["away"],
         "risultato": m.get("score", ""),
         "data_testo": m.get("date", "")}
        for i, m in enumerate(raw)
    ])


def copertura(file_df: pd.DataFrame) -> pd.DataFrame:
    """Calendario contro file su disco, stagione per stagione.

    I denominatori si prendono dal calendario, **mai assunti a 380**: il
    2022-23 ne dichiara 381 (c'e' il playout, che e' una partita vera).
    """
    righe = []
    for stagione in sorted(file_df["stagione"].unique()):
        cal = calendario(stagione)
        su_disco = set(file_df.loc[file_df["stagione"] == stagione, "matchId"])
        attesi = set(cal["matchId"])
        vuoti = file_df.loc[(file_df["stagione"] == stagione)
                            & (file_df["n_eventi"] == 0), "matchId"]
        righe.append({
            "stagione": stagione,
            "calendario": len(cal),
            "matchId_distinti_calendario": len(attesi),
            "file_su_disco": len(su_disco),
            "mancanti": len(attesi - su_disco),
            "su_disco_non_in_calendario": len(su_disco - attesi),
            "file_con_zero_eventi": int(len(vuoti)),
            "copertura": len(su_disco & attesi) / max(len(attesi), 1),
        })
    return pd.DataFrame(righe)


def partite_mancanti(file_df: pd.DataFrame) -> pd.DataFrame:
    """Le singole partite del calendario che non hanno un CSV."""
    out = []
    for stagione in sorted(file_df["stagione"].unique()):
        cal = calendario(stagione)
        su_disco = set(file_df.loc[file_df["stagione"] == stagione, "matchId"])
        out.append(cal[~cal["matchId"].isin(su_disco)])
    return pd.concat(out, ignore_index=True)


def perdita_per_squadra(file_df: pd.DataFrame) -> pd.DataFrame:
    """Quante partite perde ciascuna squadra, e quante ne ha in calendario.

    La perdita **non e' casuale rispetto alla squadra** (l'acquisizione lo
    aveva gia' segnalato per l'Atalanta): qui si ricalcola dai dati invece di
    riportarlo, perche' un denominatore per squadra sbagliato si propaga in
    ogni tasso per 90 delle fasi successive.
    """
    out = []
    for stagione in sorted(file_df["stagione"].unique()):
        cal = calendario(stagione)
        su_disco = set(file_df.loc[file_df["stagione"] == stagione, "matchId"])
        lunghe = pd.concat([
            cal[["matchId", "casa"]].rename(columns={"casa": "squadra"}),
            cal[["matchId", "ospite"]].rename(columns={"ospite": "squadra"}),
        ])
        lunghe["presente"] = lunghe["matchId"].isin(su_disco)
        g = (lunghe.groupby("squadra")
             .agg(calendario=("matchId", "size"), presenti=("presente", "sum"))
             .reset_index())
        g["mancanti"] = g["calendario"] - g["presenti"]
        g["stagione"] = stagione
        out.append(g)
    return pd.concat(out, ignore_index=True)[
        ["stagione", "squadra", "calendario", "presenti", "mancanti"]]


def indice_giornata(stagione: str) -> dict:
    """Accerta se `matches.json` sia ordinato per giornata. Non lo assume.

    Il test e': spezzando l'elenco in blocchi di dieci, un blocco che sia una
    giornata vera contiene **venti squadre distinte**. Dove non lo e', l'ordine
    non e' una giornata e non va usato come tale.
    """
    cal = calendario(stagione)
    blocchi, anomali = [], 0
    for i in range(0, len(cal), 10):
        b = cal.iloc[i:i + 10]
        squadre = pd.concat([b["casa"], b["ospite"]])
        ok = (len(b) == 10) and (squadre.nunique() == 20)
        anomali += (not ok)
        blocchi.append({"blocco": i // 10 + 1, "n_partite": len(b),
                        "squadre_distinte": int(squadre.nunique()), "coerente": ok})

    # L'ipotesi alternativa: l'ordine e' cronologico. Si misura sulle date vere
    # (`startDate` dei CSV), non su quelle testuali del JSON, che sono vuote su
    # parecchie voci.
    date = (pd.read_parquet(CACHE["file"])
            .query("stagione == @stagione")[["matchId", "data"]]
            if CACHE["file"].exists() else pd.DataFrame(columns=["matchId", "data"]))
    d = cal.merge(date, on="matchId", how="left")["data"]
    passi = d.diff().dt.days.dropna()
    return {
        "stagione": stagione,
        "n_blocchi": len(blocchi),
        "blocchi_anomali": anomali,
        "date_vuote": int((cal["data_testo"].astype(str).str.strip() == "").sum()),
        "quota_ordine_cronologico": float((passi >= 0).mean()) if len(passi) else float("nan"),
        "dettaglio": pd.DataFrame(blocchi),
    }


def presenza_qualifier_per_partita(qualifiers: tuple[str, ...],
                                   stagione: str) -> pd.DataFrame:
    """Occorrenze dei qualifier indicati, partita per partita, in una stagione.

    Serve a distinguere due sparizioni che il totale di stagione confonde:
    un'etichetta che cala **ovunque** (criterio che si sposta) e una che sta al
    livello vecchio in poche partite e crolla in tutte le altre (due versioni
    del dizionario della fonte). La seconda e' cio' che si osserva.
    """
    rx = re.compile(r"'type':\s*'(" + "|".join(qualifiers) + r")'")
    d = config.raw_dir("whoscored", season=stagione) / "events"
    righe = []
    for f in sorted(d.glob("*.csv")):
        col = pd.read_csv(f, usecols=["qualifiers"], low_memory=False)
        c = dict.fromkeys(qualifiers, 0)
        for s in col["qualifiers"].astype(str).to_numpy():
            for m in rx.findall(s):
                c[m] += 1
        righe.append({"stagione": stagione, "matchId": int(f.stem),
                      "n_eventi": len(col), **c})
    return pd.DataFrame(righe)


# --------------------------------------------------------------------------
# 0.1 — stabilita' dello schema fra stagioni
# --------------------------------------------------------------------------

def stabilita_schema(colonne_df: pd.DataFrame) -> pd.DataFrame:
    """Una riga per colonna: in quante stagioni compare e con che copertura.

    Serve a separare i tre casi che un confronto ingenuo confonde:
    colonna assente in una stagione, colonna presente ma mai valorizzata,
    colonna presente e valorizzata in modo diverso.
    """
    piv = colonne_df.pivot(index="colonna", columns="stagione", values="quota_file")
    # `quota_valorizzata`, non `quota_non_nulli`: la seconda conta come presente
    # il `False` che lo scraper scrive al posto del campo assente.
    piv_nn = colonne_df.pivot(index="colonna", columns="stagione",
                              values="quota_valorizzata")
    out = pd.DataFrame(index=piv.index)
    out["stagioni_con_colonna"] = piv.notna().sum(axis=1)
    out["quota_file_min"] = piv.min(axis=1)
    out["quota_file_max"] = piv.max(axis=1)
    out["quota_valorizzata_min"] = piv_nn.min(axis=1)
    out["quota_valorizzata_max"] = piv_nn.max(axis=1)
    out["escursione_valorizzata"] = (out["quota_valorizzata_max"]
                                     - out["quota_valorizzata_min"])
    return out.reset_index().sort_values(
        ["stagioni_con_colonna", "escursione_valorizzata"],
        ascending=[True, False])


def deriva_qualifier(qual_df: pd.DataFrame, file_df: pd.DataFrame,
                     min_totale: int = 500) -> pd.DataFrame:
    """Frequenza di ogni qualifier per evento, stagione per stagione.

    Normalizzata sugli eventi della stagione: i totali grezzi non sono
    confrontabili perche' le stagioni hanno un numero diverso di partite
    acquisite (374 contro 380).
    """
    ev = file_df.groupby("stagione")["n_eventi"].sum().rename("eventi")
    d = qual_df.merge(ev, on="stagione")
    d["per_evento"] = d["n"] / d["eventi"]
    piv = d.pivot(index="qualifier", columns="stagione", values="per_evento")
    tot = qual_df.groupby("qualifier")["n"].sum()
    piv = piv.loc[tot[tot >= min_totale].index.intersection(piv.index)]
    piv = piv.fillna(0.0)
    out = piv.copy()
    out["min"] = piv.min(axis=1)
    out["max"] = piv.max(axis=1)
    # Rapporto max/min: e' la scala su cui un qualifier "sparisce" si legge.
    out["rapporto"] = np.where(out["min"] > 0, out["max"] / out["min"], np.inf)
    return out.reset_index().sort_values("rapporto", ascending=False)


# --------------------------------------------------------------------------
# 0.2 — anagrafiche, cioe' il SOLO lato WhoScored della corrispondenza
# --------------------------------------------------------------------------

def registro_squadre(file_df: pd.DataFrame) -> pd.DataFrame:
    """`teamId` -> nome WhoScored, per stagione.

    I nomi non esistono nei CSV: si ricavano incrociando `matchId` + casa/
    trasferta con `matches.json`. E' l'unico modo, ed e' la trappola nota.
    """
    out = []
    for stagione in sorted(file_df["stagione"].unique()):
        cal = calendario(stagione).set_index("matchId")
        f = file_df[file_df["stagione"] == stagione]
        coppie = Counter()
        for r in f.itertuples(index=False):
            if r.matchId not in cal.index:
                continue
            riga = cal.loc[r.matchId]
            coppie[(r.teamId_casa, riga["casa"])] += 1
            coppie[(r.teamId_ospite, riga["ospite"])] += 1
        d = pd.DataFrame([{"teamId": t, "nome_whoscored": n, "n": k}
                          for (t, n), k in coppie.items()])
        # Voto di maggioranza: protegge da una singola riga mal accoppiata.
        d = d.sort_values("n").groupby("teamId", as_index=False).tail(1)
        d["stagione"] = stagione
        out.append(d[["stagione", "teamId", "nome_whoscored", "n"]])
    return (pd.concat(out, ignore_index=True)
            .rename(columns={"n": "partite"})
            .sort_values(["stagione", "nome_whoscored"]))


def registro_giocatori(gioc_df: pd.DataFrame,
                       squadre: pd.DataFrame) -> pd.DataFrame:
    """Anagrafica giocatori WhoScored per stagione, con squadre e volume.

    Un `playerId` puo' avere **piu' squadre nella stessa stagione** (mercato di
    gennaio) e **piu' grafie del nome**: entrambe le cose si conservano invece
    di risolverle, perche' sono esattamente i casi su cui l'aggancio ai voti
    fallira'.
    """
    nomi = (gioc_df.sort_values("n_eventi", ascending=False)
            .groupby(["stagione", "playerId"], as_index=False)
            .agg(nome_modale=("playerName", "first"),
                 n_grafie=("playerName", "nunique"),
                 n_eventi=("n_eventi", "sum"),
                 n_squadre=("teamId", "nunique")))
    sq = squadre.set_index(["stagione", "teamId"])["nome_whoscored"]
    princ = (gioc_df.sort_values("n_eventi", ascending=False)
             .groupby(["stagione", "playerId"], as_index=False)
             .agg(teamId_principale=("teamId", "first")))
    out = nomi.merge(princ, on=["stagione", "playerId"])
    out["squadra_principale"] = [
        sq.get((s, t), pd.NA)
        for s, t in zip(out["stagione"], out["teamId_principale"])
    ]
    return out.sort_values(["stagione", "squadra_principale", "nome_modale"])


def anomalie_identita(reg: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """I casi che il prompt chiede di gestire esplicitamente (0.2).

    Si **elencano**, non si risolvono: la risoluzione richiede il lato voti,
    che non esiste.
    """
    omonimi = (reg.groupby(["stagione", "nome_modale"])
               .agg(n_playerId=("playerId", "nunique"))
               .reset_index().query("n_playerId > 1"))
    multisquadra = reg.query("n_squadre > 1")
    multigrafia = reg.query("n_grafie > 1")
    un_nome = reg[~reg["nome_modale"].astype(str).str.contains(r"\s")]
    non_ascii = reg[reg["nome_modale"].astype(str)
                    .str.contains(r"[^\x00-\x7F']", regex=True, na=False)]
    return {"omonimi": omonimi, "multisquadra": multisquadra,
            "multigrafia": multigrafia, "nome_singolo": un_nome,
            "nome_non_ascii": non_ascii}


# --------------------------------------------------------------------------
# 0.4 — la regola dell'80', per la meta' che i dati in casa consentono
# --------------------------------------------------------------------------

def esposizione_regola_80(soglia: float = 80.0) -> pd.DataFrame:
    """Quante righe giocatore-partita la regola dell'80' marcherebbe s.v.

    **Non e' il tasso d'errore richiesto da §1.2.** Il tasso d'errore ha due
    versi e tutti e due hanno bisogno dell's.v. **osservato**, che sta nei voti
    e non e' sul disco. Questo e' il solo denominatore: quanta massa la regola
    sposta. Serve a dimensionare la domanda, non a rispondere.

    Gira sulla stagione di `config.SEASON` (2025-2026), l'unica per cui la
    catena minuti del repository e' costruita.
    """
    from . import io_events, minutes

    lineup = io_events.load_lineup_events()
    events = io_events.load_events()
    mins = minutes.minutes_played(lineup, events)

    giocato = mins[mins["minutes"].notna() & (mins["start_min"].notna())].copy()
    giocato["subentrato"] = ~giocato["is_starter"]
    giocato["sv_proiettato"] = (giocato["subentrato"]
                                & (giocato["start_min"] >= soglia))

    tot = len(giocato)
    return pd.DataFrame([{
        "stagione": config.SEASON,
        "soglia_expanded": soglia,
        "righe_scese_in_campo": tot,
        "titolari": int(giocato["is_starter"].sum()),
        "subentrati": int(giocato["subentrato"].sum()),
        "sv_proiettato": int(giocato["sv_proiettato"].sum()),
        "quota_sv_proiettato": giocato["sv_proiettato"].mean(),
        "quota_sv_fra_subentrati": (giocato.loc[giocato["subentrato"],
                                                "sv_proiettato"].mean()),
        "minuti_mediani_sv": giocato.loc[giocato["sv_proiettato"],
                                         "minutes"].median(),
        "minuti_max_sv": giocato.loc[giocato["sv_proiettato"], "minutes"].max(),
        # La soglia e' su `expandedMinute` e la partita dura 94-99': chi entra
        # all'80' espanso puo' giocare parecchio piu' di dieci minuti.
        "sv_con_almeno_15_min": int((giocato["sv_proiettato"]
                                     & (giocato["minutes"] >= 15)).sum()),
        # Il verso d'errore che la regola non copre affatto: il titolare che
        # esce presto. Non e' uno dei due che §1.2 chiede di misurare.
        "titolari_usciti_entro_10": int((giocato["is_starter"]
                                         & (giocato["end_min"] < 10)).sum()),
        "titolari_usciti_entro_20": int((giocato["is_starter"]
                                         & (giocato["end_min"] < 20)).sum()),
    }])


def ingressi_per_minuto(passo: int = 5) -> pd.DataFrame:
    """Distribuzione del minuto d'ingresso dei subentrati, a scaglioni.

    Mostra quanto la soglia 80' sia sensibile alla sua posizione: se la massa
    e' concentrata proprio li' intorno, spostarla di due minuti cambia molto.
    """
    from . import io_events, minutes

    mins = minutes.minutes_played(io_events.load_lineup_events(),
                                  io_events.load_events())
    sub = mins[(~mins["is_starter"]) & mins["start_min"].notna()].copy()
    bordi = list(range(0, 105 + passo, passo))
    sub["scaglione"] = pd.cut(sub["start_min"], bins=bordi, right=False)
    g = sub.groupby("scaglione", observed=True).size().rename("n").reset_index()
    g["quota"] = g["n"] / g["n"].sum()
    g["scaglione"] = g["scaglione"].astype(str)
    return g


# --------------------------------------------------------------------------
# Lo stato della seconda fonte: si accerta, non si assume
# --------------------------------------------------------------------------

# Percorsi in cui i voti starebbero se esistessero, secondo la tassonomia
# gia' fissata in `config.py`. Sono elencati per poter dire *dove si e'
# guardato*, che e' cio' che rende l'accertamento verificabile.
PERCORSI_ATTESI_VOTI = (
    "data/raw/fantacalcio/ITA-serie-a/<stagione>/",
    "data/external/voti/",
    "data/external/quote/",
)


def stato_fonte_voti() -> pd.DataFrame:
    """Accerta se i voti fantacalcio e le quotazioni siano sul disco.

    Il prompt del Blocco 0 chiede la ricognizione di **due** fonti. Questa
    funzione e' la ragione per cui il report puo' affermare che la seconda non
    c'e' senza che sia un'impressione: elenca i percorsi guardati e cosa ci si
    e' trovato.
    """
    righe = []
    for rel in PERCORSI_ATTESI_VOTI:
        for stagione in config.SEASONS_STORICHE:
            p = config.ROOT / rel.replace("<stagione>", stagione)
            if "<stagione>" not in rel and stagione != config.SEASONS_STORICHE[0]:
                continue
            n = len(list(p.rglob("*"))) if p.exists() else 0
            righe.append({
                "percorso": str(p.relative_to(config.ROOT)).replace("\\", "/"),
                "esiste": p.exists(),
                "file_presenti": n,
            })
    return pd.DataFrame(righe).drop_duplicates("percorso")


def scrivi_mapping(squadre: pd.DataFrame, giocatori: pd.DataFrame,
                   anomalie: dict[str, pd.DataFrame]) -> list[Path]:
    """Scrive in `data/mapping/` il **lato WhoScored** delle corrispondenze.

    Non scrive nessuna tabella di corrispondenza vera: una corrispondenza ha
    due lati e il secondo non esiste. Un file con la colonna dei voti vuota
    sarebbe un segnaposto — cioe' esattamente cio' che la regola di condotta 1
    vieta — e verrebbe letto da qualcuno come "aggancio fallito" invece che
    "aggancio mai tentato".
    """
    MAPPING_DIR.mkdir(parents=True, exist_ok=True)
    scritti = []
    for nome, df in [("whoscored_squadre", squadre),
                     ("whoscored_giocatori", giocatori)]:
        p = MAPPING_DIR / f"{nome}.csv"
        df.to_csv(p, index=False, encoding="utf-8")
        scritti.append(p)
    for nome, df in anomalie.items():
        p = MAPPING_DIR / f"whoscored_anomalie_{nome}.csv"
        df.to_csv(p, index=False, encoding="utf-8")
        scritti.append(p)
    return scritti
