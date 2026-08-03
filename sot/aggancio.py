# -*- coding: utf-8 -*-
"""Aggancio fra le due fonti: WhoScored (eventi, minuti) e fantacalcio.it (voti).

E' il prerequisito di tutta la Fase 8, e il Blocco 0 non poteva farlo: aveva un
lato solo. `data/mapping/whoscored_*.csv` elenca **le anomalie di identita' su
cui l'aggancio avrebbe fallito** — omonimi, multigrafia, cambi di squadra a
gennaio — proprio perche' il secondo lato non c'era. Adesso c'e'.

## Il principio: la chiave e' diversa ai due livelli, e il perche' e' misurato

Le due fonti non condividono nessun identificatore. Condividono un **calendario**
e dei **nomi**, e quale dei due sia l'impronta digitale **cambia col livello**:

| livello | chiave | verifica | perche' |
| --- | --- | --- | --- |
| squadra | l'insieme delle 38 coppie `(data, in casa)` | il nome | zero ambiguita' su cinque stagioni: il margine sul secondo candidato sta fra 19 e 29 partite su 38 |
| partita | `(stagione, casa, trasferta)` | la data | in un girone all'italiana la coppia **ordinata** compare una volta sola |
| giocatore | il **cognome** dentro la squadra, con le iniziali a disambiguare | il calendario | 586 su 609 sono gia' unici col solo cognome |

**Al livello di squadra il calendario e' una chiave e il nome no**, ed e' bene
che sia cosi': `AC Milan` contro `Milan`, `Parma Calcio 1913` contro `Parma`,
`Hellas Verona` contro `Verona` sono i nomi veri di queste due fonti.

**Al livello di giocatore e' l'esatto contrario, e questa e' la cosa che ho
dovuto misurare invece di assumerla.** La prima versione di questo modulo
agganciava i giocatori per insieme di presenze, per simmetria con le squadre.
Non funziona, e il motivo e' strutturale: l'insieme delle partite di una
*squadra* e' 38 su 380 — sparso, quindi discriminante — mentre quello di un
*giocatore* dentro la sua squadra e' 35 su 38, cioe' quasi pieno. Due titolari
qualsiasi della stessa squadra hanno un Jaccard di ~0,85 **fra loro**, e il
margine sul secondo candidato scendeva sotto 0,03 su meta' della rosa. Il
calendario, al livello di giocatore, non e' un'impronta: e' rumore.

Il nome invece lo e', a patto di normalizzarlo sul serio. I 23 casi su 609 che il
cognome grezzo sbaglia sono tutti e soli di due specie, e nessuna delle due e'
un'omonimia:

- **lettere che l'ASCII non piega**: `Højlund`, `Østigård`, `Grønbæk`, `Løvik`,
  `Sørensen`. La decomposizione Unicode non le tocca — `ø` non e' una `o` con un
  segno sopra, e' un'altra lettera — e servono a mano.
- **le iniziali del nome proprio**, che la fonte dei voti aggiunge **solo quando
  servono a distinguere**: `Martinez L.` e `Martinez Jo.`, `Pellegrini Lu.` e
  `Pellegrini Lo.`, `Esposito F.P.` e `Esposito Se.`. Sono l'informazione che
  risolve i due unici cognomi ambigui della stagione, quindi **si usano, non si
  tolgono** — la versione che le buttava via creava le ambiguita' che avrebbero
  poi dovuto essere risolte.

Il calendario resta, al livello di giocatore, come **verifica**: la colonna
`jaccard` dice quanto i due insiemi di presenze si sovrappongono. Un valore basso
non fa scartare la riga — la fa **pubblicare**, perche' significa che le due
fonti non sono d'accordo su chi e' sceso in campo, e quella e' una notizia.

## Cosa non si aggancia, e si dichiara

- **Le 12 partite che WhoScored non ha** (2021-22 e 2022-23, `matchCentreData:
  null`, verificate una per una). I voti ci sono, i minuti no.
- **Lo spareggio salvezza Spezia-Verona del 2022-23.** E' l'unica coppia
  ordinata che si ripete in una stagione, ed e' una partita vera che WhoScored ha
  e che le pagine dei voti — organizzate per giornata — non contengono.
- **Tutto cio' che non e' 2025-2026, per i giocatori.** L'aggancio dei giocatori
  ha bisogno delle presenze partita per partita dal lato WhoScored, che oggi
  esistono solo per la stagione pubblicata (`player_match.parquet`). E' anche
  l'unica stagione in cui serve davvero: la regola dell'80' e' falsificabile
  li' e solo li'.

## La giornata di campionato, che nei dati WhoScored non c'e'

Chiude la **D6** del Blocco 0 per la via (b): la giornata non si stima e non si
sostituisce con l'indice cronologico di squadra — **si legge dalla fonte dei
voti** e si porta sulle partite WhoScored attraverso questo aggancio. Il
`team_match_idx` resta cio' che era, un indice cronologico, e le due grandezze
non vanno confuse: divergono sui recuperi, ed e' esattamente per questo che
serviva la giornata vera.
"""

