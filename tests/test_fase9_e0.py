# -*- coding: utf-8 -*-
"""Test del blocco E0 — le tabelle di Fase 1 sulle cinque stagioni.

Girano dai Parquet gia' costruiti: non rileggono i 1.889 CSV e non toccano la
rete. Se i Parquet non ci sono, i test che ne hanno bisogno si saltano invece di
fallire — un test rosso deve dire "il codice e' sbagliato", non "non hai ancora
eseguito lo script".
"""

from __future__ import annotations

import ast
from pathlib import Path

import pandas as pd
import pytest

from sot import aggancio as AG, aggregate, config, multistagione as MS

RADICE = Path(__file__).resolve().parent.parent


def _esiste(stagione: str) -> bool:
    return config.player_match(season=stagione).is_file()


TUTTE = all(_esiste(s) for s in config.SEASONS_STORICHE)
serve_parquet = pytest.mark.skipif(
    not TUTTE, reason="le cinque stagioni non sono state costruite")


# --------------------------------------------------------------------------
# La parametrizzazione non ha spostato il default
# --------------------------------------------------------------------------

def test_le_costanti_sono_la_stagione_pubblicata():
    """I NOMI storici devono valere esattamente `funzione(SEASON)`.

    E' cio' che rende la parametrizzazione invisibile a valle: se una di queste
    divergesse, le Fasi 1-6 leggerebbero un file diverso da quello che scrivono.
    """
    assert config.PLAYER_MATCH == config.player_match()
    assert config.TEAM_MATCH == config.team_match()
    assert config.SHOTS_PARQUET == config.shots_parquet()
    assert config.EVENTS_SLIM == config.events_slim()
    assert config.RAW_MATCH_DIR == config.match_dir()
    assert config.MATCHES_JSON == config.matches_json()
    assert config.player_match() == config.player_match(season=config.SEASON)


def test_stagioni_diverse_percorsi_diversi():
    visti = {config.player_match(season=s) for s in config.SEASONS_STORICHE}
    assert len(visti) == len(config.SEASONS_STORICHE)


def test_stagione_malformata_rifiutata():
    """La forma ambigua non deve creare in silenzio una cartella accanto."""
    for cattiva in ("2025-26", "2526", "2025/2026"):
        with pytest.raises(ValueError):
            config.player_match(season=cattiva)


# --------------------------------------------------------------------------
# Provenienza dell'xG: il punto dell'etichetta
# --------------------------------------------------------------------------

@serve_parquet
@pytest.mark.parametrize("stagione", config.SEASONS_STORICHE)
def test_xg_fit_dichiara_la_stagione(stagione):
    """`xg_fit` deve dire quale fit ha prodotto `xg`, in tutte e tre le tabelle.

    **Si verifica la PROPRIETA', non la forma della stringa**, e la correzione e'
    della Fase 14. Il test pretendeva `xg_fit == stagione`, cioe' la forma che
    `etichetta_fit` aveva **fino alla Fase 13**: da li' l'etichetta e'
    `campionato/stagione`, perche' con cinque campionati i fit sono venticinque e
    `"2025-2026"` ne identificherebbe cinque.

    Passava lo stesso perche' i Parquet su disco erano piu' vecchi del codice, e
    si e' rotto appena `run_phase1.py` — che e' un passo di **verifica**
    prescritto da CLAUDE.md — ne ha rigenerato uno. Un test che sorveglia un
    formato invece di una proprieta' dichiara verde una cache stantia.
    """
    for percorso in (config.player_match, config.team_match, config.shots_parquet):
        df = pd.read_parquet(percorso(season=stagione))
        assert "xg_fit" in df.columns, percorso.__name__
        etichette = set(df["xg_fit"].unique())
        assert len(etichette) == 1, percorso.__name__
        (e,) = etichette
        # la stagione ci deve essere: e' il fatto che E0 aveva stabilito
        assert stagione in e, (percorso.__name__, e)
        # e se c'e' anche il campionato, deve essere quello dichiarato da
        # `etichetta_fit`, non una terza forma inventata
        assert e in (stagione, aggregate.etichetta_fit(season=stagione)), \
            (percorso.__name__, e)


@serve_parquet
@pytest.mark.parametrize("stagione", config.SEASONS_STORICHE)
def test_stagione_presente_e_unica(stagione):
    for percorso in (config.player_match, config.team_match):
        df = pd.read_parquet(percorso(season=stagione))
        assert set(df["stagione"].unique()) == {stagione}


