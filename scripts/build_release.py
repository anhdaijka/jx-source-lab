#!/usr/bin/env python3
"""Assemble the local Research Release 1.0 snapshot."""
from __future__ import annotations

import gzip
import json
import shutil
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import jxlab

ROOT=Path(__file__).resolve().parents[1]
RELEASE=ROOT/'generated'/'release'
VERSION='1.0'

def write_json(path,payload):path.write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding='utf-8')

def copy_json(source,destination):write_json(destination,json.loads(source.read_text(encoding='utf-8')))

def gzip_jsonl(sources,destination):
    with destination.open('wb') as raw,gzip.GzipFile(filename='',mode='wb',fileobj=raw,mtime=0) as compressed:
        for source in sources:
            with source.open('rb') as input_file:
                shutil.copyfileobj(input_file,compressed)

def count_jsonl(path):
    with gzip.open(path,'rt',encoding='utf-8') as source:return sum(1 for line in source if line.strip())

def artifact(path,deliverable,canonical_sources):
    return {'deliverable':deliverable,'path':jxlab.rel(path),'sha256':jxlab.sha256_file(path),'size':path.stat().st_size,
            'record_count':count_jsonl(path) if path.suffix=='.gz' else None,
            'canonical_sources':[{'path':jxlab.rel(source),'sha256':jxlab.sha256_file(source)} for source in canonical_sources]}

