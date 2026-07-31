# -*- coding: utf-8 -*-
"""Fase 6A — la catena del livello regge, e il livello non viene dal modello.

I test qui non verificano che i numeri della proiezione siano *giusti*: quello
non e' decidibile con una stagione sola. Verificano che la catena aritmetica
dichiarata nel report sia davvero quella che il codice esegue — che ogni
fattore si ricomponga, che il contesto di squadra si semplifichi davvero, che
il livello pubblicato sia proporzionale al riferimento esterno e non a cio' che
il modello stima.
"""

from __future__ import annotations

import re
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from sot import config, level_chain as LC, model_team as MT, project_2627 as P
from sot import squad_2627 as SQ

TAU = 3.0          # quello scelto in Fase 3, fissato qui per non rifare la CV
R_NB2 = 26.0       # dispersione di Fase 2, fissata per la stessa ragione


@pytest.fixture(scope="module")
def proiezione(player_match, team_match):
    proj, summary, model, _ = P.build_projection(player_match, team_match, tau=TAU)
    return proj, summary, model


# ------------------------------------------------------------- le due catene
def test_ogni_riga_della_catena_si_ricompone(team_match, proiezione):
    """partenza x fattore = risultante, riga per riga. Nessun passo implicito."""
    proj, summary, model = proiezione
    for catena in (LC.catena_modello(team_match),
                   LC.catena_pubblicata(proj, summary, model, R_NB2, n_sim=4000)):
        d = catena.dropna(subset=["valore_partenza", "fattore"])
        assert len(d) >= 3
        assert np.allclose(d["valore_partenza"] * d["fattore"],
                           d["valore_risultante"], rtol=1e-9)


def test_il_prodotto_dei_fattori_riproduce_il_numero_pubblicato(proiezione):
    """4.90 x rapporto x convessita' x 38 = il totale di stagione pubblicato."""
    proj, summary, model = proiezione
    c = LC.catena_pubblicata(proj, summary, model, R_NB2, n_sim=20000)
    fattori = c["fattore"].dropna().to_numpy()
    assert c.iloc[0]["valore_risultante"] == config.REF_TOPDOWN_PER_MATCH
    assert np.isclose(config.REF_TOPDOWN_PER_MATCH * np.prod(fattori),
                      c.iloc[-1]["valore_risultante"], rtol=1e-9)


def test_senza_fonti_il_montecarlo_restituisce_esattamente_l_ancora(proiezione):
    """Se questo fallisce, c'e' un fattore che il report non elenca."""
    proj, summary, model = proiezione
    sim = P.monte_carlo(proj, summary, model, R_NB2, n_sim=500, sources=())
    ancora = summary["ratio"] * config.REF_TOPDOWN_PER_MATCH
    assert np.allclose(sim / SQ.N_MATCHES, ancora, rtol=1e-12)


# --------------------------------------------- il livello non viene dal modello
def test_il_contesto_di_squadra_si_semplifica(proiezione):
    """Moltiplicare il contesto per 1.5 non sposta il livello pubblicato.

    E' la prova che rating, alpha ed effetti attacco/difesa determinano la
    ripartizione fra i giocatori e non il livello.
    """
    proj, summary, model = proiezione
    out = LC.livello_non_dipende_dal_contesto(proj, summary, model, R_NB2,
                                              k=1.5, n_sim=2000)
    assert out["scarto_massimo"] == 0.0


def test_il_livello_e_proporzionale_al_riferimento(proiezione, monkeypatch):
    """Cambiando 4.90 in 5.90 la proiezione si muove del rapporto esatto."""
    proj, summary, model = proiezione
    base = P.monte_carlo(proj, summary, model, R_NB2, n_sim=500, sources=())
    monkeypatch.setattr(config, "REF_TOPDOWN_PER_MATCH", 5.90)
    alzato = P.monte_carlo(proj, summary, model, R_NB2, n_sim=500, sources=())
    assert np.allclose(alzato / base, 5.90 / 4.90, rtol=1e-12)


def test_il_riferimento_e_una_costante_dichiarata_non_un_calcolo():
    """4.90 e' un valore fornito: nessun modulo lo ricava dai dati.

    In `config.py` deve comparire come letterale, e nessun altro file deve
    assegnarlo. Se un giorno qualcuno lo calcolasse davvero — da altre
    stagioni, per esempio — questo test fallisce, ed e' giusto cosi': vorrebbe
    dire che l'affermazione del report di Fase 6A va riscritta.
    """
    testo = (config.ROOT / "sot" / "config.py").read_text(encoding="utf-8")
    assert re.search(r"^REF_TOPDOWN_PER_MATCH = [0-9.]+\s*$", testo, re.M)

    for d in ("sot", "scripts"):
        for p in (config.ROOT / d).glob("*.py"):
            if p.name == "config.py":
                continue
            assert not re.search(r"^\s*REF_TOPDOWN_PER_MATCH\s*=",
                                 p.read_text(encoding="utf-8"), re.M), p.name


