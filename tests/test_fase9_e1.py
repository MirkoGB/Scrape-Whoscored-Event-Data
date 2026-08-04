# -*- coding: utf-8 -*-
"""Test del blocco E1 — la regola di costruzione delle feature.

I tre corollari del blocco sono qui **come test e non come buone intenzioni**,
che e' cio' che il prompt chiede:

    1. nessuna feature costruita sul nome di un qualifier senza averne
       verificato la frequenza nelle cinque stagioni;
    2. un test che fallisce se una colonna che entra in un modello
       multi-stagione ha una media di stagione che si muove oltre la soglia
       dichiarata senza essere stata standardizzata;
    3. le 72 colonne mai valorizzate restano fuori, e le grandezze che qualcuno
       cercherebbe li' si derivano.

Come per E0: se i Parquet non ci sono, i test che ne hanno bisogno si saltano
invece di fallire. Un test rosso deve dire "il codice e' sbagliato", non "non
hai ancora eseguito lo script".
"""

from __future__ import annotations

import ast
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from sot import config, features_giocatore as FG, io_events

RADICE = Path(__file__).resolve().parent.parent

PARQUET = all(config.player_match(season=s).is_file()
              for s in config.SEASONS_STORICHE)
serve_parquet = pytest.mark.skipif(
    not PARQUET, reason="le cinque stagioni non sono state costruite")

RICOGNIZIONE = (config.processed_league_dir() / "blocco0_colonne.parquet").is_file()
serve_ricognizione = pytest.mark.skipif(
    not RICOGNIZIONE, reason="manca la cache del Blocco 0")


@pytest.fixture(scope="module")
def tavole():
    o = FG.costruisci()
    return o["feature"], o["riferimenti"]


# --------------------------------------------------------------------------
# Il registro: contratto minimo
# --------------------------------------------------------------------------

def test_i_nomi_sono_unici_e_il_suffisso_e_un_contratto():
    nomi = FG.nomi_grezzi()
    assert len(set(nomi)) == len(nomi)
    for f in FG.CANDIDATE:
        assert f.rel == f.nome + FG.SUFFISSO_STANDARDIZZATA
        assert f.descrizione.strip()
        assert f.famiglia and f.unita


@serve_parquet
def test_ogni_candidata_e_un_rapporto_fra_colonne_esistenti(tavole):
    """`num` e `den` devono essere colonne vere della tabella degli ingredienti.

    E' cio' che rende il riferimento di campionato la STESSA grandezza del
    valore individuale: se `num` non fosse il numeratore vero, la media pesata
    sarebbe un altro numero con lo stesso nome.
    """
    feat, _ = tavole
    for f in FG.CANDIDATE:
        assert f.num in feat.columns, f.nome
        assert f.den in feat.columns, f.nome
        assert f.nome in feat.columns and f.rel in feat.columns, f.nome


@serve_parquet
def test_la_chiave_e_la_tripla_di_e0(tavole):
    feat, _ = tavole
    assert list(FG.CHIAVE) == ["stagione", "playerId", "teamId"]
    assert not feat.duplicated(list(FG.CHIAVE)).any()
    assert set(feat["stagione"].unique()) == set(config.SEASONS_STORICHE)


@serve_parquet
def test_i_denominatori_di_squadra_vengono_contati(tavole):
    """La lezione di E0 propagata allo strato feature: l'Atalanta ha 35 partite.

    Se `partite_squadra` fosse 38 per tutti, ogni quota di esposizione sarebbe
    sbagliata proprio dove sbagliare costa di piu' — la perdita alla fonte non e'
    casuale rispetto alla squadra.
    """
    feat, _ = tavole
    atalanta = feat[(feat["team"] == "Atalanta")
                    & (feat["stagione"].isin(["2021-2022", "2022-2023"]))]
    assert len(atalanta) > 0
    assert (atalanta["partite_squadra"] == 35).all()
    assert feat["partite_squadra"].max() == 38


@serve_parquet
def test_le_quote_stanno_dentro_i_loro_estremi(tavole):
    feat, _ = tavole
    for nome in ("quota_titolare", "quota_presenze", "precisione_passaggi",
                 "quota_tocchi_area", "quota_porta_inviolata"):
        v = feat[nome].dropna()
        assert v.between(0.0, 1.0).all(), nome
    # Un titolare esce per definizione dopo essere entrato a 0.
    v = feat["minuto_medio_uscita"].dropna()
    assert v.between(0.0, 130.0).all()


# --------------------------------------------------------------------------
# Corollario 3 — le 72 colonne mai valorizzate restano fuori
# --------------------------------------------------------------------------

