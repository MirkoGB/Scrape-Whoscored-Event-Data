# -*- coding: utf-8 -*-
"""Fase 9 / Blocco E1 — la regola di costruzione delle feature, misurata.

    ./.venv/Scripts/python.exe scripts/run_fase9_e1.py [--force]

**Non tocca la rete e non scrive niente sotto `data/raw/`.** Legge i Parquet di
E0 (`player_match`, `team_match`), la cache degli eventi e la ricognizione del
Blocco 0, costruisce lo strato feature del giocatore in unita' grezze **e**
standardizzate, e misura per ogni candidata la deriva fra stagioni prima e dopo.

**Non stima niente**: nessun fit, nessun bersaglio, nessun iperparametro.

`--force` ricalcola la tabella invece di rileggerla dalla cache (~30 s).
"""

from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sot import config, features_giocatore as FG  # noqa: E402

OUT_MD = config.REPORTS / "fase9_e1_stabilita_feature.md"

# I qualifier che i blocchi successivi vorranno, piu' i due casi noti di
# dizionario cambiato. Stanno qui e non nel modulo perche' sono cio' che si
# **mostra** nel report, non cio' che le candidate dichiarano.
QUALIFIER_DA_MOSTRARE = ("CornerTaken", "FreekickTaken", "Penalty",
                         "ThrowIn", "BigChance", "KeyPass",
                         "StandingSave", "OtherBodyPart")


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


def _pct(x) -> str:
    """Percentuale con la virgola, come il resto dei report del progetto."""
    return f"{x:.1%}".replace(".", ",")


