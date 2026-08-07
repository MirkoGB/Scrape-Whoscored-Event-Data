# -*- coding: utf-8 -*-
"""Fase 9 / Blocco E3 — la difesa.

    ./.venv/Scripts/python.exe scripts/run_fase9_e3.py [--force]

**Non tocca la rete.** Legge i Parquet di E0, i voti e i listoni; produce il
modello di squadra sui gol (rivalidato per conto suo), la porta inviolata come
probabilita', il voto della linea condizionato alla forza difensiva, la
correlazione dentro la linea e la verifica sui portieri.

`--force` rifa' il walk-forward dei gol (~25 s); senza, lo rilegge dalla cache.
"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sot import config, difesa as DF  # noqa: E402

OUT_MD = config.REPORTS / "fase9_e3_difesa.md"


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

    print("gol ricomposti col punteggio vero...")
    gsp = DF.gol_squadra_partita()
    ver = DF.verifica_punteggio(gsp=gsp)

    print("E3.1 modello di squadra sui gol (walk-forward)...")
    wf = DF.walkforward_gol(force=force)
    val = DF.valutazione_gol(wf)
    conf = DF.confronto_appaiato_gol(wf)
    forma = DF.forma_predittiva_gol(wf)

    print("E3.2 porta inviolata...")
    pi = DF.porta_inviolata(wf)

    print("E3.3 voto della linea...")
    v = DF.voti_difensori(wf=wf)
    cond = DF.voto_condizionato(v)
    pend = DF.pendenza_voto(v)

    print("E3.4 correlazione dentro la linea...")
    corr = DF.correlazione_linea(v)
    eff = DF.effetto_correlazione()

    print("verifica: i portieri...")
    prem = DF.premessa_portieri()
    sp = DF.spearman_portieri()

    print("E3.5 coda: le due componenti del portiere...")
    comp = DF.componenti_portiere(v=v)
    pcomp = DF.pendenza_componenti(comp)
    ccomp = DF.correlazione_componenti(comp)
    due = DF.collegamento_due_lati(c=comp)
    qual = DF.qualita_componente_difensiva()

    for nome, df in (("fase9_e3_punteggio_verifica", ver),
                     ("fase9_e3_valutazione_gol", val),
                     ("fase9_e3_confronto_gol", conf),
                     ("fase9_e3_porta_inviolata", pi),
                     ("fase9_e3_voto_condizionato", cond),
                     ("fase9_e3_pendenza_voto", pend),
                     ("fase9_e3_correlazione_linea", corr),
                     ("fase9_e3_effetto_correlazione", eff),
                     ("fase9_e3_premessa_portieri", prem),
                     ("fase9_e3_spearman", sp),
                     ("fase9_e3_5_pendenza_componenti", pcomp),
                     ("fase9_e3_5_correlazione_componenti", ccomp),
                     ("fase9_e3_5_due_lati", due),
                     ("fase9_e3_5_qualita_componente", qual)):
        df.to_csv(config.REPORTS / f"{nome}.csv", index=False)

    rho = float(eff["rho"].iloc[0])
    n_val = int(wf["eligible"].sum())
    pit = forma["pit"]
    sp_p = sp[sp["ruolo"] == "p"].set_index("candidato")

    # E3.5, i numeri che decidono l'ipotesi
    pc = pcomp[pcomp["ruolo"] == "p"].set_index("componente")
    quota_malus = pcomp.attrs["quota_malus_superstite"]
    compensa = pcomp.attrs["compensazione"]
    cc = ccomp.set_index("pavimento_presenze")
    due_p = due.pivot(index="candidato", columns="soglia_presenze_attese",
                      values="spearman")
    q = qual.set_index("stimatore")
    q_sto = q.loc["bonus storico del portiere (il modello d'asta)"]
    q_e3 = q.loc["difesa E3 (modello di squadra)"]

    testo = f"""# Fase 9 / Blocco E3 — la difesa

> Generato da `scripts/run_fase9_e3.py` il {date.today().isoformat()}.
> Nessuna richiesta di rete.

## In breve

| | esito |
|---|---|
| E3.1 modello di squadra sui gol | **funziona**: batte il baseline migliore per **t = {conf['t'].iloc[0]:.2f}** |
| E3.2 porta inviolata come probabilita' | **funziona**: pendenza **{pi['calib_slope'].iloc[0]:.3f} ± {pi['calib_se'].iloc[0]:.3f}**, Brier {pi['brier'].iloc[0]:.4f} contro {pi['brier'].iloc[2]:.4f} |
| E3.3 voto della linea condizionato | **effetto reale e grande**: {pend[(pend.ruolo=='d') & (pend.regressore=='lam_subiti (previsto)')]['delta_p10_p90'].iloc[0]:.3f} di voto sui difensori |
| E3.3 sui **portieri** | **segno OPPOSTO**, e non era previsto |
| E3.4 correlazione dentro la linea | misurata: **{rho:.3f}**, e il segno del suo effetto **si inverte** |
| **verifica sui portieri** | **FALLISCE**: la difesa di squadra non e' cio' che separa i portieri |
| E3.5 coda — la compensazione voto/malus | **ipotesi CONFUTATA**: sopravvive il **{100 * quota_malus:.0f}%** del malus, non un terzo |
| E3.5 coda — collegare **entrambi** i lati | non recupera niente, **nemmeno con la pendenza oracolo** |
| E3.5 coda — la difesa di E3 come stimatore | **e' il migliore dei due**: MAE {q_e3['mae']:.3f} contro {q_sto['mae']:.3f} dello storico |