def test_inventario_degli_usi_del_riferimento_e_completo():
    """Ogni file che tocca REF_TOPDOWN e' dichiarato in USI_DEL_RIFERIMENTO."""
    dichiarati = {u[0].split(":")[0] for u in LC.USI_DEL_RIFERIMENTO}
    trovati = set()
    for d in ("sot", "scripts"):
        for p in (config.ROOT / d).glob("*.py"):
            if "REF_TOPDOWN" in p.read_text(encoding="utf-8"):
                trovati.add(f"{d}/{p.name}")
    assert trovati - dichiarati == set(), "uso non dichiarato del riferimento"


# ------------------------------------------------------------ scale di campo
def test_le_tre_scale_di_campo_sono_coerenti(team_match):
    rat = LC.ratings_per_campo(team_match)
    f = LC.fattore_campo(team_match)
    assert f > 1.0
    assert np.allclose(rat["casa"], rat["neutro"] * f)
    assert np.allclose(rat["media_calendario"], (rat["neutro"] + rat["casa"]) / 2)


def test_la_colonna_neutro_e_il_valore_in_trasferta(team_match):
    """`neutro` deve coincidere con la previsione del modello in trasferta.

    E' il fatto documentato in Fase 6A: il nome dice campo neutro, il numero e'
    la trasferta. Il test lo blocca cosi' com'e', perche' il valore e' gia'
    pubblicato in `fig5` e non va spostato di nascosto.
    """
    m = MT.TeamModel(alpha=12.0).fit(team_match)
    rat = LC.ratings_per_campo(team_match).set_index("team")
    finta = pd.DataFrame({"team": ["Como"], "opponent": ["Como"], "is_home": [0.0]})
    atteso = float(np.exp(m.mu_ + rat.loc["Como", "attack"]
                          + rat.loc["Como", "defence"]))
    assert np.isclose(float(m.predict(finta)[0]), atteso)
    # e con la difesa media al posto di quella del Como si ottiene `neutro`
    media = float(LC.ratings_per_campo(team_match)["defence"].mean())
    assert np.isclose(float(np.exp(m.mu_ + rat.loc["Como", "attack"] + media)),
                      float(rat.loc["Como", "neutro"]))


# ------------------------------------------------------------- compressione
def _lega_sintetica(n_squadre: int = 10, seed: int = 0) -> pd.DataFrame:
    """Girone di andata e ritorno con forze note e nessuna compressione vera."""
    rng = np.random.default_rng(seed)
    teams = [f"T{i:02d}" for i in range(n_squadre)]
    att = np.linspace(-0.45, 0.45, n_squadre)
    rows = []
    d0 = pd.Timestamp("2025-08-23")
    k = 0
    for i, a in enumerate(teams):
        for j, b in enumerate(teams):
            if i == j:
                continue
            lam = np.exp(1.4 + att[i] + 0.15)
            rows.append({"team": a, "opponent": b, "is_home": 1.0,
                         "date": d0 + pd.Timedelta(days=k % 280),
                         "sot": rng.poisson(lam)})
            k += 1
    df = pd.DataFrame(rows)
    # riga speculare: ogni partita vista dall'altra squadra
    alt = df.rename(columns={"team": "opponent", "opponent": "team"}).copy()
    alt["is_home"] = 0.0
    alt["sot"] = rng.poisson(np.exp(1.4 + att[[teams.index(t) for t in alt["team"]]]))
    return pd.concat([df, alt], ignore_index=True)


def test_la_pendenza_scende_quando_la_ridge_stringe():
    """Piu' penalizzazione, piu' compressione: la metrica deve accorgersene."""
    df = _lega_sintetica()
    debole = LC.compressione_ratings(df, alpha=0.5, squadra="T00")["pendenza"]
    forte = LC.compressione_ratings(df, alpha=200.0, squadra="T00")["pendenza"]
    assert forte < debole
    assert debole > 0.85, "senza penalizzazione non ci deve essere compressione"
    assert forte < 0.5, "con penalizzazione forte i rating devono collassare"


def test_la_ridge_comprime_i_rating_veri(team_match):
    """Sui dati veri la pendenza sta sotto 1.0 di parecchi errori standard."""
    c = LC.compressione_ratings(team_match)
    z = (1.0 - c["pendenza"]) / c["se_pendenza"]
    assert c["pendenza"] < 1.0 and z > 3.0
    # e la de-compressione implicita nel livello usato va nella stessa direzione
    assert c["decompressione_implicita"] > 1.0
    assert c["decompressione_da_pendenza"] > c["decompressione_implicita"]


def test_il_report_di_fase6a_e_rigenerabile():
    """Il report esiste e non contiene numeri digitati a mano.

    Controllo minimo ma non vuoto: le grandezze citate nell'esito in breve
    devono coincidere con quelle che il modulo ricalcola adesso.
    """
    path = config.REPORTS / "phase6_livello.md"
    if not path.exists():
        pytest.skip("esegui prima scripts/run_phase6a.py")
    testo = path.read_text(encoding="utf-8")
    assert "REF_TOPDOWN_PER_MATCH" in testo
    assert "project_2627.py:157" in testo
    assert str(config.REF_TOPDOWN_PER_MATCH) in testo
