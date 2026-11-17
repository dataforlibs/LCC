#!/usr/bin/env python3
"""
Build all dashboard tables + statistical tests from a raw (lcc_subclass,pub_year) file.

Usage: python3 02_build_tables.py <subclass_raw_records.csv> <meta.csv> <out_dir> [--ref-rankings old_rankings.csv] [--class-raw class_raw_records.csv]
--class-raw adds one residual column per class (status OTHER) holding valid LC subclasses that are outside the
analysis list, so class totals are complete. OTHER columns are NOT used in sigmoid fits or tests.
Outputs (same names/columns the dashboard reads):
  subclass_annual_counts.csv, subclass_cumulative_counts.csv, subclass_sigmoids_v2.csv,
  inflection_comparison_v2.csv, subclass_rankings_over_time.csv,
  all_subclass_tests_data.csv, all_subclass_tests_report.txt
meta.csv columns: code,label,jefferson_status,parent_class,jeff_ch,baconian  (row order = column order)
"""
import sys, os, numpy as np, pandas as pd
from scipy import stats
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lcc_common import *

raw_path, meta_path, out = sys.argv[1], sys.argv[2], sys.argv[3]
rank_years = None
class_raw_path = sys.argv[sys.argv.index('--class-raw')+1] if '--class-raw' in sys.argv else None
if '--ref-rankings' in sys.argv:
    rank_years = sorted(pd.read_csv(sys.argv[sys.argv.index('--ref-rankings')+1], keep_default_na=False, na_values=['']).year.unique())
os.makedirs(out, exist_ok=True)
meta = pd.read_csv(meta_path, keep_default_na=False, na_values=[''])
YEARS = np.arange(1400, 2021)
MIN_TOTAL = 50   # subclasses with fewer records get no sigmoid (2014 run: AN=2, LH=36, VD=38 had none; smallest fitted was 97)

raw = pd.read_csv(raw_path, keep_default_na=False, na_values=[''])
raw = raw[(raw.pub_year >= 1400) & (raw.pub_year <= 2020)]
ann = raw.groupby(['pub_year','lcc_subclass']).size().unstack(fill_value=0).reindex(YEARS, fill_value=0)
ann = ann.reindex(columns=meta.code, fill_value=0)
OTHER = {}
if class_raw_path:
    cr = pd.read_csv(class_raw_path, keep_default_na=False, na_values=['']); cr = cr[(cr.pub_year >= 1400) & (cr.pub_year <= 2020)]
    cann = cr.groupby(['pub_year','main_class']).size().unstack(fill_value=0).reindex(YEARS, fill_value=0)
    listed = ann.T.groupby(meta.set_index('code').parent_class).sum().T
    for L in sorted(cann.columns):
        res = cann[L] - (listed[L] if L in listed.columns else 0)
        assert (res >= 0).all(), f'negative residual in class {L}'
        if res.sum() > 0: OTHER[L] = res
keep = (ann.sum(axis=1) > 0) | (pd.concat(OTHER, axis=1).sum(axis=1) > 0 if OTHER else False)
ann = ann[keep]; YEARS = ann.index.values
OTHER = {L: r.loc[YEARS] for L, r in OTHER.items()}
cum = ann.cumsum()
# output matrices = listed subclasses + residual column at the end of each class group
meta_out = meta.assign(code_out=meta.code, label_out=meta.label, status_out=meta.jefferson_status, cls_out=meta.parent_class)
ann_out, cols_out = ann.copy(), list(meta.code)
for L, r in OTHER.items():
    code = f'{L}-other'; ann_out[code] = r.values
    pos = max([i for i, c in enumerate(cols_out) if meta.set_index('code').parent_class.get(c) == L], default=len(cols_out)-1) + 1
    cols_out.insert(pos, code)
