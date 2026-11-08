"""Stime dopo G5, indipendenti dai regolamenti. Calibrazione cronologica."""
from __future__ import annotations

import numpy as np
import pandas as pd

from sot.rose import RoseError

HORIZONS = (5, 8, 33)
GRID = (float('inf'), 100., 50., 20., 10., 5., 3., 1., 0.)
MODELS = ('storico', 'recente', 'combinato')
COMPONENTS = ('p', 'voto', 'bonus')


def validate_calendar(votes, matches, season, complete=True):
    """Non attribuire zero contributi a partite della fonte mancanti."""
    m = matches[matches.stagione.eq(season)].copy()
    v = votes[votes.stagione.eq(season) & ~votes.allenatore].copy()
    expected = set(range(1, 39 if complete else 6))
    if set(m.giornata) != expected or not m.groupby('giornata').size().eq(10).all():
        raise RoseError(f'{season}: calendario incompleto')
    if m.partita_id.duplicated().any() or v.duplicated(['partita_id', 'giocatore_id']).any():
        raise RoseError(f'{season}: partite o voti duplicati')
    if set(v.partita_id) != set(m.partita_id):
        raise RoseError(f'{season}: mancano pagine voti per alcune partite')
    by_match = m.set_index('partita_id')
    if not v.giornata.eq(v.partita_id.map(by_match.giornata)).all():
        raise RoseError(f'{season}: giornate incoerenti fra voti e calendario')
    if not pd.to_datetime(v.data).eq(pd.to_datetime(v.partita_id.map(by_match.data))).all():
        raise RoseError(f'{season}: date voti/calendario incoerenti')
    if v.giocatore_id.isna().any() or (v.voto_redazione.notna() & v.fantavoto_redazione.isna()).any():
        raise RoseError(f'{season}: voti o identità incompleti')
    cutoff = (pd.to_datetime(m.loc[m.giornata.eq(6), 'data']).min() - pd.Timedelta(days=1)
              if complete else pd.to_datetime(m.data).max())
    if pd.to_datetime(m.loc[m.giornata.le(5), 'data']).gt(cutoff).any():
        raise RoseError(f'{season}: recuperi G1-G5 oltre il cutoff; gestione esplicita richiesta')
    if complete and pd.to_datetime(m.loc[m.giornata.gt(5), 'data']).le(cutoff).any():
        raise RoseError(f'{season}: gare successive anticipate prima del cutoff')
    return cutoff


def observed(rows):
    rated = rows[rows.voto_redazione.notna()].copy()
    rated['bonus'] = rated.fantavoto_redazione - rated.voto_redazione
    g = rated.groupby('giocatore_id')
    return g.agg(n=('voto_redazione', 'size'), voto=('voto_redazione', 'mean'),
                 bonus=('bonus', 'mean'), punti=('fantavoto_redazione', 'sum'))


