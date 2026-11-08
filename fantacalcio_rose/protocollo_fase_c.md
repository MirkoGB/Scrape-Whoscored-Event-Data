# Fase C — protocollo del confronto al cutoff G5

Scritto il 6 ottobre 2026 prima di eseguire il nuovo confronto numerico.
Questo blocco riguarda la scala Redazione del provider, non i punti delle leghe.

- Universo storico: ID con almeno una riga FC (anche s.v.) nelle G1–G5
  effettivamente giocate prima della G6. Nessun listone di fine stagione,
  rosa corrente, QA, FVM, club o ruolo futuro entra nelle feature.
- Cutoff di ogni stagione: giorno precedente la prima gara G6. Si richiedono
  50 partite G1–G5 già disputate; altrimenti la stagione fallisce il controllo
  e occorre gestire esplicitamente i recuperi.
- Bersagli: numero di voti e somma FV fonte nelle G6–G10, G6–G13 e G6–G38;
  media voto e bonus fonte condizionati alle righe a voto. Mancanza di voto
  su un calendario verificato significa nessun contributo osservato del
  provider; non significa zero minuti, infortunio o assenza dalla distinta.
- Baseline storico: tasso a voto e medie dell'anno precedente, fallback
  per ruolo dalle stagioni precedenti per i nuovi arrivi. Baseline recente:
  frequenza e medie G1–G5, con prior storico quando mancano voti numerici.
- Combinazione: (esposizione recente × recente + k × storico) / (esposizione
  recente + k). Per le presenze l'esposizione è 5 giornate; per voto/bonus
  è il numero di voti. k separato per componente e orizzonte, scelto sulla
  griglia 0, 1, 3, 5, 10, 20, 50, 100, infinito minimizzando il MAE solo
  sulle transizioni già concluse; parità risolta verso più regolarizzazione.
- 2021/22 fornisce i prior; 2022/23 la prima calibrazione. Prove cronologiche
  su 2023/24, 2024/25, 2025/26, senza usare l'esito della stagione prevista.
  Ogni componente viene calibrata sul proprio bersaglio, non sui punti finali.
- Promozione della combinazione per orizzonte solo se il MAE punti è inferiore
  a entrambi i baseline nel totale e in ciascuna delle tre stagioni di prova.
  Se non passa, usare il baseline con MAE storico fuori campione minore,
  dichiarando che la scelta fra baseline usa quei risultati e non costituisce
  una nuova prova indipendente della politica selezionata.
- Intervalli empirici 80% da quantile conservativo dei residui assoluti fuori
  campione, per ruolo se almeno 30 residui, altrimenti globale. Verificarne la
  copertura su 2025/26 usando soltanto residui 2023/24–2024/25, per ogni modello.
  Non sono garanzie individuali né intervalli validati per infortuni recenti.
- La previsione assume continuità media del tasso futuro; non distingue la
  difficoltà delle singole partite. L'orizzonte lungo include possibili uscite
  dal campionato come nel bersaglio storico; non promette titolarità.
- Sensibilità: scenari a ±20% del tasso a voto (limitato a [0,1]), con
  rendimento condizionato fisso. Sono scenari, non probabilità o intervalli.
- Giocatori senza riga FC G1–G5: nessuna previsione operativa; mostrare solo
  copertura e motivo. Lo storico estero non viene convertito in voti italiani.
- Disponibilità medica, modificatori, punti schierabili e valore marginale
  rispetto al sostituto restano distinti e non calcolati senza regole complete.
  Costi d'asta ed esposizione tra leghe non entrano nel modello sportivo.

Il confronto dopo G5 è una domanda diversa dal modello pre-stagione della
Fase 9. Non riapre i predittori evento già esclusi né attribuisce validità
predittiva agli xG descrittivi della Fase B.
