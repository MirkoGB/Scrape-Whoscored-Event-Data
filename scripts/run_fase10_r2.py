# -*- coding: utf-8 -*-
"""Fase 10 / Blocco R2 — 1X2 e over/under, valutati.

    ./.venv/Scripts/python.exe scripts/run_fase10_r2.py

**Non tocca la rete e non scrive niente sotto `data/`.** Legge il perimetro di R0
e la congiunta di R1, e misura. **Non stima nessun parametro nuovo**: `rho = 0`
arriva da R1, i lambda da E3.1.

**Vincolo 3**: nessuna valutazione di scommessa, nessuna quota. Si misura quanto
la previsione e' buona, non quanto varrebbe puntarci.

~1 min.
"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sot import config, esiti as E, perimetro as PM  # noqa: E402

OUT_MD = config.REPORTS / "fase10_r2_esiti.md"


def _tab(df: pd.DataFrame, dec: dict[str, int] | None = None) -> str:
    dec = dec or {}
    num = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]

    def cella(c, v) -> str:
        if isinstance(v, (bool, np.bool_)):
            return "si" if v else "no"
        if pd.isna(v):
            return ""
        if c in dec:
            return f"{v:.{dec[c]}f}"
        if c in num and float(v) == int(v):
            return str(int(v))
        if c in num:
            return f"{v:.4f}"
        return str(v).replace("|", r"\|")

    testa = "| " + " | ".join(str(c) for c in df.columns) + " |"
    sep = "|" + "|".join("---:" if c in num else "---" for c in df.columns) + "|"
    righe = ["| " + " | ".join(cella(c, v) for c, v in zip(df.columns, r)) + " |"
             for r in df.itertuples(index=False)]
    return "\n".join([testa, sep, *righe])


def main() -> int:
    print("Fase 10 / R2 — esiti\n" + "=" * 60)

    pv = E.previsioni()
    val = E.valutazione(pv)
    pav = E.righe_pavimentate()
    seg = E.per_segmento(pv)
    disp = E.dispersione_somma()
    _dz = disp.set_index('candidato')['sd']
    corr_mod = float(disp.set_index('candidato').loc['modello', 'corr con il totale vero'])
    sd_mod = float(_dz['modello']); sd_camp = float(_dz['media campionato'])
    sd_squadra = float(_dz['media squadra'])

    app = {m: E.confronto_appaiato(pv, m)
           for m in ("RPS", "log-loss", "Brier O1.5", "Brier O2.5", "Brier O3.5")}

    cal = pd.DataFrame([E.pendenza_calibrazione(pv, c, cl)
                        for c in ("modello", "media squadra + campo",
                                  "media campionato")
                        for cl in E.CLASSI])
    aff = E.calibrazione(pv)

    m_rps = float(val.loc[val.candidato == "modello", "RPS"].iloc[0])
    best_b = val[val.candidato != "modello"].sort_values("RPS").iloc[0]
    a_rps = app["RPS"].set_index("baseline")
    a_o25 = app["Brier O2.5"].set_index("baseline")

    print(f"\nRPS modello {m_rps:.4f} | miglior baseline "
          f"{best_b['candidato']} {best_b['RPS']:.4f}")
    print(f"  t appaiato vs quel baseline: "
          f"{a_rps.loc[best_b['candidato'], 't']:+.2f} "
          f"(oltre il rumore: {a_rps.loc[best_b['candidato'], 'oltre il rumore']})")
    print(f"\nO2.5: modello {val.loc[val.candidato=='modello','Brier O2.5'].iloc[0]:.4f}"
          f" | media campionato {val.loc[val.candidato=='media campionato','Brier O2.5'].iloc[0]:.4f}")
    print(f"  t vs media campionato: {a_o25.loc['media campionato','t']:+.2f}")
    print(f"  t vs media squadra + campo: {a_o25.loc['media squadra + campo','t']:+.2f}")

    tab_val = _tab(val)
    tab_pav = _tab(pav)
    tab_seg = _tab(seg)
    tab_disp = _tab(disp, dec={"media": 3, "sd": 3, "corr con il totale vero": 4})
    tab_cal = _tab(cal, dec={"pendenza": 3, "errore standard": 3, "z vs 1.0": 2})
    tab_aff = _tab(aff, dec={"dichiarata": 3, "osservata": 3})
    tab_app = {m: _tab(a, dec={"differenza": 5, "errore standard": 5,
                               "t": 2, "MDE (80%)": 5})
               for m, a in app.items()}

    dist = pd.DataFrame({
        "esito": list(E.CLASSI),
        "osservata": [float((pv["esito"] == c).mean()) for c in E.CLASSI],
        "modello (media)": [float(pv[f"modello|p{c}"].mean()) for c in E.CLASSI],
    })
    tab_dist = _tab(dist, dec={"osservata": 4, "modello (media)": 4})

    testo = f"""# Fase 10 / Blocco R2 — 1X2 e over/under, valutati

