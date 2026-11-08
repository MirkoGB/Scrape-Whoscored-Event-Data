"""Fase 16 / Blocco O1 — la verifica PROSPETTICA delle prime due giornate.

Tutto cio' che questo repository ha validato e' **within-season** o
**retrospettivo**: il walk-forward di V1, il prior di A2 misurato su venti
transizioni gia' concluse, la trasferibilita' di F13 sui gol. Nessun numero
pubblicato era mai stato messo alla prova nel modo piu' severo che esista —
**previsione scritta prima, esito letto dopo**. La Fase 14 ha prodotto un
deliverable operativo (`reports/previsioni.html`) e nessuna misura di quanto
quel deliverable sbagli.

**Non c'e' niente da simulare: l'esclusione e' gia' avvenuta.** Le previsioni
stanno su disco dal 2026-08-30; il primo CSV di evento della 2026-2027 e' del
2026-09-03. Questo modulo non stima nessun modello predittivo nuovo: legge le
previsioni congelate, le rimette accanto ai candidati dichiarati da A2 e
**misura**.

Due cose vanno tenute separate, e la separazione e' il contenuto metodologico
del blocco:

1. **Che le previsioni precedano i dati** e' provato da due fatti indipendenti,
   e il secondo e' molto piu' forte del primo. Il `mtime` chiede di fidarsi di
   un orologio; la **riproducibilita'** no. `verifica_anteriorita` pretende
   entrambi: che il file sia piu' vecchio del primo evento, **e** che le sue
   colonne si riproducano da `prior_stagione.lam_dal_prior` applicato al fit
   della sola stagione precedente. Una previsione riproducibile da dati che
   finiscono a maggio 2026 non puo' contenere informazione sulle giornate 1-2
   **qualunque sia la data in cui il file e' stato scritto**.

2. **Che la previsione valutata sia quella che la regola dichiarata avrebbe
   fatto**, e non una variante costruita per l'occasione. `PS.REGOLA_DUE_REGIMI`
   prescrive `modello prec` sotto `config.BURN_IN_ROUND`, e le previsioni
   congelate **sono** `modello prec`: misurato, non assunto.

**«Giornata» e «prime due partite di squadra» sono due grandezze diverse** e
non si scambiano (vincolo 7). La giornata vera e' accertabile solo dove la
seconda fonte e' sana — cioe' sulla sola Serie A — e li' fa da **controllo
positivo** della regola di ripiego: `verifica_giornata` misura l'accordo, e
`ripiego_ammesso` si rifiuta di applicare il ripiego se l'accordo non e' stato
misurato da nessuna parte. Senza quel controllo, «ho valutato le prime due
giornate» non significherebbe niente.

Il modulo **non tocca la rete**, **non stima nessun modello predittivo nuovo** e
**non scrive niente sotto `data/`**. L'unica cosa che scrive e' il registro, ed
e' l'unico artefatto del blocco che non sia rigenerabile.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import numpy as np
import pandas as pd

from . import config
from . import prior_stagione as PS
from . import tentativi as T

# --------------------------------------------------------------------------
# Le costanti, dichiarate PRIMA di guardare i numeri
#
# Un test vieta `argmax`/`idxmax`/`quantile` nel codice di questo modulo, come
# per `tentativi.py` e `soglie_2627.py`: una soglia scelta guardando il campione
# su cui poi la si valuta e' il vincolo 1 violato nel punto in cui costa di piu'.
# --------------------------------------------------------------------------

#: La data in cui le previsioni sono state prodotte, cioe' il nome del registro.
#: **Non e' un parametro**: e' un fatto, e cambiarlo vorrebbe dire valutare un
#: altro file.
CONGELATE_AL = "2026-08-30"

#: Il perimetro: le prime DUE partite di ogni squadra. `team_match_idx` e'
#: l'indice cronologico di squadra, **non** la giornata — vedi
#: `verifica_giornata`, che e' il posto in cui la differenza si misura.
PERIMETRO_IDX_MAX = 2

#: La metrica primaria, scelta prima di vedere un numero. Le ragioni stanno
#: nella docstring di `validate.crps_conteggi`; qui sta la sola decisione.
METRICA_PRIMARIA = "CRPS"

BERSAGLI = ("shots", "sot")

#: I candidati, con gli stessi nomi di `PS.CANDIDATI` piu' l'oracolo. Tenere i
#: nomi di A2 non e' cosmesi: e' cio' che rende questo blocco leggibile accanto
#: a `reports/fase14_prior.md` invece che un secondo esperimento scollegato.
CANDIDATI = tuple(PS.CANDIDATI) + ("oracolo di livello",)

#: Il soggetto della verifica: e' cio' che la regola dichiarata avrebbe
#: pubblicato sotto il burn-in, ed e' cio' che il file congelato contiene.
SOGGETTO = "modello prec"

#: Il concorrente di riferimento, lo stesso di A2: «l'anno prossimo come l'anno
#: scorso», nella forma piu' semplice che esista.
RIFERIMENTO = "media squadra prec"

#: Quando il blocco puo' dire qualcosa e quando deve dichiarare di non
#: concludere. Scritto prima, applicato da `verdetto()` meccanicamente.
CRITERIO_LEGGIBILITA = (
    "un confronto CONCLUDE solo se |delta| / MDE >= 1, con il MDE clusterizzato "
    "per partita e a due code (la stessa forma di PS.mde_relativo, cioe' quella "
    "con cui A2 ha giudicato le stesse righe di avvio). Sotto 1 il blocco "
    "dichiara «il test non conclude», che NON e' «l'effetto non c'e'»."
)

#: Le due letture della giornata, tenute separate (vincolo 7).
FONTE_GIORNATA = "wikipedia"
RIPIEGO_GIORNATA = "team_match_idx <= 2 (indice cronologico di squadra)"

#: Come le colonne del file congelato si chiamano, per bersaglio.
COLONNA_LAMBDA = {"shots": "lambda_tentativi", "sot": "lambda_sot"}
COLONNA_R = {"shots": "r", "sot": "r_sot"}

#: Da quale colonna di `previsioni_avvio` viene ciascun candidato.
COLONNA_CANDIDATO = {
    "con prior": "lam_con_prior",
    "senza prior": "lam_senza_prior",
    "modello prec": "lam_modello_prec",
    "media squadra prec": "lam_media_squadra_prec",
    "media campionato prec": "lam_media_campionato_prec",
    "oracolo di livello": "lam_oracolo_livello",
}

#: Tolleranza della riproduzione, **derivata dall'ottimizzatore e non scelta
#: guardando lo scarto osservato** — che sarebbe far tornare un numero.
#:
#: Le due strade sono algebricamente la **stessa funzione**, e dentro un solo
#: processo coincidono a precisione macchina (scarto 0,0 esatto, misurato). Fra
#: due processi no, e la ragione e' che riprodurre vuol dire **rifare un fit
#: iterativo**: `TeamModel` chiama L-BFGS-B con `ftol = 1e-12` sull'obiettivo, e
#: vicino a un ottimo quadratico una tolleranza `f` sull'obiettivo vale circa
#: `sqrt(f)` sui parametri, cioe' ~1e-6 su `log(lambda)`. L'ordine delle somme
#: in BLAS multithread cambia gli ultimi bit del gradiente e sposta il punto di
#: arresto dentro quella tolleranza.
#:
#: Si ammette percio' `1e-5`, cioe' un ordine di grandezza sopra il limite che
#: l'ottimizzatore stesso dichiara. Su un lambda di ~12 tiri sono 1e-4 tiri:
#: cinque ordini di grandezza sotto qualunque cosa questo blocco misuri.
TOLL_RIPRODUZIONE = 1e-5

#: Repliche del bootstrap sui cluster. Stesso ordine di grandezza di
#: `precisione.rapporto_dispersioni`, da cui questa forma e' presa.
N_BOOT = 1000


# --------------------------------------------------------------------------
# §1 — il registro e la sua anteriorita'
# --------------------------------------------------------------------------
def percorso_congelate(league: str) -> Path:
    """Il file congelato, con la data NEL NOME.

    `run_previsioni.py --csv` riscrive `reports/previsioni_<L>.csv`
    sovrascrivendo e senza data, e l'aggiornamento automatico del martedi' e'
    attivo: una sola esecuzione cancellerebbe l'unica evidenza documentale del
    blocco. La copia datata esiste per questo.
    """
    return config.REPORTS / f"fase16_o1_congelate_{league}_{CONGELATE_AL}.csv"


def percorso_vivo(league: str) -> Path:
    """Il file che `run_previsioni.py` riscrive. Si legge, non ci si affida."""
    return config.REPORTS / f"previsioni_{league}.csv"


def congela(leagues=None, verbose: bool = True) -> pd.DataFrame:
    """Copia i file vivi nei loro nomi datati, **preservando il `mtime`**.

    Idempotente: se la copia esiste gia' non la tocca, perche' riscriverla ne
    cancellerebbe la data — che e' l'unica cosa che quella copia aggiunge.
    """
    leagues = list(config.LEAGUE_CODES) if leagues is None else list(leagues)
    righe = []
    for lg in leagues:
        src, dst = percorso_vivo(lg), percorso_congelate(lg)
        if dst.is_file():
            stato = "gia' presente"
        elif not src.is_file():
            stato = "sorgente assente"
        else:
            shutil.copy2(src, dst)          # copy2 conserva il mtime
            stato = "copiato"
        if verbose:
            print(f"    {lg}: {stato}")
        righe.append({"campionato": lg, "stato": stato, "file": dst.name})
    return pd.DataFrame(righe)


def _sha256(path: Path) -> str:
    from acquisition.manifest import sha256          # una definizione sola
    return sha256(path)


def primo_evento(league: str, season: str | None = None):
    """Il `mtime` piu' VECCHIO fra i CSV di evento della stagione in corso.

    E' il momento in cui il primo dato di quella stagione e' entrato nel
    repository: qualunque cosa sia piu' vecchia di questo non puo' averlo
    guardato.
    """
    season = config.SEASON_CORRENTE if season is None else season
    d = config.match_dir(league, season)
    if not d.is_dir():
        return None
    ts = [p.stat().st_mtime for p in d.glob("*.csv")]
    return pd.Timestamp(min(ts), unit="s") if ts else None


def registro(leagues=None) -> pd.DataFrame:
    """Provenienza delle previsioni congelate: hash, byte, `mtime`, anteriorita'.

    Vive in git come eccezione dichiarata in `.gitignore`, con la stessa
    motivazione gia' scritta per `data/raw/manifest.json`: una provenienza
    senza storia non e' verificabile.

    **Il commit non prova la data.** La storia in git comincia dopo i fatti; a
    provare che le previsioni non guardano le giornate 1-2 e' la riproduzione di
    `verifica_anteriorita`, non questo timestamp.
    """
    leagues = list(config.LEAGUE_CODES) if leagues is None else list(leagues)
    righe = []
    for lg in leagues:
        p = percorso_congelate(lg)
        if not p.is_file():
            righe.append({"campionato": lg, "file": p.name, "presente": False})
            continue
        st = p.stat()
        scritte = pd.Timestamp(st.st_mtime, unit="s")
        primo = primo_evento(lg)
        righe.append({
            "campionato": lg,
            "file": p.name,
            "presente": True,
            "righe": int(len(pd.read_csv(p))),
            "byte": int(st.st_size),
            "sha256": _sha256(p),
            "previsioni_scritte": scritte,
            "primo_evento_stagione": primo,
            "anteriore": bool(primo is not None and scritte < primo),
            "giorni_di_anticipo": (float((primo - scritte) / pd.Timedelta(days=1))
                                   if primo is not None else np.nan),
        })
    return pd.DataFrame(righe)


def verifica_anteriorita(leagues=None,
                         toll: float = TOLL_RIPRODUZIONE) -> pd.DataFrame:
    """La guardia del blocco, e non e' una formalita': e' **falsificabile**.

    Pretende due cose insieme, e la seconda e' quella che conta:

    * `mtime(previsioni) < mtime(primo evento)` — necessaria, ma debole: un
      timestamp si puo' cambiare;
    * le colonne del file congelato si riproducono da `PS.lam_dal_prior`
      applicato al fit della **sola stagione precedente**, entro `toll`. Questa
      non chiede di fidarsi di niente: se il numero pubblicato e' una funzione
      di dati che finiscono a maggio 2026, non contiene informazione sulle
      giornate 1-2.

    Se una delle due cade, il blocco **non si pubblica**.
    """
    leagues = list(config.LEAGUE_CODES) if leagues is None else list(leagues)
    reg = registro(leagues).set_index("campionato")
    righe = []
    for lg in leagues:
        if not bool(reg.loc[lg].get("presente", False)):
            righe.append({"campionato": lg, "presente": False, "supera": False})
            continue
        cong = pd.read_csv(percorso_congelate(lg))
        scarti = {}
        for tg in BERSAGLI:
            p = PS.prior_per(config.SEASON_CORRENTE, league=lg, target=tg)
            lam = PS.lam_dal_prior(p, cong["squadra"], cong["avversario"],
                                   (cong["campo"] == "casa").astype(int))
            atteso = cong[COLONNA_LAMBDA[tg]].to_numpy(dtype=float)
            scarti[tg] = float(np.max(np.abs(lam / atteso - 1.0)))
        ant = bool(reg.loc[lg, "anteriore"])
        peggio = max(scarti.values())
        righe.append({
            "campionato": lg,
            "presente": True,
            "anteriore_al_primo_evento": ant,
            "scarto_max_shots": scarti["shots"],
            "scarto_max_sot": scarti["sot"],
            "riprodotto": bool(peggio < toll),
            "supera": bool(ant and peggio < toll),
        })
    return pd.DataFrame(righe)


# --------------------------------------------------------------------------
# §2 — il perimetro, e la giornata come grandezza da ACCERTARE
# --------------------------------------------------------------------------
def perimetro(league: str, season: str | None = None) -> pd.DataFrame:
    """Le righe valutate: `team_match_idx <= PERIMETRO_IDX_MAX`.

    La riga e' la **squadra-partita**, l'unita' indipendente e' la **partita**:
    ogni confronto appaiato piu' avanti raggruppa per `matchId`.
    """
    season = config.SEASON_CORRENTE if season is None else season
    u = T.universo([season], league=league)
    if not len(u):
        return u
    d = u[u["team_match_idx"] <= PERIMETRO_IDX_MAX].copy()
    return d.sort_values(["date", "matchId", "team"]).reset_index(drop=True)


def _completezza_seconda_fonte(league: str, season: str) -> dict:
    """Cosa la seconda fonte dichiara di se stessa.

    Serve a distinguere **incompleta** da **storta**, che e' la stessa
    distinzione che `calendario.completezza()` tiene separata da
    `calendario.verifica()`: una pagina che elenca meta' stagione non e'
    sbagliata, e' a meta'. Il criterio del ripiego poggia sui campionati in cui
    la fonte si dichiara COMPLETA, non su una soglia numerica scelta dopo aver
    visto gli scarti.
    """
    import json

    from acquisition.wikipedia import target as WT

    try:
        d = json.loads(WT.percorso(league, season).read_text(encoding="utf-8"))
    except Exception:                               # noqa: BLE001
        return {}
    return d.get("completezza", {}) or {}


def verifica_giornata(league: str, season: str | None = None) -> dict:
    """La giornata vera contro il ripiego: **controllo positivo** del perimetro.

    Tre esiti diversi che e' facile confondere, e che qui restano separati:

    * **assente dalla fonte** — la seconda fonte non elenca quella partita. Non
      dice niente sul ripiego: e' incompletezza della pagina, e va contata a
      parte invece di finire nel numeratore di un disaccordo.
    * **ambigua** — la fonte elenca lo stesso accoppiamento a due giornate
      diverse. Sono i **rinvii**, gia' documentati dalla Fase 15
      (`accoppiamento_ripetuto` in Ligue 1): la partita compare sia al turno
      originale sia a quello di recupero. Si tolgono **tutte** le copie, perche'
      non c'e' modo di sapere quale sia la buona — la stessa regola di
      `calendario.py`. Tenerne una a caso produrrebbe un disaccordo inventato:
      la prima stesura di questa funzione lo ha fatto, ha attribuito al ripiego
      un errore che era suo, e il caso era `Paris FC-Nizza`, elencato dalla
      fonte alla giornata 2 **e** alla 7.
    * **discorde** — la fonte la elenca senza ambiguita' a una giornata sopra la
      soglia. **Questo, e solo questo, e' un disaccordo.**

    Restituisce sempre un esito, mai un'eccezione: su quattro campionati su
    cinque la seconda fonte e' parziale o rotta, e "non verificabile" e' la
    risposta giusta, non un errore.
    """
    from . import calendario as CAL

    season = config.SEASON_CORRENTE if season is None else season
    per = perimetro(league, season)
    comp = _completezza_seconda_fonte(league, season)
    out = {"campionato": league,
           "n_righe": int(len(per)),
           "n_partite": int(per["matchId"].nunique()) if len(per) else 0,
           "fonte_completa": bool(comp.get("completo", False)),
           "verificabile": False, "motivo": "", "accordo": np.nan,
           "n_note": 0, "n_assenti_dalla_fonte": 0, "n_ambigue": 0,
           "n_discordi": 0, "n_nella_giornata_vera": 0, "discordi": ""}
    if not len(per):
        out["motivo"] = "perimetro vuoto"
        return out

    wiki = CAL.carica_wikipedia(league, season)
    if wiki.empty or "giornata" not in wiki.columns:
        out["motivo"] = "seconda fonte assente o senza giornata"
        return out

    # il nome non e' una chiave fra le due fonti (Fase 8): serve la mappa
    try:
        squadre_ws = sorted(set(per["team"]) | set(per["opponent"]))
        mappa = CAL.mappa_squadre(squadre_ws,
                                  CAL.squadre_wikipedia(league, season),
                                  league=league)
    except Exception as exc:                        # noqa: BLE001
        out["motivo"] = f"riconciliazione dei nomi impossibile ({exc})"
        return out

    w = wiki.copy()
    w["casa_ws"] = w["casa"].map(mappa)
    w["trasferta_ws"] = w["trasferta"].map(mappa)
    w["g"] = pd.to_numeric(w["giornata"], errors="coerce")
    w = w[w[["casa_ws", "trasferta_ws", "g"]].notna().all(axis=1)]
    if not len(w):
        out["motivo"] = "la mappa non copre nessuna riga della seconda fonte"
        return out

    # un accoppiamento con piu' di una giornata e' AMBIGUO: via tutte le copie
    per_coppia = w.groupby(["casa_ws", "trasferta_ws"])["g"].agg(["nunique", "min"])
    ambigue = set(per_coppia.index[per_coppia["nunique"] > 1])
    certe = {k: float(v) for k, v in
             per_coppia.loc[per_coppia["nunique"] == 1, "min"].items()}

    casa = per[per["is_home"] == 1]
    nostre = list(zip(casa["team"], casa["opponent"]))
    note = [q for q in nostre if q in certe]
    assenti = [q for q in nostre if q not in certe and q not in ambigue]
    amb = [q for q in nostre if q in ambigue]
    discordi = [(q, certe[q]) for q in note if certe[q] > PERIMETRO_IDX_MAX]

    out.update({
        "verificabile": bool(note),
        "motivo": ("accordo misurato" if note else
                   "nessuna partita del perimetro e' elencata senza ambiguita'"),
        "n_note": int(len(note)),
        "n_assenti_dalla_fonte": int(len(assenti)),
        "n_ambigue": int(len(amb)),
        "n_discordi": int(len(discordi)),
        "n_nella_giornata_vera": int(sum(1 for g in certe.values()
                                         if g <= PERIMETRO_IDX_MAX)),
        "accordo": (float(1.0 - len(discordi) / len(note)) if note else np.nan),
        "discordi": "; ".join(f"{a}-{b} (g{int(g)})" for (a, b), g in discordi),
    })
    return out


def ripiego_ammesso(verifiche) -> dict:
    """Il ripiego si usa se il CONTROLLO POSITIVO passa.

    Il criterio non e' una soglia sull'accordo medio — quella si sceglierebbe
    dopo aver visto gli scarti, cioe' il vincolo 1 violato. E' una condizione
    sulla **fonte**: dove la seconda fonte si dichiara completa, l'accordo deve
    essere **totale**. Li' un disaccordo sarebbe un disaccordo vero; dove la
    fonte e' parziale l'accordo e' informativo ma non decisivo, e i casi
    discordi si contano e si dichiarano invece di far scattare o cadere una
    soglia.

    Se nessun campionato ha una fonte completa il ripiego **non e' ammesso**:
    "prime due giornate" sarebbe un nome dato a righe che nessuno ha mai
    confrontato con una giornata vera.
    """
    v = (verifiche if isinstance(verifiche, pd.DataFrame)
         else pd.DataFrame(list(verifiche)))
    ok = v[v["verificabile"].fillna(False).astype(bool)]
    pieni = ok[ok["fonte_completa"].fillna(False).astype(bool)]
    if not len(pieni):
        return {"ammesso": False, "controllo_positivo": [],
                "accordo_sul_controllo": np.nan,
                "discordi_altrove": int(ok["n_discordi"].sum()) if len(ok) else 0,
                "perche": "nessuna seconda fonte completa: il controllo "
                          "positivo non esiste e il ripiego non si applica"}
    minimo = float(pieni["accordo"].min())
    altrove = int(ok.loc[~ok.index.isin(pieni.index), "n_discordi"].sum())
    return {
        "ammesso": bool(minimo >= 1.0),
        "controllo_positivo": pieni["campionato"].tolist(),
        "accordo_sul_controllo": minimo,
        "discordi_altrove": altrove,
        "perche": (f"accordo totale dove la fonte e' completa "
                   f"({', '.join(pieni['campionato'])}); {altrove} discordi "
                   "dove e' parziale, contati e dichiarati"
                   if minimo >= 1.0 else
                   f"accordo {minimo:.3f} < 1 su una fonte COMPLETA: il ripiego "
                   "non si applica"),
    }


# --------------------------------------------------------------------------
# §3 — le previsioni del perimetro, e il ponte con il file congelato
# --------------------------------------------------------------------------
def _alpha_prior(league: str, target: str) -> float:
    """L'`alpha_prior` di produzione, con un ripiego dichiarato."""
    try:
        a = PS.alpha_prior_produzione(league=league, target=target)
    except Exception:                               # noqa: BLE001
        a = None
    return 12.0 if a is None else float(a)


