#!/usr/bin/env python3
"""Build evidence-only reconstruction and audit ledgers from generated corpora."""
from __future__ import annotations

import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

import jxlab

ROOT=Path(__file__).resolve().parents[1]
RESEARCH=ROOT/'research'
PARSER_VERSION='jxlab research-audit/0.1'

def load_jsonl(path):
    return [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line]

def write_json(path,payload):
    path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding='utf-8')

def generated_meta():return {'schema_version':'1.0','generator':'scripts/build_research.py','parser_version':PARSER_VERSION,'generated_at_utc':datetime.now(timezone.utc).isoformat()}

def evidence(path,locator=None,note=None):
    record={'path':jxlab.rel(path),'sha256':jxlab.sha256_file(path)}
    if locator:record['locator']=locator
    if note:record['note']=note
    return record

def build_task_graph():
    task_path=ROOT/'generated/records/tasks/task-archive-records.jsonl';sub_path=ROOT/'generated/records/tasks/subtask-archive-records.jsonl'
    edge_path=ROOT/'generated/records/edges/task-reference-edges.jsonl'
    tasks=load_jsonl(task_path);subs=load_jsonl(sub_path);edges=load_jsonl(edge_path)
    names={record['record_key']:record.get('name','') for record in tasks+subs}
    next_edges=defaultdict(list);managed=defaultdict(list);prerequisites=[]
    for edge in edges:
        if edge['relation']=='accepts_next_sub':next_edges[edge['source_key']].append(edge)
        elif edge['relation']=='manages_sub':managed[edge['source_key']].append(edge)
        elif edge['relation']=='requires_finished_sub':prerequisites.append(edge)
    incoming_next={edge['target_key'] for values in next_edges.values() for edge in values}
    chains=[]
    for task in tasks:
        task_managed=managed.get(task['record_key'],[])
        starts=[edge for edge in task_managed if edge['target_key'] not in incoming_next] or task_managed
        for start_edge in starts:
            current=start_edge['target_key'];sequence=[];edge_ids=[start_edge['edge_id']];seen=set();termination='no_explicit_next'
            while current and current not in seen:
                seen.add(current);sequence.append(current);outgoing=next_edges.get(current,[])
                if not outgoing:termination='no_explicit_next';break
                if len(outgoing)>1:termination='branch';edge_ids.extend(edge['edge_id'] for edge in outgoing);break
                edge=outgoing[0];edge_ids.append(edge['edge_id']);current=edge['target_key']
            else:
                if current in seen:termination='cycle'
            chains.append({'task_record_key':task['record_key'],'task_id':task['task_id'],'task_name':task['name'],
                           'classification':task['classification'],'subtask_sequence':sequence,
                           'subtask_names':[names.get(key,'UNKNOWN') for key in sequence],
                           'edge_ids':edge_ids,'termination':termination})
    nodes=[]
    for record in tasks:
        nodes.append({'key':record['record_key'],'logical_key':record['logical_key'],'kind':'task','id':record['task_id'],'name':record['name'],'classification':record['classification']})
    for record in subs:nodes.append({'key':record['record_key'],'logical_key':record['logical_key'],'kind':'subtask','id':record['task_id'],'name':record['name']})
    graph_edge_fields=('edge_id','source_key','target_key','relation','resolution','function','managed_inline_id','managed_refer_id','managed_inline_name','managed_inline_description','standalone_name','label_relation','semantic_join_status','standalone_content_usable','wrapper_inline_authority')
    graph_edges=[{key:edge.get(key) for key in graph_edge_fields if edge.get(key) is not None} for edge in edges if edge['relation'] in {'manages_sub','accepts_next_sub','requires_finished_sub'}]
    main_tasks=[record for record in tasks if record['classification']['class']=='main']
    non_main=[record for record in tasks if record['classification']['class']=='configured_non_main']
    reconstruction={**generated_meta(),'reconstruction_type':'evidence_graph_not_narrative',
                    'evidence_boundary':'Task names, descriptions, explicit XML containment, AskAccept targets, and IsRefFinished targets are preserved. No missing causal link, motive, culprit, outcome, or chronology is invented.',
                    'counts':{'task_nodes':len(tasks),'subtask_nodes':len(subs),'graph_edges':len(graph_edges),'main_tasks':len(main_tasks),'configured_non_main_tasks':len(non_main),'chains':len(chains)},
                    'relation_counts':dict(Counter(edge['relation'] for edge in graph_edges)),
                    'resolution_counts':dict(Counter(edge['resolution'] for edge in graph_edges)),
                    'nodes':nodes,'edges':graph_edges,'chains':chains,
                    'source_artifacts':[evidence(task_path),evidence(sub_path),evidence(edge_path)]}
    graph_path=RESEARCH/'reconstruction'/'game-story-evidence-graph.json';write_json(graph_path,reconstruction)
    main_task_keys={record['record_key'] for record in main_tasks}
    main_subkeys={key for chain in chains if chain['classification']['class']=='main' for key in chain['subtask_sequence']}
    main_path=RESEARCH/'reconstruction'/'main-task-graph.json';write_json(main_path,{**generated_meta(),'classification_basis':'Server task_def.txt explicit ID ranges whose configured label contains “chính tuyến”; client task_def differs and is recorded as EDITION_DRIFT.',
                                                                                   'tasks':[record['record_key'] for record in main_tasks],
                                                                                   'edges':[edge for edge in graph_edges if edge['source_key'] in main_task_keys or (edge['source_key'] in main_subkeys and edge['target_key'] in main_subkeys)],
                                                                                   'chains':[chain for chain in chains if chain['classification']['class']=='main']})
    side_path=RESEARCH/'reconstruction'/'configured-non-main-task-index.json';write_json(side_path,{**generated_meta(),'classification_basis':'Explicit server task_def.txt range label not marked chính tuyến. This index does not infer a single universal side-quest category.',
                                                                                                 'tasks':[{'record_key':record['record_key'],'task_id':record['task_id'],'name':record['name'],'classification':record['classification']} for record in non_main]})
    md_path=RESEARCH/'reconstruction'/'game-story-reconstruction.md'
    longest=sorted(chains,key=lambda value:len(value['subtask_sequence']),reverse=True)[:20]
    lines=['# Game Story Reconstruction — Evidence Graph','',
           'This artifact is a structured reconstruction of implementation evidence, not a novel narrative and not authorization to adapt it as fiction.','',
           f"- Task roots: **{len(tasks):,}**",f"- Subtask roots: **{len(subs):,}**",f"- Explicit graph edges: **{len(graph_edges):,}**",
           f"- Config-classified main tasks: **{len(main_tasks):,}**",f"- Configured non-main tasks: **{len(non_main):,}**",'',
           '## Promotable relations','',
           '- `manages_sub`: explicit `<Managed><Sub refer=...>` relation in a Task XML record.',
           '- `accepts_next_sub`: explicit `TaskAct:AskAccept` with a `referid` parameter.',
           '- `requires_finished_sub`: explicit `TaskCond:IsRefFinished` with a `referid` parameter.','',
           '## Evidence limits','',
           '- XML task names and text are raw-build content, not automatically launch-era producer canon.',
           '- A missing edge means `UNKNOWN`; adjacency, numeric IDs, and task titles are never used to invent links.',
           '- One logical task ID occurs in two archive entries; both records are preserved independently.',
           '- Internet-package summaries remain `LEGACY_LEAD`; verified underlying Kingsoft/Xoyo/VNG pages are tracked separately in `research/reconciliation/lore-concordance.json`.','',
           '- Source-only causal dossiers are generated under `research/reconstruction/game-story-dossiers/`; no player-to-novel-character adaptation is performed.','',
           '## Longest explicit chains (identifiers only)','']
    lines.extend(f"- `{chain['task_record_key']}`: {len(chain['subtask_sequence'])} subtask nodes; termination `{chain['termination']}`" for chain in longest)
    md_path.write_text('\n'.join(lines)+'\n',encoding='utf-8')
    return {'graph':jxlab.rel(graph_path),'main_graph':jxlab.rel(main_path),'non_main_index':jxlab.rel(side_path),'report':jxlab.rel(md_path),'counts':reconstruction['counts']}

