from copy import deepcopy

import pytest

from sot import over_paper as P


NOW='2026-09-18T10:00:00+00:00'
DAY='2026-09-18'


def leg(i, p=.95, odds=1.3):
    return dict(id=f'q{i}',selection_id=f's{i}',league='ITA-serie-a',match_id=str(i),
                home=f'home{i}',away=f'away{i}',bookmaker='Test',p=p,over_odds=odds,
                target='shots',side='home',line=8.5,
                match_date=DAY,published_at='2026-09-17T10:00:00+00:00',
                observed_at='2026-09-18T09:55:00+00:00',recorded_at='2026-09-18T09:56:00+00:00',
                kickoff='2026-09-18T18:00:00+00:00')


def test_frechet_and_uncertainty_are_not_independence():
    m=P.coupon_metrics([leg(i,.8) for i in range(5)],4.)
    assert m['p_independent']==pytest.approx(.8**5)
    assert m['p_lower']==0
    assert m['p_upper']==.8
    assert m['ev_robust']==-1
    assert m['fair_robust'] is None


def test_same_match_team_or_book_cannot_be_multiplied():
    a,b=leg(1),leg(2)
    for patch in ({'match_id':'1'},{'home':'home1'},{'bookmaker':'Other'}):
        with pytest.raises(ValueError):P.coupon_metrics([a,{**b,**patch}],2.)


def test_no_quotes_means_no_bets_not_fabricated_roi():
    plans=P.select_slips([],[],P.DEFAULT_RULES,DAY,NOW)
    assert all(p['status']=='no_bet' and p['stake']==0 for p in plans)
    scores=P.performance([dict(day=DAY,plans=plans)],{},P.DEFAULT_RULES)
    assert all(x['roi'] is None and x['profit'] is None and x['bankroll']==100 for x in scores)


def test_equal_budget_and_documented_multiple_price_required():
    quotes=[leg(i) for i in range(5)]
    plans=P.select_slips(quotes,[],P.DEFAULT_RULES,DAY,NOW)
    assert plans[0]['stake']==1
    assert all(p['status']=='no_bet' for p in plans[1:])
    offered=[dict(id=f'c{n}',quote_ids=[q['id'] for q in quotes[:n]],odds=1.3**n,
                  observed_at=NOW,recorded_at=NOW) for n in range(2,6)]
    plans=P.select_slips(quotes,offered,P.DEFAULT_RULES,DAY,NOW)
    assert all(p['status']=='paper_bet' and p['stake']==1 for p in plans)
    assert [len(p['legs']) for p in plans]==[1,2,3,4,5]


def test_new_bad_quote_does_not_resurrect_older_good_price():
    old=leg(1)
    new={**old,'id':'new','over_odds':1.01,'observed_at':'2026-09-18T09:59:00+00:00','recorded_at':NOW}
    plans=P.select_slips([old,new],[],P.DEFAULT_RULES,DAY,NOW)
    assert plans[0]['status']=='no_bet'


def test_stale_and_future_quotes_are_rejected():
    for patch in ({'observed_at':'2026-09-18T08:00:00+00:00'},
                  {'recorded_at':'2026-09-18T10:01:00+00:00'},
                  {'kickoff':'2026-09-18T09:00:00+00:00'}):
        assert P.select_slips([{**leg(1),**patch}],[],P.DEFAULT_RULES,DAY,NOW)[0]['status']=='no_bet'


def test_capture_requires_prediction_before_observation_and_clock_before_kickoff():
    rule={**P.DEFAULT_RULES,'frozen_at':'2026-09-16T12:00:00+00:00','test_from':'2026-09-17'}
    row={**leg(1),'source_url':'https://example.org','rules_url':'https://example.org/rules',
         'evidence_path':'proof.png','settlement_rule':'opta_90min_halfline'}
    assert P.validate_quote(row,leg(1),NOW,rule)
    for patch in ({'observed_at':'2026-09-16T10:00:00+00:00'},
                  {'kickoff':'2026-09-18T09:59:00+00:00'},
                  {'observed_at':'2026-09-18T10:00:01+00:00'},
                  {'settlement_rule':'unknown'}):
        with pytest.raises(ValueError):P.validate_quote({**row,**patch},leg(1),NOW,rule)


def test_payout_streak_drawdown_and_pending_are_separate():
    plans=[];results={}
    for i,result in enumerate(['lost','lost','won']):
        q=leg(i)
        entry=P.select_slips([q],[],P.DEFAULT_RULES,DAY,NOW)
        plans.append(dict(day=f'2026-09-{18+i}',plans=entry))
        results[q['id']]={'result':result}
    before=deepcopy(plans)
    r=P.performance(plans,results,P.DEFAULT_RULES)[0]
    assert r['profit']==pytest.approx(-1.7)
    assert r['staked_settled']==3
    assert r['loss_rate']==pytest.approx(2/3)
    assert r['max_drawdown']==2
    assert r['max_losing_streak']==2
    assert plans==before
    del results['q2']
    r=P.performance(plans,results,P.DEFAULT_RULES)[0]
    assert r['pending']==1 and r['profit']==-2 and r['staked_settled']==2


