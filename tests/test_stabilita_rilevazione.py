# -*- coding: utf-8 -*-
"""Verifica di stabilita' del criterio di rilevazione: i test.

Due famiglie, e la distinzione conta.

* **Su dati simulati in cui la risposta e' nota** — il gradino c'e' e i modelli
  lo trovano, il gradino non c'e' e non lo trovano, la sovradispersione simulata
  torna dov'e' stata messa. Sono i test che dicono se la macchina funziona.
  Validarla sui risultati del progetto sarebbe circolare, come in
  `test_validate.py`.
* **Sui dati veri, come test di regressione** — la partizione delle categorie,
  l'identita' con il flag Opta, i totali del 2025-26 che devono coincidere con
  le Fasi 0-1. Sono i test che dicono se i dati sono ancora quelli.
"""

from __future__ import annotations

import re
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from sot import config, recording_stability as RS, shots as SH

ROOT = Path(__file__).resolve().parent.parent


# --------------------------------------------------------------------------
# Fixture: la cache multi-stagione, costruita una volta per sessione
# --------------------------------------------------------------------------
@pytest.fixture(scope="session")
def tiri_storici():
    if not config.SHOTS_ALL_SEASONS.exists():
        pytest.skip("cache multi-stagione assente: esegui run_phase7_stabilita.py")
    return RS.carica_tiri()


@pytest.fixture(scope="session")
def file_storici():
    if not config.FILES_ALL_SEASONS.exists():
        pytest.skip("cache multi-stagione assente: esegui run_phase7_stabilita.py")
    return RS.carica_file()


@pytest.fixture(scope="session")
def unita(tiri_storici, file_storici):
    return RS.unita_squadra_partita(tiri_storici, file_storici)


