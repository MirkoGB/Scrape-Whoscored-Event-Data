# -*- coding: utf-8 -*-
"""La configurazione della lega, separata dal codice.

`docs/regole_fantacalcio.md` §6 lo chiede esplicitamente: bonus, malus, fasce e
formato si modificano **senza riscrivere ne' riaddestrare la pipeline**. Questo
modulo e' quel posto. Non contiene modelli, non legge dati, non stima niente:
sono le regole del gioco, e le regole del gioco sono un input.

## Cosa e' deciso

**Tutte e cinque le voci di §0**, prese dall'utente il **2026-08-03**. La `0.3`
e' arrivata per ultima ed e' `escludi`. Il meccanismo che si fermava — 
`gestione_sv()` che solleva `DecisioneMancante` — **resta in piedi**: non e'
un'impalcatura da togliere una volta risolto il caso, e' il modo in cui una
prossima voce `[DA DECIDERE]` fara' fallire il codice invece di prendere un
default. Un test lo verifica ancora, mettendo la costante a `None`.

## Perche' `N_DIFENSORI` non e' un numero

`[DECISO 0.2 — dipende dal modulo]`. Era la contraddizione (2) del Blocco 0: il
documento diceva `n_difensori: 4` e i sette moduli ammessi ne schierano 3, 4 o 5,
quindi il test di coerenza che §3.2 pretende sarebbe stato insoddisfacibile per
costruzione. Con la decisione presa, il test diventa possibile ed e' scritto:
**per ogni modulo ammesso, i difensori che concorrono al modificatore sono
quelli schierati**.

Ne seguono due conseguenze operative che §2.2 aveva gia' previsto e che ora
sono vincolanti:

1. la simulazione del modificatore va fatta **per modulo**, non una volta sola;
2. il contributo marginale di un difensore e' relativo a **una linea e a un
   modulo**, e un numero senza entrambi e' incompleto.
"""

from __future__ import annotations

from dataclasses import dataclass, field


class DecisioneMancante(RuntimeError):
    """Una voce `[DA DECIDERE]` e' stata incontrata dal codice.

    Non si sceglie un valore plausibile, non si assume un default, non si
    prosegue con un segnaposto: si solleva questa e si chiede.
    """


# --------------------------------------------------------------------------
# 1. Bonus e malus — §1.1, decisi dall'utente
#
# **NON e' il barema della fonte.** Quello sta in
# `acquisition/fantacalcio/pagina.BAREME_FONTE` ed e' stato ricavato per
# differenza dai dati; questo e' il regolamento di *questa* lega. Le due
# differiscono su una voce misurabile: **la porta inviolata**, che la fonte non
# applica e questa lega si'. Percio' il fantavoto di lega si **ricalcola dai
# bonus** e non si legge mai dalla colonna `fantavoto_*` (vincolo 7).
# --------------------------------------------------------------------------
BONUS = {
    "gol_segnati": +3.0,
    "rigori_segnati": +3.0,       # il gol su rigore NON e' anche in gol_segnati
    "rigori_sbagliati": -3.0,
    "rigori_parati": +3.0,        # solo portiere
    "assist": +1.0,
    "ammonizione": -0.5,
    "espulsione": -1.0,
    "autoreti": -2.0,
    "gol_subiti": -1.0,           # solo portiere, -1 per ogni gol
    "porta_inviolata": +1.0,      # solo portiere — la voce che la fonte non ha
}

# `player of the match` esiste come colonna nella fonte e **non entra**: e'
# un'opzione di lega, e in questa lega non c'e'. Dichiarato invece che omesso,
# perche' un domani qualcuno vedra' la colonna e si chiedera' perche'.
FUORI_DAL_FANTAVOTO = ("player_of_the_match",)

RUOLI = ("p", "d", "c", "a")
SOLO_PORTIERE = ("rigori_parati", "gol_subiti", "porta_inviolata")


# --------------------------------------------------------------------------
# 2. Modificatore di difesa — §2, decisioni 0.1 e 0.2 prese, 0.3 no
# --------------------------------------------------------------------------

@dataclass(frozen=True)
class Fascia:
    """Intervallo **semiaperto** `[min, max)`. `None` = illimitato."""
    minimo: float | None
    massimo: float | None
    bonus: float

    def contiene(self, media: float) -> bool:
        if self.minimo is not None and media < self.minimo:
            return False
        if self.massimo is not None and media >= self.massimo:
            return False
        return True


# `[DECISO 0.1 — 2026-08-03]` tre fasce, soglie 6.00 / 6.50 / 7.00.
# `[DECISO 0.4]` sotto la soglia minima e' un **malus**, non zero.
#
# Gli intervalli sono semiaperti e coprono l'intera retta reale: e' un
# invariante, non uno stile. Le fasce dichiarate nel documento prima di questa
# decisione avevano una sovrapposizione (6.75 in due fasce), un buco (nessuna
# fascia conteneva 7.00 esatto) e due valori duplicati.
FASCE = (
    Fascia(None, 6.00, -1.0),
    Fascia(6.00, 6.50, +1.0),
    Fascia(6.50, 7.00, +3.0),
    Fascia(7.00, None, +6.0),
)


def modificatore(media_difensiva: float) -> float:
    """Il bonus di fascia per una media difensiva. Copre tutta la retta reale."""
    for f in FASCE:
        if f.contiene(media_difensiva):
            return f.bonus
    raise AssertionError(f"nessuna fascia contiene {media_difensiva}: "
                         "le fasce non coprono la retta, ed e' un invariante")


