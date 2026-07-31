# -*- coding: utf-8 -*-
"""Fase 6A — da dove viene il livello della proiezione.

    python scripts/run_phase6a.py

Scrive `reports/phase6_livello.md`: la catena aritmetica dal rating al numero
pubblicato, l'origine di 4.90 con l'inventario dei suoi usi, il gonfiamento del
Monte Carlo scomposto per fonte, e la compressione della ridge misurata come
pendenza. **Non cambia nessun numero pubblicato**: `run_phase3.py` e
`run_phase5.py` continuano a stampare 5.03 / 191 / [151, 240].

Prerequisiti: `run_phase1.py` (tabelle) e `run_phase2.py`
(`walkforward_base.parquet`, da cui si stima `r`).
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sot import (aggregate, config, dispersion as D, level_chain as LC,  # noqa: E402
                 model_player as MP, project_2627 as P, squad_2627 as SQ)

N_SIM = 20000


def _tab(df: pd.DataFrame, dec: int = 4) -> str:
    return df.round(dec).to_markdown(index=False)


def _f(infl: pd.DataFrame, fonte: str) -> float:
    """Scostamento dall'ancora della fonte accesa da sola, in frazione."""
    return float(infl.loc[infl["fonte"] == fonte, "fattore"].iloc[0]) - 1.0


