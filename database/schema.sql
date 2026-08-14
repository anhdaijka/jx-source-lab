PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS source_records (id INTEGER PRIMARY KEY, source_id TEXT NOT NULL, evidence_class TEXT NOT NULL, path TEXT NOT NULL, sha256 TEXT, edition TEXT, encoding TEXT, locator TEXT, notes TEXT);
CREATE INDEX IF NOT EXISTS idx_source_records_path ON source_records(path);
CREATE INDEX IF NOT EXISTS idx_source_records_sha ON source_records(sha256);
CREATE TABLE IF NOT EXISTS tasks (id INTEGER PRIMARY KEY, task_key TEXT NOT NULL, parent_key TEXT, name_cn TEXT, name_vi TEXT, giver_npc_key TEXT, turnin_npc_key TEXT, location_key TEXT, raw_payload_json TEXT);
CREATE INDEX IF NOT EXISTS idx_tasks_key ON tasks(task_key);
CREATE INDEX IF NOT EXISTS idx_tasks_parent ON tasks(parent_key);
CREATE TABLE IF NOT EXISTS task_dependencies (task_key TEXT NOT NULL, prerequisite_key TEXT NOT NULL, relation TEXT, source_record_id INTEGER, FOREIGN KEY(source_record_id) REFERENCES source_records(id));
CREATE TABLE IF NOT EXISTS dialogues (id INTEGER PRIMARY KEY, dialogue_key TEXT, task_key TEXT, npc_key TEXT, phase TEXT, language TEXT, text TEXT NOT NULL, source_record_id INTEGER, FOREIGN KEY(source_record_id) REFERENCES source_records(id));
CREATE TABLE IF NOT EXISTS npcs (id INTEGER PRIMARY KEY, npc_key TEXT NOT NULL, name_cn TEXT, name_vi TEXT, faction_key TEXT, location_key TEXT, raw_payload_json TEXT);
CREATE TABLE IF NOT EXISTS sects (id INTEGER PRIMARY KEY, sect_key TEXT NOT NULL, name_cn TEXT, name_vi TEXT, raw_payload_json TEXT);
CREATE TABLE IF NOT EXISTS skills (id INTEGER PRIMARY KEY, skill_key TEXT NOT NULL, name_cn TEXT, name_vi TEXT, sect_key TEXT, route_key TEXT, level_req TEXT, description TEXT, raw_payload_json TEXT);
CREATE TABLE IF NOT EXISTS items (id INTEGER PRIMARY KEY, item_key TEXT NOT NULL, name_cn TEXT, name_vi TEXT, item_type TEXT, description TEXT, raw_payload_json TEXT);
CREATE TABLE IF NOT EXISTS locations (id INTEGER PRIMARY KEY, location_key TEXT NOT NULL, name_cn TEXT, name_vi TEXT, map_key TEXT, description TEXT, raw_payload_json TEXT);
CREATE TABLE IF NOT EXISTS assets (id INTEGER PRIMARY KEY, asset_key TEXT, source_archive TEXT, internal_path TEXT, output_path TEXT, sha256 TEXT, file_type TEXT, width INTEGER, height INTEGER, raw_payload_json TEXT);
CREATE INDEX IF NOT EXISTS idx_assets_key ON assets(asset_key);
CREATE INDEX IF NOT EXISTS idx_assets_archive ON assets(source_archive);
CREATE TABLE IF NOT EXISTS asset_sources (
  asset_id INTEGER NOT NULL,
  source_record_id INTEGER NOT NULL,
  locator TEXT NOT NULL,
  PRIMARY KEY(asset_id, source_record_id),
  FOREIGN KEY(asset_id) REFERENCES assets(id),
  FOREIGN KEY(source_record_id) REFERENCES source_records(id)
);
CREATE TABLE IF NOT EXISTS entity_sources (entity_type TEXT NOT NULL, entity_key TEXT NOT NULL, source_record_id INTEGER NOT NULL, locator TEXT, FOREIGN KEY(source_record_id) REFERENCES source_records(id));
CREATE TABLE IF NOT EXISTS claims (id INTEGER PRIMARY KEY, claim_key TEXT NOT NULL, claim_text TEXT NOT NULL, status TEXT NOT NULL, notes TEXT);
CREATE TABLE IF NOT EXISTS claim_evidence (claim_id INTEGER NOT NULL, source_record_id INTEGER NOT NULL, support_type TEXT, locator TEXT, FOREIGN KEY(claim_id) REFERENCES claims(id), FOREIGN KEY(source_record_id) REFERENCES source_records(id));

-- Release-wide generic index. Domain tables above remain convenient query
-- surfaces; these tables preserve every heterogeneous record and its lineage.
CREATE TABLE IF NOT EXISTS corpus_files (
  path TEXT PRIMARY KEY,
  sha256 TEXT NOT NULL,
  record_count INTEGER NOT NULL,
  parser_versions_json TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS corpus_entities (
  entity_key TEXT PRIMARY KEY,
  logical_key TEXT,
  entity_type TEXT NOT NULL,
  name TEXT,
  payload_json TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_corpus_entities_type ON corpus_entities(entity_type);
CREATE INDEX IF NOT EXISTS idx_corpus_entities_logical ON corpus_entities(logical_key);
CREATE TABLE IF NOT EXISTS corpus_entity_sources (
  entity_key TEXT NOT NULL,
  source_record_id INTEGER NOT NULL,
  PRIMARY KEY(entity_key, source_record_id),
  FOREIGN KEY(entity_key) REFERENCES corpus_entities(entity_key),
  FOREIGN KEY(source_record_id) REFERENCES source_records(id)
);
CREATE TABLE IF NOT EXISTS reference_edges (
  edge_key TEXT PRIMARY KEY,
  source_key TEXT NOT NULL,
  target_key TEXT NOT NULL,
  relation TEXT NOT NULL,
  resolution TEXT NOT NULL,
  payload_json TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_reference_edges_source ON reference_edges(source_key);
CREATE INDEX IF NOT EXISTS idx_reference_edges_target ON reference_edges(target_key);
CREATE INDEX IF NOT EXISTS idx_reference_edges_relation ON reference_edges(relation);
CREATE TABLE IF NOT EXISTS reference_edge_sources (
  edge_key TEXT NOT NULL,
  source_record_id INTEGER NOT NULL,
  PRIMARY KEY(edge_key, source_record_id),
  FOREIGN KEY(edge_key) REFERENCES reference_edges(edge_key),
  FOREIGN KEY(source_record_id) REFERENCES source_records(id)
);
CREATE TABLE IF NOT EXISTS features (
  id INTEGER PRIMARY KEY,
  feature_key TEXT NOT NULL,
  feature_type TEXT NOT NULL,
  name TEXT,
  raw_payload_json TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_features_key ON features(feature_key);
