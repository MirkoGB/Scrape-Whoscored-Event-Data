# -*- coding: utf-8 -*-
"""Fase 7 — stabilita' del criterio di rilevazione fra le cinque stagioni.

    python scripts/run_phase7_stabilita.py [--force]

Scrive `reports/phase7_stabilita_rilevazione.md` piu' due CSV di appoggio.
**Non scarica niente** e non tocca nessun numero delle Fasi 1-6: legge i CSV
gia' su disco, scrive un Parquet di cache nuovo e un report.

`--force` rilegge i 1.889 CSV (~90 s) invece di usare la cache.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sot import config, recording_stability as RS  # noqa: E402

N_SIM = 2000
SOGLIA_Z_QUALIFIER = 6.0


def _md(df: pd.DataFrame, dec: int = 4) -> str:
    return df.round(dec).to_markdown(index=False)


def _n(x) -> str:
    """Migliaia col punto, come nel resto dei report."""
    return f"{int(x):,}".replace(",", ".")


def main(force: bool = False) -> None:
    print("Fase 7 — stabilita' del criterio di rilevazione")
    tiri = RS.carica_tiri(force=force)
    meta = RS.carica_file()
    u = RS.unita_squadra_partita(tiri, meta)
    stag = RS.per_stagione(u)
    mese = RS.per_mese(u)

    # ---------------------------------------------------------------- livelli
    liv_tent = RS.scarti_livello(stag, "tentativi_per_sp", u, "tentativi")
    liv_sot = RS.scarti_livello(stag, "in_porta_per_sp", u, "in_porta")
    mde_tent = RS.mde_livello(u, "tentativi")
    mde_sot_liv = RS.mde_livello(u, "in_porta")

    # ---------------------------------------------------------------- rapporti
    scarti = {c: RS.scarti_dal_numero_unico(stag, c) for c in RS.CATEGORIE}
    modelli = {c: RS.confronto_modelli(u, c) for c in RS.CATEGORIE}
    annidati = {c: RS.test_annidati(u, c) for c in RS.CATEGORIE}
    mde = {c: RS.mde_gradino(u, c) for c in RS.CATEGORIE}

    rotture = pd.DataFrame([
        RS.prova_rottura(u, c, n_sim=N_SIM, solo_stagione=so) | {"ipotesi":
            "solo confini di stagione" if so else "tutti i confini di mese"}
        for c in RS.CATEGORIE for so in (False, True)])
    scan_sot = RS.scansione_rottura(u, "in_porta").sort_values(
        "riduzione_devianza", ascending=False)

    # ------------------------------------------------------- ingressi dell'xG
    flag = RS.flag_del_modello(tiri)
    flag_q = flag.pivot(index="flag", columns="stagione", values="quota")
    flag_z = flag.pivot(index="flag", columns="stagione", values="z")
    flag_mod = {f: RS.confronto_modelli(u, f) for f in RS.FLAG_MODELLO
                if u[f].sum() > 100}
    flag_ann = {f: RS.test_annidati(u, f) for f in flag_mod}
    flag_rot = pd.DataFrame([
        RS.prova_rottura(u, f, n_sim=N_SIM, solo_stagione=True)
        for f in flag_mod])
    flag_mde = {f: RS.mde_gradino(u, f) for f in flag_mod}

    # ------------------------------------------------------------- annotazione
    coerenza = RS.coerenza_flag_opta(tiri)
    igiene = RS.igiene_annotazione(tiri)
    freq = RS.frequenze_qualifier(tiri)
    instabili = RS.qualifier_instabili(tiri, freq, soglia_z=SOGLIA_Z_QUALIFIER)
    colonne = RS.colonne_per_stagione(meta)
    col_inst = RS.colonne_instabili(colonne)

    # `StandingSave`: e' o non e' una proprieta' della singola pagina?
    ss = RS.presenza_per_partita(tiri, "StandingSave")
    ss_part = (ss.assign(alta=ss["quota"] >= 0.5)
                 .groupby("stagione")
                 .agg(partite=("quota", "size"), con_qualifier=("alta", "sum"),
                      quota_media=("quota", "mean"))
                 .reset_index())
    ss_mese = (ss.merge(u[["stagione", "matchId", "mese"]].drop_duplicates(),
                        on=["stagione", "matchId"])
                 .groupby("mese")["quota"].agg(["mean", "size"])
                 .reset_index().rename(columns={"mean": "quota_media",
                                                "size": "partite"}))
    # Il passaggio interessante e' l'ultimo: i mesi precedenti stanno tutti
    # attorno a 0.80 e occuperebbero quaranta righe per dire "niente".
    taglio = ss_mese["mese"] >= "2024-08"
    ss_mese_dopo = ss_mese[taglio]
    # Per l'intervallo di riferimento contano i mesi pieni: le code di giugno
    # hanno una o due partite e darebbero un minimo che e' rumore di una sola.
    ss_mese_prima = ss_mese[~taglio & (ss_mese["partite"] >= 10)]

    # ------------------------------------------------------- casa / trasferta
    campo = (u.groupby(["stagione", "h_a"])[["in_porta", "tentativi"]].mean()
             .round(4).reset_index()
             .pivot(index="stagione", columns="h_a", values="in_porta")
             .reset_index())
    campo["vantaggio"] = campo["h"] / campo["a"]

    # --------------------------------------------------------------- il report
    p_sot = float(rotture.query("categoria == 'in_porta' and "
                                "ipotesi == 'solo confini di stagione'")["p_max"].iloc[0])
    p_sot_tutti = float(rotture.query("categoria == 'in_porta' and "
                                      "ipotesi == 'tutti i confini di mese'")["p_max"].iloc[0])
    mde_sot = float(mde["in_porta"]["mde_in_tiri_per_sp"].max())
    phi_sot = float(modelli["in_porta"]["phi"].iloc[0])
    liv_min, liv_max = stag["in_porta_per_sp"].min(), stag["in_porta_per_sp"].max()
    ten_min, ten_max = stag["tentativi_per_sp"].min(), stag["tentativi_per_sp"].max()
    cnt = flag_q.loc["shotCounter"]
    n_confini = int(rotture.query("ipotesi == 'tutti i confini di mese'")
                    ["candidati"].iloc[0])
    n_valide = len(RS.unita_valide(u))

    # Quali flag si muovono davvero, invece di dirlo a memoria.
    mossi = [f for f in flag_mod
             if flag_mod[f].sort_values("QAIC").iloc[0]["modello"] != "M0 costante"]
    deriva = [f for f in mossi
              if flag_mod[f].sort_values("QAIC").iloc[0]["modello"] == "M2 deriva continua"]
    conf_2024 = [f for f in mossi if flag_rot.set_index("categoria")
                 .loc[f, "confine_migliore"] == "2024-08"]
    ss_prime = ss_part.iloc[:4]
    ss_tot_prime = int(ss_prime["partite"].sum())
    ss_con_prime = int(ss_prime["con_qualifier"].sum())

    L = [
        "# Fase 7 — stabilita' del criterio di rilevazione fra stagioni", "",
        "L'acquisizione WhoScored 2021-2026 si e' chiusa con un limite "
        "dichiarato: *\"nessuna verifica di stabilita' del criterio di "
        "rilevazione fra stagioni. Schema identico non implica annotazione "
        "identica: da misurare prima di stimare `rho` su cinque stagioni.\"* "
        "Questo blocco e' quella misura. **Non e' stato scaricato niente**: "
        f"gira sui {_n(meta.shape[0])} CSV gia' su disco.",
        "",
        "## Esito in breve", "",
        "1. **La definizione di tiro in porta e' stabile su tutte e cinque le "
        "stagioni, e non e' un giudizio: e' un'identita' esatta.** La regola "
        "del repository e il flag Opta nativo `shotOnTarget` coincidono "
        "**evento per evento**, con **zero** discordanze in ciascuna delle "
        "cinque stagioni. La Fase 0 lo aveva verificato sul solo 2025-26 "
        "(3066 = 3066); ora vale su 47.530 tentativi.",
        f"2. **I rapporti fra le quattro categorie non si muovono.** La quota "
        f"di tentativi che finisce in porta sta fra "
        f"{stag['q_in_porta'].min():.4f} e {stag['q_in_porta'].max():.4f}; "
        f"contro il numero unico ({float(stag['in_porta'].sum() / stag['tentativi'].sum()):.4f}) "
        f"nessuna stagione supera 2.3 deviazioni standard binomiali, e con la "
        f"sovradispersione osservata (`phi` = {phi_sot:.3f}) il gradino di "
        f"stagione non batte il baseline costante "
        f"(F = {float(annidati['in_porta']['F'].iloc[0]):.2f}, "
        f"p = {float(annidati['in_porta']['p'].iloc[0]):.3f}).",
        f"3. **Il livello invece si muove, e si muove come si muove il "
        f"calcio.** I tentativi per squadra-partita scendono da "
        f"{ten_max:.2f} a {ten_min:.2f} e i tiri in porta da {liv_max:.3f} a "
        f"{liv_min:.3f}: **-{100 * (1 - liv_min / liv_max):.1f}%** in cinque "
        "stagioni. Ma la **ripartizione** fra le categorie resta ferma, ed e' "
        "la firma di \"si tira di meno\", non di \"si conta diversamente\".",
        f"4. **Gli ingressi dell'xG interno, invece, non sono stabili — ed e' "
        f"il risultato che il blocco non si aspettava.** `shotCounter` passa "
        f"dal {100 * cnt.iloc[0]:.1f}% al {100 * cnt.iloc[-1]:.1f}% dei "
        f"tentativi, `shotOpenPlay` dal "
        f"{100 * flag_q.loc['shotOpenPlay'].iloc[0]:.1f}% al "
        f"{100 * flag_q.loc['shotOpenPlay'].iloc[-1]:.1f}%. Sono le colonne "
        "che `sot/xg.py` usa come predittori. **La definizione di SoT e' "
        "salva, quella del contesto del tiro no.**",
        "5. **Un qualifier sparisce, e sparisce per pagina intera.** "
        f"`StandingSave` sta sull'{100 * float(ss_part['quota_media'].iloc[0]):.0f}% "
        "dei tentativi nelle prime quattro stagioni e sul "
        f"{100 * float(ss_part['quota_media'].iloc[-1]):.1f}% nel 2025-26, con "
        f"**{int(ss_part['con_qualifier'].iloc[-1])} partite su "
        f"{int(ss_part['partite'].iloc[-1])}** che lo conservano e le altre a "
        "zero esatto. Non e' un travaso graduale: e' una proprieta' della "
        "singola pagina della fonte. Non tocca niente di cio' che il modello "
        "usa, ma dice che **il livello dei qualifier non e' garantito stabile** "
        "e che le colonne da esso derivate vanno verificate una per una prima "
        "dell'uso, non assunte.",
        f"6. **Il risultato negativo ha la sua potenza dichiarata.** Un gradino "
        f"al confine di stagione sulla quota di tiri in porta verrebbe visto se "
        f"valesse almeno **{mde_sot:.2f} tiri in porta per squadra-partita** "
        f"(80% di potenza, 5%). Sotto quella soglia questo blocco non lo "
        f"distingue dal rumore. Che la macchina abbia sensibilita' non e' "
        "un'assunzione: **la stessa macchina, sulle stesse unita', trova la "
        f"deriva di `shotCounter` con F = "
        f"{float(flag_ann['shotCounter']['F'].iloc[1]):.0f}**.",
        "",
        "> **Per la Fase 7B/7D**: `rho` puo' essere stimato sulle cinque "
        "stagioni **sui tiri in porta**, ma sugli **eccessi relativi** (rapporto "
        "alla media di campionato della stagione), non sugli scarti assoluti — "
        "la media di campionato si e' mossa del "
        f"{100 * (liv_max / liv_min - 1):.1f}% per ragioni di gioco, e uno "
        "scarto assoluto di +1 tiro non significa la stessa cosa nel 2021-22 e "
        "nel 2025-26. Quello che **non** si puo' fare senza altri controlli e' "
        "stimare l'xG interno su piu' stagioni insieme.", "",
        "---", "",
        "## 1. Su cosa gira", "",
        _md(meta.groupby("stagione").agg(
            file=("matchId", "size"), eventi=("n_eventi", "sum"),
            colonne_min=("n_colonne", "min"), colonne_max=("n_colonne", "max"),
        ).reset_index(), 0),
        "",
        "Le 12 partite che WhoScored non ha (`manifest.json`, "
        "`assenti_alla_fonte`) restano fuori, e la loro assenza **non e' "
        "casuale rispetto alla squadra** (6 all'Atalanta). Per questo blocco il "
        "rischio e' contenuto: tutte le grandezze qui sono rapporti o medie su "
        "decine di migliaia di tiri, e sei partite di una squadra su 1.889 non "
        "spostano una quota. Sarebbe un problema serio per una stima **per "
        "squadra**, che qui non si fa.", "",
        "Le unita' sono **squadra-partita**, non tiri: i tiri della stessa "
        f"squadra nella stessa partita non sono indipendenti. Sono {_n(len(u))} "
        "righe, ricostruite dalle due squadre di ogni file e non dai tiri, "
        f"perche' {len(u) - n_valide} squadre-partita nel campione hanno **zero "
        "tentativi** (Pisa-Cremonese del 2026-05-10 e una del 2021-22) e "
        "ricostruendo dai tiri sparirebbero dal denominatore.", "",
        "### Le quattro categorie", "",
        "Sono una **partizione** dei tentativi, verificata riga per riga: "
        "`in porta + respinto da un difensore + palo + fuori = tentativi`, "
        "sempre. E' cio' che le rende diagnostiche: un confine che si sposta "
        "si vede come travaso fra due categorie, a totale fermo.", "",
        "---", "",
        "## 2. I livelli: qui qualcosa si muove", "",
        _md(stag[["stagione", "partite", "squadra_partita", "tentativi",
                  "tentativi_per_sp", "in_porta_per_sp", "bloccato_per_sp",
                  "palo_per_sp", "fuori_per_sp"]]),
        "",
        "Contro il baseline stupido — **una media sola per tutte e cinque le "
        "stagioni** — con l'errore standard campionario vero:", "",
        "**Tentativi per squadra-partita**", "", _md(liv_tent),
        "", "**Tiri in porta per squadra-partita**", "", _md(liv_sot), "",
        f"Il 2021-22 sta {float(liv_sot['z'].iloc[0]):.2f} errori standard "
        f"sopra la media unica e il 2024-25 "
        f"{abs(float(liv_sot['z'].iloc[3])):.2f} sotto. **Questo movimento e' "
        "vero**, ed e' il primo motivo per cui il blocco non poteva fermarsi "
        "ai livelli: un livello che si muove non dice da solo se a muoversi e' "
        "il calcio o il righello.", "",
        "Effetto minimo rilevabile sui livelli, per confronto:", "",
        _md(mde_sot_liv), "",
        "Il 2025-26 e' la stagione su cui poggiano tutte le Fasi 0-6, e il suo "
        f"livello ({float(stag['in_porta_per_sp'].iloc[-1]):.4f}) riproduce "
        "esattamente il valore di riferimento della Fase 0 (4.034 contro 4.03 "
        "fornito): la catena di lettura di questo blocco e' la stessa del "
        "resto del repository, e su una stagione lo si vede.", "",
        "### Casa e trasferta", "",
        _md(campo.rename(columns={"h": "casa", "a": "trasferta"})), "",
        "Il 2021-22 e' la prima stagione col pubblico tornato "
        "(`config.SEASONS_STORICHE` lo dichiara): il vantaggio del campo di "
        "quella stagione non e' confrontabile con le successive, ed e' un "
        "limite gia' registrato, non una scoperta di questo blocco.", "",
        "---", "",
        "## 3. I rapporti: qui non si muove niente", "",
        "**E' la misura che discrimina.** Un cambio di criterio sposta la "
        "ripartizione fra categorie lasciando il totale quasi fermo; una "
        "variazione di gioco sposta il totale lasciando la ripartizione ferma. "
        "Quello che si osserva e' il secondo caso.", "",
        _md(stag[["stagione", "tentativi", "q_in_porta", "q_bloccato",
                  "q_palo", "q_fuori"]]),
        "",
    ]
    for c in RS.CATEGORIE:
        L += [f"**{c}** — contro il numero unico:", "", _md(scarti[c], 5), ""]
    L += [
        "Nessuno `z` binomiale arriva a 2.5, e lo `z` binomiale e' gia' la "
        "versione **ottimistica**: ignora che i tiri della stessa partita sono "
        "correlati. Con la sovradispersione dentro, i valori si dividono per "
        f"circa `sqrt(phi)`.", "",
        "---", "",
        "## 4. Gradino o deriva", "",
        "Quattro modelli sulla stessa quantita', tutti sulle stesse unita' "
        "squadra-partita, confrontati in **quasi-verosimiglianza** con `phi` "
        "stimato dal modello piu' ricco (cella stagione x mese):", "",
        "| modello | cosa afferma |", "|---|---|",
        "| M0 costante | il baseline stupido: un tasso solo, sempre |",
        "| M1 gradino di stagione | il criterio cambia **solo** ai confini di stagione |",
        "| M2 deriva continua | il tasso si muove piano, nel logit, lungo il tempo |",
        "| M3 mese di calendario | e' stagionalita' calcistica, uguale ogni anno |",
        "",
        "M1 contro M2 e' il confronto che decide e **non e' annidato**: si "
        "legge sulla QAIC, non su un test. M3 esiste perche' senza di lui un "
        "effetto di calendario che si ripete ogni anno — inverno, fatica, "
        "campi pesanti — verrebbe letto come gradino.", "",
    ]
    for c in RS.CATEGORIE:
        L += [f"### {c}", "", _md(modelli[c], 3), "", _md(annidati[c]), ""]
    L += [
        "**Su tutte e quattro le categorie nessun modello batte il baseline "
        "costante.** La lettura non e' l'ordinamento nudo — un parametro in "
        "piu' arriva primo per caso circa una volta su sei — ma la distanza in "
        "QAIC, la cui soglia convenzionale e' 2. Il caso meno tranquillo e' "
        "`in_porta`, dove M1 e M2 stanno a meno di un punto dal baseline: non "
        "e' preferenza per il gradino, e' indifferenza.", "",
        "---", "",
        "## 5. Dove cadrebbe il gradino, se ci fosse", "",
        "Un gradino solo, provato in **tutti** i confini di mese. Il punto non "
        "e' se esista un confine che migliora l'adattamento — ne esiste sempre "
        f"uno, e' il massimo di {n_confini} numeri positivi — ma **dove cade** "
        "e **quanto vale rispetto al massimo che il caso produce**.", "",
        "I sei confini migliori per `in_porta`:", "",
        _md(scan_sot.head(6), 3), "",
        f"Il massimo cade a **{scan_sot['prima_di'].iloc[0]}**, cioe' "
        "esattamente al passaggio 2021-22 -> 2022-23. Ma la sua altezza va "
        "confrontata con la distribuzione del massimo **sotto l'ipotesi che non "
        "ci sia nessun gradino**, simulata con i denominatori veri e la "
        f"sovradispersione osservata ({_n(N_SIM)} repliche beta-binomiali):", "",
        _md(rotture[["categoria", "ipotesi", "candidati", "confine_migliore",
                     "riduzione_osservata", "mediana_nulla", "q95_nulla",
                     "p_max", "quota_nulla_su_confine_stagione"]], 4), "",
        "Due letture, e vanno tenute insieme:", "",
        f"- **cercando ovunque** il massimo osservato su `in_porta` non e' "
        f"raro (p = {p_sot_tutti:.2f}): il caso produce spesso di meglio;",
        f"- **cercando solo dove l'ipotesi lo prevede** — i quattro confini di "
        f"stagione, dichiarati in anticipo — il test guadagna potenza e "
        f"`in_porta` arriva a **p = {p_sot:.3f}**, che e' al limite. Non e' "
        "corretto per aver provato quattro categorie: con Bonferroni vale "
        f"{min(1.0, 4 * p_sot):.2f}, e non passa.",
        "",
        "Sotto l'ipotesi nulla il massimo cade su un confine di stagione solo "
        f"nel {100 * float(rotture.query('ipotesi == \"tutti i confini di mese\"')['quota_nulla_su_confine_stagione'].mean()):.0f}% "
        "delle repliche: che il migliore osservato ci cada e' un indizio, non "
        "una prova, e riguarda **il passaggio 2021-22 -> 2022-23** — cioe' "
        "l'uscita dalla stagione che il progetto gia' dichiara non "
        "confrontabile per il ritorno del pubblico. La spiegazione piu' "
        "economica non e' un cambio di criterio.", "",
        "---", "",
        "## 6. La potenza del risultato negativo", "",
        "Un risultato negativo senza potenza dichiarata non e' un risultato — "
        "e' la lezione della Fase 6D, e qui vale identica. Effetto minimo "
        "rilevabile di un gradino sulla quota di tiri in porta, a ciascun "
        "confine di stagione, con l'80% di potenza al 5%:", "",
        _md(mde["in_porta"], 5), "",
        f"**Un gradino di annotazione piu' piccolo di ~{mde_sot:.2f} tiri in "
        "porta per squadra-partita passerebbe inosservato.** E' il 4-5% del "
        "livello: non e' una sensibilita' eccezionale, ed e' il limite "
        "principale di questo blocco. Va confrontato con cio' che deve "
        "sopportare: l'eccesso del Como sulla media di campionato vale 1.07 "
        f"tiri, quindi un gradino non rilevabile arriva al "
        f"{100 * mde_sot / 1.0711:.0f}% dell'eccesso di una squadra di vertice.",
        "",
        "**Il controllo positivo.** Che la macchina abbia sensibilita' non e' "
        f"un'assunzione: la stessa procedura, sulle stesse {_n(n_valide)} "
        "unita', vede senza sforzo la deriva di `shotCounter` (paragrafo 8). "
        "Se non ci fosse sensibilita' non vedrebbe nemmeno quella.", "",
        "---", "",
        "## 7. L'identita' con il flag Opta nativo", "",
        "**E' il risultato piu' forte del blocco, perche' non passa da nessun "
        "modello.** La regola del repository "
        "(`isShot AND ((SavedShot AND NOT shotBlocked) OR (Goal AND NOT "
        "isOwnGoal))`) viene confrontata evento per evento con il flag Opta "
        "`shotOnTarget` presente nei dati:", "",
        _md(coerenza, 0), "",
        "Zero discordanze in entrambe le direzioni, in tutte e cinque le "
        "stagioni. Qualunque cosa sia cambiata nel feed, **non e' cambiato il "
        "rapporto fra la nostra definizione e quella della fonte**.", "",
        "---", "",
        "## 8. Gli ingressi dell'xG interno: qui il criterio si muove", "",
        "Le colonne booleane che `sot/xg.py` usa come predittori sono derivate "
        "da `satisfiedEventsTypes`, cioe' dallo stesso strato di annotazione "
        "dei qualifier. Quota sui tentativi, per stagione:", "",
        flag_q.round(4).to_markdown(), "",
        "Lo stesso in deviazioni standard binomiali dal numero unico:", "",
        flag_z.round(2).to_markdown(), "",
        "`shotDirectCorner` e' praticamente sempre falsa (poche unita' in "
        "tutta la storia) e non entra nei confronti che seguono.", "",
    ]
    for f in flag_mod:
        L += [f"### {f}", "", _md(flag_mod[f], 2), "", _md(flag_ann[f]), ""]
    L += [
        "Massimo gradino ai soli confini di stagione, contro il nullo simulato:",
        "", _md(flag_rot[["categoria", "confine_migliore",
                          "riduzione_osservata", "mediana_nulla", "q95_nulla",
                          "p_max"]], 3), "",
        "Effetto minimo rilevabile, per capire quanto sono grandi questi "
        "movimenti rispetto a cio' che il blocco riesce a vedere:", "",
        _md(pd.concat([flag_mde[f].assign(flag=f) for f in flag_mde])
            [["flag", "confine", "mde_relativo"]], 4), "",
        "Come leggerli:", "",
        f"- **si muovono {len(mossi)} flag su {len(flag_mod)}**: "
        f"{', '.join('`' + f + '`' for f in mossi)}. Sull'unico che resta fermo "
        "(`bigChanceScored`) vince il baseline costante, ed e' il controllo "
        "interno che non e' la procedura a vedere gradini ovunque;",
        f"- **la deriva vince sul gradino** su {len(deriva)} dei {len(mossi)} "
        "che si muovono: M2 batte M1 sulla QAIC pur avendo tre parametri in meno, "
        "quindi il movimento e' **graduale** e distribuito su cinque stagioni, "
        "non un salto a una data precisa. E' la firma che questo modulo "
        "attribuisce al calcio, non all'annotazione;",
        f"- **ma e' un movimento enorme.** `shotCounter` piu' che raddoppia "
        f"({100 * cnt.iloc[0]:.1f}% -> {100 * cnt.iloc[-1]:.1f}%), contro un "
        f"effetto minimo rilevabile del "
        f"{100 * flag_mde['shotCounter']['mde_relativo'].min():.0f}% relativo. "
        "`shotOpenPlay` scende di "
        f"{100 * (flag_q.loc['shotOpenPlay'].iloc[0] - flag_q.loc['shotOpenPlay'].iloc[-1]):.1f} "
        "punti. Che sia gioco davvero cambiato o criterio scivolato, "
        "**l'effetto sul modello e' lo stesso**: un xG stimato su cinque "
        "stagioni insieme impara un predittore che non significa la stessa "
        "cosa alle due estremita' del campione;",
        f"- **il singolo confine peggiore cade a 2024-08 per {len(conf_2024)} "
        f"flag su {len(mossi)}**, e li' il gradino non e' rumore. Chi volesse usare gli "
        "eventi di piu' stagioni ha due strade: stimare l'xG **per stagione** "
        "(costoso in dati, ma non mescola definizioni) oppure tenere la "
        "stagione come effetto esplicito nel modello. Non c'e' una terza "
        "strada che consista nel non accorgersene.", "",
        "---", "",
        "## 9. I qualifier, uno per uno", "",
        f"Presenza per tiro, per stagione, su {len(freq)} qualifier distinti. "
        "Si conta la **presenza sul tiro**, non le occorrenze: cosi' la "
        "grandezza e' una proporzione con denominatore noto e la variabilita' "
        "attesa sotto stabilita' e' calcolabile.", "",
        f"Quelli che compaiono, spariscono, o saltano di piu' di "
        f"{SOGLIA_Z_QUALIFIER:.0f} deviazioni standard fra stagioni adiacenti:",
        "", _md(instabili, 4), "",
        "La soglia e' alta di proposito: con novemila tiri per stagione uno "
        "`z` di 3 lo produce qualunque fluttuazione reale di stile di gioco, e "
        "la domanda qui non e' se il calcio sia cambiato.", "",
        "### `StandingSave`: il caso che vale la pena guardare", "",
        _md(ss_part, 4), "",
        "**Non e' un travaso graduale: e' una proprieta' della singola "
        f"pagina.** Nelle prime quattro stagioni il qualifier sta su piu' della "
        f"meta' dei tiri in **ogni** partita ({_n(ss_con_prime)} partite su "
        f"{_n(ss_tot_prime)}); nel 2025-26 lo conservano "
        f"{int(ss_part['con_qualifier'].iloc[-1])} partite su "
        f"{int(ss_part['partite'].iloc[-1])} e le altre lo hanno a **zero "
        "esatto**, non a un valore basso. Il profilo per mese di partita "
        "attorno al passaggio (nelle stagioni precedenti ogni mese sta fra "
        f"{ss_mese_prima['quota_media'].min():.3f} e "
        f"{ss_mese_prima['quota_media'].max():.3f}):", "",
        _md(ss_mese_dopo, 4), "",
        "Due spiegazioni sono compatibili con questo, e **i dati in casa non "
        "le separano**:", "",
        "1. **l'archivio della fonte**: le pagine della stagione 2025-26 sono "
        "annotate diversamente da quelle delle stagioni chiuse;",
        "2. **il momento del prelievo**: le pagine vengono arricchite dopo "
        "qualche tempo, e la 2025-26 e' stata scaricata piu' vicino alle "
        "partite.",
        "",
        "La seconda **non e' esclusa dai tempi di download** — i file delle "
        "cinque stagioni hanno `mtime` fra il 29 luglio e il 1 agosto 2026, "
        "ma quello del 2025-26 potrebbe essere stato riscritto dallo "
        "spostamento della 7A. **L'esperimento che le separa e' un solo GET** "
        "su una partita 2025-26 gia' in casa, confrontando il qualifier: non e' "
        "stato fatto perche' questo blocco non scarica. Va messo in conto al "
        "primo blocco che tocca la rete.", "",
        "**Non tocca niente di cio' che il modello usa** — `StandingSave` non "
        "compare in nessuna colonna di `io_events.BOOL_COLS` ne' in `shots.py`. "
        "Conta come avvertimento: il livello dei qualifier **non e' garantito "
        "stabile**, e ogni colonna da esso derivata va verificata prima "
        "dell'uso invece che assunta. Le tre di cui sopra lo erano gia'.", "",
        "### Le colonne dei CSV", "",
        "Presenza per stagione, frazione dei file. Su 259 colonne una sola non "
        "e' presente ovunque:", "", col_inst.round(4).to_markdown(), "",
        "Ed e' **la trappola gia' nota**: pandas emette `isOwnGoal` solo se in "
        "quella partita c'e' stato un autogol. La quota per stagione (6-10%) e' "
        "la frequenza degli autogol, non un cambio di schema. Nessuna colonna "
        "compare o sparisce fra stagioni.", "",
        "### Igiene dell'annotazione", "", _md(igiene, 5), "",
        "`x_medio` e `x_sotto_50` confermano su tutte e cinque le stagioni "
        "l'orientamento delle coordinate accertato nella Fase 0 (si attacca "
        "sempre verso x = 100). `situation_nulla` **raddoppia** fra la prima e "
        "l'ultima stagione: e' un campo che il progetto non usa — i rigori si "
        "identificano da `penaltyScored | penaltyMissed` proprio perche' "
        "`situation` e' inutilizzabile — ma e' un altro segnale che lo strato "
        "descrittivo della fonte si e' mosso mentre quello strutturale no.", "",
        "---", "",
        "## 10. Cosa ne segue, operativamente", "",
        "| domanda | risposta di questo blocco |", "|---|---|",
        "| Si puo' stimare `rho` sui tiri in porta delle cinque stagioni? | "
        "**Si'**, sulla definizione: e' identica al flag della fonte in tutte e "
        "cinque, e le quote fra categorie non si muovono. |",
        "| Sugli scarti assoluti dalla media di campionato? | **No.** La media "
        f"di campionato si e' mossa del {100 * (liv_max / liv_min - 1):.1f}% "
        "per ragioni di gioco: +1 tiro di eccesso nel 2021-22 e nel 2025-26 non "
        "sono la stessa cosa. Usare eccessi **relativi**. |",
        "| Si puo' stimare l'xG interno su piu' stagioni insieme? | **No, non "
        "senza un termine di stagione**: `shotOpenPlay` e `shotCounter` si "
        "muovono di molto piu' del rilevabile, e il singolo salto piu' grande "
        "cade fra 2023-24 e 2024-25. |",
        "| Si possono usare i qualifier come predittori multi-stagione? | "
        "**Uno alla volta e solo dopo averlo verificato.** `StandingSave` "
        "mostra che un qualifier puo' sparire per intero senza che schema, "
        "conteggio colonne o numero di eventi se ne accorgano. |",
        "| Il 2021-22 e' confrontabile con le altre? | Sul criterio si'. Sul "
        "**vantaggio del campo** no, ed era gia' dichiarato: e' la prima "
        "stagione col pubblico tornato. |",
        "",
        "---", "",
        "## Limiti di questo blocco", "",
        f"- **La sensibilita' e' quella che e'**: un gradino sotto "
        f"~{mde_sot:.2f} tiri in porta per squadra-partita non verrebbe visto. "
        "Il blocco esclude un cambio di criterio **grande**, non un cambio di "
        "criterio.",
        "- **Non separa \"il criterio e' cambiato\" da \"il calcio e' cambiato "
        "bruscamente a fine giugno\".** Nessun dato interno alla fonte puo' "
        "farlo: la firma delle due ipotesi e' la stessa. Il blocco dice quale "
        "sia la spiegazione piu' economica, non quale sia vera.",
        "- **Una fonte sola.** Tutto qui dentro e' WhoScored contro WhoScored. "
        "Il confronto con una definizione **esterna** e' un'altra cosa ed e' il "
        "blocco 7C.",
        "- **Non e' una verifica per squadra.** Le 12 partite mancanti sono "
        "concentrate su una squadra (6 all'Atalanta): irrilevante per le quote "
        "di campionato calcolate qui, non irrilevante per una stima per squadra.",
        "- **`StandingSave` resta senza spiegazione accertata**, e l'esperimento "
        "che la darebbe richiede una richiesta di rete che questo blocco non "
        "fa.",
        "- **Niente di questo blocco entra nel modello.** Nessuno script delle "
        "Fasi 1-6 importa `recording_stability`, e i numeri pubblicati sono "
        "stati rieseguiti dopo: invariati.",
    ]

    path = config.REPORTS / "phase7_stabilita_rilevazione.md"
    path.write_text("\n".join(L), encoding="utf-8")
    mese.to_csv(config.REPORTS / "phase7_stabilita_mensile.csv", index=False)
    freq.to_csv(config.REPORTS / "phase7_stabilita_qualifier.csv")

    print(f"  {len(u)} squadra-partita, {int(u['tentativi'].sum())} tentativi")
    print(f"  regola SoT = flag Opta in tutte le stagioni: "
          f"{bool(coerenza['identiche'].all())}")
    print(f"  quota in porta: {stag['q_in_porta'].min():.4f} - "
          f"{stag['q_in_porta'].max():.4f} (phi = {phi_sot:.3f})")
    print(f"  gradino di stagione su in_porta: p = {p_sot:.3f} "
          f"(MDE {mde_sot:.2f} tiri/squadra-partita)")
    print(f"  shotCounter: {cnt.iloc[0]:.4f} -> {cnt.iloc[-1]:.4f} "
          f"(deriva, non gradino)")
    print(f"  report -> {path}")


if __name__ == "__main__":
    main(force="--force" in sys.argv)