def previsioni_del_perimetro(league: str, target: str = "shots",
                             season: str | None = None) -> pd.DataFrame:
    """I candidati sulle stesse righe, piu' il ponte con il file congelato.

    **Riusa `PS.previsioni_avvio`** invece di riscriverne una copia: quella
    funzione e' gia' il walk-forward per data dei cinque candidati di A2, e
    rifarla qui vorrebbe dire avere due definizioni della stessa cosa. Le si
    chiede solo un perimetro piu' corto (`fino_a = 2`).

    Due colonne dichiarano cio' che non si puo' nascondere:

    * `da_file_congelato` — la riga ha una previsione **documentale**, cioe' un
      numero scritto su disco prima dei fatti. Dove e' `False` la previsione
      esiste lo stesso (`PS.lam_dal_prior` da' coefficiente 0 a una squadra
      sconosciuta) ma e' un **default**, non una stima: la media di campionato
      dell'anno scorso.
    * `neopromossa_coinvolta` — perche' quel `False` ha una causa sola, e va
      contata invece che subita.

    L'`oracolo di livello` non e' un modello: e' `modello prec` riscalato in
    modo che la media prevista sul perimetro coincida con quella **osservata**.
    Serve a separare «ho sbagliato il livello del campionato nuovo» da «ho
    sbagliato l'ordinamento fra le squadre», ed e' dichiarato oracolo perche'
    usa un numero che il 30 agosto non esisteva.
    """
    season = config.SEASON_CORRENTE if season is None else season
    prev = PS.previsioni_avvio(season, league=league, target=target,
                               alpha_prior=_alpha_prior(league, target),
                               fino_a=PERIMETRO_IDX_MAX)
    if not len(prev):
        return prev
    prev = prev[prev["team_match_idx"] <= PERIMETRO_IDX_MAX].copy()
    prev["campionato"] = league
    prev["bersaglio"] = target

    # --- il ponte con il file congelato --------------------------------
    p = percorso_congelate(league)
    if p.is_file():
        cong = pd.read_csv(p)
        c = cong[["squadra", "avversario", "campo",
                  COLONNA_LAMBDA[target], COLONNA_R[target]]].copy()
        c.columns = ["team", "opponent", "campo", "lam_congelata", "r_congelata"]
        c["is_home"] = (c["campo"] == "casa").astype(int)
        c = c.drop(columns="campo")
        # la chiave DEVE essere unica: nessuna chiave di questo repository lo e'
        # finche' non e' misurata (trappola del Blocco 0)
        if c.duplicated(["team", "opponent", "is_home"]).any():
            raise ValueError(
                f"{p.name}: la tripla (squadra, avversario, campo) non e' unica, "
                "quindi il join moltiplicherebbe le righe in silenzio")
        n0 = len(prev)
        prev = prev.merge(c, on=["team", "opponent", "is_home"], how="left")
        if len(prev) != n0:
            raise ValueError(
                f"il join col file congelato ha cambiato le righe: {n0} -> "
                f"{len(prev)}")
    else:
        prev["lam_congelata"] = np.nan
        prev["r_congelata"] = np.nan

    prev["da_file_congelato"] = prev["lam_congelata"].notna()
    prev["neopromossa_coinvolta"] = prev["senza_prior_in_rosa"] > 0

    # --- l'oracolo di livello ------------------------------------------
    base = prev["lam_modello_prec"].to_numpy(dtype=float)
    osservato = prev[target].to_numpy(dtype=float)
    fattore = float(osservato.mean() / base.mean())
    prev["lam_oracolo_livello"] = base * fattore
    prev.attrs["fattore_oracolo"] = fattore

    # La dispersione PUBBLICATA di questo campionato, portata riga per riga.
    # E' cio' che rende lecito mediare il CRPS fra campionati diversi: `r` e'
    # una costante DI CAMPIONATO (T1: fra Bundesliga e Liga cambia di un fattore
    # 2,7), quindi ogni riga deve viaggiare con la propria.
    prev["r_lega"] = r_pubblicata(prev)
    return prev


