# -*- coding: utf-8 -*-
"""Acquisizione dei voti da fantacalcio.it: bersagli, parser, idempotenza.

Girano **senza rete**. La pagina su cui il parser viene provato e' costruita qui
sotto riga per riga: e' l'unico modo di avere test veri su uno scraper, perche'
una pagina vera cambia sotto i piedi e un test che la scarica misura la fonte,
non il codice. La fixture riproduce il contratto del markup descritto in
`acquisition/fantacalcio/pagina.py`, **compresi i casi scomodi** — il codice di
s.v., il cartellino come classe CSS, la riga dell'allenatore senza link, e
l'ordine alfabetico delle tabelle che non coincide con l'accoppiamento delle
partite.
"""

from __future__ import annotations

import gzip
from pathlib import Path

import pytest

from acquisition.fantacalcio import pagina as P
from acquisition.fantacalcio import target as T
from sot import config

ROOT = Path(__file__).resolve().parent.parent

# Venti squadre in ordine alfabetico, con id **non** in ordine alfabetico: e' il
# caso reale (Cagliari ha id 21, Bologna 2) e serve a impedire che un parser
# indovini l'accoppiamento dall'ordine.
SQUADRE = [(f"Squadra{chr(65 + i)}", 100 + (i * 7) % 20) for i in range(20)]

# Dieci partite che accoppiano **la prima meta' con la seconda**: la squadra in
# posizione 0 gioca con quella in posizione 10, non con quella in posizione 1.
# Un parser che assumesse "due tabelle consecutive = una partita" sbaglierebbe
# tutti e dieci gli avversari, e questo test lo prende.
PARTITE = [(i, i + 10) for i in range(10)]


def _pill(voto: str, fantavoto: str, classe: str = "") -> str:
    cls = ("player-grade " + classe).strip()
    return (f'<div class="pill">'
            f'<span class="{cls}" data-value="{voto}"></span>'
            f'<span class="player-fanta-grade" data-value="{fantavoto}"></span>'
            f"</div>")


def _riga(nome, ruolo, voto, fantavoto, *, giocatore_id=None, cartellino="",
          bonus=None, icone=(), altre_scale=None):
    """`altre_scale` fa divergere Statistico e Italia dalla Redazione.

    Serve a un caso solo, ma e' quello: le tre scale non usano lo stesso
    vocabolario, e il codice `56` compare **solo** sulle altre due.
    """
    bonus = bonus or {}
    if giocatore_id is None:
        chi = f'<span class="player-name">{nome}</span>'
    else:
        chi = (f'<a class="player-name player-link" href="https://www.fantacalcio.it'
               f'/serie-a/squadre/x/{nome.lower()}/{giocatore_id}/2025-26">'
               f"<span>{nome}</span></a>")
    img = "".join(f'<img class="player-icon icon" title="{t}">' for t in icone)
    altre = altre_scale or [(voto, fantavoto), (voto, fantavoto)]
    pill = (_pill(voto, fantavoto, cartellino)
            + "".join(_pill(v, fv, cartellino) for v, fv in altre))
    voci = "".join(
        f'<span class="player-bonus cell" data-value="{bonus.get(campo, 0)}" '
        f'title="{titolo}"></span>'
        for _, campo, titolo in P.BONUS
    )
    return (
        "<tr>"
        f'<td><div class="player-item cell"><span class="role" data-value="{ruolo}"></span>'
        f"{chi}{img}</div></td>"
        f'<td><div class="group">{pill}</div></td>'
        f'<td><div class="group">{voci}</div></td>'
        "</tr>"
    )


def _thead(squadra: str) -> str:
    scale = "".join(f'<img title="{t}">' for t in P.TITOLI_SCALE)
    icone = "".join(f'<figure class="icon bonus-icon" data-key="{k}"></figure>'
                    for k, _, _ in P.BONUS)
    return (
        "<thead><tr>"
        f'<th><div class="team-info"><a class="team-name team-link" '
        f'href="https://www.fantacalcio.it/serie-a/squadre/{squadra.lower()}">'
        f'<meta itemprop="name" content="{squadra}"></a></div></th>'
        f'<th><div class="group">{scale}</div></th>'
        f'<th><div class="group">{icone}</div></th>'
        "</tr></thead>"
    )


