#!/usr/bin/env python3
"""Prepare a local mask/clone workbench or replay its source-bound native plan."""
import argparse
import hashlib
import json
import shutil
from pathlib import Path
from PIL import Image, ImageDraw
from build_page_review import png_url
from retouch_page import run as retouch, asset, dump


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def fresh(out):
    if out.exists() or out.is_symlink():
        raise ValueError('Output directory must be new')


def prepare(source_path, out):
    source_path, out = Path(source_path).resolve(), Path(out).resolve()
    fresh(out)
    if not source_path.is_file() or source_path.stat().st_size > 64*1024*1024:
        raise ValueError('Missing or oversized source')
    with Image.open(source_path) as im:
        if im.width*im.height > 40_000_000 or getattr(im, 'n_frames', 1) != 1:
            raise ValueError('Animated or oversized source')
        source = im.convert('RGBA')
    out.mkdir(parents=True)
    source.save(out/'source.png')
    plan = {'schema_version': 1, 'source': 'source.png', 'source_sha256': sha(out/'source.png'),
            'source_dimensions': list(source.size), 'mask_strokes': [], 'protected_strokes': [],
            'operations': [], 'mask_reviewed': False, 'mask_evidence': ''}
    data = json.dumps(plan, ensure_ascii=False).replace('<', '\\u003c')
    template = Path(__file__).with_name('retouch_workbench.html').read_text(encoding='utf-8')
    document = template.replace('__PLAN__', data).replace('__SOURCE__', png_url(source))
    (out/'retouch.html').write_text(document, encoding='utf-8')
    report = {'source_sha256': plan['source_sha256'], 'source_dimensions': list(source.size),
              'original_file_sha256': sha(source_path), 'source_normalization': 'Lossless RGBA PNG; no resize',
              'mask_reviewed': False, 'art_review': 'pending', 'output': str(out/'retouch.html')}
    dump(out/'preparation-report.json', report)
    return report


def rasterize(strokes, size):
    if not isinstance(strokes, list) or len(strokes) > 1000:
        raise ValueError('Expected at most 1000 mask strokes')
    mask = Image.new('L', size)
    draw = ImageDraw.Draw(mask)
    total = 0
    for stroke in strokes:
        if not isinstance(stroke, dict) or set(stroke) != {'radius', 'points'}:
            raise ValueError('Invalid mask stroke')
        radius, points = stroke['radius'], stroke['points']
        if type(radius) is not int or not 1 <= radius <= 128:
            raise ValueError('Integer stroke radius 1..128 required')
        if not isinstance(points, list) or not 1 <= len(points) <= 2000:
            raise ValueError('Expected 1..2000 native points per stroke')
        total += len(points)
        if total > 20000:
            raise ValueError('Too many mask points')
        for p in points:
            if not isinstance(p, list) or len(p) != 2 or any(type(v) is not int for v in p):
                raise ValueError('Mask coordinates must be integer pixel pairs')
            if not 0 <= p[0] < size[0] or not 0 <= p[1] < size[1]:
                raise ValueError('Mask point leaves native source')
        xy = [tuple(p) for p in points]
        if len(xy) > 1:
            draw.line(xy, fill=255, width=2*radius+1)
        for x, y in xy:
            draw.ellipse((x-radius, y-radius, x+radius, y+radius), fill=255)
    return mask


def apply(plan_path, out):
    plan_path, out = Path(plan_path).resolve(), Path(out).resolve()
    fresh(out)
    if plan_path.stat().st_size > 4*1024*1024:
        raise ValueError('Plan exceeds 4 MiB')
    j = json.loads(plan_path.read_bytes())
    keys = {'schema_version','source','source_sha256','source_dimensions','mask_strokes',
            'protected_strokes','operations','mask_reviewed','mask_evidence'}
    if not isinstance(j, dict) or set(j) != keys or type(j['schema_version']) is not int or j['schema_version'] != 1:
        raise ValueError('Invalid workbench plan')
    src = asset(plan_path.parent, j['source'])
    if sha(src) != j['source_sha256']:
        raise ValueError('Stale source_sha256')
    with Image.open(src) as im:
        if im.width*im.height > 40_000_000 or getattr(im,'n_frames',1) != 1:
            raise ValueError('Animated or oversized source')
        size = im.size
    if j['source_dimensions'] != list(size) or any(type(v) is not int for v in j['source_dimensions']):
        raise ValueError('Native dimensions changed')
    if j['mask_reviewed'] is not True or not isinstance(j['mask_evidence'], str) or not j['mask_evidence'].strip():
        raise ValueError('Reviewed mask and concrete evidence required')
    mask = rasterize(j['mask_strokes'], size)
    protected = rasterize(j['protected_strokes'], size)
    if not isinstance(j['operations'],list) or not 1 <= len(j['operations']) <= 2000:
        raise ValueError('Expected 1..2000 clone operations')
    # This UI exports immutable-source clones only; keep existing retouch validation authoritative.
    if any(not isinstance(op,dict) or op.get('kind') != 'clone' for op in j['operations']):
        raise ValueError('Workbench accepts clone operations only')
    out.mkdir(parents=True)
    shutil.copyfile(src, out/'source.png')
    mask.save(out/'mask.png'); protected.save(out/'protected.png')
    job = {'schema_version':1,'source':'source.png','source_sha256':sha(out/'source.png'),
           'mask':'mask.png','mask_reviewed':True,'mask_evidence':j['mask_evidence'],
           'protected_masks':['protected.png'],'operations':j['operations']}
    dump(out/'retouch-job.json',job)
    report = retouch(out/'retouch-job.json',out/'result')
    report.update({'workbench_plan_sha256':sha(plan_path), 'mask_rasterization':'Binary native-size Pillow line/circle strokes; browser preview is approximate',
                   'protected_mask_supplied':bool(protected.getbbox()), 'independent_review':False})
    dump(out/'workbench-report.json',report)
    return report


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode',choices=['prepare','apply']);parser.add_argument('input',type=Path);parser.add_argument('output',type=Path)
    args=parser.parse_args()
    try:
        r=(prepare if args.mode=='prepare' else apply)(args.input,args.output)
        print(json.dumps(r,ensure_ascii=False))
    except (OSError,ValueError,KeyError,TypeError) as e:
        parser.exit(2,str(e)+'\n')
