# -*- coding: utf-8 -*-
"""Fase 11 / Blocco S1 — le soglie di tiri in porta del Como 2026-27.

    ./.venv/Scripts/python.exe scripts/run_fase11_s1.py

**Non tocca la rete e non scrive niente sotto `data/`.** L'unica informazione
esterna sono i nomi delle tre promosse, dichiarati in `soglie_2627.PROMOSSE_2627`
con la loro provenienza; le tre retrocesse che li accompagnano sono **verificate
contro la classifica ricostruita dai dati**.

**Vincolo 3**: nessuna valutazione di scommessa. Si pubblica `P(SoT > linea)` e
la **quota di pareggio** `1/P`; il guadagno atteso e' una funzione della quota
che si fornisce, e il caso «quota generata dal modello» sta in tabella per essere
squalificato, non letto.

~2 min (il modello dei giocatori e il Monte Carlo della proiezione).
"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sot import (aggregate, calendar_2627 as CAL, config, dispersion as D,  # noqa: E402
                 project_2627 as P, soglie_2627 as S, validate as V)

import pagina_s1  # noqa: E402  (sta accanto a questo script)

OUT_MD = config.REPORTS / "fase11_s1_soglie_como.md"
OUT_CSV = config.REPORTS / "fase11_s1_soglie_como.csv"
OUT_HTML = config.REPORTS / "fase11_s1_simulatore.html"


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
    print("Fase 11, blocco S1 — soglie del Como 2026-27")
    print("=" * 60)

    tm = aggregate.load_team_match()
    pm = aggregate.load_player_match()
    wf_path = config.PROCESSED / "walkforward_base.parquet"
    if not wf_path.exists():
        raise SystemExit("manca walkforward_base.parquet: esegui prima run_phase2.py")
    wfd = pd.read_parquet(wf_path)
    r = D.fit_r(wfd["sot"].to_numpy(float), wfd["lam"].to_numpy(float))

    # --- 1. le squadre, e la verifica della fonte esterna -------------------
    sq = S.verifica_squadre(tm)
    print("\n[1] fonte esterna verificata contro i dati")
    print(sq.to_string(index=False))

    # --- 2. il ponte -------------------------------------------------------
    print("\n[2] proiezione e ancora (modello dei giocatori, ~1 min)")
    proj, summary, model, du = P.build_projection(pm, tm)
    ancora = S.ancora_pubblicata(summary)
    lam = S.lambda_per_partita(tm, ancora)
    print(f"    ancora = {ancora:.4f} = 4.90 x {summary['ratio']:.5f}")
    print(f"    media dei 38 lambda = {lam['lam'].mean():.6f}")
    print(f"    da {lam['lam'].min():.3f} ({lam.loc[lam['lam'].idxmin(), 'avversario']}"
          f" {lam.loc[lam['lam'].idxmin(), 'campo']})"
          f" a {lam['lam'].max():.3f} ({lam.loc[lam['lam'].idxmax(), 'avversario']}"
          f" {lam.loc[lam['lam'].idxmax(), 'campo']})")

    # --- 3. le probabilita' ------------------------------------------------
    print("\n[3] probabilita' per soglia (Monte Carlo del livello)")
    mult = S.moltiplicatori_livello(proj, summary, model, r, ancora)
    ps = S.p_soglie(lam, mult, r=S.R_NB2)
    sintesi = S.sintesi_per_linea(ps)
    print(sintesi.round(4).to_string(index=False))

    sens = S.sensibilita_r(lam)

    # --- 4. guadagno atteso, come funzione della quota ---------------------
    gua = S.tabella_guadagno(ps, colonna="p_puntuale")
    gua_int = S.tabella_guadagno(ps, colonna="p_integrata")
    circ = S.identita_circolare(ps)

    # --- 5. la validazione del macchinario ---------------------------------
    print("")
    print("[5] validazione walk-forward sulla stagione pubblicata")
    B = V.evaluation_bundle(tm, wf_path, verbose=False)
    val = S.validazione_2526(B)
    cal2526 = S.calibrazione_2526(B)
    print(val.round(4).to_string(index=False))
    print(f"    pendenza di calibrazione {cal2526['pendenza']:.3f} "
          f"± {cal2526['se']:.3f} (z = {cal2526['z_vs_1']:+.2f}) su n = {cal2526['n']}")

    # --- 6. scenari sulle promosse ----------------------------------------
    righe = []
    for nome, natura in CAL.SCENARI:
        l = S.lambda_per_partita(tm, ancora, scenario=nome)
        p45 = D.p_over(l["lam"].to_numpy(), 4.5, S.R_NB2)
        righe.append({"scenario": nome, "natura": natura,
                      "media_lambda": l["lam"].mean(),
                      "sd_fra_partite": l["lam"].std(),
                      "p_over_4.5_media": float(p45.mean()),
                      "lambda_vs_promossa_casa": float(
                          l.loc[l["promossa"] & (l["is_home"] == 1), "lam"].iloc[0])})
    scen = pd.DataFrame(righe)

    # --- CSV e pagina locale ------------------------------------------------
    ps.to_csv(OUT_CSV, index=False, encoding="utf-8")
    pagina_s1.scrivi(ps, OUT_HTML, ancora=ancora, r_nb2=S.R_NB2,
                     data=date.today().isoformat(), linee=S.LINEE)

    ancora_note = (f"{config.REF_TOPDOWN_PER_MATCH} x {summary['ratio']:.5f} "
                   f"= {ancora:.4f}")
    n_val = int(val["n"].iloc[0])

    # Le tabelle si compongono qui: dentro una f-string `{{` non e' un `{`
    # letterale ma l'inizio di un set, e un dizionario di decimali diventerebbe
    # un `TypeError: unhashable type`.
    t_sq = _tab(sq)
    t_estremi = _tab(
        pd.concat([lam.nsmallest(3, "lam"), lam.nlargest(3, "lam")])
        [["avversario", "campo", "promossa", "exp_difesa", "lam"]],
        dec={"exp_difesa": 4, "lam": 3})
    t_sintesi = _tab(sintesi, dec={
        "linea": 1, "p_media": 4, "p_min": 4, "p_max": 4, "p_media_integrata": 4,
        "quota_pareggio_stagione": 3, "quota_pareggio_stagione_integrata": 3,
        "attese_su_38": 1})
    t_sens = _tab(sens, dec={"linea": 1,
                             **{c: 4 for c in sens.columns if c != "linea"}})
    t_gua = _tab(gua, dec={
        "linea": 1, "p_media": 4, "quota_pareggio_stagione": 3,
        **{c: 2 for c in gua.columns if c.startswith("q=")}})
    t_gua_int = _tab(gua_int, dec={
        "linea": 1, "p_media": 4, "quota_pareggio_stagione": 3,
        **{c: 2 for c in gua_int.columns if c.startswith("q=")}})
    t_val = _tab(val, dec={
        "linea": 1, "p_media": 4, "frequenza_osservata": 4, "brier_modello": 4,
        "brier_tasso_base": 4, "differenza": 4, "mde_brier": 4})
    t_circ = _tab(circ, dec={
        "overround": 2, "linea": 1, "guadagno_proporzionale_per_partita": 6,
        "dispersione_proporzionale": 6, "guadagno_potenza_per_partita": 4,
        "dispersione_potenza": 4, "guadagno_proporzionale_su_38": 4})
    t_scen = _tab(scen, dec={
        "media_lambda": 6, "sd_fra_partite": 4, "p_over_4.5_media": 4,
        "lambda_vs_promossa_casa": 3})

    s_ = sintesi.set_index("linea")
    g_ = gua.set_index("linea")
    gi_ = gua_int.set_index("linea")

    # Quanto il margine a potenza dipende dalla LINEA invece che dall'overround.
    # Si misura invece di affermarlo: la prima stesura di §6 diceva il contrario,
    # e i numeri l'hanno corretta.
    c_ov = circ[circ["overround"] == S.OVERROUND_IPOTIZZATI[0]].set_index("linea")
    b_alto = float(c_ov.loc[2.5, "guadagno_potenza_per_partita"])
    b_basso = float(c_ov.loc[7.5, "guadagno_potenza_per_partita"])
    b_rapporto = b_basso / b_alto

    testo = f"""# Fase 11 / Blocco S1 — le soglie di tiri in porta del Como 2026-27

