# -*- coding: utf-8 -*-
"""Fase 6B — il test giusto per il bottom-up compositivo.

    python scripts/run_phase6b.py

Scrive `reports/phase6_compositivo.md`. Non cambia nessun numero pubblicato: la
proiezione resta 5.03 / 191 / [151, 240]. Quello che cambia e' **che cosa il
test di mezza stagione dice a chi**: fino alla Fase 5 bocciava l'estimatore che
fissa il livello dai giocatori, mentre la proiezione ne pubblica un altro.

Prerequisiti: `run_phase1.py` (tabelle).
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sot import (aggregate, config, model_player as MP, project_2627 as P,  # noqa: E402
                 squad_2627 as SQ, validate as V)

SPLIT = 19


def _tab(df: pd.DataFrame, dec: int = 4) -> str:
    return df.round(dec).to_markdown(index=False)


def ricambio_di_rosa(player_match: pd.DataFrame, split: int = SPLIT) -> pd.DataFrame:
    """Quanti minuti cambiano mano fra i due tempi di stagione, squadra per squadra.

    E' la misura della potenza disponibile: l'estimatore compositivo agisce
    **solo** attraverso il ricambio di rosa, quindi se fra le due meta' non
    cambia quasi niente il test non puo' dire niente, comunque vada.
    """
    d = player_match[MP.usable(player_match)]
    rows = []
    for team, g in d.groupby("team"):
        m1 = g[g["team_match_idx"] <= split].groupby("playerId")["minutes"].sum()
        m2 = g[g["team_match_idx"] > split].groupby("playerId")["minutes"].sum()
        usciti = m1.index.difference(m2.index)
        rows.append({"team": team,
                     "minuti_1o_tempo": float(m1.sum()),
                     "usciti": int(len(usciti)),
                     "nuovi": int(len(m2.index.difference(m1.index))),
                     "minuti_liberati": float(m1.loc[usciti].sum()),
                     "quota_liberata": float(m1.loc[usciti].sum() / m1.sum())})
    return pd.DataFrame(rows).sort_values("quota_liberata", ascending=False)


def main() -> None:
    print("Fase 6B — i due estimatori, separati")
    pm = aggregate.load_player_match()
    tm = aggregate.load_team_match()

    tau = float(MP.select_tau(MP.with_context(pm, tm)).iloc[0]["tau"])
    ht = P.first_half_test(pm, tm, split=SPLIT, tau=tau)

    # baseline di campionato, come in Fase 4: stesso test, stesse righe
    league_h1 = float(tm.loc[tm["team_match_idx"] <= SPLIT, "sot"].mean())
    ht["media campionato"] = league_h1
    ht["err_media campionato"] = ht["media campionato"] - ht["actual_h2"]

    ordine = ["topdown", "livello_dai_giocatori", "compositivo", "media campionato"]
    conf = P.confronto_stimatori(ht, ordine)
    conf["stimatore"] = ["nessun aggiustamento di rosa (= media squadra 1o tempo)",
                         "A — livello dai giocatori",
                         "B — compositivo (quello pubblicato)",
                         "baseline: media di campionato"]

    coppie = [
        ("A contro il suo baseline (media squadra)", "topdown", "livello_dai_giocatori"),
        ("B contro il suo baseline (rapporto = 1.0)", "topdown", "compositivo"),
        ("baseline di squadra contro media campionato", "media campionato", "topdown"),
    ]
    righe = []
    for etichetta, a, b in coppie:
        _, t = V.paired_t(ht[f"err_{a}"].abs(), ht[f"err_{b}"].abs())
        m = P.effetto_minimo_rilevabile(ht[f"err_{a}"], ht[f"err_{b}"])
        righe.append({"confronto": etichetta,
                      "d MAE": m["differenza_osservata"], "t": t,
                      "sd differenze": m["sd_differenze"],
                      "MDE 80%": m["mde"]})
    paired = pd.DataFrame(righe)

    ric = ricambio_di_rosa(pm)
    quota_stagione = sum(m for _, m, _ in SQ.DEPARTED) / SQ.OUTFIELD_MINUTES_BUDGET

    # Quanto l'estimatore B sposta davvero le previsioni: e' il tetto massimo
    # del guadagno ottenibile, perche' nel caso migliore ogni aggiustamento
    # andrebbe nel verso giusto e per intero.
    intervento = (ht["compositivo"] - ht["topdown"]).abs()
    mde_b = float(paired.loc[1, "MDE 80%"])

    proj, s, _, _ = P.build_projection(pm, tm, tau=tau)

    L = [
        "# Fase 6B — il test giusto per il bottom-up compositivo", "",
        "Fino alla Fase 5 \"dal basso\" era un nome solo per due stimatori "
        "diversi, e il test di mezza stagione bocciava quello che la proiezione "
        "**non** usa. Qui i due sono separati nel codice "
        "(`project_2627.stima_livello_dai_giocatori` e "
        "`project_2627.stima_compositiva`) e testati ciascuno contro il proprio "
        "baseline. **Nessun numero pubblicato cambia**: il rapporto compositivo "
        f"resta {s['ratio']:.4f} e la proiezione resta quella della Fase 3.", "",
        "## Esito in breve", "",
        "1. **Il risultato negativo della Fase 3 resta, e resta dov'era**: "
        f"l'estimatore A (livello deciso dai giocatori) fa MAE "
        f"{conf.loc[1, 'MAE']:.4f} contro {conf.loc[0, 'MAE']:.4f} del tasso di "
        f"squadra, differenza appaiata {paired.loc[0, 'd MAE']:+.4f} "
        f"(t = {paired.loc[0, 't']:+.2f}). Nessuna correzione: era gia' il "
        "risultato giusto sull'estimatore sbagliato.",
        f"2. **L'estimatore B non e' mai stato validato, e questo test non lo "
        f"valida.** MAE {conf.loc[2, 'MAE']:.4f} contro {conf.loc[0, 'MAE']:.4f} "
        f"del suo baseline corretto (\"nessun aggiustamento di rosa\", cioe' "
        f"rapporto identicamente 1.0): differenza {paired.loc[1, 'd MAE']:+.4f}, "
        f"t = {paired.loc[1, 't']:+.2f}. **Non e' una conferma: e' mancanza di "
        "potenza**, e il punto 3 dice quanta.",
        f"3. **Il test di B e' quasi vuoto per costruzione.** L'effetto minimo "
        f"rilevabile su questo confronto vale {mde_b:.4f} di MAE; "
        f"l'aggiustamento compositivo sposta le previsioni di "
        f"{intervento.mean():.4f} in media (massimo {intervento.max():.4f}). "
        "Il guadagno massimo **concepibile** — ogni aggiustamento nel verso "
        f"giusto e per intero — vale quindi {intervento.mean():.4f}, cioe' "
        f"{intervento.mean() / mde_b:.2f} volte la soglia. Perche' il test "
        "distinguesse B dal proprio baseline, l'aggiustamento dovrebbe essere "
        "praticamente perfetto: a qualunque efficacia parziale il test e' "
        "cieco.",
        f"4. **Perche' e' vuoto**: fra i due tempi di una stessa stagione la "
        f"rosa quasi non cambia. Si libera in media il "
        f"{ric['quota_liberata'].mean():.1%} dei minuti (mediana "
        f"{ric['quota_liberata'].median():.1%}), contro il "
        f"{quota_stagione:.1%} che cambia fra un'estate e l'altra nel caso "
        f"Como. I rapporti restano fra {ht['rapporto'].min():.4f} e "
        f"{ht['rapporto'].max():.4f}.",
        "",
        "---", "",
        "## 1. I due estimatori", "",
        "| | chi decide il livello | chi decide la ripartizione | dove sta |",
        "|---|---|---|---|",
        "| **A — livello dai giocatori** | i giocatori | i giocatori | "
        "`stima_livello_dai_giocatori` |",
        "| **B — compositivo** | l'ancora dall'alto (4.90) | i giocatori, via "
        "rapporto di rosa | `stima_compositiva` |", "",
        "La differenza non e' di sfumatura: B e' **invariante** rispetto al "
        "contesto di squadra (compare a numeratore e denominatore del rapporto "
        "e si semplifica), A no. E' la stessa invarianza dimostrata in Fase 6A "
        "sul numero pubblicato, e un test la verifica su entrambi.", "",
        "Baseline corretto per ciascuno:", "",
        "- **A** fissa un livello, quindi va confrontato con un altro livello: "
        "il tasso di squadra del primo tempo.",
        "- **B** non fissa nessun livello: prende quello dall'alto e lo "
        "moltiplica per il rapporto di rosa. Il suo baseline e' **lo stesso "
        "livello con rapporto identicamente 1.0**, cioe' \"nessun aggiustamento "
        "di rosa\". Nel test di mezza stagione il livello dall'alto e' il tasso "
        "di squadra del primo tempo, quindi le due colonne di baseline "
        "coincidono numericamente — ma la domanda che pongono e' diversa.",
        "",
        "---", "",
        "## 2. Il test 1o/2o tempo su entrambi", "",
        f"Stima sulle prime {SPLIT} partite di ogni squadra, previsione della "
        f"media di tiri in porta delle {SPLIT} successive. 20 squadre.", "",
        _tab(conf[["stimatore", "MAE", "RMSE", "bias", "corr"]]),
        "",
        "Confronti appaiati, con l'effetto minimo che il test potrebbe "
        "distinguere (potenza 80%, alpha 5%):", "",
        _tab(paired),
        "",
        f"Sul confronto che conta per la proiezione — la riga B — la differenza "
        f"osservata ({paired.loc[1, 'd MAE']:+.4f}) e' "
        f"{abs(paired.loc[1, 'd MAE']) / mde_b:.0%} dell'effetto minimo "
        f"rilevabile ({mde_b:.4f}). Un t di {paired.loc[1, 't']:+.2f} qui non "
        "significa \"il metodo non funziona\" e nemmeno \"funziona\": "
        "significa che questo test non e' in grado di vederlo.",
        "",
        "### Dettaglio per squadra", "",
        _tab(ht[["team", "topdown", "livello_dai_giocatori", "compositivo",
                 "rapporto", "actual_h2"]]),
        "",
        "---", "",
        "## 3. Quanto ricambio c'e' davvero fra i due tempi", "",
        _tab(ric[["team", "usciti", "nuovi", "minuti_liberati", "quota_liberata"]], 4),
        "",
        f"Media {ric['quota_liberata'].mean():.1%}, mediana "
        f"{ric['quota_liberata'].median():.1%}, massimo "
        f"{ric['quota_liberata'].max():.1%} ({ric.iloc[0]['team']}). Il Como e' "
        f"il caso limite in senso opposto: "
        f"{ric.loc[ric.team == 'Como', 'quota_liberata'].iloc[0]:.2%} dei "
        "minuti liberati, cioe' la sua riga del test non contiene alcuna "
        "informazione sull'estimatore compositivo — ed e' proprio la squadra "
        "che la proiezione riguarda.", "",
        f"Nel passaggio vero, 2025-26 -> 2026-27, se ne liberano "
        f"{quota_stagione:.1%}: un ordine di grandezza diverso. Il test "
        "sottopone l'estimatore a una perturbazione che e' una frazione di "
        "quella su cui poi lo si usa.",
        "",
        "---", "",
        "## 4. Cosa questo test puo' e non puo' dire", "",
        "**Puo' dire** che fissare il livello dai giocatori peggiora la "
        "previsione: l'estimatore A perde contro il tasso di squadra, il segno "
        "e' stabile e la causa (doppia compressione, danno concentrato sulle "
        "squadre di vertice) e' documentata in Fase 3 e confermata come "
        "pendenza in Fase 6A.", "",
        "**Non puo' dire** se l'aggiustamento compositivo aggiunga o tolga "
        "qualcosa. Tre ragioni, tutte strutturali e nessuna risolvibile con "
        "questi dati:", "",
        "1. **Non c'e' ricambio di rosa vero** fra i due tempi di una stessa "
        "stagione: la sessione di gennaio muove una frazione dei minuti che "
        "cambiano fra un'estate e l'altra.",
        "2. **Venti righe**, una per squadra, e non indipendenti fra loro "
        "(la stessa partita compare in due righe con segni opposti sul "
        "calendario).",
        "3. **La rosa del secondo tempo e' nota al test.** Per proiettare i "
        "minuti bisogna sapere chi c'e': si usa la composizione reale della "
        "rosa del secondo tempo — identita' e ruolo, mai tiri o minuti. E' "
        "l'analogo della proiezione vera, dove la rosa 2026-27 e' nota, ma "
        "resta informazione che viene dal periodo bersaglio e **favorisce** "
        "l'estimatore B. Anche cosi' favorito non si distingue dal baseline.",
        "",
        "Se un domani qualcuno leggesse `t = "
        f"{paired.loc[1, 't']:+.2f}` come \"il metodo compositivo e' "
        "convalidato\", starebbe leggendo rumore. La riga da citare e' l'altra: "
        f"MDE {mde_b:.4f} contro un intervento medio di "
        f"{intervento.mean():.4f}, cioe' un test che vedrebbe qualcosa solo se "
        "l'aggiustamento fosse perfetto.",
        "",
        "---", "",
        "## Limiti di questo blocco", "",
        f"- `tau` = {tau:g} e la scelta di `alpha` = 12.0 sono quelli delle fasi "
        "precedenti: questo blocco non ristima niente.",
        "- La rotazione nella proiezione dei minuti del secondo tempo e' posta "
        "a **zero**: dentro la stagione non c'e' l'analogo della rotazione "
        "Champions. Nella proiezione vera vale 0.15, fatta variare fra 0.05 e "
        "0.25.",
        "- Il rapporto compositivo del test usa **una riga per giocatore** su "
        "entrambi i lati (ruolo in cui ha giocato piu' minuti), altrimenti il "
        "quoziente conterrebbe anche la differenza di convenzione. "
        "L'estimatore A resta sulla convenzione precedente, per non spostare "
        "un numero gia' pubblicato.",
        "- **Una sola stagione**: il test e' interno alla stagione e la "
        "persistenza dentro la stagione e' piu' alta di quella fra stagioni. "
        "Vale per il livello (blocco 6C) come per il rapporto.",
    ]

    path = config.REPORTS / "phase6_compositivo.md"
    path.write_text("\n".join(L), encoding="utf-8")
    ht.to_csv(config.REPORTS / "phase6_halfseason_due_stimatori.csv", index=False)

    print(f"  tau = {tau:g}")
    for _, row in conf.iterrows():
        print(f"  {row['stimatore']:<52} MAE {row['MAE']:.4f}")
    for _, row in paired.iterrows():
        print(f"  {row['confronto']:<45} d {row['d MAE']:+.4f} "
              f"t {row['t']:+.2f}  MDE {row['MDE 80%']:.4f}")
    print(f"  intervento compositivo: medio {intervento.mean():.4f}, "
          f"massimo {intervento.max():.4f}")
    print(f"  report -> {path}")


if __name__ == "__main__":
    main()
