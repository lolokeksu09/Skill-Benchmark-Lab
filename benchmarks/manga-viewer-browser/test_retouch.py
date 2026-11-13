"""Synthetic contract/negative tests; no human review or retouch-quality certification."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from PIL import Image,ImageDraw
from retouch_page import run as retouch
from check_page_review import check,CHECKS
from build_transcription_review import build

class ReviewRetouchTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        im=Image.new('RGB',(200,140),'#d2e5f7');ImageDraw.Draw(im).rectangle((80,70,110,100),fill='black');im.save(self.root/'source.png')
        m=Image.new('L',im.size);ImageDraw.Draw(m).rectangle((78,68,112,102),fill=255);m.save(self.root/'mask.png')
        self.hash=hashlib.sha256((self.root/'source.png').read_bytes()).hexdigest()
        self.job={'schema_version':1,'source':'source.png','source_sha256':self.hash,'mask':'mask.png','mask_reviewed':True,'mask_evidence':'Synthetic rectangle mask, not a real art review','operations':[{'kind':'clone','source':[40,40],'target':[95,85],'radius':25}]}
    def write(self,name,data):
        p=self.root/name;p.write_text(json.dumps(data,ensure_ascii=False));return p
    def test_clone_preserves_every_protected_pixel(self):
        r=retouch(self.write('job.json',self.job),self.root/'out');self.assertEqual(r['outside_mask_changes'],0);self.assertEqual(r['existing_checker_exit_code'],0);self.assertEqual(r['manual_art_review'],'pending')
        original=Image.open(self.root/'source.png').convert('RGBA');result=Image.open(self.root/'out/cleaned.png');mask=Image.open(self.root/'mask.png')
        self.assertTrue(all(original.getpixel((x,y))==result.getpixel((x,y)) for y in range(140) for x in range(200) if not mask.getpixel((x,y))))
        self.assertEqual(result.getpixel((95,85)),original.getpixel((40,40)))
    def test_retouch_rejects_stale_source(self):
        self.job['source_sha256']='0'*64
        with self.assertRaisesRegex(ValueError,'Stale'):retouch(self.write('job.json',self.job),self.root/'out')
    def test_retouch_rejects_unreviewed_mask(self):
        self.job['mask_reviewed']=False
        with self.assertRaisesRegex(ValueError,'Reviewed mask'):retouch(self.write('job.json',self.job),self.root/'out')
    def test_retouch_rejects_outside_donor(self):
        self.job['operations'][0]['source']=[0,0]
        with self.assertRaisesRegex(ValueError,'donor leaves'):retouch(self.write('job.json',self.job),self.root/'out')
    def test_imported_patch_has_no_implicit_resize(self):
        del self.job['operations'];self.job['patch']='patch.png';Image.new('RGB',(100,70)).save(self.root/'patch.png')
        with self.assertRaisesRegex(ValueError,'dimensions differ'):retouch(self.write('job.json',self.job),self.root/'out')
    def protect(self,xy):
        pm=Image.new('L',(200,140));pm.putpixel(xy,255);pm.save(self.root/'protected.png');self.job['protected_masks']=['protected.png']
    def test_clone_rejects_changed_protected_pixel_inside_edit_mask(self):
        self.protect((95,85))
        with self.assertRaisesRegex(ValueError,'changes protected artwork: 1 pixels'):
            retouch(self.write('job.json',self.job),self.root/'out')
        self.assertFalse((self.root/'out').exists())
    def test_imported_patch_rejects_changed_protected_pixel(self):
        self.protect((95,85));del self.job['operations'];self.job['patch']='patch.png'
        im=Image.open(self.root/'source.png');im.putpixel((95,85),(255,0,0));im.save(self.root/'patch.png')
        with self.assertRaisesRegex(ValueError,'changes protected artwork: 1 pixels'):
            retouch(self.write('job.json',self.job),self.root/'out')
    def test_overlapping_protected_mask_allows_unchanged_pixels(self):
        self.protect((78,68))
        r=retouch(self.write('job.json',self.job),self.root/'out')
        self.assertEqual(r['protected_artwork_changes'],0)
        self.assertEqual(r['protected_masks']['protected.png'],hashlib.sha256((self.root/'protected.png').read_bytes()).hexdigest())
    def test_nonbinary_protected_mask_rejected(self):
        self.protect((95,85));im=Image.open(self.root/'protected.png');im.putpixel((0,0),128);im.save(self.root/'protected.png')
        with self.assertRaisesRegex(ValueError,'Protected mask must contain'):
            retouch(self.write('job.json',self.job),self.root/'out')
    def test_fill_rejects_changed_protected_pixel(self):
        self.protect((95,85));self.job['operations']=[{'kind':'fill','target':[95,85],'radius':4,'color':'white'}]
        with self.assertRaisesRegex(ValueError,'changes protected artwork'):
            retouch(self.write('job.json',self.job),self.root/'out')
    def evidence(self):
        b={k:self.hash for k in ['source_image_sha256','cleaned_image_sha256','rendered_page_sha256']};b['inventory_sha256']='synthetic-inventory';b['reading_regions']=None;b['dialogue_reading_regions']=None;b['review_regions']=[{'id':'cleanup-1','kind':'cleanup','box':[78,68,112,102]}]
        report=self.write('report.json',dict(b,inventory_review_status=[{'id':'sample','source_reviewed':True,'handling':'translate','translation_approved':True}]))
        evidence={'schema_version':1,'binding':copy.deepcopy(b),'checks':{k:{'reviewed':True,'evidence':'Synthetic schema fixture; no real human inspection claimed'} for k in CHECKS},'regions':[{'id':'cleanup-1','reviewed':True,'evidence':'Synthetic format fixture'}]}
        return report,evidence
    def validate(self,report,evidence):
        return check(report,self.write('review.json',evidence),*[self.root/'source.png']*3)
    def test_synthetic_complete_record_is_not_release_approval(self):
        p,e=self.evidence();r=self.validate(p,e);self.assertTrue(r['recorded_review_complete']);self.assertFalse(r['release_ready']);self.assertFalse(r['review_performed_by_checker'])
    def test_pending_review_is_not_completed(self):
        p,e=self.evidence();e['checks']['art_inside_mask']['reviewed']=False;self.assertFalse(self.validate(p,e)['recorded_review_complete'])
    def test_region_review_cannot_be_omitted(self):
        p,e=self.evidence();e['regions']=[];self.assertIn('missing_region_reviews',self.validate(p,e)['findings'])
    def test_changed_asset_invalidates_review(self):
        p,e=self.evidence();Image.new('RGB',(200,140),'red').save(self.root/'source.png');self.assertFalse(self.validate(p,e)['recorded_review_complete'])
    def test_changed_inventory_invalidates_review(self):
        p,e=self.evidence();e['binding']['inventory_sha256']='stale';self.assertFalse(self.validate(p,e)['recorded_review_complete'])
    def test_review_checkboxes_cannot_override_unreadable_ledger(self):
        p,e=self.evidence();r=json.loads(p.read_bytes());r['inventory_review_status'][0]['handling']='unreadable';p.write_text(json.dumps(r));self.assertFalse(self.validate(p,e)['recorded_review_complete'])
    def test_changed_reading_window_invalidates_phone_review(self):
        p,e=self.evidence();r=json.loads(p.read_bytes());r['reading_regions']=[{'id':'changed-window','box':[0,0,100,100]}];p.write_text(json.dumps(r));self.assertFalse(self.validate(p,e)['recorded_review_complete'])
    def test_transcription_keeps_unverified_guesses_separate(self):
        inv={'source_sha256':self.hash,'source_dimensions':[200,140],'regions':[{'id':'sound','box':[78,68,35,35],'source_text':'?','target_text':'','handling':'unreadable'}]}
        ocr={'source_sha256':self.hash,'regions':[{'box':[80,70,30,30],'source_text_candidate':'부엉','alternatives':[{'source_text_candidate':'뿌옹'}]}]}
        r=build(self.root/'source.png',self.write('inventory.json',inv),self.root/'transcription.html',ocr);self.assertFalse(r['inventory_complete']);self.assertFalse(r['ocr_is_ground_truth']);text=(self.root/'transcription.html').read_text();self.assertIn('부엉',text);self.assertIn('뿌옹',text)
    def test_transcription_rejects_unbound_baseline(self):
        inv={'regions':[]}
        with self.assertRaisesRegex(ValueError,'bound to current'):build(self.root/'source.png',self.write('inventory.json',inv),self.root/'bad.html')

if __name__=='__main__':unittest.main(verbosity=2)
