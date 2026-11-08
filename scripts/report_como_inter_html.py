# -*- coding: utf-8 -*-
"""Build a standalone, printable HTML dossier with extended match statistics."""
from __future__ import annotations

import argparse
import base64
import html
import json
import re
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import pandas as pd
from threadpoolctl import threadpool_limits
from sot import match_report_stats as M


def esc(s):return html.escape(str(s),quote=True)
def num(x,d=1):return f"{x:.{d}f}".replace(".",",")


def data_uri(path):
    mime="image/png" if path.suffix==".png" else "text/csv;charset=utf-8"
    return f"data:{mime};base64,"+base64.b64encode(path.read_bytes()).decode("ascii")


def inline(s,out):
    """Render the small, known Markdown vocabulary in the original dossier."""
    pat=r"!\[([^\]]*)\]\(([^)]+)\)|\[([^\]]+)\]\(([^)]+)\)|\*\*(.+?)\*\*|`([^`]+)`"
    result=[];end=0
    for m in re.finditer(pat,s):
        result.append(esc(s[end:m.start()]));a,img,label,url,bold,code=m.groups()
        if img:
            path=(out/img).resolve()
            if path.parent!=out.resolve():raise ValueError("Unexpected image path")
            result.append(f'<img src="{data_uri(path)}" alt="{esc(a)}" loading="lazy">')
        elif url:
            href=url if url.startswith(("https://","http://","#")) else "#sources"
            result.append(f'<a href="{esc(href)}">{esc(label)}</a>')
        elif bold:result.append(f'<strong>{esc(bold)}</strong>')
        else:result.append(f'<code>{esc(code)}</code>')
        end=m.end()
    result.append(esc(s[end:]))
    return "".join(result)


def markdown(text,out):
    lines=text.splitlines();parts=[];i=0
    while i<len(lines):
        line=lines[i]
        if not line.strip():i+=1;continue
        if line.startswith("```"):
            buf=[];i+=1
            while i<len(lines) and not lines[i].startswith("```"):buf.append(lines[i]);i+=1
            parts.append("<pre><code>"+esc("\n".join(buf))+"</code></pre>");i+=1;continue
        if line.startswith("|"):
            rows=[]
            while i<len(lines) and lines[i].startswith("|"):
                cells=[s.strip() for s in lines[i].strip().strip("|").split("|")]
                if not all(re.fullmatch(r"[-: ]+",c) for c in cells):rows.append(cells)
                i+=1
            parts.append('<div class="table-scroll" tabindex="0" role="region" aria-label="Tabella del dossier"><table><thead><tr>'+"".join("<th>"+inline(c,out)+"</th>" for c in rows[0])+"</tr></thead><tbody>"+
                "".join("<tr>"+"".join("<td>"+inline(c,out)+"</td>" for c in row)+"</tr>" for row in rows[1:])+"</tbody></table></div>")
            continue
        if line.startswith("- "):
            buf=[]
            while i<len(lines) and lines[i].startswith("- "):
                buf.append("<li>"+inline(lines[i][2:],out)+"</li>");i+=1
            parts.append("<ul>"+"".join(buf)+"</ul>");continue
        heading=re.match(r"^(#{1,6}) (.*)",line)
        if heading:
            level=min(len(heading[1])+1,6)
            parts.append(f"<h{level}>"+inline(heading[2],out)+f"</h{level}>");i+=1;continue
        buf=[line];i+=1
        while i<len(lines) and lines[i].strip() and not re.match(r"^(#|\||- |```)",lines[i]):
            buf.append(lines[i]);i+=1
        parts.append("<p>"+inline(" ".join(buf),out)+"</p>")
    return "\n".join(parts)


def stat_rows(result):
    rows=[];rare={"red_cards","penalty_shots","woodwork"}
    for r in result["rows"]:
        key=r["key"];nd=2 if key in rare else 1
        cells=[]
        for side in (0,1):
            lo,hi=r["interval80"][side]
            cell=f'<span class="estimate">{num(r["mean"][side],nd)}</span><span class="range">{lo}–{hi}</span>'
            if key in rare:cell+=f'<span class="event-prob">≥1: {num(100*r["probability_at_least_one"][side],0)}%</span>'
            cells.append(cell)
        if key=="aerial_duels":total='<span class="not-summed">Stesso duello<br>su due lati</span>'
        else:
            lo,hi=r["total_interval80"]
            total=f'<span class="estimate">{num(r["total_mean"],nd)}</span><span class="range">{lo}–{hi}</span>'
            if key in rare:total+=f'<span class="event-prob">≥1: {num(100*r["total_probability_at_least_one"],0)}%</span>'
        ratio=r["current_calibration"]
        calibration=f'Osservato/previsto nella stagione corrente: {num(ratio,2)} (ideale: 1).'
        note=f'{r["definition"]} Metodo: {r["method"]}. Errore medio nel test storico: {num(r["holdout_mae"],2)}. {calibration}'
        if r["current_coverage80"] is not None:note+=f' Copertura attuale dell’intervallo nominale 80%: {num(100*r["current_coverage80"],0)}%.'
        else:note+=' Intervallo indicativo: non include l’incertezza della quota condizionata.'
        rows.append(f'<tr data-group="{esc(r["group"])}" data-label="{esc(r["label"].lower())}" data-key="{key}">'
            f'<th scope="row">{esc(r["label"])}<details class="definition"><summary>Definizione e verifica</summary><p>{esc(note)}</p></details></th>'
            f'<td class="inter-value">{cells[0]}</td><td class="como-value">{cells[1]}</td><td>{total}</td></tr>')
    return "\n".join(rows)


