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
    checksum_lines=(RELEASE/'checksums.sha256').read_text(encoding='ascii').splitlines()
    for line in checksum_lines:
        match=re.fullmatch(r'([0-9a-f]{64})  (.+)',line)
        if not match:errors.append(f'Invalid checksum line: {line!r}');continue
        path=RELEASE/match.group(2)
        if not path.exists() or jxlab.sha256_file(path)!=match.group(1):errors.append(f'Checksum mismatch {match.group(2)}')
        checks['release_checksums_checked']+=1
    for path in sorted(RELEASE.glob('*.json')):
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
    if confidence.get('promotion_decision')!='NOT_AUTHORIZED_FOR_NOVEL_PROMOTION':errors.append('Novel promotion boundary is missing')
    unresolved=json.loads((RELEASE/'14-unresolved-questions.json').read_text(encoding='utf-8'))
    if any(row.get('status')!='UNKNOWN' for row in unresolved['entries']):errors.append('Unresolved question promoted above UNKNOWN')
    contradiction=json.loads((RELEASE/'15-edition-drift-ledger.json').read_text(encoding='utf-8'))
    if any(row.get('status') not in {'EDITION_DRIFT','CONFLICT'} for row in contradiction['entries']):errors.append('Contradiction ledger contains an invalid promoted status')
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
