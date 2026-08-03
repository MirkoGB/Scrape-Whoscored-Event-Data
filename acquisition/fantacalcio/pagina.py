# -*- coding: utf-8 -*-
"""Il parser della vista voti di `fantacalcio.it`. Funzione pura, niente rete.

Tutta la conoscenza del markup della fonte sta qui dentro e da nessun'altra
parte. Il modulo **non scarica e non scrive**: prende i byte di una pagina e
restituisce righe. Ne segue che si prova su una pagina sintetica di venti
righe, senza connessione — che e' l'unico modo di avere test veri su uno
scraper.

## Il contratto del markup, accertato leggendo tre pagine di tre stagioni

    ul.teams
      li#team-<idSquadra>.team-table
        table.grades-table
          thead   nome della squadra, le tre scale, le otto voci di bonus
          tbody
            tr
              span.role[data-value]         p | d | c | a | all
              a.player-name[href .../<id>/<stagione>]   assente per gli allenatori
              img.player-icon[title]        "Subentrato" | "Sostituito"
              div.pill x3                   Redazione | Statistico | Italia, in
                span.player-grade           quest'ordine fisso
                span.player-fanta-grade
              span.player-bonus[title] x8
    nav.match-menu-container
      li.match[data-teams-id="<casa>|<trasferta>"]      il calendario di giornata

Cinque cose che il markup dice e che non si vedono guardando la pagina resa:

1. **`data-value="55"` non e' un voto: e' il codice dell's.v.** Sulle cinque
   stagioni compare 15.397 volte, e mai su un titolare. `56` esiste, 10 volte in
   tutto, e **mai sulla scala Redazione**. Entrambi sono conservati in una
   colonna a parte invece di diventare nulli anonimi: sono due codici diversi
   della fonte e appiattirli mescolerebbe due grandezze (vincolo 7).
   **La soglia che li riconosce vale sul voto e non sul fantavoto**, che ha un
   altro dominio — vedi `_pill`, dove sta l'unico errore che questo parser ha
   davvero commesso.
2. **I cartellini non sono una colonna di bonus.** Le otto voci di bonus non li
   contengono. Stanno come **classe CSS sullo span del voto**: `yellow-card` e
   `red-card`. Chi legge solo `data-value` li perde in silenzio, e sono −0,5 e
   −1 nel fantavoto.
3. **Venti righe per pagina sono allenatori**, non giocatori: `role="all"`,
   nessun link, e prendono un voto come tutti. Vanno tenute distinte o il conto
   dei giocatori sbaglia di venti per giornata.
4. **Le venti tabelle sono in ordine alfabetico di squadra, non appaiate per
   partita.** L'accoppiamento si fa solo passando dal calendario in cima alla
   pagina, via `data-teams-id`. Chi assumesse "due tabelle consecutive = una
   partita" otterrebbe avversari sbagliati per tutte e dieci le partite.
5. **In tabella ci sono solo i giocatori scesi in campo**, non la rosa: i
   panchinari non usati non hanno riga. La "presenza fantacalcistica" e' un
   sottoinsieme ancora piu' piccolo (chi prende un voto numerico).

## Cosa succede se il markup cambia

Si solleva `MarkupInatteso` e la pagina non entra nel dataset. E' il requisito
di `docs/regole_fantacalcio.md` §4.2 — "rilevazione dei cambiamenti di struttura
HTML, segnalati e non assorbiti" — e la lezione della Fase 7 su `StandingSave`:
un'etichetta della fonte puo' cambiare significato senza che schema e conteggi
si muovano di un bit.
"""

from __future__ import annotations

import gzip
import re
from pathlib import Path

from bs4 import BeautifulSoup

# Le tre scale, nell'ordine fisso in cui la fonte le affianca in ogni riga.
# Prendere la Redazione — la scala scelta dall'utente (§7.1, decisione 5) — non
# costa una richiesta in piu': le altre due arrivano insieme e si scartano in
# lettura. Vengono conservate lo stesso, perche' scartare in scrittura sarebbe
# irreversibile e la scelta della scala e' di modello, non di acquisizione.
SCALE = ("redazione", "statistico", "italia")
TITOLI_SCALE = ("Redazione Fantacalcio", "Voto Statistico", "Voto Italia")

