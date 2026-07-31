# -*- coding: utf-8 -*-
"""Piano dati: che cosa servirebbe davvero per chiudere le domande aperte.

**Questo modulo non scarica niente e non deve scaricare niente.** E' un
inventario dichiarato delle domande che le Fasi 6A-6E hanno lasciato aperte,
piu' una simulazione — l'unica cosa calcolata qui — su quanto varrebbe avere i
dati dei sei nuovi arrivi.

IL CRITERIO GUIDA, E PERCHE' NON E' OVVIO
-----------------------------------------
La maggior parte delle domande aperte **non richiede dati evento**. E' il
contrario dell'intuizione di un repository nato come scraper di eventi, ma
segue da come i blocchi 6A-6E hanno localizzato l'incertezza:

* la Fase 6A ha mostrato che il livello pubblicato **non contiene il modello di
  squadra** — il contesto si semplifica dentro `monte_carlo`. Quindi tutto cio'
  che riguarda il livello (`rho`, l'ancora 4.90, la de-compressione) vive su
  totali di squadra per stagione, che sono la granularita' piu' grossolana che
  esista;
* la Fase 6B ha mostrato che l'estimatore in uso e' **compositivo**, cioe' un
  rapporto fra due ricomposizioni. Per validarlo serve un ricambio di rosa
  vero, cioe' minuti e tiri in porta per giocatore su due stagioni
  consecutive — tassi per 90, non eventi;
* la Fase 6E ha bisogno di sapere quanto concedono le neopromosse: di nuovo
  totali di squadra per stagione, su piu' coorti.

Gli eventi grezzi servono **solo** al blocco 6D, perche' possesso, field tilt,
PPDA, tocchi in area e xG interno non esistono come totali pubblicati: vanno
ricalcolati evento per evento. E' anche la domanda con il rapporto peggiore fra
costo dei dati e valore atteso, ed e' l'unica su cui questi dati hanno gia'
dato tre volte lo stesso esito negativo.

LE QUATTRO GRANULARITA'
-----------------------
Sono dichiarate come una scala: ogni livello contiene i precedenti. Il piano
indica per ogni domanda il **minimo** che basta, non il massimo che si
vorrebbe. Chiedere una granularita' piu' fine di quella necessaria e' il modo
piu' comune di rendere irrealizzabile un piano dati.

LA SIMULAZIONE SUI NUOVI ARRIVI
-------------------------------
I sei nuovi arrivi di movimento valgono il 18% dei minuti proiettati e il 13%
del lambda, e oggi entrano con la sola media del proprio ruolo e un prior
gonfiato. La domanda "di quanto si stringerebbe l'intervallo se avessimo un
tasso individuale?" **si risponde adesso, per simulazione**: si sostituisce la
deviazione standard del prior con quella che l'esposizione osservata
implicherebbe, e si rifa' il Monte Carlo.

Due avvertenze, entrambe dentro il calcolo e non in fondo:

1. un tasso preso da un altro campionato **non e' un tasso di Serie A**. Il
   `v_p` del modello e' definito al netto del contesto di squadra, quindi
   trasportarlo costa un'incertezza in piu' che qui non e' stimata ma
   **parametrizzata** (`MULT_TRASFERIMENTO`), con l'estremo superiore scelto in
   modo che il dato individuale non aggiunga nulla. Se la verita' e' li',
   scaricare quei dati non serve, e il calcolo lo dice;
2. i nuovi arrivi pesano l'1.4% della varianza (Fase 3). Il tetto del
   restringimento e' quindi noto in anticipo ed e' piccolo: la simulazione
   serve a **quantificare quanto piccolo**, cioe' a stabilire una priorita', non
   a giustificare la raccolta.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from . import config, model_player as MP, project_2627 as P, squad_2627 as SQ

# --------------------------------------------------------------------------
# Le granularita', come scala dichiarata. `costo` e' un ordinamento, non una
# stima di prezzo: serve solo a rendere confrontabili le righe del piano.
# --------------------------------------------------------------------------
GRANULARITA = (
    ("G1", "totali di squadra per stagione",
     "tiri in porta fatti e concessi, per squadra e per stagione", 1),
    ("G2", "totali di squadra per partita",
     "una riga per squadra-partita: tiri in porta, avversario, casa, data", 2),
    ("G3", "tassi per 90 per giocatore",
     "minuti e tiri in porta per giocatore-stagione, con la squadra", 3),
    ("G4", "eventi grezzi",
     "flusso eventi Opta/WhoScored, l'unico da cui si ricavano possesso, "
     "field tilt, PPDA, tocchi in area e xG interno", 4),
)

# --------------------------------------------------------------------------
# L'inventario delle domande aperte. E' scritto a mano perche' e'
# un'affermazione su che cosa i blocchi precedenti hanno lasciato irrisolto, e
# un test verifica che ogni blocco da 6A a 6E compaia almeno una volta e che
# ogni granularita' citata esista in GRANULARITA.
#
# `ampiezza` e' il minimo, non l'ideale. `sblocca` e' il blocco che il dato
# chiude, non quello che lo ha sollevato.
# --------------------------------------------------------------------------
DOMANDE_APERTE = (
    {
        "id": "D1",
        "domanda": "rho, la persistenza fra stagioni dell'eccesso di una "
                   "squadra sulla media di campionato",
        "perche_aperta": "con una stagione sola non esiste il campione su cui "
                         "stimarla; alpha e il test 1o/2o tempo sono limiti "
                         "superiori, non stime (Fase 6C)",
        "granularita": "G1",
        "ampiezza": "Serie A, 10+ stagioni consecutive (20 squadre x stagione); "
                    "altri campionati solo per verificare che rho non sia "
                    "specifico dell'Italia",
        "sblocca": "6C",
        "impatto": "19 tiri di stagione sulla griglia 0.50-0.95, cioe' 21% "
                   "dell'ampiezza dell'IC80%: la piu' grande assunzione non "
                   "stimabile del progetto",
        "eventi": False,
    },
    {
        "id": "D2",
        "domanda": "l'ancora 4.90 e' ricostruibile? il modello di persistenza "
                   "su 21 stagioni che la produce non esiste nel repository",
        "perche_aperta": "e' un valore fornito, dichiarato con coefficienti "
                         "0.591 e 0.247, e nessun modulo contiene quel calcolo "
                         "(Fase 6A)",
        "granularita": "G1",
        "ampiezza": "le stesse 21 stagioni di Serie A dichiarate dal "
                    "riferimento, per la sola squadra proiettata e per la media "
                    "di campionato",
        "sblocca": "6A",
        "impatto": "il livello pubblicato **e'** questo numero: se e' sbagliato "
                   "lo e' tutta la proiezione, e niente nel repository se ne "
                   "accorgerebbe",
        "eventi": False,
    },
    {
        "id": "D3",
        "domanda": "la de-compressione implicita nel livello usato (x1.109) e' "
                   "della misura giusta? la pendenza della ridge ne "
                   "giustificherebbe x1.316",
        "perche_aperta": "la pendenza 0.760 e' misurata in campione su una "
                         "stagione: dice quanto la ridge comprime, non quanto "
                         "una squadra tirera' l'anno dopo (Fase 6A)",
        "granularita": "G2",
        "ampiezza": "Serie A, 3+ stagioni consecutive: servono le righe partita "
                    "per rifittare la ridge, e almeno una transizione di "
                    "stagione per separare compressione da ritorno alla media",
        "sblocca": "6A",
        "impatto": "0.16 tiri a partita, 6 in stagione, fra livello usato e "
                   "livello de-compresso",
        "eventi": False,
    },
    {
        "id": "D4",
        "domanda": "l'estimatore compositivo (quello pubblicato) aggiunge o "
                   "toglie qualcosa?",
        "perche_aperta": "il test 1o/2o tempo e' quasi vuoto per costruzione: "
                         "MDE 0.0394 contro un intervento medio di 0.0414, e "
                         "fra due meta' di stagione si libera il 3.9% dei "
                         "minuti contro il 16.9% fra due estati (Fase 6B)",
        "granularita": "G3",
        "ampiezza": "2+ stagioni consecutive, tutte e 20 le squadre, minuti e "
                    "tiri in porta per giocatore-stagione piu' i totali di "
                    "squadra per il contesto; con 20 righe per transizione "
                    "servono 4-5 transizioni per uscire dalla zona cieca",
        "sblocca": "6B",
        "impatto": "e' l'unico limite del README che dice che il metodo "
                   "pubblicato non e' mai stato validato",
        "eventi": False,
    },
    {
        "id": "D5",
        "domanda": "quanto concedono le neopromosse, come prior e non come "
                   "coorte singola",
        "perche_aperta": "l'unica coorte osservabile e' quella del 2025-26: "
                         "tre squadre, una stagione, identita' presa da fuori "
                         "(Fase 6E)",
        "granularita": "G1",
        "ampiezza": "Serie A, 10+ stagioni, tiri in porta concessi per squadra "
                    "con l'indicazione di chi era neopromossa: 30+ squadre "
                    "promosse, abbastanza per una media e una dispersione",
        "sblocca": "6E",
        "impatto": "9 tiri di stagione, 0.20 sulla scala di rho: la piu' "
                   "piccola delle assunzioni non stimabili",
        "eventi": False,
    },
    {
        "id": "D6",
        "domanda": "la congestione infrasettimanale abbassa il lambda di "
                   "squadra a parita' di undici schierato?",
        "perche_aperta": "il Como 2025-26 non giocava le coppe: zero partite "
                         "congestionate nel campione, quindi il fattore non e' "
                         "stimabile qui (Fase 6E)",
        "granularita": "G2",
        "ampiezza": "le squadre italiane impegnate in Europa, 3+ stagioni, "
                    "righe partita con **la data**; il calendario europeo serve "
                    "solo per marcare quali partite seguono un turno "
                    "infrasettimanale",
        "sblocca": "6E",
        "impatto": "segno atteso negativo e oggi assente dal modello: su questo "
                   "asse la proiezione e' ottimistica di una quantita' ignota",
        "eventi": False,
    },
    {
        "id": "D7",
        "domanda": "un tasso individuale per i sei nuovi arrivi, al posto della "
                   "sola media di ruolo",
        "perche_aperta": "del loro campionato di provenienza non abbiamo "
                         "niente: valgono il 18% dei minuti proiettati e il 13% "
                         "del lambda su prior di ruolo (Fase 3)",
        "granularita": "G3",
        "ampiezza": "una stagione sola, ma del campionato **giusto** per "
                    "ciascuno, piu' i totali di squadra del loro club per la "
                    "correzione di contesto; il campionato di provenienza non "
                    "e' registrato nel repository",
        "sblocca": "6B",
        "impatto": "quantificato per simulazione in questo blocco: e' il tetto "
                   "dell'1.4% di varianza che i nuovi arrivi pesano oggi",
        "eventi": False,
    },
    {
        "id": "D8",
        "domanda": "i predittori da dati evento pagano dove l'effetto attacco "
                   "e' acerbo?",
        "perche_aperta": "il test acerbo ha potenza 11% e il maturo 28%: "
                         "nessuno dei due e' sensibile, e cio' che conclude e' "
                         "un test in campione, che vale solo come limite "
                         "superiore (Fase 6D)",
        "granularita": "G4",
        "ampiezza": "vedi `righe_per_potenza`: e' l'unica domanda che richiede "
                    "eventi grezzi, e ne richiede molti",
        "sblocca": "6D",
        "impatto": "nessun predittore e' passato in tre regimi; il valore "
                   "atteso di questa raccolta e' il piu' basso di tutte",
        "eventi": True,
    },
)

# --------------------------------------------------------------------------
# I sei nuovi arrivi di movimento. Il campionato di provenienza **non e' nel
# repository**: `squad_2627.NEW_SIGNINGS` registra nome e ruolo e basta, e la
# rosa e' stata ricostruita dal web senza la storia dei trasferimenti. Non lo
# si inventa qui: il piano dice di quale grandezza c'e' bisogno e lascia il
# campionato-stagione come cosa da leggere dal registro trasferimenti.
#
# Quello che serve per ciascuno e' **tre** cose, non una:
#   1. minuti e tiri in porta della sua stagione 2025-26, nel campionato in cui
#      l'ha giocata;
#   2. i totali per partita del suo club in quel campionato, perche' `v_p` e'
#      definito al netto del contesto di squadra: senza, si sovrastima chi
#      arriva da una squadra dominante;
#   3. la media di campionato di quel torneo, per riportare il tasso sulla
#      scala della Serie A.
# La terza e' quella che di solito manca e che introduce l'incertezza di
# trasferimento parametrizzata sotto.
# --------------------------------------------------------------------------
DATI_MINIMI_PER_ARRIVO = (
    "minuti e tiri in porta della stagione 2025-26 nel campionato giocato",
    "totali per partita del club di provenienza, per la correzione di contesto",
    "media di campionato di quel torneo, per riportare il tasso su scala Serie A",
)

# Esposizione (minuti in una stagione) su cui si valuta il guadagno. 0 e' lo
# status quo: nessun dato individuale.
MINUTI_GRID = (0, 450, 900, 1350, 1800, 2400, 3000)

# Incertezza di trasferimento fra campionati, come multiplo della dispersione
# fra giocatori dello stesso ruolo. **Dichiarata, non stimata**: questi dati
# non contengono due campionati, quindi non c'e' modo di misurarla qui.
#   0.0 -> il tasso si trasporta perfettamente (limite inferiore ottimistico);
#   1.0 -> trasportare aggiunge tanto rumore quanto l'intera dispersione fra
#          giocatori, cioe' il dato individuale non serve a niente. E' il
#          limite superiore, ed e' li' apposta: se la verita' e' li', la
#          raccolta e' inutile e il calcolo lo deve poter dire.
MULT_TRASFERIMENTO = (0.0, 0.5, 1.0)


# ------------------------------------------------------------------ granularita'
def tabella_granularita() -> pd.DataFrame:
    return pd.DataFrame(GRANULARITA,
                        columns=["livello", "nome", "contenuto", "costo"])


def tabella_domande() -> pd.DataFrame:
    """Il piano, una riga per domanda, con il nome esteso della granularita'."""
    nomi = {g[0]: g[1] for g in GRANULARITA}
    df = pd.DataFrame(list(DOMANDE_APERTE))
    df["granularita_nome"] = df["granularita"].map(nomi)
    return df


