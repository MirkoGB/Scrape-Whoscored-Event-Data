# -*- coding: utf-8 -*-
"""Dai grezzi di `fantacalcio.it` alla tabella giocatore-partita dei voti.

Sta in `sot/` e non in `acquisition/` per il criterio dichiarato in
`acquisition/__init__.py`: qui non si scarica niente. Questo modulo legge le
pagine gia' su disco, le passa al parser della fonte
(`acquisition.fantacalcio.pagina`) e ne fa una tabella.

## Cosa contiene la tabella, e cosa deliberatamente non contiene

Una riga per **giocatore sceso in campo per partita**, con tutte e tre le scale
di voto affiancate. Non c'e' una riga per chi e' rimasto in panchina: la fonte
non lo elenca, e inventare righe a zero significherebbe dichiarare un'assenza
che non abbiamo osservato.

**Non c'e' il fantavoto della lega dell'utente**, e non e' una dimenticanza. Il
`FV` della fonte e' calcolato con il barema della fonte, che differisce da
`docs/regole_fantacalcio.md` §1.1 su un punto misurabile: **la porta inviolata
non ci sta**. Il +1 al portiere imbattuto e' un'opzione di lega che la fonte non
applica, e si vede nella riconciliazione — che torna esatta *senza* di esso.
Chi volesse il fantavoto di lega deve ricalcolarlo dalle colonne di bonus, e la
porta inviolata va **derivata** (`ruolo == "p"` e `gol_subiti == 0`), non letta:
e' fra le 72 colonne che la Fase 7 ha trovato mai valorizzate anche in
WhoScored. Ricalcolarlo qui vorrebbe dire fissare una regola di lega dentro lo
strato dei dati, e le decisioni di lega sono ancora aperte (§0 delle regole).

## Le trappole di questa fonte

Le cinque strutturali stanno nella docstring di `acquisition/fantacalcio/pagina.py`
e non si ripetono. Quelle che si vedono solo a tabella costruita:

- **Venti righe per giornata sono allenatori** (`allenatore == True`,
  `giocatore_id` nullo). Prendono un voto come i giocatori. Vanno filtrate da
  qualunque conteggio per ruolo, o ogni media di squadra ha dentro un pagellista
  che giudica il tecnico.
- **`giocatore_id` e' stabile fra stagioni** (viene dall'URL del profilo) ed e'
  la chiave con cui ricucire l'identita' senza passare dai nomi. Sui nomi
  passare non si puo': la fonte usa forme abbreviate e omonimie disambiguate a
  mano (`Ivanovic M.`).
- **`codice_sv` non e' un nullo.** `55` e `56` sono due codici diversi della
  fonte, e il secondo compare **solo** nella colonna del Voto Statistico. Sono
  conservati; il voto corrispondente e' nullo, come dev'essere.
- **La presenza fantacalcistica non e' il numero di righe.** E' il numero di
  righe con `voto_redazione` non nullo, che e' la grandezza che
  `docs/regole_fantacalcio.md` §1.2 dichiara come bersaglio del modello.
"""

from __future__ import annotations

import pandas as pd

from acquisition.fantacalcio import pagina as P
from acquisition.fantacalcio import target as T
from sot import config

# La cache attraversa le stagioni, quindi non appartiene a nessuna: stessa
# ragione per cui ci stanno i Parquet multi-stagione della Fase 7.
VOTI_PARQUET = config.processed_league_dir() / "fantacalcio_voti.parquet"
PARTITE_PARQUET = config.processed_league_dir() / "fantacalcio_partite.parquet"

# Gli stessi dati in CSV, accanto al Parquet. Il Parquet resta la forma che i
# moduli leggono — conserva i tipi, e `giocatore_id` nullo per gli allenatori
# resta `Int64` invece di diventare `1234.0` — mentre il CSV serve ad aprire la
# tabella fuori di qui. Sono la stessa tabella scritta due volte, non due
# tabelle: se un giorno divergessero, quella giusta e' il Parquet.
VOTI_CSV = config.processed_league_dir() / "fantacalcio_voti.csv"
PARTITE_CSV = config.processed_league_dir() / "fantacalcio_partite.csv"

