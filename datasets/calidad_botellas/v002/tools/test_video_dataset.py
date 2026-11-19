"""MP4 y matrices artificiales SOLO en temporales de prueba, nunca datos reales."""
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
import subprocess
from unittest.mock import patch, MagicMock

import cv2
import numpy as np
import capture_dataset as photo
import video_dataset as video


class VideoTests(unittest.TestCase):
    def setUp(self):
        self.temp=TemporaryDirectory(prefix='epp_video_tests_');self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        photo.write_new(self.root/'dataset.json',{'dataset_id':'epp-own-v002','origin':'OWN_REAL_CAPTURE'})
        self.dataset=video.VideoDataset(self.root)
        self.session=self.dataset.session('TEST','TEST','TEST','TEST','TEST','TEST','TEST',True)['session_id']
        self.bottle=self.dataset.bottle('TEST-001')['bottle_id']
        self.profile=self.dataset.profile(self.bottle,'PP','pote','cilindrica','blanco','presion','TEST')['profile_id']
        self.source=self.root/'fixture.mp4'
        writer=cv2.VideoWriter(str(self.source),cv2.VideoWriter_fourcc(*'mp4v'),10,(320,240))
        if not writer.isOpened():self.fail('No hay codificador de prueba MP4')
        for n in range(10):
            image=np.full((240,320,3),(n*20,70,110),np.uint8)
            cv2.rectangle(image,(20+n*10,40),(70+n*10,200),(200,200,200),-1);writer.write(image)
        writer.release()

    def register(self):
        return self.dataset.video(self.source,self.session,'2026-01-01T12:00:00-04:00','conveyor-real',True)

    def frame(self,index=0):
        record=self.register()
        return record,self.dataset.frame(record['video_id'],self.bottle,self.profile,index,single_container=True)

    def test_real_content_validation_pts_and_copy(self):
        record=self.register()
        self.assertEqual(record['frames'],10)
        self.assertEqual(photo.sha(self.source),photo.sha(self.root/record['video']))
        self.assertAlmostEqual(record['pts_seconds'][3],.3)
        self.assertEqual(self.dataset.validate()['videos'],1)

    def test_fake_mp4_rejected(self):
        path=self.root/'fake.mp4';path.write_text('not video')
        with self.assertRaises(ValueError):video.inspect_video(path)

    def test_duplicate_and_missing_provenance_rejected(self):
        self.register()
        with self.assertRaises(ValueError):self.register()
        with self.assertRaises(ValueError):self.dataset.video(self.source,self.session,'2026-01-01T12:00:00Z','recorded-real',False)

    def test_frame_identity_profile_pts_and_unknown_labels(self):
        record,sample=self.frame(3)
        self.assertEqual(sample['frame_index'],3)
        self.assertAlmostEqual(sample['timestamp_seconds'],.3)
        self.assertEqual(sample['video_sha256'],record['video_sha256'])
        report=self.dataset.validate()
        self.assertEqual(report['materials'],{'PP':1})
        self.assertEqual(report['latest_labels']['RAYADURA']['unknown'],1)
        self.assertIsNone(report['automatic_confidence'])

    def test_frame_requires_roi_or_single_container_confirmation(self):
        record=self.register()
        with self.assertRaises(ValueError):self.dataset.frame(record['video_id'],self.bottle,self.profile,0)
        with self.assertRaises(ValueError):self.dataset.frame(record['video_id'],self.bottle,self.profile,50,single_container=True)
        with self.assertRaises(ValueError):self.dataset.frame(record['video_id'],self.bottle,self.profile,0,[-1,0,5,5])

    def test_roi_and_manual_multilabel_review_reuse_photo_schema(self):
        record=self.register();sample=self.dataset.frame(record['video_id'],self.bottle,self.profile,1,[20,20,120,160])
        self.assertEqual((sample['width'],sample['height']),(120,160))
        decision=photo.blank_annotation();decision['labels'].update(RAYADURA=1,DEFORMACION=1)
        self.dataset.annotate(sample['sample_id'],decision,'A');self.dataset.annotate(sample['sample_id'],decision,'B',True)
        self.assertEqual(self.dataset.validate()['reviewed_labels']['DEFORMACION']['positive'],1)

    def test_repeated_frame_and_other_profile_rejected(self):
        record,sample=self.frame()
        with self.assertRaises(ValueError):self.dataset.frame(record['video_id'],self.bottle,self.profile,0,single_container=True)
        other=self.dataset.bottle('TEST-OTHER')['bottle_id']
        with self.assertRaises(ValueError):self.dataset.frame(record['video_id'],other,self.profile,1,single_container=True)

    def test_temporal_event_does_not_propagate_labels(self):
        record,sample=self.frame(3)
        event=self.dataset.event(record['video_id'],self.bottle,2,5,'RAYADURA','A','Test only')
        self.assertEqual(event['status'],'HUMAN_ASSOCIATION_UNREVIEWED')
        self.assertFalse(event['propagates_frame_labels'])
        result=self.dataset.validate()
        self.assertEqual(result['temporal_associations'],1)
        self.assertEqual(result['latest_labels']['RAYADURA']['unknown'],1)

    def test_temporal_event_requires_anchor_and_valid_interval(self):
        record=self.register()
        with self.assertRaises(ValueError):self.dataset.event(record['video_id'],self.bottle,0,3,'RAYADURA','A','Test')
        with self.assertRaises(ValueError):self.dataset.event(record['video_id'],self.bottle,0,30,'NEW_CLASS','A','Test')

    def test_video_and_session_prevent_partition_leakage(self):
        record,sample=self.frame()
        other=self.dataset.bottle('TEST-OTHER')['bottle_id']
        profile=self.dataset.profile(other,'HDPE','bidon','rectangular','UNKNOWN','rosca','A')['profile_id']
        second=self.dataset.frame(record['video_id'],other,profile,1,single_container=True)
        plan=self.dataset.propose();self.dataset.validate(plan)
        self.assertEqual(len(plan['components']),1)
        plan['assignments'][second['sample_id']]='test'
        with self.assertRaises(ValueError):self.dataset.validate(plan)

    def test_tampered_video_or_pts_rejected(self):
        record,sample=self.frame()
        path=self.root/'metadata/samples'/(sample['sample_id']+'.json')
        item=photo.read(path);item['timestamp_seconds']=99
        path.write_text(__import__('json').dumps(item),encoding='utf-8')
        with self.assertRaises(ValueError):self.dataset.validate()
        (self.root/record['video']).write_bytes(b'changed')
        with self.assertRaises(ValueError):self.dataset.validate()

    def test_preview_reports_no_model_and_preserves_source(self):
        record=self.register();before=photo.sha(self.source)
        with patch.object(cv2,'imshow'),patch.object(cv2,'waitKey',return_value=ord('q')),patch.object(cv2,'destroyAllWindows'):
            report=video.preview_video(self.dataset,record['video_id'])
        self.assertFalse(report['model_available']);self.assertIsNone(report['automatic_result'])
        self.assertEqual(photo.sha(self.source),before)

    def test_unavailable_camera_creates_no_record(self):
        fake=MagicMock();fake.isOpened.return_value=False
        with patch.object(cv2,'VideoCapture',return_value=fake),patch.object(cv2,'destroyAllWindows'):
            with self.assertRaises(ValueError):video.camera(self.dataset,0,1)
        self.assertEqual(self.dataset.records('videos'),[])

    def test_camera_recording_pipeline_mocked_device_only(self):
        actual=cv2.VideoCapture;fake=MagicMock();fake.isOpened.return_value=True
        fake.read.return_value=(True,np.full((240,320,3),70,np.uint8))
        def factory(source):return fake if isinstance(source,int) else actual(source)
        with patch.object(cv2,'VideoCapture',side_effect=factory),patch.object(cv2,'imshow'),patch.object(cv2,'waitKey',return_value=ord('q')),patch.object(cv2,'destroyAllWindows'):
            result=video.camera(self.dataset,0,1,self.session,True,True)
        self.assertEqual(result['mode'],'webcam-real')
        self.assertEqual(len(result['camera_capture_offsets_seconds']),1)
        self.dataset.validate()

    def test_materials_and_container_types_do_not_change_defect_classes(self):
        for material in video.MATERIALS:
            record=self.dataset.profile(self.bottle,material,'recipiente','UNKNOWN','UNKNOWN','UNKNOWN','A')
            self.assertEqual(record['material'],material)
        self.assertEqual(photo.LABELS,('RAYADURA','DEFORMACION','TAPA_DEFECTUOSA'))

    def test_vfr_uses_pts_instead_of_frame_divided_by_fps(self):
        output=self.root/'vfr_fixture.mp4'
        run=subprocess.run([video.imageio_ffmpeg.get_ffmpeg_exe(),'-nostdin','-v','error','-i',str(self.source),
                            '-vf','setpts=(N+floor(N/2))/(10*TB)','-fps_mode','vfr','-c:v','mpeg4',str(output)],capture_output=True,timeout=30)
        self.assertEqual(run.returncode,0,run.stderr.decode(errors='replace'))
        result=video.inspect_video(output)
        self.assertAlmostEqual(result['pts_seconds'][3],.4)
        self.assertNotAlmostEqual(result['pts_seconds'][3],3/result['fps_nominal'])

    def test_photo_and_video_same_container_across_sessions_stay_together(self):
        record,sample=self.frame()
        session=self.dataset.session('A','P','L','S','C','FIXED','NORMAL',True)['session_id']
        path=self.root/'photo_fixture.png';cv2.imwrite(str(path),np.full((240,320,3),40,np.uint8))
        still=self.dataset.capture(path,session,self.bottle,'2026-01-01T13:00:00Z',True)
        self.assertEqual(len(self.dataset.components()),1)
        plan=self.dataset.propose();self.dataset.validate(plan)
        plan['assignments'][still['sample_id']]='test'
        with self.assertRaises(ValueError):self.dataset.validate(plan)

    def test_nonzero_source_pts_origin_is_preserved(self):
        output=self.root/'shifted_fixture.mp4'
        run=subprocess.run([video.imageio_ffmpeg.get_ffmpeg_exe(),'-nostdin','-v','error','-i',str(self.source),
                            '-c','copy','-output_ts_offset','5',str(output)],capture_output=True,timeout=30)
        self.assertEqual(run.returncode,0,run.stderr.decode(errors='replace'))
        result=video.inspect_video(output)
        self.assertAlmostEqual(result['time_origin_pts_seconds'],5)
        self.assertAlmostEqual(result['pts_seconds'][3],5.3)
        self.assertAlmostEqual(result['duration_last_frame_seconds'],.9)

    def test_existing_real_video_read_only_regression(self):
        source=photo.PROJECT/'media/produccion/videos/produccion.mp4'
        before=photo.sha(source);result=video.inspect_video(source)
        self.assertEqual(result['frames'],434)
        self.assertAlmostEqual(result['pts_seconds'][-1]-result['pts_seconds'][0],8.66)
        self.assertEqual(photo.sha(source),before)


if __name__=='__main__':unittest.main(verbosity=2)
