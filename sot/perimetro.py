# -*- coding: utf-8 -*-
"""Fase 10 / Blocco R0 — il perimetro di cio' che e' validabile.

**Non stima niente.** Non c'e' un fit, un bersaglio, un iperparametro. Questo
modulo *conta*, e conta una cosa sola: quali partite hanno una previsione su
**entrambi** i lati, che e' la condizione perche' di quella partita esista una
distribuzione del risultato.

**Perche' esiste come modulo e non come script.** La definizione di «partita
validabile» e' usata da R1 (che ci costruisce sopra la congiunta), da R2 (che ci
misura RPS e log-loss) e da R3 (che ci simula la classifica). Tre copie della
stessa condizione sono tre occasioni di farle divergere senza accorgersene: e' la
ragione per cui la definizione di tiro in porta sta in `shots.py` e nessun altro
posto. Qui vale lo stesso.

**La riga e' la PARTITA, non la squadra-partita.** E' il cambio di granularita'
che separa la Fase 9 da questa: E3 modella `gol_fatti` di una squadra contro un
avversario, e le sue righe sono 3.478; un esito 1X2 non esiste finche' i due lati
non stanno sulla stessa riga. `partite()` fa quella rotazione e **verifica** che
ogni partita abbia esattamente due lati, invece di assumerlo.

Tre cose che questo modulo dichiara e che non erano scritte da nessuna parte:

1. **`eligible` equivale a `team_match_idx >= 6`**, ed e' una proprieta' della
   SQUADRA, non della partita. Ne segue che una partita puo' avere un lato
   eligible e l'altro no, e succede: vedi `disallineamenti()`.
2. **`team_match_idx` non e' la giornata** (gia' noto dal Blocco 0), e per R3 la
   differenza conta perche' una classifica si costruisce per turni. La giornata
   vera arriva dall'aggancio della Fase 8, che ha chiuso la D6.
3. **L'esito osservato e' disponibile da DUE fonti indipendenti** — i gol
   ricomposti da WhoScored (verificati 3.778/3.778 contro `matches.json` in E3) e
   il punteggio della fonte dei voti. `verifica_esito()` le mette una contro
   l'altra: e' il vincolo 7 applicato a costo zero, e sulla grandezza che R2
   userebbe come bersaglio.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from . import config

#: La soglia di burn-in del walk-forward, **osservata e non imposta qui**.
#: `validate.date_splits` pretende 30 partite di training prima di produrre una
#: previsione valutabile; con 10 partite per turno sono tre turni, e le prime tre
#: giornate non compaiono affatto nel derivato di E3. Le giornate 4 e 5 hanno una
#: previsione ma non sono `eligible`. Il numero e' verificato da
#: `verifica_soglia_eligible()`, che fallisce se la relazione cambia.
IDX_ELIGIBLE = 6

#: L'aggancio partite della Fase 8: e' cio' che porta la **giornata** vera.
#: Sta in `data/mapping/` e non sotto `processed/` perche' e' una mappa fra due
#: fonti, non un derivato rigenerabile da una sola.
MAPPA_PARTITE = config.DATA / "mapping" / "aggancio_partite.csv"


def _walkforward() -> pd.DataFrame:
    """Il walk-forward dei gol di E3, letto e basta. Non lo ricalcola."""
    from . import difesa

    return difesa.walkforward_gol()


def partite(stagioni=None) -> pd.DataFrame:
    """Una riga per PARTITA, con i due lambda affiancati e l'esito osservato.

    La rotazione da squadra-partita a partita e' il contributo del blocco. Due
    controlli la accompagnano, e nessuno dei due e' decorativo:

    - **ogni partita ha esattamente due lati**, altrimenti `lam_casa` e
      `lam_trasferta` verrebbero da un `groupby` che sceglie in silenzio;
    - **`is_home` e' 1 su un lato e 0 sull'altro**. Se fosse costante — e su una
      fonte che non ha i nomi delle squadre nei CSV non e' un'ipotesi assurda —
      casa e trasferta si scambierebbero senza che nessun totale se ne accorga.
    """
    wf = _walkforward()
    if stagioni is not None:
        wf = wf[wf["stagione"].isin(list(stagioni))]

    n = wf.groupby(["stagione", "matchId"]).size()
    if not (n == 2).all():
        rotte = n[n != 2]
        raise ValueError(
            f"{len(rotte)} partite non hanno due lati: {rotte.head().to_dict()}. "
            "La rotazione a livello partita non e' definita."
        )
    casa_per_partita = wf.groupby(["stagione", "matchId"])["is_home"].sum()
    if not (casa_per_partita == 1).all():
        raise ValueError(
            "esistono partite senza esattamente un lato di casa: `is_home` non "
            "distingue i due lati e casa/trasferta sarebbero intercambiabili"
        )

    c = wf[wf["is_home"] == 1].set_index(["stagione", "matchId"])
    t = wf[wf["is_home"] == 0].set_index(["stagione", "matchId"])

    out = pd.DataFrame({
        "data": c["date"],
        "casa": c["team"],
        "trasferta": t["team"],
        "lam_casa": c["lam"],
        "lam_trasferta": t["lam"],
        "idx_casa": c["team_match_idx"],
        "idx_trasferta": t["team_match_idx"],
        "elig_casa": c["eligible"].astype(bool),
        "elig_trasferta": t["eligible"].astype(bool),
        "gol_casa": c["gol_fatti"],
        "gol_trasferta": t["gol_fatti"],
    })

    # `lam_subiti` di E3 e' il lambda dell'avversario nella stessa partita: dopo
    # la rotazione dev'essere ridondante, e verificarlo e' gratis. Se non lo
    # fosse, l'accoppiamento casa/trasferta sarebbe sbagliato.
    #
    # **Il confronto e' allineato sull'indice, non sull'ordine delle righe.** Un
    # `to_numpy()` su due Series con indici diversi le confronterebbe per
    # posizione, che e' il modo silenzioso di far passare un accoppiamento
    # sbagliato — o, come e' successo scrivendo questo modulo, di far fallire un
    # accoppiamento giusto.
    atteso = c["lam_subiti"].reindex(out.index)
    if not np.allclose(atteso.to_numpy(), out["lam_trasferta"].to_numpy(),
                       equal_nan=True):
        raise ValueError(
            "`lam_subiti` del lato di casa non coincide con `lam` della "
            "trasferta: la rotazione ha accoppiato le squadre sbagliate"
        )

    out = out.reset_index()

    # **La condizione del blocco.** Serve che ENTRAMBI i lati siano eligible:
    # un esito 1X2 non e' meta' previsto.
    out["validabile"] = out["elig_casa"] & out["elig_trasferta"]

    out["esito"] = np.select(
        [out["gol_casa"] > out["gol_trasferta"],
         out["gol_casa"] == out["gol_trasferta"]],
        ["1", "X"], default="2",
    )
    out["gol_totali"] = out["gol_casa"] + out["gol_trasferta"]

    return out.merge(_giornate(), on=["stagione", "matchId"], how="left")


def _giornate() -> pd.DataFrame:
    """La giornata vera, dall'aggancio della Fase 8 (D6).

    `team_match_idx` **non e' la giornata**: numera le partite presenti nei dati,
    quindi su una squadra a cui la fonte ne ha perse tre scorre indietro di tre.
    E' lo stesso difetto che E2 ha trovato sulle squalifiche, e per R3 sarebbe
    peggio: una classifica costruita su un indice che salta i recuperi mette la
    stessa squadra in due turni diversi.
    """
    a = pd.read_csv(MAPPA_PARTITE)
    a = a[a["matchId"].notna()].copy()
    a["matchId"] = a["matchId"].astype("int64")
    return a[["stagione", "matchId", "giornata",
              "gol_casa", "gol_trasferta"]].rename(
        columns={"gol_casa": "gol_casa_voti", "gol_trasferta": "gol_trasferta_voti"})


def cascata(p: pd.DataFrame = None) -> pd.DataFrame:
    """Dal grezzo acquisito alle partite validabili, un gradino per volta.

    E' la tabella che il blocco esiste per produrre: **dove si perdono le
    partite, e perche'**. Ogni gradino ha una causa diversa e le tre non vanno
    sommate come se fossero la stessa cosa.
    """
    p = partite() if p is None else p
    from . import multistagione as MS

    # L'universo acquisito si **conta** da `team_match`, non si assume a 380: il
    # calendario 2022-23 ne ha 381 (il playout) e WhoScored ne ha perse 12, che
    # sono due scarti di segno opposto e nessuno dei due e' ipotizzabile.
    tm = MS.carica("team_match")
    acquisite = tm.groupby("stagione")["matchId"].nunique()

    righe = []
    for st in config.SEASONS_STORICHE:
        d = p[p["stagione"] == st]
        n_acq = int(acquisite.get(st, 0))
        righe.append({
            "stagione": st,
            "acquisite": n_acq,
            "senza_training": n_acq - len(d),
            "con_previsione": len(d),
            "perse_burnin": int((~d["validabile"]).sum()),
            "validabili": int(d["validabile"].sum()),
        })
    return pd.DataFrame(righe)


def struttura_giornate(p: pd.DataFrame = None) -> pd.DataFrame:
    """Quante giornate sono PIENE, cioe' con tutte e dieci le partite validabili.

    E' il numero che R3 usa e che R2 non usa: una metrica per partita non ha
    bisogno che il turno sia completo, una **classifica** si'. Una giornata a cui
    manca una partita non e' un turno simulabile senza dichiarare cosa si fa del
    buco.
    """
    p = partite() if p is None else p
    d = p[p["giornata"].notna()]
    g = d.groupby(["stagione", "giornata"])["validabile"].agg(["size", "sum"])
    g["piena"] = (g["size"] == 10) & (g["sum"] == 10)

    righe = []
    for st, sub in g.groupby(level=0):
        piene = sub[sub["piena"]]
        non_piene = sorted(int(x) for x in sub[~sub["piena"]].index.get_level_values(1))
        righe.append({
            "stagione": st,
            "giornate_con_previsione": len(sub),
            "giornate_piene": int(sub["piena"].sum()),
            "prima_piena": int(piene.index.get_level_values(1).min()) if len(piene) else None,
            "non_piene": ", ".join(str(x) for x in non_piene),
        })
    return pd.DataFrame(righe)


def disallineamenti(p: pd.DataFrame = None) -> pd.DataFrame:
    """Le partite con un lato eligible e l'altro no.

    Non sono una curiosita': sono la prova che `eligible` e' una proprieta' della
    squadra e non della partita, e **cadono dove la perdita alla fonte non e'
    casuale**. Le due del 2021-22 coinvolgono l'Atalanta, che e' la squadra a cui
    WhoScored ha perso sei partite — la stessa non-casualita' che
    `reports/phase7_acquisizione_whoscored.md` ha dichiarato e non spiegato.
    """
    p = partite() if p is None else p
    d = p[p["elig_casa"] != p["elig_trasferta"]].copy()
    # La data si formatta qui: nel report l'orario e' rumore, e `00:00:00` in
    # tabella suggerisce una precisione che il dato non ha.
    d["data"] = pd.to_datetime(d["data"]).dt.strftime("%Y-%m-%d")
    # Il lato **in ritardo**, che e' cio' che si vuole leggere: e' la squadra a
    # cui la fonte ha perso partite, e nominarla rende l'affermazione
    # falsificabile invece che allusiva.
    d["in_ritardo"] = np.where(d["elig_casa"], d["trasferta"], d["casa"])
    return d[["stagione", "data", "giornata", "casa", "trasferta",
              "idx_casa", "idx_trasferta", "in_ritardo"]]


def verifica_soglia_eligible(p: pd.DataFrame = None) -> dict:
    """`eligible` equivale a `team_match_idx >= IDX_ELIGIBLE`? Falsificabile.

    Se un blocco futuro cambiasse il burn-in, ogni conteggio pubblicato qui
    diventerebbe falso in silenzio. Questa e' la riga che lo impedisce.
    """
    wf = _walkforward()
    atteso = wf["team_match_idx"] >= IDX_ELIGIBLE
    ok = bool((wf["eligible"].astype(bool) == atteso).all())
    return {"soglia": IDX_ELIGIBLE, "coincide": ok,
            "discordanti": int((wf["eligible"].astype(bool) != atteso).sum())}


def verifica_esito(p: pd.DataFrame = None) -> dict:
    """Il punteggio di WhoScored contro quello della fonte dei voti (vincolo 7).

    **E' il bersaglio di R2**, quindi vale la pena saperlo prima e non dopo. Le
    due derivazioni sono indipendenti: una ricompone i gol dagli eventi (con gli
    autogol riattribuiti, che `shots_mask` esclude), l'altra li legge da una
    pagina che non ha mai visto un evento.
    """
    p = partite() if p is None else p
    d = p[p["gol_casa_voti"].notna() & p["gol_trasferta_voti"].notna()].copy()
    conc_casa = d["gol_casa"] == d["gol_casa_voti"]
    conc_tras = d["gol_trasferta"] == d["gol_trasferta_voti"]
    conc = conc_casa & conc_tras

    esito_voti = np.select(
        [d["gol_casa_voti"] > d["gol_trasferta_voti"],
         d["gol_casa_voti"] == d["gol_trasferta_voti"]],
        ["1", "X"], default="2",
    )
    return {
        "confrontabili": len(d),
        "senza_giornata": int(p["giornata"].isna().sum()),
        "punteggio_identico": int(conc.sum()),
        "punteggio_discorde": int((~conc).sum()),
        "esito_identico": int((d["esito"].to_numpy() == esito_voti).sum()),
        "esito_discorde": int((d["esito"].to_numpy() != esito_voti).sum()),
    }


#: Il calendario COMPLETO, dalla fonte dei voti: 380 partite per stagione, gol
#: mai nulli. E' cio' che rende rispondibile la domanda sulle mancanti — di una
#: partita che WhoScored non ha, il **risultato** ce l'abbiamo lo stesso.
CALENDARIO = config.processed_league_dir() / "fantacalcio_partite.parquet"


def _calendario_lungo() -> pd.DataFrame:
    """Una riga per squadra-partita su TUTTO il calendario, con `acquisita`.

    La forma lunga serve perche' la domanda e' per squadra: «delle partite che
    mancano **a questa squadra**, quante erano vittorie».
    """
    cal = pd.read_parquet(CALENDARIO)
    ag = pd.read_csv(MAPPA_PARTITE)
    agganciate = set(zip(ag["stagione"], ag["partita_id"]))

    righe = []
    for r in cal.itertuples(index=False):
        acq = (r.stagione, r.partita_id) in agganciate
        for team, avv, gf, gs, casa in (
            (r.casa, r.trasferta, r.gol_casa, r.gol_trasferta, 1),
            (r.trasferta, r.casa, r.gol_trasferta, r.gol_casa, 0),
        ):
            righe.append({
                "stagione": r.stagione, "giornata": r.giornata, "team": team,
                "avversario": avv, "casa": casa, "acquisita": acq,
                "gf": gf, "gs": gs,
                "punti": 3 if gf > gs else (1 if gf == gs else 0),
                "esito": "V" if gf > gs else ("P" if gf == gs else "S"),
            })
    return pd.DataFrame(righe)


def partite_mancanti() -> pd.DataFrame:
    """Le partite del calendario che WhoScored non ha, **con il loro risultato**.

    Sono le 12 gia' dichiarate da `reports/phase7_acquisizione_whoscored.md` come
    `matchCentreData: null`. La novita' non e' quali siano: e' che il risultato si
    puo' leggere dall'altra fonte, quindi la domanda «mancano a caso rispetto
    all'esito?» ha una risposta invece di essere retorica.
    """
    cal = pd.read_parquet(CALENDARIO)
    ag = pd.read_csv(MAPPA_PARTITE)
    agganciate = set(zip(ag["stagione"], ag["partita_id"]))
    m = cal[[(s, p) not in agganciate
             for s, p in zip(cal["stagione"], cal["partita_id"])]]
    return m[["stagione", "giornata", "casa", "trasferta",
              "gol_casa", "gol_trasferta"]].reset_index(drop=True)


def _medie_permutate(v: np.ndarray, k: int, repliche: int,
                     rng, blocco: int = 25000) -> np.ndarray:
    """Medie di `repliche` campioni di `k` elementi da `v`, senza reinserimento.

    Vettorizzata: l'estrazione senza reinserimento e' l'`argsort` di una matrice
    di uniformi, quindi le `repliche` si fanno in una volta invece che in un
    ciclo Python. A blocchi perche' la matrice intera sarebbe centinaia di MB.

    **Il ciclo ingenuo costava 58 s per chiamata**, e la funzione che la usa
    veniva invocata quattro volte dai test: era il 90% del tempo del modulo.
    """
    fuori = np.empty(repliche)
    n = len(v)
    for i in range(0, repliche, blocco):
        m = min(blocco, repliche - i)
        idx = np.argsort(rng.random((m, n)), axis=1)[:, :k]
        fuori[i:i + m] = v[idx].mean(axis=1)
    return fuori


def casualita_mancanti(min_mancanti: int = 2, repliche: int = 200000,
                       seed: int = None) -> pd.DataFrame:
    """Le partite mancanti sono a caso rispetto al risultato? Per squadra.

    **Non e' la domanda a cui l'acquisizione ha gia' risposto.** Li' si era
    chiesto se le partite mancassero a caso rispetto alla **squadra** (no:
    l'Atalanta ne perde sei contro un'attesa di 1,2, p corretto 1,1%). Qui si
    chiede, data la squadra, se manchino a caso rispetto all'**esito** — cioe' se
    la fonte abbia perso sistematicamente vittorie, o partite in trasferta.

    Il test e' una **permutazione esatta**: sotto il nullo le partite mancanti
    sono un campione casuale senza reinserimento di quelle che la squadra ha
    giocato in quelle stagioni. Due code, perche' il verso non era previsto.

    Si testa su quattro grandezze e non su una: i **punti** sono cio' che la
    domanda nomina, ma **i gol sono cio' che il modello usa** — e le due possono
    divergere, perche' i punti sono una funzione a gradini dei gol.
    """
    rng = np.random.default_rng(config.SEED if seed is None else seed)
    L = _calendario_lungo()
    mancanti = L[~L["acquisita"]]

    righe = []
    for t, sub in mancanti.groupby("team"):
        if len(sub) < min_mancanti:
            continue
        stag = sorted(sub["stagione"].unique())
        tot = L[(L["team"] == t) & (L["stagione"].isin(stag))]
        riga = {"squadra": t, "mancanti": len(sub), "giocate": len(tot),
                "record": "".join(f"{e}{int((sub['esito'] == e).sum())}"
                                  for e in ("V", "P", "S"))}
        for col in ("punti", "gf", "gs", "casa"):
            v = tot[col].to_numpy()
            oss = float(sub[col].mean())
            sim = _medie_permutate(v, len(sub), repliche, rng)
            riga[f"{col}_oss"] = oss
            riga[f"{col}_atteso"] = float(v.mean())
            riga[f"{col}_p"] = float(
                (np.abs(sim - v.mean()) >= abs(oss - v.mean())).mean())
        righe.append(riga)

    out = pd.DataFrame(righe).sort_values("mancanti", ascending=False)
    return out.reset_index(drop=True)


def mde_mancanti(squadra: str = "Atalanta", col: str = "gf",
                 repliche: int = 200000, seed: int = None) -> dict:
    """Quale scarto sarebbe stato visibile, con sei partite. Potenza dichiarata.

    E' la lezione della 6D: un `p` sopra soglia non dice che l'effetto sia zero
    finche' non si sa quanto grande dovesse essere per essere visto. Con `n = 6`
    la risposta e' «molto», e va scritta accanto al risultato.
    """
    rng = np.random.default_rng(config.SEED if seed is None else seed)
    L = _calendario_lungo()
    sub = L[(~L["acquisita"]) & (L["team"] == squadra)]
    stag = sorted(sub["stagione"].unique())
    tot = L[(L["team"] == squadra) & (L["stagione"].isin(stag))]

    v = tot[col].to_numpy()
    sim = _medie_permutate(v, len(sub), repliche, rng)
    q = float(np.quantile(sim, 0.975))
    return {"squadra": squadra, "grandezza": col, "n_mancanti": int(len(sub)),
            "atteso": float(v.mean()), "soglia_975": q,
            "mde": q - float(v.mean()),
            "osservato": float(sub[col].mean()) - float(v.mean())}


def realizzazioni(p: pd.DataFrame = None) -> pd.DataFrame:
    """L'unita' di validazione di ogni affermazione, e quante ne esistono.

    E' la tabella che decide l'ordine fra G1 e G2, e sta nel codice invece che
    solo nel report perche' e' un **conteggio**, non un'opinione. Una probabilita'
    di scudetto ha una realizzazione per stagione: cinque stagioni sono cinque
    estrazioni, e nessuna metrica calcolata su cinque punti separa un modello da
    un altro.
    """
    p = partite() if p is None else p
    val = p[p["validabile"]]
    return pd.DataFrame([
        {"affermazione": "1X2 (RPS, log-loss, calibrazione)",
         "unita": "partita", "n": int(len(val)), "blocco": "R2"},
        {"affermazione": "over/under sulla linea dei gol",
         "unita": "partita", "n": int(len(val)), "blocco": "R2"},
        {"affermazione": "classifica: scudetto, Europa, retrocessione",
         "unita": "**stagione**", "n": int(val["stagione"].nunique()), "blocco": "R3"},
        {"affermazione": "generalizzazione fra campionati",
         "unita": "campionato", "n": 1, "blocco": "G2"},
    ])