from __future__ import annotations

import pandas as pd

from sot import config, voti as V

MAPPING_DIR = config.DATA / "mapping"
SQUADRE_CSV = MAPPING_DIR / "aggancio_squadre.csv"
PARTITE_CSV = MAPPING_DIR / "aggancio_partite.csv"
GIOCATORI_CSV = MAPPING_DIR / "aggancio_giocatori.csv"
IRRISOLTI_CSV = MAPPING_DIR / "aggancio_giocatori_irrisolti.csv"

FILE_WS = config.processed_league_dir() / "blocco0_file.parquet"
SQUADRE_WS = MAPPING_DIR / "whoscored_squadre.csv"

# La sola stagione in cui coesistono minuti WhoScored e voti (cfr.
# `docs/regole_fantacalcio.md` §7.1, seconda conseguenza) — ed **e'
# `config.SEASON` per costruzione**, non per coincidenza: i voti coprono tutte e
# cinque le stagioni, i minuti solo quella per cui la Fase 1 ha costruito
# `player_match.parquet`, che e' la stagione pubblicata. Scriverla a mano qui
# creerebbe un secondo posto in cui una stagione ha un nome.
STAGIONE_CON_ENTRAMBE = config.SEASON


class AggancioAmbiguo(RuntimeError):
    """Due candidati a pari punteggio. Non si sceglie: si dichiara."""


# --------------------------------------------------------------------------
# Squadre
# --------------------------------------------------------------------------

def _firme_ws(f: pd.DataFrame) -> dict[int, set]:
    firme: dict[int, set] = {}
    for data, casa, ospite in zip(f["data"], f["teamId_casa"], f["teamId_ospite"]):
        g = data.date()
        firme.setdefault(int(casa), set()).add((g, 1))
        firme.setdefault(int(ospite), set()).add((g, 0))
    return firme


def _firme_fc(p: pd.DataFrame) -> dict[int, set]:
    firme: dict[int, set] = {}
    for data, casa, ospite in zip(p["data"], p["casa_id"], p["trasferta_id"]):
        g = data.date()
        firme.setdefault(int(casa), set()).add((g, 1))
        firme.setdefault(int(ospite), set()).add((g, 0))
    return firme


