"""Fase 16 / Blocco O1 — la verifica prospettica.

Il blocco poggia su due affermazioni che, se false, renderebbero tutto il resto
privo di senso: che le previsioni **precedano** i dati, e che siano quelle che
la regola dichiarata avrebbe prodotto. I test qui sotto le rendono
**falsificabili**: guastano cio' che dovrebbe far scattare la guardia e
pretendono che scatti. Senza, «la verifica passa» e «la verifica non controlla
niente» sarebbero indistinguibili.
"""

from __future__ import annotations

import io
import tokenize
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from sot import config
from sot import verifica_prospettica as VP

MODULO = Path(VP.__file__)
SCRIPT = config.ROOT / "scripts" / "run_fase16_o1.py"


def _codice(path: Path) -> str:
    """Il sorgente **senza commenti e senza stringhe**.

    Stessa funzione di `tests/test_fase12_v0.py`, e per la stessa ragione: una
    guardia a sottostringa punirebbe la docstring che spiega *perche'* una cosa
    non si fa, ed e' un difetto che questo repository ha gia' pagato tre volte.
    Anche la parte letterale di una f-string e' una stringa (da Python 3.12 e'
    spezzata in `FSTRING_*`).
    """
    letterali = {tokenize.COMMENT, tokenize.STRING}
    for nome in ("FSTRING_START", "FSTRING_MIDDLE", "FSTRING_END"):
        t = getattr(tokenize, nome, None)
        if t is not None:
            letterali.add(t)
    fuori = []
    src = path.read_text(encoding="utf-8")
    for tok in tokenize.generate_tokens(io.StringIO(src).readline):
        if tok.type not in letterali:
            fuori.append(tok.string)
    return " ".join(fuori)


@pytest.fixture(scope="module")
def prev():
    """Il perimetro della Serie A sui tiri: e' il campionato di controllo."""
    return VP.previsioni_del_perimetro("ITA-serie-a", "shots")


# ------------------------------------------------------------ le costanti
def test_le_soglie_sono_dichiarate_e_non_ricavate_dai_dati():
    """Nessun `argmax`/`idxmax`/`quantile` nel CODICE del modulo.

    E' la regola di `tentativi.py` e `soglie_2627.py`: una soglia scelta
    guardando il campione su cui poi la si valuta e' il vincolo 1 violato nel
    punto in cui costa di piu'. Qui varrebbe doppio, perche' il perimetro e la
    metrica sono dichiarati **prima** che gli esiti siano letti.
    """
    codice = _codice(MODULO)
    for vietato in ("argmax", "idxmax", "quantile"):
        assert vietato not in codice, f"{vietato} nel codice di {MODULO.name}"


def test_la_guardia_sul_codice_distingue_prosa_e_codice(tmp_path):
    """Il meta-test: la guardia deve vedere il codice e NON la docstring."""
    f = tmp_path / "x.py"
    f.write_text('"""Qui non si usa argmax."""\n# nemmeno quantile\nx = 1\n',
                 encoding="utf-8")
    assert "argmax" not in _codice(f) and "quantile" not in _codice(f)
    f.write_text('"""Innocua."""\ny = s.argmax()\n', encoding="utf-8")
    assert "argmax" in _codice(f)


def test_vincolo_3_nessuna_quota_nel_modulo():
    """Nessun prezzo, nessun ritorno atteso: non ci sono quote reali in casa."""
    codice = _codice(MODULO).lower()
    for vietato in ("quota_pareggio", "overround", "roi", "bankroll",
                    "guadagno_atteso", "puntata"):
        assert vietato not in codice, f"{vietato} nel codice di {MODULO.name}"


def test_il_modulo_non_tocca_la_rete():
    codice = _codice(MODULO)
    for vietato in ("requests", "selenium", "urlopen", "webdriver", "httpx"):
        assert vietato not in codice


def test_il_modulo_non_scrive_sotto_data():
    """Scrive solo il registro, e solo sotto `reports/`."""
    codice = _codice(MODULO)
    for vietato in ("to_parquet", "to_csv"):
        assert vietato not in codice, (
            f"{vietato} nel modulo: la scrittura appartiene allo script")
    # l'unica scrittura ammessa e' la copia del registro
    assert "copy2" in codice


def test_le_linee_sot_restano_quelle_della_fase_4():
    """`LINEE_SOT_INVARIATE` non e' decorativa: linee nuove romperebbero il
    confronto con tutto cio' che il progetto ha pubblicato sui tiri in porta."""
    from sot import tentativi as T
    from sot import validate as V

    assert T.LINEE_SOT_INVARIATE is True
    assert VP.linee_del_lato("sot") == tuple(V.LINES)
    assert VP.linee_del_lato("shots") == tuple(T.LINEE_TIRI)


