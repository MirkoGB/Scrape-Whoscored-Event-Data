# -*- coding: utf-8 -*-
"""Fase 6B — i due estimatori sono davvero due, e il test giudica quello giusto.

Non si verifica che la proiezione sia *giusta* — con una stagione sola non e'
decidibile. Si verifica che:

* l'estimatore compositivo sia invariante rispetto al contesto di squadra e
  quello che fissa il livello no (e' la differenza che li separa);
* il baseline del compositivo sia davvero "nessun aggiustamento di rosa", cioe'
  che con rapporto identicamente 1.0 le due colonne coincidano **esattamente**;
* il numero gia' pubblicato dall'estimatore A non si sia spostato con il
  rinominamento;
* la procedura di proiezione dei minuti sia una sola, condivisa fra la
  proiezione vera e il test di mezza stagione.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from sot import config, model_player as MP, project_2627 as P, squad_2627 as SQ

TAU = 3.0

# Valori pubblicati (Fase 3, README): il rinominamento della Fase 6B non deve
# averli spostati di un millesimo.
MAE_TOPDOWN_PUBBLICATO = 0.416
MAE_LIVELLO_PUBBLICATO = 0.482


@pytest.fixture(scope="module")
def ht(player_match, team_match):
    return P.first_half_test(player_match, team_match, tau=TAU)


# ------------------------------------------------- i due estimatori sono due
def test_il_compositivo_non_dipende_dal_livello_dei_giocatori():
    """Moltiplicare entrambe le ricomposizioni per k non cambia B, cambia A.

    E' la differenza che separa i due estimatori, ed e' la stessa invarianza
    dimostrata in Fase 6A sul numero pubblicato.
    """
    share = np.array([0.4, 0.3, 0.2])
    minuti = np.array([2000.0, 1500.0, 900.0])

    a1 = P.stima_livello_dai_giocatori(share, minuti, context=4.0, n_partite=38)
    a2 = P.stima_livello_dai_giocatori(share, minuti, context=6.0, n_partite=38)
    assert not np.isclose(a1, a2)
    assert np.isclose(a2 / a1, 1.5)

    b1 = P.stima_compositiva(4.90, a1 * 1.02, a1)
    b2 = P.stima_compositiva(4.90, a2 * 1.02, a2)
    assert np.isclose(b1, b2)
    assert np.isclose(b1, 4.90 * 1.02)


def test_rapporto_uguale_a_uno_riproduce_il_baseline():
    """Il baseline corretto di B e' "nessun aggiustamento di rosa"."""
    assert P.stima_compositiva(4.2718, 3.9, 3.9) == 4.2718


def test_l_ancora_del_montecarlo_e_la_stima_compositiva(player_match, team_match):
    """Il livello simulato e' esattamente livello x rapporto, senza scorciatoie."""
    proj, s, model, _ = P.build_projection(player_match, team_match, tau=TAU)
    sim = P.monte_carlo(proj, s, model, r=26.0, n_sim=200, sources=())
    atteso = P.stima_compositiva(config.REF_TOPDOWN_PER_MATCH,
                                 s["lambda_bottomup_2627"],
                                 s["lambda_bottomup_2526"])
    assert np.allclose(sim / SQ.N_MATCHES, atteso, rtol=1e-12)


def test_il_livello_dall_alto_e_parametrizzabile(player_match, team_match):
    """Il default non cambia niente; passarne uno diverso scala tutto."""
    proj, s, model, _ = P.build_projection(player_match, team_match, tau=TAU)
    base = P.monte_carlo(proj, s, model, r=26.0, n_sim=400, sources=())
    uguale = P.monte_carlo(proj, s, model, r=26.0, n_sim=400, sources=(),
                           livello_dall_alto=config.REF_TOPDOWN_PER_MATCH)
    doppio = P.monte_carlo(proj, s, model, r=26.0, n_sim=400, sources=(),
                           livello_dall_alto=2 * config.REF_TOPDOWN_PER_MATCH)
    assert np.array_equal(base, uguale)
    assert np.allclose(doppio / base, 2.0, rtol=1e-12)


# ---------------------------------------------------- il test di mezza stagione
def test_il_test_produce_entrambi_gli_stimatori(ht):
    assert len(ht) == 20
    attese = {"topdown", "livello_dai_giocatori", "compositivo", "rapporto",
              "actual_h2"}
    assert attese <= set(ht.columns)
    assert ht[list(attese)].notna().all().all()


def test_il_compositivo_e_il_topdown_moltiplicato_per_il_rapporto(ht):
    """Nessun altro fattore fra i due: se ce ne fosse uno, sarebbe implicito."""
    assert np.allclose(ht["compositivo"], ht["topdown"] * ht["rapporto"],
                       rtol=1e-12)


