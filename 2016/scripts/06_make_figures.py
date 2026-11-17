#!/usr/bin/env python3
"""
Regenerate the three figures and the decade-growth page from the 2016 tables.
Usage: python3 06_make_figures.py <tables_dir> <out_dir> [sens_dir]
Writes: subclass_lifepaths.png, fig_subclass_lifepaths_normalized.png, fig_inflection_distribution.png, lcc_catalog_growth_by_decade.html
Needs subclass_cumulative_counts.csv, subclass_annual_counts.csv, subclass_sigmoids_v2.csv, inflection_comparison_v2.csv in <tables_dir>.
"""
import sys, os, re, numpy as np, pandas as pd
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from scipy.stats import gaussian_kde
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lcc_common import logistic
T, OUT = sys.argv[1], sys.argv[2]; os.makedirs(OUT, exist_ok=True)
import json
SJ = json.load(open(os.path.join(sys.argv[3], 'sensitivity_cutoff.json')))['2011'] if len(sys.argv) > 3 else None
rd = lambda f, **k: pd.read_csv(f'{T}/{f}', keep_default_na=False, na_values=[''], **k)
cum = rd('subclass_cumulative_counts.csv', index_col=0).reindex(np.arange(1400, 2021)).ffill().fillna(0)
ann = rd('subclass_annual_counts.csv', index_col=0)
sig = rd('subclass_sigmoids_v2.csv').set_index('subclass')
inf = rd('inflection_comparison_v2.csv').iloc[0]
code = lambda c: c.split(' -- ')[0]
col = {code(c): c for c in cum.columns}
years = cum.index.values
CLS_C, ABS_C = '#1f4fd8', '#c4421a'
NAMES = {'PA':'Classical Languages','PE':'English Language','PR':'English Literature','PS':'American Literature','PN':'General Literature',
         'PG':'Slavic Languages & L','PJ':'Oriental Languages','PL':'E Asian / African La','PM':'Indigenous American',
         'HF':'Commerce','HA':'Statistics','HM':'Sociology','HQ':'Gender / Sexuality','HT':'Communities / Race','HV':'Social Pathology','HX':'Socialism / Communis'}
is_cls = lambda k: sig.loc[k, 'jefferson_status'] != 'ABSENT'
N = int(cum.iloc[-1].sum())
_a = rd('subclass_annual_counts.csv', index_col=0).sum(axis=1)
NOTE = (f"Data limitation: publication years after 2011 are incomplete in the 2016 MARC file (records per year fall from {int(_a.loc[2011]):,} in 2011 to {int(_a.loc[2016]):,} in 2016). "
        "Totals, fitted sigmoids and inflection years use these years." + (f" Refit on 1400–2011: Jeffersonian vs absent gap {SJ['gap']:+.1f} y, p={SJ['p_B']:.4f}; inflection years shift {abs(SJ['shift_median']):.1f} y earlier." if SJ else ''))
def foot(fig, y=.005): fig.text(.5, y, NOTE, ha='center', fontsize=8.5, color='#8a3a1a', wrap=True)
def shade(ax): ax.axvspan(2012, ax.get_xlim()[1] if ax.get_xlim()[1] > 2012 else 2020, color='#c4421a', alpha=.08, lw=0); ax.text(2012.5, ax.get_ylim()[1]*.97, 'incomplete\nin 2016 file', fontsize=7, color='#8a3a1a', va='top')

def vlines(ax, ymax=None):
    for y, lab, c in ((1897, '1897 LCC', '#c0504d'), (1958, '1958 NDEA', '#1f1f8f')):
        ax.axvline(y, color=c, ls=':', lw=1, alpha=.7)
        ax.text(y + 1, ax.get_ylim()[1] * 0.06, lab, rotation=90, fontsize=7.5, color=c, va='bottom')

