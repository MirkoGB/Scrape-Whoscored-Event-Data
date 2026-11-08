# -*- coding: utf-8 -*-
"""Fase 15 / P1 - la pagina delle previsioni, a GIORNATA.

E' la pagina della Fase 14 rifatta su tre assi, e nessuno dei tre e' cosmetico:

1. **si sceglie una partita vera**, dal calendario della stagione in corso
   (Fase 15 / C1), invece di comporre una coppia con quattro menu a tendina.
   Il raggruppamento e' per **giornata** dove la giornata c'e' davvero, e la
   pagina **dichiara riga per riga** da dove viene il turno: la giornata della
   fonte, una deduzione dalla data, o un blocco di date;
2. **il TOTALE di partita**, cioe' la somma delle due squadre, che e' cio' che
   l'utente ha chiesto. Viene da T1: `lam_totale = lam_casa + lam_trasferta` e'
   **esatto** qualunque sia la dipendenza fra i due lati, e cio' che la
   dipendenza rompe e' la dispersione - assorbita da `r_tot`, stimata sui
   totali osservati e **presa da quel campionato**;
3. **il limite accanto al numero** (vincolo 5): il totale e' sotto-calibrato, la
   pendenza di quel campionato sta nella stessa riga della probabilita', e la
   pagina non la nasconde in fondo.

**La modalita' a coppia libera resta**, come secondo pannello: e' utile, e
toglierla avrebbe fatto sparire una risposta che il repository sa gia' dare.

**Autonoma**: nessun CDN, nessun font remoto, nessuna richiesta di rete. Un test
lo pretende, perche' <<pagina locale>> vuol dire che funziona offline.

**Nessuna quota** (vincolo 3): si mostra la probabilita' e la quota di
**pareggio** (`1/p`), che e' il punto in cui il guadagno sarebbe zero, mai una
previsione di prezzo.

**Questo modulo non calcola niente**: serializza. Un solo conto qui e la pagina
potrebbe divergere dal modello senza che nessuno se ne accorga - un test vieta
`TeamModel`, `fit(` e compagnia nel sorgente.
"""
from __future__ import annotations

import json
from pathlib import Path

