# -*- coding: utf-8 -*-
"""Fase 12 / Blocco V4 — il ponte: `previsione(squadra, avversario, campo)`.

**E' cio' che l'utente ha chiesto**: dato in ingresso una squadra, un avversario
e il campo, la distribuzione del numero di tiri. Prima di questo blocco il
progetto non aveva una funzione del genere per una squadra qualsiasi:
`soglie_2627` la aveva per il **solo Como** e per il **solo 2026-27**, ancorata a
un livello fornito dall'utente che per le altre diciannove squadre non esiste.

Qui il livello non serve: la previsione e' **within-season**, cioe' il modello
sa gia' quanto tira ciascuna squadra perche' gliel'hanno detto le partite
precedenti. E' anche l'unica forma **validabile**, ed e' validata — V1 la misura
su 3.278 righe reali.

TRE DECISIONI DI DISEGNO CHE CONTANO
------------------------------------
1. **`al` non e' cosmetico.** E' la data a cui ci si mette: il modello si stima
   sulle sole partite **precedenti**, ed e' cio' che rende la previsione fuori
   campione. Se la partita chiesta e' gia' dentro la storia usata, il campo
   `dentro_campione` lo **dichiara** invece di lasciar credere che sia una
   previsione.
2. **`campo` e' una stringa**, non un booleano. Un `0/1` si scambia senza
   rumore: nessun totale se ne accorgerebbe, e la differenza fra casa e trasferta
   vale il 26% del livello.
3. **La guardia sulla squadra sconosciuta sta a DUE livelli**, e servono
   entrambi: `verifica_squadre` all'ingresso e `TeamModel(strict_teams=True)`
   dentro. Una guardia sola all'API si aggira chiamando il modello direttamente,
   che e' esattamente il buco che `soglie_2627.difese_avversari` tappa per il solo
   Como.

CHE COSA QUESTO MODULO NON FA
-----------------------------
**Non produce quote e non valuta scommesse** (vincolo 3): nel repository non ci
sono prezzi di mercato, e le uniche ottenibili sarebbero generate da questo
stesso modello — il codice che lo faceva sta in `legacy/` con la spiegazione.
`quota_pareggio` e `guadagno_atteso` si **importano** da `soglie_2627` invece di
essere riscritti: una definizione in un posto solo, e il guadagno resta una
**funzione della quota fornita dall'utente**, mai di una quota inventata qui.

**Non usa la gerarchia di V2 per i tiri in porta.** V2 l'ha misurata e non l'ha
adottata: a parita' si tiene il modello con meno parti. `sot` viene quindi dal
modello **diretto**, che e' quello che la Fase 2 ha pubblicato.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from . import (config, dispersion as D, model_team as MT, tentativi as T,
               validate as V, volume as VL)

#: I due valori ammessi per `campo`. Stringhe e non booleani, di proposito.
CAMPI = ("casa", "trasferta")

#: I livelli degli intervalli di previsione riportati.
LIVELLI = (0.5, 0.8, 0.95)

#: Le linee Over sui **tiri in porta**. Sono `validate.LINES` **invariate**, e
#: non e' pigrizia: `tentativi.LINEE_SOT_INVARIATE` lo prescrive esplicitamente,
#: perche' inventarne di nuove renderebbe questi numeri non confrontabili con la
#: Fase 4, che e' il difetto contro cui esiste il vincolo 7.
LINEE_SOT = V.LINES


def storia(stagione: str | None = None,
           al: pd.Timestamp | str | None = None,
           league: str | None = None) -> pd.DataFrame:
    """Le partite disponibili al momento della previsione.

    `al` **esclusivo**: si usano le partite con data **strettamente minore**, la
    stessa regola di `walkforward.date_splits`. Includere la data corrente
    farebbe entrare nella stima la partita che si vuole prevedere, ed e' la forma
    piu' banale di leakage.
    """
    stagione = config.SEASONS_STORICHE[-1] if stagione is None else stagione
    u = T.universo([stagione], league=league)
    if al is None:
        return u
    al = pd.Timestamp(al)
    return u[u["date"] < al]


def verifica_squadre(note: set[str], squadra: str, avversario: str,
                     stagione: str) -> None:
    """Solleva **prima** di stimare, con il messaggio che serve a capire.

    Il caso vero non e' la squadra inventata: e' chiedere **Como-Cremonese nel
    2023-24**, dove la Cremonese non era in Serie A. Senza questa guardia il
    modello risponderebbe un numero perfettamente plausibile, ottenuto trattando
    la Cremonese come una squadra esattamente media.
    """
    if squadra == avversario:
        raise ValueError(f"squadra e avversario coincidono: {squadra!r}")
    ignote = [s for s in (squadra, avversario) if s not in note]
    if ignote:
        raise ValueError(
            f"squadre non presenti in {stagione}: {ignote}. "
            f"Presenti: {sorted(note)}")


def _verifica_campo(campo: str) -> bool:
    if campo not in CAMPI:
        raise ValueError(f"campo {campo!r} non ammesso: usare uno di {CAMPI}. "
                         "Un booleano 0/1 si scambierebbe senza rumore.")
    return campo == "casa"


def modello_alla_data(st: pd.DataFrame, alpha: float | None = None,
                      league: str | None = None,
                      contesto: dict | None = None) -> dict:
    """Stima i due modelli sulla storia data: volume e tiri in porta diretti.

    `alpha` non si sceglie qui guardando il risultato: il default e' la mediana
    degli alpha che il walk-forward di V1 ha scelto sul solo passato, che e' un
    valore gia' prodotto dalla procedura validata.

    **L'`alpha` viene dal walk-forward DI QUEL CAMPIONATO**, mai da un altro: i
    campionati non si poolano (regola di E1, riscritta da R0 proprio su G2), e la
    Fase 13 ha misurato che il livello dei gol varia del 25% fra i cinque. Un
    `alpha` italiano applicato alla Bundesliga sarebbe un iperparametro preso in
    prestito da una popolazione diversa.
    """
    if alpha is None:
        wf = VL.walkforward_tiri(league=league)
        alpha = float(wf.loc[wf["eligible"], "alpha"].median())

    teams = sorted(set(st["team"]) | set(st["opponent"]))

    # Il centro della penalita': zero (media di campionato) senza contesto,
    # i coefficienti dell'anno scorso con contesto. `alpha_prior` non si sceglie
    # qui: viene da `prior_stagione`, tarato sulle sole transizioni storiche.
    def _pri(t):
        c = (contesto or {}).get(t, {})
        p = c.get("prior")
        return (p.come_centro() if p is not None else None), c.get("alpha_prior")

    cen_v, ap_v = _pri(T.TARGET)
    cen_s, ap_s = _pri(T.TARGET_PRECISIONE)

    m_vol = MT.TeamModel(alpha=alpha, target=T.TARGET, strict_teams=True,
                         prior=cen_v, alpha_prior=ap_v).fit(st, teams=teams)
    m_sot = MT.TeamModel(alpha=alpha, target=T.TARGET_PRECISIONE,
                         strict_teams=True,
                         prior=cen_s, alpha_prior=ap_s).fit(st, teams=teams)
    return {"volume": m_vol, "sot": m_sot, "alpha": alpha, "teams": teams,
            "partite": int(st["matchId"].nunique()),
            "al": st["date"].max() if len(st) else None}


def _r_corrente(st: pd.DataFrame, lam_col: str = "lam",
                league: str | None = None, target: str = T.TARGET) -> float:
    """`r` della NB2, stimata sulle sole partite gia' giocate.

    Vincolo 1: `r` entra negli intervalli e nelle probabilita' Over, quindi
    stimarla sull'intera stagione la renderebbe non fuori campione. Ricade sul
    valore di V1 se la storia e' troppo corta per stimarla.

    **Una `r` per bersaglio e per campionato.** Sui tentativi vale ~20, sui tiri
    in porta ~26: sono due grandezze diverse e la seconda non si eredita dalla
    prima — e' la stessa ragione per cui V1 ha rifatto da capo la validazione
    invece di ereditarla dalla Fase 4.
    """
    wf = VL.walkforward_tiri(league=league, target=target)
    d = wf[wf["eligible"]]
    if len(st):
        d = d[d["date"] <= st["date"].max()]
    if len(d) < 60:
        # storia troppo corta per stimarla: si ricade su tutte le righe
        # valutabili di QUEL bersaglio e di QUEL campionato — mai su un numero
        # ereditato da un altro dei due, che e' il difetto contro cui il
        # parametro `target` esiste
        d = wf[wf["eligible"]]
    return float(D.fit_r(d[target].to_numpy(dtype=float), d[lam_col].to_numpy()))


def _p_over(lam: float, linee, r: float) -> pd.DataFrame:
    """`P(Over)` e quota di pareggio per una serie di linee.

    `quota_pareggio` si **importa** da `soglie_2627` invece di riscrivere
    `1.0/p`: una definizione in un posto solo. Fino alla Fase 14 la docstring di
    questo modulo lo dichiarava e il codice non lo faceva — erano due copie che
    coincidevano per caso, e il test verificava l'uguaglianza numerica invece
    dell'unicita'.
    """
    from . import soglie_2627 as S

    p = pd.DataFrame({
        "linea": list(linee),
        "p_over": [float(D.p_over(np.array([lam]), ln, r)[0]) for ln in linee],
    })
    p["quota_pareggio"] = S.quota_pareggio(p["p_over"].to_numpy())
    return p


def _intervalli(lam: float, r: float) -> pd.DataFrame:
    return pd.DataFrame({
        "livello": list(LIVELLI),
        "basso": [float(D.ppf((1 - l) / 2, np.array([lam]), r)[0])
                  for l in LIVELLI],
        "alto": [float(D.ppf(1 - (1 - l) / 2, np.array([lam]), r)[0])
                 for l in LIVELLI],
    })


#: Il nome dei due regimi. Stringhe e non booleani per la stessa ragione per cui
#: `campo` lo e': un `0/1` si scambia senza rumore, e qui la differenza fra i due
#: e' l'intera risposta nelle prime giornate.
REGIMI = ("prior (stagione precedente)", "within-season")


def _lambda(st: pd.DataFrame, riga: pd.DataFrame, n_squadra: int,
            league: str | None = None, contesto: dict | None = None):
    """I due lambda e il regime che li ha prodotti.

    **Senza `contesto` non cambia niente**: e' la strada di V4, within-season, e
    un test verifica l'identita' bit per bit.

    Con `contesto` (Fase 14 / A2) si applica la regola a due regimi:
    sotto `config.BURN_IN_ROUND` la stagione nuova non ha ancora abbastanza
    partite e il modello dell'anno scorso applicato **tale e quale** batte ogni
    miscela (misurato su 20 transizioni, t per cluster 4,4 sui tentativi e 4,2
    sui tiri in porta); da li' in su vince la miscela.
    """
    from . import prior_stagione as PS

    prossimo_idx = n_squadra + 1
    usa_prior = (contesto is not None
                 and prossimo_idx < config.BURN_IN_ROUND
                 and contesto.get(T.TARGET, {}).get("prior") is not None)

    if usa_prior:
        p_vol = contesto[T.TARGET]["prior"]
        p_sot = contesto[T.TARGET_PRECISIONE]["prior"]
        lam = float(PS.lam_dal_prior(p_vol, riga["team"], riga["opponent"],
                                     riga["is_home"])[0])
        lam_sot = float(PS.lam_dal_prior(p_sot, riga["team"], riga["opponent"],
                                         riga["is_home"])[0])
        return lam, lam_sot, REGIMI[0], None

    m = modello_alla_data(st, league=league, contesto=contesto)
    return (float(m["volume"].predict(riga)[0]),
            float(m["sot"].predict(riga)[0]), REGIMI[1], m)


def previsione(squadra: str, avversario: str, campo: str,
               stagione: str | None = None,
               al: pd.Timestamp | str | None = None,
               st: pd.DataFrame | None = None,
               linee=T.LINEE_TIRI,
               league: str | None = None,
               contesto: dict | None = None) -> dict:
    """La distribuzione dei tiri di `squadra` contro `avversario`, in `campo`.

    Ritorna anche i tiri in porta, dal modello **diretto**: V2 ha misurato la
    gerarchia e non l'ha adottata.

    Il campo `dentro_campione` e' `True` se la partita chiesta e' gia' fra quelle
    usate per stimare — nel qual caso **non e' una previsione** e il dizionario lo
    dice invece di lasciarlo intuire.
    """
    stagione = config.SEASONS_STORICHE[-1] if stagione is None else stagione
    in_casa = _verifica_campo(campo)
    st = storia(stagione, al, league=league) if st is None else st
    if not len(st):
        raise ValueError(f"nessuna partita disponibile in {stagione} prima di {al}")

    note = set(st["team"]) | set(st["opponent"])
    verifica_squadre(note, squadra, avversario, stagione)

    riga = pd.DataFrame([{"team": squadra, "opponent": avversario,
                          "is_home": int(in_casa)}])
    n_squadra = int((st["team"] == squadra).sum())

    lam, lam_sot, regime, m = _lambda(
        st, riga, n_squadra, league=league, contesto=contesto)
    r = _r_corrente(st, league=league)
    r_sot = _r_corrente(st, league=league, target=T.TARGET_PRECISIONE)

    # La partita chiesta e' gia' nella storia usata?
    tutte = T.universo([stagione], league=league)
    gia = tutte[(tutte["team"] == squadra) & (tutte["opponent"] == avversario)
                & (tutte["is_home"].astype(bool) == in_casa)]
    dentro = bool(len(gia) and gia["date"].min() <= st["date"].max())

    p_over = _p_over(lam, linee, r)
    p_over_sot = _p_over(lam_sot, LINEE_SOT, r_sot)

    intervalli = _intervalli(lam, r)
    intervalli_sot = _intervalli(lam_sot, r_sot)

    avvisi = []
    if dentro:
        avvisi.append("la partita chiesta e' GIA' nella storia usata per stimare: "
                      "questo non e' un numero fuori campione")
    if regime == REGIMI[0]:
        p = contesto[T.TARGET]["prior"]
        ignote = [s for s in (squadra, avversario) if s not in p.squadre()]
        avvisi.append(
            f"{squadra} ha {n_squadra} partite in {stagione}: sotto il burn-in di "
            f"{config.BURN_IN_ROUND} il numero viene dal modello di {p.stagione_origine} "
            "applicato tale e quale, non dalle partite di questa stagione")
        if ignote:
            avvisi.append(
                f"neopromosse senza storia: {ignote} — trattate come esattamente "
                f"medie di {p.stagione_origine}, che e' l'unico default onesto ma "
                "resta un'assunzione")
    elif n_squadra < config.BURN_IN_ROUND:
        avvisi.append(f"{squadra} ha solo {n_squadra} partite di storia, sotto il "
                      f"burn-in di {config.BURN_IN_ROUND}: la stima e' dominata "
                      "dall'intercetta")

    return {
        "squadra": squadra, "avversario": avversario, "campo": campo,
        "stagione": stagione,
        "campionato": config.LEAGUE if league is None else league,
        "lambda_tentativi": lam,
        "lambda_sot": lam_sot,
        "quota_in_porta_implicita": lam_sot / lam if lam > 0 else float("nan"),
        "r": r,
        "r_sot": r_sot,
        "regime": regime,
        "p_over": p_over,
        "p_over_sot": p_over_sot,
        "intervalli": intervalli,
        "intervalli_sot": intervalli_sot,
        "come_di": st["date"].max(),
        "partite_di_storia": int(st["matchId"].nunique()),
        "partite_della_squadra": n_squadra,
        "alpha": m["alpha"] if m else None,
        "dentro_campione": dentro,
        "avvisi": avvisi,
        "limiti": limiti(),
    }


def tabella_avversari(squadra: str, stagione: str | None = None,
                      al: pd.Timestamp | str | None = None,
                      league: str | None = None) -> pd.DataFrame:
    """`squadra` contro **tutti** gli avversari, in casa e in trasferta.

    E' la forma in cui la domanda dell'utente si legge meglio: non un numero,
    ma la dispersione fra avversari, che e' il motivo per cui un lambda unico di
    squadra non basta.
    """
    stagione = config.SEASONS_STORICHE[-1] if stagione is None else stagione
    st = storia(stagione, al, league=league)
    tutte = set(st["team"]) | set(st["opponent"])
    if squadra not in tutte:
        raise ValueError(f"{squadra!r} non e' in {stagione}")
    note = sorted(tutte - {squadra})

    # I due modelli si stimano UNA volta sola: rifarli per ogni avversario
    # costerebbe 38 fit identici e renderebbe la tabella inutilizzabile.
    m = modello_alla_data(st, league=league)
    r = _r_corrente(st, league=league)

    riga = pd.DataFrame([{"team": squadra, "opponent": avv,
                          "is_home": int(campo == "casa"), "campo": campo,
                          "avversario": avv}
                         for avv in note for campo in CAMPI])
    riga["lambda_tentativi"] = m["volume"].predict(riga)
    riga["lambda_sot"] = m["sot"].predict(riga)
    for ln in T.LINEE_TIRI:
        riga[f"p_over_{ln}"] = D.p_over(riga["lambda_tentativi"].to_numpy(), ln, r)

    out = riga[["avversario", "campo", "lambda_tentativi", "lambda_sot"]
               + [f"p_over_{ln}" for ln in T.LINEE_TIRI]]
    return out.sort_values(["campo", "lambda_tentativi"],
                           ascending=[True, False]).reset_index(drop=True)


def tabella_completa(stagione: str | None = None,
                     al: pd.Timestamp | str | None = None,
                     league: str | None = None,
                     contesto: dict | None = None) -> pd.DataFrame:
    """Tutte le squadre contro tutti gli avversari, in casa e in trasferta.

    760 righe per una stagione a venti squadre. E' il deliverable tabellare del
    blocco: la domanda dell'utente ha una risposta per **ogni** coppia, non solo
    per quella che si ha in mente adesso.
    """
    stagione = config.SEASONS_STORICHE[-1] if stagione is None else stagione
    st = storia(stagione, al, league=league)
    if not len(st):
        raise ValueError(f"nessuna partita in {stagione} prima di {al}: "
                         "senza una partita giocata non si sa nemmeno quali "
                         "squadre siano in questo campionato")

    # Le squadre sono quelle **viste in questa stagione**, mai ereditate dal
    # prior: prenderle da li' rimetterebbe dentro le retrocesse. Alla prima
    # giornata sono quindi meno di venti, e il conteggio lo dichiara.
    squadre = sorted(set(st["team"]) | set(st["opponent"]))
    giocate = st.groupby("team")["matchId"].nunique().to_dict()

    m = modello_alla_data(st, league=league, contesto=contesto)
    r = _r_corrente(st, league=league)
    r_sot = _r_corrente(st, league=league, target=T.TARGET_PRECISIONE)

    riga = pd.DataFrame([{"team": s, "opponent": o, "is_home": int(c == "casa"),
                          "squadra": s, "avversario": o, "campo": c}
                         for s in squadre for o in squadre if o != s
                         for c in CAMPI])
    riga["partite_squadra"] = riga["squadra"].map(giocate).fillna(0).astype(int)

    riga["lambda_tentativi"] = m["volume"].predict(riga)
    riga["lambda_sot"] = m["sot"].predict(riga)
    riga["regime"] = REGIMI[1]

    # Il regime e' una proprieta' della SQUADRA che tira, non della partita:
    # a settembre il Como puo' avere tre partite e l'Inter quattro.
    pri = (contesto or {}).get(T.TARGET, {}).get("prior")
    if pri is not None:
        from . import prior_stagione as PS
        sotto = (riga["partite_squadra"] + 1) < config.BURN_IN_ROUND
        if sotto.any():
            d = riga[sotto]
            riga.loc[sotto, "lambda_tentativi"] = PS.lam_dal_prior(
                pri, d["team"], d["opponent"], d["is_home"])
            riga.loc[sotto, "lambda_sot"] = PS.lam_dal_prior(
                contesto[T.TARGET_PRECISIONE]["prior"],
                d["team"], d["opponent"], d["is_home"])
            riga.loc[sotto, "regime"] = REGIMI[0]
        note = pri.squadre()
        riga["senza_prior"] = ((~riga["squadra"].isin(note)).astype(int)
                               + (~riga["avversario"].isin(note)).astype(int))
    else:
        riga["senza_prior"] = 0

    for ln in T.LINEE_TIRI:
        riga[f"p_over_{ln}"] = D.p_over(riga["lambda_tentativi"].to_numpy(), ln, r)
    for ln in LINEE_SOT:
        riga[f"p_over_sot_{ln}"] = D.p_over(
            riga["lambda_sot"].to_numpy(), ln, r_sot)

    riga["r"] = r
    riga["r_sot"] = r_sot
    riga["stagione"] = stagione
    riga["campionato"] = config.LEAGUE if league is None else league
    return riga[["campionato", "stagione", "squadra", "avversario", "campo",
                 "lambda_tentativi", "lambda_sot", "r", "r_sot",
                 "regime", "partite_squadra", "senza_prior"]
                + [f"p_over_{ln}" for ln in T.LINEE_TIRI]
                + [f"p_over_sot_{ln}" for ln in LINEE_SOT]]


def limiti() -> list[str]:
    """I limiti che vanno **accanto** ai numeri, non in fondo (vincolo 5)."""
    return [
        "MAE 3,57 tiri per squadra-partita (V1, su 3.278 righe walk-forward): "
        "il numero puntuale non e' preciso, la distribuzione si'",
        "sotto la 6a giornata la previsione e' dominata dall'intercetta e V1 non "
        "la valuta (burn-in dichiarato)",
        "`r` e' assunta costante fra squadre e stagioni (domanda aperta di V1)",
        "i tiri in porta vengono dal modello DIRETTO: V2 ha misurato la gerarchia "
        "volume x precisione e non l'ha adottata",
        "nessuna quota e nessuna valutazione di scommessa (vincolo 3): nel "
        "repository non ci sono prezzi di mercato reali",
    ]


# --------------------------------------------------------------------------
# Fase 15 / P1 - il TOTALE di partita, sul calendario della stagione in corso
# --------------------------------------------------------------------------
def linee_totale(target: str = T.TARGET):
    """Le linee del totale. Vengono da T1 e **non si riscrivono qui**.

    Sono state dichiarate prima di guardare i risultati, con la `REGOLA_LINEE`
    di V0 applicata alla media dei totali. Riscriverle in questo modulo sarebbe
    la seconda copia della stessa regola, cioe' il modo di farle divergere - il
    difetto che la Fase 14 ha gia' dovuto correggere su `quota_pareggio`.
    """
    from . import totale as TOT
    return TOT.linee_del(target)


#: **La ricalibrazione del totale NON si applica in pagina, e la decisione va
#: scritta accanto al suo perche'.**
#:
#: T1 ha misurato che il lambda del totale e' sotto-calibrato e ha costruito una
#: correzione walk-forward, adottandola col criterio scritto in anticipo. Ma
#: l'adozione e' **per (campionato, bersaglio)** e vale in **3 celle su 10**:
#: applicarla dove passa e non dove non passa renderebbe i cinque campionati non
#: confrontabili fra loro, che e' esattamente cio' che la regola di E1 vieta - e
#: la pagina li mostra uno accanto all'altro.
#:
#: Ci sono altre due ragioni, e nessuna e' prudenza:
#:
#: 1. la correzione e' validata **dentro** il walk-forward delle cinque stagioni
#:    storiche; portarla sulla 2026-2027 e' un passo in piu' che nessuno ha
#:    misurato;
#: 2. la domanda a cui la pagina risponde e' <<la stima della somma delle due
#:    squadre>>, e `E[X+Y] = E[X] + E[Y]` e' esatto qualunque sia la dipendenza.
#:    Mostrare un numero che non e' la somma risponderebbe a un'altra domanda.
#:
#: Cio' che si fa invece e' il vincolo 5: la pendenza di calibrazione di QUEL
#: campionato va **accanto al numero**, non in fondo. `calibrazione_totale()` la
#: porta, e la pagina la stampa.
RICALIBRAZIONE_IN_PAGINA = False


def _r_tot_corrente(st: pd.DataFrame, league: str | None = None,
                    target: str = T.TARGET) -> float:
    """`r_tot` della NB2 sui TOTALI, stimata sulle sole partite gia' giocate.

    E' `_r_corrente` per lato, ruotata a partita: stessa disciplina (vincolo 1,
    `r` entra nelle probabilita' Over) e stesso ripiego se la storia e' corta.

    **`r_tot` non si eredita da `r` per lato**, ed e' misurato e non assunto:
    T1 ha trovato 83,97 contro 20,00 sui tiri, con IC95 del rapporto
    [3,46, 5,66] che non contiene 1. **E non si eredita nemmeno da un altro
    campionato**: fra Bundesliga e Liga sui tiri in porta vale 190,6 contro
    70,5, cioe' un fattore 2,7, e un `r_tot` preso in prestito sbaglierebbe le
    code grossolanamente.
    """
    from . import totale as TOT

    d = TOT.partite(league=league, target=target, con_baseline=False)
    v = d[d["validabile"]]
    if len(st):
        v = v[v["data"] <= st["date"].max()]
    if len(v) < 60:
        v = d[d["validabile"]]
    return float(D.fit_r(v["y_totale"].to_numpy(dtype=float),
                         v["lam_totale"].to_numpy()))


def calibrazione_totale(league: str | None = None,
                        target: str = T.TARGET) -> dict:
    """La pendenza di calibrazione del totale in QUEL campionato, da dichiarare.

    Non corregge niente (`RICALIBRAZIONE_IN_PAGINA` e' `False`): e' il limite
    che va **accanto** ai numeri. Per lato il modello sta a 1,008; sul totale
    scende, e di quanto dipende dal campionato.
    """
    from . import totale as TOT

    d = TOT.partite(league=league, target=target, con_baseline=False)
    v = TOT.verdetto(d, target=target)
    return {"pendenza": v["pendenza_grezza"], "se": v["se_grezza"],
            "z": v["z_grezza"], "n": v["n"],
            "correzione_adottata_in_T1": v["adottata"]}


def tabella_calendario(cal: pd.DataFrame, stagione: str | None = None,
                       league: str | None = None, contesto: dict | None = None,
                       tab: pd.DataFrame | None = None) -> pd.DataFrame:
    """Una riga per PARTITA del calendario, con i due lati e i due totali.

    E' il ponte che P1 aggiunge a quello di V4: `previsione()` risponde su una
    coppia `(squadra, avversario, campo)`, questa risponde su una **partita
    vera** del calendario della stagione in corso, e ne da' anche il totale.

    IL TOTALE E' LA SOMMA, ED E' ESATTO
    -----------------------------------
    `lam_totale = lam_casa + lam_trasferta` non richiede nessuna ipotesi sulla
    dipendenza fra i due lati: e' la linearita' del valore atteso. Cio' che la
    dipendenza rompe e' la **dispersione**, ed e' il motivo per cui `r_tot` si
    **stima sui totali osservati** invece di ereditarla (T1).

    LE SQUADRE VENGONO DAL CALENDARIO, I NUMERI DAL MODELLO
    -------------------------------------------------------
    E' la decisione dell'utente sul <<turno zero>>. Una squadra del calendario
    che il modello di questa stagione non ha ancora visto - una neopromossa
    prima della sua prima partita - **non viene trattata come media in
    silenzio**: si usa il prior, che e' un regime dichiarato, e la si **conta**
    in `squadre_non_viste`. Se nemmeno il prior c'e', la partita esce dalla
    tabella e finisce in `attrs["scartate"]`: una riga senza numeri e' meglio di
    una riga con un numero inventato.

    **Le due guardie di V4 non sono state allentate**: `verifica_squadre` e
    `TeamModel(strict_teams=True)` restano dove sono. Qui non si chiama il
    modello within-season su una squadra che non conosce - si prende l'altra
    strada, che e' un regime in piu' e non una guardia in meno.
    """
    from . import prior_stagione as PS
    from . import totale as TOT

    stagione = config.SEASONS_STORICHE[-1] if stagione is None else stagione
    if cal is None or len(cal) == 0:
        vuota = pd.DataFrame(columns=["casa", "trasferta"])
        vuota.attrs["scartate"] = 0
        vuota.attrs["scartate_nomi"] = []
        return vuota
    if tab is None:
        tab = tabella_completa(stagione, league=league, contesto=contesto)

    idx = tab.set_index(["squadra", "avversario", "campo"])
    note = set(tab["squadra"])
    pri = (contesto or {}).get(T.TARGET, {}).get("prior")
    pri_sot = (contesto or {}).get(T.TARGET_PRECISIONE, {}).get("prior")

    righe, scartate = [], []
    for _, p in cal.iterrows():
        casa, trasf = p["casa"], p["trasferta"]
        non_viste = int(casa not in note) + int(trasf not in note)

        if non_viste == 0:
            rc = idx.loc[(casa, trasf, "casa")]
            rt = idx.loc[(trasf, casa, "trasferta")]
            lam_c = float(rc["lambda_tentativi"])
            lam_t = float(rt["lambda_tentativi"])
            sot_c, sot_t = float(rc["lambda_sot"]), float(rt["lambda_sot"])
            # Il regime e' una proprieta' della SQUADRA (A2): in una partita i
            # due lati possono stare in due regimi diversi, e allora la partita
            # dichiara il piu' debole dei due invece di nasconderne uno.
            reg = (REGIMI[0] if REGIMI[0] in (rc["regime"], rt["regime"])
                   else REGIMI[1])
            n_c, n_t = int(rc["partite_squadra"]), int(rt["partite_squadra"])
            senza_prior = int(max(rc["senza_prior"], rt["senza_prior"]))
        elif pri is not None:
            d = pd.DataFrame([{"team": casa, "opponent": trasf, "is_home": 1},
                              {"team": trasf, "opponent": casa, "is_home": 0}])
            lam_c, lam_t = [float(x) for x in PS.lam_dal_prior(
                pri, d["team"], d["opponent"], d["is_home"])]
            sot_c, sot_t = [float(x) for x in PS.lam_dal_prior(
                pri_sot, d["team"], d["opponent"], d["is_home"])]
            reg = REGIMI[0]
            n_c = n_t = 0
            noti = pri.squadre()
            senza_prior = int(casa not in noti) + int(trasf not in noti)
        else:
            scartate.append(f"{casa}-{trasf}")
            continue

        righe.append({
            "campionato": tab["campionato"].iloc[0], "stagione": stagione,
            "matchId": p.get("matchId"), "url": p.get("url"),
            "data": p.get("data"), "data_fonte": p.get("data_fonte"),
            "giornata": p.get("giornata"),
            "fonte_giornata": p.get("fonte_giornata"),
            "turno": p.get("turno"), "etichetta_turno": p.get("etichetta_turno"),
            "fonte_turno": p.get("fonte_turno"),
            "casa": casa, "trasferta": trasf,
            "lam_casa": lam_c, "lam_trasferta": lam_t,
            "lam_totale": lam_c + lam_t,
            "sot_casa": sot_c, "sot_trasferta": sot_t,
            "sot_totale": sot_c + sot_t,
            "regime": reg, "partite_casa": n_c, "partite_trasferta": n_t,
            "senza_prior": senza_prior, "squadre_non_viste": non_viste,
        })

    out = pd.DataFrame(righe)
    out.attrs["scartate"] = len(scartate)
    out.attrs["scartate_nomi"] = scartate
    if len(out) == 0:
        return out

    st = storia(stagione, league=league)
    r_tot = _r_tot_corrente(st, league=league, target=T.TARGET)
    r_tot_sot = _r_tot_corrente(st, league=league, target=T.TARGET_PRECISIONE)
    out["r_tot"] = r_tot
    out["r_tot_sot"] = r_tot_sot

    lam = out["lam_totale"].to_numpy()
    for ln in TOT.LINEE_TOTALE_TIRI:
        out[f"p_tot_{ln}"] = D.p_over(lam, ln, r_tot)
    lam_s = out["sot_totale"].to_numpy()
    for ln in TOT.LINEE_TOTALE_SOT:
        out[f"p_tot_sot_{ln}"] = D.p_over(lam_s, ln, r_tot_sot)
    return out
