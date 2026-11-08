# -*- coding: utf-8 -*-
"""Fase 12 / Blocco V1 — lo strato del volume: i tentativi per squadra-partita.

    ./.venv/Scripts/python.exe scripts/run_fase12_v1.py [--force]

**Non tocca la rete.** Scrive una sola cache sotto `data/processed/`
(`fase12_walkforward_tiri.parquet`), rigenerabile con `--force`.

Stessa specificazione della Fase 2, bersaglio diverso, **validazione rifatta da
capo**: che il modello sia calibrato sui tiri in porta non dice niente sui
tentativi. Walk-forward **dentro** la stagione, come E3.

~30 s da cache, ~50 s con `--force`.
"""
from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sot import config, tentativi as T, validate as V, volume as VL  # noqa: E402

OUT_MD = config.REPORTS / "fase12_v1_volume.md"
OUT_VAL = config.REPORTS / "fase12_v1_valutazione.csv"
OUT_APP = config.REPORTS / "fase12_v1_appaiato.csv"
OUT_STAG = config.REPORTS / "fase12_v1_per_stagione.csv"
OUT_BRIER = config.REPORTS / "fase12_v1_brier_linee.csv"
OUT_SEG = config.REPORTS / "fase12_v1_segmenti.csv"
OUT_RAT = config.REPORTS / "fase12_v1_ratings.csv"


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
    ap.add_argument("--force", action="store_true",
                    help="rifa' il walk-forward invece di leggerlo dalla cache")
    args = ap.parse_args()

    print("Fase 12, blocco V1 — lo strato del volume")
    print("=" * 62)

    wf = VL.walkforward_tiri(force=args.force)
    cop = VL.copertura(wf)
    tot = cop.iloc[-1]
    print(f"[1] walk-forward: {len(wf)} righe con previsione, "
          f"{int(tot['valutabili'])} valutabili "
          f"({tot['quota_valutabile']:.1%} dell'universo)")

    val = VL.valutazione(wf)
    m = val.iloc[0]
    print(f"[2] modello: MAE {m['mae']:.4f}  bias {m['bias']:+.4f}  "
          f"corr {m['corr']:.4f}  pendenza {m['calib_slope']:.4f} "
          f"(z {m['calib_z_vs_1']:+.2f})")

    app = VL.confronto_appaiato(wf)
    b = app.iloc[0]
    print(f"[3] contro `{b['baseline']}`: delta MAE {b['delta_mae']:+.4f}, "
          f"t {b['t_per_riga']:.2f} per riga / {b['t_per_cluster']:.2f} per cluster")

    stag = VL.per_stagione(wf)
    print(f"[4] per stagione: vince in {int(stag['vince'].sum())}/5, "
          f"MAE relativo {stag['mae_relativo'].min():.3f}-{stag['mae_relativo'].max():.3f}")

    disp = VL.dispersione_tiri(wf)
    print(f"[5] dispersione: r NB2 {disp['nb2_r']:.2f} "
          f"(sospetto: {disp['suspicious']}), var/media grezzo "
          f"{disp['raw_var_mean_ratio']:.3f} -> Pearson {disp['pearson_dispersion']:.3f}")

    forma = VL.forma_predittiva(wf)
    print(f"[6] PIT: chi2 {forma['pit']['chi2']:.2f} su {forma['pit']['dof']} gdl, "
          f"p = {forma['pit']['p_value']:.4f}")

    brier = VL.brier_per_linea(wf)
    print(f"[7] Brier: vince su {int(brier['vince_su_baseline'].sum())}/"
          f"{len(brier)} linee contro il baseline migliore")

    seg = VL.segmenti(wf)
    print(f"[8] segmenti: vince in {int(seg['vince'].sum())}/{len(seg)}")

    rat = VL.ratings(wf)
    print(f"[9] ratings {rat['stagione'].iloc[0]}: "
          f"{rat['team'].iloc[0]} {rat['tentativi_attesi_trasferta'].iloc[0]:.2f} "
          f"-> {rat['team'].iloc[-1]} {rat['tentativi_attesi_trasferta'].iloc[-1]:.2f}, "
          f"vantaggio campo x{rat['vantaggio_campo'].iloc[0]:.3f}")

    val.to_csv(OUT_VAL, index=False, encoding="utf-8")
    app.to_csv(OUT_APP, index=False, encoding="utf-8")
    stag.to_csv(OUT_STAG, index=False, encoding="utf-8")
    brier.to_csv(OUT_BRIER, index=False, encoding="utf-8")
    seg.to_csv(OUT_SEG, index=False, encoding="utf-8")
    rat.to_csv(OUT_RAT, index=False, encoding="utf-8")

    como = rat[rat["team"] == "Como"]
    riga_como = (f"Il **Como** sta a {como['tentativi_attesi_trasferta'].iloc[0]:.2f} "
                 f"tentativi attesi (posizione {rat.index[rat['team'] == 'Como'][0] + 1} "
                 f"su {len(rat)})." if len(como) else "")

    testo = f"""# Fase 12 / Blocco V1 — lo strato del volume

> Generato da `scripts/run_fase12_v1.py` il {date.today().isoformat()}.
> **Non tocca la rete.** Unica scrittura sotto `data/`: la cache
> `fase12_walkforward_tiri.parquet`, rigenerabile con `--force`.

## 0. Che cosa fa questo blocco

```
shots_ij ~ NB2(lambda_ij, r)
log(lambda_ij) = mu + attacco_i + difesa_j + gamma * casa
```

**Stessa specificazione della Fase 2, bersaglio diverso.** E' voluto: se la
specificazione cambiasse insieme al bersaglio non si saprebbe a quale delle due
cose attribuire la differenza. E' la disciplina con cui E3 ha portato
`TeamModel` sui gol.

**La validazione non si eredita, ed e' rifatta da capo.** `r`, il tasso base, la
pendenza e il PIT sono ricostruiti sul solo passato, perche' entrano nelle
metriche e un parametro stimato sull'intero campione non e' fuori campione.

## 1. Il perimetro

{_tab(cop, {"quota_valutabile": 4})}

**I cold start sono cinque, non uno**, ed e' il costo del perimetro
multi-stagione: le prime tre giornate di ogni stagione non hanno previsione
(`date_splits` pretende 30 partite di training) e il burn-in ne toglie altre
due. Le due cause **non si sommano** e sono in colonne separate.

Le {int(tot['valutabili'])} righe valutabili sono le stesse di E3 sui gol, ed e'
un controllo di coerenza: due bersagli diversi sullo stesso universo devono
produrre lo stesso perimetro.

## 2. Il modello contro i quattro baseline (vincolo 6)

{_tab(val[["modello", "n", "mae", "bias", "corr", "sharpness", "calib_slope",
           "calib_se", "calib_z_vs_1", "brier", "brier_base"]],
      {"mae": 4, "bias": 4, "corr": 4, "sharpness": 4, "calib_slope": 4,
       "calib_se": 4, "calib_z_vs_1": 2, "brier": 4, "brier_base": 4, "n": 0})}

## 3. Il margine, e il suo `t` — per riga E per cluster

{_tab(app, {"mae_baseline": 4, "mae_modello": 4, "delta_mae": 4,
            "t_per_riga": 2, "t_per_cluster": 2, "rapporto": 3})}

**Questo e' il risultato del blocco: sui tentativi il modello si giustifica
anche sull'ACCURATEZZA, e sui tiri in porta non ci riusciva.**

| bersaglio | fase | `t` contro `media squadra + campo` |
|---|---|---:|
| tiri in porta | Fase 2 / Fase 4 | **1,86** — dentro il rumore |
| gol | Fase 9 / E3.1 | **5,52** |
| **tentativi** | **Fase 12 / V1** | **{b['t_per_cluster']:.2f}** |

Non e' un modello migliore: e' un **bersaglio piu' facile da distinguere**. I
tentativi sono tre volte piu' numerosi dei tiri in porta, quindi il rumore
relativo e' minore, e dipendono dal dominio territoriale, che e' la cosa piu'
persistente che una squadra abbia. Il tiro in porta aggiunge a quel volume un
passaggio di precisione che V2 modella a parte — ed e' proprio quel passaggio a
rendere i SoT piu' rumorosi.

**I due `t` si riportano in coppia**, e il rapporto e' la misura che rende
leggibile la correzione. V0 aveva previsto un fattore **0,807** dalla
correlazione fra i due lati (-0,349); l'osservato sul confronto appaiato vale
**{app['rapporto'].min():.3f}-{app['rapporto'].max():.3f}**, cioe' molto piu' vicino a 1.

**La previsione di V0 era approssimativa e va corretta**: quel fattore riguarda
la correlazione dei **valori**, mentre qui conta la correlazione degli **errori**
del confronto appaiato, che e' molto piu' debole. Le due squadre di una partita
si sottraggono i tentativi, ma il modello non sbaglia sull'una perche' ha
sbagliato sull'altra. La conclusione non cambia — il `t` per cluster resta
l'unita' onesta e resta enorme — ma il numero di V0 non va citato come se
descrivesse questo.

## 4. La calibrazione, e perche' e' l'argomento piu' forte

Il modello ha pendenza **{m['calib_slope']:.4f} ± {m['calib_se']:.4f}**
(z = {m['calib_z_vs_1']:+.2f}), cioe' compatibile con 1.0. I due baseline
informativi stanno a {val.loc[1, 'calib_slope']:.3f} e {val.loc[2, 'calib_slope']:.3f}
con z {val.loc[1, 'calib_z_vs_1']:.1f} e {val.loc[2, 'calib_z_vs_1']:.1f}: danno
previsioni **troppo estreme**, perche' una media campionaria non regredisce
verso il centro. La ridge corregge esattamente quello.

E' la stessa forma dell'argomento della Fase 4, molto piu' netta. `media
campionato` non e' identificata (errore standard {val.loc[4, 'calib_se']:.3f} su un
lambda quasi costante), come in Fase 4 e per la stessa ragione.

## 5. Cinque quasi-repliche invece di un numero solo

{_tab(stag, {"media_osservata": 3, "mae": 4, "mae_relativo": 4, "bias": 4,
             "corr": 4, "delta_su_baseline": 4, "t_per_cluster": 2, "n": 0})}

**Vince in tutte e cinque**, con `t` per cluster fra {stag['t_per_cluster'].min():.1f} e
{stag['t_per_cluster'].max():.1f}. Cinque segni concordi sono un'evidenza diversa da un `t`
pooled dello stesso valore, e la seconda non si legge dalla prima.

**Il MAE assoluto non e' confrontabile fra stagioni** — il livello si muove del
5,5%, quindi un MAE piu' basso puo' voler dire solo che si tirava di meno. La
colonna da leggere in orizzontale e' `mae_relativo`, che resta fra
{stag['mae_relativo'].min():.3f} e {stag['mae_relativo'].max():.3f}: la difficolta' del problema non
cambia fra stagioni.

## 6. La dispersione, e la forma della predittiva

| | |
|---|---:|
| var/media **grezzo** | {disp['raw_var_mean_ratio']:.4f} |
| dispersione di Pearson, **condizionata a lambda** | {disp['pearson_dispersion']:.4f} |
| `r` NB2 | **{disp['nb2_r']:.2f}** |
| sospetto (`r < 10`) | {'si' if disp['suspicious'] else 'no'} |

I tentativi **sono sovradispersi**: `r = {disp['nb2_r']:.1f}` contro i 26,0 dei tiri in
porta. Condizionare a lambda toglie gran parte dell'eccesso
({disp['raw_var_mean_ratio']:.2f} -> {disp['pearson_dispersion']:.2f}), cioe' il modello
spiega una parte importante della variazione — ma non tutta, e la Poisson pura
sarebbe sbagliata su questo bersaglio. `r` entra nel Brier e negli intervalli
**ricostruita walk-forward**, mai stimata sull'intero campione.

**PIT randomizzato: chi2 = {forma['pit']['chi2']:.2f} su {forma['pit']['dof']} gdl,
p = {forma['pit']['p_value']:.4f}.** E' il controllo che la pendenza di calibrazione
non fa: la forma dell'intera distribuzione predittiva regge, non solo la media.

{_tab(forma['copertura'], {"livello": 2, "copertura": 4, "ampiezza_media": 3})}

La copertura e' **conservativa**, com'e' strutturale sui conteggi (la
discretezza impedisce di centrare il nominale) e come gia' osservato in Fase 4.

## 7. Le cinque linee, tutte

{_tab(brier, {"tasso_base": 4, "brier_modello": 4, "brier_baseline": 4,
              "brier_tasso_base": 4, "linea": 1})}

**Vince su tutte e cinque**, contro il baseline migliore e contro il tasso base.
Una linea sola sarebbe un risultato scelto: e' la lezione della Fase 4, che
misuro' su quattro soglie invece che su una.

## 8. I segmenti, e il terzile alto

{_tab(seg, {"mae_modello": 4, "mae_baseline": 4, "delta": 4, "bias": 4, "n": 0})}

**Vince in tutti e sette**, e il terzile alto e' la riga interessante. Sui tiri
in porta la Fase 4 aveva trovato che il modello **perde** li' (+0,0031 di
Brier), ed era lo shrinkage: le squadre che tirano molto sono quelle che il
ritorno alla media penalizza. Sui tentativi il margine si **attenua**
({seg.loc[seg['valore'] == 'alto', 'delta'].iloc[0]:.4f} contro
{seg.loc[seg['valore'] == 'basso', 'delta'].iloc[0]:.4f} nel terzile basso) ma **non si
inverte**.

E' la stessa firma, piu' debole: la compressione della ridge esiste anche qui —
e' la quinta misura dello stesso effetto dopo Fase 3, Fase 4, 6A e R3 — ma su un
bersaglio piu' informativo non arriva a rovesciare il confronto. **Non va
"corretta"**: sarebbe la quinta volta che il progetto rifiuta quella strada.

Il MAE cresce col lambda (terzile basso {seg.loc[seg['valore'] == 'basso', 'mae_modello'].iloc[0]:.3f},
alto {seg.loc[seg['valore'] == 'alto', 'mae_modello'].iloc[0]:.3f}) ed e' atteso: su conteggi
la varianza cresce con la media.

## 9. I ratings — una descrizione, non una previsione

{_tab(rat[["team", "attack", "defence", "tentativi_attesi_trasferta"]].head(10),
      {"attack": 4, "defence": 4, "tentativi_attesi_trasferta": 3})}

*(prime dieci; la tabella intera e' in `fase12_v1_ratings.csv`)*

**Il fit usa tutta la stagione**, quindi serve a leggere il modello e non a
validarlo. La scala e' quella di `fig5` — **avversario medio in trasferta**, non
campo neutro: la Fase 6A dovette documentarlo dopo averlo scoperto, e qui si
dichiara subito. Vantaggio del campo **x{rat['vantaggio_campo'].iloc[0]:.3f}**.
{riga_como}

## 10. Che cosa V1 consegna

1. **A V2**: la cache `fase12_walkforward_tiri.parquet` con `lam` e, accanto,
   `sot` e `shots` osservati — cosi' V2 non deve rifare nessun join. E `r` dello
   strato 1, che la composizione riusa invece di ristimare.
2. **A V3**: lo stesso perimetro e gli stessi baseline, su cui i predittori da
   dati evento vanno testati con la potenza dichiarata.
3. **A V4**: il modello che il ponte `previsione(squadra, avversario, campo)`
   interroghera'.

## 11. Domande aperte

1. **Il fattore di cluster previsto da V0 (0,807) non descrive il confronto
   appaiato** ({app['rapporto'].min():.3f}-{app['rapporto'].max():.3f} osservato). La correlazione
   fra i **valori** dei due lati e' forte e negativa; quella fra gli **errori**
   e' debole. Perche' lo sia non e' stato misurato.
2. **`r` e' assunto costante fra squadre e fra stagioni.** La sovradispersione
   potrebbe dipendere dal livello — le squadre che tirano molto potrebbero
   essere anche piu' variabili — e non e' stato guardato.
3. ~~**Il totale di partita.**~~ `[CHIUSA - Fase 15 / T1]` La risposta e' che la
   congiunta **non serve**: la media del totale e' esatta comunque, e la
   dipendenza si assorbe stimando `r_tot` sui totali osservati (83,97 contro
   20,00 per lato, IC95 del rapporto [3,46, 5,66], che non contiene 1).
   L'indipendenza ingrassa entrambe le code fino a 3,4 punti percentuali.
   Vedi `reports/fase15_totale.md`.
4. **Il `gamma` della 2021-22 non e' confrontabile** con gli altri quattro (e' la
   prima stagione di ritorno del pubblico). Dentro stagione non fa danno; una
   media dei cinque sarebbe una media di due regimi.
"""
    OUT_MD.write_text(testo, encoding="utf-8")
    for p in (OUT_MD, OUT_VAL, OUT_APP, OUT_STAG, OUT_BRIER, OUT_SEG, OUT_RAT):
        print(f"-> {p}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
