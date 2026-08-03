# -*- coding: utf-8 -*-
"""Presenza fantacalcistica: chi riceve un voto, e la regola dell'80' misurata.

`docs/regole_fantacalcio.md` §1.2 distingue due grandezze che il repository
teneva separate senza poterle confrontare:

| grandezza | definizione | dove sta |
| --- | --- | --- |
| **presenza fantacalcistica** | giornate in cui il giocatore riceve un voto numerico | i voti, dalla Fase 8 |
| minuti giocati | minuti effettivi in campo | `sot/minutes.py`, dalla Fase 1 |

Il bersaglio del modello e' la **prima**; i minuti ne sono un predittore, non un
sostituto. Adesso che l'aggancio esiste (`sot/aggancio.py`) le due stanno sulla
stessa riga, e la regola dell'80' — decisa dall'utente per la **proiezione**
2026-27 e marcata `[DA MISURARE]` — si puo' finalmente falsificare.

## Cosa si misura, e perche' solo qui

> `[DECISO dall'utente]` per la proiezione si assume s.v. a chi entra al minuto
> ≥ 80', su `expandedMinute`, e la regola e' la stessa su tutte e cinque le
> stagioni.

La regola e' falsificabile **su una stagione sola**, la 2025-26: e' l'unica in
cui coesistono i minuti WhoScored e l's.v. osservato. Le altre quattro hanno i
voti ma non i minuti, e misurarci sopra vorrebbe dire inventare il predittore.

Si misura l'errore **nei due versi**, come §1.2 chiede, e i due non sono
intercambiabili:

- **falso s.v.**: entra al ≥ 80' e il voto invece lo prende. La regola gli toglie
  una presenza che c'e';
- **s.v. mancato**: entra prima dell'80' e il voto non lo prende. La regola gli
  attribuisce una presenza che non c'e'.

## Il limite che viene prima del numero

**Sulla scala Redazione l's.v. non e' una funzione dei minuti, e la fonte lo
dichiara**: "Non esiste, e mai esisterà, una regola che prevede che il voto
venga dato a chi gioca un numero minimo di minuti". Quindi il tasso d'errore
misurato qui **non e' l'errore di una stima di una soglia vera**: e' la distanza
fra una regola meccanica e una decisione editoriale che regola non ha. Un
tasso d'errore basso non dimostra che la soglia esista; dice solo che la
discrezionalita' del pagellista, in media, ci somiglia.

Ne segue che il numero da riportare accanto a ogni stima non e' "la regola e'
giusta al 90%" ma **quante righe la regola sposta e in che verso**.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from sot import aggancio as AG, config, io_events, minutes as M, voti as V

SOGLIA_SV = 80.0          # `[DECISO dall'utente]`, su expandedMinute
TAVOLA_PARQUET = (config.processed_league_dir()
                  / f"presenza_{AG.STAGIONE_CON_ENTRAMBE}.parquet")


def tavola(stagione: str = AG.STAGIONE_CON_ENTRAMBE, force: bool = False) -> pd.DataFrame:
    """Una riga per giocatore-partita, con il voto **e** i minuti.

    L'universo e' **chi e' sceso in campo**, che e' l'universo della fonte dei
    voti: i panchinari non utilizzati non hanno riga li', e aggiungerli qui
    dichiarerebbe un s.v. che nessuno ha osservato.

    Sono 11.926 righe contro le 11.928 che `minutes_played` conta con almeno un
    minuto, e **le due che mancano non sono un difetto dell'aggancio**: la fonte
    dei voti non elenca affatto Estevez (entrato al 90', 7 minuti) e Folino
    (entrato all'88', 10 minuti). Non gli da' s.v.: non gli da' riga. E' un terzo
    stato oltre "voto" e "s.v.", che per il modello ricade nel secondo — chi non
    e' elencato non prende voto — ma che va saputo, perche' significa che
    l'universo dei voti e' *quasi* e non *esattamente* chi e' sceso in campo.
    """
    if TAVOLA_PARQUET.is_file() and not force:
        return pd.read_parquet(TAVOLA_PARQUET)

    part = AG.mappa_partite(stagioni=[stagione])["partite"]
    gioc = AG.mappa_giocatori(stagione)["mappa"]

    fc = V.carica()
    fc = fc[(fc["stagione"] == stagione) & (~fc["allenatore"])].copy()
    fc["matchId"] = fc["partita_id"].map(part.set_index("partita_id")["matchId"])
    chiave = gioc.set_index(["teamId_ws", "giocatore_id_fc"])["playerId_ws"]
    verso_ws = AG.mappa_squadre([stagione]).set_index(
        ["stagione", "squadra_id_fc"])["teamId_ws"]
    fc["teamId"] = [verso_ws.get((stagione, int(t))) for t in fc["squadra_id"]]
    fc["playerId"] = [chiave.get((t, int(g))) if pd.notna(g) else None
                      for t, g in zip(fc["teamId"], fc["giocatore_id"])]

    mins = M.minutes_played(io_events.load_lineup_events(), io_events.load_events())
    mins = mins[mins["minutes"] > 0][
        ["matchId", "teamId", "playerId", "is_starter", "start_min", "end_min",
         "minutes", "maxMinute"]]

    out = fc.merge(mins, on=["matchId", "teamId", "playerId"], how="left")
    out["sv_osservato"] = out["voto_redazione"].isna()
    # La regola dell'utente, applicata: s.v. a chi entra al ≥ 80'. I titolari
    # hanno `start_min` 0 e non ricadono mai nella regola — ed e' il suo limite
    # strutturale, non un errore di campionamento (vedi `titolari_usciti_presto`).
    out["sv_proiettato"] = out["start_min"] >= SOGLIA_SV
    TAVOLA_PARQUET.parent.mkdir(parents=True, exist_ok=True)
    out.to_parquet(TAVOLA_PARQUET, index=False)
    return out


def _matrice(t: pd.DataFrame) -> pd.DataFrame:
    dentro = t[t["start_min"].notna()]
    n = len(dentro)
    vp = int((dentro["sv_proiettato"] & dentro["sv_osservato"]).sum())
    fp = int((dentro["sv_proiettato"] & ~dentro["sv_osservato"]).sum())
    fn = int((~dentro["sv_proiettato"] & dentro["sv_osservato"]).sum())
    vn = int((~dentro["sv_proiettato"] & ~dentro["sv_osservato"]).sum())
    return pd.DataFrame([{
        "righe": n,
        "sv_osservati": vp + fn, "sv_proiettati": vp + fp,
        "concordi": vp + vn, "quota_concordi": round((vp + vn) / n, 4) if n else np.nan,
        "falsi_sv": fp, "sv_mancati": fn,
        "quota_falsi_sv": round(fp / (vp + fp), 4) if (vp + fp) else np.nan,
        "quota_sv_mancati": round(fn / (vn + fn), 4) if (vn + fn) else np.nan,
        "richiamo": round(vp / (vp + fn), 4) if (vp + fn) else np.nan,
    }])


def misura_regola(t: pd.DataFrame = None) -> dict:
    """La regola dell'80' contro l's.v. osservato, con i baseline accanto.

    **I baseline non sono un ornamento** (vincolo 6): senza, "l'88% di accordo"
    non significa niente, perche' dire "nessuno prende s.v." ne azzecca gia'
    il 90%. Il confronto giusto e' con le due regole stupide che esistono:
    *nessun s.v.* e *s.v. a tutti i subentrati*.
    """
    t = tavola() if t is None else t
    dentro = t[t["start_min"].notna()].copy()

    righe = []
    for nome, previsione in (
        ("regola 80' (utente)", dentro["start_min"] >= SOGLIA_SV),
        ("baseline: nessun s.v.", pd.Series(False, index=dentro.index)),
        ("baseline: s.v. a ogni subentrato", ~dentro["is_starter"].astype(bool)),
    ):
        m = _matrice(dentro.assign(sv_proiettato=previsione))
        righe.append({"regola": nome, **m.iloc[0].to_dict()})
    return {"confronto": pd.DataFrame(righe),
            "per_ingresso": _per_ingresso(dentro),
            "sensibilita": sensibilita_soglia(dentro),
            "titolari": titolari_usciti_presto(dentro)}


def _per_ingresso(t: pd.DataFrame) -> pd.DataFrame:
    """Dove sta l'errore: sui titolari o sui subentrati, e in quale verso."""
    t = t.copy()
    t["gruppo"] = np.where(t["is_starter"].astype(bool), "titolare", "subentrato")
    g = t.groupby("gruppo")
    return pd.DataFrame({
        "righe": g.size(),
        "sv_osservati": g["sv_osservato"].sum(),
        "sv_proiettati": g["sv_proiettato"].sum(),
        "falsi_sv": g.apply(lambda d: int((d["sv_proiettato"] & ~d["sv_osservato"]).sum()),
                            include_groups=False),
        "sv_mancati": g.apply(lambda d: int((~d["sv_proiettato"] & d["sv_osservato"]).sum()),
                              include_groups=False),
    }).reset_index()


def sensibilita_soglia(t: pd.DataFrame, soglie=range(60, 96, 5)) -> pd.DataFrame:
    """La soglia e' scelta, non stimata: qui si mostra cosa costerebbe muoverla.

    Il Blocco 0 aveva gia' misurato che l'80' cade **nel punto di massima
    densita' degli ingressi**, quindi e' la posizione in cui la regola e' piu'
    sensibile alla propria scelta. Questa tavola dice di quanto.
    """
    fuori = []
    for s in soglie:
        m = _matrice(t.assign(sv_proiettato=t["start_min"] >= s))
        fuori.append({"soglia": s, **m.iloc[0].to_dict()})
    return pd.DataFrame(fuori)


def titolari_usciti_presto(t: pd.DataFrame, limiti=(10, 20, 30)) -> pd.DataFrame:
    """Il verso d'errore **strutturale** che la regola non prevede.

    Un titolare uscito al 15' per infortunio puo' prendere s.v., e la regola —
    che guarda solo il minuto d'**ingresso** — non lo vedra' mai. Non e' errore
    di campionamento: e' una classe di casi fuori dal dominio della regola, e
    §1.2 non la elenca fra i due versi da misurare. La si misura lo stesso,
    perche' non misurarla la farebbe sparire.
    """
    tit = t[t["is_starter"].astype(bool)]
    fuori = []
    for lim in limiti:
        sel = tit[tit["end_min"] < lim]
        fuori.append({
            "uscito_prima_del": lim, "titolari": len(sel),
            "di_cui_sv": int(sel["sv_osservato"].sum()),
            "quota_sv": round(sel["sv_osservato"].mean(), 4) if len(sel) else np.nan,
        })
    return pd.DataFrame(fuori)


def regola_sui_minuti_giocati(t: pd.DataFrame = None, soglie=range(10, 41, 5)) -> pd.DataFrame:
    """La stessa regola scritta sui **minuti giocati** invece che sull'ingresso.

    **Non e' la regola dell'utente e non la sostituisce.** §1.2 fissa la forma —
    minuto d'ingresso ≥ 80' su `expandedMinute` — e quella resta finche' l'utente
    non decide altro. Questa tavola e' nata da un sospetto: la quota di s.v.
    crolla a **zero esatto sopra i 30 minuti giocati** (8.552 righe), quindi i
    minuti giocati sembravano la variabile piu' netta delle due.

    **Il sospetto e' stato misurato ed e' risultato infondato**, ed e' il motivo
    per cui la tavola resta qui invece di diventare una proposta: al suo optimum
    (20 minuti) la regola sui minuti giocati fa **0,9783** di accordo contro
    **0,9784** della regola dell'utente. Sono la stessa cosa. Cambia il *mix*
    degli errori, non la loro quantita': la forma sui minuti prende quasi tutti
    gli s.v. veri (richiamo 0,97 contro 0,90) e in cambio ne inventa di piu'
    (225 falsi contro 142). Quale dei due errori pesi di piu' e' una domanda di
    prodotto, non di statistica, e non la decido io.

    Le due forme si separano dove un subentrato esce: chi entra al 70' ed esce
    all'85' ha giocato 15 minuti, e la regola sull'ingresso lo dichiara presente.
    """
    t = tavola() if t is None else t
    dentro = t[t["minutes"].notna()].copy()
    fuori = []
    for s in soglie:
        m = _matrice(dentro.assign(sv_proiettato=dentro["minutes"] < s))
        fuori.append({"soglia_minuti": s, **m.iloc[0].to_dict()})
    return pd.DataFrame(fuori)


def minuti_e_sv(t: pd.DataFrame = None, passo: int = 10) -> pd.DataFrame:
    """Quota di s.v. per scaglione di minuti giocati.

    E' la forma della relazione che la regola approssima con un gradino. Se la
    fonte dice il vero — nessuna soglia — questa curva scende in modo graduale
    invece di crollare in un punto, e si vede qui.
    """
    t = tavola() if t is None else t
    t = t[t["minutes"].notna()].copy()
    bordi = list(range(0, 100 + passo, passo))
    t["scaglione"] = pd.cut(t["minutes"], bins=bordi, right=False)
    g = t.groupby("scaglione", observed=True)
    out = pd.DataFrame({"righe": g.size(), "sv": g["sv_osservato"].sum()})
    out["quota_sv"] = (out["sv"] / out["righe"]).round(4)
    return out.reset_index().astype({"scaglione": str})