_CSS = """
:root{--bg:#fbfbfa;--fg:#1a1a18;--mut:#6b6b66;--line:#e2e2dd;--acc:#2f6f4f;
--acc2:#4a5fa5;--acc3:#8a4f7d;--card:#fff;--warn:#8a5a00;--sel:#eaf3ee}
@media (prefers-color-scheme:dark){:root{--bg:#16171a;--fg:#e9e9e6;--mut:#9a9a94;
--line:#2c2e33;--acc:#7fbf9a;--acc2:#8fa4dd;--acc3:#d09ac4;--card:#1e2024;
--warn:#d9a441;--sel:#22302a}}
*{box-sizing:border-box}
body{margin:0;padding:2rem 1rem 4rem;background:var(--bg);color:var(--fg);
font:15px/1.6 ui-sans-serif,system-ui,-apple-system,Segoe UI,Roboto,sans-serif}
.wrap{max-width:64rem;margin:0 auto}
h1{font-size:1.5rem;margin:0 0 .2rem;letter-spacing:-.01em}
h2{font-size:.95rem;margin:1.2rem 0 .4rem;letter-spacing:.01em}
h3{font-size:.82rem;margin:1rem 0 .3rem;color:var(--mut);
text-transform:uppercase;letter-spacing:.05em}
.sub{color:var(--mut);font-size:.9rem;margin-bottom:1.6rem}
.card{background:var(--card);border:1px solid var(--line);border-radius:10px;
padding:1.1rem 1.2rem;margin-bottom:1.1rem}
.row{display:flex;gap:.8rem;flex-wrap:wrap;align-items:flex-end}
.f{display:flex;flex-direction:column;gap:.25rem;flex:1 1 10rem}
label{font-size:.78rem;color:var(--mut);text-transform:uppercase;
letter-spacing:.04em}
select{padding:.5rem .6rem;border:1px solid var(--line);border-radius:7px;
background:var(--bg);color:var(--fg);font:inherit;max-width:100%}
.tabs{display:flex;gap:.4rem;margin-bottom:1.1rem;flex-wrap:wrap}
.tab{padding:.45rem .9rem;border:1px solid var(--line);border-radius:999px;
background:var(--card);color:var(--mut);cursor:pointer;font-size:.85rem}
.tab[aria-selected=true]{background:var(--sel);color:var(--fg);
border-color:var(--acc);font-weight:600}
.grid{display:grid;gap:.6rem;margin-top:.9rem;
grid-template-columns:repeat(auto-fill,minmax(15rem,1fr))}
.m{text-align:left;padding:.6rem .75rem;border:1px solid var(--line);
border-radius:9px;background:var(--card);color:var(--fg);cursor:pointer;
font:inherit;display:flex;justify-content:space-between;gap:.6rem;
align-items:center}
.m:hover{border-color:var(--acc)}
.m[aria-pressed=true]{background:var(--sel);border-color:var(--acc)}
.m .nm{display:flex;flex-direction:column;line-height:1.3;min-width:0}
.m .nm span{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.m .tot{font-size:1.15rem;font-weight:640;color:var(--acc);
font-variant-numeric:tabular-nums}
.big{display:flex;gap:2.2rem;flex-wrap:wrap;margin:.2rem 0 .1rem}
.big div{min-width:8rem}
.big .n{font-size:2rem;font-weight:640;letter-spacing:-.02em;
font-variant-numeric:tabular-nums;color:var(--acc)}
.big .n2{color:var(--acc2)}
.big .n3{color:var(--acc3)}
.big .l{font-size:.78rem;color:var(--mut)}
table{width:100%;border-collapse:collapse;font-variant-numeric:tabular-nums}
th,td{padding:.42rem .5rem;border-bottom:1px solid var(--line);text-align:right}
th:first-child,td:first-child{text-align:left}
th{font-size:.76rem;color:var(--mut);text-transform:uppercase;
letter-spacing:.04em;font-weight:600}
.scroll{overflow-x:auto}
.bar{height:5px;background:var(--acc);border-radius:3px;opacity:.85}
.bar2{background:var(--acc2)}
.bar3{background:var(--acc3)}
.note{font-size:.84rem;color:var(--mut);margin-top:.5rem}
.warn{color:var(--warn);font-weight:600}
.avv{border-left:3px solid var(--warn);padding-left:.7rem;margin:.6rem 0;
font-size:.88rem}
.due{display:grid;gap:1.1rem;grid-template-columns:repeat(auto-fit,minmax(17rem,1fr))}
ul{margin:.4rem 0 0;padding-left:1.1rem}li{margin:.18rem 0}
code{font-size:.85em;background:rgba(128,128,128,.13);padding:.05rem .3rem;
border-radius:4px}
.hide{display:none}
"""

