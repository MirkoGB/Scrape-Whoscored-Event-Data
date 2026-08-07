# -*- coding: utf-8 -*-
"""Il modello per l'asta: punti totali attesi di stagione, per giocatore.

E' il prodotto scelto in `docs/regole_fantacalcio.md` §3.1, e la grandezza da
ordinare e' quella di §3.3: **il totale stagionale, non la fantamedia**. Un
giocatore con fantamedia alta e otto presenze vale meno di uno con fantamedia
media e trentotto.

## La forma del modello e' quella di §6.1, non una scelta libera

```
punti_stagione = presenze_attese × [ voto_base_atteso + bonus_per_presenza_atteso ]
```

I tre fattori si stimano **separatamente** e non insieme, per due ragioni che
non sono estetiche:

1. **hanno persistenze diverse.** Il voto base e' quasi una costante di ruolo —
   la sua deviazione fra giocatori e' piccola — mentre le presenze variano
   enormemente e i bonus sono rari e rumorosi. Un unico modello sul totale
   userebbe lo stesso grado di regolarizzazione per tutte e tre;
2. **si sbagliano in modo diverso, e per l'asta conta sapere quale.** Sbagliare
   le presenze di un titolare e' un errore da 100 punti; sbagliare il voto base
   di 0,1 e' un errore da 4.

## Come si evita di stimare sul futuro (vincolo 1)

Il bersaglio e' la stagione `t`; **tutto cio' che entra nella previsione viene
da stagioni `< t`**. Vale per le medie di ruolo, per i pesi di shrinkage e per
la storia del singolo. Con cinque stagioni le transizioni valutabili sono
quattro: 2022-23, 2023-24, 2024-25, 2025-26. E' esattamente il numero che il
piano dati della Fase 6F stimava necessario per la domanda D4 — quattro-cinque
transizioni di stagione — e non e' un caso: e' la stessa domanda.

**La quotazione iniziale `QI` non e' leakage.** E' pubblicata *prima*
dell'asta, quindi e' un predittore legittimamente disponibile al momento della
decisione. E' anche la baseline piu' dura da battere, perche' incorpora il
mercato di riparazione, gli infortuni noti e le gerarchie di rosa che i dati
storici non vedono.

## I baseline, che non sono un ornamento (vincolo 6)

| baseline | cosa dice |
| --- | --- |
| media di ruolo | "tutti i difensori valgono uguale" |
| persistenza | "l'anno prossimo come l'anno scorso" |
| **QI** | "il mercato ha gia' deciso" |
| **FVM** | "l'aggregatore ha gia' deciso" |

Le ultime due sono **concorrenti veri**, non riferimenti: se il modello non le
batte, il modello non serve, e la cosa onesta e' comprare al listino. Trattarle
come verita' sarebbe circolare nello stesso modo del backtest archiviato in
`legacy/`.

## Cosa questo modulo NON fa

- **Non calcola il modificatore di difesa.** Non e' decomponibile per giocatore
  (§2.2), quindi non puo' stare in una colonna per riga: vive in
  `sot/modificatore.py`, che lo **simula per giornata e per modulo**. I punti
  prodotti qui sono al netto del modificatore, per tutti i ruoli, e per portieri
  e difensori vanno sommati al contributo marginale prima di essere confrontati
  con un prezzo.
- **Non risolve l'asta.** Produce l'ingresso di un problema combinatorio con
  budget, non la sua soluzione (§2.2, seconda conseguenza).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from sot import config, fantapunti as FP, lega as L, quotazioni as Q

# Le stagioni valutabili: tutte tranne la prima, che non ha passato.
STAGIONI_VALUTABILI = config.SEASONS_STORICHE[1:]

GIORNATE = 38


def _shrink(valore: pd.Series, n: pd.Series, prior: pd.Series, k: float) -> pd.Series:
    """Media pesata fra l'osservato del singolo e il prior di ruolo.

    `w = n / (n + k)`: con poca esposizione conta il prior, con molta conta il
    giocatore. `k` **non e' scelto guardando il bersaglio**: si stima sulle sole
    stagioni passate (vedi `_stima_k`), altrimenti sarebbe un iperparametro
    adattato ai dati su cui poi lo si valuta — il vincolo 1 con un altro nome.
    """
    w = n / (n + k)
    return w * valore + (1 - w) * prior


def _stima_k(storia: pd.DataFrame, colonna: str, esposizione: str) -> float:
    """`k` dal rapporto fra varianza entro giocatore e varianza fra giocatori.

    E' la forma classica dello shrinkage empirico: `k = var_entro / var_fra`.
    Quando la variabilita' fra giocatori e' piccola rispetto al rumore — il caso
    del voto base — `k` esce grande e il modello quasi non distingue i singoli.
    **E' il risultato, non un difetto da correggere.**
    """
    g = storia.groupby("giocatore_id")
    medie = g[colonna].mean()
    pesi = g[esposizione].sum()
    ammessi = pesi >= 5
    if ammessi.sum() < 20:
        return 10.0
    var_fra = float(np.var(medie[ammessi], ddof=1))
    var_entro = float(storia[colonna].var(ddof=1)) - var_fra
    if not np.isfinite(var_fra) or var_fra <= 0 or var_entro <= 0:
        return 10.0
    return float(np.clip(var_entro / var_fra, 0.5, 200.0))


def per_giocatore_stagione_default() -> pd.DataFrame:
    """L'osservato per giocatore-stagione, importato tardi per non ciclare.

    `fantapunti` non importa questo modulo, ma l'import in testa costerebbe il
    calcolo dei voti a chiunque importi `modello_asta` anche solo per le
    costanti. Sta qui in una funzione per la stessa ragione per cui `impiego` e
    `difesa` fanno import locali.
    """
    return FP.per_giocatore_stagione()


def storia_fino_a(per_stagione: pd.DataFrame, stagione: str) -> pd.DataFrame:
    """Le stagioni **precedenti** a quella bersaglio. Nient'altro."""
    return per_stagione[per_stagione["stagione"] < stagione]


