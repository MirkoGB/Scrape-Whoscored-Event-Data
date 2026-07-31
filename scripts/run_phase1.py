"""Fase 1 — costruisce le tabelle squadra-partita e giocatore-partita.

    python scripts/run_phase1.py [--force]

Scrive in data/processed/ i Parquet usati da tutte le fasi successive e in
reports/phase1_audit.md il resoconto dell'audit e del controllo di sanita'.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sot import aggregate, config, io_events, minutes as minutes_mod, xg as xg_mod  # noqa: E402


def _pct(a: float, b: float) -> str:
    return f"{(a - b) / b * 100:+.2f}%"


def main(force: bool = False) -> None:
    print("Fase 1 — aggregazione")
    events = io_events.load_events(force=force)
    lineup = io_events.load_lineup_events()
    print(f"  eventi: {len(events):,} | partite: {events['matchId'].nunique()}")

    out = aggregate.run(force=force)
    team, player, shots = out["team_match"], out["player_match"], out["shots"]
    mins = minutes_mod.minutes_played(lineup, events)
    dur = minutes_mod.match_duration(events)

    checks = [
        ("media di campionato", team["sot"].mean(), config.REF_LEAGUE_MEAN),
        ("media in casa", team.loc[team.is_home == 1, "sot"].mean(), config.REF_HOME_MEAN),
        ("media in trasferta", team.loc[team.is_home == 0, "sot"].mean(), config.REF_AWAY_MEAN),
        ("media del Como", team.loc[team.team == "Como", "sot"].mean(), config.REF_COMO_MEAN),
        ("partite", float(team["matchId"].nunique()), float(config.REF_N_MATCHES)),
    ]

    lines = ["# Fase 1 — audit e aggregazione", "",
             f"Eventi letti: {len(events):,} da {events['matchId'].nunique()} partite.", "",
             "## Controllo di sanita'", "",
             "| Voce | Riferimento | Ottenuto | Scarto |", "|---|---|---|---|"]
    ok = True
    for name, got, ref in checks:
        rel = abs(got - ref) / ref
        ok &= rel < config.SANITY_TOLERANCE
        lines.append(f"| {name} | {ref} | {got:.3f} | {_pct(got, ref)} |")
    lines += ["", f"Esito: {'**superato**' if ok else '**NON superato**'} "
                  f"(soglia {config.SANITY_TOLERANCE:.0%}).", ""]

    chk = minutes_mod.check_minutes(mins, lineup, dur)
    n_exact = int((chk["diff"].abs() < 1e-9).sum())
    xg_stats = xg_mod.evaluate(shots, shots["xg"])

    lines += [
        "## Ricostruzione dei minuti", "",
        f"Squadra-partita riconciliate esattamente: **{n_exact}/{len(chk)}**.",
        f"Minuti totali: {mins['minutes'].sum():,.0f}. "
        f"Giocatori con almeno un minuto: {(mins.groupby('playerId')['minutes'].sum() > 0).sum()}.",
        "",
        "## xG interno", "",
        f"- tiri {xg_stats['n_shots']:,}, gol {xg_stats['n_goals']}",
        f"- somma xG {xg_stats['xg_sum']:.1f} contro {xg_stats['goals']} gol",
        f"- log-loss {xg_stats['logloss_model']:.4f} contro {xg_stats['logloss_base']:.4f} del tasso base",
        f"- AUC {xg_stats['auc']:.3f}",
        "",
        "Non e' xG di un fornitore: e' stimato in casa, cross-fitted a "
        f"{xg_mod.N_FOLDS} fold raggruppati per partita.",
        "",
        "## Tabelle prodotte", "",
        f"- `{config.TEAM_MATCH.name}` — {len(team)} righe, {team.shape[1]} colonne",
        f"- `{config.PLAYER_MATCH.name}` — {len(player)} righe, {player.shape[1]} colonne",
        f"- `{config.SHOTS_PARQUET.name}` — {len(shots)} tiri",
    ]

    path = config.REPORTS / "phase1_audit.md"
    path.write_text("\n".join(lines), encoding="utf-8")

    for name, got, ref in checks:
        print(f"  {name:22s} {got:8.3f}  (rif {ref})  {_pct(got, ref)}")
    print(f"  minuti riconciliati: {n_exact}/{len(chk)}")
    print(f"  report -> {path}")
    if not ok:
        raise SystemExit("controllo di sanita' NON superato")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true", help="rilegge i CSV grezzi")
    main(**vars(ap.parse_args()))
