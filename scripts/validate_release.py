#!/usr/bin/env python3
"""Validate Research Release 1.0 and its canonical corpus/database inputs."""
from __future__ import annotations

import argparse
import gzip
import json
import re
import sqlite3
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import jxlab

ROOT=Path(__file__).resolve().parents[1]
RELEASE=ROOT/'generated'/'release'
REPORT=ROOT/'generated'/'reports'/'release-validation-report.json'
ALLOWED_CLAIM_STATUS={'VERIFIED_DIRECT','VERIFIED_CROSS_SOURCE','STRONG','INFERENCE','UNKNOWN','CONFLICT','EDITION_DRIFT'}
ALLOWED_PROMOTION={'NOVEL_PROMOTION_READY','NOVEL_PROMOTION_NOT_READY'}

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--verify-source-hashes',action='store_true');args=parser.parse_args()
    errors=[];warnings=[];checks=Counter();metrics={}
    manifest_path=RELEASE/'release-manifest.json'
    try:manifest=json.loads(manifest_path.read_text(encoding='utf-8'));checks['json_files_parsed']+=1
    except Exception as error:raise SystemExit(f'Cannot parse release manifest: {error}')
    artifacts=manifest.get('artifacts',[])
    if len(artifacts)!=16:errors.append(f'Expected 16 deliverables, found {len(artifacts)}')
    if len({row['deliverable'] for row in artifacts})!=len(artifacts):errors.append('Duplicate deliverable names in release manifest')
    for row in artifacts:
        path=ROOT/row['path']
        if not path.exists():errors.append(f"Missing artifact {row['path']}");continue
        actual=jxlab.sha256_file(path);checks['artifact_hashes_checked']+=1
        if actual!=row['sha256']:errors.append(f"Artifact hash mismatch {row['path']}")
        for source in row.get('canonical_sources',[]):
            source_path=ROOT/source['path']
            if not source_path.exists():errors.append(f"Missing canonical source {source['path']}");continue
            if jxlab.sha256_file(source_path)!=source['sha256']:errors.append(f"Canonical source hash mismatch {source['path']}")
            checks['canonical_source_hashes_checked']+=1
    for row in manifest.get('supporting_artifacts',[]):
        path=ROOT/row['path']
        if not path.exists() or jxlab.sha256_file(path)!=row['sha256']:errors.append(f"Supporting artifact mismatch {row['path']}")
        checks['supporting_artifact_hashes_checked']+=1
    checksum_lines=(RELEASE/'checksums.sha256').read_text(encoding='ascii').splitlines()
    for line in checksum_lines:
        match=re.fullmatch(r'([0-9a-f]{64})  (.+)',line)
        if not match:errors.append(f'Invalid checksum line: {line!r}');continue
        path=RELEASE/match.group(2)
        if not path.exists() or jxlab.sha256_file(path)!=match.group(1):errors.append(f'Checksum mismatch {match.group(2)}')
        checks['release_checksums_checked']+=1
    for path in sorted(RELEASE.rglob('*.json')):
        try:json.loads(path.read_text(encoding='utf-8'));checks['json_files_parsed']+=1
        except Exception as error:errors.append(f'JSON parse failure {path.name}: {error}')
    corpus_metrics={}
    for row in artifacts:
        path=ROOT/row['path']
        if path.suffix!='.gz':continue
        count=0;missing_provenance=0;invalid=0;status_counts=Counter()
        try:
            with gzip.open(path,'rt',encoding='utf-8') as source:
                for line_number,line in enumerate(source,1):
                    if not line.strip():continue
                    try:record=json.loads(line)
                    except Exception as error:
                        errors.append(f'{path.name}:{line_number} invalid JSON: {error}');invalid+=1;continue
                    count+=1
                    if not record.get('schema_version') or not record.get('parser_version'):invalid+=1
                    status_counts[str(record.get('status','record'))]+=1
                    if path.name.startswith('12-client-asset'):
                        required=('asset_id','source_archive','source_archive_sha256','locator','evidence_class','status')
                        if any(record.get(key) in (None,'') for key in required):missing_provenance+=1
                        if record['status']=='decoded_validated' and (not record.get('output_sha256') or record.get('file_type')=='UNKNOWN'):invalid+=1
                    elif not record.get('source_records'):
                        missing_provenance+=1
            checks['gzip_jsonl_files_parsed']+=1
        except Exception as error:errors.append(f'Gzip corpus failure {path.name}: {error}')
        if row.get('record_count')!=count:errors.append(f"Record count mismatch {path.name}: manifest={row.get('record_count')} actual={count}")
        if missing_provenance:errors.append(f'{path.name} has {missing_provenance} records without provenance')
        if invalid:errors.append(f'{path.name} has {invalid} invalid records')
        corpus_metrics[path.name]={'records':count,'missing_provenance':missing_provenance,'invalid':invalid,'status_counts':dict(status_counts)}
    metrics['corpora']=corpus_metrics
    claims=[]
    for line_number,line in enumerate((RELEASE/'claims.jsonl').read_text(encoding='utf-8').splitlines(),1):
        if not line:continue
        claim=json.loads(line);claims.append(claim)
        if claim.get('status') not in ALLOWED_CLAIM_STATUS:errors.append(f'Claim {line_number} has invalid status')
        if not claim.get('evidence'):errors.append(f'Claim {line_number} has no evidence')
    metrics['claim_status_counts']=dict(Counter(claim['status'] for claim in claims));checks['claims_checked']=len(claims)
    confidence=json.loads((RELEASE/'16-confidence-report.json').read_text(encoding='utf-8'))
    promotion=confidence.get('promotion_decision')
    if promotion not in ALLOWED_PROMOTION:errors.append('Invalid novel promotion decision')
    if manifest.get('novel_promotion')!=promotion:errors.append('Manifest/confidence promotion decision mismatch')
    unresolved=json.loads((RELEASE/'14-unresolved-questions.json').read_text(encoding='utf-8'))
    if any(row.get('status')!='UNKNOWN' for row in unresolved['entries']):errors.append('Unresolved question promoted above UNKNOWN')
    central_blockers=sum(row.get('centrality')=='CENTRAL_BLOCKER' for row in unresolved['entries'])
    if promotion=='NOVEL_PROMOTION_READY' and central_blockers:errors.append('Promotion ready with CENTRAL_BLOCKER questions')
    contradiction=json.loads((RELEASE/'15-edition-drift-ledger.json').read_text(encoding='utf-8'))
    if any(row.get('status') not in {'EDITION_DRIFT','CONFLICT'} for row in contradiction['entries']):errors.append('Contradiction ledger contains an invalid promoted status')
    unresolved_material=[row for row in contradiction['entries'] if row.get('narrative_impact')=='MATERIAL' and row.get('resolution_status')!='RESOLVED']
    if promotion=='NOVEL_PROMOTION_READY' and unresolved_material:errors.append('Promotion ready with unresolved MATERIAL narrative conflict')
    concordance=json.loads((RELEASE/'13-lore-concordance.json').read_text(encoding='utf-8'))
    if concordance.get('promotion_decision')!=promotion:errors.append('Concordance promotion decision mismatch')
    if concordance.get('central_blocker_count')!=central_blockers:errors.append('Concordance central blocker count mismatch')
    if promotion=='NOVEL_PROMOTION_READY' and any(row.get('status')!='PASS' for row in concordance.get('promotion_gates',{}).values()):errors.append('Promotion ready while a promotion gate is not PASS')
    core_audit=concordance.get('structural_audit',{}).get('core_50_80',{})
    if core_audit.get('managed_edges')!=61 or core_audit.get('explicit_refer_matches')!=61:errors.append('50-80 managed-sub explicit-reference audit is incomplete')
    if core_audit.get('label_variants')!=61:errors.append('50-80 managed-sub label variants are not fully preserved')
    if core_audit.get('semantic_joins_blocked')!=61:errors.append('50-80 unsafe standalone semantic joins are not fully blocked')
    post50_audit=concordance.get('structural_audit',{}).get('post50_49_89',{})
    expected_post50_order=[13,14,15,17,16,18,21,19,20,22,23,24]
    if post50_audit.get('managed_edges')!=77 or post50_audit.get('label_variants')!=77:errors.append('49-89 managed wrapper audit is incomplete')
    if post50_audit.get('id_reuse_variants')!=77 or post50_audit.get('semantic_joins_blocked')!=77:errors.append('49-89 unsafe standalone semantic joins are not fully blocked')
    if post50_audit.get('macro_task_order')!=expected_post50_order:errors.append('49-89 macro task order differs from the validated order')
    post50=json.loads((RELEASE/'level-50-89-mainline.json').read_text(encoding='utf-8'))
    if post50.get('macro_task_order')!=expected_post50_order or post50.get('family_count')!=12:errors.append('49-89 reconstruction family order/count mismatch')
    if post50.get('managed_inline_subtask_count')!=77 or post50.get('blocked_standalone_join_count')!=77:errors.append('49-89 reconstruction semantic safety counts mismatch')
    if sum(row.get('managed_inline_count',0) for row in post50.get('task_families',[]))!=77:errors.append('49-89 reconstruction managed-sub count mismatch')
    if any(subtask.get('standalone_content_usable') is not False or subtask.get('semantic_join_status')!='ID_REUSE_VARIANT' for family in post50.get('task_families',[]) for subtask in family.get('managed_subtasks',[])):errors.append('49-89 reconstruction contains an unsafe standalone content join')
    post50_search=json.loads((RELEASE/'level-50-89-internet-search-ledger.json').read_text(encoding='utf-8'))
    if post50_search.get('result')!='BOUNDED_NOT_FOUND_DETAILED_WALKTHROUGH':errors.append('49-89 bounded Internet search result is not preserved')
    claim_ids={claim['claim_id'] for claim in claims}
    dossier_index=json.loads((RELEASE/'game-story-dossiers'/'index.json').read_text(encoding='utf-8'))
    dossier_paths=sorted(path for path in (RELEASE/'game-story-dossiers').glob('*.json') if path.name!='index.json')
    if dossier_index.get('dossier_count')!=len(dossier_paths):errors.append('Dossier index count mismatch')
    if set(dossier_index.get('declared_arcs',[]))!={json.loads(path.read_text(encoding='utf-8'))['arc_id'] for path in dossier_paths}:errors.append('Dossier arc coverage mismatch')
    for path in dossier_paths:
        dossier=json.loads(path.read_text(encoding='utf-8'));refs=set(dossier.get('premise_claim_ids',[]))
        for row in dossier.get('ordered_events',[]):refs.add(row.get('claim_id'))
        for field in ('character_and_faction_claim_ids','goal_and_motive_claim_ids','player_learns_claim_ids','reveal_claim_ids','climax_resolution_claim_ids','consequence_claim_ids','important_named_reference_claim_ids'):refs.update(dossier.get(field,[]))
        missing=refs-claim_ids
        if missing:errors.append(f'{path.name} references unknown claims: {sorted(missing)}')
        if not dossier.get('ordered_events') or not dossier.get('premise_claim_ids'):errors.append(f'{path.name} lacks claim-linked causal structure')
        if dossier.get('arc_id')=='arc-06' and [row.get('claim_id') for row in dossier.get('ordered_events',[])]!=['IR022','IR023','IR024','IR025']:errors.append('arc-06 ordered events do not match the validated 49-89 phase order')
        checks['dossiers_checked']+=1
    metrics['promotion']={'decision':promotion,'central_blockers':central_blockers,'unresolved_material_conflicts':len(unresolved_material),'dossiers':len(dossier_paths)}
    main_graph=json.loads((RELEASE/'03-main-task-graph.json').read_text(encoding='utf-8'))
    unresolved_graph=[edge for edge in main_graph['edges'] if edge.get('resolution')!='resolved']
    if unresolved_graph:errors.append(f'Main task graph has {len(unresolved_graph)} non-resolved explicit edges')
    metrics['main_task_graph']={'tasks':len(main_graph['tasks']),'edges':len(main_graph['edges']),'chains':len(main_graph['chains'])}
    database=ROOT/'database/work/jx-source-lab.sqlite3';database_report=json.loads((ROOT/'generated/reports/database-build-report.json').read_text(encoding='utf-8'))
    if jxlab.sha256_file(database)!=database_report['database_sha256']:errors.append('SQLite hash differs from database build report')
    connection=sqlite3.connect(database);foreign_errors=connection.execute('PRAGMA foreign_key_check').fetchall()
    if foreign_errors:errors.append(f'SQLite foreign key errors: {len(foreign_errors)}')
    db_counts={table:connection.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0] for table in database_report['table_counts']}
    connection.close()
    if db_counts!=database_report['table_counts']:errors.append('SQLite table counts differ from build report')
    if database_report['entities_without_source_records'] or database_report['edges_without_source_records']:errors.append('SQLite entity/edge lineage coverage is incomplete')
    metrics['database_table_counts']=db_counts;checks['sqlite_foreign_key_checks']+=1
    schemas=list((ROOT/'schemas').glob('*.json'))
    for schema in schemas:
        try:json.loads(schema.read_text(encoding='utf-8'));checks['json_schemas_parsed']+=1
        except Exception as error:errors.append(f'Schema parse failure {schema.name}: {error}')
    source_manifest=json.loads((RELEASE/'01-source-manifest.json').read_text(encoding='utf-8'))
    if not source_manifest.get('hashes_included'):errors.append('Source manifest does not include hashes')
    if args.verify_source_hashes:
        for row in source_manifest['files']:
            path=ROOT/row['path']
            if not path.exists():errors.append(f"Source manifest path missing {row['path']}");continue
            if jxlab.sha256_file(path)!=row.get('sha256'):errors.append(f"Raw source hash mismatch {row['path']}")
            checks['raw_source_hashes_checked']+=1
    else:warnings.append('Raw source file hashes were not re-read; use --verify-source-hashes for the full audit.')
    result={
        'schema_version':'1.0','generator':'scripts/validate_release.py','generated_at_utc':datetime.now(timezone.utc).isoformat(),
        'status':'PASS' if not errors else 'FAIL','full_source_hash_verification':bool(args.verify_source_hashes),
        'checks':dict(checks),'metrics':metrics,'errors':errors,'warnings':warnings,
    }
    REPORT.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'status':result['status'],'checks':result['checks'],'errors':errors,'warnings':warnings},ensure_ascii=False,indent=2))
    if errors:raise SystemExit(1)

if __name__=='__main__':main()
