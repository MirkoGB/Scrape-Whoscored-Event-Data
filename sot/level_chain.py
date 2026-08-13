# -*- coding: utf-8 -*-
"""Da dove viene il livello della proiezione: la catena aritmetica, esplicita.

Il README metteva sulla stessa pagina tre numeri — 4.34 (rating del Como in
`fig5`), 4.90 (riferimento dall'alto) e 5.03 (proiezione pubblicata) — senza
nessun passaggio che li collegasse. Questo modulo ricostruisce ogni
moltiplicazione, **nessuna implicita**, e mostra il fatto centrale: sono due
catene separate che non si toccano.

I DUE RAMI
----------
* **Ramo del modello**: rating -> vantaggio del campo -> calendario reale ->
  osservato. E' quello che il modello di squadra sa dire sul Como 2025-26.
* **Ramo pubblicato**: 4.90 -> rapporto compositivo -> convessita' Monte Carlo
  -> 5.03. E' quello che finisce nel README.

Il ramo del modello **non entra** nel ramo pubblicato. In
`project_2627.monte_carlo` la riga

    lam = lam / summary["lambda_bottomup_2627"] * anchor

normalizza via il contesto di squadra: `context_como` compare a numeratore e a
denominatore e si semplifica esattamente. Si semplifica anche nel rapporto
compositivo, che e' il quoziente di due ricomposizioni con lo stesso contesto.
Quindi rating, `alpha`, effetti attacco/difesa e vantaggio del campo
determinano **come** il lambda si ripartisce fra i giocatori, non **quanto**
vale. Il livello e' 4.90 x rapporto x convessita', e basta.
`livello_non_dipende_dal_contesto` lo verifica numericamente invece di
affermarlo.

LA SCALA DI `fig5`
------------------
`exp(mu + attacco + difesa media)` non contiene il termine di campo e `is_home`
e' una dummy 0/1: quel numero e' il valore **in trasferta** contro una difesa
media, non a campo neutro. Per il Como: 4.343 in trasferta, 5.287 in casa,
4.815 di media su 19 + 19. La differenza non e' cosmetica — con 19 partite in
casa il rating sottostima di circa il 10% cio' che la squadra fa in stagione.
Qui si documenta e si converte; **non si cambia la definizione**, perche'
aggiungere mezzo termine di campo porterebbe 4.34 a 4.79, cioe' piu' vicino a
4.90, che e' esattamente il modo di far tornare i numeri che il progetto
vieta.

LA COMPRESSIONE
---------------
La ridge minimizza l'errore predittivo, non stima livelli senza distorsione:
tira gli attacchi verso zero, quindi comprime le squadre di vertice verso la
media di campionato. E' lo stesso fenomeno gia' documentato altrove — terzile
alto di lambda in Fase 4, danno sopra 4.5 SoT in Fase 3 — mai pero' quantificato
come pendenza. `compressione_ratings` la misura regredendo i rating sui tassi
grezzi riportati sulla stessa scala di campo: la pendenza e' il fattore di
compressione, il suo reciproco la de-compressione che servirebbe per tornare a
un livello non distorto. La regressione e' **descrittiva e in campione**: dice
quanto la ridge comprime, non quanto una squadra tirera' l'anno prossimo.

`rho`: LA PERSISTENZA FRA STAGIONI (Fase 6C)
--------------------------------------------
Il livello usato assume implicitamente che il Como trattenga una quota `rho`
del proprio eccesso sulla media di campionato passando dal 2025-26 al 2026-27:

    livello = media_lega + rho * (grezzo della squadra - media_lega)

`rho_implicito` la ricava dai numeri gia' pubblicati in Fase 6A — non la
ipotizza — e vale 0.808. Con una sola stagione il `rho` **corretto** non e'
stimabile: `alpha` e il test 1o/2o tempo misurano la persistenza *dentro* la
stagione, che e' un'altra cosa e piu' alta per costruzione. Quello che si puo'
fare, e che `sensibilita_rho` fa, e' mostrare quanto si sposta la proiezione
lungo una griglia dichiarata di `rho`.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from . import config, model_team as MT, project_2627 as P, squad_2627 as SQ

# Punti del repository in cui il riferimento esterno entra nei calcoli. E'
# scritto a mano perche' e' un'affermazione sul codice, e un test lo verifica
# rileggendo i file: se qualcuno aggiunge un uso e non lo dichiara qui, il test
# fallisce.
USI_DEL_RIFERIMENTO = (
    ("sot/config.py", "REF_TOPDOWN_PER_MATCH = 4.90",
     "valore fornito dall'utente, non calcolato qui"),
    ("sot/config.py", "REF_TOPDOWN_SEASON = 186 / REF_TOPDOWN_PI80 = (152, 222)",
     "idem, e l'intervallo alimenta le deviazioni standard qui sotto"),
    ("sot/project_2627.py:46", "TOPDOWN_SEASON_SD dall'IC80% del riferimento",
     "l'ampiezza dell'intervallo pubblicato e' ereditata, non stimata"),
    ("sot/project_2627.py:50-51", "TEAM_SHOCK_SD_LOG, LEAGUE_SD_LOG",
     "shock di squadra 65% e livello di campionato 6%: quote assunte"),
    ("sot/project_2627.py:157", "anchor = ratio * REF_TOPDOWN_PER_MATCH",
     "QUI il livello pubblicato viene fissato dal riferimento"),
    ("scripts/run_phase3.py:64-65", "riga 'riferimento dall'alto' del report",
     "citato come riferimento, uso corretto"),
    ("scripts/run_phase5.py:113-114,136-138", "fig6 e tabella del deliverable",
     "citato come riferimento, uso corretto"),
    ("sot/level_chain.py", "default di `livello_usato` in compressione_ratings",
     "e' il livello di cui si misura la de-compressione"),
    ("sot/level_chain.py", "default di `livello_usato` in rho_implicito",
     "da qui si ricava il rho implicito nella proiezione pubblicata (6C)"),
    ("sot/project_2627.py:monte_carlo", "livello_dall_alto=None -> riferimento",
     "il livello resta quello pubblicato finche' non lo si fa variare (6C)"),
    ("scripts/run_phase6a.py", "report di Fase 6A",
     "citato come riferimento, uso corretto"),
    ("scripts/run_phase6c.py", "griglia di rho e figura della sensibilita'",
     "citato come riferimento, uso corretto"),
    ("sot/calendar_2627.py", "livello_implicato = 4.90 x fattore di calendario",
     "misura del limite di calendario (6E): NON applicato alla proiezione"),
    ("sot/calendar_2627.py", "equivalente_in_rho",
     "converte un fattore di calendario nello spostamento di rho equivalente"),
    ("sot/soglie_2627.py", "ancora_pubblicata -> stima_compositiva(4.90, ...)",
     "il LIVELLO dei 38 lambda per partita del blocco S1: la struttura relativa "
     "viene dal modello di squadra, il livello da qui, e la media dei 38 vale "
     "l'ancora a precisione macchina"),
    ("scripts/run_fase11_s1.py", "riga dell'ancora nel report di S1",
     "citato come riferimento, uso corretto"),
)


# --------------------------------------------------------------- scale di campo
def ratings_per_campo(team_match: pd.DataFrame, alpha: float = 12.0) -> pd.DataFrame:
    """Rating di attacco sulle tre scale di campo, per le venti squadre.

    * `neutro` — `exp(mu + attacco + difesa media)`, cioe' il valore **in
      trasferta**: e' la colonna che `fig5` disegna, e il nome storico resta
      per non spostare un numero pubblicato;
    * `casa` — la stessa cosa moltiplicata per il vantaggio del campo;
    * `media_calendario` — la media su 19 partite in casa e 19 in trasferta,
      che e' la scala su cui si leggono i tassi grezzi di stagione.
    """
    m = MT.TeamModel(alpha=alpha).fit(team_match)
    r = m.ratings()
    trasferta = np.exp(m.mu_ + r["attack"] + r["defence"].mean())
    f = float(np.exp(m.home_advantage))
    return r.assign(neutro=trasferta, casa=trasferta * f,
                    media_calendario=trasferta * (1.0 + f) / 2.0)


def fattore_campo(team_match: pd.DataFrame, alpha: float = 12.0) -> float:
    """`exp(gamma)`: quanto la stessa squadra tira in piu' giocando in casa."""
    return float(np.exp(MT.TeamModel(alpha=alpha).fit(team_match).home_advantage))


