# -*- coding: utf-8 -*-
"""Fase 10 / Blocco R2-bis — test della de-compressione e della ricalibrazione.

Le due parti si verificano in modi diversi, ed e' voluto. La de-compressione e'
**algebra** e si verifica su identita' esatte; la ricalibrazione **stima**, quindi
si verifica come si verifica ogni stima di questo progetto: che non guardi il
futuro, e che la misura con cui la si giudica dia la risposta giusta su dati in
cui la risposta e' nota.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from sot import config, esiti as E, perimetro as PM, ricalibrazione as RC


@pytest.fixture(scope="module")
def d() -> pd.DataFrame:
    return RC.dati()


# ---------------------------------------------------------------------------
# §2 — la de-compressione e' algebra: identita' esatte
# ---------------------------------------------------------------------------

def test_decompressione_a_k_uno_e_l_identita():
    lc = np.array([1.7, 0.6, 2.9])
    lt = np.array([0.9, 2.1, 1.1])
    a, b = RC.decomprimi(lc, lt, 1.0)
    assert np.allclose(a, lc) and np.allclose(b, lt)


def test_decompressione_scala_il_divario_esattamente():
    """`k` moltiplica il log-rapporto. Se non lo facesse, «de-compressione» starebbe
    descrivendo un'altra trasformazione e ogni numero di §2 misurerebbe altro."""
    lc = np.array([1.7, 0.6, 2.9])
    lt = np.array([0.9, 2.1, 1.1])
    for k in (0.7, 1.3, 1.9):
        a, b = RC.decomprimi(lc, lt, k)
        assert np.allclose(np.log(a) - np.log(b), k * (np.log(lc) - np.log(lt)))


def test_decompressione_conserva_il_livello():
    """Il prodotto dei due lambda non si muove: la ridge comprime il divario, non
    `mu`, e la de-compressione deve essere il suo inverso e non un altro
    intervento."""
    lc = np.array([1.7, 0.6, 2.9])
    lt = np.array([0.9, 2.1, 1.1])
    a, b = RC.decomprimi(lc, lt, 1.6)
    assert np.allclose(a * b, lc * lt)


def test_verifica_decompressione_passa():
    v = RC.verifica_decompressione()
    assert v["k=1 e' l'identita'"]
    assert v["divario scalato per k"]
    assert v["prodotto invariato"]


def test_le_probabilita_a_k_uno_sono_QUELLE_di_r2(d):
    """Il ponte con R2. Se non coincidessero, questo blocco starebbe misurando la
    calibrazione di un modello diverso da quello che R2 ha pubblicato."""
    pv = E.previsioni()
    p0 = RC.probabilita_decompresse(d, 1.0)
    assert np.allclose(p0, pv[[f"modello|p{c}" for c in E.CLASSI]].to_numpy())


# ---------------------------------------------------------------------------
# §2 — i risultati, bloccati
# ---------------------------------------------------------------------------

def test_la_pendenza_sui_gol_sta_SOTTO_uno(d):
    """Il fatto che contraddice l'ipotesi, e viene da E3 e non da qui.

    Se la ridge comprimesse i lambda, la pendenza di calibrazione **sui gol**
    starebbe sopra 1.0 (previsioni troppo compresse). Sta sotto.
    """
    g = RC.pendenza_marginale_gol(d, 1.0)
    assert g["pendenza"] < 1.0
    assert g["z vs 1.0"] < 0


def test_de_comprimere_peggiora_la_calibrazione_sui_gol(d):
    """Il verso e' monotono: piu' si allarga il divario, piu' i gol si scalibrano."""
    z = [RC.pendenza_marginale_gol(d, k)["pendenza"] for k in (1.0, 1.15, 1.45)]
    assert z[0] > z[1] > z[2]


def test_il_k_che_calibra_il_1x2_e_vicino_a_quello_che_l_ipotesi_prevede(d):
    """La meta' del risultato che va **a favore** dell'ipotesi, e che va detta.

    Il `k` che calibra le classi `1` e `2` sta vicino a `1 / 0,760`. Se il blocco
    riportasse solo il controllo sui gol, nasconderebbe che il sintomo, guardato
    da solo, l'ipotesi la confermerebbe.
    """
    k1 = RC.k_calibrante(d, "1")["k"]
    k2 = RC.k_calibrante(d, "2")["k"]
    assert 1.1 < k1 < RC.K_RIFERIMENTO
    assert abs(k2 - RC.K_RIFERIMENTO) < 0.05


