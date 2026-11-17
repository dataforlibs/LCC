#!/usr/bin/env python3
"""
Sensitivity check: how much do the main results depend on the incomplete recent years (2012+ in the 2016 file)?
Refits every subclass sigmoid on cumulative counts truncated at END (default 2011, normalised by the END total) and repeats
Test D (Mann-Whitney on inflection year) and the growth comparison (c(END)/c(1815), Welch on log10).
Usage: python3 07_sensitivity_cutoff.py <tables_dir> <out_dir> [END ...]
"""
import sys, os, numpy as np, pandas as pd
from scipy import stats
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lcc_common import fit_sigmoid
T, OUT = sys.argv[1], sys.argv[2]; ENDS = [int(x) for x in sys.argv[3:]] or [2011, 2008]
rd = lambda f, **k: pd.read_csv(f'{T}/{f}', keep_default_na=False, na_values=[''], **k)
cum = rd('subclass_cumulative_counts.csv', index_col=0).reindex(np.arange(1400, 2021)).ffill().fillna(0)
sig = rd('subclass_sigmoids_v2.csv').set_index('subclass')
code = lambda c: c.split(' -- ')[0]
rows = []; out = []; J = {}
def w(s): out.append(s); print(s)
for END in ENDS:
    yrs = np.arange(1400, END + 1); res = {}
    for col in cum.columns:
        k = code(col); y = cum.loc[yrs, col].values
        if y[-1] < 50 or k not in sig.index: continue
        f = fit_sigmoid(yrs, y)
        ok = bool(f['r2'] >= 0.85 and f['k'] < 1) if not np.isnan(f['r2']) else False
        g = y[-1] / cum.loc[1815, col] if cum.loc[1815, col] > 0 else np.nan
        res[k] = dict(t0=f['t0'], k=f['k'], r2=f['r2'], reliable=ok, growth=g, status=sig.loc[k, 'jefferson_status'], t0_full=sig.loc[k, 'inflection_year'])
    R = pd.DataFrame(res).T; R.index.name = 'subclass'
    R.to_csv(f'{OUT}/sensitivity_cutoff_{END}.csv')
    r = R[R.reliable == True]; r = r.assign(t0=r.t0.astype(float), t0_full=r.t0_full.astype(float))
    A = r[r.status == 'ABSENT']; C = r[r.status != 'ABSENT']; C2 = r[r.status.isin(['MERGED', 'DIRECT'])]
    uB = stats.mannwhitneyu(A.t0, C.t0, alternative='two-sided'); uA = stats.mannwhitneyu(A.t0, C2.t0, alternative='two-sided')
    g = R.dropna(subset=['growth']); gJ = np.log10(g[g.status != 'ABSENT'].growth.astype(float)); gA = np.log10(g[g.status == 'ABSENT'].growth.astype(float))
    wt = stats.ttest_ind(gJ, gA, equal_var=False)
    w(f'=== fits on years 1400-{END} (cumulative normalised by the {END} total) ===')
    w(f'  reliable fits: {len(r)} of {len(R)} subclasses with >=50 records; compare {int((sig.reliable==True).sum())} of {len(sig)} on the full 1400-2020 data')
    w(f'  mean t0 absent {A.t0.mean():.1f} (n={len(A)}), classified {C.t0.mean():.1f} (n={len(C)}); gap {A.t0.mean()-C.t0.mean():+.1f} y; MW p={uB.pvalue:.4f} (version B), {uA.pvalue:.4f} (version A, RENAMED excluded)')
    w(f'  full-data reference: gap +1.6 y, p=0.0039 (B), +0.9 y, p=0.0089 (A)')
    w(f'  t0 shift vs full data (same subclasses): median {np.median(r.t0 - r.t0_full):+.1f} y, IQR [{np.percentile(r.t0 - r.t0_full, 25):+.1f}, {np.percentile(r.t0 - r.t0_full, 75):+.1f}]')
    J[END] = dict(n_reliable=len(r), gap=float(A.t0.mean()-C.t0.mean()), p_B=float(uB.pvalue), p_A=float(uA.pvalue), shift_median=float(np.median(r.t0 - r.t0_full)), med_J=float(10**gJ.median()), med_A=float(10**gA.median()), welch_p=float(wt.pvalue))
    w(f'  growth c({END})/c(1815): median Jeffersonian {10**gJ.median():.0f}x (n={len(gJ)}), absent {10**gA.median():.0f}x (n={len(gA)}); Welch t={wt.statistic:.2f}, p={wt.pvalue:.2g}')
import json; json.dump(J, open(f'{OUT}/sensitivity_cutoff.json', 'w'), indent=1)
open(f'{OUT}/sensitivity_cutoff_report.txt', 'w').write('\n'.join(out) + '\n')
