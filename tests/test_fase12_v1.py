# -*- coding: utf-8 -*-
"""Fase 12 / Blocco V1 — lo strato del volume.

Due gruppi contano piu' degli altri:

* i test di **leakage** sul walk-forward multi-stagione, che e' la novita' vera
  di questa fase — cinque walk-forward invece di uno, e la separazione fra
  stagioni non e' garantita da niente se non dal codice che la fa;
* il test che `paired_t` con `cluster=None` sia **identico bit per bit** a
  prima, perche' quella funzione e' usata da tutte le fasi pubblicate.
"""
from __future__ import annotations

import io
import tokenize
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from sot import config, tentativi as T, validate as V, volume as VL


def _codice(path) -> str:
    """Sorgente senza commenti e senza stringhe (vedi `test_fase12_v0`)."""
    src = path.read_text(encoding="utf-8")
    return " ".join(t.string for t in tokenize.generate_tokens(io.StringIO(src).readline)
                    if t.type not in (tokenize.COMMENT, tokenize.STRING))


@pytest.fixture(scope="module")
def wf():
    return VL.walkforward_tiri()


@pytest.fixture(scope="module")
def val(wf):
    return VL.valutazione(wf)


# --------------------------------------------------------------------------
# 1. `paired_t` esteso — l'identita' che protegge undici fasi
# --------------------------------------------------------------------------
def test_paired_t_senza_cluster_e_identico_a_prima():
    """`cluster=None` deve dare esattamente cio' che dava prima dell'estensione.
    Tutto cio' che le Fasi 1-11 hanno pubblicato passa di qui."""
    rng = np.random.default_rng(config.SEED)
    a, b = rng.normal(size=500), rng.normal(size=500)
    d = a - b
    se = d.std(ddof=1) / np.sqrt(len(d))
    somma, t = V.paired_t(a, b)
    assert somma == pytest.approx(float(d.sum()), abs=1e-12)
    assert t == pytest.approx(float(d.mean() / se), abs=1e-12)


def test_paired_t_con_cluster_degenere_e_come_senza():
    """Un cluster per riga non raggruppa niente: deve tornare il caso base."""
    rng = np.random.default_rng(config.SEED)
    a, b = rng.normal(size=200), rng.normal(size=200)
    assert V.paired_t(a, b)[1] == pytest.approx(
        V.paired_t(a, b, cluster=np.arange(200))[1], abs=1e-12)


def test_paired_t_con_cluster_riduce_le_unita():
    """Con due righe per cluster il `t` si calcola su n/2 medie, non su n."""
    rng = np.random.default_rng(config.SEED)
    a, b = rng.normal(size=200), rng.normal(size=200)
    clu = np.repeat(np.arange(100), 2)
    _s, t = V.paired_t(a, b, cluster=clu)
    d = pd.Series(a - b).groupby(clu).mean().to_numpy()
    assert t == pytest.approx(d.mean() / (d.std(ddof=1) / np.sqrt(100)), abs=1e-12)


def test_paired_t_la_somma_non_dipende_dal_cluster():
    """La somma e' della differenza grezza: raggrupparla sarebbe un'altra cosa."""
    rng = np.random.default_rng(config.SEED)
    a, b = rng.normal(size=100), rng.normal(size=100)
    clu = np.repeat(np.arange(50), 2)
    assert V.paired_t(a, b)[0] == pytest.approx(V.paired_t(a, b, cluster=clu)[0],
                                                abs=1e-12)


def test_paired_t_cluster_di_lunghezza_sbagliata_solleva():
    with pytest.raises(ValueError, match="cluster ha"):
        V.paired_t(np.zeros(10), np.zeros(10), cluster=np.arange(5))


# --------------------------------------------------------------------------
# 2. Leakage — cinque walk-forward invece di uno
# --------------------------------------------------------------------------
def test_il_walkforward_e_dentro_la_stagione(wf):
    """Ogni riga appartiene a una stagione sola, e la colonna la dichiara.

    Se il walk-forward attraversasse l'estate, un decadimento di 150 giorni
    darebbe alla prima giornata di settembre un training fatto di maggio, cioe'
    di una squadra che non esiste piu'."""
    u = T.universo()
    vera = u.set_index("matchId")["stagione"].to_dict()
    assert (wf["matchId"].map(vera) == wf["stagione"]).all()


def test_ogni_stagione_perde_le_stesse_giornate(wf):
    """60 righe senza previsione e 40 perse per burn-in, in ogni stagione: sono
    3 e 2 giornate da 20 squadre. Se una stagione ne perdesse di piu', il
    perimetro non sarebbe confrontabile fra stagioni."""
    cop = VL.copertura(wf)
    per_st = cop[cop["stagione"] != "TOTALE"]
    assert (per_st["senza_previsione"] == 60).all()
    assert (per_st["perse_burnin"] == 40).all()


