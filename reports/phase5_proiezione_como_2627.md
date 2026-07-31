# Proiezione Como 2026-27 — output completo

Rigenerato da `scripts/run_phase5.py`. Ogni numero viene dai dati; nessuno e' stato aggiustato a mano.

## Il numero, e cosa c'e' dentro

| | per partita | stagione (38) | IC 80% |
|---|---|---|---|
| **dal basso** (questo file) | **5.03** | **191** | [151, 240] |
| dall'alto (riferimento) | 4.90 | 186 | [152, 222] |

Rapporto compositivo (ricambio di rosa + minuti): **1.0101** (+1.0%). E' l'unica cosa che i dati per giocatore aggiungono davvero: il **livello** resta quello dall'alto, per non contarlo due volte.

La media simulata e' 193.6, sopra la mediana: gli shock sono lognormali e la media ne risente per convessita'. **La mediana e' la sintesi da leggere.**

## L'intervallo e' piu' largo del riferimento, non piu' stretto

Non e' un difetto del calcolo: e' il risultato. Il metodo per giocatore **sostituisce** lo 0.4% di incertezza sui coefficienti con l'incertezza su minuti, tassi individuali e nuovi arrivi, e non tocca lo shock di squadra, che resta la fonte dominante.

| fonte                  |   varianza |   quota |
|:-----------------------|-----------:|--------:|
| team_shock             |    511.965 |   0.423 |
| sampling               |    221.416 |   0.183 |
| minutes                |    219.242 |   0.181 |
| player_rates           |    123.042 |   0.102 |
| league_level           |     46.305 |   0.038 |
| new_signings           |     17.029 |   0.014 |
| TOTALE (tutte insieme) |   1210.86  |   1     |

## Limiti, accanto al numero e non in fondo

- **Rosa provvisoria**: il mercato chiude il 1 settembre 2026.
- **6 nuovi arrivi di movimento senza alcun dato**: 18% dei minuti proiettati e 13% del lambda poggiano sulla sola media di ruolo.
- **Rotazione Champions** fatta variare fra 5% e 25%: non e' stimabile da una stagione in cui il Como non giocava le coppe.
- **Una sola stagione**: tau = 3 scelto per validazione interna alla stagione, non su un orizzonte annuale.
- **Il metodo dal basso non ha superato la sua verifica** (Fase 3 e Fase 4): non batte il tasso di squadra. Questo file va letto come scomposizione di un numero deciso dall'alto, non come una previsione migliore.

## Scomposizione per giocatore

`sot_per90_neutro` = tiri in porta per 90 minuti in una squadra di forza media contro una difesa media: e' la quantita' portabile fra club. `se_v` e' l'errore standard dell'effetto individuale — grande dove i minuti sono pochi, ed e' cosi' che l'incertezza si propaga invece di sparire.

| name                  | role   | is_new   |   minutes_2526 |   sot_2526 |   minutes_proj |   minutes_per_match |   sot_per90_neutro |    se_v |   contributo |   quota_lambda |
|:----------------------|:-------|:---------|---------------:|-----------:|---------------:|--------------------:|-------------------:|--------:|-------------:|---------------:|
| Nico Paz              | MID    | False    |           3101 |         48 |       2878.39  |              75.747 |              0.979 |   0.151 |        1.003 |          0.21  |
| Tasos Douvikas        | FWD    | False    |           2457 |         30 |       2330.99  |              61.342 |              0.869 |   0.173 |        0.721 |          0.151 |
| Lucas da Cunha        | MID    | False    |           2940 |         16 |       2741.54  |              72.146 |              0.374 |   0.221 |        0.365 |          0.076 |
| Alvaro Morata         | FWD    | False    |           1043 |          8 |       1129.09  |              29.713 |              0.648 |   0.26  |        0.26  |          0.054 |
| Jesus Rodriguez       | MID    | False    |           1874 |         12 |       1835.44  |              48.301 |              0.397 |   0.248 |        0.26  |          0.054 |
| Maximo Perrone        | MID    | False    |           2959 |          9 |       2757.69  |              72.571 |              0.254 |   0.25  |        0.249 |          0.052 |
| Martin Baturina       | MID    | False    |           1719 |          9 |       1703.69  |              44.834 |              0.352 |   0.267 |        0.214 |          0.045 |
| Assane Diao           | MID    | False    |           1143 |         10 |       1214.09  |              31.95  |              0.484 |   0.276 |        0.209 |          0.044 |
| Jacobo Ramon          | DEF    | False    |           2977 |          9 |       2772.99  |              72.973 |              0.179 |   0.278 |        0.176 |          0.037 |
| Maxence Caqueret      | MID    | False    |           1596 |          4 |       1599.14  |              42.083 |              0.246 |   0.298 |        0.14  |          0.029 |
| Marc-Oliver Kempf     | DEF    | False    |           2548 |          6 |       2408.34  |              63.377 |              0.151 |   0.3   |        0.129 |          0.027 |
| Jayden Addai          | MID    | False    |            741 |          6 |        872.387 |              22.958 |              0.414 |   0.314 |        0.129 |          0.027 |
| Adrian Lahdo          | MID    | True     |              0 |          0 |       1131.35  |              29.772 |              0.306 | nan     |        0.123 |          0.026 |
| Mattia Liberali       | MID    | True     |              0 |          0 |       1131.35  |              29.772 |              0.306 | nan     |        0.123 |          0.026 |
| Luis Milla            | MID    | True     |              0 |          0 |       1131.35  |              29.772 |              0.306 | nan     |        0.123 |          0.026 |
| Fabio Rispoli         | MID    | True     |              0 |          0 |       1131.35  |              29.772 |              0.306 | nan     |        0.123 |          0.026 |
| Nicolas Kuhn          | MID    | False    |            757 |          3 |        885.987 |              23.315 |              0.296 |   0.33  |        0.093 |          0.02  |
| Ivan Smolcic          | DEF    | False    |           1814 |          4 |       1784.44  |              46.959 |              0.146 |   0.327 |        0.093 |          0.019 |
| Alex Valle            | DEF    | False    |           2209 |          2 |       2120.19  |              55.794 |              0.109 |   0.331 |        0.082 |          0.017 |
| Kaiki Bruno           | DEF    | True     |              0 |          0 |       1131.35  |              29.772 |              0.132 | nan     |        0.053 |          0.011 |
| Andres Cuenca         | DEF    | True     |              0 |          0 |       1131.35  |              29.772 |              0.132 | nan     |        0.053 |          0.011 |
| Ignace Van der Brempt | DEF    | False    |           1019 |          0 |       1108.69  |              29.176 |              0.104 |   0.367 |        0.041 |          0.009 |
| Edoardo Goldaniga     | DEF    | False    |             18 |          0 |        257.837 |               6.785 |              0.131 |   0.407 |        0.012 |          0.003 |
