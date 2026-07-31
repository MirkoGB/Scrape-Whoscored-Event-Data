# -*- coding: utf-8 -*-
"""Fase 6E — il calendario 2026-27 e l'insieme degli avversari.

I test non verificano che il fattore di calendario sia *giusto* — con una
stagione sola e zero dati sulle promosse non e' decidibile. Verificano tre
cose diverse:

1. che l'aritmetica del fattore sia quella dichiarata nel report (status quo a
   1 esatto, invarianza di scala, monotonia nel verso giusto);
2. che l'affermazione centrale del blocco sul **codice** sia vera: il livello
   pubblicato non conosce il calendario, e applicare un fattore non e' una cosa
   che la proiezione fa da sola;
3. che la classifica da cui escono le retrocesse sia coerente con i dati.
"""

from __future__ import annotations

import re

import numpy as np
import pandas as pd
import pytest

from sot import calendar_2627 as CAL, config, level_chain as LC, project_2627 as P
from sot import squad_2627 as SQ

TAU = 3.0          # quello di Fase 3, fissato per non rifare la CV
R_NB2 = 26.0       # dispersione di Fase 2, fissata per la stessa ragione


@pytest.fixture(scope="module")
def proiezione(player_match, team_match):
    proj, summary, model, _ = P.build_projection(player_match, team_match, tau=TAU)
    return proj, summary, model


# ------------------------------------------------------------- la classifica
def test_la_classifica_torna_con_i_dati(team_match):
    cl = CAL.classifica(team_match)
    assert len(cl) == 20
    assert (cl["partite"] == 38).all()
    # ogni partita distribuisce 3 punti (vittoria) oppure 2 (pareggio)
    gol = team_match.groupby("matchId")["goals"]
    pareggi = int((gol.max() == gol.min()).sum())
    assert cl["punti"].sum() == 3 * 380 - pareggi
    # i gol fatti da tutti sono i gol subiti da tutti
    assert cl["gf"].sum() == cl["gs"].sum() == int(team_match["goals"].sum())
    assert cl["posizione"].tolist() == list(range(1, 21))


def test_le_retrocesse_sono_le_ultime_tre(team_match):
    cl = CAL.classifica(team_match).set_index("team")
    uscite = CAL.retrocesse(team_match)
    assert len(uscite) == 3
    salve = cl.drop(list(uscite))
    # nessuna ambiguita': la 17a ha piu' punti della 18a, niente spareggi
    assert salve["punti"].min() > cl.loc[list(uscite), "punti"].max()


# --------------------------------------------------------- il fattore di calendario
def test_lo_status_quo_da_esattamente_uno(team_match):
    """Promosse uguali alle retrocesse = calendario invariato, F = 1 esatto.

    E' l'ipotesi che il codice fa oggi senza dichiararla, e il fatto che dia
    esattamente 1 e' la ragione per cui non e' mai stata notata.
    """
    liv = CAL.livelli_difensivi(team_match)
    uscite = CAL.retrocesse(team_match)
    for scala in ("modello", "grezzo"):
        c = liv[scala]
        f = CAL.fattore_calendario(c, uscite, float(c[list(uscite)].mean()))
        assert np.isclose(f, 1.0, rtol=1e-12)


def test_il_fattore_non_dipende_dalla_scala_di_campo(team_match):
    """Moltiplicare tutte le difese per una costante non cambia il rapporto."""
    liv = CAL.livelli_difensivi(team_match)
    uscite = CAL.retrocesse(team_match)
    c = liv["modello"]
    cp = float(c.mean())
    base = CAL.fattore_calendario(c, uscite, cp)
    for k in (0.5, 1.217, 7.0):
        assert np.isclose(CAL.fattore_calendario(c * k, uscite, cp * k), base,
                          rtol=1e-12)


def test_il_fattore_cresce_con_la_porosita_delle_promosse(team_match):
    liv = CAL.livelli_difensivi(team_match)
    uscite = CAL.retrocesse(team_match)
    c = liv["grezzo"]
    valori = [CAL.fattore_calendario(c, uscite, x) for x in (3.0, 4.0, 5.0, 6.0)]
    assert valori == sorted(valori)
    # 3 avversari su 19: la derivata e' 3 / somma, non 1
    atteso = 3.0 / float(c[[t for t in c.index if t != "Como"]].sum())
    assert np.isclose((valori[-1] - valori[0]) / 3.0, atteso, rtol=1e-12)


