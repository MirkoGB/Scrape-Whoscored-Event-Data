# -*- coding: utf-8 -*-
"""Fase 9 / Blocco E1 — lo strato feature del giocatore, e la regola che lo governa.

Questo modulo **non produce modelli**: produce il vincolo che tutti i blocchi
successivi rispettano, e il vincolo nasce da cose gia' misurate in questo
repository, non da un principio generale.

LA REGOLA
---------
    Nessuna feature da dati evento entra in un modello multi-stagione in
    **unita' grezze**. Ogni feature entra come **scarto relativo alla media di
    campionato della propria stagione**.

E' la stessa forma che CLAUDE.md prescrive per `rho` ("eccessi relativi alla
media di campionato della stagione, non scarti assoluti"), e per la stessa
ragione: fra le cinque stagioni la media di campionato dei tiri in porta si e'
mossa del 9,2% **per ragioni di gioco**, quindi +1 tiro di eccesso non significa
la stessa cosa nel 2021-22 e nel 2025-26. Sulle grandezze da cui verrebbero le
feature del voto base la deriva e' peggiore: `Clearance` +48%, `BallRecovery`
-26%, `Error` +162%, `shotCounter` da 3,4% a 7,7% dei tentativi.

La forma e' `x / m_s - 1`, dove `m_s` e' il riferimento di campionato della
stagione `s`. Non e' uno z-score: dividere per la deviazione standard di
stagione **normalizzerebbe via anche la dispersione**, che e' proprio cio' che
distingue i giocatori e cioe' il segnale. Qui si toglie il livello, non la
scala.

DOVE VIVE LA REGOLA, E PERCHE' NON PIU' IN BASSO
------------------------------------------------
Nel derivato (`player_match`, `team_match`) le unita' restano **grezze**: la
deriva si porta avanti, non si normalizza via, perche' cancellarla dentro il
derivato cancellerebbe un fatto misurato (vincolo 4) in un posto da cui non e'
piu' recuperabile. La standardizzazione avviene **qui**, al momento in cui la
feature entra in un modello multi-stagione, e da qui il derivato resta
ricostruibile all'indietro: `x = (x_rel + 1) * m_s`, con `m_s` in tabella.

OGNI FEATURE E' UN RAPPORTO DICHIARATO, NON UNA COLONNA
-------------------------------------------------------
Ogni candidata e' definita come **numeratore su denominatore** (`Feature.num`,
`Feature.den`), e non come una colonna gia' calcolata. Non e' pedanteria: e' cio'
che rende il riferimento di campionato **la stessa grandezza** del valore del
singolo. Il riferimento e' `somma(num) / somma(den)` su tutto il campionato —
non la media delle medie individuali, che peserebbe uguale chi ha giocato 90
minuti e chi ne ha giocati 3.000, e non sarebbe piu' confrontabile con il
numeratore che sta al numeratore del singolo.

TRE COROLLARI, IMPLEMENTATI COME TEST E NON COME BUONE INTENZIONI
------------------------------------------------------------------
1. **Nessuna feature costruita sul nome di un qualifier senza aver verificato la
   sua frequenza nelle cinque stagioni** (`verifica_qualifier`). `StandingSave`
   e' la dimostrazione che il nome non e' un identificatore: sta sul 71% di
   tutti gli eventi nelle prime quattro stagioni e sul 4% nel 2025-26, a schema
   invariato, perche' e' **la stessa etichetta su id diversi**. Il gate e'
   necessario e **non sufficiente**: l'unico controllo sufficiente sarebbe l'id
   numerico, che `acquisition/whoscored/main.py:432` butta via tenendo solo il
   `displayName`.
2. **Un test che fallisce se una colonna che entra in un modello multi-stagione
   ha una media di stagione che si muove oltre la soglia dichiarata senza essere
   stata standardizzata** (`verifica_standardizzazione`).
3. **Le 72 colonne mai valorizzate restano fuori** (`colonne_mai_valorizzate`),
   e le grandezze che qualcuno cercherebbe li' — porta inviolata, gol subiti,
   precisione dei passaggi — **si derivano** (`derivazioni`). La misura giusta
   di presenza e' "ne' nullo ne' `False`", non `notna()`: lo scraper scrive il
   literal `False` dove il campo della fonte e' assente, quindi `notna()`
   direbbe "valorizzata al 100%" di una colonna vuota.

COSA QUESTO MODULO NON FA
--------------------------
- **Non stima niente.** Nessun fit, nessun iperparametro, nessun bersaglio.
- **Non aggrega a `giocatore_id`.** La riga e' la tripla `(stagione, playerId,
  teamId)`, cioe' la stessa granularita' dell'aggancio di E0: chi cambia squadra
  a gennaio ha due righe, perche' i suoi minuti sono di due squadre diverse.
  Portare la tabella al livello del modello d'asta e' lavoro di E2, e vuole una
  decisione (sommare? tenere la squadra principale?) che non e' di questo blocco.
- **Non rende `xg` confrontabile fra stagioni.** La standardizzazione toglie il
  livello, ma i cinque fit di xG sono **cinque modelli diversi** e non solo
  cinque livelli: `xg_per_90_rel` va usato sapendolo, ed e' segnato nel registro.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from . import config, features as FT, io_events, ricognizione as RIC

STAGIONI = config.SEASONS_STORICHE

# --------------------------------------------------------------------------
# Le due soglie, dichiarate PRIMA di guardare l'esito (lezione della Fase 6D)
# --------------------------------------------------------------------------

# Di quanto la media di stagione di una colonna puo' muoversi prima che quella
# colonna sia inutilizzabile in unita' grezze. 5% e' scelto cosi':
#
#   * sta **sotto** la piu' piccola deriva reale gia' misurata nel repository —
#     i tiri in porta per squadra-partita, -9,2% fra la prima e l'ultima
#     stagione — quindi tutto cio' che si sa gia' muoversi viene preso;
#   * sta **molto sopra** l'errore di campionamento di una media di campionato,
#     che su 17.000 righe giocatore-partita e' dell'ordine di qualche decimo di
#     punto percentuale. Una soglia a quel livello dichiarerebbe instabile
#     qualunque cosa, e una guardia che scatta sempre non e' una guardia.
#
# Non e' stata scelta guardando quali candidate passano: e' il numero che
# separa le due grandezze note.
SOGLIA_DERIVA = 0.05

# Rapporto massimo fra la frequenza per evento piu' alta e piu' bassa di un
# qualifier nelle cinque stagioni. 1,5 e' il punto oltre il quale il movimento
# non e' piu' compatibile con cio' che il *gioco* ha fatto: la deriva piu'
# grande mai misurata su un tipo di evento e' `Clearance` +48%. I due casi noti
# di dizionario cambiato stanno a 17x (`StandingSave`) e 30x (`OtherBodyPart`),
# cioe' un ordine di grandezza oltre la soglia: non e' un numero delicato.
SOGLIA_QUALIFIER = 1.5

# Esposizione minima perche' una riga entri nelle **medie di stagione** con cui
# si misura la deriva. Non tocca il riferimento di campionato, che usa tutto.
# Serve solo a evitare che la media di stagione di un tasso per 90 sia dominata
# dagli spezzoni di tre minuti, dove il denominatore e' minuscolo e il tasso
# esplode. 450 minuti = cinque partite intere.
MIN_MINUTI_DERIVA = 450.0


class FeatureNonStandardizzata(RuntimeError):
    """Una colonna che deriva oltre la soglia sta entrando in unita' grezze."""


