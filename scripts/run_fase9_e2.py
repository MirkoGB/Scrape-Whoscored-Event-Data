# -*- coding: utf-8 -*-
"""Fase 9 / Blocco E2 — le presenze.

    ./.venv/Scripts/python.exe scripts/run_fase9_e2.py

**Non tocca la rete.** Legge i Parquet di E0, la cache degli eventi di formazione
e le tabelle del fantacalcio; produce le squalifiche (che non si stimano), lo
strato distinta e la valutazione del modello d'impiego sulle stesse quattro
transizioni del modello d'asta.

L'ordine di esecuzione **non e' indifferente**: le squalifiche vanno per prime,
prima che entri un solo predittore stimato, o la parte di presenze mancate che
una regola di conteggio spiega gratis finirebbe attribuita a un modello.
"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sot import (config, distinta as D, impiego as IM,  # noqa: E402
                 squalifiche as SQ)

OUT_MD = config.REPORTS / "fase9_e2_presenze.md"


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
    print("squalifiche (nessuna stima)...")
    riep_sq = SQ.riepilogo()
    ver = pd.DataFrame([SQ.verifica(st) for st in config.SEASONS_STORICHE])
    fonti = SQ.confronto_fonti()
    sens_rosso = SQ.sensibilita_durata_rosso()
    divario_sq = SQ.divario_oracolo()
    peggiora = SQ.perche_peggiora()

    print("strato distinta...")
    nm = D.numero_maglia_multi()
    coll = D.collinearita_fascia_ruolo(nm)
    coll_num = D.collinearita_per_numero(nm)
    tace = D.dove_il_ruolo_tace(nm)
    cambio = D.cambio_numero(nm)

    print("modello d'impiego e valutazione...")
    val = IM.valutazione()
    mde = IM.potenza_mde(val["dettaglio"], "pres_impiego (senza maglia)")
    primo_anno = IM.maglia_sul_primo_anno()
    sens_pav = IM.sensibilita_pavimento()

    print("coda: il cartellino come predittore...")
    deriva_c = IM.deriva_cartellini()
    cart = IM.contributo_cartellini()
    ridond = IM.ridondanza_cartellini()

    print("(b): la quotazione QI come predittore di presenza...")
    deriva_q = IM.deriva_qi()
    ridond_q = IM.ridondanza_qi()
    qi = IM.contributo_qi()
    tab_qi = IM.con_quotazione()

    for nome, df in (("fase9_e2_squalifiche", riep_sq),
                     ("fase9_e2_squalifiche_verifica", ver),
                     ("fase9_e2_cartellini_due_fonti", fonti),
                     ("fase9_e2_divario_squalifiche", divario_sq),
                     ("fase9_e2_maglia_fasce", coll),
                     ("fase9_e2_maglia_numeri", coll_num),
                     ("fase9_e2_valutazione", val["tabella"]),
                     ("fase9_e2_pavimento", sens_pav),
                     ("fase9_e2_primo_anno", primo_anno),
                     ("fase9_e2_cartellini_deriva", deriva_c),
                     ("fase9_e2_cartellini_contributo", cart["tabella"]),
                     ("fase9_e2_cartellini_mde", cart["mde"]),
                     ("fase9_e2_qi_deriva", deriva_q),
                     ("fase9_e2_qi_ridondanza", ridond_q),
                     ("fase9_e2_qi_contributo", qi["tabella"]),
                     ("fase9_e2_qi_mde", qi["mde"])):
        df.to_csv(config.REPORTS / f"{nome}.csv", index=False)

    q_tab = qi["tabella"].set_index("variante")
    q_mde = qi["mde"].set_index("variante")
    q_rid = ridond_q.set_index("colonna")
    q_der = deriva_q.set_index("colonna")
    VINCE = "impiego + QI (percentile di ruolo)"
    BASE_Q = "impiego (senza maglia)"

    n_multi = int((nm["n_numeri"] > 1).sum())
    multi = nm[nm["n_numeri"] > 1][["stagione", "teamId", "playerId", "jersey",
                                    "n_numeri"]]
    n_cambio = int(cambio["numero_cambiato"].fillna(0).sum())
    n_stesso = int(cambio["stesso_club_anno_prima"].sum())

    testo = f"""# Fase 9 / Blocco E2 — le presenze

> Generato da `scripts/run_fase9_e2.py` il {date.today().isoformat()}.
> Nessuna richiesta di rete.

