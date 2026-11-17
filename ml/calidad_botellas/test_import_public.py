"""Prueba conversión y protección con imágenes de fixture, nunca datos entrenables."""
from pathlib import Path
import json
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from PIL import Image
import yaml

from . import import_public as public


class PublicImportTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory(prefix='epp_public_import_')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.public_root = self.root / 'public'
        context = patch.object(public, 'PUBLIC_ROOT', self.public_root)
        context.start()
        self.addCleanup(context.stop)
        self.source = self.root / 'source'
        (self.source / 'train/images').mkdir(parents=True)
        (self.source / 'train/labels').mkdir()
        Image.new('RGB', (80, 100), 'gray').save(self.source / 'train/images/a.png')
        (self.source / 'train/labels/a.txt').write_text('0 0.5 0.5 0.5 0.5\n', encoding='utf-8')
        config = {'names': ['Broken Cap', 'Good Cap', 'No Cap'], 'nc': 3,
                  'roboflow': {'workspace': 'product-defect-detection', 'project': 'bottle-defects-o4gnx', 'version': 26, 'license': 'CC BY 4.0'}}
        (self.source / 'data.yaml').write_text(yaml.safe_dump(config), encoding='utf-8')

    def run_import(self, name='run', fmt='yolo'):
        return public.import_dataset('roboflow_caps_v26', self.source, self.public_root / 'imports' / name, fmt,
                                     self.root / 'references', self.public_root / 'imports')

    def test_positive_mapping_never_infers_negatives_or_conformity(self):
        source = public.source_definition('roboflow_caps_v26')
        self.assertEqual(public.map_positive_presence(['Broken Cap', 'Good Cap'], source),
                         {'RAYADURA': None, 'DEFORMACION': None, 'TAPA_DEFECTUOSA': 1})
        self.assertTrue(all(v is None for v in public.map_positive_presence(['Good Cap', 'No Cap', 'Broken Ring'], source).values()))

    def test_import_preserves_bytes_annotations_and_license(self):
        original = public.sha256(self.source / 'train/images/a.png')
        stats = self.run_import()
        self.assertEqual(stats['candidate_images'], 1)
        self.assertEqual(stats['training_approved_images'], 0)
        manifest = self.public_root / 'imports/run/samples.public.jsonl'
        row = json.loads(manifest.read_text())
        self.assertEqual(row['license'], 'CC-BY-4.0')
        self.assertIsNone(row['annotator'])
        self.assertIsNone(row['categories']['CONFORME'])
        self.assertFalse(row['training_eligible'])
        self.assertEqual(public.sha256(manifest.parent / row['image']), original)
        self.assertEqual(row['source_occurrences'][0]['annotations'][0]['source_yolo_line'], '0 0.5 0.5 0.5 0.5')

    def test_duplicate_images_merge_evidence_without_overwrite(self):
        (self.source / 'train/images/b.png').write_bytes((self.source / 'train/images/a.png').read_bytes())
        (self.source / 'train/labels/b.txt').write_text('1 0.5 0.5 0.5 0.5\n')
        stats = self.run_import()
        self.assertEqual(stats['duplicates_within_source'], 1)
        row = json.loads((self.public_root / 'imports/run/samples.public.jsonl').read_text())
        self.assertEqual(len(row['source_occurrences']), 2)
        self.assertEqual(set(row['source_classes']), {'Good Cap', 'Broken Cap'})
        with self.assertRaises(FileExistsError):
            self.run_import()

    def test_duplicate_previous_public_import_not_copied(self):
        self.run_import('first')
        stats = self.run_import('second')
        self.assertEqual(stats['external_duplicates'], 1)
        self.assertEqual(stats['copied_images'], 0)
        row = json.loads((self.public_root / 'imports/second/samples.public.jsonl').read_text())
        self.assertIsNone(row['image'])
        self.assertEqual(row['duplicate_of']['kind'], 'PREVIOUS_PUBLIC_IMPORT')

    def test_unmapped_class_stays_unknown_separate_bucket(self):
        (self.source / 'train/labels/a.txt').write_text('1 0.5 0.5 0.5 0.5\n')
        stats = self.run_import()
        self.assertEqual(stats['unmapped_only_images'], 1)
        row = json.loads((self.public_root / 'imports/run/samples.public.jsonl').read_text())
        self.assertIn('unmapped_review_only', row['image'])
        self.assertTrue(all(v is None for v in row['labels'].values()))

    def test_unsafe_path_and_invalid_box_rejected(self):
        for path in ['../private.png', '/etc/private.png', 'C:/private.png', '..\\private.png']:
            with self.assertRaises(ValueError):
                public.safe_path(self.source, path)
        (self.source / 'train/labels/a.txt').write_text('0 0.9 0.5 0.5 0.5\n')
        with self.assertRaises(ValueError):
            self.run_import()
        self.assertFalse((self.public_root / 'imports/run').exists())

    def test_missing_annotation_is_not_a_negative(self):
        (self.source / 'train/labels/a.txt').unlink()
        with self.assertRaises(ValueError):
            self.run_import()

    def test_export_identity_or_license_must_match(self):
        config = yaml.safe_load((self.source / 'data.yaml').read_text())
        config['roboflow']['license'] = 'Unknown'
        (self.source / 'data.yaml').write_text(yaml.safe_dump(config))
        with self.assertRaises(ValueError):
            self.run_import()
        self.assertFalse((self.public_root / 'imports/run').exists())

    def test_private_output_refused(self):
        with self.assertRaises(ValueError):
            public.import_dataset('roboflow_caps_v26', self.source, self.root / 'private', 'yolo')

    def test_coco_parser_and_unknown_class(self):
        folder = self.source / 'train'
        coco = {'categories': [{'id': 1, 'name': 'Broken Cap'}, {'id': 2, 'name': 'Unknown source defect'}],
                'images': [{'id': 10, 'file_name': 'images/a.png', 'width': 80, 'height': 100}],
                'annotations': [{'id': 1, 'image_id': 10, 'category_id': 1, 'bbox': [20, 25, 40, 50]},
                                {'id': 2, 'image_id': 10, 'category_id': 2, 'bbox': [20, 25, 40, 50]}]}
        (folder / '_annotations.coco.json').write_text(json.dumps(coco))
        (self.source / 'README.roboflow.txt').write_text('https://universe.roboflow.com/product-defect-detection/bottle-defects-o4gnx\nv26\nLicense: CC BY 4.0')
        stats = self.run_import(fmt='coco')
        self.assertEqual(stats['positive_image_counts']['TAPA_DEFECTUOSA'], 1)
        self.assertEqual(stats['source_instances']['Unknown source defect'], 1)
        coco['images'][0]['file_name'] = '../../private.png'
        (folder / '_annotations.coco.json').write_text(json.dumps(coco))
        with self.assertRaises(ValueError):
            list(public.parse_coco(self.source))


if __name__ == '__main__':
    unittest.main()
