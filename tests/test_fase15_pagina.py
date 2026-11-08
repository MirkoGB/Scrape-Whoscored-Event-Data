# -*- coding: utf-8 -*-
"""Fase 15 / P1 - il turno, il ponte sul calendario e la pagina.

Tre cose vanno bloccate, e nessuna e' cosmetica:

1. **il turno non e' sempre una giornata.** Dove la fonte non la porta si
   ripiega, e il ripiego va dichiarato: un blocco di date spacciato per un turno
   di campionato e' esattamente il genere di difetto che il vincolo 7 esiste per
   impedire. In piu' la deduzione dalla data non deve MAI diventare la giornata
   della riga - solo il turno in cui la riga e' mostrata;
2. **il totale e' la somma esatta.** `E[X+Y]=E[X]+E[Y]` non ha ipotesi, e la
   pagina non deve mostrare un numero che non sia quella somma;
3. **il generatore serializza e basta.** Un solo conto li' e la pagina puo'
   divergere dal modello senza che nessuno se ne accorga.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from sot import calendario as CAL, config, dispersion as DI  # noqa: E402
from sot import previsione as P, tentativi as T, totale as TOT  # noqa: E402

PAGINA = config.REPORTS / "previsioni.html"


# --------------------------------------------------------------------------
# 1. la data, e la sua forma accertata
# --------------------------------------------------------------------------
def test_la_data_si_legge_nella_forma_accertata():
    assert CAL.data("venerdi, set 04 2026") == pd.Timestamp(2026, 9, 4)
    assert CAL.data("domenica, dic 13 2026") == pd.Timestamp(2026, 12, 13)


def test_una_data_illeggibile_torna_none_e_non_solleva():
    """Una riga storta e' un limite di quella riga, non la fine del calendario
    di un campionato intero."""
    for storta in (None, "", "boh", "lunedi, xxx 04 2026", "set 04 2026",
                   "lunedi, set 99 2026", 7):
        assert CAL.data(storta) is None


def test_i_mesi_osservati_sono_un_sottoinsieme_dei_dichiarati():
    """I tre non osservati (giu lug ago) sono completamento della serie, e la
    distinzione sta scritta invece di essere persa."""
    assert set(CAL.MESI_OSSERVATI) <= set(CAL.MESI)
    assert len(CAL.MESI) == 12
    assert len(CAL.MESI_OSSERVATI) == 9


def test_le_date_dei_calendari_veri_si_leggono_tutte():
    """Il complemento eseguibile: se la forma cambiasse alla fonte, qui si
    vedrebbe subito invece che in un turno <<data ignota>> in pagina."""
    visti = 0
    for L in sorted(config.LEAGUE_CODES):
        c = CAL.calendario(league=L)
        if c.empty:
            continue
        visti += 1
        assert all(CAL.data(x) is not None for x in c["data_fonte"]), L
    assert visti >= 1, "nessun calendario su disco: il test non ha guardato niente"


# --------------------------------------------------------------------------
# 2. il turno
# --------------------------------------------------------------------------
def _finto(righe) -> pd.DataFrame:
    """Un calendario minimo. `data_fonte` nella forma vera della fonte."""
    return pd.DataFrame([{
        "data_fonte": d, "casa": c, "trasferta": a, "score": None,
        "url": "", "giocata": False, "campionato": "X", "stagione": "2026-2027",
        "matchId": i, "giornata": g,
        "fonte_giornata": "wikipedia" if g is not None else "assente",
    } for i, (d, c, a, g) in enumerate(righe)])


def test_la_giornata_della_fonte_vince_dove_ce():
    c = CAL.con_turno(_finto([("sabato, set 05 2026", "A", "B", 3),
                              ("domenica, set 06 2026", "C", "D", 3)]))
    assert list(c["turno"]) == ["g3", "g3"]
    assert set(c["fonte_turno"]) == {CAL.FONTI_TURNO[0]}
    assert set(c["etichetta_turno"]) == {"3a giornata"}


def test_la_deduzione_dalla_data_non_diventa_mai_la_giornata_della_riga():
    """**E' il test piu' importante del gruppo.** Il contenimento decide dove la
    riga viene MOSTRATA; scrivere quel numero nella colonna della giornata
    sarebbe inventarla, che e' il difetto che C1 ha rifiutato di commettere."""
    c = CAL.con_turno(_finto([("sabato, set 05 2026", "A", "B", 3),
                              ("domenica, set 06 2026", "C", "D", 3),
                              ("domenica, set 06 2026", "E", "F", None)]))
    riga = c[c["casa"] == "E"].iloc[0]
    assert riga["turno"] == "g3"
    assert riga["fonte_turno"] == CAL.FONTI_TURNO[1]
    assert riga["fonte_giornata"] == "assente"
    assert pd.isna(riga["giornata"])


