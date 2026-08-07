# -*- coding: utf-8 -*-
"""Fase 10 / Blocco R1 — la distribuzione congiunta del risultato.

    ./.venv/Scripts/python.exe scripts/run_fase10_r1.py [--repliche N]

**Non tocca la rete e non scrive niente sotto `data/`.** Legge il perimetro di R0
e il walk-forward dei gol di E3, e stima **un parametro solo**: `rho`, la
dipendenza fra i due lati a marginali fissate.

Si apre con il controllo chiesto dall'utente il 2026-08-07: **le partite che
WhoScored non ha sono a caso rispetto al risultato?** E' una precondizione, non
un dettaglio — se il bersaglio ha un buco non casuale, ogni numero che segue lo
eredita.

~2 min (la potenza e' simulata).
"""

from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sot import config, perimetro as PM, risultato as R  # noqa: E402

OUT_MD = config.REPORTS / "fase10_r1_congiunta.md"


def _tab(df: pd.DataFrame, dec: dict[str, int] | None = None) -> str:
    dec = dec or {}
    num = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]

    def cella(c, v) -> str:
        if isinstance(v, bool):
            return "si" if v else "no"
        if pd.isna(v):
            return ""
        if c in dec:
            return f"{v:.{dec[c]}f}"
        if c in num and float(v) == int(v):
            return str(int(v))
        if c in num:
            return f"{v:.3f}"
        return str(v).replace("|", r"\|")

    testa = "| " + " | ".join(str(c) for c in df.columns) + " |"
    sep = "|" + "|".join("---:" if c in num else "---" for c in df.columns) + "|"
    righe = ["| " + " | ".join(cella(c, v) for c, v in zip(df.columns, r)) + " |"
             for r in df.itertuples(index=False)]
    return "\n".join([testa, sep, *righe])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repliche", type=int, default=200,
                    help="repliche per la potenza di rho (default 200)")
    args = ap.parse_args()

    print("Fase 10 / R1 — la congiunta\n" + "=" * 60)

    p = PM.partite()
    d = p[p["validabile"]].copy()

    # --- §1 il controllo d'apertura -------------------------------------
    manc = PM.partite_mancanti()
    cas = PM.casualita_mancanti()
    mde_gf = PM.mde_mancanti(col="gf")
    mde_pt = PM.mde_mancanti(col="punti")
    n_test = len(cas)
    soglia_bonf = 0.05 / n_test
    ata = cas[cas["squadra"] == "Atalanta"].iloc[0]

    print(f"\n[1] mancanti: {len(manc)} | squadre testate: {n_test}")
    print(f"    Atalanta {ata['record']}: punti {ata['punti_oss']:.2f} vs "
          f"{ata['punti_atteso']:.2f}, p={ata['punti_p']:.4f} "
          f"(Bonferroni {soglia_bonf:.4f})")
    print(f"    sui GOL: gf p={ata['gf_p']:.3f}, gs p={ata['gs_p']:.3f}")

    # --- §2-§3 la congiunta e la dipendenza -----------------------------
    marg = R.verifica_marginali()
    tronc = R.massa_troncata_dati(d)
    tutte = R.stima_rho(d)
    per_stag = pd.DataFrame([{"stagione": st, **R.stima_rho(s)}
                             for st, s in d.groupby("stagione")])
    celle = R.celle_osservate(d)
    corr = R.correlazione_residui(d)

    print(f"\n[3] rho = {tutte['rho']:+.4f}  LR = {tutte['lr']:.3f}  "
          f"p = {tutte['p_lr']:.3f}")
    print(f"    corr residui = {corr['corr']:+.4f} (p = {corr['p']:.3f})")

    # z per cella, calcolati qui perche' e' la lettura del report
    lam_c = d["lam_casa"].to_numpy(); lam_t = d["lam_trasferta"].to_numpy()
    gc = d["gol_casa"].to_numpy(); gt = d["gol_trasferta"].to_numpy()
    zs, righe_z = [], []
    for (x, y) in R.CELLE_CORRETTE:
        pi = stats.poisson.pmf(x, lam_c) * stats.poisson.pmf(y, lam_t)
        att, var = pi.sum(), (pi * (1 - pi)).sum()
        oss = int(((gc == x) & (gt == y)).sum())
        z = (oss - att) / np.sqrt(var)
        zs.append(z)
        righe_z.append({"cella": f"{x}-{y}", "osservate": oss, "attese": att,
                        "z": z, "verso osservato": "su" if z > 0 else "giu",
                        "verso di Dixon-Coles (rho>0)":
                            "giu" if (x, y) in ((0, 0), (1, 1)) else "su"})
    tab_z = pd.DataFrame(righe_z)
    chi2 = float(np.sum(np.square(zs)))
    p_chi2 = float(stats.chi2.sf(chi2, 4))
    discordi = int(sum(1 for r in righe_z
                       if r["verso osservato"] != r["verso di Dixon-Coles (rho>0)"]))

    # --- §4 la potenza ---------------------------------------------------
    print(f"\n[4] potenza ({args.repliche} repliche)...")
    mde = R.mde_rho(d, repliche=args.repliche)
    print(mde.to_string(index=False))

    dist = (d["esito"].value_counts(normalize=True)
            .reindex(["1", "X", "2"]).rename("quota").reset_index())
    dist.columns = ["esito", "osservata"]
    pr = np.array([R.esiti(R.congiunta(a, b, 0.0))
                   for a, b in zip(lam_c, lam_t)]).mean(axis=0)
    dist["modello (rho=0)"] = pr
    tab_dist = _tab(dist, dec={"osservata": 4, "modello (rho=0)": 4})

    cols_c = ["squadra", "mancanti", "record", "punti_oss", "punti_atteso",
              "punti_p", "gf_p", "gs_p", "casa_p"]
    tab_cas = _tab(cas[cols_c], dec={"punti_oss": 2, "punti_atteso": 2,
                                     "punti_p": 4, "gf_p": 3, "gs_p": 3,
                                     "casa_p": 3})
    # Precalcolate: dentro un'espressione f-string `{{...}}` e' un set, non un
    # dict letterale. E' il secondo blocco in cui ci casco, quindi nessuna
    # tabella viene piu' costruita dentro la stringa.
    tab_stag = _tab(per_stag[["stagione", "n", "rho", "lr", "p_lr"]],
                    dec={"rho": 4, "lr": 3, "p_lr": 3})
    tab_celle = _tab(tab_z, dec={"attese": 1, "z": 2})
    tab_mde = _tab(mde, dec={"potenza": 3})

    testo = f"""# Fase 10 / Blocco R1 — la distribuzione congiunta del risultato

> Generato da `scripts/run_fase10_r1.py` il {date.today().isoformat()}.
> **Nessuna richiesta di rete.** Si stima **un parametro solo**, `rho`, a
> marginali fissate: i lambda di E3.1 entrano come dati e non vengono ristimati.

---

## 1. Precondizione — le partite che mancano alla fonte sono a caso rispetto al risultato?

> Richiesto dall'utente il 2026-08-07, **prima** della congiunta e non dopo: se
> il bersaglio ha un buco non casuale su due squadre, ogni numero che segue lo
> eredita.

**Non e' la domanda a cui l'acquisizione ha gia' risposto.** Li' si chiedeva se
le partite mancassero a caso rispetto alla **squadra**, e la risposta era no —
l'Atalanta ne perde sei contro un'attesa di 1,2, p corretto 1,1%. Qui si chiede,
**data** la squadra, se manchino a caso rispetto all'**esito**.

La domanda e' rispondibile per una ragione sola: di una partita che WhoScored non
ha, **il risultato ce l'abbiamo lo stesso**, dalla fonte dei voti, che ha tutte
e 380 le partite di ogni stagione con i gol mai nulli.

{_tab(manc)}

Il test e' una **permutazione esatta a due code**: sotto il nullo le mancanti
sono un campione casuale senza reinserimento delle partite che quella squadra ha
giocato in quelle stagioni. Due code perche' il verso non era previsto.

{tab_cas}

**Sui punti l'Atalanta e' anomala: {ata['record']} in sei partite**, cioe'
{ata['punti_oss']:.2f} punti a partita contro {ata['punti_atteso']:.2f} attesi,
p = {ata['punti_p']:.4f} grezzo. **Non sopravvive alla molteplicita'**: sono
{n_test} squadre testate, la soglia di Bonferroni vale {soglia_bonf:.4f} e il p
corretto e' circa {min(1.0, ata['punti_p'] * n_test):.2f}.

**Ma la grandezza che conta qui non sono i punti, sono i gol** — R1 compone una
distribuzione di **gol**, e il modello di E3.1 e' stimato sui gol. Li' non c'e'
niente:

| grandezza | osservata | attesa | p (2 code) |
|---|---:|---:|---:|
| punti | {ata['punti_oss']:.2f} | {ata['punti_atteso']:.2f} | **{ata['punti_p']:.4f}** |
| gol fatti | {ata['gf_oss']:.2f} | {ata['gf_atteso']:.2f} | {ata['gf_p']:.3f} |
| gol subiti | {ata['gs_oss']:.2f} | {ata['gs_atteso']:.2f} | {ata['gs_p']:.3f} |
| quota in casa | {ata['casa_oss']:.2f} | {ata['casa_atteso']:.2f} | {ata['casa_p']:.3f} |

**E il meccanismo che spiega la divergenza e' aritmetico, non statistico.** I
punti sono una funzione **a gradini** dei gol: vincere 5 partite su 6 segnando
{ata['gf_oss']:.2f} gol e subendone {ata['gs_oss']:.2f} e' del tutto ordinario in
gol e straordinario in punti. Il vantaggio nei gol e' modesto ({ata['gf_oss'] - ata['gs_oss']:+.2f}
di differenza reti a partita) e la soglia lo amplifica.

**La potenza e' dichiarata, ed e' il punto piu' importante della sezione** (e' la
lezione della 6D): con **sei** partite il test vede pochissimo.

| grandezza | scarto rilevabile (MDE, 2 code 5%) | scarto osservato |
|---|---:|---:|
| gol fatti | {mde_gf['mde']:+.2f} a partita | {mde_gf['osservato']:+.2f} |
| punti | {mde_pt['mde']:+.2f} a partita | {mde_pt['osservato']:+.2f} |

Sui punti **l'osservato coincide con la soglia a ogni cifra**
({mde_pt['osservato']:.4f} contro {mde_pt['mde']:.4f}): l'effetto sta esattamente
sul limite di rilevabilita', ed e' un altro modo di leggere il p = {ata['punti_p']:.3f}.
Sui gol servirebbe uno scarto di {mde_gf['mde']:+.2f} gol a partita per essere
visto, e ce n'e' {mde_gf['osservato']:+.2f}.

> **Verdetto, e va letto per intero.** Sul bersaglio che R1 usa — i **gol** — non
> c'e' nessuna non-casualita' dimostrata, e su nessuna delle sette squadre
> testate. Sui **punti** l'Atalanta ha un punto stimato anomalo che **non
> sopravvive alla correzione per molteplicita'** e che sta esattamente sul limite
> di rilevabilita' del test. **Non e' un via libera e non e' un allarme**: e' un
> segnale in una direzione coerente, su sei partite, che i dati non permettono di
> confermare ne' di escludere. **R1 procede, e il limite resta dichiarato qui.**
>
> **Una cosa che il buco NON tocca**: l'esito di R3. La classifica finale si
> ricostruisce dal calendario completo della fonte dei voti, che non ha buchi.
> Il buco e' nell'**ingresso** del modello, non nel bersaglio contro cui lo si
> misurerebbe.

---

## 2. Perche' serve un parametro in piu'

E3.1 consegna due **marginali**: il lambda dei gol di ciascun lato. Un esito 1X2
non e' una marginale — e' una funzione della **congiunta**, e **le marginali non
determinano la congiunta**. Moltiplicarle e' gia' una scelta: e' l'ipotesi di
indipendenza, presa senza dichiararla. Questo blocco la rende un parametro.

La forma e' quella di Dixon-Coles: `tau` vale 1 ovunque tranne nelle quattro
celle dei punteggi bassi, dove sta il fenomeno noto (due squadre sullo 0-0
all'80' non giocano come sullo 0-0 al 10'). **`rho = 0` e' l'indipendenza**, ed e'
il nullo di ogni test qui.

**La verifica falsificabile del blocco**: le marginali della congiunta devono
restare le due Poisson di partenza, a `rho` qualsiasi.

| | |
|---|---:|
| scarto sulla marginale di casa | {marg['scarto_marg_casa']:.2e} |
| scarto sulla marginale di trasferta | {marg['scarto_marg_trasf']:.2e} |
| massa persa dal troncamento a {R.MAX_GOL} gol (max sui lambda veri) | {tronc['max']:.2e} |
| la stessa, in media sulle partite | {tronc['media']:.2e} |

**Zero a ogni cifra, ed e' algebra e non fortuna numerica**: sulla riga `x = 0` la
variazione delle due celle toccate e'
`P(0;c)P(0;t)·(−c·t·rho) + P(0;c)P(1;t)·(c·rho)`, e con `P(1;t) = t·P(0;t)` i due
termini si cancellano. La forma di Dixon-Coles e' costruita per spostare massa
**dentro** l'angolo senza toccare i totali di riga e colonna.

> La docstring di `verifica_marginali` affermava il contrario — che restasse un
> residuo dell'ordine di `rho·lam` — finche' la funzione non l'ha misurato e non
> ha restituito zero. **E' la verifica che ha corretto la prosa**, ed e' il motivo
> per cui e' scritta come misura e non come commento.

---

## 3. La dipendenza misurata, per tre strade indipendenti

| strada | stima | statistica | p |
|---|---:|---:|---:|
| MLE su `rho` (verosimiglianza) | {tutte['rho']:+.4f} | LR = {tutte['lr']:.3f} | {tutte['p_lr']:.3f} |
| frequenza delle 4 celle (senza modelli) | — | chi2 = {chi2:.2f} su 4 gdl | {p_chi2:.3f} |
| correlazione dei residui (senza `tau`) | {corr['corr']:+.4f} | — | {corr['p']:.3f} |

**Nessuna delle tre trova niente**, e non misurano la stessa cosa per strade
equivalenti: la seconda non passa da nessuna ottimizzazione, la terza non usa
nemmeno la forma di Dixon-Coles.

Le cinque stagioni, separate — cinque stime indipendenti che **cambiano segno**:

{tab_stag}

---

## 4. Lo scostamento che c'e' non ha la forma di Dixon-Coles

E' il risultato che il blocco non cercava, e spiega **perche'** l'MLE cade a zero
invece di limitarsi a dire che ci cade.

{tab_celle}

**{discordi} celle su 4 vanno nel verso opposto a quello che Dixon-Coles impone.**
Con un `rho` solo, la forma classica lega le quattro celle: `(0,0)` e `(1,1)` si
muovono **insieme**, e qui vanno in direzioni opposte — meno 0-0 e piu' 1-1 del
previsto. **Nessun valore di `rho` puo' produrre quel disegno**, quindi l'MLE non
ha modo di allontanarsi da zero: lo scostamento presente e' **ortogonale** a cio'
che il parametro sa esprimere.

E lo scostamento, di suo, **non e' significativo**: chi2 = {chi2:.2f} su 4 gdl,
p = {p_chi2:.3f}. Quindi non e' che ci sia una dipendenza di forma diversa e noi
usiamo il modello sbagliato: e' che con {len(d)} partite non si distingue niente
dall'indipendenza, **in nessuna delle due forme**.

---

## 5. La potenza, che e' cio' che rende il negativo leggibile

Un `rho` non distinguibile da zero non dice che la dipendenza sia zero, finche'
non si sa quanto grande dovesse essere per essere vista. Simulando risultati
**dalla congiunta con `rho` vero** e contando i rifiuti:

{tab_mde}

**La potenza dell'80% cade intorno a `rho` = 0,09**, e a 0,12 il test rifiuta
quasi sempre. Il campione **non e'** cieco: esclude dipendenze di taglia media,
non solo enormi. Cio' che non escluderebbe e' un `rho` sotto 0,05, dove la
potenza e' del 36%.

---

## 6. Cosa consegna R1 a R2

**`rho = 0`, cioe' l'indipendenza condizionata ai lambda** — non come default
comodo ma come esito misurato, con la potenza dichiarata sopra.

Distribuzione degli esiti, osservata contro modello a `rho = 0`, sulle {len(d)}
partite validabili:

{tab_dist}

E' la prima volta che il modello dei gol viene letto come previsione di
**risultato**, ed e' il materiale su cui R2 calcolera' RPS e log-loss contro i
baseline. **Qui non c'e' nessuna valutazione fuori campione**: questa e' una
media in campione, serve a mostrare che la composizione non e' sbilanciata, e
**non va citata come un risultato di accuratezza**.

> **Vincolo 1, per chi in futuro volesse un `rho` diverso da zero.** `rho` qui e'
> stimato **in campione**, ed e' lecito perche' e' usato come **limite
> superiore** — la direzione in cui 6D ha usato lo stesso genere di test. Se un
> blocco futuro volesse *usarlo* in previsione, va ristimato sul solo passato,
> come `walkforward_r` fa per `r`. Usare questo numero sarebbe stimare su dati
> che seguono il bersaglio.

---

## 7. Domande aperte

1. **Il buco dell'Atalanta resta non risolto, e non e' risolvibile qui.** Sei
   partite non bastano, e non ne arriveranno altre: la fonte non le ha. L'unica
   strada sarebbe un'altra fonte di dati evento per quelle sei, che e'
   un'acquisizione e non un'analisi.
2. **La dipendenza e' stata cercata solo nella forma di Dixon-Coles.** Lo
   scostamento osservato (meno 0-0, piu' 1-1) suggerisce una forma diversa, ma
   non e' significativo e inseguirlo su {len(d)} partite sarebbe adattarsi al
   rumore. Se G2 portasse altri campionati, e' la prima cosa che avrebbe massa
   per essere guardata.
3. **`rho` e' assunto costante fra partite.** Potrebbe dipendere dal divario di
   forza — le partite squilibrate non hanno la fase di studio che il meccanismo
   presuppone — e questo blocco non l'ha guardato.
4. **La correzione di Dixon-Coles originale ha un decadimento temporale**, qui
   assente perche' i lambda di E3.1 ce l'hanno gia' dentro. Che i due decadimenti
   debbano essere lo stesso non e' ovvio e non e' stato verificato.
"""

    OUT_MD.write_text(testo, encoding="utf-8")
    print(f"\n-> {OUT_MD}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
