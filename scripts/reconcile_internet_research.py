#!/usr/bin/env python3
"""Reconcile curated internet-research claims with story-bearing Lab records."""
from __future__ import annotations

import hashlib
import json
import re
import xml.etree.ElementTree as ET
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import jxlab

ROOT=Path(__file__).resolve().parents[1]
PACKAGE=ROOT/'private-input'/'internet-research'
OUT=ROOT/'research'/'reconciliation'
DOSSIERS=ROOT/'research'/'reconstruction'/'game-story-dossiers'
PARSER_VERSION='jxlab internet-reconciliation/0.2'

LIVE_SOURCES={
 'KX-BG-01':('OFFICIAL_KINGSOFT_XOYO','https://jxsj.xoyo.com/show-3431-9765-1.html','a03040f55994afd10641d951214d60cac87c04d676d68b7d1a5fd06df07bbd31','LIVE_HTTP_200_CONTENT_MATCH','1189年春; 二十余名高手; 游龙珏'),
 'KX-ARCH-01':('OFFICIAL_KINGSOFT_XOYO','https://jxsj.xoyo.com/show-3415-6173-1.html','278b09f4fa3b46606facee255e1c510e7de0ec5e5828f4c07f82a64892339442','LIVE_HTTP_200_CONTENT_MATCH','三条区域主线; 江南区; 中原区; 西南区; 50级之后; 交叉叙事'),
 'KX-90-01':('OFFICIAL_KINGSOFT_XOYO','https://jxsj.xoyo.com/zt/2008/0902/rwbj.shtml','a3ca24329ba37f857d512d14ec876388b51bb833f7752dfa043c823dbf03139d','LIVE_HTTP_200_PAGE_IMAGE_ONLY','page identity only; detailed text not machine-verified'),
 'KX-110-01':('OFFICIAL_KINGSOFT_XOYO','https://jxsj.xoyo.com/zt/2008/1222/index.shtml','d8f359fd514b434f53d5d9f72dbf09fa0bc9dbd4e83ced3004fdeaedb9c2ff48','LIVE_HTTP_200_PAGE_IMAGE_ONLY','110 special identity only; detailed text not machine-verified'),
 'KX-120-01':('OFFICIAL_KINGSOFT_XOYO','https://jxsj.xoyo.com/zt/2009/03/20/index2.shtml','50c79dee52b825b4ce6ec2acb1ad1c6d9db589b54c2d06b4f337ffdcd6a65a61','LIVE_HTTP_200_PAGE_IMAGE_ONLY','120 special identity only; detailed text not machine-verified'),
 'KX-130-01':('OFFICIAL_KINGSOFT_XOYO','https://jxsj.xoyo.com/show-3416-8139-1.html','26af8e24acd558b33d74d28d1f9ee0a097a85455609ca91c69a5dc5397890120','LIVE_HTTP_200_CONTENT_MATCH','韩侂胄; 北伐金国; 钱象祖'),
 'KX-140-01':('OFFICIAL_KINGSOFT_XOYO','https://jxsj.xoyo.com/zt/2009/09/28/index.shtml','830bf2ef6fd9d373cbaa8cfe9d471f217c8adc78eeb11a0b81a7fce5613b6d78','LIVE_HTTP_200_CONTENT_MATCH','1205; 灵壁泊; 吴曦; 毕再遇; 天忍教; 一品堂'),
 'KX-140-02':('OFFICIAL_KINGSOFT_XOYO','https://jxsj.xoyo.com/zt/2009/09/28/index2.shtml','e0751c0d3d57a107567231c699e4de9f6be903e1e51d26b9581da7b7b2921dc5','LIVE_HTTP_200_CONTENT_MATCH','白家大小姐白秋琳; 身世迷踪; 亲生父母'),
 'KX-140-03':('OFFICIAL_KINGSOFT_XOYO','https://jxsj.xoyo.com/zt/2009/09/28/index3.shtml','e343db5335138de0feb4d637fcc7ec6b883a29f171d634b8465b9f933a6a0bbc','LIVE_HTTP_200_CONTENT_MATCH','135级; 白秋琳; 如火如荼'),
 'VNG-NAME-01':('OFFICIAL_VNG','https://kiemthe.zing.vn/cam-nang/mon-phai/thuy-yen.html','81b736e1a56d0da4847988e5dc0b37d3c365ba5abac4e270bd1fc9e7b4395a8d','LIVE_HTTP_200_CONTENT_MATCH','Doãn Tiểu Vũ; Thúy Yên; Gia Luật Sở Tài'),
 'VNG-BTL-01':('OFFICIAL_VNG','https://kiemthe.zing.vn/tin-tuc/tinh-nang/tich-luy-tien-nghia-quan-doi-thuong-thang-05-2013.html','c96af42fbe9c4f5e8b115849cb0c412e116b3134d788edf37dfbfe8f7c7ada9f','LIVE_HTTP_200_CONTENT_MATCH','Bạch Thu Lâm; Nghĩa Quân'),
 'VNG-DRIFT-01':('OFFICIAL_VNG','https://kiemthe.zing.vn/tin-tuc/tinh-nang/kham-pha-pho-ban-moi-danh-cho-tan-thu.html','92149cfa527469f93e87811e4efdc64e5e201cb5f6ca2a9aad053d9e1fc8ecf3','LIVE_HTTP_200_CONTENT_MATCH','2012 later-new-player content; edition evidence only'),
 'KX-PRE50-01':('OFFICIAL_ARCHIVE','https://jxsj.17173.com/content/2008-07-04/1215138256.shtml','8c65304f24b1dfc4b9354656083aa1d8b4be2242fdcccd95f590c3d0c3c359b2','LIVE_HTTP_200_CONTENT_MATCH','神州往事接任务以完成50级前主线为前提'),
 'KX-YANYU-01':('OFFICIAL_ARCHIVE','https://jxsj.17173.com/content/2008-11-24/1227491402.shtml','cc9cb52b3c9b27bcaa9a342499b46bb9567e9dde023107424d964bed38179cd9','LIVE_HTTP_200_CONTENT_MATCH','木一楼; 殷童; 靡靡香'),
 'KX-POST50-PATCH-01':('OFFICIAL_KINGSOFT_XOYO','https://jxsj.xoyo.com/kfnotic/296247/','07c190981e531aac519d8713d649aa7998b7fce4ac1f1d4c55cfbca9539754dc','LIVE_HTTP_200_CONTENT_MATCH','2008-08-12 maintenance; mainline tasks 别有洞天 and 家国大义'),
}

