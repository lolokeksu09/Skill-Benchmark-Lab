#!/usr/bin/env python3
"""Compare visually authored source regions with OCR guesses; export corrected inventory."""
import argparse
import hashlib
import html
import json
from pathlib import Path
from PIL import Image
from build_page_review import png_url

def build(source_path,inventory_path,output,ocr=None):
    source_path,inventory_path,output=map(Path,(source_path,inventory_path,output))
    inventory=json.loads(inventory_path.read_bytes());digest=hashlib.sha256(source_path.read_bytes()).hexdigest()
    with Image.open(source_path) as im:
        if im.width*im.height>40_000_000:raise ValueError('Source too large')
        source=im.convert('RGBA')
    if inventory.get('source_sha256')!=digest or inventory.get('source_dimensions')!=list(source.size):raise ValueError('Source inventory must be bound to current hash and dimensions')
    if ocr is not None and ocr.get('source_sha256')!=digest:raise ValueError('OCR is bound to a different source')
    regions=inventory.get('regions')
    if not isinstance(regions,list) or not 1<=len(regions)<=200:raise ValueError('Need 1..200 visually authored source regions, not a generated OCR inventory')
    cards=[];ids=set()
    for i,r in enumerate(regions):
        ident=r.get('id');box=r.get('box')
        if not isinstance(ident,str) or not ident or ident in ids:raise ValueError('Unique source IDs required')
        ids.add(ident)
        if not isinstance(box,list) or len(box)!=4 or any(type(v)is not int for v in box):raise ValueError('Source region requires integer xywh box')
        x,y,w,h=box
        if not 0<=x<x+w<=source.width or not 0<=y<y+h<=source.height:raise ValueError('Source region outside actual image')
        candidates=[]
        for c in (ocr or {}).get('regions',[]):
            cx,cy,cw,ch=c['box']
            if max(x,cx)<min(x+w,cx+cw) and max(y,cy)<min(y+h,cy+ch):
                candidates.append(str(c.get('source_text_candidate','')))
                candidates.extend(str(a.get('source_text_candidate','')) for a in c.get('alternatives',[]))
        options=''.join('<option value="'+v+'"'+(' selected' if r.get('handling')==v else '')+'>'+label+'</option>' for v,label in [('translate','Перевести'),('retain_original','Сохранить оригинал'),('unreadable','Не прочитано')])
        def esc(v):return html.escape(str(v or ''),quote=True)
        cards.append('<article data-index="'+str(i)+'"><h2>'+esc(ident)+'</h2><p>Координаты: '+str(box)+'</p><img class="crop" alt="Исходная надпись" src="'+png_url(source.crop((x,y,x+w,y+h)))+'"><p>Непроверенные варианты OCR: '+esc(' | '.join(candidates) or 'Нет кандидатов — область всё равно нужно прочитать')+'</p><label>Точная исходная надпись<textarea data-field="source_text">'+esc(r.get('source_text'))+'</textarea></label><label>Русский текст<textarea data-field="target_text">'+esc(r.get('target_text'))+'</textarea></label><label>Обработка<select data-field="handling">'+options+'</select></label><label>Причина сохранения / неопределённость<textarea data-field="retention_reason">'+esc(r.get('retention_reason'))+'</textarea></label><label><input type="checkbox" data-field="source_reviewed"> Сверено с исходным изображением</label><label><input type="checkbox" data-field="translation_approved"> Русский текст проверен по доступному исходнику</label></article>')
    base=dict(inventory);base['source_sha256']=digest;base['source_dimensions']=list(source.size);base['inventory_complete']=False;base['independent_review']=False
    data=json.dumps(base,ensure_ascii=False).replace('<','\\u003c')
    doc='''<!doctype html><html lang="ru"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Сверка исходных надписей</title><style>body{font:16px system-ui;margin:24px;background:#14171c;color:#eee}article{border:1px solid #59616b;padding:16px;margin:18px 0}label{display:block;margin:10px 0}textarea,select{display:block;width:95%;font:inherit}textarea{min-height:60px}.crop{max-width:100%;height:auto;image-rendering:auto}#whole{max-width:100%;height:auto}button{font:inherit;padding:12px;margin:10px}p{overflow-wrap:anywhere}</style><h1>Сверка исходных надписей</h1><p>Опись создана визуально, OCR показан только как набор догадок. Сверьте корейские звуки по самому изображению. Отсутствие рамки OCR не доказывает отсутствие текста. Пропущенные элементы добавьте в исходную опись и пересоздайте эту страницу.</p><button id="actual-source">100% исходника</button><div style="overflow:auto"><img id="whole" alt="Полный исходник" src="'''+png_url(source)+'''"></div>'''+''.join(cards)+'''<button id="export-source">Сохранить исправленную опись JSON</button><p id="status" role="status"></p><script>
const sourceInventory='''+data+''';document.getElementById('actual-source').onclick=()=>{const im=document.getElementById('whole');im.style.maxWidth=im.style.maxWidth==='none'?'100%':'none'};
document.getElementById('export-source').onclick=()=>{const r=JSON.parse(JSON.stringify(sourceInventory));document.querySelectorAll('article[data-index]').forEach(card=>{const region=r.regions[Number(card.dataset.index)];card.querySelectorAll('[data-field]').forEach(e=>{region[e.dataset.field]=e.type==='checkbox'?e.checked:e.value.trim()})});r.inventory_complete=false;r.independent_review=false;const u=URL.createObjectURL(new Blob([JSON.stringify(r,null,2)],{type:'application/json'}));const a=document.createElement('a');a.href=u;a.download='source-inventory-reviewed.json';a.click();setTimeout(()=>URL.revokeObjectURL(u),1000);document.getElementById('status').textContent='Опись экспортирована. Полнота всей страницы не подтверждена автоматически.'};
</script></html>'''
    if output.exists():raise ValueError('Output HTML must be new')
    output.parent.mkdir(parents=True,exist_ok=True);output.write_text(doc,encoding='utf-8')
    return {'regions':len(regions),'source_sha256':digest,'ocr_is_ground_truth':False,'inventory_complete':False,'output':str(output)}

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('source');p.add_argument('inventory');p.add_argument('output');p.add_argument('--ocr',type=Path);a=p.parse_args()
    try:print(json.dumps(build(a.source,a.inventory,a.output,json.loads(a.ocr.read_bytes()) if a.ocr else None),ensure_ascii=False))
    except (OSError,ValueError,KeyError,TypeError) as e:p.exit(2,str(e)+'\n')
