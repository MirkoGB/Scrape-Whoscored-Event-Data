"""Guardie temporali, universi al cutoff e separazione dei bersagli FC."""
import numpy as np
import pandas as pd
import pytest

from sot import rose_valutazione as C
from sot.rose import RoseError


def seasons():
    votes, matches = [], []
    for year in range(2021, 2026):
        season=f'{year}-{year+1}'
        for round_no in range(1,39):
            for club in range(10):
                mid=year*1000+round_no*10+club
                date=pd.Timestamp(f'{year}-08-01')+pd.Timedelta(days=7*round_no)
                matches.append(dict(stagione=season,partita_id=mid,giornata=round_no,data=date))
                # Uno per partita basta a provare la copertura di pagine.
                grade=6+(club%3)*.5
                votes.append(dict(stagione=season,partita_id=mid,giornata=round_no,data=date,
                                  giocatore_id=club+1,giocatore=f'P{club}',ruolo=['p','d','c','a'][club%4],
                                  squadra_id=club,allenatore=False,voto_redazione=grade,
                                  fantavoto_redazione=grade+(1 if round_no%5==0 else 0)))
    return pd.DataFrame(votes),pd.DataFrame(matches)


def test_features_ignore_future_players_roles_and_outcomes():
    v,m=seasons();s='2025-2026';cutoff=C.validate_calendar(v,m,s)
    expected=C.features(v,s,cutoff)
    later=v.stagione.eq(s)&v.giornata.gt(5)
    v.loc[later,'giocatore_id']=999
    v.loc[later,'ruolo']='a'
    v.loc[later,'voto_redazione']=10
    v.loc[later,'fantavoto_redazione']=30
    actual=C.features(v,s,cutoff)
    pd.testing.assert_frame_equal(actual,expected)
    assert 999 not in set(actual.giocatore_id)


def test_same_fold_predictions_do_not_read_their_own_targets():
    v,m=seasons()
    wf,_,cal=C.walkforward(v,m)
    v.loc[v.stagione.eq('2025-2026')&v.giornata.gt(5),'fantavoto_redazione']+=10
    changed,_,_=C.walkforward(v,m)
    pd.testing.assert_frame_equal(wf.drop(columns=['y_punti','y_bonus']),changed.drop(columns=['y_punti','y_bonus']))
    assert all(all(past < row['stagione'] for past in row['stagioni_training']) for row in cal)


@pytest.mark.parametrize('corruption',['page','round','date','recovery','duplicate','missing_fv'])
def test_incomplete_or_misdated_inputs_fail(corruption):
    v,m=seasons();s='2025-2026';idx=v[v.stagione.eq(s)].index[0]
    if corruption=='page': v=v.drop(index=idx)
    if corruption=='round': v.loc[idx,'giornata']=2
    if corruption=='date': v.loc[idx,'data']+=pd.Timedelta(days=1)
    if corruption=='duplicate': v=pd.concat([v,v.loc[[idx]]])
    if corruption=='missing_fv': v.loc[idx,'fantavoto_redazione']=np.nan
    if corruption=='recovery':
        mid=v.loc[idx,'partita_id'];v.loc[idx,'data']=pd.Timestamp('2026-01-01');m.loc[m.partita_id.eq(mid),'data']=pd.Timestamp('2026-01-01')
    with pytest.raises(RoseError): C.validate_calendar(v,m,s)


def test_no_future_votes_is_zero_contribution_not_zero_conditional_grade():
    v,_=seasons()
    y=C.targets(v,'2025-2026',5,pd.Series([1,999],name='giocatore_id')).set_index('giocatore_id')
    assert y.loc[999,'y_n']==0 and y.loc[999,'y_punti']==0
    assert pd.isna(y.loc[999,'y_voto'])
    assert y.loc[1,'y_n']==5


def test_no_numeric_recent_votes_uses_prior_and_never_divides_by_zero():
    v,m=seasons();s='2025-2026'
    v.loc[v.stagione.eq(s)&v.giocatore_id.eq(1)&v.giornata.le(5),['voto_redazione','fantavoto_redazione']]=np.nan
    x=C.features(v,s,C.validate_calendar(v,m,s))
    p=C.predict(x,5,'recente').set_index('giocatore_id')
    assert p.loc[1,'p']==0 and p.loc[1,'punti']==0
    assert np.isfinite(p.loc[1,'voto'])
    combined=C.predict(x,5,'combinato',dict(p=5,voto=5,bonus=5)).set_index('giocatore_id')
    assert combined.loc[1,'p']>0
    assert combined.loc[1,'peso_recente_voto']==0


def test_missing_previous_year_is_explicit_role_fallback():
    v,m=seasons();s='2025-2026'
    v.loc[v.stagione.eq(s)&v.giocatore_id.eq(1),'giocatore_id']=999
    x=C.features(v,s,C.validate_calendar(v,m,s)).set_index('giocatore_id')
    assert x.loc[999,'prior_ruolo']
    assert np.isfinite(x.loc[999,'history_voto'])
    assert pd.isna(x.loc[999,'n_previous'])


def test_model_gate_requires_improvement_in_every_fold():
    v,m=seasons();wf,_,_=C.walkforward(v,m)
    # Combinato mediamente migliore, ma peggiore in una stagione.
    wf['y_punti']=10.
    wf['punti']=wf.modello.map({'storico':12.,'recente':13.,'combinato':10.})
    wf.loc[wf.stagione.eq('2025-2026')&wf.modello.eq('combinato'),'punti']=14.
    selection=C.select_models(wf)
    assert all(not s['combinazione_promossa'] and s['modello']=='storico' for s in selection.values())


def test_empirical_radius_has_role_fallback_and_is_not_zero_by_default():
    rows=pd.DataFrame([dict(orizzonte=5,modello='storico',ruolo='a',punti=10.,y_punti=float(i),presenze=3.,y_n=2.) for i in range(40)])
    radius,n=C.interval_radius(rows,5,'storico','p')
    assert n==40 and radius>0
    with pytest.raises(RoseError): C.interval_radius(rows,8,'storico','p')
