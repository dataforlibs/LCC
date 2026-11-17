#!/usr/bin/env python3
"""
Add the 'recent years are incomplete' note under the navigation bar of all five pages (numbers computed, not typed).
Usage: python3 08_add_data_notes.py <pages_dir> <sens_dir>      (sens_dir = output of 07_sensitivity_cutoff.py)
Run after 05_unify_nav.py. Idempotent.
"""
import sys, os, re, json, pandas as pd
pages, sens = sys.argv[1], sys.argv[2]
ann = pd.read_csv(os.path.join(pages, 'output', 'subclass_annual_counts.csv'), keep_default_na=False, na_values=[''], index_col=0).sum(axis=1)
J = json.load(open(os.path.join(sens, 'sensitivity_cutoff.json')))
pk = int(ann.loc[2000:2016].idxmax()); f = lambda y: f'{int(ann.loc[y]):,}'
late = int(ann.loc[2017:].sum())
a, b = J['2011'], J['2008']
html = f'''<!-- data-note -->
<div class="data-note" style="margin:14px 32px 0;padding:10px 14px;border-left:3px solid #c46a4a;background:#fbf3ee;font-size:11.5px;line-height:1.55;color:#1e1c18;font-family:'Libre Baskerville',Georgia,serif;">
<strong>Data limitation — recent publication years are incomplete in the 2016 file.</strong>
The file is a 2016 snapshot, so it holds only the books catalogued by then. Records per publication year peak at {f(pk)} ({pk}) and are still {f(2010)} (2010) and {f(2011)} (2011),
then fall to {f(2012)} (2012), {f(2013)} (2013), {f(2014)} (2014), {f(2015)} (2015) and {f(2016)} (2016); {late:,} records are dated 2017–2020. The pattern fits cataloguing lag (books published shortly before the snapshot not yet catalogued) rather than a fall in publishing; I have not checked it against outside publication counts. Nothing here has been removed or corrected.
<strong>It affects the results:</strong> every 2020 total, sigmoid fit and inflection year is computed with these incomplete years.
Refitting on 1400–2011 moves the inflection years earlier by a median of {abs(a['shift_median']):.1f} years ({abs(b['shift_median']):.1f} years for a 2008 cutoff), so absolute inflection years depend on the cutoff.
The Jeffersonian vs non-Jeffersonian comparison keeps its direction and significance: gap {a['gap']:+.1f} years (Mann-Whitney p={a['p_B']:.4f}) with the 2011 cutoff, {b['gap']:+.1f} years (p={b['p_B']:.4f}) with 2008, against +1.6 years (p=0.0039) using all years;
median growth {a['med_J']:.0f}× (Jeffersonian) vs {a['med_A']:.0f}× (non-Jeffersonian) with the 2011 cutoff. Details: <code>output/sensitivity_cutoff_report.txt</code>.
</div>
<!-- /data-note -->'''
for fn in ('index.html', 'jefferson_lcc_alluvial.html', 'lcc_bubble_animation_2.html', 'lcc_cumulative_share_v2.html', 'lcc_cumulative_jefferson_split.html'):
    p = os.path.join(pages, fn); s = open(p, encoding='utf-8').read()
    s = re.sub(r'\s*<!-- data-note -->.*?<!-- /data-note -->', '', s, flags=re.S)
    s = s.replace('</nav>', '</nav>\n' + html, 1)
    open(p, 'w', encoding='utf-8').write(s); print(fn, 'ok')
