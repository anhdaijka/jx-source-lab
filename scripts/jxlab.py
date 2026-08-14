#!/usr/bin/env python3
from __future__ import annotations
import argparse, csv, hashlib, io, json, os, re, struct, time, tomllib
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from collections import Counter, defaultdict

ROOT=Path(__file__).resolve().parents[1]
with (ROOT/'lab.toml').open('rb') as f: CFG=tomllib.load(f)
REPORT_DIR=ROOT/CFG['outputs']['reports']; REPORT_DIR.mkdir(parents=True,exist_ok=True)
TASK_RECORD_DIR=ROOT/CFG['outputs']['records']/'tasks'; TASK_RECORD_DIR.mkdir(parents=True,exist_ok=True)
GENERATOR='scripts/jxlab.py'
REPORT_SCHEMA_VERSION='1.0'
PACK_INDEX_RECORD_SIZE=16
PACK_STORED_SIZE_MASK=0x07ffffff
PACK_FRAGMENT_FLAG=0x10000000
PACK_METHOD_MASK=0xf0000000
PACK_METHOD_NONE=0x00000000
PACK_METHOD_UCL_NRV2B_SAFE_8=0x20000000

class NRVDecodeError(ValueError):
    """Raised when a packed NRV2B stream violates the bounded decoder contract."""

def nrv2b_decompress_safe_8(source, expected_size):
    """Decode the exact UCL NRV2B safe_8 stream variant used by XPackFile.

    The implementation is output-bounded and rejects input overrun, output
    overrun, invalid lookbehind, unconsumed input, and size mismatches.
    """
    if expected_size < 0:
        raise NRVDecodeError('Expected output size cannot be negative.')
    input_offset=0;bit_buffer=0;output=bytearray();last_match_offset=1

    def get_bit():
        nonlocal input_offset,bit_buffer
        if bit_buffer & 0x7f:
            bit_buffer*=2
        else:
            if input_offset>=len(source):
                raise NRVDecodeError('Input overrun while reading the bit stream.')
            bit_buffer=source[input_offset]*2+1
            input_offset+=1
        return (bit_buffer>>8)&1

    while True:
        while get_bit():
            if input_offset>=len(source):
                raise NRVDecodeError('Input overrun while reading a literal.')
            if len(output)>=expected_size:
                raise NRVDecodeError('Output overrun while writing a literal.')
            output.append(source[input_offset]);input_offset+=1

        match_offset=1
        while True:
            match_offset=match_offset*2+get_bit()
            if match_offset>0xffffff+3:
                raise NRVDecodeError('Match offset exceeds the NRV2B safe bound.')
            if get_bit():break

        if match_offset==2:
            match_offset=last_match_offset
        else:
            if input_offset>=len(source):
                raise NRVDecodeError('Input overrun while reading a match offset.')
            match_offset=((match_offset-3)*256+source[input_offset])&0xffffffff
            input_offset+=1
            if match_offset==0xffffffff:
                break
            match_offset+=1;last_match_offset=match_offset

        match_length=get_bit();match_length=match_length*2+get_bit()
        if match_length==0:
            match_length=1
            while True:
                match_length=match_length*2+get_bit()
                if match_length>=expected_size:
                    raise NRVDecodeError('Match length exceeds the output bound.')
                if get_bit():break
            match_length+=2
        match_length+=int(match_offset>0xd00)
        replay_length=match_length+1
        if match_offset>len(output):
            raise NRVDecodeError('Match offset exceeds decoded output.')
        if len(output)+replay_length>expected_size:
            raise NRVDecodeError('Output overrun while replaying a match.')
        for _ in range(replay_length):output.append(output[-match_offset])

    if len(output)!=expected_size:
        raise NRVDecodeError(f'Decoded size {len(output)} does not equal expected size {expected_size}.')
    if input_offset!=len(source):
        raise NRVDecodeError(f'Compressed input was not fully consumed ({input_offset}/{len(source)} bytes).')
    return bytes(output)

def report_metadata():
    return {
        'schema_version': REPORT_SCHEMA_VERSION,
        'generator': GENERATOR,
        'generated_at_utc': datetime.now(timezone.utc).isoformat(),
        'input_scope': {sid: rel(base) for sid,base in source_roots()},
    }

def markdown_metadata(metadata):
    scope=', '.join(f'`{sid}` = `{path}`' for sid,path in metadata['input_scope'].items())
    return [
        f"- Generator: `{metadata['generator']}`",
        f"- Schema version: `{metadata['schema_version']}`",
        f"- Generated (UTC): `{metadata['generated_at_utc']}`",
        f'- Input scope: {scope}',
    ]

def rel(p):
    try:return p.relative_to(ROOT).as_posix()
    except ValueError:return str(p)

def sha256_file(path,chunk=1024*1024):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(chunk),b''):h.update(b)
    return h.hexdigest()

def read_prefix(path, max_bytes):
    with path.open('rb') as f:
        return f.read(max_bytes)

def probe_encoding(path,max_bytes):
    try:data=read_prefix(path,max_bytes)
    except Exception:return None,False
    if b'\x00' in data[:4096]:
        for enc in ('utf-16','utf-16-le','utf-16-be'):
            try:data.decode(enc);return enc,True
            except Exception:pass
        return None,False
    for enc in ('utf-8-sig','utf-8','gb18030','cp936','big5','cp1252'):
        try:data.decode(enc);return enc,True
        except Exception:pass
    return None,False

