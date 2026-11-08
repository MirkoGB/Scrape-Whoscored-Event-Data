"""Raccolta prospettica locale e simulazione senza denaro degli Over.

Comandi: snapshot, quote FILE.json, combined FILE.json, plan AAAA-MM-GG,
settle FILE.json, report. Tutte le date operative vengono registrate adesso.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import uuid
from pathlib import Path

import pandas as pd

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from sot import config, over_paper as OP

ROOT=config.ROOT/"data/external/paper_over"


def evidence(path):
    p=Path(path).resolve()
    if not p.is_file():
        raise ValueError(f"Prova documentale non trovata: {p}")
    raw=p.read_bytes()
    sha=hashlib.sha256(raw).hexdigest()
    target=ROOT/"evidence"/(sha+p.suffix.lower())
    target.parent.mkdir(parents=True,exist_ok=True)
    if not target.exists():
        with target.open('xb') as f:
            f.write(raw)
    return {"evidence_file":str(target.relative_to(ROOT)),"evidence_sha256":sha}


def prediction_index():
    return {s["selection_id"]:{**s,"snapshot_id":r["id"]} for r in OP.load_records(ROOT/"predictions") for s in r["selections"]}


def snapshot():
    from sot import calendario as C, previsione as P, prior_stagione as PS, tentativi as T, totale as TOT, dispersion
    protocol=OP.freeze_protocol(ROOT)
    stamp=OP.utc_now()
    now=OP.utc(stamp).tz_convert('Europe/Rome')
    start=(now+pd.Timedelta(days=1)).date()
    end=(now+pd.Timedelta(days=15)).date()
    selections=[]
    inputs=[]
    ident='forecast_'+uuid.uuid4().hex[:16]
    for lg in config.LEAGUE_CODES:
        st=P.storia(config.SEASON_CORRENTE,league=lg)
        if pd.Timestamp(st.date.max()).date()>=now.date():
            raise ValueError("Dati con data odierna/futura: escluderli prima del fit prospettico")
        path=config.team_match(lg,config.SEASON_CORRENTE)
        inputs.append({"file":str(path.relative_to(config.ROOT)),"sha256":hashlib.sha256(path.read_bytes()).hexdigest(),"training_max":str(st.date.max())})
        counts=st.groupby('team').matchId.nunique()
        context=PS.contesto(config.SEASON_CORRENTE,league=lg) if (counts+1<config.BURN_IN_ROUND).any() else None
        tab=P.tabella_completa(config.SEASON_CORRENTE,league=lg,contesto=context)
        raw=C.calendario(lg,config.SEASON_CORRENTE)
        raw['parsed']=raw.data_fonte.map(C.data)
        raw=raw[raw.parsed.notna()&raw.parsed.dt.date.between(start,end)].copy()
        cal=P.tabella_calendario(C.con_turno(raw),config.SEASON_CORRENTE,league=lg,contesto=context,tab=tab)
        index=tab.set_index(['squadra','avversario','campo'])
        for _,r in cal.iterrows():
            date=str(C.data(r.data_fonte).date())
            common=dict(league=lg,match_id=str(r.matchId),match_date=date,home=r.casa,away=r.trasferta,
                        published_at=stamp,training_through=str(st.date.max().date()),regime=r.regime,
                        model_version='production_two_regimes',snapshot_id=ident)
            for target,lines,total_lines in [('shots',T.LINEE_TIRI,TOT.LINEE_TOTALE_TIRI),('sot',P.LINEE_SOT,TOT.LINEE_TOTALE_SOT)]:
                for side,team,opp,campo in [('home',r.casa,r.trasferta,'casa'),('away',r.trasferta,r.casa,'trasferta')]:
                    if (team,opp,campo) in index.index:
                        tr=index.loc[(team,opp,campo)]
                        lam=float(tr['lambda_tentativi' if target=='shots' else 'lambda_sot'])
                        dispersion_r=float(tr['r' if target=='shots' else 'r_sot'])
                    else:
                        lam=float(r['lam_casa' if side=='home' else 'lam_trasferta'] if target=='shots' else r['sot_casa' if side=='home' else 'sot_trasferta'])
                        dispersion_r=float(tab['r' if target=='shots' else 'r_sot'].iloc[0])
                    for line in lines:
                        key=f'{ident}|{lg}|{r.matchId}|{target}|{side}|{line}'
                        p=float(dispersion.p_over([lam],line,dispersion_r)[0])
                        selections.append({**common,'selection_id':key,'target':target,'scope':'team','side':side,'line':float(line),'p':p})
                for line in total_lines:
                    key=f'{ident}|{lg}|{r.matchId}|{target}|total|{line}'
                    prefix='p_tot_' if target=='shots' else 'p_tot_sot_'
                    selections.append({**common,'selection_id':key,'target':target,'scope':'total','side':'total','line':float(line),'p':float(r[prefix+str(line)])})
        print(lg,len(cal),'partite future',flush=True)
    # La pubblicazione è il momento in cui il calcolo finisce, non il suo avvio.
    published=OP.utc_now()
    for selection in selections:
        selection['published_at']=published
    record=OP.save_record(ROOT/'predictions',dict(id=ident,published_at=published,generation_started_at=stamp,inputs=inputs,protocol_sha256=protocol['sha256'],selections=selections))
    print('Snapshot:',record['id'],'selezioni:',len(selections))
    pd.DataFrame(selections).to_csv(config.REPORTS/'over_2627_catalogo_quote.csv',index=False)


def capture_quote(path):
    row=json.loads(Path(path).read_text(encoding='utf-8-sig'))
    p=prediction_index()[row['selection_id']]
    now=OP.utc_now()
    protocol=OP.freeze_protocol(ROOT)
    OP.validate_quote(row,p,now,protocol)
    record={**p,**{k:row[k] for k in ('bookmaker','source_url','rules_url','observed_at','kickoff','settlement_rule')},
            'over_odds':float(row['over_odds']),'under_odds':float(row['under_odds']) if row.get('under_odds') else None,
            'recorded_at':now,'id':'quote_'+uuid.uuid4().hex[:16],**evidence(row['evidence_path'])}
    print(OP.save_record(ROOT/'quotes',record)['id'])


def capture_combined(path):
    row=json.loads(Path(path).read_text(encoding='utf-8-sig'))
    quotes={q['id']:q for q in OP.load_records(ROOT/'quotes')}
    legs=[quotes[k] for k in row['quote_ids']]
    if not 2<=len(legs)<=5:
        raise ValueError('Una quota multipla richiede 2–5 selezioni')
    now=OP.utc_now()
    protocol=OP.freeze_protocol(ROOT)
    if len({x['match_date'] for x in legs})!=1:
        raise ValueError('Le selezioni devono appartenere alla stessa data di gioco')
    if row['bookmaker']!=legs[0]['bookmaker']:
        raise ValueError('Bookmaker diverso dalle selezioni')
    for q in legs:
        OP.validate_quote({**q,'observed_at':row['observed_at'],'evidence_path':row['evidence_path']},q,now,protocol)
    OP.coupon_metrics(legs,float(row['odds']))
    if not row.get('source_url'):
        raise ValueError('URL della quota multipla richiesto')
    record=dict(id='combined_'+uuid.uuid4().hex[:16],quote_ids=row['quote_ids'],bookmaker=row['bookmaker'],
                observed_at=row['observed_at'],recorded_at=now,odds=float(row['odds']),source_url=row['source_url'],**evidence(row['evidence_path']))
    print(OP.save_record(ROOT/'combined',record)['id'])


def plan(day):
    if day != str(pd.Timestamp(day).date()):
        raise ValueError('La data deve essere nel formato AAAA-MM-GG')
    protocol=OP.freeze_protocol(ROOT)
    previous=OP.load_records(ROOT/'decisions')
    if any(d['day']==day for d in previous):
        raise ValueError('Decisione di questa data già congelata: non si sostituisce')
    if previous and day<=max(d['day'] for d in previous):
        raise ValueError('Le decisioni devono procedere in ordine cronologico')
    clock=OP.utc_now()
    if day<protocol['test_from'] or day<str(OP.utc(clock).tz_convert('Europe/Rome').date()):
        raise ValueError('Non è consentito creare un piano retrospettivo')
    results={r['quote_id']:r for r in OP.load_records(ROOT/'settlements')}
    results.update({f"{r['decision_id']}:{r['size']}":r for r in OP.load_records(ROOT/'coupon_settlements')})
    performance=OP.performance(previous,results,protocol)
    plans=OP.select_slips(OP.load_records(ROOT/'quotes'),OP.load_records(ROOT/'combined'),protocol,day,clock)
    for p,stats in zip(plans,performance):
        reason=None
        if stats['pending']:
            reason='precedente schedina ancora da liquidare'
        elif stats['bankroll']<protocol['daily_budget']:
            reason='capitale virtuale insufficiente'
        elif (stats['max_drawdown'] or 0)>=protocol['stop_drawdown']:
            reason='limite di perdita dal picco raggiunto'
        if reason:
            p.update(status='no_bet',stake=0.,legs=[],metrics=None,reason=reason)
    record=dict(id='decision_'+day,day=day,recorded_at=clock,protocol_sha256=protocol['sha256'],plans=plans)
    OP.save_record(ROOT/'decisions',record)
    for p in plans:
        print(p['size'],p['status'],p['reason'])


def settle(path):
    row=json.loads(Path(path).read_text(encoding='utf-8-sig'))
    q=next(q for q in OP.load_records(ROOT/'quotes') if q['id']==row['quote_id'])
    now=OP.utc_now()
    if OP.utc(now)<=OP.utc(q['kickoff'])+pd.Timedelta(minutes=110):
        raise ValueError('Attendere il termine della partita')
    if row.get('result') not in ('won','lost','void') or not row.get('source_url'):
        raise ValueError('Esito won/lost/void e URL della liquidazione richiesti')
    if row['result']!='void':
        value=float(row['observed_count'])
        if not value.is_integer() or value<0 or not pd.notna(value):
            raise ValueError('Conteggio osservato non valido')
        if ('won' if value>q['line'] else 'lost')!=row['result']:
            raise ValueError('Esito e conteggio non coerenti')
    record=dict(id='settlement_'+q['id'],quote_id=q['id'],recorded_at=now,result=row['result'],
                observed_count=row.get('observed_count'),source_url=row['source_url'],**evidence(row['evidence_path']))
    print(OP.save_record(ROOT/'settlements',record)['id'])


def settle_slip(path):
    row=json.loads(Path(path).read_text(encoding='utf-8-sig'))
    decision=next(d for d in OP.load_records(ROOT/'decisions') if d['id']==row['decision_id'])
    plan=next(p for p in decision['plans'] if p['size']==int(row['size']))
    receipts={r['quote_id']:r for r in OP.load_records(ROOT/'settlements')}
    status=OP.settle_coupon(plan,receipts)
    if status['status']!='needs_bookmaker_settlement':
        raise ValueError('Liquidazione complessiva riservata a multiple con tutti gli esiti noti e almeno un annullamento')
    gross=float(row['gross_return'])
    if not pd.notna(gross) or not 0<=gross<float('inf') or not row.get('source_url'):
        raise ValueError('Ritorno lordo non negativo e fonte richiesti')
    now=OP.utc_now()
    if any(OP.utc(now)<=OP.utc(q['kickoff'])+pd.Timedelta(minutes=110) for q in plan['legs']):
        raise ValueError('Attendere il termine di tutte le gare')
    record=dict(id=f"coupon_{decision['id']}_{plan['size']}",decision_id=decision['id'],size=plan['size'],
                gross_return=gross,recorded_at=now,source_url=row['source_url'],**evidence(row['evidence_path']))
    print(OP.save_record(ROOT/'coupon_settlements',record)['id'])


def main():
    p=argparse.ArgumentParser(description=__doc__)
    sub=p.add_subparsers(dest='command',required=True)
    for cmd in ('snapshot','report'):
        sub.add_parser(cmd)
    for cmd in ('quote','combined','settle','settle-slip'):
        sub.add_parser(cmd).add_argument('file')
    sub.add_parser('plan').add_argument('day')
    args=p.parse_args()
    if args.command=='snapshot':snapshot()
    elif args.command=='quote':capture_quote(args.file)
    elif args.command=='combined':capture_combined(args.file)
    elif args.command=='plan':plan(args.day)
    elif args.command=='settle':settle(args.file)
    elif args.command=='settle-slip':settle_slip(args.file)
    from scripts.analizza_over_2627 import main as report
    report()


if __name__=='__main__':
    main()
