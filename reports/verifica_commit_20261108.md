# Verifica della coda dei commit - 8 novembre 2026

L'intervento organizza le modifiche gia' presenti nella working tree in commit
per argomento. Ogni commit viene inviato separatamente a `origin/main`,
verificando subito dopo che il riferimento remoto coincida con quello locale.
Il punto di partenza era `04f3206`, gia' allineato a `origin/main`.

## Gruppi

1. Riordino documentazione e script R; esclusione output locali Graphify.
2. Gestione browser dello scraper e prevenzione avvio Firefox al login.
3. Acquisizione WhoScored/Wikipedia, cinque campionati, calendari e manifest.
4. Aggregazioni, metriche evento e confronto fra campionati.
5. Modello tiri: volume, precisione e validazione CRPS.
6. Previsioni correnti, totali, calendari e aggiornamento settimanale.
7. Verifica prospettica e previsioni congelate.
8. Analisi tattica e report Como-Inter.
9. Analisi over, registro previsioni e suggerimenti.
10. Quote Sisal, estensione e osservazioni acquisite.
11. Rose fantacalcio, regole, valutazioni e scambi.
12. Dashboard fantacalcio e convenienza degli scambi.
13. Contesto del progetto e questo verbale di verifica.

I backup di sistema, gli helper usati per i commit, i log completi e le cache
restano locali. La directory `graphify-out/` e' stata aggiunta a `.gitignore`:
contiene analisi generate, cache e dipendenze scaricate. I dati esterni e gli
snapshot congelati seguono invece le eccezioni gia' previste dal repository.

## Test Python

Comando eseguito dalla radice, con directory temporanea nuova dentro `reports/`
e `TEMP`/`TMP` diretti alla stessa directory per rispettare i permessi locali:

```powershell
.venv/Scripts/python.exe -m pytest tests -q --rootdir=. -p no:cacheprovider --basetemp <directory-temporanea>/pytest --junitxml=reports/commit_validation_pytest.xml
```

**1.393 test: 1.374 passati, 9 falliti, 10 saltati; durata 407,65 secondi.**
Nessun errore di setup nella corsa completa. Un tentativo precedente era stato
interrotto per accesso negato alla directory temporanea esterna al workspace.

I fallimenti erano presenti nelle modifiche iniziali; l'intervento di
raggruppamento non ha modificato le implementazioni o le asserzioni coinvolte.
La suite non e' verde e questi risultati non costituiscono una certificazione
di correttezza delle funzionalita' archiviate.

| Area | Esito osservato |
| --- | --- |
| Pagina previsioni | HTML salvato e previsione ricalcolata sui dati attuali differiscono: 16,5256 contro 15,1411 per il caso confrontato. |
| Coerenza fonti calendario | Juventus-Venezia compare soltanto nella fonte WhoScored del confronto. |
| Date calendario | Alcune date della Premier League non vengono interpretate; la costruzione dei turni arriva a indicizzare un valore non valido. Tre test falliscono su questa famiglia. |
| Pagina calendario | Una partita della pagina salvata non si trova nel calendario corrente. |
| Verifica prospettica | Due controlli dipendono da casi storici che i dati locali correnti non presentano piu': coppia ambigua e fonte completa. |
| Convenzioni dei percorsi | La guardia segnala percorsi con stagione fuori da `config.py`, insieme ad alcune stringhe descrittive intercettate dalla stessa espressione regolare. |

Test falliti:

- `tests/test_fase14.py::test_la_pagina_contiene_i_numeri_della_previsione`
- `tests/test_fase15_calendario.py::test_le_due_fonti_concordano_sulle_partite_da_giocare`
- `tests/test_fase15_pagina.py::test_le_date_dei_calendari_veri_si_leggono_tutte`
- `tests/test_fase15_pagina.py::test_nessun_turno_supera_la_capienza_sui_dati_veri`
- `tests/test_fase15_pagina.py::test_i_turni_partizionano_le_partite`
- `tests/test_fase15_pagina.py::test_la_pagina_contiene_i_numeri_del_calendario`
- `tests/test_fase16_o1.py::test_una_coppia_ambigua_non_diventa_un_disaccordo`
- `tests/test_fase16_o1.py::test_il_controllo_positivo_e_totale_dove_la_fonte_e_completa`
- `tests/test_layout.py::test_nessun_percorso_con_stagione_scritto_a_mano`

Dei 10 test saltati, 9 richiedono percorsi locali espliciti di Chrome e driver;
uno riguarda il prior in una stagione che attualmente non lo usa.

## Controlli JavaScript

```powershell
$nodeTests = @(Get-ChildItem tests -File -Filter '*.cjs' | Select-Object -ExpandProperty FullName)
node --test @nodeTests
```

**33 test passati, 0 falliti**, inclusi i confronti dei motori della dashboard.
Durata 106,03 secondi. I controlli di parita' che leggono gli artefatti sotto
`reports/` richiedono tali artefatti locali anche dopo il clone.

## Altri controlli

- Inventario esplicito dei file per gruppo e verifica dell'indice prima di ogni commit.
- Verifica degli spostamenti dei documenti e degli script R.
- Controllo dei nuovi file testuali per alcune forme comuni di credenziali;
  non equivale a una scansione esaustiva.
- Rimozione di uno spazio finale nel lettore dell'estensione Sisal, senza
  cambiamenti di comportamento.
- Nessuna rigenerazione dei dati grezzi o delle previsioni storiche per far
  passare le verifiche.