@serve_parquet
def test_carica_concatena_senza_perdere_la_stagione():
    pm = MS.carica("player_match")
    assert set(pm["stagione"].unique()) == set(config.SEASONS_STORICHE)
    per_stagione = pm.groupby("stagione").size()
    for s in config.SEASONS_STORICHE:
        atteso = len(pd.read_parquet(config.player_match(season=s)))
        assert per_stagione[s] == atteso


def test_nessuna_colonna_xg_confrontabile_fra_stagioni():
    """Il derivato NON deve contenere una versione normalizzata di `xg`.

    E' la decisione del blocco: l'etichetta di provenienza basta, la
    comparabilita' vive nello strato feature (E1). Una colonna `xg_std` o
    `xg_rel` dentro `aggregate` sarebbe la standardizzazione scesa nel derivato,
    cioe' un fatto misurato cancellato dove non si puo' piu' recuperare.
    """
    src = (RADICE / "sot" / "aggregate.py").read_text(encoding="utf-8")
    albero = ast.parse(src)
    assegnate = set()
    for nodo in ast.walk(albero):
        if isinstance(nodo, ast.Subscript) and isinstance(nodo.slice, ast.Constant):
            if isinstance(nodo.slice.value, str):
                assegnate.add(nodo.slice.value)
    vietate = {"xg_std", "xg_rel", "xg_z", "xg_normalizzato", "xg_scalato"}
    assert not (assegnate & vietate)


# --------------------------------------------------------------------------
# Stato di impiego (coda di E0)
# --------------------------------------------------------------------------

@serve_parquet
@pytest.mark.parametrize("stagione", config.SEASONS_STORICHE)
def test_stato_e_una_partizione(stagione):
    """I tre stati coprono tutte le righe e non si sovrappongono."""
    pm = pd.read_parquet(config.player_match(season=stagione))
    assert set(pm["stato"].unique()) <= set(aggregate.STATI_IMPIEGO)
    assert pm["stato"].notna().all()

    titolare = pm["stato"] == "titolare"
    subentrato = pm["stato"] == "subentrato"
    panchina = pm["stato"] == "panchina"
    assert int(titolare.sum() + subentrato.sum() + panchina.sum()) == len(pm)


@serve_parquet
@pytest.mark.parametrize("stagione", config.SEASONS_STORICHE)
def test_stato_coerente_con_minuti_e_titolarita(stagione):
    """`panchina` vuol dire zero minuti, e solo quello. Mai un titolare."""
    pm = pd.read_parquet(config.player_match(season=stagione))
    assert (pm.loc[pm["stato"] == "panchina", "minutes"] == 0).all()
    assert (pm.loc[pm["stato"] == "subentrato", "minutes"] > 0).all()
    assert (pm.loc[pm["stato"] == "titolare", "minutes"] > 0).all()
    assert not pm.loc[pm["stato"] == "panchina", "is_starter"].any()
    assert pm.loc[pm["stato"] == "titolare", "is_starter"].all()
    # zero minuti <=> panchina, nei due versi
    assert ((pm["minutes"] == 0) == (pm["stato"] == "panchina")).all()


@serve_parquet
def test_undici_titolari_per_squadra_partita():
    """Il controllo che dice che `InvolvedPlayers` e' stato letto bene."""
    pm = MS.carica("player_match")
    per_squadra = pm[pm["stato"] == "titolare"].groupby(
        ["stagione", "matchId", "teamId"]).size()
    assert (per_squadra == 11).all()


@serve_parquet
def test_i_convocati_non_impiegati_esistono_davvero():
    """Non e' una colonna vuota: e' un terzo della tabella."""
    pm = MS.carica("player_match")
    quota = (pm["stato"] == "panchina").mean()
    assert 0.25 < quota < 0.40
    for s in config.SEASONS_STORICHE:
        assert (pm.loc[pm["stagione"] == s, "stato"] == "panchina").sum() > 4_000


def test_stato_impiego_e_una_funzione_pura():
    """Si puo' chiamare su un frame costruito a mano, senza leggere niente."""
    finto = pd.DataFrame({"is_starter": [True, False, False],
                          "minutes": [90.0, 12.0, 0.0]})
    assert list(aggregate.stato_impiego(finto)) == [
        "titolare", "subentrato", "panchina"]


# --------------------------------------------------------------------------
# Medie di campionato: e' una tabella, non colonne su ogni riga
# --------------------------------------------------------------------------