> Generato da `scripts/run_fase11_s1.py` il {date.today().isoformat()}.
> **Non tocca la rete e non scrive niente sotto `data/`.** L'unica informazione
> esterna sono i nomi delle tre promosse; le tre retrocesse che le accompagnano
> sono verificate contro la classifica ricostruita dai dati.
> Tabella completa (38 partite x 6 linee): `{OUT_CSV.name}`.
> **Pagina locale interattiva**: `{OUT_HTML.name}` — si apre con un doppio clic,
> funziona offline, e permette di far variare linea, quota e puntata e di
> incollare le quote vere riga per riga.

## 0. La domanda, e che cosa si puo' onestamente risponderle

La domanda era: **1 EUR su ogni partita del Como 2026-27, per ogni fascia di over
tiri in porta da 2.5 a 7.5, guadagno atteso** — con una stima della quota
probabile in base all'avversaria.

Il guadagno atteso di 1 EUR e' `P x quota - 1`. Di quei due fattori questo
progetto puo' produrre **il primo e non il secondo**: nel repository non
esistono prezzi di mercato. L'unico artefatto che ne porta
(`data/external/quote/como_tiri_in_porta_2025-2026.xlsx`) li deriva dalla `P` di
questo stesso modello piu' un margine ipotizzato, ed e' esattamente cio' che fa
il codice archiviato in `legacy/`, che `legacy/README.md` descrive come
«circolare e privo di significato».

