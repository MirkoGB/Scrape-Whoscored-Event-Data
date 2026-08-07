# -*- coding: utf-8 -*-
"""Test del blocco E3 — gol subiti, porta inviolata, voto e correlazione di linea.

Girano dai Parquet gia' costruiti e dalla cache del walk-forward: non rileggono i
1.889 CSV e non toccano la rete. Se i Parquet non ci sono, i test che ne hanno
bisogno si saltano invece di fallire.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from sot import config, difesa as DF, modificatore as MOD

RADICE = Path(__file__).resolve().parent.parent

TUTTE = all(config.team_match(season=s).is_file()
            for s in config.SEASONS_STORICHE)
serve_parquet = pytest.mark.skipif(
    not TUTTE, reason="le cinque stagioni non sono state costruite")


# --------------------------------------------------------------------------
# Il bersaglio parametrizzato NON deve aver spostato le Fasi 1-6
# --------------------------------------------------------------------------

def test_il_target_di_default_resta_i_tiri_in_porta():
    """Se il default cambiasse, ogni numero pubblicato cambierebbe in silenzio."""
    from sot import baselines as bl, model_team

    assert bl.TARGET == "sot"
    assert model_team.TeamModel().target == "sot"
    assert DF.TARGET == "gol_fatti", "E3 non deve modellare i tiri in porta"


@serve_parquet
def test_i_baseline_col_default_danno_gli_stessi_numeri_di_prima():
    """Il parametro `target` non deve cambiare cio' che i baseline calcolavano.

    Si ricalcola a mano cio' che facevano prima — media di `sot` — e si pretende
    l'uguaglianza esatta, non approssimata.
    """
    from sot import baselines as bl

    tm = pd.read_parquet(config.team_match(season=config.SEASON))
    train, test = tm.iloc[:400], tm.iloc[400:]

    assert np.allclose(bl.league_mean(train, test),
                       np.full(len(test), train["sot"].mean()))
    atteso = test["team"].map(train.groupby("team")["sot"].mean()).fillna(
        train["sot"].mean()).to_numpy()
    assert np.allclose(bl.team_mean(train, test), atteso)


# --------------------------------------------------------------------------
# Gli autogol, e il punteggio vero
# --------------------------------------------------------------------------

@serve_parquet
def test_il_punteggio_ricostruito_coincide_con_la_fonte():
    """Verifica falsificabile: o i due numeri coincidono o non coincidono.

    `matches.json` porta il punteggio **dichiarato**, non ricostruito dagli
    eventi: e' una fonte indipendente, ed e' cio' che rende questo un controllo e
    non una tautologia.
    """
    v = DF.verifica_punteggio()
    assert (v["gol_fatti_esatti"] == v["righe"]).all(), v.to_string()
    assert (v["gol_subiti_esatti"] == v["righe"]).all(), v.to_string()
    assert v["simmetria_ok"].all()


@serve_parquet
def test_ignorare_gli_autogol_sbaglia_e_di_quanto():
    """Il baseline dell'aggiustamento: senza autogol il punteggio NON torna.

    Senza questo, "760/760" potrebbe voler dire che l'aggiustamento non fa niente.
    """
    v = DF.verifica_punteggio()
    assert (v["senza_autogol_esatti"] < v["righe"]).all()
    assert int(v["autogol"].sum()) > 100, "cinque stagioni di autogol sono ~150"


@serve_parquet
def test_i_gol_subiti_sono_i_gol_fatti_dell_avversario():
    """La stessa grandezza vista dai due lati, riga per riga e non solo in somma."""
    g = DF.gol_squadra_partita(["2025-2026"])
    k = g.set_index(["matchId", "teamId"])["gol_fatti"]
    atteso = [k.get((m, o)) for m, o in zip(g["matchId"], g["opponentId"])]
    assert (g["gol_subiti"].to_numpy() == np.array(atteso)).all()


@serve_parquet
def test_il_denominatore_non_e_38():
    """L'Atalanta ha 35 partite nelle due stagioni bucate: si contano, mai assunte."""
    g = DF.gol_squadra_partita(["2021-2022"])
    n = g.groupby("team").size()
    assert n.min() == 35, n.min()
    assert n.max() == 38


