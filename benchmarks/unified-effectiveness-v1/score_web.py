#!/usr/bin/env python3
"""Deterministic contract tests for the web arm. Never calls a model or API.

Usage: python score_web.py --candidate /path/to/web/files --out /tmp/score
Python 3.12+, playwright==1.57.0, Chromium.
"""
import argparse
import hashlib
import json
import re
import shutil
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent
API = (ROOT/'fixtures/queue-api.js').read_text(encoding='utf-8')

def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def mount(browser, directory, width=375, screenshot=None):
    html=(directory/'index.html').read_text(encoding='utf-8')
    css=(directory/'styles.css').read_text(encoding='utf-8')
    js=(directory/'app.js').read_text(encoding='utf-8')
    # Avoid sandbox-local HTTP/CORS dependency; inspect the exact source files.
    html=html.replace('<link rel="stylesheet" href="styles.css">','<style>'+css+'</style>')
    html=html.replace('<script src="app.js" defer></script>','')
    page=browser.new_page(viewport={'width':width,'height':820},device_scale_factor=1)
    page.set_default_timeout(1500)
    page.set_content(html,wait_until='domcontentloaded')
    page.add_script_tag(content=API)
    page.add_script_tag(content=js)
    page.wait_for_timeout(230)
    if screenshot: page.screenshot(path=str(screenshot),full_page=True)
    return page

def identifiers(page):
    return page.locator('.card').evaluate_all('els => els.map(el => el.dataset.id)')

