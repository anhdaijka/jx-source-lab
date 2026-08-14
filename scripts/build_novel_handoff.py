#!/usr/bin/env python3
"""Build the curated, source-only one-way handoff for kiem-the-novel."""
from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import jxlab

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'generated'/'novel-handoff'
GENERATOR='scripts/build_novel_handoff.py'
SCHEMA_VERSION='1.0'

CHARACTERS=[
 {'entity_id':'character:game-player','vi':'Người chơi','cn':None,'aliases':['game player'],'role':'Player-controlled participant in the evidenced game story; no novel-protagonist identity is assigned.','affiliations':['Nghĩa Quân'],'claim_ids':['IR004','IR011','IR021'],'arc_ids':['arc-01','arc-07','arc-12'],'lookup_names':[],'relationships':[{'target':'character:bach-thu-lam','relation':'mission authority and source of withheld parentage information','claim_ids':['IR004','IR021']},{'target':'character:biological-parents','relation':'biological child','claim_ids':['IR011','IR021']}]},
 {'entity_id':'character:bach-thu-lam','vi':'Bạch Thu Lâm','cn':'白秋琳','aliases':['Thu Di','秋姨'],'role':'Opening guide and recurring Nghĩa Quân mission authority.','affiliations':['Nghĩa Quân'],'claim_ids':['IR004','IR011','IR016','IR021'],'arc_ids':['arc-01','arc-07','arc-12'],'lookup_names':['Bạch Thu Lâm'],'relationships':[{'target':'character:game-player','relation':'caretaker/mission authority; exact kinship is not established','claim_ids':['IR004','IR021']}]},
 {'entity_id':'character:biological-parents','vi':'Cha mẹ ruột của người chơi','cn':None,'aliases':['biological parents'],'role':'Unnamed biological parents encountered or referenced through the player-origin mystery.','affiliations':[],'claim_ids':['IR011','IR021'],'arc_ids':['arc-01','arc-12'],'lookup_names':[],'relationships':[{'target':'character:game-player','relation':'biological parents; names and exact fate remain UNKNOWN','claim_ids':['IR011','IR021']}]},
 {'entity_id':'character:gia-vuong','vi':'Gia Vương','cn':'嘉王','aliases':[],'role':'Royal figure whom the player locates and protects in the level 49–58 succession chain.','affiliations':['Nam Tống'],'claim_ids':['IR022'],'arc_ids':['arc-06'],'lookup_names':[],'relationships':[]},
 {'entity_id':'character:ly-hau','vi':'Lý Hậu','cn':'李后','aliases':[],'role':'Court actor whose intervention is countered in the succession chain.','affiliations':['Triều đình Nam Tống'],'claim_ids':['IR022'],'arc_ids':['arc-06'],'lookup_names':[],'relationships':[]},
 {'entity_id':'character:han-thac-tru','vi':'Hàn Thác Trụ','cn':'韩侂胄','aliases':[],'role':'Southern Song political leader associated with the Northern Expedition decision.','affiliations':['Nam Tống'],'claim_ids':['IR009'],'arc_ids':['arc-07','arc-11'],'lookup_names':['Hàn Thác Trụ'],'relationships':[]},
 {'entity_id':'character:ngo-hi','vi':'Ngô Hi','cn':'吴曦','aliases':['Ngô Hỉ'],'role':'Figure in the early regional chain and later first-party 1205 treason arc.','affiliations':['Nam Tống'],'claim_ids':['IR010','IR020','IR024'],'arc_ids':['arc-04','arc-06','arc-12'],'lookup_names':['Ngô Hỉ'],'relationships':[]},
 {'entity_id':'character:doan-tri-hung','vi':'Đoàn Trí Hưng','cn':'段智兴','aliases':[],'role':'Đại Lý figure in the level-110 crisis material.','affiliations':['Đại Lý','Đoàn Thị'],'claim_ids':['IR006'],'arc_ids':['arc-09'],'lookup_names':['Đoàn Trí Hưng'],'relationships':[]},
 {'entity_id':'character:la-tuyet','vi':'La Tuyết','cn':'罗雪','aliases':[],'role':'Character linked to the Đại Lý story and Thúy Yên disaster thread.','affiliations':[],'claim_ids':['IR006','IR020'],'arc_ids':['arc-04','arc-09'],'lookup_names':['La Tuyết'],'relationships':[]},
 {'entity_id':'character:doan-tieu-vu','vi':'Doãn Tiểu Vũ','cn':'尹筱雨','aliases':[],'role':'Protected/intelligence-linked character in the northern mission arc.','affiliations':['Nghĩa Quân'],'claim_ids':['IR007','IR016'],'arc_ids':['arc-10'],'lookup_names':[],'relationships':[]},
 {'entity_id':'character:gia-luat-so-tai','vi':'Gia Luật Sở Tài','cn':'耶律楚材','aliases':[],'role':'Named character in the northern mission setup.','affiliations':[],'claim_ids':['IR007','IR016'],'arc_ids':['arc-10'],'lookup_names':['Gia Luật Sở Tài'],'relationships':[]},
 {'entity_id':'character:hoan-nhan-tuong','vi':'Hoàn Nhan Tương','cn':'完颜襄','aliases':[],'role':'Jin-linked figure in the northern mission and post-50 treasure conflict.','affiliations':['Kim'],'claim_ids':['IR007','IR025'],'arc_ids':['arc-06','arc-10'],'lookup_names':['Hoàn Nhan Tương'],'relationships':[]},
 {'entity_id':'character:an-dong','vi':'Ân Đồng','cn':'殷童','aliases':[],'role':'Yên Vũ route contact preserved by raw dialogue and a contemporary retelling.','affiliations':[],'claim_ids':['IR014'],'arc_ids':['arc-02'],'lookup_names':['Ân Đồng'],'relationships':[]},
 {'entity_id':'character:ly-nguyen-triet','vi':'Lý Nguyên Triết','cn':'李元哲','aliases':[],'role':'Character in the Đường Môn insider and Du Long diagram investigation.','affiliations':[],'claim_ids':['IR023'],'arc_ids':['arc-06'],'lookup_names':['Lý Nguyên Triết'],'relationships':[]},
 {'entity_id':'character:duong-khuyet','vi':'Đường Khuyết','cn':'唐缺','aliases':[],'role':'Đường Môn-linked character in the Du Long diagram investigation.','affiliations':['Đường Môn'],'claim_ids':['IR023'],'arc_ids':['arc-06'],'lookup_names':['Đường Khuyết'],'relationships':[]},
 {'entity_id':'character:nap-tu','vi':'Nạp Tư','cn':None,'aliases':[],'role':'Character linked to the Hắc Long Đàm stage of the Du Long investigation.','affiliations':[],'claim_ids':['IR023'],'arc_ids':['arc-06'],'lookup_names':[],'relationships':[]},
 {'entity_id':'character:bach-cuong','vi':'Bạch Cương','cn':None,'aliases':[],'role':'Source of the letter evidence in the player-parentage chain.','affiliations':[],'claim_ids':['IR021'],'arc_ids':['arc-01','arc-12'],'lookup_names':['Bạch Cương'],'relationships':[]},
 {'entity_id':'character:chu-hy','vi':'Chu Hy','cn':'朱熹','aliases':['Chu lão tiên sinh'],'role':'Scholar covertly returned toward Lâm An in the recovered Man Thiên Quá Hải material.','affiliations':[],'claim_ids':['IR015'],'arc_ids':['arc-08'],'lookup_names':['Chu Hy'],'relationships':[]},
]

