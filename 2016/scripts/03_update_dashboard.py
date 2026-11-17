#!/usr/bin/env python3
"""
Update the LCC dashboard (index.html) for a new data build.

Usage: python3 03_update_dashboard.py <old_index.html> <tables_dir> <class_raw_records.csv> <extraction_summary.csv> <out_dir>
 * copies the 5 CSVs the dashboard reads into <out_dir>/output/
 * regenerates the hard-coded fallbacks (BUMP_RANKS, RANK_DATA, HK_SUB, R2B_DS)
 * recomputes the numbers quoted in the narrative text from the new tables
 * patches the JS so the OTHER residual columns count toward class totals but not subclass-level views
"""
import sys, os, re, json, shutil, numpy as np, pandas as pd
old_html, tdir, class_raw, summ, out = sys.argv[1:6]
os.makedirs(f'{out}/output', exist_ok=True)
for f in ['subclass_cumulative_counts','subclass_annual_counts','subclass_sigmoids_v2','inflection_comparison_v2','subclass_rankings_over_time']:
    shutil.copy(f'{tdir}/{f}.csv', f'{out}/output/{f}.csv')
for f in ['all_subclass_tests_data.csv','all_subclass_tests_report.txt']: shutil.copy(f'{tdir}/{f}', f'{out}/output/{f}')
s = open(old_html, encoding='utf-8').read()

def const_span(name):
    m = re.search(r'const '+name+r'=(.*?);\n', s, re.S); return m
cum = pd.read_csv(f'{tdir}/subclass_cumulative_counts.csv', index_col=0, keep_default_na=False, na_values=[''])
meta = {c: c.split(' -- ')[0] for c in cum.columns}
cum.columns = [meta[c] for c in cum.columns]
cum = cum.reindex(np.arange(1400, 2021)).ffill().fillna(0)
letter = lambda code: re.sub('[^A-Z]', '', code)[:1]
cls = cum.T.groupby([letter(c) for c in cum.columns]).sum().T           # complete class totals (incl. OTHER columns)
tot = cls.sum(axis=1)
KEYS = json.loads(re.search(r'const KEYS=(\[.*?\]);', s).group(1))
def crank(y):
    v = cls.loc[y, KEYS].sort_values(ascending=False, kind='stable'); return {k: i+1 for i, k in enumerate(v.index)}

# ---- hard-coded fallbacks
yrs = json.loads(re.search(r'const BUMP_YRS=(\[.*?\]);', s).group(1))
BR = [crank(y) for y in yrs]
hkyrs = json.loads(re.search(r'const HK_SUB=(\{.*?\});\n', s, re.S).group(1))['years']
RD = [{'y': y, 'H': crank(y)['H'], 'K': crank(y)['K']} for y in hkyrs]
oldHK = json.loads(re.search(r'const HK_SUB=(\{.*?\});\n', s, re.S).group(1))
sig = pd.read_csv(f'{tdir}/subclass_sigmoids_v2.csv', keep_default_na=False, na_values=['']).set_index('subclass')
hk_codes = [c for c in cum.columns if letter(c) in 'HK' and not c.endswith('-other')]
sub = cum.loc[hkyrs, hk_codes]
ranks = sub.rank(axis=1, ascending=False, method='first').astype(int)
series = []
for c in [x['code'] for x in oldHK['series']]:
    o = next(x for x in oldHK['series'] if x['code'] == c)
    series.append({**o, 'ranks': ranks[c].tolist(), 'final_count': int(cum.loc[2020, c])})
series.sort(key=lambda x: x['ranks'][-1]); HK = {'years': hkyrs, 'series': series}
R2B = json.loads(const_span('R2B_DS').group(1))
for d in R2B: d['ranks'] = ranks[d['code']].tolist()
def sub_const(name, val):
    global s
    m = const_span(name); s = s[:m.start(1)] + json.dumps(val, separators=(',', ':')) + s[m.end(1):]
sub_const('BUMP_RANKS', BR); sub_const('RANK_DATA', RD); sub_const('HK_SUB', HK); sub_const('R2B_DS', R2B)

