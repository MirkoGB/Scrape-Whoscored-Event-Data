# -*- coding: utf-8 -*-
"""Fase 10 / Blocco R3 — la classifica: simulare il resto di una stagione.

    ./.venv/Scripts/python.exe scripts/run_fase10_r3.py

**Non tocca la rete e non scrive niente sotto `data/`.** Legge il calendario
completo della fonte dei voti, i lambda di E3.1 e le probabilita' ricalibrate di
R2-bis. **Non stima nessun parametro nuovo**: simula.

~5 min (Monte Carlo: 10.000 repliche x 5 stagioni x 3 giornate x 4 varianti).
"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sot import classifica as CL, config  # noqa: E402

OUT_MD = config.REPORTS / "fase10_r3_classifica.md"
STAGIONE_VETRINA = "2025-2026"
K_VETRINA = 19


def _tab(df: pd.DataFrame, dec: dict[str, int] | None = None) -> str:
    dec = dec or {}
    num = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]

    def cella(c, v) -> str:
        if isinstance(v, (bool, np.bool_)):
            return "si" if v else "no"
        if pd.isna(v):
            return "—"
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
    print("Fase 10 / R3 — classifica\n" + "=" * 60)

    ver = CL.verifica_calendario()
    ordine = CL.partite_fuori_ordine()
    cop_prev = CL.copertura_previsioni()

    sim_v = CL.simula(STAGIONE_VETRINA, K_VETRINA)
    prob = CL.probabilita(STAGIONE_VETRINA, K_VETRINA, sim=sim_v)
    pm = CL.pari_merito(sim_v)

    cop = CL.copertura()
    pit = CL.forma_pit(k=K_VETRINA)
    var = CL.confronto_varianti(k=K_VETRINA)
    app = CL.confronto_appaiato_punti(k=K_VETRINA)
    aff = CL.affidabilita_claim()

    disp = {k: CL.dispersione_finale(k=k) for k in CL.K_VALUTAZIONE}
    disp_k = pd.DataFrame([{"k": k, "rapporto sd medio": float(t["rapporto sd"].mean()),
                            "sd punti veri": float(t["sd punti veri"].mean()),
                            "sd punti attesi": float(t["sd punti attesi"].mean())}
                           for k, t in disp.items()])

    a = app.set_index("baseline")
    c19 = cop.set_index("k").loc[K_VETRINA]

    print(f"\nMAE punti finali dalla {K_VETRINA}a: {c19['MAE punti']:.2f} "
          f"| copertura 50/80/95: {c19['copertura 50%']:.0%}/"
          f"{c19['copertura 80%']:.0%}/{c19['copertura 95%']:.0%}")
    print(f"  vs media squadra + campo: {a.loc['media squadra + campo', 'differenza']:+.3f} "
          f"punti, t stagione {a.loc['media squadra + campo', 't (stagione, n=5)']:+.2f}")
    print(f"  rapporto sd classifica: " +
          " · ".join(f"k={int(r.k)} {r._2:.2f}" for r in disp_k.itertuples()))

    n_team = len(prob)
    retrocesse = prob[prob["posizione vera"] > n_team - CL.POSTI_RETROCESSIONE]
    retrocesse = retrocesse.sort_values("retrocessione", ascending=False)
    terza_piu_alta = prob.sort_values("retrocessione", ascending=False).iloc[2]
    como = prob[prob["squadra"] == "Como"].iloc[0]
    como_top = float(como[f"top {CL.POSTI_EUROPA}"])
    como_pos = int(como["posizione vera"])
    print(f"\n  Como dalla {K_VETRINA}a: {como['punti attesi']:.1f} punti attesi "
          f"(veri {int(como['punti finali veri'])}), top {CL.POSTI_EUROPA} "
          f"{como_top:.0%}, posizione vera {como_pos}")

    testo = f"""# Fase 10 / Blocco R3 — la classifica: simulare il resto di una stagione

> Generato da `scripts/run_fase10_r3.py` il {date.today().isoformat()}.
> **Nessuna richiesta di rete. Nessun parametro nuovo**: i lambda vengono da
> E3.1, le probabilita' ricalibrate da R2-bis, il calendario dalla fonte dei
> voti. Questo blocco **simula**.

---

## 0. Il vincolo che struttura il blocco, e che viene da R0

**Non si simula una stagione da zero.** Le prime tre giornate non hanno alcuna
previsione — il walk-forward di E3 pretende 30 partite di training — la 4a e la
5a ne hanno una ma non sono `eligible`, e la prima giornata piena e' **la sesta o
la settima, mai prima**. Non esiste una probabilita' di scudetto alla prima
giornata, e il blocco non finge che esista: **simula il resto di una stagione
dalla giornata `k`, data la classifica vera a `k`**.

