"""Importazione e identità delle rose. Nessun default sui regolamenti di lega.

Il collegamento a WhoScored usa ID storici univoci o nome/iniziali e club
concordanti. Non usa similarità fuzzy né interpreta colori XLSX come ruoli.
"""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
import hashlib
from pathlib import Path, PurePosixPath
import posixpath
import re
import unicodedata
import xml.etree.ElementTree as ET
import zipfile

import pandas as pd

from sot.aggancio import _normalizza, _scomponi_fc

NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
DOC_REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
RULE_FIELDS = ("formato", "fonte_voti", "moduli_consentiti", "vincoli_rosa",
               "bonus_malus", "modificatori", "sostituzioni", "scambi", "crediti")


class RoseError(ValueError):
    """Input incompatibile: correggere il dato, non indovinarlo."""


def nome_chiave(value):
    """Solo Unicode canonico, spazi e maiuscole; nessuna perdita di accenti."""
    return " ".join(unicodedata.normalize("NFC", str(value)).split()).casefold()


def file_info(path):
    path = Path(path)
    return {"file": path.name, "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "bytes": path.stat().st_size,
            "modificato_utc": datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat()}


def _column(ref):
    match = re.fullmatch(r"([A-Z]+)[1-9][0-9]*", ref)
    if not match:
        raise RoseError(f"Riferimento cella non valido: {ref}")
    number = 0
    for char in match[1]:
        number = number * 26 + ord(char) - ord("A") + 1
    return number


def _decimal(value, where):
    if value in (None, ""):
        return None
    try:
        result = Decimal(str(value))
    except InvalidOperation as exc:
        raise RoseError(f"Costo non numerico in {where}: {value!r}") from exc
    if not result.is_finite() or result < 0:
        raise RoseError(f"Costo non valido in {where}: {value!r}")
    return result


def read_roster_sheet(path, sheet_name="ROSE"):
    """Seleziona il foglio per nome e relationship, non per posizione nel ZIP."""
    with zipfile.ZipFile(path) as archive:
        workbook = ET.fromstring(archive.read("xl/workbook.xml"))
        sheets = [s for s in workbook.findall("m:sheets/m:sheet", NS)
                  if s.get("name") == sheet_name]
        if len(sheets) != 1:
            raise RoseError(f"{path}: atteso un foglio {sheet_name!r}")
        rels = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
        rid = sheets[0].get(f"{{{DOC_REL}}}id")
        targets = [r for r in rels.findall(f"{{{REL_NS}}}Relationship") if r.get("Id") == rid]
        if len(targets) != 1 or targets[0].get("TargetMode") == "External":
            raise RoseError(f"{path}: relationship del foglio non valida")
        target = targets[0].get("Target", "")
        member = posixpath.normpath(target.lstrip("/") if target.startswith("/") else "xl/" + target)
        if not member.startswith("xl/") or ".." in PurePosixPath(member).parts:
            raise RoseError(f"{path}: destinazione foglio non valida")
        strings = []
        if "xl/sharedStrings.xml" in archive.namelist():
            strings = ["".join(t.text or "" for t in node.findall(".//m:t", NS))
                       for node in ET.fromstring(archive.read("xl/sharedStrings.xml")).findall("m:si", NS)]
        rows = []
        for row in ET.fromstring(archive.read(member)).findall(".//m:sheetData/m:row", NS):
            cells = {}
            for cell in row.findall("m:c", NS):
                ref = cell.attrib["r"]
                value = cell.find("m:v", NS)
                formula = cell.find("m:f", NS)
                if formula is not None and (value is None or value.text is None):
                    raise RoseError(f"{path}:{ref}: formula senza risultato salvato")
                raw = value.text if value is not None else ""
                if cell.get("t") == "s":
                    try:
                        raw = strings[int(raw)]
                    except (ValueError, IndexError, TypeError) as exc:
                        raise RoseError(f"{path}:{ref}: shared string non valida") from exc
                elif cell.get("t") == "inlineStr":
                    raw = "".join(t.text or "" for t in cell.findall(".//m:t", NS))
                elif cell.get("t") in ("e", "b"):
                    raise RoseError(f"{path}:{ref}: tipo cella non ammesso {cell.get('t')}")
                cells[_column(ref)] = {"value": raw or "", "cell": ref, "style": cell.get("s")}
            if any(c["value"] for c in cells.values()):
                rows.append(cells)
        if not rows:
            raise RoseError(f"{path}: foglio vuoto")
        return rows