`[DECISO {date.today().isoformat()}]` dall'utente: si pubblica **`P` e la quota di
pareggio `1/P`**, e il guadagno atteso come **funzione della quota fornita**. Il
caso «quota generata dal modello» resta, in §6, **per essere squalificato**.

**Che cosa e' nuovo qui.** `project_2627.monte_carlo` produceva solo il totale
stagionale, con un lambda costante sulle 38 giornate, senza avversario e senza
campo. Il ponte `lambda(Como, avversario, campo)` per il 2026-27 **non esisteva**
ed e' il contenuto del blocco.

---

## 1. Le squadre 2026-27, e l'unica verifica possibile sulla fonte

{t_sq}

Le promosse sono **informazione esterna** e non sono verificabili in casa: la
Serie B non e' in questo repository. Le retrocesse arrivano dalla **stessa
pagina**, e quelle si': `calendar_2627.retrocesse()` le ricostruisce dai gol
delle righe partita, senza sapere niente della fonte. **Le due strade coincidono**,
e se non lo facessero anche le promosse andrebbero rimesse in discussione.

**Il calendario giornata per giornata c'e', ed e' costato quattro fonti.**
`verifica_calendario` ne ha **rifiutate tre**: elencavano il Como fra i propri
avversari, oppure la stessa squadra tre volte, oppure due volte in casa. La
quarta ha una struttura perfetta — 19 avversari, ognuno due volte, ognuno una
volta per campo — ma dava **37 righe su 38**.

**La riga mancante non e' stata indovinata: e' determinata.** Napoli compariva
solo in trasferta, quindi l'unica partita compatibile con la struttura e'
`Como-Napoli in casa`; delle 38 righe, l'unica cosa presa da fuori e' la sua
**giornata** (la 21a), che concorda su due fonti indipendenti. Una
corroborazione esterna che non e' stata usata per costruirlo: **le prime tre
giornate sono tutte in trasferta**, ed e' cio' che le fonti riportano a parte
per i lavori al Sinigaglia.

