"""Shared helpers: sigmoid fit, event list, metadata."""
import numpy as np, pandas as pd
from scipy.optimize import curve_fit

def logistic(t, k, t0): return 1.0/(1.0+np.exp(-k*(t-t0)))

def fit_sigmoid(years, cum):
    """2-parameter logistic on normalized cumulative counts (asymptote fixed at 1).
    t0 bounded to [1400, 2020]. Returns dict(k, t0, r2)."""
    cum = np.asarray(cum, float); tot = cum[-1]
    if tot <= 0: return dict(k=np.nan, t0=np.nan, r2=np.nan)
    y = cum/tot; t = np.asarray(years, float)
    best=None
    for p0 in [(0.05,1960),(0.02,1900),(0.1,1985),(0.03,1800)]:
        try:
            p,_ = curve_fit(logistic, t, y, p0=p0, bounds=([1e-4,1400],[2.0,2020]), maxfev=20000)
            sse=((y-logistic(t,*p))**2).sum()
            if best is None or sse<best[0]: best=(sse,p)
        except Exception: pass
    if best is None: return dict(k=np.nan,t0=np.nan,r2=np.nan)
    sse,p=best; sst=((y-y.mean())**2).sum()
    return dict(k=p[0], t0=p[1], r2=1-sse/sst if sst>0 else np.nan)

EVENTS = [(1897,'LCC system created'),(1954,'Brown v. Board of Education'),(1964,'Civil Rights Act'),
          (1968,'American Indian Movement / MARC format'),(1972,'Title IX'),
          (1975,'Helsinki Accords (Eastern Europe)'),(1991,'Soviet collapse'),
          (2007,'UN Declaration on Rights of Indigenous Peoples')]
