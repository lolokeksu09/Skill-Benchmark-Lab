#!/usr/bin/env python3
"""Actual source-coordinate reading windows; preserves the full-size page separately."""
import argparse
import hashlib
import html
import json
from pathlib import Path
from PIL import Image
from build_page_review import png_url

def build(final_file,report_file,regions,output):
    final_file,report_file,output=map(Path,(final_file,report_file,output))
    report=json.loads(report_file.read_bytes());digest=hashlib.sha256(final_file.read_bytes()).hexdigest()
    if report.get('rendered_page_sha256')!=digest:raise ValueError('Reading windows do not match actual final image hash')
    if not isinstance(regions,list) or not 1<=len(regions)<=50:raise ValueError('Expected 1..50 explicitly ordered reading regions')
    with Image.open(final_file) as im:
        if im.width*im.height>40_000_000:raise ValueError('Oversized page')
        page=im.convert('RGBA')
    seen=set();cards=[];manifest=[]
    for i,r in enumerate(regions):
        ident=r.get('id');box=r.get('box')
        if not isinstance(ident,str) or not ident.strip() or ident in seen:raise ValueError('Unique reading-region IDs required')
        seen.add(ident)
        if not isinstance(box,list) or len(box)!=4 or any(type(v)is not int for v in box):raise ValueError('Region needs integer [x,y,width,height]')
        x,y,w,h=box
        if not 0<=x<x+w<=page.width or not 0<=y<y+h<=page.height:raise ValueError('Reading region leaves original raster')
        crop=page.crop((x,y,x+w,y+h));name=html.escape(str(r.get('label',ident)))
        cards.append('<article id="reading-'+str(i)+'"><h2>'+name+'</h2><p>'+html.escape(str(box))+' px</p><div class="pan"><img class="reading" data-native-width="'+str(w)+'" alt="'+html.escape(ident,quote=True)+'" src="'+png_url(crop)+'"></div></article>')
        manifest.append({'id':ident,'box':box,'label':str(r.get('label',ident))})
    doc='''<!doctype html><html lang="ru"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Чтение фрагментов разворота</title><style>*{box-sizing:border-box}body{margin:0;background:#14171c;color:#eee;font:16px/1.45 system-ui}main{max-width:900px;margin:auto;padding:18px}button{font:inherit;padding:12px;margin:6px 6px 6px 0}article{border:1px solid #4d5967;margin:22px 0;padding:12px}h2{font-size:18px}.pan{overflow:auto}.reading{display:block;width:390px;max-width:100%;height:auto;margin:auto}body.native .reading{width:var(--native);max-width:none}p{overflow-wrap:anywhere}</style><main><h1>Чтение фрагментов</h1><p>Точные области увеличения из полного разворота в заданном порядке. Полное изображение сохранено отдельно. Читаемость при ширине 390 px проверяется здесь по каждому фрагменту.</p><button id="reading-phone" aria-pressed="true">390 px</button><button id="reading-native" aria-pressed="false">100% исходных пикселей</button>'''+''.join(cards)+'''<p>SHA-256 полного изображения: '''+digest+'''</p></main><script>
document.querySelectorAll('.reading').forEach(im=>im.style.setProperty('--native',im.dataset.nativeWidth+'px'));
document.getElementById('reading-native').onclick=()=>{document.body.classList.add('native');document.getElementById('reading-native').setAttribute('aria-pressed','true');document.getElementById('reading-phone').setAttribute('aria-pressed','false')};
document.getElementById('reading-phone').onclick=()=>{document.body.classList.remove('native');document.getElementById('reading-native').setAttribute('aria-pressed','false');document.getElementById('reading-phone').setAttribute('aria-pressed','true')};
</script></html>'''
    if output.exists():raise ValueError('Reading HTML output must be new')
    output.parent.mkdir(parents=True,exist_ok=True);output.write_text(doc,encoding='utf-8')
    return {'output':str(output),'rendered_page_sha256':digest,'reading_regions':manifest,'full_spread_phone_legibility':'requires_zoom; not certified by regional checks','visual_review':'pending'}

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('final');p.add_argument('report');p.add_argument('regions',type=Path);p.add_argument('output');a=p.parse_args()
    try:print(json.dumps(build(a.final,a.report,json.loads(a.regions.read_bytes()),a.output),ensure_ascii=False))
    except (ValueError,KeyError,TypeError,OSError) as e:p.exit(2,str(e)+'\n')