def _calendario() -> str:
    voci = []
    for k, (i, j) in enumerate(PARTITE):
        casa, id_casa = SQUADRE[i]
        via, id_via = SQUADRE[j]
        voci.append(
            f'<li class="match" id="match-{900 + k}" data-teams-id="{id_casa}|{id_via}">'
            f'<div class="match-pill"><div class="matchweek">7</div>'
            f'<label class="team-home"><a class="team-name">'
            f'<meta itemprop="name" content="{casa}"></a></label>'
            f'<label class="team-away"><a class="team-name">'
            f'<meta itemprop="name" content="{via}"></a></label>'
            f'<a class="match-score"><span class="score-home">1</span>'
            f'<span class="score-away">0</span></a>'
            f'<div class="match-date"><meta itemprop="startDate" content="2025-10-05"></div>'
            f'<span class="stadium">Stadio {k}</span></div></li>'
        )
    return ('<nav class="match-menu-container"><ul class="matches" id="match-menu">'
            + "".join(voci) + "</ul></nav>")


def _righe_di(indice: int) -> str:
    """Undici righe uguali per tutte le squadre, piu' i casi scomodi sulla prima."""
    base = [
        _riga("Portiere", "p", "6", "5", giocatore_id=1000 + indice,
              bonus={"gol_subiti": 1}),
        _riga("Difensore", "d", "6", "6", giocatore_id=2000 + indice),
        _riga("Allenatore", "all", "6", "6"),          # nessun link: e' il tecnico
    ]
    if indice == 0:
        base += [
            # s.v.: il codice della fonte, non un voto. Solo sui subentrati.
            # Sulle altre due scale il codice e' `56` e il fantavoto e' reso
            # come `0` — che non e' un fantavoto, e' l'assenza scritta a numero.
            _riga("Subentrato", "c", "55", "55", giocatore_id=3000,
                  icone=("Subentrato",), altre_scale=[("56", "0"), ("55", "55")]),
            # ammonizione: −0,5, e sta nella CLASSE, non nei bonus
            _riga("Ammonito", "c", "6", "5,5", giocatore_id=3001,
                  cartellino="yellow-card"),
            # espulsione: −1
            _riga("Espulso", "d", "5", "4", giocatore_id=3002,
                  cartellino="red-card", icone=("Sostituito",)),
            # gol su rigore: +3 UNA volta sola, e non e' anche in gol_segnati
            _riga("Rigorista", "a", "6", "9", giocatore_id=3003,
                  bonus={"rigori_segnati": 1}),
            # player of the match: colonna valorizzata, zero nel fantavoto
            _riga("Migliore", "a", "7", "7", giocatore_id=3004,
                  bonus={"player_of_the_match": 1}),
            # doppietta: il FANTAVOTO esce dalla scala 0-10, e resta un numero.
            # E' il caso su cui la prima versione del parser sbagliava.
            _riga("Bomber", "a", "8", "14", giocatore_id=3005,
                  bonus={"gol_segnati": 2}),
            # autorete ed espulsione: il fantavoto va sotto zero
            _riga("Disastro", "d", "4", "1", giocatore_id=3006,
                  cartellino="red-card", bonus={"autoreti": 1}),
        ]
    return "".join(base)


def pagina_finta() -> bytes:
    tabelle = []
    for k, (squadra, id_squadra) in enumerate(SQUADRE):
        tabelle.append(
            f'<li id="team-{id_squadra}" class="team-table">'
            f'<div class="team-table-body"><table class="grades-table">'
            f"{_thead(squadra)}<tbody>{_righe_di(k)}</tbody></table></div></li>"
        )
    return (
        "<html><body>" + _calendario()
        + '<ul class="teams">' + "".join(tabelle) + "</ul></body></html>"
    ).encode("utf-8")


@pytest.fixture(scope="module")
def letta():
    return P.analizza(pagina_finta(), "2025-2026", 7)