def r_pubblicata(prev: pd.DataFrame) -> float:
    """La `r` NB2 che era nel file congelato, cioe' quella davvero pubblicata.

    **Non si ristima qui**, ed e' il punto: valutare con una `r` migliore
    misurerebbe un modello che nessuno ha mai pubblicato. Quanto quella `r` sia
    sbagliata all'avvio e' una domanda diversa, e ha la sua sezione
    (`dispersione_di_avvio`).
    """
    r = prev["r_congelata"].dropna()
    if len(r):
        return float(r.iloc[0])
    from . import dispersion as D
    return float(D.R_MAX)


def coerenza_col_congelato(prev: pd.DataFrame) -> dict:
    """Il file congelato e `modello prec` sono la stessa cosa? Misurato per riga.

    E' la seconda meta' di `verifica_anteriorita`, ristretta alle righe che
    contano davvero: se qui lo scarto non fosse zero, il blocco starebbe
    valutando un numero diverso da quello pubblicato.
    """
    d = prev[prev["da_file_congelato"]]
    if not len(d):
        return {"n": 0, "scarto_max": np.nan, "coincidono": False}
    scarto = float(np.max(np.abs(d["lam_congelata"].to_numpy(dtype=float)
                                 / d["lam_modello_prec"].to_numpy(dtype=float)
                                 - 1.0)))
    return {"n": int(len(d)), "scarto_max": scarto,
            "coincidono": bool(scarto < TOLL_RIPRODUZIONE)}