**Il limite che non si aggira, e che vale per ogni numero di questo report: gli
infortuni non sono nei dati.** Sono la componente piu' grossa dell'assenza e
questo blocco non li prevede. Non e' una nota a pie' di pagina: e' la ragione per
cui il tetto raggiungibile qui e' molto piu' basso del divario oracolo.

## In breve

Il blocco produce **tre risultati negativi e due positivi**, e i negativi sono il
contenuto.

| | esito |
|---|---|
| squalifiche come sottrazione di presenze | **−1,9%** del divario oracolo: peggiorano |
| predittori d'impiego da dati evento | **+0,20%** del divario, sotto l'MDE di 1,53% |
| numero di maglia | **nessun contributo** distinguibile, e la versione utile non e' costruibile |
| il cartellino come **predittore** (coda §4) | **±0,03%** del divario, con MDE 0,04-0,12%: confutato |
| la **quotazione QI** come predittore (§5) | **+{float(q_tab.loc[VINCE, 'divario_chiuso_pct']):.2f}%** del divario, t = {float(q_mde.loc[VINCE, 't']):.2f}: **il primo che passa** |
| la regola delle squalifiche in se' | **verificata**, accordo 96-99% contro baseline 13-16% |
| il pavimento di esposizione a zero | **confermato da una misura**, non da un'opinione |

## 1. Le squalifiche, che non si stimano

Regola deterministica dai cartellini, con tre assunzioni dichiarate: cinque
ammonizioni una giornata col contatore che riparte; l'ammonizione del doppio
giallo non entra nel cumulo; **l'espulsione vale una giornata, ed e' un limite
inferiore** — la durata vera la decide il giudice sportivo e non e' nei dati.

Il taglio sui destinatari **non e' quello dei minuti**: le 85 espulsioni del
2025-26 danno 65 uomini tolti dal campo, ma per le squalifiche contano tutte
quelle a **giocatori**, panchinari compresi. Il numero giusto e' **68**.

{_tab(riep_sq)}

### La verifica, che non passa da nessun modello

Se la regola dice che un giocatore salta la partita successiva della sua squadra,
quel giocatore non deve comparire fra i convocati. E' falsificabile e si controlla
riga per riga.

{_tab(ver[['stagione', 'squalifiche_scontate', 'accordo',
           'accordo_calendario_intero', 'baseline_assenza', 'errori',
           'errori_su_squadra_bucata', 'quota_righe_squadra_bucata']],
      {'accordo': 3, 'accordo_calendario_intero': 3, 'baseline_assenza': 3,
       'quota_righe_squadra_bucata': 3})}

**Il baseline e' il punto** (vincolo 6): le stesse persone, nelle giornate in cui
**non** sono squalificate, mancano dalla distinta il **13-16%** delle volte. Il
96-99% di accordo va letto contro quello, non contro zero.

**Il residuo ha una causa, ed e' stata cercata invece che addotta.** L'accordo
grezzo scende al 91,4% nel 2021-22, e non perche' la regola funzioni peggio: **17
errori su 20** cadono su squadre a cui WhoScored manca almeno una partita, mentre
quelle squadre sono solo il 42,9% delle righe. `team_match_idx` numera le partite
**presenti nei dati**, quindi se la successiva al cartellino e' fra le 12 assenti
alla fonte, `idx + 1` e' la partita dopo — in cui il giocatore e' gia' rientrato.
E' un difetto dell'indice, non della regola: sulle squadre col calendario intero
l'accordo sta fra **96,2% e 99,4%** ovunque.

### Le due fonti dei cartellini, una contro l'altra (vincolo 7)

La fonte dei voti porta `ammonizioni` ed `espulsioni` per conto suo. Non si
sceglie la comoda: si misurano.

{_tab(fonti, {'accordo_gialli': 3, 'accordo_espulsioni': 3})}

**Le espulsioni concordano** (98-99%), le **ammonizioni no** (85-93%), e la fonte
dei voti ne conta sistematicamente **di piu'**. L'accordo e' peggiore proprio
nelle due stagioni con partite mancanti, quindi una parte e' il buco
dell'archivio — ma **non tutto**: nel 2023-24, che e' completo, restano 42
ammonizioni di scarto. **La causa residua non e' identificata e non e' stata
ipotizzata.**

### Quanto vale l'assunzione piu' fragile