# Le otto voci di bonus, nell'ordine dichiarato dai `data-key` del thead. Il
# nome italiano e' il `title` dello span nella riga; i due elenchi vanno tenuti
# allineati perche' il contratto si verifica su entrambi.
BONUS = (
    ("scoredGoals", "gol_segnati", "Gol segnati"),
    ("concededGoals", "gol_subiti", "Gol subiti"),
    ("ownGoals", "autoreti", "Autoreti"),
    ("scoredPenalties", "rigori_segnati", "Rigori segnati"),
    ("missedPenalties", "rigori_sbagliati", "Rigori sbagliati"),
    ("savedPenalties", "rigori_parati", "Rigori parati"),
    ("assists", "assist", "Assist"),
    ("manOfTheMatch", "player_of_the_match", "Player of the match"),
)

# Il barema **della fonte**, non quello della lega dell'utente. Non e' una
# congettura: e' stato ricavato per differenza e verificato esattamente su 895
# righe di tre stagioni (residuo 0,00 su tutte). Vale FV = V + questo.
#
# Due cose che ne discendono e che il documento di lega non dice:
#   - **il gol su rigore NON e' in `scoredGoals`**: sta solo in
#     `scoredPenalties` e vale +3 una volta sola. Sommare le due colonne
#     conterebbe due volte lo stesso gol;
#   - **`manOfTheMatch` non entra nel fantavoto** della fonte, benche' abbia una
#     colonna. E' un'opzione di lega, e nella lega dell'utente non c'e'.
#
# Manca invece, rispetto a `regole_fantacalcio.md` §1.1, il **+1 di porta
# inviolata**: il FV della fonte non lo applica. Quindi il fantavoto della lega
# **non e' quello della fonte** e va ricalcolato dai bonus, mai letto da `FV`.
BAREME_FONTE = {
    "gol_segnati": +3.0,
    "gol_subiti": -1.0,
    "autoreti": -2.0,
    "rigori_segnati": +3.0,
    "rigori_sbagliati": -3.0,
    "rigori_parati": +3.0,
    "assist": +1.0,
    "player_of_the_match": 0.0,
    "ammonizione": -0.5,
    "espulsione": -1.0,
}

RUOLI = {"p", "d", "c", "a", "all"}
N_SQUADRE = 20
_ID_SQUADRA = re.compile(r"^team-(\d+)$")
_ID_PARTITA = re.compile(r"^match-(\d+)$")
# .../squadre/<squadra>/<nome>/<idGiocatore>/<stagione>
_ID_GIOCATORE = re.compile(r"/squadre/[^/]+/[^/]+/(\d+)/")


class ListoneNonPubblicato(RuntimeError):
    """La pagina c'e' ed e' sana: e' il listone che non esiste ancora.

    Distinta da `MarkupInatteso` perche' significa una cosa diversa e chiede una
    reazione diversa: qui non c'e' niente da guardare e niente da correggere, si
    torna piu' avanti. Confonderle manderebbe in quarantena una pagina sana.
    """


class MarkupInatteso(RuntimeError):
    """Il markup non rispetta il contratto: la pagina non entra nel dataset.

    Distinta da un'eccezione di rete o di parsing generico perche' significa una
    cosa sola e precisa: **la fonte e' cambiata**. Ritentare non serve; serve
    guardare la pagina.
    """


# --------------------------------------------------------------------------
# I/O del grezzo — leggere e scrivere gli stessi byte
# --------------------------------------------------------------------------

def scrivi(percorso: Path, html: bytes) -> None:
    """Scrive la pagina compressa. `mtime=0` per rendere il file deterministico.

    Senza `mtime=0` gzip incorpora l'istante di scrittura: lo stesso HTML
    darebbe file con hash diverso a ogni esecuzione, e il manifest segnalerebbe
    "contenuto cambiato" su dati identici — cioe' l'allarme che il vincolo 9
    vuole affidabile diventerebbe rumore.
    """
    percorso.parent.mkdir(parents=True, exist_ok=True)
    percorso.write_bytes(gzip.compress(html, mtime=0))