ann_out = ann_out[cols_out]; cum_out = ann_out.cumsum()
full = {r.code: f"{r.code} -- {r.label} [{r.jefferson_status}]" for r in meta.itertuples()}
for L in OTHER: full[f'{L}-other'] = f'{L}-other -- Other {L} subclasses outside the 204 analysed (e.g. unlisted LC subclasses) [OTHER]'
A = ann_out.rename(columns=full); A.index.name='pub_year'; A.to_csv(f'{out}/subclass_annual_counts.csv')
C = cum_out.rename(columns=full); C.index.name='pub_year'; C.to_csv(f'{out}/subclass_cumulative_counts.csv')

# ---- sigmoids
rows=[]
for r in meta.itertuples():
    c = cum[r.code].values; f = fit_sigmoid(YEARS, c)
    ok = (c[-1] >= MIN_TOTAL) and (not np.isnan(f['t0'])) and f['k'] < 1.0   # tiny/degenerate fits are not reported
    t0 = f['t0'] if ok else np.nan
    ev = min(EVENTS, key=lambda e: abs(e[0]-t0)) if ok else (np.nan, np.nan)
    nz = ann[r.code].values > 0
    rows.append(dict(subclass=r.code,label=r.label,jefferson_status=r.jefferson_status,group=f'{r.parent_class}-Class',
        first_year=int(YEARS[nz][0]) if nz.any() else np.nan, total=int(c[-1]), nonzero_years=int(nz.sum()),
        inflection_year=round(t0,1) if ok else np.nan, growth_rate_k=round(f['k'],6) if ok else np.nan,
        growth_width_yrs=round(np.log(81)/f['k'],1) if ok else np.nan, sigmoid_r2=round(f['r2'],4) if ok else np.nan,
        c_norm_at_t0=0.5 if ok else np.nan, nearest_event_yr=ev[0], nearest_event_dist=abs(ev[0]-t0) if ok else np.nan,
        nearest_event_desc=ev[1], reliable=bool(ok and f['r2']>=0.85)))
S = pd.DataFrame(rows); S.to_csv(f'{out}/subclass_sigmoids_v2.csv', index=False)

# ---- tests data
T = meta.copy(); T['v1815']=[cum.loc[1815,c] for c in T.code]; T['v2020']=[cum.loc[2020,c] for c in T.code]
T['raw_gf']=np.where(T.v1815>0, T.v2020/T.v1815.replace(0,np.nan), np.nan); T['log_gf']=np.log10(T.raw_gf)
T['absent_by_1815']=T.v1815==0
T['inflection_year']=S.inflection_year.values; T['sigmoid_r2']=S.sigmoid_r2.values; T['reliable']=S.reliable.values
T.to_csv(f'{out}/all_subclass_tests_data.csv', index=False)

# ---- Test D / E / 5b / 1 / 2
rel = T[T.reliable]
ab = rel[rel.jefferson_status=='ABSENT'].inflection_year
clsA = rel[rel.jefferson_status.isin(['MERGED','DIRECT'])].inflection_year
clsB = rel[rel.jefferson_status.isin(['MERGED','DIRECT','RENAMED'])].inflection_year
def mw(x,y):
    u,p = stats.mannwhitneyu(x,y,alternative='two-sided'); return u,p,1-2*u/(len(x)*len(y))
uB,pB,rB = mw(ab,clsB); uA,pA,rA = mw(ab,clsA)
# P-class sub-test: general P excluded, as in the 2014 run
Pc = rel[(rel.parent_class=='P') & (rel.code!='P')]; pw = Pc[Pc.jefferson_status!='ABSENT'].inflection_year; pn = Pc[Pc.jefferson_status=='ABSENT'].inflection_year
uP,pP,rP = mw(pn,pw); pP = pP/2   # one-sided (absent later), as in the 2014 run
pd.DataFrame([dict(mean_absent=round(ab.mean(),1),mean_classified=round(clsB.mean(),1),median_absent=round(ab.median(),1),
  median_classified=round(clsB.median(),1),std_absent=round(ab.std(),1),std_classified=round(clsB.std(),1),
  gap_years=round(ab.mean()-clsB.mean(),1),mann_whitney_U=uB,p_value=round(pB,4),effect_r=round(rB,3),
  n_absent=len(ab),n_classified=len(clsB),p_class_gap=round(pn.mean()-pw.mean(),1),p_class_p=round(pP,4))]
 ).to_csv(f'{out}/inflection_comparison_v2.csv', index=False)

