# -*- coding: utf-8 -*-
"""Fase 14 — l'aggiornamento della stagione in corso e la previsione sui cinque
campionati.

Il blocco A0 non aggiunge nessun numero: rende parametrica su `league` una
catena che era **cablata sulla Serie A senza dirlo**. La forma dei test segue da
li': quasi tutti verificano che qualcosa **non** sia cambiato.
"""
from __future__ import annotations

import ast
import inspect
import re
from pathlib import Path

import pytest

from sot import config, multistagione as MS, previsione as P, tentativi as T, volume as VL


# --------------------------------------------------------------------------
# 1. La stagione in corso e' separata dalle storiche
# --------------------------------------------------------------------------
def test_la_stagione_in_corso_non_e_fra_le_storiche():
    """**E' l'invariante che tiene in piedi la Fase 14.**

    `SEASONS_STORICHE` e' il default di mezzo repository: `previsione` ne prende
    l'ultimo elemento, `tentativi.universo` la usa quando `stagioni is None`,
    `volume.walkforward_tiri` pure. Aggiungerci la stagione in corso sposterebbe
    in silenzio ogni numero validato dalle Fasi 0-13, e nessun test se ne
    accorgerebbe: leggono tutti la costante, non il suo valore.
    """
    assert config.SEASON_CORRENTE not in config.SEASONS_STORICHE
    assert len(config.SEASONS_STORICHE) == 5
    assert config.SEASONS_STORICHE[-1] == "2025-2026"


def test_la_stagione_in_corso_e_ben_formata_e_successiva():
    config._check_season(config.SEASON_CORRENTE)
    assert config.SEASON_CORRENTE > max(config.SEASONS_STORICHE)


# --------------------------------------------------------------------------
# 2. `league=None` e' identico a prima, bit per bit
# --------------------------------------------------------------------------
def test_universo_col_campionato_esplicito_e_identico_al_default():
    """Se divergessero, il default avrebbe smesso di essere `config.LEAGUE` e
    ogni numero delle Fasi 12-13 sarebbe stato ricalcolato su altri dati."""
    a = T.universo()
    b = T.universo(league=config.LEAGUE)
    assert a.equals(b)
    assert len(a) == 3778


def test_carica_col_campionato_esplicito_e_identico_al_default():
    a = MS.carica("team_match")
    b = MS.carica("team_match", league=config.LEAGUE)
    assert a.equals(b)


@pytest.mark.parametrize("fn", [MS.carica, T.universo, VL.walkforward_tiri,
                                P.storia, P.previsione, P.tabella_avversari,
                                P.tabella_completa, P.modello_alla_data])
def test_league_e_sempre_un_parametro_con_default_none(fn):
    """`None` e non `config.LEAGUE` come default letterale: un default valutato
    all'import congelerebbe il campionato al momento del caricamento del modulo,
    che e' esattamente il difetto delle vecchie costanti `CACHE`."""
    p = inspect.signature(fn).parameters
    assert "league" in p, f"{fn.__name__} non prende `league`"
    assert p["league"].default is None


# --------------------------------------------------------------------------
# 3. Le cache: una per campionato, e la Serie A resta dov'era
# --------------------------------------------------------------------------
def test_la_cache_della_serie_a_non_si_e_spostata():
    """Se il percorso cambiasse, la cache gia' su disco verrebbe ignorata e V1
    si ricalcolerebbe — cioe' i numeri pubblicati passerebbero da un file letto
    a un file riscritto, senza che nessuno lo chieda."""
    assert VL.CACHE == VL.cache()
    assert VL.CACHE == (config.processed_league_dir()
                        / "fase12_walkforward_tiri.parquet")


def test_ogni_campionato_ha_la_sua_cache():
    """I campionati non si poolano (regola di E1, riscritta da R0 su G2): due
    campionati che condividessero il file condividerebbero `alpha` e `r`."""
    percorsi = {L: VL.cache(L) for L in config.LEAGUE_CODES}
    assert len(set(percorsi.values())) == len(percorsi)
    for L, p in percorsi.items():
        assert p.parent.name == L


def test_la_cache_non_si_usa_per_un_insieme_di_stagioni_diverso():
    """La correzione della Fase 14: prima la cache si leggeva **qualunque** cosa
    fosse passata in `stagioni`, quindi chiedere una stagione sola restituiva in
    silenzio il walk-forward di tutte e cinque.

    Si verifica sul sorgente e non eseguendo, perche' eseguire il ramo non
    cacheabile costa un walk-forward intero.
    """
    src = (config.ROOT / "sot" / "volume.py").read_text(encoding="utf-8")
    corpo = src[src.index("def walkforward_tiri"):src.index("def _valutabili")]
    assert "cacheabile = stagioni == default" in corpo
    assert "if cacheabile and percorso.is_file()" in corpo
    assert "if cacheabile:" in corpo


