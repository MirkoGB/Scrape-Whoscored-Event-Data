# Fase 9 / Blocco E3 — la difesa

> Generato da `scripts/run_fase9_e3.py` il 2026-08-05.
> Nessuna richiesta di rete.

## In breve

| | esito |
|---|---|
| E3.1 modello di squadra sui gol | **funziona**: batte il baseline migliore per **t = 5.52** |
| E3.2 porta inviolata come probabilita' | **funziona**: pendenza **1.044 ± 0.083**, Brier 0.1899 contro 0.1992 |
| E3.3 voto della linea condizionato | **effetto reale e grande**: -0.243 di voto sui difensori |
| E3.3 sui **portieri** | **segno OPPOSTO**, e non era previsto |
| E3.4 correlazione dentro la linea | misurata: **0.261**, e il segno del suo effetto **si inverte** |
| **verifica sui portieri** | **FALLISCE**: la difesa di squadra non e' cio' che separa i portieri |
| E3.5 coda — la compensazione voto/malus | **ipotesi CONFUTATA**: sopravvive il **93%** del malus, non un terzo |
| E3.5 coda — collegare **entrambi** i lati | non recupera niente, **nemmeno con la pendenza oracolo** |
| E3.5 coda — la difesa di E3 come stimatore | **e' il migliore dei due**: MAE 0.322 contro 0.378 dello storico |

**Il blocco produce quattro strumenti che funzionano e una verifica finale che
li boccia**, ed e' il risultato piu' informativo possibile: la causa che il
blocco del modello d'asta dava per **identificata** — *i punti di un portiere
dipendono dalla difesa della sua squadra, e quel modello non guarda la squadra*
— **e' stata provata e non regge**.

## 0. Gli autogol, e il punteggio vero

`team_match.goals` **non e' il punteggio**: `shots.shots_mask` esclude gli autogol
dai tiri, quindi un autogol non compare da nessuna parte. Per i tiri in porta e'
giusto; per i **gol subiti** e' un errore, e per il fantacalcio doppiamente,
perche' il portiere il gol lo prende comunque.

L'attribuzione **e' verificata, non assunta**: l'evento `Goal` con `isOwnGoal`
porta il `teamId` della squadra che lo **subisce**.

| stagione | righe | gol_fatti_esatti | gol_subiti_esatti | senza_autogol_esatti | autogol | simmetria_ok |
|---|---:|---:|---:|---:|---:|---:|
| 2021-2022 | 748 | 748 | 748 | 712 | 36 | si |
| 2022-2023 | 750 | 750 | 750 | 719 | 31 | si |
| 2023-2024 | 760 | 760 | 760 | 736 | 24 | si |
| 2024-2025 | 760 | 760 | 760 | 723 | 37 | si |
| 2025-2026 | 760 | 760 | 760 | 738 | 22 | si |

