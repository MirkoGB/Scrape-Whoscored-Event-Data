# Fase 6D — i predittori nel regime a bassa informazione

In Fase 2 gli otto candidati sono stati misurati come valore **incrementale** contro un effetto attacco con trenta e piu' giornate di storia. Sono medie mobili della squadra stessa: li' sono collineari con l'effetto attacco, e la conclusione "ripetono l'informazione invece di aggiungerla" vale in quel regime. Qui si verifica l'ipotesi mai testata: che paghino dove l'effetto attacco e' ancora acerbo.

**Cambia solo l'insieme di valutazione.** Stesse previsioni walk-forward, stesso split per data, stessa griglia di `alpha` scelta sul solo passato, stessi predittori, stessa soglia dichiarata in anticipo (`t > 2.0`), stessa correzione per la molteplicita' di otto candidati. Nessun parametro e' ristimato sul regime.

## Esito in breve

1. **Nessun predittore passa in nessun regime.** Nel maturo il massimo e' +1.42, nell'acerbo +0.88, sulle sole righe escluse dal burn-in +1.45. Su otto candidati indipendenti il massimo atteso sotto l'ipotesi nulla e' 1.42: p del massimo 0.48 / 0.81 / 0.46.
2. **Ma il test acerbo, da solo, non ha la potenza per dirlo.** Su 100 righe la potenza contro l'effetto per riga piu' grande mai osservato nel regime maturo (`poss_att`, +0.00579 di log-verosimiglianza per riga) vale **11%**. Il pavimento di un test a una coda con soglia 2.0 e' 2.3%: quel 11% e' quasi tutta la distanza dal caso. Un `t` sotto soglia li' dentro **non e' una conferma**.
3. **Nemmeno il test piu' potente disponibile rifiuta.** Stimando i coefficienti **sulle sole righe del regime** — cioe' guardandole tutte, il massimo favore possibile — il rapporto di verosimiglianza da', nell'acerbo, un minimo di p = 0.093 (`poss_att`), che sugli otto candidati diventa 0.54; nel disgiunto p = 0.034 (`xgps_att`) → 0.24. E' un test **in campione**, quindi un suo rifiuto non avrebbe dimostrato valore predittivo; ma un suo non-rifiuto chiude la questione, perche' non esiste un test piu' sensibile da provare dentro questa specificazione. **E' qui, non nel `t`, che il risultato negativo di Fase 2 si estende al regime acerbo** — con l'avvertenza, spiegata sotto, che la penalita' ridge rende quel `p` approssimato, di un fattore che a questi valori non cambia la lettura.
4. **`xg_per_shot` non risorge.** Nell'acerbo fa +0.86 di `t` contro -0.82 nel maturo — cambia segno, ma resta a meno di meta' della soglia. E' il caso piu' vicino a qualcosa in tutto il blocco: nel regime disgiunto ha p in campione = 0.034, che sugli otto candidati diventa 0.24. Su 40 righe, in campione, dopo aver guardato tre regimi: e' l'aspetto che ha il rumore, non una scoperta. **Resta scartato.**

---

## 1. I regimi, e quante righe hanno davvero

| regime | `team_match_idx` | righe valutabili | note |
|---|---|---|---|
| acerbo | 1-8 | **100** | le prime 3 partite non hanno previsione: a quelle date il campionato non ha ancora le 30 partite che `date_splits` pretende. L'insieme parte dalla quarta |
| maturo | 6-38 | **660** | e' esattamente il campione valutato dalla Fase 2 |
| acerbo disgiunto | 1-5 | **40** | solo righe **mai** valutate prima (partite 4 e 5) |

I primi due regimi **si sovrappongono** sulle partite 6-8: 60 delle 100 righe acerbe sono anche fra le 660 mature. Il terzo regime esiste per questo: e' l'unico confronto davvero disgiunto, e paga la disgiunzione con meta' delle righe.

**Il troncamento a partite 4-8 e' una perdita reale, e va detta.** L'ipotesi da testare riguarda il regime a informazione minima, che sono le prime giornate; le prime tre — quelle in cui l'effetto attacco e' letteralmente non identificato — non sono valutabili senza cambiare il protocollo di stima, e cambiarlo qui vorrebbe dire confrontare due esperimenti diversi. Alla quarta partita ciascuna squadra ha gia' tre partite di storia.

---

## 2. Il test, regime per regime