# --------------------------------------------------------------------------
# 4. Nessun percorso scritto a mano (vincolo gia' della Fase 7A)
# --------------------------------------------------------------------------
def test_nessun_modulo_della_fase_14_scrive_un_campionato_a_mano():
    """Il campionato ha un nome in un posto solo, `config.LEAGUE_CODES`. Un
    letterale `"ITA-serie-a"` dentro un modulo di modellazione e' il ritorno del
    percorso scritto a mano che `tests/test_layout.py` blocca sulle stagioni."""
    for nome in ("previsione.py", "volume.py", "tentativi.py", "multistagione.py"):
        albero = ast.parse((config.ROOT / "sot" / nome).read_text(encoding="utf-8"))
        letterali = [n.value for n in ast.walk(albero)
                     if isinstance(n, ast.Constant) and isinstance(n.value, str)
                     and n.value in config.LEAGUE_CODES]
        assert letterali == [], f"{nome} nomina un campionato a mano: {letterali}"


# --------------------------------------------------------------------------
# 5. A1 — la stagione in corso, lato acquisizione
# --------------------------------------------------------------------------
import sys as _sys                                                  # noqa: E402

for _p in (config.ROOT / "acquisition" / "whoscored", config.ROOT / "scripts"):
    if str(_p) not in _sys.path:
        _sys.path.insert(0, str(_p))

import aggiorna_stagione as AGG                                     # noqa: E402
import target as TG                                                 # noqa: E402


def _finto_calendario(n_squadre: int, giornate: int):
    """Un calendario sintetico: `giornate` turni completi fra `n_squadre`."""
    squadre = [f"S{i}" for i in range(n_squadre)]
    partite = []
    for g in range(giornate):
        for i in range(0, n_squadre, 2):
            casa = squadre[(i + g) % n_squadre]
            fuori = squadre[(i + 1 + g) % n_squadre]
            partite.append({"home": casa, "away": fuori})
    return partite


def test_avanzamento_deduce_il_denominatore_dalle_squadre():
    """Mai 38 scritto dentro: la Bundesliga e la Ligue 1 ne hanno 34.

    E' la stessa ragione per cui `report_completeness` non ha un numero fisso, e
    per cui E0 conta le partite invece di assumerle.
    """
    a20 = TG.avanzamento(_finto_calendario(20, 3))
    assert a20["squadre"] == 20
    assert a20["per_squadra_attese"] == 38
    assert a20["partite_attese"] == 380
    assert a20["partite_viste"] == 30

    a18 = TG.avanzamento(_finto_calendario(18, 3))
    assert a18["per_squadra_attese"] == 34
    assert a18["partite_attese"] == 306


def test_avanzamento_non_e_report_completeness_con_un_flag():
    """Le due funzioni rispondono a due domande diverse e non vanno fuse.

    `report_completeness` ritorna un **booleano** che lo scraper usa come
    criterio di arresto; `avanzamento` ritorna una **misura**. Se `avanzamento`
    ritornasse un bool, chi legge il log non potrebbe distinguere «completo» da
    «per ora e' arrivato fin qui».
    """
    assert isinstance(TG.avanzamento(_finto_calendario(20, 1)), dict)
    assert isinstance(TG.report_completeness(_finto_calendario(20, 19)), bool)


def test_avanzamento_su_una_stagione_finita_dice_il_cento_per_cento():
    """Controllo positivo: se la macchina non sapesse dire anche «finita»,
    «25%» non significherebbe niente."""
    a = TG.avanzamento(_finto_calendario(20, 38))
    assert a["quota"] == pytest.approx(1.0)
    assert a["per_squadra_min"] == a["per_squadra_max"] == 38


def test_il_flag_in_corso_esiste_ed_e_spento_per_default():
    """Spento per default: le cinque stagioni storiche sono finite, e il
    comportamento di prima deve restare quello di prima."""
    assert TG.parser().parse_args([]).in_corso is False
    assert TG.parser().parse_args(["--in-corso"]).in_corso is True


def test_in_corso_fa_una_passata_sola_e_non_perde_la_cache():
    """Le due proprieta' che rendono il flag sicuro, verificate sul sorgente.

    Eseguirle vorrebbe un browser; il punto pero' e' strutturale e si legge:
    (a) il numero di passate diventa 1, (b) `merged` parte comunque dalla cache,
    quindi una navigazione che non risalisse fino a settembre non cancella
    settembre.
    """
    src = (config.ROOT / "acquisition" / "whoscored"
           / "scrape_season.py").read_text(encoding="utf-8")
    corpo = src[src.index("def load_match_urls"):src.index("class Progress")]
    assert "passate = 1 if in_corso else MAX_URL_PASSES" in corpo
    assert "merged = {m['url']: m for m in cached}" in corpo
    assert "if not in_corso and not refresh and report_completeness(cached)" in corpo
    assert "avanzamento(urls)" in corpo


