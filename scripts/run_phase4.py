# -*- coding: utf-8 -*-
"""Fase 4 — consolidamento della validazione.

    python scripts/run_phase4.py

Non introduce modelli nuovi: prende quelli delle Fasi 2 e 3 e li sottopone,
tutti sulle **stesse identiche righe**, allo stesso blocco di controlli.

Tre cose che le fasi precedenti non facevano:

1. **Tabelle di affidabilita' per tutti i modelli**, non solo per il modello
   principale. Senza le tabelle dei baseline non si sa se una miscalibrazione
   sia colpa del modello o del problema.
2. **Baseline affiancati a ogni metrica**, incluse quelle probabilistiche, e
   ciascuno con la **propria** dispersione: usare per un baseline la r stimata
   sui lambda del modello lo penalizzerebbe per un parametro non suo.
3. **`r` e tasso base stimati walk-forward.** In Fase 2 erano stimati
   sull'intero campione valutato: non entrano nella previsione puntuale, ma
   entrano nel Brier. Qui si riportano entrambe le versioni, cosi' la
   differenza si legge invece di doverla assumere trascurabile.

Scrive reports/phase4_validation.md.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import norm

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sot import (aggregate, config, dispersion as D, model_player as MP,  # noqa: E402
                 project_2627 as P, validate as V, walkforward as wf)

LINES = V.LINES
MODEL = V.MODEL_NAME


def main() -> None:
    print("Fase 4 — validazione consolidata")
    tm = aggregate.load_team_match()
    df = wf.build_predictors(tm)

    B = V.evaluation_bundle(df, config.PROCESSED / "walkforward_base.parquet")
    ef, y, preds = B["ef"], B["y"], B["preds"]
    r_wf, r_full, base_wf = B["r_wf"], B["r_full"], B["base_wf"]
    print(f"  r walk-forward (modello): mediana {np.median(r_wf[MODEL]):.1f}, "
          f"finale {r_wf[MODEL][-1]:.1f}, intero campione {r_full[MODEL]:.1f}")

    tab_wf, cmp_wf = B["tab"], B["cmp"]
    tab_full, _ = V.compare_models(y, preds, r=r_full)

    cols = ["n", "mae", "rmse", "bias", "corr", "sharpness", "loglik_nb2",
            "brier", "brier_base", "ece"]
    calib = tab_wf[["calib_slope", "calib_se", "calib_z_vs_1"]].copy()
    calib["p_value"] = 2 * norm.sf(np.abs(calib["calib_z_vs_1"]))
    calib["compatibile con 1.0"] = np.where(calib["p_value"] > 0.05, "si", "NO")

    # ------------------------------------------------ affidabilita' per modello
    rel = {n: V.reliability_table((y > config.OVER_LINE).astype(float),
                                  D.p_over(preds[n], config.OVER_LINE, r_wf[n]))
           for n in preds}
    dec = pd.DataFrame([dict(V.brier_decomposition(
        (y > config.OVER_LINE).astype(float),
        D.p_over(preds[n], config.OVER_LINE, r_wf[n])), modello=n)
        for n in preds]).set_index("modello")

    # ------------------------------------------------------ Brier su piu' linee
    rows = []
    for n in preds:
        row = {"modello": n}
        for ln in LINES:
            yb = (y > ln).astype(float)
            row[f"Over {ln}"] = V.brier(yb, D.p_over(preds[n], ln, r_wf[n]))
        rows.append(row)
    rows.append({"modello": "baseline: tasso base (walk-forward)",
                 **{f"Over {ln}": V.brier((y > ln).astype(float), base_wf[ln])
                    for ln in LINES}})
    lines_tab = pd.DataFrame(rows).set_index("modello")
    freq_tab = pd.DataFrame([{f"Over {ln}": float((y > ln).mean()) for ln in LINES}],
                            index=["frequenza osservata"])

    # --------------------------------------------- predittiva intera: PIT e IC
    u = V.pit(y, preds[MODEL], r_wf[MODEL])
    pit_m = V.pit_uniformity(u)
    u_base = V.pit(y, preds["media squadra + campo"], r_wf["media squadra + campo"])
    pit_b = V.pit_uniformity(u_base)
    cov = V.interval_coverage(y, preds[MODEL], r_wf[MODEL])
    cov_b = V.interval_coverage(y, preds["media squadra + campo"],
                                r_wf["media squadra + campo"])

    # ------------------------------------------------------------- segmenti
    lam = preds[MODEL]
    segs = {
        "campo": pd.Series(np.where(ef["is_home"], "casa", "trasferta")),
        "terzile di lambda previsto": pd.qcut(
            pd.Series(lam), 3, labels=["basso", "medio", "alto"]),
        "meta' di stagione": pd.Series(
            np.where(ef["team_match_idx"] <= 19, "1a meta'", "2a meta'")),
    }
    seg_tabs = {k: V.metrics_by_segment(y, lam, s, r=r_wf[MODEL]) for k, s in segs.items()}
    seg_base = {k: V.metrics_by_segment(y, preds["media squadra + campo"], s,
                                        r=r_wf["media squadra + campo"])
                for k, s in segs.items()}

    # ------------------------------------------- Fase 3: baseline sullo stesso test
    pm = aggregate.load_player_match()
    d_ctx = MP.with_context(pm, tm)
    tau = float(MP.select_tau(d_ctx).iloc[0]["tau"])
    ht = P.first_half_test(pm, tm, tau=tau)

    league_h1 = float(tm.loc[tm["team_match_idx"] <= 19, "sot"].mean())
    ht = ht.assign(**{"media campionato": league_h1})
    ht["err_media campionato"] = ht["media campionato"] - ht["actual_h2"]

    h3_rows = []
    for label, col in [("dall'alto (= media squadra 1a meta')", "topdown"),
                       ("dal basso, livello dai giocatori (A)",
                        "livello_dai_giocatori"),
                       ("dal basso, compositivo (B, quello pubblicato)",
                        "compositivo"),
                       ("baseline: media campionato", "media campionato")]:
        e = ht[f"err_{col}"]
        h3_rows.append({"metodo": label, "MAE": e.abs().mean(),
                        "RMSE": float(np.sqrt((e ** 2).mean())),
                        "bias": e.mean(),
                        "corr": float(np.corrcoef(ht[col], ht["actual_h2"])[0, 1])
                        if ht[col].std() > 0 else np.nan})
    h3 = pd.DataFrame(h3_rows).set_index("metodo")
    d_bu, t_bu = V.paired_t(ht["err_topdown"].abs(),
                            ht["err_livello_dai_giocatori"].abs())
    d_lg, t_lg = V.paired_t(ht["err_media campionato"].abs(), ht["err_topdown"].abs())

    # ------------------------------------------------------------------ report
    ref = {"mae": 1.69, "bias": 0.01, "corr": 0.41, "calib_slope": 1.05,
           "brier": 0.211, "brier_base": 0.238}
    m = tab_wf.loc[MODEL]
    conf = pd.DataFrame({
        "riferimento": ref,
        "Fase 2 (r intero campione)": {k: tab_full.loc[MODEL, k] for k in ref},
        "Fase 4 (r walk-forward)": {k: m[k] for k in ref},
    })

    L = [
        "# Fase 4 — validazione consolidata", "",
        f"Righe valutate: **{len(ef)}** su 760 (burn-in: dalla "
        f"{config.BURN_IN_ROUND}a partita di ciascuna squadra). "
        "Modello e baseline sono valutati sulle **stesse** righe: qualunque "
        "confronto su sottoinsiemi diversi sarebbe privo di significato.", "",
        "Nessun modello nuovo: si validano quelli delle Fasi 2 e 3.", "",

        "## Esito in breve", "",
        f"1. **Il modello e' calibrato, i baseline informativi no.** Pendenza "
        f"{m['calib_slope']:.3f} +- {m['calib_se']:.3f} (z = {m['calib_z_vs_1']:+.2f}, "
        f"compatibile con 1.0); `media squadra` sta a "
        f"{calib.loc['media squadra', 'calib_slope']:.3f} "
        f"(z = {calib.loc['media squadra', 'calib_z_vs_1']:+.2f}) e "
        f"`media squadra + campo` a {calib.loc['media squadra + campo', 'calib_slope']:.3f} "
        f"(z = {calib.loc['media squadra + campo', 'calib_z_vs_1']:+.2f}). Questa e' "
        "la giustificazione empirica piu' netta del modello, piu' netta del suo "
        "vantaggio sul MAE.",
        f"2. **Il vantaggio sul MAE resta invece dentro il rumore**: t = "
        f"{cmp_wf.set_index('vs').loc['media squadra + campo', 't_mae']:.2f} contro "
        "il baseline migliore. La Fase 2 lo diceva gia'; qui e' confermato su "
        "quattro soglie, tre segmentazioni e con i parametri di probabilita' "
        "anch'essi walk-forward.",
        "3. **La forma della predittiva regge**, non solo la media: PIT "
        f"randomizzato chi2 = {pit_m['chi2']:.2f} su {pit_m['dof']} gradi di "
        f"liberta' (p = {pit_m['p_value']:.3f}). E' un controllo che le Fasi 2 e "
        "3 non facevano.",
        "4. **La scorciatoia della Fase 2 su `r` non cambiava le conclusioni**, "
        f"ma lo si sa solo adesso: il Brier si sposta di "
        f"{tab_wf.loc[MODEL, 'brier'] - tab_full.loc[MODEL, 'brier']:+.4f}.",
        "5. **Il metodo dal basso della Fase 3 non batte il piu' banale "
        "baseline di squadra**, e il segno resta contrario. Nessuna correzione "
        "e' stata applicata. Vale pero' per l'estimatore che fissa il livello "
        "dai giocatori: quello **compositivo**, che e' l'estimatore pubblicato, "
        "e' un'altra cosa e questo test non ha la potenza per giudicarlo "
        "(Fase 6B).", "",

        "## 1. I parametri di probabilita' vengono anch'essi dal passato", "",
        "Convertire lambda in una probabilita' richiede due parametri che non "
        "fanno parte della previsione puntuale: la dispersione `r` della NB2 e "
        "il tasso base contro cui si misura il Brier. In Fase 2 erano stimati "
        "sull'intero campione valutato. Qui sono ricostruiti riga per riga sul "
        "solo passato (minimo "
        f"{V.MIN_PRIOR} righe precedenti, prima delle quali si resta sulla "
        "Poisson).", "",
        f"- r del modello: mediana walk-forward **{np.median(r_wf[MODEL]):.1f}**, "
        f"valore a fine stagione {r_wf[MODEL][-1]:.1f}, "
        f"sull'intero campione {r_full[MODEL]:.1f}",
        "- r per baseline (intero campione): "
        + ", ".join(f"{n} {r_full[n]:.1f}" for n in preds if n != MODEL),
        f"- tasso base Over {config.OVER_LINE}: walk-forward medio "
        f"**{base_wf[config.OVER_LINE].mean():.4f}**, osservato "
        f"{float((y > config.OVER_LINE).mean()):.4f}", "",
        "La riga dei baseline va letta: **r scende quanto piu' il modello e' "
        "povero** — "
        f"{r_full['media campionato']:.1f} per la media di campionato contro "
        f"{r_full[MODEL]:.1f} per il modello. Non e' che i dati siano piu' "
        "dispersi per un modello che per l'altro: e' la variazione di lambda "
        "che il baseline non spiega, e che finisce nella dispersione perche' "
        "non ha altro posto dove andare. La media di campionato arriva a "
        "sfiorare la soglia di sospetto di 10 dichiarata in `dispersion.py`; "
        "qui pero' non e' il sintomo di un errore, e' il baseline che fa il "
        "suo mestiere di essere stupido.", "",
        "Confronto diretto con i valori dichiarati in Fase 2:", "",
        conf.round(4).to_markdown(), "",
        "La differenza fra le due colonne e' l'effetto della scorciatoia. MAE, "
        "bias, correlazione e pendenza non cambiano per costruzione — non "
        "dipendono da `r`. Cambia il Brier, di "
        f"{tab_wf.loc[MODEL, 'brier'] - tab_full.loc[MODEL, 'brier']:+.4f}, e il "
        "suo tasso base, di "
        f"{tab_wf.loc[MODEL, 'brier_base'] - tab_full.loc[MODEL, 'brier_base']:+.4f}. "
        "Sono spostamenti di quarta cifra: la scorciatoia della Fase 2 non "
        "cambiava le conclusioni. Questo si sa **adesso** che e' stato "
        "misurato; non era una cosa da assumere. I numeri da citare sono quelli "
        "dell'ultima colonna.", "",

        "## 2. Metriche, modello e baseline affiancati", "",
        "`sharpness` e' la deviazione standard dei lambda previsti. Va letta "
        "insieme alla calibrazione: prevedere la media a tutti da' calibrazione "
        "perfetta e sharpness zero. `ece` e' l'errore di calibrazione atteso "
        f"sull'Over {config.OVER_LINE}.", "",
        tab_wf[cols].round(4).to_markdown(), "",
        f"Confronti appaiati contro **{MODEL}** "
        "(`d_loglik` > 0 e `d_mae` > 0 = il modello vince):", "",
        cmp_wf[["vs", "d_loglik", "t_loglik", "d_mae", "t_mae"]]
        .round(4).to_markdown(index=False), "",
        "Il margine sul baseline migliore resta sotto le due deviazioni "
        "standard. Quasi tutta la prevedibilita' dei tiri in porta e' \"questa "
        "squadra tira tanto, e gioca in casa\"; il modello aggiunge poco, e "
        "quel poco non e' distinguibile dal rumore su una stagione sola.", "",

        "## 3. Pendenza di calibrazione contro 1.0", "",
        "Poisson di `y` su `log(lambda)`; errore standard dall'informazione di "
        "Fisher. b < 1 = previsioni troppo estreme, b > 1 = troppo compresse.", "",
        calib.round(4).to_markdown(), "",
        "Due letture obbligatorie:", "",
        "- **`media campionato` non e' interpretabile.** Il suo `log(lambda)` e' "
        f"quasi costante (sharpness {tab_wf.loc['media campionato', 'sharpness']:.3f}), "
        "quindi la pendenza e' stimata su nessuna variazione: l'errore standard "
        f"di {calib.loc['media campionato', 'calib_se']:.2f} lo dice. Il \"si\" "
        "in tabella e' assenza di potenza, non calibrazione.",
        "- **I due baseline informativi sono miscalibrati, il modello no.** "
        f"`media squadra` (b = {calib.loc['media squadra', 'calib_slope']:.3f}) e "
        f"`media squadra + campo` (b = {calib.loc['media squadra + campo', 'calib_slope']:.3f}) "
        "sono sotto 1.0 di piu' di tre e quasi tre errori standard: le loro "
        "previsioni sono **troppo estreme**, perche' una media campionaria non "
        "regredisce verso il centro e prende per buono il rumore di poche "
        "partite. E' esattamente il difetto che la penalizzazione ridge del "
        "modello corregge, ed e' la sua giustificazione empirica piu' netta — "
        "piu' netta del vantaggio sul MAE, che resta sotto le due deviazioni "
        "standard.", "",

        "## 4. Tabelle di affidabilita' (Over "
        f"{config.OVER_LINE}), tutti i modelli", "",
        "`se` e' l'errore standard binomiale della frequenza osservata, `z` lo "
        "scarto in sue unita'. Le fasce vuote non compaiono, ed e' informativo: "
        "quante fasce un modello riesce a popolare **e' la sua risoluzione**. "
        "`media campionato` ne popola due su otto.", "",
    ]
    for n in preds:
        L += [f"**{n}**", "", rel[n].round(4).to_markdown(index=False), ""]

    L += [
        "### Scomposizione di Murphy", "",
        "Brier = affidabilita' - risoluzione + incertezza. L'**affidabilita'** "
        "(bassa e' meglio) e' l'errore che si toglierebbe ricalibrando; la "
        "**risoluzione** (alta e' meglio) e' l'unica parte che misura se il "
        "modello sa qualcosa. `residuo` e' lo scarto dovuto alla "
        "discretizzazione in fasce e va guardato prima dei tre termini.", "",
        dec.round(5).to_markdown(), "",

        "### Brier su piu' soglie", "",
        "Una sola soglia puo' essere fortunata: il rango dei modelli va "
        "verificato dove l'evento e' comune e dove e' raro. Ultima riga: il "
        "baseline che prevede a tutti il tasso base walk-forward.", "",
        lines_tab.round(4).to_markdown(), "",
        "Frequenza con cui l'evento si e' effettivamente verificato, per "
        "leggere le colonne (un evento raro ha Brier basso per costruzione, "
        "non per merito):", "",
        freq_tab.round(4).to_markdown(), "",
        "Il modello batte il tasso base su tutte e quattro le soglie, e il "
        "baseline `media squadra + campo` su tutte e quattro; ma il margine su "
        "quest'ultimo e' dello stesso ordine su ogni soglia, cioe' piccolo.", "",

        "## 5. L'intera distribuzione predittiva, non solo la media", "",
        "La pendenza di calibrazione controlla il livello di lambda. Il PIT "
        "randomizzato controlla la distribuzione: e' uniforme se e solo se "
        "anche la forma e' giusta. Eccesso agli estremi = predittiva troppo "
        "stretta, eccesso al centro = troppo larga.", "",
        f"- **{MODEL}**: chi2 = {pit_m['chi2']:.2f} su {pit_m['dof']} gradi di "
        f"liberta', p = {pit_m['p_value']:.3f}; media {pit_m['mean']:.4f} "
        f"(attesa 0.5), sd {pit_m['sd']:.4f} (attesa 0.289)",
        f"- **media squadra + campo**: chi2 = {pit_b['chi2']:.2f}, "
        f"p = {pit_b['p_value']:.3f}; media {pit_b['mean']:.4f}, sd {pit_b['sd']:.4f}",
        "",
        "Conteggi per decile del PIT (attesi "
        f"{pit_m['expected']:.1f} per fascia): "
        + ", ".join(str(int(c)) for c in pit_m["counts"]), "",
        "Copertura degli intervalli di previsione. Su conteggi la copertura e' "
        "strutturalmente **conservativa** — gli estremi sono interi — quindi "
        "qualche punto sopra il nominale e' atteso; sotto il nominale no.", "",
        cov.round(4).to_markdown(index=False), "",
        "Stesso calcolo per il baseline migliore:", "",
        cov_b.round(4).to_markdown(index=False), "",

        "## 6. Il modello e' storto da qualche parte?", "",
        "Un MAE aggregato accettabile puo' nascondere un segmento in cui il "
        "modello sbaglia sistematicamente. Baseline affiancato in ogni "
        "segmento.", "",
    ]
    seg_cols = ["n", "mae", "bias", "corr", "sharpness", "calib_slope",
                "calib_se", "brier"]
    for k in segs:
        L += [f"**Per {k}** — modello:", "",
              seg_tabs[k][seg_cols].round(4).to_markdown(),
              "", f"**Per {k}** — baseline `media squadra + campo`:", "",
              seg_base[k][seg_cols].round(4).to_markdown(), ""]

    ter = seg_tabs["terzile di lambda previsto"]
    campo = seg_tabs["campo"]
    L += [
        "Tre letture:", "",
        f"- **Il MAE cresce con lambda** ({ter.loc['basso', 'mae']:.3f} nel "
        f"terzile basso, {ter.loc['alto', 'mae']:.3f} nell'alto). Non e' un "
        "difetto: su conteggi la varianza cresce con la media, quindi il MAE "
        "**deve** crescere. Va notato perche' rende il MAE aggregato dominato "
        "dalle squadre che tirano di piu'.",
        f"- **Il bias e' concentrato in trasferta** ({campo.loc['trasferta', 'bias']:+.4f} "
        f"contro {campo.loc['casa', 'bias']:+.4f} in casa): il modello "
        "sovrastima leggermente chi gioca fuori, cioe' il coefficiente di "
        "campo e' un filo troppo piccolo. Lo scarto vale "
        f"{abs(campo.loc['trasferta', 'bias']):.3f} tiri in porta su una media "
        "di 4, ed e' dello stesso ordine anche per il baseline "
        f"({seg_base['campo'].loc['trasferta', 'bias']:+.4f}): e' una proprieta' "
        "dei dati, non del modello.",
        "- **Le pendenze per terzile non vanno confrontate con quella "
        "aggregata.** Dentro un terzile `log(lambda)` varia pochissimo per "
        "costruzione, quindi la pendenza e' stimata su un intervallo "
        "artificialmente ristretto e il suo errore standard esplode (fino a "
        f"{ter['calib_se'].max():.2f} contro "
        f"{tab_wf.loc[MODEL, 'calib_se']:.3f} sul campione intero). Servono a "
        "vedere il **bias** per fascia, non la pendenza.", "",
    ]

    won = [(k, i, float(seg_tabs[k].loc[i, "brier"] - seg_base[k].loc[i, "brier"]))
           for k in segs for i in seg_tabs[k].index]
    lost = [(k, i, d) for k, i, d in won if d >= 0]
    L += [
        "Il confronto che conta e' l'ultima colonna, riga per riga: il modello "
        f"ha un Brier migliore del baseline in {len(won) - len(lost)} segmenti "
        f"su {len(won)}.",
        ("Perde in: " + "; ".join(f"**{i}** ({k}, {d:+.4f})" for k, i, d in lost)
         + "." if lost else "Non perde in nessun segmento."),
        ("Il terzile alto e' lo stesso segmento su cui la Fase 3 aveva trovato "
         "il danno maggiore della scomposizione per giocatore, e la causa e' la "
         "stessa: le squadre che tirano molto sono quelle che il ritorno alla "
         "media penalizza, e la ridge **e'** un ritorno alla media. Qui il "
         "prezzo e' piccolo — al punto 3 si vede che comprare quella "
         "compressione compra anche l'unica calibrazione accettabile fra i "
         "modelli in gara — ma il segno e' coerente fra le due fasi e non e' un "
         "caso." if any(i == "alto" for _, i, _ in lost) else ""), "",


        "## 7. Fase 3: il metodo dal basso, con i baseline accanto", "",
        f"Stima sulle prime 19 partite di ogni squadra, previsione delle 19 "
        f"successive; 20 righe, una per squadra. tau = {tau}.", "",
        h3.round(4).to_markdown().replace("nan", "n.d."), "",
        "`n.d.`: la media di campionato e' costante su tutte le squadre, quindi "
        "la correlazione non e' definita. E' il suo limite, non un dato "
        "mancante.", "",
        f"- dal basso (A, livello dai giocatori) contro dall'alto: differenza "
        f"appaiata dei |errori| {d_bu / len(ht):+.4f} a favore di "
        f"**dall'alto** (t = {t_bu:.2f})",
        f"- dall'alto contro media di campionato: {d_lg / len(ht):+.4f} a favore "
        f"di dall'alto (t = {t_lg:.2f})", "",
        "Il punto da leggere: **\"dall'alto\" e' esattamente il baseline "
        "\"media squadra\"** calcolato sulla prima meta' di stagione. "
        "L'estimatore A non batte il piu' stupido dei baseline di squadra. Con "
        "20 righe la differenza non e' significativa in nessuno dei due sensi, "
        "ma il segno e' contrario al metodo piu' complesso, e non c'e' nulla "
        "nei dati che sostenga di adottarlo.", "",
        "**La riga B e' un'altra cosa e va letta con l'avvertenza di Fase 6B**: "
        "l'estimatore compositivo — quello che la proiezione pubblica — non "
        "fissa il livello, quindi il suo baseline corretto e' \"nessun "
        "aggiustamento di rosa\", che qui coincide numericamente con la riga "
        "dall'alto. Le due colonne sono quasi identiche perche' fra le due "
        "meta' di una stessa stagione la rosa non cambia: il confronto non ha "
        "la potenza per distinguerle e **non e' una convalida**. Dettaglio, con "
        "l'effetto minimo rilevabile, in `reports/phase6_compositivo.md`.", "",

        "## Limiti dichiarati", "",
        "- **Una stagione sola.** Ogni intervallo qui dentro e' condizionato a "
        "2025-26. Nessuno di questi numeri dice come il modello si comporti "
        "attraverso stagioni, che e' proprio l'orizzonte della proiezione "
        "2026-27.",
        f"- **{len(ef)} righe valutate, 20 squadre.** I confronti appaiati "
        "hanno gradi di liberta' effettivi minori del nominale: le due righe "
        "della stessa partita non sono indipendenti.",
        "- **Il burn-in di 6 giornate e' una scelta dichiarata**, non ottimizzata: "
        "e' fissato in `config.BURN_IN_ROUND` prima di guardare i risultati. "
        "Abbassarlo peggiorerebbe tutti i modelli, alzarlo li migliorerebbe "
        "tutti; il confronto fra modelli non ne risente.",
        "- **Il test di Fase 3 ha 20 osservazioni.** Va letto come indicazione, "
        "non come dimostrazione. E' pero' l'unica prova fuori campione "
        "disponibile sull'orizzonte che interessa.",
        f"- **`r` walk-forward parte da {V.MIN_PRIOR} righe di storia.** Prima "
        "di quella soglia le probabilita' sono poissoniane, quindi leggermente "
        "troppo sicure sulle prime date valutate.",
        "- **Nessun backtest su quote**: servirebbero prezzi di mercato reali. "
        "Il codice che usava quote generate dal modello e' in `legacy/` e non "
        "va riusato.", "",
    ]

    path = config.REPORTS / "phase4_validation.md"
    path.write_text("\n".join(L), encoding="utf-8")

    tab_wf.round(6).to_csv(config.REPORTS / "phase4_metrics.csv")
    pd.concat({n: rel[n] for n in rel}, names=["modello"]).round(6).to_csv(
        config.REPORTS / "phase4_reliability.csv")

    print(f"  MAE {m['mae']:.4f} | bias {m['bias']:+.4f} | corr {m['corr']:.4f}")
    print(f"  pendenza {m['calib_slope']:.4f} +- {m['calib_se']:.4f} "
          f"(z = {m['calib_z_vs_1']:+.2f})")
    print(f"  Brier {m['brier']:.4f} vs tasso base {m['brier_base']:.4f}")
    print(f"  PIT chi2 = {pit_m['chi2']:.2f}, p = {pit_m['p_value']:.3f}")
    print(f"  report -> {path}")


if __name__ == "__main__":
    main()