FACTIONS=[
 {'entity_id':'faction:nghia-quan','vi':'Nghĩa Quân','cn':'义军','aliases':[],'role':'Recurring player-aligned organization and mission authority.','claim_ids':['IR004','IR007','IR016','IR025']},
 {'entity_id':'faction:nam-tong','vi':'Nam Tống','cn':'南宋','aliases':['Đại Tống'],'role':'Primary political state whose succession, defense and Northern Expedition frame the main story.','claim_ids':['IR001','IR009','IR022','IR025']},
 {'entity_id':'faction:kim','vi':'Kim','cn':'金','aliases':['Jin'],'role':'Northern state and intelligence/war antagonist context.','claim_ids':['IR007','IR010','IR024','IR025']},
 {'entity_id':'faction:tay-ha','vi':'Tây Hạ','cn':'西夏','aliases':[],'role':'Regional power and location context in the post-50 pursuit.','claim_ids':['IR024']},
 {'entity_id':'faction:nhat-pham-duong','vi':'Nhất Phẩm Đường','cn':'一品堂','aliases':[],'role':'Organization involved in the Tây Hạ pursuit and later attack on Nghĩa Quân.','claim_ids':['IR010','IR024','IR025']},
 {'entity_id':'faction:duong-mon','vi':'Đường Môn','cn':'唐门','aliases':[],'role':'Sect/institution central to the insider and Du Long diagram investigation.','claim_ids':['IR023']},
 {'entity_id':'faction:cai-bang','vi':'Cái Bang','cn':'丐帮','aliases':[],'role':'Wulin faction involved in the cross-faction pursuit.','claim_ids':['IR024']},
 {'entity_id':'faction:ngu-doc','vi':'Ngũ Độc','cn':'五毒','aliases':[],'role':'Wulin faction involved in the cross-faction pursuit.','claim_ids':['IR024']},
 {'entity_id':'faction:thuy-yen','vi':'Thúy Yên','cn':'翠烟','aliases':[],'role':'Sect tied to the relic-triggered opening disaster and Đại Lý thread.','claim_ids':['IR002','IR006','IR020']},
 {'entity_id':'faction:thien-nhan','vi':'Thiên Nhẫn','cn':'天忍','aliases':[],'role':'Sect involved in the 1205 Linh Bích conflict.','claim_ids':['IR010']},
]

