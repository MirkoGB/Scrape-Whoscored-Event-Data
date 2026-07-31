# -*- coding: utf-8 -*-
"""
Tiri in porta (shots on target) di una squadra, partita per partita.

Uso:
    python tiri_in_porta.py "Napoli"
    python tiri_in_porta.py "AC Milan" --csv serie_a_2025_2026_events.csv
    python tiri_in_porta.py Roma --no-plot          # solo tabella
    python tiri_in_porta.py Roma --out roma.png     # salva il grafico

Definizione usata (convenzione WhoScored):
    tiro in porta = evento 'SavedShot' NON bloccato da un difensore  +  'Goal'
                    (esclusi gli autogol).
    Sono esclusi: MissedShots, ShotOnPost (legno) e i tiri respinti da un
    giocatore di movimento (shotBlocked == True).

Il CSV completo pesa ~1 GB: viene letto a blocchi e solo sulle colonne
necessarie, quindi la RAM usata resta bassa. Se la cartella
`data/serie_a_2025_2026/` e' presente, viene usata di default perche' e' molto
piu' veloce (un CSV per partita).
"""

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

BASE = Path(__file__).resolve().parent
BIG_CSV = BASE / 'serie_a_2025_2026_events.csv'
MATCH_DIR = BASE / 'data' / 'serie_a_2025_2026'
MATCHES_JSON = BASE / 'data' / 'serie_a_2025_2026_matches.json'

# Solo queste colonne servono: leggere le altre 250 sarebbe uno spreco.
COLS = ['matchId', 'teamId', 'h_a', 'type', 'isShot',
        'isGoal', 'isOwnGoal', 'shotBlocked', 'startDate']

INK = '#1c1c1c'
MUTED = '#8a8a8a'
BAR = '#3b6fd4'          # tinta unica: una sola serie, nessuna legenda
BAR_HI = '#1c3f8f'       # step piu' scuro della stessa rampa per il massimo
GRID = '#e4e4e7'


# ──────────────────────────────────────────────
#  LETTURA EVENTI
# ──────────────────────────────────────────────
def _read_one(path):
    """Legge un CSV partita tenendo solo COLS.

    Non tutti i file hanno le stesse colonne (es. 'isOwnGoal' manca dove non ci
    sono stati autogol), quindi si intersecano le colonne e si reintegrano
    quelle mancanti come False.
    """
    header = pd.read_csv(path, nrows=0).columns
    present = [c for c in COLS if c in header]
    df = pd.read_csv(path, usecols=present, low_memory=False)
    df['matchId'] = df.get('matchId', pd.Series(int(path.stem), index=df.index))
    for col in COLS:
        if col not in df.columns:
            df[col] = False
    return df[COLS]


def read_events(csv_path=None, chunksize=500_000):
    """Restituisce un DataFrame con le sole colonne COLS di tutti gli eventi."""
    if csv_path is None and MATCH_DIR.is_dir():
        files = sorted(MATCH_DIR.glob('*.csv'))
        if files:
            print(f'Lettura di {len(files)} file partita da {MATCH_DIR.name}/ ...')
            return pd.concat([_read_one(f) for f in files], ignore_index=True)

    path = Path(csv_path) if csv_path else BIG_CSV
    if not path.is_file():
        sys.exit(f'File non trovato: {path}')

    print(f'Lettura a blocchi di {path.name} ({path.stat().st_size / 1e9:.2f} GB) ...')
    chunks = []
    for i, chunk in enumerate(pd.read_csv(path, usecols=COLS,
                                          chunksize=chunksize, low_memory=False), 1):
        chunks.append(chunk)
        print(f'  blocco {i} ({i * chunksize:,} righe lette)', end='\r')
    print()
    return pd.concat(chunks, ignore_index=True)


def team_id_map(events):
    """teamId -> nome squadra, ricavato incrociando h_a con il JSON delle partite."""
    if not MATCHES_JSON.is_file():
        sys.exit(f'Manca {MATCHES_JSON}: senza di esso i teamId non hanno un nome.')

    with open(MATCHES_JSON, encoding='utf-8') as fh:
        matches = json.load(fh)

    # url = /matches/<matchId>/live/...
    by_match = {int(m['url'].split('/')[2]): (m['home'], m['away']) for m in matches}

    names = {}
    pairs = events[['matchId', 'teamId', 'h_a']].drop_duplicates()
    for match_id, team_id, side in pairs.itertuples(index=False):
        if match_id in by_match:
            names[team_id] = by_match[match_id][0 if side == 'h' else 1]
    return names


def resolve_team(name, names):
    """Match esatto, altrimenti 'contiene', case-insensitive."""
    wanted = name.strip().lower()
    exact = [tid for tid, n in names.items() if n.lower() == wanted]
    if exact:
        return exact[0], names[exact[0]]

    partial = sorted({n for n in names.values() if wanted in n.lower()})
    if len(partial) == 1:
        tid = next(t for t, n in names.items() if n == partial[0])
        return tid, partial[0]
    if len(partial) > 1:
        sys.exit(f"'{name}' e' ambiguo: {', '.join(partial)}")

    sys.exit(f"Squadra '{name}' non trovata.\n"
             f"Disponibili: {', '.join(sorted(set(names.values())))}")