# --------------------------------------------------------------------------
# E3.1 — il modello dei gol, rivalidato per conto suo
# --------------------------------------------------------------------------

@serve_parquet
def test_il_modello_dei_gol_batte_il_baseline_migliore():
    """E qui, a differenza dei tiri in porta, il margine e' fuori dal rumore."""
    c = DF.confronto_appaiato_gol().set_index("baseline")
    assert float(c.loc["media squadra + campo", "delta_mae"]) > 0
    assert float(c.loc["media squadra + campo", "t"]) > 3.0


@serve_parquet
def test_la_validazione_dei_gol_non_e_quella_dei_tiri():
    """La soglia Over e' dichiarata e diversa: 4.5 sui gol sarebbe assurda."""
    assert DF.LINEA_GOL == 1.5
    from sot import validate as V
    assert DF.LINEA_GOL not in V.LINES, (
        "se la linea dei gol coincidesse con una dei tiri, le due tabelle "
        "sarebbero confondibili")


@serve_parquet
def test_i_baseline_sono_mal_calibrati_e_il_modello_no():
    """E' l'argomento della Fase 4, e sui gol e' piu' netto, non meno."""
    v = DF.valutazione_gol().set_index("modello")
    assert abs(float(v.loc["Poisson ridge att/dif/casa", "calib_z_vs_1"])) < 3.0
    for b in ("media squadra + campo", "media squadra"):
        assert float(v.loc[b, "calib_z_vs_1"]) < -5.0, b


@serve_parquet
def test_la_forma_della_predittiva_regge():
    """Il PIT e' il controllo che la pendenza di calibrazione non fa."""
    f = DF.forma_predittiva_gol()
    assert f["pit"]["p_value"] > 0.05
    # Gli zeri sono la porta inviolata: se sbagliassero, E3.2 poggerebbe sul nulla.
    assert abs(f["quota_zeri_osservata"] - f["quota_zeri_attesa"]) < 0.03


# --------------------------------------------------------------------------
# E3.2 — la porta inviolata
# --------------------------------------------------------------------------

@serve_parquet
def test_la_porta_inviolata_e_calibrata_e_batte_le_frequenze():
    p = DF.porta_inviolata().set_index("candidato")
    mod = p.loc["modello, Poisson"]
    assert abs(float(mod["calib_slope"]) - 1.0) < 2 * float(mod["calib_se"])
    for b in ("frequenza storica della squadra", "frequenza di campionato"):
        assert float(mod["brier"]) < float(p.loc[b, "brier"]), b


@serve_parquet
def test_la_frequenza_grezza_e_degenere_ed_e_in_tabella():
    """Il baseline smorzato non e' un favore: quello grezzo emette `p = 0`.

    Se un domani si togliesse lo smorzamento "per semplicita'", il confronto
    diventerebbe sleale in favore del modello. Il test blocca il fatto.
    """
    p = DF.porta_inviolata().set_index("candidato")
    grezza = p.loc["frequenza storica GREZZA (degenere)"]
    smorzata = p.loc["frequenza storica della squadra"]
    assert float(grezza["logloss"]) > float(smorzata["logloss"])
    assert np.isnan(float(grezza["calib_slope"])), (
        "la pendenza non e' identificabile sotto separazione: deve essere nan")


def test_la_pendenza_logit_non_diverge():
    """Su probabilita' 0/1 Newton diverge: deve tornare `nan`, non 1e10."""
    rng = np.random.default_rng(0)
    y = (rng.random(500) < 0.3).astype(float)
    # Separazione quasi perfetta: p e' 0 o 1 esattamente dove y lo e'.
    p = np.where(y > 0, 1.0, 0.0)
    s, se = DF.pendenza_logit(y, p)
    assert np.isnan(s) or abs(s) < 100, (s, se)

    # ...e su dati ben calibrati deve invece dare 1.0, o non guarda niente.
    lin = rng.normal(0, 1, 20000)
    pp = 1 / (1 + np.exp(-lin))
    yy = (rng.random(20000) < pp).astype(float)
    s2, se2 = DF.pendenza_logit(yy, pp)
    assert abs(s2 - 1.0) < 4 * se2, (s2, se2)