def test_il_como_non_e_avversario_di_se_stesso(team_match):
    liv = CAL.livelli_difensivi(team_match)
    with pytest.raises(ValueError):
        CAL.fattore_calendario(liv["grezzo"], ["Como"], 4.0)


def test_la_scala_del_modello_comprime_rispetto_al_grezzo(team_match):
    """La ridge sottostima il ricambio: stesso scenario, effetto piu' piccolo.

    Non e' un difetto del modulo, e' la compressione della ridge (Fase 6A)
    vista sulle difese. Il test blocca il segno, che e' quello che il report
    afferma; la misura resta un intervallo fra le due scale.
    """
    tab = CAL.scenari_promosse(team_match).set_index(["scenario", "scala"])
    for scen, _ in CAL.SCENARI:
        if scen == "come le retrocesse":
            continue
        m = abs(tab.loc[(scen, "modello"), "fattore"] - 1.0)
        g = abs(tab.loc[(scen, "grezzo"), "fattore"] - 1.0)
        assert m < g, scen


def test_gli_estremi_racchiudono_lo_status_quo_e_l_empirico(team_match):
    """L'intervallo dichiarato deve essere un intervallo, non un lato solo."""
    tab = CAL.scenari_promosse(team_match)
    for scala, g in tab.groupby("scala"):
        v = g.set_index("scenario")["fattore"]
        lo, hi = v["media di campionato"], v["peggiore difesa 2025-26"]
        assert lo < 1.0 < hi
        assert lo <= v["come le retrocesse"] <= hi
        assert lo <= v["coorte promossa 2025-26"] <= hi


# ------------------------------------- il codice non conosce il calendario 26-27
def test_il_livello_pubblicato_non_dipende_dalle_difese_degli_avversari(proiezione):
    """Il fatto centrale del blocco, verificato invece che affermato.

    Se la proiezione tenesse conto dell'insieme di avversari, cambiare i
    coefficienti di difesa la sposterebbe. Non la sposta: il livello e'
    l'ancora esterna, e il contesto si semplifica (Fase 6A). E' anche il motivo
    per cui una correzione di calendario **deve** passare dall'ancora.
    """
    proj, summary, model = proiezione
    a = P.monte_carlo(proj, summary, model, R_NB2, n_sim=2000)
    s2 = dict(summary)
    s2["context_como"] = summary["context_como"] * 1.3   # avversari piu' molli
    s2["lambda_bottomup_2526"] = summary["lambda_bottomup_2526"] * 1.3
    s2["lambda_bottomup_2627"] = summary["lambda_bottomup_2627"] * 1.3
    b = P.monte_carlo(proj, s2, model, R_NB2, n_sim=2000)
    assert float(np.max(np.abs(a - b))) == 0.0


def test_lo_status_quo_riproduce_la_proiezione_pubblicata(proiezione, team_match):
    """Con F = 1 la macchina del blocco deve restituire il numero pubblicato."""
    proj, summary, model = proiezione
    tab = CAL.scenari_promosse(team_match)
    tab = tab[tab["scenario"] == "come le retrocesse"]
    eff = CAL.effetto_su_proiezione(proj, summary, model, R_NB2, tab, n_sim=4000)
    atteso = np.percentile(P.monte_carlo(proj, summary, model, R_NB2, n_sim=4000), 50)
    assert (eff["stagione"] == atteso).all()


def test_il_fattore_entra_solo_dall_ancora(proiezione, team_match):
    """Applicare F equivale a moltiplicare il livello, esattamente."""
    proj, summary, model = proiezione
    f = 1.05
    base = P.monte_carlo(proj, summary, model, R_NB2, n_sim=500, sources=())
    mosso = P.monte_carlo(proj, summary, model, R_NB2, n_sim=500, sources=(),
                          livello_dall_alto=config.REF_TOPDOWN_PER_MATCH * f)
    assert np.allclose(mosso / base, f, rtol=1e-12)


