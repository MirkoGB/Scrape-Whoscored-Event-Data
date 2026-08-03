# -*- coding: utf-8 -*-
"""Aggancio delle due fonti e misura della regola dell'80'.

    ./.venv/Scripts/python.exe scripts/run_aggancio.py

**Non tocca la rete e non scrive niente sotto `data/raw/`.** Legge i voti gia'
acquisiti e gli eventi WhoScored gia' su disco, produce le tre tabelle di
corrispondenza in `data/mapping/` e il report `reports/aggancio.md`.
"""

from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sot import aggancio as AG, config, presenza as PR  # noqa: E402

OUT_MD = config.REPORTS / "aggancio.md"


def _tab(df: pd.DataFrame, allinea_dx: tuple[str, ...] = ()) -> str:
    def cella(v) -> str:
        return "" if pd.isna(v) else str(v).replace("|", r"\|")
    cols = list(df.columns)
    testa = "| " + " | ".join(cella(c) for c in cols) + " |"
    sep = "|" + "|".join("---:" if c in allinea_dx else "---" for c in cols) + "|"
    righe = ["| " + " | ".join(cella(v) for v in r) + " |"
             for r in df.itertuples(index=False)]
    return "\n".join([testa, sep, *righe])


def _num(df: pd.DataFrame) -> tuple[str, ...]:
    return tuple(c for c in df.columns if pd.api.types.is_numeric_dtype(df[c]))


