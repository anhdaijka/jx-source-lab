#!/usr/bin/env python3
"""Build the disposable SQLite index from deterministic JSONL corpora."""
from __future__ import annotations

import hashlib
import gzip
import json
import os
import sqlite3
import tempfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import jxlab

ROOT=Path(__file__).resolve().parents[1]
RECORD_ROOT=ROOT/'generated'/'records'
DATABASE_PATH=ROOT/jxlab.CFG['outputs']['database']

def canonical_json(value):return json.dumps(value,ensure_ascii=False,separators=(',',':'),sort_keys=True)

def source_key(source):return hashlib.sha256(canonical_json(source).encode('utf-8')).hexdigest()

def entity_key(record,path,line_number):
    for field in ('record_key','dialogue_id','localization_id','asset_id','claim_id'):
        value=record.get(field)
        if value is not None:return str(value)
    return f"generated:{path.relative_to(RECORD_ROOT).as_posix()}:line:{line_number}"

def entity_name(record):
    value=record.get('name')
    if isinstance(value,str):return value
    return record.get('value') if record.get('record_kind')=='localization' else None

def insert_source(connection,source,cache):
    key=source_key(source)
    if key in cache:return cache[key]
    cursor=connection.execute(
        'INSERT INTO source_records(source_id,evidence_class,path,sha256,edition,encoding,locator,notes) VALUES(?,?,?,?,?,?,?,?)',
        (source.get('source_id','UNKNOWN'),source.get('evidence_class','UNKNOWN'),source.get('path','UNKNOWN'),source.get('sha256'),
         source.get('edition'),source.get('encoding'),source.get('locator'),source.get('notes','')),
    )
    cache[key]=cursor.lastrowid;return cursor.lastrowid