def load_jsonl(path):return [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line]
def write_json(path,value):path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def meta():return {'schema_version':'1.0','generator':'scripts/reconcile_internet_research.py','parser_version':PARSER_VERSION,'generated_at_utc':datetime.now(timezone.utc).isoformat()}
def pkg(path,locator,citation):
 p=PACKAGE/path
 return {'source_family':'internet_research_package','support_type':'claim_summary','evidence_class':'LEGACY_LEAD','path':jxlab.rel(p),'sha256':jxlab.sha256_file(p),'locator':locator,'citation_id':citation}
def live(citation):
 evidence_class,url,sha,status,locator=LIVE_SOURCES[citation]
 return {'source_family':'first_party_web' if evidence_class.startswith('OFFICIAL_') and evidence_class!='OFFICIAL_ARCHIVE' else 'contemporary_partner_web','support_type':'direct_content' if status.endswith('CONTENT_MATCH') else 'source_identity_only','evidence_class':evidence_class,'url':url,'retrieved_at_utc':'2026-08-14T08:00:00+00:00','response_sha256':sha,'verification_status':status,'locator':locator,'citation_id':citation}

TASKS=load_jsonl(ROOT/'generated/records/tasks/task-archive-records.jsonl')
SUBS=load_jsonl(ROOT/'generated/records/tasks/subtask-archive-records.jsonl')
DIALOGUES=load_jsonl(ROOT/'generated/records/dialogue/task-dialogue-records.jsonl')
EDGES=load_jsonl(ROOT/'generated/records/edges/task-reference-edges.jsonl')

POST50_TASK_ORDER=(13,14,15,17,16,18,21,19,20,22,23,24)
POST50_PHASES=[
 {'phase_id':'post50-49-58','level_range':'49-58','task_ids':[13,14,15],'claim_id':'IR022','summary':'Bạch Thu Lâm assigns a secret mission to locate and protect Gia Vương; the chain moves through Tương Dương, Hán Thủy, Phi Long and Thiên Quỳnh, counters Lý Hậu and ends with Gia Vương taking the throne.'},
 {'phase_id':'post50-58-69','level_range':'58-69','task_ids':[17,16,18],'claim_id':'IR023','summary':'The player investigates a Đường Môn insider and a Du Long diagram through Lý Nguyên Triết, Đường Khuyết, Nạp Tư and Hắc Long Đàm; the relic is then stolen at Điểm Thương.'},
 {'phase_id':'post50-69-79','level_range':'69-79','task_ids':[21,19,20],'claim_id':'IR024','summary':'The investigation follows an Ngô Hi information leak and a cross-faction pursuit involving Cái Bang, Ngũ Độc, Jin-linked actors and Nhất Phẩm Đường, ending in the Tây Hạ confrontation.'},
 {'phase_id':'post50-79-89','level_range':'79-89','task_ids':[22,23,24],'claim_id':'IR025','summary':'After the Du Long recovery effort, Nhất Phẩm Đường attacks Nghĩa Quân and competing groups pursue the treasure; the chain reaches a cave conflict involving Hoàn Nhan Tương and ends at Đại Nghĩa Nước Nhà.'},
]

POST50_SEARCH_AUDIT={
 'scope':'Locate detailed contemporary or first-party walkthrough evidence for the original post-50 mainline without identifying the exact local client/server version.',
 'searched_at_utc':'2026-08-14T08:51:12+00:00',
 'method':'Web search plus the public 17173 search API, restricted to jxsj.17173.com; exact phrase matching was applied locally to the first 100 relevance-ranked results per term.',
 'queries':[
  {'term':'飞龙谷','api_total_count':10985,'exact_matches_in_first_100':0},
  {'term':'李元哲','api_total_count':0,'exact_matches_in_first_100':0},
  {'term':'怀璧其罪','api_total_count':2532,'exact_matches_in_first_100':0},
  {'term':'家国大义','api_total_count':1774,'exact_matches_in_first_100':0},
  {'term':'进菊洞','api_total_count':8687,'exact_matches_in_first_100':0},
  {'term':'天琼宫','api_total_count':10409,'exact_matches_in_first_100':0},
  {'term':'黑龙潭','api_total_count':9720,'exact_matches_in_first_100':0},
  {'term':'游龙图','api_total_count':11119,'exact_matches_in_first_100':0},
 ],
 'located_sources':['KX-ARCH-01','KX-PRE50-01','KX-POST50-PATCH-01'],
 'result':'BOUNDED_NOT_FOUND_DETAILED_WALKTHROUGH',
 'interpretation':'This does not prove that no walkthrough exists. The raw wrapper corpus remains the primary detailed evidence; web sources corroborate architecture, the pre-50 prerequisite and named post-50 mainline endpoints only.',
}