def listone_surrogato(stagione_bersaglio: str, stagione_fonte: str,
                      quote: pd.DataFrame = None) -> pd.DataFrame:
    """Il listone di una stagione riusato come universo di quella successiva.

    **E' un surrogato dichiarato, non un listone.** Serve quando quello vero non
    esiste ancora — il 2026-27 esce a fine agosto — e permette di produrre una
    lista d'asta provvisoria invece di nessuna lista. Cosa porta con se', e va
    letto accanto a ogni numero che ne discende:

    - **le rose sono quelle dell'anno prima.** Ogni trasferimento estivo e'
      ignorato, e il giocatore compare con la squadra vecchia;
    - **mancano del tutto i promossi dalla Serie B**, che non sono nel
      repository. Sono tre squadre su venti, cioe' ~15% del listone vero;
    - **ci sono i retrocessi**, che nel listone vero non ci saranno. Sono
      marcati in `squadra_retrocessa` invece che tolti: toglierli sarebbe una
      decisione di prodotto, e la si prende guardando la colonna;
    - **`qi` e `fvm` sono dell'anno prima.** Sono conservati con un nome che lo
      dice (`qi_anno_prima`) perche' come *ordine* restano informativi, come
      *prezzo* no.
    """
    quote = Q.carica() if quote is None else quote
    fuori = quote[quote["stagione"] == stagione_fonte].copy()
    if fuori.empty:
        raise ValueError(f"nessun listone per {stagione_fonte}")
    fuori["stagione_listone"] = stagione_fonte
    fuori["stagione"] = stagione_bersaglio
    fuori = fuori.rename(columns={"qi_classic": "qi_anno_prima",
                                  "qa_classic": "qa_anno_prima",
                                  "fvm_classic": "fvm_anno_prima"})
    # Le colonne che il resto del modulo si aspetta restano, con i valori
    # dell'anno prima: e' esplicito, non nascosto.
    fuori["qi_classic"] = fuori["qi_anno_prima"]
    fuori["fvm_classic"] = fuori["fvm_anno_prima"]
    return fuori