**Il blocco produce quattro strumenti che funzionano e una verifica finale che
li boccia**, ed e' il risultato piu' informativo possibile: la causa che il
blocco del modello d'asta dava per **identificata** — *i punti di un portiere
dipendono dalla difesa della sua squadra, e quel modello non guarda la squadra*
— **e' stata provata e non regge**.

## 0. Gli autogol, e il punteggio vero

`team_match.goals` **non e' il punteggio**: `shots.shots_mask` esclude gli autogol
dai tiri, quindi un autogol non compare da nessuna parte. Per i tiri in porta e'
giusto; per i **gol subiti** e' un errore, e per il fantacalcio doppiamente,
perche' il portiere il gol lo prende comunque.

L'attribuzione **e' verificata, non assunta**: l'evento `Goal` con `isOwnGoal`
porta il `teamId` della squadra che lo **subisce**.

{_tab(ver)}

**{int(ver['gol_fatti_esatti'].sum())} righe su {int(ver['righe'].sum())}, in entrambe le direzioni**, contro le
{int(ver['senza_autogol_esatti'].sum())} che si otterrebbero ignorando gli autogol. La fonte del confronto e'
`matches.json`, che porta il punteggio **dichiarato** e non ricostruito dagli
eventi: e' cio' che rende questa una verifica e non una tautologia. La simmetria
interna (i gol fatti di un lato sono i gol subiti dell'altro) regge ovunque e non
usa la fonte esterna, quindi vale anche dove `matches.json` non arriva.

## 1. E3.1 — il modello di squadra sui gol, rivalidato per conto suo

Stessa specificazione della Fase 2 — `mu + attacco_i + difesa_j + gamma*casa`,
ridge, emivita 150 giorni, alpha scelto in walk-forward sul solo passato — e
**bersaglio diverso**. L'unica cosa che cambia e' `target`: se cambiasse anche la
specificazione non si saprebbe a cosa attribuire la differenza.

**La validazione non si eredita.** Che il modello sia calibrato sui tiri in porta
non dice niente sui gol: sono conteggi con media tre volte piu' bassa, il 28% di
zeri e una dispersione diversa. Ereditare la validazione della Fase 2 sarebbe
leggere male il vincolo 7. Il walk-forward e' **dentro la stagione** e le
previsioni si impilano dopo — le squadre cambiano fra stagioni, e un decadimento
di 150 giorni attraverso l'estate darebbe a settembre un training fatto di maggio.

**{n_val} righe valutate** su cinque stagioni.

{_tab(val[['modello', 'n', 'mae', 'bias', 'corr', 'sharpness', 'calib_slope',
           'calib_se', 'calib_z_vs_1', 'brier', 'brier_base']],
      {'mae': 3, 'bias': 3, 'corr': 3, 'sharpness': 3, 'calib_slope': 3,
       'calib_se': 3, 'calib_z_vs_1': 2, 'brier': 4, 'brier_base': 4})}

{_tab(conf, {'mae_baseline': 4, 'mae_modello': 4, 'delta_mae': 4, 't': 2, 'se': 4})}

**Qui il modello si giustifica anche sull'accuratezza, e sui tiri non era cosi'.**
Sul MAE batte il baseline migliore per **t = {conf['t'].iloc[0]:.2f}**; nella Fase 2, sullo
stesso confronto e con la stessa procedura, il margine valeva t = 1.86, cioe'
dentro il rumore. **Non e' un modello migliore: e' un bersaglio piu' facile da
distinguere.** I gol dipendono dall'avversario molto piu' dei tiri in porta, che
sono in gran parte "quanto tira questa squadra".

Sulla **calibrazione** si ritrova invece il fatto della Fase 4, piu' netto: i due
baseline informativi stanno a {val['calib_slope'].iloc[1]:.3f} e {val['calib_slope'].iloc[2]:.3f} con z sotto −11, cioe' danno
previsioni **troppo estreme** perche' una media campionaria non regredisce verso
il centro. Il modello sta a {val['calib_slope'].iloc[0]:.3f} ± {val['calib_se'].iloc[0]:.3f} (z = {val['calib_z_vs_1'].iloc[0]:.2f}), appena sotto 1.

**La forma dell'intera distribuzione**, che la pendenza non controlla: PIT
randomizzato chi2 = {pit['chi2']:.2f} su {pit['dof']} gdl, **p = {pit['p_value']:.3f}**. Gli zeri osservati sono il
{100 * forma['quota_zeri_osservata']:.1f}% contro il {100 * forma['quota_zeri_attesa']:.1f}% atteso — ed e' il controllo che conta di piu' qui,
perche' la porta inviolata **e'** lo zero.

{_tab(forma['copertura'], {'copertura': 3, 'ampiezza_media': 2})}

La copertura e' conservativa, com'e' strutturale sui conteggi (stesso esito della
Fase 4).