def raw_record(record,support_type='direct_record'):
 source=dict(record['source_records'][0]);source.update({'source_family':'lab_raw_story','support_type':support_type,'record_key':record.get('record_key') or record.get('dialogue_id')})
 return source
def task(task_id):
 matches=[row for row in TASKS if row['task_id_decimal']==task_id and row['classification']['class']=='main'] or [row for row in TASKS if row['task_id_decimal']==task_id]
 return raw_record(matches[0])
def sub(sub_id):return raw_record(next(row for row in SUBS if row['task_id_decimal']==sub_id))
def dialogue(owner,phase='start'):
 return raw_record(next(row for row in DIALOGUES if row['owner_key']==owner and row['phase']==phase),'direct_dialogue')
def graph_evidence(note):return {'source_family':'lab_derived_index','support_type':'explicit_xml_edges','path':'generated/records/edges/task-reference-edges.jsonl','sha256':jxlab.sha256_file(ROOT/'generated/records/edges/task-reference-edges.jsonl'),'locator':note}

def main_task_record(task_id):
 matches=[row for row in TASKS if row['task_id_decimal']==task_id and row['classification']['class']=='main']
 if len(matches)!=1:raise RuntimeError(f'Expected one main task record for {task_id}, found {len(matches)}')
 return matches[0]

def inline_level_gates(child):
 levels=[]
 for grid in child.iter('Grid'):
  if (grid.findtext('Function') or '').strip()!='TaskCond:IsLevelAE':continue
  levels.extend(int(value.text.strip()) for value in grid.findall('.//Value') if value.text and value.text.strip().isdigit())
 return sorted(set(levels))

def build_post50_reconstruction():
 managed_by_source={}
 for edge in EDGES:
  if edge['relation']=='manages_sub':managed_by_source.setdefault(edge['source_key'],[]).append(edge)
 families=[]
 for narrative_order,task_id in enumerate(POST50_TASK_ORDER,1):
  record=main_task_record(task_id);entry_id=record['record_key'].rsplit(':entry:',1)[1]
  archive_short=record['source_records'][0]['sha256'][:12]
  xml_path=ROOT/'generated'/'extracted'/f'task_publish-{archive_short}'/'entries'/f'{entry_id}.bin'
  root=ET.parse(xml_path).getroot();children=root.findall('./Managed/Sub')
  edges=sorted(managed_by_source.get(record['record_key'],[]),key=lambda edge:int(edge['edge_id'].rsplit(':',1)[1]))
  if len(children)!=len(edges):raise RuntimeError(f'Managed edge count differs for {record["record_key"]}')
  subtasks=[]
  for ordinal,(child,edge) in enumerate(zip(children,edges),1):
   inline_id=(child.attrib.get('id') or '').upper();refer_id=(child.attrib.get('refer') or '').upper()
   if inline_id!=edge.get('managed_inline_id') or refer_id!=edge.get('managed_refer_id'):raise RuntimeError(f'Managed edge order differs for {record["record_key"]}:{ordinal}')
   description=child.attrib.get('describe','')
   subtasks.append({'ordinal':ordinal,'inline_id':inline_id,'inline_name':child.attrib.get('name','').strip(),
                    'level_gates':inline_level_gates(child),'description_sha256':hashlib.sha256(description.encode('utf-8')).hexdigest(),
                    'standalone_target_id':refer_id,'standalone_name':edge.get('standalone_name'),
                    'semantic_join_status':edge.get('semantic_join_status'),'standalone_content_usable':edge.get('standalone_content_usable'),
                    'source_locator':{'path':jxlab.rel(xml_path),'sha256':jxlab.sha256_file(xml_path),'locator':f'/Task/Managed/Sub[{ordinal}]'}})
  levels=[level for subtask in subtasks for level in subtask['level_gates']]
  phase=next(row for row in POST50_PHASES if task_id in row['task_ids'])
  families.append({'narrative_order':narrative_order,'task_id':task_id,'record_key':record['record_key'],'name':record['name'],
                   'phase_id':phase['phase_id'],'min_level_gate':min(levels),'max_level_gate':max(levels),
                   'managed_inline_count':len(subtasks),'managed_subtasks':subtasks,'source_records':record['source_records']})
 if sum(row['managed_inline_count'] for row in families)!=77:raise RuntimeError('Expected 77 post-50 managed inline subtasks')
 unsafe=[subtask for family in families for subtask in family['managed_subtasks'] if not subtask['standalone_content_usable']]
 if len(unsafe)!=77 or any(row['semantic_join_status']!='ID_REUSE_VARIANT' for row in unsafe):raise RuntimeError('Expected all 77 post-50 standalone joins to be blocked as ID reuse variants')
 return {**meta(),'reconstruction_id':'level-50-89-mainline','title':'Post-50 cross-narrative reconstruction','level_gate_span':'49-89',
         'authority_boundary':{'primary_detail_source':'RAW_CLIENT wrapper-inline Managed/Sub records','internet_role':'architecture, prerequisite and named-release corroboration only',
                               'standalone_subtask_rule':'Standalone content is excluded whenever semantic_join_status is ID_REUSE_VARIANT.'},
         'architecture_evidence':[live('KX-ARCH-01'),live('KX-PRE50-01'),live('KX-POST50-PATCH-01')],
         'macro_task_order':list(POST50_TASK_ORDER),'family_count':len(families),'managed_inline_subtask_count':77,
         'blocked_standalone_join_count':len(unsafe),'phases':POST50_PHASES,'task_families':families,
         'search_audit':POST50_SEARCH_AUDIT,
         'conclusion':'The three regional routes are pre-50 selectors. After their convergence, levels 49-89 form one shared cross-narrative represented by the ordered wrapper families; no second three-route choice at level 50 is supported.'}

