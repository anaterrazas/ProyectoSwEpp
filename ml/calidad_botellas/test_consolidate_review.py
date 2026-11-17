"""La consolidación es una capa independiente, sin mutar evidencia fuente."""
from copy import deepcopy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from . import consolidate_review as review


class HumanConsolidationTests(unittest.TestCase):
    directory = Path(__file__).resolve().parents[2] / 'datasets/publicos_calidad_botellas/selections/pretrain_v001'

    def rows(self):
        return review.read_rows(self.directory / 'review_selection.jsonl')

    def test_all_explicit_decisions_and_source_preservation(self):
        rows = self.rows()
        original = deepcopy(rows)
        results = [review.decide(r, 'test-time') for r in rows]
        self.assertEqual(rows, original)
        self.assertEqual(len(results), 100)
        self.assertEqual(sum(r['labels']['RAYADURA'] == 1 for r in results), 16)
        self.assertEqual(sum(r['labels']['DEFORMACION'] == 1 for r in results), 16)
        self.assertEqual(sum(r['labels']['TAPA_DEFECTUOSA'] == 1 for r in results), 36)
        self.assertEqual(sum(r['status'] == 'PENDING' for r in results), 9)
        for source, result in zip(rows, results):
            self.assertEqual(source['labels'], result['source_labels'])
            self.assertEqual(result['categories'], {'CONFORME': None, 'NO_EVALUABLE': None})
            self.assertIsNone(result['review_author']['identity'])
            self.assertFalse(result['training_authorized'])

    def test_good_cap_is_only_partial_negative(self):
        rows = [r for r in self.rows() if r['review_reason'].startswith('Good Cap:')]
        self.assertEqual(len(rows), 14)
        for row in rows:
            result = review.decide(row, 'test-time')
            self.assertEqual(result['labels'], {'RAYADURA': None, 'DEFORMACION': None, 'TAPA_DEFECTUOSA': 0})
            row['classes'].append('Broken Cap')
            with self.assertRaises(ValueError):
                review.decide(row, 'test-time')

    def test_original_cap_subtypes_are_all_preserved(self):
        results = [review.decide(r, 'test-time') for r in self.rows()]
        absent = [r for r in results if r['review_reason'].startswith('Mapeo condicional:')]
        self.assertEqual(len(absent), 12)
        self.assertTrue(all(r['cap_subtypes'] == ['TAPA_AUSENTE'] for r in absent))
        rings = [r for r in results if 'Broken Ring' in r['classes']]
        self.assertEqual(len(rings), 2)
        for row in rings:
            self.assertEqual(set(row['cap_subtypes']), {'ANILLO_ROTO', 'TAPA_MAL_COLOCADA'})

    def test_retention_and_exclusion_never_infer_labels(self):
        results = [review.decide(r, 'test-time') for r in self.rows()]
        deferred = [r for r in results if r['status'] != 'CONFIRMED_PARTIAL']
        self.assertEqual(len(deferred), 18)
        self.assertTrue(all(all(v is None for v in r['labels'].values()) for r in deferred))

    def test_unknown_reason_and_contradiction_rejected(self):
        row = self.rows()[0]
        row['review_reason'] = 'unapproved'
        with self.assertRaises(ValueError):
            review.decide(row, 'test-time')
        row = review.decide(self.rows()[0], 'test-time')
        row['categories']['CONFORME'] = 1
        with self.assertRaises(ValueError):
            review.validate_decision(row)

    def test_full_integration_hashes_groups_and_no_overwrite(self):
        before = {n: review.digest(self.directory / n) for n in review.INPUTS}
        with TemporaryDirectory(prefix='human_review_test_') as tmp:
            summary = review.consolidate(self.directory, tmp)
            self.assertEqual(summary['total_decisions'], 100)
            self.assertEqual(summary['image_hashes_verified'], 100)
            self.assertEqual(summary['errors'], [])
            output = Path(tmp) / 'human_review_v001.jsonl'
            first = output.read_bytes()
            self.assertEqual(len(review.read_rows(output)), 100)
            with self.assertRaises(FileExistsError):
                review.consolidate(self.directory, tmp)
            self.assertEqual(output.read_bytes(), first)
        self.assertEqual(before, {n: review.digest(self.directory / n) for n in review.INPUTS})

    def test_changed_hash_rejected_without_output(self):
        original_digest = review.digest
        def altered(path):
            return '0' * 64 if Path(path).suffix.lower() in ('.jpg', '.png', '.jpeg') else original_digest(path)
        with TemporaryDirectory(prefix='human_review_test_') as tmp:
            with patch.object(review, 'digest', side_effect=altered):
                with self.assertRaisesRegex(ValueError, 'Hash'):
                    review.consolidate(self.directory, tmp)
            self.assertEqual(list(Path(tmp).iterdir()), [])

    def test_duplicate_ids_and_origin_leak_rejected(self):
        row = self.rows()[0]
        with self.assertRaises(ValueError):
            review.indexed([row, row])
        original_read = review.read_rows
        def inconsistent(path):
            rows = original_read(path)
            if Path(path).name == 'split_proposal.jsonl':
                rows[0]['proposed_partition'] = 'wrong-partition'
            return rows
        with TemporaryDirectory(prefix='human_review_test_') as tmp:
            with patch.object(review, 'read_rows', side_effect=inconsistent):
                with self.assertRaisesRegex(ValueError, 'partición'):
                    review.consolidate(self.directory, tmp)
            self.assertEqual(list(Path(tmp).iterdir()), [])