def test_il_soggetto_e_il_candidato_prescritto_dalla_regola():
    """Si valuta cio' che `REGOLA_DUE_REGIMI` avrebbe pubblicato sotto il
    burn-in, non una variante costruita per l'occasione."""
    from sot import prior_stagione as PS

    assert VP.SOGGETTO in PS.CANDIDATI
    assert VP.SOGGETTO == "modello prec"
    assert VP.PERIMETRO_IDX_MAX < config.BURN_IN_ROUND


# ------------------------------------------------- anteriorita' e registro
def test_il_registro_dichiara_l_anteriorita_sui_dati():
    reg = VP.registro()
    assert bool(reg["presente"].all())
    assert bool(reg["anteriore"].all())
    assert float(reg["giorni_di_anticipo"].min()) > 0.0


def test_le_congelate_si_riproducono_dal_solo_anno_scorso():
    """La prova che non chiede di fidarsi di un orologio."""
    v = VP.verifica_anteriorita(["ITA-serie-a"])
    assert bool(v["riprodotto"].all())
    assert bool(v["supera"].all())


def test_la_tolleranza_viene_dall_ottimizzatore_non_dallo_scarto():
    """`TOLL_RIPRODUZIONE` dev'essere >= sqrt(ftol) di L-BFGS-B.

    Sceglierla guardando lo scarto osservato sarebbe far tornare un numero. Il
    test lega la costante alla `ftol` che `TeamModel` dichiara nel sorgente.
    """
    src = (config.ROOT / "sot" / "model_team.py").read_text(encoding="utf-8")
    assert "1e-12" in src, "la ftol di TeamModel e' cambiata: rivedere la soglia"
    assert VP.TOLL_RIPRODUZIONE >= np.sqrt(1e-12)
    # e resta cinque ordini di grandezza sotto qualunque cosa si misuri
    assert VP.TOLL_RIPRODUZIONE < 1e-3


def test_la_verifica_dell_anteriorita_e_falsificabile(monkeypatch):
    """Se il file congelato NON venisse dal modello dell'anno scorso, la
    guardia deve accorgersene. Senza questo test, «riprodotto» potrebbe voler
    dire «non guarda niente»."""
    vero = VP.PS.lam_dal_prior

    def guasto(p, squadra, avversario, in_casa):
        out = vero(p, squadra, avversario, in_casa).copy()
        out[0] *= 1.05          # una riga sola, il 5%
        return out

    monkeypatch.setattr(VP.PS, "lam_dal_prior", guasto)
    v = VP.verifica_anteriorita(["ITA-serie-a"])
    assert not bool(v["riprodotto"].iloc[0])
    assert not bool(v["supera"].iloc[0])


# ------------------------------------------------------------ il perimetro
def test_il_perimetro_e_coerente_col_disco_non_una_fotografia():
    """Non si asserisce «170 righe»: quel numero cresce ogni martedi'.

    La Fase 15 ha gia' pagato due test-fotografia diventati rossi da soli. Qui
    si verifica la **proprieta'**: ogni squadra contribuisce al piu' due
    partite, la riga e' la squadra-partita, e il conto torna con i CSV su disco.
    """
    for lg in config.LEAGUE_CODES:
        p = VP.perimetro(lg)
        if not len(p):
            continue
        assert int(p["team_match_idx"].max()) <= VP.PERIMETRO_IDX_MAX
        per_squadra = p.groupby("team")["matchId"].nunique()
        assert int(per_squadra.max()) <= VP.PERIMETRO_IDX_MAX
        assert len(p) == 2 * p["matchId"].nunique()
        csv = list(config.match_dir(lg, config.SEASON_CORRENTE).glob("*.csv"))
        assert p["matchId"].nunique() <= len(csv)


def test_una_coppia_ambigua_non_diventa_un_disaccordo():
    """La trappola che la prima stesura ha davvero preso.

    Se la seconda fonte elenca lo stesso accoppiamento a due giornate — un
    rinvio — tenerne una a caso inventa un disaccordo che e' del codice, non
    del ripiego. Si tolgono tutte le copie, come fa `calendario.py`.
    """
    v = VP.verifica_giornata("FRA-ligue-1")
    assert v["n_ambigue"] >= 1, "il caso di prova non esiste piu' nella fonte"
    assert v["n_discordi"] == 0
    assert v["accordo"] == pytest.approx(1.0)


def test_il_controllo_positivo_e_totale_dove_la_fonte_e_completa():
    ver = pd.DataFrame([VP.verifica_giornata(lg) for lg in config.LEAGUE_CODES])
    pieni = ver[ver["fonte_completa"].astype(bool)]
    assert len(pieni) >= 1, "nessun controllo positivo disponibile"
    assert float(pieni["accordo"].min()) == pytest.approx(1.0)
    assert VP.ripiego_ammesso(ver)["ammesso"]