def main():
    RELEASE.mkdir(parents=True,exist_ok=True)
    inventory_path=ROOT/'generated/reports/source-inventory.json';inventory=json.loads(inventory_path.read_text(encoding='utf-8'))
    if not inventory.get('hashes_included') or any('sha256' not in row for row in inventory['files']):
        raise ValueError('Release requires a fully hashed source inventory.')
    source_manifest=RELEASE/'01-source-manifest.json';copy_json(inventory_path,source_manifest)

    edition_ledger=ROOT/'research/edition-drift-ledger.json';edition=json.loads(edition_ledger.read_text(encoding='utf-8'))
    version_path=ROOT/'client/version.cfg';version_value=version_path.read_text(encoding='utf-8-sig').strip() if version_path.exists() else 'UNKNOWN'
    edition_matrix={
        'schema_version':'1.0','generator':'scripts/build_release.py','release_version':VERSION,
        'generated_at_utc':datetime.now(timezone.utc).isoformat(),
        'roots':[
            {'source_id':'client-primary','evidence_class':'RAW_CLIENT','build_version_from_client_config':version_value,'edition_identity':'UNKNOWN','path':'client/'},
            {'source_id':'server-primary','evidence_class':'RAW_SERVER','build_version':'UNKNOWN','edition_identity':'UNKNOWN','path':'server/'},
            {'source_id':'official-pages','evidence_class':'UNKNOWN','available_evidence_files':sum(1 for path in (ROOT/'official-pages').rglob('*') if path.is_file() and path.name!='README.txt'),'path':'official-pages/'},
            {'source_id':'private-input','evidence_class':'LEGACY_LEAD','available_evidence_files':sum(1 for path in (ROOT/'private-input').rglob('*') if path.is_file() and path.name!='README.txt'),'path':'private-input/'},
        ],
        'comparisons':edition['entries'],
        'interpretation_boundary':'Build/version values identify local file content only. They do not establish launch-era producer canon without authoritative provenance.',
        'manifest_source':{'path':'manifests/edition-manifest.local.yml','sha256':jxlab.sha256_file(ROOT/'manifests/edition-manifest.local.yml')},
    }
    edition_matrix_path=RELEASE/'02-edition-matrix.json';write_json(edition_matrix_path,edition_matrix)

    copy_pairs=[
        (ROOT/'research/reconstruction/main-task-graph.json',RELEASE/'03-main-task-graph.json'),
        (ROOT/'research/reconstruction/configured-non-main-task-index.json',RELEASE/'04-configured-non-main-task-index.json'),
        (ROOT/'research/reconstruction/game-story-evidence-graph.json',RELEASE/'13-game-story-reconstruction.json'),
        (ROOT/'research/unresolved-questions.json',RELEASE/'14-unresolved-questions.json'),
        (ROOT/'research/contradiction-ledger.json',RELEASE/'15-edition-drift-ledger.json'),
        (ROOT/'research/confidence-report.json',RELEASE/'16-confidence-report.json'),
    ]
    for source,destination in copy_pairs:copy_json(source,destination)
    shutil.copyfile(ROOT/'research/reconstruction/game-story-reconstruction.md',RELEASE/'13-game-story-reconstruction.md')
    shutil.copyfile(ROOT/'research/claims.jsonl',RELEASE/'claims.jsonl')

    corpus_specs=[
        ('dialogue corpus',[ROOT/'generated/records/dialogue/dialognpc-records.jsonl',ROOT/'generated/records/dialogue/task-dialogue-records.jsonl',ROOT/'generated/records/dialogue/localization-records.jsonl'],RELEASE/'05-dialogue-corpus.jsonl.gz'),
        ('NPC corpus',[ROOT/'generated/records/npcs/npc-records.jsonl'],RELEASE/'06-npc-corpus.jsonl.gz'),
        ('sect and route corpus',[ROOT/'generated/records/sects/faction-records.jsonl',ROOT/'generated/records/sects/route-records.jsonl'],RELEASE/'07-sect-route-corpus.jsonl.gz'),
        ('martial skill corpus',[ROOT/'generated/records/skills/skill-records.jsonl'],RELEASE/'08-martial-skill-corpus.jsonl.gz'),
        ('item corpus',[ROOT/'generated/records/items/item-records.jsonl'],RELEASE/'09-item-corpus.jsonl.gz'),
        ('location and map corpus',[ROOT/'generated/records/locations/location-records.jsonl'],RELEASE/'10-location-map-corpus.jsonl.gz'),
        ('feature and system corpus',[ROOT/'generated/records/features/feature-records.jsonl'],RELEASE/'11-feature-system-corpus.jsonl.gz'),
    ]
    for _,sources,destination in corpus_specs:gzip_jsonl(sources,destination)
    shutil.copyfile(ROOT/'generated/records/assets/client-asset-index.jsonl.gz',RELEASE/'12-client-asset-index.jsonl.gz')

    readme=RELEASE/'README.md'
    readme.write_text('\n'.join([
        '# JX Source Lab — Research Release 1.0','',
        'Local evidence release assembled from the supplied unknown-build client/server trees. This is source archaeology, not novel authorization.','',
        '## Authority boundary','',
        '- Raw-build implementation facts are scoped to their hashed source files.',
        '- Official Kingsoft/Xoyo/VNG evidence is absent from the supplied source scope.',
        '- Missing facts remain `UNKNOWN`; client/server/listing conflicts remain `EDITION_DRIFT`.',
        '- Proprietary payloads are not included. The client asset artifact contains metadata/hashes only.',
        '- Do not publicly redistribute this local release without a separate ownership/licensing decision.','',
        '## Known omissions','',
        '- 27,519 client fragment entries are indexed but not decoded because fragment framing is `UNKNOWN`.',
        '- Two variant-layout archives are recorded at archive level but not entry-indexed.',
        '- Image/audio/update payloads follow the text/config-first protocol and are structurally indexed, not decoded.',
        '- Internal asset paths remain `UNKNOWN` where no binary-exact listing exists.',
        '- Novel promotion remains `NOT_AUTHORIZED_FOR_NOVEL_PROMOTION`.','',
        'See `release-manifest.json`, `checksums.sha256`, and `16-confidence-report.json` for audit state.',''
    ]),encoding='utf-8')

    artifacts=[
        artifact(source_manifest,'source manifest',[inventory_path]),
        artifact(edition_matrix_path,'edition matrix',[edition_ledger,ROOT/'manifests/edition-manifest.local.yml']),
        artifact(RELEASE/'03-main-task-graph.json','main task graph',[ROOT/'research/reconstruction/main-task-graph.json']),
        artifact(RELEASE/'04-configured-non-main-task-index.json','configured non-main task index',[ROOT/'research/reconstruction/configured-non-main-task-index.json']),
    ]
    artifacts.extend(artifact(destination,label,sources) for label,sources,destination in corpus_specs)
    artifacts.extend([
        artifact(RELEASE/'12-client-asset-index.jsonl.gz','client asset index',[ROOT/'generated/records/assets/client-asset-index.jsonl.gz']),
        artifact(RELEASE/'13-game-story-reconstruction.json','game-story evidence reconstruction',[ROOT/'research/reconstruction/game-story-evidence-graph.json']),
        artifact(RELEASE/'14-unresolved-questions.json','unresolved questions',[ROOT/'research/unresolved-questions.json']),
        artifact(RELEASE/'15-edition-drift-ledger.json','edition-drift and contradiction ledger',[ROOT/'research/contradiction-ledger.json']),
        artifact(RELEASE/'16-confidence-report.json','confidence report',[ROOT/'research/confidence-report.json']),
    ])
    manifest={
        'schema_version':'1.0','release_name':'JX Source Lab Research Release','release_version':VERSION,
        'generator':'scripts/build_release.py','generated_at_utc':datetime.now(timezone.utc).isoformat(),
        'release_status':'COMPLETE_WITH_DOCUMENTED_UNKNOWNS','novel_promotion':'NOT_AUTHORIZED_FOR_NOVEL_PROMOTION',
        'artifacts':artifacts,
        'validation_requirements':['artifact SHA-256','gzip JSONL parse','JSON parse','source provenance coverage','SQLite foreign keys','claim status audit'],
    }
    manifest_path=RELEASE/'release-manifest.json';write_json(manifest_path,manifest)
    checksum_targets=sorted([path for path in RELEASE.iterdir() if path.is_file() and path.name not in {'.gitkeep','checksums.sha256'}],key=lambda value:value.name)
    (RELEASE/'checksums.sha256').write_text('\n'.join(f'{jxlab.sha256_file(path)}  {path.name}' for path in checksum_targets)+'\n',encoding='ascii')
    print(json.dumps({'release':jxlab.rel(RELEASE),'artifact_count':len(artifacts),'status':manifest['release_status'],
                      'sizes':{path.name:path.stat().st_size for path in checksum_targets}},indent=2))

if __name__=='__main__':main()
