"""Pruebas de propuestas; no cambian etiquetas reales ni autorizan entrenamiento."""
from copy import deepcopy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from . import select_review as selection


class SelectionTests(unittest.TestCase):
    def row(self, sample_id, group, day=None):
        return {'sample_id': sample_id, 'expected_hash': sample_id, 'role': 'PUBLIC', 'source': 'roboflow_caps_v26' if day else 'mendeley_test',
                'file_name': f'WIN_{day}_12_00_00_Pro.jpg' if day else sample_id+'.jpg',
                'source_groups': [group], 'labels': dict.fromkeys(selection.LABELS)}

    def test_transitive_grouping_covers_origin_visual_and_session(self):
        rows = [self.row('a','first'), self.row('b','first'), self.row('c','other'),
                self.row('d','cap1','20220704'), self.row('e','cap2','20220704')]
        groups, membership = selection.origin_groups(rows, [[1,2]])
        self.assertEqual(len(groups), 2)
        self.assertEqual(membership[0], membership[2])
        self.assertEqual(membership[3], membership[4])
        split = selection.propose_splits(groups)
        self.assertEqual(split[membership[3]], 'train')
        with self.assertRaises(ValueError):
            selection.origin_groups(rows, [[999]])

    def test_known_epp_similarity_requires_hold_without_selecting_epp(self):
        rows = [self.row('public','a'), dict(self.row('private','b'), role='EPP_REFERENCE')]
        groups, membership = selection.origin_groups(rows, [[0,1]])
        self.assertEqual(len(groups), 1)
        self.assertTrue(groups[0]['linked_to_epp_reference'])
        self.assertNotIn(1, membership)
        self.assertEqual(selection.propose_splits(groups)[membership[0]], 'HOLD_FOR_REVIEW')
        rows[1]['expected_hash']=rows[0]['expected_hash']
        groups,membership=selection.origin_groups(rows,[])
        self.assertTrue(groups[0]['linked_to_epp_reference'])
        self.assertEqual(selection.propose_splits(groups)[membership[0]], 'HOLD_FOR_REVIEW')

    def tiny_row(self, dimensions, classes=None):
        return {'occurrences':[{'annotations':[{'source_class': c, 'bbox_xywh_pixels':[0,0,*size]} for c,size in zip(classes or ['scuff_marg']*len(dimensions),dimensions)]}],
                'expected_width':400, 'expected_height':700, 'flags':[]}

    def test_small_regions_have_distinct_utilities_without_mutation(self):
        mapping = {'scuff_marg':'RAYADURA'}
        for row, expected in [(self.tiny_row([(8,80)]),'THIN_ELONGATED_TARGET_POTENTIALLY_USEFUL'),
                              (self.tiny_row([(8,10)]),'ONLY_SMALL_TARGET_REGIONS_NEEDS_DETAIL'),
                              (self.tiny_row([(8,10),(40,40)]),'OTHER_LARGER_TARGET_REGION_AVAILABLE'),
                              (self.tiny_row([(8,10)],['tear_marg']),'OUTSIDE_TARGET_TAXONOMY')]:
            before=deepcopy(row)
            result=selection.tiny_utility(row,mapping)
            self.assertEqual(result['category'],expected)
            self.assertEqual(row,before)

    def test_good_cap_never_becomes_conforme_or_negative(self):
        row=self.row('cap','cap','20220701')
        row.update(classes=['Good Cap'],flags=[],metrics={'aspect_ratio':1.77},expected_height=2160)
        before=deepcopy(row)
        cues=selection.review_cues(row)
        self.assertEqual(cues['conformity_candidate'],'CAP_GOOD_SOURCE_CUE_ONLY')
        self.assertIsNone(cues['conformity_confirmed'])
        self.assertIsNone(cues['joint_evaluation_confirmed'])
        self.assertEqual(row,before)

    def test_real_selection_balanced_unique_deterministic_and_no_known_leakage(self):
        audit=selection.ROOT/'datasets/publicos_calidad_botellas/audits/visual_v002'
        before={p.name:selection.sha256(p) for p in [audit/'metrics.jsonl',audit/'summary.json']}
        with TemporaryDirectory(prefix='epp_selection_test_') as temp:
            root=Path(temp)
            with patch.object(selection,'ROOT',root):
                output=root/'datasets/publicos_calidad_botellas/selections/test'
                summary=selection.prepare(audit,output)
                with self.assertRaises(FileExistsError):
                    selection.prepare(audit,output)
            selected=[json.loads(line) for line in (output/'review_selection.jsonl').read_text(encoding='utf-8').splitlines()]
            self.assertEqual(len(selected),100)
            self.assertEqual(len({r['sample_id'] for r in selected}),100)
            self.assertEqual(sorted(summary['selected_by_source'].values()),[50,50])
            self.assertEqual(summary['small_region_images'],945)
            self.assertEqual(sum(summary['small_region_utility'].values()),945)
            self.assertEqual(summary['origin_components'],202)
            self.assertFalse(summary['training_authorized'])
            self.assertEqual(summary['confirmed_conforming_bottles'],0)
            self.assertTrue(all(r['human_confirmation'] is None for r in selected))
            originals=[json.loads(line) for line in (audit/'metrics.jsonl').read_text(encoding='utf-8').splitlines()]
            original_map={row['sample_id']:row for row in originals}
            for row in selected:
                self.assertEqual(row['labels'],original_map[row['sample_id']]['labels'])
                self.assertEqual(original_map[row['sample_id']]['role'],'PUBLIC')
            assignments=[json.loads(line) for line in (output/'split_proposal.jsonl').read_text(encoding='utf-8').splitlines()]
            by_id={r['sample_id']:r for r in assignments}
            graph=json.loads((audit/'summary.json').read_text(encoding='utf-8'))['visual_candidate_groups']
            for group in graph:
                splits={by_id[originals[i]['sample_id']]['proposed_partition'] for i in group if originals[i]['role']=='PUBLIC'}
                self.assertLessEqual(len(splits),1)
            groups,membership=selection.origin_groups(originals,graph)
            registry=json.loads(Path(selection.__file__).with_name('public_sources.json').read_text(encoding='utf-8'))['sources']
            utilities={i:selection.tiny_utility(r,registry[r['source']]['positive_mapping']) for i,r in enumerate(originals) if r['role']=='PUBLIC'}
            cues={i:selection.review_cues(r) for i,r in enumerate(originals) if r['role']=='PUBLIC'}
            a,_=selection.select_review(originals,membership,cues,utilities)
            b,_=selection.select_review(originals,membership,cues,utilities)
            self.assertEqual(a,b)
            smaller,_=selection.select_review(originals,membership,cues,utilities,limit=10)
            self.assertEqual(len(smaller),10)
            self.assertEqual(sum(originals[i]['source'].startswith('mendeley_') for i in smaller),5)
            with self.assertRaises(ValueError):
                selection.select_review(originals,membership,cues,utilities,limit=101)
        self.assertEqual(before,{p.name:selection.sha256(p) for p in [audit/'metrics.jsonl',audit/'summary.json']})


if __name__ == '__main__':
    unittest.main()
