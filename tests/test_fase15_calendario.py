# -*- coding: utf-8 -*-
"""Fase 15 / C1 - il calendario delle partite ancora da giocare.

**Nessun test di questo file tocca la rete.** Cio' che la rete ha stabilito -
che `dayChangeBtn-next` esiste e che `/live/` separa le giocate dalle future -
sta in `reports/fase15_calendario_verifica.json`, prodotto una volta da
`verifica_calendario.py`; qui si verifica che il CODICE usi quel fatto e non un
altro, e che le guardie sappiano dire di no.

Il gruppo che conta di piu' e' il secondo: **il calendario futuro non deve
finire in `matches.json`**. Quel file e' il criterio di arresto dello scraper e
il denominatore di `avanzamento`, e mescolarci le partite da giocare romperebbe
entrambi senza sollevare niente.
"""
from __future__ import annotations

import json
import sys
import tokenize
import io
from pathlib import Path

import pytest

from sot import config

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "acquisition" / "whoscored"))

import scrape_season as S  # noqa: E402
import target as T  # noqa: E402
import verifica_calendario as VC  # noqa: E402

VERIFICA = config.REPORTS / "fase15_calendario_verifica.json"


def _codice(path) -> str:
    """Il sorgente senza commenti e senza stringhe (la guardia di V0)."""
    src = path.read_text(encoding="utf-8")
    return " ".join(t.string for t in
                    tokenize.generate_tokens(io.StringIO(src).readline)
                    if t.type not in (tokenize.COMMENT, tokenize.STRING))


# --------------------------------------------------------------------------
# 1. Il discriminante fra giocata e da giocare
# --------------------------------------------------------------------------
def test_il_discriminante_e_una_definizione_sola():
    """`/live/` sta in un posto solo e lo usano parser e verifica."""
    assert S.SEGMENTO_GIOCATA == "/live/"
    assert S._e_giocata("/matches/1/live/x") is True
    assert S._e_giocata("/matches/1/show/x") is False
    assert S._e_giocata("") is False
    assert S._e_giocata(None) is False


def test_il_criterio_di_controllo_si_astiene_invece_di_negare():
    """`None` non e' `False`: una riga illeggibile non e' una riga futura.

    Contarla come negativa gonfierebbe l'accordo fra i due criteri senza motivo,
    ed e' la ragione per cui la funzione ha tre esiti e non due.
    """
    assert VC.giocata_da_punteggio("1:0") is True
    assert VC.giocata_da_punteggio("20:45") is False      # un orario
    assert VC.giocata_da_punteggio("-:-") is None         # la forma osservata
    assert VC.giocata_da_punteggio("") is None


def test_i_due_criteri_sono_indipendenti():
    """Uno guarda l'href, l'altro il testo: non devono condividere sorgente."""
    src = _codice(ROOT / "acquisition" / "whoscored" / "verifica_calendario.py")
    assert "giocata_da_href" in src and "giocata_da_punteggio" in src
    # il criterio di controllo non deve poter leggere l'href
    import inspect
    assert "href" not in inspect.getsource(VC.giocata_da_punteggio)


# --------------------------------------------------------------------------
# 2. Il calendario futuro NON finisce in matches.json
# --------------------------------------------------------------------------
def test_i_due_file_sono_separati():
    t = T.Target(league=config.LEAGUE, season=config.SEASON_CORRENTE)
    assert t.cache_url.name == "matches.json"
    assert t.cache_calendario.name == "calendario.json"
    assert t.cache_url.parent == t.cache_calendario.parent
    assert t.cache_calendario == config.calendario_json(
        config.LEAGUE, config.SEASON_CORRENTE)


def test_la_raccolta_del_calendario_non_scrive_mai_in_matches_json():
    """La guardia e' sul CODICE della funzione, non sulla prosa del modulo."""
    import inspect
    corpo = inspect.getsource(S.raccogli_calendario)
    assert "cache_calendario" in corpo
    assert "cache_url" not in corpo


