# -*- coding: utf-8 -*-
"""Fase 10 / Blocco R3 — la classifica: simulare il RESTO di una stagione.

**Il vincolo che struttura il blocco viene da R0 e non si aggira: non si simula
una stagione da zero.** Le prime giornate non hanno previsione affatto — il
walk-forward di E3 pretende 30 partite di training — e la prima giornata piena e'
la sesta o la settima, mai prima. Non esiste una probabilita' di scudetto alla
prima giornata, e questo modulo non finge che esista: simula il **resto** di una
stagione dalla giornata `k`, **data la classifica vera a `k`**.

**E la seconda cosa che viene da R0 e' quanto poco si puo' concludere.** Una
probabilita' di scudetto ha **una realizzazione per stagione**: cinque stagioni
sono cinque estrazioni, e previsioni fatte a giornate diverse della stessa
stagione **non sono indipendenti** perche' condividono l'esito. Ne segue che il
blocco **non valida le probabilita' di scudetto** — non ci sono i numeri per
farlo — e valida invece cio' che ha 100 realizzazioni per giornata di partenza:
**i punti finali di ogni squadra**, con copertura e PIT.

**Gli ingressi.**

- La **classifica vera** a `k` e i risultati veri vengono dal **calendario
  completo della fonte dei voti**: 380 partite per stagione, gol mai nulli. E' il
  punto in cui il buco di WhoScored **non morde** — R1 lo aveva gia' dichiarato:
  il buco sta negli ingressi, non nel bersaglio.
- Le **probabilita' 1X2** vengono da R2-bis, ricalibrate con Platt walk-forward
  dove esiste un passato su cui stimarle.
- Il **punteggio** — che serve alla differenza reti, cioe' allo scioglimento dei
  pari merito — viene dalla congiunta di R1 **condizionata all'esito
  ricalibrato**. E' la costruzione che tiene insieme le due cose: la
  ricalibrazione agisce sull'esito, e il punteggio si estrae dentro la classe
  estratta. Cosi' i punti simulati usano le probabilita' adottate da R2-bis e la
  differenza reti resta coerente con esse.

> **Il limite che R2-bis ha misurato e che qui va DICHIARATO accanto ai numeri
> (vincolo 5): la classifica simulata e' troppo corta.** L'identita' di
> dispersione dice che la varianza dei punti fra le squadre e' circa il doppio di
> quella che il modello dichiara, 1,42 volte nella sola seconda meta'. Ne segue
> che le code — scudetto e retrocessione — sono **troppo grasse**: il modello
> distribuisce probabilita' a squadre che non hanno una vera possibilita' e ne
> toglie a chi ce l'ha. `copertura()` lo misura sui punti finali invece di
> lasciarlo come avvertenza.

**Lo scioglimento dei pari merito e' una semplificazione dichiarata.** La Serie A
usa **gli scontri diretti**; qui si usa la differenza reti, poi i gol fatti, poi
un'estrazione col seme del progetto. Ricostruire gli scontri diretti dentro una
simulazione richiederebbe di tenere la matrice degli incroci in ogni replica;
`pari_merito()` misura **quanto spesso la scelta conta** invece di dichiararla
irrilevante.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from . import config, perimetro as PM, ricalibrazione as RC, risultato as R

#: Repliche della simulazione. Dichiarato: con 10.000 l'errore Monte Carlo su una
#: probabilita' vicina a 0,5 vale 0,005, cioe' meno di quanto qualunque
#: conclusione del blocco possa distinguere.
REPLICHE = 10000

#: Le giornate di partenza su cui si valuta, **dichiarate e non scelte guardando
#: i risultati**: un quarto, la meta' esatta (il giro di boa) e tre quarti di
#: stagione. Sotto la 6a non esiste una giornata piena (R0), quindi la prima non
#: e' una scelta ma un limite.
K_VALUTAZIONE = (10, 19, 28)

#: Le tre affermazioni di classifica. I posti sono quelli del regolamento del
#: campionato, non soglie ricavate dai dati.
POSTI_EUROPA = 4
POSTI_RETROCESSIONE = 3

#: Le varianti confrontate. **Ogni baseline e' composto con la STESSA procedura
#: del modello** — stessa congiunta, stesso scioglimento dei pari merito, stesse
#: repliche — altrimenti si misurerebbe la composizione invece del lambda. Sono
#: gli stessi baseline che R2 ha gia' usato, e non nuovi inventati qui.
VARIANTI = ("modello", "modello grezzo", "media squadra + campo", "media campionato")


# ---------------------------------------------------------------------------
# Il calendario completo, con le probabilita' attaccate
# ---------------------------------------------------------------------------

def _mappa() -> pd.DataFrame:
    a = pd.read_csv(PM.MAPPA_PARTITE)
    a = a[a["matchId"].notna()].copy()
    a["matchId"] = a["matchId"].astype("int64")
    return a[["stagione", "partita_id", "matchId"]]


def calendario(stagioni=None, variante: str = "modello") -> pd.DataFrame:
    """Le 380 partite di ogni stagione, con la previsione attaccata dove esiste.

    **La riga viene dal calendario dei voti e non dal derivato di E3**, ed e' la
    scelta che rende il blocco possibile: una classifica ha bisogno di **tutte**
    le partite, comprese le 12 che WhoScored non ha e le prime cinque giornate,
    che una previsione non ce l'hanno. Il risultato di quelle si conosce lo
    stesso, quindi entrano nella classifica a `k`; se cadono nel **futuro** della
    simulazione ricevono il ripiego dichiarato qui sotto e si **contano**.

    `prevedibile` distingue i due casi, e nessun numero del blocco va letto senza
    la colonna `ripiego` che li conta.
    """
    cal = pd.read_parquet(PM.CALENDARIO)
    if stagioni is not None:
        cal = cal[cal["stagione"].isin(list(stagioni))]
    cal = cal.merge(_mappa(), on=["stagione", "partita_id"], how="left")

    d = RC.dati()
    if variante == "modello":
        P, applicata, _p = RC.walkforward_ricalibrazione(d, "platt")
    else:
        P, applicata, _p = RC.probabilita_decompresse(d, 1.0), None, None
        if variante != "modello grezzo":
            lc = np.maximum(d[f"{variante}_casa"].to_numpy(float), 0.05)
            lt = np.maximum(d[f"{variante}_trasferta"].to_numpy(float), 0.05)
            P = np.array([R.esiti(R.congiunta(a, b, 0.0)) for a, b in zip(lc, lt)])

    prev = pd.DataFrame({
        "stagione": d["stagione"].to_numpy(), "matchId": d["matchId"].to_numpy(),
        "p1": P[:, 0], "pX": P[:, 1], "p2": P[:, 2],
    })
    if variante in ("modello", "modello grezzo"):
        prev["lam_casa"] = d["lam_casa"].to_numpy()
        prev["lam_trasferta"] = d["lam_trasferta"].to_numpy()
    else:
        prev["lam_casa"] = np.maximum(d[f"{variante}_casa"].to_numpy(float), 0.05)
        prev["lam_trasferta"] = np.maximum(d[f"{variante}_trasferta"].to_numpy(float), 0.05)
    if applicata is not None:
        prev["ricalibrata"] = applicata
    else:
        prev["ricalibrata"] = False

    out = cal.merge(prev, on=["stagione", "matchId"], how="left")
    out["prevedibile"] = out["p1"].notna()

    # **Il ripiego, dichiarato e contato.** Una partita del futuro senza
    # previsione riceve i lambda medi di casa e trasferta **della sua stagione**,
    # cioe' il baseline meno informativo che il repository abbia. Sono al massimo
    # cinque per stagione e stanno tutte nelle due annate a cui WhoScored ha perso
    # partite: non e' una scelta di modellazione, e' il modo di non far sparire
    # una partita dalla classifica.
    for st, sub in out.groupby("stagione"):
        m = (out["stagione"] == st) & (~out["prevedibile"])
        if not m.any():
            continue
        lc = float(sub["lam_casa"].mean())
        lt = float(sub["lam_trasferta"].mean())
        p1, px, p2 = R.esiti(R.congiunta(lc, lt, 0.0))
        out.loc[m, ["lam_casa", "lam_trasferta", "p1", "pX", "p2"]] = [lc, lt, p1, px, p2]
    out["ripiego"] = ~out["prevedibile"]
    return out.reset_index(drop=True)


def copertura_previsioni(stagioni=None) -> pd.DataFrame:
    """Quante partite del calendario hanno una previsione, per stagione e per `k`.

    Si conta, non si assume: e' la tabella che dice quanto pesa il ripiego dentro
    ogni simulazione, e senza di essa «la classifica e' simulata dal modello»
    sarebbe un'affermazione senza denominatore.
    """
    cal = calendario(stagioni)
    righe = []
    for st, sub in cal.groupby("stagione"):
        riga = {"stagione": st, "partite": len(sub),
                "con previsione": int(sub["prevedibile"].sum())}
        for k in K_VALUTAZIONE:
            f = sub[sub["giornata"] > k]
            riga[f"ripiego dopo la {k}a"] = int((~f["prevedibile"]).sum())
        righe.append(riga)
    return pd.DataFrame(righe)


# ---------------------------------------------------------------------------
# La classifica vera
# ---------------------------------------------------------------------------

def _lungo(cal: pd.DataFrame) -> pd.DataFrame:
    """Una riga per squadra-partita: e' la forma in cui una classifica si somma."""
    a = cal.rename(columns={"casa": "team", "trasferta": "avversario",
                            "gol_casa": "gf", "gol_trasferta": "gs"})
    b = cal.rename(columns={"trasferta": "team", "casa": "avversario",
                            "gol_trasferta": "gf", "gol_casa": "gs"})
    col = ["stagione", "giornata", "team", "avversario", "gf", "gs"]
    L = pd.concat([a[col], b[col]], ignore_index=True)
    L["punti"] = np.select([L["gf"] > L["gs"], L["gf"] == L["gs"]], [3, 1], 0)
    return L


