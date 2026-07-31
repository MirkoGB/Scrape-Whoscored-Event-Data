# -*- coding: utf-8 -*-
"""Il calendario 2026-27 non e' quello 2025-26: quale insieme di avversari usa
il codice, e quanto vale il ricambio di tre squadre su venti.

LA DOMANDA
----------
La proiezione parla del Como "contro una difesa media". Ma nel 2026-27 tre
promosse sostituiscono tre retrocesse, e delle promosse **questi dati non
sanno niente**: non hanno giocato in Serie A 2025-26 e non hanno un rating.
Prima di stimare qualunque cosa bisogna sapere che cosa il codice fa oggi.

QUALE INSIEME DI AVVERSARI USA IL CODICE
----------------------------------------
Nel repository esistono **entrambe** le convenzioni, in punti diversi:

* `level_chain.ratings_per_campo` usa **l'avversario medio** — `exp(mu +
  attacco + difesa media)`, la media aritmetica dei venti coefficienti di
  difesa. E' la colonna che `fig5` disegna;
* `project_2627.como_context` usa **l'insieme reale 2025-26** — predice sulle
  38 righe vere del Como, quindi ogni avversario effettivo, in casa e in
  trasferta, con i pesi di decadimento.

**Nessuna delle due entra nel livello pubblicato.** E' il risultato della Fase
6A: dentro `monte_carlo` il contesto di squadra si semplifica, e il livello e'
`4.90 x rapporto compositivo x convessita'`. L'insieme di avversari entra
quindi per una terza via, implicita e mai dichiarata prima: `rho` ancora il
livello al **tasso grezzo del Como 2025-26**, che e' un numero ottenuto contro
l'insieme 2025-26. Il calendario 2026-27 non compare in nessun punto del
codice, e nessun modulo si accorgerebbe se cambiasse.

COME SI MISURA IL RICAMBIO
--------------------------
Il Como affronta 19 avversari, ciascuno una volta in casa e una in trasferta.
Nel modello log-lineare la difesa entra moltiplicativamente, quindi il fattore
di calendario e' un rapporto fra medie di `exp(difesa)`:

    F = [ somma sui 16 che restano + 3 x c_promossa ] / [ somma sui 19 del 25-26 ]

Il termine di campo compare identico a numeratore e denominatore e si
semplifica: `F` non dipende dalla scala di campo, e un test lo verifica.

**Lo status quo non e' "avversario medio", e' "le promosse difendono come le
retrocesse"**: con `c_promossa` uguale alla media delle tre retrocesse `F` vale
esattamente 1. E' questo il punto di riferimento rispetto a cui va letto tutto
il resto — non la media di campionato.

L'INTERVALLO, NON IL PUNTO
--------------------------
`c_promossa` non e' stimabile qui e **non viene stimato**. Si dichiarano in
anticipo due estremi, entrambi calcolati da questi dati ma *scelti* come
estremi:

* **media di campionato** — le promosse difendono come una squadra qualunque
  di Serie A. E' un limite, non uno scenario: storicamente le neopromosse
  stanno sotto la media, quindi questo estremo e' quasi certamente troppo
  favorevole a loro;
* **peggiore difesa 2025-26** — tutte e tre porose come la squadra piu' battuta
  del campionato.

Dentro l'intervallo si riporta anche un riferimento **empirico**: la coorte
promossa nel 2025-26 (`PROMOSSE_2526`), l'unica coorte di neopromosse
osservabile in questo repository. E' **una coorte sola** e la sua identita' e'
informazione esterna, dichiarata qui come lo e' la rosa 2026-27.

Tutto si calcola su due scale affiancate, come vuole la regola dei baseline:
i coefficienti di difesa del modello, che la ridge comprime (pendenza 0.760,
Fase 6A) e che quindi **sottostimano** il ricambio, e i tiri in porta concessi
grezzi, che non sono compressi ma sono piu' rumorosi. La verita' sta fra le
due, e le due si riportano entrambe.

PERCHE' IL NUMERO PUBBLICATO NON VIENE CORRETTO
-----------------------------------------------
Applicare `F` all'ancora sarebbe un doppio conteggio: 4.90 esce da un modello
di persistenza su 21 stagioni, e in 21 stagioni ci sono 21 ricambi di
neopromosse. Quel livello *contiene gia'*, nella propria media storica, un
calendario che cambia tre squadre l'anno. La correzione legittima sarebbe solo
lo scarto fra il trio 2026-27 e un trio tipico — e per caratterizzare un trio
tipico serve piu' di una coorte. Quindi qui si **misura e si dichiara**, non si
corregge: `effetto_su_proiezione` esiste per quantificare il limite, e non e'
chiamata da nessuno script della proiezione.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from . import config, model_team as MT, project_2627 as P, squad_2627 as SQ

# Punti del repository in cui si sceglie un insieme di avversari. E' scritto a
# mano perche' e' un'affermazione sul codice, e un test la verifica rileggendo
# i file: se qualcuno introduce una terza convenzione senza dichiararla qui, il
# test fallisce.
INSIEMI_AVVERSARI = (
    ("sot/level_chain.py", "ratings_per_campo",
     "avversario medio (media dei 20 coefficienti di difesa)",
     "fig5 e phase5_ratings.csv; NON entra nel livello pubblicato"),
    ("sot/project_2627.py", "como_context",
     "insieme reale 2025-26 (le 38 righe vere del Como)",
     "summary['context_como']; si semplifica nel Monte Carlo (Fase 6A)"),
    ("sot/model_team.py", "TeamModel.predict",
     "insieme reale, avversario per avversario",
     "walk-forward within-season; non riguarda il 2026-27"),
    ("sot/level_chain.py", "rho_implicito / livello_da_rho",
     "insieme reale 2025-26, implicito nel tasso grezzo del Como",
     "QUI l'insieme di avversari entra davvero nel livello pubblicato"),
    ("sot/project_2627.py", "monte_carlo",
     "nessuno: l'ancora e' il riferimento esterno 4.90",
     "il calendario 2026-27 non compare in nessun punto del codice"),
)

# Le tre squadre promosse in Serie A per il 2025-26. **Informazione esterna**,
# come la rosa 2026-27: la Serie B non e' in questo repository e la promozione
# non e' deducibile dai dati che ci sono. Serve solo come riferimento empirico
# — l'unica coorte di neopromosse su cui questi dati dicano qualcosa — e non
# come stima: e' una coorte sola.
PROMOSSE_2526 = ("Sassuolo", "Pisa", "Cremonese")

# Scenari dichiarati in anticipo per la difesa delle promosse 2026-27. I primi
# due sono gli estremi dell'intervallo, il terzo lo status quo (F = 1 per
# costruzione), il quarto il riferimento empirico.
SCENARI = (
    ("media di campionato", "estremo: promosse forti come una squadra qualunque"),
    ("peggiore difesa 2025-26", "estremo: tutte e tre porose come la piu' battuta"),
    ("come le retrocesse", "status quo: e' cio' che il codice assume oggi"),
    ("coorte promossa 2025-26", "riferimento empirico, UNA coorte sola"),
)

SCALE = ("modello (exp difesa, compressa dalla ridge)", "grezzo (tiri concessi)")

# --------------------------------------------------------------------------
# Punto 2 del blocco: la congestione infrasettimanale.
# Non e' stimata qui, per una ragione di dati e non di comodo: il Como 2025-26
# non giocava le coppe, quindi in questo campione non esiste una sola partita
# del Como dopo un turno infrasettimanale europeo. Si dichiara come limite, con
# il segno atteso, e si indica dove entrerebbe se un giorno fosse stimata.
# --------------------------------------------------------------------------
LIMITE_CONGESTIONE = {
    "che_cosa": "congestione da impegni infrasettimanali (Champions League)",
    "cosa_e_modellato_oggi": "solo i minuti: ROTATION_DEFAULT 0.15, "
                             "variato 0.05-0.25 nel Monte Carlo",
    "cosa_manca": "l'effetto sul lambda di squadra, che agisce anche a parita' "
                  "di undici schierato (recupero incompleto, gestione del "
                  "ritmo, meno transizioni ad alta intensita')",
    "segno_atteso": -1,
    "lettura": "la proiezione, su questo asse, e' ottimistica",
    "stimabile_da_questi_dati": False,
    "perche_no": "il Como 2025-26 non giocava le coppe: zero partite congestionate",
    "dove_entrerebbe": "un fattore moltiplicativo sull'ancora del livello, "
                       "cioe' lo stesso ingresso di rho (Fase 6A/6C)",
}


# --------------------------------------------------------------- la classifica
def classifica(team_match: pd.DataFrame) -> pd.DataFrame:
    """Classifica finale 2025-26, ricostruita dai gol delle righe partita.

    Serve solo a stabilire **quali** tre squadre retrocedono, che e' un fatto
    dei dati e non un'informazione esterna. I punti si ricavano da `goals` e
    dai gol dell'altra riga della stessa partita; l'ordinamento e' punti,
    differenza reti, gol fatti, come da regolamento (gli spareggi non si
    applicano qui perche' nessuna coppia in zona retrocessione e' a pari punti).
    """
    g = team_match[["matchId", "team", "goals"]].copy()
    g["subiti"] = g.groupby("matchId")["goals"].transform("sum") - g["goals"]
    g["punti"] = np.where(g["goals"] > g["subiti"], 3,
                          np.where(g["goals"] == g["subiti"], 1, 0))
    out = (g.groupby("team")
            .agg(partite=("punti", "size"), punti=("punti", "sum"),
                 gf=("goals", "sum"), gs=("subiti", "sum"))
            .assign(dr=lambda d: d["gf"] - d["gs"])
            .sort_values(["punti", "dr", "gf"], ascending=False))
    out.insert(0, "posizione", np.arange(1, len(out) + 1))
    return out.reset_index()


def retrocesse(team_match: pd.DataFrame, k: int = 3) -> tuple[str, ...]:
    """Le `k` squadre in fondo alla classifica 2025-26."""
    cl = classifica(team_match)
    return tuple(cl.tail(k)["team"])


# ------------------------------------------------------- i livelli difensivi
def livelli_difensivi(team_match: pd.DataFrame, alpha: float = 12.0) -> pd.DataFrame:
    """Quanto ogni squadra concede, sulle due scale affiancate.

    * `modello` — `exp(difesa_j)` del Poisson ridge: e' la grandezza che entra
      davvero nel lambda, ma la ridge la comprime verso 1 (pendenza 0.760 sui
      livelli, Fase 6A), quindi **sottostima** qualunque ricambio di squadre;
    * `grezzo` — tiri in porta concessi per partita, media sulle 38 giornate.
      Non e' compresso, ma e' descrittivo: dentro c'e' anche chi la squadra ha
      affrontato. Nessuna delle due e' la risposta giusta da sola.
    """
    m = MT.TeamModel(alpha=alpha).fit(team_match)
    r = m.ratings().set_index("team")
    grezzo = team_match.groupby("opponent")["sot"].mean()
    return pd.DataFrame({
        "modello": np.exp(r["defence"]),
        "grezzo": grezzo,
    }).sort_values("grezzo")


def fattore_calendario(c: pd.Series, uscite, c_promossa: float,
                       squadra: str = "Como") -> float:
    """Rapporto fra il calendario 2026-27 e quello 2025-26, a parita' d'attacco.

    `c` e' una colonna di `livelli_difensivi`, `uscite` le squadre sostituite,
    `c_promossa` il livello difensivo assunto per **ciascuna** delle promosse.

    Il fattore e' invariante rispetto a una riscalatura di `c` (moltiplicare
    tutte le difese per una costante non lo cambia): e' un rapporto fra somme
    sullo stesso insieme di scala. Da qui segue anche che non dipende dal
    vantaggio del campo, che moltiplica identicamente i due membri.
    """
    uscite = list(uscite)
    avversari = [t for t in c.index if t != squadra]
    if not set(uscite) <= set(avversari):
        raise ValueError("le squadre sostituite devono essere avversarie")
    restano = [t for t in avversari if t not in uscite]
    nuovo = float(c[restano].sum()) + len(uscite) * float(c_promossa)
    return nuovo / float(c[avversari].sum())


def livelli_scenario(c: pd.Series, uscite, promosse_2526=PROMOSSE_2526) -> dict:
    """Il valore di `c_promossa` per ciascuno degli scenari dichiarati."""
    return {
        "media di campionato": float(c.mean()),
        "peggiore difesa 2025-26": float(c.max()),
        "come le retrocesse": float(c[list(uscite)].mean()),
        "coorte promossa 2025-26": float(c[list(promosse_2526)].mean()),
    }


def scenari_promosse(team_match: pd.DataFrame, alpha: float = 12.0,
                     squadra: str = "Como") -> pd.DataFrame:
    """Fattore di calendario e livello implicato, scenario per scenario e scala
    per scala.

    Il livello riportato e' `4.90 x F`: e' la grandezza su cui il fattore
    agirebbe **se** lo si applicasse, non un numero pubblicato. Vedi la
    docstring del modulo per il motivo per cui non lo si applica.
    """
    liv = livelli_difensivi(team_match, alpha=alpha)
    uscite = retrocesse(team_match)
    rows = []
    for scala in ("modello", "grezzo"):
        c = liv[scala]
        valori = livelli_scenario(c, uscite)
        for nome, natura in SCENARI:
            cp = valori[nome]
            f = fattore_calendario(c, uscite, cp, squadra=squadra)
            rows.append({
                "scala": scala, "scenario": nome, "natura": natura,
                "c_promossa": cp,
                "c_medio_avversari_2526": float(
                    c[[t for t in c.index if t != squadra]].mean()),
                "fattore": f,
                "livello_implicato": config.REF_TOPDOWN_PER_MATCH * f,
            })
    return pd.DataFrame(rows)


def equivalente_in_rho(fattore: float, team_match: pd.DataFrame,
                       squadra: str = "Como") -> float:
    """Di quanto andrebbe spostata `rho` per ottenere lo stesso livello.

    Serve a mettere il calendario sulla stessa scala dell'altra assunzione non
    stimabile del progetto: livello e `rho` sono legati da
    `livello = media_lega + rho * eccesso`, quindi uno spostamento
    moltiplicativo del livello equivale a `4.90 * (F - 1) / eccesso` di `rho`.
    """
    media = float(team_match["sot"].mean())
    grezzo = float(team_match.loc[team_match["team"] == squadra, "sot"].mean())
    return config.REF_TOPDOWN_PER_MATCH * (fattore - 1.0) / (grezzo - media)


# ------------------------------------------------- effetto sulla proiezione
def effetto_su_proiezione(proj: pd.DataFrame, summary: dict, model, r: float,
                          tab: pd.DataFrame, n_sim: int = 20000) -> pd.DataFrame:
    """La proiezione stagionale che si otterrebbe applicando ciascun fattore.

    **Non e' la proiezione pubblicata e non la sostituisce**: e' il calcolo che
    quantifica il limite. Cambia solo l'ancora del livello — rapporto
    compositivo, Monte Carlo, seed e fonti restano quelli pubblicati — perche'
    l'ancora e' l'unico ingresso da cui il livello si muove (Fase 6A).
    """
    rows = []
    for _, row in tab.iterrows():
        sim = P.monte_carlo(proj, summary, model, r, n_sim=n_sim,
                            livello_dall_alto=row["livello_implicato"])
        q10, q50, q90 = np.percentile(sim, [10, 50, 90])
        rows.append({**row.to_dict(), "stagione": q50, "q10": q10, "q90": q90,
                     "per_partita": q50 / SQ.N_MATCHES})
    return pd.DataFrame(rows)
