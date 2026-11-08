# -*- coding: utf-8 -*-
"""Fase 13 / M1. Metriche avanzate da dati evento, per squadra-partita.

Chieste dall'utente il 2026-08-14 insieme all'apertura di G2: i **tocchi per
zona** (campo in cinque zone, aree di rigore incluse) e la famiglia dei
**passaggi progressivi**.

**Non stima niente.** Conta e misura, come `perimetro.py` (R0) e `tentativi.py`
(V0). Il test predittivo di queste colonne e' un altro blocco, e va disegnato
con la potenza dichiarata **prima** — i predittori da dati evento sono gia'
stati scartati tre volte (Fase 2, 6D, V3) e un quarto negativo cieco non
aggiungerebbe niente.

Perche' un modulo nuovo invece di allargare `features.py`
--------------------------------------------------------
`features.py` produce i predittori delle Fasi 1-6 ed e' congelato dai numeri
pubblicati: `possession`, `field_tilt`, `ppda`, `box_touches`. Aggiungere
colonne li' cambierebbe la forma di una tabella che quattro fasi rileggono.
**La geometria pero' NON si duplica**: le costanti si importano da `features`,
perche' l'area di rigore del progetto e' una sola — stessa ragione per cui la
definizione di tiro in porta sta solo in `shots.py`.

Le due assunzioni dichiarate
----------------------------
1. **Le coordinate Opta non sono metri.** La conversione poggia sul campo
   regolamentare 105 x 68 m gia' assunto da `features.py`, quindi una unita' di
   `x` vale 1,05 m e una di `y` 0,68 m. **Gli stadi veri variano** (la norma FIFA
   ammette 100-110 x 64-75): la soglia dei 10 m e' quindi una soglia *nominale*,
   e va scritta accanto al numero invece che in fondo (vincolo 5).
2. **"Riuscito" e' `outcomeType`, non `passAccurate`.** Misurato sulla 2025-26:
   `passAccurate=True` implica **sempre** `Successful` (zero contraddizioni su
   273.027), ma **l'8,3% dei passaggi non ha nessuno dei due flag** e fra questi
   17.440 sono riusciti. I non marcati sono piu' lunghi (22,2 m contro 18,0),
   coerente col fatto che Opta li classifichi in flag separati che
   `io_events.BOOL_COLS` non conserva. Usare `passAccurate` scarterebbe in
   silenzio il 6% dei riusciti **sbilanciato verso i passaggi lunghi**, cioe'
   esattamente la popolazione che definisce un progressivo: sarebbe un errore
   sistematico, non rumore. `verifica_definizioni_riuscito()` lo rimisura.

Cosa NON e' costruibile, e non si approssima
--------------------------------------------
La **deep completion** standard esclude i cross, e in `events_slim` **non c'e'
nessun flag di cross** (verificato: nessuna colonna contiene "cross"). La
colonna qui si chiama percio' `completamenti_profondi_cross_inclusi` e **non**
`deep_completions`: e' il vincolo 7 applicato a se stessi — due nomi per la
stessa grandezza non sono la stessa grandezza finche' non e' misurato che lo
siano, e qui e' gia' misurato che NON lo sono. Il cross-flag sta nei
`qualifiers`, che costano una rilettura dei 1.889 CSV.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .features import BOX_X, BOX_Y_LO, BOX_Y_HI, FINAL_THIRD_X

# --------------------------------------------------------------------------
# Geometria. Le costanti offensive si IMPORTANO da `features`; qui si aggiunge
# solo cio' che li' non serviva.
# --------------------------------------------------------------------------

#: Ogni squadra attacca verso x = 100, quindi la propria area e' lo specchio
#: di quella avversaria. 100 - 84.29 = 15.71.
BOX_X_DIFENSIVO = 100.0 - BOX_X

#: Confine fra terzo difensivo e terzo medio.
FIRST_THIRD_X = 100.0 / 3.0

#: Campo regolamentare assunto, in metri. **Assunzione dichiarata**: vedi la
#: docstring del modulo. Deriva da `features.py`, che la usa per l'area.
CAMPO_M = (105.0, 68.0)
M_PER_X = CAMPO_M[0] / 100.0   # 1.05
M_PER_Y = CAMPO_M[1] / 100.0   # 0.68

#: `[DECISO dall'utente — 2026-08-14]` un passaggio e' progressivo se
#: **avanza in x di almeno 10 m ED e' riuscito**. Sulla 2025-26 sono 88,9 per
#: squadra-partita. Le altre due letture restano calcolate come colonne
#: affiancate e non fuse (vincolo 7).
SOGLIA_PROGRESSIVO_M = 10.0

#: Raggio entro cui un passaggio completato conta come "profondo", misurato dal
#: centro della porta avversaria (100, 50). 20 m e' la soglia della definizione
#: corrente in letteratura.
RAGGIO_PROFONDO_M = 20.0

#: Le cinque zone, **in ordine da difesa ad attacco**. L'ordine e' parte della
#: definizione: le colonne escono cosi' e i grafici le leggono cosi'.
ZONE = (
    "area_dif",
    "terzo_dif",
    "terzo_medio",
    "terzo_off",
    "area_off",
)

CHIAVE = ["matchId", "teamId"]


# --------------------------------------------------------------------------
# Le cinque zone
# --------------------------------------------------------------------------
def zona(x: pd.Series, y: pd.Series) -> pd.Series:
    """Assegna ogni punto a **esattamente una** delle cinque zone.

    E' una **partizione** di `[0, 100] x [0, 100]`, e non e' un dettaglio: se
    due zone si sovrapponessero i tocchi si conterebbero due volte e le quote
    non sommerebbero a 1. `verifica_partizione()` lo pretende sui dati veri, e
    un test lo pretende su una griglia fitta che copre tutto il campo.

    La suddivisione e' per terzi lungo `x`, con le due aree di rigore ritagliate
    dai terzi estremi:

        area_dif     x <= 15.71  e  20.35 <= y <= 79.65
        terzo_dif    x <  33.33  e  non area_dif
        terzo_medio  33.33 <= x < 66.67
        terzo_off    x >= 66.67  e  non area_off
        area_off     x >= 84.29  e  20.35 <= y <= 79.65

    Nel sistema di riferimento di ogni squadra, quindi `area_off` e' l'area
    avversaria e `area_dif` la propria.
    """
    banda_y = y.between(BOX_Y_LO, BOX_Y_HI)
    in_area_off = (x >= BOX_X) & banda_y
    in_area_dif = (x <= BOX_X_DIFENSIVO) & banda_y

    # `np.select` prende la PRIMA condizione vera: l'ordine rende il ritaglio
    # delle aree prioritario sui terzi, ed e' cio' che garantisce la partizione.
    return pd.Series(
        np.select(
            [
                in_area_dif,
                in_area_off,
                x < FIRST_THIRD_X,
                x < FINAL_THIRD_X,
            ],
            ["area_dif", "area_off", "terzo_dif", "terzo_medio"],
            default="terzo_off",
        ),
        index=x.index,
        dtype=object,
    )


def tocchi_per_zona(events: pd.DataFrame) -> pd.DataFrame:
    """Tocchi per squadra-partita in ognuna delle cinque zone.

    Escono **due** famiglie di colonne per la stessa ragione per cui E1 fa
    uscire ogni candidata grezza e `_rel`: il conteggio dipende da quanto una
    partita e' durata e da quanto una squadra ha avuto la palla, la **quota**
    no. La quota e' il rapporto `num/den` dichiarato che E1 pretende, con
    denominatore i tocchi della squadra in quella partita.
    """
    t = events[events["isTouch"]].copy()
    t["zona"] = zona(t["x"], t["y"])

    conte = (
        t.groupby(CHIAVE + ["zona"]).size()
        .unstack("zona", fill_value=0)
        .reindex(columns=list(ZONE), fill_value=0)
    )
    conte.columns = [f"tocchi_{z}" for z in ZONE]
    conte["tocchi_totali"] = conte.sum(axis=1)

    for z in ZONE:
        conte[f"quota_tocchi_{z}"] = (
            conte[f"tocchi_{z}"] / conte["tocchi_totali"].replace(0, np.nan)
        )
    return conte.reset_index()


# --------------------------------------------------------------------------
# La famiglia dei progressivi
# --------------------------------------------------------------------------
def _passaggi(events: pd.DataFrame) -> pd.DataFrame:
    """I passaggi con geometria completa, piu' le grandezze derivate in metri."""
    p = events[(events["type"] == "Pass")].dropna(subset=["endX", "endY"]).copy()

    p["avanzamento_m"] = (p["endX"] - p["x"]) * M_PER_X
    p["laterale_m"] = (p["endY"] - p["y"]) * M_PER_Y
    p["lunghezza_m"] = np.hypot(p["avanzamento_m"], p["laterale_m"])
    p["riuscito"] = p["outcomeType"] == "Successful"

    # distanza dell'ARRIVO dal centro della porta avversaria (100, 50)
    p["dist_porta_m"] = np.hypot(
        (100.0 - p["endX"]) * M_PER_X, (50.0 - p["endY"]) * M_PER_Y
    )
    p["arriva_in_area"] = (p["endX"] >= BOX_X) & p["endY"].between(BOX_Y_LO, BOX_Y_HI)
    p["parte_da_area"] = (p["x"] >= BOX_X) & p["y"].between(BOX_Y_LO, BOX_Y_HI)
    return p