def test_decisions_do_not_read_outcomes():
    quotes=[leg(i) for i in range(3)]
    before=P.select_slips(quotes,[],P.DEFAULT_RULES,DAY,NOW)
    for q in quotes:q['future_outcome']='lost'
    after=P.select_slips(quotes,[],P.DEFAULT_RULES,DAY,NOW)
    assert [p['metrics'] for p in before]==[p['metrics'] for p in after]
    assert [[q['id'] for q in p['legs']] for p in before]==[[q['id'] for q in p['legs']] for p in after]


def test_immutable_record_and_tamper_detection(tmp_path):
    r={'id':'test','value':3}
    P.save_record(tmp_path,r)
    with pytest.raises(FileExistsError):P.save_record(tmp_path,r)
    assert P.load_records(tmp_path)[0]['value']==3
    path=tmp_path/'test.json'
    path.write_text(path.read_text().replace('"value": 3','"value": 4'))
    with pytest.raises(ValueError):P.load_records(tmp_path)


def test_void_single_returns_stake_but_multiple_requires_official_adjustment():
    q=leg(1)
    s=P.select_slips([q],[],P.DEFAULT_RULES,DAY,NOW)[0]
    assert P.settle_coupon(s,{'q1':{'result':'void'}})['profit']==0
    s['legs'].append(leg(2))
    assert P.settle_coupon(s,{'q1':{'result':'void'},'q2':{'result':'won'}})['status']=='needs_bookmaker_settlement'
    official=P.settle_coupon(s,{}, {'gross_return':1.3})
    assert official['profit']==pytest.approx(.3)


def test_risk_simulation_has_no_fake_numbers_without_slips():
    r=P.simulate_risk([],P.DEFAULT_RULES)
    assert len(r)==10 and all(x['probability_loss'] is None for x in r)


def test_pending_first_bet_does_not_publish_zero_profit():
    plans=P.select_slips([leg(1)],[],P.DEFAULT_RULES,DAY,NOW)
    stats=P.performance([dict(day=DAY,plans=plans)],{},P.DEFAULT_RULES)[0]
    assert stats['pending']==1 and stats['profit'] is None and stats['roi'] is None


def test_plan_stops_strategy_at_drawdown_and_leaves_other_sizes_independent(tmp_path,monkeypatch):
    from scripts import paper_over as CLI
    monkeypatch.setattr(CLI,'ROOT',tmp_path)
    protocol=P.freeze_protocol(tmp_path,now='2026-08-01T12:00:00+00:00')
    for i in range(20):
        q=leg(i)
        slips=P.select_slips([q],[],protocol,DAY,NOW)
        P.save_record(tmp_path/'decisions',dict(id=f'past{i}',day=f'2026-08-{i+1:02}',plans=slips))
        P.save_record(tmp_path/'settlements',dict(id=f's{i}',quote_id=q['id'],result='lost'))
    future={**leg(30),'id':'next'}
    P.save_record(tmp_path/'quotes',future)
    monkeypatch.setattr(P,'utc_now',lambda:NOW)
    CLI.plan(DAY)
    d=next(d for d in P.load_records(tmp_path/'decisions') if d['day']==DAY)
    assert d['plans'][0]['status']=='no_bet'
    assert 'limite di perdita' in d['plans'][0]['reason']
    assert all(p['stake']==0 for p in d['plans'])


def test_complete_paper_lifecycle_and_one_decision_per_day(tmp_path,monkeypatch):
    import json
    from scripts import paper_over as CLI
    monkeypatch.setattr(CLI,'ROOT',tmp_path)
    protocol=P.freeze_protocol(tmp_path,now='2026-09-16T12:00:00+00:00')
    q=leg(1)
    P.save_record(tmp_path/'predictions',dict(id='snapshot_test',published_at=q['published_at'],selections=[q]))
    proof=tmp_path/'synthetic_test_evidence.txt'
    proof.write_text('Synthetic fixture for software test only, not a bookmaker price.')
    row={**q,'source_url':'https://example.org/market','rules_url':'https://example.org/rules',
         'evidence_path':str(proof),'settlement_rule':'opta_90min_halfline'}
    inp=tmp_path/'input.json';inp.write_text(json.dumps(row))
    monkeypatch.setattr(P,'utc_now',lambda:NOW)
    CLI.capture_quote(inp)
    captured=P.load_records(tmp_path/'quotes')[0]
    assert captured['recorded_at']==NOW
    CLI.plan(DAY)
    with pytest.raises(ValueError):CLI.plan(DAY)
    decision=P.load_records(tmp_path/'decisions')[0]
    assert decision['plans'][0]['stake']==1
    assert all(x['status']=='no_bet' for x in decision['plans'][1:])
    monkeypatch.setattr(P,'utc_now',lambda:'2026-09-18T21:00:00+00:00')
    inp.write_text(json.dumps(dict(quote_id=captured['id'],result='won',observed_count=10,
                                   source_url='https://example.org/result',evidence_path=str(proof))))
    CLI.settle(inp)
    results={r['quote_id']:r for r in P.load_records(tmp_path/'settlements')}
    assert P.performance([decision],results,protocol)[0]['profit']==pytest.approx(.3)
    with pytest.raises(FileExistsError):CLI.settle(inp)