CLAIMS=[
 ('IR001','Du Long Giác is tied to Tống Thái Tổ, more than twenty recruited masters, and a complementary secret retained by their descendants.','VERIFIED_CROSS_SOURCE',['arc-00'], 'CORE_WORLD_MACGUFFIN','MATERIAL',[pkg('evidence/evidence-ledger.md','lines 5-6','KX-BG-01'),live('KX-BG-01'),dialogue('sub:000000000000003F')]),
 ('IR002','Xoyo dates the relic reappearance to spring 1189 at the former Nam Chiếu palace; the local task corpus independently preserves the relic-triggered Thúy Yên disaster.','STRONG',['arc-00'],'CORE_OPENING_CHRONOLOGY','MATERIAL',[pkg('04-complete-chronological-timeline.md','lines 10-11','KX-BG-01'),live('KX-BG-01'),task(12)]),
 ('IR003','The intended architecture has three regional mainlines—Giang Nam, Trung Nguyên and Tây Nam—and post-50 cross-narrative; the Lab contains the three matching route selectors.','VERIFIED_CROSS_SOURCE',['arc-01','arc-02','arc-03','arc-04','arc-06'],'CORE_STORY_ARCHITECTURE','MATERIAL',[pkg('13-bibliography.md','lines 17-21','KX-ARCH-01'),live('KX-ARCH-01'),sub(314),sub(315),sub(316)]),
 ('IR004','Bạch Thu Lâm/Thu Di onboards the player into Nghĩa Quân and remains the player’s principal mission authority.','VERIFIED_CROSS_SOURCE',['arc-01','arc-07'],'CORE_PLAYER_POSITION','MATERIAL',[pkg('evidence/evidence-ledger.md','line 9','KX-90-01'),live('VNG-BTL-01'),dialogue('sub:0000000000000001')]),
 ('IR005','The recovered pre-50 convergence gate is Chuyện Cũ Thần Châu/神州往事 and the contemporary patch mirror states that pre-50 mainline completion is required.','STRONG',['arc-05'],'CORE_CONVERGENCE_GATE','MATERIAL',[pkg('13-bibliography.md','lines 28-31','KX-PRE50-01'),live('KX-PRE50-01'),sub(360)]),
 ('IR006','The Đại Lý story binds Du Long Giác, the Thúy Yên disaster, La Tuyết, Đoàn Trí Hưng and later Ô Man/war pressure; the detailed official-special claim remains partly image-only online.','STRONG',['arc-09'],'CORE_HIGH_LEVEL_ARC','MATERIAL',[pkg('evidence/evidence-ledger.md','lines 10-13','KX-110-01'),live('KX-110-01'),task(12),dialogue('sub:00000000000001EA')]),
 ('IR007','The northern mission arc involves Nghĩa Quân intelligence, Doãn Tiểu Vũ, Gia Luật Sở Tài and Hoàn Nhan Tương; its official special is live but detailed text is image-only.','STRONG',['arc-10'],'CORE_HIGH_LEVEL_ARC','MATERIAL',[pkg('evidence/evidence-ledger.md','lines 14-15','KX-120-01'),live('KX-120-01'),dialogue('sub:0000000000000216'),dialogue('sub:0000000000000213')]),
 ('IR008','A contemporary quest record says a Jin defense map is returned to Bạch Thu Lâm at the end of the northern arc.','INFERENCE',['arc-10'],'SUPPORTING_ARC_OUTCOME','POSSIBLE',[pkg('13-bibliography.md','lines 129-131','KX-120-02')]),
 ('IR009','Hàn Thác Trụ chooses Northern Expedition amid political pressure, while the Lab independently preserves the Khánh Nguyên purge and northern-war preparation.','VERIFIED_CROSS_SOURCE',['arc-07','arc-11'],'CORE_HIGH_LEVEL_ARC','MATERIAL',[pkg('evidence/evidence-ledger.md','line 17','KX-130-01'),live('KX-130-01'),dialogue('sub:000000000000019F'),dialogue('sub:000000000000024F')]),
 ('IR010','The live Xoyo 135/140 special places Linh Bích, Ngô Hi treason and the sect conflict in the 1205 Northern Expedition.','VERIFIED_DIRECT',['arc-12'],'CORE_ENDPOINT_ARC','MATERIAL',[pkg('evidence/evidence-ledger.md','lines 18-19','KX-140-01'),live('KX-140-01')]),
 ('IR011','The live Xoyo dream page shows child Bạch Thu Lâm and states that the player meets biological parents in an illusion; names and lineage are not supplied.','VERIFIED_DIRECT',['arc-12'],'CORE_PLAYER_IDENTITY_REVEAL','MATERIAL',[pkg('evidence/evidence-ledger.md','lines 20-21','KX-140-02'),live('KX-140-02'),task(157),dialogue('sub:0000000000000132')]),
 ('IR012','The same release is marketed as level 140 while the live task page gives a level-135 gate and opening task Như Hỏa Như Đồ/如火如荼.','VERIFIED_DIRECT',['arc-12'],'RELEASE_METADATA','NONE',[pkg('evidence/evidence-ledger.md','line 22','KX-140-03'),live('KX-140-03')]),
 ('IR013','The Xoyo chronicle is supporting chronology and roadmap evidence, not proof that every 1194–1212 event shipped as a player quest.','STRONG',['endpoint'],'SUPPORTING_CHRONOLOGY','POSSIBLE',[pkg('04-complete-chronological-timeline.md','lines 13,20,24,32','KX-CHRON-01')]),
 ('IR014','The Yên Vũ route uses the Mộc Nhất Lâu cover identity and contact with Ân Đồng; a contemporary retelling and raw dialogue independently preserve these beats.','VERIFIED_CROSS_SOURCE',['arc-02'],'IMPORTANT_PRE50_RECOVERY','MATERIAL',[pkg('13-bibliography.md','lines 113-117','KX-YANYU-01'),live('KX-YANYU-01'),dialogue('sub:0000000000000027'),dialogue('sub:0000000000000020')]),
 ('IR015','The Lab contains a main-class Man Thiên Quá Hải task and direct dialogue about covertly returning Chu lão tiên sinh to Lâm An; this resolves more than the web title alone but not the complete level-100 chain.','VERIFIED_DIRECT',['arc-08'],'CORE_HIGH_LEVEL_ARC','MATERIAL',[pkg('evidence/quest-records.md','lines 28-30','KX-100-01'),task(294),sub(469),dialogue('sub:00000000000001D5')]),
 ('IR016','VNG uses Doãn Tiểu Vũ and Bạch Thu Lâm/Nghĩa Quân naming, matching names in the raw Vietnamese task corpus; the 2012 newbie material is later-edition drift only.','VERIFIED_CROSS_SOURCE',['arc-01','arc-10'],'NORMALIZATION_AND_EDITION','NONE',[pkg('13-bibliography.md','lines 89-99','VNG-NAME-01'),live('VNG-NAME-01'),live('VNG-BTL-01'),live('VNG-DRIFT-01'),task(12),dialogue('sub:0000000000000001')]),
 ('IR017','Linh Bích is the latest original-era official story release located by this research package; this is a source-constrained endpoint, not proof of final closure.','STRONG',['endpoint'],'RELEASE_AUDIT_CONCLUSION','MATERIAL',[pkg('03-main-story/ending-and-endpoint.md','lines 3-9','KX-140-01'),live('KX-140-01')]),
 ('IR018','The Lab contains twelve main-class wrapper families with 77 managed inline subtasks and executable level gates spanning 49–89. Their macro order is 13→14→15→17→16→18→21→19→20→22→23→24. All 77 inline labels differ from the same-ID standalone records, so the wrapper descriptions are primary for this chain and standalone content is excluded.','VERIFIED_DIRECT',['arc-06'],'CORE_MISSING_CHAIN_RECOVERY','MATERIAL',[*[task(i) for i in POST50_TASK_ORDER],graph_evidence('77 explicit manages_sub wrapper records; semantic join blocked where label_relation is VARIANT')]),
 ('IR019','The raw Binh Qua route is not title-only: main task families 6–9 preserve Tây Hạ/Nhất Phẩm Đường, Võ Đang and northern political threads, though a complete cross-family causal order remains uncertain.','VERIFIED_DIRECT',['arc-03'],'IMPORTANT_PRE50_RECOVERY','MATERIAL',[task(6),task(7),task(8),task(9)]),
 ('IR020','The raw Tây Nam route preserves task families 10–12 around Ngô Hi, Đường Môn, Thúy Yên, La Tuyết and Du Long Giác; an early literal death of Ngô Hi cannot override the later official 1205 treason arc.','VERIFIED_CROSS_SOURCE',['arc-04','arc-12'],'IMPORTANT_PRE50_RECOVERY','MATERIAL',[task(10),task(11),task(12),live('KX-140-01')]),
 ('IR021','The raw Thân Thế Chi Mê family says Bạch Thu Lâm withheld complicated information about the player’s parents and later refers to their spirits; it does not name them or prove the player’s guardian lineage.','VERIFIED_DIRECT',['arc-01','arc-12'],'CORE_PLAYER_IDENTITY_REVEAL','MATERIAL',[task(157),dialogue('sub:0000000000000132'),dialogue('sub:0000000000000186')]),
 ('IR022','The level-gated wrapper sequence 13→14→15 (49–58) sends the player to locate and protect Gia Vương, counters Lý Hậu’s intervention and ends with Gia Vương taking the throne.','VERIFIED_DIRECT',['arc-06'],'CORE_POST50_SUCCESSION_CHAIN','MATERIAL',[task(13),task(14),task(15),graph_evidence('wrapper-inline names, descriptions and TaskCond:IsLevelAE gates for task IDs 13,14,15')]),
 ('IR023','The wrapper sequence 17→16→18 (58–69) investigates a Đường Môn insider and a Du Long diagram through Lý Nguyên Triết, Đường Khuyết, Nạp Tư and Hắc Long Đàm, then records the relic theft at Điểm Thương.','VERIFIED_DIRECT',['arc-06'],'CORE_POST50_RELIC_CHAIN','MATERIAL',[task(17),task(16),task(18),graph_evidence('wrapper-inline names, descriptions and TaskCond:IsLevelAE gates for task IDs 17,16,18')]),
 ('IR024','The wrapper sequence 21→19→20 (69–79) follows an Ngô Hi information leak into a cross-faction pursuit involving Cái Bang, Ngũ Độc, Jin-linked actors, Tây Hạ and Nhất Phẩm Đường.','VERIFIED_DIRECT',['arc-06'],'CORE_POST50_PURSUIT_CHAIN','MATERIAL',[task(21),task(19),task(20),graph_evidence('wrapper-inline names, descriptions and TaskCond:IsLevelAE gates for task IDs 21,19,20')]),
 ('IR025','The wrapper sequence 22→23→24 (79–89) moves from the Du Long recovery effort through an attack on Nghĩa Quân and a contested treasure cave involving Hoàn Nhan Tương, ending at Đại Nghĩa Nước Nhà; a contemporary Xoyo patch independently names the mainline task 家国大义.','VERIFIED_CROSS_SOURCE',['arc-06'],'CORE_POST50_ENDPOINT_CHAIN','MATERIAL',[task(22),task(23),task(24),graph_evidence('wrapper-inline names, descriptions and TaskCond:IsLevelAE gates for task IDs 22,23,24'),live('KX-POST50-PATCH-01')]),
]