def source_roots():
    for sid,value in CFG['source_roots'].items():
        p=ROOT/value
        if p.exists():yield sid,p

def iter_files(base):
    for dp,dns,fns in os.walk(base):
        dns[:]=[d for d in dns if d not in {'.git','__pycache__'}]
        for n in fns:
            p=Path(dp)/n
            if p.is_file() and p.name!='README.txt':yield p

def inventory(args):
    max_probe=int(CFG['inventory']['max_text_probe_bytes']); do_hash=args.hash or bool(CFG['inventory']['hash_files_by_default'])
    records=[]; extc=Counter(); rootc=Counter(); rootb=Counter(); txtc=Counter()
    for sid,base in source_roots():
        for p in iter_files(base):
            try:st=p.stat()
            except OSError:continue
            enc,text_like=probe_encoding(p,max_probe); ext=p.suffix.lower() or '<none>'
            r={'source_root':sid,'path':rel(p),'size':st.st_size,'mtime':st.st_mtime,'extension':ext,'text_like':text_like,'encoding_probe':enc}
            if do_hash:
                try:r['sha256']=sha256_file(p)
                except OSError as e:r['sha256_error']=str(e)
            records.append(r);extc[ext]+=1;rootc[sid]+=1;rootb[sid]+=st.st_size;txtc['text_like' if text_like else 'binary_or_unknown']+=1
    records.sort(key=lambda r:r['path'].lower())
    metadata=report_metadata()
    payload={**metadata,'generated_at_unix':time.time(),'hashes_included':do_hash,'file_count':len(records),'roots':{k:{'files':rootc[k],'bytes':rootb[k]} for k in rootc},'extension_counts':dict(extc.most_common()),'text_probe_counts':dict(txtc),'files':records}
    (REPORT_DIR/'source-inventory.json').write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding='utf-8')
    tree=[{'path':r['path'],'size':r['size'],'ext':r['extension'],'text_like':r['text_like'],'encoding':r['encoding_probe']} for r in records]
    (REPORT_DIR/'source-tree-index.json').write_text(json.dumps({**metadata,'files':tree},ensure_ascii=False,indent=2),encoding='utf-8')
    lines=['# Source Inventory','',*markdown_metadata(metadata),f'- Files: **{len(records):,}**',f'- Hashes included: **{do_hash}**','','## Roots','']
    for k in sorted(rootc):lines.append(f'- `{k}`: {rootc[k]:,} files / {rootb[k]:,} bytes')
    lines+=['','## Top extensions','']+[f'- `{e}`: {c:,}' for e,c in extc.most_common(60)]+['','## Text probe','']+[f'- {k}: {v:,}' for k,v in txtc.items()]
    (REPORT_DIR/'source-inventory.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(f'Wrote inventory for {len(records):,} files to {rel(REPORT_DIR)}')
    if not do_hash:print('Tip: run `inventory --hash` later for SHA-256 provenance.')

def find_pak_refs(args):
    max_probe=int(CFG['inventory']['max_text_probe_bytes']); pak_exts={x.lower() for x in CFG['pak']['extensions']}; cext={x.lower() for x in CFG['text']['candidate_extensions']}
    archives=[]; refs=[]; needles=['.pak','pakfile','packfile','loadpack','package','archive','compress','inflate','deflate','zlib','virtual file','filesystem','fileindex','file index']
    for sid,base in source_roots():
        for p in iter_files(base):
            ext=p.suffix.lower()
            if ext in pak_exts:
                try:
                    with p.open('rb') as fh:head=fh.read(32).hex()
                    archives.append({'source_root':sid,'path':rel(p),'size':p.stat().st_size,'sha256':sha256_file(p) if args.hash else None,'header_hex':head})
                except OSError:pass
            if ext not in cext:continue
            enc,ok=probe_encoding(p,max_probe)
            if not ok or not enc:continue
            try:text=read_prefix(p,max_probe).decode(enc,errors='replace')
            except Exception:continue
            low=text.lower(); hits=[n for n in needles if n in low]
            if hits:
                samples=[]
                for i,line in enumerate(text.splitlines(),1):
                    if any(n in line.lower() for n in hits):
                        samples.append({'line':i,'text':line[:500]})
                        if len(samples)>=12:break
                refs.append({'source_root':sid,'path':rel(p),'encoding':enc,'hits':hits,'samples':samples})
    metadata=report_metadata()
    (REPORT_DIR/'pak-reference-report.json').write_text(json.dumps({**metadata,'hashes_included':args.hash,'archives':archives,'code_text_references':refs},ensure_ascii=False,indent=2),encoding='utf-8')
    lines=['# PAK / Archive Reference Report','',*markdown_metadata(metadata),f"- Archive hashes included: **{args.hash}**",'','## Archive files','']
    lines += [f"- `{a['path']}` — {a['size']:,} bytes; header `{a['header_hex']}`" for a in archives] or ['- None found.']
    lines += ['','## Candidate loader/code references','']
    if refs:
        for r in refs[:300]:
            lines += [f"### `{r['path']}`",'Hits: '+', '.join(r['hits'])]
            lines += [f"- L{s['line']}: `{s['text']}`" for s in r['samples']]+['']
    else:lines+=['- No obvious references found.']
    (REPORT_DIR/'pak-reference-report.md').write_text('\n'.join(lines).rstrip()+'\n',encoding='utf-8')
    print(f'Found {len(archives)} archives and {len(refs)} candidate loader/reference files.')

def text_candidates(args):
    max_probe=int(CFG['inventory']['max_text_probe_bytes']); limit=int(CFG['inventory']['max_candidate_examples']); cext={x.lower() for x in CFG['text']['candidate_extensions']}
    keys={'quest_task':['task','quest','任务','任务id','mission'],'dialogue':['dialog','talk','npc','对话','对白','say'],'skill_martial':['skill','magic','技能','武功','门派','faction'],'item':['item','物品','道具','equip','装备'],'map_world':['map','地图','scene','world','teleport'],'localization':['local','string','language','translate','简体','繁体']}
    buckets=defaultdict(list)
    for sid,base in source_roots():
        for p in iter_files(base):
            if p.suffix.lower() not in cext:continue
            enc,ok=probe_encoding(p,max_probe)
            if not ok or not enc:continue
            try:text=read_prefix(p,max_probe).decode(enc,errors='replace')
            except Exception:continue
            hay=(rel(p)+'\n'+text[:50000]).lower()
            for b,terms in keys.items():
                if any(t.lower() in hay for t in terms) and len(buckets[b])<limit:
                    buckets[b].append({'source_root':sid,'path':rel(p),'encoding':enc,'size':p.stat().st_size})
    metadata=report_metadata()
    (REPORT_DIR/'text-candidates.json').write_text(json.dumps({**metadata,'candidate_groups':buckets},ensure_ascii=False,indent=2),encoding='utf-8')
    lines=['# Candidate Data Sources','',*markdown_metadata(metadata),'']
    for b in keys:
        lines += [f'## {b}','']+[f"- `{r['path']}` ({r['encoding']}, {r['size']:,} bytes)" for r in buckets[b]]+[''] if buckets[b] else [f'## {b}','','- No candidates yet.','']
    content='\n'.join(lines).rstrip()+'\n';(REPORT_DIR/'text-candidates.md').write_text(content,encoding='utf-8');(REPORT_DIR/'candidate-data-sources.md').write_text(content,encoding='utf-8')
    print('Wrote candidate source reports.')

TASK_TABLES=(
    ('task_id_range', 'server/gameserver/setting/task/task_def.txt', 'TASK_ID_FIRST', 'TASK_NAME'),
    ('task_objective_type', 'server/gameserver/setting/task/linktask/type_select.txt', 'TypeId', 'TypeName'),
    ('task_objective_kill_npc', 'server/gameserver/setting/task/linktask/entity_killnpc.txt', 'TaskId', 'TaskName'),
    ('task_objective_find_item', 'server/gameserver/setting/task/linktask/entity_finditem.txt', 'TaskId', 'TaskName'),
    ('task_objective_find_equip', 'server/gameserver/setting/task/linktask/entity_findequip.txt', 'TaskId', 'TaskName'),
    ('task_objective_buy_item', 'server/gameserver/setting/task/linktask/entity_buyitem.txt', 'TaskId', 'TaskName'),
)

def read_text_file(path):
    encoding,ok=probe_encoding(path,int(CFG['inventory']['max_text_probe_bytes']))
    if not ok or not encoding:
        raise ValueError(f'Unable to determine text encoding: {rel(path)}')
    return path.read_bytes().decode(encoding),encoding

def parse_tsv_table(path):
    text,encoding=read_text_file(path)
    rows=[row for row in csv.reader(io.StringIO(text),delimiter='\t') if any(cell for cell in row)]
    if len(rows)<3:
        raise ValueError(f'Expected two header rows and at least one data row: {rel(path)}')
    header,localized_header=rows[:2]
    if not all(header):
        raise ValueError(f'Empty column name in header: {rel(path)}')
    records=[]; malformed=[]
    for line_number,row in enumerate(rows[2:],3):
        if len(row)!=len(header):
            malformed.append({'line':line_number,'column_count':len(row),'expected_column_count':len(header),'raw_fields':row})
            continue
        records.append((line_number,dict(zip(header,row))))
    return {'encoding':encoding,'header':header,'localized_header':localized_header,'records':records,'malformed_rows':malformed}

def parse_task_catalog(args):
    metadata=report_metadata(); output_path=TASK_RECORD_DIR/'task-source-records.jsonl'
    report_rows=[]; total_records=0
    with output_path.open('w',encoding='utf-8',newline='\n') as output:
        for kind,relative_path,id_field,name_field in TASK_TABLES:
            path=ROOT/relative_path
            parsed=parse_tsv_table(path)
            source_hash=sha256_file(path)
            emitted=0
            for line_number,fields in parsed['records']:
                if kind=='task_id_range':
                    task_id=[fields['TASK_ID_FIRST'],fields['TASK_ID_LAST']]
                else:
                    task_id=fields[id_field]
                source_record={
                    'source_id':'server-primary','evidence_class':'RAW_SERVER','path':relative_path,
                    'sha256':source_hash,'edition':None,'encoding':parsed['encoding'],
                    'locator':f'line:{line_number}','notes':'Raw TSV task-source table; no story interpretation.',
                }
                record={
                    'schema_version':'1.0','parser_version':'jxlab task-catalog/0.1','record_kind':kind,
                    'task_id':task_id,'name':fields[name_field],'raw_fields':fields,'source_records':[source_record],
                }
                output.write(json.dumps(record,ensure_ascii=False,separators=(',',':'))+'\n')
                emitted+=1
            total_records+=emitted
            report_rows.append({
                'record_kind':kind,'path':relative_path,'sha256':source_hash,'encoding':parsed['encoding'],
                'header':parsed['header'],'localized_header':parsed['localized_header'],'records_emitted':emitted,
                'malformed_rows':parsed['malformed_rows'],
            })
    payload={**metadata,'parser_version':'jxlab task-catalog/0.1','output_path':rel(output_path),
             'records_emitted':total_records,'dependency_edges_emitted':0,
             'dependency_note':'No dependency source was parsed; no dependency is inferred from task titles, ranges, or objective rows.',
             'inputs':report_rows}
    (REPORT_DIR/'task-parser-report.json').write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding='utf-8')
    lines=['# Task Catalog Parser Report','',*markdown_metadata(metadata),'- Parser version: `jxlab task-catalog/0.1`',
           f'- Output: `{rel(output_path)}`',f'- Records emitted: **{total_records:,}**','- Dependency edges emitted: **0**',
           '- Dependency status: no dependency is inferred from these source tables.','','## Inputs','']
    for row in report_rows:
        lines += [f"### `{row['path']}`",f"- Record kind: `{row['record_kind']}`",f"- SHA-256: `{row['sha256']}`",
                  f"- Encoding: `{row['encoding']}`",f"- Records emitted: {row['records_emitted']}",
                  f"- Malformed rows: {len(row['malformed_rows'])}",'']
    (REPORT_DIR/'task-parser-report.md').write_text('\n'.join(lines).rstrip()+'\n',encoding='utf-8')
    print(f'Wrote {total_records:,} task-source records from {len(TASK_TABLES)} TSV inputs.')

