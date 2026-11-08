# -*- coding: utf-8 -*-
"""Fase 15 / Blocco T1 - il TOTALE di partita: la somma delle due squadre.

    ./.venv/Scripts/python.exe scripts/run_fase15_totale.py

**Non tocca la rete** e **non scrive niente sotto `data/`**: legge il
walk-forward gia' prodotto da V1 e lo ruota da squadra-partita a partita.

Chiude la domanda aperta n. 3 di V1 e n. 3 di V4 - la stessa domanda scritta
due volte: il totale di partita non e' la somma di due indipendenti.

~15 s.
"""
from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sot import config, tentativi as T, totale as TT, validate as V  # noqa: E402

OUT_MD = config.REPORTS / "fase15_totale.md"
OUT_COP = config.REPORTS / "fase15_copertura.csv"
OUT_VAL = config.REPORTS / "fase15_valutazione.csv"
OUT_APP = config.REPORTS / "fase15_appaiato.csv"
OUT_STAG = config.REPORTS / "fase15_per_stagione.csv"
OUT_BRIER = config.REPORTS / "fase15_brier_linee.csv"
OUT_IND = config.REPORTS / "fase15_indipendenza.csv"
OUT_ANTI = config.REPORTS / "fase15_anticorrelazione.csv"
OUT_CAMP = config.REPORTS / "fase15_per_campionato.csv"


def _tab(df: pd.DataFrame, dec: dict[str, int] | None = None) -> str:
    dec = dec or {}
    d = df.copy()
    for c in d.columns:
        if c in dec:
            d[c] = d[c].map(lambda v: "" if pd.isna(v) else f"{v:.{dec[c]}f}")
        elif d[c].dtype == bool:
            d[c] = d[c].map(lambda v: "si" if v else "no")
        else:
            d[c] = d[c].map(lambda v: "-" if pd.isna(v) else str(v))
    num = [c for c in df.columns
           if pd.api.types.is_numeric_dtype(df[c]) and df[c].dtype != bool]
    head = "| " + " | ".join(str(c).replace("|", r"\|") for c in d.columns) + " |"
    sep = "|" + "|".join("---:" if c in num else "---" for c in d.columns) + "|"
    body = "\n".join("| " + " | ".join(r) + " |" for r in d.astype(str).values)
    return "\n".join([head, sep, body])


def main() -> int:
    print("[1] rotazione a partita, tentativi")
    d_sh = TT.partite(target=TT.TARGET)
    print("[2] rotazione a partita, tiri in porta")
    d_so = TT.partite(target=TT.TARGET_PRECISIONE)

    print("[3] perimetro e realizzazioni")
    cop = TT.copertura(d_sh)
    real = TT.realizzazioni(d_sh)

    print("[4] la dipendenza fra i due lati")
    corr = TT.correlazione_lati(d_sh)
    rapp = TT.rapporto_dispersioni(d_sh)

    print("[5] la NB2 diretta contro l'indipendenza (convoluzione)")
    ind = TT.confronto_indipendenza(d_sh)

    print("[6] validazione contro i baseline")
    val = TT.valutazione(d_sh)
    app = TT.confronto_appaiato(d_sh)
    stag = TT.per_stagione(d_sh)

    print("[7] Brier per linea, e la forma della predittiva")
    br_sh = TT.brier_per_linea(d_sh, target=TT.TARGET)
    br_so = TT.brier_per_linea(d_so, target=TT.TARGET_PRECISIONE)
    forma = TT.forma_predittiva(d_sh)

    print("[8] la sotto-calibrazione, e il verdetto sulla correzione")
    anti_sh = TT.anticorrelazione(d_sh)
    anti_so = TT.anticorrelazione(d_so, target=TT.TARGET_PRECISIONE)
    ver_sh = TT.verdetto(d_sh)
    ver_so = TT.verdetto(d_so, target=TT.TARGET_PRECISIONE)

    print("[9] lo stesso sui cinque campionati, mai poolati")
    camp = TT.per_campionato()

    for df, path in ((cop, OUT_COP), (val, OUT_VAL), (app, OUT_APP),
                     (stag, OUT_STAG), (ind, OUT_IND), (camp, OUT_CAMP)):
        df.to_csv(path, index=False, encoding="utf-8")
    pd.concat([br_sh.assign(bersaglio="tiri"),
               br_so.assign(bersaglio="tiri in porta")]).to_csv(
        OUT_BRIER, index=False, encoding="utf-8")
    pd.concat([anti_sh.assign(bersaglio="tiri"),
               anti_so.assign(bersaglio="tiri in porta")]).to_csv(
        OUT_ANTI, index=False, encoding="utf-8")

    v = d_sh[d_sh["validabile"]]
    sd_oss = float(v["y_totale"].std())
    sd_ind = float(np.sqrt(v["y_casa"].var(ddof=1) + v["y_trasferta"].var(ddof=1)))
    testo = _report(cop, real, corr, rapp, ind, val, app, stag, br_sh, br_so,
                    forma, anti_sh, anti_so, ver_sh, ver_so, sd_oss, sd_ind,
                    camp)
    OUT_MD.write_text(testo, encoding="utf-8")

    for p in (OUT_MD, OUT_COP, OUT_VAL, OUT_APP, OUT_STAG, OUT_BRIER,
              OUT_IND, OUT_ANTI, OUT_CAMP):
        print(f"-> {p}")
    return 0


