from pathlib import Path
import importlib.util
import json
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]

def load_validator():
    scripts=ROOT/'scripts'
    if str(scripts) not in sys.path:sys.path.insert(0,str(scripts))
    spec=importlib.util.spec_from_file_location('validate_novel_handoff',scripts/'validate_novel_handoff.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module

class TestNovelHandoff(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.validator=load_validator()

    def test_handoff_integrity(self):
        result=self.validator.validate()
        self.assertEqual(result['status'],'NOVEL_HANDOFF_READY',result['errors'])
        self.assertFalse(result['errors'])

    def test_manifest_has_zero_blockers(self):
        manifest=json.loads((ROOT/'generated'/'novel-handoff'/'handoff-manifest.json').read_text(encoding='utf-8'))
        self.assertEqual(manifest['unresolved_counts']['CENTRAL_BLOCKER'],0)
        self.assertEqual(manifest['unresolved_counts']['UNRESOLVED_MATERIAL_CONFLICT'],0)
        self.assertTrue(manifest['raw_proprietary_payloads_excluded'])

    def test_no_proprietary_payload_file_types(self):
        root=ROOT/'generated'/'novel-handoff'
        prohibited={'.pak','.exe','.dll','.zip','.rar','.7z','.bin','.spr'}
        self.assertFalse([path for path in root.rglob('*') if path.is_file() and path.suffix.lower() in prohibited])

    def test_source_story_bible_projections_exist(self):
        root=ROOT/'generated'/'novel-handoff'
        required=[
            'game-story/plot-thread-index.json',
            'game-story/mystery-payoff-map.json',
            'characters/character-index.json',
            'factions/faction-index.json',
            'relationships/source-relationship-map.json',
            'knowledge/source-knowledge-timeline.json',
        ]
        self.assertFalse([path for path in required if not (root/path).is_file()])

    def test_manifest_preserves_evidence_commit_and_richer_counts(self):
        manifest=json.loads((ROOT/'generated'/'novel-handoff'/'handoff-manifest.json').read_text(encoding='utf-8'))
        self.assertEqual(manifest['source_lab_commit'],'8d7645a4d659d0baac86c9eafc7fc0ef18c90254')
        for key in (
            'promoted_plot_thread_count','promoted_mystery_payoff_count',
            'promoted_character_trajectory_count','promoted_faction_trajectory_count',
            'source_relationship_count','source_knowledge_event_count',
        ):
            self.assertGreater(manifest[key],0,key)

if __name__=='__main__':unittest.main()
