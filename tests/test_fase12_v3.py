# -*- coding: utf-8 -*-
"""Fase 12 / Blocco V3 — i predittori da dati evento, ritestati sui tentativi.

V3 non ha un modulo proprio: **parametrizza `sot/predictor_power.py`** su
`target`, ed e' un'eccezione dichiarata alla regola «1 blocco = 1 modulo».
Duplicare quel modulo violerebbe «una definizione in un posto solo», che e' la
ragione per cui `shots.py` e `perimetro.py` esistono.

Il gruppo di test piu' importante e' quello che protegge la **Fase 6D**: la
parametrizzazione tocca codice su cui poggia un report gia' pubblicato, e la
condizione di accettazione e' l'identita' **bit per bit** con il default.

Il secondo blocca il difetto vero della parametrizzazione: `_fit` costruiva
`TeamModel` **senza** `target`, quindi il parametro sarebbe sembrato funzionare
(`y_in` era gia' del bersaglio giusto) mentre il modello veniva stimato su `sot`.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from sot import (baselines as bl, config, predictor_power as PP,
                 tentativi as T, volume as VL, walkforward as wf)


@pytest.fixture(scope="module")
def prev_6d():
    """Le previsioni della Fase 6D, gia' in cache: il riferimento da non muovere."""
    p = config.PROCESSED / "phase6d_predittori.parquet"
    if not p.is_file():
        pytest.skip("manca phase6d_predittori.parquet: esegui run_phase6d.py")
    return pd.read_parquet(p)


# --------------------------------------------------------------------------
# 1. Il default non si muove — la Fase 6D e' pubblicata
# --------------------------------------------------------------------------
def test_il_default_e_identico_al_target_esplicito(prev_6d):
    """`confronto(prev, r)` e `confronto(prev, r, target="sot")` devono dare la
    stessa tabella, colonna per colonna e bit per bit."""
    for regime in PP.REGIMI:
        a = PP.confronto(prev_6d, regime)
        b = PP.confronto(prev_6d, regime, target="sot")
        pd.testing.assert_frame_equal(a, b, check_exact=True)


def test_i_numeri_della_fase_6d_si_riproducono(prev_6d):
    """Il report e il codice non devono poter divergere senza che nessuno se ne
    accorga. `poss_att` nel maturo vale t = 1.4200797158768528, ed e' il numero
    che CLAUDE.md cita come 1,42."""
    pub = pd.read_csv(config.REPORTS / "phase6_predittori.csv")
    for regime in pub["regime"].unique():
        atteso = pub[pub["regime"] == regime].set_index("predittore")
        got = PP.confronto(prev_6d, regime).set_index("predittore")
        for col in ("d_riga", "se_riga", "t", "mde_riga"):
            if col in atteso.columns:
                assert np.abs(got[col] - atteso[col]).max() < 1e-12, f"{regime}/{col}"

    t = PP.confronto(prev_6d, "maturo").set_index("predittore").loc["poss_att", "t"]
    assert t == pytest.approx(1.4200797158768528, abs=1e-12)


def test_le_costanti_dichiarate_non_sono_cambiate():
    """`T_KEEP` ritoccata dopo aver visto i `t` del bersaglio nuovo sarebbe
    esattamente l'errore che la 6D esiste per non commettere."""
    assert PP.T_KEEP == 2.0
    assert PP.FAMIGLIA == 8 == len(wf.CANDIDATES)
    assert PP.POTENZA_OBIETTIVO == 0.80
    assert PP.ALPHA_INS == 12.0
    assert PP.REGIMI["maturo"] == (config.BURN_IN_ROUND, 38)
    assert PP.REGIMI["acerbo"] == (1, 8)
    assert PP.REGIMI["acerbo disgiunto"] == (1, 5)


def test_i_default_dei_target_restano_sot():
    """La garanzia strutturale: cambiare il default qui muoverebbe undici fasi."""
    import inspect

    from sot import model_team as MT

    assert bl.TARGET == "sot"
    assert MT.TeamModel().target == "sot"
    for f in (PP.previsioni, PP.confronto, PP.penalita, PP.contesto):
        assert inspect.signature(f).parameters["target"].default == "sot"


# --------------------------------------------------------------------------
# 2. Il difetto vero: il fit deve usare il target
# --------------------------------------------------------------------------
def _finto() -> pd.DataFrame:
    """Un campione sintetico con `shots` e `sot` deliberatamente diversi.

    Porta anche le sette colonne sorgente da cui `build_predictors` ricava gli
    otto candidati: senza, il fallimento sarebbe un `KeyError` sulle colonne e
    non direbbe niente sul bersaglio, che e' cio' che questi test verificano.
    """
    rng = np.random.default_rng(config.SEED)
    squadre = [f"T{i}" for i in range(8)]
    sorgenti = sorted({c for c, _ in wf.CANDIDATES.values()})
    righe = []
    for g in range(24):
        for i, t in enumerate(squadre):
            o = squadre[(i + g + 1) % len(squadre)]
            n = int(rng.poisson(12) + 1)
            r = {
                "matchId": g * 100 + i, "team": t, "opponent": o,
                "is_home": g % 2, "team_match_idx": g + 1,
                "date": pd.Timestamp("2024-01-01") + pd.Timedelta(days=3 * g),
                "shots": n, "sot": int(rng.binomial(n, 0.33)),
            }
            r.update({c: float(rng.normal(0.5, 0.1)) for c in sorgenti})
            righe.append(r)
    return pd.DataFrame(righe)