{_tab(sens_rosso, {'per_stagione': 1})}

### E ora il numero per cui il blocco esisteva

{_tab(divario_sq[['variante', 'righe', 'mae', 'divario_chiuso_pct']],
      {'mae': 2, 'divario_chiuso_pct': 2})}

**Le squalifiche non chiudono niente del divario: lo allargano.** Anche
nell'oracolo, cioe' conoscendo i cartellini della stagione bersaglio, sottrarre le
giornate di squalifica **peggiora** il MAE dell'1,9%.

**Il perche' e' misurato, non addotto:**

{_tab(peggiora, {'presenze_attese': 2, 'presenze_osservate': 2, 'bias': 2})}

Chi prende squalifiche e' chi gioca — cinque ammonizioni non le accumula un
panchinaro — e su quei giocatori il modello d'asta **gia' sottostima** le presenze
di sei, perche' lo shrinkage al ruolo tira verso il basso chi sta in alto.
Togliere altre giornate a una previsione gia' troppo bassa allontana.

> **L'inversione che il meccanismo suggerisce: il cartellino non e' una presenza
> in meno, e' il segnale che quel giocatore gioca.** Come sottrazione e' dannoso;
> come predittore d'impiego avrebbe il segno opposto — **ed e' stata provata in
> quella forma nella coda §4, dove non regge.** La lettura del meccanismo resta
> valida; la sua conseguenza operativa no.

## 2. Lo strato distinta

**Costa quasi zero, e non e' un'aspettativa ma una misura**: `JerseyNumber` e
`CaptainPlayerId` stanno nella stessa lista di qualifier da cui `minutes.squads()`
gia' estrae `PlayerPosition`. Presenti sul **100%** delle 3.778 righe
`FormationSet` di tutte e cinque le stagioni, lunghezze sempre allineate a
`InvolvedPlayers`, **estrazione in 0,3 secondi** dai Parquet gia' in cache. I
piazzati di E4, che vogliono `qualifiers` sugli eventi normali, costerebbero
invece una rilettura dei 1.889 CSV.

Le triple sono **{len(nm)}**, la stessa granularita' di E1. **{n_multi}** hanno piu' di un
numero nella stessa stagione e si risolvono con la **prima distinta**, non con la
moda pesata sui minuti: la moda userebbe i minuti della stagione per costruire un
predittore il cui unico pregio e' di esistere **prima** che quei minuti siano
giocati. Eccole tutte:

{_tab(multi)}

Il numero cambia in **{n_cambio}** casi su **{n_stesso}** permanenze nello stesso club.

### La fascia dei portieri non e' quella dei portieri

Era la verifica richiesta: la fascia `1/12/22` duplica il `role_code`?

{_tab(coll, {'quota_dominante': 3})}

Il ruolo dominante di `portiere_classico` e' GK al **46%**, cioe' non domina
affatto. Il dettaglio dice perche':

{_tab(coll_num, {'GK': 3, 'DIF': 3, 'CEN': 3, 'ATT': 3})}

**La 1 e' portiere nel 100% dei casi; la 12 nel 18% e la 22 nell'8%.** Il folklore
«1/12/22 sono i tre portieri» e' falso in questi dati. E solo il 35% dei portieri
porta uno di quei tre numeri.

**La fascia non e' stata ridefinita**, ed e' il punto: si e' scoperto *dopo* aver
dichiarato la partizione, e cambiarla adesso sarebbe adattarla al campione su cui
poi la si valuta. La sua **eterogeneita' e' il risultato**.

### Dove il ruolo tace, il numero c'e'

**{tace['senza_ruolo']} triple su {tace['triple']}** ({100 * tace['quota_senza_ruolo']:.1f}%) non hanno **nessun**
ruolo: sono i convocati che non sono mai scesi in campo, `role_code == 5` in ogni
distinta. Per loro il ruolo non esiste — e **tutte e {tace['con_maglia_fra_i_senza_ruolo']} hanno un numero di
maglia**. E' l'argomento a favore della feature detto nel modo piu' stretto
possibile.

## 3. Il modello d'impiego

### Prima, il difetto che rende inutilizzabile la versione interessante della maglia

Il numero e' assegnato **in agosto**, e questo era l'argomento: e' noto al momento
della previsione anche per chi al nuovo club non ha storia. Ma la nostra **unica
fonte del numero e' la distinta di una partita**. Chi non viene mai convocato non
ha nessuna distinta, quindi non ha nessun numero.