def test_il_ripiego_non_si_applica_se_il_controllo_positivo_cade():
    """La regola deve saper dire anche di NO."""
    finta = pd.DataFrame([
        {"campionato": "X", "verificabile": True, "fonte_completa": True,
         "accordo": 0.9, "n_discordi": 2},
    ])
    assert not VP.ripiego_ammesso(finta)["ammesso"]
    senza = pd.DataFrame([
        {"campionato": "X", "verificabile": True, "fonte_completa": False,
         "accordo": 1.0, "n_discordi": 0},
    ])
    assert not VP.ripiego_ammesso(senza)["ammesso"]


# ------------------------------------------------ il ponte col congelato
def test_il_join_col_congelato_non_moltiplica_le_righe(prev):
    assert len(prev) == len(VP.perimetro("ITA-serie-a"))
    assert prev["matchId"].nunique() * 2 == len(prev)


def test_il_congelato_coincide_con_modello_prec(prev):
    c = VP.coerenza_col_congelato(prev)
    assert c["n"] > 0
    assert c["coincidono"]
    assert c["scarto_max"] < VP.TOLL_RIPRODUZIONE


def test_le_neopromosse_non_hanno_previsione_documentale(prev):
    """Le due colonne devono dire la stessa cosa: dove manca il numero
    congelato c'e' una squadra che il prior non conosce."""
    assert prev["neopromossa_coinvolta"].any()
    assert not (prev["da_file_congelato"] & prev["neopromossa_coinvolta"]).any()
    # e la quota e' grande: al giorno 1 e' un fatto, non un dettaglio
    assert 0.0 < float((~prev["da_file_congelato"]).mean()) < 0.6


def test_l_oracolo_di_livello_azzera_il_bias_per_costruzione(prev):
    """Sta in tabella per essere letto come oracolo, non come modello."""
    y = prev["shots"].to_numpy(dtype=float)
    assert float(np.mean(prev["lam_oracolo_livello"] - y)) == pytest.approx(
        0.0, abs=1e-9)
    # e non riordina niente: e' una riscalatura
    r = np.corrcoef(prev["lam_modello_prec"], prev["lam_oracolo_livello"])[0, 1]
    assert r == pytest.approx(1.0, abs=1e-12)


def test_ogni_riga_porta_la_dispersione_del_suo_campionato():
    """`r` e' una costante DI CAMPIONATO: mediare il CRPS fra campionati e'
    lecito solo se ogni riga viaggia con la propria."""
    ins = VP.insieme([VP.previsioni_del_perimetro(lg, "shots")
                      for lg in config.LEAGUE_CODES])
    assert ins["r_lega"].notna().all()
    assert ins.groupby("campionato")["r_lega"].nunique().eq(1).all()
    assert ins["r_lega"].nunique() > 1


# --------------------------------------------------------- la valutazione
def test_il_percorso_di_valutazione_non_ristima_mai_la_dispersione():
    """Si valuta con la `r` PUBBLICATA, non con una migliore.

    Il divieto vale sul percorso di valutazione, **non sul modulo**:
    `dispersione_di_avvio` deve stimare `r`, ed e' il suo mestiere — misurare
    quanto quella pubblicata sia sbagliata all'avvio. Legare la guardia al file
    intero avrebbe punito il diagnostico, ed e' il difetto di forma che questo
    repository ha gia' pagato cinque volte: si sorveglia una **proprieta'**
    delle funzioni che valutano, non una sottostringa del sorgente.
    """
    import inspect

    for f in (VP.valutazione, VP.confronto_appaiato, VP.brier_per_linea,
              VP.valutazione_totale, VP.scomposizione_livello):
        src = inspect.getsource(f)
        assert "fit_r" not in src, f"{f.__name__} ristima `r`"
        assert "R_MAX" not in src

    # e il diagnostico, che invece DEVE stimarla
    assert "fit_r" in inspect.getsource(VP.dispersione_di_avvio)