def classifica_a(stagione: str, k: int, cal: pd.DataFrame = None) -> pd.DataFrame:
    """La classifica vera dopo la giornata `k`. Punti, differenza reti, gol fatti.

    **`k` e' ordinale, non una data**, ed e' una scelta dichiarata: «dopo la
    giornata k» significa «tutte le partite con `giornata <= k`», anche quelle
    rinviate e giocate dopo. E' la convenzione con cui una classifica si legge a
    posteriori; un osservatore in tempo reale vedrebbe invece squadre con partite
    da recuperare. `partite_fuori_ordine()` misura quanto spesso le due letture
    divergono, invece di dichiarare la differenza trascurabile.
    """
    cal = calendario([stagione]) if cal is None else cal[cal["stagione"] == stagione]
    L = _lungo(cal)
    L = L[L["giornata"] <= k]
    g = L.groupby("team").agg(punti=("punti", "sum"), gf=("gf", "sum"),
                              gs=("gs", "sum"), giocate=("punti", "size"))
    g["dr"] = g["gf"] - g["gs"]
    return g.sort_values(["punti", "dr", "gf"], ascending=False)


def partite_fuori_ordine(stagioni=None) -> pd.DataFrame:
    """Quante partite si giocano fuori dall'ordine della propria giornata.

    E' la domanda aperta n. 4 di R0 — «non e' verificato che l'ordine per data
    basti a ricostruire la classifica progressiva in presenza di recuperi» —
    risposta con una misura invece che con un'assunzione. Una partita e' fuori
    ordine se si gioca **dopo** che la giornata successiva e' cominciata.
    """
    cal = calendario(stagioni)
    righe = []
    for st, sub in cal.groupby("stagione"):
        inizio = sub.groupby("giornata")["data"].min()
        n = 0
        for g, s in sub.groupby("giornata"):
            if g + 1 in inizio.index:
                n += int((s["data"] > inizio[g + 1]).sum())
        righe.append({"stagione": st, "partite": len(sub), "fuori ordine": n,
                      "quota": n / len(sub)})
    return pd.DataFrame(righe)