def build_ledgers(task_summary):
    edition_path=RESEARCH/'edition-drift-ledger.json';edition=json.loads(edition_path.read_text(encoding='utf-8'))
    domain_report_path=ROOT/'generated/reports/domain-corpus-report.json';domain=json.loads(domain_report_path.read_text(encoding='utf-8'))
    unresolved_edge_path=RESEARCH/'unresolved-reference-ledger.json';unresolved_edges=json.loads(unresolved_edge_path.read_text(encoding='utf-8'))
    pack_report=ROOT/'generated/reports/pak-structure-report.json';asset_report=ROOT/'generated/reports/client-asset-index-report.json'
    reconciliation_path=RESEARCH/'reconciliation'/'lore-concordance.json'
    reconciliation=json.loads(reconciliation_path.read_text(encoding='utf-8'))
    reconciliation_claims=load_jsonl(RESEARCH/'reconciliation'/'internet-research-claims.jsonl')
    drift_entries=[entry for entry in edition['entries'] if entry['status']=='EDITION_DRIFT']
    drift_entries.extend([
        {'domain':'task_publish_external_listing','status':'EDITION_DRIFT','archive_path':'client/pak/task_publish.pak','archive_sha256':'ac48ad39a653007f9244a0f0abf0ab5944c638533114eea4fb7830b29c8bce3f',
         'listing_path':'client/pak/task_publish.pak.txt','listing_sha256':'e8693778360260780cdcb78b7d4280a66aeb885fe7922542540096877525179b',
         'difference':'binary index 1,074 entries vs companion listing 1,129 entries; ID sets and most sizes differ'},
        {'domain':'task_publish_embedded_listing','status':'EDITION_DRIFT','archive_path':'client/pak/task_publish.pak','embedded_entry_id':'9efc8acb',
         'difference':'embedded listing covers 1,073 archive IDs but 563 entries differ on expanded or stored sizes; path mapping remains lead-only'},
        {'domain':'task_archive_duplicate_logical_id','status':'CONFLICT','logical_task_id':'000000000000017B','archive_record_count':2,
         'handling':'both entry-specific records retained; no automatic merge'},
    ])
    drift_entries.extend(reconciliation['conflicts'])
    contradiction_path=RESEARCH/'contradiction-ledger.json';write_json(contradiction_path,{**generated_meta(),'entries':drift_entries,
                                                                                           'counts':dict(Counter(entry['status'] for entry in drift_entries))})
    questions=list(reconciliation['unresolved_questions'])+[
        {'question_id':'pak-fragment-format','status':'UNKNOWN','centrality':'NON_CENTRAL','question':'What is the fragment payload subformat for flag 0x10000000?','impact':'27,519 client entries remain structurally indexed but not decoded.','next_evidence':'XPackFile fragment-read evidence and copied-sample validation.'},
        {'question_id':'pak-variant-layouts','status':'UNKNOWN','centrality':'NON_CENTRAL','question':'What layouts are used by image21168.pak and update2021.pak?','impact':'Two archives are recorded but not entry-indexed.','next_evidence':'Loader branch evidence for these variants.'},
        {'question_id':'pack-path-hash','status':'UNKNOWN','centrality':'NON_CENTRAL','question':'How are internal paths mapped to PACK entry IDs?','impact':'Most client asset internal paths remain UNKNOWN.','next_evidence':'Hash routine/source or binary-exact companion listings.'},
        {'question_id':'ambiguous-references','status':'UNKNOWN','centrality':'NON_CENTRAL','question':'Which additional keys disambiguate class/name-only joins?','impact':f"{unresolved_edges['counts'].get('ambiguous',0):,} edges remain ambiguous.",'next_evidence':'Runtime loader keys or additional composite fields.'},
        {'question_id':'unresolved-references','status':'UNKNOWN','centrality':'NON_CENTRAL','question':'What sources resolve currently absent target IDs?','impact':f"{unresolved_edges['counts'].get('unresolved',0):,} edges remain unresolved.",'next_evidence':'Edition-matched NPC/map/item tables or loader behavior.'},
    ]
    questions_path=RESEARCH/'unresolved-questions.json';write_json(questions_path,{**generated_meta(),'entries':questions})
    claims=[
        {'claim_id':'pack-codec','claim':'For the matched engined.dll build, PACK method 0x20000000 calls ucl_nrv2b_decompress_safe_8; stored size uses mask 0x07FFFFFF and fragment flag 0x10000000.','status':'VERIFIED_DIRECT','evidence':[evidence(ROOT/'server/gameserver/engined.dll','XPackFile::ExtractRead and ReadElemFile disassembly'),evidence(ROOT/'server/gameserver/engined.pdb','matched private symbols')],'notes':'Implementation fact for this local build.'},
        {'claim_id':'task-xml-corpus','claim':f"The current task_publish archive decodes to {task_summary['counts']['task_nodes']} Task roots and {task_summary['counts']['subtask_nodes']} Sub roots used by the evidence graph.",'status':'VERIFIED_DIRECT','evidence':[evidence(ROOT/'client/pak/task_publish.pak','PACK index and decoded XML roots')],'notes':'Three non-XML payloads and one Text XML payload are separately recorded.'},
        {'claim_id':'task-explicit-edges','claim':f"The reconstruction contains {task_summary['counts']['graph_edges']} explicit Task/Sub graph edges from XML containment, AskAccept, or IsRefFinished fields.",'status':'VERIFIED_DIRECT','evidence':[evidence(ROOT/'generated/records/edges/task-reference-edges.jsonl')],'notes':'No title or numeric adjacency edges are included.'},
        {'claim_id':'domain-corpus-lineage','claim':'All generated corpus entities and reference edges loaded into SQLite have at least one source record; foreign-key validation is clean.','status':'VERIFIED_DIRECT','evidence':[evidence(ROOT/'generated/reports/database-build-report.json')],'notes':'SQLite is a derived index, not higher authority than raw sources.'},
        {'claim_id':'client-server-drift','claim':f"Core client/server comparison records {len([e for e in edition['entries'] if e['status']=='EDITION_DRIFT'])} byte-level edition drifts and {len([e for e in edition['entries'] if e['status']=='CROSS_SOURCE_CONFIRMED'])} byte-identical pairs.",'status':'EDITION_DRIFT','evidence':[evidence(edition_path)],'notes':'Equality applies only to the supplied unknown-build copies.'},
        {'claim_id':'internet-research-scope','claim':f"The reconciled internet package contains {reconciliation['package_inventory']['file_count']} hashed research files; package summaries remain LEGACY_LEAD while verified underlying pages retain their own authority class.",'status':'VERIFIED_DIRECT','evidence':[evidence(reconciliation_path),evidence(RESEARCH/'reconciliation'/'internet-research-claims.jsonl')],'notes':'Package authority and underlying-source authority are never conflated.'},
    ]
    claims.extend(reconciliation_claims)
    claims_path=RESEARCH/'claims.jsonl'
    with claims_path.open('w',encoding='utf-8',newline='\n') as output:
        for claim in claims:output.write(json.dumps(claim,ensure_ascii=False,separators=(',',':'))+'\n')
    confidence={**generated_meta(),'claim_status_counts':dict(Counter(claim['status'] for claim in claims)),'claims':claims,
                'coverage':{'corpus_counts':domain['task_archive']['counts']|domain['npc_dialogue']['counts']|domain['localization']['counts']|domain['faction_skill']['counts']|domain['items']['counts']|domain['map_features']['counts'],
                            'unresolved_reference_counts':unresolved_edges['counts'],
                            'asset_scope':json.loads(asset_report.read_text(encoding='utf-8'))['status_counts'],
                            'internet_research_claims':len(reconciliation_claims),'game_story_dossiers':14},
                'unresolved_centrality_counts':dict(Counter(row['centrality'] for row in questions)),
                'promotion_gates':reconciliation['promotion_gates'],
                'promotion_decision':reconciliation['promotion_decision'],
                'reason':'Central story and cross-source lore are sufficient under the current policy; remaining central gaps are explicit and tolerable, with no unresolved MATERIAL narrative conflict.'}
    confidence_path=RESEARCH/'confidence-report.json';write_json(confidence_path,confidence)
    return {'contradiction_ledger':jxlab.rel(contradiction_path),'unresolved_questions':jxlab.rel(questions_path),'claims':jxlab.rel(claims_path),'confidence_report':jxlab.rel(confidence_path)}

def main():
    task_summary=build_task_graph();ledgers=build_ledgers(task_summary)
    report={**generated_meta(),'task_reconstruction':task_summary,'ledgers':ledgers}
    path=ROOT/'generated/reports/research-build-report.json';write_json(path,report)
    print(json.dumps({'report':jxlab.rel(path),**task_summary,**ledgers},ensure_ascii=False,indent=2))

if __name__=='__main__':main()