# --------------------------------------------------------------------------
# 6. A1 — lo script di aggiornamento
# --------------------------------------------------------------------------
def test_la_soglia_dei_derivati_e_imposta_dalla_procedura():
    """Non e' un numero scelto: sotto `xg.N_FOLDS` partite il `GroupKFold`
    dell'xG non ha abbastanza gruppi, quindi i derivati non sono costruibili."""
    from sot import xg as xg_mod
    assert AGG.MIN_PARTITE_DERIVATI == xg_mod.N_FOLDS


def test_lo_scraper_riceve_sempre_in_corso():
    """Se il flag si perdesse, ogni aggiornamento settimanale tornerebbe a
    pagare quattro navigazioni complete del calendario."""
    src = (config.ROOT / "scripts"
           / "aggiorna_stagione.py").read_text(encoding="utf-8")
    corpo = src[src.index("def scarica("):src.index("def derivati(")]
    assert '"--in-corso"' in corpo


def test_lo_script_copre_tutti_e_cinque_i_campionati():
    assert set(AGG.CAMPIONATI) == set(config.LEAGUE_CODES)
    assert len(AGG.CAMPIONATI) == 5


def test_stato_riconosce_i_derivati_gia_aggiornati():
    """Controllo positivo su una stagione finita: i Parquet della 2025-2026 sono
    piu' recenti dei suoi CSV, quindi NON vanno rifatti. Senza questo, la regola
    sui mtime potrebbe dire sempre «rifai» e nessuno se ne accorgerebbe."""
    s = AGG.stato(config.LEAGUE, "2025-2026")
    assert s["csv"] == 380
    assert s["abbastanza"] is True
    assert s["derivati_da_rifare"] is False


def test_stato_su_una_stagione_non_ancora_completa_e_coerente_col_disco():
    """Deve rispondere, non esplodere: e' cio' che fa partire il primo martedi'.

    **Questo test era una fotografia e ora e' una proprieta'.** Fino al
    2026-09-03 asseriva `csv == 0` e `in_calendario is None`, che era vero solo
    finche' la 2026-2027 non era mai stata scaricata; il primo giro
    dell'attivita' pianificata l'ha resa falsa. Una guardia che descrive uno
    stato transitorio invece di una proprieta' diventa rossa da sola — ed e'
    la stessa classe di difetto che questo repository ha gia' pagato cinque
    volte sulle guardie di forma.
    """
    s = AGG.stato(config.LEAGUE, config.SEASON_CORRENTE)
    csv_veri = len(list(config.match_dir(config.LEAGUE,
                                         config.SEASON_CORRENTE).glob("*.csv")))
    assert s["csv"] == csv_veri
    assert s["abbastanza"] is (csv_veri >= AGG.MIN_PARTITE_DERIVATI)
    cal = config.matches_json(config.LEAGUE, config.SEASON_CORRENTE)
    if cal.is_file():
        assert isinstance(s["in_calendario"], int)
        assert s["in_calendario"] >= s["csv"]
    else:
        assert s["in_calendario"] is None
        # senza CSV non c'e' niente da rigenerare: dirlo evita un giro a vuoto
        assert s["derivati_da_rifare"] is False


def test_lo_script_di_aggiornamento_non_importa_selenium():
    """L'orchestrazione non tocca la rete: lo scraper gira in un sottoprocesso,
    ed e' cio' che rende `--dry-run` verificabile senza browser."""
    src = (config.ROOT / "scripts"
           / "aggiorna_stagione.py").read_text(encoding="utf-8")
    for vietato in ("import selenium", "from selenium", "import requests"):
        assert vietato not in src


def test_l_attivita_pianificata_ricomincia_se_il_pc_era_spento():
    """`StartWhenAvailable` e' la ragione per cui l'attivita' e' un XML e non una
    riga di `schtasks /SC WEEKLY`: senza, un martedi' a PC spento e' perso."""
    import xml.etree.ElementTree as ET
    x = config.ROOT / "scripts" / "attivita_martedi.xml"
    assert x.is_file()
    ns = {"t": "http://schemas.microsoft.com/windows/2004/02/mit/task"}
    r = ET.parse(x).getroot()
    assert r.find(".//t:StartWhenAvailable", ns).text == "true"
    assert r.find(".//t:ScheduleByWeek/t:DaysOfWeek/t:Tuesday", ns) is not None
    # `[DECISO 2026-08-31]` dall'utente: martedi' alle 21:00. E' una scelta
    # dichiarata, quindi sta in un test come le altre — chi la cambia deve
    # cambiarla anche qui e in CLAUDE.md, invece di spostarla in silenzio.
    assert r.find(".//t:StartBoundary", ns).text.endswith("T21:00:00")
    # su un portatile i default di Windows impedirebbero l'avvio a batteria
    assert r.find(".//t:DisallowStartIfOnBatteries", ns).text == "false"
    assert r.find(".//t:Actions/t:Exec/t:Command", ns).text.endswith(
        "aggiorna_stagione.cmd")


