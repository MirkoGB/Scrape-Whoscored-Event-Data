# -*- coding: utf-8 -*-
"""Bersagli dell'acquisizione voti: campionato, stagione, giornata.

Qui **non si importa `requests`**. E' la stessa scelta di
`acquisition/whoscored/target.py` con selenium: la parametrizzazione — quali
pagine, in che ordine, verso quali file — dev'essere verificabile dai test senza
aprire una connessione. Una raccolta che si puo' provare solo eseguendola non si
puo' provare affatto finche' non e' gia' partita.

Tre convenzioni di stagione si incontrano in questo progetto, e il punto del
modulo e' tenerle separate:

| | forma | dove vive |
| --- | --- | --- |
| repository | `2025-2026` | `sot/config.py`, nomi di cartella |
| fantacalcio.it, negli URL | `2025-26` | solo qui dentro |
| fantacalcio.it, negli export | `20` (idStagione) | solo qui dentro, e non serve |

La conversione va in **un verso solo**: `2025-2026` -> `2025-26`. La forma della
fonte non entra mai nella tassonomia, ed e' la stessa regola per cui la cartella
si chiama `ITA-serie-a` e non `I1`.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

from sot import config

FONTE = "fantacalcio"
BASE_URL = "https://www.fantacalcio.it"

# Identificabile e veritiero, come chiede `regole_fantacalcio.md` §4.2.
# **Non e' un `User-Agent` di browser**: dichiarare di essere Chrome per passare
# inosservati sarebbe la forma piu' banale di aggiramento — vietata dall'art.
# 3.3(e) dei Termini e non coperta da nessuna autorizzazione — ed e' anche
# inutile, perche' la fonte serve regolarmente le pagine a questa stringa.
#
# Sta qui e non nello scraper perche' e' il modo in cui il progetto si presenta
# alla fonte: e' parte del bersaglio, e va leggibile senza importare `requests`.
# Se la fonte chiedesse un recapito, va aggiunto qui — ma e' una scelta
# dell'utente, perche' significa mandare un dato personale al sito.
USER_AGENT = ("SoT-Serie-A-research/1.0 (acquisizione autorizzata; "
              "ricerca statistica, nessuna redistribuzione dei contenuti)")

# Il percorso della vista voti dipende dal campionato e **non e' derivabile**
# dal nome della cartella: e' uno slug della fonte. `None` dove non e' stato
# verificato, per la stessa ragione per cui `LEAGUE_CODES["whoscored"]` e' `None`
# fuori dalla Serie A — meglio un errore che un URL inventato che porta altrove.
PERCORSI_VOTI = {
    "ITA-serie-a": "voti-fantacalcio-serie-a",
}

# Il listone. Una pagina per stagione, non per giornata: le quotazioni sono un
# oggetto stagionale. `QI` (quotazione iniziale) e' il prezzo di partenza
# dell'asta, cioe' la grandezza che serve alla verifica principale del progetto;
# `QA` e' un unico valore corrente e **non** una serie storica.
PERCORSI_QUOTE = {
    "ITA-serie-a": "quotazioni-fantacalcio",
}

# Giornate di un campionato a 20 squadre. Non e' un parametro della fonte: e' il
# formato del torneo, e la fonte lo conferma con 38 opzioni nel menu a tendina
# `select#matchweek` di ogni pagina (verificato su 2021-22 e 2025-26).
N_GIORNATE = 38

# idStagione degli endpoint di export `/api/v1/Excel/votes/<id>/<giornata>`,
# verificati uno per uno in `reports/phase7_fattibilita_fonte.md` (addendum).
# **Non servono alla vista HTML** e non sono usati da questo modulo: stanno qui
# perche' sono provenienza gia' accertata e ritrovarli costerebbe cinque
# richieste. Gli endpoint rispondono 401 senza credenziali.
ID_STAGIONE_EXPORT = {
    "2021-2022": 16,
    "2022-2023": 17,
    "2023-2024": 18,
    "2024-2025": 19,
    "2025-2026": 20,
}


def stagione_sito(season: str) -> str:
    """`2025-2026` -> `2025-26`, la forma che sta negli URL della fonte.

    Passa da `config._check_season` invece di tagliare la stringa: cosi' una
    stagione mal formata fallisce qui, prima della prima richiesta, e non
    scaricando 38 pagine 404.
    """
    config._check_season(season)
    inizio, fine = season.split("-")
    return f"{inizio}-{fine[2:]}"


@dataclass(frozen=True)
class TargetVoti:
    """Una coppia campionato-stagione e tutti i percorsi che ne discendono.

    Immutabile: uno scraper che gira su cinque stagioni non deve poter
    riscrivere il proprio bersaglio a meta' esecuzione.
    """

    league: str = config.LEAGUE
    season: str = config.SEASON

    def __post_init__(self):
        config._check_league(self.league)
        config._check_season(self.season)
        if PERCORSI_VOTI.get(self.league) is None:
            raise ValueError(
                f"per {self.league} il percorso della vista voti di {FONTE} non e' "
                "stato verificato: va accertato e dichiarato in PERCORSI_VOTI, "
                "non inventato qui"
            )

    # ---- la fonte -------------------------------------------------------
    @property
    def slug_stagione(self) -> str:
        return stagione_sito(self.season)

    def url(self, giornata: int) -> str:
        _check_giornata(giornata)
        return f"{BASE_URL}/{PERCORSI_VOTI[self.league]}/{self.slug_stagione}/{giornata}"

    # ---- le destinazioni ------------------------------------------------
    @property
    def dir_grezzo(self) -> Path:
        """Una pagina per giornata. E' grezzo: non si sovrascrive mai (vincolo 9)."""
        return config.raw_dir(FONTE, self.league, self.season) / "voti"

    def percorso(self, giornata: int) -> Path:
        """`.html.gz`, e la compressione e' una scelta dichiarata.

        Una pagina pesa ~1,2 MB di cui la quasi totalita' e' impalcatura del
        sito; per cinque stagioni sarebbero ~230 MB. Gzip e' **senza perdita**,
        quindi il grezzo resta grezzo: `pagina.leggi()` restituisce gli stessi
        byte che sono arrivati dalla rete. La compressione e' scritta con
        `mtime=0` perche' altrimenti lo stesso HTML darebbe file diversi a ogni
        scrittura, e l'hash del manifest smetterebbe di significare qualcosa.
        """
        _check_giornata(giornata)
        return self.dir_grezzo / f"{giornata:02d}.html.gz"

    def __str__(self) -> str:
        return f"{self.league} {self.season}"