@serve_parquet
def test_medie_sono_una_tabella_a_parte():
    medie = MS.medie_campionato()
    assert set(medie.columns) == {"stagione", "grandezza", "unita", "media", "n"}
    assert set(medie["stagione"].unique()) == set(config.SEASONS_STORICHE)
    # una riga per (stagione, grandezza, unita), senza duplicati
    assert not medie.duplicated(["stagione", "grandezza", "unita"]).any()


@serve_parquet
def test_le_medie_non_stanno_dentro_player_match():
    """Il derivato non porta la media di campionato come colonna ripetuta.

    **La guardia cerca la media, non la parola.** Cercava `"campionato" not in c`
    e ha cominciato a punire la colonna `campionato` — che e' legittima, e' nella
    lista dichiarata di `build_player_match`, e dice a quale campionato appartiene
    la riga. E' la quinta volta in questo repository che una guardia scritta su
    una sottostringa da' un falso positivo, dopo il gate sui qualifier, le
    guardie del vincolo 3, la cache di V1 e il `--league` della Fase 14.
    """
    pm = pd.read_parquet(config.player_match(season=config.SEASON))
    for c in pm.columns:
        assert not c.startswith("media_"), c
        assert "media_campionato" not in c, c
    # il controllo positivo: senza, «nessuna media» potrebbe voler dire «la
    # guardia non guarda niente»
    assert "campionato" in pm.columns


@serve_parquet
def test_xg_e_xg_concesso_hanno_la_stessa_media():
    """Controllo di identita': l'xG prodotto da una squadra e' concesso da un'altra.

    Se divergessero, il ribaltamento casa/trasferta sarebbe rotto in qualche
    stagione — ed e' esattamente il tipo di difetto che una stagione sola non
    fa vedere.
    """
    medie = MS.medie_campionato()
    p = medie[medie["unita"] == "squadra_partita"].pivot_table(
        index="stagione", columns="grandezza", values="media")
    for s in config.SEASONS_STORICHE:
        assert abs(p.loc[s, "xg"] - p.loc[s, "xg_conceded"]) < 1e-9, s


# --------------------------------------------------------------------------
# Denominatori
# --------------------------------------------------------------------------

@serve_parquet
def test_denominatori_presi_dai_dati():
    """Il denominatore si conta. Ne' 38 ne' il calendario sono la risposta.

    L'Atalanta ne ha 35 nelle due stagioni bucate. E **nessuna squadra arriva a
    39** nel 2022-23, benche' Spezia e Verona abbiano giocato 39 partite
    (38 + playout): di quelle, WhoScored non ha rispettivamente 2 e 1. Assumere
    il numero di calendario sbaglierebbe quanto assumere 38 — solo nell'altro
    verso.
    """
    p = MS.partite_per_squadra()
    atalanta = p[(p["team"] == "Atalanta") & (p["stagione"].isin(
        ["2021-2022", "2022-2023"]))]
    assert (atalanta["partite"] == 35).all()

    d23 = p[p["stagione"] == "2022-2023"].set_index("team")["partite"]
    assert d23.max() == 38
    assert d23["Spezia"] == 37
    assert d23["Verona"] == 38

    assert (p["partite"] != 38).any()


@serve_parquet
def test_le_partite_contate_tornano_con_i_csv():
    """Somma dei denominatori = 2 x numero di partite acquisite, per stagione."""
    p = MS.partite_per_squadra()
    tm = MS.carica("team_match")
    for s in config.SEASONS_STORICHE:
        assert p.loc[p["stagione"] == s, "partite"].sum() == 2 * tm.loc[
            tm["stagione"] == s, "matchId"].nunique()


@serve_parquet
def test_squadre_partita_a_zero_tiri_non_spariscono():
    """L'universo viene dalle due squadre di ogni file, non dal groupby dei tiri."""
    tm = MS.carica("team_match")
    assert (tm["sot"] == 0).any()
    # due righe per partita in ogni stagione, sempre
    per_partita = tm.groupby(["stagione", "matchId"]).size()
    assert (per_partita == 2).all()


# --------------------------------------------------------------------------
# Aggancio esteso
# --------------------------------------------------------------------------

