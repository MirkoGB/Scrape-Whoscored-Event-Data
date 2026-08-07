# -*- coding: utf-8 -*-
"""Test del blocco E2 — presenze, squalifiche, strato distinta.

Girano dai Parquet gia' costruiti: non rileggono i 1.889 CSV e non toccano la
rete. Se i Parquet non ci sono, i test che ne hanno bisogno si saltano invece di
fallire.
"""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd
import pytest

from sot import (config, distinta as D, impiego as IM, minutes,
                 squalifiche as SQ)

RADICE = Path(__file__).resolve().parent.parent

TUTTE = all(config.player_match(season=s).is_file()
            for s in config.SEASONS_STORICHE)
serve_parquet = pytest.mark.skipif(
    not TUTTE, reason="le cinque stagioni non sono state costruite")


# --------------------------------------------------------------------------
# Le costanti sono DICHIARATE, non ricavate dai dati (vincolo 1)
# --------------------------------------------------------------------------

MODULI_CON_SOGLIE = ("sot/squalifiche.py", "sot/distinta.py", "sot/impiego.py")


@pytest.mark.parametrize("modulo", MODULI_CON_SOGLIE)
def test_nessuna_soglia_ricavata_dal_campione(modulo):
    """Vietato scegliere una soglia guardando i dati su cui poi si valuta.

    E' la stessa guardia che E1 ha sul proprio modulo. `argmax`/`idxmax`/
    `quantile` qui vorrebbero dire che una costante della regola e' stata
    adattata al campione, e sarebbe il vincolo 1 violato.

    La guardia legge l'**AST**, non il testo. Cercare la stringa nel sorgente e'
    gia' costato un falso positivo a questo progetto (`test_stabilita_rilevazione`
    dichiarava colpevole `run_voti_fantacalcio.py` perche' *nominava* il modulo in
    prosa): qui i nomi vietati compaiono nelle docstring proprio per dire che sono
    vietati, e una guardia testuale li troverebbe li'.
    """
    import ast

    albero = ast.parse((RADICE / modulo).read_text(encoding="utf-8"))
    vietati = {"argmax", "idxmax", "quantile"}
    trovati = [n.attr for n in ast.walk(albero)
               if isinstance(n, ast.Attribute) and n.attr in vietati]
    trovati += [n.id for n in ast.walk(albero)
                if isinstance(n, ast.Name) and n.id in vietati]
    assert not trovati, f"{modulo} ricava una soglia dai dati: {trovati}"


def test_le_costanti_della_regola_sono_letterali():
    """I numeri della regola sono quelli del regolamento, non del campione."""
    assert SQ.GIALLI_PER_SQUALIFICA == 5
    assert SQ.GIORNATE_PER_ROSSO == 1
    assert IM.PAVIMENTO == 0
    assert IM.PAVIMENTI_ACCANTO[0] == IM.PAVIMENTO


def test_le_espulsioni_sono_le_stesse_dei_minuti():
    """Se la fonte aggiungesse un `cardType`, minuti e squalifiche devono
    cambiare insieme: due liste separate divergerebbero in silenzio."""
    assert set(SQ.ESPULSIONI) == set(minutes.SENDING_OFF)


# --------------------------------------------------------------------------
# Le squalifiche
# --------------------------------------------------------------------------

@serve_parquet
def test_lo_staff_non_prende_squalifiche():
    """`playerId` nullo e' allenatore o staff e non e' un giocatore.

    Il filtro sta in un punto solo (`cartellini`) proprio perche' due strade —
    cumulo ed espulsioni — potrebbero applicarlo in modo diverso.
    """
    c = SQ.cartellini(config.SEASON)
    assert c["playerId"].notna().all()
    assert (c["playerId"] > 0).all()


@serve_parquet
def test_il_doppio_giallo_non_conta_due_volte():
    """Ogni `SecondYellow` ha un `Yellow` accanto, e quel giallo non entra nel
    cumulo delle cinque: senza questa regola varrebbe due volte."""
    ev = SQ.eventi_disciplinari(config.SEASON)
    doppi = ev[ev["doppio_giallo"] > 0]
    assert len(doppi), "nessun doppio giallo: il test non sta guardando niente"
    # `gialli` e' gia' al netto, `gialli_grezzi` no.
    assert (doppi["gialli"] == doppi["gialli_grezzi"] - doppi["doppio_giallo"]).all()
    assert (doppi["gialli"] >= 0).all()


