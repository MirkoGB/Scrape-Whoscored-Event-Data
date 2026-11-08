# -*- coding: utf-8 -*-
"""Fase 15 / C1 — il calendario della stagione in corso, da DUE fonti.

Le due fonti non sono ridondanti: portano cose diverse, e nessuna delle due da
sola basta.

| | WhoScored | Wikipedia |
|---|---|---|
| URL e `matchId` | **si** | no |
| data della partita | **si** | solo a volte (`rowspan`) |
| **giornata di campionato** | **NO** | **si** |
| copertura 2026-2027 | completa | variabile per campionato |

**Che la giornata manchi a WhoScored non e' un dettaglio**: si naviga per
GIORNO, e la giornata di campionato non compare da nessuna parte. E' lo stesso
fatto che il Blocco 0 aveva misurato su `matches.json` e che ha costretto R3 a
prenderla dall'aggancio della Fase 8 — che pero' esiste solo per la Serie A e
solo per le cinque stagioni storiche, cioe' non per la stagione in corso.

IL NOME NON E' UNA CHIAVE
-------------------------
Al livello di squadra il nome **non e' una chiave**, ed e' la lezione della
Fase 8: li' `AC Milan` contro `Milan` e `Parma Calcio 1913` contro `Parma`
avevano gia' impedito di agganciare due fonti per nome. Qui succede lo stesso, e
`mappa_squadre()` lo risolve in tre passi con una **verifica** alla fine:

1. corrispondenza esatta (18 su 20 in Serie A);
2. contenimento, se e solo se e' **unico** — un nome contenuto in due nomi
   diversi e' ambiguo e solleva invece di scegliere;
3. si pretende una **biiezione su tutte** le squadre. Una mappa parziale che
   coprisse 19 su 20 farebbe sparire in silenzio le partite della ventesima.

**Se la verifica non passa, non si riconcilia niente.** Un calendario a cui
manchi una squadra e' peggio di nessun calendario, perche' sembra completo.

CHE COSA QUESTO MODULO NON FA
-----------------------------
**Non sceglie fra le due fonti dove divergono**: le mette a verbale
(`divergenze()`). E' il vincolo 7 — due nomi per la stessa grandezza non sono la
stessa grandezza finche' non e' misurato che lo siano — e la Fase 11 lo ha gia'
applicato a un calendario, rifiutando tre fonti su quattro.
"""

from __future__ import annotations

import json

import pandas as pd

from . import config

#: La fonte primaria delle PARTITE: porta URL e `matchId`, che sono cio' che
#: serve a scaricare gli eventi. La giornata non ce l'ha.
FONTE_PARTITE = "whoscored"

#: La fonte della GIORNATA. Non porta URL, quindi non puo' sostituire l'altra.
FONTE_GIORNATA = "wikipedia"


def _leggi(percorso):
    if not percorso.is_file():
        return None
    return json.loads(percorso.read_text(encoding="utf-8"))


def carica_whoscored(league: str | None = None,
                     season: str | None = None) -> pd.DataFrame:
    """Le partite ancora da giocare secondo WhoScored, con URL e `matchId`."""
    league = config.LEAGUE if league is None else league
    season = config.SEASON_CORRENTE if season is None else season
    d = _leggi(config.calendario_json(league, season))
    if d is None:
        return pd.DataFrame()
    righe = pd.DataFrame(d["righe"])
    if righe.empty:
        return righe
    righe["campionato"] = league
    righe["stagione"] = season
    # il `matchId` sta nell'URL, ed e' l'unico modo di legarsi agli eventi
    righe["matchId"] = righe["url"].str.extract(r"/matches/(\d+)/")[0]
    return righe.rename(columns={"home": "casa", "away": "trasferta",
                                 "date": "data_fonte"})


def carica_wikipedia(league: str | None = None,
                     season: str | None = None) -> pd.DataFrame:
    """Il calendario di Wikipedia, con la giornata."""
    from acquisition.wikipedia import target as WT

    league = config.LEAGUE if league is None else league
    season = config.SEASON_CORRENTE if season is None else season
    d = _leggi(WT.percorso(league, season))
    if d is None:
        return pd.DataFrame()
    righe = pd.DataFrame(d["righe"])
    if not righe.empty:
        righe["campionato"] = league
        righe["stagione"] = season
    return righe


