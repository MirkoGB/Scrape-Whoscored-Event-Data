# -*- coding: utf-8 -*-
"""Fase 10 / Blocco R1 — test della congiunta e della precondizione.

Due gruppi. Il primo verifica le proprieta' della congiunta su casi in cui la
risposta e' nota **per costruzione** — che e' l'unico modo di validare uno
strumento senza usarlo sui propri risultati, la regola che `tests/test_validate.py`
segue dalla Fase 4. Il secondo protegge i numeri pubblicati.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from scipy import stats

from sot import config, perimetro as PM, risultato as R


@pytest.fixture(scope="module")
def d() -> pd.DataFrame:
    p = PM.partite()
    return p[p["validabile"]].copy()


@pytest.fixture(scope="module")
def cas() -> pd.DataFrame:
    """Calcolata una volta per il modulo: e' una permutazione su 200.000
    repliche, e quattro test la vogliono. Ricalcolarla ogni volta era il 90%
    del tempo di questo file."""
    return PM.casualita_mancanti()


# ---------------------------------------------------------------------------
# La congiunta, su casi in cui la risposta e' nota
# ---------------------------------------------------------------------------

def test_a_rho_zero_e_il_prodotto_delle_marginali():
    """`rho = 0` deve dare esattamente il prodotto esterno delle due Poisson."""
    lam_c, lam_t = 1.7, 1.1
    g = np.arange(R.MAX_GOL + 1)
    atteso = np.outer(stats.poisson.pmf(g, lam_c), stats.poisson.pmf(g, lam_t))
    assert np.allclose(R.congiunta(lam_c, lam_t, 0.0), atteso)


def test_le_marginali_si_conservano_a_rho_qualsiasi():
    """La verifica falsificabile del blocco, su una griglia di rho e lambda.

    Non basta provarla al valore del report: la proprieta' e' algebrica e deve
    valere ovunque, altrimenti e' una coincidenza numerica.
    """
    g = np.arange(R.MAX_GOL + 1)
    for lam_c in (0.6, 1.4, 2.8):
        for lam_t in (0.5, 1.2, 2.2):
            mc = stats.poisson.pmf(g, lam_c)
            mt = stats.poisson.pmf(g, lam_t)
            for rho in (-0.15, -0.05, 0.0, 0.05, 0.15):
                p = R.congiunta(lam_c, lam_t, rho)
                assert np.allclose(p.sum(axis=1), mc, atol=1e-12)
                assert np.allclose(p.sum(axis=0), mt, atol=1e-12)


def test_tau_tocca_solo_quattro_celle():
    """Fuori dall'angolo `tau` vale 1: se toccasse altro non sarebbe Dixon-Coles."""
    p0 = R.congiunta(1.5, 1.2, 0.0)
    p1 = R.congiunta(1.5, 1.2, 0.12)
    diverse = {(int(i), int(j)) for i, j in zip(*np.nonzero(~np.isclose(p0, p1)))}
    assert diverse == set(R.CELLE_CORRETTE)


def test_rho_positivo_sposta_massa_come_dichiarato():
    """Segni attesi: 0-0 e 1-1 giu', 0-1 e 1-0 su. E' l'ipotesi, non un dettaglio."""
    p0 = R.congiunta(1.5, 1.2, 0.0)
    p1 = R.congiunta(1.5, 1.2, 0.10)
    assert p1[0, 0] < p0[0, 0]
    assert p1[1, 1] < p0[1, 1]
    assert p1[0, 1] > p0[0, 1]
    assert p1[1, 0] > p0[1, 0]


def test_esiti_sommano_a_uno():
    for lam_c, lam_t in ((1.6, 1.1), (0.7, 2.4), (2.0, 2.0)):
        assert abs(sum(R.esiti(R.congiunta(lam_c, lam_t, 0.05))) - 1.0) < 1e-9


def test_lambda_uguali_danno_1_e_2_simmetrici():
    """Con marginali uguali `P(1)` e `P(2)` devono coincidere. Caso noto."""
    p1, px, p2 = R.esiti(R.congiunta(1.4, 1.4, 0.0))
    assert abs(p1 - p2) < 1e-12


