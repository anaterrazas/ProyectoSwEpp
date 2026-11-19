"""Regresiones del ensayo, no generan ejemplos ni reentrenan con el test."""
import hashlib
import json
from pathlib import Path
import unittest

from PIL import Image
import torch
import model
import demo


def read(name):return json.loads((model.BASE/name).read_text(encoding='utf-8'))


class PrototypeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        torch.set_num_threads(2)
        cls.rows=[json.loads(s) for s in (model.BASE/'dataset/manifest.jsonl').read_text(encoding='utf-8').splitlines()]

    def test_unique_hashes_and_known_target_only(self):
        self.assertEqual(len(self.rows),50)
        self.assertEqual(len({r['expected_hash'] for r in self.rows}),50)
        for r in self.rows:
            self.assertIn(r['target'],(0,1));self.assertEqual(r['license'],'CC-BY-4.0')
            self.assertIsNone(r['labels']['RAYADURA']);self.assertIsNone(r['labels']['DEFORMACION'])
            self.assertEqual(hashlib.sha256((model.ROOT/r['path']).read_bytes()).hexdigest(),r['expected_hash'])

    def test_partitions_do_not_split_origin_groups(self):
        groups={p:{r['group_id'] for r in self.rows if r['partition']==p} for p in ('train','validation','test')}
        self.assertFalse(groups['train']&groups['test']);self.assertFalse(groups['train']&groups['validation']);self.assertFalse(groups['test']&groups['validation'])
        self.assertEqual([sum(r['partition']==p for r in self.rows) for p in ('train','validation','test')],[18,15,17])

    def test_test_measurements_match_saved_predictions(self):
        predictions=read('artifacts/predictions.json');truth=read('artifacts/metrics.json')
        for part in ('train','validation','test'):
            subset=[r for r in predictions if r['partition']==part]
            self.assertEqual(model.metrics([r['target'] for r in subset],[r['score'] for r in subset]),truth['partitions'][part])
        self.assertEqual(truth['partitions']['test']['fn'],3)
        self.assertEqual(truth['partitions']['test']['fp'],4)

    def test_checkpoint_reproduces_saved_inference(self):
        classifier=model.load_model();predictions=read('artifacts/predictions.json')
        for r in [next(r for r in predictions if r['partition']==p) for p in ('train','validation','test')]:
            with Image.open(model.ROOT/r['path']) as im:result=model.predict(classifier,im)
            self.assertAlmostEqual(result['TAPA_DEFECTUOSA']['score'],r['score'],places=5)

    def test_unavailable_classes_and_model_stay_unknown(self):
        r=self.rows[0]
        with Image.open(model.ROOT/r['path']) as image:
            absent=model.predict(None,image);present=model.predict(model.load_model(),image)
        self.assertTrue(all(not v['available'] and v['score'] is None and v['prediction'] is None for v in absent.values()))
        for key in ('RAYADURA','DEFORMACION'):
            self.assertIsNone(present[key]['prediction']);self.assertFalse(present[key]['available'])

    def test_exclusions_preserve_unknown_screenshot_labels(self):
        excluded=read('inspection/exclusions.json');additional=[r for r in excluded if r.get('inspection_id')]
        self.assertEqual(len(additional),15)
        self.assertEqual(sum(r['visible_watermark'] is True for r in additional),3)
        self.assertTrue(all(r['excluded'] and r['license'] is None and all(v is None for v in r['labels'].values()) for r in additional))
        own=[r for r in excluded if r.get('source')=='OWN_PREIMPORT']
        self.assertEqual(len(own),11)
        self.assertEqual({r['group_id'] for r in own},{'BOT-001','BOT-002','BOT-004','BOT-005'})

    def test_roi_validation(self):
        with Image.open(model.ROOT/self.rows[0]['path']) as image:
            with self.assertRaises(ValueError):demo.crop_image(image,[-1,0,100,100])
            with self.assertRaises(ValueError):demo.crop_image(image,[0,0,0,10])
            self.assertEqual(demo.crop_image(image,[0,0,50,50]).size,(50,50))

    def test_output_cannot_write_outside_experiment(self):
        with self.assertRaisesRegex(ValueError,'day1_v001/runs'):
            demo.process(model.ROOT/self.rows[0]['path'],model.ROOT/'produccion/forbidden_demo_output',whole_frame=True)

    def test_metrics_handle_missing_class_without_invented_specificity(self):
        result=model.metrics([1,1],[.8,.2])
        self.assertIsNone(result['specificity']);self.assertEqual(result['false_negative_rate'],.5)
        self.assertIsNone(model.metrics([],[])['accuracy'])

    def test_no_test_driven_threshold_or_global_conformity(self):
        plan=read('dataset/plan.json');result=read('artifacts/metrics.json')
        self.assertEqual(plan['threshold_fixed_before_training'],.5)
        self.assertEqual(plan['epochs_fixed'],result['epochs_fixed'])
        self.assertFalse(result['calibrated']);self.assertFalse(result['production_ready'])
        self.assertTrue(result['validation_missing_negative_class'])

    def test_video_demo_is_real_and_complete_not_an_accuracy_claim(self):
        result=read('runs/reference_demo/report.json')
        self.assertEqual(result['frames_processed'],434)
        self.assertEqual(len(result['predictions']),434)
        self.assertIsNone(result['accuracy_measured_for_upload'])
        self.assertEqual(result['input_sha256'],hashlib.sha256((model.ROOT/'media/produccion/videos/produccion.mp4').read_bytes()).hexdigest())
        self.assertFalse(result['production_ready']);self.assertTrue(result['not_an_object_detector'])
        self.assertTrue((model.BASE/'runs/reference_demo/result.mp4').is_file())


if __name__=='__main__':unittest.main(verbosity=2)
