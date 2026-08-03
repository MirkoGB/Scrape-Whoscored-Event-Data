# -*- coding: utf-8 -*-
"""Lista d'asta provvisoria 2026-27, su listone surrogato.

    ./.venv/Scripts/python.exe scripts/run_asta_2627.py

**Il listone 2026-27 non esiste ancora** — verificato il 2026-08-03, la pagina
della fonte dichiara "Dati non disponibili" — quindi l'universo e' quello della
2025-26 riusato: gli stessi nomi dell'anno scorso. E' un **surrogato
dichiarato**, e i suoi limiti stanno in fondo al report e accanto a ogni numero
che ne discende.

Non tocca la rete.
"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sot import (config, fantapunti as FP, lega as L,  # noqa: E402
                 modello_asta as MA, modificatore as MOD, voti as V)

BERSAGLIO = "2026-2027"
FONTE_LISTONE = config.SEASON          # 2025-2026, l'ultimo listone pubblicato
OUT_MD = config.REPORTS / "asta_2627.md"


def _tab(df: pd.DataFrame) -> str:
    dx = tuple(c for c in df.columns if pd.api.types.is_numeric_dtype(df[c]))

    def cella(v) -> str:
        return "" if pd.isna(v) else str(v).replace("|", r"\|")
    testa = "| " + " | ".join(cella(c) for c in df.columns) + " |"
    sep = "|" + "|".join("---:" if c in dx else "---" for c in df.columns) + "|"
    return "\n".join([testa, sep] + ["| " + " | ".join(cella(v) for v in r) + " |"
                                     for r in df.itertuples(index=False)])


def retrocesse(stagione: str) -> pd.DataFrame:
    """Le ultime tre della classifica, **ricavate dai risultati**, non elencate.

    La Serie B non e' nel repository, quindi le promosse non si possono sapere;
    le retrocesse invece si contano, e contarle e' meglio che scriverle a mano —
    e' la stessa scelta gia' fatta in Fase 6E per il fattore di calendario.
    """
    p = pd.read_parquet(V.PARTITE_PARQUET)
    p = p[p["stagione"] == stagione]
    righe = []
    for _, m in p.iterrows():
        for casa in (True, False):
            gf = m["gol_casa"] if casa else m["gol_trasferta"]
            gs = m["gol_trasferta"] if casa else m["gol_casa"]
            righe.append({"squadra_id": m["casa_id"] if casa else m["trasferta_id"],
                          "squadra": m["casa"] if casa else m["trasferta"],
                          "punti": 3 if gf > gs else (1 if gf == gs else 0),
                          "gf": gf, "gs": gs})
    cl = (pd.DataFrame(righe).groupby(["squadra_id", "squadra"])
          .agg(punti=("punti", "sum"), gf=("gf", "sum"), gs=("gs", "sum"))
          .reset_index())
    cl["dr"] = cl["gf"] - cl["gs"]
    return cl.sort_values(["punti", "dr"]).head(3)


def main() -> int:
    print("previsione su listone surrogato...")
    per_stagione = FP.per_giocatore_stagione()
    listone = MA.listone_surrogato(BERSAGLIO, FONTE_LISTONE)
    prev = MA.previsione(BERSAGLIO, per_stagione, listone)

    giu = retrocesse(FONTE_LISTONE)
    prev["squadra_retrocessa"] = prev["squadra_id"].isin(set(giu["squadra_id"]))

    print("modificatore: simulazione per giornata e per modulo...")
    contributi = MOD.contributo_marginale(prev)
    contributi.to_csv(config.REPORTS / "asta_2627_modificatore.csv", index=False)

    costi = pd.concat([MOD.costo_della_media(prev, n, universo=u)
                       for u in MOD.UNIVERSI
                       for n in sorted(L.LEGA.difensori_schierabili)],
                      ignore_index=True)
    costi.to_csv(config.REPORTS / "asta_2627_costo_della_media.csv", index=False)

    # Il contributo entra nella lista al modulo mediano fra quelli ammessi: e'
    # una scelta di presentazione, e la colonna dice quale — gli altri due
    # restano nel CSV del modificatore, mai schiacciati in una media.
    n_rif = sorted(L.LEGA.difensori_schierabili)[len(L.LEGA.difensori_schierabili) // 2]
    contrib = (contributi[contributi["n_difensori"] == n_rif]
               .set_index("giocatore_id")["contributo_stagione"])
    prev["contributo_modificatore"] = prev["giocatore_id"].map(contrib).fillna(0.0)
    prev["punti_totali"] = (prev["punti_previsti"] + prev["contributo_modificatore"]).round(1)
    # **Nessuna colonna `crediti`.** Convertire punti attesi in crediti d'asta e'
    # un problema di allocazione con budget, non una proporzione (§2.2, seconda
    # conseguenza): una colonna di zeri o una divisione plausibile sarebbero
    # entrambe un segnaposto, che e' cio' che questo progetto non mette.

    lista = prev.sort_values(["ruolo", "punti_totali"], ascending=[True, False])
    colonne = ["ruolo", "giocatore", "giocatore_id", "squadra_sigla",
               "squadra_retrocessa", "presenze_attese", "voto_atteso",
               "punti_previsti", "contributo_modificatore", "punti_totali",
               "qi_anno_prima", "fvm_anno_prima", "senza_storia"]
    lista[colonne].round(2).to_csv(config.REPORTS / "asta_2627_lista.csv", index=False)

    per_ruolo = {}
    for r in ("p", "d", "c", "a"):
        t = lista[lista["ruolo"] == r].head(12)[
            ["giocatore", "squadra_sigla", "squadra_retrocessa", "presenze_attese",
             "voto_atteso", "punti_previsti", "contributo_modificatore",
             "punti_totali", "qi_anno_prima", "fvm_anno_prima"]].round(1)
        # La colonna della retrocessione e' nella tabella e non solo nel CSV:
        # e' l'avvertenza piu' importante di questa lista, e un avviso che sta
        # solo in fondo al documento non e' un'avvertenza.
        t["squadra_retrocessa"] = t["squadra_retrocessa"].map({True: "SI", False: ""})
        per_ruolo[r] = t

    schierabili = costi[costi["universo"] == "schierabili"]
    quotati = costi[costi["universo"] == "tutti i quotati"]

    testo = f"""# Lista d'asta 2026-27 — provvisoria, su listone surrogato

