# -*- coding: utf-8 -*-
"""Fase 10 / Blocco R0 — il perimetro di cio' che e' validabile.

    ./.venv/Scripts/python.exe scripts/run_fase10_r0.py

**Non tocca la rete, non scrive niente sotto `data/`, e non stima niente**:
nessun fit, nessun bersaglio, nessun iperparametro. Legge il walk-forward dei gol
prodotto da E3 e l'aggancio partite della Fase 8, ruota da squadra-partita a
partita, e **conta**.

Il blocco esiste per rispondere a una domanda che l'ordine fra G1 e G2 rende
urgente: **di quante partite esiste davvero una distribuzione del risultato**, e
quante realizzazioni ha ciascuna affermazione che i blocchi successivi vorrebbero
fare. Un conteggio, non una stima.

~5 s, tutto da cache.
"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sot import config, perimetro as PM  # noqa: E402

OUT_MD = config.REPORTS / "fase10_r0_perimetro.md"


def _tab(df: pd.DataFrame, dec: dict[str, int] | None = None) -> str:
    """Tabella markdown. Nessun separatore delle migliaia (vedi `run_fase9_e0`)."""
    dec = dec or {}
    num = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]

    def cella(c, v) -> str:
        if isinstance(v, bool):
            return "si" if v else "no"
        if pd.isna(v):
            return ""
        if c in dec:
            return f"{v:.{dec[c]}f}"
        if c in num and float(v) == int(v):
            return str(int(v))
        if c in num:
            return f"{v:.3f}"
        return str(v).replace("|", r"\|")

    testa = "| " + " | ".join(str(c) for c in df.columns) + " |"
    sep = "|" + "|".join("---:" if c in num else "---" for c in df.columns) + "|"
    righe = ["| " + " | ".join(cella(c, v) for c, v in zip(df.columns, r)) + " |"
             for r in df.itertuples(index=False)]
    return "\n".join([testa, sep, *righe])


def main() -> int:
    print("Fase 10 / R0 — perimetro\n" + "=" * 60)

    p = PM.partite()
    casc = PM.cascata(p)
    gio = PM.struttura_giornate(p)
    dis = PM.disallineamenti(p)
    soglia = PM.verifica_soglia_eligible()
    esito = PM.verifica_esito(p)
    real = PM.realizzazioni(p)

    tot_acq = int(casc["acquisite"].sum())
    tot_prev = int(casc["con_previsione"].sum())
    tot_val = int(casc["validabili"].sum())

    print(f"\nacquisite      : {tot_acq}")
    print(f"con previsione : {tot_prev}  (-{tot_acq - tot_prev}, senza training)")
    print(f"VALIDABILI     : {tot_val}  (-{tot_prev - tot_val}, burn-in)")
    print(f"\nquota persa    : {100 * (tot_acq - tot_val) / tot_acq:.1f}%")
    print(f"\nsoglia eligible: idx >= {soglia['soglia']}, "
          f"coincide={soglia['coincide']}, discordanti={soglia['discordanti']}")
    print(f"vincolo 7      : punteggio {esito['punteggio_identico']}/"
          f"{esito['confrontabili']}, esito {esito['esito_identico']}/"
          f"{esito['confrontabili']}")
    print(f"\ngiornate piene : {int(gio['giornate_piene'].sum())} su "
          f"{int(gio['giornate_con_previsione'].sum())}")
    print(f"realizzazioni della classifica: {int(real.loc[real.blocco == 'R3', 'n'].iloc[0])}")

    dist = (p[p["validabile"]]["esito"].value_counts(normalize=True)
            .reindex(["1", "X", "2"]).rename("quota").reset_index())
    dist.columns = ["esito", "quota"]
    # Precalcolata: dentro un'espressione f-string `{{...}}` e' un set, non un
    # dict letterale, e il messaggio d'errore ("unhashable type") non lo dice.
    tab_dist = _tab(dist, dec={"quota": 4})

    testo = f"""# Fase 10 / Blocco R0 — il perimetro di cio' che e' validabile

> Generato da `scripts/run_fase10_r0.py` il {date.today().isoformat()}.
> **Nessuna richiesta di rete. Nessuna stima**: nessun fit, nessun bersaglio,
> nessun iperparametro. Questo blocco *conta*.

Il blocco risponde a una domanda sola, e la risposta decide quanto ha senso
spendere sui blocchi successivi: **di quante partite esiste davvero una
distribuzione del risultato**, e con quante realizzazioni si potrebbe validare
ciascuna affermazione che R2 e R3 vorrebbero fare.

---

## 1. La cascata: dove si perdono le partite

**{tot_acq} acquisite → {tot_prev} con previsione → {tot_val} validabili.**
Il {100 * (tot_acq - tot_val) / tot_acq:.1f}% si perde, e si perde per **due**
ragioni diverse che non vanno sommate come se fossero la stessa.

{_tab(casc)}

