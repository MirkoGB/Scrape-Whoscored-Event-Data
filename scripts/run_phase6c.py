# -*- coding: utf-8 -*-
"""Fase 6C — shrinkage entro stagione contro shrinkage fra stagioni.

    python scripts/run_phase6c.py

Scrive `reports/phase6_rho.md` e `reports/figures/fig8_rho.png`. Non cambia
nessun numero pubblicato: alla `rho` implicita la proiezione resta 5.03 / 191 /
[151, 240].

`alpha` e' scelto in walk-forward per prevedere la partita t+1: e' shrinkage
**entro** la stagione. La proiezione fa un'altra cosa — prevedere il 2026-27
dato il 2025-26 — e la persistenza fra stagioni e' piu' bassa. Con una stagione
sola il coefficiente giusto non e' stimabile e qui **non si prova**: si
parametrizza (`rho`) e si mostra la sensibilita'.

Prerequisiti: `run_phase1.py` (tabelle) e `run_phase2.py`
(`walkforward_base.parquet`, da cui si stima `r`).
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sot import (aggregate, config, dispersion as D, figures as F,  # noqa: E402
                 level_chain as LC, model_player as MP, project_2627 as P,
                 squad_2627 as SQ)

N_SIM = 20000


def main() -> None:
    print("Fase 6C — sensibilita' alla persistenza fra stagioni")
    tm = aggregate.load_team_match()
    pm = aggregate.load_player_match()

    wf_path = config.PROCESSED / "walkforward_base.parquet"
    if not wf_path.exists():
        raise SystemExit("manca walkforward_base.parquet: esegui prima run_phase2.py")
    wfd = pd.read_parquet(wf_path)
    r = D.fit_r(wfd["sot"].to_numpy(), wfd["lam"].to_numpy())

    tau = float(MP.select_tau(MP.with_context(pm, tm)).iloc[0]["tau"])
    proj, s, model, _ = P.build_projection(pm, tm, tau=tau)

    rho = LC.rho_implicito(tm)
    comp = LC.compressione_ratings(tm)
    media_lega = float(tm["sot"].mean())
    grezzo = float(tm.loc[tm["team"] == "Como", "sot"].mean())
    eccesso = grezzo - media_lega

    tab = LC.sensibilita_rho(proj, s, model, r, tm, n_sim=N_SIM)
    pend = LC.pendenza_su_rho(tab)

    ht = P.first_half_test(pm, tm, tau=tau)
    corr_meta = float(np.corrcoef(ht["topdown"], ht["actual_h2"])[0, 1])

    # Proiezione pubblicata: stessa simulazione, ancora al riferimento.
    sim = P.monte_carlo(proj, s, model, r, n_sim=N_SIM)
    q10, q50, q90 = np.percentile(sim, [10, 50, 90])
    ancora = s["ratio"] * config.REF_TOPDOWN_PER_MATCH
    f_mc = (q50 / SQ.N_MATCHES) / ancora
    # Pendenza esatta sull'ancora: il livello entra per moltiplicazione, quindi
    # d(stagione)/d(rho) = 38 x rapporto x convessita' x eccesso grezzo.
    pend_esatta = SQ.N_MATCHES * s["ratio"] * f_mc * eccesso

    fig = F.proiezione_per_rho(tab, rho, pubblicato=q50)
    fig_path = config.FIGURES / "fig8_rho.png"
    fig.savefig(fig_path, facecolor=fig.get_facecolor(), bbox_inches="tight")
    import matplotlib.pyplot as plt
    plt.close(fig)

    estremi = tab.iloc[[0, -1]]

    L = [
        "# Fase 6C — shrinkage entro stagione contro shrinkage fra stagioni", "",
        "`alpha` e' scelto per prevedere la partita t+1 date le precedenti: e' "
        "shrinkage **entro** la stagione. La proiezione risponde a un'altra "
        "domanda — il 2026-27 dato il 2025-26 — e su quell'orizzonte la "
        "persistenza e' piu' bassa, quindi lo shrinkage corretto e' piu' forte. "
        "Anche il test 1o/2o tempo e' interno alla stagione e sovrastima la "
        "persistenza per costruzione. **Con una stagione sola il coefficiente "
        "giusto non e' stimabile, e qui non si prova a stimarlo.**", "",
        "## Esito in breve", "",
        f"1. **La proiezione pubblicata assume rho = {rho:.3f}**, cioe' che il "
        f"Como trattenga l'{rho:.1%} del proprio eccesso sulla media di "
        "campionato passando da una stagione all'altra. Non e' un'ipotesi fatta "
        "qui: e' ricavata dai numeri della Fase 6A, e "
        f"`livello_da_rho({rho:.6f})` restituisce esattamente "
        f"{config.REF_TOPDOWN_PER_MATCH}.",
        f"2. **Ogni 0.05 di rho vale circa {pend['per_005']:.1f} tiri in porta "
        f"di stagione** ({pend_esatta * 0.05:.2f} sull'ancora, "
        f"{pend['per_005']:.2f} sulla mediana simulata, che e' un intero e "
        "quindi si muove a scalini). Sull'intera griglia dichiarata "
        f"0.50-0.95 la proiezione va da {estremi.iloc[0]['stagione']:.0f} a "
        f"{estremi.iloc[1]['stagione']:.0f}, cioe' "
        f"{estremi.iloc[1]['stagione'] - estremi.iloc[0]['stagione']:.0f} tiri "
        "in porta.",
        f"3. **Il valore corretto non e' determinabile con questi dati.** Serve "
        "piu' di una stagione: rho e' una persistenza fra stagioni e con una "
        "stagione sola non ha nemmeno un campione su cui essere calcolata. "
        f"L'intera griglia sposta la proiezione di "
        f"{estremi.iloc[1]['stagione'] - estremi.iloc[0]['stagione']:.0f} tiri, "
        f"contro un intervallo di credibilita' largo {q90 - q10:.0f} "
        f"([{q10:.0f}, {q90:.0f}]): "
        f"{(estremi.iloc[1]['stagione'] - estremi.iloc[0]['stagione']) / (q90 - q10):.0%} "
        "di quell'ampiezza. Non e' il termine dominante dell'incertezza, ma "
        "non e' trascurabile — e a differenza degli altri e' un'assunzione, "
        "non un rumore.",
        "",
        "---", "",
        "## 1. Che cos'e' `rho` e da dove viene il suo default", "",
        "```",
        "livello = media_lega + rho * (grezzo della squadra - media_lega)",
        "```", "",
        "E' la quota di eccesso sulla media di campionato che la squadra "
        "trattiene passando da una stagione all'altra. Sulla scala di "
        "calendario, dove vivono i tassi grezzi di stagione e il livello usato:",
        "",
        "| grandezza | valore |", "|---|---|",
        f"| media di campionato 2025-26 | {media_lega:.4f} |",
        f"| Como grezzo 2025-26 | {grezzo:.4f} |",
        f"| eccesso del Como | {eccesso:.4f} |",
        f"| livello usato nella proiezione | {config.REF_TOPDOWN_PER_MATCH:.4f} |",
        f"| eccesso del livello usato | "
        f"{config.REF_TOPDOWN_PER_MATCH - media_lega:.4f} |",
        f"| **rho implicito** | **{rho:.4f}** |",
        "",
        "Il default **non e' stato scelto**: e' quello che il livello 4.90 gia' "
        "assumeva, letto dai numeri della sezione 4 di Fase 6A (eccesso usato "
        f"{comp['eccesso_usato']:.4f} contro eccesso grezzo "
        f"{comp['eccesso_grezzo']:.4f} sulla scala di trasferta, rapporto "
        f"{comp['rho_implicito']:.4f}). La grandezza e' invariante rispetto "
        "alla scala di campo, perche' le tre scale differiscono per lo stesso "
        "fattore moltiplicativo: calcolata sulla scala di calendario da' lo "
        "stesso numero, e un test lo verifica.", "",
        "**Attenzione a non confonderlo con la compressione della ridge.** Sono "
        "due cose diverse che agiscono nella stessa direzione:", "",
        f"- la ridge comprime i rating **dentro** la stagione con pendenza "
        f"{comp['pendenza']:.3f}: e' una proprieta' dello stimatore, misurata "
        "in campione (Fase 6A, sezione 4);",
        f"- `rho` = {rho:.3f} e' un'assunzione sul **futuro**: quanto di quello "
        "che una squadra ha fatto si ripete l'anno dopo. Nessuno dei due e' "
        "stimato dall'altro.",
        "",
        "---", "",
        "## 2. La proiezione lungo la griglia di rho", "",
        f"Griglia dichiarata in anticipo (`level_chain.RHO_GRID`): "
        f"{LC.RHO_GRID[0]:.2f}-{LC.RHO_GRID[-1]:.2f} a passi di 0.05. Cambia "
        "**solo** l'ancora del livello: rapporto compositivo, Monte Carlo, "
        f"seed e fonti di incertezza restano quelli pubblicati, {N_SIM} "
        "simulazioni ciascuna.", "",
        tab.round(4).to_markdown(index=False),
        "",
        f"![Proiezione in funzione di rho](figures/fig8_rho.png)", "",
        f"Pendenza sulla griglia: **{pend['per_unita']:.1f}** tiri di stagione "
        f"per unita' di rho, cioe' **{pend['per_005']:.2f} per ogni 0.05** "
        f"(R2 {pend['r2']:.4f}; i residui sono a scalini perche' la mediana "
        "simulata e' un intero). Sull'ancora, dove la relazione e' esattamente "
        f"lineare, la pendenza vale {pend_esatta:.1f} per unita' e "
        f"{pend_esatta * 0.05:.2f} per 0.05.",
        "",
        "---", "",
        "## 3. Perche' non si prova a stimare rho", "",
        "Con una stagione sola non esiste il campione su cui stimarlo. Le due "
        "quantita' che il progetto ha gia' misurato e che potrebbero sembrare "
        "candidate **non lo sono**:", "",
        f"- **`alpha` = 12.0** e' scelto in walk-forward per minimizzare "
        "l'errore sulla partita successiva. E' persistenza fra partite della "
        "stessa stagione, con la stessa rosa e lo stesso allenatore.",
        f"- **Il test 1o/2o tempo** (Fase 6B) misura la persistenza fra due "
        f"meta' della stessa stagione: correlazione {corr_meta:.3f}. E' un "
        "limite superiore per la persistenza fra stagioni, non una sua stima: "
        "fra due meta' di stagione non cambiano ne' la rosa ne' l'allenatore "
        "ne' la categoria.",
        "",
        "Il riferimento fornito dichiara di venire da un modello di persistenza "
        "su 21 stagioni con coefficienti 0.591 sull'ultima stagione e 0.247 "
        "sulla penultima (`config.py`). Se fossero i coefficienti di "
        f"un'autoregressione sui livelli, la loro somma (0.838) starebbe vicino "
        f"al rho implicito qui ricavato ({rho:.3f}). **Non e' una conferma**: "
        "quelle stagioni non sono nel repository, il calcolo non esiste in "
        "nessun modulo, e non e' nemmeno detto che i due coefficienti si "
        "applichino alla stessa parametrizzazione. Si segnala la vicinanza, "
        "non la si usa.",
        "",
        "---", "",
        "## Limiti di questo blocco", "",
        "- **Rho non e' stimato, e' parametrizzato.** La griglia 0.50-0.95 e' "
        "un intervallo dichiarato, non un intervallo di confidenza: nessuno dei "
        "suoi estremi e' escluso da questi dati.",
        "- **La sensibilita' e' solo sul livello.** L'ampiezza dell'intervallo "
        "resta quella ereditata dal riferimento (shock di squadra 65%, livello "
        "di campionato 6%): far variare rho sposta la proiezione, non la sua "
        "incertezza.",
        "- **Rho e' definito sulla singola squadra.** Qui e' calcolato sul "
        "Como; una stessa rho applicata a tutte le squadre non e' testata, e "
        "la letteratura sul ritorno alla media suggerisce che dipenda dal "
        "livello — ma verificarlo richiede piu' stagioni.",
        f"- `tau` = {tau:g}, `alpha` = 12.0 e `r` = {r:.1f} sono quelli delle "
        "fasi precedenti, non ristimati qui.",
    ]

    path = config.REPORTS / "phase6_rho.md"
    path.write_text("\n".join(L), encoding="utf-8")

    print(f"  rho implicito = {rho:.4f} -> livello "
          f"{LC.livello_da_rho(rho, tm):.4f} (riferimento "
          f"{config.REF_TOPDOWN_PER_MATCH})")
    print(f"  griglia {LC.RHO_GRID[0]:.2f}-{LC.RHO_GRID[-1]:.2f}: stagione da "
          f"{estremi.iloc[0]['stagione']:.0f} a {estremi.iloc[1]['stagione']:.0f}")
    print(f"  per 0.05 di rho: {pend['per_005']:.2f} tiri di stagione "
          f"({pend_esatta * 0.05:.2f} sull'ancora)")
    print(f"  figura -> {fig_path.relative_to(config.ROOT)}")
    print(f"  report -> {path}")


if __name__ == "__main__":
    main()
