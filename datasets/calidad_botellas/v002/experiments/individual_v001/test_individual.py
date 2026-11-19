"""Pruebas de evidencia real y unidad; fixtures de tracker solo en memoria, nunca demo."""
import hashlib
import json
import unittest
from unittest.mock import patch
import cv2
import numpy as np
from detectors import BASE,ROOT
import pipeline
import quality_gate as gate


def read(path):return json.loads((BASE/path).read_text(encoding='utf-8'))


class IndividualTests(unittest.TestCase):
    def test_real_detector_comparison_is_complete_and_prior_to_selection(self):
        report=read('comparison/results.json');selection=read('comparison/selection.json')
        self.assertEqual(len(report['frames']),70)
        self.assertEqual(selection['selected_detector'],'yolo11s640')
        self.assertEqual(report['summary']['yolo11s640']['prueba2']['detections'],64)
        self.assertEqual(report['summary']['fasterrcnn320']['prueba2']['detections'],4)
        for detector,results in report['summary'].items():self.assertEqual(results['tapas']['detections'],0)
        self.assertIsNone(report['map'])

    def test_tracking_does_not_draw_predictions_without_observation(self):
        tracker=pipeline.ObservedTracker();image=np.zeros((100,120,3),dtype=np.uint8)
        detection={'bbox_xyxy':[20.,10.,60.,90.],'score':.9,'class_id':39,'label':'bottle'}
        observed=tracker.update([detection],image)
        self.assertIsNotNone(observed[0]['track_id'])
        self.assertEqual(observed[0]['bbox_xyxy'],detection['bbox_xyxy'])
        self.assertEqual(tracker.update([],image),[])

    def test_same_detected_object_reuses_id(self):
        tracker=pipeline.ObservedTracker();image=np.zeros((100,120,3),dtype=np.uint8)
        first=tracker.update([{'bbox_xyxy':[20.,10.,60.,90.],'score':.9}],image)[0]
        second=tracker.update([{'bbox_xyxy':[21.,10.,61.,90.],'score':.9}],image)[0]
        self.assertEqual(first['track_id'],second['track_id'])
        self.assertEqual(second['bbox_xyxy'],[21.,10.,61.,90.])

    def test_regions_are_bounded_and_explicitly_candidates(self):
        body,cap=pipeline.boxes_for_regions([-1.,0.,120.,100.],(100,120,3))
        self.assertEqual(body,[0,38,120,100]);self.assertEqual(cap,[0,0,120,38])

    def test_bad_quality_rejects_visibility(self):
        result=gate.region_quality(np.zeros((20,20,3),dtype=np.uint8),True,True)
        self.assertFalse(result['technical_pass'])
        self.assertIn('RESOLUCION_INSUFICIENTE',result['reasons'])
        self.assertIn('POSIBLE_DESENFOQUE',result['reasons'])

    def test_no_domain_approval_never_calls_classifier(self):
        profile=gate.reference_profile();manifest=gate.cap_model.BASE/'dataset/train_manifest.jsonl'
        reference=json.loads(manifest.read_text(encoding='utf-8').splitlines()[0]);image=cv2.imread(str(ROOT/reference['path']))
        with patch.object(gate.cap_model,'predict',side_effect=AssertionError('No debe llamarse')):
            result=gate.classify(image,{'reasons':[]},profile,None,'test',object())
        self.assertFalse(result['classifier_called']);self.assertIsNone(result['classes']['TAPA_DEFECTUOSA']['score'])
        self.assertEqual(result['inspection_result'],'NO EVALUABLE')

    def test_gate_requires_domain_region_and_stage_even_if_appearance_matches(self):
        profile=gate.reference_profile();reference=json.loads((gate.cap_model.BASE/'dataset/train_manifest.jsonl').read_text(encoding='utf-8').splitlines()[0])
        image=cv2.imread(str(ROOT/reference['path']))
        approval={'video_sha256':'test','reviewer_id':'TEST_ONLY','compatible_with_training_domain':True,
                  'cap_neck_roi_assignment_verified':True,'post_capping_inspection_stage_verified':False,'cap_required':None}
        self.assertFalse(gate.eligibility(image,{'reasons':[]},profile,approval,'test')['eligible'])

    def test_eligible_reference_can_call_real_saved_classifier_without_global_conformity(self):
        profile=gate.reference_profile();reference=json.loads((gate.cap_model.BASE/'dataset/train_manifest.jsonl').read_text(encoding='utf-8').splitlines()[0])
        image=cv2.imread(str(ROOT/reference['path']))
        approval={'video_sha256':'TEST_FIXTURE_ONLY','reviewer_id':'TEST_ONLY','compatible_with_training_domain':True,
                  'cap_neck_roi_assignment_verified':True,'post_capping_inspection_stage_verified':True,'cap_required':True}
        result=gate.classify(image,{'reasons':[]},profile,approval,'TEST_FIXTURE_ONLY',gate.cap_model.load_model())
        self.assertTrue(result['classifier_called']);self.assertIsNotNone(result['classes']['TAPA_DEFECTUOSA']['score'])
        self.assertIsNone(result['global_conformity']);self.assertEqual(result['inspection_result'],'NO EVALUABLE')

    def test_full_reference_results_and_no_fake_tapas_tracks(self):
        expected={'prueba2_v001':(406,3769,13),'tapas_v001':(450,0,0)}
        for name,counts in expected.items():
            result=read(f'runs/{name}/report.json')
            self.assertEqual((result['frames_processed'],result['observed_detections'],result['temporary_track_ids']),counts)
            self.assertEqual(result['classifier_calls'],0);self.assertIsNone(result['precision']);self.assertIsNone(result['id_switches'])
            self.assertEqual(hashlib.sha256(__import__('pathlib').Path(result['source_video']).read_bytes()).hexdigest(),result['input_video_sha256'])

    def test_frame_records_use_current_observations_and_pts(self):
        report=read('runs/prueba2_v001/report.json');ids=set()
        for line in (BASE/'runs/prueba2_v001/frames.jsonl').read_text(encoding='utf-8').splitlines():
            row=json.loads(line)
            self.assertEqual(row['pts_seconds'],report['video_metadata']['pts_seconds'][row['frame_index']])
            frame_ids=[o['track_id'] for o in row['objects'] if o['track_id'] is not None]
            self.assertEqual(len(frame_ids),len(set(frame_ids)))
            for obj in row['objects']:
                self.assertTrue(obj['observed_this_frame']);self.assertIsNone(obj['physical_container_id'])
                self.assertIn('CURRENT_DETECTOR_OBSERVATION',obj['bbox_source'])
                self.assertIsNone(obj['classes']['TAPA_DEFECTUOSA']['prediction'])
                self.assertFalse(obj['classes']['RAYADURA']['available'])
                if obj['track_id'] is not None:ids.add(obj['track_id'])
        self.assertEqual(len(ids),13)

    def test_saved_regions_match_hashes_and_reproduce_real_frame_pixels(self):
        report=read('runs/prueba2_v001/report.json');source=report['source_video']
        for track in report['tracks']:
            for item in track['saved_regions']:
                self.assertEqual(pipeline.sha(BASE/'runs/prueba2_v001'/item['path']),item['sha256'])
        track=report['tracks'][0];observation=read(f'runs/prueba2_v001/crops/track_{track["track_id"]:04d}/observation.json')
        frame=pipeline.video_tools.decoded_frame(source,observation['frame_index'])
        for item,key in zip(track['saved_regions'],('body_region','cap_neck_region')):
            x1,y1,x2,y2=observation[key]['bbox_xyxy'];actual=cv2.imread(str(BASE/'runs/prueba2_v001'/item['path']))
            self.assertTrue(np.array_equal(actual,frame[y1:y2,x1:x2]))

    def test_video_encodings_are_real_and_keep_frame_counts(self):
        for name,expected in [('prueba2_v001',406),('tapas_v001',450)]:
            cap=cv2.VideoCapture(str(BASE/f'runs/{name}/processed.mp4'))
            self.assertTrue(cap.isOpened());self.assertEqual(int(cap.get(cv2.CAP_PROP_FRAME_COUNT)),expected);cap.release()


if __name__=='__main__':unittest.main(verbosity=2)
