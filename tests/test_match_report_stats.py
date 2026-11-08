import numpy as np
import pandas as pd
import pytest

from sot import match_report_stats as M


def events(rows):
    defaults=dict(teamId=1,period="FirstHalf",type="Pass",outcomeType="Successful",
        isShot=False,shotBlocked=False,cardType=False,qualifiers="[]",x=40.,y=50.)
    return pd.DataFrame([dict(defaults,**row) for row in rows])


def test_corner_and_foul_mirror_events_not_counted_twice():
    e=events([dict(type="CornerAwarded"),dict(type="CornerAwarded",teamId=2,outcomeType="Unsuccessful"),
              dict(type="Foul",foulCommitted=False),dict(type="Foul",teamId=2,outcomeType="Unsuccessful",foulCommitted=True)])
    r=M.extract(e).set_index("teamId")
    assert r.corners.sum()==1 and r.loc[1,"corners"]==1
    assert r.fouls.sum()==1 and r.loc[2,"fouls"]==1


def test_keeper_saves_exclude_outfield_blocks_and_false_strings():
    e=events([dict(type="Save",keeperSaveTotal="True"),dict(type="Save",keeperSaveTotal="False")])
    assert M.extract(e).saves.iloc[0]==1


def test_second_yellow_is_a_yellow_and_dismissal_but_void_is_neither():
    e=events([dict(type="Card",cardType="Yellow"),dict(type="Card",cardType="SecondYellow"),
              dict(type="Card",cardType="Yellow",voidYellowCard=True),dict(type="Card",cardType="Red")])
    r=M.extract(e).iloc[0]
    assert r.yellow_cards==2 and r.red_cards==2


def test_shot_partition_includes_woodwork_and_excludes_own_goals():
    e=events([dict(type="Goal",isShot=True),dict(type="Goal",isShot=True,goalOwn=True),
              dict(type="ShotOnPost",isShot=True),dict(type="SavedShot",isShot=True,shotBlocked=True),
              dict(type="MissedShots",isShot=True)])
    r=M.extract(e).iloc[0]
    assert r.shots==4 and r.sot==1 and r.woodwork==1
    assert r.shots==r.sot+r.shots_offtarget+r.shots_blocked
    assert r.woodwork<=r.shots_offtarget


def test_conditional_rates_ignore_future_and_stay_bounded():
    data=pd.DataFrame([dict(team="A",opponent="B",date=pd.Timestamp("2025-01-01"),done=8,total=10),
                       dict(team="A",opponent="B",date=pd.Timestamp("2026-01-01"),done=0,total=10000)])
    future=pd.DataFrame([dict(team="A",opponent="B")])
    a=M.conditional_rate(data,future,"done","total","2025-02-01")
    b=M.conditional_rate(data.iloc[:1],future,"done","total","2025-02-01")
    assert a==pytest.approx(b)
    assert 0<a[0]<1


def test_joint_count_draws_have_nonnegative_margins_and_expected_means():
    m=dict(lambda_home=6.,lambda_away=4.,r=20.,rho=.3)
    d=M.draw_counts(m,np.random.default_rng(5),n=20000)
    assert (d>=0).all()
    assert np.allclose(d.mean(axis=0),[6,4],atol=.12)
    assert np.corrcoef(d.T)[0,1]>.15
