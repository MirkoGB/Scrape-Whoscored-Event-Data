from copy import deepcopy
from pathlib import Path
import json

import pytest

from sot.rose import RoseError
from sot.rose_regole import read_declarations,normalize,check_roster

ROOT=Path(__file__).resolve().parents[1]


@pytest.fixture
def intake():
    settings=json.loads((ROOT/'fantacalcio_rose/leghe.json').read_text(encoding='utf-8'))
    text=(ROOT/'fantacalcio_rose/regole_da_completare.md').read_text(encoding='utf-8')
    configs={c['id']:c for c in settings['leghe']}
    return configs,read_declarations(text,set(configs)),text


def test_alias_empty_bonus_and_originals_preserved(intake):
    configs,declarations,_=intake
    original=deepcopy(configs)
    draft=normalize(configs['fantamassa21'],declarations['fantamassa21'],'2026-2027')
    assert draft['dichiarazioni_ricevute']['nome_dichiarato']=='fantamassa'
    assert draft['regole']['formato']=='mantra'
    assert draft['regole']['moduli_consentiti'] is None
    assert draft['regole']['bonus_malus'] is None
    assert draft['regole']['modificatori']['capitano']['formula'] is None
    assert draft['regole']['modificatori']['capitano']['ruoli_esclusi_dichiarati']==['pc','a']
    assert not draft['regole_confermate']
    assert configs==original


def test_statistico_and_initial_budget_are_not_redazione_or_balance(intake):
    configs,decl,_=intake
    draft=normalize(configs['fantazavomerda'],decl['fantazavomerda'],'2026-2027')
    assert draft['regole']['fonte_voti']=='statistico'
    assert draft['regole']['modificatori']['capitano']['attivo'] is False
    assert draft['dichiarazioni_ricevute']['budget_iniziale']==300
    assert draft['regole']['crediti'] is None
    assert draft['regole']['scambi'] is None


def test_ambiguous_roster_limit_does_not_become_exact(intake):
    configs,decl,_=intake
    draft=normalize(configs['fantamassa21'],decl['fantamassa21'],'2026-2027')
    constraints=draft['regole']['vincoli_rosa']
    result=check_roster([{'ruolo_classic':'d'}]*35,constraints)
    assert constraints['dimensione_dichiarata']==32
    assert constraints['totale_esatto'] is None
    assert result['dimensione_coincide'] is False
    assert result['verifica_completa'] is False
    assert result['conforme_regolamento'] is None


def test_role_changing_trade_violates_fixed_roster(intake):
    configs,decl,_=intake
    constraints=normalize(configs['fantagas2020'],decl['fantagas2020'],'2026-2027')['regole']['vincoli_rosa']
    roster=[{'ruolo_classic':r} for r,n in zip('pdca',[3,8,8,6]) for _ in range(n)]
    assert check_roster(roster,constraints)['conforme_vincoli_espliciti']
    after=deepcopy(roster)
    after[-1]['ruolo_classic']='d'
    assert not check_roster(after,constraints)['conforme_vincoli_espliciti']
    assert check_roster(after,constraints)['conforme_regolamento'] is None


def test_minimum_goalkeepers(intake):
    configs,decl,_=intake
    constraints=normalize(configs['fantazavomerda'],decl['fantazavomerda'],'2026-2027')['regole']['vincoli_rosa']
    roster=[{'ruolo_classic':'p'}]+[{'ruolo_classic':'d'}]*28
    assert not check_roster(roster,constraints)['conforme_vincoli_espliciti']
    roster[1]['ruolo_classic']='p'
    result=check_roster(roster,constraints)
    assert result['conforme_vincoli_espliciti'] and not result['verifica_completa']


def test_duplicate_and_unknown_leagues_rejected(intake):
    configs,_,text=intake
    with pytest.raises(RoseError,match='duplicata'):
        read_declarations(text+'\n```text\nLega: fantamassa21\n```\n',set(configs))
    with pytest.raises(RoseError,match='non riconosciuta'):
        read_declarations(text.replace('Lega: fantamassa\n','Lega: altra\n'),set(configs))


def test_missing_league_and_wrong_season_rejected(intake):
    configs,decl,text=intake
    with pytest.raises(RoseError,match='Mancano'):
        read_declarations(text.split('```text')[0],set(configs))
    changed=deepcopy(decl['fantagas2020'])
    changed['campi']['Stagione / formato / fonte voti']='2025-2026 / Classic / Redazione'
    with pytest.raises(RoseError,match='Stagione'):
        normalize(configs['fantagas2020'],changed,'2026-2027')


