# -*- coding: utf-8 -*-
"""Fase 14 / A2 — il prior dalla stagione precedente, e la sua validazione.

IL PROBLEMA CHE QUESTO MODULO ESISTE PER COPRIRE
------------------------------------------------
Il modello di squadra e' **within-season** in tutto il repository, e non per
comodita': le squadre cambiano fra un'annata e l'altra, e un'emivita di 150
giorni attraverso l'estate darebbe alla prima giornata di settembre un training
fatto quasi solo di maggio (E3, poi V1, poi la Fase 13).

La conseguenza e' che a stagione appena cominciata **non c'e' niente su cui
stimare**: `previsione()` restituisce un numero dominato dall'intercetta, e V1
non lo valuta nemmeno (burn-in alla 6a giornata). Chi vuole una previsione a
settembre non ce l'ha.

QUELLO CHE SI FA QUI, E PERCHE' E' UNA RIGA SOLA DI MATEMATICA
--------------------------------------------------------------
`TeamModel` tira attacco e difesa **verso zero**, cioe' verso la media di
campionato. Il prior sposta quel centro sui coefficienti di **fine stagione
precedente**:

    reg = alpha_prior * SUM pen * (b - b_prior)^2

Quattro proprieta' che rendono questa la forma giusta, e nessuna e' un'opinione:

1. **A zero partite giocate il fit restituisce il prior**, e man mano che le
   partite arrivano la verosimiglianza cresce con `n` mentre la penalita' resta
   fissa: **il prior si scioglie da solo**. Non c'e' nessun decadimento da
   sintonizzare, e quindi nessun iperparametro in piu' da adattare al campione.
2. **Porta la forza RELATIVA, non il livello.** `mu` e `gamma` non sono
   penalizzati, quindi il livello della stagione nuova lo imparano i dati nuovi.
   E' cio' che evita il difetto di famiglia gia' misurato due volte: i cinque
   fit di xG di E4 (forma stabile, livello che si muove del 15,8%) e i tentativi
   di V0 (livello che si muove del 5,5% fra le cinque stagioni).
3. **Il prior va CENTRATO**, e non e' cosmesi. Una neopromossa non ha prior e
   riceve centro zero. Se la media dei coefficienti noti non fosse zero, quello
   zero non sarebbe «la media di campionato» ma un punto arbitrario accanto — e
   le tre neopromosse verrebbero sistematicamente sopra o sotto le altre
   diciassette per un motivo che non ha niente a che vedere con quanto tirano.
4. **Un fit per campionato, mai poolati.** E' la regola di E1 che R0 aveva gia'
   scritto in anticipo su G2 e che la Fase 13 ha reso un numero: il livello dei
   gol varia del 25% fra i cinque campionati.

LA VALIDAZIONE, DICHIARATA PRIMA DI GUARDARE I NUMERI
------------------------------------------------------
Il blocco introduce **modellazione**, quindi non si pubblica finche' non e'
misurato — ed e' misurato contro il baseline che conta davvero, «l'anno prossimo
come l'anno scorso», che in Fase 8 ha gia' battuto un modello di questo
repository.

* **campione**: le transizioni `s-1 -> s`, per tutti e cinque i campionati.
* **bersaglio**: le righe con `team_match_idx <= IDX_AVVIO`, cioe' esattamente
  il buco. Le righe da `IDX_AVVIO + 1` in poi sono il **controllo**: li' il
  prior deve valere circa zero, e se valesse molto vorrebbe dire che sta
  sostituendo informazione che i dati nuovi hanno gia'.
* **candidati** (vincolo 6): con prior · senza prior · media di squadra di s-1 ·
  media di campionato di s-1. Gli ultimi due sono noti **prima** che la stagione
  cominci, quindi sono concorrenti leali.
* **metrica**: log-verosimiglianza Poisson per riga e MAE, con `t` appaiato
  **per cluster di partita** — l'unita' indipendente e' la partita, non la
  squadra-partita.
* **`alpha_prior` si sceglie sul solo PASSATO** (`scegli_alpha_prior`): per
  valutare la transizione verso `s` si usa la migliore delle transizioni
  precedenti. La prima transizione non ha un passato su cui tararsi e resta
  **marcata come non tarata**, esattamente come la 2021-2022 in R2-bis.

E' un blocco che puo' finire in negativo. Se il prior non batte «media squadra
dell'anno scorso», **non si adotta**, e la pagina dichiara che sotto la 6a
giornata la previsione non c'e'. Non si ritocca `alpha_prior` finche' il numero
diventa gradevole.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from . import config, model_team as MT, tentativi as T, validate as V

#: Il bersaglio principale del blocco. `sot` si ottiene passando `target`.
TARGET = T.TARGET

#: Le righe che il blocco esiste per coprire: le prime cinque partite di una
#: squadra, cioe' quelle che il burn-in di `config.BURN_IN_ROUND` esclude.
#: **Non e' una soglia scelta qui**: e' il complemento di una soglia gia'
#: dichiarata dalla Fase 2 e usata da tutto il repository.
IDX_AVVIO = config.BURN_IN_ROUND - 1

#: Fin dove si spinge il **controllo**. Le righe fra `IDX_AVVIO + 1` e qui sono
#: gia' coperte dal modello within-season: li' il prior non deve servire.
IDX_CONTROLLO = 12

#: La griglia di `alpha_prior`, **dichiarata prima** e con gli estremi larghi di
#: proposito. Un ottimo sul bordo non e' una scelta ma l'esaurimento delle
#: opzioni — e' il difetto che la Fase 5 ha trovato su `tau`, e
#: `scegli_alpha_prior` lo segnala invece di lasciarlo passare.
ALPHA_PRIOR_GRID = (0.5, 1.0, 3.0, 6.0, 12.0, 25.0, 50.0, 100.0, 200.0)

#: I cinque candidati, nell'ordine in cui si leggono.
#:
#: `modello prec` e' il modello di fine stagione precedente applicato **tale e
#: quale**, senza guardare una sola partita nuova: e' il caso limite
#: `alpha_prior -> infinito`. Sta qui perche' senza di lui un esito negativo
#: sarebbe ambiguo — non si saprebbe se a non funzionare sia il **prior** (la
#: forza dell'anno scorso non si trasporta) o la **miscela** (il prior va bene ma
#: le poche partite nuove lo rovinano). Sono due diagnosi diverse con due rimedi
#: diversi, ed e' la stessa forma della `ridondanza_cartellini` di E2, che
#: distingueva «e' gia' nel set» da «non c'e' segnale».
CANDIDATI = ("con prior", "senza prior", "modello prec", "media squadra prec",
             "media campionato prec")

CRITERIO_ADOZIONE = (
    "il prior si adotta se, sulle righe di avvio (team_match_idx <= 5) e sulle "
    "sole transizioni TARATE: (a) batte «media squadra prec» in log-verosimiglianza "
    "per riga con t appaiato per cluster di partita sopra 2, e (b) il segno del "
    "margine e' positivo in almeno 3 campionati su 5. Altrimenti non si adotta e "
    "la previsione sotto la 6a giornata resta dichiarata non disponibile."
)


# --------------------------------------------------------------------------
# Il prior
# --------------------------------------------------------------------------
def centra(d: dict) -> dict:
    """Sottrae la media: lo zero delle assenti diventa la media delle presenti.

    Senza, il centro della penalita' per una neopromossa (`0`) e quello per una
    squadra media (`media dei noti`) sarebbero due punti diversi, e le tre
    neopromosse finirebbero tutte dalla stessa parte per un motivo aritmetico.
    """
    if not d:
        return {}
    m = float(np.mean(list(d.values())))
    return {k: float(v) - m for k, v in d.items()}


@dataclass(frozen=True)
class Prior:
    """I coefficienti di fine stagione precedente, gia' centrati."""

    campionato: str
    stagione_origine: str
    target: str
    alpha: float
    attacco: dict = field(default_factory=dict)
    difesa: dict = field(default_factory=dict)
    mu: float = 0.0
    gamma: float = 0.0
    partite: int = 0

    def come_centro(self) -> dict:
        """La forma che `TeamModel.prior` si aspetta: squadra -> (att, dif)."""
        return {t: (self.attacco[t], self.difesa.get(t, 0.0))
                for t in self.attacco}

    def squadre(self) -> set:
        return set(self.attacco)