**3778 righe su 3778, in entrambe le direzioni**, contro le
3628 che si otterrebbero ignorando gli autogol. La fonte del confronto e'
`matches.json`, che porta il punteggio **dichiarato** e non ricostruito dagli
eventi: e' cio' che rende questa una verifica e non una tautologia. La simmetria
interna (i gol fatti di un lato sono i gol subiti dell'altro) regge ovunque e non
usa la fonte esterna, quindi vale anche dove `matches.json` non arriva.

## 1. E3.1 — il modello di squadra sui gol, rivalidato per conto suo

Stessa specificazione della Fase 2 — `mu + attacco_i + difesa_j + gamma*casa`,
ridge, emivita 150 giorni, alpha scelto in walk-forward sul solo passato — e
**bersaglio diverso**. L'unica cosa che cambia e' `target`: se cambiasse anche la
specificazione non si saprebbe a cosa attribuire la differenza.

**La validazione non si eredita.** Che il modello sia calibrato sui tiri in porta
non dice niente sui gol: sono conteggi con media tre volte piu' bassa, il 28% di
zeri e una dispersione diversa. Ereditare la validazione della Fase 2 sarebbe
leggere male il vincolo 7. Il walk-forward e' **dentro la stagione** e le
previsioni si impilano dopo — le squadre cambiano fra stagioni, e un decadimento
di 150 giorni attraverso l'estate darebbe a settembre un training fatto di maggio.

**3278 righe valutate** su cinque stagioni.

| modello | n | mae | bias | corr | sharpness | calib_slope | calib_se | calib_z_vs_1 | brier | brier_base |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Poisson ridge att/dif/casa | 3278 | 0.872 | 0.015 | 0.299 | 0.398 | 0.898 | 0.052 | -1.98 | 0.2202 | 0.2349 |
| media squadra + campo | 3278 | 0.902 | 0.020 | 0.254 | 0.494 | 0.553 | 0.041 | -11.03 | 0.2266 | 0.2349 |
| media squadra | 3278 | 0.901 | 0.020 | 0.246 | 0.480 | 0.535 | 0.042 | -11.07 | 0.2271 | 0.2349 |
| media casa/trasferta | 3278 | 0.926 | 0.019 | 0.075 | 0.169 | 0.513 | 0.120 | -4.07 | 0.2352 | 0.2349 |
| media campionato | 3278 | 0.932 | 0.019 | 0.046 | 0.116 | 0.463 | 0.178 | -3.02 | 0.2352 | 0.2349 |

| baseline | mae_baseline | mae_modello | delta_mae | t | se |
|---|---:|---:|---:|---:|---:|
| media squadra + campo | 0.9022 | 0.8720 | 0.0302 | 5.52 | 0.0055 |
| media squadra | 0.9010 | 0.8720 | 0.0290 | 4.99 | 0.0058 |
| media casa/trasferta | 0.9265 | 0.8720 | 0.0545 | 9.56 | 0.0057 |
| media campionato | 0.9316 | 0.8720 | 0.0596 | 10.04 | 0.0059 |

**Qui il modello si giustifica anche sull'accuratezza, e sui tiri non era cosi'.**
Sul MAE batte il baseline migliore per **t = 5.52**; nella Fase 2, sullo
stesso confronto e con la stessa procedura, il margine valeva t = 1.86, cioe'
dentro il rumore. **Non e' un modello migliore: e' un bersaglio piu' facile da
distinguere.** I gol dipendono dall'avversario molto piu' dei tiri in porta, che
sono in gran parte "quanto tira questa squadra".

Sulla **calibrazione** si ritrova invece il fatto della Fase 4, piu' netto: i due
baseline informativi stanno a 0.553 e 0.535 con z sotto −11, cioe' danno
previsioni **troppo estreme** perche' una media campionaria non regredisce verso
il centro. Il modello sta a 0.898 ± 0.052 (z = -1.98), appena sotto 1.

**La forma dell'intera distribuzione**, che la pendenza non controlla: PIT
randomizzato chi2 = 5.67 su 9 gdl, **p = 0.773**. Gli zeri osservati sono il
27.7% contro il 28.9% atteso — ed e' il controllo che conta di piu' qui,
perche' la porta inviolata **e'** lo zero.

| livello | copertura | ampiezza_media |
|---:|---:|---:|
| 0.500 | 0.789 | 2.61 |
| 0.800 | 0.947 | 3.79 |
| 0.950 | 0.988 | 4.91 |

La copertura e' conservativa, com'e' strutturale sui conteggi (stesso esito della
Fase 4).

**I gol non sono sovradispersi**: var/media 1.03 e la `r` NB2 stimata sul solo
passato resta appiccicata al suo massimo. E' il motivo per cui in E3.2 la Poisson
e la NB2 danno lo stesso numero — **misurato, non assunto**.

## 2. E3.2 — la porta inviolata come probabilita'

`P(gol subiti = 0)` per squadra-partita, non frequenza storica. La differenza non
e' formale: la frequenza dice *"questo portiere ha fatto il 28% di clean sheet"*,
la probabilita' dice *"contro questo avversario, in casa, e' il 34%"* — e solo la
seconda si somma sul calendario vero.

| candidato | righe | p_media | osservato | brier | logloss | calib_slope | calib_se |
|---|---:|---:|---:|---:|---:|---:|---:|
| modello, Poisson | 3278 | 0.289 | 0.278 | 0.1899 | 0.5641 | 1.044 | 0.083 |
| modello, NB2 | 3278 | 0.289 | 0.278 | 0.1899 | 0.5641 | 1.044 | 0.083 |
| frequenza storica della squadra | 3278 | 0.267 | 0.278 | 0.1992 | 0.6055 | 0.372 | 0.062 |
| frequenza storica GREZZA (degenere) | 3178 | 0.273 | 0.279 | 0.2147 | 1.1893 |  |  |
| frequenza di campionato | 3278 | 0.257 | 0.278 | 0.2014 | 0.6092 |  |  |

**Il modello e' calibrato e i baseline no**, esattamente come sui gol: pendenza
1.044 ± 0.083 contro 0.372 della frequenza storica, che e' **troppo
estrema** di dieci errori standard.

**La frequenza storica grezza e' un estimatore degenere, e sta in tabella per
mostrarlo.** Una squadra che dopo sei giornate non ha ancora tenuto la porta
inviolata riceve `p = 0` esatto, cioe' «impossibile»: il log-loss ne esce a
1.189 contro 0.606 della versione smorzata, e la pendenza non e' nemmeno
identificabile. Il baseline usato nel confronto e' quindi quello **smorzato**
verso la media di campionato del solo passato, perche' il vincolo 6 chiede un
avversario serio: batterne uno degenere non dimostrerebbe niente.