TASK_PUBLISH_LISTINGS=(
    ('client-primary','RAW_CLIENT','client/pak/task_publish.pak','client/pak/task_publish.pak.txt'),
    ('server-primary','RAW_SERVER','server/gameserver/pak/task_publish.pak','server/gameserver/pak/task_publish.pak.txt'),
)

def parse_pak_listing(path):
    text,encoding=read_text_file(path)
    lines=[line for line in text.splitlines() if line]
    if len(lines)<3:
        raise ValueError(f'Listing is missing metadata, header, or entries: {rel(path)}')
    metadata=dict(re.findall(r'([A-Za-z]+):([^\t]+)',lines[0]))
    if 'TotalFile' not in metadata:
        raise ValueError(f'Listing has no TotalFile metadata: {rel(path)}')
    header=lines[1].split('\t')
    expected=['Index','ID','Time','FileName','Size','InPakSize','ComprFlag','CRC']
    if header!=expected:
        raise ValueError(f'Unexpected listing header: {rel(path)}')
    entries=[]
    for line_number,line in enumerate(lines[2:],3):
        fields=line.split('\t')
        if len(fields)!=len(header):
            raise ValueError(f'Malformed listing row at {rel(path)} line {line_number}')
        entries.append((line_number,dict(zip(header,fields))))
    if len(entries)!=int(metadata['TotalFile']):
        raise ValueError(f"Listing count mismatch in {rel(path)}: metadata={metadata['TotalFile']} rows={len(entries)}")
    return {'encoding':encoding,'metadata':metadata,'entries':entries}

