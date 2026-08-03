# -*- coding: utf-8 -*-
"""Provenienza dei file acquisiti — vincoli 8 e 9 della Fase 7.

> Ogni riga scaricata porta con se' la sua provenienza: fonte, URL, data di
> download, hash del file, e la definizione della metrica *in quella fonte*.
> Una riga senza provenienza non entra nel dataset.

`data/raw/manifest.json` e' l'unica cosa sotto `data/` che sta in git: e'
piccolo, testuale e diffabile, e una provenienza senza storia non e'
verificabile.

Due cose che questo modulo **non** fa, di proposito:

- **non scarica** e non contatta nessuna fonte. Registra cio' che e' gia' su
  disco. Tenere separate acquisizione e registrazione significa che il manifest
  si puo' ricostruire senza rifare i download;
- **non modifica e non cancella** nulla sotto `raw/`. L'unico file che scrive e'
  il manifest stesso.

Sull'hash: e' calcolato sul contenuto del file, non sulla data di modifica. Un
hash invariato dice che il file e' lo stesso; un hash **cambiato** su un file
gia' registrato e' un evento da segnalare, non da assorbire in silenzio — la
fonte ha cambiato i dati sotto di noi, ed e' esattamente il caso che il vincolo
9 vuole rendere visibile.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from sot import config

VERSIONE = 1

# La definizione della metrica *nella fonte*, che il vincolo 8 richiede accanto
# ai dati. Non e' la nostra: la nostra vive in `sot/shots.py` e le due non vanno
# mescolate (vincolo 7).
DEFINIZIONI = {
    "whoscored": {
        "fornitore": "Opta, via la chalkboard di WhoScored",
        "granularita": "evento; schema appiattito da createEventsDF",
        "tiro_in_porta": (
            "non e' una colonna pre-calcolata: si deriva dagli eventi. Il flag "
            "Opta `shotOnTarget` esiste nello schema. La definizione usata dal "
            "progetto e' in sot/shots.py e coincide con quel flag."
        ),
        "note": (
            "il dominio effettivamente contattato e' 1xbet.whoscored.com, un "
            "mirror di affiliazione fissato in acquisition/whoscored/main.py, "
            "non www.whoscored.com"
        ),
    },
    "fantacalcio": {
        "fornitore": (
            "Fantacalcio S.r.l., vista HTML pubblica /voti-fantacalcio-serie-a. "
            "Tre scale affiancate nella stessa riga: Redazione Fantacalcio "
            "(pagellisti interni), Voto Statistico (algoritmo Alvin482), "
            "Voto Italia (sintesi di piu' testate). Il progetto usa la Redazione "
            "(regole_fantacalcio.md §7.1, decisione 5); le altre due sono "
            "conservate perche' arrivano nella stessa richiesta"
        ),
        "granularita": "giocatore x partita, solo per chi e' sceso in campo",
        "voto": (
            "giudizio editoriale su scala 0-10 a passi di 0,5. NON e' una "
            "grandezza oggettiva e non e' confrontabile con niente di WhoScored: "
            "e' l'opinione di un pagellista. L's.v. e' discrezionale e la fonte "
            "dichiara esplicitamente che nessuna soglia di minuti esiste"
        ),
        "fantavoto": (
            "voto piu' i bonus/malus del barema DELLA FONTE, verificato per "
            "differenza: gol +3, gol subito -1, autorete -2, rigore segnato +3 "
            "(e il gol su rigore NON e' anche in `gol segnati`), rigore "
            "sbagliato -3, rigore parato +3, assist +1, ammonizione -0,5, "
            "espulsione -1. `player of the match` NON entra. La porta inviolata "
            "NON entra, quindi il fantavoto della lega dell'utente "
            "(regole_fantacalcio.md §1.1) e' una grandezza DIVERSA e va "
            "ricalcolata dai bonus, mai letta da questa colonna"
        ),
        "minuti": (
            "assenti. Non e' l'interfaccia che li nasconde: non sono nel dato. "
            "L'unico segnale di tempo di gioco e' binario (subentrato/sostituito), "
            "senza minuto. I minuti vengono da WhoScored (§7.1, decisione 2)"
        ),
        "note": (
            "acquisizione su autorizzazione dichiarata dall'utente ed estesa "
            "esplicitamente allo scraping dei voti (regole_fantacalcio.md §7.1, "
            "decisione 1), che soddisfa l'art. 3.3(a) dei Termini di Utilizzo. "
            "Il repository registra la dichiarazione, non conserva il documento. "
            "Il grezzo e' HTML compresso con gzip mtime=0: senza perdita, quindi "
            "resta grezzo, e deterministico, quindi l'hash significa qualcosa"
        ),
    },
}


def sha256(path: Path, blocco: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for pezzo in iter(lambda: fh.read(blocco), b""):
            h.update(pezzo)
    return h.hexdigest()


def carica() -> dict:
    if config.MANIFEST.is_file():
        return json.loads(config.MANIFEST.read_text(encoding="utf-8"))
    return {"versione": VERSIONE, "file": {}}


def _url_per_match(fonte_dir: Path) -> dict:
    """matchId -> URL, letto dalla cache del calendario gia' su disco.

    L'URL e' provenienza (vincolo 8) e va conservato: senza, un CSV dice da
    quale stagione viene ma non da quale pagina.
    """
    cache = fonte_dir / "matches.json"
    if not cache.is_file():
        return {}
    fuori = {}
    for m in json.loads(cache.read_text(encoding="utf-8")):
        parti = [p for p in m["url"].split("/") if p]
        mid = parti[parti.index("matches") + 1] if "matches" in parti else parti[-1]
        fuori[mid] = m["url"]
    return fuori


def registra_whoscored(league=None, seasons=None, verbose=True) -> dict:
    """Registra i CSV partita gia' scaricati. Non scarica niente.

    Restituisce un riepilogo con i **cambiamenti**, che sono la cosa da
    guardare: `nuovi` e' lavoro normale, `modificati` no.
    """
    league = config.LEAGUE if league is None else league
    seasons = seasons or config.SEASONS_STORICHE
    man = carica()
    ora = datetime.now(timezone.utc).isoformat(timespec="seconds")
    riepilogo = {"nuovi": 0, "invariati": 0, "modificati": []}

    for season in seasons:
        base = config.raw_dir("whoscored", league, season)
        eventi = base / "events"
        if not eventi.is_dir():
            continue
        urls = _url_per_match(base)

        for csv in sorted(eventi.glob("*.csv")):
            chiave = str(csv.relative_to(config.ROOT)).replace("\\", "/")
            digest = sha256(csv)
            vecchio = man["file"].get(chiave)

            if vecchio and vecchio["sha256"] == digest:
                riepilogo["invariati"] += 1
                continue
            if vecchio:
                # Non si sovrascrive in silenzio: si registra la revisione
                # precedente e si segnala.
                riepilogo["modificati"].append(chiave)
                vecchio.setdefault("revisioni_precedenti", []).append(
                    {"sha256": vecchio["sha256"], "scaricato": vecchio["scaricato"]}
                )

            man["file"][chiave] = {
                "fonte": "whoscored",
                "campionato": league,
                "stagione": season,
                "url": urls.get(csv.stem),
                "match_id": csv.stem,
                # Ora di scrittura del file, non di registrazione: il manifest
                # per i 1889 CSV e' stato creato dopo l'acquisizione, e mettere
                # `ora` avrebbe datato tutti i download allo stesso istante —
                # una provenienza comoda e falsa.
                "scaricato": datetime.fromtimestamp(
                    csv.stat().st_mtime, timezone.utc).isoformat(timespec="seconds"),
                "registrato": ora,
                "byte": csv.stat().st_size,
                "sha256": digest,
                **({"revisioni_precedenti": vecchio["revisioni_precedenti"]}
                   if vecchio and "revisioni_precedenti" in vecchio else {}),
            }
            riepilogo["nuovi"] += 0 if vecchio else 1

        if verbose:
            print(f"  {season}: {len(list(eventi.glob('*.csv')))} file")

    man["definizioni"] = DEFINIZIONI
    man["aggiornato"] = ora
    config.MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    config.MANIFEST.write_text(
        json.dumps(man, indent=1, ensure_ascii=False, sort_keys=True), encoding="utf-8")
    return riepilogo


def registra_fantacalcio(league=None, seasons=None, verbose=True) -> dict:
    """Registra le pagine dei voti gia' scaricate. Non scarica niente.

    Due hash e non uno, ed e' il punto che distingue questa fonte da WhoScored:

    - `sha256` e' del file su disco, cioe' del `.gz`. Serve a dire che il file
      non e' stato toccato;
    - `sha256_html` e' dell'**HTML decompresso**, cioe' di cio' che la fonte ha
      davvero servito. Serve a dire che *la fonte* non ha cambiato i dati sotto
      di noi, ed e' l'unico dei due che sopravvive a un cambio della nostra
      politica di compressione.

    Con `mtime=0` in scrittura i due sono in corrispondenza uno a uno oggi. Se
    un domani divergessero — stesso HTML, `.gz` diverso — la causa sarebbe
    nostra e non della fonte, e i due hash lo direbbero.
    """
    from acquisition.fantacalcio import pagina as P
    from acquisition.fantacalcio import target as T

    league = config.LEAGUE if league is None else league
    seasons = seasons or config.SEASONS_STORICHE
    man = carica()
    ora = datetime.now(timezone.utc).isoformat(timespec="seconds")
    riepilogo = {"nuovi": 0, "invariati": 0, "modificati": []}

    for target in T.targets(league, seasons):
        presenti = 0
        # Il listone e' una risorsa diversa con un'altra granularita' — una
        # pagina per stagione, non per giornata — ma la provenienza e' la stessa
        # cosa e va nello stesso posto: `giornata` resta nulla, ed e' proprio
        # quello a distinguerlo.
        pagine = [(g, target.percorso(g)) for g in range(1, T.N_GIORNATE + 1)]
        pagine.append((None, T.TargetQuote(league, target.season).percorso))

        for giornata, percorso in pagine:
            if not percorso.is_file():
                continue
            presenti += 1
            chiave = str(percorso.relative_to(config.ROOT)).replace("\\", "/")
            digest = sha256(percorso)
            vecchio = man["file"].get(chiave)

            if vecchio and vecchio["sha256"] == digest:
                riepilogo["invariati"] += 1
                continue
            if vecchio:
                riepilogo["modificati"].append(chiave)
                vecchio.setdefault("revisioni_precedenti", []).append(
                    {"sha256": vecchio["sha256"], "scaricato": vecchio["scaricato"]}
                )

            man["file"][chiave] = {
                "fonte": T.FONTE,
                "campionato": league,
                "stagione": target.season,
                "risorsa": "voti" if giornata is not None else "quotazioni",
                "giornata": giornata,
                "url": (target.url(giornata) if giornata is not None
                        else T.TargetQuote(league, target.season).url),
                "scaricato": datetime.fromtimestamp(
                    percorso.stat().st_mtime, timezone.utc).isoformat(timespec="seconds"),
                "registrato": ora,
                "byte": percorso.stat().st_size,
                "byte_html": len(P.leggi(percorso)),
                "sha256": digest,
                "sha256_html": hashlib.sha256(P.leggi(percorso)).hexdigest(),
                **({"revisioni_precedenti": vecchio["revisioni_precedenti"]}
                   if vecchio and "revisioni_precedenti" in vecchio else {}),
            }
            riepilogo["nuovi"] += 0 if vecchio else 1

        if verbose:
            print(f"  {target.season}: {presenti}/{T.N_GIORNATE + 1} pagine "
                  "(38 giornate + listone)")

    man["definizioni"] = DEFINIZIONI
    man["aggiornato"] = ora
    config.MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    config.MANIFEST.write_text(
        json.dumps(man, indent=1, ensure_ascii=False, sort_keys=True), encoding="utf-8")
    return riepilogo


def registra_assenti(voci: list[dict]) -> int:
    """Registra le partite che **esistono nel calendario ma non hanno dati**.

    E' provenienza dell'assenza, e serve quanto quella della presenza: senza,
    la prossima sessione vede 374 CSV su 380, non sa perche', e ritenta. Le 12
    partite del 2021-22 e 2022-23 sono state verificate una per una — tutte con
    `matchCentreData: null` — e ritentarle non le recupera.
    """
    man = carica()
    ora = datetime.now(timezone.utc).isoformat(timespec="seconds")
    assenti = man.setdefault("assenti_alla_fonte", {})
    for v in voci:
        assenti[f"{v['stagione']}/{v['match_id']}"] = {**v, "verificato": ora,
                                                       "motivo": "matchCentreData null"}
    man["aggiornato"] = ora
    config.MANIFEST.write_text(
        json.dumps(man, indent=1, ensure_ascii=False, sort_keys=True), encoding="utf-8")
    return len(assenti)


if __name__ == "__main__":
    totale = {"nuovi": 0, "invariati": 0, "modificati": []}
    for nome, funzione in (("whoscored", registra_whoscored),
                           ("fantacalcio", registra_fantacalcio)):
        print(f"\n{nome}:")
        r = funzione()
        for k in ("nuovi", "invariati"):
            totale[k] += r[k]
        totale["modificati"] += r["modificati"]
    print(f"\nnuovi {totale['nuovi']} | invariati {totale['invariati']} | "
          f"MODIFICATI {len(totale['modificati'])}")
    for k in totale["modificati"]:
        print(f"  !! contenuto cambiato: {k}")
    print(f"-> {config.MANIFEST}")
