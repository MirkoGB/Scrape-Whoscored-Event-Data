# -*- coding: utf-8 -*-
"""Fase 11 / Blocco S1 — le soglie del Como 2026-27.

I test che contano sono quelli che **guastano** qualcosa e pretendono che la
guardia se ne accorga: una lista di avversari sbagliata o un calendario corrotto
producono 38 lambda perfettamente plausibili, e senza queste verifiche nessun
controllo a valle se ne accorgerebbe. La tabella di fixture raccolta in fase di
piano era esattamente di quel genere.
"""

from __future__ import annotations

import re

import numpy as np
import pandas as pd
import pytest

from sot import config, dispersion as D, soglie_2627 as S

#: Il vocabolario da scommessa vietato dal vincolo 3, com'e' in R2/R2-bis/R3.
VIETATE_VINCOLO_3 = ("odds", "quota_decimale", "payout", "bankroll", "kelly",
                     "stake", "profitto", "roi", "edge_scommessa")


def _vietata(parola: str, testo: str) -> bool:
    """La parola compare come termine a se', non dentro un'altra parola.

    Confine di **lettera** e non `\\b`: `_` e' un carattere di parola, quindi
    `\\b` non vedrebbe `calcola_bankroll`. Vedi il test che usa questa funzione.
    """
    return re.search(rf"(?<![a-zA-Z]){re.escape(parola)}(?![a-zA-Z])",
                     testo, flags=re.IGNORECASE) is not None


# --------------------------------------------------------------------------
# Fixture: i dati veri, letti una volta sola per l'intero modulo.
# --------------------------------------------------------------------------
@pytest.fixture(scope="module")
def tm():
    from sot import aggregate
    return aggregate.load_team_match()


@pytest.fixture(scope="module")
def lam(tm):
    # L'ancora vera richiede il modello dei giocatori (lento). Qui si usa il
    # riferimento nudo: il ponte non dipende da COME l'ancora e' calcolata, e i
    # test sull'invarianza lo dimostrano.
    return S.lambda_per_partita(tm, config.REF_TOPDOWN_PER_MATCH)


# --------------------------------------------------------------------------
# 1. Le squadre, e la verifica della fonte esterna
# --------------------------------------------------------------------------
def test_retrocesse_dichiarate_coincidono_con_i_dati(tm):
    """L'unico controllo falsificabile sulla fonte esterna, e passa."""
    from sot import calendar_2627 as CAL
    assert sorted(CAL.retrocesse(tm)) == sorted(S.RETROCESSE_2526_DICHIARATE)
    S.verifica_squadre(tm)


def test_verifica_squadre_solleva_se_la_fonte_diverge(tm, monkeypatch):
    """Guastata la fonte, la verifica DEVE vederlo: senza, non guarda niente."""
    monkeypatch.setattr(S, "RETROCESSE_2526_DICHIARATE",
                        ("Inter", "Juventus", "Napoli"))
    with pytest.raises(ValueError, match="non coincidono"):
        S.verifica_squadre(tm)


def test_diciannove_avversari_e_il_como_non_e_fra_loro(tm):
    avv = S.avversari(tm)
    assert len(avv) == 19
    assert "Como" not in avv
    assert set(S.PROMOSSE_2627) <= set(avv)
    assert not (set(S.RETROCESSE_2526_DICHIARATE) & set(avv))


def test_le_promosse_non_sono_nei_dati_2526(tm):
    """Se lo fossero, lo scenario sarebbe superfluo e la guardia non servirebbe."""
    assert not (set(S.PROMOSSE_2627) & set(tm["team"].unique()))


# --------------------------------------------------------------------------
# 2. Il calendario, e la guardia che ha rifiutato quello vero
# --------------------------------------------------------------------------
def test_calendario_ha_la_struttura_pretesa(tm):
    cal = S.calendario(tm)
    assert len(cal) == 38
    assert cal["avversario"].nunique() == 19
    assert (cal["avversario"].value_counts() == 2).all()
    assert (cal.groupby("avversario")["is_home"].sum() == 1).all()
    assert int(cal["is_home"].sum()) == 19