#: Gli **esonimi**: nomi che le due fonti scrivono in due lingue diverse, e che
#: nessuna regola tipografica puo' riconciliare. Wikipedia italiana traduce
#: (`Siviglia`, `Barcellona`) e abbrevia in modo suo (`Manchester Utd`), mentre
#: WhoScored tiene il nome locale o inglese.
#:
#: **Sono dichiarati, non dedotti**, come `soglie_2627.NOMI_FONTE`: una mappa di
#: nomi e' informazione esterna, e va scritta dove si vede. La chiave e' il nome
#: **Wikipedia**, il valore quello **WhoScored**, che e' la forma che vince
#: perche' e' quella dei dati evento.
#:
#: L'elenco e' volutamente **corto**: tutto cio' che si risolve da solo — accenti
#: e sigle contenute — passa da `_normalizza` e dal contenimento, e non va
#: messo qui. Una mappa lunga sarebbe una mappa che nasconde una regola mancante.
NOMI_FONTE = {
    "ENG-premier-league": {"Manchester Utd": "Manchester United"},
    # Wikipedia italiana traduce quasi ogni citta' tedesca: qui gli
    # esonimi sono la regola e non l'eccezione, ed e' una proprieta'
    # dell'accoppiata di fonti, non una regola mancante.
    "GER-bundesliga": {
        'Amburgo': 'Hamburger SV',
        'Augusta': 'Augsburg',
        'Bayern Monaco': 'Bayern Munich',
        "Borussia M'gladbach": 'Borussia M.Gladbach',
        'Colonia': 'FC Koln',
        'Eintracht Francoforte': 'Eintracht Frankfurt',
        'Friburgo': 'Freiburg',
        'Magonza': 'Mainz 05',
        'RB Lipsia': 'RB Leipzig',
        'Stoccarda': 'VfB Stuttgart',
        'Werder Brema': 'Werder Bremen',
    },
    # Anche il francese: Wikipedia italiana traduce le citta'.
    "FRA-ligue-1": {
        'Lilla': 'Lille',
        'Nizza': 'Nice',
        'Olympique Lione': 'Lyon',
        'Olympique Marsiglia': 'Marseille',
        'Strasburgo': 'Strasbourg',
        'Tolosa': 'Toulouse',
    },
    "ESP-la-liga": {
        "Athletic Bilbao": "Athletic Club",
        "Barcellona": "Barcelona",
        "Siviglia": "Sevilla",
        'Deportivo A Coruña': 'Deportivo de A Coruna',
    },
}


def _normalizza(nome: str) -> str:
    """Minuscolo, senza accenti, spazi normalizzati.

    Serve al **contenimento**, non all'aggancio esatto: `Alavés` e `Alaves` sono
    la stessa squadra scritta da due tastiere diverse, e trattarli come nomi
    diversi costringerebbe a dichiarare come esonimo cio' che e' solo un accento.
    E' la stessa distinzione che l'aggancio della Fase 8 ha dovuto fare fra
    `Hojlund` e `Hoglund`: li' pero' l'accento **distingueva** due persone, qui
    no, e la differenza sta nel fatto che qui l'insieme e' chiuso e verificato.
    """
    import unicodedata

    piatto = unicodedata.normalize("NFKD", nome or "")
    piatto = "".join(c for c in piatto if not unicodedata.combining(c))
    return " ".join(piatto.lower().split())


def squadre_wikipedia(league: str | None = None,
                      season: str | None = None) -> list[str]:
    """Le squadre partecipanti **dichiarate dalla pagina**, non quelle viste.

    E' la differenza che ha fatto fallire la riconciliazione di Premier e Liga
    alla prima prova: su una pagina parziale le squadre che compaiono nelle
    righe sono meno di venti, e confrontare quell'insieme con i venti di
    WhoScored dava "numero diverso di squadre" su una fonte che invece li ha
    tutti. L'elenco dei partecipanti c'e' anche quando il calendario e' a meta'.
    """
    from acquisition.wikipedia import target as WT

    league = config.LEAGUE if league is None else league
    season = config.SEASON_CORRENTE if season is None else season
    d = _leggi(WT.percorso(league, season))
    return list(d.get("squadre", [])) if d else []