def _riga(passo, partenza, fattore, risultato, modulo, funzione, natura):
    return {"passo": passo, "valore_partenza": partenza, "fattore": fattore,
            "valore_risultante": risultato, "modulo": modulo,
            "funzione": funzione, "natura": natura}


# ------------------------------------------------------------ ramo del modello
def catena_modello(team_match: pd.DataFrame, squadra: str = "Como",
                   alpha: float = 12.0) -> pd.DataFrame:
    """Dal rating di `fig5` al tasso osservato, un fattore alla volta."""
    rat = ratings_per_campo(team_match, alpha=alpha).set_index("team")
    f = fattore_campo(team_match, alpha=alpha)

    trasferta = float(rat.loc[squadra, "neutro"])
    casa = float(rat.loc[squadra, "casa"])
    calendario = float(rat.loc[squadra, "media_calendario"])
    ctx = P.como_context(team_match, alpha=alpha)
    oss = float(team_match.loc[team_match["team"] == squadra, "sot"].mean())

    return pd.DataFrame([
        _riga(f"rating {squadra} contro difesa media, in trasferta",
              np.nan, np.nan, trasferta,
              "scripts/run_phase5.py", "ratings_neutri -> level_chain.ratings_per_campo",
              "stimato dal modello"),
        _riga("vantaggio del campo, partite in casa",
              trasferta, f, casa,
              "sot/model_team.py", "TeamModel.home_advantage",
              "stimato dal modello"),
        _riga("media di calendario (19 in casa + 19 in trasferta)",
              trasferta, (1.0 + f) / 2.0, calendario,
              "sot/level_chain.py", "ratings_per_campo",
              "aritmetica, esplicitata qui per la prima volta"),
        _riga("calendario reale: avversari effettivi e pesi di decadimento",
              calendario, ctx / calendario, ctx,
              "sot/project_2627.py", "como_context",
              "stimato dal modello"),
        _riga("scarto in campione fra modello e osservato (compressione ridge)",
              ctx, oss / ctx, oss,
              "-", "-",
              "NON e' un fattore applicato: e' il residuo che resta"),
    ])