class QualifierNonVerificato(RuntimeError):
    """Una feature dichiara un qualifier che non ha superato il gate."""


# --------------------------------------------------------------------------
# Il registro delle candidate
# --------------------------------------------------------------------------

@dataclass(frozen=True)
class Feature:
    """Una feature candidata, definita come rapporto fra due somme.

    `num` e `den` sono nomi di colonne della tabella degli ingredienti, che e'
    fatta di **sole somme** per riga. E' quella forma a rendere il riferimento
    di campionato la stessa grandezza del valore individuale.
    """

    nome: str
    num: str
    den: str
    famiglia: str
    unita: str
    descrizione: str
    qualifier: tuple[str, ...] = ()
    nota: str = ""

    @property
    def rel(self) -> str:
        """Il nome della colonna standardizzata. Il suffisso e' un contratto."""
        return f"{self.nome}_rel"


SUFFISSO_STANDARDIZZATA = "_rel"

CANDIDATE: tuple[Feature, ...] = (
    # --- esposizione: e' qui che aspetta il 91% dell'errore del modello d'asta
    Feature("quota_minuti_squadra", "minuti", "minuti_squadra", "esposizione",
            "quota", "minuti del giocatore sui minuti-giocatore della sua squadra",
            nota="il riferimento e' quasi una costante di costruzione "
                 "(~1/rosa): si muove solo se si muove l'ampiezza delle rose"),
    Feature("quota_presenze", "presenze", "partite_squadra", "esposizione",
            "quota", "partite giocate sulle partite ACQUISITE della sua squadra",
            nota="il denominatore si conta, non e' 38: l'Atalanta ne ha 35 nelle "
                 "due stagioni bucate (E0). Chi arriva a gennaio ha comunque il "
                 "calendario intero al denominatore — limite dichiarato"),
    Feature("quota_titolare", "da_titolare", "partite_squadra", "esposizione",
            "quota", "partite da titolare sulle partite acquisite della squadra"),
    Feature("minuto_medio_ingresso", "somma_ingresso", "ingressi", "esposizione",
            "minuto", "minuto espanso medio d'ingresso, sui soli subentri",
            nota="e' l'ingresso del modello dell's.v.: la regola dell'80' guarda "
                 "esattamente questo minuto"),
    Feature("minuto_medio_uscita", "somma_uscita", "da_titolare", "esposizione",
            "minuto", "minuto medio di uscita, sulle sole partite da titolare",
            nota="per un titolare `minutes` COINCIDE con il minuto di uscita, "
                 "perche' entra a 0. Chi esce al 60' e chi esce al 90' hanno la "
                 "stessa presenza oggi e non lo stesso futuro"),

    # --- produzione
    Feature("tiri_per_90", "tiri", "novantesimi", "produzione", "per_90",
            "tentativi per 90 minuti"),
    Feature("sot_per_90", "sot", "novantesimi", "produzione", "per_90",
            "tiri in porta per 90 minuti",
            nota="la media di campionato di questa grandezza si e' mossa del "
                 "9,2% fra la prima e l'ultima stagione, ed e' il caso su cui la "
                 "regola e' stata scritta"),
    Feature("gol_per_90", "gol", "novantesimi", "produzione", "per_90",
            "gol per 90 minuti"),
    Feature("xg_per_90", "xg", "novantesimi", "produzione", "per_90",
            "xG interno per 90 minuti",
            nota="ATTENZIONE: cinque fit indipendenti, quindi cinque SCALE "
                 "(`xg_fit`). La standardizzazione toglie il livello ma non "
                 "rende i cinque modelli lo stesso modello"),

    # --- coinvolgimento
    Feature("tocchi_per_90", "tocchi", "novantesimi", "coinvolgimento", "per_90",
            "tocchi per 90 minuti: quanto la squadra passa da lui"),
    Feature("passaggi_per_90", "passaggi", "novantesimi", "coinvolgimento",
            "per_90", "passaggi tentati per 90 minuti"),
    Feature("precisione_passaggi", "passaggi_riusciti", "passaggi",
            "coinvolgimento", "quota", "quota di passaggi riusciti",
            nota="DERIVATA: `passAccuracy` e' una delle 72 colonne mai "
                 "valorizzate, quindi si deriva da `passAccurate` e "
                 "`passInaccurate` invece di leggerla"),
    Feature("quota_tocchi_area", "tocchi_area", "tocchi", "coinvolgimento",
            "quota", "quota dei tocchi dentro l'area avversaria"),
    Feature("x_medio", "somma_x", "tocchi", "coinvolgimento", "coordinata",
            "ascissa media dei tocchi, in coordinate Opta 0-100",
            nota="tutte le squadre attaccano verso x = 100, quindi non serve "
                 "nessun ribaltamento"),

    # --- difesa e disciplina
    Feature("azioni_difensive_per_90", "azioni_difensive", "novantesimi",
            "difesa", "per_90", "contrasti, intercetti e respinte per 90 minuti",
            nota="contiene `clearanceTotal`, cioe' la grandezza che il Blocco 0 "
                 "ha misurato a +48% fra 2021-22 e 2025-26. E' il caso peggiore "
                 "del blocco ed e' tenuto apposta"),
    Feature("falli_per_90", "falli", "novantesimi", "difesa", "per_90",
            "falli commessi per 90 minuti, come predittore dei cartellini"),
    Feature("ammonizioni_per_90", "ammonizioni", "novantesimi", "difesa",
            "per_90", "cartellini gialli per 90 minuti",
            nota="alimenta le squalifiche di E2, che sono DETERMINISTICHE dai "
                 "cartellini e non vanno previste. Le espulsioni ad allenatore e "
                 "staff hanno `playerId` nullo e sono escluse qui"),
    Feature("quota_porta_inviolata", "partite_porta_inviolata", "presenze",
            "difesa", "quota", "quota delle sue partite chiuse senza subire gol",
            nota="DERIVATA: tutte le `cleanSheet*` sono fra le 72 colonne mai "
                 "valorizzate. Si deriva dai gol dell'avversario"),
    Feature("gol_subiti_per_partita", "gol_subiti_pesati", "minuti", "difesa",
            "gol_partita", "gol subiti dalla squadra nelle sue partite, "
                           "pesati sui suoi minuti",
            nota="DERIVATA come sopra (`goalConcededByTeam*` mai valorizzate). "
                 "E' un peso pro-quota sui minuti, NON i gol subiti mentre era "
                 "in campo: quelli vorrebbero il minuto del gol, ed e' un altro "
                 "calcolo. La differenza va dichiarata da chi la usa"),
)

