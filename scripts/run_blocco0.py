# -*- coding: utf-8 -*-
"""Blocco 0 — ricognizione. Rigenera report, tabelle e mapping con un comando.

    ./.venv/Scripts/python.exe scripts/run_blocco0.py            # ~5 s da cache
    ./.venv/Scripts/python.exe scripts/run_blocco0.py --force    # ~3 min, rilegge 4,8 GB

Non scrive niente sotto `data/raw/`, non tocca la rete, non stima niente.
"""

from __future__ import annotations

import argparse
import sys
from datetime import date

import pandas as pd

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent.parent))

from sot import config, ricognizione as R  # noqa: E402

OUT_MD = config.REPORTS / "blocco0_ricognizione.md"


def _tab(df: pd.DataFrame, allinea_dx: tuple[str, ...] = ()) -> str:
    """DataFrame -> tabella markdown, senza dipendenze in piu'."""
    def cella(v) -> str:
        # Il pipe dentro una cella spezza la tabella. Capita davvero: il dtype
        # di `cardType` e' la stringa `bool|str`.
        return "" if pd.isna(v) else str(v).replace("|", r"\|")

    cols = list(df.columns)
    testa = "| " + " | ".join(cella(c) for c in cols) + " |"
    sep = "|" + "|".join("---:" if c in allinea_dx else "---" for c in cols) + "|"
    righe = ["| " + " | ".join(cella(v) for v in r) + " |"
             for r in df.itertuples(index=False)]
    return "\n".join([testa, sep, *righe])


def _mila(n: int) -> str:
    """Separatore delle migliaia all'italiana."""
    return f"{int(n):,}".replace(",", ".")


