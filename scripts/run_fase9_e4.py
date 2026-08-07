# -*- coding: utf-8 -*-
"""Fase 9 / Blocco E4 — voto base e bonus.

    ./.venv/Scripts/python.exe scripts/run_fase9_e4.py [--force]

**Non tocca la rete.** Legge i CSV WhoScored gia' acquisiti, i Parquet di E0/E1,
i voti e i listoni; produce il derivato dei piazzati, npxG e xA, la verifica dei
cinque fit di xG, i modelli del voto base e dei bonus, i rigori come assegnazione
discreta e la prova su QI.

`--force` rilegge i 1.889 CSV per rifare il derivato dei piazzati (~2 min);
senza, lo rilegge dalla cache.
"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sot import config, fantapunti as FP, modello_asta as MA  # noqa: E402
from sot import voto_bonus as VB  # noqa: E402

OUT_MD = config.REPORTS / "fase9_e4_voto_bonus.md"


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
    return "\n".join([testa, sep] + righe)


def main() -> None:
    force = "--force" in sys.argv
    p: list[str] = []

    print("E4.0 — gate sui qualifier e sulle colonne...")
    pattern = VB.verifica_pattern()
    gate_q = VB.gate_qualifier()
    gate_c = VB.gate_colonne()
    collisione = VB.collisione_passfreekick()

    print("E4.0 — derivato dei piazzati (rilettura dei CSV se --force)...")
    piazzati = VB.piazzati(force=force)
    coer_rig = VB.coerenza_rigori(piazzati)
    coer_cor = VB.coerenza_corner(piazzati)
    quad = VB.quadratura_rigoristi(piazzati)
    quad2 = VB.quadratura_rigoristi(piazzati, min_rigori=2)
    conc = VB.sintesi_concentrazione(VB.concentrazione_rigoristi(piazzati))
    qual_assist = VB.qualita_assist()

    print("E4.2 — i cinque fit di xG...")
    fit_forma = VB.differenza_fra_fit()
    fit_scala = VB.scale_dei_fit()

    print("E4 — strato feature e gate di E1 sulle candidate nuove...")
    residuo = VB.residuo_ponte()
    g, _rif = VB.standardizza_e4(VB.per_giocatore())
    deriva = VB.deriva_e4(g)

    print("il divario vero di E4 (corregge un numero pubblicato)...")
    ps = FP.per_giocatore_stagione()
    wf = MA.walkforward(per_stagione=ps)
    scomp = MA.scomposizione_errore(wf, ps)

    print("E4.1 — quanto del voto e' spiegabile...")
    spieg = VB.spiegazione_voto()
    varianza = VB.varianza_del_voto()

    print("E4.3 — rigori...")
    tab = VB.con_contesto()
    sens_rig = VB.sensibilita_designato(tab)

    print("E4.4 — autogol...")
    autogol = VB.autogol_effetto_individuale(tab)

    print("E4.5 — QI...")
    rid_qi = VB.ridondanza_qi(tab)
    der_qi = VB.deriva_qi(tab)

    print("valutazione sulle quattro transizioni...")
    ris = VB.confronto(tab=tab)
    sens_pav = VB.sensibilita_pavimento()
    per_r = VB.per_ruolo(ris["dettaglio"], "punti_E4 voto + bonus")

    d3 = {"quota": 3, "deriva": 3, "rapporto": 3}

    p.append(f"# Fase 9 / Blocco E4 — voto base e bonus\n")
    p.append(f"> Rigenerato da `scripts/run_fase9_e4.py` il {date.today()}. "
             "Nessuna richiesta di rete.\n")

    p.append("""
## In una riga

**Il margine di E4 non era 8,9 punti: e' 2,5, e la correzione e' il risultato
piu' importante del blocco.** Sul denominatore corretto nessuna feature da dati
evento aggiunge niente al modello d'asta — tre varianti su tre sono negative,
tutte dentro il rumore — e l'unica cosa che si muove e' la quotazione QI da
sola, che chiude il 10,5% con `t = 2,31` e **non sopravvive alla correzione per
molteplicita'**. Lungo la strada, due colonne della fonte si sono rivelate non
essere cio' che il loro nome dice.
""")

    # ---------------------------------------------------------------- 0
    p.append("\n## 0. Il divario di E4 non e' quello che credevamo\n")
    p.append("""
La priorita' di E4 poggiava su un numero pubblicato — «con i bonus noti il MAE
scende da 61,4 a 52,5», cioe' **8,9 punti** — che questo blocco ha dovuto
misurare per costruirci sopra il proprio denominatore. Misurandolo l'ha corretto,
e i difetti sono due, indipendenti.

