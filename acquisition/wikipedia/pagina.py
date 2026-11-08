# -*- coding: utf-8 -*-
"""Il parser del calendario di Wikipedia. **Funzione pura: HTML dentro, righe fuori.**

Non tocca la rete e non conosce i percorsi: tutta la conoscenza del markup della
fonte sta qui, come in `acquisition/fantacalcio/pagina.py`.

LE DUE TRAPPOLE DI QUESTA FONTE
-------------------------------
1. **La cella della partita e' TESTO, non due link.** Contiene `Atalanta-Sassuolo`
   in un solo `<td>`, senza `<a>` da cui prendere i due nomi. Spezzare sul primo
   `-` funziona in Serie A e **sbaglia in Ligue 1**, dove esistono `Saint-Étienne`
   e `Le Havre`... e in Bundesliga, dove il trattino sta dentro i nomi di mezza
   classifica. Per questo `dividi()` **non indovina**: prova ogni posizione e
   tiene solo quella in cui **entrambe** le meta' sono squadre note, e solleva se
   le soluzioni sono zero o piu' di una. E' la stessa forma con cui l'aggancio
   della Fase 8 ha risolto i cognomi: si usa un elenco noto come vincolo, non una
   regola tipografica.

2. **Una partita da giocare mostra l'ORARIO dove una giocata mostra il
   risultato.** `2-1` e `20:45` stanno nella stessa colonna, ed e' esattamente
   l'ambiguita' che la Fase 14 aveva dichiarato come domanda aperta. Qui si
   separa sul **separatore** — `-` per il punteggio, `:` per l'ora — che e' una
   proprieta' di QUESTA fonte: su WhoScored il discriminante e' `/live/`
   nell'href, e i due criteri **non si scambiano** (vincolo 7).
"""

from __future__ import annotations

import re

from bs4 import BeautifulSoup as soup

#: Il criterio con cui si separa una partita giocata da una da giocare **su
#: questa fonte**. Dichiarato prima, e diverso da quello di WhoScored di
#: proposito: due fonti, due discriminanti.
CRITERIO_GIOCATA = (
    "giocata <=> la cella dell'esito ha la forma 'a-b' con a e b interi. "
    "NON giocata: un orario ('20:45'), un trattino nudo ('-') o una cella "
    "vuota. Tutto il resto e' illeggibile e si dichiara."
)

#: I marcatori con cui questa fonte dice "non c'e' ancora un risultato".
#:
#: **Il trattino nudo e' stato aggiunto dopo la prima esecuzione**, e va detto:
#: il criterio dichiarato prima elencava solo l'orario e la cella vuota, e su
#: Premier, Bundesliga e Ligue 1 ha prodotto centinaia di righe `illeggibile`.
#: Non e' una soglia ritoccata per far tornare un numero — e' il completamento
#: dell'elenco dei marcatori della fonte, che non si potevano conoscere prima di
#: guardarla, e la distinzione fra le due cose e' quella che il vincolo 1
#: protegge.
SENZA_RISULTATO = ("", "-", "–", "—")

_RE_PUNTEGGIO = re.compile(r"^\s*(\d{1,2})\s*[-–]\s*(\d{1,2})\s*$")
_RE_ORARIO = re.compile(r"^\s*\d{1,2}\s*:\s*\d{2}\s*$")
_RE_GIORNATA = re.compile(r"^\s*(\d{1,2})\s*[ªa°]?\s*giornata\s*$", re.IGNORECASE)


def e_giocata(esito: str):
    """`True` giocata, `False` da giocare, `None` illeggibile.

    Tre esiti e non due, per la ragione per cui `verifica_calendario` ne ha tre:
    una cella vuota — che su Wikipedia e' frequentissima, perche' l'orario di una
    giornata lontana non e' ancora fissato — **non e' una partita giocata** e non
    e' nemmeno un errore. Trattarla come `False` sarebbe corretto per caso;
    trattarla come `True` riempirebbe il calendario di partite inventate.
    """
    t = (esito or "").strip()
    if _RE_PUNTEGGIO.match(t):
        return True
    if _RE_ORARIO.match(t) or t in SENZA_RISULTATO:
        return False
    return None


#: Il titolo della sezione delle squadre. **Si cerca il TITOLO nell'HTML, non
#: l'indice di sezione dell'API**: l'indice cambia appena qualcuno ne aggiunge
#: una sopra, e chiedere la sezione sbagliata non da' nessun errore.
TITOLO_SQUADRE = "Squadre partecipanti"


