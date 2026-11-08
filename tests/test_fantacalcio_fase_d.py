"""Proprietà, enumerazione completa, reversibilità e blocchi della Fase D."""
from copy import deepcopy
import hashlib

import pytest

from sot.rose import RoseError
from sot import rose_scambi as D
from scripts.run_fantacalcio_fase_d import verify_sources


def fixture(league='lega'):
    config=dict(id=league,mia_squadra='Mia',regole={},regole_confermate=False,stagione_confermata=False)
    rosters=dict(id=league,squadre=[])
    values={}
    for t,name in enumerate(('Mia','Altra','Terza')):
        rows=[]
        for n,role in enumerate(('p','d','a')):
            pid=t*3+n+1
            rows.append(dict(lega=league,squadra=name,mia_squadra=t==0,giocatore_id_fc=pid,
                             nome_fc=f'P{pid}',costo=0 if pid==1 else pid*2,
                             ruolo_classic=role,ruolo_mantra=role))
            values[pid]=dict(stato='stima_provider' if pid!=4 else 'non_stimabile_senza_righe_fc_g1_g5',
                            appartenenze=[dict(lega=league,squadra=name,mia_squadra=t==0,costo=rows[-1]['costo'])])
        rosters['squadre'].append(dict(nome=name,mia_squadra=t==0,giocatori=3,rosa=rows))
    return rosters,config,values


def context():
    rosters,config,values=fixture()
    return D.league_state(rosters,config,values),config,values


@pytest.mark.parametrize('send,receive',[([1],[4]),([1,2],[4,5]),([],[])])
def test_exchange_is_reversible_and_inputs_and_third_team_unchanged(send,receive):
    state,config,values=context();before=deepcopy(state)
    trade=D.Exchange('lega','Mia','Altra',send,receive)
    after=D.apply_exchange(state,trade)
    assert state==before
    assert after['rose']['Terza']==state['rose']['Terza']
    assert D.apply_exchange(after,trade.inverse())==state
    assert set().union(*map(set,after['rose'].values()))==set(state['giocatori'])
    result=D.simulate(state,trade,config,values)
    assert result['legalita_regolamento'] is None and not result['consigliato']
    assert result['rose'][0]['dopo']['giocatori']==3
    if send:
        assert result['guadagno_punti_schierabili_utente'] is None
        assert result['giocatori_coinvolti'][0]['costo_export']==0
        assert result['giocatori_coinvolti'][0]['squadra_export']=='Mia'
    else:
        assert result['guadagno_punti_schierabili_utente']==0
        assert result['guadagno_punti_schierabili_controparte']==0
        assert result['rose'][0]['prima']==result['rose'][0]['dopo']


def test_candidate_catalogue_is_complete_and_counts_match_brute_force():
    state,_,values=context()
    candidates=list(D.iter_candidates(state))
    assert len(candidates)==36 and len({x.id for x in candidates})==36
    assert len(list(D.iter_candidates(state,'altra',1)))==9
    for row in D.candidate_counts(state,values):
        ops=[op for op in candidates if op.controparte==row['controparte'] and len(op.cedi)==int(row['formato'][0])]
        assert row['combinazioni']==len(ops)
        assert row['firma_classic_invariata']==sum(D.signature(state,x.cedi)==D.signature(state,x.ricevi) for x in ops)
        assert row['con_stime_individuali']==sum(D.fully_estimated(x.cedi+x.ricevi,values) for x in ops)
    assert any(4 in x.ricevi for x in candidates)  # il mancante non è scartato


@pytest.mark.parametrize('send,receive',[([1,1],[4,5]),([True],[4]),([1.0],[4]),([-1],[4]),([1,2],[4]),([1],[4,5]),([1,2,3],[4,5,6]),([1],[1]),([1],[])])
def test_invalid_packages_are_rejected(send,receive):
    with pytest.raises(RoseError): D.Exchange('lega','Mia','Altra',send,receive)


