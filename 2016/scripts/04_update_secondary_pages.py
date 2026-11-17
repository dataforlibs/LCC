#!/usr/bin/env python3
"""
Update the four secondary LCC pages from the new tables.
Usage: python3 04_update_secondary_pages.py <old_pages_dir> <tables_dir> <out_dir>
  jefferson_lcc_alluvial.html, lcc_bubble_animation_2.html, lcc_cumulative_share_v2.html, lcc_cumulative_jefferson_split.html
E and F are added as MERGED under Jefferson 'Ch.4 American' (provisional).
Class nodes in the alluvial sum the analysed subclasses only (the X-other columns are not shown).
"""
import sys, re, json, os, numpy as np, pandas as pd
old, tdir, out = sys.argv[1:4]
os.makedirs(out, exist_ok=True)
rd = lambda f: open(f'{old}/{f}', encoding='utf-8').read()
def rep(s, a, b):
    assert a in s, f'missing: {a[:70]}'; return s.replace(a, b)
ann = pd.read_csv(f'{tdir}/subclass_annual_counts.csv', index_col=0, keep_default_na=False, na_values=[''])
cum = pd.read_csv(f'{tdir}/subclass_cumulative_counts.csv', index_col=0, keep_default_na=False, na_values=['']).reindex(np.arange(1400, 2021)).ffill().fillna(0)
code = lambda c: c.split(' -- ')[0]
status = lambda c: re.search(r'\[(\w+)\]$', c).group(1)
listed = [c for c in ann.columns if status(c) != 'OTHER']
n_sub = len(listed)

