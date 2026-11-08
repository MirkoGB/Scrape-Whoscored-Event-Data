# -*- coding: utf-8 -*-
"""Risoluzione di campionato + stagione per lo scraper WhoScored.

Separato da `scrape_season.py` per una ragione precisa: **qui non si importa
selenium**. Ne segue che la parametrizzazione e' verificabile dai test senza
browser, senza rete e senza toccare WhoScored — i cui termini d'uso non sono
ancora stati accertati (`docs/regole_fantacalcio.md` §7.1, terza conseguenza).
Se la logica stesse dentro lo scraper, l'unico modo di provarla sarebbe
eseguirlo.

Due convenzioni si incontrano qui, e il punto del modulo e' tenerle separate:

| | forma | dove vive |
| --- | --- | --- |
| repository | `2025-2026` | `sot/config.py`, nomi di cartella |
| WhoScored | `2025/2026` (a volte `2025/26`) | solo il menu a tendina del sito |

La conversione sta in questo file e **non** in `config.py`: la forma del sito e'
una proprieta' della fonte, e far entrare la convenzione di una fonte nella
tassonomia e' esattamente cio' che la Fase 7A ha evitato scegliendo
`ITA-serie-a` invece di `I1`.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from sot import config  # noqa: E402


def stagione_whoscored(season: str) -> str:
    """`2025-2026` -> `2025/2026`, la forma del menu a tendina del sito.

    Passa da `config._check_season` invece di fare una `replace` diretta: cosi'
    una stagione mal formata fallisce qui, prima di aprire un browser, e non
    dentro `_select_season` dopo trenta secondi di attesa su una pagina.
    """
    config._check_season(season)
    return season.replace("-", "/")


@dataclass(frozen=True)
class Target:
    """Una coppia campionato-stagione, e tutti i percorsi che ne discendono.

    Immutabile di proposito: uno scraper che gira su cinque stagioni non deve
    poter riscrivere il proprio bersaglio a meta' esecuzione. Prima della
    parametrizzazione questi erano cinque variabili globali del modulo, ed e'
    la ragione per cui una sola stagione alla volta era possibile.
    """

    league: str = config.LEAGUE
    season: str = config.SEASON

    def __post_init__(self):
        config._check_league(self.league)
        config._check_season(self.season)
        if config.LEAGUE_CODES[self.league]["whoscored"] is None:
            raise ValueError(
                f"per {self.league} i codici WhoScored non sono stati verificati: "
                "vanno accertati e dichiarati in config.LEAGUE_CODES, non inventati qui"
            )

    # ---- la fonte -------------------------------------------------------
    @property
    def stagione_sito(self) -> str:
        return stagione_whoscored(self.season)

    @property
    def percorso_competizione(self) -> str:
        c = config.LEAGUE_CODES[self.league]["whoscored"]
        return f"/regions/{c['regione']}/tournaments/{c['torneo']}/{c['slug']}"

    def url_competizione(self, main_url: str) -> str:
        return main_url.rstrip("/") + self.percorso_competizione

    # ---- le destinazioni ------------------------------------------------
    @property
    def dir_partite(self) -> Path:
        """Un CSV per partita. E' grezzo: non si sovrascrive mai (vincolo 9)."""
        return config.raw_dir("whoscored", self.league, self.season) / "events"

    @property
    def cache_url(self) -> Path:
        return config.raw_dir("whoscored", self.league, self.season) / "matches.json"

    @property
    def cache_calendario(self) -> Path:
        """Le partite ANCORA DA GIOCARE, in un file **separato** da `matches.json`.

        Il perche' della separazione sta in `config.calendario_json`, ed e'
        misurabile: `report_completeness` usa `matches.json` come criterio di
        arresto e `avanzamento` come denominatore di "partite viste". Mescolarci
        le future romperebbe entrambi in silenzio.
        """
        return config.calendario_json(self.league, self.season)

    @property
    def file_unito(self) -> Path:
        """Concatenazione dei CSV: derivata, quindi sotto `processed/`.

        Non si scrive per default. Su cinque stagioni sarebbero cinque copie da
        1 GB di dati gia' presenti — esattamente cio' che la Fase 7A ha
        cancellato. Serve `--merge` per chiederla.
        """
        return config.processed_dir(self.league, self.season) / "events_concat.csv"

    def __str__(self) -> str:
        return f"{self.league} {self.season}"