# ------------------------------------------------- errore standard di un tasso
def se_da_esposizione(rate_per90: float, minuti: float, tau: float) -> float:
    """Errore standard di `v_p` che una data esposizione implica.

    Dalla stessa informazione di Fisher penalizzata di `player_effect_se`: per
    la colonna indicatrice di un giocatore la diagonale di `H` vale la somma
    dei lambda attesi sulle sue righe piu' `2*tau`, quindi

        se(v) ~ 1 / sqrt( tiri in porta attesi + 2*tau )

    E' un'approssimazione — trascura la correlazione con gli effetti di ruolo —
    ma su questi dati riproduce `player_effect_se` con uno scarto mediano dello
    0.2%, e un test lo verifica. A esposizione nulla da' `1/sqrt(2*tau)`, cioe'
    il tetto che il modello assegna a chi non ha giocato: **e' il numero da
    confrontare con il prior gonfiato dei nuovi arrivi**, non zero.
    """
    attesi = float(rate_per90) * float(minuti) / 90.0
    return float(1.0 / np.sqrt(attesi + 2.0 * tau))


def sd_prior_nuovi(proj: pd.DataFrame, model: MP.PlayerModel, minuti: float,
                   mult_trasferimento: float, tau: float,
                   sd_popolazione: float | None = None) -> np.ndarray:
    """Deviazione standard del prior di ciascun giocatore proiettato.

    Per i confermati non cambia niente (sono zero: la loro incertezza e' gia'
    `se_v`). Per i nuovi arrivi si compone in quadratura l'errore standard che
    l'esposizione implicherebbe con l'incertezza di trasferimento fra
    campionati, che e' **parametrizzata e non stimata**.

    Con `minuti = 0` e `mult_trasferimento` qualunque non si torna esattamente
    al valore pubblicato: il prior pubblicato e' `1.5 x` la dispersione fra
    giocatori (0.365), il tetto del modello a esposizione nulla e' `1/sqrt(2
    tau)` (0.408). Sono due numeri diversi e la differenza va vista, non
    nascosta — il prior "gonfiato" e' in realta' **piu' stretto** di quello che
    il modello darebbe a un giocatore senza dati.
    """
    eff = model.player_effects()["v"].to_numpy()
    if sd_popolazione is None:
        sd_popolazione = float(np.std(eff[np.abs(eff) > 1e-9]))

    rate = model.rate_per90(proj)
    se = np.array([se_da_esposizione(rt, minuti, tau) for rt in rate])
    sd_tr = float(mult_trasferimento) * sd_popolazione
    sd = np.sqrt(se ** 2 + sd_tr ** 2)
    return np.where(proj["is_new"].to_numpy(), sd, 0.0)