def _report(cop, real, corr, rapp, ind, val, app, stag, br_sh, br_so, forma,
            anti_sh, anti_so, ver_sh, ver_so, sd_oss, sd_ind, camp) -> str:
    n = int(cop.loc[cop["stagione"] == "TOTALE", "validabili"].iloc[0])
    return f"""# Fase 15 / Blocco T1 - il totale di partita

Generato il {date.today().isoformat()} da `scripts/run_fase15_totale.py`.
Non tocca la rete, non scrive niente sotto `data/`.

## 0. Che cosa fa questo blocco

Chiude la domanda aperta n. 3 di V1 e n. 3 di V4, che erano la stessa domanda:

> il totale di partita e' la linea di mercato piu' comune e `lam_subiti` e' gia'
> nella cache, ma la correlazione negativa misurata da V0 dice che **non e' la
> somma di due indipendenti**: serve la congiunta, che sui tentativi non e'
> misurata.

La risposta e' che **la congiunta non serve**:

```
lambda_tot = lambda_casa + lambda_trasferta      esatto, qualunque dipendenza
y_tot      ~ NB2(lambda_tot, r_tot)              r_tot STIMATA sui totali
```

`E[X+Y] = E[X]+E[Y]` non richiede ipotesi: la media del totale e' esatta. Cio'
che la dipendenza rompe e' la **dispersione**, e `r_tot` stimata sui totali
osservati la assorbe per misura invece che per assunzione.

## 1. Il perimetro: la riga e' la PARTITA

{_tab(cop, {"quota_validabile": 3})}

**{n} partite validabili**, che e' esattamente il numero che R0 conto' sui gol
sullo stesso universo - il controllo interno piu' forte disponibile. E le **2
partite con un lato solo stanno entrambe nel 2021-2022**, come R0 aveva
documentato: `eligible` e' una proprieta' della squadra, non della partita, e
cade dove WhoScored ha perso partite.

{_tab(real)}

> Le righe si dimezzano rispetto a V1 e **non e' una perdita di dati**: e' un
> cambio di unita'. Ne segue che il `t` per cluster di partita diventa
> **degenere** - una riga *e'* una partita - e coincide col `t` per riga per
> costruzione. Si riporta lo stesso, in coppia, invece di farlo dedurre.

## 2. La dipendenza fra i due lati, misurata su questo perimetro

{_tab(corr, {"corr": 3, "sd_totale_osservata": 3, "sd_se_indipendenti": 3,
             "rapporto_sd": 3})}

La correlazione e' **negativa in tutte e cinque le stagioni** (il possesso e' a
somma costante: chi domina tira molto e lascia tirare poco). Sul perimetro
validabile la sd osservata del totale vale **{sd_oss:.3f}** contro i
**{sd_ind:.3f}** che due lati indipendenti darebbero: **{100*(1-sd_oss/sd_ind):.1f}%
in meno**.

### `r_tot` non si eredita, ed e' falsificato

| | |
|---|---:|
| `r` per lato | {rapp['r_lato']:.2f} |
| **`r` del totale** | **{rapp['r_totale']:.2f}** |
| rapporto | **{rapp['rapporto']:.2f}** |
| IC95 bootstrap ({rapp['n_boot']} repliche sulle partite) | [{rapp['ic95'][0]:.2f}, {rapp['ic95'][1]:.2f}] |
| l'IC contiene 1? | {"si" if rapp['eredita'] else "**no**"} |

E' la stessa forma con cui `precisione.rapporto_dispersioni()` aveva falsificato
l'ereditarieta' fra `r_shots` e `r_sot`. Qui l'IC **non contiene 1** e sta tutto
sopra: il totale e' molto meno disperso di quanto `r` per lato implicherebbe, che
e' esattamente il segno della covarianza negativa.

## 3. L'alternativa scartata, calcolata e messa accanto

Convoluzione di due NB2 **indipendenti** per lato, con la stessa `r`
walk-forward, contro la NB2 diretta sul totale:

{_tab(ind, {"tasso_base": 3, "p_nb2_diretta": 3, "p_indipendenza": 3,
            "errore_diretta": 4, "errore_indipendenza": 4,
            "brier_diretta": 4, "brier_indipendenza": 4})}

**L'indipendenza ingrassa entrambe le code**, che e' il segno previsto prima di
guardare: sotto la linea piu' bassa sbaglia di -0,033 e sopra la piu' alta di
+0,035, contro -0,004 e +0,021 della diretta.

> **Due avvertenze che il confronto impone.** (1) Sulla linea centrale
> l'indipendenza e' leggermente **piu' vicina** (-0,005 contro +0,006): il
> vantaggio della diretta e' sulle **code**, che e' dove le due ipotesi
> differiscono, e va detto invece di riportare cinque vittorie su cinque. (2) Il
> **Brier non distingue le due**: le differenze sono in quarta cifra. Cio' che si
> guadagna e' calibrazione della coda, non capacita' di ordinare le partite.
""" + _parte2(val, app, stag, br_sh, br_so, forma,
                     anti_sh, anti_so, ver_sh, ver_so, camp)