def mappa_squadre(stagioni=None) -> pd.DataFrame:
    """Le 20 squadre di ogni stagione, agganciate per calendario.

    **Il margine e' la colonna da guardare**, non la sovrapposizione: dice di
    quante partite il primo candidato batte il secondo. Un margine di 1 su 38
    sarebbe un aggancio che regge per caso; qui sta sopra le 30 ovunque, perche'
    due squadre diverse condividono al massimo qualche giornata di calendario.
    """
    stagioni = stagioni or config.SEASONS_STORICHE
    ws = pd.read_parquet(FILE_WS)
    nomi_ws = pd.read_csv(SQUADRE_WS).set_index(["stagione", "teamId"])["nome_whoscored"]
    fc_part = pd.read_parquet(V.PARTITE_PARQUET)
    nomi_fc = (pd.concat([
        fc_part[["stagione", "casa_id", "casa"]].rename(
            columns={"casa_id": "id", "casa": "nome"}),
        fc_part[["stagione", "trasferta_id", "trasferta"]].rename(
            columns={"trasferta_id": "id", "trasferta": "nome"})])
        .drop_duplicates().set_index(["stagione", "id"])["nome"])

    righe = []
    for stagione in stagioni:
        a = _firme_ws(ws[ws["stagione"] == stagione])
        b = _firme_fc(fc_part[fc_part["stagione"] == stagione])
        for id_fc, firma_fc in sorted(b.items()):
            punteggi = sorted(((len(firma_ws & firma_fc), id_ws)
                               for id_ws, firma_ws in a.items()), reverse=True)
            (primo, id_ws), (secondo, _) = punteggi[0], punteggi[1]
            if primo == secondo:
                raise AggancioAmbiguo(
                    f"{stagione}: la squadra fantacalcio {id_fc} "
                    f"({nomi_fc.get((stagione, id_fc))}) ha due candidati "
                    f"WhoScored a pari punteggio ({primo}/38)"
                )
            righe.append({
                "stagione": stagione,
                "teamId_ws": id_ws,
                "nome_ws": nomi_ws.get((stagione, id_ws)),
                "squadra_id_fc": id_fc,
                "nome_fc": nomi_fc.get((stagione, id_fc)),
                "partite_ws": len(a[id_ws]),
                "partite_fc": len(firma_fc),
                "in_comune": primo,
                "margine": primo - secondo,
            })

    out = pd.DataFrame(righe)
    # Deve essere una biiezione dentro ogni stagione: se due squadre fantacalcio
    # finissero sulla stessa WhoScored, una delle due sarebbe agganciata male e
    # tutti i suoi voti finirebbero sui minuti di un'altra.
    dup = out.groupby(["stagione", "teamId_ws"]).size()
    if (dup > 1).any():
        raise AggancioAmbiguo(f"aggancio squadre non biunivoco:\n{dup[dup > 1]}")
    return out.sort_values(["stagione", "nome_fc"]).reset_index(drop=True)


# --------------------------------------------------------------------------
# Partite
# --------------------------------------------------------------------------

def mappa_partite(squadre: pd.DataFrame = None, stagioni=None) -> dict:
    """Aggancia le partite sulla coppia **ordinata** di squadre.

    Restituisce `{"partite": ..., "solo_ws": ..., "solo_fc": ...}`. I due
    residui non sono scarti: sono il conto di cio' che una fonte ha e l'altra no,
    e vanno guardati prima di qualunque media — e' la lezione dell'acquisizione
    WhoScored, dove l'Atalanta perdeva 6 partite su 38 e il denominatore assunto
    l'avrebbe nascosto.
    """
    squadre = mappa_squadre(stagioni) if squadre is None else squadre
    stagioni = stagioni or config.SEASONS_STORICHE
    ws = pd.read_parquet(FILE_WS)
    ws = ws[ws["stagione"].isin(stagioni)]
    fc = pd.read_parquet(V.PARTITE_PARQUET)
    fc = fc[fc["stagione"].isin(stagioni)]

    verso = squadre.set_index(["stagione", "teamId_ws"])["squadra_id_fc"]
    ws = ws.assign(
        casa_fc=[verso.get((s, int(t))) for s, t in zip(ws["stagione"], ws["teamId_casa"])],
        trasferta_fc=[verso.get((s, int(t)))
                      for s, t in zip(ws["stagione"], ws["teamId_ospite"])],
    )

    unite = fc.merge(
        ws[["stagione", "matchId", "data", "casa_fc", "trasferta_fc",
            "teamId_casa", "teamId_ospite"]].rename(columns={"data": "data_ws"}),
        left_on=["stagione", "casa_id", "trasferta_id"],
        right_on=["stagione", "casa_fc", "trasferta_fc"],
        how="outer", indicator=True,
    )

    solo_fc = unite[unite["_merge"] == "left_only"].copy()
    solo_ws = unite[unite["_merge"] == "right_only"].copy()
    ok = unite[unite["_merge"] == "both"].copy()
    ok["scarto_giorni"] = (ok["data_ws"] - ok["data"]).dt.days.abs()

    # La coppia ordinata e' unica *quasi* sempre: nel 2022-23 Spezia-Verona
    # compare due volte lato WhoScored, la giornata 25 e lo spareggio salvezza.
    # Senza questa riga la giornata 25 si aggancerebbe a **entrambe**, e una
    # partita di giugno finirebbe sotto i voti di marzo. Vince la data piu'
    # vicina; l'altra non e' scartata, va fra le partite senza voti.
    ok = ok.sort_values("scarto_giorni")
    doppie = ok.duplicated(subset=["stagione", "partita_id"], keep="first")
    scartate = ok[doppie]
    ok = ok[~doppie]
    solo_ws = pd.concat([solo_ws, scartate], ignore_index=True)

    return {
        "partite": ok.drop(columns=["_merge", "casa_fc", "trasferta_fc"])
                     .sort_values(["stagione", "giornata", "data"])
                     .reset_index(drop=True),
        "solo_fc": solo_fc[["stagione", "giornata", "partita_id", "casa",
                            "trasferta", "data"]].reset_index(drop=True),
        "solo_ws": solo_ws[["stagione", "matchId", "data_ws",
                            "teamId_casa", "teamId_ospite"]].reset_index(drop=True),
    }


