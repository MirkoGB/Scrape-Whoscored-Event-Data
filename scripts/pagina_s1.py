# -*- coding: utf-8 -*-
"""Fase 11 / S1 — la pagina locale interattiva.

Sta in un file a parte perche' e' **presentazione**, non statistica: il template
qui sotto non calcola niente e non decide niente. Tutti i numeri arrivano gia'
fatti da `sot/soglie_2627.py` via `scripts/run_fase11_s1.py`, che e' l'unico
posto in cui il blocco stima qualcosa.

La pagina e' **autonoma**: nessun CDN, nessun font remoto, nessuna richiesta di
rete. Si apre con un doppio clic e funziona offline, che e' cio' che «pagina
locale» vuol dire.

> **Vincolo 3, anche qui.** La quota e' un **ingresso dell'utente**, mai un
> output: la pagina non ne propone una, non ne stima una e non ne suggerisce una.
> Cio' che mostra e' `P` (dal modello) e il guadagno atteso **condizionato alla
> quota che l'utente scrive**. Il valore di partenza dello slider e' la quota di
> pareggio, cioe' il punto in cui il guadagno e' zero: e' il default piu' neutro
> possibile, e non e' una previsione di prezzo.
"""

from __future__ import annotations

import json

import pandas as pd

# Il template e' un `str.replace` e non una f-string: qui dentro ci sono
# centinaia di graffe fra CSS e JavaScript, e in una f-string ognuna andrebbe
# raddoppiata. E' lo stesso inciampo gia' incontrato nel report markdown.
TEMPLATE = r"""<!doctype html>
<html lang="it">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Como 2026-27 — soglie tiri in porta</title>
<style>
:root{
  color-scheme: light;
  --surface-1:#fcfcfb; --page:#f9f9f7;
  --text-primary:#0b0b0b; --text-secondary:#52514e; --muted:#898781;
  --grid:#e1e0d9; --axis:#c3c2b7; --border:rgba(11,11,11,0.10);
  --series:#2a78d6; --pos:#2a78d6; --neg:#e34948; --zero:#f0efec;
  --chip:#ffffff;
}
@media (prefers-color-scheme: dark){
  :root:not([data-theme="light"]){
    color-scheme: dark;
    --surface-1:#1a1a19; --page:#0d0d0d;
    --text-primary:#ffffff; --text-secondary:#c3c2b7; --muted:#898781;
    --grid:#2c2c2a; --axis:#383835; --border:rgba(255,255,255,0.10);
    --series:#3987e5; --pos:#3987e5; --neg:#e66767; --zero:#383835;
    --chip:#232322;
  }
}
:root[data-theme="dark"]{
  color-scheme: dark;
  --surface-1:#1a1a19; --page:#0d0d0d;
  --text-primary:#ffffff; --text-secondary:#c3c2b7; --muted:#898781;
  --grid:#2c2c2a; --axis:#383835; --border:rgba(255,255,255,0.10);
  --series:#3987e5; --pos:#3987e5; --neg:#e66767; --zero:#383835;
  --chip:#232322;
}
*{box-sizing:border-box}
body{
  margin:0; padding:28px 20px 64px;
  background:var(--page); color:var(--text-primary);
  font-family:system-ui,-apple-system,"Segoe UI",sans-serif;
  font-size:15px; line-height:1.55;
}
.wrap{max-width:1120px;margin:0 auto}
h1{font-size:25px;line-height:1.25;margin:0 0 6px;font-weight:650}
.sub{color:var(--text-secondary);margin:0 0 4px;max-width:75ch}
.meta{color:var(--muted);font-size:13px;margin:0 0 24px}
.card{
  background:var(--surface-1);border:1px solid var(--border);
  border-radius:12px;padding:18px 20px;margin-bottom:18px;
}
h2{font-size:15px;margin:0 0 14px;font-weight:650;letter-spacing:.01em}
/* ---- filtri: UNA riga sopra tutto cio' che governano ---- */
.filtri{display:flex;flex-wrap:wrap;gap:22px;align-items:flex-end}
.campo{display:flex;flex-direction:column;gap:7px;min-width:0}
label{font-size:12px;color:var(--text-secondary);font-weight:600;
      text-transform:uppercase;letter-spacing:.04em}
.seg{display:flex;gap:2px;background:var(--zero);padding:3px;border-radius:9px}
.seg button{
  border:0;background:transparent;color:var(--text-secondary);
  font:inherit;font-size:14px;font-weight:600;padding:7px 13px;
  border-radius:7px;cursor:pointer;min-height:36px;
}
.seg button:hover{color:var(--text-primary)}
.seg button[aria-pressed="true"]{background:var(--chip);color:var(--text-primary);
  box-shadow:0 1px 2px rgba(0,0,0,.10)}
input[type=number]{
  font:inherit;font-variant-numeric:tabular-nums;padding:8px 10px;width:110px;
  border:1px solid var(--border);border-radius:8px;
  background:var(--surface-1);color:var(--text-primary);min-height:36px;
}
input[type=range]{width:230px;accent-color:var(--series);min-height:36px}
.quotaRiga{display:flex;gap:12px;align-items:center}
/* ---- stat tiles ---- */
.tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:14px}
.tile{background:var(--surface-1);border:1px solid var(--border);
      border-radius:12px;padding:15px 17px}
.tile .k{font-size:12px;color:var(--text-secondary);font-weight:600;
         text-transform:uppercase;letter-spacing:.04em;margin-bottom:7px}
.tile .v{font-size:29px;font-weight:650;line-height:1.1}
.tile .n{font-size:13px;color:var(--muted);margin-top:5px}
.pos{color:var(--pos)} .neg{color:var(--neg)}
/* ---- grafico ---- */
.chartbox{position:relative}
svg{display:block;width:100%;height:auto;overflow:visible}
.tip{
  position:absolute;pointer-events:none;opacity:0;transition:opacity .10s;
  background:var(--surface-1);border:1px solid var(--border);border-radius:9px;
  padding:9px 12px;font-size:13px;box-shadow:0 4px 14px rgba(0,0,0,.14);
  white-space:nowrap;z-index:5;
}
.tip b{font-weight:650}
.tip .r{color:var(--text-secondary)}
/* ---- tabella ---- */
.scroll{overflow-x:auto}
table{border-collapse:collapse;width:100%;font-size:14px}
th,td{padding:8px 11px;text-align:right;
      border-bottom:1px solid var(--grid);font-variant-numeric:tabular-nums}
th{font-size:11.5px;color:var(--text-secondary);font-weight:650;
   text-transform:uppercase;letter-spacing:.04em;white-space:nowrap;
   border-bottom:1px solid var(--axis)}
/* `text-transform:uppercase` trasforma la lambda in Lambda, che e' un'altra
   grandezza: questa colonna resta minuscola. */
th.mate{text-transform:none;letter-spacing:0;font-size:13px}
th:nth-child(2),td:nth-child(2),th:nth-child(3),td:nth-child(3){
  text-align:left;font-variant-numeric:normal}
tbody tr:hover{background:var(--zero)}
td input{width:82px;padding:5px 7px;font-size:14px;min-height:30px}
tfoot td{font-weight:650;border-top:1px solid var(--axis);border-bottom:0}
.nota{color:var(--text-secondary);font-size:13.5px;max-width:82ch}
.nota strong{color:var(--text-primary)}
.warn{border-left:3px solid var(--neg);padding-left:14px;margin:14px 0}
details{margin-top:10px}
summary{cursor:pointer;font-weight:600;font-size:13.5px;color:var(--text-secondary)}
.azioni{display:flex;gap:10px;align-items:center;margin-top:14px;flex-wrap:wrap}
.btn{border:1px solid var(--border);background:var(--surface-1);
     color:var(--text-primary);font:inherit;font-size:13.5px;font-weight:600;
     padding:8px 14px;border-radius:8px;cursor:pointer;min-height:36px}
.btn:hover{background:var(--zero)}
</style>
</head>
<body>
<div class="wrap">

<h1>Como 2026-27 — over tiri in porta, partita per partita</h1>
<p class="sub">La probabilit&agrave; viene dal modello; <strong>la quota la scrivi
tu</strong>. Il guadagno atteso di 1&nbsp;&euro; &egrave;
<code>P &times; quota &minus; 1</code>, e questa pagina calcola il secondo pezzo
solo dopo che hai fornito il primo prezzo.</p>
<p class="meta">Generato da <code>scripts/run_fase11_s1.py</code> il __DATA__ ·
&lambda; ancorati a __ANCORA__ tiri/partita · NB2 con r&nbsp;=&nbsp;__R__ ·
calendario 2026-27 verificato · nessuna richiesta di rete</p>

<div class="card">
  <h2>Parametri</h2>
  <div class="filtri">
    <div class="campo">
      <label id="lblLinea">Linea (over tiri in porta)</label>
      <div class="seg" role="group" aria-labelledby="lblLinea" id="segLinea"></div>
    </div>
    <div class="campo">
      <label for="quotaNum">Quota offerta</label>
      <div class="quotaRiga">
        <input type="number" id="quotaNum" min="1.01" max="30" step="0.01">
        <input type="range" id="quotaRange" min="1.01" max="15" step="0.01"
               aria-label="Quota offerta">
      </div>
    </div>
    <div class="campo">
      <label for="puntata">Puntata per partita (&euro;)</label>
      <input type="number" id="puntata" min="0" step="0.5" value="1">
    </div>
    <div class="campo">
      <label id="lblP">Incertezza sul livello</label>
      <div class="seg" role="group" aria-labelledby="lblP" id="segP">
        <button type="button" data-p="p_puntuale" aria-pressed="true">esclusa</button>
        <button type="button" data-p="p_integrata" aria-pressed="false">inclusa</button>
      </div>
    </div>
  </div>
  <div class="azioni">
    <button class="btn" id="allaPari" type="button">Porta la quota alla pari</button>
    <button class="btn" id="reset" type="button">Reimposta le quote per partita</button>
    <span class="nota" id="statoQuote"></span>
  </div>
</div>

<div class="tiles" id="tiles"></div>

<div class="card" style="margin-top:18px">
  <h2 id="titoloGrafico"></h2>
  <div class="chartbox">
    <svg id="chart" viewBox="0 0 900 330" preserveAspectRatio="xMidYMid meet"
         role="img" aria-labelledby="titoloGrafico"></svg>
    <div class="tip" id="tip"></div>
  </div>
  <p class="nota" id="notaGrafico"></p>
</div>

<div class="card">
  <h2>Le 38 partite</h2>
  <p class="nota">La colonna <strong>quota</strong> &egrave; modificabile riga per
  riga: incolla i prezzi veri quando li hai, e il guadagno atteso si aggiorna solo
  per quella partita. La <strong>quota di pareggio</strong> &egrave; il punto in
  cui il guadagno atteso &egrave; esattamente zero.
  <br>L'asterisco marca le tre <strong>neopromosse</strong> (Venezia, Frosinone,
  Monza): della loro difesa questi dati non sanno niente, e il valore usato
  &egrave; uno scenario dichiarato, non una stima.</p>
  <div class="scroll">
    <table>
      <thead><tr>
        <th>G</th><th>Avversario</th><th>Campo</th><th class="mate">&lambda;</th>
        <th>P(over)</th><th>Quota di pareggio</th><th>Quota</th>
        <th>Guadagno atteso</th><th>Cumulato</th>
      </tr></thead>
      <tbody id="tbody"></tbody>
      <tfoot id="tfoot"></tfoot>
    </table>
  </div>
</div>

<div class="card">
  <h2>Come va letta</h2>
  <p class="nota"><strong>Nel repository non esistono prezzi di mercato.</strong>
  Per questo la pagina non propone una quota: la propria la genererebbe dal
  modello stesso, e il conto diventerebbe circolare — con margine proporzionale
  il guadagno atteso varrebbe <code>1/overround &minus; 1</code> su ogni partita e
  ogni linea, identicamente, senza contenere una sola informazione sul Como.</p>
  <div class="warn">
    <p class="nota" style="margin:0"><strong>Due limiti da tenere accanto ai
    numeri.</strong> Le linee <strong>6.5 e 7.5</strong> sono un'estrapolazione:
    la validazione del progetto si ferma a 5.5, e su quelle due soglie la
    dispersione <code>r</code> — che qui non &egrave; stimata — pesa molto di
    pi&ugrave;. E la verifica sul 2025-26 gira su <strong>33 partite di una
    squadra sola</strong>: esclude divari grandi, non divari piccoli.</p>
  </div>
  <details>
    <summary>Che cosa cambia includendo l'incertezza sul livello</summary>
    <p class="nota">La proiezione dice che il 65% della varianza stagionale
    &egrave; shock di squadra: non sappiamo con precisione quanto tirer&agrave; il
    Como. Includerla <strong>ingrassa le code</strong> — alza le linee alte,
    abbassa quelle basse — e sulla 7.5 sposta la quota di pareggio di circa
    mezzo punto. Non &egrave; neutro: rende gli estremi pi&ugrave; probabili.</p>
  </details>
</div>

</div>
<script>
const DATI = __DATI__;
const LINEE = __LINEE__;

let linea = 4.5, colonnaP = "p_puntuale", override = {};

const fmtE = (x, s) => (x >= 0 ? "+" : "−") + "€" + Math.abs(x).toFixed(s ?? 2);
const cls  = x => x >= 0 ? "pos" : "neg";
const righe = () => DATI.filter(d => d.linea === linea)
                        .sort((a, b) => a.giornata - b.giornata);
const chiave = d => d.linea + "|" + d.giornata;
const pDi = d => d[colonnaP];
const quotaDi = d => override[chiave(d)] ?? (+quotaNum.value);

function calcola(){
  const s = +puntata.value || 0;
  let cum = 0;
  return righe().map(d => {
    const p = pDi(d), q = quotaDi(d), ev = s * (p * q - 1);
    cum += ev;
    return {...d, p, q, ev, cum, pari: 1 / p};
  });
}

/* ---------- stat tiles ---------- */
function disegnaTiles(r){
  const s = +puntata.value || 0;
  const pMedia = r.reduce((a, x) => a + x.p, 0) / r.length;
  const tot = r.reduce((a, x) => a + x.ev, 0);
  const buone = r.filter(x => x.ev > 0).length;
  tiles.innerHTML = `
    <div class="tile"><div class="k">P(over ${linea}) media</div>
      <div class="v">${(pMedia * 100).toFixed(1)}%</div>
      <div class="n">da ${(Math.min(...r.map(x => x.p)) * 100).toFixed(0)}%
        a ${(Math.max(...r.map(x => x.p)) * 100).toFixed(0)}% fra le partite</div></div>
    <div class="tile"><div class="k">Quota di pareggio</div>
      <div class="v">${(1 / pMedia).toFixed(2)}</div>
      <div class="n">sopra questa, il guadagno atteso &egrave; positivo</div></div>
    <div class="tile"><div class="k">Guadagno atteso, stagione</div>
      <div class="v ${cls(tot)}">${fmtE(tot)}</div>
      <div class="n">su ${fmtE(s * r.length).slice(1)} puntati in 38 partite</div></div>
    <div class="tile"><div class="k">Partite in guadagno</div>
      <div class="v">${buone}<span style="font-size:17px;color:var(--muted)">/38</span></div>
      <div class="n">quota offerta sopra quella di pareggio</div></div>`;
}

/* ---------- grafico: una serie, guadagno cumulato ---------- */
const W = 900, H = 330, M = {t: 18, r: 96, b: 46, l: 62};
function disegnaChart(r){
  const pw = W - M.l - M.r, ph = H - M.t - M.b;
  const ys = r.map(x => x.cum).concat([0]);
  let lo = Math.min(...ys), hi = Math.max(...ys);
  if (hi - lo < 1e-9){ lo -= 1; hi += 1; }
  const pad = (hi - lo) * 0.12; lo -= pad; hi += pad;
  const X = i => M.l + (r.length === 1 ? pw / 2 : i * pw / (r.length - 1));
  const Y = v => M.t + ph - (v - lo) / (hi - lo) * ph;

  // Passi 1/2/5 x 10^k, e i decimali seguono il PASSO: con passo 0.5 e zero
  // decimali le etichette diventerebbero "€1" sia a 0.5 sia a 1.0.
  const grezzo = (hi - lo) / 5;
  const mag = Math.pow(10, Math.floor(Math.log10(Math.max(1e-9, grezzo))));
  const step = [1, 2, 5, 10].find(m => mag * m >= grezzo) * mag;
  const dec = Math.max(0, -Math.floor(Math.log10(step) + 1e-9));
  const ticks = [];
  for (let t = Math.ceil(lo / step - 1e-9) * step; t <= hi + 1e-9; t += step)
    ticks.push(Math.abs(t) < step / 1e6 ? 0 : t);

  const linea_ = r.map((d, i) => (i ? "L" : "M") + X(i).toFixed(1) + " " + Y(d.cum).toFixed(1)).join(" ");
  const ultimo = r[r.length - 1];

  chart.innerHTML = `
   <g>${ticks.map(t => `<line x1="${M.l}" x2="${M.l + pw}" y1="${Y(t).toFixed(1)}"
        y2="${Y(t).toFixed(1)}" stroke="var(--grid)" stroke-width="1"/>
      <text x="${M.l - 10}" y="${(Y(t) + 4).toFixed(1)}" text-anchor="end"
        font-size="12" fill="var(--muted)"
        style="font-variant-numeric:tabular-nums">${t >= 0 ? "" : "−"}€${Math.abs(t).toFixed(dec)}</text>`).join("")}
   </g>
   <line x1="${M.l}" x2="${M.l + pw}" y1="${Y(0).toFixed(1)}" y2="${Y(0).toFixed(1)}"
         stroke="var(--axis)" stroke-width="1"/>
   <line x1="${M.l}" x2="${M.l + pw}" y1="${M.t + ph}" y2="${M.t + ph}"
         stroke="var(--axis)" stroke-width="1"/>
   ${r.map((d, i) => (i === r.length - 1 || (d.giornata % 4 === 1 && i < r.length - 3)) ? `
     <text x="${X(i).toFixed(1)}" y="${M.t + ph + 20}" text-anchor="middle"
       font-size="12" fill="var(--muted)"
       style="font-variant-numeric:tabular-nums">${d.giornata}</text>` : "").join("")}
   <text x="${M.l + pw / 2}" y="${M.t + ph + 41}" text-anchor="middle"
     font-size="12" fill="var(--text-secondary)">giornata</text>
   <path d="${linea_}" fill="none" stroke="var(--series)" stroke-width="2"
     stroke-linejoin="round" stroke-linecap="round"/>
   <circle cx="${X(r.length - 1).toFixed(1)}" cy="${Y(ultimo.cum).toFixed(1)}" r="4.5"
     fill="var(--series)" stroke="var(--surface-1)" stroke-width="2"/>
   <text x="${(X(r.length - 1) + 12).toFixed(1)}" y="${(Y(ultimo.cum) + 4).toFixed(1)}"
     font-size="13" font-weight="650" fill="var(--text-primary)"
     style="font-variant-numeric:tabular-nums">${fmtE(ultimo.cum)}</text>
   <line id="cross" x1="0" x2="0" y1="${M.t}" y2="${M.t + ph}" stroke="var(--axis)"
     stroke-width="1" opacity="0"/>
   <circle id="dot" r="5" fill="var(--series)" stroke="var(--surface-1)"
     stroke-width="2" opacity="0"/>
   <rect x="${M.l}" y="${M.t}" width="${pw}" height="${ph}" fill="transparent"
     id="hit" style="cursor:crosshair"/>`;

  const hit = chart.querySelector("#hit");
  const cross = chart.querySelector("#cross");
  const dot = chart.querySelector("#dot");
  hit.onmousemove = e => {
    const box = chart.getBoundingClientRect();
    const px = (e.clientX - box.left) / box.width * W;
    let i = Math.round((px - M.l) / (pw / (r.length - 1)));
    i = Math.max(0, Math.min(r.length - 1, i));
    const d = r[i];
    cross.setAttribute("x1", X(i)); cross.setAttribute("x2", X(i));
    cross.setAttribute("opacity", "1");
    dot.setAttribute("cx", X(i)); dot.setAttribute("cy", Y(d.cum));
    dot.setAttribute("opacity", "1");
    tip.innerHTML = `<b>${d.giornata}&ordf; · ${d.avversario}</b>
      <span class="r">(${d.campo})</span><br>
      <span class="r">P(over ${linea}) </span><b>${(d.p * 100).toFixed(1)}%</b>
      <span class="r"> · pareggio a </span><b>${d.pari.toFixed(2)}</b><br>
      <span class="r">quota </span><b>${d.q.toFixed(2)}</b>
      <span class="r"> · partita </span><b class="${cls(d.ev)}">${fmtE(d.ev)}</b><br>
      <span class="r">cumulato </span><b class="${cls(d.cum)}">${fmtE(d.cum)}</b>`;
    tip.style.opacity = "1";
    const lx = X(i) / W * box.width, ly = Y(d.cum) / H * box.height;
    tip.style.left = Math.min(box.width - tip.offsetWidth - 4, Math.max(0, lx + 14)) + "px";
    tip.style.top = Math.max(0, ly - tip.offsetHeight - 12) + "px";
  };
  hit.onmouseleave = () => {
    tip.style.opacity = "0"; cross.setAttribute("opacity", "0");
    dot.setAttribute("opacity", "0");
  };
}

/* ---------- tabella ---------- */
function disegnaTabella(r){
  tbody.innerHTML = r.map(d => `<tr>
    <td>${d.giornata}</td><td>${d.avversario}${d.promossa ? " *" : ""}</td>
    <td>${d.campo}</td><td>${d.lam.toFixed(2)}</td>
    <td>${(d.p * 100).toFixed(1)}%</td><td>${d.pari.toFixed(2)}</td>
    <td><input type="number" min="1.01" max="99" step="0.01"
         value="${d.q.toFixed(2)}" data-k="${chiave(d)}"
         aria-label="Quota giornata ${d.giornata}"></td>
    <td class="${cls(d.ev)}">${fmtE(d.ev)}</td>
    <td class="${cls(d.cum)}">${fmtE(d.cum)}</td></tr>`).join("");
  const tot = r.reduce((a, x) => a + x.ev, 0);
  tfoot.innerHTML = `<tr><td colspan="7">Totale su 38 partite</td>
    <td class="${cls(tot)}">${fmtE(tot)}</td><td></td></tr>`;
  tbody.querySelectorAll("input").forEach(inp => {
    inp.onchange = () => {
      const v = parseFloat(inp.value);
      if (isFinite(v) && v > 1) override[inp.dataset.k] = v;
      aggiorna();
    };
  });
}

/* ---------- orchestrazione ---------- */
function aggiorna(){
  const r = calcola();
  disegnaTiles(r); disegnaChart(r); disegnaTabella(r);
  titoloGrafico.textContent =
    `Guadagno atteso cumulato lungo la stagione — over ${linea}`;
  const tot = r[r.length - 1].cum;
  notaGrafico.innerHTML = `Una riga sola: il guadagno atteso che si accumula
    puntando &euro;${(+puntata.value || 0).toFixed(2)} su ogni partita.
    La pendenza cambia con l'avversario e con il campo — dove la curva scende, la
    quota offerta &egrave; sotto quella di pareggio di quella partita.
    A fine stagione: <b class="${cls(tot)}">${fmtE(tot)}</b>.`;
  const n = Object.keys(override).filter(k => k.startsWith(linea + "|")).length;
  statoQuote.textContent = n
    ? `${n} quot${n === 1 ? "a" : "e"} inserit${n === 1 ? "a" : "e"} a mano su questa linea`
    : "nessuna quota inserita a mano su questa linea";
}

/* ---------- controlli ---------- */
segLinea.innerHTML = LINEE.map(l =>
  `<button type="button" data-l="${l}" aria-pressed="${l === linea}">${l}</button>`).join("");
segLinea.onclick = e => {
  const b = e.target.closest("button"); if (!b) return;
  linea = +b.dataset.l;
  [...segLinea.children].forEach(c => c.setAttribute("aria-pressed", c === b));
  allaPari.click();
};
segP.onclick = e => {
  const b = e.target.closest("button"); if (!b) return;
  colonnaP = b.dataset.p;
  [...segP.children].forEach(c => c.setAttribute("aria-pressed", c === b));
  aggiorna();
};
function setQuota(v){
  const q = Math.max(1.01, Math.min(30, v));
  quotaNum.value = q.toFixed(2);
  quotaRange.value = Math.min(15, q).toFixed(2);
}
quotaNum.oninput  = () => { quotaRange.value = Math.min(15, +quotaNum.value || 1.01); aggiorna(); };
quotaRange.oninput = () => { quotaNum.value = (+quotaRange.value).toFixed(2); aggiorna(); };
puntata.oninput = aggiorna;
reset.onclick = () => { override = {}; aggiorna(); };
allaPari.onclick = () => {
  // La quota di pareggio della stagione: il punto in cui il guadagno e' zero.
  // E' il default piu' neutro possibile, e non e' una previsione di prezzo.
  override = {};
  const r = DATI.filter(d => d.linea === linea);
  setQuota(r.length / r.reduce((a, x) => a + pDi(x), 0));
  aggiorna();
};

allaPari.click();
</script>
</body>
</html>
"""


def scrivi(ps: pd.DataFrame, percorso, ancora: float, r_nb2: float,
           data: str, linee) -> None:
    """Scrive la pagina, con i dati gia' calcolati incorporati.

    Non calcola niente: `ps` arriva da `soglie_2627.p_soglie`. L'unica cosa che
    succede qui e' una serializzazione.
    """
    cols = ["linea", "giornata", "avversario", "campo", "promossa", "lam",
            "p_puntuale", "p_integrata"]
    d = ps[cols].copy()
    d["giornata"] = d["giornata"].astype(int)
    d["promossa"] = d["promossa"].astype(bool)
    for c in ("lam", "p_puntuale", "p_integrata"):
        d[c] = d[c].astype(float).round(6)

    html = (TEMPLATE
            .replace("__DATI__", json.dumps(d.to_dict("records"),
                                            ensure_ascii=False))
            .replace("__LINEE__", json.dumps([float(x) for x in linee]))
            .replace("__ANCORA__", f"{ancora:.2f}")
            .replace("__R__", f"{r_nb2:g}")
            .replace("__DATA__", data))
    percorso.write_text(html, encoding="utf-8")
