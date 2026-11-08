"""Critical boundaries: leakage, incomplete games, inferred receivers and restarts."""
import numpy as np
import pandas as pd
import pytest

from sot import tactical_matchup as T


def events(rows):
    defaults=dict(teamId=1,playerId=11,playerName="A",period="FirstHalf",minute=0,
        second=0,clock=0,x=30.,y=50.,endX=40.,endY=50.,outcomeType="Successful",
        isShot=False,isOwnGoal=False,keeperSaveTotal=False,restart=False)
    return pd.DataFrame([dict(defaults,**r) for r in rows])


def test_receiver_must_follow_same_team_near_endpoint():
    e=events([dict(type="Pass"),dict(type="Pass",clock=2,playerId=12,playerName="B",x=40.),
              dict(type="Pass",clock=4,playerId=13,playerName="C",x=90.)])
    _,links=T.event_chains(e)
    assert len(links)==1
    assert links.iloc[0].receiver==12


@pytest.mark.parametrize("middle",[
    dict(type="Foul",clock=1),dict(type="Pass",clock=1,teamId=2),
    dict(type="CornerAwarded",clock=1)])
def test_receiver_cannot_jump_over_opponent_or_stoppage(middle):
    _,links=T.event_chains(events([dict(type="Pass"),middle,
        dict(type="Pass",clock=3,playerId=12,x=40.)]))
    assert len(links)==0


def test_restart_and_period_change_are_not_pass_links():
    for modified in [dict(restart=True),dict(period="SecondHalf")]:
        _,links=T.event_chains(events([dict(type="Pass"),
            dict(type="Pass",clock=2,playerId=12,x=40.,**modified)]))
        assert len(links)==0


def test_transition_window_and_restart_barrier():
    e=events([dict(type="BallRecovery",x=70.),dict(type="Pass",clock=2),
              dict(type="SavedShot",clock=9,isShot=True)])
    ch,_=T.event_chains(e)
    assert ch.transition_shots.sum()==1
    assert ch.high_regain.sum()==1
    e.loc[2,"clock"]=11
    ch,_=T.event_chains(e)
    assert ch.transition_shots.sum()==0
    e=events([dict(type="BallRecovery"),dict(type="Foul",clock=1),
              dict(type="SavedShot",clock=3,isShot=True)])
    ch,_=T.event_chains(e)
    assert ch.transition_shots.sum()==0


def test_failed_pass_breaks_chain():
    e=events([dict(type="BallRecovery"),dict(type="Pass",clock=2,outcomeType="Unsuccessful"),
              dict(type="SavedShot",clock=4,isShot=True)])
    ch,_=T.event_chains(e)
    assert ch.transition_shots.sum()==0


def test_features_exclude_same_date_and_future_even_if_mutated():
    d=pd.DataFrame([dict(team=t,date=pd.Timestamp(f"2026-01-{day:02}"),
        **{c:float(day) for c in T.TACTICAL}) for t in ["A","B"] for day in range(1,8)])
    f=pd.DataFrame([dict(team="A",opponent="B",date=pd.Timestamp("2026-01-05"))])
    before=T.pre_match_features(d,f)
    d.loc[d.date>=f.date.iloc[0],list(T.TACTICAL)]=9999
    after=T.pre_match_features(d,f)
    pd.testing.assert_frame_equal(before,after)
    assert before.att_progressive_rate.iloc[0]==2.5


def test_incomplete_and_wrong_final_score_are_rejected():
    e=pd.DataFrame(dict(ftScore=["2 : 1","2 : 1"],type=["End","End"],
        period=["FirstHalf","SecondHalf"],minute=[47,94],teamId=[1,2],h_a=["h","a"]))
    assert T.audit_match(e,"2:1")==[]
    assert "risultato_diverso_dal_calendario" in T.audit_match(e,"2:2")
    e["ftScore"]=np.nan
    assert "risultato_finale_assente" in T.audit_match(e)
    e.loc[1,"minute"]=70
    assert "fine_partita_non_documentata" in T.audit_match(e)


def test_result_probabilities_normalized_and_orientation_correct():
    d=T.outcome_distribution(dict(bootstrap_lambdas=[[2.,.7]]*20,r=50.))
    assert d["home"]>d["away"]
    assert d["home"]+d["draw"]+d["away"]==pytest.approx(1)
    assert 0<d["both_score"]<1
    assert d["truncated_mass"]<1e-8


def test_added_coefficients_are_penalized():
    model=T.TacticalCountModel(alpha=3,extra=T.EXTRA)
    model.teams_=["A","B"]
    penalty=model._penalty_mask()
    assert penalty[0]==0
    assert np.all(penalty[-len(T.EXTRA):]==8)


def test_fit_responds_to_opponent_strength():
    rng=np.random.default_rng(7)
    rows=[]
    for i in range(120):
        for t,o,home in [("A","B",1),("B","A",0)]:
            rows.append(dict(team=t,opponent=o,is_home=home,date=pd.Timestamp("2025-01-01")+pd.Timedelta(days=i),
                goals=int(rng.poisson(2.5 if t=="A" else .5))))
    train=pd.DataFrame(rows)
    f=pd.DataFrame([dict(team="A",opponent="B",is_home=1),dict(team="B",opponent="A",is_home=0)])
    p=T.fit_predict(train,f,"goals","base",3,120,"2025-05-01")
    assert p[0]>p[1]>0


def test_season_prior_adapts_league_level_and_falls_back_before_30_games():
    rows=[]
    for season,start,level,n in [("2024-2025","2025-01-01",1,40),
                                  ("2025-2026","2025-08-01",4,40)]:
        for i in range(n):
            for team,opponent,home in [("A","B",1),("B","A",0)]:
                rows.append(dict(season=season,matchId=f"{season}-{i}",team=team,
                    opponent=opponent,is_home=home,goals=level,
                    date=pd.Timestamp(start)+pd.Timedelta(days=i)))
    train=pd.DataFrame(rows)
    fixture=pd.DataFrame([dict(team="A",opponent="B",is_home=1),
                          dict(team="B",opponent="A",is_home=0)])
    adapted=T.fit_predict(train,fixture,"goals","season_prior",3,120,"2025-10-01")
    assert np.allclose(adapted,4,atol=.05)
    early=train[(train.season=="2024-2025")|(train.date<pd.Timestamp("2025-08-20"))]
    fallback=T.fit_predict(early,fixture,"goals","season_prior",3,120,"2025-08-20")
    assert np.allclose(fallback,1,atol=.05)