def test_verifica_calendario_rifiuta_la_squadra_fra_i_propri_avversari(tm):
    """E' il difetto esatto della tabella raccolta in fase di piano."""
    cal = S.calendario(tm)
    guasto = cal.copy()
    guasto.loc[guasto.index[0], "avversario"] = "Como"
    with pytest.raises(ValueError, match="fra i propri avversari"):
        S.verifica_calendario(guasto)


def test_verifica_calendario_rifiuta_due_volte_in_casa(tm):
    """L'altro difetto della stessa tabella: una squadra in casa due volte."""
    cal = S.calendario(tm).copy()
    riga = cal.index[cal["is_home"] == 0][0]
    cal.loc[riga, "is_home"] = 1
    with pytest.raises(ValueError, match="una volta per campo"):
        S.verifica_calendario(cal)


def test_verifica_calendario_rifiuta_il_numero_di_righe(tm):
    cal = S.calendario(tm)
    with pytest.raises(ValueError, match="righe invece di 38"):
        S.verifica_calendario(cal.iloc[:37])


def test_la_data_resta_nulla_e_la_giornata_no(tm):
    """Le fonti discordano sulle date: meglio vuota che riempita a caso."""
    cal = S.calendario(tm)
    assert cal["data"].isna().all()
    assert sorted(cal["giornata"]) == list(range(1, 39))


def test_il_calendario_vero_passa_la_propria_guardia(tm):
    """Tre fonti su quattro sono state rifiutate: questa deve passare."""
    S.verifica_calendario(S.calendario(tm, con_giornate=True))


def test_le_giornate_non_cambiano_NESSUN_numero(tm):
    """**E' cio' che rende il calendario un comodo e non una dipendenza.**

    Con e senza giornate le 38 righe sono le stesse coppie (avversario, campo),
    quindi i lambda ordinati e ogni probabilita' aggregata coincidono. Se un
    giorno non fosse piu' vero, vorrebbe dire che l'ordine e' entrato in qualche
    somma senza che nessuno lo dichiarasse.
    """
    a = S.lambda_per_partita(tm, config.REF_TOPDOWN_PER_MATCH)
    cal_b = S.calendario(tm, con_giornate=False)
    dif = S.difese_avversari(tm)
    assert (sorted(np.round(a["lam"], 9))
            == sorted(np.round(a["lam"], 9)))
    assert (sorted(zip(a["avversario"], a["is_home"]))
            == sorted(zip(cal_b["avversario"], cal_b["is_home"])))
    assert set(cal_b["avversario"]) == set(dif.index)


def test_i_nomi_della_fonte_sono_tradotti_e_verificati(tm, monkeypatch):
    """Al livello di squadra il nome non e' una chiave (Fase 8). Una mappa
    incompleta deve sollevare, non produrre un NaN che sparisce."""
    avv = S.avversari(tm)
    for nome, _, _ in [(n, 0, 0) for _, n, _ in S.CALENDARIO_2627]:
        assert S.NOMI_FONTE.get(nome, nome) in avv
    monkeypatch.setattr(S, "NOMI_FONTE", {})
    with pytest.raises(ValueError, match="NOMI_FONTE"):
        S.calendario(tm)


def test_la_partita_ricostruita_e_determinata_non_indovinata(tm):
    """La fonte dava 37 righe. Napoli compariva solo in trasferta, quindi
    l'unica partita compatibile con la struttura e' Como-Napoli in casa: e'
    forzata dai vincoli, non scelta. Qui si verifica che sia proprio quella."""
    cal = S.calendario(tm)
    nap = cal[cal["avversario"] == "Napoli"]
    assert len(nap) == 2
    assert set(nap["is_home"]) == {0, 1}
    assert int(nap.loc[nap["is_home"] == 1, "giornata"].iloc[0]) == 21


def test_le_prime_tre_sono_in_trasferta(tm):
    """Corroborazione esterna indipendente: il Sinigaglia e' in lavori, e le
    fonti lo riportano a parte. Se il calendario fosse mescolato, cadrebbe."""
    cal = S.calendario(tm).sort_values("giornata")
    assert list(cal.head(3)["is_home"]) == [0, 0, 0]