def alpha_del_campionato(league: str | None = None) -> float:
    """L'`alpha` gia' scelto dal walk-forward di V1 per quel campionato.

    Non si sceglie qui: e' la stessa mediana che `previsione.modello_alla_data`
    usa, e prenderne un'altra farebbe divergere due strade che devono dare lo
    stesso numero.
    """
    from . import volume as VL
    wf = VL.walkforward_tiri(league=league)
    return float(wf.loc[wf["eligible"], "alpha"].median())


def fit_fine_stagione(stagione: str, league: str | None = None,
                      target: str = TARGET, alpha: float | None = None,
                      u: pd.DataFrame | None = None) -> Prior:
    """Il modello di squadra stimato su una stagione INTERA, gia' finita.

    E' una **descrizione** della stagione passata, non una previsione, e non c'e'
    leakage: quando la si usa come prior, la stagione da cui viene e' finita da
    mesi. `as_of` e' l'ultima data della stagione, quindi i pesi a decadimento
    contano di piu' il finale — che e' cio' che si vuole trasportare.
    """
    alpha = alpha_del_campionato(league) if alpha is None else alpha
    u = T.universo([stagione], league=league) if u is None else u
    d = u[u["stagione"] == stagione]
    if not len(d):
        raise ValueError(f"nessuna partita in {stagione} per {league}")

    m = MT.TeamModel(alpha=alpha, target=target).fit(d)
    r = m.ratings()
    return Prior(
        campionato=config.LEAGUE if league is None else league,
        stagione_origine=stagione, target=target, alpha=alpha,
        attacco=centra(dict(zip(r["team"], r["attack"]))),
        difesa=centra(dict(zip(r["team"], r["defence"]))),
        mu=float(m.mu_), gamma=float(m.home_advantage),
        partite=int(d["matchId"].nunique()),
    )


