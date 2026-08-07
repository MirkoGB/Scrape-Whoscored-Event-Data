# -*- coding: utf-8 -*-
"""Il listone: quotazioni di inizio e di fine stagione, per cinque stagioni.

E' la **verifica principale del progetto** (`docs/regole_fantacalcio.md` §7,
blocco F5): un modello per l'asta si giudica confrontando il valore che stima
con il prezzo che il mercato chiede. Senza queste righe, le due baseline rimaste
non bastano a dire se il modello ha valore d'uso.

## La grandezza che serve e' QI, e il FVM NON e' un concorrente leale

| colonna | cos'e' | serve? |
| --- | --- | --- |
| **QI** | quotazione **iniziale**, il prezzo di partenza dell'asta | **si', e' la variabile del confronto** |
| QA | quotazione attuale — un unico valore corrente, non una serie | come diagnostica, e come **controllo contaminato** del gate |
| FVM | Fanta Valore di Mercato della fonte | **solo come baseline dichiarato contaminato** |

**Il FVM e' stato squalificato dal ruolo di concorrente, e la ragione e'
misurata**: `orologio()` e `scarti_di_pagina()` mostrano che il FVM della pagina
archiviata sta sull'orologio di **QA**, non su quello di QI — cioe' si muove
*durante* la stagione. Per una stagione passata ne conosce l'esito, e un
confronto fuori campione con lui lo fa giocare a carte scoperte. Fino al
2026-08-05 questo modulo lo chiamava «terza baseline» e «concorrente»: era
sbagliato, e le due righe sono state riscritte invece che lasciate li'.

**Il concorrente leale e' QI.** E' gia' una stima di valore fatta da qualcun
altro ed e' davvero disponibile al momento in cui si fa l'asta: se il modello non
lo batte, il modello non serve. Trattare una quotazione come *verita'* sarebbe
invece circolare nello stesso modo in cui lo era il backtest su quote generate
dal modello, archiviato in `legacy/` — ed e' un'altra cosa dal problema
dell'orologio.

Il gate sta in fondo al modulo, con `COLONNE_PULITE` e `COLONNE_CONTAMINATE`
dichiarate: e' una proprieta' della **fonte**, non di un modello, e percio' vive
qui e non al punto d'uso.

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


# --------------------------------------------------------------------------
# L'OROLOGIO DELLE COLONNE — quale quotazione e' nota PRIMA della stagione
#
# E' il gate che va superato prima di usare una di queste colonne come
# **ingresso** di un modello, e non solo come baseline. La domanda: la pagina
# archiviata di una stagione passata porta i valori di **agosto** o quelli
# dell'ultimo stato al momento del prelievo?
#
# I cinque listoni sono stati scaricati **tutti nell'agosto 2026**, una pagina per
# stagione. Se il valore archiviato si e' mosso durante la stagione, allora per
# una stagione passata contiene il suo esito — e usarlo per prevedere quella
# stagione e' leakage (vincolo 1).
#
# IL DISEGNO: DUE CONTROLLI NOTI E UN SOGGETTO
# ---------------------------------------------
# Sulla stessa pagina ci sono due colonne di cui l'orologio si conosce gia', ed e'
# la fonte a dichiararlo: **QI** e' la quotazione *iniziale*, **QA** quella
# *attuale* — «un unico valore corrente, non una serie». Il FVM sta in mezzo e non
# ha una data dichiarata da nessuna parte. Quindi non si chiede "il FVM e'
# pulito?" in astratto: si chiede **a quale dei due controlli somigli**, che e'
# una domanda con una risposta.
#
# `orologio()` confronta la colonna presa dalla pagina di t con la stessa colonna
# presa dalla pagina di t-1, contro gli esiti di t. `scarti_di_pagina()` guarda
# **dentro la stessa pagina**: quanto lo scostamento di una colonna dal QI predice
# l'esito di quella stagione. Il secondo non e' confuso dalla qualita' intrinseca
# delle colonne, perche' entrambi gli scarti sono presi rispetto allo stesso QI.
#
# COSA E' RISULTATO, E COSA NON E' DIMOSTRATO
# --------------------------------------------
# Il FVM sta sull'orologio di QA, non su quello di QI. **Non e' dimostrato che sia
# un valore di fine stagione**: e' dimostrato che non e' uno snapshot
# pre-stagione. E' anche coerente col fatto che un "Fanta Valore di Mercato" sia
# per costruzione ricalcolato in continuo — non un incidente del prelievo, ma cosa
# la grandezza e'. In entrambi i casi, per una stagione passata quello che abbiamo
# e' l'ultimo stato.
#
# Su QI il verdetto e' **sostenuto, non provato**: l'unica prova sarebbe una
# pagina scaricata prima dell'inizio di una stagione, e non ne esiste una nel
# repository. Le tre firme concordano, e QI e' comunque la sola quotazione
# davvero disponibile al momento in cui si fa l'asta.
# --------------------------------------------------------------------------

#: Le colonne utilizzabili come **ingresso** di un modello che prevede la
#: stagione da cui la pagina proviene. Dichiarate qui e non al punto d'uso,
#: perche' e' una proprieta' della fonte e non di un modello.
COLONNE_PULITE = ("qi_classic", "qi_mantra")

#: Le colonne che si muovono **durante** la stagione. Restano utilizzabili come
#: descrizione e come baseline **dichiarato contaminato**; non come ingresso, e
#: non come concorrente leale in un confronto fuori campione.
COLONNE_CONTAMINATE = ("qa_classic", "fvm_classic", "qa_mantra", "fvm_mantra")


def _esiti_stagione(esiti: pd.DataFrame = None) -> pd.DataFrame:
    from sot import fantapunti as FP
    if esiti is None:
        esiti = FP.per_giocatore_stagione()
    return esiti[["stagione", "giocatore_id", "punti_stagione", "presenze"]]


def orologio(quote: pd.DataFrame = None, esiti: pd.DataFrame = None,
             colonne=("qi_classic", "qa_classic", "fvm_classic")) -> pd.DataFrame:
    """Ogni colonna, dalla pagina di t e dalla pagina di t-1, contro gli esiti di t.

    Il numero da leggere e' `vantaggio_di_essere_di_t`. Una quota di vantaggio c'e'
    **legittimamente** anche per una colonna pulita — la pagina di t conosce il
    mercato estivo, quella di t-1 no — quindi il confronto non e' con lo zero: e'
    con il vantaggio delle **due colonne di controllo**.
    """
    from scipy.stats import spearmanr

    quote = carica() if quote is None else quote
    esiti = _esiti_stagione(esiti)
    stagioni = sorted(quote["stagione"].unique())

    righe = []
    for prec, t in zip(stagioni, stagioni[1:]):
        e = esiti[esiti["stagione"] == t].set_index("giocatore_id")
        for eta, s in (("listone_t", t), ("listone_t-1", prec)):
            pag = quote[quote["stagione"] == s].set_index("giocatore_id")
            for col in colonne:
                d = e.join(pag[[col]], how="inner").dropna(subset=[col])
                righe.append({
                    "transizione": f"{prec}->{t}", "colonna": col, "eta": eta,
                    "n": len(d),
                    "spearman": (spearmanr(d[col], d["punti_stagione"]).statistic
                                 if len(d) >= 50 else float("nan")),
                })
    return pd.DataFrame(righe)


def orologio_sintesi(oro: pd.DataFrame = None) -> pd.DataFrame:
    """Le medie sulle transizioni, con il vantaggio e il confronto coi controlli."""
    oro = orologio() if oro is None else oro
    piv = oro.pivot_table(index="colonna", columns="eta", values="spearman")
    piv["vantaggio_di_essere_di_t"] = piv["listone_t"] - piv["listone_t-1"]
    piv["orologio"] = [
        "pulita (controllo)" if c in COLONNE_PULITE
        else "contaminata (controllo)" if c == "qa_classic"
        else "SOGGETTO" for c in piv.index]
    return piv.reset_index()


def scarti_di_pagina(quote: pd.DataFrame = None,
                     esiti: pd.DataFrame = None) -> pd.DataFrame:
    """Quanto lo scostamento di una colonna dal QI predice l'esito di quella stagione.

    E' il taglio che **non e' confuso dalla qualita' intrinseca delle colonne**:
    entrambi gli scarti sono presi rispetto allo stesso QI, sulla stessa pagina e
    sulla stessa popolazione. Se `FVM - QI` sa quanto `QA - QI`, il FVM e' sullo
    stesso orologio di QA.

    Gli scarti si prendono **sui ranghi**: QI e FVM non hanno la stessa scala
    (uno e' un prezzo intero limitato dal budget, l'altro un valore di mercato) e
    una differenza in unita' grezze sarebbe dominata dal cambio di scala.
    """
    from scipy.stats import spearmanr

    quote = carica() if quote is None else quote
    esiti = _esiti_stagione(esiti)

    righe = []
    for t in sorted(quote["stagione"].unique()):
        d = quote[quote["stagione"] == t].merge(
            esiti[esiti["stagione"] == t], on=["stagione", "giocatore_id"],
            how="left")
        # Un quotato che non compare fra gli esiti non ha giocato: zero osservato,
        # come in `con_esito`. Toglierlo qui guarderebbe il risultato.
        d["punti_stagione"] = d["punti_stagione"].fillna(0.0)
        d = d.dropna(subset=["qi_classic", "fvm_classic"])
        if len(d) < 50:
            continue
        r_qi = d["qi_classic"].rank(pct=True)
        riga = {"stagione": t, "n": len(d)}
        for nome, col in (("qa", "qa_classic"), ("fvm", "fvm_classic")):
            riga[f"scarto_{nome}_meno_qi"] = spearmanr(
                d[col].rank(pct=True) - r_qi, d["punti_stagione"]).statistic
            riga[f"corr_{nome}_con_qi"] = spearmanr(d[col], d["qi_classic"]).statistic
        riga["corr_fvm_con_qa"] = spearmanr(d["fvm_classic"],
                                            d["qa_classic"]).statistic
        righe.append(riga)
    return pd.DataFrame(righe)


def run(league: str = None, seasons=None, verbose: bool = True) -> pd.DataFrame:
    quote = costruisci(league, seasons, verbose=verbose)
    quote.to_parquet(QUOTE_PARQUET, index=False)
    quote.to_csv(QUOTE_CSV, index=False)
    return quote


def carica() -> pd.DataFrame:
    if not QUOTE_PARQUET.is_file():
        raise FileNotFoundError(f"{QUOTE_PARQUET} non c'e': serve prima `run()`")
    return pd.read_parquet(QUOTE_PARQUET)