def test_una_data_in_due_finestre_e_ambigua_e_non_si_sceglie():
    """La stessa disciplina di `mappa_squadre`: contenimento **se unico**."""
    c = CAL.con_turno(_finto([
        ("sabato, set 05 2026", "A", "B", 3),
        ("mercoledi, set 09 2026", "C", "D", 3),      # la 3a copre 5-9 set
        ("lunedi, set 07 2026", "E", "F", 4),
        ("giovedi, set 10 2026", "G", "H", 4),        # la 4a copre 7-10 set
        ("martedi, set 08 2026", "I", "J", None),     # dentro entrambe
    ]))
    riga = c[c["casa"] == "I"].iloc[0]
    assert riga["fonte_turno"] == CAL.FONTI_TURNO[2], "ha scelto invece di astenersi"


def test_il_contenimento_non_sfonda_la_capienza_strutturale():
    """Un turno non puo' avere piu' di `squadre/2` partite. Senza questo
    vincolo la Ligue 1 usciva con una <<5a giornata>> da 12 partite su 18
    squadre: i rinvii hanno una data che cade nella finestra di un altro turno.
    """
    righe = [("sabato, set 05 2026", "A", "B", 3),
             ("sabato, set 05 2026", "C", "D", 3)]
    # quattro squadre => capienza 2, gia' piena: i candidati vanno RIFIUTATI
    righe.append(("domenica, set 06 2026", "A", "C", None))
    c = CAL.con_turno(_finto(righe))
    assert c[c["casa"] == "A"].iloc[-1]["fonte_turno"] == CAL.FONTI_TURNO[2]