def mappa_squadre(nomi_partite, nomi_giornata, league: str | None = None) -> dict:
    """Da nome Wikipedia a nome WhoScored, **verificata biiettiva**.

    Solleva invece di restituire una mappa parziale: e' la differenza fra un
    calendario incompleto e uno che *sembra* completo.
    """
    a = sorted(set(nomi_partite))          # WhoScored: e' la forma che vince
    b = sorted(set(nomi_giornata))         # Wikipedia
    if len(a) != len(b):
        raise ValueError(
            f"le due fonti vedono un numero diverso di squadre: {len(a)} contro "
            f"{len(b)}. Solo in {sorted(set(a) - set(b))}, solo in "
            f"{sorted(set(b) - set(a))}"
        )

    esonimi = NOMI_FONTE.get(league or "", {})
    mappa, presi = {}, set()
    for n in b:                            # 1. esonimi DICHIARATI
        if n in esonimi and esonimi[n] in a:
            mappa[n] = esonimi[n]
            presi.add(esonimi[n])
    for n in b:                            # 2. esatti
        if n not in mappa and n in a and n not in presi:
            mappa[n] = n
            presi.add(n)
    for n in b:                            # 3. contenimento, se UNICO
        if n in mappa:
            continue
        nn = _normalizza(n)
        cand = [x for x in a if x not in presi
                and (nn in _normalizza(x) or _normalizza(x) in nn)]
        if len(cand) != 1:
            raise ValueError(
                f"{n!r} non si aggancia a una sola squadra: {cand or 'nessuna'}. "
                "Un nome contenuto in due nomi diversi e' ambiguo, e sceglierne "
                "uno produrrebbe un calendario plausibile e sbagliato."
            )
        mappa[n] = cand[0]
        presi.add(cand[0])

    if len(mappa) != len(b) or len(set(mappa.values())) != len(a):
        raise ValueError(
            f"la mappa non e' biiettiva: {len(mappa)} voci, "
            f"{len(set(mappa.values()))} destinazioni, {len(a)} squadre"
        )
    return mappa


def calendario(league: str | None = None, season: str | None = None,
               solo_da_giocare: bool = True) -> pd.DataFrame:
    """Le partite da giocare, con la **giornata** attaccata dove si riesce.

    Il perimetro e' quello di WhoScored — e' la fonte che ha gli URL — e
    Wikipedia entra solo per **aggiungere una colonna**. Se manca, o se i nomi
    non si riconciliano, si ritorna lo stesso il calendario **senza** giornata e
    lo si dichiara nella colonna `fonte_giornata`: una giornata mancante e' un
    limite, una giornata inventata e' un difetto.
    """
    ws = carica_whoscored(league, season)
    if ws.empty:
        return ws

    ws["giornata"] = pd.NA
    ws["fonte_giornata"] = "assente"

    wk = carica_wikipedia(league, season)
    if not wk.empty:
        try:
            mappa = mappa_squadre(
                set(ws["casa"]) | set(ws["trasferta"]),
                set(squadre_wikipedia(league, season)),
                league=league)
        except ValueError:
            mappa = None
        if mappa is not None:
            wk = wk.assign(casa=wk["casa"].map(mappa),
                           trasferta=wk["trasferta"].map(mappa))
            # Una coppia (casa, trasferta) dovrebbe essere unica in una
            # stagione di andata e ritorno, ed e' la chiave del join. **Dove non
            # lo e', si tolgono TUTTE le copie invece di sceglierne una**: in
            # Ligue 1 esistono partite rinviate che la fonte elenca sia alla
            # giornata originale sia a quella di recupero, e non c'e' modo di
            # sapere quale sia quella buona. Una coppia ambigua resta **senza
            # giornata**, che e' un limite; una giornata scelta a caso sarebbe
            # un difetto.
            #
            # La prima stesura, trovando un solo doppione, saltava **l'intero
            # aggancio**: la Ligue 1 usciva con zero giornate su 288 per via di
            # tre rinvii. Una guardia troppo grossolana costa quanto una assente.
            univoche = wk.drop_duplicates(subset=["casa", "trasferta"],
                                          keep=False)
            scartate = len(wk) - len(univoche)
            if len(univoche):
                g = univoche.set_index(["casa", "trasferta"])["giornata"]
                idx = pd.MultiIndex.from_frame(ws[["casa", "trasferta"]])
                trovate = g.reindex(idx).to_numpy()
                ws["giornata"] = trovate
                ws["fonte_giornata"] = [
                    FONTE_GIORNATA if pd.notna(x) else "assente" for x in trovate]
                ws.attrs["coppie_ambigue_scartate"] = int(scartate)

    if solo_da_giocare and "giocata" in ws.columns:
        ws = ws[~ws["giocata"].fillna(False)]
    return ws.reset_index(drop=True)