# --------------------------------------------------- quanto si stringerebbe
def peso_nuovi_arrivi(proj: pd.DataFrame) -> dict:
    """Quanto pesano i sei nuovi arrivi, in minuti e in lambda."""
    is_new = proj["is_new"].to_numpy()
    return {
        "n_nuovi": int(is_new.sum()),
        "quota_minuti": float(proj.loc[is_new, "minutes_proj"].sum()
                              / proj["minutes_proj"].sum()),
        "quota_lambda": float(proj.loc[is_new, "contributo"].sum()
                              / proj["contributo"].sum()),
    }


def stringimento_intervallo(proj: pd.DataFrame, summary: dict,
                            model: MP.PlayerModel, r: float, tau: float,
                            minuti_grid=MINUTI_GRID,
                            mult_grid=MULT_TRASFERIMENTO,
                            n_sim: int = 20000) -> pd.DataFrame:
    """Di quanto si stringe l'IC80% sostituendo il prior di ruolo con un tasso.

    Cambia **solo** la deviazione standard del prior dei nuovi arrivi: ancora
    del livello, rapporto compositivo, seed, fonti e numero di simulazioni
    restano quelli pubblicati. La riga di riferimento e' quella pubblicata
    (`sd_nuovi=None`), e compare in tabella come `stato = pubblicato`.

    Si riportano tre colonne e non una: `ampiezza` dell'IC80%, `sd_stagione` e
    `stagione` mediana.

    * **`ampiezza` e' quantizzata**. Il totale stagionale simulato e' un intero
      (binomiale negativa), quindi i suoi percentili si muovono a scalini da 1
      e un effetto piu' piccolo di un tiro non e' leggibile li' dentro. E' la
      colonna che il README pubblica, quindi va riportata — ma non e' quella su
      cui leggere il guadagno.
    * **`sd_stagione` e' continua** ed e' la colonna da leggere: misura la
      stessa cosa senza lo scalino.
    * il dato individuale non stringe soltanto — **sposta anche il centro**,
      perche' il prior entra in una somma di esponenziali e la sua varianza ne
      alza la mediana (Jensen, +0.65% misurato in Fase 6A). Ridurre il prior
      toglie quel gonfiamento, e su questa proiezione lo spostamento del centro
      e' dello stesso ordine del restringimento.
    """
    sim0 = P.monte_carlo(proj, summary, model, r, n_sim=n_sim)
    q10, q50, q90 = np.percentile(sim0, [10, 50, 90])
    amp0, sd0 = q90 - q10, float(sim0.std())
    rows = [{"stato": "pubblicato", "minuti": np.nan, "mult_trasferimento": np.nan,
             "sd_media_nuovi": np.nan, "stagione": q50, "q10": q10, "q90": q90,
             "ampiezza": amp0, "d_ampiezza": 0.0, "sd_stagione": sd0,
             "riduzione_sd": 0.0, "d_stagione": 0.0}]

    for mult in mult_grid:
        for minuti in minuti_grid:
            sd = sd_prior_nuovi(proj, model, minuti, mult, tau)
            sim = P.monte_carlo(proj, summary, model, r, n_sim=n_sim, sd_nuovi=sd)
            a, b, c = np.percentile(sim, [10, 50, 90])
            rows.append({
                "stato": "con dati individuali",
                "minuti": float(minuti),
                "mult_trasferimento": float(mult),
                "sd_media_nuovi": float(sd[sd > 0].mean()),
                "stagione": b, "q10": a, "q90": c,
                "ampiezza": c - a,
                "d_ampiezza": (c - a) - amp0,
                "sd_stagione": float(sim.std()),
                "riduzione_sd": (sd0 - float(sim.std())) / sd0,
                "d_stagione": b - q50,
            })
    return pd.DataFrame(rows)