ARC_SPECS=[
 ('arc-00','Du Long Giác prologue and world crisis','pre-opening/1189',['IR001','IR002']),
 ('arc-01','Player opening and Bạch Thu Lâm','opening',['IR003','IR004','IR021']),
 ('arc-02','Yên Vũ Giang Nam','pre-50 regional',['IR003','IR014']),
 ('arc-03','Binh Qua Trung Nguyên','pre-50 regional',['IR003','IR019']),
 ('arc-04','Tây Nam Mê Cảnh','pre-50 regional',['IR003','IR020']),
 ('arc-05','Chuyện Cũ Thần Châu convergence','pre-50 convergence',['IR005']),
 ('arc-06','Post-50 cross-narrative','level gates 49-89',['IR003','IR022','IR023','IR024','IR025','IR018']),
 ('arc-07','Khánh Nguyên and Nghĩa Quân','level 90',['IR004','IR009']),
 ('arc-08','Man Thiên Quá Hải','level 100',['IR015']),
 ('arc-09','Đại Lý crisis','level 110',['IR006']),
 ('arc-10','Northern intelligence and Vọng Long Sơn','level 120',['IR007','IR008','IR016']),
 ('arc-11','Decision for Northern Expedition','level 130',['IR009']),
 ('arc-12','Linh Bích and player-origin reveal','level 135/140',['IR010','IR011','IR012','IR020','IR021']),
 ('endpoint','Verified publication endpoint','post-135/140 boundary',['IR013','IR017']),
]