def test_aggancio_legge_la_stagione_che_gli_si_chiede():
    """Il difetto che una stagione sola nascondeva.

    Prima di E0 il lato WhoScored leggeva `config.PLAYER_MATCH`, cioe' sempre la
    stagione pubblicata, qualunque stagione fosse stata chiesta. Con una
    stagione sola i due coincidevano.
    """
    src = (RADICE / "sot" / "aggancio.py").read_text(encoding="utf-8")
    assert "config.player_match(season=stagione)" in src
    assert "pd.read_parquet(config.PLAYER_MATCH)" not in src


def test_le_stagioni_agganciabili_non_sono_piu_una():
    assert len(AG.STAGIONI_CON_ENTRAMBE) == len(config.SEASONS_STORICHE)


@serve_parquet
def test_coerenza_fra_stagioni_e_una_tabella_non_un_assert():
    """Il controllo incrociato deve *ritornare* i discordi, non sollevare."""
    mappa = pd.read_csv(AG.GIOCATORI_CSV)
    coer = MS.coerenza_fra_stagioni(mappa)
    assert set(coer) == {"per_giocatore", "discordi_fc", "discordi_ws"}
    riep = MS.riepilogo_coerenza(mappa, coer)
    assert riep.loc[0, "controlli_incrociati"] > 0


@serve_parquet
def test_coerenza_vede_una_discordanza_costruita():
    """La macchina e' sensibile: se sporco un aggancio, il controllo lo vede.

    Senza questa prova, «zero discordanze» potrebbe voler dire «il controllo non
    guarda niente» — la lezione della 6D applicata a un risultato negativo.
    """
    mappa = pd.read_csv(AG.GIOCATORI_CSV)
    assert len(MS.coerenza_fra_stagioni(mappa)["discordi_fc"]) == 0

    multi = (mappa.groupby("giocatore_id_fc")["stagione"].nunique()
             .pipe(lambda s: s[s > 1]).index)
    assert len(multi) > 0
    guasta = mappa.copy()
    riga = guasta.index[guasta["giocatore_id_fc"] == multi[0]][0]
    guasta.loc[riga, "playerId_ws"] = -1
    assert len(MS.coerenza_fra_stagioni(guasta)["discordi_fc"]) == 1


# --------------------------------------------------------------------------
# Il blocco non deve aver spostato i numeri pubblicati
# --------------------------------------------------------------------------

@serve_parquet
def test_la_stagione_pubblicata_e_invariata():
    """Le righe e le medie della 2025-26 sono quelle delle Fasi 1-6."""
    tm = pd.read_parquet(config.team_match(season="2025-2026"))
    pm = pd.read_parquet(config.player_match(season="2025-2026"))

    assert len(tm) == 760
    assert len(pm) == 17_774
    assert tm["matchId"].nunique() == config.REF_N_MATCHES

    assert abs(tm["sot"].mean() - 4.034) < 5e-4
    assert abs(tm.loc[tm.is_home == 1, "sot"].mean() - 4.432) < 5e-4
    assert abs(tm.loc[tm.is_home == 0, "sot"].mean() - 3.637) < 5e-4
    assert abs(tm.loc[tm.team == "Como", "sot"].mean() - 5.105) < 5e-4


@serve_parquet
def test_aggregate_senza_stagione_e_la_stagione_pubblicata():
    """`load_*()` senza argomenti continua a leggere la 2025-26."""
    a = aggregate.load_player_match()
    b = aggregate.load_player_match(season=config.SEASON)
    assert len(a) == len(b) == 17_774


# --------------------------------------------------------------------------
# Coda del blocco — il residuo lato WhoScored, con identita' e minuti
# --------------------------------------------------------------------------

@serve_parquet
def test_il_conteggio_pubblicato_sottostima_il_residuo():
    """Il residuo per COPPIA non puo' essere minore del residuo per PERSONA.

    `aggancio_giocatori()` sottrae insiemi di `playerId` ignorando la squadra:
    chi e' agganciato in un club risulta agganciato **ovunque**, anche nel club
    in cui l'aggancio e' fallito. Il conteggio pubblicato quindi sottostima, e la
    disuguaglianza va nel verso giusto per costruzione.

    La relazione e' bloccata come disuguaglianza e non come uguaglianza perche'
    l'uguaglianza e' **falsa**, e scoprirlo e' stato il contenuto della coda:
    pretenderla avrebbe nascosto il caso `Maxime Lopez` invece di rivelarlo.
    """
    agg = MS.aggancio_giocatori()
    res = MS.residuo_whoscored(mappa=agg["mappa"])
    tasso = agg["tasso"].set_index("stagione")

    for st in config.SEASONS_STORICHE:
        r = res[res["stagione"] == st]
        assert r["playerId"].nunique() >= int(tasso.loc[st, "ws_non_agganciati"]), st