_JS = """
const D=DATI;
const $=id=>document.getElementById(id);
const camp=$('camp'), tur=$('tur'), griglia=$('griglia'), out=$('out'),
      meta=$('meta'), sq=$('sq'), av=$('av'), cp=$('cp'), outL=$('outL');
let scelta=null, modo='turno';

function opts(el,vals,keep,testi){
  const old=el.value; el.innerHTML='';
  vals.forEach((v,i)=>{const o=document.createElement('option');
    o.value=v;o.textContent=testi?testi[i]:v;el.appendChild(o);});
  if(keep&&vals.includes(old))el.value=old;
}
function B(){return D.campionati[camp.value];}
function pct(x){return (100*x).toFixed(1)+'%';}
function q(x){return x>0?(1/x).toFixed(2):'-';}

function tabella(linee,p,cls){
  let h='<div class="scroll"><table><thead><tr><th>linea</th>'
      +'<th>P(Over)</th><th>quota di pareggio</th><th></th></tr></thead><tbody>';
  linee.forEach((ln,i)=>{
    h+='<tr><td>Over '+ln.toFixed(1)+'</td><td>'+pct(p[i])+'</td><td>'+q(p[i])
      +'</td><td style="width:36%"><div class="bar '+cls+'" style="width:'
      +(100*p[i]).toFixed(1)+'%"></div></td></tr>';
  });
  return h+'</tbody></table></div>';
}

function riempiCampionato(){
  const b=B();
  opts(tur,b.turni.map(t=>t.t),true,b.turni.map(t=>t.e+' ('+t.p.length+')'));
  meta.innerHTML='stagione <strong>'+b.stagione+'</strong> - '+b.partite
    +' partite giocate - aggiornato al '+b.come_di
    +' - <code>r_tot='+b.r_tot.toFixed(1)+'</code> tiri, <code>r_tot='
    +b.r_tot_sot.toFixed(1)+'</code> in porta'
    +(b.nota?' - <span class="warn">'+b.nota+'</span>':'');
  const squadre=[...new Set(b.righe.map(r=>r.s))].sort();
  opts(sq,squadre,true); riempiAvversari();
  scelta=null; disegnaTurno();
}
function disegnaTurno(){
  const b=B(), t=b.turni.find(x=>x.t===tur.value);
  if(!t){griglia.innerHTML='';out.innerHTML='';return;}
  griglia.innerHTML=t.p.map(i=>{
    const p=b.partite_cal[i];
    return '<button class="m" data-i="'+i+'" aria-pressed="'+(scelta===i)+'">'
      +'<span class="nm"><span>'+p.c+'</span><span>'+p.a+'</span></span>'
      +'<span class="tot">'+p.lt.toFixed(1)+'</span></button>';
  }).join('');
  griglia.querySelectorAll('.m').forEach(el=>el.addEventListener(
    'click',()=>{scelta=+el.dataset.i;disegnaTurno();}));
  const nota=t.f===D.fonti_turno[0]
    ? 'Giornata dalla fonte.'
    : (t.f===D.fonti_turno[1]
       ? 'Giornata <strong>dedotta dalla data</strong>: la fonte non la scrive '
         +'per queste partite, e il numero della giornata NON viene attribuito '
         +'alle righe - cambia solo il turno in cui sono mostrate.'
       : 'Non e&#39; una giornata di campionato: e&#39; un <strong>blocco di '
         +'date</strong>, perche&#39; la fonte non porta la giornata per queste '
         +'partite. Non va letto come un turno.');
  // **L'elemento della nota e' FISSO.** La prima stesura la inseriva con
  // `insertAdjacentHTML('afterend', ...)` a ogni ridisegno, quindi le note si
  // accumulavano una sotto l'altra a ogni click: un difetto che non si vede
  // finche' non si clicca due volte.
  $('nt').innerHTML=nota
    +' Il numero grande in scheda e&#39; il <strong>totale di tiri atteso</strong>.';
  if(scelta===null||!t.p.includes(scelta)){out.innerHTML=
    '<p class="note">Scegli una partita qui sopra.</p>';}
  else dettaglio();
}
function dettaglio(){
  const b=B(), p=b.partite_cal[scelta];
  let h='<h2>'+p.c+' - '+p.a+'</h2>'
   +'<p class="note">'+(p.d||'data ignota')+' - '+p.e+'</p>'
   +'<div class="big">'
   +'<div><div class="n n3">'+p.lt.toFixed(2)+'</div>'
   +'<div class="l">tiri TOTALI attesi</div></div>'
   +'<div><div class="n n3">'+p.st.toFixed(2)+'</div>'
   +'<div class="l">tiri in porta TOTALI</div></div>'
   +'<div><div class="n">'+p.lc.toFixed(2)+'</div><div class="l">tiri '+p.c
   +'</div></div>'
   +'<div><div class="n n2">'+p.la.toFixed(2)+'</div><div class="l">tiri '+p.a
   +'</div></div></div>'
   +'<p class="note">Il totale e&#39; la <strong>somma esatta</strong> dei due '
   +'lati: <code>E[X+Y]=E[X]+E[Y]</code> non richiede nessuna ipotesi sulla '
   +'dipendenza. Cio&#39; che la dipendenza rompe e&#39; la dispersione, ed e&#39; '
   +'per questo che <code>r_tot</code> e&#39; stimata sui totali osservati di '
   +'QUESTO campionato invece di essere ereditata dai due lati.</p>';

  h+='<div class="avv"><span class="warn">Il lambda del totale e&#39; '
   +'sotto-calibrato:</span> pendenza '+b.pend_tot.toFixed(2)+' sui tiri e '
   +b.pend_tot_sot.toFixed(2)+' sui tiri in porta in questo campionato, contro '
   +'1,008 per lato. Il modello crede i due lati piu&#39; anti-correlati di '
   +'quanto siano, e sommando si cancella il segnale comune. Le probabilita&#39; '
   +'qui sotto vanno lette con questo accanto: sono piu&#39; affidabili al centro '
   +'che sulle code. La correzione misurata in T1 <strong>non e&#39; '
   +'applicata</strong>, perche&#39; passa il criterio in 3 celle su 10 e '
   +'applicarla a macchia renderebbe i cinque campionati non confrontabili.</div>';

  if(p.r!==D.regimi[1]){
    h+='<div class="avv"><span class="warn">Regime: '+p.r+'.</span> '
     +'Le due squadre hanno '+p.nc+' e '+p.na+' partite in questa stagione, '
     +'sotto il burn-in di '+D.burn_in+': i numeri vengono dal modello della '
     +'stagione precedente applicato tale e quale, non dalle partite di questa. '
     +'E&#39; la forma che la Fase 14 / A2 ha misurato come migliore li&#39;.</div>';
  }
  if(p.nv>0){
    h+='<div class="avv">'+p.nv+' di queste due squadre non ha ancora giocato '
     +'in questa stagione: il modello within-season non la conosce affatto, e il '
     +'numero viene dal prior. Le squadre vengono dal <strong>calendario</strong>, '
     +'i numeri dal modello.</div>';
  }
  if(p.sp>0){
    h+='<div class="avv">'+p.sp+' di queste due squadre non era nel campionato '
     +'la stagione scorsa: il prior non la conosce e la tratta come esattamente '
     +'media. E&#39; l&#39;unico default onesto, ma resta un&#39;assunzione.</div>';
  }
  h+='<div class="due"><div><h3>Tiri totali</h3>'+tabella(D.linee_tot,p.pt,'bar3')
   +'</div><div><h3>Tiri in porta totali</h3>'
   +tabella(D.linee_tot_sot,p.pts,'bar3')+'</div></div>';

  const rc=b.righe.find(x=>x.s===p.c&&x.a===p.a&&x.c==='casa');
  const ra=b.righe.find(x=>x.s===p.a&&x.a===p.c&&x.c==='trasferta');
  if(rc&&ra){
    h+='<div class="due"><div><h3>Tiri - '+p.c+' (in casa)</h3>'
     +tabella(D.linee,rc.p,'')+'</div><div><h3>Tiri - '+p.a+' (in trasferta)</h3>'
     +tabella(D.linee,ra.p,'bar2')+'</div></div>';
  }else{
    h+='<p class="note">Le tabelle per lato non ci sono per questa partita: '
     +'almeno una delle due squadre non ha ancora giocato, quindi non compare '
     +'nella tabella delle coppie.</p>';
  }
  out.innerHTML=h;
}

function riempiAvversari(){
  const b=B();
  opts(av,[...new Set(b.righe.filter(r=>r.s===sq.value).map(r=>r.a))].sort(),true);
  disegnaLibera();
}
function disegnaLibera(){
  const b=B();
  const r=b.righe.find(x=>x.s===sq.value&&x.a===av.value&&x.c===cp.value);
  if(!r){outL.innerHTML='<p class="note">combinazione non disponibile.</p>';return;}
  let h='<div class="big">'
   +'<div><div class="n">'+r.lam.toFixed(2)+'</div>'
   +'<div class="l">tiri attesi</div></div>'
   +'<div><div class="n n2">'+r.sot.toFixed(2)+'</div>'
   +'<div class="l">tiri in porta attesi</div></div>'
   +'<div><div class="n">'+(100*r.sot/r.lam).toFixed(1)+'%</div>'
   +'<div class="l">precisione implicita</div></div></div>';
  if(r.reg!==D.regimi[1]){
    h+='<div class="avv"><span class="warn">Regime: '+r.reg+'.</span> '
     +sq.value+' ha '+r.n+' partite in questa stagione, sotto il burn-in di '
     +D.burn_in+': il numero viene dal modello della stagione precedente '
     +'applicato tale e quale.</div>';
  }
  if(r.np>0){
    h+='<div class="avv">'+r.np+' delle due squadre non erano nel campionato '
     +'la stagione scorsa: il prior le tratta come esattamente medie.</div>';
  }
  h+='<div class="due"><div><h3>Tiri</h3>'+tabella(D.linee,r.p,'')
   +'</div><div><h3>Tiri in porta</h3>'+tabella(D.linee_sot,r.ps,'bar2')
   +'</div></div>';
  outL.innerHTML=h;
}

function modoTab(m){
  modo=m;
  document.querySelectorAll('.tab').forEach(
    t=>t.setAttribute('aria-selected',String(t.dataset.m===m)));
  $('pTurno').className=(m==='turno')?'':'hide';
  $('pLibera').className=(m==='libera')?'':'hide';
}
document.querySelectorAll('.tab').forEach(
  t=>t.addEventListener('click',()=>modoTab(t.dataset.m)));
camp.addEventListener('change',riempiCampionato);
tur.addEventListener('change',()=>{scelta=null;disegnaTurno();});
sq.addEventListener('change',riempiAvversari);
av.addEventListener('change',disegnaLibera);
cp.addEventListener('change',disegnaLibera);
opts(camp,Object.keys(D.campionati));
riempiCampionato();
modoTab('turno');
"""