# `[DECISO 0.3 — 2026-08-03]` **escludi**: un difensore senza voto esce dalla
# media e la linea si accorcia. Le altre due letture — sostituirlo con un
# panchinaro, oppure annullare il modificatore — davano risultati diversi sulla
# stessa giornata, e la differenza non era piccola.
#
# **Conseguenza che "escludi" porta con se' e che va tenuta a mente leggendo i
# numeri**: escludere un s.v. NON e' neutro. La media si ricalcola su meno
# elementi, quindi diventa **piu' variabile**, e con fasce a scalini piu'
# variabile non vuol dire ne' meglio ne' peggio a priori — dipende da dove sta
# la linea rispetto alle soglie. E' esattamente il fenomeno di convessita' che
# §2.2 chiede di misurare invece di assumere, e per questo il modificatore si
# simula per giornata e non si applica alle medie di stagione.
GESTIONE_SV: str | None = "escludi"
GESTIONE_SV_AMMESSE = ("escludi", "sostituisci_con_panchina", "annulla_modificatore")


def gestione_sv() -> str:
    """Si ferma finche' la 0.3 non e' decisa, invece di scegliere per l'utente."""
    if GESTIONE_SV is None:
        raise DecisioneMancante(
            "docs/regole_fantacalcio.md §0, decisione 0.3: come si tratta un "
            "difensore senza voto dentro la linea difensiva. Valori ammessi: "
            f"{GESTIONE_SV_AMMESSE}. Il modificatore non si calcola senza."
        )
    if GESTIONE_SV not in GESTIONE_SV_AMMESSE:
        raise ValueError(f"GESTIONE_SV={GESTIONE_SV!r} fuori da {GESTIONE_SV_AMMESSE}")
    return GESTIONE_SV


# --------------------------------------------------------------------------
# 3. Formato della lega — §3.2, `[DECISO 0.5 — 2026-08-03]`, valori veri
# --------------------------------------------------------------------------

@dataclass(frozen=True)
class Modulo:
    """`"3-4-3"` -> difensori 3, centrocampisti 4, attaccanti 3, portiere 1."""
    nome: str

    @property
    def reparti(self) -> tuple[int, int, int]:
        d, c, a = (int(x) for x in self.nome.split("-"))
        return d, c, a

    @property
    def difensori(self) -> int:
        return self.reparti[0]

    @property
    def n_difensori_modificatore(self) -> int:
        """`[DECISO 0.2]` concorrono **tutti** i difensori schierati.

        E' qui e non in una costante perche' la decisione dice esattamente
        questo: non e' un numero della lega, e' una funzione del modulo.
        """
        return self.difensori

    def __post_init__(self):
        if sum(self.reparti) != 10:
            raise ValueError(f"il modulo {self.nome} non schiera dieci giocatori di movimento")


@dataclass(frozen=True)
class Lega:
    n_squadre: int = 8
    budget_asta: int = 1000
    portieri: int = 3
    difensori: int = 8
    centrocampisti: int = 8
    attaccanti: int = 6
    moduli: tuple[Modulo, ...] = field(default_factory=lambda: tuple(
        Modulo(n) for n in ("3-4-3", "3-5-2", "4-3-3", "4-4-2",
                            "4-5-1", "5-3-2", "5-4-1")))

    @property
    def rosa(self) -> dict[str, int]:
        return {"p": self.portieri, "d": self.difensori,
                "c": self.centrocampisti, "a": self.attaccanti}

    @property
    def giocatori_per_rosa(self) -> int:
        return sum(self.rosa.values())

    @property
    def difensori_schierabili(self) -> set[int]:
        """Quante linee difensive diverse i moduli ammessi permettono.

        E' l'insieme su cui il modificatore va simulato: con `n_difensori` fisso
        sarebbe stato un solo valore, e §2.2 avrebbe avuto un caso solo da
        considerare invece di tre.
        """
        return {m.n_difensori_modificatore for m in self.moduli}

    def verifica(self) -> None:
        """Gli invarianti che §3.2 pretende. Si chiamano, non si sperano.

        Il piu' importante e' l'ultimo: **la rosa deve poter schierare ogni
        modulo ammesso**. Con 8 difensori in rosa e un 5-3-2 servono almeno 5
        difensori disponibili, e la rosa li ha; se un domani qualcuno abbassasse
        `difensori` a 4 il formato diventerebbe incoerente in silenzio.
        """
        if self.budget_asta <= 0:
            raise ValueError("senza budget il confronto valore/quotazione non e' definibile")
        if self.n_squadre < 2:
            raise ValueError("una lega ha almeno due squadre")
        for m in self.moduli:
            d, c, a = m.reparti
            if d > self.difensori or c > self.centrocampisti or a > self.attaccanti:
                raise ValueError(
                    f"il modulo {m.nome} non e' schierabile con la rosa {self.rosa}")
        if self.portieri < 1:
            raise ValueError("serve almeno un portiere")

    @property
    def crediti_per_giocatore(self) -> float:
        """Il prezzo medio se il budget si spalmasse su tutta la rosa.

        Non e' una previsione: e' il numero con cui si legge qualunque
        quotazione. Un giocatore da 30 crediti su 1000 e' il 3% del budget, ed e'
        quella la scala su cui il modello va giudicato.
        """
        return self.budget_asta / self.giocatori_per_rosa


LEGA = Lega()
LEGA.verifica()
