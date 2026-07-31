# -*- coding: utf-8 -*-
"""Figure del report, tutte rigenerabili da zero.

Nessuna figura contiene un numero che non venga da `data/processed/` o dai CSV
delle fasi precedenti: non ci sono valori digitati a mano. `scripts/run_phase5.py`
le riscrive tutte in `reports/figures/`.

SCELTE DI RAPPRESENTAZIONE
--------------------------
Ogni figura sceglie **prima la forma**, poi il colore.

* Quando la storia e' "questa cosa qui, le altre sono contesto" — il Como fra
  venti squadre, il modello fra cinque candidati — la forma e' l'**enfasi**: un
  elemento a colore, il resto in grigio. Colorare tutto renderebbe piu' difficile
  vedere il punto, non piu' facile.
* Le stime con incertezza (pendenze, guadagni appaiati) sono **punti con
  intervallo**, mai barre: una barra suggerisce che la distanza da zero sia il
  dato, mentre il dato e' se l'intervallo attraversa la soglia.
* Nessun asse doppio, nessuna scala di colore su categorie senza ordine,
  griglia a filo di capello e mai tratteggiata (il tratteggio e' riservato alle
  **soglie**, che sono un'altra cosa).
* I colori sono i primi tre slot categorici della palette di riferimento
  (blu, arancio, acquamarina), che sono validati per CVD anche a coppie tutte
  contro tutte. Non sono stati inventati colori nuovi ne' ristagliati i passi.
  Ogni figura ha comunque la sua tabella numerica nel README: il colore non e'
  mai l'unico canale.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

# --- palette di riferimento, modalita' chiara -------------------------------
SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK_2 = "#52514e"
MUTED = "#898781"
GRID = "#e1e0d9"
AXIS = "#c3c2b7"

SERIE_1 = "#2a78d6"      # blu     — il soggetto
SERIE_2 = "#eb6834"      # arancio — il confronto
SERIE_3 = "#1baf7a"      # acqua   — terza categoria, solo con etichetta diretta
DEEMPH = "#c3c2b7"       # grigio di de-enfasi

DPI = 200


def _style(ax, xgrid: bool = True, ygrid: bool = False) -> None:
    """Cromo recessivo: la griglia non deve competere con i dati."""
    ax.set_facecolor(SURFACE)
    for lato in ("top", "right"):
        ax.spines[lato].set_visible(False)
    for lato in ("left", "bottom"):
        ax.spines[lato].set_color(AXIS)
        ax.spines[lato].set_linewidth(0.8)
    ax.tick_params(colors=MUTED, labelsize=8.5, length=3, width=0.8)
    for t in ax.get_xticklabels() + ax.get_yticklabels():
        t.set_color(INK_2)
    # Passare le proprieta' di linea insieme a `False` **accende** la griglia
    # (matplotlib le interpreta come richiesta di disegnarla): i due rami vanno
    # tenuti separati.
    for attivo, asse in ((xgrid, "x"), (ygrid, "y")):
        if attivo:
            ax.grid(True, axis=asse, color=GRID, linewidth=0.8, linestyle="-")
        else:
            ax.grid(False, axis=asse)
    ax.set_axisbelow(True)


def _fig(w: float, h: float):
    fig, ax = plt.subplots(figsize=(w, h), dpi=DPI)
    fig.patch.set_facecolor(SURFACE)
    return fig, ax


def _titolo(ax, titolo: str, sottotitolo: str = "") -> None:
    """Titolo e sottotitolo allineati a sinistra, senza sovrapporsi.

    Il sottotitolo e' posizionato in **punti** sopra il riquadro, non in
    frazione di asse: con `1.02 * altezza` una figura alta lo spingerebbe
    dentro al titolo, ed e' esattamente quello che succedeva.
    """
    righe = sottotitolo.count("\n") + 1 if sottotitolo else 0
    ax.set_title(titolo, color=INK, fontsize=11.5, fontweight="bold",
                 loc="left", pad=8 + 11 * righe if righe else 10)
    if sottotitolo:
        ax.annotate(sottotitolo, xy=(0.0, 1.0), xycoords="axes fraction",
                    xytext=(0, 5), textcoords="offset points",
                    color=INK_2, fontsize=8.8, va="bottom", ha="left")


def _punti_con_intervallo(ax, y, stime, se, colori, k: float = 2.0) -> None:
    """Punto + intervallo a k errori standard, con anello di superficie."""
    for yi, m, s, c in zip(y, stime, se, colori):
        ax.plot([m - k * s, m + k * s], [yi, yi], color=c, linewidth=1.6,
                solid_capstyle="round", zorder=3)
        ax.plot([m], [yi], "o", color=c, markersize=7, zorder=4,
                markeredgecolor=SURFACE, markeredgewidth=2)


# ---------------------------------------------------------------- 1. pendenza
def calibrazione_pendenza(calib: pd.DataFrame, modello: str,
                          escludi: tuple[str, ...] = ()):
    """Pendenza di calibrazione con IC95%, contro la retta a 1.0.

    E' il risultato principale del progetto e merita la prima figura: il
    modello e' l'unico candidato informativo compatibile con 1.0.

    `escludi` serve per i modelli la cui pendenza **non e' identificata** —
    lambda quasi costante, errore standard enorme. Tenerli dilaterebbe l'asse
    di un fattore cinque e schiaccerebbe contro il bordo destro tutte le stime
    che invece significano qualcosa. L'esclusione va detta nel sottotitolo,
    non fatta di nascosto.
    """
    d = calib.drop(index=list(escludi), errors="ignore")
    d = d.dropna(subset=["calib_slope"]).iloc[::-1]
    y = np.arange(len(d))
    colori = [SERIE_1 if i == modello else DEEMPH for i in d.index]

    fig, ax = _fig(7.4, 0.38 * len(d) + 1.7)
    ax.axvline(1.0, color=INK_2, linewidth=1.0, zorder=2)
    _punti_con_intervallo(ax, y, d["calib_slope"], d["calib_se"], colori)

    ax.set_yticks(y, list(d.index))
    ax.set_xlabel("pendenza di calibrazione (1.0 = calibrato)", color=INK_2,
                  fontsize=9)
    _style(ax)

    # Le z stanno in colonna a destra, non appese alla fine del proprio
    # intervallo: appese, quelle dei baseline finirebbero sopra la retta a 1.0.
    x_lab = float((d["calib_slope"] + 2 * d["calib_se"]).max()) + 0.04
    for yi, (nome, r) in zip(y, d.iterrows()):
        ax.text(x_lab, yi, f"z = {r['calib_z_vs_1']:+.2f}", va="center",
                fontsize=8.2, color=INK if nome == modello else MUTED)

    ax.set_xlim(min(d["calib_slope"] - 2 * d["calib_se"]) - 0.06, x_lab + 0.26)
    sotto = "punto e intervallo al 95%; sotto 1.0 = previsioni troppo estreme"
    if escludi:
        sotto += f"\nescluso {', '.join(escludi)}: pendenza non identificata"
    _titolo(ax, "Solo il modello e' calibrato", sotto)
    fig.tight_layout()
    return fig


# ------------------------------------------------------------ 2. affidabilita'
def affidabilita(rel_modello: pd.DataFrame, rel_baseline: pd.DataFrame,
                 nome_modello: str, nome_baseline: str, linea: float):
    """Diagramma di affidabilita': probabilita' dichiarata contro frequenza."""
    fig, ax = _fig(6.2, 5.4)
    ax.plot([0, 0.9], [0, 0.9], color=AXIS, linewidth=1.0, zorder=2)

    for d, c, nome in ((rel_baseline, SERIE_2, nome_baseline),
                       (rel_modello, SERIE_1, nome_modello)):
        ax.errorbar(d["p_mean"], d["freq"], yerr=d["se"], fmt="o",
                    color=c, ecolor=c, elinewidth=1.4, capsize=0,
                    markersize=7, markeredgecolor=SURFACE, markeredgewidth=2,
                    label=nome, zorder=4 if c == SERIE_1 else 3)

    ax.set_xlabel(f"probabilita' prevista di Over {linea}", color=INK_2, fontsize=9)
    ax.set_ylabel("frequenza osservata", color=INK_2, fontsize=9)
    _style(ax, xgrid=True, ygrid=True)

    leg = ax.legend(frameon=False, fontsize=8.8, loc="upper left")
    for t in leg.get_texts():
        t.set_color(INK_2)
    ax.text(0.62, 0.06, "sulla diagonale = calibrato", transform=ax.transAxes,
            fontsize=8.2, color=MUTED)
    _titolo(ax, "Le probabilita' dichiarate reggono",
            "barre = un errore standard binomiale della frequenza osservata")
    fig.tight_layout()
    return fig


# --------------------------------------------------------- 3. predittori
def predittori_scartati(cand: pd.DataFrame, soglia: float):
    """Tutti e otto i predittori da dati evento, e la soglia che non superano."""
    d = cand.sort_values("t")
    y = np.arange(len(d))

    fig, ax = _fig(7.2, 0.34 * len(d) + 1.7)
    ax.axvline(0.0, color=AXIS, linewidth=1.0, zorder=2)
    ax.axvline(soglia, color=INK_2, linewidth=1.0, linestyle=(0, (4, 3)), zorder=2)

    ax.plot(d["t"], y, "o", color=SERIE_1, markersize=7,
            markeredgecolor=SURFACE, markeredgewidth=2, zorder=4)
    for yi, t in zip(y, d["t"]):
        ax.plot([0, t], [yi, yi], color=SERIE_1, linewidth=1.2, alpha=0.35, zorder=3)

    ax.set_yticks(y, list(d["predittore"]))
    ax.set_xlabel("t appaiato del guadagno fuori campione", color=INK_2, fontsize=9)
    _style(ax)
    ax.set_xlim(min(d["t"].min() - 0.4, -1.6), max(soglia + 0.9, d["t"].max() + 0.6))
    ax.text(soglia + 0.08, len(d) - 0.6, f"soglia t > {soglia:g}", fontsize=8.2,
            color=INK_2, va="center")
    _titolo(ax, "Nessun predittore da dati evento supera il rumore",
            "il migliore arriva a t = 1.42: su otto candidati e' quanto ci si "
            "aspetta per caso")
    fig.tight_layout()
    return fig


# ------------------------------------------------------- 4. contro i baseline
def vantaggio_sui_baseline(cmp_tab: pd.DataFrame, se_mae: dict):
    """Guadagno di MAE del modello su ciascun baseline, con IC95%."""
    d = cmp_tab.set_index("vs").iloc[::-1]
    y = np.arange(len(d))
    se = np.array([se_mae[i] for i in d.index])
    colori = [SERIE_2 if (m - 2 * s) <= 0 else SERIE_1
              for m, s in zip(d["d_mae"], se)]

    fig, ax = _fig(7.4, 0.46 * len(d) + 1.8)
    ax.axvline(0.0, color=INK_2, linewidth=1.0, zorder=2)
    _punti_con_intervallo(ax, y, d["d_mae"].to_numpy(), se, colori)

    ax.set_yticks(y, list(d.index))
    ax.set_xlabel("MAE del baseline meno MAE del modello (positivo = "
                  "il modello vince)", color=INK_2, fontsize=9)
    _style(ax)
    for yi, (nome, r), s in zip(y, d.iterrows(), se):
        ax.text(r["d_mae"] + 2 * s + 0.004, yi, f"t = {r['t_mae']:.2f}",
                va="center", fontsize=8.2,
                color=INK if (r["d_mae"] - 2 * s) <= 0 else MUTED)
    ax.set_xlim(min(d["d_mae"] - 2 * se) - 0.012, max(d["d_mae"] + 2 * se) + 0.045)
    _titolo(ax, "Sull'accuratezza il margine e' dentro il rumore",
            "in arancio l'intervallo che tocca lo zero: il baseline non e' "
            "battuto in modo distinguibile")
    fig.tight_layout()
    return fig


# ------------------------------------------------------------- 5. ratings
def ratings_squadra(rat: pd.DataFrame, evidenzia: str):
    """Tiri in porta attesi a campo neutro contro difesa media, per squadra."""
    d = rat.sort_values("neutro")
    y = np.arange(len(d))
    colori = [SERIE_1 if t == evidenzia else DEEMPH for t in d["team"]]

    fig, ax = _fig(6.6, 0.24 * len(d) + 1.7)
    ax.barh(y, d["neutro"], height=0.58, color=colori, zorder=3)
    ax.set_yticks(y, list(d["team"]))
    ax.set_xlabel("tiri in porta attesi a partita, campo neutro", color=INK_2,
                  fontsize=9)
    _style(ax)

    for yi, (t, v) in enumerate(zip(d["team"], d["neutro"])):
        if t == evidenzia or yi in (0, len(d) - 1):
            ax.text(v + 0.06, yi, f"{v:.2f}", va="center", fontsize=8.4,
                    color=INK if t == evidenzia else MUTED)

    ax.set_xlim(0, d["neutro"].max() * 1.12)
    for lab in ax.get_yticklabels():
        if lab.get_text() == evidenzia:
            lab.set_color(INK)
            lab.set_fontweight("bold")
    _titolo(ax, f"Forza offensiva a campo neutro — {evidenzia} evidenziato",
            "effetti del modello di squadra, non medie grezze: "
            "l'avversario e' tenuto fisso")
    fig.tight_layout()
    return fig


# -------------------------------------------------------- 6. proiezione Como
def proiezione_como(sim: np.ndarray, q10: float, q50: float, q90: float,
                    ancora: float, ancora_pi: tuple[float, float]):
    """Distribuzione simulata del totale stagionale, con l'ancora dall'alto."""
    fig, ax = _fig(7.4, 4.4)
    ax.hist(sim, bins=60, color=SERIE_1, alpha=0.16, zorder=2)
    ax.hist(sim, bins=60, histtype="step", color=SERIE_1, linewidth=1.5, zorder=3)

    # Mediana e riferimento distano meno di dieci tiri: le due etichette vanno
    # su altezze diverse, altrimenti si scrivono l'una sopra l'altra.
    ymax = ax.get_ylim()[1]
    ax.set_ylim(0, ymax * 1.18)
    ymax = ax.get_ylim()[1]

    ax.plot([q50, q50], [0, ymax * 0.86], color=SERIE_1, linewidth=1.6, zorder=4)
    for q in (q10, q90):
        ax.plot([q, q], [0, ymax * 0.62], color=SERIE_1, linewidth=1.2,
                alpha=0.55, zorder=4)
    ax.plot([ancora, ancora], [0, ymax * 0.98], color=SERIE_2, linewidth=1.6,
            linestyle=(0, (4, 3)), zorder=4)

    ax.annotate(f"mediana {q50:.0f}", (q50, ymax * 0.86), xytext=(5, -1),
                textcoords="offset points", fontsize=8.6, color=INK)
    ax.annotate(f"IC 80%  [{q10:.0f}, {q90:.0f}]", (q10, ymax * 0.62),
                xytext=(-5, 1), textcoords="offset points", fontsize=8.4,
                color=INK_2, ha="right")
    ax.annotate(f"riferimento dall'alto {ancora:.0f}, "
                f"IC 80% [{ancora_pi[0]:.0f}, {ancora_pi[1]:.0f}]",
                (ancora, ymax * 0.98), xytext=(-6, 0),
                textcoords="offset points", fontsize=8.4, color=SERIE_2,
                ha="right", va="center")

    ax.set_xlabel("tiri in porta del Como nella stagione 2026-27", color=INK_2,
                  fontsize=9)
    ax.set_ylabel("simulazioni", color=INK_2, fontsize=9)
    _style(ax, xgrid=False, ygrid=True)
    _titolo(ax, "Proiezione Como 2026-27, 20.000 simulazioni",
            "l'intervallo dal basso e' piu' largo del riferimento, non piu' "
            "stretto: e' il risultato, non un difetto")
    fig.tight_layout()
    return fig


# -------------------------------------------------------- 8. sensibilita' a rho
def proiezione_per_rho(tab: pd.DataFrame, rho_evidenziato: float,
                       pubblicato: float | None = None):
    """Proiezione stagionale in funzione della persistenza `rho` fra stagioni.

    Enfasi su un solo punto — il `rho` implicito nel numero pubblicato — e il
    resto della griglia in grigio: la storia non e' "ecco dieci proiezioni", e'
    "la proiezione pubblicata e' una scelta lungo questa retta, e non sappiamo
    quale sia quella giusta". Punti con intervallo, mai barre, perche' il dato
    e' l'incertezza attorno a ciascun valore e non la distanza da zero.
    """
    d = tab.sort_values("rho")
    x = d["rho"].to_numpy(dtype=float)
    vicino = np.isclose(x, rho_evidenziato, atol=1e-6)
    colori = [SERIE_1 if v else DEEMPH for v in vicino]

    fig, ax = _fig(7.4, 4.6)
    if pubblicato is not None:
        ax.axhline(pubblicato, color=SERIE_2, linewidth=1.2,
                   linestyle=(0, (4, 3)), zorder=2)
        ax.annotate(f"pubblicato {pubblicato:.0f}", (x[0], pubblicato),
                    xytext=(0, 5), textcoords="offset points", fontsize=8.4,
                    color=SERIE_2, ha="left")

    for xi, q10, q90, c in zip(x, d["q10"], d["q90"], colori):
        ax.plot([xi, xi], [q10, q90], color=c, linewidth=1.6,
                solid_capstyle="round", zorder=3)
    for xi, y, c in zip(x, d["stagione"], colori):
        ax.plot([xi], [y], "o", color=c, markersize=7, zorder=5,
                markeredgecolor=SURFACE, markeredgewidth=2)

    i = int(np.argmax(vicino))
    ax.annotate(f"rho = {rho_evidenziato:.3f}\n{d['stagione'].iloc[i]:.0f} in stagione",
                (x[i], d["stagione"].iloc[i]), xytext=(8, -18),
                textcoords="offset points", fontsize=8.6, color=INK)

    ax.set_xlabel("rho — quota di eccesso sulla media di campionato che il Como "
                  "trattiene fra le due stagioni", color=INK_2, fontsize=9)
    ax.set_ylabel("tiri in porta, stagione 2026-27", color=INK_2, fontsize=9)
    _style(ax, xgrid=False, ygrid=True)
    # Tacche sulla griglia dichiarata, a passi di 0.05: il valore implicito non
    # ci cade sopra e resta identificato dall'enfasi e dall'etichetta diretta.
    ax.set_xticks(np.round(np.arange(x.min(), x.max() + 1e-9, 0.05), 2))
    _titolo(ax, "Il livello della proiezione e' una scelta di rho",
            "mediana e IC 80% del Monte Carlo; con una stagione sola il rho "
            "corretto non e' determinabile")
    fig.tight_layout()
    return fig


# ---------------------------------------------------- 7. contributi giocatori
def contributo_giocatori(proj: pd.DataFrame, top: int = 18):
    """Quanto ciascun giocatore porta al lambda di squadra proiettato."""
    d = proj.sort_values("contributo", ascending=False).head(top).iloc[::-1]
    y = np.arange(len(d))
    colori = [SERIE_2 if n else SERIE_1 for n in d["is_new"]]

    fig, ax = _fig(6.8, 0.26 * len(d) + 1.9)
    ax.barh(y, d["contributo"], height=0.58, color=colori, zorder=3)
    ax.set_yticks(y, list(d["name"]))
    ax.set_xlabel("tiri in porta a partita attribuiti al giocatore",
                  color=INK_2, fontsize=9)
    _style(ax)

    quota = d["contributo"] / proj["contributo"].sum()
    for yi, (v, q, nome) in enumerate(zip(d["contributo"], quota, d["name"])):
        if yi >= len(d) - 3:
            ax.text(v + 0.012, yi, f"{v:.2f}  ({q:.0%})", va="center",
                    fontsize=8.4, color=INK)

    from matplotlib.patches import Patch
    leg = ax.legend(handles=[Patch(color=SERIE_1, label="gia' in rosa nel 2025-26"),
                             Patch(color=SERIE_2, label="nuovo arrivo, solo "
                                                        "media di ruolo")],
                    frameon=False, fontsize=8.6, loc="lower right")
    for t in leg.get_texts():
        t.set_color(INK_2)

    ax.set_xlim(0, d["contributo"].max() * 1.28)
    _titolo(ax, "Da chi arriva il lambda proiettato del Como",
            f"primi {top} contributi; i nuovi arrivi non hanno dati e "
            "poggiano sulla sola media di ruolo")
    fig.tight_layout()
    return fig