def _righe_coppie(tab, linee, linee_sot) -> list[dict]:
    """Le 760 coppie della modalita' libera. Nomi corti: sono 3.800 righe."""
    return [{
        "s": row["squadra"], "a": row["avversario"], "c": row["campo"],
        "lam": round(float(row["lambda_tentativi"]), 4),
        "sot": round(float(row["lambda_sot"]), 4),
        "reg": row["regime"],
        "n": int(row["partite_squadra"]),
        "np": int(row["senza_prior"]),
        "p": [round(float(row[f"p_over_{ln}"]), 6) for ln in linee],
        "ps": [round(float(row[f"p_over_sot_{ln}"]), 6) for ln in linee_sot],
    } for _, row in tab.iterrows()]


def _righe_calendario(cal, linee_tot, linee_tot_sot) -> list[dict]:
    """Le partite del calendario, gia' con i due totali e le loro `P(Over)`."""
    return [{
        "c": row["casa"], "a": row["trasferta"],
        "d": row["data_fonte"], "e": row["etichetta_turno"],
        "lc": round(float(row["lam_casa"]), 4),
        "la": round(float(row["lam_trasferta"]), 4),
        "lt": round(float(row["lam_totale"]), 4),
        "sc": round(float(row["sot_casa"]), 4),
        "sa": round(float(row["sot_trasferta"]), 4),
        "st": round(float(row["sot_totale"]), 4),
        "r": row["regime"],
        "nc": int(row["partite_casa"]), "na": int(row["partite_trasferta"]),
        "nv": int(row["squadre_non_viste"]), "sp": int(row["senza_prior"]),
        "pt": [round(float(row[f"p_tot_{ln}"]), 6) for ln in linee_tot],
        "pts": [round(float(row[f"p_tot_sot_{ln}"]), 6) for ln in linee_tot_sot],
    } for _, row in cal.iterrows()]