# --------------------------------------------------------------------------
# §4 — la valutazione
# --------------------------------------------------------------------------
def _colonne_disponibili(prev: pd.DataFrame) -> list:
    """I candidati che hanno davvero una previsione su queste righe.

    `senza prior` non e' definito alla **prima data** della stagione — li' il
    training e' vuoto e `previsioni_avvio` mette `NaN` invece di inventare
    un'intercetta. Dichiararlo e' meglio che riempirlo.
    """
    fuori = []
    for nome in CANDIDATI:
        col = COLONNA_CANDIDATO[nome]
        if col in prev.columns and prev[col].notna().any():
            fuori.append(nome)
    return fuori


def _r_di(d: pd.DataFrame, r=None):
    """La dispersione da usare su queste righe: scalare o **una per riga**.

    `r` e' una costante **di campionato**, non del progetto: sui tentativi vale
    ~20 in Serie A e cambia altrove, e T1 ha misurato che prenderla in prestito
    da un altro campionato sbaglia le code grossolanamente. Quando le righe di
    piu' campionati stanno nella stessa tabella (`insieme()`), ognuna porta con
    se' la propria — che e' l'unico modo di poterle mediare.
    """
    if r is not None:
        return r
    if "r_lega" in d.columns and d["r_lega"].notna().any():
        v = d["r_lega"].to_numpy(dtype=float)
        return float(v[0]) if len(np.unique(v[~np.isnan(v)])) == 1 else v
    return r_pubblicata(d)


