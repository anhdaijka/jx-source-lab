#!/usr/bin/env python3
"""Deterministic evidence-corpus builders for JX Source Lab.

Raw inputs are opened read-only. Outputs contain normalized records plus exact
source hashes and locators; no story interpretation is performed here.
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import re
import struct
import unicodedata
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

import jxlab

ROOT=Path(__file__).resolve().parents[1]
RECORD_ROOT=ROOT/'generated'/'records'
REPORT_ROOT=ROOT/'generated'/'reports'
PARSER_VERSION='jxcorpus/0.1'

def utc_now():return datetime.now(timezone.utc).isoformat()

def sha256_bytes(data):return hashlib.sha256(data).hexdigest()

def write_jsonl(path,records):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('w',encoding='utf-8',newline='\n') as output:
        for record in records:output.write(json.dumps(record,ensure_ascii=False,separators=(',',':'))+'\n')

def source_record(path,locator,evidence_class='RAW_SERVER',encoding='utf-8-sig',notes='',sha256=None):
    return {
        'source_id':'server-primary' if evidence_class=='RAW_SERVER' else 'client-primary',
        'evidence_class':evidence_class,'path':jxlab.rel(path),
        'sha256':sha256 or jxlab.sha256_file(path),'edition':None,'encoding':encoding,
        'locator':locator,'notes':notes,
    }

def parse_tsv(path,memo_rows=0,allow_blank_header=False,encoding='utf-8-sig'):
    data=path.read_bytes()
    if b'\x00' in data[:4096]:raise ValueError('NUL/binary data in text table')
    text=data.decode(encoding)
    # These legacy tables use TAB as the only structural delimiter. Quote
    # characters occur inside literal dialogue/name fields and are not CSV
    # framing, so RFC-style quote handling would merge unrelated lines.
    rows=list(csv.reader(io.StringIO(text),delimiter='\t',quoting=csv.QUOTE_NONE))
    if not rows:raise ValueError('empty table')
    raw_header=rows[0]
    header=[]
    for index,name in enumerate(raw_header,1):
        if name:header.append(name)
        elif allow_blank_header:header.append(f'__column_{index}')
        else:raise ValueError(f'blank header column {index}')
    records=[];malformed=[];start=1+memo_rows
    for line_number,row in enumerate(rows[start:],start+1):
        if not any(row):continue
        fields=list(row)
        if len(fields)!=len(header):
            malformed.append({'line':line_number,'columns':len(fields),'expected':len(header),
                              'handling':'padded_trailing_empty' if len(fields)<len(header) else 'preserved_extra_columns'})
        if len(fields)<len(header):fields.extend(['']*(len(header)-len(fields)))
        record=dict(zip(header,fields[:len(header)]))
        for extra_index,value in enumerate(fields[len(header):],1):record[f'__extra_{extra_index}']=value
        records.append((line_number,record))
    return {'encoding':encoding,'header':header,'memo_rows':rows[1:start],
            'records':records,'malformed':malformed,'sha256':sha256_bytes(data)}

def normalize_label(value):
    return unicodedata.normalize('NFC',value).strip()

def pack_entry_source(archive_path,archive_hash,entry,output_hash,notes=''):
    return source_record(
        archive_path,
        f"index:{entry['index']};id:{entry['id_hex']};offset:{entry['offset']};stored:{entry['stored_size']};expanded:{entry['expanded_size']};output_sha256:{output_hash}",
        'RAW_CLIENT','binary PACK + decoded UTF-8 XML',notes,archive_hash,
    )

def decode_pack_entry(source,entry):
    if entry['fragment_flag']:raise ValueError('fragment entry unsupported')
    source.seek(entry['offset']);packed=source.read(entry['stored_size'])
    if len(packed)!=entry['stored_size']:raise ValueError('truncated stored payload')
    if entry['method']==jxlab.PACK_METHOD_NONE:
        if len(packed)!=entry['expanded_size']:raise ValueError('NONE size mismatch')
        return packed
    if entry['method']==jxlab.PACK_METHOD_UCL_NRV2B_SAFE_8:
        return jxlab.nrv2b_decompress_safe_8(packed,entry['expanded_size'])
    raise ValueError(f"unsupported method 0x{entry['method']:08x}")

def task_ranges():
    path=ROOT/'server/gameserver/setting/task/task_def.txt';parsed=parse_tsv(path,memo_rows=1)
    ranges=[]
    for line,fields in parsed['records']:
        ranges.append((int(fields['TASK_ID_FIRST']),int(fields['TASK_ID_LAST']),fields,line))
    return path,parsed,ranges

def task_classification(task_id,ranges):
    numeric=int(task_id,16)
    matches=[(fields,line) for first,last,fields,line in ranges if first<=numeric<=last]
    if len(matches)!=1:return {'class':'UNKNOWN','reason':f'range_matches:{len(matches)}'}
    fields,line=matches[0];label=normalize_label(fields['TASK_NAME'])
    classification='main' if 'chính tuyến' in label.casefold() else 'configured_non_main'
    return {'class':classification,'configured_type':fields['TASK_TYPE'],'configured_label':label,
            'configured_description':normalize_label(fields['TASK_DESC']),'range_locator':f'line:{line}'}

def grid_parameters(grid):
    result=[];parameter=grid.find('Parameter')
    if parameter is None:return result
    for child in parameter:
        result.append({'type':child.tag,'values':[(value.text or '') for value in child.findall('.//Value')]})
    return result

def first_parameter(parameters,kind):
    for parameter in parameters:
        if parameter['type']==kind and parameter['values']:return parameter['values'][0]
    return None

def build_task_archive_corpus():
    archive=ROOT/'client/pak/task_publish.pak';archive_hash=jxlab.sha256_file(archive)
    pack=jxlab.read_pack_index(archive);range_path,range_parsed,ranges=task_ranges()
    tasks=[];subs=[];dialogues=[];edges=[];entry_reports=[];roots=[]
    with archive.open('rb') as source:
        for entry in pack['entries']:
            try:decoded=decode_pack_entry(source,entry)
            except Exception as error:
                entry_reports.append({'id_hex':entry['id_hex'],'status':'decode_error','error':str(error)});continue
            output_hash=sha256_bytes(decoded)
            try:root=ET.fromstring(decoded)
            except Exception as error:
                entry_reports.append({'id_hex':entry['id_hex'],'status':'non_task_payload','output_sha256':output_hash,'reason':str(error),'signature_hex':decoded[:16].hex()});continue
            if root.tag not in {'Task','Sub'}:
                entry_reports.append({'id_hex':entry['id_hex'],'status':'non_task_xml','root_tag':root.tag,'output_sha256':output_hash});continue
            root_id=root.attrib.get('id','').upper();logical_key=f"{root.tag.lower()}:{root_id}"
            root_key=f'{logical_key}:entry:{entry["id_hex"]}' if root.tag=='Task' else logical_key
            provenance=[pack_entry_source(archive,archive_hash,entry,output_hash,'Decoded with engine-confirmed UCL NRV2B safe_8 mapping.')]
            record={
                'schema_version':'1.0','parser_version':PARSER_VERSION,'record_kind':root.tag.lower(),
                'record_key':root_key,'logical_key':logical_key,'task_id':root_id,'task_id_decimal':int(root_id,16),
                'name':root.attrib.get('name',''),'description':root.attrib.get('describe',''),
                'source_records':provenance,
            }
            if root.tag=='Task':
                record['classification']=task_classification(root_id,ranges);tasks.append(record)
            else:subs.append(record)
            roots.append((root,root_key,root_id,provenance,entry))
            dialog=root.find('./Attribute/Dialog')
            if dialog is not None:
                for phase in ('Start','Procedure','Error','Prize','End'):
                    text=(dialog.findtext(phase) or '').strip()
                    if not text:continue
                    dialogues.append({
                        'schema_version':'1.0','parser_version':PARSER_VERSION,'record_kind':'task_dialogue',
                        'dialogue_id':f"{root_key}:{phase.lower()}",'owner_key':root_key,'phase':phase.lower(),
                        'language':'vi','text':text,'source_records':provenance,
                    })
    task_keys={record['task_id'] for record in tasks};sub_keys={record['task_id'] for record in subs}
    for root,root_key,root_id,provenance,entry in roots:
        if root.tag=='Task':
            for ordinal,child in enumerate(root.findall('./Managed/Sub'),1):
                target=(child.attrib.get('refer') or child.attrib.get('id') or '').upper()
                edges.append({'edge_id':f'{root_key}:manages:{ordinal}','source_key':root_key,'target_key':f'sub:{target}',
                              'relation':'manages_sub','resolution':'resolved' if target in sub_keys else 'unresolved',
                              'source_records':provenance})
        for ordinal,grid in enumerate(root.iter('Grid'),1):
            function=(grid.findtext('Function') or '').strip();parameters=grid_parameters(grid)
            relation=None
            if function=='TaskAct:AskAccept':relation='accepts_next_sub'
            elif function=='TaskCond:IsRefFinished':relation='requires_finished_sub'
            if relation:
                target=(first_parameter(parameters,'referid') or '').upper()
                edges.append({'edge_id':f'{root_key}:{relation}:{ordinal}','source_key':root_key,'target_key':f'sub:{target}',
                              'relation':relation,'resolution':'resolved' if target in sub_keys else 'unresolved',
                              'function':function,'source_records':provenance})
            for parameter in parameters:
                if parameter['type'] not in {'dialognpc','fightnpc'}:continue
                for value in parameter['values']:
                    if value.isdigit():
                        edges.append({'edge_id':f'{root_key}:{parameter["type"]}:{ordinal}:{value}',
                                      'source_key':root_key,'target_key':f'npc:{value}','relation':f'{parameter["type"]}_reference',
                                      'resolution':'pending_npc_corpus','function':function,'source_records':provenance})
        combined='\n'.join(filter(None,[root.attrib.get('describe','')]+[(node.text or '') for node in root.findall('./Attribute/Dialog/*')]))
        for ordinal,npc_id in enumerate(re.findall(r'<(?:npc|npcpos)=(\d+)',combined),1):
            edges.append({'edge_id':f'{root_key}:markup_npc:{ordinal}:{npc_id}','source_key':root_key,'target_key':f'npc:{npc_id}',
                          'relation':'dialogue_markup_npc_reference','resolution':'pending_npc_corpus','source_records':provenance})
        for ordinal,map_id in enumerate(re.findall(r'<pos=[^,>]+,(\d+),',combined),1):
            edges.append({'edge_id':f'{root_key}:markup_map:{ordinal}:{map_id}','source_key':root_key,'target_key':f'map:{map_id}',
                          'relation':'description_markup_map_reference','resolution':'pending_map_corpus','source_records':provenance})
    outputs={
        'tasks':RECORD_ROOT/'tasks'/'task-archive-records.jsonl','subtasks':RECORD_ROOT/'tasks'/'subtask-archive-records.jsonl',
        'task_dialogues':RECORD_ROOT/'dialogue'/'task-dialogue-records.jsonl','task_edges':RECORD_ROOT/'edges'/'task-reference-edges.jsonl',
    }
    write_jsonl(outputs['tasks'],tasks);write_jsonl(outputs['subtasks'],subs);write_jsonl(outputs['task_dialogues'],dialogues);write_jsonl(outputs['task_edges'],edges)
    duplicate_task_ids={key:count for key,count in Counter(record['task_id'] for record in tasks).items() if count>1}
    return {'outputs':{key:jxlab.rel(path) for key,path in outputs.items()},'counts':{'tasks':len(tasks),'subtasks':len(subs),'task_dialogues':len(dialogues),'task_edges':len(edges)},
            'archive_path':jxlab.rel(archive),'archive_sha256':archive_hash,'entry_status_counts':dict(Counter(row['status'] for row in entry_reports)),
            'entry_exceptions':entry_reports,'duplicate_task_ids':duplicate_task_ids,
            'task_range_path':jxlab.rel(range_path),'task_range_sha256':range_parsed['sha256']}

def build_npc_dialogue_corpus():
    npc_path=ROOT/'server/gameserver/setting/npc/npc.txt';dialogue_path=ROOT/'server/gameserver/setting/npc/dialognpc.txt'
    npc_table=parse_tsv(npc_path);dialogue_table=parse_tsv(dialogue_path)
    npcs=[];dialogues=[];edges=[];by_class=defaultdict(list)
    for line,fields in npc_table['records']:
        npc_id=fields['Id'];key=f'npc:{npc_id}';by_class[fields['ClassName']].append(key)
        npcs.append({'schema_version':'1.0','parser_version':PARSER_VERSION,'record_kind':'npc','record_key':key,
                     'npc_id':npc_id,'name':fields['Name'],'description':fields['Desc'],'title':fields['Title'],
                     'class_name':fields['ClassName'],'camp':fields['Camp'],'kind':fields['Kind'],'raw_fields':fields,
                     'source_records':[source_record(npc_path,f'line:{line}',sha256=npc_table['sha256'])]})
    npc_keys={record['record_key'] for record in npcs}
    for line,fields in dialogue_table['records']:
        key=f"dialognpc:{fields['Id']}";class_targets=by_class.get(fields['ClassName'],[])
        dialogues.append({'schema_version':'1.0','parser_version':PARSER_VERSION,'record_kind':'dialognpc_literal',
                          'dialogue_id':key,'npc_class_name':fields['ClassName'],'map_id':fields['MapId'] or '0',
                          'map_name':fields['Map'],'language':'vi','text':fields['Msg'],
                          'options':[fields[f'Option{i}'] for i in range(1,13) if fields[f'Option{i}']],
                          'npc_class_resolution':'unique' if len(class_targets)==1 else 'ambiguous' if class_targets else 'unresolved',
                          'npc_class_candidates':class_targets,'source_records':[source_record(dialogue_path,f'line:{line}',sha256=dialogue_table['sha256'])]})
        edges.append({'edge_id':f'{key}:map','source_key':key,'target_key':f"map:{fields['MapId'] or '0'}",'relation':'dialogue_map_reference','resolution':'pending_map_corpus',
                      'source_records':[source_record(dialogue_path,f'line:{line}',sha256=dialogue_table['sha256'])]})
        for ordinal,target in enumerate(class_targets,1):
            edges.append({'edge_id':f'{key}:npc-class:{ordinal}','source_key':key,'target_key':target,'relation':'npc_class_name_match',
                          'resolution':'unique' if len(class_targets)==1 else 'ambiguous',
                          'source_records':[source_record(dialogue_path,f'line:{line}',sha256=dialogue_table['sha256'])]})
    write_jsonl(RECORD_ROOT/'npcs'/'npc-records.jsonl',npcs);write_jsonl(RECORD_ROOT/'dialogue'/'dialognpc-records.jsonl',dialogues);write_jsonl(RECORD_ROOT/'edges'/'dialogue-reference-edges.jsonl',edges)
    return {'counts':{'npcs':len(npcs),'dialognpc_dialogues':len(dialogues),'dialogue_edges':len(edges)},
            'malformed':{'npc':npc_table['malformed'],'dialognpc':dialogue_table['malformed']},'npc_keys':npc_keys}

def build_localization_corpus():
    records=[];inputs=[]
    base=ROOT/'server/gameserver/pak/l10n/vi-vi'
    for name in ('stringtable_core.txt','stringtable_gccore.txt','stringtable_log.txt'):
        path=base/name;table=parse_tsv(path);inputs.append({'path':jxlab.rel(path),'sha256':table['sha256'],'malformed':table['malformed']})
        family=path.stem.removeprefix('stringtable_')
        for line,fields in table['records']:
            records.append({'schema_version':'1.0','parser_version':PARSER_VERSION,'record_kind':'localization',
                            'localization_id':f"vi-vi:{family}:{fields['key']}",'language':'vi-vi','family':family,
                            'key':fields['key'],'value':fields['value'],'source_records':[source_record(path,f'line:{line}',sha256=table['sha256'])]})
    write_jsonl(RECORD_ROOT/'dialogue'/'localization-records.jsonl',records)
    return {'counts':{'localization':len(records)},'inputs':inputs}

def build_faction_skill_corpus():
    faction_path=ROOT/'server/gameserver/setting/faction/faction.xml';skill_path=ROOT/'server/gameserver/setting/fightskill/skill.txt'
    faction_hash=jxlab.sha256_file(faction_path);root=ET.parse(faction_path).getroot();factions=[];routes=[];xml_edges=[]
    route_keys=set()
    for faction in root.findall('faction'):
        fid=faction.attrib['id'];fkey=f'faction:{fid}'
        factions.append({'schema_version':'1.0','parser_version':PARSER_VERSION,'record_kind':'faction','record_key':fkey,
                         'faction_id':fid,'name':normalize_label(faction.attrib.get('name','')),'raw_attributes':faction.attrib,
                         'source_records':[source_record(faction_path,f"xpath:/factions/faction[@id='{fid}']",sha256=faction_hash)]})
        for route in faction.findall('route'):
            rid=route.attrib['id'];rkey=f'{fkey}:route:{rid}';route_keys.add((fid,rid))
            routes.append({'schema_version':'1.0','parser_version':PARSER_VERSION,'record_kind':'route','record_key':rkey,
                           'route_id':{'faction_id':fid,'route_id':rid},'name':normalize_label(route.attrib.get('name','')),
                           'description':normalize_label(route.attrib.get('desc','')),'raw_attributes':route.attrib,
                           'source_records':[source_record(faction_path,f"xpath:/factions/faction[@id='{fid}']/route[@id='{rid}']",sha256=faction_hash)]})
            for ordinal,skill in enumerate(route.findall('skill'),1):
                sid=skill.attrib['id'];xml_edges.append({'edge_id':f'{rkey}:skill:{ordinal}:{sid}','source_key':rkey,'target_key':f'skill:{sid}',
                                                        'relation':'route_skill_reference','resolution':'pending_skill_corpus',
                                                        'source_records':[source_record(faction_path,f"xpath:/factions/faction[@id='{fid}']/route[@id='{rid}']/skill[{ordinal}]",sha256=faction_hash)]})
    table=parse_tsv(skill_path,allow_blank_header=True);skills=[];by_id=defaultdict(list);skill_edges=[]
    for line,fields in table['records']:
        sid=fields['SkillId'];record_key=f'skill:{sid}:line:{line}';by_id[sid].append(record_key)
        skills.append({'schema_version':'1.0','parser_version':PARSER_VERSION,'record_kind':'skill','record_key':record_key,
                       'skill_id':sid,'name':fields['SkillName'],'property':fields['Property'],'description':fields['SkillDesc'],
                       'faction_limit':fields['FactionLimit'],'route_limit':fields['RouteLimit'],'class_name':fields['ClassName'],
                       'raw_fields':fields,'source_records':[source_record(skill_path,f'line:{line}',sha256=table['sha256'])]})
        if fields['FactionLimit'].isdigit() and fields['RouteLimit'].isdigit() and int(fields['FactionLimit'])>0 and int(fields['RouteLimit'])>0:
            pair=(fields['FactionLimit'],fields['RouteLimit'])
            skill_edges.append({'edge_id':f'{record_key}:route','source_key':record_key,'target_key':f'faction:{pair[0]}:route:{pair[1]}',
                                'relation':'skill_faction_route_limit','resolution':'resolved' if pair in route_keys else 'unresolved',
                                'source_records':[source_record(skill_path,f'line:{line}',sha256=table['sha256'])]})
    for edge in xml_edges:
        candidates=by_id.get(edge['target_key'].split(':',1)[1],[])
        edge['target_candidates']=candidates;edge['resolution']='resolved' if len(candidates)==1 else 'ambiguous' if candidates else 'unresolved'
    write_jsonl(RECORD_ROOT/'sects'/'faction-records.jsonl',factions);write_jsonl(RECORD_ROOT/'sects'/'route-records.jsonl',routes)
    write_jsonl(RECORD_ROOT/'skills'/'skill-records.jsonl',skills);write_jsonl(RECORD_ROOT/'edges'/'faction-skill-reference-edges.jsonl',xml_edges+skill_edges)
    return {'counts':{'factions':len(factions),'routes':len(routes),'skills':len(skills),'faction_skill_edges':len(xml_edges)+len(skill_edges)},
            'duplicate_skill_ids':{sid:keys for sid,keys in by_id.items() if len(keys)>1},'malformed':table['malformed']}

def build_item_corpus():
    base=ROOT/'server/gameserver/setting/item/001';records=[];inputs=[];skipped=[];identity=defaultdict(list)
    required={'Name','Genre','DetailType','ParticularType','Level'}
    for path in sorted(base.rglob('*.txt'),key=lambda value:value.as_posix().lower()):
        try:table=parse_tsv(path,allow_blank_header=True)
        except (UnicodeDecodeError,ValueError) as error:
            skipped.append({'path':jxlab.rel(path),'reason':str(error)});continue
        if not required.issubset(table['header']):
            skipped.append({'path':jxlab.rel(path),'reason':'not an item definition table'});continue
        emitted=0;family=path.relative_to(base).as_posix()
        for line,fields in table['records']:
            if not fields['Name']:
                skipped.append({'path':jxlab.rel(path),'line':line,'reason':'blank item name'});continue
            key=f'item:{family}:line:{line}';item_id={name:fields[name] for name in ('Genre','DetailType','ParticularType','Level')}
            identity_key=tuple(item_id.values());identity[identity_key].append(key)
            records.append({'schema_version':'1.0','parser_version':PARSER_VERSION,'record_kind':'item','record_key':key,
                            'item_id':item_id,'family':family,'name':fields['Name'],'kind':fields.get('Kind',''),
                            'description':fields.get('Intro',''),'class_name':fields.get('ClassName',''),'icon':fields.get('Icon',''),
                            'source_row_sha256':sha256_bytes(json.dumps(fields,ensure_ascii=False,separators=(',',':')).encode('utf-8')),
                            'source_records':[source_record(path,f'line:{line}',sha256=table['sha256'])]});emitted+=1
        inputs.append({'path':jxlab.rel(path),'sha256':table['sha256'],'records':emitted,'malformed':table['malformed']})
    write_jsonl(RECORD_ROOT/'items'/'item-records.jsonl',records)
    return {'counts':{'items':len(records),'item_definition_files':len(inputs),'skipped_item_files_or_rows':len(skipped)},
            'inputs':inputs,'skipped':skipped,'duplicate_composite_identity_count':sum(1 for keys in identity.values() if len(keys)>1)}

def build_map_feature_corpus():
    map_path=ROOT/'server/gameserver/setting/map/maplist.txt';transmit_path=ROOT/'server/gameserver/setting/map/transmit.txt'
    maps_table=parse_tsv(map_path,memo_rows=1);transmit_table=parse_tsv(transmit_path)
    maps=[];features=[];edges=[];by_info=defaultdict(list);map_ids=set()
    for line,fields in maps_table['records']:
        mid=fields['TemplateId'];map_ids.add(mid);key=f'map:{mid}'
        for join in {fields['InfoFile'].casefold(),fields['ResName'].casefold()}-{''}:by_info[join].append(key)
        maps.append({'schema_version':'1.0','parser_version':PARSER_VERSION,'record_kind':'map','record_key':key,
                     'location_id':mid,'name':fields['MapName'],'resource_name':fields['ResName'],'info_file':fields['InfoFile'],
                     'map_type':fields['MapType'],'map_level':fields['MapLevel'],'domain':fields['Domain'],'raw_fields':fields,
                     'source_records':[source_record(map_path,f'line:{line}',sha256=maps_table['sha256'])]})
    for line,fields in transmit_table['records']:
        key=f'map-transfer:line:{line}';provenance=[source_record(transmit_path,f'line:{line}',sha256=transmit_table['sha256'])]
        runtime_path=ROOT/'server/gameserver/script/map/map.lua'
        provenance.append(source_record(runtime_path,'line:90-113',notes='Runtime loader constructs directed traffic and trap transfers from transmit.txt.'))
        normalized_from=[int(fields['FromPosX'])/32,int(fields['FromPosY'])/32]
        normalized_to=[int(fields['ToPosX'])/32,int(fields['ToPosY'])/32]
        features.append({'schema_version':'1.0','parser_version':PARSER_VERSION,'record_kind':'map_transfer','record_key':key,
                         'feature_id':key,'name':fields['Name'],'from_map_id':fields['FromMapId'],'to_map_id':fields['ToMapId'],
                         'from_position':[fields['FromPosX'],fields['FromPosY']],'to_position':[fields['ToPosX'],fields['ToPosY']],
                         'runtime_position_divisor':32,'runtime_from_position':normalized_from,'runtime_to_position':normalized_to,
                         'transfer_type':fields['Type'],'to_fight_state':fields['ToFightState'],'be_protected':fields['BeProtected'],
                         'raw_fields':fields,'source_records':provenance})
        for relation,mid in (('from_map',fields['FromMapId']),('to_map',fields['ToMapId'])):
            edges.append({'edge_id':f'{key}:{relation}','source_key':key,'target_key':f'map:{mid}','relation':relation,
                          'resolution':'resolved' if mid in map_ids else 'unresolved','source_records':provenance})
    feature_tables=[
        ('map_level_membership',ROOT/'server/gameserver/setting/map/mapid_level.txt','gb18030',ROOT/'server/gameserver/script/map/map.lua','line:90-113'),
        ('map_transmit_catalog',ROOT/'server/gameserver/setting/map/chuansongmapinfo.txt','utf-8-sig',ROOT/'server/gameserver/script/map/map.lua','line:184'),
        ('map_protection',ROOT/'server/gameserver/setting/map/map_protected.txt','utf-8-sig',ROOT/'server/gameserver/script/map/map.lua','line:803'),
        ('travel_station',ROOT/'server/gameserver/setting/map/station.txt','utf-8-sig',ROOT/'server/gameserver/script/npc/chefu.lua','line:14'),
        ('revive_position',ROOT/'server/gameserver/setting/map/revivepos.txt','utf-8-sig',ROOT/'server/gameserver/script/npc/wupinbaoguanren.lua','line:16'),
    ]
    feature_family_counts=Counter()
    for family,path,encoding,runtime_path,runtime_locator in feature_tables:
        table=parse_tsv(path,encoding=encoding);runtime_note=f'Runtime loader evidence for {path.name}.'
        for line,fields in table['records']:
            provenance=[source_record(path,f'line:{line}',encoding=encoding,sha256=table['sha256']),
                        source_record(runtime_path,runtime_locator,notes=runtime_note)]
            if family=='map_level_membership':
                for column,value in fields.items():
                    if not column.startswith('MapId') or not value:continue
                    key=f'{family}:{fields["MapType"]}:{column}:{value}'
                    features.append({'schema_version':'1.0','parser_version':PARSER_VERSION,'record_kind':family,'record_key':key,
                                     'feature_id':key,'category':fields['MapType'],'map_id':value,'source_records':provenance})
                    edges.append({'edge_id':f'{key}:map','source_key':key,'target_key':f'map:{value}','relation':'map_category_membership',
                                  'resolution':'resolved' if value in map_ids else 'unresolved','source_records':provenance});feature_family_counts[family]+=1
                continue
            if family=='map_transmit_catalog':map_id=fields['MAP_ID'];name=fields['MAP_INFO']
            else:map_id=fields['MapId'];name=fields.get('MapName') or fields.get('Desc(程序不读)','')
            key=f'{family}:line:{line}'
            record={'schema_version':'1.0','parser_version':PARSER_VERSION,'record_kind':family,'record_key':key,
                    'feature_id':key,'name':name,'map_id':map_id,'raw_fields':fields,'source_records':provenance}
            if family=='revive_position':
                record['point_type']=fields['Type'];record['position']=[fields['PosX'],fields['PosY']]
                record['description_usage']='raw_note_not_read_by_runtime'
            elif family=='travel_station':record['station_type']=fields['MapType']
            elif family=='map_protection':record['be_protected']=fields['BeProtected']
            elif family=='map_transmit_catalog':record['map_class']=fields['MAP_CLASS'];record['position']=[fields['MAP_X'],fields['MAP_Y']]
            features.append(record);feature_family_counts[family]+=1
            edges.append({'edge_id':f'{key}:map','source_key':key,'target_key':f'map:{map_id}','relation':f'{family}_map_reference',
                          'resolution':'resolved' if map_id in map_ids else 'unresolved','source_records':provenance})
    skipped=[];spawn_count=0
    info_root=ROOT/'server/gameserver/setting/map/map_info'
    for path in sorted(info_root.rglob('info.txt'),key=lambda value:value.as_posix().lower()):
        try:table=parse_tsv(path,allow_blank_header=True)
        except (UnicodeDecodeError,ValueError) as error:
            skipped.append({'path':jxlab.rel(path),'reason':str(error)});continue
        required={'NpcName','Class','NpcTemplateId','XPos','YPos'}
        if not required.issubset(table['header']):
            skipped.append({'path':jxlab.rel(path),'reason':'unrecognized map info schema'});continue
        directory_key=path.parent.name.casefold();map_candidates=by_info.get(directory_key,[])
        for line,fields in table['records']:
            key=f'map-spawn:{path.parent.name}:line:{line}';provenance=[source_record(path,f'line:{line}',sha256=table['sha256'])]
            features.append({'schema_version':'1.0','parser_version':PARSER_VERSION,'record_kind':'map_spawn','record_key':key,
                             'feature_id':key,'name':fields['NpcName'],'spawn_class':fields['Class'],'npc_template_id':fields['NpcTemplateId'],
                             'map_candidates':map_candidates,'position':[fields['XPos'],fields['YPos']],'raw_fields':fields,'source_records':provenance});spawn_count+=1
            if fields['Class']=='0' and fields['NpcTemplateId']:
                edges.append({'edge_id':f'{key}:npc','source_key':key,'target_key':f"npc:{fields['NpcTemplateId']}",'relation':'spawn_npc_template',
                              'resolution':'pending_npc_corpus','source_records':provenance})
            for ordinal,target in enumerate(map_candidates,1):
                edges.append({'edge_id':f'{key}:map:{ordinal}','source_key':key,'target_key':target,'relation':'spawn_map_directory_match',
                              'resolution':'resolved' if len(map_candidates)==1 else 'ambiguous','source_records':provenance})
    write_jsonl(RECORD_ROOT/'locations'/'location-records.jsonl',maps);write_jsonl(RECORD_ROOT/'features'/'feature-records.jsonl',features)
    write_jsonl(RECORD_ROOT/'edges'/'map-feature-reference-edges.jsonl',edges)
    return {'counts':{'maps':len(maps),'map_transfers':len(transmit_table['records']),'map_spawns':spawn_count,
                      **dict(feature_family_counts),'map_feature_edges':len(edges)},
            'malformed':{'maplist':maps_table['malformed'],'transmit':transmit_table['malformed']},'skipped_map_info':skipped,
            'map_ids':map_ids}

def resolve_pending_edges(npc_keys,map_ids):
    changes=Counter();unresolved=[]
    for path in sorted((RECORD_ROOT/'edges').glob('*.jsonl')):
        records=[]
        for line in path.read_text(encoding='utf-8').splitlines():
            if not line:continue
            record=json.loads(line);target=record.get('target_key','')
            if record.get('resolution')=='pending_npc_corpus':
                record['resolution']='resolved' if target in npc_keys else 'unresolved';changes[record['resolution']]+=1
            elif record.get('resolution')=='pending_map_corpus':
                record['resolution']='resolved' if target.startswith('map:') and target.split(':',1)[1] in map_ids else 'unresolved';changes[record['resolution']]+=1
            if record.get('resolution') in {'unresolved','ambiguous'}:
                unresolved.append({'edge_file':jxlab.rel(path),'edge_id':record.get('edge_id'),'source_key':record.get('source_key'),
                                   'target_key':target,'relation':record.get('relation'),'status':record.get('resolution')})
            records.append(record)
        write_jsonl(path,records)
    unresolved_path=ROOT/'research'/'unresolved-reference-ledger.json'
    unresolved_path.parent.mkdir(parents=True,exist_ok=True)
    unresolved_path.write_text(json.dumps({'schema_version':'1.0','generator':'scripts/jxcorpus.py','generated_at_utc':utc_now(),
                                           'counts':dict(Counter(row['status'] for row in unresolved)),'entries':unresolved},ensure_ascii=False,indent=2),encoding='utf-8')
    return {'resolution_changes':dict(changes),'unresolved_count':len(unresolved),'output':jxlab.rel(unresolved_path)}

def edition_comparisons():
    pairs=[
        ('task_def','server/gameserver/setting/task/task_def.txt','client/setting/task/task_def.txt'),
        ('linktask_type_select','server/gameserver/setting/task/linktask/type_select.txt','client/setting/task/linktask/type_select.txt'),
        ('linktask_killnpc','server/gameserver/setting/task/linktask/entity_killnpc.txt','client/setting/task/linktask/entity_killnpc.txt'),
        ('linktask_finditem','server/gameserver/setting/task/linktask/entity_finditem.txt','client/setting/task/linktask/entity_finditem.txt'),
        ('linktask_findequip','server/gameserver/setting/task/linktask/entity_findequip.txt','client/setting/task/linktask/entity_findequip.txt'),
        ('linktask_buyitem','server/gameserver/setting/task/linktask/entity_buyitem.txt','client/setting/task/linktask/entity_buyitem.txt'),
        ('npc','server/gameserver/setting/npc/npc.txt','client/setting/npc/npc.txt'),
        ('dialognpc','server/gameserver/setting/npc/dialognpc.txt','client/setting/npc/dialognpc.txt'),
        ('faction','server/gameserver/setting/faction/faction.xml','client/setting/faction/faction.xml'),
        ('skill','server/gameserver/setting/fightskill/skill.txt','client/setting/fightskill/skill.txt'),
        ('maplist','server/gameserver/setting/map/maplist.txt','client/setting/map/maplist.txt'),
        ('transmit','server/gameserver/setting/map/transmit.txt','client/setting/map/transmit.txt'),
        ('map_info_hanshuigudu','server/gameserver/setting/map/map_info/hanshuigudu/info.txt','client/setting/map/map_info/hanshuigudu/info.txt'),
        ('mapid_level','server/gameserver/setting/map/mapid_level.txt','client/setting/map/mapid_level.txt'),
        ('map_transmit_catalog','server/gameserver/setting/map/chuansongmapinfo.txt','client/setting/map/chuansongmapinfo.txt'),
        ('map_protected','server/gameserver/setting/map/map_protected.txt','client/setting/map/map_protected.txt'),
        ('station','server/gameserver/setting/map/station.txt','client/setting/map/station.txt'),
        ('revivepos','server/gameserver/setting/map/revivepos.txt','client/setting/map/revivepos.txt'),
        ('taskquest','server/gameserver/setting/item/001/other/taskquest.txt','client/setting/item/001/other/taskquest.txt'),
        ('scriptitem','server/gameserver/setting/item/001/other/scriptitem.txt','client/setting/item/001/other/scriptitem.txt'),
    ]
    entries=[]
    for domain,left_value,right_value in pairs:
        left=ROOT/left_value;right=ROOT/right_value
        if not left.exists() or not right.exists():
            entries.append({'domain':domain,'status':'UNKNOWN','reason':'one or both comparison paths are absent','paths':[left_value,right_value]});continue
        left_hash=jxlab.sha256_file(left);right_hash=jxlab.sha256_file(right)
        entries.append({'domain':domain,'status':'CROSS_SOURCE_CONFIRMED' if left_hash==right_hash else 'EDITION_DRIFT',
                        'server_path':left_value,'server_sha256':left_hash,'client_path':right_value,'client_sha256':right_hash,
                        'interpretation':'Byte equality/difference applies to these local unknown-build copies only.'})
    path=ROOT/'research'/'edition-drift-ledger.json';path.write_text(json.dumps({'schema_version':'1.0','generator':'scripts/jxcorpus.py','generated_at_utc':utc_now(),'entries':entries},ensure_ascii=False,indent=2),encoding='utf-8')
    return {'output':jxlab.rel(path),'counts':dict(Counter(entry['status'] for entry in entries))}

def main():
    REPORT_ROOT.mkdir(parents=True,exist_ok=True)
    report={'schema_version':'1.0','generator':'scripts/jxcorpus.py','parser_version':PARSER_VERSION,'generated_at_utc':utc_now()}
    report['task_archive']=build_task_archive_corpus()
    npc_result=build_npc_dialogue_corpus();report['npc_dialogue']={key:value for key,value in npc_result.items() if key!='npc_keys'}
    report['localization']=build_localization_corpus()
    report['faction_skill']=build_faction_skill_corpus()
    report['items']=build_item_corpus()
    map_result=build_map_feature_corpus();report['map_features']={key:value for key,value in map_result.items() if key!='map_ids'}
    report['reference_resolution']=resolve_pending_edges(npc_result['npc_keys'],map_result['map_ids'])
    report['edition_comparison']=edition_comparisons()
    output=REPORT_ROOT/'domain-corpus-report.json';output.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'report':jxlab.rel(output),'counts':{section:value.get('counts',{}) for section,value in report.items() if isinstance(value,dict)}},ensure_ascii=False,indent=2))

if __name__=='__main__':main()
