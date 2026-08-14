#!/usr/bin/env python3
"""Validate the curated source-story-bible handoff integrity boundary."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'generated'/'novel-handoff'
REPORT=ROOT/'generated'/'reports'/'novel-handoff-validation-report.json'
SOURCE_EVIDENCE_COMMIT='8d7645a4d659d0baac86c9eafc7fc0ef18c90254'
ALLOWED_SUFFIXES={'.json','.md'}
PROHIBITED_SUFFIXES={'.pak','.exe','.dll','.zip','.rar','.7z','.bin','.spr','.wav','.mp3','.png','.jpg','.jpeg'}
PROHIBITED_CREATIVE_MARKERS=('Tieu Phung','Ti\u00eau Ph\u00f9ng','NovelOS','episode planning')
KNOWLEDGE_STATUSES={'KNOWS','BELIEVES','SUSPECTS','HEARD_RUMOR','MISINFORMED','UNKNOWN'}
MYSTERY_PHASE_TYPES={'SETUP','CLUE','SUSPICION','REVEAL','PAYOFF','RESIDUE'}

def load_json(path):return json.loads(path.read_text(encoding='utf-8'))
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def collect_claim_ids(value):
 found=[]
 if isinstance(value,dict):
  for key,item in value.items():
   if key.endswith('claim_ids') or key=='claim_id':found.extend(item if isinstance(item,list) else [item])
   found.extend(collect_claim_ids(item))
 elif isinstance(value,list):
  for item in value:found.extend(collect_claim_ids(item))
 return [item for item in found if isinstance(item,str) and item.startswith('IR')]

def validate():
 errors=[];checks={}
 manifest_path=OUT/'handoff-manifest.json'
 if not manifest_path.exists():return {'status':'NOVEL_HANDOFF_BLOCKED','errors':['Missing handoff-manifest.json'],'checks':{},'metrics':{}}
 manifest=load_json(manifest_path);checks['manifest_parsed']=1
 concordance=load_json(ROOT/'research'/'reconciliation'/'lore-concordance.json')
 release_validation=load_json(ROOT/'generated'/'reports'/'release-validation-report.json')
 if manifest.get('handoff_status')!='NOVEL_HANDOFF_READY' or manifest.get('promotion_status')!='NOVEL_PROMOTION_READY':errors.append('Handoff is not promotion ready')
 if manifest.get('source_lab_commit')!=SOURCE_EVIDENCE_COMMIT:errors.append('Source evidence/reconciliation commit was not preserved')
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

 json_objects={};total_bytes=manifest_path.stat().st_size
 for relative,path in actual.items():
  total_bytes+=path.stat().st_size
  suffix=path.suffix.lower()
  if suffix not in ALLOWED_SUFFIXES or suffix in PROHIBITED_SUFFIXES:errors.append(f'Prohibited handoff file type: {relative}')
  if any(part in {'client','server','official-pages','private-input','extracted'} for part in path.relative_to(OUT).parts):errors.append(f'Prohibited payload path: {relative}')
  text=path.read_text(encoding='utf-8')
  for marker in PROHIBITED_CREATIVE_MARKERS:
   if marker.lower() in text.lower():errors.append(f'Creative/adaptation marker {marker!r} in {relative}')
  if suffix=='.json':
   try:json_objects[relative]=json.loads(text)
   except Exception as error:errors.append(f'JSON parse failure {relative}: {error}')
 checks['json_files_parsed']=len(json_objects)

 claims={row['claim_id']:row for row in [json.loads(line) for line in (ROOT/'research'/'reconciliation'/'internet-research-claims.jsonl').read_text(encoding='utf-8').splitlines() if line]}
 referenced=[]
 for value in json_objects.values():referenced.extend(collect_claim_ids(value))
 missing=sorted(set(referenced)-set(claims))
 if missing:errors.append(f'Unknown claim references: {missing}')
 for claim_id in set(referenced)&set(claims):
  if not claims[claim_id].get('evidence'):errors.append(f'Load-bearing claim lacks evidence: {claim_id}')
 checks['claim_references_checked']=len(set(referenced))

 required=(
  'game-story/arc-index.json','game-story/causal-spine.json','game-story/plot-thread-index.json','game-story/mystery-payoff-map.json',
  'characters/character-index.json','factions/faction-index.json','relationships/source-relationship-map.json','knowledge/source-knowledge-timeline.json',
  'sects/index.json','martial-arts/index.json','important-items/index.json','important-locations/index.json',
  'concordance/cn-vi-names.json','concordance/entity-aliases.json','concordance/task-story-map.json',
 )
 for relative in required:
  if relative not in json_objects:errors.append(f'Missing semantic group: {relative}')

 arc_index=json_objects.get('game-story/arc-index.json',{});dossiers=arc_index.get('arcs',[]);arc_ids={row.get('arc_id') for row in dossiers}
 if arc_index.get('arc_count')!=14 or len(dossiers)!=14 or len(arc_ids)!=14:errors.append('Promoted dossier count/arc IDs are not exactly 14 unique records')
 thread_index=json_objects.get('game-story/plot-thread-index.json',{});threads=thread_index.get('threads',[]);thread_ids={row.get('thread_id') for row in threads}
 if thread_index.get('thread_count')!=len(threads) or len(thread_ids)!=len(threads):errors.append('Plot thread count/IDs are inconsistent')
 mystery_map=json_objects.get('game-story/mystery-payoff-map.json',{});mysteries=mystery_map.get('mysteries',[]);mystery_ids={row.get('mystery_id') for row in mysteries}
 if mystery_map.get('mystery_count')!=len(mysteries) or len(mystery_ids)!=len(mysteries):errors.append('Mystery/payoff count/IDs are inconsistent')

 characters=json_objects.get('characters/character-index.json',{});character_rows=characters.get('characters',[]);character_ids={row.get('entity_id') for row in character_rows}
 factions=json_objects.get('factions/faction-index.json',{});faction_rows=factions.get('factions',[]);faction_ids={row.get('entity_id') for row in faction_rows}
 sect_ids={row.get('entity_id') for row in json_objects.get('sects/index.json',{}).get('sects',[])}
 item_ids={row.get('entity_id') for row in json_objects.get('important-items/index.json',{}).get('items',[])}
 location_ids={row.get('entity_id') for row in json_objects.get('important-locations/index.json',{}).get('locations',[])}
 entity_ids=character_ids|faction_ids|sect_ids|item_ids|location_ids

 for arc in dossiers:
  if set(arc.get('principal_entity_ids',[]))-entity_ids:errors.append(f"Arc has unknown principal entity: {arc.get('arc_id')}")
  if set(arc.get('active_plot_thread_ids',[]))-thread_ids:errors.append(f"Arc has unknown plot thread: {arc.get('arc_id')}")
  if set(arc.get('mystery_reveal_ids',[]))-mystery_ids:errors.append(f"Arc has unknown mystery: {arc.get('arc_id')}")
  if set(arc.get('important_item_ids',[]))-item_ids:errors.append(f"Arc has unknown item: {arc.get('arc_id')}")
  if set(arc.get('important_location_ids',[]))-location_ids:errors.append(f"Arc has unknown location: {arc.get('arc_id')}")
  if set(arc.get('important_sect_ids',[]))-sect_ids:errors.append(f"Arc has unknown sect: {arc.get('arc_id')}")

 for thread in threads:
  if set(thread.get('participant_entity_ids',[]))-entity_ids:errors.append(f"Plot thread has unknown entities: {thread.get('thread_id')}")
  if set(thread.get('intersection_thread_ids',[]))-thread_ids:errors.append(f"Plot thread has unknown intersections: {thread.get('thread_id')}")
  stages=[thread.get('first_setup',{}),*thread.get('developments',[]),*thread.get('reversals_or_reframes',[])]
  if thread.get('payoff'):stages.append(thread['payoff'])
  for stage in stages:
   if stage.get('arc_id') not in arc_ids:errors.append(f"Plot thread stage has unknown arc: {thread.get('thread_id')}")
   if not stage.get('claim_ids'):errors.append(f"Plot thread stage lacks claim evidence: {thread.get('thread_id')}")
 checks['plot_threads_checked']=len(threads)

 for mystery in mysteries:
  if set(mystery.get('thread_ids',[]))-thread_ids:errors.append(f"Mystery has unknown thread IDs: {mystery.get('mystery_id')}")
  for phase in mystery.get('phases',[]):
   if phase.get('phase_type') not in MYSTERY_PHASE_TYPES:errors.append(f"Mystery has invalid phase type: {mystery.get('mystery_id')}")
   if phase.get('arc_id') not in arc_ids:errors.append(f"Mystery phase has unknown arc: {mystery.get('mystery_id')}")
   support=[claims[claim_id]['status'] for claim_id in phase.get('claim_ids',[]) if claim_id in claims]
   if not support:errors.append(f"Mystery phase lacks claim evidence: {mystery.get('mystery_id')}")
   if phase.get('phase_type') in {'REVEAL','PAYOFF'} and support and all(status=='INFERENCE' for status in support):errors.append(f"Mystery promotes inference-only reveal/payoff: {mystery.get('mystery_id')}")
 checks['mysteries_checked']=len(mysteries)

 for row in dossiers:
  relative=row.get('dossier_path','');path=OUT/relative
  if not path.exists():errors.append(f"Missing dossier path for {row.get('arc_id')}");continue
  dossier=load_json(path)
  if not dossier.get('resolved_claims') or any(not claim.get('evidence') for claim in dossier['resolved_claims']):errors.append(f"Dossier lacks resolved claim evidence: {row.get('arc_id')}")
  if not dossier.get('story_bible_sections') or not dossier.get('ordered_source_events'):errors.append(f"Dossier lacks writer-facing source sections: {row.get('arc_id')}")
  if set(dossier.get('active_plot_thread_ids',[]))-thread_ids:errors.append(f"Dossier has unknown plot thread: {row.get('arc_id')}")
  if set(dossier.get('mystery_payoff_ids',[]))-mystery_ids:errors.append(f"Dossier has unknown mystery: {row.get('arc_id')}")
  if set(dossier.get('important_item_ids',[]))-item_ids or set(dossier.get('important_location_ids',[]))-location_ids or set(dossier.get('important_sect_ids',[]))-sect_ids:errors.append(f"Dossier has unresolved important entity references: {row.get('arc_id')}")
 checks['dossiers_checked']=len(dossiers)

 causal=json_objects.get('game-story/causal-spine.json',{});node_ids={row['claim_id'] for row in causal.get('nodes',[])}
 for edge in causal.get('edges',[]):
  if edge.get('source_claim_id') not in node_ids or edge.get('target_claim_id') not in node_ids:errors.append(f"Causal edge does not resolve: {edge.get('edge_id')}")
  if set(edge.get('related_plot_thread_ids',[]))-thread_ids:errors.append(f"Causal edge has unknown plot thread: {edge.get('edge_id')}")
  for relative in edge.get('dossier_paths',[]):
   if relative not in json_objects:errors.append(f"Causal edge has unknown dossier: {edge.get('edge_id')} -> {relative}")
 checks['causal_edges_checked']=len(causal.get('edges',[]))

 trajectory_count=0
 for row in [*character_rows,*faction_rows]:
  relative=row.get('trajectory_path')
  if not relative:continue
  trajectory_count+=1;trajectory=json_objects.get(relative)
  if not trajectory:errors.append(f'Missing trajectory: {relative}');continue
  if trajectory.get('entity_id')!=row.get('entity_id'):errors.append(f'Trajectory entity mismatch: {relative}')
  if set(trajectory.get('related_plot_thread_ids',[]))-thread_ids:errors.append(f'Trajectory has unknown thread: {relative}')
  if set(trajectory.get('related_mystery_reveal_ids',[]))-mystery_ids:errors.append(f'Trajectory has unknown mystery: {relative}')
  for stage in trajectory.get('stages',[]):
   if stage.get('arc_id') not in arc_ids:errors.append(f'Trajectory stage has unknown arc: {relative}')
   if not stage.get('claim_ids'):errors.append(f'Trajectory stage lacks claim evidence: {relative}')
 checks['trajectories_checked']=trajectory_count

 relationship_map=json_objects.get('relationships/source-relationship-map.json',{});relationships=relationship_map.get('relationships',[])
 for relation in relationships:
  if relation.get('source_entity_id') not in entity_ids or relation.get('target_entity_id') not in entity_ids:errors.append(f"Relationship has unknown entity: {relation.get('relationship_id')}")
  support=[claims[claim_id]['status'] for claim_id in relation.get('claim_ids',[]) if claim_id in claims]
  if not support or all(status=='INFERENCE' for status in support):errors.append(f"Relationship lacks non-inference support: {relation.get('relationship_id')}")
  for change in relation.get('changes',[]):
   if change.get('arc_id') not in arc_ids:errors.append(f"Relationship change has unknown arc: {relation.get('relationship_id')}")
 checks['relationships_checked']=len(relationships)

 knowledge=json_objects.get('knowledge/source-knowledge-timeline.json',{});knowledge_events=knowledge.get('events',[])
 for event in knowledge_events:
  if event.get('entity_id') not in entity_ids:errors.append(f"Knowledge event has unknown entity: {event.get('knowledge_event_id')}")
  if event.get('prior_status') not in KNOWLEDGE_STATUSES or event.get('new_status') not in KNOWLEDGE_STATUSES:errors.append(f"Knowledge event has invalid status: {event.get('knowledge_event_id')}")
  if event.get('arc_id') not in arc_ids:errors.append(f"Knowledge event has unknown arc: {event.get('knowledge_event_id')}")
  if set(event.get('thread_ids',[]))-thread_ids or set(event.get('mystery_ids',[]))-mystery_ids:errors.append(f"Knowledge event has unresolved thread/mystery: {event.get('knowledge_event_id')}")
  support=[claims[claim_id]['status'] for claim_id in event.get('claim_ids',[]) if claim_id in claims]
  if not support or all(status=='INFERENCE' for status in support):errors.append(f"Knowledge event lacks non-inference support: {event.get('knowledge_event_id')}")
 checks['knowledge_events_checked']=len(knowledge_events)

 task_map=json_objects.get('concordance/task-story-map.json',{});hazards=[row for row in task_map.get('entries',[]) if row.get('id_reuse_hazard')=='ID_REUSE_VARIANT']
 if not hazards or any(row.get('standalone_semantic_content_excluded') is not True for row in hazards):errors.append('Task ID reuse/variant hazards are not preserved')
 checks['task_id_reuse_hazards_checked']=len(hazards)

 alias_index=json_objects.get('concordance/entity-aliases.json',{});alias_entries=alias_index.get('entries',[])
 if alias_index.get('count')!=len(alias_entries) or len({row.get('entity_id') for row in alias_entries})!=len(alias_entries):errors.append('Alias index has duplicate entity records')
 alias_owner={}
 for row in alias_entries:
  for value in [row.get('canonical'),*row.get('aliases',[])]:
   if not value:continue
   normalized=value.strip().casefold();owner=alias_owner.setdefault(normalized,row.get('entity_id'))
   if owner!=row.get('entity_id'):errors.append(f'Alias maps to duplicate canonical entities: {value}')
 checks['entity_aliases_checked']=len(alias_entries)

 material=json_objects.get('unresolved/material-conflicts.json',{})
 if material.get('count')!=0 or material.get('entries'):errors.append('Material conflict projection is not empty')
 release_bytes=sum(path.stat().st_size for path in (ROOT/'generated'/'release').rglob('*') if path.is_file())
 if total_bytes>=release_bytes//4:errors.append('Handoff is too large to be a curated projection')
 if not manifest.get('raw_proprietary_payloads_excluded') or manifest.get('runtime_dependency_on_lab') is not False:errors.append('One-way/raw-payload contract is not explicit')
 provenance=json_objects.get('provenance.json',{})
 if provenance.get('new_broad_source_research_performed') is not False:errors.append('Provenance does not confirm focused regeneration only')
 expected_counts={
  'promoted_plot_thread_count':len(threads),'promoted_mystery_payoff_count':len(mysteries),
  'promoted_character_trajectory_count':characters.get('trajectory_count'),'promoted_faction_trajectory_count':factions.get('trajectory_count'),
  'source_relationship_count':len(relationships),'source_knowledge_event_count':len(knowledge_events),
 }
 for key,value in expected_counts.items():
  if manifest.get(key)!=value:errors.append(f'Manifest count mismatch: {key}')
 metrics={'handoff_bytes':total_bytes,'research_release_bytes':release_bytes,'curated_ratio':round(total_bytes/release_bytes,6),'files':len(actual)+1,'dossiers':len(dossiers),'plot_threads':len(threads),'mysteries':len(mysteries),'character_trajectories':characters.get('trajectory_count'),'faction_trajectories':factions.get('trajectory_count'),'relationships':len(relationships),'knowledge_events':len(knowledge_events),'central_tolerable':counts.get('CENTRAL_TOLERABLE'),'non_central':counts.get('NON_CENTRAL')}
 return {'status':'NOVEL_HANDOFF_READY' if not errors else 'NOVEL_HANDOFF_BLOCKED','checks':checks,'metrics':metrics,'errors':errors}

def main():
 result=validate();REPORT.parent.mkdir(parents=True,exist_ok=True);REPORT.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(json.dumps(result,ensure_ascii=False,indent=2));raise SystemExit(0 if not result['errors'] else 1)

if __name__=='__main__':main()