def test_avanzamento_conta_le_giocate_e_non_il_calendario():
    """Se le future entrassero in matches.json, la quota andrebbe a 1,00 subito."""
    # quattro squadre, due partite giocate: 12 attese, 2 viste.
    # Con DUE squadre il denominatore dedotto sarebbe 2 e la quota 100%: e' il
    # limite gia' dichiarato da `avanzamento`, non un difetto, e il test usa un
    # campionato abbastanza grande da non caderci dentro.
    giocate = [{"home": "A", "away": "B"}, {"home": "C", "away": "D"}]
    a = T.avanzamento(giocate)
    assert a["squadre"] == 4
    assert a["partite_viste"] == 2
    assert a["partite_attese"] == 12
    assert a["quota"] < 1.0

    # se le partite FUTURE finissero nello stesso elenco, la quota mentirebbe
    con_future = giocate + [{"home": "B", "away": "A"}, {"home": "D", "away": "C"}]
    assert T.avanzamento(con_future)["partite_viste"] == 4


# --------------------------------------------------------------------------
# 3. La verifica di struttura sa dire di no, e sa dire di si'
# --------------------------------------------------------------------------
def _riga(home, away, data="sabato, set 05 2026", url=None, score=None):
    return {"date": data, "home": home, "away": away,
            "url": url or f"/matches/x/{home}-{away}", "score": score}


def test_la_struttura_rifiuta_una_squadra_contro_se_stessa():
    p = S.verifica_calendario_futuro([_riga("Como", "Como")])
    assert "squadra_contro_se_stessa" in p


def test_la_struttura_rifiuta_una_squadra_due_volte_nello_stesso_giorno():
    p = S.verifica_calendario_futuro([_riga("Como", "Inter"),
                                      _riga("Como", "Roma")])
    assert "squadra_due_volte_nello_stesso_giorno" in p


def test_la_struttura_rifiuta_un_accoppiamento_ripetuto():
    p = S.verifica_calendario_futuro([
        _riga("Como", "Inter", "sabato, set 05 2026", "/a"),
        _riga("Como", "Inter", "sabato, set 12 2026", "/b")])
    assert "accoppiamento_ripetuto" in p


def test_la_struttura_rifiuta_una_partita_futura_con_punteggio():
    """`score` su una riga futura significa che un orario ci e' finito dentro."""
    p = S.verifica_calendario_futuro([_riga("Como", "Inter", score="20:45")])
    assert "partita_futura_con_punteggio" in p


def test_la_struttura_sa_dire_anche_di_si():
    """Senza, 'nessuna violazione' e 'la guardia non guarda' coinciderebbero."""
    sano = [_riga("Como", "Inter", "sabato, set 05 2026", "/a"),
            _riga("Roma", "Lazio", "sabato, set 05 2026", "/b"),
            _riga("Inter", "Como", "sabato, gen 10 2027", "/c")]
    assert S.verifica_calendario_futuro(sano) == {}


def test_la_struttura_non_assume_38_giornate():
    """I denominatori si contano, mai si assumono (§7.2): Bundesliga ne ha 34.

    Un calendario di due sole partite deve passare: e' parziale, non storto.
    """
    assert S.verifica_calendario_futuro(
        [_riga("Bayern", "Dortmund"), _riga("Leipzig", "Union", url="/z")]) == {}


# --------------------------------------------------------------------------
# 4. Il comportamento storico non cambia di un bit
# --------------------------------------------------------------------------
def test_il_parser_per_default_scarta_ancora_le_future():
    """`includi_future=False` e' l'acquisizione degli eventi, e non si tocca."""
    import inspect
    sig = inspect.signature(S._parse_visible_fixtures)
    assert sig.parameters["includi_future"].default is False
    corpo = inspect.getsource(S._parse_visible_fixtures)
    assert "if not giocata and not includi_future:" in corpo
    assert "continue" in corpo


def test_la_navigazione_ha_una_sola_implementazione():
    """Il ripiego JS sul banner e' gia' costato due stagioni: una copia sola."""
    import inspect
    assert S.BTN_PREV == "dayChangeBtn-prev"
    assert S.BTN_NEXT == "dayChangeBtn-next"
    for f in (S._click_prev_day, S._click_next_day):
        corpo = inspect.getsource(f)
        assert "_click_day(" in corpo
        assert "execute_script" not in corpo, "il ripiego e' stato duplicato"
    assert "execute_script" in inspect.getsource(S._click_day)


def test_load_match_urls_conserva_le_guardie_della_fase_14():
    """Quattro sottostringhe che `test_fase14.py` fissa alla lettera."""
    src = (ROOT / "acquisition" / "whoscored" / "scrape_season.py").read_text(
        encoding="utf-8")
    corpo = src[src.index("def load_match_urls"):src.index("class Progress")]
    for atteso in ("passate = 1 if in_corso else MAX_URL_PASSES",
                   "merged = {m['url']: m for m in cached}",
                   "if not in_corso and not refresh and report_completeness(cached)",
                   "avanzamento(urls)"):
        assert atteso in corpo, atteso