def test_la_X_e_gia_calibrata_e_chiede_il_verso_opposto(d):
    """Coerente con «non e' una compressione sola» — e **non** una prova: a
    `k = 1` la pendenza della `X` non e' distinguibile da 1.0."""
    kx = RC.k_calibrante(d, "X")["k"]
    assert kx < 1.0
    p = RC.probabilita_decompresse(d, 1.0)
    b, se = RC._pendenza(p, d["esito"].to_numpy(), "X")
    assert abs((b - 1.0) / se) < 2.0


def test_l_ipotesi_prevede_una_pendenza_sui_gol_e_i_dati_la_rifiutano(d):
    """Il controllo che decide §2, e la sua potenza.

    Se i lambda fossero compressi di `c`, la pendenza sui gol varrebbe `1/c`:
    l'ipotesi della 6A prevede 1,316 e si osserva 0,898.
    """
    t = RC.controllo_ipotesi_sui_gol(d).set_index("voce")
    z_prev = float(t.iloc[1]["z"])
    assert z_prev < -5.0, z_prev
    # ...e il negativo non e' mancanza di potenza: la compressione minima visibile
    # e' molto piu' piccola di quella che l'ipotesi dichiara.
    visibile = float(t.iloc[2]["valore"])
    assert visibile > RC.PENDENZA_RIDGE_6A


def test_i_tre_modi_di_de_comprimere_danno_la_stessa_conclusione(d):
    """La conclusione non deve dipendere da quale pezzo della de-compressione si
    applica: se dipendesse, sarebbe una parametrizzazione fortunata."""
    k2 = [RC.k_calibrante(d, "2", modo=m)["k"]
          for m in ("divario", "divario_netto", "pieno")]
    assert max(k2) - min(k2) < 0.03
    for m in ("divario", "divario_netto", "pieno"):
        g = RC.pendenza_marginale_gol(d, RC.K_RIFERIMENTO, m)
        assert g["z vs 1.0"] < -4.0, (m, g)


def test_solo_il_modo_pieno_allarga_il_livello(d):
    """`"divario"` conserva il prodotto dei due lambda, `"pieno"` no — ed e' la
    differenza per cui esistono entrambi."""
    for modo, cresce in (("divario", False), ("pieno", True)):
        s1 = np.std(np.log(np.multiply(*RC._lambda_decompressi(d, 1.0, modo))))
        s2 = np.std(np.log(np.multiply(*RC._lambda_decompressi(d, 1.5, modo))))
        assert bool(s2 > s1 * 1.05) == cresce, (modo, s1, s2)


def test_de_comprimere_toglie_pareggi(d):
    """Allargare il divario sposta massa fuori dalla `X`, che gia' ne ha poca."""
    g = RC.griglia_decompressione(d, k_grid=(1.0, 1.15, 1.45))
    px = g["P(X) media"].to_numpy()
    assert px[0] > px[1] > px[2]


def test_il_deficit_di_pareggi_e_positivo(d):
    """Due Poisson indipendenti producono meno pareggi di quanti se ne osservano."""
    t = RC.deficit_pareggi(d)
    tot = t[t["stagione"] == "**tutte**"].iloc[0]
    assert tot["deficit"] > 0
    assert tot["deficit"] > tot["se binomiale"]


# ---------------------------------------------------------------------------
# §3 — la ricalibrazione stima: vincolo 1, e la forma dell'uscita
# ---------------------------------------------------------------------------

def test_temperatura_a_uno_e_l_identita():
    p = np.array([[0.5, 0.3, 0.2], [0.1, 0.2, 0.7]])
    assert np.allclose(RC.applica_temperatura(p, 1.0), p)


def test_temperatura_sotto_uno_affila_e_sopra_uno_appiattisce():
    p = np.array([[0.5, 0.3, 0.2]])
    assert RC.applica_temperatura(p, 0.5)[0, 0] > p[0, 0]
    assert RC.applica_temperatura(p, 2.0)[0, 0] < p[0, 0]


@pytest.mark.parametrize("metodo", RC.METODI)
def test_le_probabilita_ricalibrate_sommano_a_uno(d, metodo):
    P, _app, _par = RC.walkforward_ricalibrazione(d, metodo)
    assert np.allclose(P.sum(axis=1), 1.0)
    assert (P >= 0).all()


@pytest.mark.parametrize("metodo", RC.METODI)
def test_la_prima_stagione_resta_non_ricalibrata(d, metodo):
    """Non ha un passato. Non si riempie con il ricalibratore di un'altra
    stagione e non si toglie dal campione: si marca."""
    P, app, _par = RC.walkforward_ricalibrazione(d, metodo)
    prima = (d["stagione"] == config.SEASONS_STORICHE[0]).to_numpy()
    assert not app[prima].any()
    p0 = RC.probabilita_decompresse(d, 1.0)
    assert np.allclose(P[prima], p0[prima])


