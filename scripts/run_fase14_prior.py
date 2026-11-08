# -*- coding: utf-8 -*-
"""Fase 14 / A2 — il prior dalla stagione precedente, misurato.

Il blocco introduce **modellazione**, quindi non si pubblica finche' non e'
misurato contro i baseline che contano. Il disegno e' dichiarato in
`sot/prior_stagione.py` PRIMA dei numeri, e `verdetto()` applica
`CRITERIO_ADOZIONE` meccanicamente invece di lasciarlo rileggere a occhio.

Costa ~5 minuti alla prima esecuzione (5 campionati x 4 transizioni x 9 punti di
griglia x 2 bersagli), pochi secondi dalla cache. NON tocca la rete.
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sot import config, prior_stagione as PS  # noqa: E402

CAMPIONATI = tuple(sorted(config.LEAGUE_CODES))
BERSAGLI = ("shots", "sot")
OUT = config.REPORTS


def per_campionato(league: str, target: str, force: bool) -> dict:
    """Una riga per transizione valutata, piu' la tabella di taratura."""
    g = PS.griglia_avvio(league=league, target=target, force=force)
    if not len(g):
        return {"righe": pd.DataFrame(), "tarature": pd.DataFrame(),
                "prev": pd.DataFrame()}

    storiche = list(config.SEASONS_STORICHE)
    transizioni = storiche[1:]                      # 2022-23 ... 2025-26

    righe, tarature, prev = [], [], []
    for s in transizioni:
        # SOLO le transizioni precedenti: tararsi sulla stessa stagione che poi
        # si riporta sarebbe scegliere un iperparametro guardando il bersaglio.
        passate = [t for t in transizioni if t < s]
        scelta = PS.scegli_alpha_prior(g, passate, target=target)
        tarata = scelta["alpha_prior"] is not None
        a = scelta["alpha_prior"]
        if not tarata:
            # senza un passato su cui tararsi la transizione resta MARCATA e
            # fuori dal titolo, come la 2021-2022 non ricalibrata di R2-bis.
            a = float(np.median(PS.ALPHA_PRIOR_GRID))

        d = g[(g["stagione"] == s) & (g["alpha_prior"] == a)]
        if not len(d):
            continue
        prev.append(d)

        val = PS.valutazione(d, avvio=True)
        conf = PS.confronto(d, avvio=True)
        mde = PS.mde_relativo(d, avvio=True)
        rif = conf[conf["riferimento"]]

        righe.append({
            "campionato": league, "stagione": s, "tarata": tarata,
            "alpha_prior": a, "sul_bordo": scelta["sul_bordo"],
            "n": int(val["n"].iloc[0]) if len(val) else 0,
            **{f"ll_{c}": float(val.loc[val["candidato"] == c,
                                        "loglik_per_riga"].iloc[0])
               for c in PS.CANDIDATI if (val["candidato"] == c).any()},
            "delta_vs_media_squadra": (float(rif.iloc[0]["delta_loglik_per_riga"])
                                       if len(rif) else np.nan),
            "t_cluster": float(rif.iloc[0]["t_cluster"]) if len(rif) else np.nan,
            "delta_su_mde": mde.get("delta_su_mde", np.nan),
        })
        tarature.append(scelta["tabella"].assign(campionato=league, stagione=s))

    return {"righe": pd.DataFrame(righe),
            "tarature": pd.concat(tarature, ignore_index=True) if tarature
            else pd.DataFrame(),
            "prev": pd.concat(prev, ignore_index=True) if prev else pd.DataFrame()}


