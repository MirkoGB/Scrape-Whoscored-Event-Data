# -*- coding: utf-8 -*-
"""Il listone: quotazioni di inizio e di fine stagione, per cinque stagioni.

E' la **verifica principale del progetto** (`docs/regole_fantacalcio.md` §7,
blocco F5): un modello per l'asta si giudica confrontando il valore che stima
con il prezzo che il mercato chiede. Senza queste righe, le due baseline rimaste
non bastano a dire se il modello ha valore d'uso.

## La grandezza che serve e' QI, non QA

| colonna | cos'e' | serve? |
| --- | --- | --- |
| **QI** | quotazione **iniziale**, il prezzo di partenza dell'asta | **si', e' la variabile del confronto** |
| QA | quotazione attuale — un unico valore corrente, non una serie | come diagnostica |
| FVM | Fanta Valore di Mercato della fonte | come **terza baseline**, non come bersaglio |

**FVM e' un concorrente, non un riferimento.** E' gia' una stima di valore fatta
da qualcun altro: se il modello non lo batte, il modello non serve. Trattarlo
come verita' sarebbe circolare nello stesso modo in cui lo era il backtest su
quote generate dal modello, archiviato in `legacy/`.

## L'universo del listone non e' quello dei voti

Sono due popolazioni diverse e la differenza non e' un difetto:

- il **listone** contiene chi era quotabile a inizio stagione, compresi
  giocatori che poi non scenderanno mai in campo;
- i **voti** contengono chi e' sceso in campo, compresi giocatori arrivati a
  mercato aperto che nel listone iniziale non c'erano.

`copertura()` misura le due direzioni invece di assumerle, e nessuna delle due
va trattata come mancanza da riempire: un quotato senza presenze **ha zero
presenze**, non un dato mancante, ed e' un'informazione preziosa per l'asta.

## L'aggancio qui e' gratis, ed e' l'unico posto in cui lo e'

`giocatore_id` e `squadra_id` del listone sono **gli stessi** della vista voti —
stessa fonte, stesso dizionario. Non serve nessuna euristica sui nomi, nessun
calendario, nessuna soglia: e' una `merge` e basta. Vale la pena notarlo perche'
in tutto il resto della Fase 8 l'aggancio e' costato lavoro (`sot/aggancio.py`).
"""

from __future__ import annotations

import pandas as pd

from acquisition.fantacalcio import pagina as P
from acquisition.fantacalcio import target as T
from sot import config, voti as V

QUOTE_PARQUET = config.processed_league_dir() / "fantacalcio_quotazioni.parquet"
QUOTE_CSV = config.processed_league_dir() / "fantacalcio_quotazioni.csv"

ORDINE = [
    "stagione", "giocatore_id", "giocatore", "squadra_id", "squadra_sigla",
    "ruolo_classic", "ruolo_mantra",
    "qi_classic", "qa_classic", "fvm_classic",
    "qi_mantra", "qa_mantra", "fvm_mantra",
    "fuori_dal_campionato", "pagina",
]


def costruisci(league: str = None, seasons=None, verbose: bool = True) -> pd.DataFrame:
    """Legge i listoni gia' su disco. Non tocca la rete."""
    league = config.LEAGUE if league is None else league
    seasons = seasons or config.SEASONS_STORICHE
    righe = []
    for stagione in seasons:
        t = T.TargetQuote(league, stagione)
        if not t.percorso.is_file():
            continue
        relativo = str(t.percorso.relative_to(config.ROOT)).replace("\\", "/")
        for r in P.analizza_quote(P.leggi(t.percorso), stagione):
            righe.append({**r, "pagina": relativo})
        if verbose:
            print(f"  {stagione}: {sum(1 for x in righe if x['stagione'] == stagione)} quotati")

    if not righe:
        raise FileNotFoundError(
            "nessun listone su disco. Serve prima "
            "`python -m acquisition.fantacalcio.scrape_quote`")

    out = pd.DataFrame(righe)[ORDINE]
    for col in ("qi_classic", "qa_classic", "fvm_classic",
                "qi_mantra", "qa_mantra", "fvm_mantra"):
        out[col] = out[col].astype("Int64")
    return out.sort_values(["stagione", "ruolo_classic", "qi_classic"],
                           ascending=[True, True, False]).reset_index(drop=True)