**I gol non sono sovradispersi**: var/media 1.03 e la `r` NB2 stimata sul solo
passato resta appiccicata al suo massimo. E' il motivo per cui in E3.2 la Poisson
e la NB2 danno lo stesso numero — **misurato, non assunto**.

## 2. E3.2 — la porta inviolata come probabilita'

`P(gol subiti = 0)` per squadra-partita, non frequenza storica. La differenza non
e' formale: la frequenza dice *"questo portiere ha fatto il 28% di clean sheet"*,
la probabilita' dice *"contro questo avversario, in casa, e' il 34%"* — e solo la
seconda si somma sul calendario vero.

{_tab(pi, {'p_media': 3, 'osservato': 3, 'brier': 4, 'logloss': 4,
           'calib_slope': 3, 'calib_se': 3})}

**Il modello e' calibrato e i baseline no**, esattamente come sui gol: pendenza
{pi['calib_slope'].iloc[0]:.3f} ± {pi['calib_se'].iloc[0]:.3f} contro {pi['calib_slope'].iloc[2]:.3f} della frequenza storica, che e' **troppo
estrema** di dieci errori standard.

**La frequenza storica grezza e' un estimatore degenere, e sta in tabella per
mostrarlo.** Una squadra che dopo sei giornate non ha ancora tenuto la porta
inviolata riceve `p = 0` esatto, cioe' «impossibile»: il log-loss ne esce a
{pi['logloss'].iloc[3]:.3f} contro {pi['logloss'].iloc[2]:.3f} della versione smorzata, e la pendenza non e' nemmeno
identificabile. Il baseline usato nel confronto e' quindi quello **smorzato**
verso la media di campionato del solo passato, perche' il vincolo 6 chiede un
avversario serio: batterne uno degenere non dimostrerebbe niente.

## 3. E3.3 — il voto della linea, condizionato alla forza difensiva

E' l'ingresso del modificatore, che vale fino a +6. La domanda: **di quanto si
muove il voto base quando cambia la forza difensiva della squadra?**

{_tab(cond, {'lam_subiti_medio': 3, 'voto_medio': 3, 'sd_voto': 3})}

{_tab(pend, {'pendenza': 4, 'se': 4, 't': 2, 'delta_p10_p90': 3})}

**Sui difensori l'effetto e' reale e grande**: dal decimo al novantesimo
percentile della forza difensiva attesa il voto base si muove di
{abs(pend[(pend.ruolo=='d') & (pend.regressore=='lam_subiti (previsto)')]['delta_p10_p90'].iloc[0]):.3f},
con t = {pend[(pend.ruolo=='d') & (pend.regressore=='lam_subiti (previsto)')]['t'].iloc[0]:.1f}. Con le fasce a 6,00 / 6,50 / 7,00 un quarto di punto di voto
medio di linea e' esattamente cio' che sposta una fascia.

> **Sui portieri il segno e' OPPOSTO, ed e' significativo.** Un portiere di una
> difesa attesa **debole** prende un voto base piu' **alto**
> (pendenza {pend[(pend.ruolo=='p') & (pend.regressore=='lam_subiti (previsto)')]['pendenza'].iloc[0]:+.4f}, t = {pend[(pend.ruolo=='p') & (pend.regressore=='lam_subiti (previsto)')]['t'].iloc[0]:.2f}), mentre a **gol subiti osservati** il suo voto
> scende ({pend[(pend.ruolo=='p') & (pend.regressore=='gol_subiti (osservato)')]['pendenza'].iloc[0]:+.4f}, t = {pend[(pend.ruolo=='p') & (pend.regressore=='gol_subiti (osservato)')]['t'].iloc[0]:.1f}). Non e' una contraddizione: il portiere e'
> **giudicato rispetto all'attesa**. Chi para molto perche' la sua difesa lo
> espone viene premiato per le parate; chi prende gol viene punito per i gol.
> **Non era previsto e non e' stato aggiustato.**

Le due colonne `lam_subiti (previsto)` e `gol_subiti (osservato)` stanno insieme
apposta: **solo la prima e' disponibile quando serve.** La seconda dice quanto
piu' grande sarebbe l'effetto conoscendo il risultato, cioe' il tetto di cio' che
un modello di squadra migliore potrebbe recuperare — sui difensori {abs(pend[(pend.ruolo=='d') & (pend.regressore=='gol_subiti (osservato)')]['delta_p10_p90'].iloc[0]):.3f} contro
{abs(pend[(pend.ruolo=='d') & (pend.regressore=='lam_subiti (previsto)')]['delta_p10_p90'].iloc[0]):.3f}, cioe' circa il triplo.

