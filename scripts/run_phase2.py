"""Fase 2 — modello within-season, selezione dei predittori, sovradispersione.

    python scripts/run_phase2.py

Tutto e' walk-forward: parametri, scelta di alpha e medie mobili dei
predittori usano solo partite antecedenti. Scrive reports/phase2_model.md e
data/processed/walkforward_base.parquet.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import brentq

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sot import (aggregate, config, dispersion as D, model_team as MT,  # noqa: E402
                 predictor_power as PP, validate as V, walkforward as wf)

# Soglia sul t appaiato per tenere un predittore. Dichiarata in anticipo qui in
# Fase 2 e da allora **una sola**, in `predictor_power`: la Fase 6D rifa' lo
# stesso test in un altro regime e due copie che divergono renderebbero i due
# esiti non confrontabili.
T_KEEP = PP.T_KEEP


def _paired(a: np.ndarray, b: np.ndarray) -> tuple[float, float]:
    d = a - b
    se = d.std(ddof=1) / np.sqrt(len(d))
    return float(d.sum()), float(d.mean() / se)


def main() -> None:
    print("Fase 2 — modello within-season")
    df = wf.build_predictors(aggregate.load_team_match())

    base = V.walkforward_predict(df, extra=())
    e0 = base[base.eligible].sort_values(["matchId", "team"]).reset_index(drop=True)
    ll0 = D.nb2_loglik(e0["sot"].to_numpy(), e0["lam"].to_numpy(), D.R_MAX)
    print(f"  base: {len(e0)} righe valutate (burn-in giornata {config.BURN_IN_ROUND})")

    # ---------------------------------------------------- predittori candidati
    rows = []
    for name in wf.CANDIDATES:
        p = V.walkforward_predict(df, extra=(name,))
        ei = p[p.eligible].sort_values(["matchId", "team"]).reset_index(drop=True)
        lli = D.nb2_loglik(ei["sot"].to_numpy(), ei["lam"].to_numpy(), D.R_MAX)
        tot, t = _paired(lli, ll0)

        m_in = MT.TeamModel(alpha=12.0, extra=(name,)).fit(df)
        d_in = df[wf.eligible(df)]
        ins = float(np.sum(D.nb2_loglik(d_in["sot"].to_numpy(),
                                        m_in.predict(d_in), D.R_MAX)))
        rows.append({"predittore": name, "d_oos": tot, "t": t, "ins_ll": ins,
                     "tenuto": t > T_KEEP})
        print(f"  {name:10s} d_oos={tot:+7.2f}  t={t:+5.2f}  "
              f"{'TENUTO' if t > T_KEEP else 'scartato'}")

    cand = pd.DataFrame(rows).sort_values("t", ascending=False)
    m_base_in = MT.TeamModel(alpha=12.0).fit(df)
    d_in = df[wf.eligible(df)]
    ins_base = float(np.sum(D.nb2_loglik(d_in["sot"].to_numpy(),
                                         m_base_in.predict(d_in), D.R_MAX)))
    cand["d_ins"] = cand["ins_ll"] - ins_base

    kept = tuple(cand.loc[cand["tenuto"], "predittore"])
    final = V.walkforward_predict(df, extra=kept) if kept else base
    ef = final[final.eligible].sort_values(["matchId", "team"]).reset_index(drop=True)

    # --------------------------------------------------------- sovradispersione
    y, lam = ef["sot"].to_numpy(), ef["lam"].to_numpy()
    disp = D.conditional_dispersion(y, lam)
    r = disp["nb2_r"]
    ll = lambda rr: float(np.sum(D.nb2_loglik(y, lam, rr)))
    target = ll(r) - 1.920
    r_lo = float(np.exp(brentq(lambda z: ll(np.exp(z)) - target, np.log(2), np.log(r))))
    try:
        r_hi = float(np.exp(brentq(lambda z: ll(np.exp(z)) - target,
                                   np.log(r), np.log(D.R_MAX * 0.9))))
    except ValueError:
        r_hi = float("inf")

    # ------------------------------------------------------------- baseline
    blw = V.walkforward_baselines(df)
    be = blw[blw.eligible].set_index(["matchId", "team"])
    ei = ef.set_index(["matchId", "team"])

    table = [dict(V.metrics(ei["sot"].to_numpy(), ei["lam"].to_numpy(), r=r),
                  modello="Poisson ridge att/dif/casa")]
    v_m = D.nb2_loglik(ei["sot"].to_numpy(), ei["lam"].to_numpy(), r)
    paired = {}
    for name in be.columns.drop(["date", "team_match_idx", "sot", "eligible"],
                                errors="ignore"):
        lam_b = be.loc[ei.index, name].to_numpy()
        table.append(dict(V.metrics(ei["sot"].to_numpy(), lam_b, r=r), modello=name))
        paired[name] = _paired(v_m, D.nb2_loglik(ei["sot"].to_numpy(), lam_b, r))
    tab = pd.DataFrame(table).set_index("modello")

    rel = V.reliability_table((ei["sot"].to_numpy() > config.OVER_LINE).astype(float),
                              D.p_over(ei["lam"].to_numpy(), config.OVER_LINE, r))

    ef.to_parquet(config.PROCESSED / "walkforward_base.parquet", index=False)
    # CSV per la Fase 5: le figure non devono ricalcolare cinque minuti di
    # walk-forward, ne' rileggere i numeri da un markdown.
    cand.to_csv(config.REPORTS / "phase2_predittori.csv", index=False)
    tab.to_csv(config.REPORTS / "phase2_metriche.csv")

    # ------------------------------------------------------------------ report
    L = ["# Fase 2 — modello within-season", "",
         f"Righe valutate: **{len(ef)}** su 760 (burn-in: dalla "
         f"{config.BURN_IN_ROUND}a partita di ciascuna squadra).",
         "Tutto walk-forward: parametri, alpha e medie mobili usano solo il passato.",
         "", "## Predittori candidati", "",
         "`d_oos` = guadagno di log-verosimiglianza **fuori campione** sul modello base; "
         "`t` = statistica appaiata sullo stesso guadagno; `d_ins` = variazione **in campione**.",
         "", cand[["predittore", "d_oos", "t", "d_ins", "tenuto"]].round(3).to_markdown(index=False),
         "", f"Soglia adottata: t > {T_KEEP}. "
         f"Predittori tenuti: **{', '.join(kept) if kept else 'nessuno'}**.", "",
         "## Sovradispersione condizionata a lambda", "",
         f"- r NB2 = **{r:.1f}**, IC95% profilo [{r_lo:.1f}, "
         f"{r_hi:.1f}" + ("" if np.isfinite(r_hi) else "inf") + "]",
         f"- var/media **grezzo** {disp['raw_var_mean_ratio']:.3f}",
         f"- var/media **condizionato a lambda** "
         f"{disp['implied_var_at_mean'] / disp['mean_lambda']:.3f}",
         f"- dispersione di Pearson {disp['pearson_dispersion']:.3f}",
         "", "## Metriche vs baseline (stesse righe)", "",
         tab[["n", "mae", "bias", "corr", "calib_slope", "calib_se",
              "loglik_poisson", "brier", "brier_base"]].round(4).to_markdown(),
         "", "Test appaiati del modello contro ciascun baseline:", "",
         "\n".join(f"- vs {k}: d = {v[0]:+.2f}, t = {v[1]:.2f}"
                   for k, v in paired.items()),
         "", "## Affidabilita' (Over 4.5, NB2)", "", rel.round(4).to_markdown(index=False), ""]

    path = config.REPORTS / "phase2_model.md"
    path.write_text("\n".join(L), encoding="utf-8")
    print(f"  r NB2 = {r:.1f}  IC95% [{r_lo:.1f}, {r_hi:.1f}]")
    print(f"  report -> {path}")


if __name__ == "__main__":
    main()
