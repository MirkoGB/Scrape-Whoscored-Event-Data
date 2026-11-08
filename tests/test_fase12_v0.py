# -*- coding: utf-8 -*-
"""Fase 12 / Blocco V0 — il perimetro del bersaglio.

I test di questo blocco seguono la disciplina del repository: le metriche si
verificano su casi in cui la risposta e' **nota** (dati generati, identita'
algebriche), mai sui risultati del progetto, che sarebbe circolare.

Il gruppo piu' importante e' quello sulla **taratura**: un test di dispersione
che rifiutasse sempre darebbe lo stesso identico verdetto di uno che funziona,
e senza la taratura i due casi non si distinguono. `test_la_taratura_da_la_
dimensione_a_tau_zero` e' quello che rende leggibile tutto il resto.
"""
from __future__ import annotations

import io
import tokenize

import numpy as np
import pandas as pd
import pytest

from sot import config, tentativi as T, validate as V

# I nulli simulati costano: nei test si usano poche repliche, e i test che
# guardano la potenza lo dichiarano nella propria tolleranza.
N_SIM = 200


def _codice(path) -> str:
    """Il sorgente **senza commenti e senza stringhe**.

    Le guardie di questo repository cercano sottostringhe, e il difetto e' gia'
    costato: la guardia dei voti fantacalcio dichiarava colpevole
    `run_voti_fantacalcio.py` perche' *nominava* un modulo in prosa per dire che
    non lo usava, e S1 ha dovuto correggere la guardia del vincolo 3 perche'
    `roi` scattava dentro `proiezione`.

    Una docstring che spiega **perche' una cosa non si fa** e' la forma piu'
    utile di documentazione, e una guardia che la punisce spinge a cancellarla.
    Qui si tokenizza e si tengono i soli token di codice: il divieto vale su
    cio' che il modulo *fa*, non su cio' che *dice*.

    **Anche la parte letterale di una f-string e' una stringa.** Da Python 3.12
    un'f-string non e' piu' un unico token `STRING`: viene spezzata in
    `FSTRING_START` / `FSTRING_MIDDLE` / `FSTRING_END`, e il testo letterale
    sopravviveva alla setacciatura. Trovato in P1, dove il nome di colonna
    `f"p_over_{ln}"` faceva scattare il divieto di `p_over` sul generatore della
    pagina, che quel conto non lo fa affatto. Se un giorno questa funzione gira
    su un Python che quei tipi non li ha, `getattr` li rende innocui.
    """
    src = path.read_text(encoding="utf-8")
    letterali = {tokenize.COMMENT, tokenize.STRING}
    for nome in ("FSTRING_START", "FSTRING_MIDDLE", "FSTRING_END"):
        tipo = getattr(tokenize, nome, None)
        if tipo is not None:
            letterali.add(tipo)
    fuori = []
    for tok in tokenize.generate_tokens(io.StringIO(src).readline):
        if tok.type in letterali:
            continue
        fuori.append(tok.string)
    return " ".join(fuori)


@pytest.fixture(scope="module")
def u():
    return T.universo()


@pytest.fixture(scope="module")
def agg(u):
    return T.quota_aggregata(u, "attacco")


# --------------------------------------------------------------------------
# 1. Il bersaglio, e le verifiche falsificabili
# --------------------------------------------------------------------------
def test_sot_mai_maggiore_di_shots(u):
    """Se cadesse, la binomiale dello strato 2 sarebbe IMPOSSIBILE, non malamente
    specificata. E' il controllo che una fase intera puo' non fare mai."""
    assert (u[T.TARGET_PRECISIONE] <= u[T.TARGET]).all()


def test_le_verifiche_di_conteggio_passano_tutte(u):
    tab = T.verifica_conteggi(u)
    assert tab["passa"].all(), tab[~tab["passa"]].to_string()


def test_le_righe_a_zero_tentativi_ci_sono_e_non_entrano_nei_rapporti(u):
    """Esistono squadre-partita con zero tentativi (gia' noto dalla Fase 7).
    Entrano nei livelli e NON nei rapporti: una quota senza denominatore non
    esiste, e uno zero la farebbe entrare nelle medie come una squadra che non
    ha mai centrato la porta."""
    zero = u[u[T.TARGET] == 0]
    assert len(zero) > 0, "se sparissero, l'universo sarebbe ricostruito dai tiri"
    assert zero["quota_in_porta"].isna().all()
    assert u.loc[u[T.TARGET] > 0, "quota_in_porta"].notna().all()


