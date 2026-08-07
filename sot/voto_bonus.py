# -*- coding: utf-8 -*-
"""Fase 9 / Blocco E4 — voto base e bonus.

E' l'ultimo blocco di modellazione della Fase 9, ed e' quello col margine piu'
piccolo. Dopo questo blocco il tetto del progetto — **gli infortuni, che non
sono in nessuna delle due fonti acquisite** — diventa il limite dichiarato
invece che uno fra tanti.

IL MARGINE DI E4 NON E' 8,9 PUNTI: E' 2,5, E LA CORREZIONE E' DEL BLOCCO
------------------------------------------------------------------------
La priorita' di E4 poggiava su un numero pubblicato — «con i bonus noti il MAE
scende da 61,4 a 52,5», cioe' 8,9 punti — che questo blocco ha dovuto misurare
per costruirci sopra il proprio denominatore, e misurandolo l'ha corretto. Due
difetti, indipendenti, e **il piu' grande dei due e' il primo**:

1. **Il campione cambia.** «Bonus noti» gira su **2.204 righe** e non 2.678: chi
   non ha mai giocato in `t` non ha un tasso osservato, e quelle 474 righe
   cadono. Sono le righe **peggiori** — il modello predice punti a chi ne fara'
   zero — quindi toglierle abbassa il MAE da sola. Sulle stesse 2.204 righe il
   modello completo fa **55,01**, non 61,42.
2. **«Bonus noti» non era il bonus.** Era costruito per differenza come
   `punti/presenze - voto_atteso`, che e' l'intero **tasso per presenza**, voto
   compreso. L'identita' si vede appena si prova a costruire anche l'oracolo del
   voto nello stesso modo: da' lo stesso identico numero.

Con le componenti prese separate da `fantapunti.per_giocatore_stagione`, e a
campione fisso, i divari veri sono: **voto 1,24 · bonus 1,44 · entrambi 2,51**
punti di MAE, contro i **55,86** delle presenze. E4 lavora quindi sul **4%**
dell'errore, non sul 14,5%, e ogni percentuale di questo blocco e' riferita a
quel denominatore corretto — che e' il solo modo di non far sembrare grande un
guadagno piccolo.

Il fatto resta quello che era: **le presenze sono il problema, i bonus no.** La
correzione lo rende piu' vero, non meno.

LA COLLISIONE DI `passFreekick`, CHE E' IL RISULTATO METODOLOGICO DI E4.0
-------------------------------------------------------------------------
La strada comoda per i piazzati erano le colonne booleane derivate da
`satisfiedEventsTypes`: `passCorner` e `passFreekick` sono valorizzate in tutte
e cinque le stagioni e derivano pochissimo (rapporto max/min 1,08), quindi
avrebbero passato ogni gate di E1 senza fare rumore.

**`passFreekick` non contiene le punizioni.** E' la stessa identica colonna di
`passCorner`, riga per riga: misurato su 43.176 eventi, i suoi 296 `True`
coincidono esattamente con i 296 `CornerTaken` e hanno intersezione **vuota**
con gli 813 `FreekickTaken` veri (`collisione_passfreekick`). Chi l'avesse usata
avrebbe ottenuto una tabella di "battitori di punizioni" perfettamente
plausibile in cui ogni riga era in realta' un battitore di corner, e nessun
controllo di quadratura se ne sarebbe accorto: i numeri sono dell'ordine di
grandezza giusto.

E' la lezione di `StandingSave` un piano piu' su. Li' il nome di un **qualifier**
non era un identificatore; qui non lo e' il nome di una **colonna**. Ne segue la
scelta del blocco:

    i piazzati si contano dai QUALIFIER (`CornerTaken`, `FreekickTaken`,
    `DirectFreekick`, `IndirectFreekickTaken`), non dalle colonne omonime.

I qualifier sono la strada che E1 aveva gia' istruito e **gia' misurato**:
`CornerTaken` sta a 1,08 e `FreekickTaken` a 1,07 di rapporto max/min fra le
cinque stagioni, cioe' passano `features_giocatore.SOGLIA_QUALIFIER`. La colonna
`passCorner` resta letta e resta in tabella come **controllo indipendente** dei
soli corner, dove le due strade coincidono; `passFreekick` resta letta apposta
per poter pubblicare la collisione invece di limitarsi a evitarla.

PERCHE' UNA RILETTURA DEI CSV, E PERCHE' NON ALLARGANDO `events_slim`
---------------------------------------------------------------------
`events_slim` non porta `qualifiers` (li tiene solo per i cinque tipi di evento
di formazione), quindi i piazzati non sono nel derivato. La strada alternativa
sarebbe allargare `io_events.BOOL_COLS` e ricostruire la cache — ma
`events_slim` e' la cache **condivisa delle Fasi 1-6**, e riscriverla
costringerebbe a rivalidare ogni numero pubblicato in cambio di qualche colonna.
Qui si rilegge con una lista di colonne stretta e si scrive un derivato **a se'**,
come la specifica chiede: sono dati grezzi riletti per uno scopo, non una
ricostruzione strutturale come `player_match` e' stata in E0.

Costo: ~4 minuti a freddo sulle cinque stagioni, poi cache.

I RIGORI SONO L'UNICA COSA CHE NON COSTA LA RILETTURA
------------------------------------------------------
`penaltyScored | penaltyMissed` e' gia' in `events_slim` ed e' gia' dichiarata
equivalente al qualifier `Penalty` (`xg.is_penalty`, verificato sulla 2025-26).
Qui le due strade si contano **affiancate su tutte e cinque le stagioni**
(`coerenza_rigori`): e' una verifica che non passa da nessun modello, ed e' il
controllo che dice se il parsing dei qualifier regge.

CHI E' DEFINITORIO E CHI E' PREDITTORE
---------------------------------------
Vale qui la stessa regola che E2 ha fissato per i cartellini
(`impiego.FONTE_CARTELLINI`) ed E3 per i gol subiti (`difesa.FONTE_MALUS`): **la
fonte dei voti e' definitoria** — e' quella che ha prodotto i `punti_osservati`,
cioe' il bersaglio — e WhoScored e' un **predittore**, mai il bersaglio. Vale per
gli assist (WhoScored ne conta di suoi), per i gol e per i cartellini. Non si
inverte per comodita' di join, e `confronto_assist` misura di quanto le due
fonti divergano invece di assumerle uguali (vincolo 7).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from . import config, features_giocatore as FG, ricognizione as RIC

STAGIONI = config.SEASONS_STORICHE

#: Il derivato dei piazzati. Attraversa le stagioni — la riga porta `stagione` —
#: quindi sta nella cartella di campionato e non dentro nessuna delle cinque.
CACHE_PIAZZATI = config.processed_league_dir() / "fase9_e4_piazzati.parquet"

#: Le colonne che la rilettura chiede ai CSV. **Stretta di proposito**: la
#: ricognizione del Blocco 0 legge tutte e 259 le colonne e costa ~3 minuti in
#: piu' proprio per quello. Qui servono l'identita' della riga, il tipo di evento,
#: i qualifier e le due booleane dei rigori.
COLONNE_LETTE = (
    "matchId", "teamId", "playerId", "eventId", "type", "isShot",
    "minute", "second",
    "penaltyScored", "penaltyMissed",
    # Le due colonne omonime dei piazzati. **Si leggono per essere confrontate**,
    # non per essere usate: vedi `collisione_passfreekick`.
    "passCorner", "passFreekick",
    "qualifiers",
)

#: I qualifier da cui si contano i piazzati e i passaggi chiave. Si cercano nella
#: stringa `qualifiers` **nella forma completa** `'type': '<nome>'`, mai col nome
#: nudo, e non e' pedanteria: `FreekickTaken` nudo e' una sottostringa di
#: `IndirectFreekickTaken`, quindi conterebbe le punizioni indirette dentro le
#: dirette. La forma completa lo impedisce perche' pretende l'apice **prima** del
#: nome. E' la stessa famiglia di errore della collisione di `passFreekick`, e
#: qui e' fermata da `verifica_pattern`, che la misura contro l'elenco vero dei
#: qualifier del Blocco 0 invece di fidarsi.
QUALIFIER = {
    "corner": "CornerTaken",
    "punizione": "FreekickTaken",
    "punizione_diretta": "DirectFreekick",
    "punizione_indiretta": "IndirectFreekickTaken",
    "rigore": "Penalty",
    "passaggio_chiave": "KeyPass",
    "tiro_assistito": "Assisted",
}


#: **Il qualifier `Penalty` non marca il rigorista: marca il rigore.** Misurato su
#: 60 partite del 2024-25, i suoi 92 eventi sono `Foul` 44 (chi l'ha concesso),
#: `PenaltyFaced` 22 e `Save` 4 (il portiere), e solo 22 sono il tiro. Contarlo
#: nudo attribuirebbe "rigori battuti" al difensore che ha commesso il fallo, e
#: darebbe quattro-cinque rigoristi per squadra — cioe' esattamente il numero che
#: `quadratura_rigoristi` esiste per rifiutare.
#:
#: Ristretto a `isShot` coincide **riga per riga** con `penaltyScored |
#: penaltyMissed` (22 = 22, zero discordanze in entrambi i versi). E' la stessa
#: equivalenza che `xg.is_penalty` dichiarava sulla sola 2025-26, con la
#: precisazione che li' era implicita perche' quella funzione riceve gia' solo
#: tiri: fuori da quel contesto la parola "rigore" ha un perimetro piu' largo.
SCOPO_PENALTY = "il qualifier Penalty sta anche su Foul, PenaltyFaced e Save"


def _pattern(nome: str) -> str:
    """La forma completa con cui un qualifier compare nel repr Python.

    I qualifier sono repr Python con apici singoli, non JSON: `{'type': 'X'}`
    oppure `{'type': 'X', 'value': '3'}`. Cercare `'type': 'X'` — con un apice
    **prima** del nome e uno dopo — identifica il nome esatto in entrambi i casi;
    cercare il nome nudo no, ed e' li' che sta la collisione.
    """
    return f"'type': '{nome}'"


class PatternAmbiguo(RuntimeError):
    """Un pattern di qualifier ne identificherebbe piu' di uno."""


def verifica_pattern(qualifier: dict[str, str] = None) -> pd.DataFrame:
    """Ogni pattern identifica **uno** e un solo qualifier fra quelli osservati.

    E' la guardia che rende sicura la ricerca per sottostringa, e non e'
    teorica: `FreekickTaken` e `IndirectFreekickTaken` coesistono nei dati, e
    cercando il **nome nudo** il secondo verrebbe contato dentro il primo. Si
    misura contro l'elenco dei qualifier osservati dal Blocco 0, non contro un
    elenco scritto a mano qui.
    """
    qualifier = QUALIFIER if qualifier is None else qualifier
    if not RIC.CACHE["qualifier"].exists():
        raise FileNotFoundError(
            "manca la ricognizione del Blocco 0: "
            "./.venv/Scripts/python.exe scripts/run_blocco0.py")
    osservati = sorted(pd.read_parquet(RIC.CACHE["qualifier"])["qualifier"].unique())

    righe = []
    for etichetta, nome in qualifier.items():
        pat = _pattern(nome)
        # Quali qualifier osservati produrrebbero questo pattern nel testo?
        colpiti = [q for q in osservati if pat in _pattern(q)]
        righe.append({"etichetta": etichetta, "qualifier": nome,
                      "presente_nei_dati": nome in osservati,
                      "identificati": len(colpiti),
                      "collisioni": ", ".join(q for q in colpiti if q != nome)})
    out = pd.DataFrame(righe)
    cattivi = out[(out["identificati"] != 1) | (~out["presente_nei_dati"])]
    if len(cattivi):
        raise PatternAmbiguo(
            "pattern che non identificano esattamente un qualifier osservato: "
            + ", ".join(f"{r.qualifier} -> {r.identificati}"
                        for r in cattivi.itertuples(index=False)))
    return out


def gate_qualifier(qualifier: dict[str, str] = None) -> pd.DataFrame:
    """Il gate di E1 applicato ai qualifier che questo blocco usa davvero.

    Non si assume dal report di E1 e non si assume da `CLAUDE.md`: si richiama
    `features_giocatore.verifica_qualifier`, che e' la stessa macchina, sulla
    lista effettiva. Presenza in tutte e cinque le stagioni e rapporto max/min
    della frequenza per evento sotto `FG.SOGLIA_QUALIFIER`.

    Resta **necessario e non sufficiente**, per la ragione che E1 ha gia'
    scritto: l'unico controllo sufficiente sarebbe l'id numerico del qualifier,
    che `acquisition/whoscored/main.py:432` butta via tenendo solo il
    `displayName`.
    """
    qualifier = QUALIFIER if qualifier is None else qualifier
    nomi = tuple(dict.fromkeys(qualifier.values()))
    return FG.verifica_qualifier(nomi)