# --------------------------------------------------------------------------
# Bersagli: percorsi e URL, senza rete
# --------------------------------------------------------------------------

def test_la_stagione_del_sito_e_a_due_cifre():
    assert T.stagione_sito("2025-2026") == "2025-26"
    assert T.stagione_sito("2021-2022") == "2021-22"


def test_la_forma_del_sito_non_entra_in_ingresso():
    """`2025-26` e' la forma della FONTE: in ingresso e' un errore, non un alias.

    E' la stessa regola per cui la cartella si chiama `ITA-serie-a` e non `I1`.
    Accettarla qui la farebbe entrare nei nomi di cartella dalla porta di
    servizio.
    """
    for cattiva in ("2025-26", "2526", "2025/2026", "2025"):
        with pytest.raises(ValueError):
            T.stagione_sito(cattiva)
        with pytest.raises(ValueError):
            T.TargetVoti(config.LEAGUE, cattiva)


def test_le_cinque_stagioni_hanno_percorsi_distinti():
    percorsi = {t.percorso(1) for t in T.targets()}
    assert len(percorsi) == len(config.SEASONS_STORICHE)


def test_senza_argomenti_sono_tutte_e_cinque():
    assert [t.season for t in T.targets()] == sorted(config.SEASONS_STORICHE)


def test_url_e_percorso_di_una_giornata():
    t = T.TargetVoti("ITA-serie-a", "2021-2022")
    assert t.url(1) == "https://www.fantacalcio.it/voti-fantacalcio-serie-a/2021-22/1"
    assert t.percorso(1).name == "01.html.gz"
    assert t.percorso(38).name == "38.html.gz"
    assert t.percorso(1).parent.parent == config.raw_dir("fantacalcio", t.league, t.season)


def test_le_giornate_fuori_scala_sono_rifiutate():
    t = T.TargetVoti()
    for cattiva in (0, 39, -1):
        with pytest.raises(ValueError):
            t.url(cattiva)
    with pytest.raises(TypeError):
        t.url("1")


def test_un_campionato_senza_percorso_verificato_non_si_inventa():
    with pytest.raises(ValueError, match="non e' stato verificato"):
        T.TargetVoti("ENG-premier-league", "2025-2026")


def test_lo_stato_si_legge_senza_rete():
    s = T.stato(T.TargetVoti())
    assert s["attese"] == T.N_GIORNATE
    assert s["presenti"] + len(s["mancanti"]) == T.N_GIORNATE


# --------------------------------------------------------------------------
# Il grezzo: compresso, senza perdita, deterministico
# --------------------------------------------------------------------------

def test_il_grezzo_torna_indietro_identico(tmp_path):
    html = pagina_finta()
    f = tmp_path / "07.html.gz"
    P.scrivi(f, html)
    assert P.leggi(f) == html


def test_la_compressione_e_deterministica(tmp_path):
    """Senza `mtime=0` lo stesso HTML darebbe hash diversi a ogni scrittura, e
    l'allarme "contenuto cambiato" del manifest diventerebbe rumore."""
    html = pagina_finta()
    a, b = tmp_path / "a.gz", tmp_path / "b.gz"
    P.scrivi(a, html)
    P.scrivi(b, html)
    assert a.read_bytes() == b.read_bytes()
    assert gzip.decompress(a.read_bytes()) == html


# --------------------------------------------------------------------------
# Il parser
# --------------------------------------------------------------------------

def test_venti_squadre_dieci_partite(letta):
    assert len(letta["partite"]) == 10
    assert len({r["squadra_id"] for r in letta["righe"]}) == 20


def test_l_avversario_viene_dal_calendario_non_dall_ordine(letta):
    """La squadra in posizione 0 gioca con quella in posizione 10.

    Un parser che accoppiasse le tabelle adiacenti darebbe `SquadraB`, che e'
    la riga successiva in ordine alfabetico. E' l'errore piu' facile da fare su
    questa pagina e il piu' difficile da notare a valle: i voti sarebbero giusti
    e gli avversari sbagliati.
    """
    per_squadra = {r["squadra"]: r for r in letta["righe"]}
    assert per_squadra[SQUADRE[0][0]]["avversario"] == SQUADRE[10][0]
    assert per_squadra[SQUADRE[0][0]]["casa"] is True
    assert per_squadra[SQUADRE[10][0]]["avversario"] == SQUADRE[0][0]
    assert per_squadra[SQUADRE[10][0]]["casa"] is False