@serve_parquet
def test_lo_scarto_e_solo_chi_ha_cambiato_squadra():
    """La sottostima ha UNA causa sola, e va nominata invece che tollerata.

    Ogni giocatore che sta nel residuo per coppia ma non in quello per persona
    deve comparire nella mappa dell'aggancio con un'**altra** squadra nella
    stessa stagione. Se ne comparisse uno senza quella spiegazione, la differenza
    fra i due conteggi non sarebbe piu' il trasferimento di gennaio e ci sarebbe
    un secondo meccanismo da cercare.
    """
    agg = MS.aggancio_giocatori()
    m, res = agg["mappa"], MS.residuo_whoscored(mappa=agg["mappa"])
    tasso = agg["tasso"].set_index("stagione")

    trovati = 0
    for st in config.SEASONS_STORICHE:
        r = res[res["stagione"] == st]
        ms = m[m["stagione"] == st]
        scarto = r["playerId"].nunique() - int(tasso.loc[st, "ws_non_agganciati"])
        if not scarto:
            continue
        for pid in r["playerId"].unique():
            altrove = ms[ms["playerId_ws"] == pid]
            if len(altrove):
                squadre_res = set(r.loc[r["playerId"] == pid, "teamId"])
                assert not (set(altrove["teamId_ws"]) & squadre_res), (
                    "agganciato e non agganciato nella STESSA squadra")
                trovati += 1
    assert trovati, "lo scarto esiste ma nessuno cambia squadra: altra causa"


@serve_parquet
def test_residuo_ws_contiene_un_giocatore_da_rotazione_piena():
    """Il residuo NON e' fatto solo di comparse, ed e' il motivo per cui esiste.

    Se un domani qualcuno "semplificasse" il residuo assumendo che sia
    trascurabile, questo test glielo impedisce: nel 2023-24 c'e' una riga da
    oltre 2.000 minuti, cioe' oltre venti partite intere.
    """
    res = MS.residuo_whoscored()
    assert res["minuti"].max() > 2_000
    # ...e resta comunque irrilevante per qualunque MEDIA, che e' il motivo per
    # cui era passato inosservato. Le due cose stanno insieme.
    assert res["quota_minuti_stagione"].sum() < 0.01


@serve_parquet
def test_residuo_ws_e_vuoto_nella_stagione_pubblicata():
    """La 2025-26 e' a zero in entrambi i versi, ed e' la stagione dei numeri."""
    res = MS.residuo_whoscored()
    assert len(res[res["stagione"] == config.SEASON]) == 0


@serve_parquet
def test_corrispondenza_residui_misura_e_non_risolve():
    """Ogni irrisolto ha una controparte, ma la regola NON e' una chiave.

    Le due asserzioni vanno insieme e sono il contenuto della coda: da una parte
    l'informazione c'e' (ogni irrisolto trova un candidato con le stesse identiche
    presenze), dall'altra non basta a decidere (un caso ne trova due). Se un
    domani la seconda diventasse vera-per-tutti, la corrispondenza diventerebbe
    una chiave e la domanda aperta si chiuderebbe da sola — ma va **verificato**,
    non sperato.
    """
    agg = MS.aggancio_giocatori()
    res = MS.residuo_whoscored(mappa=agg["mappa"])
    corr = MS.corrispondenza_residui(agg["irrisolti"], res)

    coperti = corr.groupby(["stagione", "nome_fc"]).ngroups
    assert coperti == len(agg["irrisolti"]), "un irrisolto senza controparte"
    assert not corr["unico"].all(), "se fosse una chiave, andrebbe usata"
    # Le presenze coincidono per costruzione: e' il filtro. Che il filtro non
    # sia vuoto e' il fatto.
    assert (corr["presenze_fc"] == corr["presenze"]).all()


@serve_parquet
def test_corrispondenza_residui_non_tocca_la_mappa_pubblicata():
    """MISURA e non risolve: la mappa dell'aggancio resta quella di prima."""
    agg = MS.aggancio_giocatori()
    prima = len(agg["mappa"])
    res = MS.residuo_whoscored(mappa=agg["mappa"])
    MS.corrispondenza_residui(agg["irrisolti"], res)
    assert len(MS.aggancio_giocatori()["mappa"]) == prima