CHIAVE = ("stagione", "playerId", "teamId")

# Colonne descrittive che accompagnano la chiave e non sono feature.
ANAGRAFICA = ("playerName", "team", "role", "role_inferred", "minuti",
              "presenze", "partite_squadra")


def per_nome(nome: str) -> Feature:
    for f in CANDIDATE:
        if f.nome == nome:
            return f
    raise KeyError(nome)


def nomi_grezzi() -> tuple[str, ...]:
    return tuple(f.nome for f in CANDIDATE)


def nomi_standardizzati() -> tuple[str, ...]:
    return tuple(f.rel for f in CANDIDATE)


# --------------------------------------------------------------------------
# Corollario 3 — le 72 colonne mai valorizzate, e cio' che si deriva al loro posto
# --------------------------------------------------------------------------

def colonne_mai_valorizzate() -> frozenset[str]:
    """Le colonne che in **nessuna** stagione portano un valore.

    La misura e' `quota_valorizzata`, cioe' "ne' nullo ne' `False`", e non
    `quota_non_nulli`: lo scraper del fork scrive il literal `False` dove il
    campo della fonte e' assente, quindi `notna()` dichiara valorizzate al 100%
    circa 200 colonne su 259 che valorizzate non sono. E' la trappola misurata
    dal Blocco 0, e qui e' il motivo per cui questa funzione non usa `notna()`.

    Sono 72, e fra loro ci sono tutte le `cleanSheet*`, `goalConcededByTeam*`,
    `goalScoredByTeam*`, le `save*` per settore di porta e `passAccuracy`.
    """
    if not RIC.CACHE["colonne"].exists():
        raise FileNotFoundError(
            "manca la ricognizione del Blocco 0: "
            "./.venv/Scripts/python.exe scripts/run_blocco0.py")
    c = pd.read_parquet(RIC.CACHE["colonne"])
    piv = c.pivot(index="colonna", columns="stagione", values="quota_valorizzata")
    return frozenset(piv.index[(piv.fillna(0.0) == 0.0).all(axis=1)])


