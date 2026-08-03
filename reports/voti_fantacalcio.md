# Voti fantacalcio — acquisizione delle cinque stagioni

Generato da `scripts/run_voti_fantacalcio.py` il 2026-08-03.
Fonte: `https://www.fantacalcio.it/voti-fantacalcio-serie-a`, vista HTML pubblica.

## Esito in una riga

**190 pagine, 63.105 righe giocatore-partita, cinque
stagioni**, e il fantavoto della fonte si ricostruisce dai bonus **esattamente
su 57.574 righe su 57.574** — che e' la
verifica piu' forte che questa acquisizione permetta, perche' non passa da
nessun modello.

## Come e' stata presa

| | |
|---|---|
| base giuridica | autorizzazione dichiarata dall'utente, `docs/regole_fantacalcio.md` §7.1 dec. 1 |
| via scelta | **vista HTML pubblica** — chiude il `[NON DECISO]` di §7.1 |
| perche' non l'export | `/api/v1/Excel/...` risponde 401 senza credenziali (addendum di `phase7_fattibilita_fonte.md`) |
| `User-Agent` | `SoT-Serie-A-research/1.0 (acquisizione autorizzata; ricerca statistica, nessuna redistribuzione dei contenuti)` |
| ritmo | una pagina ogni 3 s, dichiarato in `--sleep` |
| grezzo | `data/raw/fantacalcio/ITA-serie-a/<stagione>/voti/<gg>.html.gz`, 8.3 MB |
| provenienza | `data/raw/manifest.json`, con **due** hash: del `.gz` e dell'HTML servito |

Il `User-Agent` **non finge di essere un browser**. Dichiararsi Chrome per
passare inosservati sarebbe la forma piu' banale di aggiramento, vietata
dall'art. 3.3(e) dei Termini e non coperta da nessuna autorizzazione; ed e'
inutile, perche' la fonte serve regolarmente le pagine a questa stringa.

## Copertura

| stagione | giornate | partite | squadre | righe | righe_giocatore | righe_allenatore | righe_per_partita |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2021-2022 | 38 | 380 | 20 | 12471 | 11711 | 760 | 30.8 |
| 2022-2023 | 38 | 380 | 20 | 12640 | 11881 | 759 | 31.3 |
| 2023-2024 | 38 | 380 | 20 | 12662 | 11902 | 760 | 31.3 |
| 2024-2025 | 38 | 380 | 20 | 12646 | 11886 | 760 | 31.3 |
| 2025-2026 | 38 | 380 | 20 | 12686 | 11926 | 760 | 31.4 |

**I denominatori si contano, non si assumono.** E' la lezione dell'acquisizione
WhoScored, dove l'Atalanta aveva 35 partite su 38 e assumere il denominatore
avrebbe nascosto la perdita.

## Il fantavoto si ricostruisce: 57.574/57.574

La fonte pubblica il voto, il fantavoto **e** separatamente le otto voci di
bonus. Le due strade devono chiudere, e chiudono con questo barema — ricavato
per differenza, non dichiarato dalla fonte:

| voce | valore |
|---|---:|
| gol segnato | +3 |
| gol subito | −1 |
| autorete | −2 |
| rigore segnato | +3 |
| rigore sbagliato | −3 |
| rigore parato | +3 |
| assist | +1 |
| **ammonizione** | **−0,5** |
| **espulsione** | **−1** |
| player of the match | **0** |

**Tre fatti che la riconciliazione ha portato a galla, e nessuno dei tre si
vede guardando la pagina resa:**

1. **I cartellini non sono una colonna di bonus.** Le otto voci non li
   contengono. Stanno come **classe CSS sullo span del voto**
   (`player-grade yellow-card`, `red-card`). Chi legge solo `data-value` li
   perde in silenzio, e valgono −0,5 e −1. Sono 7.884
   ammonizioni e 432 espulsioni sulle cinque stagioni.
2. **Il gol su rigore non e' anche in "gol segnati".** Sta solo in "rigori
   segnati" e vale +3 una volta sola. Sommare le due colonne conterebbe due
   volte lo stesso gol — ed e' l'errore che la riconciliazione ha escluso, non
   una precauzione: con il rigore contato nei gol restano 458
   righe con residuo +3.
3. **"Player of the match" ha una colonna ma non entra nel fantavoto** della
   fonte. E' un'opzione di lega, e nella lega dell'utente non c'e'.

> **Conseguenza da tenere ferma: il `FV` della fonte NON e' il fantavoto della
> lega dell'utente.** Il barema di `regole_fantacalcio.md` §1.1 contiene **+1 di
> porta inviolata**, che la fonte non applica — e si vede proprio dal fatto che
> la riconciliazione torna esatta *senza* di esso. Il fantavoto di lega va
> ricalcolato dalle colonne di bonus, e la porta inviolata **si deriva**
> (`ruolo == "p"` e `gol_subiti == 0`), non si legge. Vincolo 7: due definizioni
> della stessa grandezza non si mescolano.