def _num(x, dec: int = 3) -> str:
    return f"{x:.{dec}f}".replace(".", ",")


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--force", action="store_true",
                   help="ricalcola la tabella feature invece di rileggerla")
    args = p.parse_args(argv)

    print("costruzione dello strato feature sulle cinque stagioni...")
    tavole = FG.costruisci(force=args.force)
    feat, rif = tavole["feature"], tavole["riferimenti"]
    print(f"  {len(feat)} righe (stagione, playerId, teamId), "
          f"{len(FG.CANDIDATE)} candidate")

    print("gate sui qualifier...")
    FG.controlla_qualifier_delle_candidate()
    qual = FG.verifica_qualifier(QUALIFIER_DA_MOSTRARE)

    print("deriva prima e dopo...")
    der = FG.deriva_feature(feat)
    scomp = FG.scomposizione_deriva(feat, rif)
    sens = FG.sensibilita_pavimento(feat)

    print("corollario sulle 72 colonne mai valorizzate...")
    mai = FG.colonne_mai_valorizzate()
    deriv = FG.derivazioni()

    for nome, df in (("fase9_e1_deriva", der),
                     ("fase9_e1_scomposizione", scomp),
                     ("fase9_e1_sensibilita_pavimento", sens),
                     ("fase9_e1_qualifier", qual),
                     ("fase9_e1_riferimenti", rif)):
        df.to_csv(config.REPORTS / f"{nome}.csv", index=False)

    # --- numeri che entrano nella prosa, calcolati e non scritti a mano ------
    per_verdetto = der["verdetto"].value_counts()
    n_grezze = int(per_verdetto.get(FG.VERDETTI[0], 0))
    n_std = int(per_verdetto.get(FG.VERDETTI[1], 0))
    n_stagione = int(per_verdetto.get(FG.VERDETTI[2], 0))
    non_risolte = FG.richiede_effetto_stagione(feat)
    sempre = sorted(sens.loc[sens["sempre_effetto_stagione"], "feature"])
    instabili = sorted(set(non_risolte) - set(sempre))
    peggiorate = der.loc[der["deriva_std"] > der["deriva_grezza"], "feature"].tolist()
    # Le quote di esposizione hanno una causa **loro**, identificata in §4: il
    # riferimento pesato non e' la quota del giocatore tipico, e' 11/rosa. Il
    # segno fra prima e ultima stagione le smisterebbe ora in un meccanismo ora
    # nell'altro, e sarebbe una classificazione che nasconde la causa vera.
    esposizione = sorted(f.nome for f in FG.CANDIDATE
                         if f.famiglia == "esposizione" and f.unita == "quota")
    opposti = set(scomp.loc[~scomp["stesso_verso"], "feature"])
    opposti_peggio = sorted((opposti & set(peggiorate)) - set(esposizione))
    sovracorrette = sorted(set(peggiorate) - opposti - set(esposizione))
    esposizione_peggio = sorted(set(esposizione) & set(peggiorate))
    # Le candidate il cui verdetto NON e' lo stesso su tutti e quattro i
    # pavimenti: e' la misura di quanto il risultato deve a una scelta.
    colonne_pav = [c for c in sens.columns if isinstance(c, float)]
    ballerine = sorted(sens.loc[sens[colonne_pav].nunique(axis=1) > 1, "feature"])
    tenute = (feat["minuti"] >= FG.MIN_MINUTI_DERIVA)
    quota_minuti = float(feat.loc[tenute, "minuti"].sum() / feat["minuti"].sum())

    d_ind = der.set_index("feature")
    s_ind = scomp.set_index("feature")
    q_ind = qual.set_index("qualifier")

    t_der = _tab(der[["feature", "famiglia", "prima", "ultima", "deriva_grezza",
                      "deriva_std", "verdetto"]],
                 {"prima": 3, "ultima": 3, "deriva_grezza": 3, "deriva_std": 3})
    t_scomp = _tab(scomp[["feature", "deriva_riferimento", "deriva_popolazione",
                          "stesso_verso"]],
                   {"deriva_riferimento": 3, "deriva_popolazione": 3})
    t_qual = _tab(qual[["qualifier", "stagioni", "min", "max", "rapporto", "ammesso"]],
                  {"min": 5, "max": 5, "rapporto": 2})
    t_deriv = _tab(deriv[["grandezza", "colonna_della_fonte", "derivazione", "feature"]])
    t_sens = _tab(sens[["feature", 270.0, 450.0, 900.0, 1800.0]].rename(
        columns={270.0: "270'", 450.0: "450'", 900.0: "900'", 1800.0: "1800'"}))
    t_reg = _tab(pd.DataFrame([
        {"feature": f.nome, "famiglia": f.famiglia, "unita": f.unita,
         "num / den": f"{f.num} / {f.den}", "descrizione": f.descrizione}
        for f in FG.CANDIDATE]))

    testo = f"""# Fase 9 / E1 — la regola delle feature, e dove non basta

Generato da `scripts/run_fase9_e1.py` il {date.today().isoformat()}.
**Nessuna richiesta di rete, niente scritto sotto `data/raw/`, nessuna stima.**

## Esito in una riga

La regola e' scritta, e' eseguibile ed e' **misurata**: su
{len(FG.CANDIDATE)} candidate, {n_grezze} possono entrare in unita' grezze
perche' non si muovono, {n_std} sono risolte dalla standardizzazione, e
**{n_stagione} non lo sono** — per quelle la stagione deve entrare come effetto
esplicito, che e' l'uscita che la regola stessa prevedeva.

Il risultato che non era scontato e' il **perche'**: la standardizzazione toglie
il *livello* di campionato e non puo' toccare la *forma* della distribuzione. Su
**{len(peggiorate)} candidate su {len(FG.CANDIDATE)}** dividere per la media di
campionato **aggiunge** deriva invece di toglierla, per due meccanismi distinti e
misurati in §4. E' il motivo per cui la regola non e' "standardizza tutto per
riflesso": la guardia **misura** invece di fidarsi del nome della colonna.

## 1. La regola

> Nessuna feature da dati evento entra in un modello multi-stagione in **unita'
> grezze**. Ogni feature entra come **scarto relativo alla media di campionato
> della propria stagione**:
>
> ```
> x_rel = x / m_s - 1
> ```
>
> Dove questo non basta, la stagione entra come **effetto esplicito**.

E' la stessa forma che `CLAUDE.md` prescrive per `rho` — "eccessi relativi alla
media di campionato della stagione, non scarti assoluti" — e nasce dalle stesse
misure: fra le cinque stagioni i tiri in porta per squadra-partita si sono mossi
del 9,2% **per ragioni di gioco**, `Clearance` +48%, `BallRecovery` -26%,
`Error` +162%, `shotCounter` da 3,4% a 7,7% dei tentativi.

**Non e' uno z-score, e la differenza conta.** Dividere anche per la deviazione
standard di stagione normalizzerebbe via la **dispersione**, che e' cio' che
distingue i giocatori, cioe' il segnale. Qui si toglie il livello e si lascia la
scala.

**La regola vive nello strato feature, non nel derivato.** `player_match` e
`team_match` restano in unita' grezze; un test verifica che nessuna colonna `_rel`
sia scesa li'. E la standardizzazione non cancella niente, perche' e' invertibile:
`x = (x_rel + 1) * m_s`, con `m_s` in tabella e un test che ricostruisce le
colonne grezze a meno del floating point. Cancellare la deriva **dentro** il
derivato sarebbe cancellare un fatto misurato in un posto da cui non si recupera
piu' — il vincolo 4.

### Ogni feature e' un rapporto dichiarato, non una colonna

Ogni candidata e' definita come **numeratore su denominatore**, e il riferimento
di campionato e' `somma(num) / somma(den)` su tutte le righe della stagione. Non
e' pedanteria: e' cio' che rende il riferimento **la stessa grandezza** del
valore del singolo. La media delle medie individuali — la scorciatoia — peserebbe
uguale chi ha giocato 90 minuti e chi ne ha giocati 3.000, e un test verifica che
i due numeri siano davvero diversi invece di assumerlo.

## 2. Le {len(FG.CANDIDATE)} candidate

Una riga e' la tripla `(stagione, playerId, teamId)`, cioe' **la stessa
granularita' dell'aggancio di E0**: chi cambia squadra a gennaio ha due righe,
perche' i suoi minuti sono di due squadre diverse. Sono
{len(feat)} righe su cinque stagioni.

{t_reg}

I denominatori di squadra **si contano, non si assumono**, ed e' la lezione di E0
propagata qui: l'Atalanta ha 35 partite nel 2021-22 e nel 2022-23, e un test lo
verifica. Con 38 al denominatore ogni quota di esposizione sarebbe sbagliata
proprio dove sbagliare costa di piu', perche' la perdita alla fonte **non e'
casuale rispetto alla squadra**.

## 3. La deriva, prima e dopo

Le due colonne sono confrontabili perche' sono nella stessa unita': entrambe sono
escursioni **relative** della media di stagione. La soglia dichiarata e'
**{_pct(FG.SOGLIA_DERIVA)}**.

{t_der}

**La soglia e' dichiarata prima, non ricavata dopo** (vincolo 1 applicato a una
soglia, come gia' fatto per l'80'): {_pct(FG.SOGLIA_DERIVA)} sta **sotto** la piu'
piccola deriva reale gia' misurata nel repository — i tiri in porta per
squadra-partita, -9,2% — e **molto sopra** l'errore di campionamento di una media
di campionato su 17.000 righe. Un test verifica che sia una costante letterale e
che nel modulo non compaiano `argmax`, `idxmax` o `quantile`.

Le medie di stagione si misurano sulle righe con almeno
**{FG.MIN_MINUTI_DERIVA:.0f} minuti** ({_pct(quota_minuti)} dei minuti totali, e
poco piu' della meta' delle righe). Il **riferimento** invece usa tutto: il
riferimento e' il campionato, non i titolari. Senza il pavimento la media di
stagione di un tasso per 90 sarebbe dominata dagli spezzoni di tre minuti, dove
il denominatore e' minuscolo.

### I tre verdetti

- **grezza ammessa** ({n_grezze}): non si muove oltre la soglia. Puo' entrare
  cosi' com'e', e per alcune standardizzarla sarebbe **dannoso** — vedi §4.
- **standardizzata** ({n_std}): la regola fa il suo lavoro. Il caso migliore e'
  `quota_porta_inviolata`, che passa da
  {_pct(d_ind.loc['quota_porta_inviolata', 'deriva_grezza'])} a
  {_pct(d_ind.loc['quota_porta_inviolata', 'deriva_std'])}: le porte inviolate
  sono aumentate del 29% fra le cinque stagioni — si segna meno — e in unita'
  grezze un difensore del 2021-22 e uno del 2025-26 non sarebbero confrontabili.
- **serve effetto di stagione** ({n_stagione}): {", ".join(f"`{n}`" for n in non_risolte)}.
  La standardizzazione non basta, e non e' un fallimento del calcolo: e' il caso
  che la regola prevede. Chi le usa in un modello multi-stagione deve portarsi
  dietro un effetto di stagione, e puo' chiederlo al codice
  (`richiede_effetto_stagione`) invece di leggerlo qui.

**Sono quasi tutte della famiglia produzione**, e la coincidenza non e' tale:
tiri, tiri in porta, gol, xG e tocchi in area sono le grandezze **concentrate su
pochi giocatori**, cioe' quelle in cui la forma della distribuzione pesa piu' del
livello.

## 4. Perche' a volte non basta, e a volte peggiora

E' la parte del blocco che non era prevista, e il meccanismo si misura invece di
raccontarlo. Due grandezze, tenute separate:

- **`deriva_riferimento`** — di quanto si muove la media di campionato pesata,
  cioe' il **livello**. E' esattamente cio' che la standardizzazione toglie;
- **`deriva_popolazione`** — di quanto si muove la media non pesata fra i
  giocatori sopra il pavimento, cioe' la **forma** e la composizione di chi gioca.

{t_scomp}

Se le due coincidono, dividere per il riferimento azzera la deriva. Se divergono
resta un residuo, e i due modi in cui divergono danno due esiti diversi.

**Primo meccanismo — sovracorrezione**, e riguarda
{", ".join(f"`{n}`" for n in sovracorrette)}. Le due derive vanno nello stesso
verso ma con ampiezze diverse. Su `sot_per_90` il livello di campionato scende del
{_pct(s_ind.loc['sot_per_90', 'deriva_riferimento'])} mentre il tasso del
giocatore tipico scende del
{_pct(s_ind.loc['sot_per_90', 'deriva_popolazione'])}: dividere per il primo toglie
piu' di quanto ce ne sia nel secondo, e il residuo cambia segno. Detto altrimenti,
**la caduta dei tiri in porta non e' distribuita uniformemente sui giocatori**, ed
e' un fatto sul gioco, non un difetto del conto. Stesso schema su `gol_per_90`
({_pct(s_ind.loc['gol_per_90', 'deriva_riferimento'])} contro
{_pct(s_ind.loc['gol_per_90', 'deriva_popolazione'])}) e su `xg_per_90`.

**Secondo meccanismo — versi opposti**, e riguarda
{", ".join(f"`{n}`" for n in opposti_peggio)}. Su `quota_tocchi_area` il
riferimento **scende** mentre la media fra i giocatori **sale** del
{_pct(s_ind.loc['quota_tocchi_area', 'deriva_popolazione'])}, e la deriva passa da
{_pct(d_ind.loc['quota_tocchi_area', 'deriva_grezza'])} grezza a
{_pct(d_ind.loc['quota_tocchi_area', 'deriva_std'])} standardizzata: si tocca
**meno** in area per tocco a livello di campionato e **piu'** per giocatore che
gioca, il che vuol dire che i tocchi in area si stanno concentrando.

Il verso opposto **non basta da solo** a peggiorare le cose: `minuto_medio_uscita`
va in verso opposto e migliora lo stesso, perche' il suo riferimento si sposta
dell'1,1%, e un verso contrario su un movimento che non c'e' non sposta niente.
Serve che il riferimento si muova davvero — ed e' la condizione doppia che un test
verifica.

**Il terzo caso non e' un meccanismo, e' un errore di grandezza**, e riguarda le
tre quote di esposizione ({", ".join(f"`{n}`" for n in esposizione)}), di cui
{len(esposizione_peggio)} peggiorano standardizzate. La causa e' identificata e non
e' il verso: per queste `somma(num)/somma(den)` **non e' "la quota del giocatore
tipico"**, e' la quota media su **tutta la rosa convocata**, panchinari compresi —
per `quota_titolare` vale esattamente `11 / ampiezza della rosa`. E' un fatto sulle
**rose**, non sui giocatori. Si vede a occhio nudo — riferimento
{_num(s_ind.loc['quota_titolare', 'riferimento_prima'])} contro media fra i
giocatori {_num(s_ind.loc['quota_titolare', 'popolazione_prima'])}: due numeri che
non possono essere la stessa grandezza. Standardizzare importa nella feature la
deriva delle rose, e `quota_titolare` passa da
{_pct(d_ind.loc['quota_titolare', 'deriva_grezza'])} grezza a
{_pct(d_ind.loc['quota_titolare', 'deriva_std'])} standardizzata.
**Restano grezze**, e possono: la loro deriva grezza sta sotto la soglia.

> **La lezione per E2 ed E4**: la standardizzazione non e' gratis e non e' un
> riflesso. Va applicata dove la deriva e' di livello, e la guardia serve proprio
> a distinguere i due casi **misurando**, invece di fidarsi del suffisso nel nome
> della colonna.

### Il verdetto dipende dal pavimento di esposizione?

`MIN_MINUTI_DERIVA` e' una scelta dichiarata, quindi si mostra quanto il
risultato le deve, su quattro pavimenti (3, 5, 10 e 20 partite intere).

{t_sens}

**{len(sempre)} candidate stanno oltre la soglia a ogni pavimento**
({", ".join(f"`{n}`" for n in sempre)}): quello e' un risultato che il pavimento
non decide. {"Le altre due non risolte a 450' — " + ", ".join(f"`{n}`" for n in instabili) + " — cambiano verdetto al variare del pavimento, e vanno trattate come **non risolte** lo stesso: e' il verso prudente." if instabili else ""}

In totale **{len(ballerine)} candidate su {len(FG.CANDIDATE)} cambiano verdetto**
fra i quattro pavimenti ({", ".join(f"`{n}`" for n in ballerine)}), e il movimento
va in entrambe le direzioni: `ammonizioni_per_90` peggiora abbassando il pavimento,
`azioni_difensive_per_90` peggiora alzandolo. Il pavimento non e' un dettaglio di
implementazione, ed e' meglio saperlo adesso che scoprirlo in E2 quando cambiera'
per un'altra ragione.

## 5. Corollario 1 — nessuna feature sul nome di un qualifier senza verifica

`StandingSave` e' la dimostrazione che **il nome di un qualifier non e' un
identificatore**: sta sul 71% di tutti gli eventi nelle prime quattro stagioni e
sul 4% nel 2025-26, a schema, conteggio colonne e numero di eventi invariati.
Non e' una parata che sparisce, e' la stessa etichetta su id diversi — due
versioni del dizionario della fonte.

Il gate (`verifica_qualifier`) chiede due cose: presenza in **tutte e cinque** le
stagioni, e rapporto fra frequenza massima e minima per evento sotto
**{FG.SOGLIA_QUALIFIER}**.

{t_qual}

La soglia e' scelta cosi': {FG.SOGLIA_QUALIFIER} e' il punto oltre il quale il
movimento non e' piu' compatibile con cio' che il **gioco** ha fatto — la deriva
piu' grande mai misurata su un tipo di evento e' `Clearance` +48%. I due casi noti
di dizionario cambiato stanno a
{q_ind.loc['StandingSave', 'rapporto']:.0f}x e
{q_ind.loc['OtherBodyPart', 'rapporto']:.0f}x, cioe' un ordine di grandezza oltre:
**non e' un numero delicato**, e non e' stato scelto per far passare qualcuno.

**Il gate e' necessario e non sufficiente**, e va detto: un qualifier che lo passa
non e' *dimostrato* essere la stessa cosa in tutte le stagioni. L'unico controllo
sufficiente sarebbe l'**id numerico**, che `acquisition/whoscored/main.py:432`
butta via tenendo solo il `displayName`. Il gate esclude i casi in cui il nome ha
cambiato significato in modo **visibile**.

**Nessuna candidata di oggi usa qualifier**, e non per virtu': `events_slim` non
porta la colonna `qualifiers` — la tiene solo per i cinque tipi di evento di
formazione — quindi una feature sui piazzati vuole una rilettura dei 1.889 CSV, ed
e' un costo che paga E4. La guardia esiste lo stesso, e un test costruisce una
candidata finta che dichiara `StandingSave` e pretende che venga fermata: senza
quella prova, "nessuna candidata usa qualifier" potrebbe voler dire "la guardia
non guarda niente".

## 6. Corollario 3 — le 72 colonne mai valorizzate, e cosa si deriva

Sono **{len(mai)}**, misurate col criterio giusto: **"ne' nullo ne' `False`"**, non
`notna()`. Lo scraper del fork scrive il literal `False` dove il campo della fonte
e' assente, quindi `notna()` dichiarerebbe valorizzate al 100% circa 200 colonne
su 259 che valorizzate non sono — un test verifica che la differenza fra le due
misure esista davvero sui dati, invece di ripeterla a parole.

{t_deriv}

Le tre grandezze che qualcuno cercherebbe li' — **porta inviolata, gol subiti,
precisione dei passaggi** — sono esattamente quelle che servono al voto base e al
modificatore, ed esistono nello schema con un nome invitante e nessun valore.
Si derivano.

**La garanzia piu' forte non e' la disciplina, e' l'impossibilita'**: `io_events`
tiene ~60 colonne su 259 e **nessuna delle 72 e' fra quelle**, quindi una feature
non puo' leggerle nemmeno per errore. Un test lo verifica sull'elenco delle
colonne caricate, cosi' che allargarlo un domani faccia scattare la guardia.

## 7. La guardia, che e' il deliverable vero

```python
FG.verifica_standardizzazione(feat, colonne_che_sto_per_usare)
```

Va chiamata da chiunque faccia entrare colonne di questa tabella in un modello
che attraversa le stagioni. Solleva `FeatureNonStandardizzata` elencando le
colonne colpevoli con la loro deriva.

**Non distingue "grezza" da "standardizzata" guardando il nome: misura.** Una
colonna grezza che non si muove passa — e ce ne sono {n_grezze} — e una colonna
`_rel` che si muove lo stesso viene fermata. Quest'ultimo e' il caso
interessante, perche' e' quello che il suffisso da solo nasconderebbe, e un test
lo verifica iniettando un gradino del 20% in una colonna `_rel` sana e
pretendendo che la guardia lo veda.

## 8. Cosa e' stato prodotto

| | |
|---|---|
| `sot/features_giocatore.py` | il registro, la standardizzazione, il gate e la guardia |
| `data/processed/ITA-serie-a/fase9_feature_giocatore.parquet` | {len(feat)} righe x {len(feat.columns)} colonne |
| `data/processed/ITA-serie-a/fase9_feature_riferimenti.parquet` | {len(rif)} righe, **stesso schema** di `fase9_medie_campionato` |
| `reports/fase9_e1_*.csv` | le tavole di questo report |
| `tests/test_fase9_e1.py` | i tre corollari come test |

I riferimenti hanno lo stesso schema delle medie di campionato di E0 e stanno in
un **file separato** per una ragione operativa e non concettuale:
`run_fase9_e0.py` riscrive il proprio Parquet per intero a ogni esecuzione,
quindi righe di E1 appese li' sparirebbero al primo rilancio di E0 senza che
nessuno se ne accorga.

## Domande aperte

1. **Il riferimento giusto per le quote di esposizione non e' quello di
   campionato**, ed e' §4: per `quota_titolare` la media pesata vale `11/rosa`.
   Oggi restano grezze perche' la loro deriva grezza e' sotto soglia, e va bene;
   ma se un domani l'ampiezza delle rose si muovesse davvero, servirebbe un
   riferimento diverso — la media fra i giocatori sopra un pavimento — e quella
   scelta dipenderebbe dal pavimento. Non e' stata presa qui.
2. **`xg_per_90` ha un problema in piu' degli altri quattro.** I cinque fit di xG
   sono **cinque modelli**, non cinque livelli: la standardizzazione ne toglie il
   livello e lascia intatto il resto. Un effetto di stagione lo copre solo se la
   differenza fra i fit e' un'intercetta, e questo non e' stato verificato.
3. **La stabilita' della posizione media in campo** — uno dei candidati di E2 —
   non e' un rapporto e quindi non entra in questo registro, che e' costruito su
   rapporti perche' e' cio' che rende il riferimento la stessa grandezza. Una
   dispersione vuole un'altra forma di standardizzazione, e va decisa in E2.
4. **La riga e' `(stagione, playerId, teamId)` e il modello d'asta lavora su
   `giocatore_id`.** Portare la tabella al livello del modello vuole una
   decisione — sommare le due meta' di stagione di chi si trasferisce, oppure
   tenere la squadra principale — che cambia il significato di ogni quota di
   esposizione. E' lavoro di E2, non di questo blocco.
5. **`quota_presenze` ha il calendario intero al denominatore anche per chi
   arriva a gennaio**, quindi sottostima l'impiego dei nuovi arrivati. Il rimedio
   sarebbe restringere il denominatore alla finestra di permanenza, che i dati
   non registrano direttamente.
6. **Le squalifiche non sono ancora qui.** `ammonizioni_per_90` e' l'ingresso, ma
   la regola delle cinque ammonizioni e' **deterministica** e va applicata alla
   sequenza dentro la stagione, non a un tasso. E' il pezzo gratis di E2.
"""

    OUT_MD.write_text(testo, encoding="utf-8")
    print(f"\n-> {OUT_MD}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