def poola(prev_per_campionato: list, target: str, avvio: bool) -> dict:
    """Il confronto su tutti i campionati insieme.

    **Non e' un modello poolato** — i cinque fit restano cinque, ed e' la regola
    di E1. E' un confronto poolato: le previsioni sono gia' state fatte da fit
    separati, e qui si sommano solo le loro log-verosimiglianze. La differenza
    conta: poolare i *fit* attribuirebbe il contesto ai coefficienti di squadra,
    poolare le *valutazioni* aumenta solo il numero di realizzazioni.
    """
    if not prev_per_campionato:
        return {}
    d = pd.concat(prev_per_campionato, ignore_index=True)
    # il cluster e' la partita, e una partita e' identificata dalla coppia
    # (campionato, matchId): appoggiarsi al solo matchId sarebbe fidarsi che sia
    # unico fra campionati, che nessuno ha verificato
    d = d.assign(matchId=d["campionato"].astype(str) + ":" + d["matchId"].astype(str))
    d = PS.con_due_regimi(d)
    return {"valutazione": PS.valutazione(d, avvio=avvio),
            "confronto": PS.confronto(d, avvio=avvio),
            "confronto_prec": PS.confronto(d, avvio=avvio,
                                           soggetto="modello prec"),
            "mde": PS.mde_relativo(d, avvio=avvio),
            "mde_prec": PS.mde_relativo(d, avvio=avvio, soggetto="modello prec"),
            "per_indice": PS.per_indice(d),
            "n_righe": len(PS._righe_confrontabili(d, avvio=avvio))}