def test_massa_troncata_trascurabile(d):
    """Il troncamento e' misurato sui lambda VERI, non su una coppia comoda.

    La soglia e' 1e-4 e non 1e-8 perche' la massa cresce ripidamente col lambda:
    a 1.6/1.2 sta sotto la precisione di stampa, a 3.2 no. 1e-4 e' due ordini di
    grandezza sotto l'ultima cifra che il report stampa (4 decimali), quindi non
    puo' spostare nessun numero pubblicato.
    """
    m = R.massa_troncata_dati(d)
    assert m["max"] < 1e-4
    assert m["media"] < 1e-5
    # E cresce col lambda: se non lo facesse, la funzione non starebbe misurando
    # quello che dice.
    assert R.massa_troncata(3.0, 3.0) > R.massa_troncata(1.0, 1.0)


def test_over_e_monotono_nella_linea():
    p = R.congiunta(1.6, 1.3, 0.0)
    v = [R.over(p, s) for s in (0.5, 1.5, 2.5, 3.5, 4.5)]
    assert all(a > b for a, b in zip(v, v[1:]))


# ---------------------------------------------------------------------------
# La stima di rho, su dati generati con rho NOTO
# ---------------------------------------------------------------------------

def test_stima_rho_recupera_un_rho_iniettato():
    """Generando da `rho = 0.15`, la stima deve tornarci vicino.

    Senza questo, un `rho` stimato a zero sui dati veri sarebbe indistinguibile
    da uno stimatore che ritorna sempre zero.
    """
    rng = np.random.default_rng(config.SEED)
    n, vero = 4000, 0.15
    lam_c = rng.uniform(0.8, 2.2, n)
    lam_t = rng.uniform(0.6, 1.9, n)
    lato = R.MAX_GOL + 1
    gc = np.empty(n, dtype=int)
    gt = np.empty(n, dtype=int)
    for i in range(n):
        q = np.clip(R.congiunta(lam_c[i], lam_t[i], vero), 0, None).ravel()
        k = rng.choice(q.size, p=q / q.sum())
        gc[i], gt[i] = divmod(k, lato)
    out = R.stima_rho(pd.DataFrame({"lam_casa": lam_c, "lam_trasferta": lam_t,
                                    "gol_casa": gc, "gol_trasferta": gt}))
    assert abs(out["rho"] - vero) < 0.05
    assert out["p_lr"] < 0.01


def test_stima_rho_non_rifiuta_sotto_indipendenza():
    """Generando da `rho = 0`, il test non deve rifiutare. Il verso opposto."""
    rng = np.random.default_rng(config.SEED + 1)
    n = 3000
    lam_c = rng.uniform(0.8, 2.2, n)
    lam_t = rng.uniform(0.6, 1.9, n)
    out = R.stima_rho(pd.DataFrame({
        "lam_casa": lam_c, "lam_trasferta": lam_t,
        "gol_casa": rng.poisson(lam_c), "gol_trasferta": rng.poisson(lam_t)}))
    assert out["p_lr"] > 0.05
    assert abs(out["rho"]) < 0.05


def test_correlazione_residui_vede_una_dipendenza_iniettata():
    """La terza strada deve accorgersi di una dipendenza costruita a mano."""
    rng = np.random.default_rng(config.SEED)
    n = 3000
    base = rng.poisson(1.4, n)
    d = pd.DataFrame({"lam_casa": 1.4, "lam_trasferta": 1.4,
                      "gol_casa": base, "gol_trasferta": base})
    assert R.correlazione_residui(d)["corr"] > 0.9
    indip = pd.DataFrame({"lam_casa": 1.4, "lam_trasferta": 1.4,
                          "gol_casa": rng.poisson(1.4, n),
                          "gol_trasferta": rng.poisson(1.4, n)})
    assert abs(R.correlazione_residui(indip)["corr"]) < 0.06


# ---------------------------------------------------------------------------
# I numeri pubblicati
# ---------------------------------------------------------------------------

def test_rho_pubblicato(d):
    """rho ~ -0.009, LR ~ 0.08, p ~ 0.78 sulle 1.638 partite."""
    out = R.stima_rho(d)
    assert out["n"] == 1638
    assert abs(out["rho"] - (-0.00874)) < 1e-3
    assert out["p_lr"] > 0.7
    assert not out["sul_bordo"]


def test_nessuna_delle_tre_strade_trova_dipendenza(d):
    assert R.stima_rho(d)["p_lr"] > 0.05
    assert R.correlazione_residui(d)["p"] > 0.05
    c = R.celle_osservate(d)
    angolo = c[c["cella"] == "**angolo**"].iloc[0]
    assert abs(angolo["rapporto"] - 1.0) < 0.01