def derivazioni() -> pd.DataFrame:
    """Le tre grandezze che si derivano, con la colonna che NON si legge.

    Non e' documentazione: e' l'elenco su cui un test verifica che nessuna delle
    colonne della prima riga compaia nel sorgente di questo modulo.
    """
    return pd.DataFrame([
        {"grandezza": "porta inviolata",
         "colonna_della_fonte": "cleanSheet* (17 colonne)",
         "stato": "mai valorizzata in nessuna stagione",
         "derivazione": "gol dell'avversario nella stessa partita == 0",
         "feature": "quota_porta_inviolata"},
        {"grandezza": "gol subiti",
         "colonna_della_fonte": "goalConcededByTeam* (17 colonne)",
         "stato": "mai valorizzata in nessuna stagione",
         "derivazione": "`goals` della riga avversaria di `team_match`",
         "feature": "gol_subiti_per_partita"},
        {"grandezza": "precisione dei passaggi",
         "colonna_della_fonte": "passAccuracy",
         "stato": "mai valorizzata in nessuna stagione",
         "derivazione": "passAccurate / (passAccurate + passInaccurate)",
         "feature": "precisione_passaggi"},
    ])


# --------------------------------------------------------------------------
# Corollario 1 — il gate sui qualifier
# --------------------------------------------------------------------------

def verifica_qualifier(nomi: tuple[str, ...] = None,
                       soglia: float = SOGLIA_QUALIFIER) -> pd.DataFrame:
    """Frequenza per evento di ogni qualifier nelle cinque stagioni, con verdetto.

    Colonne: una per stagione, piu' `min`, `max`, `rapporto`, `stagioni`,
    `ammesso`. Un qualifier e' ammesso se compare in **tutte e cinque** le
    stagioni e se il rapporto fra la frequenza massima e la minima sta sotto
    `soglia`.

    **Il gate e' necessario, non sufficiente.** Un qualifier che lo passa non e'
    dimostrato essere la stessa cosa in tutte le stagioni: dimostrarlo vorrebbe
    l'id numerico, che non e' nei dati in casa. Il gate esclude i casi in cui il
    nome ha cambiato significato **in modo visibile**, che sono i due gia' noti.
    """
    if not (RIC.CACHE["qualifier"].exists() and RIC.CACHE["file"].exists()):
        raise FileNotFoundError(
            "manca la ricognizione del Blocco 0: "
            "./.venv/Scripts/python.exe scripts/run_blocco0.py")

    qual = pd.read_parquet(RIC.CACHE["qualifier"])
    file = pd.read_parquet(RIC.CACHE["file"])
    eventi = file.groupby("stagione")["n_eventi"].sum().rename("eventi")

    d = qual.merge(eventi, on="stagione")
    d["per_evento"] = d["n"] / d["eventi"]
    piv = d.pivot(index="qualifier", columns="stagione", values="per_evento")

    if nomi is not None:
        mancanti = [n for n in nomi if n not in piv.index]
        piv = piv.reindex([n for n in nomi if n in piv.index])
    else:
        mancanti = []

    out = piv.copy()
    out["stagioni"] = piv.notna().sum(axis=1)
    out["min"] = piv.min(axis=1)
    out["max"] = piv.max(axis=1)
    out["rapporto"] = np.where(out["min"] > 0, out["max"] / out["min"], np.inf)
    out["ammesso"] = ((out["stagioni"] == len(STAGIONI))
                      & (out["rapporto"] <= soglia))
    out = out.reset_index()

    for n in mancanti:
        # Un qualifier che la ricognizione non ha mai visto non e' "raro": e'
        # non verificabile, e non verificabile vuol dire non ammesso.
        out = pd.concat([out, pd.DataFrame([{
            "qualifier": n, "stagioni": 0, "min": np.nan, "max": np.nan,
            "rapporto": np.inf, "ammesso": False}])], ignore_index=True)
    return out


def qualifier_dichiarati() -> tuple[str, ...]:
    """I qualifier che le feature del registro dichiarano di usare."""
    visti: list[str] = []
    for f in CANDIDATE:
        for q in f.qualifier:
            if q not in visti:
                visti.append(q)
    return tuple(visti)


def controlla_qualifier_delle_candidate(soglia: float = SOGLIA_QUALIFIER) -> None:
    """Solleva se una candidata usa un qualifier che non passa il gate.

    Oggi non solleva perche' **nessuna candidata usa qualifier**, e non per
    virtu': `events_slim` non porta la colonna `qualifiers` (la tiene solo per i
    cinque tipi di evento di formazione), quindi una feature sui piazzati vuole
    una rilettura dei 1.889 CSV. E' un costo che paga E4, non E1. La guardia
    esiste perche' il giorno in cui qualcuno la aggiunge, il gate scatti da solo.
    """
    dichiarati = qualifier_dichiarati()
    if not dichiarati:
        return
    v = verifica_qualifier(dichiarati, soglia).set_index("qualifier")
    cattivi = [q for q in dichiarati if not bool(v.loc[q, "ammesso"])]
    if cattivi:
        raise QualifierNonVerificato(
            f"qualifier non verificati: {cattivi} (soglia {soglia})")


# --------------------------------------------------------------------------
# Gli ingredienti: solo somme, una riga per (stagione, playerId, teamId)
# --------------------------------------------------------------------------

_DEF_BOOL = ("tackleWon", "tackleLost", "interceptionAll", "clearanceTotal")