**Primo, e piu' grande: il campione cambia.** «Bonus noti» gira su **2.204
righe** e non 2.678. Chi non ha mai giocato in `t` non ha un tasso osservato, e
quelle 474 righe cadono — ma sono **le peggiori**, quelle in cui il modello
predice punti a chi ne fara' zero. Sulle stesse 2.204 righe il modello completo
fa **55,01**, non 61,42.

**Secondo: «bonus noti» non era il bonus.** Era costruito per differenza come
`punti/presenze - voto_atteso`, che e' l'intero **tasso per presenza**, voto
compreso. Si vede da un'identita' che la vecchia tabella non poteva mostrare
perche' aveva una riga sola: costruendo allo stesso modo l'oracolo del *voto* si
ottiene lo stesso identico numero. Le due componenti sono osservate separatamente
in `fantapunti.per_giocatore_stagione`, e da li' ora si prendono.
""")
    p.append(_tab(scomp))
    p.append("""
La colonna `mae_stesse_righe` e' nuova ed e' il rimedio strutturale: porta il MAE
del modello completo **sul campione di quella riga**, cosi' che il confronto sia
sempre orizzontale. `guadagno_vero` e' la differenza che conta.

**Il fatto di fondo non cambia, anzi si rafforza: le presenze sono il problema,
i bonus no.** 55,86 punti contro 2,51. Cambia la taglia del pezzo su cui E4
lavora — il **4%** dell'errore, non il 14,5% — e cambia quindi come si leggono i
suoi numeri: una variante che chiude il 5% di 2,5 punti sposta il MAE di un
decimo.
""")

    # ---------------------------------------------------------------- 1
    p.append("\n## 1. E4.0 — i piazzati, e due colonne che non sono cio' che dicono\n")
    p.append("""
### `passFreekick` non contiene le punizioni

E' la trappola del blocco, ed e' della stessa famiglia di `StandingSave` un piano
piu' su: li' il nome di un **qualifier** non era un identificatore, qui non lo e'
il nome di una **colonna**.
""")
    p.append(_tab(collisione))
    p.append("""
La colonna `passFreekick` e' identica riga per riga a `passCorner`, coincide con
i `CornerTaken` e ha intersezione **vuota** con gli 813 `FreekickTaken` veri. Chi
l'avesse usata avrebbe ottenuto una tabella di battitori di punizioni
perfettamente plausibile — ordine di grandezza giusto, nessun conteggio assurdo —
in cui ogni riga era un battitore di corner.

**E il gate non l'avrebbe fermata**: `passFreekick` passa a pieni voti, perche'
un gate misura se una colonna si e' mossa fra le stagioni, non se si chiama come
cio' che contiene.
""")
    p.append(_tab(gate_c, d3))
    p.append("""
Ne segue la scelta del blocco: **i piazzati si contano dai qualifier**, che sono
la strada gia' istruita e gia' misurata da E1. Il gate rifatto sui qualifier
effettivamente usati:
""")
    p.append(_tab(gate_q, {c: 5 for c in gate_q.columns if c != "qualifier"}))
    p.append("""
E la guardia che rende sicura la ricerca per sottostringa — senza l'apice di
chiusura nel pattern, `FreekickTaken` matcherebbe dentro `IndirectFreekickTaken`:
""")
    p.append(_tab(pattern))

    p.append("\n### Il qualifier `Penalty` non marca il rigorista\n")
    p.append("""
Seconda trappola, indipendente dalla prima. Il qualifier `Penalty` sta su **tutto
cio' che riguarda il rigore**: il fallo di chi l'ha concesso, il `PenaltyFaced`
del portiere, la parata. Solo un quarto dei suoi eventi e' il tiro. Contarlo nudo
avrebbe attribuito «rigori battuti» al difensore che ha commesso il fallo.

Ristretto a `isShot` coincide **riga per riga** con `penaltyScored |
penaltyMissed`, che e' una derivazione indipendente gia' in `events_slim`:
""")
    p.append(_tab(coer_rig, {"conversione": 4}))
    p.append("""
**Scarto zero in tutte e cinque le stagioni.** La colonna
`qualifier_senza_isShot` e' li' per far vedere quanto sarebbe stato l'errore: un
fattore quattro. La conversione 76,4-78,3% riproduce il 76,4% della Fase 1.