# ---- Figure 1: absolute lifepaths
def panel1(ax, codes, title):
    m = years >= 1850
    pal_c = plt.cm.winter(np.linspace(0.05, 0.75, max(1, sum(is_cls(k) for k in codes)))); ci = 0
    pal_a = ['#c4421a', '#d06a10', '#a020f0', '#c01a60', '#7a2fe0', '#b8400a']; ai = 0
    for k in codes:
        y = cum[col[k]].values; tot = y[-1]
        if is_cls(k): c, ls = pal_c[ci], '-'; ci += 1
        else: c, ls = pal_a[ai % len(pal_a)], '--'; ai += 1
        ax.plot(years[m], y[m], color=c, ls=ls, lw=2, label=f"{k}: {NAMES.get(k, sig.loc[k,'label'])} [{'classified' if is_cls(k) else 'absent'}]")
        s = sig.loc[k]
        if s.reliable: ax.plot(years[m], tot * logistic(years[m], s.growth_rate_k, s.inflection_year), color=c, ls=':', lw=1, alpha=.7)
    ax.set_xlim(1850, 2020); ax.set_title(title, fontsize=11); ax.set_xlabel('Publication year'); ax.set_ylabel('Cumulative record count')
    ax.grid(alpha=.3); ax.legend(fontsize=7.5, loc='upper left'); vlines(ax); shade(ax)
fig, axs = plt.subplots(1, 2, figsize=(20, 7.3))
panel1(axs[0], ['PA', 'PE', 'PR', 'PS', 'PN', 'PG', 'PJ', 'PL', 'PM'], 'P class: Western vs Non-Western')
panel1(axs[1], ['HF', 'HA', 'HM', 'HQ', 'HT', 'HV', 'HX'], 'H class: Classic vs Modern Social Science')
fig.suptitle("LCC Subclass Growth: Jefferson-classified vs. Absent\nLC MARC 2016 files · dotted = fitted logistic", fontsize=14, fontweight='bold')
foot(fig); fig.tight_layout(rect=[0, .03, 1, .93]); fig.savefig(f'{OUT}/subclass_lifepaths.png', dpi=120); plt.close(fig)

# ---- Figure 2: normalised
def panel2(ax, codes, title, note=None):
    m = years >= 1850; first = {True: True, False: True}
    for k in codes:
        y = cum[col[k]].values; y = y / y[-1] * 100; c = is_cls(k)
        ax.plot(years[m], y[m], color=('#1f4fd8' if title.startswith('P') else '#2a8a50') if c else (ABS_C if title.startswith('P') else '#7b3fe4'),
                ls='-' if c else '--', lw=2.2 if c else 1.6, alpha=.85)
    ax.axvline(1897, color='#c0504d', ls='--', lw=1, alpha=.7); ax.text(1898, 85, '1897 LCC', rotation=90, fontsize=7, color='#c0504d')
    ax.axvline(1968, color='gray', ls='--', lw=1, alpha=.7); ax.text(1969, 85, '1968 MARC', rotation=90, fontsize=7, color='gray')
    cc = ('#1f4fd8', ABS_C) if title.startswith('P') else ('#2a8a50', '#7b3fe4')
    ax.plot([], [], color=cc[0], lw=2.2, label='Jefferson-classified (MERGED)'); ax.plot([], [], color=cc[1], ls='--', lw=1.6, label='Absent from Jefferson (ABSENT)')
    ax.set_xlim(1850, 2022); ax.set_ylim(-2, 108); ax.axvspan(2012, 2022, color='#c4421a', alpha=.08, lw=0); ax.text(2012.5, 106, 'incomplete\nin 2016 file', fontsize=7, color='#8a3a1a', va='top'); ax.yaxis.set_major_formatter(lambda v, _: f'{v:.0f}%'); ax.grid(alpha=.2)
    ax.set_title(title, fontsize=11, fontweight='bold'); ax.set_xlabel('Publication year'); ax.set_ylabel('% of 2020 cumulative total'); ax.legend(loc='upper left', fontsize=8)
    for s in ('top', 'right'): ax.spines[s].set_visible(False)
    if note: ax.text(.02, .04, note, transform=ax.transAxes, fontsize=8.5, style='italic', bbox=dict(boxstyle='round', fc='#eefbee', ec='#2a8a50'))
Pc = [k for k in sig.index if re.fullmatch(r'P[A-T]', k) and k in col]; Hc = [k for k in sig.index if re.fullmatch(r'H[A-Z]', k) and k in col]
fig, axs = plt.subplots(1, 2, figsize=(20, 8.2))
panel2(axs[0], Pc, 'P class: Western vs Non-Western\n(normalized)')
panel2(axs[1], Hc, 'H class: Classic vs Modern Social Science\n(normalized)',
       note='HF/HJ (classified) vs the absent H subclasses:\nsee Test D for the timing comparison.')
