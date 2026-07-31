# -*- coding: utf-8 -*-
"""Fase 6E — il calendario 2026-27 non e' quello 2025-26.

    python scripts/run_phase6e.py

Scrive `reports/phase6_calendario.md`. **Non cambia nessun numero pubblicato**:
la proiezione resta 5.03 / 191 / [151, 240]. Il blocco stabilisce quale insieme
di avversari il codice usa, misura quanto vale il ricambio di tre squadre su
venti con un intervallo dichiarato per la difesa delle promosse, e aggiunge
alla lista dei limiti la congestione infrasettimanale, che non viene stimata.

Prerequisiti: `run_phase1.py` (tabelle) e `run_phase2.py`
(`walkforward_base.parquet`, da cui si stima `r`).
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sot import (aggregate, calendar_2627 as CAL, config,  # noqa: E402
                 dispersion as D, level_chain as LC, model_player as MP,
                 project_2627 as P, squad_2627 as SQ)

N_SIM = 20000


def main() -> None:
    print("Fase 6E — calendario 2026-27 e insieme degli avversari")
    tm = aggregate.load_team_match()
    pm = aggregate.load_player_match()

    wf_path = config.PROCESSED / "walkforward_base.parquet"
    if not wf_path.exists():
        raise SystemExit("manca walkforward_base.parquet: esegui prima run_phase2.py")
    wfd = pd.read_parquet(wf_path)
    r = D.fit_r(wfd["sot"].to_numpy(), wfd["lam"].to_numpy())

    tau = float(MP.select_tau(MP.with_context(pm, tm)).iloc[0]["tau"])
    proj, s, model, _ = P.build_projection(pm, tm, tau=tau)

    # --- proiezione pubblicata, per il confronto ---
    sim = P.monte_carlo(proj, s, model, r, n_sim=N_SIM)
    p10, p50, p90 = np.percentile(sim, [10, 50, 90])

    cl = CAL.classifica(tm)
    uscite = CAL.retrocesse(tm)
    liv = CAL.livelli_difensivi(tm)
    tab = CAL.scenari_promosse(tm)
    eff = CAL.effetto_su_proiezione(proj, s, model, r, tab, n_sim=N_SIM)
    eff["equiv_rho"] = [CAL.equivalente_in_rho(f, tm) for f in eff["fattore"]]

    rho = LC.rho_implicito(tm)
    media_lega = float(tm["sot"].mean())

    # Estremi dell'intervallo dichiarato, su entrambe le scale insieme.
    estremi = eff[eff["scenario"].isin(("media di campionato",
                                        "peggiore difesa 2025-26"))]
    s_min, s_max = float(estremi["stagione"].min()), float(estremi["stagione"].max())
    f_min, f_max = float(estremi["fattore"].min()), float(estremi["fattore"].max())
    emp = eff[eff["scenario"] == "coorte promossa 2025-26"]

    def _righe(df, cols):
        return df[cols].round(4).to_markdown(index=False)

    L = [
        "# Fase 6E — il calendario 2026-27 non e' quello 2025-26", "",
        "La proiezione parla del Como contro \"una difesa media\". Nel 2026-27 "
        "tre promosse sostituiscono tre retrocesse, e delle promosse questi dati "
        "non sanno niente. Prima di stimare qualunque cosa: **che cosa fa il "
        "codice oggi?**", "",
        "## Esito in breve", "",
        "1. **Il codice contiene tutte e due le convenzioni, e nessuna delle due "
        "entra nel livello pubblicato.** `ratings_per_campo` usa l'avversario "
        "medio (e' `fig5`), `como_context` usa l'insieme reale 2025-26 — ma dalla "
        "Fase 6A sappiamo che il contesto di squadra si semplifica dentro "
        "`monte_carlo`. L'insieme di avversari entra per una terza via, implicita: "
        f"`rho` ancora il livello al **tasso grezzo del Como 2025-26**, che e' un "
        "numero ottenuto contro l'insieme 2025-26. **Il calendario 2026-27 non "
        "compare in nessun punto del codice.**",
        f"2. **Lo status quo non e' \"avversario medio\": e' \"le promosse "
        "difendono come le retrocesse\"**, e sotto quell'ipotesi il fattore di "
        f"calendario vale 1 esattamente. Le tre retrocesse ({', '.join(uscite)}) "
        f"hanno concesso in media {float(liv.loc[list(uscite), 'grezzo'].mean()):.3f} "
        f"tiri in porta a partita contro {media_lega:.3f} di campionato: **il trio "
        "che esce e' gia' fra i piu' battuti**, quindi il segno dell'effetto non "
        "e' nemmeno determinato.",
        f"3. **L'intervallo dichiarato sposta la proiezione fra {s_min:.0f} e "
        f"{s_max:.0f} tiri di stagione** (fattore da {f_min:.4f} a {f_max:.4f}), "
        f"contro i {p50:.0f} pubblicati e un intervallo di credibilita' largo "
        f"{p90 - p10:.0f}. E' {abs(s_max - s_min) / (p90 - p10):.0%} di "
        "quell'ampiezza, e meno della meta' di quanto vale la griglia di `rho` "
        "(19 tiri). Il riferimento empirico — l'unica coorte di neopromosse "
        f"osservabile, quella del 2025-26 — vale "
        f"{emp['stagione'].min():.0f}-{emp['stagione'].max():.0f}.",
        "4. **Nessuna correzione e' stata applicata**, e non per prudenza: "
        "sarebbe un doppio conteggio. 4.90 esce da un modello di persistenza su "
        "21 stagioni, e in 21 stagioni ci sono 21 ricambi di neopromosse — quel "
        "livello contiene gia' un calendario che cambia tre squadre l'anno. La "
        "correzione legittima sarebbe solo lo scarto fra il trio 2026-27 e un "
        "trio *tipico*, e con una coorte sola un trio tipico non e' "
        "caratterizzabile.",
        "5. **La congestione infrasettimanale e' un limite, non un numero.** "
        "Oggi la Champions e' modellata solo sui minuti; l'effetto sul lambda di "
        "squadra manca del tutto. Non e' stimato qui — il Como 2025-26 non "
        "giocava le coppe, quindi il campione non contiene una sola sua partita "
        "congestionata — e il segno atteso e' **negativo**: su questo asse la "
        "proiezione e' ottimistica.",
        "",
        "---", "",
        "## 1. Quale insieme di avversari usa il codice", "",
        "| modulo | funzione | insieme | dove finisce |", "|---|---|---|---|",
    ]
    L += [f"| `{m}` | `{f}` | {i} | {d} |" for m, f, i, d in CAL.INSIEMI_AVVERSARI]
    L += [
        "",
        "Le prime due righe sono le due convenzioni possibili, entrambe presenti. "
        "La quarta e' quella che conta davvero, ed e' la meno visibile: nessuno "
        "sceglie un insieme di avversari, ma il livello e' ancorato a un tasso "
        "grezzo che quell'insieme lo ha gia' incorporato. La quinta e' il fatto "
        "negativo del blocco — **non esiste, in nessun modulo, il calendario "
        "2026-27**.", "",
        "---", "",
        "## 2. Chi esce e chi entra", "",
        "Le tre retrocesse si ricavano dai dati (punti dai gol delle righe "
        "partita, nessuna informazione esterna). Ultime sei posizioni:", "",
        cl.tail(6)[["posizione", "team", "punti", "gf", "gs", "dr"]]
          .to_markdown(index=False),
        "",
        f"Retrocedono **{', '.join(uscite)}**. Nessuna coppia in zona "
        "retrocessione e' a pari punti, quindi l'ordinamento non dipende dai "
        "criteri di spareggio.", "",
        "Chi entra non e' deducibile da questi dati: la Serie B non e' nel "
        "repository. Quello che serve non e' comunque l'identita' delle promosse "
        "ma il loro **livello difensivo**, che e' la grandezza su cui si "
        "dichiara l'intervallo.", "",
        "### I livelli difensivi delle venti squadre 2025-26", "",
        "Due scale affiancate, e nessuna delle due e' la risposta da sola: i "
        "coefficienti del modello sono quelli che entrano davvero nel lambda ma "
        "la ridge li comprime (pendenza 0.760 sui livelli, Fase 6A), quindi "
        "**sottostimano** qualunque ricambio; i tiri concessi grezzi non sono "
        "compressi ma dentro hanno anche chi la squadra ha affrontato.", "",
        liv.round(4).reset_index().rename(columns={"index": "team"})
           .to_markdown(index=False),
        "",
        "---", "",
        "## 3. Quanto vale il ricambio", "",
        "Il Como affronta 19 avversari, ciascuno una volta in casa e una in "
        "trasferta. La difesa entra moltiplicativamente nel lambda, quindi il "
        "fattore di calendario e' un rapporto fra somme:", "",
        "```",
        "F = [ somma sui 16 che restano + 3 x c_promossa ] / [ somma sui 19 del 25-26 ]",
        "```", "",
        "Il termine di campo compare identico sopra e sotto e si semplifica: `F` "
        "non dipende dalla scala di campo, e un test lo verifica. Gli scenari "
        "sono dichiarati in anticipo (`calendar_2627.SCENARI`): i primi due sono "
        "gli **estremi dell'intervallo**, il terzo lo status quo, il quarto un "
        "riferimento empirico.", "",
        _righe(eff, ["scala", "scenario", "c_promossa", "fattore",
                     "livello_implicato", "stagione", "q10", "q90", "equiv_rho"]),
        "",
        "Come leggerla:", "",
        "- **`come le retrocesse` da' fattore 1.0000 per costruzione**, ed e' "
        "l'ipotesi che il codice fa oggi senza dichiararla. Non e' un'ipotesi "
        "neutra: e' l'ipotesi che le promosse siano porose quanto le tre squadre "
        "peggiori del campionato precedente. Le sue due righe riproducono "
        f"esattamente la proiezione pubblicata ({p50:.0f}, "
        f"[{p10:.0f}, {p90:.0f}]): e' il controllo che il resto della tabella "
        "esca dalla stessa macchina e non da un calcolo parallelo.",
        "- **`media di campionato` e' l'unico scenario che abbassa la "
        "proiezione**, e lo fa perche' assume promosse forti come una squadra "
        "qualunque di Serie A. Storicamente le neopromosse stanno sotto la media, "
        "quindi e' un limite dell'intervallo, non uno scenario plausibile.",
        f"- **Il riferimento empirico sta dalla parte opposta**: la coorte "
        f"promossa nel 2025-26 ({', '.join(CAL.PROMOSSE_2526)}) ha concesso piu' "
        "delle retrocesse, quindi il fattore sale sopra 1. **E' una coorte sola** "
        "e la sua identita' e' informazione esterna, dichiarata in "
        "`PROMOSSE_2526`: non e' una stima di come difenderanno le promosse del "
        "2026-27.",
        "- **La scala grezza da' sempre un effetto piu' grande di quella del "
        "modello**, in tutti e quattro gli scenari. E' la compressione della "
        "ridge vista da un'altra angolazione: gli stessi coefficienti che "
        "schiacciano le squadre di vertice verso la media schiacciano anche le "
        "difese peggiori, e quindi riducono lo scarto fra chi esce e chi entra.",
        "- **L'ultima colonna mette il calendario sulla scala di `rho`**: "
        "l'intero intervallo vale "
        f"{eff['equiv_rho'].max() - eff['equiv_rho'].min():.3f} di `rho`, contro "
        f"i 0.45 della griglia dichiarata in Fase 6C. **Il calendario e' la piu' "
        "piccola delle assunzioni non stimabili del progetto**, non la piu' "
        "grande.",
        "",
        "---", "",
        "## 4. Perche' il numero pubblicato non e' stato corretto", "",
        "Non per prudenza: **sarebbe un doppio conteggio**. Il livello 4.90 esce "
        "da un modello di persistenza su 21 stagioni (`config.py`), e in 21 "
        "stagioni ci sono 21 ricambi di neopromosse: quella media storica "
        "contiene gia' un calendario che cambia tre squadre l'anno. L'unica "
        "correzione legittima sarebbe lo scarto fra il trio 2026-27 e un trio "
        "**tipico** — e per caratterizzare un trio tipico serve piu' di una "
        "coorte, che e' esattamente quello che qui manca.", "",
        "`effetto_su_proiezione` esiste per quantificare il limite e **non e' "
        "chiamata da nessuno script della proiezione**: `run_phase3.py` e "
        f"`run_phase5.py` continuano a stampare {p50:.0f} tiri di stagione, "
        f"IC80% [{p10:.0f}, {p90:.0f}].", "",
        "---", "",
        "## 5. La congestione infrasettimanale: limite, non numero", "",
        "| voce | contenuto |", "|---|---|",
    ]
    L += [f"| {k} | {v} |" for k, v in CAL.LIMITE_CONGESTIONE.items()]
    L += [
        "",
        "La rotazione per la Champions e' modellata sui **minuti** — chi scende "
        "in campo, con `ROTATION_DEFAULT` 0.15 variato fra 0.05 e 0.25 nel Monte "
        "Carlo. Ma la congestione agisce anche a **parita' di undici schierato**: "
        "recupero incompleto, gestione del ritmo, meno transizioni ad alta "
        "intensita'. Quell'effetto oggi nel modello non c'e' per niente.", "",
        "**Non e' stimato qui, ed e' una scelta dichiarata**: il Como 2025-26 non "
        "giocava le coppe europee, quindi in questo campione non esiste una sola "
        "partita del Como dopo un turno infrasettimanale. Stimarlo dalle altre "
        "squadre italiane impegnate in Europa e' un'altra domanda, con un altro "
        "disegno, e va al piano dati (blocco 6F) — non a questo blocco.", "",
        "**Il segno atteso e' negativo**: a parita' di tutto il resto una squadra "
        "che gioca infrasettimanale produce meno, non di piu'. Quindi la "
        "proiezione, su questo asse, e' **ottimistica**. Se un giorno il fattore "
        "venisse stimato entrerebbe come moltiplicatore sull'ancora del livello, "
        "cioe' dallo stesso ingresso di `rho`: e' l'unico punto da cui il livello "
        "si muove (Fase 6A).", "",
        "---", "",
        "## Limiti di questo blocco", "",
        "- **L'intervallo sulle promosse e' dichiarato, non stimato.** I due "
        "estremi sono calcolati da questi dati ma *scelti* come estremi: nessuno "
        "dei due e' escluso, e nessuno dei due ha una probabilita' attaccata.",
        "- **Il riferimento empirico e' una coorte sola.** Tre squadre, una "
        "stagione, e la loro identita' e' informazione esterna al repository.",
        "- **Il fattore assume che l'attacco del Como non cambi** in funzione "
        "dell'avversario oltre a quanto il modello moltiplicativo prevede: "
        "nessuna interazione fra forza dell'attacco e forza della difesa e' "
        "stimata, e con una stagione sola non sarebbe identificabile.",
        f"- **La scala del modello e' compressa.** La colonna `modello` "
        "sottostima il ricambio di un fattore che la Fase 6A ha misurato sui "
        "livelli d'attacco (pendenza 0.760) ma **non** sulle difese: qui non e' "
        "stata rimisurata, e il divario fra le due scale va letto come un "
        "intervallo, non come un errore dell'una o dell'altra.",
        f"- `tau` = {tau:g}, `alpha` = 12.0, `r` = {r:.1f} e `rho` = {rho:.3f} "
        "sono quelli delle fasi precedenti, non ristimati qui.",
    ]

    path = config.REPORTS / "phase6_calendario.md"
    path.write_text("\n".join(L), encoding="utf-8")

    print(f"  retrocesse: {', '.join(uscite)}")
    print(f"  fattore di calendario nell'intervallo dichiarato: "
          f"{f_min:.4f} - {f_max:.4f}")
    print(f"  stagione: da {s_min:.0f} a {s_max:.0f} (pubblicata {p50:.0f}, "
          f"IC80% [{p10:.0f}, {p90:.0f}])")
    print(f"  equivalente in rho: {eff['equiv_rho'].min():+.3f} / "
          f"{eff['equiv_rho'].max():+.3f}")
    print(f"  congestione: non stimata, segno atteso "
          f"{CAL.LIMITE_CONGESTIONE['segno_atteso']:+d}")
    print(f"  report -> {path}")


if __name__ == "__main__":
    main()
