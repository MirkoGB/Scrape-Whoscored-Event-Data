# Fase 4 — validazione consolidata

Righe valutate: **660** su 760 (burn-in: dalla 6a partita di ciascuna squadra). Modello e baseline sono valutati sulle **stesse** righe: qualunque confronto su sottoinsiemi diversi sarebbe privo di significato.

Nessun modello nuovo: si validano quelli delle Fasi 2 e 3.

## Esito in breve

1. **Il modello e' calibrato, i baseline informativi no.** Pendenza 0.965 +- 0.083 (z = -0.42, compatibile con 1.0); `media squadra` sta a 0.747 (z = -3.15) e `media squadra + campo` a 0.785 (z = -2.86). Questa e' la giustificazione empirica piu' netta del modello, piu' netta del suo vantaggio sul MAE.
2. **Il vantaggio sul MAE resta invece dentro il rumore**: t = 1.95 contro il baseline migliore. La Fase 2 lo diceva gia'; qui e' confermato su quattro soglie, tre segmentazioni e con i parametri di probabilita' anch'essi walk-forward.
3. **La forma della predittiva regge**, non solo la media: PIT randomizzato chi2 = 6.03 su 9 gradi di liberta' (p = 0.737). E' un controllo che le Fasi 2 e 3 non facevano.
4. **La scorciatoia della Fase 2 su `r` non cambiava le conclusioni**, ma lo si sa solo adesso: il Brier si sposta di +0.0002.
5. **Il metodo dal basso della Fase 3 non batte il piu' banale baseline di squadra**, e il segno resta contrario. Nessuna correzione e' stata applicata. Vale pero' per l'estimatore che fissa il livello dai giocatori: quello **compositivo**, che e' l'estimatore pubblicato, e' un'altra cosa e questo test non ha la potenza per giudicarlo (Fase 6B).

## 1. I parametri di probabilita' vengono anch'essi dal passato

Convertire lambda in una probabilita' richiede due parametri che non fanno parte della previsione puntuale: la dispersione `r` della NB2 e il tasso base contro cui si misura il Brier. In Fase 2 erano stimati sull'intero campione valutato. Qui sono ricostruiti riga per riga sul solo passato (minimo 60 righe precedenti, prima delle quali si resta sulla Poisson).

- r del modello: mediana walk-forward **23.9**, valore a fine stagione 28.2, sull'intero campione 26.0
- r per baseline (intero campione): media campionato 10.5, media casa/trasferta 11.8, media squadra 16.3, media squadra + campo 20.0
- tasso base Over 4.5: walk-forward medio **0.3755**, osservato 0.3879

La riga dei baseline va letta: **r scende quanto piu' il modello e' povero** — 10.5 per la media di campionato contro 26.0 per il modello. Non e' che i dati siano piu' dispersi per un modello che per l'altro: e' la variazione di lambda che il baseline non spiega, e che finisce nella dispersione perche' non ha altro posto dove andare. La media di campionato arriva a sfiorare la soglia di sospetto di 10 dichiarata in `dispersion.py`; qui pero' non e' il sintomo di un errore, e' il baseline che fa il suo mestiere di essere stupido.

Confronto diretto con i valori dichiarati in Fase 2:

|             |   riferimento |   Fase 2 (r intero campione) |   Fase 4 (r walk-forward) |
|:------------|--------------:|-----------------------------:|--------------------------:|
| mae         |         1.69  |                       1.7395 |                    1.7395 |
| bias        |         0.01  |                       0.0341 |                    0.0341 |
| corr        |         0.41  |                       0.3944 |                    0.3944 |
| calib_slope |         1.05  |                       0.9652 |                    0.9652 |
| brier       |         0.211 |                       0.2127 |                    0.2129 |
| brier_base  |         0.238 |                       0.2374 |                    0.239  |