def targets(league: str | None = None, seasons=None) -> list[Target]:
    """Bersagli da scaricare, in ordine cronologico.

    `seasons=None` significa **tutto il perimetro storico dichiarato**
    (`config.SEASONS_STORICHE`), non "la stagione corrente": chi lancia lo
    script senza argomenti vuole le cinque stagioni, ed e' il caso d'uso per cui
    la parametrizzazione e' stata chiesta.
    """
    league = config.LEAGUE if league is None else league
    seasons = config.SEASONS_STORICHE if not seasons else tuple(seasons)
    return [Target(league, s) for s in sorted(seasons)]


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Scarica i dati evento WhoScored per una o piu' stagioni.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""esempi:
  scrape_season.py --dry-run                    cosa farebbe, senza browser
  scrape_season.py                              tutte e cinque le stagioni
  scrape_season.py --season 2021-2022           una sola
  scrape_season.py --season 2021-2022 2022-2023 due, in ordine
  scrape_season.py --season 2026-2027 --in-corso  la stagione ancora aperta
""",
    )
    p.add_argument(
        "--league", default=config.LEAGUE, choices=sorted(config.LEAGUE_CODES),
        help="campionato (default: %(default)s)",
    )
    p.add_argument(
        "--season", nargs="+", metavar="AAAA-AAAA",
        help=f"stagioni nella forma 2021-2022. Default: tutte "
             f"({', '.join(config.SEASONS_STORICHE)})",
    )
    p.add_argument(
        "--dry-run", action="store_true",
        help="stampa bersagli, percorsi e stato di avanzamento e si ferma. "
             "Non apre il browser e non tocca la rete",
    )
    p.add_argument(
        "--refresh-urls", action="store_true",
        help="ri-scansiona il calendario anche se la cache e' gia' completa",
    )
    p.add_argument(
        "--in-corso", action="store_true",
        help="la stagione non e' finita: una sola passata sul calendario, cache "
             "sempre rinfrescata, e l'incompletezza non e' un difetto",
    )
    p.add_argument(
        "--calendario", action="store_true",
        help="raccoglie ANCHE le partite ancora da giocare, navigando il "
             "calendario in avanti, e le scrive in calendario.json (file "
             "separato da matches.json, che resta il criterio di arresto)",
    )
    p.add_argument(
        "--solo-calendario", action="store_true",
        help="raccoglie SOLO il calendario delle partite da giocare, senza "
             "scaricare nessun evento",
    )
    p.add_argument(
        "--merge", action="store_true",
        help="scrive anche la concatenazione dei CSV sotto processed/. "
             "Nessun modulo la legge: e' 1 GB per stagione",
    )
    p.add_argument(
        "--sleep", type=float, default=7.0, metavar="SEC",
        help="pausa fra una partita e l'altra (default: %(default)s). "
             "Abbassarla fa scattare il blocco della fonte",
    )
    return p


def stato(target: Target) -> dict:
    """Quante partite sono gia' su disco. Non tocca la rete.

    E' cio' che rende l'acquisizione ripartibile (vincolo 9) leggibile *prima*
    di lanciarla: se le 380 ci sono gia', non c'e' niente da scaricare e lo si
    sa senza aprire un browser.
    """
    scaricate = len(list(target.dir_partite.glob("*.csv"))) if target.dir_partite.is_dir() else 0
    in_cache = 0
    if target.cache_url.is_file():
        import json
        in_cache = len(json.loads(target.cache_url.read_text(encoding="utf-8")))
    return {
        "target": str(target),
        "dir_partite": target.dir_partite,
        "cache_url": target.cache_url,
        "csv_su_disco": scaricate,
        "partite_in_cache": in_cache,
        "da_scaricare": max(in_cache - scaricate, 0) if in_cache else None,
    }

# --------------------------------------------------------------------------
# Completezza del calendario
#
# Sta qui e non nello scraper perche' e' logica pura su una lista di dict:
# nessun browser, nessuna rete, quindi verificabile dai test come il resto
# di questo modulo. Nello scraper era controllabile solo eseguendolo.
# --------------------------------------------------------------------------

def avanzamento(matches):
    """A che punto e' una stagione ANCORA IN CORSO. Logica pura, come la gemella.

    **Non e' `report_completeness` con un flag, ed e' voluto.** Quella risponde
    «il calendario e' completo?» con un booleano che lo scraper usa come criterio
    di arresto. Una stagione in corso e' incompleta **per definizione**: farle
    dire `True` significherebbe far dire «completo» a un calendario che non lo e',
    e chi legge il log non avrebbe modo di distinguere i due casi. Farle dire
    `False` costerebbe `MAX_URL_PASSES` passate di navigazione a ogni esecuzione,
    a cercare partite che non esistono ancora perche' non si sono giocate.

    Quindi la domanda cambia: non «manca qualcosa?» ma «quante se ne sono
    giocate?». Il denominatore si **deduce dalle squadre viste**, mai assunto a
    38: la Bundesliga e la Ligue 1 ne hanno 34 (18 squadre), ed e' lo stesso
    motivo per cui `report_completeness` non ha un 38 scritto dentro.

    Attenzione al limite dichiarato: finche' una squadra non e' mai comparsa, il
    conteggio delle squadre e' sottostimato e con lui il numero atteso di
    partite. Alla prima giornata i numeri sono grezzi; dalla seconda in poi tutte
    le squadre hanno giocato e il denominatore e' quello vero.
    """
    per_team = {}
    for match in matches:
        for team in (match['home'], match['away']):
            per_team[team] = per_team.get(team, 0) + 1

    squadre = len(per_team)
    per_squadra = (squadre - 1) * 2 if squadre else 0
    attese = squadre * per_squadra // 2 if squadre else 0
    giocate = len(matches)

    info = {
        "squadre": squadre,
        "partite_viste": giocate,
        "partite_attese": attese,
        "per_squadra_attese": per_squadra,
        "per_squadra_min": min(per_team.values()) if per_team else 0,
        "per_squadra_max": max(per_team.values()) if per_team else 0,
        "quota": giocate / attese if attese else 0.0,
    }
    print("")
    print(f"Stagione in corso: {squadre} squadre | {giocate} partite giocate "
          f"su {attese} del calendario ({info['quota']:.0%}) | "
          f"per squadra {info['per_squadra_min']}-{info['per_squadra_max']} "
          f"su {per_squadra}")
    return info


def report_completeness(matches):
    """Il calendario e' completo? In Serie A ogni squadra gioca 38 partite.

    **Piu' di 38 non e' un calendario incompleto**, ed e' la distinzione che
    questa funzione all'inizio non faceva: confrontava con `!= expected`, quindi
    una squadra con 39 partite finiva nell'elenco delle mancanti sotto
    l'intestazione "squadre con meno di 38".

    Non e' teorico. La 2022-2023 ha uno stage in piu', `Serie A Relegation
    Playoff`: 381 partite invece di 380, e due squadre a 39. Il calendario era
    completo e veniva dichiarato incompleto, con due conseguenze — quattro
    passate di navigazione buttate a cercare partite che c'erano gia', e un
    messaggio che diceva il falso a chi lo leggeva.

    Lo spareggio **non viene scartato**: e' una partita di Serie A davvero
    giocata. Viene segnalato, perche' rende il conteggio delle due squadre
    coinvolte diverso da quello delle altre diciotto, e chi userra' questi dati
    deve saperlo invece di scoprirlo da un totale che non torna.
    """
    per_team = {}
    for match in matches:
        for team in (match['home'], match['away']):
            per_team[team] = per_team.get(team, 0) + 1

    expected = (len(per_team) - 1) * 2 if per_team else 0
    mancanti = {t: n for t, n in per_team.items() if n < expected}
    extra = {t: n for t, n in per_team.items() if n > expected}

    print(f"\nSquadre: {len(per_team)} | partite totali: {len(matches)} "
          f"(attese: {len(per_team) * expected // 2 if per_team else 0})")

    if extra:
        print(f"{len(extra)} squadre oltre le {expected} partite "
              "(spareggi/playout: partite vere, tenute):")
        for team, n in sorted(extra.items(), key=lambda p: -p[1]):
            print(f"  {n:3d}/{expected}  {team}")

    if not mancanti:
        print('Calendario completo.')
        return True

    print(f"Calendario INCOMPLETO - squadre con meno di {expected} partite:")
    for team, n in sorted(mancanti.items(), key=lambda p: p[1]):
        print(f"  {n:3d}/{expected}  {team}")
    print("Rilancia con --refresh-urls: i risultati si sommano alla cache.")
    return False