def main(force: bool = False) -> None:
    d = R.scansione(force=force)
    F, C, E, Q, G = d["file"], d["colonne"], d["eventi"], d["qualifier"], d["giocatori"]

    # ---------------------------------------------------------------- 0.1
    sint = F.groupby("stagione").agg(
        file=("matchId", "size"), eventi=("n_eventi", "sum"),
        eventi_per_partita=("n_eventi", "mean"),
        colonne_min=("n_colonne", "min"), colonne_max=("n_colonne", "max"),
        byte=("byte", "sum"), prima=("data", "min"), ultima=("data", "max"),
        zero_eventi=("n_eventi", lambda x: int((x == 0).sum())),
        dup_chiave=("dup_chiave", "sum"), dup_id=("dup_id", "sum")).reset_index()
    sq = R.registro_squadre(F)
    reg = R.registro_giocatori(G, sq)
    sint = sint.merge(
        reg.groupby("stagione")["playerId"].nunique().rename("giocatori").reset_index(),
        on="stagione")
    sint = sint.merge(sq.groupby("stagione").size().rename("squadre").reset_index(),
                      on="stagione")

    sint_md = sint.assign(
        GB=(sint["byte"] / 1e9).round(2),
        eventi_per_partita=sint["eventi_per_partita"].round(0).astype(int),
        prima=sint["prima"].dt.date, ultima=sint["ultima"].dt.date,
        eventi=sint["eventi"].map("{:,}".format).str.replace(",", "."),
    )[["stagione", "file", "eventi", "eventi_per_partita", "squadre", "giocatori",
       "prima", "ultima", "GB", "zero_eventi"]]

    cop = R.copertura(F)
    cop_md = cop.assign(copertura=(cop["copertura"] * 100).round(1).astype(str) + "%")[
        ["stagione", "calendario", "file_su_disco", "mancanti",
         "su_disco_non_in_calendario", "file_con_zero_eventi", "copertura"]]

    mancanti = R.partite_mancanti(F)
    perdita = R.perdita_per_squadra(F)
    perdita_pos = perdita[perdita["mancanti"] > 0].copy()
    denom = perdita[perdita["calendario"] != 38]

    st = R.stabilita_schema(C)
    morte = sorted(st[st["quota_valorizzata_max"] == 0]["colonna"].tolist())
    vive = len(st) - len(morte)
    # Le famiglie di colonne morte si contano, non si stimano a occhio.
    FAM = ("cleanSheet", "goalConcededByTeam", "goalScoredByTeam", "penaltyShootout")
    fam, resto = dict.fromkeys(FAM, 0), []
    for c in morte:
        for k in FAM:
            if c.startswith(k):
                fam[k] += 1
                break
        else:
            resto.append(c)
    dtipi = C.pivot(index="colonna", columns="stagione", values="dtype")
    dtipi_misti = dtipi[dtipi.nunique(axis=1) > 1]

    ev_tot = F.groupby("stagione")["n_eventi"].sum()
    tipi = E.groupby(["stagione", "type"])["n"].sum().unstack(0).fillna(0)
    tipi_mille = (tipi / ev_tot * 1000)
    tipi_mille["rapporto"] = tipi_mille.max(axis=1) / tipi_mille.min(axis=1)
    tipi_mille["totale"] = tipi.sum(axis=1).astype(int)
    deriva_tipi = (tipi_mille[tipi_mille["totale"] >= 1000]
                   .sort_values("rapporto", ascending=False).round(2).reset_index())

    prima, ultima = config.SEASONS_STORICHE[0], config.SEASONS_STORICHE[-1]

    def _var(tipo: str) -> float:
        """Variazione relativa di un tipo di evento fra prima e ultima stagione."""
        r = tipi_mille.loc[tipo]
        return r[ultima] / r[prima] - 1.0

    dq = R.deriva_qualifier(Q, F, min_totale=500)
    dq_md = dq.head(8).copy()
    for c in dq_md.columns:
        if c not in ("qualifier",):
            dq_md[c] = dq_md[c].round(4)

    giorn = pd.DataFrame([
        {k: v for k, v in R.indice_giornata(s).items() if k != "dettaglio"}
        for s in config.SEASONS_STORICHE])
    giorn_md = giorn.assign(
        quota_ordine_cronologico=(giorn["quota_ordine_cronologico"] * 100)
        .round(1).astype(str) + "%")

    # Le due etichette che cambiano significato: il conteggio per partita e'
    # l'unico modo di distinguere "cala ovunque" da "vive in poche partite".
    p_qual = config.processed_league_dir() / "blocco0_qualifier_partita.parquet"
    if force or not p_qual.exists():
        R.presenza_qualifier_per_partita(
            ("StandingSave", "OtherBodyPart"), config.SEASON).to_parquet(
                p_qual, index=False)
    QP = pd.read_parquet(p_qual)
    ss_vive = int((QP["StandingSave"] > 0).sum())
    obp_vive = int((QP["OtherBodyPart"] > 0).sum())
    entrambe = int(((QP["StandingSave"] > 0) & (QP["OtherBodyPart"] > 0)).sum())
    # Regime "vecchio": le partite in cui StandingSave sta su piu' di un quarto
    # degli eventi, che e' l'ordine di grandezza delle prime quattro stagioni.
    vecchio = int((QP["StandingSave"] / QP["n_eventi"] > 0.25).sum())

    # ---------------------------------------------------------------- 0.2
    anom = R.anomalie_identita(reg)
    scritti = R.scrivi_mapping(sq, reg, anom)

    squadre_piv = (sq.pivot_table(index="nome_whoscored", columns="stagione",
                                  values="partite", aggfunc="sum")
                   .fillna(0).astype(int).reset_index())

    # ---------------------------------------------------------------- 0.4
    voti = R.stato_fonte_voti()
    esp = R.esposizione_regola_80()
    ingressi = R.ingressi_per_minuto()

    # ---------------------------------------------------------------- CSV
    csvs = {
        "blocco0_sintesi_stagioni.csv": sint,
        "blocco0_copertura.csv": cop,
        "blocco0_partite_mancanti.csv": mancanti,
        "blocco0_perdita_per_squadra.csv": perdita,
        "blocco0_colonne.csv": C,
        "blocco0_stabilita_schema.csv": st,
        "blocco0_tipi_evento.csv": E,
        "blocco0_qualifier_deriva.csv": dq,
        "blocco0_squadre.csv": sq,
        "blocco0_ingressi_per_minuto.csv": ingressi,
        "blocco0_stato_fonte_voti.csv": voti,
    }
    for nome, df in csvs.items():
        df.to_csv(config.REPORTS / nome, index=False, encoding="utf-8")

    tot_file = int(sint["file"].sum())
    tot_eventi = int(sint["eventi"].sum())
    tot_cal = int(cop["calendario"].sum())
    e80 = esp.iloc[0]
    q_sotto = ingressi[ingressi["scaglione"].isin(["[75, 80)"])]["n"].sum()
    q_sopra = ingressi[ingressi["scaglione"].isin(["[80, 85)"])]["n"].sum()

    md = f"""# Blocco 0 — Ricognizione dei dati

Generato da `scripts/run_blocco0.py` il {date.today().isoformat()}.
Nessun modello e' stato scritto, niente e' stato scaricato, niente e' stato
imputato. Tutte le tabelle di questo documento si rigenerano con un comando.

---

## Esito in una riga

**Il Blocco 0 si chiude su una delle due fonti e non sull'altra.** WhoScored e'
sul disco e misurato ({_mila(tot_file)} partite su {_mila(tot_cal)} di calendario,
{_mila(tot_eventi)} eventi, cinque stagioni) — con **cinque problemi che vanno
conosciuti prima di modellare**, elencati sotto. **I voti fantacalcio non
esistono nel repository**: non un file, non una riga. Ne segue che 0.2
(aggancio delle identita'), 0.3 (stabilita' del criterio di voto) e il tasso
d'errore di 0.4 **non sono calcolabili**, e non sono stati simulati.

I cinque problemi lato WhoScored, in ordine di quanto costano se scoperti dopo:

1. **{len(morte)} delle 259 colonne non sono mai valorizzate**, e fra queste ci sono
   tutte le `cleanSheet*` e le `goalConcededByTeam*` — cioe' esattamente quelle
   a cui il blocco P8 (portieri) allungherebbe la mano per prime. §1.4
2. **Il criterio descrittivo degli eventi si muove fra stagioni**, e si muove
   proprio sulle grandezze che servono al voto base (P2): `Clearance`
   {_var('Clearance'):+.0%}, `BallRecovery` {_var('BallRecovery'):+.0%},
   `Error` {_var('Error'):+.0%} fra la prima stagione e l'ultima. §1.5
3. **Due etichette di qualifier cambiano significato fra stagioni**
   (`StandingSave`, `OtherBodyPart`), e l'id numerico che permetterebbe di
   disambiguarle **e' scartato in acquisizione**. §1.6
4. **La giornata di campionato non esiste nei dati**, e non e' ricostruibile
   dall'ordine di `matches.json`, che e' cronologico e non per turno. Il
   bersaglio di P1 e' definito "alla giornata g". §1.7
5. **La chiave `(matchId, teamId, eventId)` ha una collisione** nel 2025-26,
   mentre il repository la documenta come unica. §1.8

Il resto del documento riporta i numeri. Le domande sono in fondo (§7), come da
modo di lavorare concordato.

---

## 1. (0.1) WhoScored — che cosa c'e' davvero sul disco

### 1.1 Sintesi per stagione

{_tab(sint_md)}

Le unita', che i nomi delle colonne non dicono: le coordinate `x`/`y`/`endX`/
`endY` sono **Opta 0-100 su entrambi gli assi** (non metri) e tutte le squadre
attaccano verso `x = 100`; `minute` e' il minuto di gioco, `expandedMinute`
include il recupero ed e' quello su cui il repository calcola i minuti, per cui
una partita dura 94-99 e non 90; `startDate` e' **solo la data**, senza orario
(`startTime` e' una colonna separata).

`squadre` e `giocatori` sono conteggi di identita' **WhoScored**: `teamId` e
`playerId`. I nomi delle squadre non stanno nei CSV — solo `teamId` — e si
ricavano incrociando `matchId` e casa/trasferta con `matches.json`.

### 1.2 Copertura

{_tab(cop_md)}

Nessun file contiene zero eventi, e nessun file sul disco e' fuori calendario.

### 1.3 Le {len(mancanti)} partite mancanti, e i denominatori che non sono 38

{_tab(mancanti[["stagione", "matchId", "casa", "ospite", "risultato"]])}

**La perdita non e' casuale rispetto alla squadra.** L'Atalanta ne perde 6 su
12, tre per stagione nelle due stagioni interessate:

{_tab(perdita_pos)}

E i denominatori non sono tutti 38, perche' il 2022-23 ha 381 partite in
calendario — c'e' il playout, che e' una partita vera:

{_tab(denom)}

> **Conseguenza operativa per ogni tasso per 90 delle fasi P.** Il denominatore
> di una squadra-stagione va **preso dai dati**, mai scritto 38. Per l'Atalanta
> 2021-22 e 2022-23 vale 35, per lo Spezia 2022-23 vale 39. Un tasso costruito
> su 38 sbaglia dell'8,6% sull'Atalanta, sempre nello stesso verso.

Le dodici assenze sono gia' accertate come **assenti alla fonte**
(`matchCentreData: null`), registrate in `data/raw/manifest.json` sotto
`assenti_alla_fonte`: non sono un difetto dell'acquisizione e non si recuperano.

### 1.4 Schema: 259 colonne, {vive} vive

Lo schema e' **stabile in senso stretto**: 259 colonne in tutte e cinque le
stagioni, nessuna che compaia o sparisca. L'unica non emessa in ogni file e'
`isOwnGoal`, che e' la trappola nota (pandas la omette quando nella partita non
ci sono autogol: {C[C['colonna'] == 'isOwnGoal']['quota_file'].min():.1%}–{C[C['colonna'] == 'isOwnGoal']['quota_file'].max():.1%} dei file per stagione).

**Ma "presente" non vuol dire "valorizzata", e la differenza qui e' enorme:
{len(morte)} colonne su 259 non contengono un solo valore in nessuna delle
cinque stagioni.** Sono presenti nell'intestazione e sempre vuote.

> **Nota di misura, ed e' il motivo per cui questo numero non era mai emerso.**
> Lo scraper scrive il literal `False` dove il campo Opta e' assente. Contare
> `notna()` e chiamarlo copertura fa risultare `cardType` "valorizzata al 100%"
> quando lo e' solo sui cartellini. La colonna `quota_valorizzata` di
> `blocco0_colonne.csv` conta i valori **ne' nulli ne' `False`**, ed e' quella
> da leggere.

Le {len(morte)} colonne morte, per famiglia:

- **`cleanSheet*` ({fam['cleanSheet']})** — porta inviolata per posizione in campo.
- **`goalConcededByTeam*` ({fam['goalConcededByTeam']})** e
  **`goalScoredByTeam*` ({fam['goalScoredByTeam']})** — gol subiti e segnati per
  posizione in campo.
- **`penaltyShootout*` ({fam['penaltyShootout']})** — vuote **attese**: in campionato
  non ci sono i rigori di fine partita. Sono l'unica famiglia la cui assenza non
  e' una notizia.
- le altre {len(resto)}: {", ".join(f"`{c}`" for c in resto)}.

`passThroughBallInacurate` e' un refuso di WhoScored, e accanto c'e' la forma
corretta `passThroughBallInaccurate`, che invece e' valorizzata: sono due
colonne distinte nello schema, una viva e una morta.

> **Questo tocca P8 direttamente.** La porta inviolata e i gol subiti del
> portiere **non si leggono**: `cleanSheetGK` e `goalConcededByTeamGK` sono
> vuote. Vanno derivati dagli eventi `Goal` per squadra-partita, che e' cio'
> che `sot/aggregate.py` gia' fa. Lo stesso vale per la precisione dei passaggi
> (`passAccuracy` vuota, si ricava da `passAccurate`/`passInaccurate`) e per le
> parate per zona, che non esistono affatto.

Un solo tipo si muove fra stagioni, ed e' l'artefatto di cui sopra:

{_tab(dtipi_misti.reset_index())}

`cardType` e' stringa pura in tutti i {int(C[(C['colonna'] == 'cardType') & (C['stagione'] == '2021-2022')]['file_con_colonna'].iloc[0])} file del 2021-22 e mista
booleana/stringa nelle altre quattro: nelle prime non c'e' una sola partita
senza cartellini, nelle altre si'. E' una proprieta' del calcio che si e'
travestita da proprieta' dello schema.

### 1.5 Tipi di evento: 39, tutti presenti in tutte le stagioni — ma non alle stesse frequenze

Nessun tipo di evento compare o sparisce. **Le frequenze pero' si muovono, e si
muovono proprio dove serve al voto base.** Frequenza per 1.000 eventi
(normalizzata: le stagioni hanno un numero diverso di partite acquisite):

{_tab(deriva_tipi.head(14))}

`rapporto` e' max/min fra le cinque stagioni. Le voci in cima sono tutte
azioni **difensive e di errore**, cioe' le feature naturali di P2 per difensori
e centrocampisti.

> **Non e' possibile dire da questi dati se sia calcio o annotazione**, ed e' la
> stessa impossibilita' gia' dichiarata in `reports/phase7_stabilita_rilevazione.md`:
> le due ipotesi lasciano la stessa firma. Quel che si puo' dire e' la
> **grandezza**, e a queste grandezze una regressione del voto base addestrata
> sul 2021-22 e applicata al 2025-26 sta usando due strati descrittivi diversi.
> La verifica di stabilita' gia' fatta riguardava **la definizione di tiro in
> porta**, che risulta stabile (identita' esatta col flag Opta su tutte e cinque
> le stagioni): non copre queste colonne, che nessuno aveva ancora guardato.

### 1.6 Qualifier: 114 etichette, e due che cambiano significato

Nessun qualifier con almeno 200 occorrenze e' assente da una stagione. Ma due
cambiano frequenza in modo che non e' deriva:

{_tab(dq_md)}

**`StandingSave` non e' una parata.** Nelle prime quattro stagioni compare su
circa il **71% di tutti gli eventi**, e su una partita presa a caso 683 delle
885 occorrenze stanno su eventi `Pass`. Un'etichetta che sta su due terzi dei
passaggi non sta descrivendo un portiere fermo sulla linea. Nel 2025-26 la
stessa etichetta compare su ~30 eventi per partita e **solo** su `Tackle`,
`Foul` e `Save` — cioe' su qualcosa di compatibile col nome.

**`OtherBodyPart` si comporta allo stesso modo, e nelle stesse partite.** Nel
2025-26 sopravvive in {obp_vive} partite su {len(QP)}, e le {vecchio} partite che
conservano il regime vecchio di `StandingSave` (piu' di un evento su quattro,
come nelle prime quattro stagioni, invece di ~30 per partita) sono fra queste.
La sovrapposizione e' quasi esatta: **{entrambe} delle {obp_vive}**.

> **La spiegazione economica e' una sola: due versioni del dizionario
> qualifier della fonte, e {vecchio} pagine del 2025-26 servite dalla versione
> vecchia.** Non e' un cambio di criterio di annotazione — e' la stessa
> etichetta appiccicata a id diversi.
>
> **E non e' disambiguabile dai dati in casa.** `acquisition/whoscored/main.py:432`
> fa `row[irow]['type'] = row[irow]['type']['displayName']`: **l'id numerico del
> qualifier viene buttato via** e resta solo il nome. Per sciogliere il nodo
> servirebbe riacquisire conservando l'id, il che tocca la rete e va deciso.
>
> Questo **precisa e in parte corregge** quanto sta in `CLAUDE.md` ("`StandingSave`
> c'e' su ~81% dei tiri nelle prime quattro stagioni e su ~2% nel 2025-26, [...]
> su 11 partite su 380 nel 2025-26 e zero esatto nelle altre"): misurato sui
> **tiri** e' cosi', misurato su **tutti gli eventi** l'etichetta e' viva in
> **{ss_vive} partite su {len(QP)}**, a un trentesimo del tasso. Il fatto nuovo e'
> che sta per due terzi sui passaggi, che e' quello che ne rivela la natura.
>
> **Nessuna colonna usata dalle Fasi 1-6 dipende da questi due qualifier**, quindi
> nessun numero pubblicato si muove. Il rischio e' a valle, sulle feature di P2.

### 1.7 La giornata di campionato non c'e'

Nessun CSV e nessun `matches.json` contiene il numero di turno. `matches.json`
**e' ordinato per data, non per giornata**: spezzandolo in blocchi di dieci,
un blocco che fosse una giornata conterrebbe venti squadre distinte, e invece:

{_tab(giorn_md)}

**L'ordine e' cronologico**, non per turno: le date crescono nel
{giorn['quota_ordine_cronologico'].min():.1%}-{giorn['quota_ordine_cronologico'].max():.1%} dei passi
consecutivi, e i turni rinviati bastano a mescolare i blocchi di dieci. Le date
testuali del JSON sono per giunta vuote su {int(giorn['date_vuote'].min())}-{int(giorn['date_vuote'].max())} voci per stagione — quelle
vere si prendono da `startDate` nei CSV.

> **Sostituto usato, e va dichiarato in ogni blocco che ne dipenda**: l'**indice
> cronologico di squadra** (l'ennesima partita di quella squadra in quella
> stagione), che e' completo — 38 per tutte le squadre in tre stagioni, 35-38
> nelle due con partite mancanti — ed e' la stessa grandezza che le Fasi 2-6
> chiamano `team_match_idx`. **Non e' la giornata**: per una squadra che ha
> giocato un recupero, indice e giornata divergono. Il bersaglio di P1 e'
> scritto "P(riceve voto alla giornata g)": se la giornata vera serve davvero,
> va presa da fuori. E' una domanda aperta (§7).

### 1.8 La chiave unica ha una collisione

Il repository documenta `(matchId, teamId, eventId)` come chiave unica con zero
duplicati. **Ce n'e' uno**, e sta nel 2025-26:

| stagione | duplicati su `(matchId, teamId, eventId)` | duplicati su `id` |
|---|---:|---:|
{chr(10).join(f"| {r.stagione} | {int(r.dup_chiave)} | {int(r.dup_id)} |" for r in sint.itertuples())}

Nella partita `1901279` (2026-04-26) l'`eventId` 838 della squadra 75 sta su due
eventi diversi: un `Save` a 84:29 e un `BallRecovery` a 84:32, giocatori
diversi. Non sono righe duplicate — sono due eventi veri con lo stesso numero,
esattamente come le 30 collisioni note su `id`, che restano (23-40 per stagione).

> **Perche' conta:** un `merge` su quella chiave duplica silenziosamente una
> riga. Su 2,8 milioni di eventi una riga non sposta nessuna stima, ma
> l'invariante va scritto giusto: **nessuna delle chiavi disponibili e' unica**,
> e l'unica difesa e' verificare la cardinalita' dopo ogni join invece di
> fidarsi. `blocco0_sintesi_stagioni.csv` porta le due colonne.

---

## 2. (0.1) I voti fantacalcio — accertamento di assenza

Il Blocco 0 chiede la ricognizione di **due** fonti. La seconda non c'e'. Non e'
un'impressione: sono i percorsi guardati, dalla tassonomia gia' fissata in
`sot/config.py`.

{_tab(voti)}

L'unico file in `data/external/` e' `quote/como_tiri_in_porta_2025-2026.xlsx`,
che riguarda i tiri in porta del Como e **non e' un listone di quotazioni**.

Ne segue, meccanicamente:

| punto del Blocco 0 | stato | perche' |
|---|---|---|
| 0.1 lato WhoScored | **chiuso** | §1 |
| 0.1 lato voti | **non calcolabile** | nessun dato |
| 0.2 corrispondenza giocatori e squadre | **non calcolabile** | una corrispondenza ha due lati; c'e' solo il sinistro (§3) |
| 0.3 stabilita' del criterio di voto | **non calcolabile** | tutte e otto le grandezze di §5 delle regole vivono nei voti |
| 0.4 tasso d'errore della regola dell'80' | **non calcolabile** | serve l's.v. **osservato**; c'e' solo il proiettato (§5) |

Lo stato dell'acquisizione, dai report esistenti e non da una nuova verifica:
`reports/phase7_fattibilita_fonte.md` ha accertato che gli endpoint di export
rispondono **401** senza credenziali, che la vista HTML e' pubblica su tutte e
cinque le stagioni, e che **i minuti nella fonte non ci sono** (per questo i
minuti vengono da WhoScored). `docs/regole_fantacalcio.md` §7.1 registra
l'autorizzazione dichiarata dall'utente e lascia **`[NON DECISO]`** da quale
delle due vie si acquisisce. **Finche' quella decisione non e' presa, non c'e'
niente da scaricare e il Blocco 0 non si puo' chiudere.**

---

## 3. (0.2) Identita': c'e' solo il lato WhoScored, ed e' scritto

Le tabelle di corrispondenza non esistono e **non sono state create vuote**: un
file con la colonna dei voti a `NA` verrebbe letto a valle come "aggancio
fallito" invece che "aggancio mai tentato", e sarebbe il segnaposto che la
regola di condotta 1 vieta. Un test lo blocca
(`test_mapping_non_contiene_colonne_di_voto`).

Cio' che c'e' e' l'**anagrafica WhoScored**, che e' il lato sinistro di
entrambe le corrispondenze e serve comunque:

{chr(10).join(f"- `{p.relative_to(config.ROOT)}`".replace(chr(92), "/") for p in scritti)}

**Squadre**: {sq['nome_whoscored'].nunique()} nomi distinti su cinque stagioni, 20 per stagione.
Il `partite` e' il numero di partite **con un CSV sul disco**, non quelle di
calendario (§1.3).

{_tab(squadre_piv)}

> Gia' visibile senza il lato destro: **`Parma Calcio 1913`** e' la forma
> WhoScored, e nessuna fonte italiana di voti la scrive cosi'. Le squadre sono
> 27 in tutto e la corrispondenza si fa a mano in dieci minuti — **e va fatta a
> mano**, perche' un fuzzy su 27 nomi non ha alcun vantaggio e ha il rischio di
> agganciare `Verona` a `Venezia`.

**Giocatori**: {_mila(reg['playerId'].nunique())} `playerId` distinti su cinque stagioni,
{reg.groupby('stagione')['playerId'].nunique().min()}-{reg.groupby('stagione')['playerId'].nunique().max()} per stagione. I casi che il Blocco 0
chiede di gestire esplicitamente, contati **dentro WhoScored** (il conteggio
sul lato voti sara' diverso, e la loro intersezione e' il rischio vero):

| caso | righe giocatore-stagione | lettura |
|---|---:|---|
| omonimi (stesso nome, `playerId` diversi, stessa stagione) | {len(anom['omonimi'])} | **nessuno**: WhoScored non ha omonimi interni. Non dice niente sul lato voti, dove i cognomi sono spesso soli |
| piu' grafie dello stesso `playerId` | {len(anom['multigrafia'])} | **nessuna**: WhoScored e' internamente coerente sulla grafia |
| piu' squadre nella stessa stagione (mercato di gennaio, prestiti) | {len(anom['multisquadra'])} | ~{len(anom['multisquadra']) / 5:.0f} per stagione, il {len(anom['multisquadra']) / len(reg):.1%} delle righe |
| nome di un solo token | {len(anom['nome_singolo'])} | brasiliani e portoghesi (`Dalbert`, `Bremer`, `Beto`, `Danilo`) |
| nome con caratteri non ASCII | {len(anom['nome_non_ascii'])} | il {len(anom['nome_non_ascii']) / len(reg):.0%} delle righe: `Ribéry`, `Kjær`, `Tolói`, `Mäenpää` |

I file `whoscored_anomalie_*.csv` in `data/mapping/` contengono gli elenchi
completi, che sono il materiale da rivedere a mano quando il lato destro
arrivera'.

> **Il tasso di aggancio richiesto (soglia 98%) non e' misurabile e non e'
> stimabile.** Il rischio non e' distribuito uniformemente: si concentra sui
> {len(anom['nome_non_ascii'])} nomi non ASCII, sui {len(anom['nome_singolo'])} a
> token singolo e sui {len(anom['multisquadra'])} con due squadre — dove
> l'aggancio va fatto **per stagione e per squadra**, non per nome, altrimenti un
> giocatore ceduto a gennaio si aggancia alla squadra sbagliata per meta'
> stagione senza che niente lo segnali.

---

## 4. (0.3) Stabilita' del criterio di voto — non calcolabile

Le otto grandezze chieste da `docs/regole_fantacalcio.md` §5 (voto medio
complessivo e per ruolo, deviazione standard, percentuale di s.v.,
distribuzione dei voti, fantamedia per ruolo, frequenza di bonus e malus,
provider dichiarato) **vivono tutte nei voti**. Nessuna e' derivabile dagli
eventi. Non e' stata calcolata nessuna approssimazione.

I minuti medi giocati — l'unica delle otto che sta in WhoScored — sono gia'
riconciliati esattamente su 760/760 squadra-partita per il 2025-26
(`reports/phase1_audit.md`). **Per le altre quattro stagioni la catena dei
minuti non e' ancora costruita**: `sot/minutes.py` gira sulla stagione di
`config.SEASON`. E' lavoro noto e non bloccante, ma va contato.

---

## 5. (0.4) La regola dell'80' — c'e' il denominatore, non il tasso d'errore

`docs/regole_fantacalcio.md` §1.2 chiede il tasso d'errore **nei due versi**:
chi entra dopo l'80' e un voto lo prende, chi entra prima e non lo prende.
**Tutti e due hanno bisogno dell's.v. osservato**, che sta nei voti. Non
calcolato, non stimato.

Cio' che si puo' misurare e' **quanta massa la regola sposta**, sul 2025-26:

| grandezza | valore |
|---|---:|
| righe giocatore-partita con almeno un minuto giocato | {_mila(e80['righe_scese_in_campo'])} |
| di cui titolari | {_mila(e80['titolari'])} |
| di cui subentrati | {_mila(e80['subentrati'])} |
| marcate **s.v. proiettato** dalla regola (ingresso ≥ 80' su `expandedMinute`) | **{_mila(e80['sv_proiettato'])}** |
| quota sul totale di chi e' sceso in campo | {e80['quota_sv_proiettato']:.1%} |
| quota fra i soli subentrati | {e80['quota_sv_fra_subentrati']:.1%} |

Tre fatti che la regola porta con se', e che vanno accanto a ogni numero che vi
poggi:

1. **La soglia cade nel punto di massima densita' degli ingressi.** Lo scaglione
   [75, 80) contiene {int(q_sotto)} ingressi e lo scaglione [80, 85) ne contiene
   {int(q_sopra)}: **spostare la soglia di cinque minuti sposta ~{int(min(q_sotto, q_sopra))} righe**, cioe'
   il {min(q_sotto, q_sopra) / e80['righe_scese_in_campo']:.1%} di tutte le righe. La regola e' nel punto in cui e' piu'
   sensibile alla propria posizione. Distribuzione completa in
   `blocco0_ingressi_per_minuto.csv`.
2. **Su `expandedMinute` l'80' non e' l'80'.** La partita dura 94-99 minuti,
   quindi chi entra all'80' espanso gioca fino a {int(e80['minuti_max_sv'])} minuti
   (mediana {int(e80['minuti_mediani_sv'])}), e **{int(e80['sv_con_almeno_15_min'])} delle {int(e80['sv_proiettato'])} righe marcate s.v.
   hanno almeno 15 minuti giocati**. La scelta di `expandedMinute` e'
   dell'utente ed e' coerente con tutto il repository; la conseguenza, che va
   detta accanto, e' che la regola e' **piu' permissiva** di quanto "80'"
   suggerisca, non meno.
3. **La regola non copre il titolare che esce presto.** Nel 2025-26 ci sono
   {int(e80['titolari_usciti_entro_10'])} titolari usciti prima del 10' e {int(e80['titolari_usciti_entro_20'])} prima del 20' —
   infortuni ed espulsioni. Se la scala Redazione da' loro s.v., la regola non
   lo prevede: e' un verso d'errore **strutturale**, non campionario, e non e'
   fra i due che §1.2 chiede di misurare.

---

## 6. Le quattro contraddizioni sciolte prima di scrivere codice

Come richiesto, con la mia lettura di ciascuna. **Nessuna e' stata risolta da
me**: sono in §7 come domande.

**(1) La sezione 0 dichiara aperte decisioni che gli YAML piu' avanti hanno gia'
un valore.** La mia lettura: **gli YAML sono segnaposto illustrativi, la sezione
0 e' aggiornata**, e non il contrario. Tre indizi. `0.1` e' seguita nel testo da
`[DA DECIDERE 0.1] — le fasce sono 3` (una decisione presa) *e* da un blocco
YAML con tre fasce che porta ancora il marcatore `[DA DECIDERE 0.1]` sopra le
soglie: il numero di fasce e' deciso, le **soglie** no. Stessa forma per `0.4`,
dove `— malus di -1` e' deciso e `sotto_soglia_minima: -1` lo riflette. Per
`0.2` (`n_difensori: 4`) e `0.5` non c'e' nessuna riga di decisione nel testo,
solo lo YAML: quelli sono i due davvero aperti. Il commento `# tipicamente 3 o 4`
accanto a `n_difensori: 4` e' scritto da chi propone, non da chi decide.

**(2) `n_difensori: 4` e' incompatibile con i moduli ammessi, e §3.2 pretende un
test di coerenza che fallirebbe sempre.** La mia lettura: **`n_difensori` non
puo' essere una costante**. I sette moduli ammessi schierano 3, 4 o 5
difensori; con `n_difensori` fisso a 4 il test di §3.2 e' insoddisfacibile per
costruzione. Le letture possibili sono due e danno codice diverso:
(a) il modificatore usa il portiere **piu' i migliori `n` difensori schierati**
con `n` che dipende dal modulo — allora la simulazione F2 deve girare **per
modulo** e il contributo marginale di §2.2 e' relativo a una linea *e* a un
modulo; (b) il regolamento fissa un `n` unico (tipicamente 4) **indipendente**
dal modulo, prendendo i migliori 4 fra i difensori schierati e ignorando il
quinto, il che rende il 5-3-2 diverso dal 3-5-2 nel valore dei difensori.
Sono le due letture piu' comuni nelle leghe reali e **non si distinguono dal
documento**. Non ho scelto.

**(3) La copertura dei voti e' dichiarata in due modi diversi.** §1.2 da' l's.v.
osservato su 2021/22-2025/26; §7.1 punto 2 dice che la 2025/26 e' l'unica con
entrambe le fonti. La mia lettura: **non sono in contraddizione, dicono due cose
diverse** — la prima e' la copertura dei *voti*, la seconda la copertura di
*voti* **e** *minuti* insieme. Il fatto misurato sul disco e' pero' un terzo:
**nessuna delle due e' verificabile, perche' i voti non ci sono in nessuna
stagione** (§2). Sul disco la copertura dei voti e' zero su cinque; quella dei
minuti e' cinque su cinque, ma la catena dei minuti e' costruita per una sola
(§4).

**(4) Nomenclatura.** Il repository numera per **fase** (`Fase 0`…`Fase 7`,
report `phaseN_*.md`) e `docs/regole_fantacalcio.md` chiama gia' `8A` il voto
base e `8D` il modificatore, cioe' **Fase 8 = fantacalcio**. Il prompt usa
`Blocco 0`, `T1-T5`, `P1-P9`, `F1-F5`. Cio' che ho adottato, e che si puo'
cambiare con una riga: **`Fase 8` come contenitore**, e **i nomi `T`/`P`/`F` del
prompt per i blocchi**, perche' sono piu' fini di `8A`/`8D` e mappano uno a uno
sui moduli. Il deliverable resta `reports/blocco0_ricognizione.md`, che e' il
nome che il prompt chiede esplicitamente, **e questa e' l'unica incoerenza con
`phaseN_*`**: la segnalo invece di rinominare di mia iniziativa. La
corrispondenza con i nomi gia' scritti nelle regole e' `8A = P2` (voto base) e
`8D = F3` (modificatore).

---

## 7. Domande aperte — qui il blocco si ferma

**Bloccanti: senza queste non si scrive una riga di modello.**

**D1. I voti fantacalcio: dove sono?** Il prompt dice "ho i voti fantacalcio
della stessa finestra", il disco dice di no (§2). Le possibilita' sono che
esistano fuori dal repository, oppure che vadano ancora acquisiti. Se vanno
acquisiti, resta aperto **da quale via** — `docs/regole_fantacalcio.md` §7.1 la
lascia `[NON DECISO]` fra export Excel da sessione autenticata (serve che tu
faccia login: gli endpoint danno 401) e vista HTML pubblica. **Non procedo su
nessuna delle due senza che tu scelga**, ed entrambe toccano la rete.

**D2. Le quotazioni del listone, idem.** Non sono sul disco. Sono la **terza
baseline obbligatoria** della sezione di validazione e l'oggetto di F5, cioe'
la verifica principale del progetto. Senza, F5 non esiste e le altre due
baseline non bastano a dire se il modello ha valore d'uso.

**D3. `n_difensori` e' fisso o dipende dal modulo?** (contraddizione 2). Cambia
la forma della simulazione F2 e del contributo marginale F3, quindi va deciso
prima di scriverli, non dopo.

**D4. Le soglie delle fasce del modificatore** restano `[DA DECIDERE 0.1]` anche
nella lettura piu' generosa (§6.1): il numero di fasce e' deciso (tre), i valori
6.00 / 6.50 / 7.00 dello YAML no. Confermi quelli o sono illustrativi?

**D5. Il formato della lega** (`[DA DECIDERE 0.5]`): 8 squadre, budget 1000,
rosa 3/8/8/6 sono valori reali o segnaposto? Il budget in particolare — senza,
il confronto valore/quotazione non e' definibile.

**Non bloccanti, ma da decidere prima del blocco che le usa.**

**D6. La giornata di campionato** (§1.7). Il bersaglio di P1 e' scritto "alla
giornata g", e la giornata non e' nei dati. Tre vie: (a) usare l'indice
cronologico di squadra e riscrivere il bersaglio di conseguenza — costa zero e
diverge dalla giornata vera solo sui recuperi; (b) prendere la giornata dalla
fonte dei voti, che l'ha di sicuro, ma la lega a un aggancio che non esiste
ancora; (c) prenderla da una terza fonte. La (a) e' quella che consiglierei,
dichiarando la divergenza.

**D7. I due qualifier con l'id buttato via** (§1.6). Se le feature di P2 devono
usare i qualifier, l'id numerico serve, e per riaverlo bisogna riacquisire.
**Non lo faccio senza un tuo via**, perche' tocca la rete e perche' riacquisire
sovrascriverebbe — che il vincolo 9 vieta. La domanda vera e' se P2 possa
vivere sui **tipi di evento** e sulle colonne booleane, che sono stabili nello
schema, invece che sui qualifier.

**D8. La deriva delle frequenze degli eventi** (§1.5). `Clearance` +48% e
`BallRecovery` −26% fra il 2021-22 e il 2025-26. Tre opzioni: stimare P2 per
stagione con un effetto di stagione esplicito; restringere il perimetro alle
stagioni piu' recenti; oppure normalizzare per stagione ciascuna feature — che
e' l'unica delle tre che *cambia il dato*, e che secondo il vincolo di §5 delle
regole va documentata e misurata, non applicata in silenzio. **Come per la
normalizzazione del criterio di voto: la scelgo io o la scegli tu?** Il
documento dice che la normalizzazione la decidi tu.

**D9. Perimetro temporale.** La 2021-22 e' gia' dichiarata non confrontabile sul
vantaggio del campo (ritorno del pubblico), ed e' anche l'estremo di quasi tutte
le derive di §1.5, e una delle due che perdono partite. Vale la pena tenerla?
E' una domanda di costi e benefici come quella che la Fase 6F si e' posta sul
piano dati, non una questione tecnica.

---

## Cosa e' stato prodotto

| | |
|---|---|
| `sot/ricognizione.py` | il modulo di misura, {vive} colonne vive su 259 misurate su 1.889 file |
| `scripts/run_blocco0.py` | rigenera tutto con un comando |
| `tests/test_ricognizione.py` | invarianti, compresi quelli che **vietano il segnaposto** sui voti |
| `reports/blocco0_ricognizione.md` | questo documento |
| `reports/blocco0_*.csv` | {len(csvs)} tabelle |
| `data/mapping/whoscored_*.csv` | anagrafiche e anomalie, **solo lato WhoScored** |
| `data/processed/ITA-serie-a/blocco0_*.parquet` | cache della scansione, rigenerabile con `--force` |

Nessun modello, nessuna stima, nessuna riga scritta sotto `data/raw/`, nessuna
richiesta di rete, nessuna dipendenza aggiunta.
"""
    OUT_MD.write_text(md, encoding="utf-8")
    print(f"scritto {OUT_MD}")
    print(f"scritte {len(csvs)} tabelle in {config.REPORTS}")
    print(f"scritti {len(scritti)} file in {R.MAPPING_DIR}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true",
                    help="rilegge i 1.889 CSV invece di usare la cache (~3 min)")
    main(**vars(ap.parse_args()))
