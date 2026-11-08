# Dati necessari per completare C e D

Puoi fornire il regolamento completo o schermate delle impostazioni per ogni
lega. Per le regole comuni basta dichiarare a quali leghe si applicano.
Indica esplicitamente «non previsto» per una regola assente.

## C — Punti schierabili e valore nella rosa

Per ciascuna lega:

1. Conferma stagione 2026/27, formato Classic o Mantra e fonte dei voti
   (Redazione, Statistico, Italia o altra scala).
2. Moduli ammessi, numero di giocatori e vincoli dei ruoli in rosa. In Mantra:
   modalità di sostituzione, adattamenti e relativi malus.
3. Bonus/malus: gol (eventuali differenze per ruolo), assist, rigori segnati,
   sbagliati e parati, gol subiti, autoreti, ammonizioni, espulsioni,
   porta inviolata e ogni bonus particolare.
4. Modificatore difesa: chi entra nella media, portiere incluso o escluso,
   quanti difensori e quale selezione, minimo di difensori schierati,
   trattamento dei senza voto. Precisazione del 7 ottobre: sotto 6 il valore
   è zero nelle prime quattro leghe. Le altre fasce sono nella tabella seguente.
5. Capitano: formula completa e comportamento in caso di senza voto;
   conferma se attivo anche in fantaunipdgiantiamiamo e fantazavomerda.
6. Panchina: ordine e numero massimo di sostituzioni, cambio modulo,
   senza voto, riserve d'ufficio e voti politici/rinvii.

| Lega / tua squadra | Modificatore difesa già acquisito | Capitano |
|---|---|---|
| fantagas2020 / Swiftdon Town | 6–<6,5: +1; 6,5–<7: +3; ≥7: +6 | Attivo, manca formula |
| fantamassa21 / Daughter from Helgason | 6–<6,5: +1; 6,5–<7: +3; ≥7: +6 | Attivo, manca formula |
| fantaonlyfans / Il parco dei bambini | 6–<6,5: +1; 6,5–<7: +3; ≥7: +6 | Attivo, manca formula |
| fantaunipdgiantiamiamo / Expectations goals | Da 6, passi di 0,25: +1 / +1,5 / +2 / +2,5 / +3 / +4; da 7,5: +5 | Da confermare |
| fantazavomerda / Old-ham Fashioned Athletic | <5,5: −1,5; 5,5–<5,75: −1; 5,75–<6,25: 0; 6,25–<6,5: +1; 6,5–<6,75: +2; 6,75–<7: +3; ≥7: +3,5 | Da confermare |

## D — Legalità e convenienza degli scambi

Per ciascuna lega servono: formati ammessi (1×1, 2×2, eventuale 2×1),
finestre/scadenze, limiti numerici, eventuali approvazioni o veti, trasferimento
di crediti e costi dopo lo scambio. Per 2×1 specificare obblighi di reintegro,
svincoli e bacino degli svincolati. Crediti residui solo se incidono sulle
operazioni; altrimenti dichiarare che non si trasferiscono crediti.

Per consigli aggiornati servono inoltre export delle rose se cambiati e
informazioni datate su indisponibilità o vincoli personali (incedibili,
preferenze, orizzonte). Si possono acquisire fonti pubbliche in una fase
esplicita di aggiornamento: le assenze in G1–G5 non sono diagnosi mediche.

## Cosa resta da implementare

Ricevute le regole, resta lavoro tecnico: motore di formazioni legali,
sostituzioni, punteggi e modificatori; valore marginale rispetto alle
alternative nella rosa; poi ricalcolo prima/dopo per entrambe le squadre,
robustezza e graduatoria delle proposte. Compilare i campi non attiva da solo
questo motore. Le stime individuali e il catalogo strutturale già pronti sono
gli input, non una graduatoria di convenienza.

## Precisazioni ricevute il 7 ottobre 2026

Queste precisazioni integrano le risposte originali conservate sotto:

- Capitano, dove attivo: **modificatore aggiuntivo = voto base − 6**, anche
  negativo. Quindi 5,5 → −0,5; 6 → 0; 6,5 → +0,5; 7 → +1. Rimane escluso
  nelle leghe senza capitano e rimane la restrizione Pc/A di fantamassa.
- Sostituzioni esclusivamente nello stesso ruolo, anche in Mantra, senza
  adattamenti di ruolo. Nessun tetto numerico ai cambi, entro la disponibilità
  delle riserve e i limiti di panchina dichiarati. Resta da specificare la
  precedenza fra più riserve dello stesso ruolo.

- Bonus/malus successivamente comunicati: gol +3; rigori segnati +3 e sbagliati
  −3, tranne fantazavomerda (+2 e −2). Rigore parato +3; ammonizione −0,5;
  espulsione −1; autorete −2; gol subito −1; porta inviolata +1 in tutte le leghe.
- Assist +1 in fantagas2020 e fantaonlyfans. Quality Assist (+0,5 / +1 / +1,5)
  in fantamassa21, fantaunipdgiantiamiamo e fantazavomerda. Queste indicazioni
  completano i campi «Bonus e malus» lasciati vuoti nelle risposte originali.

- Correzione successiva: fantamassa ha un **massimo di 35 giocatori**. Questa
  indicazione sostituisce i 32 riportati nella risposta originale sotto;
  sono ammesse rose con meno di 35 giocatori rispetto a questo limite.

- Modificatore difesa zero sotto il 6 per fantagas2020, fantamassa21,
  fantaonlyfans e fantaunipdgiantiamiamo. Restano le fasce già indicate per fantazavomerda.
- La media usa i migliori quattro voti fra portiere e difensori schierati;
  il portiere può quindi essere escluso dai quattro. Resta il requisito del
  modulo con almeno quattro difensori già dichiarato.
- Se dopo le sostituzioni restano meno di quattro voti utili, il modificatore
  non si applica.
- Panchina fantagas2020 e fantaonlyfans: 1P–2D–2C–2A, sette posti complessivi.
- Panchina libera nelle altre tre leghe. Cambi illimitati entro la disponibilità
  della panchina; precedenza fra riserve dello stesso ruolo ancora da specificare.

La trascrizione strutturata è in `precisazioni_regole.json`; il riepilogo
aggiornato delle informazioni mancanti è in `verifica_regole.md`.

## Modello di risposta (ripetere per ciascuna lega)

```text
Lega: fantazavomerda
Stagione / formato / fonte voti: 2026-2027 / Classic / Statistico
Moduli / dimensione e vincoli rosa: I normali moduli del Classic / 29 Giocatori senza vincoli fra numero di ruoli eccetto che bisogna avere almeno 2 portieri per forza
Bonus e malus:
Media difesa / minimo difensori / senza voto / sotto 6: Si prende la media dei migliori 4 giocatori schierati portiere compreso, se si sceglie il modulo a 4 difensori o più / i senza voto non contano nella media e le fasce le ho spiegate precedentemente
Capitano e formula: Non c'è capitano
Panchina / sostituzioni / adattamenti / voti politici: Sostituzione normale dalla panchina del giocatore con lo stesso ruolo
Scambi ammessi / finestre / limiti / approvazioni: Tutti gli scambi ammessi nelle finestre delle soste nazionali
Crediti / costi dopo scambio / reintegri: Crediti di partenza 300 prima dell'asta
Data del regolamento e fonte: Inizio settembre
Rose cambiate rispetto agli export del 6 ottobre: nessun cambiamento
Vincoli o indisponibilità note (facoltativo, con data):
```