def test_il_manifest_non_dichiara_piu_il_mirror_come_dominio_attuale():
    """Provenienza falsa in git: la nota diceva 1xbet mentre `main.py` punta a
    www dal 2026-08-14. Il mirror resta CITATO — i file vecchi ci sono passati —
    ma non come dominio corrente."""
    from acquisition import manifest
    nota = manifest.DEFINIZIONI["whoscored"]["note"]
    assert "il dominio contattato e' www.whoscored.com" in nota
    assert "1xbet" in nota and "2026-08-14" in nota


# --------------------------------------------------------------------------
# 7. A2 — il prior dalla stagione precedente
# --------------------------------------------------------------------------
import numpy as np                                                  # noqa: E402
import pandas as pd                                                 # noqa: E402

from sot import model_team as MT, prior_stagione as PS              # noqa: E402


def _dati_finti(n_partite: int = 60, seed: int = 0) -> pd.DataFrame:
    """Un campionato giocattolo dove la forza vera e' nota."""
    rng = np.random.default_rng(seed)
    squadre = [f"T{i}" for i in range(8)]
    forza = {t: 0.3 * (i - 3.5) / 3.5 for i, t in enumerate(squadre)}
    righe = []
    for k in range(n_partite):
        a, b = rng.choice(squadre, 2, replace=False)
        for casa, (x, y) in ((1, (a, b)), (0, (b, a))):
            lam = np.exp(2.4 + forza[x] - forza[y] + 0.2 * casa)
            righe.append({"matchId": k, "date": pd.Timestamp("2025-01-01")
                          + pd.Timedelta(days=k),
                          "team": x, "opponent": y, "is_home": casa,
                          "shots": rng.poisson(lam), "sot": rng.poisson(lam / 3)})
    return pd.DataFrame(righe)


def test_prior_none_e_identico_bit_per_bit():
    """La disciplina gia' applicata a `target`, `strict_teams` e `cluster`: un
    parametro nuovo non deve muovere di un bit cio' che e' pubblicato."""
    d = _dati_finti()
    a = MT.TeamModel(alpha=6.0, target="shots").fit(d)
    b = MT.TeamModel(alpha=6.0, target="shots", prior=None,
                     alpha_prior=999.0).fit(d)
    assert np.array_equal(a.beta_, b.beta_)
    riga = pd.DataFrame([{"team": "T0", "opponent": "T7", "is_home": 1}])
    assert a.predict(riga)[0] == b.predict(riga)[0]


def test_a_zero_partite_il_fit_restituisce_il_prior():
    """E' la proprieta' per cui il blocco esiste: con pochissimi dati e una
    penalita' fortissima il modello deve tornare al centro che gli si e' dato."""
    d = _dati_finti(n_partite=2)
    centro = {"T0": (0.5, -0.4), "T1": (-0.5, 0.4)}
    m = MT.TeamModel(alpha=6.0, target="shots", prior=centro,
                     alpha_prior=1e6).fit(d, teams=[f"T{i}" for i in range(8)])
    r = m.ratings().set_index("team")
    assert r.loc["T0", "attack"] == pytest.approx(0.5, abs=1e-3)
    assert r.loc["T0", "defence"] == pytest.approx(-0.4, abs=1e-3)
    # una squadra senza prior resta al centro zero, cioe' alla media
    assert r.loc["T5", "attack"] == pytest.approx(0.0, abs=1e-3)


def test_il_prior_si_scioglie_da_solo_al_crescere_dei_dati():
    """Nessun decadimento da sintonizzare: la verosimiglianza cresce con `n`
    mentre la penalita' resta fissa. Se non fosse cosi', il prior resterebbe
    incollato e la stagione nuova non conterebbe mai.

    Si misura la **distanza fra il fit con prior e quello senza**, sugli stessi
    dati: e' quanto il prior sta ancora spostando la risposta. Deve calare al
    crescere delle partite. Il prior e' centrato apposta — uno spostamento
    costante di tutti gli attacchi verrebbe assorbito da `mu` e non misurerebbe
    niente.
    """
    centro = {f"T{i}": (0.4 * (3.5 - i) / 3.5, 0.0) for i in range(8)}
    distanze = []
    for n in (6, 40, 400):
        d = _dati_finti(n_partite=n)
        squadre = sorted(set(d["team"]) | set(d["opponent"]))
        con = MT.TeamModel(alpha=6.0, target="shots", prior=centro,
                           alpha_prior=30.0).fit(d, teams=squadre)
        senza = MT.TeamModel(alpha=6.0, target="shots").fit(d, teams=squadre)
        distanze.append(float(np.abs(con.beta_ - senza.beta_).mean()))
    assert distanze[0] > distanze[1] > distanze[2], distanze


def test_il_prior_si_centra_e_lo_zero_diventa_la_media():
    """Senza centratura lo zero di una neopromossa non sarebbe la media delle
    altre, e le tre promosse finirebbero tutte dalla stessa parte per un motivo
    aritmetico invece che calcistico."""
    c = PS.centra({"a": 1.0, "b": 2.0, "c": 6.0})
    assert sum(c.values()) == pytest.approx(0.0, abs=1e-12)
    assert c["b"] == pytest.approx(-1.0)
    assert PS.centra({}) == {}


