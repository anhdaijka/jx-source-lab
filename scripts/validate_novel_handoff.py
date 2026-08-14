#!/usr/bin/env python3
"""Validate the curated novel handoff integrity boundary."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'generated'/'novel-handoff'
REPORT=ROOT/'generated'/'reports'/'novel-handoff-validation-report.json'
ALLOWED_SUFFIXES={'.json','.md'}
PROHIBITED_SUFFIXES={'.pak','.exe','.dll','.zip','.rar','.7z','.bin','.spr','.wav','.mp3','.png','.jpg','.jpeg'}
PROHIBITED_CREATIVE_MARKERS=('Tiêu Phùng','NovelOS','episode planning')

def load_json(path):return json.loads(path.read_text(encoding='utf-8'))
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def collect_claim_ids(value):
 found=[]
 if isinstance(value,dict):
  for key,item in value.items():
   if (key.endswith('claim_ids') or key=='claim_id'):
    found.extend(item if isinstance(item,list) else [item])
   found.extend(collect_claim_ids(item))
 elif isinstance(value,list):
  for item in value:found.extend(collect_claim_ids(item))
 return [item for item in found if isinstance(item,str) and item.startswith('IR')]

def validate():
 errors=[];checks={};metrics={}
 manifest_path=OUT/'handoff-manifest.json'
 if not manifest_path.exists():return {'status':'NOVEL_HANDOFF_BLOCKED','errors':['Missing handoff-manifest.json'],'checks':{},'metrics':{}}
 manifest=load_json(manifest_path);checks['manifest_parsed']=1
 concordance=load_json(ROOT/'research'/'reconciliation'/'lore-concordance.json')
 release_validation=load_json(ROOT/'generated'/'reports'/'release-validation-report.json')
 if manifest.get('handoff_status')!='NOVEL_HANDOFF_READY' or manifest.get('promotion_status')!='NOVEL_PROMOTION_READY':errors.append('Handoff is not promotion ready')
 if concordance.get('promotion_decision')!='NOVEL_PROMOTION_READY':errors.append('Persisted reconciliation is not promotion ready')
 if any(concordance.get('promotion_gates',{}).get(gate,{}).get('status')!='PASS' for gate in ('S3','S4','S5')):errors.append('A required promotion gate is not PASS')
 if concordance.get('central_blocker_count')!=0:errors.append('CENTRAL_BLOCKER remains')
 if concordance.get('unresolved_material_conflict_count')!=0:errors.append('Unresolved MATERIAL narrative conflict remains')
 if release_validation.get('status')!='PASS' or release_validation.get('errors'):errors.append('Research Release validation is not clean')
 counts=manifest.get('unresolved_counts',{})
 if counts.get('CENTRAL_BLOCKER')!=0 or counts.get('UNRESOLVED_MATERIAL_CONFLICT')!=0:errors.append('Manifest blocker counts are not zero')

 listed={row['path']:row for row in manifest.get('files',[])}
 actual={path.relative_to(OUT).as_posix():path for path in OUT.rglob('*') if path.is_file() and path.name!='handoff-manifest.json'}
 if set(listed)!=set(actual):errors.append('Manifest file list differs from actual payload files')
 for relative,path in actual.items():
  if listed.get(relative,{}).get('sha256')!=sha(path):errors.append(f'Hash mismatch: {relative}')
  if listed.get(relative,{}).get('bytes')!=path.stat().st_size:errors.append(f'Size mismatch: {relative}')
 checks['payload_hashes_checked']=len(actual)

 json_objects={}
 total_bytes=manifest_path.stat().st_size
 for relative,path in actual.items():
  total_bytes+=path.stat().st_size
  if path.suffix.lower() not in ALLOWED_SUFFIXES or path.suffix.lower() in PROHIBITED_SUFFIXES:errors.append(f'Prohibited handoff file type: {relative}')
  if any(part in {'client','server','official-pages','private-input','extracted'} for part in path.relative_to(OUT).parts):errors.append(f'Prohibited payload path: {relative}')
  text=path.read_text(encoding='utf-8')
  for marker in PROHIBITED_CREATIVE_MARKERS:
   if marker.lower() in text.lower():errors.append(f'Creative/adaptation marker {marker!r} in {relative}')
  if path.suffix=='.json':
   try:json_objects[relative]=json.loads(text)
   except Exception as error:errors.append(f'JSON parse failure {relative}: {error}')
 checks['json_files_parsed']=len(json_objects)

 claims={row['claim_id']:row for row in [json.loads(line) for line in (ROOT/'research'/'reconciliation'/'internet-research-claims.jsonl').read_text(encoding='utf-8').splitlines() if line]}
 referenced=[]
 for value in json_objects.values():referenced.extend(collect_claim_ids(value))
 missing=sorted(set(referenced)-set(claims))
 if missing:errors.append(f'Unknown claim references: {missing}')
 for claim_id in set(referenced):
  if not claims[claim_id].get('evidence'):errors.append(f'Load-bearing claim lacks evidence: {claim_id}')
 checks['claim_references_checked']=len(set(referenced))

 arc_index=json_objects.get('game-story/arc-index.json',{})
 dossiers=arc_index.get('arcs',[])
 if arc_index.get('arc_count')!=14 or len(dossiers)!=14:errors.append('Promoted dossier count is not 14')
 for row in dossiers:
  path=OUT/row.get('dossier_path','')
  if not path.exists():errors.append(f"Missing dossier path for {row.get('arc_id')}")
  else:
   dossier=load_json(path)
   if not dossier.get('resolved_claims') or any(not claim.get('evidence') for claim in dossier['resolved_claims']):errors.append(f"Dossier lacks resolved claim evidence: {row.get('arc_id')}")
 checks['dossiers_checked']=len(dossiers)

 causal=json_objects.get('game-story/causal-spine.json',{})
 node_ids={row['claim_id'] for row in causal.get('nodes',[])}
 for edge in causal.get('edges',[]):
  if edge.get('source_claim_id') not in node_ids or edge.get('target_claim_id') not in node_ids:errors.append(f"Causal edge does not resolve: {edge.get('edge_id')}")
 checks['causal_edges_checked']=len(causal.get('edges',[]))
 for required in ('characters/index.json','factions/index.json','sects/index.json','martial-arts/index.json','important-items/index.json','important-locations/index.json','concordance/cn-vi-names.json','concordance/entity-aliases.json','concordance/task-story-map.json'):
  if required not in json_objects:errors.append(f'Missing semantic group: {required}')
 material=json_objects.get('unresolved/material-conflicts.json',{})
 if material.get('count')!=0 or material.get('entries'):errors.append('Material conflict projection is not empty')

 release_bytes=sum(path.stat().st_size for path in (ROOT/'generated'/'release').rglob('*') if path.is_file())
 if total_bytes>=release_bytes//4:errors.append('Handoff is too large to be a curated projection')
 if not manifest.get('raw_proprietary_payloads_excluded') or manifest.get('runtime_dependency_on_lab') is not False:errors.append('One-way/raw-payload contract is not explicit')
 metrics={'handoff_bytes':total_bytes,'research_release_bytes':release_bytes,'curated_ratio':round(total_bytes/release_bytes,6),'files':len(actual)+1,'dossiers':len(dossiers),'central_tolerable':counts.get('CENTRAL_TOLERABLE'),'non_central':counts.get('NON_CENTRAL')}
 return {'status':'NOVEL_HANDOFF_READY' if not errors else 'NOVEL_HANDOFF_BLOCKED','checks':checks,'metrics':metrics,'errors':errors}

def main():
 result=validate();REPORT.parent.mkdir(parents=True,exist_ok=True);REPORT.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(json.dumps(result,ensure_ascii=False,indent=2));raise SystemExit(0 if not result['errors'] else 1)

if __name__=='__main__':main()