def test_il_bonus_del_portiere_usa_le_due_voci_giuste():
    """`-1 * E[gol] + 1 * P(0)`, e i coefficienti vengono da `lega`, non a mano."""
    from sot import lega as L
    lam = np.array([0.5, 1.0, 2.0])
    atteso = (L.BONUS["gol_subiti"] * lam
              + L.BONUS["porta_inviolata"] * np.exp(-lam))
    assert np.allclose(DF.bonus_difensivo_portiere(lam), atteso)
    # Monotono decrescente: piu' gol attesi, meno bonus. Se salisse sarebbe
    # un segno invertito da qualche parte.
    b = DF.bonus_difensivo_portiere(np.array([0.5, 1.0, 1.5, 2.0]))
    assert (np.diff(b) < 0).all()


# --------------------------------------------------------------------------
# E3.3 — il voto della linea
# --------------------------------------------------------------------------

@serve_parquet
def test_il_voto_del_difensore_scende_con_la_debolezza_difensiva():
    """L'effetto che giustifica il modificatore, col suo segno."""
    p = DF.pendenza_voto().set_index(["ruolo", "regressore"])
    d = p.loc[("d", "lam_subiti (previsto)")]
    assert float(d["pendenza"]) < 0
    assert abs(float(d["t"])) > 5


@serve_parquet
def test_il_portiere_va_nel_VERSO_OPPOSTO_e_non_e_un_errore():
    """Il risultato che non era previsto, bloccato perche' non venga "corretto".

    Il portiere e' giudicato **rispetto all'attesa**: su una difesa debole para di
    piu' e prende voti base piu' alti, ma a gol subiti osservati il voto scende.
    Le due cose insieme sono la firma di quel meccanismo, e un test che pretende
    entrambi i segni impedisce di "sistemarne" uno solo.
    """
    p = DF.pendenza_voto().set_index(["ruolo", "regressore"])
    assert float(p.loc[("p", "lam_subiti (previsto)"), "pendenza"]) > 0
    assert float(p.loc[("p", "gol_subiti (osservato)"), "pendenza"]) < 0
    assert float(p.loc[("d", "lam_subiti (previsto)"), "pendenza"]) < 0


# --------------------------------------------------------------------------
# E3.4 — la correlazione dentro la linea
# --------------------------------------------------------------------------

def test_rho_zero_riproduce_il_modificatore_pubblicato():
    """Bit per bit: il parametro nuovo non deve spostare nulla di gia' pubblicato."""
    mu = np.full(5, 6.1)
    sd = np.full(5, 0.55)
    pv = np.full(5, 0.85)
    a = MOD.simula_linea(mu, sd, pv)
    b = MOD.simula_linea(mu, sd, pv, rho=0.0)
    assert np.array_equal(a, b)


def test_rho_aumenta_la_varianza_della_media_di_linea():
    """La correlazione deve fare cio' per cui e' stata introdotta.

    Si controlla contro la **forma chiusa**, non contro una soglia a occhio: per
    `n` normali equicorrelate la deviazione standard della media vale
    `sqrt((1 + (n-1) rho) / n)`. Una soglia arbitraria avrebbe verificato il mio
    numero preferito invece della proprieta'.
    """
    rng = np.random.default_rng(0)
    n, rip = 5, 200000
    for rho in (0.0, 0.3, 0.6):
        comune = rng.normal(0, 1, (rip, 1))
        proprio = rng.normal(0, 1, (rip, n))
        z = np.sqrt(rho) * comune + np.sqrt(1 - rho) * proprio
        atteso = np.sqrt((1 + (n - 1) * rho) / n)
        assert abs(z.mean(axis=1).std() - atteso) < 0.01, (rho, atteso)