def stagione_precedente(stagione: str) -> str | None:
    """La stagione prima, se e' fra le storiche. `None` se non c'e'."""
    storiche = list(config.SEASONS_STORICHE)
    if stagione in storiche:
        i = storiche.index(stagione)
        return storiche[i - 1] if i > 0 else None
    # una stagione fuori dall'elenco (quella in corso) prende l'ultima storica
    return storiche[-1] if stagione > storiche[-1] else None


def prior_per(stagione: str, league: str | None = None,
              target: str = TARGET, alpha: float | None = None) -> Prior | None:
    """Il prior da usare per `stagione`: il fit della stagione prima."""
    prec = stagione_precedente(stagione)
    if prec is None:
        return None
    return fit_fine_stagione(prec, league=league, target=target, alpha=alpha)


# --------------------------------------------------------------------------
# I due baseline che vengono da fuori stagione
# --------------------------------------------------------------------------
def baseline_precedente(stagione: str, league: str | None = None,
                        target: str = TARGET) -> dict:
    """«L'anno prossimo come l'anno scorso», nelle sue due forme.

    E' il concorrente vero: in Fase 8 la persistenza ha battuto il modello
    d'asta, e un prior che non la superasse sarebbe un modo complicato di dire
    la stessa cosa.
    """
    prec = stagione_precedente(stagione)
    if prec is None:
        return {"stagione_origine": None, "per_squadra": {}, "campionato": np.nan}
    u = T.universo([prec], league=league)
    d = u[u["stagione"] == prec]
    return {
        "stagione_origine": prec,
        "per_squadra": d.groupby("team")[target].mean().to_dict(),
        # la media di campionato copre le neopromosse, che un anno fa non c'erano
        "campionato": float(d[target].mean()),
    }