# --------------------------------------------------------------------------
# 3. Il ponte: lambda per partita
# --------------------------------------------------------------------------
def test_una_squadra_sconosciuta_solleva_invece_di_scivolare_a_zero(tm, monkeypatch):
    """`model_team._design` la tratterebbe in silenzio come esattamente media.

    E' la trappola per cui la guardia esiste: nessun errore, nessun avviso, e
    lambda sbagliati che sembrano ragionevoli.
    """
    monkeypatch.setattr(S, "PROMOSSE_2627", ("Venezia", "Frosinone", "Monza"))
    monkeypatch.setattr(S, "RETROCESSE_2526_DICHIARATE",
                        ("Cremonese", "Verona", "Pisa"))
    vere = S.avversari(tm)

    def finto(_tm, squadra="Como"):
        return sorted(set(vere) - {"Inter"} | {"Squadra Inesistente"})

    monkeypatch.setattr(S, "avversari", finto)
    with pytest.raises(ValueError, match="coefficiente di difesa"):
        S.difese_avversari(tm)


def test_la_media_dei_lambda_e_esattamente_l_ancora(lam):
    """E' cio' che rende questa tabella coerente con la proiezione pubblicata."""
    assert lam["lam"].mean() == pytest.approx(config.REF_TOPDOWN_PER_MATCH,
                                              abs=1e-12)


def test_lo_scenario_sulle_promosse_non_sposta_il_livello(tm):
    """Decisione della Fase 6E: applicare il fattore all'ancora sarebbe un
    doppio conteggio. Lo scenario muove la distribuzione, non la media."""
    from sot import calendar_2627 as CAL
    medie, spread = [], []
    for nome, _ in CAL.SCENARI:
        l = S.lambda_per_partita(tm, config.REF_TOPDOWN_PER_MATCH, scenario=nome)
        medie.append(l["lam"].mean())
        spread.append(l["lam"].std())
    assert np.allclose(medie, config.REF_TOPDOWN_PER_MATCH, atol=1e-12)
    # ...ma non e' un no-op: la dispersione fra le partite si muove davvero.
    assert max(spread) - min(spread) > 1e-6


def test_scenario_sconosciuto_solleva(tm):
    with pytest.raises(ValueError, match="sconosciuto"):
        S.difese_avversari(tm, scenario="a occhio")


def test_il_livello_scala_esattamente_con_l_ancora(tm):
    """Raddoppiando l'ancora i lambda raddoppiano tutti: il livello entra per
    moltiplicazione e la struttura relativa non ne dipende."""
    a = S.lambda_per_partita(tm, 4.0)["lam"].to_numpy()
    b = S.lambda_per_partita(tm, 8.0)["lam"].to_numpy()
    assert np.allclose(b, 2.0 * a, rtol=1e-12)


def test_casa_batte_trasferta_su_ogni_avversario(lam):
    """Il vantaggio del campo e' moltiplicativo: nessuna inversione e' possibile.
    Se una comparisse, il join fra difese e calendario sarebbe rotto."""
    p = lam.pivot(index="avversario", columns="campo", values="lam")
    assert (p["casa"] > p["trasferta"]).all()


def test_le_tre_promosse_hanno_la_stessa_difesa(lam):
    """Lo scenario assegna un valore solo, ed e' onesto che si veda."""
    prom = lam[lam["promossa"]]["exp_difesa"].unique()
    assert len(prom) == 1


# --------------------------------------------------------------------------
# 4. Le probabilita'
# --------------------------------------------------------------------------
def test_sampling_e_escluso_dalle_sorgenti_di_livello():
    """Tenerlo conterebbe le code due volte, e in silenzio."""
    from sot import project_2627 as P
    assert "sampling" in P.SOURCES
    assert "sampling" not in S.SORGENTI_LIVELLO
    assert set(S.SORGENTI_LIVELLO) == set(P.SOURCES) - {"sampling"}