def test_rho_fuori_intervallo_e_rifiutato():
    mu, sd, pv = np.full(4, 6.0), np.full(4, 0.5), np.full(4, 0.9)
    for cattivo in (-0.1, 1.0, 1.5):
        with pytest.raises(ValueError):
            MOD.simula_linea(mu, sd, pv, rho=cattivo)


@serve_parquet
def test_la_correlazione_non_e_composizione_di_rosa():
    """Al netto del giocatore la correlazione deve restare: e' l'argomento di E3.4.

    Se crollasse, sarebbe "le difese forti hanno difensori bravi" — gia' dentro
    `mu` — e iniettarla nel simulatore la conterebbe due volte.
    """
    c = DF.correlazione_linea().set_index(["insieme", "voto"])
    grezza = float(c.loc[("linea intera (p+d)", "grezzo"), "icc"])
    netta = float(c.loc[("linea intera (p+d)", "al netto del giocatore"), "icc"])
    assert netta > 0.15
    assert netta > 0.8 * grezza


@serve_parquet
def test_il_segno_dell_effetto_correlazione_si_inverte():
    """Il punto di E3.4: con fasce a scalini il segno NON e' costante.

    Un test che pretendesse solo "positivo" avrebbe consacrato la meta' della
    griglia che si era guardata per prima.
    """
    e = DF.effetto_correlazione()
    assert (e["delta_stagione"] > 0).any(), "sotto le soglie deve aiutare"
    assert (e["delta_stagione"] < 0).any(), "dentro l'ultima fascia deve nuocere"
    basso = e[e["voto_medio_linea"] <= 6.0]["delta_stagione"].mean()
    alto = e[e["voto_medio_linea"] >= 7.0]["delta_stagione"].mean()
    assert basso > 0 > alto, (basso, alto)


# --------------------------------------------------------------------------
# La verifica finale, e il fatto che sia negativa
# --------------------------------------------------------------------------

@serve_parquet
def test_la_difesa_di_squadra_non_migliora_i_portieri():
    """Il risultato negativo del blocco, bloccato perche' non venga "sistemato".

    Vale con **entrambe** le forme della forza difensiva: se dipendesse da quella
    scelta, sarebbe la scelta il risultato e non la difesa.
    """
    s = DF.spearman_portieri()
    p = s[s["ruolo"] == "p"].set_index("candidato")
    base = float(p.loc["modello d'asta", "spearman"])
    for modo in ("ultima stagione", "tutte le stagioni"):
        assert float(p.loc[f"modello d'asta + difesa E3 ({modo})",
                           "spearman"]) < base, modo


@serve_parquet
def test_i_numeri_di_riferimento_del_modello_d_asta_sono_riprodotti():
    """La precisione 0 sui portieri e 0,667 del FVM sono quelle gia' pubblicate.

    Senza questo controllo il confronto sarebbe con numeri ricalcolati in modo
    leggermente diverso, e la differenza sembrerebbe un risultato.
    """
    s = DF.spearman_portieri()
    p = s[s["ruolo"] == "p"].set_index("candidato")
    assert float(p.loc["modello d'asta", "precisione_top"]) == 0.0
    assert abs(float(p.loc["FVM della fonte (CONTAMINATO)", "precisione_top"]) - 2 / 3) < 0.01
    # ...e con il concorrente LEALE quel divario sparisce: QI sta a un pescaggio
    # dal modello, cioe' dentro la risoluzione della metrica (3 posti x 4
    # stagioni = passi da 1/12). Vedi il test sui pari merito qui sotto.
    assert float(p.loc["quotazione iniziale QI", "precisione_top"]) <= 1 / 12 + 1e-9


@serve_parquet
def test_la_premessa_del_blocco_e_falsa_sui_quotati():
    """La maggioranza dei portieri a listino non gioca **nemmeno una partita**.

    E' il fatto che spiega l'esito, ed e' l'opposto della premessa da cui il
    blocco era partito.
    """
    pr = DF.premessa_portieri().set_index("soglia_presenze_attese")
    assert float(pr.loc[0, "quota_mai_in_campo"]) > 0.3
    # Fra i probabili titolari le presenze SONO risolte...
    assert float(pr.loc[20, "quota_mai_in_campo"]) < 0.05
    # ...e li' nessuno dei NOSTRI candidati sa piu' niente.
    assert float(pr.loc[20, "spearman_modello"]) < 0.3
    assert float(pr.loc[20, "spearman_sole_presenze_attese"]) < 0.1