## 3. E3.3 — il voto della linea, condizionato alla forza difensiva

E' l'ingresso del modificatore, che vale fino a +6. La domanda: **di quanto si
muove il voto base quando cambia la forza difensiva della squadra?**

| ruolo | condizione | righe | lam_subiti_medio | voto_medio | sd_voto |
|---|---|---:|---:|---:|---:|
| p | terzile atteso: forte | 1103 | 0.924 | 6.143 | 0.479 |
| p | terzile atteso: media | 1102 | 1.251 | 6.155 | 0.521 |
| p | terzile atteso: debole | 1102 | 1.764 | 6.219 | 0.578 |
| p | gol subiti (osservati): 0 | 917 | 1.171 | 6.351 | 0.408 |
| p | gol subiti (osservati): 1 | 1150 | 1.292 | 6.229 | 0.506 |
| p | gol subiti (osservati): 2 | 779 | 1.389 | 6.064 | 0.558 |
| p | gol subiti (osservati): 3+ | 461 | 1.518 | 5.859 | 0.567 |
| d | terzile atteso: forte | 5647 | 0.927 | 6.025 | 0.546 |
| d | terzile atteso: media | 5645 | 1.256 | 5.913 | 0.573 |
| d | terzile atteso: debole | 5643 | 1.776 | 5.797 | 0.608 |
| d | gol subiti (osservati): 0 | 4605 | 1.174 | 6.261 | 0.428 |
| d | gol subiti (osservati): 1 | 5872 | 1.295 | 5.987 | 0.503 |
| d | gol subiti (osservati): 2 | 4015 | 1.393 | 5.726 | 0.531 |
| d | gol subiti (osservati): 3+ | 2443 | 1.531 | 5.377 | 0.601 |

| ruolo | regressore | righe | pendenza | se | t | delta_p10_p90 |
|---|---|---:|---:|---:|---:|---:|
| p | lam_subiti (previsto) | 3307 | 0.0795 | 0.0231 | 3.44 | 0.078 |
| p | gol_subiti (osservato) | 3307 | -0.1413 | 0.0076 | -18.70 | -0.424 |
| d | lam_subiti (previsto) | 16935 | -0.2481 | 0.0110 | -22.52 | -0.243 |
| d | gol_subiti (osservato) | 16935 | -0.2571 | 0.0033 | -78.26 | -0.771 |

**Sui difensori l'effetto e' reale e grande**: dal decimo al novantesimo
percentile della forza difensiva attesa il voto base si muove di
0.243,
con t = -22.5. Con le fasce a 6,00 / 6,50 / 7,00 un quarto di punto di voto
medio di linea e' esattamente cio' che sposta una fascia.

> **Sui portieri il segno e' OPPOSTO, ed e' significativo.** Un portiere di una
> difesa attesa **debole** prende un voto base piu' **alto**
> (pendenza +0.0795, t = 3.44), mentre a **gol subiti osservati** il suo voto
> scende (-0.1413, t = -18.7). Non e' una contraddizione: il portiere e'
> **giudicato rispetto all'attesa**. Chi para molto perche' la sua difesa lo
> espone viene premiato per le parate; chi prende gol viene punito per i gol.
> **Non era previsto e non e' stato aggiustato.**

Le due colonne `lam_subiti (previsto)` e `gol_subiti (osservato)` stanno insieme
apposta: **solo la prima e' disponibile quando serve.** La seconda dice quanto
piu' grande sarebbe l'effetto conoscendo il risultato, cioe' il tetto di cio' che
un modello di squadra migliore potrebbe recuperare — sui difensori 0.771 contro
0.243, cioe' circa il triplo.

## 4. E3.4 — la correlazione dentro la linea

`modificatore.simula_linea` estraeva i membri della linea in modo indipendente e
lo dichiarava come limite. Finche' resta dichiarato e non stimato, e' un'ipotesi.

| insieme | voto | righe | gruppi | dimensione_media | icc | sd_entro |
|---|---|---:|---:|---:|---:|---:|
| linea intera (p+d) | grezzo | 20242 | 3276 | 6.18 | 0.263 | 0.500 |
| linea intera (p+d) | al netto del giocatore | 20242 | 3276 | 6.18 | 0.261 | 0.465 |
| solo d | grezzo | 16935 | 3276 | 5.17 | 0.337 | 0.475 |
| solo d | al netto del giocatore | 16935 | 3276 | 5.17 | 0.315 | 0.453 |