def verifica_calendario(stagioni=None) -> pd.DataFrame:
    """Il calendario regge le identita' che una stagione deve rispettare.

    Falsificabile e senza modelli di mezzo: 380 partite, 20 squadre, 38 partite a
    testa di cui 19 in casa, e l'identita' dei punti — la somma dei punti di
    tutte le squadre vale `3 x partite - pareggi`, perche' un pareggio distribuisce
    2 punti invece di 3. Se una qualsiasi non tornasse, ogni classifica del blocco
    sarebbe costruita su un calendario rotto.
    """
    cal = calendario(stagioni)
    righe = []
    for st, sub in cal.groupby("stagione"):
        L = _lungo(sub)
        per_team = L.groupby("team").size()
        casa = sub.groupby("casa").size()
        pareggi = int((sub["gol_casa"] == sub["gol_trasferta"]).sum())
        righe.append({
            "stagione": st, "partite": len(sub),
            "squadre": int(per_team.size),
            "38 partite a testa": bool((per_team == 38).all()),
            "19 in casa a testa": bool((casa == 19).all()),
            "punti totali": int(L["punti"].sum()),
            "attesi (3n - pareggi)": 3 * len(sub) - pareggi,
        })
    out = pd.DataFrame(righe)
    out["identita' dei punti"] = out["punti totali"] == out["attesi (3n - pareggi)"]
    return out


