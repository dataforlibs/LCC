#!/usr/bin/env python3
"""Add search (SEO / social / structured-data) and accessibility meta to the LCC pages.
Usage: 09_add_meta.py <pages_dir>   (idempotent; re-run replaces the block)"""
import sys, os, re, json
d = sys.argv[1]
BASE = 'https://dataforlibs.github.io/LCC/'
IMG = 'https://dataforlibs.github.io/lcc.png'
AUTHOR = 'Olha Buchel'
KW = 'Library of Congress Classification, LCC, Thomas Jefferson, Francis Bacon, library classification, catalog growth, MARC records, sigmoid growth, digital humanities, information visualization'
PAGES = {
 'index.html': ("Did Jefferson's Library Shape What We Know? Library of Congress Catalog Growth Dashboard",
   "Interactive dashboard analysing 9.5 million Library of Congress MARC records across 238 subclasses to test whether Jefferson's 1815 Baconian classification left a trace in catalog growth. Subclasses absent from his scheme grew more and peaked later.", 'Dataset'),
 'jefferson_lcc_alluvial.html': ("Jefferson 1815 to LCC Alluvial Diagram: Baconian Faculties, Chapters and Subclasses",
   "Alluvial diagram linking Bacon's three faculties (Memory, Reason, Imagination) to Jefferson's 1815 chapters, Library of Congress main classes and current LCC subclasses.", 'WebPage'),
 'lcc_bubble_animation_2.html': ("LCC Subclass Growth 1400-2020: Animated Bubble Chart",
   "Animated bubble chart of how every Library of Congress Classification subclass grew from 1400 to 2020, coloured by whether it has a counterpart in Jefferson's 1815 scheme.", 'WebPage'),
 'lcc_cumulative_share_v2.html': ("Library of Congress Catalog: Cumulative Share by Publication Decade",
   "How much of the Library of Congress catalog was published in each decade, with cumulative share from 1400 to 2020, based on the 2016 MARC distribution.", 'WebPage'),
 'lcc_cumulative_jefferson_split.html': ("Library of Congress Catalog: Jeffersonian vs Absent Subclass Share",
   "Cumulative and per-decade share of the Library of Congress catalog split between subclasses with a Jefferson counterpart and subclasses absent from his 1815 scheme.", 'WebPage'),
 'output/lcc_catalog_growth_by_decade.html': ("Library of Congress Catalog Record Growth by Decade",
   "Library of Congress catalog records per decade and per year, 1400-2020, with a note on incompletely catalogued recent years in the 2016 file.", 'WebPage'),
}
CSS = """<style id="a11y-css">
.skip-link{position:absolute;left:-9999px;top:0;background:#1e1c18;color:#fff;padding:8px 14px;z-index:1000;font:13px sans-serif}
.skip-link:focus{left:8px;top:8px}
a:focus-visible,button:focus-visible,[tabindex]:focus-visible,select:focus-visible,input:focus-visible{outline:3px solid #c46a4a;outline-offset:2px}
#main-content:focus{outline:none}
@media (prefers-reduced-motion: reduce){*{animation-duration:.01ms!important;animation-iteration-count:1!important;transition-duration:.01ms!important;scroll-behavior:auto!important}}
</style>"""
JS = """<script id="a11y-js">
(function(){
  document.querySelectorAll('canvas:not([aria-label]),svg[id]:not([aria-label])').forEach(function(el){
    if(el.closest('[aria-hidden="true"]')) return;
    var n=el, t='';
    while(n && !t){
      var p=n.previousElementSibling;
      while(p && !t){ var h=p.matches('h2,h3,h4,.chart-title,.card-title')?p:p.querySelector('h2,h3,h4,.chart-title,.card-title'); if(h) t=h.textContent.trim(); p=p.previousElementSibling; }
      n=n.parentElement;
    }
    el.setAttribute('role','img'); el.setAttribute('aria-label',(t||'Chart')+' (chart)');
  });
})();
</script>"""
def meta(fn, title, desc, typ):
    url = BASE + fn.replace('output/', 'output/')
    ld = {"@context": "https://schema.org", "@type": typ, "name": title, "url": url, "description": desc,
          "inLanguage": "en", "author": {"@type": "Person", "name": AUTHOR}, "keywords": KW,
          "isPartOf": {"@type": "WebSite", "name": "Data Science for Libraries", "url": "https://dataforlibs.github.io/"}}
    if typ == 'Dataset':
        ld.update({"temporalCoverage": "1400/2020", "variableMeasured": "Library of Congress catalog records per subclass and publication year",
                   "measurementTechnique": "Parsing of Library of Congress MARC21 records; logistic fits of cumulative growth per LC subclass",
                   "isBasedOn": "Library of Congress MARC distribution, 2016"})
    e = lambda s: s.replace('&', '&amp;').replace('"', '&quot;')
    return f"""<!-- seo-meta -->
<title>{e(title)}</title>
<meta name="description" content="{e(desc)}">
<meta name="keywords" content="{e(KW)}">
<meta name="author" content="{AUTHOR}">
<meta name="robots" content="index, follow, max-image-preview:large">
<meta name="color-scheme" content="light">
<link rel="canonical" href="{url}">
<meta property="og:type" content="article">
<meta property="og:site_name" content="Data Science for Libraries">
<meta property="og:title" content="{e(title)}">
<meta property="og:description" content="{e(desc)}">
<meta property="og:url" content="{url}">
<meta property="og:image" content="{IMG}">
<meta property="og:image:alt" content="Median growth of Library of Congress subclasses since 1815: 437 times for subclasses not in Jefferson's scheme, 221 times for those with a counterpart">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{e(title)}">
<meta name="twitter:description" content="{e(desc)}">
<meta name="twitter:image" content="{IMG}">
<script type="application/ld+json">{json.dumps(ld, ensure_ascii=False)}</script>
{CSS}
<!-- /seo-meta -->
"""
for fn, (title, desc, typ) in PAGES.items():
    p = os.path.join(d, fn)
    if not os.path.exists(p): print('skip', fn); continue
    s = open(p, encoding='utf-8').read()
    s = re.sub(r'<!-- seo-meta -->.*?<!-- /seo-meta -->\n?', '', s, flags=re.S)
    s = re.sub(r'<!-- a11y-js -->.*?<!-- /a11y-js -->\n?', '', s, flags=re.S)
    s = re.sub(r'<title>.*?</title>\s*', '', s, count=1, flags=re.S)
    s = s.replace('</head>', meta(fn, title, desc, typ) + '</head>', 1)
    # landmark + skip link + nav label
    if 'id="main-content"' not in s:
        if '<main' in s:
            s = s.replace('<main', '<main id="main-content" tabindex="-1"', 1)
        else:
            s = re.sub(r'<h1(\s|>)', lambda m: '<h1 id="main-content" tabindex="-1"' + m.group(1), s, count=1)
    if 'class="skip-link"' not in s:
        s = re.sub(r'(<body[^>]*>)', r'\1\n<a class="skip-link" href="#main-content">Skip to main content</a>', s, count=1)
    s = s.replace('<nav class="site-nav">', '<nav class="site-nav" aria-label="Site pages">')
    s = s.replace('</body>', '<!-- a11y-js -->\n' + JS + '\n<!-- /a11y-js -->\n</body>', 1)
    open(p, 'w', encoding='utf-8').write(s)
    print('ok', fn)