def test_l_aggiornamento_settimanale_chiede_il_calendario():
    """E continua a chiedere `--in-corso`: le due cose non si escludono."""
    src = (ROOT / "scripts" / "aggiorna_stagione.py").read_text(encoding="utf-8")
    corpo = src[src.index("def scarica("):src.index("def derivati(")]
    assert '"--calendario"' in corpo
    assert '"--in-corso"' in corpo


# --------------------------------------------------------------------------
# 5. Cio' che la rete ha accertato, e che il codice deve usare
# --------------------------------------------------------------------------
def test_la_verifica_di_rete_e_leggibile():
    """I quattro controlli devono essere passati tutti, o non si dichiara niente.

    Non e' un test della rete: e' un test del **verbale**. Se qualcuno rifacesse
    la verifica e uno dei controlli cadesse, questo test lo direbbe invece di
    lasciare che il calendario venga raccolto lo stesso.
    """
    if not VERIFICA.is_file():
        pytest.skip("manca il verbale: esegui verifica_calendario.py")
    v = json.loads(VERIFICA.read_text(encoding="utf-8"))["verdetto"]
    assert v["bottone_next_esiste"] is True
    assert v["bottone_next_muove"] is True
    assert v["controllo_positivo"] is True
    assert v["controllo_negativo"] is True
    assert v["criteri_discordi"] == 0
    assert v["verifica_leggibile"] is True


def test_il_verbale_e_coerente_col_criterio_del_codice():
    """Il codice non deve poter usare un criterio diverso da quello accertato."""
    if not VERIFICA.is_file():
        pytest.skip("manca il verbale: esegui verifica_calendario.py")
    v = json.loads(VERIFICA.read_text(encoding="utf-8"))["verdetto"]
    assert S.SEGMENTO_GIOCATA.strip("/") in v["criterio_primario"]


def test_il_verbale_registra_i_due_controlli_in_versi_opposti():
    """Un controllo solo non renderebbe leggibile nessun esito."""
    if not VERIFICA.is_file():
        pytest.skip("manca il verbale: esegui verifica_calendario.py")
    prove = json.loads(VERIFICA.read_text(encoding="utf-8"))["prove"]
    pos = next(p for p in prove if p["nome"] == "positivo")
    neg = next(p for p in prove if p["nome"] == "negativo")
    # il positivo: tutte giocate e tutte gia' su disco
    assert pos["righe_lette"] > 0
    assert pos["giocate_secondo_href"] == pos["righe_lette"]
    assert pos["in_matches_json"] == pos["righe_lette"]
    # il negativo: nessuna giocata e nessuna su disco
    assert neg["righe_lette"] > 0
    assert neg["giocate_secondo_href"] == 0
    assert neg["in_matches_json"] == 0


# --------------------------------------------------------------------------
# 6. Il difetto del riepilogo settimanale, trovato eseguendo
# --------------------------------------------------------------------------
def test_il_riepilogo_del_manifest_non_chiama_len_su_un_contatore():
    """`nuovi` e' un INT, `modificati` una LISTA: `len()` sul primo solleva.

    Il difetto ha fatto riportare per cinque campionati, a ogni esecuzione
    settimanale, un errore inesistente attribuito ai **derivati**, che erano
    riusciti. Il test guarda i tipi alla fonte invece della riga di stampa,
    cosi' vale anche se la stampa cambia forma.
    """
    from acquisition import manifest

    r = manifest.registra_whoscored(config.LEAGUE, [config.SEASON_CORRENTE],
                                    verbose=False)
    assert isinstance(r["nuovi"], int)
    assert isinstance(r["modificati"], list)
    with pytest.raises(TypeError):
        len(r["nuovi"])          # e' esattamente cio' che il codice faceva


def test_derivati_e_manifest_hanno_due_try_separati():
    """Un guasto del riepilogo non deve poter accusare i derivati.

    Con un `try` solo, un errore vero dei derivati e uno cosmetico della riga di
    stampa erano indistinguibili: entrambi uscivano come 'derivati: ...'.
    """
    src = (ROOT / "scripts" / "aggiorna_stagione.py").read_text(encoding="utf-8")
    corpo = src[src.index("righe = derivati(league"):src.index("esiti.append(")]
    assert 'f"derivati: {exc}"' in corpo
    assert 'f"manifest: {exc}"' in corpo
    assert corpo.count("except Exception as exc:") == 2


