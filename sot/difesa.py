# -*- coding: utf-8 -*-
"""Fase 9 / Blocco E3 — la difesa: gol subiti, porta inviolata, voto della linea.

Il bersaglio del blocco e' il difetto con la **causa piu' identificata** di tutto
il progetto: il modello d'asta fa Spearman **0** sui portieri contro **0,667** del
FVM, e la ragione e' scritta nel report di quel blocco — *i punti di un portiere
dipendono dalla difesa della sua squadra, e quel modello non guarda la squadra
affatto*. Qui la squadra entra.

PERCHE' E3 PUO' RIUSCIRE DOVE E2 HA FALLITO
--------------------------------------------
Non e' ottimismo, e' una proprieta' del ruolo. L'errore di E2 viveva sulle
**presenze**, e le presenze sono il 91% dell'errore complessivo perche' le
rotazioni di movimento sono quasi imprevedibili senza i dati sugli infortuni. Un
**portiere titolare gioca quasi tutto**: e' il ruolo in cui le presenze sono
quasi deterministiche, e quindi quello in cui quasi tutto l'errore residuo sta
altrove — cioe' esattamente dove questo blocco lavora.

LA VALIDAZIONE NON SI EREDITA
------------------------------
`model_team.TeamModel` e' calibrato sui tiri in porta, e questo blocco lo riusa
con `target="gol_fatti"`. **Che sia calibrato sui tiri non dice niente sui gol**:
sono conteggi con media tre volte piu' bassa, dispersione diversa e una frazione
di zeri molto maggiore. Ereditare la validazione della Fase 2 sarebbe leggere
male il vincolo 7 — due grandezze diverse trattate come la stessa perche' escono
dallo stesso codice. Quindi il modello dei gol e' **rivalidato per conto suo**,
con gli stessi baseline accanto e lo stesso walk-forward.

GLI AUTOGOL, E PERCHE' NON SONO UN DETTAGLIO
---------------------------------------------
`team_match.goals` **non e' il punteggio**: `shots.shots_mask` esclude gli autogol
dai tiri, quindi un autogol non compare da nessuna parte. Per i tiri in porta e'
la scelta giusta (un autogol non e' un tiro in porta di chi ne beneficia); per i
**gol subiti** e' un errore, perche' un autogol e' un gol subito a tutti gli
effetti — e per il fantacalcio lo e' due volte, visto che il portiere lo prende
comunque.

L'attribuzione **e' stata verificata, non assunta**: l'evento `Goal` con
`isOwnGoal` porta il `teamId` della squadra che lo **subisce** (il marcatore e'
suo). Ricomposto cosi', il punteggio ricostruito coincide con quello di
`matches.json` su **760/760** righe nel 2025-26, contro 738/760 ignorando gli
autogol. `verifica_punteggio()` lo ricontrolla su tutte e cinque le stagioni, e
non passa da nessun modello.

I DENOMINATORI ESCONO DAI DATI
-------------------------------
35 partite per l'Atalanta, non 38. Nessuna funzione di questo modulo scrive un
calendario a mano: si contano le righe, come E0 ed E1 hanno gia' dovuto fare.
"""

from __future__ import annotations

import json
import re

import numpy as np
import pandas as pd

from . import config, io_events

#: Bersaglio del modello di squadra di E3. Si modellano i **gol fatti**, non i
#: gol subiti, e i gol subiti si leggono come i gol fatti dell'avversario: cosi'
#: la forza difensiva della squadra i e' il coefficiente `difesa_i` di un modello
#: solo, invece di essere stimata due volte in due modi che potrebbero divergere.
TARGET = "gol_fatti"


# --------------------------------------------------------------------------
# I gol, ricomposti col punteggio vero
# --------------------------------------------------------------------------

def autogol(stagione: str, league: str = None) -> pd.DataFrame:
    """Autogol per `(matchId, teamId)`, dove `teamId` e' **chi lo subisce**.

    L'attribuzione non e' assunta: `verifica_punteggio` la falsifica contro il
    punteggio di `matches.json`, e l'ipotesi alternativa (autogol attribuito a chi
    ne beneficia) sbaglia 44 righe su 760 nel solo 2025-26.
    """
    ev = io_events.load_events(league=league, season=stagione)
    g = ev[ev["type"] == "Goal"]
    # `isOwnGoal` manca in 358 file su 380 (CLAUDE.md): pandas la emette solo se in
    # quella partita c'e' stato un autogol. `fillna(False)` non e' prudenza, e' la
    # lettura corretta di una colonna che lo scraper omette quando e' tutta falsa.
    og = g["isOwnGoal"].astype("boolean").fillna(False)
    out = (g[og.to_numpy()].groupby(["matchId", "teamId"]).size()
           .rename("autogol_subiti").reset_index())
    out["stagione"] = stagione
    return out


def gol_squadra_partita(stagioni=None, league: str = None) -> pd.DataFrame:
    """`team_match` con il punteggio VERO: `gol_fatti` e `gol_subiti`.

    `gol_fatti` = gol da tiri propri + autogol dell'avversario.
    `gol_subiti` = gol da tiri dell'avversario + autogol propri.

    Le due colonne sono la stessa grandezza vista dai due lati, e la simmetria e'
    verificata (`verifica_punteggio`): la somma dei gol fatti di una partita deve
    uguagliare la somma dei gol subiti.
    """
    stagioni = list(config.SEASONS_STORICHE if stagioni is None else stagioni)
    pezzi = []
    for st in stagioni:
        tm = pd.read_parquet(config.team_match(league=league, season=st))
        ag = autogol(st, league).set_index(["matchId", "teamId"])["autogol_subiti"]

        d = tm.copy()
        d["autogol_subiti"] = [ag.get((m, t), 0) for m, t
                               in zip(d["matchId"], d["teamId"])]
        d["autogol_a_favore"] = [ag.get((m, o), 0) for m, o
                                 in zip(d["matchId"], d["opponentId"])]

        # I gol dell'avversario, agganciati per partita. `nunique` sulla chiave e'
        # il controllo che il join non abbia moltiplicato: nessuna delle chiavi
        # disponibili in questi dati e' unica (CLAUDE.md), quindi si verifica.
        avv = d.set_index(["matchId", "teamId"])["goals"]
        d["goals_avversario"] = [avv.get((m, o), 0) for m, o
                                 in zip(d["matchId"], d["opponentId"])]

        d["gol_fatti"] = d["goals"] + d["autogol_a_favore"]
        d["gol_subiti"] = d["goals_avversario"] + d["autogol_subiti"]
        d["porta_inviolata"] = (d["gol_subiti"] == 0).astype(int)
        pezzi.append(d)

    out = pd.concat(pezzi, ignore_index=True)
    assert len(out) == len(out.drop_duplicates(["stagione", "matchId", "teamId"])), \
        "la chiave squadra-partita non e' unica"
    return out


def verifica_punteggio(stagioni=None, gsp: pd.DataFrame = None) -> pd.DataFrame:
    """Il punteggio ricostruito contro quello di `matches.json`. Falsificabile.

    E' il controllo forte del blocco e non passa da nessun modello: o i due
    numeri coincidono o non coincidono. Riporta accanto la variante **senza**
    autogol, che e' il baseline obbligatorio (vincolo 6) e qui serve a mostrare
    che l'aggiustamento fa qualcosa invece di dichiararlo.

    Le partite che `matches.json` elenca ma i cui eventi mancano alla fonte (le 12
    `matchCentreData: null`) non entrano nel denominatore: non sono un
    disaccordo, sono un'assenza gia' registrata nel manifest.
    """
    stagioni = list(config.SEASONS_STORICHE if stagioni is None else stagioni)
    gsp = gol_squadra_partita(stagioni) if gsp is None else gsp

    righe = []
    for st in stagioni:
        sc = punteggio_fonte(st)
        d = gsp[gsp["stagione"] == st].merge(sc, on="matchId", how="inner")
        veri = np.where(d["is_home"] == 1, d["gh"], d["ga"])
        subiti_veri = np.where(d["is_home"] == 1, d["ga"], d["gh"])
        righe.append({
            "stagione": st, "righe": len(d),
            "gol_fatti_esatti": int((d["gol_fatti"] == veri).sum()),
            "gol_subiti_esatti": int((d["gol_subiti"] == subiti_veri).sum()),
            "senza_autogol_esatti": int((d["goals"] == veri).sum()),
            "autogol": int(d["autogol_subiti"].sum()),
            # Simmetria interna: in ogni partita i gol fatti dei due lati sono i
            # gol subiti dell'altro. Non usa la fonte esterna, quindi resta
            # verificabile anche dove `matches.json` non arriva.
            "simmetria_ok": bool(
                d.groupby("matchId")["gol_fatti"].sum().equals(
                    d.groupby("matchId")["gol_subiti"].sum())),
        })
    return pd.DataFrame(righe)