La differenza fra le due colonne e' l'effetto della scorciatoia. MAE, bias, correlazione e pendenza non cambiano per costruzione — non dipendono da `r`. Cambia il Brier, di +0.0002, e il suo tasso base, di +0.0016. Sono spostamenti di quarta cifra: la scorciatoia della Fase 2 non cambiava le conclusioni. Questo si sa **adesso** che e' stato misurato; non era una cosa da assumere. I numeri da citare sono quelli dell'ultima colonna.

## 2. Metriche, modello e baseline affiancati

`sharpness` e' la deviazione standard dei lambda previsti. Va letta insieme alla calibrazione: prevedere la media a tutti da' calibrazione perfetta e sharpness zero. `ece` e' l'errore di calibrazione atteso sull'Over 4.5.

| modello                    |   n |    mae |   rmse |   bias |    corr |   sharpness |   loglik_nb2 |   brier |   brier_base |    ece |
|:---------------------------|----:|-------:|-------:|-------:|--------:|------------:|-------------:|--------:|-------------:|-------:|
| Poisson ridge att/dif/casa | 660 | 1.7395 | 2.1525 | 0.0341 |  0.3944 |      0.959  |     -1416.84 |  0.2129 |        0.239 | 0.0249 |
| media campionato           | 660 | 1.8771 | 2.3446 | 0.0361 | -0.0393 |      0.05   |     -1472.31 |  0.238  |        0.239 | 0.0142 |
| media casa/trasferta       | 660 | 1.8802 | 2.3114 | 0.0361 |  0.1618 |      0.4005 |     -1462.48 |  0.2352 |        0.239 | 0.0096 |
| media squadra              | 660 | 1.8116 | 2.2325 | 0.0352 |  0.3187 |      0.9825 |     -1441.29 |  0.2225 |        0.239 | 0.0502 |
| media squadra + campo      | 660 | 1.7851 | 2.1924 | 0.0352 |  0.3621 |      1.049  |     -1430.31 |  0.2193 |        0.239 | 0.0563 |

Confronti appaiati contro **Poisson ridge att/dif/casa** (`d_loglik` > 0 e `d_mae` > 0 = il modello vince):

| vs                    |   d_loglik |   t_loglik |   d_mae |   t_mae |
|:----------------------|-----------:|-----------:|--------:|--------:|
| media campionato      |    55.4665 |     5.2417 |  0.1377 |  4.0835 |
| media casa/trasferta  |    45.6425 |     4.6247 |  0.1407 |  4.6577 |
| media squadra         |    24.4514 |     2.8475 |  0.0721 |  2.6294 |
| media squadra + campo |    13.47   |     1.8202 |  0.0456 |  1.9545 |

Il margine sul baseline migliore resta sotto le due deviazioni standard. Quasi tutta la prevedibilita' dei tiri in porta e' "questa squadra tira tanto, e gioca in casa"; il modello aggiunge poco, e quel poco non e' distinguibile dal rumore su una stagione sola.

## 3. Pendenza di calibrazione contro 1.0

Poisson di `y` su `log(lambda)`; errore standard dall'informazione di Fisher. b < 1 = previsioni troppo estreme, b > 1 = troppo compresse.

| modello                    |   calib_slope |   calib_se |   calib_z_vs_1 |   p_value | compatibile con 1.0   |
|:---------------------------|--------------:|-----------:|---------------:|----------:|:----------------------|
| Poisson ridge att/dif/casa |        0.9652 |     0.0833 |        -0.4183 |    0.6758 | si                    |
| media campionato           |       -1.8421 |     1.565  |        -1.816  |    0.0694 | si                    |
| media casa/trasferta       |        0.9549 |     0.1971 |        -0.229  |    0.8189 | si                    |
| media squadra              |        0.7467 |     0.0803 |        -3.1538 |    0.0016 | NO                    |
| media squadra + campo      |        0.7846 |     0.0752 |        -2.8636 |    0.0042 | NO                    |