def _k_max(d: pd.DataFrame, cols, r) -> int:
    """Troncamento del CRPS: dal lambda piu' grande e dalla `r` piu' grande.

    Si prende l'estremo invece di tarare riga per riga perche' il troncamento
    dev'essere **lo stesso per tutti i candidati**: un `k_max` diverso per
    ciascuno renderebbe i loro CRPS non confrontabili, che e' l'unica cosa per
    cui servono.
    """
    from . import validate as V

    lam_max = max(float(d[c].max()) for c in cols if d[c].notna().any())
    r_max = float(np.max(r)) if np.ndim(r) else float(r)
    return V.crps_k_max(np.array([lam_max]), r_max)


def insieme(prevs) -> pd.DataFrame:
    """Le righe di piu' campionati in una tabella sola, ognuna con la sua `r`.

    Mettere insieme i campionati e' lecito **solo** perche' il CRPS e' una
    perdita per riga, gia' calcolata con la dispersione giusta: mediarla e'
    mediare numeri omogenei. Stimare un modello unico sui cinque sarebbe invece
    l'errore che E1 vieta e che F13 ha quantificato — e infatti qui non si
    stima niente.
    """
    pezzi = [p for p in prevs if p is not None and len(p)]
    if not pezzi:
        return pd.DataFrame()
    return pd.concat(pezzi, ignore_index=True)


def valutazione(prev: pd.DataFrame, target: str, r=None,
                solo_congelate: bool = False) -> pd.DataFrame:
    """CRPS (primaria), log score, MAE e bias per candidato.

    Ogni candidato si compone con la **stessa** NB2 e la **stessa** `r` del
    soggetto: e' la regola di R2, dove ogni baseline passava per la stessa
    congiunta del modello. Comporre diversamente misurerebbe la composizione
    invece del lambda.

    **Due denominatori, ed e' voluto** — e' la correzione che E4 ha dovuto fare
    sul divario dei bonus, dove un confronto verticale fra campioni diversi
    aveva prodotto un numero sbagliato di un fattore tre:

    * `crps` sta sulle righe in cui **quel** candidato e' definito;
    * `crps_righe_comuni` sulle righe in cui lo sono **tutti**, ed e' la sola
      colonna che si possa leggere in verticale.

    Le due differiscono perche' `senza prior` non esiste alla prima data:
    pretendere l'intersezione ovunque butterebbe via proprio le partite di
    avvio piu' fredde, che sono quelle che il blocco vuole misurare.
    """
    from . import dispersion as D
    from . import validate as V

    nomi = _colonne_disponibili(prev)
    cols = [COLONNA_CANDIDATO[n] for n in nomi]

    base = prev if not solo_congelate else prev[prev["da_file_congelato"]]
    if not len(base):
        return pd.DataFrame()
    comuni = base[base[cols].notna().all(axis=1)]
    k_max = _k_max(base, cols, _r_di(base, r))

    righe = []
    for nome, col in zip(nomi, cols):
        d = base[base[col].notna()]
        rr = _r_di(d, r)
        y = d[target].to_numpy(dtype=float)
        lam = d[col].to_numpy(dtype=float)
        voce = {
            "candidato": nome,
            "n": int(len(d)),
            "n_partite": int(d["matchId"].nunique()),
            "crps": float(V.crps_conteggi(y, lam, rr, k_max=k_max).mean()),
            "log_score": float(-D.nb2_loglik(y, lam, rr).mean()),
            "mae": float(np.mean(np.abs(y - lam))),
            "bias": float(np.mean(lam - y)),
            "sharpness": float(np.std(lam, ddof=1)),
        }
        if len(comuni):
            rc = _r_di(comuni, r)
            voce["n_comuni"] = int(len(comuni))
            voce["crps_righe_comuni"] = float(V.crps_conteggi(
                comuni[target].to_numpy(dtype=float),
                comuni[col].to_numpy(dtype=float), rc, k_max=k_max).mean())
        righe.append(voce)

    out = pd.DataFrame(righe)
    out.attrs["k_max"] = int(k_max)
    return out


def confronto_appaiato(prev: pd.DataFrame, target: str, r=None,
                       soggetto: str = SOGGETTO,
                       solo_congelate: bool = False) -> pd.DataFrame:
    """Il soggetto contro ogni altro candidato, **appaiato e clusterizzato**.

    Ogni coppia gira sulle righe in cui **entrambi** sono definiti, non
    sull'intersezione di tutti e sei: restringere ovunque all'intersezione
    farebbe pagare a ogni confronto il buco di `senza prior`, che riguarda solo
    lui. `n` e' in tabella proprio perche' i denominatori differiscono.

    L'unita' indipendente e' la **partita**, non la riga: le due squadre della
    stessa partita condividono ritmo, punteggio e arbitro, e sui tentativi V0
    ha misurato fra i due lati una correlazione di -0,35. Si passa quindi
    `cluster = matchId` a `validate.paired_t`, che ritorna `(somma, t)` e **non**
    `(t, p)` — lo scambio e' silenzioso ed e' una trappola gia' annotata nel
    repository.

    Il MDE e' a **due code** e sui cluster, cioe' la stessa forma con cui A2 ha
    giudicato le stesse righe di avvio: usarne un'altra renderebbe i due
    blocchi non confrontabili.
    """
    from scipy.stats import norm

    from . import validate as V

    nomi = _colonne_disponibili(prev)
    if soggetto not in nomi:
        return pd.DataFrame()
    col_s = COLONNA_CANDIDATO[soggetto]

    base = prev if not solo_congelate else prev[prev["da_file_congelato"]]
    if not len(base):
        return pd.DataFrame()
    cols = [COLONNA_CANDIDATO[n] for n in nomi]
    k_max = _k_max(base, cols, _r_di(base, r))

    # z a due code alla potenza dichiarata: la stessa costante di PS.mde_relativo
    z = float(norm.isf(0.05 / 2) + norm.isf(1 - 0.80))

    righe = []
    for nome in nomi:
        if nome == soggetto:
            continue
        col_a = COLONNA_CANDIDATO[nome]
        d = base[base[[col_s, col_a]].notna().all(axis=1)]
        if len(d) < 2:
            continue
        rr = _r_di(d, r)
        y = d[target].to_numpy(dtype=float)
        cl = d["matchId"].to_numpy()
        mio = V.crps_conteggi(y, d[col_s].to_numpy(dtype=float), rr, k_max=k_max)
        suo = V.crps_conteggi(y, d[col_a].to_numpy(dtype=float), rr, k_max=k_max)
        # il CRPS e' una PERDITA: il soggetto vince se la differenza e' negativa
        _, t = V.paired_t(mio, suo, cluster=cl)
        per_cluster = pd.Series(mio - suo).groupby(cl).mean().to_numpy()
        se = float(per_cluster.std(ddof=1) / np.sqrt(len(per_cluster)))
        mde = z * se
        delta = float(per_cluster.mean())
        righe.append({
            "soggetto": soggetto,
            "avversario": nome,
            "n": int(len(d)),
            "n_cluster": int(len(per_cluster)),
            "crps_soggetto": float(mio.mean()),
            "crps_avversario": float(suo.mean()),
            "delta_crps": delta,
            "t_cluster": float(t),
            "mde": mde,
            "delta_su_mde": float(abs(delta) / mde) if mde > 0 else np.nan,
            "conclude": bool(mde > 0 and abs(delta) / mde >= 1.0),
            "vince_il_soggetto": bool(delta < 0),
        })
    return pd.DataFrame(righe)