def test_la_maschera_e_la_stessa_per_i_tre_metodi(d):
    """`confronto_ricalibrazione` costruisce la riga di riferimento con la
    maschera della temperatura e la riusa per tutti: se le maschere divergessero,
    il confronto girerebbe su righe diverse senza dirlo."""
    m = [RC.walkforward_ricalibrazione(d, x)[1] for x in RC.METODI]
    assert all(np.array_equal(m[0], x) for x in m[1:])


def test_il_ricalibratore_non_guarda_il_futuro(d):
    """Vincolo 1, verificato guastando i dati.

    Si rovescia l'esito di tutta l'ultima stagione: **nessun** parametro deve
    muoversi, perche' l'ultima stagione non sta nel passato di nessuna. E' la
    stessa prova che `tests/test_leakage.py` fa su `walkforward_r`.

    Da solo questo test sarebbe soddisfatto anche da un ricalibratore che non
    guarda niente: e' `test_guastare_una_stagione_PRECEDENTE_muove_le_successive`
    a renderlo non vacuo, e i due vanno letti insieme.
    """
    guasto = d.copy()
    ultima = guasto["stagione"] == config.SEASONS_STORICHE[-1]
    guasto.loc[ultima, "gol_casa"] = 9
    guasto.loc[ultima, "gol_trasferta"] = 0
    guasto.loc[ultima, "esito"] = "1"

    _P0, _a0, par0 = RC.walkforward_ricalibrazione(d, "temperatura")
    _P1, _a1, par1 = RC.walkforward_ricalibrazione(guasto, "temperatura")
    assert (par0["parametro"].to_numpy() == par1["parametro"].to_numpy()).all()


def test_guastare_una_stagione_PRECEDENTE_muove_le_successive(d):
    """Il controllo speculare: se non si muovesse, il ricalibratore non starebbe
    usando il passato che dichiara di usare."""
    guasto = d.copy()
    prima = guasto["stagione"] == config.SEASONS_STORICHE[0]
    guasto.loc[prima, "esito"] = "X"

    _P0, _a0, par0 = RC.walkforward_ricalibrazione(d, "temperatura")
    _P1, _a1, par1 = RC.walkforward_ricalibrazione(guasto, "temperatura")
    assert par0["parametro"].iloc[1] != par1["parametro"].iloc[1]


# ---------------------------------------------------------------------------
# §3 — il criterio, e il verdetto che lo applica
# ---------------------------------------------------------------------------

def test_il_criterio_e_dichiarato_e_non_ricavato():
    """Vincolo 1 applicato a una soglia, come per l'80' e per le soglie di E1."""
    src = (config.ROOT / "sot" / "ricalibrazione.py").read_text(encoding="utf-8")
    assert "CRITERIO_ADOZIONE = (" in src
    for vietato in ("argmax", "idxmax", "idxmin"):
        assert vietato not in src, f"il criterio non va ricavato dai dati: {vietato!r}"


def test_il_verdetto_boccia_chi_peggiora_l_rps():
    """Il criterio applicato a una tabella costruita a mano, dove la risposta e'
    nota: pendenze perfette ma RPS peggiorato oltre il rumore = non adottabile."""
    finta = pd.DataFrame([
        {"metodo": "modello (R2, non ricalibrato)", "z 1": 3.0, "z X": 0.0,
         "z 2": 3.0, "delta RPS": 0.0, "MDE (80%)": np.nan},
        {"metodo": "temperatura", "z 1": 0.1, "z X": 0.1, "z 2": 0.1,
         "delta RPS": 0.010, "MDE (80%)": 0.001},
        {"metodo": "platt", "z 1": 0.1, "z X": 0.1, "z 2": 0.1,
         "delta RPS": -0.002, "MDE (80%)": 0.001},
        {"metodo": "isotonica", "z 1": 5.0, "z X": 0.1, "z 2": 0.1,
         "delta RPS": -0.002, "MDE (80%)": 0.001},
    ])
    v = RC.verdetto(finta)
    assert v["adottabili"] == ["platt"]
    assert v["scelto"] == "platt"


def test_il_metodo_adottato_e_platt(d):
    """Il risultato di §3, bloccato: e' l'unico che passa il criterio dichiarato."""
    v = RC.verdetto(RC.confronto_ricalibrazione(d))
    assert v["scelto"] == "platt"


