# -*- coding: utf-8 -*-
"""Fase 12 / Blocco V4 — il ponte `previsione(squadra, avversario, campo)`.

    ./.venv/Scripts/python.exe scripts/run_fase12_v4.py [--squadra Como]

**Non tocca la rete e non scrive niente sotto `data/`.** Legge il walk-forward
di V1 e l'universo delle cinque stagioni.

E' cio' che l'utente ha chiesto: dato in ingresso squadra, avversario e campo, la
distribuzione del numero di tiri. Scrive anche
`reports/fase12_v4_simulatore.html`, la pagina locale interattiva.

~20 s.
"""
from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sot import config, previsione as P, tentativi as T, volume as VL  # noqa: E402
import pagina_v4  # noqa: E402

OUT_MD = config.REPORTS / "fase12_v4_ponte.md"
OUT_CSV = config.REPORTS / "fase12_v4_tiri_attesi.csv"
OUT_HTML = config.REPORTS / "fase12_v4_simulatore.html"


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
    ap.add_argument("--squadra", default="Como", help="la squadra dell'esempio")
    args = ap.parse_args()

    print("Fase 12, blocco V4 — il ponte previsione(squadra, avversario, campo)")
    print("=" * 68)

    stagione = config.SEASONS_STORICHE[-1]
    tab = P.tabella_completa(stagione)
    print(f"[1] tabella completa: {len(tab)} righe "
          f"({tab['squadra'].nunique()} squadre x {tab['squadra'].nunique() - 1} "
          f"avversari x 2 campi)")

    lo = tab.loc[tab["lambda_tentativi"].idxmin()]
    hi = tab.loc[tab["lambda_tentativi"].idxmax()]
    print(f"[2] dispersione: da {lo['lambda_tentativi']:.2f} "
          f"({lo['squadra']}-{lo['avversario']}, {lo['campo']}) a "
          f"{hi['lambda_tentativi']:.2f} ({hi['squadra']}-{hi['avversario']}, "
          f"{hi['campo']}) — fattore {hi['lambda_tentativi'] / lo['lambda_tentativi']:.2f}")

    esempio = P.previsione(args.squadra, "Inter", "casa", stagione)
    print(f"[3] esempio {args.squadra}-Inter (casa): "
          f"{esempio['lambda_tentativi']:.2f} tiri, "
          f"{esempio['lambda_sot']:.2f} in porta, r {esempio['r']:.1f}")

    t_sq = P.tabella_avversari(args.squadra, stagione)
    casa = t_sq[t_sq["campo"] == "casa"]
    fuori = t_sq[t_sq["campo"] == "trasferta"]
    print(f"[4] {args.squadra}: in casa {casa['lambda_tentativi'].min():.2f}-"
          f"{casa['lambda_tentativi'].max():.2f}, in trasferta "
          f"{fuori['lambda_tentativi'].min():.2f}-{fuori['lambda_tentativi'].max():.2f}")

    # Le guardie, esercitate: e' il modo in cui si dimostra che esistono.
    guardie = []
    for descr, fn in (
            ("squadra non in stagione", lambda: P.previsione(args.squadra, "Venezia", "casa", stagione)),
            ("squadra == avversario", lambda: P.previsione(args.squadra, args.squadra, "casa", stagione)),
            ("campo non ammesso", lambda: P.previsione(args.squadra, "Inter", "fuori", stagione))):
        try:
            fn()
            guardie.append({"guardia": descr, "solleva": False, "messaggio": "—"})
        except ValueError as e:
            guardie.append({"guardia": descr, "solleva": True,
                            "messaggio": str(e)[:64] + "…"})
    guardie = pd.DataFrame(guardie)
    print(f"[5] guardie: {int(guardie['solleva'].sum())}/{len(guardie)} sollevano")

    tab.to_csv(OUT_CSV, index=False, encoding="utf-8")
    pagina_v4.scrivi(tab, OUT_HTML, stagione=stagione,
                     come_di=str(esempio["come_di"])[:10], r=esempio["r"],
                     linee=T.LINEE_TIRI, limiti=P.limiti())

    top = tab.sort_values("lambda_tentativi", ascending=False)
    medie = (tab.groupby(["squadra", "campo"])["lambda_tentativi"].mean()
             .unstack().round(2).sort_values("casa", ascending=False))
    medie["divario"] = (medie["casa"] / medie["trasferta"]).round(3)

    testo = f"""# Fase 12 / Blocco V4 — il ponte `previsione(squadra, avversario, campo)`

> Generato da `scripts/run_fase12_v4.py` il {date.today().isoformat()}.
> **Non tocca la rete e non scrive niente sotto `data/`.**

## 0. Che cosa questo blocco consegna

**E' la risposta alla domanda dell'utente**: dato in ingresso una squadra, un
avversario e il campo, la distribuzione del numero di tiri.

```python
from sot import previsione as P
p = P.previsione("Como", "Inter", "casa")
p["lambda_tentativi"]   # {esempio['lambda_tentativi']:.3f}
p["p_over"]             # P(Over) per le cinque linee, con la quota di pareggio
p["intervalli"]         # 50 / 80 / 95%
```

Prima di V4 il progetto **non aveva** una funzione del genere per una squadra
qualsiasi: `soglie_2627` la aveva per il **solo Como** e per il **solo 2026-27**,
ancorata a un livello fornito dall'utente che per le altre diciannove squadre non
esiste. Qui il livello non serve, perche' la previsione e' **within-season**: il
modello sa gia' quanto tira ciascuna squadra perche' gliel'hanno detto le partite
precedenti. Ed e' l'unica forma **validabile** — V1 la misura su 3.278 righe.

## 1. La dispersione fra le coppie, che e' il motivo per cui il ponte serve

| | squadra | avversario | campo | tiri attesi |
|---|---|---|---|---:|
| minimo | {lo['squadra']} | {lo['avversario']} | {lo['campo']} | **{lo['lambda_tentativi']:.2f}** |
| massimo | {hi['squadra']} | {hi['avversario']} | {hi['campo']} | **{hi['lambda_tentativi']:.2f}** |

**Un fattore {hi['lambda_tentativi'] / lo['lambda_tentativi']:.2f} fra la coppia piu' bassa e la piu' alta**, contro una
media di campionato di {T.universo([stagione])[T.TARGET].mean():.2f}. Un numero unico per
squadra non basta, e nemmeno un numero per squadra piu' il campo: l'avversario
sposta il lambda quanto il campo.

## 2. Le venti squadre, medie sui diciannove avversari

{_tab(medie.reset_index(), {"casa": 2, "trasferta": 2, "divario": 3})}

Il **divario casa/trasferta** e' quasi costante fra squadre ed e' il vantaggio
del campo del modello (x{np.exp(VL.ratings()['vantaggio_campo'].iloc[0] * 0 + np.log(VL.ratings()['vantaggio_campo'].iloc[0])):.3f}):
il modello lo stima **una volta sola** per tutto il campionato, quindi le
differenze residue vengono solo dal fatto che ogni squadra affronta un insieme
diverso di avversari.

## 3. Un esempio letto per intero — {args.squadra} contro l'Inter, in casa

| | |
|---|---:|
| tiri attesi | **{esempio['lambda_tentativi']:.3f}** |
| di cui in porta | {esempio['lambda_sot']:.3f} |
| precisione implicita | {100 * esempio['quota_in_porta_implicita']:.1f}% |
| `r` (NB2) | {esempio['r']:.2f} |
| stimato su | {esempio['partite_di_storia']} partite, al {str(esempio['come_di'])[:10]} |
| alpha | {esempio['alpha']:.1f} |

{_tab(esempio['p_over'], {"linea": 1, "p_over": 4, "quota_pareggio": 3})}

{_tab(esempio['intervalli'], {"livello": 2, "basso": 0, "alto": 0})}

**L'intervallo all'80% e' largo {esempio['intervalli'].loc[1, 'alto'] - esempio['intervalli'].loc[1, 'basso']:.0f} tiri**, ed e' il numero
che va guardato insieme al lambda: il modello prevede bene la *distribuzione* e
male il *numero*, ed e' esattamente cio' che V1 misura (MAE 3,57).

## 4. {args.squadra} contro tutti, in casa e in trasferta

{_tab(t_sq.head(12), {"lambda_tentativi": 2, "lambda_sot": 2,
                      **{f"p_over_{ln}": 3 for ln in T.LINEE_TIRI}})}

*(prime dodici righe; la tabella completa delle {len(tab)} coppie e' in
`fase12_v4_tiri_attesi.csv`)*

## 5. Le guardie, esercitate

{_tab(guardie)}

**La guardia sulla squadra sconosciuta sta a due livelli, e servono entrambi.**
`verifica_squadre` protegge l'API; `TeamModel(strict_teams=True)` protegge il
modello, perche' una guardia sola all'ingresso si aggira chiamando il modello
direttamente — che e' il buco che `soglie_2627.difese_avversari` tappa per il
solo Como.

**Il difetto e' silenzioso**, ed e' la ragione per cui la guardia esiste:
`df["team"].map(idx)` da' `NaN`, la maschera salta la riga e la dummy resta a
zero, cioe' la squadra viene trattata **come esattamente media**, senza errore
ne' avviso. Il caso realistico non e' la squadra inventata: e' chiedere
**{args.squadra}-Venezia nel {stagione}**, dove il Venezia non c'era.

**`strict_teams` ha default `False`** e un test verifica che con quel default le
previsioni siano identiche bit per bit: dentro il walk-forward il coefficiente
zero e' il comportamento *giusto* — una squadra alla sua prima apparizione in un
training parziale — e sollevare romperebbe la Fase 2, E3 e R0-R3.

**`campo` e' una stringa e non un booleano**: un `0/1` si scambierebbe senza
rumore, e la differenza fra casa e trasferta vale un quarto del livello.

## 6. La pagina locale

`reports/fase12_v4_simulatore.html` — si sceglie squadra, avversario e campo e si
leggono lambda, precisione implicita, `P(Over)` per le cinque linee e la quota di
pareggio.

**E' autonoma**: nessun CDN, nessun font remoto, nessuna richiesta di rete, e un
test lo pretende — «pagina locale» vuol dire che funziona offline.

**Nessuna quota** (vincolo 3): la pagina mostra la quota di **pareggio**
(`1/p`), che e' il punto in cui il guadagno sarebbe zero, e lo dichiara come tale
invece di presentarlo come una previsione di prezzo. Non propone quote e non
calcola guadagni.

## 7. I limiti, accanto ai numeri

{chr(10).join(f'{i + 1}. {x}' for i, x in enumerate(P.limiti()))}

## 8. Domande aperte

1. **`al` e' esposto ma il report non lo usa**: tutte le tabelle qui sono alla
   fine della stagione, quindi `dentro_campione` e' `True` per le coppie gia'
   giocate. Per una previsione vera va passato `al` con la data della giornata,
   e la funzione lo dichiara. Non e' stato costruito un esempio giornata per
   giornata: sarebbe la naturale coda del blocco.
2. **La stagione e' una sola** (`{stagione}`). Il ponte accetta le altre quattro,
   ma i ratings di una stagione passata servono a poco se non per verifica.
3. ~~**Il totale di partita non e' esposto.**~~ `[CHIUSA - Fase 15 / T1]` Non
   serviva la congiunta: `sot/totale.py` somma i due lambda (esatto) e stima
   `r_tot` sui totali. **Con un limite dichiarato**: sul totale il lambda e'
   sotto-calibrato (pendenza 0,63 contro 1,008 per lato), perche' il modello
   crede i due lati piu' anti-correlati di quanto siano.
4. **Nessun prezzo di mercato**: finche' non ci sono quote di chiusura reali,
   «il modello e' meglio del mercato» non e' una frase che questo progetto possa
   pronunciare.
"""
    OUT_MD.write_text(testo, encoding="utf-8")
    for p in (OUT_MD, OUT_CSV, OUT_HTML):
        print(f"-> {p}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