def task_publish_entry_kind(internal_path):
    normalized=internal_path.replace('\\','/').lower()
    match=re.search(r'/task_publish/(task|sub)/([0-9a-f]{16})\.xml$',normalized)
    if match:
        return (f"{'task' if match.group(1)=='task' else 'subtask'}_xml_candidate",match.group(2))
    if normalized.endswith('/task_publish/textlist.xml'):
        return ('textlist_xml_candidate',None)
    return ('other_archive_entry',None)

def inspect_task_publish_index(args):
    metadata=report_metadata(); parsed_sources=[]
    for source_id,evidence_class,archive_relative,listing_relative in TASK_PUBLISH_LISTINGS:
        archive_path=ROOT/archive_relative; listing_path=ROOT/listing_relative
        parsed=parse_pak_listing(listing_path)
        parsed_sources.append({
            'source_id':source_id,'evidence_class':evidence_class,'archive_path':archive_relative,
            'archive_sha256':sha256_file(archive_path),'archive_size':archive_path.stat().st_size,
            'listing_path':listing_relative,'listing_sha256':sha256_file(listing_path),'listing_size':listing_path.stat().st_size,
            **parsed,
        })
    canonical=parsed_sources[-1]
    entries=[]
    for line_number,fields in canonical['entries']:
        entry_kind,task_id_hex=task_publish_entry_kind(fields['FileName'])
        entries.append({
            'entry_kind':entry_kind,'task_id_hex':task_id_hex,'archive_entry':fields,
            'source_records':[{
                'source_id':source['source_id'],'evidence_class':source['evidence_class'],
                'path':source['listing_path'],'sha256':source['listing_sha256'],'edition':None,'encoding':source['encoding'],
                'locator':f'line:{line_number}','notes':'Companion PAK listing entry; archive payload was not extracted.',
            } for source in parsed_sources],
        })
    comparison={
        'archive_bytes_identical':len({source['archive_sha256'] for source in parsed_sources})==1,
        'listing_bytes_identical':len({source['listing_sha256'] for source in parsed_sources})==1,
        'entry_count_identical':len({len(source['entries']) for source in parsed_sources})==1,
        'interpretation':'Byte identity applies only to the listed client/server task_publish files; it does not establish complete edition identity or validate archive extraction.',
    }
    payload={**metadata,'parser_version':'jxlab task-publish-index/0.1','pak_payload_extracted':False,
             'sources':[{key:value for key,value in source.items() if key not in {'entries'}} for source in parsed_sources],
             'comparison':comparison,'entries':entries}
    output_json=REPORT_DIR/'task-publish-index.json'; output_md=REPORT_DIR/'task-publish-index.md'
    output_json.write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding='utf-8')
    kinds=Counter(entry['entry_kind'] for entry in entries)
    lines=['# Task Publish Listing Index','',*markdown_metadata(metadata),'- Parser version: `jxlab task-publish-index/0.1`',
           '- Archive payload extracted: **False**','',f"- Entries listed: **{len(entries):,}**",
           f"- Client/server archive bytes identical: **{comparison['archive_bytes_identical']}**",
           f"- Client/server listing bytes identical: **{comparison['listing_bytes_identical']}**",'', '## Entry classes','']
    lines += [f'- `{kind}`: {count:,}' for kind,count in sorted(kinds.items())]
    lines += ['','## Evidence boundary','',f"- {comparison['interpretation']}",
              '- `ComprFlag` is preserved as a listing field only; this report does not assign a compression algorithm.']
    output_md.write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(f'Wrote task_publish listing index for {len(entries):,} entries.')