def test_i_numeri_pubblicati_non_si_sono_spostati(ht):
    """Il rinominamento non e' un cambio di calcolo."""
    mae_td = ht["err_topdown"].abs().mean()
    mae_liv = ht["err_livello_dai_giocatori"].abs().mean()
    assert abs(mae_td - MAE_TOPDOWN_PUBBLICATO) < 0.001, mae_td
    assert abs(mae_liv - MAE_LIVELLO_PUBBLICATO) < 0.001, mae_liv


def test_senza_ricambio_di_rosa_il_compositivo_e_vuoto(player_match, team_match):
    """Il test di B e' vuoto per costruzione quando la rosa non cambia.

    Si costruisce il caso limite: il secondo tempo di stagione ha la stessa
    rosa del primo, con gli stessi minuti relativi. Il rapporto deve valere
    **esattamente** 1.0 e il compositivo coincidere con il proprio baseline.
    Non e' un dettaglio tecnico: e' la ragione per cui il risultato sui dati
    veri non e' una conferma del metodo.
    """
    pm = player_match.copy()
    h1 = pm[pm["team_match_idx"] <= 19]
    # il secondo tempo diventa una copia del primo: stessi giocatori, stessi minuti
    h2 = h1.copy()
    h2["team_match_idx"] = h2["team_match_idx"] + 19
    finto = pd.concat([h1, h2], ignore_index=True)

    ht = P.first_half_test(finto, team_match, tau=TAU)
    assert np.allclose(ht["rapporto"], 1.0, atol=1e-12)
    assert np.allclose(ht["compositivo"], ht["topdown"], rtol=1e-12)


def test_l_effetto_minimo_rilevabile_supera_l_intervento(ht):
    """Il test non puo' distinguere B dal suo baseline: va detto con un numero.

    Se un domani il MDE scendesse sotto l'intervento medio, il confronto
    diventerebbe informativo e la formulazione del report andrebbe riscritta.
    """
    m = P.effetto_minimo_rilevabile(ht["err_topdown"], ht["err_compositivo"])
    intervento = (ht["compositivo"] - ht["topdown"]).abs().mean()
    assert m["mde"] > abs(m["differenza_osservata"]) * 5
    assert intervento < 1.5 * m["mde"], (intervento, m["mde"])


def test_effetto_minimo_rilevabile_scala_come_ci_si_aspetta():
    """Piu' rumore -> soglia piu' alta; piu' righe -> soglia piu' bassa."""
    rng = np.random.default_rng(0)
    a = rng.normal(0, 1, 200)
    b = a + rng.normal(0, 0.1, 200)
    stretto = P.effetto_minimo_rilevabile(a[:20], b[:20])
    largo = P.effetto_minimo_rilevabile(a[:20], b[:20] + rng.normal(0, 1, 20))
    assert largo["mde"] > stretto["mde"]
    assert P.effetto_minimo_rilevabile(a, b)["mde"] < stretto["mde"]


# ------------------------------------------------------ una sola procedura minuti
def test_le_quote_di_minuti_sono_una_procedura_sola():
    """`project_minutes` deve essere `quote_minuti` piu' il budget, e nient'altro."""
    proj = SQ.project_minutes(rotation=SQ.ROTATION_DEFAULT)
    atteso = SQ.quote_minuti(proj["minutes_2526"].to_numpy(dtype=float),
                             proj["is_new"].to_numpy(),
                             sum(m for _, m, _ in SQ.DEPARTED),
                             SQ.ROTATION_DEFAULT)
    assert np.allclose(proj["share"], atteso)
    assert np.isclose(proj["minutes_proj"].sum(), SQ.OUTFIELD_MINUTES_BUDGET)


def test_i_nuovi_si_spartiscono_i_minuti_liberati():
    base = np.array([1000.0, 500.0, 0.0, 0.0])
    is_new = np.array([False, False, True, True])
    q = SQ.quote_minuti(base, is_new, freed=600.0)
    assert np.isclose(q.sum(), 1.0)
    assert np.isclose(q[2], q[3])
    assert np.isclose(q[2] / q[0], 300.0 / 1000.0)


def test_la_rotazione_comprime_verso_la_quota_uniforme():
    base = np.array([2000.0, 1000.0, 200.0])
    a = SQ.quote_minuti(base, np.zeros(3, dtype=bool), 0.0, rotation=0.0)
    b = SQ.quote_minuti(base, np.zeros(3, dtype=bool), 0.0, rotation=0.5)
    assert b.std() < a.std()
    assert np.isclose(b.sum(), 1.0)