Due letture obbligatorie:

- **`media campionato` non e' interpretabile.** Il suo `log(lambda)` e' quasi costante (sharpness 0.050), quindi la pendenza e' stimata su nessuna variazione: l'errore standard di 1.56 lo dice. Il "si" in tabella e' assenza di potenza, non calibrazione.
- **I due baseline informativi sono miscalibrati, il modello no.** `media squadra` (b = 0.747) e `media squadra + campo` (b = 0.785) sono sotto 1.0 di piu' di tre e quasi tre errori standard: le loro previsioni sono **troppo estreme**, perche' una media campionaria non regredisce verso il centro e prende per buono il rumore di poche partite. E' esattamente il difetto che la penalizzazione ridge del modello corregge, ed e' la sua giustificazione empirica piu' netta — piu' netta del vantaggio sul MAE, che resta sotto le due deviazioni standard.

## 4. Tabelle di affidabilita' (Over 4.5), tutti i modelli

`se` e' l'errore standard binomiale della frequenza osservata, `z` lo scarto in sue unita'. Le fasce vuote non compaiono, ed e' informativo: quante fasce un modello riesce a popolare **e' la sua risoluzione**. `media campionato` ne popola due su otto.

**Poisson ridge att/dif/casa**

| bin           |   n |   p_mean |   freq |    diff |     se |       z |
|:--------------|----:|---------:|-------:|--------:|-------:|--------:|
| (-0.001, 0.1] |  14 |   0.0741 | 0.0714 | -0.0026 | 0.07   | -0.0376 |
| (0.1, 0.2]    |  72 |   0.1517 | 0.1806 |  0.0289 | 0.0423 |  0.683  |
| (0.2, 0.3]    | 142 |   0.2533 | 0.2394 | -0.0139 | 0.0365 | -0.3809 |
| (0.3, 0.4]    | 150 |   0.3504 | 0.3733 |  0.0229 | 0.039  |  0.5887 |
| (0.4, 0.5]    | 135 |   0.4494 | 0.4741 |  0.0247 | 0.0428 |  0.5772 |
| (0.5, 0.6]    |  95 |   0.5493 | 0.5684 |  0.0191 | 0.051  |  0.3745 |
| (0.6, 0.7]    |  32 |   0.6522 | 0.5625 | -0.0897 | 0.0842 | -1.0649 |
| (0.7, 1.0]    |  20 |   0.7546 | 0.8    |  0.0454 | 0.0962 |  0.4715 |

**media campionato**

| bin        |   n |   p_mean |   freq |    diff |     se |       z |
|:-----------|----:|---------:|-------:|--------:|-------:|--------:|
| (0.3, 0.4] | 650 |   0.3795 | 0.3908 |  0.0113 | 0.019  |  0.5935 |
| (0.4, 0.5] |  10 |   0.4031 | 0.2    | -0.2031 | 0.1551 | -1.3092 |

**media casa/trasferta**

| bin        |   n |   p_mean |   freq |    diff |     se |       z |
|:-----------|----:|---------:|-------:|--------:|-------:|--------:|
| (0.2, 0.3] |  32 |   0.2916 | 0.4062 |  0.1146 | 0.0803 |  1.4263 |
| (0.3, 0.4] | 298 |   0.3144 | 0.3221 |  0.0077 | 0.0269 |  0.2863 |
| (0.4, 0.5] | 330 |   0.4466 | 0.4455 | -0.0011 | 0.0274 | -0.0415 |

**media squadra**

