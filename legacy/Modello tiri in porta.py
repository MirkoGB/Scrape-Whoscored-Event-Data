import numpy as np, pandas as pd
from scipy.optimize import minimize
from scipy.stats import nbinom
import warnings; warnings.filterwarnings('ignore')

# ---------- 1. Dati in formato lungo (una riga per squadra-partita) ----------
def load(fn, season):
    d = pd.read_csv(fn)
    d['Date'] = pd.to_datetime(d['Date'])
    d = d.dropna(subset=['HST', 'AST'])
    rows = []
    for _, r in d.iterrows():
        rows.append(dict(date=r.Date, season=season, team=r.HomeTeam, opp=r.AwayTeam, home=1, sot=r.HST))
        rows.append(dict(date=r.Date, season=season, team=r.AwayTeam, opp=r.HomeTeam, home=0, sot=r.AST))
    return pd.DataFrame(rows)

L = pd.concat([load('sa_2425.csv', '24-25'), load('sa_2526.csv', '25-26')], ignore_index=True)
L['sot'] = L['sot'].astype(int)
TEAMS = sorted(set(L.team) | set(L.opp))
IDX = {t: i for i, t in enumerate(TEAMS)}
NT = len(TEAMS)

# ---------- 2. Poisson ridge-penalizzato con pesi di decadimento temporale ----------
# log(lambda) = mu + att[team] + def[opp] + gamma*home
def fit(df, w, alpha):
    ti = df.team.map(IDX).values
    oi = df.opp.map(IDX).values
    h = df.home.values.astype(float)
    y = df.sot.values.astype(float)

    def nll(th):
        mu, gam = th[0], th[1]
        att, dfn = th[2:2 + NT], th[2 + NT:2 + 2 * NT]
        eta = mu + att[ti] + dfn[oi] + gam * h
        eta = np.clip(eta, -6, 4)
        lam = np.exp(eta)
        ll = np.sum(w * (y * eta - lam))
        pen = alpha * (np.sum(att ** 2) + np.sum(dfn ** 2))
        return -ll + pen

    th0 = np.zeros(2 + 2 * NT); th0[0] = np.log(max(y.mean(), .5))
    res = minimize(nll, th0, method='L-BFGS-B', options=dict(maxiter=3000))
    return res.x

def predict(th, team, opp, home):
    mu, gam = th[0], th[1]
    att, dfn = th[2:2 + NT], th[2 + NT:2 + 2 * NT]
    return float(np.exp(mu + att[IDX[team]] + dfn[IDX[opp]] + gam * home))

HALF_LIFE = 150.0  # giorni

def weights(df, ref_date):
    age = (ref_date - df.date).dt.days.values.astype(float)
    return 0.5 ** (age / HALF_LIFE)

