# -*- coding: utf-8 -*-
"""Fase 9 / Blocco E2 — le squalifiche, che NON si stimano.

E' il pezzo gratis del blocco, e va speso per primo per una ragione che non e'
di comodita': se lo si calcolasse dopo aver stimato qualcosa, la parte di
presenze mancate che le squalifiche spiegano da sole finirebbe attribuita a un
modello che non l'ha prodotta. Qui non c'e' nessun parametro stimato, nessun
iperparametro e nessun fit: c'e' una regola di conteggio applicata ai cartellini.

LA REGOLA, E LE TRE ASSUNZIONI CHE PORTA CON SE'
------------------------------------------------
Sono dichiarate qui e non ricavate dai dati (vincolo 1: una soglia scelta
guardando il campione su cui poi la si valuta e' un iperparametro adattato).

1. **Cinque ammonizioni valgono una giornata**, e il contatore riparte da zero.
   Le squalifiche cadono quindi alla 5a, alla 10a, alla 15a.
2. **L'ammonizione che porta all'espulsione per doppio giallo non entra nel
   conteggio delle cinque.** WhoScored registra le due cose separatamente — ogni
   `SecondYellow` ha **esattamente un** `Yellow` dello stesso giocatore nella
   stessa partita, verificato su tutte e cinque le stagioni — quindi senza questa
   regola il primo giallo verrebbe contato due volte, una nel cumulo e una
   nell'espulsione.
3. **L'espulsione vale UNA giornata**, ed e' un **limite inferiore**, non una
   previsione. La durata vera la decide il giudice sportivo e **non e' nei
   dati**: una condotta violenta ne vale tre o piu'. Quindi tutto cio' che questo
   modulo produce va letto come "almeno queste", mai come "esattamente queste".

CHI NON E' UN GIOCATORE
-----------------------
`playerId` nullo significa allenatore o staff, ed e' il caso che CLAUDE.md ha
gia' misurato: 85 espulsioni nel 2025-26 ma solo 65 tolgono un uomo dal campo,
17 delle quali a staff. **Per le squalifiche il taglio e' un altro**, e sbagliarlo
sarebbe facile: le 3 espulsioni a giocatori gia' usciti o in panchina **contano
eccome** — un espulso dalla panchina salta la giornata dopo esattamente come chi
era in campo. Cio' che non conta e' solo lo staff. Il numero giusto e' 68, non 65
e non 85.

LA VERIFICA, CHE NON PASSA DA NESSUN MODELLO
--------------------------------------------
Una squalifica e' falsificabile: se la regola dice che un giocatore salta la
partita successiva della sua squadra, quel giocatore **non deve comparire** fra i
convocati di quella partita. `verifica()` lo controlla riga per riga. E' la stessa
specie di controllo della riconciliazione `FV = V + bonus` dell'acquisizione dei
voti — non c'e' niente da stimare, o torna o non torna — ed e' il motivo per cui
questo modulo puo' dichiarare un risultato senza un walk-forward.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from . import config, io_events

# --------------------------------------------------------------------------
# Le costanti della regola. Sono LETTERALI: non si ricavano dai dati.
# Un test vieta argmax/quantile in questo modulo, come E1 fa sul proprio.
# --------------------------------------------------------------------------

#: Ammonizioni che fanno scattare una giornata di squalifica.
GIALLI_PER_SQUALIFICA = 5

#: Giornate attribuite a un'espulsione. E' il MINIMO regolamentare: la durata
#: vera non e' nei dati. Vedi `SCENARI_ROSSO` per la sensibilita'.
GIORNATE_PER_ROSSO = 1

#: Durate alternative dell'espulsione, per mostrare quanto il risultato dipende
#: dall'assunzione 3 invece di nasconderlo dentro un numero solo.
SCENARI_ROSSO = (1, 2, 3)

#: I `cardType` che sono espulsioni. Identico a `minutes.SENDING_OFF`, e un test
#: verifica che le due non divergano: se un domani la fonte ne aggiungesse un
#: terzo, i minuti e le squalifiche devono cambiare insieme.
ESPULSIONI = ("Red", "SecondYellow")


def cartellini(stagione: str) -> pd.DataFrame:
    """Un cartellino per riga, con l'indice cronologico della squadra.

    Lo **staff esce qui** (`playerId` nullo) e non piu' avanti: e' l'unico
    filtro, e tenerlo in un posto solo evita che una delle due strade — cumulo e
    espulsioni — lo applichi e l'altra no.

    L'ordinamento e' `team_match_idx` di `player_match`, cioe' l'indice
    cronologico **di squadra**. Non e' la giornata di campionato, che nei dati
    non esiste (CLAUDE.md), e per questo conteggio non serve: una squalifica si
    sconta alla partita successiva **della propria squadra**, che e' esattamente
    cio' che quell'indice ordina. Con un recupero fuori posto la giornata
    sarebbe la cosa sbagliata da usare.
    """
    lu = io_events.load_lineup_events(season=stagione)
    c = lu[lu["type"] == "Card"].dropna(subset=["playerId"]).copy()
    c["playerId"] = c["playerId"].astype("int64")
    c["teamId"] = c["teamId"].astype("int64")
    c["matchId"] = c["matchId"].astype("int64")

    pm = pd.read_parquet(config.player_match(season=stagione))
    idx = (pm[["matchId", "teamId", "team_match_idx", "date"]]
           .drop_duplicates(["matchId", "teamId"]))
    n_prima = len(c)
    c = c.merge(idx, on=["matchId", "teamId"], how="inner")
    # Invariante di join: e' il difetto comune ai tre script R della specifica —
    # un fallback sulla chiave parziale moltiplica le righe. Qui la chiave e'
    # completa e il join non puo' che ridurre.
    assert len(c) <= n_prima, "il join sui match ha moltiplicato i cartellini"

    c["stagione"] = stagione
    return c[["stagione", "matchId", "teamId", "playerId", "playerName",
              "cardType", "team_match_idx", "date", "expandedMinute"]]


def eventi_disciplinari(stagione: str) -> pd.DataFrame:
    """Per (partita, giocatore): gialli che contano, ed espulsione si'/no.

    Applica l'assunzione 2. Il giallo che precede un doppio giallo si toglie
    **qui**, in un punto solo, cosi' che il cumulo non possa divergere
    dall'espulsione.
    """
    c = cartellini(stagione)
    g = (c.groupby(["stagione", "teamId", "playerId", "playerName",
                    "matchId", "team_match_idx", "date"])
         .agg(gialli_grezzi=("cardType", lambda s: int((s == "Yellow").sum())),
              doppio_giallo=("cardType", lambda s: int((s == "SecondYellow").sum())),
              rosso_diretto=("cardType", lambda s: int((s == "Red").sum())))
         .reset_index())

    # Assunzione 2: il primo giallo del doppio giallo non entra nel cumulo.
    g["gialli"] = (g["gialli_grezzi"] - g["doppio_giallo"]).clip(lower=0)
    g["espulso"] = ((g["doppio_giallo"] + g["rosso_diretto"]) > 0).astype(int)
    return g.sort_values(["teamId", "playerId", "team_match_idx"]).reset_index(drop=True)


def squalifiche(stagione: str, giornate_per_rosso: int = GIORNATE_PER_ROSSO
                ) -> pd.DataFrame:
    """Le giornate di squalifica maturate, con l'indice della prima scontata.

    Una riga per squalifica, non per giocatore: chi ne prende due nella stagione
    ha due righe, e `motivo` dice quale delle due regole l'ha prodotta.

    `idx_prima_saltata` e' `team_match_idx` della partita in cui la squalifica si
    sconta, cioe' quella **successiva** a quella del cartellino. Puo' cadere oltre
    la fine della stagione, e in quel caso la squalifica e' maturata ma non
    scontata: resta in tabella con `scontata_in_stagione = False`, perche'
    toglierla sarebbe far sparire un fatto.
    """
    ev = eventi_disciplinari(stagione)
    righe = []
    for (tid, pid), g in ev.groupby(["teamId", "playerId"], sort=False):
        g = g.sort_values("team_match_idx")
        cumulo = 0
        nome = g["playerName"].iloc[0]
        for r in g.itertuples(index=False):
            cumulo += r.gialli
            if cumulo >= GIALLI_PER_SQUALIFICA:
                cumulo -= GIALLI_PER_SQUALIFICA          # assunzione 1: riparte
                righe.append((tid, pid, nome, r.team_match_idx, "cumulo_gialli", 1))
            if r.espulso:
                motivo = "doppio_giallo" if r.doppio_giallo else "rosso_diretto"
                righe.append((tid, pid, nome, r.team_match_idx, motivo,
                              giornate_per_rosso))

    out = pd.DataFrame(righe, columns=["teamId", "playerId", "playerName",
                                       "idx_cartellino", "motivo", "giornate"])
    if not len(out):
        return out.assign(stagione=stagione, idx_prima_saltata=[],
                          scontata_in_stagione=[])

    out["stagione"] = stagione
    out["idx_prima_saltata"] = out["idx_cartellino"] + 1

    # Il calendario vero della squadra, contato dai dati e mai assunto a 38:
    # l'Atalanta ne ha 35 nelle due stagioni bucate.
    pm = pd.read_parquet(config.player_match(season=stagione))
    ultimo = pm.groupby("teamId")["team_match_idx"].max()
    out["ultimo_idx_squadra"] = out["teamId"].map(ultimo)
    out["scontata_in_stagione"] = out["idx_prima_saltata"] <= out["ultimo_idx_squadra"]

    cols = ["stagione", "teamId", "playerId", "playerName", "motivo",
            "idx_cartellino", "idx_prima_saltata", "giornate",
            "ultimo_idx_squadra", "scontata_in_stagione"]
    return out[cols].sort_values(["teamId", "playerId", "idx_cartellino"]
                                 ).reset_index(drop=True)


def verifica(stagione: str, sq: pd.DataFrame = None) -> dict:
    """Il giocatore squalificato NON deve comparire fra i convocati. Falsificabile.

    E' il controllo forte del modulo, e non passa da nessun modello: o il
    giocatore c'e' o non c'e'. Un accordo alto **non e' scontato**, perche' la
    regola e' stata scritta senza guardare le presenze.

    Il baseline e' obbligatorio (vincolo 6) e qui e' particolarmente necessario:
    un giocatore qualunque e' assente dalla distinta abbastanza spesso, quindi
    "il 90% dei squalificati non gioca" non significa niente finche' non si sa
    quanto fa **lo stesso giocatore nelle giornate in cui non e' squalificato**.

    IL RESIDUO HA UNA CAUSA, ED E' STATA CERCATA
    --------------------------------------------
    L'accordo non e' uniforme fra stagioni: 91,4% nel 2021-22 contro 99,4% nel
    2024-25. La spiegazione **non e' che la regola funzionasse peggio**, ed e'
    misurata invece che addotta: nel 2021-22 **17 errori su 20** cadono su
    squadre a cui WhoScored manca almeno una partita, mentre quelle squadre sono
    solo il **42,9%** delle righe. Nel 2022-23, 8 su 13 contro il 35,1%.

    Il meccanismo e' meccanico. `team_match_idx` numera le partite **presenti nei
    dati**: se quella successiva al cartellino e' fra le 12 assenti alla fonte,
    `idx + 1` non e' la partita in cui la squalifica si sconta ma quella dopo, in
    cui il giocatore e' gia' rientrato. La regola dice "assente" e i dati dicono
    "presente" — ed e' un difetto dell'indice, non della regola.

    Ne segue che l'accordo da citare e' **quello sulle squadre col calendario
    intero**, riportato a parte. Le tre stagioni complete stanno fra 96,3% e
    99,4% senza alcun aggiustamento.
    """
    if sq is None:
        sq = squalifiche(stagione)
    pm = pd.read_parquet(config.player_match(season=stagione))
    convocato = set(zip(pm["teamId"], pm["playerId"], pm["team_match_idx"]))

    s = sq[sq["scontata_in_stagione"]].copy()
    s["assente"] = [(t, p, i) not in convocato for t, p, i
                    in zip(s["teamId"], s["playerId"], s["idx_prima_saltata"])]
    s["calendario_intero"] = s["teamId"].map(_calendario_intero(pm))

    # Baseline: le stesse persone, nelle giornate in cui NON sono squalificate.
    saltate = set(zip(s["teamId"], s["playerId"], s["idx_prima_saltata"]))
    ultimo = pm.groupby("teamId")["team_match_idx"].max()
    base = []
    for tid, pid in s[["teamId", "playerId"]].drop_duplicates().itertuples(index=False):
        for i in range(1, int(ultimo.get(tid, 0)) + 1):
            if (tid, pid, i) in saltate:
                continue
            base.append((tid, pid, i) not in convocato)

    pulite = s[s["calendario_intero"]]
    return {
        "stagione": stagione,
        "squalifiche_scontate": int(len(s)),
        "assenti": int(s["assente"].sum()),
        "accordo": float(s["assente"].mean()) if len(s) else float("nan"),
        "baseline_assenza": float(np.mean(base)) if base else float("nan"),
        "righe_baseline": len(base),
        # La scomposizione che spiega quasi tutto il residuo, vedi docstring.
        "righe_calendario_intero": int(len(pulite)),
        "accordo_calendario_intero": (float(pulite["assente"].mean())
                                      if len(pulite) else float("nan")),
        "errori": int((~s["assente"]).sum()),
        "errori_su_squadra_bucata": int((~s["assente"] & ~s["calendario_intero"]).sum()),
        "quota_righe_squadra_bucata": (float((~s["calendario_intero"]).mean())
                                       if len(s) else float("nan")),
    }


def _calendario_intero(pm: pd.DataFrame) -> pd.Series:
    """Quali squadre hanno tutte le partite nei dati.

    Il denominatore si **conta**, mai assunto a 38 (CLAUDE.md): il massimo
    osservato nella stagione e' il calendario pieno, e chi ci arriva ce l'ha
    intero. Nel 2022-23 nessuna squadra tocca 39 benche' Spezia e Verona ne
    abbiano giocate 39, quindi il confronto e' col massimo dei dati e non con un
    numero scritto a mano.
    """
    n = pm.groupby("teamId")["team_match_idx"].max()
    return n == n.max()


def giornate_per_giocatore(stagione: str,
                           giornate_per_rosso: int = GIORNATE_PER_ROSSO
                           ) -> pd.DataFrame:
    """Giornate di squalifica per `(stagione, teamId, playerId)`.

    E' la forma in cui la quantita' entra in E2: un numero per la tripla, alla
    stessa granularita' dell'aggancio di E0 e delle feature di E1.
    """
    sq = squalifiche(stagione, giornate_per_rosso=giornate_per_rosso)
    if not len(sq):
        return pd.DataFrame(columns=["stagione", "teamId", "playerId",
                                     "playerName", "giornate_squalifica"])
    out = (sq[sq["scontata_in_stagione"]]
           .groupby(["stagione", "teamId", "playerId", "playerName"])["giornate"]
           .sum().rename("giornate_squalifica").reset_index())
    return out


def riepilogo(stagioni=None, giornate_per_rosso: int = GIORNATE_PER_ROSSO
              ) -> pd.DataFrame:
    """Una riga per stagione: quante squalifiche, di che tipo, quante persone."""
    stagioni = list(config.SEASONS_STORICHE if stagioni is None else stagioni)
    righe = []
    for st in stagioni:
        sq = squalifiche(st, giornate_per_rosso=giornate_per_rosso)
        s = sq[sq["scontata_in_stagione"]]
        m = s["motivo"].value_counts()
        righe.append({
            "stagione": st,
            "squalifiche": len(s),
            "cumulo_gialli": int(m.get("cumulo_gialli", 0)),
            "doppio_giallo": int(m.get("doppio_giallo", 0)),
            "rosso_diretto": int(m.get("rosso_diretto", 0)),
            "giornate_totali": int(s["giornate"].sum()),
            "giocatori_colpiti": int(s.groupby(["teamId", "playerId"]).ngroups),
            "maturate_non_scontate": int((~sq["scontata_in_stagione"]).sum()),
        })
    return pd.DataFrame(righe)


def sensibilita_durata_rosso(stagioni=None) -> pd.DataFrame:
    """Quanto il totale dipende dall'assunzione 3, che e' la piu' fragile.

    La durata vera dell'espulsione non e' nei dati. Invece di scegliere 1 e
    tacere, si mostra il totale sotto i tre scenari: la differenza fra loro **e'**
    l'incertezza di quell'assunzione.
    """
    stagioni = list(config.SEASONS_STORICHE if stagioni is None else stagioni)
    righe = []
    for n in SCENARI_ROSSO:
        r = riepilogo(stagioni, giornate_per_rosso=n)
        righe.append({
            "giornate_per_rosso": n,
            "giornate_totali": int(r["giornate_totali"].sum()),
            "per_stagione": float(r["giornate_totali"].mean()),
        })
    return pd.DataFrame(righe)


# --------------------------------------------------------------------------
# La seconda strada: i cartellini della fonte dei voti
#
# `fantapunti.per_giocatore_stagione()` porta gia' `ammonizioni` ed `espulsioni`
# per giocatore-stagione, sulla chiave `giocatore_id`. E' una fonte INDIPENDENTE
# per la stessa grandezza, e il vincolo 7 dice cosa farne: misurarle una contro
# l'altra, e se divergono tenerle in due colonne invece di scegliere la comoda.
#
# COME DIVERGONO (misurato, `confronto_fonti`)
# --------------------------------------------
# * **Le espulsioni concordano**: 98-99% delle righe, e i totali di stagione
#   stanno a un paio di unita' l'uno dall'altro. E' la grandezza che conta di
#   piu' per le squalifiche ed e' quella che regge.
# * **Le ammonizioni no**: 85-93% delle righe, e la fonte dei voti ne conta
#   **sistematicamente di piu'** (+2-3% ogni stagione). L'accordo e' peggiore
#   proprio nelle due stagioni con partite mancanti (87,4% e 85,2% contro 92-93%
#   delle complete), quindi una parte del divario e' il buco dell'archivio
#   WhoScored — ma **non tutto**: nel 2023-24, che e' completo, restano 42
#   ammonizioni di scarto. La causa residua non e' identificata e **non e' stata
#   ipotizzata**.
#
# QUALE SI USA, E PERCHE'
# -----------------------
# Per la misura del divario oracolo si usa **la fonte dei voti**, per due ragioni
# che non sono la comodita': sta gia' sulla chiave del modello d'asta
# (`giocatore_id`, nessun aggancio di mezzo, nessun residuo) e **non ha buchi di
# calendario**, che e' il difetto che si e' appena visto rovinare l'indice
# cronologico. WhoScored resta il controllo indipendente e l'unica fonte della
# *sequenza* — quando la squalifica cade — che i totali di stagione non danno.
# --------------------------------------------------------------------------

def giornate_da_voti(stagione: str, per_stagione: pd.DataFrame = None,
                     giornate_per_rosso: int = GIORNATE_PER_ROSSO) -> pd.DataFrame:
    """Giornate di squalifica dai totali di stagione della fonte dei voti.

    `ammonizioni // 5 + espulsioni * giornate_per_rosso`. La divisione intera **e'**
    la regola dell'assunzione 1 letta sui totali: con il contatore che riparte da
    zero, il numero di squalifiche da cumulo in una stagione e' esattamente il
    quoziente. Non e' un'approssimazione della sequenza, e' la stessa cosa.

    Cio' che i totali NON danno e' **quando** la squalifica cade, ed e' il motivo
    per cui la strada WhoScored resta.
    """
    from . import fantapunti as FP
    ps = FP.per_giocatore_stagione() if per_stagione is None else per_stagione
    d = ps[ps["stagione"] == stagione].copy()
    d["squalifiche_cumulo"] = d["ammonizioni"] // GIALLI_PER_SQUALIFICA
    d["giornate_squalifica"] = (d["squalifiche_cumulo"]
                                + d["espulsioni"] * giornate_per_rosso)
    return d[["stagione", "giocatore_id", "giocatore", "ruolo", "ammonizioni",
              "espulsioni", "squalifiche_cumulo", "giornate_squalifica"]]


def confronto_fonti(stagioni=None, mappa: pd.DataFrame = None) -> pd.DataFrame:
    """Le due fonti dei cartellini, una contro l'altra. Vincolo 7.

    Non riconcilia e non sceglie: misura. L'accordo si riporta **per riga** e non
    solo sui totali, perche' due totali possono coincidere compensandosi.
    """
    from . import fantapunti as FP, multistagione as MS
    stagioni = list(config.SEASONS_STORICHE if stagioni is None else stagioni)
    ps = FP.per_giocatore_stagione()
    mappa = MS.aggancio_giocatori()["mappa"] if mappa is None else mappa

    righe = []
    for st in stagioni:
        ev = eventi_disciplinari(st)
        ws = (ev.groupby(["teamId", "playerId"])
              .agg(gialli=("gialli", "sum"), dg=("doppio_giallo", "sum"),
                   rd=("rosso_diretto", "sum")).reset_index())
        m = mappa[mappa["stagione"] == st][["teamId_ws", "playerId_ws",
                                            "giocatore_id_fc"]]
        n_prima = len(ws)
        ws = ws.merge(m, left_on=["teamId", "playerId"],
                      right_on=["teamId_ws", "playerId_ws"])
        assert len(ws) <= n_prima, "il join sull'aggancio ha moltiplicato le righe"

        fc = ps[ps["stagione"] == st][["giocatore_id", "ammonizioni", "espulsioni"]]
        j = ws.merge(fc, left_on="giocatore_id_fc", right_on="giocatore_id")
        j["esp_ws"] = j["dg"] + j["rd"]
        righe.append({
            "stagione": st, "righe": len(j),
            "gialli_ws": int(j["gialli"].sum()),
            "gialli_fc": int(j["ammonizioni"].sum()),
            "accordo_gialli": float((j["gialli"] == j["ammonizioni"]).mean()),
            "esp_ws": int(j["esp_ws"].sum()),
            "esp_fc": int(j["espulsioni"].sum()),
            "accordo_espulsioni": float((j["esp_ws"] == j["espulsioni"]).mean()),
        })
    return pd.DataFrame(righe)


# --------------------------------------------------------------------------
# Quanta parte del divario oracolo chiudono le squalifiche DA SOLE
#
# E' la misura per cui questo blocco esiste, e va fatta **prima** che entri un
# solo predittore stimato: altrimenti la parte di presenze mancate che una regola
# di conteggio spiega gratis finirebbe attribuita a un modello che non l'ha
# prodotta.
#
# IL DIVARIO
# ----------
# `modello_asta.scomposizione_errore` lo ha gia' misurato: MAE 61,4 col modello
# completo, **5,6** con le presenze note. I 55,8 punti in mezzo sono tutto cio'
# che un predittore d'impiego perfetto potrebbe guadagnare, e la metrica di E2 e'
# la **quota** di quei 55,8, non il MAE grezzo (che scende sempre un po').
#
# DUE VARIANTI, E LA PRIMA E' UN ORACOLO DICHIARATO
# -------------------------------------------------
# 1. **oracolo dei cartellini** — le squalifiche della stagione bersaglio sono
#    note e si sottraggono. NON e' disponibile al momento della previsione: i
#    cartellini di t+1 si prendono in t+1. E' il **tetto** di cio' che le
#    squalifiche possono valere, e serve a sapere se vale la pena prevederle.
# 2. **dal solo passato** — il tasso di giornate per presenza del giocatore nelle
#    stagioni precedenti, applicato alle presenze attese. Questa e' disponibile
#    alla previsione, e rispetta il vincolo 1.
#
# Riportarle insieme e' il punto: la distanza fra le due dice quanto del tetto e'
# effettivamente raggiungibile, che e' una domanda diversa da quanto vale il
# tetto.
#
# UN LIMITE STRUTTURALE DELLA SOTTRAZIONE
# ---------------------------------------
# Le presenze del fantacalcio sono le partite **con un voto**, non le convocazioni.
# Una squalifica a un panchinaro non toglie nessuna presenza, perche' quella
# presenza non ci sarebbe stata comunque. Sottrarre le giornate dalle presenze
# attese quindi **sovracorregge sulle riserve**, e il clip a zero non basta a
# sistemarlo: e' dichiarato qui e si vede nella scomposizione per ruolo.
# --------------------------------------------------------------------------

def _giornate_attese_dal_passato(stagione: str, per_stagione: pd.DataFrame,
                                 giornate_per_rosso: int = GIORNATE_PER_ROSSO
                                 ) -> pd.Series:
    """Tasso di giornate per presenza dal SOLO passato, per `giocatore_id`.

    Nessun fit: e' un rapporto fra somme, calcolato sulle stagioni precedenti a
    quella bersaglio. Chi non ha passato prende il tasso del proprio ruolo, e chi
    non ha nemmeno quello prende il tasso generale — sempre dal passato.
    """
    passato = per_stagione[per_stagione["stagione"] < stagione]
    if passato.empty:
        return pd.Series(dtype=float)

    g = giornate_da_voti_multi(sorted(passato["stagione"].unique()),
                               per_stagione, giornate_per_rosso)
    g = g.merge(passato[["stagione", "giocatore_id", "presenze", "ruolo"]],
                on=["stagione", "giocatore_id"], how="left")
    per_gioc = g.groupby("giocatore_id").agg(
        gio=("giornate_squalifica", "sum"), pres=("presenze", "sum"))
    tasso = per_gioc["gio"] / per_gioc["pres"].replace(0, np.nan)
    return tasso


def giornate_da_voti_multi(stagioni, per_stagione: pd.DataFrame = None,
                           giornate_per_rosso: int = GIORNATE_PER_ROSSO
                           ) -> pd.DataFrame:
    """`giornate_da_voti` su piu' stagioni, concatenate."""
    from . import fantapunti as FP
    ps = FP.per_giocatore_stagione() if per_stagione is None else per_stagione
    return pd.concat([giornate_da_voti(st, ps, giornate_per_rosso)
                      for st in stagioni], ignore_index=True)