def test_nessun_turno_supera_la_capienza_sui_dati_veri():
    for L in sorted(config.LEAGUE_CODES):
        c = CAL.calendario(league=L)
        if c.empty:
            continue
        capienza = max(1, len(set(c["casa"]) | set(c["trasferta"])) // 2)
        t = CAL.turni(league=L, cal=c)
        assert int(t["partite"].max()) <= capienza, L


def test_i_turni_partizionano_le_partite():
    """Ogni partita in esattamente un turno: ne' persa ne' contata due volte."""
    for L in sorted(config.LEAGUE_CODES):
        c = CAL.calendario(league=L)
        if c.empty:
            continue
        t = CAL.turni(league=L, cal=c)
        assert int(t["partite"].sum()) == len(c), L
        assert CAL.con_turno(c)["turno"].notna().all(), L


def test_i_turni_sono_in_ordine_di_data_non_di_numero():
    """Con i recuperi la 12a puo' giocarsi dopo la 13a: ordinare per numero
    metterebbe in pagina un turno gia' passato in mezzo ai futuri."""
    c = _finto([("sabato, ott 03 2026", "A", "B", 12),
                ("sabato, set 05 2026", "C", "D", 13)])
    t = CAL.turni(cal=c)
    assert list(t["turno"]) == ["g13", "g12"]


def test_le_fonti_del_turno_sono_tre_e_dichiarate():
    assert len(CAL.FONTI_TURNO) == 3
    assert CAL.FONTI_TURNO[0] == "giornata"
    assert "blocco" in CAL.FONTI_TURNO[2]


# --------------------------------------------------------------------------
# 3. il ponte sul calendario
# --------------------------------------------------------------------------
@pytest.fixture(scope="module")
def blocco_ita():
    import run_previsioni as RP
    b = RP.blocco(config.LEAGUE, config.SEASON_CORRENTE, verbose=False)
    if b is None or len(b["calendario"]) == 0:
        pytest.skip("manca il calendario della stagione in corso")
    return b


def test_il_totale_e_la_somma_esatta_dei_due_lati(blocco_ita):
    """`E[X+Y] = E[X] + E[Y]` non richiede nessuna ipotesi sulla dipendenza:
    e' l'unica cosa di T1 che non abbia avuto bisogno di una misura."""
    c = blocco_ita["calendario"]
    assert np.allclose(c["lam_totale"], c["lam_casa"] + c["lam_trasferta"])
    assert np.allclose(c["sot_totale"], c["sot_casa"] + c["sot_trasferta"])


def test_le_probabilita_del_totale_usano_r_tot_e_non_r_per_lato(blocco_ita):
    c = blocco_ita["calendario"]
    r_tot = float(c["r_tot"].iloc[0])
    r_lato = float(blocco_ita["tabella"]["r"].iloc[0])
    # T1: il rapporto ha IC95 [3,46, 5,66] e non contiene 1
    assert r_tot > 2 * r_lato, (r_tot, r_lato)

    ln = TOT.LINEE_TOTALE_TIRI[2]
    atteso = DI.p_over(c["lam_totale"].to_numpy(), ln, r_tot)
    assert np.allclose(c[f"p_tot_{ln}"], atteso)


def test_r_tot_si_stima_sul_solo_passato(blocco_ita):
    """Vincolo 1: `r` entra nelle probabilita' Over. Se `_r_tot_corrente`
    ignorasse la data, tagliare la storia non cambierebbe il numero."""
    st = P.storia(blocco_ita["stagione"], league=config.LEAGUE)
    intero = P._r_tot_corrente(st, league=config.LEAGUE)

    d = TOT.partite(league=config.LEAGUE, con_baseline=False)
    v = d[d["validabile"]]
    meta = v["data"].quantile(0.5)
    corto = P._r_tot_corrente(pd.DataFrame({"date": [meta]}),
                              league=config.LEAGUE)
    assert not np.isclose(intero, corto), "la data non filtra niente"


def test_una_squadra_mai_vista_passa_dal_prior_e_viene_contata(blocco_ita):
    """La decisione dell'utente sul turno zero: **squadre dal calendario,
    numeri dal prior**, e la squadra si conta invece di sparire."""
    c = blocco_ita["calendario"].iloc[:2].copy()
    c["casa"] = "Squadra Che Non Esiste"
    fuori = P.tabella_calendario(c, blocco_ita["stagione"],
                                 league=config.LEAGUE,
                                 contesto=blocco_ita["contesto"],
                                 tab=blocco_ita["tabella"])
    if blocco_ita["contesto"] is None:
        pytest.skip("questa stagione non usa il prior")
    assert len(fuori) == 2
    assert (fuori["squadre_non_viste"] == 1).all()
    assert (fuori["regime"] == P.REGIMI[0]).all()
    assert fuori.attrs["scartate"] == 0


def test_senza_prior_una_squadra_mai_vista_esce_e_si_dichiara(blocco_ita):
    """Una riga senza numeri e' meglio di una riga con un numero inventato -
    ma va **contata**, non fatta sparire."""
    c = blocco_ita["calendario"].iloc[:3].copy()
    c["casa"] = "Squadra Che Non Esiste"
    fuori = P.tabella_calendario(c, blocco_ita["stagione"],
                                 league=config.LEAGUE, contesto=None,
                                 tab=blocco_ita["tabella"])
    assert len(fuori) == 0
    assert fuori.attrs["scartate"] == 3
    assert len(fuori.attrs["scartate_nomi"]) == 3


def test_le_due_guardie_di_v4_non_sono_state_allentate():
    """P1 aggiunge un regime, non toglie una guardia: il modello within-season
    continua a rifiutare una squadra che non conosce."""
    with pytest.raises(Exception):
        P.previsione("Squadra Che Non Esiste", "Inter", "casa")
    with pytest.raises(Exception):
        P.verifica_squadre({"Inter", "Como"}, "Fantasia", "Inter",
                           config.SEASONS_STORICHE[-1])


def test_la_ricalibrazione_del_totale_non_si_applica_in_pagina():
    """T1 l'ha adottata in **3 celle su 10**: applicarla dove passa e non dove
    non passa renderebbe i cinque campionati non confrontabili. La decisione e'
    una costante dichiarata, non un'omissione."""
    from test_fase12_v0 import _codice

    assert P.RICALIBRAZIONE_IN_PAGINA is False
    # **La guardia guarda il CODICE, non la prosa**: `run_previsioni` PARLA
    # della ricalibrazione nei propri commenti, ed e' cio' che deve fare. La
    # prima stesura di questo test cercava la sottostringa nel sorgente intero,
    # cioe' ripeteva l'errore che P1 stesso ha dovuto correggere due volte.
    codice = _codice(config.ROOT / "scripts" / "run_previsioni.py")
    assert "ricalibrazione" not in codice
    assert "lam_ricalibrato" not in codice


def test_la_calibrazione_del_totale_e_dichiarata_per_campionato(blocco_ita):
    """Vincolo 5: il limite sta accanto al numero, e il numero e' di QUEL
    campionato - fra Bundesliga e Liga `r_tot` cambia di un fattore 2,7."""
    c = P.calibrazione_totale(league=config.LEAGUE)
    assert 0.3 < c["pendenza"] < 1.0
    assert c["z"] < -2, "il totale dovrebbe risultare sotto-calibrato"
    assert c["n"] > 1000


def test_il_ponte_non_scrive_niente_sotto_data(blocco_ita):
    """`previsione` non ha cache: un test lo pretende, come `SCRIVE_SU_DISCO`
    per `totale`."""
    from test_fase12_v0 import _codice

    codice = _codice(config.ROOT / "sot" / "previsione.py")
    assert "to_parquet" not in codice
    assert "to_csv" not in codice


# --------------------------------------------------------------------------
# 4. la pagina
# --------------------------------------------------------------------------
def _blob():
    if not PAGINA.is_file():
        pytest.skip("manca la pagina: esegui run_previsioni.py")
    t = PAGINA.read_text(encoding="utf-8")
    i = t.index("const DATI=")
    return t, json.loads(t[i + len("const DATI="):t.index(";</script>", i)])


def test_la_pagina_serializza_le_linee_del_totale_di_t1():
    """Le linee del totale sono dichiarate in T1 prima dei risultati e non si
    riscrivono in pagina."""
    _, d = _blob()
    assert d["linee_tot"] == list(TOT.LINEE_TOTALE_TIRI)
    assert d["linee_tot_sot"] == list(TOT.LINEE_TOTALE_SOT)
    assert d["fonti_turno"] == list(CAL.FONTI_TURNO)
    assert d["regimi"] == list(P.REGIMI)


def test_in_pagina_i_turni_partizionano_le_partite():
    _, d = _blob()
    for nome, b in d["campionati"].items():
        if not b["partite_cal"]:
            continue
        idx = sorted(i for t in b["turni"] for i in t["p"])
        assert idx == list(range(len(b["partite_cal"]))), nome


def test_in_pagina_il_totale_e_la_somma_esatta():
    """Il numero grande in scheda deve essere `lc + la`, non una terza cosa."""
    _, d = _blob()
    for nome, b in d["campionati"].items():
        for p in b["partite_cal"]:
            assert abs(p["lt"] - (p["lc"] + p["la"])) < 1e-3, (nome, p["c"])
            assert abs(p["st"] - (p["sc"] + p["sa"])) < 1e-3, (nome, p["c"])


def test_la_pagina_dichiara_la_sotto_calibrazione_del_totale():
    """Vincolo 5. Il difetto peggiore sarebbe mostrare `P(Over)` sul totale
    senza dire che quella pendenza sta a 0,63."""
    testo, d = _blob()
    assert "sotto-calibrato" in testo
    for nome, b in d["campionati"].items():
        assert 0.3 < b["pend_tot"] < 1.0, nome
        assert 0.3 < b["pend_tot_sot"] < 1.2, nome


def test_la_pagina_dichiara_che_un_blocco_di_date_non_e_una_giornata():
    testo, _ = _blob()
    assert "blocco di date" in testo
    assert "dedotta dalla data" in testo


def test_la_pagina_contiene_i_numeri_del_calendario():
    """Se il generatore calcolasse invece di serializzare, pagina e modello
    potrebbero divergere. Si riusa `run_previsioni.blocco`, non si rifa' il
    conto a mano: rifarlo qui sarebbe una seconda copia della stessa regola."""
    import run_previsioni as RP

    _, d = _blob()
    b = d["campionati"][config.LEAGUE]
    if not b["partite_cal"]:
        pytest.skip("nessun calendario in pagina per questo campionato")

    vero = RP.blocco(config.LEAGUE, b["stagione"], verbose=False)
    cal = vero["calendario"]
    p = b["partite_cal"][0]
    riga = cal[(cal["casa"] == p["c"]) & (cal["trasferta"] == p["a"])].iloc[0]
    assert p["lt"] == pytest.approx(float(riga["lam_totale"]), abs=1e-4)
    assert p["st"] == pytest.approx(float(riga["sot_totale"]), abs=1e-4)
    assert p["r"] == riga["regime"]
    assert b["r_tot"] == pytest.approx(float(riga["r_tot"]), abs=1e-3)


def test_la_pagina_tiene_la_modalita_a_coppia_libera():
    """Toglierla avrebbe fatto sparire una risposta che il repository sa gia'
    dare, e che il calendario non copre (una coppia che non si gioca)."""
    testo, d = _blob()
    for nome, b in d["campionati"].items():
        assert b["righe"], nome
    assert "coppia qualsiasi" in testo