# --------------------------------------------------------------------------
# 7. La seconda fonte: Wikipedia, che porta la GIORNATA
# --------------------------------------------------------------------------
from acquisition.wikipedia import pagina as WP  # noqa: E402
from acquisition.wikipedia import target as WT  # noqa: E402

from sot import calendario as CAL  # noqa: E402


def test_le_due_fonti_hanno_due_criteri_diversi():
    """Il criterio di una fonte non si eredita dall'altra (vincolo 7).

    Su WhoScored una partita da giocare ha `/show/` nell'href; su Wikipedia
    mostra l'orario nella cella del risultato. Sono due proprieta' di due fonti,
    e scambiarle darebbe una tabella dell'ordine di grandezza giusto e del
    contenuto sbagliato.
    """
    assert "live" in S.SEGMENTO_GIOCATA
    assert "live" not in WP.CRITERIO_GIOCATA
    assert "20:45" in WP.CRITERIO_GIOCATA


def test_la_cella_si_divide_contro_nomi_noti_e_non_sul_primo_trattino():
    """In Ligue 1 esiste Saint-Etienne: spezzare sul primo `-` sbaglia."""
    note = {"Saint-Etienne", "Le Havre", "Lens"}
    assert WP.dividi("Saint-Etienne-Le Havre", note) == ("Saint-Etienne", "Le Havre")
    assert WP.dividi("Lens-Saint-Etienne", note) == ("Lens", "Saint-Etienne")


def test_la_divisione_solleva_invece_di_scegliere():
    """Zero soluzioni o due: si dichiara, non si sceglie la piu' comoda."""
    with pytest.raises(ValueError, match="non si divide"):
        WP.dividi("Pippo-Pluto", {"Inter", "Milan"})


def test_i_marcatori_senza_risultato_sono_dichiarati():
    """Tre esiti e non due: illeggibile non e' 'da giocare'."""
    assert WP.e_giocata("2-1") is True
    assert WP.e_giocata("20:45") is False
    assert WP.e_giocata("-") is False
    assert WP.e_giocata("") is False
    assert WP.e_giocata("rinviata?") is None


def test_la_completezza_non_e_una_violazione():
    """Una stagione in corso e' incompleta per definizione, non storta.

    E' la distinzione che `scrape_quote.py` fa fra 'listone non ancora
    pubblicato' e 'markup cambiato'.
    """
    meta = [{"giornata": 1, "casa": "A", "trasferta": "B", "giocata": True,
             "esito_grezzo": "1-0"}]
    assert WP.verifica(meta, 4) == {}                 # nessuna violazione
    c = WP.completezza(meta, 4)
    assert c["completo"] is False
    assert c["partite_attese"] == 12                  # 4 squadre, 6 giornate


def test_i_denominatori_si_contano_dal_numero_di_squadre():
    """18 squadre = 34 giornate, non 38 (§7.2)."""
    assert WP.completezza([], 18)["giornate_attese"] == 34
    assert WP.completezza([], 20)["giornate_attese"] == 38
    assert WP.completezza([], 18)["partite_attese"] == 306


def test_il_titolo_wikipedia_solleva_su_un_campionato_non_coperto():
    with pytest.raises(ValueError, match="senza titolo Wikipedia"):
        WT.titolo("POR-primeira-liga", config.SEASON_CORRENTE)


def test_il_parser_wikipedia_non_importa_la_rete():
    """Il parser e i bersagli restano verificabili senza rete."""
    for modulo in ("pagina.py", "target.py"):
        src = _codice(ROOT / "acquisition" / "wikipedia" / modulo)
        for vietato in ("requests", "urlopen", "httpx"):
            assert vietato not in src, f"{modulo} importa {vietato}"


# --------------------------------------------------------------------------
# 8. La riconciliazione: il nome NON e' una chiave
# --------------------------------------------------------------------------
def test_la_mappa_delle_squadre_e_verificata_biiettiva():
    """`Milan` -> `AC Milan` per contenimento, ma solo se e' UNICO."""
    ws = {"AC Milan", "Parma Calcio 1913", "Inter"}
    wk = {"Milan", "Parma", "Inter"}
    m = CAL.mappa_squadre(ws, wk)
    assert m == {"Milan": "AC Milan", "Parma": "Parma Calcio 1913",
                 "Inter": "Inter"}


