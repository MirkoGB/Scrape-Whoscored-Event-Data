# Fase 2 — modello within-season

Righe valutate: **660** su 760 (burn-in: dalla 6a partita di ciascuna squadra).
Tutto walk-forward: parametri, alpha e medie mobili usano solo il passato.

## Predittori candidati

`d_oos` = guadagno di log-verosimiglianza **fuori campione** sul modello base; `t` = statistica appaiata sullo stesso guadagno; `d_ins` = variazione **in campione**.

| predittore   |   d_oos |      t |   d_ins | tenuto   |
|:-------------|--------:|-------:|--------:|:---------|
| poss_att     |   3.821 |  1.42  |   0.257 | False    |
| tilt_att     |   3.44  |  1.337 |   0.696 | False    |
| box_att      |   1.864 |  0.888 |  -0.525 | False    |
| xgps_def     |   0.104 |  0.157 |   0.311 | False    |
| ppda_att     |  -0.015 | -0.013 |  -0.429 | False    |
| dist_att     |  -0.205 | -0.312 |  -0.334 | False    |
| xgps_att     |  -1.077 | -0.817 |   0.161 | False    |
| ppda_def     |  -1.039 | -1.182 |  -0.459 | False    |

Soglia adottata: t > 2.0. Predittori tenuti: **nessuno**.

## Sovradispersione condizionata a lambda

- r NB2 = **26.0**, IC95% profilo [13.7, 111.8]
- var/media **grezzo** 1.363
- var/media **condizionato a lambda** 1.156
- dispersione di Pearson 1.149

## Metriche vs baseline (stesse righe)

| modello                    |   n |    mae |   bias |    corr |   calib_slope |   calib_se |   loglik_poisson |   brier |   brier_base |
|:---------------------------|----:|-------:|-------:|--------:|--------------:|-----------:|-----------------:|--------:|-------------:|
| Poisson ridge att/dif/casa | 660 | 1.7395 | 0.0341 |  0.3944 |        0.9652 |     0.0833 |         -1418.94 |  0.2127 |       0.2374 |
| media campionato           | 660 | 1.8771 | 0.0361 | -0.0393 |       -1.8421 |     1.565  |         -1488.03 |  0.238  |       0.2374 |
| media casa/trasferta       | 660 | 1.8802 | 0.0361 |  0.1618 |        0.9549 |     0.1971 |         -1475.32 |  0.2353 |       0.2374 |
| media squadra              | 660 | 1.8116 | 0.0352 |  0.3187 |        0.7467 |     0.0803 |         -1447.79 |  0.2225 |       0.2374 |
| media squadra + campo      | 660 | 1.7851 | 0.0352 |  0.3621 |        0.7846 |     0.0752 |         -1434.71 |  0.2192 |       0.2374 |

Test appaiati del modello contro ciascun baseline:

- vs media campionato: d = +59.72, t = 5.15
- vs media casa/trasferta: d = +48.71, t = 4.63
- vs media squadra: d = +25.06, t = 2.82
- vs media squadra + campo: d = +13.88, t = 1.86

## Affidabilita' (Over 4.5, NB2)

| bin           |   n |   p_mean |   freq |    diff |     se |       z |
|:--------------|----:|---------:|-------:|--------:|-------:|--------:|
| (-0.001, 0.1] |  15 |   0.0768 | 0.0667 | -0.0101 | 0.0687 | -0.1469 |
| (0.1, 0.2]    |  71 |   0.1531 | 0.1831 |  0.03   | 0.0427 |  0.7019 |
| (0.2, 0.3]    | 144 |   0.2534 | 0.25   | -0.0034 | 0.0362 | -0.0928 |
| (0.3, 0.4]    | 149 |   0.3513 | 0.3624 |  0.0111 | 0.0391 |  0.283  |
| (0.4, 0.5]    | 131 |   0.4492 | 0.4809 |  0.0317 | 0.0435 |  0.7287 |
| (0.5, 0.6]    |  97 |   0.5477 | 0.5464 | -0.0013 | 0.0505 | -0.0249 |
| (0.6, 0.7]    |  36 |   0.6525 | 0.6389 | -0.0136 | 0.0794 | -0.1715 |
| (0.7, 1.0]    |  17 |   0.762  | 0.7647 |  0.0027 | 0.1033 |  0.0261 |