def leggi(percorso: Path) -> bytes:
    """Gli stessi byte arrivati dalla rete. La compressione e' senza perdita."""
    return gzip.decompress(Path(percorso).read_bytes())


# --------------------------------------------------------------------------
# Il parser
# --------------------------------------------------------------------------

def _numero(valore: str) -> float | None:
    if valore is None or valore.strip() == "":
        return None
    try:
        return float(valore.strip().replace(",", "."))
    except ValueError:
        raise MarkupInatteso(f"valore non numerico: {valore!r}")


# Un voto sta in 0-10 e nei dati osservati non esce da 3,0-9,5. Un **fantavoto**
# no: un attaccante da 8 con due gol fa 14, e nelle cinque stagioni si arriva a
# 21 e si scende a -2. Sono due grandezze con due domini diversi, e la soglia
# vale solo sulla prima.
VOTO_MASSIMO = 10.0


def _pill(tag_voto, tag_fantavoto) -> tuple[float | None, float | None, int | None]:
    """Voto, fantavoto e codice di s.v. di **una** delle tre scale.

    La sentinella si riconosce dal **voto**, mai dal fantavoto, ed e' il punto
    in cui la prima versione di questo parser sbagliava. Applicare la soglia dei
    10 a entrambi sembra simmetrico e non lo e': `"14"` e' un fantavoto vero e
    diventava un codice inesistente, e in cambio ~1.000 righe — proprio quelle
    dei marcatori — uscivano dalla riconciliazione senza far rumore, perche' un
    residuo nullo si filtra da solo.

    Quando il voto e' una sentinella, **tutta la pill e' s.v.** e il fantavoto e'
    nullo qualunque cosa dica il suo `data-value`. Non e' un dettaglio teorico:
    su 8 righe delle cinque stagioni — tutte subentrati, tutte sulle scale
    Statistico e Italia, mai sulla Redazione — il voto e' `56` e il fantavoto e'
    `0`. Quello zero non e' un fantavoto: e' l'assenza resa come numero, e
    prenderlo per buono inietterebbe uno zero nella distribuzione.
    """
    voto = _numero(tag_voto.get("data-value"))
    if voto is not None and voto > VOTO_MASSIMO:
        return None, None, int(voto)
    return voto, _numero(tag_fantavoto.get("data-value")), None


def _contratto(soup: BeautifulSoup) -> list:
    tabelle = soup.select("li.team-table")
    if len(tabelle) != N_SQUADRE:
        raise MarkupInatteso(
            f"{len(tabelle)} tabelle di squadra invece di {N_SQUADRE}"
        )
    prima = tabelle[0].select_one("table.grades-table")
    if prima is None:
        raise MarkupInatteso("nessuna table.grades-table dentro li.team-table")
    titoli = [i.get("title") for i in prima.select("thead div.group img")]
    if tuple(titoli) != TITOLI_SCALE:
        raise MarkupInatteso(
            f"le scale non sono {TITOLI_SCALE} ma {tuple(titoli)}: "
            "l'ordine delle tre colonne di voto e' cambiato"
        )
    chiavi = tuple(f.get("data-key") for f in prima.select("thead figure.bonus-icon"))
    attese = tuple(k for k, _, _ in BONUS)
    if chiavi != attese:
        raise MarkupInatteso(
            f"le voci di bonus sono {chiavi} invece di {attese}: "
            "la fonte ne ha aggiunta, tolta o riordinata una"
        )
    return tabelle