def previsione(stagione: str, per_stagione: pd.DataFrame = None,
               quote: pd.DataFrame = None) -> pd.DataFrame:
    """Punti attesi per ogni giocatore del listone di `stagione`.

    L'universo e' **il listone**, non chi ha poi giocato: e' l'insieme su cui si
    fa l'asta, e include i quotati che non scenderanno mai in campo. Escluderli
    a posteriori sarebbe guardare il risultato.
    """
    per_stagione = FP.per_giocatore_stagione() if per_stagione is None else per_stagione
    quote = Q.carica() if quote is None else quote

    passato = storia_fino_a(per_stagione, stagione)
    if passato.empty:
        raise ValueError(f"{stagione} non ha stagioni precedenti: non e' valutabile")

    # I prior di ruolo, dal solo passato.
    per_ruolo = passato.groupby("ruolo").agg(
        presenze_ruolo=("presenze", "mean"),
        voto_ruolo=("voto_medio", "mean"),
        bonus_ruolo=("bonus_totale", "sum"))
    tot_pres = passato.groupby("ruolo")["presenze"].sum()
    per_ruolo["bonus_per_presenza_ruolo"] = per_ruolo["bonus_ruolo"] / tot_pres
    # La dispersione del voto base **entro** giocatore, che serve al
    # modificatore. E' presa al livello di ruolo e non del singolo di proposito:
    # la varianza fra giocatori delle loro sd e' piccola e stimata su poche
    # decine di righe, quindi una sd individuale sarebbe soprattutto rumore
    # spacciato per informazione. Misurata: 0,561 entro giocatore contro 0,207
    # fra giocatori, cioe' il voto base e' quasi una costante di ruolo.
    per_ruolo["sd_voto_ruolo"] = passato.groupby("ruolo")["sd_voto_stagione"].median()

    # La storia del singolo, sempre dal solo passato. Chi ha giocato piu'
    # stagioni pesa di piu' attraverso l'esposizione, non attraverso una media
    # di medie: 30 presenze in una stagione valgono 30, non "una stagione".
    g = passato.groupby("giocatore_id")
    st = pd.DataFrame({
        "stagioni_viste": g.size(),
        "presenze_tot": g["presenze"].sum(),
        "in_campo_tot": g["in_campo"].sum(),
        "voto_somma": (passato["voto_medio"] * passato["presenze"]).groupby(
            passato["giocatore_id"]).sum(),
        "bonus_tot": g["bonus_totale"].sum(),
    })
    st["presenze_medie"] = st["presenze_tot"] / st["stagioni_viste"]
    st["voto_medio"] = st["voto_somma"] / st["presenze_tot"].replace(0, np.nan)
    st["bonus_per_presenza"] = st["bonus_tot"] / st["presenze_tot"].replace(0, np.nan)

    k_pres = _stima_k(passato.assign(x=passato["presenze"]), "presenze", "presenze")
    k_voto = _stima_k(passato.rename(columns={"voto_medio": "v"}), "v", "presenze")
    k_bonus = _stima_k(passato.assign(b=passato["bonus_totale"] / passato["presenze"]
                                      .replace(0, np.nan)).dropna(subset=["b"]),
                       "b", "presenze")

    base = quote[quote["stagione"] == stagione].copy()
    base = base.rename(columns={"ruolo_classic": "ruolo"})
    base = base.merge(st, left_on="giocatore_id", right_index=True, how="left")
    base = base.merge(per_ruolo, left_on="ruolo", right_index=True, how="left")

    # Chi non ha passato prende il prior di ruolo puro, con esposizione zero.
    # Non e' un dato mancante da riempire: e' un giocatore su cui non sappiamo
    # niente, e il modello deve dirlo dando la media del suo ruolo.
    esp = base["presenze_tot"].fillna(0.0)
    base["senza_storia"] = esp == 0

    base["presenze_attese"] = _shrink(
        base["presenze_medie"].fillna(base["presenze_ruolo"]),
        base["stagioni_viste"].fillna(0.0) * GIORNATE,
        base["presenze_ruolo"], k_pres * GIORNATE)
    base["voto_atteso"] = _shrink(
        base["voto_medio"].fillna(base["voto_ruolo"]), esp,
        base["voto_ruolo"], k_voto)
    base["bonus_per_presenza_atteso"] = _shrink(
        base["bonus_per_presenza"].fillna(base["bonus_per_presenza_ruolo"]), esp,
        base["bonus_per_presenza_ruolo"], k_bonus)

    base["punti_previsti"] = (base["presenze_attese"]
                              * (base["voto_atteso"] + base["bonus_per_presenza_atteso"]))
    base["sd_voto"] = base["sd_voto_ruolo"]

    # --- i baseline, calcolati sullo stesso universo e dallo stesso passato ---
    base["b_media_ruolo"] = (base["presenze_ruolo"]
                             * (base["voto_ruolo"] + base["bonus_per_presenza_ruolo"]))
    ultima = passato[passato["stagione"] == passato["stagione"].max()]
    base["b_persistenza"] = base["giocatore_id"].map(
        ultima.set_index("giocatore_id")["punti_stagione"]).fillna(base["b_media_ruolo"])
    base["b_qi"] = base["qi_classic"].astype("Float64")
    base["b_fvm"] = base["fvm_classic"].astype("Float64")
    base["k_presenze"], base["k_voto"], base["k_bonus"] = k_pres, k_voto, k_bonus
    base["stagione_prevista"] = stagione
    return base