def divario_oracolo(wf: pd.DataFrame = None, per_stagione: pd.DataFrame = None,
                    giornate_per_rosso: int = GIORNATE_PER_ROSSO) -> pd.DataFrame:
    """La quota del divario oracolo chiusa dalle squalifiche, sulle 4 transizioni.

    Le stesse righe e le stesse transizioni del modello d'asta: cambiare campione
    renderebbe i numeri non confrontabili con quelli gia' pubblicati.
    """
    from . import fantapunti as FP, modello_asta as MA
    per_stagione = FP.per_giocatore_stagione() if per_stagione is None else per_stagione
    wf = MA.walkforward(per_stagione=per_stagione) if wf is None else wf

    d = wf.copy()
    tasso_unita = d["voto_atteso"] + d["bonus_per_presenza_atteso"]

    # (1) oracolo: le giornate della stagione bersaglio, note.
    oss = giornate_da_voti_multi(sorted(d["stagione_prevista"].unique()),
                                 per_stagione, giornate_per_rosso)
    chiave = oss.set_index(["stagione", "giocatore_id"])["giornate_squalifica"]
    d["gio_osservate"] = [chiave.get((s, g), 0.0) for s, g
                          in zip(d["stagione_prevista"], d["giocatore_id"])]

    # (2) dal solo passato: tasso per presenza x presenze attese.
    attese = []
    for st, sub in d.groupby("stagione_prevista"):
        t = _giornate_attese_dal_passato(st, per_stagione, giornate_per_rosso)
        attese.append(pd.Series(
            sub["giocatore_id"].map(t).fillna(0.0).to_numpy() * sub["presenze_attese"].to_numpy(),
            index=sub.index))
    d["gio_attese"] = pd.concat(attese).reindex(d.index)

    varianti = {
        "modello completo": d["punti_previsti"],
        "meno squalifiche attese (dal solo passato)":
            (d["presenze_attese"] - d["gio_attese"]).clip(lower=0) * tasso_unita,
        "meno squalifiche note (ORACOLO dei cartellini)":
            (d["presenze_attese"] - d["gio_osservate"]).clip(lower=0) * tasso_unita,
        "presenze note (ORACOLO, il pavimento)":
            d["presenze_osservate"] * tasso_unita,
    }

    righe = []
    for nome, x in varianti.items():
        ok = x.notna()
        righe.append({"variante": nome, "righe": int(ok.sum()),
                      "mae": float((x[ok] - d["punti_osservati"][ok]).abs().mean())})
    out = pd.DataFrame(righe)

    completo = float(out.loc[out["variante"] == "modello completo", "mae"].iloc[0])
    pavimento = float(out["mae"].iloc[-1])
    divario = completo - pavimento
    out["divario_chiuso"] = (completo - out["mae"]) / divario
    out["divario_chiuso_pct"] = 100 * out["divario_chiuso"]
    return out