@serve_parquet
def test_un_espulso_dalla_panchina_e_comunque_squalificato():
    """Il taglio delle squalifiche NON e' quello dei minuti.

    CLAUDE.md dice che 85 espulsioni tolgono solo 65 uomini dal campo. Per le
    squalifiche contano tutte quelle a giocatori, anche a chi era gia' uscito o
    in panchina: e' l'errore piu' facile da fare qui.
    """
    ev = SQ.eventi_disciplinari(config.SEASON)
    pm = pd.read_parquet(config.player_match(season=config.SEASON))
    zero = set(zip(pm.loc[pm["minutes"] == 0, "teamId"],
                   pm.loc[pm["minutes"] == 0, "playerId"],
                   pm.loc[pm["minutes"] == 0, "matchId"]))
    espulsi = ev[ev["espulso"] == 1]
    dalla_panchina = [(t, p, m) in zero for t, p, m
                      in zip(espulsi["teamId"], espulsi["playerId"],
                             espulsi["matchId"])]
    sq = SQ.squalifiche(config.SEASON)
    # Chiunque sia stato espulso ha una squalifica, panchinari inclusi.
    for t, p in espulsi[["teamId", "playerId"]].drop_duplicates().itertuples(index=False):
        assert len(sq[(sq["teamId"] == t) & (sq["playerId"] == p)]), (t, p)
    assert isinstance(dalla_panchina, list)


@serve_parquet
def test_la_squalifica_si_verifica_contro_le_presenze():
    """La verifica forte: chi e' squalificato non compare fra i convocati.

    Con il baseline accanto, che e' la meta' del test: senza, il 96% non
    significherebbe niente.
    """
    for st in config.SEASONS_STORICHE:
        v = SQ.verifica(st)
        assert v["accordo_calendario_intero"] > 0.95, (st, v)
        assert v["baseline_assenza"] < 0.20, (st, v)
        # E il guadagno sul baseline dev'essere grande, non solo positivo.
        assert v["accordo_calendario_intero"] - v["baseline_assenza"] > 0.7


@serve_parquet
def test_il_residuo_della_verifica_e_spiegato_dalle_partite_mancanti():
    """Il calo di accordo nelle prime due stagioni ha una causa NOTA.

    Se un domani il residuo crescesse su una stagione completa, questo test
    fallisce e costringe a cercare un secondo meccanismo invece di attribuirlo
    di nuovo alle partite mancanti.
    """
    for st in config.SEASONS_STORICHE:
        v = SQ.verifica(st)
        if v["quota_righe_squadra_bucata"] == 0:
            assert v["errori_su_squadra_bucata"] == 0
        elif v["errori"] >= 10:
            # Gli errori devono concentrarsi sulle squadre bucate piu' di quanto
            # la loro quota di righe giustificherebbe.
            quota_err = v["errori_su_squadra_bucata"] / v["errori"]
            assert quota_err > v["quota_righe_squadra_bucata"], (st, v)


@serve_parquet
def test_le_squalifiche_peggiorano_ed_e_il_risultato():
    """Il risultato negativo e' bloccato: non va "sistemato".

    Se una sessione futura ritoccasse la sottrazione finche' il numero diventa
    positivo, starebbe rifacendo l'errore che le Fasi 2 e 3 servivano a
    escludere. Il meccanismo, non solo il segno, e' verificato.
    """
    d = SQ.divario_oracolo()
    oracolo = d[d["variante"].str.contains("ORACOLO dei cartellini")]
    assert float(oracolo["divario_chiuso"].iloc[0]) < 0

    p = SQ.perche_peggiora()
    squal = p[p["gruppo"].str.startswith("squalificato")].iloc[0]
    mai = p[p["gruppo"] == "mai squalificato"].iloc[0]
    # Chi viene squalificato e' SOTTOSTIMATO, chi no e' sovrastimato: e' la
    # ragione per cui sottrarre allontana.
    assert squal["bias"] < 0 < mai["bias"]


