# -*- coding: utf-8 -*-
"""Fase 15 / Blocco T1 - il totale di partita.

Il gruppo piu' importante e' il primo: la **rotazione** da squadra-partita a
partita. Se accoppiasse le squadre sbagliate, ogni numero del blocco sarebbe
plausibile e sbagliato, e nessuna metrica se ne accorgerebbe - e' lo stesso
difetto che V0 trovo' su `sot_conceded` aggregato con la chiave sbagliata.

Il secondo gruppo verifica che la disciplina sia stata seguita e non solo
dichiarata: soglie letterali, criterio applicato meccanicamente, walk-forward
davvero walk-forward.
"""
from __future__ import annotations

import re

import numpy as np
import pandas as pd
import pytest

from sot import config, tentativi as T, totale as TT, validate as V
from test_fase12_v0 import _codice          # riusata, non riscritta

MODULO = config.ROOT / "sot" / "totale.py"


@pytest.fixture(scope="module")
def d():
    return TT.partite()


# --------------------------------------------------------------------------
# 1. La rotazione a partita
# --------------------------------------------------------------------------
def test_il_perimetro_e_quello_di_r0(d):
    """1.638 partite validabili: lo stesso numero che R0 conto' sui gol.

    Due bersagli diversi sullo stesso universo devono dare lo stesso perimetro,
    perche' `eligible` non dipende dal bersaglio. Se divergessero, uno dei due
    walk-forward starebbe girando su righe che l'altro non ha.
    """
    assert int(d["validabile"].sum()) == 1638
    assert len(d) == 1739


def test_le_partite_con_un_lato_solo_sono_due_e_stanno_nel_2021_2022(d):
    """`eligible` e' una proprieta' della SQUADRA, non della partita."""
    storte = d[d["elig_casa"] ^ d["elig_trasferta"]]
    assert len(storte) == 2
    assert set(storte["stagione"]) == {"2021-2022"}


def test_la_rotazione_solleva_se_una_partita_ha_un_lato_solo():
    """Senza questo controllo `lam_casa` verrebbe da un groupby che sceglie."""
    wf = TT.VL.walkforward_tiri()
    rotto = wf.drop(index=wf.index[0])
    with pytest.raises(ValueError, match="non hanno due lati"):
        TT.partite(wf=rotto)


def test_la_rotazione_solleva_se_i_due_lati_non_si_distinguono():
    """Se `is_home` fosse costante, casa e trasferta sarebbero intercambiabili."""
    wf = TT.VL.walkforward_tiri().copy()
    wf["is_home"] = 1
    with pytest.raises(ValueError, match="esattamente un lato di casa"):
        TT.partite(wf=wf)


def test_la_verifica_su_lam_subiti_vede_un_accoppiamento_sbagliato():
    """La guardia gratuita deve poter fallire, o non sta guardando niente.

    Si guasta `lam_subiti` di una riga sola: e' la firma di un accoppiamento
    sbagliato, e senza questo test 'la verifica passa' e 'la verifica non
    controlla' sarebbero indistinguibili.
    """
    wf = TT.VL.walkforward_tiri().copy()
    prima = wf.index[wf["is_home"] == 1][0]
    wf.loc[prima, "lam_subiti"] = 999.0
    with pytest.raises(ValueError, match="accoppiato le squadre sbagliate"):
        TT.partite(wf=wf)


def test_il_totale_e_esattamente_la_somma_dei_due_lati(d):
    """L'unica cosa del blocco che non ha bisogno di una misura."""
    assert np.allclose(d["lam_totale"], d["lam_casa"] + d["lam_trasferta"])
    assert np.allclose(d["y_totale"], d["y_casa"] + d["y_trasferta"])