def copertura(quote: pd.DataFrame, voti: pd.DataFrame = None) -> pd.DataFrame:
    """Quanto le due popolazioni si sovrappongono, misurato nei due versi.

    Le colonne da guardare sono le ultime due, e dicono cose diverse:
    `quotati_senza_presenze` e' informazione (chi non ha mai giocato),
    `con_voti_non_quotati` e' il mercato di gennaio piu' i promossi dalla
    Primavera.
    """
    voti = V.carica() if voti is None else voti
    v = voti[~voti["allenatore"]]
    presenti = (v.groupby(["stagione", "giocatore_id"])
                .agg(righe=("giornata", "size"),
                     con_voto=("voto_redazione", lambda s: int(s.notna().sum())))
                .reset_index())

    fuori = []
    for stagione, blocco in quote.groupby("stagione"):
        p = presenti[presenti["stagione"] == stagione]
        id_quote = set(blocco["giocatore_id"])
        id_voti = set(p["giocatore_id"])
        fuori.append({
            "stagione": stagione,
            "quotati": len(id_quote),
            "con_almeno_una_presenza": len(id_quote & id_voti),
            "quotati_senza_presenze": len(id_quote - id_voti),
            "con_voti_non_quotati": len(id_voti - id_quote),
        })
    return pd.DataFrame(fuori)


def con_esito(quote: pd.DataFrame, voti: pd.DataFrame = None) -> pd.DataFrame:
    """Il listone con accanto cio' che quel giocatore ha poi fatto.

    E' la tabella su cui F5 si gioca: prezzo chiesto a sinistra, resa osservata a
    destra. **Non e' ancora un confronto col modello** — e' il confronto fra
    prezzo e realta', cioe' il metro con cui poi si giudichera' il modello.

    `presenze` e' la **presenza fantacalcistica** di §1.2 (righe con un voto
    numerico), non le partite in cui e' stato in campo: sono due grandezze e qui
    conta la prima, perche' e' quella che produce punti.
    """
    voti = V.carica() if voti is None else voti
    v = voti[~voti["allenatore"]]
    esito = (v.groupby(["stagione", "giocatore_id"])
             .agg(in_campo=("giornata", "size"),
                  presenze=("voto_redazione", lambda s: int(s.notna().sum())),
                  voto_medio=("voto_redazione", "mean"),
                  gol=("gol_segnati", "sum"), rigori=("rigori_segnati", "sum"),
                  assist=("assist", "sum"),
                  ammonizioni=("ammonizione", "sum"),
                  espulsioni=("espulsione", "sum"))
             .reset_index())
    out = quote.merge(esito, on=["stagione", "giocatore_id"], how="left")
    for col in ("in_campo", "presenze", "gol", "rigori", "assist",
                "ammonizioni", "espulsioni"):
        # Un quotato che non compare fra i voti **non ha giocato**: lo zero e'
        # osservato, non imputato. E' il solo posto di questo modulo in cui un
        # nullo diventa uno zero, e la ragione e' che le due popolazioni sono
        # note per intero — non c'e' nessuna riga che potrebbe esistere e non
        # e' stata vista.
        out[col] = out[col].fillna(0).astype(int)
    return out


def run(league: str = None, seasons=None, verbose: bool = True) -> pd.DataFrame:
    quote = costruisci(league, seasons, verbose=verbose)
    quote.to_parquet(QUOTE_PARQUET, index=False)
    quote.to_csv(QUOTE_CSV, index=False)
    return quote


def carica() -> pd.DataFrame:
    if not QUOTE_PARQUET.is_file():
        raise FileNotFoundError(f"{QUOTE_PARQUET} non c'e': serve prima `run()`")
    return pd.read_parquet(QUOTE_PARQUET)