def main() -> None:
    print("Fase 6A — la catena del livello")
    tm = aggregate.load_team_match()
    pm = aggregate.load_player_match()

    wf_path = config.PROCESSED / "walkforward_base.parquet"
    if not wf_path.exists():
        raise SystemExit("manca walkforward_base.parquet: esegui prima run_phase2.py")
    wfd = pd.read_parquet(wf_path)
    r = D.fit_r(wfd["sot"].to_numpy(), wfd["lam"].to_numpy())

    # tau dalla griglia unica di MP, come in Fase 3: nessuna griglia locale.
    tau = float(MP.select_tau(MP.with_context(pm, tm)).iloc[0]["tau"])
    proj, s, model, _ = P.build_projection(pm, tm, tau=tau)

    modello = LC.catena_modello(tm)
    pubblicato = LC.catena_pubblicata(proj, s, model, r, n_sim=N_SIM)
    infl = LC.inflazione_montecarlo(proj, s, model, r, n_sim=N_SIM)
    canc = LC.livello_non_dipende_dal_contesto(proj, s, model, r)
    comp = LC.compressione_ratings(tm)
    rat = LC.ratings_per_campo(tm)

    rif = config.REF_TOPDOWN_PER_MATCH
    ancora = s["ratio"] * rif
    pubblicato_pp = float(pubblicato.iloc[2]["valore_risultante"])
    pubblicato_st = float(pubblicato.iloc[3]["valore_risultante"])
    f_mc = float(pubblicato.iloc[2]["fattore"])
    f = comp["fattore_campo"]

    usi = pd.DataFrame(LC.USI_DEL_RIFERIMENTO,
                       columns=["punto", "cosa", "come viene usato"])

    # Verdetto sulla coerenza fra livello usato e pendenza: si scrive quello che
    # esce, non quello che farebbe comodo.
    d_imp = comp["decompressione_implicita"]
    d_pen = comp["decompressione_da_pendenza"]
    scarto = comp["livello_decompresso_calendario"] - rif
    coda = (f"({d_imp:.3f} contro {d_pen:.3f}). Sulla scala di calendario il "
            f"rating de-compresso vale {comp['livello_decompresso_calendario']:.3f} "
            f"contro il {rif} usato: {abs(scarto):.2f} tiri in porta a partita, "
            f"{abs(scarto) * SQ.N_MATCHES:.0f} in stagione")
    if d_imp > d_pen * 1.05:
        verdetto = ("il livello usato **de-comprime piu'** di quanto la pendenza "
                    "giustifichi " + coda)
    elif d_imp < d_pen * 0.95:
        verdetto = ("il livello usato **de-comprime meno** di quanto la pendenza "
                    "giustifichi " + coda + ", cioe' 4.90 sta fra il rating del "
                    "modello e il rating de-compresso, piu' vicino al primo")
    else:
        verdetto = ("il livello usato coincide, entro il 5%, con il rating "
                    "de-compresso dalla pendenza " + coda)

    L = [
        "# Fase 6A — da dove viene il livello della proiezione", "",
        "Ricostruzione della catena aritmetica che porta dal rating del modello "
        "al numero pubblicato. Nessuna moltiplicazione implicita. "
        "**Nessun numero pubblicato viene cambiato da questo blocco**: `alpha`, "
        "`tau` e i rating restano quelli delle Fasi 2-5.", "",
        "## Esito in breve", "",
        "1. **Il livello pubblicato non contiene il modello di squadra.** Il "
        "contesto si semplifica algebricamente dentro `monte_carlo`, e la prova "
        "numerica e' nella sezione 3: moltiplicando il contesto del Como per "
        f"{canc['k']} il numero pubblicato non cambia di un bit "
        f"(scarto massimo fra le due simulazioni: {canc['scarto_massimo']:.1f}). "
        "Rating, `alpha` e vantaggio del campo decidono **come** il lambda si "
        "ripartisce fra i giocatori, non **quanto** vale.",
        f"2. **4.90 e' un valore fornito, non ricostruibile da questi dati.** "
        "E' `config.REF_TOPDOWN_PER_MATCH`, dichiarato come modello di "
        "persistenza su 21 stagioni: quelle stagioni non sono nel repository e "
        "il calcolo non esiste in nessun modulo. Inventario dei suoi usi nella "
        "sezione 2.",
        f"3. **Il salto da {ancora:.2f} a {pubblicato_pp:.2f} e' tutto Monte "
        f"Carlo**: fattore {f_mc:.4f}, mai documentato prima. Con `sources=()` "
        f"la simulazione restituisce esattamente l'ancora {ancora:.4f}. E' "
        "convessita', non un ingrediente del modello. Ecco perche' "
        f"4.90 x {s['ratio']:.3f} faceva {ancora:.2f} e non {pubblicato_pp:.2f}.",
        f"4. **Il rating di `fig5` non e' a campo neutro**: e' il valore in "
        f"trasferta. Il Como fa {rat.set_index('team').loc['Como', 'neutro']:.3f} "
        f"in trasferta, {rat.set_index('team').loc['Como', 'casa']:.3f} in casa, "
        f"{rat.set_index('team').loc['Como', 'media_calendario']:.3f} di media su "
        "19 + 19. La definizione **non e' stata cambiata**: portarla al punto "
        "medio geometrico sposterebbe 4.34 verso 4.79, cioe' verso 4.90, ed e' "
        "esattamente il modo di far tornare i numeri che il progetto vieta.",
        f"5. **La ridge comprime con pendenza {comp['pendenza']:.3f} "
        f"(+- {comp['se_pendenza']:.3f})** rispetto ai tassi grezzi, e "
        f"{verdetto}.",
        "",
        "---", "",
        "## 1. Le due catene", "",
        "Sono due, e **non si toccano**. Il ramo del modello e' quello che "
        "questi dati sanno dire; il ramo pubblicato e' quello che finisce nel "
        "README.", "",
        "### Ramo A — il modello di squadra", "",
        _tab(modello),
        "",
        "L'ultima riga non e' un fattore applicato da nessuno: e' quanto resta "
        "fra la previsione in campione del modello e il tasso davvero "
        f"realizzato dal Como. Il modello sta sotto del "
        f"{(1 - float(modello.iloc[4]['valore_partenza']) / float(modello.iloc[4]['valore_risultante'])) * 100:.1f}% "
        "**sulla stagione che ha usato per stimare**, che e' il ritorno alla "
        "media della ridge visto da vicino (sezione 4).",
        "",
        "### Ramo B — il numero pubblicato", "",
        _tab(pubblicato),
        "",
        "### Ramo C — la ricomposizione per giocatore, che si semplifica", "",
        f"- contesto di squadra del Como (media delle 38 previsioni): "
        f"**{s['context_como']:.4f}**",
        f"- ricomposizione dal basso della rosa 2025-26 con i minuti reali: "
        f"**{s['lambda_bottomup_2526']:.4f}** "
        f"({(s['lambda_bottomup_2526'] / s['context_como'] - 1) * 100:+.1f}% "
        "rispetto al contesto: lo shrinkage al ruolo perde qualcosa per strada)",
        f"- ricomposizione della rosa 2026-27 con i minuti proiettati: "
        f"**{s['lambda_bottomup_2627']:.4f}**",
        f"- rapporto = **{s['ratio']:.6f}**",
        "",
        "Il contesto compare a numeratore e denominatore del rapporto e si "
        "semplifica: e' per questo che il ramo C entra nel ramo B solo con il "
        "rapporto, mai con un livello.",
        "",
        "---", "",
        "## 2. Da dove nasce 4.90", "",
        "**Non e' una stima di questo modello e non e' ricostruibile qui.** In "
        "`sot/config.py` e' dichiarato come proiezione top-down di riferimento, "
        "da un modello di persistenza su 21 stagioni con coefficienti 0.591 "
        "sull'ultima stagione e 0.247 sulla penultima. Quelle stagioni non "
        "esistono nel repository — i dati sono la sola 2025-26 — e nessun "
        "modulo contiene quel calcolo. Chi volesse verificarlo non puo' farlo "
        "con questo codice.", "",
        "Ogni punto in cui il riferimento entra nei calcoli:", "",
        _tab(usi),
        "",
        "**La riga da guardare e' `project_2627.py:157`**: li' il livello della "
        "proiezione viene fissato dal riferimento, e le due righe 50-51 fanno "
        "lo stesso con l'ampiezza dell'intervallo. Non c'e' niente di "
        "sbagliato nell'usare un'ancora esterna — quello che mancava era "
        "dichiararlo accanto al numero.", "",
        f"Coincidenza da segnalare, perche' e' probabilmente il motivo per cui "
        f"nessuno si e' accorto che la catena non era chiusa: il contesto del "
        f"Como calcolato dal modello vale **{s['context_como']:.4f}**, cioe' "
        f"{rif} a due decimali. Le due grandezze si somigliano ma non hanno "
        "alcun legame: una e' la media delle 38 previsioni in campione del "
        "2025-26, l'altra e' una previsione esterna per il 2026-27. "
        "L'uguaglianza e' un caso.",
        "",
        "---", "",
        "## 3. Il gonfiamento del Monte Carlo, fonte per fonte", "",
        _tab(infl, 5),
        "",
        "La prima riga e' il controllo che conta: senza nessuna fonte accesa la "
        f"simulazione restituisce l'ancora esatta ({ancora:.4f}), quindi non ci "
        "sono altri fattori nascosti oltre a quelli qui elencati.", "",
        f"Il gonfiamento totale vale **{f_mc:.4f}** e non e' uniforme fra le "
        f"fonti. L'incertezza sui tassi individuali pesa {_f(infl, 'player_rates'):+.2%}"
        f" e i nuovi arrivi {_f(infl, 'new_signings'):+.2%}: sono perturbazioni "
        "dentro una somma di esponenziali, quindi ne alzano il centro "
        f"(disuguaglianza di Jensen). L'incertezza sui minuti va invece "
        f"**nell'altro verso**, {_f(infl, 'minutes'):+.2%}: ridistribuire i "
        "minuti verso la rosa allargata li toglie a chi tira di piu', e il "
        "Como ha un tiratore che da solo vale il 21% del lambda. Gli shock "
        "lognormali e il campionamento hanno mediana centrata e non spostano "
        f"({_f(infl, 'team_shock'):+.2%}, {_f(infl, 'league_level'):+.2%}, "
        f"{_f(infl, 'sampling'):+.2%}). Le fonti non sono esattamente "
        "moltiplicative: accese insieme interagiscono.",
        "",
        "### Il contesto si semplifica: verifica numerica", "",
        f"- mediana con il contesto originale: **{canc['mediana_originale']:.1f}**",
        f"- mediana con il contesto moltiplicato per {canc['k']}: "
        f"**{canc['mediana_contesto_perturbato']:.1f}**",
        f"- scarto massimo fra le due simulazioni, simulazione per simulazione: "
        f"**{canc['scarto_massimo']:.1f}**",
        "",
        "Se il livello pubblicato dipendesse dal modello di squadra, "
        "moltiplicare il contesto per 1.5 lo cambierebbe del 50%. Non lo "
        "cambia affatto.",
        "",
        "---", "",
        "## 4. Quanto comprime la ridge", "",
        f"Regressione dei {comp['n']} rating sui tassi grezzi di stagione, "
        "riportati sulla stessa scala di campo (i grezzi vivono sulla scala di "
        f"calendario, i rating su quella di trasferta: si divide per "
        f"(1 + {f:.4f}) / 2 = {comp['scala_calendario_su_trasferta']:.4f}). "
        "**Descrittiva e in campione**: misura quanto la ridge comprime, non "
        "prevede niente.", "",
        f"| grandezza | valore |", "|---|---|",
        f"| pendenza | **{comp['pendenza']:.4f}** +- {comp['se_pendenza']:.4f} |",
        f"| intercetta | {comp['intercetta']:.4f} |",
        f"| R2 | {comp['r2']:.4f} |",
        "",
        "La pendenza sotto 1.0 e' il fenomeno: un tiro in porta di eccesso "
        "grezzo diventa meno di un tiro di eccesso nel rating. **La ridge "
        "minimizza l'errore predittivo, non stima livelli senza distorsione**; "
        "l'errore quadratico si riduce tirando tutti verso il centro, e chi sta "
        "in alto e' chi paga. E' lo stesso fenomeno del terzile alto di lambda "
        "(Fase 4) e del danno sopra 4.5 SoT (Fase 3): tre misure diverse dello "
        "stesso effetto, tutte con lo stesso segno.",
        "",
        f"Sul Como, tutto sulla scala di trasferta (media di campionato "
        f"{comp['media_lega_trasferta']:.4f}):", "",
        f"| livello | valore | eccesso sulla media |", "|---|---|---|",
        f"| rating del modello | {comp['modello_trasferta']:.4f} | "
        f"{comp['eccesso_modello']:.4f} |",
        f"| livello usato (4.90) | {comp['usato_trasferta']:.4f} | "
        f"{comp['eccesso_usato']:.4f} |",
        f"| grezzo 2025-26 | {comp['grezzo_trasferta']:.4f} | "
        f"{comp['eccesso_grezzo']:.4f} |",
        "",
        f"- de-compressione implicita nel livello usato: **{d_imp:.4f}**",
        f"- de-compressione che la pendenza giustificherebbe (1 / pendenza): "
        f"**{d_pen:.4f}**",
        f"- livello del Como de-compresso dalla pendenza, riportato su scala di "
        f"calendario: **{comp['livello_decompresso_calendario']:.3f}** contro "
        f"{comp['livello_modello_calendario']:.3f} del modello, "
        f"{rif} usato e {comp['livello_grezzo_calendario']:.3f} grezzo",
        "",
        f"Quindi {verdetto}. ",
        "Il gap fra il rating e il livello usato non e' un errore di nessuno "
        "dei due: e' la distanza fra una stima costruita per minimizzare "
        "l'errore sulla prossima partita e un livello, che sono due obiettivi "
        "diversi. La de-compressione implicita in 4.90 va nella direzione "
        "giusta; se sia della misura giusta, con una stagione sola, questi dati "
        "non lo possono dire — e' il tema del blocco 6C.",
        "",
        "---", "",
        "## 5. Le tre scale di campo, per tutte le squadre", "",
        _tab(rat[["team", "neutro", "casa", "media_calendario"]], 3),
        "",
        f"`neutro` e' il nome storico della colonna disegnata in `fig5` ed e' il "
        f"valore **in trasferta**; `casa` = `neutro` x {f:.4f}; "
        "`media_calendario` e' la media su 19 + 19, che e' la scala su cui si "
        "leggono i tassi grezzi di stagione e il livello 4.90. Il nome della "
        "colonna non e' stato cambiato perche' e' un numero gia' pubblicato: "
        "si documenta la scala, non si sposta il valore.",
        "",
        "---", "",
        "## Limiti di questo blocco", "",
        "- La regressione della sezione 4 e' **in campione su una stagione**: "
        "quantifica la compressione della ridge su questi 20 punti, non "
        "identifica il livello corretto per il 2026-27.",
        "- L'origine di 4.90 e' **dichiarata dall'utente e non verificabile "
        "qui**: se quel numero e' sbagliato, tutta la proiezione lo e', e "
        "niente in questo repository se ne accorgerebbe.",
        f"- Le quote 65% / 6% da cui escono `TEAM_SHOCK_SD_LOG` e "
        f"`LEAGUE_SD_LOG` sono **assunzioni ereditate** dallo stesso "
        "riferimento, non stime: l'intervallo pubblicato e' largo quanto il "
        "riferimento ha deciso che fosse.",
        f"- `tau` = {tau} e `r` = {r:.1f} sono quelli delle fasi precedenti, "
        "non ristimati qui.",
    ]

    path = config.REPORTS / "phase6_livello.md"
    path.write_text("\n".join(L), encoding="utf-8")

    print(f"  ramo A: rating {float(modello.iloc[0]['valore_risultante']):.3f} "
          f"(trasferta) -> calendario {float(modello.iloc[2]['valore_risultante']):.3f} "
          f"-> contesto {s['context_como']:.3f} -> osservato "
          f"{float(modello.iloc[4]['valore_risultante']):.3f}")
    print(f"  ramo B: {rif} x {s['ratio']:.4f} = {ancora:.4f} x {f_mc:.4f} "
          f"= {pubblicato_pp:.4f} x {SQ.N_MATCHES} = {pubblicato_st:.0f}")
    print(f"  contesto perturbato x{canc['k']}: scarto massimo "
          f"{canc['scarto_massimo']:.1f}")
    print(f"  compressione: pendenza {comp['pendenza']:.3f} +- "
          f"{comp['se_pendenza']:.3f} | de-compressione implicita {d_imp:.3f} "
          f"contro {d_pen:.3f}")
    print(f"  report -> {path}")


if __name__ == "__main__":
    main()