def wait_and_ids(page,ms=220):
    page.wait_for_timeout(ms)
    return identifiers(page)

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--candidate',required=True,type=Path)
    parser.add_argument('--out',required=True,type=Path)
    parser.add_argument('--screenshot',action='store_true')
    args=parser.parse_args()
    candidate=args.candidate.resolve(); out=args.out.resolve();out.mkdir(parents=True,exist_ok=True)
    required=['index.html','styles.css','app.js']
    if not all((candidate/f).is_file() for f in required):parser.error('candidate must contain index.html styles.css and app.js')
    results=[]
    with sync_playwright() as p:
        sys_chrome=shutil.which('chromium') or shutil.which('google-chrome')
        kwargs={'executable_path':sys_chrome} if sys_chrome else {}
        browser=p.chromium.launch(headless=True,args=['--no-sandbox'],**kwargs)
        def run(name,check,width=375):
            page=None
            try:
                page=mount(browser,candidate,width, out/(name+'.png') if args.screenshot and name in ['responsive_375','responsive_1280'] else None)
                got=check(page)
                ok,msg=(got if isinstance(got,tuple) else (got,''))
                results.append({'name':name,'status':'pass' if ok else 'fail','details':msg})
            except Exception as e:
                results.append({'name':name,'status':'fail','details':type(e).__name__+': '+str(e)[:280]})
            finally:
                if page:page.close()
        run('initial_six_requests', lambda page: (len(identifiers(page))==6,str(identifiers(page))))
        def filter_done(page):
            page.locator('#filter').select_option('done')
            ids=wait_and_ids(page)
            return (ids==['r3','r5'],str(ids))
        run('status_filter_done',filter_done)
        def search_trim(page):
            page.locator('#search').fill('  BATTERY   ')
            ids=wait_and_ids(page)
            return (ids==['r1'],str(ids))
        run('trim_casefold_search',search_trim)
        def paired_filter(page):
            page.locator('#filter').select_option('done')
            page.locator('#search').fill('pump')
            ids=wait_and_ids(page)
            return (ids==['r3'],str(ids))
        run('combined_filter_and_search',paired_filter)
        def empty(page):
            page.locator('#search').fill('zx-unseen-query')
            ids=wait_and_ids(page)
            state=page.locator('#empty').is_visible()
            return (ids==[] and state,'ids='+str(ids)+', visible='+str(state))
        run('no_results_empty_state',empty)
        def error_recovery(page):
            before=identifiers(page)
            page.locator('#search').fill('error')
            after=wait_and_ids(page)
            fb=page.locator('#feedback').inner_text().lower()
            return (before==after and ('error' in fb or 'could not' in fb or 'failed' in fb),str(after)+': '+fb[:160])
        run('failed_search_preserves_cards',error_recovery)
        def race(page):
            inp=page.locator('#search')
            inp.fill('slow'); page.wait_for_timeout(7); inp.fill('fast')
            ids=wait_and_ids(page,280)
            return (ids==['r6'],str(ids))
        run('stale_search_response_discarded',race)
        def safe_html(page):
            nodes=page.locator('.card img').count()
            injected=page.evaluate('Boolean(window.__injected)')
            title=page.locator('.card[data-id="r5"] h2').inner_text()
            return (not nodes and not injected and '<img' in title,f'img_nodes={nodes} injected={injected} title={title}')
        run('untrusted_data_safe_text',safe_html)
        def bookmark_label(page):
            arr=page.locator('.bookmark').evaluate_all('xs=>xs.map(b=>({name:b.getAttribute("aria-label")||b.getAttribute("aria-labelledby"),pressed:b.getAttribute("aria-pressed")}))')
            return (len(arr)==6 and all(x['name'] and x['pressed'] in ['true','false'] for x in arr),str(arr)[:250])
        run('accessible_bookmarks',bookmark_label)
        def bookmark_keyboard(page):
            button=page.locator('.card[data-id="r1"] .bookmark')
            before=button.get_attribute('aria-pressed');button.focus();page.keyboard.press('Space');page.wait_for_timeout(60)
            after=button.get_attribute('aria-pressed')
            return (before=='false' and after=='true',f'{before}->{after}')
        run('keyboard_space_operates_bookmark',bookmark_keyboard)
        def failed_toggle(page):
            button=page.locator('.card[data-id="r2"] .bookmark')
            before=button.get_attribute('aria-pressed')
            page.evaluate('window.queueApi.rejectNextToggle()')
            button.click();page.wait_for_timeout(70)
            after=button.get_attribute('aria-pressed')
            feedback=page.locator('#feedback').inner_text().lower()
            return (before==after=='true' and ('could not' in feedback or 'failed' in feedback or 'error' in feedback),f'{before}->{after}; {feedback[:120]}')
        run('rejected_bookmark_restores_true',failed_toggle)
        def retry(page):
            button=page.locator('.card[data-id="r2"] .bookmark')
            page.evaluate('window.queueApi.rejectNextToggle()')
            button.click();page.wait_for_timeout(60)
            button.click();page.wait_for_timeout(60)
            after=button.get_attribute('aria-pressed')
            return (after=='false','retry pressed='+str(after))
        run('retry_after_rejected_bookmark',retry)
        def target(page):
            details=page.locator('.bookmark').first.evaluate('b=>({w:b.getBoundingClientRect().width,h:b.getBoundingClientRect().height})')
            return (details['w']>=44 and details['h']>=44,str(details))
        run('touch_target_44px',target)
        def focus(page):
            b=page.locator('.bookmark').first;b.focus()
            d=b.evaluate('b=>({style:getComputedStyle(b).outlineStyle,width:parseFloat(getComputedStyle(b).outlineWidth)})')
            return (d['style']!='none' and d['width']>=2,str(d))
        run('visible_focus_indicator',focus)
        for w in (375,768,1280):
            def widthcheck(page):
                dim=page.evaluate('({viewport:innerWidth,content:document.documentElement.scrollWidth})')
                return (dim['content']<=dim['viewport'],str(dim))
            run('responsive_'+str(w),widthcheck,width=w)
        browser.close()
    static=[]
    for f in required:
        text=(candidate/f).read_text(encoding='utf-8')
        if re.search(r'https?://|@import|<iframe|<script[^>]+src=["\']https?://',text,re.I):static.append(f)
    results.append({'name':'no_external_assets','status':'pass' if not static else 'fail','details':','.join(static)})
    counts={'passed':sum(r['status']=='pass' for r in results),'total':len(results)}
    doc={'schema':'unified-effectiveness-web-v1','candidate_path':str(candidate),'sha256':{f:digest(candidate/f) for f in required},'source_fixture_sha256':digest(ROOT/'fixtures/queue-api.js'),'checks':results,'summary':counts,'agent_trials':0,'inference':'none: deterministic UI contract only'}
    (out/'results.json').write_text(json.dumps(doc,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    print(json.dumps(counts));print('results: '+str(out/'results.json'))
    return 0 if counts['passed']==counts['total'] else 1
if __name__=='__main__':raise SystemExit(main())