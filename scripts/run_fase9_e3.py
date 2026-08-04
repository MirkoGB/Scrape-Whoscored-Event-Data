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

    for nome, df in (("fase9_e3_punteggio_verifica", ver),
                     ("fase9_e3_valutazione_gol", val),
                     ("fase9_e3_confronto_gol", conf),
                     ("fase9_e3_porta_inviolata", pi),
                     ("fase9_e3_voto_condizionato", cond),
                     ("fase9_e3_pendenza_voto", pend),
                     ("fase9_e3_correlazione_linea", corr),
                     ("fase9_e3_effetto_correlazione", eff),
                     ("fase9_e3_premessa_portieri", prem),
                     ("fase9_e3_spearman", sp)):
        df.to_csv(config.REPORTS / f"{nome}.csv", index=False)

    rho = float(eff["rho"].iloc[0])
    n_val = int(wf["eligible"].sum())
    pit = forma["pit"]
    sp_p = sp[sp["ruolo"] == "p"].set_index("candidato")

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
             'spearman_fvm': 3})}

Tre letture, in ordine:

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
3. **Ma il FVM non crolla: {prem[prem.soglia_presenze_attese == 20]['spearman_fvm'].iloc[0]:.3f}.** Ed e' il numero decisivo del blocco.
   Il vantaggio del FVM sui portieri **non e' sapere chi gioca** — sopravvive
   intatto proprio dove le presenze sono note — e **non e' la forza difensiva
   della squadra**, perche' e' esattamente quello che E3 ha provato e che va nel
   verso sbagliato.

> **La causa data per identificata non regge.** Il blocco del modello d'asta
> scriveva che i punti di un portiere dipendono dalla difesa della sua squadra e
> che il modello non la guarda. La prima meta' e' vera — E3.2 e E3.3 la misurano —
> ma **la seconda non e' la spiegazione dello Spearman**: dare al modello la
> difesa della squadra, con un modello di squadra validato per conto suo, non
> migliora l'ordinamento dei portieri. **Cio' che il FVM sa sui portieri resta
> ignoto, ed e' ora una domanda molto piu' stretta di prima.**

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

1. **Che cosa sa il FVM sui portieri.** E' la domanda piu' stretta e piu' preziosa
   che il progetto abbia adesso: sopravvive al condizionamento sulle presenze
   (0,70 fra i probabili titolari) e non e' la forza difensiva della squadra.
   Restano gerarchia dichiarata dai club, mercato in corso e valutazione
   individuale del portiere — nessuna delle tre e' nel repository.
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