def test_il_prior_vero_e_centrato_e_non_conosce_le_neopromosse():
    p = PS.prior_per("2025-2026")
    assert p.stagione_origine == "2024-2025"
    assert sum(p.attacco.values()) == pytest.approx(0.0, abs=1e-9)
    assert sum(p.difesa.values()) == pytest.approx(0.0, abs=1e-9)
    # le promosse del 2025-26 non erano in Serie A l'anno prima
    u = T.universo(["2025-2026"])
    nuove = set(u["team"]) - p.squadre()
    assert len(nuove) == 3


def test_la_soglia_di_avvio_non_e_scelta_qui():
    """`IDX_AVVIO` e' il complemento del burn-in gia' dichiarato dalla Fase 2:
    sceglierlo qui vorrebbe dire tararlo sul campione su cui poi lo si valuta."""
    assert PS.IDX_AVVIO == config.BURN_IN_ROUND - 1
    src = (config.ROOT / "sot" / "prior_stagione.py").read_text(encoding="utf-8")
    assert "IDX_AVVIO = config.BURN_IN_ROUND - 1" in src

    # `idxmax` e' ammesso in DUE posti soli, e per due ragioni dichiarate:
    # `scegli_alpha_prior` sceglie su un passato che il chiamante gli passa, e
    # `per_indice` descrive senza scegliere niente. Ovunque altrove sarebbe una
    # soglia letta dai dati che poi si valutano.
    import ast as _ast
    albero = _ast.parse(src)
    dove = []
    for f in _ast.walk(albero):
        if isinstance(f, _ast.FunctionDef):
            testo = _ast.dump(f)
            if "idxmax" in testo or "argmax" in testo or "quantile" in testo:
                dove.append(f.name)
    assert sorted(dove) == ["per_indice", "scegli_alpha_prior"], dove


def test_alpha_prior_si_sceglie_solo_sul_passato():
    """Vincolo 1. Se la taratura guardasse la stagione valutata, il margine
    riportato sarebbe in campione."""
    src = (config.ROOT / "scripts"
           / "run_fase14_prior.py").read_text(encoding="utf-8")
    assert "passate = [t for t in transizioni if t < s]" in src
    assert "PS.scegli_alpha_prior(g, passate" in src


def test_la_regola_a_due_regimi_usa_una_soglia_dichiarata_altrove():
    """Non e' un terzo modello: e' la composizione di due candidati dichiarati a
    una soglia che il repository aveva gia' (Fase 2). Sceglierne una nuova
    guardando il grafico sarebbe adattarla al campione."""
    assert str(config.BURN_IN_ROUND) in PS.REGOLA_DUE_REGIMI
    d = pd.DataFrame({"team_match_idx": [1, 5, 6, 20],
                      "lam_modello_prec": [1.0, 2.0, 3.0, 4.0],
                      "lam_con_prior": [10.0, 20.0, 30.0, 40.0]})
    r = PS.con_due_regimi(d)
    assert list(r["lam_due_regimi"]) == [1.0, 2.0, 30.0, 40.0]


def test_le_righe_confrontabili_sono_le_stesse_per_tutti():
    """Confronto orizzontale e non verticale: `senza prior` non risponde alla
    primissima giornata, e valutarlo su un campione piu' facile degli altri e'
    l'errore che E4 ha dovuto correggere sul divario dei bonus."""
    g = PS.griglia_avvio()
    d = g[g["alpha_prior"] == 25.0]
    conf = PS.confronto(d, avvio=True)
    assert conf["n"].nunique() == 1
    val = PS.valutazione(d, avvio=True)
    assert val["n"].nunique() == 1


def test_il_verdetto_applica_il_criterio_meccanicamente():
    """Scritto prima e applicato dal codice: se lo si rileggesse a occhio, la
    soglia si sposterebbe da sola verso il risultato che si spera."""
    conf = pd.DataFrame([{"avversario": "media squadra prec", "riferimento": True,
                          "t_cluster": 3.0}])
    segni = pd.Series({"a": 1.0, "b": 1.0, "c": 1.0, "d": -1.0, "e": -1.0})
    assert PS.verdetto(conf, segni)["adotta"] is True
    # basta che una delle due meta' cada
    assert PS.verdetto(conf.assign(t_cluster=1.0), segni)["adotta"] is False
    assert PS.verdetto(conf, segni * -1)["adotta"] is False


# --------------------------------------------------------------------------
# 8. A3 — i tiri in porta accanto ai tiri
# --------------------------------------------------------------------------
from sot import previsione as P, validate as V                      # noqa: E402

STAGIONE = config.SEASONS_STORICHE[-1]


@pytest.fixture(scope="module")
def prev():
    return P.previsione("Como", "Inter", "casa", STAGIONE)


def test_le_linee_dei_tiri_in_porta_non_sono_state_reinventate():
    """`tentativi.LINEE_SOT_INVARIATE` lo prescrive: linee nuove renderebbero
    questi numeri non confrontabili con la Fase 4, che e' il difetto contro cui
    esiste il vincolo 7."""
    assert P.LINEE_SOT == V.LINES == (2.5, 3.5, 4.5, 5.5)
    assert T.LINEE_SOT_INVARIATE is True