def test_lo_scostamento_non_ha_la_forma_di_dixon_coles(d):
    """0-0 sotto e 1-1 sopra: due versi che un `rho` solo non puo' produrre.

    E' il risultato di §4 del report, ed e' il motivo per cui l'MLE cade a zero.
    """
    lam_c = d["lam_casa"].to_numpy(); lam_t = d["lam_trasferta"].to_numpy()
    gc = d["gol_casa"].to_numpy(); gt = d["gol_trasferta"].to_numpy()

    def z(x, y):
        pi = stats.poisson.pmf(x, lam_c) * stats.poisson.pmf(y, lam_t)
        return (((gc == x) & (gt == y)).sum() - pi.sum()) / np.sqrt((pi * (1 - pi)).sum())

    # Dixon-Coles lega (0,0) e (1,1) allo STESSO verso; qui vanno opposti.
    assert z(0, 0) < 0
    assert z(1, 1) > 0


def test_la_potenza_e_dichiarata_e_non_e_cieca(d):
    """Il campione vede rho = 0.12; e' cio' che rende leggibile il negativo."""
    m = R.mde_rho(d, griglia=[0.12], repliche=40)
    assert float(m["potenza"].iloc[0]) > 0.80


# ---------------------------------------------------------------------------
# La precondizione: le partite mancanti
# ---------------------------------------------------------------------------

def test_dodici_partite_mancanti():
    m = PM.partite_mancanti()
    assert len(m) == 12
    assert m["gol_casa"].notna().all() and m["gol_trasferta"].notna().all()
    assert set(m["stagione"]) == {"2021-2022", "2022-2023"}


def test_atalanta_record_delle_mancanti(cas):
    """V5 P1 S0: e' il fatto su cui poggia tutta la §1."""
    a = cas[cas["squadra"] == "Atalanta"].iloc[0]
    assert a["mancanti"] == 6
    assert a["record"] == "V5P1S0"


def test_il_segnale_e_sui_punti_e_non_sui_gol(cas):
    """La distinzione che decide se R1 puo' procedere.

    Se un giorno il p sui gol scendesse sotto soglia, la conclusione del blocco
    andrebbe riscritta: questo test lo rende visibile invece di silenzioso.
    """
    a = cas[cas["squadra"] == "Atalanta"].iloc[0]
    assert a["punti_p"] < 0.10          # anomalo sui punti
    assert a["gf_p"] > 0.20             # niente sui gol fatti
    assert a["gs_p"] > 0.20             # niente sui gol subiti


def test_non_sopravvive_alla_molteplicita(cas):
    """Il p grezzo non passa Bonferroni sulle squadre testate."""
    a = cas[cas["squadra"] == "Atalanta"].iloc[0]
    assert a["punti_p"] > 0.05 / len(cas)


def test_nessuna_altra_squadra_e_anomala(cas):
    altre = cas[cas["squadra"] != "Atalanta"]
    assert (altre["punti_p"] > 0.05).all()
    assert (altre["gf_p"] > 0.05).all()


def test_il_calendario_dei_voti_e_completo():
    """E' cio' che rende la domanda rispondibile, e va verificato non assunto."""
    cal = pd.read_parquet(PM.CALENDARIO)
    assert len(cal) == 1900
    assert cal["gol_casa"].notna().all()
    assert cal.groupby("stagione")["partita_id"].nunique().eq(380).all()


# ---------------------------------------------------------------------------
# Guardie
# ---------------------------------------------------------------------------

def test_r1_non_ristima_i_lambda():
    """I lambda di E3.1 sono dati. Se R1 li rifittasse, la validazione di E3
    non varrebbe piu' per il modello che R2 userebbe."""
    src = (config.ROOT / "sot" / "risultato.py").read_text(encoding="utf-8")
    for vietato in ("TeamModel", "walkforward_predict", "fit_team", "date_splits"):
        assert vietato not in src, f"R1 non ristima i lambda: trovato {vietato!r}"


def test_nessun_numero_pubblicato_e_cambiato():
    from sot import difesa

    wf = difesa.walkforward_gol()
    assert len(wf) == 3478
    p = PM.partite()
    assert int(p["validabile"].sum()) == 1638
