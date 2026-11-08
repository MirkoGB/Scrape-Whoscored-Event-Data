# -*- coding: utf-8 -*-
"""Fase 12 / Blocco V0 — il perimetro del bersaglio, e l'identita' che decide lo strato 2.

**Non stima nessun modello predittivo.** Non c'e' un walk-forward, un
iperparametro, un bersaglio previsto. Questo modulo *conta* e *misura*, ed e'
l'analogo di R0 per la Fase 12: il suo esito decide la **forma** di V1 e V2
invece di essere un loro risultato.

IL BERSAGLIO
------------
La Fase 12 modella i **tentativi** (`team_match.shots`, che e' `isShot AND NOT
isOwnGoal` — vedi `sot/shots.py`, che resta l'unica definizione), non i tiri in
porta. La colonna esiste dalla Fase 1 su tutte e cinque le stagioni: **questa
fase non acquisisce niente e non ricalcola nessun derivato.**

Il disegno e' gerarchico, in due strati:

    strato 1 (volume)     shots_ij ~ NB2(lambda_ij, r)
    strato 2 (precisione) sot_ij | shots_ij ~ Binomiale(shots_ij, p_ij)

e se `p` e' costante dato `(i, j)` il **thinning binomiale di una NB2 e' una
NB2** con lo stesso `r` e media `lambda*p`: la marginale di `sot` ha forma
chiusa. `thinning_simulato()` lo verifica dove la risposta e' nota, perche' e'
la premessa su cui poggia tutta la gerarchia e non va assunta.

LA DOMANDA CHE DECIDE LO STRATO 2
---------------------------------
**`p_ij` varia davvero fra squadre, o e' un numero solo piu' rumore
binomiale?** Se non varia, lo strato 2 collassa a `sot = shots * p_lega`, la
composizione diventa esatta e il modello ha meno parti. Non e' un fallimento:
e' un risultato piu' parsimonioso, e va dichiarato come esito possibile
**prima** di sapere quale sia.

**L'evidenza gia' in casa NON risponde a questa domanda, ed e' l'errore che
questo modulo esiste per non commettere.** `recording_stability` ha misurato che
la quota in porta e' stabile *fra stagioni e fra mesi* (nessuno z sopra 2,3,
F = 1,75 sul gradino di stagione) e ha riportato `phi = 1,101`. Ma quel `phi` e'
la sovradispersione delle unita' **squadra-partita** attorno alla cella
`stagione|mese`: contiene rumore di partita, effetto squadra ed effetto
avversario **tutti insieme**, e non li separa. «La quota di campionato non si
muove fra stagioni» e «la quota non varia fra squadre» sono **due nulli
diversi**, e il secondo non e' mai stato testato.
`livello_sbagliato()` mette a verbale la differenza, cosi' che citare 1,101
come risposta risulti visibilmente un errore invece di sembrare una scorciatoia.

PERCHE' A LIVELLO SQUADRA-STAGIONE E NON SQUADRA-PARTITA
--------------------------------------------------------
Con ~12,6 tentativi per squadra-partita la deviazione standard binomiale della
quota vale ~13,4 punti: una differenza fra squadre di 2-3 punti ci sparisce
dentro, e `phi = 1,101` **e' quel rumore**. Aggregando a squadra-stagione
(~470 tentativi) il rumore binomiale scende a ~2,2 punti e la componente di
squadra, se c'e', emerge. E' l'unico livello in cui il rumore di partita si
cancella invece di gonfiare la statistica.

IL NULLO VA GENERATO, NON PRESO DAL CHI-QUADRO
----------------------------------------------
Il `chi2` teorico assume binomialita' **esatta** anche dentro la
squadra-stagione. Ma la sovradispersione di partita esiste e vale `phi ~ 1,10`:
un test che la ignorasse la scambierebbe per eterogeneita' di squadra ed e'
**garantito di rifiutare**. Il nullo giusto e' quindi «`p` non varia fra
squadre, ma varia da partita a partita quanto gia' sappiamo», realizzato come
beta-binomiale a livello squadra-partita con la correlazione intraclasse
misurata sui dati. E' la stessa disciplina con cui `recording_stability`
simula la distribuzione del massimo invece di leggerla da una tabella.

`taratura_test()` chiude il cerchio: su mondi generati con `tau` noto, la
frequenza di rifiuto deve valere ~5% a `tau = 0` (che e' la **dimensione** del
test, non zero) e ~80% al MDE dichiarato. Se la riga `tau = 0` esce al 15%, il
test e' rotto e non c'e' niente da leggere sui dati veri.

LE SOGLIE SONO DICHIARATE PRIMA
-------------------------------
`LINEE_TIRI` e `CRITERIO_STRATO2` sono costanti letterali, scritte prima di
guardare gli esiti, e un test vieta `argmax`/`idxmax`/`quantile` in questo
modulo. **Il divieto di `quantile` e' una regola NUOVA e piu' severa** di
quella di S1 (`tests/test_fase11_s1.py:407` vieta solo i primi due, e
`np.quantile` e' usato legittimamente altrove): qui vale perche' nessun
quantile empirico deve poter entrare in una soglia.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import optimize, stats

from . import config, multistagione as MS, predictor_power as PP

# --------------------------------------------------------------------------
# Il bersaglio e le soglie — dichiarati PRIMA
# --------------------------------------------------------------------------

#: Lo strato 1. E' `team_match.shots`, cioe' i tentativi totali.
TARGET = "shots"

#: Il numeratore dello strato 2. Il denominatore e' `TARGET`.
TARGET_PRECISIONE = "sot"

#: La regola con cui le linee sono state scelte, scritta prima dei numeri
#: perche' sia falsificabile che sia stata seguita.
REGOLA_LINEE = (
    "multipli interi + 0,5 (convenzione di mercato), passo 2, centrati sul "
    "multiplo di 2 piu' vicino alla media pubblicata di tentativi per "
    "squadra-partita delle cinque stagioni (12,58); estesi finche' il tasso "
    "base resta dentro [0,10 - 0,90]."
)

#: Le linee Over sui **tentativi**. Stanno a -0,78 / -0,40 / -0,02 / +0,37 /
#: +0,75 deviazioni standard dalla media (12,58, sd 5,21): e' lo **stesso**
#: esperimento di `validate.LINES` sui tiri in porta (-0,73 / -0,25 / +0,22 /
#: +0,70), su un bersaglio riscalato. E' la sola forma in cui i numeri delle due
#: fasi si possano mettere accanto. Un passo di 1 tiro darebbe 0,19 sd fra una
#: linea e l'altra, cioe' cinque volte lo stesso test.
LINEE_TIRI = (8.5, 10.5, 12.5, 14.5, 16.5)

#: L'analoga di `config.OVER_LINE = 4.5`, che sui tentativi non ha senso.
LINEA_PRINCIPALE = 12.5

#: **Le linee dei tiri in porta NON si toccano.** Lo strato 2 e la marginale
#: composta si valutano su `validate.LINES` inalterata (2,5-5,5). Inventarne di
#: nuove renderebbe la Fase 12 non confrontabile con la Fase 4, che e' il
#: difetto contro cui esiste il vincolo 7.
LINEE_SOT_INVARIATE = True

#: Il tasso base ammesso per una linea. Fuori da qui il Brier misura soprattutto
#: `r` invece del lambda, ed e' il difetto che S1 ha dovuto dichiarare sulle sue
#: due linee estreme. Qui nessuna linea si pubblica fuori dall'intervallo.
BASE_RATE_AMMESSO = (0.10, 0.90)

#: Potenza e dimensione del test di eterogeneita', dichiarate prima.
POTENZA_OBIETTIVO = 0.80
ALPHA_TEST = 0.05

#: I tre lati su cui l'eterogeneita' della precisione viene cercata. Sono tre
#: ipotesi, non una: la molteplicita' si corregge con `PP.soglia_sidak(k=3)`,
#: riusata invece di riscritta.
LATI = ("attacco", "difesa", "campo")

CRITERIO_STRATO2 = (
    "lo strato 2 si STIMA solo se (a) almeno uno dei tre lati rifiuta alla "
    "soglia di Sidak per k=3 con il nullo SIMULATO, e (b) il tau stimato "
    "supera il proprio MDE all'80%. Altrimenti p = p_lega stimata sul solo "
    "passato, lo strato 2 e' UN NUMERO, e la marginale di sot e' "
    "NB2(lambda*p_lega, r) in forma chiusa."
)

#: I lati che lo strato 2 stima davvero. **NON e' l'uscita di
#: `verdetto_strato2()`**, ed e' voluto che le due cose restino separate.
#:
#: `[DECISO 2026-08-13]` **dall'utente: la difesa entra.** Il criterio qui sopra,
#: applicato meccanicamente, dice *solo attacco*: sul lato difensivo il test di
#: dispersione rifiuta (z = +2,51) ma `tau` resta **sotto il proprio MDE tarato**
#: (1,39 contro 1,59 punti), e la regola scritta prima chiede entrambe le cose.
#:
#: **Il criterio non e' stato riscritto per farlo tornare** — sarebbe l'errore che
#: questo progetto rifiuta da undici fasi — e `verdetto_strato2()` continua a
#: rispondere `['attacco']`. La difesa entra per decisione, e la decisione ha un
#: argomento: la **seconda strada, indipendente, la rifiuta nettamente**
#: (GLM in quasi-verosimiglianza, F = 2,83 su 26 gdl, p = 2,3e-06). Le due strade
#: non si contraddicono — il GLM stima coefficienti invece che dispersione, quindi
#: ha piu' potenza — e il test di dispersione dichiara di *non poter risolvere* un
#: effetto che c'e' ed e' piccolo.
#:
#: **Il costo resta dichiarato e va misurato, non assunto**: un effetto sotto il
#: MDE del test primario puo' valere zero fuori campione. V2 stima entrambe le
#: varianti — `("attacco",)` e `("attacco", "difesa")` — e ne riporta il confronto
#: appaiato. Il campo resta fuori: non rifiuta in **nessuna** delle due strade.
LATI_STRATO2 = ("attacco", "difesa")


# --------------------------------------------------------------------------
# L'universo
# --------------------------------------------------------------------------
def universo(stagioni=None, league: str | None = None) -> pd.DataFrame:
    """Le righe squadra-partita delle cinque stagioni, lette e basta.

    Non ricalcola niente: `team_match.parquet` esiste per tutte e cinque dalla
    Fase 1 e dal blocco E0. Aggiunge solo `quota_in_porta`, che e' `NaN` — e non
    zero — dove i tentativi sono zero: **una quota senza denominatore non
    esiste**, e metterci uno zero la farebbe entrare nelle medie come se fosse
    una squadra che non ha mai centrato la porta.

    `league=None` significa `config.LEAGUE`, cioe' esattamente cio' che questa
    funzione faceva prima della Fase 14 — quando non poteva fare altro.
    """
    u = MS.carica("team_match", stagioni=config.SEASONS_STORICHE
                  if stagioni is None else tuple(stagioni), league=league)
    u = u.sort_values(["stagione", "date", "matchId", "team"]).reset_index(drop=True)
    n = u[TARGET].to_numpy(dtype=float)
    k = u[TARGET_PRECISIONE].to_numpy(dtype=float)
    u["quota_in_porta"] = np.where(n > 0, k / np.where(n > 0, n, 1.0), np.nan)
    return u


def verifica_conteggi(u: pd.DataFrame | None = None) -> pd.DataFrame:
    """Verifiche falsificabili sul bersaglio. Non passano da nessun modello.

    `sot <= shots` non e' pedanteria: se cadesse, la binomiale dello strato 2
    sarebbe **impossibile** e non malamente specificata. Ed e' il genere di
    controllo che una fase intera puo' poggiare su un derivato senza mai fare.
    """
    u = universo() if u is None else u
    n = u[TARGET].to_numpy(dtype=float)
    k = u[TARGET_PRECISIONE].to_numpy(dtype=float)

    righe = [
        ("righe totali", len(u), None),
        ("sot > shots (impossibile)", int((k > n).sum()), 0),
        ("shots negativi", int((n < 0).sum()), 0),
        ("shots nulli (NaN)", int(np.isnan(n).sum()), 0),
        ("righe a zero tentativi", int((n == 0).sum()), None),
        ("quota definita dove shots > 0",
         int(u.loc[u[TARGET] > 0, "quota_in_porta"].notna().sum()),
         int((n > 0).sum())),
        ("quota NaN dove shots == 0",
         int(u.loc[u[TARGET] == 0, "quota_in_porta"].isna().sum()),
         int((n == 0).sum())),
        ("stagioni", u["stagione"].nunique(), len(config.SEASONS_STORICHE)),
        ("squadre-stagione", len(u.groupby(["stagione", "team"])), None),
        ("partite", u["matchId"].nunique(), None),
    ]
    out = pd.DataFrame(righe, columns=["controllo", "valore", "atteso"])
    out["passa"] = out.apply(
        lambda r: bool(pd.isna(r["atteso"]) or r["valore"] == r["atteso"]), axis=1)
    return out


def matchid_unico(u: pd.DataFrame | None = None) -> dict:
    """`matchId` non si ripete fra stagioni?

    Serve a V1, non a V0, ed e' il motivo per cui sta qui: `build_predictors`
    aggancia il lato difensivo con `merge(on=["matchId", "opponent"])`. Se un
    `matchId` esistesse in due stagioni, il predittore dell'avversario verrebbe
    da un'altra stagione **senza che nulla lo dica**. Nessuno l'aveva
    verificato.
    """
    u = universo() if u is None else u
    per_id = u.groupby("matchId")["stagione"].nunique()
    return {
        "matchId distinti": int(len(per_id)),
        "max stagioni per matchId": int(per_id.max()),
        "unico": bool(per_id.max() == 1),
        "collisioni": int((per_id > 1).sum()),
    }


def deriva_livello(u: pd.DataFrame | None = None) -> pd.DataFrame:
    """Livello e dispersione del bersaglio, stagione per stagione.

    Il livello si muove, e va dichiarato: e' la ragione per cui V1 fa il
    walk-forward **dentro** la stagione (cosi' `mu` lo assorbe) invece di
    poolare e doverci mettere un effetto di stagione.
    """
    u = universo() if u is None else u
    r = u.groupby("stagione").apply(
        lambda d: pd.Series({
            "n": len(d),
            "shots": d[TARGET].mean(),
            "shots_sd": d[TARGET].std(),
            "sot": d[TARGET_PRECISIONE].mean(),
            "quota_in_porta": d[TARGET_PRECISIONE].sum() / d[TARGET].sum(),
            "var_su_media": d[TARGET].var() / d[TARGET].mean(),
        }), include_groups=False).reset_index()
    base = r["shots"].iloc[0]
    r["deriva_pct"] = (r["shots"] / base - 1.0) * 100.0
    return r


# --------------------------------------------------------------------------
# Il cluster di partita — quanto valgono davvero 3.778 righe
# --------------------------------------------------------------------------
def correlazione_lati(u: pd.DataFrame | None = None) -> pd.DataFrame:
    """I tentativi dei due lati della stessa partita sono correlati?

    **La domanda che rende leggibile ogni MDE di questa fase.** Le due squadre
    di una partita condividono ritmo, punteggio, arbitro e campo: se i due lati
    sono correlati, 3.778 righe non sono 3.778 osservazioni indipendenti e ogni
    errore standard appaiato va corretto di `sqrt(1 + rho)`.

    R1 ha misurato `rho ~ 0` **sui gol**, e non si eredita.

    **Misurato, il segno e' NEGATIVO e forte (~-0,35), non positivo**, con lo
    stesso segno in tutte e cinque le stagioni e intervalli che non contengono
    lo zero. L'attesa era il contrario — ritmo condiviso, quindi correlazione
    positiva — e il meccanismo vero e' piu' forte: **il possesso e' a somma
    costante**. Chi domina tira molto e lascia tirare poco, quindi i tentativi
    dei due lati si sottraggono invece di sommarsi.

    La conseguenza va nel verso **favorevole**, ed e' per questo che va detta:
    `sqrt(1 - 0,35) = 0,81`, cioe' gli errori standard appaiati sono piu'
    **piccoli** del nominale e le 3.778 righe valgono, per un confronto
    appaiato, piu' di 3.778 indipendenti. Il fattore va comunque applicato: un
    fattore favorevole non dichiarato resta un numero sbagliato.
    """
    u = universo() if u is None else u
    righe = []
    for st, d in u.groupby("stagione"):
        # `is_home` e' 0/1 in alcune stagioni e booleana in altre: si normalizza
        # invece di indicizzare con `True`, che su una colonna intera solleva.
        casa = d.assign(_casa=d["is_home"].astype(bool))
        w = casa.pivot_table(index="matchId", columns="_casa", values=TARGET).dropna()
        if len(w) < 3 or w.shape[1] < 2:
            continue
        a = w[True].to_numpy(dtype=float)
        b = w[False].to_numpy(dtype=float)
        rho = float(np.corrcoef(a, b)[0, 1])
        n = len(w)
        # Fisher, per un intervallo che non sbatte contro |rho| = 1.
        z = np.arctanh(np.clip(rho, -0.999999, 0.999999))
        se = 1.0 / np.sqrt(max(n - 3, 1))
        righe.append({
            "stagione": st, "partite": n, "corr": rho,
            "ic95_basso": float(np.tanh(z - 1.96 * se)),
            "ic95_alto": float(np.tanh(z + 1.96 * se)),
            "fattore_se": float(np.sqrt(max(1.0 + rho, 0.0))),
        })
    return pd.DataFrame(righe)


def fattore_cluster(u: pd.DataFrame | None = None) -> dict:
    """Il fattore di cui va moltiplicato ogni errore standard appaiato.

    Riportato **pooled e per stagione**: un pooled solo nasconderebbe che il
    fattore cambia, e cambiare e' l'unica cosa che lo renderebbe pericoloso.
    """
    tab = correlazione_lati(u)
    if tab.empty:
        return {"corr_pooled": float("nan"), "fattore_se": float("nan"), "n": 0}
    peso = tab["partite"].to_numpy(dtype=float)
    rho = float(np.average(tab["corr"].to_numpy(dtype=float), weights=peso))
    return {
        "corr_pooled": rho,
        "fattore_se": float(np.sqrt(max(1.0 + rho, 0.0))),
        "corr_min": float(tab["corr"].min()),
        "corr_max": float(tab["corr"].max()),
        "stesso_segno": bool((tab["corr"] > 0).all() or (tab["corr"] < 0).all()),
        "partite": int(peso.sum()),
        "righe": int(2 * peso.sum()),
    }


# --------------------------------------------------------------------------
# Le linee
# --------------------------------------------------------------------------
def base_rate_linee(u: pd.DataFrame | None = None, linee=LINEE_TIRI) -> pd.DataFrame:
    """Tasso base di ciascuna linea, con la regola applicata meccanicamente.

    Una linea fuori da `BASE_RATE_AMMESSO` **non si pubblica**: e' la regola
    dichiarata, non un giudizio a posteriori.
    """
    u = universo() if u is None else u
    y = u[TARGET].to_numpy(dtype=float)
    media, sd = float(np.mean(y)), float(np.std(y, ddof=1))
    righe = []
    for ln in linee:
        p = float(np.mean(y > ln))
        righe.append({
            "linea": ln,
            "tasso_base": p,
            "sd_dalla_media": (ln - media) / sd,
            "dentro_regola": bool(BASE_RATE_AMMESSO[0] <= p <= BASE_RATE_AMMESSO[1]),
        })
    return pd.DataFrame(righe)


def confronto_con_le_linee_sot() -> pd.DataFrame:
    """Le linee delle due fasi, affiancate in unita' di deviazione standard.

    E' l'argomento di `REGOLA_LINEE` reso un numero: le linee dei tentativi non
    sono state inventate, sono le linee dei tiri in porta trasportate sulla
    scala del nuovo bersaglio.
    """
    from . import validate as V

    u = universo()
    righe = []
    for nome, col, linee in (("tiri in porta", TARGET_PRECISIONE, V.LINES),
                             ("tentativi", TARGET, LINEE_TIRI)):
        y = u[col].to_numpy(dtype=float)
        m, s = float(np.mean(y)), float(np.std(y, ddof=1))
        for ln in linee:
            righe.append({"bersaglio": nome, "media": m, "sd": s,
                          "linea": ln, "sd_dalla_media": (ln - m) / s})
    return pd.DataFrame(righe)


# --------------------------------------------------------------------------
# L'identita' di dispersione che decide lo strato 2
# --------------------------------------------------------------------------
def _chiave_lato(u: pd.DataFrame, lato: str) -> pd.DataFrame:
    """Numeratore e denominatore della quota, per il lato richiesto.

    * `attacco` — la precisione della squadra sui propri tentativi;
    * `difesa`  — la precisione che la squadra **concede**, da `sot_conceded` e
      `shots_conceded`, che esistono gia' in `team_match`;
    * `campo`   — casa contro trasferta.

    **La chiave della difesa e' `team`, non `opponent`**, ed e' un errore che
    questo blocco ha commesso e corretto: `sot_conceded` sulla riga `(i, j)` sono
    i tiri in porta di `j`, quindi aggregarli sotto la chiave `j` ricostruisce
    **l'attacco di `j`** e i due lati danno lo stesso identico `phi`. Il difetto
    e' visibile solo perche' i due numeri coincidevano a ogni cifra: con una
    chiave sbagliata ma non degenere sarebbe passato.

    **Il lato `campo` ha 10 unita' e 5 gradi di liberta'**, quindi il test di
    dispersione li' e' quasi cieco (il MDE lo dichiara). Non e' il piu' potente
    dei tre come si potrebbe credere guardando l'`n` per cella: la strada buona
    per il campo e' il test F di `test_eterogeneita_glm`, che lo stima come un
    coefficiente invece che come dispersione.
    """
    if lato == "attacco":
        return pd.DataFrame({"stagione": u["stagione"], "chiave": u["team"],
                             "k": u[TARGET_PRECISIONE], "n": u[TARGET]})
    if lato == "difesa":
        return pd.DataFrame({"stagione": u["stagione"], "chiave": u["team"],
                             "k": u["sot_conceded"], "n": u["shots_conceded"]})
    if lato == "campo":
        return pd.DataFrame({"stagione": u["stagione"],
                             "chiave": np.where(u["is_home"], "casa", "trasferta"),
                             "k": u[TARGET_PRECISIONE], "n": u[TARGET]})
    raise ValueError(f"lato ignoto: {lato!r}. Ammessi: {LATI}")


def quota_aggregata(u: pd.DataFrame | None = None, lato: str = "attacco") -> pd.DataFrame:
    """La quota in porta aggregata a `(stagione, chiave)`.

    **Il denominatore si conta, non si assume**: l'Atalanta ha 35 partite nel
    2021-22 e nel 2022-23, e mettere 38 sbaglierebbe ogni quota proprio dove la
    perdita alla fonte non e' casuale.
    """
    u = universo() if u is None else u
    d = _chiave_lato(u, lato)
    agg = d.groupby(["stagione", "chiave"], as_index=False)[["k", "n"]].sum()
    agg = agg[agg["n"] > 0].reset_index(drop=True)
    p_s = agg.groupby("stagione").apply(
        lambda g: g["k"].sum() / g["n"].sum(), include_groups=False)
    agg["p_stagione"] = agg["stagione"].map(p_s)
    agg["p_hat"] = agg["k"] / agg["n"]
    agg["atteso"] = agg["n"] * agg["p_stagione"]
    var = agg["n"] * agg["p_stagione"] * (1.0 - agg["p_stagione"])
    agg["residuo_pearson"] = (agg["k"] - agg["atteso"]) / np.sqrt(var)
    agg["lato"] = lato
    return agg


def _x2(agg: pd.DataFrame) -> float:
    """La statistica di Pearson delle quote aggregate contro il numero unico."""
    return float(np.sum(agg["residuo_pearson"].to_numpy(dtype=float) ** 2))


def _gdl(agg: pd.DataFrame) -> int:
    """Righe meno le quote di stagione stimate: un parametro per stagione."""
    return int(len(agg) - agg["stagione"].nunique())


def rho_intraclasse(u: pd.DataFrame | None = None) -> dict:
    """La sovradispersione **di partita**, che entra nel nullo del test.

    E' il pezzo che il chi-quadro teorico non sa e che, ignorato, farebbe
    rifiutare il test sempre. `phi = 1 + rho*(n_medio - 1)` e' l'identita' della
    beta-binomiale, letta al contrario per ricavare `rho` dalla dispersione
    osservata sulle unita' squadra-partita.
    """
    u = universo() if u is None else u
    d = u[u[TARGET] > 0]
    p_s = d.groupby("stagione").apply(
        lambda g: g[TARGET_PRECISIONE].sum() / g[TARGET].sum(), include_groups=False)
    p = d["stagione"].map(p_s).to_numpy(dtype=float)
    n = d[TARGET].to_numpy(dtype=float)
    k = d[TARGET_PRECISIONE].to_numpy(dtype=float)
    res2 = (k - n * p) ** 2 / (n * p * (1.0 - p))
    phi = float(np.sum(res2) / (len(d) - d["stagione"].nunique()))
    n_medio = float(np.mean(n))
    rho = float(max((phi - 1.0) / (n_medio - 1.0), 0.0))
    return {"phi_squadra_partita": phi, "n_medio": n_medio,
            "rho_intraclasse": rho, "righe": int(len(d))}


def livello_sbagliato(u: pd.DataFrame | None = None) -> pd.DataFrame:
    """Perche' `phi = 1,101` a livello squadra-partita NON risponde.

    Mette i due livelli affiancati con il **MDE di ciascuno**, cosi' che citare
    la dispersione di squadra-partita come risposta risulti visibilmente un
    errore. A ~12,6 tentativi il rumore binomiale della quota vale ~13 punti e
    una differenza fra squadre di 2-3 punti ci sparisce dentro; a ~470 no.
    """
    u = universo() if u is None else u
    righe = []
    for livello, agg in (("squadra-partita",
                          pd.DataFrame({
                              "stagione": u.loc[u[TARGET] > 0, "stagione"],
                              "n": u.loc[u[TARGET] > 0, TARGET],
                              "k": u.loc[u[TARGET] > 0, TARGET_PRECISIONE]})),
                         ("squadra-stagione", quota_aggregata(u, "attacco"))):
        if "p_stagione" not in agg.columns:
            p_s = agg.groupby("stagione").apply(
                lambda g: g["k"].sum() / g["n"].sum(), include_groups=False)
            agg = agg.copy()
            agg["p_stagione"] = agg["stagione"].map(p_s)
            var = agg["n"] * agg["p_stagione"] * (1.0 - agg["p_stagione"])
            agg["residuo_pearson"] = (agg["k"] - agg["n"] * agg["p_stagione"]) / np.sqrt(var)
        gdl = _gdl(agg)
        n_bar = float(agg["n"].mean())
        p = float(agg["k"].sum() / agg["n"].sum())
        # MDE in tau: quel phi che il test vede all'80% di potenza.
        phi_crit = 1.0 + stats.norm.isf(ALPHA_TEST) * np.sqrt(2.0 / gdl)
        phi_80 = phi_crit + stats.norm.ppf(POTENZA_OBIETTIVO) * np.sqrt(2.0 / gdl)
        tau_mde = float(np.sqrt(max(phi_80 - 1.0, 0.0) * p * (1.0 - p) / n_bar))
        righe.append({
            "livello": livello, "unita": len(agg), "gdl": gdl,
            "n_medio": n_bar, "sd_binomiale_quota": float(np.sqrt(p * (1 - p) / n_bar)),
            "phi_osservato": _x2(agg) / gdl,
            "tau_mde": tau_mde, "tau_mde_punti": tau_mde * 100.0,
        })
    return pd.DataFrame(righe)


def phi_e_tau(agg: pd.DataFrame, phi0: float = 1.0) -> dict:
    """Da `X2` alla deviazione standard della quota **fra le chiavi**.

    `E[X2/gdl] = phi0 + tau^2 * n_medio / (p(1-p))`, da cui `tau`. `phi0` e' il
    valore atteso **sotto il nullo vero**, cioe' con la sovradispersione di
    partita dentro: passare 1,0 sovrastimerebbe `tau` attribuendo all'effetto di
    squadra il rumore che gia' c'era. Va preso da `nullo_simulato`.

    `tau` esce in **due unita'**: punti di quota, e tiri in porta per
    squadra-partita, che e' l'unita' in cui il resto del progetto ragiona.
    """
    gdl = _gdl(agg)
    phi = _x2(agg) / gdl
    n_bar = float(agg["n"].mean())
    p = float(agg["k"].sum() / agg["n"].sum())
    tau2 = max(phi - phi0, 0.0) * p * (1.0 - p) / n_bar
    tau = float(np.sqrt(tau2))
    tentativi_sp = float(agg["n"].sum() / _partite_per_chiave(agg))
    return {
        "unita": int(len(agg)), "gdl": gdl, "x2": _x2(agg), "phi": phi,
        "phi0": phi0, "p": p, "n_medio": n_bar,
        "tau": tau, "tau_punti": tau * 100.0,
        "tau_in_sot_per_partita": tau * tentativi_sp,
    }


def _partite_per_chiave(agg: pd.DataFrame) -> float:
    """Tentativi medi per squadra-partita, per convertire `tau` in tiri.

    Approssimato con 38 partite per squadra-stagione dove la chiave e' una
    squadra; sul lato `campo` la conversione non ha senso e vale 1.
    """
    n_bar = float(agg["n"].mean())
    return n_bar / 38.0 if n_bar < 2000 else 1.0


def mde_tau(agg: pd.DataFrame, phi0: float = 1.0, sd_phi0: float | None = None,
            potenza: float = POTENZA_OBIETTIVO, alpha: float = ALPHA_TEST) -> dict:
    """L'effetto minimo rilevabile, in `tau`.

    Senza questo numero un non-rifiuto non e' leggibile — e' la lezione della
    Fase 6D applicata a un test di dispersione invece che a un predittore.
    """
    gdl = _gdl(agg)
    sd = float(np.sqrt(2.0 / gdl)) if sd_phi0 is None else float(sd_phi0)
    n_bar = float(agg["n"].mean())
    p = float(agg["k"].sum() / agg["n"].sum())
    phi_crit = phi0 + stats.norm.isf(alpha) * sd
    phi_80 = phi_crit + stats.norm.ppf(potenza) * sd
    tau_mde = float(np.sqrt(max(phi_80 - phi0, 0.0) * p * (1.0 - p) / n_bar))
    return {"gdl": gdl, "sd_phi": sd, "phi_critico": phi_crit,
            "phi_a_potenza": phi_80, "tau_mde": tau_mde,
            "tau_mde_punti": tau_mde * 100.0,
            "tau_mde_in_sot_per_partita": tau_mde * _partite_per_chiave(agg)}


# --------------------------------------------------------------------------
# Il nullo simulato
# --------------------------------------------------------------------------
def _beta_binomiale(rng, n: np.ndarray, p: np.ndarray, rho: float) -> np.ndarray:
    """Estrazioni beta-binomiali con media `p` e correlazione intraclasse `rho`.

    Con `rho = 0` degenera nella binomiale, ed e' voluto: il nullo senza
    sovradispersione di partita deve restare ottenibile per la taratura.
    """
    if rho <= 0:
        return rng.binomial(n.astype(int), p)
    s = 1.0 / rho - 1.0
    a = np.clip(p * s, 1e-9, None)
    b = np.clip((1.0 - p) * s, 1e-9, None)
    return rng.binomial(n.astype(int), rng.beta(a, b))


def nullo_simulato(u: pd.DataFrame | None = None, lato: str = "attacco",
                   tau: float = 0.0, rho_partita: float | None = None,
                   n_sim: int = 2000, seed: int = config.SEED) -> np.ndarray:
    """Distribuzione di `phi = X2/gdl` sotto un mondo con `tau` noto.

    Simula alla granularita' **squadra-partita** e poi aggrega, che e' l'unico
    modo di far entrare la sovradispersione di partita nel nullo: aggregando
    prima, quella variabilita' sparirebbe e il test rifiuterebbe sempre.

    `tau = 0` da' il nullo; `tau > 0` da' l'alternativa e serve alla taratura.
    """
    u = universo() if u is None else u
    rho = rho_intraclasse(u)["rho_intraclasse"] if rho_partita is None else rho_partita
    d = _chiave_lato(u, lato)
    d = d[d["n"] > 0].reset_index(drop=True)

    p_s = d.groupby("stagione").apply(
        lambda g: g["k"].sum() / g["n"].sum(), include_groups=False)
    p_base = d["stagione"].map(p_s).to_numpy(dtype=float)
    n = d["n"].to_numpy(dtype=float)
    chiavi, codici = np.unique(
        d["stagione"].astype(str) + "|" + d["chiave"].astype(str), return_inverse=True)

    rng = np.random.default_rng(seed)
    out = np.empty(n_sim, dtype=float)
    logit = np.log(p_base / (1.0 - p_base))

    for s in range(n_sim):
        if tau > 0:
            scarto = rng.normal(0.0, tau, size=len(chiavi))[codici]
            # `tau` e' sulla scala della quota: si converte in logit con la
            # derivata locale, cosi' che il MDE dichiarato e il mondo simulato
            # parlino della stessa grandezza.
            pv = 1.0 / (1.0 + np.exp(-(logit + scarto / (p_base * (1.0 - p_base)))))
            pv = np.clip(pv, 1e-6, 1 - 1e-6)
        else:
            pv = p_base
        k = _beta_binomiale(rng, n, pv, rho)

        num = np.bincount(codici, weights=k, minlength=len(chiavi))
        den = np.bincount(codici, weights=n, minlength=len(chiavi))
        pk = np.bincount(codici, weights=n * p_base, minlength=len(chiavi)) / den
        var = den * pk * (1.0 - pk)
        x2 = np.sum((num - den * pk) ** 2 / var)
        out[s] = x2 / (len(chiavi) - d["stagione"].nunique())

    return out


def test_eterogeneita(u: pd.DataFrame | None = None, lato: str = "attacco",
                      n_sim: int = 2000, seed: int = config.SEED,
                      mde_tarato: float | None = None) -> dict:
    """Il test, con il nullo generato e la potenza dichiarata.

    Ritorna sia il `p` simulato sia quello del chi-quadro teorico: il secondo e'
    li' per **mostrare quanto sarebbe stato sbagliato**, non per essere usato.

    `mde_tarato` e' il MDE da `mde_da_taratura`, e quando c'e' **e' quello che
    decide** `supera_mde`: il MDE analitico e' ottimistico di circa un terzo, e
    usarlo renderebbe piu' facile dichiarare un effetto reale. Le due colonne
    restano affiancate, cosi' che la differenza si veda invece di sparire.
    """
    u = universo() if u is None else u
    agg = quota_aggregata(u, lato)
    nullo = nullo_simulato(u, lato=lato, tau=0.0, n_sim=n_sim, seed=seed)
    phi_oss = _x2(agg) / _gdl(agg)
    phi0 = float(np.mean(nullo))
    sd0 = float(np.std(nullo, ddof=1))

    p_sim = float((np.sum(nullo >= phi_oss) + 1.0) / (n_sim + 1.0))
    p_chi2 = float(stats.chi2.sf(_x2(agg), _gdl(agg)))
    t = phi_e_tau(agg, phi0=phi0)
    m = mde_tau(agg, phi0=phi0, sd_phi0=sd0, potenza=POTENZA_OBIETTIVO)

    soglia = PP.soglia_sidak(k=len(LATI), alpha=ALPHA_TEST)
    z = (phi_oss - phi0) / sd0 if sd0 > 0 else float("nan")
    mde = m["tau_mde"] if mde_tarato is None else float(mde_tarato)
    return {
        "lato": lato, "unita": t["unita"], "gdl": t["gdl"],
        "phi_osservato": phi_oss, "phi0_simulato": phi0, "sd_phi0": sd0,
        "z": float(z), "soglia_sidak": soglia, "rifiuta": bool(z > soglia),
        "p_simulato": p_sim, "p_chi2_teorico": p_chi2,
        "tau": t["tau"], "tau_punti": t["tau_punti"],
        "tau_mde_analitico": m["tau_mde"],
        "tau_mde": mde, "tau_mde_punti": mde * 100.0,
        "mde_e_tarato": bool(mde_tarato is not None),
        "supera_mde": bool(t["tau"] > mde),
    }


#: La griglia su cui la potenza viene tarata. Dichiarata, non scelta guardando
#: dove cade il risultato: copre da zero a piu' del doppio del `tau` analitico.
TAU_GRIGLIA = (0.0, 0.005, 0.010, 0.013, 0.015, 0.0175, 0.020, 0.025, 0.030)


def mde_da_taratura(tar: pd.DataFrame, potenza: float = POTENZA_OBIETTIVO) -> float:
    """Il `tau` a cui la potenza SIMULATA raggiunge l'obiettivo.

    **E' questo il MDE da pubblicare, non quello di `mde_tau`.** La formula
    analitica assume che `phi` sia normale con deviazione standard costante;
    sotto l'alternativa la sd cresce con `tau`, e il risultato e' che il MDE
    analitico e' **ottimistico**. Misurato: al `tau` analitico la potenza vera
    vale ~53%, non 80%.

    E' la stessa disciplina della Fase 6D — un MDE dichiarato serve a rendere
    leggibile un non-rifiuto, quindi un MDE sbagliato nella direzione comoda e'
    peggio che non averlo. Interpolazione lineare fra i due punti della griglia
    che circondano l'obiettivo; `nan` se la griglia non lo attraversa.
    """
    d = tar.sort_values("tau")
    x = d["tau"].to_numpy(dtype=float)
    y = d["potenza"].to_numpy(dtype=float)
    sopra = np.nonzero(y >= potenza)[0]
    if len(sopra) == 0:
        return float("nan")
    i = int(sopra[0])
    if i == 0:
        return float(x[0])
    x0, x1, y0, y1 = x[i - 1], x[i], y[i - 1], y[i]
    if y1 == y0:
        return float(x1)
    return float(x0 + (potenza - y0) * (x1 - x0) / (y1 - y0))


def taratura_test(u: pd.DataFrame | None = None, lato: str = "attacco",
                  tau_griglia=TAU_GRIGLIA,
                  n_sim: int = 400, seed: int = config.SEED) -> pd.DataFrame:
    """La macchina messa alla prova su mondi in cui la risposta e' nota.

    E' l'unico modo di distinguere «il test ha trovato eterogeneita'» da «il
    test rifiuta sempre». Attese **dichiarate prima**: ~5% alla riga `tau = 0`
    (che e' la dimensione, non zero — stessa lettura di `PP.potenza(0, se)`),
    ~80% al MDE, monotona in mezzo.
    """
    u = universo() if u is None else u
    nullo = nullo_simulato(u, lato=lato, tau=0.0, n_sim=n_sim, seed=seed)
    phi0, sd0 = float(np.mean(nullo)), float(np.std(nullo, ddof=1))
    soglia = phi0 + PP.soglia_sidak(k=len(LATI), alpha=ALPHA_TEST) * sd0

    agg = quota_aggregata(u, lato)
    mde = mde_tau(agg, phi0=phi0, sd_phi0=sd0)["tau_mde"]

    righe = []
    for i, tau in enumerate(tau_griglia):
        d = nullo_simulato(u, lato=lato, tau=tau, n_sim=n_sim, seed=seed + 1000 + i)
        righe.append({
            "tau": tau, "tau_punti": tau * 100.0,
            "phi_medio": float(np.mean(d)),
            "rifiuti": int(np.sum(d > soglia)),
            "potenza": float(np.mean(d > soglia)),
            "atteso": ("dimensione ~5%" if tau == 0 else
                       ("~80%" if abs(tau - mde) < 1e-9 else "")),
        })
    out = pd.DataFrame(righe)
    out.attrs["soglia"] = soglia
    out.attrs["tau_mde"] = mde
    return out


# --------------------------------------------------------------------------
# La strada di controllo: GLM binomiale in quasi-verosimiglianza
# --------------------------------------------------------------------------
def _glm_binomiale(k: np.ndarray, n: np.ndarray, X: np.ndarray) -> dict:
    """GLM binomiale con logit, senza penalita'. Devianza e Pearson.

    Non usa `TeamModel`: li' la ridge e' indispensabile all'identificabilita' e
    renderebbe la devianza non confrontabile fra modelli annidati. Qui
    l'identificabilita' viene dalla categoria di riferimento omessa.
    """
    def neg(b):
        eta = np.clip(X @ b, -30, 30)
        p = 1.0 / (1.0 + np.exp(-eta))
        ll = np.sum(k * np.log(np.clip(p, 1e-12, 1)) +
                    (n - k) * np.log(np.clip(1 - p, 1e-12, 1)))
        return -ll, -(X.T @ (k - n * p))

    b0 = np.zeros(X.shape[1])
    tot = k.sum() / n.sum()
    b0[0] = np.log(tot / (1 - tot))
    res = optimize.minimize(neg, b0, jac=True, method="L-BFGS-B",
                            options={"maxiter": 500, "ftol": 1e-12})
    eta = np.clip(X @ res.x, -30, 30)
    p = 1.0 / (1.0 + np.exp(-eta))
    kk, nn = np.clip(k, 1e-9, None), n
    dev = 2.0 * np.sum(
        kk * np.log(kk / np.clip(nn * p, 1e-12, None)) +
        np.where(nn - k > 0, (nn - k) * np.log(
            np.clip((nn - k), 1e-9, None) / np.clip(nn * (1 - p), 1e-12, None)), 0.0))
    pearson = float(np.sum((k - n * p) ** 2 / np.clip(n * p * (1 - p), 1e-12, None)))
    return {"beta": res.x, "devianza": float(dev), "pearson": pearson,
            "k_par": int(X.shape[1]), "p": p}


def test_eterogeneita_glm(u: pd.DataFrame | None = None) -> pd.DataFrame:
    """La seconda strada, indipendente dalla prima: test F annidati con `phi`.

    Due strade che concordano sono un risultato; una sola e' un'asserzione. E'
    la stessa macchina di quasi-verosimiglianza di `recording_stability`, su
    unita' squadra-partita invece che squadra-stagione: qui il `phi` del modello
    pieno assorbe la sovradispersione che li' andava simulata.
    """
    u = universo() if u is None else u
    d = u[u[TARGET] > 0].reset_index(drop=True)
    k = d[TARGET_PRECISIONE].to_numpy(dtype=float)
    n = d[TARGET].to_numpy(dtype=float)

    st = pd.get_dummies(d["stagione"], drop_first=True).to_numpy(dtype=float)
    att = pd.get_dummies(d["team"], drop_first=True).to_numpy(dtype=float)
    dif = pd.get_dummies(d["opponent"], drop_first=True).to_numpy(dtype=float)
    casa = d["is_home"].to_numpy(dtype=float).reshape(-1, 1)
    uno = np.ones((len(d), 1))

    base = np.hstack([uno, st])
    modelli = {
        "solo stagione": base,
        "+ campo": np.hstack([base, casa]),
        "+ attacco": np.hstack([base, casa, att]),
        "+ difesa": np.hstack([base, casa, att, dif]),
    }
    fit = {nome: _glm_binomiale(k, n, X) for nome, X in modelli.items()}
    pieno = fit["+ difesa"]
    phi = pieno["pearson"] / (len(d) - pieno["k_par"])

    ordine = list(modelli)
    righe = []
    for prec, cur in zip(ordine, ordine[1:]):
        a, b = fit[prec], fit[cur]
        gdl1 = b["k_par"] - a["k_par"]
        gdl2 = len(d) - pieno["k_par"]
        f = (a["devianza"] - b["devianza"]) / gdl1 / phi
        righe.append({
            "confronto": f"{prec} -> {cur}", "gdl_num": gdl1, "gdl_den": gdl2,
            "delta_devianza": a["devianza"] - b["devianza"], "phi": phi,
            "F": f, "p": float(stats.f.sf(f, gdl1, gdl2)),
        })
    return pd.DataFrame(righe)


# --------------------------------------------------------------------------
# Il thinning: la premessa della gerarchia, verificata dove la risposta e' nota
# --------------------------------------------------------------------------
def thinning_simulato(lam: float = 12.58, p: float = 0.3303, r: float = 30.0,
                      n: int = 200_000, seed: int = config.SEED) -> dict:
    """Se `N ~ NB2(lam, r)` e `S|N ~ Bin(N, p)`, allora `S ~ NB2(lam*p, r)`.

    E' la proprieta' su cui poggia l'intera gerarchia: senza, la marginale dei
    tiri in porta non avrebbe forma chiusa e V2 dovrebbe convolvere
    numericamente. **Verificata su dati generati**, dove la risposta e' nota,
    invece che asserita — e con `fit_r` del progetto, non con una formula
    scritta apposta.
    """
    from . import dispersion as D

    rng = np.random.default_rng(seed)
    N = rng.negative_binomial(r, r / (r + lam), size=n)
    S = rng.binomial(N, p)
    r_hat = D.fit_r(S.astype(float), np.full(n, lam * p))
    return {
        "lam": lam, "p": p, "r_vero": r,
        "media_N": float(N.mean()), "media_S": float(S.mean()),
        "media_attesa_S": lam * p,
        "r_stimata_su_S": float(r_hat),
        "scarto_media_pct": float((S.mean() / (lam * p) - 1.0) * 100.0),
        "scarto_r_pct": float((r_hat / r - 1.0) * 100.0),
    }


# --------------------------------------------------------------------------
# Il verdetto, applicato meccanicamente
# --------------------------------------------------------------------------
def tabella_eterogeneita(u: pd.DataFrame | None = None, n_sim: int = 2000,
                         n_sim_taratura: int = 1000,
                         seed: int = config.SEED) -> tuple[pd.DataFrame, dict]:
    """I tre lati con il MDE **tarato**, piu' le tre tarature che lo producono.

    Esiste perche' il MDE tarato costa una simulazione per lato e per punto
    della griglia: calcolarlo dentro `test_eterogeneita` lo farebbe rifare a
    ogni chiamata senza che si veda.
    """
    u = universo() if u is None else u
    righe, tarature = [], {}
    for lato in LATI:
        tar = taratura_test(u, lato=lato, n_sim=n_sim_taratura, seed=seed)
        mde = mde_da_taratura(tar)
        tarature[lato] = tar
        righe.append(test_eterogeneita(u, lato=lato, n_sim=n_sim, seed=seed,
                                       mde_tarato=mde))
    return pd.DataFrame(righe), tarature


def verdetto_strato2(tab: pd.DataFrame | None = None,
                     u: pd.DataFrame | None = None,
                     n_sim: int = 2000) -> dict:
    """`CRITERIO_STRATO2` applicato al codice, non a occhio.

    E' la forma di `ricalibrazione.verdetto()`: il criterio e' scritto prima di
    guardare i numeri e questa funzione lo esegue. Il ramo del collasso non e'
    un fallimento — e' un modello con meno parti e una composizione esatta.
    """
    if tab is None:
        u = universo() if u is None else u
        tab, _ = tabella_eterogeneita(u, n_sim=n_sim)

    rifiuta = tab["rifiuta"].to_numpy(dtype=bool)
    supera = tab["supera_mde"].to_numpy(dtype=bool)
    stima = bool((rifiuta & supera).any())
    lati_ok = list(tab.loc[rifiuta & supera, "lato"])
    return {
        "criterio": CRITERIO_STRATO2,
        "lati_che_rifiutano": list(tab.loc[rifiuta, "lato"]),
        "lati_che_superano_mde": list(tab.loc[supera, "lato"]),
        "lati_adottati": lati_ok,
        "stima_lo_strato_2": stima,
        "ramo": "modello di precisione" if stima else "p_lega (strato 2 collassato)",
        "forma_chiusa_valida": not stima,
    }
