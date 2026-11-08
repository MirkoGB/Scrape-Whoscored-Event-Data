"""Controlli del confine temporale e dei denominatori della Fase B; senza rete."""
import pandas as pd
import pytest

from acquisition.fantacalcio import pagina as P
from sot import voti as V
from sot.rose import RoseError
from sot.rose_comparative import (aggregate_votes, aggregate_ws, calendar_bridge,
                                 compare, strict_sum)


def fixtures():
    official, matches, teams, results = [], [], [], []
    for g in range(1, 6):
        for h in range(10):
            a = 10 + (h + g) % 10
            mid = 100 * g + h
            home, away = f'T{h}', f'T{a}'
            date = pd.Timestamp('2026-08-20') + pd.Timedelta(days=7*g)
            official.append(dict(giornata=g, casa=home, trasferta=away))
            matches.append(dict(partita_id=mid+1000, giornata=g, casa=home, trasferta=away,
                                data=date, gol_casa=2, gol_trasferta=0))
            teams.extend([dict(matchId=mid, teamId=h, opponentId=a, team=home, opponent=away, is_home=1, date=date, goals=1),
                          dict(matchId=mid, teamId=a, opponentId=h, team=away, opponent=home, is_home=0, date=date, goals=0)])
            results.append(dict(url=f'/matches/{mid}/live/example', score='2:0'))
    return [pd.DataFrame(x) for x in (matches, teams, official, results)]


def test_calendar_uses_official_round_and_scoreboard_including_own_goals():
    fc, ws, official, scores = fixtures()
    result = calendar_bridge(fc.sample(frac=1), ws, official, '2026-09-30', scores)
    assert len(result) == 50
    assert result.goals_casa_ws.eq(1).all()
    assert result.risultato_casa_ws.eq(2).all()
    assert result.groupby('giornata').size().to_dict() == dict.fromkeys(range(1, 6), 10)


@pytest.mark.parametrize('error', ['round', 'cutoff', 'duplicate', 'missing', 'date', 'score'])
def test_calendar_rejects_invalid_alignment(error):
    fc, ws, official, scores = fixtures()
    cutoff = '2026-09-30'
    if error == 'round': fc.loc[0, 'giornata'] = 2
    if error == 'cutoff': cutoff = '2026-08-01'
    if error == 'duplicate': fc = pd.concat([fc, fc.iloc[:1]])
    if error == 'missing': ws = ws[ws.matchId != ws.iloc[0].matchId]
    if error == 'date': fc.loc[0, 'data'] += pd.Timedelta(days=1)
    if error == 'score': scores.loc[0, 'score'] = '3:0'
    with pytest.raises(RoseError):
        calendar_bridge(fc, ws, official, cutoff, scores)


def vote_rows():
    rows=[]
    for i, (v, fv, code) in enumerate([(6., 9., None), (None, None, 55), (9., 21., None)]):
        row=dict(partita_id=i, giocatore_id=1, allenatore=False, squadra='Roma', ruolo='a',
                 subentrato=False, sostituito=False)
        for scale in ('redazione', 'statistico', 'italia'):
            row.update({f'voto_{scale}':v, f'fantavoto_{scale}':fv, f'codice_sv_{scale}':code})
        row.update({name:0 for name in V.COLONNE_BONUS + ['ammonizione','espulsione']})
        row['gol_segnati'] = [1, 0, 4][i]
        row['ammonizione'] = i == 1
        rows.append(row)
    return pd.DataFrame(rows)


def test_sv_missing_and_observed_zero_have_distinct_denominators():
    rows = vote_rows()
    stats = aggregate_votes(rows)
    assert stats['presenze_voto_redazione'] == 2
    assert stats['sv_redazione'] == 1
    assert stats['media_fantavoto_fonte_redazione'] == 15
    assert stats['ammonizione'] == 1 and stats['ammonizione_per_voto'] == 0
    assert stats['gol_segnati_per_voto'] == 2.5
    assert stats['assist'] == 0
    assert stats['fantavoto_lega'] is None
    absent = aggregate_votes(rows.iloc[:0])
    assert absent['assist'] is None and absent['presenze_voto_redazione'] is None
    only_sv = aggregate_votes(rows.iloc[1:2])
    assert only_sv['presenze_voto_redazione'] == 0
    assert only_sv['media_voto_redazione'] is None
    assert only_sv['gol_segnati_per_voto'] is None


def test_coaches_and_duplicates():
    rows = vote_rows()
    coach = rows.iloc[:1].assign(allenatore=True, giocatore_id=None, voto_redazione=10)
    assert aggregate_votes(pd.concat([rows, coach]))['media_voto_redazione'] == 7.5
    with pytest.raises(RoseError):
        aggregate_votes(pd.concat([rows, rows.iloc[:1]]))


def ws_rows():
    return pd.DataFrame([dict(campionato='ITA-serie-a', matchId=i, playerId=1, teamId=2,
                             team='Roma', stato='titolare' if i == 1 else 'panchina',
                             is_starter=i==1, minutes=90 if i==1 else 0, shots=2 if i==1 else 0,
                             sot=1 if i==1 else 0, goals=0, xg=.4 if i==1 else 0, xg_fit='ITA/2026-2027')
                         for i in (1, 2)])


def test_bench_is_observed_zero_absence_unknown_and_per_vote_is_paired():
    pm=ws_rows()
    lineup=pd.DataFrame(columns=['matchId','playerId','type'])
    shots=pd.DataFrame(columns=['matchId','playerId','is_goal','shotOpenPlay','shotCounter','penaltyScored'])
    teams=pm[['matchId','teamId']]
    stats=aggregate_ws(pm, lineup, shots, teams, [1])
    assert stats['convocazioni_osservate']==2 and stats['presenze_effettive']==1
    assert stats['tiri_per90']==2 and stats['tiri_per_voto_appaiato']==2
    assert stats['presenze_voto_con_ws']==1
    bench=aggregate_ws(pm.iloc[1:],lineup,shots,teams)
    assert bench['minuti']==0 and bench['tiri_per90'] is None
    absent=aggregate_ws(pm.iloc[:0],lineup,shots,teams)
    assert absent['minuti'] is None and absent['presenze_effettive'] is None


def test_partial_missing_never_summed_as_complete_and_xg_delta_excluded():
    assert strict_sum(pd.Series([1., None])) is None
    assert strict_sum(pd.Series([0., 0.])) == 0
    assert 'xg_interno' not in compare({'xg_interno':1}, {'xg_interno':2})


@pytest.mark.parametrize('selector,wrong', [('season','2025/26'), ('matchweek','6')])
def test_vote_redirect_detected(monkeypatch, selector, wrong):
    monkeypatch.setattr(P, '_contratto', lambda soup: [])
    html=f'<select id="{selector}"><option selected value="{wrong}"></option></select>'.encode()
    with pytest.raises(P.MarkupInatteso, match=selector):
        P.analizza(html, '2026-2027', 1)


def test_build_does_not_even_parse_rounds_outside_snapshot(monkeypatch):
    class Target:
        season='2026-2027'
        def percorso(self, g):
            raise AssertionError('Non deve leggere G6')
    monkeypatch.setattr(V, '_pagine', lambda *a: [(Target(), 6)])
    with pytest.raises(FileNotFoundError):
        V.costruisci(seasons=['2026-2027'], giornate=range(1, 6), verbose=False)