- **`senza_training` ({tot_acq - tot_prev} partite, 30 per stagione).**
  `validate.date_splits` pretende 30 partite di training prima di produrre una
  previsione: con dieci partite per turno sono **le prime tre giornate**, che nel
  derivato di E3 non compaiono affatto. Non e' una perdita di dati, e' l'assenza
  di un passato da cui prevedere.
- **`perse_burnin` ({tot_prev - tot_val} partite).** Hanno una previsione ma non
  sono `eligible`: sono le giornate 4 e 5. La soglia e' **`team_match_idx >= {soglia['soglia']}`**,
  e la relazione e' verificata invece che assunta — `verifica_soglia_eligible()`
  ritorna `coincide={soglia['coincide']}`, {soglia['discordanti']} discordanti su
  {tot_prev * 2} righe.

**L'universo acquisito si conta, non si assume a 380.** Il 2022-23 ne ha 375
perche' il calendario ne ha 381 (il playout) e WhoScored ne ha perse 6; il
2021-22 ne ha 374. Sono due scarti di segno opposto e nessuno dei due sarebbe
stato ipotizzabile.

---

## 2. `eligible` e' una proprieta' della SQUADRA, non della partita

Ne segue che una partita puo' avere un lato eligible e l'altro no. **Succede due
volte, ed entrambe nel 2021-22:**

{_tab(dis)}

Non e' una curiosita'. `team_match_idx` numera le partite **presenti nei dati**,
quindi su una squadra a cui la fonte ne ha perse alcune scorre indietro: alla sua
sesta partita vera l'Atalanta e' all'indice 5. **E' lo stesso difetto
dell'indice che E2 aveva trovato sulle squalifiche.**

**E il lato in ritardo e' una squadra con perdite alla fonte in entrambi i casi,
verificato e non addotto**: nel 2021-22 l'Atalanta ha 35 partite acquisite su 38
e la Salernitana 37. Sono le due che stanno all'indice 5 mentre l'avversario e'
gia' al 6. Il difetto cade quindi **dove la perdita alla fonte e' gia' dichiarata
non casuale** — l'Atalanta ne perde sei in due stagioni contro un'attesa di 1,2,
p corretto 1,1% — e non a caso fra le venti squadre.

Per una previsione 1X2 **servono entrambi i lati**: un esito non e' meta'
previsto. Le due partite escono, ed e' il motivo per cui il 2021-22 ne perde 21 e
non 20.

---

## 3. La giornata vera, e perche' R3 non puo' usare `team_match_idx`

`team_match_idx` **non e' la giornata** — lo dice gia' il Blocco 0 — e per una
metrica per partita non importa. Per una **classifica** importa: un indice che
salta i recuperi mette la stessa squadra in due turni diversi. La giornata vera
arriva dall'aggancio della Fase 8, che ha chiuso la D6, ed e' disponibile su
**{esito['confrontabili']} partite su {tot_prev}**.

{_tab(gio)}

- **Una giornata "piena" ha tutte e dieci le partite validabili**, ed e' l'unita'
  che R3 userebbe. Sono **{int(gio['giornate_piene'].sum())} su {int(gio['giornate_con_previsione'].sum())}**.
- Le giornate non piene **oltre il burn-in** sono esattamente le 12 partite che
  WhoScored non ha: 2021-22 giornate 10-12, 2022-23 giornate 12, 18, 28, 29, 33.
- **La prima giornata piena e' la 6a o la 7a**, mai prima. Ne segue il fatto che
  R3 deve dichiarare in specifica invece di scoprire: **non si simula una
  stagione da zero.** Non esiste una probabilita' di scudetto alla prima
  giornata, perche' prima della sesta il modello non ha previsioni. Si simula il
  **resto** di una stagione a partire dalla giornata k, data la classifica a k.

**L'unica partita senza giornata** e' lo spareggio Spezia-Verona del 2022-23: e'
il residuo gia' dichiarato dall'aggancio — l'unica coppia ordinata che si ripete,
che senza accorgersene si sarebbe agganciata ai voti della giornata 25.

---

## 4. Il bersaglio di R2 regge a due derivazioni indipendenti (vincolo 7)

L'esito osservato viene da due fonti che non si sono mai parlate: i gol
ricomposti dagli eventi WhoScored (con gli autogol riattribuiti, che
`shots_mask` esclude — verificati 3.778/3.778 contro `matches.json` in E3) e il
punteggio della fonte dei voti, che non ha mai visto un evento.

| | |
|---|---:|
| partite confrontabili | {esito['confrontabili']} |
| **punteggio identico** | **{esito['punteggio_identico']}** |
| punteggio discorde | {esito['punteggio_discorde']} |
| **esito 1X2 identico** | **{esito['esito_identico']}** |
| esito 1X2 discorde | {esito['esito_discorde']} |

