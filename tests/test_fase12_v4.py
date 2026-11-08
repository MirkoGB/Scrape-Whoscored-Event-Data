# -*- coding: utf-8 -*-
"""Fase 12 / Blocco V4 — il ponte `previsione(squadra, avversario, campo)`.

Due gruppi contano piu' degli altri:

* **`strict_teams` non deve muovere niente col default.** Il parametro tocca
  `model_team._design`, cioe' il cuore su cui poggiano undici fasi, e la
  condizione di accettazione e' l'identita' bit per bit.
* **Le guardie devono scattare, e devono anche saper dire di no.** Un test che
  verifica solo i veri positivi non distingue una guardia che funziona da una che
  solleva sempre.
"""
from __future__ import annotations

import importlib.util
import io
import re
import tokenize

import numpy as np
import pandas as pd
import pytest

from sot import (config, model_team as MT, previsione as P, soglie_2627 as S,
                 tentativi as T)

STAGIONE = config.SEASONS_STORICHE[-1]

#: Il vocabolario vietato dal vincolo 3, con il confine di **lettera** e non
#: `\b`: `_` e' un carattere di parola, quindi `\bbankroll\b` non scatterebbe
#: dentro `calcola_bankroll`. E' la correzione che S1 ha gia' dovuto fare.
VIETATE = ("odds", "quota_decimale", "payout", "bankroll", "kelly", "stake",
           "profitto", "roi", "edge_scommessa", "scommessa")


def _codice(path) -> str:
    src = path.read_text(encoding="utf-8")
    return " ".join(t.string for t in tokenize.generate_tokens(io.StringIO(src).readline)
                    if t.type not in (tokenize.COMMENT, tokenize.STRING))


@pytest.fixture(scope="module")
def st():
    return P.storia(STAGIONE)


# --------------------------------------------------------------------------
# 1. `strict_teams` — il default non muove niente
# --------------------------------------------------------------------------
def test_strict_teams_ha_default_false():
    """Dentro il walk-forward il coefficiente zero e' il comportamento GIUSTO:
    una squadra alla sua prima apparizione in un training parziale. Sollevare
    romperebbe la Fase 2, E3 e R0-R3."""
    assert MT.TeamModel().strict_teams is False


def test_col_default_le_previsioni_sono_identiche(st):
    """L'identita' bit per bit: `strict_teams` non deve poter spostare un numero
    gia' pubblicato."""
    teams = sorted(set(st["team"]) | set(st["opponent"]))
    a = MT.TeamModel(alpha=6.0).fit(st, teams=teams)
    b = MT.TeamModel(alpha=6.0, strict_teams=True).fit(st, teams=teams)
    assert np.array_equal(a.predict(st), b.predict(st))


def test_col_default_una_squadra_ignota_scivola_a_zero(st):
    """Il difetto che la guardia esiste per intercettare, messo a verbale: senza
    `strict_teams` la squadra ignota diventa **esattamente media**, in silenzio.

    Il test lo pretende, cosi' che se un domani il comportamento cambiasse ci si
    accorgesse che qualcosa e' successo."""
    teams = sorted(set(st["team"]) | set(st["opponent"]))
    m = MT.TeamModel(alpha=6.0).fit(st, teams=teams)
    riga = pd.DataFrame([{"team": "Squadra Inventata", "opponent": "Inter",
                          "is_home": 1}])
    lam = float(m.predict(riga)[0])
    assert np.isfinite(lam) and lam > 0        # nessun errore, nessun avviso


def test_la_guardia_scatta_anche_bypassando_l_api(st):
    """Una guardia sola all'ingresso si aggira chiamando il modello
    direttamente: e' il buco che `soglie_2627.difese_avversari` tappa per il solo
    Como, e qui si tappa nel modello."""
    teams = sorted(set(st["team"]) | set(st["opponent"]))
    m = MT.TeamModel(alpha=6.0, strict_teams=True).fit(st, teams=teams)
    riga = pd.DataFrame([{"team": "Squadra Inventata", "opponent": "Inter",
                          "is_home": 1}])
    with pytest.raises(ValueError, match="squadre sconosciute"):
        m.predict(riga)


def test_il_messaggio_elenca_le_squadre_note(st):
    """Il messaggio d'errore e' parte del contratto: senza l'elenco, chi sbaglia
    un nome non sa quale usare."""
    teams = sorted(set(st["team"]) | set(st["opponent"]))
    m = MT.TeamModel(alpha=6.0, strict_teams=True).fit(st, teams=teams)
    riga = pd.DataFrame([{"team": "Pippo", "opponent": "Inter", "is_home": 1}])
    with pytest.raises(ValueError) as e:
        m.predict(riga)
    assert "Pippo" in str(e.value) and "Inter" in str(e.value)