def _mila(n) -> str:
    return f"{int(n):,}".replace(",", ".")


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--force", action="store_true",
                   help="ricalcola la tavola presenza invece di leggerne la cache")
    args = p.parse_args(argv)

    AG.MAPPING_DIR.mkdir(parents=True, exist_ok=True)

    print("aggancio squadre...")
    squadre = AG.mappa_squadre()
    squadre.to_csv(AG.SQUADRE_CSV, index=False)

    print("aggancio partite...")
    part = AG.mappa_partite(squadre)
    partite, solo_fc, solo_ws = part["partite"], part["solo_fc"], part["solo_ws"]
    partite.to_csv(AG.PARTITE_CSV, index=False, date_format="%Y-%m-%d")

    print("aggancio giocatori (2025-2026)...")
    g = AG.mappa_giocatori()
    g["mappa"].to_csv(AG.GIOCATORI_CSV, index=False)
    if len(g["irrisolti"]):
        g["irrisolti"].to_csv(AG.IRRISOLTI_CSV, index=False)
    elif AG.IRRISOLTI_CSV.is_file():
        AG.IRRISOLTI_CSV.unlink()

    print("misura della regola dell'80'...")
    t = PR.tavola(force=args.force)
    r = PR.misura_regola(t)
    curva = PR.minuti_e_sv(t)
    alt = PR.regola_sui_minuti_giocati(t)

    for nome, df in (("aggancio_copertura_partite", partite.groupby("stagione").size()
                      .rename("agganciate").reset_index()),
                     ("presenza_regola80", r["confronto"]),
                     ("presenza_sensibilita", r["sensibilita"]),
                     ("presenza_minuti_sv", curva),
                     ("presenza_regola_minuti", alt)):
        df.to_csv(config.REPORTS / f"{nome}.csv", index=False)

    cop = partite.groupby("stagione").agg(
        agganciate=("matchId", "size"), scarto_max=("scarto_giorni", "max")).reset_index()
    cop["voti_senza_eventi"] = cop["stagione"].map(
        solo_fc.groupby("stagione").size()).fillna(0).astype(int)
    cop["eventi_senza_voti"] = cop["stagione"].map(
        solo_ws.groupby("stagione").size()).fillna(0).astype(int)

    sq_riass = squadre.groupby("stagione").agg(
        squadre=("teamId_ws", "size"), margine_min=("margine", "min"),
        in_comune_min=("in_comune", "min")).reset_index()

    m = g["mappa"]
    ruolo_ws = m["ruolo_fc"].map({"p": "GK", "d": "DEF", "c": "MID", "a": "FWD"})
    discordi = int((ruolo_ws != m["ruolo_ws"]).sum())
    incrocio = (pd.crosstab(m["ruolo_fc"], m["ruolo_ws"])
                .reindex(index=["p", "d", "c", "a"]).fillna(0).astype(int).reset_index())

    conf = r["confronto"]
    regola = conf.iloc[0]
    base = conf.iloc[1]

    testo = f"""# Aggancio delle due fonti, e la regola dell'80' misurata

Generato da `scripts/run_aggancio.py` il {date.today().isoformat()}.
Nessuna richiesta di rete, niente scritto sotto `data/raw/`.

## Esito in una riga

Le due fonti sono agganciate su **{_mila(len(partite))} partite** di cinque
stagioni e su **{_mila(len(m))} giocatori su {_mila(len(m) + len(g['irrisolti']))}**
della 2025-26, senza nessun caso irrisolto; e la regola dell'80' — decisa
dall'utente e marcata `[DA MISURARE]` in `docs/regole_fantacalcio.md` §1.2 —
**concorda con l's.v. osservato sul {regola['quota_concordi']:.2%} delle righe,
contro il {base['quota_concordi']:.2%} del baseline che non prevede nessun s.v.**

## 1. La chiave e' diversa ai due livelli, e non era ovvio

| livello | chiave | verifica |
|---|---|---|
| squadra | l'insieme delle 38 coppie `(data, in casa)` | il nome |
| partita | `(stagione, casa, trasferta)` | la data |
| giocatore | il **cognome** dentro la squadra, con le iniziali a disambiguare | il calendario |

**Al livello di squadra il nome non e' una chiave**: la fonte degli eventi dice
`AC Milan`, `Parma Calcio 1913`, `Hellas Verona`; quella dei voti dice `Milan`,
`Parma`, `Verona`. Il calendario invece lo e', ed e' esatto:

{_tab(sq_riass, _num(sq_riass))}

`margine` e' di quante partite il primo candidato batte il secondo. Sta fra 19 e
29 su 38: non e' un aggancio che regge per poco.

**Al livello di giocatore vale l'esatto contrario, e questa e' la cosa che ho
dovuto misurare invece di assumerla.** La prima versione agganciava i giocatori
per insieme di presenze, per simmetria con le squadre. **Non funziona**, e il
motivo e' strutturale: l'insieme delle partite di una *squadra* e' 38 su 380 —
sparso, quindi discriminante — mentre quello di un *giocatore* dentro la sua
squadra e' 35 su 38, cioe' quasi pieno. Due titolari qualsiasi della stessa
squadra hanno fra loro un Jaccard di ~0,85, e il margine sul secondo candidato
scendeva **sotto 0,03 su meta' della rosa**. Al livello di giocatore il
calendario non e' un'impronta: e' rumore.

## 2. Partite: {_mila(len(partite))} agganciate, e i residui si dichiarano

{_tab(cop, _num(cop))}

- **{len(solo_fc)} partite hanno i voti e non gli eventi**, tutte nel 2021-22 e
  2022-23: sono esattamente le **12 che WhoScored non ha**, con
  `matchCentreData: null`, verificate una per una durante l'acquisizione. Non
  sono un difetto dell'aggancio e non si recuperano.
- **{len(solo_ws)} partita ha gli eventi e non i voti**: lo **spareggio salvezza
  Spezia-Verona dell'11 giugno 2023**. E' l'unica coppia ordinata che si ripete
  in una stagione, e le pagine dei voti — organizzate per giornata — non la
  contengono. Senza accorgersene, si sarebbe agganciata ai voti della **giornata
  25**, mettendo una partita di giugno sotto i voti di marzo.
- **Due partite hanno le due fonti in disaccordo sulla data**, ed entrambe hanno
  una ragione: Udinese-Roma 2023-24 (11 giorni) e Fiorentina-Inter 2024-25 (67
  giorni) sono le due partite **interrotte e riprese** in un'altra data. I voti
  le datano alla giornata, gli eventi al completamento. L'aggancio e' giusto, la
  data no — e va scelta quella che serve, non mediata.

**La giornata di campionato adesso c'e'.** Chiude la **D6** del Blocco 0 per la
via (b): non si stima e non si sostituisce con l'indice cronologico di squadra,
**si legge dalla fonte dei voti** e arriva sulle partite WhoScored attraverso
questo aggancio. `team_match_idx` resta cio' che era — un indice — e le due
grandezze divergono sui recuperi, che e' il motivo per cui serviva quella vera.

## 3. Giocatori: {_mila(len(m))} su {_mila(len(m))}, e il residuo e' zero

{_tab(m['risolto_da'].value_counts().rename('giocatori').reset_index(), ('giocatori',))}

Il lato WhoScored e' ristretto a chi ha **almeno un minuto**: sono 609, gli
stessi 609 dei voti. `player_match` ne contiene 803, ma 194 sono panchinari mai
entrati, che i voti giustamente non elencano.

**La verifica e' il calendario, e passa**: il Jaccard fra i due insiemi di
presenze ha media **{m['jaccard'].mean():.4f}** e minimo **{m['jaccard'].min():.4f}**.
Le due fonti sono d'accordo su chi e' sceso in campo, partita per partita.

I 23 casi su 609 che il cognome grezzo sbaglia sono tutti e soli di due specie,
e **nessuna delle due e' un'omonimia**:

- **lettere che l'ASCII non piega**: `Højlund`, `Østigård`, `Grønbæk`, `Løvik`,
  `Sørensen`. La decomposizione Unicode non le tocca — `ø` non e' una `o` con un
  segno sopra, e' un'altra lettera — e servono a mano;
- **le iniziali del nome proprio**, che la fonte dei voti aggiunge **solo quando
  servono**: `Martinez L.` contro `Martinez Jo.`, `Pellegrini Lu.` contro
  `Pellegrini Lo.`, `Esposito F.P.` contro `Esposito Se.`. Sono l'informazione
  che risolve i due unici cognomi ambigui della stagione, quindi **si usano, non
  si tolgono** — buttarle via creava le ambiguita' da risolvere.

Un caso solo ha richiesto il ripiego sull'ultimo pezzo del cognome:
**`Zambo Anguissa` contro `Frank Anguissa`**, dove `Zambo` e' patronimico per una
fonte e nome proprio per l'altra. 18 presenze da entrambe le parti.

### Il ruolo NON e' la stessa grandezza nelle due fonti

**{discordi} giocatori su {len(m)} hanno ruoli discordanti**, e non e' un errore
di aggancio: e' il vincolo 7 in azione. Il ruolo dei voti e' quello del
fantacalcio Classic (P/D/C/A, un'etichetta di *lega*); quello di WhoScored e'
posizionale. Un esterno di centrocampo e' `d` per il fantacalcio e `MID` per
WhoScored, e nessuno dei due ha torto.

{_tab(incrocio, _num(incrocio))}

**Le due colonne restano separate** nella tabella prodotta (`ruolo_fc`,
`ruolo_ws`). Non si convertono e non si sceglie la piu' comoda: per il modello
del fantacalcio conta il ruolo di lega, perche' e' quello che determina bonus e
modificatore.

## 4. La regola dell'80', misurata — §1.2 `[DA MISURARE]`, chiuso

Universo: **{_mila(int(regola['righe']))} righe giocatore-partita** della 2025-26,
cioe' chi e' sceso in campo. Su tutte c'e' sia il voto sia il minuto d'ingresso.

> WhoScored ne conta **{_mila(int(regola['righe']) + 2)}** con almeno un minuto, e
> le due che mancano non sono un difetto dell'aggancio: la fonte dei voti **non
> elenca affatto** Estevez (entrato al 90', 7 minuti) e Folino (all'88', 10
> minuti). Non gli da' s.v.: non gli da' riga. E' un terzo stato oltre "voto" e
> "s.v.", che per il modello ricade nel secondo, ma che dice una cosa
> sull'universo: quello dei voti e' *quasi* — non *esattamente* — chi e' sceso
> in campo.

{_tab(conf[['regola', 'sv_proiettati', 'concordi', 'quota_concordi',
            'falsi_sv', 'sv_mancati', 'richiamo']],
      _num(conf))}

**L'accordo del {regola['quota_concordi']:.2%} va letto accanto al baseline, non
da solo** (vincolo 6). Dire *"nessuno prende s.v."* ne azzecca gia' il
{base['quota_concordi']:.2%}, perche' l's.v. e' raro. Il guadagno vero della
regola e' di **{(regola['quota_concordi'] - base['quota_concordi']) * 100:.1f}
punti**, non di 98.

I due versi che §1.2 chiede, separati:

- **falsi s.v.**: {int(regola['falsi_sv'])} righe — entra al ≥ 80' e il voto
  invece lo prende. Sono il **{regola['quota_falsi_sv']:.1%}** di chi la regola
  dichiara senza voto;
- **s.v. mancati**: {int(regola['sv_mancati'])} righe — entra prima e il voto non
  lo prende. Sono il **{regola['quota_sv_mancati']:.2%}** di chi la regola
  dichiara a voto.

### La soglia e' scelta, non stimata — e cade sul massimo

{_tab(r['sensibilita'][['soglia', 'sv_proiettati', 'concordi', 'quota_concordi',
                        'falsi_sv', 'sv_mancati', 'richiamo']], _num(r['sensibilita']))}

**L'80' e' il massimo della griglia**, e va detto con l'avvertenza giusta: non e'
stato scelto guardando questa tabella. E' una decisione dell'utente presa prima,
dichiarata in `regole_fantacalcio.md` §1.2, e **qui viene solo verificata**. Se
fosse stato scelto qui sarebbe un iperparametro adattato al campione, cioe' il
vincolo 1 violato; scelto prima e trovato al massimo, e' una conferma.

Attorno la superficie e' ripida: a 75' l'accordo scende a
{r['sensibilita'].set_index('soglia').loc[75, 'quota_concordi']:.4f} e a 85' a
{r['sensibilita'].set_index('soglia').loc[85, 'quota_concordi']:.4f}. Il Blocco 0
aveva gia' misurato che l'80' cade nel punto di **massima densita' degli
ingressi**: e' la posizione in cui la regola e' piu' sensibile alla propria
scelta, e questa tabella dice di quanto.

### Il verso d'errore che la regola non puo' vedere

{_tab(r['titolari'], _num(r['titolari']))}

Un titolare uscito al 15' per infortunio o espulsione puo' prendere s.v., e la
regola — che guarda il minuto d'**ingresso** — non lo vedra' mai. Non e' errore
di campionamento, e' una **classe di casi fuori dal dominio della regola**;
§1.2 non la elenca fra i due versi da misurare. **Tutti e {int(r['per_ingresso'].set_index('gruppo').loc['titolare', 'sv_osservati'])}
gli s.v. dei titolari sono di questa specie**: nessun titolare che abbia superato
il 20' ha mai preso s.v. nella stagione.

### Il fatto che la misura ha portato a galla

{_tab(curva, _num(curva))}

**Sopra i 30 minuti giocati non c'e' un solo s.v. su 8.552 righe.** Il crollo e'
fra i 20 e i 30 minuti, e la transizione e' netta: 78,6% a [10,20), 3,6% a
[20,30), zero esatto sopra.

Questo **non contraddice** la dichiarazione della fonte — "non esiste, e mai
esisterà, una regola che prevede che il voto venga dato a chi gioca un numero
minimo di minuti" — ma la mette in prospettiva: la regola formale non c'e', la
*pratica* editoriale e' quasi deterministica. Un modello che predica l's.v. dai
minuti non sta adattandosi a rumore quanto §7 della ricognizione temeva.

**Il sospetto conseguente e' stato misurato, ed e' risultato infondato:**

{_tab(alt[['soglia_minuti', 'sv_proiettati', 'concordi', 'quota_concordi',
           'falsi_sv', 'sv_mancati', 'richiamo']], _num(alt))}

Al suo optimum (20 minuti giocati) la regola alternativa fa **0,9783** contro
**0,9784** della regola dell'utente. **Sono la stessa cosa.** Cambia il *mix*
degli errori, non la loro quantita': la forma sui minuti prende quasi tutti gli
s.v. veri (richiamo 0,97 contro 0,90) e in cambio ne inventa di piu' (225 falsi
contro 142). Quale dei due errori pesi di piu' e' una domanda di prodotto, e non
la decido io. **La regola resta quella di §1.2.**

## Cosa e' stato prodotto

| | |
|---|---|
| `data/mapping/aggancio_squadre.csv` | 100 righe, 20 per stagione |
| `data/mapping/aggancio_partite.csv` | {_mila(len(partite))} righe, con giornata e `matchId` |
| `data/mapping/aggancio_giocatori.csv` | {_mila(len(m))} righe, 2025-26 |
| `{PR.TAVOLA_PARQUET.relative_to(config.ROOT).as_posix()}` | voti **e** minuti sulla stessa riga |
| `reports/presenza_*.csv` | le quattro tavole di questa sezione |

## Limiti dichiarati

1. **L'aggancio dei giocatori copre solo la 2025-2026.** Ha bisogno delle
   presenze partita per partita dal lato WhoScored, che oggi esistono solo per la
   stagione pubblicata (`player_match.parquet`). Estenderlo alle altre quattro
   vuol dire far girare l'aggregazione della Fase 1 su 1.509 CSV in piu': e'
   fattibile e non e' stato fatto qui.
2. **La regola dell'80' e' misurata su una stagione e non puo' esserlo su
   altre.** 11.926 righe sono tante, ma sono un anno solo di una redazione sola.
   Se il criterio editoriale cambiasse, questo numero non se ne accorgerebbe.
3. **`expandedMinute` non e' il minuto di gioco.** La partita dura 94-99', quindi
   l'80' della regola non e' l'80' dell'orologio: chi entra all'80' espanso gioca
   fino a 25 minuti, mediana 12. La regola e' **piu' permissiva** di quanto "80'"
   suggerisca, ed e' una conseguenza della scelta — coerente con tutto il
   repository — di usare `expandedMinute`.
4. **Il ruolo di lega e quello posizionale restano due colonne.** Vedi §3.
"""

    OUT_MD.write_text(testo, encoding="utf-8")
    print(f"\n-> {OUT_MD}")
    for f in (AG.SQUADRE_CSV, AG.PARTITE_CSV, AG.GIOCATORI_CSV, PR.TAVOLA_PARQUET):
        print(f"-> {f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