jef = T[(T.jefferson_status.isin(['MERGED','DIRECT'])) & (T.v1815>0)]
r5,p5 = stats.spearmanr(jef.jeff_ch, jef.log_gf)
g1 = T[T.v1815>=50]; grp = [g1[g1.baconian==b].raw_gf for b in ['Memory','Reason','Imagination']]
h1,p1 = stats.kruskal(*grp)
g2 = rel; grp2=[g2[g2.baconian==b].inflection_year for b in ['Memory','Reason','Imagination']]
h2,p2 = stats.kruskal(*grp2)
L=[]; w=L.append
w('ALL-SUBCLASS TESTS REPORT (regenerated)'); w('='*70)
w(f'  Total subclasses: {len(T)}   v1815=0: {(T.v1815==0).sum()}   reliable fits: {len(rel)}')
w(f'  Total records: {int(cum.iloc[-1].sum()):,}'); w('  Status: '+', '.join(f'{k} {v}' for k,v in T.jefferson_status.value_counts().items()))
w(f'\nTEST 1 Baconian vs growth factor (v1815>=50, n={len(g1)}): KW H={h1:.3f} p={p1:.4f}')
for b,g in zip(['Memory','Reason','Imagination'],grp): w(f'   {b:12s} n={len(g)} mean={g.mean():.0f}x median={g.median():.0f}x')
w(f'\nTEST 2 Baconian vs inflection year (n={len(g2)}): KW H={h2:.3f} p={p2:.4f}')
for b,g in zip(['Memory','Reason','Imagination'],grp2): w(f'   {b:12s} n={len(g)} mean={g.mean():.1f} median={g.median():.1f}')
w(f'\nTEST 5b Spearman jeff_ch vs log growth (Jeffersonian, v1815>0, n={len(jef)}): rho={r5:.3f} p={p5:.4f}')
w(f'\nTEST D ABSENT vs classified inflection timing')
w(f'  ABSENT n={len(ab)} mean={ab.mean():.1f} median={ab.median():.1f}')
w(f'  Version A (RENAMED excl.) n={len(clsA)} mean={clsA.mean():.1f} gap={ab.mean()-clsA.mean():+.1f}y MW U={uA:.1f} p={pA:.4f} r={rA:.3f}')
w(f'  Version B (RENAMED incl.) n={len(clsB)} mean={clsB.mean():.1f} gap={ab.mean()-clsB.mean():+.1f}y MW U={uB:.1f} p={pB:.4f} r={rB:.3f}')
w(f'\nTEST E P-class: classified n={len(pw)} mean={pw.mean():.1f}; absent n={len(pn)} mean={pn.mean():.1f}; gap={pn.mean()-pw.mean():+.1f}y MW U={uP:.1f} p={pP:.4f}')
open(f'{out}/all_subclass_tests_report.txt','w').write('\n'.join(L)+'\n'); print('\n'.join(L))

# ---- rankings
if rank_years is None: rank_years=[1480,1550,1600,1650,1700,1750,1800,1815,1850,1897,1920,1950,1970,1990,2011,2020]
cum_all = cum.reindex(np.arange(1400,2021)).ffill().fillna(0); cum_out_all = cum_out.reindex(np.arange(1400,2021)).ffill().fillna(0)
rr=[]
for y in rank_years:
    v = cum_all.loc[int(y)]; rk = v.where(v>0).rank(ascending=False, method='min')
    for r in meta.itertuples():
        rr.append(dict(subclass=r.code,label=r.label,status=r.jefferson_status,main_class=r.parent_class,year=int(y),rank=rk[r.code],cumulative=int(v[r.code])))
    for L in OTHER:
        rr.append(dict(subclass=f'{L}-other',label=f'Other {L} subclasses (outside list)',status='OTHER',main_class=L,year=int(y),rank=np.nan,cumulative=int(cum_out_all.loc[int(y),f'{L}-other'])))
pd.DataFrame(rr).to_csv(f'{out}/subclass_rankings_over_time.csv', index=False)
