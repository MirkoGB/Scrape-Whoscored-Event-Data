# -*- coding: utf-8 -*-
"""Fase 6F — piano dati, senza scaricare niente.

    python scripts/run_phase6f.py

Scrive `reports/phase6_piano_dati.md`. **Non scarica nulla, non aggiunge
dipendenze e non cambia nessun numero pubblicato**: la proiezione resta
5.03 / 191 / [151, 240]. L'unica cosa calcolata e' la simulazione sui sei nuovi
arrivi, che la specifica del blocco chiede esplicitamente di fare adesso.

Prerequisiti: `run_phase1.py` (tabelle) e `run_phase2.py`
(`walkforward_base.parquet`, da cui si stima `r`). `reports/phase6_predittori.csv`
scritto da `run_phase6d.py` serve alla sezione sul blocco 6D: senza, quella
sezione dichiara che manca invece di inventarsi i numeri.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sot import (aggregate, config, data_plan as DP,  # noqa: E402
                 dispersion as D, model_player as MP, project_2627 as P)

N_SIM = 200000          # alto apposta: l'effetto da leggere e' dell'1% sulla sd
MINUTI_RIFERIMENTO = 1800.0

# Volume dei dati evento, per il conto del blocco 6D. ~1 GB per 380 partite in
# `data/serie_a_2025_2026/`, cioe' 2.6 MB a partita.
MB_PER_PARTITA = 1000.0 / 380.0
PARTITE_PER_GIORNATA = 10       # 20 squadre
GIORNATE_STAGIONE = 38
GIORNATE_ACERBO = 10            # prime 8 valutate + le 30 partite di storia


def main() -> None:
    print("Fase 6F — piano dati (nessun download)")
    tm = aggregate.load_team_match()
    pm = aggregate.load_player_match()

    wf_path = config.PROCESSED / "walkforward_base.parquet"
    if not wf_path.exists():
        raise SystemExit("manca walkforward_base.parquet: esegui prima run_phase2.py")
    wfd = pd.read_parquet(wf_path)
    r = D.fit_r(wfd["sot"].to_numpy(), wfd["lam"].to_numpy())

    tau = float(MP.select_tau(MP.with_context(pm, tm)).iloc[0]["tau"])
    proj, s, model, _ = P.build_projection(pm, tm, tau=tau)

    eff = model.player_effects()["v"].to_numpy()
    sd_prior_pubblicato = 1.5 * float(np.std(eff[np.abs(eff) > 1e-9]))

    peso = DP.peso_nuovi_arrivi(proj)
    dett = DP.dettaglio_arrivi(proj, model, tau, minuti=MINUTI_RIFERIMENTO)
    st = DP.stringimento_intervallo(proj, s, model, r, tau, n_sim=N_SIM)
    va = DP.varianza_nuovi_arrivi(proj, s, model, r, tau, n_sim=N_SIM)

    pub = st.iloc[0]
    con = st[st["stato"] == "con dati individuali"]
    # Il caso migliore e' l'estremo ottimistico della griglia: trasferimento
    # perfetto e una stagione piena di minuti.
    best = con[(con["mult_trasferimento"] == 0.0)
               & (con["minuti"] == max(DP.MINUTI_GRID))].iloc[0]
    worst = con[con["mult_trasferimento"] == 1.0]

    v_pub = va.iloc[0]
    v_best = va[(va["mult_trasferimento"] == 0.0)
                & (va["minuti"] == max(DP.MINUTI_GRID))].iloc[0]

    # Controllo analitico: se le fonti fossero additive in varianza, la sd
    # totale scenderebbe di questo. Non lo sono (Fase 6A), quindi e' un
    # controllo d'ordine di grandezza e va detto cosi'.
    sd_attesa = float(np.sqrt(pub["sd_stagione"] ** 2
                              - (v_pub["varianza_fonte"] - v_best["varianza_fonte"])))

    # --- blocco 6D: quante stagioni di eventi grezzi ---
    pred_path = config.REPORTS / "phase6_predittori.csv"
    p6d = DP.piano_6d(pd.read_csv(pred_path)) if pred_path.exists() else None

    # Volume dei dati, in partite e in GB. Il regime maturo ha bisogno di
    # stagioni intere (38 giornate); l'acerbo vive sulle prime 8 e ne bastano
    # ~10, contando le 30 partite che `date_splits` pretende come storia.
    gb_acerbo = gb_maturo = None
    if p6d is not None:
        def _volume(regime: str, giornate: int) -> dict:
            st = float(p6d.loc[p6d["regime"] == regime,
                               "stagioni_campionato"].iloc[0])
            partite = st * giornate * PARTITE_PER_GIORNATA
            return {"stagioni": st, "partite": partite,
                    "gb": partite * MB_PER_PARTITA / 1000.0}

        gb_acerbo = _volume("acerbo", GIORNATE_ACERBO)
        gb_maturo = _volume("maturo", GIORNATE_STAGIONE)

    dom = DP.tabella_domande()
    gran = DP.tabella_granularita()

    def _md(df, cols=None, dec=4):
        d = df[cols] if cols else df
        return d.round(dec).to_markdown(index=False)

    L = [
        "# Fase 6F — piano dati, senza scaricare niente", "",
        "Che cosa servirebbe davvero per chiudere le domande che le Fasi 6A-6E "
        "hanno lasciato aperte. **Non e' stato scaricato niente, non e' stata "
        "aggiunta nessuna dipendenza e nessun numero pubblicato cambia**: la "
        "proiezione resta 5.03 a partita, 191 in stagione, IC80% [151, 240]. "
        "L'unica cosa calcolata qui e' la simulazione sui sei nuovi arrivi, che "
        "la specifica del blocco chiede di fare adesso.", "",
        "Prima di tutto il resto, il fatto di stato: **i blocchi 6A, 6B, 6C, 6D "
        "e 6E sono stati eseguiti** e i loro report esistono "
        "(`phase6_livello.md`, `phase6_compositivo.md`, `phase6_rho.md`, "
        "`phase6_predittori.md`, `phase6_calendario.md`). Questo piano riassume "
        "cosa hanno trovato, non cosa avrebbero potuto trovare.", "",
        "## Esito in breve", "",
        "1. **Sette domande aperte su otto non richiedono dati evento.** Il "
        "criterio non e' una preferenza: segue da dove i blocchi precedenti "
        "hanno localizzato l'incertezza. La Fase 6A ha mostrato che il livello "
        "pubblicato **non contiene il modello di squadra** — il contesto si "
        "semplifica dentro `monte_carlo` — quindi tutto cio' che riguarda il "
        "livello vive su totali di squadra per stagione, la granularita' piu' "
        "grossolana che esista.",
        "2. **La domanda piu' grande e' anche la piu' economica.** `rho`, la "
        "persistenza fra stagioni, sposta la proiezione di 19 tiri (21% "
        "dell'IC80%) e si risponde con un numero per squadra per stagione su "
        "10+ stagioni: una tabella che si scrive a mano.",
        f"3. **La domanda piu' cara e' quella con il valore atteso piu' basso.** "
        + (f"Il blocco 6D avrebbe bisogno di **{p6d[p6d['regime'] == 'acerbo']['stagioni_campionato'].iloc[0]:.1f} "
           f"stagioni-campionato di eventi grezzi** per portare il test acerbo "
           f"a potenza 80%, e {p6d[p6d['regime'] == 'maturo']['stagioni_campionato'].iloc[0]:.1f} "
           "per quello maturo — contro un esito gia' negativo in tre regimi. "
           "Una stagione-campionato intera qui vale ~1 GB e 562.672 eventi."
           if p6d is not None else
           "Il conto per il blocco 6D non e' riportato perche' manca "
           "`reports/phase6_predittori.csv`: eseguire `run_phase6d.py`."),
        f"4. **I sei nuovi arrivi sono il limite piu' vistoso e valgono meno di "
        f"tutti.** Valgono il {peso['quota_minuti']:.0%} dei minuti proiettati e "
        f"il {peso['quota_lambda']:.0%} del lambda, ma avere per ciascuno un "
        f"tasso individuale stringerebbe la deviazione standard della "
        f"proiezione di **{best['riduzione_sd']:.1%} nel caso migliore** "
        f"({pub['ampiezza']:.0f} tiri di IC80% che diventano "
        f"{best['ampiezza']:.0f}), e **di niente** all'estremo superiore "
        "dell'incertezza di trasferimento. La simulazione e' nella sezione 3.",
        "",
        "---", "",
        "## 1. Le quattro granularita'", "",
        "Sono una scala: ogni livello contiene i precedenti. Il piano indica per "
        "ogni domanda il **minimo** che basta, non il massimo che si vorrebbe — "
        "chiedere una granularita' piu' fine del necessario e' il modo piu' "
        "comune di rendere un piano dati irrealizzabile.", "",
        _md(gran),
        "",
        "---", "",
        "## 2. Le domande aperte, una per una", "",
        _md(dom, ["id", "domanda", "granularita", "granularita_nome", "sblocca",
                  "eventi"]),
        "",
        "### Perche' ciascuna e' aperta, e cosa costa", "",
    ]
    for d in DP.DOMANDE_APERTE:
        L += [
            f"**{d['id']} — {d['domanda']}** ({d['granularita']}, sblocca "
            f"{d['sblocca']}, eventi grezzi: {'si' if d['eventi'] else 'no'})",
            "",
            f"- *perche' e' aperta*: {d['perche_aperta']}",
            f"- *ampiezza minima*: {d['ampiezza']}",
            f"- *quanto pesa*: {d['impatto']}",
            "",
        ]

    n_no_eventi = sum(1 for d in DP.DOMANDE_APERTE if not d["eventi"])
    L += [
        f"**{n_no_eventi} domande su {len(DP.DOMANDE_APERTE)} si chiudono senza "
        "un solo evento grezzo**, e le due che spostano di piu' la proiezione "
        "(D1 e D2) stanno entrambe sulla granularita' piu' grossolana. Non e' "
        "una comodita': e' la conseguenza diretta della Fase 6A, che ha mostrato "
        "che il livello pubblicato e' `4.90 x rapporto x convessita'` e che "
        "rating, `alpha` e vantaggio del campo decidono come il lambda si "
        "ripartisce, non quanto vale.", "",
        "---", "",
        "## 3. I sei nuovi arrivi: quanto varrebbe avere i loro dati", "",
        f"Sono {peso['n_nuovi']} giocatori di movimento senza una riga in questi "
        f"dati: valgono il **{peso['quota_minuti']:.1%} dei minuti proiettati** e "
        f"il **{peso['quota_lambda']:.1%} del lambda**, oggi interamente sulla "
        "media del proprio ruolo.", "",
        "### Che dati servirebbero, per ciascuno", "",
        "Non uno, **tre**, e la terza e' quella che di solito manca:", "",
    ]
    L += [f"{i}. {t}" for i, t in enumerate(DP.DATI_MINIMI_PER_ARRIVO, 1)]
    L += [
        "",
        "La seconda e la terza non sono zelo: `v_p` e' definito **al netto del "
        "contesto di squadra** (`model_player`), quindi un tasso grezzo preso da "
        "un altro campionato non e' la stessa grandezza. Senza la correzione si "
        "sovrastima chi arriva da una squadra dominante — che e' esattamente "
        "l'errore che il contesto esiste per evitare.", "",
        "**Il campionato-stagione di provenienza non e' nel repository.** "
        "`squad_2627.NEW_SIGNINGS` registra nome e ruolo e basta: la rosa e' "
        "stata ricostruita dal web senza la storia dei trasferimenti. Non viene "
        "inventato qui — la colonna lo dichiara, e va letto dal registro "
        "trasferimenti come si e' fatto per la rosa.", "",
        f"Esposizione di riferimento della tabella: {MINUTI_RIFERIMENTO:.0f} "
        "minuti, cioe' una stagione da titolare.", "",
        _md(dett),
        "",
        f"`se_oggi_tetto_modello` = `1/sqrt(2 tau)` = "
        f"{dett['se_oggi_tetto_modello'].iloc[0]:.4f} e' quello che il modello "
        "assegnerebbe a un giocatore senza esposizione. **Il prior pubblicato "
        f"dei nuovi arrivi vale {sd_prior_pubblicato:.4f}** "
        "(`1.5 x` la dispersione fra giocatori), cioe' e' **piu' stretto** del "
        "tetto del modello, non piu' largo. Il prior chiamato \"gonfiato\" "
        "gonfia rispetto alla dispersione fra giocatori, non rispetto "
        "all'ignoranza: la differenza non era mai stata scritta.", "",
        "### La simulazione: di quanto si stringe l'intervallo", "",
        "Cambia **solo** la deviazione standard del prior dei nuovi arrivi. "
        "Ancora del livello, rapporto compositivo, seed, fonti e numero di "
        f"simulazioni ({N_SIM // 1000} mila per riga) restano quelli pubblicati. "
        "La griglia e' dichiarata in `data_plan.MINUTI_GRID` e "
        "`data_plan.MULT_TRASFERIMENTO`.", "",
        "`mult_trasferimento` e' l'incertezza di trasporto fra campionati, come "
        "multiplo della dispersione fra giocatori. **E' parametrizzata, non "
        "stimata**: questi dati contengono un campionato solo. Lo `0.0` e' il "
        "limite ottimistico (il tasso si trasporta intatto); l'`1.0` e' il "
        "limite superiore ed e' li' apposta — se la verita' e' li', il dato "
        "individuale non aggiunge niente e il calcolo lo deve poter dire.", "",
        _md(st, ["stato", "minuti", "mult_trasferimento", "sd_media_nuovi",
                 "stagione", "q10", "q90", "ampiezza", "sd_stagione",
                 "riduzione_sd", "d_stagione"]),
        "",
        "Come leggerla:", "",
        "- **La colonna da guardare e' `sd_stagione`, non `ampiezza`.** Il "
        "totale stagionale simulato e' un intero, quindi i suoi percentili si "
        "muovono a scalini da 1 e un effetto piu' piccolo di un tiro non e' "
        "leggibile nell'ampiezza. `ampiezza` resta in tabella perche' e' la "
        "grandezza che il README pubblica.",
        f"- **Caso migliore: {best['riduzione_sd']:.2%} di deviazione "
        f"standard**, cioe' l'IC80% passa da {pub['ampiezza']:.0f} a "
        f"{best['ampiezza']:.0f} tiri. Serve trasporto perfetto fra campionati "
        f"e {max(DP.MINUTI_GRID):.0f} minuti a testa, cioe' l'angolo piu' "
        "favorevole della griglia.",
        f"- **All'estremo superiore non si stringe niente**: con "
        f"`mult_trasferimento = 1.0` la riduzione va da "
        f"{worst['riduzione_sd'].min():+.2%} a {worst['riduzione_sd'].max():+.2%}, "
        "cioe' comprende lo zero e i valori negativi. Un dato individuale che "
        "non si trasporta e' rumore in piu', non informazione.",
        f"- **Il centro si sposta quanto l'intervallo si stringe**: da "
        f"{pub['stagione']:.0f} a {best['stagione']:.0f} tiri di stagione. E' il "
        "gonfiamento di Jensen misurato in Fase 6A (+0.65% dai nuovi arrivi) "
        "che si sgonfia quando il prior si stringe. Chi raccogliesse quei dati "
        "aspettandosi un intervallo piu' stretto otterrebbe soprattutto una "
        "proiezione leggermente piu' bassa.",
        f"- **Le righe a `minuti = 0` allargano.** Sostituire il prior "
        "pubblicato (0.3654) col tetto del modello a esposizione nulla (0.4082) "
        "peggiora, ed e' il controllo che la simulazione stia facendo quello che "
        "dice: senza dati, essere onesti sull'ignoranza costa.", "",
        "### La stessa cosa sulla sola fonte `new_signings`", "",
        "Sul totale il guadagno e' diluito, perche' i nuovi arrivi pesano "
        f"{v_pub['quota_sul_totale']:.1%} della varianza. Accendendo la sola "
        "fonte si vede quanto vale **la fonte**, che e' la grandezza da citare "
        "per decidere se la raccolta ha senso:", "",
        _md(va, ["stato", "minuti", "mult_trasferimento", "varianza_fonte",
                 "quota_sul_totale", "riduzione_fonte"], dec=5),
        "",
        f"Nel caso migliore la varianza della fonte scende da "
        f"{v_pub['varianza_fonte']:.1f} a {v_best['varianza_fonte']:.1f} "
        f"(**{v_best['riduzione_fonte']:.0%}**), ma la fonte vale l'1.4% del "
        "totale. Controllo d'ordine di grandezza: se le fonti fossero additive "
        f"in varianza la sd totale scenderebbe a {sd_attesa:.2f} contro i "
        f"{best['sd_stagione']:.2f} simulati e i {pub['sd_stagione']:.2f} "
        "pubblicati. Non coincidono perche' **le fonti interagiscono**, come "
        "gia' documentato in Fase 6A: l'approssimazione additiva vale come "
        "controllo, non come risultato.", "",
        "**Conclusione operativa: D7 e' l'ultima voce della lista, non la "
        "prima.** E' il limite piu' visibile del README — sei giocatori su "
        "media di ruolo — ma sposta l'incertezza pubblicata meno di ogni altra "
        "domanda del piano. Se si raccoglie, si raccolga perche' rende la "
        "ripartizione fra giocatori piu' credibile (`fig7`), non perche' "
        "stringa l'intervallo.", "",
        "---", "",
        "## 4. Il blocco 6D: l'unico che vuole eventi grezzi", "",
    ]
    if p6d is None:
        L += ["**Non calcolato**: manca `reports/phase6_predittori.csv`. "
              "Eseguire `scripts/run_phase6d.py` e rilanciare questo script. "
              "I numeri non vengono inventati.", ""]
    else:
        L += [
            "Quante righe servirebbero perche' il test dei predittori avesse "
            "potenza 80% contro l'alternativa dichiarata dalla Fase 6D — "
            "l'effetto per riga piu' grande che gli otto candidati abbiano mai "
            f"prodotto (`{DP.PREDITTORE_ALTERNATIVA}` nel regime maturo). "
            "L'errore standard scala come `1/sqrt(n)`, quindi le righe crescono "
            "col quadrato del rapporto fra il `t` che serve e quello che si ha. "
            "`righe_per_stagione` e' quante ne produce **una** stagione di Serie "
            "A in quel regime.", "",
            _md(p6d),
            "",
            f"- **`t_ora` riproduce esattamente il `t` di Fase 6D** "
            f"({p6d[p6d['regime'] == 'maturo']['t_ora'].iloc[0]:.4f} contro "
            "1.4201 nel regime maturo). Non e' un controllo indipendente — e' "
            "lo stesso rapporto `d_riga / se_riga`, ricalcolato dalle stesse "
            "colonne — ma conferma che il conto delle righe parte dalla "
            "parametrizzazione che la Fase 6D ha davvero usato, e non da una "
            "reinterpretazione dei suoi numeri.",
            f"- **Il regime acerbo, che e' quello dell'ipotesi da testare, "
            f"chiede {p6d[p6d['regime'] == 'acerbo']['stagioni_campionato'].iloc[0]:.1f} "
            "stagioni-campionato** di eventi grezzi. Possono essere campionati "
            "diversi nello stesso anno — 3 stagioni per 5 campionati vanno bene "
            "quanto 14 anni di Serie A.",
            "- **Ma non servono stagioni intere, e questo cambia il conto.** Il "
            "regime acerbo vive sulle prime 8 giornate: ne bastano ~10 per "
            "campionato-stagione, contando le 30 partite che `date_splits` "
            f"pretende come storia, cioe' {gb_acerbo['partite']:.0f} partite "
            f"invece di {gb_maturo['partite']:.0f}. A ~{MB_PER_PARTITA:.1f} MB "
            f"per partita fanno **{gb_acerbo['gb']:.1f} GB contro "
            f"{gb_maturo['gb']:.1f} GB** del regime maturo, che di stagioni "
            "intere ha bisogno. I due sono dello stesso ordine, e sopra a "
            "entrambi vanno comunque ricalcolati field tilt, PPDA, tocchi in "
            "area e xG interno, che nessun fornitore pubblica come totali.",
            "- **E' l'unica domanda del piano che richiede eventi**, ed e' anche "
            "quella con il valore atteso piu' basso: tre regimi, otto candidati, "
            "nessuno che passi, e un test in campione — il piu' favorevole "
            "concepibile — che non rifiuta. Il piano la mette per ultima e la "
            "motivazione e' questa, non il costo.",
            "- **Attenzione all'assunzione**: il conto suppone che la "
            "variabilita' per riga resti quella misurata, mentre la Fase 6D ha "
            "trovato che nel regime acerbo e' **piu' piccola** (MDE x1.8 contro "
            "un x2.6 giustificato dalle sole righe perse). Vale come ordine di "
            "grandezza.", "",
        ]

    L += [
        "---", "",
        "## 5. In che ordine", "",
        "Non e' una classifica di importanza scientifica: e' tiri in porta di "
        "incertezza spostati per unita' di dato raccolto.", "",
        "| ordine | domande | granularita' | perche' prima |",
        "|---|---|---|---|",
        "| 1 | D1, D2, D5 | G1, totali di squadra per stagione | sono le tre "
        "che toccano il **livello**, cioe' l'unica cosa che sposta la "
        "proiezione (Fase 6A), e stanno tutte sulla granularita' piu' "
        "grossolana. D1 vale 19 tiri, D5 ne vale 9, D2 e' la verifica "
        "dell'ancora da cui dipende tutto |",
        "| 2 | D3, D6 | G2, totali di squadra per partita | un livello di "
        "granularita' in piu' per due domande piu' piccole: la misura della "
        "de-compressione (6 tiri) e il segno della congestione, che oggi manca "
        "del tutto |",
        "| 3 | D4 | G3, tassi per 90 per giocatore | valida l'estimatore "
        "**pubblicato**, che non e' mai stato validato: costa una stagione di "
        "dati per giocatore per ogni transizione, e ne servono 4-5 |",
        "| 4 | D7 | G3, tassi per 90 per giocatore | il limite piu' visibile e "
        "il guadagno piu' piccolo, quantificato nella sezione 3 |",
        "| 5 | D8 | G4, eventi grezzi | l'unica che richiede eventi, la piu' "
        "cara, e l'unica il cui esito e' gia' stato misurato tre volte |",
        "",
        "---", "",
        "## Limiti di questo blocco", "",
        "- **E' un piano, non un risultato.** Le uniche cifre calcolate qui sono "
        "quelle della sezione 3 e il conto delle righe della sezione 4; tutto il "
        "resto e' un inventario di cio' che i blocchi 6A-6E hanno gia' trovato.",
        "- **L'incertezza di trasferimento fra campionati non e' stimata.** E' "
        "una griglia dichiarata, e il caso migliore della sezione 3 e' il suo "
        "estremo ottimistico: va citato come limite superiore del guadagno, non "
        "come previsione.",
        "- **La simulazione tiene ferma la rosa.** Il mercato chiude il "
        "1 settembre 2026 e la rosa cambiera': se cambiano i nuovi arrivi "
        "cambia anche quanto varrebbe conoscerli.",
        "- **Il campionato di provenienza dei sei nuovi arrivi non e' nel "
        "repository** e non e' stato ipotizzato. Senza quello, la sezione 3 "
        "dice quanto varrebbe il dato, non dove prenderlo.",
        "- **Le ampiezze richieste (10+ stagioni, 4-5 transizioni) sono ordini "
        "di grandezza**, non calcoli di potenza. L'unico conto di potenza vero "
        "e' quello della sezione 4, che riguarda il blocco 6D.",
        f"- `tau` = {tau:g}, `alpha` = 12.0 e `r` = {r:.1f} sono quelli delle "
        "fasi precedenti, non ristimati qui.",
    ]

    path = config.REPORTS / "phase6_piano_dati.md"
    path.write_text("\n".join(L), encoding="utf-8")

    dom.to_csv(config.REPORTS / "phase6_piano_dati.csv", index=False)

    print(f"  domande aperte: {len(DP.DOMANDE_APERTE)}, senza eventi: {n_no_eventi}")
    print(f"  nuovi arrivi: {peso['n_nuovi']} = {peso['quota_minuti']:.1%} dei "
          f"minuti, {peso['quota_lambda']:.1%} del lambda")
    print(f"  restringimento sd: {best['riduzione_sd']:.2%} nel caso migliore, "
          f"IC80% {pub['ampiezza']:.0f} -> {best['ampiezza']:.0f}")
    if p6d is not None:
        print("  6D, stagioni-campionato di eventi per potenza 80%: "
              + ", ".join(f"{row.regime} {row.stagioni_campionato:.1f}"
                          for row in p6d.itertuples()))
    else:
        print("  6D: saltato (manca reports/phase6_predittori.csv)")
    print(f"  report -> {path}")


if __name__ == "__main__":
    main()