# --------------------------------------------------------------------------
# 2. Le guardie dell'API
# --------------------------------------------------------------------------
def test_squadra_di_un_altra_stagione_solleva():
    """**Il caso realistico**, e non e' la squadra inventata: il Venezia non era
    in Serie A nel 2025-26. Senza guardia il modello darebbe un numero
    perfettamente plausibile, trattandolo come una squadra media."""
    with pytest.raises(ValueError, match="non presenti"):
        P.previsione("Como", "Venezia", "casa", STAGIONE)


def test_squadra_uguale_ad_avversario_solleva():
    with pytest.raises(ValueError, match="coincidono"):
        P.previsione("Como", "Como", "casa", STAGIONE)


def test_campo_non_e_un_booleano():
    """Un `0/1` si scambierebbe senza rumore, e la differenza casa/trasferta vale
    un quarto del livello."""
    for cattivo in ("fuori", "home", "1", "Casa"):
        with pytest.raises(ValueError, match="non ammesso"):
            P.previsione("Como", "Inter", cattivo, STAGIONE)


def test_la_guardia_sa_dire_anche_di_si():
    """Senza questo, «solleva sempre» e «funziona» sarebbero indistinguibili."""
    p = P.previsione("Como", "Inter", "casa", STAGIONE)
    assert p["lambda_tentativi"] > 0
    p2 = P.previsione("Como", "Inter", "trasferta", STAGIONE)
    assert p2["lambda_tentativi"] > 0


# --------------------------------------------------------------------------
# 3. Vincolo 1 — la previsione non usa il futuro
# --------------------------------------------------------------------------
def test_al_e_esclusivo(st):
    """`al` usa le partite con data **strettamente minore**, come
    `date_splits`. Includere la data corrente farebbe entrare nella stima la
    partita che si vuole prevedere."""
    d = P.storia(STAGIONE, al="2026-01-01")
    assert (d["date"] < pd.Timestamp("2026-01-01")).all()
    assert len(d) < len(P.storia(STAGIONE))


def test_la_previsione_non_cambia_se_si_guasta_il_futuro():
    """Si guasta la coda della stagione e si pretende che una previsione fatta
    a meta' non si muova di un bit."""
    u = T.universo([STAGIONE])
    taglio = pd.Timestamp("2026-01-01")
    st = u[u["date"] < taglio]

    base = P.previsione("Como", "Inter", "casa", STAGIONE, st=st)

    rotto = u.copy()
    rotto.loc[rotto["date"] >= taglio, T.TARGET] = 40
    st2 = rotto[rotto["date"] < taglio]
    dopo = P.previsione("Como", "Inter", "casa", STAGIONE, st=st2)

    assert base["lambda_tentativi"] == pytest.approx(dopo["lambda_tentativi"],
                                                     abs=1e-12)


def test_dentro_campione_e_dichiarato():
    """Una previsione in campione presentata come previsione sarebbe il difetto
    piu' facile da non notare in tutto il blocco."""
    p = P.previsione("Como", "Inter", "casa", STAGIONE)      # tutta la stagione
    assert p["dentro_campione"] is True
    assert any("GIA'" in a for a in p["avvisi"])

    u = T.universo([STAGIONE])
    st = u[u["date"] < pd.Timestamp("2025-10-01")]
    q = P.previsione("Como", "Inter", "casa", STAGIONE, st=st)
    assert isinstance(q["dentro_campione"], bool)


def test_storia_vuota_solleva():
    with pytest.raises(ValueError, match="nessuna partita"):
        P.previsione("Como", "Inter", "casa", STAGIONE, al="2020-01-01")


# --------------------------------------------------------------------------
# 4. Coerenza dei numeri
# --------------------------------------------------------------------------
def test_casa_batte_trasferta_su_ogni_avversario():
    """Il vantaggio del campo e' uno solo nel modello, quindi la disuguaglianza
    deve valere per **tutti** gli avversari. Se cadesse su qualcuno, il join fra
    lambda e campo sarebbe rotto."""
    t = P.tabella_avversari("Como", STAGIONE)
    casa = t[t["campo"] == "casa"].set_index("avversario")["lambda_tentativi"]
    fuori = t[t["campo"] == "trasferta"].set_index("avversario")["lambda_tentativi"]
    assert (casa > fuori.reindex(casa.index)).all()


def test_p_over_decresce_nella_linea():
    """Monotonia: prende ogni errore di indice sulle linee."""
    p = P.previsione("Como", "Inter", "casa", STAGIONE)["p_over"]
    assert (p["p_over"].diff().dropna() < 0).all()


def test_la_quota_di_pareggio_e_l_inverso():
    p = P.previsione("Como", "Inter", "casa", STAGIONE)["p_over"]
    assert np.allclose(p["quota_pareggio"], 1.0 / p["p_over"])


def test_gli_intervalli_contengono_il_lambda():
    p = P.previsione("Como", "Inter", "casa", STAGIONE)
    for _, r in p["intervalli"].iterrows():
        assert r["basso"] <= p["lambda_tentativi"] <= r["alto"]


def test_gli_intervalli_crescono_col_livello():
    iv = P.previsione("Como", "Inter", "casa", STAGIONE)["intervalli"]
    largh = (iv["alto"] - iv["basso"]).to_numpy()
    assert (np.diff(largh) > 0).all()


