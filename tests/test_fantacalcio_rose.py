"""Errori d'importazione, omonimie, ruoli e isolamento tra leghe; senza rete."""
import json
from pathlib import Path
from xml.sax.saxutils import escape
import zipfile

import pandas as pd
import pytest

from acquisition.fantacalcio import pagina as P
from sot.rose import (RoseError, check_ownership, import_roster, nome_chiave,
                      require_rules, resolve_identities, rules_status)


def workbook(tmp_path, rows, sheet="ROSE", shared=False):
    path = tmp_path / "test-rosters-1791274848274.xlsx"
    ns = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
    rel = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
    strings, rendered = [], []
    for i, row in enumerate(rows, 1):
        cells = []
        for col, value in row.items():
            if value is None:
                continue
            ref = f"{col}{i}"
            if shared:
                strings.append(str(value))
                cells.append(f'<c r="{ref}" t="s"><v>{len(strings)-1}</v></c>')
            else:
                cells.append(f'<c r="{ref}" t="inlineStr"><is><t>{escape(str(value))}</t></is></c>')
        rendered.append(f'<row r="{i}">{"".join(cells)}</row>')
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("xl/workbook.xml", f'<workbook xmlns="{ns}" xmlns:r="{rel}"><sheets><sheet name="{sheet}" sheetId="3" r:id="rId7"/></sheets></workbook>')
        z.writestr("xl/_rels/workbook.xml.rels", '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId7" Target="worksheets/real.xml"/></Relationships>')
        z.writestr("xl/worksheets/real.xml", f'<worksheet xmlns="{ns}"><sheetData>{"".join(rendered)}</sheetData></worksheet>')
        if shared:
            z.writestr("xl/sharedStrings.xml", f'<sst xmlns="{ns}">' + ''.join(f'<si><t>{escape(s)}</t></si>' for s in strings) + '</sst>')
    return path


@pytest.mark.parametrize("shared", [False, True])
def test_relationship_totals_zero_and_unicode(tmp_path, shared):
    rows = [{'A':'Mia', 'B':'costo'}, {'A':'Lucumì', 'B':0}, {}, {'A':'Fini ', 'B':2}, {'A':'totale','B':2}]
    data, audit = import_roster(workbook(tmp_path, rows, shared=shared), 'lega', 'MIA')
    assert [x['giocatore'] for x in data] == ['Lucumì', 'Fini ']
    assert data[0]['costo'] == 0 and data[1]['nome_chiave'] == 'fini'
    assert audit['squadre'][0]['giocatori'] == 2
    assert audit['squadre'][0]['totale_coerente'] is True
    assert len(audit['fonte']['sha256']) == 64
    assert audit['fonte']['export_utc_da_nome_file'] is not None


def test_missing_cost_is_not_zero_or_reconciled(tmp_path):
    p=workbook(tmp_path,[{'A':'Mia','B':'costo'},{'A':'Uno'},{'A':'totale','B':0}])
    rows,audit=import_roster(p,'l','Mia')
    assert rows[0]['costo'] is None
    assert audit['squadre'][0]['totale_coerente'] is None
    assert audit['squadre'][0]['costi_mancanti']==1


@pytest.mark.parametrize('rows, message', [
    ([{'A':'Mia','B':'costo'},{'A':'Uno','B':2},{'A':'totale','B':3}], 'diverso'),
    ([{'A':'Mia','B':'costo'},{'A':'Uno','B':2}], 'totale mancante'),
    ([{'A':'Mia','B':'costo'},{'A':'Uno','B':'NaN'},{'A':'totale','B':0}], 'non valido'),
    ([{'A':'Mia','B':'costo'},{'A':'Uno','B':-1},{'A':'totale','B':0}], 'non valido'),
    ([{'A':'Mia','B':'costo'},{'B':2},{'A':'totale','B':0}], 'senza giocatore'),
    ([{'A':'Mia','B':'costo'},{'A':'Uno','B':1},{'A':'uno ','B':1},{'A':'totale','B':2}], 'ripetuti'),
    ([{'A':'Mia','B':'costo'},{'A':'Uno','B':1},{'A':'totale','B':1},{'A':'Due','B':1}], 'dopo il totale'),
])
def test_reject_corrupt_rosters(tmp_path, rows, message):
    with pytest.raises(RoseError, match=message):
        import_roster(workbook(tmp_path,rows),'l','Mia')


def test_wrong_sheet_not_silently_selected(tmp_path):
    with pytest.raises(RoseError,match='foglio'):
        import_roster(workbook(tmp_path,[{'A':'Mia'}],sheet='ALTRO'),'l','Mia')


def sources(fc='Mora', ws='Rodrigo Mora', fc_role='c', ws_role='MID'):
    q=pd.DataFrame([dict(stagione='2026-2027',giocatore_id=1,giocatore=fc,squadra_id=10,
                        squadra_sigla='ROM',ruolo_classic=fc_role,ruolo_mantra='c',fuori_dal_campionato=False)])
    hist=pd.DataFrame(columns=['giocatore_id_fc','playerId_ws','nome_ws','stagione'])
    current=pd.DataFrame([dict(playerId=20,playerName=ws,teamId=100,team='Roma',role=ws_role)])
    teams=pd.DataFrame([dict(squadra_id_fc=10,teamId_ws=100)])
    return q,hist,current,teams


