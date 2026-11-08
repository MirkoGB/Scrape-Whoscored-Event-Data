# -*- coding: utf-8 -*-
"""Fase 12 / Blocco V2 — la precisione, e la composizione.

Il gruppo che conta di piu' e' quello sulla **composizione**: la forma chiusa e
la convoluzione devono coincidere dove entrambe valgono e divergere dove solo
una vale. Sono identita' matematiche, quindi verificabili a precisione macchina
su casi in cui la risposta e' nota — mai sui risultati del progetto.

Il secondo gruppo blocca i **risultati negativi**: lo strato 2 non batte
`p_lega`, la gerarchia non batte il modello diretto, la difesa costa. Sono il
contenuto del blocco e non vanno "sistemati".
"""
from __future__ import annotations

import io
import tokenize

import numpy as np
import pandas as pd
import pytest
from scipy.stats import nbinom

from sot import config, precisione as PR, tentativi as T, validate as V


def _codice(path) -> str:
    src = path.read_text(encoding="utf-8")
    return " ".join(t.string for t in tokenize.generate_tokens(io.StringIO(src).readline)
                    if t.type not in (tokenize.COMMENT, tokenize.STRING))


@pytest.fixture(scope="module")
def wf():
    return PR.walkforward_precisione()


@pytest.fixture(scope="module")
def val(wf):
    return PR._valutabili(wf)


# --------------------------------------------------------------------------
# 1. La composizione — identita' verificabili a precisione macchina
# --------------------------------------------------------------------------
def test_la_forma_chiusa_e_la_nb2_scalata():
    """`S ~ NB2(lam*p, r)`: la premessa della gerarchia, come identita'."""
    lam, p, r = 12.5, 0.33, 20.0
    a = PR.pmf_composta(lam, p, r, rho=0.0)
    b = nbinom.pmf(np.arange(len(a)), r, r / (r + lam * p))
    assert np.allclose(a, b, atol=1e-14)


def test_la_convoluzione_coincide_con_la_chiusa_a_rho_zero():
    """Le due strade devono dare lo stesso numero dove entrambe valgono.
    Se divergessero, una delle due sarebbe sbagliata e non si saprebbe quale."""
    a = PR.pmf_composta(12.5, 0.33, 20.0, rho=0.0)
    c = PR.pmf_composta(12.5, 0.33, 20.0, rho=1e-9)
    assert np.allclose(a, c, atol=1e-6)


def test_con_rho_positivo_la_convoluzione_diverge():
    """Se non divergesse, il ramo `rho > 0` non starebbe facendo niente e la
    sovradispersione residua sarebbe ignorata in silenzio."""
    a = PR.pmf_composta(12.5, 0.33, 20.0, rho=0.0)
    e = PR.pmf_composta(12.5, 0.33, 20.0, rho=0.05)
    assert not np.allclose(a, e, atol=1e-4)


def test_le_pmf_sommano_a_uno():
    """Un `n_max` troncato troppo basso sposterebbe le code senza sollevare."""
    for rho in (0.0, 0.02, 0.05):
        pmf = PR.pmf_composta(12.5, 0.33, 20.0, rho=rho)
        assert pmf.sum() == pytest.approx(1.0, abs=1e-6)


def test_la_composizione_conserva_la_media():
    """`E[S] = lam * p` in entrambe le strade: la sovradispersione cambia la
    forma, non il centro."""
    for rho in (0.0, 0.05):
        pmf = PR.pmf_composta(12.5, 0.33, 20.0, rho=rho)
        media = float((pmf * np.arange(len(pmf))).sum())
        assert media == pytest.approx(12.5 * 0.33, rel=1e-4)


def test_rho_negativo_solleva():
    with pytest.raises(ValueError, match="rho negativo"):
        PR.pmf_composta(12.5, 0.33, 20.0, rho=-0.1)