def test_l_allenatore_e_distinto_dai_giocatori(letta):
    tecnici = [r for r in letta["righe"] if r["allenatore"]]
    assert len(tecnici) == 20                      # uno per squadra
    assert all(r["giocatore_id"] is None for r in tecnici)
    assert all(r["ruolo"] == "all" for r in tecnici)
    # e prende un voto come tutti: escluderlo e' una scelta di chi legge
    assert all(r["voto_redazione"] == 6.0 for r in tecnici)


def test_il_codice_di_sv_non_e_un_voto(letta):
    r = next(x for x in letta["righe"] if x["giocatore"] == "Subentrato")
    assert r["voto_redazione"] is None
    assert r["fantavoto_redazione"] is None
    assert r["codice_sv_redazione"] == 55
    assert r["subentrato"] is True


def test_le_tre_scale_non_usano_lo_stesso_codice(letta):
    """`56` esiste solo fuori dalla Redazione, e li' il fantavoto e' reso `0`.

    Quello zero non e' un fantavoto: e' l'assenza scritta a numero. Prenderlo
    per buono inietterebbe uno zero nella distribuzione dei fantavoti — un
    errore che nessun totale farebbe notare.
    """
    r = next(x for x in letta["righe"] if x["giocatore"] == "Subentrato")
    assert r["codice_sv_statistico"] == 56
    assert r["voto_statistico"] is None and r["fantavoto_statistico"] is None
    assert r["codice_sv_italia"] == 55


def test_un_fantavoto_sopra_dieci_resta_un_numero(letta):
    """Il caso su cui la prima versione del parser sbagliava.

    Un voto sta in 0-10, un fantavoto no: 8 con due gol fa 14. Applicare la
    soglia delle sentinelle a entrambi trasformava ~1.000 fantavoti veri in
    codici inesistenti — e quelle righe, diventate nulle, **uscivano dalla
    riconciliazione senza far rumore**, perche' un residuo nullo si filtra da
    solo. La verifica dichiarava esatte 53.775 righe su 53.775 saltando proprio
    quelle dei marcatori.
    """
    r = next(x for x in letta["righe"] if x["giocatore"] == "Bomber")
    assert r["voto_redazione"] == 8.0
    assert r["fantavoto_redazione"] == 14.0
    assert r["codice_sv_redazione"] is None


def test_un_fantavoto_sotto_zero_resta_un_numero(letta):
    r = next(x for x in letta["righe"] if x["giocatore"] == "Disastro")
    assert r["voto_redazione"] == 4.0
    assert r["fantavoto_redazione"] == 1.0
    assert r["autoreti"] == 1 and r["espulsione"] is True


def test_i_cartellini_stanno_nella_classe_non_nei_bonus(letta):
    """Il caso che ha giustificato la riconciliazione: le otto voci di bonus
    NON contengono i cartellini, che valgono −0,5 e −1 nel fantavoto."""
    giallo = next(x for x in letta["righe"] if x["giocatore"] == "Ammonito")
    rosso = next(x for x in letta["righe"] if x["giocatore"] == "Espulso")
    assert giallo["ammonizione"] is True and giallo["espulsione"] is False
    assert rosso["espulsione"] is True
    assert rosso["sostituito"] is True
    # nessuna delle otto voci di bonus e' valorizzata: se qualcuno un giorno
    # leggesse solo quelle, perderebbe entrambi i malus in silenzio
    assert all(giallo[c] == 0 for _, c, _ in P.BONUS)