def test_matchid_e_unico_fra_le_cinque_stagioni(u):
    """Serve a V1: `build_predictors` aggancia il lato difensivo con
    `merge(on=["matchId","opponent"])`. Un `matchId` ripetuto farebbe arrivare il
    predittore dell'avversario da un'altra stagione, in silenzio."""
    assert T.matchid_unico(u)["unico"]


def test_il_denominatore_si_conta_e_non_e_38(u):
    """L'Atalanta ha 35 partite nel 2021-22 e nel 2022-23: assumere 38
    sbaglierebbe ogni quota proprio dove la perdita alla fonte non e' casuale."""
    n = u.groupby(["stagione", "team"]).size()
    assert n.min() < 38
    assert set(n.unique()) - {38} != set()


# --------------------------------------------------------------------------
# 2. Le soglie, dichiarate prima
# --------------------------------------------------------------------------
def test_le_linee_sono_letterali_e_non_derivate_dai_dati():
    """Vincolo 1 applicato a una soglia. Il divieto di `quantile` e' una regola
    NUOVA e piu' severa di quella di S1 (che vieta solo argmax/idxmax e usa
    `np.quantile` legittimamente): qui nessun quantile empirico deve poter
    entrare in una soglia."""
    src = _codice(config.ROOT / "sot" / "tentativi.py")
    assert T.LINEE_TIRI == (8.5, 10.5, 12.5, 14.5, 16.5)
    assert T.LINEA_PRINCIPALE == 12.5
    for vietato in ("argmax", "idxmax", "quantile"):
        assert vietato not in src, f"{vietato} nel CODICE del modulo delle soglie"


def test_ogni_linea_ha_tasso_base_dentro_la_regola(u):
    """Fuori da [0,10-0,90] il Brier misura soprattutto `r` invece del lambda:
    e' il difetto che S1 ha dovuto dichiarare sulle sue due linee estreme."""
    tab = T.base_rate_linee(u)
    assert tab["dentro_regola"].all(), tab.to_string()


def test_le_linee_dei_tiri_in_porta_non_si_toccano():
    """Inventare linee nuove per `sot` renderebbe la Fase 12 non confrontabile
    con la Fase 4, che e' il difetto contro cui esiste il vincolo 7."""
    assert V.LINES == (2.5, 3.5, 4.5, 5.5)
    assert T.LINEE_SOT_INVARIATE is True


def test_le_linee_sono_le_stesse_in_deviazioni_standard(u):
    """L'argomento di `REGOLA_LINEE` reso un numero: le linee dei tentativi non
    sono inventate, sono quelle dei tiri in porta trasportate sulla nuova
    scala. Entrambe coprono all'incirca [-0,8, +0,8] sd."""
    c = T.confronto_con_le_linee_sot()
    for _, g in c.groupby("bersaglio"):
        assert g["sd_dalla_media"].min() > -1.0
        assert g["sd_dalla_media"].max() < 1.0


def test_il_criterio_e_scritto_prima():
    """Il criterio deve nominare entrambe le condizioni e il ramo del collasso,
    altrimenti `verdetto_strato2` potrebbe applicarne uno diverso."""
    for pezzo in ("Sidak", "MDE", "p_lega", "forma chiusa"):
        assert pezzo in T.CRITERIO_STRATO2


# --------------------------------------------------------------------------
# 3. Il livello dell'aggregazione — perche' 1,101 non risponde
# --------------------------------------------------------------------------
def test_il_livello_squadra_partita_non_risponde_alla_domanda(u):
    """Mette a verbale che citare `phi = 1,101` come risposta e' un errore.

    A ~12,6 tentativi il rumore binomiale della quota vale ~13 punti e una
    differenza fra squadre di 2-3 punti ci sparisce dentro; a ~475 no. Il test
    pretende che il MDE del livello sbagliato sia **peggiore**, cosi' che la
    scorciatoia risulti visibilmente tale."""
    tab = T.livello_sbagliato(u).set_index("livello")
    sp, ss = tab.loc["squadra-partita"], tab.loc["squadra-stagione"]
    assert sp["sd_binomiale_quota"] > 5 * ss["sd_binomiale_quota"]
    assert sp["tau_mde"] > ss["tau_mde"]
    assert 1.0 < sp["phi_osservato"] < 1.2       # e' il rumore, non un effetto