@serve_ricognizione
def test_le_settantadue_sono_settantadue_e_sono_quelle():
    mai = FG.colonne_mai_valorizzate()
    assert len(mai) == 72
    assert "passAccuracy" in mai
    assert any(c.startswith("cleanSheet") for c in mai)
    assert any(c.startswith("goalConcededByTeam") for c in mai)


@serve_ricognizione
def test_la_misura_e_ne_nullo_ne_falso_non_notna():
    """`notna()` direbbe il contrario del vero su queste colonne.

    Lo scraper scrive il literal `False` dove il campo della fonte e' assente:
    misurate con `quota_non_nulli` le 72 risultano coperte, misurate con
    `quota_valorizzata` sono vuote. Il test verifica che sia proprio cosi', cioe'
    che la distinzione non sia teorica.
    """
    c = pd.read_parquet(config.processed_league_dir() / "blocco0_colonne.parquet")
    mai = FG.colonne_mai_valorizzate()
    d = c[c["colonna"].isin(mai)]
    assert (d["quota_valorizzata"].fillna(0.0) == 0.0).all()
    # ...e la misura ingenua ne dichiarerebbe coperte parecchie.
    assert (d["quota_non_nulli"].fillna(0.0) > 0.99).any()


@serve_ricognizione
def test_nessuna_delle_settantadue_e_letta_come_colonna():
    """Cerca gli **usi**, non le menzioni.

    La docstring del modulo nomina `passAccuracy` e le `cleanSheet*` proprio per
    dire che non si leggono, e una ricerca testuale dichiarerebbe colpevole il
    commento — e' il difetto gia' trovato in `test_stabilita_rilevazione.py`.
    Qui si guardano solo le stringhe usate come **indice** (`df["colonna"]`).
    """
    src = (RADICE / "sot" / "features_giocatore.py").read_text(encoding="utf-8")
    indici = {n.slice.value for n in ast.walk(ast.parse(src))
              if isinstance(n, ast.Subscript) and isinstance(n.slice, ast.Constant)
              and isinstance(n.slice.value, str)}
    assert not (indici & FG.colonne_mai_valorizzate())


@serve_ricognizione
def test_la_cache_degli_eventi_non_porta_nemmeno_una_delle_settantadue():
    """La garanzia piu' forte: non e' disciplina, e' impossibilita'.

    `io_events` tiene ~60 colonne su 259 e nessuna delle 72 e' fra quelle,
    quindi una feature non puo' leggerle nemmeno per errore. Se un domani
    qualcuno allargasse `ALL_COLS`, questo test se ne accorge.
    """
    assert not (set(io_events.ALL_COLS) & FG.colonne_mai_valorizzate())


@serve_ricognizione
def test_le_tre_grandezze_si_derivano_e_la_derivazione_e_dichiarata():
    d = FG.derivazioni()
    assert len(d) == 3
    mai = FG.colonne_mai_valorizzate()
    for r in d.itertuples(index=False):
        # La colonna della fonte e' davvero mai valorizzata (col prefisso).
        radice = r.colonna_della_fonte.split("*")[0].split(" ")[0]
        assert any(c.startswith(radice) for c in mai), radice
        # ...e la feature che la sostituisce esiste nel registro.
        FG.per_nome(r.feature)


@serve_parquet
def test_la_porta_inviolata_e_derivata_e_non_e_costante(tavole):
    """Se la derivazione fosse rotta la colonna sarebbe 0 o 1 ovunque."""
    feat, _ = tavole
    v = feat.loc[feat["presenze"] > 0, "quota_porta_inviolata"]
    assert 0.1 < v.mean() < 0.6
    assert v.nunique() > 50


# --------------------------------------------------------------------------
# Corollario 1 — il gate sui qualifier
# --------------------------------------------------------------------------

@serve_ricognizione
def test_il_gate_boccia_i_due_casi_noti_di_dizionario_cambiato():
    """`StandingSave` e `OtherBodyPart` sono la ragione per cui il gate esiste."""
    v = FG.verifica_qualifier(("StandingSave", "OtherBodyPart")).set_index("qualifier")
    assert not v.loc["StandingSave", "ammesso"]
    assert not v.loc["OtherBodyPart", "ammesso"]
    assert v.loc["StandingSave", "rapporto"] > 10
    assert v.loc["OtherBodyPart", "rapporto"] > 10