def forma_predittiva(prev: pd.DataFrame, target: str,
                     candidato: str = SOGGETTO,
                     r: float | None = None) -> dict:
    """PIT e copertura: la **forma** della predittiva, non solo la sua media.

    Su questo perimetro il PIT e' **debole** — dieci fasce su poche decine di
    righe — e va letto come indizio. La stessa misura sulla taratura storica,
    dove le righe sono migliaia, e' invece informativa: e' una delle ragioni
    per cui la taratura non e' un ornamento.
    """
    from . import validate as V

    r = r_pubblicata(prev) if r is None else r
    col = COLONNA_CANDIDATO[candidato]
    d = prev[prev[col].notna()]
    y = d[target].to_numpy(dtype=float)
    lam = d[col].to_numpy(dtype=float)
    u = V.pit(y, lam, r)
    return {"n": int(len(d)), "r": float(r),
            "pit": V.pit_uniformity(u),
            "copertura": V.interval_coverage(y, lam, r)}


def scomposizione_livello(prev: pd.DataFrame, target: str,
                          r: float | None = None) -> dict:
    """Quanto dell'errore e' il LIVELLO del campionato nuovo, e quanto no.

    Il livello si muove fra stagioni ed e' gia' misurato altrove (V0: tentativi
    da 13,03 a 12,31, -5,5%; E4: 15,8% di escursione fra i cinque fit di xG).
    Una previsione cross-stagione lo eredita dall'anno prima, quindi la prima
    domanda da separare e' se sbagli il livello o l'ordinamento.

    L'oracolo di livello risponde: e' lo stesso modello con la stessa struttura
    e la media rimessa a posto. La differenza fra i due CRPS e' la parte
    dell'errore **attribuibile al solo livello**.
    """
    from . import validate as V

    r = r_pubblicata(prev) if r is None else r
    y = prev[target].to_numpy(dtype=float)
    lam = prev["lam_modello_prec"].to_numpy(dtype=float)
    orc = prev["lam_oracolo_livello"].to_numpy(dtype=float)
    k_max = V.crps_k_max(np.concatenate([lam, orc]), r)
    c_mod = float(V.crps_conteggi(y, lam, r, k_max=k_max).mean())
    c_orc = float(V.crps_conteggi(y, orc, r, k_max=k_max).mean())
    return {
        "n": int(len(prev)),
        "media_prevista": float(lam.mean()),
        "media_osservata": float(y.mean()),
        "fattore_di_livello": float(prev.attrs.get("fattore_oracolo", np.nan)),
        "scarto_di_livello_pct": float(y.mean() / lam.mean() - 1.0) * 100.0,
        "crps_modello_prec": c_mod,
        "crps_oracolo_livello": c_orc,
        "quota_del_crps_dal_livello": (float((c_mod - c_orc) / c_mod)
                                       if c_mod > 0 else np.nan),
    }


# --------------------------------------------------------------------------
# Brier sulle linee dichiarate, e il TOTALE di partita
# --------------------------------------------------------------------------
def linee_del_lato(target: str) -> tuple:
    """Le linee di quel bersaglio, **prese da dove sono gia' dichiarate**.

    Sui tiri sono `tentativi.LINEE_TIRI`; sui tiri in porta restano
    `validate.LINES`, che `tentativi.LINEE_SOT_INVARIATE` prescrive di non
    toccare — linee nuove renderebbero questi numeri non confrontabili con la
    Fase 4. Inventarne qui sarebbe la stessa cosa fatta di nascosto.
    """
    from . import validate as V

    return tuple(T.LINEE_TIRI) if target == "shots" else tuple(V.LINES)


def brier_per_linea(prev: pd.DataFrame, target: str, r: float | None = None,
                    candidato: str = SOGGETTO) -> pd.DataFrame:
    """Il Brier su ogni linea dichiarata, col tasso base accanto (vincolo 6).

    Il tasso base e' quello **osservato sul perimetro stesso**, ed e' percio'
    un ORACOLO: nessuno lo conosceva il 30 agosto. Sta in tabella come limite
    superiore di cio' che un modello senza informazione potrebbe fare, non come
    un concorrente leale — la stessa disciplina con cui E3 ha tenuto la
    frequenza storica grezza accanto a quella smorzata.
    """
    from . import dispersion as D
    from . import validate as V

    r = r_pubblicata(prev) if r is None else r
    col = COLONNA_CANDIDATO[candidato]
    d = prev[prev[col].notna()]
    y = d[target].to_numpy(dtype=float)
    lam = d[col].to_numpy(dtype=float)

    righe = []
    for ln in linee_del_lato(target):
        yb = (y > ln).astype(float)
        righe.append({
            "bersaglio": target,
            "linea": ln,
            "n": int(len(d)),
            "tasso_base_osservato": float(yb.mean()),
            "p_media_dichiarata": float(D.p_over(lam, ln, r).mean()),
            "brier": float(V.brier(yb, D.p_over(lam, ln, r))),
            "brier_tasso_base_oracolo": float(V.brier(yb, np.full(len(yb),
                                                                 yb.mean()))),
        })
    out = pd.DataFrame(righe)
    out["vince_sul_tasso_base"] = out["brier"] < out["brier_tasso_base_oracolo"]
    return out