# ---------- decade pages
def decade(df):
    return df.sum(axis=1).groupby(np.minimum(df.index.values // 10 * 10, 2010)).sum()
decs = list(range(1400, 2011, 10))
d_all = decade(ann).reindex(decs, fill_value=0)
jf = decade(ann[[c for c in listed if status(c) in ('MERGED', 'DIRECT', 'RENAMED')]]).reindex(decs, fill_value=0)
ab = decade(ann[[c for c in listed if status(c) == 'ABSENT']]).reindex(decs, fill_value=0)
tot = d_all.sum(); pct = lambda s: s / s.sum() * 100
yr_tot = ann.sum(axis=1); cm = yr_tot.cumsum() / yr_tot.sum()
after50 = int(cm[cm < 0.5].index[-1]); after80 = int(cm[cm < 0.2].index[-1])
pre60 = d_all[d_all.index < 1960].sum() / tot * 100
top = {d: pct(d_all)[d] for d in (2000, 1990, 1980)}

s = rd('lcc_cumulative_share_v2.html')
s = re.sub(r'const counts=\[.*?\];', 'const counts=' + json.dumps([int(x) for x in d_all.values]) + ';', s, count=1)
s = rep(s, '50% of catalog published after 1985, 80% after 1975.', f'50% of catalog published after {after50}, 80% after {after80}.')
s = rep(s, '50% of catalog published after 1985.', f'50% of catalog published after {after50}.')
s = rep(s, "2000s = 22%, 1990s = 20%, 1980s = 18%. Everything before 1960 combined = 12.6%.", f"2000s = {top[2000]:.0f}%, 1990s = {top[1990]:.0f}%, 1980s = {top[1980]:.0f}%. Everything before 1960 combined = {pre60:.1f}%.")
s = rep(s, 'The 2000s alone account for 22% of the entire catalog.', f'The 2000s alone account for {top[2000]:.0f}% of the entire catalog.')
s = rep(s, 'Before 1960 — 12.6% of catalog', f'Before 1960 — {pre60:.1f}% of catalog'); s = rep(s, '1960 onward — 87.4% of catalog', f'1960 onward — {100-pre60:.1f}% of catalog')
s = rep(s, 'Publication decade distribution of the LC catalog · 1400–2020', f'Publication decade distribution of the LC catalog · 1400–2020 · LC MARC 2016 files, {int(tot):,} records with a valid LC class')
open(f'{out}/lcc_cumulative_share_v2.html', 'w', encoding='utf-8').write(s)

s = rd('lcc_cumulative_jefferson_split.html')
s = re.sub(r'const jeff=\[.*?\];', 'const jeff=' + json.dumps([int(x) for x in jf.values]) + ';', s, count=1)
s = re.sub(r'const absent=\[.*?\];', 'const absent=' + json.dumps([int(x) for x in ab.values]) + ';', s, count=1)
s = rep(s, 'split by Jefferson classification status · 1400–2020', f'split by Jefferson classification status · 1400–2020 · LC MARC 2016 files, {int(jf.sum()+ab.sum()):,} records in the {n_sub} analysed subclasses (unlisted LC subclasses have no status and are excluded)')
open(f'{out}/lcc_cumulative_jefferson_split.html', 'w', encoding='utf-8').write(s)

# ---------- bubble animation
s = rd('lcc_bubble_animation_2.html')
years = json.loads(re.search(r'const years=(\[.*?\]);', s).group(1))
olddata = json.loads(re.search(r'const data=(\[.*?\]);\n', s, re.S).group(1))
meta = pd.read_csv(f'{tdir}/all_subclass_tests_data.csv', keep_default_na=False, na_values=['']).set_index('code')
newdata = []
for c in listed:
    k = code(c); m = meta.loc[k]
    newdata.append({'code': k, 'label': m.label, 'status': m.jefferson_status, 'baconian': m.baconian,
                    'counts': {str(y): int(cum.loc[y, c]) for y in years}})
s = re.sub(r'const data=\[.*?\];\n', lambda m: 'const data=' + json.dumps(newdata, ensure_ascii=False, separators=(',', ':')) + ';\n', s, count=1, flags=re.S)
s = rep(s, '<p>202 subclasses grouped', f'<p>{n_sub} subclasses grouped')
s = rep(s, 'hover for details</p>', 'hover for details · LC MARC 2016 files</p>')
open(f'{out}/lcc_bubble_animation_2.html', 'w', encoding='utf-8').write(s)

# ---------- alluvial
s = rd('jefferson_lcc_alluvial.html')
i = s.index('const records = ['); j = s.index('];', i)
recs = json.loads(s[i + len('const records = '):j + 1])
byc = {r['subclass']: r for r in recs}
for k in ('E', 'F'):
    m = meta.loc[k]
    byc[k] = {'source': 'Ch.4 American', 'chapter': '4', 'main': 'E', 'mainLabel': 'E/F — History of the Americas', 'subclass': k,
              'label': m.label, 'status': 'MERGED', 'count2020': 0, 'baconian': 'Memory'}
order = [r['subclass'] for r in recs]
order.insert(order.index('E18'), 'E'); order.insert(order.index('E99') + 1, 'F')
# v2: every valid LC subclass is analysed; subclasses missing from the 2014 alluvial get a Jefferson chapter here (provisional)
CH = {'NA': ('Ch.30–31 Architecture & Arts', '30'), 'BQ': ('Ch.17 Religion', '17'),
      'J': ('Ch.24 Politics & Commerce', '24'), 'JA': ('Ch.24 Politics & Commerce', '24'),
      'JF': ('Ch.24 Politics & Commerce', '24'), 'JJ': ('Ch.24 Politics & Commerce', '24'),
      'KA': ('Ch.18–23 Law', '18'), 'KK': ('Ch.18–23 Law', '18')}
mainlab = {r['main']: r['mainLabel'] for r in recs}
for k in sorted(c for c in (code(x) for x in listed) if c not in byc):
    m = meta.loc[k]; main = m.parent_class
    src, ch = CH.get(k, ('Not in Jefferson', ''))
    byc[k] = {'source': src, 'chapter': ch, 'main': main, 'mainLabel': mainlab.get(main, main), 'subclass': k, 'label': m.label,
              'status': m.jefferson_status, 'count2020': 0, 'baconian': m.baconian}
    idx = max(i for i, o in enumerate(order) if byc[o]['main'] == main) + 1
    order.insert(idx, k)
new = []
for k in order:
    r = dict(byc[k]); ccol = next(c for c in listed if code(c) == k); r['count2020'] = int(cum.loc[2020, ccol])
    r['label'] = meta.loc[k].label if k in ('E', 'F') or k not in {x['subclass'] for x in recs} else r['label']
    new.append(r)
assert len(new) == n_sub
body = ',\n'.join('  ' + json.dumps(r, ensure_ascii=True) for r in new)
s = s[:i] + 'const records = [\n' + body + '\n' + s[j:]
s = rep(s, '→ 202 subclasses. Flows weighted by 2020 cumulative record counts.', f'→ {n_sub} subclasses. Flows weighted by 2020 cumulative record counts (LC MARC 2016 files; E and F now included under Jefferson Ch.4 American).')
s = rep(s, 'min="20" max="202" value="100"', f'min="20" max="{n_sub}" value="100"')
open(f'{out}/lcc_bubble_dummy', 'w').close(); os.remove(f'{out}/lcc_bubble_dummy')
open(f'{out}/jefferson_lcc_alluvial.html', 'w', encoding='utf-8').write(s)
print('ok', n_sub, after50, after80, round(pre60, 1), {k: int(v.sum()) for k, v in (('jeff', jf), ('absent', ab))})