def test_i_tiri_in_porta_hanno_la_loro_r(prev):
    """~20 sui tentativi, ~32 sui tiri in porta: sono due grandezze diverse e la
    seconda non si eredita — e' la stessa ragione per cui V1 ha rifatto da capo
    la validazione della Fase 4 invece di ereditarla."""
    assert prev["r"] != prev["r_sot"]
    assert 15 < prev["r"] < 30
    assert 20 < prev["r_sot"] < 50


def test_la_r_dei_tiri_in_porta_viene_dal_suo_walk_forward():
    """Non da quello dei tentativi con un'altra colonna: `cache` deve separarli,
    altrimenti il secondo sovrascriverebbe il primo."""
    assert VL.cache(target="sot") != VL.cache(target=T.TARGET)
    assert VL.cache(target=T.TARGET) == VL.CACHE


def test_le_probabilita_sono_monotone_e_coerenti(prev):
    """Controllo che non passa da nessun modello: P(Over) deve calare al salire
    della linea, su entrambi i bersagli."""
    for k in ("p_over", "p_over_sot"):
        p = prev[k]["p_over"].to_numpy()
        assert (np.diff(p) < 0).all(), k
        assert ((p > 0) & (p < 1)).all(), k


def test_la_quota_di_pareggio_si_IMPORTA_da_soglie_2627():
    """Fino alla Fase 14 la docstring lo dichiarava e il codice riscriveva
    `1.0/p` a mano: due copie che coincidevano per caso, e il test verificava
    l'uguaglianza numerica invece dell'unicita' della definizione."""
    src = (config.ROOT / "sot" / "previsione.py").read_text(encoding="utf-8")
    assert "soglie_2627 as S" in src
    assert "S.quota_pareggio(" in src
    assert "1.0 / p_over" not in src


# --------------------------------------------------------------------------
# 9. A4 — la regola a due regimi dentro la previsione
# --------------------------------------------------------------------------
def test_senza_contesto_niente_cambia(prev):
    """La disciplina di sempre: un parametro nuovo non muove cio' che e'
    pubblicato. 12.85183830802627 e' il numero di V4."""
    assert prev["lambda_tentativi"] == pytest.approx(12.85183830802627, abs=1e-9)
    assert prev["regime"] == P.REGIMI[1]


@pytest.fixture(scope="module")
def contesto():
    return PS.contesto(STAGIONE)


def test_a_inizio_stagione_il_regime_cambia_da_solo(contesto):
    """Il regime e' una proprieta' della squadra, non della data: a settembre il
    Como puo' avere tre partite e un'altra squadra quattro."""
    p = P.previsione("Como", "Inter", "casa", STAGIONE, al="2025-09-20",
                     contesto=contesto)
    assert p["regime"] == P.REGIMI[0]
    assert p["partite_della_squadra"] < config.BURN_IN_ROUND
    assert any("applicato tale e quale" in a for a in p["avvisi"])


def test_sopra_il_burn_in_si_torna_al_within_season(contesto):
    p = P.previsione("Como", "Inter", "casa", STAGIONE, al="2026-01-15",
                     contesto=contesto)
    assert p["regime"] == P.REGIMI[1]


def test_le_due_strade_danno_lo_stesso_numero(contesto):
    """Tabella e previsione singola devono coincidere: se divergessero, una
    delle due userebbe un modello diverso senza dirlo."""
    t = P.tabella_completa(STAGIONE, al="2025-09-20", contesto=contesto)
    r = t[(t["squadra"] == "Como") & (t["avversario"] == "Inter")
          & (t["campo"] == "casa")].iloc[0]
    p = P.previsione("Como", "Inter", "casa", STAGIONE, al="2025-09-20",
                     contesto=contesto)
    assert r["lambda_tentativi"] == pytest.approx(p["lambda_tentativi"], rel=1e-9)
    assert r["lambda_sot"] == pytest.approx(p["lambda_sot"], rel=1e-9)
    assert r["regime"] == p["regime"]


def test_le_neopromosse_si_contano_invece_di_sparire(contesto):
    """Il prior non le conosce e le tratta come esattamente medie. E' l'unico
    default onesto, ma va **contato**: senza, la pagina mostrerebbe un numero
    plausibile senza dire su cosa poggia."""
    t = P.tabella_completa(STAGIONE, al="2025-09-20", contesto=contesto)
    assert (t["senza_prior"] > 0).sum() > 0
    p = contesto[T.TARGET]["prior"]
    nuove = sorted(set(t["squadra"]) - p.squadre())
    assert len(nuove) == 3
    # e la riga di una neopromossa lo dichiara nei propri avvisi
    q = P.previsione(nuove[0], "Inter", "casa", STAGIONE, al="2025-09-20",
                     contesto=contesto)
    assert any("neopromosse" in a for a in q["avvisi"])