# ---------------------------------------------------------------------------
# La simulazione
# ---------------------------------------------------------------------------

def _celle_condizionate(lam_c: float, lam_t: float):
    """Per ciascuna delle tre classi, i punteggi possibili e la loro probabilita'.

    **E' il pezzo che tiene insieme la ricalibrazione e la differenza reti.** La
    congiunta di R1 da' `P(gc, gt)`; condizionandola alla classe si ottiene
    `P(gc, gt | esito)`, che non dipende da come la probabilita' dell'esito e'
    stata ricalibrata. Estraendo prima l'esito con la probabilita' **adottata** e
    poi il punteggio dentro la classe, i punti simulati usano la ricalibrazione e
    il punteggio resta coerente con essa.
    """
    p = R.congiunta(lam_c, lam_t, 0.0)
    n = p.shape[0]
    x, y = np.meshgrid(np.arange(n), np.arange(n), indexing="ij")
    fuori = []
    for m in (x > y, x == y, x < y):
        w = p[m]
        tot = w.sum()
        fuori.append((np.column_stack([x[m], y[m]]),
                      w / tot if tot > 0 else np.full(len(w), 1 / len(w))))
    return fuori


def simula(stagione: str, k: int, repliche: int = REPLICHE,
           variante: str = "modello", cal: pd.DataFrame = None,
           seed: int = None) -> dict:
    """Simula il resto della stagione dalla giornata `k`. Ritorna punti, dr, gf.

    Le matrici sono `(repliche, 20)` e le colonne sono le squadre nell'ordine di
    `squadre`. La classifica a `k` entra come **costante**: e' la storia, non una
    previsione, e simularla sarebbe simulare cio' che si sa gia'.
    """
    cal = calendario([stagione], variante) if cal is None else cal
    cal = cal[cal["stagione"] == stagione]
    rng = np.random.default_rng(config.SEED if seed is None else seed)

    cl = classifica_a(stagione, k, cal)
    squadre = sorted(cl.index)
    idx = {t: i for i, t in enumerate(squadre)}

    punti = np.tile(cl.loc[squadre, "punti"].to_numpy(float), (repliche, 1))
    gf = np.tile(cl.loc[squadre, "gf"].to_numpy(float), (repliche, 1))
    gs = np.tile(cl.loc[squadre, "gs"].to_numpy(float), (repliche, 1))

    futuro = cal[cal["giornata"] > k]
    for r in futuro.itertuples(index=False):
        ic, it = idx[r.casa], idx[r.trasferta]
        p = np.array([r.p1, r.pX, r.p2], dtype=float)
        p = p / p.sum()
        u = rng.random(repliche)
        classe = (u[:, None] > np.cumsum(p)).sum(axis=1)
        celle = _celle_condizionate(r.lam_casa, r.lam_trasferta)
        for j in range(3):
            m = classe == j
            if not m.any():
                continue
            cc, pp = celle[j]
            scelte = rng.choice(len(pp), size=int(m.sum()), p=pp)
            g_c = cc[scelte, 0].astype(float)
            g_t = cc[scelte, 1].astype(float)
            gf[m, ic] += g_c
            gs[m, ic] += g_t
            gf[m, it] += g_t
            gs[m, it] += g_c
            punti[m, ic] += (3.0 if j == 0 else (1.0 if j == 1 else 0.0))
            punti[m, it] += (0.0 if j == 0 else (1.0 if j == 1 else 3.0))

    return {"squadre": squadre, "punti": punti, "dr": gf - gs, "gf": gf,
            "stagione": stagione, "k": k, "variante": variante,
            "ripiego": int(futuro["ripiego"].sum())}