def varianza_nuovi_arrivi(proj: pd.DataFrame, summary: dict,
                          model: MP.PlayerModel, r: float, tau: float,
                          minuti_grid=MINUTI_GRID,
                          mult_grid=MULT_TRASFERIMENTO,
                          n_sim: int = 20000) -> pd.DataFrame:
    """La sola fonte `new_signings`, accesa da sola, lungo la stessa griglia.

    Isola l'effetto che `stringimento_intervallo` misura diluito nel totale: la
    quota di varianza dei nuovi arrivi e' l'1.4% (Fase 3), quindi sul totale il
    guadagno e' per forza piccolo. Qui si vede quanto vale **la fonte**, che e'
    la grandezza da citare per decidere se la raccolta ha senso.
    """
    tot = float(P.monte_carlo(proj, summary, model, r, n_sim=n_sim).var())
    v0 = float(P.monte_carlo(proj, summary, model, r, n_sim=n_sim,
                             sources=("new_signings",)).var())
    rows = [{"stato": "pubblicato", "minuti": np.nan, "mult_trasferimento": np.nan,
             "varianza_fonte": v0, "quota_sul_totale": v0 / tot, "riduzione_fonte": 0.0}]
    for mult in mult_grid:
        for minuti in minuti_grid:
            sd = sd_prior_nuovi(proj, model, minuti, mult, tau)
            v = float(P.monte_carlo(proj, summary, model, r, n_sim=n_sim,
                                    sources=("new_signings",), sd_nuovi=sd).var())
            rows.append({"stato": "con dati individuali", "minuti": float(minuti),
                         "mult_trasferimento": float(mult), "varianza_fonte": v,
                         "quota_sul_totale": v / tot,
                         "riduzione_fonte": (v0 - v) / v0 if v0 > 0 else np.nan})
    return pd.DataFrame(rows)


