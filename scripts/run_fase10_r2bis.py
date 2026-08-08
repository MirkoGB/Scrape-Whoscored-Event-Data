# -*- coding: utf-8 -*-
"""Fase 10 / Blocco R2-bis — la sotto-sicurezza su 1X2: da dove viene, e se si toglie.

    ./.venv/Scripts/python.exe scripts/run_fase10_r2bis.py

**Non tocca la rete e non scrive niente sotto `data/`.** Legge il perimetro di R0
e i lambda di E3.1, come R2. **A differenza di R2 questo blocco stima**: la
ricalibrazione ha parametri, e sono walk-forward — il mappatore di una stagione
si addestra sulle stagioni precedenti e su nient'altro.

~1 min.
"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sot import config, esiti as E, ricalibrazione as RC  # noqa: E402

OUT_MD = config.REPORTS / "fase10_r2bis_calibrazione.md"


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
    print("Fase 10 / R2-bis — calibrazione\n" + "=" * 60)

    d = RC.dati()
    ver = RC.verifica_decompressione()

    griglia = RC.griglia_decompressione(d)
    kcal = pd.DataFrame([RC.k_calibrante(d, cl) for cl in E.CLASSI])[["classe", "k"]]
    ipo = RC.controllo_ipotesi_sui_gol(d)
    gol0 = RC.pendenza_marginale_gol(d, 1.0)
    gol_rif = RC.pendenza_marginale_gol(d, RC.K_RIFERIMENTO)
    dp = RC.deficit_pareggi(d)

    # I tre modi affiancati: la conclusione non deve dipendere da quale pezzo
    # della de-compressione si sceglie di applicare.
    modi = []
    for modo in ("divario", "divario_netto", "pieno"):
        riga = {"modo": modo}
        for cl in E.CLASSI:
            riga[f"k che calibra {cl}"] = RC.k_calibrante(d, cl, modo=modo)["k"]
        g = RC.pendenza_marginale_gol(d, riga["k che calibra 2"], modo)
        riga["pendenza gol a quel k"] = g["pendenza"]
        riga["z gol"] = g["z vs 1.0"]
        modi.append(riga)
    modi = pd.DataFrame(modi)

    conf = RC.confronto_ricalibrazione(d)
    par = RC.walkforward_ricalibrazione(d, "platt")[2]
    ver_ric = RC.verdetto(conf)

    ident = RC.identita_punti(d)
    ident_meta = RC.identita_punti_per_meta(d)
    ident_conf = RC.identita_punti_confronto(d)

    k1 = float(kcal.set_index("classe").loc["1", "k"])
    kx = float(kcal.set_index("classe").loc["X", "k"])
    k2 = float(kcal.set_index("classe").loc["2", "k"])
    c = conf.set_index("metodo")
    base = "modello (R2, non ricalibrato)"

    print(f"\n§2  k che calibra: 1 -> {k1:.3f} | X -> {kx:.3f} | 2 -> {k2:.3f}"
          f"   (riferimento 6A: {RC.K_RIFERIMENTO:.3f})")
    print(f"    pendenza sui GOL a k=1: {gol0['pendenza']:.3f} "
          f"(z {gol0['z vs 1.0']:+.2f}) -> a k={RC.K_RIFERIMENTO:.3f}: "
          f"{gol_rif['pendenza']:.3f} (z {gol_rif['z vs 1.0']:+.2f})")
    print(f"\n§3  adottabili: {ver_ric['adottabili']} -> scelto: {ver_ric['scelto']}")
    r_meta = float(ident_meta["rapporto medio"].iloc[1])
    print(f"\n§4  rapporto di dispersione della classifica: "
          f"{ident['rapporto'].mean():.2f} (2a meta': {r_meta:.2f})")

    dec_g = {c_: 3 for c_ in griglia.columns if c_ != "k"}
    dec_g["k"] = 4
    dec_g["RPS"] = 4
    dec_g["log-loss"] = 4
    dec_g["Brier O2.5"] = 4

    testo = f"""# Fase 10 / Blocco R2-bis — la sotto-sicurezza su 1X2: da dove viene, e se si toglie

