from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


def load_validator():
    path = ROOT / "scripts" / "validate_novel_source_supplement.py"
    spec = importlib.util.spec_from_file_location("validate_novel_source_supplement", path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


class TestNovelSourceSupplement(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.validator = load_validator()

    def test_novel_source_supplement_is_ready(self):
        result = self.validator.validate()
        self.assertEqual(result["status"], "NOVEL_SOURCE_SUPPLEMENT_READY", result["errors"])
        self.assertEqual(result["metrics"]["promoted_story_claims"], 0)


if __name__ == "__main__":
    unittest.main()