# ---------- 3. Scelta di alpha per validazione temporale ----------
cur = L[L.season == '25-26'].sort_values('date').reset_index(drop=True)
dates = sorted(cur.date.unique())
val_dates = dates[len(dates) // 3:]  # salto l'inizio stagione

def cv_score(alpha):
    tot, n = 0.0, 0
    for d in val_dates[::4]:  # sottocampiono per velocità
        tr = L[L.date < d]
        te = cur[cur.date == d]
        if len(tr) < 100 or len(te) == 0: continue
        th = fit(tr, weights(tr, d), alpha)
        for _, r in te.iterrows():
            lam = predict(th, r.team, r.opp, r.home)
            tot += r.sot * np.log(lam) - lam; n += 1
    return tot / n

print('Taratura penalizzazione (log-verosimiglianza fuori campione):')
best, bs = None, -1e9
for a in [1, 3, 6, 12, 25, 50]:
    s = cv_score(a)
    print(f'  alpha={a:>3}  ->  {s:.4f}')
    if s > bs: bs, best = s, a
print(f'  scelto alpha = {best}\n')

# ---------- 4. Stima pre-partita (walk-forward) per TUTTA la Serie A ----------
recs = []
cache = {}
for d in dates:
    tr = L[L.date < d]
    if len(tr) < 100: continue
    th = fit(tr, weights(tr, d), best)
    cache[d] = th
    for _, r in cur[cur.date == d].iterrows():
        recs.append(dict(date=r.date, team=r.team, opp=r.opp, home=r.home,
                         sot=r.sot, lam_pre=predict(th, r.team, r.opp, r.home)))
W = pd.DataFrame(recs)

# ---------- 5. Dispersione NB2 (Var = lam + lam^2/r) ----------
def fit_r(y, lam):
    def nll(lr):
        r = np.exp(lr[0])
        p = r / (r + lam)
        return -np.sum(nbinom.logpmf(y, r, p))
    return float(np.exp(minimize(nll, [np.log(8.0)], method='Nelder-Mead').x[0]))

R = fit_r(W.sot.values, W.lam_pre.values)
print(f'Parametro di dispersione NB2 stimato: r = {R:.2f}')
print(f'(r alto = quasi-Poisson; r basso = code piu\' grasse)\n')

# ---------- 6. Calibrazione sul campionato intero ----------
LINES = [1.5, 2.5, 3.5, 4.5, 5.5, 6.5, 7.5]
def p_over(lam, line, r=None):
    r = R if r is None else r
    k = int(np.floor(line))  # Over line  <=>  sot >= k+1
    return float(nbinom.sf(k, r, r / (r + lam)))

print('Calibrazione (tutte le 760 squadra-partita di Serie A 25-26, stima pre-partita):')
pr = np.array([p_over(l, 4.5) for l in W.lam_pre])
ac = (W.sot.values >= 5).astype(float)
bins = pd.cut(pr, [0, .2, .3, .4, .5, .6, 1.0])
cal = pd.DataFrame({'p': pr, 'y': ac, 'b': bins}).groupby('b', observed=True).agg(
    n=('y', 'size'), prevista=('p', 'mean'), osservata=('y', 'mean'))
print(cal.round(3).to_string())
print(f'\nBrier score (Over 4.5): {np.mean((pr-ac)**2):.4f}  '
      f'| baseline tasso base: {np.mean((ac.mean()-ac)**2):.4f}')
print(f'MAE su lambda: {np.mean(np.abs(W.lam_pre-W.sot)):.3f} tiri\n')

# ---------- 7. Fit in-sample sulla sola 25-26 (tasso retrospettivo) ----------
th_full = fit(cur, np.ones(len(cur)), best)

# ---------- 8. Tabella Como ----------
MARGIN = 1.07  # overround 7%, tipico dei mercati secondari

# Metodo "power" (Buchdahl): p' = p^(1/k), con k tale che la somma = MARGIN.
# Carica piu' margine sui longshot -> nessuna quota sotto 1.00, come nei book reali.
from scipy.optimize import brentq
def apply_margin(p):
    p = min(max(p, 1e-6), 1 - 1e-6)
    f = lambda k: p ** (1 / k) + (1 - p) ** (1 / k) - MARGIN
    k = brentq(f, 1.0, 6.0)
    return p ** (1 / k), (1 - p) ** (1 / k)
C = W[W.team == 'Como'].sort_values('date').reset_index(drop=True)
out = []
for i, r in C.iterrows():
    lam_post = predict(th_full, r.team, r.opp, r.home)
    row = {
        'Giornata': i + 1,
        'Data': r.date.strftime('%Y-%m-%d'),
        'Avversario': r.opp,
        'C/T': 'Casa' if r.home else 'Trasferta',
        'Lambda_prepartita': round(r.lam_pre, 2),
        'Lambda_retrospettivo': round(lam_post, 2),
        'TiP_reali': int(r.sot),
    }
    ps = {l: p_over(r.lam_pre, l) for l in LINES}
    main = min(LINES, key=lambda l: abs(ps[l] - .5))
    row['Linea_principale'] = main
    for l in LINES:
        p = ps[l]
        po, pu = apply_margin(p)
        row[f'P_Over{l}'] = round(p, 5)
        row[f'Over{l}'] = round(1 / po, 2)
        row[f'Under{l}'] = round(1 / pu, 2)
    row['Esito_linea_principale'] = 'Over' if r.sot > main else 'Under'
    out.append(row)

O = pd.DataFrame(out)
W.to_csv('walkforward_all.csv', index=False)
O.to_csv('como_tip_quote_2526.csv', index=False)

print('=' * 100)
print('COMO — TIRI IN PORTA, SERIE A 2025-26 — QUOTE STIMATE (margine 7%)')
print('=' * 100)
show = O[['Giornata', 'Data', 'Avversario', 'C/T', 'Lambda_prepartita', 'TiP_reali',
          'Linea_principale', 'Over4.5', 'Under4.5']]
print(show.to_string(index=False))

print(f'\nMedia TiP reali Como: {C.sot.mean():.2f} | media lambda pre-partita: {C.lam_pre.mean():.2f}')
print(f'MAE Como: {np.mean(np.abs(C.lam_pre - C.sot)):.2f} tiri')
hit = np.mean([(r.sot > O.Linea_principale[i]) for i, r in C.iterrows()])
print(f'Over sulla linea principale: {hit:.1%} delle partite (atteso ~50%)')