#!/usr/bin/env python3
"""Replay local clone/fill edits through an actual reviewed mask; no invented redraw."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from PIL import Image, ImageDraw, ImageChops, ImageColor

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def asset(root,value):
    if not isinstance(value,str) or not value or Path(value).is_absolute():raise ValueError('Expected project-relative asset')
    p=(root/value).resolve()
    if not p.is_relative_to(root) or not p.is_file() or p.stat().st_size>64*1024*1024:raise ValueError('Missing/oversized asset or path escapes project')
    return p
def dump(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

def run(job_path,out):
    job_path=Path(job_path).resolve();out=Path(out)
    if out.exists() or out.is_symlink():raise ValueError('Retouch output must be new')
    if job_path.stat().st_size>4*1024*1024:raise ValueError('Retouch job exceeds 4 MiB')
    j=json.loads(job_path.read_bytes());root=job_path.parent
    if not isinstance(j,dict) or set(j)-{'schema_version','source','source_sha256','mask','mask_reviewed','mask_evidence','operations','patch','protected_masks'} or j.get('schema_version')!=1:raise ValueError('Invalid retouch job')
    src=asset(root,j.get('source'));mask_path=asset(root,j.get('mask'))
    if j.get('source_sha256')!=sha(src):raise ValueError('Stale source_sha256; recheck actual original')
    if j.get('mask_reviewed') is not True or not isinstance(j.get('mask_evidence'),str) or not j['mask_evidence'].strip():raise ValueError('Reviewed mask with concrete evidence required')
    with Image.open(src) as im:
        if im.width*im.height>40_000_000 or getattr(im,'n_frames',1)!=1:raise ValueError('Oversized or animated source')
        source=im.convert('RGBA')
    with Image.open(mask_path) as im:
        if im.format!='PNG' or im.mode not in {'L','1'} or im.size!=source.size:raise ValueError('Expected full-size binary grayscale PNG mask')
        mask=im.convert('L')
    if any(n for v,n in enumerate(mask.histogram()) if v not in {0,255}):raise ValueError('Mask must contain only 0 and 255')
    active=mask.histogram()[255]
    if not 0<active<source.width*source.height*.9:raise ValueError('Empty or overly broad mask')
    if ('patch' in j)==('operations' in j):raise ValueError('Choose imported patch OR clone/fill operations')
    current=source.copy();touched=Image.new('L',source.size);regions=[];inputs={j['source']:sha(src),j['mask']:sha(mask_path)}
    protected_files=j.get('protected_masks',[])
    if not isinstance(protected_files,list) or len(protected_files)>100:raise ValueError('Expected at most 100 protected_masks')
    protected=Image.new('L',source.size)
    for filename in protected_files:
        p=asset(root,filename)
        with Image.open(p) as im:
            if im.format!='PNG' or im.mode not in {'L','1'} or im.size!=source.size:raise ValueError('Expected full-size binary grayscale protected mask PNG')
            pm=im.convert('L')
        if any(n for v,n in enumerate(pm.histogram()) if v not in {0,255}):raise ValueError('Protected mask must contain only 0 and 255')
        protected=ImageChops.lighter(protected,pm);inputs[filename]=sha(p)
    if 'patch' in j:
        p=asset(root,j['patch'])
        with Image.open(p) as im:
            if im.size!=source.size:raise ValueError('Patch dimensions differ; no resize or alignment is performed')
            patch=im.convert('RGBA')
        if patch.getchannel('A').getextrema()!=(255,255):raise ValueError('Retouch patch must be opaque; transparent lettering is not cleanup')
        current=Image.composite(patch,source,mask);touched=mask.copy();inputs[j['patch']]=sha(p);regions=[{'id':'patch','box':list(mask.getbbox()),'operation':'imported_patch','inside_mask_review':'pending'}]
    else:
        ops=j['operations']
        if not isinstance(ops,list) or not 1<=len(ops)<=2000:raise ValueError('Expected 1..2000 clone/fill operations')
        for i,op in enumerate(ops):
            if not isinstance(op,dict) or set(op)-{'kind','target','source','radius','color'}:raise ValueError('Invalid operation fields')
            radius=op.get('radius');target=op.get('target')
            if type(radius)is not int or not 1<=radius<=128 or not isinstance(target,list) or len(target)!=2 or any(type(v)is not int for v in target):raise ValueError('Integer target and radius 1..128 required')
            x,y=target;box=(x-radius,y-radius,x+radius+1,y+radius+1);size=(radius*2+1,)*2
            if box[0]<0 or box[1]<0 or box[2]>source.width or box[3]>source.height:raise ValueError('Target brush leaves page; no clipping')
            brush=Image.new('L',size);ImageDraw.Draw(brush).ellipse((0,0,size[0]-1,size[1]-1),fill=255)
            brush=ImageChops.multiply(brush,mask.crop(box))
            if not brush.getbbox():raise ValueError('Brush does not intersect reviewed edit mask')
            if op.get('kind')=='clone':
                donor=op.get('source')
                if not isinstance(donor,list) or len(donor)!=2 or any(type(v)is not int for v in donor):raise ValueError('Clone source must be an integer pixel pair')
                sx,sy=donor;sb=(sx-radius,sy-radius,sx+radius+1,sy+radius+1)
                if sb[0]<0 or sb[1]<0 or sb[2]>source.width or sb[3]>source.height:raise ValueError('Clone donor leaves source')
                # Immutable donor avoids silently cloning earlier retouch mistakes.
                content=source.crop(sb)
            elif op.get('kind')=='fill':
                color=ImageColor.getcolor(op.get('color',''),'RGBA')
                if color[3]!=255:raise ValueError('Flat fills must be opaque')
                content=Image.new('RGBA',size,color)
            else:raise ValueError('Operation must be clone or fill')
            current.paste(content,box[:2],brush);touched.paste(ImageChops.lighter(touched.crop(box),brush),box[:2])
            regions.append({'id':f'edit-{i+1:04d}','box':list(box),'operation':op['kind'],'donor':op.get('source'),'inside_mask_review':'pending'})
    diff=ImageChops.difference(source,current);changed=diff.getchannel('R')
    for c in 'GBA':changed=ImageChops.lighter(changed,diff.getchannel(c))
    changed=changed.point(lambda v:255 if v else 0)
    protected_changes=ImageChops.multiply(changed,protected).histogram()[255]
    if protected_changes:raise ValueError(f'Retouch changes protected artwork: {protected_changes} pixels')
    outside=ImageChops.multiply(changed,ImageChops.invert(mask)).histogram()[255]
    if outside:raise AssertionError('Retouch changed protected pixels')
    if not changed.getbbox():raise ValueError('No decoded change; retouch is incomplete or unnecessary')
    out.mkdir(parents=True);source.save(out/'source.png');current.save(out/'cleaned.png');mask.save(out/'mask.png');touched.save(out/'touched-mask.png');changed.save(out/'changed-mask.png')
    # Keep original input assets + job fingerprints with the exported local evidence.
    check={'schema_version':1,'pages':[{'id':'page','original':'source.png','cleaned':'cleaned.png','mask':'mask.png','mask_reviewed':True,'mask_evidence':j['mask_evidence']}]};dump(out/'cleaning-job.json',check)
    checker=Path(__file__).resolve().parents[2]/'manga-cleaning/scripts/check_cleaning.py'
    r=subprocess.run([sys.executable,str(checker),str(out/'cleaning-job.json'),'--report',str(out/'cleaning-report.json')],capture_output=True,text=True,timeout=120)
    (out/'check.log').write_text(r.stdout+'\n'+r.stderr,encoding='utf-8')
    report={'schema_version':1,'job_sha256':sha(job_path),'source_sha256':sha(src),'cleaned_sha256':sha(out/'cleaned.png'),'source_dimensions':list(source.size),'inputs':inputs,'changed_pixels':changed.histogram()[255],'outside_mask_changes':outside,'protected_artwork_changes':protected_changes,'protected_masks':{f:inputs[f] for f in protected_files},'existing_checker_exit_code':r.returncode,'regions':regions,'manual_art_review':'pending','limits':['Immutable clone donors preserve sampled source pixels, not hidden original artwork','Seams, texture direction, residual glyphs and reconstructed geometry need actual visual inspection','Imported patches are constrained to the supplied mask; inside-mask authenticity is unverified']};dump(out/'retouch-report.json',report)
    return report

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('job',type=Path);p.add_argument('output',type=Path);a=p.parse_args()
    try:r=run(a.job,a.output);print(json.dumps({'outside_mask_changes':r['outside_mask_changes'],'changed_pixels':r['changed_pixels'],'manual_art_review':'pending','checker_exit_code':r['existing_checker_exit_code']}));sys.exit(0 if r['existing_checker_exit_code']==0 else 1)
    except (OSError,ValueError,KeyError,TypeError,subprocess.TimeoutExpired) as e:print(str(e),file=sys.stderr);sys.exit(2)
