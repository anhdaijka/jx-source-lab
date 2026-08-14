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

if __name__=='__main__':unittest.main()
