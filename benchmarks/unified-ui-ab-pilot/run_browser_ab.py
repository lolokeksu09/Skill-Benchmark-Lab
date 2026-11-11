"""Browser smoke using frozen Skill-Benchmark-Lab V4 sources and a manually guided candidate.

Not an independent AI-agent experiment. Uses Playwright/Chromium DOM renderer with
in-memory API stubs because browser navigation to local HTTP is blocked.
"""
from pathlib import Path
from playwright.sync_api import sync_playwright
import json, hashlib, shutil

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'results'
OUT.mkdir(exist_ok=True)
TESTJS = r'''window.__mock = {mode:'normal', calls:[]};
window.fetch=async (uri, opt={})=>{
  let url=String(uri); const state=window.__mock; state.calls.push({url,method:opt.method||'GET'});
  if(url.startsWith('/api/bookmarks/')){
    let body=JSON.parse(opt.body||'{}');
    if(state.mode==='reject-bookmark') return new Response('{"error":"stale"}',{status:412,headers:{'Content-Type':'application/json'}});
    return new Response(JSON.stringify({version:2,saved:body.saved}),{status:200,headers:{'Content-Type':'application/json'}});
  }
  const q=new URLSearchParams(url.split('?')[1]||'').get('q')||'';
  if(state.mode==='feed-error' && q==='err') return new Response('{"error":"not available"}',{status:503,headers:{'Content-Type':'application/json'}});
  if(state.mode==='race') await new Promise(r=>setTimeout(r,q==='slow'?170:q==='fast'?5:0));
  const cursor=new URLSearchParams(url.split('?')[1]||'').get('cursor');
  const posts=[
    {id:'p1',title:'Public discussion',summary:'The public news board.',saved:false,version:1},
    {id:'p2',title:'<img src=x onerror="window.__labXSS=1">',summary:'Untrusted text sample.',saved:false,version:1}
  ];
  if(state.mode==='race' && q==='slow') return new Response(JSON.stringify({items:[{id:'slow',title:'Older request',summary:'Should not overwrite',saved:false,version:1}],nextCursor:null}),{status:200});
  if(state.mode==='race' && q==='fast') return new Response(JSON.stringify({items:[{id:'fast',title:'Fresh request',summary:'The correct result',saved:false,version:1}],nextCursor:null}),{status:200});
  if(state.mode==='paginate') return new Response(JSON.stringify(cursor ? {items:[posts[1],{id:'p3',title:'Later discussion',summary:'Third post',saved:false,version:1}],nextCursor:null} : {items:posts,nextCursor:'next-page'}),{status:200});
  return new Response(JSON.stringify({items:posts,nextCursor:null}),{status:200,headers:{'Content-Type':'application/json'}});
};'''

def mount(browser,variant,width=375,mode='normal'):
    page=browser.new_page(viewport={'width':width,'height':812},device_scale_factor=1)
    paths=ROOT/'web'/variant
    html=(paths/'index.html').read_text()
    css=(paths/'styles.css').read_text()
    html=html.replace('<link rel="stylesheet" href="/styles.css">','<style>'+css+'</style>').replace('<script type="module" src="/app.mjs"></script>','')
    page.set_content(html,wait_until='domcontentloaded')
    page.add_script_tag(content=TESTJS)
    page.evaluate('(mode)=>window.__mock.mode=mode',mode)
    page.add_script_tag(content=(paths/'app.mjs').read_text(), type='module')
    page.locator('.card').first.wait_for(timeout=8000)
    return page

def condition(fn):
    try: return {'passed': bool(fn())}
    except Exception as e: return {'passed':False,'error':str(e)[:240]}

with sync_playwright() as p:
    chrome=shutil.which('chromium') or shutil.which('google-chrome')
    browser=p.chromium.launch(headless=True,args=['--no-sandbox'],**({'executable_path':chrome} if chrome else {}))
    results={}
    for variant in ('control','candidate'):
        tests={}
        for width in (375,768,1280):
            page=mount(browser,variant,width)
            dims=page.evaluate('''() => ({width: innerWidth, scrollWidth:document.documentElement.scrollWidth,clientWidth:document.documentElement.clientWidth})''')
            tests[f'no_overflow_{width}']={'passed': dims['scrollWidth']<=dims['clientWidth'],'details':dims}
            if width in (375,1280):page.screenshot(path=str(OUT/f'{variant}-{width}.png'))
            if width==375:
                a11y=page.locator('.bookmark').evaluate_all('bs=>bs.every(b=>!!b.getAttribute("aria-label")||!!b.getAttribute("aria-labelledby"))')
                tests['bookmark_accessible_name']={'passed':bool(a11y)}
                tests['safe_untrusted_content']={'passed':page.evaluate('window.__labXSS !== 1')}
                button=page.locator('.bookmark').first
                button.focus()
                style=button.evaluate('b=>({width:b.getBoundingClientRect().width,height:b.getBoundingClientRect().height,outline:getComputedStyle(b).outlineWidth})')
                tests['minimum_touch_target_44px']={'passed':style['width']>=44 and style['height']>=44,'details':style}
            page.close()
        page=mount(browser,variant,mode='reject-bookmark')
        b=page.locator('.bookmark').first
        before=b.get_attribute('aria-pressed')
        b.click()
        page.wait_for_timeout(170)
        after=b.get_attribute('aria-pressed')
        status=page.locator('#status').inner_text()
        tests['rollback_on_412']={'passed':before==after and 'could not' in status.lower(),'details':{'before':before,'after':after,'status':status}}
        page.close()
        page=mount(browser,variant,mode='feed-error')
        page.locator('#search').fill('err')
        page.wait_for_timeout(150)
        status=page.locator('#status').inner_text()
        tests['failed_search_recovery']={'passed':page.locator('.card').count()==2 and ('could not' in status.lower() or 'error' in status.lower()),'details':{'status':status,'cards':page.locator('.card').count()}}
        page.close()
        page=mount(browser,variant,mode='race')
        field=page.locator('#search')
        field.fill('slow'); field.fill('fast')
        page.wait_for_timeout(280)
        ids=page.locator('.card').evaluate_all('els=>els.map(e=>e.dataset.id)')
        tests['stale_request_discarded']={'passed':ids==['fast'],'details':{'ids':ids}}
        page.close()
        page=mount(browser,variant,mode='paginate')
        page.locator('#more').click()
        page.wait_for_timeout(150)
        ids=page.locator('.card').evaluate_all('els=>els.map(e=>e.dataset.id)')
        tests['pagination_no_duplicates']={'passed':ids==['p1','p2','p3'],'details':{'ids':ids}}
        page.close()
        results[variant]={'tests':tests,'pass':sum(v['passed'] for v in tests.values()),'total':len(tests)}
    browser.close()

report={'experiment_type':'exploratory unblinded comparison; NOT independent agent efficacy test',
        'source':'Skill-Benchmark-Lab bench/v4-hard-base web fixture',
        'control_provenance':'frozen baseline from Lab; intentionally defective',
        'candidate_provenance':'same-session manually implemented and guided by Unified UX/anti-AI-slop instructions',
        'execution':'Chromium with Playwright DOM, in-memory stub API, no backend server or Android device',
        'source_digests': {v:{f:hashlib.sha256((ROOT/'web'/v/f).read_bytes()).hexdigest() for f in ('index.html','styles.css','app.mjs')} for v in ('control','candidate')},
        'results':results}
(OUT/'web-ab-results.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({v:{'pass':r['pass'],'total':r['total'],'failed':[k for k,t in r['tests'].items() if not t['passed']]} for v,r in results.items()},ensure_ascii=False,indent=2))