@serve_parquet
def test_il_pavimento_del_divario_riproduce_i_numeri_pubblicati():
    """61,4 e 5,6 sono gia' pubblicati: se si muovessero, il campione e'
    cambiato e la percentuale non sarebbe piu' confrontabile con niente."""
    d = SQ.divario_oracolo().set_index("variante")
    assert abs(float(d.loc["modello completo", "mae"]) - 61.4) < 0.1
    pav = [i for i in d.index if "il pavimento" in i][0]
    assert abs(float(d.loc[pav, "mae"]) - 5.6) < 0.1


# --------------------------------------------------------------------------
# Lo strato distinta
# --------------------------------------------------------------------------

@serve_parquet
def test_la_maglia_c_e_su_tutte_le_distinte():
    """Il costo quasi nullo poggia su questo: se `JerseyNumber` mancasse su una
    parte delle righe, la feature avrebbe un pattern di assenza da spiegare."""
    for st in config.SEASONS_STORICHE:
        d = D.distinte(st)
        fs = d[d["tipo"] == "FormationSet"]
        assert fs["jersey"].notna().all(), st
        assert fs["role_code"].notna().all(), st


@serve_parquet
def test_la_chiave_e_la_tripla_e_i_numeri_multipli_sono_contati():
    """Non si aggrega alla moda su piu' stagioni: distruggerebbe il segnale."""
    nm = D.numero_maglia_multi()
    assert not nm.duplicated(["stagione", "teamId", "playerId"]).any()
    assert int((nm["n_numeri"] > 1).sum()) > 0, "il conteggio non guarda niente"


@serve_parquet
def test_la_prima_distinta_non_usa_i_minuti():
    """La regola per le triple con piu' numeri e' "prima distinta".

    La moda pesata sui minuti userebbe i minuti della stagione per costruire un
    predittore il cui pregio e' di esistere PRIMA di quei minuti. Il test
    verifica che il numero scelto sia quello della partita a indice minimo.
    """
    st = config.SEASON
    nm = D.numero_maglia(st)
    d = D.distinte(st)
    d = d[d["tipo"] == "FormationSet"].merge(
        D._indice_partite(st), on=["matchId", "teamId"], how="inner")
    multi = nm[nm["n_numeri"] > 1]
    for r in multi.itertuples(index=False):
        sub = d[(d["teamId"] == r.teamId) & (d["playerId"] == r.playerId)]
        prima = sub.loc[sub["team_match_idx"].idxmin(), "jersey"]
        assert r.jersey == prima, (r.playerId, r.jersey, prima)


@serve_parquet
def test_la_maglia_1_e_portiere_e_la_12_no():
    """La fascia dichiarata e' eterogenea, e NON e' stata ridefinita.

    Se un domani qualcuno "sistemasse" `portiere_classico` restringendola alla
    sola 1 perche' i numeri tornano meglio, starebbe adattando la partizione al
    campione. Il test blocca sia il fatto sia la partizione.
    """
    # La partizione applica la PRIMA regola che matcha: la 12 ricade anche in
    # `undici_25`, ed e' l'ordine a deciderlo. Si verifica l'esito, non l'insieme
    # delle regole compatibili.
    assert D.fascia_maglia(12) == "portiere_classico", "la 12 e' uscita dalla fascia"
    assert D.fascia_maglia(22) == "portiere_classico"
    assert D.fascia_maglia(1) == "portiere_classico"
    c = D.collinearita_per_numero().set_index("jersey")
    assert c.loc[1, "GK"] == 1.0
    assert c.loc[12, "GK"] < 0.5
    assert c.loc[22, "GK"] < 0.5


@serve_parquet
def test_il_capitano_e_sfasato_di_una_stagione():
    """Lo sfasamento e' parte della DEFINIZIONE, non un aggiustamento a valle.

    La fascia di t contro le presenze di t misurerebbe una conseguenza del
    giocare e la chiamerebbe causa.
    """
    c = D.capitano_sfasato()
    assert "capitano_prec" in c.columns
    # Chi non c'era nel club l'anno prima ha NaN, non zero: sono due
    # affermazioni diverse.
    assert c.loc[~c["stesso_club_anno_prima"], "capitano_prec"].isna().all()


