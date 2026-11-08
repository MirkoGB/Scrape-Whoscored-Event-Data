"""Auditable event-only tactical profiles and chronological matchup forecasts.

No tracking is available: pass recipients, carries and transitions below are
explicit proxies. Geometry and the definitions of shots/PPDA reuse the project.
New tactical covariates must beat the base model on a development period; the
later test period is never used for selection. No betting optimisation.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

from .features import BOX_X, BOX_Y_LO, BOX_Y_HI, team_context, ppda
from .model_team import TeamModel, poisson_loglik
from .shots import shots_mask, shots_on_target_mask
from . import dispersion as D

VERSION = 2
MODEL_VERSION = 2
LEAGUE = "ITA-serie-a"
SEASONS = ("2024-2025", "2025-2026", "2026-2027")
TARGETS = ("goals", "shots", "sot", "passes")
TACTICAL = ("progressive_rate", "transition_shot_rate", "high_regain_rate", "long_chain_threat_rate")
EXTRA = tuple(f"{side}_{c}" for side in ("att", "opp") for c in TACTICAL)
PERIODS = {"FirstHalf": 0, "SecondHalf": 1}
RAW_COLS = {
    "matchId", "teamId", "h_a", "playerId", "playerName", "type", "period",
    "minute", "second", "expandedMinute", "x", "y", "endX", "endY",
    "outcomeType", "isTouch", "isShot", "isGoal", "isOwnGoal", "shotBlocked",
    "foulCommitted", "ftScore", "passCorner", "passFreekick", "qualifiers",
    "keeperSaveTotal", "shotDirectCorner", "cardType",
}
BOOL = ("isTouch", "isShot", "isGoal", "isOwnGoal", "shotBlocked", "foulCommitted",
        "passCorner", "passFreekick", "keeperSaveTotal", "shotDirectCorner")


def read_events(path: Path) -> pd.DataFrame:
    e = pd.read_csv(path, usecols=lambda c: c in RAW_COLS, low_memory=False)
    for c in BOOL:
        e[c] = e.get(c, pd.Series(False, index=e.index)).fillna(False).astype(bool)
    for c in ("x", "y", "endX", "endY", "playerId", "second"):
        if c not in e:
            e[c] = np.nan
    e["period_order"] = e.period.map(PERIODS)
    e["clock"] = e.minute * 60 + e.second.fillna(0)
    q = e.get("qualifiers", pd.Series("", index=e.index)).fillna("")
    e["restart"] = (e.passCorner | e.passFreekick
                    | q.str.contains("'type': 'ThrowIn'", regex=False))
    return e.sort_values(["period_order", "clock"], kind="stable").reset_index(drop=True)


def parse_score(value) -> tuple[int, int] | None:
    nums = re.findall(r"\d+", str(value))
    return tuple(map(int, nums)) if len(nums) == 2 else None


def audit_match(e: pd.DataFrame, calendar_score=None) -> list[str]:
    reasons = []
    ft = e.ftScore.dropna()
    score = parse_score(ft.iloc[-1]) if len(ft) else None
    if score is None:
        reasons.append("risultato_finale_assente")
    cal = parse_score(calendar_score)
    if cal is not None and score is not None and cal != score:
        reasons.append("risultato_diverso_dal_calendario")
    end = e[e.type.eq("End") & e.period.eq("SecondHalf")]
    if end.empty or end.minute.max() < 90:
        reasons.append("fine_partita_non_documentata")
    if e[e.h_a.isin(["h", "a"])].teamId.nunique() != 2:
        reasons.append("numero_squadre_non_valido")
    return reasons


def in_box(x, y):
    return (x >= BOX_X) & (y >= BOX_Y_LO) & (y <= BOX_Y_HI)


def event_chains(e: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Conservative observed control chains, not provider possession sequences.

    Stops on stoppages, unsuccessful passes, period changes and >15 s gaps.
    An opponent challenge alone is not treated as a possession change.
    """
    types = {"Pass", "TakeOn", "BallTouch", "BallRecovery", "Interception",
             "MissedShots", "SavedShot", "ShotOnPost", "Goal", "Dispossessed",
             "Miscontrol", "KeeperPickup", "Clearance", "Tackle"}
    barriers = {"Foul", "OffsideGiven", "CornerAwarded", "End", "Start"}
    chains, links = [], []
    current = None
    previous = None

    def close():
        nonlocal current
        if current is not None:
            chains.append(current)
        current = None

    for r in e.itertuples():
        if r.period not in PERIODS:
            continue
        if r.type in barriers:
            close()
            previous = None
            continue
        keeper = r.type == "Save" and r.keeperSaveTotal
        if r.type not in types and not keeper:
            continue
        if r.type in ("Tackle", "Interception", "TakeOn") and r.outcomeType != "Successful":
            continue
        if pd.isna(r.teamId):
            continue
        regain = r.type in ("BallRecovery", "Interception", "Tackle")
        new = (current is None or current["teamId"] != r.teamId
               or current["period"] != r.period or r.clock-current["end"] > 15
               or r.restart)
        if new:
            close()
            current = dict(teamId=r.teamId, period=r.period, start=r.clock, end=r.clock,
                           start_x=r.x, passes=0, shots=0, box=0, regained=regain,
                           high_regain=regain and r.x >= 200/3, restart=r.restart,
                           transition_shots=0, reached_third=False, carry_count=0, carry_m=0.0)
        if (previous is not None and previous.teamId == r.teamId
                and previous.playerId == r.playerId and pd.notna(r.playerId)
                and previous.period == r.period and previous.type != "Pass"
                and 0 < r.clock-previous.clock <= 8 and not r.restart):
            displacement = np.hypot((r.x-previous.x)*1.05, (r.y-previous.y)*.68)
            if 2 <= displacement <= 30:
                current["carry_count"] += 1
                current["carry_m"] += displacement
        if (previous is not None and previous.type == "Pass"
                and previous.outcomeType == "Successful" and not previous.restart
                and not r.restart
                and previous.teamId == r.teamId and previous.period == r.period
                and 0 <= r.clock-previous.clock <= 5
                and pd.notna(r.playerId) and pd.notna(previous.playerId)
                and r.playerId != previous.playerId
                and np.hypot((r.x-previous.endX)*1.05, (r.y-previous.endY)*.68) <= 12):
            links.append(dict(teamId=r.teamId, passer=previous.playerId,
                              receiver=r.playerId, passer_name=previous.playerName,
                              receiver_name=r.playerName, x=previous.x, y=previous.y,
                              endX=previous.endX, endY=previous.endY))
        current["end"] = r.clock
        current["passes"] += int(r.type == "Pass" and r.outcomeType == "Successful")
        current["shots"] += int(r.isShot and not r.isOwnGoal)
        current["box"] += int(in_box(r.x, r.y))
        current["reached_third"] |= bool(r.x >= 200/3 or (r.type == "Pass"
            and r.outcomeType == "Successful" and r.endX >= 200/3))
        current["transition_shots"] += int(r.isShot and not r.isOwnGoal
            and current["regained"] and r.clock-current["start"] <= 10)
        previous = r
        if ((r.type == "Pass" and r.outcomeType != "Successful")
                or r.isShot or r.type in ("Dispossessed", "Miscontrol", "Clearance")):
            close()
            previous = None
    close()
    return pd.DataFrame(chains), pd.DataFrame(links)