def import_roster(path, league, own_team, sheet_name="ROSE"):
    rows = read_roster_sheet(path, sheet_name)
    records, teams = [], []
    info = file_info(path)
    stamp = re.search(r"-rosters-(\d{13})\.xlsx$", Path(path).name)
    info["export_utc_da_nome_file"] = (datetime.fromtimestamp(int(stamp[1]) / 1000, timezone.utc).isoformat()
                                       if stamp else None)
    for col, header in sorted(rows[0].items()):
        name = header["value"]
        if not name or nome_chiave(name) == "costo":
            continue
        if nome_chiave(rows[0].get(col + 1, {}).get("value", "")) != "costo":
            raise RoseError(f"{path}:{header['cell']}: manca colonna costo")
        members, total, seen_total = [], None, False
        for row in rows[1:]:
            cell = row.get(col, {})
            player = cell.get("value", "")
            raw_cost = row.get(col + 1, {}).get("value", "")
            if not player.strip():
                if raw_cost:
                    raise RoseError(f"{path}: costo senza giocatore per {name}")
                continue
            cost = _decimal(raw_cost, f"{path}:{cell['cell']}")
            if nome_chiave(player) == "totale":
                if seen_total or cost is None:
                    raise RoseError(f"{path}: totale duplicato o vuoto per {name}")
                total, seen_total = cost, True
                continue
            if seen_total:
                raise RoseError(f"{path}: giocatore dopo il totale per {name}")
            entry = {"lega": league, "squadra": name, "mia_squadra": nome_chiave(name) == nome_chiave(own_team),
                     "giocatore": player, "nome_chiave": nome_chiave(player),
                     "costo": float(cost) if cost is not None else None,
                     "file": Path(path).name, "foglio": sheet_name, "cella": cell["cell"],
                     "stile": cell.get("style"), "sha256_export": info["sha256"]}
            members.append((entry, cost))
            records.append(entry)
        if not seen_total or not members:
            raise RoseError(f"{path}: rosa vuota o totale mancante per {name}")
        missing = sum(cost is None for _, cost in members)
        paid = sum((cost for _, cost in members if cost is not None), Decimal(0))
        if not missing and paid != total:
            raise RoseError(f"{path}: totale {total} diverso dalla somma {paid} per {name}")
        teams.append({"nome": name, "mia_squadra": nome_chiave(name) == nome_chiave(own_team),
                      "giocatori": len(members), "costo_totale_noto": float(paid),
                      "totale_export": float(total), "costi_mancanti": missing,
                      "totale_coerente": None if missing else True})
    if len({nome_chiave(t['nome']) for t in teams}) != len(teams):
        raise RoseError(f"{league}: nomi squadra duplicati")
    if sum(t["mia_squadra"] for t in teams) != 1:
        raise RoseError(f"{league}: squadra utente non identificata univocamente")
    duplicates = [n for n, count in Counter(r["nome_chiave"] for r in records).items() if count > 1]
    if duplicates:
        raise RoseError(f"{league}: giocatori ripetuti nella stessa lega: {duplicates}")
    return records, {"lega": league, "squadre": teams, "fonte": info}