# --------------------------------------------------------------------------
# Le previsioni di avvio stagione
# --------------------------------------------------------------------------
def previsioni_avvio(stagione: str, league: str | None = None,
                     target: str = TARGET,
                     alpha_prior: float = 12.0,
                     fino_a: int = IDX_CONTROLLO,
                     prior: Prior | None = None,
                     base: dict | None = None) -> pd.DataFrame:
    """Walk-forward sulle prime giornate: quattro candidati sulle stesse righe.

    Per ogni **data** della stagione si stima sulle partite **strettamente
    precedenti** e si prevede quelle del giorno. E' la stessa regola esclusiva
    di `walkforward.date_splits`, ma senza il suo minimo di 30 partite di
    training: quel minimo e' proprio cio' che rende invisibili le prime
    giornate, ed e' il buco che questo blocco misura.

    Alla primissima data il training e' **vuoto** e `TeamModel` non si stima
    affatto. Li' la previsione con prior e' il modello di fine stagione
    precedente applicato tale e quale — `mu` e `gamma` compresi, perche' senza
    dati non ci sono altri numeri da cui prenderli — e la variante «senza prior»
    non ha nessuna previsione. E' il modo piu' onesto di dire che il modello
    within-season, li', **non risponde**.
    """
    alpha = alpha_del_campionato(league)
    prior = prior_per(stagione, league, target, alpha) if prior is None else prior
    base = baseline_precedente(stagione, league, target) if base is None else base
    if prior is None:
        return pd.DataFrame()

    u = T.universo([stagione], league=league)
    d = u[u["stagione"] == stagione].sort_values("date").reset_index(drop=True)
    d = d[d["team_match_idx"] <= fino_a]
    if not len(d):
        return pd.DataFrame()

    teams = sorted(set(d["team"]) | set(d["opponent"]))
    centro = prior.come_centro()
    tutte = u[u["stagione"] == stagione]

    pezzi = []
    for giorno in sorted(d["date"].unique()):
        oggi = d[d["date"] == giorno]
        # il training e' TUTTA la stagione fino a ieri, non solo le prime
        # giornate: restringerlo alle righe valutate toglierebbe informazione
        # che a quel momento esisteva davvero
        storia = tutte[tutte["date"] < giorno]

        riga = oggi[["team", "opponent", "is_home"]].copy()

        # Il modello dell'anno scorso applicato tale e quale: nessuna partita
        # nuova guardata. E' il caso limite `alpha_prior -> infinito`, e serve a
        # separare «il prior non si trasporta» da «la miscela lo rovina».
        lam_prec = np.exp(
            prior.mu
            + riga["team"].map(prior.attacco).fillna(0.0).to_numpy()
            + riga["opponent"].map(prior.difesa).fillna(0.0).to_numpy()
            + prior.gamma * riga["is_home"].to_numpy())

        if len(storia):
            m_p = MT.TeamModel(alpha=alpha, target=target, prior=centro,
                               alpha_prior=alpha_prior).fit(storia, teams=teams)
            m_s = MT.TeamModel(alpha=alpha, target=target).fit(storia, teams=teams)
            lam_p = m_p.predict(riga)
            lam_s = m_s.predict(riga)
        else:
            # nessuna partita giocata: il prior e' tutto cio' che c'e', e la
            # variante senza prior **non risponde** — dirlo con un NaN e' piu'
            # onesto che riempirlo con l'intercetta di un fit inesistente
            lam_p = lam_prec
            lam_s = np.full(len(riga), np.nan)

        out = oggi[["matchId", "date", "team", "opponent", "is_home",
                    "team_match_idx", target]].copy()
        out["lam_con_prior"] = lam_p
        out["lam_senza_prior"] = lam_s
        out["lam_modello_prec"] = lam_prec
        out["lam_media_squadra_prec"] = (
            out["team"].map(base["per_squadra"]).fillna(base["campionato"]))
        out["lam_media_campionato_prec"] = base["campionato"]
        out["partite_di_storia"] = int(storia["matchId"].nunique())
        # quante squadre di questa stagione il prior non conosce: e' il costo
        # dichiarato delle neopromosse, contato invece che subito
        out["senza_prior_in_rosa"] = (
            (~out["team"].isin(prior.squadre())).astype(int)
            + (~out["opponent"].isin(prior.squadre())).astype(int))
        pezzi.append(out)

    res = pd.concat(pezzi, ignore_index=True)
    res["stagione"] = stagione
    res["campionato"] = config.LEAGUE if league is None else league
    res["alpha_prior"] = alpha_prior
    res["avvio"] = res["team_match_idx"] <= IDX_AVVIO
    return res