def test_defense_clarification_preserves_negative_exception(intake):
    configs,decl,_=intake
    clarification=json.loads((ROOT/'fantacalcio_rose/precisazioni_regole.json').read_text(encoding='utf-8'))
    for league_id,config in configs.items():
        draft=normalize(config,decl[league_id],'2026-2027',clarification)
        defense=draft['regole']['modificatori']['difesa']
        assert defense['criterio_media']=='migliori_quattro_fra_portiere_e_difensori_schierati'
        assert defense['gestione_sv']['meno_di_quattro_voti']=='modificatore_non_applicato'
        if league_id=='fantazavomerda':
            assert defense['fasce_complete']==config['regole']['modificatori']['difesa']['fasce_complete']
            assert defense['fasce_complete'][0]['bonus']==-1.5
        else:
            assert defense['bonus_sotto_6']==0
            assert defense['fasce_complete'][0]=={'min_incluso':'-inf','max_escluso':6,'bonus':0}
        assert not draft['regole_confermate']


def test_bench_size_does_not_become_number_of_substitutions(intake):
    configs,decl,_=intake
    clarification=json.loads((ROOT/'fantacalcio_rose/precisazioni_regole.json').read_text(encoding='utf-8'))
    original=deepcopy(clarification)
    for league_id,config in configs.items():
        subs=normalize(config,decl[league_id],'2026-2027',clarification)['regole']['sostituzioni']
        assert subs['numero_massimo']=='illimitato' and subs['ordine_ingresso'] is None
        if league_id in ('fantagas2020','fantaonlyfans'):
            assert subs['panchina']['posti_per_ruolo']=={'p':1,'d':2,'c':2,'a':2}
            assert subs['panchina']['numero_posti']==7
        else:
            assert subs['panchina']['composizione']=='libera'
            assert subs['panchina']['numero_posti'] is None
    assert clarification==original


@pytest.mark.parametrize('size,valid',[(32,True),(35,True),(36,False)])
def test_fantamassa_maximum_is_not_exact_size(intake,size,valid):
    configs,decl,_=intake
    clarification=json.loads((ROOT/'fantacalcio_rose/precisazioni_regole.json').read_text(encoding='utf-8'))
    draft=normalize(configs['fantamassa21'],decl['fantamassa21'],'2026-2027',clarification)
    constraints=draft['regole']['vincoli_rosa']
    assert constraints['totale_massimo']==35
    assert constraints['totale_esatto'] is None
    result=check_roster([{'ruolo_classic':'d'}]*size,constraints)
    assert result['dimensione_coerente'] is valid
    assert result['conforme_vincoli_espliciti'] is valid
    assert result['conforme_regolamento'] is None


@pytest.mark.parametrize('league,penalty,missed,assist_mode',[
    ('fantagas2020',3,-3,'fisso'),
    ('fantamassa21',3,-3,'quality'),
    ('fantaonlyfans',3,-3,'fisso'),
    ('fantaunipdgiantiamiamo',3,-3,'quality'),
    ('fantazavomerda',2,-2,'quality'),
])
def test_scoring_exceptions_are_isolated_by_league(intake,league,penalty,missed,assist_mode):
    configs,decl,_=intake
    clarification=json.loads((ROOT/'fantacalcio_rose/precisazioni_regole.json').read_text(encoding='utf-8'))
    original=deepcopy(clarification)
    draft=normalize(configs[league],decl[league],'2026-2027',clarification)
    bonus=draft['regole']['bonus_malus']
    assert bonus['gol_segnati']==3
    assert bonus['rigori_segnati']==penalty and bonus['rigori_sbagliati']==missed
    assert bonus['rigori_parati']==3 and bonus['porta_inviolata']==1
    assert bonus['ammonizione']==-0.5 and bonus['espulsione']==-1
    assert bonus['autoreti']==-2 and bonus['gol_subiti']==-1
    assert bonus['assist']['modalita']==assist_mode
    if assist_mode=='quality':
        assert bonus['assist']['fasce_bonus']==[0.5,1,1.5]
        assert 'bonus_per_assist' not in bonus['assist']
    else:
        assert bonus['assist']['bonus_per_assist']==1
    assert not draft['regole_confermate']
    assert clarification==original


def test_captain_only_in_enabled_leagues_and_no_mantra_adaptations(intake):
    configs,decl,_=intake
    clarification=json.loads((ROOT/'fantacalcio_rose/precisazioni_regole.json').read_text(encoding='utf-8'))
    original=deepcopy(clarification)
    for league,config in configs.items():
        draft=normalize(config,decl[league],'2026-2027',clarification)
        cap=draft['regole']['modificatori']['capitano']
        if league in ('fantagas2020','fantamassa21','fantaonlyfans'):
            assert cap['attivo'] is True
            assert cap['formula']=={'operazione':'voto_base_meno_soglia','soglia':6}
        else:
            assert cap['attivo'] is False and cap['formula'] is None
        if league=='fantamassa21':
            assert cap['ruoli_esclusi_dichiarati']==['pc','a']
        subs=draft['regole']['sostituzioni']
        assert subs['modalita_dichiarata']=='stesso_ruolo'
        assert subs['adattamenti_ruolo_consentiti'] is False
        assert subs['numero_massimo']=='illimitato'
        assert subs['ordine_ingresso'] is None
    assert clarification==original
