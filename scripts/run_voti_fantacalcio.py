# -*- coding: utf-8 -*-
"""Dai grezzi di fantacalcio.it ai Parquet, al manifest e al report.

    ./.venv/Scripts/python.exe scripts/run_voti_fantacalcio.py

**Non tocca la rete.** Legge le pagine gia' scaricate da
`acquisition/fantacalcio/scrape_voti.py`, le passa al parser, verifica, scrive
i due Parquet, aggiorna `data/raw/manifest.json` e rigenera
`reports/voti_fantacalcio.md` con le tabelle di contorno.
"""

from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from acquisition import manifest  # noqa: E402
from acquisition.fantacalcio import pagina as P, target as T  # noqa: E402
from sot import config, voti as V  # noqa: E402

OUT_MD = config.REPORTS / "voti_fantacalcio.md"


def _tab(df: pd.DataFrame, allinea_dx: tuple[str, ...] = ()) -> str:
    def cella(v) -> str:
        return "" if pd.isna(v) else str(v).replace("|", r"\|")
    cols = list(df.columns)
    testa = "| " + " | ".join(cella(c) for c in cols) + " |"
    sep = "|" + "|".join("---:" if c in allinea_dx else "---" for c in cols) + "|"
    righe = ["| " + " | ".join(cella(v) for v in r) + " |"
             for r in df.itertuples(index=False)]
    return "\n".join([testa, sep, *righe])