def _posizioni(sim: dict, rng: np.random.Generator) -> np.ndarray:
    """Posizione di ogni squadra in ogni replica, 1 = prima.

    I pari merito si sciolgono per differenza reti, poi gol fatti, poi
    **estrazione col seme del progetto**: la Serie A userebbe gli scontri
    diretti, e la semplificazione e' dichiarata nella docstring del modulo.
    """
    n_rep, n_team = sim["punti"].shape
    rumore = rng.random((n_rep, n_team))
    chiave = (sim["punti"] * 1e9 + sim["dr"] * 1e5 + sim["gf"] * 1e1 + rumore)
    ordine = np.argsort(-chiave, axis=1)
    pos = np.empty_like(ordine)
    np.put_along_axis(pos, ordine, np.arange(1, n_team + 1)[None, :].repeat(n_rep, 0), axis=1)
    return pos


def pari_merito(sim: dict) -> dict:
    """Quanto spesso lo scioglimento dei pari merito decide una delle tre soglie.

    Serve a dire se la semplificazione sugli scontri diretti conta: si misura,
    non si dichiara trascurabile.
    """
    p = sim["punti"]
    n_team = p.shape[1]
    fuori = {}
    for nome, taglio in (("scudetto", 1), ("europa", POSTI_EUROPA),
                         ("retrocessione", n_team - POSTI_RETROCESSIONE)):
        ordinati = np.sort(p, axis=1)[:, ::-1]
        fuori[nome] = float((ordinati[:, taglio - 1] == ordinati[:, taglio]).mean())
    return fuori


def probabilita(stagione: str, k: int, repliche: int = REPLICHE,
                variante: str = "modello", sim: dict = None,
                seed: int = None) -> pd.DataFrame:
    """Le tre affermazioni di classifica, per squadra, con l'esito vero accanto."""
    sim = simula(stagione, k, repliche, variante, seed=seed) if sim is None else sim
    rng = np.random.default_rng(config.SEED if seed is None else seed)
    pos = _posizioni(sim, rng)
    n_team = len(sim["squadre"])

    finale = classifica_a(stagione, 38)
    vera = {t: i + 1 for i, t in enumerate(finale.index)}

    return pd.DataFrame({
        "squadra": sim["squadre"],
        "punti a k": classifica_a(stagione, k).loc[sim["squadre"], "punti"].to_numpy(),
        "punti attesi": sim["punti"].mean(axis=0),
        "scudetto": (pos == 1).mean(axis=0),
        f"top {POSTI_EUROPA}": (pos <= POSTI_EUROPA).mean(axis=0),
        "retrocessione": (pos > n_team - POSTI_RETROCESSIONE).mean(axis=0),
        "punti finali veri": finale.loc[sim["squadre"], "punti"].to_numpy(),
        "posizione vera": [vera[t] for t in sim["squadre"]],
    }).sort_values("punti attesi", ascending=False).reset_index(drop=True)