def _tabella_dopo(s, titolo: str):
    """La prima tabella che segue l'intestazione con quel titolo."""
    for tag in s.find_all(["h2", "h3", "h4"]):
        if titolo.lower() in tag.get_text(" ", strip=True).lower():
            return tag.find_next("table")
    return None


def squadre(html: str) -> list[str]:
    """I nomi delle squadre partecipanti, dalla prima colonna della tabella.

    E' l'elenco che `dividi()` usa come vincolo. Prenderlo dalla stessa pagina —
    invece che dall'altra fonte — tiene il parser **indipendente**: se lo si
    alimentasse con i nomi di WhoScored, il confronto fra le due fonti non
    sarebbe piu' un confronto.

    Si lavora sull'HTML **dell'intera pagina** e si trova la tabella dal suo
    titolo. La prima stesura chiedeva all'API la singola sezione, e ha scoperto
    per errore che la struttura non e' la stessa nei cinque campionati: la
    divisione in "Girone di andata / di ritorno" e' una convenzione della pagina
    italiana della Serie A, e Premier e Bundesliga non ce l'hanno affatto.
    """
    s = soup(html, "lxml")
    tabella = _tabella_dopo(s, TITOLO_SQUADRE) or s.find("table")
    if tabella is None:
        raise ValueError("nessuna tabella nella sezione delle squadre: "
                         "il markup della fonte e' cambiato")
    fuori = []
    for tr in tabella.find_all("tr")[1:]:
        celle = tr.find_all(["th", "td"])
        if not celle:
            continue
        nome = celle[0].get_text(" ", strip=True)
        if nome and nome not in fuori:
            fuori.append(nome)
    if not fuori:
        raise ValueError("tabella delle squadre vuota")
    return fuori


def dividi(cella: str, note: set[str]) -> tuple[str, str]:
    """`'Atalanta-Sassuolo'` -> `('Atalanta', 'Sassuolo')`, contro nomi NOTI.

    **Non spezza sul primo trattino**: prova ogni posizione e tiene solo quella
    in cui entrambe le meta' sono squadre note. Se le soluzioni non sono
    esattamente una, solleva invece di sceglierne una — perche' scegliere
    produrrebbe una riga plausibile e sbagliata, che nessun controllo a valle
    saprebbe piu' distinguere da una giusta.
    """
    testo = (cella or "").strip()
    soluzioni = []
    for i, ch in enumerate(testo):
        if ch not in "-–":
            continue
        a, b = testo[:i].strip(), testo[i + 1:].strip()
        if a in note and b in note:
            soluzioni.append((a, b))
    if len(soluzioni) == 1:
        return soluzioni[0]
    raise ValueError(
        f"{testo!r} non si divide in due squadre note: {len(soluzioni)} "
        f"soluzioni. Squadre note: {sorted(note)}"
    )


def giornate(html: str, note) -> list[dict]:
    """Le partite della pagina, ognuna con la GIORNATA a cui appartiene.

    **Non si assume la posizione delle celle**, e questa non e' prudenza: la
    prima stesura pretendeva tre celle `(data, partita, esito)` e leggeva 72
    partite su 380. Dalla sesta giornata in poi Wikipedia usa un `rowspan` per la
    data e non scrive l'orario, quindi quelle righe hanno **una cella sola** — e
    sono la grande maggioranza del calendario, cioe' proprio le partite future
    che questo modulo esiste per raccogliere. Si cerca invece la cella che si
    **divide in due squadre note**, e si prendono data ed esito da quelle
    accanto, se ci sono.

    Le tabelle sono annidate: la stessa riga compare piu' volte scorrendo
    `find_all('tr')`. Si deduplica sulla tripla `(giornata, casa, trasferta)`,
    che e' la chiave vera, invece di fidarsi della struttura del documento. La
    riga esterna, il cui testo e' l'intero blob della giornata, non supera
    `dividi()` e si scarta da sola.

    **`data_fonte` puo' essere `None` e non e' un difetto**: con il `rowspan` la
    data appartiene al gruppo, non alla riga. Non viene ereditata dalla riga
    precedente, perche' sarebbe una ricostruzione non verificabile — e la data
    vera ce l'ha gia' l'altra fonte, che invece la giornata non ce l'ha.
    """
    note = set(note)
    s = soup(html, "lxml")

    fuori, viste = [], set()
    giornata = None
    for tr in s.find_all("tr"):
        testi = [c.get_text(" ", strip=True)
                 for c in tr.find_all(["th", "td"])]

        intestazioni = [t for t in testi if _RE_GIORNATA.match(t or "")]
        if intestazioni:
            giornata = int(_RE_GIORNATA.match(intestazioni[0]).group(1))
            continue
        if giornata is None:
            continue

        coppia = idx = None
        for i, t in enumerate(testi):
            try:
                coppia = dividi(t, note)
                idx = i
                break
            except ValueError:
                continue
        if coppia is None:
            continue

        chiave = (giornata, *coppia)
        if chiave in viste:
            continue
        viste.add(chiave)

        data = testi[idx - 1].strip() if idx > 0 else ""
        esito = testi[idx + 1].strip() if idx + 1 < len(testi) else ""
        fuori.append({
            "giornata": giornata,
            "data_fonte": data or None,
            "casa": coppia[0],
            "trasferta": coppia[1],
            "esito_grezzo": esito or None,
            "giocata": e_giocata(esito),
        })
    return fuori