def divergenze(league: str | None = None,
               season: str | None = None) -> dict:
    """Che cosa le due fonti dicono di diverso. **Si dichiara, non si sceglie.**"""
    ws = carica_whoscored(league, season)
    wk = carica_wikipedia(league, season)
    fuori = {"campionato": league or config.LEAGUE,
             "partite_whoscored": int(len(ws)),
             "righe_wikipedia": int(len(wk))}
    if ws.empty or wk.empty:
        fuori["confrontabili"] = False
        return fuori

    try:
        mappa = mappa_squadre(set(ws["casa"]) | set(ws["trasferta"]),
                              set(squadre_wikipedia(league, season)),
                              league=league)
        fuori["squadre_riconciliate"] = len(mappa)
        fuori["nomi_diversi"] = {k: v for k, v in mappa.items() if k != v}
    except ValueError as e:
        fuori["confrontabili"] = False
        fuori["perche"] = str(e)[:300]
        return fuori

    wk2 = wk.assign(casa=wk["casa"].map(mappa),
                    trasferta=wk["trasferta"].map(mappa))
    a = set(zip(ws["casa"], ws["trasferta"]))
    b = set(zip(wk2["casa"], wk2["trasferta"]))
    fuori["confrontabili"] = True
    fuori["comuni"] = len(a & b)
    fuori["solo_whoscored"] = sorted(f"{c}-{t}" for c, t in (a - b))[:12]
    fuori["solo_wikipedia"] = sorted(f"{c}-{t}" for c, t in (b - a))[:12]
    fuori["n_solo_whoscored"] = len(a - b)
    fuori["n_solo_wikipedia"] = len(b - a)
    return fuori


def coerenza_fonti(league: str | None = None,
                   season: str | None = None) -> dict:
    """Una partita non puo' essere insieme **giocata** e **da giocare**.

    E' il controllo piu' semplice del blocco ed e' quello che ha trovato il
    difetto piu' vecchio: `matches.json` e `calendario.json` non devono avere
    nessun URL in comune, perche' il primo porta le partite giocate e il secondo
    quelle da giocare.

    **Ha trovato `Ipswich-Liverpool`** nella Premier 2026-2027, presente in
    entrambi con punteggio `-:-`. La causa non era il calendario: era il criterio
    con cui lo scraper decideva che una partita fosse giocata, che cercava la
    sottostringa `'live'` nell'href — e `'live'` **sta dentro `'liverpool'`**.
    Ogni partita del Liverpool passava il filtro anche se non giocata. Il criterio
    accertato (`'/live/'`, con le barre) non ci cade, ma le righe gia' scritte in
    `matches.json` restano: la cache si rinfresca sommando, non sostituendo.
    """
    league = config.LEAGUE if league is None else league
    season = config.SEASON_CORRENTE if season is None else season

    giocate = _leggi(config.matches_json(league, season)) or []
    futuro = _leggi(config.calendario_json(league, season))
    righe = (futuro or {}).get("righe", [])

    u_gio = {r.get("url") for r in giocate}
    u_fut = {r.get("url") for r in righe}
    comuni = sorted(u_gio & u_fut)

    # una riga di `matches.json` il cui URL non e' `/live/` non e' una partita
    # giocata: e' il difetto di cui sopra, e si conta a parte
    non_live = sorted(u for u in u_gio if u and "/live/" not in u)

    return {
        "campionato": league,
        "stagione": season,
        "giocate": len(u_gio),
        "da_giocare": len(u_fut),
        "totale": len(u_gio) + len(u_fut),
        "in_entrambi": comuni,
        "coerente": not comuni and not non_live,
        "in_matches_json_senza_live": non_live,
    }