Misurato sulle quattro transizioni: fra i quotati con una distinta nella stagione
bersaglio le presenze medie sono **19,1-19,3**; fra quelli senza sono **0,0-0,3**.
**La sola disponibilita' della feature e' la risposta.** Si usa quindi il numero
della **stagione precedente**, come il capitano — e il costo e' esattamente il
caso che si voleva coprire: per chi cambia club, il numero disponibile e' quello
del club vecchio.

> Il numero d'agosto **sarebbe acquisibile** — lo pubblicano i club e sta nei
> listoni — ma non e' nel repository. E' una domanda aperta con una risposta nota,
> non un limite dei dati evento.

### La valutazione, sulle stesse quattro transizioni del modello d'asta

{_tab(val['tabella'], {'mae': 2, 'divario_chiuso_pct': 2})}

**Lo 0,20% del divario oracolo**, e la maglia non aggiunge niente (0,19%, cioe'
un'inezia peggio). Sulle presenze il MAE e' 9,906 contro 9,904 del modello d'asta:
identico. La correlazione sale da 0,438 a 0,461, e non basta.

**La potenza e' dichiarata**, come in 6D: differenza appaiata {mde['delta_mae']:.3f} di MAE,
errore standard {mde['se']:.3f}, **t = {mde['t']:.2f}**. L'MDE a potenza 80% vale {mde['mde_mae']:.3f} di MAE,
cioe' il **{mde['mde_quota_divario_pct']:.2f}%** del divario. Quindi il test **non** avrebbe visto un
effetto sotto l'1,5%: il risultato negativo esclude effetti grandi, non effetti
piccoli, e va letto cosi'.

**Perche' non aiuta e' leggibile**: il modello d'asta usa gia' le presenze passate
del giocatore, e `quota_titolare`, `quota_convocato`, capitano e ruolo instabile
sono un altro modo di dire la stessa cosa. E' lo stesso meccanismo della Fase 2 —
i predittori evento erano gia' coperti dagli effetti attacco/difesa — su un
bersaglio diverso.

### Il pavimento di esposizione: la decisione era giusta, e adesso c'e' il numero

{_tab(sens_pav[sens_pav['variante'] != 'presenze note (ORACOLO, il pavimento)'],
      {'mae': 3, 'divario_chiuso_pct': 3})}

**Il pavimento distrugge il risultato in modo monotono**: +0,20% a zero, −0,83% a
450, −1,15% a 900, **−5,07% a 1.800**. Addestrare sui soli giocatori con molti
minuti rende il modello peggiore proprio dove il bersaglio vive. In E1 il
pavimento proteggeva le medie; qui i pochi minuti **sono** il bersaglio, non la
coda, e questa tabella e' la misura di quella differenza.

### La maglia dove dovrebbe servire

{_tab(primo_anno, {'mae': 2})}

Sui giocatori al **primo anno nel club** la maglia migliora di 0,03 di MAE; su chi
era gia' nel club **peggiora** di 0,06. Il segno e' quello previsto e la grandezza
e' indistinguibile da zero — entrambe molto sotto l'MDE. **E' coerente con
l'ipotesi e non la conferma**, ed e' la lettura corretta di due numeri cosi'
piccoli.

## 4. Coda — il cartellino come predittore, e la fine dell'inversione

§1 aveva consegnato un'inversione: **il cartellino non e' una presenza in meno,
e' il segnale che quel giocatore gioca.** Era una lettura del meccanismo, non un
risultato: `tasso_cartellini` **non era nel set di E2.4** — `FEATURE` sono cinque
colonne e nessuna e' un cartellino — quindi l'inversione non era ne' confermata
ne' confutata. **Era non provata**, ed e' la ragione per cui questa coda si fa
qui e non fra due blocchi.

**La fonte e' quella dei voti, ed e' una scelta dichiarata** (vincolo 7: le due
divergono, le ammonizioni concordano solo all'85-93%). Per i punti fantacalcio la
fonte dei voti e' **definitoria** — e' quella che ha prodotto il malus dentro
`punti_osservati`, cioe' il bersaglio — e sta gia' sulla chiave `giocatore_id`
senza aggancio di mezzo. WhoScored resta il controllo indipendente di §1.

### Due forme, perche' sono due ipotesi diverse

Il **conteggio** `amm + esp` di t-1 e' l'inversione detta alla lettera: il
cartellino come marcatore di esposizione. Il **tasso** `(amm+esp)/presenze` e' la
propensione disciplinare **al netto** del minutaggio. Provarne una sola avrebbe
lasciato aperta l'altra.

### Il gate di E1 non si chiude, e non e' stato aggirato

{_tab(deriva_c, {'min': 4, 'max': 4, 'deriva': 3, 'deriva_riferimento': 3})}

**Nessuna delle due forme passa la soglia del 5%**, ne' grezza ne' standardizzata.
E il conteggio **non e' un rapporto**: il suo unico denominatore possibile e' il
numero di giocatori, quindi il riferimento coincide con la media fra i giocatori e
la sua `_rel` ha media esattamente zero in ogni stagione **per costruzione**. Non
e' una candidata che passa il gate, e' una colonna resa degenere — dichiarato qui
invece che nascosto dentro un numero.

Ne segue che si provano **entrambe le forme**: se l'esito coincide, la conclusione
non dipende da una scelta di standardizzazione che i dati non giustificano.

### Il risultato

{_tab(cart['tabella'], {'mae_punti': 3, 'mae_presenze': 3, 'corr_presenze': 3,
                        'divario_chiuso_pct': 3})}

**Niente, in tutte e cinque le varianti.** Il divario chiuso resta lo 0,19-0,22%
contro lo 0,196% del set di E2.4, cioe' si muove di **tre centesimi di punto
percentuale**; il MAE sulle presenze sta a 9,902-9,906 contro 9,906; la
correlazione non si muove dalla terza cifra. Grezza o `_rel`, conteggio o tasso.

{_tab(cart['mde'], {'delta_mae': 4, 'se': 4, 't': 3, 'mde_mae': 4,
                    'mde_quota_divario_pct': 3})}

**E qui la potenza non e' una scusa, e' l'argomento.** In E2.4 l'MDE valeva
l'1,53% del divario e il risultato negativo escludeva solo effetti grandi. Qui il
confronto e' **appaiato contro un modello quasi identico** — cambia una colonna —
quindi la varianza della differenza e' minuscola e l'MDE scende a **0,04-0,12%**
del divario. **Il test vedrebbe effetti dieci volte piu' piccoli di quelli che
E2.4 poteva vedere, e non ne trova nessuno.** Tutti i `t` stanno sotto 0,56 in
valore assoluto.

### Perche' il nulla non e' ridondanza

{_tab(ridond, {'r2_sul_set_e2_4': 3, 'corr_quota_minuti': 3,
               'corr_quota_titolare': 3})}

E' la misura che distingue una confutazione da un'ambiguita'. Un predittore che
non aggiunge niente puo' non aggiungere per due ragioni **opposte**: perche' e'
gia' dentro, o perche' non c'e' segnale.

* **Il conteggio e' in buona parte gia' nel set** (R2 0,41 sulle tre quote,
  correlazione 0,64 con `quota_minuti_prec`). Da solo, il suo nulla si
  spiegherebbe con la ridondanza — ed e' esattamente il meccanismo della Fase 2,
  dove i predittori evento erano gia' coperti dagli effetti attacco/difesa.
* **Il tasso no: R2 0,021, cioe' quasi ortogonale.** Porta informazione che il set
  di E2.4 **non ha**, e non serve lo stesso.

> **L'inversione e' confutata, e non resta una pista aperta in nessun blocco.**
> Il cartellino come sottrazione peggiora (§1); come predittore d'impiego non
> aggiunge niente, con un test che avrebbe visto lo 0,12% del divario. Le due
> letture sono state provate entrambe, in due forme ciascuna, e il meccanismo del
> nulla e' identificato per tutte e due. **Non va riaperta in E3 ne' in E4**, e
> non va "sistemata" ritoccando la forma della feature finche' un `t` supera 2:
> sarebbe la ricerca sugli otto predittori della Fase 2 rifatta su un bersaglio
> diverso, e con un MDE cosi' basso il margine per illudersi non c'e'.

**Cio' che resta vero di §1 e' il meccanismo, non la sua conseguenza operativa**:
chi prende cartellini gioca di piu', il modello d'asta gia' sottostima quei
giocatori, e per questo la sottrazione allontana. Il fatto e' misurato e non
cambia. Ma la quantita' che lo esprime era gia' nel modello sotto un altro nome.

## 5. (b) — la quotazione QI come predittore di presenza

**E' il primo predittore di presenze del progetto che superi il rumore**, e vale
la pena dire subito perche' puo' riuscire dove le feature evento hanno fallito:
tutte quelle vengono da **t-1**, perche' i dati evento di t non esistono ancora.
**QI viene da t** — e' un prezzo della stagione bersaglio, pubblicato prima che
cominci. E' l'unica cosa nel repository che guardi t senza guardarne l'esito.

**Il FVM e' fuori, e non per prudenza**: sta sull'orologio di QA, cioe' si muove
durante la stagione (§3-bis di `modello_asta.md`). QI e' la quotazione iniziale.
Un test verifica che nessuna colonna contaminata entri qui, e la guardia e'
sull'**elenco delle colonne ammesse**, non sul nome del suffisso.

### Due forme, e il gate di E1 le separa da solo

{_tab(deriva_q, {"min": 4, "max": 4, "deriva": 4})}

Il **prezzo grezzo deriva dell'{100 * float(q_der.loc['qi_asta', 'deriva']):.1f}%** fra le quattro stagioni e non passa la
soglia del 5%; il **percentile dentro `(stagione, ruolo)` deriva dell'{100 * float(q_der.loc['qi_pct_ruolo_asta', 'deriva']):.1f}%** e
passa — com'e' giusto, perche' un rango dentro la stagione e' piatto per
costruzione, ed e' anche il modo di far vedere che la guardia sa dire di si'.

Le due forme sono **due ipotesi diverse**, non due parametrizzazioni: il grezzo
dice quanto vale un giocatore in assoluto, il percentile dice dove sta nella
gerarchia del suo ruolo. La seconda e' l'ipotesi vera — la gerarchia dichiarata
dai club e' cio' che si suppone il mercato sappia e i dati evento no — e le scale
dei ruoli sono incomparabili (un portiere costa 16, un attaccante 44) mentre il
modello non ha un termine di ruolo.

### Il risultato

{_tab(q_tab.reset_index(), {"mae_punti": 4, "mae_presenze": 4,
                            "corr_presenze": 4, "divario_chiuso_pct": 4})}

{_tab(qi["mde"], {"delta_mae": 4, "se": 4, "t": 2, "mde_mae": 4,
                  "mde_quota_divario_pct": 4})}

**Il percentile di ruolo chiude l'{float(q_tab.loc[VINCE, 'divario_chiuso_pct']):.2f}% del divario oracolo**, contro lo
**{float(q_tab.loc[BASE_Q, 'divario_chiuso_pct']):.3f}%** del set di E2.4 — cioe' **{float(q_tab.loc[VINCE, 'divario_chiuso_pct']) / float(q_tab.loc[BASE_Q, 'divario_chiuso_pct']):.0f} volte** quello che le feature da dati evento
avevano prodotto. La differenza appaiata vale **t = {float(q_mde.loc[VINCE, 't']):.2f}**, contro un MDE del
{float(q_mde.loc[VINCE, 'mde_quota_divario_pct']):.2f}% del divario: **e' il primo predittore d'impiego di questo progetto
che stia sopra la propria soglia di rilevabilita'.** Con quattro varianti provate,
la soglia di Bonferroni a due code sarebbe |t| > 2.50, e {float(q_mde.loc[VINCE, 't']):.2f} la supera.

Sul MAE delle presenze si passa da {float(q_tab.loc[BASE_Q, 'mae_presenze']):.3f} a {float(q_tab.loc[VINCE, 'mae_presenze']):.3f} e la correlazione da
{float(q_tab.loc[BASE_Q, 'corr_presenze']):.3f} a {float(q_tab.loc[VINCE, 'corr_presenze']):.3f}: si muove il passaggio giusto, non solo il prodotto finale.

**Tre cose che ridimensionano il risultato, e vanno lette insieme al numero:**

1. **L'{float(q_tab.loc[VINCE, 'divario_chiuso_pct']):.1f}% resta piccolo in assoluto.** Il MAE sui punti va da {float(q_tab.loc[BASE_Q, 'mae_punti']):.2f} a
   {float(q_tab.loc[VINCE, 'mae_punti']):.2f}: sette decimi di punto su sessantuno. Le presenze restano il 91%
   dell'errore, e questo ne intacca una frazione. **Gli infortuni continuano a non
   essere nei dati**, e sono il tetto vero.
2. **Il prezzo grezzo da solo NON passa** ({float(q_tab.loc['impiego + QI (prezzo grezzo)', 'divario_chiuso_pct']):.2f}%, t = {float(q_mde.loc['impiego + QI (prezzo grezzo)', 't']):.2f}, sotto il proprio
   MDE del {float(q_mde.loc['impiego + QI (prezzo grezzo)', 'mde_quota_divario_pct']):.2f}%). Le due forme danno risposte diverse, quindi **la
   conclusione dipende dalla forma** — ed e' la forma dichiarata in anticipo come
   l'ipotesi vera, non quella scelta dopo aver visto i numeri. La coincidenza col
   gate di E1 e' un argomento in piu': la forma che funziona e' anche l'unica che
   non deriva.
3. **QI da solo e' PEGGIO del modello d'asta** ({float(q_tab.loc['SOLO QI, senza le feature evento', 'divario_chiuso_pct']):.2f}%): senza le feature evento la
   quotazione non basta. **E' un complemento, non un sostituto**, e chi ne
   ricavasse "all'asta guarda solo il prezzo" leggerebbe il contrario di quello
   che c'e' scritto.

### Il nulla non e' ridondanza, e qui nemmeno il positivo lo e'

{_tab(ridond_q, {"r2_sulle_quote": 4, "corr_quota_minuti": 4})}

QI e' **in buona parte gia' nel set**: il percentile ha R² {float(q_rid.loc['qi_pct_ruolo_asta', 'r2_sulle_quote']):.2f} sulle tre quote di
esposizione di t-1 e correla {float(q_rid.loc['qi_pct_ruolo_asta', 'corr_quota_minuti']):.2f} con `quota_minuti_prec`. Circa meta' di cio' che
il prezzo dice e' "ha giocato molto l'anno scorso", e quello lo sapevamo. **Il
guadagno viene dall'altra meta'** — ed e' esattamente la parte che nessun dato
evento puo' contenere, perche' e' il mercato estivo e la gerarchia dichiarata.

### L'indicatrice, e perche' non aggiunge niente

Il **31,2%** delle righe di `tabella_predittori` non ha QI: sono giocatori che
hanno giocato in t-1 e non sono nel listone di t, cioe' hanno lasciato il
campionato. Il riempimento a zero direbbe "il piu' economico", che e' un'altra
cosa da "non c'e'", quindi `senza_quotazione_asta` esiste come indicatrice
esplicita invece di lasciare che il riempimento decida in silenzio.

Non cambia niente ({float(q_tab.loc['impiego + QI (percentile + indicatrice)', 'divario_chiuso_pct']):.2f}% contro {float(q_tab.loc[VINCE, 'divario_chiuso_pct']):.2f}%), **e il motivo e' strutturale**: la
valutazione gira sul listone, quindi **tutte e {int(q_tab.loc[VINCE, 'righe'])} le righe valutate hanno un
QI** e la mancanza tocca solo l'addestramento. Riportarlo evita che qualcuno
concluda che la mancanza non e' informativa: qui non e' *misurabile*, che e'
un'altra cosa.

## Domande aperte

1. **Il numero di maglia d'agosto**, dalla fonte giusta invece che dalla distinta.
   E' l'unico modo di provare l'argomento per cui la feature esisteva, e la fonte
   e' nota.
2. **Le 42 ammonizioni di scarto del 2023-24** fra le due fonti, in una stagione
   senza partite mancanti. Non identificate. **Per i punti fantacalcio la fonte
   dei voti e' definitoria e non una candidata**: e' quella che alimenta il malus,
   e lo scarto e' un problema di WhoScored da spiegare, non una scelta da fare.
3. **La durata vera delle espulsioni**, che il giudice sportivo pubblica e i dati
   evento non contengono: oggi tutte valgono una giornata come limite inferiore.
4. **Gli infortuni**, che restano la componente piu' grossa e non sono in nessuna
   delle due fonti acquisite.

> Il **cartellino come predittore d'impiego** era la terza domanda aperta di
> questo elenco. **E' chiusa dalla coda §4**, con esito negativo e potenza
> dichiarata, e per questo non compare piu' qui.
"""

    OUT_MD.write_text(testo, encoding="utf-8")
    print(f"\n-> {OUT_MD}")


if __name__ == "__main__":
    main()