def test_il_fantavoto_si_ricostruisce_dal_barema(letta):
    """FV = V + bonus, su ogni riga con un voto. E' la verifica che non passa da
    nessun modello, ed e' quella che ha fatto emergere i cartellini."""
    for r in letta["righe"]:
        if r["voto_redazione"] is None:
            continue
        atteso = sum(P.BAREME_FONTE[c] * r[c] for _, c, _ in P.BONUS)
        atteso += (P.BAREME_FONTE["ammonizione"] * r["ammonizione"]
                   + P.BAREME_FONTE["espulsione"] * r["espulsione"])
        assert round(r["fantavoto_redazione"] - r["voto_redazione"] - atteso, 2) == 0, r


def test_il_gol_su_rigore_vale_tre_una_volta_sola(letta):
    r = next(x for x in letta["righe"] if x["giocatore"] == "Rigorista")
    assert r["rigori_segnati"] == 1
    assert r["gol_segnati"] == 0          # il gol NON e' anche qui
    assert r["fantavoto_redazione"] - r["voto_redazione"] == 3.0


def test_player_of_the_match_non_entra_nel_fantavoto(letta):
    r = next(x for x in letta["righe"] if x["giocatore"] == "Migliore")
    assert r["player_of_the_match"] == 1
    assert r["fantavoto_redazione"] == r["voto_redazione"]
    assert P.BAREME_FONTE["player_of_the_match"] == 0.0


def test_la_porta_inviolata_non_e_nel_barema_della_fonte():
    """Il +1 di `regole_fantacalcio.md` §1.1 non c'e', e non e' una svista.

    E' la ragione per cui `fantavoto_redazione` **non e' il fantavoto della
    lega**: la riconciliazione torna esatta senza quel +1, quindi la fonte non
    lo applica. Un test lo blocca perche' la tentazione di leggere `FV` e
    chiamarlo fantavoto e' forte e costerebbe un punto per ogni clean sheet.
    """
    assert "porta_inviolata" not in P.BAREME_FONTE
    assert "clean_sheet" not in P.BAREME_FONTE


def test_le_tre_scale_arrivano_tutte(letta):
    r = next(x for x in letta["righe"] if x["giocatore"] == "Portiere")
    for scala in P.SCALE:
        assert f"voto_{scala}" in r and f"fantavoto_{scala}" in r


# --------------------------------------------------------------------------
# Il markup che cambia: si segnala, non si assorbe
# --------------------------------------------------------------------------

def test_scale_riordinate(letta):
    rotta = pagina_finta().replace(b"Voto Statistico", b"Voto Zzz")
    with pytest.raises(P.MarkupInatteso, match="scale"):
        P.analizza(rotta, "2025-2026", 7)


def test_una_voce_di_bonus_in_meno():
    rotta = pagina_finta().replace(b'data-key="assists"', b'data-key="qualcosAltro"')
    with pytest.raises(P.MarkupInatteso, match="bonus"):
        P.analizza(rotta, "2025-2026", 7)


def test_una_voce_di_bonus_rinominata_nella_riga():
    rotta = pagina_finta().replace(b'title="Assist"', b'title="Assistenze"')
    with pytest.raises(P.MarkupInatteso, match="bonus"):
        P.analizza(rotta, "2025-2026", 7)


def test_diciannove_squadre():
    intero = pagina_finta().decode()
    taglio = intero.rindex('<li id="team-')
    with pytest.raises(P.MarkupInatteso, match="tabelle di squadra"):
        P.analizza((intero[:taglio] + "</ul></body></html>").encode(), "2025-2026", 7)


def test_una_squadra_fuori_dal_calendario():
    """Ha una tabella di voti ma non compare fra le dieci partite.

    Succederebbe con un rinvio, e il rischio non e' un errore: e' che quella
    squadra prenda in silenzio l'avversario di un'altra.
    """
    rotta = pagina_finta().replace(
        f'data-teams-id="{SQUADRE[0][1]}|'.encode(),
        b'data-teams-id="999|')
    with pytest.raises(P.MarkupInatteso, match="calendario"):
        P.analizza(rotta, "2025-2026", 7)


def test_la_giornata_dichiarata_deve_coincidere():
    """Difesa contro un redirect silenzioso: chiedere la 7 e ricevere un'altra."""
    with pytest.raises(P.MarkupInatteso, match="giornata"):
        P.analizza(pagina_finta(), "2025-2026", 8)


