"""Fase C: backtest dopo G5 e previsioni del provider; nessuna rete."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sot.rose import RoseError, file_info, rules_status
from sot import rose_valutazione as C


def dump(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False)+'\n', encoding='utf-8')


def records(frame):
    return json.loads(frame.to_json(orient='records', force_ascii=False))


def number(value):
    return 'n.d.' if value is None else f'{value:.2f}'.replace('.', ',')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT/'reports/fantacalcio_scambi')
    args = parser.parse_args(argv)
    out = args.output
    inputs = []

    def document(path):
        inputs.append(path)
        return json.loads(path.read_text(encoding='utf-8'))

    def parquet(path):
        inputs.append(path)
        return pd.read_parquet(path)

    settings = document(ROOT/'fantacalcio_rose/leghe.json')
    season = settings['stagione']
    if season != '2026-2027':
        raise RoseError('Protocollo Fase C attuale valido per il 2026/27')
    cards_b = document(out/'schede_comparative.json')
    audit_b = document(out/'audit_fase_b.json')
    if audit_b['stagione'] != season or audit_b['cutoff_statistiche'] != '2026-09-20':
        raise RoseError('Snapshot B incompatibile con il protocollo')
    # Collegare la previsione allo snapshot effettivamente letto, non a dati B obsoleti.
    for source in audit_b['fonti']:
        p = ROOT/source['percorso']
        if hashlib.sha256(p.read_bytes()).hexdigest() != source['sha256']:
            raise RoseError(f'Fase B da rigenerare: fonte modificata {p}')
    hist = parquet(ROOT/'data/processed/ITA-serie-a/fantacalcio_voti.parquet')
    matches = parquet(ROOT/'data/processed/ITA-serie-a/fantacalcio_partite.parquet')
    current = parquet(out/'voti_2026_2027_g1_g5.parquet')
    inputs.append(out/'partite_g1_g5_verificate.csv')
    current_matches = pd.read_csv(inputs[-1], parse_dates=['data'])
    if current.stagione.nunique() != 1 or not current.stagione.eq(season).all() or not current.giornata.between(1, 5).all():
        raise RoseError('Voti correnti fuori dal perimetro G1-G5')
    if not hist.stagione.lt(season).all():
        raise RoseError('Storico contiene la stagione bersaglio o stagioni successive')
    cutoff = C.validate_calendar(current, current_matches, season, complete=False)
    if str(cutoff.date()) != audit_b['cutoff_statistiche']:
        raise RoseError('Cutoff diverso dallo snapshot B')
    print('Validazione cronologica su tre stagioni, con calibrazione sul solo passato...', flush=True)
    wf, tables, calibration = C.walkforward(hist, matches)
    metrics = C.metrics(wf)
    by_role = C.metrics(wf, per_role=True)
    selection = C.select_models(wf)
    coverage = C.interval_coverage(wf)
    x = C.features(pd.concat([hist, current], ignore_index=True), season, cutoff)
    live_predictions, live_parameters = {}, []
    for horizon in C.HORIZONS:
        train = [frame for (s,h), frame in tables.items() if h == horizon and s < season]
        k, losses = C.tune(train, horizon)
        live_parameters.append(dict(orizzonte=horizon, stagioni_training=sorted({t.stagione.iloc[0] for t in train}),
                                    k={c: None if np.isinf(v) else v for c,v in k.items()}, griglia=losses))
        live_predictions[horizon] = C.predict(x, horizon, selection[horizon]['modello'], k).set_index('giocatore_id')
    inputs += [Path(__file__), ROOT/'sot/rose_valutazione.py', ROOT/'sot/rose.py',
               ROOT/'fantacalcio_rose/protocollo_fase_c.md']
    sources = [{**file_info(path), 'percorso':str(path.relative_to(ROOT))} for path in inputs]
    digest = hashlib.sha256(json.dumps(sources, sort_keys=True).encode()).hexdigest()
    values, flat = [], []
    radii = {(h,role,target):C.interval_radius(wf,h,selection[h]['modello'],role,target)
             for h in C.HORIZONS for role in ('p','d','c','a') for target in ('punti','presenze')}
    by_id = x.set_index('giocatore_id')
    for card in cards_b:
        ident = card['identita']
        player_id = ident['giocatore_id_fc']
        available = player_id in by_id.index
        value = dict(giocatore_id_fc=player_id, nome=ident['nome_fc'], club=ident['club_fc'],
                     ruolo_classic=ident['ruolo_classic'], appartenenze=card['appartenenze'],
                     stato='stima_provider' if available else 'non_stimabile_senza_righe_fc_g1_g5',
                     disponibilita_medica=None, probabilita_titolare=None,
                     fonte_voto='redazione', snapshot_id=digest, snapshot_fase_b=audit_b['snapshot_id'],
                     cutoff_statistiche=str(cutoff.date()), notizie_aggiornate_al=None,
                     orizzonti=[], indicatori_descrittivi={key:dict(corrente=card['corrente'].get(key),
                                                                  storico=card['storico_serie_a'].get(key))
                                                         for key in ['minuti','titolare','tiri_per90','sot_per90','gol_ws_per90']})
        if available:
            f = by_id.loc[player_id]
            value['campione'] = dict(voti_g1_g5=int(f.n_recent), voti_anno_precedente=None if pd.isna(f.n_previous) else int(f.n_previous),
                                    fallback_ruolo=bool(f.prior_ruolo), ruolo_modello=f.ruolo,
                                    fallback_ruolo_componenti={key:bool(f[f'prior_ruolo_{key}']) for key in C.COMPONENTS},
                                    probabilita_voto_recente=float(f.recent_p), probabilita_voto_storica=float(f.history_p))
        else:
            value['campione'] = None
        for horizon in C.HORIZONS:
            row = dict(orizzonte=horizon, giornate=[6,5+horizon], modello=selection[horizon]['modello'],
                       probabilita_voto=None, presenze_attese=None, voto_condizionato=None, bonus_fonte_condizionato=None,
                       fv_fonte_condizionato=None, punti_fonte_attesi=None, intervallo80_punti=None,
                       intervallo80_presenze=None, sensibilita_impiego=None, pesi_recenti=None)
            if available:
                p = live_predictions[horizon].loc[player_id]
                radius, n = radii[(horizon,f.ruolo,'punti')]
                n_radius, _ = radii[(horizon,f.ruolo,'presenze')]
                row.update(probabilita_voto=float(p.p), presenze_attese=float(p.presenze),
                           voto_condizionato=float(p.voto), bonus_fonte_condizionato=float(p.bonus),
                           fv_fonte_condizionato=float(p.fv_condizionato), punti_fonte_attesi=float(p.punti),
                           intervallo80_punti=[float(p.punti-radius), float(p.punti+radius)],
                           intervallo80_presenze=[max(0., float(p.presenze-n_radius)), min(float(horizon), float(p.presenze+n_radius))],
                           residui_intervallo=n, sensibilita_impiego={str(factor):float(np.clip(p.p*factor,0,1)*horizon*p.fv_condizionato) for factor in (.8,1.,1.2)},
                           pesi_recenti={c:float(p[f'peso_recente_{c}']) for c in C.COMPONENTS})
            value['orizzonti'].append(row)
            flat.append(dict(giocatore_id_fc=player_id, nome=value['nome'], club=value['club'], ruolo=value['ruolo_classic'], stato=value['stato'],
                             **{k:v for k,v in row.items() if not isinstance(v,(list,dict))}))
        values.append(value)
    league_results = []
    for league in settings['leghe']:
        status = rules_status(league)
        league_results.append(dict(lega=league['id'], mia_squadra=league['mia_squadra'],
                                   stato='calcolo_schierabile_da_implementare' if status['pronta_per_valutazione'] else 'regole_incomplete',
                                   **status, punti_schierabili=None, modificatore_atteso=None,
                                   valore_sul_sostituto=None, sensibilita_regole=None,
                                   giocatori=[dict(giocatore_id_fc=v['giocatore_id_fc'], squadra=m['squadra'],
                                                   mia_squadra=m['mia_squadra'], costo_export=m['costo'])
                                              for v in values for m in v['appartenenze'] if m['lega']==league['id']]))
    audit = dict(fase='C', stato='stime_provider_validate; contributo_schierabile_in_attesa_regole',
                 snapshot_id=digest, snapshot_fase_b=audit_b['snapshot_id'], generato_utc=datetime.now(timezone.utc).isoformat(),
                 cutoff_statistiche=str(cutoff.date()), stagione=season, schede=len(values),
                 giocatori_stimati=sum(v['stato']=='stima_provider' for v in values),
                 stagioni_prova=sorted(wf.stagione.unique()), selezione=selection,
                 calibrazione_storica=calibration, calibrazione_corrente=live_parameters,
                 copertura_intervalli=records(coverage), fonti=sources,
                 limitazioni=['Punti provider, non di lega o schierabili', 'Nessuna notizia medica/gerarchia corrente',
                              'Tre stagioni di prova; dipendenza fra giocatori/stagioni',
                              'Intervalli empirici, copertura di popolazione non garanzia individuale',
                              'Nessuna conversione dello storico estero in voti Serie A',
                              'Media orizzonte, senza correzione per avversario o modello specifico dei minuti'])
    # Output separati da Fase B e dallo storico, dopo tutti i controlli.
    out.mkdir(parents=True, exist_ok=True)
    wf.to_csv(out/'fase_c_backtest.csv', index=False)
    metrics.to_csv(out/'fase_c_metriche.csv', index=False)
    by_role.to_csv(out/'fase_c_metriche_per_ruolo.csv', index=False)
    coverage.to_csv(out/'fase_c_copertura_intervalli.csv', index=False)
    pd.DataFrame(flat).to_csv(out/'valutazioni_giocatori.csv', index=False, encoding='utf-8-sig')
    dump(out/'valutazioni_giocatori.json', values)
    dump(out/'valutazioni_per_lega.json', league_results)
    dump(out/'audit_fase_c.json', audit)
    (out/'snapshots').mkdir(exist_ok=True)
    snapshot = out/'snapshots'/f'fase_c_{digest}.json'
    if not snapshot.exists():
        dump(snapshot, dict(audit=audit, valutazioni=values, leghe=league_results, metriche=records(metrics), backtest=records(wf)))
    folder = out/'valutazioni'
    folder.mkdir(exist_ok=True)
    for v in values:
        lines=[f"# {v['nome']} — valutazione dopo G5", '',
               'Scala Redazione; punti della fonte, non punti di lega né contributo alle formazioni.',
               'Statistiche al 20 settembre 2026. Infortuni, disponibilità medica e gerarchie correnti non verificati.', '',
               f"Stato: {v['stato']}.", '']
        if v['campione']:
            c=v['campione']
            lines += [f"Voti G1–G5: {c['voti_g1_g5']}/5; anno precedente: {c['voti_anno_precedente'] if c['voti_anno_precedente'] is not None else 'n.d.'}. "
                      f"Prior di ruolo per assenza di storico: {'sì' if c['fallback_ruolo'] else 'no'}.", '']
        lines += ['| Orizzonte | Modello | P(voto) | Voti attesi | MV cond. | Bonus cond. | FV fonte cond. | Punti fonte | Intervallo empirico 80% |',
                  '|---|---|---:|---:|---:|---:|---:|---:|---|']
        for r in v['orizzonti']:
            interval='n.d.' if r['intervallo80_punti'] is None else ' – '.join(number(z) for z in r['intervallo80_punti'])
            lines.append(f"| G6–G{5+r['orizzonte']} | {r['modello']} | {number(r['probabilita_voto'])} | {number(r['presenze_attese'])} | {number(r['voto_condizionato'])} | {number(r['bonus_fonte_condizionato'])} | {number(r['fv_fonte_condizionato'])} | {number(r['punti_fonte_attesi'])} | {interval} |")
        lines += ['', 'Gli intervalli derivano dagli errori storici: non sono garanzie per il singolo giocatore. '
                  'P(voto) è la frequenza futura media stimata per giornata, non la probabilità di essere sano o titolare.', '',
                  '## Sensibilità all’impiego', '', 'Scenario con tasso a voto ±20%, rendimento condizionato fisso; non è un intervallo probabilistico.', '']
        for r in v['orizzonti']:
            if r['sensibilita_impiego']:
                lines.append(f"- {r['orizzonte']} giornate: " + ' / '.join(number(z) for z in r['sensibilita_impiego'].values()) + ' punti fonte (−20% / centrale / +20%).')
        lines += ['', f"[Scheda descrittiva](../schede/{v['giocatore_id_fc']}.md) · [Validazione, fonti e limiti](../fase_c.md).", '',
                  'Modificatori, formazione ottimale e valore sul sostituto attendono i regolamenti completi.', '', f"Snapshot `{digest}`."]
        (folder/f"{v['giocatore_id_fc']}.md").write_text('\n'.join(lines)+'\n', encoding='utf-8')
    lines=['# Fantacalcio — Fase C', '', '**Completati stime del provider e confronto cronologico. Il valore schierabile per lega resta aperto.**', '',
           f"{audit['giocatori_stimati']} giocatori stimati su {len(values)}; gli altri non hanno righe FC G1–G5 e restano senza previsione operativa.",
           'Orizzonti G6–G10, G6–G13 e G6–G38. Scala Redazione; nessuna regola delle leghe applicata per default.', '',
           '## Confronto fuori campione', '',
           'Calibrazione iniziale sulla transizione 2021/22 → 2022/23; prove su 2023/24, 2024/25, 2025/26. '
           'Ruoli e universo di giocatori ricavati dalle sole righe G1–G5, senza listoni futuri. '
           'Ogni peso è stimato soltanto su stagioni precedenti a quella prevista.', '',
           '| Orizzonte | MAE storico | MAE recente | MAE combinato | Scelta | Combinazione promossa |', '|---|---:|---:|---:|---|---|']
    for h, s in selection.items():
        e=s['mae_punti']
        lines.append(f"| {h} giornate | {number(e['storico'])} | {number(e['recente'])} | {number(e['combinato'])} | {s['modello']} | {'sì' if s['combinazione_promossa'] else 'no'} |")
    lines += ['', 'La combinazione passa solo se migliora entrambi i baseline anche in ciascuna stagione. '
              'Il confronto è descrittivo su tre stagioni, non prova causale del beneficio di uno scambio. '
              'L’eventuale baseline selezionato sui risultati non dispone di una seconda prova indipendente della selezione.', '',
              '## Copertura degli intervalli', '', 'Prova finale su 2025/26 usando solo residui 2023/24–2024/25; nominale 80%.', '',
              '| Orizzonte | Modello scelto | Copertura punti | Copertura presenze |', '|---|---|---:|---:|']
    for h,s in selection.items():
        c=coverage[coverage.orizzonte.eq(h)&coverage.modello.eq(s['modello'])].set_index('bersaglio')
        lines.append(f"| {h} | {s['modello']} | {number(100*c.loc['punti','copertura'])}% | {number(100*c.loc['presenze','copertura'])}% |")
    lines += ['', '## Limiti operativi', '',
              '- Presenza a voto separata da disponibilità medica, titolarità e minuti. Nessuna diagnosi dedotta dalle assenze.',
              '- Punti fonte = voti attesi × (voto condizionato + bonus condizionato); non sono punti schierabili né valore di mercato.',
              '- Nessuna correzione per avversario e nessuna conversione delle prestazioni estere in voto italiano.',
              '- Zero nei bersagli futuri significa nessun voto pubblicato su calendari completi; non inventa zero minuti. Gli s.v. non sono voti numerici.',
              '- Fallback di ruolo esplicito per chi non aveva storico italiano. I giocatori senza osservazioni FC G1–G5 sono fuori dal perimetro validato.',
              '- Intervalli empirici dagli errori storici; sensibilità ±20% dell’impiego come scenario separato. Nessun aggiustamento per infortuni non acquisiti.', '',
              '## Regole necessarie per completare il valore schierabile', '']
    for league in league_results:
        lines.append(f"- **{league['lega']}**: " + ', '.join(league['campi_da_confermare']))
    lines += ['', 'Modificatore, sostituti della rosa e sensibilità alle regole rimangono nulli. '
              'Il ranking degli scambi della Fase D non è stato avviato.', '',
              '## Riproduzione e fonti', '', '```powershell', './.venv/Scripts/python.exe scripts/run_fantacalcio_fase_c.py', '```', '',
              '[Protocollo fissato prima del confronto](../../fantacalcio_rose/protocollo_fase_c.md). '
              'Hash e calibrazioni in `audit_fase_c.json`; predizioni storiche in `fase_c_backtest.csv`, '
              'metriche per stagione in `fase_c_metriche.csv` e per ruolo in `fase_c_metriche_per_ruolo.csv`, '
              'con errore sulle presenze e Brier per turno. Snapshot immutabile in `snapshots/fase_c_<hash>.json`.', '',
              '## Le mie rose', '']
    for league in settings['leghe']:
        lines += [f"### {league['id']}", '', '| Giocatore | Voti attesi G6–G10 | FV fonte cond. | Punti fonte G6–G10 |', '|---|---:|---:|---:|']
        for v in values:
            if not any(m['lega']==league['id'] and m['mia_squadra'] for m in v['appartenenze']): continue
            r=v['orizzonti'][0]
            lines.append(f"| [{v['nome']}](valutazioni/{v['giocatore_id_fc']}.md) | {number(r['presenze_attese'])} | {number(r['fv_fonte_condizionato'])} | {number(r['punti_fonte_attesi'])} |")
    lines += ['', '## Tutti i giocatori', '']
    lines += [f"- [{v['nome']} — {v['club']}](valutazioni/{v['giocatore_id_fc']}.md)" for v in values]
    (out/'fase_c.md').write_text('\n'.join(lines)+'\n', encoding='utf-8')
    print(json.dumps(dict(schede=len(values), stimati=audit['giocatori_stimati'], selezione=selection, snapshot_id=digest), indent=2))
    print(f"Report: {out/'fase_c.md'}")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
