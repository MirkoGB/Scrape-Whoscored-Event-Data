# -*- coding: utf-8 -*-
"""Fase 12 / Blocco V3 — i predittori da dati evento, ritestati sui tentativi.

    ./.venv/Scripts/python.exe scripts/run_fase12_v3.py [--force]

**Non tocca la rete.** Scrive una sola cache sotto `data/processed/`
(`fase12_v3_predittori.parquet`): nove walk-forward per cinque stagioni, ~5 min
con `--force`, pochi secondi da cache.

**V3 non ha un modulo proprio**: parametrizza `sot/predictor_power.py` su
`target`, ed e' un'eccezione dichiarata alla regola «1 blocco = 1 modulo».
Duplicare quel modulo violerebbe «una definizione in un posto solo».
"""
from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sot import (config, predictor_power as PP, tentativi as T,  # noqa: E402
                 volume as VL, walkforward as wf)

OUT_MD = config.REPORTS / "fase12_v3_predittori.md"
OUT_CSV = config.REPORTS / "fase12_v3_predittori.csv"
OUT_CTX = config.REPORTS / "fase12_v3_contesto.csv"
OUT_SEG = config.REPORTS / "fase12_v3_segno_stagioni.csv"


def _tab(df: pd.DataFrame, dec: dict[str, int] | None = None) -> str:
    dec = dec or {}
    d = df.copy()
    for c in d.columns:
        if c in dec:
            d[c] = d[c].map(lambda v: "" if pd.isna(v) else f"{v:.{dec[c]}f}")
        elif d[c].dtype == bool:
            d[c] = d[c].map(lambda v: "si" if v else "no")
        else:
            d[c] = d[c].map(lambda v: "—" if pd.isna(v) else str(v))
    num = [c for c in df.columns
           if pd.api.types.is_numeric_dtype(df[c]) and df[c].dtype != bool]
    head = "| " + " | ".join(str(c).replace("|", "\\|") for c in d.columns) + " |"
    sep = "|" + "|".join("---:" if c in num else "---" for c in d.columns) + "|"
    body = "\n".join("| " + " | ".join(r) + " |" for r in d.astype(str).values)
    return "\n".join([head, sep, body])


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    print("Fase 12, blocco V3 — i predittori, ritestati sui tentativi")
    print("=" * 62)

    prev = VL.previsioni_predittori(force=args.force)
    print(f"[1] previsioni: {len(prev)} righe, base + {len(wf.CANDIDATES)} candidati")

    c = VL.confronto_predittori(prev)
    print(f"[2] tenuti: {int(c['tenuto'].sum())} su {len(c)} "
          f"({c['predittore'].nunique()} candidati x {c['regime'].nunique()} regimi)")
    for r in PP.REGIMI:
        g = c[c["regime"] == r]
        best = g.loc[g["t"].idxmax()]
        print(f"    {r:<18} n {int(best['n']):>5}  t max {best['t']:+.3f} "
              f"({best['predittore']})  MDE/riga {best['mde_riga']:.5f}")

    ctx = VL.contesto_regimi(prev)
    print("[3] contesto (MAE del modello contro i baseline, per regime):")
    for r in PP.REGIMI:
        g = ctx[ctx["regime"] == r].set_index("modello")
        peggiore = g["delta_vs_modello"].max()
        print(f"    {r:<18} il baseline peggiore sta a {peggiore:+.4f} di MAE")

    rel = VL.mde_relativo(prev)
    print("[3b] MDE in quota del guadagno del modello sul baseline "
          "(l'unita' confrontabile fra bersagli):")
    for _, r in rel.iterrows():
        print(f"    {r['regime']:<18} {r['mde_in_quota_del_guadagno']:.4f}")

    seg = VL.segno_per_stagione(prev)
    print(f"[4] consistenza fra stagioni (regime maturo): "
          f"nessun candidato ha 5/5 positivi: "
          f"{bool((seg['positivi'] < 5).all())}")

    # Potenza contro l'alternativa dichiarata: il piu' grande effetto per riga
    # prodotto dagli otto candidati in questo blocco.
    mat = c[c["regime"] == "maturo"]
    alt = float(mat["d_riga"].max())
    pot = {r: PP.potenza(alt, float(c[c["regime"] == r]["se_riga"].min()))
           for r in PP.REGIMI}
    t_max = float(mat["t"].max())
    p_max = PP.p_del_massimo(t_max)
    print(f"[5] potenza contro l'alternativa {alt:.5f}/riga: "
          + ", ".join(f"{r} {p:.0%}" for r, p in pot.items()))
    print(f"[6] p del massimo su 8 candidati (maturo): t {t_max:.3f} -> {p_max:.3f}")

    c.to_csv(OUT_CSV, index=False, encoding="utf-8")
    ctx.to_csv(OUT_CTX, index=False, encoding="utf-8")
    seg.to_csv(OUT_SEG, index=False, encoding="utf-8")

    negativi = mat[mat["t"] < -PP.T_KEEP]
    dis = c[c["regime"] == "acerbo disgiunto"]
    dis_neg = dis[dis["t"] < -PP.T_KEEP]

    testo = f"""# Fase 12 / Blocco V3 — i predittori, ritestati sui tentativi

> Generato da `scripts/run_fase12_v3.py` il {date.today().isoformat()}.
> **Non tocca la rete.** Unica scrittura sotto `data/`: la cache
> `fase12_v3_predittori.parquet`, rigenerabile con `--force`.

## 0. Che cosa fa questo blocco, e perche' non ha un modulo

Gli **stessi otto candidati** di `walkforward.CANDIDATES` — possesso, field
tilt, PPDA (due lati), tocchi in area, distanza media di tiro, xG per tiro (due
lati) — furono scartati **sui tiri in porta** dalla Fase 2 e riesaminati dalla
6D, che ne dichiaro' la potenza: **28% nel regime maturo, 11% nell'acerbo**.

Qui si rifa' lo stesso test su un **bersaglio diverso** e su un perimetro **cinque
volte piu' grande**. `sot/predictor_power.py` e' stato parametrizzato su
`target`: V3 **non ha un modulo proprio**, ed e' un'eccezione dichiarata alla
regola «1 blocco = 1 modulo» — duplicare quel modulo violerebbe «una definizione
in un posto solo», che e' la ragione per cui `shots.py` e `perimetro.py`
esistono.

**Il default non si e' mosso**: `confronto(prev, r)` e
`confronto(prev, r, target="sot")` danno la stessa tabella bit per bit, e i
numeri di `reports/phase6_predittori.csv` si riproducono a 1e-12
(`poss_att` maturo, t = 1.4200797158768528). Due test lo bloccano.

> **Il difetto che la parametrizzazione poteva introdurre**, e che un test
> blocca: `_fit` costruiva `TeamModel` **senza** `target`. Siccome `y_in` era
> gia' del bersaglio giusto, il parametro sarebbe *sembrato* funzionare mentre
> il modello veniva stimato su `sot` e valutato sui tentativi. Il test pretende
> che la verosimiglianza in campione **cambi** al cambiare del target.

## 1. Il perimetro, e il guadagno di potenza

I predittori sono costruiti **una stagione per volta**. Sul concatenato
`pre_match_ewm` raggruppa per `team`, che e' un nome e si ripete fra stagioni:
la prima giornata di settembre 2023 riceverebbe una media a decadimento
dominata da maggio 2023 (peso 0,57 a 110 giorni), cioe' da una rosa che non
esiste piu'. E' l'argomento di E3 sul walk-forward, applicato un livello piu' in
basso. La firma e' verificabile e un test la usa: **la prima partita di ogni
stagione deve avere predittori nulli**.

| regime | righe nella 6D | righe qui | fattore |
|---|---:|---:|---:|
| maturo | 660 | {int(mat['n'].iloc[0])} | **{mat['n'].iloc[0] / 660:.1f}x** |
| acerbo | 100 | {int(c[c['regime'] == 'acerbo']['n'].iloc[0])} | **{c[c['regime'] == 'acerbo']['n'].iloc[0] / 100:.1f}x** |
| acerbo disgiunto | 40 | {int(dis['n'].iloc[0])} | **{dis['n'].iloc[0] / 40:.1f}x** |

**Il regime «acerbo disgiunto» era il risultato negativo piu' debole del
progetto** — 40 righe, MDE enorme — ed e' quello che questo blocco puo'
finalmente attaccare.

## 2. Il risultato: nessuno passa, in nessun regime

{_tab(c[["regime", "predittore", "n", "d_riga", "se_riga", "t", "mde_riga",
         "tenuto"]],
      {"d_riga": 5, "se_riga": 5, "t": 3, "mde_riga": 5, "n": 0})}

**Zero candidati tenuti su {len(c)} combinazioni.** E' il terzo test indipendente
con lo stesso esito — Fase 2 sui tiri in porta, 6D nei regimi acerbi, V3 sui
tentativi — e stavolta il MDE e' molto piu' stretto.

Nel regime maturo il massimo vale **t = {t_max:.3f}** ({mat.loc[mat['t'].idxmax(), 'predittore']}),
e su otto candidati un massimo del genere ha `p = {p_max:.3f}`: e' quanto ci si
aspetta sotto l'ipotesi nulla. **`t_atteso_massimo(8)` vale
{PP.t_atteso_massimo():.4f}**, cioe' il massimo osservato e' *sotto* il valore atteso
del massimo di otto normali standard.

## 3. La potenza, dichiarata — e un errore di lettura corretto per strada

| regime | MDE per riga | potenza contro l'alternativa {alt:.5f} |
|---|---:|---:|
{chr(10).join(f"| {r} | {c[c['regime'] == r]['mde_riga'].min():.5f} | {pot[r]:.0%} |" for r in PP.REGIMI)}

L'alternativa e' **l'effetto per riga piu' grande mai prodotto dagli otto
candidati in questo blocco** ({alt:.5f}, {mat.loc[mat['d_riga'].idxmax(), 'predittore']} nel
maturo), con l'errore standard piu' favorevole di ciascun regime. E' la stessa
costruzione della 6D: non la media degli otto, che sarebbe dominata dai
candidati a varianza minuscola e descriverebbe un test mai fatto.

### I MDE di due bersagli diversi non sono confrontabili in unita' assolute

Questo blocco era partito dall'aspettativa che cinque volte le righe dessero un
MDE piu' stretto. **E' falso in unita' assolute**, e va detto:

| regime | MDE 6D (tiri in porta) | MDE V3 (tentativi) |
|---|---:|---:|
| maturo | 0,00282 | {c[c['regime'] == 'maturo']['mde_riga'].min():.5f} |
| acerbo | 0,00668 | {c[c['regime'] == 'acerbo']['mde_riga'].min():.5f} |
| acerbo disgiunto | 0,00483 | {c[c['regime'] == 'acerbo disgiunto']['mde_riga'].min():.5f} |

Il MDE **peggiora**, nonostante le righe siano cinque volte tante. Il motivo e'
la scala del bersaglio: la log-verosimiglianza Poisson di un conteggio con media
12,6 ha una varianza per riga molto maggiore di uno con media 4,0, e il
guadagno di `sqrt(5)` non la compensa.

**L'unita' confrontabile e' adimensionale**: quanto vale il MDE rispetto a cio'
che il modello guadagna sul baseline migliore, **nella stessa unita'** di
log-verosimiglianza per riga. Un MDE pari al 10% di quel guadagno significa che
il test vede un predittore che valga un decimo del modello intero.

{_tab(rel, {"mde_riga": 5, "guadagno_modello_su_baseline": 5,
            "mde_in_quota_del_guadagno": 4, "n": 0})}

| regime | quota nella 6D | quota qui | |
|---|---:|---:|---|
| maturo | 0,118 | **{rel[rel['regime'] == 'maturo']['mde_in_quota_del_guadagno'].iloc[0]:.3f}** | **5x piu' sensibile** |
| acerbo | 0,159 | **{rel[rel['regime'] == 'acerbo']['mde_in_quota_del_guadagno'].iloc[0]:.3f}** | poco meglio |
| acerbo disgiunto | 0,057 | **{rel[rel['regime'] == 'acerbo disgiunto']['mde_in_quota_del_guadagno'].iloc[0]:.3f}** | **peggio** |

**Nel regime maturo il guadagno di potenza c'e' ed e' grande**: il test vede
predittori che valgono il 2,3% del modello intero, contro l'11,8% della 6D.
**Nel regime acerbo disgiunto no**, ed e' l'opposto di cio' che ci si aspettava:
li' il modello stacca i baseline **piu'** che nel maturo ({rel[rel['regime'] == 'acerbo disgiunto']['guadagno_modello_su_baseline'].iloc[0]:.3f}
contro {rel[rel['regime'] == 'maturo']['guadagno_modello_su_baseline'].iloc[0]:.3f}), quindi il
denominatore cresce piu' del numeratore.

**Resta la lettura della 6D, e va ripetuta**: un test negativo esclude effetti
grandi, non effetti piccoli. Che nessun candidato passi non dimostra che il loro
effetto sia zero — dimostra che se c'e', e' sotto il MDE dichiarato.

## 4. Due candidati PEGGIORANO, e nel regime dove ci si aspettava il contrario

{_tab(dis_neg[["regime", "predittore", "n", "d_riga", "t", "mde_riga"]],
      {"d_riga": 5, "t": 3, "mde_riga": 5, "n": 0}) if len(dis_neg) else "*(nessuno)*"}

Nel regime **acerbo disgiunto** — le primissime giornate, dove l'effetto attacco
e' piu' debolmente identificato e dove un predittore incrementale avrebbe *piu'*
spazio — `tilt_att` e `poss_att` non solo non aiutano: **danneggiano oltre la
soglia**, con `t` sotto −2.

E' l'osservazione piu' interessante del blocco, e la 6D non poteva farla: con 40
righe l'errore standard era tre volte piu' grande e quei `t` sarebbero stati
attorno a −0,8. La direzione e' coerente con il meccanismo che la Fase 2 aveva
dedotto e che la 6D ha reso visibile nei due termini dell'obiettivo: **un
predittore collineare con l'effetto attacco compra una riduzione della penalita'
ridge e paga in adattamento**. Dove l'effetto attacco e' acerbo, la sostituzione
e' peggiore.

{f"Nel regime **maturo** invece nessun candidato scende sotto −2 (il piu' negativo e' {mat.loc[mat['t'].idxmin(), 'predittore']} a t = {mat['t'].min():.3f})." if len(negativi) == 0 else ""}

## 5. Il contesto: il modello contro i baseline, dentro ogni regime

{_tab(ctx, {"mae": 4, "delta_vs_modello": 4, "n": 0})}

**E' la premessa del blocco, verificata invece che assunta.** Se nel regime
acerbo il modello non staccasse i baseline, un predittore incrementale avrebbe
piu' spazio per esistere — ed e' proprio l'ipotesi da testare. I baseline
vengono dal walk-forward di V1, gia' calcolati per stagione, invece di essere
ricalcolati poolando.

## 6. La consistenza fra stagioni

{_tab(seg, {c: 3 for c in seg.columns if c not in ("predittore", "positivi")})}

Cinque `t` con lo stesso segno sarebbero un'evidenza diversa da un `t` pooled
dello stesso valore. **Nessun candidato ha cinque segni positivi**, il che
toglie l'ultima lettura possibile di un pooled vicino a zero — che qualche
stagione nasconda un effetto reale annullato dalle altre.

## 7. Che cosa V3 conclude

**Gli otto predittori da dati evento non aggiungono niente al modello di
squadra, nemmeno sul bersaglio che li favorisce di piu'.** I tentativi sono la
grandezza piu' vicina a cio' che possesso e field tilt misurano — molto piu' dei
tiri in porta — e nemmeno li' passano.

Il meccanismo resta quello della Fase 2, ora misurato su tre bersagli: **gli
effetti attacco/difesa con decadimento assorbono gia' tutto cio' che una media
mobile di squadra puo' portare**. Un predittore che dice «questa squadra ha
avuto molto possesso nelle ultime partite» sta dicendo, con piu' rumore, «questa
squadra e' forte», che il coefficiente d'attacco gia' sa.

> **Trappola per le sessioni future.** Questo e' il **terzo** esito negativo
> sullo stesso insieme di candidati, e il piu' potente dei tre. Non va
> "sistemato" reintroducendone uno perche' il suo `t` e' il piu' alto: su otto
> candidati un massimo di {t_max:.2f} e' esattamente quanto ci si aspetta sotto
> l'ipotesi nulla, e il blocco lo calcola invece di lasciarlo intuire.

## 8. Domande aperte

1. **Il tetto in campione non e' stato rifatto multi-stagione.** `confronto` e'
   chiamato con `df=None`: la versione con i due numeri in campione della 6D
   richiederebbe un fit poolato che attraversa l'estate, cioe' esattamente cio'
   che V1 ha deciso di non fare. Il tetto della 6D vale per un altro bersaglio e
   **non si eredita**.
2. **Perche' `tilt_att` e `poss_att` danneggino nel regime acerbo** e' coerente
   col meccanismo della sostituzione ridge, ma non e' stato misurato **qui** nei
   due termini dell'obiettivo: `PP.penalita` lo farebbe, e vorrebbe lo stesso fit
   in campione del punto 1.
3. **I candidati sono gli otto dichiarati, e non e' stato allargato l'insieme**
   (decisione dell'utente). Candidati mirati al **volume** invece che alla
   qualita' — ritmo di gioco, corner, recuperi alti, stato del punteggio — non
   sono stati provati, e sarebbero un blocco a se' con la propria famiglia da
   correggere.
4. **La precisione potrebbe avere un predittore anche se il volume non ce l'ha**
   (domanda aperta di V2): `xg_per_shot` e' gia' fra gli otto e sul volume non
   passa, ma non e' stato testato sul **logit della quota**, che e' un altro
   bersaglio.
"""
    OUT_MD.write_text(testo, encoding="utf-8")
    for p in (OUT_MD, OUT_CSV, OUT_CTX, OUT_SEG):
        print(f"-> {p}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
