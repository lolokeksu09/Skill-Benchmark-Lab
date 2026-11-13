#!/usr/bin/env python3
"""Compare decoded image pixels outside separately reviewed cleanup masks. Never edits images."""
import argparse
import hashlib
import json
import sys
from pathlib import Path

MAX_BYTES = 64 * 1024 * 1024
MAX_PIXELS = 40_000_000


def sha(raw): return hashlib.sha256(raw).hexdigest()


def asset(base, value):
    if not isinstance(value, str) or not value: raise ValueError('Expected a relative local asset path')
    if Path(value).is_absolute(): raise ValueError('Asset paths must be relative to the job')
    path = (base / value).resolve()
    if not path.is_relative_to(base.resolve()): raise ValueError('Asset path escapes job directory')
    if not path.is_file() or path.stat().st_size > MAX_BYTES: raise ValueError('Missing or oversized asset')
    return path


def read_image(path, mask=False):
    from io import BytesIO
    from PIL import Image
    raw = path.read_bytes()
    with Image.open(BytesIO(raw)) as image:
        if image.width * image.height > MAX_PIXELS or getattr(image, 'n_frames', 1) != 1:
            raise ValueError('Image exceeds pixel limit or is animated')
        image.load()
        if mask:
            if image.format != 'PNG' or image.mode not in {'1', 'L'}: raise ValueError('Edit mask must be grayscale PNG (mode 1 or L)')
            result = image.convert('L')
            if any(count for i, count in enumerate(result.histogram()) if i not in {0, 255}): raise ValueError('Edit mask must contain only 0 and 255')
        else: result = image.convert('RGBA')
    return result, sha(raw)


def inspect_job(manifest):
    if manifest.stat().st_size > 4 * 1024 * 1024: raise ValueError('Job JSON exceeds 4 MiB')
    raw = manifest.read_bytes(); job = json.loads(raw)
    if not isinstance(job, dict) or type(job.get('schema_version')) is not int or job['schema_version'] != 1: raise ValueError('Expected job schema_version 1')
    pages = job.get('pages')
    if not isinstance(pages, list) or not pages or len(pages) > 200: raise ValueError('Expected 1..200 pages')
    protected = {manifest.resolve()}
    for page in pages:
        if not isinstance(page, dict): raise ValueError('Page must be an object')
        protected.update(asset(manifest.parent, page.get(key)) for key in ('original', 'cleaned', 'mask'))
    try:
        from PIL import ImageChops
    except ImportError:
        return {'report_type': 'cleaning_mask_qc', 'schema_version': 1, 'passed': False, 'status': 'not_performed', 'error': 'Pillow is unavailable', 'pages': []}, protected
    report = {'report_type': 'cleaning_mask_qc', 'schema_version': 1, 'passed': False, 'status': 'needs_review', 'manifest_sha256': sha(raw), 'pages': [],
              'scope': 'Exact decoded RGBA pixel preservation outside supplied masks only. Mask correctness, text removal and reconstructed art inside masks require visual review.'}
    ids = set()
    total_pixels = 0
    for page in pages:
        if not isinstance(page, dict) or not isinstance(page.get('id'), str) or not page['id'].strip() or page['id'] in ids: raise ValueError('Each page needs a unique nonblank id')
        ident = page['id']; ids.add(ident)
        paths = {key: asset(manifest.parent, page.get(key)) for key in ('original', 'cleaned', 'mask')}; protected.update(paths.values())
        original, original_hash = read_image(paths['original']); cleaned, cleaned_hash = read_image(paths['cleaned']); mask, mask_hash = read_image(paths['mask'], True)
        if original.size != cleaned.size or mask.size != original.size: raise ValueError(f'{ident}: dimensions differ; no automatic resize or alignment is allowed')
        total_pixels += original.width * original.height
        if total_pixels > 400_000_000: raise ValueError('Job exceeds total page pixel limit')
        hist = mask.histogram(); masked = hist[255]; pixels = original.width * original.height
        findings = []
        reviewed = page.get('mask_reviewed') is True and isinstance(page.get('mask_evidence'), str) and bool(page['mask_evidence'].strip())
        if not reviewed: findings.append({'code': 'mask_unreviewed', 'detail': 'Review the mask against the source and document evidence'})
        if masked == pixels: findings.append({'code': 'mask_covers_entire_page', 'detail': 'No protected artwork remains for comparison'})
        # Include alpha, even when a hidden RGB value is different under transparent pixels.
        delta = ImageChops.difference(original, cleaned)
        channels = delta.split(); greatest = channels[0]
        for channel in channels[1:]: greatest = ImageChops.lighter(greatest, channel)
        changed = greatest.point(lambda v: 255 if v else 0)
        outside = ImageChops.multiply(changed, ImageChops.invert(mask))
        outside_count = outside.histogram()[255]; changed_count = changed.histogram()[255]
        if outside_count: findings.append({'code': 'changed_outside_mask', 'detail': 'Decoded pixels outside the allowed cleanup region changed', 'pixels': outside_count, 'box': outside.getbbox()})
        if not changed_count and masked: findings.append({'code': 'no_changes_in_requested_cleanup', 'detail': 'A nonempty cleanup mask was supplied but decoded pixels did not change'})
        record = {'id': ident, 'passed': not findings, 'size': list(original.size), 'mask_reviewed': reviewed, 'masked_pixels': masked,
                  'changed_pixels': changed_count, 'changed_outside_mask': outside_count, 'outside_change_box': outside.getbbox(),
                  'sha256': {'original': original_hash, 'cleaned': cleaned_hash, 'mask': mask_hash}, 'findings': findings}
        report['pages'].append(record)
    report['passed'] = all(p['passed'] for p in report['pages'])
    report['status'] = 'passed' if report['passed'] else 'needs_review'
    return report, protected


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('job', type=Path); parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    try:
        report, inputs = inspect_job(args.job)
        if args.report:
            if args.report.resolve() in inputs or args.report.resolve() == args.job.resolve(): raise ValueError('Report cannot overwrite any input')
            if args.report.is_symlink(): raise ValueError('Report cannot replace a symlink')
            args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        print(json.dumps(report, ensure_ascii=False, indent=2)); return 0 if report['passed'] else 1
    except (OSError, ValueError, TypeError, KeyError, ImportError) as exc:
        print(json.dumps({'report_type': 'cleaning_mask_qc', 'schema_version': 1, 'passed': False, 'status': 'error', 'error': str(exc), 'pages': []}, ensure_ascii=False), file=sys.stderr); return 2

if __name__ == '__main__': raise SystemExit(main())