def punteggio_fonte(stagione: str) -> pd.DataFrame:
    """Il punteggio dichiarato da `matches.json`, che e' grezzo e non derivato.

    E' una fonte **indipendente** dagli eventi: il punteggio sta nel calendario
    scaricato, non nella ricostruzione evento per evento. E' cio' che rende la
    verifica una verifica e non una tautologia.
    """
    p = config.matches_json(season=stagione)
    righe = []
    for m in json.loads(p.read_text(encoding="utf-8")):
        mm = re.search(r"/matches/(\d+)/", m["url"])
        s = re.match(r"\s*(\d+)\s*:\s*(\d+)\s*$", str(m.get("score", "")))
        if not mm or not s:
            continue
        righe.append({"matchId": int(mm.group(1)),
                      "gh": int(s.group(1)), "ga": int(s.group(2))})
    return pd.DataFrame(righe)


# --------------------------------------------------------------------------
# E3.1 — il modello di squadra sui gol, RIVALIDATO per conto suo
#
# Stessa specificazione della Fase 2 (`mu + attacco + difesa + gamma*casa`, ridge,
# decadimento a 150 giorni, alpha scelto in walk-forward sul solo passato) e
# bersaglio diverso. La sola cosa che cambia e' `target`, ed e' voluto: se la
# specificazione cambiasse insieme al bersaglio non si saprebbe a quale delle due
# cose attribuire la differenza.
#
# IL WALK-FORWARD E' DENTRO LA STAGIONE, NON ATTRAVERSO
# ------------------------------------------------------
# Ogni stagione ha il proprio walk-forward e le previsioni si mettono insieme
# dopo. Non e' una comodita': le squadre cambiano fra stagioni (tre entrano e tre
# escono), e un decadimento di 150 giorni attraverso l'estate darebbe alla prima
# giornata di settembre un training fatto quasi solo di maggio, cioe' di una
# squadra che non esiste piu'. Le previsioni restano confrontabili perche' il
# burn-in e i baseline sono gli stessi ovunque.
# --------------------------------------------------------------------------

#: Soglia Over per le metriche binarie sui gol. **Dichiarata**, non scelta
#: guardando i dati: 1.5 e' la linea di mercato piu' vicina alla media di gol per
#: squadra-partita (~1,4). La 4.5 della Fase 2 sarebbe assurda qui, ed e' un altro
#: modo di dire che le due validazioni non si ereditano.
LINEA_GOL = 1.5

CACHE = config.processed_league_dir() / "fase9_e3_walkforward_gol.parquet"


def walkforward_gol(stagioni=None, force: bool = False) -> pd.DataFrame:
    """Walk-forward del modello dei gol, una stagione per volta, poi impilate.

    Aggiunge `lam_subiti`: il lambda dell'**avversario** nella stessa partita.
    E' il punto in cui il modello smette di essere un modello d'attacco e diventa
    quello che a E3 serve — la stessa stima, letta dall'altro lato.
    """
    if CACHE.is_file() and not force:
        return pd.read_parquet(CACHE)

    from . import validate as V

    stagioni = list(config.SEASONS_STORICHE if stagioni is None else stagioni)
    gsp = gol_squadra_partita(stagioni)

    pezzi = []
    for st in stagioni:
        d = gsp[gsp["stagione"] == st].copy()
        p = V.walkforward_predict(d, target=TARGET)
        b = V.walkforward_baselines(d, target=TARGET)
        # La chiave e' `(matchId, team)`: su `matchId` da solo accoppierebbe fra
        # loro le due squadre della stessa partita, che e' il modo piu' silenzioso
        # di scambiare attacco e difesa. Si dichiara e si verifica.
        m = p.merge(b.drop(columns=["date", "team_match_idx", TARGET, "eligible"]),
                    on=["matchId", "team"], how="inner")
        assert len(m) == len(p), "il join dei baseline ha cambiato le righe"
        m["stagione"] = st

        # Il lambda dei gol SUBITI e' quello dell'avversario nella stessa partita.
        k = m.set_index(["matchId", "team"])["lam"]
        m["lam_subiti"] = [k.get((mi, o), np.nan) for mi, o
                           in zip(m["matchId"], m["opponent"])]
        pezzi.append(m)

    out = pd.concat(pezzi, ignore_index=True)
    # I gol subiti osservati e la porta inviolata, riportati accanto.
    g = gsp.set_index(["stagione", "matchId", "team"])
    for c in ("gol_subiti", "porta_inviolata"):
        out[c] = [g[c].get((s, mi, t), np.nan) for s, mi, t
                  in zip(out["stagione"], out["matchId"], out["team"])]

    CACHE.parent.mkdir(parents=True, exist_ok=True)
    out.to_parquet(CACHE, index=False)
    return out


def valutazione_gol(wf: pd.DataFrame = None) -> pd.DataFrame:
    """Il modello dei gol contro i quattro baseline, sulle stesse righe.

    **Non eredita niente dalla Fase 2.** `r` e il tasso base sono ricostruiti sul
    solo passato con la stessa procedura di Fase 4, perche' entrano nel Brier e un
    Brier con parametri stimati sull'intero campione non e' fuori campione.
    """
    from . import validate as V

    wf = walkforward_gol() if wf is None else wf
    d = wf[wf["eligible"]].copy()
    y = d[TARGET].to_numpy(dtype=float)

    r = V.walkforward_r(y, d["lam"].to_numpy(), d["date"])
    base = V.walkforward_base_rate(y, d["date"], line=LINEA_GOL)

    righe = [{"modello": "Poisson ridge att/dif/casa",
              **V.metrics(y, d["lam"].to_numpy(), r=r, line=LINEA_GOL,
                          base_rate=base)}]
    for nome in ("media squadra + campo", "media squadra", "media casa/trasferta",
                 "media campionato"):
        righe.append({"modello": nome,
                      **V.metrics(y, d[nome].to_numpy(), r=r, line=LINEA_GOL,
                                  base_rate=base)})
    return pd.DataFrame(righe)


def confronto_appaiato_gol(wf: pd.DataFrame = None) -> pd.DataFrame:
    """Il margine sul baseline, con il suo `t` appaiato. Vincolo 6.

    Senza questo, "il modello vince" e' una differenza di terza cifra letta come
    se fosse un risultato. La Fase 2 lo ha gia' insegnato sui tiri: li' il margine
    sul baseline migliore valeva t = 1.86, cioe' dentro il rumore.
    """
    from . import validate as V

    wf = walkforward_gol() if wf is None else wf
    d = wf[wf["eligible"]].copy()
    y = d[TARGET].to_numpy(dtype=float)
    e_mod = np.abs(y - d["lam"].to_numpy())

    righe = []
    for nome in ("media squadra + campo", "media squadra", "media casa/trasferta",
                 "media campionato"):
        e_b = np.abs(y - d[nome].to_numpy())
        # `paired_t` ritorna (somma, t), NON (t, p). Scambiarli e' un errore
        # facile e silenzioso: produce "p" sopra 1 senza che nulla sollevi.
        _somma, t = V.paired_t(e_b, e_mod)
        delta = float((e_b - e_mod).mean())
        righe.append({"baseline": nome,
                      "mae_baseline": float(e_b.mean()),
                      "mae_modello": float(e_mod.mean()),
                      "delta_mae": delta, "t": t,
                      "se": abs(delta / t) if t else float("nan")})
    return pd.DataFrame(righe)


def forma_predittiva_gol(wf: pd.DataFrame = None) -> dict:
    """PIT randomizzato e copertura: la forma della distribuzione, non solo la media.

    E' il controllo che la pendenza di calibrazione **non** fa, e su un conteggio
    a media bassa conta piu' che sui tiri: la frazione di zeri e' il 24% e una
    predittiva sbagliata nella coda sinistra si vedrebbe qui e non nel MAE.
    """
    from . import validate as V

    wf = walkforward_gol() if wf is None else wf
    d = wf[wf["eligible"]].copy()
    y = d[TARGET].to_numpy(dtype=float)
    lam = d["lam"].to_numpy()
    r = V.walkforward_r(y, lam, d["date"])

    u = V.pit(y, lam, r=r)
    return {"pit": V.pit_uniformity(u),
            "copertura": V.interval_coverage(y, lam, r=r),
            "quota_zeri_osservata": float((y == 0).mean()),
            "quota_zeri_attesa": float(np.mean(np.exp(-lam)))}