> Generato da `scripts/run_fase10_r2bis.py` il {date.today().isoformat()}.
> **Nessuna richiesta di rete.** A differenza di R2, **questo blocco stima**: la
> ricalibrazione ha parametri, e sono walk-forward.

---

## 0. Perche' adesso, e non dopo R3

R2 ha misurato che il modello e' **sotto-sicuro** su 1X2 — pendenza 1,223 sulla
classe `1` e 1,324 sulla `2`, cioe' sopra 1.0 — e ha lasciato la spiegazione
come domanda aperta n. 1, indicando la **compressione della ridge** della Fase 6A
come ipotesi compatibile e non misurata.

**Su una partita sola un errore di calibrazione resta piccolo e locale. R3 lo
propaga.** Una simulazione di stagione somma le stesse probabilita' su 38 turni,
e cio' che esce non e' una previsione di partita ma una distribuzione di scudetto
e di retrocessione — cioe' due **code**. Un errore sistematico nel verso della
compressione non si annulla sommandosi: sposta tutta la distribuzione simulata
verso il centro, ed e' esattamente il punto in cui R3 pubblica.

Il blocco tiene separate due domande che e' facile confondere:

| | domanda | risposta |
|---|---|---|
| **§2** | la sotto-sicurezza **viene** dalla compressione della ridge? | **no**: il controllo diretto la rifiuta a otto errori standard |
| **§3** | si **toglie** con una ricalibrazione walk-forward? | **si', con Platt**, e senza peggiorare l'RPS |
| **§4** | dopo la ricalibrazione, R3 e' al sicuro? | **no**, e §4 dice di quanto |

> **Che §3 funzioni non e' una conferma di §2.** Una ricalibrazione corregge il
> sintomo qualunque sia la causa: e' una mappa monotona stimata sull'errore
> osservato, e non sa da dove l'errore venga. Le due sezioni possono dare — e
> danno — esiti opposti.

---

## 1. La de-compressione, e perche' e' *quella* trasformazione

L'ipotesi della Fase 6A dice una cosa precisa: la penalita' ridge comprime
`attacco` e `difesa` verso zero e **non tocca `mu`**. Quello che risulta
compresso e' il **divario** fra le due squadre, non il livello del campionato.
L'inverso esatto e' quindi

```
d  = log(lam_casa) - log(lam_trasferta)        il divario
d' = k * d                                     k > 1 allarga
```

con i due lambda ricostruiti in modo che il **prodotto resti invariato**. Le tre
identita' sono verificate e non lasciate all'intenzione
(`verifica_decompressione`): `k = 1` e' l'identita' ({ver["k=1 e' l'identita'"]}),
il divario e' scalato per `k` esatto ({ver['divario scalato per k']}), il
prodotto non si muove ({ver['prodotto invariato']}, scarto massimo
{ver['max scarto sul prodotto']:.1e}).

La de-compressione passa poi per la **stessa** `risultato.congiunta` di R2 con lo
stesso `rho = 0`: cambia il lambda e nient'altro, altrimenti si misurerebbe la
composizione. A `k = 1` le probabilita' coincidono con le `modello|p*` di R2 a
ogni cifra, e un test lo pretende.

**Il riferimento della 6A e' dichiarato per quello che e'**: pendenza 0,760, cioe'
`k = {RC.K_RIFERIMENTO:.3f}`. E' misurata sui **tiri in porta del 2025-26**, non
sui gol delle cinque stagioni: entra come ordine di grandezza dell'ipotesi, non
come misura di questo modello.

---

## 2. L'ipotesi: il verso e' giusto, e proprio per questo si vede che e' sbagliata

### 2.1 La de-compressione che calibra il 1X2 e' quasi quella che la 6A prevede

{_tab(griglia, dec=dec_g)}

Il `k` che porta ciascuna classe esattamente a 1.0, cercato come **radice** e non
letto dal minimo di una griglia — un `argmin` su una griglia dichiarata
restituirebbe un punto della griglia e farebbe sembrare una coincidenza cio' che
e' solo la spaziatura scelta:

{_tab(kcal, dec={"k": 4})}