# --------------------------------------------------------------------------
# Dati finti con la risposta nota
# --------------------------------------------------------------------------
def _unita_finte(p, n_partite=200, seed=0, n_tiri=12, rho_ic=0.0):
    """Unita' squadra-partita generate da quote note.

    `p` e' una funzione (indice della stagione, indice del mese nella stagione)
    -> quota. Cosi' lo stesso generatore produce un baseline costante, un
    gradino esatto al confine di stagione e una deriva continua.
    """
    rng = np.random.default_rng(seed)
    righe = []
    for s in range(5):
        for m in range(10):
            anno = 2021 + s + (1 if m >= 5 else 0)
            mese_cal = (8 + m) if m < 5 else (m - 4)
            for j in range(n_partite // 10):
                q = p(s, m)
                if rho_ic > 0:
                    a = q * (1 - rho_ic) / rho_ic
                    b = (1 - q) * (1 - rho_ic) / rho_ic
                    q = rng.beta(a, b)
                k = int(rng.binomial(n_tiri, q))
                righe.append({
                    "stagione": f"{2021 + s}-{2022 + s}",
                    "matchId": s * 10000 + m * 100 + j, "teamId": j % 20,
                    "h_a": "h" if j % 2 else "a",
                    "data": pd.Timestamp(year=anno, month=mese_cal, day=1 + j % 27),
                    "tentativi": n_tiri, "in_porta": k,
                    "bloccato": 0, "palo": 0, "fuori": n_tiri - k,
                })
    u = pd.DataFrame(righe)
    u["mese"] = u["data"].dt.to_period("M").astype(str)
    u["giorno"] = (u["data"] - u["data"].min()).dt.days.astype(float)
    return u.sort_values("data").reset_index(drop=True)


# --------------------------------------------------------------------------
# 1. Le primitive
# --------------------------------------------------------------------------
def test_devianza_nulla_quando_il_modello_e_saturo():
    k = np.array([3.0, 7.0, 0.0, 12.0])
    n = np.array([12.0, 12.0, 12.0, 12.0])
    assert RS._devianza(k, n, k / n) == pytest.approx(0.0, abs=1e-9)


def test_devianza_positiva_quando_il_modello_sbaglia():
    k = np.array([3.0, 9.0])
    n = np.array([12.0, 12.0])
    assert RS._devianza(k, n, np.full(2, 0.5)) > 0


def test_devianza_ignora_le_unita_senza_tentativi():
    """Una squadra-partita con zero tiri esiste davvero (Pisa, 2026-05-10) e
    non deve produrre 0/0 ne' contribuire alla devianza."""
    k = np.array([3.0, 0.0])
    n = np.array([12.0, 0.0])
    p = np.array([0.25, 0.25])
    assert RS._devianza(k, n, p) == pytest.approx(
        RS._devianza(k[:1], n[:1], p[:1]))


def test_p_per_gruppo_e_la_proporzione_del_gruppo():
    k = np.array([1.0, 3.0, 5.0, 5.0])
    n = np.array([10.0, 10.0, 10.0, 10.0])
    g = np.array(["a", "a", "b", "b"])
    p = RS._p_per_gruppo(k, n, g)
    assert p[0] == pytest.approx(0.2) and p[2] == pytest.approx(0.5)


def test_irls_recupera_i_coefficienti_veri():
    rng = np.random.default_rng(1)
    t = np.linspace(-2, 2, 4000)
    X = np.column_stack([np.ones_like(t), t])
    vero = np.array([-0.5, 0.8])
    p = 1 / (1 + np.exp(-(X @ vero)))
    n = np.full(len(t), 30.0)
    k = rng.binomial(30, p).astype(float)
    stimato = RS._logistica_pesata(X, k, n)
    assert stimato == pytest.approx(vero, abs=0.05)


# --------------------------------------------------------------------------
# 2. La sovradispersione
# --------------------------------------------------------------------------
def test_phi_vale_circa_uno_su_dati_binomiali_puri():
    u = _unita_finte(lambda s, m: 0.33, n_partite=1000, seed=2)
    assert RS.dispersione(u, "in_porta") == pytest.approx(1.0, abs=0.08)


def test_phi_cresce_quando_la_sovradispersione_c_e_davvero():
    pura = _unita_finte(lambda s, m: 0.33, n_partite=1000, seed=3)
    sovra = _unita_finte(lambda s, m: 0.33, n_partite=1000, seed=3, rho_ic=0.03)
    assert RS.dispersione(sovra, "in_porta") > RS.dispersione(pura, "in_porta") + 0.15


# --------------------------------------------------------------------------
# 3. I modelli trovano quello che c'e', e solo quello
# --------------------------------------------------------------------------
def test_senza_gradino_il_test_e_calibrato():
    """Il controllo giusto e' il **tasso di rifiuto**, non un singolo seed.

    Su un seed solo un modello con un parametro in piu' arriva primo per caso
    circa una volta su sei — bastano due punti di devianza — e un test che
    pretendesse il primo posto di M0 fallirebbe da solo ogni tanto, cioe'
    sarebbe rumore travestito da controllo. Qui si genera venti volte sotto
    l'ipotesi nulla e si pretende che il tasso di rifiuto resti vicino al
    nominale: e' cio' che rende leggibile il risultato negativo sui dati veri.
    """
    p = []
    for seed in range(20):
        u = _unita_finte(lambda s, m: 0.33, n_partite=200, seed=100 + seed)
        p.append(float(RS.test_annidati(u, "in_porta")
                       .set_index("contro M0")["p"].min()))
    rifiuti = sum(x < 0.05 for x in p)
    assert rifiuti <= 4, f"{rifiuti}/20 rifiuti al 5%: test anticonservativo"


def test_senza_la_correzione_per_phi_il_test_rifiuterebbe_tutto():
    """Perche' la quasi-verosimiglianza c'e'.

    Su dati sovradispersi ma **senza nessun effetto**, la stessa statistica
    letta come un chi-2 ingenuo (phi = 1) rifiuta molto piu' spesso del
    dovuto. E' la ragione per cui `phi` non e' un dettaglio implementativo.
    """
    from scipy import stats

    naif, corretti = 0, 0
    for seed in range(15):
        u = _unita_finte(lambda s, m: 0.33, n_partite=200, seed=200 + seed,
                         rho_ic=0.05)
        k = u["in_porta"].to_numpy(float)
        n = u["tentativi"].to_numpy(float)
        d0 = RS._devianza(k, n, np.full(len(k), k.sum() / n.sum()))
        d1 = RS._devianza(k, n, RS._p_per_gruppo(k, n, u["stagione"].to_numpy()))
        naif += float(stats.chi2.sf(d0 - d1, 4)) < 0.05
        corretti += float(RS.test_annidati(u, "in_porta")
                          .set_index("contro M0").loc["M1 gradino di stagione", "p"]) < 0.05
    assert naif > corretti


def test_con_un_gradino_di_stagione_vince_il_gradino():
    u = _unita_finte(lambda s, m: 0.30 if s < 2 else 0.38,
                     n_partite=1000, seed=5)
    ordinati = RS.confronto_modelli(u, "in_porta").sort_values("QAIC")
    assert ordinati.iloc[0]["modello"] == "M1 gradino di stagione"
    assert ordinati.iloc[1]["QAIC"] - ordinati.iloc[0]["QAIC"] > 2.0


def test_con_una_deriva_continua_vince_la_deriva():
    """La discriminazione che il blocco esiste per fare: gli stessi dati
    aggregati per stagione sembrerebbero cinque gradini."""
    u = _unita_finte(lambda s, m: 0.28 + 0.004 * (s * 10 + m),
                     n_partite=1000, seed=6)
    ordinati = RS.confronto_modelli(u, "in_porta").sort_values("QAIC")
    assert ordinati.iloc[0]["modello"] == "M2 deriva continua"


def test_una_stagionalita_di_calendario_non_diventa_un_gradino():
    """Se il tasso e' alto d'inverno **in ogni stagione**, la risposta giusta e'
    M3, non M1: e' calcio, non annotazione."""
    u = _unita_finte(lambda s, m: 0.30 + 0.06 * (m in (3, 4, 5)),
                     n_partite=1000, seed=7)
    ordinati = RS.confronto_modelli(u, "in_porta").sort_values("QAIC")
    assert ordinati.iloc[0]["modello"] == "M3 mese di calendario"


def test_il_test_annidato_non_rifiuta_quando_non_c_e_niente():
    u = _unita_finte(lambda s, m: 0.33, n_partite=1000, seed=8)
    p = RS.test_annidati(u, "in_porta")
    assert (p["p"] > 0.05).all()


# --------------------------------------------------------------------------
# 4. La scansione del punto di rottura
# --------------------------------------------------------------------------
def test_la_scansione_trova_il_confine_giusto_quando_il_gradino_c_e():
    u = _unita_finte(lambda s, m: 0.30 if s < 2 else 0.40,
                     n_partite=600, seed=9)
    esito = RS.prova_rottura(u, "in_porta", n_sim=100, solo_stagione=False)
    assert esito["confine_migliore"] == "2023-08"
    assert esito["p_max"] < 0.05


def test_senza_gradino_la_scansione_non_rifiuta():
    """E' il test che rende utile il risultato negativo sui dati veri: senza il
    nullo simulato, il massimo di quarantacinque numeri positivi sembra sempre
    un gradino."""
    u = _unita_finte(lambda s, m: 0.33, n_partite=600, seed=10)
    esito = RS.prova_rottura(u, "in_porta", n_sim=200, solo_stagione=False)
    assert esito["p_max"] > 0.05


def test_la_versione_ristretta_cerca_solo_i_confini_di_stagione():
    u = _unita_finte(lambda s, m: 0.33, n_partite=200, seed=11)
    esito = RS.prova_rottura(u, "in_porta", n_sim=50, solo_stagione=True)
    assert esito["candidati"] == 4
    assert esito["e_confine_di_stagione"]
    assert esito["quota_nulla_su_confine_stagione"] == 1.0


def test_i_confini_di_stagione_sono_luglio_e_agosto():
    assert RS._e_confine_di_stagione("2024-08")
    assert RS._e_confine_di_stagione("2024-07")
    assert not RS._e_confine_di_stagione("2024-01")
    assert not RS._e_confine_di_stagione("2024-05")


def test_la_simulazione_e_riproducibile():
    u = _unita_finte(lambda s, m: 0.33, n_partite=200, seed=12)
    a = RS.prova_rottura(u, "in_porta", n_sim=40, seed=7)
    b = RS.prova_rottura(u, "in_porta", n_sim=40, seed=7)
    assert a["p_max"] == b["p_max"]


# --------------------------------------------------------------------------
# 5. La potenza dichiarata
# --------------------------------------------------------------------------
def test_l_mde_scende_quando_i_dati_crescono():
    piccolo = _unita_finte(lambda s, m: 0.33, n_partite=200, seed=13)
    grande = _unita_finte(lambda s, m: 0.33, n_partite=2000, seed=13)
    a = RS.mde_gradino(piccolo, "in_porta")["mde_quota"].mean()
    b = RS.mde_gradino(grande, "in_porta")["mde_quota"].mean()
    assert b < a / 2.5


def test_un_effetto_pari_all_mde_viene_trovato_quasi_sempre():
    """Non un controllo di formula: un controllo che l'MDE dichiarato sia
    l'effetto che il test **davvero** vede."""
    base = _unita_finte(lambda s, m: 0.33, n_partite=1000, seed=14)
    delta = float(RS.mde_gradino(base, "in_porta")
                  .query("confine == '2023-2024'")["mde_quota"].iloc[0])
    u = _unita_finte(lambda s, m: 0.33 + (delta if s >= 2 else 0.0),
                     n_partite=1000, seed=14)
    p = RS.test_annidati(u, "in_porta").query(
        "`contro M0` == 'M1 gradino di stagione'")["p"].iloc[0]
    assert p < 0.05


# --------------------------------------------------------------------------
# 6. I qualifier
# --------------------------------------------------------------------------
def _tiri_finti(qualifiers_per_stagione):
    righe = []
    for s, quals in qualifiers_per_stagione.items():
        for i, q in enumerate(quals):
            righe.append({
                "stagione": s, "matchId": 1, "teamId": 1, "h_a": "h",
                "type": "SavedShot", "isShot": True, "isGoal": False,
                "isOwnGoal": False, "shotBlocked": False,
                "shotOnTarget": True, "qualifiers": str(q),
                "startDate": pd.Timestamp("2024-01-01"),
            })
    return pd.DataFrame(righe)


def test_le_frequenze_dei_qualifier_contano_la_presenza_sul_tiro():
    t = _tiri_finti({
        "A": [[{"type": "X"}], [{"type": "X"}, {"type": "Y"}]],
        "B": [[{"type": "Y"}], [{"type": "Y"}]],
    })
    f = RS.frequenze_qualifier(t)
    assert f.loc["X", "A"] == pytest.approx(1.0)
    assert f.loc["X", "B"] == pytest.approx(0.0)
    assert f.loc["Y", "A"] == pytest.approx(0.5)


def test_un_qualifier_che_sparisce_viene_segnalato():
    t = _tiri_finti({
        "A": [[{"type": "X"}]] * 50,
        "B": [[{"type": "Y"}]] * 50,
    })
    inst = RS.qualifier_instabili(t, RS.frequenze_qualifier(t), soglia_z=6.0)
    assert set(inst["qualifier"]) == {"X", "Y"}
    assert inst["compare_o_sparisce"].all()


def test_presenza_per_partita_distingue_la_pagina_dal_criterio():
    """Sparizione per pagine intere contro sparizione diffusa: il primo caso
    da' quote per partita a 0 o 1, il secondo tutte intermedie."""
    per_pagina = pd.concat([
        _tiri_finti({"A": [[{"type": "X"}]] * 10}).assign(matchId=1),
        _tiri_finti({"A": [[{"type": "Z"}]] * 10}).assign(matchId=2),
    ])
    q = RS.presenza_per_partita(per_pagina, "X")["quota"]
    assert set(q.round(3)) == {0.0, 1.0}


# --------------------------------------------------------------------------
# 7. Sui dati veri: regressione
# --------------------------------------------------------------------------
def test_le_categorie_sono_una_partizione_dei_tentativi(unita):
    somma = unita[list(RS.CATEGORIE)].sum(axis=1)
    assert (somma == unita["tentativi"]).all()


def test_in_porta_e_esattamente_la_definizione_del_repo(tiri_storici):
    """Se qualcuno riscrivesse la regola qui invece di importarla, questo test
    cadrebbe. La definizione di SoT sta in `sot/shots.py` e in nessun altro
    posto."""
    attesa = SH.shots_on_target_mask(tiri_storici).to_numpy()
    ottenuta = (RS.categoria(tiri_storici) == "in_porta").to_numpy()
    assert (attesa == ottenuta).all()


def test_la_regola_coincide_col_flag_opta_in_tutte_le_stagioni(tiri_storici):
    """Il risultato piu' forte del blocco, e non passa da nessun modello."""
    c = RS.coerenza_flag_opta(tiri_storici)
    assert len(c) == 5
    assert (c["solo_regola"] == 0).all()
    assert (c["solo_flag"] == 0).all()


def test_il_2025_2026_riproduce_i_numeri_delle_fasi_0_e_1(unita):
    corrente = unita[unita["stagione"] == config.SEASON]
    assert len(corrente) == 760
    assert int(corrente["tentativi"].sum()) == 9359
    assert int(corrente["in_porta"].sum()) == 3066
    assert corrente["in_porta"].mean() == pytest.approx(4.034, abs=0.001)


def test_l_universo_ha_due_righe_per_partita_anche_a_zero_tiri(unita, file_storici):
    assert len(unita) == 2 * len(file_storici)
    assert (unita["tentativi"] == 0).sum() == 2


def test_unita_valide_toglie_solo_le_squadre_partita_senza_tiri(unita):
    v = RS.unita_valide(unita)
    assert len(v) == len(unita) - 2
    assert (v["tentativi"] > 0).all()


def test_nessuna_colonna_compare_o_sparisce_fra_stagioni(file_storici):
    """259 colonne ovunque non bastava come verifica, ma la verifica fatta bene
    conferma: l'unica colonna non sempre presente e' la trappola nota."""
    inst = RS.colonne_instabili(RS.colonne_per_stagione(file_storici))
    assert list(inst.index) == ["isOwnGoal"]
    assert not inst["assente_in_una_stagione_intera"].any()


def test_gli_ingressi_dell_xg_non_sono_stabili(unita):
    """Il risultato scomodo del blocco, tenuto fermo da un test: se un giorno
    `shotCounter` risultasse stabile, o e' cambiata la fonte o e' cambiato il
    calcolo, e in entrambi i casi va guardato."""
    ordinati = RS.confronto_modelli(unita, "shotCounter").sort_values("QAIC")
    assert ordinati.iloc[0]["modello"] in ("M2 deriva continua",
                                           "M1 gradino di stagione")
    assert float(RS.test_annidati(unita, "shotCounter")["p"].min()) < 1e-6


def test_la_macchina_ha_potenza_sui_dati_veri(unita):
    """Controllo positivo. Senza, il "nessun gradino sui tiri in porta" non si
    distinguerebbe da un test che non funziona."""
    conta = RS.test_annidati(unita, "shotCounter")["F"].max()
    porta = RS.test_annidati(unita, "in_porta")["F"].max()
    assert conta > 50 and porta < 3


# --------------------------------------------------------------------------
# 8. Il blocco non tocca niente
# --------------------------------------------------------------------------
def _importa(sorgente: str, modulo: str) -> bool:
    """Cerca un `import`, non una menzione.

    La versione precedente cercava il nome del modulo **ovunque nel file**, e
    per un po' ha funzionato perche' nessuno lo nominava in prosa. Poi
    `scripts/run_voti_fantacalcio.py` ha scritto nel proprio report che il test
    di rottura formale sta in `sot/recording_stability.py` e **non e' stato
    rifatto sui voti** — cioe' ha citato il modulo proprio per dire che non lo
    usa — e il test lo ha dichiarato colpevole. Un controllo che vieta di
    *parlare* di un modulo e' rumore: quello da vietare e' importarlo.
    """
    return re.search(rf"^\s*(?:from|import)\b.*\b{re.escape(modulo)}\b",
                     sorgente, re.MULTILINE) is not None


def test_nessuno_script_delle_fasi_1_6_importa_questo_modulo():
    colpevoli = [p.name for p in sorted((ROOT / "scripts").glob("*.py"))
                 if _importa(p.read_text(encoding="utf-8"), "recording_stability")
                 and "phase7" not in p.name]
    assert not colpevoli, colpevoli


def test_nessun_modulo_del_modello_importa_questo_modulo():
    colpevoli = [p.name for p in sorted((ROOT / "sot").glob("*.py"))
                 if p.name != "recording_stability.py"
                 and _importa(p.read_text(encoding="utf-8"), "recording_stability")]
    assert not colpevoli, colpevoli


def test_la_cache_non_finisce_dentro_una_cartella_di_stagione():
    """Un Parquet che attraversa cinque stagioni non appartiene a nessuna delle
    cinque: metterlo sotto una direbbe una cosa falsa, e la prima sessione che
    cancella `2025-2026/` per rigenerarla si porterebbe via anche questo."""
    for p in (config.SHOTS_ALL_SEASONS, config.FILES_ALL_SEASONS):
        assert config.SEASON not in p.parts
        assert config.LEAGUE in p.parts
        assert p.parent == config.PROCESSED_LEAGUE


def test_il_modulo_non_scrive_mai_sotto_raw():
    sorgente = (ROOT / "sot" / "recording_stability.py").read_text(encoding="utf-8")
    scritture = re.compile(r"to_parquet|to_csv|mkdir|unlink|rmtree|open\([^)]*['\"]w")
    for n, riga in enumerate(sorgente.splitlines(), 1):
        if scritture.search(riga):
            assert "raw" not in riga.lower(), f"riga {n}: {riga.strip()}"