# --------------------------------------------------------------------------
# 2. Le soglie: dichiarate prima, non ricavate dai dati
# --------------------------------------------------------------------------
def test_le_linee_del_totale_sono_letterali_e_non_derivate():
    """Vincolo 1 applicato a una soglia, con la regola piu' severa di V0.

    Il divieto di `quantile` e' quello di V0: nessun quantile empirico deve
    poter entrare in una soglia. La guardia tokenizza, quindi il commento del
    modulo che *nomina* `to_parquet` per dire che non lo usa non viene punito.
    """
    src = _codice(MODULO)
    assert TT.LINEE_TOTALE_TIRI == (20.5, 22.5, 24.5, 26.5, 28.5)
    assert TT.LINEE_TOTALE_SOT == (6.5, 7.5, 8.5, 9.5)
    for vietato in ("argmax", "idxmax", "quantile"):
        assert vietato not in src, f"{vietato} nel CODICE del modulo delle soglie"


def test_il_modulo_non_scrive_niente():
    """`SCRIVE_SU_DISCO` non e' una dichiarazione di intenti: e' verificabile."""
    src = _codice(MODULO)
    assert TT.SCRIVE_SU_DISCO is False
    for vietato in ("to_parquet", "to_csv", "write_text"):
        assert vietato not in src, f"{vietato} nel codice: il modulo scrive"


def test_ogni_linea_sta_dentro_la_regola_dei_tassi_base(d):
    """`BASE_RATE_AMMESSO` si RIUSA da `tentativi`, non si riscrive."""
    for target, dd in ((TT.TARGET, d), (TT.TARGET_PRECISIONE, None)):
        tab = TT.brier_per_linea(dd, target=target)
        assert tab["dentro_regola"].all(), tab[~tab["dentro_regola"]]
        basso, alto = T.BASE_RATE_AMMESSO
        assert tab["tasso_base"].between(basso, alto).all()


def test_le_linee_del_totale_non_sono_quelle_per_squadra():
    """Sono un'altra grandezza, e usare quelle per squadra sarebbe fuori regola.

    Il flag `LINEE_SOT_INVARIATE` protegge le linee **per squadra**: questo test
    verifica che la distinzione sia reale e non un cavillo, cioe' che le linee
    per squadra applicate al totale darebbero tassi base fuori dalla regola.
    """
    assert T.LINEE_SOT_INVARIATE is True
    assert set(TT.LINEE_TOTALE_SOT).isdisjoint(V.LINES)
    d = TT.partite(target=TT.TARGET_PRECISIONE)
    y = d.loc[d["validabile"], "y_totale"].to_numpy(dtype=float)
    fuori = [ln for ln in V.LINES if (y > ln).mean() > T.BASE_RATE_AMMESSO[1]]
    # TRE su quattro, non tutte: la 5.5 resterebbe dentro a 0,818. Il test
    # fissa il numero vero invece di quello comodo.
    assert fuori == [2.5, 3.5, 4.5]


def test_linee_del_solleva_su_un_bersaglio_senza_linee():
    with pytest.raises(ValueError, match="senza linee dichiarate"):
        TT.linee_del("gol_fatti")


# --------------------------------------------------------------------------
# 3. Vincolo 1: niente si stima su dati che seguono il target
# --------------------------------------------------------------------------
def test_r_totale_walkforward_non_usa_il_futuro(d):
    """Si guasta la coda della stagione e le date precedenti non devono muoversi.

    E' la forma che V4 usa sul lambda e che i test di leakage usano su
    `walkforward_r`: un guasto nel futuro che cambiasse il passato sarebbe la
    prova che il passato lo sta guardando.
    """
    v = d[d["validabile"]].copy()
    r_sano = TT.r_walkforward(d)

    taglio = v["data"].quantile(0.8)
    rotto = d.copy()
    m = rotto["data"] >= taglio
    rotto.loc[m, "y_casa"] = 40.0
    rotto["y_totale"] = rotto["y_casa"] + rotto["y_trasferta"]
    r_rotto = TT.r_walkforward(rotto)

    prima = v["data"].to_numpy() < np.datetime64(taglio)
    assert np.allclose(r_sano[prima], r_rotto[prima]), "il passato ha visto il futuro"
    assert not np.allclose(r_sano[~prima], r_rotto[~prima]), "il guasto non ha effetto"