# ---------------------------------------------------------- ramo pubblicato
def catena_pubblicata(proj: pd.DataFrame, summary: dict, model, r: float,
                      n_sim: int = 20000) -> pd.DataFrame:
    """Da 4.90 al numero del README, un fattore alla volta."""
    rif = config.REF_TOPDOWN_PER_MATCH
    ratio = float(summary["ratio"])
    anchor = ratio * rif
    sim = P.monte_carlo(proj, summary, model, r, n_sim=n_sim)
    mediana = float(np.percentile(sim, 50))
    per_partita = mediana / SQ.N_MATCHES

    return pd.DataFrame([
        _riga("riferimento dall'alto 2026-27", np.nan, np.nan, rif,
              "sot/config.py", "REF_TOPDOWN_PER_MATCH",
              "valore fornito dall'utente, NON calcolato da questi dati"),
        _riga("rapporto compositivo (ricambio di rosa + minuti)",
              rif, ratio, anchor,
              "sot/project_2627.py", "build_projection -> monte_carlo (anchor)",
              "stimato dai dati per giocatore"),
        _riga("convessita' del Monte Carlo (mediana simulata / ancora)",
              anchor, per_partita / anchor, per_partita,
              "sot/project_2627.py", "monte_carlo",
              "artefatto numerico della simulazione, mai documentato prima"),
        _riga("conversione in stagione", per_partita, float(SQ.N_MATCHES), mediana,
              "sot/squad_2627.py", "N_MATCHES",
              "aritmetica"),
    ])