# --------------------------------------------------------------------------
# E3.2 — la porta inviolata come PROBABILITA', non come frequenza
#
# La differenza non e' formale. La frequenza storica dice "questo portiere ha
# fatto il 28% di clean sheet"; il modello dice "contro QUESTO avversario, in
# casa, la probabilita' e' il 34%". La seconda si somma sulle 38 partite del
# calendario vero e la prima no, ed e' la ragione per cui il bonus atteso di un
# portiere dipende dalla squadra — che e' esattamente cio' che manca al modello
# d'asta e che gli costa lo Spearman 0.
# --------------------------------------------------------------------------

def porta_inviolata(wf: pd.DataFrame = None) -> pd.DataFrame:
    """`P(gol subiti = 0)` per squadra-partita, contro tre riferimenti.

    I candidati sono quattro e tre sono baseline obbligatori:

    * **Poisson** `exp(-lambda_subiti)` — la forma chiesta dalla specifica;
    * **NB2** con la `r` dal solo passato — perche' se i gol fossero
      sovradispersi la Poisson sottostimerebbe **entrambe** le code, e la porta
      inviolata vive proprio nella coda sinistra;
    * **frequenza storica della squadra** — il baseline che il modello deve
      battere per giustificarsi;
    * **frequenza di campionato** — il baseline piatto.
    """
    from . import validate as V
    from . import dispersion

    wf = walkforward_gol() if wf is None else wf
    d = wf[wf["eligible"] & wf["lam_subiti"].notna()].copy()
    y = d["porta_inviolata"].to_numpy(dtype=float)
    lam_s = d["lam_subiti"].to_numpy()

    # `r` si stima sui gol SUBITI contro il loro lambda: e' la grandezza di cui
    # qui si vuole la distribuzione, e usare quella dei gol fatti sarebbe un
    # riferimento sbagliato per un motivo non ovvio.
    r = V.walkforward_r(d["gol_subiti"].to_numpy(dtype=float), lam_s, d["date"])

    p_poisson = np.exp(-lam_s)
    p_nb2 = dispersion.p_over(lam_s, 0.5, r)      # P(Y > 0)
    p_nb2 = 1.0 - p_nb2                            # -> P(Y = 0)
    p_storica = _frequenza_storica(d)
    p_grezza = _frequenza_storica(d, smorzamento=0.0)
    p_lega = V.walkforward_base_rate(y, d["date"], line=0.5)

    righe = []
    for nome, p in (("modello, Poisson", p_poisson),
                    ("modello, NB2", p_nb2),
                    ("frequenza storica della squadra", p_storica),
                    ("frequenza storica GREZZA (degenere)", p_grezza),
                    ("frequenza di campionato", p_lega)):
        ok = ~np.isnan(p)
        slope, se = pendenza_logit(y[ok], p[ok])
        righe.append({
            "candidato": nome, "righe": int(ok.sum()),
            "p_media": float(np.mean(p[ok])), "osservato": float(np.mean(y[ok])),
            "brier": V.brier(y[ok], p[ok]),
            "logloss": float(-np.mean(y[ok] * np.log(np.clip(p[ok], 1e-9, 1))
                                      + (1 - y[ok]) * np.log(np.clip(1 - p[ok], 1e-9, 1)))),
            "calib_slope": slope, "calib_se": se,
        })
    return pd.DataFrame(righe)


def pendenza_logit(y: np.ndarray, p: np.ndarray) -> tuple[float, float]:
    """Pendenza di calibrazione per un evento BINARIO, con errore standard.

    `validate.calibration_slope` e' la versione Poisson e qui non si puo' usare:
    il bersaglio e' 0/1 e il legame giusto e' il logit. Si stima
    `logit(P) = a + b * logit(p)` per Newton-Raphson, e un modello calibrato ha
    `b = 1` con la stessa lettura di sempre — sotto 1 previsioni troppo estreme,
    sopra 1 troppo compresse.

    Con `p` costante la pendenza **non e' identificata** e si ritorna `nan`,
    esattamente come fa la versione Poisson sul lambda costante: e' il caso del
    baseline piatto, e un numero uscito da una matrice singolare sarebbe peggio
    di un `nan`.
    """
    y = np.asarray(y, dtype=float)
    p = np.clip(np.asarray(p, dtype=float), 1e-6, 1 - 1e-6)
    z = np.log(p / (1 - p))
    if np.std(z) < 1e-12:
        return float("nan"), float("nan")

    Z = np.column_stack([np.ones(len(y)), z])
    b = np.array([0.0, 1.0])
    converge = False
    for _ in range(200):
        eta = np.clip(Z @ b, -30, 30)
        mu = 1.0 / (1.0 + np.exp(-eta))
        W = np.clip(mu * (1 - mu), 1e-12, None)
        g = Z.T @ (y - mu)
        H = Z.T @ (Z * W[:, None])
        try:
            step = np.linalg.solve(H, g)
        except np.linalg.LinAlgError:
            return float("nan"), float("nan")
        # Passo limitato: senza, un candidato che emette probabilita' 0 o 1
        # (separazione quasi perfetta) manda Newton a divergere e restituisce una
        # pendenza di 1e10 con l'aria di essere un numero. Un `nan` dichiarato e'
        # molto meglio di un numero prodotto da una divergenza.
        step = np.clip(step, -2.0, 2.0)
        b = b + step
        if np.max(np.abs(step)) < 1e-10:
            converge = True
            break
    if not converge:
        return float("nan"), float("nan")
    eta = np.clip(Z @ b, -30, 30)
    mu = 1.0 / (1.0 + np.exp(-eta))
    W = np.clip(mu * (1 - mu), 1e-12, None)
    cov = np.linalg.inv(Z.T @ (Z * W[:, None]))
    return float(b[1]), float(np.sqrt(cov[1, 1]))


#: Peso del prior nella frequenza storica, in "partite equivalenti". DICHIARATO.
#:
#: Serve perche' la frequenza grezza e' un **estimatore degenere**: una squadra
#: che dopo sei giornate non ha ancora tenuto la porta inviolata riceve p = 0
#: esatto, cioe' «impossibile». Il log-loss di uno zero sbagliato e' infinito e la
#: pendenza di calibrazione non e' nemmeno identificabile (separazione quasi
#: perfetta). Un baseline cosi' non e' un avversario serio, e il vincolo 6 chiede
#: un avversario serio: batterlo non dimostrerebbe niente.
#:
#: Il valore 5 non e' scelto guardando l'esito — e' lo stesso ordine di grandezza
#: del pavimento gia' dichiarato ed equivale a "cinque partite di prior". La
#: versione grezza resta calcolabile (`smorzamento=0`) e il report la mostra
#: accanto, perche' *quanto* la degenerazione costi e' esso stesso un risultato.
SMORZAMENTO_STORICO = 5.0


def _frequenza_storica(d: pd.DataFrame,
                       smorzamento: float = SMORZAMENTO_STORICO) -> np.ndarray:
    """Quota di porte inviolate della squadra **fino alla partita precedente**.

    E' il baseline serio della porta inviolata, ed e' anche quello che un
    fantallenatore userebbe davvero. Smorzata verso la media di campionato del
    solo passato con peso `smorzamento`: vedi la costante per il perche'.

    Tutto viene dal passato — il cumulato esclude la riga corrente e il prior di
    campionato guarda le sole date precedenti — quindi il vincolo 1 e' rispettato
    su entrambi i termini, non solo sul primo.
    """
    d = d.reset_index(drop=True)
    date = d["date"].to_numpy()
    pi = d["porta_inviolata"].to_numpy(dtype=float)

    # Prior di campionato per data, dal solo passato. Senza precedenti si usa la
    # quota strutturale di una Poisson a media ~1,4, non un numero comodo.
    ordine = np.argsort(date, kind="stable")
    prior = np.full(len(d), np.nan)
    for giorno in np.unique(date):
        prima = ordine[date[ordine] < giorno]
        prior[date == giorno] = pi[prima].mean() if len(prima) else 0.25

    out = np.full(len(d), np.nan)
    for _, g in d.groupby(["stagione", "team"], sort=False):
        g = g.sort_values("date")
        idx = g.index.to_numpy()
        y = pi[idx]
        cum = np.concatenate([[0.0], np.cumsum(y)[:-1]])
        n = np.arange(len(y), dtype=float)
        # Con `smorzamento = 0` la prima partita di ogni squadra e' 0/0: e' la
        # degenerazione stessa, non un incidente numerico, e resta `nan` invece di
        # essere riempita con un numero comodo.
        with np.errstate(invalid="ignore", divide="ignore"):
            out[idx] = (cum + smorzamento * prior[idx]) / (n + smorzamento)
    return out