def test_la_forma_chiusa_vale_anche_con_p_che_cambia_fra_righe():
    """La precisazione a V0: cio' che rompe la forma chiusa NON e' che `p` vari
    fra squadre, ma che vari DENTRO la riga. Con `p` diverso riga per riga
    ciascuna resta una NB2, ed e' il caso di un `p` prodotto da un modello."""
    for p in (0.25, 0.33, 0.45):
        a = PR.pmf_composta(12.0, p, 20.0, rho=0.0)
        b = nbinom.pmf(np.arange(len(a)), 20.0, 20.0 / (20.0 + 12.0 * p))
        assert np.allclose(a, b, atol=1e-14)


# --------------------------------------------------------------------------
# 2. Il modello della precisione
# --------------------------------------------------------------------------
def test_la_ridge_penalizza_solo_attacco_e_difesa():
    """Come in `TeamModel`: senza penalita' i due blocchi non sono
    identificabili separatamente dall'intercetta. `mu_p` e `gamma_p` restano
    liberi."""
    m = PR.ModelloPrecisione(lati=("attacco", "difesa"))
    m.teams_ = [f"T{i}" for i in range(20)]
    pen = m._penalty_mask()
    assert pen[0] == 0.0            # intercetta
    assert pen[-1] == 0.0           # campo
    assert pen[1:41].sum() == 40    # attacco + difesa


def test_i_lati_cambiano_il_numero_di_parametri():
    """Con `("attacco",)` la difesa non ha dummy affatto: azzerarla a posteriori
    darebbe gli stessi numeri ma renderebbe illeggibile il conteggio."""
    a = PR.ModelloPrecisione(lati=("attacco",))
    b = PR.ModelloPrecisione(lati=("attacco", "difesa"))
    a.teams_ = b.teams_ = [f"T{i}" for i in range(20)]
    assert a._n_par() == 22
    assert b._n_par() == 42


def test_il_modello_recupera_un_effetto_noto():
    """Su dati generati con una quota che dipende dalla squadra, il modello deve
    ordinare le squadre giusto. E' la verifica dove la risposta e' nota."""
    rng = np.random.default_rng(config.SEED)
    squadre = [f"T{i}" for i in range(10)]
    vera = {t: 0.20 + 0.03 * i for i, t in enumerate(squadre)}
    righe = []
    for g in range(30):
        for i, t in enumerate(squadre):
            o = squadre[(i + g + 1) % len(squadre)]
            n = int(rng.poisson(14) + 1)
            righe.append({"team": t, "opponent": o, "is_home": g % 2,
                          "date": pd.Timestamp("2024-01-01") + pd.Timedelta(days=g),
                          T.TARGET: n,
                          T.TARGET_PRECISIONE: rng.binomial(n, vera[t])})
    d = pd.DataFrame(righe)
    m = PR.ModelloPrecisione(lati=("attacco",), alpha=1.0).fit(d)
    p = pd.Series(m.predict(d), index=d.index).groupby(d["team"]).mean()
    assert p["T9"] > p["T0"]
    assert float(np.corrcoef(p.reindex(squadre), [vera[t] for t in squadre])[0, 1]) > 0.9


def test_le_righe_a_zero_tentativi_non_entrano_nel_fit():
    """Senza tentativi non c'e' una prova binomiale: includerle darebbe un
    contributo nullo alla verosimiglianza ma un peso al decadimento."""
    d = pd.DataFrame({
        "team": ["A", "B", "A"], "opponent": ["B", "A", "B"],
        "is_home": [1, 0, 1],
        "date": pd.to_datetime(["2024-01-01", "2024-01-01", "2024-01-08"]),
        T.TARGET: [10, 0, 12], T.TARGET_PRECISIONE: [4, 0, 5]})
    m = PR.ModelloPrecisione(lati=("attacco",)).fit(d)
    assert np.isfinite(m.beta_).all()