**Zero discordanze in entrambi i versi.** Non passa da nessun modello, ed e' la
verifica piu' forte che R0 poteva fare a costo zero: il bersaglio che R2
userebbe non dipende da quale delle due fonti lo fornisce.

Distribuzione osservata dell'esito sulle {tot_val} partite validabili:

{tab_dist}

E' anche il **baseline piu' stupido di R2** (vincolo 6), e va battuto prima di
qualunque altra affermazione.

---

## 5. Quante realizzazioni ha ciascuna affermazione

E' la tabella che decide l'ordine fra G1 e G2, e sta nel codice
(`perimetro.realizzazioni()`) perche' e' un conteggio e non un'opinione.

{_tab(real)}

**Le due righe di R2 sono abbondanti.** {tot_val} partite sono due volte e mezzo
le 660 righe su cui le Fasi 2 e 4 hanno concluso, e su un bersaglio — l'esito —
che E3 ha gia' mostrato essere **piu' facile da distinguere** dei tiri in porta
(t = 5,52 contro 1,86 sullo stesso confronto). Il burn-in **non** e' un problema
per R2: era la preoccupazione che ha motivato questo blocco, ed e' infondata.

**La riga di R3 e' il problema, ed e' quantificato.** Una probabilita' di
scudetto ha **una realizzazione per stagione**: cinque stagioni sono cinque
estrazioni. Nessun RPS calcolato su cinque punti separa un modello da un altro.
E le previsioni fatte a giornate diverse **della stessa stagione non sono
indipendenti**: condividono l'esito, quindi 155 giornate piene non sono 155
osservazioni ma cinque, guardate piu' volte.

---

## 6. La dipendenza da G2, dichiarata prima e non scoperta a meta'

| affermazione | G2 la cambia? | perche' |
|---|---|---|
| calibrazione dei parametri | **no** | poolare i campionati e' l'errore che E1 vieta e che E4 ha quantificato (livello dei fit +15,8% fra stagioni; fra campionati di piu'). G2 da' fit **paralleli**, non un fit italiano piu' grande |
| R2 — 1X2, over/under | **no** | {tot_val} partite bastano; G2 aggiungerebbe generalizzazione, che e' una domanda di G2 |
| **R3 — classifica** | **si', ed e' l'unico punto** | da 5 realizzazioni a 25. **Sottile, non sufficiente** |

**Ne segue che la dipendenza non impone G2 prima.** Impone che R3 dichiari il
proprio limite invece di fabbricare una validazione, che e' il vincolo 5. Se G2
si facesse, porterebbe la classifica da *invalidabile* a *debolmente validabile*:
va detto adesso perche' nessuno se lo aspetti come una soluzione.

---

## 7. Condizione bloccante su G2 — autorizzazione

**Registrata qui come condizione, non come dettaglio tecnico**, su richiesta
dell'utente del 2026-08-07.

L'autorizzazione dichiarata in `regole_fantacalcio.md` §7.1 riguarda **WhoScored
per la Serie A**, via il mirror `1xbet.whoscored.com` fissato in
`acquisition/whoscored/main.py:60`. **Estenderla a quattro campionati e' una
decisione dell'utente, che verra' presa se e quando si arriva a G2, e non
prima.** Nessun blocco della Fase 10 la presuppone.

Accanto, e indipendente: tutti e quattro gli altri campionati hanno
`whoscored: None` in `config.LEAGUE_CODES`. La terna `(regione, torneo, slug)`
**non e' accertata per nessuno**, e `target.py:63` solleva un'eccezione invece di
inventare un URL. «Lo scraper e' gia' parametrizzato» e' vero e non basta.

---

## 8. Domande aperte

1. **La forma della dipendenza fra i due lati non e' stata guardata**, ed e' di
   proposito: R0 non stima. Che i due lambda di una partita vengano dallo stesso
   modello non implica che i gol siano indipendenti dati i lambda, ed e' la
   domanda di R1. Qui c'e' solo l'universo su cui la si misurera'.
2. **Le due partite disallineate potrebbero essere recuperate**, allineando il
   burn-in alla **giornata** invece che a `team_match_idx`. Non e' stato fatto:
   cambierebbe la definizione di `eligible` che E3 ha gia' pubblicato, e due
   partite su 1.638 non giustificano il rischio di spostare un numero altrove.
   Va deciso in R2 **se** si tocca, non qui.
3. **Il playout Spezia-Verona resta fuori** per mancanza di giornata. E' una
   partita vera e non va scartata in silenzio: se R3 la vuole, va deciso a quale
   turno appartenga, e non c'e' una risposta ovvia.
4. **Non e' stato verificato che l'ordine di `p['data']` sia sufficiente a
   ricostruire la classifica progressiva** in presenza di recuperi. R3 ne ha
   bisogno e questo blocco non gliel'ha dato.
"""

    OUT_MD.write_text(testo, encoding="utf-8")
    print(f"\n-> {OUT_MD}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