@serve_parquet
def test_il_ruolo_e_una_serie_non_una_costante():
    """Lo script R teneva la prima occorrenza; E2 vuole i cambi."""
    rs = D.ruolo_serie(config.SEASON)
    assert int((rs["ruoli_distinti"] > 1).sum()) > 0
    # Il codice 5 non e' un ruolo e non deve entrare nella variabilita'.
    assert not (rs["ruolo_modale"] == 5).any()


# --------------------------------------------------------------------------
# Il modello d'impiego
# --------------------------------------------------------------------------

@serve_parquet
def test_tutte_le_feature_sono_sfasate():
    """Nessuna colonna in contemporanea: sarebbe il vincolo 1 per distrazione."""
    for f in IM.FEATURE_CON_MAGLIA:
        assert f.endswith("_prec"), f
    tab = IM.tabella_predittori()
    for f in IM.FEATURE_CON_MAGLIA:
        assert f in tab.columns, f


@serve_parquet
def test_la_maglia_della_stagione_bersaglio_sarebbe_leakage():
    """Il difetto che rende inutilizzabile la versione interessante.

    La sola ESISTENZA di una distinta nella stagione bersaglio separa quasi
    perfettamente chi gioca da chi no. Il test lo verifica invece di lasciarlo
    come affermazione del report — ed e' anche la guardia contro chi in futuro
    fosse tentato di usare il numero contemporaneo.
    """
    from sot import modello_asta as MA, multistagione as MS
    nm = D.numero_maglia_multi()
    mappa = MS.aggancio_giocatori()["mappa"]
    nm = nm.merge(mappa[["stagione", "teamId_ws", "playerId_ws", "giocatore_id_fc"]],
                  left_on=["stagione", "teamId", "playerId"],
                  right_on=["stagione", "teamId_ws", "playerId_ws"], how="inner")
    wf = MA.walkforward()
    for st in MA.STAGIONI_VALUTABILI:
        sub = wf[wf["stagione_prevista"] == st]
        ids = set(nm.loc[nm["stagione"] == st, "giocatore_id_fc"])
        ha = sub["giocatore_id"].isin(ids)
        assert sub.loc[ha, "presenze_osservate"].mean() > 15
        assert sub.loc[~ha, "presenze_osservate"].mean() < 1


@serve_parquet
def test_la_stima_guarda_solo_il_passato():
    """Guastare una stagione tarda non deve cambiare le previsioni precedenti.

    E' il test di leakage nella forma che il progetto usa gia' in
    `test_validate.py`: si rompe il futuro e si pretende che il passato non se
    ne accorga.
    """
    from sot import fantapunti as FP
    ps = FP.per_giocatore_stagione()
    oss = ps[["stagione", "giocatore_id", "presenze"]]
    tab = IM.tabella_predittori()

    prima = IM.previsione_presenze("2023-2024", tab, oss)
    guasto = oss.copy()
    tardi = guasto["stagione"] >= "2024-2025"
    guasto.loc[tardi, "presenze"] = 0.0
    dopo = IM.previsione_presenze("2023-2024", tab, oss=guasto)
    assert (prima.to_numpy() == dopo.to_numpy()).all(), "il futuro entra nel passato"

    # ...e guastare il passato invece DEVE cambiarle, o il test non guarda niente.
    guasto2 = oss.copy()
    guasto2.loc[guasto2["stagione"] < "2023-2024", "presenze"] = 0.0
    assert not (IM.previsione_presenze("2023-2024", tab, oss=guasto2).to_numpy()
                == prima.to_numpy()).all()


@serve_parquet
def test_il_pavimento_zero_e_il_migliore_ed_e_misurato():
    """La decisione sul pavimento non e' un'opinione: e' una tabella.

    Se un domani qualcuno alzasse il pavimento "per pulizia", questo test
    fallisce e mostra il costo.
    """
    s = IM.sensibilita_pavimento()
    s = s[s["variante"] == "impiego (senza maglia)"].set_index("pavimento")
    assert float(s.loc[0, "divario_chiuso_pct"]) > float(s.loc[450, "divario_chiuso_pct"])
    assert float(s.loc[450, "divario_chiuso_pct"]) > float(s.loc[1800, "divario_chiuso_pct"])