def test_p_over_e_una_probabilita_e_decresce_nella_linea(lam):
    ps = S.p_soglie(lam)
    assert ps["p_puntuale"].between(0.0, 1.0).all()
    m = ps.groupby("linea")["p_puntuale"].mean()
    assert (m.diff().dropna() < 0).all()


def test_senza_moltiplicatori_la_colonna_integrata_e_nulla(lam):
    """Non deve essere silenziosamente uguale alla puntuale."""
    ps = S.p_soglie(lam)
    assert ps["p_integrata"].isna().all()


def test_l_integrazione_ingrassa_le_code_nel_verso_dichiarato(lam):
    """Segno dichiarato PRIMA di guardare i numeri: alza le linee alte, abbassa
    le basse. Un test lo blocca cosi' che non lo si possa aggiustare dopo."""
    rng = np.random.default_rng(config.SEED)
    mult = np.quantile(np.exp(rng.normal(0.0, 0.18, 20000)),
                       (np.arange(400) + 0.5) / 400)
    ps = S.p_soglie(lam, mult)
    m = ps.groupby("linea")[["p_puntuale", "p_integrata"]].mean()
    assert m.loc[2.5, "p_integrata"] < m.loc[2.5, "p_puntuale"]
    assert m.loc[7.5, "p_integrata"] > m.loc[7.5, "p_puntuale"]


def test_la_quadratura_e_deterministica(lam):
    """Quantili invece di un sottocampione casuale: due letture, stesso numero."""
    rng = np.random.default_rng(0)
    x = rng.normal(5.0, 1.0, 5000)
    q = (np.arange(50) + 0.5) / 50
    assert np.array_equal(np.quantile(x, q), np.quantile(x, q))


# --------------------------------------------------------------------------
# 5. Quota di pareggio e guadagno atteso — vincolo 3
# --------------------------------------------------------------------------
def test_alla_quota_di_pareggio_il_guadagno_e_zero(lam):
    """E' l'identita' che definisce la quota di pareggio."""
    ps = S.p_soglie(lam)
    p = ps["p_puntuale"].to_numpy()
    g = S.guadagno_atteso(p, S.quota_pareggio(p))
    assert np.allclose(g, 0.0, atol=1e-12)


def test_il_guadagno_e_crescente_nella_quota():
    p = np.array([0.3, 0.5, 0.7])
    assert (S.guadagno_atteso(p, 3.0) > S.guadagno_atteso(p, 2.0)).all()


def test_la_quota_di_pareggio_di_stagione_non_e_la_media_delle_quote(lam):
    """Sono due grandezze diverse (Jensen) ed e' uno scambio che passa
    inosservato: `1/media(p)` non e' `media(1/p)`."""
    ps = S.p_soglie(lam)
    s = S.sintesi_per_linea(ps)
    media_quote = ps.groupby("linea")["quota_pareggio"].mean()
    assert (s.set_index("linea")["quota_pareggio_stagione"]
            < media_quote).all()


def test_margine_proporzionale_da_un_guadagno_IDENTICAMENTE_costante(lam):
    """**Il numero che squalifica l'appendice circolare.**

    Con la quota generata dal modello e margine proporzionale, il guadagno atteso
    vale `1/overround - 1` su ogni partita e su ogni linea. Non contiene una sola
    informazione sul Como: e' il margine, scritto al contrario.
    """
    ps = S.p_soglie(lam)
    circ = S.identita_circolare(ps)
    for ov in S.OVERROUND_IPOTIZZATI:
        g = circ[circ["overround"] == ov]
        assert np.allclose(g["guadagno_proporzionale_per_partita"],
                           1.0 / ov - 1.0, atol=1e-12)
        assert np.allclose(g["dispersione_proporzionale"], 0.0, atol=1e-12)


def test_anche_col_margine_potenza_il_guadagno_resta_negativo(lam):
    """Varia con `p` — il che lo fa *sembrare* una misura — ma e' negativo
    ovunque per costruzione, e a deciderne la taglia e' l'overround."""
    circ = S.identita_circolare(S.p_soglie(lam))
    assert (circ["guadagno_potenza_per_partita"] < 0).all()
    assert (circ["dispersione_potenza"] > 0).all()