Sui corner le due strade coincidono, ed e' cio' che rende il disaccordo sulle
punizioni attribuibile alla colonna e non ai qualifier:
""")
    p.append(_tab(coer_cor))

    p.append("\n### Il test di quadratura non passa alla lettera, e la diagnosi e' misurata\n")
    p.append("""
La specifica si aspettava 1-2 rigoristi distinti per squadra-stagione «nella
grande maggioranza dei casi». Contando chiunque abbia battuto **almeno un**
rigore, si osserva:
""")
    p.append(_tab(quad, d3))
    p.append("""
Che non sia il parsing lo dice `coerenza_rigori`, che e' un controllo **piu'
forte** di questo: due derivazioni indipendenti con scarto zero non possono
sbagliare nello stesso modo. Cio' che si rompe e' la **premessa**. Contando solo
chi ne ha battuti almeno due, l'attesa torna:
""")
    p.append(_tab(quad2, d3))
    p.append("""
E la concentrazione dice quanto «battitore designato» sia un concetto solido:
""")
    p.append(_tab(conc, {c: 3 for c in conc.columns}))
    p.append("""
**Il battitore principale mediano prende il 57,7% dei rigori della sua squadra**,
i primi due l'83,3%. Un modello che desse tutti i rigori al primo sbaglierebbe di
quasi la meta': e' il numero che E4.3 usa al posto di un'assegnazione secca.
""")

    p.append("\n### Il legame passaggio chiave -> tiro\n")
    p.append("""
Il legame **non e' nei dati**: la fonte marca il tiro con `Assisted` e il
passaggio con `KeyPass`, ma non dice quale appartenga a quale. Si ricostruisce
con la regola piu' stretta possibile — il passaggio chiave piu' vicino che
precede, della stessa squadra, entro tre eventi — e la quota che resta senza
legame si conta invece di sparire:
""")
    p.append(_tab(qual_assist, {"quota_legata": 4}))

    # ---------------------------------------------------------------- 2
    p.append("\n## 2. E4.2 — i cinque fit di xG: la verifica rimandata due volte\n")
    p.append("""
E0 l'aveva dichiarata necessaria, E3 aveva potuto evitarla perche' il modello dei
gol non usa l'xG. Qui l'xG attraversa le stagioni sommato, quindi va fatta.

**La forma dei cinque fit e' la stessa.** Un modello poolato con interazioni
stagione x feature **non batte** quello con la sola intercetta di stagione, fuori
campione e con i fold raggruppati per partita:
""")
    p.append(_tab(fit_forma, {"logloss_fuori_campione": 5,
                              "guadagno_su_intercetta": 5}))
    p.append("""
**Il livello no, e la differenza e' grande.** Applicando i cinque fit agli
**stessi** tiri — che e' la domanda letterale, perche' cio' che il progetto usa
sono cinque fit separati:
""")
    p.append(_tab(fit_scala, {c: 5 for c in fit_scala.columns
                              if c != "fit_della_stagione"}))
    p.append("""
I cinque ordinano i tiri quasi allo stesso modo — correlazione **0,986-1,000**,
che e' "quasi" e non "uguale", e il residuo di forma e' proprio cio' che il test
fuori campione qui sopra dichiara inutile a prevedere. Ma il **livello** si
muove del **15,8%**, monotono e discendente: tre volte la soglia del 5% di E1.

**La risposta alla domanda e' quindi: si', la differenza fra i cinque fit e' di
sola intercetta — e l'intercetta vale il 15,8%.** Ne segue che npxG **non si
somma fra stagioni in unita' grezze**, e che la regola di E1 e' esattamente il
rimedio giusto: dividere per il riferimento di stagione toglie il livello, e la
forma stabile garantisce che non resti altro di rilevante. E' anche il *perche'*
di un verdetto che E1 aveva misurato senza potersi dare una spiegazione:
`xg_per_90` era fra le cinque irriducibili.
""")

    # ---------------------------------------------------------------- 3
    p.append("\n## 3. Lo strato feature, e il gate di E1 sulle candidate nuove\n")
    p.append("""
Le candidate di E4 sono nuove — npxG, xA, i piazzati — quindi il loro verdetto
non esiste e non si eredita: si misura, con la stessa soglia e la stessa
macchina.
""")
    p.append(_tab(deriva, {c: 4 for c in deriva.columns
                           if c not in ("candidata", "verdetto")}))
    p.append("""