def inspect_pack_layout(path):
    file_size=path.stat().st_size
    with path.open('rb') as source:
        header=source.read(32)
        if len(header)<32:
            return {'status':'invalid_header','file_size':file_size,'header_hex':header.hex(),'reason':'Header is shorter than 32 bytes.'}
        magic,count,index_offset,header_size=struct.unpack_from('<4sIII',header,0)
        result={
            'status':'unknown','file_size':file_size,'header_hex':header.hex(),'magic_ascii':magic.decode('ascii',errors='replace'),
            'index_record_count':count,'index_offset':index_offset,'header_size_field':header_size,
            'index_record_size':PACK_INDEX_RECORD_SIZE,
            'expected_index_bytes':count*PACK_INDEX_RECORD_SIZE,'actual_tail_bytes':file_size-index_offset,
        }
        if magic!=b'PACK':
            result.update(status='unsupported_magic',reason='Magic is not PACK.');return result
        if header_size!=32 or not (32<=index_offset<=file_size) or file_size-index_offset!=count*PACK_INDEX_RECORD_SIZE:
            result.update(status='variant_or_trailing_layout',reason='Header/index boundary does not match the observed 32-byte header plus count x 16-byte index layout.');return result
        source.seek(index_offset);index_data=source.read(count*PACK_INDEX_RECORD_SIZE)
    methods=Counter();fragment_flags=Counter();ranges=[];ids=set();duplicate_ids=0;samples=[];size_relations=Counter()
    for index in range(count):
        elem_id,offset,expanded_size_candidate,packed_method=struct.unpack_from('<IIII',index_data,index*PACK_INDEX_RECORD_SIZE)
        stored_size=packed_method&PACK_STORED_SIZE_MASK
        method=packed_method&PACK_METHOD_MASK
        fragment=bool(packed_method&PACK_FRAGMENT_FLAG)
        methods[method]+=1;fragment_flags[fragment]+=1
        if elem_id in ids:duplicate_ids+=1
        ids.add(elem_id);ranges.append((offset,offset+stored_size))
        size_relations['expanded_eq_stored' if expanded_size_candidate==stored_size else 'expanded_gt_stored' if expanded_size_candidate>stored_size else 'expanded_lt_stored']+=1
        if len(samples)<8:
            samples.append({'index':index,'id_hex':f'{elem_id:08x}','offset':offset,
                            'expanded_size_candidate':expanded_size_candidate,'stored_size_27':stored_size,
                            'packed_method_and_size_hex':f'0x{packed_method:08x}',
                            'method_nibble_hex':f'0x{method:08x}','fragment_flag':fragment})
    sorted_ranges=sorted(ranges)
    in_bounds=all(header_size<=start<=end<=index_offset for start,end in sorted_ranges)
    gaps=[{'previous_end':left[1],'next_start':right[0]} for left,right in zip(sorted_ranges,sorted_ranges[1:]) if left[1]!=right[0]]
    contiguous=(not sorted_ranges and index_offset==header_size) or bool(sorted_ranges and sorted_ranges[0][0]==header_size and sorted_ranges[-1][1]==index_offset and not gaps)
    result.update(status='standard_index_layout',index_ids_unique=len(ids),duplicate_index_ids=duplicate_ids,
                  method_nibble_counts={f'0x{method:08x}':value for method,value in sorted(methods.items())},
                  fragment_flag_counts={str(flag).lower():value for flag,value in sorted(fragment_flags.items())},
                  payload_ranges_in_bounds=in_bounds,payload_contiguous=contiguous,payload_gap_count=len(gaps),
                  payload_gap_samples=gaps[:20],size_relation_counts=dict(size_relations),index_record_samples=samples)
    return result