def tabella_md(df: pd.DataFrame, cifre: int = 4) -> str:
    if not len(df):
        return "_(nessuna riga)_"
    d = df.copy()
    for c in d.columns:
        if pd.api.types.is_float_dtype(d[c]):
            d[c] = d[c].map(lambda x: "" if pd.isna(x) else f"{x:.{cifre}f}")
    testa = "| " + " | ".join(str(c) for c in d.columns) + " |"
    sep = "|" + "|".join("---" for _ in d.columns) + "|"
    corpo = ["| " + " | ".join(str(v) for v in r) + " |"
             for r in d.itertuples(index=False)]
    return "\n".join([testa, sep, *corpo])


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--force", action="store_true",
                   help="ricalcola la griglia invece di leggerla dalla cache")
    p.add_argument("--league", nargs="+", choices=sorted(config.LEAGUE_CODES),
                   default=list(CAMPIONATI))
    args = p.parse_args(argv)
    t0 = time.time()

    sezioni = []
    esiti = {}
    for target in BERSAGLI:
        print(f"=== bersaglio {target} ===")
        righe, tarature, prev_tarate = [], [], []
        for L in args.league:
            print(f"  {L}...")
            r = per_campionato(L, target, args.force)
            if not len(r["righe"]):
                continue
            righe.append(r["righe"])
            tarature.append(r["tarature"])
            tarate = r["righe"][r["righe"]["tarata"]]["stagione"].tolist()
            prev_tarate.append(r["prev"][r["prev"]["stagione"].isin(tarate)])

        if not righe:
            continue
        tab = pd.concat(righe, ignore_index=True)
        pool_avvio = poola(prev_tarate, target, avvio=True)
        pool_ctrl = poola(prev_tarate, target, avvio=False)

        # il segno per campionato: 3 su 5 e' la seconda meta' del criterio
        segni = (tab[tab["tarata"]].groupby("campionato")["delta_vs_media_squadra"]
                 .mean())
        v = PS.verdetto(pool_avvio.get("confronto", pd.DataFrame()), segni)
        esiti[target] = {"tab": tab, "pool": pool_avvio, "ctrl": pool_ctrl,
                         "segni": segni, "verdetto": v,
                         "tarature": pd.concat(tarature, ignore_index=True)}

        print(f"    -> {v['perche']}")

    # ---------------- report ----------------
    testo = ["# Fase 14 / A2 — il prior dalla stagione precedente", "",
             f"_Generato da `scripts/run_fase14_prior.py` — "
             f"{time.strftime('%Y-%m-%d %H:%M')}_", "",
             "## Il criterio, scritto prima dei numeri", "",
             "```", PS.CRITERIO_ADOZIONE, "```", "",
             f"Righe di avvio: `team_match_idx <= {PS.IDX_AVVIO}`. "
             f"Controllo: da {PS.IDX_AVVIO + 1} a {PS.IDX_CONTROLLO}.", "",
             "I cinque candidati: " + " · ".join(f"`{c}`" for c in PS.CANDIDATI)
             + ".", "",
             "La riga `due regimi` non e' un sesto modello: e' la composizione "
             "di due candidati gia' dichiarati a una soglia dichiarata **altrove** "
             "(`config.BURN_IN_ROUND`, Fase 2). Regola: " + PS.REGOLA_DUE_REGIMI,
             ""]

    from sot import predictor_power as PP
    soglia = PP.soglia_sidak(k=len(PS.CANDIDATI))

    for target, e in esiti.items():
        v = e["verdetto"]
        m, mp = e["pool"]["mde"], e["pool"]["mde_prec"]
        testo += [f"## Bersaglio `{target}`", "",
                  f"**Il criterio scritto prima: "
                  f"{'ADOTTATO' if v['adotta'] else 'NON adottato'}** "
                  f"— {v['perche']}", "",
                  "### Poolato sulle transizioni tarate — righe di avvio", "",
                  tabella_md(e["pool"].get("valutazione", pd.DataFrame())), "",
                  "#### `con prior` contro gli altri", "",
                  tabella_md(e["pool"].get("confronto", pd.DataFrame())), "",
                  f"MDE contro il riferimento: delta {m.get('delta', float('nan')):.4f}, "
                  f"MDE {m.get('mde', float('nan')):.4f}, "
                  f"**delta/MDE {m.get('delta_su_mde', float('nan')):.2f}** "
                  f"su {m.get('n_cluster', 0)} partite.", "",
                  "> Sotto 1 in valore assoluto il test **non conclude**: e' "
                  "diverso da dire che l'effetto non c'e' (lezione di 6D, unita' "
                  "di V3).", "",
                  "#### `modello prec` contro gli altri", "",
                  "_L'anno scorso applicato tale e quale, senza guardare una "
                  "sola partita nuova. Era il **diagnostico** del blocco, non il "
                  "candidato da adottare._", "",
                  tabella_md(e["pool"].get("confronto_prec", pd.DataFrame())), "",
                  f"MDE: delta {mp.get('delta', float('nan')):.4f}, "
                  f"MDE {mp.get('mde', float('nan')):.4f}, "
                  f"**delta/MDE {mp.get('delta_su_mde', float('nan')):.2f}**.", "",
                  f"Soglia di Sidak su {len(PS.CANDIDATI)} candidati dichiarati: "
                  f"|t| > {soglia:.2f}.", "",
                  "### Controllo — righe gia' coperte dal within-season", "",
                  tabella_md(e["ctrl"].get("valutazione", pd.DataFrame())), "",
                  "#### `con prior` contro gli altri, sul controllo", "",
                  tabella_md(e["ctrl"].get("confronto", pd.DataFrame())), "",
                  "### Dove i due regimi si scambiano", "",
                  "_Descrizione, non scelta: dice se la soglia gia' dichiarata "
                  "dal repository cade dove i dati la metterebbero._", "",
                  tabella_md(e["pool"].get("per_indice", pd.DataFrame())), "",
                  "### Per campionato e transizione", "",
                  tabella_md(e["tab"]), "",
                  "### Segno del margine per campionato", "",
                  tabella_md(e["segni"].reset_index()), ""]

    (OUT / "fase14_prior.md").write_text("\n".join(testo), encoding="utf-8")
    for target, e in esiti.items():
        e["tab"].to_csv(OUT / f"fase14_prior_{target}.csv", index=False)
        e["tarature"].to_csv(OUT / f"fase14_prior_taratura_{target}.csv",
                             index=False)

    print("")
    print(f"-> {OUT / 'fase14_prior.md'}")
    print(f"Fatto in {time.time() - t0:.0f} s.")
    return esiti


if __name__ == "__main__":
    main()