## I codici di s.v., e la soglia che li riconosce

`data-value` non porta sempre un voto. Sopra 10 e' un **codice**, e i codici
sono conservati invece di essere appiattiti a nullo:

| scala | codice | righe |
|---|---:|---:|
| redazione | 55 | 5531 |
| statistico | 55 | 4644 |
| statistico | 56 | 8 |
| italia | 55 | 5222 |
| italia | 56 | 2 |

**`56` non compare mai sulla scala Redazione**, che e' quella che il progetto
usa: sta solo sulle altre due, e sempre su righe che la Redazione ha gia'
marcato `55`. Appiattire tutto a nullo avrebbe fatto sparire il fatto che le
sentinelle sono due e che le tre scale non usano lo stesso vocabolario.

> **La soglia dei 10 vale sul voto e non sul fantavoto**, ed e' l'unico errore
> che questa acquisizione ha davvero commesso — corretto prima di pubblicare i
> numeri, e riportato perche' e' istruttivo. Un voto sta in 0-10 (osservato:
> 3,0-9,5); un fantavoto no — Simeone, 9 con quattro gol, fa **21**. Applicando
> la stessa soglia a entrambi, ~1.000 fantavoti veri diventavano codici
> inesistenti; e quelle righe, diventate nulle, **uscivano dalla riconciliazione
> senza far rumore**, perche' un residuo nullo si filtra da solo. La verifica
> dichiarava 53.775/53.775 saltando proprio le righe dei marcatori — cioe' le
> uniche in cui il barema dei gol veniva messo alla prova. Ora il denominatore
> e' "righe con un voto" e una riga con il voto e senza fantavoto conta come
> fuori registro, non come riga da saltare.

## L's.v. osservato, e dove sta

| stagione | ingresso | righe | sv | quota_sv |
|---|---|---:|---:|---:|
| 2021-2022 | dal primo minuto | 8359 | 13 | 0.0016 |
| 2021-2022 | subentrato | 3352 | 1044 | 0.3115 |
| 2022-2023 | dal primo minuto | 8360 | 20 | 0.0024 |
| 2022-2023 | subentrato | 3521 | 1051 | 0.2985 |
| 2023-2024 | dal primo minuto | 8358 | 18 | 0.0022 |
| 2023-2024 | subentrato | 3544 | 1079 | 0.3045 |
| 2024-2025 | dal primo minuto | 8360 | 17 | 0.002 |
| 2024-2025 | subentrato | 3526 | 1150 | 0.3261 |
| 2025-2026 | dal primo minuto | 8361 | 18 | 0.0022 |
| 2025-2026 | subentrato | 3565 | 1121 | 0.3144 |