`d_oos` = guadagno di log-verosimiglianza **fuori campione** sul modello base, sommato sulle righe del regime; `t` = statistica appaiata sullo stesso guadagno; `mde_oos` = guadagno che sarebbe servito per avere l'80% di probabilita' di superare la soglia; `d_ins` = variazione **in campione** sulle stesse righe con la stima di Fase 2 (tutte le 760 righe, `as_of` a fine stagione); `d_ins_regime` = la stessa cosa con i coefficienti stimati **sulle sole righe del regime**; `p_lr` = il p del rapporto di verosimiglianza su quel guadagno.

I due numeri in campione non sono intercambiabili, e nessuno dei due va letto come un guadagno. `d_ins` sta qui per continuita' con la Fase 2, ma non descrive il regime: il decadimento a 150 giorni pesa le prime giornate per circa un terzo, quindi quei coefficienti non sono scelti per l'acerbo. `d_ins_regime` lo e', e su di esso si calcola `p_lr` confrontando `2 x d_ins_regime` con un chi-quadro a un grado di liberta'. Sotto l'ipotesi nulla quel guadagno vale in media 0.5: e' il sovradattamento che un parametro libero regala comunque, ed e' la ragione per cui la colonna da leggere e' `p_lr` e non il guadagno.

**Perche' `d_ins_regime` e' negativo per sei candidati su otto nel regime maturo.** Non e' un errore numerico, ed e' la cosa piu' interessante della tabella. Quello che il modello minimizza non e' la verosimiglianza: e' verosimiglianza pesata **piu' la penalita' ridge** su attacco e difesa. Un predittore collineare con l'effetto attacco compra una riduzione della penalita' e paga in adattamento. Sulle 660 righe mature, con `alpha` = 12:

| modello | verosimiglianza grezza | penalita' ridge | obiettivo |
|---|---|---|---|
| base | -1377.61 | 10.54 | -691.62 |
| + `poss_att` | -1377.98 | 5.91 | -696.06 |

L'obiettivo migliora, come deve; la penalita' quasi si dimezza; la verosimiglianza peggiora. **E' la sostituzione che la Fase 2 aveva dedotto dal risultato fuori campione, qui visibile direttamente nei due termini.** Ne segue anche un limite di questo blocco: con una penalita' in mezzo, `p_lr` e' approssimato — la distribuzione nulla esatta di un rapporto di verosimiglianza penalizzato non e' un chi-quadro a un grado di liberta'. Vale come ordine di grandezza, e nessuno dei valori e' cosi' vicino alla soglia da rendere la differenza importante.

### Regime maturo — 660 righe

| predittore   |   n |   d_oos |       t |   mde_oos |   d_ins |   d_ins_regime |   p_lr |
|:-------------|----:|--------:|--------:|----------:|--------:|---------------:|-------:|
| poss_att     | 660 |  3.8207 |  1.4201 |    7.6453 |  0.2573 |        -0.367  | 1      |
| tilt_att     | 660 |  3.4397 |  1.337  |    7.3107 |  0.6963 |         0.072  | 0.7043 |
| box_att      | 660 |  1.8638 |  0.8877 |    5.9664 | -0.5255 |        -1.7967 | 1      |
| xgps_def     | 660 |  0.1036 |  0.1567 |    1.8783 |  0.3113 |         0.2279 | 0.4996 |
| ppda_att     | 660 | -0.0145 | -0.0132 |    3.1341 | -0.4288 |        -1.1052 | 1      |
| dist_att     | 660 | -0.2047 | -0.3122 |    1.8627 | -0.334  |        -1.4841 | 1      |
| xgps_att     | 660 | -1.0772 | -0.8171 |    3.7461 |  0.1614 |        -0.5783 | 1      |
| ppda_def     | 660 | -1.0393 | -1.1817 |    2.4992 | -0.4591 |        -0.6046 | 1      |

Predittori tenuti: **nessuno**. Massimo `t` = +1.420, p del massimo su otto candidati = 0.477; soglia di famiglia al 5% (Sidak) = 2.49. In campione, sulle sole righe del regime, il minimo `p_lr` e' 0.500 (`xgps_def`), che sugli otto candidati vale 1.00.

### Regime acerbo — 100 righe