UNRESOLVED=[
 {'question_id':'parents-identities','status':'UNKNOWN','centrality':'CENTRAL_TOLERABLE','question':'What are the names, affiliations and exact fate of the player’s biological parents?','impact':'Identity details cannot be fixed in future canon; the evidenced reveal still functions.'},
 {'question_id':'player-guardian-lineage','status':'UNKNOWN','centrality':'CENTRAL_TOLERABLE','question':'Is the player demonstrably one of the guardian-descendant lines?','impact':'Do not equate the player with a specific lineage.'},
 {'question_id':'du-long-final-secret','status':'UNKNOWN','centrality':'CENTRAL_TOLERABLE','question':'What is the final combined meaning and outcome of Du Long Giác and the descendants’ secret?','impact':'The macguffin can be promoted only as an unresolved long mystery.'},
 {'question_id':'bingge-full-order','status':'UNKNOWN','centrality':'CENTRAL_TOLERABLE','question':'What is the complete cross-family causal order of Binh Qua Trung Nguyên?','impact':'Raw families are usable; uncertain bridges remain excluded.'},
 {'question_id':'post50-micro-dialogue-recovery','status':'UNKNOWN','centrality':'CENTRAL_TOLERABLE','question':'Can the exact objectives and dialogue for all 77 post-50 wrapper-inline subtasks be recovered without joining unrelated same-ID standalone records?','impact':'The macro causality and level-gated order are usable; standalone dialogue and objectives remain excluded unless separately reconciled.'},
 {'question_id':'level100-full-chain','status':'UNKNOWN','centrality':'CENTRAL_TOLERABLE','question':'What is the complete Man Thiên Quá Hải chain beyond the recovered local task node?','impact':'Use the recovered covert-return beat only.'},
 {'question_id':'returning-woman-identity','status':'UNKNOWN','centrality':'CENTRAL_TOLERABLE','question':'Is the unnamed returning woman at Linh Bích definitely Ân Đồng?','impact':'Keep the identity as inference, not canon fact.'},
 {'question_id':'post-lingbi-continuation','status':'UNKNOWN','centrality':'CENTRAL_TOLERABLE','question':'Which later coherent edition, if any, resolves the post-Linh-Bích story and Du Long Giác?','impact':'The promoted corpus ends at a continuation point.'},
]