def rules_status(config):
    """Stato operativo; il motore futuro deve chiamare require_rules prima dei calcoli."""
    rules = config.get("regole", {})
    def incomplete(value, path):
        if value is None or value in ({}, [], ""):
            return [path]
        if isinstance(value, dict):
            if value.get("attivo") is False:
                return []
            return [p for key, child in value.items() for p in incomplete(child, path + "." + key)]
        return []
    missing = [p for key in RULE_FIELDS for p in incomplete(rules.get(key), key)]
    if config.get("regole_confermate") is not True:
        missing.insert(0, "regole_confermate")
    if config.get("stagione_confermata") is not True:
        missing.insert(0, "stagione_confermata")
    if rules.get("formato") not in (None, "classic", "mantra"):
        raise RoseError("Formato ammesso: classic, mantra oppure null")
    return {"pronta_per_valutazione": not missing, "campi_da_confermare": missing}


def require_rules(config):
    status = rules_status(config)
    if not status["pronta_per_valutazione"]:
        raise RoseError("Regole incomplete: " + ", ".join(status["campi_da_confermare"]))
    return config["regole"]


def _name_agrees(fc_name, ws_name):
    if not isinstance(fc_name, str) or not isinstance(ws_name, str):
        return False
    if "\ufffd" in fc_name or "\ufffd" in ws_name:
        return False
    surname, initials = _scomponi_fc(fc_name)
    parts = _normalizza(ws_name)
    # Nessuna sottostringa: Mora non deve agganciare Morata.
    if not surname or not set(surname).issubset(parts):
        return False
    given = [p for p in parts if p not in surname]
    return all(any(p.startswith(initial) for p in given) for initial in initials)