| bin           |   n |   p_mean |   freq |    diff |     se |       z |
|:--------------|----:|---------:|-------:|--------:|-------:|--------:|
| (-0.001, 0.1] |  15 |   0.0819 | 0.2    |  0.1181 | 0.0708 |  1.6669 |
| (0.1, 0.2]    |  96 |   0.153  | 0.1875 |  0.0345 | 0.0367 |  0.9389 |
| (0.2, 0.3]    | 100 |   0.2535 | 0.34   |  0.0865 | 0.0435 |  1.9873 |
| (0.3, 0.4]    | 164 |   0.3474 | 0.3232 | -0.0242 | 0.0372 | -0.6506 |
| (0.4, 0.5]    | 137 |   0.4567 | 0.5036 |  0.047  | 0.0426 |  1.1039 |
| (0.5, 0.6]    |  84 |   0.5411 | 0.4524 | -0.0887 | 0.0544 | -1.6318 |
| (0.6, 0.7]    |  55 |   0.6537 | 0.6545 |  0.0008 | 0.0642 |  0.0131 |
| (0.7, 1.0]    |   9 |   0.7244 | 0.5556 | -0.1689 | 0.1489 | -1.1339 |

**media squadra + campo**

| bin           |   n |   p_mean |   freq |    diff |     se |       z |
|:--------------|----:|---------:|-------:|--------:|-------:|--------:|
| (-0.001, 0.1] |  26 |   0.0662 | 0.1538 |  0.0876 | 0.0488 |  1.7964 |
| (0.1, 0.2]    |  83 |   0.1474 | 0.1807 |  0.0333 | 0.0389 |  0.8554 |
| (0.2, 0.3]    | 126 |   0.2501 | 0.3492 |  0.0991 | 0.0386 |  2.568  |
| (0.3, 0.4]    | 113 |   0.35   | 0.3186 | -0.0314 | 0.0449 | -0.6994 |
| (0.4, 0.5]    | 145 |   0.4436 | 0.4    | -0.0436 | 0.0413 | -1.0569 |
| (0.5, 0.6]    |  94 |   0.5472 | 0.4894 | -0.0578 | 0.0513 | -1.1258 |
| (0.6, 0.7]    |  53 |   0.6398 | 0.717  |  0.0772 | 0.0659 |  1.1706 |
| (0.7, 1.0]    |  20 |   0.7385 | 0.75   |  0.0115 | 0.0983 |  0.1166 |

### Scomposizione di Murphy

