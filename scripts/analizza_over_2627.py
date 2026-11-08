"""Audit Over salvati, calibrazione descrittiva e stato del test prospettico.

Non inventa quote e non trasforma le probabilità del modello in prezzi di mercato.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sot import config, dispersion, over_paper as OP

ROOT = config.ROOT / "data" / "external" / "paper_over" if hasattr(config, "ROOT") else Path(__file__).resolve().parents[1] / "data/external/paper_over"


def forecast_rows(cutoff=None):
    sides = pd.read_csv(config.REPORTS / "analisi_2627_squadra_partita.csv")
    sides = sides[sides.pre_partita].copy()
    if cutoff is not None:
        sides = sides[pd.to_datetime(sides.date) < pd.Timestamp(cutoff)].copy()
    page = json.loads((config.REPORTS / "analisi_2627_pagina_snapshot.json").read_text(encoding="utf-8"))
    records = []
    for lg, d in sides.groupby("campionato"):
        prior = pd.read_parquet(config.team_match(lg, config.SEASONS_STORICHE[-1]))
        b = page["campionati"][lg]
        calendar = {(r["c"], r["a"]): r for r in b["partite_cal"]}
        for target, lines in (("shots", page["linee"]), ("sot", page["linee_sot"])):
            for line in lines:
                probabilities = dispersion.p_over(d[f"previsto_{target}"].to_numpy(), line, d[f"r_{target}"].to_numpy())
                baseline = float(prior[target].gt(line).mean())
                for (_, r), p in zip(d.iterrows(), probabilities):
                    records.append(dict(league=lg, match_id=str(r.matchId), date=r.date,
                                        scope="team", target=target, side="home" if r.is_home else "away",
                                        line=line, p=float(p), outcome=int(r[target]>line), baseline=baseline,
                                        source=r.fonte, published_at=r.data_pubblicazione))
            lines_total = page["linee_tot" if target == "shots" else "linee_tot_sot"]
            old_totals = prior.groupby("matchId")[target].sum()
            for _, r in d[d.is_home.eq(1)].iterrows():
                if r.fonte != "previsioni.html":
                    continue  # nessuna distribuzione totale documentata nel CSV del 30/08
                match = calendar.get((r.team, r.opponent))
                if match is None:
                    continue
                other = d[(d.matchId==r.matchId)&d.is_home.eq(0)].iloc[0]
                probs = match["pt" if target == "shots" else "pts"]
                for line, p in zip(lines_total, probs):
                    records.append(dict(league=lg, match_id=str(r.matchId), date=r.date,
                                        scope="total", target=target, side="total", line=line,
                                        p=p, outcome=int(r[target]+other[target]>line),
                                        baseline=float(old_totals.gt(line).mean()), source=r.fonte,
                                        published_at=r.data_pubblicazione))
    return pd.DataFrame(records), sides


def block_interval(d):
    """Blocchi per data: preserva lati della gara e dipendenze nello stesso giorno."""
    d = d.assign(error=d.outcome-d.p)
    blocks = d.groupby("date").error.agg(["sum", "count"])
    if len(blocks) < 2:
        return [None, None]
    rng = np.random.default_rng(42)
    ids = rng.integers(0, len(blocks), size=(2000,len(blocks)))
    delta = blocks["sum"].to_numpy()[ids].sum(axis=1)/blocks["count"].to_numpy()[ids].sum(axis=1)
    return np.quantile(delta,[.025,.975]).tolist()


def assess(d):
    low, high = block_interval(d)
    bs = float(np.mean((d.p-d.outcome)**2))
    base = float(np.mean((d.baseline-d.outcome)**2))
    return dict(n=len(d), matches=d[["league","match_id"]].drop_duplicates().shape[0],
                dates=d.date.nunique(), predicted=float(d.p.mean()), observed=float(d.outcome.mean()),
                calibration_gap=float((d.outcome-d.p).mean()), gap_low=low, gap_high=high,
                brier=bs, brier_baseline=base, brier_skill=1-bs/base if base else None,
                logloss=float(-np.mean(d.outcome*np.log(np.clip(d.p,1e-9,1-1e-9))+(1-d.outcome)*np.log(np.clip(1-d.p,1e-9,1-1e-9)))))


def main():
    protocol = OP.freeze_protocol(ROOT)
    development = OP.load_records(ROOT / "development")
    if development:
        d = pd.DataFrame(development[0]["over_rows"])
        sides = pd.DataFrame(development[0]["team_rows"])
    else:
        # La diagnosi non si allarga al futuro intoccato mentre il test procede.
        cutoff = str(OP.utc(protocol["frozen_at"]).tz_convert("Europe/Rome").date())
        d, sides = forecast_rows(cutoff)
        OP.save_record(ROOT / "development", dict(
            id="development_v1", recorded_at=OP.utc_now(), cutoff_exclusive=cutoff,
            protocol_sha256=protocol["sha256"],
            over_rows=json.loads(d.to_json(orient="records",double_precision=15)),
            team_rows=json.loads(sides.to_json(orient="records",double_precision=15))))
    rows, bins = [], []
    for lg, data in [("TUTTI",d), *d.groupby("league")]:
        for (scope,target,line), g in data.groupby(["scope","target","line"]):
            rows.append(dict(league=lg,scope=scope,target=target,line=float(line),**assess(g)))
        # Ogni linea conserva il proprio denominatore: nessuna finta moltiplicazione delle gare.
        for (scope,target,line), g in data.groupby(["scope","target","line"]):
            for i in range(5):
                cut=g[(g.p>=i/5)&(g.p<((i+1)/5) if i<4 else g.p<=1)]
                if len(cut):
                    bins.append(dict(league=lg,scope=scope,target=target,line=float(line),bin_low=i/5,bin_high=(i+1)/5,**assess(cut)))
    calibration = pd.DataFrame(rows)
    calibration.to_csv(config.REPORTS/"over_2627_calibrazione.csv",index=False)
    pd.DataFrame(bins).to_csv(config.REPORTS/"over_2627_affidabilita.csv",index=False)
    d.to_csv(config.REPORTS/"over_2627_previsioni_valutate.csv",index=False)
    pairs = sides[sides.is_home.eq(1)].merge(sides[sides.is_home.eq(0)],on=["campionato","matchId"],suffixes=("_h","_a"),validate="one_to_one")
    correlations=[]
    for lg,g in [("TUTTI",pairs),*pairs.groupby("campionato")]:
        for title,a,b in (("tiri casa / tiri trasferta","errore_shots_h","errore_shots_a"),
                          ("SoT casa / SoT trasferta","errore_sot_h","errore_sot_a"),
                          ("tiri / SoT casa","errore_shots_h","errore_sot_h"),
                          ("tiri / SoT trasferta","errore_shots_a","errore_sot_a")):
            correlations.append(dict(league=lg,pair=title,n=len(g),correlation=float(g[a].corr(g[b]))))
    quotes=OP.load_records(ROOT/"quotes")
    plans=OP.load_records(ROOT/"decisions")
    settlements={r["quote_id"]:r for r in OP.load_records(ROOT/"settlements")}
    settlements.update({f"{r['decision_id']}:{r['size']}":r for r in OP.load_records(ROOT/'coupon_settlements')})
    # Confronto con probabilità di mercato no-vig solo dove entrambe le quote sono documentate.
    market=[]
    for q in quotes:
        s=settlements.get(q["id"])
        if s is None or s["result"]=="void":
            continue
        y=int(s["result"]=="won")
        under=q.get("under_odds")
        market_p=(1/q["over_odds"])/(1/q["over_odds"]+1/under) if under else None
        market.append(dict(quote_id=q["id"],p_model=q["p"],p_market=market_p,outcome=y,
                           brier_model=(q["p"]-y)**2,brier_market=(market_p-y)**2 if market_p is not None else None))
    snapshots=OP.load_records(ROOT/"predictions")
    candidates=max(snapshots,key=lambda s:s["published_at"])["selections"] if snapshots else []
    state={"protocol":protocol,"calibration":rows,"reliability":bins,"dependence":correlations,
           "coverage":{"team_matches":sides[["campionato","matchId"]].drop_duplicates().shape[0],
                       "total_matches":d[d.scope.eq("total")][["league","match_id"]].drop_duplicates().shape[0],
                       "historical_verified_odds":0,"prospective_quotes":len(quotes)},
           "odds_audit":[{"file":"como_tiri_in_porta_2025-2026.xlsx","status":"escluso: quote sintetiche",
                          "evidence":"Formule K2=1/(I2^(1/J2)), L2=1/((1-I2)^(1/J2)); nota: margine del bookmaker ipotizzato"},
                         {"file":"legacy/como_tip_quote_2526.csv","status":"escluso: nessun bookmaker o timestamp di raccolta; stagione 2025/26"}],
           "performance":OP.performance(plans,settlements,protocol),"risk":OP.simulate_risk(plans,protocol),
           "decisions":plans,"quotes":quotes,"candidates":candidates,"market_comparison":market,
           "status":"nessuna giocata" if not quotes else "quote registrate; valutare decisioni congelate",
           "development_note":"Le 105 gare erano già state analizzate: sviluppo e diagnosi, non test intoccato della strategia. Il test economico comincia dopo il congelamento del protocollo.",
           "sources":[{"title":"Quote storiche: snapshot temporali e copertura","url":"https://the-odds-api.com/historical-odds-data/"},
                      {"title":"Regole di liquidazione pubblicate","url":"https://www.gamblingcommission.gov.uk/licensees-and-businesses/page/settling-bets-in-accordance-with-published-rules"}]}
    out=config.REPORTS/"over_2627_stato.json"
    out.write_text(json.dumps(state,ensure_ascii=False,indent=2,allow_nan=False),encoding="utf-8")
    pooled=calibration[calibration.league.eq("TUTTI")]
    md=["# Over 2026/27: calibrazione e protocollo di paper trading\n",
        "**Profitto non dimostrato: zero quote storiche reali e verificabili per il perimetro.** Nessun ROI storico viene inventato.\n",
        state["development_note"],"\n## Quote escluse\n",
        "Il foglio Excel Como 2025/26 genera i prezzi dalle probabilità (`1/(p^(1/k))`) con un margine ipotizzato. Non contiene un prezzo di mercato utilizzabile per un backtest. Il CSV legacy manca di bookmaker e timestamp. Non è stato riusato il codice legacy.\n",
        "## Calibrazione delle linee\n",
        "Squadre: 105 partite / 210 lati. Totali: 98 partite con probabilità salvate nella pagina pre-partita; le altre 7 non hanno una distribuzione totale archiviata. Le probabilità di squadra sono ricostruite dai parametri salvati, con i loro arrotondamenti. Baseline: frequenza 2025/26 del rispettivo campionato e mercato, disponibile prima delle gare.\n",
        pooled.to_markdown(index=False,floatfmt=".4f"),
        "\nIl gap è osservato meno previsto. IC95 bootstrap per data (2.000 repliche, seed 42); preserva i lati e le gare dello stesso giorno. Poche date: intervalli esplorativi, senza correzione multipla. Le fasce di affidabilità sono fisse: 0–20–40–60–80–100%, separate per linea.\n",
        "## Dipendenza\n",pd.DataFrame(correlations).query("league == 'TUTTI'").to_markdown(index=False,floatfmt=".3f"),
        "\nCorrelazioni descrittive dei residui, non un modello congiunto validato. Sono vietate selezioni della stessa partita e squadre ripetute. Per gare diverse si mostra il prodotto delle probabilità solo come scenario di indipendenza e l'intervallo di Fréchet `[max(0,sum(p)-n+1), min(p)]`, valido senza assumere indipendenza a marginali date.\n",
        "## Regole congelate prima del test futuro\n",json.dumps(protocol,ensure_ascii=False,indent=2),
        "\nIl taglio di 5 punti percentuali (e lo stress a 10) è un'ipotesi prudente, non un intervallo di confidenza individuale e non una garanzia. Nessuna ricalibrazione verso l'alto basata sugli esiti già visti. Prezzi delle multiple richiesti esplicitamente: il prodotto delle quote singole non prova che quella schedina sia disponibile.\n",
        "Ogni strategia dispone di 100 unità iniziali e al massimo 1 unità per data di gioco. Se non gioca, mantiene il capitale: riportare anche l'esposizione effettiva. Stop a 20 unità di drawdown e nessun nuovo piano finché una puntata precedente è da liquidare. Pool: migliori 18 selezioni per EV marginale stressato, una selezione per bookmaker/mercato; stessa regola per tutte le taglie.\n",
        "## Rendimento osservato\n",pd.DataFrame(state["performance"]).to_markdown(index=False,floatfmt=".3f"),
        "\nValori assenti indicano non misurabile, non profitto zero. Gli scenari di perdita del capitale si attivano solo con schedine congelate: 5.000 percorsi, giorni indipendenti, scenario indipendente e stress prudente; non sono risultati di backtest.\n",
        "## Raccolta e uso\nVedi `docs/guide/paper_over.md` e `docs/guide/quote_sisal.md`. Il raccoglitore Sisal registra automaticamente tentativi e osservazioni riconoscibili; la verifica sul sito reale è ancora bloccata dall'accesso. Le osservazioni restano separate dal protocollo economico finché le regole non sono riconciliate. Nessun account collegato o giocata reale; il protocollo usa solo unità virtuali.\n"]
    (config.REPORTS/"over_2627_verifica.md").write_text("\n".join(md),encoding="utf-8")
    from scripts.pagina_analisi_2627 import scrivi
    scrivi()
    print(pooled[["scope","target","line","n","predicted","observed","brier","brier_skill"]].to_string(index=False))
    print("Quote reali:",len(quotes),"Candidati prospettici:",len(candidates),"Stato:",state["status"])


if __name__=="__main__":
    main()
