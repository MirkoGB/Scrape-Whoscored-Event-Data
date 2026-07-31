# Fase 3 — proiezione Como 2026-27 dal basso

## Esito in breve

- rapporto compositivo (ricambio di rosa + minuti): **1.0101** (+1.0%)
- proiezione: **5.03** tiri in porta a partita, **191** in stagione (mediana)
- intervallo 80%: **[151, 240]**
- riferimento dall'alto: 4.9 a partita, 186 in stagione, IC80% [152, 222]

La media simulata e' 193.6, superiore alla mediana: gli shock moltiplicativi sono lognormali e la media ne risente per convessita'. La mediana e' la sintesi da leggere.

## Il metodo dal basso aggiunge informazione?

Test: stima su 19 partite per squadra, previsione delle 19 successive.

| metodo | MAE | correlazione |
|---|---|---|
| dall'alto (tasso di squadra) | **0.4158** | 0.8386 |
| dal basso, livello dai giocatori | 0.4823 | 0.7979 |

Differenza appaiata: -0.0665 (t = -1.33). **Il metodo dal basso non batte quello dall'alto**; il segno gli e' contrario.

**Quale dei due estimatori e' questo** (chiarito in Fase 6B): quello che fissa il **livello** dai giocatori. La proiezione pubblicata usa l'altro, il compositivo, che prende il livello dall'alto e applica solo il rapporto di rosa: quello e' testato in `reports/phase6_compositivo.md`, e il test non ha la potenza per dire niente su di lui.

### Perche': doppia compressione

- pendenza della regressione dal-basso su dall-alto: **0.875** (1.0 = nessuna compressione aggiuntiva)
- correlazione fra livello della squadra e compressione aggiuntiva: **-0.466**
- squadre sopra 4.5: MAE dall'alto 0.541 contro 0.729 dal basso
- squadre sotto 4.5: 0.348 contro 0.349

Lo shrinkage per giocatore verso la media di ruolo si somma a quello gia' applicato dalla ridge di squadra. L'effetto colpisce solo le squadre di vertice, cioe' proprio quelle su cui il ritorno alla media e' gia' sospetto di essere troppo conservativo.

## Scomposizione della varianza

| fonte                  |   varianza |   quota |
|:-----------------------|-----------:|--------:|
| team_shock             |    511.965 |   0.423 |
| sampling               |    221.416 |   0.183 |
| minutes                |    219.242 |   0.181 |
| player_rates           |    123.042 |   0.102 |
| league_level           |     46.305 |   0.038 |
| new_signings           |     17.029 |   0.014 |
| TOTALE (tutte insieme) |   1210.86  |   1     |

Riferimento dall'alto: shock di squadra 65%, campionamento 29%, livello di campionato 6%, coefficienti 0.4%.

**Lo shock di squadra non e' stato ridotto.** La sua varianza assoluta (512) e' quella ereditata dal modello dall'alto: la quota scende dal 65% al 42% solo perche' il totale e' cresciuto, non perche' il numeratore sia calato. Il metodo per giocatore **aggiunge** incertezza su minuti e tassi individuali al posto dello 0.4% dei coefficienti.

## Limiti dichiarati

- **Rosa provvisoria**: mercato aperto fino al 1 settembre 2026.
- **6 nuovi arrivi senza alcun dato**: 6788 minuti proiettati su 37189 (18%) e 13% del lambda poggiano sulla sola media di ruolo.
- **Rotazione Champions**: assunzione non stimabile da dati in cui il Como non giocava le coppe. Fatta variare fra 5% e 25% nel Monte Carlo.
- **Una sola stagione**: tau = 3.0 scelto per validazione incrociata interna alla stagione, non su un orizzonte annuale.

## Scomposizione per giocatore

| name                  | role   | is_new   |   minutes_2526 |   minutes_proj |   sot_per90_neutro |    se_v |   contributo |
|:----------------------|:-------|:---------|---------------:|---------------:|-------------------:|--------:|-------------:|
| Nico Paz              | MID    | False    |           3101 |       2878.39  |              0.979 |   0.151 |        1.003 |
| Jacobo Ramon          | DEF    | False    |           2977 |       2772.99  |              0.179 |   0.278 |        0.176 |
| Maximo Perrone        | MID    | False    |           2959 |       2757.69  |              0.254 |   0.25  |        0.249 |
| Lucas da Cunha        | MID    | False    |           2940 |       2741.54  |              0.374 |   0.221 |        0.365 |
| Marc-Oliver Kempf     | DEF    | False    |           2548 |       2408.34  |              0.151 |   0.3   |        0.129 |
| Tasos Douvikas        | FWD    | False    |           2457 |       2330.99  |              0.869 |   0.173 |        0.721 |
| Alex Valle            | DEF    | False    |           2209 |       2120.19  |              0.109 |   0.331 |        0.082 |
| Jesus Rodriguez       | MID    | False    |           1874 |       1835.44  |              0.397 |   0.248 |        0.26  |
| Ivan Smolcic          | DEF    | False    |           1814 |       1784.44  |              0.146 |   0.327 |        0.093 |
| Martin Baturina       | MID    | False    |           1719 |       1703.69  |              0.352 |   0.267 |        0.214 |
| Maxence Caqueret      | MID    | False    |           1596 |       1599.14  |              0.246 |   0.298 |        0.14  |
| Assane Diao           | MID    | False    |           1143 |       1214.09  |              0.484 |   0.276 |        0.209 |
| Luis Milla            | MID    | True     |              0 |       1131.35  |              0.306 | nan     |        0.123 |
| Mattia Liberali       | MID    | True     |              0 |       1131.35  |              0.306 | nan     |        0.123 |
| Kaiki Bruno           | DEF    | True     |              0 |       1131.35  |              0.132 | nan     |        0.053 |
| Fabio Rispoli         | MID    | True     |              0 |       1131.35  |              0.306 | nan     |        0.123 |
| Adrian Lahdo          | MID    | True     |              0 |       1131.35  |              0.306 | nan     |        0.123 |
| Andres Cuenca         | DEF    | True     |              0 |       1131.35  |              0.132 | nan     |        0.053 |
| Alvaro Morata         | FWD    | False    |           1043 |       1129.09  |              0.648 |   0.26  |        0.26  |
| Ignace Van der Brempt | DEF    | False    |           1019 |       1108.69  |              0.104 |   0.367 |        0.041 |
| Nicolas Kuhn          | MID    | False    |            757 |        885.987 |              0.296 |   0.33  |        0.093 |
| Jayden Addai          | MID    | False    |            741 |        872.387 |              0.414 |   0.314 |        0.129 |
| Edoardo Goldaniga     | DEF    | False    |             18 |        257.837 |              0.131 |   0.407 |        0.012 |