#!/usr/bin/env python3
"""Build a compact client PACK entry index; decode text/config archives first."""
from __future__ import annotations

import gzip
import hashlib
import json
import os
import tempfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import jxlab

ROOT=Path(__file__).resolve().parents[1]
OUTPUT=ROOT/'generated'/'records'/'assets'/'client-asset-index.jsonl.gz'
REPORT=ROOT/'generated'/'reports'/'client-asset-index-report.json'
PARSER_VERSION='jxlab client-asset-index/0.1'
TEXT_FIRST_ARCHIVES={
    'aspaksc.pak','aspakst.pak','l10n.pak','launcher.pak','misc.pak','script.pak',
    'setting.pak','task_publish.pak','ui.pak','wind_pak.pak',
}

def known_archive_hashes():
    path=ROOT/'generated'/'reports'/'pak-reference-report.json'
    payload=json.loads(path.read_text(encoding='utf-8'))
    return {row['path']:row.get('sha256') for row in payload['archives']}

def main():
    hashes=known_archive_hashes();OUTPUT.parent.mkdir(parents=True,exist_ok=True)
    fd,temp_name=tempfile.mkstemp(prefix='client-assets-',suffix='.jsonl.gz',dir=OUTPUT.parent);os.close(fd)
    temp=Path(temp_name);status_counts=Counter();type_counts=Counter();archives=[];record_count=0
    try:
        with temp.open('wb') as raw_output,gzip.GzipFile(filename='',mode='wb',fileobj=raw_output,mtime=0) as compressed:
            for archive in sorted((ROOT/'client').rglob('*.pak'),key=lambda value:value.as_posix().lower()):
                relative=jxlab.rel(archive);layout=jxlab.inspect_pack_layout(archive);archive_hash=hashes.get(relative)
                if not archive_hash:
                    archive_hash=jxlab.sha256_file(archive)
                archive_summary={'path':relative,'sha256':archive_hash,'size':archive.stat().st_size,'layout_status':layout['status'],
                                 'index_record_count':layout.get('index_record_count'),'text_first_scope':archive.name.lower() in TEXT_FIRST_ARCHIVES}
                archives.append(archive_summary)
                if layout['status']!='standard_index_layout':
                    status_counts['unsupported_archive_layout']+=1;continue
                pack=jxlab.read_pack_index(archive);decode_scope=archive.name.lower() in TEXT_FIRST_ARCHIVES
                with archive.open('rb') as source:
                    for entry in pack['entries']:
                        record={
                            'schema_version':'1.0','parser_version':PARSER_VERSION,
                            'asset_id':f'{archive_hash}:{entry["id_hex"]}','source_archive':relative,
                            'source_archive_sha256':archive_hash,'internal_path':None,'internal_path_status':'UNKNOWN',
                            'archive_entry_id':entry['id_hex'],'archive_index':entry['index'],'offset':entry['offset'],
                            'stored_size':entry['stored_size'],'expanded_size':entry['expanded_size'],
                            'method_hex':f"0x{entry['method']:08x}",'fragment_flag':entry['fragment_flag'],
                            'locator':f"index:{entry['index']};id:{entry['id_hex']};offset:{entry['offset']};stored:{entry['stored_size']}",
                            'evidence_class':'RAW_CLIENT','output_sha256':None,'file_type':'UNKNOWN','dimensions':None,
                        }
                        if entry['fragment_flag']:
                            record['status']='unsupported_fragment'
                        elif not decode_scope:
                            record['status']='indexed_not_decoded_protocol_scope'
                        else:
                            source.seek(entry['offset']);packed=source.read(entry['stored_size'])
                            try:
                                if entry['method']==jxlab.PACK_METHOD_NONE:
                                    output=packed
                                    if len(output)!=entry['expanded_size']:raise ValueError('NONE size mismatch')
                                elif entry['method']==jxlab.PACK_METHOD_UCL_NRV2B_SAFE_8:
                                    output=jxlab.nrv2b_decompress_safe_8(packed,entry['expanded_size'])
                                else:raise ValueError(f"unsupported method 0x{entry['method']:08x}")
                                metadata=jxlab.payload_metadata(output)
                                record.update(status='decoded_validated',output_sha256=hashlib.sha256(output).hexdigest(),
                                              file_type=metadata['file_type'],dimensions=metadata['dimensions'],
                                              encoding_candidate=metadata['encoding_candidate'],signature_hex=metadata['signature_hex'])
                                type_counts[metadata['file_type']]+=1
                            except Exception as error:
                                record.update(status='decode_error',error=str(error))
                        status_counts[record['status']]+=1;record_count+=1
                        compressed.write((json.dumps(record,ensure_ascii=False,separators=(',',':'))+'\n').encode('utf-8'))
        os.replace(temp,OUTPUT)
    finally:
        if temp.exists():temp.unlink()
    report={
        'schema_version':'1.0','generator':'scripts/build_asset_index.py','parser_version':PARSER_VERSION,
        'generated_at_utc':datetime.now(timezone.utc).isoformat(),'output_path':jxlab.rel(OUTPUT),
        'output_sha256':jxlab.sha256_file(OUTPUT),'record_count':record_count,'archive_count':len(archives),
        'status_counts':dict(status_counts),'decoded_type_counts':dict(type_counts),'archives':archives,
        'omissions':[
            'Internal paths remain UNKNOWN unless a binary-exact listing is available; no path-hash algorithm is inferred.',
            'Image/audio/update payloads are indexed structurally but not decoded in Research Release 1.0 text/config-first scope.',
            'Fragment entries and two variant archive layouts remain unsupported and are explicitly counted.',
        ],
    }
    REPORT.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'output':jxlab.rel(OUTPUT),'record_count':record_count,'status_counts':dict(status_counts)},indent=2))

if __name__=='__main__':main()