def _da_eventi(stagione: str) -> pd.DataFrame:
    """Somme per giocatore-squadra dagli eventi di UNA stagione.

    Una stagione per volta, mai concatenate: le frequenze dei tipi di evento
    derivano fra stagioni, e un `groupby` che dimenticasse `stagione`
    mescolerebbe cinque regimi di annotazione.
    """
    ev = io_events.load_events(season=stagione)
    ev = ev[ev["playerId"].notna()].copy()
    ev["playerId"] = ev["playerId"].astype("int64")

    tocchi = ev[ev["isTouch"]]
    in_area = tocchi[FT._in_box(tocchi)]

    chiave = ["playerId", "teamId"]
    somme = pd.DataFrame({
        "tocchi": tocchi.groupby(chiave).size(),
        "somma_x": tocchi.groupby(chiave)["x"].sum(),
        "tocchi_area": in_area.groupby(chiave).size(),
        "passaggi_riusciti": ev.groupby(chiave)["passAccurate"].sum(),
        "passaggi_sbagliati": ev.groupby(chiave)["passInaccurate"].sum(),
        "falli": ev.groupby(chiave)["foulCommitted"].sum(),
        "azioni_difensive": ev.groupby(chiave)[list(_DEF_BOOL)].sum().sum(axis=1),
    }).fillna(0.0).reset_index()
    somme["passaggi"] = somme["passaggi_riusciti"] + somme["passaggi_sbagliati"]
    return somme


def _da_lineup(stagione: str) -> pd.DataFrame:
    """Ingressi dalla panchina e ammonizioni, dagli eventi di formazione.

    Il minuto d'ingresso **non e' in `player_match`** e non e' derivabile dai
    minuti: un subentrato puo' uscire a sua volta, o essere espulso. Si legge da
    `SubstitutionOn`, che e' l'unico posto in cui c'e'.

    Le ammonizioni escludono le righe con `playerId` nullo: sono i cartellini ad
    allenatore e staff — 17 espulsioni su 85 nella sola 2025-26 — e non
    appartengono a nessun giocatore.
    """
    lu = io_events.load_lineup_events(season=stagione)
    lu = lu[lu["playerId"].notna()].copy()
    lu["playerId"] = lu["playerId"].astype("int64")
    chiave = ["playerId", "teamId"]

    on = lu[lu["type"] == "SubstitutionOn"]
    # Un giocatore puo' entrare una volta sola per partita: il `min` protegge da
    # eventuali doppioni del feed senza cambiare niente dove non ce ne sono.
    ingressi = (on.groupby(chiave + ["matchId"])["expandedMinute"].min()
                .reset_index().groupby(chiave)["expandedMinute"]
                .agg(ingressi="size", somma_ingresso="sum"))

    gialli = lu[(lu["type"] == "Card") & (lu["cardType"] == "Yellow")]
    ammonizioni = gialli.groupby(chiave).size().rename("ammonizioni")

    return (pd.concat([ingressi, ammonizioni], axis=1)
            .fillna(0.0).reset_index())


def _da_player_match(stagione: str) -> pd.DataFrame:
    """Somme di esposizione e produzione da `player_match`, piu' i gol subiti.

    I gol subiti e la porta inviolata si **derivano** dalla riga avversaria di
    `team_match` (corollario 3), non si leggono: `goalConcededByTeam*` e
    `cleanSheet*` sono fra le 72 colonne mai valorizzate.
    """
    pm = pd.read_parquet(config.player_match(season=stagione))
    tm = pd.read_parquet(config.team_match(season=stagione))

    subiti = (tm[["matchId", "opponentId", "goals"]]
              .rename(columns={"opponentId": "teamId", "goals": "gol_subiti"}))
    pm = pm.merge(subiti, on=["matchId", "teamId"], how="left")
    pm["gol_subiti"] = pm["gol_subiti"].fillna(0.0)

    giocata = pm["minutes"] > 0
    pm["presenze"] = giocata.astype(int)
    pm["da_titolare"] = (pm["stato"] == "titolare").astype(int)
    # Per un titolare `minutes` E' il minuto di uscita: entra a 0.
    pm["somma_uscita"] = np.where(pm["stato"] == "titolare", pm["minutes"], 0.0)
    pm["porta_inviolata"] = (giocata & (pm["gol_subiti"] == 0)).astype(int)
    pm["gol_subiti_pesati"] = pm["gol_subiti"] * pm["minutes"]

    chiave = ["playerId", "teamId"]
    agg = pm.groupby(chiave).agg(
        playerName=("playerName", "first"),
        team=("team", "first"),
        role=("role", "first"),
        role_inferred=("role_inferred", "first"),
        convocazioni=("minutes", "size"),
        minuti=("minutes", "sum"),
        presenze=("presenze", "sum"),
        da_titolare=("da_titolare", "sum"),
        somma_uscita=("somma_uscita", "sum"),
        tiri=("shots", "sum"),
        sot=("sot", "sum"),
        gol=("goals", "sum"),
        xg=("xg", "sum"),
        partite_porta_inviolata=("porta_inviolata", "sum"),
        gol_subiti_pesati=("gol_subiti_pesati", "sum"),
    ).reset_index()

    # I due denominatori di squadra. **Si contano, non si assumono**: e' la
    # lezione di E0, e vale qui perche' entra in ogni quota di esposizione.
    per_squadra = tm.groupby("teamId")["matchId"].nunique().rename("partite_squadra")
    minuti_squadra = pm.groupby("teamId")["minutes"].sum().rename("minuti_squadra")
    agg = (agg.merge(per_squadra, on="teamId", how="left")
              .merge(minuti_squadra, on="teamId", how="left"))
    agg["playerId"] = agg["playerId"].astype("int64")
    return agg