def test_la_chiave_della_difesa_non_ricostruisce_l_attacco(u):
    """Il difetto vero di questo blocco, trovato perche' i due lati davano lo
    stesso identico `phi`. `sot_conceded` sulla riga (i,j) sono i tiri in porta
    di j: aggregarli sotto la chiave j ricostruisce l'attacco di j."""
    a = T.quota_aggregata(u, "attacco").set_index(["stagione", "chiave"])["p_hat"]
    d = T.quota_aggregata(u, "difesa").set_index(["stagione", "chiave"])["p_hat"]
    comune = a.index.intersection(d.index)
    assert len(comune) > 50
    assert not np.allclose(a.loc[comune], d.loc[comune])


def test_lato_ignoto_solleva(u):
    with pytest.raises(ValueError, match="lato ignoto"):
        T.quota_aggregata(u, "pippo")


# --------------------------------------------------------------------------
# 4. La taratura — cio' che rende leggibile tutto il resto
# --------------------------------------------------------------------------
def test_la_taratura_da_la_dimensione_a_tau_zero(u):
    """SENZA QUESTO TEST IL RISULTATO DI V0 NON SIGNIFICA NIENTE.

    Un test che rifiuta sempre darebbe lo stesso verdetto di uno che funziona.
    A `tau = 0` la frequenza di rifiuto e' la **dimensione** del test — stessa
    lettura di `PP.potenza(0, se)` — e con la soglia di Sidak per k = 3 vale
    ~1,7%. Tolleranza larga perche' le repliche qui sono poche."""
    tar = T.taratura_test(u, lato="attacco", tau_griglia=(0.0,), n_sim=N_SIM)
    assert tar.loc[0, "potenza"] < 0.12


def test_la_taratura_e_monotona_e_arriva_alla_potenza_piena(u):
    tar = T.taratura_test(u, lato="attacco",
                          tau_griglia=(0.0, 0.010, 0.020, 0.030), n_sim=N_SIM)
    p = tar["potenza"].to_numpy()
    assert (np.diff(p) >= -0.05).all(), "la potenza deve crescere con tau"
    assert p[-1] > 0.90


def test_il_mde_tarato_e_piu_grande_di_quello_analitico(u, agg):
    """La formula analitica assume `phi` normale con sd costante; sotto
    l'alternativa la sd cresce, quindi il MDE analitico e' OTTIMISTICO. Il test
    blocca la direzione: un MDE sbagliato nel verso comodo e' peggio che non
    averlo."""
    tar = T.taratura_test(u, lato="attacco", n_sim=N_SIM)
    tarato = T.mde_da_taratura(tar)
    analitico = T.mde_tau(agg, phi0=float(tar["phi_medio"].iloc[0]))["tau_mde"]
    assert tarato > analitico


def test_mde_da_taratura_interpola(u):
    """Su una griglia costruita a mano il risultato e' calcolabile a mano."""
    finta = pd.DataFrame({"tau": [0.0, 0.01, 0.02], "potenza": [0.05, 0.60, 0.90]})
    got = T.mde_da_taratura(finta, potenza=0.80)
    assert got == pytest.approx(0.01 + 0.20 / 0.30 * 0.01, abs=1e-12)


def test_mde_da_taratura_e_nan_se_la_griglia_non_arriva():
    finta = pd.DataFrame({"tau": [0.0, 0.01], "potenza": [0.05, 0.30]})
    assert np.isnan(T.mde_da_taratura(finta))


# --------------------------------------------------------------------------
# 5. Il nullo simulato
# --------------------------------------------------------------------------
def test_il_nullo_simulato_include_la_sovradispersione_di_partita(u):
    """Il pezzo che il chi-quadro teorico non sa. Senza, il nullo starebbe
    attorno a 1 e il test rifiuterebbe scambiando la sovradispersione di partita
    per eterogeneita' di squadra: sarebbe GARANTITO di rifiutare."""
    con = T.nullo_simulato(u, lato="attacco", tau=0.0, n_sim=N_SIM)
    senza = T.nullo_simulato(u, lato="attacco", tau=0.0, rho_partita=0.0, n_sim=N_SIM)
    assert np.mean(con) > np.mean(senza)
    assert np.mean(senza) == pytest.approx(1.0, abs=0.12)