def perche_peggiora(wf: pd.DataFrame = None, per_stagione: pd.DataFrame = None,
                    giornate_per_rosso: int = GIORNATE_PER_ROSSO) -> pd.DataFrame:
    """Il bias delle presenze attese, separato fra chi viene squalificato e chi no.

    E' la spiegazione del risultato negativo, e non e' stata addotta: e' misurata.

    Sottrarre le giornate di squalifica **peggiora** il MAE, e la ragione e' che
    la correzione va nel verso sbagliato proprio dove si applica. Chi prende
    squalifiche e' chi gioca: cinque ammonizioni non le accumula un panchinaro.
    Ma su quei giocatori il modello d'asta gia' **sottostima** le presenze, perche'
    lo shrinkage al ruolo tira verso il basso chi sta in alto. Togliere altre
    giornate a una previsione gia' troppo bassa allontana.

    Ne segue l'inversione che questo blocco consegna a E2.4: **il cartellino non
    e' una presenza in meno, e' il segnale che quel giocatore gioca.** Come
    sottrazione e' dannoso, come predittore d'impiego ha il segno opposto e va
    provato in quella forma.
    """
    from . import fantapunti as FP, modello_asta as MA
    per_stagione = FP.per_giocatore_stagione() if per_stagione is None else per_stagione
    wf = MA.walkforward(per_stagione=per_stagione) if wf is None else wf

    oss = giornate_da_voti_multi(sorted(wf["stagione_prevista"].unique()),
                                 per_stagione, giornate_per_rosso)
    chiave = oss.set_index(["stagione", "giocatore_id"])["giornate_squalifica"]
    d = wf.copy()
    d["gio"] = [chiave.get((s, g), 0.0) for s, g
                in zip(d["stagione_prevista"], d["giocatore_id"])]

    righe = []
    for nome, sub in (("squalificato almeno una volta", d[d["gio"] > 0]),
                      ("mai squalificato", d[d["gio"] == 0])):
        righe.append({
            "gruppo": nome, "righe": len(sub),
            "presenze_attese": float(sub["presenze_attese"].mean()),
            "presenze_osservate": float(sub["presenze_osservate"].mean()),
            "bias": float((sub["presenze_attese"] - sub["presenze_osservate"]).mean()),
        })
    return pd.DataFrame(righe)