def build_database(target):
    connection=sqlite3.connect(target)
    connection.executescript((ROOT/'database'/'schema.sql').read_text(encoding='utf-8'))
    source_cache={};counts=Counter();file_manifest=[]
    for path in sorted(RECORD_ROOT.rglob('*.jsonl'),key=lambda value:value.as_posix().lower()):
        file_hash=jxlab.sha256_file(path);records=[];versions=set()
        for line_number,line in enumerate(path.read_text(encoding='utf-8').splitlines(),1):
            if not line:continue
            record=json.loads(line);records.append((line_number,record));versions.add(record.get('parser_version','UNKNOWN'))
        is_edge=path.parent.name=='edges'
        for line_number,record in records:
            sources=record.get('source_records') or []
            if is_edge:
                key=str(record.get('edge_id') or f'{path.name}:line:{line_number}')
                connection.execute('INSERT INTO reference_edges(edge_key,source_key,target_key,relation,resolution,payload_json) VALUES(?,?,?,?,?,?)',
                                   (key,str(record.get('source_key','UNKNOWN')),str(record.get('target_key','UNKNOWN')),
                                    str(record.get('relation','UNKNOWN')),str(record.get('resolution','UNKNOWN')),canonical_json(record)))
                for source in sources:
                    sid=insert_source(connection,source,source_cache)
                    connection.execute('INSERT OR IGNORE INTO reference_edge_sources(edge_key,source_record_id) VALUES(?,?)',(key,sid))
                counts['edges']+=1;continue
            key=entity_key(record,path,line_number);kind=str(record.get('record_kind') or path.parent.name)
            connection.execute('INSERT INTO corpus_entities(entity_key,logical_key,entity_type,name,payload_json) VALUES(?,?,?,?,?)',
                               (key,record.get('logical_key'),kind,entity_name(record),canonical_json(record)))
            for source in sources:
                sid=insert_source(connection,source,source_cache)
                connection.execute('INSERT OR IGNORE INTO corpus_entity_sources(entity_key,source_record_id) VALUES(?,?)',(key,sid))
            if kind in {'map_transfer','map_spawn','map_level_membership','map_transmit_catalog','map_protection','travel_station','revive_position'}:
                connection.execute('INSERT INTO features(feature_key,feature_type,name,raw_payload_json) VALUES(?,?,?,?)',
                                   (key,kind,entity_name(record),canonical_json(record)))
            counts[f'entity:{kind}']+=1;counts['entities']+=1
        connection.execute('INSERT INTO corpus_files(path,sha256,record_count,parser_versions_json) VALUES(?,?,?,?)',
                           (jxlab.rel(path),file_hash,len(records),canonical_json(sorted(versions))))
        file_manifest.append({'path':jxlab.rel(path),'sha256':file_hash,'records':len(records),'parser_versions':sorted(versions)})
    asset_path=RECORD_ROOT/'assets'/'client-asset-index.jsonl.gz'
    if asset_path.exists():
        asset_versions=set();asset_count=0;archive_source_ids={}
        with gzip.open(asset_path,'rt',encoding='utf-8') as source:
            for line in source:
                if not line:continue
                record=json.loads(line);asset_versions.add(record.get('parser_version','UNKNOWN'));asset_count+=1
                dimensions=record.get('dimensions') or {}
                compact_payload={key:record.get(key) for key in ('status','archive_entry_id','archive_index','offset','stored_size','expanded_size','method_hex','fragment_flag','internal_path_status','locator')}
                cursor=connection.execute('INSERT INTO assets(asset_key,source_archive,internal_path,output_path,sha256,file_type,width,height,raw_payload_json) VALUES(?,?,?,?,?,?,?,?,?)',
                                          (record['asset_id'],record['source_archive'],record.get('internal_path'),None,record.get('output_sha256'),record.get('file_type'),
                                           dimensions.get('width'),dimensions.get('height'),canonical_json(compact_payload)))
                archive_key=(record['source_archive'],record['source_archive_sha256'])
                if archive_key not in archive_source_ids:
                    archive_source_ids[archive_key]=insert_source(connection,{
                        'source_id':'client-primary','evidence_class':'RAW_CLIENT','path':record['source_archive'],
                        'sha256':record['source_archive_sha256'],'edition':None,'encoding':'binary PACK','locator':'PACK archive',
                        'notes':'Archive-level source record; per-entry locator is stored in asset_sources.',
                    },source_cache)
                connection.execute('INSERT INTO asset_sources(asset_id,source_record_id,locator) VALUES(?,?,?)',
                                   (cursor.lastrowid,archive_source_ids[archive_key],record['locator']))
        connection.execute('INSERT INTO corpus_files(path,sha256,record_count,parser_versions_json) VALUES(?,?,?,?)',
                           (jxlab.rel(asset_path),jxlab.sha256_file(asset_path),asset_count,canonical_json(sorted(asset_versions))))
        file_manifest.append({'path':jxlab.rel(asset_path),'sha256':jxlab.sha256_file(asset_path),'records':asset_count,'parser_versions':sorted(asset_versions)})
        counts['assets']=asset_count
    connection.commit()
    foreign_key_errors=connection.execute('PRAGMA foreign_key_check').fetchall()
    entities_without_source=connection.execute('SELECT COUNT(*) FROM corpus_entities e WHERE NOT EXISTS (SELECT 1 FROM corpus_entity_sources s WHERE s.entity_key=e.entity_key)').fetchone()[0]
    edges_without_source=connection.execute('SELECT COUNT(*) FROM reference_edges e WHERE NOT EXISTS (SELECT 1 FROM reference_edge_sources s WHERE s.edge_key=e.edge_key)').fetchone()[0]
    db_counts={table:connection.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0] for table in ('corpus_files','corpus_entities','source_records','corpus_entity_sources','reference_edges','reference_edge_sources','features','assets','asset_sources')}
    connection.close()
    return {'schema_version':'1.0','generator':'scripts/build_database.py','generated_at_utc':datetime.now(timezone.utc).isoformat(),
            'database_path':jxlab.rel(DATABASE_PATH),'database_sha256':jxlab.sha256_file(target),'table_counts':db_counts,
            'entities_without_source_records':entities_without_source,'edges_without_source_records':edges_without_source,
            'foreign_key_errors':foreign_key_errors,'input_files':file_manifest,'record_counts':dict(counts)}

def main():
    DATABASE_PATH.parent.mkdir(parents=True,exist_ok=True)
    fd,temp_name=tempfile.mkstemp(prefix='jx-source-lab-',suffix='.sqlite3',dir=DATABASE_PATH.parent);os.close(fd)
    temp_path=Path(temp_name)
    try:
        report=build_database(temp_path)
        os.replace(temp_path,DATABASE_PATH)
    finally:
        if temp_path.exists():temp_path.unlink()
    report['database_sha256']=jxlab.sha256_file(DATABASE_PATH)
    report_path=ROOT/'generated'/'reports'/'database-build-report.json'
    report_path.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'database':jxlab.rel(DATABASE_PATH),'report':jxlab.rel(report_path),'table_counts':report['table_counts']},indent=2))

if __name__=='__main__':main()
