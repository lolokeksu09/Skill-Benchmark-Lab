#!/usr/bin/env python3
"""Real Chromium UI checks against exact MTS source; all page/review data is synthetic."""
import argparse
import copy
import functools
import hashlib
from http.server import SimpleHTTPRequestHandler,ThreadingHTTPServer
import json
import os
from pathlib import Path
import sys
import threading
import traceback
from PIL import Image,ImageDraw

ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'vendor'))
sys.path.insert(0,str(ROOT/'vendor/skills/manga-page/scripts'))
from retouch_workbench import prepare as prepare_retouch, apply as apply_retouch
from build_page_review import make_review
from build_transcription_review import build
from check_page_review import check
from build_phone_reading import build as phone_reading

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def dump(p,data):p.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def fixtures(out):
    source=Image.new('RGB',(1280,960),'#eef1f5');d=ImageDraw.Draw(source)
    d.rectangle((35,35,1245,925),outline='#233140',width=6);d.rounded_rectangle((320,280,830,480),radius=55,fill='white',outline='black',width=4);d.text((480,355),'ORIGINAL',fill='black',font_size=36)
    source.save(out/'source.png');cleaned=source.copy();ImageDraw.Draw(cleaned).rectangle((400,330,760,420),fill='white');cleaned.save(out/'cleaned.png');final=cleaned.copy();ImageDraw.Draw(final).text((470,355),'TRANSLATED',fill='#001944',font_size=32);final.save(out/'final.png')
    inv={'source_sha256':sha(out/'source.png'),'source_dimensions':[1280,960],'inventory_complete':False,'regions':[{'id':'synthetic-dialogue','box':[400,330,360,90],'source_text':'ORIGINAL','target_text':'ПЕРЕВОД','source_reviewed':True,'handling':'translate','translation_approved':True}]};dump(out/'inventory.json',inv)
    report={'source_image_sha256':sha(out/'source.png'),'cleaned_image_sha256':sha(out/'cleaned.png'),'rendered_page_sha256':sha(out/'final.png'),'inventory_sha256':sha(out/'inventory.json'),'review_regions':[{'id':'cleanup-1','kind':'cleanup','box':[400,330,760,420]},{'id':'lettering-1','kind':'lettering','box':[460,345,760,405]}],'inventory_review_status':[{'id':'synthetic-dialogue','source_reviewed':True,'handling':'translate','translation_approved':True}],'issues_pending':['Synthetic browser fixture only; no translation or artistic quality assessment']};dump(out/'page-report.json',report)
    make_review(out/'source.png',out/'cleaned.png',out/'final.png',out/'page-report.json',out/'review.html')
    guesses={'source_sha256':inv['source_sha256'],'regions':[{'box':[400,330,360,90],'source_text_candidate':'ORIG1NAL','alternatives':[{'source_text_candidate':'ORIGINAL'}]}]}
    build(out/'source.png',out/'inventory.json',out/'transcription.html',guesses)
    phone_reading(out/'final.png',out/'page-report.json',[{'id':'focus','label':'Focused reading window','box':[320,280,510,200]},{'id':'context','label':'Full context','box':[0,0,1280,960]}],out/'phone-reading.html')
    local=Image.new('RGB',(600,400),'#c9d6e3');ImageDraw.Draw(local).rectangle((296,196,304,204),fill='black');local.save(out/'clone-source.png')
    prepare_retouch(out/'clone-source.png',out/'workbench')
    return report