def test_vincolo_3_nessun_linguaggio_da_scommessa_nel_modulo():
    """Stessa guardia di R2/R2-bis/R3, sul modulo nuovo — ma **per parola intera**.

    La versione a sottostringa di `tests/test_fase10_r2.py:275` qui darebbe un
    falso positivo: `roi` sta dentro `p-roi-ezione`, che in questo modulo compare
    di continuo. E' lo stesso difetto latente gia' trovato una volta nel progetto
    — la guardia «nessuno script importa questo modulo» che bastava *nominare* il
    modulo in prosa per far scattare.

    Il confine non e' pero' `\\b`: `_` e' un carattere di parola, quindi `\\b`
    **non** vedrebbe `calcola_bankroll`, che e' proprio il caso da fermare. Si
    cerca quindi un confine di **lettera**, che scarta `proiezione` e prende
    `calcola_bankroll`. Il test qui sotto verifica entrambe le direzioni.
    """
    src = (config.ROOT / "sot" / "soglie_2627.py").read_text(encoding="utf-8")
    for vietato in VIETATE_VINCOLO_3:
        assert not _vietata(vietato, src), f"vincolo 3: trovato {vietato!r}"


def test_la_guardia_del_vincolo_3_sa_dire_anche_di_si():
    """Altrimenti «nessuna parola vietata» potrebbe voler dire «non guarda niente».

    Due direzioni, e servono entrambe: la guardia deve prendere il nome anche
    dentro un identificatore composto, e deve lasciar passare la parola italiana
    che lo contiene per caso.
    """
    assert _vietata("bankroll", "def calcola_bankroll(x): ...")
    assert _vietata("kelly", "# frazione di kelly")
    assert _vietata("roi", "roi = 0.1")
    assert not _vietata("roi", "la proiezione 2026-27")
    assert not _vietata("stake", "mistakes")


def test_vincolo_3_la_sezione_circolare_e_etichettata():
    """Il numero comodo deve essere visibile E visibilmente vuoto."""
    src = (config.ROOT / "sot" / "soglie_2627.py").read_text(encoding="utf-8")
    assert "identita_circolare" in src
    assert "circolare" in src.lower()
    assert "legacy/" in src


def test_vincolo_3_nessun_prezzo_di_mercato_e_dichiarato_tale():
    """La griglia di quote e' di lettura, non osservata: deve dirlo."""
    doc = S.tabella_guadagno.__doc__.lower()
    assert "non e' un prezzo osservato" in doc or "non un prezzo" in doc \
        or "ipotesi di lettura" in doc


# --------------------------------------------------------------------------
# 6. Coerenza con cio' che il progetto ha gia' pubblicato
# --------------------------------------------------------------------------
def test_r_e_alpha_sono_quelli_gia_usati_altrove():
    """Due tabelle del progetto non devono parlare di due modelli diversi
    chiamandoli allo stesso modo."""
    from sot import calendar_2627 as CAL
    import inspect
    assert S.ALPHA_LIVELLI == 12.0
    assert inspect.signature(CAL.livelli_difensivi).parameters["alpha"].default == 12.0
    assert S.R_NB2 == 26.0
    assert S.R_NB2_IC95 == (13.7, 111.8)


def test_le_linee_sono_dichiarate_e_non_derivate_dai_dati():
    """Vincolo 1 applicato a una soglia: costanti letterali, mai un argmax."""
    src = (config.ROOT / "sot" / "soglie_2627.py").read_text(encoding="utf-8")
    assert S.LINEE == (2.5, 3.5, 4.5, 5.5, 6.5, 7.5)
    for vietato in ("argmax", "idxmax"):
        assert vietato not in src


def test_le_due_linee_estreme_sono_fuori_dal_perimetro_validato():
    """`validate.LINES` si ferma a 5.5. La 6.5 e la 7.5 sono un'estrapolazione e
    il modulo deve dirlo accanto alla costante, non in fondo al report."""
    from sot import validate as V
    assert max(V.LINES) == 5.5
    assert set(S.LINEE) - set(V.LINES) == {6.5, 7.5}
    src = (config.ROOT / "sot" / "soglie_2627.py").read_text(encoding="utf-8")
    i = src.index("LINEE = ")
    assert "fuori dal perimetro" in src[max(0, i - 500):i]


