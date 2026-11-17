from playwright.sync_api import sync_playwright
pages=['jefferson_lcc_alluvial','lcc_bubble_animation_2','lcc_cumulative_share_v2','lcc_cumulative_jefferson_split']
L='/tmp/lib/node_modules/'
with sync_playwright() as p:
    b=p.chromium.launch(executable_path='/usr/bin/google-chrome',args=['--no-sandbox'])
    for n in pages:
        pg=b.new_page(viewport={'width':1400,'height':1000}); errs=[]
        pg.on('pageerror',lambda e:errs.append(str(e)))
        def route(r):
            u=r.request.url
            if 'd3-sankey' in u: r.fulfill(path=L+'d3-sankey/dist/d3-sankey.min.js',content_type='application/javascript')
            elif 'd3' in u and u.endswith(('.js','d3@7')) : r.fulfill(path=L+'d3/dist/d3.min.js',content_type='application/javascript')
            elif 'chart' in u.lower() and 'umd' in u: r.fulfill(path=L+'chart.js/dist/chart.umd.js',content_type='application/javascript')
            elif u.startswith('http://localhost'): r.continue_()
            else: r.abort()
        pg.route('**/*',route); pg.goto(f'http://localhost:8765/{n}.html'); pg.wait_for_timeout(3500)
        extra=pg.inner_text('#stats') if n.startswith('jeff') else ''
        pg.screenshot(path=f'/home/claude/work/shots/{n}.png'); print(n,'errors',errs[:3],extra); pg.close()
    b.close()