Generato da `scripts/run_asta_2627.py` il {date.today().isoformat()}.
Nessuna richiesta di rete.

## Prima di leggere i numeri

**Il listone 2026-27 non esiste ancora.** Verificato sulla fonte il 2026-08-03:
la pagina c'e' e dichiara "Dati non disponibili" — esce a fine agosto. Questa
lista usa quindi **l'universo della {FONTE_LISTONE}**, cioe' gli stessi nomi
dell'anno scorso, ed e' un surrogato dichiarato. Cosa comporta:

| | |
|---|---|
| **rose** | quelle dell'anno scorso: ogni trasferimento estivo e' ignorato |
| **promosse dalla Serie B** | **mancano del tutto** — tre squadre su venti, ~15% del listone vero |
| **retrocesse** | ci sono ancora, e sono **marcate**, non tolte: {', '.join(giu['squadra'])} |
| **`qi` e `fvm`** | sono dell'anno scorso. Come *ordine* restano informativi, come *prezzo* no |

Sono {len(prev)} giocatori, di cui **{int(prev['squadra_retrocessa'].sum())} di
squadre retrocesse** e **{int(prev['senza_storia'].sum())} senza nessuna storia**
nelle cinque stagioni (per loro il modello restituisce la media del ruolo, ed e'
il massimo che si possa dire).

> **E il modello, ricordiamolo, perde contro il FVM.** Su quattro transizioni di
> stagione la sua correlazione di rango e' 0,45 contro 0,81 del FVM
> (`reports/modello_asta.md`). Questa lista e' utile per *vedere* la forma della
> stima, non per comprarci sopra al posto del listino.

## Il modificatore, e perche' non si calcola sulle medie

`[DECISO 0.3]` **escludi**: un difensore senza voto esce dalla media e la linea
si accorcia.

§2.2 chiede di misurare quanto costi applicare le fasce alla media di stagione
invece di simulare per giornata, e dice che **il segno puo' andare in entrambe le
direzioni**. Va in entrambe, e non e' un modo di dire:

{_tab(costi)}

- Contro una linea di **schierabili** (i migliori {L.LEGA.n_squadre} x N per
  punti attesi, cioe' quello che una lega di {L.LEGA.n_squadre} squadre mette in
  campo) la media di stagione vale {schierabili['media_difensiva_attesa'].iloc[0]:.2f},
  quindi cade nella fascia **+1**; la simulazione da'
  {schierabili['bonus_simulato_per_giornata'].iloc[0]:.2f} per giornata. La
  scorciatoia **sopravvaluta** di ~{abs(schierabili['scarto_di_stagione'].mean()):.0f}
  punti di stagione.
- Contro il **mediano di tutti i quotati** la media attesa e'
  {quotati['media_difensiva_attesa'].iloc[0]:.2f}, cioe' sotto la soglia minima:
  la scorciatoia dice **−1** e la simulazione dice
  {quotati['bonus_simulato_per_giornata'].iloc[0]:.2f}. Qui **sottovaluta** di
  ~{quotati['scarto_di_stagione'].mean():.0f} punti.

Lo stesso errore metodologico, quindi, sbaglia di 20 punti in un verso o di 50
nell'altro **a seconda della linea**. E' esattamente la ragione per cui §2.2
vieta la media di stagione.

> **La linea di riferimento va dichiarata** (§2.2): lo stesso giocatore ha
> contributi diversi rispetto a linee diverse. Qui e' `schierabili`, e la prima
> versione di questo modulo usava `tutti i quotati` — il cui mediano e' un
> panchinaro, con media difensiva attesa sotto 6,00. Ogni contributo misurato
> contro quella linea risultava gonfiato.

Il contributo in lista e' quello a **{n_rif} difensori**; gli altri due moduli
stanno in `reports/asta_2627_modificatore.csv`, mai schiacciati in una media.

## La lista, per ruolo

I punti totali sono `punti_previsti` + `contributo_modificatore`. Per
centrocampisti e attaccanti il contributo e' **zero per costruzione**: il
modificatore riguarda solo portiere e difensori.

### Portieri
{_tab(per_ruolo['p'])}

### Difensori
{_tab(per_ruolo['d'])}

### Centrocampisti
{_tab(per_ruolo['c'])}

### Attaccanti
{_tab(per_ruolo['a'])}

Lista completa in `reports/asta_2627_lista.csv`.

## Limiti, in ordine di quanto pesano

1. **L'universo e' quello sbagliato.** Non e' un difetto del modello: e' che il
   listone vero non esiste. Ogni numero qui va rifatto quando esce, ed e' un
   comando solo (`scrape_quote --season 2026-2027`, poi questo script con il
   listone vero al posto del surrogato).
2. **Il modello perde contro il FVM** (0,45 contro 0,81 di Spearman). La colonna
   `fvm_anno_prima` e' in tabella apposta: se le due liste divergono molto su un
   giocatore, la storia dice che ha ragione il FVM.
3. **Le presenze sono l'80-90% dell'errore.** Con le presenze note il MAE dei
   punti crollerebbe del 91%. Tutto cio' che sposta questa lista in modo
   sostanziale e' informazione sul *minutaggio atteso*, che non e' nei dati.
4. **La simulazione del modificatore assume i membri della linea indipendenti.**
   Una difesa che prende tre gol prende voti bassi *insieme*: la correlazione
   vera e' positiva, quindi la variabilita' della media di linea e'
   sottostimata. Con fasce a scalini il segno dell'effetto sul bonus atteso non
   e' ovvio, e non e' stato corretto a occhio.
5. **Non c'e' nessuna colonna di crediti, ed e' voluto.** Convertire punti attesi
   in prezzo d'asta e' un problema di allocazione con budget, non una
   proporzione — §2.2 dice che la soluzione dell'asta e' un blocco a se'. Una
   divisione plausibile sarebbe stata un segnaposto travestito da risultato.
"""
    OUT_MD.write_text(testo, encoding="utf-8")
    print(f"\n-> {OUT_MD}")
    print(f"-> {config.REPORTS / 'asta_2627_lista.csv'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
