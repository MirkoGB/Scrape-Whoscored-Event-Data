# -*- coding: utf-8 -*-
"""Fase 12 / Blocco V0 — il perimetro del bersaglio, e l'identita' che decide lo strato 2.

    ./.venv/Scripts/python.exe scripts/run_fase12_v0.py [--repliche N]

**Non tocca la rete e non scrive niente sotto `data/`.** Legge `team_match` delle
cinque stagioni, che esiste dalla Fase 1 e dal blocco E0: questa fase non
acquisisce e non ricalcola nessun derivato.

**Non stima nessun modello predittivo**: nessun walk-forward, nessun
iperparametro, nessun bersaglio previsto. Conta, misura, e decide la forma di V1
e V2. E' l'analogo di R0 per la Fase 12.

~1 min con le repliche di default.
"""
from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sot import config, tentativi as T  # noqa: E402

OUT_MD = config.REPORTS / "fase12_v0_perimetro.md"
OUT_ETERO = config.REPORTS / "fase12_v0_eterogeneita.csv"
OUT_TARATURA = config.REPORTS / "fase12_v0_taratura.csv"
OUT_LINEE = config.REPORTS / "fase12_v0_linee.csv"
OUT_CLUSTER = config.REPORTS / "fase12_v0_cluster.csv"
OUT_QUOTA = config.REPORTS / "fase12_v0_quota_squadra_stagione.csv"