def test_un_giocatore_senza_link_non_diventa_un_allenatore():
    rotta = pagina_finta().replace(
        b'<a class="player-name player-link" href="https://www.fantacalcio.it'
        b'/serie-a/squadre/x/difensore/2000/2025-26"><span>Difensore</span></a>',
        b'<span class="player-name">Difensore</span>')
    with pytest.raises(P.MarkupInatteso, match="senza link"):
        P.analizza(rotta, "2025-2026", 7)


# --------------------------------------------------------------------------
# Vincoli 8 e 9 verificati sul sorgente
# --------------------------------------------------------------------------

def test_lo_scraper_guarda_il_disco_prima_della_rete():
    """Vincolo 9 in forma eseguibile: `is_file()` deve precedere il `get`.

    Verificato sul sorgente e non sul comportamento perche' provarlo eseguendo
    significherebbe fare una richiesta vera, che e' esattamente cio' che il
    vincolo vuole evitare.
    """
    src = (ROOT / "acquisition" / "fantacalcio" / "scrape_voti.py").read_text(encoding="utf-8")
    corpo = src[src.index("def scarica_giornata"):src.index("def scarica_stagione")]
    assert corpo.index("is_file()") < corpo.index("sess.get")


def test_lo_scraper_non_sovrascrive_mai_il_grezzo():
    src = (ROOT / "acquisition" / "fantacalcio" / "scrape_voti.py").read_text(encoding="utf-8")
    corpo = src[src.index("def scarica_giornata"):src.index("def scarica_stagione")]
    # l'unica scrittura in raw/ e' preceduta dal ritorno anticipato
    assert 'return "saltata"' in corpo
    assert corpo.index('return "saltata"') < corpo.index("P.scrivi(fuori")


def test_bersagli_e_parser_non_importano_la_rete():
    """Sono la parte verificabile senza connessione, e devono restarlo."""
    for modulo in ("target.py", "pagina.py"):
        src = (ROOT / "acquisition" / "fantacalcio" / modulo).read_text(encoding="utf-8")
        assert "import requests" not in src, modulo


def test_un_rifiuto_non_si_ritenta():
    """401/403 non stanno fra i codici ritentabili: un rifiuto e' una risposta,
    non un inciampo, e insistere sarebbe la prima mossa di un aggiramento."""
    from acquisition.fantacalcio import scrape_voti as S
    assert 401 not in S.RITENTABILI and 403 not in S.RITENTABILI
    assert {500, 502, 503} <= S.RITENTABILI


def test_lo_user_agent_non_finge_di_essere_un_browser():
    ua = T.USER_AGENT.lower()
    assert "sot-serie-a-research" in ua
    for maschera in ("mozilla", "chrome", "safari", "gecko", "applewebkit"):
        assert maschera not in ua


def test_la_definizione_della_fonte_sta_nel_manifest():
    """Vincolo 8: la definizione della metrica *in quella fonte* viaggia con i
    dati. Per i voti non e' un dettaglio — un voto e' un giudizio editoriale,
    non un fatto, e senza quella riga qualcuno lo confondera' con una misura."""
    from acquisition import manifest
    d = manifest.DEFINIZIONI["fantacalcio"]
    assert "Redazione" in d["fornitore"]
    assert "assenti" in d["minuti"]
    assert "porta inviolata" in d["fantavoto"].lower() or "inviolata" in d["fantavoto"]


# --------------------------------------------------------------------------
# Sui dati veri, se ci sono
# --------------------------------------------------------------------------

@pytest.mark.skipif(not T.TargetVoti().percorso(1).is_file(),
                    reason="grezzo dei voti non ancora acquisito")
def test_una_pagina_vera_rispetta_il_contratto():
    t = T.TargetVoti()
    letta = P.analizza(P.leggi(t.percorso(1)), t.season, 1)
    assert len(letta["partite"]) == 10
    assert sum(1 for r in letta["righe"] if r["allenatore"]) == 20
    assert sum(1 for r in letta["righe"] if not r["allenatore"]) > 250
