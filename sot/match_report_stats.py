"""Extended, auditable pre-match box score; no bookmaker settlement assumptions.

Counts are selected on Aug 2025-Jan 2026, tested on Feb-May 2026. Conditional
subcounts preserve their parents. All extraction uses the accepted-match audit.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

from . import dispersion as D
from . import tactical_matchup as T
from .shots import shots_mask, shots_on_target_mask

VERSION = 1
MODEL_VERSION = 2
# key: label, group, operational definition
SPECS = {
    "goals": ("Gol", "Attacco", "Risultato finale, inclusi gli autogol."),
    "shots": ("Tiri totali", "Attacco", "Tentativi, esclusi gli autogol."),
    "sot": ("Tiri in porta", "Attacco", "Gol regolari e tiri parati; esclusi blocchi e pali senza gol."),
    "shots_offtarget": ("Tiri fuori, inclusi i pali", "Attacco", "Tiri non in porta e non bloccati. I pali sono un sottoinsieme."),
    "shots_blocked": ("Tiri bloccati dai difensori", "Attacco", "Tentativi con flag shotBlocked, esclusi i tiri in porta."),
    "shots_box": ("Tiri da dentro l’area", "Attacco", "Coordinate del tiro nell’area di rigore, inclusi i rigori."),
    "shots_outside": ("Tiri da fuori area", "Attacco", "Complemento dei tiri da dentro l’area."),
    "woodwork": ("Pali e traverse senza gol", "Attacco", "Eventi ShotOnPost: non tutti i contatti col legno dopo una deviazione."),
    "big_chances": ("Grandi occasioni", "Attacco", "Tiri con flag bigChanceMissed o bigChanceScored del fornitore."),
    "penalty_shots": ("Rigori calciati", "Attacco", "Tentativi con qualificatore Penalty; esclusi spareggi ai rigori."),
    "corners": ("Calci d’angolo ottenuti", "Palle ferme e disciplina", "CornerAwarded Successful: il gemello concesso non viene contato."),
    "fouls": ("Falli commessi", "Palle ferme e disciplina", "Foul con flag foulCommitted: esclusa la copia della squadra che subisce."),
    "offsides": ("Fuorigioco", "Palle ferme e disciplina", "Solo eventi OffsideGiven, non OffsidePass o OffsideProvoked."),
    "yellow_cards": ("Ammonizioni", "Palle ferme e disciplina", "Yellow e SecondYellow, escluse ammonizioni annullate. Non sono punti-cartellino."),
    "red_cards": ("Espulsioni", "Palle ferme e disciplina", "Red e SecondYellow. Il secondo giallo compare anche fra le ammonizioni."),
    "throwins": ("Rimesse laterali", "Palle ferme e disciplina", "Passaggi con qualificatore/flag ThrowIn."),
    "passes": ("Passaggi tentati", "Costruzione", "Eventi Pass, incluse le rimesse annotate come passaggio."),
    "passes_complete": ("Passaggi riusciti", "Costruzione", "Eventi Pass Successful; stessa base dei passaggi tentati."),
    "crosses": ("Cross tentati", "Costruzione", "passCrossAccurate o passCrossInaccurate; incluse palle ferme marcate come cross."),
    "crosses_complete": ("Cross riusciti", "Costruzione", "Cross con flag passCrossAccurate."),
    "long_balls": ("Lanci lunghi", "Costruzione", "Flag passLongBallAccurate o passLongBallInaccurate del fornitore."),
    "long_balls_complete": ("Lanci lunghi riusciti", "Costruzione", "Flag passLongBallAccurate."),
    "throughballs": ("Passaggi filtranti", "Costruzione", "Flag passThroughBallAccurate o le varianti Inaccurate/Inacurate."),
    "keypasses": ("Passaggi chiave", "Costruzione", "Flag passKey; la definizione non include automaticamente gli assist."),
    "touches": ("Tocchi registrati", "Costruzione", "Numero di eventi isTouch; non ogni contatto fisico con il pallone."),
    "saves": ("Parate del portiere", "Difesa e duelli", "Save con keeperSaveTotal; esclusi blocchi dei giocatori di movimento."),
    "tackles": ("Contrasti effettuati", "Difesa e duelli", "Eventi Tackle, riusciti e non; non include tutti i duelli a terra."),
    "tackles_won": ("Contrasti vinti", "Difesa e duelli", "Tackle Successful; sottoinsieme dei contrasti effettuati."),
    "interceptions": ("Intercetti", "Difesa e duelli", "Interception Successful."),
    "clearances": ("Respinte difensive", "Difesa e duelli", "Eventi Clearance."),
    "ball_recoveries": ("Recuperi palla", "Difesa e duelli", "Eventi BallRecovery; diversi dai recuperi di inizio catena del dossier tattico."),
    "dribbles": ("Dribbling tentati", "Difesa e duelli", "Eventi TakeOn."),
    "dribbles_won": ("Dribbling riusciti", "Difesa e duelli", "TakeOn Successful."),
    "aerial_duels": ("Duelli aerei disputati", "Difesa e duelli", "Eventi Aerial per squadra; lo stesso duello è osservato da entrambe le parti."),
    "aerial_won": ("Duelli aerei vinti", "Difesa e duelli", "Aerial Successful."),
    "aerial_lost": ("Duelli aerei persi", "Difesa e duelli", "Complemento dei duelli aerei vinti."),
    "dispossessed": ("Palloni sottratti in duello", "Difesa e duelli", "Eventi Dispossessed; non equivale a tutti i palloni persi."),
}
RATIOS = {
    "shots_blocked": "non_sot", "woodwork": "shots_offtarget", "shots_box": "shots",
    "passes_complete": "passes", "crosses_complete": "crosses", "long_balls_complete": "long_balls",
    "dribbles_won": "dribbles", "tackles_won": "tackles", "aerial_won": "aerial_duels",
}
COMPLEMENTS = {"shots_offtarget": ("non_sot", "shots_blocked"),
               "shots_outside": ("shots", "shots_box"), "aerial_lost": ("aerial_duels", "aerial_won")}
ORIGINAL = ("goals", "shots", "sot", "passes")
COUNTS = tuple(k for k in SPECS if k not in ORIGINAL and k not in RATIOS and k not in COMPLEMENTS)
FLAGS = {
    "isShot", "isGoal", "isTouch", "shotBlocked", "goalOwn", "isOwnGoal", "keeperSaveTotal",
    "foulCommitted", "voidYellowCard", "passCrossAccurate", "passCrossInaccurate",
    "passLongBallAccurate", "passLongBallInaccurate", "passThroughBallAccurate",
    "passThroughBallInaccurate", "passThroughBallInacurate", "passKey", "throwIn",
    "bigChanceMissed", "bigChanceScored",
}
COLS = FLAGS | {"type", "outcomeType", "teamId", "period", "cardType", "qualifiers", "x", "y"}


def flag(e, name):
    """Missing optional flag is false; strings such as 'False' are not truthy."""
    s = e.get(name, pd.Series(False, index=e.index))
    return s.fillna(False).astype(str).str.lower().isin(["true", "1", "1.0"])


def extract(e):
    e = e[e.period.isin(T.PERIODS)].copy()
    e["isOwnGoal"] = flag(e, "isOwnGoal") | flag(e, "goalOwn")
    for c in ("isShot", "shotBlocked"):
        e[c] = flag(e, c)
    records = []
    for tid,g in e.groupby("teamId"):
        good = g.outcomeType.eq("Successful")
        shot = shots_mask(g); sot = shots_on_target_mask(g)
        blocked = shot & flag(g,"shotBlocked") & ~sot
        off = shot & ~sot & ~blocked
        pas = g.type.eq("Pass")
        q = g.qualifiers.fillna("")
        card = g.type.eq("Card") & ~flag(g,"voidYellowCard")
        ct = g.cardType.astype(str)
        masks = {
            "shots":shot,"sot":sot,"non_sot":shot & ~sot,
            "shots_blocked":blocked,"shots_offtarget":off,
            "shots_box":shot & T.in_box(g.x,g.y),
            "woodwork":off & g.type.eq("ShotOnPost"),
            "big_chances":shot & (flag(g,"bigChanceMissed")|flag(g,"bigChanceScored")),
            "penalty_shots":shot & q.str.contains("'type': 'Penalty'",regex=False),
            "corners":g.type.eq("CornerAwarded") & good,
            "fouls":g.type.eq("Foul") & flag(g,"foulCommitted"),
            "offsides":g.type.eq("OffsideGiven"),
            "yellow_cards":card & ct.isin(["Yellow","SecondYellow"]),
            "red_cards":card & ct.isin(["Red","SecondYellow"]),
            "throwins":pas & (flag(g,"throwIn")|q.str.contains("'type': 'ThrowIn'",regex=False)),
            "passes":pas,"passes_complete":pas & good,
            "crosses":pas & (flag(g,"passCrossAccurate")|flag(g,"passCrossInaccurate")),
            "crosses_complete":pas & flag(g,"passCrossAccurate"),
            "long_balls":pas & (flag(g,"passLongBallAccurate")|flag(g,"passLongBallInaccurate")),
            "long_balls_complete":pas & flag(g,"passLongBallAccurate"),
            "throughballs":pas & (flag(g,"passThroughBallAccurate")|flag(g,"passThroughBallInaccurate")|flag(g,"passThroughBallInacurate")),
            "keypasses":pas & flag(g,"passKey"),"touches":flag(g,"isTouch"),
            "saves":g.type.eq("Save") & flag(g,"keeperSaveTotal"),
            "tackles":g.type.eq("Tackle"),"tackles_won":g.type.eq("Tackle") & good,
            "interceptions":g.type.eq("Interception") & good,
            "clearances":g.type.eq("Clearance"),"ball_recoveries":g.type.eq("BallRecovery"),
            "dribbles":g.type.eq("TakeOn"),"dribbles_won":g.type.eq("TakeOn") & good,
            "aerial_duels":g.type.eq("Aerial"),"aerial_won":g.type.eq("Aerial") & good,
            "dispossessed":g.type.eq("Dispossessed"),
        }
        r = {k:int(m.sum()) for k,m in masks.items()}
        r.update(teamId=tid, shots_outside=r["shots"]-r["shots_box"],
                 aerial_lost=r["aerial_duels"]-r["aerial_won"])
        records.append(r)
    return pd.DataFrame(records)


def build(root: Path, out: Path):
    audit = pd.read_csv(out/"audit.csv")
    audit = audit[audit.accepted]
    files = [root/"data/raw/whoscored"/T.LEAGUE/r.season/"events"/f"{r.matchId}.csv" for r in audit.itertuples()]
    stamp = hashlib.sha256(json.dumps([VERSION,[(str(p),p.stat().st_size,p.stat().st_mtime_ns) for p in files]]).encode()).hexdigest()
    meta = out/"extended_dataset_meta.json"
    if meta.exists() and json.loads(meta.read_text())["fingerprint"] == stamp:
        return pd.read_parquet(out/"extended_dataset.parquet"),stamp
    all_rows=[]
    # Required annotation families: fail explicitly instead of treating missing data as zero.
    required = COLS - {"isOwnGoal","passThroughBallInaccurate","passThroughBallInacurate"}
    for i,(r,p) in enumerate(zip(audit.itertuples(),files)):
        e=pd.read_csv(p,usecols=lambda c:c in COLS,low_memory=False)
        missing=required-set(e.columns)
        if missing:raise ValueError(f"{p.name}: annotazioni mancanti {sorted(missing)}")
        all_rows.append(extract(e).assign(matchId=r.matchId))
        if i%100==0:print(f"Statistiche estese: {i+1}/{len(files)}",flush=True)
    counts=pd.concat(all_rows,ignore_index=True)
    base=pd.read_parquet(out/"dataset.parquet")
    merged=base[["matchId","teamId","team","opponent","is_home","date","season","goals"]].merge(
        counts,on=["matchId","teamId"],validate="one_to_one")
    for c in ("shots","sot","passes"):
        check=base[["matchId","teamId",c]].merge(merged[["matchId","teamId",c]],on=["matchId","teamId"],suffixes=("_old","_new"))
        if not np.array_equal(check[f"{c}_old"].to_numpy(),check[f"{c}_new"].to_numpy()):
            raise ValueError(f"La definizione estesa di {c} non coincide col dossier originale")
    for child,parent in RATIOS.items():
        if not (merged[child] <= merged[parent]).all():raise ValueError(f"{child} supera {parent}")
    merged.to_parquet(out/"extended_dataset.parquet",index=False)
    meta.write_text(json.dumps(dict(fingerprint=stamp,version=VERSION,matches=len(audit)),indent=2))
    return merged,stamp


def conditional_rate(train,future,child,parent,as_of,half_life=240,prior_exposure=100):
    """Shrunk attacking and opponent-conceding fractions; no future information."""
    train=train[train.date < pd.Timestamp(as_of)]
    w=.5**((pd.Timestamp(as_of)-train.date).dt.days.to_numpy()/half_life)
    exposure=np.dot(w,train[parent]);success=np.dot(w,train[child])
    league=(success+.5)/(exposure+1)
    result=[]
    for row in future.itertuples():
        ps=[]
        for mask in (train.team.eq(row.team).to_numpy(),train.opponent.eq(row.opponent).to_numpy()):
            ps.append((np.dot(w[mask],train.loc[mask,child])+prior_exposure*league)/
                      (np.dot(w[mask],train.loc[mask,parent])+prior_exposure))
        result.append(float(np.clip(np.mean(ps),0,1)))
    return np.array(result)


def residual_correlation(p):
    z=p.assign(residual=(p.observed-p["lambda"])/np.sqrt(p["lambda"].clip(lower=.01)))
    pair=z.pivot(index="matchId",columns="is_home",values="residual").dropna()
    if len(pair)<30 or pair[0].std()==0 or pair[1].std()==0:return 0.
    rho=stats.spearmanr(pair[0],pair[1]).statistic
    return float(np.clip(2*np.sin(np.pi*rho/6),-.7,.7)) if np.isfinite(rho) else 0.


def draw_counts(model,rng,n=30000):
    # Copula correlation is fitted on development residuals only. Marginal
    # intervals are validated; total intervals remain an explicit approximation.
    rho=model.get("rho",0.)
    z=rng.multivariate_normal([0,0],[[1,rho],[rho,1]],size=n)
    u=np.clip(stats.norm.cdf(z),1e-9,1-1e-9)
    if "bootstrap_lambdas" in model:
        boot=np.array(model["bootstrap_lambdas"])
        lam=boot[rng.integers(0,len(boot),n)]
    else:lam=np.broadcast_to([model["lambda_home"],model["lambda_away"]],(n,2))
    r=model["r"]
    return stats.nbinom.ppf(u,r,r/(r+lam)).astype(int)


def fit_all(data,out,original,stamp):
    signature=hashlib.sha256(json.dumps([MODEL_VERSION,stamp,original],sort_keys=True).encode()).hexdigest()
    dest=out/"extended_forecast.json"
    if dest.exists():
        saved=json.loads(dest.read_text(encoding="utf-8"))
        if saved.get("signature")==signature:return saved
    cutoff=original["cutoff"];match_date=original["match_date"]
    data=data[data.date<pd.Timestamp(cutoff)].copy()
    future=pd.DataFrame([dict(team="Inter",opponent="Como",is_home=1),dict(team="Como",opponent="Inter",is_home=0)])
    months={"development":pd.date_range("2025-08-01","2026-01-01",freq="MS"),
            "holdout_2026":pd.date_range("2026-02-01","2026-05-01",freq="MS"),
            "current_2026_27":pd.date_range("2026-08-01",cutoff,freq="MS")}
    model={k:dict(original["models"][k]) for k in ORIGINAL}
    old=pd.read_parquet(out/"validation_predictions.parquet")
    selected_parts=[];summaries=[]
    for k in ORIGINAL:
        p=old[(old.target==k)&(old.variant==model[k]["variant"])].copy()
        selected_parts.append(p)
        # Keep the original goal independence assumption and 1X2 probabilities.
        model[k]["rho"]=0. if k=="goals" else residual_correlation(p[p.period.eq("development")])
        model[k]["method"]="Modello del dossier originale"
    for i,k in enumerate(COUNTS):
        print(f"Modello statistiche {i+1}/{len(COUNTS)}: {k}",flush=True)
        candidates=[]
        for variant in ("team_mean","base","season_prior"):
            p=T.walk_forward(data,k,variant,12,240,months["development"])
            candidates.append((p.loglik.mean(),variant,p))
        _,variant,dev=max(candidates,key=lambda x:x[0])
        r=D.fit_r(dev[k].to_numpy(),dev["lambda"].to_numpy())
        parts=[]
        for period,m in months.items():
            p=dev if period=="development" else T.walk_forward(data,k,variant,12,240,m)
            summary=T.evaluate_predictions(p,k,r)
            baseline=T.walk_forward(data,k,"team_mean",12,240,m)
            b=T.evaluate_predictions(baseline,k,r)
            summaries.append(dict(target=k,period=period,variant=variant,baseline_mae=b["mae"],
                baseline_poisson_nll=b["poisson_nll"],**summary))
            parts.append(p.rename(columns={k:"observed"}).assign(target=k,period=period,variant=variant))
        p=pd.concat(parts,ignore_index=True);selected_parts.append(p)
        lam=T.fit_predict(data,future,k,variant,12,240,match_date)
        model[k]=dict(variant=variant,lambda_home=float(lam[0]),lambda_away=float(lam[1]),r=float(r),
            rho=residual_correlation(p[p.period.eq("development")]),method="Conteggio con test temporale")
    predictions=pd.concat(selected_parts,ignore_index=True)
    predictions.to_parquet(out/"extended_count_predictions.parquet",index=False)
    validation=pd.DataFrame(summaries)
    validation.to_csv(out/"extended_validation.csv",index=False)
    rng=np.random.default_rng(20261108)
    draws={k:draw_counts(v,rng) for k,v in model.items()}
    means={k:np.array([v["lambda_home"],v["lambda_away"]]) for k,v in model.items()}
    # Keep original independently validated SOT prediction. For the descriptive
    # partition only, thin total shots to its expected non-SOT fraction.
    non_ratio=np.clip(1-means["sot"]/means["shots"],0,1)
    means["non_sot"]=means["shots"]*non_ratio
    draws["non_sot"]=rng.binomial(draws["shots"],non_ratio)
    for child,parent in RATIOS.items():
        rate=conditional_rate(data,future,child,parent,cutoff)
        means[child]=means[parent]*rate
        draws[child]=rng.binomial(draws[parent],rate)
        for comp,(whole,part) in COMPLEMENTS.items():
            if part==child:
                means[comp]=means[whole]-means[part]
                draws[comp]=draws[whole]-draws[part]
    # Test conditional predictions out of time too; intervals below retain fixed
    # rates and are indicative (not a beta-binomial confidence claim).
    ratio_valid=[]
    for period,mo in months.items():
        for start in mo:
            test=data[(data.date>=start)&(data.date<start+pd.offsets.MonthBegin(1))].copy()
            if test.empty:continue
            pp=predictions[(predictions.period==period)&predictions.date.ge(start)&predictions.date.lt(start+pd.offsets.MonthBegin(1))]
            pred=test[["matchId","team","opponent","is_home","date"]].copy()
            for k in ORIGINAL+COUNTS:
                v=pp[pp.target.eq(k)][["matchId","team","lambda"]].rename(columns={"lambda":k})
                pred=pred.merge(v,on=["matchId","team"],validate="one_to_one")
            pred["non_sot"]=(pred.shots-pred.sot).clip(lower=0)
            for child,parent in RATIOS.items():
                pred[child]=pred[parent]*conditional_rate(data,pred,child,parent,start)
                for comp,(whole,part) in COMPLEMENTS.items():
                    if part==child:pred[comp]=pred[whole]-pred[part]
            for k in (*RATIOS,*COMPLEMENTS):
                p=pred[["matchId","team",k]].merge(test[["matchId","team",k]],on=["matchId","team"],suffixes=("_pred","_obs"))
                ratio_valid.append(p.assign(target=k,period=period).rename(columns={f"{k}_pred":"lambda",f"{k}_obs":"observed"}))
    rv=pd.concat(ratio_valid,ignore_index=True)
    rv.to_parquet(out/"extended_conditional_predictions.parquet",index=False)
    cond=[]
    for (k,period),p in rv.groupby(["target","period"]):
        cond.append(dict(target=k,period=period,matches=p.matchId.nunique(),mae=float(abs(p.observed-p["lambda"]).mean()),
            calibration_ratio=float(p.observed.sum()/max(p["lambda"].sum(),1e-9))))
    cv=pd.DataFrame(cond);cv.to_csv(out/"extended_conditional_validation.csv",index=False)
    rows=[]
    original_v=pd.read_csv(out/"validation_summary.csv")
    for k,(label,group,definition) in SPECS.items():
        d=draws[k];mu=means[k]
        if k in ORIGINAL:
            v=original_v[(original_v.target==k)&original_v.selected]
        elif k in model:v=validation[validation.target==k]
        else:v=cv[cv.target==k]
        h=v[v.period.eq("holdout_2026")].iloc[0];cur=v[v.period.eq("current_2026_27")].iloc[0]
        intervals=model[k]["count80"] if k in ORIGINAL else np.quantile(d,[.1,.9],axis=0).astype(int).T.tolist()
        rows.append(dict(key=k,label=label,group=group,definition=definition,
            mean=mu.tolist(),interval80=intervals,
            total_mean=float(mu.sum()),total_interval80=np.quantile(d.sum(axis=1),[.1,.9]).astype(int).tolist(),
            probability_at_least_one=(d>0).mean(axis=0).tolist(),
            total_probability_at_least_one=float((d.sum(axis=1)>0).mean()),
            method=model[k]["method"] if k in model else "Quota condizionata al conteggio principale",
            variant=model.get(k,{}).get("variant","conditional"),
            holdout_mae=float(h.mae),current_calibration=float(cur.calibration_ratio),
            current_coverage80=float(cur.coverage80) if "coverage80" in cur.index else None,
            interval_kind="marginale" if k in model else "indicativo; quota fissa",
            baseline_mae=float(h.baseline_mae) if "baseline_mae" in h.index else None))
    possession=100*draws["touches"][:,0]/np.maximum(draws["touches"].sum(axis=1),1)
    possession_mean=100*means["touches"]/means["touches"].sum()
    rates=dict(possession_proxy=dict(mean=possession_mean.tolist(),interval80=[np.quantile(possession,[.1,.9]).tolist(),np.quantile(100-possession,[.1,.9]).tolist()]),
        pass_accuracy=dict(mean=(100*means["passes_complete"]/means["passes"]).tolist()),
        shot_accuracy=dict(mean=(100*means["sot"]/means["shots"]).tolist()))
    saved=dict(version=MODEL_VERSION,signature=signature,cutoff=cutoff,match_date=match_date,
        matches=int(data.matchId.nunique()),simulation_draws=30000,rows=rows,rates=rates,
        count_models=model,original_outcomes=original["models"]["outcomes"])
    dest.write_text(json.dumps(saved,ensure_ascii=False,indent=2),encoding="utf-8")
    pd.DataFrame([{k:v for k,v in r.items() if k not in ("mean","interval80","probability_at_least_one")}
        |dict(inter=r["mean"][0],como=r["mean"][1],inter_low=r["interval80"][0][0],inter_high=r["interval80"][0][1],
              como_low=r["interval80"][1][0],como_high=r["interval80"][1][1]) for r in rows]).to_csv(out/"extended_forecast.csv",index=False)
    return saved