```text
Lega: fantagas2020
Stagione / formato / fonte voti: 2026-2027 / Classic / Redazione
Moduli / dimensione e vincoli rosa: I normali moduli del Classic / 25 Giocatori con vincolo 3P - 8D - 8C - 6A
Bonus e malus:
Media difesa / minimo difensori / senza voto / sotto 6: Si prende la media dei migliori 4 giocatori schierati portiere compreso, se si sceglie il modulo a 4 difensori o più / i senza voto non contano nella media e le fasce le ho spiegate precedentemente
Capitano e formula: C'è il capitano
Panchina / sostituzioni / adattamenti / voti politici: Sostituzione normale dalla panchina del giocatore con lo stesso ruolo
Scambi ammessi / finestre / limiti / approvazioni: Tutti gli scambi ammessi nelle finestre delle soste nazionali
Crediti / costi dopo scambio / reintegri: Crediti di partenza 1000 prima dell'asta
Data del regolamento e fonte: Inizio settembre
Rose cambiate rispetto agli export del 6 ottobre: nessun cambiamento
Vincoli o indisponibilità note (facoltativo, con data):
```

```text
Lega: fantaonlyfans
Stagione / formato / fonte voti: 2026-2027 / Classic / Redazione
Moduli / dimensione e vincoli rosa: I normali moduli del Classic / 25 Giocatori con vincolo 3P - 8D - 8C - 6A
Bonus e malus:
Media difesa / minimo difensori / senza voto / sotto 6: Si prende la media dei migliori 4 giocatori schierati portiere compreso, se si sceglie il modulo a 4 difensori o più / i senza voto non contano nella media e le fasce le ho spiegate precedentemente
Capitano e formula: C'è il capitano
Panchina / sostituzioni / adattamenti / voti politici: Sostituzione normale dalla panchina del giocatore con lo stesso ruolo
Scambi ammessi / finestre / limiti / approvazioni: Tutti gli scambi ammessi nelle finestre delle soste nazionali
Crediti / costi dopo scambio / reintegri: Crediti di partenza 1000 prima dell'asta
Data del regolamento e fonte: Inizio settembre
Rose cambiate rispetto agli export del 6 ottobre: nessun cambiamento
Vincoli o indisponibilità note (facoltativo, con data):
```


```text
Lega: fantaunipdgiantiamiamo
Stagione / formato / fonte voti: 2026-2027 / Classic / Redazione
Moduli / dimensione e vincoli rosa: I normali moduli del Classic / 25 Giocatori con vincolo 3P - 8D - 8C - 6A
Bonus e malus:
Media difesa / minimo difensori / senza voto / sotto 6: Si prende la media dei migliori 4 giocatori schierati portiere compreso, se si sceglie il modulo a 4 difensori o più / i senza voto non contano nella media e le fasce le ho spiegate precedentemente
Capitano e formula: Non c'è il capitano
Panchina / sostituzioni / adattamenti / voti politici: Sostituzione normale dalla panchina del giocatore con lo stesso ruolo
Scambi ammessi / finestre / limiti / approvazioni: Tutti gli scambi ammessi nelle finestre delle soste nazionali
Crediti / costi dopo scambio / reintegri: Crediti di partenza 500 prima dell'asta
Data del regolamento e fonte: Inizio settembre
Rose cambiate rispetto agli export del 6 ottobre: nessun cambiamento
Vincoli o indisponibilità note (facoltativo, con data):
```


```text
Lega: fantamassa
Stagione / formato / fonte voti: 2026-2027 / Mantra / Redazione
Moduli / dimensione e vincoli rosa: I normali moduli del Classic / 32 Giocatori senza vincoli di ruoli
Bonus e malus:
Media difesa / minimo difensori / senza voto / sotto 6: Si prende la media dei migliori 4 giocatori schierati portiere compreso, se si sceglie il modulo a 4 difensori o più / i senza voto non contano nella media e le fasce le ho spiegate precedentemente
Capitano e formula: C'è il capitano ma non si può mettere ai giocatori con Pc, A
Panchina / sostituzioni / adattamenti / voti politici: Sostituzione normale dalla panchina del giocatore con lo stesso ruolo
Scambi ammessi / finestre / limiti / approvazioni: Tutti gli scambi ammessi nelle finestre delle soste nazionali
Crediti / costi dopo scambio / reintegri: Crediti di partenza 650 prima dell'asta
Data del regolamento e fonte: Inizio settembre
Rose cambiate rispetto agli export del 6 ottobre: nessun cambiamento
Vincoli o indisponibilità note (facoltativo, con data):
```