def inflazione_montecarlo(proj: pd.DataFrame, summary: dict, model, r: float,
                          n_sim: int = 20000) -> pd.DataFrame:
    """Il fattore di gonfiamento del Monte Carlo, fonte per fonte.

    Con `sources=()` la simulazione deve restituire **esattamente** l'ancora:
    se non lo fa, c'e' un altro fattore nascosto oltre a quelli qui elencati.
    Ogni fonte accesa da sola dice quanto di quel gonfiamento le spetta. Le
    perturbazioni su `v`, nuovi arrivi e minuti entrano dentro una somma di
    esponenziali e quindi ne alzano il centro (Jensen); gli shock lognormali
    hanno mediana 1 e non dovrebbero spostare la mediana; la NB finale
    arrotonda a interi.
    """
    anchor = float(summary["ratio"]) * config.REF_TOPDOWN_PER_MATCH
    rows = [{"fonte": "nessuna (sources=())",
             "per_partita": float(P.monte_carlo(proj, summary, model, r, n_sim,
                                                sources=()).mean()) / SQ.N_MATCHES}]
    for s in P.SOURCES:
        sim = P.monte_carlo(proj, summary, model, r, n_sim, sources=(s,))
        rows.append({"fonte": s,
                     "per_partita": float(np.percentile(sim, 50)) / SQ.N_MATCHES})
    sim = P.monte_carlo(proj, summary, model, r, n_sim)
    rows.append({"fonte": "TUTTE (il numero pubblicato)",
                 "per_partita": float(np.percentile(sim, 50)) / SQ.N_MATCHES})

    out = pd.DataFrame(rows)
    out["ancora"] = anchor
    out["fattore"] = out["per_partita"] / anchor
    return out


def livello_non_dipende_dal_contesto(proj: pd.DataFrame, summary: dict, model,
                                     r: float, k: float = 1.5,
                                     n_sim: int = 4000) -> dict:
    """Il contesto di squadra si semplifica: prova numerica, non affermazione.

    Si moltiplica per `k` il contesto del Como — come se il modello di squadra
    avesse prodotto un livello completamente diverso — e si rifa' la
    simulazione con lo stesso seed. Se il livello pubblicato dipendesse dal
    modello, cambierebbe; non cambia di un bit.
    """
    s2 = dict(summary)
    for key in ("context_como", "lambda_bottomup_2526", "lambda_bottomup_2627"):
        s2[key] = summary[key] * k
    s2["ratio"] = s2["lambda_bottomup_2627"] / s2["lambda_bottomup_2526"]

    a = P.monte_carlo(proj, summary, model, r, n_sim=n_sim)
    b = P.monte_carlo(proj, s2, model, r, n_sim=n_sim)
    return {"k": k,
            "mediana_originale": float(np.percentile(a, 50)),
            "mediana_contesto_perturbato": float(np.percentile(b, 50)),
            "scarto_massimo": float(np.max(np.abs(a - b)))}