def test_la_ricalibrazione_e_walkforward(d):
    """Rovesciare l'ultima stagione non deve muovere nessun `k` gia' applicato."""
    r_sano = TT.ricalibrazione(d)
    ultima = sorted(d["stagione"].unique())[-1]

    rotto = d.copy()
    m = rotto["stagione"] == ultima
    rotto.loc[m, "y_casa"] = 40.0
    rotto["y_totale"] = rotto["y_casa"] + rotto["y_trasferta"]
    r_rotto = TT.ricalibrazione(rotto)

    k_sano = r_sano.groupby("stagione")["k_applicato"].first()
    k_rotto = r_rotto.groupby("stagione")["k_applicato"].first()
    assert np.allclose(k_sano.to_numpy(dtype=float),
                       k_rotto.to_numpy(dtype=float), equal_nan=True)


def test_la_stagione_piu_vecchia_resta_non_ricalibrata(d):
    """Marcata, non riempita: lo stesso trattamento della 2021-2022 in R2-bis."""
    r = TT.ricalibrazione(d)
    prima = sorted(r["stagione"].unique())[0]
    assert not r.loc[r["stagione"] == prima, "ricalibrata"].any()
    assert r.loc[r["stagione"] == prima, "lam_ricalibrato"].isna().all()
    assert r.loc[r["stagione"] != prima, "ricalibrata"].all()


# --------------------------------------------------------------------------
# 4. I fatti che il blocco pubblica, fissati perche' restino visibili
# --------------------------------------------------------------------------
def test_r_del_totale_non_si_eredita_da_r_per_lato(d):
    """L'IC95 del rapporto non contiene 1: e' la verifica falsificabile."""
    r = TT.rapporto_dispersioni(d, n_boot=200)
    assert r["r_totale"] > r["r_lato"]
    assert not r["eredita"]
    assert r["ic95"][0] > 1.0


def test_i_quattro_baseline_diventano_due_sul_totale(d):
    """Il termine di campo si cancella nella somma: e' aritmetica, non un difetto.

    Il fatto sta in un test perche' altrimenti sparirebbe: il vincolo 6 e'
    rispettato con **due** concorrenti distinti e non quattro, e chi leggesse
    quattro righe nella tabella crederebbe il contrario.
    """
    v = d[d["validabile"]]
    coppie = [("media squadra + campo", "media squadra"),
              ("media casa/trasferta", "media campionato")]
    for a, b in coppie:
        assert np.allclose(v[f"{a}_totale"], v[f"{b}_totale"]), f"{a} != {b}"
        # ma per LATO sono diversi eccome, o il collasso sarebbe un altro difetto
        assert not np.allclose(v[f"{a}_casa"], v[f"{b}_casa"])


def test_il_cluster_di_partita_e_degenere(d):
    """Una riga *e'* una partita: i due `t` coincidono per costruzione."""
    app = TT.confronto_appaiato(d)
    assert app["cluster_degenere"].all()
    assert np.allclose(app["t_per_riga"], app["t_per_cluster"])


def test_la_pendenza_ha_una_definizione_sola(d):
    """`_fit_log_poisson` aggiunge l'intercetta, non una seconda pendenza."""
    v = d[d["validabile"]]
    y = v["y_totale"].to_numpy(dtype=float)
    lam = v["lam_totale"].to_numpy()
    _a, b = TT._fit_log_poisson(y, lam)
    assert np.isclose(b, V.calibration_slope(y, lam)[0], atol=1e-10)


def test_il_verdetto_applica_il_criterio_meccanicamente(d):
    """`adottata` deve essere la congiunzione dei tre criteri, non un giudizio."""
    ver = TT.verdetto(d)
    atteso = (ver["criterio_1_pendenza"] and ver["criterio_2_mae"]
              and ver["criterio_3_segno"])
    assert ver["adottata"] is atteso
    assert TT.CRITERIO_ADOZIONE in ver["criterio"]