# ---- narrative numbers
g = lambda k, a, b: cls.loc[b, k] / cls.loc[a, k]
ranksH = {y: crank(y)['H'] for y in (1815, 1970, 2020)}; ranksK = {y: crank(y)['K'] for y in (1815, 1970, 2020)}
post = sorted(((g(k, 1897, 1970), k) for k in KEYS if cls.loc[1897, k] > 0), reverse=True)
NAMES = {'H':'H Social Sciences','S':'S Agriculture','L':'L Education','E':'E American History','F':'F Local History','Z':'Z Bibliography','M':'M Music',
         'V':'V Naval Science','U':'U Military Science','T':'T Technology','Q':'Q Science','R':'R Medicine','N':'N Fine Arts','G':'G Geography','J':'J Political Science',
         'D':'D World History','C':'C Auxiliary Sciences of History','B':'B Philosophy / Religion','A':'A General Works','P':'P Language & Lit','K':'K Law'}
top3 = [k for _, k in post[:3]]
dem = ['H','E','F','J','G']; eli = ['K','P','B']
share = lambda ks, y: cls.loc[y, ks].sum() / tot[y]
inf = pd.read_csv(f'{tdir}/inflection_comparison_v2.csv', keep_default_na=False, na_values=['']).iloc[0]
info = dict(H_rank_1815=ranksH[1815], H_rank_1970=ranksH[1970], K_rank_1815=ranksK[1815], K_rank_2020=ranksK[2020],
            H_growth=g('H',1897,1970), K_growth=g('K',1897,1970), top3=top3, K_rank_pos=[k for _, k in post].index('K')+1, P_rank_pos=[k for _, k in post].index('P')+1,
            dem_1815=share(dem,1815), dem_2020=share(dem,2020), eli_1815=share(eli,1815), eli_2020=share(eli,2020),
            absent_mean=inf.mean_absent, class_mean=inf.mean_classified, gap=inf.gap_years)
print(json.dumps(info, indent=1, default=float))

def rep(a, b, count=1):
    global s
    assert s.count(a) >= 1, f'missing: {a[:60]}'
    s = s.replace(a, b)
rep('H (Social Sciences) rose from rank 10 in 1815 to\n    <span style="color:#4a90c4">rank 2 by 1970</span>.',
    f'H (Social Sciences) rose from rank {ranksH[1815]} in 1815 to\n    <span style="color:#4a90c4">rank {ranksH[1970]} by 1970</span>.')
rep('K (Law — Jefferson\'s dominant class) fell from\n    rank 2 to <span style="color:#c46a4a">rank 6 by 2020</span>.',
    f'K (Law — Jefferson\'s dominant class) went from\n    rank {ranksK[1815]} to <span style="color:#c46a4a">rank {ranksK[2020]} by 2020</span>.')
rep('Post-LCC era (1897–1970): H grew 20× — fastest of all classes. K grew only 4.6×.',
    f'Post-LCC era (1897–1970): H grew {info["H_growth"]:.0f}×; K grew {info["K_growth"]:.1f}×. (Class totals include every valid LC subclass; E and F now counted.)')
rep('<strong>H Social Sciences</strong>, <strong>S Agriculture</strong>, and <strong>L Education</strong>',
    f'<strong>{NAMES[top3[0]]}</strong>, <strong>{NAMES[top3[1]]}</strong>, and <strong>{NAMES[top3[2]]}</strong>')
rep('<strong>doubled</strong> from ~11% (1815) to ~21% (2020), while Jefferson-heavy classes (K Law, P Language &amp; Lit, B Philosophy)\n      <em>fell</em> from ~44% to ~34%.',
    f'<strong>{"doubled" if info["dem_2020"]/info["dem_1815"] >= 1.9 else "rose" if info["dem_2020"] > info["dem_1815"] else "fell"}</strong> from ~{100*info["dem_1815"]:.0f}% (1815) to ~{100*info["dem_2020"]:.0f}% (2020), while Jefferson-heavy classes (K Law, P Language &amp; Lit, B Philosophy)\n      <em>{"fell" if info["eli_2020"] < info["eli_1815"] else "rose"}</em> from ~{100*info["eli_1815"]:.0f}% to ~{100*info["eli_2020"]:.0f}%.')