SECT_CN={1:'少林',2:'天王',3:'唐门',4:'五毒',5:'峨眉',6:'翠烟',7:'丐帮',8:'天忍',9:'武当',10:'昆仑',11:'明教',12:'段氏'}
SECT_CLAIMS={3:['IR023'],4:['IR024'],6:['IR002','IR006','IR020'],7:['IR024'],8:['IR010']}

ITEM_SPECS={
 'item:other/taskquest.txt:line:201':(['IR001','IR002'],'Central relic/macguffin record.'),
 'item:other/taskquest.txt:line:319':(['IR023'],'Wet bag explicitly described as containing a Du Long Giác secret.'),
 'item:other/taskquest.txt:line:326':(['IR023'],'Quest-instance Du Long Giác record.'),
 'item:other/taskquest.txt:line:351':(['IR024'],'Ngô Hỉ military tally used to command troops.'),
 'item:other/taskquest.txt:line:440':(['IR022'],'Ngọc Bút Lệnh command token.'),
 'item:other/taskquest.txt:line:453':(['IR023'],'First fragment of the mysterious scroll.'),
 'item:other/taskquest.txt:line:454':(['IR023'],'Second fragment of the mysterious scroll.'),
 'item:other/taskquest.txt:line:455':(['IR023'],'Third fragment of the mysterious scroll.'),
 'item:other/taskquest.txt:line:456':(['IR023'],'Fourth fragment of the mysterious scroll.'),
 'item:other/taskquest.txt:line:561':(['IR025'],'Map of Hoàn Nhan Tương’s residence.'),
 'item:other/taskquest.txt:line:665':(['IR001'],'Du Long Giác-Hùng record that references combination with Du Long Thư Giác.'),
}

LOCATION_SPECS=[
 ('location:nam-chieu','Nam Chiếu','南诏',None,['IR002'],'Official opening location; no exact promoted map record is asserted.'),
 ('map:12','Côn Lôn Phái','昆仑派','map:12',['IR003'],'Starting destination for the Binh Qua route selector.'),
 ('map:16','Nga My Phái','峨眉派','map:16',['IR003'],'Starting destination for the Tây Nam route selector.'),
 ('map:22','Thiên Vương Bang','天王帮','map:22',['IR003'],'Starting destination for the Yên Vũ route selector.'),
 ('map:25','Tương Dương Phủ','襄阳府','map:25',['IR022'],'Succession-chain city and mission staging area.'),
 ('map:29','Lâm An Phủ','临安府','map:29',['IR015'],'Destination context for the recovered Man Thiên Quá Hải beat.'),
 ('map:88','Hán Thủy Cổ Độ','汉水古渡','map:88',['IR022'],'Succession-chain crossing and conflict location.'),
 ('map:98','Điểm Thương Sơn','点苍山','map:98',['IR023'],'Location associated with the Du Long theft.'),
 ('map:13','Tây Hạ Nhất Phẩm Đường','西夏一品堂','map:13',['IR024','IR025'],'Tây Hạ/Nhất Phẩm Đường setting in the pursuit and recovery chain.'),
 ('map:511','Phi Long Cốc','飞龙谷','map:511',['IR022'],'Succession-chain location.'),
 ('map:513','Thiên Quỳnh Cung','千琼宫','map:513',['IR022'],'Succession-chain palace location.'),
 ('map:530','Hắc Long Đàm','黑龙潭','map:530',['IR023'],'Du Long diagram investigation location.'),
 ('map:561','Vọng Long Sơn','望龙山','map:561',['IR007'],'Northern mission location.'),
 ('map:569','Linh Bích Bạc','灵壁泊','map:569',['IR010','IR011'],'1205 endpoint conflict and player-origin reveal setting.'),
 ('map:28','Đại Lý Phủ','大理府','map:28',['IR006'],'Primary city context for the Đại Lý arc.'),
 ('map:819','Hoàng Cung Đại Lý','大理皇宫','map:819',['IR006'],'Palace context for the Đại Lý arc.'),
]