**La correlazione c'e' e non e' piccola: 0.261** sulla linea intera. Ed e'
**genuina co-variazione di giornata, non composizione della rosa**: togliendo la
media di ogni giocatore passa da 0.263 a 0.261, cioe' **non si muove**. Se
fosse "le difese forti hanno difensori bravi" sarebbe crollata, perche' quella
parte e' gia' dentro `mu` nella simulazione e verrebbe contata due volte. E'
quindi la riga giusta da iniettare nel simulatore.

`simula_linea` ha ora un parametro `rho`, **0 di default**: un test verifica che
con `rho=0` l'uscita sia identica bit per bit a prima che il parametro esistesse.
La correlazione entra con un fattore comune, che e' la struttura giusta per un
gruppo **senza ordine** — non c'e' un "primo" e un "secondo" difensore.

| voto_medio_linea | bonus_indipendenti | bonus_correlati | delta_per_giornata | delta_stagione |
|---:|---:|---:|---:|---:|
| 5.50 | -0.8816 | -0.7486 | 0.1331 | 5.06 |
| 5.75 | -0.4945 | -0.3250 | 0.1695 | 6.44 |
| 5.90 | -0.0594 | 0.0702 | 0.1296 | 4.92 |
| 6.00 | 0.2906 | 0.3875 | 0.0969 | 3.68 |
| 6.10 | 0.6630 | 0.7315 | 0.0686 | 2.61 |
| 6.25 | 1.2535 | 1.3007 | 0.0472 | 1.79 |
| 6.40 | 1.8702 | 1.9195 | 0.0493 | 1.87 |
| 6.50 | 2.3000 | 2.3573 | 0.0572 | 2.17 |
| 6.60 | 2.7452 | 2.7982 | 0.0530 | 2.02 |
| 6.75 | 3.4666 | 3.4762 | 0.0096 | 0.37 |
| 6.90 | 4.2260 | 4.1464 | -0.0797 | -3.03 |
| 7.00 | 4.7115 | 4.5605 | -0.1510 | -5.74 |
| 7.10 | 5.1364 | 4.9243 | -0.2122 | -8.06 |
| 7.30 | 5.7092 | 5.4782 | -0.2310 | -8.78 |
| 7.60 | 5.9710 | 5.8870 | -0.0840 | -3.19 |

> **Il segno si inverte, e questo era il punto.** Sotto i 6,60 di voto medio di
> linea la correlazione **aumenta** il bonus atteso, fino a +6 punti di stagione;
> sopra i 6,90 lo **riduce**, fino a −8,8. Il meccanismo e' la forma della scala:
> le fasce sono convesse crescenti (−1 / +1 / +3 / +6), quindi piu' varianza aiuta
> — **finche' non si e' dentro l'ultima**, che non ha nulla sopra di se', e da li'
> la varianza puo' solo far uscire. Il punto di inversione sta intorno a 6,7.

Ne segue che la simulazione indipendente **non era conservativa**: sbagliava in
un verso o nell'altro a seconda della linea, come gia' `costo_della_media` aveva
trovato per la scorciatoia sulle medie di stagione. `sd` e `p_voto` sono tenuti
fissi e dichiarati: qui si isola la **correlazione**, non si ricalibra il
modificatore.

## 5. La verifica che chiude il blocco — i portieri

Riportata **separata** per ruolo e mai annegata nella metrica complessiva: i
portieri sono ~12% del listone.

**Prima una precisazione sui numeri di riferimento.** Il blocco del modello
d'asta pubblica *"sui portieri il modello fa 0 e il FVM 0,667"*, e quella e' la
**precisione sui primi N**, non lo Spearman: lo Spearman sui portieri non era mai
stato pubblicato, e vale 0.465. Le due cose vanno tenute distinte, e qui
ci sono entrambe.

| candidato | stagioni | spearman | min | max | precisione_top |
|---|---:|---:|---:|---:|---:|
| modello d'asta | 4 | 0.465 | 0.355 | 0.555 | 0.000 |
| modello d'asta + difesa E3 (ultima stagione) | 4 | 0.435 | 0.341 | 0.544 | 0.000 |
| modello d'asta + difesa E3 (tutte le stagioni) | 4 | 0.421 | 0.341 | 0.517 | 0.000 |
| FVM della fonte (CONTAMINATO) | 4 | 0.818 | 0.763 | 0.865 | 0.667 |
| quotazione iniziale QI | 4 | 0.730 | 0.589 | 0.797 | 0.083 |
| persistenza (anno prima) | 4 | 0.446 | 0.361 | 0.514 | 0.167 |

**La sostituzione peggiora.** Rimpiazzare la componente difensiva del bonus del
portiere — gol subiti e porta inviolata, le due voci che dipendono dalla squadra —
con quella derivata dal modello di squadra porta lo Spearman da
0.465 a 0.435, e la precisione resta **0**. Voto base e presenze attese
non sono stati toccati, quindi la differenza e' attribuibile alla sola
sostituzione. **Vale con entrambe le forme della forza difensiva** (ultima
stagione e tutte), quindi non dipende da quella scelta.