# ---------------------------------------------------------------------------
# La validazione: i punti finali, che sono l'unica cosa con abbastanza righe
# ---------------------------------------------------------------------------

def _pit(campione: np.ndarray, y: float, rng: np.random.Generator) -> float:
    """PIT randomizzato per una distribuzione discreta simulata.

    Su conteggi la PIT non randomizzata e' a scalini e rifiuterebbe sempre; e' la
    stessa correzione che `validate` applica dalla Fase 4.
    """
    sotto = float((campione < y).mean())
    uguale = float((campione == y).mean())
    return sotto + rng.random() * uguale


def copertura(stagioni=None, k_list=K_VALUTAZIONE, repliche: int = REPLICHE,
              variante: str = "modello", seed: int = None) -> pd.DataFrame:
    """Copertura e PIT dei **punti finali**, per giornata di partenza.

    **E' la validazione del blocco, ed e' l'unica che i numeri permettono.** Una
    probabilita' di scudetto ha cinque realizzazioni; i punti finali ne hanno
    venti per stagione, cioe' cento per giornata di partenza. Restano correlati
    dentro la stagione — venti squadre si dividono un monte punti quasi fisso — e
    per questo la tabella riporta anche il numero di stagioni e non solo `n`.

    La lettura attesa, se R2-bis ha ragione, e' **sotto-copertura**: intervalli
    troppo stretti perche' la classifica simulata e' troppo corta.
    """
    rng = np.random.default_rng(config.SEED if seed is None else seed)
    stagioni = list(config.SEASONS_STORICHE) if stagioni is None else list(stagioni)

    righe = []
    for k in k_list:
        pit, dentro = [], {50: [], 80: [], 95: []}
        sd_sim, sd_oss, err = [], [], []
        for st in stagioni:
            sim = simula(st, k, repliche, variante, seed=seed)
            finale = classifica_a(st, 38)
            veri = finale.loc[sim["squadre"], "punti"].to_numpy(float)
            for j, y in enumerate(veri):
                camp = sim["punti"][:, j]
                pit.append(_pit(camp, y, rng))
                for liv, lo in ((50, 25), (80, 10), (95, 2.5)):
                    a, b = np.percentile(camp, [lo, 100 - lo])
                    dentro[liv].append(bool(a <= y <= b))
                err.append(camp.mean() - y)
            sd_sim.append(float(sim["punti"].mean(axis=0).std(ddof=1)))
            sd_oss.append(float(veri.std(ddof=1)))
        pit = np.array(pit)
        att, _bordi = np.histogram(pit, bins=10, range=(0, 1))
        atteso = len(pit) / 10
        righe.append({
            "k": k, "stagioni": len(stagioni), "n": len(pit),
            "copertura 50%": float(np.mean(dentro[50])),
            "copertura 80%": float(np.mean(dentro[80])),
            "copertura 95%": float(np.mean(dentro[95])),
            "MAE punti": float(np.abs(err).mean()),
            "bias punti": float(np.mean(err)),
            "sd simulata": float(np.mean(sd_sim)),
            "sd osservata": float(np.mean(sd_oss)),
            "chi2 PIT (9 gdl)": float(((att - atteso) ** 2 / atteso).sum()),
        })
    return pd.DataFrame(righe)


