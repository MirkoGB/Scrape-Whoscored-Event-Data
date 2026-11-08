# Verifica delle regole ricevute

Le dichiarazioni sono registrate in `regole_in_revisione.json`. Le parti ambigue
non sono applicate a `leghe.json` o agli snapshot A–E. Il file compilato è preservato.
Le precisazioni successive della conversazione sono in `precisazioni_regole.json`.

| Lega | Formato / voti confermati | Dimensione dichiarata | Rose esportate | Capitano |
|---|---|---:|---|---|
| fantagas2020 | classic / redazione | 25 | 25 | Voto base − 6 |
| fantamassa21 | mantra / redazione | Massimo 35 | 32, 35 | Voto base − 6 |
| fantaonlyfans | classic / redazione | 25 | 25 | Voto base − 6 |
| fantaunipdgiantiamiamo | classic / redazione | 25 | 25 | Assente |
| fantazavomerda | classic / statistico | 29 | 26, 27, 29 | Assente |

## Conferme registrate

- Stagione 2026/27 e rose dichiarate invariate per tutte le leghe.
- Fantamassa è ricondotta a `fantamassa21`; restrizione capitano Pc/A conservata.
- Confermati tutti gli undici moduli ufficiali Mantra; sette moduli standard Classic.
- Capitano nelle tre leghe in cui è attivo: modificatore aggiuntivo = voto base − 6.
  Esempi: 5 → −1; 5,5 → −0,5; 6 → 0; 6,5 → +0,5; 7 → +1.
  Usa il voto base, prima dei bonus/malus; non il fantavoto.
- Sostituzioni esclusivamente nello stesso ruolo, anche in Mantra, senza adattamenti.
- Nessun tetto numerico ai cambi: ingressi limitati da disponibilità delle riserve,
  ruoli e composizione della panchina. «Illimitato» non crea riserve aggiuntive.
- Fantamassa: massimo 35 giocatori, corretto dall’utente. Tutte le otto rose,
  comprese quelle da 32 giocatori, rispettano questo limite.
- Fantagas2020, fantaonlyfans e fantaunipd: tutte le 26 rose rispettano 3P–8D–8C–6A.
- Fantazavomerda: tutte le 12 rose hanno almeno due portieri.
- Attivazione della difesa con almeno quattro difensori; senza voto esclusi dalla media.
- Media difesa: migliori quattro voti fra portiere e difensori schierati; il portiere
  può restare escluso dai quattro. Con meno di quattro voti utili dopo i cambi il modificatore non si applica.
- Sotto la media del 6: modificatore zero per fantagas2020, fantamassa21, fantaonlyfans
  e fantaunipdgiantiamiamo. Le fasce negative di fantazavomerda sono conservate.
- Panchina fantagas2020 e fantaonlyfans: 1P–2D–2C–2A (7 posti). Nelle altre tre è libera;
  resta da specificare la precedenza fra riserve dello stesso ruolo.
- Budget iniziali conservati come dichiarazioni, senza dedurne i crediti residui.
- Finestre degli scambi dichiarate nelle soste nazionali; date e reintegri non dedotti.

## Bonus e malus confermati

| Evento | fantagas2020 / fantaonlyfans | fantamassa21 / fantaunipd | fantazavomerda |
|---|---:|---:|---:|
| Gol non su rigore | +3 | +3 | +3 |
| Rigore segnato | +3 | +3 | +2 |
| Rigore sbagliato | −3 | −3 | −2 |
| Assist | +1 | Quality: +0,5 / +1 / +1,5 | Quality: +0,5 / +1 / +1,5 |
| Ammonizione | −0,5 | −0,5 | −0,5 |
| Espulsione | −1 | −1 | −1 |
| Autorete | −2 | −2 | −2 |
| Gol subito | −1 | −1 | −1 |
| Porta inviolata | +1 | +1 | +1 |
| Rigore parato | +3 | +3 | +3 |

Gol su azione e rigori segnati sono eventi separati nella fonte: il rigore
riceve un solo bonus, +3 oppure +2 secondo la lega.

## Informazioni ancora necessarie

1. Precedenza fra riserve dello stesso ruolo;
   gestione senza voto e voti politici/rinvii, capitano senza voto;
   eventuale limite di posti nelle tre panchine a composizione libera.
2. Fantazavomerda: Lula FC ha 27 giocatori e PIO AVE 26, contro i 29 dichiarati.
   Precisare se 29 è un massimo o un totale obbligatorio; nessuna rosa viene corretta.
3. Crediti negli scambi, costi assegnati dopo lo scambio e regole di reintegro per 2×1.
   «Tutti gli scambi ammessi» non determina come completare una rosa incompleta.

## Conseguenze per C e D

Il calcolo separato `calcola_convenienza_scambi.py` usa queste regole nel perimetro
condizionato del [protocollo](protocollo_convenienza.md), con ricalibrazione distinta
per Redazione e Statistico. Le stime individuali originarie C restano conservate.
La tabella voti G1–G5 importata contiene soltanto il conteggio aggregato degli assist:
mancano le categorie Quality Assist. Occorre acquisire e verificare quel dettaglio
per fantamassa, fantaunipd e fantazavomerda, anche nello storico di calibrazione.
Lo scenario centrale assist +1 è un surrogato dichiarato, accompagnato da
sensibilità +0,5/+1,5: non rappresenta categorie Quality osservate.
Sono implementati formazioni, panchina, modificatori e confronto prima/dopo.
Il [README](README.md) descrive il report e i limiti residui. Restano distinte
convenienza sportiva stimata, validazione del ranking e legalità amministrativa.

## Discrepanze di dimensione rispetto al testo

- fantazavomerda / Lula FC: 27 osservati, 29 dichiarati.
- fantazavomerda / PIO AVE: 26 osservati, 29 dichiarati.
