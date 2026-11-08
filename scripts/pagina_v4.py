# -*- coding: utf-8 -*-
"""La pagina locale di V4: scegli squadra, avversario e campo.

**Autonoma**: nessun CDN, nessun font remoto, nessuna richiesta di rete. Un test
lo pretende, perche' «pagina locale» vuol dire che funziona offline.

**Nessuna quota** (vincolo 3): la pagina mostra probabilita' e quota di
**pareggio** (`1/p`), che e' il punto in cui il guadagno sarebbe zero — non una
previsione di prezzo. Non propone quote e non calcola guadagni: nel repository
non ci sono prezzi di mercato reali, e generarli da questo stesso modello e' il
codice archiviato in `legacy/`.
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

_CSS = """
:root{--bg:#fbfbfa;--fg:#1a1a18;--mut:#6b6b66;--line:#e2e2dd;--acc:#2f6f4f;
--card:#fff;--warn:#8a5a00}
@media (prefers-color-scheme:dark){:root{--bg:#16171a;--fg:#e9e9e6;--mut:#9a9a94;
--line:#2c2e33;--acc:#7fbf9a;--card:#1e2024;--warn:#d9a441}}
*{box-sizing:border-box}
body{margin:0;padding:2rem 1rem 4rem;background:var(--bg);color:var(--fg);
font:15px/1.6 ui-sans-serif,system-ui,-apple-system,Segoe UI,Roboto,sans-serif}
.wrap{max-width:52rem;margin:0 auto}
h1{font-size:1.5rem;margin:0 0 .2rem;letter-spacing:-.01em}
.sub{color:var(--mut);font-size:.9rem;margin-bottom:1.6rem}
.card{background:var(--card);border:1px solid var(--line);border-radius:10px;
padding:1.1rem 1.2rem;margin-bottom:1.1rem}
.row{display:flex;gap:.8rem;flex-wrap:wrap;align-items:flex-end}
.f{display:flex;flex-direction:column;gap:.25rem;flex:1 1 11rem}
label{font-size:.78rem;color:var(--mut);text-transform:uppercase;
letter-spacing:.04em}
select{padding:.5rem .6rem;border:1px solid var(--line);border-radius:7px;
background:var(--bg);color:var(--fg);font:inherit}
.big{display:flex;gap:2.2rem;flex-wrap:wrap;margin:.2rem 0 .1rem}
.big div{min-width:8rem}
.big .n{font-size:2rem;font-weight:640;letter-spacing:-.02em;
font-variant-numeric:tabular-nums;color:var(--acc)}
.big .l{font-size:.78rem;color:var(--mut)}
table{width:100%;border-collapse:collapse;font-variant-numeric:tabular-nums}
th,td{padding:.42rem .5rem;border-bottom:1px solid var(--line);text-align:right}
th:first-child,td:first-child{text-align:left}
th{font-size:.76rem;color:var(--mut);text-transform:uppercase;
letter-spacing:.04em;font-weight:600}
.scroll{overflow-x:auto}
.bar{height:5px;background:var(--acc);border-radius:3px;opacity:.85}
.note{font-size:.84rem;color:var(--mut);margin-top:.5rem}
.warn{color:var(--warn);font-weight:600}
ul{margin:.4rem 0 0;padding-left:1.1rem}li{margin:.18rem 0}
"""

_JS = """
const S=DATI.righe, L=DATI.linee, R=DATI.r;
const sq=document.getElementById('sq'), av=document.getElementById('av'),
      cp=document.getElementById('cp');
const squadre=[...new Set(S.map(r=>r.s))].sort();
function opts(el,vals,sel){el.innerHTML=vals.map(v=>
  `<option${v===sel?' selected':''}>${v}</option>`).join('')}
function avversari(s){return squadre.filter(x=>x!==s)}
function fmt(x,n){return x.toLocaleString('it-IT',
  {minimumFractionDigits:n,maximumFractionDigits:n})}
function aggiorna(){
  const s=sq.value, a=av.value, c=cp.value;
  const r=S.find(x=>x.s===s&&x.a===a&&x.c===c);
  if(!r){document.getElementById('out').innerHTML='<p>coppia non disponibile</p>';return}
  const maxp=Math.max(...r.p);
  let righe=L.map((ln,i)=>`<tr><td>Over ${fmt(ln,1)}</td>
    <td>${fmt(100*r.p[i],1)}%</td><td>${fmt(1/r.p[i],2)}</td>
    <td style="width:38%"><div class="bar" style="width:${100*r.p[i]/maxp}%"></div></td>
    </tr>`).join('');
  document.getElementById('out').innerHTML=`
   <div class="big">
     <div><div class="n">${fmt(r.lam,2)}</div><div class="l">tiri attesi</div></div>
     <div><div class="n">${fmt(r.sot,2)}</div><div class="l">di cui in porta</div></div>
     <div><div class="n">${fmt(100*r.sot/r.lam,1)}%</div><div class="l">precisione implicita</div></div>
   </div>
   <div class="scroll"><table><thead><tr><th>linea</th><th>probabilita'</th>
     <th>quota di pareggio</th><th></th></tr></thead><tbody>${righe}</tbody></table></div>
   <p class="note">La <em>quota di pareggio</em> e' <code>1/p</code>: il prezzo a cui
   la scommessa avrebbe guadagno atteso zero. <strong>Non e' una previsione di
   prezzo</strong> e questa pagina non ne propone: nel repository non ci sono
   quote di mercato reali.</p>`;
}
sq.onchange=()=>{opts(av,avversari(sq.value),
  avversari(sq.value).includes(av.value)?av.value:avversari(sq.value)[0]);aggiorna()};
av.onchange=cp.onchange=aggiorna;
opts(sq,squadre,'Como');opts(av,avversari('Como'),'Inter');aggiorna();
"""


def scrivi(tab: pd.DataFrame, out: Path, stagione: str, come_di: str,
           r: float, linee: tuple[float, ...], limiti: list[str]) -> None:
    """Scrive la pagina autonoma dai dati gia' calcolati."""
    righe = [{"s": row["squadra"], "a": row["avversario"], "c": row["campo"],
              "lam": round(float(row["lambda_tentativi"]), 4),
              "sot": round(float(row["lambda_sot"]), 4),
              "p": [round(float(row[f"p_over_{ln}"]), 6) for ln in linee]}
             for _, row in tab.iterrows()]
    dati = {"righe": righe, "linee": list(linee), "r": round(float(r), 3)}

    html = f"""<!doctype html>
<html lang="it"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Tiri attesi — Serie A {stagione}</title>
<style>{_CSS}</style></head><body><div class="wrap">
<h1>Tiri attesi per squadra-partita</h1>
<div class="sub">Serie A {stagione} · modello aggiornato al {come_di} ·
dispersione NB2 <code>r = {r:.1f}</code> · Fase 12 / V4</div>

<div class="card"><div class="row">
  <div class="f"><label for="sq">squadra</label><select id="sq"></select></div>
  <div class="f"><label for="av">avversario</label><select id="av"></select></div>
  <div class="f"><label for="cp">campo</label>
    <select id="cp"><option>casa</option><option>trasferta</option></select></div>
</div></div>

<div class="card" id="out"></div>

<div class="card"><strong>Limiti, accanto ai numeri e non in fondo</strong>
<ul>{''.join(f'<li>{x}</li>' for x in limiti)}</ul></div>

<p class="note">Pagina locale e autonoma: nessuna richiesta di rete.
Rigenerabile con <code>scripts/run_fase12_v4.py</code>.</p>
</div>
<script>const DATI={json.dumps(dati, ensure_ascii=False)};</script>
<script>{_JS}</script></body></html>"""
    out.write_text(html, encoding="utf-8")