def _partite(soup: BeautifulSoup, giornata: int) -> list[dict]:
    fuori = []
    for li in soup.select("nav.match-menu-container li.match"):
        m = _ID_PARTITA.match(li.get("id") or "")
        ids = (li.get("data-teams-id") or "").split("|")
        if m is None or len(ids) != 2:
            raise MarkupInatteso(f"partita senza id o senza data-teams-id: {li.get('id')!r}")
        casa = li.select_one("label.team-home a.team-name")
        trasferta = li.select_one("label.team-away a.team-name")
        data = li.select_one("meta[itemprop=startDate]")
        gh = li.select_one("span.score-home")
        ga = li.select_one("span.score-away")
        settimana = li.select_one("div.matchweek")
        if settimana is not None and settimana.get_text(strip=True).isdigit():
            dichiarata = int(settimana.get_text(strip=True))
            if dichiarata != giornata:
                raise MarkupInatteso(
                    f"la pagina della giornata {giornata} contiene una partita "
                    f"dichiarata di giornata {dichiarata}"
                )
        fuori.append({
            "partita_id": int(m.group(1)),
            "casa_id": int(ids[0]),
            "trasferta_id": int(ids[1]),
            "casa": casa.find("meta").get("content") if casa else None,
            "trasferta": trasferta.find("meta").get("content") if trasferta else None,
            "data": data.get("content") if data is not None else None,
            "gol_casa": _intero(gh),
            "gol_trasferta": _intero(ga),
            "stadio": (li.select_one("span.stadium").get_text(strip=True)
                       if li.select_one("span.stadium") else None),
        })
    if len(fuori) != N_SQUADRE // 2:
        raise MarkupInatteso(f"{len(fuori)} partite in calendario invece di {N_SQUADRE // 2}")
    return fuori


def _intero(tag) -> int | None:
    if tag is None:
        return None
    testo = tag.get_text(strip=True)
    return int(testo) if testo.isdigit() else None


def _riga(tr, squadra_id: int, squadra: str) -> dict:
    ruolo_tag = tr.select_one("span.role")
    if ruolo_tag is None:
        raise MarkupInatteso("riga senza span.role")
    ruolo = ruolo_tag.get("data-value")
    if ruolo not in RUOLI:
        raise MarkupInatteso(f"ruolo {ruolo!r} fuori da {sorted(RUOLI)}")

    link = tr.select_one("a.player-name")
    if link is not None:
        nome = link.get_text(strip=True)
        trovato = _ID_GIOCATORE.search(link.get("href") or "")
        if trovato is None:
            raise MarkupInatteso(f"link giocatore senza id: {link.get('href')!r}")
        giocatore_id = int(trovato.group(1))
    else:
        # Gli allenatori non hanno pagina profilo, quindi non hanno id. E' il
        # solo caso legittimo di riga senza link, e coincide con `ruolo == all`:
        # se un giorno un *giocatore* arrivasse senza link, questo controllo lo
        # fa emergere invece di dargli id nullo in silenzio.
        if ruolo != "all":
            raise MarkupInatteso(f"riga di ruolo {ruolo!r} senza link al giocatore")
        nodo = tr.select_one("span.player-name")
        nome = nodo.get_text(strip=True) if nodo is not None else None
        giocatore_id = None

    voti = tr.select("span.player-grade")
    fanta = tr.select("span.player-fanta-grade")
    if len(voti) != len(SCALE) or len(fanta) != len(SCALE):
        raise MarkupInatteso(
            f"{len(voti)} voti e {len(fanta)} fantavoti invece di {len(SCALE)}"
        )

    riga = {
        "squadra_id": squadra_id,
        "squadra": squadra,
        "giocatore_id": giocatore_id,
        "giocatore": nome,
        "ruolo": ruolo,
        "allenatore": ruolo == "all",
    }

    # I cartellini stanno sullo span del voto, una scala alla volta. Sono un
    # fatto della partita, non un giudizio, quindi devono coincidere fra le tre
    # scale: se non coincidessero, una delle due letture sarebbe sbagliata e va
    # vista, non mediata.
    gialli = {("yellow-card" in (v.get("class") or [])) for v in voti}
    rossi = {("red-card" in (v.get("class") or [])) for v in voti}
    if len(gialli) > 1 or len(rossi) > 1:
        raise MarkupInatteso(
            f"{nome}: cartellini discordanti fra le tre scale "
            f"(gialli {gialli}, rossi {rossi})"
        )
    riga["ammonizione"] = gialli.pop()
    riga["espulsione"] = rossi.pop()

    for scala, v, fv in zip(SCALE, voti, fanta):
        voto, fantavoto, codice = _pill(v, fv)
        riga[f"voto_{scala}"] = voto
        riga[f"fantavoto_{scala}"] = fantavoto
        riga[f"codice_sv_{scala}"] = codice

    bonus = tr.select("span.player-bonus")
    if len(bonus) != len(BONUS):
        raise MarkupInatteso(f"{len(bonus)} voci di bonus invece di {len(BONUS)}")
    for (_, campo, titolo), span in zip(BONUS, bonus):
        if span.get("title") != titolo:
            raise MarkupInatteso(
                f"voce di bonus {span.get('title')!r} dove era attesa {titolo!r}"
            )
        riga[campo] = int(span.get("data-value"))

    icone = {i.get("title") for i in tr.select("img.player-icon")}
    riga["subentrato"] = "Subentrato" in icone
    riga["sostituito"] = "Sostituito" in icone
    return riga


