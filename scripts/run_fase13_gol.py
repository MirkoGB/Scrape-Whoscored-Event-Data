# -*- coding: utf-8 -*-
"""Fase 13 / G2 — il modello dei GOL sui campionati acquisiti.

**I campionati NON si poolano**, ed e' la regola di E1 che R0 aveva gia' scritto
in anticipo proprio su G2: poolare sarebbe «l'errore che E1 vieta e che E4 ha
quantificato». Qui si fa **un fit per campionato**, e il confronto fra campionati
e' un confronto fra risultati, mai un unico modello con dentro tutto.

Dentro ogni campionato il walk-forward e' **dentro la stagione**, come E3.1: le
squadre cambiano fra un'annata e l'altra, e un'emivita di 150 giorni attraverso
l'estate darebbe a settembre un training fatto di maggio.

Non stima niente di nuovo: e' `TeamModel(target="gol_fatti")` di E3 applicato a
campionati diversi. Il punto del blocco e' se **trasferisce**.
"""
from __future__ import annotations

import sys, time
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sot import config, difesa as D, predictor_power as PP, validate as V  # noqa: E402

CAMPIONATI = ("ITA-serie-a", "ENG-premier-league", "ESP-la-liga",
              "GER-bundesliga", "FRA-ligue-1")
OUT = Path("reports")


def walkforward(league: str) -> pd.DataFrame:
    """Walk-forward dentro la stagione, poi le stagioni si impilano."""
    stagioni = [s for s in config.SEASONS_STORICHE
                if config.team_match(league=league, season=s).is_file()]
    if not stagioni:
        return pd.DataFrame()
    gsp = D.gol_squadra_partita(stagioni, league=league)
    pezzi = []
    for st in stagioni:
        d = gsp[gsp["stagione"] == st].copy()
        if len(d) < 100:
            continue
        p = V.walkforward_predict(d, target=D.TARGET)
        b = V.walkforward_baselines(d, target=D.TARGET)
        m = p.merge(b.drop(columns=["date", "team_match_idx", D.TARGET, "eligible"]),
                    on=["matchId", "team"], how="inner")
        assert len(m) == len(p), "il join dei baseline ha cambiato le righe"
        m["stagione"] = st
        pezzi.append(m)
    out = pd.concat(pezzi, ignore_index=True)
    out["campionato"] = league
    return out


def main():
    righe, dettagli = [], []
    for L in CAMPIONATI:
        t0 = time.time()
        wf = walkforward(L)
        if wf.empty:
            print(f"{L}: nessuna tabella, saltato"); continue
        e = wf[wf["eligible"]]

        val = D.valutazione_gol(wf)
        conf = D.confronto_appaiato_gol(wf)
        forma = D.forma_predittiva_gol(wf)

        mod = val[val["modello"].str.contains("ridge")].iloc[0]
        # `confronto_appaiato_gol` ordina per delta crescente: la prima riga e'
        # il baseline piu' DIFFICILE da battere, che e' quello contro cui il
        # confronto significa qualcosa (vincolo 6).
        best = conf.iloc[0]

        # --- il `t` per CLUSTER, che e' quello onesto ---
        # La riga e' la squadra-partita, ma l'unita' indipendente e' la PARTITA:
        # le due righe di una partita condividono l'esito, e V0 ha misurato che
        # i due lati sono correlati (-0,349). Un `t` che le tratta come
        # indipendenti conta due volte la stessa informazione.
        # `walkforward_baselines` nomina le colonne con l'ETICHETTA del
        # baseline ("media squadra + campo"), non con uno slug: la colonna si
        # prende dal nome, e si verifica che esista invece di assumerlo.
        col_base = best["baseline"]
        assert col_base in e.columns, (
            f"baseline {col_base!r} non fra le colonne: {list(e.columns)}")
        err_mod = np.abs(e[D.TARGET] - e["lam"])
        err_bas = np.abs(e[D.TARGET] - e[col_base])
        _, t_riga = V.paired_t(err_mod, err_bas)
        _, t_cluster = V.paired_t(err_mod, err_bas, cluster=e["matchId"])

        # MDE: l'effetto minimo che questo confronto avrebbe visto con
        # probabilita' 80%. Senza, "non significativo" e "non c'e' effetto"
        # sono indistinguibili — lezione della 6D.
        d = (err_bas - err_mod).to_numpy()
        se_cluster = abs(d.mean() / t_cluster) if t_cluster else float("nan")
        mde = PP.effetto_minimo(se_cluster)

        righe.append(dict(
            campionato=L, stagioni=wf["stagione"].nunique(),
            n=int(len(e)), partite=int(e["matchId"].nunique()),
            mae=mod["mae"], bias=mod["bias"], corr=mod["corr"],
            pendenza=mod["calib_slope"], z_vs_1=mod["calib_z_vs_1"],
            mae_baseline=best["mae_baseline"], delta=best["delta_mae"],
            t_riga=t_riga, t_cluster=t_cluster,
            mde=mde, delta_su_mde=best["delta_mae"] / mde if mde else float("nan"),
            baseline=best["baseline"],
            pit_p=forma["pit"]["p_value"],
            zeri_oss=forma["quota_zeri_osservata"],
            zeri_att=forma["quota_zeri_attesa"],
        ))
        dettagli.append(val.assign(campionato=L))
        print(f"{L}: {len(e)} righe valutabili [{time.time()-t0:.0f}s]", flush=True)

    r = pd.DataFrame(righe)
    OUT.mkdir(exist_ok=True)
    r.to_csv(OUT / "fase13_gol_campionati.csv", index=False)
    pd.concat(dettagli, ignore_index=True).to_csv(
        OUT / "fase13_gol_dettaglio.csv", index=False)

    print("\n" + "=" * 78)
    print("IL MODELLO DEI GOL, UN FIT PER CAMPIONATO (mai poolati)")
    print("=" * 78)
    print(r.to_string(index=False, float_format=lambda x: f"{x:.4f}"))


if __name__ == "__main__":
    main()