ARC_ENTITIES={
 'arc-00':['character:game-player','faction:nam-tong'],
 'arc-01':['character:game-player','character:bach-thu-lam','character:biological-parents'],
 'arc-02':['character:game-player','character:an-dong'],
 'arc-03':['character:game-player'],
 'arc-04':['character:game-player','character:ngo-hi','character:la-tuyet','faction:thuy-yen'],
 'arc-05':['character:game-player'],
 'arc-06':['character:game-player','character:gia-vuong','character:ly-hau','character:ly-nguyen-triet','character:duong-khuyet','character:nap-tu','character:ngo-hi','character:hoan-nhan-tuong','faction:nghia-quan','faction:kim','faction:tay-ha','faction:nhat-pham-duong'],
 'arc-07':['character:game-player','character:bach-thu-lam','character:han-thac-tru','faction:nghia-quan'],
 'arc-08':['character:game-player','character:chu-hy'],
 'arc-09':['character:game-player','character:doan-tri-hung','character:la-tuyet'],
 'arc-10':['character:game-player','character:doan-tieu-vu','character:gia-luat-so-tai','character:hoan-nhan-tuong','faction:kim','faction:nghia-quan'],
 'arc-11':['character:han-thac-tru','faction:nam-tong'],
 'arc-12':['character:game-player','character:bach-thu-lam','character:biological-parents','character:ngo-hi','faction:thien-nhan','faction:nhat-pham-duong'],
 'endpoint':['faction:nam-tong'],
}

CAUSAL_EDGES=[
 ('IR001','IR002','relic background to documented reappearance/crisis','STRONG'),
 ('IR003','IR005','regional-mainline architecture to pre-50 convergence prerequisite','STRONG'),
 ('IR005','IR022','pre-50 completion/convergence to shared post-50 chain','STRONG'),
 ('IR022','IR023','succession chain to Du Long diagram investigation','VERIFIED_DIRECT'),
 ('IR023','IR024','Du Long theft to leak investigation and pursuit','VERIFIED_DIRECT'),
 ('IR024','IR025','Tây Hạ pursuit to recovery/treasure conflict','VERIFIED_DIRECT'),
 ('IR009','IR010','Northern Expedition decision context to the 1205 campaign arc','VERIFIED_CROSS_SOURCE'),
]

def load_json(path:Path):return json.loads(path.read_text(encoding='utf-8'))
def load_jsonl(path:Path):return [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line]
def write_json(path:Path,value):path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def sha(path:Path):return hashlib.sha256(path.read_bytes()).hexdigest()
def git_head():return subprocess.run(['git','rev-parse','HEAD'],cwd=ROOT,text=True,capture_output=True,check=True).stdout.strip()
def generated_meta():return {'schema_version':SCHEMA_VERSION,'generator':GENERATOR,'generated_at_utc':datetime.now(timezone.utc).isoformat()}
def clean_text(value):return re.sub(r'<[^>]+>','',value or '').strip()
def record_source(record):return [{key:row.get(key) for key in ('source_id','evidence_class','path','sha256','locator','edition') if row.get(key) not in (None,'')} for row in record.get('source_records',[])]
def compact_evidence(evidence):return {key:evidence.get(key) for key in ('source_family','support_type','evidence_class','path','url','sha256','response_sha256','locator','record_key','citation_id') if evidence.get(key) not in (None,'')}
def claim_projection(claim):return {'claim_id':claim['claim_id'],'claim':claim['claim'],'status':claim['status'],'centrality':claim['centrality'],'narrative_impact':claim['narrative_impact'],'evidence':[compact_evidence(row) for row in claim['evidence']]}

def assert_preconditions(concordance,release,validation):
 gates=concordance.get('promotion_gates',{})
 failures=[]
 for gate in ('S3','S4','S5'):
  if gates.get(gate,{}).get('status')!='PASS':failures.append(f'{gate} is not PASS')
 if concordance.get('promotion_decision')!='NOVEL_PROMOTION_READY':failures.append('reconciliation is not NOVEL_PROMOTION_READY')
 if concordance.get('central_blocker_count')!=0:failures.append('CENTRAL_BLOCKER count is not zero')
 if concordance.get('unresolved_material_conflict_count')!=0:failures.append('unresolved MATERIAL narrative conflict count is not zero')
 if release.get('novel_promotion')!='NOVEL_PROMOTION_READY':failures.append('release manifest is not promotion ready')
 if validation.get('status')!='PASS' or validation.get('errors'):failures.append('Research Release validation is not clean')
 if failures:raise RuntimeError('NOVEL_HANDOFF_BLOCKED: '+'; '.join(failures))