def walkforward(per_stagione: pd.DataFrame = None, quote: pd.DataFrame = None,
                stagioni=None) -> pd.DataFrame:
    """Previsione e osservato per tutte le stagioni valutabili."""
    per_stagione = FP.per_giocatore_stagione() if per_stagione is None else per_stagione
    quote = Q.carica() if quote is None else quote
    pezzi = []
    for stagione in (stagioni or STAGIONI_VALUTABILI):
        p = previsione(stagione, per_stagione, quote)
        osservato = per_stagione[per_stagione["stagione"] == stagione].set_index(
            "giocatore_id")
        # Un quotato che non compare fra i voti non ha giocato: **zero punti**,
        # osservato e non imputato. E' il caso piu' importante da non buttare —
        # e' il rischio che l'asta paga.
        p["punti_osservati"] = p["giocatore_id"].map(
            osservato["punti_stagione"]).fillna(0.0)
        p["presenze_osservate"] = p["giocatore_id"].map(
            osservato["presenze"]).fillna(0.0)
        pezzi.append(p)
    return pd.concat(pezzi, ignore_index=True)


# --------------------------------------------------------------------------
# Metriche
#
# Per l'asta contano DUE cose diverse e vanno riportate entrambe: quanto il
# numero e' giusto (MAE) e quanto l'ordine e' giusto (Spearman, precisione sui
# primi N). Un modello puo' sbagliare il livello di venti punti su tutti e
# ordinare perfettamente: all'asta serve l'ordine.
# --------------------------------------------------------------------------

COLONNE_CONFRONTO = {
    "modello": "punti_previsti",
    "media di ruolo": "b_media_ruolo",
    "persistenza (anno prima)": "b_persistenza",
    "quotazione iniziale QI": "b_qi",
    "FVM della fonte (CONTAMINATO)": "b_fvm",
}