def test_le_squadre_non_si_ereditano_dal_prior(contesto):
    """Prenderle dal prior rimetterebbe dentro le RETROCESSE, che quest'anno non
    giocano. Si prendono dalle partite viste in questa stagione."""
    t = P.tabella_completa(STAGIONE, al="2025-09-20", contesto=contesto)
    viste = set(t["squadra"])
    u = T.universo([STAGIONE])
    assert viste <= set(u["team"])
    retrocesse = contesto[T.TARGET]["prior"].squadre() - set(u["team"])
    assert retrocesse and not (retrocesse & viste)


# --------------------------------------------------------------------------
# 10. A4 — la pagina
# --------------------------------------------------------------------------
PAGINA = config.REPORTS / "previsioni.html"

VIETATE = ("scommessa", "bankroll", "kelly", "stake", "roi", "puntata",
           "bookmaker", "quota consigliata")


def test_la_pagina_e_autonoma():
    """«Pagina locale» vuol dire che funziona offline: nessun CDN, nessun font
    remoto, nessuna richiesta di rete."""
    if not PAGINA.is_file():
        pytest.skip("manca la pagina: esegui run_previsioni.py")
    testo = PAGINA.read_text(encoding="utf-8")
    for vietato in ("http://", "https://", "//cdn", "fetch(", "XMLHttpRequest",
                    "WebSocket", "@import"):
        assert vietato not in testo, f"la pagina contiene {vietato}"


def test_la_pagina_non_propone_scommesse():
    """Vincolo 3. Il confine e' di LETTERA e non di sottostringa: `roi` dentro
    `proiezione` non deve far scattare la guardia — e' il falso positivo che S1
    ha dovuto correggere."""
    if not PAGINA.is_file():
        pytest.skip("manca la pagina: esegui run_previsioni.py")
    testo = PAGINA.read_text(encoding="utf-8").lower()
    trovate = [v for v in VIETATE
               if re.search(rf"(?<![a-zA-Z]){re.escape(v)}(?![a-zA-Z])", testo)]
    # `scommessa` compare nella frase che DICHIARA di non proporne — e' uno dei
    # `limiti()` di V4, stampati in pagina. Si ammette solo quella, e il test la
    # nomina invece di allargare il divieto: e' la stessa eccezione, scritta allo
    # stesso modo, di `tests/test_fase12_v4.py`.
    assert set(trovate) - {"scommessa"} == set(), trovate
    assert "valutazione di scommessa (vincolo 3)" in testo


def test_la_guardia_del_vincolo_3_sa_dire_anche_di_si():
    """Meta-test: senza, «nessuna parola vietata» potrebbe voler dire «la
    guardia non guarda niente»."""
    def trova(t):
        return [v for v in VIETATE
                if re.search(rf"(?<![a-zA-Z]){re.escape(v)}(?![a-zA-Z])", t)]
    assert "bankroll" in trova("calcola_bankroll = 1")
    assert trova("proiezione") == []
    assert trova("mistakes") == []


def test_la_pagina_contiene_i_numeri_della_previsione():
    """Se il generatore calcolasse invece di serializzare, pagina e modello
    potrebbero divergere senza che nessuno se ne accorga."""
    if not PAGINA.is_file():
        pytest.skip("manca la pagina: esegui run_previsioni.py")
    import json as _json
    testo = PAGINA.read_text(encoding="utf-8")
    i = testo.index("const DATI=")
    dati = _json.loads(testo[i + len("const DATI="):testo.index(";</script>", i)])

    assert set(dati["campionati"]) <= set(config.LEAGUE_CODES)
    assert dati["linee"] == list(T.LINEE_TIRI)
    assert dati["linee_sot"] == list(P.LINEE_SOT)
    assert dati["burn_in"] == config.BURN_IN_ROUND

    b = dati["campionati"][config.LEAGUE]
    r = next(x for x in b["righe"]
             if x["s"] == "Como" and x["a"] == "Inter" and x["c"] == "casa")

    # **Si riusa `run_previsioni.blocco`, non si rifa' il conto a mano.** Il test
    # chiamava `P.previsione(...)` senza `contesto`, e ha smesso di funzionare
    # quando la 2026-2027 ha avuto le prime partite: sotto il burn-in la pagina
    # usa il **prior** e il test la confrontava con il within-season. Rifare qui
    # la costruzione del contesto sarebbe una seconda copia della stessa regola,
    # cioe' il modo di farle divergere; chiamare la stessa funzione della pagina
    # verifica cio' che il test vuole davvero — che il generatore SERIALIZZI
    # invece di calcolare.
    import run_previsioni as RP

    tab = RP.blocco(config.LEAGUE, b["stagione"])["tabella"]
    riga = tab[(tab["squadra"] == "Como") & (tab["avversario"] == "Inter")
               & (tab["campo"] == "casa")].iloc[0]
    assert r["lam"] == pytest.approx(float(riga["lambda_tentativi"]), abs=1e-4)
    assert r["sot"] == pytest.approx(float(riga["lambda_sot"]), abs=1e-4)
    assert r["reg"] == riga["regime"]


