"""Comprobaciones de solo lectura y de las salidas de revisión pendiente."""
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from . import pending_contact_sheet as sheet


class PendingContactSheetTests(unittest.TestCase):
    def test_exact_pending_set_and_original_metadata(self):
        rows = sheet.pending_records(sheet.BASE)
        self.assertEqual(len(rows), 9)
        self.assertEqual(len({r['sample_id'] for r in rows}), 9)
        coverage = json.loads((sheet.BASE / sheet.SOURCES[2]).read_text(encoding='utf-8'))
        self.assertEqual({r['sample_id'] for r in rows}, {r['sample_id'] for r in coverage['pending']})

    def test_original_images_and_zoom_are_present(self):
        rows = sheet.pending_records(sheet.BASE)
        html = sheet.render(rows)
        self.assertEqual(html.count('<article '), 9)
        for row in rows:
            for key in ('sample_id', 'expected_hash', 'group_id', 'proposed_partition', 'original_url'):
                self.assertIn(row[key], html)
        self.assertIn('max="600"', html)
        self.assertIn('100 % original', html)
        malicious = dict(rows[0], file_name='<script>alert(1)</script>')
        self.assertNotIn('<script>alert(1)</script>', sheet.render([malicious]))

    def test_export_preserves_evidence_and_leaves_decisions_null(self):
        rows = sheet.pending_records(sheet.BASE)
        with TemporaryDirectory(prefix='pending_sheet_') as tmp:
            destination = Path(tmp)
            for name in sheet.SOURCES:
                (destination / name).write_bytes((sheet.BASE / name).read_bytes())
            with patch.object(sheet, 'pending_records', return_value=rows):
                result = sheet.generate(destination)
            self.assertEqual(result['verified_hashes'], 9)
            output = sheet.read_rows(destination / sheet.OUTPUTS[1])
            for original, record in zip(rows, output):
                for key, value in original.items():
                    self.assertEqual(value, record[key])
                decision = record['pending_decision']
                self.assertTrue(all(v is None for v in decision['labels'].values()))
                self.assertTrue(all(v is None for v in decision['evaluability'].values()))
                self.assertIsNone(decision['reviewer'])
                self.assertIsNone(decision['CONFORME'])
            with self.assertRaises(FileExistsError):
                sheet.generate(destination)

    def test_altered_image_hash_is_rejected(self):
        original = sheet.digest
        def altered(path):
            return '0' * 64 if Path(path).suffix == '.jpg' else original(path)
        with patch.object(sheet, 'digest', side_effect=altered):
            with self.assertRaisesRegex(ValueError, 'Hash'):
                sheet.pending_records(sheet.BASE)

    def test_inconsistent_report_is_rejected(self):
        original = Path.read_text
        def altered(path, *args, **kwargs):
            text = original(path, *args, **kwargs)
            if path.name == sheet.SOURCES[1]:
                text = text.replace('- mendeley_kthmmbsh8t_v1:', '- changed:', 1)
            return text
        with patch.object(Path, 'read_text', altered):
            with self.assertRaisesRegex(ValueError, 'informe'):
                sheet.pending_records(sheet.BASE)
