# -*- coding: utf-8 -*-
"""Fase 6C — `rho` e' ricavato, non scelto, e sposta solo cio' che deve.

Il rischio di questo blocco e' esattamente l'opposto di quello di 6A: li' si
poteva credere che il modello decidesse il livello quando non lo faceva, qui si
puo' credere di aver **stimato** una persistenza fra stagioni che con una
stagione sola non e' stimabile. I test bloccano le due affermazioni che il
report fa:

* il default di `rho` riproduce esattamente il livello gia' pubblicato, quindi
  e' ricavato da quel livello e non ipotizzato;
* far variare `rho` cambia il livello della proiezione e **nient'altro**.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from sot import config, level_chain as LC, project_2627 as P, squad_2627 as SQ

TAU = 3.0
R_NB2 = 26.0


@pytest.fixture(scope="module")
def proiezione(player_match, team_match):
    proj, summary, model, _ = P.build_projection(player_match, team_match, tau=TAU)
    return proj, summary, model


# ------------------------------------------------------- il default e' ricavato
def test_il_default_di_rho_riproduce_il_livello_pubblicato(team_match):
    """`livello_da_rho(rho_implicito)` deve dare 4.90 al bit.

    E' la definizione di "ricavato": se questo test fallisse, `rho` sarebbe un
    numero scelto e il report andrebbe riscritto.
    """
    rho = LC.rho_implicito(team_match)
    assert np.isclose(LC.livello_da_rho(rho, team_match),
                      config.REF_TOPDOWN_PER_MATCH, rtol=1e-12)
    assert 0.0 < rho < 1.0


def test_rho_non_dipende_dalla_scala_di_campo(team_match):
    """Trasferta, casa o calendario: la quota di eccesso e' la stessa.

    In Fase 6A il rapporto e' calcolato sulla scala di trasferta, qui su quella
    di calendario. Se i due divergessero, uno dei due report starebbe leggendo
    la grandezza sbagliata.
    """
    c = LC.compressione_ratings(team_match)
    assert np.isclose(c["rho_implicito"], LC.rho_implicito(team_match), rtol=1e-9)


def test_gli_estremi_di_rho_hanno_il_significato_dichiarato(team_match):
    media = float(team_match["sot"].mean())
    grezzo = float(team_match.loc[team_match["team"] == "Como", "sot"].mean())
    assert np.isclose(LC.livello_da_rho(0.0, team_match), media)
    assert np.isclose(LC.livello_da_rho(1.0, team_match), grezzo)
    # monotona crescente, e il livello usato sta fra i due
    liv = [LC.livello_da_rho(r, team_match) for r in LC.RHO_GRID]
    assert all(b > a for a, b in zip(liv, liv[1:]))
    assert media < config.REF_TOPDOWN_PER_MATCH < grezzo


def test_la_griglia_e_dichiarata_e_contiene_il_valore_implicito(team_match):
    """La griglia va dichiarata in anticipo e non deve escludere l'implicito."""
    assert LC.RHO_GRID == tuple(sorted(LC.RHO_GRID))
    assert LC.RHO_GRID[0] == 0.50 and LC.RHO_GRID[-1] == 0.95
    assert LC.RHO_GRID[0] < LC.rho_implicito(team_match) < LC.RHO_GRID[-1]


# --------------------------------------------------- rho sposta solo il livello
def test_alla_rho_implicita_la_proiezione_e_quella_pubblicata(proiezione, team_match):
    """La parametrizzazione non deve aver spostato il numero pubblicato."""
    proj, s, model = proiezione
    rho = LC.rho_implicito(team_match)
    a = P.monte_carlo(proj, s, model, R_NB2, n_sim=4000)
    b = P.monte_carlo(proj, s, model, R_NB2, n_sim=4000,
                      livello_dall_alto=LC.livello_da_rho(rho, team_match))
    assert np.array_equal(a, b)


