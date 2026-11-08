# -*- coding: utf-8 -*-
"""Fase 15 / Blocco T1 — il TOTALE di partita: la somma delle due squadre.

**E' la domanda aperta n. 3 di V1 e n. 3 di V4**, lasciata aperta due volte con
la stessa motivazione: «il totale di partita e' la linea di mercato piu' comune,
ma la correlazione negativa misurata da V0 dice che **non e' la somma di due
indipendenti**: serve la congiunta, che sui tentativi non e' misurata».

Questo blocco la chiude, e la chiude **senza costruire una congiunta**.

LA SCELTA, E PERCHE' NON E' UNA SCORCIATOIA
-------------------------------------------
Della somma di due variabili dipendenti, **la media e' esatta comunque**:
`E[X+Y] = E[X] + E[Y]` non richiede nessuna ipotesi. Quello che la dipendenza
rompe e' la **dispersione**, e con essa le probabilita' Over:

    Var(X+Y) = Var(X) + Var(Y) + 2*Cov(X,Y)

Con `rho = -0,346` fra i due lati (V0 misuro' -0,349 sul suo perimetro) la
covarianza e' **negativa**, quindi il totale e' MENO disperso della somma di due
indipendenti. In numeri: sotto indipendenza la sd del totale varrebbe
`sqrt(2)*5,215 = 7,375`; si osserva **5,823**, il 21% in meno.

La strada presa e' una **NB2 diretta sul totale**: `lambda_tot` e' la somma dei
due lambda — esatta — e `r_tot` si stima **sui totali osservati**, cioe' la
dipendenza viene assorbita da una misura invece che assunta via. Non serve una
congiunta bidimensionale e non serve la convoluzione.

**L'alternativa non e' stata cancellata**: `confronto_indipendenza()` calcola la
convoluzione delle due NB2 per lato e la mette accanto. Toglierla renderebbe la
scelta un'asserzione invece di un confronto — e' la stessa ragione per cui V2
tiene in tabella il modello diretto contro la marginale composta.

`r_tot` NON SI EREDITA, E LO SI MISURA
---------------------------------------
Il precedente e' `precisione.rapporto_dispersioni()`, che ha **falsificato**
l'ereditarieta' fra `r_shots` e `r_sot` (rapporto 1,63, IC95 [1,15, 2,80]). Qui
la domanda e' la stessa un piano piu' su: `r_tot` si puo' prendere da `r` per
lato? `rapporto_dispersioni()` risponde con un IC bootstrap, e la direzione
attesa dalla teoria e' quella della correlazione negativa.

LA RIGA E' LA PARTITA
---------------------
La rotazione da squadra-partita a partita e' **quella di R0**
(`perimetro.partite()`), ripetuta nei suoi due controlli e nella sua verifica
gratuita via `lam_subiti`, non reinventata. Ne segue che:

- le righe valutabili non sono 3.278 ma **1.638** — lo stesso numero che R0
  contava sui gol, ed e' il controllo interno piu' forte disponibile;
- la condizione e' `elig_casa AND elig_trasferta`, mai `or`: un totale non e'
  meta' previsto;
- **il `t` per cluster di partita diventa degenere**, perche' una riga *e'* una
  partita. I due `t` coincidono per costruzione, e va detto invece di
  presentarlo come una robustezza guadagnata.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from . import config, tentativi as T, volume as VL

#: I due bersagli, quelli di V0. Il totale e' una loro funzione: non esiste una
#: colonna `tiri_totali` nel derivato e non va creata — `team_match` resta
#: grezzo (regola di E1), la somma vive qui.
TARGET = T.TARGET                        # "shots"
TARGET_PRECISIONE = T.TARGET_PRECISIONE  # "sot"

#: La regola con cui le linee del TOTALE sono state scelte, scritta prima dei
#: numeri perche' sia falsificabile che sia stata seguita. E' la
#: `tentativi.REGOLA_LINEE` applicata alla media dei **totali**, non una regola
#: nuova: cambiarla insieme al bersaglio renderebbe i due esperimenti non
#: confrontabili, che e' il difetto contro cui esiste il vincolo 7.
REGOLA_LINEE_TOTALE = (
    "la REGOLA_LINEE di V0 applicata al totale di partita: multipli interi + "
    "0,5 (convenzione di mercato), passo scelto per coprire lo stesso "
    "intervallo in deviazioni standard che le linee per squadra coprono, "
    "centrati sul multiplo piu' vicino alla media dei totali; estesi finche' il "
    "tasso base resta dentro tentativi.BASE_RATE_AMMESSO."
)

#: Le linee Over sul **totale dei tentativi**. Media 25,161, sd 5,823: stanno a
#: -0,80 / -0,46 / -0,11 / +0,23 / +0,57 deviazioni standard, cioe' lo **stesso
#: esperimento** di `tentativi.LINEE_TIRI` per squadra (-0,78 / -0,40 / -0,02 /
#: +0,37 / +0,75). Tassi base osservati 0,786 / 0,663 / 0,527 / 0,379 / 0,265,
#: tutti dentro `BASE_RATE_AMMESSO`. Il passo resta 2 e non 2,3 — che
#: allineerebbe le sd alla terza cifra — perche' 2 e' la convenzione di mercato
#: e la differenza sta sotto la risoluzione dell'esperimento.
LINEE_TOTALE_TIRI = (20.5, 22.5, 24.5, 26.5, 28.5)

#: Le linee Over sul **totale dei tiri in porta**. Media 8,310, sd 2,995: stanno
#: a -0,60 / -0,27 / +0,06 / +0,40 sd, lo stesso esperimento di `validate.LINES`
#: per squadra (-0,70 / -0,28 / +0,15 / +0,57). Tassi base osservati 0,709 /
#: 0,588 / 0,456 / 0,326.
#:
#: **Non violano `tentativi.LINEE_SOT_INVARIATE`**, e la distinzione non e'
#: cavillosa: quel flag protegge le linee **per squadra** (2,5-5,5), perche'
#: cambiarle renderebbe la Fase 12 non confrontabile con la Fase 4. Il totale di
#: partita e' **un'altra grandezza** (media doppia), e su di essa TRE delle
#: quattro linee per squadra darebbero un tasso base sopra 0,90 (0,989 /
#: 0,960 / 0,910), cioe' fuori dalla regola. La quarta (5,5) resterebbe
#: dentro a 0,818: la distinzione e' quantitativa e va riportata cosi'.
LINEE_TOTALE_SOT = (6.5, 7.5, 8.5, 9.5)

#: I quattro baseline (vincolo 6), gli stessi di V1 e nello stesso ordine.
#: **Vanno composti con la STESSA procedura del modello** — i due lati sommati
#: dopo la rotazione — altrimenti il confronto misura la composizione invece del
#: lambda. E' la regola che R2 ha dovuto scrivere sui baseline dell'1X2.
BASELINE = VL.BASELINE


def linee_del(target: str = TARGET) -> tuple[float, ...]:
    """Le linee del totale per il bersaglio dato. Una definizione in un posto solo."""
    if target == TARGET:
        return LINEE_TOTALE_TIRI
    if target == TARGET_PRECISIONE:
        return LINEE_TOTALE_SOT
    raise ValueError(f"bersaglio {target!r} senza linee dichiarate: "
                     f"usare uno di {(TARGET, TARGET_PRECISIONE)}")


#: **Questo modulo non ha una cache e non scrive niente**, ed e' una scelta e non
#: una dimenticanza: la rotazione a partita e' un `set_index` su un walk-forward
#: gia' in cache e costa meno di un secondo. Una cache qui sarebbe un secondo
#: posto in cui i numeri di V1 potrebbero invecchiare in silenzio. Un test vieta
#: `to_parquet`, `to_csv` e `write_text` in questo file, come V0 fa su
#: `tentativi.py` per la stessa ragione.
SCRIVE_SU_DISCO = False


# --------------------------------------------------------------------------
# La rotazione a partita
# --------------------------------------------------------------------------
def partite(stagioni=None, league: str | None = None, target: str = TARGET,
            wf: pd.DataFrame | None = None,
            con_baseline: bool = True) -> pd.DataFrame:
    """Una riga per PARTITA: i due lambda, i due osservati, e i due totali.

    **La rotazione e' quella di `perimetro.partite()`**, con i suoi due controlli
    e la sua verifica gratuita. Non e' importata perche' li' il bersaglio sono i
    gol e il walk-forward viene da E3, mentre qui sono i tiri e viene da V1; ma
    la proprieta' verificata e' identica, e ripeterla e' l'unico modo di non
    ereditare in silenzio un accoppiamento sbagliato.
    """
    if wf is None:
        wf = VL.walkforward_tiri(stagioni=stagioni, league=league, target=target)
    elif stagioni is not None:
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
        "y_casa": c[target].astype(float),
        "y_trasferta": t[target].astype(float),
    })

    if con_baseline:
        for col in BASELINE:
            out[f"{col}_casa"] = c[col]
            out[f"{col}_trasferta"] = t[col]

    # La verifica gratuita, identica a `perimetro.py:139`: `lam_subiti` del lato
    # di casa DEVE essere il `lam` della trasferta. Il confronto e' allineato
    # sull'indice e non sull'ordine — un `to_numpy()` su due Series con indici
    # diversi le confronterebbe per posizione, che e' il modo silenzioso di far
    # passare un accoppiamento sbagliato.
    atteso = c["lam_subiti"].reindex(out.index)
    if not np.allclose(atteso.to_numpy(), out["lam_trasferta"].to_numpy(),
                       equal_nan=True):
        raise ValueError(
            "`lam_subiti` del lato di casa non coincide con `lam` della "
            "trasferta: la rotazione ha accoppiato le squadre sbagliate"
        )

    out = out.reset_index()

    # **La condizione del blocco**, la stessa di R0: servono ENTRAMBI i lati.
    # Un totale non e' meta' previsto.
    out["validabile"] = out["elig_casa"] & out["elig_trasferta"]

    # I due totali. `lam_totale` e' esatto qualunque sia la dipendenza fra i
    # lati: e' l'unica cosa di questo blocco che non abbia bisogno di una misura.
    out["lam_totale"] = out["lam_casa"] + out["lam_trasferta"]
    out["y_totale"] = out["y_casa"] + out["y_trasferta"]
    if con_baseline:
        for col in BASELINE:
            out[f"{col}_totale"] = out[f"{col}_casa"] + out[f"{col}_trasferta"]

    return out.sort_values(["stagione", "data", "matchId"]).reset_index(drop=True)


def _valutabili(d: pd.DataFrame | None = None, **kw) -> pd.DataFrame:
    d = partite(**kw) if d is None else d
    return d[d["validabile"]].copy()


def copertura(d: pd.DataFrame | None = None, **kw) -> pd.DataFrame:
    """Quante partite si perdono, e per quale dei due motivi.

    Le due cause **non si sommano**: `un_lato_solo` sono le partite in cui una
    delle due squadre e' sotto il burn-in e l'altra no — la firma del fatto che
    `eligible` e' una proprieta' della SQUADRA, non della partita, che R0 aveva
    gia' misurato sui gol.
    """
    d = partite(**kw) if d is None else d
    righe = []
    for st, g in d.groupby("stagione"):
        un_lato = int((g["elig_casa"] ^ g["elig_trasferta"]).sum())
        righe.append({
            "stagione": st,
            "partite": len(g),
            "validabili": int(g["validabile"].sum()),
            "nessun_lato": int((~g["elig_casa"] & ~g["elig_trasferta"]).sum()),
            "un_lato_solo": un_lato,
            "quota_validabile": float(g["validabile"].sum() / len(g)),
        })
    tot = pd.DataFrame(righe)
    somma = {c: tot[c].sum() for c in tot.columns
             if c not in ("stagione", "quota_validabile")}
    tot.loc[len(tot)] = {
        "stagione": "TOTALE", **somma,
        "quota_validabile": float(somma["validabili"] / somma["partite"]),
    }
    return tot


# --------------------------------------------------------------------------
# `r_tot`: si stima, non si eredita
# --------------------------------------------------------------------------
def r_totale(d: pd.DataFrame | None = None, **kw) -> float:
    """`r` della NB2 sui totali, a lambda fissato. In campione."""
    from . import dispersion as D

    v = _valutabili(d, **kw)
    return float(D.fit_r(v["y_totale"].to_numpy(dtype=float),
                         v["lam_totale"].to_numpy()))


def r_walkforward(d: pd.DataFrame | None = None, **kw) -> np.ndarray:
    """`r_tot` ricostruita **sul solo passato**, riga per riga (vincolo 1).

    `r` entra nelle probabilita' Over e negli intervalli: stimarla sull'intero
    campione renderebbe il Brier non fuori campione. E' la correzione che la
    Fase 4 ha dovuto applicare all'indietro alla Fase 2, e qui si applica subito.
    """
    from . import validate as V

    v = _valutabili(d, **kw)
    return V.walkforward_r(v["y_totale"].to_numpy(dtype=float),
                           v["lam_totale"].to_numpy(), v["data"])


def rapporto_dispersioni(d: pd.DataFrame | None = None, n_boot: int = 1000,
                         seed: int = config.SEED, **kw) -> dict:
    """`r` del totale contro `r` per lato, **sulle stesse partite**.

    E' la verifica falsificabile del blocco, ed e' modellata su
    `precisione.rapporto_dispersioni()`, che con la stessa forma ha rifiutato
    l'ereditarieta' fra `r_shots` e `r_sot`.

    Se il totale fosse la somma di due lati indipendenti con la stessa `r`, la
    dispersione relativa del totale sarebbe **piu' piccola per un fattore noto**
    e non arbitrario. Con `rho` negativo il totale e' ancora meno disperso, e
    `r_tot` esce quindi **piu' grande** di `r` per lato. Il rapporto e' un
    numero, e l'IC dice se il campione lo distingue da 1.
    """
    from . import dispersion as D

    v = _valutabili(d, **kw)
    lati = np.concatenate([v["y_casa"].to_numpy(dtype=float),
                           v["y_trasferta"].to_numpy(dtype=float)])
    lam_lati = np.concatenate([v["lam_casa"].to_numpy(),
                               v["lam_trasferta"].to_numpy()])
    y_tot = v["y_totale"].to_numpy(dtype=float)
    lam_tot = v["lam_totale"].to_numpy()

    r_lato = float(D.fit_r(lati, lam_lati))
    r_tot = float(D.fit_r(y_tot, lam_tot))

    # Il bootstrap ricampiona le **partite**, non le righe-lato: e' l'unita'
    # indipendente, e ricampionare i lati romperebbe l'accoppiamento che tutto
    # il blocco esiste per tenere insieme.
    rng = np.random.default_rng(seed)
    rap = np.empty(n_boot)
    n = len(v)
    for b in range(n_boot):
        idx = rng.integers(0, n, n)
        rl = D.fit_r(np.concatenate([v["y_casa"].to_numpy(dtype=float)[idx],
                                     v["y_trasferta"].to_numpy(dtype=float)[idx]]),
                     np.concatenate([v["lam_casa"].to_numpy()[idx],
                                     v["lam_trasferta"].to_numpy()[idx]]))
        rt = D.fit_r(y_tot[idx], lam_tot[idx])
        rap[b] = rt / rl

    basso, alto = np.percentile(rap, [2.5, 97.5])
    return {
        "r_lato": r_lato,
        "r_totale": r_tot,
        "rapporto": r_tot / r_lato,
        "ic95": (float(basso), float(alto)),
        "eredita": bool(basso <= 1.0 <= alto),
        "n_partite": int(n),
        "n_boot": int(n_boot),
    }


def correlazione_lati(d: pd.DataFrame | None = None, **kw) -> pd.DataFrame:
    """La correlazione fra i due lati, per stagione, sul perimetro di questo blocco.

    **Non sostituisce `tentativi.correlazione_lati()`**, che gira sull'universo
    intero: qui il perimetro e' quello validabile, ed e' il numero che descrive
    le partite su cui il blocco misura. Riportare quello di V0 al posto di questo
    sarebbe citare una misura fatta su un'altra popolazione.
    """
    v = _valutabili(d, **kw)
    righe = []
    for st, g in v.groupby("stagione"):
        a = g["y_casa"].to_numpy(dtype=float)
        b = g["y_trasferta"].to_numpy(dtype=float)
        rho = float(np.corrcoef(a, b)[0, 1])
        sd_oss = float(g["y_totale"].std())
        sd_indip = float(np.sqrt(a.var(ddof=1) + b.var(ddof=1)))
        righe.append({
            "stagione": st, "partite": len(g), "corr": rho,
            "sd_totale_osservata": sd_oss,
            "sd_se_indipendenti": sd_indip,
            "rapporto_sd": sd_oss / sd_indip,
        })
    return pd.DataFrame(righe)


# --------------------------------------------------------------------------
# La distribuzione del totale, e l'alternativa che non batte
# --------------------------------------------------------------------------
def p_over_totale(lam_totale, linee=None, r=None,
                  target: str = TARGET) -> pd.DataFrame:
    """`P(Over)` e quota di pareggio sul totale, per le linee dichiarate.

    `quota_pareggio` si **importa** da `soglie_2627`, mai riscritta come
    `1.0/p`: una definizione in un posto solo. La Fase 14 ha gia' dovuto
    correggere esattamente questa duplicazione in `previsione._p_over`.
    """
    from . import dispersion as D, soglie_2627 as S

    linee = linee_del(target) if linee is None else linee
    lam = np.atleast_1d(np.asarray(lam_totale, dtype=float))
    out = pd.DataFrame({
        "linea": list(linee),
        "p_over": [float(np.mean(D.p_over(lam, ln, r))) for ln in linee],
    })
    out["quota_pareggio"] = S.quota_pareggio(out["p_over"].to_numpy())
    return out


def confronto_indipendenza(d: pd.DataFrame | None = None,
                           target: str = TARGET, **kw) -> pd.DataFrame:
    """La NB2 diretta contro la convoluzione di due NB2 **indipendenti**.

    **Questa funzione esiste per non trasformare una scelta in un'asserzione.**
    L'alternativa scartata va calcolata e messa accanto: e' la stessa disciplina
    con cui V2 tiene in tabella la marginale composta che non ha adottato, e con
    cui R2 compone ogni baseline con la stessa congiunta del modello.

    Entrambe le colonne usano `r` **walk-forward** — quella per lato per la
    convoluzione, quella del totale per la diretta — altrimenti si
    confronterebbe un modello fuori campione con uno in campione.

    L'attesa teorica e' che l'indipendenza **ingrassi entrambe le code**, perche'
    ignora una covarianza negativa. Il segno e' previsto prima di guardare.
    """
    from . import validate as V
    from scipy import stats

    v = _valutabili(d, target=target, **kw) if d is None else _valutabili(d)
    linee_t = linee_del(target)

    y = v["y_totale"].to_numpy(dtype=float)
    lam_tot = v["lam_totale"].to_numpy()
    r_tot = V.walkforward_r(y, lam_tot, v["data"])

    # `r` per lato, walk-forward sulle righe-lato impilate: e' la stessa
    # procedura di V1, applicata alle due colonne che la rotazione ha separato.
    lati = np.concatenate([v["y_casa"].to_numpy(dtype=float),
                           v["y_trasferta"].to_numpy(dtype=float)])
    lam_lati = np.concatenate([v["lam_casa"].to_numpy(),
                               v["lam_trasferta"].to_numpy()])
    date_lati = pd.concat([v["data"], v["data"]], ignore_index=True)
    r_lati = V.walkforward_r(lati, lam_lati, date_lati)
    r_casa, r_trasf = r_lati[:len(v)], r_lati[len(v):]

    # La griglia del troncamento e' esplicita, come in `precisione.pmf_composta`:
    # media del totale piu' dodici deviazioni standard NB2, mai un numero magico.
    massimo = float(lam_tot.max())
    r_min = float(np.min(r_lati))          # la r piu' piccola = la coda piu' grassa
    n_max = int(massimo + 12.0 * np.sqrt(massimo + massimo ** 2 / r_min) + 20)
    k = np.arange(n_max + 1)

    p_ind = np.zeros((len(v), len(linee_t)))
    for i, (a, b, ra, rb) in enumerate(zip(v["lam_casa"], v["lam_trasferta"],
                                           r_casa, r_trasf)):
        pa = stats.nbinom.pmf(k, ra, ra / (ra + a))
        pb = stats.nbinom.pmf(k, rb, rb / (rb + b))
        conv = np.convolve(pa, pb)
        coda = np.concatenate([conv[::-1].cumsum()[::-1], [0.0]])
        for j, ln in enumerate(linee_t):
            p_ind[i, j] = coda[int(np.floor(ln)) + 1]

    from . import dispersion as D

    righe = []
    for j, ln in enumerate(linee_t):
        oss = float((y > ln).mean())
        dir_ = float(np.mean(D.p_over(lam_tot, ln, r_tot)))
        ind = float(p_ind[:, j].mean())
        righe.append({
            "linea": ln,
            "tasso_base": oss,
            "p_nb2_diretta": dir_,
            "p_indipendenza": ind,
            "errore_diretta": dir_ - oss,
            "errore_indipendenza": ind - oss,
            "brier_diretta": V.brier((y > ln).astype(float),
                                     D.p_over(lam_tot, ln, r_tot)),
            "brier_indipendenza": V.brier((y > ln).astype(float), p_ind[:, j]),
        })
    out = pd.DataFrame(righe)
    out["diretta_piu_vicina"] = (out["errore_diretta"].abs()
                                 < out["errore_indipendenza"].abs())
    return out


# --------------------------------------------------------------------------
# La validazione, rifatta da capo (non si eredita da V1)
# --------------------------------------------------------------------------
def valutazione(d: pd.DataFrame | None = None, linea: float | None = None,
                target: str = TARGET, **kw) -> pd.DataFrame:
    """Il modello contro i quattro baseline, sulle stesse identiche partite.

    **Non eredita niente da V1.** Che il modello sia calibrato per squadra non
    dice niente sul totale: media doppia, dispersione diversa, e una `r` quattro
    volte piu' grande. `r` e tasso base sono ricostruiti sul solo passato.

    I baseline sono composti **con la stessa procedura del modello** (i due lati
    sommati dopo la rotazione), altrimenti si misurerebbe la composizione.
    """
    from . import validate as V

    v = _valutabili(d, target=target, **kw) if d is None else _valutabili(d)
    linea = linee_del(target)[2] if linea is None else linea

    y = v["y_totale"].to_numpy(dtype=float)
    lam = v["lam_totale"].to_numpy()
    r = V.walkforward_r(y, lam, v["data"])
    base = V.walkforward_base_rate(y, v["data"], line=linea)

    righe = [{"modello": V.MODEL_NAME + " (somma dei due lati)",
              **V.metrics(y, lam, r=r, line=linea, base_rate=base)}]
    for nome in BASELINE:
        righe.append({"modello": nome,
                      **V.metrics(y, v[f"{nome}_totale"].to_numpy(), r=r,
                                  line=linea, base_rate=base)})
    return pd.DataFrame(righe)


def confronto_appaiato(d: pd.DataFrame | None = None, target: str = TARGET,
                       **kw) -> pd.DataFrame:
    """Il margine sul baseline con il suo `t`, per riga **e** per cluster.

    **Qui il cluster e' degenere e va detto.** In V1 la riga era la
    squadra-partita e il cluster la partita, quindi raggruppare cambiava
    qualcosa; dopo la rotazione una riga *e'* una partita, e i due `t` coincidono
    **per costruzione**. Si riportano lo stesso, in coppia, perche' chi arriva da
    V1 si aspetta due numeri e deve vedere che sono uguali invece di dedurlo.
    """
    from . import validate as V

    v = _valutabili(d, target=target, **kw) if d is None else _valutabili(d)
    y = v["y_totale"].to_numpy(dtype=float)
    e_mod = np.abs(y - v["lam_totale"].to_numpy())

    righe = []
    for nome in BASELINE:
        e_b = np.abs(y - v[f"{nome}_totale"].to_numpy())
        # `paired_t` ritorna (somma, t), NON (t, p): scambiarli e' silenzioso.
        _s, t_riga = V.paired_t(e_b, e_mod)
        _s, t_clu = V.paired_t(e_b, e_mod, cluster=v["matchId"].to_numpy())
        righe.append({"baseline": nome,
                      "mae_baseline": float(e_b.mean()),
                      "mae_modello": float(e_mod.mean()),
                      "delta_mae": float((e_b - e_mod).mean()),
                      "t_per_riga": t_riga,
                      "t_per_cluster": t_clu,
                      "cluster_degenere": bool(np.isclose(t_riga, t_clu))})
    return pd.DataFrame(righe)


def per_stagione(d: pd.DataFrame | None = None, target: str = TARGET,
                 **kw) -> pd.DataFrame:
    """Cinque quasi-repliche invece di un numero solo.

    Il MAE assoluto non e' confrontabile fra stagioni: il livello dei totali si
    muove come quello per squadra. Il **MAE relativo** e' la colonna da leggere
    in orizzontale, e i cinque segni dicono una cosa che il `t` pooled non ha.
    """
    from . import validate as V

    v = _valutabili(d, target=target, **kw) if d is None else _valutabili(d)
    righe = []
    for st, g in v.groupby("stagione"):
        y = g["y_totale"].to_numpy(dtype=float)
        lam = g["lam_totale"].to_numpy()
        e_mod = np.abs(y - lam)
        e_b = np.abs(y - g[f"{V.BEST_BASELINE}_totale"].to_numpy())
        _s, t = V.paired_t(e_b, e_mod)
        righe.append({
            "stagione": st, "n": len(g),
            "media_osservata": float(y.mean()),
            "mae": float(e_mod.mean()),
            "mae_relativo": float(e_mod.mean() / y.mean()),
            "bias": float((lam - y).mean()),
            "corr": float(np.corrcoef(y, lam)[0, 1]),
            "delta_su_baseline": float((e_b - e_mod).mean()),
            "t": t,
            "vince": bool(e_mod.mean() < e_b.mean()),
        })
    return pd.DataFrame(righe)


def brier_per_linea(d: pd.DataFrame | None = None, target: str = TARGET,
                    **kw) -> pd.DataFrame:
    """Brier del modello e del baseline migliore su tutte le linee dichiarate.

    Una linea sola sarebbe un risultato scelto: la Fase 4 lo ha stabilito
    misurando su quattro soglie invece che su una. `dentro_regola` applica
    meccanicamente `tentativi.BASE_RATE_AMMESSO`, cosi' che se una linea uscisse
    dalla regola si vedrebbe invece di restare implicito.
    """
    from . import dispersion as D, validate as V

    v = _valutabili(d, target=target, **kw) if d is None else _valutabili(d)
    y = v["y_totale"].to_numpy(dtype=float)
    lam = v["lam_totale"].to_numpy()
    lam_b = v[f"{V.BEST_BASELINE}_totale"].to_numpy()
    r = V.walkforward_r(y, lam, v["data"])

    righe = []
    for ln in linee_del(target):
        yb = (y > ln).astype(float)
        base = V.walkforward_base_rate(y, v["data"], line=ln)
        righe.append({
            "linea": ln,
            "tasso_base": float(yb.mean()),
            "dentro_regola": bool(T.BASE_RATE_AMMESSO[0] <= yb.mean()
                                  <= T.BASE_RATE_AMMESSO[1]),
            "brier_modello": V.brier(yb, D.p_over(lam, ln, r)),
            "brier_baseline": V.brier(yb, D.p_over(lam_b, ln, r)),
            "brier_tasso_base": V.brier(yb, base),
        })
    out = pd.DataFrame(righe)
    out["vince_su_baseline"] = out["brier_modello"] < out["brier_baseline"]
    out["vince_su_tasso_base"] = out["brier_modello"] < out["brier_tasso_base"]
    return out


def forma_predittiva(d: pd.DataFrame | None = None, target: str = TARGET,
                     **kw) -> dict:
    """PIT randomizzato e copertura: la forma, non solo la media.

    E' il controllo che la pendenza di calibrazione **non** fa, ed e' qui che si
    vedrebbe se `r_tot` fosse sbagliata: una `r` troppo piccola darebbe una
    predittiva troppo larga e un PIT a U rovesciata, che la pendenza non vede.
    """
    from . import validate as V

    v = _valutabili(d, target=target, **kw) if d is None else _valutabili(d)
    y = v["y_totale"].to_numpy(dtype=float)
    lam = v["lam_totale"].to_numpy()
    r = V.walkforward_r(y, lam, v["data"])
    return {"pit": V.pit_uniformity(V.pit(y, lam, r=r)),
            "copertura": V.interval_coverage(y, lam, r=r),
            "r_mediana": float(np.median(r))}


def realizzazioni(d: pd.DataFrame | None = None, **kw) -> pd.DataFrame:
    """Quante realizzazioni ha davvero ogni affermazione di questo blocco.

    Sta nel codice e non solo nel report per la stessa ragione per cui ci sta
    `perimetro.realizzazioni()`: e' un conteggio, non un'opinione. E dice la cosa
    che il confronto con V1 renderebbe altrimenti confusa: le righe si dimezzano
    passando alla partita, e non e' una perdita di dati ma un cambio di unita'.
    """
    d = partite(**kw) if d is None else d
    val = d[d["validabile"]]
    return pd.DataFrame([
        {"affermazione": "MAE e calibrazione sul totale", "unita": "partita",
         "n": int(len(val)), "blocco": "T1"},
        {"affermazione": "Over/Under sul totale, per linea", "unita": "partita",
         "n": int(len(val)), "blocco": "T1"},
        {"affermazione": "lo stesso, per squadra-partita",
         "unita": "squadra-partita", "n": int(2 * len(val)), "blocco": "V1"},
        {"affermazione": "il segno del margine per stagione", "unita": "stagione",
         "n": int(val["stagione"].nunique()), "blocco": "T1"},
    ])


def limiti() -> list[str]:
    """I limiti che vanno accanto ai numeri, non in fondo (vincolo 5)."""
    return [
        "il totale e' la somma di due lambda correlati NEGATIVAMENTE (-0,35): la "
        "media e' esatta, la dispersione no, e per questo `r_tot` si stima sui "
        "totali invece di ereditarla da `r` per lato",
        "**il lambda del totale e' SOTTO-CALIBRATO**: pendenza 0,63 sui tiri e "
        "0,48 sui tiri in porta, contro 1,008 per lato. Il modello crede i due "
        "lati piu' anti-correlati di quanto siano, e sommando si cancella il "
        "segnale comune. La correzione walk-forward passa il criterio sui tiri "
        "(0,81) e NON sui tiri in porta (0,64)",
        "`r_tot` e' assunta costante fra squadre e stagioni, come `r` in V1",
        "la riga e' la PARTITA: 1.638 realizzazioni e non 3.278, e il `t` per "
        "cluster e' degenere perche' coincide con quello per riga",
        "le linee del totale sono NUOVE e non confrontabili con quelle per "
        "squadra: sono un'altra grandezza, con media doppia",
        "nessuna quota e nessuna valutazione di scommessa (vincolo 3): nel "
        "repository non ci sono prezzi di mercato reali",
    ]


# --------------------------------------------------------------------------
# La sotto-calibrazione del totale, e la sua correzione
# --------------------------------------------------------------------------
#: **Il criterio di adozione, scritto PRIMA di guardare i numeri della
#: ricalibrazione.** E' la disciplina di R2-bis, e la ragione e' la stessa: una
#: correzione a un parametro solo trova quasi sempre un miglioramento in
#: campione, quindi la decisione va vincolata prima.
#:
#: La correzione si adotta se e solo se, **fuori campione** (walk-forward per
#: stagione, la stagione piu' vecchia resta non ricalibrata come la 2021-2022 di
#: R2-bis):
#:
#: 1. la pendenza di calibrazione del totale ricalibrato dista da 1,0 meno di
#:    **due errori standard** (oggi il grezzo dista 4,78);
#: 2. il **MAE non peggiora** oltre l'errore standard della differenza appaiata;
#: 3. il segno del miglioramento della pendenza regge in **almeno 4 stagioni su
#:    5**, perche' un pooled puo' nascondere due regimi opposti.
CRITERIO_ADOZIONE = (
    "si adotta se, walk-forward: (1) |pendenza - 1| < 2 errori standard, "
    "(2) il MAE non peggiora oltre l'errore standard della differenza "
    "appaiata, (3) il segno regge in almeno 4 stagioni su 5."
)

#: Quante stagioni su cinque devono concordare (criterio 3).
STAGIONI_CONCORDI = 4


def anticorrelazione(d: pd.DataFrame | None = None, target: str = TARGET,
                     **kw) -> pd.DataFrame:
    """Quanto il modello CREDE anti-correlati i due lati, contro quanto lo sono.

    **E' la diagnosi della sotto-calibrazione del totale, e non era prevista.**
    Per lato il modello e' calibrato a 1,008 (z = +0,33, cioe' il risultato di
    V1 riprodotto); sul totale scende a 0,70 con z = -4,78. Le due cose non si
    contraddicono: sommando, la parte di segnale che i due lati hanno in comune
    si **cancella**, e sopravvive proporzionalmente piu' rumore.

    Il numero che lo dice e' questo: `corr(lam_casa, lam_trasferta)` contro
    `corr(y_casa, y_trasferta)`. Se il modello anti-correla piu' del vero, la
    somma dei suoi lambda e' troppo compressa verso la media e le sue deviazioni
    residue sono troppo grandi in proporzione.
    """
    v = _valutabili(d, target=target, **kw) if d is None else _valutabili(d)
    righe = []
    for st, g in v.groupby("stagione"):
        righe.append({
            "stagione": st, "partite": len(g),
            "corr_lambda": float(np.corrcoef(g["lam_casa"], g["lam_trasferta"])[0, 1]),
            "corr_osservata": float(np.corrcoef(g["y_casa"], g["y_trasferta"])[0, 1]),
            "sd_lam_totale": float(g["lam_totale"].std()),
            "sd_y_totale": float(g["y_totale"].std()),
        })
    out = pd.DataFrame(righe)
    out["il_modello_anticorrela_di_piu"] = out["corr_lambda"] < out["corr_osservata"]
    return out


def _fit_log_poisson(y: np.ndarray, lam: np.ndarray) -> tuple[float, float]:
    """`log(mu) = a + b*log(lambda)` per Newton-Raphson. Ritorna `(a, b)`.

    **La `b` deve coincidere con `validate.calibration_slope(y, lam)[0]`**, e un
    test lo pretende: la pendenza ha una definizione sola in questo repository, e
    questa funzione aggiunge soltanto l'intercetta, che li' non viene restituita
    perche' non serviva a nessuno prima di questo blocco.
    """
    y = np.asarray(y, dtype=float)
    z = np.log(np.clip(np.asarray(lam, dtype=float), 1e-9, None))
    if np.std(z) < 1e-12:
        return float("nan"), float("nan")
    Z = np.column_stack([np.ones(len(y)), z])
    b = np.array([0.0, 1.0])
    for _ in range(100):
        mu = np.exp(np.clip(Z @ b, -20, 20))
        step = np.linalg.solve(Z.T @ (Z * mu[:, None]), Z.T @ (y - mu))
        b = b + step
        if np.max(np.abs(step)) < 1e-10:
            break
    return float(b[0]), float(b[1])


def ricalibrazione(d: pd.DataFrame | None = None, target: str = TARGET,
                   **kw) -> pd.DataFrame:
    """La correzione della sotto-calibrazione del totale, **walk-forward**.

    Il mappatore della stagione `s` si stima sulle stagioni **precedenti** e su
    nient'altro (vincolo 1). La stagione piu' vecchia non ha un passato e
    **resta non ricalibrata**, marcata invece che riempita: e' esattamente il
    trattamento che R2-bis ha riservato alla 2021-2022.

    La forma e' `log(lam_ric) = a + k*log(lam_tot)`, cioe' l'inverso letterale
    della pendenza di calibrazione — non una manopola scelta perche' funziona.
    """
    v = _valutabili(d, target=target, **kw) if d is None else _valutabili(d)
    v = v.sort_values(["stagione", "data"]).reset_index(drop=True)

    stagioni = sorted(v["stagione"].unique())
    v["lam_ricalibrato"] = np.nan
    v["ricalibrata"] = False
    v["k_applicato"] = np.nan

    for i, st in enumerate(stagioni):
        if i == 0:
            continue                      # nessun passato: resta non ricalibrata
        passato = v[v["stagione"].isin(stagioni[:i])]
        a, k = _fit_log_poisson(passato["y_totale"].to_numpy(dtype=float),
                                passato["lam_totale"].to_numpy())
        m = v["stagione"] == st
        v.loc[m, "lam_ricalibrato"] = np.exp(
            a + k * np.log(np.clip(v.loc[m, "lam_totale"].to_numpy(), 1e-9, None)))
        v.loc[m, "ricalibrata"] = True
        v.loc[m, "k_applicato"] = k
    return v


def verdetto(d: pd.DataFrame | None = None, target: str = TARGET,
             **kw) -> dict:
    """Applica `CRITERIO_ADOZIONE` **meccanicamente**, senza guardare i numeri.

    Il criterio e' scritto sopra, prima della misura. Questa funzione non lo
    interpreta: lo esegue, e ritorna anche le tre condizioni separate perche' un
    verdetto senza le sue componenti non e' verificabile.
    """
    from . import validate as V

    r = ricalibrazione(d, target=target, **kw)
    m = r["ricalibrata"]
    if not m.any():
        raise ValueError("nessuna stagione ricalibrata: serve piu' di una stagione")

    y = r.loc[m, "y_totale"].to_numpy(dtype=float)
    grezzo = r.loc[m, "lam_totale"].to_numpy()
    ric = r.loc[m, "lam_ricalibrato"].to_numpy()

    b0, se0 = V.calibration_slope(y, grezzo)
    b1, se1 = V.calibration_slope(y, ric)

    e0 = np.abs(y - grezzo)
    e1 = np.abs(y - ric)
    _s, t_mae = V.paired_t(e1, e0)        # > 0 = il ricalibrato ha errore MAGGIORE

    concordi = 0
    for st, g in r[m].groupby("stagione"):
        yy = g["y_totale"].to_numpy(dtype=float)
        pb0, _ = V.calibration_slope(yy, g["lam_totale"].to_numpy())
        pb1, _ = V.calibration_slope(yy, g["lam_ricalibrato"].to_numpy())
        concordi += int(abs(pb1 - 1.0) < abs(pb0 - 1.0))

    n_stagioni = int(r.loc[m, "stagione"].nunique())
    c1 = bool(abs(b1 - 1.0) < 2.0 * se1)
    c2 = bool(t_mae < 1.0)                # il MAE non peggiora oltre un e.s.
    c3 = bool(concordi >= min(STAGIONI_CONCORDI, n_stagioni))

    return {
        "n": int(m.sum()),
        "stagioni_ricalibrate": n_stagioni,
        "pendenza_grezza": b0, "se_grezza": se0, "z_grezza": (b0 - 1.0) / se0,
        "pendenza_ricalibrata": b1, "se_ricalibrata": se1,
        "z_ricalibrata": (b1 - 1.0) / se1,
        "mae_grezzo": float(e0.mean()), "mae_ricalibrato": float(e1.mean()),
        "t_mae": t_mae,
        "stagioni_migliorate": concordi,
        "criterio_1_pendenza": c1,
        "criterio_2_mae": c2,
        "criterio_3_segno": c3,
        "adottata": bool(c1 and c2 and c3),
        "criterio": CRITERIO_ADOZIONE,
    }


def per_campionato(n_boot: int = 200, targets=(TARGET, TARGET_PRECISIONE)
                   ) -> pd.DataFrame:
    """Lo stesso blocco sui cinque campionati, **un fit per campionato**.

    E' la domanda che la Fase 13 ha posto ai gol - **trasferisce?** - applicata a
    questo blocco, e i campionati **non si poolano** (regola di E1, riscritta da
    R0 proprio su G2): ogni riga viene dal walk-forward di quel campionato.

    Serve a due cose. La prima e' scientifica: un risultato che valesse solo in
    Serie A sarebbe un'idiosincrasia italiana, non una proprieta' del gioco. La
    seconda e' operativa: **la pagina ha bisogno di una `r_tot` per campionato**,
    perche' `r` non si eredita fra campionati piu' di quanto si erediti fra
    bersagli.
    """
    from . import dispersion as D, validate as V

    righe = []
    for league in sorted(config.LEAGUE_CODES):
        for target in targets:
            d = partite(league=league, target=target)
            v = d[d["validabile"]]
            if not len(v):
                continue
            y = v["y_totale"].to_numpy(dtype=float)
            lam = v["lam_totale"].to_numpy()
            lati = np.concatenate([v["y_casa"].to_numpy(dtype=float),
                                   v["y_trasferta"].to_numpy(dtype=float)])
            lam_lati = np.concatenate([v["lam_casa"].to_numpy(),
                                       v["lam_trasferta"].to_numpy()])
            b, se = V.calibration_slope(y, lam)
            righe.append({
                "campionato": league,
                "bersaglio": "tiri" if target == TARGET else "tiri in porta",
                "partite": len(v),
                "media_totale": float(y.mean()),
                "corr_lati": float(np.corrcoef(v["y_casa"], v["y_trasferta"])[0, 1]),
                "r_lato": float(D.fit_r(lati, lam_lati)),
                "r_totale": float(D.fit_r(y, lam)),
                "pendenza_totale": b,
                "z_vs_1": (b - 1.0) / se,
            })
    out = pd.DataFrame(righe)
    out["rapporto_r"] = out["r_totale"] / out["r_lato"]
    return out