> Generato da `scripts/run_fase10_r2.py` il {date.today().isoformat()}.
> **Nessuna richiesta di rete. Nessun parametro nuovo**: `rho = 0` arriva da R1,
> i lambda da E3.1. Questo blocco misura.

---

## 0. Due decisioni ereditate, dichiarate qui

1. **Il burn-in NON e' stato allineato alla giornata.** R0 aveva trovato due
   partite con un lato solo eligible (Inter-Atalanta e Sassuolo-Salernitana,
   2021-22) e lasciato aperta la scelta. `[DECISO 2026-08-08]` dall'utente:
   **restano fuori**. Due partite su {len(pv)} non giustificano il rischio di
   spostare una definizione che E3 ha gia' pubblicato.
2. **`rho = 0`**, dall'esito misurato di R1 e non come default comodo: MLE
   −0,0087 con potenza dell'80% a 0,09.

> **Vincolo 3, e non e' aggirabile.** Qui non si valuta nessuna scommessa. Non
> ci sono quote di mercato nel repository, e le uniche ottenibili sarebbero
> generate da questo stesso modello: confrontarcisi e' circolare, ed e' il codice
> che sta in `legacy/`. Si misura **quanto la previsione e' buona**, non quanto
> varrebbe puntarci. Un test vieta che una quota compaia in `sot/esiti.py`.

---

## 1. Come si misura, e perche' cosi'

**La metrica principale e' l'RPS, non la log-loss.** L'esito 1X2 e' **ordinale**:
fra `1` e `2` c'e' `X`, e sbagliare dando probabilita' al pareggio e' un errore
piu' piccolo che darla alla vittoria opposta. La log-loss tratta le tre classi
come etichette scambiabili e non lo sa; sta accanto, non al posto.

**Il confronto e' a composizione fissata** (vincolo 6): ogni baseline e' una
coppia di lambda e viene composta con la **stessa** `risultato.congiunta` del
modello. Se il modello passasse per la congiunta e i baseline per una regola
diversa, si misurerebbe la composizione invece del lambda.

**Il pavimento sui lambda e' dichiarato** (`PAVIMENTO_LAMBDA` = {E.PAVIMENTO_LAMBDA}).
Un lambda esattamente zero e' un estimatore **degenere**: su una riga del
campione `media squadra` lo produce **mentre quella squadra segna davvero**, e
senza pavimento la log-loss di quel baseline sarebbe infinita — un artefatto, non
un risultato. E' lo stesso caso della frequenza storica grezza di E3 e si tratta
allo stesso modo: si smorza, si dichiara, si conta quante righe tocca.

{tab_pav}

**Un difetto trovato e corretto prima di pubblicare**: il tasso base dell'over
era stimato sull'**intero campione** mentre quello 1X2 era gia' walk-forward.
Dava a ogni partita la conoscenza di quanti gol si sarebbero segnati nel resto
della stagione — vincolo 1. Ora entrambi usano il solo passato, con la stessa
soglia di 30 partite del walk-forward di E3.

---

## 2. Il quadro completo

{tab_val}

Su **tutte** le metriche piu' basso e' meglio.

---

## 3. Su 1X2 il modello batte l'ignoranza, non batte la forza di squadra

{tab_app['RPS']}

- Contro i tre candidati non informativi il margine e' **enorme e ben oltre il
  rumore**: t fra −10,4 e −10,9.
- Contro **`media squadra + campo`** — «quanti gol fa in media questa squadra, e
  gioca in casa?» — il margine vale **t = {a_rps.loc['media squadra + campo', 't']:+.2f}**,
  con una differenza di {a_rps.loc['media squadra + campo', 'differenza']:.5f}
  contro un MDE di {a_rps.loc['media squadra + campo', 'MDE (80%)']:.5f}:
  **dentro il rumore.**