def read_pack_index(path):
    """Return a bounded PACK header and complete index without reading payloads."""
    layout=inspect_pack_layout(path)
    if layout['status']!='standard_index_layout':
        raise ValueError(f"Unsupported PACK layout for {rel(path)}: {layout['status']}")
    with path.open('rb') as source:
        header=source.read(32)
        _,count,index_offset,header_size=struct.unpack_from('<4sIII',header,0)
        source.seek(index_offset)
        index_data=source.read(count*PACK_INDEX_RECORD_SIZE)
    entries=[]
    for index in range(count):
        elem_id,offset,expanded_size,packed=struct.unpack_from('<IIII',index_data,index*PACK_INDEX_RECORD_SIZE)
        entries.append({
            'index':index,'id':elem_id,'id_hex':f'{elem_id:08x}','offset':offset,
            'expanded_size':expanded_size,'stored_size':packed&PACK_STORED_SIZE_MASK,
            'packed_method_and_size':packed,'method':packed&PACK_METHOD_MASK,
            'fragment_flag':bool(packed&PACK_FRAGMENT_FLAG),
        })
    return {'header_size':header_size,'index_offset':index_offset,'entries':entries}

def validated_listing_map(archive_path,entries,listing_path=None):
    """Use a companion listing only when its IDs and sizes match the binary index."""
    listing_path=listing_path or archive_path.with_name(archive_path.name+'.txt')
    if not listing_path.exists():
        return {},{'status':'not_available','path':rel(listing_path)}
    parsed=parse_pak_listing(listing_path)
    rows={int(fields['ID'],16):fields for _,fields in parsed['entries']}
    reasons=[]
    if len(rows)!=len(entries):reasons.append(f"unique listing IDs {len(rows)} != binary entries {len(entries)}")
    for entry in entries:
        fields=rows.get(entry['id'])
        if fields is None:
            reasons.append(f"missing id {entry['id_hex']}")
        elif int(fields['Size'])!=entry['expanded_size'] or int(fields['InPakSize'])!=entry['stored_size']:
            reasons.append(f"size mismatch for id {entry['id_hex']}")
        if len(reasons)>=20:break
    if reasons:
        return {},{
            'status':'edition_drift','path':rel(listing_path),'sha256':sha256_file(listing_path),
            'encoding':parsed['encoding'],'reasons':reasons,
            'interpretation':'Companion listing is retained as a lead only and is not used for internal paths.',
        }
    return rows,{
        'status':'binary_exact','path':rel(listing_path),'sha256':sha256_file(listing_path),
        'encoding':parsed['encoding'],'entry_count':len(rows),
    }

def safe_internal_path(value):
    normalized=value.replace('\\','/').lstrip('/')
    parts=PurePosixPath(normalized).parts
    if not parts or any(part in {'','..','.'} or ':' in part or '\x00' in part for part in parts):
        raise ValueError(f'Unsafe archive path: {value!r}')
    return Path(*parts)