@pytest.mark.parametrize('trade',[
    D.Exchange('altra_lega','Mia','Altra',(1,),(4,)),
    D.Exchange('lega','Mia','Altra',(4,),(1,)),
    D.Exchange('lega','Mia','Altra',(1,),(7,)),
    D.Exchange('lega','Mia','Sconosciuta',(1,),(4,)),
])
def test_cross_league_and_wrong_ownership_fail(trade):
    state,_,_=context()
    with pytest.raises(RoseError): D.apply_exchange(state,trade)


def test_self_exchange_and_invalid_enumeration_fail():
    state,config,values=context()
    with pytest.raises(RoseError): D.Exchange('lega','Mia',' mia ',(1,),(2,))
    with pytest.raises(RoseError): list(D.iter_candidates(state,'Mia'))
    with pytest.raises(RoseError): list(D.iter_candidates(state,size=3))
    with pytest.raises(RoseError): D.simulate(state,D.Exchange('lega','Altra','Terza',(4,),(7,)),config,values)


def test_id_permutation_is_same_operation_but_league_changes_identity():
    a=D.Exchange('lega','Mia','Altra',(2,1),(5,4))
    b=D.Exchange('lega','Mia','Altra',(1,2),(4,5))
    c=D.Exchange('lega2','Mia','Altra',(1,2),(4,5))
    assert a.id==b.id and a.id!=c.id
    assert a.inverse().inverse()==a


def test_identical_player_ids_can_exist_in_distinct_leagues():
    states=[]
    for league in ('uno','due'):
        rosters,config,values=fixture(league)
        states.append(D.league_state(rosters,config,values))
    changed=D.apply_exchange(states[0],D.Exchange('uno','Mia','Altra',(1,),(4,)))
    assert 4 in changed['rose']['Mia'] and 1 in states[1]['rose']['Mia']


@pytest.mark.parametrize('error',['duplicate','wrong_owner','missing_card','stale_card','missing_role','wrong_count'])
def test_inconsistent_inputs_are_rejected(error):
    rosters,config,values=fixture()
    row=rosters['squadre'][0]['rosa'][0]
    if error=='duplicate': rosters['squadre'][1]['rosa'][0]['giocatore_id_fc']=1
    if error=='wrong_owner': row['squadra']='Altra'
    if error=='missing_card': del values[1]
    if error=='stale_card': values[1]['appartenenze'][0]['costo']=999
    if error=='missing_role': row['ruolo_mantra']=None
    if error=='wrong_count': rosters['squadre'][0]['giocatori']=4
    with pytest.raises(RoseError): D.league_state(rosters,config,values)


def test_complete_configuration_does_not_fabricate_a_scoring_engine(monkeypatch):
    monkeypatch.setattr(D,'rules_status',lambda config:dict(pronta_per_valutazione=True,campi_da_confermare=[]))
    result=D.blockers({})
    assert result['stato']=='non_valutabile'
    assert result['motivi']==['valutatore_formazioni_e_punti_di_lega_non_disponibile']


def test_missing_estimate_remains_explicit_after_trade():
    state,config,values=context()
    result=D.simulate(state,D.Exchange('lega','Mia','Altra',(1,),(4,)),config,values)
    assert result['rose'][0]['prima']['senza_stima']==[]
    assert result['rose'][0]['dopo']['senza_stima']==[4]
    assert result['rose'][1]['dopo']['senza_stima']==[]
    assert result['guadagno_punti_schierabili_utente'] is None


def test_source_changes_are_detected(tmp_path):
    path=tmp_path/'source.json';path.write_bytes(b'originale')
    audit=dict(fonti=[dict(percorso=str(path),sha256=hashlib.sha256(path.read_bytes()).hexdigest())])
    verify_sources(audit)
    path.write_bytes(b'modificato')
    with pytest.raises(RoseError): verify_sources(audit)