# ------------------------------------------------------------- compressione
def compressione_ratings(team_match: pd.DataFrame, alpha: float = 12.0,
                         livello_usato: float = config.REF_TOPDOWN_PER_MATCH,
                         squadra: str = "Como") -> dict:
    """Quanto la ridge comprime, e se il livello usato e' coerente con quella
    compressione.

    Si regrediscono i venti rating sui tassi grezzi di stagione, riportati
    sulla stessa scala di campo (i grezzi vivono sulla scala di calendario, i
    rating su quella di trasferta: si divide per `(1 + exp(gamma)) / 2`). La
    pendenza e' il fattore di compressione; sotto 1.0 significa che un tiro in
    porta di eccesso grezzo diventa meno di un tiro di eccesso nel rating.

    La de-compressione implicita nel livello usato e' il rapporto fra il suo
    eccesso sulla media di campionato e quello del modello. Se coincide con
    `1 / pendenza`, il livello usato e' esattamente il rating de-compresso; se
    e' minore, il livello usato resta piu' conservativo di quanto la pendenza
    giustifichi; se e' maggiore, va oltre. Tutti e tre gli esiti si pubblicano.
    """
    rat = ratings_per_campo(team_match, alpha=alpha).set_index("team")
    f = fattore_campo(team_match, alpha=alpha)
    scala = (1.0 + f) / 2.0

    grezzo = team_match.groupby("team")["sot"].mean()
    x = (grezzo.loc[rat.index] / scala).to_numpy(dtype=float)   # scala trasferta
    y = rat["neutro"].to_numpy(dtype=float)
    n = len(x)

    X = np.column_stack([np.ones(n), x])
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    resid = y - X @ beta
    s2 = float(resid @ resid) / (n - 2)
    cov = s2 * np.linalg.inv(X.T @ X)
    pendenza, intercetta = float(beta[1]), float(beta[0])
    se_pendenza = float(np.sqrt(cov[1, 1]))
    r2 = 1.0 - float(resid @ resid) / float(((y - y.mean()) ** 2).sum())

    media_lega = float(team_match["sot"].mean()) / scala
    modello = float(rat.loc[squadra, "neutro"])
    grezzo_sq = float(grezzo.loc[squadra]) / scala
    usato = livello_usato / scala

    ecc_modello = modello - media_lega
    return {
        "media_lega_calendario": media_lega * scala,
        "pendenza": pendenza, "se_pendenza": se_pendenza,
        "intercetta": intercetta, "r2": r2, "n": n,
        "fattore_campo": f, "scala_calendario_su_trasferta": scala,
        "media_lega_trasferta": media_lega,
        "modello_trasferta": modello,
        "grezzo_trasferta": grezzo_sq,
        "usato_trasferta": usato,
        "eccesso_modello": ecc_modello,
        "eccesso_grezzo": grezzo_sq - media_lega,
        "eccesso_usato": usato - media_lega,
        "decompressione_implicita": (usato - media_lega) / ecc_modello,
        "decompressione_da_pendenza": 1.0 / pendenza,
        "livello_decompresso_calendario": (media_lega + ecc_modello / pendenza) * scala,
        "livello_modello_calendario": modello * scala,
        "livello_grezzo_calendario": grezzo_sq * scala,
        # Quota dell'eccesso grezzo che il livello usato trattiene: e' `rho`
        # (Fase 6C), ricavato e non ipotizzato. Vedi `rho_implicito`.
        "rho_implicito": (usato - media_lega) / (grezzo_sq - media_lega),
    }


# --------------------------------------------- persistenza fra stagioni (6C)
# Griglia dichiarata in anticipo, come da specifica del blocco: 0.50-0.95 a
# passi di 0.05. Non si sceglie un `rho` "migliore" — non e' stimabile con una
# stagione sola — si mostra come si sposta la proiezione lungo la griglia.
RHO_GRID = tuple(round(0.50 + 0.05 * i, 2) for i in range(10))


def rho_implicito(team_match: pd.DataFrame,
                  livello_usato: float = config.REF_TOPDOWN_PER_MATCH,
                  squadra: str = "Como") -> float:
    """Quota di eccesso sulla media di campionato che il livello usato trattiene.

        livello = media_lega + rho * (grezzo della squadra - media_lega)

    E' la persistenza fra stagioni **implicita** nella proiezione pubblicata,
    ricavata dai numeri della Fase 6A (sezione 4) e non ipotizzata: il livello
    usato eccede la media di campionato di 0.78 tiri sulla scala di trasferta,
    il grezzo 2025-26 di 0.97, e il rapporto e' `rho`. La grandezza e'
    invariante rispetto alla scala di campo — trasferta, casa o calendario —
    perche' le tre scale differiscono per lo stesso fattore moltiplicativo, e
    un test lo verifica.

    Non e' una stima: e' la lettura di che cosa il valore fornito 4.90 sta
    assumendo. Con una stagione sola il `rho` corretto **non e' stimabile**.
    """
    media = float(team_match["sot"].mean())
    grezzo = float(team_match.loc[team_match["team"] == squadra, "sot"].mean())
    return (livello_usato - media) / (grezzo - media)


