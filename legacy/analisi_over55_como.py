import argparse
from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


matplotlib.use("Agg")

BASE_DIR = Path(__file__).resolve().parent
INPUT_CSV = BASE_DIR / "como_tip_quote_2526.csv"
OUTPUT_CHART = BASE_DIR / "risultato_over55_como.png"
OUTPUT_DETAIL = BASE_DIR / "dettaglio_scommesse_over55_como.csv"


def leggi_puntata() -> float:
    parser = argparse.ArgumentParser(
        description="Simula una puntata fissa sull'Over 5,5 tiri in porta del Como."
    )
    parser.add_argument(
        "--puntata",
        help="Importo in euro per ogni giornata (esempio: 2,50).",
    )
    args = parser.parse_args()

    valore = args.puntata
    if valore is None:
        valore = input("Puntata per ogni giornata in euro [1,00]: ").strip() or "1,00"

    try:
        puntata = float(valore.replace(",", "."))
    except ValueError:
        parser.error("la puntata deve essere un numero, per esempio 2 oppure 2,50")

    if puntata <= 0:
        parser.error("la puntata deve essere maggiore di zero")

    return round(puntata, 2)


def euro(value: float, signed: bool = False) -> str:
    sign = "+" if signed and value > 0 else ""
    return f"{sign}{value:,.2f} €".replace(",", "X").replace(".", ",").replace("X", ".")


puntata_per_giornata = leggi_puntata()
df = pd.read_csv(INPUT_CSV)
df["Vincente"] = df["TiP_reali"].ge(6)
df["Puntata"] = puntata_per_giornata
df["Ritorno_lordo"] = np.where(
    df["Vincente"], df["Over5.5"] * puntata_per_giornata, 0
).round(2)
df["Profitto_netto"] = (df["Ritorno_lordo"] - puntata_per_giornata).round(2)
df["Saldo_cumulato"] = df["Profitto_netto"].cumsum().round(2)

puntato = float(df["Puntata"].sum())
ritorno_lordo = float(df["Ritorno_lordo"].sum())
profitto_netto = float(df["Profitto_netto"].sum())
roi = profitto_netto / puntato * 100
vinte = int(df["Vincente"].sum())
perse = int((~df["Vincente"]).sum())

dettaglio = df[
    [
        "Giornata",
        "Data",
        "Avversario",
        "C/T",
        "TiP_reali",
        "Over5.5",
        "Vincente",
        "Puntata",
        "Ritorno_lordo",
        "Profitto_netto",
        "Saldo_cumulato",
    ]
].rename(
    columns={
        "C/T": "Casa_Trasferta",
        "Over5.5": "Quota_Over5.5",
        "Vincente": "Esito_vincente",
    }
)
dettaglio.to_csv(OUTPUT_DETAIL, index=False, encoding="utf-8-sig")

plt.rcParams.update(
    {
        "font.family": "DejaVu Sans",
        "axes.titleweight": "bold",
        "axes.titlesize": 15,
        "axes.labelsize": 10,
    }
)
fig, (ax1, ax2) = plt.subplots(
    2,
    1,
    figsize=(13, 8),
    sharex=True,
    gridspec_kw={"height_ratios": [2.2, 1]},
)
fig.patch.set_facecolor("#f6f7f9")
for ax in (ax1, ax2):
    ax.set_facecolor("white")
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(axis="y", color="#d9dee7", linewidth=0.8, alpha=0.8)

giornate = df["Giornata"].to_numpy()
saldo = df["Saldo_cumulato"].to_numpy()
giornate_linea = np.insert(giornate, 0, 0)
saldo_linea = np.insert(saldo, 0, 0)

ax1.axhline(0, color="#59636f", linewidth=1.1)
ax1.plot(
    giornate_linea,
    saldo_linea,
    color="#1565c0",
    linewidth=2.5,
    marker="o",
    markersize=3.8,
)
ax1.fill_between(
    giornate_linea,
    0,
    saldo_linea,
    where=saldo_linea >= 0,
    color="#34a853",
    alpha=0.12,
    interpolate=True,
)
ax1.fill_between(
    giornate_linea,
    0,
    saldo_linea,
    where=saldo_linea < 0,
    color="#d93025",
    alpha=0.12,
    interpolate=True,
)
ax1.scatter(
    [giornate[-1]],
    [saldo[-1]],
    s=85,
    color="#1565c0",
    edgecolor="white",
    linewidth=1.4,
    zorder=5,
)
ax1.annotate(
    f"Saldo finale: {euro(profitto_netto, signed=True)}",
    xy=(giornate[-1], saldo[-1]),
    xytext=(-12, 18),
    textcoords="offset points",
    ha="right",
    color="#0d47a1",
    fontsize=11,
    fontweight="bold",
)
ax1.set_ylabel("Profitto netto cumulato (€)")

metriche = (
    f"Puntato: {euro(puntato)}   |   Ritorno lordo: {euro(ritorno_lordo)}   |   "
    f"Profitto netto: {euro(profitto_netto, signed=True)}   |   "
    f"ROI: {roi:.1f}%   |   Vinte/perse: {vinte}/{perse}"
)
fig.suptitle(
    f"Como — {euro(puntata_per_giornata)} su Over 5,5 tiri in porta a ogni giornata",
    x=0.07,
    y=0.975,
    ha="left",
    fontsize=20,
    fontweight="bold",
)
fig.text(
    0.07,
    0.93,
    metriche.replace(".", ","),
    fontsize=10,
    color="#424b57",
    ha="left",
    va="center",
)

colori = np.where(df["Vincente"], "#34a853", "#d93025")
ax2.bar(giornate, df["Profitto_netto"], color=colori, width=0.72)
ax2.axhline(0, color="#59636f", linewidth=1.1)
ax2.set_ylabel("Profitto giornata (€)")
ax2.set_xlabel("Giornata")
ax2.set_xticks(np.arange(1, len(df) + 1))
ax2.tick_params(axis="x", labelsize=8)

fig.text(
    0.99,
    0.012,
    "Vincita: almeno 6 tiri in porta. Quote Over 5,5 arrotondate a due decimali.",
    ha="right",
    fontsize=8.5,
    color="#626b76",
)
fig.tight_layout(rect=(0, 0.035, 1, 0.90))
fig.savefig(OUTPUT_CHART, dpi=180, bbox_inches="tight", facecolor=fig.get_facecolor())

print(f"Scommesse: {len(df)}")
print(f"Puntata per giornata: {puntata_per_giornata:.2f}")
print(f"Vinte: {vinte}")
print(f"Perse: {perse}")
print(f"Puntato: {puntato:.2f}")
print(f"Ritorno lordo: {ritorno_lordo:.2f}")
print(f"Profitto netto: {profitto_netto:.2f}")
print(f"ROI: {roi:.2f}%")
print(f"Grafico: {OUTPUT_CHART}")
print(f"Dettaglio: {OUTPUT_DETAIL}")