def ingredienti(stagioni=STAGIONI) -> pd.DataFrame:
    """Le somme, una riga per `(stagione, playerId, teamId)`. Nessun rapporto.

    Tenere separate le somme dai rapporti non e' un vezzo: e' cio' che permette
    al riferimento di campionato di essere `somma(num)/somma(den)` sulla stessa
    coppia di colonne che definisce il valore individuale.
    """
    pezzi = []
    for st in stagioni:
        base = _da_player_match(st)
        base = base.merge(_da_eventi(st), on=["playerId", "teamId"], how="left")
        base = base.merge(_da_lineup(st), on=["playerId", "teamId"], how="left")
        base["stagione"] = st
        pezzi.append(base)

    out = pd.concat(pezzi, ignore_index=True)
    conteggi = ["tocchi", "somma_x", "tocchi_area", "passaggi", "passaggi_riusciti",
                "passaggi_sbagliati", "falli", "azioni_difensive",
                "ingressi", "somma_ingresso", "ammonizioni"]
    out[conteggi] = out[conteggi].fillna(0.0)
    out["novantesimi"] = out["minuti"] / 90.0
    cols = list(CHIAVE) + [c for c in out.columns if c not in CHIAVE]
    return out[cols].sort_values(list(CHIAVE)).reset_index(drop=True)


# --------------------------------------------------------------------------
# I riferimenti di campionato e la standardizzazione
# --------------------------------------------------------------------------

def riferimenti(ingr: pd.DataFrame) -> pd.DataFrame:
    """Riferimento di campionato per stagione e feature. Forma lunga.

    Colonne: `stagione`, `grandezza`, `unita`, `media`, `n` — **lo stesso schema
    di `multistagione.medie_campionato`**, di proposito: sono la stessa cosa a un
    altro livello di aggregazione, e chi le legge non deve imparare due formati.

    Sta pero' in un **file separato** e non appeso a quella tabella per una
    ragione operativa: `run_fase9_e0.py` riscrive il proprio Parquet per intero
    a ogni esecuzione, quindi righe di E1 aggiunte li' sparirebbero al primo
    rilancio di E0 senza che nessuno se ne accorga.

    `media = somma(num) / somma(den)` su **tutte** le righe della stagione, senza
    filtro di esposizione: il riferimento e' il campionato, non i titolari.
    """
    righe = []
    for st, blocco in ingr.groupby("stagione", sort=True):
        for f in CANDIDATE:
            den = float(blocco[f.den].sum())
            num = float(blocco[f.num].sum())
            righe.append({
                "stagione": st,
                "grandezza": f.nome,
                "unita": f.unita,
                "media": num / den if den > 0 else np.nan,
                "n": int((blocco[f.den] > 0).sum()),
            })
    return pd.DataFrame(righe).sort_values(["grandezza", "stagione"]).reset_index(drop=True)


def standardizza(ingr: pd.DataFrame, rif: pd.DataFrame = None) -> pd.DataFrame:
    """Dalle somme alle feature, grezze **e** standardizzate, affiancate.

    Per ogni candidata produce due colonne:

        `nome`       il rapporto in unita' grezze, cioe' cio' che il derivato
                     direbbe. Resta in tabella: la regola vieta di usarla in un
                     modello multi-stagione, non di guardarla — e senza, la
                     deriva non sarebbe piu' misurabile;
        `nome_rel`   `nome / m_s - 1`, lo scarto relativo alla media di
                     campionato della **propria** stagione.

    Il derivato resta ricostruibile all'indietro: `nome = (nome_rel + 1) * m_s`,
    e `m_s` sta in `riferimenti`. E' la ragione per cui la standardizzazione puo'
    stare qui senza cancellare niente.
    """
    rif = riferimenti(ingr) if rif is None else rif
    tavola = rif.set_index(["grandezza", "stagione"])["media"]
    out = ingr.copy()
    for f in CANDIDATE:
        den = out[f.den].astype(float)
        valore = np.where(den > 0, out[f.num].astype(float) / den.replace(0, np.nan), np.nan)
        out[f.nome] = valore
        m = np.array([tavola.get((f.nome, s), np.nan) for s in out["stagione"]])
        with np.errstate(invalid="ignore", divide="ignore"):
            out[f.rel] = np.where(np.isfinite(m) & (m != 0), valore / m - 1.0, np.nan)
    return out


def costruisci(stagioni=STAGIONI, force: bool = False) -> dict[str, pd.DataFrame]:
    """Tabella feature + riferimenti, con cache Parquet.

    Non tocca `raw/` e non tocca la rete. `force` ricalcola invece di rileggere.
    """
    p_feat, p_rif = config.FEATURE_GIOCATORE, config.FEATURE_RIFERIMENTI
    if not force and p_feat.exists() and p_rif.exists():
        feat = pd.read_parquet(p_feat)
        if set(feat["stagione"].unique()) == set(stagioni):
            return {"feature": feat, "riferimenti": pd.read_parquet(p_rif)}

    ingr = ingredienti(stagioni)
    rif = riferimenti(ingr)
    feat = standardizza(ingr, rif)
    feat.to_parquet(p_feat, index=False)
    rif.to_parquet(p_rif, index=False)
    return {"feature": feat, "riferimenti": rif}


