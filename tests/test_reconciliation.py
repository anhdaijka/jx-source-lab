from pathlib import Path
import importlib.util
import json
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]

def load_module():
    scripts=ROOT/'scripts'
    if str(scripts) not in sys.path:sys.path.insert(0,str(scripts))
    spec=importlib.util.spec_from_file_location('reconcile_internet_research',scripts/'reconcile_internet_research.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module

class TestInternetReconciliation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.module=load_module()

    def test_package_claims_never_count_as_first_party(self):
        evidence=self.module.pkg('evidence/evidence-ledger.md','line 5','KX-BG-01')
        self.assertEqual(evidence['evidence_class'],'LEGACY_LEAD')
        self.assertEqual(evidence['source_family'],'internet_research_package')

    def test_cross_source_claim_has_raw_and_first_party(self):
        claim=next(row for row in self.module.CLAIMS if row[0]=='IR001')
        families={row['source_family'] for row in claim[-1]}
        self.assertIn('lab_raw_story',families)
        self.assertIn('first_party_web',families)

    def test_no_unresolved_material_conflict_or_central_blocker(self):
        self.assertFalse(any(row['centrality']=='CENTRAL_BLOCKER' for row in self.module.UNRESOLVED))
        self.assertFalse(any(row['narrative_impact']=='MATERIAL' and row['resolution_status']!='RESOLVED' for row in self.module.CONFLICTS))

    def test_every_dossier_claim_exists(self):
        ids={row[0] for row in self.module.CLAIMS}
        for _,_,_,refs in self.module.ARC_SPECS:self.assertTrue(set(refs)<=ids)

    def test_new_schema_files_parse(self):
        json.loads((ROOT/'schemas'/'game-story-dossier.schema.json').read_text(encoding='utf-8'))

    def test_generated_managed_edges_preserve_both_labels_when_available(self):
        path=ROOT/'generated'/'records'/'edges'/'task-reference-edges.jsonl'
        edges=[json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line]
        managed=[row for row in edges if row['relation']=='manages_sub']
        if managed and 'managed_inline_name' in managed[0]:
            self.assertTrue(all('label_relation' in row for row in managed))
            self.assertTrue(any(row['label_relation']=='VARIANT' for row in managed))

    def test_post50_macro_order_and_semantic_join_guard(self):
        self.assertEqual(self.module.POST50_TASK_ORDER,(13,14,15,17,16,18,21,19,20,22,23,24))
        reconstruction=self.module.build_post50_reconstruction()
        self.assertEqual(reconstruction['managed_inline_subtask_count'],77)
        self.assertEqual(reconstruction['blocked_standalone_join_count'],77)
        self.assertTrue(all(
            subtask['semantic_join_status']=='ID_REUSE_VARIANT' and subtask['standalone_content_usable'] is False
            for family in reconstruction['task_families'] for subtask in family['managed_subtasks']
        ))

    def test_arc06_uses_validated_phase_claim_order(self):
        arc=next(row for row in self.module.ARC_SPECS if row[0]=='arc-06')
        self.assertEqual(arc[3],['IR003','IR022','IR023','IR024','IR025','IR018'])
        phase_claims=[row['claim_id'] for row in self.module.POST50_PHASES]
        self.assertEqual(phase_claims,['IR022','IR023','IR024','IR025'])

if __name__=='__main__':unittest.main()
