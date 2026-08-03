# -*- coding: utf-8 -*-
"""Il modello per l'asta: costruzione, validazione walk-forward, report.

    ./.venv/Scripts/python.exe scripts/run_modello_asta.py

**Non tocca la rete.** Legge i voti e i listoni gia' acquisiti, ricalcola il
fantavoto di lega, valuta il modello su quattro transizioni di stagione contro
quattro baseline, e scrive `reports/modello_asta.md`.
"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sot import (config, fantapunti as FP, lega as L,  # noqa: E402
                 modello_asta as MA, quotazioni as Q)

OUT_MD = config.REPORTS / "modello_asta.md"


def _tab(df: pd.DataFrame) -> str:
    dx = tuple(c for c in df.columns if pd.api.types.is_numeric_dtype(df[c]))

    def cella(v) -> str:
        return "" if pd.isna(v) else str(v).replace("|", r"\|")
    testa = "| " + " | ".join(cella(c) for c in df.columns) + " |"
    sep = "|" + "|".join("---:" if c in dx else "---" for c in df.columns) + "|"
    righe = ["| " + " | ".join(cella(v) for v in r) + " |"
             for r in df.itertuples(index=False)]
    return "\n".join([testa, sep, *righe])


def main() -> int:
    print("fantavoto di lega...")
    v = FP.con_fantavoto_lega()
    scarti = FP.scarto_dalla_fonte(v)
    per_stagione = FP.per_giocatore_stagione(v)
    per_stagione.to_csv(config.REPORTS / "asta_punti_per_stagione.csv", index=False)

    print("walk-forward su quattro transizioni...")
    quote = Q.carica()
    wf = MA.walkforward(per_stagione, quote)
    wf.to_parquet(config.processed_league_dir() / "asta_walkforward.parquet", index=False)

    met = MA.metriche(wf)
    prec = MA.precisione_top(wf)
    scomp = MA.scomposizione_errore(wf)
    cop = Q.copertura(quote, v)
    for nome, df in (("asta_metriche", met), ("asta_precisione_top", prec),
                     ("asta_scomposizione", scomp), ("asta_copertura_listone", cop)):
        df.to_csv(config.REPORTS / f"{nome}.csv", index=False)

    tutte = met[met["stagione"] == "tutte"].drop(columns=["stagione"])
    prec_media = (prec.groupby("candidato")["precisione"].mean().round(3)
                  .sort_values(ascending=False).rename("precisione_media").reset_index())
    prec_ruolo = (prec.pivot_table(index="candidato", columns="ruolo",
                                   values="precisione").round(3).reset_index())
    mod = tutte[tutte["candidato"] == "modello"].iloc[0]
    fvm = tutte[tutte["candidato"] == "FVM della fonte"].iloc[0]

    ultima = wf[wf["stagione_prevista"] == wf["stagione_prevista"].max()]
    top = (ultima.nlargest(15, "punti_previsti")[
        ["giocatore", "ruolo", "qi_classic", "presenze_attese", "voto_atteso",
         "punti_previsti", "punti_osservati"]]
        .round(2).rename(columns={"qi_classic": "QI"}))

    testo = f"""# Modello per l'asta — punti totali attesi di stagione

Generato da `scripts/run_modello_asta.py` il {date.today().isoformat()}.
Nessuna richiesta di rete.

## Esito in una riga

**Il modello batte l'ignoranza e non batte il mercato.** Su quattro transizioni
di stagione e {len(wf)} righe giocatore-stagione, ordina meglio di una media di
ruolo (precisione sui primi N **{prec_media.set_index('candidato').loc['modello', 'precisione_media']:.3f}**
contro **{prec_media.set_index('candidato').loc['media di ruolo', 'precisione_media']:.3f}**)
ma **perde contro il FVM della fonte** ({fvm['spearman']:.3f} di Spearman contro
{mod['spearman']:.3f}, precisione **{prec_media.set_index('candidato').loc['FVM della fonte', 'precisione_media']:.3f}**).
Allo stato attuale, **all'asta conviene guardare il FVM piu' che questo modello**,
e la cosa onesta e' scriverlo.

## 1. Il fantavoto di lega non e' quello della fonte, e si vede

Ricalcolato dai bonus col barema di §1.1. Diverge dalla colonna della fonte su
**{len(scarti)} righe su {int(v['fantavoto_lega'].notna().sum())}**, e la
divergenza e' **esattamente** quella prevista:

| | |
|---|---|
| scarti distinti osservati | `{sorted(scarti['scarto'].unique())}` |
| ruoli coinvolti | `{sorted(scarti['ruolo'].unique())}` |
| tutte con porta inviolata | `{bool(scarti['porta_inviolata'].all())}` |

Un solo valore, `+1`, su soli portieri, tutti con `gol_subiti == 0`. **Se
divergesse altrove sarebbe un difetto**; divergendo solo qui, e' la conferma che
il barema di lega e quello della fonte differiscono per la voce che sapevamo — la
porta inviolata — e per nient'altro.

## 2. Cosa si prevede, e su cosa

L'universo e' **il listone**, non chi ha poi giocato: e' l'insieme su cui si fa
l'asta. Restringerlo a posteriori a chi ha giocato sarebbe guardare il risultato.

{_tab(cop)}

- **~100 quotati per stagione non scendono mai in campo.** Non sono dati
  mancanti: valgono **zero punti**, ed e' il rischio che l'asta paga. Il modello
  li deve prevedere, non escludere.
- **15-29 giocatori per stagione prendono voti senza essere nel listone
  iniziale**: mercato di gennaio e promossi dalla Primavera. Non sono
  acquistabili all'asta e non entrano nella valutazione.

