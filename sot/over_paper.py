"""Paper trading Over: decisioni senza esiti, quote documentate, registri immutabili.

Nessuna funzione effettua giocate o contatta un bookmaker. Le probabilità
congiunte indipendenti sono scenari; il criterio prudente usa Fréchet dopo
uno stress dichiarato sulle probabilità marginali, non un presunto IC individuale.
"""
from __future__ import annotations

import hashlib
import itertools
import json
import math
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

DEFAULT_RULES = {
    "version": 1, "mode": "paper_only", "bankroll": 100.0,
    "daily_budget": 1.0, "stop_drawdown": 20.0,
    "probability_stress": 0.05, "extra_stress": 0.10,
    "min_robust_ev": 0.05, "max_quote_age_minutes": 60,
    "pool_limit": 18, "sizes": [1, 2, 3, 4, 5],
    "selection": "massimo EV al limite inferiore Frechet con p ridotta di 5 punti; astensione se EV < 5%",
    "same_match": "vietato", "shared_team": "vietato", "same_bookmaker": True,
    "multiple_price": "quota complessiva esplicitamente documentata; prodotto quote solo indicativo",
    "settlement": "90 minuti + recupero; linee .5; vittoria/perdita/annullata; fonte e regole documentate",
    "holdout": "solo decisioni registrate dopo il congelamento, prima delle gare; nessun tuning sul test",
    "budget_note": "100 unita virtuali; massimo 1 unita per strategia e data delle gare; non spesa in caso di astensione",
}


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def utc(value):
    t = pd.Timestamp(value)
    if t.tzinfo is None:
        raise ValueError("Timestamp senza fuso orario")
    return t.tz_convert("UTC")


def digest(value):
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False).encode()
    return hashlib.sha256(raw).hexdigest()