# --------------------------------------------------------------------------
# Valutazione
# --------------------------------------------------------------------------
_COL = {"con prior": "lam_con_prior",
        "senza prior": "lam_senza_prior",
        "modello prec": "lam_modello_prec",
        "media squadra prec": "lam_media_squadra_prec",
        "media campionato prec": "lam_media_campionato_prec"}


def _colonne(d: pd.DataFrame) -> dict:
    """I candidati presenti nel frame.

    `due regimi` compare **solo** se la colonna c'e': e' una composizione di due
    candidati gia' dichiarati, non un sesto modello, e non deve entrare nei
    confronti in cui non e' stata costruita.
    """
    c = dict(_COL)
    if "lam_due_regimi" in d.columns:
        c["due regimi"] = "lam_due_regimi"
    return c


def _righe_confrontabili(prev: pd.DataFrame, avvio: bool = True) -> pd.DataFrame:
    """Le righe su cui **tutti e quattro** i candidati hanno una previsione.

    Senza questo filtro il confronto sarebbe verticale invece che orizzontale:
    «senza prior» non risponde alla primissima giornata, e confrontare la sua
    media su un campione piu' facile con quella degli altri su uno piu' difficile
    e' l'errore che E4 ha dovuto correggere sul divario dei bonus.
    """
    d = prev[prev["avvio"]] if avvio else prev[~prev["avvio"]]
    return d.dropna(subset=list(_colonne(d).values())).copy()


def valutazione(prev: pd.DataFrame, avvio: bool = True) -> pd.DataFrame:
    """MAE e log-verosimiglianza per riga dei quattro candidati."""
    d = _righe_confrontabili(prev, avvio)
    if not len(d):
        return pd.DataFrame()
    y = d[TARGET if TARGET in d.columns else "sot"].to_numpy(dtype=float)
    righe = []
    for nome, col in _colonne(d).items():
        lam = d[col].to_numpy(dtype=float)
        righe.append({
            "candidato": nome,
            "n": len(d),
            "mae": float(np.abs(lam - y).mean()),
            "bias": float((lam - y).mean()),
            "loglik_per_riga": float(MT.poisson_loglik(y, lam).mean()),
        })
    return pd.DataFrame(righe)


def confronto(prev: pd.DataFrame, avvio: bool = True,
              contro: str = "media squadra prec",
              soggetto: str = "con prior") -> pd.DataFrame:
    """Il margine di `soggetto` sugli altri, con il `t` per cluster di partita.

    Il `t` **per riga** viene riportato accanto e non al posto: l'unita'
    indipendente e' la partita, ma un fattore favorevole non dichiarato resta un
    numero sbagliato (e' la lezione di V1).
    """
    d = _righe_confrontabili(prev, avvio)
    if not len(d):
        return pd.DataFrame()
    col_y = TARGET if TARGET in d.columns else "sot"
    y = d[col_y].to_numpy(dtype=float)
    cols = _colonne(d)
    ll = {k: MT.poisson_loglik(y, d[c].to_numpy(dtype=float))
          for k, c in cols.items()}

    righe = []
    for nome in cols:
        if nome == soggetto:
            continue
        _, t_riga = V.paired_t(ll[soggetto], ll[nome])
        _, t_clus = V.paired_t(ll[soggetto], ll[nome], cluster=d["matchId"])
        delta = float((ll[soggetto] - ll[nome]).mean())
        righe.append({
            "soggetto": soggetto, "avversario": nome, "n": len(d),
            "delta_loglik_per_riga": delta,
            "t_riga": t_riga, "t_cluster": t_clus,
            "vince_il_soggetto": bool(delta > 0),
            "riferimento": nome == contro,
        })
    return pd.DataFrame(righe).sort_values("delta_loglik_per_riga")