def gate_colonne(colonne=("passCorner", "passFreekick", "penaltyScored",
                          "penaltyMissed")) -> pd.DataFrame:
    """Lo stesso gate, ma sulle **colonne** `satisfiedEventsTypes`.

    E' un altro spazio di nomi rispetto ai qualifier — una colonna booleana del
    CSV, non una voce dentro `qualifiers` — quindi la guardia di E1 non si
    applica tale e quale e la misura si rifa' qui, sulla ricognizione del
    Blocco 0 (`quota_valorizzata`, cioe' "ne' nullo ne' `False`", che e' la
    misura giusta: `notna()` direbbe il contrario del vero).

    **Passare questo gate non basta**, ed e' il punto di tutto il blocco:
    `passFreekick` lo passa a pieni voti e nomina una grandezza che non contiene.
    Il gate dice che una colonna non si e' mossa fra le stagioni; non dice che si
    chiami come cio' che contiene.
    """
    if not RIC.CACHE["colonne"].exists():
        raise FileNotFoundError(
            "manca la ricognizione del Blocco 0: "
            "./.venv/Scripts/python.exe scripts/run_blocco0.py")
    c = pd.read_parquet(RIC.CACHE["colonne"])
    piv = c.pivot(index="colonna", columns="stagione", values="quota_valorizzata")
    piv = piv.reindex(list(colonne))

    out = piv.copy()
    out["stagioni"] = piv.notna().sum(axis=1)
    out["min"], out["max"] = piv.min(axis=1), piv.max(axis=1)
    out["rapporto"] = np.where(out["min"] > 0, out["max"] / out["min"], np.inf)
    out["passa_il_gate"] = ((out["stagioni"] == len(STAGIONI))
                            & (out["rapporto"] <= FG.SOGLIA_QUALIFIER))
    return out.reset_index()


# --------------------------------------------------------------------------
# E4.0 — la rilettura, una stagione per volta
# --------------------------------------------------------------------------

def _leggi_partita(path) -> pd.DataFrame:
    """Un CSV partita, con le sole colonne di `COLONNE_LETTE` che esistono.

    Le booleane assenti si forzano a `False`: e' la trappola di `isOwnGoal`
    generalizzata a tutte le colonne derivate da `satisfiedEventsTypes`, che
    pandas emette solo se in quella partita almeno un evento le soddisfa.
    """
    header = pd.read_csv(path, nrows=0).columns
    use = [c for c in COLONNE_LETTE if c in header]
    df = pd.read_csv(path, usecols=use, low_memory=False)

    for c in ("isShot", "penaltyScored", "penaltyMissed",
              "passCorner", "passFreekick"):
        if c not in df.columns:
            df[c] = False
        df[c] = df[c].astype("boolean").fillna(False).astype(bool)
    for c in ("qualifiers", "type"):
        if c not in df.columns:
            df[c] = ""
    df["qualifiers"] = df["qualifiers"].astype(str)
    return df


def _marca_qualifier(df: pd.DataFrame) -> pd.DataFrame:
    """Una colonna booleana per ogni qualifier dichiarato, dal testo grezzo.

    Ricerca per sottostringa e non `ast.literal_eval`: qui servono i *nomi* e non
    i *valori*, e su milioni di righe il parser costerebbe due ordini di
    grandezza in piu' per lo stesso conteggio. E' la stessa scelta che
    `ricognizione` documenta; la sicurezza della sottostringa e' garantita da
    `verifica_pattern`, non dalla fiducia.
    """
    out = df.copy()
    for etichetta, nome in QUALIFIER.items():
        out[f"q_{etichetta}"] = out["qualifiers"].str.contains(
            _pattern(nome), regex=False)
    return out


def _assist_dal_tiro(df: pd.DataFrame, finestra: int = 3) -> pd.DataFrame:
    """Lega ogni tiro assistito al passaggio chiave che lo precede.

    Il legame **non e' nei dati**: la fonte marca il tiro con `Assisted` e il
    passaggio con `KeyPass`, ma non dice quale passaggio appartenga a quale tiro.
    Si ricostruisce con la regola piu' stretta possibile — il passaggio chiave
    **piu' vicino che precede** il tiro, della **stessa squadra**, entro
    `finestra` eventi — e la quota di tiri che restano senza legame si conta
    invece di sparire (`qualita_assist`).

    Ritorna una riga per tiro assistito legato: `(matchId, teamId, eventId)` del
    tiro e `playerId` di chi ha fatto il passaggio.
    """
    d = df.reset_index(drop=True)
    tiri = d.index[d["isShot"] & d["q_tiro_assistito"]]
    passaggi = d.index[d["q_passaggio_chiave"]]

    righe = []
    for i in tiri:
        squadra = d.at[i, "teamId"]
        # All'indietro dal tiro, al piu' `finestra` eventi.
        for j in range(i - 1, max(i - 1 - finestra, -1), -1):
            if j in passaggi and d.at[j, "teamId"] == squadra:
                righe.append({"matchId": d.at[i, "matchId"],
                              "teamId": squadra,
                              "eventId": d.at[i, "eventId"],
                              "playerId_assist": d.at[j, "playerId"]})
                break
    return pd.DataFrame(righe, columns=["matchId", "teamId", "eventId",
                                        "playerId_assist"])


def _piazzati_stagione(stagione: str) -> tuple[pd.DataFrame, pd.DataFrame, int]:
    """Conteggi per `(playerId, teamId)`, legami assist-tiro e tiri assistiti.

    I tiri assistiti si contano **in questa passata** e non in una funzione a
    parte: sono il denominatore di `qualita_assist`, e ricavarli dopo vorrebbe
    dire riattraversare i 1.889 CSV una seconda volta per un numero che qui e'
    gia' sotto gli occhi.
    """
    files = sorted(config.match_dir(season=stagione).glob("*.csv"))
    if not files:
        raise FileNotFoundError(f"nessun CSV per {stagione}")

    conteggi, legami, assistiti = [], [], 0
    for f in files:
        d = _marca_qualifier(_leggi_partita(f))
        legami.append(_assist_dal_tiro(d))
        assistiti += int((d["isShot"] & d["q_tiro_assistito"]).sum())

        g = d[d["playerId"].notna()].copy()
        g["playerId"] = g["playerId"].astype("int64")
        # **Il rigore si conta sul TIRO, non sul qualifier nudo**: vedi
        # `SCOPO_PENALTY`. Senza `isShot` il fallo da rigore finirebbe nel
        # conteggio del difensore che l'ha commesso.
        g["rigore_tirato"] = g["isShot"] & g["q_rigore"]
        g["rigore_segnato"] = g["penaltyScored"]
        g["rigore_sbagliato"] = g["penaltyMissed"]
        g["rigore_booleane"] = g["penaltyScored"] | g["penaltyMissed"]
        conteggi.append(g.groupby(["playerId", "teamId"]).agg(
            corner_battuti=("q_corner", "sum"),
            punizioni_battute=("q_punizione", "sum"),
            punizioni_dirette=("q_punizione_diretta", "sum"),
            punizioni_indirette=("q_punizione_indiretta", "sum"),
            rigori_battuti=("rigore_tirato", "sum"),
            rigori_battuti_booleane=("rigore_booleane", "sum"),
            rigori_qualifier_ovunque=("q_rigore", "sum"),
            rigori_segnati=("rigore_segnato", "sum"),
            rigori_sbagliati=("rigore_sbagliato", "sum"),
            passaggi_chiave=("q_passaggio_chiave", "sum"),
            corner_colonna=("passCorner", "sum"),
            punizioni_colonna=("passFreekick", "sum"),
        ).reset_index())

    tot = (pd.concat(conteggi, ignore_index=True)
           .groupby(["playerId", "teamId"], as_index=False).sum())
    tot.insert(0, "stagione", stagione)

    lg = pd.concat(legami, ignore_index=True)
    lg.insert(0, "stagione", stagione)
    return tot, lg, assistiti


CACHE_ASSIST = config.processed_league_dir() / "fase9_e4_assist_tiro.parquet"
CACHE_ASSIST_QUALITA = (config.processed_league_dir()
                        / "fase9_e4_assist_qualita.parquet")


def piazzati(stagioni=STAGIONI, force: bool = False) -> pd.DataFrame:
    """Il derivato dei piazzati, con cache. Non tocca la rete e non tocca `raw/`.

    Riga: `(stagione, playerId, teamId)` — la stessa chiave di E1, cosi' che il
    join con lo strato feature non possa moltiplicare.
    """
    caches = (CACHE_PIAZZATI, CACHE_ASSIST, CACHE_ASSIST_QUALITA)
    if not force and all(c.exists() for c in caches):
        p = pd.read_parquet(CACHE_PIAZZATI)
        if set(p["stagione"].unique()) == set(stagioni):
            return p

    conteggi, legami, qualita = [], [], []
    for st in stagioni:
        c, l, n_assistiti = _piazzati_stagione(st)
        conteggi.append(c)
        legami.append(l)
        qualita.append({"stagione": st, "tiri_assistiti": n_assistiti,
                        "legati": len(l)})

    out = pd.concat(conteggi, ignore_index=True).sort_values(
        ["stagione", "playerId", "teamId"]).reset_index(drop=True)
    out.to_parquet(CACHE_PIAZZATI, index=False)
    pd.concat(legami, ignore_index=True).to_parquet(CACHE_ASSIST, index=False)
    pd.DataFrame(qualita).to_parquet(CACHE_ASSIST_QUALITA, index=False)
    return out


def legami_assist(stagioni=STAGIONI, force: bool = False) -> pd.DataFrame:
    """I legami passaggio-chiave -> tiro, ricostruiti da `piazzati`."""
    piazzati(stagioni, force=force)
    return pd.read_parquet(CACHE_ASSIST)


# --------------------------------------------------------------------------
# Le verifiche di E4.0. Nessuna passa da un modello.
# --------------------------------------------------------------------------

def collisione_passfreekick(stagione: str = "2024-2025",
                            n_partite: int = 30) -> pd.DataFrame:
    """La misura che squalifica `passFreekick`. E' il risultato di E4.0.

    Tre righe, e servono tutte e tre: la colonna coincide con `passCorner`, e'
    **disgiunta** dai `FreekickTaken` veri, e coincide con i `CornerTaken`. Una
    sola delle tre lascerebbe aperta la lettura "e' una definizione diversa di
    punizione"; le tre insieme dicono che la colonna e' il corner.

    Gira su un campione di partite e non sulle cinque stagioni perche' e' una
    verifica di **identita' riga per riga**: se una sola riga discorda il fatto
    e' un altro, e per accorgersene bastano trentamila eventi.
    """
    files = sorted(config.match_dir(season=stagione).glob("*.csv"))[:n_partite]
    d = pd.concat([_marca_qualifier(_leggi_partita(f)) for f in files],
                  ignore_index=True)
    return pd.DataFrame([
        {"confronto": "passFreekick == passCorner (riga per riga)",
         "eventi": len(d), "a": int(d["passFreekick"].sum()),
         "b": int(d["passCorner"].sum()),
         "in_comune": int((d["passFreekick"] & d["passCorner"]).sum()),
         "identiche": bool((d["passFreekick"] == d["passCorner"]).all())},
        {"confronto": "passFreekick vs qualifier FreekickTaken",
         "eventi": len(d), "a": int(d["passFreekick"].sum()),
         "b": int(d["q_punizione"].sum()),
         "in_comune": int((d["passFreekick"] & d["q_punizione"]).sum()),
         "identiche": bool((d["passFreekick"] == d["q_punizione"]).all())},
        {"confronto": "passCorner vs qualifier CornerTaken",
         "eventi": len(d), "a": int(d["passCorner"].sum()),
         "b": int(d["q_corner"].sum()),
         "in_comune": int((d["passCorner"] & d["q_corner"]).sum()),
         "identiche": bool((d["passCorner"] == d["q_corner"]).all())},
    ])


def coerenza_rigori(p: pd.DataFrame = None) -> pd.DataFrame:
    """Le due strade ai rigori, affiancate su tutte e cinque le stagioni.

    Il qualifier `Penalty` e le due booleane `penaltyScored | penaltyMissed` sono
    due derivazioni indipendenti della stessa grandezza. `xg.is_penalty` le
    dichiarava equivalenti sulla sola 2025-26 (106 = 106); qui la dichiarazione
    si estende alle altre quattro, ed e' il controllo che dice se il parsing dei
    qualifier di questo blocco regge.
    """
    p = piazzati() if p is None else p
    g = p.groupby("stagione").agg(
        da_qualifier=("rigori_battuti", "sum"),
        da_booleane=("rigori_battuti_booleane", "sum"),
        qualifier_senza_isShot=("rigori_qualifier_ovunque", "sum"),
        segnati=("rigori_segnati", "sum"),
        sbagliati=("rigori_sbagliati", "sum")).reset_index()
    g["scarto"] = g["da_qualifier"] - g["da_booleane"]
    g["conversione"] = g["segnati"] / (g["segnati"] + g["sbagliati"])
    return g