def forma_pit(stagioni=None, k: int = 19, repliche: int = REPLICHE,
              variante: str = "modello", seed: int = None) -> pd.DataFrame:
    """Le dieci frequenze della PIT, perche' un chi2 non dice **come** sbaglia.

    Una PIT a `U` significa intervalli troppo stretti, una a campana intervalli
    troppo larghi, una inclinata un bias. Il chi2 le confonde tutte in un numero,
    e su cento righe correlate quel numero non e' nemmeno un test.
    """
    rng = np.random.default_rng(config.SEED if seed is None else seed)
    stagioni = list(config.SEASONS_STORICHE) if stagioni is None else list(stagioni)
    pit = []
    for st in stagioni:
        sim = simula(st, k, repliche, variante, seed=seed)
        veri = classifica_a(st, 38).loc[sim["squadre"], "punti"].to_numpy(float)
        pit += [_pit(sim["punti"][:, j], y, rng) for j, y in enumerate(veri)]
    att, bordi = np.histogram(pit, bins=10, range=(0, 1))
    return pd.DataFrame({
        "fascia": [f"{bordi[i]:.1f}-{bordi[i+1]:.1f}" for i in range(10)],
        "osservate": att, "attese": len(pit) / 10,
    })


def confronto_appaiato_punti(stagioni=None, k: int = 19,
                             repliche: int = REPLICHE, seed: int = None) -> pd.DataFrame:
    """Modello contro baseline sull'errore nei punti finali, appaiato (vincolo 6).

    **Due `t` e non uno, ed e' il punto della funzione.** L'unita' naturale
    sembra la squadra-stagione (n = 100), ma venti squadre di una stessa stagione
    si dividono un monte punti quasi fisso: i loro errori sono **correlati per
    costruzione**, e un `t` su cento righe cosi' e' ottimista. Il `t` per
    **stagione** (n = 5) e' onesto e quasi cieco. Si riportano entrambi, come R0
    ha insegnato a fare con le realizzazioni di classifica: il primo dice il
    verso, il secondo dice quanto poco si puo' concludere.
    """
    from scipy import stats

    stagioni = list(config.SEASONS_STORICHE) if stagioni is None else list(stagioni)
    err = {}
    for v in VARIANTI:
        per_riga, per_stagione = [], []
        for st in stagioni:
            sim = simula(st, k, repliche, v, seed=seed)
            veri = classifica_a(st, 38).loc[sim["squadre"], "punti"].to_numpy(float)
            e = np.abs(sim["punti"].mean(axis=0) - veri)
            per_riga.append(e)
            per_stagione.append(float(e.mean()))
        err[v] = (np.concatenate(per_riga), np.array(per_stagione))

    m_riga, m_stag = err["modello"]
    righe = []
    for v in VARIANTI[1:]:
        b_riga, b_stag = err[v]
        d1 = m_riga - b_riga
        d2 = m_stag - b_stag
        se1 = d1.std(ddof=1) / np.sqrt(len(d1))
        se2 = d2.std(ddof=1) / np.sqrt(len(d2))
        righe.append({
            "baseline": v,
            "MAE modello": float(m_riga.mean()), "MAE baseline": float(b_riga.mean()),
            "differenza": float(d1.mean()),
            "t (squadra-stagione, n=100)": float(d1.mean() / se1) if se1 else np.nan,
            "t (stagione, n=5)": float(d2.mean() / se2) if se2 else np.nan,
            "p (stagione)": float(stats.ttest_1samp(d2, 0.0).pvalue),
            "modello vince": bool(d1.mean() < 0),
        })
    return pd.DataFrame(righe)


def confronto_varianti(stagioni=None, k: int = 19, repliche: int = REPLICHE,
                       seed: int = None) -> pd.DataFrame:
    """Il modello contro i baseline, sulla stessa giornata e con la stessa
    procedura di simulazione (vincolo 6).

    Il MAE sui punti finali e' la metrica leggibile; la copertura sta accanto
    perche' — come la Fase 4 ha insegnato — un modello puo' vincere sull'accuratezza
    e perdere sulla calibrazione, o il contrario.
    """
    righe = []
    for v in VARIANTI:
        t = copertura(stagioni, (k,), repliche, v, seed=seed).iloc[0].to_dict()
        t["variante"] = v
        righe.append(t)
    out = pd.DataFrame(righe)
    return out[["variante", "k", "n", "MAE punti", "bias punti", "copertura 50%",
                "copertura 80%", "copertura 95%", "sd simulata", "sd osservata"]]