Cinque passano standardizzate, **cinque restano irriducibili** — e npxG e' fra
queste, con la spiegazione appena data. Un effetto di stagione esplicito pero'
**non e' usabile fuori campione**: la stagione bersaglio non e' fra quelle su cui
si e' stimato. Entrano quindi in forma `_rel`, che e' cio' che si puo' fare, e la
conseguenza si misura: la variante «E4 senza le irriducibili» rifa' tutto senza
di loro, e la conclusione non cambia.

Il ponte a `giocatore_id` lascia indietro il 22% delle righe e lo **0,13% dei
minuti**: sono i convocati mai scesi in campo, che la fonte dei voti non elenca
perche' non hanno preso nessun voto.
""")
    p.append(_tab(residuo, {"quota_righe": 4, "quota_minuti": 5}))

    # ---------------------------------------------------------------- 4
    p.append("\n## 4. E4.1 — quanto del voto base e' spiegabile, e quanto prevedibile\n")
    p.append("""
Sono due domande diverse, e confonderle e' il modo piu' facile di far sembrare
utile un modello che non lo e'. **In campione**, al livello giocatore-stagione:
""")
    p.append(_tab(spieg, {"r2_in_campione": 4, "sd_residua": 4, "sd_totale": 4}))
    p.append("""
Il 41% della varianza del voto medio di stagione si lascia descrivere — ma e' un
**limite superiore**, come il test in campione della Fase 6D, e comprende la
forza di squadra osservata di quella stessa stagione.

**Il tetto vero sta piu' in basso**, e si legge alla riga giocatore-partita:
""")
    p.append(_tab(varianza, {c: 4 for c in varianza.columns
                             if c != "raggruppamento"}))
    p.append("""
**Solo l'11-13% della varianza del voto sta FRA i giocatori**; l'87-89% sta
dentro lo stesso giocatore, cioe' e' la partita, l'avversario, la giornata.
Nessun modello che assegni un numero a un giocatore puo' prenderla. E' la parte
di voto che nessun modello prende, ed e' dichiarata qui accanto al numero e non
in fondo.

Il **risultato di partita**, che la specifica chiedeva fra i regressori, entra in
questa tabella e **non** nel modello predittivo, per una ragione di orologio: il
risultato di una partita di `t` non e' noto all'asta. La forza di squadra e' il
modo in cui quella stessa informazione entra legittimamente — e' cio' che del
risultato si sa prima.
""")

    # ---------------------------------------------------------------- 5
    p.append("\n## 5. E4.3 — i rigori, dove l'assegnazione discreta vale piu' di tutto\n")
    p.append("""
Un rigorista vale +3 per rigore segnato e -3 per uno sbagliato. Il modello e'
`rigori attesi della squadra x P(e' lui il designato) x tasso di realizzazione`,
con la conversione **quasi interamente shrinkata** verso la media di lega: un
rigorista batte 5-6 rigori in stagione, quindi la sua conversione osservata ha un
errore standard di ~0,18, piu' grande di qualunque differenza vera fra rigoristi.

**I rigori attesi non vengono da E3.1**, e la precisazione non e' pedanteria:
E3.1 modella i gol, e i rigori assegnati sono un'altra grandezza (~0,28 per
partita contro ~1,4 gol). Attribuire a un modello validato una stima che non ha
prodotto sarebbe prendere in prestito la sua validazione.

**Quanto vale spostare il designato**, cioe' l'unico interruttore che all'asta si
gira davvero — le cinque squadre-stagione in cui pesa di piu':
""")
    p.append(_tab(sens_rig, {"quota_primo": 3, "punti_primo_naturale": 2,
                             "punti_secondo_se_designato": 2, "spostamento": 2}))
    p.append("""
**Fino a 15 punti di stagione da un singolo switch.** E' piu' di tutto il divario
medio su cui E4 lavora (2,5 punti di MAE), e va letto cosi': sul singolo
giocatore l'assegnazione del rigorista e' la decisione piu' pesante del blocco,
anche se sulla media di 2.678 righe non si vede. Per il 2026-27 il designato **e'
un input**, non una stima: `punti_rigori(designato={...})` lo impone a mano.
""")

    # ---------------------------------------------------------------- 6
    p.append("\n## 6. E4.4 — gli autogol non hanno un effetto individuale\n")
    p.append(_tab(autogol, {"mae_autogol": 4, "guadagno": 4}))
    p.append("""
Il modello con l'effetto individuale non batte quello col solo tasso di ruolo:
resta il secondo, che e' quello che la specifica prevedeva — **verificato invece
che assunto**.