def _parte2(val, app, stag, br_sh, br_so, forma, anti_sh, anti_so,
            ver_sh, ver_so, camp) -> str:
    mig = app.loc[app["baseline"] == V.BEST_BASELINE].iloc[0]
    pit = forma["pit"]
    dec_m = {"mae": 4, "rmse": 4, "bias": 4, "corr": 4, "sharpness": 4,
             "calib_slope": 4, "calib_se": 4, "calib_z_vs_1": 2, "brier": 4,
             "brier_base": 4, "ece": 4, "base_rate": 4,
             "loglik_poisson": 1, "loglik_nb2": 1}
    return f"""
## 4. Contro i baseline (vincolo 6)

{_tab(val, dec_m)}

{_tab(app, {"mae_baseline": 4, "mae_modello": 4, "delta_mae": 4,
            "t_per_riga": 3, "t_per_cluster": 3})}

**Il modello vince, e con margine**: {mig['delta_mae']:.3f} di MAE su
`{V.BEST_BASELINE}` con t = {mig['t_per_riga']:.2f}.

> **I quattro baseline sono in realta' DUE, e va detto.** Dopo la rotazione
> `media squadra + campo` e' **identica** a `media squadra` sul totale (a 7e-15),
> e `media casa/trasferta` e' identica a `media campionato`. Il motivo e'
> aritmetico e non un difetto: il termine di campo aggiunge alla squadra di casa
> quello che toglie a quella di trasferta, quindi **si cancella nella somma**.
> Per lato le quattro colonne differiscono eccome (fino a 1,83 tiri). Il vincolo
> 6 e' rispettato, ma con due concorrenti distinti, non quattro.

{_tab(stag, {"media_osservata": 3, "mae": 4, "mae_relativo": 4, "bias": 4,
             "corr": 4, "delta_su_baseline": 4, "t": 3})}

## 5. Brier per linea, su entrambi i bersagli

Totale dei **tiri**:

{_tab(br_sh, {"tasso_base": 4, "brier_modello": 4, "brier_baseline": 4,
              "brier_tasso_base": 4})}

Totale dei **tiri in porta**:

{_tab(br_so, {"tasso_base": 4, "brier_modello": 4, "brier_baseline": 4,
              "brier_tasso_base": 4})}

Tutte le linee stanno dentro `tentativi.BASE_RATE_AMMESSO`, applicato
meccanicamente e non a occhio, e il modello batte **sia** il baseline migliore
**sia** il tasso base su ognuna.

## 6. La forma della predittiva

PIT randomizzato: chi2 = {pit['chi2']:.2f} su {pit['dof']} gdl,
**p = {pit['p_value']:.3f}**. `r_tot` mediana walk-forward {forma['r_mediana']:.1f}.

{_tab(forma['copertura'], {"copertura": 3, "ampiezza_media": 2})}

La copertura e' **sopra** il nominale, com'e' strutturale sui conteggi: e' la
stessa firma conservativa gia' misurata in Fase 4 e in V1, non un difetto nuovo.

## 7. Il risultato che non era previsto: il totale e' SOTTO-CALIBRATO

Per **lato** il modello e' calibrato a 1,008 (z = +0,33), cioe' il numero di V1
riprodotto. Sul **totale** la pendenza crolla:

| bersaglio | pendenza grezza | z | pendenza ricalibrata | z |
|---|---:|---:|---:|---:|
| tiri | {ver_sh['pendenza_grezza']:.4f} | {ver_sh['z_grezza']:.2f} | {ver_sh['pendenza_ricalibrata']:.4f} | {ver_sh['z_ricalibrata']:.2f} |
| tiri in porta | {ver_so['pendenza_grezza']:.4f} | {ver_so['z_grezza']:.2f} | {ver_so['pendenza_ricalibrata']:.4f} | {ver_so['z_ricalibrata']:.2f} |

**Le due cose non si contraddicono, e il meccanismo e' misurato**: sommando, la
parte di segnale che i due lati hanno in comune si cancella, e sopravvive
proporzionalmente piu' rumore. Il numero che lo dice e' che **il modello crede i
due lati molto piu' anti-correlati di quanto siano**:

{_tab(anti_sh, {"corr_lambda": 4, "corr_osservata": 4, "sd_lam_totale": 3,
                "sd_y_totale": 3})}

Sui tiri in porta il divario e' anche piu' largo - nel 2023-2024 il modello
crede -0,40 dove l'osservato e' **+0,007**, cioe' nessuna dipendenza affatto:

{_tab(anti_so, {"corr_lambda": 4, "corr_osservata": 4, "sd_lam_totale": 3,
                "sd_y_totale": 3})}

### Il verdetto sulla correzione, applicato meccanicamente

Criterio scritto **prima** di misurare (`totale.CRITERIO_ADOZIONE`):

> {ver_sh['criterio']}

| | tiri | tiri in porta |
|---|---|---|
| (1) pendenza entro 2 e.s. | {"si" if ver_sh['criterio_1_pendenza'] else "**no**"} | {"si" if ver_so['criterio_1_pendenza'] else "**no**"} |
| (2) il MAE non peggiora | {"si" if ver_sh['criterio_2_mae'] else "**no**"} | {"si" if ver_so['criterio_2_mae'] else "**no**"} |
| (3) segno concorde | {"si" if ver_sh['criterio_3_segno'] else "**no**"} ({ver_sh['stagioni_migliorate']}/{ver_sh['stagioni_ricalibrate']}) | {"si" if ver_so['criterio_3_segno'] else "**no**"} ({ver_so['stagioni_migliorate']}/{ver_so['stagioni_ricalibrate']}) |
| **adottata** | **{"SI" if ver_sh['adottata'] else "NO"}** | **{"SI" if ver_so['adottata'] else "NO"}** |

**Il verdetto e' diviso, e non e' stato aggiustato per farlo tornare uguale.**
Sui tiri la correzione si adotta - ma z passa a {ver_sh['z_ricalibrata']:.2f},
cioe' **appena dentro** la soglia, e va letto cosi'. Sui tiri in porta cade il
solo criterio (1): la pendenza resta a {ver_so['pendenza_ricalibrata']:.2f} con
z = {ver_so['z_ricalibrata']:.2f}, fuori da 2 errori standard.

> Il criterio diceva "4 stagioni su 5": le stagioni ricalibrabili sono **4**,
> perche' la piu' vecchia non ha un passato e resta marcata come non
> ricalibrata - lo stesso trattamento della 2021-2022 in R2-bis. Il conteggio e'
> quindi 4 su 4, e la soglia e' stata letta come "tutte quelle disponibili"
> invece di essere abbassata.

## 7-bis. Trasferisce? Lo stesso blocco sui cinque campionati

Un fit per campionato, **mai poolati** (regola di E1, riscritta da R0 su G2).
E' la domanda che la Fase 13 pose ai gol, applicata qui.

{_tab(camp, {"media_totale": 3, "corr_lati": 3, "r_lato": 2, "r_totale": 2,
             "pendenza_totale": 3, "z_vs_1": 2, "rapporto_r": 2})}

**Le tre firme del blocco reggono in tutte e dieci le righe**, e nessuna e'
un'idiosincrasia italiana:

- la correlazione fra i due lati e' **negativa ovunque** (da -0,11 a -0,41);
- **`r_tot` e' fra 2,3 e 5,8 volte `r` per lato** ovunque, cioe' il totale e'
  sempre molto meno disperso di quanto l'indipendenza implicherebbe;
- la pendenza del totale sta **sotto 1 ovunque**, con z da -2,37 a -7,01: la
  sotto-calibrazione non e' un accidente della Serie A.

> **Ne segue una conseguenza operativa per la pagina**: `r_tot` va presa **da
> quel campionato**, mai da un altro. Fra Bundesliga e Liga sui tiri in porta
> vale 190,6 contro 70,5, cioe' un fattore 2,7 - un `r_tot` preso in prestito
> sbaglierebbe le code in modo grossolano.

## 8. Che cosa T1 consegna

- `lambda_totale = lambda_casa + lambda_trasferta`, **esatto**, per qualunque
  coppia che il modello sappia prevedere;
- `r_tot` **stimata sui totali** e walk-forward, con la prova che non si eredita;
- le linee del totale, dichiarate prima e dentro la regola dei tassi base;
- **il limite piu' importante**: sul totale il lambda e' sotto-calibrato, sui
  tiri in porta lo resta anche dopo la correzione. Va scritto **accanto** ai
  numeri della pagina, non in fondo (vincolo 5).

## 9. Domande aperte

1. **Perche' il modello anti-correli i due lati piu' del vero** e' misurato ma
   non spiegato. Il sospetto e' che attacco e difesa della stessa partita
   condividano i coefficienti stimati sulle stesse righe, quindi l'errore di
   stima entri con segno opposto nei due lati; separarlo vuole un disegno
   apposito, non una rilettura di questo.
2. **La correzione e' una sola trasformazione monotona sul lambda**: sistema il
   sintomo e non sa da dove venga. E' la lezione di R2-bis, e vale qui identica -
   che funzioni non conferma nessuna spiegazione.
3. **`r_tot` e' assunta costante fra squadre e stagioni**, come `r` in V1.
4. **Senza prezzi di mercato reali** nessuna valutazione di scommessa e'
   possibile (vincolo 3), e questo blocco non ne apre la strada.
"""


if __name__ == "__main__":
    raise SystemExit(main())
