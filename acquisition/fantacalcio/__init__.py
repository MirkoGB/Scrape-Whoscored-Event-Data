# -*- coding: utf-8 -*-
"""Acquisizione dei voti fantacalcio da `fantacalcio.it`.

**Differenza strutturale rispetto a `acquisition/whoscored/`**: quello e' un
insieme di *script* ereditati dal fork e non ha `__init__.py`; questo e' un
*pacchetto* vero, importabile come `acquisition.fantacalcio`. La ragione e'
pratica prima che estetica: la cartella WhoScored espone gia' i nomi `target` e
`pagina`, e i test la mettono in `sys.path`. Due moduli `target` importabili per
nome nudo nello stesso processo pytest sarebbero lo stesso oggetto in
`sys.modules`, e il secondo import restituirebbe silenziosamente il primo.

Contenuto:

- `target.py`  — risoluzione campionato + stagione + giornata, URL e percorsi.
  **Non importa `requests`**: e' verificabile dai test senza toccare la rete,
  per la stessa ragione per cui `whoscored/target.py` non importa selenium.
- `pagina.py`  — il parser. Funzione pura da byte HTML a righe: nessuna rete,
  nessuna scrittura. E' dove vive tutta la conoscenza del markup della fonte.
- `scrape_voti.py` — l'unico modulo che apre una connessione.

Base giuridica dell'acquisizione: **autorizzazione dichiarata dall'utente**
(`docs/regole_fantacalcio.md` §7.1, decisione 1), estesa esplicitamente allo
scraping dei voti, che soddisfa l'art. 3.3(a) dei Termini di Utilizzo per la via
che lo stesso articolo prevede. Il repository ne registra la dichiarazione, non
ne conserva il documento — come per l'autorizzazione WhoScored.
"""
