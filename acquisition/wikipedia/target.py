# -*- coding: utf-8 -*-
"""Bersagli, titoli di pagina e percorsi per il calendario da Wikipedia.

**Non importa `requests`**, esattamente come `acquisition/fantacalcio/target.py`:
cosi' la risoluzione dei bersagli e' verificabile dai test senza rete.

PERCHE' UNA SECONDA FONTE
-------------------------
Il calendario di WhoScored (`acquisition/whoscored`, Fase 15 / C1) porta gli URL
e i `matchId`, che sono cio' che serve per scaricare gli eventi. **Non porta la
giornata**, e non e' una dimenticanza: quella pagina si naviga per GIORNO, e la
giornata di campionato non compare da nessuna parte — e' lo stesso fatto che il
Blocco 0 aveva gia' misurato su `matches.json` e che ha costretto R3 a prendere
la giornata dall'aggancio della Fase 8.

Wikipedia la porta, perche' il suo calendario e' organizzato **per giornata** e
non per data. Ne segue che le due fonti non sono ridondanti: portano cose
diverse, e messe una contro l'altra sono anche il vincolo 7 applicato a costo
quasi zero.

**Le due fonti hanno due discriminanti DIVERSI**, e questo e' il punto da non
perdere. Su WhoScored una partita da giocare ha `/show/` nell'href e mostra
`-:-`. Su Wikipedia mostra l'**orario** (`20:45`) nella stessa cella in cui una
partita giocata mostra il risultato (`2-1`); li' il separatore distingue i due
casi (`-` per il punteggio, `:` per l'ora), ma e' una proprieta' di QUESTA fonte
e non si eredita dall'altra. Riusare il criterio di WhoScored qui darebbe una
tabella dell'ordine di grandezza giusto e del contenuto sbagliato.
"""

from __future__ import annotations

from pathlib import Path

from sot import config

#: L'endpoint dell'API. Si usa l'API e non lo scraping dell'HTML della pagina
#: perche' e' l'interfaccia che la fonte dichiara stabile: il markup di una
#: pagina wiki cambia con il template, l'API no.
API = "https://it.wikipedia.org/w/api.php"

#: Wikipedia chiede un User-Agent che identifichi chi chiama e perche'.
#: Dichiararsi e' la condizione d'uso della loro API, non una cortesia.
USER_AGENT = ("Scrape-Whoscored-Event-Data/1.0 "
              "(progetto personale di modellazione statistica del calcio)")

#: Il titolo della pagina di stagione, per campionato. **Sono accertati**, non
#: costruiti da una regola: la Liga non segue lo schema degli altri quattro e sta
#: sotto `Primera Division ... (Spagna)`, con la disambiguazione fra parentesi.
#: Cercarla con il nome "regolare" da' MANCA, e una regola che la producesse
#: sarebbe una regola inventata per un caso solo.
TITOLI = {
    "ITA-serie-a": "Serie A {stagione}",
    "ENG-premier-league": "Premier League {stagione}",
    "ESP-la-liga": "Primera División {stagione} (Spagna)",
    "GER-bundesliga": "Fußball-Bundesliga {stagione}",
    "FRA-ligue-1": "Ligue 1 {stagione}",
}

#: I titoli delle sezioni da leggere. **Si cercano per NOME e non per indice**:
#: l'indice di una sezione cambia appena qualcuno ne aggiunge una sopra, e il
#: parser leggerebbe la sezione sbagliata senza accorgersene.
SEZIONE_SQUADRE = "Squadre partecipanti"
SEZIONI_CALENDARIO = ("Girone di andata", "Girone di ritorno")


def titolo(league: str, season: str) -> str:
    """Il titolo della pagina di stagione. Solleva su un campionato non coperto."""
    if league not in TITOLI:
        raise ValueError(
            f"campionato {league!r} senza titolo Wikipedia dichiarato. "
            f"Coperti: {sorted(TITOLI)}. Un titolo INVENTATO porterebbe a una "
            "pagina che non esiste, o peggio a un'altra stagione."
        )
    config._check_season(season)
    return TITOLI[league].format(stagione=season)


def percorso(league: str, season: str) -> Path:
    """Dove si scrive il calendario di questa fonte.

    Sta sotto `raw/wikipedia/`, **accanto e non dentro** `raw/whoscored/`: sono
    due fonti diverse della stessa grandezza, e il vincolo 7 vuole che restino
    in due posti separati finche' non e' misurato che coincidano.
    """
    return config.raw_dir("wikipedia", league, season) / "calendario.json"


def bersagli(leagues=None, season: str | None = None) -> list[dict]:
    """L'elenco dei bersagli, senza toccare la rete. E' cio' che `--dry-run` stampa."""
    season = config.SEASON_CORRENTE if season is None else season
    leagues = sorted(TITOLI) if leagues is None else list(leagues)
    return [{"league": L, "season": season, "titolo": titolo(L, season),
             "percorso": percorso(L, season)} for L in leagues]
