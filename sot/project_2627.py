# -*- coding: utf-8 -*-
"""Proiezione 2026-27 dal basso, Monte Carlo e scomposizione della varianza.

RICOMPOSIZIONE
--------------
    lambda_squadra = contesto * SUM_p exp(ruolo_p + v_p) * minuti_p / 90

dove il contesto e' `exp(mu + attacco + difesa_media + campo)` del modello di
squadra. La somma e' sui soli giocatori di movimento.

LA CIRCOLARITA' DA EVITARE
--------------------------
Se il contesto 2026-27 viene fissato al valore Como 2025-26, il metodo dal
basso **riproduce meccanicamente** quello dall'alto: il livello e' lo stesso,
cambia solo la ripartizione interna. Il contributo informativo del metodo per
giocatore e' quindi **compositivo** — deriva dal ricambio di rosa e dalla
redistribuzione dei minuti — e va letto come un rapporto, non come un livello:

    rapporto = lambda(rosa 26-27, minuti proiettati) / lambda(rosa 25-26, minuti reali)

Questo rapporto e' l'unica cosa che i dati per giocatore aggiungono davvero.
Applicarlo all'ancora dall'alto (4.90) da' la proiezione finale senza contare
due volte lo stesso livello.

I DUE ESTIMATORI HANNO DUE NOMI (Fase 6B)
-----------------------------------------
Fino alla Fase 5 "dal basso" indicava due cose diverse, e il test di mezza
stagione ne bocciava una mentre la proiezione ne pubblicava l'altra:

* `stima_livello_dai_giocatori` — ESTIMATORE A: il livello lo decidono i
  giocatori. E' quello che il test 1o/2o tempo boccia (MAE 0.482 contro 0.416
  del tasso di squadra), e **non e' quello pubblicato**.
* `stima_compositiva` — ESTIMATORE B: il livello resta dall'alto e i giocatori
  contribuiscono solo il rapporto di rosa. E' quello che la proiezione usa, ed
  e' invariante rispetto al contesto di squadra.

`first_half_test` li valuta entrambi, ciascuno contro il proprio baseline: il
baseline corretto per B non e' il tasso di squadra generico ma "nessun
aggiustamento di rosa", cioe' rapporto identicamente 1.0.

DECOMPOSIZIONE DELLA VARIANZA
-----------------------------
Il riferimento dall'alto e': 65% shock idiosincratico di squadra, 29% rumore
campionario su 38 partite, 6% livello del campionato, 0.4% incertezza sui
coefficienti. I parametri qui sotto sono ricavati da quell'intervallo (80%
[152, 222] su 186) e sono **assunzioni ereditate**, non stime di questi dati:
con una sola stagione lo shock di squadra fra stagioni non e' osservabile.
Se il metodo per giocatore riduca davvero quel 65% e' una domanda empirica a
cui risponde `first_half_test`, non il Monte Carlo.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from . import (config, dispersion as D, model_player as MP, model_team as MT,
               squad_2627 as SQ)

# --- parametri della scomposizione dall'alto, ricavati dal riferimento ---
# 80% PI [152, 222] su 186 -> semiampiezza 35 = 1.2816 SD -> SD stagionale 27.3
TOPDOWN_SEASON_SD = (config.REF_TOPDOWN_PI80[1] - config.REF_TOPDOWN_PI80[0]) / 2 / 1.2816
TEAM_SHOCK_SHARE = 0.65
LEAGUE_SHARE = 0.06

TEAM_SHOCK_SD_LOG = np.sqrt(TEAM_SHOCK_SHARE) * TOPDOWN_SEASON_SD / config.REF_TOPDOWN_SEASON
LEAGUE_SD_LOG = np.sqrt(LEAGUE_SHARE) * TOPDOWN_SEASON_SD / config.REF_TOPDOWN_SEASON


# --------------------------------------------------------------- incertezza v
def player_effect_se(model: MP.PlayerModel, df: pd.DataFrame) -> pd.Series:
    """Errore standard di `v_p`, dall'informazione di Fisher penalizzata.

    H = X' diag(lambda) X + 2*tau*P. La diagonale dell'inversa da' la varianza
    a posteriori approssimata: chi ha giocato poco riceve un errore standard
    grande, ed e' cosi' che l'incertezza sui minuti scarsi si propaga fino alla
    proiezione invece di sparire.
    """
    X, offset = model._design(df)
    lam = np.exp(np.clip(X @ model.beta_ + offset, -25, 25))
    pen = np.zeros(X.shape[1])
    pen[len(MP.ROLES):] = 2.0 * model.tau
    H = X.T @ (X * lam[:, None]) + np.diag(pen)
    cov = np.linalg.pinv(H)
    se = np.sqrt(np.clip(np.diag(cov)[len(MP.ROLES):], 0, None))
    return pd.Series(se, index=model.players_, name="se_v")


# --------------------------------------------------------- i due estimatori
# Sono due cose diverse e finora avevano un nome solo ("dal basso"). La
# proiezione pubblicata usa il secondo; il test di mezza stagione bocciava il
# primo. Da qui in poi hanno due nomi distinti e vanno testati separatamente.
def stima_livello_dai_giocatori(share_per90: np.ndarray, minutes: np.ndarray,
                                context: float,
                                n_partite: float = SQ.N_MATCHES) -> float:
    """ESTIMATORE A — il livello viene dai giocatori.

    lambda di squadra per partita, ricomposto dai contributi dei singoli. Il
    livello e' interamente deciso qui: se lo shrinkage al ruolo comprime i
    tiratori, il livello scende. E' l'estimatore bocciato dal test di mezza
    stagione (MAE 0.482 contro 0.416), e **non e' quello che la proiezione
    pubblica**.
    """
    return float(context * np.sum(share_per90 * minutes / 90.0) / n_partite)


def stima_compositiva(livello_dall_alto: float, lam_rosa_nuova: float,
                      lam_rosa_vecchia: float) -> float:
    """ESTIMATORE B — il livello viene dall'alto, i giocatori danno il rapporto.

    E' l'estimatore **effettivamente in uso** nella proiezione 2026-27: il
    livello resta l'ancora esterna e i dati per giocatore contribuiscono solo
    il rapporto fra la ricomposizione della rosa nuova e quella della vecchia.

    Il contesto di squadra compare a numeratore e a denominatore del rapporto e
    si semplifica (Fase 6A): moltiplicare entrambe le ricomposizioni per una
    costante non cambia il risultato. E' proprio questa invarianza a
    distinguerlo dall'estimatore A, e un test la verifica.
    """
    # L'ordine delle operazioni e' quello di prima (livello x rapporto): cosi'
    # il numero pubblicato resta identico fino all'ultimo bit.
    return float(livello_dall_alto * (lam_rosa_nuova / lam_rosa_vecchia))


def como_context(team_match: pd.DataFrame, alpha: float = 12.0) -> float:
    """Contesto medio del Como 2025-26: exp(mu + att + difesa media + campo)."""
    m = MT.TeamModel(alpha=alpha).fit(team_match)
    como = team_match[team_match["team"] == "Como"]
    return float(np.mean(m.predict(como)))


def build_projection(player_match: pd.DataFrame, team_match: pd.DataFrame,
                     tau: float = 3.0, rotation: float = SQ.ROTATION_DEFAULT):
    """Ritorna (tabella per giocatore, riepilogo)."""
    d = MP.with_context(player_match, team_match)
    du = d[MP.usable(d)].reset_index(drop=True)
    model = MP.PlayerModel(tau=tau).fit(du)
    se = player_effect_se(model, du)

    ctx = como_context(team_match)

    # --- riferimento: stessa ricomposizione sulla rosa e sui minuti 2025-26 ---
    como25 = (du[du["team"] == "Como"]
              .groupby(["playerId", "playerName", "role"], as_index=False)
              .agg(minutes=("minutes", "sum")))
    como25["share_per90"] = model.share_per90(como25)
    lam_2526 = stima_livello_dai_giocatori(como25["share_per90"].to_numpy(),
                                           como25["minutes"].to_numpy(), ctx)

    # --- proiezione 2026-27 ---
    proj = SQ.project_minutes(rotation=rotation)
    proj["playerId"] = proj["playerId"].astype("Int64")
    proj["share_per90"] = model.share_per90(proj)
    proj["se_v"] = proj["playerId"].map(se)
    lam_2627 = stima_livello_dai_giocatori(proj["share_per90"].to_numpy(),
                                           proj["minutes_proj"].to_numpy(), ctx)

    proj["sot_per90_neutro"] = model.rate_per90(proj)
    proj["contributo"] = (ctx * proj["share_per90"]
                          * proj["minutes_proj"] / 90.0 / SQ.N_MATCHES)

    summary = {
        "context_como": ctx,
        "lambda_bottomup_2526": lam_2526,
        "lambda_bottomup_2627": lam_2627,
        "ratio": lam_2627 / lam_2526,
        "observed_2526": float(team_match.loc[team_match["team"] == "Como", "sot"].mean()),
        "tau": tau,
        "rotation": rotation,
    }
    return proj, summary, model, du


# ------------------------------------------------------------------ Monte Carlo
SOURCES = ("player_rates", "new_signings", "minutes", "team_shock",
           "league_level", "sampling")


def monte_carlo(proj: pd.DataFrame, summary: dict, model: MP.PlayerModel,
                r: float, n_sim: int = 20000, sources=SOURCES,
                seed: int = config.SEED,
                livello_dall_alto: float | None = None,
                sd_nuovi: float | np.ndarray | None = None) -> np.ndarray:
    """Simula il totale stagionale di tiri in porta del Como 2026-27.

    `sources` permette di accendere una fonte alla volta per la scomposizione.

    `livello_dall_alto` e' l'ancora del livello: `None` significa il
    riferimento fornito (`config.REF_TOPDOWN_PER_MATCH`), cioe' il
    comportamento pubblicato, che non cambia. Il parametro esiste per l'analisi
    di sensibilita' della Fase 6C, dove il livello viene fatto variare con la
    persistenza `rho` fra stagioni: e' l'unico ingresso da cui si puo' spostare
    la proiezione, come stabilito in Fase 6A.

    `sd_nuovi` e' la deviazione standard del prior dei nuovi arrivi — scalare o
    un valore per giocatore. `None` significa il comportamento pubblicato
    (`1.5 x` la dispersione fra giocatori, prior gonfiato perche' del loro
    campionato di provenienza non abbiamo niente). Il parametro esiste per la
    Fase 6F, che simula **di quanto si stringerebbe l'intervallo** se quei dati
    ci fossero: e' una domanda del piano dati, non una modifica della
    proiezione. L'ordine delle estrazioni non cambia, quindi con `None` il
    risultato e' identico bit per bit a quello pubblicato.
    """
    rng = np.random.default_rng(seed)
    n = len(proj)

    role = pd.Series(model.role_effects)
    role_v = proj["role"].map(role).to_numpy()
    v_hat = np.log(np.clip(proj["share_per90"].to_numpy(), 1e-12, None)) - role_v
    se_v = proj["se_v"].to_numpy(dtype=float)
    is_new = proj["is_new"].to_numpy()

    # Dispersione fra giocatori dello stesso ruolo: prior dei nuovi arrivi,
    # gonfiata perche' non abbiamo dati del loro campionato di provenienza.
    eff = model.player_effects()["v"].to_numpy()
    sd_new = 1.5 * float(np.std(eff[np.abs(eff) > 1e-9]))
    if sd_nuovi is not None:
        sd_new = np.asarray(sd_nuovi, dtype=float)

    base_min = proj["minutes_proj"].to_numpy()
    ctx = summary["context_como"]
    livello = (config.REF_TOPDOWN_PER_MATCH if livello_dall_alto is None
               else float(livello_dall_alto))
    anchor = stima_compositiva(livello, summary["lambda_bottomup_2627"],
                               summary["lambda_bottomup_2526"])

    V = np.tile(v_hat, (n_sim, 1))
    if "player_rates" in sources:
        s = np.where(is_new, 0.0, np.nan_to_num(se_v, nan=0.0))
        V = V + rng.normal(0.0, 1.0, (n_sim, n)) * s
    if "new_signings" in sources:
        V = V + rng.normal(0.0, 1.0, (n_sim, n)) * np.where(is_new, sd_new, 0.0)

    if "minutes" in sources:
        # Dirichlet attorno alle quote proiettate + rotazione incerta.
        conc = 60.0
        shares = rng.dirichlet(np.clip(base_min / base_min.sum() * conc, 1e-3, None),
                               size=n_sim)
        rot = rng.uniform(*SQ.ROTATION_RANGE, size=(n_sim, 1))
        unif = 1.0 / n
        shares = (1 - rot) * shares + rot * unif
        M = shares / shares.sum(axis=1, keepdims=True) * base_min.sum()
    else:
        M = np.tile(base_min, (n_sim, 1))

    lam = ctx * np.sum(np.exp(role_v + V) * M / 90.0, axis=1) / SQ.N_MATCHES
    # Si riporta il livello sull'ancora dall'alto: il metodo dal basso
    # contribuisce il rapporto compositivo, non il livello.
    lam = lam / summary["lambda_bottomup_2627"] * anchor

    if "team_shock" in sources:
        lam = lam * np.exp(rng.normal(0.0, TEAM_SHOCK_SD_LOG, n_sim))
    if "league_level" in sources:
        lam = lam * np.exp(rng.normal(0.0, LEAGUE_SD_LOG, n_sim))

    season = lam * SQ.N_MATCHES
    if "sampling" in sources:
        p = r / (r + lam)
        season = rng.negative_binomial(r * SQ.N_MATCHES,
                                       np.clip(p, 1e-6, 1 - 1e-6)).astype(float)
    return season


def variance_decomposition(proj, summary, model, r, n_sim=20000) -> pd.DataFrame:
    """Varianza attribuibile a ciascuna fonte, accesa da sola."""
    total = monte_carlo(proj, summary, model, r, n_sim, sources=SOURCES).var()
    rows = []
    for s in SOURCES:
        v = monte_carlo(proj, summary, model, r, n_sim, sources=(s,)).var()
        rows.append({"fonte": s, "varianza": v, "quota": v / total})
    df = pd.DataFrame(rows).sort_values("quota", ascending=False)
    df.loc[len(df)] = {"fonte": "TOTALE (tutte insieme)", "varianza": total, "quota": 1.0}
    return df


# ------------------------------------------------- i due estimatori funzionano?
def _rosa_una_riga(df: pd.DataFrame) -> pd.DataFrame:
    """Una riga per giocatore, con il ruolo in cui ha giocato piu' minuti.

    Serve per il **rapporto** compositivo, che e' il quoziente di due
    ricomposizioni: se i due lati contassero i giocatori con convenzioni
    diverse — uno con una riga per (giocatore, ruolo), l'altro con una riga per
    giocatore — il rapporto conterrebbe anche quella differenza. Scelta
    dichiarata, non silenziosa: l'estimatore A resta invece sulla convenzione
    di prima, per non spostare un numero gia' pubblicato.
    """
    g = df.groupby(["playerId", "role"], as_index=False).agg(minutes=("minutes", "sum"))
    return (g.sort_values("minutes")
             .drop_duplicates("playerId", keep="last")
             .sort_values("playerId")
             .reset_index(drop=True))


def first_half_test(player_match: pd.DataFrame, team_match: pd.DataFrame,
                    split: int = 19, tau: float = 3.0,
                    rotation: float = 0.0) -> pd.DataFrame:
    """I due estimatori battono il tasso di squadra su un orizzonte fuori campione?

    Analogo interno alla stagione del passaggio 2025-26 -> 2026-27: si stima
    tutto sulle prime `split` partite di ogni squadra e si prevede la media di
    tiri in porta delle restanti. Le colonne prodotte:

    * `topdown` — il tasso della squadra nel primo tempo di stagione. E'
      insieme il metodo "dall'alto" e il baseline **corretto per l'estimatore
      compositivo**: rapporto identicamente 1.0 significa "nessun
      aggiustamento di rosa", e da' esattamente questa colonna;
    * `livello_dai_giocatori` — ESTIMATORE A, il livello deciso dai giocatori
      (era la colonna `bottomup`, stesso calcolo);
    * `compositivo` — ESTIMATORE B, `topdown` x `rapporto`, cioe' quello che la
      proiezione pubblica davvero usa;
    * `rapporto` — il rapporto compositivo di ciascuna squadra.

    COSA QUESTO TEST NON PUO' DIRE
    ------------------------------
    Sull'estimatore B il test e' **quasi vuoto per costruzione**. Fra i due
    tempi di una stessa stagione non c'e' un vero ricambio di rosa: la sessione
    di gennaio libera in media una frazione piccola dei minuti, contro il 15%
    che cambia fra un'estate e l'altra. Il rapporto resta quindi vicinissimo a
    1.0 e le due colonne `compositivo` e `topdown` sono quasi la stessa cosa.
    Se il confronto non distingue i due, **non e' una conferma del metodo: e'
    mancanza di potenza**, e va letto insieme all'effetto minimo rilevabile
    riportato dal report di Fase 6B.

    Inoltre, per proiettare i minuti serve sapere **chi** gioca nel secondo
    tempo: si usa la composizione reale della rosa del secondo tempo (chi c'e'
    e in che ruolo), mai i suoi tiri o i suoi minuti. E' l'analogo della
    proiezione vera, dove la rosa 2026-27 e' nota e i minuti sono proiettati —
    ma resta un'informazione che arriva dal periodo bersaglio, quindi
    **favorisce** l'estimatore compositivo. Anche cosi' favorito, va misurato.
    """
    tm1 = team_match[team_match["team_match_idx"] <= split]
    tm2 = team_match[team_match["team_match_idx"] > split]
    pm1 = player_match[player_match["team_match_idx"] <= split]
    pm2 = player_match[player_match["team_match_idx"] > split]

    d = MP.with_context(pm1, tm1)
    du = d[MP.usable(d)].reset_index(drop=True)
    model = MP.PlayerModel(tau=tau).fit(du)

    m1 = MT.TeamModel(alpha=12.0).fit(tm1)
    ctx = pd.Series({t: float(np.mean(m1.predict(tm1[tm1["team"] == t])))
                     for t in sorted(tm1["team"].unique())})

    # Rosa del secondo tempo: solo identita' e ruolo, nessun dato di esito. Il
    # modello dei giocatori resta quello stimato sul primo tempo.
    du2 = pm2[MP.usable(pm2)]

    rows = []
    for team, g in du.groupby("team"):
        # --- ESTIMATORE A, convenzione invariata (una riga per giocatore-ruolo)
        agg = g.groupby(["playerId", "role"], as_index=False).agg(minutes=("minutes", "sum"))
        agg["share_per90"] = model.share_per90(agg)
        liv = stima_livello_dai_giocatori(agg["share_per90"].to_numpy(),
                                          agg["minutes"].to_numpy(),
                                          ctx[team], n_partite=split)

        # --- ESTIMATORE B: le due ricomposizioni del rapporto, stessa convenzione
        r1 = _rosa_una_riga(g)
        r2 = _rosa_una_riga(du2[du2["team"] == team])
        restano = r2["playerId"].isin(r1["playerId"])
        base = (r2["playerId"].map(r1.set_index("playerId")["minutes"])
                .fillna(0.0).to_numpy(dtype=float))
        freed = float(r1.loc[~r1["playerId"].isin(r2["playerId"]), "minutes"].sum())
        quote = SQ.quote_minuti(base, ~restano.to_numpy(), freed, rotation)
        minuti_proj = quote * float(r1["minutes"].sum())

        lam_vecchia = stima_livello_dai_giocatori(
            model.share_per90(r1), r1["minutes"].to_numpy(), ctx[team], split)
        lam_nuova = stima_livello_dai_giocatori(
            model.share_per90(r2), minuti_proj, ctx[team], split)

        topdown = float(tm1.loc[tm1["team"] == team, "sot"].mean())
        rows.append({
            "team": team,
            "topdown": topdown,
            "livello_dai_giocatori": liv,
            "compositivo": stima_compositiva(topdown, lam_nuova, lam_vecchia),
            "rapporto": lam_nuova / lam_vecchia,
            "actual_h2": float(tm2.loc[tm2["team"] == team, "sot"].mean()),
        })
    out = pd.DataFrame(rows)
    for c in ("topdown", "livello_dai_giocatori", "compositivo"):
        out[f"err_{c}"] = out[c] - out["actual_h2"]
    return out


def confronto_stimatori(ht: pd.DataFrame, colonne=None) -> pd.DataFrame:
    """MAE, RMSE, bias e correlazione di ogni colonna di `first_half_test`."""
    colonne = colonne or [c[4:] for c in ht.columns if c.startswith("err_")]
    rows = []
    for c in colonne:
        e = ht[f"err_{c}"]
        rows.append({
            "stimatore": c,
            "MAE": float(e.abs().mean()),
            "RMSE": float(np.sqrt((e ** 2).mean())),
            "bias": float(e.mean()),
            "corr": (float(np.corrcoef(ht[c], ht["actual_h2"])[0, 1])
                     if ht[c].std() > 0 else np.nan),
        })
    return pd.DataFrame(rows)


def effetto_minimo_rilevabile(errori_a: np.ndarray, errori_b: np.ndarray,
                              alpha: float = 0.05,
                              potenza: float = 0.80) -> dict:
    """Differenza di MAE piu' piccola che questo test potrebbe distinguere.

    Senza questo numero un confronto non significativo si legge come conferma,
    che e' l'errore che la Fase 6B esiste per non fare: su 20 squadre e con
    rapporti di rosa tutti vicini a 1.0 il test non ha la potenza per
    distinguere l'estimatore compositivo dal proprio baseline, qualunque sia il
    suo valore vero.

    MDE = (t_{1-alpha/2} + t_{potenza}) * sd(differenze appaiate) / sqrt(n),
    l'approssimazione usuale per il t appaiato.
    """
    from scipy import stats

    d = np.abs(np.asarray(errori_a, dtype=float)) - np.abs(np.asarray(errori_b, dtype=float))
    n = len(d)
    sd = float(d.std(ddof=1))
    mde = (stats.t.ppf(1 - alpha / 2, n - 1) + stats.t.ppf(potenza, n - 1)) * sd / np.sqrt(n)
    return {"n": n, "differenza_osservata": float(d.mean()),
            "sd_differenze": sd, "mde": float(mde),
            "alpha": alpha, "potenza": potenza}