# Le otto voci di bonus della fonte, nell'ordine in cui il parser le emette.
COLONNE_BONUS = [campo for _, campo, _ in P.BONUS]

ORDINE = [
    "stagione", "giornata", "data", "partita_id",
    "squadra_id", "squadra", "avversario_id", "avversario", "casa",
    "giocatore_id", "giocatore", "ruolo", "allenatore",
    "voto_redazione", "fantavoto_redazione", "codice_sv_redazione",
    "voto_statistico", "fantavoto_statistico", "codice_sv_statistico",
    "voto_italia", "fantavoto_italia", "codice_sv_italia",
    *COLONNE_BONUS,
    "ammonizione", "espulsione", "subentrato", "sostituito",
    "bonus_fonte", "pagina",
]


def _pagine(league: str, seasons) -> list[tuple[T.TargetVoti, int]]:
    fuori = []
    for t in T.targets(league, seasons):
        for g in range(1, T.N_GIORNATE + 1):
            if t.percorso(g).is_file():
                fuori.append((t, g))
    return fuori


def costruisci(league: str = None, seasons=None, verbose: bool = True):
    """Legge tutte le pagine su disco e restituisce `(voti, partite)`.

    Non tocca la rete e non scrive: chi vuole i Parquet chiama `run()`.
    """
    league = config.LEAGUE if league is None else league
    righe, partite = [], []
    for t, g in _pagine(league, seasons):
        percorso = t.percorso(g)
        letto = P.analizza(P.leggi(percorso), t.season, g)
        relativo = str(percorso.relative_to(config.ROOT)).replace("\\", "/")
        for r in letto["righe"]:
            r["pagina"] = relativo
            righe.append(r)
        for p in letto["partite"]:
            partite.append({"stagione": t.season, "giornata": g, **p})
        if verbose and g == T.N_GIORNATE:
            print(f"  {t.season}: {sum(1 for x in righe if x['stagione'] == t.season)} righe")

    if not righe:
        raise FileNotFoundError(
            f"nessuna pagina di voti sotto {config.raw_dir(T.FONTE, league, config.SEASON).parent}. "
            "Serve prima `python -m acquisition.fantacalcio.scrape_voti`"
        )

    voti = pd.DataFrame(righe)
    voti["data"] = pd.to_datetime(voti["data"])
    # Il totale di bonus **della fonte**, per differenza. E' l'unica grandezza
    # derivata che questo modulo si permette, ed e' derivata da due colonne
    # osservate: non contiene nessuna regola di lega.
    voti["bonus_fonte"] = (voti["fantavoto_redazione"] - voti["voto_redazione"]).round(2)
    for col in ("giocatore_id", "codice_sv_redazione",
                "codice_sv_statistico", "codice_sv_italia"):
        voti[col] = voti[col].astype("Int64")
    voti = voti[ORDINE].sort_values(
        ["stagione", "giornata", "squadra", "ruolo", "giocatore"]
    ).reset_index(drop=True)

    part = pd.DataFrame(partite)
    part["data"] = pd.to_datetime(part["data"])
    part = part.sort_values(["stagione", "giornata", "data", "casa"]).reset_index(drop=True)
    return voti, part


# --------------------------------------------------------------------------
# Verifiche
#
# Sono controlli sui dati, non sul codice, e per questo stanno qui e girano a
# ogni costruzione invece di vivere solo nei test: i test provano il parser su
# una pagina sintetica, queste provano le 190 pagine vere.
# --------------------------------------------------------------------------