def test_il_rho_intraclasse_riproduce_la_dispersione_nota(u):
    """`phi ~ 1,10` sulle unita' squadra-partita e' cio' che la Fase 7 aveva gia'
    misurato (1,101) con un'altra macchina e su un'altra aggregazione: due
    strade indipendenti che concordano."""
    r = T.rho_intraclasse(u)
    assert r["phi_squadra_partita"] == pytest.approx(1.10, abs=0.05)
    assert 0.0 < r["rho_intraclasse"] < 0.02


def test_il_nullo_e_deterministico_a_seme_fisso(u):
    a = T.nullo_simulato(u, tau=0.0, n_sim=50, seed=config.SEED)
    b = T.nullo_simulato(u, tau=0.0, n_sim=50, seed=config.SEED)
    assert np.array_equal(a, b)


def test_beta_binomiale_con_rho_zero_e_binomiale():
    """Il ramo degenere deve restare ottenibile, altrimenti la taratura non
    potrebbe separare le due componenti."""
    rng = np.random.default_rng(config.SEED)
    n = np.full(20000, 12.0)
    p = np.full(20000, 0.33)
    k = T._beta_binomiale(rng, n, p, 0.0)
    var_att = 20000 * 0  # placeholder, la verifica e' sulla dispersione
    res = (k - n * p) ** 2 / (n * p * (1 - p))
    assert res.mean() == pytest.approx(1.0, abs=0.05)


def test_beta_binomiale_con_rho_positivo_disperde_di_piu():
    rng = np.random.default_rng(config.SEED)
    n = np.full(20000, 12.0)
    p = np.full(20000, 0.33)
    res0 = ((T._beta_binomiale(rng, n, p, 0.0) - n * p) ** 2 / (n * p * (1 - p))).mean()
    res1 = ((T._beta_binomiale(rng, n, p, 0.05) - n * p) ** 2 / (n * p * (1 - p))).mean()
    assert res1 > res0 * 1.2


# --------------------------------------------------------------------------
# 6. Il thinning — la premessa della gerarchia
# --------------------------------------------------------------------------
def test_il_thinning_e_esatto_su_dati_simulati():
    """Se `N ~ NB2(lam, r)` e `S|N ~ Bin(N,p)` allora `S ~ NB2(lam*p, r)`, stesso
    `r`. E' cio' su cui poggia la forma chiusa della marginale in V2: verificata
    dove la risposta e' nota, con `dispersion.fit_r` del progetto e non con una
    formula scritta apposta."""
    t = T.thinning_simulato(n=200_000)
    assert abs(t["scarto_media_pct"]) < 1.0
    assert abs(t["scarto_r_pct"]) < 12.0


def test_il_thinning_conserva_r_a_p_diversi():
    """`r` non deve dipendere da `p`: se dipendesse, la forma chiusa sarebbe
    valida solo attorno al `p` provato."""
    for p in (0.20, 0.33, 0.50):
        t = T.thinning_simulato(p=p, n=120_000)
        assert abs(t["scarto_r_pct"]) < 20.0


# --------------------------------------------------------------------------
# 7. Il cluster di partita
# --------------------------------------------------------------------------
def test_la_correlazione_fra_i_lati_e_negativa_in_ogni_stagione(u):
    """Il segno NON era l'attesa (si temeva positiva, per ritmo condiviso). E'
    negativa perche' il possesso e' a somma costante, e la conseguenza va nel
    verso favorevole. Il test blocca il fatto perche' resti leggibile: se un
    domani diventasse positiva, ogni MDE di questa fase andrebbe rifatto."""
    tab = T.correlazione_lati(u)
    assert len(tab) == 5
    assert (tab["corr"] < 0).all()
    assert (tab["ic95_alto"] < 0).all(), "lo zero non deve stare negli intervalli"


def test_il_fattore_di_cluster_e_sotto_uno(u):
    c = T.fattore_cluster(u)
    assert c["corr_pooled"] < 0
    assert 0.7 < c["fattore_se"] < 1.0
    assert c["stesso_segno"]