fig.suptitle('LCC Subclass Growth: Jefferson-classified vs. Absent\n(Normalized to % of 2020 maximum — shows timing, not scale) · LC MARC 2016 files', fontsize=14, fontweight='bold')
fig.text(.5, .01, 'Solid = Jefferson-classified · Dashed = absent from Jefferson\nNormalization removes scale differences and isolates growth timing.', ha='center', fontsize=9, style='italic', color='#555')
foot(fig, .045); fig.tight_layout(rect=[0, .08, 1, .93]); fig.savefig(f'{OUT}/fig_subclass_lifepaths_normalized.png', dpi=120); plt.close(fig)

# ---- Figure 3: inflection distribution
r = sig[sig.reliable == True]; A = r[r.jefferson_status == 'ABSENT']; C = r[r.jefferson_status != 'ABSENT']
fig, axs = plt.subplots(1, 2, figsize=(20, 7.9)); rng = np.random.default_rng(1)
ax = axs[0]; ax.axvspan(1968, 1995, color='#fff8dc', alpha=.7)
for d, y0, c, lab in ((A, 1, '#d07a4a', 'Absent from Jefferson'), (C, 0, '#6f8fe0', 'Jefferson-classified')):
    ax.scatter(d.inflection_year, y0 + rng.uniform(-.32, .32, len(d)), s=np.sqrt(d.total.astype(float)) / 4, color=c, alpha=.75, label=lab, edgecolor='none')
ax.axvline(A.inflection_year.mean(), color=ABS_C, ls='--', lw=3, label=f'Absent mean: {A.inflection_year.mean():.0f}')
ax.axvline(C.inflection_year.mean(), color=CLS_C, ls='--', lw=3, label=f'Classified mean: {C.inflection_year.mean():.0f}')
ax.set_yticks([0, 1]); ax.set_yticklabels(['Jefferson-classified', 'Absent from Jefferson'], fontsize=11); ax.set_xlim(1960, 2020); ax.set_ylim(-.7, 1.7)
ax.set_xlabel('Inflection year t₀ (year each subclass reached 50% of 2020 total)'); ax.set_title('Inflection year distribution\n(bubble size ∝ record count)'); ax.legend(loc='upper left', fontsize=9, framealpha=.9)
for s in ('top', 'right'): ax.spines[s].set_visible(False)
ax = axs[1]; xs = np.linspace(1960, 2020, 400); sc = 0.9
for d, base, c, fc, lab in ((A, 1.1, ABS_C, '#e8bfae', f'Absent (n={len(A)})'), (C, 0, CLS_C, '#b3c4f2', f'Classified (n={len(C)})')):
    ky = gaussian_kde(d.inflection_year.astype(float))(xs); ky = ky / ky.max() * sc
    ax.fill_between(xs, base, base + ky, color=fc, alpha=.9); ax.plot(xs, base + ky, color=c, lw=2, label=lab)
ax.axvline(A.inflection_year.mean(), color=ABS_C, ls='--', lw=3); ax.axvline(C.inflection_year.mean(), color=CLS_C, ls='--', lw=3)
iq = lambda d: np.percentile(d.inflection_year, [25, 75]); (a1, a2), (c1, c2) = iq(A), iq(C)
ovl = max(a1, c1) < min(a2, c2)
ax.text(.02, .02, f"Gap: {inf.gap_years:.1f} years ({inf.gap_years/2:.1f}% of study period)\nIQR absent {a1:.0f}–{a2:.0f}; classified {c1:.0f}–{c2:.0f}" + ("\nIQRs overlap substantially" if ovl else ''),
        transform=ax.transAxes, fontsize=9, va='bottom', bbox=dict(boxstyle='round', fc='#fbfbe8', ec='#999'))