> **Il calendario resta un comodo, non una dipendenza, e un test lo blocca**:
> con e senza giornate i lambda e le probabilita' sono gli stessi. L'ordine non
> entra in nessuna somma — ogni avversario si gioca una volta per campo, quindi
> le 38 righe erano gia' determinate dalla sola lista delle venti squadre. Il
> calendario aggiunge **quando**, e serve a leggere la tabella per partita.
>
> Le **date** restano nulle: le fonti discordano, e qui non servono.

---

## 2. Il ponte: lambda per partita

**La struttura relativa viene dal modello, il livello dall'ancora.** E' la
lezione della Fase 6A: il livello pubblicato non contiene il modello di squadra,
quindi il modello dice *chi e' l'avversario e se si gioca in casa*, e l'ancora
dice *quanto vale la media*.

    lam_i = lam_modello_i / media(lam_modello) x ancora

Ancora = {ancora_note} (4.90 x rapporto compositivo), e la media dei 38 lambda
vale **{lam['lam'].mean():.6f}**, cioe' l'ancora a precisione macchina. Un test lo
blocca: e' cio' che rende questa tabella coerente con la proiezione gia'
pubblicata invece di essere una seconda proiezione che le somiglia.

Le sei partite estreme:

{t_estremi}

> **Lo scenario sulle promosse NON sposta il livello**, e va detto prima che
> qualcuno lo scopra leggendo §7: la media delle 38 righe e' l'ancora per
> costruzione, qualunque difesa si assegni a Venezia, Frosinone e Monza. Muove
> solo **come** il livello si distribuisce fra le partite. E' la decisione della
> Fase 6E — applicare il fattore di calendario all'ancora sarebbe un doppio
> conteggio, perche' 4.90 esce da 21 stagioni che contengono gia' 21 ricambi di
> neopromosse.

---

## 3. Le sei soglie