# --------------------------------------------------------------------------
# Corollario 2 — la deriva, prima e dopo, e la guardia
# --------------------------------------------------------------------------

def _medie_di_stagione(df: pd.DataFrame, colonne, min_minuti: float) -> pd.DataFrame:
    d = df[df["minuti"] >= min_minuti] if min_minuti else df
    return d.groupby("stagione")[list(colonne)].mean()


def deriva_feature(feat: pd.DataFrame,
                   min_minuti: float = MIN_MINUTI_DERIVA) -> pd.DataFrame:
    """Di quanto si muove la media di stagione di ogni candidata, prima e dopo.

    E' **il** risultato del blocco, e le due colonne sono confrontabili perche'
    sono nella stessa unita':

        `deriva_grezza`  escursione delle medie di stagione della colonna
                         grezza, divisa per la media complessiva. E'
                         adimensionale;
        `deriva_std`     escursione delle medie di stagione della colonna
                         standardizzata. E' gia' adimensionale, perche' la
                         colonna e' uno scarto **relativo**.

    Non e' garantito che `deriva_std` sia zero, e non deve esserlo: il
    riferimento e' la media **pesata sull'esposizione** (`somma(num)/somma(den)`)
    mentre qui si guarda la media **non pesata** fra giocatori. Se le due si
    muovono in modo diverso, cio' che resta e' un cambio di *composizione* del
    campionato — piu' minuti a chi tira, rose piu' larghe — e non un cambio di
    livello. Quel residuo e' un risultato, non un errore di calcolo, e per questo
    la guardia lo misura invece di darlo per morto.

    `min_minuti` esclude gli spezzoni dalle sole **medie**: il riferimento usa
    tutto. Senza il filtro un tasso per 90 calcolato su tre minuti giocati
    dominerebbe la media di stagione.
    """
    grezze = _medie_di_stagione(feat, nomi_grezzi(), min_minuti)
    rel = _medie_di_stagione(feat, nomi_standardizzati(), min_minuti)

    righe = []
    for f in CANDIDATE:
        g, r = grezze[f.nome], rel[f.rel]
        scala = float(np.abs(g.mean()))
        righe.append({
            "feature": f.nome,
            "famiglia": f.famiglia,
            "unita": f.unita,
            "prima": float(g.iloc[0]),
            "ultima": float(g.iloc[-1]),
            "deriva_grezza": (float(g.max() - g.min()) / scala) if scala > 0 else np.nan,
            "deriva_std": float(r.max() - r.min()),
            "oltre_soglia_grezza": bool(
                scala > 0 and (g.max() - g.min()) / scala > SOGLIA_DERIVA),
            "oltre_soglia_std": bool((r.max() - r.min()) > SOGLIA_DERIVA),
        })
    out = pd.DataFrame(righe)
    out["riduzione"] = 1.0 - out["deriva_std"] / out["deriva_grezza"]
    out["verdetto"] = [_verdetto(r) for r in out.itertuples(index=False)]
    return out.sort_values("deriva_grezza", ascending=False).reset_index(drop=True)


# I tre esiti possibili, ed e' l'esito che decide come la feature entra in un
# modello multi-stagione. Il terzo e' previsto dalla regola stessa: "dove la
# standardizzazione non basta, la stagione entra come effetto esplicito".
VERDETTI = ("grezza ammessa", "standardizzata", "serve effetto di stagione")


def _verdetto(r) -> str:
    if not r.oltre_soglia_grezza:
        # Non si muove: standardizzarla non e' obbligatorio, e per alcune e'
        # perfino dannoso (vedi `scomposizione_deriva`).
        return VERDETTI[0]
    return VERDETTI[1] if not r.oltre_soglia_std else VERDETTI[2]


def richiede_effetto_stagione(feat: pd.DataFrame,
                              min_minuti: float = MIN_MINUTI_DERIVA) -> tuple[str, ...]:
    """Le candidate su cui la standardizzazione **non basta**.

    Esiste per essere interrogata da E2 ed E4 invece che letta nel report: un
    modello che usa una di queste deve portarsi dietro un effetto di stagione
    esplicito, e "l'avevo letto nel markdown" non e' un vincolo eseguibile.
    """
    d = deriva_feature(feat, min_minuti)
    return tuple(d.loc[d["verdetto"] == VERDETTI[2], "feature"])


