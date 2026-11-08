# Firefox aperto fuori dallo scaricamento

## Ricomparsa dell'8 novembre 2026

Nel registro dell'utente erano presenti esattamente quattro nuovi avvii
`-os-autostart`, per le copie Selenium 158.0, 158.0.1, 159.0 e 159.0.1.
Le sei attivita' di aggiornamento precedenti erano ancora disabilitate.
Le preferenze dei profili temporanei non coprivano tutti gli avvii delle
nuove copie: la sola pulizia delle registrazioni non era sufficiente.

Lo script ora offre una protezione persistente esplicita:

```powershell
& scripts/ripara_avvio_firefox.ps1 -PreventLogin -WhatIf
& scripts/ripara_avvio_firefox.ps1 -PreventLogin
```

Oltre alla pulizia mirata delle copie Selenium, imposta il DWORD
`HKCU:\Software\Policies\Mozilla\Firefox\DisableLaunchOnLogin` a `1`.
La [policy Mozilla](https://firefox-admin-docs.mozilla.org/reference/policies/disablelaunchonlogin/)
impedisce l'avvio al login per tutte le versioni Firefox dell'utente,
comprese quelle scaricate successivamente. L'apertura manuale e lo
scraping restano disponibili. Non cambia le impostazioni degli altri utenti.
Non disabilita gli aggiornamenti del Firefox personale.

Il backup `policy.json` registra esistenza, tipo e valore precedenti:
per annullare la policy ripristinare quel valore, oppure rimuovere solo
`DisableLaunchOnLogin` se `Existed` era `false`. Il backup `run.json`
conserva le voci di avvio rimosse. Una seconda esecuzione senza nuove
registrazioni non produce modifiche o ulteriori backup.

Se Windows richiede le credenziali di un account amministratore diverso,
usare `-TargetUserSid` con il SID dell'utente destinatario (ottenuto con
`whoami /user` nella sua sessione). Lo script risolve il profilo da
`ProfileList` e opera sull'hive gia' caricato in `HKEY_USERS`, evitando
di applicare la policy all'account amministratore.

## Intervento precedente

Il 13 ottobre 2026 le cinque finestre indesiderate erano processi delle copie
in `%USERPROFILE%\.cache\selenium\firefox`, avviati con `-os-autostart`.
Erano presenti sei valori `Mozilla-Firefox-*` nella chiave Run dell'utente
e sei attivita' `Firefox Background Update` relative alle stesse copie.

La protezione in `main.nuovo_driver` non era usata dal download settimanale:
`aggiorna_stagione.py` avvia `scrape_season.py`, che usa
`scrape_matches.build_driver`. Ora entrambi i costruttori chiamano
`configura_firefox_scraper` prima di avviare Firefox, anche quando Firefox
e' il ripiego dopo un errore di Chrome o si usa un geckodriver esplicito.
Le preferenze riguardano il profilo Selenium temporaneo.

La preferenza che controlla l'avvio al login e' documentata da
[Mozilla](https://firefox-admin-docs.mozilla.org/reference/policies/disablelaunchonlogin/).

Per pulire registrazioni gia' esistenti su questa macchina:

```powershell
# Prima ispezionare, poi applicare:
& scripts/ripara_avvio_firefox.ps1 -WhatIf
& scripts/ripara_avvio_firefox.ps1
```

Lo script salva valori Run e XML delle attivita' in
`reports/firefox_autostart_backup_<timestamp>`, disabilita le sole attivita'
delle copie Selenium e rimuove i loro avvii al login. Chiede la normale
chiusura delle finestre con `-os-autostart`, senza terminazioni forzate.
Non interviene sul Firefox installato o sull'attivita' del martedi'.
E' una riparazione una tantum, non un nuovo processo in background.

La pianificazione dei dati resta martedi' alle 21:00, incluso il recupero
gia' configurato delle esecuzioni saltate quando il PC era spento
(`StartWhenAvailable`). Questo recupero e' distinto dagli avvii Firefox
al login individuati qui.

Regressione senza browser o rete:

```powershell
.venv\Scripts\python.exe -m pytest tests/test_firefox_scraper.py tests/test_acquisizione_target.py -q
```
