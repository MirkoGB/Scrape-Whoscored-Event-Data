# -*- coding: utf-8 -*-
"""Fase 6D — i predittori nel regime a bassa informazione.

    python scripts/run_phase6d.py [--force]

Scrive `reports/phase6_predittori.md` e `reports/phase6_predittori.csv`.
Non cambia nessun numero pubblicato e non tocca la proiezione: qui si rifa'
**solo** il test dei predittori, restringendo la valutazione alle prime partite
di ciascuna squadra, cioe' dove l'effetto attacco ha poca storia alle spalle.

I risultati sull'intero campione restano accanto ai nuovi, non al loro posto:
il regime maturo viene ricalcolato nella stessa esecuzione e deve riprodurre
`reports/phase2_predittori.csv`.

`--force` ricalcola i nove walk-forward (~5 min); senza, li rilegge da
`data/processed/phase6d_predittori.parquet`.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sot import (aggregate, config, predictor_power as PP,  # noqa: E402
                 validate as V, walkforward as wf)

CACHE = config.PROCESSED / "phase6d_predittori.parquet"


def main(force: bool = False) -> None:
    print("Fase 6D — i predittori nel regime a bassa informazione")
    df = wf.build_predictors(aggregate.load_team_match())

    if CACHE.exists() and not force:
        print(f"  previsioni da {CACHE.name} (--force per ricalcolarle)")
        prev = pd.read_parquet(CACHE)
    else:
        prev = PP.previsioni(df)
        prev.to_parquet(CACHE, index=False)
        print(f"  previsioni -> {CACHE.relative_to(config.ROOT)}")

    # Il maturo per primo: e' il riferimento contro cui si calcola la potenza
    # degli altri regimi.
    maturo = PP.confronto(prev, "maturo", df=df)
    acerbo = PP.confronto(prev, "acerbo", df=df, riferimento=maturo)
    disg = PP.confronto(prev, "acerbo disgiunto", df=df, riferimento=maturo)

    tabelle = {"maturo": maturo, "acerbo": acerbo, "acerbo disgiunto": disg}
    ctx = {k: PP.contesto(prev, df, k) for k in tabelle}

    # --- il regime maturo deve riprodurre la Fase 2 -------------------------
    ph2 = config.REPORTS / "phase2_predittori.csv"
    riproduce = None
    if ph2.exists():
        old = pd.read_csv(ph2).set_index("predittore")
        new = maturo.set_index("predittore")
        scarto = float((new.loc[old.index, "t"] - old["t"]).abs().max())
        riproduce = scarto
        print(f"  regime maturo vs Fase 2: scarto massimo sul t = {scarto:.2e}")

    # --- salvataggio -------------------------------------------------------
    lungo = pd.concat([t.assign(regime=k) for k, t in tabelle.items()],
                      ignore_index=True)
    lungo.to_csv(config.REPORTS / "phase6_predittori.csv", index=False)

    # --- numeri di sintesi -------------------------------------------------
    t_max = {k: float(t["t"].max()) for k, t in tabelle.items()}
    p_max = {k: PP.p_del_massimo(v) for k, v in t_max.items()}
    best_maturo = maturo.iloc[0]
    rif = str(best_maturo["predittore"])
    delta_rif = float(best_maturo["d_riga"])

    # Potenza contro l'effetto per riga piu' grande che il regime maturo abbia
    # prodotto: un'alternativa unica, dichiarata, e generosa (nessuno degli
    # otto ha mai fatto meglio). Si usa l'errore standard **di quel predittore**
    # in ciascun regime, non la media degli otto: la media e' dominata dai
    # candidati a varianza minuscola e darebbe una potenza che non appartiene a
    # nessun test realmente fatto.
    se_rif = {k: float(t.set_index("predittore").loc[rif, "se_riga"])
              for k, t in tabelle.items()}
    pot_comune = {k: PP.potenza(delta_rif, se_rif[k]) for k in tabelle}

    n = {k: int(t["n"].iloc[0]) for k, t in tabelle.items()}
    passati = {k: list(t.loc[t["tenuto"], "predittore"]) for k, t in tabelle.items()}

    # Il test in campione (rapporto di verosimiglianza sulle sole righe del
    # regime) e' il piu' potente disponibile: se non rifiuta nemmeno lui, non
    # c'e' un test piu' sensibile da provare. Va corretto per gli otto
    # candidati come tutto il resto.
    p_lr_min = {k: float(t["p_lr"].min()) for k, t in tabelle.items()}
    p_lr_cor = {k: 1.0 - (1.0 - v) ** PP.FAMIGLIA for k, v in p_lr_min.items()}
    best_lr = {k: str(t.loc[t["p_lr"].idxmin(), "predittore"])
               for k, t in tabelle.items()}

    # Rapporto fra gli effetti minimi rilevabili, e quanto ne spiega la sola
    # perdita di righe. Lo scarto fra i due e' la diversa variabilita' per riga
    # della differenza di log-verosimiglianza: si riporta la direzione che
    # hanno i numeri, non quella che ci si aspetterebbe.
    rap_mde = PP.effetto_minimo(se_rif["acerbo"]) / PP.effetto_minimo(se_rif["maturo"])
    rap_n = np.sqrt(n["maturo"] / n["acerbo"])
    verso = ("piu' piccola" if rap_mde < rap_n else "piu' grande")
    chiusa = ("il regime acerbo perde potenza per il numero di righe, non per "
              "il rumore" if rap_mde < rap_n else
              "il regime acerbo perde potenza due volte, per le righe e per il "
              "rumore")

    cols = ["predittore", "n", "d_oos", "t", "mde_oos", "d_ins",
            "d_ins_regime", "p_lr"]
    cols_pot = cols + ["potenza_vs_maturo", "potenza_vs_tetto"]

    L = [
        "# Fase 6D — i predittori nel regime a bassa informazione", "",
        "In Fase 2 gli otto candidati sono stati misurati come valore "
        "**incrementale** contro un effetto attacco con trenta e piu' giornate "
        "di storia. Sono medie mobili della squadra stessa: li' sono collineari "
        "con l'effetto attacco, e la conclusione \"ripetono l'informazione "
        "invece di aggiungerla\" vale in quel regime. Qui si verifica l'ipotesi "
        "mai testata: che paghino dove l'effetto attacco e' ancora acerbo.", "",
        "**Cambia solo l'insieme di valutazione.** Stesse previsioni "
        "walk-forward, stesso split per data, stessa griglia di `alpha` scelta "
        "sul solo passato, stessi predittori, stessa soglia dichiarata in "
        f"anticipo (`t > {PP.T_KEEP}`), stessa correzione per la molteplicita' "
        "di otto candidati. Nessun parametro e' ristimato sul regime.", "",
        "## Esito in breve", "",
        f"1. **Nessun predittore passa in nessun regime.** Nel maturo il "
        f"massimo e' {t_max['maturo']:+.2f}, nell'acerbo "
        f"{t_max['acerbo']:+.2f}, sulle sole righe escluse dal burn-in "
        f"{t_max['acerbo disgiunto']:+.2f}. Su otto candidati indipendenti il "
        f"massimo atteso sotto l'ipotesi nulla e' "
        f"{PP.t_atteso_massimo():.2f}: p del massimo "
        f"{p_max['maturo']:.2f} / {p_max['acerbo']:.2f} / "
        f"{p_max['acerbo disgiunto']:.2f}.",
        f"2. **Ma il test acerbo, da solo, non ha la potenza per dirlo.** Su "
        f"{n['acerbo']} righe la potenza contro l'effetto per riga piu' grande "
        f"mai osservato nel regime maturo (`{rif}`, {delta_rif:+.5f} di "
        f"log-verosimiglianza per riga) vale **{pot_comune['acerbo']:.0%}**. "
        f"Il pavimento di un test a una coda con soglia {PP.T_KEEP} e' "
        f"{PP.potenza(0.0, 1.0):.1%}: quel {pot_comune['acerbo']:.0%} e' quasi "
        "tutta la distanza dal caso. Un `t` sotto soglia li' dentro **non e' "
        "una conferma**.",
        f"3. **Nemmeno il test piu' potente disponibile rifiuta.** Stimando i "
        "coefficienti **sulle sole righe del regime** — cioe' guardandole "
        "tutte, il massimo favore possibile — il rapporto di verosimiglianza "
        f"da', nell'acerbo, un minimo di p = {p_lr_min['acerbo']:.3f} "
        f"(`{best_lr['acerbo']}`), che sugli otto candidati diventa "
        f"{p_lr_cor['acerbo']:.2f}; nel disgiunto p = "
        f"{p_lr_min['acerbo disgiunto']:.3f} (`{best_lr['acerbo disgiunto']}`) "
        f"→ {p_lr_cor['acerbo disgiunto']:.2f}. E' un test **in campione**, "
        "quindi un suo rifiuto non avrebbe dimostrato valore predittivo; ma un "
        "suo non-rifiuto chiude la questione, perche' non esiste un test piu' "
        "sensibile da provare dentro questa specificazione. **E' qui, non nel "
        "`t`, che il risultato negativo di Fase 2 si estende al regime "
        "acerbo** — con l'avvertenza, spiegata sotto, che la penalita' ridge "
        "rende quel `p` approssimato, di un fattore che a questi valori non "
        "cambia la lettura.",
        f"4. **`xg_per_shot` non risorge.** Nell'acerbo fa "
        f"{float(acerbo.set_index('predittore').loc['xgps_att', 't']):+.2f} di "
        f"`t` contro "
        f"{float(maturo.set_index('predittore').loc['xgps_att', 't']):+.2f} nel "
        "maturo — cambia segno, ma resta a meno di meta' della soglia. E' il "
        f"caso piu' vicino a qualcosa in tutto il blocco: nel regime disgiunto "
        f"ha p in campione = "
        f"{float(disg.set_index('predittore').loc['xgps_att', 'p_lr']):.3f}, "
        f"che sugli otto candidati diventa "
        f"{1 - (1 - float(disg.set_index('predittore').loc['xgps_att', 'p_lr'])) ** PP.FAMIGLIA:.2f}. "
        "Su 40 righe, in campione, dopo aver guardato tre regimi: e' l'aspetto "
        "che ha il rumore, non una scoperta. **Resta scartato.**",
        "",
        "---", "",
        "## 1. I regimi, e quante righe hanno davvero", "",
        "| regime | `team_match_idx` | righe valutabili | note |",
        "|---|---|---|---|",
        f"| acerbo | 1-8 | **{n['acerbo']}** | le prime 3 partite non hanno "
        "previsione: a quelle date il campionato non ha ancora le 30 partite "
        "che `date_splits` pretende. L'insieme parte dalla quarta |",
        f"| maturo | {config.BURN_IN_ROUND}-38 | **{n['maturo']}** | e' "
        "esattamente il campione valutato dalla Fase 2 |",
        f"| acerbo disgiunto | 1-{config.BURN_IN_ROUND - 1} | "
        f"**{n['acerbo disgiunto']}** | solo righe **mai** valutate prima "
        "(partite 4 e 5) |",
        "",
        f"I primi due regimi **si sovrappongono** sulle partite "
        f"{config.BURN_IN_ROUND}-8: {n['acerbo'] - n['acerbo disgiunto']} delle "
        f"{n['acerbo']} righe acerbe sono anche fra le {n['maturo']} mature. "
        "Il terzo regime esiste per questo: e' l'unico confronto davvero "
        "disgiunto, e paga la disgiunzione con meta' delle righe.", "",
        "**Il troncamento a partite 4-8 e' una perdita reale, e va detta.** "
        "L'ipotesi da testare riguarda il regime a informazione minima, che "
        "sono le prime giornate; le prime tre — quelle in cui l'effetto "
        "attacco e' letteralmente non identificato — non sono valutabili senza "
        "cambiare il protocollo di stima, e cambiarlo qui vorrebbe dire "
        "confrontare due esperimenti diversi. Alla quarta partita ciascuna "
        "squadra ha gia' tre partite di storia.", "",
        "---", "",
        "## 2. Il test, regime per regime", "",
        "`d_oos` = guadagno di log-verosimiglianza **fuori campione** sul "
        "modello base, sommato sulle righe del regime; `t` = statistica "
        "appaiata sullo stesso guadagno; `mde_oos` = guadagno che sarebbe "
        f"servito per avere l'{PP.POTENZA_OBIETTIVO:.0%} di probabilita' di "
        "superare la soglia; `d_ins` = variazione **in campione** sulle stesse "
        "righe con la stima di Fase 2 (tutte le 760 righe, `as_of` a fine "
        "stagione); `d_ins_regime` = la stessa cosa con i coefficienti stimati "
        "**sulle sole righe del regime**; `p_lr` = il p del rapporto di "
        "verosimiglianza su quel guadagno.", "",
        "I due numeri in campione non sono intercambiabili, e nessuno dei due "
        "va letto come un guadagno. `d_ins` sta qui per continuita' con la "
        "Fase 2, ma non descrive il regime: il decadimento a 150 giorni pesa "
        "le prime giornate per circa un terzo, quindi quei coefficienti non "
        "sono scelti per l'acerbo. `d_ins_regime` lo e', e su di esso si "
        "calcola `p_lr` confrontando `2 x d_ins_regime` con un chi-quadro a un "
        "grado di liberta'. Sotto l'ipotesi nulla quel guadagno vale in media "
        "0.5: e' il sovradattamento che un parametro libero regala comunque, "
        "ed e' la ragione per cui la colonna da leggere e' `p_lr` e non il "
        "guadagno.", "",
        "**Perche' `d_ins_regime` e' negativo per sei candidati su otto nel "
        "regime maturo.** Non e' un errore numerico, ed e' la cosa piu' "
        "interessante della tabella. Quello che il modello minimizza non e' la "
        "verosimiglianza: e' verosimiglianza pesata **piu' la penalita' ridge** "
        "su attacco e difesa. Un predittore collineare con l'effetto attacco "
        "compra una riduzione della penalita' e paga in adattamento. Sulle 660 "
        "righe mature, con `alpha` = "
        f"{PP.ALPHA_INS:g}:", "",
        "| modello | verosimiglianza grezza | penalita' ridge | obiettivo |",
        "|---|---|---|---|",
    ]
    for etichetta, extra in (("base", ()), (f"+ `{rif}`", (rif,))):
        p = PP.penalita(PP.righe_del_regime(df, prev, "maturo"), extra)
        L.append(f"| {etichetta} | {p['loglik']:.2f} | {p['penalita']:.2f} | "
                 f"{p['obiettivo']:.2f} |")
    L += [
        "",
        f"L'obiettivo migliora, come deve; la penalita' quasi si dimezza; la "
        "verosimiglianza peggiora. **E' la sostituzione che la Fase 2 aveva "
        "dedotto dal risultato fuori campione, qui visibile direttamente nei "
        "due termini.** Ne segue anche un limite di questo blocco: con una "
        "penalita' in mezzo, `p_lr` e' approssimato — la distribuzione nulla "
        "esatta di un rapporto di verosimiglianza penalizzato non e' un "
        "chi-quadro a un grado di liberta'. Vale come ordine di grandezza, e "
        "nessuno dei valori e' cosi' vicino alla soglia da rendere la "
        "differenza importante.", "",
    ]

    for k in ("maturo", "acerbo", "acerbo disgiunto"):
        t = tabelle[k]
        use = cols if k == "maturo" else cols_pot
        L += [f"### Regime {k} — {n[k]} righe", "",
              t[use].round(4).to_markdown(index=False), "",
              f"Predittori tenuti: **{', '.join(passati[k]) or 'nessuno'}**. "
              f"Massimo `t` = {t_max[k]:+.3f}, p del massimo su otto candidati "
              f"= {p_max[k]:.3f}; soglia di famiglia al 5% (Sidak) = "
              f"{PP.soglia_sidak():.2f}. In campione, sulle sole righe del "
              f"regime, il minimo `p_lr` e' {p_lr_min[k]:.3f} "
              f"(`{best_lr[k]}`), che sugli otto candidati vale "
              f"{p_lr_cor[k]:.2f}.", ""]

    L += [
        "---", "",
        "## 3. La potenza, cioe' cosa questi `t` possono dire", "",
        "Un `t` sotto soglia su cento righe non dice \"il predittore non "
        "serve\": dice \"questo test non l'avrebbe visto\". Le due frasi si "
        "distinguono solo calcolando contro quale effetto il test avrebbe "
        "avuto una probabilita' decente di rifiutare. Due alternative, "
        "entrambe dichiarate prima di guardare i risultati:", "",
        "- **contro il maturo**: l'effetto per riga che lo *stesso* predittore "
        "mostra sulle 660 righe. Se qui valesse quanto vale li', lo vedremmo?",
        "- **contro il proprio tetto in campione** (`potenza_vs_tetto`): il "
        "guadagno ottenuto sulle righe del regime con i coefficienti stimati "
        "**su quelle stesse righe**, meno i 0.5 punti che il sovradattamento "
        "regala comunque. Fuori campione non puo' rendere di piu'.",
        "",
        f"| regime | righe | `se` per riga di `{rif}` | MDE per riga | "
        "potenza contro il miglior effetto maturo |",
        "|---|---|---|---|---|",
    ]
    for k in ("maturo", "acerbo", "acerbo disgiunto"):
        L.append(f"| {k} | {n[k]} | {se_rif[k]:.5f} | "
                 f"{PP.effetto_minimo(se_rif[k]):.5f} | **{pot_comune[k]:.0%}** |")

    L += [
        "",
        f"L'alternativa comune e' l'effetto per riga di `{rif}` nel regime "
        f"maturo ({delta_rif:+.5f}), il piu' grande che gli otto candidati "
        "abbiano mai prodotto su questi dati; l'errore standard e' quello di "
        f"`{rif}` **in ciascun regime**, non la media degli otto, che sarebbe "
        "dominata dai candidati a varianza minuscola e descriverebbe un test "
        "mai fatto.", "",
        f"Il {pot_comune['maturo']:.0%} del regime maturo non e' una notizia "
        f"indipendente: li' l'alternativa **coincide** con l'effetto osservato, "
        f"quindi quella potenza e' solo un altro modo di scrivere t = "
        f"{float(best_maturo['t']):.2f}. I numeri informativi sono gli altri "
        "due — ed e' esattamente il punto: la Fase 2 aveva concluso con un "
        "test che, contro il migliore dei propri effetti, rifiutava una volta "
        f"su {1 / pot_comune['maturo']:.0f}. La differenza fra i regimi non e' "
        "che uno e' potente e l'altro no; e' che nessuno dei due lo e', e "
        "l'unica cosa conclusiva del blocco e' il test in campione della "
        "sezione 2.", "",
        "Le colonne `potenza_vs_maturo` delle tabelle sopra usano invece "
        "l'effetto di **ciascun** predittore, e sono quasi tutte piu' basse "
        "ancora, perche' quasi tutti gli effetti maturi sono vicini a zero o "
        "negativi. Contro un'alternativa negativa la potenza scende **sotto** "
        f"il pavimento {PP.potenza(0.0, 1.0):.1%}, ed e' corretto cosi': quel "
        "test non cerca un peggioramento.", "",
        f"Un'ultima lettura, che va contro l'intuizione: il MDE per riga di "
        f"`{rif}` passa da {PP.effetto_minimo(se_rif['maturo']):.5f} nel maturo "
        f"a {PP.effetto_minimo(se_rif['acerbo']):.5f} nell'acerbo, cioe' "
        f"×{rap_mde:.1f}, mentre la sola perdita di righe "
        f"({n['maturo']} → {n['acerbo']}) ne giustificherebbe ×{rap_n:.1f}. La "
        f"variabilita' per riga della differenza di log-verosimiglianza e' "
        f"quindi **{verso}** nelle prime giornate: {chiusa}.", "",
        "---", "",
        "## 4. La premessa del blocco, verificata: baseline stupidi accanto", "",
        "L'ipotesi da testare e' che i predittori paghino **dove l'effetto "
        "attacco e' debolmente identificato**. Che il regime acerbo sia "
        "davvero quel posto non va assunto: si guarda quanto il modello stacca "
        "i baseline li' dentro, contro quanto li stacca a stagione matura.", "",
    ]
    for k in ("maturo", "acerbo", "acerbo disgiunto"):
        L += [f"### Regime {k}", "",
              ctx[k].round(4).to_markdown(), ""]

    def _riga(regime, baseline):
        return (float(ctx[regime].loc[baseline, "d_loglik_vs_modello"])
                / n[regime])

    L += [
        "I due confronti che contano dicono cose diverse, e vanno riportati "
        "tutti e due:", "",
        f"- contro **`media campionato`**, cioe' l'intero contenuto "
        f"informativo del modello: {_riga('acerbo', 'media campionato'):+.4f} "
        f"per riga nell'acerbo contro "
        f"{_riga('maturo', 'media campionato'):+.4f} nel maturo, e nel regime "
        f"disgiunto **{_riga('acerbo disgiunto', 'media campionato'):+.4f}**, "
        "cioe' alle partite 4-5 il modello e' *peggio* del numero unico per "
        "tutti. **La premessa del blocco regge**: li' l'effetto attacco vale "
        "poco o niente, ed e' esattamente il posto in cui un predittore "
        "avrebbe spazio.",
        f"- contro **`{V.BEST_BASELINE}`**, cioe' il valore *incrementale* "
        f"della ridge sopra una media di squadra: {_riga('acerbo', V.BEST_BASELINE):+.4f} "
        f"per riga nell'acerbo contro {_riga('maturo', V.BEST_BASELINE):+.4f} "
        "nel maturo — qui il modello sta **meglio** da acerbo, non peggio. Non "
        "e' una contraddizione: con tre o quattro partite la media di squadra "
        "e' pessima e lo shrinkage della ridge vale molto, mentre a stagione "
        "matura le due cose convergono. Il primo confronto misura quanta "
        "informazione c'e', il secondo quanto serve regolarizzarla.",
        "",
        "Messi insieme: nelle prime giornate **c'e' meno informazione di "
        "squadra** — che e' la premessa — e nessuno dei candidati la "
        "sostituisce, nemmeno con i coefficienti scelti su quelle righe.", "",
        "Nota di lettura sui `t` di questa sezione: sono calcolati sulla "
        "log-verosimiglianza Poisson, come il test dei predittori. La Fase 2 "
        "riporta 1.86 contro "
        f"`{V.BEST_BASELINE}` perche' li' il confronto usa la NB2 con "
        "r = 26; e' la stessa quantita' misurata con due dispersioni diverse, "
        "non due risultati.", "",
        "---", "",
        "## Limiti di questo blocco", "",
        f"- **Il test acerbo ha potenza {pot_comune['acerbo']:.0%}, e da solo "
        "non conclude.** Il suo non-rifiuto e' compatibile sia con \"i "
        "predittori non servono nemmeno da acerbi\" sia con \"servono e queste "
        "righe non bastano a vederlo\". Cio' che permette di scegliere fra le "
        "due non e' il `t`, e' il test in campione — e va detto che vale solo "
        "**per questi otto predittori**, non per la classe delle medie mobili "
        "da dati evento in generale.",
        f"- **Anche il test maturo aveva potenza {pot_comune['maturo']:.0%}** "
        "contro il migliore dei propri effetti. Il \"nessuno passa\" di Fase 2 "
        "resta corretto, ma la sua forza veniva dal fatto che gli effetti "
        "misurati erano piccoli, non dal fatto che il test fosse sensibile. "
        "Questo blocco corregge la lettura, non il risultato.",
        "- **Il regime acerbo e' troncato alle partite 4-8** (le prime tre non "
        "hanno previsione) e **si sovrappone** al maturo su 6-8. Il regime "
        f"disgiunto elimina la sovrapposizione ma scende a "
        f"{n['acerbo disgiunto']} righe, con potenza "
        f"{pot_comune['acerbo disgiunto']:.0%}: e' un controllo, non un test.",
        "- **Tre regimi sono tre sguardi sugli stessi otto candidati.** La "
        "correzione riportata copre gli otto candidati dentro un regime, come "
        "in Fase 2, non i regimi fra loro. Non e' stato necessario stringerla "
        "perche' nessun `t` si e' avvicinato alla soglia: se uno l'avesse "
        "superata, andrebbe ripesato su tutta la famiglia.",
        "- **I candidati non sono indipendenti** — possesso, field tilt e "
        "tocchi in area misurano cose vicine. La correzione per il massimo "
        "assume indipendenza ed e' quindi **piu' severa del vero**; con "
        "correlazione positiva il p del massimo reale sarebbe piu' alto, cioe' "
        "ancora meno favorevole a una scoperta.",
        "- **`alpha` nelle prime giornate e' il valore centrale della griglia**, "
        "non una scelta: la selezione cumulativa non ha ancora storia "
        "sufficiente. E' lo stesso comportamento del modello base e dei "
        "candidati, quindi il confronto appaiato resta valido, ma il regime "
        "acerbo non e' un regime in cui `alpha` sia stato ottimizzato.",
        "- **Il test in campione e' in campione.** Stima il coefficiente sulle "
        "righe su cui poi lo giudica: se avesse rifiutato, non avrebbe "
        "dimostrato valore predittivo, e non andrebbe usato in nessuna "
        "affermazione sul modello. Vale come **limite superiore**, cioe' solo "
        "nella direzione in cui e' stato usato qui. Ed e' un limite per "
        "*questa* specificazione: non esclude che una trasformazione diversa "
        "dello stesso predittore abbia un coefficiente utile.",
        "- **`xg_per_shot` resta scartato.** Testato in un regime diverso, non "
        "reintrodotto. Fuori campione non si avvicina alla soglia in nessuno "
        "dei tre regimi; in campione, sulle 40 righe del disgiunto, e' il solo "
        "candidato con un p sotto 0.05 prima della correzione per la "
        "molteplicita' — e sopra dopo. Riportato perche' e' il risultato, non "
        "perche' cambi la conclusione.",
    ]
    if riproduce is not None:
        L += [f"- **Controllo di riproducibilita'**: il regime maturo "
              f"ricalcolato qui riproduce `phase2_predittori.csv` con uno "
              f"scarto massimo sul `t` di {riproduce:.1e}. Se un giorno "
              "divergesse, i due esiti non sarebbero piu' confrontabili e "
              "questo report non andrebbe letto."]

    path = config.REPORTS / "phase6_predittori.md"
    path.write_text("\n".join(L), encoding="utf-8")

    for k in ("maturo", "acerbo", "acerbo disgiunto"):
        print(f"  {k:18s} n={n[k]:4d}  t_max={t_max[k]:+5.2f}  "
              f"tenuti={len(passati[k])}  potenza={pot_comune[k]:.0%}")
    print(f"  report -> {path.relative_to(config.ROOT)}")


if __name__ == "__main__":
    main(force="--force" in sys.argv)