def per_indice(prev: pd.DataFrame) -> pd.DataFrame:
    """Log-verosimiglianza di ogni candidato **per giornata di squadra**.

    E' una descrizione, non una scelta: dice **dove** i due regimi si scambiano,
    e serve a sapere se la soglia gia' dichiarata dal repository
    (`config.BURN_IN_ROUND`) cade dove i dati la metterebbero. Se cadesse
    altrove, il fatto andrebbe scritto — non la soglia spostata, che sarebbe
    sceglierla guardando il bersaglio.
    """
    cols = _colonne(prev)
    d = prev.dropna(subset=list(cols.values())).copy()
    if not len(d):
        return pd.DataFrame()
    col_y = TARGET if TARGET in d.columns else "sot"
    y = d[col_y].to_numpy(dtype=float)
    for nome, col in cols.items():
        d[f"ll::{nome}"] = MT.poisson_loglik(y, d[col].to_numpy(dtype=float))

    g = (d.groupby("team_match_idx")[[f"ll::{n}" for n in cols]]
         .mean().reset_index())
    g.columns = ["team_match_idx"] + list(cols)
    g["n"] = d.groupby("team_match_idx").size().to_numpy()
    g["migliore"] = g[list(cols)].idxmax(axis=1)
    return g


#: La regola dei DUE REGIMI, scritta come composizione di due candidati gia'
#: dichiarati a una soglia gia' dichiarata **altrove**.
#:
#: Non e' un terzo modello e non ha parametri propri: sotto `config.BURN_IN_ROUND`
#: si usa `modello prec` (la stagione scorsa applicata tale e quale), da li' in su
#: `con prior` (la miscela). La soglia **non e' stata scelta qui**: e' la stessa
#: che la Fase 2 ha dichiarato e che tutto il repository usa come burn-in, ed e'
#: la stessa disciplina con cui la Fase 8 ha tenuto l'80' invece di leggerlo da
#: un `argmax`.
REGOLA_DUE_REGIMI = (
    f"team_match_idx < {config.BURN_IN_ROUND}: `modello prec`; "
    f"team_match_idx >= {config.BURN_IN_ROUND}: `con prior`. La soglia e' "
    "`config.BURN_IN_ROUND`, dichiarata dalla Fase 2 e non scelta qui."
)


def con_due_regimi(prev: pd.DataFrame) -> pd.DataFrame:
    """Aggiunge la colonna della regola a due regimi. Nessun parametro nuovo."""
    d = prev.copy()
    sotto = d["team_match_idx"] < config.BURN_IN_ROUND
    d["lam_due_regimi"] = np.where(sotto, d["lam_modello_prec"],
                                   d["lam_con_prior"])
    return d


def mde_relativo(prev: pd.DataFrame, avvio: bool = True,
                 contro: str = "media squadra prec",
                 soggetto: str = "con prior",
                 potenza: float = 0.80, alpha: float = 0.05) -> dict:
    """Il minimo effetto rilevabile, **in quota del margine misurato**.

    In unita' assolute i MDE di due bersagli non sono confrontabili — V3 l'ha
    misurato e ha dovuto cambiare unita' — quindi si riporta il rapporto
    `delta / MDE`: sotto 1 il test **non conclude**, e dirlo e' diverso da dire
    che l'effetto non c'e'.
    """
    from scipy import stats

    d = _righe_confrontabili(prev, avvio)
    if not len(d):
        return {}
    y = d[TARGET if TARGET in d.columns else "sot"].to_numpy(dtype=float)
    a = MT.poisson_loglik(y, d[_colonne(d)[soggetto]].to_numpy(dtype=float))
    b = MT.poisson_loglik(y, d[_colonne(d)[contro]].to_numpy(dtype=float))

    diff = pd.Series(a - b).groupby(np.asarray(d["matchId"])).mean().to_numpy()
    n = len(diff)
    se = float(diff.std(ddof=1) / np.sqrt(n)) if n > 1 else np.nan
    z = stats.norm.isf(alpha / 2) + stats.norm.isf(1 - potenza)
    mde = z * se
    delta = float(diff.mean())
    return {"soggetto": soggetto, "contro": contro,
            "n_cluster": n, "delta": delta, "se": se,
            "mde": mde, "delta_su_mde": delta / mde if mde else np.nan}