def test_il_verdetto_e_diviso_fra_i_due_bersagli():
    """Non e' stato aggiustato per farlo tornare uguale, ed e' il risultato.

    Sui tiri la correzione si adotta, sui tiri in porta no: cade il criterio (1)
    perche' la pendenza resta fuori da due errori standard.
    """
    assert TT.verdetto(target=TT.TARGET)["adottata"] is True
    so = TT.verdetto(target=TT.TARGET_PRECISIONE)
    assert so["adottata"] is False
    assert so["criterio_1_pendenza"] is False
    assert so["criterio_2_mae"] and so["criterio_3_segno"]


def test_il_modello_anticorrela_i_due_lati_piu_del_vero(d):
    """E' la diagnosi della sotto-calibrazione, e regge in tutte le stagioni."""
    for target in (TT.TARGET, TT.TARGET_PRECISIONE):
        a = TT.anticorrelazione(None if target != TT.TARGET else d, target=target)
        assert a["il_modello_anticorrela_di_piu"].all(), a


# --------------------------------------------------------------------------
# 5. Vincolo 3 - nessuna quota, nessuna scommessa
# --------------------------------------------------------------------------
VIETATE = ("odds", "quota_decimale", "payout", "bankroll", "kelly", "stake",
           "profitto", "roi", "edge_scommessa", "scommessa")


def _vietate_nel(testo: str) -> list[str]:
    return [v for v in VIETATE
            if re.search(rf"(?<![a-zA-Z]){re.escape(v)}(?![a-zA-Z])", testo)]


def test_il_modulo_del_totale_non_parla_di_scommesse():
    assert _vietate_nel(_codice(MODULO)) == []


def test_il_report_non_propone_scommesse():
    md = config.REPORTS / "fase15_totale.md"
    if not md.is_file():
        pytest.skip("manca il report: esegui run_fase15_totale.py")
    trovate = set(_vietate_nel(md.read_text(encoding="utf-8"))) - {"scommessa"}
    assert trovate == set()


def test_la_guardia_del_vincolo_3_sa_dire_anche_di_si():
    """Senza, 'nessuna parola vietata' e 'la guardia non guarda' coinciderebbero."""
    assert "bankroll" in _vietate_nel("calcola_bankroll = 1")
    assert _vietate_nel("proiezione") == []      # `roi` dentro `proiezione`
    assert _vietate_nel("mistakes") == []        # `stake` dentro `mistakes`


def test_la_quota_di_pareggio_viene_da_soglie_2627():
    """Una definizione in un posto solo: mai riscrivere `1.0/p`."""
    src = MODULO.read_text(encoding="utf-8")
    assert "soglie_2627 as S" in src
    assert "S.quota_pareggio(" in src
    assert "1.0 / p_over" not in src
    assert "1.0/p_over" not in src


# --------------------------------------------------------------------------
# 6. Trasferisce? Le tre firme sui cinque campionati
# --------------------------------------------------------------------------
def test_le_tre_firme_reggono_su_tutti_i_campionati():
    """Un risultato che valesse solo in Serie A sarebbe un'idiosincrasia.

    E' la domanda della Fase 13 sui gol, applicata a questo blocco. Un fit per
    campionato, **mai poolati**: la tabella ha una riga per (campionato,
    bersaglio) e nessuna riga mescola due campionati.
    """
    t = TT.per_campionato(n_boot=50)
    assert len(t) == 2 * len(config.LEAGUE_CODES)
    assert (t["corr_lati"] < 0).all(), t[t["corr_lati"] >= 0]
    assert (t["rapporto_r"] > 1).all(), t[t["rapporto_r"] <= 1]
    assert (t["pendenza_totale"] < 1).all(), t[t["pendenza_totale"] >= 1]


def test_r_tot_non_si_prende_in_prestito_da_un_altro_campionato():
    """Fra Bundesliga e Liga sui tiri in porta il fattore e' 2,7."""
    t = TT.per_campionato(n_boot=50)
    so = t[t["bersaglio"] == "tiri in porta"].set_index("campionato")["r_totale"]
    assert so.max() / so.min() > 2.0, so
