import sys
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    b=p.chromium.launch(executable_path='/usr/bin/google-chrome',args=['--no-sandbox']); pg=b.new_page(viewport={'width':1400,'height':900})
    errs=[]; pg.on('pageerror',lambda e:errs.append(str(e))); pg.on('console',lambda m: errs.append('console:'+m.text) if m.type=='error' else None)
    def route(r):
        u=r.request.url
        if 'd3.min.js' in u: r.fulfill(path='/tmp/lib/node_modules/d3/dist/d3.min.js',content_type='application/javascript')
        elif 'chart.umd' in u: r.fulfill(path='/tmp/lib/node_modules/chart.js/dist/chart.umd.js',content_type='application/javascript')
        elif u.startswith('http://localhost'): r.continue_()
        else: r.abort()
    pg.route('**/*',route)
    pg.goto('http://localhost:8765/index.html'); pg.wait_for_timeout(6000)
    print('status', pg.inner_text('#load-note') if pg.query_selector('#load-note') else '')
    print('errors', [e for e in errs if 'cdnjs' not in e and 'fonts' not in e][:8], len(errs))
    pg.click('#render-btn') if pg.query_selector('#render-btn') else None; pg.wait_for_timeout(3000)
    tabs=[t.get_attribute('onclick') or t.inner_text() for t in pg.query_selector_all('.tab-btn, [data-tab], nav button')][:40]; print('tabs',tabs)
    pg.screenshot(path='/home/claude/work/shot_main.png'); b.close()