# --------------------------------------------------------------------------
# E3.3 — il voto base della linea, condizionato alla forza difensiva
#
# E' l'ingresso del modificatore, che vale fino a +6 ed e' la leva piu' alta del
# prodotto. La domanda e' precisa: **di quanto si muove il voto base di un
# difensore quando cambia la forza difensiva della sua squadra?** Se la risposta
# fosse "di niente", il modificatore sarebbe imprevedibile per costruzione e il
# modello di squadra non servirebbe a nulla qui.
#
# SI USA IL LAMBDA PRE-PARTITA, NON I GOL REALIZZATI
# ---------------------------------------------------
# Le due cose si riportano entrambe ed e' voluto, ma **solo la prima e'
# disponibile al momento in cui serve**. `gol_subiti` osservati spiegano di piu' e
# non si possono usare per prevedere: e' la differenza fra descrivere e prevedere,
# e tenerle nella stessa tabella e' il modo di non confonderle.
# --------------------------------------------------------------------------

#: I ruoli della linea difensiva secondo la lega (etichetta di lega, non
#: posizionale: sono due grandezze diverse e il progetto le tiene separate).
RUOLI_LINEA = ("p", "d")


def voti_difensori(stagioni=None, wf: pd.DataFrame = None) -> pd.DataFrame:
    """Voto base di portieri e difensori, con la forza difensiva della squadra.

    Il ponte fra le due fonti e' quello gia' costruito e verificato: `partita_id`
    -> `matchId` dalla mappa delle partite, `squadra_id` -> `teamId` da quella
    delle squadre. Non si riaggancia niente qui.

    **Il voto e' quello base**, non il fantavoto: il modificatore si calcola sui
    voti, non sui fantavoti (`regole_fantacalcio.md` §2.1), e usare il secondo ci
    metterebbe dentro gol e assist, che con la solidita' difensiva non c'entrano.
    """
    from . import aggancio as AG, voti as VT

    stagioni = list(config.SEASONS_STORICHE if stagioni is None else stagioni)
    wf = walkforward_gol() if wf is None else wf

    v = VT.carica()
    v = v[v["stagione"].isin(stagioni) & v["ruolo"].isin(RUOLI_LINEA)].copy()
    v = v[v["voto_redazione"].notna() & ~v["allenatore"]]

    part = AG.mappa_partite()["partite"][["stagione", "partita_id", "matchId"]]
    sq = AG.mappa_squadre()[["stagione", "squadra_id_fc", "teamId_ws"]]

    n = len(v)
    v = v.merge(part, on=["stagione", "partita_id"], how="inner")
    v = v.merge(sq, left_on=["stagione", "squadra_id"],
                right_on=["stagione", "squadra_id_fc"], how="inner")
    v.attrs["righe_perse_nel_ponte"] = n - len(v)

    # `wf` ha il nome della squadra, non il teamId: si passa da `team_match`, che
    # ha entrambi. Un join in piu' e' meglio di un nome ricostruito a mano.
    nomi = pd.concat([
        pd.read_parquet(config.team_match(season=s))[["stagione", "matchId",
                                                      "teamId", "team"]]
        for s in stagioni], ignore_index=True)
    v = v.merge(nomi, left_on=["stagione", "matchId", "teamId_ws"],
                right_on=["stagione", "matchId", "teamId"], how="inner")

    k = wf.set_index(["stagione", "matchId", "team"])
    for c in ("lam_subiti", "gol_subiti", "porta_inviolata", "eligible"):
        v[c] = [k[c].get((s, m, t), np.nan) for s, m, t
                in zip(v["stagione"], v["matchId"], v["team"])]

    v = v[v["lam_subiti"].notna() & v["eligible"].astype("boolean").fillna(False)]
    return v.rename(columns={"voto_redazione": "voto"})


def voto_condizionato(v: pd.DataFrame = None) -> pd.DataFrame:
    """Il voto base per terzile di forza difensiva attesa, e per gol subiti.

    Due tabelle in una, e la distinzione e' il punto: il terzile di `lam_subiti`
    e' **noto prima**, i gol subiti no.
    """
    v = voti_difensori() if v is None else v
    righe = []
    for ruolo in RUOLI_LINEA:
        d = v[v["ruolo"] == ruolo]
        if not len(d):
            continue
        terzile = pd.qcut(d["lam_subiti"], 3, labels=["forte", "media", "debole"])
        for et, sub in d.groupby(terzile, observed=True):
            righe.append({"ruolo": ruolo, "condizione": f"terzile atteso: {et}",
                          "righe": len(sub),
                          "lam_subiti_medio": float(sub["lam_subiti"].mean()),
                          "voto_medio": float(sub["voto"].mean()),
                          "sd_voto": float(sub["voto"].std())})
        for g, sub in d.groupby(d["gol_subiti"].clip(upper=3), observed=True):
            righe.append({"ruolo": ruolo,
                          "condizione": f"gol subiti (osservati): {int(g)}"
                                        + ("+" if g == 3 else ""),
                          "righe": len(sub),
                          "lam_subiti_medio": float(sub["lam_subiti"].mean()),
                          "voto_medio": float(sub["voto"].mean()),
                          "sd_voto": float(sub["voto"].std())})
    return pd.DataFrame(righe)


def pendenza_voto(v: pd.DataFrame = None) -> pd.DataFrame:
    """Di quanto si muove il voto per unita' di forza difensiva. Con baseline.

    La pendenza su `lam_subiti` e' l'unica utilizzabile in previsione; quella su
    `gol_subiti` e' riportata accanto per far vedere **quanto piu' grande sarebbe
    l'effetto se lo si conoscesse**, che e' anche il tetto di cio' che un modello
    di squadra migliore potrebbe recuperare.
    """
    v = voti_difensori() if v is None else v
    righe = []
    for ruolo in RUOLI_LINEA:
        d = v[v["ruolo"] == ruolo]
        if len(d) < 50:
            continue
        for nome, x in (("lam_subiti (previsto)", d["lam_subiti"]),
                        ("gol_subiti (osservato)", d["gol_subiti"])):
            x = x.to_numpy(dtype=float)
            y = d["voto"].to_numpy(dtype=float)
            X = np.column_stack([np.ones(len(x)), x])
            b, *_ = np.linalg.lstsq(X, y, rcond=None)
            res = y - X @ b
            se = float(np.sqrt((res ** 2).sum() / (len(y) - 2)
                               * np.linalg.inv(X.T @ X)[1, 1]))
            righe.append({
                "ruolo": ruolo, "regressore": nome, "righe": len(d),
                "pendenza": float(b[1]), "se": se,
                "t": float(b[1] / se) if se else float("nan"),
                # L'ampiezza utile: quanto il voto si muove dal 10o al 90o
                # percentile del regressore. Una pendenza per unita' non dice se
                # l'effetto e' grande, perche' dipende da quanto varia la x.
                "delta_p10_p90": float(b[1] * (np.quantile(x, 0.9)
                                               - np.quantile(x, 0.1))),
            })
    return pd.DataFrame(righe)


# --------------------------------------------------------------------------
# E3.4 — la correlazione DENTRO la linea
#
# `modificatore.simula_linea` estrae i membri della linea in modo indipendente, e
# lo dichiara come limite: "una difesa che prende tre gol prende voti bassi
# *insieme*". Finche' resta dichiarato e non stimato, il limite e' un'ipotesi.
# Qui si misura.
#
# IL SEGNO NON E' OVVIO, E NON VA INDOVINATO
# -------------------------------------------
# Piu' correlazione = piu' varianza della **media di linea**. Con fasce a scalini
# questo non alza ne' abbassa il bonus atteso in modo prevedibile: dipende da dove
# la linea cade rispetto alle soglie. Una linea appena SOTTO una soglia guadagna
# dalla varianza (a volte la supera); una appena SOPRA ci perde. Quindi si misura
# a piu' livelli di partenza invece di riportare un numero solo.
# --------------------------------------------------------------------------