# --------------------------------------------------------------------------
# 3. Vincolo 1 — niente futuro
# --------------------------------------------------------------------------
def test_p_lega_guarda_solo_il_passato(wf):
    """Si guasta la coda e si pretende che il passato non si muova, e che il
    futuro si': la seconda meta' del test serve a provare che guarda qualcosa."""
    d = wf[wf["stagione"] == config.SEASONS_STORICHE[-1]].sort_values("date")
    d = d[d[PR.DENOM] > 0].reset_index(drop=True)
    base = PR._p_lega_passato(d)

    meta = len(d) // 2
    rotto = d.copy()
    rotto.loc[meta:, PR.TARGET] = rotto.loc[meta:, PR.DENOM]   # tutti in porta
    dopo = PR._p_lega_passato(rotto)

    ok = ~np.isnan(base[:meta]) & ~np.isnan(dopo[:meta])
    assert ok.sum() > 20
    assert np.allclose(base[:meta][ok], dopo[:meta][ok])
    coda = ~np.isnan(base[meta:]) & ~np.isnan(dopo[meta:])
    assert not np.allclose(base[meta:][coda], dopo[meta:][coda])


def test_p_lega_non_e_la_media_dell_intero_campione(wf):
    """Se coincidesse, il walk-forward non starebbe facendo niente."""
    d = PR._valutabili(wf)
    intero = d[PR.TARGET].sum() / d[PR.DENOM].sum()
    assert not np.allclose(d["p_lega"].to_numpy(), intero)


def test_lo_strato_1_entra_come_dato_e_non_si_ristima(wf):
    """`lam` viene da V1. Ristimarlo qui vorrebbe dire che la validazione di V1
    non varrebbe piu' per il modello che V2 compone."""
    from sot import volume as VL

    wf1 = VL.walkforward_tiri().set_index(["matchId", "team"])["lam"]
    d = PR._valutabili(wf)
    atteso = [wf1.get((mi, t), np.nan) for mi, t in zip(d["matchId"], d["team"])]
    assert np.allclose(d["lam"], atteso, equal_nan=True)


def test_il_lambda_composto_e_il_prodotto(wf):
    """Identita' contabile: se si rompesse, la gerarchia non sarebbe piu' tale."""
    d = PR._valutabili(wf)
    assert np.allclose(d["lam_composto"], d["lam"] * d["p_hat"])
    assert np.allclose(d["lam_composto_lega"], d["lam"] * d["p_lega"])


# --------------------------------------------------------------------------
# 4. I risultati negativi — il contenuto del blocco
# --------------------------------------------------------------------------
def test_lo_strato_2_NON_batte_p_lega(wf):
    """**Non va sistemato.** L'eterogeneita' che V0 ha trovato e' reale ma non
    predittiva: e' la stessa forma del risultato della Fase 2 sugli otto
    predittori, un effetto in campione che fuori campione non paga."""
    q = PR.valutazione_condizionata(wf).set_index("modello")
    lega = q.loc["p_lega (walk-forward)", "ll_per_riga"]
    assert q.loc["strato 2 (attacco+difesa)", "ll_per_riga"] < lega
    assert q.loc["strato 2 (solo attacco)", "ll_per_riga"] < lega


def test_il_modello_ha_correlazione_positiva_ma_perde(wf):
    """Le due cose insieme sono la diagnosi: il modello sa qualcosa (corr > 0)
    ed e' troppo estremo per quanto poco sa (verosimiglianza peggiore). Citarne
    una sola darebbe la conclusione sbagliata in entrambe le direzioni."""
    q = PR.valutazione_condizionata(wf).set_index("modello")
    assert q.loc["strato 2 (solo attacco)", "corr"] > 0
    assert q.loc["strato 2 (solo attacco)", "guadagno_per_riga"] < 0


def test_la_difesa_costa(wf):
    """Il costo della decisione dell'utente, misurato e non assunto. Il criterio
    di V0 escludeva la difesa perche' sotto il MDE; fuori campione peggiora."""
    c = PR.confronto_lati(wf)
    assert c["guadagno_ll_per_riga"] < 0
    assert c["t_quota"] < 0
    assert c["la_difesa_paga"] is False