def progressione(events: pd.DataFrame) -> pd.DataFrame:
    """La famiglia dei progressivi, per squadra-partita.

    **Le tre letture di «10 metri in avanti» escono come colonne separate e non
    si fondono mai** (vincolo 7): sono tre grandezze diverse, con tre numeri
    diversi per squadra-partita, e quale sia «il» passaggio progressivo e' una
    decisione, non una misura. Quella dell'utente e' `prog_riusciti`.

    | colonna | definizione | per squadra-partita (2025-26) |
    | --- | --- | ---: |
    | `prog_tentati` | avanzamento in x >= 10 m | ~137,8 |
    | `prog_riusciti` | ...**e** riuscito — **la scelta dell'utente** | ~88,9 |
    | `prog_per_distanza` | lunghezza >= 10 m e diretto in avanti | ~231,6 |

    Nessuna delle tre coincide con i "progressive passes" dei fornitori
    standard (~40-50 per squadra-partita), che usano l'avanzamento **relativo
    alla distanza dalla porta**. Non e' un difetto: e' una definizione diversa,
    ed e' dichiarata invece di essere presentata come la stessa cosa.
    """
    p = _passaggi(events)

    avanti = p["avanzamento_m"] >= SOGLIA_PROGRESSIVO_M
    p["prog_tentati"] = avanti
    p["prog_riusciti"] = avanti & p["riuscito"]
    p["prog_per_distanza"] = (p["lunghezza_m"] >= SOGLIA_PROGRESSIVO_M) & (
        p["avanzamento_m"] > 0
    )

    # Ingresso in area: arriva dentro l'area avversaria partendo da fuori. Il
    # "partendo da fuori" non e' pedanteria — senza, ogni scarico dentro l'area
    # conterebbe come ingresso.
    p["ingressi_area"] = p["arriva_in_area"] & ~p["parte_da_area"] & p["riuscito"]

    # Vedi la docstring del modulo: il nome dice "cross inclusi" perche' il
    # flag di cross NON e' in `events_slim` e la definizione standard li esclude.
    p["completamenti_profondi_cross_inclusi"] = (
        p["riuscito"] & (p["dist_porta_m"] <= RAGGIO_PROFONDO_M)
    )

    # Metri di avanzamento effettivamente guadagnati coi passaggi riusciti.
    # I passaggi all'indietro entrano col loro segno: e' una progressione NETTA,
    # e sommare solo i positivi misurerebbe un'altra cosa.
    p["metri_progressione"] = np.where(p["riuscito"], p["avanzamento_m"], 0.0)

    out = p.groupby(CHIAVE).agg(
        passaggi=("riuscito", "size"),
        passaggi_riusciti=("riuscito", "sum"),
        prog_tentati=("prog_tentati", "sum"),
        prog_riusciti=("prog_riusciti", "sum"),
        prog_per_distanza=("prog_per_distanza", "sum"),
        ingressi_area=("ingressi_area", "sum"),
        completamenti_profondi_cross_inclusi=(
            "completamenti_profondi_cross_inclusi", "sum"),
        metri_progressione=("metri_progressione", "sum"),
        lunghezza_media_m=("lunghezza_m", "mean"),
    )

    # I rapporti `num/den` dichiarati, che E1 pretende per poter standardizzare.
    den = out["passaggi"].replace(0, np.nan)
    out["quota_prog_riusciti"] = out["prog_riusciti"] / den
    out["quota_passaggi_riusciti"] = out["passaggi_riusciti"] / den
    out["precisione_progressivi"] = (
        out["prog_riusciti"] / out["prog_tentati"].replace(0, np.nan)
    )
    out["metri_per_passaggio"] = out["metri_progressione"] / den
    return out.reset_index()