# --------------------------------------------------------------------------
# La griglia completa, calcolata una volta e messa in cache
# --------------------------------------------------------------------------
def cache(league: str | None = None, target: str = TARGET):
    """Una cache per campionato: i campionati non si poolano nemmeno su disco."""
    return (config.processed_league_dir(league)
            / f"fase14_prior_avvio_{target}.parquet")


def griglia_avvio(league: str | None = None, target: str = TARGET,
                  stagioni=None, griglia=ALPHA_PRIOR_GRID,
                  force: bool = False, verbose: bool = True) -> pd.DataFrame:
    """Le previsioni di avvio per ogni transizione e ogni `alpha_prior`.

    Si calcola **una volta sola** e i regimi si applicano dopo: ricalcolarla per
    ogni scelta di `alpha_prior` renderebbe i confronti non appaiati sulle stesse
    righe, che e' la condizione perche' il `t` appaiato significhi qualcosa.
    """
    percorso = cache(league, target)
    if percorso.is_file() and not force and stagioni is None:
        return pd.read_parquet(percorso)

    # la prima stagione storica non ha una stagione prima: niente prior
    stagioni = list(config.SEASONS_STORICHE[1:]) if stagioni is None else list(stagioni)

    pezzi = []
    for st in stagioni:
        # il prior e i baseline non dipendono da `alpha_prior`: si calcolano una
        # volta per stagione invece che una per punto della griglia
        p = prior_per(st, league=league, target=target)
        b = baseline_precedente(st, league=league, target=target)
        if p is None:
            continue
        for a in griglia:
            r = previsioni_avvio(st, league=league, target=target,
                                 alpha_prior=a, prior=p, base=b)
            if len(r):
                pezzi.append(r)
        if verbose:
            print(f"    {league or config.LEAGUE} {st}: "
                  f"{len(griglia)} punti di griglia")

    if not pezzi:
        return pd.DataFrame()
    out = pd.concat(pezzi, ignore_index=True)
    if stagioni == list(config.SEASONS_STORICHE[1:]):
        percorso.parent.mkdir(parents=True, exist_ok=True)
        out.to_parquet(percorso, index=False)
    return out


# --------------------------------------------------------------------------
# La scelta di `alpha_prior`, sul solo passato
# --------------------------------------------------------------------------
def scegli_alpha_prior(g: pd.DataFrame, stagioni, target: str = TARGET,
                       griglia=ALPHA_PRIOR_GRID) -> dict:
    """Il migliore `alpha_prior` sulle transizioni date. Vincolo 1.

    Chi la chiama passa **solo transizioni precedenti** a quella che poi
    valutera': tararlo sulla stessa stagione su cui lo si riporta sarebbe
    scegliere un iperparametro guardando il bersaglio, che e' l'errore che
    `tests/test_figures.py` blocca su `tau` dalla Fase 5.

    Segnala se l'ottimo cade **sul bordo** della griglia: un ottimo sul bordo non
    e' una scelta, e' l'esaurimento delle opzioni.
    """
    stagioni = list(stagioni)
    if not len(g) or not stagioni:
        return {"alpha_prior": None, "tabella": pd.DataFrame(), "sul_bordo": False}

    d = g[g["stagione"].isin(stagioni)]
    d = _righe_confrontabili(d, avvio=True)
    if not len(d):
        return {"alpha_prior": None, "tabella": pd.DataFrame(), "sul_bordo": False}

    y = d[target].to_numpy(dtype=float)
    ll = MT.poisson_loglik(y, d["lam_con_prior"].to_numpy(dtype=float))
    tab = (pd.DataFrame({"alpha_prior": d["alpha_prior"].to_numpy(), "ll": ll})
           .groupby("alpha_prior")["ll"].agg(["mean", "size"])
           .rename(columns={"mean": "loglik_per_riga", "size": "n"})
           .reset_index())

    best = tab.loc[tab["loglik_per_riga"].idxmax()]
    return {"alpha_prior": float(best["alpha_prior"]), "tabella": tab,
            "sul_bordo": bool(best["alpha_prior"] in (griglia[0], griglia[-1]))}