@serve_parquet
def test_il_risultato_e_negativo_e_la_potenza_e_dichiarata():
    """Il guadagno sta sotto l'MDE: e' la lettura che 6D ha insegnato.

    "Nessun effetto" e "il test non vede" sono due conclusioni diverse, e senza
    l'MDE non si sa quale delle due si e' ottenuta.
    """
    v = IM.valutazione()
    t = v["tabella"].set_index("variante")
    quota = float(t.loc["impiego (senza maglia)", "divario_chiuso_pct"])
    assert 0 <= quota < 1.0, quota
    mde = IM.potenza_mde(v["dettaglio"], "pres_impiego (senza maglia)")
    assert mde["mde_quota_divario_pct"] > quota, (
        "se l'MDE fosse sotto il guadagno, il risultato non sarebbe negativo")


# --------------------------------------------------------------------------
# Coda di E2 — il cartellino come predittore, non come sottrazione
# --------------------------------------------------------------------------

@serve_parquet
def test_i_cartellini_sono_sfasati_come_le_altre_feature():
    """Nessuna quantita' della stagione bersaglio entra, denominatore compreso.

    Il tasso ha le **presenze** al denominatore, ed e' il punto in cui il leakage
    sarebbe piu' facile: le presenze di t sono il bersaglio. Il test verifica che
    la colonna di t-1 non cambi guastando le stagioni successive.
    """
    for feat in IM.FEATURE_CARTELLINI.values():
        for f in feat:
            assert f.endswith("_prec"), f

    from sot import fantapunti as FP
    ps = FP.per_giocatore_stagione()
    prima = IM.cartellini_precedenti(per_stagione=ps)

    guasto = ps.copy()
    tardi = guasto["stagione"] >= "2024-2025"
    guasto.loc[tardi, ["ammonizioni", "espulsioni", "presenze"]] = 0
    dopo = IM.cartellini_precedenti(per_stagione=guasto)

    # Le stagioni bersaglio fino alla 2024-2025 leggono t-1 <= 2023-2024: intatte.
    k = ["stagione", "giocatore_id"]
    a = prima[prima["stagione"] <= "2024-2025"].sort_values(k).reset_index(drop=True)
    b = dopo[dopo["stagione"] <= "2024-2025"].sort_values(k).reset_index(drop=True)
    pd.testing.assert_frame_equal(a, b)
    # ...e la 2025-2026, che legge la 2024-2025 guastata, DEVE essersi mossa, o il
    # test non sta guardando niente.
    assert not prima[prima["stagione"] == "2025-2026"]["cartellini_prec"].equals(
        dopo[dopo["stagione"] == "2025-2026"]["cartellini_prec"])


@serve_parquet
def test_la_rel_del_conteggio_e_degenere_ed_e_dichiarata():
    """Il conteggio non e' un rapporto: la sua `_rel` e' zero per costruzione.

    Va dichiarato e non spacciato per una candidata che passa il gate. Se un
    domani qualcuno la usasse come se fosse standardizzata, questo test spiega
    perche' non lo e'.
    """
    d = IM.deriva_cartellini().set_index(["candidata", "forma"])
    assert bool(d.loc[("cartellini", "_rel"), "degenere"])
    assert not bool(d.loc[("cartellini", "_rel"), "passa"])
    assert not bool(d.loc[("tasso_cartellini", "_rel"), "degenere"])
    # Nessuna delle due forme chiude il gate di E1: e' la ragione per cui la coda
    # prova sia la grezza sia la `_rel`.
    assert not d["passa"].any(), "se una passasse, il report andrebbe riscritto"


@serve_parquet
def test_il_cartellino_come_predittore_e_confutato_con_potenza():
    """L'inversione di E2.1 non regge, e il test che la nega e' sensibile.

    E' la differenza fra questo risultato negativo e quello di E2.4: li' l'MDE
    valeva l'1,53% del divario e il negativo escludeva solo effetti grandi. Qui il
    confronto e' appaiato contro un modello quasi identico, la varianza della
    differenza e' minuscola e l'MDE scende sotto lo 0,12%. **Il test vedrebbe
    effetti dieci volte piu' piccoli di quelli che E2.4 poteva vedere, e non ne
    trova nessuno.**
    """
    r = IM.contributo_cartellini()
    t = r["tabella"].set_index("variante")
    base = float(t.loc["impiego (senza maglia)", "divario_chiuso_pct"])

    for nome in IM.FEATURE_CARTELLINI:
        assert abs(float(t.loc[nome, "divario_chiuso_pct"]) - base) < 0.05, nome

    mde = r["mde"].set_index("variante")
    for nome in IM.FEATURE_CARTELLINI:
        assert abs(float(mde.loc[nome, "t"])) < 2.0, nome
        # La sensibilita' e' il punto: senza questa riga «nessun effetto» e «il
        # test non guarda» sarebbero indistinguibili.
        assert float(mde.loc[nome, "mde_quota_divario_pct"]) < 0.20, nome