La fonte **dichiara che una soglia di minuti non esiste** ("Non esiste, e mai
esisterà, una regola che prevede che il voto venga dato a chi gioca un numero
minimo di minuti"). Quindi l's.v. non e' una funzione dei minuti e la regola
dell'80' resta cio' che §1.2 dice che sia: un'**assunzione di modello**, da
misurare sulla 2025-26 — l'unica stagione con entrambe le fonti — e non una
lettura. Questa tabella misura solo **dove** l's.v. si concentra, che e' un fatto.

## Il livello dei voti, stagione per stagione

| stagione | righe | con_voto | voto_medio | voto_sd | fantavoto_medio | gol | assist | ammonizioni | espulsioni | quota_sv |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 2021-2022 | 11711 | 10654 | 6.0024 | 0.6308 | 6.1638 | 1052 | 669 | 1683 | 89 | 0.0903 |
| 2022-2023 | 11881 | 10810 | 6.0002 | 0.5936 | 6.1426 | 943 | 624 | 1643 | 65 | 0.0901 |
| 2023-2024 | 11902 | 10805 | 5.9978 | 0.5896 | 6.148 | 968 | 617 | 1563 | 62 | 0.0922 |
| 2024-2025 | 11886 | 10719 | 5.9978 | 0.6019 | 6.1481 | 936 | 622 | 1392 | 78 | 0.0982 |
| 2025-2026 | 11926 | 10787 | 5.981 | 0.602 | 6.1268 | 900 | 575 | 1357 | 66 | 0.0955 |

Per ruolo, con l'allenatore escluso da tutte le righe:

| stagione | ruolo | righe | con_voto | voto_medio | fantavoto_medio | quota_sv |
|---|---|---:|---:|---:|---:|---:|
| 2021-2022 | a | 2550 | 2242 | 6.1122 | 6.872 | 0.1208 |
| 2021-2022 | c | 4106 | 3710 | 6.0209 | 6.2623 | 0.0964 |
| 2021-2022 | d | 4283 | 3934 | 5.8916 | 5.9349 | 0.0815 |
| 2021-2022 | p | 772 | 768 | 6.1602 | 4.7936 | 0.0052 |
| 2022-2023 | a | 2453 | 2122 | 6.0521 | 6.6892 | 0.1349 |
| 2022-2023 | c | 4400 | 3994 | 6.0209 | 6.2568 | 0.0923 |
| 2022-2023 | d | 4258 | 3927 | 5.9155 | 5.9631 | 0.0777 |
| 2022-2023 | p | 770 | 767 | 6.1825 | 4.9557 | 0.0039 |
| 2023-2024 | a | 2414 | 2088 | 6.0824 | 6.7268 | 0.135 |
| 2023-2024 | c | 4447 | 4027 | 6.0137 | 6.2732 | 0.0944 |
| 2023-2024 | d | 4268 | 3921 | 5.9041 | 5.9513 | 0.0813 |
| 2023-2024 | p | 773 | 769 | 6.1632 | 4.9246 | 0.0052 |
| 2024-2025 | a | 2504 | 2123 | 6.0422 | 6.6755 | 0.1522 |
| 2024-2025 | c | 4360 | 3901 | 6.0227 | 6.2697 | 0.1053 |
| 2024-2025 | d | 4253 | 3929 | 5.9123 | 5.9738 | 0.0762 |
| 2024-2025 | p | 769 | 766 | 6.186 | 4.9621 | 0.0039 |
| 2025-2026 | a | 2465 | 2130 | 5.9908 | 6.5768 | 0.1359 |
| 2025-2026 | c | 4388 | 3933 | 5.9898 | 6.2286 | 0.1037 |
| 2025-2026 | d | 4302 | 3957 | 5.931 | 5.996 | 0.0802 |
| 2025-2026 | p | 771 | 767 | 6.1669 | 5.03 | 0.0052 |

> **Questa tabella e' descrittiva e va letta come tale.** Dice se il *livello*
> dei voti si e' mosso, non se il *criterio editoriale* e' cambiato: le due cose
> non coincidono, e la seconda non e' osservabile dall'esterno — la fonte non
> pubblica un changelog dei criteri di voto (§8 di
> `reports/phase7_fattibilita_fonte.md`). Il test formale di rottura, con il
> punto di rottura **cercato** e non assunto e con la potenza dichiarata, e'
> quello che la Fase 7 ha fatto sui tiri in `sot/recording_stability.py`: qui
> non e' stato rifatto, e finche' non lo e' la §5 delle regole resta aperta.

## Cosa c'e' nella tabella e cosa no

Una riga per giocatore sceso in campo per partita, 36 colonne,
tutte e tre le scale affiancate. La stessa tabella e' scritta in due forme:

| file | a cosa serve |
|---|---|
| `data/processed/ITA-serie-a/fantacalcio_voti.parquet` | e' la forma che i moduli leggono: conserva i tipi |
| `data/processed/ITA-serie-a/fantacalcio_voti.csv` | per aprirla fuori di qui |
| `data/processed/ITA-serie-a/fantacalcio_partite.parquet` · `data/processed/ITA-serie-a/fantacalcio_partite.csv` | il calendario: 1.900 partite con data, risultato e stadio |

**Se le due forme divergessero, quella giusta e' il Parquet.** Il CSV perde i
tipi: `giocatore_id`, che e' `Int64` con i nulli degli allenatori, in CSV e' una
colonna di testo, e riletto con `read_csv` senza `dtype` torna `float` —
`4431.0` invece di `4431`. E' la ragione per cui non e' il CSV a essere letto da
`sot/voti.py`.

**Non c'e' una riga per chi e' rimasto in panchina**: la fonte non lo elenca, e
inventare righe a zero dichiarerebbe un'assenza che non abbiamo osservato.
**Non ci sono i minuti**: non sono nel dato, e l'unico segnale di tempo di gioco
e' binario (`subentrato` / `sostituito`), senza minuto. Vengono da WhoScored.
**Venti righe per giornata sono allenatori** (`allenatore == True`,
`giocatore_id` nullo): prendono un voto come i giocatori e vanno filtrate da
qualunque media, o dentro c'e' il giudizio sul tecnico.

`giocatore_id` viene dall'URL del profilo ed e' **stabile fra stagioni**: e' la
chiave con cui ricucire l'identita' senza passare dai nomi, che la fonte
abbrevia e disambigua a mano (`Ivanovic M.`).

## Cosa resta aperto

- **Le quotazioni del listone non sono state prese.** Sono la verifica
  principale del progetto (F5) e stanno su un'altra pagina,
  `/quotazioni-fantacalcio`. Non erano nella richiesta.
- **La §5 delle regole non e' chiusa**: il confronto fra stagioni qui e'
  descrittivo. Vedi sopra.
- **Le nove domande del Blocco 0** restano quelle che sono, meno la prima: `D1`
  e' chiusa (i voti ci sono, la via e' la vista HTML), `D2` no.
