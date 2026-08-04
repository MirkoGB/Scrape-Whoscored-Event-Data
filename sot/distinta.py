# -*- coding: utf-8 -*-
"""Fase 9 / Blocco E2 — lo strato distinta: maglia, capitano, ruolo come serie.

COSTA QUASI ZERO, ED E' STATO VERIFICATO INVECE CHE SPERATO
-----------------------------------------------------------
`lineup_events.parquet` conserva la stringa `qualifiers` grezza degli eventi di
formazione, e `minutes.squads()` gia' ne estrae `PlayerPosition`. `JerseyNumber`
e `CaptainPlayerId` stanno **nella stessa lista**: sono un campo in piu' da una
struttura gia' attraversata, non una rilettura dei 1.889 CSV. Misurato: presenti
sul **100%** delle 3.778 righe `FormationSet` di tutte e cinque le stagioni,
lunghezza sempre allineata a `InvolvedPlayers`, zero nulli su 87.449 righe,
estrazione completa in **0,3 secondi**.

E' la differenza fra un predittore economico e uno caro, e va detta: l'incarico
sui piazzati di E4 vuole `qualifiers` sugli eventi normali, che `events_slim` non
porta, quindi quello costa una rilettura. Questo no.

PERCHE' LA MAGLIA E' UN PREDITTORE DIVERSO DAGLI ALTRI
------------------------------------------------------
Ogni altro predittore d'impiego richiede che si sia gia' giocato. Il numero di
maglia e' **assegnato prima che la stagione cominci**, quindi e' disponibile al
momento della previsione anche per chi al nuovo club non ha storia — cioe' il
caso in cui E2 e' piu' cieco. E' la dichiarazione con cui il club colloca il
giocatore nella gerarchia, e la fa in agosto.

TRE DISCIPLINE, TUTTE E TRE IMPOSTE DA TEST
-------------------------------------------
1. **La maglia non e' una scala.** Il 10 non e' "meglio" del 30 lungo un continuo.
   Le fasce sono dichiarate in `FASCE_MAGLIA` **prima** di guardare i risultati, e
   un test vieta `argmax`/`idxmax`/`quantile` in questo modulo come E1 fa sul
   proprio.
2. **La maglia e' confusa con ruolo ed eta'.** Un numero alto e' spesso un
   giovane, e un giovane gioca poco per ragioni sue. Il test e' **al netto del
   ruolo**, mai marginale: `collinearita_fascia_ruolo` misura quanta
   dell'informazione della fascia il `role_code` gia' contiene.
3. **Il capitano e' sfasato di una stagione.** La fascia della stagione t contro
   le presenze della stessa t sarebbe in parte una **conseguenza** del giocare,
   non una causa: si e' capitani perche' si e' in campo. `capitano_sfasato` usa
   t-1 per prevedere t, e lo sfasamento e' **parte della definizione della
   feature**, non un accorgimento applicato a valle.

LA CHIAVE E' LA TRIPLA, E NON E' UN DETTAGLIO
---------------------------------------------
`(stagione, playerId, teamId)`, la stessa di E0 e di E1. Il numero cambia fra
stagioni **e fra club**: aggregare alla moda su piu' stagioni — che e' cio' che
lo script R fa quando fonde col file esistente — distrugge esattamente il segnale
che serve. E ogni join va su `teamId`, perche' `teamName` **non esiste nei nostri
CSV**: lo script R era scritto su una forma dei dati che aveva il nome.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from . import config, io_events

#: Gli eventi che portano una distinta. `FormationChange` c'e' perche' il ruolo
#: e' una **serie**: chi cambia ruolo a partita in corso cambia rotazione, ed e'
#: un predittore d'impiego. Lo script R prendeva solo `FormationSet` e quei cambi
#: li perdeva.
TIPI_DISTINTA = ("FormationSet", "FormationChange")

#: Le fasce del numero di maglia. DICHIARATE PRIMA, mai ricavate dai dati.
#: L'ordine conta: si applica la prima che matcha.
#:
#: `portiere_classico` (1/12/22) e' tenuta benche' il `role_code` identifichi gia'
#: i portieri. La ragione non e' la ridondanza ma il contrario: se il test e' al
#: netto del ruolo come dev'essere, quella fascia deve risultare **vuota di
#: segnale**. Se invece ne avesse, vorrebbe dire che il numero dice qualcosa che
#: il ruolo non dice — quale dei tre portieri e' il titolare — e sarebbe il
#: risultato piu' interessante del lotto. `collinearita_fascia_ruolo` lo misura.
FASCE_MAGLIA = (
    ("portiere_classico", lambda n: n in (1, 12, 22)),
    ("cifra_singola", lambda n: 1 <= n <= 9),
    ("dieci", lambda n: n == 10),
    ("undici_25", lambda n: 11 <= n <= 25),
    ("ventisei_45", lambda n: 26 <= n <= 45),
    ("oltre_45", lambda n: n > 45),
)

ORDINE_FASCE = tuple(nome for nome, _ in FASCE_MAGLIA)


def fascia_maglia(n) -> str:
    """La fascia di un numero. Prima regola che matcha, ordine di `FASCE_MAGLIA`."""
    if n is None or (isinstance(n, float) and np.isnan(n)):
        return "ignoto"
    n = int(n)
    for nome, test in FASCE_MAGLIA:
        if test(n):
            return nome
    return "ignoto"


def distinte(stagione: str) -> pd.DataFrame:
    """Ogni distinta in forma lunga: una riga per (evento, giocatore).

    I tre qualifier allineati posizionalmente a `InvolvedPlayers` —
    `PlayerPosition`, `JerseyNumber` e la posizione in lista — si estraggono in
    **un passaggio solo**: attraversare la stessa struttura tre volte sarebbe
    triplicare il costo per niente.

    `CaptainPlayerId` non e' allineato: e' un id singolo, e diventa un flag.
    """
    lu = io_events.load_lineup_events(season=stagione)
    d = lu[lu["type"].isin(TIPI_DISTINTA)]

    righe = []
    for r in d.itertuples(index=False):
        q = io_events.parse_qualifiers(r.qualifiers)
        inv = [int(v) for v in str(q.get("InvolvedPlayers", "")).split(",") if v.strip()]
        pos = [int(v) for v in str(q.get("PlayerPosition", "")).split(",") if v.strip()]
        jer = [int(v) for v in str(q.get("JerseyNumber", "")).split(",") if v.strip()]
        cap = q.get("CaptainPlayerId")
        cap = int(cap) if cap not in (None, "") else None
        for slot, pid in enumerate(inv):
            righe.append({
                "matchId": int(r.matchId), "teamId": int(r.teamId),
                "tipo": r.type, "expandedMinute": r.expandedMinute,
                "playerId": pid, "slot": slot,
                "role_code": pos[slot] if slot < len(pos) else np.nan,
                "jersey": jer[slot] if slot < len(jer) else np.nan,
                "is_capitano": int(cap == pid) if cap is not None else 0,
            })
    out = pd.DataFrame(righe)
    out["stagione"] = stagione
    # `FormationSet` prima di `FormationChange` a parita' di minuto: la distinta
    # iniziale e' quella di riferimento.
    out["ordine"] = (out["tipo"] != "FormationSet").astype(int)
    return out.sort_values(["matchId", "teamId", "expandedMinute", "ordine"]
                           ).reset_index(drop=True)


def _indice_partite(stagione: str) -> pd.DataFrame:
    pm = pd.read_parquet(config.player_match(season=stagione))
    return (pm[["matchId", "teamId", "team_match_idx"]]
            .drop_duplicates(["matchId", "teamId"]))


def numero_maglia(stagione: str) -> pd.DataFrame:
    """Il numero per `(stagione, teamId, playerId)`: **la prima distinta**.

    LA REGOLA E' "PRIMA DISTINTA", NON "MODA PESATA SUI MINUTI"
    -----------------------------------------------------------
    Undici triple su 3.972 hanno piu' di un numero dentro la stessa stagione, e
    servono una regola. La moda pesata sui minuti userebbe **i minuti della
    stagione** per costruire un predittore il cui unico pregio e' di **esistere
    prima che quei minuti siano giocati**: sarebbe informazione del bersaglio
    dentro il predittore, cioe' il vincolo 1 violato nel punto esatto in cui la
    feature ha valore. La prima distinta e' la piu' vicina all'assegnazione
    d'agosto ed e' disponibile quando serve.

    Le triple con piu' numeri restano contate in `n_numeri` e sono elencate nel
    report: sono un fatto, non un caso da appianare.
    """
    d = distinte(stagione)
    d = d[d["tipo"] == "FormationSet"]
    d = d.merge(_indice_partite(stagione), on=["matchId", "teamId"], how="inner")

    d = d.sort_values(["teamId", "playerId", "team_match_idx", "slot"])
    g = d.groupby(["teamId", "playerId"], sort=False)
    out = pd.DataFrame({
        "jersey": g["jersey"].first(),          # la PRIMA distinta di stagione
        "n_numeri": g["jersey"].nunique(),
        "prima_apparizione_idx": g["team_match_idx"].first(),
        "distinte": g.size(),
        "capitano_volte": g["is_capitano"].sum(),
    }).reset_index()
    out["stagione"] = stagione
    out["fascia_maglia"] = [fascia_maglia(v) for v in out["jersey"]]
    out["e_capitano"] = (out["capitano_volte"] > 0).astype(int)
    return out[["stagione", "teamId", "playerId", "jersey", "fascia_maglia",
                "n_numeri", "prima_apparizione_idx", "distinte",
                "capitano_volte", "e_capitano"]]


def numero_maglia_multi(stagioni=None) -> pd.DataFrame:
    stagioni = list(config.SEASONS_STORICHE if stagioni is None else stagioni)
    return pd.concat([numero_maglia(st) for st in stagioni], ignore_index=True)


def cambio_numero(nm: pd.DataFrame = None) -> pd.DataFrame:
    """Il cambio di numero fra stagioni **nello stesso club**.

    E' una feature a se', e probabilmente piu' informativa del livello: prendere
    la 10, o passare dalla 7 alla 47, e' un fatto sulla gerarchia che il numero da
    solo non dice.

    Definita solo dove il club e' lo stesso: fra club diversi il numero cambia per
    disponibilita' e non direbbe niente. Chi cambia squadra ha `NaN`, che e'
    l'informazione giusta — non zero, che vorrebbe dire "confermato".
    """
    nm = numero_maglia_multi() if nm is None else nm
    stagioni = sorted(nm["stagione"].unique())
    pos = {s: i for i, s in enumerate(stagioni)}

    prec = nm.copy()
    prec["stagione_succ"] = [stagioni[pos[s] + 1] if pos[s] + 1 < len(stagioni)
                             else None for s in prec["stagione"]]
    prec = prec.dropna(subset=["stagione_succ"])[
        ["stagione_succ", "teamId", "playerId", "jersey", "fascia_maglia",
         "e_capitano"]]
    prec = prec.rename(columns={"stagione_succ": "stagione",
                                "jersey": "jersey_prec",
                                "fascia_maglia": "fascia_prec",
                                "e_capitano": "capitano_prec"})

    n_prima = len(nm)
    out = nm.merge(prec, on=["stagione", "teamId", "playerId"], how="left")
    # Invariante di join (il difetto comune ai tre script R): la chiave e'
    # completa, quindi il conteggio righe non puo' cambiare.
    assert len(out) == n_prima, "il join sulla stagione precedente ha moltiplicato"

    out["stesso_club_anno_prima"] = out["jersey_prec"].notna()
    out["numero_cambiato"] = np.where(
        out["stesso_club_anno_prima"], out["jersey"] != out["jersey_prec"], np.nan)
    out["salito_di_fascia"] = np.where(
        out["stesso_club_anno_prima"],
        [ORDINE_FASCE.index(a) < ORDINE_FASCE.index(b)
         if (a in ORDINE_FASCE and b in ORDINE_FASCE) else False
         for a, b in zip(out["fascia_maglia"], out["fascia_prec"].fillna("ignoto"))],
        np.nan)
    return out


def capitano_sfasato(nm: pd.DataFrame = None) -> pd.DataFrame:
    """La fascia di capitano della stagione **precedente**, come feature di t.

    LO SFASAMENTO E' PARTE DELLA DEFINIZIONE, NON UN AGGIUSTAMENTO
    --------------------------------------------------------------
    Essere capitano nella stagione t e giocare nella stagione t sono la stessa
    cosa guardata due volte: si porta la fascia perche' si e' in campo. Usare t
    per prevedere t misurerebbe una conseguenza e la chiamerebbe causa. La fascia
    di t-1, invece, e' nota in agosto — come il numero di maglia, e per la stessa
    ragione e' un predittore legittimo.

    `capitano_prec` e' `NaN` per chi non c'era in quel club l'anno prima: e' la
    stessa scelta di `cambio_numero`, e vale lo stesso motivo — zero direbbe "non
    era capitano", che e' un'affermazione diversa da "non lo sappiamo".
    """
    c = cambio_numero(nm)
    return c[["stagione", "teamId", "playerId", "jersey", "fascia_maglia",
              "e_capitano", "capitano_prec", "stesso_club_anno_prima",
              "numero_cambiato", "salito_di_fascia"]]


def ruolo_serie(stagione: str) -> pd.DataFrame:
    """Il ruolo come **serie**, non come costante di partita.

    Lo script R faceva `distinct(playerId, .keep_all = TRUE)`, cioe' teneva la
    prima occorrenza e costringeva il ruolo a essere unico per partita. E2 vuole
    l'opposto: chi cambia ruolo cambia rotazione, e la variabilita' del ruolo e'
    essa stessa un predittore d'impiego.

    Il codebook e' quello della fonte, confermato da due strade indipendenti
    (CLAUDE.md): 1 portiere, 2 difensore, 3 centrocampista, 4 attaccante, 5
    panchina. Il 5 **non e' un ruolo** e va tolto prima di misurare la
    variabilita', o "il panchinaro cambia ruolo" ogni volta che entra.
    """
    d = distinte(stagione)
    d = d.merge(_indice_partite(stagione), on=["matchId", "teamId"], how="inner")
    in_campo = d[d["role_code"] != 5]

    g = in_campo.groupby(["teamId", "playerId"])
    out = pd.DataFrame({
        "ruoli_distinti": g["role_code"].nunique(),
        "ruolo_modale": g["role_code"].agg(lambda s: int(s.mode().iloc[0])),
        "partite_in_campo": g["matchId"].nunique(),
        "cambi_ruolo_in_partita": in_campo.groupby(["teamId", "playerId"]).apply(
            lambda x: int(x.groupby("matchId")["role_code"].nunique().gt(1).sum()),
            include_groups=False),
    }).reset_index()
    out["stagione"] = stagione
    out["ruolo_instabile"] = (out["ruoli_distinti"] > 1).astype(int)
    return out[["stagione", "teamId", "playerId", "ruolo_modale", "ruoli_distinti",
                "ruolo_instabile", "cambi_ruolo_in_partita", "partite_in_campo"]]


def collinearita_fascia_ruolo(nm: pd.DataFrame = None,
                              stagioni=None) -> pd.DataFrame:
    """Quanta dell'informazione della fascia il `role_code` gia' contiene.

    E' la disciplina 2, ed e' il controllo che impedisce di misurare il ruolo e
    chiamarlo maglia. Per ogni fascia si riporta la distribuzione dei ruoli
    modali: se una fascia e' quasi interamente di un ruolo solo, quella fascia
    **non porta informazione propria** una volta condizionato al ruolo, e va
    letta cosi' invece che come un effetto.

    In particolare `portiere_classico` (1/12/22) dovrebbe risultare quasi tutta
    `role_code == 1`. Se non lo fosse, il numero direbbe qualcosa che il ruolo non
    dice, e sarebbe il risultato piu' interessante del lotto.
    """
    stagioni = list(config.SEASONS_STORICHE if stagioni is None else stagioni)
    nm = numero_maglia_multi(stagioni) if nm is None else nm
    rs = pd.concat([ruolo_serie(st) for st in stagioni], ignore_index=True)

    n_prima = len(nm)
    j = nm.merge(rs, on=["stagione", "teamId", "playerId"], how="left")
    assert len(j) == n_prima, "il join col ruolo ha moltiplicato le righe"

    j = j.dropna(subset=["ruolo_modale"])
    tab = (j.groupby(["fascia_maglia", "ruolo_modale"]).size()
           .rename("n").reset_index())
    tot = tab.groupby("fascia_maglia")["n"].transform("sum")
    tab["quota"] = tab["n"] / tot
    tab["ruolo"] = tab["ruolo_modale"].map(
        {1: "GK", 2: "DIF", 3: "CEN", 4: "ATT"}).fillna("?")

    dom = (tab.sort_values("quota", ascending=False)
           .groupby("fascia_maglia").first().reset_index()
           .rename(columns={"ruolo": "ruolo_dominante", "quota": "quota_dominante"}))
    dom["righe"] = dom["fascia_maglia"].map(tab.groupby("fascia_maglia")["n"].sum())
    return dom[["fascia_maglia", "righe", "ruolo_dominante", "quota_dominante"]]


def collinearita_per_numero(nm: pd.DataFrame = None, numeri=(1, 12, 22, 10),
                            stagioni=None) -> pd.DataFrame:
    """La composizione di ruolo dei singoli numeri che la fascia mette insieme.

    Serve a leggere `collinearita_fascia_ruolo`, che sulla fascia
    `portiere_classico` da' un dominante GK al **46%** — cioe' non domina affatto.
    Il dettaglio dice perche', e il perche' e' che la fascia dichiarata mette
    insieme cose diverse: la **1** e' portiere nel 100% dei casi, la **12** nel
    18% e la **22** nell'8%.

    LA FASCIA NON VIENE RIDEFINITA, ED E' IL PUNTO
    ----------------------------------------------
    Il folklore "1/12/22 sono i tre portieri" e' falso in questi dati, e lo si
    scopre **dopo** aver dichiarato la partizione. Cambiarla adesso perche' i
    numeri non tornano sarebbe adattare la partizione al campione su cui poi la
    si valuta — esattamente cio' che il vincolo 1 vieta e che il committente ha
    chiesto di non fare («la partizione fissata prima di guardare i risultati»).
    La fascia resta com'e' ed e' la sua **eterogeneita'** a essere il risultato.
    """
    stagioni = list(config.SEASONS_STORICHE if stagioni is None else stagioni)
    nm = numero_maglia_multi(stagioni) if nm is None else nm
    rs = pd.concat([ruolo_serie(st) for st in stagioni], ignore_index=True)
    j = nm.merge(rs, on=["stagione", "teamId", "playerId"], how="left")
    jj = j.dropna(subset=["ruolo_modale"])

    righe = []
    for n in numeri:
        s = jj[jj["jersey"] == n]
        q = s["ruolo_modale"].value_counts(normalize=True)
        righe.append({"jersey": n, "righe": len(s),
                      "GK": float(q.get(1, 0.0)), "DIF": float(q.get(2, 0.0)),
                      "CEN": float(q.get(3, 0.0)), "ATT": float(q.get(4, 0.0))})
    return pd.DataFrame(righe)


def dove_il_ruolo_tace(nm: pd.DataFrame = None, stagioni=None) -> dict:
    """Quante triple non hanno **nessun** ruolo, e sono quelle che contano.

    Chi non e' mai sceso in campo ha `role_code == 5` in ogni distinta, cioe'
    "sostituto", che non e' una posizione: per quelle triple il ruolo **non
    esiste**. Sono 1.013 su 3.972, il **25,5%**.

    E' l'argomento a favore del numero di maglia detto nel modo piu' stretto
    possibile: proprio dove ogni predittore d'impiego tace — nessun minuto,
    nessun ruolo, nessuna storia in quel club — **il numero c'e' lo stesso**,
    perche' e' stato assegnato in agosto. Se la feature serve, serve li'.
    """
    stagioni = list(config.SEASONS_STORICHE if stagioni is None else stagioni)
    nm = numero_maglia_multi(stagioni) if nm is None else nm
    rs = pd.concat([ruolo_serie(st) for st in stagioni], ignore_index=True)
    j = nm.merge(rs, on=["stagione", "teamId", "playerId"], how="left")
    senza = j["ruolo_modale"].isna()
    return {
        "triple": len(j),
        "senza_ruolo": int(senza.sum()),
        "quota_senza_ruolo": float(senza.mean()),
        "con_maglia_fra_i_senza_ruolo": int(j.loc[senza, "jersey"].notna().sum()),
    }