def correlazione_linea(v: pd.DataFrame = None) -> pd.DataFrame:
    """Correlazione fra i voti dei membri della stessa linea, nella stessa partita.

    Stimata come **correlazione intraclasse**: la quota di varianza del voto che
    sta *fra* le squadre-partita invece che *dentro*. E' la forma giusta perche' la
    linea non ha un ordine — non c'e' un "primo" e un "secondo" difensore — e una
    correlazione a coppie dipenderebbe da come li si numera.

    Si riporta anche la versione **al netto del giocatore**: parte della
    correlazione e' che le difese forti schierano difensori bravi, che prendono
    voti alti sempre. Quella parte e' gia' dentro `mu` nella simulazione, e
    contarla due volte gonfierebbe la correlazione da iniettare. La riga che serve
    a E3.4 e' la seconda.
    """
    v = voti_difensori() if v is None else v
    righe = []
    for etichetta, ruoli in (("linea intera (p+d)", RUOLI_LINEA), ("solo d", ("d",))):
        d = v[v["ruolo"].isin(ruoli)].copy()
        gruppo = ["stagione", "matchId", "teamId_ws"]

        for netto in (False, True):
            x = d.copy()
            if netto:
                # Si toglie la media di ogni giocatore nella stagione: cio' che
                # resta e' lo scarto di giornata, che e' l'oggetto della domanda.
                x["voto"] = x["voto"] - x.groupby(
                    ["stagione", "giocatore_id"])["voto"].transform("mean")
            g = x.groupby(gruppo)["voto"]
            n = g.size()
            valide = n[n >= 2].index
            x = x.set_index(gruppo).loc[valide].reset_index()
            if len(x) < 50:
                continue

            g = x.groupby(gruppo)["voto"]
            medie, conta = g.mean(), g.size()
            gran = x["voto"].mean()
            # ANOVA a una via: MSB e MSW, poi ICC(1).
            ssb = float((conta * (medie - gran) ** 2).sum())
            ssw = float(((x["voto"] - x.set_index(gruppo).index.map(medie).to_numpy()) ** 2).sum())
            k_gruppi, n_tot = len(medie), len(x)
            msb = ssb / (k_gruppi - 1)
            msw = ssw / (n_tot - k_gruppi)
            n0 = (n_tot - (conta ** 2).sum() / n_tot) / (k_gruppi - 1)
            icc = (msb - msw) / (msb + (n0 - 1) * msw)
            righe.append({
                "insieme": etichetta,
                "voto": "al netto del giocatore" if netto else "grezzo",
                "righe": n_tot, "gruppi": k_gruppi,
                "dimensione_media": float(n0),
                "icc": float(icc), "sd_entro": float(np.sqrt(msw)),
            })
    return pd.DataFrame(righe)


def effetto_correlazione(rho_misurato: float = None, sd: float = 0.55,
                         p_voto: float = 0.85) -> pd.DataFrame:
    """Il bonus atteso con e senza correlazione, a diversi livelli della linea.

    Il livello si fa variare perche' **e' li' che il segno si decide**: con fasce
    a scalini la varianza aiuta chi sta sotto una soglia e danneggia chi sta
    sopra. Riportare un solo livello darebbe un segno e nasconderebbe che e'
    l'altro poco piu' in la'.

    `sd` e `p_voto` sono tenuti fissi e dichiarati: qui si isola l'effetto della
    **correlazione**, non si rifa' la calibrazione del modificatore.
    """
    from . import modificatore as MOD

    if rho_misurato is None:
        c = correlazione_linea()
        riga = c[(c["insieme"] == "linea intera (p+d)")
                 & (c["voto"] == "al netto del giocatore")]
        rho_misurato = float(riga["icc"].iloc[0]) if len(riga) else 0.0

    righe = []
    for n_dif in L_MODULI:
        n = n_dif + 1                                     # portiere + difensori
        # La griglia arriva fino a 7,60 **apposta**: e' oltre l'ultima soglia, ed
        # e' li' che il segno si inverte. Fermarla a 6,60 avrebbe dato un effetto
        # sempre positivo e una conclusione sbagliata.
        for mu0 in (5.50, 5.75, 5.90, 6.00, 6.10, 6.25, 6.40, 6.50, 6.60,
                    6.75, 6.90, 7.00, 7.10, 7.30, 7.60):
            mu = np.full(n, mu0)
            sd_v = np.full(n, sd)
            pv = np.full(n, p_voto)
            a = MOD.simula_linea(mu, sd_v, pv, rho=0.0).mean()
            b = MOD.simula_linea(mu, sd_v, pv, rho=rho_misurato).mean()
            righe.append({
                "n_difensori": n_dif, "voto_medio_linea": mu0,
                "bonus_indipendenti": float(a),
                "bonus_correlati": float(b),
                "delta_per_giornata": float(b - a),
                "delta_stagione": float((b - a) * MOD.GIORNATE),
                "rho": rho_misurato,
            })
    return pd.DataFrame(righe)


#: I moduli su cui si valuta la linea. Sono quelli della lega (decisione 0.2: il
#: numero di difensori dipende dal modulo), non una scelta di questo blocco.
L_MODULI = (3, 4, 5)


# --------------------------------------------------------------------------
# La verifica che chiude il blocco: lo Spearman SUI PORTIERI
#
# E' il bersaglio dichiarato di E3 e va riportato **separato**, mai annegato nella
# metrica complessiva: i portieri sono il 12% del listone, quindi un
# miglioramento anche grande su di loro sparirebbe in una media su tutti i ruoli.
# Il riferimento e' la riga del modello d'asta: **Spearman 0 sui portieri contro
# 0,667 del FVM**.
#
# COSA CAMBIA E COSA NO
# ---------------------
# Si sostituisce **solo** la componente difensiva del bonus atteso del portiere —
# gol subiti e porta inviolata, cioe' le due voci di `lega.SOLO_PORTIERE` che
# dipendono dalla squadra — con quella derivata dal modello di squadra. Voto base
# e presenze attese restano **quelli del modello d'asta**, non toccati: se
# cambiassero anche quelli non si saprebbe a cosa attribuire la differenza.
#
# LA FORZA DIFENSIVA VIENE DAL SOLO PASSATO
# ------------------------------------------
# `forza_difensiva_attesa` stima i gol subiti per partita della stagione bersaglio
# usando le **stagioni precedenti**, con shrinkage verso la media di campionato.
# Il club del portiere in t+1 e' invece trattato come **noto**, ed e' una scelta
# dichiarata: all'asta lo e' davvero, e lo assumono gia' sia il FVM sia la QI, che
# sono i concorrenti. Assumerlo ignoto renderebbe il confronto scorretto **contro**
# il modello, non a suo favore.
# --------------------------------------------------------------------------

#: Peso dello shrinkage della forza difensiva verso la media di campionato, in
#: partite equivalenti. DICHIARATO, non scelto sull'esito: 10 partite e' circa un
#: quarto di stagione, l'ordine di grandezza a cui una difesa smette di essere
#: rumore. Una neopromossa senza storia prende la media di campionato piena.
SMORZAMENTO_DIFESA = 10.0


#: Come si guarda il passato per stimare la forza difensiva della stagione
#: bersaglio. **`ultima` e' il default**, e la ragione e' di coerenza con il
#: progetto, non di esito: tutto il resto del repository pesa il passato con
#: un'emivita di 150 giorni, cioe' meno di una stagione, quindi mettere sullo
#: stesso piano quattro stagioni fa e l'anno scorso sarebbe l'unica parte del
#: progetto che non decade. `tutte` resta disponibile e il report riporta
#: **entrambe**: la conclusione del blocco e' la stessa con l'una e con l'altra,
#: quindi non dipende da questa scelta.
MODI_FORZA = ("ultima", "tutte")


def forza_difensiva_attesa(stagione: str, gsp: pd.DataFrame = None,
                           smorzamento: float = SMORZAMENTO_DIFESA,
                           modo: str = "ultima") -> pd.Series:
    """Gol subiti attesi per partita in `stagione`, dalle sole stagioni precedenti.

    Indicizzata per `teamId`. Chi non ha passato (le neopromosse) non compare, e
    a valle prende un `nan` invece di un numero inventato: la Serie B non e' nel
    repository, e la media delle retrocesse sarebbe un'informazione diversa da
    quella che serve (Fase 6E l'ha gia' misurata e non e' neutra).
    """
    if modo not in MODI_FORZA:
        raise ValueError(f"modo={modo!r} non e' fra {MODI_FORZA}")

    gsp = gol_squadra_partita() if gsp is None else gsp
    passato = gsp[gsp["stagione"] < stagione]
    if passato.empty:
        return pd.Series(dtype=float)
    if modo == "ultima":
        passato = passato[passato["stagione"] == passato["stagione"].max()]

    media_lega = float(passato["gol_subiti"].mean())
    g = passato.groupby("teamId")["gol_subiti"].agg(["sum", "size"])
    return ((g["sum"] + smorzamento * media_lega)
            / (g["size"] + smorzamento)).rename("gol_subiti_attesi")


def bonus_difensivo_portiere(lam: np.ndarray) -> np.ndarray:
    """Bonus atteso per partita di un portiere, dalla sola distribuzione dei gol.

    `-1 * E[gol subiti] + 1 * P(gol subiti = 0)`, cioe' le due voci di
    `lega.BONUS` che dipendono dalla squadra. Le altre — rigori parati su tutte —
    non dipendono dalla forza difensiva e restano dove sono.

    **La porta inviolata e' una probabilita', non una frequenza** (E3.2): e' il
    punto per cui il blocco esiste, perche' e' cio' che rende il bonus una
    funzione dell'avversario e del campo invece che una costante del portiere.
    """
    from . import lega as L
    lam = np.clip(np.asarray(lam, dtype=float), 1e-9, None)
    return (L.BONUS["gol_subiti"] * lam
            + L.BONUS["porta_inviolata"] * np.exp(-lam))


