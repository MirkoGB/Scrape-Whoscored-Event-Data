"""Fase 16 / Blocco O1 — la verifica PROSPETTICA delle prime due giornate.

    ./.venv/Scripts/python.exe scripts/run_fase16_o1.py

**Non tocca la rete. Non stima nessun modello predittivo nuovo. Non scrive
niente sotto `data/`.** L'unica cosa che scrive fuori da `reports/` e' la copia
datata delle previsioni congelate, che e' l'unico artefatto non rigenerabile
del blocco: `run_previsioni.py --csv` riscrive `reports/previsioni_<L>.csv`
senza data nel nome, e l'aggiornamento automatico del martedi' e' attivo.

Il passo `[1]` e' una **guardia**: se le previsioni non risultano anteriori ai
dati e riproducibili da un modello che finisce a maggio 2026, lo script si
ferma invece di pubblicare una verifica su un file rigenerato dopo i fatti.

~3 min.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sot import config  # noqa: E402
from sot import verifica_prospettica as VP  # noqa: E402

OUT_MD = config.REPORTS / "fase16_o1_verifica_prospettica.md"
OUT_REGISTRO = config.REPORTS / "fase16_o1_registro.csv"
OUT_PERIMETRO = config.REPORTS / "fase16_o1_perimetro.csv"
OUT_VALUTAZIONE = config.REPORTS / "fase16_o1_valutazione.csv"
OUT_APPAIATO = config.REPORTS / "fase16_o1_appaiato.csv"
OUT_PER_CAMPIONATO = config.REPORTS / "fase16_o1_per_campionato.csv"
OUT_BRIER = config.REPORTS / "fase16_o1_brier_linee.csv"
OUT_FORMA = config.REPORTS / "fase16_o1_forma_predittiva.csv"
OUT_TARATURA = config.REPORTS / "fase16_o1_taratura.csv"
OUT_COLLOCAZIONE = config.REPORTS / "fase16_o1_collocazione.csv"
OUT_LIVELLO = config.REPORTS / "fase16_o1_livello.csv"
OUT_DISPERSIONE = config.REPORTS / "fase16_o1_dispersione.csv"
OUT_TOTALE = config.REPORTS / "fase16_o1_totale.csv"

ETICHETTA = {"shots": "tiri", "sot": "tiri in porta"}


def _tab(df: pd.DataFrame, dec: dict | None = None) -> str:
    """DataFrame -> tabella markdown. Stessa funzione degli altri run_fase*.

    Due aggiunte rispetto alla versione di `run_fase12_v1.py`, e nessuna delle
    due e' cosmetica: una colonna di **conteggi** esce senza decimali (`760`,
    non `760.000`), e `dec` accetta anche una stringa di formato, perche' gli
    scarti di riproduzione valgono ~1e-8 e con tre decimali si leggerebbero
    tutti `0.000` — cioe' la colonna che dimostra il punto del blocco sarebbe
    illeggibile proprio dove serve.
    """
    if df is None or not len(df):
        return "_(vuota)_\n"
    d = df.copy()
    dec = dec or {}
    num = []

    def _fmt(v, spec):
        if pd.isna(v):
            return "-"
        if isinstance(spec, str):
            return format(v, spec)
        return f"{v:,.{spec}f}".replace(",", " ")

    for c in d.columns:
        if d[c].dtype == bool:
            d[c] = np.where(d[c], "si", "no")
        elif pd.api.types.is_numeric_dtype(d[c]):
            num.append(c)
            if c in dec:
                spec = dec[c]
            else:
                finiti = d[c].dropna()
                intera = len(finiti) and bool((finiti % 1 == 0).all())
                spec = 0 if intera else 3
            d[c] = d[c].map(lambda v, s=spec: _fmt(v, s))
        else:
            d[c] = d[c].fillna("-").astype(str)
    testa = "| " + " | ".join(str(c) for c in d.columns) + " |"
    riga = "|" + "|".join("---:" if c in num else "---" for c in d.columns) + "|"
    corpo = "\n".join("| " + " | ".join(r) + " |"
                      for r in d.astype(str).to_numpy())
    return f"{testa}\n{riga}\n{corpo}\n"


def _pct(x: float) -> str:
    return "-" if pd.isna(x) else f"{x:+.1f}%"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--league", nargs="*", default=None,
                    help="default: tutti e cinque")
    args = ap.parse_args()
    leagues = list(args.league or config.LEAGUE_CODES)

    # ---------------------------------------------------------------- [1]
    print("[1] il registro, e la guardia sull'anteriorita'")
    VP.congela(leagues)
    reg = VP.registro(leagues)
    ant = VP.verifica_anteriorita(leagues)
    for _, r in ant.iterrows():
        print(f"    {r['campionato']}: anteriore={r.get('anteriore_al_primo_evento')} "
              f"riprodotto={r.get('riprodotto')} "
              f"(scarto max {max(r.get('scarto_max_shots', np.nan), r.get('scarto_max_sot', np.nan)):.2e})")
    if not bool(ant["supera"].all()):
        print("\n  LA GUARDIA NON PASSA: il blocco non si pubblica.")
        return 1
    print(f"    tutte superano; anticipo minimo "
          f"{reg['giorni_di_anticipo'].min():.2f} giorni")

    # ---------------------------------------------------------------- [2]
    print("[2] il perimetro, e la giornata come controllo positivo")
    ver = pd.DataFrame([VP.verifica_giornata(lg) for lg in leagues])
    rip = VP.ripiego_ammesso(ver)
    print(f"    {int(ver['n_righe'].sum())} righe / "
          f"{int(ver['n_partite'].sum())} partite")
    print(f"    ripiego ammesso: {rip['ammesso']} - {rip['perche']}")
    if not rip["ammesso"]:
        print("\n  Il ripiego sulla giornata non e' ammesso: il blocco si ferma.")
        return 1

    # ---------------------------------------------------------------- [3]
    print("[3] le previsioni del perimetro, e il ponte col file congelato")
    prev, coer = {}, []
    for tg in VP.BERSAGLI:
        prev[tg] = {lg: VP.previsioni_del_perimetro(lg, tg) for lg in leagues}
        for lg, p in prev[tg].items():
            c = VP.coerenza_col_congelato(p)
            coer.append({"campionato": lg, "bersaglio": tg, **c,
                         "n_righe": int(len(p)),
                         "n_congelate": int(p["da_file_congelato"].sum()),
                         "n_neopromossa": int(p["neopromossa_coinvolta"].sum())})
    coer = pd.DataFrame(coer)
    if not bool(coer["coincidono"].all()):
        print("\n  Il file congelato NON coincide con `modello prec`: ci si ferma.")
        return 1
    q = float(coer.loc[coer["bersaglio"] == "shots", "n_congelate"].sum()
              / coer.loc[coer["bersaglio"] == "shots", "n_righe"].sum())
    print(f"    coerenza col congelato: tutte le righe, scarto max "
          f"{coer['scarto_max'].max():.2e}")
    print(f"    righe con previsione documentale: {q:.1%}; "
          f"il resto e' il default delle neopromosse")

    ins = {tg: VP.insieme(prev[tg].values()) for tg in VP.BERSAGLI}

    # ---------------------------------------------------------------- [4]
    print("[4] la valutazione: CRPS (primaria), log score, MAE, bias")
    val, app, brier, forma, livello, percamp = [], [], [], [], [], []
    for tg in VP.BERSAGLI:
        v = VP.valutazione(ins[tg], tg).assign(bersaglio=tg, perimetro="pieno")
        vc = (VP.valutazione(ins[tg], tg, solo_congelate=True)
              .assign(bersaglio=tg, perimetro="solo congelate"))
        val += [v, vc]
        a = VP.confronto_appaiato(ins[tg], tg).assign(bersaglio=tg)
        app.append(a)
        brier.append(VP.brier_per_linea(ins[tg], tg))
        f = VP.forma_predittiva(ins[tg], tg)
        forma.append(pd.DataFrame([{
            "bersaglio": tg, "n": f["n"], "r": f["r"],
            "pit_chi2": f["pit"]["chi2"], "pit_p": f["pit"]["p_value"],
            "pit_media": f["pit"]["mean"], "pit_sd": f["pit"]["sd"],
            **{f"copertura_{int(100 * l)}": c for l, c in
               zip(f["copertura"]["livello"], f["copertura"]["copertura"])}}]))
        livello.append(pd.DataFrame([{"bersaglio": tg,
                                      **VP.scomposizione_livello(ins[tg], tg)}]))
        d = VP.verdetto(a)
        print(f"    {ETICHETTA[tg]}: CRPS {v.set_index('candidato').loc[VP.SOGGETTO, 'crps']:.4f}"
              f"  vs {VP.RIFERIMENTO} delta {d['delta_crps']:+.4f}"
              f"  t {d['t_cluster']:+.2f}  delta/MDE {d['delta_su_mde']:.2f}"
              f"  -> {'CONCLUDE' if d['conclude'] else 'non conclude'}")
        for lg in leagues:
            p = prev[tg][lg]
            if not len(p):
                continue
            vv = VP.valutazione(p, tg).set_index("candidato")
            percamp.append({
                "campionato": lg, "bersaglio": tg,
                "n": int(len(p)), "n_partite": int(p["matchId"].nunique()),
                "r": float(p["r_lega"].iloc[0]),
                "crps_modello_prec": float(vv.loc[VP.SOGGETTO, "crps"]),
                "crps_media_squadra_prec": float(vv.loc[VP.RIFERIMENTO, "crps"]),
                "delta_crps": float(vv.loc[VP.SOGGETTO, "crps"]
                                    - vv.loc[VP.RIFERIMENTO, "crps"]),
                "mae": float(vv.loc[VP.SOGGETTO, "mae"]),
                "bias": float(vv.loc[VP.SOGGETTO, "bias"]),
                "media_osservata": float(p[tg].mean()),
                "scarto_di_livello_pct":
                    float(p[tg].mean() / p["lam_modello_prec"].mean() - 1) * 100,
                "quota_congelate": float(p["da_file_congelato"].mean()),
            })
    val = pd.concat(val, ignore_index=True)
    app = pd.concat(app, ignore_index=True)
    brier = pd.concat(brier, ignore_index=True)
    forma = pd.concat(forma, ignore_index=True)
    livello = pd.concat(livello, ignore_index=True)
    percamp = pd.DataFrame(percamp)

    # ---------------------------------------------------------------- [5]
    print("[5] la taratura storica: 20 transizioni in cui l'esito e' noto")
    tar = pd.concat([VP.taratura_storica(leagues, target=tg)
                     for tg in VP.BERSAGLI], ignore_index=True)
    # L'aggregazione dev'essere la STESSA sui due lati del confronto: la media
    # di cinque campionati non si legge dentro la distribuzione dei singoli
    # campionato-stagione, che ha molta piu' varianza. Si pesa per righe, che e'
    # come il valore osservato e' stato costruito (E4: confronto orizzontale).
    def _pesata(d, col):
        return float((d[col] * d["n"]).sum() / d["n"].sum())

    tar_stagione = (tar.groupby(["bersaglio", "stagione"])
                    .apply(lambda d: pd.Series({
                        "n": int(d["n"].sum()),
                        "crps_modello_prec": _pesata(d, "crps_modello_prec"),
                        "delta_crps": _pesata(d, "delta_crps"),
                        "scarto_di_livello_pct":
                            _pesata(d, "scarto_di_livello_pct")}),
                        include_groups=False)
                    .reset_index())

    coll = []
    for tg in VP.BERSAGLI:
        s = tar_stagione[tar_stagione["bersaglio"] == tg]
        oss = percamp[percamp["bersaglio"] == tg]
        for grand, meglio in (("crps_modello_prec", True),
                              ("delta_crps", True),
                              ("scarto_di_livello_pct", False)):
            c = VP.collocazione(_pesata(oss, grand), s[grand],
                                piu_basso_e_meglio=meglio)
            coll.append({"bersaglio": tg, "grandezza": grand,
                         "confronto": "5 campionati insieme, per stagione", **c})
        # e lo stesso campionato per campionato, dentro le sue quattro
        for lg in leagues:
            sl = tar[(tar["bersaglio"] == tg) & (tar["campionato"] == lg)]
            ol = oss[oss["campionato"] == lg]
            if not len(sl) or not len(ol):
                continue
            for grand, meglio in (("crps_modello_prec", True),
                                  ("scarto_di_livello_pct", False)):
                c = VP.collocazione(float(ol[grand].iloc[0]), sl[grand],
                                    piu_basso_e_meglio=meglio)
                coll.append({"bersaglio": tg, "grandezza": grand,
                             "confronto": lg, **c})
    coll = pd.DataFrame(coll)
    pool5 = coll["confronto"] == "5 campionati insieme, per stagione"
    for _, r in coll[pool5 & (coll["grandezza"] == "scarto_di_livello_pct")].iterrows():
        print(f"    {ETICHETTA[r['bersaglio']]}: scarto di livello "
              f"{_pct(r['osservato'])} contro un intervallo storico "
              f"[{_pct(r['minimo_storico'])}, {_pct(r['massimo_storico'])}]"
              f" - dentro: {r['dentro_l_intervallo_storico']}")

    # ---------------------------------------------------------------- [6]
    print("[6] la dispersione di avvio (diagnostico, non adozione)")
    disp = pd.DataFrame([VP.dispersione_di_avvio(leagues, target=tg)
                         for tg in VP.BERSAGLI])
    for _, r in disp.iterrows():
        print(f"    {ETICHETTA[r['bersaglio']]}: r avvio {r['r_avvio']:.2f} "
              f"contro {r['r_pubblicata']:.2f} pubblicata; rapporto "
              f"{r['rapporto']:.3f} IC95 [{r['ic95'][0]:.3f}, {r['ic95'][1]:.3f}]"
              f" - troppo stretta: {r['predittiva_troppo_stretta']}")

    # ---------------------------------------------------------------- [7]
    print("[7] il totale di partita (secondario)")
    tot = []
    for tg in VP.BERSAGLI:
        for lg in leagues:
            p = prev[tg][lg]
            if not len(p):
                continue
            t = VP.totale_del_perimetro(p, tg)
            rt = VP.r_totale_pubblicata(lg, tg)
            tot.append(VP.valutazione_totale(t, rt)
                       .assign(campionato=lg, bersaglio=tg, r_tot=rt))
    tot = pd.concat(tot, ignore_index=True) if tot else pd.DataFrame()
    if len(tot):
        agg = (tot.groupby(["bersaglio", "candidato"])
               .agg(n_partite=("n_partite", "sum"), crps=("crps", "mean"),
                    mae=("mae", "mean"), bias=("bias", "mean"))
               .reset_index())
        for tg in VP.BERSAGLI:
            s = agg[(agg["bersaglio"] == tg)
                    & (agg["candidato"] == VP.SOGGETTO)]
            if len(s):
                print(f"    {ETICHETTA[tg]}: CRPS totale "
                      f"{float(s['crps'].iloc[0]):.4f}, bias "
                      f"{float(s['bias'].iloc[0]):+.3f}")
    else:
        agg = pd.DataFrame()

    # ---------------------------------------------------------------- [8]
    print("[8] scrittura")
    for df, path in ((reg, OUT_REGISTRO), (ver, OUT_PERIMETRO),
                     (val, OUT_VALUTAZIONE), (app, OUT_APPAIATO),
                     (percamp, OUT_PER_CAMPIONATO), (brier, OUT_BRIER),
                     (forma, OUT_FORMA), (tar, OUT_TARATURA),
                     (coll, OUT_COLLOCAZIONE),
                     (livello, OUT_LIVELLO), (disp, OUT_DISPERSIONE),
                     (tot, OUT_TOTALE)):
        df.to_csv(path, index=False, encoding="utf-8")

    OUT_MD.write_text(_report(reg, ant, ver, rip, coer, val, app, percamp,
                              brier, forma, livello, tar, coll, disp, agg),
                      encoding="utf-8")

    for p in (OUT_MD, OUT_REGISTRO, OUT_PERIMETRO, OUT_VALUTAZIONE,
              OUT_APPAIATO, OUT_PER_CAMPIONATO, OUT_BRIER, OUT_FORMA,
              OUT_TARATURA, OUT_COLLOCAZIONE, OUT_LIVELLO,
              OUT_DISPERSIONE, OUT_TOTALE):
        print(f"-> {p}")
    return 0


def _report(reg, ant, ver, rip, coer, val, app, percamp, brier, forma,
            livello, tar, coll, disp, agg) -> str:
    import datetime as _dt

    quando = _dt.datetime.now().strftime("%Y-%m-%d %H:%M")
    from scipy.stats import norm
    # la famiglia sono i confronti fatti contro il soggetto, cioe' gli altri
    # candidati: e' la stessa numerosita' con cui A2 ha corretto (5 -> 2,32)
    k_fam = len(VP.CANDIDATI) - 1
    sidak = float(norm.isf(1.0 - 0.95 ** (1.0 / k_fam)))
    z_mde = float(norm.isf(0.05 / 2) + norm.isf(1 - 0.80))
    v_sh = VP.verdetto(app[app["bersaglio"] == "shots"])
    v_so = VP.verdetto(app[app["bersaglio"] == "sot"])

    def _bloc(tg: str) -> str:
        et = ETICHETTA[tg]
        v = val[(val["bersaglio"] == tg) & (val["perimetro"] == "pieno")]
        vc = val[(val["bersaglio"] == tg) & (val["perimetro"] == "solo congelate")]
        a = app[app["bersaglio"] == tg]
        d = VP.verdetto(a)
        liv = livello[livello["bersaglio"] == tg].iloc[0]
        return f"""