Sui cartellini, la fonte del malus resta quella dei **voti** e non WhoScored: e'
gia' stabilito da E2 e da E3, ed e' definitoria perche' e' quella che ha prodotto
i `punti_osservati`. WhoScored resta un predittore (`falli_per_90`), mai il
bersaglio.
""")

    # ---------------------------------------------------------------- 7
    p.append("\n## 7. La valutazione, sulle stesse quattro transizioni\n")
    p.append(_tab(ris["tabella"], {"mae_punti": 4, "divario_chiuso_pct": 2}))
    p.append("\nPotenza e MDE, dichiarati con lo stesso disegno appaiato di (b):\n")
    p.append(_tab(ris["mde"], {"delta_mae": 4, "se": 4, "t": 3, "mde_mae": 4,
                               "mde_quota_divario_pct": 2}))
    p.append(f"""
Divari sul campione **fisso** di 2.678 righe: voto {ris['divari']['voto']:.3f} ·
bonus {ris['divari']['bonus']:.3f} · entrambi {ris['divari']['entrambi']:.3f}
punti di MAE.

**Le feature da dati evento non aggiungono niente, e sono negative in tutte e tre
le varianti.** Nessuna si avvicina alla propria soglia: |t| massimo 1,55 contro
un MDE dell'11-14% del divario. Il test **non** avrebbe visto un effetto sotto
quella taglia, e va letto cosi' — esclude effetti grandi su un divario che e'
gia' piccolo, non dimostra che l'effetto sia zero.

**L'unica cosa che si muove e' QI da solo**: 10,5% del divario, `t = 2,31`.
Passa la soglia a due code del 5% (1,96) e **non passa Bonferroni** su sei
varianti, che chiede |t| > 2,64. Va riportato come suggestivo e non come
risultato, ed e' esattamente lo standard che (b) ha fissato per se stesso.

**Il contrasto con (b) e' il fatto piu' interessante della sezione.** Li' QI da
solo era *peggio* del modello completo (-0,18%) ed era un complemento; qui QI da
solo e' *meglio* di QI piu' le feature evento (10,5% contro 2,0%). Le feature
evento non sono neutre: peggiorano.
""")
    p.append("\nL'errore separato per ruolo, con la variante «E4 voto + bonus»:\n")
    p.append(_tab(per_r, {"mae_base": 3, "mae_nuovo": 3, "delta": 4}))
    p.append("\nE la sensibilita' al pavimento di addestramento, che e' dichiarato "
             "e non stimato:\n")
    p.append(_tab(sens_pav, {"mae_punti": 4, "divario_chiuso_pct": 2}))

    # ---------------------------------------------------------------- 8
    p.append("\n## 8. Domande aperte\n")
    p.append("""
1. **Il rating WhoScored non e' nel repository.** La specifica di E4.1 lo chiedeva
   come regressore e non c'e': nessuna delle 259 colonne lo contiene, e le pagine
   grezze non sono state conservate — `createEventsDF` tiene solo gli eventi. E'
   la **terza** domanda della stessa famiglia, e va tenuta appaiata alle altre
   due: **numero di maglia d'agosto** (E2) e **FVM pre-stagione** (E3). Sono tre
   valori che la fonte pubblica, che si acquisirebbero, e che il repository non
   ha; se un giorno si risponde a una si risponde a tutte e tre.
2. **Perche' le feature evento peggiorino invece di essere neutre** non ha una
   spiegazione misurata. Il sospetto e' la solita ridondanza — il modello d'asta
   usa gia' la storia del giocatore, e npxG di t-1 e' un altro modo di dirla — ma
   qui, a differenza delle code di E2, la ridondanza non e' stata misurata contro
   il set del modello d'asta. E' il controllo che manca.
3. **Il divario corretto va riportato all'indietro.** `CLAUDE.md` e i report del
   modello d'asta e di E2 citano il 61,4 -> 52,5 come divario dei bonus. Il numero
   e' riproducibile e resta in tabella, ma la sua **lettura** cambia, e i punti in
   cui e' citato andrebbero rivisti insieme.
4. **Il designato dei rigori per il 2026-27** e' un input che nessuna fonte
   acquisita contiene, e vale fino a 15 punti sul singolo giocatore.
5. **Gli infortuni**, che restano fuori da entrambe le fonti e che dopo E4 sono il
   limite dichiarato del progetto invece che uno fra tanti.
""")

    OUT_MD.write_text("\n".join(p) + "\n", encoding="utf-8")
    print(f"\nscritto {OUT_MD}")


if __name__ == "__main__":
    main()