# --------------------------------------------------------------------------
# La data, e il TURNO - Fase 15 / P1
# --------------------------------------------------------------------------
#: I mesi come WhoScored li scrive **in italiano**: il sito serve
#: `it.whoscored.com` (accertato in C1), quindi la data e' `dic` e non `dec`.
#:
#: **Nove dei dodici sono osservati** nei calendari raccolti - `apr dic feb gen
#: mag mar nov ott set` - e i tre che mancano (`giu lug ago`) non compaiono
#: perche' `calendario.json` contiene le sole partite DA GIOCARE, e a settembre
#: agosto e' gia' passato. Sono dichiarati lo stesso completando la serie: un
#: calendario a cui manchi un mese produrrebbe righe senza data, cioe' un turno
#: <<data ignota>> al posto di uno vero. La distinzione fra osservato e
#: completato sta in `MESI_OSSERVATI`, cosi' che non si perda.
MESI = {"gen": 1, "feb": 2, "mar": 3, "apr": 4, "mag": 5, "giu": 6,
        "lug": 7, "ago": 8, "set": 9, "ott": 10, "nov": 11, "dic": 12}

#: Quali dei dodici sono stati visti davvero nei dati (2026-2027, cinque
#: campionati). Gli altri tre sono completamento della serie, non misura.
MESI_OSSERVATI = ("apr", "dic", "feb", "gen", "mag", "mar", "nov", "ott", "set")

#: La forma della data, **accertata** su tutte le righe di tutti e cinque i
#: calendari: zero righe non conformi. Non e' un'ipotesi sul markup.
FORMA_DATA = "<giorno della settimana>, <mese abbreviato> <gg> <aaaa>"

_GIORNI_BREVI = ("lun", "mar", "mer", "gio", "ven", "sab", "dom")


def data(testo) -> pd.Timestamp | None:
    """La data di una riga di calendario WhoScored, o `None` se non si legge.

    **Ritorna `None` invece di sollevare**, e la differenza conta: una riga con
    la data illeggibile e' un limite di quella riga - finisce in un turno
    dichiarato <<data ignota>> - mentre sollevare farebbe sparire l'intero
    calendario di un campionato per una cella storta. Le righe senza data si
    **contano**, come i denominatori di E0.
    """
    if not isinstance(testo, str):
        return None
    pezzi = testo.split(",")
    if len(pezzi) != 2:
        return None
    campi = pezzi[1].split()
    if len(campi) != 3:
        return None
    mese, giorno, anno = campi
    if mese.lower() not in MESI:
        return None
    try:
        return pd.Timestamp(int(anno), MESI[mese.lower()], int(giorno))
    except ValueError:
        return None


def _etichetta_giorno(t: pd.Timestamp) -> str:
    """`sab 12 set`. Costruita a mano e non con `strftime`: i nomi che
    `strftime` produce dipendono dal `locale` della macchina, quindi la stessa
    pagina uscirebbe in inglese su un PC configurato diversamente."""
    inv = {v: k for k, v in MESI.items()}
    return f"{_GIORNI_BREVI[t.weekday()]} {t.day} {inv[t.month]}"


#: Quanti giorni di stacco aprono un turno nuovo, quando la giornata non c'e'.
#:
#: **E' una scelta di PRESENTAZIONE, non una soglia statistica**, e sta qui
#: dichiarata invece che sepolta nel generatore della pagina. Tre giorni perche'
#: una giornata di campionato si spalma su venerdi'-lunedi' (quattro giorni,
#: stacchi interni di uno) mentre fra un turno e il successivo passano almeno
#: tre giorni anche nei turni infrasettimanali. Non e' stata scelta guardando i
#: dati: un `argmax` su un raggruppamento non ha nemmeno un criterio da
#: massimizzare.
GIORNI_STACCO = 3