Brier = affidabilita' - risoluzione + incertezza. L'**affidabilita'** (bassa e' meglio) e' l'errore che si toglierebbe ricalibrando; la **risoluzione** (alta e' meglio) e' l'unica parte che misura se il modello sa qualcosa. `residuo` e' lo scarto dovuto alla discretizzazione in fasce e va guardato prima dei tre termini.

| modello                    |   brier |   affidabilita |   risoluzione |   incertezza |   residuo |   n_fasce |
|:---------------------------|--------:|---------------:|--------------:|-------------:|----------:|----------:|
| Poisson ridge att/dif/casa | 0.21288 |        0.00088 |       0.02444 |      0.23743 |  -0.001   |         8 |
| media campionato           | 0.23804 |        0.00075 |       0.00054 |      0.23743 |   0.0004  |         2 |
| media casa/trasferta       | 0.23519 |        0.00066 |       0.00362 |      0.23743 |   0.00072 |         3 |
| media squadra              | 0.22251 |        0.00362 |       0.01765 |      0.23743 |  -0.00089 |         8 |
| media squadra + campo      | 0.21929 |        0.00386 |       0.02283 |      0.23743 |   0.00083 |         8 |

### Brier su piu' soglie

Una sola soglia puo' essere fortunata: il rango dei modelli va verificato dove l'evento e' comune e dove e' raro. Ultima riga: il baseline che prevede a tutti il tasso base walk-forward.

| modello                             |   Over 2.5 |   Over 3.5 |   Over 4.5 |   Over 5.5 |
|:------------------------------------|-----------:|-----------:|-----------:|-----------:|
| Poisson ridge att/dif/casa          |     0.1907 |     0.2258 |     0.2129 |     0.1682 |
| media campionato                    |     0.2055 |     0.2493 |     0.238  |     0.1865 |
| media casa/trasferta                |     0.2044 |     0.245  |     0.2352 |     0.1825 |
| media squadra                       |     0.1956 |     0.2375 |     0.2225 |     0.1773 |
| media squadra + campo               |     0.1951 |     0.2332 |     0.2193 |     0.1727 |
| baseline: tasso base (walk-forward) |     0.2074 |     0.2499 |     0.239  |     0.188  |

Frequenza con cui l'evento si e' effettivamente verificato, per leggere le colonne (un evento raro ha Brier basso per costruzione, non per merito):

|                     |   Over 2.5 |   Over 3.5 |   Over 4.5 |   Over 5.5 |
|:--------------------|-----------:|-----------:|-----------:|-----------:|
| frequenza osservata |     0.7121 |     0.5394 |     0.3879 |      0.247 |

Il modello batte il tasso base su tutte e quattro le soglie, e il baseline `media squadra + campo` su tutte e quattro; ma il margine su quest'ultimo e' dello stesso ordine su ogni soglia, cioe' piccolo.

## 5. L'intera distribuzione predittiva, non solo la media

La pendenza di calibrazione controlla il livello di lambda. Il PIT randomizzato controlla la distribuzione: e' uniforme se e solo se anche la forma e' giusta. Eccesso agli estremi = predittiva troppo stretta, eccesso al centro = troppo larga.

- **Poisson ridge att/dif/casa**: chi2 = 6.03 su 9 gradi di liberta', p = 0.737; media 0.4976 (attesa 0.5), sd 0.2945 (attesa 0.289)
- **media squadra + campo**: chi2 = 7.39, p = 0.596; media 0.5000, sd 0.2977

Conteggi per decile del PIT (attesi 66.0 per fascia): 77, 63, 59, 73, 54, 65, 67, 68, 64, 70

Copertura degli intervalli di previsione. Su conteggi la copertura e' strutturalmente **conservativa** — gli estremi sono interi — quindi qualche punto sopra il nominale e' atteso; sotto il nominale no.

|   livello |   copertura |   ampiezza_media |
|----------:|------------:|-----------------:|
|      0.5  |      0.6242 |           3.8985 |
|      0.8  |      0.8667 |           6.4439 |
|      0.95 |      0.9818 |           9.3136 |

Stesso calcolo per il baseline migliore:

|   livello |   copertura |   ampiezza_media |
|----------:|------------:|-----------------:|
|      0.5  |      0.6091 |           3.8939 |
|      0.8  |      0.8652 |           6.5091 |
|      0.95 |      0.9788 |           9.397  |

## 6. Il modello e' storto da qualche parte?

Un MAE aggregato accettabile puo' nascondere un segmento in cui il modello sbaglia sistematicamente. Baseline affiancato in ogni segmento.

**Per campo** — modello:

| segmento   |   n |    mae |    bias |   corr |   sharpness |   calib_slope |   calib_se |   brier |
|:-----------|----:|-------:|--------:|-------:|------------:|--------------:|-----------:|--------:|
| casa       | 330 | 1.8581 | -0.0087 | 0.3902 |      0.947  |        1.0264 |     0.124  |  0.22   |
| trasferta  | 330 | 1.6208 |  0.0768 | 0.3131 |      0.8113 |        0.831  |     0.1327 |  0.2058 |

**Per campo** — baseline `media squadra + campo`:

| segmento   |   n |    mae |    bias |   corr |   sharpness |   calib_slope |   calib_se |   brier |
|:-----------|----:|-------:|--------:|-------:|------------:|--------------:|-----------:|--------:|
| casa       | 330 | 1.8939 | -0.0117 | 0.3496 |      0.9727 |        0.8715 |     0.12   |  0.2276 |
| trasferta  | 330 | 1.6763 |  0.0821 | 0.2976 |      0.9885 |        0.6281 |     0.1074 |  0.211  |

**Per terzile di lambda previsto** — modello:

| segmento   |   n |    mae |    bias |   corr |   sharpness |   calib_slope |   calib_se |   brier |
|:-----------|----:|-------:|--------:|-------:|------------:|--------------:|-----------:|--------:|
| basso      | 220 | 1.498  |  0.0277 | 0.1439 |      0.401  |        0.6844 |     0.2902 |  0.1625 |
| medio      | 220 | 1.7148 | -0.03   | 0.1302 |      0.2386 |        1.1488 |     0.5644 |  0.2394 |
| alto       | 220 | 2.0056 |  0.1045 | 0.2684 |      0.6367 |        1.0886 |     0.2423 |  0.2367 |

**Per terzile di lambda previsto** — baseline `media squadra + campo`:

| segmento   |   n |    mae |    bias |   corr |   sharpness |   calib_slope |   calib_se |   brier |
|:-----------|----:|-------:|--------:|-------:|------------:|--------------:|-----------:|--------:|
| basso      | 220 | 1.6184 |  0.1472 | 0.0672 |      0.7519 |        0.1978 |     0.1619 |  0.1749 |
| medio      | 220 | 1.7587 | -0.0335 | 0.1214 |      0.694  |        0.3893 |     0.1929 |  0.2493 |
| alto       | 220 | 1.9782 | -0.0081 | 0.3008 |      0.757  |        1.0158 |     0.2007 |  0.2336 |

**Per meta' di stagione** — modello:

| segmento   |   n |    mae |   bias |   corr |   sharpness |   calib_slope |   calib_se |   brier |
|:-----------|----:|-------:|-------:|-------:|------------:|--------------:|-----------:|--------:|
| 1a meta'   | 280 | 1.7845 | 0.0171 | 0.3396 |      0.8633 |        0.9269 |     0.1414 |  0.2214 |
| 2a meta'   | 380 | 1.7063 | 0.0466 | 0.4309 |      1.025  |        0.9858 |     0.103  |  0.2066 |

**Per meta' di stagione** — baseline `media squadra + campo`:

| segmento   |   n |    mae |   bias |   corr |   sharpness |   calib_slope |   calib_se |   brier |
|:-----------|----:|-------:|-------:|-------:|------------:|--------------:|-----------:|--------:|
| 1a meta'   | 280 | 1.8507 | 0.0083 | 0.2998 |      1.0433 |        0.665  |     0.1138 |  0.2327 |
| 2a meta'   | 380 | 1.7367 | 0.055  | 0.4078 |      1.0546 |        0.8752 |     0.0998 |  0.2094 |

Tre letture:

- **Il MAE cresce con lambda** (1.498 nel terzile basso, 2.006 nell'alto). Non e' un difetto: su conteggi la varianza cresce con la media, quindi il MAE **deve** crescere. Va notato perche' rende il MAE aggregato dominato dalle squadre che tirano di piu'.
- **Il bias e' concentrato in trasferta** (+0.0768 contro -0.0087 in casa): il modello sovrastima leggermente chi gioca fuori, cioe' il coefficiente di campo e' un filo troppo piccolo. Lo scarto vale 0.077 tiri in porta su una media di 4, ed e' dello stesso ordine anche per il baseline (+0.0821): e' una proprieta' dei dati, non del modello.
- **Le pendenze per terzile non vanno confrontate con quella aggregata.** Dentro un terzile `log(lambda)` varia pochissimo per costruzione, quindi la pendenza e' stimata su un intervallo artificialmente ristretto e il suo errore standard esplode (fino a 0.56 contro 0.083 sul campione intero). Servono a vedere il **bias** per fascia, non la pendenza.

Il confronto che conta e' l'ultima colonna, riga per riga: il modello ha un Brier migliore del baseline in 6 segmenti su 7.
Perde in: **alto** (terzile di lambda previsto, +0.0031).
Il terzile alto e' lo stesso segmento su cui la Fase 3 aveva trovato il danno maggiore della scomposizione per giocatore, e la causa e' la stessa: le squadre che tirano molto sono quelle che il ritorno alla media penalizza, e la ridge **e'** un ritorno alla media. Qui il prezzo e' piccolo — al punto 3 si vede che comprare quella compressione compra anche l'unica calibrazione accettabile fra i modelli in gara — ma il segno e' coerente fra le due fasi e non e' un caso.

## 7. Fase 3: il metodo dal basso, con i baseline accanto

Stima sulle prime 19 partite di ogni squadra, previsione delle 19 successive; 20 righe, una per squadra. tau = 3.0.

| metodo                                        |    MAE |   RMSE |   bias |     corr |
|:----------------------------------------------|-------:|-------:|-------:|---------:|
| dall'alto (= media squadra 1a meta')          | 0.4158 | 0.561  | 0.0526 |   0.8386 |
| dal basso, livello dai giocatori (A)          | 0.4823 | 0.6163 | 0.0466 |   0.7979 |
| dal basso, compositivo (B, quello pubblicato) | 0.4154 | 0.5599 | 0.0788 |   0.8418 |
| baseline: media campionato                    | 0.8216 | 1.0206 | 0.0526 | n.d.      |

`n.d.`: la media di campionato e' costante su tutte le squadre, quindi la correlazione non e' definita. E' il suo limite, non un dato mancante.

- dal basso (A, livello dai giocatori) contro dall'alto: differenza appaiata dei |errori| -0.0665 a favore di **dall'alto** (t = -1.33)
- dall'alto contro media di campionato: +0.4058 a favore di dall'alto (t = 2.64)

Il punto da leggere: **"dall'alto" e' esattamente il baseline "media squadra"** calcolato sulla prima meta' di stagione. L'estimatore A non batte il piu' stupido dei baseline di squadra. Con 20 righe la differenza non e' significativa in nessuno dei due sensi, ma il segno e' contrario al metodo piu' complesso, e non c'e' nulla nei dati che sostenga di adottarlo.

**La riga B e' un'altra cosa e va letta con l'avvertenza di Fase 6B**: l'estimatore compositivo — quello che la proiezione pubblica — non fissa il livello, quindi il suo baseline corretto e' "nessun aggiustamento di rosa", che qui coincide numericamente con la riga dall'alto. Le due colonne sono quasi identiche perche' fra le due meta' di una stessa stagione la rosa non cambia: il confronto non ha la potenza per distinguerle e **non e' una convalida**. Dettaglio, con l'effetto minimo rilevabile, in `reports/phase6_compositivo.md`.

## Limiti dichiarati

- **Una stagione sola.** Ogni intervallo qui dentro e' condizionato a 2025-26. Nessuno di questi numeri dice come il modello si comporti attraverso stagioni, che e' proprio l'orizzonte della proiezione 2026-27.
- **660 righe valutate, 20 squadre.** I confronti appaiati hanno gradi di liberta' effettivi minori del nominale: le due righe della stessa partita non sono indipendenti.
- **Il burn-in di 6 giornate e' una scelta dichiarata**, non ottimizzata: e' fissato in `config.BURN_IN_ROUND` prima di guardare i risultati. Abbassarlo peggiorerebbe tutti i modelli, alzarlo li migliorerebbe tutti; il confronto fra modelli non ne risente.
- **Il test di Fase 3 ha 20 osservazioni.** Va letto come indicazione, non come dimostrazione. E' pero' l'unica prova fuori campione disponibile sull'orizzonte che interessa.
- **`r` walk-forward parte da 60 righe di storia.** Prima di quella soglia le probabilita' sono poissoniane, quindi leggermente troppo sicure sulle prime date valutate.
- **Nessun backtest su quote**: servirebbero prezzi di mercato reali. Il codice che usava quote generate dal modello e' in `legacy/` e non va riusato.