Le giornate di partenza sono **dichiarate e non scelte guardando i risultati**:
{", ".join(str(x) + "a" for x in CL.K_VALUTAZIONE)}, cioe' un quarto, il giro di
boa e tre quarti di stagione.

**E R0 dice anche quanto poco si potra' concludere.** Una probabilita' di
scudetto ha **una realizzazione per stagione**, e previsioni fatte a giornate
diverse della stessa stagione condividono l'esito. Ne segue la scelta che governa
tutto il blocco:

> **La validazione di R3 sono i PUNTI FINALI di ogni squadra, non le probabilita'
> di scudetto.** I primi hanno venti realizzazioni per stagione, le seconde una.
> §5 misura i punti; §6 riporta le probabilita' di classifica come
> **descrizione**, con il proprio limite scritto accanto e non in fondo.

---

## 1. Gli ingressi, e dove il buco di WhoScored non morde

| ingresso | fonte |
|---|---|
| classifica vera a `k`, risultati veri | **calendario completo della fonte dei voti**: 380 partite per stagione, gol mai nulli |
| probabilita' 1X2 | R2-bis, **Platt walk-forward** dove esiste un passato su cui stimarlo |
| punteggio (per la differenza reti) | congiunta di R1 **condizionata all'esito ricalibrato** |

**La classifica non ha buchi**, ed e' il punto che R1 aveva anticipato: delle 12
partite che WhoScored non ha, il **risultato** si legge lo stesso dall'altra
fonte. Il buco sta negli **ingressi** della previsione, non nel bersaglio.

Il calendario regge le identita' che una stagione deve rispettare — falsificabili
e senza modelli di mezzo:

{_tab(ver)}

**Le partite del futuro senza previsione ricevono un ripiego dichiarato** — i
lambda medi di casa e trasferta della loro stagione, cioe' il candidato meno
informativo del repository — e **si contano**:

{_tab(cop_prev)}

Sono al massimo cinque per stagione e stanno tutte nelle due annate a cui
WhoScored ha perso partite. Non e' una scelta di modellazione: e' il modo di non
far sparire una partita dalla classifica.

**La domanda aperta n. 4 di R0 ha una misura.** Era «non e' verificato che
l'ordine per data basti a ricostruire la classifica progressiva in presenza di
recuperi». Qui `k` e' **ordinale**: «dopo la giornata `k`» significa «tutte le
partite con `giornata <= k`», anche quelle rinviate e giocate dopo. Le due
letture divergono su:

{_tab(ordine, dec={"quota": 4})}

Circa l'1,3% delle partite si gioca dopo che la giornata successiva e'
cominciata. **La convenzione ordinale e' dichiarata, non dimostrata equivalente**:
un osservatore in tempo reale vedrebbe squadre con partite da recuperare, e per
quelle quattro o cinque partite per stagione la classifica di partenza di questo
blocco e' piu' informata della sua.

---

## 2. Come si simula, e perche' cosi'

La classifica a `k` entra come **costante**: e' la storia, non una previsione, e
simularla sarebbe simulare cio' che si sa gia'. Delle partite rimanenti si estrae
prima l'**esito** con la probabilita' ricalibrata di R2-bis, poi il **punteggio**
dentro la classe estratta, con `P(gol_casa, gol_trasferta | esito)` presa dalla
congiunta di R1.

> **E' la costruzione che tiene insieme la ricalibrazione e la differenza reti.**
> R2-bis aveva dichiarato il prezzo di Platt: le tre probabilita' 1X2 non escono
> piu' dalla stessa congiunta che produce l'over/under. Condizionando il
> punteggio all'esito quel prezzo non si paga sui punti — la probabilita'
> dell'esito e' quella adottata, e il punteggio resta coerente con essa.

**Lo scioglimento dei pari merito e' una semplificazione dichiarata**: punti,
poi differenza reti, poi gol fatti, poi estrazione col seme del progetto. La
Serie A userebbe gli **scontri diretti**. Quanto spesso la scelta decide una
soglia, misurato sulla stagione vetrina:

| soglia | repliche in cui c'e' un pari merito al confine |
|---|---:|
| scudetto | {pm['scudetto']:.1%} |
| top {CL.POSTI_EUROPA} | {pm['europa']:.1%} |
| retrocessione | {pm['retrocessione']:.1%} |

**Non e' trascurabile al confine dell'Europa e della retrocessione**, ed e' il
motivo per cui sta in tabella invece che in una nota.

---

## 3. La stagione vetrina: {STAGIONE_VETRINA} dalla {K_VETRINA}a giornata

{_tab(prob, dec={"punti attesi": 1, "scudetto": 3, f"top {CL.POSTI_EUROPA}": 3, "retrocessione": 3})}

Le colonne `punti finali veri` e `posizione vera` sono **l'esito**, non un
ingresso: la simulazione non le vede.