def payload_metadata(data,internal_path=None):
    suffix=Path(internal_path).suffix.lower() if internal_path else ''
    kind='binary';dimensions=None
    if data.startswith(b'\x89PNG\r\n\x1a\n') and len(data)>=24:
        kind='png';dimensions={'width':struct.unpack_from('>I',data,16)[0],'height':struct.unpack_from('>I',data,20)[0]}
    elif data.startswith(b'\xff\xd8\xff'):kind='jpeg'
    elif data.startswith(b'BM') and len(data)>=26:
        kind='bmp';dimensions={'width':struct.unpack_from('<I',data,18)[0],'height':struct.unpack_from('<I',data,22)[0]}
    elif data.startswith(b'RIFF') and data[8:12]==b'WAVE':kind='wav'
    elif data.startswith(b'OggS'):kind='ogg'
    elif data.lstrip().startswith((b'<?xml',b'<Task',b'<Sub',b'<Text',b'<factions')):kind='xml'
    elif data.startswith(b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1'):kind='ole_compound_file'
    elif suffix in {'.xml','.lua','.txt','.ini','.cfg','.csv','.tsv','.tab','.lst','.list','.properties'}:
        kind=suffix.lstrip('.') or 'text'
    elif data and b'\x00' not in data[:4096]:
        sample=data[:4096]
        printable=sum(byte in b'\t\r\n' or 32<=byte<127 or byte>=128 for byte in sample)
        if printable/len(sample)>=0.95:kind='text_candidate'
    encoding=None
    if kind in {'xml','lua','txt','ini','cfg','csv','tsv','tab','lst','list','properties','text_candidate'}:
        for candidate in ('utf-8-sig','utf-8','utf-16','gb18030','big5'):
            try:data.decode(candidate);encoding=candidate;break
            except (UnicodeDecodeError,LookupError):pass
    return {'file_type':kind,'dimensions':dimensions,'encoding_candidate':encoding,'signature_hex':data[:16].hex()}

def extract_pak(args):
    archive_path=Path(args.archive)
    if not archive_path.is_absolute():archive_path=ROOT/archive_path
    archive_path=archive_path.resolve(strict=True)
    pack=read_pack_index(archive_path);entries=pack['entries']
    listing_path=Path(args.listing).resolve(strict=True) if args.listing else None
    listing_map,listing_status=validated_listing_map(archive_path,entries,listing_path)
    archive_hash=sha256_file(archive_path)
    output_root=(ROOT/'generated'/'extracted'/f'{archive_path.stem}-{archive_hash[:12]}').resolve()
    allowed_root=(ROOT/'generated'/'extracted').resolve()
    if allowed_root not in output_root.parents:
        raise ValueError('Extraction output escaped generated/extracted.')
    if args.write_payloads:output_root.mkdir(parents=True,exist_ok=True)
    selected=[]
    requested={value.lower().removeprefix('0x').zfill(8) for value in args.entry_id}
    for entry in entries:
        if requested and entry['id_hex'] not in requested:continue
        selected.append(entry)
        if args.max_entries is not None and len(selected)>=args.max_entries:break
    records=[]
    with archive_path.open('rb') as source:
        for entry in selected:
            record={key:value for key,value in entry.items() if key not in {'id','packed_method_and_size','method'}}
            record.update({
                'method_hex':f"0x{entry['method']:08x}",'packed_method_and_size_hex':f"0x{entry['packed_method_and_size']:08x}",
                'archive_path':rel(archive_path),'archive_sha256':archive_hash,
                'archive_locator':f"index:{entry['index']};offset:{entry['offset']};stored:{entry['stored_size']}",
                'evidence_class':'RAW_CLIENT' if str(archive_path).lower().startswith(str((ROOT/'client').resolve()).lower()) else 'RAW_SERVER' if str(archive_path).lower().startswith(str((ROOT/'server').resolve()).lower()) else 'UNKNOWN',
            })
            listing_fields=listing_map.get(entry['id'])
            internal_path=listing_fields['FileName'] if listing_fields else None
            record['internal_path']=internal_path
            if entry['fragment_flag']:
                record.update(status='unsupported_fragment',reason='Fragment payload subformat is UNKNOWN and was not extracted.');records.append(record);continue
            source.seek(entry['offset']);packed_data=source.read(entry['stored_size'])
            if len(packed_data)!=entry['stored_size']:
                record.update(status='error',reason='Stored payload is truncated.');records.append(record);continue
            try:
                if entry['method']==PACK_METHOD_NONE:
                    output=packed_data
                    if len(output)!=entry['expanded_size']:raise ValueError('Stored and expanded sizes differ for method NONE.')
                elif entry['method']==PACK_METHOD_UCL_NRV2B_SAFE_8:
                    output=nrv2b_decompress_safe_8(packed_data,entry['expanded_size'])
                else:
                    record.update(status='unsupported_method',reason='Method is not mapped by engine evidence.');records.append(record);continue
            except (NRVDecodeError,ValueError) as error:
                record.update(status='decode_error',reason=str(error));records.append(record);continue
            record.update(status='validated',output_size=len(output),output_sha256=hashlib.sha256(output).hexdigest(),**payload_metadata(output,internal_path))
            if args.write_payloads:
                relative_output=safe_internal_path(internal_path) if internal_path else Path('entries')/(entry['id_hex']+'.bin')
                destination=(output_root/relative_output).resolve()
                if output_root!=destination and output_root not in destination.parents:
                    raise ValueError('Archive output path escaped the extraction root.')
                if destination.exists():
                    record['payload_write_status']='existing_no_overwrite'
                else:
                    destination.parent.mkdir(parents=True,exist_ok=True);destination.write_bytes(output)
                    record['payload_write_status']='written';record['output_path']=rel(destination)
            records.append(record)
    metadata=report_metadata();slug=re.sub(r'[^a-z0-9]+','-',archive_path.stem.lower()).strip('-') or 'archive'
    payload={**metadata,'parser_version':'jxlab pak-extractor/0.1','archive_path':rel(archive_path),'archive_sha256':archive_hash,
             'listing':listing_status,'payloads_written':bool(args.write_payloads),'selection':{'entry_ids':sorted(requested),'max_entries':args.max_entries},
             'status_counts':dict(Counter(record['status'] for record in records)),'records':records}
    report_path=REPORT_DIR/f'pak-extraction-{slug}-{archive_hash[:12]}.json'
    report_path.write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding='utf-8')
    print(f"Validated {payload['status_counts'].get('validated',0):,}/{len(records):,} selected entries; report {rel(report_path)}")

def binary_string_evidence(path,needles):
    data=path.read_bytes();matches=[]
    for needle in needles:
        encoded=needle.encode('ascii');offset=data.find(encoded)
        matches.append({'text':needle,'byte_offset':offset if offset>=0 else None})
    return {'path':rel(path),'size':len(data),'sha256':hashlib.sha256(data).hexdigest(),'matches':matches}