## 4. E3.4 — la correlazione dentro la linea

`modificatore.simula_linea` estraeva i membri della linea in modo indipendente e
lo dichiarava come limite. Finche' resta dichiarato e non stimato, e' un'ipotesi.

{_tab(corr, {'dimensione_media': 2, 'icc': 3, 'sd_entro': 3})}

**La correlazione c'e' e non e' piccola: {rho:.3f}** sulla linea intera. Ed e'
**genuina co-variazione di giornata, non composizione della rosa**: togliendo la
media di ogni giocatore passa da {corr[(corr.insieme=='linea intera (p+d)') & (corr.voto=='grezzo')]['icc'].iloc[0]:.3f} a {rho:.3f}, cioe' **non si muove**. Se
fosse "le difese forti hanno difensori bravi" sarebbe crollata, perche' quella
parte e' gia' dentro `mu` nella simulazione e verrebbe contata due volte. E'
quindi la riga giusta da iniettare nel simulatore.

`simula_linea` ha ora un parametro `rho`, **0 di default**: un test verifica che
con `rho=0` l'uscita sia identica bit per bit a prima che il parametro esistesse.
La correlazione entra con un fattore comune, che e' la struttura giusta per un
gruppo **senza ordine** — non c'e' un "primo" e un "secondo" difensore.

{_tab(eff[eff.n_difensori == 4][['voto_medio_linea', 'bonus_indipendenti',
                                 'bonus_correlati', 'delta_per_giornata',
                                 'delta_stagione']],
      {'voto_medio_linea': 2, 'bonus_indipendenti': 4, 'bonus_correlati': 4,
       'delta_per_giornata': 4, 'delta_stagione': 2})}

> **Il segno si inverte, e questo era il punto.** Sotto i 6,60 di voto medio di
> linea la correlazione **aumenta** il bonus atteso, fino a +6 punti di stagione;
> sopra i 6,90 lo **riduce**, fino a −8,8. Il meccanismo e' la forma della scala:
> le fasce sono convesse crescenti (−1 / +1 / +3 / +6), quindi piu' varianza aiuta
> — **finche' non si e' dentro l'ultima**, che non ha nulla sopra di se', e da li'
> la varianza puo' solo far uscire. Il punto di inversione sta intorno a 6,7.

Ne segue che la simulazione indipendente **non era conservativa**: sbagliava in
un verso o nell'altro a seconda della linea, come gia' `costo_della_media` aveva
trovato per la scorciatoia sulle medie di stagione. `sd` e `p_voto` sono tenuti
fissi e dichiarati: qui si isola la **correlazione**, non si ricalibra il
modificatore.

## 5. La verifica che chiude il blocco — i portieri

Riportata **separata** per ruolo e mai annegata nella metrica complessiva: i
portieri sono ~12% del listone.

**Prima una precisazione sui numeri di riferimento.** Il blocco del modello
d'asta pubblica *"sui portieri il modello fa 0 e il FVM 0,667"*, e quella e' la
**precisione sui primi N**, non lo Spearman: lo Spearman sui portieri non era mai
stato pubblicato, e vale {sp_p.loc["modello d'asta", 'spearman']:.3f}. Le due cose vanno tenute distinte, e qui
ci sono entrambe.

{_tab(sp[sp.ruolo == 'p'][['candidato', 'stagioni', 'spearman', 'min', 'max',
                           'precisione_top']],
      {'spearman': 3, 'min': 3, 'max': 3, 'precisione_top': 3})}

**La sostituzione peggiora.** Rimpiazzare la componente difensiva del bonus del
portiere — gol subiti e porta inviolata, le due voci che dipendono dalla squadra —
con quella derivata dal modello di squadra porta lo Spearman da
{sp_p.loc["modello d'asta", 'spearman']:.3f} a {sp_p.loc["modello d'asta + difesa E3 (ultima stagione)", 'spearman']:.3f}, e la precisione resta **0**. Voto base e presenze attese
non sono stati toccati, quindi la differenza e' attribuibile alla sola
sostituzione. **Vale con entrambe le forme della forza difensiva** (ultima
stagione e tutte), quindi non dipende da quella scelta.

### Perche', e qui il blocco consegna la cosa piu' utile che ha

{_tab(prem, {'quota_mai_in_campo': 3, 'spearman_modello': 3,
             'spearman_con_difesa_e3': 3, 'spearman_sole_presenze_attese': 3,
             'spearman_qi': 3, 'spearman_fvm_CONTAMINATO': 3})}

Quattro letture, in ordine:

1. **La premessa del blocco era falsa per la popolazione che conta.**
   L'argomento era: *un portiere titolare gioca quasi tutto, quindi le presenze
   sono quasi risolte e l'errore sta altrove.* Vero per il titolare, falso per i
   **quotati**: il {100 * prem['quota_mai_in_campo'].iloc[0]:.0f}% dei portieri a listino non gioca **nemmeno una
   partita**. Fra tutti i quotati, ordinare per **sole presenze attese** da'
   {prem['spearman_sole_presenze_attese'].iloc[0]:.3f} contro {prem['spearman_modello'].iloc[0]:.3f} del modello intero: il modello sui portieri
   **e' gia' quasi solo un modello di presenze**.
2. **Fra i probabili titolari non funziona piu' niente.** Alzando la soglia a 20
   presenze attese restano {int(prem[prem.soglia_presenze_attese == 20]['portieri'].iloc[0])} portieri, di cui solo il {100 * prem[prem.soglia_presenze_attese == 20]['quota_mai_in_campo'].iloc[0]:.0f}% non gioca: le
   presenze sono davvero risolte li'. E il modello crolla a
   {prem[prem.soglia_presenze_attese == 20]['spearman_modello'].iloc[0]:.3f}, le sole presenze a {prem[prem.soglia_presenze_attese == 20]['spearman_sole_presenze_attese'].iloc[0]:.3f}, la difesa di E3 a
   {prem[prem.soglia_presenze_attese == 20]['spearman_con_difesa_e3'].iloc[0]:.3f}. **Tolte le presenze, nessuno dei nostri candidati sa niente.**
3. **La quotazione non crolla come il resto, e QI e' quella che conta.** Fra i
   probabili titolari **QI** fa {prem[prem.soglia_presenze_attese == 20]['spearman_qi'].iloc[0]:.3f} — contro {prem[prem.soglia_presenze_attese == 20]['spearman_modello'].iloc[0]:.3f} del modello e
   {prem[prem.soglia_presenze_attese == 20]['spearman_sole_presenze_attese'].iloc[0]:.3f} delle sole presenze. E' l'unica cosa sopra lo zero li' dentro,
   ed e' informazione **disponibile prima dell'asta**. Il vantaggio della
   quotazione sui portieri **non e' sapere chi gioca**: sopravvive proprio dove le
   presenze sono risolte.
4. **Ma il numero che questo report citava era un altro, e non era leale.**