def metriche_evento(events: pd.DataFrame) -> pd.DataFrame:
    """Tutte le metriche del blocco, una riga per `(matchId, teamId)`.

    Il join e' `outer` di proposito: una squadra-partita con zero passaggi
    validi deve restare nella tabella con zero, non sparire. E' la trappola che
    V0 ha gia' pagato — ricostruire l'universo dai soli tiri fa sparire dal
    denominatore le squadre-partita con zero tiri, che esistono.
    """
    z = tocchi_per_zona(events)
    g = progressione(events)
    return z.merge(g, on=CHIAVE, how="outer")


# --------------------------------------------------------------------------
# Le verifiche. Falsificabili, e nessuna passa da un modello.
# --------------------------------------------------------------------------
def verifica_partizione(events: pd.DataFrame) -> dict:
    """Le cinque zone coprono tutto e non si sovrappongono.

    Se cadesse, le quote non sommerebbero a 1 e i tocchi si conterebbero due
    volte: e' la precondizione di tutto il resto del modulo.
    """
    t = events[events["isTouch"]]
    z = zona(t["x"], t["y"])
    conte = tocchi_per_zona(events)
    somma = conte[[f"quota_tocchi_{k}" for k in ZONE]].sum(axis=1)
    return {
        "tocchi": int(len(t)),
        "zone_osservate": sorted(z.unique().tolist()),
        "zone_dichiarate": sorted(ZONE),
        "senza_zona": int(z.isna().sum()),
        "quote_sommano_a_1": bool(np.allclose(somma.dropna(), 1.0)),
        "scarto_massimo_dalla_somma_1": float((somma.dropna() - 1.0).abs().max()),
    }