@serve_parquet
def test_il_nulla_del_tasso_non_e_ridondanza():
    """Il tasso porta informazione che il set di E2.4 non ha, e non serve lo stesso.

    E' la parte che rende la confutazione forte invece che ambigua. Il
    **conteggio** e' in buona parte gia' nel set (R2 ~0,41 sulle tre quote), quindi
    da solo il suo nulla si spiegherebbe con la ridondanza. Il **tasso** no: e'
    quasi ortogonale, quindi il suo nulla e' un'assenza di segnale, non una
    ripetizione.
    """
    import numpy as np
    tab = IM.tabella_predittori()
    quote = ["quota_minuti_prec", "quota_titolare_prec", "quota_convocato_prec"]
    X = tab[quote].astype(float).fillna(0.0).to_numpy()
    X = np.hstack([np.ones((len(X), 1)), X])

    def r2(col: str) -> float:
        y = tab[col].astype(float).fillna(0.0).to_numpy()
        b, *_ = np.linalg.lstsq(X, y, rcond=None)
        return 1 - ((y - X @ b) ** 2).sum() / ((y - y.mean()) ** 2).sum()

    assert r2("cartellini_prec") > 0.25, "il conteggio dovrebbe essere ridondante"
    assert r2("tasso_cartellini_prec") < 0.10, (
        "se anche il tasso fosse ridondante, la confutazione sarebbe piu' debole")


@serve_parquet
def test_la_coda_non_sposta_i_numeri_di_e2_4():
    """Aggiungere colonne alla tabella non deve cambiare cio' che E2.4 ha pubblicato.

    Le colonne nuove entrano in `tabella_predittori` ma non in `FEATURE`: se il
    61,32 o lo 0,196% si muovessero, vorrebbe dire che il join dei cartellini ha
    perso o moltiplicato righe.
    """
    v = IM.valutazione()["tabella"].set_index("variante")
    assert abs(float(v.loc["impiego (senza maglia)", "mae"]) - 61.315) < 0.01
    assert abs(float(v.loc["impiego (senza maglia)", "divario_chiuso_pct"])
               - 0.196) < 0.01
    r = IM.contributo_cartellini()["tabella"].set_index("variante")
    # Le due strade calcolano la stessa variante e devono coincidere.
    assert abs(float(r.loc["impiego (senza maglia)", "mae_punti"])
               - float(v.loc["impiego (senza maglia)", "mae"])) < 1e-9


# --------------------------------------------------------------------------
# (b) — la quotazione QI come predittore di presenza
# --------------------------------------------------------------------------

@serve_parquet
def test_solo_colonne_pulite_del_listone():
    """Il gate di `quotazioni` applicato al punto d'uso, e non a parole.

    La guardia e' sull'**elenco** e non sul suffisso `_asta`: un nome che dice
    "noto all'asta" resterebbe vero anche mettendoci QA o FVM, e sarebbe falso.
    """
    from sot import quotazioni as Q

    assert set(IM.COLONNE_LISTONE_AMMESSE) <= set(Q.COLONNE_PULITE)
    assert not set(IM.COLONNE_LISTONE_AMMESSE) & set(Q.COLONNE_CONTAMINATE)
    for feat in IM.FEATURE_QI.values():
        for f in feat:
            assert "fvm" not in f and "qa_" not in f, f


@serve_parquet
def test_il_join_del_listone_non_moltiplica_ne_perde_righe():
    """E la valutazione gira su righe che hanno TUTTE un QI, per costruzione."""
    tab = IM.tabella_predittori()
    con = IM.con_quotazione(tab)
    assert len(con) == len(tab)
    # ~31% delle righe di t-1 non e' nel listone di t: ha lasciato il campionato.
    assert 0.2 < float(con["senza_quotazione_asta"].mean()) < 0.45