@serve_parquet
def test_il_vantaggio_sui_portieri_regge_con_qi_ma_si_riduce():
    """La correzione della domanda aperta n. 1, bloccata nei due sensi.

    Il numero che il blocco citava (0,700 del FVM) era misurato su un concorrente
    **contaminato**: la pagina archiviata del FVM si muove durante la stagione
    (`quotazioni.orologio()`). Rifatto con QI, che e' pulito e noto prima
    dell'asta, il vantaggio **regge** — quindi la risposta non era solo "sapeva
    come era andata" — ma **si riduce di molto**, quindi buona parte di quel
    numero era esattamente quello.

    Il test pretende **entrambe** le cose, cosi' che non si possa raccontare solo
    la meta' comoda in nessuna delle due direzioni.
    """
    pr = DF.premessa_portieri().set_index("soglia_presenze_attese")
    qi = float(pr.loc[20, "spearman_qi"])
    fvm = float(pr.loc[20, "spearman_fvm_CONTAMINATO"])
    assert qi > float(pr.loc[20, "spearman_modello"]), "il vantaggio deve reggere"
    assert qi > float(pr.loc[20, "spearman_sole_presenze_attese"])
    assert qi < 0.6 * fvm, "e deve ridursi: gran parte del 0,700 era contaminazione"


@serve_parquet
def test_sui_portieri_la_precisione_non_ha_risoluzione():
    """Perche' il confronto QI-contro-modello sulla precisione non si puo' fare.

    QI e' un prezzo **intero**, e fra i portieri ci sono pari merito **al confine
    dei primi tre in due stagioni su quattro** (2024-25 ha 15 e 15 al terzo e
    quarto posto, 2025-26 ha quattro 16 per tre posti): li' quali tre entrano lo
    decide il sorteggio che scioglie i pari, non la quotazione. Con 3 posti per 4
    stagioni la metrica ha passi da 1/12, e le due implementazioni del repository
    — `modello_asta` e `difesa` — sciolgono i pari in modo diverso e danno 0,000 e
    0,083.

    **Non e' un difetto da appianare: e' la risoluzione della metrica.** Il test
    lo blocca cosi' che nessuno legga quella differenza come un risultato.
    """
    from sot import modello_asta as MA

    wf = MA.walkforward()
    ambigue = 0
    for _, g in wf[wf["ruolo"] == "p"].groupby("stagione_prevista"):
        x = pd.to_numeric(g["b_qi"], errors="coerce").dropna().nlargest(4)
        ambigue += int(x.iloc[2] == x.iloc[3])
    assert ambigue >= 2, (
        "senza pari merito al confine questo test non descrive piu' i dati")

    a = MA.precisione_top(wf)
    a = float(a[(a["ruolo"] == "p")
                & (a["candidato"] == "quotazione iniziale QI")]["precisione"].mean())
    s = DF.spearman_portieri()
    b = float(s[(s["ruolo"] == "p")
                & (s["candidato"] == "quotazione iniziale QI")]["precisione_top"].iloc[0])
    assert abs(a - b) <= 1 / 12 + 1e-9, (a, b)


@serve_parquet
def test_il_fvm_resta_in_tabella_e_resta_marcato():
    """Un errore di questo progetto non si cancella: si marca e resta in vista.

    Se qualcuno togliesse la colonna o le levasse il marchio, il confronto
    tornerebbe a sembrare leale.
    """
    from sot import quotazioni as Q

    assert "spearman_fvm_CONTAMINATO" in DF.premessa_portieri().columns
    s = DF.spearman_portieri()
    nomi = set(s["candidato"])
    assert "FVM della fonte (CONTAMINATO)" in nomi
    assert "FVM della fonte" not in nomi
    assert "fvm_classic" in Q.COLONNE_CONTAMINATE


