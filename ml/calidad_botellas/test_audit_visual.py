"""Las imágenes/etiquetas artificiales son fixtures temporales, no datos reales."""
from copy import deepcopy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

import cv2
import numpy as np

from . import audit_visual as visual


class VisualAuditTests(unittest.TestCase):
    def test_bk_tree_finds_all_candidates_in_radius(self):
        tree = visual.BKTree()
        for i, value in enumerate([0, 1, 3, 255, 1]):
            tree.add(value, i)
        self.assertEqual(set(tree.find(0, 1)), {0, 1, 4})
        self.assertEqual(set(tree.find(255, 0)), {3})

    def test_metrics_blur_resolution_hash_and_damage(self):
        with TemporaryDirectory() as temp:
            path = Path(temp) / 'fixture.png'
            cv2.imwrite(str(path), np.full((100, 80, 3), 100, np.uint8))
            metrics, *_ = visual.inspect_image(path, 'wrong_hash')
            self.assertIn('possible_blur', metrics['flags'])
            self.assertIn('low_resolution', metrics['flags'])
            self.assertIn('hash_mismatch', metrics['flags'])
            path.write_bytes(b'not an image')
            with self.assertRaises(ValueError):
                visual.inspect_image(path)

    def test_distribution_never_infers_negative_from_unknown(self):
        base = {'source': 'test', 'flags': [], 'semantic_flags': [], 'metrics': None}
        rows = [dict(base, labels={'RAYADURA': 1, 'DEFORMACION': 1, 'TAPA_DEFECTUOSA': None}),
                dict(base, labels={'RAYADURA': 0, 'DEFORMACION': None, 'TAPA_DEFECTUOSA': None})]
        original = deepcopy(rows)
        stats = visual.distributions(rows)['test']
        self.assertEqual(stats['labels']['RAYADURA'], {'positive': 1, 'negative': 1, 'unknown': 0})
        self.assertEqual(stats['labels']['TAPA_DEFECTUOSA'], {'positive': 0, 'negative': 0, 'unknown': 2})
        self.assertEqual(stats['positive_overlap']['RAYADURA + DEFORMACION'], 1)
        self.assertEqual(rows, original)

    def test_complete_audit_keeps_sources_and_tracks_exact_duplicates(self):
        with TemporaryDirectory(prefix='epp_visual_test_') as temp:
            root = Path(temp)
            imported, reference = root / 'import', root / 'reference'
            (imported / 'images').mkdir(parents=True)
            (reference / 'images').mkdir(parents=True)
            original = np.random.default_rng(5).integers(10, 230, (300, 250, 3), dtype=np.uint8)
            cv2.imwrite(str(imported / 'images/a.png'), original)
            (imported / 'images/b.png').write_bytes((imported / 'images/a.png').read_bytes())
            (imported / 'images/c.png').write_bytes(b'broken fixture')
            cv2.imwrite(str(reference / 'images/epp.png'), np.full((200, 100, 3), 120, np.uint8))
            (imported / 'STATUS.json').write_text('{"status":"COMPLETED"}')
            rows = []
            for index, name in enumerate(['a.png', 'b.png', 'c.png']):
                row = {'sample_id': f'fixture-{index}', 'image': 'images/'+name,
                       'dataset_id': 'fixture', 'image_sha256': visual.sha256(imported/'images'/name),
                       'labels': {'RAYADURA': 1 if index == 0 else None, 'DEFORMACION': None, 'TAPA_DEFECTUOSA': None},
                       'license': 'Test fixture only', 'license_url': '', 'source_url': '', 'source_creators': ['Test'],
                       'source_classes': ['scuff_marg'], 'source_occurrences': [{'relative': name, 'split': 'train' if index == 0 else 'test', 'annotations': []}],
                       'filename_source_groups': ['same-origin'], 'label_scope': 'scene', 'width': 250, 'height': 300}
                rows.append(row)
            (imported/'samples.public.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in rows))
            epp = {'sample_id': 'epp-test', 'image': 'images/epp.png', 'image_sha256': visual.sha256(reference/'images/epp.png'),
                   'labels': dict.fromkeys(visual.LABELS), 'run_id': 'fixture-run', 'track_id': 1,
                   'quality': {'width': 100, 'height': 200}, 'annotation_status': 'PENDING'}
            (reference/'samples.jsonl').write_text(json.dumps(epp)+'\n')
            before = {str(p): visual.sha256(p) for d in [imported, reference] for p in d.rglob('*') if p.is_file()}
            output = root/'datasets/publicos_calidad_botellas/audits/test'
            with patch.object(visual, 'ROOT', root):
                summary = visual.audit([imported], reference, None, output)
                with self.assertRaises(FileExistsError):
                    visual.audit([imported], reference, None, output)
            self.assertEqual(summary['public_images'], 3)
            self.assertEqual(summary['epp_reference_images'], 1)
            self.assertEqual(len(summary['exact_duplicate_groups']), 1)
            self.assertEqual(summary['visual_candidate_pairs_total'], 1)
            self.assertEqual(summary['filename_groups_crossing_source_partitions'], 1)
            self.assertEqual(summary['sources']['fixture']['technical_flags']['unreadable_or_damaged'], 1)
            self.assertTrue((output/'index.html').is_file())
            self.assertTrue((output/'INFORME_CALIDAD.md').is_file())
            self.assertNotIn('AUDIT_DATA_HERE', (output/'index.html').read_text(encoding='utf-8'))
            self.assertEqual(before, {str(p): visual.sha256(p) for d in [imported, reference] for p in d.rglob('*') if p.is_file()})

    def test_output_cannot_be_inside_originals(self):
        with self.assertRaises(ValueError):
            visual.audit([], 'unused', None, visual.ROOT/'media/forbidden')


if __name__ == '__main__':
    unittest.main()