def completezza(righe: list[dict], n_squadre: int) -> dict:
    """Quanto del calendario la fonte ha scritto. **Non e' una violazione.**

    Una stagione in corso su Wikipedia e' incompleta per definizione: il girone
    di ritorno viene scritto quando si avvicina. Confondere "incompleto" con
    "storto" farebbe scartare una fonte buona, ed e' l'errore che
    `scrape_quote.py` ha gia' evitato distinguendo "listone non ancora
    pubblicato" da "markup cambiato".

    **I denominatori si contano da `n_squadre`, mai assunti**: la Bundesliga ne
    ha 18 e fa 34 giornate, non 38 (§7.2).
    """
    attese_giornate = 2 * (n_squadre - 1)
    attese_partite = n_squadre * attese_giornate // 2
    viste = sorted({r["giornata"] for r in righe})
    return {
        "squadre": n_squadre,
        "giornate_attese": attese_giornate,
        "giornate_viste": len(viste),
        "partite_attese": attese_partite,
        "partite_viste": len(righe),
        "prima_giornata": min(viste) if viste else None,
        "ultima_giornata": max(viste) if viste else None,
        "completo": len(righe) == attese_partite,
    }


def verifica(righe: list[dict], n_squadre: int) -> dict:
    """Le violazioni di struttura, su un calendario anche PARZIALE.

    Cio' che si pretende vale a prescindere da quante giornate la fonte abbia
    scritto: **niente di piu' di quanto ci si aspetta**, mai niente di meno. Un
    calendario a meta' non e' un difetto (vedi `completezza`); un accoppiamento
    ripetuto lo e'.

    Ritorna un dizionario di violazioni; vuoto significa che i controlli passano.
    """
    problemi = {}
    attese_giornate = 2 * (n_squadre - 1)
    attese_partite = n_squadre * attese_giornate // 2
    per_giornata = n_squadre // 2

    if len(righe) > attese_partite:
        problemi["troppe_partite"] = f"{len(righe)} contro {attese_partite} attese"

    giornate_viste = sorted({r["giornata"] for r in righe})
    fuori = [g for g in giornate_viste if not 1 <= g <= attese_giornate]
    if fuori:
        problemi["giornata_fuori_intervallo"] = fuori

    conteggio = {}
    for r in righe:
        conteggio[r["giornata"]] = conteggio.get(r["giornata"], 0) + 1
    # una giornata PRESENTE deve essere completa: se ne mancano di intere e' la
    # fonte che non le ha ancora scritte, e lo dice `completezza`
    storte = {g: n for g, n in conteggio.items() if n > per_giornata}
    if storte:
        problemi["troppe_partite_in_una_giornata"] = storte

    # ogni coppia ordinata esattamente una volta: andata e ritorno, mai di piu'
    coppie = {}
    for r in righe:
        coppie.setdefault((r["casa"], r["trasferta"]), []).append(r["giornata"])
    ripetute = {f"{a}-{b}": g for (a, b), g in coppie.items() if len(g) > 1}
    if ripetute:
        problemi["accoppiamento_ripetuto"] = ripetute

    # una squadra gioca una volta per giornata
    doppie = {}
    for r in righe:
        for sq in (r["casa"], r["trasferta"]):
            doppie.setdefault((r["giornata"], sq), []).append(sq)
    male = {f"g{g} {sq}": len(v) for (g, sq), v in doppie.items() if len(v) > 1}
    if male:
        problemi["squadra_due_volte_nella_giornata"] = male

    illeggibili = [r for r in righe if r["giocata"] is None]
    if illeggibili:
        problemi["esito_illeggibile"] = [
            f"g{r['giornata']} {r['casa']}-{r['trasferta']}: {r['esito_grezzo']!r}"
            for r in illeggibili[:10]]

    return problemi