| predittore   |   n |   d_oos |       t |   mde_oos |   d_ins |   d_ins_regime |   p_lr |   potenza_vs_maturo |   potenza_vs_tetto |
|:-------------|----:|--------:|--------:|----------:|--------:|---------------:|-------:|--------------------:|-------------------:|
| poss_att     | 100 |  0.6592 |  0.8794 |    2.1302 | -0.7442 |         1.4139 | 0.0926 |              0.1098 |             0.2174 |
| xgps_att     | 100 |  0.9628 |  0.8584 |    3.1873 | -0.6766 |         1.1713 | 0.1259 |              0.016  |             0.0805 |
| dist_att     | 100 |  0.3281 |  0.6164 |    1.5124 | -0.5736 |         0.1697 | 0.5602 |              0.0198 |             0.0228 |
| ppda_def     | 100 |  0.268  |  0.502  |    1.5172 | -0.0964 |         0.788  | 0.2093 |              0.0109 |             0.0721 |
| box_att      | 100 |  0.3936 |  0.3557 |    3.1438 | -1.0998 |         0.6386 | 0.2584 |              0.0405 |             0.0304 |
| tilt_att     | 100 |  0.293  |  0.2922 |    2.8496 | -1.1815 |         0.8633 | 0.1889 |              0.0694 |             0.0507 |
| ppda_att     | 100 |  0.0082 |  0.0347 |    0.668  | -1.2983 |         0.0597 | 0.7296 |              0.0222 |             0.0228 |
| xgps_def     | 100 | -0.1858 | -0.3017 |    1.7497 |  0.1353 |         0.2341 | 0.4938 |              0.0242 |             0.0228 |

Predittori tenuti: **nessuno**. Massimo `t` = +0.879, p del massimo su otto candidati = 0.814; soglia di famiglia al 5% (Sidak) = 2.49. In campione, sulle sole righe del regime, il minimo `p_lr` e' 0.093 (`poss_att`), che sugli otto candidati vale 0.54.

### Regime acerbo disgiunto — 40 righe

| predittore   |   n |   d_oos |       t |   mde_oos |   d_ins |   d_ins_regime |   p_lr |   potenza_vs_maturo |   potenza_vs_tetto |
|:-------------|----:|--------:|--------:|----------:|--------:|---------------:|-------:|--------------------:|-------------------:|
| xgps_att     |  40 |  0.8641 |  1.4458 |    1.6984 | -0.5853 |         2.2479 | 0.034  |              0.0175 |             0.8224 |
| ppda_def     |  40 |  0.2206 |  0.9501 |    0.6599 |  0.0191 |         0.783  | 0.2108 |              0.0116 |             0.2173 |
| poss_att     |  40 |  0.0983 |  0.4793 |    0.5825 | -0.4619 |         0.9527 | 0.1675 |              0.192  |             0.5825 |
| dist_att     |  40 |  0.0763 |  0.2886 |    0.7508 | -0.5343 |         0.0351 | 0.7911 |              0.0203 |             0.0228 |
| xgps_def     |  40 | -0.2484 | -0.4908 |    1.438  |  0.3785 |        -0.0018 | 1      |              0.0234 |             0.0228 |
| box_att      |  40 | -0.0748 | -0.7594 |    0.28   | -1.2178 |         0.3922 | 0.3758 |              0.1966 |             0.0228 |
| tilt_att     |  40 | -0.2003 | -0.8563 |    0.6646 | -0.8027 |         1.1238 | 0.1338 |              0.1338 |             0.7477 |
| ppda_att     |  40 | -0.067  | -0.9857 |    0.1931 | -0.1704 |         0.4966 | 0.319  |              0.0221 |             0.0228 |

Predittori tenuti: **nessuno**. Massimo `t` = +1.446, p del massimo su otto candidati = 0.460; soglia di famiglia al 5% (Sidak) = 2.49. In campione, sulle sole righe del regime, il minimo `p_lr` e' 0.034 (`xgps_att`), che sugli otto candidati vale 0.24.

---

## 3. La potenza, cioe' cosa questi `t` possono dire

Un `t` sotto soglia su cento righe non dice "il predittore non serve": dice "questo test non l'avrebbe visto". Le due frasi si distinguono solo calcolando contro quale effetto il test avrebbe avuto una probabilita' decente di rifiutare. Due alternative, entrambe dichiarate prima di guardare i risultati:

- **contro il maturo**: l'effetto per riga che lo *stesso* predittore mostra sulle 660 righe. Se qui valesse quanto vale li', lo vedremmo?
- **contro il proprio tetto in campione** (`potenza_vs_tetto`): il guadagno ottenuto sulle righe del regime con i coefficienti stimati **su quelle stesse righe**, meno i 0.5 punti che il sovradattamento regala comunque. Fuori campione non puo' rendere di piu'.

| regime | righe | `se` per riga di `poss_att` | MDE per riga | potenza contro il miglior effetto maturo |
|---|---|---|---|---|
| maturo | 660 | 0.00408 | 0.01158 | **28%** |
| acerbo | 100 | 0.00750 | 0.02130 | **11%** |
| acerbo disgiunto | 40 | 0.00512 | 0.01456 | **19%** |