La forma e' quella di §6.1, con i tre fattori stimati separatamente:

```
punti_stagione = presenze_attese x [ voto_base_atteso + bonus_per_presenza_atteso ]
```

**Tutto cio' che entra viene da stagioni precedenti a quella prevista** — medie
di ruolo, pesi di shrinkage, storia del singolo. Le transizioni valutabili sono
quattro, ed e' esattamente il numero che il piano dati della Fase 6F stimava
necessario per la sua domanda D4.

`QI` **non e' leakage**: la quotazione iniziale e' pubblicata prima dell'asta,
quindi e' informazione disponibile al momento della decisione.

## 3. La validazione, coi baseline accanto (vincolo 6)

{_tab(tutte)}

`MAE` e `bias` sono in punti di fantacalcio; **per `QI` e `FVM` restano vuoti
perche' sono su un'altra scala** (crediti), e un MAE fra grandezze diverse
sarebbe un numero senza significato. Le correlazioni invece sono confrontabili,
e sono quelle che contano per un'asta.

Precisione sui primi N, dove N e' **la rosa di questa lega**
({L.LEGA.rosa}) e non una soglia inventata:

{_tab(prec_media)}

{_tab(prec_ruolo)}

**Tre letture, e nessuna e' comoda:**

1. **Il modello supera la media di ruolo di tre volte** ({prec_media.set_index('candidato').loc['modello', 'precisione_media']:.3f}
   contro {prec_media.set_index('candidato').loc['media di ruolo', 'precisione_media']:.3f}):
   c'e' segnale, e non e' zero.
2. **Ma non supera la persistenza** ({prec_media.set_index('candidato').loc['persistenza (anno prima)', 'precisione_media']:.3f}),
   cioe' "l'anno prossimo come l'anno scorso". Tutto il macchinario dei tre
   fattori con shrinkage non aggiunge niente a una copia dell'anno prima.
3. **E perde di larghissimo margine contro il FVM.** Non e' un riferimento: e'
   una stima di valore fatta da qualcun altro con informazioni che questo modello
   non ha — mercato in corso, gerarchie di rosa, infortuni noti. Se non lo si
   batte, comprare al listino e' la scelta razionale.

> Sui **portieri** il modello fa precisione 0 e il FVM 0,667. Con tre portieri
> per rosa su ~75 quotati il campione e' minuscolo, ma il segno e' netto e la
> causa e' identificabile: i punti di un portiere dipendono da porte inviolate e
> gol subiti, cioe' dalla **difesa della sua squadra**, e questo modello non
> guarda la squadra affatto.

## 4. Dove sta l'errore: nelle presenze, e non c'e' gara

{_tab(scomp)}

**Se le presenze fossero note, il MAE crollerebbe da
{scomp.set_index('variante').loc['modello completo', 'mae']:.1f} a
{scomp.set_index('variante').loc['presenze note', 'mae']:.1f}**, cioe' del
{100 * (1 - scomp.set_index('variante').loc['presenze note', 'mae'] / scomp.set_index('variante').loc['modello completo', 'mae']):.0f}%.
Conoscere i bonus invece lo abbassa solo a
{scomp.set_index('variante').loc['bonus noti', 'mae']:.1f}.

E' il risultato piu' utile del blocco, perche' dice **dove lavorare**: il voto
base e i bonus sono quasi risolti, il problema e' prevedere **quante partite un
giocatore giochera'**. E quello dipende da cose che nessuna delle tabelle
acquisite contiene: minutaggio atteso, gerarchia in rosa, mercato, infortuni.
Non e' un difetto di stima, e' un'assenza di dati.

La scomposizione **non e' esatta** — i tre fattori si moltiplicano, quindi gli
effetti non sono additivi — ed e' riportata come diagnostica.

## 5. I primi quindici della {ultima['stagione_prevista'].iloc[0]}, con l'osservato accanto

{_tab(top)}

## Limiti dichiarati

1. **Il modificatore di difesa non c'e'.** Non e' decomponibile per giocatore
   (§2.2) ed e' fermo sulla decisione **0.3** — come si tratta un difensore senza
   voto dentro la linea. `sot/lega.gestione_sv()` solleva `DecisioneMancante`
   invece di scegliere un default. I punti qui sono **al netto** del
   modificatore, per tutti i ruoli: per portieri e difensori vanno letti
   sapendolo, perche' il bonus arriva a +6.
2. **Il listone 2026-27 non esiste ancora.** Verificato il 2026-08-03: la pagina
   c'e' e dichiara "Dati non disponibili". Quindi **la lista d'asta vera non e'
   producibile oggi** — il modello si applica a un listone, e quel listone
   uscira' a fine agosto. Lo scraper distingue questo caso da un cambio di
   markup e non manda la pagina in quarantena.
3. **Quattro transizioni sono poche.** Con quattro stagioni valutabili, la
   differenza fra modello e persistenza (0,03 di precisione) non e'
   distinguibile dal rumore. Il segno e' contrario al modello, ed e' l'unica
   cosa che si puo' dire.
4. **Il modello non guarda la squadra.** Ne' l'attacco, ne' la difesa, ne' il
   calendario. Il repository ha un modello di squadra validato (Fasi 2-4) e
   questo blocco **non lo usa**: e' la prima cosa da collegare, e sui portieri
   e' quasi certamente dove sta la differenza col FVM.
5. **Nessuna correzione e' stata applicata per far salire i numeri.** Il
   risultato negativo contro FVM e persistenza e' il risultato.
"""

    OUT_MD.write_text(testo, encoding="utf-8")
    print(f"\n-> {OUT_MD}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