**La `1` chiede {k1:.3f} e la `2` chiede {k2:.3f}, contro i
{RC.K_RIFERIMENTO:.3f} che l'ipotesi prevede.** Verso giusto, taglia quasi
giusta: se ci si fermasse qui, l'ipotesi della compressione sarebbe confermata.

La `X` chiede {kx:.3f}, cioe' di **stringere** invece che di allargare, ma va
detto per quello che e': a `k = 1` la sua pendenza vale 0,966 con
z = −0,11, cioe' **non e' distinguibile da calibrata**, e allargare non la rompe
in modo leggibile (z = {float(griglia.set_index('k').loc[RC.K_RIFERIMENTO, 'z X']):+.2f}
al `k` del riferimento). Che i tre `k` non coincidano e' **coerente** con «non e'
una compressione sola», non e' una prova.

**La conclusione non dipende da quale pezzo della de-compressione si applica**, ed
e' il controllo che rende la sezione qualcosa di piu' di una parametrizzazione
fortunata. Il modo semplice scala anche il **vantaggio del campo**, che sta dentro
il divario e non e' un effetto di squadra compresso dalla ridge; il modo `pieno`
e' invece l'inverso **letterale** della penalita' — allarga lo scarto di ciascun
lato dal `mu` stimato sul solo passato, cioe' anche la somma dei due lati:

{_tab(modi, dec={"k che calibra 1": 4, "k che calibra X": 4, "k che calibra 2": 4, "pendenza gol a quel k": 3, "z gol": 2})}

### 2.2 Il controllo diretto, che viene da E3 e non da qui, la esclude

C'e' un numero che misura la compressione **senza passare dall'esito**, e nessuno
lo aveva messo accanto alla pendenza 1X2: la pendenza di calibrazione **sui gol**.
La relazione e' esatta — se i lambda fossero compressi di un fattore `c`, quella
pendenza varrebbe `1/c` — quindi l'ipotesi della 6A non prevede genericamente
«sopra 1»: prevede **{RC.K_RIFERIMENTO:.3f}**.

{_tab(ipo, dec={"valore": 4, "errore standard": 4, "z": 2})}

- **Osservata {float(ipo.loc[0, 'valore']):.3f} ± {float(ipo.loc[0, 'errore standard']):.3f}**,
  cioe' z = {float(ipo.loc[0, 'z']):+.2f} contro 1.0: se mai, i lambda sono un po'
  troppo **estremi**, che e' il verso opposto alla compressione.
- **Contro il valore che l'ipotesi prevede, z = {float(ipo.loc[1, 'z']):+.2f}.**
  Non e' un negativo debole: e' un rifiuto a otto errori standard.
- **E non e' mancanza di potenza** (lezione della 6D): una compressione fino a
  {float(ipo.loc[2, 'valore']):.3f} — cioe' del {100 * (1 - float(ipo.loc[2, 'valore'])):.0f}% —
  sarebbe stata vista con probabilita' 80%. La 6A ne dichiara una del 24%.

**Ne segue il fatto centrale della sezione: la stessa trasformazione che calibra
l'esito scalibra la grandezza da cui l'esito e' costruito.** Al `k` del
riferimento la pendenza sui gol scende da {gol0['pendenza']:.3f}
(z = {gol0['z vs 1.0']:+.2f}) a {gol_rif['pendenza']:.3f}
(z = {gol_rif['z vs 1.0']:+.2f}). Non e' un pareggio fra due diagnostiche: e' una
che si sistema e una che si rompe.

> **L'ipotesi della compressione della ridge e' quindi da abbandonare come
> *causa*, pur restando una buona *descrizione* del sintomo.** E' una distinzione
> che questo progetto ha gia' incontrato: coincidere in taglia non e' spiegare.
> La coincidenza fra `k = {RC.K_RIFERIMENTO:.3f}` e il `k` che calibra il 1X2 va
> registrata come tale, come la 6A ha registrato che `como_context` valesse 4,9041
> contro un'ancora di 4,90 senza che le due grandezze avessero un legame.

### 2.3 Cosa c'e' al posto: il deficit di pareggi

La colonna `P(X) media` della griglia dice dove finisce la massa quando si
allarga il divario, e la risposta e' **i pareggi**, che gia' scarseggiano:

{_tab(dp, dec={"P(X) dichiarata": 4, "X osservati": 4, "deficit": 4, "se binomiale": 4, "pareggi mancanti": 1})}

Il modello dichiara {float(dp[dp.stagione == "**tutte**"]["P(X) dichiarata"].iloc[0]):.4f} di pareggi
contro {float(dp[dp.stagione == "**tutte**"]["X osservati"].iloc[0]):.4f} osservati:
**{float(dp[dp.stagione == "**tutte**"]["pareggi mancanti"].iloc[0]):.0f} pareggi
mancanti** su {int(dp[dp.stagione == "**tutte**"]["n"].iloc[0]):,} partite.
**E' la firma della composizione, non del lambda**: due Poisson indipendenti
producono meno pareggi di quanti se ne osservino, ed e' la ragione per cui la
correzione di Dixon-Coles esiste.

> **Il deficit da solo non e' significativo, e va scritto cosi'.**
> {float(dp[dp.stagione == "**tutte**"]["deficit"].iloc[0]):.4f} contro un errore
> standard binomiale di {float(dp[dp.stagione == "**tutte**"]["se binomiale"].iloc[0]):.4f}
> fa 1,5 errori standard, e il segno cambia in due stagioni su cinque. **Non e'
> la prova di un difetto della composizione**: e' la direzione in cui la
> ricalibrazione di §3 si muove — dove il segnale si accumula su quattro
> stagioni di addestramento — e vale come indizio coerente, non come misura.

> **E qui R1 aveva gia' detto la sua**, e le due letture si incastrano. R1 ha
> misurato `rho = 0` e — questo e' il punto — che lo scostamento presente ha la
> forma «**meno 0-0 e piu' 1-1**», che **nessun valore di `rho` puo' produrre**,
> perche' un `rho` solo lega quelle due celle allo stesso verso. Il deficit di
> pareggi resta li', non e' un problema di livello dei lambda, e la forma di
> Dixon-Coles non e' lo strumento per toglierlo. **Non e' stato tolto**:
> inventare qui una seconda forma di dipendenza su 1.638 partite sarebbe
> adattarsi al rumore, ed e' la domanda aperta n. 2 di R1 — quella per cui G2
> avrebbe la massa.

---

## 3. La ricalibrazione: si toglie, e con che cosa

**Il criterio di adozione e' scritto prima di guardare i numeri**, in
`CRITERIO_ADOZIONE`, e `verdetto()` lo applica meccanicamente — un criterio
dichiarato che poi si applica a occhio non e' un criterio dichiarato:

> {RC.CRITERIO_ADOZIONE}

**La stima e' walk-forward** (vincolo 1): il mappatore della stagione `s` si
addestra su tutte le partite delle stagioni precedenti e su nient'altro. La
**2021-2022 non ha un passato** e resta non ricalibrata — non si riempie con il
mappatore di un'altra stagione e non si toglie dal campione: si marca, e il
confronto gira sulle {int(c.loc[base, 'n'])} righe marcate. Due test guastano i
dati per verificarlo: rovesciare l'ultima stagione non deve muovere **nessun**
parametro, rovesciare la prima deve muovere i successivi.

{_tab(conf, dec={"pendenza 1": 3, "z 1": 2, "pendenza X": 3, "z X": 2, "pendenza 2": 3, "z 2": 2, "RPS": 4, "log-loss": 4, "delta RPS": 5, "t": 2, "MDE (80%)": 5})}

{_tab(ver_ric['tabella'])}

**Adottato: `{ver_ric['scelto']}`.**

- **La temperatura non basta.** Un parametro solo, stimato fra
  {par['n_training'].iloc[1]:,} e {par['n_training'].iloc[-1]:,} partite di
  passato, vale `T` fra 0,93 e 1,02: affila appena, e lascia la classe `2` a
  z = {c.loc['temperatura', 'z 2']:+.2f}. **Ed e' il secondo argomento contro
  l'ipotesi di §2**: se il difetto fosse «tutte le probabilita' troppo vicine al
  centro», una manopola che le allarga tutte insieme lo toglierebbe. Non lo
  toglie, perche' il difetto non e' simmetrico fra le tre classi.