### Perche', e qui il blocco consegna la cosa piu' utile che ha

| soglia_presenze_attese | portieri | quota_mai_in_campo | spearman_modello | spearman_con_difesa_e3 | spearman_sole_presenze_attese | spearman_qi | spearman_fvm_CONTAMINATO |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 0 | 258 | 0.399 | 0.536 | 0.507 | 0.534 | 0.740 | 0.831 |
| 10 | 195 | 0.364 | 0.592 | 0.528 | 0.586 | 0.779 | 0.865 |
| 15 | 177 | 0.367 | 0.720 | 0.623 | 0.714 | 0.798 | 0.869 |
| 20 | 63 | 0.016 | 0.073 | -0.027 | -0.011 | 0.273 | 0.700 |
| 25 | 48 | 0.021 | -0.010 | -0.168 | -0.153 | 0.300 | 0.745 |

Quattro letture, in ordine:

1. **La premessa del blocco era falsa per la popolazione che conta.**
   L'argomento era: *un portiere titolare gioca quasi tutto, quindi le presenze
   sono quasi risolte e l'errore sta altrove.* Vero per il titolare, falso per i
   **quotati**: il 40% dei portieri a listino non gioca **nemmeno una
   partita**. Fra tutti i quotati, ordinare per **sole presenze attese** da'
   0.534 contro 0.536 del modello intero: il modello sui portieri
   **e' gia' quasi solo un modello di presenze**.
2. **Fra i probabili titolari non funziona piu' niente.** Alzando la soglia a 20
   presenze attese restano 63 portieri, di cui solo il 2% non gioca: le
   presenze sono davvero risolte li'. E il modello crolla a
   0.073, le sole presenze a -0.011, la difesa di E3 a
   -0.027. **Tolte le presenze, nessuno dei nostri candidati sa niente.**
3. **La quotazione non crolla come il resto, e QI e' quella che conta.** Fra i
   probabili titolari **QI** fa 0.273 — contro 0.073 del modello e
   -0.011 delle sole presenze. E' l'unica cosa sopra lo zero li' dentro,
   ed e' informazione **disponibile prima dell'asta**. Il vantaggio della
   quotazione sui portieri **non e' sapere chi gioca**: sopravvive proprio dove le
   presenze sono risolte.
4. **Ma il numero che questo report citava era un altro, e non era leale.**