ax.set_yticks([]); ax.set_xlim(1960, 2020); ax.set_xlabel('Inflection year'); ax.legend(loc='upper left', fontsize=9)
ax.set_title(f'Density (KDE)\nMann-Whitney p={inf.p_value:.4f}, effect r={abs(inf.effect_r):.3f} (small)')
for s in ('top', 'right', 'left'): ax.spines[s].set_visible(False)
fig.suptitle(f'Normalized Sigmoid Inflection Years — Jefferson-classified vs. Absent\n({len(r)} of {len(sig)} LCC subclasses have r²≥0.85 fits, t₀ bounded 1400–2020 · LC MARC 2016 files)', fontsize=14, fontweight='bold')
foot(fig); fig.tight_layout(rect=[0, .03, 1, .92]); fig.savefig(f'{OUT}/fig_inflection_distribution.png', dpi=120); plt.close(fig)

# ---- decade page
dec = ann.sum(axis=1); dec = dec.groupby((dec.index // 10) * 10).sum().reindex(range(1400, 2030, 10), fill_value=0).astype(int)
# standalone page (own <html>, nav bar, Chart.js + annotation plugin loaded in order, then the chart is built)
EVENTS_D = [(1450, 'Gutenberg press', '#E24B4A'), (1620, 'Early colonial print', '#E24B4A'), (1770, 'American Revolution', '#E24B4A'),
            (1810, "Jefferson's sale 1815", '#BA7517'), (1860, 'Civil War era', '#E24B4A'), (1900, 'LC expansion begins', '#E24B4A'),
            (1940, 'GI Bill 1944', '#E24B4A'), (1960, 'NDEA + civil rights + MARC', '#E24B4A'), (1970, 'Area studies boom', '#E24B4A'),
            (1990, 'Digital cataloging', '#E24B4A')]
import json
NAV = ''.join(f'<a href="../{f}">{l}</a>' for f, l in (('index.html', 'Dashboard'), ('jefferson_lcc_alluvial.html', 'Jefferson → LCC alluvial'),
        ('lcc_bubble_animation_2.html', 'Bubble animation'), ('lcc_cumulative_share_v2.html', 'Cumulative share'), ('lcc_cumulative_jefferson_split.html', 'Jefferson split')))
HTML = """<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>LC catalog record growth by decade</title>
<style>
  body { margin:0; background:#fff; color:#1e1c18; font-family:"Libre Baskerville",Georgia,serif; font-size:13px; }
  .site-nav { padding: 8px 32px; background: #f5f3f0; border-bottom: 1px solid #d4d0c8; display: flex; gap: 6px; flex-wrap: wrap; align-items: center; }
  .site-nav a { padding: 5px 14px; font-size: 11px; border-radius: 2px; letter-spacing: 0.05em; text-decoration: none; display: inline-block; line-height: 1.4; background: #4a90c4; color: #fff; }
  .site-nav a:hover { background: #5aa0d4; }
  main { padding: 20px 32px 32px; max-width: 1400px; }
  h1 { font-size: 18px; margin: 0 0 4px; letter-spacing: -.01em; }
  .sub { font-size: 11px; color: #706e68; font-style: italic; margin-bottom: 14px; }
  .legend { display:flex; gap:16px; flex-wrap:wrap; margin-bottom:8px; font-size:12px; color:#706e68; }
  .legend span { display:flex; align-items:center; gap:4px; }
  #err { display:none; color:#c46a4a; font-size:12px; margin-top:8px; }
</style></head>
<body>
<nav class="site-nav">__NAV__</nav>
<main>
<h1>LC catalog record growth by decade, 1400–2020</h1>
<div class="sub">LC MARC 2016 files · __N__ records with a valid LC class and a publication year 1400–2020 · log scale · the 2010s bar covers 2010–2016 only and the 2020s bar holds one record; bars drawn in red include incomplete years</div>
<div class="legend">
  <span><span style="width:10px;height:10px;border-radius:2px;background:#378ADD;display:inline-block"></span>Records per decade</span>
  <span><span style="width:2px;height:10px;background:#E24B4A;display:inline-block"></span>Major event</span>
  <span><span style="width:10px;height:10px;border-radius:2px;background:#c4421a;display:inline-block"></span>Decade / years that include incomplete data (2012+ in the 2016 file)</span>
</div>
<div style="position:relative;width:100%;height:420px"><canvas id="growthChart" role="img" aria-label="Bar chart of LC catalog records per decade 1400–2020 with major events annotated."></canvas></div>
<div style="margin:14px 0 6px;padding:10px 14px;border-left:3px solid #c46a4a;background:#fbf3ee;font-size:11.5px;line-height:1.55">__NOTE__</div>
<h2 style="font-size:14px;margin:18px 0 6px">Records per publication year, 1990–2020</h2>
<div style="position:relative;width:100%;height:300px"><canvas id="yearChart"></canvas></div>
<div id="err">The chart could not load (Chart.js is fetched from cdnjs.cloudflare.com). Check the network connection.</div>
</main>
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/chartjs-plugin-annotation/3.0.1/chartjs-plugin-annotation.min.js"></script>
<script>
(function(){
  if (typeof Chart === 'undefined') { document.getElementById('err').style.display = 'block'; return; }
  try { Chart.register(window['chartjs-plugin-annotation']); } catch (e) { /* annotation plugin missing: bars still draw */ }
  const decades = __DECADES__, counts = __COUNTS__, events = __EVENTS__;
  const annotations = {};
  events.forEach((e, i) => { const idx = decades.indexOf(e.decade); if (idx < 0) return;
    annotations['line_' + e.decade] = { type:'line', xMin:idx, xMax:idx, borderColor:e.color, borderWidth:1.5, borderDash:[4,3],
      label:{ content:e.label, display:true, position:'end', yAdjust: 4 + (i % 3) * 15, font:{size:10, weight:'400'}, color:e.color, backgroundColor:'transparent', padding:0 } }; });
  const yrs = __YEARS__, ycounts = __YCOUNTS__;
  new Chart(document.getElementById('yearChart'), { type:'bar',
    data:{ labels: yrs, datasets:[{ label:'Records', data:ycounts, backgroundColor: yrs.map(y => y >= 2012 ? '#c4421a' : '#378ADD'), borderWidth:0 }] },
    options:{ responsive:true, maintainAspectRatio:false, plugins:{ legend:{display:false}, tooltip:{ callbacks:{ label: c => ' ' + c.parsed.y.toLocaleString() + ' records' + (c.label >= 2012 ? ' (incomplete in the 2016 file)' : '') } } },
      scales:{ x:{ grid:{display:false}, ticks:{ color:'#888780', font:{size:11} } }, y:{ ticks:{ color:'#888780', font:{size:11}, callback: v => v >= 1000 ? (v/1000) + 'K' : v }, grid:{color:'rgba(136,135,128,0.15)'} } } } });
  new Chart(document.getElementById('growthChart'), {
    type:'bar',
    data:{ labels: decades.map(d => d + 's'), datasets:[{ label:'Records', data:counts, backgroundColor: decades.map(d => d >= 2010 ? '#c4421a' : '#378ADD'), borderWidth:0, borderRadius:2 }] },
    options:{ responsive:true, maintainAspectRatio:false,
      plugins:{ legend:{display:false}, tooltip:{ callbacks:{ label: ctx => ' ' + ctx.parsed.y.toLocaleString() + ' records' } }, annotation:{ annotations } },
      scales:{ x:{ ticks:{ autoSkip:true, maxTicksLimit:13, maxRotation:45, font:{size:11}, color:'#888780' }, grid:{display:false} },
               y:{ type:'logarithmic', max:30000000, ticks:{ color:'#888780', font:{size:11},
                   callback: v => [1,10,100,1000,10000,100000,1000000,10000000].includes(v) ? (v >= 1000000 ? (v/1000000)+'M' : v >= 1000 ? (v/1000)+'K' : v) : null },
                   grid:{color:'rgba(136,135,128,0.15)'} } } }
  });
})();
</script>
</body></html>
"""
yr = _a.loc[1990:2020]
page = (HTML.replace('__NOTE__', NOTE).replace('__YEARS__', str(list(map(int, yr.index)))).replace('__YCOUNTS__', str(list(map(int, yr.values)))).replace('__NAV__', NAV).replace('__N__', f'{int(dec.sum()):,}').replace('__DECADES__', str(list(dec.index)))
        .replace('__COUNTS__', str(list(map(int, dec.values)))).replace('__EVENTS__', json.dumps([dict(decade=d, label=l, color=c) for d, l, c in EVENTS_D])))
open(f'{OUT}/lcc_catalog_growth_by_decade.html', 'w', encoding='utf-8').write(page)
print('records', int(dec.sum()), 'A', len(A), 'C', len(C), 'gap', inf.gap_years, 'p', inf.p_value)