def features(votes, season, cutoff):
    """Feature esclusivamente da passato e righe già osservate prima di G6."""
    clean = votes[~votes.allenatore].copy()
    prior = clean[clean.stagione.lt(season)]
    early = clean[clean.stagione.eq(season) & clean.giornata.le(5)
                  & pd.to_datetime(clean.data).le(pd.Timestamp(cutoff))].copy()
    if prior.empty or early.empty:
        raise RoseError(f'{season}: passato o prefisso G1-G5 assente')
    # Identità, ruolo e club sono quelli osservati al cutoff, mai dal listone futuro.
    meta = early.sort_values(['data', 'partita_id']).drop_duplicates('giocatore_id', keep='last')
    out = meta[['giocatore_id', 'giocatore', 'ruolo', 'squadra_id']].set_index('giocatore_id')
    if not out.ruolo.isin(['p', 'd', 'c', 'a']).all():
        raise RoseError('Ruolo non valido nel prefisso storico')
    recent = observed(early)
    out['n_recent'] = recent.n.reindex(out.index).fillna(0)
    out['recent_p'] = out.n_recent / 5
    if out.n_recent.gt(5).any():
        raise RoseError('Più di cinque voti per giocatore nel prefisso')
    years = []
    for s, rows in prior.groupby('stagione'):
        stats = observed(rows)
        ids = rows.sort_values(['data', 'partita_id']).drop_duplicates('giocatore_id', keep='last').set_index('giocatore_id')
        stats = ids[['ruolo']].join(stats)
        stats['n'] = stats.n.fillna(0)
        if stats.n.gt(38).any():
            raise RoseError(f'{s}: più di 38 voti per giocatore')
        stats['p'] = stats.n / 38
        stats['stagione'] = s
        years.append(stats.reset_index())
    past = pd.concat(years, ignore_index=True)
    role_p = past.groupby('ruolo').p.mean()
    rated_prior = prior[prior.voto_redazione.notna()].copy()
    rated_prior['bonus'] = rated_prior.fantavoto_redazione - rated_prior.voto_redazione
    role_vote = rated_prior.groupby('ruolo').voto_redazione.mean()
    role_bonus = rated_prior.groupby('ruolo').bonus.mean()
    year = int(season[:4])
    previous = past[past.stagione.eq(f'{year-1}-{year}')].set_index('giocatore_id')
    out['n_previous'] = previous.n.reindex(out.index)
    out['prior_ruolo'] = out.n_previous.isna()
    for key, role in (('p', role_p), ('voto', role_vote), ('bonus', role_bonus)):
        out[f'prior_ruolo_{key}'] = previous[key].reindex(out.index).isna()
        out[f'history_{key}'] = previous[key].reindex(out.index).fillna(out.ruolo.map(role))
        if out[f'history_{key}'].isna().any():
            raise RoseError(f'Prior di ruolo mancante: {key}')
    out['recent_voto'] = recent.voto.reindex(out.index).fillna(out.history_voto)
    out['recent_bonus'] = recent.bonus.reindex(out.index).fillna(out.history_bonus)
    out['stagione'] = season
    out['cutoff'] = str(pd.Timestamp(cutoff).date())
    return out.reset_index()


def targets(votes, season, horizon, ids):
    rows = votes[votes.stagione.eq(season) & ~votes.allenatore
                 & votes.giornata.between(6, 5+horizon)]
    out = observed(rows).reindex(ids)
    # Calendario/pagine completi sono verificati prima: nessun voto pubblicato
    # significa nessun contributo FC, senza inventare minuti o diagnosi.
    out[['n', 'punti']] = out[['n', 'punti']].fillna(0)
    out['p'] = out.n / horizon
    return out.rename(columns=lambda c: f'y_{c}').reset_index()


def predict(frame, horizon, model, k=None):
    if model not in MODELS:
        raise ValueError(model)
    k = k or {}
    out = frame[['giocatore_id', 'ruolo', 'stagione']].copy()
    for component in COMPONENTS:
        old, recent = frame[f'history_{component}'].to_numpy(), frame[f'recent_{component}'].to_numpy()
        exposure = np.full(len(frame), 5.) if component == 'p' else frame.n_recent.to_numpy()
        strength = np.inf if model == 'storico' else 0. if model == 'recente' else k[component]
        w = np.zeros(len(frame)) if np.isinf(strength) else np.divide(
            exposure, exposure+strength, out=np.zeros(len(frame)), where=(exposure+strength)>0)
        out[component] = w*recent + (1-w)*old
        out[f'peso_recente_{component}'] = w
    out['presenze'] = out.p * horizon
    out['fv_condizionato'] = out.voto + out.bonus
    out['punti'] = out.presenze * out.fv_condizionato
    out['modello'] = model
    out['orizzonte'] = horizon
    return out


def tune(training, horizon):
    if not training:
        raise RoseError('Calibrazione senza stagioni precedenti')
    joined = pd.concat(training, ignore_index=True)
    chosen, losses = {}, []
    for component in COMPONENTS:
        best = np.inf
        for strength in GRID:
            trial = {c: strength for c in COMPONENTS}
            prediction = predict(joined, horizon, 'combinato', trial)
            valid = joined[f'y_{component}'].notna().to_numpy()
            if not valid.any():
                raise RoseError(f'Bersaglio di calibrazione assente: {component}')
            errors = np.abs(prediction[component].to_numpy() - joined[f'y_{component}'].to_numpy())
            loss = float(errors[valid].mean())
            losses.append(dict(componente=component, k=None if np.isinf(strength) else strength, mae=loss))
            if loss < best - 1e-12:
                chosen[component], best = strength, loss
    return chosen, losses