def dettaglio_arrivi(proj: pd.DataFrame, model: MP.PlayerModel, tau: float,
                     minuti: float = 1800.0) -> pd.DataFrame:
    """Una riga per nuovo arrivo: peso proiettato e `se` a una data esposizione.

    `minuti` e' l'esposizione di riferimento su cui si legge il guadagno per
    giocatore; il campionato-stagione da cui prenderla non e' nel repository ed
    e' dichiarato come tale nella colonna `campionato_provenienza`.
    """
    out = proj[proj["is_new"]].copy()
    rate = model.rate_per90(out)
    out["rate_per90_prior_ruolo"] = rate
    out["se_oggi_tetto_modello"] = se_da_esposizione(0.0, 0.0, tau)
    out["se_con_dati"] = [se_da_esposizione(rt, minuti, tau) for rt in rate]
    out["sot_attesi_nel_dato"] = rate * minuti / 90.0
    out["quota_lambda"] = out["contributo"] / float(proj["contributo"].sum())
    out["campionato_provenienza"] = "non registrato nel repository"
    return out[["name", "role", "minutes_proj", "quota_lambda",
                "rate_per90_prior_ruolo", "sot_attesi_nel_dato",
                "se_oggi_tetto_modello", "se_con_dati",
                "campionato_provenienza"]].reset_index(drop=True)


