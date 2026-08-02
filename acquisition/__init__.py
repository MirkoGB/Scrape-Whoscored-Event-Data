"""Strato di acquisizione: tutto il codice che porta dati dentro il repository.

Il criterio che separa questo pacchetto da `sot/` non e' la fonte ma la
direzione: qui si scarica e si verifica, in `sot/` si modella. Un modulo che
legge da `data/` senza scaricare niente non sta qui.

Contenuto:

- `whoscored/` — gli script del fork che hanno prodotto i 380 CSV della Serie A
  2025-26. **Sono script, non moduli**: si eseguono direttamente
  (`python acquisition/whoscored/scrape_season.py`) e fanno import relativi alla
  propria cartella. Non c'e' `__init__.py` li' dentro, ed e' voluto: importarli
  come pacchetto non funziona e dichiararli importabili sarebbe una promessa
  falsa.

Tre vincoli valgono per ogni fonte che verra' aggiunta qui (Fase 7):

7. mai mescolare due definizioni della stessa grandezza senza averle prima
   misurate una contro l'altra;
8. ogni riga scaricata porta con se' la sua provenienza — fonte, URL, data,
   hash, e la definizione della metrica *in quella fonte*;
9. ogni download e' idempotente e ripartibile, e nessuna esecuzione puo'
   cancellare o sovrascrivere grezzo gia' acquisito.
"""
