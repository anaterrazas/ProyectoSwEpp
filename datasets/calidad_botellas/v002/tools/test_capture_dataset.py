"""Fixtures artificiales SOLO en temporales; nunca se exportan al dataset real."""
from copy import deepcopy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from PIL import Image
import capture_dataset as capture


class CaptureTests(unittest.TestCase):
    def setUp(self):
        self.temp=TemporaryDirectory(prefix='epp_v002_tests_')
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        capture.write_new(self.root/'dataset.json',{'dataset_id':'epp-own-v002','origin':'OWN_REAL_CAPTURE'})
        self.dataset=capture.Dataset(self.root)

    def session(self):
        return self.dataset.session('CAPTURADOR_TEST','PRODUCTO_TEST','LOTE_TEST','ETAPA_TEST','CAMARA_TEST','FIJA_TEST','NORMAL_TEST',True)['session_id']

    def photo(self,number=1,session=None,bottle=None):
        path=self.root/f'fixture_{number}.png'
        Image.new('RGB',(240,400),(number,80,110)).save(path)
        session=session or self.session()
        bottle=bottle or self.dataset.bottle('BOTELLA_TEST_'+str(number))['bottle_id']
        return self.dataset.capture(path,session,bottle,'2026-01-01T12:00:00-04:00',True)

    def test_empty_structure_is_valid_but_not_ready(self):
        result=self.dataset.validate()
        self.assertEqual(result['images'],0)
        self.assertFalse(result['training_authorized'])
        self.assertTrue(result['warnings'])

    def test_register_preserves_original_bytes_and_unknowns(self):
        row=self.photo()
        self.assertEqual((self.root/row['image']).read_bytes(),(self.root/'fixture_1.png').read_bytes())
        result=self.dataset.validate()
        for label in capture.LABELS:self.assertEqual(result['latest_labels'][label],{'positive':0,'negative':0,'unknown':1})

    def test_duplicate_photograph_rejected(self):
        row=self.photo()
        with self.assertRaisesRegex(ValueError,'duplicada'):
            self.dataset.capture(self.root/'fixture_1.png',row['session_id'],row['bottle_id'],'2026-01-01T12:00:00-04:00',True)

    def test_known_public_or_v001_image_rejected(self):
        session=self.session();bottle=self.dataset.bottle('TEST')['bottle_id']
        path=self.root/'fixture.png';Image.new('RGB',(240,400)).save(path)
        with patch.object(self.dataset,'forbidden_hashes',return_value={capture.sha(path)}):
            with self.assertRaisesRegex(ValueError,'público'):
                self.dataset.capture(path,session,bottle,'2026-01-01T12:00:00Z',True)

    def test_invalid_image_and_unattested_provenance_rejected(self):
        session=self.session();bottle=self.dataset.bottle('TEST')['bottle_id']
        path=self.root/'bad.jpg';path.write_bytes(b'not a photograph')
        with self.assertRaises(OSError):self.dataset.capture(path,session,bottle,'2026-01-01T12:00:00Z',True)
        with self.assertRaises(ValueError):self.dataset.capture(path,session,bottle,'2026-01-01T12:00:00Z',False)

    def test_timezone_and_duplicate_inventory_reference(self):
        with self.assertRaises(ValueError):capture.timestamp('2026-01-01T12:00:00')
        self.dataset.bottle('EXISTING')
        with self.assertRaises(ValueError):self.dataset.bottle('EXISTING')

    def test_multilabel_and_negative_visibility(self):
        annotation=capture.blank_annotation();annotation['labels'].update(RAYADURA=1,DEFORMACION=1)
        capture.check_annotation(annotation)
        annotation['labels']['TAPA_DEFECTUOSA']=0
        with self.assertRaises(ValueError):capture.check_annotation(annotation)
        annotation['evaluable']['cap']=True
        capture.check_annotation(annotation)
        annotation['labels']['RAYADURA']=True
        with self.assertRaises(ValueError):capture.check_annotation(annotation)

    def test_conformity_cannot_be_inferred(self):
        annotation=capture.blank_annotation();annotation['categories']['CONFORME']=True
        with self.assertRaises(ValueError):capture.check_annotation(annotation)

    def test_annotator_reviewer_separation_and_history(self):
        row=self.photo();annotation=capture.blank_annotation()
        self.dataset.annotate(row['sample_id'],annotation,'ANOTADOR')
        with self.assertRaises(ValueError):self.dataset.annotate(row['sample_id'],annotation,'ANOTADOR',True)
        self.dataset.annotate(row['sample_id'],annotation,'REVISOR',True)
        first=self.root/'reviews'/row['sample_id']/'000001.jsonl';before=first.read_bytes()
        annotation['notes']='Correction test only'
        self.dataset.annotate(row['sample_id'],annotation,'ANOTADOR')
        self.assertEqual(first.read_bytes(),before)
        self.assertEqual(self.dataset.validate()['independently_reviewed_images'],0)

    def test_history_tampering_is_detected(self):
        row=self.photo();annotation=capture.blank_annotation()
        self.dataset.annotate(row['sample_id'],annotation,'A');self.dataset.annotate(row['sample_id'],annotation,'B',True)
        path=self.root/'reviews'/row['sample_id']/'000001.jsonl';record=capture.rows(path)[0]
        record['annotation']['notes']='tampered'
        path.write_text(json.dumps(record)+'\n',encoding='utf-8')
        with self.assertRaises(ValueError):self.dataset.validate()

    def test_image_hash_tampering_detected(self):
        row=self.photo();(self.root/row['image']).write_bytes(b'changed')
        with self.assertRaises(ValueError):self.dataset.validate()

    def test_transitive_bottle_and_session_components_prevent_leaks(self):
        first=self.photo(1);second_session=self.session()
        self.photo(2,session=second_session,bottle=first['bottle_id'])
        self.photo(3,session=second_session)
        self.assertEqual(len(self.dataset.components()),1)
        proposal=self.dataset.propose()
        self.dataset.validate(proposal)
        proposal['assignments'][first['sample_id']]='test'
        with self.assertRaisesRegex(ValueError,'Fuga'):self.dataset.validate(proposal)

    def test_three_independent_components_allow_three_partitions(self):
        for number in (1,2,3):self.photo(number)
        proposal=self.dataset.propose()
        self.assertEqual(set(proposal['assignments'].values()),set(capture.SPLITS))
        self.assertEqual(proposal,self.dataset.propose())
        self.dataset.validate(proposal)

    def test_coverage_counts_bottles_instead_of_photos(self):
        row=self.photo(1);other=self.photo(2,session=row['session_id'],bottle=row['bottle_id'])
        annotation=capture.blank_annotation();annotation['labels']['RAYADURA']=1
        for sample in (row,other):
            self.dataset.annotate(sample['sample_id'],annotation,'A');self.dataset.annotate(sample['sample_id'],annotation,'B',True)
        result=self.dataset.validate()
        self.assertEqual(result['reviewed_labels']['RAYADURA']['positive'],2)
        self.assertEqual(result['bottles_with_reviewed_positive_evidence']['RAYADURA'],1)


if __name__=='__main__':unittest.main(verbosity=2)