def test_il_fit_in_campione_usa_il_target():
    """**Il difetto che questa parametrizzazione poteva introdurre.** `_fit`
    costruiva `TeamModel` senza `target`: `y_in` era gia' del bersaglio giusto,
    quindi il parametro sarebbe sembrato funzionare mentre il modello veniva
    stimato su `sot`. Se la verosimiglianza non cambiasse al cambiare del
    target, il fit lo starebbe ignorando."""
    d = _finto()
    a = PP.penalita(d, target="shots")
    b = PP.penalita(d, target="sot")
    assert a["loglik"] != b["loglik"]
    assert a["obiettivo"] != b["obiettivo"]


def test_penalita_su_shots_e_coerente_col_bersaglio():
    """Controllo di sanita': la verosimiglianza Poisson su un conteggio con media
    12,6 non puo' coincidere con quella di un conteggio con media 4,2."""
    d = _finto()
    a = PP.penalita(d, target="shots")["loglik"]
    b = PP.penalita(d, target="sot")["loglik"]
    assert a < b        # piu' massa, verosimiglianza per riga piu' bassa


def test_la_colonna_esce_col_proprio_nome():
    """Due tabelle con bersagli diversi non devono poter essere confuse a valle."""
    d = wf.build_predictors(_finto())
    p = PP.previsioni(d, candidati=("poss_att",), verbose=False, target="shots")
    assert "shots" in p.columns
    assert "sot" not in p.columns


def test_target_assente_solleva():
    """Un `NaN` silenzioso sarebbe il modo peggiore di sbagliare bersaglio."""
    d = wf.build_predictors(_finto())
    with pytest.raises((KeyError, ValueError)):
        PP.previsioni(d, candidati=("poss_att",), verbose=False, target="pippo")


# --------------------------------------------------------------------------
# 3. I predittori si costruiscono PER STAGIONE
# --------------------------------------------------------------------------
def test_i_predittori_sono_costruiti_per_stagione():
    """Sul concatenato `pre_match_ewm` raggruppa per `team`, che e' un nome e si
    ripete fra stagioni: settembre 2023 riceverebbe una media dominata da maggio
    2023 (peso 0,57 a 110 giorni), cioe' da una rosa che non esiste piu'.

    La firma e' la **prima partita di ogni stagione**: deve avere predittori
    nulli. Sul concatenato non lo sarebbero."""
    d = VL.predittori_per_stagione()
    prime = d[d["team_match_idx"] == 1]
    assert len(prime) >= 90
    for nome in wf.CANDIDATES:
        assert prime[nome].isna().all(), f"{nome} non e' nullo alla prima giornata"


def test_ogni_stagione_ha_le_sue_venti_squadre():
    d = VL.predittori_per_stagione()
    per_st = d.groupby("stagione")["team"].nunique()
    assert (per_st == 20).all()


def test_la_tabella_dei_predittori_copre_tutto_l_universo():
    """Se `build_predictors` perdesse righe, il regime acerbo — che vive sulle
    prime giornate — sarebbe il primo a soffrirne."""
    d = VL.predittori_per_stagione()
    assert len(d) == len(T.universo())


# --------------------------------------------------------------------------
# 4. Il confronto sul nuovo bersaglio
# --------------------------------------------------------------------------
@pytest.fixture(scope="module")
def prev_v3():
    if not VL.CACHE_PRED.is_file():
        pytest.skip("manca fase12_v3_predittori.parquet: esegui run_fase12_v3.py")
    return pd.read_parquet(VL.CACHE_PRED)


def test_le_previsioni_sono_le_stesse_in_tutti_i_regimi(prev_v3):
    """Le previsioni si calcolano una volta sola e i regimi si applicano dopo:
    ricalcolarle per regime renderebbe i tre esiti non confrontabili."""
    a = prev_v3[PP.maschera(prev_v3, "acerbo")]
    b = prev_v3[PP.maschera(prev_v3, "acerbo disgiunto")]
    comuni = set(zip(a["matchId"], a["team"])) & set(zip(b["matchId"], b["team"]))
    assert len(comuni) > 100
    ia = a.set_index(["matchId", "team"]).loc[list(comuni), f"lam_{PP.BASE}"]
    ib = b.set_index(["matchId", "team"]).loc[list(comuni), f"lam_{PP.BASE}"]
    assert np.allclose(ia.sort_index(), ib.sort_index())


def test_il_bersaglio_delle_previsioni_e_shots(prev_v3):
    assert T.TARGET in prev_v3.columns
    assert prev_v3[T.TARGET].mean() > 10.0     # tentativi, non tiri in porta


def test_ogni_riga_negativa_ha_il_suo_mde(prev_v3):
    """La lezione della 6D, meccanizzata: un `t` sotto soglia pubblicato senza
    MDE non e' leggibile — non dimostra che l'effetto sia zero."""
    c = VL.confronto_predittori(prev_v3)
    assert c["mde_riga"].notna().all()
    assert (c.loc[~c["tenuto"], "mde_riga"] > 0).all()


def test_il_regime_acerbo_disgiunto_ha_piu_righe_che_nella_6d(prev_v3):
    """Il guadagno vero del perimetro multi-stagione: il regime piu' debole
    della 6D aveva 40 righe, qui ne ha ~200, e il MDE si divide per ~2,2."""
    n = int(PP.maschera(prev_v3, "acerbo disgiunto").sum())
    assert n > 150


def test_la_famiglia_resta_otto(prev_v3):
    """Nessun candidato aggiunto strada facendo: la correzione per molteplicita'
    e' calcolata su k = 8, e cambiarla dopo aver visto i `t` sarebbe adattarsi."""
    c = VL.confronto_predittori(prev_v3)
    assert c["predittore"].nunique() == 8