def _tab(df: pd.DataFrame, dec: dict[str, int] | None = None) -> str:
    """Tabella markdown. Colonne numeriche a destra, NaN come trattino."""
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
    ap.add_argument("--repliche", type=int, default=2000,
                    help="repliche del nullo simulato (default 2000)")
    ap.add_argument("--repliche-taratura", type=int, default=1000,
                    help="repliche per punto della griglia di taratura (default 1000)")
    args = ap.parse_args()

    print("Fase 12, blocco V0 — il perimetro del bersaglio")
    print("=" * 62)

    u = T.universo()
    print(f"[1] universo: {len(u)} righe squadra-partita, "
          f"{u['matchId'].nunique()} partite, {u['stagione'].nunique()} stagioni")

    conteggi = T.verifica_conteggi(u)
    assert conteggi["passa"].all(), conteggi[~conteggi["passa"]]
    print(f"    verifiche falsificabili: {int(conteggi['passa'].sum())}/{len(conteggi)} passate")

    mid = T.matchid_unico(u)
    print(f"[2] matchId unico fra stagioni: {mid['unico']} "
          f"({mid['collisioni']} collisioni)")

    deriva = T.deriva_livello(u)
    print(f"[3] livello: {deriva['shots'].iloc[0]:.2f} -> {deriva['shots'].iloc[-1]:.2f} "
          f"tentativi per squadra-partita ({deriva['deriva_pct'].iloc[-1]:+.1f}%)")

    clu = T.fattore_cluster(u)
    print(f"[4] cluster di partita: corr {clu['corr_pooled']:+.3f} "
          f"-> fattore {clu['fattore_se']:.3f} (stesso segno: {clu['stesso_segno']})")

    linee = T.base_rate_linee(u)
    print(f"[5] linee: {T.LINEE_TIRI}, tutte dentro la regola: "
          f"{bool(linee['dentro_regola'].all())}")

    rho = T.rho_intraclasse(u)
    print(f"[6] sovradispersione di partita: phi {rho['phi_squadra_partita']:.4f} "
          f"-> rho intraclasse {rho['rho_intraclasse']:.5f}")

    liv = T.livello_sbagliato(u)
    print(f"[7] il livello giusto e' squadra-STAGIONE: MDE "
          f"{liv.loc[1, 'tau_mde_punti']:.2f} punti contro "
          f"{liv.loc[0, 'tau_mde_punti']:.2f} a squadra-partita")

    print(f"[8] test di eterogeneita' ({args.repliche} repliche, "
          f"taratura {args.repliche_taratura})...")
    etero, tarature = T.tabella_eterogeneita(
        u, n_sim=args.repliche, n_sim_taratura=args.repliche_taratura)
    for _, r in etero.iterrows():
        print(f"    {r['lato']:<8} phi {r['phi_osservato']:.3f}  z {r['z']:+.2f}  "
              f"tau {r['tau_punti']:.2f} pt  MDE {r['tau_mde_punti']:.2f} pt  "
              f"-> {'ADOTTATO' if r['rifiuta'] and r['supera_mde'] else 'no'}")

    glm = T.test_eterogeneita_glm(u)
    print("[9] strada di controllo (GLM quasi-verosimiglianza):")
    for _, r in glm.iterrows():
        print(f"    {r['confronto']:<28} F {r['F']:.2f}  p {r['p']:.4g}")

    thin = T.thinning_simulato()
    print(f"[10] thinning: r vera {thin['r_vero']:.0f} -> stimata "
          f"{thin['r_stimata_su_S']:.2f} ({thin['scarto_r_pct']:+.1f}%), "
          f"media {thin['scarto_media_pct']:+.3f}%")

    ver = T.verdetto_strato2(etero)
    print(f"[11] VERDETTO: {ver['ramo']} — lati adottati: {ver['lati_adottati']}")

    quota = T.quota_aggregata(u, "attacco")
    tar_lunga = pd.concat(
        [t.assign(lato=l) for l, t in tarature.items()], ignore_index=True)

    etero.to_csv(OUT_ETERO, index=False, encoding="utf-8")
    tar_lunga.to_csv(OUT_TARATURA, index=False, encoding="utf-8")
    linee.to_csv(OUT_LINEE, index=False, encoding="utf-8")
    T.correlazione_lati(u).to_csv(OUT_CLUSTER, index=False, encoding="utf-8")
    quota.to_csv(OUT_QUOTA, index=False, encoding="utf-8")

    top = quota.sort_values("p_hat", ascending=False)
    estremi = pd.concat([top.head(5), top.tail(5)])[
        ["stagione", "chiave", "n", "k", "p_hat", "p_stagione", "residuo_pearson"]]

    testo = f"""# Fase 12 / Blocco V0 — il perimetro del bersaglio

> Generato da `scripts/run_fase12_v0.py` il {date.today().isoformat()}.
> **Non tocca la rete e non scrive niente sotto `data/`.** Legge `team_match`
> delle cinque stagioni, che esiste dalla Fase 1 e dal blocco E0.
> **Non stima nessun modello predittivo**: conta, misura, e decide la forma di
> V1 e V2. E' l'analogo di R0 per questa fase.

## 0. Che cosa questo blocco decide

La Fase 12 modella i **tentativi** (`team_match.shots`), non i tiri in porta, e
per **qualsiasi** squadra. Il disegno e' gerarchico:

```
strato 1 (volume)      shots_ij ~ NB2(lambda_ij, r)
strato 2 (precisione)  sot_ij | shots_ij ~ Binomiale(shots_ij, p_ij)
```

V0 risponde a una domanda sola: **`p_ij` varia davvero fra squadre, o e' un
numero solo piu' rumore binomiale?** Se non varia, lo strato 2 collassa a
`sot = shots * p_lega`, la composizione diventa esatta e il modello ha meno
parti — che non e' un fallimento, e' un risultato piu' parsimonioso.

Il criterio e' stato scritto **prima** di guardare i numeri:

> {T.CRITERIO_STRATO2}

## 1. L'universo, e le verifiche che non passano da nessun modello

{_tab(conteggi, {"valore": 0, "atteso": 0})}

**`sot <= shots` su tutte e {len(u)} le righe.** Non e' pedanteria: se cadesse,
la binomiale dello strato 2 sarebbe *impossibile*, non malamente specificata.

**Le 2 righe a zero tentativi esistono e restano**: entrano nei livelli e non
nei rapporti, dove la quota e' `NaN` e non zero. Uno zero le farebbe entrare
nelle medie come squadre che non hanno mai centrato la porta.

**`matchId` e' unico fra le cinque stagioni** ({mid['matchId distinti']} distinti,
{mid['collisioni']} collisioni). Serve a V1 e non a V0, ed e' il motivo per cui
sta qui: `build_predictors` aggancia il lato difensivo con
`merge(on=["matchId", "opponent"])`, e un `matchId` ripetuto farebbe arrivare il
predittore dell'avversario **da un'altra stagione** senza che nulla lo dica.
Nessuno l'aveva verificato.

## 2. Il livello si muove, ed e' il motivo del disegno di V1

{_tab(deriva, {"shots": 3, "shots_sd": 3, "sot": 3, "quota_in_porta": 4,
               "var_su_media": 3, "deriva_pct": 2, "n": 0})}

Il livello dei tentativi scende del **{abs(deriva['deriva_pct'].iloc[-1]):.1f}%**
fra la prima e l'ultima stagione, non monotono. La quota in porta invece **non
si muove** ({deriva['quota_in_porta'].min():.4f}-{deriva['quota_in_porta'].max():.4f}),
coerente con quanto la Fase 7 aveva gia' misurato sulle categorie di tiro.

**Ne segue il disegno di V1: walk-forward DENTRO la stagione**, con le sole
righe valutate impilate. Cosi' `mu` assorbe il livello di quella stagione per
costruzione, e non servono ne' un effetto di stagione ne' la standardizzazione
di E1 — che governa il confronto fra unita' grezze di stagioni diverse, cosa
che qui non avviene mai. E' la stessa scelta di E3 sui gol, per la stessa
ragione.

## 3. Il cluster di partita — quanto valgono davvero 3.778 righe

{_tab(T.correlazione_lati(u), {"corr": 4, "ic95_basso": 4, "ic95_alto": 4,
                               "fattore_se": 4, "partite": 0})}

**Il segno e' NEGATIVO, e non era l'attesa.** Si temeva una correlazione
positiva — ritmo, punteggio e arbitro condivisi — che avrebbe gonfiato ogni `t`
appaiato di questa fase. Misurata, vale **{clu['corr_pooled']:+.3f}**, con lo
stesso segno in tutte e cinque le stagioni e intervalli che non contengono lo
zero.

Il meccanismo e' piu' forte di quello atteso: **il possesso e' a somma
costante**. Chi domina tira molto e lascia tirare poco, quindi i tentativi dei
due lati si sottraggono invece di sommarsi.

La conseguenza va nel verso **favorevole** —
`sqrt(1 - {abs(clu['corr_pooled']):.3f}) = {clu['fattore_se']:.3f}`, cioe' gli errori
standard appaiati sono piu' **piccoli** del nominale — e va applicata lo stesso:
un fattore favorevole non dichiarato resta un numero sbagliato. V1 riportera'
entrambi i `t`, per riga e per cluster.

## 4. Le linee, dichiarate prima

> {T.REGOLA_LINEE}

{_tab(linee, {"tasso_base": 4, "sd_dalla_media": 4})}

{_tab(T.confronto_con_le_linee_sot(), {"media": 3, "sd": 3, "sd_dalla_media": 3})}

Le linee dei tentativi coprono **lo stesso intervallo** in deviazioni standard
che `validate.LINES` copre sui tiri in porta (circa da -0,8 a +0,8): e' lo
**stesso esperimento** su un bersaglio riscalato, che e' la sola forma in cui i
numeri della Fase 12 e della Fase 4 si possano mettere accanto. Non sono
identiche riga per riga — le linee di mercato sono mezzi interi e la scala e'
diversa — ma la copertura si', ed e' quella che conta. Un passo di 1 tiro invece
di 2 darebbe cinque linee a 0,19 sd l'una dall'altra, cioe' cinque volte lo
stesso test.

**Le linee dei tiri in porta NON si toccano**: la marginale composta di V2 si
valuta su `validate.LINES` inalterata. Inventarne di nuove renderebbe questa
fase non confrontabile con la Fase 4.

## 5. Perche' `phi = 1,101` non risponde alla domanda

E' l'errore che questo blocco esiste per non commettere. `recording_stability`
ha misurato che la quota in porta e' stabile *fra stagioni e fra mesi*, e ha
riportato `phi = 1,101`. Ma quel `phi` e' la sovradispersione delle unita'
**squadra-partita**: contiene rumore di partita, effetto squadra ed effetto
avversario tutti insieme, e non li separa. «La quota di campionato non si muove
fra stagioni» e «la quota non varia fra squadre» sono **due nulli diversi**, e
il secondo non era mai stato testato.

{_tab(liv, {"n_medio": 2, "sd_binomiale_quota": 5, "phi_osservato": 4,
            "tau_mde": 5, "tau_mde_punti": 2, "unita": 0, "gdl": 0})}

A ~12,6 tentativi la deviazione standard binomiale della quota vale
**{liv.loc[0, 'sd_binomiale_quota'] * 100:.1f} punti**: una differenza fra squadre di 2-3
punti ci sparisce dentro, e `phi = 1,10` **e' quel rumore**. A ~475 tentativi
scende a **{liv.loc[1, 'sd_binomiale_quota'] * 100:.1f} punti** e la componente di squadra emerge.
Il livello sbagliato ha un MDE **{liv.loc[0, 'tau_mde_punti'] / liv.loc[1, 'tau_mde_punti']:.1f} volte peggiore**.

## 6. Il nullo va generato, non letto da una tabella

Il `chi2` teorico assume binomialita' **esatta** dentro la squadra-stagione. Ma
la sovradispersione di partita esiste — `phi = {rho['phi_squadra_partita']:.4f}`,
cioe' correlazione intraclasse **{rho['rho_intraclasse']:.5f}** — e un test che
la ignorasse la scambierebbe per eterogeneita' di squadra: sarebbe **garantito
di rifiutare**. Il nullo giusto e' «`p` non varia fra squadre, ma varia da
partita a partita quanto gia' sappiamo», realizzato come beta-binomiale a
livello squadra-partita e poi aggregato.

Che la differenza non sia accademica si legge nella tabella qui sotto: il `p`
del chi-quadro teorico e quello simulato non si somigliano.

## 7. Il test, e la sua taratura

{_tab(etero[["lato", "unita", "gdl", "phi_osservato", "phi0_simulato", "z",
             "soglia_sidak", "rifiuta", "p_simulato", "p_chi2_teorico",
             "tau_punti", "tau_mde_analitico", "tau_mde_punti", "supera_mde"]],
      {"phi_osservato": 3, "phi0_simulato": 3, "z": 2, "soglia_sidak": 3,
       "p_simulato": 4, "p_chi2_teorico": 6, "tau_punti": 2,
       "tau_mde_analitico": 4, "tau_mde_punti": 2, "unita": 0, "gdl": 0})}

**La taratura e' cio' che rende leggibile il risultato**, ed e' l'unico modo di
distinguere «il test ha trovato eterogeneita'» da «il test rifiuta sempre».
Attese dichiarate prima: ~5% alla riga `tau = 0` (che e' la **dimensione**, non
zero), ~80% al MDE, monotona in mezzo.

{_tab(tar_lunga[["lato", "tau_punti", "phi_medio", "potenza"]],
      {"tau_punti": 2, "phi_medio": 3, "potenza": 3})}

**La taratura ha corretto il MDE, ed e' il motivo per cui esiste.** Il MDE
analitico vale {etero.loc[0, 'tau_mde_analitico'] * 100:.2f} punti, ma a quel `tau` la potenza
**vera** e' ~53%, non 80%: la formula assume `phi` normale con deviazione
standard costante, mentre sotto l'alternativa la sd cresce. Il MDE pubblicato e'
quello **tarato** ({etero.loc[0, 'tau_mde_punti']:.2f} punti), che e' un terzo piu' grande.
Un MDE sbagliato nella direzione comoda e' peggio che non averlo.

A `tau = 0` la frequenza di rifiuto vale {tar_lunga.loc[tar_lunga['tau'] == 0, 'potenza'].min():.3f}-{tar_lunga.loc[tar_lunga['tau'] == 0, 'potenza'].max():.3f},
sotto il 5% nominale e coerente con la soglia di Sidak per `k = 3` (~1,7% per
test singolo): **il test non e' liberale**.

## 8. La strada di controllo, indipendente dalla prima

{_tab(glm, {"delta_devianza": 2, "phi": 4, "F": 3, "p": 6,
            "gdl_num": 0, "gdl_den": 0})}

Due strade che concordano sono un risultato; una sola e' un'asserzione. La GLM
binomiale in quasi-verosimiglianza stima `p` come **coefficienti** invece che
come dispersione, quindi ha piu' potenza — ed e' la ragione per cui sul lato
difesa rifiuta mentre il test di dispersione mette l'effetto sotto il proprio
MDE. Le due cose non sono in contraddizione: l'effetto difensivo **c'e' ed e'
piccolo**, e il test di dispersione dichiara di non poterlo risolvere.

**Sul lato campo il disegno iniziale era sbagliato**, e l'esecuzione lo ha
corretto: si era scritto che il campo fosse «il piu' potente dei tre» perche' ha
un `n` enorme per cella. Ha pero' **10 unita' e 5 gradi di liberta'**, quindi il
test di dispersione li' e' quasi cieco. La strada buona per il campo e' il test
F, che infatti lo misura: F = {glm.loc[0, 'F']:.2f}, p = {glm.loc[0, 'p']:.4f}.

## 9. Il thinning — la premessa della gerarchia, verificata dove la risposta e' nota

Se `N ~ NB2(lambda, r)` e `S | N ~ Bin(N, p)` con `p` costante, allora
`S ~ NB2(lambda*p, r)`: **stesso `r`**, media scalata. E' la proprieta' su cui
poggia tutta la gerarchia — senza, la marginale dei tiri in porta non avrebbe
forma chiusa e V2 dovrebbe convolvere numericamente.

Verificata su {200_000:,} estrazioni generate, con `dispersion.fit_r` del
progetto e non con una formula scritta apposta: media attesa
{thin['media_attesa_S']:.4f} contro osservata {thin['media_S']:.4f}
({thin['scarto_media_pct']:+.3f}%), `r` vera {thin['r_vero']:.0f} contro stimata
{thin['r_stimata_su_S']:.2f} ({thin['scarto_r_pct']:+.1f}%).

## 10. Il verdetto, applicato meccanicamente

**{ver['ramo'].upper()}** — lati adottati: **{', '.join(ver['lati_adottati']) or 'nessuno'}**.

| lato | rifiuta | supera il MDE | adottato |
|---|---|---|---|
{chr(10).join(f"| {r['lato']} | {'si' if r['rifiuta'] else 'no'} | {'si' if r['supera_mde'] else 'no'} | {'**si**' if r['rifiuta'] and r['supera_mde'] else 'no'} |" for _, r in etero.iterrows())}

**La precisione e' una proprieta' di chi tira, non di chi difende e non del
campo.** Il lato attacco ha `tau = {etero.loc[0, 'tau_punti']:.2f}` punti di quota contro un
MDE tarato di {etero.loc[0, 'tau_mde_punti']:.2f}, con z = {etero.loc[0, 'z']:+.2f} e p simulato
{etero.loc[0, 'p_simulato']:.4f}. Il lato difesa rifiuta il test ma **resta sotto il proprio
MDE** ({etero.loc[1, 'tau_punti']:.2f} contro {etero.loc[1, 'tau_mde_punti']:.2f}): l'effetto c'e', il GLM
lo vede, e questo test dichiara di non poterlo risolvere. Il campo non rifiuta.

Le cinque squadre-stagione piu' e meno precise, per dare la scala di cio' di cui
si parla:

{_tab(estremi, {"p_hat": 4, "p_stagione": 4, "residuo_pearson": 2, "n": 0, "k": 0})}

### Che cosa V0 consegna a V1 e V2

1. **A V1**: il walk-forward va **dentro la stagione**; `build_predictors` va
   eseguito **per stagione separatamente** (sul concatenato, settembre 2023
   userebbe maggio 2023 con peso 0,57); `matchId` e' unico, quindi il join del
   lato difensivo e' sicuro; il fattore di cluster vale
   **{clu['fattore_se']:.3f}** e va applicato a ogni errore standard appaiato;
   le linee sono `{T.LINEE_TIRI}`.
2. **A V2**: **lo strato 2 si stima**, ma con **il solo lato attacco**. La forma
   chiusa del thinning **non e' valida** cosi' com'e', perche' `p` varia fra
   squadre: V2 deve avere entrambe le strade — chiusa e convoluzione numerica —
   e un test che le fa coincidere dove `p` e' costante.

## 11. Domande aperte

1. **Il lato difesa e' al limite** ({etero.loc[1, 'tau_punti']:.2f} punti contro un MDE di
   {etero.loc[1, 'tau_mde_punti']:.2f}) e le due strade lo trattano diversamente. V2 lo
   includera' o no: la decisione va presa **prima** di guardarne l'effetto
   predittivo, altrimenti e' un iperparametro scelto sul bersaglio.
2. **La correlazione negativa fra i due lati non e' stata spiegata, solo
   misurata.** Il possesso a somma costante e' la spiegazione compatibile piu'
   economica, ma non e' stata verificata — servirebbe rifare la misura
   condizionando sul possesso, e non e' in questo blocco.
3. **`tau` e' assunto costante fra stagioni.** Con 100 unita' complessive
   stimarne cinque separati non e' possibile, ed e' la stessa forma del limite
   che R1 dichiara su `rho`.
4. **Il totale di partita** (`lambda_casa + lambda_trasferta`) e' la linea di
   mercato piu' comune, e la correlazione negativa misurata qui dice che **non
   e' la somma di due indipendenti**. Serve la congiunta, che sui tentativi non
   e' misurata. E' una domanda per V1, o un blocco a se'.
"""
    OUT_MD.write_text(testo, encoding="utf-8")
    for p in (OUT_MD, OUT_ETERO, OUT_TARATURA, OUT_LINEE, OUT_CLUSTER, OUT_QUOTA):
        print(f"-> {p}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