def walkforward(votes, matches):
    seasons = sorted(votes.stagione.unique())
    tables, predictions, calibrations = {}, [], []
    for season in seasons:
        cutoff = validate_calendar(votes, matches, season)
        if season == seasons[0]:
            continue
        x = features(votes, season, cutoff)
        for horizon in HORIZONS:
            table = x.merge(targets(votes, season, horizon, x.giocatore_id), on='giocatore_id', validate='one_to_one')
            previous = [t for (s, h), t in tables.items() if s < season and h == horizon]
            if previous:
                k, losses = tune(previous, horizon)
                calibrations.append(dict(stagione=season, orizzonte=horizon, stagioni_training=sorted({t.stagione.iloc[0] for t in previous}),
                                         k={c: None if np.isinf(v) else v for c, v in k.items()}, griglia=losses))
                for model in MODELS:
                    p = predict(x, horizon, model, k)
                    p = p.merge(table[['giocatore_id', 'y_n', 'y_punti', 'y_voto', 'y_bonus', 'y_p', 'prior_ruolo', 'n_recent']], on='giocatore_id', validate='one_to_one')
                    predictions.append(p)
            tables[(season, horizon)] = table
    return pd.concat(predictions, ignore_index=True), tables, calibrations


def metrics(predictions, per_role=False):
    rows = []
    keys_to_group = ['stagione', 'orizzonte', 'modello'] + (['ruolo'] if per_role else [])
    for keys, group in predictions.groupby(keys_to_group):
        row = dict(zip(keys_to_group, keys))
        row['giocatori'] = len(group)
        row['con_voto_futuro'] = int(group.y_voto.notna().sum())
        for predicted, observed_col in (('punti','y_punti'), ('presenze','y_n'), ('voto','y_voto'), ('bonus','y_bonus')):
            row[f'mae_{predicted}'] = float((group[predicted] - group[observed_col]).abs().mean())
        # Media degli errori quadratici binari per turno, ricostruibile dal
        # numero di voti: E[(p-y)^2] = p² - 2p E[y] + E[y].
        row['brier_presenza'] = float((group.p**2 - 2*group.p*group.y_p + group.y_p).mean())
        row['bias_presenze'] = float((group.presenze-group.y_n).mean())
        rows.append(row)
    return pd.DataFrame(rows)


def select_models(predictions):
    summary = metrics(predictions)
    selections = {}
    for horizon in HORIZONS:
        groups = predictions[predictions.orizzonte.eq(horizon)]
        mae = groups.assign(error=(groups.punti-groups.y_punti).abs()).groupby('modello').error.mean()
        folds = summary[summary.orizzonte.eq(horizon)].pivot(index='stagione', columns='modello', values='mae_punti')
        passed = bool(len(folds) >= 3 and (folds.combinato < folds.storico).all()
                      and (folds.combinato < folds.recente).all()
                      and mae.combinato < min(mae.storico, mae.recente))
        fallback = min(('storico','recente'), key=lambda key: mae[key])
        selections[horizon] = dict(modello='combinato' if passed else fallback,
                                   combinazione_promossa=passed, mae_punti=mae.to_dict())
    return selections


def interval_radius(predictions, horizon, model, role, target='punti'):
    residuals = predictions[predictions.orizzonte.eq(horizon) & predictions.modello.eq(model)].copy()
    local = residuals[residuals.ruolo.eq(role)]
    pool = local if len(local) >= 30 else residuals
    observed_col = 'y_punti' if target == 'punti' else 'y_n'
    errors = (pool[target]-pool[observed_col]).abs().dropna().sort_values().to_numpy()
    if not len(errors):
        raise RoseError('Residui di calibrazione assenti')
    index = min(len(errors)-1, int(np.ceil(.8*(len(errors)+1)))-1)
    return float(errors[index]), len(errors)


def interval_coverage(predictions):
    last = predictions.stagione.max()
    past = predictions[predictions.stagione.lt(last)]
    rows = []
    for (horizon, model), group in predictions[predictions.stagione.eq(last)].groupby(['orizzonte','modello']):
        for target, label in (('punti','y_punti'), ('presenze','y_n')):
            inside = []
            radii = {role:interval_radius(past,horizon,model,role,target)[0] for role in group.ruolo.unique()}
            for r in group.itertuples():
                radius = radii[r.ruolo]
                inside.append(abs(getattr(r,target)-getattr(r,label)) <= radius)
            rows.append(dict(stagione_test=last, orizzonte=horizon, modello=model, bersaglio=target,
                             n=len(inside), copertura=float(np.mean(inside)), nominale=.8))
    return pd.DataFrame(rows)
