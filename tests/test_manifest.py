"""Il manifest di provenienza — vincoli 8 e 9 della Fase 7.

Girano sul manifest vero, non su uno simulato: e' l'unico modo di verificare
che i 1889 file acquisiti abbiano davvero una provenienza, che e' cio' che il
vincolo 8 richiede. I test sulla *logica* (idempotenza, rilevazione di un
contenuto cambiato) usano invece una cartella temporanea.
"""

from __future__ import annotations

import json

import pytest

from acquisition import manifest as M
from sot import config


@pytest.fixture(scope="module")
def man():
    if not config.MANIFEST.is_file():
        pytest.skip("manifest non ancora generato")
    return json.loads(config.MANIFEST.read_text(encoding="utf-8"))


# --------------------------------------------------------------------------
# Ogni file acquisito ha la sua provenienza
# --------------------------------------------------------------------------
def test_ogni_csv_su_disco_e_registrato(man):
    """Vincolo 8: una riga senza provenienza non entra nel dataset."""
    su_disco = set()
    for season in config.SEASONS_STORICHE:
        d = config.raw_dir("whoscored", season=season) / "events"
        if d.is_dir():
            su_disco |= {str(p.relative_to(config.ROOT)).replace("\\", "/")
                         for p in d.glob("*.csv")}
    assert su_disco, "nessun CSV su disco: il test non direbbe niente"
    assert su_disco - set(man["file"]) == set()


@pytest.mark.parametrize("campo", ["fonte", "campionato", "stagione", "url",
                                   "scaricato", "byte", "sha256"])
def test_nessuna_voce_incompleta(man, campo):
    vuote = [k for k, v in man["file"].items() if not v.get(campo)]
    assert not vuote[:5], f"{len(vuote)} voci senza `{campo}`: {vuote[:3]}"


def test_la_definizione_della_metrica_nella_fonte_e_dichiarata(man):
    """Vincolo 8 di nuovo, ed e' la meta' che si dimentica: non basta sapere da
    dove viene un numero, serve sapere cosa significa **li'**."""
    d = man["definizioni"]["whoscored"]
    assert d["fornitore"] and d["tiro_in_porta"]
    assert "sot/shots.py" in d["tiro_in_porta"], (
        "la definizione della fonte deve rimandare alla nostra senza confondersi "
        "con essa (vincolo 7)"
    )


def test_gli_hash_sono_tutti_distinti(man):
    """Due file identici significherebbero la stessa pagina salvata due volte —
    tipicamente una pagina d'errore scritta al posto dei dati."""
    hash_ = [v["sha256"] for v in man["file"].values()]
    assert len(set(hash_)) == len(hash_)


def test_la_data_di_download_non_e_quella_di_registrazione(man):
    """Il manifest e' stato creato dopo l'acquisizione. Datare tutti i download
    all'istante della registrazione sarebbe una provenienza comoda e falsa."""
    giorni = {v["scaricato"][:10] for v in man["file"].values()}
    assert len(giorni) > 1, giorni


# --------------------------------------------------------------------------
# Idempotenza, e un contenuto cambiato che non passa in silenzio
# --------------------------------------------------------------------------
def _finta_stagione(tmp_path, monkeypatch, contenuto=b"a,b\n1,2\n"):
    ev = tmp_path / "raw" / "whoscored" / "ITA-serie-a" / "2021-2022" / "events"
    ev.mkdir(parents=True)
    (ev / "999.csv").write_bytes(contenuto)
    (ev.parent / "matches.json").write_text(
        json.dumps([{"url": "/matches/999/live/x", "home": "A", "away": "B",
                     "date": "", "score": "0:0"}]), encoding="utf-8")
    monkeypatch.setattr(config, "RAW", tmp_path / "raw")
    monkeypatch.setattr(config, "MANIFEST", tmp_path / "raw" / "manifest.json")
    monkeypatch.setattr(config, "ROOT", tmp_path)
    return ev / "999.csv"


def test_una_seconda_registrazione_non_riscrive_niente(tmp_path, monkeypatch):
    _finta_stagione(tmp_path, monkeypatch)
    a = M.registra_whoscored(seasons=["2021-2022"], verbose=False)
    b = M.registra_whoscored(seasons=["2021-2022"], verbose=False)
    assert (a["nuovi"], a["invariati"]) == (1, 0)
    assert (b["nuovi"], b["invariati"], b["modificati"]) == (0, 1, [])


def test_un_contenuto_cambiato_e_segnalato_non_assorbito(tmp_path, monkeypatch):
    """Un hash cambiato su un file gia' registrato significa che la fonte ha
    cambiato i dati sotto di noi: e' un evento, non un aggiornamento."""
    csv = _finta_stagione(tmp_path, monkeypatch)
    M.registra_whoscored(seasons=["2021-2022"], verbose=False)
    csv.write_bytes(b"a,b\n9,9\n")
    r = M.registra_whoscored(seasons=["2021-2022"], verbose=False)
    assert len(r["modificati"]) == 1
    voce = json.loads((tmp_path / "raw" / "manifest.json").read_text(
        encoding="utf-8"))["file"]["raw/whoscored/ITA-serie-a/2021-2022/events/999.csv"]
    assert len(voce["revisioni_precedenti"]) == 1, (
        "la revisione precedente va conservata, non sovrascritta"
    )


def test_il_manifest_non_tocca_i_dati_grezzi(tmp_path, monkeypatch):
    """Vincolo 9: l'unico file che questo modulo scrive e' il manifest."""
    csv = _finta_stagione(tmp_path, monkeypatch)
    prima = csv.read_bytes(), csv.stat().st_mtime
    M.registra_whoscored(seasons=["2021-2022"], verbose=False)
    assert (csv.read_bytes(), csv.stat().st_mtime) == prima