def riconciliazione(voti: pd.DataFrame, scala: str = "redazione") -> pd.DataFrame:
    """`FV - V` contro il barema della fonte, riga per riga.

    E' la verifica piu' forte che questa acquisizione permette, perche' **non
    passa da nessun modello**: la fonte pubblica voto e fantavoto e pubblica
    separatamente le voci di bonus, quindi le due strade devono chiudere. Un
    residuo diverso da zero significa una di tre cose, tutte da guardare: una
    voce di bonus che non leggiamo (e' cosi' che sono emersi i cartellini, che
    non sono una colonna ma una classe CSS), un barema cambiato fra stagioni,
    oppure un errore di lettura.
    """
    v = voti[f"voto_{scala}"]
    fv = voti[f"fantavoto_{scala}"]
    atteso = sum(P.BAREME_FONTE[c] * voti[c] for c in COLONNE_BONUS)
    atteso = (atteso
              + P.BAREME_FONTE["ammonizione"] * voti["ammonizione"].astype(int)
              + P.BAREME_FONTE["espulsione"] * voti["espulsione"].astype(int))
    residuo = (fv - v - atteso).round(2)
    # **Un residuo nullo si filtra da solo, ed e' il modo in cui questa verifica
    # puo' mentire.** La prima versione teneva solo `residuo != 0` fra i non
    # nulli: le righe in cui il fantavoto non era stato letto sparivano dal
    # numeratore *e* dal denominatore, e il rapporto usciva 100% proprio perche'
    # erano rotte. Una riga con il voto e senza fantavoto e' un difetto di
    # lettura, non una riga da saltare, e qui entra fra i fuori registro.
    non_letta = v.notna() & fv.isna()
    return voti.assign(residuo=residuo).loc[non_letta | (residuo.notna() & (residuo != 0))]


def valutabili(voti: pd.DataFrame, scala: str = "redazione") -> pd.Series:
    """Le righe su cui la riconciliazione ha qualcosa da dire: quelle con un voto.

    E' il denominatore giusto, e va preso da `voto` e non da `voto & fantavoto`:
    prendere l'intersezione renderebbe il rapporto insensibile proprio al difetto
    che deve trovare.
    """
    return voti[f"voto_{scala}"].notna()


def copertura(voti: pd.DataFrame, partite: pd.DataFrame) -> pd.DataFrame:
    """Giornate, partite e righe per stagione. I denominatori si contano, mai
    si assumono a 38 x 10: e' la lezione dell'acquisizione WhoScored, dove
    l'Atalanta aveva 35 partite e non 38 e assumere il denominatore avrebbe
    nascosto la perdita."""
    g = voti.groupby("stagione")
    p = partite.groupby("stagione")
    fuori = pd.DataFrame({
        "giornate": g["giornata"].nunique(),
        "partite": p["partita_id"].nunique(),
        "squadre": g["squadra_id"].nunique(),
        "righe": g.size(),
        "righe_giocatore": g.apply(lambda d: int((~d["allenatore"]).sum()), include_groups=False),
        "righe_allenatore": g["allenatore"].sum(),
    })
    fuori["righe_per_partita"] = (fuori["righe_giocatore"] / fuori["partite"]).round(1)
    return fuori.reset_index()


def sintesi_stagioni(voti: pd.DataFrame, scala: str = "redazione") -> pd.DataFrame:
    """Le grandezze che `docs/regole_fantacalcio.md` §5 chiede per stagione.

    E' **descrittiva**: dice se il livello dei voti si e' mosso, non se il
    criterio editoriale e' cambiato. Le due cose non coincidono e la seconda non
    e' osservabile dall'esterno (§8 della ricognizione di fattibilita'). Il test
    formale di rottura — quello che la Fase 7 ha fatto sui tiri, con il punto di
    rottura cercato e non assunto — e' un blocco a se': qui si mette il numero
    accanto alla stagione e basta.
    """
    g = voti.loc[~voti["allenatore"]].copy()
    voto = g[f"voto_{scala}"]
    per = g.groupby("stagione")
    fuori = pd.DataFrame({
        "righe": per.size(),
        "con_voto": per.apply(lambda d: int(d[f"voto_{scala}"].notna().sum()),
                              include_groups=False),
        "voto_medio": per.apply(lambda d: d[f"voto_{scala}"].mean(), include_groups=False),
        "voto_sd": per.apply(lambda d: d[f"voto_{scala}"].std(), include_groups=False),
        "fantavoto_medio": per.apply(lambda d: d[f"fantavoto_{scala}"].mean(),
                                     include_groups=False),
        "gol": per["gol_segnati"].sum() + per["rigori_segnati"].sum(),
        "assist": per["assist"].sum(),
        "ammonizioni": per["ammonizione"].sum(),
        "espulsioni": per["espulsione"].sum(),
    })
    fuori["quota_sv"] = (1 - fuori["con_voto"] / fuori["righe"]).round(4)
    del voto
    return fuori.round(4).reset_index()