def validation_rows(result):
    rows=[]
    for r in result["rows"]:
        baseline="—" if r["baseline_mae"] is None else num(r["baseline_mae"],2)
        coverage="Indicativo" if r["current_coverage80"] is None else num(100*r["current_coverage80"],0)+"%"
        rows.append(f'<tr><th scope="row">{esc(r["label"])}</th><td>{num(r["holdout_mae"],2)}</td><td>{baseline}</td>'
            f'<td>{num(r["current_calibration"],2)}</td><td>{coverage}</td></tr>')
    return "".join(rows)


def render(out,result):
    source=(out/"report.md").read_text(encoding="utf-8")
    template=(ROOT/"scripts/templates/inter_como_report.html").read_text(encoding="utf-8")
    profiles=pd.read_csv(out/"team_profiles.csv")
    venue=profiles[profiles.scope.eq("campo_partita")]
    venue_rows="".join(f'<tr><th scope="row">{esc(r.team)} {"in casa" if r.team=="Inter" else "fuori casa"}</th>'
        f'<td>{esc(r.season)}</td><td>{r.n}</td><td>{num(r.shots)}</td><td>{num(r.sot)}</td><td>{num(r.shots_against)}</td></tr>' for r in venue.itertuples())
    rates=result["rates"]
    rate_rows=[]
    for k,label,note in [("possession_proxy","Quota di possesso stimata dai tocchi","Proxy: non è il possesso ufficiale misurato sul tempo."),
                         ("pass_accuracy","Precisione dei passaggi","Passaggi riusciti / tentati, stessa definizione degli eventi."),
                         ("shot_accuracy","Precisione al tiro","Tiri in porta / tiri totali attesi.")]:
        r=rates[k]
        rate_rows.append(f'<tr><th scope="row">{label}<span class="row-note">{note}</span></th><td>{num(r["mean"][0])}%</td><td>{num(r["mean"][1])}%</td></tr>')
    o=result["original_outcomes"]
    vals={"STAT_ROWS":stat_rows(result),"RATE_ROWS":"".join(rate_rows),"VALIDATION_ROWS":validation_rows(result),
        "VENUE_ROWS":venue_rows,"ORIGINAL_REPORT":markdown(source,out),
        "NETWORK_IMAGE":data_uri(out/"passing_networks.png"),"CSV_URI":data_uri(out/"extended_forecast.csv"),
        "HOME_PROB":num(o["home"]*100),"DRAW_PROB":num(o["draw"]*100),"AWAY_PROB":num(o["away"]*100),
        "HOME_WIDTH":str(o["home"]*100),"DRAW_WIDTH":str(o["draw"]*100),"AWAY_WIDTH":str(o["away"]*100),
        "BOTH_SCORE":num(o["both_score"]*100),"OVER25":num(o["over25"]*100),
        "SCORELINES":", ".join(f'<strong>{esc(r["score"])}</strong> ({num(100*r["probability"])}%)' for r in o["scorelines"][:3]),
        "STAT_COUNT":str(len(result["rows"])),
        "PAYLOAD":json.dumps({"cutoff":result["cutoff"],"rows":result["rows"],"rates":rates},ensure_ascii=False).replace("<","\\u003c"),
    }
    for key,value in vals.items():template=template.replace("@@"+key+"@@",value)
    if re.search(r"@@[A-Z_]+@@",template):raise ValueError("Unresolved HTML placeholder")
    (out/"report.html").write_text(template,encoding="utf-8")
    print(f'HTML: {out/"report.html"}',flush=True)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--render-only",action="store_true")
    args=parser.parse_args()
    out=ROOT/"reports/inter_como_2026-11-08"
    if args.render_only:result=json.loads((out/"extended_forecast.json").read_text(encoding="utf-8"))
    else:
        with threadpool_limits(limits=1):
            data,stamp=M.build(ROOT,out)
            result=M.fit_all(data,out,json.loads((out/"forecast.json").read_text(encoding="utf-8")),stamp)
    render(out,result)


if __name__=="__main__":main()