def alpha_prior_produzione(league: str | None = None,
                           target: str = TARGET) -> float | None:
    """L'`alpha_prior` da usare sulla stagione IN CORSO.

    Tarato su **tutte** le transizioni storiche di quel campionato, che sono
    tutte precedenti alla stagione in corso: il vincolo 1 e' rispettato per
    costruzione, e non c'e' niente da lasciare fuori come in validazione — li'
    la transizione valutata andava esclusa, qui non e' fra quelle.
    """
    g = griglia_avvio(league=league, target=target, verbose=False)
    if not len(g):
        return None
    return scegli_alpha_prior(g, list(config.SEASONS_STORICHE[1:]),
                              target=target)["alpha_prior"]


def contesto(stagione: str, league: str | None = None,
             bersagli=("shots", "sot")) -> dict:
    """Tutto cio' che serve a prevedere una stagione in corso, per bersaglio.

    Un dizionario `bersaglio -> {prior, alpha_prior}`. Se il prior non esiste
    (nessuna stagione precedente acquisita) il valore e' `None`, e chi lo usa
    deve **dirlo** invece di ripiegare in silenzio sulla sola intercetta.
    """
    out = {}
    for t in bersagli:
        try:
            p = prior_per(stagione, league=league, target=t)
        except (FileNotFoundError, ValueError):
            p = None
        out[t] = {"prior": p,
                  "alpha_prior": (alpha_prior_produzione(league, t)
                                  if p is not None else None)}
    return out


def lam_dal_prior(p: Prior, squadra, avversario, in_casa) -> np.ndarray:
    """Il modello dell'anno scorso applicato tale e quale.

    E' il candidato che A2 ha misurato come migliore sulle righe di avvio, e
    l'unica risposta possibile quando la stagione nuova non ha ancora partite.
    Una squadra che il prior non conosce (neopromossa) prende `0`, cioe' la
    media di campionato dell'anno scorso: e' l'unico default onesto, e chi
    pubblica il numero deve **contarle** invece di lasciarle sparire.
    """
    squadra = pd.Series(squadra)
    avversario = pd.Series(avversario)
    return np.exp(
        p.mu
        + squadra.map(p.attacco).fillna(0.0).to_numpy(dtype=float)
        + avversario.map(p.difesa).fillna(0.0).to_numpy(dtype=float)
        + p.gamma * np.asarray(in_casa, dtype=float))


def verdetto(conf: pd.DataFrame, segni: pd.Series | None = None) -> dict:
    """Applica `CRITERIO_ADOZIONE` meccanicamente, senza rileggerlo a occhio."""
    if not len(conf):
        return {"adotta": False, "perche": "nessuna riga valutabile"}
    rif = conf[conf["riferimento"]]
    if not len(rif):
        return {"adotta": False, "perche": "manca il baseline di riferimento"}
    t = float(rif.iloc[0]["t_cluster"])
    n_pos = int((segni > 0).sum()) if segni is not None else 0
    ok_t = t > 2.0
    ok_segni = n_pos >= 3
    return {"adotta": bool(ok_t and ok_segni), "t_cluster": t,
            "campionati_positivi": n_pos,
            "perche": ("adottato" if ok_t and ok_segni else
                       f"t = {t:.2f} (serve > 2) e {n_pos}/5 campionati positivi "
                       "(ne servono 3)")}