def coerenza_corner(p: pd.DataFrame = None) -> pd.DataFrame:
    """Corner dal qualifier contro corner dalla colonna, per stagione.

    E' il verso positivo della collisione: sui corner le due strade coincidono,
    quindi il disaccordo sulle punizioni non e' "i qualifier dicono un'altra
    cosa" ma proprio la colonna sbagliata.
    """
    p = piazzati() if p is None else p
    g = p.groupby("stagione").agg(
        da_qualifier=("corner_battuti", "sum"),
        da_colonna=("corner_colonna", "sum"),
        punizioni_da_qualifier=("punizioni_battute", "sum"),
        punizioni_da_colonna=("punizioni_colonna", "sum")).reset_index()
    g["scarto_corner"] = g["da_qualifier"] - g["da_colonna"]
    g["scarto_punizioni"] = g["punizioni_da_qualifier"] - g["punizioni_da_colonna"]
    return g


def quadratura_rigoristi(p: pd.DataFrame = None,
                         min_rigori: int = 1) -> pd.DataFrame:
    """Quanti rigoristi distinti ha una squadra in una stagione.

    E' il test di quadratura chiesto dalla specifica, e la sua forza sta nel
    fatto che la risposta e' nota **prima** di guardarla: una squadra ha uno o
    due rigoristi. Se ne uscissero cinque, il problema sarebbe il parsing, non la
    squadra.
    """
    p = piazzati() if p is None else p
    d = p[p["rigori_battuti"] >= min_rigori]
    g = d.groupby(["stagione", "teamId"])["playerId"].nunique().rename(
        "rigoristi").reset_index()
    dist = (g.groupby("rigoristi").size().rename("squadre_stagione")
            .reset_index())
    dist["quota"] = dist["squadre_stagione"] / len(g)
    return dist


def concentrazione_rigoristi(p: pd.DataFrame = None,
                             min_rigori: int = 3) -> pd.DataFrame:
    """Quanta parte dei rigori di una squadra va al suo battitore principale.

    **Esiste perche' `quadratura_rigoristi` non passa alla lettera**, e la
    diagnosi va misurata invece che addotta. La specifica si aspettava 1-2
    rigoristi distinti per squadra-stagione nella grande maggioranza dei casi; si
    osservano 1-2 nel 47%, tre nel 25% e quattro nel 23%.

    Che non sia il parsing e' gia' dimostrato da `coerenza_rigori`, che e' un
    controllo **piu' forte** di questo: il conteggio dal qualifier coincide
    esattamente con quello dalle due booleane, su tutte e cinque le stagioni,
    scarto zero. Due derivazioni indipendenti che concordano non possono essere
    sbagliate nello stesso modo.

    Cio' che si rompe e' la **premessa**, e questa funzione dice quale pezzo:
    "battitore designato" e' un concetto sensato solo se la sua quota e' alta.
    Contare le *teste* mette sullo stesso piano chi ne ha battuti sei e chi ne
    ha battuto uno perche' il designato era fuori quel giorno.

    `min_rigori` esclude le squadre con troppi pochi rigori perche' la domanda
    abbia senso: con due rigori in stagione "quota del primo" vale 0,5 o 1,0 e
    non descrive nessuna gerarchia.
    """
    p = piazzati() if p is None else p
    d = p[p["rigori_battuti"] > 0]
    righe = []
    for (st, team), sub in d.groupby(["stagione", "teamId"]):
        tot = int(sub["rigori_battuti"].sum())
        if tot < min_rigori:
            continue
        ordinati = sub["rigori_battuti"].sort_values(ascending=False).to_numpy()
        righe.append({"stagione": st, "teamId": team, "rigori": tot,
                      "battitori": len(ordinati),
                      "quota_primo": ordinati[0] / tot,
                      "quota_primi_due": ordinati[:2].sum() / tot})
    out = pd.DataFrame(righe)
    return out


def sintesi_concentrazione(c: pd.DataFrame = None) -> pd.DataFrame:
    """Una riga: la concentrazione mediana e quanto spesso il primo domina."""
    c = concentrazione_rigoristi() if c is None else c
    return pd.DataFrame([{
        "squadre_stagione": len(c),
        "rigori_mediani": float(c["rigori"].median()),
        "battitori_mediani": float(c["battitori"].median()),
        "quota_primo_mediana": float(c["quota_primo"].median()),
        "quota_primi_due_mediana": float(c["quota_primi_due"].median()),
        "quota_primo_sopra_50pct": float((c["quota_primo"] >= 0.5).mean()),
        "primi_due_sopra_80pct": float((c["quota_primi_due"] >= 0.8).mean()),
    }])


def qualita_assist(stagioni=STAGIONI) -> pd.DataFrame:
    """Quanti tiri assistiti restano senza passaggio chiave legato.

    La ricostruzione del legame e' una **derivazione dichiarata**, non un dato:
    va quindi misurata invece che creduta. La quota legata e' il numero da
    leggere accanto a ogni xA — se fosse bassa, l'xA non sarebbe l'xA di quel
    giocatore ma l'xA dei suoi passaggi che il legame ha saputo ritrovare.
    """
    piazzati(stagioni)
    q = pd.read_parquet(CACHE_ASSIST_QUALITA)
    q = q[q["stagione"].isin(stagioni)].copy()
    q["quota_legata"] = np.where(q["tiri_assistiti"] > 0,
                                 q["legati"] / q["tiri_assistiti"], np.nan)
    return q.reset_index(drop=True)


# --------------------------------------------------------------------------
# E4.2 — npxG e xA, e la verifica dei cinque fit rimandata due volte
# --------------------------------------------------------------------------

def npxg_xa(stagioni=STAGIONI) -> pd.DataFrame:
    """npxG e xA per `(stagione, playerId, teamId)`, dai tiri e dai legami.

    **npxG e' l'xG al netto dei rigori**, e il filtro non e' una sottrazione a
    occhio: `xg.fit_predict_xg` marca i rigori con `xg_source == "penalty_rate"`
    perche' li stima a parte (la loro geometria e' degenere). Tenere `xg_source
    == "model"` e' quindi *esattamente* il non-rigore, per costruzione.

    **xA e' la somma degli xG dei tiri che quel giocatore ha servito**, via il
    legame ricostruito in E4.0. Nessun tiro assistito e' un rigore — un rigore
    non si assiste — e infatti il join non ne trova nemmeno uno: e' un controllo
    interno che passa.

    ATTENZIONE, E VA DETTO ACCANTO A OGNI NUMERO: `xg` sta su **cinque scale**,
    una per fit (`xg_fit`). Sommare npxG attraverso le stagioni e' lecito solo se
    la differenza fra i cinque fit e' di **sola intercetta** — che e' la verifica
    di `differenza_fra_fit`, ed e' la ragione per cui questa funzione ritorna il
    dato grezzo e non una somma multi-stagione gia' fatta.
    """
    lg = legami_assist(stagioni)
    pezzi = []
    for st in stagioni:
        s = pd.read_parquet(config.shots_parquet(season=st))
        aperto = s[s["xg_source"] == "model"]
        npxg = (aperto[aperto["playerId"].notna()]
                .groupby(["playerId", "teamId"])["xg"].sum().rename("npxg"))

        l = lg[lg["stagione"] == st]
        n = len(l)
        m = l.merge(s[["matchId", "teamId", "eventId", "xg", "xg_source"]],
                    on=["matchId", "teamId", "eventId"], how="inner")
        # La chiave `(matchId, teamId, eventId)` ha **una** collisione nota su
        # 2,8 milioni di righe (`io_events`), quindi la cardinalita' si verifica
        # invece di assumerla.
        if len(m) > n:
            raise AssertionError(
                f"{st}: il join dei legami ha moltiplicato le righe "
                f"({n} -> {len(m)})")
        xa = (m[m["playerId_assist"].notna()]
              .groupby(["playerId_assist", "teamId"])["xg"].sum().rename("xa"))
        xa.index = xa.index.set_names(["playerId", "teamId"])
        serviti = (m[m["playerId_assist"].notna()]
                   .groupby(["playerId_assist", "teamId"]).size()
                   .rename("tiri_serviti"))
        serviti.index = serviti.index.set_names(["playerId", "teamId"])

        d = pd.concat([npxg, xa, serviti], axis=1).fillna(0.0).reset_index()
        d.insert(0, "stagione", st)
        pezzi.append(d)

    out = pd.concat(pezzi, ignore_index=True)
    out["playerId"] = out["playerId"].astype("int64")
    out["teamId"] = out["teamId"].astype("int64")
    return out


def differenza_fra_fit(stagioni=STAGIONI) -> pd.DataFrame:
    """I cinque fit di xG differiscono per la sola intercetta? Si misura qui.

    E' la verifica **rimandata due volte** — E0 l'ha dichiarata necessaria, E3
    l'ha potuta evitare perche' il modello dei gol non usa l'xG — e va fatta ora
    perche' qui e' la prima volta che l'xG attraversa le stagioni sommato.

    Il disegno e' un confronto fra due modelli sulla stessa popolazione di tiri
    su azione delle cinque stagioni:

        `intercetta`   una logistica con le feature di `xg.build_features` piu'
                       **quattro indicatrici di stagione**: il livello puo'
                       muoversi, la forma no;
        `interazioni`  la stessa piu' i prodotti stagione x feature: anche la
                       forma puo' muoversi.

    Il confronto e' **fuori campione**, con i fold raggruppati per `matchId` che
    `sot/xg.py` usa gia': i tiri di una stessa partita condividono contesto, e
    separarli lascerebbe passare informazione. Se le interazioni non migliorano
    la log-verosimiglianza fuori campione, la differenza fra i cinque fit e' di
    sola intercetta e sommare npxG attraverso le stagioni e' lecito **dopo** la
    standardizzazione di E1. Se migliorano, non lo e', e npxG entra per stagione.

    Il **baseline stupido** e' la terza riga (nessun termine di stagione), senza
    la quale non si saprebbe se il gradino di stagione serva a qualcosa.
    """
    from sklearn.linear_model import LogisticRegression
    from sklearn.model_selection import GroupKFold
    from sklearn.metrics import log_loss
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import StandardScaler

    from . import xg as XG

    pezzi = []
    for st in stagioni:
        s = pd.read_parquet(config.shots_parquet(season=st))
        s = s[~XG.is_penalty(s)].copy()
        s["stagione"] = st
        pezzi.append(s)
    tutti = pd.concat(pezzi, ignore_index=True)

    X = XG.build_features(tutti).to_numpy()
    y = tutti["is_goal"].astype(int).to_numpy()
    gruppi = tutti["matchId"].to_numpy()
    # Indicatrici di stagione, prima esclusa (riferimento).
    d_st = pd.get_dummies(tutti["stagione"], drop_first=True).astype(float).to_numpy()

    disegni = {
        "senza stagione (baseline)": X,
        "solo intercetta di stagione": np.hstack([X, d_st]),
        "interazioni stagione x feature": np.hstack(
            [X, d_st, np.hstack([X * d_st[:, [k]] for k in range(d_st.shape[1])])]),
    }

    righe = []
    for nome, M in disegni.items():
        pred = np.full(len(y), np.nan)
        gkf = GroupKFold(n_splits=XG.N_FOLDS)
        for tr, te in gkf.split(M, y, gruppi):
            mod = Pipeline([("scale", StandardScaler()),
                            ("clf", LogisticRegression(C=1.0, max_iter=4000,
                                                       random_state=config.SEED))])
            mod.fit(M[tr], y[tr])
            pred[te] = mod.predict_proba(M[te])[:, 1]
        righe.append({"disegno": nome, "parametri": M.shape[1],
                      "logloss_fuori_campione": float(log_loss(y, pred)),
                      "tiri": int(len(y))})
    out = pd.DataFrame(righe)
    base = float(out.loc[out["disegno"] == "solo intercetta di stagione",
                         "logloss_fuori_campione"].iloc[0])
    out["guadagno_su_intercetta"] = base - out["logloss_fuori_campione"]
    return out