# --------------------------------------------------------------------------
# E3.5 — la coda: l'ipotesi della compensazione, e la sua confutazione
# --------------------------------------------------------------------------

@serve_parquet
def test_e35_riproduce_la_pendenza_di_e33():
    """Le componenti stanno sulla stessa popolazione di E3.3, non su un'altra.

    Senza questo controllo, una differenza fra E3.3 ed E3.5 potrebbe essere un
    risultato oppure un campione diverso, e non si saprebbe quale delle due.
    """
    a = DF.pendenza_voto().set_index(["ruolo", "regressore"])
    b = DF.pendenza_componenti().set_index(["ruolo", "componente"])
    for ruolo in ("p", "d"):
        assert abs(float(a.loc[(ruolo, "lam_subiti (previsto)"), "pendenza"])
                   - float(b.loc[(ruolo, "comp_voto"), "pendenza"])) < 1e-9
        assert (int(a.loc[(ruolo, "lam_subiti (previsto)"), "righe"])
                == int(b.loc[(ruolo, "comp_voto"), "righe"]))


@serve_parquet
def test_il_difensore_non_ha_la_componente_del_malus():
    """Zero **per regolamento**, non per approssimazione.

    E' meta' del meccanismo di E3.5: il difensore ha un canale, il portiere due.
    Se un giorno questa componente diventasse non nulla sui difensori, il barema
    di lega sarebbe cambiato e il test deve accorgersene.
    """
    from sot import lega as L

    assert "gol_subiti" in L.SOLO_PORTIERE
    assert "porta_inviolata" in L.SOLO_PORTIERE
    b = DF.pendenza_componenti().set_index(["ruolo", "componente"])
    assert float(b.loc[("d", "comp_bonus"), "pendenza"]) == 0.0
    # e quindi netto e voto coincidono sul difensore
    assert (float(b.loc[("d", "comp_netto"), "pendenza"])
            == float(b.loc[("d", "comp_voto"), "pendenza"]))


@serve_parquet
def test_la_compensazione_non_regge_e_la_soglia_e_dichiarata():
    """Il risultato della coda: il netto NON e' piatto.

    La soglia e' una costante letterale del modulo, non un numero ricavato dai
    dati: si controlla che sia dichiarata **e** che il verdetto la usi.
    """
    assert DF.SOGLIA_COMPENSAZIONE == 1 / 3
    out = DF.pendenza_componenti()
    quota = out.attrs["quota_malus_superstite"]
    assert quota > DF.SOGLIA_COMPENSAZIONE
    assert out.attrs["compensazione"] is False
    # il netto ha lo stesso segno del malus e non e' distinguibile da esso
    p = out[out["ruolo"] == "p"].set_index("componente")
    assert float(p.loc["comp_netto", "pendenza"]) < 0
    assert abs(float(p.loc["comp_netto", "t"])) > 5


@serve_parquet
def test_i_totali_non_sono_leggibili_come_compensazione():
    """La trappola che questa coda ha evitato, bloccata perche' non ritorni.

    Sui totali di stagione le due componenti risultano correlate negativamente
    **attraverso le presenze**, e sembrerebbe la conferma cercata. Sulle medie per
    presenza — la grandezza giusta — la correlazione svanisce. Il test pretende
    entrambe le cose, cosi' che citare la prima da sola sia un errore visibile.
    """
    c = DF.correlazione_componenti().set_index("pavimento_presenze")
    assert float(c.loc[10, "corr_totali"]) < -0.2
    assert abs(float(c.loc[10, "corr_medie"])) < 0.1
    assert abs(float(c.loc[19, "corr_medie"])) < 0.1


@serve_parquet
def test_collegare_entrambi_i_lati_non_recupera_nemmeno_con_l_oracolo():
    """La conseguenza operativa dell'ipotesi, misurata e negativa.

    Se recuperasse, l'ipotesi avrebbe avuto ragione in modo utile pur essendo
    sbagliata nel meccanismo. Non recupera, e **nemmeno con la pendenza stimata
    sulla stagione bersaglio**: quindi non e' un problema di stima.
    """
    d = DF.collegamento_due_lati()
    p = d[d["soglia_presenze_attese"] == 0].set_index("candidato")["spearman"]
    base = float(p["modello d'asta (nessun lato)"])
    assert float(p["entrambi i lati"]) < base
    assert float(p["entrambi i lati (pendenza ORACOLO)"]) < base
    # e il FVM resta davanti a tutti, che e' la domanda che il blocco lascia
    assert float(p["FVM della fonte (CONTAMINATO)"]) > base