def livello_da_rho(rho: float, team_match: pd.DataFrame,
                   squadra: str = "Como") -> float:
    """Livello dall'alto implicato da una persistenza `rho`, scala di calendario.

    `rho = 1` significa che la squadra tiene tutto il proprio eccesso della
    stagione scorsa; `rho = 0` che torna alla media di campionato. Il livello
    pubblicato corrisponde a `rho_implicito`, e per costruzione
    `livello_da_rho(rho_implicito(...)) == 4.90`.
    """
    media = float(team_match["sot"].mean())
    grezzo = float(team_match.loc[team_match["team"] == squadra, "sot"].mean())
    return float(media + rho * (grezzo - media))


def sensibilita_rho(proj: pd.DataFrame, summary: dict, model, r: float,
                    team_match: pd.DataFrame, rho_grid=RHO_GRID,
                    squadra: str = "Como", n_sim: int = 20000,
                    con_implicito: bool = True) -> pd.DataFrame:
    """Proiezione stagionale e IC80% per ogni `rho` della griglia.

    Cambia **solo** l'ancora del livello: rapporto compositivo, Monte Carlo,
    seed e fonti di incertezza restano quelli pubblicati. E' l'unico ingresso
    da cui la proiezione si puo' spostare (Fase 6A), quindi la sensibilita' a
    `rho` e' l'intera sensibilita' del livello.

    `con_implicito` aggiunge alla griglia il `rho` gia' implicito nel numero
    pubblicato: e' la riga che deve riprodurre la proiezione pubblicata, ed e'
    il controllo che la parametrizzazione non abbia spostato niente.
    """
    griglia = list(rho_grid)
    if con_implicito:
        griglia = sorted(set(griglia + [rho_implicito(team_match, squadra=squadra)]))

    rows = []
    for rho in griglia:
        liv = livello_da_rho(rho, team_match, squadra=squadra)
        sim = P.monte_carlo(proj, summary, model, r, n_sim=n_sim,
                            livello_dall_alto=liv)
        q10, q50, q90 = np.percentile(sim, [10, 50, 90])
        rows.append({"rho": rho, "livello_dall_alto": liv,
                     "per_partita": q50 / SQ.N_MATCHES, "stagione": q50,
                     "q10": q10, "q90": q90})
    return pd.DataFrame(rows)


def pendenza_su_rho(tab: pd.DataFrame) -> dict:
    """Quanti tiri di stagione si spostano per ogni 0.05 di `rho`.

    Nell'ancora la relazione e' esattamente lineare — il livello entra per
    moltiplicazione — ma la mediana simulata e' un **intero**, quindi la
    regressione sulla griglia ha residui a scalini e un R2 che non arriva a 1.
    E' granularita' della simulazione, non una non-linearita': la pendenza
    esatta sull'ancora si ottiene come `38 x rapporto x convessita' x eccesso`
    e il report di Fase 6C riporta entrambe.
    """
    x = tab["rho"].to_numpy(dtype=float)
    y = tab["stagione"].to_numpy(dtype=float)
    A = np.column_stack([np.ones(len(x)), x])
    beta, *_ = np.linalg.lstsq(A, y, rcond=None)
    resid = y - A @ beta
    r2 = 1.0 - float(resid @ resid) / float(((y - y.mean()) ** 2).sum())
    return {"per_unita": float(beta[1]), "per_005": float(beta[1]) * 0.05,
            "intercetta": float(beta[0]), "r2": r2}