def scale_dei_fit(stagioni=STAGIONI) -> pd.DataFrame:
    """I cinque fit messi sugli **stessi** tiri. E' il test diretto della scala.

    `differenza_fra_fit` risponde alla domanda in forma indiretta — un modello
    poolato con interazioni non batte quello senza — ma cio' che il progetto usa
    davvero sono **cinque fit separati**, uno per stagione. La domanda letterale
    e' allora: applicati alla stessa popolazione di tiri, i cinque danno lo
    stesso numero?

    Se lo danno, `xg_fit` e' un'etichetta di provenienza e non di scala, e
    sommare npxG attraverso le stagioni e' lecito. Se non lo danno, la
    differenza fra i fit e' reale e va portata dentro come effetto.

    La popolazione comune sono **tutti** i tiri su azione delle cinque stagioni:
    non i tiri di una stagione sola, che favorirebbe il fit di quella stagione.
    """
    from . import xg as XG

    pezzi = []
    for st in stagioni:
        s = pd.read_parquet(config.shots_parquet(season=st))
        s = s[~XG.is_penalty(s)].copy()
        s["stagione"] = st
        pezzi.append(s)
    tutti = pd.concat(pezzi, ignore_index=True)
    X_comune = XG.build_features(tutti).to_numpy()
    tasso_vero = float(tutti["is_goal"].mean())

    righe, primo = [], None
    for st in stagioni:
        s = tutti[tutti["stagione"] == st]
        mod = XG.fit_full(s)
        p = mod.predict_proba(X_comune)[:, 1]
        primo = p if primo is None else primo
        righe.append({"fit_della_stagione": st, "tiri_del_fit": len(s),
                      "xg_medio_sui_tiri_comuni": float(p.mean()),
                      "sd_sui_tiri_comuni": float(p.std()),
                      # La FORMA: se i cinque ordinano i tiri allo stesso modo,
                      # la correlazione e' ~1 e cio' che li separa e' il livello.
                      "corr_col_primo_fit": float(np.corrcoef(p, primo)[0, 1])})
    out = pd.DataFrame(righe)
    out["scarto_dal_tasso_vero"] = out["xg_medio_sui_tiri_comuni"] - tasso_vero
    # L'escursione fra i cinque, in quota del livello: e' il numero da leggere.
    out["escursione_relativa"] = (
        (out["xg_medio_sui_tiri_comuni"].max()
         - out["xg_medio_sui_tiri_comuni"].min())
        / out["xg_medio_sui_tiri_comuni"].mean())
    return out


# --------------------------------------------------------------------------
# La forza di squadra della stagione BERSAGLIO
#
# `difesa.forza_difensiva_attesa` fa gia' meta' del lavoro e si riusa tale e
# quale. L'altra meta' — quanto una squadra segna — non esiste come funzione
# perche' E3 non ne aveva bisogno: il suo bersaglio erano i gol subiti dal
# portiere. Qui serve, perche' il voto di un attaccante dipende da quanto la sua
# squadra attacca, e i rigori attesi sono un tasso di squadra.
#
# **La costante di smorzamento e' la stessa di E3 e per la stessa ragione**
# (dieci partite ~ un quarto di stagione, l'ordine a cui una squadra smette di
# essere rumore). E' ridichiarata qui invece di importare `SMORZAMENTO_DIFESA`
# perche' il nome direbbe una cosa falsa applicato all'attacco, e un domani le
# due potrebbero divergere senza che nessuno se ne accorga.
# --------------------------------------------------------------------------

SMORZAMENTO_SQUADRA = 10.0


def _forza_attesa(stagione: str, colonna: str, gsp: pd.DataFrame,
                  smorzamento: float = SMORZAMENTO_SQUADRA) -> pd.Series:
    """Media per partita di `colonna` in `stagione`, dal solo passato.

    Stessa forma di `difesa.forza_difensiva_attesa`: ultima stagione disponibile,
    shrinkage verso la media di campionato. Chi non ha passato — le neopromosse —
    **non compare**, e a valle prende `nan` invece di un numero inventato: la
    Serie B non e' nel repository.
    """
    passato = gsp[gsp["stagione"] < stagione]
    if passato.empty:
        return pd.Series(dtype=float)
    passato = passato[passato["stagione"] == passato["stagione"].max()]
    media_lega = float(passato[colonna].mean())
    g = passato.groupby("teamId")[colonna].agg(["sum", "size"])
    return ((g["sum"] + smorzamento * media_lega)
            / (g["size"] + smorzamento)).rename(f"{colonna}_atteso")


def forza_squadra(stagioni=None, gsp: pd.DataFrame = None) -> pd.DataFrame:
    """Attacco, difesa e rigori attesi di ogni squadra, per stagione bersaglio.

    **I rigori attesi non vengono da E3.1**, e la precisazione non e' pedanteria:
    E3.1 modella i **gol**, e i rigori assegnati sono un'altra grandezza (~0,28
    per partita contro ~1,4 gol). Attribuire a un modello validato una stima che
    non ha prodotto sarebbe prendere in prestito la sua validazione. Qui i rigori
    attesi sono un tasso di squadra dal solo passato, con lo stesso shrinkage
    delle altre due colonne e senza nessuna validazione ereditata.
    """
    from . import difesa as DF

    gsp = DF.gol_squadra_partita() if gsp is None else gsp
    rig = _rigori_squadra_partita(gsp)

    stagioni = list(config.SEASONS_STORICHE if stagioni is None else stagioni)
    pezzi = []
    for st in stagioni:
        a = _forza_attesa(st, "gol_fatti", gsp)
        d = _forza_attesa(st, "gol_subiti", gsp)
        r = _forza_attesa(st, "rigori", rig)
        if a.empty:
            continue
        x = pd.concat([a, d, r], axis=1).reset_index()
        x.insert(0, "stagione", st)
        pezzi.append(x)
    if not pezzi:
        return pd.DataFrame(columns=["stagione", "teamId", "gol_fatti_atteso",
                                     "gol_subiti_atteso", "rigori_atteso"])
    return pd.concat(pezzi, ignore_index=True)


def _rigori_squadra_partita(gsp: pd.DataFrame) -> pd.DataFrame:
    """Rigori battuti per squadra-partita, dalle booleane di `events_slim`.

    Si usa la strada delle **booleane** e non quella dei qualifier, benche' E4.0
    abbia dimostrato che coincidono: questa non costa una rilettura, e coincidere
    e' proprio cio' che rende la scelta indifferente. La verifica sta in
    `coerenza_rigori`; qui si prende la piu' economica delle due.
    """
    from . import io_events

    pezzi = []
    for st in sorted(gsp["stagione"].unique()):
        ev = io_events.load_events(season=st)
        pen = ev[ev["penaltyScored"] | ev["penaltyMissed"]]
        c = (pen.groupby(["matchId", "teamId"]).size().rename("rigori")
             .reset_index())
        c.insert(0, "stagione", st)
        pezzi.append(c)
    r = pd.concat(pezzi, ignore_index=True)
    # Le squadre-partita **senza** rigori devono valere zero, non sparire: sono
    # la grande maggioranza, e ricostruire l'universo dai soli rigori
    # gonfierebbe il tasso di un fattore quattro. E' la stessa trappola delle
    # squadre-partita a zero tiri gia' incontrata nella verifica di stabilita'.
    universo = gsp[["stagione", "matchId", "teamId"]]
    out = universo.merge(r, on=["stagione", "matchId", "teamId"], how="left")
    out["rigori"] = out["rigori"].fillna(0.0)
    return out


# --------------------------------------------------------------------------
# LO STRATO FEATURE DI E4, E LE DUE CHIAVI
#
# Le feature nascono su `(stagione, playerId, teamId)` — la chiave di WhoScored,
# che e' quella di E0 e di E1 — e il bersaglio vive su `(stagione, giocatore_id)`,
# che e' quella dei voti. Il ponte e' l'aggancio di E0, riusato e non rifatto:
# `impiego._ponte` lo fa gia' e lo si chiama, invece di riscriverlo con un'altra
# regola che potrebbe divergere senza che nessuno se ne accorga.
#
# AGGREGARE FRA DUE SQUADRE: QUI SI SOMMA, IN E2 SI PRENDEVA LA PRINCIPALE
# ------------------------------------------------------------------------
# Chi cambia squadra a gennaio ha due righe. E2 teneva quella con piu' minuti,
# perche' le sue feature erano **quote di esposizione** e mediarle avrebbe
# mescolato due gerarchie. Qui le feature sono **conteggi e tassi di
# produzione**, e la grandezza sensata e' il totale di stagione: chi ha fatto sei
# gol in due maglie ne ha fatti sei. Le due scelte sono diverse perche' le due
# grandezze lo sono, ed e' dichiarato invece che ereditato.
# --------------------------------------------------------------------------

#: Esposizione minima in t-1 perche' una riga entri nell'ADDESTRAMENTO. Non
#: filtra la valutazione — escludere dalla valutazione chi ha poche presenze
#: sarebbe togliere dal campione la parte che il modello deve indovinare, ed e'
#: la lezione del pavimento di E2.
#:
#: Serve perche' qui il bersaglio e' un **voto medio**: su due presenze e' una
#: media di due numeri, cioe' quasi solo rumore, e addestrarci sopra insegnerebbe
#: al modello il rumore. Cinque presenze e' la stessa soglia con cui
#: `modello_asta._stima_k` ammette un giocatore allo shrinkage. DICHIARATA.
MIN_PRESENZE_ADDESTRAMENTO = 5
PAVIMENTI_ACCANTO = (0, 5, 10, 20)


def feature_whoscored(stagioni=STAGIONI) -> pd.DataFrame:
    """Lo strato feature lato WhoScored, per `(stagione, playerId, teamId)`.

    Mette insieme tre cose gia' costruite altrove — la tabella di E1, il derivato
    dei piazzati di E4.0 e npxG/xA — e non ne ricalcola nessuna.
    """
    from . import features_giocatore as FGmod

    base = FGmod.costruisci(stagioni)["feature"]
    tenute = ["stagione", "playerId", "teamId", "playerName", "role",
              "minuti", "presenze", "novantesimi", "partite_squadra",
              "gol", "tiri", "sot", "xg", "falli", "ammonizioni", "tocchi",
              "tocchi_area", "x_medio", "passaggi",
              "falli_per_90", "ammonizioni_per_90", "x_medio",
              "quota_tocchi_area", "tocchi_per_90"]
    base = base[[c for c in dict.fromkeys(tenute) if c in base.columns]].copy()

    n = len(base)
    out = base.merge(piazzati(stagioni), on=["stagione", "playerId", "teamId"],
                     how="left")
    out = out.merge(npxg_xa(stagioni), on=["stagione", "playerId", "teamId"],
                    how="left")
    assert len(out) == n, "un join dello strato feature ha moltiplicato le righe"

    conteggi = ["corner_battuti", "punizioni_battute", "punizioni_dirette",
                "punizioni_indirette", "rigori_battuti", "rigori_segnati",
                "rigori_sbagliati", "passaggi_chiave", "npxg", "xa",
                "tiri_serviti"]
    out[conteggi] = out[conteggi].fillna(0.0)
    return out


def per_giocatore(stagioni=STAGIONI) -> pd.DataFrame:
    """Lo stesso strato, portato su `(stagione, giocatore_id)` sommando.

    Le righe che l'aggancio non risolve **escono**, e quante sono si conta invece
    di lasciarle sparire: e' il difetto che la coda di E0 ha reso visibile.
    """
    from . import impiego as IMP

    f = feature_whoscored(stagioni)
    ponte = IMP._ponte(stagioni)

    n = len(f)
    m = f.merge(ponte, on=["stagione", "playerId", "teamId"], how="inner")
    perse = n - len(m)

    somme = ["minuti", "presenze", "novantesimi", "gol", "tiri", "sot", "xg",
             "falli", "ammonizioni", "tocchi", "tocchi_area", "passaggi",
             "corner_battuti", "punizioni_battute", "punizioni_dirette",
             "punizioni_indirette", "rigori_battuti", "rigori_segnati",
             "rigori_sbagliati", "passaggi_chiave", "npxg", "xa", "tiri_serviti"]
    g = m.groupby(["stagione", "giocatore_id"], as_index=False).agg(
        {**{c: "sum" for c in somme},
         "playerName": "first", "role": "first",
         # La squadra di t-1 e' quella in cui ha giocato di piu': serve solo a
         # sapere se ha cambiato club, non a pesare niente.
         "teamId": "first"})

    # I tassi si ricalcolano DOPO la somma, non si mediano: la media di due
    # tassi con denominatori diversi non e' il tasso del totale.
    n90 = g["novantesimi"].replace(0, np.nan)
    g["npxg_per_90"] = g["npxg"] / n90
    g["xa_per_90"] = g["xa"] / n90
    g["gol_per_90"] = g["gol"] / n90
    g["falli_per_90"] = g["falli"] / n90
    g["ammonizioni_per_90"] = g["ammonizioni"] / n90
    g["passaggi_chiave_per_90"] = g["passaggi_chiave"] / n90
    g["corner_per_90"] = g["corner_battuti"] / n90
    g["punizioni_dirette_per_90"] = g["punizioni_dirette"] / n90
    g["quota_tocchi_area"] = g["tocchi_area"] / g["tocchi"].replace(0, np.nan)
    g.attrs["righe_perse_nel_ponte"] = perse
    return g


