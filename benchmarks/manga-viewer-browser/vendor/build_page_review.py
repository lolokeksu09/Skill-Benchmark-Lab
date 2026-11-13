#!/usr/bin/env python3
"""Self-contained, pixel-aligned visual reviewer for a manga-page draft.

It is not an OCR, translation, or visual-QC pass; the reviewer must inspect it.
"""
import argparse
import base64
import hashlib
import html
import json
from io import BytesIO
from pathlib import Path
from PIL import Image, ImageChops


def png_url(image):
    out=BytesIO()
    image.save(out,format='PNG')
    return 'data:image/png;base64,'+base64.b64encode(out.getvalue()).decode('ascii')


def open_rgba(file):
    with Image.open(file) as im:
        return im.convert('RGBA')


def make_review(source_file, cleaned_file, final_file, report_file, output_html):
    images=[open_rgba(file) for file in (source_file,cleaned_file,final_file)]
    src,cleaned,final=images
    if src.size!=cleaned.size or src.size!=final.size:
        raise ValueError('Review images do not have identical source pixel dimensions')
    report=json.loads(Path(report_file).read_text(encoding='utf8'))
    sha=hashlib.sha256(Path(source_file).read_bytes()).hexdigest()
    if report.get('source_image_sha256')!=sha:
        raise ValueError('Review report does not match original source SHA-256')
    final_sha=hashlib.sha256(Path(final_file).read_bytes()).hexdigest()
    if report.get('rendered_page_sha256')!=final_sha:
        raise ValueError('Review report does not match rendered PNG SHA-256')
    cleaned_sha=hashlib.sha256(Path(cleaned_file).read_bytes()).hexdigest()
    if report.get('cleaned_image_sha256')!=cleaned_sha:raise ValueError('Review report does not match cleaned image SHA-256')
    # This is a VISUAL diff preview. Changes include authorized lettering and cleaning.
    diff=ImageChops.difference(src,final)
    alpha=ImageChops.lighter(ImageChops.lighter(diff.getchannel('R'),diff.getchannel('G')),
                            ImageChops.lighter(diff.getchannel('B'),diff.getchannel('A')))
    overlay=Image.new('RGBA',src.size,(255,20,45,0))
    overlay.putalpha(alpha.point(lambda v: 140 if v else 0))
    source_url,clean_url,final_url,diff_url=[png_url(x) for x in (src,cleaned,final,overlay)]
    cd=ImageChops.difference(src,cleaned);ca=cd.getchannel('R')
    for c in 'GBA':ca=ImageChops.lighter(ca,cd.getchannel(c))
    co=Image.new('RGBA',src.size,(255,20,45,0));co.putalpha(ca.point(lambda v:140 if v else 0));clean_diff_url=png_url(co)
    notes=report.get('issues_pending') or []
    notes_html=''.join('<li>'+html.escape(str(x),quote=True)+'</li>' for x in notes)
    regions=report.get('review_regions',[])
    if not isinstance(regions,list) or len(regions)>200:raise ValueError('Invalid review_regions')
    region_html=[];region_ids=[]
    for i,r in enumerate(regions):
        box=r.get('box');ident=r.get('id')
        if not isinstance(ident,str) or not ident or ident in region_ids or not isinstance(box,list) or len(box)!=4 or any(type(v)is not int for v in box) or not 0<=box[0]<box[2]<=src.width or not 0<=box[1]<box[3]<=src.height:raise ValueError('Invalid review region bounds/ID')
        region_ids.append(ident);margin=8;b=[max(0,box[0]-margin),max(0,box[1]-margin),min(src.width,box[2]+margin),min(src.height,box[3]+margin)]
        pics=''.join('<figure><figcaption>'+label+'</figcaption><img alt="'+label+'" src="'+png_url(im.crop(b))+'"></figure>' for label,im in zip(['Оригинал','Клининг','Перевод'],images))
        region_html.append('<article><h3>'+html.escape(ident)+'</h3><div class="crops">'+pics+'</div><label><input type="checkbox" data-region="'+str(i)+'"> Осмотрел участок внутри маски</label><textarea data-region-note="'+str(i)+'" placeholder="Остатки букв, швы, линии, фактура и перекрытия"></textarea></article>')
    checks={'source_transcription':'Исходные надписи и полнота описи','translation_fidelity':'Смысл перевода по доступному исходнику','rendered_words':'Слова на изображении совпадают с утверждённым текстом','source_letter_residue':'Не осталось исходных букв','art_inside_mask':'Ретушь внутри масок и сохранность линий','optical_layout':'Шрифты, переносы, отступы и акценты','phone_reading':'Чтение при ширине телефона'}
    check_html=''.join('<label><input type="checkbox" data-check="'+k+'"> '+v+'</label><textarea data-note="'+k+'" placeholder="Краткое основание отметки"></textarea>' for k,v in checks.items())
    binding={k:report.get(k) for k in ['source_image_sha256','cleaned_image_sha256','rendered_page_sha256','inventory_sha256','reading_regions','dialogue_reading_regions']};binding['review_regions']=regions
    payload=json.dumps({'schema_version':1,'binding':binding,'checks':{k:{'reviewed':False,'evidence':''} for k in checks},'regions':[{'id':r['id'],'reviewed':False,'evidence':''} for r in regions],'review_type':'self_report','independent_review':False},ensure_ascii=False).replace('<','\\u003c')
    content=f'''<!doctype html>
<html lang="ru"><head><meta charset="utf-8"/><meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>Manga Translation Studio — review draft</title>
<style>
:root{{--bg:#111317;--panel:#1c2025;--line:#343b42;--text:#f4f4f0;--muted:#a4afb9;--accent:#ecb96a}}
*{{box-sizing:border-box}}body{{background:var(--bg);color:var(--text);font:15px/1.5 system-ui,sans-serif;margin:0}}
main{{max-width:1080px;margin:auto;padding:24px 16px 55px}}h1{{font-size:22px;margin:0 0 8px}}p,small{{color:var(--muted)}}
section{{background:var(--panel);padding:16px;border:1px solid var(--line);border-radius:14px;margin:18px 0}}
.controls{{display:flex;flex-wrap:wrap;align-items:center;gap:10px;margin-bottom:15px}}
button{{background:#292f37;color:#fff;border:1px solid var(--line);border-radius:9px;padding:10px 14px;cursor:pointer}}
button[aria-pressed="true"]{{border-color:var(--accent);color:var(--accent)}}
input[type="range"]{{accent-color:var(--accent);width:min(340px,100%)}}
.viewport{{width:100%;max-width:850px;margin:auto;border:1px solid var(--line);overflow:hidden;position:relative}}
.viewport.phone{{max-width:390px}} .viewport.actual{{width:{src.width}px;max-width:none}} .stage{{position:relative;width:100%}}
.pan{{overflow:auto}}.crops{{display:flex;gap:10px;overflow:auto}}figure{{margin:0;flex:none}}figure img{{display:block;max-width:340px;height:auto}}textarea{{display:block;width:100%;min-height:50px;margin:6px 0 14px;background:#111317;color:white;border:1px solid #59616b}}.checklist label{{display:block}}article{{margin:15px 0;padding:12px;border:1px solid var(--line)}}
.stage img{{width:100%;height:auto;display:block}}.stage .top{{position:absolute;inset:0;clip-path:inset(0 50% 0 0)}}
.stage .diff{{position:absolute;inset:0;pointer-events:none;display:none}}
.divider-line{{position:absolute;left:50%;top:0;bottom:0;border-left:2px solid var(--accent);pointer-events:none}}
.info{{font-variant-numeric:tabular-nums;overflow-wrap:anywhere}}ul{{padding-left:1.3em}}li{{padding:2px 0}}footer{{color:var(--muted);margin-top:20px}}
</style></head><body><main>
<h1>Проверка страницы — черновик</h1>
<p>Сдвигайте разделитель для попиксельной сверки. Красная подсветка показывает все отличия, включая законный тайпсеттинг, а не только ошибки.</p>
<section><div class="controls">
<button id="clean" aria-pressed="false">Оригинал / клининг</button>
<button id="final" aria-pressed="true">Оригинал / перевод</button>
<button id="phone" aria-pressed="false">Ширина телефона 390 px</button>
<button id="actual" aria-pressed="false">100% — исходные пиксели</button>
<button id="diffbutton" aria-pressed="false">Показать изменения</button>
<label>Сравнение <input type="range" id="split" value="50" min="0" max="100"/></label>
</div>
<div class="pan"><div class="viewport" id="viewport"><div class="stage"><img id="base" alt="Оригинал" src="{source_url}"/>
<img class="top" id="top" alt="Черновик" src="{final_url}"/>
<img class="diff" id="diff" alt="Подсветка изменений" src="{diff_url}"/><div class="divider-line" id="divider"></div></div></div></div>
<p class="info">Размер исходника: {src.width} × {src.height} px · SHA-256: {sha}</p>
</section>
<section><h2>Требует ручной проверки</h2><ul>{notes_html}</ul>
<p>Технический отчёт не подтверждает точность перевода, отсутствие остатков исходных букв или художественную достоверность ретуши внутри масок.</p></section>
<section><h2>Участки правок</h2>{''.join(region_html)}</section>
<section class="checklist"><h2>Сохранить фактическую сверку</h2><p>Отмечайте только выполненные проверки и укажите основание. Экспорт привязан к конкретным исходнику, клинингу и переводу; он не подтверждает независимую экспертизу.</p>{check_html}<button id="export-review">Сохранить сверку JSON</button><p id="review-status" role="status"></p></section>
<footer>Локальный HTML без сетевых ресурсов. Сохранённые отметки требуют проверки актуальности; изображение не изменяется.</footer>
</main><script>
const input=document.getElementById('split'),topImage=document.getElementById('top'),line=document.getElementById('divider');
function setSplit(){{const n=Number(input.value);topImage.style.clipPath=`inset(0 ${{100-n}}% 0 0)`;line.style.left=n+'%'}}
input.addEventListener('input',setSplit);setSplit();
for(const id of ['clean','final'])document.getElementById(id).addEventListener('click',()=>{{
 topImage.src=id==='clean'?'{clean_url}':'{final_url}';
 document.getElementById('diff').src=id==='clean'?'{clean_diff_url}':'{diff_url}';
 document.getElementById('clean').setAttribute('aria-pressed',String(id==='clean'));
 document.getElementById('final').setAttribute('aria-pressed',String(id==='final'));
}});
document.getElementById('phone').addEventListener('click',e=>{{
 const v=document.getElementById('viewport');v.classList.remove('actual');document.getElementById('actual').setAttribute('aria-pressed','false');const on=v.classList.toggle('phone');e.target.setAttribute('aria-pressed',String(on))}});
document.getElementById('actual').addEventListener('click',e=>{{const v=document.getElementById('viewport');v.classList.remove('phone');document.getElementById('phone').setAttribute('aria-pressed','false');const on=v.classList.toggle('actual');e.target.setAttribute('aria-pressed',String(on))}});
document.getElementById('diffbutton').addEventListener('click',e=>{{
 const d=document.getElementById('diff');const on=d.style.display!=='block';d.style.display=on?'block':'none';
 e.target.setAttribute('aria-pressed',String(on));}});
const REVIEW_TEMPLATE={payload};
document.getElementById('export-review').addEventListener('click',()=>{{
 const r=JSON.parse(JSON.stringify(REVIEW_TEMPLATE));document.querySelectorAll('[data-check]').forEach(e=>{{r.checks[e.dataset.check].reviewed=e.checked}});document.querySelectorAll('[data-note]').forEach(e=>{{r.checks[e.dataset.note].evidence=e.value.trim()}});document.querySelectorAll('[data-region]').forEach(e=>{{r.regions[Number(e.dataset.region)].reviewed=e.checked}});document.querySelectorAll('[data-region-note]').forEach(e=>{{r.regions[Number(e.dataset.regionNote)].evidence=e.value.trim()}});
 const u=URL.createObjectURL(new Blob([JSON.stringify(r,null,2)],{{type:'application/json'}}));const a=document.createElement('a');a.href=u;a.download='page-review.json';a.click();setTimeout(()=>URL.revokeObjectURL(u),1000);document.getElementById('review-status').textContent='Сверка экспортирована. Проверьте её актуальность через check_page_review.py.';
}});
</script></body></html>'''
    output_html=Path(output_html)
    output_html.parent.mkdir(parents=True,exist_ok=True)
    output_html.write_text(content,encoding='utf8')
    return {'status':'generated_manual_viewer','output':str(output_html),
            'source_dimensions':list(src.size),'external_assets':0,
            'manual_review_performed':False,'source_sha256':sha}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--original',required=True)
    p.add_argument('--cleaned',required=True)
    p.add_argument('--final',required=True)
    p.add_argument('--report',required=True)
    p.add_argument('--output',required=True)
    a=p.parse_args()
    try:
        result=make_review(a.original,a.cleaned,a.final,a.report,a.output)
        print(json.dumps(result,ensure_ascii=False))
    except (ValueError,OSError,KeyError) as e:
        p.exit(2,f'Review viewer blocked: {e}\n')

if __name__=='__main__':main()