def test_il_confronto_appaiato_e_sempre_clusterizzato(prev):
    """L'unita' indipendente e' la partita, non la riga."""
    a = VP.confronto_appaiato(prev, "shots")
    assert len(a)
    assert (a["n_cluster"] == a["n"] // 2).all()
    assert "cluster" in _codice(MODULO)


def test_la_valutazione_porta_due_denominatori(prev):
    """La correzione di E4: un confronto verticale fra campioni diversi."""
    v = VP.valutazione(prev, "shots").set_index("candidato")
    assert "crps_righe_comuni" in v.columns
    # `senza prior` non esiste alla prima data, quindi i due n differiscono
    assert int(v.loc["senza prior", "n"]) < int(v.loc[VP.SOGGETTO, "n"])
    assert int(v.loc[VP.SOGGETTO, "n_comuni"]) == int(v.loc["senza prior", "n"])


def test_il_crps_e_la_metrica_primaria_e_ordina_come_ci_si_aspetta(prev):
    """Su un candidato costante il CRPS dev'essere peggiore che sul modello:
    e' il controllo che la metrica non sia degenere su questo perimetro."""
    v = VP.valutazione(prev, "shots").set_index("candidato")
    assert VP.METRICA_PRIMARIA == "CRPS"
    assert v.loc[VP.SOGGETTO, "crps"] < v.loc["media campionato prec", "crps"]
    assert v.loc["media campionato prec", "sharpness"] == pytest.approx(0.0)


def test_il_verdetto_dichiara_quando_NON_conclude(prev):
    """Un delta sotto il proprio MDE non e' «l'effetto non c'e'»."""
    a = VP.confronto_appaiato(prev, "shots")
    d = VP.verdetto(a)
    assert d["criterio"] == VP.CRITERIO_LEGGIBILITA
    assert d["conclude"] == bool(d["delta_su_mde"] >= 1.0)
    if not d["conclude"]:
        assert "NON conclude" in d["perche"]


# ------------------------------------------------------------- il totale
def test_la_rotazione_a_partita_pretende_due_lati(prev):
    rotto = prev.drop(index=prev.index[0])
    with pytest.raises(ValueError, match="due lati"):
        VP.totale_del_perimetro(rotto, "shots")


def test_la_rotazione_pretende_esattamente_un_lato_di_casa(prev):
    rotto = prev.copy()
    rotto["is_home"] = 1
    with pytest.raises(ValueError, match="lato di casa"):
        VP.totale_del_perimetro(rotto, "shots")


def test_il_totale_e_la_somma_esatta_dei_due_lati(prev):
    """`E[X+Y] = E[X] + E[Y]` non richiede ipotesi: e' il risultato di T1."""
    t = VP.totale_del_perimetro(prev, "shots")
    assert len(t) == prev["matchId"].nunique()
    atteso = prev.groupby("matchId")["shots"].sum()
    assert np.allclose(t.set_index("matchId")["y_totale"].sort_index(),
                       atteso.sort_index())


def test_r_totale_non_si_eredita_da_r_per_lato(prev):
    """T1: `r_tot` vale 2,3-5,8 volte `r` per lato. Ereditarla sbaglierebbe le
    code, e prenderla da un altro campionato pure."""
    r_lato = VP.r_pubblicata(prev)
    r_tot = VP.r_totale_pubblicata("ITA-serie-a", "shots")
    assert r_tot > 2.0 * r_lato


# ------------------------------------------------------------ la taratura
def test_la_taratura_gira_su_transizioni_gia_concluse():
    """Non deve toccare la stagione in corso: e' la scala di riferimento, e
    prenderla dal caso da misurare sarebbe circolare."""
    t = VP.transizioni(["ITA-serie-a"])
    assert len(t) == len(config.SEASONS_STORICHE) - 1
    assert all(s in config.SEASONS_STORICHE for _, s in t)
    assert config.SEASON_CORRENTE not in [s for _, s in t]


def test_la_collocazione_riporta_un_rango_non_una_probabilita():
    c = VP.collocazione(2.0, [1.0, 3.0, 4.0, 5.0])
    assert c["rango"] == 2
    assert c["n_storiche"] == 4
    assert c["dentro_l_intervallo_storico"]
    assert "p_value" not in c and "p" not in c
    fuori = VP.collocazione(9.0, [1.0, 3.0, 4.0, 5.0])
    assert not fuori["dentro_l_intervallo_storico"]


# --------------------------------------------------------------- lo script
def test_lo_script_si_ferma_se_la_guardia_non_passa():
    """La separazione strutturale: non si pubblica una verifica su un file che
    non risulti anteriore e riproducibile."""
    src = SCRIPT.read_text(encoding="utf-8")
    assert "verifica_anteriorita" in src
    assert "return 1" in src
    assert "ripiego_ammesso" in src


def test_lo_script_non_ricalcola_cio_che_il_modulo_gia_calcola():
    """Il generatore serializza, non stima — come `pagina_v4` e
    `pagina_previsioni`. Un solo conto qui e report e modulo potrebbero
    divergere senza che nessuno se ne accorga."""
    codice = _codice(SCRIPT)
    for vietato in ("TeamModel", "minimize", "fit_r", "crps_conteggi"):
        assert vietato not in codice, f"{vietato} dentro lo script"


def test_i_limiti_stanno_accanto_ai_numeri():
    lim = VP.limiti()
    assert len(lim) >= 5
    testo = " ".join(lim).lower()
    for atteso in ("mde", "neopromosse", "vincolo 3", "giornata"):
        assert atteso in testo