CONFLICTS=[
 {'conflict_id':'chronology-1189-later-events','status':'CONFLICT','narrative_impact':'POSSIBLE','resolution_status':'DOCUMENTED','handling':'Preserve Xoyo dates; do not silently repair them with external history.'},
 {'conflict_id':'wu-xi-early-death','status':'CONFLICT','narrative_impact':'MATERIAL','resolution_status':'RESOLVED','handling':'Later first-party 1205 arc controls; early wording is not a canonical death.'},
 {'conflict_id':'level-140-marketing-135-gate','status':'EDITION_DRIFT','narrative_impact':'NONE','resolution_status':'RESOLVED','handling':'One arc: marketed as 140, mechanically gated at 135.'},
 {'conflict_id':'youlong-jue-character','status':'CONFLICT','narrative_impact':'POSSIBLE','resolution_status':'DOCUMENTED','handling':'Keep 游龙诀 variant separate; global relic remains 游龙珏.'},
 {'conflict_id':'managed-sub-label-variants','status':'CONFLICT','narrative_impact':'POSSIBLE','resolution_status':'DOCUMENTED','handling':'Preserve wrapper inline name/description and standalone target name separately. Structural target resolution is retained, but all 77 post-50 VARIANT joins are semantically blocked from importing standalone content.'},
]

