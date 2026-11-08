"""Catalogo esatto di scambi 1x1/2x2 e simulazione strutturale, senza rete."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sot.rose import RoseError, file_info
from sot import rose_scambi as D


def dump(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False)+'\n', encoding='utf-8')


def verify_sources(audit):
    for source in audit['fonti']:
        if 'percorso' not in source:
            continue
        path = ROOT/source['percorso']
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != source['sha256']:
            raise RoseError(f'Sorgente modificata o assente; rigenerare la fase precedente: {path}')


def cell(value):
    return str(value).replace('|', '\\|').replace('\n', ' ')


def simulation_markdown(result):
    names = {p['giocatore_id_fc']:p['nome'] for p in result['giocatori_coinvolti']}
    lines = ['# Simulazione strutturale di scambio', '',
             f"Lega: **{result['lega']}** · {result['squadra']} ↔ {result['controparte']}", '',
             'Questa è una verifica della proprietà e della composizione delle rose. '
             'Convenienza sportiva e legalità regolamentare non sono state calcolate.', '',
             '**Cedi:** '+(', '.join(names[p] for p in result['cedi']) or 'nessuno')+'.',
             '**Ricevi:** '+(', '.join(names[p] for p in result['ricevi']) or 'nessuno')+'.', '',
             '| Squadra | Rosa prima/dopo | P prima/dopo | D prima/dopo | C prima/dopo | A prima/dopo | Senza stima prima/dopo |',
             '|---|---:|---:|---:|---:|---:|---:|']
    for team in result['rose']:
        before, after = team['prima'], team['dopo']
        roles = ' | '.join(f"{before['ruoli_classic'][r]}/{after['ruoli_classic'][r]}" for r in ('p','d','c','a'))
        lines.append(f"| {cell(team['squadra'])} | {before['giocatori']}/{after['giocatori']} | {roles} | {len(before['senza_stima'])}/{len(after['senza_stima'])} |")
    lines += ['', 'Proprietà verificate nella stessa lega; reversibilità verificata. '
              'Conteggi Classic descrittivi: non provano una formazione legale, soprattutto in Mantra.', '',
              'Motivi della mancata valutazione: '+', '.join(result['motivi'])+'.',
              'Campi da completare: '+', '.join(result['campi_regole_mancanti'])+'.', '',
              'Guadagni, formazioni ottimali, robustezza e interesse della controparte restano non disponibili. '
              'Per lo scambio nullo il guadagno è zero per identità, senza stimare il livello dei punti.', '',
              result['nota_costi'], '',
              'Gli ID delle rose complete prima/dopo e i costi di origine sono nel JSON affiancato.', '',
              f"Snapshot dati `{result['snapshot_id']}`; scambio `{result['id']}`."]
    return '\n'.join(lines)+'\n'


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT/'reports/fantacalcio_scambi')
    parser.add_argument('--lega', help='ID della lega per la simulazione manuale')
    parser.add_argument('--controparte', help='Nome esatto o normalizzato della squadra avversaria')
    parser.add_argument('--cedi', type=int, nargs='+', help='Uno o due ID FC della propria rosa')
    parser.add_argument('--ricevi', type=int, nargs='+', help='Uno o due ID FC della controparte')
    args = parser.parse_args(argv)
    if bool(args.lega) != bool(args.controparte) or bool(args.cedi) != bool(args.ricevi):
        parser.error('Simulazione: specificare --lega e --controparte, e insieme --cedi e --ricevi')
    if (args.cedi or args.ricevi) and not args.lega:
        parser.error('--cedi/--ricevi richiedono --lega e --controparte')
    out = args.output
    inputs = []

    def read(path):
        inputs.append(path)
        return json.loads(path.read_text(encoding='utf-8'))

    settings = read(ROOT/'fantacalcio_rose/leghe.json')
    rosters = read(out/'rose_per_lega.json')
    valuations = read(out/'valutazioni_giocatori.json')
    audits = [read(out/name) for name in ('audit.json','audit_fase_b.json','audit_fase_c.json')]
    for audit in audits:
        verify_sources(audit)
        if audit['stagione'] != settings['stagione']:
            raise RoseError('Stagioni diverse fra configurazione e snapshot')
    audit_a, audit_b, audit_c = audits
    if audit_b['fase_a_snapshot'] != audit_a['snapshot_id'] or audit_c['snapshot_fase_b'] != audit_b['snapshot_id']:
        raise RoseError('Catena di snapshot A/B/C incoerente')
    # Le valutazioni non erano input del proprio audit: confronto col contenuto
    # dello snapshot congelato, altrimenti un CSV/JSON modificato passerebbe.
    snapshot_c = read(out/'snapshots'/f"fase_c_{audit_c['snapshot_id']}.json")
    if snapshot_c['valutazioni'] != valuations:
        raise RoseError('Valutazioni C diverse dallo snapshot congelato')
    if len({v['giocatore_id_fc'] for v in valuations}) != len(valuations):
        raise RoseError('Identità duplicate nelle valutazioni C')
    values = {v['giocatore_id_fc']:v for v in valuations}
    configs = {c['id']:c for c in settings['leghe']}
    if len(configs) != len(settings['leghe']) or len({r['id'] for r in rosters}) != len(rosters) or set(configs) != {r['id'] for r in rosters}:
        raise RoseError('Leghe duplicate, assenti o non configurate')
    states = {r['id']:D.league_state(r,configs[r['id']],values) for r in rosters}
    expected_memberships = {(m['lega'],m['squadra'],v['giocatore_id_fc']) for v in valuations for m in v['appartenenze']}
    actual_memberships = {(s['lega'],team,pid) for s in states.values() for team,ids in s['rose'].items() for pid in ids}
    if expected_memberships != actual_memberships:
        raise RoseError('Tesseramenti A e C non coincidono')
    inputs += [Path(__file__), ROOT/'sot/rose_scambi.py', ROOT/'sot/rose.py']
    sources = [{**file_info(p),'percorso':str(p.relative_to(ROOT)) if p.is_relative_to(ROOT) else str(p)} for p in inputs]
    digest = D.fingerprint(sources)
    simulation = None
    if args.lega:
        if args.lega not in states:
            raise RoseError(f'Lega sconosciuta: {args.lega}')
        state = states[args.lega]
        other = D.canonical_team(state,args.controparte)
        operation = D.Exchange(state['lega'],state['mia_squadra'],other,args.cedi or (),args.ricevi or ())
        simulation = D.simulate(state,operation,configs[state['lega']],values)
        simulation.update(snapshot_id=digest, snapshot_fase_c=audit_c['snapshot_id'])
    catalogue, profiles, league_results, counts = [], [], [], []
    for league_id,state in states.items():
        packages = []
        for team in sorted(state['rose']):
            profile = D.roster_profile(state,team,values)
            profile.update(lega=league_id, mia_squadra=team==state['mia_squadra'])
            profiles.append(profile)
            packages.append(dict(squadra=team, uno=[list(p) for p in D.packages(state,team,1)],
                                 due=[list(p) for p in D.packages(state,team,2)]))
        league_counts = D.candidate_counts(state,values)
        counts.extend(league_counts)
        catalogue.append(dict(lega=league_id,mia_squadra=state['mia_squadra'],pacchetti_per_squadra=packages,
                              giocatori=[dict(giocatore_id_fc=pid,nome=row['nome_fc'],squadra_export=row['squadra'],
                                               ruolo_classic=row['ruolo_classic'],ruolo_mantra=row['ruolo_mantra'],
                                               costo_export=row['costo'],stato_stima=values[pid]['stato'])
                                         for pid,row in sorted(state['giocatori'].items())],
                              regola_enumerazione='Per ogni controparte: prodotto dei pacchetti uno x uno e due x due. Nessun filtro di ruolo.'))
        league_results.append(dict(lega=league_id,mia_squadra=state['mia_squadra'],**D.blockers(configs[league_id]),
                                   candidati_strutturali=sum(r['combinazioni'] for r in league_counts),
                                   controparti=len(league_counts)//2,candidati_valutati=0,shortlist=None,
                                   esito='valutazione_non_eseguita',due_per_uno='non_abilitato_senza_regole_e_reintegri'))
    exposure = []
    for v in valuations:
        memberships = [m for m in v['appartenenze'] if m['mia_squadra']]
        if memberships:
            exposure.append(dict(giocatore_id_fc=v['giocatore_id_fc'],nome=v['nome'],numero_leghe=len(memberships),
                                 leghe=sorted(m['lega'] for m in memberships),stato_stima=v['stato']))
    exposure.sort(key=lambda r:(-r['numero_leghe'],r['nome']))
    audit = dict(fase='D',stato='struttura_scambi_pronta; ranking_bloccato',snapshot_id=digest,
                 generato_utc=datetime.now(timezone.utc).isoformat(),stagione=settings['stagione'],
                 snapshot_fase_c=audit_c['snapshot_id'],leghe=len(states),squadre=len(profiles),
                 controparti=sum(r['controparti'] for r in league_results),
                 candidati_strutturali=sum(r['combinazioni'] for r in counts),
                 candidati_con_stime_individuali=sum(r['con_stime_individuali'] for r in counts),
                 candidati_valutati=0,scambi_raccomandati=None,
                 per_formato={k:sum(r['combinazioni'] for r in counts if r['formato']==k) for k in ('1x1','2x2')},fonti=sources)
    # Le simulazioni errate hanno già fallito prima di pubblicare output.
    out.mkdir(parents=True,exist_ok=True)
    dump(out/'catalogo_scambi.json',dict(snapshot_id=digest,leghe=catalogue))
    dump(out/'profili_rose_fase_d.json',profiles)
    dump(out/'scambi_per_lega.json',league_results)
    dump(out/'esposizione_mie_rose.json',exposure)
    dump(out/'audit_fase_d.json',audit)
    pd.DataFrame(counts).to_csv(out/'fase_d_controparti.csv',index=False,encoding='utf-8-sig')
    snapshot = out/'snapshots'/f'fase_d_{digest}.json'
    if not snapshot.exists():
        dump(snapshot,dict(audit=audit,catalogo=catalogue,profili=profiles,stato_leghe=league_results,esposizione=exposure,conteggi=counts))
    if simulation is not None:
        folder = out/'simulazioni'
        folder.mkdir(exist_ok=True)
        stem = f"{simulation['id'][:16]}_{digest[:16]}"
        path = folder/f'{stem}.json'
        if path.exists() and json.loads(path.read_text(encoding='utf-8')) != simulation:
            raise RoseError('Collisione fra identificativi di simulazione')
        dump(path,simulation)
        (folder/f'{stem}.md').write_text(simulation_markdown(simulation),encoding='utf-8')
        print(f'Simulazione: {folder / (stem+".md")}')
    lines = ['# Fantacalcio — Fase D', '',
             '**Completati catalogo e simulazione strutturale. Le raccomandazioni restano bloccate.**', '',
             f"{audit['leghe']} leghe, {audit['squadre']} rose e {audit['controparti']} controparti reali. "
             f"Il catalogo rappresenta esattamente {audit['per_formato']['1x1']:,} scambi 1×1 e {audit['per_formato']['2x2']:,} scambi 2×2.",
             'Sono combinazioni di giocatori posseduti, non scambi dichiarati legali o convenienti. '
             'Le operazioni 2×1 non sono abilitate senza regole e reintegri.', '',
             '## Stato per lega', '', '| Lega | Controparti | Candidati strutturali | Valutati | Shortlist |', '|---|---:|---:|---:|---|']
    lines += [f"| {r['lega']} | {r['controparti']} | {r['candidati_strutturali']} | 0 | non disponibile |" for r in league_results]
    lines += ['', '## Perché manca ancora una graduatoria', '',
              'La Fase C produce punti individuali della fonte, ma non punti schierabili di lega. '
              'Sommarli per ordinare uno scambio favorirebbe la quantità senza misurare la formazione, '
              'le sostituzioni e i modificatori. Per questo il beneficio per entrambe le squadre, '
              'la robustezza e la shortlist restano nulli. Non significa «nessuno scambio conveniente».', '',
              'Servono i regolamenti completi e il valutatore delle formazioni della Fase C. '
              'La compilazione dei campi da sola non attiva un calcolo dei punti ancora assente.', '']
    for r in league_results:
        lines.append(f"- **{r['lega']}**: "+', '.join(r['campi_regole_mancanti']))
    lines += ['', '## Copertura delle mie rose', '', '| Lega | Rosa | P / D / C / A | Con stima individuale | Senza stima |', '|---|---|---|---:|---|']
    for profile in profiles:
        if not profile['mia_squadra']: continue
        roles=' / '.join(str(profile['ruoli_classic'][r]) for r in ('p','d','c','a'))
        names=', '.join(values[p]['nome'] for p in profile['senza_stima']) or 'nessuno'
        lines.append(f"| {profile['lega']} | {cell(profile['squadra'])} | {roles} | {profile['con_stima_provider']}/{profile['giocatori']} | {cell(names)} |")
    lines += ['', 'I conteggi Classic e le etichette Mantra sono descrittivi. Non identificano ruoli scoperti '
              'senza moduli e vincoli confermati. I mancanti sono mantenuti nel catalogo, non trasformati in giocatori di valore zero.', '',
              '## Esposizione comune alle mie rose', '', '| Giocatore | Leghe |', '|---|---:|']
    lines += [f"| {cell(r['nome'])} | {r['numero_leghe']} |" for r in exposure if r['numero_leghe']>=3]
    lines += ['', 'Concentrazione descrittiva; non stima la correlazione del rischio né suggerisce di cedere un giocatore.', '',
              '## Comandi', '', 'Catalogo completo, riproducibile senza rete:', '', '```powershell',
              './.venv/Scripts/python.exe scripts/run_fantacalcio_fase_d.py', '```', '',
              'Simulazione manuale: aggiungere `--lega ID --controparte "Nome squadra" --cedi ID_FC --ricevi ID_FC`. '
              'Sono accettati uno o due ID per lato. Senza `--cedi/--ricevi` si verifica lo scambio nullo.', '',
              'Il comando scrive un report Markdown e JSON in `simulazioni/`, controlla proprietà e reversibilità, '
              'mostra le rose prima/dopo e conserva i costi come provenienza dell’export. Nessuna rosa originale viene modificata.', '',
              '## Artefatti e provenienza', '',
              '- `catalogo_scambi.json`: pacchetti di ogni squadra e regola di prodotto cartesiano; rappresentazione completa senza milioni di righe ridondanti.',
              '- `fase_d_controparti.csv`: conteggi esatti per controparte, formato, disponibilità delle stime e invarianza dei ruoli Classic.',
              '- `profili_rose_fase_d.json`: tutte le 46 rose con ID, ruoli e mancanti.',
              '- `scambi_per_lega.json`: blocchi espliciti e shortlist nulla.',
              '- `esposizione_mie_rose.json`: appartenenze multiple dell’utente, senza aggregare costi fra leghe.',
              '- `audit_fase_d.json` e `snapshots/fase_d_<hash>.json`: fonti, integrità A/B/C e risultato congelato.', '',
              'L’enumeratore `sot.rose_scambi.iter_candidates` restituisce ogni operazione senza tagli; '
              '`simulate` è usato anche dalla CLI. Nessuna graduatoria parallela o euristica sui prezzi.']
    (out/'fase_d.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in audit.items() if k!='fonti'},indent=2))
    print(f'Report: {out / "fase_d.md"}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