def affidabilita_claim(stagioni=None, k_list=K_VALUTAZIONE,
                       repliche: int = REPLICHE, variante: str = "modello",
                       seed: int = None) -> pd.DataFrame:
    """Le tre affermazioni di classifica contro cio' che e' successo. **Descrittiva.**

    > **Non e' una validazione, ed e' R0 a dirlo.** Uno scudetto ha **una**
    > realizzazione per stagione: le 100 righe di questa tabella sono venti
    > squadre di cinque stagioni, e dentro una stagione lo scudetto e' uno solo —
    > le righe non sono indipendenti nemmeno da lontano. Il Brier accanto al tasso
    > base serve a mostrare che le probabilita' non sono assurde, non a concludere
    > che siano buone. **La validazione del blocco sono i punti finali**
    > (`copertura`), che di realizzazioni ne hanno venti per stagione.
    """
    stagioni = list(config.SEASONS_STORICHE) if stagioni is None else list(stagioni)
    righe = []
    for k in k_list:
        acc = []
        for st in stagioni:
            p = probabilita(st, k, repliche, variante, seed=seed)
            n = len(p)
            p["vero_scudetto"] = (p["posizione vera"] == 1).astype(float)
            p[f"vero_top {POSTI_EUROPA}"] = (p["posizione vera"] <= POSTI_EUROPA).astype(float)
            p["vero_retrocessione"] = (p["posizione vera"] > n - POSTI_RETROCESSIONE).astype(float)
            acc.append(p)
        a = pd.concat(acc, ignore_index=True)
        for nome, base in (("scudetto", 1 / 20), (f"top {POSTI_EUROPA}", POSTI_EUROPA / 20),
                           ("retrocessione", POSTI_RETROCESSIONE / 20)):
            y = a[f"vero_{nome}"].to_numpy()
            p_ = a[nome].to_numpy()
            righe.append({
                "k": k, "affermazione": nome, "n": len(a),
                "media dichiarata": float(p_.mean()),
                "frequenza vera": float(y.mean()),
                "Brier": float(np.mean((p_ - y) ** 2)),
                "Brier tasso base": float(np.mean((base - y) ** 2)),
            })
    return pd.DataFrame(righe)


def dispersione_finale(stagioni=None, k: int = 19, repliche: int = REPLICHE,
                       variante: str = "modello", seed: int = None) -> pd.DataFrame:
    """La sotto-dispersione di R2-bis, riletta sui **punti finali simulati**.

    R2-bis l'aveva misurata sulle probabilita' di partita; qui si guarda cio' che
    R3 pubblica davvero — la classifica — e la domanda e' se la simulazione
    produca squadre distanti quanto lo sono.
    """
    stagioni = list(config.SEASONS_STORICHE) if stagioni is None else list(stagioni)
    righe = []
    for st in stagioni:
        sim = simula(st, k, repliche, variante, seed=seed)
        finale = classifica_a(st, 38)
        veri = finale.loc[sim["squadre"], "punti"].to_numpy(float)
        atteso = sim["punti"].mean(axis=0)
        righe.append({
            "stagione": st,
            "sd punti veri": float(veri.std(ddof=1)),
            "sd punti attesi": float(atteso.std(ddof=1)),
            "sd dentro una squadra": float(sim["punti"].std(axis=0, ddof=1).mean()),
            "primo vero": float(veri.max()), "primo atteso": float(atteso.max()),
            "ultimo vero": float(veri.min()), "ultimo atteso": float(atteso.min()),
        })
    out = pd.DataFrame(righe)
    out["rapporto sd"] = out["sd punti veri"] / out["sd punti attesi"]
    return out