@serve_ricognizione
def test_il_gate_ammette_i_qualifier_dei_piazzati():
    """Se bocciasse tutto non sarebbe un gate, sarebbe un divieto.

    E' il controllo di sensibilita' al contrario: la macchina deve saper dire
    anche di si', altrimenti "nessun qualifier passa" non significherebbe niente.
    """
    v = FG.verifica_qualifier(("CornerTaken", "FreekickTaken")).set_index("qualifier")
    assert v["ammesso"].all()
    assert (v["stagioni"] == len(config.SEASONS_STORICHE)).all()


@serve_ricognizione
def test_un_qualifier_mai_visto_non_e_raro_e_non_e_ammesso():
    v = FG.verifica_qualifier(("QualifierCheNonEsiste",)).set_index("qualifier")
    assert not v.loc["QualifierCheNonEsiste", "ammesso"]
    assert v.loc["QualifierCheNonEsiste", "stagioni"] == 0


@serve_ricognizione
def test_una_candidata_che_dichiarasse_standingsave_verrebbe_fermata():
    """Il gate scatta sul registro, non su una buona intenzione.

    Si costruisce una candidata finta che dichiara il qualifier peggiore e si
    pretende che `controlla_qualifier_delle_candidate` sollevi. Senza questa
    prova, "nessuna candidata usa qualifier" potrebbe voler dire "la guardia non
    guarda niente".
    """
    finta = FG.Feature("finta", "tiri", "novantesimi", "prova", "per_90",
                       "candidata di prova", qualifier=("StandingSave",))
    originali = FG.CANDIDATE
    try:
        FG.CANDIDATE = originali + (finta,)
        assert "StandingSave" in FG.qualifier_dichiarati()
        with pytest.raises(FG.QualifierNonVerificato):
            FG.controlla_qualifier_delle_candidate()
    finally:
        FG.CANDIDATE = originali
    # Fuori dal try le candidate sono di nuovo quelle vere, e passano.
    FG.controlla_qualifier_delle_candidate()


def test_nessuna_candidata_di_oggi_usa_qualifier():
    """Dichiarato, non sottinteso: `events_slim` non porta `qualifiers`.

    Una feature sui piazzati vuole una rilettura dei 1.889 CSV, ed e' un costo
    che paga E4. Se un domani qualcuno la aggiunge, il test sopra e' quello che
    la controlla.
    """
    assert FG.qualifier_dichiarati() == ()
    assert "qualifiers" not in io_events.ALL_COLS[:-1]


# --------------------------------------------------------------------------
# Corollario 2 — la guardia sulla deriva
# --------------------------------------------------------------------------

@serve_parquet
def test_la_guardia_ferma_una_colonna_grezza_che_deriva(tavole):
    """Il caso per cui la guardia esiste: unita' grezze in un modello a 5 stagioni."""
    feat, _ = tavole
    with pytest.raises(FG.FeatureNonStandardizzata):
        FG.verifica_standardizzazione(feat, ["quota_porta_inviolata"])
    with pytest.raises(FG.FeatureNonStandardizzata):
        FG.verifica_standardizzazione(feat, ["ammonizioni_per_90",
                                             "gol_subiti_per_partita"])


@serve_parquet
def test_la_guardia_lascia_passare_la_versione_standardizzata(tavole):
    feat, _ = tavole
    out = FG.verifica_standardizzazione(
        feat, ["quota_porta_inviolata_rel", "ammonizioni_per_90_rel",
               "gol_subiti_per_partita_rel", "falli_per_90_rel"])
    assert out["passa"].all()
    assert (out["deriva"] < FG.SOGLIA_DERIVA).all()


@serve_parquet
def test_la_guardia_misura_e_non_guarda_il_suffisso(tavole):
    """Una colonna `_rel` guastata a mano deve essere fermata lo stesso.

    E' il controllo di sensibilita' che rende leggibile un esito positivo: senza,
    "le standardizzate passano" potrebbe voler dire "il suffisso e' una password".
    """
    feat, _ = tavole
    guasto = feat.copy()
    # Un gradino di stagione del 20%, iniettato dove non c'era.
    ultima = guasto["stagione"] == config.SEASONS_STORICHE[-1]
    guasto.loc[ultima, "falli_per_90_rel"] = guasto.loc[ultima, "falli_per_90_rel"] + 0.20
    with pytest.raises(FG.FeatureNonStandardizzata):
        FG.verifica_standardizzazione(guasto, ["falli_per_90_rel"])