def test_la_proiezione_cresce_con_rho(proiezione, team_match):
    proj, s, model = proiezione
    tab = LC.sensibilita_rho(proj, s, model, R_NB2, team_match,
                             rho_grid=(0.50, 0.70, 0.95), con_implicito=False,
                             n_sim=4000)
    assert list(tab["stagione"]) == sorted(tab["stagione"])
    assert (tab["q10"] < tab["stagione"]).all()
    assert (tab["q90"] > tab["stagione"]).all()


def test_la_pendenza_su_rho_e_quella_dell_ancora(proiezione, team_match):
    """La relazione livello -> proiezione e' una moltiplicazione: la pendenza
    empirica deve stare vicino a `38 x rapporto x convessita' x eccesso`."""
    proj, s, model = proiezione
    tab = LC.sensibilita_rho(proj, s, model, R_NB2, team_match, n_sim=8000)
    pend = LC.pendenza_su_rho(tab)

    sim = P.monte_carlo(proj, s, model, R_NB2, n_sim=8000)
    ancora = P.stima_compositiva(config.REF_TOPDOWN_PER_MATCH,
                                 s["lambda_bottomup_2627"],
                                 s["lambda_bottomup_2526"])
    conv = (float(np.percentile(sim, 50)) / SQ.N_MATCHES) / ancora
    media = float(team_match["sot"].mean())
    grezzo = float(team_match.loc[team_match["team"] == "Como", "sot"].mean())
    esatta = SQ.N_MATCHES * s["ratio"] * conv * (grezzo - media)

    assert abs(pend["per_unita"] / esatta - 1.0) < 0.10, (pend, esatta)
    assert pend["r2"] > 0.99


def test_rho_non_tocca_l_ampiezza_dell_intervallo(proiezione, team_match):
    """Cambiare il livello scala la proiezione, non allarga l'incertezza.

    L'ampiezza relativa dell'intervallo e' ereditata dal riferimento (Fase 6A):
    se variasse con `rho`, vorrebbe dire che il parametro sta entrando anche
    dove il report dice che non entra.
    """
    proj, s, model = proiezione
    tab = LC.sensibilita_rho(proj, s, model, R_NB2, team_match,
                             rho_grid=(0.55, 0.95), con_implicito=False,
                             n_sim=8000)
    rel = (tab["q90"] - tab["q10"]) / tab["stagione"]
    assert abs(rel.iloc[0] / rel.iloc[1] - 1.0) < 0.05, rel.tolist()


# ------------------------------------------------------------------- figura
def test_la_figura_evidenzia_il_rho_implicito():
    from matplotlib.colors import to_rgba

    from sot import figures as F

    tab = pd.DataFrame({"rho": [0.6, 0.7, 0.808, 0.9],
                        "livello_dall_alto": [4.6, 4.8, 4.9, 5.0],
                        "stagione": [180.0, 186.0, 191.0, 195.0],
                        "q10": [140.0, 146.0, 151.0, 155.0],
                        "q90": [225.0, 232.0, 239.0, 244.0]})
    ax = F.proiezione_per_rho(tab, 0.808, pubblicato=191.0).axes[0]
    intervalli = [l.get_color() for l in ax.lines
                  if l.get_linestyle() == "-" and l.get_marker() == "None"]
    punti = [l.get_color() for l in ax.lines if l.get_marker() == "o"]

    assert intervalli.count(F.SERIE_1) == 1, "un solo intervallo evidenziato"
    assert intervalli.count(F.DEEMPH) == 3
    assert punti.count(F.SERIE_1) == 1 and punti.count(F.DEEMPH) == 3
    # e il punto a colore e' proprio quello di rho implicito
    i = [l.get_color() for l in ax.lines if l.get_marker() == "o"].index(F.SERIE_1)
    assert np.isclose([l.get_xdata()[0] for l in ax.lines
                       if l.get_marker() == "o"][i], 0.808)
    assert any("rho" in t.get_text() for t in ax.texts)
    assert any("pubblicato" in t.get_text() for t in ax.texts)