def metriche(wf: pd.DataFrame, per_ruolo: bool = False) -> pd.DataFrame:
    """MAE e correlazioni di ogni candidato contro i punti osservati.

    **QI e FVM sono su un'altra scala** — crediti, non punti — quindi il loro
    MAE non e' confrontabile e resta `NaN`: confrontarlo sarebbe un numero senza
    significato. Le correlazioni invece lo sono, e sono quelle che contano per
    l'asta.
    """
    righe = []
    gruppi = (wf.groupby(["stagione_prevista", "ruolo"]) if per_ruolo
              else wf.groupby("stagione_prevista"))
    for chiave, blocco in list(gruppi) + [(("tutte",) if per_ruolo else "tutte", wf)]:
        y = blocco["punti_osservati"]
        for nome, col in COLONNE_CONFRONTO.items():
            x = pd.to_numeric(blocco[col], errors="coerce")
            ok = x.notna()
            if ok.sum() < 10:
                continue
            stessa_scala = col not in ("b_qi", "b_fvm")
            righe.append({
                "stagione": chiave[0] if isinstance(chiave, tuple) else chiave,
                **({"ruolo": chiave[1]} if isinstance(chiave, tuple)
                   and len(chiave) > 1 else {}),
                "candidato": nome, "righe": int(ok.sum()),
                "mae": round(float((x[ok] - y[ok]).abs().mean()), 2)
                       if stessa_scala else np.nan,
                "bias": round(float((x[ok] - y[ok]).mean()), 2)
                        if stessa_scala else np.nan,
                "pearson": round(float(x[ok].corr(y[ok])), 4),
                "spearman": round(float(x[ok].corr(y[ok], method="spearman")), 4),
            })
    return pd.DataFrame(righe)


def precisione_top(wf: pd.DataFrame, n_per_ruolo: dict = None) -> pd.DataFrame:
    """Quanti dei primi N scelti stanno davvero fra i primi N.

    E' la metrica piu' vicina alla decisione vera: all'asta si comprano
    `rosa[ruolo]` giocatori per ruolo, quindi la domanda non e' "quanto e'
    preciso il numero" ma "quanti dei giocatori che compro erano da comprare".
    Il denominatore viene dalla rosa della lega, non da una soglia inventata.
    """
    n_per_ruolo = n_per_ruolo or L.LEGA.rosa
    rng = np.random.default_rng(config.SEED)
    righe = []
    for (stagione, ruolo), blocco in wf.groupby(["stagione_prevista", "ruolo"]):
        n = n_per_ruolo.get(ruolo)
        if n is None or len(blocco) < 2 * n:
            continue
        veri = set(blocco.nlargest(n, "punti_osservati")["giocatore_id"])
        for nome, col in COLONNE_CONFRONTO.items():
            x = pd.to_numeric(blocco[col], errors="coerce")
            if x.notna().sum() < n:
                continue
            # **I pari merito si sciolgono a caso, non nell'ordine della
            # tabella**, ed e' un difetto che questa funzione aveva davvero: il
            # listone arriva ordinato per `QI` decrescente, quindi il baseline
            # "media di ruolo" — che dentro un ruolo e' una costante — sceglieva
            # in silenzio i giocatori piu' cari. Il baseline che non sa niente
            # otteneva la precisione di QI, e il confronto era falsato in favore
            # dell'ignoranza. Il seme e' quello del progetto.
            scelti = set(blocco.assign(
                _x=x, _r=rng.random(len(blocco))
            ).nlargest(n, ["_x", "_r"])["giocatore_id"])
            righe.append({"stagione": stagione, "ruolo": ruolo, "candidato": nome,
                          "n": n, "azzeccati": len(veri & scelti),
                          "precisione": round(len(veri & scelti) / n, 3)})
    return pd.DataFrame(righe)


