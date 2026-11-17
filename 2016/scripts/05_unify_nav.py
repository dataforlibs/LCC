#!/usr/bin/env python3
"""
Give all five LCC pages the same top navigation bar (same markup, same CSS, current page greyed).
Usage: python3 05_unify_nav.py <pages_dir>
Run last, after 03_update_dashboard.py and 04_update_secondary_pages.py. Safe to re-run.
"""
import re, sys, os
PAGES = [('index.html', 'Dashboard'), ('jefferson_lcc_alluvial.html', 'Jefferson → LCC alluvial'),
         ('lcc_bubble_animation_2.html', 'Bubble animation'), ('lcc_cumulative_share_v2.html', 'Cumulative share'),
         ('lcc_cumulative_jefferson_split.html', 'Jefferson split')]
CSS = '''/* site-nav (same on all five pages) */
  .site-nav { padding: 8px 32px; background: #f5f3f0; border-bottom: 1px solid #d4d0c8; display: flex; gap: 6px; flex-wrap: wrap; align-items: center; }
  .site-nav a, .site-nav span.nav-current { padding: 5px 14px; font-family: "Libre Baskerville", Georgia, serif; font-size: 11px; font-weight: 400; border-radius: 2px; letter-spacing: 0.05em; text-decoration: none; border: none; cursor: pointer; display: inline-block; line-height: 1.4; }
  .site-nav a { background: #4a90c4; color: #fff; }
  .site-nav a:hover { background: #5aa0d4; }
  .site-nav span.nav-current { background: #eceae6; color: #706e68; cursor: default; }
  /* end site-nav */'''
d = sys.argv[1]
for fn, _ in PAGES:
    p = os.path.join(d, fn); s = open(p, encoding='utf-8').read()
    # CSS: drop any old site-nav rules, then add the canonical block before </style>
    s = re.sub(r'\n\s*/\* site-nav \(same on all five pages\) \*/.*?/\* end site-nav \*/', '', s, flags=re.S)
    s = re.sub(r'\n\s*\.site-nav[^{]*\{[^}]*\}', '', s)
    i = s.index('</style>'); s = s[:i] + '  ' + CSS + '\n' + s[i:]
    # markup: drop old nav, add canonical one right after <body>
    s = re.sub(r'\s*<nav class="site-nav">.*?</nav>', '', s, flags=re.S)
    items = '\n'.join(f'  <span class="nav-current">{lab}</span>' if f == fn else f'  <a href="{f}">{lab}</a>' for f, lab in PAGES)
    s = re.sub(r'<body([^>]*)>', lambda m: f'<body{m.group(1)}>\n<nav class="site-nav">\n{items}\n</nav>', s, count=1)
    # redundant links to other pages
    s = re.sub(r'\s*<a class="back" href="index.html">← Back to dashboard</a>', '', s)
    s = re.sub(r'\s*<a class="load-all-btn" href="[a-z_0-9]+\.html"[^>]*>[^<]*</a>', '', s)
    open(p, 'w', encoding='utf-8').write(s)
    print(fn, s.count('site-nav'), 'nav refs')