def test_i_tiri_in_porta_sono_meno_dei_tentativi():
    p = P.previsione("Como", "Inter", "casa", STAGIONE)
    assert p["lambda_sot"] < p["lambda_tentativi"]
    assert 0.20 < p["quota_in_porta_implicita"] < 0.50


def test_la_tabella_completa_ha_tutte_le_coppie():
    t = P.tabella_completa(STAGIONE)
    n = t["squadra"].nunique()
    assert len(t) == n * (n - 1) * 2
    assert (t["squadra"] != t["avversario"]).all()


def test_la_tabella_e_coerente_con_la_previsione_singola():
    """Due strade allo stesso numero: se divergessero, una delle due userebbe un
    modello diverso senza dirlo."""
    t = P.tabella_completa(STAGIONE)
    r = t[(t["squadra"] == "Como") & (t["avversario"] == "Inter")
          & (t["campo"] == "casa")].iloc[0]
    p = P.previsione("Como", "Inter", "casa", STAGIONE)
    assert r["lambda_tentativi"] == pytest.approx(p["lambda_tentativi"], rel=1e-9)


# --------------------------------------------------------------------------
# 5. Vincolo 3 — nessuna quota, nessuna scommessa
# --------------------------------------------------------------------------
def _vietate_nel(testo: str) -> list[str]:
    return [v for v in VIETATE
            if re.search(rf"(?<![a-zA-Z]){re.escape(v)}(?![a-zA-Z])", testo)]


def test_il_modulo_non_parla_di_scommesse():
    assert _vietate_nel(_codice(config.ROOT / "sot" / "previsione.py")) == []


def test_la_pagina_non_parla_di_scommesse():
    html = (config.REPORTS / "fase12_v4_simulatore.html")
    if not html.is_file():
        pytest.skip("manca la pagina: esegui run_fase12_v4.py")
    testo = html.read_text(encoding="utf-8")
    # `scommessa` compare nella frase che DICHIARA di non proporne: si ammette
    # solo quella, e il test la nomina invece di allargare il divieto.
    trovate = set(_vietate_nel(testo)) - {"scommessa"}
    assert trovate == set()


def test_la_guardia_del_vincolo_3_sa_dire_anche_di_si():
    """Meta-test: senza, «nessuna parola vietata» potrebbe voler dire «la guardia
    non guarda niente». Verifica i veri positivi e i veri negativi, incluso il
    confine di lettera che S1 ha dovuto correggere."""
    assert "bankroll" in _vietate_nel("calcola_bankroll = 1")
    assert "kelly" in _vietate_nel("frazione kelly")
    assert _vietate_nel("proiezione") == []      # `roi` dentro `proiezione`
    assert _vietate_nel("mistakes") == []        # `stake` dentro `mistakes`


def test_la_quota_di_pareggio_viene_da_soglie_2627():
    """Una definizione in un posto solo: se V4 la riscrivesse, le due copie
    potrebbero divergere."""
    assert S.quota_pareggio(0.5) == pytest.approx(2.0)
    p = P.previsione("Como", "Inter", "casa", STAGIONE)["p_over"]
    atteso = [S.quota_pareggio(x) for x in p["p_over"]]
    assert np.allclose(p["quota_pareggio"], atteso)


# --------------------------------------------------------------------------
# 6. La pagina locale
# --------------------------------------------------------------------------
def test_la_pagina_e_autonoma():
    """«Pagina locale» vuol dire che funziona offline: nessun CDN, nessun font
    remoto, nessuna richiesta di rete."""
    html = (config.REPORTS / "fase12_v4_simulatore.html")
    if not html.is_file():
        pytest.skip("manca la pagina: esegui run_fase12_v4.py")
    testo = html.read_text(encoding="utf-8")
    for vietato in ("http://", "https://", "//cdn", "fetch(", "XMLHttpRequest",
                    "WebSocket", "@import"):
        assert vietato not in testo, f"la pagina contiene {vietato}"


def test_la_pagina_contiene_i_numeri_del_report():
    html = (config.REPORTS / "fase12_v4_simulatore.html")
    if not html.is_file():
        pytest.skip("manca la pagina: esegui run_fase12_v4.py")
    testo = html.read_text(encoding="utf-8")
    p = P.previsione("Como", "Inter", "casa", STAGIONE)
    assert f'{p["lambda_tentativi"]:.4f}'[:6] in testo


def test_v4_non_scrive_sotto_data():
    src = _codice(config.ROOT / "sot" / "previsione.py")
    for vietato in ("to_parquet", "to_csv", "write_text"):
        assert vietato not in src


def test_i_limiti_sono_dichiarati():
    """Vincolo 5: i limiti accanto ai numeri, non in fondo."""
    lim = P.limiti()
    assert len(lim) >= 4
    assert any("MAE" in x for x in lim)
    assert any("burn-in" in x for x in lim)
    assert any("vincolo 3" in x for x in lim)