def inspect_pak_structure(args):
    metadata=report_metadata();pak_exts={value.lower() for value in CFG['pak']['extensions']}
    known_hashes={}
    reference_path=REPORT_DIR/'pak-reference-report.json'
    if reference_path.exists():
        reference=json.loads(reference_path.read_text(encoding='utf-8'))
        known_hashes={row['path']:row.get('sha256') for row in reference.get('archives',[])}
    archives=[]
    for source_id,base in source_roots():
        for path in iter_files(base):
            if path.suffix.lower() not in pak_exts:continue
            layout=inspect_pack_layout(path)
            archives.append({'source_root':source_id,'path':rel(path),'sha256_from_pak_reference_report':known_hashes.get(rel(path)),**layout})
    archives.sort(key=lambda row:row['path'].lower())
    binary_evidence=[]
    pdb_path=ROOT/'server/gameserver/engined.pdb'
    dll_path=ROOT/'server/gameserver/engine.dll'
    if pdb_path.exists():
        binary_evidence.append(binary_string_evidence(pdb_path,[
            '.\\File\\XPackFile.cpp','XPackIndexInfo','XPACK_METHOD_NONE','XPACK_METHOD_UCL',
            '_ucl_nrv2b_decompress_safe_8','_ucl_nrv2d_decompress_safe_8','_ucl_nrv2e_decompress_safe_8',
        ]))
    if dll_path.exists():
        binary_evidence.append(binary_string_evidence(dll_path,['UCL real-time data compression library.','CreatePackFileShell']))
    statuses=Counter(row['status'] for row in archives);methods=Counter();fragment_flags=Counter()
    for row in archives:
        for method,count in row.get('method_nibble_counts',{}).items():methods[method]+=count
        for flag,count in row.get('fragment_flag_counts',{}).items():fragment_flags[flag]+=count
    payload={**metadata,'parser_version':'jxlab pak-structure/0.2','pak_payload_extracted':False,
             'field_semantics_evidence':{
                 'stored_size_mask':'0x07ffffff','fragment_flag':'0x10000000','method_mask':'0xf0000000',
                 'ucl_method_value':'0x20000000','ucl_decoder':'ucl_nrv2b_decompress_safe_8',
                 'evidence':'server/gameserver/engined.dll XPackFile::ReadElemFile and XPackFile::ExtractRead disassembly; matched engined.pdb symbols',
             },
             'status_counts':dict(statuses),'method_nibble_counts':dict(methods),
             'fragment_flag_counts':dict(fragment_flags),'binary_symbol_evidence':binary_evidence,'archives':archives}
    (REPORT_DIR/'pak-structure-report.json').write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding='utf-8')
    lines=['# PAK Structure Report','',*markdown_metadata(metadata),'- Parser version: `jxlab pak-structure/0.2`',
           '- Archive payload extracted: **False**','',f'- Archives inspected: **{len(archives):,}**','', '## Layout statuses','']
    lines += [f'- `{status}`: {count:,}' for status,count in sorted(statuses.items())]
    lines += ['','## Observed method nibbles','']+[f'- `{method}`: {count:,}' for method,count in sorted(methods.items())]
    lines += ['','## Fragment flag','']+[f'- `{flag}`: {count:,}' for flag,count in sorted(fragment_flags.items())]
    lines += ['','## Variant archives','']
    variants=[row for row in archives if row['status']!='standard_index_layout']
    lines += [f"- `{row['path']}`: {row['status']}; tail {row.get('actual_tail_bytes')} vs expected {row.get('expected_index_bytes')} bytes" for row in variants] or ['- None.']
    lines += ['','## Evidence boundary','',
              '- The 16-byte index, 27-bit stored-size mask, fragment flag, and high-nibble method mask are confirmed by `XPackFile::ReadElemFile` disassembly.',
              '- Method `0x20000000` maps to `ucl_nrv2b_decompress_safe_8` in `XPackFile::ExtractRead`; output is accepted only when the decoded length equals the index expanded size.',
              '- Variant archives are recorded and not force-parsed.']
    (REPORT_DIR/'pak-structure-report.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(f'Inspected {len(archives):,} archives: '+', '.join(f'{status}={count}' for status,count in sorted(statuses.items())))

def bootstrap(args):
    inventory(args);find_pak_refs(args);text_candidates(args);print('Bootstrap reports complete.')

def main():
    ap=argparse.ArgumentParser(description='JX Source Lab read-only utilities');sub=ap.add_subparsers(dest='command',required=True)
    p=sub.add_parser('inventory');p.add_argument('--hash',action='store_true');p.set_defaults(func=inventory)
    p=sub.add_parser('find-pak-refs');p.add_argument('--hash',action='store_true');p.set_defaults(func=find_pak_refs)
    p=sub.add_parser('text-candidates');p.set_defaults(func=text_candidates,hash=False)
    p=sub.add_parser('bootstrap');p.add_argument('--hash',action='store_true');p.set_defaults(func=bootstrap)
    p=sub.add_parser('parse-task-catalog');p.set_defaults(func=parse_task_catalog)
    p=sub.add_parser('inspect-task-publish-index');p.set_defaults(func=inspect_task_publish_index)
    p=sub.add_parser('inspect-pak-structure');p.set_defaults(func=inspect_pak_structure)
    p=sub.add_parser('extract-pak');p.add_argument('archive');p.add_argument('--listing');p.add_argument('--entry-id',action='append',default=[]);p.add_argument('--max-entries',type=int);p.add_argument('--write-payloads',action='store_true');p.set_defaults(func=extract_pak)
    a=ap.parse_args();a.func(a)
if __name__=='__main__':main()