@serve_parquet
def test_la_guardia_ammette_una_grezza_che_non_si_muove(tavole):
    """Il verso opposto: la regola non e' "standardizza tutto per riflesso".

    `minuto_medio_uscita` deriva dell'1,2% fra le cinque stagioni e puo' entrare
    in unita' grezze. Una guardia che bocciasse anche quella costringerebbe a
    standardizzare per superstizione.
    """
    feat, _ = tavole
    out = FG.verifica_standardizzazione(feat, ["minuto_medio_uscita", "x_medio",
                                               "precisione_passaggi"])
    assert out["passa"].all()


@serve_parquet
def test_la_guardia_rifiuta_una_colonna_che_non_esiste(tavole):
    feat, _ = tavole
    with pytest.raises(KeyError):
        FG.verifica_standardizzazione(feat, ["colonna_inventata"])


@serve_parquet
def test_i_verdetti_sono_tre_e_dichiarati(tavole):
    feat, _ = tavole
    d = FG.deriva_feature(feat)
    assert len(d) == len(FG.CANDIDATE)
    assert set(d["verdetto"]) <= set(FG.VERDETTI)
    # Tutte e tre le classi sono popolate: se una fosse vuota, il blocco non
    # avrebbe misurato niente di distinguibile.
    assert set(d["verdetto"]) == set(FG.VERDETTI)


@serve_parquet
def test_le_candidate_non_risolte_sono_interrogabili_dal_codice(tavole):
    """E2 ed E4 devono poterlo chiedere, non leggerlo nel markdown."""
    feat, _ = tavole
    non_risolte = FG.richiede_effetto_stagione(feat)
    assert set(non_risolte) <= set(FG.nomi_grezzi())
    # L'xG e' fra queste, e ha una ragione in piu' delle altre: cinque fit.
    assert "xg_per_90" in non_risolte


@serve_parquet
def test_la_scomposizione_spiega_il_residuo(tavole):
    """Dove le due derive vanno in versi opposti, la standardizzazione peggiora.

    Non e' un'illustrazione: e' il meccanismo, e il test lo lega al verdetto.
    La condizione e' **doppia** — versi opposti *e* un riferimento che si muove
    di piu' della soglia — e la seconda meta' serve: `minuto_medio_uscita` va in
    versi opposti ma il suo riferimento si sposta dell'1%, e un verso opposto su
    un movimento che non c'e' non peggiora niente.
    """
    feat, rif = tavole
    s = FG.scomposizione_deriva(feat, rif).set_index("feature")
    d = FG.deriva_feature(feat).set_index("feature")
    opposti = s.index[(~s["stesso_verso"])
                      & (s["deriva_riferimento"] > FG.SOGLIA_DERIVA)]
    peggiorate = d.index[d["deriva_std"] > d["deriva_grezza"]]
    assert len(opposti) > 0
    assert set(opposti) <= set(peggiorate)


@serve_parquet
def test_la_soglia_non_e_stata_ricavata_dai_dati(tavole):
    """Vincolo 1 applicato a una soglia: e' dichiarata, non scelta su un argmax.

    E' lo stesso controllo che `tests/test_aggancio.py` fa sull'80': una soglia
    ricavata dal campione su cui poi la si applica e' un iperparametro adattato
    al bersaglio.
    """
    src = (RADICE / "sot" / "features_giocatore.py").read_text(encoding="utf-8")
    albero = ast.parse(src)
    for nodo in ast.walk(albero):
        if isinstance(nodo, ast.Assign) and any(
                isinstance(t, ast.Name) and t.id in ("SOGLIA_DERIVA",
                                                     "SOGLIA_QUALIFIER",
                                                     "MIN_MINUTI_DERIVA")
                for t in nodo.targets):
            assert isinstance(nodo.value, ast.Constant), ast.dump(nodo.value)
    for vietato in ("argmax", "idxmax", "quantile("):
        assert vietato not in src


@serve_parquet
def test_il_pavimento_di_esposizione_e_dichiarato_e_misurato(tavole):
    """Se il verdetto dipendesse dal pavimento e nessuno lo dicesse, sarebbe una scelta nascosta."""
    feat, _ = tavole
    s = FG.sensibilita_pavimento(feat)
    assert len(s) == len(FG.CANDIDATE)
    assert s["sempre_effetto_stagione"].any()
    assert s["mai_effetto_stagione"].any()


# --------------------------------------------------------------------------
# Vincolo 4 — la deriva non e' stata cancellata: il derivato si ricostruisce
# --------------------------------------------------------------------------