def test_platt_riporta_le_pendenze_entro_il_rumore(d):
    t = RC.confronto_ricalibrazione(d).set_index("metodo")
    assert abs(t.loc["platt", "z 1"]) < 2.0
    assert abs(t.loc["platt", "z 2"]) < 2.0
    # e il non-ricalibrato no, altrimenti non ci sarebbe niente da correggere
    assert t.loc["modello (R2, non ricalibrato)", "z 2"] > 2.0


# ---------------------------------------------------------------------------
# §4 — la misura di aggregazione, verificata su dati in cui la risposta e' nota
# ---------------------------------------------------------------------------

def test_l_identita_torna_su_esiti_GENERATI_dal_modello(d):
    """La verifica della misura, non del progetto.

    Si generano gli esiti **dalle probabilita' del modello**: per costruzione il
    modello e' allora perfettamente calibrato, e il rapporto
    `osservata / (attesa + campionamento)` deve stare attorno a 1. Se non ci
    stesse, il 2,0 misurato sui dati veri sarebbe un difetto della misura e non
    un fatto sul modello — ed e' l'unico modo di distinguere le due cose.
    """
    rng = np.random.default_rng(config.SEED)
    P = RC.probabilita_decompresse(d, 1.0)
    rapporti = []
    for _ in range(5):
        u = rng.random(len(P))
        cum = np.cumsum(P, axis=1)
        j = (u[:, None] > cum).sum(axis=1)
        finto = d.copy()
        finto["esito"] = [E.CLASSI[x] for x in j]
        rapporti.append(RC.identita_punti(finto, P)["rapporto"].mean())
    assert 0.75 < float(np.mean(rapporti)) < 1.30, rapporti


def test_la_classifica_e_sotto_dispersa_in_tutte_le_stagioni(d):
    """Il risultato di §4: il modello sotto-dichiara quanto le squadre differiscono."""
    t = RC.identita_punti(d)
    assert (t["rapporto"] > 1.2).all()
    assert t["rapporto"].mean() > 1.5


def test_la_sotto_dispersione_resta_nella_seconda_meta(d):
    """Il controllo che separa il burn-in dalla calibrazione: si riduce e resta.

    Se sparisse, sarebbe apprendimento mancante e R3 non la erediterebbe.
    """
    t = RC.identita_punti_per_meta(d).set_index("perimetro")
    prima = t.loc["1a meta' (giornata <= 19)", "rapporto medio"]
    dopo = t.loc["2a meta' (giornata > 19)", "rapporto medio"]
    assert dopo < prima
    assert dopo > 1.2


def test_la_ricalibrazione_non_chiude_la_sotto_dispersione(d):
    """Riduce e non chiude: e' cio' che R3 deve dichiarare invece di ereditare."""
    t = RC.identita_punti_confronto(d).set_index("variante")
    assert t.loc["platt", "rapporto medio"] < t.loc["modello (R2)", "rapporto medio"]
    assert t.loc["platt", "rapporto medio"] > 1.3


# ---------------------------------------------------------------------------
# Guardie
# ---------------------------------------------------------------------------

def test_nessun_numero_pubblicato_e_cambiato(d):
    """R2 non deve essersi mosso di un bit: questo blocco misura, non ritocca."""
    from sot import difesa

    assert len(difesa.walkforward_gol()) == 3478
    assert int(PM.partite()["validabile"].sum()) == 1638
    assert len(d) == 1638
    pv = E.previsioni()
    p = pv[[f"modello|p{c}" for c in E.CLASSI]].to_numpy()
    assert round(float(E.rps(p, pv["esito"].to_numpy()).mean()), 4) == 0.2041
    assert round(E.pendenza_calibrazione(pv, "modello", "1")["pendenza"], 3) == 1.223


def test_vincolo_3_nessuna_quota_nel_modulo():
    src = (config.ROOT / "sot" / "ricalibrazione.py").read_text(encoding="utf-8").lower()
    for vietato in ("odds", "quota_decimale", "payout", "bankroll", "kelly",
                    "stake", "profitto", "roi"):
        assert vietato not in src, f"vincolo 3: trovato {vietato!r}"


def test_r2_resta_senza_stime():
    """La ragione per cui questo blocco e' un modulo separato: `esiti.py` non
    deve aver guadagnato una stima per la porta di servizio."""
    src = (config.ROOT / "sot" / "esiti.py").read_text(encoding="utf-8")
    for vietato in ("minimize", "IsotonicRegression", "LogisticRegression",
                    "ricalibrazione"):
        assert vietato not in src, f"R2 non stima: trovato {vietato!r}"