# Le colonne del listone, nell'ordine dei `data-col-key` del thead. `QI` e'
# la quotazione **iniziale**, cioe' il prezzo di partenza dell'asta e l'unica
# che serva alla verifica del progetto; `QA` e' l'attuale, un valore corrente e
# non una serie storica; `FVM` e' il Fanta Valore di Mercato della fonte.
COLONNE_QUOTE = (
    ("c_qi", "qi_classic"), ("c_qa", "qa_classic"), ("c_fvm", "fvm_classic"),
    ("m_qi", "qi_mantra"), ("m_qa", "qa_mantra"), ("m_fvm", "fvm_mantra"),
)


def analizza_quote(html: bytes, stagione: str) -> list[dict]:
    """Il listone di una stagione: una riga per giocatore quotato.

    **L'universo non e' quello dei voti**, e la differenza conta: il listone
    contiene chi era quotabile a inizio stagione, i voti chi e' poi sceso in
    campo. Ci sono quotati con zero presenze e — meno ovvio — giocatori con voti
    che nel listone non ci sono, perche' arrivati a mercato aperto.

    `data-filter-team-id` e l'id nel link del giocatore sono **gli stessi** della
    vista voti: l'aggancio fra listone e voti non passa dai nomi e non ha
    bisogno di nessuna euristica. E' l'unico punto di tutta la Fase 8 in cui due
    tabelle condividono davvero una chiave.
    """
    soup = BeautifulSoup(html, "lxml")
    tabella = soup.select_one("table.pills-table")
    if tabella is None:
        # **"Dati non disponibili" non e' un markup cambiato**, ed e' la
        # distinzione che questa funzione all'inizio non faceva. Un listone non
        # ancora pubblicato — succede per la stagione entrante, verificato sulla
        # 2026-27 il 2026-08-03 — produce una pagina regolare, con la sua
        # intestazione, e senza tabella. Trattarlo come rottura del contratto
        # manda in quarantena una pagina sana e fa cercare un difetto che non
        # c'e'. E' la stessa lezione dei `matchCentreData: null` di WhoScored:
        # dati assenti alla fonte si dichiarano, pagine inattese si ritentano.
        if "Dati non disponibili" in soup.get_text(" ", strip=True):
            raise ListoneNonPubblicato(
                f"il listone {stagione} non e' ancora pubblicato: la pagina "
                "esiste e dichiara 'Dati non disponibili'"
            )
        raise MarkupInatteso("nessuna table.pills-table nel listone")
    chiavi = tuple(th.get("data-col-key") for th in tabella.select("thead th[data-col-key]"))
    attese = tuple(k for k, _ in COLONNE_QUOTE)
    if chiavi[:1] != ("sq",) or chiavi[1:] != attese:
        raise MarkupInatteso(
            f"colonne del listone {chiavi} invece di {('sq',) + attese}")

    fuori = []
    for tr in tabella.select("tbody tr.player-row"):
        link = tr.select_one("a.player-link")
        trovato = _ID_GIOCATORE.search(link.get("href") or "") if link else None
        if trovato is None:
            raise MarkupInatteso(f"riga di listone senza id giocatore: {tr.get('data-index')}")
        riga = {
            "stagione": stagione,
            "giocatore_id": int(trovato.group(1)),
            "giocatore": link.get_text(strip=True),
            "squadra_id": int(tr.get("data-filter-team-id")),
            "squadra_sigla": (tr.select_one("td.player-team").get_text(strip=True)
                              if tr.select_one("td.player-team") else None),
            "ruolo_classic": (tr.select_one("span.role").get("data-value")
                              if tr.select_one("span.role") else None),
            "ruolo_mantra": (tr.select_one("span.role-mantra").get("data-value")
                             if tr.select_one("span.role-mantra") else None),
            # L'asterisco "Non gioca piu' in Serie A" e' un'annotazione fatta
            # **dopo**, non uno stato di inizio stagione: si conserva come tale.
            "fuori_dal_campionato": tr.select_one("span.out-of-game") is not None,
        }
        for chiave, campo in COLONNE_QUOTE:
            cella = tr.select_one(f"td[data-col-key='{chiave}']")
            testo = cella.get_text(strip=True) if cella is not None else ""
            # `-` non e' uno zero: e' "non pubblicato". Il FVM non esiste sulle
            # stagioni piu' vecchie, e metterlo a zero direbbe che quei
            # giocatori valgono niente.
            riga[campo] = None if testo in ("", "-") else int(testo)
        fuori.append(riga)

    if not fuori:
        raise MarkupInatteso("listone vuoto")
    return fuori