def test_il_perimetro_coincide_con_quello_dei_gol(wf):
    """Due bersagli diversi sullo stesso universo devono dare lo stesso
    perimetro: e' un controllo di coerenza fra E3 e V1."""
    assert len(wf) == 3478
    assert int(wf["eligible"].sum()) == 3278


def test_eligible_equivale_al_burn_in(wf):
    """La stessa relazione che R0 ha verificato e reso falsificabile."""
    atteso = wf["team_match_idx"] >= config.BURN_IN_ROUND
    assert (wf["eligible"] == atteso).all()


def test_la_colonna_del_bersaglio_esce_col_proprio_nome(wf):
    """`walkforward_predict` non deve rinominare il bersaglio in `sot`: qui
    convivono `shots` (bersaglio) e `sot` (bersaglio di V2), e confonderli
    sarebbe silenzioso."""
    assert T.TARGET in wf.columns
    assert T.TARGET_PRECISIONE in wf.columns
    assert not wf[T.TARGET].equals(wf[T.TARGET_PRECISIONE])


def test_lam_subiti_e_il_lambda_dell_avversario(wf):
    """Verifica falsificabile: si prende una partita e si controlla che il
    `lam_subiti` di un lato sia il `lam` dell'altro."""
    k = wf.set_index(["matchId", "team"])["lam"]
    campione = wf.dropna(subset=["lam_subiti"]).head(200)
    atteso = [k.get((mi, o), np.nan) for mi, o
              in zip(campione["matchId"], campione["opponent"])]
    assert np.allclose(campione["lam_subiti"], atteso, equal_nan=True)


# --------------------------------------------------------------------------
# 3. I numeri pubblicati
# --------------------------------------------------------------------------
def test_il_modello_batte_il_baseline_migliore(wf):
    """**Il risultato del blocco**, e va bloccato perche' e' il contrario di cio'
    che accade sui tiri in porta (t = 1,86, dentro il rumore). Se un domani
    scendesse sotto 3, qualcosa e' cambiato nella catena e va capito."""
    app = VL.confronto_appaiato(wf).set_index("baseline")
    r = app.loc[V.BEST_BASELINE]
    assert r["delta_mae"] > 0
    assert r["t_per_cluster"] > 5.0


def test_il_modello_e_calibrato_e_i_baseline_no(val):
    """L'argomento della Fase 4, ripetuto piu' netto: il modello e' l'unico
    candidato informativo compatibile con 1.0."""
    v = val.set_index("modello")
    assert abs(v.loc[V.MODEL_NAME, "calib_z_vs_1"]) < 2.0
    for b in ("media squadra + campo", "media squadra"):
        assert v.loc[b, "calib_slope"] < 1.0
        assert v.loc[b, "calib_z_vs_1"] < -5.0


def test_media_campionato_non_e_identificata(val):
    """Stessa ragione della Fase 4: `lambda` quasi costante, errore standard
    enorme. Non e' un difetto, e' una grandezza non stimabile."""
    v = val.set_index("modello")
    assert v.loc["media campionato", "calib_se"] > 0.15


def test_vince_in_tutte_le_stagioni(wf):
    """Cinque segni concordi sono un'evidenza diversa da un `t` pooled dello
    stesso valore, e la seconda non si legge dalla prima."""
    st = VL.per_stagione(wf)
    assert len(st) == 5
    assert st["vince"].all()
    assert (st["t_per_cluster"] > 2.0).all()


def test_il_mae_relativo_e_stabile_fra_stagioni(wf):
    """Il MAE assoluto non e' confrontabile (il livello si muove del 5,5%); il
    relativo si', e dice che la difficolta' del problema non cambia."""
    st = VL.per_stagione(wf)
    assert st["mae_relativo"].max() - st["mae_relativo"].min() < 0.05


def test_r_non_e_sospetto(wf):
    """`r < 10` non e' un risultato: e' il sintomo di un errore di
    specificazione, e `dispersion` lo dichiara."""
    from sot import dispersion as D

    d = VL.dispersione_tiri(wf)
    assert not d["suspicious"]
    assert d["nb2_r"] > D.R_SUSPICIOUS


def test_condizionare_a_lambda_riduce_la_dispersione(wf):
    """Parte dell'eccesso grezzo e' variazione di lambda che il modello spiega:
    se condizionare NON riducesse, il modello non spiegherebbe niente."""
    d = VL.dispersione_tiri(wf)
    assert d["pearson_dispersion"] < d["raw_var_mean_ratio"]