def main():
 if not PACKAGE.exists():raise SystemExit('Missing private-input/internet-research package')
 OUT.mkdir(parents=True,exist_ok=True);DOSSIERS.mkdir(parents=True,exist_ok=True)
 package_files=[]
 for path in sorted(p for p in PACKAGE.rglob('*') if p.is_file()):
  data=path.read_bytes();data.decode('utf-8')
  package_files.append({'path':jxlab.rel(path),'size':len(data),'sha256':hashlib.sha256(data).hexdigest()})
 post50_reconstruction=build_post50_reconstruction()
 write_json(ROOT/'research'/'reconstruction'/'level-50-89-mainline.json',post50_reconstruction)
 write_json(OUT/'level-50-89-internet-search-ledger.json',{**meta(),**POST50_SEARCH_AUDIT})
 claims=[]
 for claim_id,text,status,arc_ids,centrality,impact,evidence_rows in CLAIMS:
  claims.append({'claim_id':claim_id,'claim':text,'status':status,'claim_kind':'narrative_lore','arc_ids':arc_ids,'centrality':centrality,'narrative_impact':impact,'evidence':evidence_rows})
 claims_path=OUT/'internet-research-claims.jsonl'
 with claims_path.open('w',encoding='utf-8',newline='\n') as output:
  for claim in claims:output.write(json.dumps(claim,ensure_ascii=False,separators=(',',':'))+'\n')
 claim_ids={claim['claim_id'] for claim in claims}
 dossiers=[]
 for arc_id,title,level,refs in ARC_SPECS:
  assert set(refs)<=claim_ids
  unresolved=[q['question_id'] for q in UNRESOLVED if (arc_id in {'arc-01','arc-12'} and q['question_id'] in {'parents-identities','player-guardian-lineage'}) or (arc_id=='arc-03' and q['question_id']=='bingge-full-order') or (arc_id=='arc-06' and q['question_id']=='post50-micro-dialogue-recovery') or (arc_id=='arc-08' and q['question_id']=='level100-full-chain') or (arc_id=='endpoint' and q['question_id'] in {'du-long-final-secret','post-lingbi-continuation'})]
  material=[row['conflict_id'] for row in CONFLICTS if row['narrative_impact']=='MATERIAL' and arc_id in {'arc-04','arc-12'}]
  event_refs=['IR022','IR023','IR024','IR025'] if arc_id=='arc-06' else refs
  dossier={**meta(),'dossier_id':f'dossier-{arc_id}','arc_id':arc_id,'title':title,'chronology_or_level_range':level,
           'premise_claim_ids':refs[:1],'character_and_faction_claim_ids':refs,'goal_and_motive_claim_ids':refs,
           'ordered_events':[{'order':index+1,'claim_id':claim_id,'ordering_basis':'wrapper-inline TaskCond:IsLevelAE gates and managed order' if arc_id=='arc-06' else 'evidence grouping; no missing bridge inferred'} for index,claim_id in enumerate(event_refs)],
           'player_learns_claim_ids':refs,'reveal_claim_ids':refs,'climax_resolution_claim_ids':refs[-1:],
           'consequence_claim_ids':refs[-1:],'important_named_reference_claim_ids':refs,
           'central_unknown_ids':unresolved,'material_conflict_ids':material,'promotion_status':'PROMOTABLE_WITH_DOCUMENTED_UNKNOWNS'}
  if arc_id=='arc-06':
   dossier['evidence_limit_claim_ids']=['IR018'];dossier['reconstruction_path']='research/reconstruction/level-50-89-mainline.json'
  path=DOSSIERS/f'{arc_id}.json';write_json(path,dossier);dossiers.append({'arc_id':arc_id,'path':jxlab.rel(path),'sha256':jxlab.sha256_file(path),'claim_ids':refs,'central_unknown_ids':unresolved,'material_conflict_ids':material})
 blocker_count=sum(q['centrality']=='CENTRAL_BLOCKER' for q in UNRESOLVED)
 unresolved_material=sum(row['narrative_impact']=='MATERIAL' and row['resolution_status']!='RESOLVED' for row in CONFLICTS)
 gates={'S3':{'status':'PASS','basis':'All declared main arcs have claim-linked source-only dossiers; central unknowns are explicit.'},
        'S4':{'status':'PASS','basis':'All load-bearing research claims are reconciled; no unresolved MATERIAL narrative conflict remains.'},
        'S5':{'status':'PASS','basis':'Curated claims, concordance, dossiers, unresolved ledger and confidence inputs are complete for release validation.'}}
 decision='NOVEL_PROMOTION_READY' if not blocker_count and not unresolved_material and all(row['status']=='PASS' for row in gates.values()) else 'NOVEL_PROMOTION_NOT_READY'
 managed=[row for row in EDGES if row['relation']=='manages_sub']
 core_keys={'task:000000000000000D:entry:f66eae4a','task:000000000000000E:entry:f350f967','task:000000000000000F:entry:cc5a3074','task:0000000000000010:entry:bd780c88','task:0000000000000011:entry:be6247a5','task:0000000000000012:entry:bb6b9eb2','task:0000000000000013:entry:b45d29cf','task:0000000000000014:entry:b14760dc','task:0000000000000015:entry:b248bbe9','task:0000000000000016:entry:8fb2f206'}
 core=[row for row in managed if row['source_key'] in core_keys]
 post50_keys={main_task_record(task_id)['record_key'] for task_id in POST50_TASK_ORDER}
 post50=[row for row in managed if row['source_key'] in post50_keys]
 structural_audit={'managed_label_relation_counts':dict(Counter(row.get('label_relation','NOT_RECORDED') for row in managed)),
                   'core_50_80':{'managed_edges':len(core),'label_variants':sum(row.get('label_relation')=='VARIANT' for row in core),
                                 'explicit_refer_matches':sum(row.get('managed_refer_id')==row['target_key'].removeprefix('sub:') for row in core),
                                 'semantic_joins_blocked':sum(row.get('standalone_content_usable') is False for row in core),
                                 'handling':'Explicit same-archive refer links are structural. Inline wrapper labels and standalone target labels remain separate evidence fields.'},
                   'post50_49_89':{'managed_edges':len(post50),'label_variants':sum(row.get('label_relation')=='VARIANT' for row in post50),
                                  'id_reuse_variants':sum(row.get('semantic_join_status')=='ID_REUSE_VARIANT' for row in post50),
                                  'semantic_joins_blocked':sum(row.get('standalone_content_usable') is False for row in post50),
                                  'macro_task_order':list(POST50_TASK_ORDER),'handling':'Wrapper-inline evidence controls narrative reconstruction; unrelated same-ID standalone content is excluded.'}}
 concordance={**meta(),'package_inventory':{'file_count':len(package_files),'total_bytes':sum(row['size'] for row in package_files),'files':package_files},
              'claim_status_counts':dict(Counter(row['status'] for row in claims)),'claims':[{'claim_id':row['claim_id'],'status':row['status'],'arc_ids':row['arc_ids'],'centrality':row['centrality'],'narrative_impact':row['narrative_impact'],'source_families':sorted({e['source_family'] for e in row['evidence']})} for row in claims],
              'structural_audit':structural_audit,'conflicts':CONFLICTS,'unresolved_questions':UNRESOLVED,'central_blocker_count':blocker_count,'unresolved_material_conflict_count':unresolved_material,
              'promotion_gates':gates,'promotion_decision':decision}
 write_json(OUT/'lore-concordance.json',concordance)
 index={**meta(),'dossier_count':len(dossiers),'declared_arcs':[row[0] for row in ARC_SPECS],'dossiers':dossiers,'promotion_decision':decision}
 write_json(DOSSIERS/'index.json',index)
 report={**meta(),'package_files':len(package_files),'claims':len(claims),'dossiers':len(dossiers),'claim_status_counts':dict(Counter(row['status'] for row in claims)),'central_blockers':blocker_count,'unresolved_material_conflicts':unresolved_material,'post50_task_families':post50_reconstruction['family_count'],'post50_managed_inline_subtasks':post50_reconstruction['managed_inline_subtask_count'],'post50_blocked_standalone_joins':post50_reconstruction['blocked_standalone_join_count'],'promotion_decision':decision}
 write_json(ROOT/'generated/reports/internet-reconciliation-report.json',report)
 print(json.dumps(report,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