**Le tre retrocesse e la probabilita' che avevano alla {K_VETRINA}a giornata**:
{", ".join(f"**{r.squadra}** {r.retrocessione:.0%}" for r in retrocesse.itertuples())}.
Due su tre erano le due piu' alte della colonna; **la terza no**, ed e' il modo
onesto di leggere la tabella — la squadra con la terza probabilita' piu' alta
({terza_piu_alta['squadra']}, {terza_piu_alta['retrocessione']:.0%}) si e'
salvata. Il Como, che e' la squadra del progetto, aveva
{como_top:.0%} di finire nei primi {CL.POSTI_EUROPA} ed e' arrivato
{int(como_pos)}o.

---

## 4. Il danno che R2-bis prevedeva e' molto piu' piccolo, e il perche' si misura

R2-bis aveva misurato che la classifica e' **sotto-dispersa di un fattore 2,0**
sulle probabilita' di partita, e ne aveva tratto che le code di R3 sarebbero
uscite troppo grasse. **Sui punti finali quel fattore quasi sparisce**, e la
ragione e' che la simulazione **parte dalla classifica vera**:

{_tab(disp_k, dec={"rapporto sd medio": 3, "sd punti veri": 2, "sd punti attesi": 2})}

Il rapporto scende da 1,27 alla 10a a 1,05 alla 28a. **Il meccanismo e'
aritmetico e non una scusa**: la classifica a `k` porta dentro la separazione
**vera** fra le squadre, quella osservata e non quella dichiarata dal modello, e
la compressione tocca solo la parte ancora da giocare. Piu' `k` avanza, meno
resta da comprimere.

> **Ne segue una correzione della lettura di R2-bis, non dei suoi numeri.** Il
> 2,0 e' giusto e riguarda cio' che il modello *dichiara per partita*; la sua
> conseguenza su R3 e' molto piu' piccola di quanto R2-bis lasciasse prevedere,
> **perche' R3 non simula una stagione intera**. Se qualcuno un giorno volesse
> simulare da giornata zero — cosa che R0 vieta per un'altra ragione — quel 2,0
> tornerebbe intero.

Il dettaglio per stagione alla {K_VETRINA}a giornata:

{_tab(disp[K_VETRINA], dec={"sd punti veri": 2, "sd punti attesi": 2, "sd dentro una squadra": 2, "primo vero": 0, "primo atteso": 1, "ultimo vero": 0, "ultimo atteso": 1, "rapporto sd": 3})}

**Dove la compressione si vede ancora e' agli estremi**: l'ultima in classifica
fa in media {disp[K_VETRINA]['ultimo vero'].mean():.0f} punti veri contro
{disp[K_VETRINA]['ultimo atteso'].mean():.0f} attesi. Il modello non crede che una
squadra possa andare cosi' male, ed e' lo stesso segno che la Fase 3 e la Fase 4
avevano trovato sul terzile alto di lambda e sulle squadre di vertice.

---

## 5. La validazione: i punti finali

{_tab(cop, dec={"copertura 50%": 2, "copertura 80%": 2, "copertura 95%": 2, "MAE punti": 3, "bias punti": 3, "sd simulata": 2, "sd osservata": 2, "chi2 PIT (9 gdl)": 1})}

- **La copertura non e' sotto il nominale: e' sopra.**
  {c19['copertura 50%']:.0%} / {c19['copertura 80%']:.0%} / {c19['copertura 95%']:.0%}
  contro 50 / 80 / 95 alla {K_VETRINA}a. Gli intervalli sono se mai **troppo
  larghi**, non troppo stretti — cioe' l'opposto di cio' che la sotto-dispersione
  faceva temere. Le due cose convivono ed e' la firma dello shrinkage: previsioni
  tirate verso il centro **e** incertezza abbondante attorno a ciascuna.
- **Il bias e' praticamente nullo** ({c19['bias punti']:+.3f} punti su una
  stagione intera) e il MAE cala con `k` come deve: 4,8 punti dalla 10a,
  {c19['MAE punti']:.1f} dalla {K_VETRINA}a, 2,7 dalla 28a.
- **Il chi2 sulla PIT non e' un test qui, ed e' importante dirlo**: venti squadre
  di una stessa stagione si dividono un monte punti quasi fisso, quindi le cento
  righe sono **correlate per costruzione** e il `p` nominale sopravvaluta la
  significativita'. Si riporta come descrizione. La forma:

{_tab(pit, dec={"attese": 1})}

  Non e' ne' una `U` (intervalli stretti) ne' una campana pulita: e' rumorosa,
  con la fascia alta piu' magra dell'attesa, cioe' qualche squadra che finisce
  sotto la coda superiore della propria distribuzione. Con cento righe correlate
  non si conclude altro.

**Contro i baseline, con la stessa procedura di simulazione** (vincolo 6):

