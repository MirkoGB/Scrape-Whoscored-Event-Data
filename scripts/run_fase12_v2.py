# -*- coding: utf-8 -*-
"""Fase 12 / Blocco V2 — lo strato della precisione, e la composizione.

    ./.venv/Scripts/python.exe scripts/run_fase12_v2.py [--force]

**Non tocca la rete.** Scrive una sola cache sotto `data/processed/`
(`fase12_strato2.parquet`), rigenerabile con `--force`.

Il blocco misura due cose che e' facile confondere: se la **quota** in porta sia
prevedibile meglio di un numero unico (§2, condizionata su `shots` osservati,
che NON e' una previsione), e se la **marginale composta** batta il modello
diretto sui tiri in porta (§4, che e' la previsione vera).

~40 s da cache, ~1 min con `--force`.
"""
from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import nbinom

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sot import config, precisione as PR, tentativi as T  # noqa: E402

OUT_MD = config.REPORTS / "fase12_v2_precisione.md"
OUT_QUOTA = config.REPORTS / "fase12_v2_quota.csv"
OUT_MARG = config.REPORTS / "fase12_v2_marginale.csv"
OUT_CONF = config.REPORTS / "fase12_v2_confronto_diretto.csv"
OUT_STAG = config.REPORTS / "fase12_v2_per_stagione.csv"


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

    print("Fase 12, blocco V2 — la precisione, e la composizione")
    print("=" * 62)

    wf = PR.walkforward_precisione(force=args.force)
    d = PR._valutabili(wf)
    print(f"[1] strato 2: {len(wf)} righe, {len(d)} valutabili")

    quota = PR.valutazione_condizionata(wf)
    print("[2] la QUOTA (condizionata su shots osservati, NON una previsione):")
    for _, r in quota.iterrows():
        t = r["t_vs_lega"]
        t_txt = "  —  " if pd.isna(t) else f"{t:+.2f}"
        print(f"    {r['modello']:<28} ll/riga {r['ll_per_riga']:.5f}  "
              f"corr {r['corr']:+.4f}  t vs lega {t_txt}")

    lati = PR.confronto_lati(wf)
    print(f"[3] costo della difesa: guadagno ll/riga "
          f"{lati['guadagno_ll_per_riga']:+.5f} (MDE {lati['mde_ll_per_riga']:.5f}), "
          f"t {lati['t_quota']:+.2f} -> paga: {lati['la_difesa_paga']}")

    marg = PR.marginale_composta(wf)
    print("[4] la MARGINALE COMPOSTA contro il modello diretto:")
    for _, r in marg.iterrows():
        print(f"    {r['modello']:<28} MAE {r['mae']:.4f}  "
              f"pendenza {r['calib_slope']:.4f} (z {r['calib_z_vs_1']:+.2f})")

    conf = PR.confronto_col_diretto(wf)
    stag = PR.per_stagione(wf)
    print(f"[5] la gerarchia batte il diretto in {int(stag['gerarchia_vince'].sum())}/5 stagioni")

    disp = PR.rapporto_dispersioni(wf, n_boot=1000)
    print(f"[6] rapporto dispersioni r_sot/r_shots = {disp['rapporto']:.3f} "
          f"IC95 [{disp['ic95'][0]:.2f}, {disp['ic95'][1]:.2f}] -> "
          f"uguali: {disp['uguali']}")

    ver = PR.verdetto_gerarchia(conf, stag)
    print(f"[7] VERDETTO: {ver['ramo']}")

    quota.to_csv(OUT_QUOTA, index=False, encoding="utf-8")
    marg.to_csv(OUT_MARG, index=False, encoding="utf-8")
    conf.to_csv(OUT_CONF, index=False, encoding="utf-8")
    stag.to_csv(OUT_STAG, index=False, encoding="utf-8")

    # Verifiche della composizione, rifatte qui per il report.
    a = PR.pmf_composta(12.5, 0.33, 20.0, rho=0.0)
    b = nbinom.pmf(np.arange(len(a)), 20.0, 20.0 / (20.0 + 12.5 * 0.33))
    c = PR.pmf_composta(12.5, 0.33, 20.0, rho=1e-9)
    e = PR.pmf_composta(12.5, 0.33, 20.0, rho=0.05)

    testo = f"""# Fase 12 / Blocco V2 — la precisione, e la composizione

> Generato da `scripts/run_fase12_v2.py` il {date.today().isoformat()}.
> **Non tocca la rete.** Unica scrittura sotto `data/`: la cache
> `fase12_strato2.parquet`, rigenerabile con `--force`.

## 0. Le due domande, che e' facile confondere

```
strato 2   sot_ij | shots_ij ~ Binomiale(shots_ij, p_ij)
           logit(p_ij) = mu_p + a_i + d_j + g_p * casa
```

1. **La quota e' prevedibile meglio di un numero unico?** (§2) Si misura
   condizionando su `shots` osservati — e **non e' una previsione di `sot`**,
   perche' quando si prevede i tentativi non sono ancora stati tirati.
2. **La marginale composta batte il modello diretto sui tiri in porta?** (§4)
   Questa e' la previsione vera, e il concorrente non e' un baseline stupido: e'
   il modello che la Fase 2 ha gia' pubblicato.

Il criterio e' stato scritto **prima** di guardare i numeri:

> {PR.CRITERIO_GERARCHIA}

## 1. I lati: decisione dell'utente, non esito del criterio

`[DECISO 2026-08-13]` dall'utente: **la difesa entra nello strato 2**.

Il criterio di V0, applicato meccanicamente, diceva *solo attacco*: sul lato
difensivo il test di dispersione rifiuta (z = +2,51) ma `tau` resta **sotto il
proprio MDE tarato** (1,39 contro 1,59 punti). **Il criterio non e' stato
riscritto** e `tentativi.verdetto_strato2()` continua a rispondere
`['attacco']`.

La decisione aveva un argomento — la seconda strada, indipendente e piu'
potente, rifiuta nettamente (GLM, F = 2,83, p = 2,3e-06) — e aveva un costo
dichiarato. **Questo blocco lo misura invece di assumerlo**, ed e' §3.

## 2. La quota, condizionata su `shots` osservati

{_tab(quota[["modello", "n", "ll_per_riga", "mae_quota", "brier_quota", "corr",
             "guadagno_per_riga", "t_vs_lega"]],
      {"ll_per_riga": 5, "mae_quota": 5, "brier_quota": 5, "corr": 4,
       "guadagno_per_riga": 5, "t_vs_lega": 2, "n": 0})}

**Il risultato e' negativo, e va letto per quello che e': l'eterogeneita' che V0
ha trovato esiste, ma NON e' predittiva.**

V0 aveva misurato una `tau` di 2,12 punti di quota fra squadre, con z = +5,91 e
un nullo simulato: quel risultato **non e' smentito**. Ma era una misura
*descrittiva*, su squadre-stagione complete (~475 tentativi ciascuna). Qui il
modello deve dire la quota di **una** squadra-partita (~12,6 tentativi) prima
che si giochi, e li' il segnale non sopravvive al rumore: il modello ha
correlazione positiva con la quota vera ({quota.loc[0, 'corr']:+.4f} e
{quota.loc[1, 'corr']:+.4f} contro {quota.loc[2, 'corr']:+.4f} del baseline) e
**verosimiglianza peggiore**, cioe' e' troppo estremo per quanto poco sa.

E' la stessa forma del risultato della Fase 2 sugli otto predittori: un effetto
reale in campione che fuori campione non paga.

## 3. Il costo della decisione sulla difesa, misurato

| | |
|---|---:|
| guadagno in log-verosimiglianza per riga | **{lati['guadagno_ll_per_riga']:+.5f}** |
| MDE a potenza 80% | {lati['mde_ll_per_riga']:.5f} |
| `t` per cluster | **{lati['t_quota']:+.2f}** |
| MAE della composta, solo attacco | {lati['mae_composto_attacco']:.5f} |
| MAE della composta, attacco + difesa | {lati['mae_composto_attacco_difesa']:.5f} |
| la difesa paga | **{'si' if lati['la_difesa_paga'] else 'no'}** |

**La difesa non paga: costa.** Il guadagno e' negativo e il `t` supera la soglia
**nella direzione sbagliata** ({lati['t_quota']:+.2f}), cioe' il peggioramento non e'
rumore. Sulla marginale composta il MAE peggiora di
{abs(lati['delta_mae']):.5f} ({lati['t_mae']:+.2f}).

Questo era il rischio dichiarato prima di eseguire — «un effetto sotto il MDE
del test primario puo' valere zero fuori campione» — e la misura dice che vale
**meno** di zero. Il meccanismo e' leggibile: venti coefficienti difensivi in
piu' stimati su un segnale che il test primario non riusciva a risolvere sono
venti modi di adattarsi al rumore.

**Il criterio di V0 aveva ragione**, e lo si sa adesso che e' misurato.

## 4. La marginale composta contro il modello diretto

{_tab(marg[["modello", "n", "mae", "bias", "corr", "calib_slope",
            "calib_z_vs_1", "brier"]],
      {"mae": 4, "bias": 4, "corr": 4, "calib_slope": 4, "calib_z_vs_1": 2,
       "brier": 4, "n": 0})}

{_tab(conf, {"mae": 5, "mae_diretto": 5, "delta_mae": 5, "t_per_cluster": 3,
             "mde": 5})}

{_tab(stag, {"mae_gerarchia": 4, "mae_diretto": 4, "delta": 4, "n": 0})}

**Nessuna variante batte il modello diretto.** La migliore e' `solo attacco`
(delta MAE {conf.loc[1, 'delta_mae']:+.5f}, t = {conf.loc[1, 't_per_cluster']:.2f}), che
resta sotto la soglia e **dentro il proprio MDE**: il test esclude differenze
grandi, non differenze piccole.

E il segno **non e' stabile**: la gerarchia vince in
{int(stag['gerarchia_vince'].sum())} stagioni su 5, e il criterio ne chiedeva almeno 4.

## 5. La composizione, verificata dove la risposta e' nota

| verifica | esito |
|---|---|
| forma chiusa `== NB2(lam*p, r)` | {'passa' if np.allclose(a, b, atol=1e-14) else 'FALLISCE'} |
| la PMF chiusa somma a 1 | {a.sum():.10f} |
| convoluzione a `rho -> 0` coincide con la chiusa | {'passa' if np.allclose(a, c, atol=1e-6) else 'FALLISCE'} (max scarto {np.abs(a - c).max():.1e}) |
| a `rho = 0,05` la convoluzione **diverge** dalla chiusa | {'passa' if not np.allclose(a, e, atol=1e-4) else 'FALLISCE'} |
| la convoluzione conserva la media | {(e * np.arange(len(e))).sum():.4f} contro {12.5 * 0.33:.4f} |

**Una precisazione a V0.** Il report di V0 diceva che «la forma chiusa del
thinning non e' valida cosi' com'e', perche' `p` varia fra squadre». **E'
impreciso**: la forma chiusa vale **riga per riga** anche quando `p` cambia fra
righe, purche' dentro la riga sia un numero e non una variabile aleatoria — che
e' il caso di un `p_ij` prodotto da un modello.

Cio' che la romperebbe e' la variabilita' di `p` **dentro** la squadra-partita,
cioe' la sovradispersione residua che V0 ha misurato (`rho` intraclasse 0,0083)
e che nessun effetto di squadra cattura. `pmf_composta(rho > 0)` e' quella
strada, e si rifiuta di usare la scorciatoia.

## 6. Il rapporto delle dispersioni — la coerenza, falsificata

| | |
|---|---:|
| `r` su **tentativi** | {disp['r_shots']:.3f} |
| `r` su **tiri in porta** | {disp['r_sot']:.3f} |
| rapporto | **{disp['rapporto']:.3f}** |
| IC95 bootstrap | [{disp['ic95'][0]:.3f}, {disp['ic95'][1]:.3f}] |
| compatibile con 1 | **{'si' if disp['uguali'] else 'no'}** |

**Sotto il thinning le due `r` dovrebbero essere uguali, e non lo sono.**
L'intervallo non contiene 1, quindi la coerenza interna della gerarchia e'
**falsificata** — ed e' un risultato, non un difetto di stima.

Il segno e' quello **opposto** a quello che l'eterogeneita' della quota
prevedrebbe: `r_sot > r_shots` significa che i tiri in porta sono **meno**
sovradispersi di quanto il thinning imponga, non piu'. Una variabilita' extra
della quota li renderebbe piu' dispersi, quindi non e' quella la causa.

**Non e' stata spiegata**, ed e' la prima domanda aperta. Il candidato piu'
economico e' che il thinning non sia indipendente dal volume — chi tira molto
tira anche da posizioni diverse — ma misurarlo e' un altro blocco.

Ne segue una conseguenza operativa gia' applicata: `marginale_composta` usa `r`
**ricostruito walk-forward su `sot`** e non ereditato dallo strato 1. Ereditarlo
sarebbe piu' coerente con la gerarchia, ma imporrebbe una predittiva troppo
larga sulle code e farebbe apparire la gerarchia peggiore per una ragione che
non e' il suo lambda.

## 7. Il verdetto, applicato meccanicamente

**{ver['ramo'].upper()}**

| condizione | valore | soddisfatta |
|---|---:|---|
| non perde oltre il MDE | delta {ver['delta_mae']:+.5f} contro MDE {ver['mde']:.5f} | {'si' if ver['non_perde_oltre_il_mde'] else 'no'} |
| segno stabile (>= 4 stagioni su 5) | {ver['stagioni_in_cui_vince']}/5 | {'si' if ver['segno_stabile'] else 'no'} |
| **adotta la gerarchia** | | **{'si' if ver['adotta_la_gerarchia'] else 'no'}** |

**La gerarchia non si adotta, e non perche' sia peggiore: perche' non e'
migliore.** A parita' si tiene il modello con meno parti, ed e' la regola scritta
prima. Il modello diretto sui tiri in porta resta quello che V4 usera' per `sot`.

**Cio' che V1 ha prodotto resta intatto e non dipende da questo esito**: lo
strato del volume batte il baseline migliore per t = 9,63 ed e' il modello che
risponde alla domanda dell'utente. La gerarchia era il tentativo di ottenere
*anche* i tiri in porta dallo stesso oggetto, e il tentativo dice di no.

## 8. Domande aperte

1. **Il rapporto delle dispersioni (1,63) non e' spiegato**, ed e' il numero piu'
   interessante del blocco: dice che la composizione non e' internamente
   coerente, nel verso opposto a quello che l'eterogeneita' della quota
   prevedrebbe.
2. **La quota potrebbe essere prevedibile da altro che dall'identita' della
   squadra** — posizione dei tiri, tipo di azione, xG per tiro. `xg_per_shot` e'
   gia' in `team_match` ed e' fra gli otto candidati di V3: se la precisione ha
   un predittore, e' li' che si vedrebbe.
3. **`alpha` dello strato 2 e' dichiarato (6.0), non scelto.** La sensibilita' e'
   riportata da `sensibilita_alpha()` e non e' stata usata per ottimizzare:
   sceglierlo sul bersaglio sarebbe il vincolo 1 violato.
4. **Il ramo `rho > 0` della composizione non e' mai stato usato in previsione.**
   Esiste, e' verificato, e servirebbe se un blocco futuro volesse la predittiva
   completa di `sot` invece del solo lambda.
"""
    OUT_MD.write_text(testo, encoding="utf-8")
    for p in (OUT_MD, OUT_QUOTA, OUT_MARG, OUT_CONF, OUT_STAG):
        print(f"-> {p}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
