# -*- coding: utf-8 -*-
"""Fase 15 / P1 - le previsioni dei cinque campionati, e la pagina a giornata.

Produce `reports/previsioni.html` (la pagina autonoma) e un CSV per campionato.
Non stima nessun parametro nuovo: e' `previsione.tabella_completa` chiamata una
volta per campionato, `previsione.tabella_calendario` sulle partite da giocare,
piu' il contesto del prior quando la stagione e' agli inizi.

**Un modello per campionato, mai poolati** (regola di E1, riscritta da R0 su G2
e resa un numero dalla Fase 13: il livello dei gol varia del 25% fra i cinque).
Qui la separazione e' strutturale - `tabella_completa(league=...)` legge solo i
Parquet di quel campionato - e la pagina tiene i cinque in blocchi distinti.

**Il ripiego di stagione e' dichiarato, non silenzioso.** Se la stagione chiesta
non ha ancora partite su disco si scende alla piu' recente che ne ha, e la
pagina lo **scrive**: mostrare i numeri dell'anno scorso credendo che siano di
quest'anno e' il difetto peggiore che questa pagina possa avere.

**Il calendario segue la stessa disciplina.** Se la stagione mostrata non e'
quella chiesta, il calendario della stagione in corso **non si attacca**: sono
partite di un'annata e numeri di un'altra, e accostarli sarebbe una divergenza
silenziosa fra la riga e il suo contenuto.

NON tocca la rete e NON scrive sotto `data/`.
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import pagina_previsioni  # noqa: E402
from sot import calendario as CAL, config, previsione as P  # noqa: E402
from sot import prior_stagione as PS, tentativi as T  # noqa: E402
from sot import totale as TOT  # noqa: E402

CAMPIONATI = tuple(sorted(config.LEAGUE_CODES))
OUT_HTML = config.REPORTS / "previsioni.html"


def stagione_disponibile(league: str, chiesta: str) -> tuple[str, str]:
    """La stagione da mostrare, e la nota da scrivere se non e' quella chiesta.

    Si scende alla piu' recente stagione con dati. Il ripiego **si dichiara**:
    una pagina che mostra l'anno scorso senza dirlo e' peggio di una pagina che
    non c'e'.
    """
    def ha_dati(s: str) -> bool:
        p = config.team_match(league=league, season=s)
        if not p.is_file():
            return False
        try:
            return len(T.universo([s], league=league)) > 0
        except Exception:                       # noqa: BLE001
            return False

    if ha_dati(chiesta):
        return chiesta, ""
    for s in reversed(config.SEASONS_STORICHE):
        if ha_dati(s):
            return s, (f"la {chiesta} non ha ancora dati su disco: "
                       f"mostrata la {s}")
    return "", f"nessuna stagione con dati per {league}"


def _calendario(league: str, stagione: str, chiesta: str, tab, contesto):
    """Le partite da giocare con i due totali, e i turni. Puo' essere vuoto.

    **Il calendario non e' una dipendenza**: se manca, o se la stagione mostrata
    non e' quella chiesta, si ritornano due tabelle vuote e la pagina ripiega
    sulla sola modalita' a coppia libera - che e' cio' che faceva la Fase 14.
    Un calendario di un'annata accostato ai numeri di un'altra sarebbe peggio di
    nessun calendario.
    """
    import pandas as pd

    vuoto = (pd.DataFrame(), pd.DataFrame(
        columns=["turno", "etichetta", "fonte", "partite"]))
    if stagione != chiesta:
        return vuoto
    try:
        grezzo = CAL.calendario(league=league, season=chiesta)
    except Exception:                           # noqa: BLE001
        return vuoto
    if grezzo.empty:
        return vuoto

    con_t = CAL.con_turno(grezzo)
    cal = P.tabella_calendario(con_t, stagione, league=league,
                               contesto=contesto, tab=tab)
    if len(cal) == 0:
        return vuoto
    turni = CAL.turni(league=league, cal=grezzo)
    # I turni si filtrano a cio' che e' rimasto: una partita scartata da
    # `tabella_calendario` non deve lasciare un turno vuoto in pagina.
    vivi = set(cal["turno"])
    return cal, turni[turni["turno"].isin(vivi)].reset_index(drop=True)


def blocco(league: str, chiesta: str, verbose: bool = True) -> dict | None:
    """La tabella completa di un campionato, il calendario, e il contesto."""
    stagione, nota = stagione_disponibile(league, chiesta)
    if not stagione:
        if verbose:
            print(f"  {league}: {nota}")
        return None

    # Il contesto serve solo se la stagione e' agli inizi. Costruirlo comunque
    # non fa danno - sopra il burn-in la regola a due regimi non lo usa - ma
    # costa un fit per bersaglio, quindi si evita quando e' inutile.
    u = T.universo([stagione], league=league)
    giornate = int(u.groupby("team")["matchId"].nunique().max())
    contesto = None
    if giornate < config.BURN_IN_ROUND:
        try:
            contesto = PS.contesto(stagione, league=league)
        except Exception as exc:                # noqa: BLE001
            nota = (nota + " - " if nota else "") + f"prior non disponibile: {exc}"

    tab = P.tabella_completa(stagione, league=league, contesto=contesto)
    cal, turni = _calendario(league, stagione, chiesta, tab, contesto)

    cal_tiri = P.calibrazione_totale(league=league, target=T.TARGET)
    cal_sot = P.calibrazione_totale(league=league, target=T.TARGET_PRECISIONE)
    st = P.storia(stagione, league=league)

    if verbose:
        n_prior = int((tab["regime"] != P.REGIMI[1]).sum())
        print(f"  {league}: {stagione} - {len(tab)} coppie - "
              f"{u['matchId'].nunique()} partite - "
              f"{n_prior} righe dal prior - {len(cal)} da giocare in "
              f"{len(turni)} turni" + (f" - {nota}" if nota else ""))

    # **Il contesto esce dal blocco**, e non e' un dettaglio: senza, la tabella
    # del calendario non ha la strada del prior e una squadra che non ha ancora
    # giocato non ha numeri affatto. In Bundesliga sono quattro squadre su
    # diciotto, cioe' 122 partite su 297 che sparirebbero dalla pagina.
    return {"tabella": tab, "stagione": stagione, "nota": nota,
            "contesto": contesto, "calendario": cal, "turni": turni,
            "r_tot": P._r_tot_corrente(st, league=league, target=T.TARGET),
            "r_tot_sot": P._r_tot_corrente(st, league=league,
                                           target=T.TARGET_PRECISIONE),
            "pend_tot": cal_tiri["pendenza"],
            "pend_tot_sot": cal_sot["pendenza"],
            "partite": int(u["matchId"].nunique()),
            "come_di": str(u["date"].max())[:10],
            "squadre": int(tab["squadra"].nunique())}


def limiti(blocchi: dict) -> list[str]:
    """I limiti che vanno accanto ai numeri (vincolo 5).

    I primi vengono da `previsione.limiti()`, gia' scritti da V4; poi quelli del
    **totale**, che sono di T1 e non si riscrivono qui; poi quelli che la Fase 14
    aggiunge, e vanno detti perche' nessuno li dedurrebbe dalla pagina.
    """
    fissi = list(P.limiti())

    # I limiti del totale si **importano** da T1, mai riscritti: sono la stessa
    # frase in un posto solo. Si toglie la riga della quota, che c'e' gia'.
    fissi += [x for x in TOT.limiti() if "vincolo 3" not in x]

    fissi.append(
        f"sotto la {config.BURN_IN_ROUND}a giornata il numero NON viene da questa "
        "stagione: viene dal modello della precedente applicato tale e quale. E' "
        "la forma che la Fase 14 / A2 ha misurato come migliore fra cinque "
        "candidati (t per cluster 4,4 sui tentativi e 4,2 sui tiri in porta, su "
        "20 transizioni), ma resta l'anno scorso")
    fissi.append(
        "le neopromosse non hanno un prior e vengono trattate come esattamente "
        "medie della stagione precedente: e' l'unico default onesto, non una "
        "stima della loro forza")
    fissi.append(
        "i cinque campionati NON si poolano: un modello per campionato, e i "
        "numeri di due campionati non si confrontano fra loro senza tener conto "
        "che il livello si muove (25% sui gol, Fase 13)")
    fissi.append(
        "il TURNO non e' sempre una giornata: dove la fonte non la porta si "
        "ripiega su una deduzione dalla data o su un blocco di date, e la pagina "
        "lo scrive sotto la griglia. Un blocco di date non e' un turno di "
        "campionato")

    ripieghi = [f"{k}: {b['nota']}" for k, b in blocchi.items() if b["nota"]]
    if ripieghi:
        fissi.append("stagione ripiegata - " + " - ".join(ripieghi))
    senza_cal = [k for k, b in blocchi.items() if len(b["calendario"]) == 0]
    if senza_cal:
        fissi.append(
            "senza calendario, quindi con la sola modalita' a coppia libera: "
            + " - ".join(senza_cal))
    parziali = [f"{k} ({b['squadre']} squadre viste)"
                for k, b in blocchi.items() if b["squadre"] < 18]
    if parziali:
        fissi.append(
            "a stagione appena cominciata compaiono solo le squadre che hanno "
            "gia' giocato: " + " - ".join(parziali))
    return fissi


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--league", nargs="+", choices=sorted(config.LEAGUE_CODES),
                   default=list(CAMPIONATI))
    p.add_argument("--season", default=config.SEASON_CORRENTE, metavar="AAAA-AAAA")
    p.add_argument("--csv", action="store_true",
                   help="scrive anche un CSV per campionato")
    args = p.parse_args(argv)
    config._check_season(args.season)
    t0 = time.time()

    print(f"Previsioni - stagione chiesta {args.season}")
    blocchi = {}
    for L in args.league:
        b = blocco(L, args.season)
        if b is not None:
            blocchi[L] = b

    if not blocchi:
        print("Nessun campionato con dati: pagina non scritta.")
        return 1

    pagina_previsioni.scrivi(
        blocchi, OUT_HTML, linee=T.LINEE_TIRI, linee_sot=P.LINEE_SOT,
        linee_tot=TOT.LINEE_TOTALE_TIRI, linee_tot_sot=TOT.LINEE_TOTALE_SOT,
        limiti=limiti(blocchi), burn_in=config.BURN_IN_ROUND,
        regimi=P.REGIMI, fonti_turno=CAL.FONTI_TURNO,
        generato=time.strftime("%Y-%m-%d %H:%M"))
    print(f"-> {OUT_HTML}")

    if args.csv:
        for L, b in blocchi.items():
            f = config.REPORTS / f"previsioni_{L}.csv"
            b["tabella"].to_csv(f, index=False)
            print(f"-> {f}")
            if len(b["calendario"]):
                fc = config.REPORTS / f"previsioni_calendario_{L}.csv"
                b["calendario"].to_csv(fc, index=False)
                print(f"-> {fc}")

    print(f"Fatto in {time.time() - t0:.0f} s.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