> ### CORREZIONE — il 0.700 del FVM era contaminato
>
> Questa sezione affermava *«ma il FVM non crolla: 0.700, ed e' il numero
> decisivo del blocco»*, e ne ricavava che il FVM sapesse qualcosa di ignoto sui
> portieri. **Il FVM della pagina archiviata si muove durante la stagione**
> (`quotazioni.orologio()`, §3-bis del report del modello d'asta), quindi per una
> stagione passata ne conosce l'esito. Il numero resta in tabella, marcato
> `CONTAMINATO`: e' un errore di questo progetto e non si cancella.
>
> **Rifatto con QI, che e' pulito, il vantaggio regge ma si riduce di molto**:
> 0.273 invece di 0.700. Ed e' la risposta alla domanda aperta n. 1: **non
> era solo "sapeva come era andata la stagione"** — una quotazione che non puo'
> saperlo sta comunque a 0.273 dove tutto il nostro sta a zero — **ma la
> maggior parte di quel 0.700 era esattamente quello**. La domanda sopravvive
> piu' piccola e meglio posta.
>
> Sulla **precisione sui primi N** il divario invece **non e' misurabile**: il
> modello fa 0 e QI fa 0,000 o 0,083 **a seconda di come si sciolgono i pari
> merito** — QI e' un prezzo intero e in **due stagioni su quattro** ci sono pari
> merito al confine dei primi tre (2024-25 ha 15 e 15 al terzo e quarto posto,
> 2025-26 ha quattro 16 per tre posti), quindi quali tre entrano lo decide il
> sorteggio. Con 3 posti per 4 stagioni la metrica ha passi da 1/12, e le due
> implementazioni del repository danno i due valori per quella ragione. **E' la
> risoluzione della metrica, non un risultato**, e su quel piano il divario col
> FVM contaminato
> (0,667) resta l'unica cosa grande — cioe' l'unica cosa che la contaminazione
> spiegava.

> **La causa data per identificata non regge.** Il blocco del modello d'asta
> scriveva che i punti di un portiere dipendono dalla difesa della sua squadra e
> che il modello non la guarda. La prima meta' e' vera — E3.2 e E3.3 la misurano —
> ma **la seconda non e' la spiegazione dello Spearman**: dare al modello la
> difesa della squadra, con un modello di squadra validato per conto suo, non
> migliora l'ordinamento dei portieri. **Cio' che la quotazione sa sui portieri
> resta ignoto, ed e' ora una domanda molto piu' stretta di prima** — vale
> 0.273, non 0.700.

## 5-bis. E3.5 — la coda: perche' la difesa peggiora, e l'ipotesi che non regge

E3.3 aveva lasciato un segno opposto sui portieri, e da li' nasceva una
spiegazione dell'esito negativo: **dietro una difesa debole il portiere para di
piu' e il voto sale, il malus dei gol subiti scende, le due voci si compensano e
il netto e' quasi piatto** — quindi collegare la difesa a un solo lato dei due
peggiora, perche' aggiunge meta' compensazione senza l'altra meta'.

E' un'ipotesi con tre conseguenze, e si misurano separate perche' possono cadere
una per volta. La soglia della seconda **e' dichiarata prima di guardare**: la
compensazione si chiama completa se nel netto sopravvive meno di **un terzo** del
malus.

### Le due componenti, e quale fonte alimenta il malus

`comp_voto` e' il voto base (la componente di E3.3); `comp_bonus` e'
`-1 x gol subiti + 1 x porta inviolata` in punti di lega, cioe' le due voci di
`lega.BONUS` che dipendono dalla squadra. **Per il difensore `comp_bonus` e' zero
per regolamento**, non per approssimazione: un difensore non prende malus sui gol
subiti. E' gia' meta' della risposta — il difensore ha **un canale**, il portiere
**due**, e i due hanno segno opposto.

**Il malus lo alimenta la fonte dei VOTI** (`difesa.FONTE_MALUS`), non i gol
ricomposti da WhoScored: e' la fonte definitoria, quella che ha prodotto i
`punti_osservati`. Non e' una formalita', perche' `voti_difensori` **sovrascrive**
`gol_subiti` con i gol di squadra (autogol compresi) e le due colonne, che hanno
lo stesso nome, differiscono su **32 righe su 3307**, sempre nel verso di
WhoScored che ne conta di piu'.

| ruolo | componente | righe | pendenza | se | t | delta_p10_p90 |
|---|---|---:|---:|---:|---:|---:|
| p | comp_voto | 3307 | 0.0795 | 0.0231 | 3.44 | 0.0775 |
| p | comp_bonus | 3307 | -1.1153 | 0.0631 | -17.67 | -1.0876 |
| p | comp_netto | 3307 | -1.0357 | 0.0739 | -14.01 | -1.0100 |
| d | comp_voto | 16935 | -0.2481 | 0.0110 | -22.52 | -0.2431 |
| d | comp_bonus | 16935 | 0.0000 |  |  | 0.0000 |
| d | comp_netto | 16935 | -0.2481 | 0.0110 | -22.52 | -0.2431 |

**La conseguenza 1 regge**, ed e' il controllo che le componenti stiano sulla
stessa popolazione di E3.3: la pendenza del voto sul portiere e'
+0.0795 con t = +3.44, cioe' il numero di E3.3 riprodotto.

**La conseguenza 2 cade, e non di poco.** Il malus si muove di
-1.1153 per unita' di gol attesi, il voto base lo compensa di
+0.0795, e nel netto sopravvive **92.9%** del malus — contro la
soglia del 33% dichiarata. Il netto ha pendenza -1.0357 con
**t = -14.0**: non e' piatto, e' quasi tutto il malus. Dal decimo al
novantesimo percentile della forza difensiva attesa un portiere perde
1.01 punti **per partita**, che su una stagione da titolare sono
una trentina di punti. **La compensazione esiste e vale il 7% del malus, non i due
terzi che servivano.**

### La conseguenza 3, e la trappola dei totali

| pavimento_presenze | portieri | corr_medie | corr_totali | sd_voto | sd_bonus | sd_netto | compressione_vs_indipendenza |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 222 | 0.357 | -0.773 | 0.363 | 0.917 | 1.101 | -0.116 |
| 5 | 148 | 0.186 | -0.592 | 0.150 | 0.558 | 0.604 | -0.046 |
| 10 | 117 | -0.003 | -0.380 | 0.128 | 0.475 | 0.492 | 0.001 |
| 19 | 90 | -0.012 | -0.223 | 0.114 | 0.452 | 0.465 | 0.003 |

**Attraverso i portieri le due componenti non sono correlate negativamente: non
sono correlate affatto.** Sulle medie per presenza si passa da
+0.357 con un pavimento di una presenza a -0.003 e -0.012 sopra le dieci e le
diciannove, cioe' zero appena si pretende che la media di bonus sia un tasso e non
un conteggio di gol.

> **La colonna `corr_totali` e' li' per essere squalificata, non per essere
> letta.** Sui totali di stagione la correlazione e' fortemente negativa
> (-0.380 a dieci presenze) e sembrerebbe la conferma cercata. Non lo e':
> il totale del voto **cresce** col numero di presenze e quello del bonus **cala**
> (ogni presenza in piu' porta altri gol subiti), quindi i totali si correlano
> negativamente **attraverso le presenze** anche se le due componenti fossero
> indipendenti. E' la stessa forma di errore che il progetto ha gia' incontrato su
> `possession` e `field_tilt` in E0, dove una media di 0.500 esatta era una
> proprieta' della definizione e non un risultato.

### La conseguenza operativa, misurata comunque

Se la compensazione fosse il meccanismo, collegare **entrambe** le componenti
dovrebbe recuperare cio' che collegarne una sola perde. E3 aveva collegato solo il
bonus, lasciando `voto_atteso` indipendente dalla squadra.

| candidato | 0 | 15 | 20 |
|---|---:|---:|---:|
| FVM della fonte (CONTAMINATO) | 0.831 | 0.869 | 0.700 |
| entrambi i lati | 0.508 | 0.624 | -0.019 |
| entrambi i lati (pendenza ORACOLO) | 0.507 | 0.624 | -0.016 |
| modello d'asta (nessun lato) | 0.536 | 0.720 | 0.073 |
| solo bonus — e' E3 | 0.507 | 0.623 | -0.027 |
| solo voto | 0.529 | 0.661 | 0.064 |

**Non recupera niente.** A soglia zero collegare entrambi i lati da'
0.508 contro 0.507 di E3 e 0.536 del modello che non
collega nulla; fra i probabili titolari -0.019 contro 0.073. La riga
**pendenza ORACOLO** — la pendenza stimata su tutte e cinque le stagioni, bersaglio
compreso, che come ingrediente di una previsione e' un imbroglio dichiarato — fa
0.507: **nemmeno conoscendo la risposta il lato del voto recupera**, ed e' il
modo di escludere che la questione sia la qualita' della stima della pendenza.

### E allora dove sta il problema — una cosa esclusa, il resto aperto

La spiegazione piu' semplice sarebbe che la componente difensiva di E3 stimi
peggio di cio' che ha sostituito. **Si misura, e non e' cosi'.**

| stimatore | portieri_qualita | mae | corr | portieri_tutti | corr_con_presenze |
|---|---:|---:|---:|---:|---:|
| bonus storico del portiere (il modello d'asta) | 85 | 0.3780 | 0.346 | 258 | 0.104 |
| difesa E3 (modello di squadra) | 85 | 0.3220 | 0.500 | 258 | 0.035 |

Contro il bonus difensivo per presenza **effettivamente realizzato** nella
stagione bersaglio, la difesa di E3 fa MAE 0.3220 e correlazione +0.500;
il bonus storico del portiere, che e' cio' che il modello d'asta usa, fa
0.3780 e +0.346. **La componente di E3 e' lo stimatore migliore della
cosa che stima, e sostituirla peggiora l'ordinamento lo stesso.**

> Le due meta' della tabella hanno **due denominatori diversi**, ed e' voluto: la
> qualita' della stima si puo' misurare solo sui 85 portieri che hanno giocato
> abbastanza da avere un tasso invece di un conteggio, mentre la correlazione con
> le presenze va misurata su **tutti** i 258, che sono la popolazione su cui la
> Spearman e' calcolata. Restringerla ai titolari troncherebbe proprio la
> variabile di cui si chiede la correlazione — ed e' l'errore che questa sezione
> aveva commesso in prima stesura, con il segno che ne usciva rovesciato.

L'unico canale per cui questo e' possibile e' che lo stimatore peggiore porti con
se' informazione su **quante partite** il portiere giochera', che e' cio' che
domina l'ordinamento dei punti di stagione. La colonna `corr_con_presenze` lo
misura, ed e' nel verso giusto ma piccola: +0.104 per il bonus storico contro
+0.035 per quello di E3. **Non basta a spiegare niente**, e va detto invece
di arrotondarlo verso l'alto: e' un indizio coerente col meccanismo, non una causa
dimostrata.

> **L'ipotesi era sbagliata, e la domanda resta aperta.** Il voto base del portiere
> si muove davvero nel verso opposto a quello dei difensori — quella meta' di E3.3
> regge — ma **non compensa il malus**: ne annulla il 7%, il netto resta
> ripido, e attraverso i portieri le due componenti sono scorrelate invece che
> compensarsi. Collegare entrambi i lati non recupera niente, nemmeno con la
> pendenza oracolo. **Cio' che questa coda aggiunge e' un'esclusione**: non e' che
> la difesa sia stimata male, perche' e' stimata meglio di cio' che ha sostituito.
> Perche' collegarla peggiori l'ordinamento resta senza spiegazione misurata.

## Cosa questo blocco lascia, e cosa no

**Quattro strumenti validati, che non dipendono dall'esito della verifica:**

* un modello di squadra sui **gol**, che batte i baseline con t = 5.5 ed e'
  calibrato in distribuzione (PIT p = 0.77);
* la **porta inviolata come probabilita' per partita**, ben calibrata, che si
  somma sul calendario vero — cosa che una frequenza non fa;
* la **pendenza del voto** dei difensori sulla forza difensiva, che e' l'ingresso
  quantificato del modificatore;
* la **correlazione dentro la linea**, misurata e messa nel simulatore, col segno
  del suo effetto che si inverte a 6,7.

**Cosa NON e' stato fatto, di proposito**: non e' stato cercato un modo di far
sembrare positiva la verifica sui portieri. Il segno e' spiegato da un meccanismo
misurato — le presenze dominano l'ordinamento, e dove non dominano non c'e'
segnale nei nostri candidati — e ritoccare la sostituzione finche' lo Spearman
supera 0.465 cancellerebbe la spiegazione invece di trovarne una.

## 6. Due cose portate dentro dal blocco precedente

**L'xG non entra nel modello dei gol, quindi il problema dei cinque fit non si
pone.** Era la condizione posta: `xg_per_90` ha cinque fit che sono **cinque
modelli, non cinque livelli**, e un effetto di stagione lo copre solo se la
differenza e' un'intercetta — cosa non verificata. La specificazione di E3.1 e'
`mu + attacco_i + difesa_j + gamma*casa` e **non contiene xG in nessuna forma**:
la parola non compare in `sot/difesa.py`. Non e' una svista da colmare — e' la
stessa specificazione della Fase 2, e cambiarla insieme al bersaglio avrebbe reso
impossibile attribuire la differenza. Se un blocco futuro volesse metterci l'xG,
**la verifica sull'intercetta va fatta prima**, e resta da fare.

**Il malus dei cartellini e' alimentato dalla fonte dei VOTI, ed e' definitorio.**
`fantapunti.con_fantavoto_lega` calcola il malus dalle colonne `ammonizione` ed
`espulsione` della tabella dei voti: e' quella fonte che ha prodotto i
`punti_osservati` contro cui tutto il progetto si misura. **WhoScored non tocca i
punti in nessun punto della catena.** Ne segue che le 42 ammonizioni di scarto del
2023-24 non sono una scelta da fare fra due candidate — la fonte dei punti e' una
sola — ma **un difetto di WhoScored da spiegare**, e resta una domanda aperta di
E2 e non di E3. La stessa dichiarazione vale per la coda di E2
(`impiego.FONTE_CARTELLINI`), che usa i voti per la stessa ragione.

## Domande aperte

1. **Che cosa sa la QUOTAZIONE sui portieri.** Era formulata sul FVM e vale
   0.273, non 0.700: la differenza fra i due era contaminazione. Resta la
   domanda piu' stretta che il progetto abbia — sopravvive al condizionamento
   sulle presenze e non e' la forza difensiva della squadra — ma su una metrica
   sola: sulla **precisione sui primi N** QI e il modello stanno entrambi a un
   pescaggio dallo zero, dentro la risoluzione della metrica. Restano gerarchia
   dichiarata dai club, mercato in corso e valutazione individuale del portiere:
   nessuna delle tre e' nel repository.
5. **Un valore pre-stagione dalla fonte, per il FVM e per il numero di maglia
   insieme.** Sono la **stessa domanda aperta**, non due: un valore d'agosto che i
   club e i listoni pubblicano e che il repository non ha. Il FVM pulito
   renderebbe leale un concorrente oggi squalificato; il numero di maglia d'agosto
   proverebbe l'argomento per cui quella feature di E2 esisteva. Vanno tenute
   appaiate — se un giorno si risponde a una si risponde all'altra.
2. **Il voto del portiere e' relativo all'attesa**, e questo blocco lo misura ma
   non lo modella. Un modello del voto base che tenesse conto dei **tiri
   affrontati** e non solo dei gol subiti e' la forma naturale, e i tiri in porta
   concessi ci sono gia' (`sot_conceded`).
3. **Il modificatore con `rho` acceso non e' stato ricalcolato** sulla lista
   d'asta: il parametro c'e' e la misura c'e', ma `run_asta_2627.py` continua a
   girare a `rho = 0`. Accenderlo cambia i contributi marginali in modo che
   dipende dalla linea, e va fatto come blocco a se'.
4. **La forza difensiva delle neopromosse** resta senza stima: la Serie B non e'
   nel repository, e la Fase 6E ha gia' misurato che assumerle "come le
   retrocesse" non e' neutro.
