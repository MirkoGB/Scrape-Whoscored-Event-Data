# -*- coding: utf-8 -*-
"""Diagnosi di una pagina partita: i dati ci sono, o non ci sono?

Esiste per una ragione precisa, e la ragione e' un errore che e' costato tempo.

Quando `matchCentreData` vale `null`, `getMatchData` di `main.py` fallisce cosi':

    metadata = script_content_list.pop(1)              # 'matchCentreData: null'
    json.loads(metadata[metadata.index('{'):])         # ValueError: substring not found

Il messaggio che arriva all'utente e' **`substring not found`**, che descrive
l'incidente meccanico e nasconde il fatto. Letto in un log, sembra un parser
rotto: manda a cercare un difetto nel codice — indentazione, tag sbagliato,
pagina non caricata — quando la verita' e' che **la fonte non ha quei dati**.
Sono due cose che richiedono azioni opposte: la prima si corregge, la seconda si
dichiara e si smette di ritentare.

Le 12 partite mancanti delle stagioni 2021-22 e 2022-23 sono tutte del secondo
tipo, verificato una per una: script di 5079 caratteri contro il ~1 MB di una
pagina con i dati, e `matchCentreData: null` in tutte e dodici.

Questo modulo **non importa selenium**: prende il testo dello script e lo
giudica, quindi e' verificabile dai test senza browser.
"""

from __future__ import annotations

import re

# Il valore nullo, tollerando spazi. `re.sub(r"[\n\t]*", "", ...)` di main.py
# toglie a capo e tabulazioni ma non gli spazi, quindi si accettano entrambe le
# forme, grezza e ripulita.
_NULLO = re.compile(r"matchCentreData\s*:\s*null\b")

OK = "ok"
DATI_ASSENTI = "dati_assenti"
SENZA_MATCHID = "senza_matchid"


def diagnosi(script_html: str | None) -> str:
    """`ok` | `dati_assenti` | `senza_matchid`.

    - `dati_assenti`: la pagina e' quella giusta e dichiara di non avere gli
      eventi. **Ritentare e' inutile**: e' una proprieta' della fonte.
    - `senza_matchid`: non e' la pagina attesa — pagina d'errore, consenso
      cookie, caricamento incompleto. Qui ritentare ha senso.
    """
    if not script_html:
        return SENZA_MATCHID
    if "matchId" not in script_html:
        return SENZA_MATCHID
    if _NULLO.search(script_html):
        return DATI_ASSENTI
    return OK


def spiega(verdetto: str) -> str:
    return {
        DATI_ASSENTI: "dati evento assenti alla fonte (matchCentreData null) "
                      "- inutile ritentare",
        SENZA_MATCHID: "pagina inattesa (nessun matchId) - ritentabile",
        OK: "dati presenti",
    }[verdetto]