rep('Non-Jeffersonian mean = 1985, Jeffersonian mean = 1983, gap = 2.3 years — trivially small (1.2% of 200-year study period).',
    f'Non-Jeffersonian mean = {info["absent_mean"]:.0f}, Jeffersonian mean = {info["class_mean"]:.0f}, gap = {info["gap"]:.1f} years — trivially small ({100*info["gap"]/200:.1f}% of 200-year study period).')
n_sub = len([c for c in cum.columns if not c.endswith('-other')])
rep('(202 total)', f'({n_sub} total)'); rep('Math.min(maxRank + 2, 202)', f'Math.min(maxRank + 2, {n_sub})')
sm = pd.read_csv(summ, keep_default_na=False, na_values=['']).set_index('item')['count']
rep('auto-loaded dashboard — data embedded from output</div>',
    f'auto-loaded dashboard — LC MARC 2016 files ({int(sm.records):,} records; {int(sm.class_level_kept):,} with a valid LC class and year 1400–2020; '
    f'{int(sm.kept):,} in the {n_sub} analysed subclasses = every valid LC subclass). Non-LCC call numbers (MLC, MIC, CPB, LAW …) are excluded.</div>')

# ---- JS patches
rep("const hkRows = DATA.rankings.filter(r => r.main_class === 'H' || r.main_class === 'K');",
    "const hkRows = DATA.rankings.filter(r => (r.main_class === 'H' || r.main_class === 'K') && r.status !== 'OTHER');")
i = s.index('function buildJeffersonGrowth'); j = s.index('cols.forEach', i)
s = s[:j] + 'cols.filter(c => c.status !== \'OTHER\').forEach' + s[j+len('cols.forEach'):]
open(f'{out}/index.html', 'w', encoding='utf-8').write(s)
json.dump(info, open(f'{out}/dashboard_numbers.json', 'w'), indent=1, default=float)

# year axes: no thousands separator (1,980 -> 1980). Appended after the main write; re-open the output page.
_p = f'{out}/index.html'; _s = open(_p, encoding='utf-8').read()
_a = "ticks:{color:'#706e68',font:{size:9}}, grid:{color:'rgba(0,0,0,0.06)'} },\n        y: { min:0.4,max:2.6"
_c = "ticks:{color:'#706e68',font:{size:9,family:'Source Code Pro, monospace'},maxTicksLimit:12},\n          grid:{color:'rgba(0,0,0,0.06)'}\n        },\n        y:{\n          type:'linear',\n          min:-maxD*0.26"
if _a in _s and _c in _s:
    _s = _s.replace(_a, _a.replace("font:{size:9}}", "font:{size:9}, callback:v=>String(v)}", 1))
    _s = _s.replace(_c, _c.replace("maxTicksLimit:12}", "maxTicksLimit:12,callback:v=>String(v)}", 1))
    open(_p, 'w', encoding='utf-8').write(_s)

# clearer mean-line labels: they are means of the per-subclass sigmoid inflection years t0
_s = open(_p, encoding='utf-8').read()
for _a, _b in [("label:`Jeff Non-J mean ${jMean.toFixed(0)}`", "label:`Jeffersonian mean t₀ ${jMean.toFixed(0)}`"),
               ("label:`Jeff Non-J mean ${nMean.toFixed(0)}`", "label:`Non-Jeffersonian mean t₀ ${nMean.toFixed(0)}`"),
               ("[['Non-Jeff mean '+Math.round(absMeanX),'#d47c5b',absMeanX],['Jeffersonian mean '+Math.round(mrgMeanX),'#5b9bd5',mrgMeanX]].forEach(([lbl,col,xv])=>{",
                "[['Non-Jeffersonian mean t₀ '+Math.round(absMeanX),'#d47c5b',absMeanX,'left'],['Jeffersonian mean t₀ '+Math.round(mrgMeanX),'#5b9bd5',mrgMeanX,'right']].forEach(([lbl,col,xv,al])=>{"),
               ("ctx.textAlign='center'; ctx.fillText(lbl, x, yS.top+10); ctx.restore();\n      });\n      const showLabels",
                "ctx.textAlign=al; ctx.fillText(lbl, x+(al==='left'?4:-4), yS.top+10); ctx.restore();\n      });\n      const showLabels")]:
    _s = _s.replace(_a, _b)
open(_p, 'w', encoding='utf-8').write(_s)