def totale_del_perimetro(prev: pd.DataFrame, target: str) -> pd.DataFrame:
    """La somma delle due squadre, ruotando il perimetro a livello PARTITA.

    `E[X+Y] = E[X] + E[Y]` non richiede nessuna ipotesi, quindi `lam_tot` e'
    esatto qualunque sia la dipendenza fra i due lati — e' il risultato di T1.
    Cio' che la dipendenza rompe e' la **dispersione**, e per questo `r_tot`
    non si eredita da `r` per lato: si prende quella gia' stimata sulle
    stagioni storiche di quel campionato.

    La rotazione ripete i **due controlli** di `perimetro.partite()` e di
    `totale.partite()` invece di importarli: due lati per partita ed esattamente
    un lato di casa. Ripeterli e' l'unico modo di non ereditare in silenzio un
    accoppiamento sbagliato.
    """
    n = prev.groupby("matchId").size()
    if not (n == 2).all():
        rotte = n[n != 2]
        raise ValueError(
            f"{len(rotte)} partite non hanno due lati: {rotte.head().to_dict()}. "
            "La rotazione a livello partita non e' definita.")
    casa = prev.groupby("matchId")["is_home"].sum()
    if not (casa == 1).all():
        raise ValueError(
            "esistono partite senza esattamente un lato di casa: casa e "
            "trasferta sarebbero intercambiabili")

    c = prev[prev["is_home"] == 1].set_index("matchId")
    t = prev[prev["is_home"] == 0].set_index("matchId")
    out = pd.DataFrame({
        "data": c["date"], "casa": c["team"], "trasferta": t["team"],
        "y_totale": c[target].astype(float) + t[target].astype(float),
    })
    for nome in _colonne_disponibili(prev):
        col = COLONNA_CANDIDATO[nome]
        out[col] = c[col] + t[col]
    out["da_file_congelato"] = c["da_file_congelato"] & t["da_file_congelato"]
    return out.reset_index()


def r_totale_pubblicata(league: str, target: str) -> float:
    """La `r_tot` gia' stimata sulle stagioni storiche di quel campionato.

    **Non si eredita da `r` per lato e non si prende in prestito da un altro
    campionato**: T1 ha misurato che `r_tot` vale 2,3-5,8 volte `r` per lato e
    che fra Bundesliga e Liga cambia di un fattore 2,7. Prenderla altrove
    sbaglierebbe le code grossolanamente.
    """
    from . import totale as TOT

    return float(TOT.r_totale(league=league, target=target))


def valutazione_totale(tot: pd.DataFrame, r_tot: float) -> pd.DataFrame:
    """CRPS, log score, MAE e bias sul totale, per candidato.

    **Sezione secondaria e dichiarata tale**: T1 ha gia' misurato che il totale
    e' sotto-calibrato (pendenza 0,633 su 1.638 partite) e qui i cluster sono
    poche decine. Ci si aspetta di **non concludere**, e cio' che si riporta e'
    se il segno e' coerente con T1 — non un'adozione.
    """
    from . import dispersion as D
    from . import validate as V

    if not len(tot):
        return pd.DataFrame()
    cols = [c for c in COLONNA_CANDIDATO.values() if c in tot.columns]
    tutti = np.concatenate([tot[c].dropna().to_numpy(dtype=float) for c in cols])
    k_max = V.crps_k_max(tutti, r_tot)
    inverso = {v: k for k, v in COLONNA_CANDIDATO.items()}

    righe = []
    for col in cols:
        d = tot[tot[col].notna()]
        y = d["y_totale"].to_numpy(dtype=float)
        lam = d[col].to_numpy(dtype=float)
        righe.append({
            "candidato": inverso[col],
            "n_partite": int(len(d)),
            "crps": float(V.crps_conteggi(y, lam, r_tot, k_max=k_max).mean()),
            "log_score": float(-D.nb2_loglik(y, lam, r_tot).mean()),
            "mae": float(np.mean(np.abs(y - lam))),
            "bias": float(np.mean(lam - y)),
        })
    out = pd.DataFrame(righe)
    out.attrs["r_tot"] = float(r_tot)
    return out


# --------------------------------------------------------------------------
# §5 — la taratura storica: senza, un CRPS e' un numero e non un risultato
# --------------------------------------------------------------------------
def transizioni(leagues=None) -> list:
    """Le coppie (campionato, stagione) su cui la taratura si puo' fare.

    Sono le stagioni storiche che hanno una stagione precedente: quattro per
    campionato, venti in tutto. La 2021-2022 non ne ha una e resta fuori — la
    stessa forma con cui R2-bis ha lasciato fuori la sua prima stagione invece
    di riempirla.
    """
    leagues = list(config.LEAGUE_CODES) if leagues is None else list(leagues)
    return [(lg, s) for lg in leagues
            for s in config.SEASONS_STORICHE
            if PS.stagione_precedente(s) is not None]


def taratura_storica(leagues=None, target: str = "shots",
                     r: float | None = None, verbose: bool = False) -> pd.DataFrame:
    """La **stessa identica procedura** sulle transizioni gia' concluse.

    Senza questa tabella «CRPS = 2,4» non e' un risultato, e' un numero: manca
    la scala con cui leggerlo. E' il gemello di `tentativi.taratura_test()` e
    del nullo simulato di V0 — la differenza fra «il test ha trovato qualcosa» e
    «il test rifiuta sempre» si vede solo mettendo accanto il caso in cui la
    risposta e' nota.

    `r` resta quella **pubblicata** su ogni campionato, non ristimata per
    transizione: valutare ogni anno con la sua `r` migliore misurerebbe un
    modello che nessuno ha pubblicato.
    """
    from . import validate as V

    righe = []
    for lg, stagione in transizioni(leagues):
        if verbose:
            print(f"    {lg} {stagione}")
        prev = previsioni_del_perimetro(lg, target=target, season=stagione)
        if not len(prev):
            continue
        rr = r_pubblicata(prev) if r is None else r
        y = prev[target].to_numpy(dtype=float)
        lam = prev["lam_modello_prec"].to_numpy(dtype=float)
        base = prev["lam_media_squadra_prec"].to_numpy(dtype=float)
        k_max = V.crps_k_max(np.concatenate([lam, base]), rr)
        c_mod = V.crps_conteggi(y, lam, rr, k_max=k_max)
        c_bas = V.crps_conteggi(y, base, rr, k_max=k_max)
        _, t = V.paired_t(c_mod, c_bas, cluster=prev["matchId"].to_numpy())
        righe.append({
            "campionato": lg,
            "stagione": stagione,
            "bersaglio": target,
            "n": int(len(prev)),
            "n_partite": int(prev["matchId"].nunique()),
            "r": float(rr),
            "crps_modello_prec": float(c_mod.mean()),
            "crps_media_squadra_prec": float(c_bas.mean()),
            "delta_crps": float(c_mod.mean() - c_bas.mean()),
            "t_cluster": float(t),
            "mae": float(np.mean(np.abs(y - lam))),
            "bias": float(np.mean(lam - y)),
            "media_osservata": float(y.mean()),
            "scarto_di_livello_pct": float(y.mean() / lam.mean() - 1.0) * 100.0,
            "quota_neopromosse": float((prev["senza_prior_in_rosa"] > 0).mean()),
        })
    return pd.DataFrame(righe)