def test_sensibilita_r_e_maggiore_sulle_code(lam):
    """`r` non e' stimata qui: quanto conta va detto, e conta di piu' sulle code
    relativamente alla probabilita' stessa."""
    s = S.sensibilita_r(lam).set_index("linea")
    rel_media = s.loc[4.5, "escursione"] / s.loc[4.5, f"r={S.R_NB2:g}"]
    rel_coda = s.loc[7.5, "escursione"] / s.loc[7.5, f"r={S.R_NB2:g}"]
    assert rel_coda > rel_media


def test_nessuna_scrittura_sotto_data():
    """Il blocco legge e basta."""
    src = (config.ROOT / "sot" / "soglie_2627.py").read_text(encoding="utf-8")
    for vietato in ("to_parquet", "to_csv", "write_text", "open("):
        assert vietato not in src


# --------------------------------------------------------------------------
# 7. La pagina locale
# --------------------------------------------------------------------------
@pytest.fixture(scope="module")
def pagina(tmp_path_factory, lam):
    """Genera la pagina vera, dai dati veri, in una cartella temporanea."""
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "pagina_s1", config.ROOT / "scripts" / "pagina_s1.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    rng = np.random.default_rng(config.SEED)
    mult = np.quantile(np.exp(rng.normal(0.0, 0.18, 5000)),
                       (np.arange(100) + 0.5) / 100)
    ps = S.p_soglie(lam, mult)
    out = tmp_path_factory.mktemp("s1") / "simulatore.html"
    mod.scrivi(ps, out, ancora=4.95, r_nb2=S.R_NB2, data="2026-08-11",
               linee=S.LINEE)
    return out.read_text(encoding="utf-8")


def test_la_pagina_e_autonoma(pagina):
    """«Pagina locale» vuol dire che funziona senza rete: nessun CDN, nessun
    font remoto, nessuna immagine esterna. Altrimenti offline si rompe."""
    assert not re.search(r'(?:src|href)\s*=\s*["\'](?!#)', pagina)
    assert "http://" not in pagina
    assert "https://" not in pagina


def test_la_pagina_porta_tutti_i_dati(pagina):
    """228 righe = 38 partite x 6 linee, con le giornate vere."""
    import json
    dati = json.loads(re.search(r"const DATI = (\[.*?\]);\n", pagina, re.S).group(1))
    assert len(dati) == 38 * len(S.LINEE)
    assert sorted({d["linea"] for d in dati}) == list(S.LINEE)
    for ln in S.LINEE:
        g = sorted(d["giornata"] for d in dati if d["linea"] == ln)
        assert g == list(range(1, 39))


def test_nessun_segnaposto_rimasto(pagina):
    """Un `__ANCORA__` non sostituito finirebbe a schermo senza rumore."""
    assert not re.findall(r"__[A-Z]+__", pagina)


def test_vincolo_3_la_pagina_non_propone_una_quota(pagina):
    """La quota e' un INGRESSO dell'utente, mai un output del modello.

    Il default dello slider e' la quota di **pareggio**, cioe' il punto in cui il
    guadagno atteso e' zero: e' il default piu' neutro possibile e non e' una
    previsione di prezzo. Il test pretende che sia quello, e non un valore che
    faccia sembrare conveniente qualcosa.
    """
    src = (config.ROOT / "scripts" / "pagina_s1.py").read_text(encoding="utf-8")
    for vietato in VIETATE_VINCOLO_3:
        assert not _vietata(vietato, src), f"vincolo 3: trovato {vietato!r}"
    assert "allaPari.click();" in pagina
    assert "overround" in pagina  # la spiegazione della circolarita' c'e'


def test_la_pagina_dichiara_i_limiti_accanto_ai_numeri(pagina):
    """Vincolo 5: i limiti stanno nella pagina, non in un file a parte."""
    for atteso in ("6.5", "7.5", "estrapolazione", "33 partite"):
        assert atteso in pagina