`p_puntuale` tratta il livello 2026-27 come noto; `p_integrata` lo tratta come
incerto e media sulla distribuzione del Monte Carlo della proiezione (di cui lo
shock di squadra e' il 65%).

{t_sintesi}

- **La colonna da leggere e' `quota_pareggio_stagione`**: e' la quota fissa a cui
  1 EUR su ogni partita della stagione va esattamente in pari. Sopra quel numero
  il guadagno atteso e' positivo, sotto e' negativo.
- **L'integrazione ingrassa le code nel verso previsto**, dichiarato prima di
  guardare i numeri: sulla 7.5 la probabilita' sale da
  {s_.loc[7.5, 'p_media']:.4f} a
  {s_.loc[7.5, 'p_media_integrata']:.4f}, sulla 2.5
  scende da {s_.loc[2.5, 'p_media']:.4f} a
  {s_.loc[2.5, 'p_media_integrata']:.4f}. Non sapere
  quanto tirera' il Como **non e' neutro**: rende gli estremi piu' probabili.
- **Si integra solo l'incertezza di livello, mai il campionamento**: quest'ultimo
  e' gia' dentro `p_over`, e tenerlo acceso conterebbe le code due volte. Un test
  lo pretende.

### La dispersione fra le partite non e' un dettaglio

Sulla 4.5 la probabilita' va da **{s_.loc[4.5, 'p_min']:.3f}**
(la partita piu' difficile) a **{s_.loc[4.5, 'p_max']:.3f}**
(la piu' facile). Una quota unica per tutta la stagione sarebbe conveniente su
alcune partite e non su altre: e' il motivo per cui il CSV esce a 38 righe per
linea e non solo come media.

### `r` non e' stimata qui, e sulle code conta

{t_sens}

`r = {S.R_NB2}` viene dalla Fase 2, con IC95% di profilo {S.R_NB2_IC95}. **L'effetto
non e' uniforme**: sulla 4.5 l'escursione e' piccola, sulla 7.5 vale una frazione
molto piu' grande della probabilita' stessa. Le due linee estreme sono quelle in
cui un'assunzione non stimata pesa di piu'.

---

## 4. Il guadagno atteso — 1 EUR su ognuna delle 38 partite

Ogni cella e' la **somma sulle 38 partite** di `p_i x q - 1`, cioe' cio' che si
attende chi mette 1 EUR su ogni partita a quella quota fissa. **Le quote sono
un'ipotesi di lettura, non prezzi osservati**: nessuno di questi numeri viene da
un mercato, e la griglia e' dichiarata in `soglie_2627.GRIGLIA_QUOTE`.

Su `p_puntuale`:

{t_gua}

Su `p_integrata` (la stessa cosa, con l'incertezza di livello dentro):

{t_gua_int}

**Come si legge.** Si prende la riga della linea che interessa e si cerca la
colonna della quota che il mercato offre davvero: quel numero e' il guadagno
atteso in euro su 38 euro puntati. Il segno cambia esattamente alla
`quota_pareggio_stagione`.

**Le due tabelle non danno la stessa risposta sulle linee estreme**, ed e' il
motivo per cui ci sono entrambe: sulla 7.5 l'integrazione sposta la quota di
pareggio da {g_.loc[7.5, 'quota_pareggio_stagione']:.2f} a
{gi_.loc[7.5, 'quota_pareggio_stagione']:.2f}.

---

## 5. Regge, questo macchinario? La verifica sul 2025-26

Senza questa sezione le tabelle sopra sarebbero numeri senza garanzia. Si usano i
lambda **walk-forward** della Fase 2 — non un fit sull'intera stagione, che
sarebbe in campione — e la `r` ricostruita riga per riga sul solo passato.
Baseline: il tasso base walk-forward di ciascuna linea.

{t_val}

Pendenza di calibrazione sulle sole partite del Como:
**{cal2526['pendenza']:.3f} ± {cal2526['se']:.3f}** (z = {cal2526['z_vs_1']:+.2f} contro 1.0),
su n = {cal2526['n']}.

> **Il limite sta qui e non in fondo: sono {n_val} partite di una squadra sola.**
> La colonna `mde_brier` dice quanta differenza servirebbe per distinguere il
> modello dal tasso base: su questa numerosita' **esclude divari grandi e non
> divari piccoli**. E' la lezione della 6D applicata a questo blocco.
>
> **Le linee 6.5 e 7.5 sono un'estrapolazione dichiarata.** `validate.LINES` si
> ferma a 5.5: il Brier pubblicato dalle Fasi 2 e 4 non e' mai stato misurato
> oltre. Su quelle due linee gli eventi sono pochi e la sensibilita' a `r` e'
> massima (§3). Vanno lette come le meno solide delle sei, e un test verifica che
> la costante `LINEE` porti questa avvertenza accanto a se'.

---

## 6. Se la quota la genera il modello — l'identita' che squalifica il conto

E' la risposta letterale alla domanda «stima la quota probabile e calcola il
guadagno», e sta qui **per essere squalificata**, non letta.

{t_circ}

- **Con margine proporzionale il guadagno atteso vale `1/overround - 1`, lo
  stesso numero su ogni partita e su ogni linea, con dispersione zero.** Non
  contiene una sola informazione sul Como: e' il margine, scritto al contrario.
  Un test lo verifica a precisione macchina.
- **Con margine a potenza (Buchdahl) il guadagno varia con `p`, e varia molto**:
  a overround fissato passa da {b_alto:.4f} sulla 2.5 a {b_basso:.4f} sulla 7.5,
  cioe' un fattore {b_rapporto:.0f}, mentre fra i tre overround a linea fissata
  cambia meno del doppio. **La linea conta piu' del margine, ed e' proprio questo
  che rende la tabella ingannevole**: sembra che il modello stia dicendo che
  l'Over 7.5 e' un pessimo affare, e invece `p^(1-1/k) - 1` e' una funzione della
  sola `p` — la trasformazione a potenza penalizza le probabilita' piccole, e di
  Como li' dentro non c'e' niente.
- **Il segno dipende da come il margine viene applicato, non da quanto il modello
  sia buono.** Qui e' negativo ovunque perche' il margine e' messo *a favore del
  banco*, che e' la convenzione onesta; applicandolo dall'altra parte
  diventerebbe positivo ovunque, con la stessa identica `P`. E' precisamente cio'
  che `legacy/README.md` descrive: «qualunque regola sistematica risulta
  redditizia per costruzione: il margine e' l'unica cosa che separa le due parti,
  e il segno del risultato dipende solo da come e' stato applicato».

> **Quindi: quanto si guadagna davvero non e' rispondibile con i dati in casa.**
> Non per prudenza — per assenza del secondo fattore. §3 e §4 danno tutto cio'
> che serve per rispondere nel momento in cui un prezzo vero esiste.

---

## 7. Gli scenari sulle promosse

{t_scen}

La colonna `media_lambda` e' **costante per costruzione** (§2). Cio' che si muove
e' `sd_fra_partite` e il lambda contro una promossa in casa, che va da
{scen['lambda_vs_promossa_casa'].min():.2f} a {scen['lambda_vs_promossa_casa'].max():.2f}
a seconda di quanto si assume porose le tre neopromosse. **Su `P(Over 4.5)` media
l'effetto e' minuscolo** ({scen['p_over_4.5_media'].min():.4f} –
{scen['p_over_4.5_media'].max():.4f}): lo scenario ridistribuisce, non aggiunge.

**Perche' non si prendono le loro stagioni storiche.** Monza, Venezia e Frosinone
hanno righe nelle cinque stagioni gia' in casa. Usarle vorrebbe dire due cose che
il progetto ha gia' escluso: confrontare unita' grezze fra stagioni in cui la
media di campionato si e' mossa del 10,1% (regola di E1), e trattare una rosa di
due o quattro anni fa come una stima di quella di oggi. Lo scenario e' meno
preciso e non e' sbagliato.

---

## 8. Domande aperte

1. **I prezzi di mercato reali restano l'unica cosa che manca** per rispondere
   alla domanda come e' stata posta. Sono un blocco di acquisizione a se', con i
   vincoli 7-8-9 e una decisione dell'utente sulla fonte — e servirebbero
   **quote di chiusura pre-partita**, non quote correnti, altrimenti il confronto
   eredita lo stesso difetto di orologio che ha squalificato il FVM.
2. **Il calendario vero non e' stato acquisito.** Non serve a queste tabelle, ma
   servirebbe a due cose che qui non ci sono: la sequenza cronologica, e le
   giornate dopo un turno di Champions — dove `calendar_2627.LIMITE_CONGESTIONE`
   dichiara un effetto di **segno noto e negativo**, mai stimato, che su quelle
   partite rende queste probabilita' ottimistiche.
3. **La difesa delle promosse resta uno scenario e non una stima.** E' la stessa
   domanda aperta della Fase 6E, e qui pesa meno di quanto si temesse (§7).
4. **Le linee 6.5 e 7.5 non hanno una validazione propria**: sono fuori dal
   perimetro su cui il Brier e' stato misurato, e su di esse `r` conta il doppio.
   Validarle vorrebbe piu' stagioni, cioe' la stessa massa che R2 e R3 chiedevano.
5. **La guardia del vincolo 3 di R2/R2-bis/R3 e' latentemente sbagliata**, e lo
   si e' scoperto scrivendo quella di questo blocco: cerca sottostringhe, quindi
   `roi` scatta dentro `proiezione` e `bankroll` **non** scatta dentro
   `calcola_bankroll`. Qui e' corretta con un confine di lettera e un test che
   verifica entrambe le direzioni; **nei tre moduli di Fase 10 non e' stata
   toccata**, perche' cambiare un test che oggi passa non era in questo blocco.
"""

    OUT_MD.write_text(testo, encoding="utf-8")
    print(f"\n-> {OUT_MD}")
    print(f"-> {OUT_CSV}")
    print(f"-> {OUT_HTML}   (pagina locale: aprila con un doppio clic)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
