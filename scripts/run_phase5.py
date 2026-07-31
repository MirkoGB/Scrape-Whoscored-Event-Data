# -*- coding: utf-8 -*-
"""Fase 5 — deliverable: figure e output della proiezione, da zero.

    python scripts/run_phase5.py

Rigenera **tutte** le figure del README e il file di proiezione del Como con
intervalli e scomposizione per giocatore. Nessun numero e' digitato a mano:
ogni valore arriva da `data/processed/` o dai CSV delle fasi precedenti, e le
figure vengono ridisegnate ogni volta.

Prerequisiti: `run_phase1.py` (tabelle), `run_phase2.py` (walk-forward in cache
e `phase2_predittori.csv`). Senza il secondo, il walk-forward viene ricalcolato
e i predittori scartati non possono essere disegnati.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sot import (aggregate, config, dispersion as D, figures as F,  # noqa: E402
                 level_chain as LC, model_player as MP, project_2627 as P,
                 squad_2627 as SQ, validate as V, walkforward as wf)

N_SIM = 20000


def ratings_neutri(team_match: pd.DataFrame, alpha: float = 12.0) -> pd.DataFrame:
    """Tiri in porta attesi contro una difesa media, avversario tenuto fisso.

    `exp(mu + attacco_i + difesa_media)`: niente termine di campo e avversario
    tenuto fisso, cosi' le venti squadre sono confrontabili fra loro. Non e' la
    media grezza — quella dipende da chi hai incontrato.

    **Non e' pero' il campo neutro**, come il nome `neutro` lascerebbe credere:
    `is_home` e' una dummy 0/1, quindi questo e' il valore in **trasferta**.
    La conversione sulle altre due scale sta in `level_chain.ratings_per_campo`,
    che e' l'unica definizione e da' anche le colonne `casa` e
    `media_calendario`. Il nome della colonna resta `neutro` perche' e' un
    numero pubblicato in `fig5` e in `phase5_ratings.csv`: si documenta la
    scala, non si sposta il valore (Fase 6A).
    """
    return LC.ratings_per_campo(team_match, alpha=alpha)


def _salva(fig, nome: str) -> Path:
    path = config.FIGURES / nome
    fig.savefig(path, facecolor=fig.get_facecolor(), bbox_inches="tight")
    import matplotlib.pyplot as plt
    plt.close(fig)
    return path


def main() -> None:
    print("Fase 5 — figure e deliverable")
    tm = aggregate.load_team_match()
    pm = aggregate.load_player_match()
    df = wf.build_predictors(tm)

    B = V.evaluation_bundle(df, config.PROCESSED / "walkforward_base.parquet")
    y, preds, r_wf = B["y"], B["preds"], B["r_wf"]
    tab, cmp_ = B["tab"], B["cmp"]

    prodotte = []

    # ---------------------------------------------------------------- 1 e 2
    calib = tab[["calib_slope", "calib_se", "calib_z_vs_1"]]
    prodotte.append(_salva(
        F.calibrazione_pendenza(calib, V.MODEL_NAME,
                                escludi=("media campionato",)),
        "fig1_calibrazione.png"))

    yb = (y > config.OVER_LINE).astype(float)
    rel = {n: V.reliability_table(yb, D.p_over(preds[n], config.OVER_LINE, r_wf[n]))
           for n in (V.MODEL_NAME, V.BEST_BASELINE)}
    prodotte.append(_salva(
        F.affidabilita(rel[V.MODEL_NAME], rel[V.BEST_BASELINE],
                       V.MODEL_NAME, V.BEST_BASELINE, config.OVER_LINE),
        "fig2_affidabilita.png"))

    # ------------------------------------------------------------------- 3
    cand_path = config.REPORTS / "phase2_predittori.csv"
    if cand_path.exists():
        cand = pd.read_csv(cand_path)
        prodotte.append(_salva(F.predittori_scartati(cand, soglia=2.0),
                               "fig3_predittori.png"))
    else:
        print(f"  ATTENZIONE: manca {cand_path.name}, figura 3 saltata "
              "(esegui run_phase2.py)")

    # ------------------------------------------------------------------- 4
    prodotte.append(_salva(
        F.vantaggio_sui_baseline(cmp_, dict(zip(cmp_["vs"], cmp_["se_mae"]))),
        "fig4_vantaggio.png"))

    # ------------------------------------------------------------------- 5
    rat = ratings_neutri(tm)
    rat.to_csv(config.REPORTS / "phase5_ratings.csv", index=False)
    prodotte.append(_salva(F.ratings_squadra(rat, evidenzia="Como"),
                           "fig5_ratings.png"))

    # --------------------------------------------------------- proiezione Como
    wfd = pd.read_parquet(config.PROCESSED / "walkforward_base.parquet")
    r = D.fit_r(wfd["sot"].to_numpy(), wfd["lam"].to_numpy())
    d_ctx = MP.with_context(pm, tm)
    tau = float(MP.select_tau(d_ctx).iloc[0]["tau"])

    proj, s, model, _ = P.build_projection(pm, tm, tau=tau)
    sim = P.monte_carlo(proj, s, model, r, n_sim=N_SIM)
    vd = P.variance_decomposition(proj, s, model, r, n_sim=N_SIM)
    q10, q50, q90 = np.percentile(sim, [10, 50, 90])

    prodotte.append(_salva(
        F.proiezione_como(sim, q10, q50, q90, config.REF_TOPDOWN_SEASON,
                          config.REF_TOPDOWN_PI80),
        "fig6_proiezione.png"))
    prodotte.append(_salva(F.contributo_giocatori(proj), "fig7_giocatori.png"))

    # ------------------------------------------- deliverable della proiezione
    out = proj[["name", "role", "is_new", "minutes_2526", "sot_2526",
                "minutes_proj", "minutes_per_match", "sot_per90_neutro",
                "se_v", "contributo"]].copy()
    out["quota_lambda"] = out["contributo"] / out["contributo"].sum()
    out = out.sort_values("contributo", ascending=False).reset_index(drop=True)
    out.round(4).to_csv(config.REPORTS / "phase5_proiezione_como_2627.csv",
                        index=False)

    nuovi = out[out["is_new"]]
    L = [
        "# Proiezione Como 2026-27 — output completo", "",
        "Rigenerato da `scripts/run_phase5.py`. Ogni numero viene dai dati; "
        "nessuno e' stato aggiustato a mano.", "",
        "## Il numero, e cosa c'e' dentro", "",
        f"| | per partita | stagione (38) | IC 80% |", "|---|---|---|---|",
        f"| **dal basso** (questo file) | **{q50 / SQ.N_MATCHES:.2f}** | "
        f"**{q50:.0f}** | [{q10:.0f}, {q90:.0f}] |",
        f"| dall'alto (riferimento) | {config.REF_TOPDOWN_PER_MATCH:.2f} | "
        f"{config.REF_TOPDOWN_SEASON} | "
        f"[{config.REF_TOPDOWN_PI80[0]}, {config.REF_TOPDOWN_PI80[1]}] |", "",
        f"Rapporto compositivo (ricambio di rosa + minuti): "
        f"**{s['ratio']:.4f}** ({(s['ratio'] - 1) * 100:+.1f}%). E' l'unica cosa "
        "che i dati per giocatore aggiungono davvero: il **livello** resta "
        "quello dall'alto, per non contarlo due volte.", "",
        f"La media simulata e' {sim.mean():.1f}, sopra la mediana: gli shock "
        "sono lognormali e la media ne risente per convessita'. **La mediana e' "
        "la sintesi da leggere.**", "",
        "## L'intervallo e' piu' largo del riferimento, non piu' stretto", "",
        "Non e' un difetto del calcolo: e' il risultato. Il metodo per "
        "giocatore **sostituisce** lo 0.4% di incertezza sui coefficienti con "
        "l'incertezza su minuti, tassi individuali e nuovi arrivi, e non tocca "
        "lo shock di squadra, che resta la fonte dominante.", "",
        vd.round(3).to_markdown(index=False), "",
        "## Limiti, accanto al numero e non in fondo", "",
        f"- **Rosa provvisoria**: il mercato chiude il 1 settembre 2026.",
        f"- **{len(nuovi)} nuovi arrivi di movimento senza alcun dato**: "
        f"{nuovi['minutes_proj'].sum() / out['minutes_proj'].sum():.0%} dei "
        f"minuti proiettati e {nuovi['quota_lambda'].sum():.0%} del lambda "
        "poggiano sulla sola media di ruolo.",
        f"- **Rotazione Champions** fatta variare fra {SQ.ROTATION_RANGE[0]:.0%} "
        f"e {SQ.ROTATION_RANGE[1]:.0%}: non e' stimabile da una stagione in cui "
        "il Como non giocava le coppe.",
        f"- **Una sola stagione**: tau = {tau:g} scelto per validazione interna "
        "alla stagione, non su un orizzonte annuale.",
        "- **Il metodo dal basso non ha superato la sua verifica** (Fase 3 e "
        "Fase 4): non batte il tasso di squadra. Questo file va letto come "
        "scomposizione di un numero deciso dall'alto, non come una previsione "
        "migliore.", "",
        "## Scomposizione per giocatore", "",
        "`sot_per90_neutro` = tiri in porta per 90 minuti in una squadra di "
        "forza media contro una difesa media: e' la quantita' portabile fra "
        "club. `se_v` e' l'errore standard dell'effetto individuale — grande "
        "dove i minuti sono pochi, ed e' cosi' che l'incertezza si propaga "
        "invece di sparire.", "",
        out.round(3).to_markdown(index=False), "",
    ]
    proj_path = config.REPORTS / "phase5_proiezione_como_2627.md"
    proj_path.write_text("\n".join(L), encoding="utf-8")

    print(f"  ratings a campo neutro: Como {float(rat.loc[rat.team == 'Como', 'neutro'].iloc[0]):.2f}, "
          f"max {rat['neutro'].max():.2f}, min {rat['neutro'].min():.2f}")
    print(f"  proiezione: {q50 / SQ.N_MATCHES:.2f}/partita, {q50:.0f} stagione, "
          f"IC80% [{q10:.0f}, {q90:.0f}]")
    for p in prodotte:
        print(f"  figura -> {p.relative_to(config.ROOT)}")
    print(f"  proiezione -> {proj_path.relative_to(config.ROOT)}")


if __name__ == "__main__":
    main()