# ------------------------------------------------------- quanti eventi per 6D
def righe_per_potenza(se_per_riga: float, n_righe: int, effetto: float,
                      potenza: float = 0.80, soglia: float = 2.0) -> dict:
    """Quante righe servirebbero al test dei predittori per avere potenza.

    Inverte il calcolo della Fase 6D. Li' `se_per_riga` e' gia' l'errore
    standard dell'effetto **medio per riga** su `n_righe` — si riconosce dal
    fatto che `mde_per_riga = (soglia + z) * se_per_riga` — quindi il `t` del
    test contro un effetto per riga vale `effetto / se_per_riga`, senza altri
    fattori. Serve

        t_atteso = soglia + z_potenza

    e siccome `se` scala come `1/sqrt(n)`, le righe crescono col quadrato del
    rapporto fra il `t` che serve e quello che si ha.

    Controllo interno: nel regime maturo il `t` cosi' ricostruito vale 1.419
    contro l'1.420 che la Fase 6D riporta come statistica osservata di
    `poss_att`. Se un giorno divergesse, uno dei due conti sarebbe sbagliato.

    **Assume che la variabilita' per riga resti quella misurata**, che e'
    esattamente cio' che la Fase 6D ha trovato non vero fra regimi (nel regime
    acerbo la variabilita' per riga e' piu' piccola). Vale quindi come ordine
    di grandezza, ed e' cosi' che va citata.
    """
    from scipy import stats

    z = float(stats.norm.ppf(potenza))
    t_ora = float(effetto) / float(se_per_riga)
    fattore = ((soglia + z) / t_ora) ** 2
    return {"t_atteso_ora": t_ora, "n_righe_ora": int(n_righe),
            "fattore": float(fattore), "n_righe_servite": float(n_righe * fattore),
            "potenza": potenza, "soglia": soglia}


