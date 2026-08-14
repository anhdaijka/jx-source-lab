from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[1]
def test_required_files_exist():
    for p in ['AGENTS.md','README.md','lab.toml','scripts/jxlab.py','database/schema.sql','docs/reconstruction-protocol.md','docs/pak-forensics-protocol.md','prompts/00-first-codex-session.md']:
        assert (ROOT/p).exists(),p
def test_json_schemas_parse():
    for p in (ROOT/'schemas').glob('*.json'):json.loads(p.read_text(encoding='utf-8'))
