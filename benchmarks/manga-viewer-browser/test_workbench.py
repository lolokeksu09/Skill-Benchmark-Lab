"""Native-plan and negative checks, with synthetic art only."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from PIL import Image, ImageDraw
from retouch_workbench import prepare, apply, rasterize


class WorkbenchTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        im=Image.new('RGB',(120,100),'#c9d6e3');ImageDraw.Draw(im).rectangle((56,46,64,54),fill='black');im.save(self.root/'input.png')
        self.before=(self.root/'input.png').read_bytes()
        self.prepared=self.root/'prepared';prepare(self.root/'input.png',self.prepared)
        self.plan={'schema_version':1,'source':'source.png','source_sha256':hashlib.sha256((self.prepared/'source.png').read_bytes()).hexdigest(),
            'source_dimensions':[120,100], 'mask_strokes':[{'radius':9,'points':[[60,50]]}],
            'protected_strokes':[{'radius':1,'points':[[51,50]]}],
            'operations':[{'kind':'clone','source':[30,30],'target':[60,50],'radius':8}],
            'mask_reviewed':True,'mask_evidence':'Synthetic contract fixture, not a real art review'}
    def replay(self):
        p=self.prepared/'plan.json';p.write_text(json.dumps(self.plan));return apply(p,self.root/'applied')
    def test_native_roundtrip_and_immutable_source(self):
        r=self.replay();self.assertEqual(r['outside_mask_changes'],0);self.assertEqual(r['protected_artwork_changes'],0)
        self.assertFalse(r['independent_review']);self.assertEqual(r['manual_art_review'],'pending')
        with Image.open(self.root/'applied/result/cleaned.png') as im:
            self.assertEqual(im.size,(120,100));self.assertEqual(im.getpixel((60,50)),(201,214,227,255))
        self.assertEqual((self.root/'input.png').read_bytes(),self.before)
        with Image.open(self.root/'applied/mask.png') as im:
            self.assertEqual(im.mode,'L');self.assertEqual({v for v,n in enumerate(im.histogram()) if n},{0,255})
    def test_preparation_does_not_claim_review(self):
        text=(self.prepared/'retouch.html').read_text();self.assertIn('"mask_reviewed": false',text)
        self.assertNotIn('__PLAN__',text);self.assertNotIn('__SOURCE__',text)
        report=json.loads((self.prepared/'preparation-report.json').read_bytes());self.assertFalse(report['mask_reviewed'])
    def test_protection_blocks_actual_clone_change(self):
        self.plan['protected_strokes']=[{'radius':1,'points':[[60,50]]}]
        with self.assertRaisesRegex(ValueError,'changes protected artwork'):self.replay()
        self.assertFalse((self.root/'applied/result/cleaned.png').exists())
    def test_unreviewed_plan_cannot_execute(self):
        self.plan['mask_reviewed']=False
        with self.assertRaisesRegex(ValueError,'Reviewed mask'):self.replay()
    def test_source_change_rejected(self):
        Image.new('RGB',(120,100),'red').save(self.prepared/'source.png')
        with self.assertRaisesRegex(ValueError,'Stale source'):self.replay()
    def test_native_dimension_change_rejected(self):
        self.plan['source_dimensions']=[119,100]
        with self.assertRaisesRegex(ValueError,'Native dimensions'):self.replay()
    def test_bad_coordinates_and_boolean_radius_rejected(self):
        for stroke in [{'radius':True,'points':[[10,10]]},{'radius':2,'points':[[120,10]]},{'radius':2,'points':[[1.5,10]]}]:
            with self.assertRaises(ValueError):rasterize([stroke],(120,100))
    def test_path_escape_and_output_overwrite_rejected(self):
        self.plan['source']='../input.png'
        with self.assertRaisesRegex(ValueError,'escapes project'):self.replay()
        with self.assertRaisesRegex(ValueError,'must be new'):prepare(self.root/'input.png',self.prepared)
    def test_empty_mask_and_empty_ops_rejected(self):
        self.plan['mask_strokes']=[]
        with self.assertRaisesRegex(ValueError,'Empty or overly broad'):self.replay()
        self.plan['operations']=[]
        p=self.prepared/'plan.json';p.write_text(json.dumps(self.plan))
        with self.assertRaisesRegex(ValueError,'1..2000'):apply(p,self.root/'another')


if __name__=='__main__':unittest.main(verbosity=2)
