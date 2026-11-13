#!/usr/bin/env python3
"""Validate recorded human checks against exact current assets; never performs them."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

CHECKS={'source_transcription','translation_fidelity','rendered_words','source_letter_residue','art_inside_mask','optical_layout','phone_reading'}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def check(report_path,evidence_path,source,cleaned,final):
    report=json.loads(report_path.read_bytes());review=json.loads(evidence_path.read_bytes());problems=[]
    if not isinstance(review,dict) or review.get('schema_version')!=1:raise ValueError('Invalid review evidence')
    binding={k:report.get(k) for k in ['source_image_sha256','cleaned_image_sha256','rendered_page_sha256','inventory_sha256','reading_regions','dialogue_reading_regions']};binding['review_regions']=report.get('review_regions',[])
    if review.get('binding')!=binding:problems.append('review_binding_changed; repeat review for current images/inventory/regions')
    ledger=report.get('inventory_review_status')
    if not isinstance(ledger,list) or not ledger:problems.append('inventory_review_status_unavailable; regenerate current page report')
    else:
        for item in ledger:
            if not isinstance(item,dict) or item.get('source_reviewed')is not True or item.get('handling')=='unreadable' or (item.get('handling')=='translate' and item.get('translation_approved')is not True):problems.append('inventory_item_unresolved: '+str(item.get('id') if isinstance(item,dict) else '?'))
    for key,path in [('source_image_sha256',source),('cleaned_image_sha256',cleaned),('rendered_page_sha256',final)]:
        if report.get(key)!=sha(path):problems.append('asset_hash_mismatch: '+key)
    checks=review.get('checks')
    if not isinstance(checks,dict) or set(checks)!=CHECKS:problems.append('missing_or_unknown_manual_check_categories');checks={}
    for key in CHECKS:
        v=checks.get(key,{})
        if not isinstance(v,dict) or v.get('reviewed')is not True or not isinstance(v.get('evidence'),str) or not v['evidence'].strip():problems.append('manual_check_pending: '+key)
    expected={r['id'] for r in binding['review_regions']};seen=set()
    regions=review.get('regions',[])
    if not isinstance(regions,list):regions=[];problems.append('invalid_region_reviews')
    for r in regions:
        if not isinstance(r,dict) or r.get('id') not in expected or r.get('id') in seen:problems.append('unknown_or_duplicate_region_review');continue
        seen.add(r['id'])
        if r.get('reviewed')is not True or not isinstance(r.get('evidence'),str) or not r['evidence'].strip():problems.append('region_review_pending: '+r['id'])
    if seen!=expected:problems.append('missing_region_reviews')
    return {'schema_version':1,'recorded_review_complete':not problems,'findings':problems,'evidence_sha256':sha(evidence_path),'report_sha256':sha(report_path),'review_performed_by_checker':False,'independent_review_verified':False,'release_ready':False,'scope':'Validates current hashes and recorded review entries only; no automatic language/art validation or chapter release approval.'}

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('report',type=Path);p.add_argument('evidence',type=Path);p.add_argument('--source',required=True,type=Path);p.add_argument('--cleaned',required=True,type=Path);p.add_argument('--final',required=True,type=Path);a=p.parse_args()
    try:r=check(a.report,a.evidence,a.source,a.cleaned,a.final);print(json.dumps(r,ensure_ascii=False,indent=2));sys.exit(0 if r['recorded_review_complete'] else 1)
    except (ValueError,KeyError,TypeError,OSError) as e:print(str(e),file=sys.stderr);sys.exit(2)
