# -*- coding: utf-8 -*-
"""Fase 11 / Blocco S1 — le soglie di tiri in porta del Como 2026-27, partita
per partita, e la quota a cui ciascuna diventa conveniente.

CHE COSA MANCAVA
----------------
`project_2627.monte_carlo` produce **solo il totale stagionale**: il suo `lam`
interno e' costante sulle 38 giornate, non ha avversario e non ha campo. Nessuna
funzione del progetto sapeva dire `lambda(Como, avversario_j, casa)` per il
2026-27. **E' questo il ponte che il blocco costruisce**, ed e' l'unica cosa
nuova che stima qualcosa — tutto il resto sono conteggi e riletture.

LA STRUTTURA VIENE DAL MODELLO, IL LIVELLO DALL'ANCORA
------------------------------------------------------
E' la lezione della Fase 6A e non va aggirata: **il livello pubblicato non
contiene il modello di squadra**. Dentro `monte_carlo` il contesto si semplifica,
e il livello e' `4.90 x rapporto compositivo`. Quindi i due ingredienti vengono
da due posti diversi, ed e' una scelta dichiarata:

* il **modello** da' la struttura *relativa* — chi e' l'avversario, e se si gioca
  in casa. E' cio' che il modello sa fare, ed e' validato per quello;
* l'**ancora** da' il *livello*, cioe' la media delle 38 previsioni.

    lam_i = lam_modello_i / media(lam_modello) * ancora

E' letteralmente la normalizzazione di `project_2627.monte_carlo:246-249`,
applicata per partita invece che in aggregato.

> **Ne segue una conseguenza che va detta prima che qualcuno la scopra leggendo
> le tabelle: lo scenario sulle promosse NON sposta il livello.** La media delle
> 38 righe e' l'ancora per costruzione, qualunque difesa si assegni a Venezia,
> Frosinone e Monza; lo scenario muove solo **come** il livello si distribuisce
> fra le partite. Non e' una svista, e' la decisione della Fase 6E: applicare il
> fattore di calendario all'ancora sarebbe un doppio conteggio, perche' 4.90 esce
> da 21 stagioni che contengono gia' 21 ricambi di neopromosse. Un test blocca
> l'invarianza della media.

L'ORDINE DELLE GIORNATE NON ENTRA IN NESSUNA SOMMA
--------------------------------------------------
Ogni avversario si gioca **esattamente due volte, una in casa e una in
trasferta**. Le 38 righe sono quindi completamente determinate dalla lista delle
venti squadre, che e' verificata; il calendario vero aggiunge la data e il numero
di giornata — narrazione, non aritmetica. `verifica_calendario` pretende quella
struttura e **solleva** se non la trova: e' la guardia che ha rifiutato la
tabella di fixture raccolta in fase di piano, che elencava il Como fra i propri
avversari.

LE DUE COLONNE DI PROBABILITA', E LA TRAPPOLA CHE LE SEPARA
------------------------------------------------------------
* `p_puntuale` — `dispersion.p_over(lam_i, linea, r)`. E' la forma con cui il
  Brier Over 4.5 e' stato validato nelle Fasi 2 e 4;
* `p_integrata` — la stessa cosa, mediata sulla distribuzione del **livello**
  2026-27, che il Monte Carlo della proiezione gia' produce. Ha code piu' grasse:
  alza `P(Over 7.5)` e `P(Under 2.5)` e lascia quasi ferma la mediana.

> **Si integra SOLO l'incertezza di livello, MAI il campionamento.** `SOURCES` di
> `project_2627` contiene `"sampling"`, che e' il rumore per-partita gia' messo
> dentro da `p_over`: tenerlo acceso conterebbe le code **due volte**, e sarebbe
> silenzioso. `SORGENTI_LIVELLO` lo esclude e un test lo pretende.

VINCOLO 3 — PERCHE' QUI NON C'E' NESSUN GUADAGNO DICHIARATO
------------------------------------------------------------
Nel repository **non esistono prezzi di mercato**. L'unico artefatto che ne porta
(`data/external/quote/como_tiri_in_porta_2025-2026.xlsx`) li deriva dalla `P(Over)`
del modello stesso piu' un overround *ipotizzato*, ed e' esattamente cio' che fa
il codice archiviato in `legacy/`, che `legacy/README.md` descrive come
«circolare e privo di significato».

Questo modulo quindi **non afferma nessun guadagno**. Pubblica:

* `quota_pareggio(p) = 1/p` — la quota a cui il guadagno atteso e' **zero**. Non
  e' un prezzo e non finge di esserlo: e' la soglia contro cui confrontare un
  prezzo vero, quando ci sara';
* `guadagno_atteso(p, q) = p*q - 1` — una **funzione della quota che si
  fornisce**, non un numero che il modello produce.

E `identita_circolare()` esiste apposta per **squalificare** il caso in cui la
quota venga dal modello stesso: con margine proporzionale il guadagno atteso vale
`1/overround - 1` **su ogni partita e su ogni linea, identicamente**, e non
contiene una sola informazione sul Como. Sta in tabella per la stessa ragione per
cui R3 pubblica `media dichiarata` e la coda di E3 pubblica `corr_totali`: perche'
il numero comodo sia visibile *e* visibilmente vuoto.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.optimize import brentq

from . import (calendar_2627 as CAL, config, dispersion as D, model_team as MT,
               project_2627 as P, squad_2627 as SQ, validate as V)

#: Le tre promosse 2026-27. **Informazione esterna**, dichiarata qui come lo sono
#: `squad_2627.CONFIRMED` e `calendar_2627.PROMOSSE_2526`: la Serie B non e' in
#: questo repository e la promozione non e' deducibile dai dati che ci sono.
PROMOSSE_2627 = ("Venezia", "Frosinone", "Monza")

#: Le tre retrocesse dichiarate dalla stessa fonte. **Non si usano per calcolare
#: niente**: esistono solo per essere messe contro `calendar_2627.retrocesse()`,
#: che le ricava dai gol. E' una verifica falsificabile a costo zero, ed e' il
#: solo controllo che questo blocco puo' fare sulla fonte esterna.
RETROCESSE_2526_DICHIARATE = ("Cremonese", "Verona", "Pisa")

#: Provenienza dell'informazione esterna (vincolo 8). Nessuna riga di questo
#: modulo viene dalla rete: la consultazione e' avvenuta una volta, in fase di
#: piano, e cio' che ne e' stato tenuto e' scritto qui.
PROVENIENZA = {
    "squadre_2026_2027": {
        "fonte": "https://it.wikipedia.org/wiki/Serie_A_2026-2027",
        "corroborata_da": "rassegna Eurosport/Sky sulle promozioni dalla Serie B",
        "consultata": "2026-08-11",
        "preso": "le tre promosse e le tre retrocesse; nient'altro",
        "verificabile_in_casa": "le retrocesse, contro calendar_2627.retrocesse()",
    },
    "calendario_giornate": {
        "fonte": "https://www.espn.com/soccer/team/fixtures/_/id/2572/league/ITA.1",
        "consultata": "2026-08-11",
        "preso": "l'ordine delle 38 partite del Como, con il verso casa/trasferta",
        "rifiutate": "tre altre fonti, tutte RIFIUTATE da verifica_calendario: "
                     "elencavano il Como fra i propri avversari, oppure la stessa "
                     "squadra tre volte, oppure due volte in casa",
        "ricostruito": "la fonte dava 37 righe su 38. La mancante NON e' stata "
                       "indovinata: la struttura la determina — Napoli compariva "
                       "solo in trasferta, quindi l'unica partita compatibile e' "
                       "Como-Napoli in casa. La sua GIORNATA (21a) e' l'unica cosa "
                       "presa da fuori, e concorda su due fonti indipendenti",
        "conseguenza": "`giornata` c'e'; `data` resta nulla, perche' le fonti "
                       "discordano sulle date e questo blocco non ne ha bisogno",
    },
}

#: Il calendario 2026-27 del Como: `(giornata, avversario nella fonte, in casa)`.
#: **Informazione esterna**, come la rosa e le promosse. Non entra in nessuna
#: somma di questo blocco — l'ordine delle giornate non cambia una probabilita' —
#: ma rende leggibile la tabella per partita, che era la ragione per cui serviva.
#: `verifica_calendario` lo passa al setaccio a ogni costruzione.
CALENDARIO_2627 = (
    (1, "Udinese", 0), (2, "Napoli", 0), (3, "Genoa", 0), (4, "Parma", 1),
    (5, "Frosinone", 0), (6, "AS Roma", 1), (7, "Fiorentina", 0),
    (8, "Sassuolo", 1), (9, "Torino", 0), (10, "Venezia", 1),
    (11, "Internazionale", 0), (12, "Cagliari", 1), (13, "Juventus", 1),
    (14, "Monza", 0), (15, "Bologna", 1), (16, "AC Milan", 0), (17, "Lecce", 1),
    (18, "Atalanta", 0), (19, "Lazio", 1), (20, "Cagliari", 0),
    (21, "Napoli", 1), (22, "Sassuolo", 0), (23, "Monza", 1), (24, "Bologna", 0),
    (25, "Torino", 1), (26, "AC Milan", 1), (27, "Lecce", 0), (28, "Udinese", 1),
    (29, "Juventus", 0), (30, "Fiorentina", 1), (31, "Parma", 0),
    (32, "Frosinone", 1), (33, "Lazio", 0), (34, "Internazionale", 1),
    (35, "Venezia", 0), (36, "Atalanta", 1), (37, "AS Roma", 0), (38, "Genoa", 1),
)

#: I nomi della fonte non sono i nomi dei dati, ed e' la trappola gia' misurata
#: dall'aggancio di Fase 8: al livello di squadra **il nome non e' una chiave**.
#: Qui la mappa e' esplicita e `calendario()` verifica che ogni nome tradotto
#: esista davvero fra gli avversari, invece di lasciar passare un `NaN`.
NOMI_FONTE = {
    "Internazionale": "Inter",
    "AS Roma": "Roma",
    "Parma": "Parma Calcio 1913",
}

#: Le sei linee richieste. **Dichiarate, non scelte guardando i dati.** Non
#: coincidono con `validate.LINES`, che si ferma a 5.5: la 6.5 e la 7.5 sono
#: fuori dal perimetro su cui il Brier e' stato validato, e il report lo dice
#: accanto ai numeri invece che in fondo.
LINEE = (2.5, 3.5, 4.5, 5.5, 6.5, 7.5)

#: Dispersione NB2, dalla Fase 2. **Fissata e dichiarata**, non ristimata qui:
#: l'IC95% di profilo la accompagna ovunque, perche' una `P(Over 7.5)` sulla coda
#: e' molto piu' sensibile a `r` di quanto lo sia una `P(Over 4.5)`.
R_NB2 = 26.0
R_NB2_IC95 = (13.7, 111.8)

#: `alpha` del modello di squadra. E' quello che `level_chain.ratings_per_campo`
#: e `calendar_2627.livelli_difensivi` gia' usano per i rating pubblicati:
#: sceglierne un altro qui vorrebbe dire che due tabelle del progetto parlano di
#: due modelli diversi chiamandoli allo stesso modo.
ALPHA_LIVELLI = 12.0

#: Lo scenario primario sulla difesa delle promosse. E' lo **status quo** della
#: Fase 6E — «le promosse difendono come le retrocesse» — e non l'avversario
#: medio. Gli altri tre di `calendar_2627.SCENARI` restano disponibili e il
#: report li affianca.
SCENARIO_PRIMARIO = "come le retrocesse"

#: Le sorgenti di incertezza che entrano nella colonna integrata. **`sampling` e'
#: escluso di proposito**: e' il rumore per-partita che `p_over` mette gia'
#: dentro. Vedi la docstring del modulo.
SORGENTI_LIVELLO = tuple(s for s in P.SOURCES if s != "sampling")

#: Nodi di quadratura sulla distribuzione del livello. Si usano i quantili invece
#: di un sottocampione casuale: a parita' di costo l'errore di integrazione e'
#: deterministico, quindi due esecuzioni danno lo stesso numero.
N_QUADRATURA = 400

#: Griglia di quote **ipotetiche** su cui il report tabula il guadagno atteso.
#: Sono valori di comodo per la lettura, non prezzi osservati e non previsioni
#: di prezzo: nessuno di questi numeri viene da un mercato.
GRIGLIA_QUOTE = (1.20, 1.50, 1.80, 2.00, 2.50, 3.00, 4.00, 6.00, 10.00)

#: Overround ipotizzati per l'appendice circolare. Anche questi sono dichiarati e
#: non misurati: servono solo a mostrare che il risultato dipende da loro e non
#: dal modello.
OVERROUND_IPOTIZZATI = (1.05, 1.07, 1.10)


# ---------------------------------------------------------------------------
# Le squadre, e la verifica che le convalida
# ---------------------------------------------------------------------------

def verifica_squadre(team_match: pd.DataFrame) -> pd.DataFrame:
    """Le retrocesse dichiarate dalla fonte coincidono con quelle **dei dati**?

    E' l'unico controllo falsificabile che questo blocco puo' fare su
    un'informazione che arriva da fuori, e costa zero: `calendar_2627.retrocesse`
    ricostruisce la classifica dai gol delle righe partita, senza sapere niente
    della fonte esterna. Se le due strade divergessero, a essere sbagliata
    sarebbe la fonte — e allora anche le promosse andrebbero rimesse in
    discussione, perche' vengono dalla stessa pagina.

    Solleva invece di ritornare un flag: una lista di avversari sbagliata
    produrrebbe 38 lambda plausibili e nessun controllo a valle se ne
    accorgerebbe.
    """
    dai_dati = tuple(sorted(CAL.retrocesse(team_match)))
    dichiarate = tuple(sorted(RETROCESSE_2526_DICHIARATE))
    if dai_dati != dichiarate:
        raise ValueError(
            f"le retrocesse dei dati {dai_dati} non coincidono con quelle "
            f"dichiarate dalla fonte {dichiarate}: la fonte esterna e' sbagliata, "
            "e con essa le promosse, che vengono dalla stessa pagina")
    return pd.DataFrame([
        {"voce": "retrocesse dai dati (classifica ricostruita)",
         "valore": ", ".join(dai_dati)},
        {"voce": "retrocesse dichiarate dalla fonte",
         "valore": ", ".join(dichiarate)},
        {"voce": "promosse dichiarate dalla fonte (NON verificabile in casa)",
         "valore": ", ".join(PROMOSSE_2627)},
    ])


def avversari(team_match: pd.DataFrame, squadra: str = "Como") -> list[str]:
    """I 19 avversari del Como nel 2026-27.

    Le sedici che restano si **contano dai dati**; le tre che entrano sono
    l'unica informazione esterna. L'ordine e' alfabetico e non ha significato:
    l'ordine vero e' il calendario, che qui non c'e'.
    """
    verifica_squadre(team_match)
    presenti = set(team_match["team"].unique())
    if squadra not in presenti:
        raise ValueError(f"{squadra!r} non e' fra le squadre 2025-26")
    restano = presenti - {squadra} - set(RETROCESSE_2526_DICHIARATE)
    return sorted(restano | set(PROMOSSE_2627))


def calendario(team_match: pd.DataFrame, squadra: str = "Como",
               con_giornate: bool = True) -> pd.DataFrame:
    """Le 38 righe: ogni avversario una volta in casa e una in trasferta.

    Con `con_giornate` si usa `CALENDARIO_2627`, che e' informazione esterna;
    senza, le stesse 38 righe in ordine alfabetico e `giornata` nulla. **Le due
    forme danno gli stessi lambda e le stesse probabilita'**, perche' l'ordine
    delle giornate non entra in nessuna somma: un test lo verifica, ed e' cio'
    che rende il calendario un comodo e non una dipendenza.

    `data` resta nulla in entrambi i casi: le fonti discordano sulle date e
    questo blocco non ne ha bisogno. Meglio vuota che riempita a caso.
    """
    avv = avversari(team_match, squadra=squadra)
    if con_giornate:
        righe = []
        for g, nome, h in CALENDARIO_2627:
            a = NOMI_FONTE.get(nome, nome)
            if a not in avv:
                raise ValueError(
                    f"il calendario nomina {nome!r} -> {a!r}, che non e' fra i 19 "
                    f"avversari: la mappa `NOMI_FONTE` e' incompleta. Senza questa "
                    f"guardia la riga diventerebbe un NaN e il lambda sparirebbe")
            righe.append({"giornata": g, "avversario": a, "is_home": h})
    else:
        righe = [{"giornata": pd.NA, "avversario": a, "is_home": h}
                 for a in avv for h in (1, 0)]

    cal = pd.DataFrame(righe)
    cal["campo"] = np.where(cal["is_home"] == 1, "casa", "trasferta")
    cal["promossa"] = cal["avversario"].isin(PROMOSSE_2627)
    cal["data"] = pd.NaT
    return verifica_calendario(cal.reset_index(drop=True), squadra=squadra)


def verifica_calendario(cal: pd.DataFrame, squadra: str = "Como") -> pd.DataFrame:
    """Struttura del calendario, **pretesa e non sperata**.

    38 righe, 19 avversari distinti, ognuno esattamente due volte e esattamente
    una volta in casa, 19 in casa e 19 in trasferta, e la squadra assente dai
    propri avversari.

    **E' la guardia che ha rifiutato la tabella raccolta in fase di piano**, che
    elencava il Como fra i propri avversari e una squadra in casa due volte. Una
    fonte di fixture puo' essere sbagliata in modi che sembrano innocui: senza
    questa funzione, quelle 38 righe avrebbero prodotto 38 lambda plausibili.
    """
    if len(cal) != 38:
        raise ValueError(f"il calendario ha {len(cal)} righe invece di 38")
    if squadra in set(cal["avversario"]):
        raise ValueError(f"{squadra!r} compare fra i propri avversari")
    n = cal["avversario"].value_counts()
    if len(n) != 19:
        raise ValueError(f"{len(n)} avversari distinti invece di 19")
    if not (n == 2).all():
        raise ValueError(f"avversari non affrontati due volte: "
                         f"{n[n != 2].to_dict()}")
    casa = cal.groupby("avversario")["is_home"].sum()
    if not (casa == 1).all():
        raise ValueError(f"avversari non affrontati una volta per campo: "
                         f"{casa[casa != 1].to_dict()}")
    if int(cal["is_home"].sum()) != 19:
        raise ValueError(f"{int(cal['is_home'].sum())} partite in casa invece di 19")
    return cal


# ---------------------------------------------------------------------------
# Il ponte: lambda per partita
# ---------------------------------------------------------------------------

def ancora_pubblicata(summary: dict) -> float:
    """Il livello 2026-27 che la proiezione pubblica, per partita.

    `4.90 x rapporto compositivo`, cioe' esattamente cio' che
    `project_2627.monte_carlo` calcola prima di simulare. Si passa dalla stessa
    funzione (`stima_compositiva`) invece di riscrivere il prodotto: se un giorno
    l'estimatore cambiasse, questo blocco cambierebbe con lui.
    """
    return P.stima_compositiva(config.REF_TOPDOWN_PER_MATCH,
                               summary["lambda_bottomup_2627"],
                               summary["lambda_bottomup_2526"])


def difese_avversari(team_match: pd.DataFrame, scenario: str = SCENARIO_PRIMARIO,
                     alpha: float = ALPHA_LIVELLI,
                     squadra: str = "Como") -> pd.Series:
    """`exp(difesa_j)` per ognuno dei 19 avversari, promosse comprese.

    Per le sedici che restano e' il coefficiente stimato. Per le tre promosse e'
    uno **scenario dichiarato** di `calendar_2627.SCENARI`, non una stima: quelle
    squadre non hanno giocato in Serie A 2025-26 e di loro questi dati non sanno
    niente.

    > **Perche' non le si prende dalle stagioni storiche.** Monza, Venezia e
    > Frosinone hanno righe nelle cinque stagioni gia' in casa. Usarle vorrebbe
    > dire due cose che il progetto ha gia' escluso: confrontare unita' grezze
    > fra stagioni in cui la media di campionato si e' mossa del 10,1% (regola di
    > E1), e trattare una rosa di due o quattro anni fa come una stima di quella
    > di oggi. Lo scenario e' meno preciso e non e' sbagliato.
    """
    liv = CAL.livelli_difensivi(team_match, alpha=alpha)
    c = liv["modello"]
    valori = CAL.livelli_scenario(c, CAL.retrocesse(team_match))
    if scenario not in valori:
        raise ValueError(f"scenario {scenario!r} sconosciuto: {sorted(valori)}")
    c_prom = valori[scenario]
    avv = avversari(team_match, squadra=squadra)
    out = {}
    for a in avv:
        if a in c.index:
            out[a] = float(c[a])
        elif a in PROMOSSE_2627:
            out[a] = float(c_prom)
        else:
            # Non e' pedanteria: `model_team._design` lascia a zero la dummy di
            # una squadra sconosciuta, cioe' la tratta in silenzio come
            # esattamente media. Nessun errore, nessun avviso, lambda sbagliati.
            raise ValueError(
                f"{a!r} non ha un coefficiente di difesa e non e' fra le "
                f"promosse dichiarate: senza questa guardia `TeamModel.predict` "
                f"le assegnerebbe in silenzio coefficiente 0")
    return pd.Series(out, name="exp_difesa").sort_index()


def lambda_per_partita(team_match: pd.DataFrame, ancora: float,
                       scenario: str = SCENARIO_PRIMARIO,
                       alpha: float = ALPHA_LIVELLI,
                       squadra: str = "Como") -> pd.DataFrame:
    """`lambda(Como, avversario_j, campo)` per le 38 partite 2026-27.

    **E' il ponte che mancava.** La struttura relativa viene dal modello di
    squadra, il livello dall'ancora, e la seconda riga di codice sotto e' la
    normalizzazione: vedi la docstring del modulo per il perche' i due pezzi
    vengano da due posti diversi.

    La media delle 38 righe vale `ancora` **a precisione macchina**, e un test lo
    blocca: e' cio' che rende questa tabella coerente con la proiezione gia'
    pubblicata invece di essere una seconda proiezione che le somiglia.
    """
    m = MT.TeamModel(alpha=alpha).fit(team_match)
    rat = m.ratings().set_index("team")
    if squadra not in rat.index:
        raise ValueError(f"{squadra!r} non e' nel modello")
    att = float(rat.loc[squadra, "attack"])
    gamma = float(m.home_advantage)

    cal = calendario(team_match, squadra=squadra)
    dif = difese_avversari(team_match, scenario=scenario, alpha=alpha,
                           squadra=squadra)
    cal["exp_difesa"] = cal["avversario"].map(dif).astype(float)
    cal["lam_modello"] = (np.exp(m.mu_ + att + gamma * cal["is_home"].to_numpy())
                          * cal["exp_difesa"].to_numpy())
    cal["lam"] = cal["lam_modello"] / cal["lam_modello"].mean() * float(ancora)
    cal["scenario"] = scenario
    return cal


# ---------------------------------------------------------------------------
# Le probabilita' di superare ciascuna soglia
# ---------------------------------------------------------------------------

def moltiplicatori_livello(proj: pd.DataFrame, summary: dict, model, r: float,
                           ancora: float, n_sim: int = 20000,
                           n_quad: int = N_QUADRATURA,
                           seed: int = config.SEED) -> np.ndarray:
    """Quadratura sulla distribuzione del **livello** 2026-27, in unita' di ancora.

    Si riusa il Monte Carlo della proiezione — non se ne scrive un altro — e se
    ne tolgono i quantili: il risultato e' deterministico a parita' di seme,
    quindi due esecuzioni del report danno lo stesso numero.

    **`sampling` e' escluso**, e la funzione lo pretende invece di fidarsi della
    costante: e' il rumore per-partita che `p_over` mette gia' dentro, e tenerlo
    conterebbe le code due volte.
    """
    if "sampling" in SORGENTI_LIVELLO:
        raise ValueError("`sampling` non deve entrare nell'incertezza di livello: "
                         "e' gia' dentro `p_over`, si conterebbe due volte")
    sim = P.monte_carlo(proj, summary, model, r, n_sim=n_sim,
                        sources=SORGENTI_LIVELLO, seed=seed)
    lam_sim = np.asarray(sim, dtype=float) / SQ.N_MATCHES
    q = (np.arange(n_quad) + 0.5) / n_quad
    return np.quantile(lam_sim, q) / float(ancora)


def p_soglie(lam: pd.DataFrame, moltiplicatori: np.ndarray | None = None,
             r: float = R_NB2, linee=LINEE) -> pd.DataFrame:
    """`P(SoT > linea)` per ogni partita e ogni linea, nelle due forme.

    `p_puntuale` tratta il livello 2026-27 come noto; `p_integrata` lo tratta
    come incerto e media su `moltiplicatori`. Con `moltiplicatori=None` la
    seconda colonna esce nulla invece di essere silenziosamente uguale alla
    prima.

    Il segno atteso e' dichiarato **prima di guardare i numeri**: l'integrazione
    ingrassa le code, quindi alza `P(Over)` sulle linee alte e la abbassa su
    quelle basse, incrociando dalle parti della mediana. Un test lo pretende,
    cosi' che non lo si possa aggiustare dopo.
    """
    l = lam["lam"].to_numpy(dtype=float)
    fuori = [c for c in ("avversario", "campo", "is_home", "promossa",
                         "giornata", "lam") if c in lam.columns]
    blocchi = []
    for ln in linee:
        b = lam[fuori].copy()
        b.insert(0, "linea", ln)
        b["p_puntuale"] = D.p_over(l, ln, r)
        if moltiplicatori is None:
            b["p_integrata"] = np.nan
        else:
            M = np.outer(np.asarray(moltiplicatori, dtype=float), l)
            b["p_integrata"] = D.p_over(M, ln, r).mean(axis=0)
        blocchi.append(b)
    out = pd.concat(blocchi, ignore_index=True)
    out["quota_pareggio"] = quota_pareggio(out["p_puntuale"].to_numpy())
    out["quota_pareggio_integrata"] = quota_pareggio(out["p_integrata"].to_numpy())
    return out


def sintesi_per_linea(ps: pd.DataFrame) -> pd.DataFrame:
    """Le sei linee in sei righe: probabilita' media, estremi, quota di pareggio.

    La quota di pareggio della riga e' `1 / p_media`, cioe' la quota **costante**
    che azzererebbe il guadagno atteso sulle 38 partite prese insieme. Non e' la
    media delle 38 quote di pareggio, che sarebbe un'altra cosa e piu' grande
    (Jensen): un test verifica che le due differiscano davvero, perche' e' il
    genere di scambio che passa inosservato.
    """
    g = ps.groupby("linea", as_index=False).agg(
        p_media=("p_puntuale", "mean"),
        p_min=("p_puntuale", "min"),
        p_max=("p_puntuale", "max"),
        p_media_integrata=("p_integrata", "mean"),
    )
    g["quota_pareggio_stagione"] = quota_pareggio(g["p_media"].to_numpy())
    g["quota_pareggio_stagione_integrata"] = quota_pareggio(
        g["p_media_integrata"].to_numpy())
    g["attese_su_38"] = g["p_media"] * 38.0
    return g


# ---------------------------------------------------------------------------
# Quota di pareggio e guadagno atteso — vincolo 3
# ---------------------------------------------------------------------------

def quota_pareggio(p) -> np.ndarray:
    """La quota a cui il guadagno atteso e' **zero**: `1/p`.

    Non e' un prezzo e non e' una previsione di prezzo. E' la soglia contro cui
    confrontare un prezzo vero: sopra conviene, sotto no, e di quanto lo dice
    `guadagno_atteso`. E' l'unica forma in cui questo progetto puo' rispondere
    alla domanda «quanto si guadagna», finche' prezzi veri non ce ne sono.
    """
    p = np.asarray(p, dtype=float)
    with np.errstate(divide="ignore", invalid="ignore"):
        return np.where(p > 0, 1.0 / p, np.inf)


def guadagno_atteso(p, q) -> np.ndarray:
    """Guadagno atteso di 1 EUR: `p*q - 1`.

    **E' una funzione della quota `q` che si fornisce**, non un numero che il
    modello produce. Con `q = quota_pareggio(p)` vale zero a precisione macchina,
    ed e' l'identita' che definisce la quota di pareggio.
    """
    return np.asarray(p, dtype=float) * np.asarray(q, dtype=float) - 1.0


def tabella_guadagno(ps: pd.DataFrame, griglia=GRIGLIA_QUOTE,
                     colonna: str = "p_puntuale") -> pd.DataFrame:
    """Guadagno atteso di 1 EUR **su ognuna** delle 38 partite, per linea e quota.

    Ogni cella e' la somma su 38 partite di `p_i*q - 1`, cioe' cio' che si
    attende chi mette 1 EUR su ogni partita della stagione a quella quota fissa.
    **La quota e' un'ipotesi di lettura, non un prezzo osservato**: la griglia e'
    dichiarata in `GRIGLIA_QUOTE` e nessuno di quei numeri viene da un mercato.
    """
    if colonna not in ps.columns:
        raise ValueError(f"colonna {colonna!r} assente")
    rows = []
    for ln, g in ps.groupby("linea"):
        p = g[colonna].to_numpy(dtype=float)
        riga = {"linea": ln, "p_media": float(np.nanmean(p)),
                "quota_pareggio_stagione": float(1.0 / np.nanmean(p))}
        for q in griglia:
            riga[f"q={q:.2f}"] = float(np.nansum(guadagno_atteso(p, q)))
        rows.append(riga)
    return pd.DataFrame(rows)


def _k_buchdahl(p_over_: float, overround: float) -> float:
    """Esponente `k` tale che `p^(1/k) + (1-p)^(1/k) = overround`."""
    def f(k):
        return p_over_ ** (1.0 / k) + (1.0 - p_over_) ** (1.0 / k) - overround
    return brentq(f, 1.0 + 1e-12, 50.0)


def identita_circolare(ps: pd.DataFrame, overround=OVERROUND_IPOTIZZATI,
                       colonna: str = "p_puntuale") -> pd.DataFrame:
    """Che cosa succede se la quota la genera **il modello stesso**.

    E' la risposta letterale alla domanda «calcolami il guadagno atteso» quando
    non ci sono prezzi veri, e sta qui per essere **squalificata**, non letta.

    Due modi di applicare un margine, entrambi ipotizzati:

    * **proporzionale** — `q = 1/(p * overround)`. Allora
      `guadagno = p*q - 1 = 1/overround - 1`, cioe' **lo stesso numero su ogni
      partita e su ogni linea**, identicamente. Non contiene una sola
      informazione sul Como: e' il margine, scritto al contrario;
    * **potenza (Buchdahl)** — `q = 1/p^(1/k)`, con `k` che realizza
      l'overround. Qui il guadagno varia un poco con `p`, il che lo fa
      *sembrare* una misura; ma resta negativo ovunque per costruzione, e a
      deciderne la taglia e' `overround`, che e' un'ipotesi.

    E' esattamente cio' che fa il codice archiviato in `legacy/`, e
    `legacy/README.md` lo descrive come «circolare e privo di significato:
    qualunque regola sistematica risulta redditizia per costruzione».
    """
    rows = []
    for ov in overround:
        for ln, g in ps.groupby("linea"):
            p = g[colonna].to_numpy(dtype=float)
            g_prop = guadagno_atteso(p, 1.0 / (p * ov))
            k = np.array([_k_buchdahl(x, ov) for x in p])
            g_buch = guadagno_atteso(p, 1.0 / p ** (1.0 / k))
            rows.append({
                "overround": ov, "linea": ln,
                "guadagno_proporzionale_per_partita": float(g_prop.mean()),
                "dispersione_proporzionale": float(g_prop.std()),
                "guadagno_potenza_per_partita": float(g_buch.mean()),
                "dispersione_potenza": float(g_buch.std()),
                "guadagno_proporzionale_su_38": float(g_prop.sum()),
            })
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# La validazione del macchinario, sulla stagione in cui l'esito si conosce
# ---------------------------------------------------------------------------

def validazione_2526(bundle: dict, squadra: str = "Como",
                     linee=LINEE) -> pd.DataFrame:
    """`P(SoT > linea)` regge, sulle partite del Como 2025-26?

    Senza questa sezione le sei tabelle sarebbero numeri senza garanzia. Si usano
    i lambda **walk-forward** gia' prodotti dalla Fase 2 — non un fit sull'intera
    stagione, che sarebbe in campione e violerebbe il vincolo 1 — e la `r`
    ricostruita riga per riga sul solo passato, che e' la stessa correzione che
    la Fase 4 ha applicato al Brier pubblicato.

    Il baseline e' il **tasso base walk-forward** di ciascuna linea: dire «l'Over
    accade con la frequenza con cui e' accaduto finora» e' l'avversario che il
    vincolo 6 pretende, e su una linea estrema e' un avversario forte.

    > **Il limite sta qui, non in fondo: sono ~33 partite di una squadra sola.**
    > La colonna `mde_brier` dice quanta differenza servirebbe per distinguere il
    > modello dal tasso base; su questa numerosita' esclude divari grandi e non
    > divari piccoli. E le linee 6.5 e 7.5 cadono su eventi rari, dove poche
    > partite spostano tutto.
    """
    ef = bundle["ef"]
    y_all = ef["sot"].to_numpy(dtype=float)
    mask = (ef["team"] == squadra).to_numpy()
    if mask.sum() == 0:
        raise ValueError(f"nessuna riga di {squadra!r} nel walk-forward")

    lam = ef["lam"].to_numpy(dtype=float)[mask]
    y = y_all[mask]
    r = np.asarray(bundle["r_wf"][V.MODEL_NAME], dtype=float)[mask]

    rows = []
    for ln in linee:
        base = V.walkforward_base_rate(y_all, ef["date"], line=ln)[mask]
        y_bin = (y > ln).astype(float)
        p = D.p_over(lam, ln, r)
        b_mod = V.brier(y_bin, p)
        b_base = V.brier(y_bin, base)
        d = (y_bin - p) ** 2 - (y_bin - base) ** 2
        sd = float(np.std(d, ddof=1))
        n = len(d)
        rows.append({
            "linea": ln, "n": n,
            "eventi_osservati": int(y_bin.sum()),
            "p_media": float(p.mean()),
            "frequenza_osservata": float(y_bin.mean()),
            "brier_modello": b_mod,
            "brier_tasso_base": b_base,
            "differenza": b_mod - b_base,
            "mde_brier": float(2.802 * sd / np.sqrt(n)) if sd > 0 else np.nan,
        })
    return pd.DataFrame(rows)


def calibrazione_2526(bundle: dict, squadra: str = "Como") -> dict:
    """Pendenza di calibrazione dei lambda sulle sole partite della squadra.

    E' la diagnostica che la Fase 4 usa come argomento principale, ristretta alle
    38 righe che interessano qui. Con una squadra sola l'errore standard e'
    grande: si riporta con il proprio `z`, e un `z` piccolo va letto come
    «compatibile», non come «confermato».
    """
    ef = bundle["ef"]
    mask = (ef["team"] == squadra).to_numpy()
    y = ef["sot"].to_numpy(dtype=float)[mask]
    lam = ef["lam"].to_numpy(dtype=float)[mask]
    slope, se = V.calibration_slope(y, lam)
    return {"squadra": squadra, "n": int(mask.sum()), "pendenza": slope,
            "se": se, "z_vs_1": (slope - 1.0) / se if se and se > 0 else np.nan}


def sensibilita_r(lam: pd.DataFrame, linee=LINEE,
                  valori=(R_NB2_IC95[0], R_NB2, R_NB2_IC95[1])) -> pd.DataFrame:
    """Quanto le sei probabilita' dipendono da `r`, che non e' stimata qui.

    Si riporta accanto ai numeri e non in fondo (vincolo 5). L'effetto non e'
    uniforme fra le linee: sulla mediana `r` conta poco, sulle code conta molto,
    ed e' esattamente sulle code che stanno la 6.5 e la 7.5.
    """
    l = lam["lam"].to_numpy(dtype=float)
    rows = []
    for ln in linee:
        riga = {"linea": ln}
        for rv in valori:
            riga[f"r={rv:g}"] = float(D.p_over(l, ln, rv).mean())
        riga["escursione"] = max(riga[f"r={rv:g}"] for rv in valori) - \
            min(riga[f"r={rv:g}"] for rv in valori)
        rows.append(riga)
    return pd.DataFrame(rows)