L'alternativa comune e' l'effetto per riga di `poss_att` nel regime maturo (+0.00579), il piu' grande che gli otto candidati abbiano mai prodotto su questi dati; l'errore standard e' quello di `poss_att` **in ciascun regime**, non la media degli otto, che sarebbe dominata dai candidati a varianza minuscola e descriverebbe un test mai fatto.

Il 28% del regime maturo non e' una notizia indipendente: li' l'alternativa **coincide** con l'effetto osservato, quindi quella potenza e' solo un altro modo di scrivere t = 1.42. I numeri informativi sono gli altri due — ed e' esattamente il punto: la Fase 2 aveva concluso con un test che, contro il migliore dei propri effetti, rifiutava una volta su 4. La differenza fra i regimi non e' che uno e' potente e l'altro no; e' che nessuno dei due lo e', e l'unica cosa conclusiva del blocco e' il test in campione della sezione 2.

Le colonne `potenza_vs_maturo` delle tabelle sopra usano invece l'effetto di **ciascun** predittore, e sono quasi tutte piu' basse ancora, perche' quasi tutti gli effetti maturi sono vicini a zero o negativi. Contro un'alternativa negativa la potenza scende **sotto** il pavimento 2.3%, ed e' corretto cosi': quel test non cerca un peggioramento.

Un'ultima lettura, che va contro l'intuizione: il MDE per riga di `poss_att` passa da 0.01158 nel maturo a 0.02130 nell'acerbo, cioe' ×1.8, mentre la sola perdita di righe (660 → 100) ne giustificherebbe ×2.6. La variabilita' per riga della differenza di log-verosimiglianza e' quindi **piu' piccola** nelle prime giornate: il regime acerbo perde potenza per il numero di righe, non per il rumore.

---

## 4. La premessa del blocco, verificata: baseline stupidi accanto

L'ipotesi da testare e' che i predittori paghino **dove l'effetto attacco e' debolmente identificato**. Che il regime acerbo sia davvero quel posto non va assunto: si guarda quanto il modello stacca i baseline li' dentro, contro quanto li stacca a stagione matura.

### Regime maturo

| modello                    |   n |    mae |   loglik |   d_loglik_vs_modello |   t_vs_modello |
|:---------------------------|----:|-------:|---------:|----------------------:|---------------:|
| Poisson ridge att/dif/casa | 660 | 1.7395 | -1418.94 |                0      |       nan      |
| media campionato           | 660 | 1.8771 | -1488.03 |               69.0886 |         5.1493 |
| media casa/trasferta       | 660 | 1.8802 | -1475.32 |               56.3865 |         4.6322 |
| media squadra              | 660 | 1.8116 | -1447.79 |               28.8552 |         2.8218 |
| media squadra + campo      | 660 | 1.7851 | -1434.71 |               15.7718 |         1.8392 |

### Regime acerbo

| modello                    |   n |    mae |   loglik |   d_loglik_vs_modello |   t_vs_modello |
|:---------------------------|----:|-------:|---------:|----------------------:|---------------:|
| Poisson ridge att/dif/casa | 100 | 1.6782 | -213.987 |                0      |       nan      |
| media campionato           | 100 | 1.7585 | -217.937 |                3.9505 |         0.8094 |
| media casa/trasferta       | 100 | 1.7653 | -218.39  |                4.4037 |         0.922  |
| media squadra              | 100 | 1.7476 | -220.276 |                6.289  |         1.0999 |
| media squadra + campo      | 100 | 1.7258 | -218.176 |                4.1891 |         0.9217 |

### Regime acerbo disgiunto

| modello                    |   n |    mae |   loglik |   d_loglik_vs_modello |   t_vs_modello |
|:---------------------------|----:|-------:|---------:|----------------------:|---------------:|
| Poisson ridge att/dif/casa |  40 | 1.7261 | -88.8714 |                0      |       nan      |
| media campionato           |  40 | 1.651  | -85.9242 |               -2.9472 |        -1.5242 |
| media casa/trasferta       |  40 | 1.7697 | -88.5741 |               -0.2972 |        -0.1856 |
| media squadra              |  40 | 1.7    | -91.0748 |                2.2035 |         0.4373 |
| media squadra + campo      |  40 | 1.7826 | -92.2491 |                3.3777 |         0.9062 |

I due confronti che contano dicono cose diverse, e vanno riportati tutti e due:

- contro **`media campionato`**, cioe' l'intero contenuto informativo del modello: +0.0395 per riga nell'acerbo contro +0.1047 nel maturo, e nel regime disgiunto **-0.0737**, cioe' alle partite 4-5 il modello e' *peggio* del numero unico per tutti. **La premessa del blocco regge**: li' l'effetto attacco vale poco o niente, ed e' esattamente il posto in cui un predittore avrebbe spazio.
- contro **`media squadra + campo`**, cioe' il valore *incrementale* della ridge sopra una media di squadra: +0.0419 per riga nell'acerbo contro +0.0239 nel maturo — qui il modello sta **meglio** da acerbo, non peggio. Non e' una contraddizione: con tre o quattro partite la media di squadra e' pessima e lo shrinkage della ridge vale molto, mentre a stagione matura le due cose convergono. Il primo confronto misura quanta informazione c'e', il secondo quanto serve regolarizzarla.

Messi insieme: nelle prime giornate **c'e' meno informazione di squadra** — che e' la premessa — e nessuno dei candidati la sostituisce, nemmeno con i coefficienti scelti su quelle righe.

Nota di lettura sui `t` di questa sezione: sono calcolati sulla log-verosimiglianza Poisson, come il test dei predittori. La Fase 2 riporta 1.86 contro `media squadra + campo` perche' li' il confronto usa la NB2 con r = 26; e' la stessa quantita' misurata con due dispersioni diverse, non due risultati.

---

## Limiti di questo blocco

- **Il test acerbo ha potenza 11%, e da solo non conclude.** Il suo non-rifiuto e' compatibile sia con "i predittori non servono nemmeno da acerbi" sia con "servono e queste righe non bastano a vederlo". Cio' che permette di scegliere fra le due non e' il `t`, e' il test in campione — e va detto che vale solo **per questi otto predittori**, non per la classe delle medie mobili da dati evento in generale.
- **Anche il test maturo aveva potenza 28%** contro il migliore dei propri effetti. Il "nessuno passa" di Fase 2 resta corretto, ma la sua forza veniva dal fatto che gli effetti misurati erano piccoli, non dal fatto che il test fosse sensibile. Questo blocco corregge la lettura, non il risultato.
- **Il regime acerbo e' troncato alle partite 4-8** (le prime tre non hanno previsione) e **si sovrappone** al maturo su 6-8. Il regime disgiunto elimina la sovrapposizione ma scende a 40 righe, con potenza 19%: e' un controllo, non un test.
- **Tre regimi sono tre sguardi sugli stessi otto candidati.** La correzione riportata copre gli otto candidati dentro un regime, come in Fase 2, non i regimi fra loro. Non e' stato necessario stringerla perche' nessun `t` si e' avvicinato alla soglia: se uno l'avesse superata, andrebbe ripesato su tutta la famiglia.
- **I candidati non sono indipendenti** — possesso, field tilt e tocchi in area misurano cose vicine. La correzione per il massimo assume indipendenza ed e' quindi **piu' severa del vero**; con correlazione positiva il p del massimo reale sarebbe piu' alto, cioe' ancora meno favorevole a una scoperta.
- **`alpha` nelle prime giornate e' il valore centrale della griglia**, non una scelta: la selezione cumulativa non ha ancora storia sufficiente. E' lo stesso comportamento del modello base e dei candidati, quindi il confronto appaiato resta valido, ma il regime acerbo non e' un regime in cui `alpha` sia stato ottimizzato.
- **Il test in campione e' in campione.** Stima il coefficiente sulle righe su cui poi lo giudica: se avesse rifiutato, non avrebbe dimostrato valore predittivo, e non andrebbe usato in nessuna affermazione sul modello. Vale come **limite superiore**, cioe' solo nella direzione in cui e' stato usato qui. Ed e' un limite per *questa* specificazione: non esclude che una trasformazione diversa dello stesso predittore abbia un coefficiente utile.
- **`xg_per_shot` resta scartato.** Testato in un regime diverso, non reintrodotto. Fuori campione non si avvicina alla soglia in nessuno dei tre regimi; in campione, sulle 40 righe del disgiunto, e' il solo candidato con un p sotto 0.05 prima della correzione per la molteplicita' — e sopra dopo. Riportato perche' e' il risultato, non perche' cambi la conclusione.
- **Controllo di riproducibilita'**: il regime maturo ricalcolato qui riproduce `phase2_predittori.csv` con uno scarto massimo sul `t` di 5.6e-17. Se un giorno divergesse, i due esiti non sarebbero piu' confrontabili e questo report non andrebbe letto.