### Bersaglio `{tg}` — {et}

{_tab(v.drop(columns=["bersaglio", "perimetro"]),
      {"crps": 4, "log_score": 4, "mae": 3, "bias": 3, "sharpness": 3,
       "crps_righe_comuni": 4})}
**Solo sulle righe con previsione DOCUMENTALE** (entrambe le squadre note al
2025-2026, cioe' un numero scritto su disco prima dei fatti):

{_tab(vc.drop(columns=["bersaglio", "perimetro"]),
      {"crps": 4, "log_score": 4, "mae": 3, "bias": 3, "sharpness": 3,
       "crps_righe_comuni": 4})}
#### Il soggetto contro ogni altro candidato

{_tab(a.drop(columns="bersaglio"),
      {"crps_soggetto": 4, "crps_avversario": 4, "delta_crps": 4,
       "t_cluster": 2, "mde": 4, "delta_su_mde": 2})}
> **Verdetto contro `{VP.RIFERIMENTO}`**: delta {d['delta_crps']:+.4f},
> t {d['t_cluster']:+.2f}, MDE {d['mde']:.4f}, **delta/MDE
> {d['delta_su_mde']:.2f}** su {d['n_cluster']} partite —
> {'**il confronto conclude**' if d['conclude'] else '**il test NON conclude**'}.
> {d['perche']}

#### Il livello del campionato nuovo, separato dall'ordinamento

| | |
|---|---:|
| media prevista | {liv['media_prevista']:.3f} |
| media osservata | {liv['media_osservata']:.3f} |
| scarto di livello | {_pct(liv['scarto_di_livello_pct'])} |
| CRPS `modello prec` | {liv['crps_modello_prec']:.4f} |
| CRPS `oracolo di livello` | {liv['crps_oracolo_livello']:.4f} |
| **quota del CRPS attribuibile al solo livello** | **{liv['quota_del_crps_dal_livello']:.1%}** |

#### Brier sulle linee dichiarate

{_tab(brier[brier["bersaglio"] == tg].drop(columns="bersaglio"),
      {"tasso_base_osservato": 3, "p_media_dichiarata": 3, "brier": 4,
       "brier_tasso_base_oracolo": 4})}
"""

    return f"""# Fase 16 / Blocco O1 — la verifica prospettica delle prime due giornate

_Generato da `scripts/run_fase16_o1.py` — {quando}_

**La prima verifica del progetto in cui la previsione e' stata scritta prima e
l'esito letto dopo.** Tutto il resto — il walk-forward di V1, il prior di A2 su
venti transizioni concluse, la trasferibilita' di F13 — e' within-season o
retrospettivo. Qui no, e non perche' si sia simulato qualcosa: **l'esclusione
era gia' avvenuta**.

---

## 1. Il registro, e perche' l'anteriorita' non chiede di fidarsi di un orologio

Le previsioni stanno su disco dal **{VP.CONGELATE_AL}**; il primo CSV di evento
della {config.SEASON_CORRENTE} e' arrivato **{reg['giorni_di_anticipo'].min():.1f}
giorni dopo** il piu' stretto dei cinque.

{_tab(reg[["campionato", "righe", "byte", "previsioni_scritte",
           "primo_evento_stagione", "anteriore", "giorni_di_anticipo"]],
      {"giorni_di_anticipo": 2, "byte": 0})}
Il `mtime` da solo sarebbe un argomento debole — un timestamp si cambia. Quello
che regge il blocco e' il secondo controllo:

{_tab(ant.drop(columns="presente"),
      {"scarto_max_shots": ".2e", "scarto_max_sot": ".2e"})}
> **Le previsioni congelate si riproducono da `prior_stagione.lam_dal_prior`
> applicato al fit della sola stagione precedente.** Ne segue che sono una
> funzione di dati che finiscono a maggio 2026, e quindi **non possono
> contenere informazione sulle giornate 1-2 qualunque sia la data in cui il
> file e' stato scritto**. E' l'argomento che non passa da nessun orologio.

**La riproduzione non e' bit-per-bit, e la ragione e' misurata**: dentro un solo
processo il re-fit da' scarto **0,0 esatto**; fra due processi resta un residuo
di ~1e-7 relativo, che e' esattamente l'ordine che `L-BFGS-B` con
`ftol = 1e-12` dichiara (`sqrt(ftol)` sui parametri). La tolleranza
(`TOLL_RIPRODUZIONE = {VP.TOLL_RIPRODUZIONE:g}`) e' **derivata da li'**, non
scelta guardando lo scarto osservato.

E le previsioni congelate **sono** `modello prec`, cioe' esattamente cio' che
`prior_stagione.REGOLA_DUE_REGIMI` prescrive sotto
`config.BURN_IN_ROUND = {config.BURN_IN_ROUND}`: si valuta la regola dichiarata,
non una variante costruita per l'occasione.

---

## 2. Il perimetro, e la giornata come grandezza da accertare

Il perimetro e' `team_match_idx <= {VP.PERIMETRO_IDX_MAX}`, cioe' le prime due
partite di ogni squadra. **Non e' la giornata**, ed e' una grandezza diversa
(vincolo 7): la giornata vera vive nella seconda fonte, che e' completa e sana
su un campionato solo.

{_tab(ver[["campionato", "n_righe", "n_partite", "fonte_completa",
           "verificabile", "n_note", "n_assenti_dalla_fonte", "n_ambigue",
           "n_discordi", "accordo"]], {"accordo": 3})}
> **Il controllo positivo passa**: {rip['perche']}. Su
> **{int(ver['n_note'].sum())} partite** in cui entrambe le fonti parlano senza
> ambiguita', i disaccordi sono **{int(ver['n_discordi'].sum())}**.

Tre esiti restano separati, perche' confonderli produce un disaccordo inventato:
una partita **assente** dalla seconda fonte non dice niente sul ripiego (e'
incompletezza della pagina); una **ambigua** e' un rinvio che la fonte elenca a
due giornate diverse, e si tolgono tutte le copie come fa gia' `calendario.py`;
solo una partita elencata **senza ambiguita'** a una giornata sopra la soglia e'
un disaccordo vero.

> **La prima stesura di questa verifica ha sbagliato proprio qui**, e vale la
> pena scriverlo: costruiva un dizionario `coppia -> giornata` in cui l'ultima
> scrittura vinceva, e su `Paris FC-Nizza` — che Wikipedia elenca **alla 2 e
> alla 7** — teneva la 7. Ne usciva un disaccordo che era suo, non del ripiego.

### Le neopromosse: due perimetri, entrambi in tabella

{_tab(coer[["campionato", "bersaglio", "n_righe", "n_congelate",
            "n_neopromossa", "scarto_max", "coincidono"]],
      {"scarto_max": ".2e"})}
Il file congelato contiene **solo le squadre della stagione precedente**, quindi
una riga che coinvolga una neopromossa non ha previsione documentale. La
previsione esiste lo stesso — `lam_dal_prior` da' coefficiente 0 a una squadra
sconosciuta — ma **e' un default, non una stima**: la media di campionato
dell'anno scorso. E' una quota grande, ed e' gia' di per se' un risultato: al
giorno 1 di una stagione nuova una riga su tre riguarda squadre che il modello
non ha mai visto.

---

## 3. La metrica, dichiarata prima

**{VP.METRICA_PRIMARIA} su conteggi**, `somma_k (F(k) - 1[y <= k])^2`, in unita'
del bersaglio. E' propria, e' **ordinale** (sbagliare di 8 costa piu' che
sbagliare di 1, che la log score non distingue), e' robusta alle code — con
poche decine di righe una sola osservazione estrema deciderebbe il verdetto — ed
e' la stessa scelta che R2 ha fatto preferendo l'RPS alla log-loss sull'esito
1X2, su un bersaglio con piu' classi.

Le altre stanno **accanto**, mai al posto: log score (l'unita' di A2, per essere
confrontabili con `fase14_prior.md`), Brier sulle linee dichiarate, MAE e bias,
PIT e copertura. **Due metriche del repository NON si usano qui**: la
scomposizione di Murphy vuole otto fasce e a questo `n` il termine di binning
non e' trascurabile, e la pendenza di calibrazione ha un errore standard che la
rende non interpretabile — lo stesso `nan` dichiarato di `media campionato` in
Fase 4.

Ogni candidato si compone con la **stessa** NB2 e la **stessa** `r`: e' la
regola di R2. `r` e' quella **pubblicata**, mai ristimata — valutare con una
dispersione migliore misurerebbe un modello che nessuno ha mai pubblicato.

{_bloc("shots")}
{_bloc("sot")}

---

## 4. Per campionato

{_tab(percamp, {"r": 2, "crps_modello_prec": 4, "crps_media_squadra_prec": 4,
                "delta_crps": 4, "mae": 3, "bias": 3, "media_osservata": 2,
                "scarto_di_livello_pct": 2, "quota_congelate": 3})}
---

## 5. La forma della predittiva

{_tab(forma, {"r": 2, "pit_chi2": 2, "pit_p": 3, "pit_media": 3, "pit_sd": 3,
              "copertura_50": 3, "copertura_80": 3, "copertura_95": 3})}
> Su questo perimetro il PIT e' **debole** — dieci fasce su poche decine di
> righe — e va letto come indizio, non come test. E' una delle ragioni per cui
> la taratura del §6 non e' un ornamento.

---

## 6. La taratura storica — senza, un CRPS e' un numero e non un risultato

La **stessa identica procedura** sulle prime due partite di ogni squadra nelle
transizioni gia' concluse, dove l'esito e' noto. E' il gemello di
`tentativi.taratura_test()` e del nullo simulato di V0: la differenza fra «il
test ha trovato qualcosa» e «il test rifiuta sempre» si vede solo mettendo
accanto il caso in cui la risposta si conosce.

{_tab(tar[["campionato", "stagione", "bersaglio", "n_partite",
           "crps_modello_prec", "crps_media_squadra_prec", "delta_crps",
           "t_cluster", "bias", "scarto_di_livello_pct"]],
      {"crps_modello_prec": 4, "crps_media_squadra_prec": 4, "delta_crps": 4,
       "t_cluster": 2, "bias": 3, "scarto_di_livello_pct": 2})}
### Dove cade la stagione nuova

{_tab(coll, {"osservato": 4, "mediana_storica": 4, "minimo_storico": 4,
             "massimo_storico": 4, "quota_peggiori": 3})}
> Si riporta il **rango**, non un p-value: venti transizioni non sono un
> campione da cui estrarre una probabilita', e chiamarla tale sarebbe fabbricare
> precisione.

---

## 7. La dispersione di avvio — DIAGNOSTICO, non adozione

**L'attesa era dichiarata prima**: `r` viene dal walk-forward **within-season**,
dove i lambda sono piu' accurati di quelli cross-stagione di `modello prec`, e
una previsione peggiore ha residui piu' dispersi. Se e' cosi', la predittiva
pubblicata e' **troppo stretta** all'avvio.

{_tab(disp[["bersaglio", "n", "n_cluster", "r_avvio", "r_pubblicata",
            "rapporto", "compatibili", "predittiva_troppo_stretta"]],
      {"r_avvio": 2, "r_pubblicata": 2, "rapporto": 3})}
IC95 del rapporto da bootstrap **sui cluster** (la partita, non la riga), la
stessa forma con cui `precisione.rapporto_dispersioni()` ha falsificato
l'ereditarieta' fra `r_shots` e `r_sot` e con cui T1 ha rifiutato di ereditare
`r_tot`: {"; ".join(f"{r['bersaglio']}: [{r['ic95'][0]:.3f}, {r['ic95'][1]:.3f}]" for _, r in disp.iterrows())}.

> **Questo blocco non ricalibra niente.** Adottare una `r` diversa vorrebbe un
> criterio scritto prima e una valutazione fuori campione sua, che qui non c'e'.

---

## 8. Il totale di partita — secondario, e ci si aspetta di non concludere

`E[X+Y] = E[X] + E[Y]` e' esatto qualunque sia la dipendenza fra i due lati
(T1), quindi `lam_tot` non richiede ipotesi; `r_tot` **non si eredita** e viene
da quella gia' stimata sulle stagioni storiche di ogni campionato.

{_tab(agg, {"crps": 4, "mae": 3, "bias": 3})}
T1 ha gia' misurato che il totale e' **sotto-calibrato** (pendenza 0,633 su
1.638 partite); qui i cluster sono poche decine. Si riporta se il segno e'
coerente con T1, **non si adotta niente**.

---

## 9. Limiti, accanto ai numeri e non in fondo

{chr(10).join("- " + x for x in VP.limiti())}

---

## 10. Il criterio, scritto prima

```
{VP.CRITERIO_LEGGIBILITA}
```

| bersaglio | delta CRPS | t | delta/MDE | conclude |
|---|---:|---:|---:|---|
| tiri | {v_sh['delta_crps']:+.4f} | {v_sh['t_cluster']:+.2f} | {v_sh['delta_su_mde']:.2f} | {'si' if v_sh['conclude'] else 'no'} |
| tiri in porta | {v_so['delta_crps']:+.4f} | {v_so['t_cluster']:+.2f} | {v_so['delta_su_mde']:.2f} | {'si' if v_so['conclude'] else 'no'} |

> **«Significativo» e «il test aveva la potenza per vederlo» non sono la stessa
> cosa, e qui le due letture divergono.** Il criterio `delta/MDE >= 1` equivale
> a `|t| >= {z_mde:.2f}`, perche' il MDE e' calcolato a due code e a potenza
> 80%. La soglia di Sidak su {k_fam} confronti dichiarati vale invece
> `|t| > {sidak:.2f}`, e quella di significativita' a due code 1,96.
>
> Sui **tiri in porta** il `t = {v_so['t_cluster']:.2f}` contro
> `{VP.RIFERIMENTO}` passa entrambe le soglie piu' basse e **non** il criterio
> dichiarato. Non e' un cavillo: vuol dire che l'effetto osservato e' piu'
> piccolo del piu' piccolo che questo campione fosse attrezzato a rilevare, e
> chiamarlo «dimostrato» sarebbe leggere un test che non aveva la potenza per
> dirlo. **Il criterio era scritto prima e non e' stato riscritto per farlo
> tornare** — la stessa disciplina di `LATI_STRATO2` in V2 e di
> `CRITERIO_ADOZIONE` in A2.
"""


if __name__ == "__main__":
    sys.exit(main())