# --------------------------------------------------------------------------
# Giocatori
# --------------------------------------------------------------------------

# Lettere che la decomposizione Unicode NON piega. `NFKD` separa i segni
# combinanti — `é` diventa `e` piu' un accento, che l'ASCII butta via — ma `ø`,
# `æ`, `å`, `ð`, `þ`, `ł`, `đ` sono **lettere a se'**, non composizioni. Senza
# questa tabella `Højlund` diventa `hjlund` e non trova nessuno: e' uno dei 23
# casi su 609 che il cognome grezzo sbaglia. La resa e' quella d'uso corrente
# nelle rispettive lingue.
TRASLITTERA = str.maketrans({
    "ø": "o", "Ø": "o", "æ": "ae", "Æ": "ae", "å": "a", "Å": "a",
    "ð": "d", "Ð": "d", "þ": "th", "Þ": "th", "ß": "ss",
    "đ": "d", "Đ": "d", "ł": "l", "Ł": "l", "ı": "i", "ħ": "h",
    "œ": "oe", "Œ": "oe", "ŋ": "n",
})


def _normalizza(nome: str) -> list[str]:
    """Nome -> parole minuscole, senza segni e senza apostrofi.

    L'apostrofo diventa spazio e non sparisce: `N'Dri` e `N´Dri` sono la stessa
    persona scritta con due caratteri diversi, e solo separando si arriva alla
    stessa forma. Il confronto poi guarda **anche** la versione attaccata, che e'
    l'unica che riconcilia `N Dri` con `NDri`.
    """
    import re
    import unicodedata

    s = str(nome).translate(TRASLITTERA)
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()
    return [p for p in re.sub(r"[^a-z]+", " ", s).split() if p]


def _scomponi_fc(nome: str) -> tuple[list[str], list[str]]:
    """`"Esposito F.P."` -> `(["esposito"], ["f", "p"])`.

    Le iniziali sono i pezzi **abbreviati** del nome proprio, che la fonte
    aggiunge in coda solo quando il cognome da solo sarebbe ambiguo. Si
    riconoscono dal punto nel testo originale, non dalla lunghezza: `Jo.` e
    `Lu.` sono abbreviazioni di due lettere, e un criterio sulla lunghezza le
    confonderebbe con i cognomi corti veri.
    """
    cognome, iniziali = [], []
    for pezzo in str(nome).split():
        if pezzo.endswith("."):
            iniziali += _normalizza(pezzo.replace(".", " "))
        else:
            cognome += _normalizza(pezzo)
    return cognome, iniziali


def _candidati(cognome: list[str], nomi_ws: dict[int, str]) -> list[int]:
    """Chi, nella rosa, porta questo cognome.

    Due prove, e basta che passi una: i pezzi del cognome sono **contenuti**
    nelle parole del nome WhoScored (`anguissa` dentro `Andre Frank Zambo
    Anguissa`), oppure il cognome **attaccato** e' una sottostringa del nome
    attaccato (`ndri` dentro `konanndri`). La seconda esiste per gli apostrofi e
    per i cognomi che una fonte scrive unito e l'altra staccato.
    """
    if not cognome:
        return []
    attaccato = "".join(cognome)
    fuori = []
    for id_ws, nome in nomi_ws.items():
        pezzi = _normalizza(nome) if nome is not None and pd.notna(nome) else []
        if not pezzi:
            continue
        if set(cognome) <= set(pezzi) or attaccato in "".join(pezzi):
            fuori.append(id_ws)
    return fuori