def analizza(html: bytes, stagione: str, giornata: int) -> dict:
    """Da byte HTML a `{"partite": [...], "righe": [...]}`. Non tocca la rete.

    `stagione` e `giornata` non si leggono dalla pagina ma si passano: sono il
    bersaglio richiesto, e confrontarli con cio' che la pagina dichiara e' il
    modo di accorgersi di un redirect silenzioso. La fonte, richiesta di una
    giornata che non esiste, potrebbe servirne un'altra senza dirlo.
    """
    soup = BeautifulSoup(html, "lxml")
    tabelle = _contratto(soup)
    partite = _partite(soup, giornata)

    # squadra -> avversario, in un verso e nell'altro. Passa dal calendario e
    # non dall'ordine delle tabelle, che e' alfabetico (punto 4 del contratto).
    avversario = {}
    for p in partite:
        avversario[p["casa_id"]] = (p, True)
        avversario[p["trasferta_id"]] = (p, False)

    righe = []
    for li in tabelle:
        m = _ID_SQUADRA.match(li.get("id") or "")
        if m is None:
            raise MarkupInatteso(f"tabella di squadra senza id: {li.get('id')!r}")
        squadra_id = int(m.group(1))
        nodo = li.select_one("table.grades-table thead a.team-name meta[itemprop=name]")
        squadra = nodo.get("content") if nodo is not None else None
        if squadra_id not in avversario:
            raise MarkupInatteso(
                f"la squadra {squadra!r} (id {squadra_id}) ha una tabella di voti "
                "ma non compare nel calendario di giornata"
            )
        partita, in_casa = avversario[squadra_id]
        for tr in li.select("table.grades-table tbody tr"):
            riga = _riga(tr, squadra_id, squadra)
            riga.update({
                "stagione": stagione,
                "giornata": giornata,
                "partita_id": partita["partita_id"],
                "data": partita["data"],
                "casa": in_casa,
                "avversario_id": partita["trasferta_id"] if in_casa else partita["casa_id"],
                "avversario": partita["trasferta"] if in_casa else partita["casa"],
            })
            righe.append(riga)

    return {"stagione": stagione, "giornata": giornata,
            "partite": partite, "righe": righe}