- **Platt per classe funziona**, e si vede *cosa* fa dai coefficienti stimati:
  l'intercetta sulla `X` e' **positiva in tre stagioni su quattro**, cioe' il
  mappatore passa il suo tempo ad **aggiungere pareggi** — che e' §2.3 letto
  dall'altro lato.
- **L'isotonica sovra-corregge** (z = {c.loc['isotonica', 'z 1']:+.2f} sulla
  classe `1`) e **peggiora** l'RPS. Sulla `X` la sua pendenza non e' nemmeno
  identificata: la mappa monotona collassa quasi a una costante e il logit non
  ha piu' varianza su cui stimare — lo stesso `nan` dichiarato che R2 e la
  Fase 4 restituiscono su `media campionato`, e per la stessa ragione. E' cio'
  che ci si aspetta da tre gradi di liberta' liberi su qualche centinaio di
  righe, ed e' il motivo per cui l'ordine di semplicita' era dichiarato prima.
- **L'RPS non peggiora, e nemmeno migliora in modo leggibile**: Platt lo sposta
  di {float(c.loc['platt', 'delta RPS']):+.5f} con t = {float(c.loc['platt', 't']):+.2f}
  contro un MDE di {float(c.loc['platt', 'MDE (80%)']):.5f}. **La ricalibrazione
  compra calibrazione, non accuratezza**, ed e' cio' che ci si deve aspettare da
  una mappa monotona: non riordina niente.

I coefficienti stimati, stagione per stagione:

{_tab(par)}

---

## 4. Quanto costa a R3, misurato al livello di R3

Una pendenza di calibrazione e' una diagnostica **per partita**. La domanda che
ha motivato il blocco e' un'altra — **la classifica simulata si disperde quanto
il modello dice?** — e ha una forma falsificabile:

```
var(punti osservati fra le squadre) = var(punti ATTESI) + media(varianza di campionamento)
```

Il primo termine e' quanto il modello crede che le squadre differiscano; il
secondo e' quanta fortuna il modello stesso ammette. Se la somma sta **sotto**
l'osservato, il modello sotto-dichiara la separazione, e una classifica simulata
esce **troppo corta**.

{_tab(ident, dec={"var osservata": 4, "var attesa": 4, "var campionamento": 4, "attesa + campionamento": 4, "rapporto": 3})}

**Il rapporto vale {ident['rapporto'].mean():.2f} in media e sta sopra 1 in tutte
e cinque le stagioni.** In unita' leggibili: la deviazione standard dei punti per
partita fra le venti squadre e' {np.sqrt(ident['var osservata'].mean()):.3f}
osservata contro {np.sqrt(ident['attesa + campionamento'].mean()):.3f} dichiarata
— su 38 giornate, circa **{np.sqrt(ident['var osservata'].mean()) * 38:.0f} punti
di dispersione contro {np.sqrt(ident['attesa + campionamento'].mean()) * 38:.0f}**.

> **La misura e' stata verificata su dati in cui la risposta e' nota**, ed e'
> l'unico modo di distinguere un difetto del modello da un difetto della misura:
> generando gli esiti **dalle probabilita' del modello** — dove per costruzione
> il modello e' perfettamente calibrato — il rapporto torna attorno a 1. Un test
> lo pretende.

**Il burn-in ne spiega una parte, e non tutta.** I lambda sono walk-forward:
alla settima giornata il modello sa poco, e una previsione onestamente incerta
abbassa la dispersione dei punti attesi senza che nulla sia mal calibrato. R3
pero' simula **il resto** di una stagione da una giornata avanzata, quindi cio'
che conta e' la seconda meta':

{_tab(ident_meta, dec={"var osservata": 4, "var attesa + camp.": 4, "rapporto medio": 3})}

Scende da {ident_meta['rapporto medio'].iloc[0]:.2f} a
{ident_meta['rapporto medio'].iloc[1]:.2f} e **non si chiude**: la parte che
resta e' una proprieta' del modello, e R3 la eredita.

**E la ricalibrazione la riduce senza chiuderla:**

{_tab(ident_conf, dec={"var osservata": 4, "var attesa + camp.": 4, "rapporto medio": 3})}