def resolve_identities(names, quotes, historical, current_ws, team_bridge, season, aliases=None):
    """Una riga per nome originale. Tutti i candidati ambigui restano ispezionabili.

    aliases: lista curata con stagione, nome_export, giocatore_id_fc, fonte,
    motivo; opzionalmente playerId_ws. Mai dedotta con distanza fra stringhe.
    """
    quotes = quotes[quotes.stagione == season].copy()
    if quotes.empty or quotes.giocatore_id.duplicated().any():
        raise RoseError("Listone corrente vuoto o ID Fantacalcio duplicati")
    aliases = aliases or []
    overrides = {}
    for alias in aliases:
        if alias["stagione"] != season:
            continue
        key = nome_chiave(alias["nome_export"])
        if key in overrides or not alias.get("fonte") or not alias.get("motivo"):
            raise RoseError("Alias duplicato o senza provenienza/motivazione")
        overrides[key] = alias
    quotes["key"] = quotes.giocatore.map(nome_chiave)
    catalog = current_ws[["playerId", "playerName", "teamId", "team", "role"]].drop_duplicates()
    results = []
    for original in sorted(set(names)):
        key = nome_chiave(original)
        alias = overrides.get(key)
        found = quotes[quotes.giocatore_id == alias["giocatore_id_fc"]] if alias else quotes[quotes.key == key]
        result = {"nome_export": original, "nome_chiave": key, "stagione": season,
                  "giocatore_id_fc": None, "nome_fc": None, "club_fc": None,
                  "squadra_id_fc": None, "ruolo_classic": None, "ruolo_mantra": None,
                  "fonte_fc": "listone_corrente", "metodo_fc": "alias_verificato" if alias else "nome_esatto_normalizzato",
                  "playerId_ws": None, "nome_ws": None, "club_ws_osservati": [],
                  "metodo_ws": None, "stagioni_ponte": [], "candidati_ws": [],
                  "stato": "fc_non_trovato", "copertura_ws_corrente": False}
        if len(found) != 1:
            if alias:
                raise RoseError(f"Alias con ID Fantacalcio assente: {original}")
            result["stato"] = "fc_ambiguo" if len(found) else "fc_non_trovato"
            results.append(result)
            continue
        fc = found.iloc[0]
        if fc.ruolo_classic not in ("p", "d", "c", "a") or pd.isna(fc.ruolo_mantra):
            raise RoseError(f"Ruoli correnti mancanti o non validi: {original}")
        if alias:
            result["fonte_alias"] = alias["fonte"]
            result["motivo_alias"] = alias["motivo"]
        result.update(giocatore_id_fc=int(fc.giocatore_id), nome_fc=fc.giocatore,
                      club_fc=fc.squadra_sigla, squadra_id_fc=int(fc.squadra_id),
                      ruolo_classic=fc.ruolo_classic, ruolo_mantra=fc.ruolo_mantra,
                      fuori_dal_campionato=bool(fc.fuori_dal_campionato))
        old = historical[(historical.giocatore_id_fc == fc.giocatore_id)
                         & (historical.stagione < season)].dropna(subset=["playerId_ws"])
        old_ids = sorted(set(int(x) for x in old.playerId_ws))
        clubs = sorted(set(int(x) for x in team_bridge.loc[
            team_bridge.squadra_id_fc == fc.squadra_id, "teamId_ws"]))
        # Il ponte dei club deve essere univoco; niente filtro indovinato.
        pool = catalog[catalog.teamId == clubs[0]] if len(clubs) == 1 else catalog.iloc[:0]
        # Il portiere Pietro Terracciano non è il difensore Filippo Terracciano.
        if fc.ruolo_classic == "p":
            pool = pool[pool.role == "GK"]
        else:
            pool = pool[pool.role != "GK"]
        candidates = sorted(set(int(row.playerId) for row in pool.itertuples()
                                if _name_agrees(fc.giocatore, row.playerName)))
        result["candidati_ws"] = candidates
        chosen = None
        if alias and alias.get("playerId_ws") is not None:
            chosen = int(alias["playerId_ws"])
            known = set(catalog.playerId) | set(historical.playerId_ws.dropna())
            if chosen not in known:
                raise RoseError(f"Alias con ID WhoScored sconosciuto: {original}")
            result["metodo_ws"] = "alias_verificato"
            result["fonte_alias"] = alias["fonte"]
        elif len(old_ids) == 1:
            # Un candidato attuale diverso segnala conflitto, non corregge la storia.
            if candidates and old_ids[0] not in candidates:
                result["stato"] = "conflitto_ponte_storico"
            else:
                chosen = old_ids[0]
                result["metodo_ws"] = "ponte_id_storico"
                result["stagioni_ponte"] = sorted(old.stagione.unique().tolist())
        elif len(old_ids) > 1:
            result["stato"] = "ponte_storico_ambiguo"
        elif len(candidates) == 1:
            chosen = candidates[0]
            result["metodo_ws"] = "nome_iniziali_club_univoci"
        else:
            result["stato"] = "ws_ambiguo" if candidates else "ws_non_trovato"
        if chosen is not None:
            current = catalog[catalog.playerId == chosen]
            result.update(playerId_ws=chosen, stato="collegato", copertura_ws_corrente=not current.empty)
            current_names = sorted(current.playerName.dropna().unique())
            old_names = old.loc[old.playerId_ws == chosen, "nome_ws"].dropna().tolist()
            result["nome_ws"] = current_names[0] if current_names else old_names[-1] if old_names else None
            result["club_ws_osservati"] = sorted(current.team.dropna().unique().tolist())
            if current.empty:
                result["stato"] = "collegato_solo_storico"
            elif len(clubs) == 1 and clubs[0] not in set(current.teamId):
                result["stato"] = "club_corrente_da_verificare"
        results.append(result)
    # Nessun ID WS assegnato a due ID FC: non scegliere il primo incontrato.
    reverse = {}
    for r in results:
        if r["playerId_ws"] is not None:
            reverse.setdefault(r["playerId_ws"], set()).add(r["giocatore_id_fc"])
    for r in results:
        if r["playerId_ws"] is not None and len(reverse[r["playerId_ws"]]) > 1:
            r["stato"] = "collisione_id_ws"
    return results


def check_ownership(records):
    seen = set()
    for record in records:
        if record.get("giocatore_id_fc") is None:
            continue
        key = (record["lega"], record["giocatore_id_fc"])
        if key in seen:
            raise RoseError(f"Giocatore assegnato due volte nella lega: {key}")
        seen.add(key)