**E' esattamente la forma che le Fasi 2 e 4 avevano trovato sui tiri in porta**
(t = 1,86 sullo stesso confronto), e va detto perche' e' un contrasto con E3: li'
il modello dei gol batteva il baseline migliore per **t = 5,52**. **Il vantaggio
misurato sui gol non sopravvive alla proiezione su 1X2**, e le cause sono due e
si sommano: le righe passano da 3.278 a {len(pv):,} (una partita, non due
squadre-partita), e l'esito a tre classi **butta via** informazione che i gol
avevano — 3-0 e 1-0 sono lo stesso `1`.

La log-loss dice la stessa cosa con numeri diversi
(t = {app['log-loss'].set_index('baseline').loc['media squadra + campo', 't']:+.2f}
contro lo stesso baseline), il che e' un controllo: se le due metriche avessero
dato verdetti opposti, ci sarebbe da spiegare quale delle due si stava leggendo.

---

## 4. Su over/under l'ordine si ROVESCIA, ed e' il risultato non previsto

{tab_app['Brier O2.5']}

**Sui gol totali il modello perde contro la media di campionato**
(t = {a_o25.loc['media campionato', 't']:+.2f}, sotto il proprio MDE quindi non
distinguibile) **e batte nettamente i baseline di squadra**
(t = {a_o25.loc['media squadra + campo', 't']:+.2f}, ben oltre il rumore). Sul
1X2 valeva l'opposto: li' i baseline di squadra erano forti e la media di
campionato inutile.

**Il meccanismo e' misurato, non addotto.** Un esito 1X2 dipende dalla
**differenza** fra i due lambda — chi e' piu' forte — mentre un over/under
dipende dalla loro **somma**. Ecco come i candidati trattano la somma:

{tab_disp}

**Il fatto centrale non e' la dispersione di un candidato: e' che il totale di
gol di una partita e' quasi imprevedibile per tutti.** La correlazione migliore
fra somma prevista e totale vero e' {corr_mod:.3f}, ed e' del modello. Con un
legame cosi' debole, ogni unita' di dispersione in piu' e' quasi tutta varianza
pagata a vuoto, e su una metrica quadratica **vince chi ne mette meno**: la media
di campionato disperde {sd_camp:.3f}, il modello {sd_mod:.3f}, le medie di
squadra {sd_squadra:.3f}. L'ordine del Brier e' esattamente quello, al contrario.

> Questa sezione affermava che «due medie di squadra sommate danno un totale piu'
> disperso del vero». **La misura l'ha corretta**: la dispersione delle medie di
> squadra (0,691) e' ben *sotto* quella del totale osservato (1,569), e il
> problema non e' disperdere troppo in assoluto — e' disperdere senza
> correlazione. `dispersione_somma()` esiste perche' quella frase era
> un'affermazione e non un numero.

**Il modello e' l'unico candidato decente su entrambe le domande**, e questo —
non l'accuratezza su una metrica sola — e' l'argomento con cui si giustifica.

E' la stessa forma dell'argomento della Fase 4, dove il modello si giustificava
per la **calibrazione** e non per l'accuratezza: la virtu' non e' essere il
migliore da qualche parte, e' non essere pessimo da nessuna.

Le altre due linee dicono lo stesso (O1.5:
t = {app['Brier O1.5'].set_index('baseline').loc['media campionato', 't']:+.2f} contro la
media di campionato; O3.5:
t = {app['Brier O3.5'].set_index('baseline').loc['media campionato', 't']:+.2f}).

---

## 5. La calibrazione, e qui il segno e' OPPOSTO a quello della Fase 4

{tab_cal}

- **Il modello e' sotto-sicuro**: pendenza {cal.loc[0, 'pendenza']:.3f} sulla classe `1`
  (z = {cal.loc[0, 'z vs 1.0']:+.2f}) e {cal.loc[2, 'pendenza']:.3f} sulla `2`
  (z = {cal.loc[2, 'z vs 1.0']:+.2f}), cioe' **sopra 1.0**: le sue probabilita'
  sono troppo vicine al centro e andrebbero allargate.