@serve_parquet
def test_il_percentile_passa_il_gate_di_e1_e_il_grezzo_no():
    """La forma che funziona e' anche la sola che non deriva, e non e' un caso.

    Se un domani il grezzo passasse la soglia, la coincidenza andrebbe rimisurata
    invece che ereditata: e' l'argomento in piu' che regge la §5.
    """
    d = IM.deriva_qi().set_index("colonna")
    assert not bool(d.loc["qi_asta", "passa"])
    assert bool(d.loc["qi_pct_ruolo_asta", "passa"])
    # il percentile e' un rango dentro la stagione: piatto per costruzione
    assert float(d.loc["qi_pct_ruolo_asta", "deriva"]) < 0.03


@serve_parquet
def test_qi_supera_il_rumore_ed_e_il_primo():
    """Il risultato di (b), bloccato nei due sensi.

    **Sopra** la propria soglia di rilevabilita' e sopra Bonferroni per le quattro
    varianti provate; e **molto sopra** lo 0,196% che i dati evento avevano
    prodotto. Se un domani scendesse sotto l'MDE, la §5 andrebbe riscritta.
    """
    r = IM.contributo_qi()
    t = r["tabella"].set_index("variante")
    m = r["mde"].set_index("variante")
    vince = "impiego + QI (percentile di ruolo)"

    quota = float(t.loc[vince, "divario_chiuso_pct"])
    assert quota > float(t.loc["impiego (senza maglia)", "divario_chiuso_pct"]) * 4
    assert quota > float(m.loc[vince, "mde_quota_divario_pct"]), "sotto il suo MDE"
    # 4 varianti: Bonferroni a due code su 0.05 vuole |t| > 2.50
    assert float(m.loc[vince, "t"]) > 2.50
    # e migliora il passaggio giusto, non solo il prodotto finale
    assert (float(t.loc[vince, "mae_presenze"])
            < float(t.loc["impiego (senza maglia)", "mae_presenze"]))


@serve_parquet
def test_qi_e_un_complemento_non_un_sostituto():
    """Da solo la quotazione e' PEGGIO del modello d'asta, e va detto.

    Senza questo test la §5 potrebbe essere letta come "all'asta guarda solo il
    prezzo", che e' il contrario di quello che i numeri dicono.
    """
    t = IM.contributo_qi()["tabella"].set_index("variante")
    assert float(t.loc["SOLO QI, senza le feature evento",
                       "divario_chiuso_pct"]) < 0


@serve_parquet
def test_qi_non_e_ne_ridondante_ne_indipendente():
    """Meta' di QI e' gia' nel set, e il guadagno viene dall'altra meta'.

    Serve a impedire le due letture sbagliate: "e' solo chi giocava gia'" (falso,
    R2 sotto 1) e "e' informazione tutta nuova" (falso, R2 ben sopra 0).
    """
    r = IM.ridondanza_qi().set_index("colonna")
    r2 = float(r.loc["qi_pct_ruolo_asta", "r2_sulle_quote"])
    assert 0.25 < r2 < 0.75, r2


@serve_parquet
def test_b_non_ha_spostato_i_numeri_di_e2_4_e_della_coda():
    """Il riferimento deve restare quello pubblicato, o le quote non si confrontano."""
    t = IM.contributo_qi()["tabella"].set_index("variante")
    assert abs(float(t.loc["impiego (senza maglia)", "mae_punti"]) - 61.315) < 0.01
    assert abs(float(t.loc["impiego (senza maglia)",
                           "divario_chiuso_pct"]) - 0.196) < 0.01


# --------------------------------------------------------------------------
# Il blocco non deve aver spostato i numeri pubblicati
# --------------------------------------------------------------------------

@serve_parquet
def test_e2_non_tocca_le_tabelle_pubblicate():
    """Nessun modulo di E2 scrive sotto `data/`: legge e basta."""
    for modulo in ("sot/squalifiche.py", "sot/distinta.py", "sot/impiego.py"):
        testo = (RADICE / modulo).read_text(encoding="utf-8")
        assert not re.search(r"\.to_parquet\(|\.to_csv\(", testo), modulo