def _lam_portieri(d: pd.DataFrame, gsp: pd.DataFrame, modo: str = "ultima"
                  ) -> pd.Series:
    """Forza difensiva attesa agganciata a ogni riga del walk-forward d'asta."""
    sq = _ponte_squadre()
    pezzi = []
    for st, sub in d.groupby("stagione_prevista"):
        f = forza_difensiva_attesa(st, gsp, modo=modo)
        team = sub["squadra_id"].map(
            sq[sq["stagione"] == st].set_index("squadra_id_fc")["teamId_ws"])
        pezzi.append(pd.Series(team.map(f).to_numpy(), index=sub.index))
    return pd.concat(pezzi).reindex(d.index)


def premessa_portieri(wf: pd.DataFrame = None, gsp: pd.DataFrame = None
                      ) -> pd.DataFrame:
    """La premessa del blocco, messa alla prova invece che assunta.

    E3 esisteva su questo argomento: *un portiere titolare gioca quasi tutto,
    quindi le presenze sono quasi deterministiche e l'errore sta altrove — cioe'
    dove E3 lavora.* L'argomento e' corretto **per il titolare** e falso **per la
    popolazione dei quotati**, e la differenza decide l'esito del blocco.

    Si riporta l'ordinamento dei portieri per soglia crescente di presenze
    attese, con accanto le sole presenze attese come ordinatore. Se le presenze
    fossero davvero risolte, la loro Spearman dovrebbe essere bassa e quella del
    modello alta; si osserva il contrario.

    **I due concorrenti di mercato non hanno lo stesso orologio, e la colonna che
    conta e' QI.** `quotazioni.orologio()` ha misurato che il FVM archiviato si
    muove **durante** la stagione: come concorrente in un confronto fuori campione
    non e' leale, perche' per una stagione passata ne conosce l'esito. Resta in
    tabella — un errore di questo progetto non si cancella — ma **marcato**, e
    accanto ci sta QI, che e' la sola quotazione davvero nota al momento
    dell'asta.
    """
    from . import modello_asta as MA
    from scipy.stats import spearmanr

    wf = MA.walkforward() if wf is None else wf
    gsp = gol_squadra_partita() if gsp is None else gsp
    d = wf[wf["ruolo"] == "p"].copy()
    d["lam"] = _lam_portieri(d, gsp)
    d = d[d["lam"].notna()]

    righe = []
    for soglia in (0, 10, 15, 20, 25):
        x = d[d["presenze_attese"] >= soglia]
        if len(x) < 40:
            continue
        dif = bonus_difensivo_portiere(x["lam"].to_numpy())
        pe3 = x["presenze_attese"] * (x["voto_atteso"] + dif)
        base, con_e3, solo_pres = [], [], []
        mercato = {"b_fvm": [], "b_qi": []}
        for _, s2 in x.groupby("stagione_prevista"):
            i = s2.index
            base.append(spearmanr(s2["punti_previsti"], s2["punti_osservati"]).statistic)
            con_e3.append(spearmanr(pe3[i], s2["punti_osservati"]).statistic)
            solo_pres.append(spearmanr(s2["presenze_attese"],
                                       s2["punti_osservati"]).statistic)
            for col in mercato:
                ok = s2[col].notna()
                mercato[col].append(
                    spearmanr(s2.loc[ok, col], s2.loc[ok, "punti_osservati"]).statistic
                    if ok.sum() >= 5 else np.nan)
        righe.append({
            "soglia_presenze_attese": soglia, "portieri": len(x),
            "quota_mai_in_campo": float((x["presenze_osservate"] == 0).mean()),
            "spearman_modello": float(np.mean(base)),
            "spearman_con_difesa_e3": float(np.mean(con_e3)),
            "spearman_sole_presenze_attese": float(np.mean(solo_pres)),
            # Il confronto decisivo: se anche la quotazione crolla fra i probabili
            # titolari, il suo vantaggio e' sapere CHI GIOCA, non la difesa.
            "spearman_qi": float(np.nanmean(mercato["b_qi"])),
            "spearman_fvm_CONTAMINATO": float(np.nanmean(mercato["b_fvm"])),
        })
    return pd.DataFrame(righe)


def spearman_portieri(wf: pd.DataFrame = None, gsp: pd.DataFrame = None
                      ) -> pd.DataFrame:
    """La verifica che chiude E3, riportata **separata** per ruolo.

    Confronta il modello d'asta, la sua versione con la componente difensiva di
    E3, e i concorrenti veri (FVM, QI) piu' la persistenza. Il FVM **non e' un
    riferimento, e' un concorrente**: e' una stima fatta da altri con
    informazioni che il modello non ha, e se non lo si batte comprare al listino
    resta la scelta razionale.
    """
    from . import modello_asta as MA
    from scipy.stats import spearmanr

    wf = MA.walkforward() if wf is None else wf
    gsp = gol_squadra_partita() if gsp is None else gsp

    d = wf.copy()
    for modo in MODI_FORZA:
        lam = _lam_portieri(d, gsp, modo=modo)
        dif = bonus_difensivo_portiere(lam.to_numpy())
        # La sostituzione riguarda SOLO la parte difensiva del bonus del portiere:
        # voto base e presenze attese restano quelli del modello d'asta.
        d[f"punti_e3_{modo}"] = np.where(
            (d["ruolo"] == "p") & lam.notna(),
            d["presenze_attese"] * (d["voto_atteso"] + dif),
            d["punti_previsti"])

    candidati = {"modello d'asta": "punti_previsti",
                 "modello d'asta + difesa E3 (ultima stagione)": "punti_e3_ultima",
                 "modello d'asta + difesa E3 (tutte le stagioni)": "punti_e3_tutte",
                 "FVM della fonte (CONTAMINATO)": "b_fvm",
                 "quotazione iniziale QI": "b_qi",
                 "persistenza (anno prima)": "b_persistenza"}

    righe = []
    for ruolo in ("p", "d", "c", "a"):
        sub = d[d["ruolo"] == ruolo]
        for nome, col in candidati.items():
            per_stagione, prec = [], []
            for _, s2 in sub.groupby("stagione_prevista"):
                ok = s2[col].notna() & s2["punti_osservati"].notna()
                if ok.sum() < 5:
                    continue
                per_stagione.append(spearmanr(s2.loc[ok, col],
                                              s2.loc[ok, "punti_osservati"]).statistic)
                prec.append(_precisione(s2[ok], col, ruolo))
            if not per_stagione:
                continue
            righe.append({"ruolo": ruolo, "candidato": nome,
                          "stagioni": len(per_stagione),
                          "spearman": float(np.mean(per_stagione)),
                          "min": float(np.min(per_stagione)),
                          "max": float(np.max(per_stagione)),
                          "precisione_top": float(np.mean(prec))})
    return pd.DataFrame(righe)


#: Quanti giocatori per ruolo entrano nella "precisione sui primi N". Sono i posti
#: di una rosa della lega (3/8/8/6, decisione 0.5), non una scelta di E3.
N_PER_RUOLO = {"p": 3, "d": 8, "c": 8, "a": 6}


def _precisione(s: pd.DataFrame, col: str, ruolo: str) -> float:
    """Quota dei primi N previsti che stanno anche fra i primi N osservati.

    I pari merito si sciolgono col seme del progetto e **non** nell'ordine della
    tabella: il listone arriva ordinato per `QI` decrescente, e scioglierli
    nell'ordine di arrivo aveva gia' falsato questo confronto in favore
    dell'ignoranza (difetto trovato dai test nel blocco del modello d'asta).
    """
    n = N_PER_RUOLO.get(ruolo, 5)
    if len(s) < n:
        return float("nan")
    rng = np.random.default_rng(config.SEED)
    rumore = rng.random(len(s)) * 1e-9
    prev = set(s.index[np.argsort(-(s[col].to_numpy() + rumore))][:n])
    oss = set(s.index[np.argsort(-(s["punti_osservati"].to_numpy() + rumore))][:n])
    return len(prev & oss) / n


def _ponte_squadre() -> pd.DataFrame:
    from . import aggancio as AG
    return AG.mappa_squadre()[["stagione", "squadra_id_fc", "teamId_ws"]]