# --------------------------------------------------------------------------
# 8. Il verdetto
# --------------------------------------------------------------------------
def test_verdetto_strato2_e_meccanico():
    """Il criterio dichiarato applicato dal codice, non a occhio. Si costruisce
    una tabella a mano e si pretende il verdetto che il criterio impone."""
    nulla = pd.DataFrame({"lato": ["attacco", "difesa", "campo"],
                          "rifiuta": [False, False, False],
                          "supera_mde": [True, True, True]})
    assert T.verdetto_strato2(nulla)["stima_lo_strato_2"] is False
    assert T.verdetto_strato2(nulla)["forma_chiusa_valida"] is True

    solo_mde = pd.DataFrame({"lato": ["attacco", "difesa", "campo"],
                             "rifiuta": [True, True, True],
                             "supera_mde": [False, False, False]})
    assert T.verdetto_strato2(solo_mde)["stima_lo_strato_2"] is False

    uno = pd.DataFrame({"lato": ["attacco", "difesa", "campo"],
                        "rifiuta": [True, False, False],
                        "supera_mde": [True, False, False]})
    v = T.verdetto_strato2(uno)
    assert v["stima_lo_strato_2"] is True
    assert v["lati_adottati"] == ["attacco"]


def test_servono_entrambe_le_condizioni():
    """Rifiutare non basta e superare il MDE non basta: il criterio chiede la
    congiunzione, ed e' cio' che tiene fuori il lato difesa."""
    mista = pd.DataFrame({"lato": ["attacco", "difesa"],
                          "rifiuta": [True, True],
                          "supera_mde": [False, False]})
    assert T.verdetto_strato2(mista)["lati_adottati"] == []


# --------------------------------------------------------------------------
# 9. La strada di controllo, e la concordanza
# --------------------------------------------------------------------------
def test_il_glm_e_una_strada_indipendente(u):
    """Non passa dal test di dispersione: stima `p` come coefficienti, con test F
    annidati e `phi` dal modello pieno. Due strade che concordano sono un
    risultato; una sola e' un'asserzione."""
    tab = T.test_eterogeneita_glm(u)
    assert len(tab) == 3
    assert (tab["phi"] > 1.0).all()
    att = tab[tab["confronto"].str.contains("attacco")].iloc[0]
    assert att["p"] < 0.001, "l'attacco deve rifiutare anche per questa strada"


def test_le_due_strade_concordano_sull_attacco(u):
    """La concordanza e' il risultato. Sul lato difesa NON concordano — il GLM
    rifiuta, il test di dispersione lo mette sotto il proprio MDE — e non e' una
    contraddizione: l'effetto c'e' ed e' piccolo. Il test lo mette a verbale."""
    disp = T.test_eterogeneita(u, lato="attacco", n_sim=N_SIM)
    glm = T.test_eterogeneita_glm(u)
    att = glm[glm["confronto"].str.contains("attacco")].iloc[0]
    assert disp["rifiuta"] and att["p"] < 0.001


# --------------------------------------------------------------------------
# 10. V0 non stima e non scrive
# --------------------------------------------------------------------------
def test_v0_non_stima_nessun_modello_predittivo():
    """Nessun walk-forward, nessun bersaglio previsto, nessun iperparametro. Il
    GLM di controllo e' una stima descrittiva in campione, non una previsione, e
    per questo `_glm_binomiale` puo' usare `optimize`."""
    src = _codice(config.ROOT / "sot" / "tentativi.py")
    for vietato in ("walkforward_predict", "TeamModel", "walkforward_baselines"):
        assert vietato not in src


def test_v0_non_scrive_sotto_data():
    src = _codice(config.ROOT / "sot" / "tentativi.py")
    for vietato in ("to_parquet", "to_csv", "write_text"):
        assert vietato not in src


def test_la_guardia_sa_dire_anche_di_si(tmp_path):
    """Meta-test sulla guardia, nella forma di `test_fase11_s1.py:360`.

    Senza, «nessuna parola vietata» potrebbe voler dire «la guardia non guarda
    niente». Verifica entrambe le direzioni: il codice vero scatta, la prosa che
    nomina la parola per dire che non la si usa **non** scatta."""
    f = tmp_path / "finto.py"
    f.write_text('"""Non si usa argmax qui."""\n# e nemmeno quantile\nx = 1\n',
                 encoding="utf-8")
    assert "argmax" not in _codice(f)
    assert "quantile" not in _codice(f)

    f.write_text('"""Docstring innocua."""\ny = serie.argmax()\n', encoding="utf-8")
    assert "argmax" in _codice(f)