def verifica_definizioni_riuscito(events: pd.DataFrame) -> dict:
    """Rimisura il vincolo 7 sul "passaggio riuscito": due derivazioni, una scelta.

    Riporta i numeri che hanno motivato la scelta di `outcomeType`, invece di
    lasciarli in una docstring dove nessuno li puo' falsificare.
    """
    p = events[events["type"] == "Pass"]
    succ = p["outcomeType"] == "Successful"
    acc = p["passAccurate"].astype(bool)
    inacc = p["passInaccurate"].astype(bool)
    nessun_flag = ~acc & ~inacc
    lung = np.hypot((p["endX"] - p["x"]) * M_PER_X, (p["endY"] - p["y"]) * M_PER_Y)

    return {
        "passaggi": int(len(p)),
        "accurate_ma_non_successful": int((acc & ~succ).sum()),  # deve essere 0
        "successful_ma_non_accurate": int((succ & ~acc).sum()),
        "senza_nessun_flag": int(nessun_flag.sum()),
        "quota_senza_flag": float(nessun_flag.mean()),
        "lunghezza_media_con_flag": float(lung[~nessun_flag].mean()),
        "lunghezza_media_senza_flag": float(lung[nessun_flag].mean()),
        "outcometype_e_completa": bool(p["outcomeType"].notna().all()),
    }