> ### CORREZIONE — il {prem[prem.soglia_presenze_attese == 20]['spearman_fvm_CONTAMINATO'].iloc[0]:.3f} del FVM era contaminato
>
> Questa sezione affermava *«ma il FVM non crolla: {prem[prem.soglia_presenze_attese == 20]['spearman_fvm_CONTAMINATO'].iloc[0]:.3f}, ed e' il numero
> decisivo del blocco»*, e ne ricavava che il FVM sapesse qualcosa di ignoto sui
> portieri. **Il FVM della pagina archiviata si muove durante la stagione**
> (`quotazioni.orologio()`, §3-bis del report del modello d'asta), quindi per una
> stagione passata ne conosce l'esito. Il numero resta in tabella, marcato
> `CONTAMINATO`: e' un errore di questo progetto e non si cancella.
>
> **Rifatto con QI, che e' pulito, il vantaggio regge ma si riduce di molto**:
> {prem[prem.soglia_presenze_attese == 20]['spearman_qi'].iloc[0]:.3f} invece di {prem[prem.soglia_presenze_attese == 20]['spearman_fvm_CONTAMINATO'].iloc[0]:.3f}. Ed e' la risposta alla domanda aperta n. 1: **non
> era solo "sapeva come era andata la stagione"** — una quotazione che non puo'
> saperlo sta comunque a {prem[prem.soglia_presenze_attese == 20]['spearman_qi'].iloc[0]:.3f} dove tutto il nostro sta a zero — **ma la
> maggior parte di quel {prem[prem.soglia_presenze_attese == 20]['spearman_fvm_CONTAMINATO'].iloc[0]:.3f} era esattamente quello**. La domanda sopravvive
> piu' piccola e meglio posta.
>
> Sulla **precisione sui primi N** il divario invece **non e' misurabile**: il
> modello fa 0 e QI fa 0,000 o 0,083 **a seconda di come si sciolgono i pari
> merito** — QI e' un prezzo intero e in **due stagioni su quattro** ci sono pari
> merito al confine dei primi tre (2024-25 ha 15 e 15 al terzo e quarto posto,
> 2025-26 ha quattro 16 per tre posti), quindi quali tre entrano lo decide il
> sorteggio. Con 3 posti per 4 stagioni la metrica ha passi da 1/12, e le due
> implementazioni del repository danno i due valori per quella ragione. **E' la
> risoluzione della metrica, non un risultato**, e su quel piano il divario col
> FVM contaminato
> (0,667) resta l'unica cosa grande — cioe' l'unica cosa che la contaminazione
> spiegava.

> **La causa data per identificata non regge.** Il blocco del modello d'asta
> scriveva che i punti di un portiere dipendono dalla difesa della sua squadra e
> che il modello non la guarda. La prima meta' e' vera — E3.2 e E3.3 la misurano —
> ma **la seconda non e' la spiegazione dello Spearman**: dare al modello la
> difesa della squadra, con un modello di squadra validato per conto suo, non
> migliora l'ordinamento dei portieri. **Cio' che la quotazione sa sui portieri
> resta ignoto, ed e' ora una domanda molto piu' stretta di prima** — vale
> {prem[prem.soglia_presenze_attese == 20]['spearman_qi'].iloc[0]:.3f}, non {prem[prem.soglia_presenze_attese == 20]['spearman_fvm_CONTAMINATO'].iloc[0]:.3f}.

## 5-bis. E3.5 — la coda: perche' la difesa peggiora, e l'ipotesi che non regge

E3.3 aveva lasciato un segno opposto sui portieri, e da li' nasceva una
spiegazione dell'esito negativo: **dietro una difesa debole il portiere para di
piu' e il voto sale, il malus dei gol subiti scende, le due voci si compensano e
il netto e' quasi piatto** — quindi collegare la difesa a un solo lato dei due
peggiora, perche' aggiunge meta' compensazione senza l'altra meta'.

E' un'ipotesi con tre conseguenze, e si misurano separate perche' possono cadere
una per volta. La soglia della seconda **e' dichiarata prima di guardare**: la
compensazione si chiama completa se nel netto sopravvive meno di **un terzo** del
malus.

### Le due componenti, e quale fonte alimenta il malus

`comp_voto` e' il voto base (la componente di E3.3); `comp_bonus` e'
`-1 x gol subiti + 1 x porta inviolata` in punti di lega, cioe' le due voci di
`lega.BONUS` che dipendono dalla squadra. **Per il difensore `comp_bonus` e' zero
per regolamento**, non per approssimazione: un difensore non prende malus sui gol
subiti. E' gia' meta' della risposta — il difensore ha **un canale**, il portiere
**due**, e i due hanno segno opposto.

**Il malus lo alimenta la fonte dei VOTI** (`difesa.FONTE_MALUS`), non i gol
ricomposti da WhoScored: e' la fonte definitoria, quella che ha prodotto i
`punti_osservati`. Non e' una formalita', perche' `voti_difensori` **sovrascrive**
`gol_subiti` con i gol di squadra (autogol compresi) e le due colonne, che hanno
lo stesso nome, differiscono su **{comp.attrs['righe_gol_subiti_discordi']} righe su {int((comp['ruolo'] == 'p').sum())}**, sempre nel verso di
WhoScored che ne conta di piu'.

{_tab(pcomp, {"pendenza": 4, "se": 4, "t": 2, "delta_p10_p90": 4})}

**La conseguenza 1 regge**, ed e' il controllo che le componenti stiano sulla
stessa popolazione di E3.3: la pendenza del voto sul portiere e'
{pc.loc['comp_voto', 'pendenza']:+.4f} con t = {pc.loc['comp_voto', 't']:+.2f}, cioe' il numero di E3.3 riprodotto.

**La conseguenza 2 cade, e non di poco.** Il malus si muove di
{pc.loc['comp_bonus', 'pendenza']:+.4f} per unita' di gol attesi, il voto base lo compensa di
{pc.loc['comp_voto', 'pendenza']:+.4f}, e nel netto sopravvive **{100 * quota_malus:.1f}%** del malus — contro la
soglia del 33% dichiarata. Il netto ha pendenza {pc.loc['comp_netto', 'pendenza']:+.4f} con
**t = {pc.loc['comp_netto', 't']:+.1f}**: non e' piatto, e' quasi tutto il malus. Dal decimo al
novantesimo percentile della forza difensiva attesa un portiere perde
{abs(pc.loc['comp_netto', 'delta_p10_p90']):.2f} punti **per partita**, che su una stagione da titolare sono
una trentina di punti. **La compensazione esiste e vale il {100 * (1 - quota_malus):.0f}% del malus, non i due
terzi che servivano.**

### La conseguenza 3, e la trappola dei totali

{_tab(ccomp, {"corr_medie": 3, "corr_totali": 3, "sd_voto": 3, "sd_bonus": 3,
              "sd_netto": 3, "compressione_vs_indipendenza": 3})}

**Attraverso i portieri le due componenti non sono correlate negativamente: non
sono correlate affatto.** Sulle medie per presenza si passa da
{cc.loc[1, 'corr_medie']:+.3f} con un pavimento di una presenza a {cc.loc[10, 'corr_medie']:+.3f} e {cc.loc[19, 'corr_medie']:+.3f} sopra le dieci e le
diciannove, cioe' zero appena si pretende che la media di bonus sia un tasso e non
un conteggio di gol.

> **La colonna `corr_totali` e' li' per essere squalificata, non per essere
> letta.** Sui totali di stagione la correlazione e' fortemente negativa
> ({cc.loc[10, 'corr_totali']:+.3f} a dieci presenze) e sembrerebbe la conferma cercata. Non lo e':
> il totale del voto **cresce** col numero di presenze e quello del bonus **cala**
> (ogni presenza in piu' porta altri gol subiti), quindi i totali si correlano
> negativamente **attraverso le presenze** anche se le due componenti fossero
> indipendenti. E' la stessa forma di errore che il progetto ha gia' incontrato su
> `possession` e `field_tilt` in E0, dove una media di 0.500 esatta era una
> proprieta' della definizione e non un risultato.

### La conseguenza operativa, misurata comunque

Se la compensazione fosse il meccanismo, collegare **entrambe** le componenti
dovrebbe recuperare cio' che collegarne una sola perde. E3 aveva collegato solo il
bonus, lasciando `voto_atteso` indipendente dalla squadra.

{_tab(due_p.reset_index(), {c: 3 for c in due_p.columns})}

**Non recupera niente.** A soglia zero collegare entrambi i lati da'
{due_p.loc['entrambi i lati', 0]:.3f} contro {due_p.loc["solo bonus — e' E3", 0]:.3f} di E3 e {due_p.loc["modello d'asta (nessun lato)", 0]:.3f} del modello che non
collega nulla; fra i probabili titolari {due_p.loc['entrambi i lati', 20]:.3f} contro {due_p.loc["modello d'asta (nessun lato)", 20]:.3f}. La riga
**pendenza ORACOLO** — la pendenza stimata su tutte e cinque le stagioni, bersaglio
compreso, che come ingrediente di una previsione e' un imbroglio dichiarato — fa
{due_p.loc['entrambi i lati (pendenza ORACOLO)', 0]:.3f}: **nemmeno conoscendo la risposta il lato del voto recupera**, ed e' il
modo di escludere che la questione sia la qualita' della stima della pendenza.

### E allora dove sta il problema — una cosa esclusa, il resto aperto

La spiegazione piu' semplice sarebbe che la componente difensiva di E3 stimi
peggio di cio' che ha sostituito. **Si misura, e non e' cosi'.**

{_tab(qual, {"mae": 4, "corr": 3, "corr_con_presenze": 3})}

Contro il bonus difensivo per presenza **effettivamente realizzato** nella
stagione bersaglio, la difesa di E3 fa MAE {q_e3['mae']:.4f} e correlazione {q_e3['corr']:+.3f};
il bonus storico del portiere, che e' cio' che il modello d'asta usa, fa
{q_sto['mae']:.4f} e {q_sto['corr']:+.3f}. **La componente di E3 e' lo stimatore migliore della
cosa che stima, e sostituirla peggiora l'ordinamento lo stesso.**

> Le due meta' della tabella hanno **due denominatori diversi**, ed e' voluto: la
> qualita' della stima si puo' misurare solo sui {int(q_e3['portieri_qualita'])} portieri che hanno giocato
> abbastanza da avere un tasso invece di un conteggio, mentre la correlazione con
> le presenze va misurata su **tutti** i {int(q_e3['portieri_tutti'])}, che sono la popolazione su cui la
> Spearman e' calcolata. Restringerla ai titolari troncherebbe proprio la
> variabile di cui si chiede la correlazione — ed e' l'errore che questa sezione
> aveva commesso in prima stesura, con il segno che ne usciva rovesciato.

L'unico canale per cui questo e' possibile e' che lo stimatore peggiore porti con
se' informazione su **quante partite** il portiere giochera', che e' cio' che
domina l'ordinamento dei punti di stagione. La colonna `corr_con_presenze` lo
misura, ed e' nel verso giusto ma piccola: {q_sto['corr_con_presenze']:+.3f} per il bonus storico contro
{q_e3['corr_con_presenze']:+.3f} per quello di E3. **Non basta a spiegare niente**, e va detto invece
di arrotondarlo verso l'alto: e' un indizio coerente col meccanismo, non una causa
dimostrata.

> **L'ipotesi era sbagliata, e la domanda resta aperta.** Il voto base del portiere
> si muove davvero nel verso opposto a quello dei difensori — quella meta' di E3.3
> regge — ma **non compensa il malus**: ne annulla il {100 * (1 - quota_malus):.0f}%, il netto resta
> ripido, e attraverso i portieri le due componenti sono scorrelate invece che
> compensarsi. Collegare entrambi i lati non recupera niente, nemmeno con la
> pendenza oracolo. **Cio' che questa coda aggiunge e' un'esclusione**: non e' che
> la difesa sia stimata male, perche' e' stimata meglio di cio' che ha sostituito.
> Perche' collegarla peggiori l'ordinamento resta senza spiegazione misurata.

## Cosa questo blocco lascia, e cosa no

**Quattro strumenti validati, che non dipendono dall'esito della verifica:**

* un modello di squadra sui **gol**, che batte i baseline con t = {conf['t'].iloc[0]:.1f} ed e'
  calibrato in distribuzione (PIT p = {pit['p_value']:.2f});
* la **porta inviolata come probabilita' per partita**, ben calibrata, che si
  somma sul calendario vero — cosa che una frequenza non fa;
* la **pendenza del voto** dei difensori sulla forza difensiva, che e' l'ingresso
  quantificato del modificatore;
* la **correlazione dentro la linea**, misurata e messa nel simulatore, col segno
  del suo effetto che si inverte a 6,7.

**Cosa NON e' stato fatto, di proposito**: non e' stato cercato un modo di far
sembrare positiva la verifica sui portieri. Il segno e' spiegato da un meccanismo
misurato — le presenze dominano l'ordinamento, e dove non dominano non c'e'
segnale nei nostri candidati — e ritoccare la sostituzione finche' lo Spearman
supera {sp_p.loc["modello d'asta", 'spearman']:.3f} cancellerebbe la spiegazione invece di trovarne una.

## 6. Due cose portate dentro dal blocco precedente

**L'xG non entra nel modello dei gol, quindi il problema dei cinque fit non si
pone.** Era la condizione posta: `xg_per_90` ha cinque fit che sono **cinque
modelli, non cinque livelli**, e un effetto di stagione lo copre solo se la
differenza e' un'intercetta — cosa non verificata. La specificazione di E3.1 e'
`mu + attacco_i + difesa_j + gamma*casa` e **non contiene xG in nessuna forma**:
la parola non compare in `sot/difesa.py`. Non e' una svista da colmare — e' la
stessa specificazione della Fase 2, e cambiarla insieme al bersaglio avrebbe reso
impossibile attribuire la differenza. Se un blocco futuro volesse metterci l'xG,
**la verifica sull'intercetta va fatta prima**, e resta da fare.

**Il malus dei cartellini e' alimentato dalla fonte dei VOTI, ed e' definitorio.**
`fantapunti.con_fantavoto_lega` calcola il malus dalle colonne `ammonizione` ed
`espulsione` della tabella dei voti: e' quella fonte che ha prodotto i
`punti_osservati` contro cui tutto il progetto si misura. **WhoScored non tocca i
punti in nessun punto della catena.** Ne segue che le 42 ammonizioni di scarto del
2023-24 non sono una scelta da fare fra due candidate — la fonte dei punti e' una
sola — ma **un difetto di WhoScored da spiegare**, e resta una domanda aperta di
E2 e non di E3. La stessa dichiarazione vale per la coda di E2
(`impiego.FONTE_CARTELLINI`), che usa i voti per la stessa ragione.

## Domande aperte

1. **Che cosa sa la QUOTAZIONE sui portieri.** Era formulata sul FVM e vale
   {prem[prem.soglia_presenze_attese == 20]['spearman_qi'].iloc[0]:.3f}, non {prem[prem.soglia_presenze_attese == 20]['spearman_fvm_CONTAMINATO'].iloc[0]:.3f}: la differenza fra i due era contaminazione. Resta la
   domanda piu' stretta che il progetto abbia — sopravvive al condizionamento
   sulle presenze e non e' la forza difensiva della squadra — ma su una metrica
   sola: sulla **precisione sui primi N** QI e il modello stanno entrambi a un
   pescaggio dallo zero, dentro la risoluzione della metrica. Restano gerarchia
   dichiarata dai club, mercato in corso e valutazione individuale del portiere:
   nessuna delle tre e' nel repository.
5. **Un valore pre-stagione dalla fonte, per il FVM e per il numero di maglia
   insieme.** Sono la **stessa domanda aperta**, non due: un valore d'agosto che i
   club e i listoni pubblicano e che il repository non ha. Il FVM pulito
   renderebbe leale un concorrente oggi squalificato; il numero di maglia d'agosto
   proverebbe l'argomento per cui quella feature di E2 esisteva. Vanno tenute
   appaiate — se un giorno si risponde a una si risponde all'altra.
2. **Il voto del portiere e' relativo all'attesa**, e questo blocco lo misura ma
   non lo modella. Un modello del voto base che tenesse conto dei **tiri
   affrontati** e non solo dei gol subiti e' la forma naturale, e i tiri in porta
   concessi ci sono gia' (`sot_conceded`).
3. **Il modificatore con `rho` acceso non e' stato ricalcolato** sulla lista
   d'asta: il parametro c'e' e la misura c'e', ma `run_asta_2627.py` continua a
   girare a `rho = 0`. Accenderlo cambia i contributi marginali in modo che
   dipende dalla linea, e va fatto come blocco a se'.
4. **La forza difensiva delle neopromosse** resta senza stima: la Serie B non e'
   nel repository, e la Fase 6E ha gia' misurato che assumerle "come le
   retrocesse" non e' neutro.
"""

    OUT_MD.write_text(testo, encoding="utf-8")
    print(f"\n-> {OUT_MD}")


if __name__ == "__main__":
    main()