@serve_parquet
def test_la_difesa_di_e3_stima_meglio_di_cio_che_ha_sostituito():
    """L'esclusione che la coda aggiunge, ed e' il suo contributo positivo.

    La spiegazione comoda — "la difesa e' stimata male" — e' falsa: contro il
    bonus difensivo realmente realizzato, E3 batte il bonus storico del portiere
    su MAE **e** su correlazione. Il peggioramento dell'ordinamento va spiegato
    altrove, e non lo e' ancora.
    """
    q = DF.qualita_componente_difensiva().set_index("stimatore")
    e3 = q.loc["difesa E3 (modello di squadra)"]
    sto = q.loc["bonus storico del portiere (il modello d'asta)"]
    assert float(e3["mae"]) < float(sto["mae"])
    assert float(e3["corr"]) > float(sto["corr"])
    # I due denominatori sono diversi ED E' VOLUTO: restringere la correlazione
    # con le presenze ai soli titolari troncherebbe la variabile in questione.
    assert int(e3["portieri_tutti"]) > int(e3["portieri_qualita"])


@serve_parquet
def test_il_malus_e_alimentato_dalla_fonte_dei_voti():
    """Quale delle due fonti produce il malus, dichiarato e verificato.

    `voti_difensori` sovrascrive `gol_subiti` con i gol di squadra ricomposti da
    WhoScored: stesso nome, altra grandezza. Il malus deve venire dalla fonte
    definitoria — quella che ha prodotto i `punti_osservati` — e le due devono
    divergere su poche righe ma **non zero**, altrimenti la distinzione sarebbe
    finta e nessuno se ne accorgerebbe piu'.
    """
    assert DF.FONTE_MALUS == "voti"
    c = DF.componenti_portiere()
    assert "gol_subiti_voti" in c.columns
    n = c.attrs["righe_gol_subiti_discordi"]
    assert 0 < n < 0.05 * int((c["ruolo"] == "p").sum())


# --------------------------------------------------------------------------
# Disciplina del modulo
# --------------------------------------------------------------------------

def test_nessuna_soglia_ricavata_dal_campione():
    """Vietato scegliere una soglia guardando i dati su cui poi si valuta.

    Stessa guardia di E1 ed E2, sull'AST e non sul testo.
    """
    albero = ast.parse((RADICE / "sot" / "difesa.py").read_text(encoding="utf-8"))
    vietati = {"argmax", "idxmax", "idxmin", "argmin"}
    for nodo in ast.walk(albero):
        if isinstance(nodo, ast.Attribute) and nodo.attr in vietati:
            raise AssertionError(f"`{nodo.attr}` in difesa.py: soglia adattata?")


def test_e3_non_scrive_sotto_data_tranne_la_propria_cache():
    """L'unico Parquet scritto e' la cache del walk-forward, ed e' rigenerabile."""
    testo = (RADICE / "sot" / "difesa.py").read_text(encoding="utf-8")
    scritture = re.findall(r"\.to_parquet\(|\.to_csv\(", testo)
    assert len(scritture) == 1, scritture
    assert "CACHE" in testo


def test_e3_non_e_importato_dagli_script_delle_fasi_1_6():
    """Nessuna proiezione pubblicata deve dipendere da questo blocco."""
    for nome in ("run_phase1.py", "run_phase2.py", "run_phase3.py",
                 "run_phase4.py", "run_phase5.py"):
        p = RADICE / "scripts" / nome
        if not p.is_file():
            continue
        testo = p.read_text(encoding="utf-8")
        assert not re.search(r"^\s*(from|import).*\bdifesa\b", testo, re.M), nome