def stagioni_campionato_per_6d(n_righe_servite: float, righe_per_stagione: int) -> float:
    """Da righe a stagioni-campionato, che e' l'unita' in cui si scaricano dati."""
    return float(n_righe_servite) / float(righe_per_stagione)


# Predittore su cui si legge l'alternativa: e' quello che ha prodotto l'effetto
# per riga piu' grande fra gli otto candidati, cioe' la stessa alternativa
# dichiarata dalla Fase 6D. Non si sceglie qui un'alternativa nuova.
PREDITTORE_ALTERNATIVA = "poss_att"


def piano_6d(pred: pd.DataFrame, predittore: str = PREDITTORE_ALTERNATIVA,
             potenza: float = 0.80) -> pd.DataFrame:
    """Quante stagioni-campionato di **eventi grezzi** servirebbero al blocco 6D.

    Legge `reports/phase6_predittori.csv` invece di rifare i nove walk-forward:
    questo blocco e' un piano, non un ricalcolo, e usare gli stessi numeri gia'
    pubblicati e' anche l'unico modo perche' il piano descriva il test che e'
    stato davvero fatto.

    `n` nella tabella di Fase 6D e' il numero di righe che **una** stagione di
    Serie A produce in quel regime (660 mature, 100 acerbe, 40 disgiunte),
    quindi il rapporto fra righe servite e `n` e' direttamente in
    stagioni-campionato. Possono essere campionati diversi nello stesso anno:
    la moltiplicazione non deve per forza venire dagli anni.
    """
    sub = pred[pred["predittore"] == predittore]
    if sub.empty:
        raise ValueError(f"{predittore} assente dalla tabella di Fase 6D")
    effetto = float(sub.loc[sub["regime"] == "maturo", "d_riga"].iloc[0])

    rows = []
    for _, row in sub.iterrows():
        p = righe_per_potenza(float(row["se_riga"]), int(row["n"]), effetto,
                              potenza=potenza)
        rows.append({
            "regime": row["regime"],
            "righe_per_stagione": int(row["n"]),
            "t_ora": p["t_atteso_ora"],
            "potenza_ora": potenza_da_t(p["t_atteso_ora"]),
            "righe_servite": p["n_righe_servite"],
            "stagioni_campionato": stagioni_campionato_per_6d(
                p["n_righe_servite"], int(row["n"])),
        })
    return pd.DataFrame(rows)


def potenza_da_t(t: float, soglia: float = 2.0) -> float:
    """Potenza di un test a una coda con soglia `soglia` contro un `t` atteso."""
    from scipy import stats

    return float(stats.norm.sf(soglia - float(t)))