def tactical_metrics(e: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    live = e[e.period.isin(PERIODS)].copy()
    ctx = team_context(live).merge(ppda(live), on=["matchId", "teamId"])
    chains, links = event_chains(live)
    rows, positions = [], []
    for tid, g in live.groupby("teamId"):
        p = g[g.type.eq("Pass")]
        success = p.outcomeType.eq("Successful")
        op = p[~p.restart]
        progressive = success & ((p.endX-p.x)*1.05 >= 10)
        box_pass = success & in_box(p.endX, p.endY) & ~in_box(p.x, p.y)
        thirds = success & (p.x < 200/3) & (p.endX >= 200/3)
        ch = chains[chains.teamId.eq(tid)]
        regains = ch[ch.regained & ~ch.restart]
        long = ch[(ch.passes >= 10) & ~ch.restart]
        build = ch[(ch.start_x < 100/3) & ~ch.restart]
        trans = int(regains.transition_shots.sum())
        opp_passes = len(live[live.type.eq("Pass") & live.teamId.ne(tid)])
        row = dict(teamId=tid, passes=len(p), passes_complete=int(success.sum()),
            pass_accuracy=float(success.mean()), open_passes=len(op),
            progressive=int(progressive.sum()), box_entries=int(box_pass.sum()),
            third_entries=int(thirds.sum()), switches=int((success & ((p.endY-p.y).abs() >= 40)).sum()),
            regains=len(regains), high_regains=int(regains.high_regain.sum()),
            transition_shots=trans, long_chains=len(long),
            inferred_carries=int(ch.carry_count.sum()), inferred_carry_m=float(ch.carry_m.sum()),
            long_chain_threats=int(((long.shots > 0) | (long.box > 0)).sum()),
            build_chains=len(build), build_exits=int(build.reached_third.sum()),
            progressive_rate=100*progressive.sum()/max(len(p), 1),
            transition_shot_rate=100*trans/max(len(regains), 1),
            high_regain_rate=100*regains.high_regain.sum()/max(opp_passes, 1),
            long_chain_threat_rate=100*((long.shots > 0) | (long.box > 0)).sum()/max(len(ch), 1),
            lane_low_pct=100*(op.y < 100/3).sum()/max(len(op), 1),
            lane_high_pct=100*(op.y > 200/3).sum()/max(len(op), 1),
            receiver_coverage=(len(links[links.teamId.eq(tid)]) if len(links) else 0)
                              /max(int((success & ~p.restart).sum()), 1))
        rows.append(row)
        touches = g[g.isTouch & g.playerId.notna()]
        for pid, pg in touches.groupby("playerId"):
            positions.append(dict(teamId=tid, playerId=pid, playerName=pg.playerName.iloc[-1],
                x=pg.x.mean(), y=pg.y.mean(), touches=len(pg),
                shots=int(shots_mask(pg).sum()), sot=int(shots_on_target_mask(pg).sum())))
    return pd.DataFrame(rows).merge(ctx, on="teamId"), links, pd.DataFrame(positions)


def build_dataset(root: Path, out: Path, cutoff: str, force=False):
    """Read-only on raw/processed sources; cache is scoped to this report."""
    files = [(s, p) for s in SEASONS for p in sorted(
        (root/"data/raw/whoscored"/LEAGUE/s/"events").glob("*.csv"))]
    metadata = [(s, p.name, p.stat().st_size, p.stat().st_mtime_ns) for s, p in files]
    for s in SEASONS:
        for p in (root/"data/raw/whoscored"/LEAGUE/s/"matches.json",
                  root/"data/processed"/LEAGUE/s/"team_match.parquet"):
            metadata.append((s, str(p), p.stat().st_size, p.stat().st_mtime_ns))
    fingerprint = hashlib.sha256(json.dumps([VERSION, cutoff, metadata]).encode()).hexdigest()
    stamp = out/"dataset_meta.json"
    if not force and stamp.exists() and json.loads(stamp.read_text())["fingerprint"] == fingerprint:
        return tuple(pd.read_parquet(out/f"{name}.parquet") for name in
                     ("dataset", "links", "positions"))
    all_rows, audits, all_links, all_pos = [], [], [], []
    for season in SEASONS:
        tm = pd.read_parquet(root/"data/processed"/LEAGUE/season/"team_match.parquet")
        schedule = json.loads((root/"data/raw/whoscored"/LEAGUE/season/"matches.json").read_text(encoding="utf-8"))
        scores = {int(re.search(r"/matches/(\d+)/", m["url"])[1]): m.get("score")
                  for m in schedule if re.search(r"/matches/(\d+)/", m.get("url", ""))}
        for i, (mid, pair) in enumerate(tm.groupby("matchId")):
            date = pd.Timestamp(pair.date.iloc[0])
            if date >= pd.Timestamp(cutoff):
                continue
            p = root/"data/raw/whoscored"/LEAGUE/season/"events"/f"{mid}.csv"
            e = read_events(p)
            reasons = audit_match(e, scores.get(int(mid)))
            audits.append(dict(season=season, matchId=mid, date=str(date.date()),
                home=pair.loc[pair.is_home.eq(1), "team"].iloc[0],
                away=pair.loc[pair.is_home.eq(0), "team"].iloc[0],
                accepted=not reasons, reasons=";".join(reasons), events=len(e)))
            if reasons:
                continue
            metrics, links, pos = tactical_metrics(e)
            final = parse_score(e.ftScore.dropna().iloc[-1])
            for r in pair.itertuples():
                g = e[e.teamId.eq(r.teamId) & e.period.isin(PERIODS)]
                m = metrics[metrics.teamId.eq(r.teamId)].iloc[0].to_dict()
                all_rows.append(dict(m, season=season, date=date, matchId=mid,
                    team=r.team, opponent=r.opponent, teamId=r.teamId, is_home=r.is_home,
                    goals=final[0 if r.is_home else 1], shots=int(shots_mask(g).sum()),
                    sot=int(shots_on_target_mask(g).sum()), xg_internal=r.xg,
                    cached_shots_delta=int(shots_mask(g).sum())-int(r.shots)))
            if season == SEASONS[-1] and pair.team.isin(["Como", "Inter"]).any():
                names = dict(zip(pair.teamId, pair.team))
                for frame, collector in ((links, all_links), (pos, all_pos)):
                    if len(frame):
                        frame = frame.assign(matchId=mid, date=date, team=frame.teamId.map(names))
                        collector.append(frame[frame.team.isin(["Como", "Inter"])])
            if i % 50 == 0:
                print(f"Dati {season}: {i+1}/{tm.matchId.nunique()}", flush=True)
    data = pd.DataFrame(all_rows).sort_values(["date", "matchId", "is_home"])
    opposite = data[["matchId", "team", "shots", "sot", "goals", "xg_internal",
                     "transition_shots", "high_regains", "box_entries"]].rename(
        columns={"team": "opponent", **{c: f"{c}_against" for c in
            ("shots", "sot", "goals", "xg_internal", "transition_shots", "high_regains", "box_entries")}})
    data = data.merge(opposite, on=["matchId", "opponent"], validate="one_to_one")
    frames = (data, pd.concat(all_links, ignore_index=True), pd.concat(all_pos, ignore_index=True))
    for name, frame in zip(("dataset", "links", "positions"), frames):
        frame.to_parquet(out/f"{name}.parquet", index=False)
    pd.DataFrame(audits).to_csv(out/"audit.csv", index=False)
    stamp.write_text(json.dumps(dict(fingerprint=fingerprint, cutoff=cutoff, version=VERSION,
        matches=int(data.matchId.nunique()), excluded=sum(not x["accepted"] for x in audits)), indent=2))
    return frames


def pre_match_features(data: pd.DataFrame, fixtures: pd.DataFrame, lookback=6) -> pd.DataFrame:
    """Strict date cutoff even when several matches share a date."""
    out = fixtures.copy()
    for side, key in (("att", "team"), ("opp", "opponent")):
        for c in TACTICAL:
            out[f"{side}_{c}"] = np.nan
        for idx, r in fixtures.iterrows():
            past = data[(data.team == r[key]) & (data.date < r.date)].sort_values("date").tail(lookback)
            if len(past) >= 3:
                for c in TACTICAL:
                    out.loc[idx, f"{side}_{c}"] = past[c].mean()
    return out


class TacticalCountModel(TeamModel):
    """Penalise added coefficients too, instead of trusting noisy correlations."""
    def _penalty_mask(self):
        mask = super()._penalty_mask()
        if self.extra:
            mask[-len(self.extra):] = 24.0/self.alpha
        return mask


def fit_predict(train, future, target, variant, alpha, half_life, as_of):
    if variant == "team_mean":
        w = .5 ** ((pd.Timestamp(as_of)-train.date).dt.days.to_numpy()/half_life)
        predictions = []
        for r in future.itertuples():
            field = train.is_home.eq(r.is_home).to_numpy()
            prior = np.average(train.loc[field, target], weights=w[field])
            own = field & train.team.eq(r.team).to_numpy()
            predictions.append((np.dot(w[own], train.loc[own, target])+5*prior)/(w[own].sum()+5))
        return np.asarray(predictions)
    if variant == "season_prior":
        # Previous-season strengths, current-season intercept: a new league
        # level must not be forced to equal last year's level. No future data.
        date = pd.Timestamp(as_of)
        year = date.year if date.month >= 7 else date.year-1
        season = f"{year}-{year+1}"
        old = train[train.season != season]
        current = train[train.season == season]
        previous_season = sorted(old.season.unique())[-1]
        old = old[old.season == previous_season]
        prior_model = TeamModel(alpha=alpha,half_life=half_life,target=target).fit(old,as_of=date)
        if current.matchId.nunique() < 30:
            return prior_model.predict(future)
        rating = prior_model.ratings()
        prior = {r.team:(r.attack-rating.attack.mean(),r.defence-rating.defence.mean())
                 for r in rating.itertuples()}
        teams = sorted(set(current.team)|set(current.opponent)|set(future.team)|set(future.opponent))
        model = TeamModel(alpha=alpha,alpha_prior=alpha,half_life=half_life,target=target,prior=prior)
        return model.fit(current,as_of=date,teams=teams).predict(future)
    model = TacticalCountModel(alpha=alpha, half_life=half_life, target=target,
                               extra=EXTRA if variant == "tactical" else ())
    return model.fit(train, as_of=pd.Timestamp(as_of)).predict(future)


def walk_forward(data, target, variant, alpha, half_life, months):
    pieces = []
    for start in months:
        start = pd.Timestamp(start)
        train = data[data.date < start]
        test = data[(data.date >= start) & (data.date < start+pd.offsets.MonthBegin(1))]
        if test.empty:
            continue
        assert train.date.max() < test.date.min()
        pred = fit_predict(train, test, target, variant, alpha, half_life, start)
        part = test[["matchId", "date", "team", "is_home", target]].copy()
        part["lambda"] = pred
        part["loglik"] = poisson_loglik(part[target].to_numpy(), pred)
        part["train_end"] = train.date.max()
        pieces.append(part)
    return pd.concat(pieces, ignore_index=True)


def paired_evidence(candidate, reference):
    z = candidate.merge(reference, on=["matchId", "team"], suffixes=("_c", "_r"), validate="one_to_one")
    delta = (z.loglik_c-z.loglik_r).groupby(z.matchId).mean()
    se = delta.std(ddof=1)/np.sqrt(len(delta))
    return dict(matches=len(delta), gain=float(delta.mean()),
                se=float(se), z=float(delta.mean()/se) if se > 0 else 0.0)


def evaluate_predictions(p, target, r):
    y = p[target].to_numpy()
    lam = p["lambda"].to_numpy()
    low, high = D.ppf(.1, lam, r), D.ppf(.9, lam, r)
    return dict(matches=int(p.matchId.nunique()), rows=len(p),
        poisson_nll=float(-poisson_loglik(y, lam).mean()),
        nb_nll=float(-D.nb2_loglik(y, lam, r).mean()), mae=float(np.abs(y-lam).mean()),
        calibration_ratio=float(y.sum()/lam.sum()), coverage80=float(((y >= low)&(y <= high)).mean()))


def train_and_validate(data: pd.DataFrame, cutoff: str, match_date: str, out: Path, bootstraps=120):
    data = data[data.date < pd.Timestamp(cutoff)].copy().reset_index(drop=True)
    design = pre_match_features(data, data)
    fixture = pd.DataFrame([dict(team="Inter", opponent="Como", is_home=1, date=pd.Timestamp(cutoff)),
                            dict(team="Como", opponent="Inter", is_home=0, date=pd.Timestamp(cutoff))])
    future = pre_match_features(data, fixture)
    tuning = pd.date_range("2025-08-01", "2026-01-01", freq="MS")
    holdout = pd.date_range("2026-02-01", "2026-05-01", freq="MS")
    current = pd.date_range("2026-08-01", pd.Timestamp(cutoff), freq="MS")
    models, summaries, validation = {}, [], []
    rng = np.random.default_rng(20261106)
    for target in TARGETS:
        print(f"Modelli e validazione: {target}", flush=True)
        candidates = []
        variants = ("team_mean", "base", "season_prior", "tactical")
        for variant in variants:
            for half in (120, 240):
                for alpha in ((6,) if variant == "team_mean" else (3, 12)):
                    p = walk_forward(design, target, variant, alpha, half, tuning)
                    candidates.append((p.loglik.mean(), variant, alpha, half, p))
        best = {v: max([x for x in candidates if x[1] == v], key=lambda x:x[0])
                for v in variants}
        ref = max((best["team_mean"], best["base"], best["season_prior"]), key=lambda x:x[0])
        ev = paired_evidence(best["tactical"][4], ref[4])
        # Predeclared conservative threshold for four targets; development evidence only.
        chosen = best["tactical"] if ev["z"] > 2.50 and ev["matches"] >= 100 else ref
        _, variant, alpha, half, dev = chosen
        r = D.fit_r(dev[target].to_numpy(), dev["lambda"].to_numpy())
        for label, months in (("development", tuning), ("holdout_2026", holdout), ("current_2026_27", current)):
            for kind in variants:
                _, _, ca, ch, _ = best[kind]
                p = walk_forward(design, target, kind, ca, ch, months)
                rr = D.fit_r(best[kind][4][target].to_numpy(), best[kind][4]["lambda"].to_numpy())
                summaries.append(dict(target=target, period=label, variant=kind,
                    selected=kind == variant, alpha=ca, half_life=ch,
                    **evaluate_predictions(p, target, rr)))
                p = p.rename(columns={target:"observed"}).assign(target=target, period=label, variant=kind)
                validation.append(p)
        lam = fit_predict(design, future, target, variant, alpha, half, match_date)
        dates = design.date.unique()
        groups = {date:design[design.date.eq(date)] for date in dates}
        boots = []
        for _ in range(bootstraps):
            sampled = pd.concat([groups[date] for date in rng.choice(dates, size=len(dates), replace=True)], ignore_index=True)
            boots.append(fit_predict(sampled, future, target, variant, alpha, half, match_date))
        boots = np.asarray(boots)
        model = dict(variant=variant, alpha=alpha, half_life=half, r=r,
            tactical_development_evidence=ev, lambda_home=float(lam[0]), lambda_away=float(lam[1]),
            parameter_sensitivity80=np.quantile(boots,[.1,.9],axis=0).tolist(),
            bootstrap_lambdas=boots.tolist(), count80=[], overs={})
        # Mixture of predictive distributions, including approximate fitted-mean uncertainty.
        limit = 1600 if target == "passes" else 120 if target == "shots" else 40
        grid = np.arange(limit+1)
        for side in (0,1):
            cdf = stats.nbinom.cdf(grid[:,None], r, r/(r+boots[:,side])).mean(axis=1)
            model["count80"].append([int(np.searchsorted(cdf,.1)),int(np.searchsorted(cdf,.9))])
        lines = {"goals":[.5,1.5,2.5],"shots":[8.5,10.5,12.5,14.5,16.5],
                 "sot":[1.5,2.5,3.5,4.5,5.5],"passes":[350.5,450.5,550.5]}[target]
        for line in lines:
            model["overs"][str(line)] = [float(D.p_over(boots[:,i],line,r).mean()) for i in (0,1)]
        models[target] = model
    pd.DataFrame(summaries).to_csv(out/"validation_summary.csv",index=False)
    validation_frame = pd.concat(validation)
    validation_frame.to_parquet(out/"validation_predictions.parquet",index=False)
    validate_outcomes(validation_frame, data, models["goals"]).to_csv(out/"outcome_validation.csv",index=False)
    models["outcomes"] = outcome_distribution(models["goals"])
    return models


def validate_outcomes(predictions, data, goal_model):
    """Evaluate the result distribution separately from the goal marginals."""
    g = predictions[(predictions.target == "goals") & (predictions.variant == goal_model["variant"])]
    records = []
    grid = np.arange(31)
    r = goal_model["r"]
    for period, p in g.groupby("period"):
        p = p[p.is_home.eq(1)][["matchId","date","lambda","observed"]].merge(
            p[p.is_home.eq(0)][["matchId","lambda","observed"]],on="matchId",suffixes=("_h","_a"))
        logloss, brier, baseline_ll, baseline_brier = [], [], [], []
        actual, forecasts = [], []
        for row in p.itertuples():
            ph = stats.nbinom.pmf(grid,r,r/(r+row.lambda_h))
            pa = stats.nbinom.pmf(grid,r,r/(r+row.lambda_a))
            joint = np.outer(ph,pa);joint /= joint.sum()
            probs = np.array([np.tril(joint,-1).sum(),np.trace(joint),np.triu(joint,1).sum()])
            result = 0 if row.observed_h > row.observed_a else 1 if row.observed_h == row.observed_a else 2
            onehot = np.eye(3)[result]
            cutoff = pd.Timestamp(row.date).replace(day=1)
            past = data[(data.date < cutoff)&data.is_home.eq(1)]
            outcome = np.where(past.goals>past.goals_against,0,np.where(past.goals==past.goals_against,1,2))
            base = (np.bincount(outcome,minlength=3)+1)/(len(outcome)+3)
            logloss.append(-np.log(max(probs[result],1e-12))); brier.append(np.square(probs-onehot).sum())
            baseline_ll.append(-np.log(base[result]));baseline_brier.append(np.square(base-onehot).sum())
            actual.append(onehot);forecasts.append(probs)
        records.append(dict(period=period,matches=len(p),logloss=np.mean(logloss),brier=np.mean(brier),
            baseline_logloss=np.mean(baseline_ll),baseline_brier=np.mean(baseline_brier),
            predicted_home=np.mean(forecasts,axis=0)[0],observed_home=np.mean(actual,axis=0)[0],
            predicted_draw=np.mean(forecasts,axis=0)[1],observed_draw=np.mean(actual,axis=0)[1]))
    return pd.DataFrame(records)


def outcome_distribution(goals):
    """Conditional independence, explicitly an assumption; no fabricated correlation."""
    means = np.asarray(goals["bootstrap_lambdas"])
    r = goals["r"]
    grid = np.arange(31)
    joint = np.zeros((31,31))
    for home, away in means:
        joint += np.outer(stats.nbinom.pmf(grid,r,r/(r+home)),stats.nbinom.pmf(grid,r,r/(r+away)))
    joint /= len(means)
    mass = joint.sum()
    joint /= mass
    ix = np.indices(joint.shape)
    best = np.argsort(joint.ravel())[-6:][::-1]
    return dict(home=float(np.tril(joint,-1).sum()),draw=float(np.trace(joint)),
        away=float(np.triu(joint,1).sum()),both_score=float(joint[1:,1:].sum()),
        over25=float(joint[(ix[0]+ix[1])>=3].sum()),truncated_mass=float(1-mass),
        scorelines=[dict(score=f"{k//31}-{k%31}",probability=float(joint.ravel()[k])) for k in best],
        assumption="Indipendenza condizionata dei gol; bootstrap appaiato per data. Nessuna correzione Dixon-Coles stimata.")