def resolve(name, data):
    return resolve_identities([name],*data,'2026-2027')[0]


def test_no_fuzzy_no_substring_and_no_foreign_club_match():
    assert resolve('Mora',sources(ws='Alvaro Morata'))['playerId_ws'] is None
    assert resolve('Moraa',sources())['giocatore_id_fc'] is None
    data=sources();data[2].loc[0,'teamId']=999
    assert resolve('Mora',data)['playerId_ws'] is None


def test_ambiguous_and_initials():
    data=sources(fc='Martinez',ws='Lautaro Martinez')
    data[2].loc[1]=[21,'Josef Martinez',100,'Roma','FWD']
    assert resolve('Martinez',data)['stato']=='ws_ambiguo'
    data[0].loc[0,'giocatore']='Martinez L.'
    assert resolve('Martinez L.',data)['playerId_ws']==20


def test_goalkeeper_not_confused_with_same_surname_defender():
    data=sources(fc='Terracciano',ws='Filippo Terracciano',fc_role='p',ws_role='DEF')
    data[1].loc[0]=[1,99,'Pietro Terracciano','2025-2026']
    r=resolve('Terracciano',data)
    assert r['playerId_ws']==99 and r['stato']=='collegato_solo_storico'
    assert r['ruolo_classic']=='p' and not r['copertura_ws_corrente']


def test_conflicting_historical_identity_and_missing_name():
    data=sources();data[1].loc[0]=[1,99,'Altro Mora','2025-2026']
    assert resolve('Mora',data)['stato']=='conflitto_ponte_storico'
    data[2].loc[0,'playerName']=pd.NA
    data[1].loc[0,'playerId_ws']=20
    assert resolve('Mora',data)['nome_ws']=='Altro Mora'


def test_current_roles_and_ownership_is_per_league():
    result=resolve('Mora',sources())
    assert result['stagione']=='2026-2027' and result['metodo_ws']=='nome_iniziali_club_univoci'
    check_ownership([dict(lega='a',giocatore_id_fc=1),dict(lega='b',giocatore_id_fc=1)])
    with pytest.raises(RoseError):
        check_ownership([dict(lega='a',giocatore_id_fc=1),dict(lega='a',giocatore_id_fc=1)])


def test_rules_partial_nested_are_not_ready():
    c={'regole_confermate':True,'stagione_confermata':True,'regole':{'modificatori':{'difesa':{'attivo':True,'fasce_complete':None}}}}
    assert 'modificatori.difesa.fasce_complete' in rules_status(c)['campi_da_confermare']
    with pytest.raises(RoseError,match='Regole incomplete'):
        require_rules(c)
    c['regole']['modificatori']['difesa']={'attivo':False}
    assert not any(p.startswith('modificatori.') for p in rules_status(c)['campi_da_confermare'])


@pytest.mark.parametrize('ending',['','/2026-27','?x=1'])
def test_current_and_old_provider_links(ending):
    headers='<th data-col-key="sq"></th>'+''.join(f'<th data-col-key="{key}"></th>' for key,_ in P.COLONNE_QUOTE)
    html=f'''<select id="season"><option value="2026/27" selected>2026/27</option></select>
    <table class="pills-table"><thead>{headers}</thead><tbody>
    <tr class="player-row" data-filter-team-id="10"><a class="player-link" href="https://www.fantacalcio.it/serie-a/squadre/roma/mora/1{ending}">Mora</a>
    <span class="role" data-value="c"></span><span class="role-mantra" data-value="c"></span><td class="player-team">ROM</td></tr></tbody></table>'''.encode()
    assert P.analizza_quote(html,'2026-2027')[0]['giocatore_id']==1
    with pytest.raises(P.MarkupInatteso,match='stagione listone'):
        P.analizza_quote(html,'2025-2026')


def test_unicode_is_preserved():
    assert nome_chiave(' Lucumi\u0300 ') == nome_chiave('Lucumì')
    assert nome_chiave('Lucumì') != nome_chiave('Lucumi')


def test_user_defense_thresholds():
    path=Path(__file__).resolve().parents[1]/'fantacalcio_rose/leghe.json'
    leagues=json.loads(path.read_text(encoding='utf-8'))['leghe']
    for league in leagues:
        bands=league['regole']['modificatori']['difesa']['fasce_complete']
        assert [b['bonus'] for b in bands]==league['dichiarazioni_utente']['difesa']['bonus_in_ordine']
        assert bands[-1]['max_escluso']=='+inf'
        for left,right in zip(bands,bands[1:]):
            assert left['max_escluso']==right['min_incluso']
            if isinstance(left['min_incluso'],(float,int)):
                assert left['max_escluso']-left['min_incluso']==0.25
        assert not rules_status(league)['pronta_per_valutazione']