def mappa_giocatori(stagione: str = STAGIONE_CON_ENTRAMBE) -> dict:
    """Aggancia i giocatori dentro ogni squadra. Chiave: il cognome.

    Tre passaggi, in quest'ordine, e ognuno interviene solo se il precedente
    lascia piu' di un candidato:

    1. **il cognome normalizzato** dentro la rosa della squadra — risolve 586
       giocatori su 609 da solo;
    2. **le iniziali del nome proprio**, che la fonte dei voti mette in coda solo
       quando servono (`Martinez L.` contro `Martinez Jo.`) — risolvono i due
       cognomi ambigui rimasti;
    3. **il calendario**, come ultimo spareggio: fra due omonimi perfetti vince
       chi condivide piu' partite.

    Il calendario non e' la chiave, e la ragione sta nella docstring del modulo:
    dentro una squadra l'insieme delle presenze e' quasi pieno, quindi due
    titolari qualsiasi si somigliano piu' di quanto un giocatore somigli a se'
    stesso visto dall'altra fonte.

    **Il lato WhoScored e' ristretto a chi ha giocato almeno un minuto.** Senza
    il filtro la rosa candidata sarebbe di 803 nomi invece di 609, perche'
    `player_match` tiene anche i panchinari non utilizzati (5.846 righe a zero
    minuti). Includerli non aggiungerebbe nessun aggancio giusto — i voti quei
    giocatori non li elencano — e in compenso creerebbe omonimie evitabili.
    """
    part = mappa_partite(stagioni=[stagione])["partite"]
    da_fc = part.set_index("partita_id")["matchId"].to_dict()

    fc = V.carica()
    fc = fc[(fc["stagione"] == stagione) & (~fc["allenatore"])].copy()
    fc["matchId"] = fc["partita_id"].map(da_fc)
    ws = pd.read_parquet(config.PLAYER_MATCH)
    ws = ws[ws["minutes"] > 0]

    squadre = mappa_squadre([stagione])
    verso_ws = squadre.set_index(["stagione", "squadra_id_fc"])["teamId_ws"]
    fc["teamId_ws"] = [verso_ws.get((stagione, int(t))) for t in fc["squadra_id"]]

    pres_fc = fc.groupby(["teamId_ws", "giocatore_id"]).agg(
        nome_fc=("giocatore", "first"), ruolo_fc=("ruolo", "first"),
        partite=("matchId", lambda s: frozenset(s.dropna())))
    pres_ws = ws.groupby(["teamId", "playerId"]).agg(
        nome_ws=("playerName", "first"), ruolo_ws=("role", "first"),
        partite=("matchId", lambda s: frozenset(s)))

    righe, irrisolti = [], []
    for team in sorted(pres_fc.index.get_level_values(0).unique()):
        blocco_fc = pres_fc.loc[team]
        if team not in pres_ws.index.get_level_values(0):
            continue
        blocco_ws = pres_ws.loc[team]
        nomi_ws = blocco_ws["nome_ws"].to_dict()

        for id_fc, r_fc in blocco_fc.iterrows():
            cognome, iniziali = _scomponi_fc(r_fc["nome_fc"])
            cand = _candidati(cognome, nomi_ws)
            passo = "cognome"

            if not cand and len(cognome) > 1:
                # Cognome composto che le due fonti accorciano in modo diverso:
                # `Zambo Anguissa` contro `Frank Anguissa`, dove `Zambo` e'
                # patronimico per una fonte e nome proprio per l'altra. Si
                # ripiega sull'ultimo pezzo, che e' quello che regge sempre —
                # ma il ripiego resta scritto nella colonna `risolto_da`,
                # perche' e' la regola piu' debole delle quattro.
                cand = _candidati(cognome[-1:], nomi_ws)
                passo = "cognome parziale"

            if len(cand) > 1 and iniziali:
                # Le iniziali guardano il nome PROPRIO, cioe' i pezzi del nome
                # WhoScored che non sono il cognome: `Jo.` deve pescare `Josep`
                # e non `Josep Martinez` per intero.
                stretti = [c for c in cand
                           if _iniziali_compatibili(iniziali, nomi_ws[c], cognome)]
                if len(stretti) == 1:
                    cand, passo = stretti, "cognome + iniziali"
                elif stretti:
                    cand = stretti

            if len(cand) > 1:
                per_calendario = sorted(
                    ((len(r_fc["partite"] & blocco_ws.loc[c, "partite"]), c) for c in cand),
                    reverse=True)
                if per_calendario[0][0] > per_calendario[1][0]:
                    cand, passo = [per_calendario[0][1]], "calendario"

            voce = {
                "stagione": stagione, "teamId_ws": int(team),
                "giocatore_id_fc": int(id_fc), "nome_fc": r_fc["nome_fc"],
                "ruolo_fc": r_fc["ruolo_fc"], "presenze_fc": len(r_fc["partite"]),
            }
            if len(cand) != 1:
                irrisolti.append({**voce, "candidati": len(cand),
                                  "nomi_candidati": "; ".join(str(nomi_ws[c]) for c in cand),
                                  "motivo": "nessun candidato" if not cand
                                            else "cognome ambiguo"})
                continue

            id_ws = cand[0]
            r_ws = blocco_ws.loc[id_ws]
            unione = len(r_fc["partite"] | r_ws["partite"])
            j = len(r_fc["partite"] & r_ws["partite"]) / unione if unione else 0.0
            righe.append({**voce, "playerId_ws": int(id_ws), "nome_ws": r_ws["nome_ws"],
                          "ruolo_ws": r_ws["ruolo_ws"], "presenze_ws": len(r_ws["partite"]),
                          "risolto_da": passo, "jaccard": round(j, 4)})

    mappa = pd.DataFrame(righe)
    if not mappa.empty:
        # Due giocatori dei voti sullo stesso WhoScored: uno dei due e' sbagliato
        # e non sappiamo quale, quindi si tolgono **entrambi**. Tenere "il
        # migliore" significherebbe scegliere, ed e' cio' che il progetto non fa.
        dup = mappa.groupby(["teamId_ws", "playerId_ws"]).size()
        contesi = set(dup[dup > 1].index)
        maschera = [(t, p) in contesi for t, p in
                    zip(mappa["teamId_ws"], mappa["playerId_ws"])]
        if any(maschera):
            irrisolti += mappa[maschera].assign(
                motivo="due giocatori dei voti sullo stesso WhoScored").to_dict("records")
            mappa = mappa[[not m for m in maschera]]

    return {"mappa": mappa.reset_index(drop=True),
            "irrisolti": pd.DataFrame(irrisolti)}


def _iniziali_compatibili(iniziali: list[str], nome_ws: str, cognome: list[str]) -> bool:
    """`["jo"]` contro `Josep Martinez` -> vero; contro `Lautaro Martinez` -> falso.

    Il confronto e' un **prefisso**, non un'uguaglianza: `Lu.` sta per `Luca` e
    `F.P.` per `Francesco Pio`. E guarda solo i pezzi che non sono il cognome,
    altrimenti `Se.` di `Esposito Se.` troverebbe da solo `Esposito`.
    """
    pezzi = [p for p in _normalizza(nome_ws) if p not in set(cognome)]
    return all(any(p.startswith(i) for p in pezzi) for i in iniziali)


def _cognomi_in_comune(nome_fc: str, nome_ws: str) -> bool:
    """`Martinez L.` contro `Lautaro Martinez`: il cognome sta in entrambi.

    Confronto volutamente grossolano — minuscole, niente accenti, niente
    iniziali puntate — perche' serve solo a spareggiare, mai a decidere da solo.
    """
    import unicodedata

    def pezzi(s):
        s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode()
        return {p.strip(".").lower() for p in s.replace("'", " ").split()
                if len(p.strip(".")) > 2}

    return bool(pezzi(nome_fc) & pezzi(nome_ws))