# --------------------------------------------------------------------------
# E3.5 — coda: perche' la difesa peggiora invece di migliorare
#
# L'IPOTESI, E COME SI FALSIFICA
# -------------------------------
# E3.3 ha trovato che sul portiere il voto base si muove nel verso **opposto** a
# quello dei difensori rispetto alla forza difensiva attesa. Da li' nasce una
# spiegazione dell'esito negativo di E3: dietro una difesa debole il portiere
# para di piu' e il voto sale, il malus dei gol subiti scende, **le due voci si
# compensano, il netto e' quasi piatto** — e collegare la difesa a un solo lato
# dei due peggiora, perche' aggiunge una meta' della compensazione senza l'altra.
#
# E' un'ipotesi con tre conseguenze misurabili, e si tengono separate perche'
# possono cadere una per volta:
#
#   1. la pendenza del voto sul portiere e' positiva          (E3.3: si', +0.0795)
#   2. il NETTO e' quasi piatto, cioe' la compensazione e' quasi completa
#   3. attraverso i portieri le due componenti sono correlate NEGATIVAMENTE
#
# La 1 e' gia' misurata e qui viene solo riprodotta, come controllo che le
# componenti siano costruite sulla stessa popolazione di E3.3. **Sono la 2 e la 3
# a decidere**, e la 2 ha una soglia dichiarata prima di guardare: la
# compensazione si chiama tale se il netto e' sotto **un terzo** del malus, cioe'
# se il voto base ne annulla almeno i due terzi. Sotto quella soglia "quasi
# piatto" e' una descrizione; sopra, non lo e'.
#
# QUALE FONTE ALIMENTA IL MALUS — E NON E' UNA FORMALITA'
# -------------------------------------------------------
# `voti_difensori` **sovrascrive** `gol_subiti` con i gol della squadra ricomposti
# dal walk-forward (autogol compresi). E' la grandezza giusta per condizionare il
# voto, ed e' sbagliata per il malus: il malus lo produce la **fonte dei voti**,
# che e' definitoria perche' e' quella che ha generato i `punti_osservati` contro
# cui tutto si valuta. Le due colonne hanno lo stesso nome e differiscono su **32
# righe su 3.307**, sempre nel verso di WhoScored che ne conta di piu'. Qui si
# riprende quella della fonte e la si tiene con un nome diverso.
# --------------------------------------------------------------------------

#: La fonte dei gol subiti che alimenta il **malus** del portiere. Dichiarata
#: perche' il vincolo 7 vieta di mescolare due definizioni della stessa
#: grandezza, e qui ce ne sono due a portata di mano.
FONTE_MALUS = "voti"

#: Sotto questa quota il netto si dice "quasi piatto", cioe' la compensazione si
#: dice completa. **Dichiarata prima di guardare i numeri** (vincolo 1 applicato a
#: una soglia, come l'80' della presenza e le soglie di E1): un terzo del malus
#: superstite significa che il voto base ne annulla i due terzi.
SOGLIA_COMPENSAZIONE = 1 / 3


def _ols(x, y) -> tuple[float, float, float]:
    """Pendenza, errore standard e `t` di una regressione semplice.

    Ritorna `se = nan` quando la risposta e' costante — succede sul difensore,
    la cui componente difensiva e' identicamente zero per regolamento — invece di
    dividere per zero e stampare un avviso.
    """
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    X = np.column_stack([np.ones(len(x)), x])
    b, *_ = np.linalg.lstsq(X, y, rcond=None)
    res = y - X @ b
    den = (res ** 2).sum()
    if den <= 0 or len(y) <= 2:
        return float(b[1]), float("nan"), float("nan")
    se = float(np.sqrt(den / (len(y) - 2) * np.linalg.inv(X.T @ X)[1, 1]))
    return float(b[1]), se, float(b[1] / se)


def componenti_portiere(v: pd.DataFrame = None, stagioni=None) -> pd.DataFrame:
    """Le due componenti che la forza difensiva muove, piu' il loro netto.

    - `comp_voto`  = il voto base, che e' la componente di E3.3;
    - `comp_bonus` = `-1 x gol subiti + 1 x porta inviolata` in punti di lega,
      cioe' le due voci di `lega.BONUS` che dipendono dalla squadra. **Solo al
      portiere**: per il difensore vale zero, e vale zero *per regolamento*, non
      per approssimazione — un difensore non prende malus sui gol subiti.
    - `comp_netto` = la loro somma.

    Il netto **non e' il fantavoto**: gol, assist e cartellini restano fuori
    perche' con la solidita' difensiva non c'entrano, ed e' la stessa scelta con
    cui E3.3 ha usato il voto base invece del fantavoto.
    """
    from . import lega as L, voti as VT

    v = voti_difensori(stagioni=stagioni) if v is None else v
    src = VT.carica()[["stagione", "partita_id", "giocatore_id", "gol_subiti"]]
    v = v.merge(src.rename(columns={"gol_subiti": "gol_subiti_voti"}),
                on=["stagione", "partita_id", "giocatore_id"], how="left")

    e_p = v["ruolo"] == "p"
    gs = v["gol_subiti_voti"]
    v["comp_voto"] = v["voto"]
    v["comp_bonus"] = np.where(
        e_p, L.BONUS["gol_subiti"] * gs
        + L.BONUS["porta_inviolata"] * (gs == 0), 0.0)
    v["comp_netto"] = v["comp_voto"] + v["comp_bonus"]
    # Quanto le due definizioni di "gol subiti" divergono, come numero e non come
    # rassicurazione: se un giorno crescesse, il malus starebbe cambiando fonte
    # senza che nessuno l'abbia deciso.
    v.attrs["righe_gol_subiti_discordi"] = int(
        (v.loc[e_p, "gol_subiti"] != gs[e_p]).sum())
    return v


def pendenza_componenti(c: pd.DataFrame = None) -> pd.DataFrame:
    """La regressione di E3.3, rifatta sulle tre grandezze e per ruolo.

    La riga `comp_voto` del portiere deve riprodurre il `+0.0795` di E3.3: e' il
    controllo che le componenti stiano sulla stessa popolazione, non un risultato
    nuovo. Il risultato nuovo e' la riga `comp_netto`.
    """
    c = componenti_portiere() if c is None else c
    righe = []
    for ruolo in RUOLI_LINEA:
        d = c[c["ruolo"] == ruolo]
        if len(d) < 50:
            continue
        x = d["lam_subiti"]
        amp = float(x.quantile(0.9) - x.quantile(0.1))
        for nome in ("comp_voto", "comp_bonus", "comp_netto"):
            b, se, t = _ols(x, d[nome])
            righe.append({"ruolo": ruolo, "componente": nome, "righe": len(d),
                          "pendenza": b, "se": se, "t": t,
                          "delta_p10_p90": b * amp})
    out = pd.DataFrame(righe)

    # La conseguenza 2, come numero invece che come impressione: quanta parte del
    # malus sopravvive nel netto. Sotto SOGLIA_COMPENSAZIONE si dice compensato.
    p = out[out["ruolo"] == "p"].set_index("componente")["pendenza"]
    out.attrs["quota_malus_superstite"] = (
        float(abs(p["comp_netto"] / p["comp_bonus"]))
        if p.get("comp_bonus") else float("nan"))
    out.attrs["compensazione"] = bool(
        out.attrs["quota_malus_superstite"] < SOGLIA_COMPENSAZIONE)
    return out


def correlazione_componenti(c: pd.DataFrame = None,
                            pavimenti=(1, 5, 10, 19)) -> pd.DataFrame:
    """Correlazione fra le due componenti **attraverso i portieri**.

    E' la conseguenza 3, ed e' la domanda che conta per l'ordinamento: la Spearman
    di E3 confronta portieri fra loro, quindi cio' che la muove e' come le due
    componenti co-variano *da un portiere all'altro*, non dentro la partita.

    **Sulle MEDIE per presenza, non sui totali di stagione**, e la differenza non
    e' cosmetica: il totale del voto cresce col numero di presenze e quello del
    bonus *cala* (ogni presenza in piu' porta altri gol subiti), quindi i totali
    risultano correlati negativamente **attraverso le presenze** anche se le due
    componenti fossero indipendenti. Si riportano entrambe le colonne proprio per
    far vedere che la seconda non e' leggibile come compensazione.

    Il pavimento di presenze e' variato invece che scelto: un portiere con una
    presenza sola ha una media di bonus che e' un conteggio di gol, non un tasso.
    """
    c = componenti_portiere() if c is None else c
    p = c[c["ruolo"] == "p"]
    g = p.groupby(["stagione", "giocatore_id"]).agg(
        presenze=("comp_voto", "size"),
        voto_medio=("comp_voto", "mean"), bonus_medio=("comp_bonus", "mean"),
        voto_totale=("comp_voto", "sum"), bonus_totale=("comp_bonus", "sum"))

    righe = []
    for pav in pavimenti:
        d = g[g["presenze"] >= pav]
        if len(d) < 30:
            continue
        sa, sb = float(d["voto_medio"].std()), float(d["bonus_medio"].std())
        sn = float((d["voto_medio"] + d["bonus_medio"]).std())
        righe.append({
            "pavimento_presenze": pav, "portieri": len(d),
            "corr_medie": float(d["voto_medio"].corr(d["bonus_medio"])),
            "corr_totali": float(d["voto_totale"].corr(d["bonus_totale"])),
            "sd_voto": sa, "sd_bonus": sb, "sd_netto": sn,
            # Quanto il netto e' piu' stretto di quanto sarebbe se le due
            # componenti fossero indipendenti. Positivo = si compensano.
            "compressione_vs_indipendenza": float(
                1 - sn / np.sqrt(sa ** 2 + sb ** 2)),
        })
    return pd.DataFrame(righe)


