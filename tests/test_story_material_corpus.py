import gzip
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "schemas" / "task-story-packet.schema.json"
CORPUS_DIR = ROOT / "generated" / "story-material-r2"
PACKETS_GZ = CORPUS_DIR / "task-story-packets.jsonl.gz"
DOSSIER_PATH = ROOT / "research" / "reconstruction" / "story-families" / "009d-than-the-chi-me.json"
HANDOFF_0134_PATH = ROOT / "research" / "handoffs" / "ga01-0134-dialogue-evidence-r1.json"

class TestStoryMaterialCorpus(unittest.TestCase):
    def test_schema_and_files_exist(self):
        self.assertTrue(SCHEMA_PATH.exists(), "Schema file missing")
        self.assertTrue(PACKETS_GZ.exists(), "Packets gzip missing")
        self.assertTrue(DOSSIER_PATH.exists(), "Reconstruction dossier missing")
        self.assertTrue((CORPUS_DIR / "manifest.json").exists(), "Manifest missing")
        self.assertTrue((CORPUS_DIR / "narrative-coverage-report.json").exists(), "Coverage report missing")

    def test_packet_structure_and_count(self):
        packets = []
        with gzip.open(PACKETS_GZ, "rt", encoding="utf-8") as f:
            for line in f:
                packets.append(json.loads(line))
                
        self.assertEqual(len(packets), 15, "Expected 15 subtask packets for Family 009D")
        
        # Check subtask 0134
        p_0134 = next((p for p in packets if p["subtask"]["id_hex"] == "0000000000000134"), None)
        self.assertIsNotNone(p_0134, "Subtask 0134 packet not found")
        
        self.assertEqual(p_0134["subtask"]["name_inline"], "Kỳ Môn Độn Giáp")
        self.assertEqual(p_0134["characters_and_npcs"]["giver_npc"]["name"], "Bất Động Tiên Sinh")
        self.assertEqual(p_0134["characters_and_npcs"]["turn_in_npc"]["name"], "Điềm Tửu Thúc")
        
        # Verify 12 sects reveal in new knowledge
        new_k = " ".join(p_0134["player_knowledge_and_state"]["new_knowledge"])
        self.assertIn("Twelve Great Sects", new_k)
        self.assertIn("Bất Động Tiên Sinh", new_k)
        self.assertIn("Thu Di", new_k)
        
        # Verify node types separation
        nodes = p_0134["narrative_texts"]["ordered_nodes"]
        node_types = {n["node_type"] for n in nodes}
        self.assertIn("NPC_DIALOGUE", node_types)
        self.assertIn("PLAYER_TASK_NARRATION", node_types)
        self.assertIn("SYSTEM_UI_TEXT", node_types)

    def test_reconstruction_dossier(self):
        with open(DOSSIER_PATH, "r", encoding="utf-8") as f:
            dossier = json.load(f)
            
        self.assertEqual(dossier["family_id_hex"], "000000000000009D")
        self.assertEqual(dossier["subtask_count"], 15)
        self.assertTrue(dossier["reconstruction_status"].startswith("RECONSTRUCTION_READY"))

    def test_audit_against_0134_handoff(self):
        if HANDOFF_0134_PATH.exists():
            with open(HANDOFF_0134_PATH, "r", encoding="utf-8") as f:
                handoff = json.load(f)
                
            self.assertEqual(handoff["task_metadata"]["subtask_name_vi"], "Kỳ Môn Độn Giáp")
            self.assertEqual(handoff["npc_cast_and_roles"]["giver_and_informant"]["name_vi"], "Bất Động Tiên Sinh")
            self.assertEqual(handoff["npc_cast_and_roles"]["turn_in_and_equipment_provider"]["name_vi"], "Điềm Tửu Thúc")

if __name__ == "__main__":
    unittest.main()