def write_once(path: Path, value):
    """Il file esistente non può essere sovrascritto, neppure con --force."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as f:
        json.dump(value, f, ensure_ascii=False, indent=2, allow_nan=False)


def load_records(folder: Path):
    out = []
    for path in sorted(folder.glob("*.json")):
        record = json.loads(path.read_text(encoding="utf-8"))
        claimed = record.pop("sha256")
        if digest(record) != claimed:
            raise ValueError(f"Registro modificato: {path}")
        record["sha256"] = claimed
        out.append(record)
    return out


def save_record(folder: Path, record):
    record = dict(record)
    record["sha256"] = digest(record)
    write_once(folder / f"{record['id']}.json", record)
    return record


def freeze_protocol(root: Path, now=None):
    path = root / "protocol.json"
    if path.exists():
        p = json.loads(path.read_text(encoding="utf-8"))
        body = {k: v for k, v in p.items() if k != "sha256"}
        if digest(body) != p["sha256"]:
            raise ValueError("Protocollo modificato dopo il congelamento")
        return p
    p = {**DEFAULT_RULES, "frozen_at": now or utc_now()}
    p["test_from"] = str((utc(p["frozen_at"]).tz_convert("Europe/Rome") + pd.Timedelta(days=1)).date())
    p["sha256"] = digest(p)
    write_once(path, p)
    return p


def coupon_metrics(legs, odds, stress=0.05, extra_stress=0.10):
    if not legs or not 1 <= len(legs) <= 5:
        raise ValueError("Una schedina richiede da 1 a 5 eventi")
    match_keys = [(x["league"], str(x["match_id"])) for x in legs]
    if len(set(match_keys)) != len(legs):
        raise ValueError("Più selezioni della stessa partita: congiunta non validata")
    teams = [(x["league"], t) for x in legs for t in (x["home"], x["away"])]
    if len(set(teams)) != len(teams):
        raise ValueError("Squadra ripetuta nella schedina")
    books = {x.get("bookmaker", "") for x in legs}
    if len(books) != 1:
        raise ValueError("Una multipla non può combinare bookmaker diversi")
    p = np.asarray([x["p"] for x in legs], dtype=float)
    if not np.isfinite(p).all() or ((p <= 0) | (p >= 1)).any():
        raise ValueError("Probabilità non valida")
    if odds is not None and (not math.isfinite(odds) or odds <= 1):
        raise ValueError("Quota decimale non valida")
    lower, upper = max(0., float(p.sum() - len(p) + 1)), float(p.min())
    robust = max(0., float(np.maximum(0., p - stress).sum() - len(p) + 1))
    severe = max(0., float(np.maximum(0., p - extra_stress).sum() - len(p) + 1))
    independent = float(p.prod())
    return {
        "p_independent": independent, "p_lower": lower, "p_upper": upper,
        "p_robust": robust, "p_stress10": severe,
        "loss_independent": 1-independent, "loss_min": 1-upper, "loss_max": 1-lower,
        "fair_independent": 1/independent, "fair_robust": 1/robust if robust else None,
        "offered_odds": odds,
        "ev_independent": independent*odds-1 if odds is not None else None,
        "ev_robust": robust*odds-1 if odds is not None else None,
        "ev_stress10": severe*odds-1 if odds is not None else None,
    }


def validate_quote(row, prediction, now, protocol):
    """Acquisizione prospettica: nessuna data di cattura può essere retrodatata."""
    now = utc(now)
    observed = utc(row["observed_at"])
    kickoff = utc(row["kickoff"])
    published = utc(prediction["published_at"])
    if not published <= observed <= now < kickoff:
        raise ValueError("Richiesto: previsione <= rilevazione <= registrazione < kickoff")
    if (now-observed).total_seconds() > protocol["max_quote_age_minutes"]*60:
        raise ValueError("Quota troppo vecchia per una decisione prospettica")
    if utc(protocol["frozen_at"]) > now:
        raise ValueError("Il protocollo deve precedere la registrazione")
    if str(kickoff.tz_convert("Europe/Rome").date()) != prediction["match_date"]:
        raise ValueError("Data kickoff diversa dal calendario della previsione")
    if prediction["match_date"] < protocol["test_from"]:
        raise ValueError("Partita fuori dal test futuro")
    if row.get("settlement_rule") != "opta_90min_halfline":
        raise ValueError("Confermare regola Opta, 90 minuti + recupero, linea .5")
    for name in ("bookmaker", "source_url", "rules_url", "evidence_path"):
        if not str(row.get(name, "")).strip():
            raise ValueError(f"Campo obbligatorio: {name}")
    for name in ("over_odds", "under_odds"):
        value = row.get(name)
        if name == "under_odds" and (value is None or value == ""):
            continue
        if not math.isfinite(float(value)) or float(value) <= 1:
            raise ValueError(f"Quota non valida: {name}")
    return True


def select_slips(quotes, combined, protocol, day, now):
    """Selezione pura: nessun esito, rendimento passato o saldo futuro in ingresso."""
    clock = utc(now)
    candidates = []
    for q in quotes:
        if q["match_date"] != day or utc(q["kickoff"]) <= clock:
            continue
        if not utc(q["recorded_at"]) <= clock or not utc(q["observed_at"]) <= clock:
            continue
        if (clock-utc(q["observed_at"])).total_seconds() > protocol["max_quote_age_minutes"]*60:
            continue
        candidates.append(q)
    # Una selezione ha un solo prezzo corrente per bookmaker.
    latest = {}
    for q in sorted(candidates, key=lambda x: utc(x["observed_at"])):
        latest[(q["league"],q["match_id"],q["target"],q["side"],q["line"],q["bookmaker"])] = q
    candidates = [q for q in latest.values() if max(0., q["p"]-protocol["probability_stress"])*q["over_odds"] >= 1]
    candidates = sorted(candidates, key=lambda q: (-(q["p"]-protocol["probability_stress"])*q["over_odds"], q["id"]))[:protocol["pool_limit"]]
    offered = {}
    for c in sorted(combined, key=lambda c: utc(c["observed_at"])):
        if not utc(c["observed_at"]) <= utc(c["recorded_at"]) <= clock:
            continue
        if (clock-utc(c["observed_at"])).total_seconds() <= protocol["max_quote_age_minutes"]*60:
            offered[tuple(sorted(c["quote_ids"]))] = c
    plans = []
    for size in protocol["sizes"]:
        best = None
        missing_price = False
        for legs in itertools.combinations(candidates, size):
            record = offered.get(tuple(sorted(q["id"] for q in legs)))
            odds = legs[0]["over_odds"] if size == 1 else record["odds"] if record else None
            try:
                stats = coupon_metrics(legs, odds, protocol["probability_stress"], protocol["extra_stress"])
            except ValueError:
                continue
            if odds is None:
                missing_price = True
                continue
            if stats["ev_robust"] < protocol["min_robust_ev"]:
                continue
            if best is None or stats["ev_robust"] > best["metrics"]["ev_robust"]:
                best = {"size": size, "status": "paper_bet", "stake": protocol["daily_budget"],
                        "legs": list(legs), "combined_quote_id": record["id"] if size > 1 else None,
                        "metrics": stats, "reason": "criterio prudente superato"}
        plans.append(best or {"size": size, "status": "no_bet", "stake": 0., "legs": [], "metrics": None,
                              "reason": "quota della multipla non documentata" if missing_price else "quote assenti, insufficienti, scadute o vantaggio prudente insufficiente"})
    return plans


def settle_coupon(plan, settlements, official=None):
    if plan["status"] != "paper_bet":
        return {"status": "no_bet", "stake": 0., "profit": 0.}
    if official is not None:
        gross = float(official["gross_return"])
        profit = gross-plan["stake"]
        return {"status": "won" if profit>0 else "lost" if profit<0 else "void",
                "stake": plan["stake"] if profit else 0., "profit": profit}
    results = [settlements.get(q["id"]) for q in plan["legs"]]
    if any(r is None for r in results):
        return {"status": "pending", "stake": plan["stake"], "profit": None}
    if any(r["result"] == "void" for r in results) and len(results) > 1:
        # Non inventare la quota ridotta di una multipla con bonus o prezzi speciali.
        return {"status": "needs_bookmaker_settlement", "stake": plan["stake"], "profit": None}
    if all(r["result"] == "void" for r in results):
        return {"status": "void", "stake": 0., "profit": 0.}
    won = all(r["result"] == "won" for r in results)
    return {"status": "won" if won else "lost", "stake": plan["stake"],
            "profit": plan["stake"]*(plan["metrics"]["offered_odds"]-1) if won else -plan["stake"]}


def performance(plans, settlements, protocol):
    out = []
    for size in protocol["sizes"]:
        balance = peak = protocol["bankroll"]
        drawdown = spent = profit = 0.
        streak = worst_streak = wins = losses = pending = bets = abstentions = settled_count = 0
        for decision in sorted(plans, key=lambda d: d["day"]):
            plan = next(p for p in decision["plans"] if p["size"] == size)
            settled = settle_coupon(plan, settlements, settlements.get(f"{decision.get('id','')}:{size}"))
            if settled["status"] == "no_bet":
                abstentions += 1
                continue
            bets += 1
            if settled["profit"] is None:
                pending += 1
                continue
            settled_count += 1
            spent += settled["stake"]
            profit += settled["profit"]
            balance += settled["profit"]
            peak = max(peak, balance)
            drawdown = max(drawdown, peak-balance)
            if settled["status"] == "lost":
                streak += 1
                losses += 1
                worst_streak = max(worst_streak, streak)
            elif settled["status"] == "won":
                streak = 0
                wins += 1
        out.append(dict(size=size, bets=bets, abstentions=abstentions, pending=pending,
                        staked_settled=spent, profit=profit if settled_count else None,
                        roi=profit/spent if spent else None, bankroll=balance,
                        loss_rate=losses/(wins+losses) if wins+losses else None,
                        max_losing_streak=worst_streak if wins+losses else None,
                        max_drawdown=drawdown if wins+losses else None))
    return out


def simulate_risk(plans, protocol, reps=5000):
    """Scenari condizionati alle schedine congelate, non un ROI storico.

    Un esito Bernoulli per schedina; giorni indipendenti. Il secondo scenario
    usa il limite prudente. Non è una previsione validata del capitale futuro.
    """
    out = []
    for size in protocol["sizes"]:
        slips = [p for d in sorted(plans, key=lambda d: d["day"]) for p in d["plans"]
                 if p["size"] == size and p["status"] == "paper_bet"]
        for scenario, key in (("indipendenza tra eventi", "p_independent"), ("stress Frechet -5 punti", "p_robust")):
            if not slips:
                out.append(dict(size=size, scenario=scenario, n=0, probability_loss=None, drawdown95=None, losing_streak95=None))
                continue
            rng = np.random.default_rng(42)
            balances = np.full(reps, protocol["bankroll"])
            peaks = balances.copy()
            dd = np.zeros(reps)
            streak = np.zeros(reps)
            max_streak = np.zeros(reps)
            stopped = np.zeros(reps, dtype=bool)
            for p in slips:
                active = ~stopped & (balances >= p["stake"])
                won = rng.random(reps) < p["metrics"][key]
                balances += active*p["stake"]*(won*p["metrics"]["offered_odds"]-1)
                streak = np.where(active, np.where(won, 0, streak+1), streak)
                max_streak = np.maximum(max_streak, streak)
                peaks = np.maximum(peaks, balances)
                dd = np.maximum(dd, peaks-balances)
                stopped |= dd >= protocol["stop_drawdown"]
            out.append(dict(size=size, scenario=scenario, n=len(slips), probability_loss=float(np.mean(balances < protocol["bankroll"])),
                            drawdown95=float(np.quantile(dd,.95)), losing_streak95=float(np.quantile(max_streak,.95))))
    return out