def test_la_forma_predittiva_regge(wf):
    """Il PIT e' il controllo che la pendenza di calibrazione non fa."""
    f = VL.forma_predittiva(wf)
    assert f["pit"]["p_value"] > 0.05


def test_la_copertura_e_conservativa(wf):
    """Strutturale sui conteggi, e gia' osservata in Fase 4: la discretezza
    impedisce di centrare il nominale."""
    c = VL.forma_predittiva(wf)["copertura"].set_index("livello")
    for liv in (0.5, 0.8, 0.95):
        assert c.loc[liv, "copertura"] >= liv


def test_vince_su_tutte_le_linee(wf):
    """Una linea sola sarebbe un risultato scelto (lezione della Fase 4)."""
    b = VL.brier_per_linea(wf)
    assert len(b) == len(T.LINEE_TIRI)
    assert b["vince_su_baseline"].all()
    assert b["vince_su_tasso_base"].all()


# --------------------------------------------------------------------------
# 4. Il terzile alto — la firma dello shrinkage, che non va corretta
# --------------------------------------------------------------------------
def test_il_margine_si_attenua_nel_terzile_alto(wf):
    """Sui tiri in porta la Fase 4 trovava che il modello PERDE nel terzile alto,
    ed era lo shrinkage: le squadre che tirano molto sono quelle che il ritorno
    alla media penalizza. Sui tentativi la firma c'e' — il margine si attenua —
    ma non si inverte.

    **Il test blocca l'attenuazione, non la vittoria**: se un domani sparisse,
    vorrebbe dire che qualcuno ha tolto lo shrinkage, che e' la strada che il
    progetto ha gia' rifiutato quattro volte."""
    seg = VL.segmenti(wf)
    t = seg[seg["segmento"] == "terzile lambda"].set_index("valore")
    assert t.loc["alto", "delta"] < t.loc["basso", "delta"]
    assert t.loc["alto", "delta"] > 0      # attenuato, non invertito


def test_il_mae_cresce_col_lambda(wf):
    """Atteso su conteggi: la varianza cresce con la media. Se non crescesse,
    ci sarebbe da controllare la specificazione."""
    seg = VL.segmenti(wf)
    t = seg[seg["segmento"] == "terzile lambda"].set_index("valore")
    assert t.loc["basso", "mae_modello"] < t.loc["alto", "mae_modello"]


# --------------------------------------------------------------------------
# 5. Le costanti, e cio' che V1 non fa
# --------------------------------------------------------------------------
def test_le_soglie_vengono_da_v0_e_non_sono_ridichiarate():
    """Una definizione in un posto solo: se V1 ridichiarasse le linee, le due
    copie potrebbero divergere senza che nessuno se ne accorga."""
    assert VL.LINEA is T.LINEA_PRINCIPALE
    assert VL.TARGET is T.TARGET
    src = _codice(config.ROOT / "sot" / "volume.py")
    for vietato in ("argmax", "idxmax"):
        assert vietato not in src


def test_v1_non_tocca_le_linee_dei_tiri_in_porta():
    assert V.LINES == (2.5, 3.5, 4.5, 5.5)


def test_i_baseline_sono_i_quattro_dichiarati():
    from sot import baselines as bl

    assert set(VL.BASELINE) == set(bl.BASELINES)


def test_v1_scrive_solo_cache_dichiarate_sotto_processed():
    """Il vincolo 9: il modello non scrive mai sotto `raw/`, e ogni scrittura di
    questo modulo e' una cache **rigenerabile** sotto `processed/`.

    Le cache sono **due** e non una, perche' V3 non ha un modulo proprio: `CACHE`
    e' il walk-forward del volume (V1), `CACHE_PRED` i nove walk-forward dei
    predittori (V3). La prima versione di questa guardia contava un letterale
    `1` ed e' diventata rossa quando V3 e' arrivato — cioe' segnalava un fatto
    innocuo e non il fatto che deve sorvegliare.

    Il conteggio e' ora legato alle costanti **dichiarate**: aggiungere una cache
    senza dichiararla, o dichiararne una fuori da `processed/`, fa fallire la
    guardia; aggiungerne una dichiarata e al posto giusto no.
    """
    cache = {k: v for k, v in vars(VL).items()
             if k.startswith("CACHE") and isinstance(v, Path)}
    assert set(cache) == {"CACHE", "CACHE_PRED"}

    proc = config.processed_league_dir().resolve()
    for nome, c in cache.items():
        assert c.resolve().parent == proc, f"{nome} non sta sotto processed/"
        assert c.suffix == ".parquet"

    src = _codice(config.ROOT / "sot" / "volume.py")
    assert src.count("to_parquet") == len(cache)
    assert "RAW" not in src