def scrivi(blocchi: dict, out: Path, linee, linee_sot, linee_tot, linee_tot_sot,
           limiti: list[str], burn_in: int, regimi, fonti_turno,
           generato: str) -> None:
    """Scrive la pagina autonoma dai dati **gia' calcolati**.

    Come `pagina_v4`, questo modulo **non calcola niente**: serializza. Se
    facesse un solo conto, la pagina e il modello potrebbero divergere senza che
    nessuno se ne accorga.
    """
    dati = {
        "campionati": {},
        "linee": [float(x) for x in linee],
        "linee_sot": [float(x) for x in linee_sot],
        "linee_tot": [float(x) for x in linee_tot],
        "linee_tot_sot": [float(x) for x in linee_tot_sot],
        "burn_in": int(burn_in),
        "regimi": list(regimi),
        "fonti_turno": list(fonti_turno),
    }

    for nome, b in blocchi.items():
        tab, cal, turni = b["tabella"], b["calendario"], b["turni"]
        # L'indice della partita dentro `partite_cal` e' la sua posizione nella
        # tabella del calendario: il turno porta gli indici, non una copia delle
        # righe, cosi' una partita esiste in un posto solo.
        pos = {k: i for i, k in enumerate(zip(cal["casa"], cal["trasferta"]))} \
            if len(cal) else {}
        dati["campionati"][nome] = {
            "stagione": b["stagione"],
            "come_di": b["come_di"],
            "partite": int(b["partite"]),
            "nota": b.get("nota", ""),
            "r": round(float(tab["r"].iloc[0]), 3),
            "r_sot": round(float(tab["r_sot"].iloc[0]), 3),
            "r_tot": round(float(b["r_tot"]), 3),
            "r_tot_sot": round(float(b["r_tot_sot"]), 3),
            "pend_tot": round(float(b["pend_tot"]), 4),
            "pend_tot_sot": round(float(b["pend_tot_sot"]), 4),
            "righe": _righe_coppie(tab, linee, linee_sot),
            "partite_cal": _righe_calendario(cal, linee_tot, linee_tot_sot),
            "turni": [{
                "t": t["turno"], "e": t["etichetta"], "f": t["fonte"],
                "p": [pos[(c, a)] for c, a in zip(
                    cal.loc[cal["turno"] == t["turno"], "casa"],
                    cal.loc[cal["turno"] == t["turno"], "trasferta"])],
            } for _, t in turni.iterrows()],
        }

    html = f"""<!doctype html>
<html lang="it"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Tiri attesi - una partita del calendario</title>
<style>{_CSS}</style></head><body><div class="wrap">
<h1>Tiri attesi, e il totale di partita</h1>
<div class="sub">Cinque campionati - un modello per campionato, mai poolati -
calendario della stagione in corso - generata il {generato} - Fase 15</div>

<div class="tabs" role="tablist">
  <button class="tab" data-m="turno" role="tab">una partita del calendario</button>
  <button class="tab" data-m="libera" role="tab">una coppia qualsiasi</button>
</div>

<div class="card"><div class="row">
  <div class="f"><label for="camp">campionato</label><select id="camp"></select></div>
  <div class="f"><label for="tur">turno</label><select id="tur"></select></div>
</div>
<p class="note" id="meta"></p></div>

<div id="pTurno">
  <div class="card"><div id="griglia" class="grid"></div>
  <p class="note" id="nt"></p></div>
  <div class="card" id="out"></div>
</div>

<div id="pLibera" class="hide">
  <div class="card"><div class="row">
    <div class="f"><label for="sq">squadra</label><select id="sq"></select></div>
    <div class="f"><label for="av">avversario</label><select id="av"></select></div>
    <div class="f"><label for="cp">campo</label>
      <select id="cp"><option>casa</option><option>trasferta</option></select></div>
  </div></div>
  <div class="card" id="outL"></div>
</div>

<div class="card"><strong>Limiti, accanto ai numeri e non in fondo</strong>
<ul>{''.join(f'<li>{x}</li>' for x in limiti)}</ul></div>

<p class="note">La <em>quota di pareggio</em> e' <code>1/P</code>, cioe' il
prezzo al quale il guadagno atteso sarebbe esattamente zero. Non e' una
previsione di prezzo e questa pagina non ne propone: nel repository non ci sono
prezzi di mercato reali.</p>

<p class="note">Pagina locale e autonoma: nessuna richiesta di rete.
Rigenerabile con <code>scripts/run_previsioni.py</code>, che
<code>scripts/aggiorna_stagione.py</code> chiama da solo ogni volta che arrivano
partite nuove.</p>
</div>
<script>const DATI={json.dumps(dati, ensure_ascii=False)};</script>
<script>{_JS}</script></body></html>"""
    out.write_text(html, encoding="utf-8")