def test_la_pagina_dichiara_il_ripiego_di_stagione():
    """Mostrare i numeri dell'anno scorso credendo che siano di quest'anno e' il
    difetto peggiore che questa pagina possa avere: se il ripiego avviene, va
    scritto."""
    import run_previsioni as RP
    s, nota = RP.stagione_disponibile(config.LEAGUE, "2026-2027")
    if s != "2026-2027":
        assert nota, "ripiego silenzioso"
        assert "2026-2027" in nota and s in nota


def test_la_pagina_e_uno_stato_completo_non_incrementale():
    """`aggiorna_stagione` NON passa `--league` a `run_previsioni`, nemmeno
    quando ha aggiornato un campionato solo.

    Il difetto e' silenzioso e l'ho trovato eseguendo: filtrando sui campionati
    aggiornati stavolta, gli altri quattro **sparirebbero dalla pagina** senza
    che nulla vada in errore. Ricalcolarli tutti costa un minuto.

    La guardia guarda il **codice**, non la prosa: la prima stesura cercava
    `--league` come sottostringa e puniva il commento che spiega perche' non lo
    si passa. E' la quarta volta che in questo repository una guardia scritta su
    una forma invece che su una proprieta' da' un falso positivo — dopo il gate
    sui qualifier, le guardie del vincolo 3 e la cache di V1.
    """
    import io
    import tokenize

    src = (config.ROOT / "scripts"
           / "aggiorna_stagione.py").read_text(encoding="utf-8")
    codice = "".join(
        t.string if t.type not in (tokenize.COMMENT, tokenize.NL) else ""
        for t in tokenize.generate_tokens(io.StringIO(src).readline)
        if t.type != tokenize.COMMENT)

    coda = codice[codice.index("Rigenero le previsioni"):]
    assert 'run_previsioni.main(["--season",args.season])' in coda.replace(" ", "")
    assert "--league" not in coda


def test_la_pagina_copre_tutti_i_campionati_con_dati():
    """Il complemento eseguibile del test qui sopra."""
    if not PAGINA.is_file():
        pytest.skip("manca la pagina: esegui run_previsioni.py")
    import json as _json
    testo = PAGINA.read_text(encoding="utf-8")
    i = testo.index("const DATI=")
    dati = _json.loads(testo[i + len("const DATI="):testo.index(";</script>", i)])
    assert set(dati["campionati"]) == set(config.LEAGUE_CODES)


#: Cio' che il generatore della pagina non deve FARE. Non e' un divieto di
#: parole: la docstring del modulo nomina `TeamModel` proprio per dichiarare che
#: non lo usa, ed e' la forma piu' utile di documentazione che ci sia.
CALCOLI_VIETATI = ("TeamModel", "p_over", "fit", "numpy")


def test_il_generatore_della_pagina_non_calcola_niente():
    """`pagina_previsioni` serializza e basta, come `pagina_v4`: un solo conto
    qui e la pagina potrebbe divergere dal modello.

    **La guardia guarda il CODICE, non la prosa.** La prima stesura cercava
    sottostringhe nel sorgente intero e ha dichiarato colpevole la docstring che
    dice <<questo modulo non calcola: un test vieta `TeamModel` nel sorgente>>.
    E' la settima volta che in questo repository una guardia scritta su una
    FORMA invece che su una PROPRIETA' da' un falso positivo - dopo il gate sui
    qualifier (E1), le guardie a sottostringa del vincolo 3 (S1), la cache di V1,
    il `--league` della Fase 14, le due guardie di E0 e l'host dell'URL in C1.
    Si riusa `_codice` di V0, che tokenizza e butta commenti e stringhe, invece
    di riscriverne una copia.
    """
    from test_fase12_v0 import _codice

    codice = _codice(config.ROOT / "scripts" / "pagina_previsioni.py")
    for vietato in CALCOLI_VIETATI:
        assert vietato not in codice, vietato


def test_la_guardia_sul_generatore_sa_dire_anche_di_si():
    """Meta-test: senza, <<il generatore non calcola>> potrebbe voler dire
    <<la guardia non guarda niente>>. Si scrive un modulo finto che CALCOLA e si
    pretende che venga fermato, e uno che ne parla soltanto e passa."""
    import io as _io
    import tokenize as _tk

    def codice(src):
        return " ".join(
            t.string for t in _tk.generate_tokens(_io.StringIO(src).readline)
            if t.type not in (_tk.COMMENT, _tk.STRING))

    riga = chr(10)
    colpevole = codice(riga.join(['x = 1', 'import numpy',
                                  'y = numpy.mean([1])', '']))
    assert any(v in colpevole for v in CALCOLI_VIETATI)

    innocente = codice(riga.join(
        ['\'\'\'un test vieta numpy e TeamModel qui dentro.\'\'\'',
         'x = 1', '']))
    assert not any(v in innocente for v in CALCOLI_VIETATI)