- **`media squadra + campo` e' meglio calibrato del modello**
  ({cal.loc[3, 'pendenza']:.3f}, z = {cal.loc[3, 'z vs 1.0']:+.2f}).
- **`media campionato` non e' identificata** (errori standard sopra 0,8): e'
  esattamente cio' che la Fase 4 aveva trovato, e per la stessa ragione — il suo
  logit e' quasi costante.

**Nella Fase 4 i baseline informativi erano sotto 1.0** (troppo estremi, perche'
una media campionaria non regredisce) **e il modello era l'unico compatibile con
1.0**. Qui il modello sta dall'altra parte. La spiegazione compatibile e' la
**compressione della ridge** che la Fase 6A ha quantificato (pendenza 0,760 dei
rating sui grezzi): lo shrinkage che sui tiri correggeva l'eccesso, sui gol
proiettati su 1X2 **corregge troppo**. Non e' stato aggiustato — sarebbe far
tornare un numero cambiando la definizione (vincolo 2) — ed e' dichiarato qui
accanto alla metrica, non in fondo.

Affidabilita' del modello sulla classe `1`, fascia per fascia:

{tab_aff}

Le due fasce estreme hanno n = 1 e n = 8 e **non vanno lette**: sono riportate
per non selezionare le fasce comode.

---

## 6. Per segmento

{tab_seg}

Il modello vince nelle partite **medie** e nella **seconda meta'** di stagione,
e perde di pochissimo nelle **equilibrate** e nella prima meta'. Tutte le
differenze sono molto sotto l'MDE del confronto complessivo: la tabella serve a
mostrare che il vantaggio non e' concentrato in un angolo, non a concludere
qualcosa su ciascun segmento.

Le **squilibrate** meritano una riga in piu' perche' sono il punto in cui R1 ha
dichiarato l'assunzione piu' fragile (`rho` costante fra partite, domanda aperta
3): li' il modello sta {seg.loc[seg.segmento == 'squilibrate', 'differenza'].iloc[0]:+.5f}
contro il baseline, cioe' non peggio che altrove. **Non e' una verifica di quella
domanda** — servirebbe stimare `rho` per fascia di squilibrio — ma se l'assunzione
facesse danno, questo e' il segmento in cui si vedrebbe per primo.

---

## 7. Distribuzione degli esiti

{tab_dist}

Media in campione delle probabilita' dichiarate contro la frequenza osservata.
**Non e' una metrica di accuratezza** e non va citata come tale: serve a mostrare
che la composizione non e' sbilanciata su una classe.

---

## 8. Domande aperte

1. **La sotto-sicurezza del modello su 1X2 non e' stata corretta e non e' stata
   spiegata fino in fondo.** Il legame con la compressione della ridge (Fase 6A)
   e' compatibile ma non e' stato misurato: servirebbe rifare la composizione con
   i lambda de-compressi e vedere se la pendenza va a 1.0. E' un blocco a se',
   e **non va fatto ritoccando lo shrinkage finche' il numero torna gradevole**.
2. **Il confronto con `media squadra + campo` non e' concluso, e' senza potenza.**
   L'MDE su RPS vale {a_rps.loc['media squadra + campo', 'MDE (80%)']:.5f} contro
   una differenza osservata di {abs(a_rps.loc['media squadra + campo', 'differenza']):.5f}:
   servirebbero circa {int((a_rps.loc['media squadra + campo', 'MDE (80%)'] / abs(a_rps.loc['media squadra + campo', 'differenza'])) ** 2 * len(pv)):,} partite
   per distinguerli, cioe' molte piu' di quante una Serie A ne produca. **E' la
   prima domanda del progetto in cui G2 avrebbe un uso diretto e quantificato.**
3. **Nessuna valutazione di valore atteso e' possibile** senza quote di chiusura
   reali (vincolo 3), e non sono nel repository. Finche' non ci sono, «il modello
   e' meglio del mercato» non e' una frase che questo progetto possa pronunciare.
4. **Le due partite disallineate restano fuori** per decisione dell'utente. Sono
   {len(pv)} contro le 1.640 che si avrebbero allineando il burn-in alla giornata.
"""

    OUT_MD.write_text(testo, encoding="utf-8")
    print(f"\n-> {OUT_MD}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
