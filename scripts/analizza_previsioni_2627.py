"""Confronta i pronostici salvati con tutti gli esiti locali, senza rifare fit.

Esecuzione: .venv/Scripts/python.exe scripts/analizza_previsioni_2627.py
La data della partita deve essere strettamente successiva alla pubblicazione.
La pagina HTML e i CSV originali vengono soltanto letti.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sot import config, dispersion, validate

OUT = config.REPORTS
PREFIX = "analisi_2627"
N_BOOT = 5000


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def ci_cluster(d, column):
    """Bootstrap per partita, stratificato per campionato: i due lati restano uniti."""
    rng = np.random.default_rng(42)
    draws = np.zeros(N_BOOT)
    count = 0
    for _, g in d.groupby("campionato"):
        clusters = g.groupby("matchId")[column].agg(["sum", "count"])
        assert clusters["count"].eq(2).all()
        x = clusters["sum"].to_numpy()
        draws += x[rng.integers(0, len(x), size=(N_BOOT, len(x)))].sum(axis=1)
        count += len(g)
    return np.quantile(draws / count, [.025, .975])


def metrics(d, scope, league, target):
    err = d[f"errore_{target}"]
    delta = f"delta_crps_{target}"
    lo, hi = ci_cluster(d, delta)
    return dict(perimetro=scope, campionato=league, bersaglio=target,
                partite=len(d) // 2, righe=len(d),
                previsto=d[f"previsto_{target}"].mean(), osservato=d[target].mean(),
                mae=err.abs().mean(), rmse=np.sqrt((err ** 2).mean()), bias=err.mean(),
                crps=d[f"crps_{target}"].mean(),
                crps_baseline=d[f"crps_base_{target}"].mean(),
                miglioramento_crps_pct=-100*d[delta].mean()/d[f"crps_base_{target}"].mean(),
                delta_crps=d[delta].mean(), delta_ci95_low=lo, delta_ci95_high=hi,
                copertura80=d[f"copertura80_{target}"].mean())


def table(d):
    return d.to_markdown(index=False, floatfmt=".3f")


def main():
    html_path = OUT / "previsioni.html"
    html = html_path.read_text(encoding="utf-8")
    page = json.loads(re.search(r"<script>const DATI=(.*?);</script>", html, re.S).group(1))
    generated = pd.Timestamp(re.search(r"generata il (\d{4}-\d{2}-\d{2} \d{2}:\d{2})", html).group(1))
    frozen_date = pd.Timestamp("2026-08-30")
    registry = pd.read_csv(OUT / "fase16_o1_registro.csv").set_index("campionato")
    provenance = [{"file": html_path.name, "sha256": sha(html_path),
                   "pubblicazione_dichiarata": str(generated)}]
    pieces, audit = [], []
    for league in config.LEAGUE_CODES:
        d = pd.read_parquet(config.team_match(league, config.SEASON_CORRENTE))
        d = d[["campionato", "stagione", "matchId", "date", "team", "opponent",
               "is_home", "team_match_idx", "shots", "sot"]].copy()
        d["date"] = pd.to_datetime(d["date"])
        assert not d.duplicated(["matchId", "is_home"]).any()
        assert d.groupby("matchId").size().eq(2).all()
        for _, match in d.groupby("matchId"):
            h, a = match.sort_values("is_home", ascending=False).to_dict("records")
            assert h["team"] == a["opponent"] and a["team"] == h["opponent"]
        frozen_path = OUT / f"fase16_o1_congelate_{league}_2026-08-30.csv"
        assert sha(frozen_path) == registry.loc[league, "sha256"], "Archivio modificato"
        provenance.append({"file": frozen_path.name, "sha256": sha(frozen_path)})
        frozen = pd.read_csv(frozen_path).rename(columns={
            "squadra": "team", "avversario": "opponent", "lambda_tentativi": "f_shots",
            "lambda_sot": "f_sot", "r": "f_r_shots", "r_sot": "f_r_sot"})
        frozen["is_home"] = frozen.campo.eq("casa").astype(int)
        d = d.merge(frozen[["team", "opponent", "is_home", "f_shots", "f_sot",
                            "f_r_shots", "f_r_sot"]],
                    on=["team", "opponent", "is_home"], how="left", validate="many_to_one")
        b = page["campionati"][league]
        assert b["stagione"] == config.SEASON_CORRENTE
        grid = pd.DataFrame(b["righe"]).rename(columns={"s": "team", "a": "opponent",
                                                        "lam": "p_shots", "sot": "p_sot"})
        grid["is_home"] = grid.c.eq("casa").astype(int)
        # Il calendario include anche squadre assenti dalla griglia libera
        # (Bundesliga: non tutte avevano disputato una gara all'ultimo update).
        calendar_rows = []
        for p in b["partite_cal"]:
            for team, opponent, home, vol, sot in (
                (p["c"], p["a"], 1, "lc", "sc"), (p["a"], p["c"], 0, "la", "sa")
            ):
                calendar_rows.append(dict(team=team, opponent=opponent, is_home=home,
                                          p_shots=p[vol], p_sot=p[sot], np=p["sp"]))
        keys = ["team", "opponent", "is_home"]
        joined = pd.concat([grid, pd.DataFrame(calendar_rows)], ignore_index=True)
        for col in ("p_shots", "p_sot"):
            assert joined.groupby(keys)[col].nunique().le(1).all(), "Pagina internamente discordante"
        grid = joined.drop_duplicates(keys)
        d = d.merge(grid[["team", "opponent", "is_home", "p_shots", "p_sot", "np"]],
                    on=["team", "opponent", "is_home"], how="left", validate="many_to_one")
        # Una pagina generata dopo l'esito non entra nel campione pre-partita.
        use_page = (d.date.gt(generated.normalize()) & d.date.gt(pd.Timestamp(b["come_di"]))
                    & d.p_shots.notna())
        use_frozen = ~use_page & d.f_shots.notna()
        d["fonte"] = np.select([use_page, use_frozen], [html_path.name, frozen_path.name], default="assente")
        d["pre_partita"] = use_page | (use_frozen & d.date.gt(frozen_date))
        d["stato"] = np.select([d.pre_partita, use_frozen],
                                ["pre_partita", "archivio_non_anteriore"], default="senza_previsione_valutabile")
        d["data_pubblicazione"] = np.select([use_page, use_frozen],
                                            [str(generated), "2026-08-30"], default="")
        d["neopromossa_coinvolta"] = d.np.gt(0)
        previous = pd.read_parquet(config.team_match(league, config.SEASONS_STORICHE[-1]))
        assert pd.to_datetime(previous.date).max() < d.date.min()
        for target in ("shots", "sot"):
            d[f"previsto_{target}"] = np.select([use_page, use_frozen],
                                                [d[f"p_{target}"], d[f"f_{target}"]], default=np.nan)
            d[f"r_{target}"] = np.where(use_page, b["r" if target == "shots" else "r_sot"], d[f"f_r_{target}"])
            d[f"errore_{target}"] = d[f"previsto_{target}"] - d[target]
            means = previous.groupby("team")[target].mean()
            d[f"baseline_{target}"] = d.team.map(means).fillna(previous[target].mean())
            ok = d[f"previsto_{target}"].notna()
            y, lam, r = (d.loc[ok, c].to_numpy() for c in [target, f"previsto_{target}", f"r_{target}"])
            base = d.loc[ok, f"baseline_{target}"].to_numpy()
            kmax = max(int(y.max()), validate.crps_k_max(np.r_[lam, base], np.r_[r, r]))
            d.loc[ok, f"crps_{target}"] = validate.crps_conteggi(y, lam, r, k_max=kmax)
            d.loc[ok, f"crps_base_{target}"] = validate.crps_conteggi(y, base, r, k_max=kmax)
            d[f"delta_crps_{target}"] = d[f"crps_{target}"] - d[f"crps_base_{target}"]
            d.loc[ok, f"copertura80_{target}"] = ((y >= dispersion.ppf(.1, lam, r)) &
                                                              (y <= dispersion.ppf(.9, lam, r))).astype(float)
        assert d.groupby("matchId").pre_partita.nunique().eq(1).all()
        audit.append(dict(campionato=league, partite=len(d)//2,
                          prima_data=str(d.date.min().date()), ultima_data=str(d.date.max().date()),
                          pre_partita=int(d.pre_partita.sum())//2,
                          archivio_non_anteriore=int(d.stato.eq("archivio_non_anteriore").sum())//2,
                          senza_previsione=int(d.fonte.eq("assente").sum())//2,
                          dati_pagina_al=b["come_di"], partite_training_pagina=b["partite"]))
        pieces.append(d)
    all_rows = pd.concat(pieces, ignore_index=True).sort_values(["campionato", "date", "matchId", "is_home"])
    detail = all_rows.drop(columns=[c for c in all_rows if c.startswith(("f_", "p_"))])
    detail.to_csv(OUT / f"{PREFIX}_squadra_partita.csv", index=False, encoding="utf-8-sig")
    summary = []
    scopes = {"pre_partita": all_rows[all_rows.pre_partita],
              "archivio_non_anteriore": all_rows[all_rows.stato.eq("archivio_non_anteriore")]}
    for scope, rows in scopes.items():
        for league, d in [("TUTTI", rows), *rows.groupby("campionato")]:
            if len(d):
                summary.extend(metrics(d, scope, league, t) for t in ("shots", "sot"))
    summary = pd.DataFrame(summary)
    summary.to_csv(OUT / f"{PREFIX}_metriche.csv", index=False)
    pd.DataFrame(audit).to_csv(OUT / f"{PREFIX}_copertura.csv", index=False)
    matches = []
    for (league, mid), m in all_rows.groupby(["campionato", "matchId"]):
        h, a = m.sort_values("is_home", ascending=False).to_dict("records")
        row = dict(campionato=league, matchId=mid, data=h["date"], casa=h["team"],
                   trasferta=a["team"], stato=h["stato"], fonte=h["fonte"])
        for t in ("shots", "sot"):
            for side, v in (("casa", h), ("trasferta", a)):
                row[f"{t}_{side}_previsti"] = v[f"previsto_{t}"]
                row[f"{t}_{side}_osservati"] = v[t]
            row[f"{t}_totale_previsto"] = h[f"previsto_{t}"] + a[f"previsto_{t}"]
            row[f"{t}_totale_osservato"] = h[t] + a[t]
        matches.append(row)
    matches = pd.DataFrame(matches).sort_values(["campionato", "data", "matchId"])
    matches.to_csv(OUT / f"{PREFIX}_partite.csv", index=False, encoding="utf-8-sig")
    eligible = scopes["pre_partita"]
    briers = []
    for lg, d in [("TUTTI", eligible), *eligible.groupby("campionato")]:
        for target, lines in (("shots", page["linee"]), ("sot", page["linee_sot"])):
            for line in lines:
                p = dispersion.p_over(d[f"previsto_{target}"].to_numpy(), line, d[f"r_{target}"].to_numpy())
                y = d[target].gt(line).to_numpy()
                briers.append(dict(campionato=lg, bersaglio=target, linea=line, n=len(d),
                                   p_media=p.mean(), frequenza=y.mean(), brier=np.mean((p-y)**2)))
    briers = pd.DataFrame(briers)
    briers.to_csv(OUT / f"{PREFIX}_brier.csv", index=False)
    (OUT / f"{PREFIX}_provenienza.json").write_text(json.dumps({
        "fonti": provenance, "bootstrap_repliche": N_BOOT, "seed": 42,
        "regola": "pubblicazione < data partita; stessa data esclusa senza kickoff",
        "input_esiti": [{"file": str(config.team_match(lg, config.SEASON_CORRENTE)),
                          "sha256": sha(config.team_match(lg, config.SEASON_CORRENTE))}
                         for lg in config.LEAGUE_CODES]}, indent=2), encoding="utf-8")
    # Copia leggibile del contenuto della pagina usata, per conservare i numeri.
    (OUT / f"{PREFIX}_pagina_snapshot.json").write_text(json.dumps(page, ensure_ascii=False, indent=2), encoding="utf-8")

    total_metrics = []
    for lg, m in [("TUTTI", matches[matches.stato.eq("pre_partita")]),
                  *matches[matches.stato.eq("pre_partita")].groupby("campionato")]:
        for t in ("shots", "sot"):
            pred, obs = m[f"{t}_totale_previsto"], m[f"{t}_totale_osservato"]
            total_metrics.append(dict(campionato=lg, bersaglio=t, partite=len(m),
                                      previsto=pred.mean(), osservato=obs.mean(),
                                      mae=(pred-obs).abs().mean(), bias=(pred-obs).mean()))
    total_metrics = pd.DataFrame(total_metrics)
    total_metrics.to_csv(OUT / f"{PREFIX}_totali.csv", index=False)
    primary = summary[summary.perimetro.eq("pre_partita")]
    overall = primary[primary.campionato.eq("TUTTI")].set_index("bersaglio")
    cols = ["campionato", "partite", "previsto", "osservato", "mae", "rmse", "bias", "crps", "copertura80"]
    parts = ["# Tiri e tiri in porta 2026/2027: previsioni salvate contro risultati locali\n",
             f"Dati locali dal {all_rows.date.min():%d/%m/%Y} al {all_rows.date.max():%d/%m/%Y}. "
             f"{len(all_rows)//2} partite; {len(eligible)//2} con previsione pre-partita verificabile "
             "rispetto alle date dichiarate negli archivi. Nessun nuovo fit e nessuno scaricamento.\n",
             "## Copertura e selezione delle previsioni\n", table(pd.DataFrame(audit)),
             "Si usa l'ultima previsione salvata prima del giorno della partita: pagina del "
             f"{generated:%d/%m/%Y %H:%M}, oppure CSV congelati del 30/08. "
             "La stessa data non prova l'anteriorità senza kickoff: si ripiega sull'archivio precedente, "
             "se disponibile. Il campione principale richiede anche dati di training anteriori alla gara. "
             "Le date di pubblicazione sono metadati locali, non una certificazione esterna. "
             "Gli hash dei CSV coincidono con il registro originale.\n",
             "I CSV riportano stagione 2025-2026 perché descrivono il fit storico; sono applicati "
             "agli accoppiamenti 2026-2027. La pagina contiene anche le neopromosse. Le previsioni "
             "archiviate restano fisse: queste metriche non valutano eventuali aggiornamenti mai salvati. "
             "La Liga include anche la sesta partita di alcune squadre: lo snapshot precedente resta "
             "una previsione valida, ma non documenta il successivo passaggio al modello within-season.\n",
             "## Lettura dei risultati\n",
             f"Nel campione pre-partita, per squadra, i tiri previsti sono "
             f"{overall.loc['shots', 'previsto']:.2f} contro {overall.loc['shots', 'osservato']:.2f} "
             f"osservati; i tiri in porta {overall.loc['sot', 'previsto']:.2f} contro "
             f"{overall.loc['sot', 'osservato']:.2f}. Il modello sottostima entrambi. "
             "La Serie A presenta gli errori assoluti medi più elevati su entrambi i bersagli; "
             "la Premier League i più bassi. Sono confronti descrittivi su partite e scale diverse.\n",
             f"Rispetto al baseline, la riduzione del CRPS complessivo è "
             f"{overall.loc['shots', 'miglioramento_crps_pct']:.2f}% sui tiri e "
             f"{overall.loc['sot', 'miglioramento_crps_pct']:.2f}% sui tiri in porta. "
             "Entrambi gli intervalli del delta comprendono zero: il vantaggio complessivo "
             "non è conclusivo. Per i tiri in porta il modello è peggiore del baseline in Liga "
             "e Serie A sul campione osservato. La Bundesliga mostra un vantaggio con intervallo "
             "puntuale sotto zero, ma su poche gare e senza correzione per confronti multipli.\n",
             "I dati indicano di monitorare soprattutto il livello previsto in Serie A e Bundesliga. "
             "Un eventuale aggiustamento va verificato su nuove partite: correggere e rivalutare "
             "sugli stessi esiti non misurerebbe un miglioramento fuori campione.\n",
             "## Risultati principali per squadra-partita\n",
             "MAE = errore assoluto medio; bias = previsto meno osservato (negativo: sottostima). "
             "Il CRPS valuta la distribuzione NB2, usando la dispersione pubblicata; più basso è meglio. "
             "Copertura80 indica la frequenza dentro l'intervallo centrale nominale all'80%; "
             "sui conteggi la discrezione può produrre coperture maggiori.\n"]
    for t, label in (("shots", "Tiri"), ("sot", "Tiri in porta")):
        parts += [f"### {label}\n", table(primary[primary.bersaglio.eq(t)][cols])]
    parts += ["## Confronto con la media della squadra nella stagione precedente\n",
              "Baseline calcolato solo sul 2025-2026; per le neopromosse si usa la media del campionato. "
              "Il confronto usa esattamente le stesse righe e la stessa dispersione. Intervalli al 95% "
              "da bootstrap per partita, stratificato per campionato (5.000 repliche). "
              "Delta negativo favorisce il modello. Gli intervalli sono puntuali, senza correzione "
              "per confronti multipli, e non modellano dipendenze persistenti fra gare della stessa squadra.\n",
              table(primary[["campionato", "bersaglio", "partite", "crps", "crps_baseline",
                             "miglioramento_crps_pct", "delta_crps", "delta_ci95_low", "delta_ci95_high"]]),
              "## Probabilità di superamento delle linee\n",
              "Probabilità ricostruite dai parametri salvati, mantenendo gli arrotondamenti "
              "della pagina (lambda a 4 decimali, dispersione a 3). Ogni riga è una squadra-partita. "
              "La frequenza osservata è descrittiva, non un baseline utilizzabile prima degli esiti.\n",
              table(briers[briers.campionato.eq("TUTTI")]),
              "## Totali delle due squadre per partita\n", table(total_metrics),
              "## Errori maggiori nel campione pre-partita\n"]
    for t in ("shots", "sot"):
        worst = eligible.assign(errore_assoluto=eligible[f"errore_{t}"].abs()).nlargest(8, "errore_assoluto")
        parts += [f"### {t}\n", table(worst[["campionato", "date", "team", "opponent", "is_home",
                                                            f"previsto_{t}", t, f"errore_{t}"]])]
    parts += ["## Archivio non anteriore: solo confronto descrittivo\n",
              "Le partite seguenti hanno una previsione nel CSV, ma la partita precede o coincide "
              "con il giorno di congelamento. Il modello usa lo storico precedente, ma questo non "
              "dimostra che il pronostico sia stato pubblicato prima della gara. Non sono incluse "
              "nel risultato principale. Le partite senza previsione valutabile rimangono nei CSV "
              "di dettaglio con valori previsti vuoti.\n",
              table(summary[summary.perimetro.eq("archivio_non_anteriore")][["bersaglio", *cols]]),
              "## Artefatti e riproduzione\n",
              "- `analisi_2627_partite.csv`: tutte le gare, tiri e SoT previsti/osservati casa, trasferta e totale.\n"
              "- `analisi_2627_squadra_partita.csv`: errori, fonte, data di pubblicazione e ammissibilità per lato.\n"
              "- `analisi_2627_metriche.csv`, `analisi_2627_brier.csv`, `analisi_2627_totali.csv`: misure aggregate.\n"
              "- `analisi_2627_copertura.csv`, `analisi_2627_provenienza.json`, `analisi_2627_pagina_snapshot.json`: audit.\n"
              "- Riproduzione: `.venv/Scripts/python.exe scripts/analizza_previsioni_2627.py`.\n",
              "La vecchia verifica sulle prime due partite per squadra ha un perimetro diverso: "
              "i suoi risultati non sono direttamente confrontabili con questi. Nessuna conclusione "
              "sulla stagione intera o sulla redditività delle scommesse deriva da questo campione.\n"]
    (OUT / f"{PREFIX}_prestazioni.md").write_text("\n\n".join(parts), encoding="utf-8")
    if (config.ROOT / "data/external/paper_over/protocol.json").exists():
        from scripts.analizza_over_2627 import main as aggiorna_over
        aggiorna_over()
    else:
        from scripts.pagina_analisi_2627 import scrivi
        print("Report HTML:", scrivi())
    print(pd.DataFrame(audit).to_string(index=False))
    print(primary.to_string(index=False))
    print("Report:", OUT / f"{PREFIX}_prestazioni.md")


if __name__ == "__main__":
    main()