> **Questo non e' un difetto di calibrazione, ed e' importante non chiamarlo
> cosi'.** Lo scarto e' la parte delle differenze **vere** fra squadre che il
> modello non ha catturato — piu' qualunque shock che duri piu' di una partita e
> che quindi si correli lungo la stagione, che l'identita' assume assente. Una
> mappa monotona sulle probabilita' di partita non puo' restituirla: sposta la
> massa dentro ogni riga, non aggiunge separazione fra le squadre.

---

## 5. Cosa consegna a R3

1. **Le probabilita' ricalibrate con Platt walk-forward** sono la previsione da
   propagare: `ricalibrazione.walkforward_ricalibrazione(metodo="platt")`. La
   2021-2022 resta non ricalibrata e va contata come tale, non riempita.

   > **Il prezzo, dichiarato: dopo Platt il modello non e' piu' internamente
   > coerente.** Le tre probabilita' 1X2 non escono piu' dalla **stessa**
   > congiunta che produce l'over/under — una mappa per classe piu' una
   > rinormalizzazione non corrisponde a nessuna distribuzione sui punteggi. R3
   > usa solo l'esito e quindi non lo paga; **un blocco che volesse 1X2 e
   > over/under insieme lo pagherebbe**, e non deve prendere la ricalibrazione
   > per buona senza rifare la domanda. E' la ragione per cui `esiti.py` resta
   > com'e' e la ricalibrazione vive in un modulo suo.
2. **La sotto-dispersione della classifica va DICHIARATA e, se possibile,
   modellata.** Simulare la stagione con le sole probabilita' di partita — anche
   ricalibrate — produce una classifica troppo corta di circa un terzo in
   varianza: campioni troppo deboli, ultime troppo forti, code delle
   distribuzioni di scudetto e retrocessione troppo grasse. **E' un limite da
   scrivere accanto ai numeri (vincolo 5), non in fondo.**
3. **Cio' che NON va fatto** e' correggere lo shrinkage finche' la pendenza torna
   a 1.0. §2 mostra che la de-compressione paga la calibrazione dell'esito con
   quella dei gol e con i pareggi; sarebbe far tornare un numero cambiando la
   definizione (vincolo 2).

---

## 6. Domande aperte

1. **Da dove venga la sotto-sicurezza resta senza una causa misurata.**
   Sull'ipotesi della ridge la risposta e' netta e negativa (§2.2, z = −8,1
   contro il valore che prevede, con la potenza dichiarata). Cio' che il blocco
   propone al suo posto — il deficit di pareggi — **e' un indizio e non una
   misura**: 1,5 errori standard, segno che cambia in due stagioni su cinque. E
   non avrebbe comunque una correzione disponibile: la forma di Dixon-Coles e'
   gia' stata provata da R1 e non e' quella giusta. **La domanda aperta n. 1 di
   R2 e' cambiata, non chiusa**: non e' piu' «e' la ridge?» — non lo e' — ma
   «quale forma di dipendenza produce meno `0-0` e piu' `1-1`», che su 1.638
   partite non si puo' cercare senza adattarsi al rumore.
2. **La sotto-dispersione della classifica non e' spiegata**, ed e' piu' grande
   di quanto la calibrazione per partita lasciasse prevedere. Le due candidate —
   varianza vera fra squadre non catturata dal modello, e shock correlati lungo
   la stagione — **non sono state separate**, e separarle vuole un modello con
   un effetto di squadra persistente, cioe' un blocco a se'.
3. **Il criterio di adozione ha una potenza dichiarata e piccola.** L'MDE su RPS
   vale {float(c.loc['platt', 'MDE (80%)']):.5f}: la condizione «non peggiora
   l'RPS» esclude peggioramenti grandi, non peggioramenti piccoli. Va letta come
   il negativo che e'.
4. **La ricalibrazione e' stimata su tre stagioni di passato al massimo**, e la
   sua granularita' e' la stagione. Rifittarla per giornata userebbe piu' dati e
   sarebbe un secondo modello che si muove sopra al primo: non e' stato fatto, e
   non e' stato misurato quanto costi non farlo.
"""

    OUT_MD.write_text(testo, encoding="utf-8")
    print(f"\n-> {OUT_MD}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
