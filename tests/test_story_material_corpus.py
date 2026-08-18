import gzip
import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "schemas" / "task-story-packet.schema.json"
CORPUS_DIR = ROOT / "generated" / "story-material-r2"
PACKETS_PART1 = CORPUS_DIR / "corpus" / "task-story-packets-part1.jsonl.gz"
PACKETS_PART2 = CORPUS_DIR / "corpus" / "task-story-packets-part2.jsonl.gz"
DOSSIER_PATH = ROOT / "research" / "reconstruction" / "story-families" / "009d-than-the-chi-me.json"

class TestStoryMaterialCorpus(unittest.TestCase):
    def test_schema_and_files_exist(self):
        self.assertTrue(SCHEMA_PATH.exists(), "Schema file missing")
        self.assertTrue(PACKETS_PART1.exists(), "Part 1 packets missing")
        self.assertTrue(PACKETS_PART2.exists(), "Part 2 packets missing")
        self.assertTrue(DOSSIER_PATH.exists(), "Reconstruction dossier missing")
        self.assertTrue((CORPUS_DIR / "manifest.json").exists(), "Manifest missing")
        self.assertTrue((CORPUS_DIR / "narrative-coverage-report.json").exists(), "Coverage report missing")
        self.assertTrue((CORPUS_DIR / "search" / "task-index.json").exists(), "Task index missing")
        self.assertTrue((CORPUS_DIR / "topology" / "managed-order-edges.json").exists(), "Managed edges missing")
        self.assertTrue((CORPUS_DIR / "topology" / "explicit-transition-edges.json").exists(), "Explicit edges missing")

    def test_packet_structure_and_counts(self):
        packets = []
        for path in (PACKETS_PART1, PACKETS_PART2):
            with gzip.open(path, "rt", encoding="utf-8") as f:
                for line in f:
                    packets.append(json.loads(line))

        self.assertEqual(len(packets), 631, "Expected 631 subtask packets across full corpus")

        # Test subtask 0134 packet
        p_0134 = next((p for p in packets if p["subtask"]["id_hex"] == "0000000000000134"), None)
        self.assertIsNotNone(p_0134, "Subtask 0134 packet missing")

        # 1. No generic extraction task-ID hardcoded semantic claims
        self.assertNotIn("prior_knowledge", p_0134.get("player_knowledge_and_state", {}), "Generic extractor must not inject task-ID semantic state")

        # 2. Every DIRECT claim must have evidence_refs
        for claim in p_0134["source_claims"]:
            if claim["status"] == "DIRECT":
                self.assertTrue(len(claim["evidence_refs"]) > 0, f"DIRECT claim {claim['claim_id']} has no evidence_refs")

        # 3. Evidence IDs must be stable and properly formatted
        for node in p_0134["extracted_evidence"]["evidence_nodes"]:
            self.assertTrue(node["evidence_id"].startswith("EID:000000000000009D:0000000000000134:"), f"Invalid evidence ID format: {node['evidence_id']}")

        # 4. Speaker resolution validation (no arbitrary prefix treated as explicit speaker)
        unresolved_nodes = [n for n in p_0134["extracted_evidence"]["evidence_nodes"] if n["speaker_resolution"] == "UNRESOLVED"]
        for node in unresolved_nodes:
            self.assertIsNone(node["speaker_id"], f"UNRESOLVED speaker node must have speaker_id=None: {node}")

        # 5. MANAGED_ORDER is NOT labeled as EXPLICIT_ASK_ACCEPT
        for edge in p_0134["topology"]["incoming_edges"]:
            if edge["edge_type"] == "MANAGED_ORDER":
                self.assertNotEqual(edge["edge_type"], "EXPLICIT_ASK_ACCEPT")

    def test_coverage_report_semantics(self):
        with open(CORPUS_DIR / "narrative-coverage-report.json", "r", encoding="utf-8") as f:
            report = json.load(f)

        self.assertEqual(report["packets_generated"], 631)
        self.assertIn("extraction_coverage_rate", report)
        self.assertNotIn("semantic_reconstruction_coverage_rate", report, "Extraction coverage must not be labeled as semantic reconstruction coverage")

    def test_reconstruction_dossier_009d(self):
        with open(DOSSIER_PATH, "r", encoding="utf-8") as f:
            dossier = json.load(f)

        self.assertEqual(dossier["family_id_hex"], "000000000000009D")
        self.assertEqual(dossier["subtask_count"], 15)
        self.assertEqual(dossier["reconstruction_status"], "RECONSTRUCTION_SYNTHESIS_EVIDENCED")
        self.assertIn("Layer 3 Synthesis", dossier["causal_reconstruction_synthesis"])

    def test_determinism_rerun(self):
        """Run generator twice and verify output packets match identically."""
        with open(PACKETS_PART1, "rb") as f:
            part1_before = f.read()

        # Run generator again
        res = subprocess.run([sys.executable, "scripts/build_story_material_corpus.py"], cwd=str(ROOT), capture_output=True, text=True)
        self.assertEqual(res.returncode, 0, f"Rerun failed: {res.stderr}")

        with open(PACKETS_PART1, "rb") as f:
            part1_after = f.read()

        self.assertEqual(part1_before, part1_after, "Part 1 packets binary output changed across rerun!")

if __name__ == "__main__":
    unittest.main()