# ──────────────────────────────────────────────
#  CALCOLO
# ──────────────────────────────────────────────
def shots_on_target(events):
    """Maschera booleana dei tiri in porta.

    La definizione vive in `sot/shots.py` ed e' una sola per tutto il repo:
    duplicarla qui significherebbe poterla far divergere senza accorgersene.
    """
    from sot.shots import shots_on_target_mask
    return shots_on_target_mask(events)


def per_match_table(events, team_id, names):
    """Una riga per partita: giornata, avversario, casa/trasferta, tiri in porta."""
    on_target = shots_on_target(events)

    # Tutte le partite giocate dalla squadra (anche quelle con 0 tiri in porta).
    played = events.loc[events['teamId'] == team_id,
                        ['matchId', 'h_a', 'startDate']].drop_duplicates('matchId')

    counts = (events.loc[on_target & (events['teamId'] == team_id)]
              .groupby('matchId').size().rename('tiri_in_porta'))

    # Avversario = l'altro teamId presente nella stessa partita.
    others = events.loc[events['matchId'].isin(played['matchId']), ['matchId', 'teamId']]
    others = others[others['teamId'] != team_id].drop_duplicates('matchId')
    others['avversario'] = others['teamId'].map(names)

    df = (played
          .merge(counts, on='matchId', how='left')
          .merge(others[['matchId', 'avversario']], on='matchId', how='left'))
    df['tiri_in_porta'] = df['tiri_in_porta'].fillna(0).astype(int)
    df['data'] = pd.to_datetime(df['startDate']).dt.date
    df['dove'] = df['h_a'].map({'h': 'Casa', 'a': 'Trasferta'})
    df = df.sort_values('data').reset_index(drop=True)
    df.insert(0, 'giornata', df.index + 1)
    return df[['giornata', 'data', 'avversario', 'dove', 'tiri_in_porta', 'matchId']]


# ──────────────────────────────────────────────
#  GRAFICO
# ──────────────────────────────────────────────
def plot(df, team, out=None):
    import matplotlib.pyplot as plt

    labels = [f"{'vs' if d == 'Casa' else '@'} {a}"
              for a, d in zip(df['avversario'], df['dove'])]
    vals = df['tiri_in_porta'].tolist()
    top = max(vals) if vals else 0
    colors = [BAR_HI if v == top and top > 0 else BAR for v in vals]

    fig, ax = plt.subplots(figsize=(max(9, len(df) * 0.34), 5.2))
    bars = ax.bar(range(len(df)), vals, color=colors, width=0.72)

    media = df['tiri_in_porta'].mean() if len(df) else 0
    ax.axhline(media, color=MUTED, lw=1, ls='--', zorder=0)
    ax.text(len(df) - 0.4, media, f'  media {media:.1f}',
            va='center', ha='left', fontsize=8, color=MUTED)

    # Etichette selettive: solo le partite con il massimo di tiri in porta.
    for bar, v in zip(bars, vals):
        if v == top and top > 0:
            ax.text(bar.get_x() + bar.get_width() / 2, v + top * 0.02, str(v),
                    ha='center', va='bottom', fontsize=8.5, color=INK)

    ax.set_title(f'{team} — tiri in porta per partita', fontsize=13,
                 color=INK, pad=14, loc='left')
    ax.set_ylabel('Tiri in porta', fontsize=9, color=MUTED)
    ax.set_xticks(range(len(df)))
    ax.set_xticklabels(labels, rotation=90, fontsize=7.5, color=MUTED)
    ax.tick_params(axis='y', labelsize=8, colors=MUTED, length=0)
    ax.set_xlim(-0.8, len(df) - 0.2)
    ax.set_ylim(0, max(top * 1.15, 1))
    ax.yaxis.grid(True, color=GRID, lw=0.8)
    ax.set_axisbelow(True)
    for side in ('top', 'right', 'left'):
        ax.spines[side].set_visible(False)
    ax.spines['bottom'].set_color(GRID)
    fig.tight_layout()

    if out:
        fig.savefig(out, dpi=160, bbox_inches='tight', facecolor='white')
        print(f'Grafico salvato in {out}')
    else:
        plt.show()


# ──────────────────────────────────────────────
def main():
    ap = argparse.ArgumentParser(description='Tiri in porta per partita di una squadra.')
    ap.add_argument('squadra', help="Nome squadra, es. 'Napoli', 'AC Milan'")
    ap.add_argument('--csv', help='CSV eventi da usare (default: cartella data/ o CSV unico)')
    ap.add_argument('--out', help='Salva il grafico su file invece di mostrarlo')
    ap.add_argument('--no-plot', action='store_true', help='Stampa solo la tabella')
    ap.add_argument('--save-csv', help='Esporta la tabella risultante in CSV')
    args = ap.parse_args()

    events = read_events(args.csv)
    names = team_id_map(events)
    team_id, team = resolve_team(args.squadra, names)

    df = per_match_table(events, team_id, names)

    print(f'\n{team}: {len(df)} partite, '
          f'{df["tiri_in_porta"].sum()} tiri in porta totali '
          f'(media {df["tiri_in_porta"].mean():.2f} a partita)\n')
    print(df.drop(columns='matchId').to_string(index=False))

    if args.save_csv:
        df.to_csv(args.save_csv, index=False)
        print(f'\nTabella salvata in {args.save_csv}')

    if not args.no_plot:
        plot(df, team, args.out)


if __name__ == '__main__':
    main()