def per_ruolo(voti: pd.DataFrame, scala: str = "redazione") -> pd.DataFrame:
    g = voti.loc[~voti["allenatore"]]
    per = g.groupby(["stagione", "ruolo"])
    fuori = pd.DataFrame({
        "righe": per.size(),
        "con_voto": per.apply(lambda d: int(d[f"voto_{scala}"].notna().sum()),
                              include_groups=False),
        "voto_medio": per.apply(lambda d: d[f"voto_{scala}"].mean(), include_groups=False),
        "fantavoto_medio": per.apply(lambda d: d[f"fantavoto_{scala}"].mean(),
                                     include_groups=False),
    })
    fuori["quota_sv"] = (1 - fuori["con_voto"] / fuori["righe"]).round(4)
    return fuori.round(4).reset_index()


def sv_e_subentri(voti: pd.DataFrame, scala: str = "redazione") -> pd.DataFrame:
    """L's.v. **osservato** incrociato con l'ingresso a partita in corso.

    E' la tabella che serve a §1.2 delle regole: la fonte dichiara che una
    soglia di minuti non esiste, quindi l's.v. non e' una funzione dei minuti e
    la regola dell'80' e' un'assunzione di modello, non una lettura. Qui si
    misura solo **quanto** l's.v. sia concentrato sui subentrati, che e' un
    fatto; il confronto con i minuti WhoScored e' un blocco successivo e vive
    sulla sola 2025-26, l'unica stagione con entrambe le fonti.
    """
    g = voti.loc[~voti["allenatore"]].copy()
    g["sv"] = g[f"voto_{scala}"].isna()
    g["ingresso"] = g["subentrato"].map({True: "subentrato", False: "dal primo minuto"})
    per = g.groupby(["stagione", "ingresso"])
    fuori = pd.DataFrame({"righe": per.size(), "sv": per["sv"].sum()})
    fuori["quota_sv"] = (fuori["sv"] / fuori["righe"]).round(4)
    return fuori.reset_index()


def run(league: str = None, seasons=None, verbose: bool = True) -> dict:
    """Costruisce, verifica e scrive le due tabelle in Parquet e in CSV.

    Non tocca la rete. La data e' scritta come `AAAA-MM-GG` e non con l'ora:
    dalla fonte arriva senza orario, e un `00:00:00` in coda direbbe una
    precisione che non c'e'.
    """
    voti, partite = costruisci(league, seasons, verbose=verbose)
    fuori = riconciliazione(voti)
    n = int(valutabili(voti).sum())
    if verbose:
        print(f"\nriconciliazione FV = V + bonus: {n - len(fuori)}/{n} esatte")
    voti.to_parquet(VOTI_PARQUET, index=False)
    partite.to_parquet(PARTITE_PARQUET, index=False)
    voti.to_csv(VOTI_CSV, index=False, date_format="%Y-%m-%d")
    partite.to_csv(PARTITE_CSV, index=False, date_format="%Y-%m-%d")
    return {"voti": voti, "partite": partite, "residui": fuori}


def carica() -> pd.DataFrame:
    if not VOTI_PARQUET.is_file():
        raise FileNotFoundError(
            f"{VOTI_PARQUET} non c'e': serve prima `scripts/run_voti_fantacalcio.py`"
        )
    return pd.read_parquet(VOTI_PARQUET)