def collocazione(osservato: float, storiche, piu_basso_e_meglio: bool = True) -> dict:
    """Dove cade il valore nuovo dentro la distribuzione di quelli noti.

    Si riporta il **rango**, non un p-value: venti transizioni non sono un
    campione da cui estrarre una probabilita', e chiamarla tale sarebbe
    fabbricare precisione. Il rango dice cio' che si puo' dire.
    """
    s = np.asarray(list(storiche), dtype=float)
    s = s[np.isfinite(s)]
    if not len(s) or not np.isfinite(osservato):
        return {"n_storiche": int(len(s)), "rango": np.nan, "quota_peggiori": np.nan}
    peggiori = int((s > osservato).sum() if piu_basso_e_meglio
                   else (s < osservato).sum())
    return {
        "n_storiche": int(len(s)),
        "osservato": float(osservato),
        "mediana_storica": float(np.median(s)),
        "minimo_storico": float(s.min()),
        "massimo_storico": float(s.max()),
        "rango": int((s < osservato).sum() + 1),
        "quota_peggiori": float(peggiori / len(s)),
        "dentro_l_intervallo_storico": bool(s.min() <= osservato <= s.max()),
    }


# --------------------------------------------------------------------------
# §6 — la dispersione di avvio: DIAGNOSTICO, non adozione
# --------------------------------------------------------------------------
def dispersione_di_avvio(leagues=None, target: str = "shots",
                         n_boot: int = N_BOOT) -> dict:
    """La `r` pubblicata e' quella giusta per una previsione cross-stagione?

    **L'attesa e' dichiarata prima**: `r` viene dal walk-forward
    **within-season**, dove i lambda sono piu' accurati di quelli
    cross-stagione di `modello prec`. Una previsione peggiore ha residui piu'
    dispersi, quindi la `r` giusta all'avvio dovrebbe essere **piu' piccola** e
    la predittiva pubblicata **troppo stretta**.

    Si misura sulle transizioni storiche, dove l'esito e' noto, e si riporta il
    rapporto con IC95 da bootstrap **sui cluster** (la partita, non la riga) —
    la stessa forma con cui `precisione.rapporto_dispersioni()` ha falsificato
    l'ereditarieta' fra `r_shots` e `r_sot`, e con cui T1 ha rifiutato di
    ereditare `r_tot`.

    **E' un diagnostico e basta**: questo blocco non ricalibra niente. Adottare
    una `r` diversa vorrebbe un criterio scritto prima e una valutazione fuori
    campione sua, che qui non c'e'.
    """
    from . import dispersion as D

    pezzi = []
    for lg, stagione in transizioni(leagues):
        p = previsioni_del_perimetro(lg, target=target, season=stagione)
        if len(p):
            pezzi.append(p[["matchId", target, "lam_modello_prec"]]
                         .assign(campionato=lg, stagione=stagione,
                                 r_pubblicata=r_pubblicata(p)))
    if not pezzi:
        return {}
    d = pd.concat(pezzi, ignore_index=True)

    y = d[target].to_numpy(dtype=float)
    lam = d["lam_modello_prec"].to_numpy(dtype=float)
    r_avvio = float(D.fit_r(y, lam))
    r_pub = float(d["r_pubblicata"].median())

    rng = np.random.default_rng(config.SEED)
    gruppi = d.groupby("matchId").indices
    chiavi = np.array(list(gruppi))
    rap = np.empty(n_boot)
    for i in range(n_boot):
        s = rng.choice(chiavi, size=len(chiavi), replace=True)
        idx = np.concatenate([gruppi[k] for k in s])
        rap[i] = D.fit_r(y[idx], lam[idx]) / r_pub

    lo, hi = float(np.percentile(rap, 2.5)), float(np.percentile(rap, 97.5))
    return {
        "bersaglio": target,
        "n": int(len(d)), "n_cluster": int(len(chiavi)),
        "r_avvio": r_avvio,
        "r_pubblicata": r_pub,
        "rapporto": r_avvio / r_pub,
        "ic95": (lo, hi),
        "compatibili": bool(lo <= 1.0 <= hi),
        "predittiva_troppo_stretta": bool(hi < 1.0),
    }


# --------------------------------------------------------------------------
# §7 — il verdetto, applicato dal codice
# --------------------------------------------------------------------------
def verdetto(conf: pd.DataFrame, riferimento: str = RIFERIMENTO) -> dict:
    """`CRITERIO_LEGGIBILITA` applicato meccanicamente, non a occhio."""
    if not len(conf):
        return {"criterio": CRITERIO_LEGGIBILITA, "conclude": False,
                "perche": "nessun confronto disponibile"}
    r = conf[conf["avversario"] == riferimento]
    if not len(r):
        return {"criterio": CRITERIO_LEGGIBILITA, "conclude": False,
                "perche": f"il riferimento {riferimento!r} non e' fra i candidati"}
    r = r.iloc[0]
    conclude = bool(r["conclude"])
    return {
        "criterio": CRITERIO_LEGGIBILITA,
        "riferimento": riferimento,
        "delta_crps": float(r["delta_crps"]),
        "t_cluster": float(r["t_cluster"]),
        "mde": float(r["mde"]),
        "delta_su_mde": float(r["delta_su_mde"]),
        "n_cluster": int(r["n_cluster"]),
        "conclude": conclude,
        "vince_il_soggetto": bool(r["vince_il_soggetto"]),
        "perche": ("il confronto conclude" if conclude else
                   "delta sotto il proprio MDE: il test NON conclude, che non e' "
                   "«l'effetto non c'e'»"),
    }


def limiti() -> list:
    """I limiti che vanno ACCANTO ai numeri, non in fondo (vincolo 5)."""
    return [
        "Il campione e' di poche decine di partite: quasi ogni confronto sta "
        "sotto il proprio MDE. Il blocco esclude divari grandi, non divari "
        "piccoli — e' la lezione di 6D, V3 e A2.",
        "Le neopromosse non hanno previsione congelata: `PS.lam_dal_prior` da' "
        "loro coefficiente 0, cioe' la media di campionato dell'anno scorso. "
        "E' un DEFAULT dichiarato, non una stima, ed e' contato riga per riga.",
        "La giornata vera e' accertata solo dove la seconda fonte e' sana; "
        "altrove il perimetro e' `team_match_idx <= 2`, che e' una grandezza "
        "diversa (vincolo 7). Quale delle due si e' usata e' scritto per "
        "campionato.",
        "Un campionato entra con i dati che ha: dove mancano CSV di evento di "
        "partite gia' giocate, il perimetro e' piu' corto e lo dichiara.",
        "`r` e' quella PUBBLICATA, non ristimata: valutare con una dispersione "
        "migliore misurerebbe un modello che nessuno ha mai pubblicato.",
        "Vincolo 3: nessuna quota, nessun valore atteso, nessuna valutazione di "
        "scommessa. Non ci sono prezzi di mercato reali nel repository, e le "
        "uniche ottenibili sarebbero generate da questo stesso modello.",
        "La taratura storica e' una scala di riferimento, non un test: venti "
        "transizioni danno un rango, non una probabilita'.",
    ]