def test_l_equivalente_in_rho_e_coerente_con_il_livello(team_match):
    """F e uno spostamento di rho devono dare lo stesso livello."""
    for f in (0.97, 1.0, 1.02):
        drho = CAL.equivalente_in_rho(f, team_match)
        liv = LC.livello_da_rho(LC.rho_implicito(team_match) + drho, team_match)
        assert np.isclose(liv, config.REF_TOPDOWN_PER_MATCH * f, rtol=1e-9)


def test_nessuno_script_della_proiezione_applica_il_calendario():
    """La correzione e' misurata e dichiarata, non applicata di nascosto.

    Il controllo e' sull'**import**, non sulla stringa: `level_chain` nomina il
    modulo nel proprio inventario del riferimento, e dichiararlo e' il
    contrario di applicarlo. Se un domani qualcuno lo importasse davvero in
    catena, questo test fallisce ed e' giusto cosi': il numero pubblicato
    cambierebbe e va cambiato alla luce del sole.
    """
    importa = re.compile(r"^\s*(from|import)\b.*\bcalendar_2627\b", re.M)
    for cartella, nomi in (("scripts", ("run_phase3.py", "run_phase5.py")),
                           ("sot", ("project_2627.py", "squad_2627.py",
                                    "level_chain.py"))):
        for nome in nomi:
            testo = (config.ROOT / cartella / nome).read_text(encoding="utf-8")
            assert not importa.search(testo), nome


def test_inventario_degli_insiemi_di_avversari_e_completo():
    """Ogni modulo che sceglie un insieme di avversari e' dichiarato.

    L'affermazione del report e' sul codice, quindi il controllo rilegge il
    codice: i moduli che costruiscono una previsione di squadra o un livello
    devono comparire in `INSIEMI_AVVERSARI`.
    """
    dichiarati = {r[0] for r in CAL.INSIEMI_AVVERSARI}
    for nome in ("sot/model_team.py", "sot/level_chain.py", "sot/project_2627.py"):
        assert nome in dichiarati, nome
    # e le funzioni dichiarate devono esistere davvero
    for modulo, funzione, _, _ in CAL.INSIEMI_AVVERSARI:
        testo = (config.ROOT / modulo).read_text(encoding="utf-8")
        for f in re.split(r"\s*/\s*", funzione):
            assert re.search(rf"def {f.split('.')[-1]}\(", testo), (modulo, f)


# ----------------------------------------------------------- la congestione
def test_la_congestione_e_dichiarata_come_limite_e_non_stimata():
    """Punto 2 del blocco: segno atteso dichiarato, nessuna stima.

    Il verso conta — un limite senza segno non e' un limite — e il fatto che
    nessun modulo la stimi e' l'altra meta' dell'affermazione: il Como 2025-26
    non giocava le coppe, quindi il campione non contiene il controfattuale.
    """
    lim = CAL.LIMITE_CONGESTIONE
    assert lim["segno_atteso"] == -1
    assert lim["stimabile_da_questi_dati"] is False
    for chiave in ("che_cosa", "cosa_manca", "perche_no", "dove_entrerebbe"):
        assert lim[chiave].strip()
    # nessun modulo introduce un fattore di congestione nel calcolo
    for p in (config.ROOT / "sot").glob("*.py"):
        testo = p.read_text(encoding="utf-8")
        assert not re.search(r"^\s*(CONGESTION|congestione)\w*\s*=\s*[0-9.]",
                             testo, re.M), p.name


def test_la_rotazione_resta_l_unico_canale_delle_coppe():
    """Oggi la Champions passa solo dai minuti: e' cio' che il limite dice."""
    assert 0.0 < SQ.ROTATION_DEFAULT < 1.0
    lo, hi = SQ.ROTATION_RANGE
    assert lo < SQ.ROTATION_DEFAULT < hi
    assert "minuti" in CAL.LIMITE_CONGESTIONE["cosa_e_modellato_oggi"]


# ------------------------------------------------------------------ il report
def test_il_report_di_fase6e_e_rigenerabile(team_match):
    path = config.REPORTS / "phase6_calendario.md"
    if not path.exists():
        pytest.skip("esegui prima scripts/run_phase6e.py")
    testo = path.read_text(encoding="utf-8")
    for t in CAL.retrocesse(team_match):
        assert t in testo
    assert "PROMOSSE_2526" in testo
    assert "segno_atteso" in testo