@dataclass(frozen=True)
class TargetQuote:
    """Il listone di una stagione. Una pagina sola, non 38.

    Separato da `TargetVoti` invece di essere un suo metodo perche' e' un'altra
    risorsa della fonte, con un'altra granularita' e un altro percorso: fonderli
    darebbe una classe con meta' dei metodi validi a seconda di come la si usa.
    """

    league: str = config.LEAGUE
    season: str = config.SEASON

    def __post_init__(self):
        config._check_league(self.league)
        config._check_season(self.season)
        if PERCORSI_QUOTE.get(self.league) is None:
            raise ValueError(
                f"per {self.league} il percorso del listone di {FONTE} non e' "
                "stato verificato: va accertato e dichiarato in PERCORSI_QUOTE"
            )

    @property
    def slug_stagione(self) -> str:
        return stagione_sito(self.season)

    @property
    def url(self) -> str:
        return f"{BASE_URL}/{PERCORSI_QUOTE[self.league]}/{self.slug_stagione}"

    @property
    def percorso(self) -> Path:
        return config.raw_dir(FONTE, self.league, self.season) / "quotazioni.html.gz"

    def __str__(self) -> str:
        return f"{self.league} {self.season} (listone)"


def _check_giornata(giornata: int) -> int:
    if not isinstance(giornata, int) or isinstance(giornata, bool):
        raise TypeError(f"giornata {giornata!r} non e' un intero")
    if not 1 <= giornata <= N_GIORNATE:
        raise ValueError(f"giornata {giornata} fuori da 1..{N_GIORNATE}")
    return giornata


def targets(league: str | None = None, seasons=None) -> list[TargetVoti]:
    """Bersagli, in ordine cronologico.

    `seasons=None` significa **tutto il perimetro storico dichiarato**
    (`config.SEASONS_STORICHE`), non "la stagione corrente": chi lancia lo script
    senza argomenti vuole le cinque stagioni di `docs/regole_fantacalcio.md` §5.
    """
    league = config.LEAGUE if league is None else league
    seasons = config.SEASONS_STORICHE if not seasons else tuple(seasons)
    return [TargetVoti(league, s) for s in sorted(seasons)]


def stato(target: TargetVoti) -> dict:
    """Quante giornate sono gia' su disco. Non tocca la rete.

    E' cio' che rende l'acquisizione ripartibile (vincolo 9) leggibile *prima* di
    lanciarla.
    """
    presenti = sorted(
        g for g in range(1, N_GIORNATE + 1) if target.percorso(g).is_file()
    )
    return {
        "target": str(target),
        "dir_grezzo": target.dir_grezzo,
        "presenti": len(presenti),
        "attese": N_GIORNATE,
        "mancanti": [g for g in range(1, N_GIORNATE + 1) if g not in set(presenti)],
    }


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Scarica i voti fantacalcio per una o piu' stagioni.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""esempi:
  scrape_voti.py --dry-run                    cosa farebbe, senza rete
  scrape_voti.py                              tutte e cinque le stagioni
  scrape_voti.py --season 2021-2022           una sola
  scrape_voti.py --season 2025-2026 --giornata 1 2 3
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
        "--giornata", nargs="+", type=int, metavar="N",
        help=f"giornate da 1 a {N_GIORNATE}. Default: tutte",
    )
    p.add_argument(
        "--dry-run", action="store_true",
        help="stampa bersagli, URL e stato di avanzamento e si ferma. "
             "Non tocca la rete",
    )
    p.add_argument(
        "--sleep", type=float, default=3.0, metavar="SEC",
        help="pausa fra una pagina e l'altra (default: %(default)s). "
             "E' il ritmo dichiarato di cui parla regole_fantacalcio §4.2",
    )
    return p