def build():
 root=OUT.resolve();expected=(ROOT/'generated'/'novel-handoff').resolve()
 if root!=expected:raise RuntimeError('Unsafe handoff output path')
 if OUT.exists():shutil.rmtree(OUT)
 OUT.mkdir(parents=True)
 source_commit=git_head()
 concordance=load_json(ROOT/'research'/'reconciliation'/'lore-concordance.json')
 release=load_json(ROOT/'generated'/'release'/'release-manifest.json')
 validation=load_json(ROOT/'generated'/'reports'/'release-validation-report.json')
 confidence=load_json(ROOT/'research'/'confidence-report.json')
 unresolved=load_json(ROOT/'research'/'unresolved-questions.json')['entries']
 claims=load_jsonl(ROOT/'research'/'reconciliation'/'internet-research-claims.jsonl');claims_by_id={row['claim_id']:row for row in claims}
 dossier_index=load_json(ROOT/'research'/'reconstruction'/'game-story-dossiers'/'index.json')
 assert_preconditions(concordance,release,validation)

 tasks=load_jsonl(ROOT/'generated'/'records'/'tasks'/'task-archive-records.jsonl')
 subs=load_jsonl(ROOT/'generated'/'records'/'tasks'/'subtask-archive-records.jsonl')
 npcs=load_jsonl(ROOT/'generated'/'records'/'npcs'/'npc-records.jsonl')
 factions=load_jsonl(ROOT/'generated'/'records'/'sects'/'faction-records.jsonl')
 routes=load_jsonl(ROOT/'generated'/'records'/'sects'/'route-records.jsonl')
 skills=load_jsonl(ROOT/'generated'/'records'/'skills'/'skill-records.jsonl')
 faction_skill_edges=load_jsonl(ROOT/'generated'/'records'/'edges'/'faction-skill-reference-edges.jsonl')
 items=load_jsonl(ROOT/'generated'/'records'/'items'/'item-records.jsonl')
 maps=load_jsonl(ROOT/'generated'/'records'/'locations'/'location-records.jsonl')
 post50=load_json(ROOT/'research'/'reconstruction'/'level-50-89-mainline.json')
 task_by_id=defaultdict(list);sub_by_id={row['task_id_decimal']:row for row in subs};npc_by_name=defaultdict(list)
 for row in tasks:task_by_id[row['task_id_decimal']].append(row)
 for row in npcs:npc_by_name[row['name'].strip()].append(row)
 item_by_key={row['record_key']:row for row in items};map_by_key={row['record_key']:row for row in maps}
 skill_by_id={}
 for row in skills:skill_by_id.setdefault(row['skill_id'],row)

 projected_dossiers=[];arc_rows=[];chronology=['# Kiếm Thế source-canon master chronology','','This is a source-only chronology for forensic import. It is not a novel outline, adaptation plan or prose.','']
 for position,entry in enumerate(dossier_index['dossiers'],1):
  source_path=ROOT/entry['path'];dossier=load_json(source_path);arc_id=dossier['arc_id']
  referenced=[]
  for field,value in dossier.items():
   if field.endswith('_claim_ids') and isinstance(value,list):referenced.extend(value)
  for event in dossier.get('ordered_events',[]):referenced.append(event['claim_id'])
  referenced=list(dict.fromkeys(referenced));resolved=[claim_projection(claims_by_id[claim_id]) for claim_id in referenced]
  projected={**dossier,'handoff_projection_version':SCHEMA_VERSION,'source_dossier':{'path':jxlab.rel(source_path),'sha256':sha(source_path)},'resolved_claims':resolved,'principal_entity_ids':ARC_ENTITIES.get(arc_id,[])}
  destination=OUT/'game-story'/'dossiers'/f'{arc_id}.json';write_json(destination,projected);projected_dossiers.append(destination)
  arc_rows.append({'order':position,'arc_id':arc_id,'title':dossier['title'],'aliases':[],'chronology_or_level_range':dossier['chronology_or_level_range'],'dossier_path':destination.relative_to(OUT).as_posix(),'principal_entity_ids':ARC_ENTITIES.get(arc_id,[]),'claim_ids':referenced,'status':'PROMOTED_SOURCE_CANON','confidence':'MIXED_PROMOTABLE','central_unresolved_count':len(dossier.get('central_unknown_ids',[])),'important_martial_item_location_references':[row for row in referenced if row in {'IR001','IR002','IR006','IR007','IR010','IR015','IR022','IR023','IR024','IR025'}]})
  chronology.extend([f"## {position}. {dossier['title']}",f"- Stable arc ID: `{arc_id}`",f"- Chronology/level: {dossier['chronology_or_level_range']}",f"- Source dossier: `{destination.relative_to(OUT).as_posix()}`"])
  for event in dossier.get('ordered_events',[]):
   claim=claims_by_id[event['claim_id']];chronology.append(f"- `{claim['claim_id']}` [{claim['status']}]: {claim['claim']}")
  if dossier.get('central_unknown_ids'):chronology.append('- Tolerated unknowns: '+', '.join(f"`{value}`" for value in dossier['central_unknown_ids']))
  chronology.append('')
 (OUT/'game-story'/'master-chronology.md').parent.mkdir(parents=True,exist_ok=True)
 (OUT/'game-story'/'master-chronology.md').write_text('\n'.join(chronology),encoding='utf-8')
 write_json(OUT/'game-story'/'arc-index.json',{**generated_meta(),'promotion_status':'NOVEL_PROMOTION_READY','arc_count':len(arc_rows),'arcs':arc_rows})

 causal_nodes=[{**claim_projection(claim),'arc_ids':claim['arc_ids']} for claim in claims]
 causal_edges=[]
 for index,(source,target,relation,status) in enumerate(CAUSAL_EDGES,1):
  causal_edges.append({'edge_id':f'causal:{index:02d}','source_claim_id':source,'target_claim_id':target,'relationship':relation,'status':status,'evidence_claim_ids':[source,target]})
 write_json(OUT/'game-story'/'causal-spine.json',{**generated_meta(),'promotion_status':'NOVEL_PROMOTION_READY','scope':'Only promoted claim nodes and explicitly curated evidence-supported transitions; absent bridges remain absent.','nodes':causal_nodes,'edges':causal_edges})

 character_rows=[]
 for spec in CHARACTERS:
  raw=[]
  for name in spec['lookup_names']:raw.extend(npc_by_name.get(name,[]))
  character_rows.append({key:value for key,value in spec.items() if key!='lookup_names'}|{'source_record_keys':[row['record_key'] for row in raw[:12]],'source_records':[source for row in raw[:12] for source in record_source(row)],'claim_evidence':[claim_projection(claims_by_id[claim_id]) for claim_id in spec['claim_ids']]})
 write_json(OUT/'characters'/'index.json',{**generated_meta(),'selection_policy':'Only recurring or load-bearing promoted-story characters; traits are not inferred.','count':len(character_rows),'characters':character_rows})

 faction_rows=[]
 for spec in FACTIONS:faction_rows.append(spec|{'claim_evidence':[claim_projection(claims_by_id[claim_id]) for claim_id in spec['claim_ids']]})
 write_json(OUT/'factions'/'index.json',{**generated_meta(),'selection_policy':'Only organizations or polities with a promoted-story role.','count':len(faction_rows),'factions':faction_rows})

 route_by_faction=defaultdict(list)
 for row in routes:
  faction_id=int(row['route_id']['faction_id'])
  if faction_id in SECT_CN:route_by_faction[faction_id].append(row)
 sect_rows=[];martial_sects=[]
 for faction in factions:
  faction_id=int(faction['faction_id'])
  if faction_id not in SECT_CN:continue
  sect_routes=[];martial_routes=[]
  for route in sorted(route_by_faction[faction_id],key=lambda row:int(row['route_id']['route_id'])):
   edges=[edge for edge in faction_skill_edges if edge['source_key']==route['record_key'] and edge['relation']=='route_skill_reference']
   representative=[]
   for edge in edges:
    skill=skill_by_id.get(edge['target_key'].removeprefix('skill:'))
    if not skill or not skill['name'] or skill['name'].startswith('Đánh thường'):continue
    representative.append({'skill_id':skill['skill_id'],'record_key':skill['record_key'],'name':skill['name'],'property':skill['property'],'description':clean_text(skill['description']),'faction_limit':skill['faction_limit'],'route_limit':skill['route_limit'],'source_records':record_source(skill)})
    if len(representative)==8:break
   sect_routes.append({'record_key':route['record_key'],'route_id':route['route_id'],'name':route['name'],'description':route['description'],'referenced_skill_count':len(edges),'source_records':record_source(route)})
   martial_routes.append({'route_record_key':route['record_key'],'route_name':route['name'],'referenced_skill_count':len(edges),'representative_skills':representative})
  claims_for_sect=SECT_CLAIMS.get(faction_id,[])
  sect_rows.append({'entity_id':f'sect:{faction_id}','faction_id':faction['faction_id'],'name_vi':faction['name'],'name_cn':SECT_CN[faction_id],'institutional_role':'One of the twelve configured sects; story role is stated only when claim evidence exists.','story_claim_ids':claims_for_sect,'routes':sect_routes,'source_records':record_source(faction)})
  martial_sects.append({'sect_id':f'sect:{faction_id}','sect_name':faction['name'],'routes':martial_routes})
 write_json(OUT/'sects'/'index.json',{**generated_meta(),'selection_policy':'Twelve configured sects and their route identities; no power ranking is inferred.','count':len(sect_rows),'sects':sect_rows})
 write_json(OUT/'martial-arts'/'index.json',{**generated_meta(),'selection_policy':'Up to eight named, non-basic representative skills per configured route; numerical mechanics are retained only as source fields, not interpreted as power rankings.','sect_count':len(martial_sects),'sects':martial_sects})

 important_items=[]
 for record_key,(claim_ids,role) in ITEM_SPECS.items():
  record=item_by_key[record_key];important_items.append({'entity_id':record_key,'name':record['name'],'story_role':role,'description':clean_text(record['description']),'item_id':record['item_id'],'family':record['family'],'claim_ids':claim_ids,'source_records':record_source(record)})
 write_json(OUT/'important-items'/'index.json',{**generated_meta(),'selection_policy':'Quest-critical relics, tokens, maps and fragments tied to promoted claims only.','count':len(important_items),'items':important_items})

 important_locations=[]
 for entity_id,vi,cn,record_key,claim_ids,role in LOCATION_SPECS:
  record=map_by_key.get(record_key)
  important_locations.append({'entity_id':entity_id,'name_vi':vi,'name_cn':cn,'story_role':role,'map_id':record['location_id'] if record else None,'map_type':record['map_type'] if record else None,'resource_name':record['resource_name'] if record else None,'claim_ids':claim_ids,'source_records':record_source(record) if record else [],'claim_evidence':[claim_projection(claims_by_id[claim_id]) for claim_id in claim_ids]})
 write_json(OUT/'important-locations'/'index.json',{**generated_meta(),'selection_policy':'Locations needed for promoted causal continuity or recurring Wulin identity.','count':len(important_locations),'locations':important_locations})

 name_rows=[];alias_rows=[]
 for row in character_rows:
  if row['cn']:name_rows.append({'entity_id':row['entity_id'],'cn':row['cn'],'vi':row['vi'],'variants':row['aliases'],'claim_ids':row['claim_ids']})
  alias_rows.append({'entity_id':row['entity_id'],'canonical':row['vi'],'aliases':([row['cn']] if row['cn'] else [])+row['aliases'],'type':'character'})
 for row in faction_rows:
  name_rows.append({'entity_id':row['entity_id'],'cn':row['cn'],'vi':row['vi'],'variants':row['aliases'],'claim_ids':row['claim_ids']});alias_rows.append({'entity_id':row['entity_id'],'canonical':row['vi'],'aliases':[row['cn']]+row['aliases'],'type':'faction'})
 for row in sect_rows:
  name_rows.append({'entity_id':row['entity_id'],'cn':row['name_cn'],'vi':row['name_vi'],'variants':[],'source_record_keys':[row['source_records'][0]['path'] if row['source_records'] else None]});alias_rows.append({'entity_id':row['entity_id'],'canonical':row['name_vi'],'aliases':[row['name_cn']],'type':'sect'})
 for row in important_locations:
  name_rows.append({'entity_id':row['entity_id'],'cn':row['name_cn'],'vi':row['name_vi'],'variants':[],'claim_ids':row['claim_ids']});alias_rows.append({'entity_id':row['entity_id'],'canonical':row['name_vi'],'aliases':[row['name_cn']],'type':'location'})
 write_json(OUT/'concordance'/'cn-vi-names.json',{**generated_meta(),'scope':'Important promoted-story entities and the twelve configured sects only.','count':len(name_rows),'entries':name_rows})
 write_json(OUT/'concordance'/'entity-aliases.json',{**generated_meta(),'count':len(alias_rows),'entries':alias_rows})

 task_map=[]
 selectors=[(314,'arc-02','IR003'),(315,'arc-03','IR003'),(316,'arc-04','IR003')]
 for sub_id,arc_id,claim_id in selectors:
  row=sub_by_id[sub_id];task_map.append({'source_record_key':row['record_key'],'source_id_decimal':sub_id,'source_name':row['name'],'record_kind':'subtask','arc_id':arc_id,'beat_claim_ids':[claim_id],'mapping_basis':'explicit route-selector record plus reconciled architecture claim','source_records':record_source(row)})
 for task_id,arc_id,claim_id in [(6,'arc-03','IR019'),(7,'arc-03','IR019'),(8,'arc-03','IR019'),(9,'arc-03','IR019'),(10,'arc-04','IR020'),(11,'arc-04','IR020'),(12,'arc-04','IR020'),(157,'arc-01','IR021'),(294,'arc-08','IR015')]:
  for row in task_by_id[task_id]:
   task_map.append({'source_record_key':row['record_key'],'source_id_decimal':task_id,'source_name':row['name'],'record_kind':'task','arc_id':arc_id,'beat_claim_ids':[claim_id],'mapping_basis':'claim evidence directly cites this task family','source_records':record_source(row)})
 for family in post50['task_families']:
  phase=next(row for row in post50['phases'] if row['phase_id']==family['phase_id'])
  task_map.append({'source_record_key':family['record_key'],'source_id_decimal':family['task_id'],'source_name':family['name'],'record_kind':'task','arc_id':'arc-06','beat_claim_ids':[phase['claim_id']],'narrative_order':family['narrative_order'],'level_gate_range':[family['min_level_gate'],family['max_level_gate']],'mapping_basis':'validated wrapper-inline level gates and managed order; standalone same-ID content excluded','source_records':family['source_records']})
 write_json(OUT/'concordance'/'task-story-map.json',{**generated_meta(),'warning':'Task identifiers support forensic lookup; they do not define novel structure.','count':len(task_map),'entries':task_map})

 central=[row|{'promotion_safety':'Coherent adaptation remains possible because the uncertainty is explicitly bounded and no promoted claim depends on an invented answer.'} for row in unresolved if row.get('centrality')=='CENTRAL_TOLERABLE']
 noncentral=[row for row in unresolved if row.get('centrality')=='NON_CENTRAL']
 write_json(OUT/'unresolved'/'central-tolerable.json',{**generated_meta(),'count':len(central),'entries':central})
 write_json(OUT/'unresolved'/'non-central.json',{**generated_meta(),'count':len(noncentral),'entries':noncentral})
 write_json(OUT/'unresolved'/'material-conflicts.json',{**generated_meta(),'count':0,'entries':[],'note':'No unresolved MATERIAL narrative conflict exists at handoff generation time.'})

 relevant_paths=[ROOT/'generated'/'release'/'release-manifest.json',ROOT/'generated'/'reports'/'release-validation-report.json',ROOT/'research'/'reconciliation'/'lore-concordance.json',ROOT/'research'/'reconstruction'/'game-story-dossiers'/'index.json',ROOT/'research'/'confidence-report.json',ROOT/'research'/'unresolved-questions.json']
 source_classes=sorted({evidence.get('evidence_class') for claim in claims for evidence in claim['evidence'] if evidence.get('evidence_class')}|{'RAW_SERVER','RAW_CLIENT'})
 provenance={**generated_meta(),'source_repository':'anhdaijka/jx-source-lab','source_lab_commit':source_commit,'research_release':{'version':release['release_version'],'status':release['release_status'],'promotion':release['novel_promotion']},'reconciliation_artifacts':[{'path':jxlab.rel(path),'sha256':sha(path)} for path in relevant_paths],'source_classes_represented':source_classes,'known_story_relevant_limitations':[row['question'] for row in central],'persisted_user_canon_decisions':[],'build_version_policy':'Exact client/server build/version identity is metadata only and is not a promotion requirement unless it changes a MATERIAL story interpretation.','raw_payload_policy':'Raw client/server files, PAKs, binaries, archives, private-input packages and bulk extracted payloads are excluded; provenance references remain textual.'}
 write_json(OUT/'provenance.json',provenance)
 confidence_summary={**generated_meta(),'promotion_status':'NOVEL_PROMOTION_READY','promotion_gates':concordance['promotion_gates'],'claim_status_counts':concordance['claim_status_counts'],'promoted_story_dossiers':len(projected_dossiers),'unresolved_counts':{'CENTRAL_BLOCKER':0,'CENTRAL_TOLERABLE':len(central),'NON_CENTRAL':len(noncentral),'UNRESOLVED_MATERIAL_CONFLICT':0},'interpretation_boundary':'Promotable source-canon only; no adaptation, episode structure or prose decision is included.'}
 write_json(OUT/'confidence-summary.json',confidence_summary)

 files=[]
 for path in sorted(p for p in OUT.rglob('*') if p.is_file() and p.name!='handoff-manifest.json'):
  files.append({'path':path.relative_to(OUT).as_posix(),'sha256':sha(path),'bytes':path.stat().st_size})
 manifest={**generated_meta(),'handoff_status':'NOVEL_HANDOFF_READY','source_repository':'anhdaijka/jx-source-lab','source_lab_commit':source_commit,'canon_target':'LATEST_COHERENT_KIEM_THE_LORE','promotion_status':'NOVEL_PROMOTION_READY','promotion_gates':concordance['promotion_gates'],'promoted_main_story_arc_count':len(projected_dossiers),'unresolved_counts':{'CENTRAL_BLOCKER':0,'CENTRAL_TOLERABLE':len(central),'NON_CENTRAL':len(noncentral),'UNRESOLVED_MATERIAL_CONFLICT':0},'raw_proprietary_payloads_excluded':True,'one_way_import_contract':True,'runtime_dependency_on_lab':False,'files':files,'manifest_self_hash_note':'The manifest cannot recursively hash itself; every payload artifact is hashed above.'}
 write_json(OUT/'handoff-manifest.json',manifest)
 return {'status':'NOVEL_HANDOFF_READY','source_lab_commit':source_commit,'files':len(files)+1,'bytes':sum(row['bytes'] for row in files)+(OUT/'handoff-manifest.json').stat().st_size,'dossiers':len(projected_dossiers),'central_tolerable':len(central),'non_central':len(noncentral)}

if __name__=='__main__':print(json.dumps(build(),ensure_ascii=False,indent=2))
