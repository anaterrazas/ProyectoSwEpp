"""Fixtures solo temporales; no se anotan las referencias reales durante pruebas."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import shutil
import unittest
from uuid import uuid4
import threading
import urllib.request
import urllib.error

import cv2
import numpy as np

import annotate as a


class ManualTests(unittest.TestCase):
    def setUp(self):
        # mkdir normal hereda ACL; TemporaryDirectory(mode=0700) falla en este sandbox Windows.
        self.root = a.BASE / ('test_only_' + uuid4().hex)
        self.root.mkdir()
        self.addCleanup(shutil.rmtree, self.root)
        (self.root/'images').mkdir()
        self.frames = []
        self.videos = []
        for n in range(2):
            source = self.root/f'source{n}.mp4'; source.write_bytes(b'unit-test-only-'+bytes([n]))
            v = {'video_id':f'v{n}', 'video_sha256':a.sha(source), 'source_path':str(source),
                 'original_filename':source.name, 'license':None,
                 'metadata':{'frames':1, 'pts_seconds':[.5], 'time_origin_pts_seconds':.5}}
            self.videos.append(v)
            image = np.full((100,120,3), n*100, dtype=np.uint8)
            cv2.imwrite(str(self.root/'images'/f's{n}.png'),image)
            self.frames.append({'sample_id':f's{n}', 'video_id':v['video_id'],
                'video_sha256':v['video_sha256'], 'frame_index':0,'pts_seconds':.5,'timestamp_seconds':0,
                'image':f'images/s{n}.png','image_sha256':a.sha(self.root/'images'/f's{n}.png'),
                'width':120,'height':100,'dhash':('0'*16 if n==0 else 'f'*16)})
        a.write_new(self.root/'manifest.json', {'frames':self.frames,'videos':self.videos})
        self.ds=a.Dataset(self.root)

    def box(self, **changes):
        b={'box_id':'b1','class_name':'ENVASE','bbox_xyxy':[10.,10.,80.,90.],
           'partial':False,'occluded':False,'not_evaluable':False,'physical_id':None,
           'parent_envase_box_id':None,'notes':''}
        return dict(b, **changes)

    def data(self, **changes):
        d={'sample_id':'s0','revision':0,'expected_hash':self.frames[0]['image_sha256'],
           'author':'TEST_ONLY','status':'draft','exhaustive':False,'empty_confirmed':False,
           'notes':'unit test, not a real annotation','boxes':[self.box()]}
        return dict(d, **changes)

    def test_revisions_keep_authors_and_previous_bytes(self):
        first=self.ds.save('s0',self.data()); p=self.root/'revisions/s0/000001.json'; original=p.read_bytes()
        second=self.ds.save('s0',self.data(revision=1,author='SECOND_TEST_ONLY',boxes=[]))
        self.assertEqual(p.read_bytes(),original)
        self.assertEqual(second['previous_revision_sha256'],hashlib.sha256(original).hexdigest())
        self.assertEqual(a.read(p)['author'],'TEST_ONLY');self.assertEqual(second['revision'],2)
        self.assertTrue(self.ds.report(verify=True)['hashes_verified'])

    def test_stale_version_cannot_overwrite(self):
        self.ds.save('s0',self.data())
        with self.assertRaisesRegex(ValueError,'Conflicto'): self.ds.save('s0',self.data())

    def test_author_required(self):
        with self.assertRaises(ValueError): self.ds.save('s0',self.data(author=''))

    def test_original_hash_required_and_image_tamper_rejected(self):
        with self.assertRaises(ValueError): self.ds.save('s0',self.data(expected_hash='bad'))
        (self.root/self.frames[0]['image']).write_bytes(b'changed')
        with self.assertRaises(ValueError): self.ds.save('s0',self.data())

    def test_outside_small_nonfinite_and_invalid_class_rejected(self):
        for b in [self.box(bbox_xyxy=[-1,0,20,20]),self.box(bbox_xyxy=[10,10,10.5,20]),
                  self.box(bbox_xyxy=[0,0,float('nan'),30]),self.box(class_name='DEFECTO')]:
            with self.subTest(box=b),self.assertRaises(ValueError): self.ds.save('s0',self.data(boxes=[b]))

    def test_duplicate_ids_and_boxes_rejected(self):
        for boxes in [[self.box(),self.box(bbox_xyxy=[1,1,5,5])],
                      [self.box(),self.box(box_id='b2')]]:
            with self.assertRaises(ValueError): self.ds.save('s0',self.data(boxes=boxes))

    def test_unknown_attributes_stay_null_draft_and_block_review(self):
        boxes=[self.box(partial=None,occluded=None,not_evaluable=None)]
        d=self.data(boxes=boxes);saved=self.ds.save('s0',d)
        self.assertIsNone(saved['boxes'][0]['partial'])
        with self.assertRaises(ValueError): self.ds.save('s0',dict(d,revision=1,status='reviewed',exhaustive=True))

    def test_exhaustiveness_and_explicit_empty(self):
        with self.assertRaises(ValueError): self.ds.save('s0',self.data(status='reviewed'))
        with self.assertRaises(ValueError): self.ds.save('s0',self.data(status='reviewed',exhaustive=True,boxes=[]))
        self.ds.save('s0',self.data(status='reviewed',exhaustive=True,boxes=[],empty_confirmed=True))
        exported=self.ds.export(); trace=a.read(Path(exported['export_directory'])/'traceability.json')
        self.assertEqual(exported['exported_frames'],1)
        self.assertEqual((Path(exported['export_directory'])/trace['records'][0]['label_file']).read_text(),'')

    def test_yolo_normalization_and_json_provenance(self):
        self.ds.save('s0',self.data(status='reviewed',exhaustive=True))
        exported=self.ds.export(); target=Path(exported['export_directory']);trace=a.read(target/'traceability.json')
        values=(target/trace['records'][0]['label_file']).read_text().split()
        self.assertEqual(values[0],'0');self.assertAlmostEqual(float(values[1]),45/120)
        self.assertEqual(trace['records'][0]['annotation']['author'],'TEST_ONLY')
        self.assertIsNone(trace['records'][0]['annotation']['boxes'][0]['physical_id'])
        self.assertFalse(trace['training_ready'])
        self.assertEqual(trace['skipped'][0]['sample_id'],'s1')

    def test_ignore_region_excludes_entire_frame_from_plain_yolo(self):
        self.ds.save('s0',self.data(status='reviewed',exhaustive=True,boxes=[self.box(not_evaluable=True)]))
        result=self.ds.export();self.assertEqual(result['exported_frames'],0)
        trace=a.read(Path(result['export_directory'])/'traceability.json')
        self.assertEqual(trace['skipped'][0]['reason'],'contains_ignore_regions_no_safe_plain_yolo_export')

    def test_cap_class_one_exports_with_human_parent_and_occlusion_flags(self):
        envase=self.box(physical_id='TEST-KNOWN',partial=True,occluded=True)
        cap=self.box(box_id='cap',class_name='TAPA',bbox_xyxy=[20,10,40,20],
                     physical_id='TEST-KNOWN',parent_envase_box_id='b1')
        self.ds.save('s0',self.data(status='reviewed',exhaustive=True,boxes=[envase,cap]))
        result=self.ds.export();target=Path(result['export_directory']);trace=a.read(target/'traceability.json')
        lines=(target/trace['records'][0]['label_file']).read_text().splitlines()
        self.assertEqual([line.split()[0] for line in lines],['0','1'])
        self.assertEqual(trace['records'][0]['annotation']['boxes'][1]['parent_envase_box_id'],'b1')

    def test_cap_association_must_reference_real_envase(self):
        with self.assertRaises(ValueError):
            self.ds.save('s0',self.data(boxes=[self.box(class_name='TAPA',parent_envase_box_id='absent')]))
        envase=self.box(physical_id='BOT-TEST')
        cap=self.box(box_id='cap',class_name='TAPA',bbox_xyxy=[20,5,40,15],parent_envase_box_id='b1',physical_id='OTHER')
        with self.assertRaises(ValueError): self.ds.save('s0',self.data(boxes=[envase,cap]))

    def test_unknown_sessions_keep_all_videos_together(self):
        self.assertEqual(len(self.ds.components()),1)
        self.ds.assign('v0','TEST_ONLY',split='train')
        self.assertEqual(self.ds.report()['partition_frames'],{'train':2})

    def test_distinct_known_sessions_can_split_but_same_physical_cannot_leak(self):
        self.ds.assign('v0','TEST_ONLY',session='session-1')
        self.ds.assign('v1','TEST_ONLY',session='session-2')
        self.ds.assign('v0','TEST_ONLY',split='train'); self.ds.assign('v1','TEST_ONLY',split='test')
        self.ds.save('s0',self.data(boxes=[self.box(physical_id='KNOWN')]))
        with self.assertRaisesRegex(ValueError,'Fuga'):
            self.ds.save('s1',dict(self.data(boxes=[self.box(physical_id='KNOWN')]),sample_id='s1',expected_hash=self.frames[1]['image_sha256']))
        self.assertEqual(self.ds.latest('s1')['revision'],0)

    def test_same_session_and_similarity_join_components(self):
        self.ds.assign('v0','TEST_ONLY',session='one'); self.ds.assign('v1','TEST_ONLY',session='one')
        self.assertEqual(len(self.ds.components()),1)
        self.ds.assign('v1','TEST_ONLY',session='two'); self.assertEqual(len(self.ds.components()),2)
        self.ds.frames['s1']['dhash']=self.ds.frames['s0']['dhash']
        self.assertEqual(len(self.ds.components()),1)

    def test_path_traversal_and_duplicate_frame_manifest_rejected(self):
        manifest=a.read(self.root/'manifest.json');manifest['frames'][0]['image']='../outside.png'
        (self.root/'manifest.json').write_text(json.dumps(manifest))
        with self.assertRaises(ValueError):a.Dataset(self.root)

    def test_history_modification_detected(self):
        self.ds.save('s0',self.data());self.ds.save('s0',self.data(revision=1))
        path=self.root/'revisions/s0/000001.json';record=a.read(path);record['author']='CHANGED';path.write_text(json.dumps(record))
        with self.assertRaisesRegex(ValueError,'Cadena'):self.ds.report(verify=True)

    def test_sampling_uses_pts_without_consecutive_frames(self):
        pts=[.3+i/50 for i in range(450)];indices=a.sample_indices(pts,1)
        self.assertEqual(indices[0],0);self.assertGreaterEqual(min(np.diff(indices)),25)
        with self.assertRaises(ValueError):a.sample_indices(pts,.1)

    def test_physical_envase_cannot_appear_twice_in_same_frame(self):
        with self.assertRaises(ValueError):
            self.ds.save('s0',self.data(boxes=[self.box(physical_id='KNOWN'), self.box(box_id='b2',physical_id='KNOWN',bbox_xyxy=[1,1,9,9])]))

    def test_http_save_resume_and_origin_token_protection(self):
        server=a.make_server(self.ds,0); thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        try:
            base=f'http://127.0.0.1:{server.server_port}'
            state=json.load(urllib.request.urlopen(base+'/api/state'))
            body=json.dumps(self.data()).encode()
            bad=urllib.request.Request(base+'/api/save',body,{'Content-Type':'application/json'})
            with self.assertRaises(urllib.error.HTTPError) as error:urllib.request.urlopen(bad)
            self.assertEqual(error.exception.code,403)
            request=urllib.request.Request(base+'/api/save',body,{'Content-Type':'application/json','Origin':base,'X-Annotation-Token':state['token']})
            saved=json.load(urllib.request.urlopen(request));self.assertEqual(saved['revision'],1)
            resumed=json.load(urllib.request.urlopen(base+'/api/state'))
            self.assertEqual(resumed['annotations']['s0']['boxes'][0]['class_name'],'ENVASE')
            image=urllib.request.urlopen(base+'/image/s0').read()
            self.assertEqual(hashlib.sha256(image).hexdigest(),self.frames[0]['image_sha256'])
        finally:
            server.shutdown();server.server_close();thread.join()


class ReferenceTests(unittest.TestCase):
    def test_actual_references_integrity_and_every_png_reproducible(self):
        ds=a.Dataset(a.BASE/'dataset');report=ds.report(verify=True)
        # No exigir cero etiquetas: estas pruebas también deben funcionar después de anotar.
        self.assertEqual(report['frames'],25)
        self.assertFalse(report['sufficient_for_training']);self.assertEqual(report['exact_duplicate_pairs'],[])
        for video in ds.manifest['videos']:
            cap=cv2.VideoCapture(video['source_path']);frames={f['frame_index']:f for f in ds.frames.values() if f['video_id']==video['video_id']}
            try:
                for index in range(video['metadata']['frames']):
                    ok,image=cap.read();self.assertTrue(ok)
                    if index in frames:
                        ok,encoded=cv2.imencode('.png',image);self.assertTrue(ok)
                        self.assertEqual(hashlib.sha256(encoded.tobytes()).hexdigest(),frames[index]['image_sha256'])
            finally:cap.release()


if __name__=='__main__':unittest.main()