def scomposizione_errore(wf: pd.DataFrame,
                         per_stagione: pd.DataFrame = None) -> pd.DataFrame:
    """Quale dei tre fattori sbaglia: presenze, voto o bonus.

    E' la ragione per cui i tre si stimano separatamente. Il confronto e' fra il
    modello completo e tre versioni in cui **un fattore alla volta e' sostituito
    dal valore osservato**: la caduta di MAE dice quanto quel fattore costa.
    Non e' una scomposizione esatta — i fattori si moltiplicano, quindi gli
    effetti non sono additivi — ed e' riportata come diagnostica, non come
    bilancio.

    ATTENZIONE AL CAMPIONE, ED E' LA COLONNA `mae_stesse_righe`
    -----------------------------------------------------------
    **Le varianti non girano tutte sulle stesse righe, e la differenza non e'
    piccola.** Chi non ha mai giocato in `t` non ha un bonus per presenza
    osservato — il denominatore e' zero — quindi le righe di "bonus noti" sono
    2.204 e non 2.678. Sono **474 righe in meno, e sono le peggiori**: il modello
    predice punti a chi ne fara' zero, ed e' li' che l'errore e' massimo.

    Ne segue che il confronto `61,42 -> 52,50` **sovrastima di molto** quanto
    valga conoscere i bonus, perche' mette insieme due cose: quanto si guadagna a
    conoscerli (poco) e quanto si guadagna a togliere dal campione i casi
    peggiori (molto). Sulle **stesse** 2.204 righe il modello completo fa
    **55,01**, quindi il guadagno vero e' 2,51 punti e non 8,92.

    La colonna `mae_stesse_righe` porta il MAE del modello completo sul campione
    di *quella* riga, cosi' che il confronto giusto sia sempre orizzontale e non
    verticale. E' stata aggiunta dal Blocco E4, che sul divario dei bonus
    fondava la propria priorita' — la misura ha corretto la premessa.

    E "BONUS NOTI" NON ERA IL BONUS
    -------------------------------
    La versione precedente costruiva il bonus osservato **per differenza**, come
    `punti/presenze - voto_atteso`. Quella quantita' non e' il bonus: e' tutto il
    **tasso per presenza**, cioe' voto *e* bonus insieme. Si vede da un'identita'
    che la vecchia tabella non poteva mostrare perche' aveva una riga sola:
    sostituire il voto per differenza da' lo stesso identico numero, perche'
    entrambe le sostituzioni si riducono a `presenze_attese x punti/presenze`.

    Le due componenti sono osservate **separatamente** in
    `fantapunti.per_giocatore_stagione` (`voto_medio` e `bonus_totale`), e da li'
    si prendono. La riga con la vecchia definizione resta in tabella, col nome
    che dice cos'era: il 52,50 pubblicato e' riproducibile, e non si cancella un
    numero — si dice che cosa misurava.
    """
    d = wf.copy()
    ps = per_giocatore_stagione_default() if per_stagione is None else per_stagione
    oss = ps.set_index(["stagione", "giocatore_id"])
    chiave = list(zip(d["stagione_prevista"], d["giocatore_id"]))
    bonus_pp = ps["bonus_totale"] / ps["presenze"].replace(0, np.nan)
    bonus_pp.index = oss.index

    voto_oss = pd.Series([oss["voto_medio"].get(k, np.nan) for k in chiave],
                         index=d.index)
    bonus_oss = pd.Series([bonus_pp.get(k, np.nan) for k in chiave], index=d.index)

    # La vecchia definizione, conservata per riproducibilita' del 52,50.
    tasso_osservato = (d["punti_osservati"] / d["presenze_osservate"].replace(0, np.nan)
                       - d["voto_atteso"])
    varianti = {
        "modello completo": d["punti_previsti"],
        "presenze note": d["presenze_osservate"] * (d["voto_atteso"]
                                                    + d["bonus_per_presenza_atteso"]),
        "voto noto": d["presenze_attese"] * (voto_oss
                                             + d["bonus_per_presenza_atteso"]),
        "bonus noti": d["presenze_attese"] * (d["voto_atteso"] + bonus_oss),
        'tasso per presenza noto (era "bonus noti")':
            d["presenze_attese"] * (d["voto_atteso"] + tasso_osservato),
    }
    righe = []
    for nome, x in varianti.items():
        ok = x.notna()
        righe.append({
            "variante": nome, "righe": int(ok.sum()),
            "mae": round(float((x[ok] - d["punti_osservati"][ok]).abs().mean()), 2),
            "mae_stesse_righe": round(float(
                (d["punti_previsti"][ok] - d["punti_osservati"][ok]).abs().mean()), 2),
        })
    out = pd.DataFrame(righe)
    out["guadagno_vero"] = (out["mae_stesse_righe"] - out["mae"]).round(2)
    return out