def residuo_ponte(stagioni=STAGIONI) -> pd.DataFrame:
    """Che cosa il ponte a `giocatore_id` lascia indietro, in righe e in minuti.

    Un conteggio di righe da solo direbbe "il 22% del campione sparisce", che
    suona grave e sarebbe letto male: quelle righe portano lo **0,13% dei
    minuti**, perche' 878 su 891 sono giocatori con zero minuti — convocati mai
    scesi in campo, che la fonte dei voti non elenca affatto perche' non hanno
    preso nessun voto. E' il quarto stato di E0 visto dall'altro lato.

    Le poche righe con minuti veri sono il residuo gia' documentato dalla coda di
    E0 (collisioni di nome), e restano dichiarate invece che risolte d'ufficio.
    """
    from . import impiego as IMP

    f = feature_whoscored(stagioni)
    m = f.merge(IMP._ponte(stagioni), on=["stagione", "playerId", "teamId"],
                how="left", indicator=True)
    perse = m[m["_merge"] == "left_only"]
    return pd.DataFrame([{
        "righe_totali": len(f), "righe_perse": len(perse),
        "quota_righe": len(perse) / len(f),
        "quota_minuti": float(perse["minuti"].sum() / f["minuti"].sum()),
        "perse_a_zero_minuti": int((perse["minuti"] == 0).sum()),
        "perse_sopra_450_minuti": int((perse["minuti"] > 450).sum()),
        "minuti_massimi_persi": float(perse["minuti"].max()),
    }])


# --------------------------------------------------------------------------
# Il registro delle candidate di E4, e il gate di E1 applicato loro
#
# E1 ha misurato 19 candidate e ne ha lasciate cinque irriducibili. Le candidate
# di E4 sono **nuove** — npxG, xA, i piazzati — quindi il loro verdetto non
# esiste e non si puo' ereditare: si misura qui, con la stessa soglia e la stessa
# macchina. Ogni candidata e' un rapporto `num/den` dichiarato, per la stessa
# ragione di E1: e' cio' che rende il riferimento di campionato la stessa
# grandezza del valore del singolo.
# --------------------------------------------------------------------------

CANDIDATE_E4 = (
    ("npxg_per_90", "npxg", "novantesimi"),
    ("xa_per_90", "xa", "novantesimi"),
    ("passaggi_chiave_per_90", "passaggi_chiave", "novantesimi"),
    ("corner_per_90", "corner_battuti", "novantesimi"),
    ("punizioni_dirette_per_90", "punizioni_dirette", "novantesimi"),
    ("rigori_per_90", "rigori_battuti", "novantesimi"),
    ("gol_per_90", "gol", "novantesimi"),
    ("falli_per_90", "falli", "novantesimi"),
    ("ammonizioni_per_90", "ammonizioni", "novantesimi"),
    ("quota_tocchi_area", "tocchi_area", "tocchi"),
)


