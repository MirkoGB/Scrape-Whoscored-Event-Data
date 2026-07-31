# -*- coding: utf-8 -*-
"""Fase 3 — proiezione 2026-27 dal basso, Monte Carlo, verifica del metodo.

    python scripts/run_phase3.py

Scrive reports/phase3_projection.md e i CSV della scomposizione per giocatore.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sot import (aggregate, config, dispersion as D, model_player as MP,  # noqa: E402
                 project_2627 as P, squad_2627 as SQ)


def main() -> None:
    print("Fase 3 — proiezione 2026-27")
    pm = aggregate.load_player_match()
    tm = aggregate.load_team_match()

    wf_path = config.PROCESSED / "walkforward_base.parquet"
    if not wf_path.exists():
        raise SystemExit("manca walkforward_base.parquet: esegui prima run_phase2.py")
    wfd = pd.read_parquet(wf_path)
    r = D.fit_r(wfd["sot"].to_numpy(), wfd["lam"].to_numpy())

    d = MP.with_context(pm, tm)
    tau_sel = MP.select_tau(d)          # griglia unica, in MP.TAU_GRID
    tau = float(tau_sel.iloc[0]["tau"])

    proj, s, model, du = P.build_projection(pm, tm, tau=tau)
    sim = P.monte_carlo(proj, s, model, r, n_sim=20000)
    vd = P.variance_decomposition(proj, s, model, r, n_sim=20000)
    ht = P.first_half_test(pm, tm, tau=tau)

    q = np.percentile(sim, [10, 50, 90])
    # ATTENZIONE (Fase 6B): la colonna testata qui e' l'ESTIMATORE A, quello
    # che fissa il livello dai giocatori. Non e' quello che la proiezione
    # pubblica, che e' il compositivo — testato in `run_phase6b.py`.
    BU = "livello_dai_giocatori"
    mae_td = ht["err_topdown"].abs().mean()
    mae_bu = ht[f"err_{BU}"].abs().mean()
    diff = ht["err_topdown"].abs() - ht[f"err_{BU}"].abs()
    t_stat = diff.mean() / (diff.std(ddof=1) / np.sqrt(len(diff)))
    slope = float(np.polyfit(ht["topdown"], ht[BU], 1)[0])
    corr_shrink = float(np.corrcoef(ht["topdown"],
                                    ht[f"err_{BU}"] - ht["err_topdown"])[0, 1])

    proj.to_csv(config.REPORTS / "phase3_player_breakdown.csv", index=False)
    ht.to_csv(config.REPORTS / "phase3_halfseason_test.csv", index=False)

    new = proj[proj["is_new"]]
    L = [
        "# Fase 3 — proiezione Como 2026-27 dal basso", "",
        "## Esito in breve", "",
        f"- rapporto compositivo (ricambio di rosa + minuti): **{s['ratio']:.4f}** "
        f"({(s['ratio'] - 1) * 100:+.1f}%)",
        f"- proiezione: **{q[1] / SQ.N_MATCHES:.2f}** tiri in porta a partita, "
        f"**{q[1]:.0f}** in stagione (mediana)",
        f"- intervallo 80%: **[{q[0]:.0f}, {q[2]:.0f}]**",
        f"- riferimento dall'alto: {config.REF_TOPDOWN_PER_MATCH} a partita, "
        f"{config.REF_TOPDOWN_SEASON} in stagione, IC80% {list(config.REF_TOPDOWN_PI80)}",
        "",
        "La media simulata e' " + f"{sim.mean():.1f}" + ", superiore alla mediana: "
        "gli shock moltiplicativi sono lognormali e la media ne risente per "
        "convessita'. La mediana e' la sintesi da leggere.",
        "",
        "## Il metodo dal basso aggiunge informazione?", "",
        "Test: stima su 19 partite per squadra, previsione delle 19 successive.",
        "",
        f"| metodo | MAE | correlazione |", "|---|---|---|",
        f"| dall'alto (tasso di squadra) | **{mae_td:.4f}** | "
        f"{np.corrcoef(ht['topdown'], ht['actual_h2'])[0, 1]:.4f} |",
        f"| dal basso, livello dai giocatori | {mae_bu:.4f} | "
        f"{np.corrcoef(ht[BU], ht['actual_h2'])[0, 1]:.4f} |",
        "",
        f"Differenza appaiata: {diff.mean():+.4f} (t = {t_stat:.2f}). "
        "**Il metodo dal basso non batte quello dall'alto**; il segno gli e' contrario.",
        "",
        "**Quale dei due estimatori e' questo** (chiarito in Fase 6B): quello "
        "che fissa il **livello** dai giocatori. La proiezione pubblicata usa "
        "l'altro, il compositivo, che prende il livello dall'alto e applica "
        "solo il rapporto di rosa: quello e' testato in "
        "`reports/phase6_compositivo.md`, e il test non ha la potenza per "
        "dire niente su di lui.",
        "",
        "### Perche': doppia compressione", "",
        f"- pendenza della regressione dal-basso su dall-alto: **{slope:.3f}** "
        "(1.0 = nessuna compressione aggiuntiva)",
        f"- correlazione fra livello della squadra e compressione aggiuntiva: **{corr_shrink:.3f}**",
        f"- squadre sopra 4.5: MAE dall'alto {ht[ht.topdown > 4.5]['err_topdown'].abs().mean():.3f} "
        f"contro {ht[ht.topdown > 4.5][f'err_{BU}'].abs().mean():.3f} dal basso",
        f"- squadre sotto 4.5: {ht[ht.topdown <= 4.5]['err_topdown'].abs().mean():.3f} "
        f"contro {ht[ht.topdown <= 4.5][f'err_{BU}'].abs().mean():.3f}",
        "",
        "Lo shrinkage per giocatore verso la media di ruolo si somma a quello "
        "gia' applicato dalla ridge di squadra. L'effetto colpisce solo le "
        "squadre di vertice, cioe' proprio quelle su cui il ritorno alla media "
        "e' gia' sospetto di essere troppo conservativo.",
        "",
        "## Scomposizione della varianza", "",
        vd.round(3).to_markdown(index=False),
        "",
        f"Riferimento dall'alto: shock di squadra 65%, campionamento 29%, "
        f"livello di campionato 6%, coefficienti 0.4%.",
        "",
        "**Lo shock di squadra non e' stato ridotto.** La sua varianza assoluta "
        f"({vd.loc[vd.fonte == 'team_shock', 'varianza'].iloc[0]:.0f}) e' quella "
        "ereditata dal modello dall'alto: la quota scende dal 65% al "
        f"{vd.loc[vd.fonte == 'team_shock', 'quota'].iloc[0] * 100:.0f}% solo perche' "
        "il totale e' cresciuto, non perche' il numeratore sia calato. Il metodo "
        "per giocatore **aggiunge** incertezza su minuti e tassi individuali al "
        "posto dello 0.4% dei coefficienti.",
        "",
        "## Limiti dichiarati", "",
        f"- **Rosa provvisoria**: mercato aperto fino al 1 settembre 2026.",
        f"- **{len(new)} nuovi arrivi senza alcun dato**: {new['minutes_proj'].sum():.0f} "
        f"minuti proiettati su {proj['minutes_proj'].sum():.0f} "
        f"({new['minutes_proj'].sum() / proj['minutes_proj'].sum() * 100:.0f}%) e "
        f"{new['contributo'].sum() / proj['contributo'].sum() * 100:.0f}% del lambda "
        "poggiano sulla sola media di ruolo.",
        "- **Rotazione Champions**: assunzione non stimabile da dati in cui il Como "
        "non giocava le coppe. Fatta variare fra "
        f"{SQ.ROTATION_RANGE[0]:.0%} e {SQ.ROTATION_RANGE[1]:.0%} nel Monte Carlo.",
        f"- **Una sola stagione**: tau = {tau} scelto per validazione incrociata "
        "interna alla stagione, non su un orizzonte annuale.",
        "",
        "## Scomposizione per giocatore", "",
        proj[["name", "role", "is_new", "minutes_2526", "minutes_proj",
              "sot_per90_neutro", "se_v", "contributo"]].round(3).to_markdown(index=False),
    ]

    path = config.REPORTS / "phase3_projection.md"
    path.write_text("\n".join(L), encoding="utf-8")

    print(f"  tau = {tau} | r = {r:.1f}")
    print(f"  rapporto compositivo = {s['ratio']:.4f}")
    print(f"  proiezione: {q[1] / SQ.N_MATCHES:.2f}/partita, {q[1]:.0f} stagione, "
          f"IC80% [{q[0]:.0f}, {q[2]:.0f}]")
    print(f"  test 1o/2o tempo: MAE dall'alto {mae_td:.4f} vs dal basso {mae_bu:.4f} "
          f"(t={t_stat:.2f})")
    print(f"  report -> {path}")


if __name__ == "__main__":
    main()