@serve_parquet
def test_la_colonna_grezza_si_ricostruisce_dalla_standardizzata(tavole):
    """`(x_rel + 1) * m_s == x`, a meno del floating point.

    E' la prova che la standardizzazione sta nello strato feature e non ha
    distrutto niente: il fatto misurato resta recuperabile all'indietro.
    """
    feat, rif = tavole
    for nome in ("sot_per_90", "quota_porta_inviolata", "ammonizioni_per_90"):
        rifatta = FG.ricostruisci(feat, rif, nome)
        ok = feat[nome].notna()
        assert np.allclose(rifatta[ok], feat.loc[ok, nome], rtol=1e-9, atol=1e-12), nome


@serve_parquet
def test_la_standardizzazione_non_e_scesa_nel_derivato():
    """`player_match` e `team_match` restano in unita' grezze (vincolo 4)."""
    for stagione in config.SEASONS_STORICHE:
        for percorso in (config.player_match, config.team_match):
            df = pd.read_parquet(percorso(season=stagione))
            for c in df.columns:
                assert not c.endswith(FG.SUFFISSO_STANDARDIZZATA), (stagione, c)
                assert not c.startswith("media_"), (stagione, c)


def test_nessuno_script_delle_fasi_precedenti_importa_questo_modulo():
    """Le Fasi 1-6 e la Fase 8 non devono dipendere dallo strato feature.

    Si cerca una riga di **import**, non il nome ovunque nel file: nominare un
    modulo in prosa per dire che non lo si usa non e' usarlo. E' il difetto gia'
    corretto una volta in `test_stabilita_rilevazione.py`.
    """
    ammessi = {"run_fase9_e1.py"}
    for p in (RADICE / "scripts").glob("run_*.py"):
        if p.name in ammessi:
            continue
        src = p.read_text(encoding="utf-8")
        righe = [r.strip() for r in src.splitlines()
                 if r.strip().startswith(("import ", "from "))]
        assert not any("features_giocatore" in r for r in righe), p.name


# --------------------------------------------------------------------------
# I riferimenti: stesso schema di E0, file separato
# --------------------------------------------------------------------------

@serve_parquet
def test_i_riferimenti_hanno_lo_schema_delle_medie_di_e0(tavole):
    _, rif = tavole
    assert set(rif.columns) == {"stagione", "grandezza", "unita", "media", "n"}
    assert not rif.duplicated(["stagione", "grandezza"]).any()
    assert set(rif["stagione"].unique()) == set(config.SEASONS_STORICHE)
    assert set(rif["grandezza"].unique()) == set(FG.nomi_grezzi())
    if config.MEDIE_STAGIONE.is_file():
        e0 = pd.read_parquet(config.MEDIE_STAGIONE)
        assert set(e0.columns) == set(rif.columns)
    assert config.FEATURE_RIFERIMENTI != config.MEDIE_STAGIONE


@serve_parquet
def test_il_riferimento_e_somma_su_somma_non_media_di_medie(tavole):
    """La differenza non e' accademica: pesa chi ha giocato 3.000 minuti.

    Si ricalcola a mano su una feature e si verifica che il riferimento sia
    `somma(num)/somma(den)` e **non** la media delle medie individuali, che su
    un tasso per 90 e' un numero diverso.
    """
    feat, rif = tavole
    f = FG.per_nome("sot_per_90")
    for st, blocco in feat.groupby("stagione"):
        atteso = blocco[f.num].sum() / blocco[f.den].sum()
        letto = rif.loc[(rif["grandezza"] == f.nome)
                        & (rif["stagione"] == st), "media"].iloc[0]
        assert abs(letto - atteso) < 1e-12, st
        media_di_medie = blocco.loc[blocco["minuti"] > 0, f.nome].mean()
        assert abs(media_di_medie - atteso) > 1e-6, st


@serve_parquet
def test_lo_scarto_relativo_e_zero_alla_media_di_campionato(tavole):
    """La forma e' `x/m - 1`: un giocatore esattamente medio vale 0."""
    feat, rif = tavole
    f = FG.per_nome("tocchi_per_90")
    tavola = rif.set_index(["grandezza", "stagione"])["media"]
    for st in config.SEASONS_STORICHE:
        m = tavola[(f.nome, st)]
        # Serve una riga con denominatore non nullo: chi non ha mai toccato il
        # pallone non ha un tasso, e `nan` non e' "esattamente medio".
        blocco = feat[(feat["stagione"] == st) & (feat[f.den] > 0)]
        riga = blocco.iloc[[0]].copy()
        riga[f.num] = m * riga[f.den]
        rifatta = FG.standardizza(riga, rif)
        assert abs(float(rifatta[f.rel].iloc[0])) < 1e-12, st
