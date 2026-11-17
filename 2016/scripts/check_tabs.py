from playwright.sync_api import sync_playwright
import sys
tabs=['cumulative','class-bump','rankings','hk-rank','hk-sub','subclass-lifepath','inflection-scatter','jefferson-growth','era-growth','democratic-share','summary-stats','data-table']
with sync_playwright() as p:
    b=p.chromium.launch(executable_path='/usr/bin/google-chrome',args=['--no-sandbox']); pg=b.new_page(viewport={'width':1400,'height':1000})
    errs=[]; pg.on('pageerror',lambda e:errs.append(str(e)))
    def route(r):
        u=r.request.url
        if 'd3.min.js' in u: r.fulfill(path='/tmp/lib/node_modules/d3/dist/d3.min.js',content_type='application/javascript')
        elif 'chart.umd' in u: r.fulfill(path='/tmp/lib/node_modules/chart.js/dist/chart.umd.js',content_type='application/javascript')
        elif u.startswith('http://localhost'): r.continue_()
        else: r.abort()
    pg.route('**/*',route); pg.goto('http://localhost:8765/index.html'); pg.wait_for_timeout(5000)
    for t in tabs:
        pg.evaluate(f"showTab('{t}')"); pg.wait_for_timeout(1500); pg.screenshot(path=f'/home/claude/work/shots/{t}.png'); print(t,'errors so far',len(errs))
    print(errs[:5]); b.close()