def test_la_gerarchia_NON_batte_il_modello_diretto(wf):
    """Il risultato che decide il blocco. **Non va sistemato**: a parita' si
    tiene il modello con meno parti, ed e' la regola scritta prima."""
    conf = PR.confronto_col_diretto(wf).set_index("variante")
    assert not conf["batte_il_diretto"].any()
    assert conf.loc["gerarchia (composta)", "dentro_il_mde"]


def test_il_segno_non_e_stabile_fra_stagioni(wf):
    """Il criterio chiedeva 4 stagioni su 5 con lo stesso segno."""
    st = PR.per_stagione(wf)
    assert len(st) == 5
    assert 1 <= int(st["gerarchia_vince"].sum()) <= 3


def test_il_rapporto_delle_dispersioni_falsifica_la_coerenza(wf):
    """Sotto il thinning le due `r` devono essere uguali. Non lo sono, e il
    verso e' l'OPPOSTO di quello che l'eterogeneita' della quota prevedrebbe:
    `r_sot > r_shots` significa meno sovradispersione, non piu'.

    Il test blocca entrambe le cose perche' restino leggibili insieme."""
    d = PR.rapporto_dispersioni(wf, n_boot=200)
    assert not d["uguali"]
    assert d["rapporto"] > 1.0


def test_il_verdetto_e_meccanico():
    """Il criterio applicato dal codice, non a occhio. Si costruiscono le
    tabelle a mano e si pretende il verdetto che il criterio impone."""
    conf = pd.DataFrame({"variante": ["gerarchia (composta)"],
                         "delta_mae": [0.5], "mde": [0.01],
                         "t_per_cluster": [9.0]})
    stag = pd.DataFrame({"gerarchia_vince": [True] * 5})
    assert PR.verdetto_gerarchia(conf, stag)["adotta_la_gerarchia"] is True

    stag_instabile = pd.DataFrame({"gerarchia_vince": [True, True, True, False, False]})
    assert PR.verdetto_gerarchia(conf, stag_instabile)["adotta_la_gerarchia"] is False

    conf_perde = pd.DataFrame({"variante": ["gerarchia (composta)"],
                               "delta_mae": [-0.5], "mde": [0.01],
                               "t_per_cluster": [-9.0]})
    assert PR.verdetto_gerarchia(conf_perde,
                                 pd.DataFrame({"gerarchia_vince": [False] * 5})
                                 )["adotta_la_gerarchia"] is False


def test_il_criterio_e_scritto_prima():
    for pezzo in ("MDE", "4 stagioni su 5", "meno parti"):
        assert pezzo in PR.CRITERIO_GERARCHIA


# --------------------------------------------------------------------------
# 5. Coerenza con gli altri blocchi
# --------------------------------------------------------------------------
def test_i_lati_sono_quelli_decisi_e_non_il_verdetto_di_v0():
    """Le due cose restano separate di proposito: `LATI_STRATO2` e' una
    decisione dell'utente, `verdetto_strato2()` e' l'esito del criterio, e il
    criterio non e' stato riscritto per farli coincidere."""
    assert T.LATI_STRATO2 == ("attacco", "difesa")
    assert PR.ModelloPrecisione().lati == T.LATI_STRATO2


def test_le_linee_dei_tiri_in_porta_restano_quelle_della_fase_4():
    """La marginale composta si valuta su `validate.LINES` inalterata: e' cio'
    che rende la Fase 12 confrontabile con la Fase 4."""
    assert V.LINES == (2.5, 3.5, 4.5, 5.5)
    assert config.OVER_LINE == 4.5


def test_v2_scrive_una_sola_cache():
    src = _codice(config.ROOT / "sot" / "precisione.py")
    assert src.count("to_parquet") == 1
    assert "RAW" not in src