def test_la_mappa_solleva_su_un_contenimento_ambiguo():
    """Un nome contenuto in due nomi diversi non si sceglie: si dichiara.

    `Real` sta dentro sia `Real Madrid` sia `Real Sociedad`, e nessuno dei due
    e' un aggancio esatto: due candidati, quindi si solleva.
    """
    with pytest.raises(ValueError, match="non si aggancia a una sola"):
        CAL.mappa_squadre({"Real Madrid", "Real Sociedad"},
                          {"Real", "Real Betis"})


def test_l_aggancio_esatto_viene_prima_e_disambigua():
    """`Manchester City` esatto toglie di mezzo l'ambiguita' di `Manchester`.

    E' il motivo per cui i due passi sono in quest'ordine e non nell'altro: con
    il contenimento per primo, `Manchester` avrebbe due candidati e la mappa
    fallirebbe su un caso che invece si risolve da se'.
    """
    m = CAL.mappa_squadre({"Manchester United", "Manchester City"},
                          {"Manchester", "Manchester City"})
    assert m == {"Manchester City": "Manchester City",
                 "Manchester": "Manchester United"}


def test_la_mappa_solleva_se_le_squadre_non_sono_lo_stesso_numero():
    """Una mappa parziale farebbe sparire in silenzio una squadra intera."""
    with pytest.raises(ValueError, match="numero diverso di squadre"):
        CAL.mappa_squadre({"Inter", "Milan", "Roma"}, {"Inter", "Milan"})


def test_il_calendario_riconciliato_non_inventa_la_giornata():
    """Senza Wikipedia il calendario esce lo stesso, con `fonte_giornata` assente.

    Una giornata mancante e' un limite; una giornata inventata e' un difetto.
    """
    cal = CAL.calendario(config.LEAGUE)
    if cal.empty:
        pytest.skip("manca il calendario: esegui scrape_season --solo-calendario")
    assert set(cal["fonte_giornata"]) <= {"wikipedia", "assente"}
    senza = cal[cal["fonte_giornata"] == "assente"]
    assert senza["giornata"].isna().all()


def test_le_due_fonti_concordano_sulle_partite_da_giocare():
    """Il controllo incrociato vero: nessuna partita solo in WhoScored.

    Le partite presenti solo in Wikipedia sono quelle **gia' giocate**, che il
    calendario futuro esclude per costruzione: la differenza e' attesa e ha un
    numero, non e' un residuo da spiegare.
    """
    d = CAL.divergenze(config.LEAGUE)
    if not d.get("confrontabili"):
        pytest.skip("le due fonti non sono entrambe presenti")
    assert d["n_solo_whoscored"] == 0, d["solo_whoscored"]
    assert d["comuni"] == d["partite_whoscored"]


# --------------------------------------------------------------------------
# 9. Il difetto piu' vecchio: 'live' sta dentro 'liverpool'
# --------------------------------------------------------------------------
def test_il_criterio_non_fa_match_dentro_liverpool():
    """Il difetto che `coerenza_fonti` ha trovato, fissato perche' non torni.

    Il criterio storico cercava la sottostringa `'live'` nell'href. Su
    `.../show/...-ipswich-liverpool` fa match dentro **liverpool**, quindi ogni
    partita del Liverpool passava come GIOCATA anche se non lo era: e' cosi' che
    `Ipswich-Liverpool` e' finita in `matches.json` con punteggio `-:-`.
    """
    url = ("/matches/1983580/show/inghilterra-premier-league-2026-2027-"
           "ipswich-liverpool")
    assert "live" in url                      # il criterio vecchio ci cadeva
    assert S._e_giocata(url) is False         # quello accertato no
    vera = url.replace("/show/", "/live/")
    assert S._e_giocata(vera) is True         # e sa ancora dire di si'


def test_anche_la_copia_legacy_usa_le_barre():
    """`main.py` aveva la stessa sottostringa nuda: una classe, non un punto."""
    src = (ROOT / "acquisition" / "whoscored" / "main.py").read_text(
        encoding="utf-8")
    assert "if '/live/' in url.get_attribute('href'):" in src
    assert "if 'live' in url.get_attribute('href'):" not in src


def test_una_partita_non_e_insieme_giocata_e_da_giocare():
    """`matches.json` e `calendario.json` non devono avere URL in comune."""
    d = CAL.coerenza_fonti(config.LEAGUE)
    if not d["da_giocare"]:
        pytest.skip("manca il calendario: esegui scrape_season --solo-calendario")
    assert d["in_entrambi"] == [], d["in_entrambi"]
    assert d["in_matches_json_senza_live"] == []
    assert d["coerente"] is True