def run(out,prepare_only=False):
    out.mkdir(parents=True,exist_ok=False)
    provenance=json.loads((ROOT/'SOURCE.json').read_bytes())
    for name,expected in provenance['sha256'].items():assert sha(ROOT/name)==expected,'Vendored source hash mismatch: '+name
    report=fixtures(out)
    if prepare_only:return {'status':'fixtures_generated','browser_tested':False,'source_hashes_verified':True}
    from playwright.sync_api import sync_playwright
    class Quiet(SimpleHTTPRequestHandler):
        def log_message(self,*args):pass
    handler=functools.partial(Quiet,directory=str(out.resolve()));server=ThreadingHTTPServer(('127.0.0.1',0),handler);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    base=f'http://127.0.0.1:{server.server_address[1]}'
    result={'status':'running','browser_tested':True,'plugin_version':provenance['plugin_version'],'plugin_release':provenance['release_id'],'commit_sha':os.environ.get('GITHUB_SHA'),'source_sha256':provenance['sha256'],'fixture':'synthetic','checks':[],'limits':['Browser controls and exported evidence only','No Korean OCR, translation quality or real-page retouch assessment','Checked review entries are synthetic test data, not a human sign-off']}
    def passed(name):result['checks'].append({'name':name,'passed':True})
    try:
        with sync_playwright() as p:
            browser=p.chromium.launch(headless=True);result['chromium_version']=browser.version
            context=browser.new_context(viewport={'width':1100,'height':900},accept_downloads=True);context.tracing.start(screenshots=True,snapshots=True,sources=True)
            page=context.new_page();errors=[];external=[];page.on('pageerror',lambda err:errors.append(str(err)))
            def route(req):
                url=req.request.url
                if url.startswith(base+'/') or url.startswith(('data:','blob:')):req.continue_()
                else:external.append(url);req.abort()
            page.route('**/*',route)
            try:
                page.goto(base+'/review.html',wait_until='load')
                assert page.locator('#base').evaluate('(im)=>im.complete && im.naturalWidth===1280 && im.naturalHeight===960')
                assert page.locator('.crops img').count()==6
                passed('Source and six actual edit-region crops load')
                page.locator('#actual').click();assert page.locator('#actual').get_attribute('aria-pressed')=='true';assert round(page.locator('#viewport').bounding_box()['width'])==1280
                page.screenshot(path=str(out/'review-100-percent.png'));passed('100% view uses native source width')
                page.locator('#phone').click();assert page.locator('#phone').get_attribute('aria-pressed')=='true';assert page.locator('#actual').get_attribute('aria-pressed')=='false';assert round(page.locator('#viewport').bounding_box()['width'])==390
                page.screenshot(path=str(out/'review-phone.png'));passed('390px view resets 100% mode')
                slider=page.locator('#split');slider.press('Home')
                for _ in range(25):slider.press('ArrowRight')
                assert slider.input_value()=='25';assert '75%' in page.locator('#top').evaluate('(im)=>im.style.clipPath');passed('Comparison slider changes visible split through keyboard input')
                page.locator('#diffbutton').click();assert page.locator('#diff').is_visible();final_diff=page.locator('#diff').get_attribute('src')
                page.locator('#clean').click();assert page.locator('#clean').get_attribute('aria-pressed')=='true';assert page.locator('#final').get_attribute('aria-pressed')=='false';assert page.locator('#diff').get_attribute('src')!=final_diff
                page.screenshot(path=str(out/'clean-diff.png'));page.locator('#final').click();assert page.locator('#diff').get_attribute('src')==final_diff;passed('Cleanup/final buttons switch the correct stage-specific difference image')
                def download(button,name):
                    with page.expect_download() as event:page.locator(button).click()
                    target=out/name;event.value.save_as(target);return target
                pending=download('#export-review','pending-review.json')
                verdict=check(out/'page-report.json',pending,out/'source.png',out/'cleaned.png',out/'final.png');assert not verdict['recorded_review_complete'];passed('Unchecked exported review remains incomplete')
                for checkbox in page.locator('[data-check],[data-region]').all():checkbox.check()
                for note in page.locator('[data-note],[data-region-note]').all():note.fill('Synthetic browser test evidence; no real human review claimed')
                complete=download('#export-review','synthetic-complete-review.json')
                verdict=check(out/'page-report.json',complete,out/'source.png',out/'cleaned.png',out/'final.png');assert verdict['recorded_review_complete'] and not verdict['release_ready'];dump(out/'review-validation.json',verdict);passed('Browser-exported categories and regions validate without release approval')
                changed=copy.deepcopy(report);changed['inventory_sha256']='changed-inventory';dump(out/'changed-report.json',changed)
                assert not check(out/'changed-report.json',complete,out/'source.png',out/'cleaned.png',out/'final.png')['recorded_review_complete'];passed('Changed inventory invalidates the actual browser export')
                page.set_viewport_size({'width':414,'height':896});page.screenshot(path=str(out/'review-mobile.png'),full_page=True)
                assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth'), 'Mobile page overflows horizontally';passed('Mobile reviewer has no document-level horizontal overflow')
                page.goto(base+'/transcription.html',wait_until='load');assert 'ORIG1NAL' in page.locator('body').inner_text();assert 'ORIGINAL' in page.locator('body').inner_text()
                assert not page.locator('[data-field="source_reviewed"]').is_checked();assert not page.locator('[data-field="translation_approved"]').is_checked()
                page.locator('[data-field="source_text"]').fill('ORIGINAL');page.locator('[data-field="target_text"]').fill('ПЕРЕВОД');page.locator('[data-field="source_reviewed"]').check();page.locator('[data-field="translation_approved"]').check()
                source_export=download('#export-source','source-inventory-reviewed.json');ledger=json.loads(source_export.read_bytes())
                assert ledger['source_sha256']==report['source_image_sha256'];assert ledger['regions'][0]['source_text']=='ORIGINAL';assert ledger['regions'][0]['target_text']=='ПЕРЕВОД';assert ledger['regions'][0]['source_reviewed'] and ledger['regions'][0]['translation_approved'];assert ledger['inventory_complete']is False and ledger['independent_review']is False
                page.locator('#actual-source').click();assert page.locator('#whole').evaluate('(im)=>im.style.maxWidth')=='none';page.locator('#actual-source').click();assert page.locator('#whole').evaluate('(im)=>im.style.maxWidth')=='100%'
                page.screenshot(path=str(out/'transcription-mobile.png'),full_page=True);passed('Source crop/OCR alternatives, actual-size toggle, editing and exported ledger preserve review limits')
                page.set_viewport_size({'width':1100,'height':900});page.goto(base+'/phone-reading.html',wait_until='load');assert page.locator('.reading').count()==2
                assert page.locator('.reading').first.evaluate('(im)=>im.complete && im.naturalWidth===510 && im.naturalHeight===200');assert round(page.locator('.reading').first.bounding_box()['width'])==390;passed('Ordered phone reading windows load exact final-image crops at 390px')
                page.locator('#reading-native').click();assert round(page.locator('.reading').first.bounding_box()['width'])==510;assert page.locator('#reading-native').get_attribute('aria-pressed')=='true';page.locator('#reading-phone').click();assert page.locator('#reading-phone').get_attribute('aria-pressed')=='true'
                page.set_viewport_size({'width':414,'height':896});assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth');page.screenshot(path=str(out/'phone-reading-mobile.png'),full_page=True);passed('Reading windows switch native/phone scale without mobile document overflow')
                # Exercise native mask drawing and downloaded clone plans through the actual Python runner.
                page.set_viewport_size({'width':1100,'height':900});page.goto(base+'/workbench/retouch.html',wait_until='load')
                page.wait_for_function("!document.getElementById('export').disabled")
                assert not page.locator('#reviewed').is_checked()
                pending_plan=download('#export','workbench/pending-plan.json')
                try:apply_retouch(pending_plan,out/'blocked-unreviewed')
                except ValueError as e:assert 'Reviewed mask' in str(e)
                else:raise AssertionError('Unreviewed UI export was accepted')
                passed('Workbench starts unreviewed and its actual downloaded plan cannot execute')
                def click_native(x,y):
                    page.locator('#page').scroll_into_view_if_needed();box=page.locator('#page').bounding_box()
                    page.mouse.click(box['x']+(x+.5)*box['width']/600,box['y']+(y+.5)*box['height']/400)
                page.locator('#radius').fill('12');click_native(300,200)
                page.locator('#tool').select_option('protect');page.locator('#radius').fill('4');click_native(400,100)
                page.locator('#tool').select_option('donor');click_native(250,150)
                page.locator('#tool').select_option('clone');page.locator('#radius').fill('8');click_native(300,200)
                page.locator('#show-masks').uncheck()
                assert page.locator('#page').evaluate('(c)=>Array.from(c.getContext("2d").getImageData(300,200,1,1).data)')==[201,214,227,255]
                page.locator('#show-clones').uncheck()
                assert page.locator('#page').evaluate('(c)=>Array.from(c.getContext("2d").getImageData(300,200,1,1).data)')==[0,0,0,255]
                page.locator('#show-clones').check();passed('Mask, protection, immutable donor and clone controls change the actual canvas preview')
                page.locator('#reviewed').check();page.locator('#evidence').fill('Synthetic browser fixture, no real art review')
                exported=download('#export','workbench/retouch-plan.json');plan=json.loads(exported.read_bytes())
                assert plan['operations'][0]['target']==[300,200] and plan['operations'][0]['source']==[250,150]
                actual=apply_retouch(exported,out/'workbench-result')
                assert actual['outside_mask_changes']==0 and actual['protected_artwork_changes']==0 and actual['manual_art_review']=='pending'
                with Image.open(out/'workbench-result/result/cleaned.png') as im:assert im.size==(600,400) and im.getpixel((300,200))==(201,214,227,255)
                dump(out/'workbench-result/browser-roundtrip.json',actual);passed('Browser-exported plan replays to native binary masks and an exact protected-pixel check')
                page.locator('#phone').click();assert round(page.locator('#page').bounding_box()['width'])==390
                page.locator('#tool').select_option('protect');page.locator('#radius').fill('1');click_native(300,200)
                assert not page.locator('#reviewed').is_checked();page.locator('#reviewed').check()
                collision=download('#export','workbench/collision-plan.json');colliding=json.loads(collision.read_bytes())
                assert colliding['protected_strokes'][-1]['points']==[[300,200]],colliding
                try:apply_retouch(collision,out/'blocked-protected')
                except ValueError as e:assert 'changes protected artwork' in str(e)
                else:raise AssertionError('Protected damage accepted')
                passed('390px pointer coordinates remain native and exported protected damage is rejected')
                page.locator('#undo').click();assert not page.locator('#reviewed').is_checked()
                undone=download('#export','workbench/undone-plan.json');assert len(json.loads(undone.read_bytes())['protected_strokes'])==1
                passed('Undo restores the actual prior plan and invalidates old mask review')
                page.locator('#native').click();assert round(page.locator('#page').bounding_box()['width'])==600
                page.set_viewport_size({'width':414,'height':896});assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
                page.locator('#fit').click();assert page.locator('#page').bounding_box()['width']<390
                page.screenshot(path=str(out/'workbench-mobile.png'),full_page=True);passed('Native workbench scrolling and mobile fit stay inside the document width')
                assert not errors,errors;assert not external,external;passed('No JavaScript errors or external resource requests')
                result['status']='passed'
            finally:
                result['page_errors']=errors;result['unexpected_external_requests']=external;context.tracing.stop(path=str(out/'trace.zip'));browser.close()
    except Exception as exc:
        result['status']='failed';result['error']=str(exc);(out/'failure.txt').write_text(traceback.format_exc(),encoding='utf-8')
    finally:
        server.shutdown();server.server_close();dump(out/'browser-report.json',result)
    return result

if __name__=='__main__':
    a=argparse.ArgumentParser(description=__doc__);a.add_argument('--out',type=Path,required=True);a.add_argument('--prepare-only',action='store_true');args=a.parse_args()
    result=run(args.out,args.prepare_only);print(json.dumps(result,ensure_ascii=False,indent=2));sys.exit(0 if result['status']in {'passed','fixtures_generated'} else 1)