def scomposizione_deriva(feat: pd.DataFrame, rif: pd.DataFrame,
                         min_minuti: float = MIN_MINUTI_DERIVA) -> pd.DataFrame:
    """Perche' la standardizzazione a volte non basta, e a volte peggiora.

    Affianca due grandezze che il resto del blocco tiene separate:

        `deriva_riferimento`  escursione della media di campionato pesata,
                              `somma(num)/somma(den)` su **tutte** le righe. E'
                              il **livello**, ed e' esattamente cio' che la
                              standardizzazione toglie;
        `deriva_popolazione`  escursione della media non pesata fra i giocatori
                              sopra il pavimento di esposizione. E' la **forma**
                              della distribuzione e la composizione di chi gioca.

    Se le due coincidono, dividere per il riferimento azzera la deriva. Se
    divergono, resta un residuo, e il residuo puo' essere **piu' grande**
    dell'originale quando le due si muovono in versi opposti. Non e' un difetto
    del calcolo: la standardizzazione toglie il livello e non puo' toccare la
    forma, ed e' il limite della regola misurato invece che assunto.
    """
    pesata = rif.pivot(index="grandezza", columns="stagione", values="media")
    non_pesata = _medie_di_stagione(feat, nomi_grezzi(), min_minuti).T

    righe = []
    for f in CANDIDATE:
        a, b = pesata.loc[f.nome], non_pesata.loc[f.nome]
        righe.append({
            "feature": f.nome,
            "riferimento_prima": float(a.iloc[0]),
            "riferimento_ultima": float(a.iloc[-1]),
            "deriva_riferimento": float(a.max() - a.min()) / float(np.abs(a.mean())),
            "popolazione_prima": float(b.iloc[0]),
            "popolazione_ultima": float(b.iloc[-1]),
            "deriva_popolazione": float(b.max() - b.min()) / float(np.abs(b.mean())),
            # I due si muovono nello stesso verso fra prima e ultima stagione?
            "stesso_verso": bool(np.sign(a.iloc[-1] - a.iloc[0])
                                 == np.sign(b.iloc[-1] - b.iloc[0])),
        })
    return pd.DataFrame(righe).sort_values(
        "deriva_riferimento", ascending=False).reset_index(drop=True)


def sensibilita_pavimento(feat: pd.DataFrame,
                          pavimenti=(270.0, 450.0, 900.0, 1800.0)) -> pd.DataFrame:
    """Il verdetto dipende dal pavimento di esposizione? Si misura, non si spera.

    `MIN_MINUTI_DERIVA` e' una scelta dichiarata e non stimata, quindi va
    mostrato quanto il risultato le deve. Le candidate che stanno oltre la soglia
    a **ogni** pavimento sono un risultato; quelle che cambiano verdetto vanno
    trattate come non risolte, che e' il verso prudente.
    """
    righe = []
    for p in pavimenti:
        d = deriva_feature(feat, min_minuti=p)
        for r in d.itertuples(index=False):
            righe.append({"pavimento": p, "feature": r.feature,
                          "verdetto": r.verdetto,
                          "deriva_std": r.deriva_std})
    out = pd.DataFrame(righe)
    piv = out.pivot(index="feature", columns="pavimento", values="verdetto")
    piv["sempre_effetto_stagione"] = (piv == VERDETTI[2]).all(axis=1)
    piv["mai_effetto_stagione"] = (piv != VERDETTI[2]).all(axis=1)
    return piv.reset_index()


def verifica_standardizzazione(feat: pd.DataFrame, colonne,
                               soglia: float = SOGLIA_DERIVA,
                               min_minuti: float = MIN_MINUTI_DERIVA) -> pd.DataFrame:
    """LA GUARDIA. Solleva se una colonna deriva oltre la soglia dichiarata.

    Va chiamata da **chiunque** faccia entrare colonne di questa tabella in un
    modello che attraversa le stagioni, passando l'elenco delle colonne che sta
    per usare. Ritorna la tabella della deriva; solleva
    `FeatureNonStandardizzata` se anche una sola colonna la supera.

    Non distingue "grezza" da "standardizzata" guardando il nome: **misura**.
    Una colonna grezza che non si muove passa (e ce ne sono), una colonna
    `_rel` che si muove lo stesso viene fermata — che e' il caso interessante,
    perche' e' quello che il suffisso da solo nasconderebbe.
    """
    colonne = list(colonne)
    ignote = [c for c in colonne if c not in feat.columns]
    if ignote:
        raise KeyError(f"colonne assenti dalla tabella feature: {ignote}")

    medie = _medie_di_stagione(feat, colonne, min_minuti)
    righe = []
    for c in colonne:
        s = medie[c]
        # Una colonna gia' relativa e' misurata in assoluto (e' una frazione);
        # una colonna grezza va rapportata alla propria scala.
        relativa = c.endswith(SUFFISSO_STANDARDIZZATA)
        scala = 1.0 if relativa else float(np.abs(s.mean()))
        escursione = float(s.max() - s.min())
        deriva = escursione / scala if scala > 0 else np.inf
        righe.append({"colonna": c, "relativa": relativa,
                      "min": float(s.min()), "max": float(s.max()),
                      "deriva": deriva, "passa": deriva <= soglia})
    out = pd.DataFrame(righe)
    cattive = out[~out["passa"]]
    if len(cattive):
        elenco = ", ".join(f"{r.colonna} ({r.deriva:.1%})"
                           for r in cattive.itertuples(index=False))
        raise FeatureNonStandardizzata(
            f"colonne che derivano oltre {soglia:.0%} fra le stagioni "
            f"senza essere standardizzate: {elenco}")
    return out


def ricostruisci(feat: pd.DataFrame, rif: pd.DataFrame, nome: str) -> pd.Series:
    """`(x_rel + 1) * m_s`, cioe' la colonna grezza rifatta dalla standardizzata.

    Esiste per essere **verificata da un test**: e' la prova che la
    standardizzazione non ha cancellato niente, e cioe' che la regola sta nello
    strato feature e non nel derivato (vincolo 4).
    """
    f = per_nome(nome)
    tavola = rif.set_index(["grandezza", "stagione"])["media"]
    m = np.array([tavola.get((nome, s), np.nan) for s in feat["stagione"]])
    return pd.Series((feat[f.rel].to_numpy() + 1.0) * m, index=feat.index)