#: Le tre origini possibili di un turno, dalla piu' forte alla piu' debole. La
#: prima e' la giornata VERA di Wikipedia; la seconda e' una **deduzione** dalla
#: data, dichiarata come tale; la terza e' il ripiego puro. Vanno **scritte in
#: pagina**: un blocco di date non e' una giornata di campionato e non va
#: spacciato per tale.
FONTI_TURNO = ("giornata", "giornata dedotta dalla data", "blocco di date")


def con_turno(cal: pd.DataFrame) -> pd.DataFrame:
    """Aggiunge `data`, `turno`, `etichetta_turno` e `fonte_turno`.

    **La giornata vera vince dove c'e', riga per riga**, e i due ripieghi
    coprono solo le righe che non ce l'hanno: la decisione non e' per
    campionato, perche' altrimenti servirebbe una soglia (<<quante giornate
    bastano?>>) scelta guardando i dati. La Serie A ha la giornata su 360 righe
    su 360, la Liga su 11 su 350, e nessuno dei due casi vuole un parametro.

    I tre passi, e il secondo e' quello che rende leggibile il risultato:

    1. **la giornata della fonte**, dove c'e';
    2. **il contenimento nella finestra di date di una giornata, se e solo se e'
       unico.** E' la stessa disciplina di `mappa_squadre`, e serve perche'
       Wikipedia copre una giornata *in parte*: in Premier League una giornata
       arriva con 8 righe su 10, e senza questo passo le altre due finirebbero
       in un blocco separato lo stesso weekend - due turni dove ce n'e' uno.
       Se due finestre contengono la stessa data (succede con i rinvii, che la
       fonte elenca a due giornate) il caso e' **ambiguo e si scende al terzo
       passo**, invece di sceglierne una;
    3. **i blocchi di date**, per cio' che resta.

    **La deduzione non diventa mai la giornata della riga**: `fonte_giornata`
    resta `assente` e cambia solo il turno in cui la riga e' mostrata. Una
    giornata dedotta scritta nella colonna della giornata sarebbe la stessa cosa
    di inventarla.
    """
    out = cal.copy()
    if out.empty:
        for c in ("data", "turno", "etichetta_turno", "fonte_turno"):
            out[c] = pd.Series(dtype="object")
        return out

    out["data"] = [data(x) for x in out["data_fonte"]]
    out["turno"] = pd.NA
    out["etichetta_turno"] = pd.NA
    out["fonte_turno"] = pd.NA

    con_g = out["giornata"].notna()
    if con_g.any():
        g = out.loc[con_g, "giornata"].astype(int)
        out.loc[con_g, "turno"] = ["g" + str(x) for x in g]
        out.loc[con_g, "etichetta_turno"] = [f"{x}a giornata" for x in g]
        out.loc[con_g, "fonte_turno"] = FONTI_TURNO[0]

    resto = list(out.index[~con_g])

    # Passo 2: la finestra di date di ogni giornata gia' assegnata.
    finestre = {}
    for chiave in {out.at[i, "turno"] for i in out.index[con_g]}:
        date = [out.at[i, "data"] for i in out.index[con_g]
                if out.at[i, "turno"] == chiave and out.at[i, "data"] is not None]
        if date:
            finestre[chiave] = (min(date), max(date))

    # **La capienza di un turno e' strutturale, non una soglia**: in un
    # campionato a `n` squadre una giornata ha `n/2` partite, e un turno che ne
    # contenesse di piu' non e' una giornata. Senza questo vincolo la Ligue 1
    # usciva con una <<5a giornata>> da 12 partite su 18 squadre: i RINVII hanno
    # una data che cade dentro la finestra di un altro turno, e il contenimento
    # li tirava dentro. Le squadre si **contano**, mai si assumono venti.
    squadre = set(out["casa"]) | set(out["trasferta"])
    capienza = max(1, len(squadre) // 2)

    ancora = []
    candidati = {}
    for i in resto:
        d = out.at[i, "data"]
        if d is None:
            ancora.append(i)
            continue
        dentro = [k for k, (a, b) in finestre.items() if a <= d <= b]
        if len(dentro) == 1:
            candidati.setdefault(dentro[0], []).append(i)
        else:
            # due finestre contengono questa data: ambiguo, non si sceglie
            ancora.append(i)

    gia_dentro = {k: sum(1 for i in out.index[con_g] if out.at[i, "turno"] == k)
                  for k in finestre}
    for chiave, idx in candidati.items():
        if gia_dentro.get(chiave, 0) + len(idx) > capienza:
            # **si rifiutano TUTTI i candidati di quel turno**, non i primi che
            # ci stanno: quale sia la partita di troppo non e' sapibile, e
            # sceglierla per ordine di data sarebbe sceglierla a caso
            ancora.extend(idx)
            continue
        etichetta = next(out.at[j, "etichetta_turno"] for j in out.index[con_g]
                         if out.at[j, "turno"] == chiave)
        for i in idx:
            out.at[i, "turno"] = chiave
            out.at[i, "fonte_turno"] = FONTI_TURNO[1]
            out.at[i, "etichetta_turno"] = etichetta

    # Passo 3: i blocchi di date, su cio' che resta.
    senza_data = [i for i in ancora if out.at[i, "data"] is None]
    con_data = [i for i in ancora if out.at[i, "data"] is not None]
    con_data.sort(key=lambda i: out.at[i, "data"])

    # Un blocco si chiude per **due** motivi, e il secondo non e' cosmetico: a
    # meta' settimana le date si concatenano (ven -> dom -> mer -> sab, stacchi
    # sempre <= 3) e la Liga usciva con un unico blocco da 29 partite su dieci
    # giorni, cioe' tre giornate in un turno solo. La capienza `squadre/2` e' la
    # stessa costante strutturale del passo 2. **Il blocco resta dichiarato come
    # blocco di date**: chiuderlo alla capienza non lo rende una giornata, e la
    # pagina non deve chiamarlo cosi'.
    blocco, precedente, quanti = 0, None, 0
    for i in con_data:
        d = out.at[i, "data"]
        stacco = precedente is not None and (d - precedente).days > GIORNI_STACCO
        if stacco or quanti >= capienza:
            blocco += 1
            quanti = 0
        precedente = d
        quanti += 1
        out.at[i, "turno"] = "b" + str(blocco)
        out.at[i, "fonte_turno"] = FONTI_TURNO[2]

    for chiave in sorted({out.at[i, "turno"] for i in con_data}):
        idx = [i for i in con_data if out.at[i, "turno"] == chiave]
        date = sorted(out.at[i, "data"] for i in idx)
        a, b = _etichetta_giorno(date[0]), _etichetta_giorno(date[-1])
        for i in idx:
            out.at[i, "etichetta_turno"] = a if a == b else a + " - " + b

    for i in senza_data:
        out.at[i, "turno"] = "ignoto"
        out.at[i, "etichetta_turno"] = "data ignota"
        out.at[i, "fonte_turno"] = FONTI_TURNO[2]

    return out


def turni(league: str | None = None, season: str | None = None,
          cal: pd.DataFrame | None = None) -> pd.DataFrame:
    """Un turno per riga, in ordine di prima data. E' l'indice della pagina.

    L'ordine e' quello del **calendario**, non quello del numero di giornata:
    con i recuperi la 12a puo' giocarsi dopo la 13a, e ordinare per numero
    metterebbe in pagina un turno gia' passato in mezzo a quelli futuri.
    """
    c = con_turno(calendario(league, season) if cal is None else cal)
    if c.empty:
        return pd.DataFrame(columns=["turno", "etichetta", "fonte", "partite",
                                     "prima_data", "ultima_data"])
    righe = []
    for chiave, g in c.groupby("turno", dropna=False):
        date = [d for d in g["data"] if d is not None]
        righe.append({
            "turno": chiave,
            "etichetta": g["etichetta_turno"].iloc[0],
            "fonte": g["fonte_turno"].iloc[0],
            "partite": len(g),
            "prima_data": min(date) if date else pd.NaT,
            "ultima_data": max(date) if date else pd.NaT,
        })
    t = pd.DataFrame(righe)
    return t.sort_values(["prima_data", "turno"],
                         na_position="last").reset_index(drop=True)