def test_la_guardia_di_coerenza_sa_dire_anche_di_no():
    """Senza, 'coerente' e 'la guardia non guarda' coinciderebbero.

    La Premier 2026-2027 ha ancora la riga sbagliata scritta dalla passata
    precedente: la cache si rinfresca **sommando**, non sostituendo, quindi una
    riga entrata con il criterio vecchio non esce da sola.
    """
    d = CAL.coerenza_fonti("ENG-premier-league")
    if not d["da_giocare"]:
        pytest.skip("manca il calendario della Premier")
    assert d["coerente"] is False
    assert any("liverpool" in u for u in d["in_matches_json_senza_live"])


# --------------------------------------------------------------------------
# 10. Gli esonimi: dichiarati, corti, e verificati
# --------------------------------------------------------------------------
def test_gli_accenti_non_vanno_dichiarati_come_esonimi():
    """`Alaves` e `Alaves` con l'accento sono la stessa squadra: e' una regola."""
    assert CAL._normalizza("Alav\u00e9s") == "alaves"
    assert CAL._normalizza("Atl\u00e9tico  Madrid") == "atletico madrid"
    m = CAL.mappa_squadre({"Deportivo Alaves"}, {"Alav\u00e9s"})
    assert m == {"Alav\u00e9s": "Deportivo Alaves"}


def test_nessun_esonimo_dichiarato_si_risolverebbe_da_solo():
    """Il principio e': non dichiarare cio' che la regola generale gia' fa.

    **Non c'e' un tetto al numero di esonimi**, e il tetto che questo test
    aveva all'inizio era una mia invenzione: su Bundesliga ne servono undici,
    perche' Wikipedia italiana traduce quasi ogni citta' tedesca. Sono una
    proprieta' dell'accoppiata di fonti, non il sintomo di una regola mancante —
    e il sintomo vero sarebbe un esonimo che accento e contenimento risolvono da
    soli, che e' quello che il test controlla.
    """
    for league, esonimi in CAL.NOMI_FONTE.items():
        for wk, ws in esonimi.items():
            a, b = CAL._normalizza(wk), CAL._normalizza(ws)
            assert not (a in b or b in a), (
                f"{wk!r} -> {ws!r} si risolve da solo col contenimento: "
                "non va dichiarato")


def test_le_squadre_vengono_dall_elenco_dei_partecipanti():
    """Su una pagina parziale le squadre VISTE sono meno di quelle iscritte.

    E' la differenza che ha fatto fallire Premier e Liga alla prima prova, e il
    test la fissa perche' non torni: l'elenco dei partecipanti c'e' anche quando
    il calendario e' scritto a meta'.
    """
    note = CAL.squadre_wikipedia(config.LEAGUE)
    if not note:
        pytest.skip("manca il calendario Wikipedia")
    wk = CAL.carica_wikipedia(config.LEAGUE)
    viste = set(wk["casa"]) | set(wk["trasferta"])
    assert set(note) >= viste, "una squadra gioca senza essere iscritta"


def test_ogni_campionato_con_due_fonti_si_riconcilia():
    """Dove entrambe le fonti ci sono, la mappa deve essere biiettiva su tutte."""
    provati = 0
    for league in sorted(config.LEAGUE_CODES):
        ws = CAL.carica_whoscored(league)
        note = CAL.squadre_wikipedia(league)
        if ws.empty or not note:
            continue
        provati += 1
        m = CAL.mappa_squadre(set(ws["casa"]) | set(ws["trasferta"]),
                              set(note), league=league)
        assert len(m) == len(note)
        assert len(set(m.values())) == len(note)
    if not provati:
        pytest.skip("nessun campionato ha entrambe le fonti")


def test_il_giro_settimanale_rinfresca_anche_wikipedia():
    """Senza, la giornata invecchia: il girone di ritorno si scrive col tempo.

    E **non deve fermare il giro**: la giornata e' un di piu', e senza di essa
    la pagina dichiara `fonte_giornata = assente` e continua a funzionare.
    """
    src = (ROOT / "scripts" / "aggiorna_stagione.py").read_text(encoding="utf-8")
    corpo = src[src.index("Aggiorno il calendario da Wikipedia"):
                src.index("Rigenero le previsioni")]
    assert "scrape_calendario" in corpo
    assert "except Exception" in corpo