{_tab(var, dec={"MAE punti": 3, "bias punti": 3, "copertura 50%": 2, "copertura 80%": 2, "copertura 95%": 2, "sd simulata": 2, "sd osservata": 2})}

{_tab(app, dec={"MAE modello": 3, "MAE baseline": 3, "differenza": 3, "t (squadra-stagione, n=100)": 2, "t (stagione, n=5)": 2, "p (stagione)": 4})}

- **Qui il modello batte il baseline migliore, e su 1X2 non lo faceva.** Contro
  `media squadra + campo` la differenza vale
  {a.loc['media squadra + campo', 'differenza']:.3f} punti di MAE con
  t = {a.loc['media squadra + campo', 't (stagione, n=5)']:+.2f} sull'unita'
  onesta (la stagione, n = 5, p = {a.loc['media squadra + campo', 'p (stagione)']:.3f}).
  Su una singola partita il margine valeva t = −1,10 e stava dentro il rumore;
  **su diciannove giornate lo stesso margine si accumula**, ed e' l'unico posto
  della Fase 10 in cui il modello si distingue da un baseline informativo.
- **La ricalibrazione di R2-bis paga**, e questo e' il ritorno del blocco
  precedente: {a.loc['modello grezzo', 'differenza']:.3f} punti di MAE contro il
  modello non ricalibrato, t = {a.loc['modello grezzo', 't (stagione, n=5)']:+.2f}
  per stagione (p = {a.loc['modello grezzo', 'p (stagione)']:.3f}). Piccolo e nella
  direzione giusta — **non e' una prova**, con cinque stagioni.
- **`media campionato` e' il candidato che si rompe sulla calibrazione**, non solo
  sull'accuratezza: copertura 33 / 57 / 79 contro il nominale 50 / 80 / 95. Non
  sapendo distinguere le squadre, sottostima quanto la classifica finale possa
  allontanarsi dalla propria previsione piatta.
- **I due `t` vanno letti insieme e non se ne sceglie uno.** Quello su cento
  righe e' ottimista perche' le squadre di una stagione si dividono un monte
  punti quasi fisso; quello su cinque stagioni e' onesto e quasi cieco.

---

## 6. Le probabilita' di classifica: descrizione, non validazione

{_tab(aff, dec={"media dichiarata": 3, "frequenza vera": 3, "Brier": 4, "Brier tasso base": 4})}

> **`media dichiarata` = `frequenza vera` e' un'IDENTITA', non un risultato.**
> In ogni replica c'e' esattamente un campione, quattro squadre nei primi quattro
> posti e tre retrocesse: le probabilita' sommano a quei numeri per costruzione,
> e la frequenza vera anche. Chi leggesse quella colonna come «il modello e'
> calibrato» leggerebbe un vincolo contabile. **La colonna che dice qualcosa e' il
> Brier accanto al tasso base**, ed e' migliore su tutte e tre le affermazioni e
> a tutte e tre le giornate.
>
> **E resta una descrizione.** Uno scudetto ha cinque realizzazioni in tutto, e
> le cento righe della tabella ne contengono cinque di indipendenti. Il vincolo di
> R0 e' questo, non e' aggirabile con piu' repliche Monte Carlo, e G2 lo
> porterebbe da 5 a 25 — **sottile, non sufficiente**, come R0 aveva gia' scritto.

---

## 7. Domande aperte

1. **Le probabilita' di classifica restano non validate**, e non per una
   mancanza di questo blocco: cinque realizzazioni non separano un modello da un
   altro. Chi volesse validarle deve portare campionati, non repliche.
2. **Gli scontri diretti non sono simulati.** Al confine dell'Europa e della
   retrocessione un pari merito compare nel {pm['europa']:.0%} e nel
   {pm['retrocessione']:.0%} delle repliche, quindi la semplificazione tocca una
   frazione non trascurabile dei casi. Il costo **non e' stato misurato**: per
   farlo servirebbe tenere la matrice degli incroci in ogni replica.
3. **La compressione agli estremi resta**, ed e' l'unica parte della
   sotto-dispersione di R2-bis che sopravvive alla partenza dalla classifica
   vera: l'ultima in classifica e' prevista troppo forte di una decina di punti.
   E' lo stesso segno gia' misurato in Fase 3, Fase 4 e 6A, e **non va corretto
   ritoccando lo shrinkage** — sarebbe la quarta volta che il progetto rifiuta
   quella strada.
4. **La convenzione ordinale su `k`** e' dichiarata e non dimostrata equivalente
   alla lettura in tempo reale: l'1,3% delle partite si gioca fuori dall'ordine
   della propria giornata, e per quelle la classifica di partenza usata qui e'
   piu' informata di quanto un osservatore alla giornata `k` avrebbe.
"""

    OUT_MD.write_text(testo, encoding="utf-8")
    print(f"\n-> {OUT_MD}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