def _mila(n) -> str:
    return f"{int(n):,}".replace(",", ".")


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--season", nargs="+", metavar="AAAA-AAAA")
    args = p.parse_args(argv)

    print("costruzione della tabella dai grezzi...")
    out = V.run(seasons=args.season)
    voti, partite, residui = out["voti"], out["partite"], out["residui"]

    print("\nregistrazione nel manifest...")
    r = manifest.registra_fantacalcio(seasons=args.season)
    print(f"  nuovi {r['nuovi']} | invariati {r['invariati']} | "
          f"MODIFICATI {len(r['modificati'])}")

    cop = V.copertura(voti, partite)
    sint = V.sintesi_stagioni(voti)
    ruoli = V.per_ruolo(voti)
    sv = V.sv_e_subentri(voti)

    cop.to_csv(config.REPORTS / "voti_copertura.csv", index=False)
    sint.to_csv(config.REPORTS / "voti_sintesi_stagioni.csv", index=False)
    ruoli.to_csv(config.REPORTS / "voti_per_ruolo.csv", index=False)
    sv.to_csv(config.REPORTS / "voti_sv_subentri.csv", index=False)

    n_voto = int(V.valutabili(voti).sum())
    pagine = sum(1 for t in T.targets() for g in range(1, T.N_GIORNATE + 1)
                 if t.percorso(g).is_file())
    byte = sum(t.percorso(g).stat().st_size for t in T.targets()
               for g in range(1, T.N_GIORNATE + 1) if t.percorso(g).is_file())

    # Le sentinelle di s.v., contate per scala: `56` esiste solo su una delle
    # tre, ed e' il tipo di fatto che sparisce se si appiattisce tutto a nullo.
    codici = []
    for scala in P.SCALE:
        col = voti[f"codice_sv_{scala}"]
        for valore, n in col.value_counts().sort_index().items():
            codici.append({"scala": scala, "codice": int(valore), "righe": int(n)})
    codici = pd.DataFrame(codici)
    codici.to_csv(config.REPORTS / "voti_codici_sv.csv", index=False)

    testo = f"""# Voti fantacalcio — acquisizione delle cinque stagioni

Generato da `scripts/run_voti_fantacalcio.py` il {date.today().isoformat()}.
Fonte: `{T.BASE_URL}/{T.PERCORSI_VOTI[config.LEAGUE]}`, vista HTML pubblica.

## Esito in una riga

**{_mila(pagine)} pagine, {_mila(len(voti))} righe giocatore-partita, cinque
stagioni**, e il fantavoto della fonte si ricostruisce dai bonus **esattamente
su {_mila(n_voto - len(residui))} righe su {_mila(n_voto)}** — che e' la
verifica piu' forte che questa acquisizione permetta, perche' non passa da
nessun modello.

## Come e' stata presa

| | |
|---|---|
| base giuridica | autorizzazione dichiarata dall'utente, `docs/regole_fantacalcio.md` §7.1 dec. 1 |
| via scelta | **vista HTML pubblica** — chiude il `[NON DECISO]` di §7.1 |
| perche' non l'export | `/api/v1/Excel/...` risponde 401 senza credenziali (addendum di `phase7_fattibilita_fonte.md`) |
| `User-Agent` | `{T.USER_AGENT}` |
| ritmo | una pagina ogni 3 s, dichiarato in `--sleep` |
| grezzo | `data/raw/fantacalcio/ITA-serie-a/<stagione>/voti/<gg>.html.gz`, {byte / 1e6:.1f} MB |
| provenienza | `data/raw/manifest.json`, con **due** hash: del `.gz` e dell'HTML servito |

Il `User-Agent` **non finge di essere un browser**. Dichiararsi Chrome per
passare inosservati sarebbe la forma piu' banale di aggiramento, vietata
dall'art. 3.3(e) dei Termini e non coperta da nessuna autorizzazione; ed e'
inutile, perche' la fonte serve regolarmente le pagine a questa stringa.

## Copertura

{_tab(cop, ("giornate", "partite", "squadre", "righe", "righe_giocatore",
            "righe_allenatore", "righe_per_partita"))}

**I denominatori si contano, non si assumono.** E' la lezione dell'acquisizione
WhoScored, dove l'Atalanta aveva 35 partite su 38 e assumere il denominatore
avrebbe nascosto la perdita.

## Il fantavoto si ricostruisce: {_mila(n_voto - len(residui))}/{_mila(n_voto)}

La fonte pubblica il voto, il fantavoto **e** separatamente le otto voci di
bonus. Le due strade devono chiudere, e chiudono con questo barema — ricavato
per differenza, non dichiarato dalla fonte:

| voce | valore |
|---|---:|
| gol segnato | +3 |
| gol subito | −1 |
| autorete | −2 |
| rigore segnato | +3 |
| rigore sbagliato | −3 |
| rigore parato | +3 |
| assist | +1 |
| **ammonizione** | **−0,5** |
| **espulsione** | **−1** |
| player of the match | **0** |

**Tre fatti che la riconciliazione ha portato a galla, e nessuno dei tre si
vede guardando la pagina resa:**

1. **I cartellini non sono una colonna di bonus.** Le otto voci non li
   contengono. Stanno come **classe CSS sullo span del voto**
   (`player-grade yellow-card`, `red-card`). Chi legge solo `data-value` li
   perde in silenzio, e valgono −0,5 e −1. Sono {_mila(voti["ammonizione"].sum())}
   ammonizioni e {_mila(voti["espulsione"].sum())} espulsioni sulle cinque stagioni.
2. **Il gol su rigore non e' anche in "gol segnati".** Sta solo in "rigori
   segnati" e vale +3 una volta sola. Sommare le due colonne conterebbe due
   volte lo stesso gol — ed e' l'errore che la riconciliazione ha escluso, non
   una precauzione: con il rigore contato nei gol restano {_mila(int(voti["rigori_segnati"].sum()))}
   righe con residuo +3.
3. **"Player of the match" ha una colonna ma non entra nel fantavoto** della
   fonte. E' un'opzione di lega, e nella lega dell'utente non c'e'.

> **Conseguenza da tenere ferma: il `FV` della fonte NON e' il fantavoto della
> lega dell'utente.** Il barema di `regole_fantacalcio.md` §1.1 contiene **+1 di
> porta inviolata**, che la fonte non applica — e si vede proprio dal fatto che
> la riconciliazione torna esatta *senza* di esso. Il fantavoto di lega va
> ricalcolato dalle colonne di bonus, e la porta inviolata **si deriva**
> (`ruolo == "p"` e `gol_subiti == 0`), non si legge. Vincolo 7: due definizioni
> della stessa grandezza non si mescolano.

## I codici di s.v., e la soglia che li riconosce

`data-value` non porta sempre un voto. Sopra 10 e' un **codice**, e i codici
sono conservati invece di essere appiattiti a nullo:

{_tab(codici, ("codice", "righe"))}

**`56` non compare mai sulla scala Redazione**, che e' quella che il progetto
usa: sta solo sulle altre due, e sempre su righe che la Redazione ha gia'
marcato `55`. Appiattire tutto a nullo avrebbe fatto sparire il fatto che le
sentinelle sono due e che le tre scale non usano lo stesso vocabolario.

> **La soglia dei 10 vale sul voto e non sul fantavoto**, ed e' l'unico errore
> che questa acquisizione ha davvero commesso — corretto prima di pubblicare i
> numeri, e riportato perche' e' istruttivo. Un voto sta in 0-10 (osservato:
> 3,0-9,5); un fantavoto no — Simeone, 9 con quattro gol, fa **21**. Applicando
> la stessa soglia a entrambi, ~1.000 fantavoti veri diventavano codici
> inesistenti; e quelle righe, diventate nulle, **uscivano dalla riconciliazione
> senza far rumore**, perche' un residuo nullo si filtra da solo. La verifica
> dichiarava 53.775/53.775 saltando proprio le righe dei marcatori — cioe' le
> uniche in cui il barema dei gol veniva messo alla prova. Ora il denominatore
> e' "righe con un voto" e una riga con il voto e senza fantavoto conta come
> fuori registro, non come riga da saltare.

## L's.v. osservato, e dove sta

{_tab(sv, ("righe", "sv", "quota_sv"))}

La fonte **dichiara che una soglia di minuti non esiste** ("Non esiste, e mai
esisterà, una regola che prevede che il voto venga dato a chi gioca un numero
minimo di minuti"). Quindi l's.v. non e' una funzione dei minuti e la regola
dell'80' resta cio' che §1.2 dice che sia: un'**assunzione di modello**, da
misurare sulla 2025-26 — l'unica stagione con entrambe le fonti — e non una
lettura. Questa tabella misura solo **dove** l's.v. si concentra, che e' un fatto.

## Il livello dei voti, stagione per stagione

{_tab(sint, ("righe", "con_voto", "voto_medio", "voto_sd", "fantavoto_medio",
             "gol", "assist", "ammonizioni", "espulsioni", "quota_sv"))}

Per ruolo, con l'allenatore escluso da tutte le righe:

{_tab(ruoli, ("righe", "con_voto", "voto_medio", "fantavoto_medio", "quota_sv"))}

> **Questa tabella e' descrittiva e va letta come tale.** Dice se il *livello*
> dei voti si e' mosso, non se il *criterio editoriale* e' cambiato: le due cose
> non coincidono, e la seconda non e' osservabile dall'esterno — la fonte non
> pubblica un changelog dei criteri di voto (§8 di
> `reports/phase7_fattibilita_fonte.md`). Il test formale di rottura, con il
> punto di rottura **cercato** e non assunto e con la potenza dichiarata, e'
> quello che la Fase 7 ha fatto sui tiri in `sot/recording_stability.py`: qui
> non e' stato rifatto, e finche' non lo e' la §5 delle regole resta aperta.

## Cosa c'e' nella tabella e cosa no

Una riga per giocatore sceso in campo per partita, {len(voti.columns)} colonne,
tutte e tre le scale affiancate. La stessa tabella e' scritta in due forme:

| file | a cosa serve |
|---|---|
| `{V.VOTI_PARQUET.relative_to(config.ROOT).as_posix()}` | e' la forma che i moduli leggono: conserva i tipi |
| `{V.VOTI_CSV.relative_to(config.ROOT).as_posix()}` | per aprirla fuori di qui |
| `{V.PARTITE_PARQUET.relative_to(config.ROOT).as_posix()}` · `{V.PARTITE_CSV.relative_to(config.ROOT).as_posix()}` | il calendario: 1.900 partite con data, risultato e stadio |

**Se le due forme divergessero, quella giusta e' il Parquet.** Il CSV perde i
tipi: `giocatore_id`, che e' `Int64` con i nulli degli allenatori, in CSV e' una
colonna di testo, e riletto con `read_csv` senza `dtype` torna `float` —
`4431.0` invece di `4431`. E' la ragione per cui non e' il CSV a essere letto da
`sot/voti.py`.

**Non c'e' una riga per chi e' rimasto in panchina**: la fonte non lo elenca, e
inventare righe a zero dichiarerebbe un'assenza che non abbiamo osservato.
**Non ci sono i minuti**: non sono nel dato, e l'unico segnale di tempo di gioco
e' binario (`subentrato` / `sostituito`), senza minuto. Vengono da WhoScored.
**Venti righe per giornata sono allenatori** (`allenatore == True`,
`giocatore_id` nullo): prendono un voto come i giocatori e vanno filtrate da
qualunque media, o dentro c'e' il giudizio sul tecnico.

`giocatore_id` viene dall'URL del profilo ed e' **stabile fra stagioni**: e' la
chiave con cui ricucire l'identita' senza passare dai nomi, che la fonte
abbrevia e disambigua a mano (`Ivanovic M.`).

## Cosa resta aperto

- **Le quotazioni del listone non sono state prese.** Sono la verifica
  principale del progetto (F5) e stanno su un'altra pagina,
  `/quotazioni-fantacalcio`. Non erano nella richiesta.
- **La §5 delle regole non e' chiusa**: il confronto fra stagioni qui e'
  descrittivo. Vedi sopra.
- **Le nove domande del Blocco 0** restano quelle che sono, meno la prima: `D1`
  e' chiusa (i voti ci sono, la via e' la vista HTML), `D2` no.
"""

    OUT_MD.write_text(testo, encoding="utf-8")
    print(f"\n-> {OUT_MD}")
    for p in (V.VOTI_PARQUET, V.VOTI_CSV, V.PARTITE_PARQUET, V.PARTITE_CSV):
        print(f"-> {p}  ({p.stat().st_size / 1e6:.1f} MB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