def pendenza_voto_dal_passato(c: pd.DataFrame = None) -> pd.Series:
    """La pendenza del voto del portiere, stimata sulle SOLE stagioni precedenti.

    Serve a collegare anche il lato del voto senza violare il vincolo 1. Il numero
    di E3.3 (`+0.0795`) e' stimato su tutte e cinque le stagioni, quindi come
    ingrediente di una previsione e' un **oracolo**: si riporta accanto come
    tetto, esattamente come E3.3 riporta `gol_subiti` osservati accanto a
    `lam_subiti`, e non al posto della versione onesta.
    """
    c = componenti_portiere() if c is None else c
    p = c[c["ruolo"] == "p"]
    fuori = {}
    for st in sorted(p["stagione"].unique()):
        passato = p[p["stagione"] < st]
        if len(passato) < 200:
            continue
        fuori[st] = _ols(passato["lam_subiti"], passato["comp_voto"])[0]
    return pd.Series(fuori, name="pendenza_voto_dal_passato")


def collegamento_due_lati(wf: pd.DataFrame = None, gsp: pd.DataFrame = None,
                          c: pd.DataFrame = None) -> pd.DataFrame:
    """Spearman sui portieri collegando la difesa a un lato, all'altro, a entrambi.

    E' la conseguenza operativa dell'ipotesi: **se la compensazione fosse il
    meccanismo, collegare entrambe le componenti dovrebbe recuperare cio' che
    collegarne una sola perde.** E3 aveva collegato solo il bonus
    (`bonus_difensivo_portiere`), lasciando `voto_atteso` indipendente dalla
    squadra; qui si aggiunge il lato del voto, da solo e insieme.

    Le due varianti del lato del voto — pendenza dal passato e pendenza oracolo —
    stanno affiancate perche' se **nemmeno l'oracolo** recupera, la questione non
    e' la qualita' della stima della pendenza.
    """
    from . import modello_asta as MA
    from scipy.stats import spearmanr

    wf = MA.walkforward() if wf is None else wf
    gsp = gol_squadra_partita() if gsp is None else gsp
    c = componenti_portiere() if c is None else c

    d = wf[wf["ruolo"] == "p"].copy()
    d["lam"] = _lam_portieri(d, gsp)
    d = d[d["lam"].notna()]
    lam_rif = float(d["lam"].mean())
    bonus = bonus_difensivo_portiere(d["lam"].to_numpy())

    pend_passato = pendenza_voto_dal_passato(c)
    pend_oracolo = _ols(c.loc[c["ruolo"] == "p", "lam_subiti"],
                        c.loc[c["ruolo"] == "p", "comp_voto"])[0]
    # Il voto corretto per la forza difensiva: si sposta il voto atteso del
    # modello d'asta lungo la pendenza, centrando sulla lam media perche' cio'
    # che si aggiunge e' uno scostamento, non un livello.
    dv_passato = (d["stagione_prevista"].map(pend_passato).astype(float)
                  * (d["lam"] - lam_rif))
    dv_oracolo = pend_oracolo * (d["lam"] - lam_rif)

    d["p_solo_bonus"] = d["presenze_attese"] * (d["voto_atteso"] + bonus)
    d["p_solo_voto"] = d["presenze_attese"] * (
        d["voto_atteso"] + dv_passato + d["bonus_per_presenza_atteso"])
    d["p_entrambi"] = d["presenze_attese"] * (d["voto_atteso"] + dv_passato + bonus)
    d["p_entrambi_oracolo"] = d["presenze_attese"] * (
        d["voto_atteso"] + dv_oracolo + bonus)

    candidati = {"modello d'asta (nessun lato)": "punti_previsti",
                 "solo bonus — e' E3": "p_solo_bonus",
                 "solo voto": "p_solo_voto",
                 "entrambi i lati": "p_entrambi",
                 "entrambi i lati (pendenza ORACOLO)": "p_entrambi_oracolo",
                 "FVM della fonte (CONTAMINATO)": "b_fvm"}

    righe = []
    for soglia in (0, 15, 20):
        x = d[d["presenze_attese"] >= soglia]
        if len(x) < 40:
            continue
        for nome, col in candidati.items():
            s = []
            for _, g in x.groupby("stagione_prevista"):
                ok = g[col].notna() & g["punti_osservati"].notna()
                if ok.sum() >= 5:
                    s.append(spearmanr(g.loc[ok, col],
                                       g.loc[ok, "punti_osservati"]).statistic)
            if s:
                righe.append({"soglia_presenze_attese": soglia, "portieri": len(x),
                              "candidato": nome, "spearman": float(np.mean(s))})
    return pd.DataFrame(righe)


def qualita_componente_difensiva(wf: pd.DataFrame = None,
                                 gsp: pd.DataFrame = None,
                                 min_presenze: int = 10) -> pd.DataFrame:
    """Il bonus difensivo di E3 contro quello storico del portiere, sull'osservato.

    Domanda separata da tutte le precedenti, e va tenuta separata: **la
    componente difensiva di E3 stima peggio o meglio della cosa che ha
    sostituito?** Il modello d'asta usa il bonus per presenza del portiere nelle
    sue stagioni passate; E3 lo rimpiazza con `bonus_difensivo_portiere(lam)`.
    Se il rimpiazzo fosse semplicemente peggiore, l'esito negativo di E3 sarebbe
    spiegato senza scomodare nessuna compensazione.

    Il bersaglio e' il bonus difensivo **per presenza effettivamente realizzato**
    nella stagione bersaglio, sui soli portieri che l'hanno giocata abbastanza da
    avere un tasso invece di un conteggio.
    """
    from . import lega as L, modello_asta as MA, voti as VT

    wf = MA.walkforward() if wf is None else wf
    gsp = gol_squadra_partita() if gsp is None else gsp
    d = wf[wf["ruolo"] == "p"].copy()
    d["lam"] = _lam_portieri(d, gsp)
    d = d[d["lam"].notna()].copy()
    d["dif_e3"] = bonus_difensivo_portiere(d["lam"].to_numpy())

    src = VT.carica()
    src = src[(src["ruolo"] == "p") & ~src["allenatore"]
              & src["voto_redazione"].notna()]
    src = src.assign(b=L.BONUS["gol_subiti"] * src["gol_subiti"]
                     + L.BONUS["porta_inviolata"] * (src["gol_subiti"] == 0))
    oss = src.groupby(["stagione", "giocatore_id"])["b"].agg(["mean", "size"])
    oss.columns = ["bonus_osservato", "presenze_osservate_voti"]

    d = d.join(oss, on=["stagione_prevista", "giocatore_id"])
    q = d[d["presenze_osservate_voti"].fillna(0) >= min_presenze]

    righe = []
    for nome, col in (("bonus storico del portiere (il modello d'asta)",
                       "bonus_per_presenza_atteso"),
                      ("difesa E3 (modello di squadra)", "dif_e3")):
        righe.append({
            "stimatore": nome,
            # DUE DENOMINATORI DIVERSI, ed e' voluto. La qualita' della stima si
            # puo' misurare solo su chi ha giocato abbastanza da avere un tasso
            # invece di un conteggio; la correlazione con le presenze va invece
            # misurata su **tutti** i portieri, perche' e' la popolazione su cui
            # la Spearman di E3 e' calcolata. Restringerla ai titolari
            # troncherebbe proprio la variabile di cui si chiede la correlazione.
            "portieri_qualita": len(q),
            "mae": float((q[col] - q["bonus_osservato"]).abs().mean()),
            "corr": float(q[col].corr(q["bonus_osservato"])),
            "portieri_tutti": len(d),
            # Quanta informazione sul GIOCARE porta con se' ciascuno stimatore.
            # E' l'unico canale per cui uno stimatore peggiore del bonus puo'
            # produrre un ordinamento migliore dei punti di stagione.
            "corr_con_presenze": float(d[col].corr(d["presenze_osservate"])),
        })
    return pd.DataFrame(righe)