def standardizza_e4(g: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Aggiunge le colonne `_rel` e ritorna anche i riferimenti di campionato.

    `x_rel = x / m_s - 1`, con `m_s = somma(num)/somma(den)` su tutta la
    stagione. E' la regola di E1 alla lettera, applicata alle candidate nuove.
    """
    out = g.copy()
    righe = []
    for nome, num, den in CANDIDATE_E4:
        for st, blocco in g.groupby("stagione"):
            d = float(blocco[den].sum())
            righe.append({"stagione": st, "grandezza": nome,
                          "media": float(blocco[num].sum()) / d if d else np.nan,
                          "n": int((blocco[den] > 0).sum())})
    rif = pd.DataFrame(righe)
    tavola = rif.set_index(["grandezza", "stagione"])["media"]
    for nome, num, den in CANDIDATE_E4:
        # La colonna grezza si **ricalcola dal rapporto dichiarato**, invece di
        # fidarsi di una colonna omonima gia' in tabella: e' cio' che garantisce
        # che numeratore e denominatore del singolo siano gli stessi del
        # riferimento di campionato. Se divergessero, la standardizzazione
        # dividerebbe due grandezze diverse.
        d = out[den].astype(float)
        out[nome] = np.where(d > 0, out[num].astype(float) / d.replace(0, np.nan),
                             np.nan)
        m = np.array([tavola.get((nome, s), np.nan) for s in out["stagione"]])
        with np.errstate(invalid="ignore", divide="ignore"):
            out[f"{nome}_rel"] = np.where(np.isfinite(m) & (m != 0),
                                          out[nome] / m - 1.0, np.nan)
    return out, rif


def deriva_e4(g: pd.DataFrame = None,
              min_minuti: float = FG.MIN_MINUTI_DERIVA) -> pd.DataFrame:
    """La deriva fra stagioni delle candidate di E4, prima e dopo. Gate di E1.

    Stessa soglia (`FG.SOGLIA_DERIVA`, 5%) e stessa lettura: la deriva della
    colonna `_rel` si misura su `rel + 1`, non su `rel`, perche' su una serie
    centrata vicino allo zero il rapporto e' dominato dal denominatore — trappola
    trovata nella coda di E2 e qui riusata invece di essere ritrovata.
    """
    if g is None:
        g, _ = standardizza_e4(per_giocatore())
    d = g[g["minuti"] >= min_minuti] if min_minuti else g

    righe = []
    for nome, _num, _den in CANDIDATE_E4:
        grezza = d.groupby("stagione")[nome].mean().dropna()
        rel = d.groupby("stagione")[f"{nome}_rel"].mean().dropna()
        if len(grezza) < 2:
            continue
        dg = float((grezza.max() - grezza.min()) / abs(grezza.mean()))
        dr = float(((rel + 1).max() - (rel + 1).min()) / abs((rel + 1).mean()))
        righe.append({
            "candidata": nome, "prima": float(grezza.iloc[0]),
            "ultima": float(grezza.iloc[-1]),
            "deriva_grezza": dg, "deriva_std": dr,
            "verdetto": (FG.VERDETTI[0] if dg <= FG.SOGLIA_DERIVA
                         else FG.VERDETTI[1] if dr <= FG.SOGLIA_DERIVA
                         else FG.VERDETTI[2])})
    return pd.DataFrame(righe).sort_values(
        "deriva_grezza", ascending=False).reset_index(drop=True)


# --------------------------------------------------------------------------
# E4.1 - E4.5 — i modelli, e la valutazione sulle stesse quattro transizioni
#
# Specificazione deliberatamente povera, per la stessa ragione di E2: minimi
# quadrati regolarizzati sulle feature di t-1, stimati sulle sole stagioni
# precedenti a quella prevista, `ALPHA` dichiarato e nessuna ricerca di
# iperparametri. Con quattro transizioni una ricerca sarebbe soprattutto
# adattamento, e il progetto ha gia' quattro risultati negativi che dicono
# quanto costa non saperlo.
#
# LE CINQUE CANDIDATE CHE E1 DICHIARA IRRIDUCIBILI
# -------------------------------------------------
# `deriva_e4` marca cinque candidate come "serve effetto di stagione": npxG,
# rigori, punizioni dirette, corner e quota dei tocchi in area. **Un effetto di
# stagione esplicito non e' usabile fuori campione**: la stagione bersaglio non
# e' fra quelle su cui si e' stimato, e il suo effetto non esiste. Qui entrano
# quindi nella forma `_rel`, che e' cio' che si puo' fare, e la conseguenza si
# **misura** invece di essere sperata: `FEATURE_SENZA_IRRIDUCIBILI` rifa' tutto
# senza di loro, e se la conclusione non cambia non dipende da questa scelta.
# E' lo stesso disegno con cui la coda di E2 ha provato entrambe le forme del
# cartellino.
# --------------------------------------------------------------------------

#: Regolarizzazione della ridge. DICHIARATA, mai cercata: un test vieta in questo
#: modulo le funzioni con cui una soglia si ricava dal campione.
ALPHA = 10.0

#: Le candidate irriducibili secondo `deriva_e4`, nella forma con cui entrano nel
#: disegno: `_rel` per la standardizzazione di E1, `_prec` perche' vengono da t-1.
#: **I due suffissi dicono due cose diverse** e vanno letti insieme.
IRRIDUCIBILI = ("npxg_per_90_rel_prec", "rigori_per_90_rel_prec",
                "punizioni_dirette_per_90_rel_prec", "corner_per_90_rel_prec",
                "quota_tocchi_area_rel_prec")

#: E4.1 — il voto base. Il **ruolo** entra come indicatrici e non come numero:
#: e' la stessa disciplina di `distinta.py`, e qui conterebbe sbagliarla perche'
#: il voto base e' quasi una costante di ruolo. `ruolo` e la forza di squadra
#: **non** portano `_prec`: sono contesto di t, noto all'asta (vedi
#: `con_contesto`), e un test verifica che tutto il resto lo porti.
FEATURE_VOTO = ("ruolo", "npxg_per_90_rel_prec", "xa_per_90_rel_prec",
                "passaggi_chiave_per_90_rel_prec", "falli_per_90_rel_prec",
                "quota_tocchi_area_rel_prec",
                "gol_fatti_atteso", "gol_subiti_atteso")

#: E4.2 + E4.3 + E4.4 — i bonus per presenza.
FEATURE_BONUS = ("ruolo", "npxg_per_90_rel_prec", "xa_per_90_rel_prec",
                 "gol_per_90_rel_prec", "passaggi_chiave_per_90_rel_prec",
                 "rigori_per_90_rel_prec", "punizioni_dirette_per_90_rel_prec",
                 "corner_per_90_rel_prec", "ammonizioni_per_90_rel_prec",
                 "gol_fatti_atteso", "gol_subiti_atteso")

#: Il contesto di t, ammesso perche' noto prima dell'asta. E' l'elenco su cui il
#: test del leakage fa l'eccezione, cosi' che l'eccezione sia enumerata invece
#: che dedotta dal nome.
COLONNE_DI_T_AMMESSE = ("ruolo", "gol_fatti_atteso", "gol_subiti_atteso",
                        "rigori_atteso", "qi_asta", "qi_pct_ruolo_asta",
                        "senza_listone")

FEATURE_VOTO_SENZA_IRRIDUCIBILI = tuple(
    c for c in FEATURE_VOTO if c not in IRRIDUCIBILI)
FEATURE_BONUS_SENZA_IRRIDUCIBILI = tuple(
    c for c in FEATURE_BONUS if c not in IRRIDUCIBILI)

#: E4.5 — QI. **Solo `qi_classic`**, e la guardia e' l'elenco di E2, non il
#: suffisso: il FVM resta squalificato per l'intera Fase 9.
COLONNE_LISTONE_AMMESSE = ("qi_classic",)


def tabella_e4(stagioni=STAGIONI) -> pd.DataFrame:
    """Per ogni `(stagione bersaglio, giocatore_id)`, le feature di **t-1**.

    Lo sfasamento e' costruito qui, in un punto solo, e ogni colonna predittiva
    porta il suffisso `_prec`: un test lo pretende, come per `impiego`.
    """
    g, rif = standardizza_e4(per_giocatore(stagioni))
    stagioni = sorted(g["stagione"].unique())
    pos = {s: i for i, s in enumerate(stagioni)}

    colonne = ([n for n, _, _ in CANDIDATE_E4]
               + [f"{n}_rel" for n, _, _ in CANDIDATE_E4]
               + ["minuti", "presenze", "npxg", "xa", "rigori_battuti",
                  "rigori_segnati", "rigori_sbagliati", "teamId"])
    prec = g[["stagione", "giocatore_id", "role"] + colonne].copy()
    prec["stagione_succ"] = [stagioni[pos[s] + 1] if pos[s] + 1 < len(stagioni)
                             else None for s in prec["stagione"]]
    prec = prec.dropna(subset=["stagione_succ"])
    prec = prec.rename(columns={c: f"{c}_prec" for c in colonne + ["role"]})
    prec = prec.drop(columns=["stagione"]).rename(
        columns={"stagione_succ": "stagione"})
    prec.attrs["riferimenti"] = rif
    return prec.reset_index(drop=True)


def _disegno(d: pd.DataFrame, feature) -> np.ndarray:
    """Matrice del disegno: le categoriche diventano indicatrici, mai ordinali."""
    pezzi = []
    for f in feature:
        if not pd.api.types.is_numeric_dtype(d[f]):
            ind = pd.get_dummies(d[f], prefix=f, drop_first=True).astype(float)
            pezzi.append(ind.to_numpy())
        else:
            pezzi.append(d[[f]].astype(float).fillna(0.0).to_numpy())
    return np.hstack(pezzi)


def previsione(stagione: str, tab: pd.DataFrame, oss: pd.DataFrame,
               bersaglio: str, feature, alpha: float = ALPHA,
               min_presenze: int = MIN_PRESENZE_ADDESTRAMENTO) -> pd.Series:
    """Ridge sul solo passato, per una stagione bersaglio.

    `min_presenze` filtra le righe di **addestramento** sull'esposizione di t-1,
    che e' un predittore e non il bersaglio: filtrare sull'esposizione di t
    sarebbe condizionare sul futuro. La valutazione non si filtra mai.
    """
    storia = tab[tab["stagione"] < stagione]
    storia = storia[storia["presenze_prec"].fillna(0) >= min_presenze]
    storia = storia.merge(oss, on=["stagione", "giocatore_id"], how="inner")
    storia = storia[storia[bersaglio].notna()]
    if len(storia) < 50:
        return pd.Series(np.nan, index=tab.index[tab["stagione"] == stagione])

    ora = tab[tab["stagione"] == stagione]
    tutte = pd.concat([storia[list(feature)], ora[list(feature)]],
                      ignore_index=True)
    X_all = _disegno(tutte, feature)
    n_st = len(storia)
    X, Xn = X_all[:n_st], X_all[n_st:]
    y = storia[bersaglio].to_numpy(dtype=float)

    mu, sd = X.mean(0), X.std(0)
    sd[sd == 0] = 1.0
    Xs, Xns = (X - mu) / sd, (Xn - mu) / sd
    A = Xs.T @ Xs + alpha * np.eye(Xs.shape[1])
    beta = np.linalg.solve(A, Xs.T @ (y - y.mean()))
    return pd.Series(y.mean() + Xns @ beta, index=ora.index)


def con_contesto(tab: pd.DataFrame = None, quote: pd.DataFrame = None
                 ) -> pd.DataFrame:
    """Aggiunge alla tabella dei predittori la squadra di t, la sua forza e QI.

    **La squadra viene dal LISTONE, non dai voti**, ed e' una differenza di
    orologio e non di comodita': il listone e' pubblicato prima dell'asta, quindi
    dice il club che si conosce *al momento della decisione*; la squadra dei voti
    e' quella per cui ha poi giocato. E' la stessa scelta dichiarata che E3 ha
    fatto per il club del portiere — all'asta il club lo si sa davvero — presa
    pero' dalla fonte che ha il diritto di dirlo.

    **La forza di squadra e' stimata dal solo passato** (`forza_squadra`), quindi
    non porta dentro niente della stagione bersaglio se non l'identita' del club.
    Una neopromossa non ha passato e resta `nan`: la Serie B non e' nel
    repository, e riempirla con la media delle retrocesse sarebbe
    un'informazione diversa da quella che serve (Fase 6E l'ha gia' misurata e non
    e' neutra).

    QI entra qui perche' e' contesto di t come la squadra, ed **e' lecito per la
    stessa ragione**: il listone esce prima dell'asta. La guardia e'
    `COLONNE_LISTONE_AMMESSE`, non il suffisso.
    """
    from . import difesa as DF, quotazioni as Q

    for c in COLONNE_LISTONE_AMMESSE:
        if c in Q.COLONNE_CONTAMINATE:
            raise ValueError(f"{c} e' una colonna contaminata: vedi Q.orologio()")

    tab = tabella_e4() if tab is None else tab
    quote = Q.carica() if quote is None else quote

    listone = quote[["stagione", "giocatore_id", "squadra_id", "ruolo_classic",
                     "qi_classic"]].copy()
    listone = listone.rename(columns={"ruolo_classic": "ruolo"})
    listone["qi_asta"] = listone["qi_classic"].astype("Float64").astype(float)
    listone["qi_pct_ruolo_asta"] = (
        listone.groupby(["stagione", "ruolo"])["qi_asta"].rank(pct=True))
    listone = listone.drop(columns=["qi_classic"])

    n = len(tab)
    out = tab.merge(listone, on=["stagione", "giocatore_id"], how="left")
    assert len(out) == n, "il join del listone ha moltiplicato le righe"

    ponte = DF._ponte_squadre()
    out = out.merge(ponte.rename(columns={"squadra_id_fc": "squadra_id"}),
                    on=["stagione", "squadra_id"], how="left")
    assert len(out) == n, "il join delle squadre ha moltiplicato le righe"

    out = out.merge(forza_squadra().rename(columns={"teamId": "teamId_ws"}),
                    on=["stagione", "teamId_ws"], how="left")
    assert len(out) == n, "il join della forza di squadra ha moltiplicato le righe"

    # Chi non e' nel listone non ha ruolo di lega: si usa quello posizionale di
    # WhoScored di t-1. Sono due grandezze diverse (vincolo 7) e la sostituzione
    # e' dichiarata, non silenziosa.
    out["ruolo"] = out["ruolo"].fillna(out["role_prec"])
    out["senza_listone"] = out["qi_asta"].isna().astype(float)
    return out


def _bersagli(per_stagione: pd.DataFrame = None) -> pd.DataFrame:
    """Voto medio e bonus per presenza osservati, per `(stagione, giocatore_id)`.

    Sono le due componenti che il modello d'asta stima separatamente, prese dal
    **fantavoto di lega** e non da quello della fonte: la differenza e' il +1 di
    porta inviolata, gia' misurata su 1.092 righe.
    """
    from . import fantapunti as FP
    ps = FP.per_giocatore_stagione() if per_stagione is None else per_stagione
    d = ps[["stagione", "giocatore_id", "presenze", "voto_medio",
            "bonus_totale", "autoreti"]].copy()
    d["bonus_per_presenza"] = (d["bonus_totale"]
                               / d["presenze"].replace(0, np.nan))
    return d


# --------------------------------------------------------------------------
# LA VALUTAZIONE, E PERCHE' QUI GLI ORACOLI SONO DUE
#
# `modello_asta.scomposizione_errore` costruisce "bonus noti" tenendo il
# `voto_atteso` del modello: **il voto base non e' dentro quel divario**. La
# specifica di E4 chiede la quota del divario dei bonus (61,4 -> 52,5 = 8,9
# punti), ma E4.1 lavora su una grandezza che quel divario non contiene, e
# misurarlo contro il pavimento sbagliato lo farebbe sembrare irrilevante per
# costruzione.
#
# Qui gli oracoli sono percio' **due**, uno per componente, e ciascuna variante
# si legge contro il proprio.
#
# IL CAMPIONE E' FISSO, E IL PERCHE' VA DETTO
# --------------------------------------------
# Un giocatore che non ha mai giocato in t non ha un voto medio osservato ne' un
# bonus per presenza osservato: il suo oracolo e' indefinito. `scomposizione_errore`
# lascia cadere quelle righe, quindi le sue tre varianti girano su campioni
# diversi. Qui l'oracolo per quelle righe vale **zero punti osservati con zero
# presenze attese osservate**, cioe' il termine si annulla comunque nel prodotto:
# si imputa il valore neutro e si tiene il campione fisso, perche' varianti su
# campioni diversi non sono confrontabili. Entrambe le letture sono riportate.
# --------------------------------------------------------------------------

def valutazione(feature_voto=FEATURE_VOTO, feature_bonus=FEATURE_BONUS,
                alpha: float = ALPHA,
                min_presenze: int = MIN_PRESENZE_ADDESTRAMENTO,
                tab: pd.DataFrame = None) -> dict:
    """Le varianti di E4 sulle stesse quattro transizioni del modello d'asta.

    Riporta il MAE sui punti e la quota chiusa del **proprio** divario oracolo:
    quello del voto per le varianti sul voto, quello dei bonus per le altre.
    """
    from . import fantapunti as FP, modello_asta as MA

    ps = FP.per_giocatore_stagione()
    oss = _bersagli(ps)
    tab = con_contesto() if tab is None else tab
    wf = MA.walkforward(per_stagione=ps)

    d = wf.copy()
    chiave = list(zip(d["stagione_prevista"], d["giocatore_id"]))

    def _mappa(bersaglio, feature):
        pezzi = []
        for st in MA.STAGIONI_VALUTABILI:
            p = previsione(st, tab, oss, bersaglio, feature, alpha, min_presenze)
            pezzi.append(tab.loc[p.index, ["stagione", "giocatore_id"]]
                         .assign(pred=p))
        k = (pd.concat(pezzi, ignore_index=True)
             .set_index(["stagione", "giocatore_id"])["pred"])
        return pd.Series([k.get(c, np.nan) for c in chiave], index=d.index)

    # Chi non ha riga di predittori non ha giocato in t-1: la sua componente
    # resta quella del modello d'asta. Sostituire solo dove la feature esiste, e
    # dichiararlo, e' l'unico modo di non cambiare campione fra le varianti.
    voto_e4 = _mappa("voto_medio", feature_voto).fillna(d["voto_atteso"])
    bonus_e4 = _mappa("bonus_per_presenza", feature_bonus).fillna(
        d["bonus_per_presenza_atteso"])
    d["voto_e4"], d["bonus_e4"] = voto_e4, bonus_e4

    # I due oracoli, a campione fisso.
    o = oss.set_index(["stagione", "giocatore_id"])
    voto_oss = pd.Series([o["voto_medio"].get(c, np.nan) for c in chiave],
                         index=d.index).fillna(d["voto_atteso"])
    bonus_oss = pd.Series([o["bonus_per_presenza"].get(c, np.nan)
                           for c in chiave],
                          index=d.index).fillna(d["bonus_per_presenza_atteso"])

    pres, v, b = d["presenze_attese"], d["voto_atteso"], d["bonus_per_presenza_atteso"]
    varianti = {
        "modello d'asta (riferimento)": (pres * (v + b), "-"),
        "E4 voto base": (pres * (voto_e4 + b), "voto"),
        "E4 bonus": (pres * (v + bonus_e4), "bonus"),
        "E4 voto + bonus": (pres * (voto_e4 + bonus_e4), "entrambi"),
        "ORACOLO voto noto": (pres * (voto_oss + b), "voto"),
        "ORACOLO bonus noti": (pres * (v + bonus_oss), "bonus"),
    }

    y = d["punti_osservati"]
    mae = {n: float((x - y).abs().mean()) for n, (x, _) in varianti.items()}
    rif = mae["modello d'asta (riferimento)"]
    divari = {"voto": rif - mae["ORACOLO voto noto"],
              "bonus": rif - mae["ORACOLO bonus noti"]}
    divari["entrambi"] = divari["voto"] + divari["bonus"]

    righe = []
    for nome, (x, comp) in varianti.items():
        quota = (100 * (rif - mae[nome]) / divari[comp]
                 if comp != "-" and divari[comp] > 0 else np.nan)
        righe.append({"variante": nome, "componente": comp, "righe": int(len(x)),
                      "mae_punti": mae[nome], "divario_chiuso_pct": quota})
    return {"tabella": pd.DataFrame(righe), "dettaglio": d, "divari": divari}


def potenza_mde(d: pd.DataFrame, colonna_a: str, colonna_b: str,
                divario: float) -> dict:
    """MDE sulla differenza appaiata di MAE dei punti, a potenza 80%.

    Appaiata perche' le due varianti girano sulle **stesse righe**: la varianza
    della differenza e' molto minore di quella dei due MAE separati. E' la stessa
    funzione di `impiego.potenza_mde`, col divario passato invece che fissato,
    perche' qui i divari sono due.
    """
    a = (d[colonna_a] - d["punti_osservati"]).abs()
    b = (d[colonna_b] - d["punti_osservati"]).abs()
    diff = (a - b).dropna()
    n = len(diff)
    se = float(diff.std(ddof=1) / np.sqrt(n)) if n > 1 else float("nan")
    mde = (1.959964 + 0.841621) * se
    return {"righe": n, "delta_mae": float(diff.mean()), "se": se,
            "t": float(diff.mean() / se) if se else float("nan"),
            "mde_mae": mde,
            "mde_quota_divario_pct": 100 * mde / divario if divario else np.nan}


# --------------------------------------------------------------------------
# E4.3 — i rigori come assegnazione discreta
#
# Un rigorista vale +3 per rigore segnato e -3 per uno sbagliato: poca massa,
# alta leva, e il valore **dipende da un'assegnazione discreta** che nessun tasso
# per 90 descrive. Il modello e' esplicito:
#
#     rigori attesi del giocatore = rigori attesi della SQUADRA
#                                 x P(e' lui il designato)
#                                 x [nessun terzo fattore: il tasso di
#                                    realizzazione entra dopo, sui punti]
#
# LA QUOTA DEL DESIGNATO NON E' UNO, ED E' UN FATTO MISURATO
# -----------------------------------------------------------
# `concentrazione_rigoristi` dice che il battitore principale mediano prende il
# **57,7%** dei rigori della sua squadra, i primi due l'83,3%. Un modello che
# desse tutti i rigori al primo sbaglierebbe di quasi la meta'.
# --------------------------------------------------------------------------

#: Tasso di realizzazione di lega, misurato: 76,4-78,3% nelle cinque stagioni.
#: Lo shrinkage e' **quasi totale** e la ragione e' la massa: un rigorista batte
#: 5-6 rigori in stagione, quindi la sua conversione osservata ha un errore
#: standard di ~0,18 — piu' grande di qualunque differenza vera fra rigoristi.
#: Stimare una conversione individuale sarebbe stimare rumore.
SMORZAMENTO_CONVERSIONE = 50.0


def rigoristi(tab: pd.DataFrame = None) -> pd.DataFrame:
    """P(e' lui il designato) e conversione attesa, dal solo passato.

    La quota si calcola sui rigori della **squadra in t-1**, che e' il solo
    passato disponibile, e resta agganciata al giocatore anche se cambia club:
    e' una proprieta' del giocatore (lo battono i rigoristi), non della maglia.
    Il limite e' dichiarato — chi arriva in un club che ha gia' un rigorista non
    battera' — ed e' esattamente cio' che il parametro manuale serve a correggere.
    """
    tab = tabella_e4() if tab is None else tab
    d = tab.copy()
    # Rigori della sua squadra di t-1, dallo stesso strato feature.
    per_squadra = (d.groupby(["stagione", "teamId_prec"])["rigori_battuti_prec"]
                   .sum().rename("rigori_squadra_prec"))
    d = d.merge(per_squadra, on=["stagione", "teamId_prec"], how="left")
    d["quota_rigorista_prec"] = (d["rigori_battuti_prec"]
                                 / d["rigori_squadra_prec"].replace(0, np.nan))
    d["quota_rigorista_prec"] = d["quota_rigorista_prec"].fillna(0.0)

    seg, sba = d["rigori_segnati_prec"], d["rigori_sbagliati_prec"]
    tot = seg + sba
    media = float(seg.sum() / tot.sum()) if tot.sum() else np.nan
    d["conversione_attesa"] = ((seg + SMORZAMENTO_CONVERSIONE * media)
                               / (tot + SMORZAMENTO_CONVERSIONE))
    return d


def punti_rigori(tab: pd.DataFrame = None, designato: dict = None) -> pd.Series:
    """Punti attesi dai rigori, per riga di `tabella_e4`.

    `designato` permette di **imporre a mano** il rigorista di una squadra:
    `{(stagione, teamId): giocatore_id}`. E' un input, non una stima, ed e' il
    punto della specifica: per il 2026-27 il designato lo si sa dai giornali e
    non dai dati, e la sensibilita' a quel singolo switch va mostrata.
    """
    from . import lega as L

    d = rigoristi(tab)
    quota = d["quota_rigorista_prec"].copy()
    if designato:
        for (st, team), gid in designato.items():
            sel = (d["stagione"] == st) & (d["teamId_prec"] == team)
            quota = quota.where(~sel, 0.0)
            quota = quota.where(~(sel & (d["giocatore_id"] == gid)), 1.0)

    # `rigori_atteso` e' per **partita**: il totale di stagione sono 38 giornate,
    # che e' la stessa costante con cui `modello_asta` converte le presenze.
    from . import modello_asta as MA
    attesi = d["rigori_atteso"].fillna(0.0) * MA.GIORNATE * quota
    c = d["conversione_attesa"]
    valore = L.BONUS["rigori_segnati"] * c + L.BONUS["rigori_sbagliati"] * (1 - c)
    return pd.Series(attesi.to_numpy() * valore.to_numpy(), index=d.index)


def sensibilita_designato(tab: pd.DataFrame = None, n: int = 5) -> pd.DataFrame:
    """Quanto sposta il totale di stagione cambiare UN rigorista.

    Si prende ogni squadra e si sposta il rigorista dal primo al secondo: la
    differenza in punti e' cio' che quel singolo interruttore vale. E' la
    sensibilita' che la specifica chiede, e non e' un'astrazione — e' la
    decisione che all'asta si prende sul serio.
    """
    d = rigoristi(tab)
    base = punti_rigori(tab)
    d = d.assign(_punti=base.to_numpy())

    righe = []
    for (st, team), sub in d.groupby(["stagione", "teamId_prec"]):
        ordine = sub.sort_values("quota_rigorista_prec", ascending=False)
        if len(ordine) < 2 or ordine["quota_rigorista_prec"].iloc[0] <= 0:
            continue
        primo, secondo = ordine.iloc[0], ordine.iloc[1]
        forzato = punti_rigori(tab, {(st, team): secondo["giocatore_id"]})
        righe.append({
            "stagione": st, "teamId": team,
            "primo": primo["giocatore_id"], "quota_primo": primo["quota_rigorista_prec"],
            "punti_primo_naturale": float(primo["_punti"]),
            "punti_secondo_se_designato": float(forzato.loc[secondo.name]),
            "spostamento": float(forzato.loc[secondo.name] - secondo["_punti"]),
        })
    out = pd.DataFrame(righe)
    return out.nlargest(n, "spostamento") if len(out) else out


# --------------------------------------------------------------------------
# E4.4 — gli autogol: c'e' un effetto individuale?
# --------------------------------------------------------------------------

def autogol_effetto_individuale(tab: pd.DataFrame = None) -> pd.DataFrame:
    """Tasso base per ruolo contro tasso base + effetto individuale, fuori campione.

    La specifica dice "nessun effetto individuale, e il test lo verifica": qui il
    test c'e', e la forma e' quella dichiarata — due modelli sulle stesse righe,
    stimati sul solo passato, confrontati sull'errore fuori campione. Se il
    modello con l'effetto individuale non batte quello senza, resta quello senza.

    Il bersaglio sono gli **autogol** della stagione `t`; il predittore in piu'
    sono gli autogol di `t-1`. Un autogol vale -2 (`lega.BONUS`), e sono rari:
    e' il caso in cui l'assenza di segnale e' l'ipotesi di partenza e va
    falsificata, non assunta.
    """
    from . import fantapunti as FP, modello_asta as MA

    tab = con_contesto() if tab is None else tab
    ps = FP.per_giocatore_stagione()
    oss = _bersagli(ps)
    d = tab.merge(oss[["stagione", "giocatore_id", "autoreti"]],
                  on=["stagione", "giocatore_id"], how="left")

    prec = oss[["stagione", "giocatore_id", "autoreti"]].copy()
    stagioni = sorted(oss["stagione"].unique())
    pos = {s: i for i, s in enumerate(stagioni)}
    prec["stagione"] = [stagioni[pos[s] + 1] if pos[s] + 1 < len(stagioni) else None
                        for s in prec["stagione"]]
    prec = prec.dropna(subset=["stagione"]).rename(
        columns={"autoreti": "autoreti_prec"})
    d = d.merge(prec, on=["stagione", "giocatore_id"], how="left")
    d["autoreti_prec"] = d["autoreti_prec"].fillna(0.0)

    righe = []
    for nome, feature in (("solo tasso di ruolo", ("ruolo",)),
                          ("ruolo + effetto individuale",
                           ("ruolo", "autoreti_prec"))):
        errori = []
        for st in MA.STAGIONI_VALUTABILI:
            storia = d[(d["stagione"] < st) & d["autoreti"].notna()]
            ora = d[(d["stagione"] == st) & d["autoreti"].notna()]
            if len(storia) < 50 or ora.empty:
                continue
            tutte = pd.concat([storia[list(feature)], ora[list(feature)]],
                              ignore_index=True)
            X = _disegno(tutte, feature)
            Xs, Xn = X[:len(storia)], X[len(storia):]
            y = storia["autoreti"].to_numpy(dtype=float)
            mu, sd = Xs.mean(0), Xs.std(0)
            sd[sd == 0] = 1.0
            Z = (Xs - mu) / sd
            A = Z.T @ Z + ALPHA * np.eye(X.shape[1])
            beta = np.linalg.solve(A, Z.T @ (y - y.mean()))
            pred = y.mean() + ((Xn - mu) / sd) @ beta
            errori.append(np.abs(pred - ora["autoreti"].to_numpy(dtype=float)))
        e = np.concatenate(errori)
        righe.append({"modello": nome, "righe": len(e),
                      "mae_autogol": float(e.mean())})
    out = pd.DataFrame(righe)
    out["guadagno"] = out["mae_autogol"].iloc[0] - out["mae_autogol"]
    return out


# --------------------------------------------------------------------------
# E4.5 — QI, con lo stesso protocollo di (b) e senza ereditarne l'esito
#
# Il risultato positivo di (b) — QI chiude l'1,49% del divario delle presenze —
# **non e' licenza**. Li' il bersaglio erano le presenze e l'ipotesi era che il
# prezzo dicesse la gerarchia di rosa; qui il bersaglio e' il rendimento per
# presenza, che e' un'altra cosa. Si misura di nuovo, da zero, sullo stesso
# standard: potenza dichiarata prima, forma scelta come ipotesi, ridondanza
# misurata.
# --------------------------------------------------------------------------

FEATURE_VOTO_QI = FEATURE_VOTO + ("qi_pct_ruolo_asta",)
FEATURE_BONUS_QI = FEATURE_BONUS + ("qi_pct_ruolo_asta",)


def ridondanza_qi(tab: pd.DataFrame = None) -> pd.DataFrame:
    """Quanto di QI e' gia' spiegato dalle feature di produzione di E4.

    E' la misura che distingue "e' gia' nel set" da "non c'e' segnale", ed e' la
    lezione delle due code di E2: senza, un risultato nullo resta ambiguo.
    """
    tab = con_contesto() if tab is None else tab
    reg = ["npxg_per_90_rel_prec", "xa_per_90_rel_prec",
           "passaggi_chiave_per_90_rel_prec", "gol_per_90_rel_prec"]
    righe = []
    for col in ("qi_asta", "qi_pct_ruolo_asta"):
        d = tab.dropna(subset=[col] + reg)
        X = np.column_stack([np.ones(len(d))]
                            + [d[c].astype(float).to_numpy() for c in reg])
        y = d[col].to_numpy(dtype=float)
        b, *_ = np.linalg.lstsq(X, y, rcond=None)
        r2 = 1 - float(((y - X @ b) ** 2).sum() / ((y - y.mean()) ** 2).sum())
        righe.append({"colonna": col, "righe": len(d),
                      "r2_sulle_feature_e4": r2,
                      "lettura": "gia' nel set" if r2 > 0.25
                                 else "informazione nuova"})
    return pd.DataFrame(righe)


def deriva_qi(tab: pd.DataFrame = None) -> pd.DataFrame:
    """Il gate di E1 sulle due forme di QI. Rifatto qui, non ereditato da (b)."""
    tab = con_contesto() if tab is None else tab
    righe = []
    for col in ("qi_asta", "qi_pct_ruolo_asta"):
        m = tab.groupby("stagione")[col].mean().dropna()
        deriva = (float((m.max() - m.min()) / abs(m.max())) if len(m) > 1
                  else float("nan"))
        righe.append({"colonna": col, "stagioni": len(m), "deriva": deriva,
                      "passa": bool(deriva < FG.SOGLIA_DERIVA)})
    return pd.DataFrame(righe)


# --------------------------------------------------------------------------
# Il confronto completo, con potenza e MDE
# --------------------------------------------------------------------------

VARIANTI = {
    "E4 voto base": ("voto", FEATURE_VOTO, None),
    "E4 bonus": ("bonus", None, FEATURE_BONUS),
    "E4 voto + bonus": ("entrambi", FEATURE_VOTO, FEATURE_BONUS),
    "E4 senza le irriducibili": ("entrambi", FEATURE_VOTO_SENZA_IRRIDUCIBILI,
                                 FEATURE_BONUS_SENZA_IRRIDUCIBILI),
    "E4 + QI": ("entrambi", FEATURE_VOTO_QI, FEATURE_BONUS_QI),
    "SOLO QI, senza le feature evento": ("entrambi",
                                         ("ruolo", "qi_pct_ruolo_asta"),
                                         ("ruolo", "qi_pct_ruolo_asta")),
}


def confronto(alpha: float = ALPHA,
              min_presenze: int = MIN_PRESENZE_ADDESTRAMENTO,
              varianti: dict = None, tab: pd.DataFrame = None) -> dict:
    """Tutte le varianti di E4 con MAE, quota del divario e MDE appaiato.

    Il riferimento e' sempre il **modello d'asta**, e i divari sono quelli
    corretti da questo blocco, ricalcolati qui sul campione **fisso** di 2.678
    righe invece che sulle 2.204 su cui il numero pubblicato era stato letto.
    """
    from . import fantapunti as FP, modello_asta as MA

    ps = FP.per_giocatore_stagione()
    oss = _bersagli(ps)
    tab = con_contesto() if tab is None else tab
    wf = MA.walkforward(per_stagione=ps)
    varianti = VARIANTI if varianti is None else varianti

    d = wf.copy()
    chiave = list(zip(d["stagione_prevista"], d["giocatore_id"]))

    def _mappa(bersaglio, feature):
        pezzi = []
        for st in MA.STAGIONI_VALUTABILI:
            p = previsione(st, tab, oss, bersaglio, feature, alpha, min_presenze)
            pezzi.append(tab.loc[p.index, ["stagione", "giocatore_id"]]
                         .assign(pred=p))
        k = (pd.concat(pezzi, ignore_index=True)
             .set_index(["stagione", "giocatore_id"])["pred"])
        return pd.Series([k.get(c, np.nan) for c in chiave], index=d.index)

    o = oss.set_index(["stagione", "giocatore_id"])
    voto_oss = pd.Series([o["voto_medio"].get(c, np.nan) for c in chiave],
                         index=d.index).fillna(d["voto_atteso"])
    bonus_oss = pd.Series([o["bonus_per_presenza"].get(c, np.nan)
                           for c in chiave],
                          index=d.index).fillna(d["bonus_per_presenza_atteso"])

    pres = d["presenze_attese"]
    v, b = d["voto_atteso"], d["bonus_per_presenza_atteso"]
    y = d["punti_osservati"]
    d["punti_riferimento"] = pres * (v + b)
    rif = float((d["punti_riferimento"] - y).abs().mean())

    oracoli = {"voto": pres * (voto_oss + b),
               "bonus": pres * (v + bonus_oss),
               "entrambi": pres * (voto_oss + bonus_oss)}
    divari = {k: rif - float((x - y).abs().mean()) for k, x in oracoli.items()}

    righe, mde = [], []
    for nome, (comp, f_voto, f_bonus) in varianti.items():
        vv = _mappa("voto_medio", f_voto).fillna(v) if f_voto else v
        bb = _mappa("bonus_per_presenza", f_bonus).fillna(b) if f_bonus else b
        d[f"punti_{nome}"] = pres * (vv + bb)
        mae = float((d[f"punti_{nome}"] - y).abs().mean())
        righe.append({"variante": nome, "componente": comp, "righe": len(d),
                      "mae_punti": mae,
                      "divario_chiuso_pct": (100 * (rif - mae) / divari[comp]
                                             if divari[comp] > 0 else np.nan)})
        mde.append({"variante": nome,
                    **potenza_mde(d, "punti_riferimento", f"punti_{nome}",
                                  divari[comp])})

    testa = pd.DataFrame([{"variante": "modello d'asta (riferimento)",
                           "componente": "-", "righe": len(d),
                           "mae_punti": rif, "divario_chiuso_pct": 0.0}])
    coda = pd.DataFrame([
        {"variante": f"ORACOLO {k} noto", "componente": k, "righe": len(d),
         "mae_punti": float((x - y).abs().mean()), "divario_chiuso_pct": 100.0}
        for k, x in oracoli.items()])
    return {"tabella": pd.concat([testa, pd.DataFrame(righe), coda],
                                 ignore_index=True),
            "mde": pd.DataFrame(mde), "divari": divari, "dettaglio": d}


def per_ruolo(d: pd.DataFrame, colonna: str) -> pd.DataFrame:
    """L'errore separato per ruolo.

    Un rigorista sbagliato e un difensore mediocre pesano diversamente, e
    mediarli li nasconde entrambi.
    """
    x = d.copy()
    x["err_base"] = (x["punti_riferimento"] - x["punti_osservati"]).abs()
    x["err_nuovo"] = (x[colonna] - x["punti_osservati"]).abs()
    righe = []
    for r, sub in x.groupby("ruolo"):
        righe.append({"ruolo": r, "righe": len(sub),
                      "mae_base": float(sub["err_base"].mean()),
                      "mae_nuovo": float(sub["err_nuovo"].mean()),
                      "delta": float((sub["err_base"]
                                      - sub["err_nuovo"]).mean())})
    return pd.DataFrame(righe)


def sensibilita_pavimento(pavimenti=PAVIMENTI_ACCANTO) -> pd.DataFrame:
    """Lo stesso risultato ai quattro pavimenti di addestramento.

    `MIN_PRESENZE_ADDESTRAMENTO` e' dichiarato e non stimato, quindi va mostrato
    quanto il risultato gli deve — e' la stessa cosa che E1 fa col pavimento dei
    minuti e E2 col pavimento di esposizione.
    """
    righe = []
    for p in pavimenti:
        t = confronto(min_presenze=p)["tabella"]
        for _, r in t.iterrows():
            if r["variante"].startswith(("modello", "ORACOLO")):
                continue
            righe.append({"min_presenze": p, "variante": r["variante"],
                          "mae_punti": r["mae_punti"],
                          "divario_chiuso_pct": r["divario_chiuso_pct"]})
    return pd.DataFrame(righe)


# --------------------------------------------------------------------------
# E4.1 — quanto del voto base e' spiegabile, e quanto e' prevedibile
#
# Sono due domande diverse e il blocco le tiene separate, perche' confonderle e'
# il modo piu' facile di far sembrare utile un modello che non lo e'.
#
# * **spiegabile** e' in campione: quanta varianza del voto si lascia descrivere
#   da ruolo, feature evento e forza di squadra guardando *quelle stesse* righe.
#   E' un limite superiore, come il test in campione della Fase 6D;
# * **prevedibile** e' `confronto`: quanta ne resta fuori campione, con le
#   feature di t-1 e la stagione bersaglio mai vista.
#
# IL RISULTATO DI PARTENZA NON E' UN PREDITTORE, ED E' IL PUNTO
# --------------------------------------------------------------
# La specifica chiede il **risultato di partita** fra i regressori, ed e' giusto
# per la domanda "spiegabile": il voto di un difensore dipende molto da come e'
# finita. Ma il risultato di una partita di `t` **non e' noto all'asta**, quindi
# non puo' entrare in un modello che prevede `t`. Entra qui, dove misura il
# limite superiore, e non entra in `FEATURE_VOTO`. La forza di squadra e' il modo
# in cui quella stessa informazione entra legittimamente: e' cio' che del
# risultato si sa prima.
# --------------------------------------------------------------------------

def spiegazione_voto(stagioni=STAGIONI) -> pd.DataFrame:
    """Varianza del voto spiegata da modelli annidati, IN CAMPIONE.

    Ogni riga aggiunge un blocco di regressori al precedente, sulle stesse righe.
    L'ultima riga e' il **risultato di partita**, che non e' un predittore
    (vedi il commento sopra) e sta qui apposta per dire quanto si lascia sul
    tavolo chi non lo puo' avere.
    """
    from . import difesa as DF, voti as V

    v = V.carica()
    v = v[(~v["allenatore"]) & v["voto_redazione"].notna()].copy()
    v = v[v["stagione"].isin(stagioni)]

    gsp = DF.gol_squadra_partita()
    # Il risultato dalla parte della SUA squadra: differenza reti e esito.
    ris = gsp[["stagione", "matchId", "teamId", "gol_fatti", "gol_subiti"]].copy()
    ris["differenza_reti"] = ris["gol_fatti"] - ris["gol_subiti"]

    ponte = DF._ponte_squadre().rename(columns={"squadra_id_fc": "squadra_id"})
    v = v.merge(ponte, on=["stagione", "squadra_id"], how="left")

    # La partita si aggancia per (stagione, teamId, giornata) via l'aggancio di
    # E0; qui basta la media di squadra-stagione del risultato, perche' la
    # domanda e' quanta varianza il risultato spiega e non quale partita fosse.
    per_partita = v.merge(
        ris.rename(columns={"teamId": "teamId_ws"}),
        on=["stagione", "teamId_ws"], how="left", suffixes=("", "_r"))

    # Aggregazione a (stagione, giocatore_id): il bersaglio del modello d'asta.
    g = (v.groupby(["stagione", "giocatore_id"])
         .agg(voto_medio=("voto_redazione", "mean"),
              presenze=("voto_redazione", "size"),
              ruolo=("ruolo", "first"),
              teamId_ws=("teamId_ws", "last")).reset_index())
    g = g[g["presenze"] >= MIN_PRESENZE_ADDESTRAMENTO]

    forza = (gsp.groupby(["stagione", "teamId"])[["gol_fatti", "gol_subiti"]]
             .mean().reset_index().rename(columns={"teamId": "teamId_ws"}))
    g = g.merge(forza, on=["stagione", "teamId_ws"], how="left")

    feat = standardizza_e4(per_giocatore(stagioni))[0]
    g = g.merge(feat[["stagione", "giocatore_id", "npxg_per_90_rel",
                      "xa_per_90_rel", "passaggi_chiave_per_90_rel",
                      "falli_per_90_rel", "quota_tocchi_area_rel"]],
                on=["stagione", "giocatore_id"], how="left")
    g = g.dropna(subset=["gol_fatti", "npxg_per_90_rel"])

    blocchi = [
        ("intercetta (media di campionato)", []),
        ("+ ruolo", ["ruolo"]),
        ("+ feature evento", ["ruolo", "npxg_per_90_rel", "xa_per_90_rel",
                              "passaggi_chiave_per_90_rel", "falli_per_90_rel",
                              "quota_tocchi_area_rel"]),
        ("+ forza di squadra", ["ruolo", "npxg_per_90_rel", "xa_per_90_rel",
                                "passaggi_chiave_per_90_rel", "falli_per_90_rel",
                                "quota_tocchi_area_rel", "gol_fatti",
                                "gol_subiti"]),
    ]
    y = g["voto_medio"].to_numpy(dtype=float)
    tot = float(((y - y.mean()) ** 2).sum())

    righe = []
    for nome, feature in blocchi:
        if not feature:
            r2 = 0.0
            k = 1
        else:
            X = np.hstack([np.ones((len(g), 1)), _disegno(g, feature)])
            beta, *_ = np.linalg.lstsq(X, y, rcond=None)
            r2 = 1 - float(((y - X @ beta) ** 2).sum() / tot)
            k = X.shape[1]
        righe.append({"modello": nome, "parametri": k, "righe": len(g),
                      "r2_in_campione": r2,
                      "sd_residua": float(np.sqrt((1 - r2) * tot / len(g)))})
    out = pd.DataFrame(righe)
    out["sd_totale"] = float(np.sqrt(tot / len(g)))
    return out


def varianza_del_voto(stagioni=STAGIONI) -> pd.DataFrame:
    """Il tetto vero: quanta varianza del voto sta FRA giocatori e quanta DENTRO.

    Nessun modello che assegni un numero a un giocatore puo' spiegare la
    varianza **dentro** il giocatore — quella e' la partita, l'avversario, la
    giornata. E' il limite superiore di E4.1 detto nel modo piu' stretto, ed e'
    lo stesso fatto che `modello_asta` gia' usava per giustificare uno shrinkage
    forte sul voto (0,561 entro contro 0,207 fra), qui misurato al livello della
    riga giocatore-partita invece che della stagione.
    """
    from . import voti as V

    v = V.carica()
    v = v[(~v["allenatore"]) & v["voto_redazione"].notna()]
    v = v[v["stagione"].isin(stagioni)]

    righe = []
    for chiave, etichetta in ((["giocatore_id"], "giocatore"),
                              (["stagione", "giocatore_id"],
                               "giocatore-stagione")):
        g = v.groupby(chiave)["voto_redazione"]
        medie, n = g.mean(), g.size()
        ammessi = n >= MIN_PRESENZE_ADDESTRAMENTO
        var_fra = float(np.var(medie[ammessi], ddof=1))
        var_tot = float(v["voto_redazione"].var(ddof=1))
        righe.append({"raggruppamento": etichetta,
                      "unita": int(ammessi.sum()),
                      "sd_totale": float(np.sqrt(var_tot)),
                      "sd_fra": float(np.sqrt(var_fra)),
                      "sd_entro": float(np.sqrt(max(var_tot - var_fra, 0.0))),
                      "quota_fra": var_fra / var_tot})
    return pd.DataFrame(righe)
