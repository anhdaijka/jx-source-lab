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
SCHEMA_VERSION='2.0'
SOURCE_EVIDENCE_COMMIT='8d7645a4d659d0baac86c9eafc7fc0ef18c90254'
ENTITY_ID_CANONICAL={
 'faction:duong-mon':'sect:3','faction:ngu-doc':'sect:4','faction:thuy-yen':'sect:6',
 'faction:cai-bang':'sect:7','faction:thien-nhan':'sect:8',
}

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

PLOT_THREADS=[
 {'thread_id':'thread:du-long-relic','canonical_label':'Du Long relic and complementary secret','type':'ARTIFACT_MYSTERY','status':'OPEN_IN_SOURCE','participant_entity_ids':['character:game-player','faction:thuy-yen','faction:duong-mon'],'intersection_thread_ids':['thread:thuy-yen-dali','thread:post50-cross-narrative'],'first_setup':{'arc_id':'arc-00','summary':'The relic and a complementary descendants secret are established in the world background.','claim_ids':['IR001']},'developments':[{'arc_id':'arc-00','summary':'The relic reappears at Nam Chieu and is independently tied to the Thuy Yen disaster.','claim_ids':['IR002']},{'arc_id':'arc-04','summary':'The southwest route preserves Du Long and Thuy Yen material.','claim_ids':['IR020']},{'arc_id':'arc-06','summary':'A diagram investigation, theft, pursuit and recovery conflict carry the relic through the post-50 chain.','claim_ids':['IR023','IR024','IR025']},{'arc_id':'arc-09','summary':'The Dali material reconnects the relic to the Thuy Yen disaster and regional war pressure.','claim_ids':['IR006']}],'reversals_or_reframes':[],'payoff':None,'downstream_residue':'The final combined meaning and outcome remain explicitly unknown.','unresolved_question_ids':['du-long-final-secret'],'claim_ids':['IR001','IR002','IR006','IR020','IR023','IR024','IR025']},
 {'thread_id':'thread:player-origin','canonical_label':'Player parentage and origin','type':'IDENTITY_MYSTERY','status':'OPEN_IN_SOURCE','participant_entity_ids':['character:game-player','character:bach-thu-lam','character:biological-parents','character:bach-cuong'],'intersection_thread_ids':['thread:nghia-quan-service'],'first_setup':{'arc_id':'arc-01','summary':'Bach Thu Lam withholds complicated information about the player parents.','claim_ids':['IR021']},'developments':[{'arc_id':'arc-01','summary':'The recovered family chain establishes unnamed parents and incomplete fate information without proving a guardian lineage.','claim_ids':['IR021']},{'arc_id':'arc-12','summary':'The player encounters the biological parents in an illusion, but their names and lineage remain unstated.','claim_ids':['IR011']}],'reversals_or_reframes':[],'payoff':{'arc_id':'arc-12','summary':'The illusion confirms the biological-parent connection but does not close the identity mystery.','claim_ids':['IR011']} ,'downstream_residue':'Parents names, affiliations, exact fate and guardian-lineage connection remain unknown.','unresolved_question_ids':['parents-identities','player-guardian-lineage'],'claim_ids':['IR011','IR021']},
 {'thread_id':'thread:regional-branches','canonical_label':'Three regional mainlines and convergence','type':'STORY_ARCHITECTURE','status':'LOCALLY_RESOLVED','participant_entity_ids':['character:game-player'],'intersection_thread_ids':['thread:post50-cross-narrative'],'first_setup':{'arc_id':'arc-01','summary':'The source architecture and three matching route selectors establish the regional choice.','claim_ids':['IR003']},'developments':[{'arc_id':'arc-02','summary':'Yen Vu Giang Nam is one selectable regional route.','claim_ids':['IR003','IR014']},{'arc_id':'arc-03','summary':'Binh Qua Trung Nguyen is one selectable regional route.','claim_ids':['IR003','IR019']},{'arc_id':'arc-04','summary':'Tay Nam Me Canh is one selectable regional route.','claim_ids':['IR003','IR020']},{'arc_id':'arc-05','summary':'Pre-50 completion leads to the recovered Than Chau convergence gate.','claim_ids':['IR005']}],'reversals_or_reframes':[],'payoff':{'arc_id':'arc-05','summary':'The three-route architecture converges before the shared post-50 sequence.','claim_ids':['IR003','IR005']},'downstream_residue':'The complete micro-order inside Binh Qua remains bounded as unknown.','unresolved_question_ids':['bingge-full-order'],'claim_ids':['IR003','IR005','IR014','IR019','IR020']},
 {'thread_id':'thread:post50-cross-narrative','canonical_label':'Shared post-50 succession, relic and pursuit chain','type':'POLITICAL_ARTIFACT','status':'LOCALLY_RESOLVED','participant_entity_ids':['character:game-player','character:gia-vuong','character:ly-hau','character:ly-nguyen-triet','character:duong-khuyet','character:nap-tu','character:ngo-hi','character:hoan-nhan-tuong','faction:nghia-quan','faction:kim','faction:tay-ha','faction:nhat-pham-duong'],'intersection_thread_ids':['thread:du-long-relic','thread:southern-song-war','thread:nghia-quan-service','thread:ngo-hi-status'],'first_setup':{'arc_id':'arc-06','summary':'A validated twelve-family wrapper sequence establishes the shared level 49-89 order.','claim_ids':['IR018']},'developments':[{'arc_id':'arc-06','summary':'The player protects Gia Vuong and counters Ly Hau until the accession.','claim_ids':['IR022']},{'arc_id':'arc-06','summary':'The chain turns to a Du Long diagram investigation and theft.','claim_ids':['IR023']},{'arc_id':'arc-06','summary':'An Ngo Hi leak drives a cross-faction pursuit into Tay Ha.','claim_ids':['IR024']},{'arc_id':'arc-06','summary':'Recovery, an attack on Nghia Quan and a contested treasure cave close the promoted macro-chain.','claim_ids':['IR025']}],'reversals_or_reframes':[],'payoff':{'arc_id':'arc-06','summary':'The validated macro-chain ends at Dai Nghia Nuoc Nha while the relic mystery remains open.','claim_ids':['IR025']},'downstream_residue':'Exact dialogue/objectives for wrapper-inline subtasks remain excluded because of ID reuse variants.','unresolved_question_ids':['post50-micro-dialogue-recovery'],'claim_ids':['IR018','IR022','IR023','IR024','IR025']},
 {'thread_id':'thread:nghia-quan-service','canonical_label':'Player service under Nghia Quan','type':'FACTIONAL','status':'OPEN_IN_SOURCE','participant_entity_ids':['character:game-player','character:bach-thu-lam','character:doan-tieu-vu','faction:nghia-quan','faction:nhat-pham-duong'],'intersection_thread_ids':['thread:player-origin','thread:post50-cross-narrative','thread:northern-war'],'first_setup':{'arc_id':'arc-01','summary':'Bach Thu Lam brings the player into Nghia Quan and acts as mission authority.','claim_ids':['IR004']},'developments':[{'arc_id':'arc-06','summary':'Nghia Quan is attacked during the relic-recovery chain.','claim_ids':['IR025']},{'arc_id':'arc-07','summary':'Bach Thu Lam remains the player mission authority.','claim_ids':['IR004']},{'arc_id':'arc-10','summary':'Nghia Quan intelligence and Doan Tieu Vu support the northern mission.','claim_ids':['IR007','IR016']}],'reversals_or_reframes':[],'payoff':None,'downstream_residue':'The organization remains active at the supported endpoint.','unresolved_question_ids':[],'claim_ids':['IR004','IR007','IR016','IR025']},
 {'thread_id':'thread:ngo-hi-status','canonical_label':'Ngo Hi status, leak and treason','type':'POLITICAL_BETRAYAL','status':'RESOLVED','participant_entity_ids':['character:ngo-hi','character:game-player','faction:nam-tong'],'intersection_thread_ids':['thread:post50-cross-narrative','thread:southern-song-war'],'first_setup':{'arc_id':'arc-04','summary':'The southwest route preserves Ngo Hi material; an early literal-death reading is rejected by later first-party evidence.','claim_ids':['IR020']},'developments':[{'arc_id':'arc-06','summary':'An Ngo Hi information leak initiates a cross-faction pursuit.','claim_ids':['IR024']},{'arc_id':'arc-12','summary':'The official 1205 arc identifies Ngo Hi treason in the Northern Expedition conflict.','claim_ids':['IR010']}],'reversals_or_reframes':[{'arc_id':'arc-12','summary':'Later first-party evidence controls over the early literal-death wording.','claim_ids':['IR010','IR020']}],'payoff':{'arc_id':'arc-12','summary':'Ngo Hi is placed as a treason actor in the 1205 campaign.','claim_ids':['IR010']},'downstream_residue':'No fabricated fake-death mechanism is asserted.','unresolved_question_ids':[],'claim_ids':['IR010','IR020','IR024']},
 {'thread_id':'thread:thuy-yen-dali','canonical_label':'Thuy Yen disaster and Dali consequences','type':'SECT_REGIONAL','status':'LOCALLY_RESOLVED','participant_entity_ids':['character:la-tuyet','character:doan-tri-hung','faction:thuy-yen'],'intersection_thread_ids':['thread:du-long-relic'],'first_setup':{'arc_id':'arc-00','summary':'The relic-triggered Thuy Yen disaster is preserved by the local task corpus.','claim_ids':['IR002']},'developments':[{'arc_id':'arc-04','summary':'The southwest route preserves Thuy Yen, La Tuyet and Du Long material.','claim_ids':['IR020']},{'arc_id':'arc-09','summary':'The Dali arc binds the disaster, La Tuyet, Doan Tri Hung and later war pressure.','claim_ids':['IR006']}],'reversals_or_reframes':[],'payoff':{'arc_id':'arc-09','summary':'The Dali material reconnects the early disaster to named regional actors and pressures.','claim_ids':['IR006']},'downstream_residue':'The final Du Long outcome remains open.','unresolved_question_ids':['du-long-final-secret'],'claim_ids':['IR002','IR006','IR020']},
 {'thread_id':'thread:southern-song-war','canonical_label':'Southern Song stability and Northern Expedition','type':'POLITICAL_WAR','status':'OPEN_IN_SOURCE','participant_entity_ids':['character:gia-vuong','character:ly-hau','character:han-thac-tru','character:ngo-hi','faction:nam-tong','faction:kim'],'intersection_thread_ids':['thread:post50-cross-narrative','thread:ngo-hi-status','thread:northern-war'],'first_setup':{'arc_id':'arc-06','summary':'The post-50 sequence resolves a Southern Song succession struggle around Gia Vuong.','claim_ids':['IR022']},'developments':[{'arc_id':'arc-07','summary':'The Khanh Nguyen purge and northern-war preparation are preserved in Lab evidence.','claim_ids':['IR009']},{'arc_id':'arc-11','summary':'Han Thac Tru chooses Northern Expedition amid political pressure.','claim_ids':['IR009']},{'arc_id':'arc-12','summary':'The 1205 campaign includes Linh Bich, Ngo Hi treason and sect conflict.','claim_ids':['IR010']}],'reversals_or_reframes':[],'payoff':None,'downstream_residue':'The located original-era source endpoint is a continuation point, not final closure.','unresolved_question_ids':['post-lingbi-continuation'],'claim_ids':['IR009','IR010','IR022']},
 {'thread_id':'thread:northern-war','canonical_label':'Northern intelligence and war preparation','type':'WAR_INTELLIGENCE','status':'LOCALLY_RESOLVED','participant_entity_ids':['character:game-player','character:doan-tieu-vu','character:gia-luat-so-tai','character:hoan-nhan-tuong','character:han-thac-tru','faction:nghia-quan','faction:kim','faction:nam-tong'],'intersection_thread_ids':['thread:nghia-quan-service','thread:southern-song-war'],'first_setup':{'arc_id':'arc-07','summary':'Northern-war preparation accompanies the Khanh Nguyen material.','claim_ids':['IR009']},'developments':[{'arc_id':'arc-10','summary':'Nghia Quan intelligence directs a northern mission involving Doan Tieu Vu, Gia Luat So Tai and Hoan Nhan Tuong.','claim_ids':['IR007','IR016']},{'arc_id':'arc-11','summary':'Han Thac Tru chooses Northern Expedition.','claim_ids':['IR009']},{'arc_id':'arc-12','summary':'The campaign reaches the Linh Bich conflict in 1205.','claim_ids':['IR010']}],'reversals_or_reframes':[],'payoff':{'arc_id':'arc-12','summary':'The prepared expedition becomes the evidenced 1205 campaign setting.','claim_ids':['IR010']},'downstream_residue':'Post-Linh-Bich continuation is not established by the promoted corpus.','unresolved_question_ids':['post-lingbi-continuation'],'claim_ids':['IR007','IR009','IR010','IR016']},
]

MYSTERIES=[
 {'mystery_id':'mystery:du-long-secret','question':'What is the combined meaning and final outcome of Du Long Giac and the descendants secret?','status':'TOLERATED_UNKNOWN','thread_ids':['thread:du-long-relic'],'unresolved_question_ids':['du-long-final-secret'],'phases':[{'phase_type':'SETUP','arc_id':'arc-00','summary':'The relic and complementary descendants secret are established.','claim_ids':['IR001']},{'phase_type':'CLUE','arc_id':'arc-00','summary':'The relic reappears at Nam Chieu and is linked to the Thuy Yen disaster.','claim_ids':['IR002']},{'phase_type':'CLUE','arc_id':'arc-06','summary':'A diagram, fragments, theft and recovery conflict expand the relic chain.','claim_ids':['IR023','IR024','IR025']},{'phase_type':'RESIDUE','arc_id':'endpoint','summary':'No promoted source establishes the final combined secret or outcome.','claim_ids':['IR017']}],'local_payoff':None,'downstream_consequence':'The relic remains an open source mystery and must not be resolved by the handoff.','claim_ids':['IR001','IR002','IR017','IR023','IR024','IR025']},
 {'mystery_id':'mystery:player-parents','question':'Who are the player biological parents and what happened to them?','status':'TOLERATED_UNKNOWN','thread_ids':['thread:player-origin'],'unresolved_question_ids':['parents-identities','player-guardian-lineage'],'phases':[{'phase_type':'SETUP','arc_id':'arc-01','summary':'Bach Thu Lam says the parent information is complicated and withholds details.','claim_ids':['IR021']},{'phase_type':'CLUE','arc_id':'arc-01','summary':'The recovered chain supplies partial history but no names or proven guardian lineage.','claim_ids':['IR021']},{'phase_type':'REVEAL','arc_id':'arc-12','summary':'The player meets the biological parents in an illusion; names and lineage remain absent.','claim_ids':['IR011']},{'phase_type':'PAYOFF','arc_id':'arc-12','summary':'Biological parentage is confirmed as the identity focus without resolving identity or fate.','claim_ids':['IR011','IR021']},{'phase_type':'RESIDUE','arc_id':'endpoint','summary':'Names, affiliations, exact fate and guardian-lineage identity remain unknown.','claim_ids':['IR011','IR021']}],'local_payoff':'The illusion confirms the parent connection, not the missing identities or fate.','downstream_consequence':'Any novel-side identity assignment requires a later explicit source/canon decision.','claim_ids':['IR011','IR021']},
 {'mystery_id':'mystery:ngo-hi-status','question':'How should the early Ngo Hi material be reconciled with the later campaign?','status':'RESOLVED','thread_ids':['thread:ngo-hi-status'],'unresolved_question_ids':[],'phases':[{'phase_type':'SETUP','arc_id':'arc-04','summary':'Early regional wording permits a literal-death reading.','claim_ids':['IR020']},{'phase_type':'CLUE','arc_id':'arc-06','summary':'An Ngo Hi information leak is part of the post-50 pursuit chain.','claim_ids':['IR024']},{'phase_type':'REVEAL','arc_id':'arc-12','summary':'Later first-party evidence places Ngo Hi alive as a treason actor in 1205.','claim_ids':['IR010']},{'phase_type':'PAYOFF','arc_id':'arc-12','summary':'The later official campaign controls; the early literal death is rejected.','claim_ids':['IR010','IR020']}],'local_payoff':'Ngo Hi is promoted as the later 1205 treason actor.','downstream_consequence':'No fake-death mechanism or unsupported bridge is introduced.','claim_ids':['IR010','IR020','IR024']},
 {'mystery_id':'mystery:du-long-diagram-theft','question':'Who drives the Du Long diagram theft and cross-faction pursuit?','status':'LOCALLY_RESOLVED','thread_ids':['thread:du-long-relic','thread:post50-cross-narrative'],'unresolved_question_ids':['post50-micro-dialogue-recovery'],'phases':[{'phase_type':'SETUP','arc_id':'arc-06','summary':'An insider and Du Long diagram investigation proceeds through named contacts and locations.','claim_ids':['IR023']},{'phase_type':'REVEAL','arc_id':'arc-06','summary':'The sequence records the relic theft at Diem Thuong.','claim_ids':['IR023']},{'phase_type':'CLUE','arc_id':'arc-06','summary':'An Ngo Hi leak leads to a cross-faction pursuit through Jin-linked and Tay Ha actors.','claim_ids':['IR024']},{'phase_type':'PAYOFF','arc_id':'arc-06','summary':'The chain moves through recovery, an attack on Nghia Quan and a contested treasure cave.','claim_ids':['IR025']},{'phase_type':'RESIDUE','arc_id':'arc-06','summary':'The exact wrapper micro-dialogue is excluded because same-ID standalone records are variants.','claim_ids':['IR018']}],'local_payoff':'The promoted macro-chain reaches recovery and the contested treasure cave.','downstream_consequence':'The global relic secret remains unresolved.','claim_ids':['IR018','IR023','IR024','IR025']},
 {'mystery_id':'mystery:returning-woman','question':'Is the unnamed returning woman at Linh Bich An Dong?','status':'TOLERATED_UNKNOWN','thread_ids':['thread:player-origin'],'unresolved_question_ids':['returning-woman-identity'],'phases':[{'phase_type':'SETUP','arc_id':'arc-02','summary':'An Dong is an evidenced contact in the Yen Vu route.','claim_ids':['IR014']},{'phase_type':'RESIDUE','arc_id':'arc-12','summary':'The later returning woman is not named by the promoted source claim; identity remains inference only.','claim_ids':['IR010']}],'local_payoff':None,'downstream_consequence':'The handoff must not identify the returning woman as An Dong.','claim_ids':['IR010','IR014']},
]

CHARACTER_TRAJECTORIES=[
 {'entity_id':'character:game-player','latest_source_backed_state':'Participant in the 1205 Linh Bich campaign and the parent-origin illusion; no novel identity is assigned.','unresolved_question_ids':['parents-identities','player-guardian-lineage','post-lingbi-continuation'],'stages':[{'arc_id':'arc-01','source_state':'Onboarded by Bach Thu Lam and offered three regional mainlines.','actions':['Enters the evidenced game-story route structure.'],'knowledge_changes':['Learns that parent information is being withheld as complicated.'],'relationship_changes':['Becomes subject to Bach Thu Lam mission authority.'],'claim_ids':['IR003','IR004','IR021']},{'arc_id':'arc-06','source_state':'Operative in the shared post-50 chain.','actions':['Protects Gia Vuong; investigates the Du Long diagram; follows the leak and recovery chain.'],'knowledge_changes':['Acquires source-backed information through the succession, theft and pursuit investigations.'],'relationship_changes':['Acts with and for Nghia Quan during the promoted chain.'],'claim_ids':['IR022','IR023','IR024','IR025']},{'arc_id':'arc-10','source_state':'Nghia Quan-linked northern operative.','actions':['Participates in the northern intelligence mission.'],'knowledge_changes':['Receives mission-relevant northern intelligence; exact image-only details remain bounded.'],'relationship_changes':[],'claim_ids':['IR007']},{'arc_id':'arc-12','source_state':'Campaign participant confronting origin evidence.','actions':['Participates in the Linh Bich conflict and encounters biological parents in an illusion.'],'knowledge_changes':['Biological parentage is presented, while names and lineage remain unknown.'],'relationship_changes':[],'claim_ids':['IR010','IR011']}]},
 {'entity_id':'character:bach-thu-lam','latest_source_backed_state':'Recurring Nghia Quan mission authority connected to the unresolved parentage thread.','unresolved_question_ids':['parents-identities','player-guardian-lineage'],'stages':[{'arc_id':'arc-01','source_state':'Caretaker/onboarding guide with incomplete disclosed parent information.','actions':['Brings the player into Nghia Quan and withholds complicated parent details.'],'knowledge_changes':['Is evidenced to know some parent information; exact extent is unknown.'],'relationship_changes':['Establishes caretaker and mission-authority relation to the player.'],'claim_ids':['IR004','IR021']},{'arc_id':'arc-07','source_state':'Principal mission authority.','actions':['Continues directing the player through Nghia Quan.'],'knowledge_changes':[],'relationship_changes':[],'claim_ids':['IR004']},{'arc_id':'arc-12','source_state':'Still connected to the player-origin reveal.','actions':[],'knowledge_changes':['The source does not establish that she discloses the parents names or full fate.'],'relationship_changes':[],'claim_ids':['IR011','IR021']}]},
 {'entity_id':'character:biological-parents','latest_source_backed_state':'Unnamed biological parents represented in the player illusion; exact identities and fate remain unknown.','unresolved_question_ids':['parents-identities','player-guardian-lineage'],'stages':[{'arc_id':'arc-01','source_state':'Absent parents known only through partial recovered testimony.','actions':[],'knowledge_changes':[],'relationship_changes':['Biological relation to the player is established; details remain incomplete.'],'claim_ids':['IR021']},{'arc_id':'arc-12','source_state':'Appear to the player in an illusion.','actions':[],'knowledge_changes':[],'relationship_changes':['Biological-parent connection is reaffirmed without names or lineage.'],'claim_ids':['IR011']}]},
 {'entity_id':'character:ngo-hi','latest_source_backed_state':'Treason actor in the official 1205 Northern Expedition conflict.','unresolved_question_ids':[],'stages':[{'arc_id':'arc-04','source_state':'Figure in the southwest route; early literal-death wording is not controlling canon.','actions':[],'knowledge_changes':[],'relationship_changes':[],'claim_ids':['IR020']},{'arc_id':'arc-06','source_state':'Source of an information leak in the promoted pursuit chain.','actions':['The leak initiates a cross-faction pursuit.'],'knowledge_changes':[],'relationship_changes':[],'claim_ids':['IR024']},{'arc_id':'arc-12','source_state':'Named treason actor in the 1205 campaign.','actions':['Participates in the Linh Bich/Northern Expedition conflict as a traitor.'],'knowledge_changes':[],'relationship_changes':['His relation to Southern Song is reframed as treason.'],'claim_ids':['IR010']}]},
 {'entity_id':'character:han-thac-tru','latest_source_backed_state':'Political leader committed to Northern Expedition in the promoted source chronology.','unresolved_question_ids':['post-lingbi-continuation'],'stages':[{'arc_id':'arc-07','source_state':'Political figure in the Khanh Nguyen purge and northern-war preparation context.','actions':[],'knowledge_changes':[],'relationship_changes':[],'claim_ids':['IR009']},{'arc_id':'arc-11','source_state':'Decision-maker under political pressure.','actions':['Chooses Northern Expedition.'],'knowledge_changes':[],'relationship_changes':['Directs Southern Song toward the northern campaign.'],'claim_ids':['IR009']}]},
 {'entity_id':'character:la-tuyet','latest_source_backed_state':'Named link between the southwest/Thuy Yen material and the Dali crisis.','unresolved_question_ids':['du-long-final-secret'],'stages':[{'arc_id':'arc-04','source_state':'Named in the southwest route around Thuy Yen and Du Long material.','actions':[],'knowledge_changes':[],'relationship_changes':[],'claim_ids':['IR020']},{'arc_id':'arc-09','source_state':'Participant in the Dali crisis chain.','actions':[],'knowledge_changes':[],'relationship_changes':['Connects the Dali material to the earlier Thuy Yen disaster context.'],'claim_ids':['IR006']}]},
 {'entity_id':'character:hoan-nhan-tuong','latest_source_backed_state':'Jin-linked actor in the northern mission and contested post-50 treasure conflict.','unresolved_question_ids':[],'stages':[{'arc_id':'arc-06','source_state':'Jin-linked participant in the contested treasure-cave endpoint.','actions':['Participates in the treasure conflict.'],'knowledge_changes':[],'relationship_changes':[],'claim_ids':['IR025']},{'arc_id':'arc-10','source_state':'Named figure in the northern intelligence mission.','actions':[],'knowledge_changes':[],'relationship_changes':[],'claim_ids':['IR007']}]},
]

FACTION_TRAJECTORIES=[
 {'entity_id':'faction:nghia-quan','latest_source_backed_state':'Active player-aligned intelligence and mission organization at the northern mission stage.','stages':[{'arc_id':'arc-01','source_state':'Organization receiving the player through Bach Thu Lam.','strategic_action':'Establishes player service and mission authority.','claim_ids':['IR004']},{'arc_id':'arc-06','source_state':'Target in the relic-recovery conflict.','strategic_action':'Suffers an attack during the promoted post-50 sequence.','claim_ids':['IR025']},{'arc_id':'arc-10','source_state':'Northern intelligence actor.','strategic_action':'Supports the mission involving Doan Tieu Vu and northern figures.','claim_ids':['IR007','IR016']}]},
 {'entity_id':'faction:nam-tong','latest_source_backed_state':'Engaged in the 1205 Northern Expedition conflict at the source-constrained endpoint.','stages':[{'arc_id':'arc-06','source_state':'Dynastic stability contested around Gia Vuong.','strategic_action':'The succession chain ends with Gia Vuong taking the throne.','claim_ids':['IR022']},{'arc_id':'arc-11','source_state':'State under political pressure.','strategic_action':'Han Thac Tru chooses Northern Expedition.','claim_ids':['IR009']},{'arc_id':'arc-12','source_state':'Campaigning state facing treason and sect conflict.','strategic_action':'The campaign reaches Linh Bich in 1205.','claim_ids':['IR010']}]},
 {'entity_id':'faction:kim','latest_source_backed_state':'Northern opposing power represented in intelligence, pursuit and campaign contexts.','stages':[{'arc_id':'arc-06','source_state':'Jin-linked actors join the cross-faction pursuit and treasure conflict.','strategic_action':'Participates through linked actors.','claim_ids':['IR024','IR025']},{'arc_id':'arc-10','source_state':'Target/context of Nghia Quan northern intelligence.','strategic_action':'Frames the northern mission.','claim_ids':['IR007']},{'arc_id':'arc-12','source_state':'Northern war opponent in the 1205 campaign frame.','strategic_action':'Forms the war context for Linh Bich.','claim_ids':['IR010']}]},
 {'entity_id':'faction:nhat-pham-duong','latest_source_backed_state':'Adversarial organization involved in Tay Ha pursuit and the attack on Nghia Quan.','stages':[{'arc_id':'arc-06','source_state':'Tay Ha organization in the cross-faction pursuit.','strategic_action':'Participates in the pursuit and later attack on Nghia Quan.','claim_ids':['IR024','IR025']}]},
 {'entity_id':'faction:duong-mon','latest_source_backed_state':'Sect implicated by an insider and Du Long diagram investigation.','stages':[{'arc_id':'arc-04','source_state':'Sect present in the southwest Du Long route material.','strategic_action':'Participates in the regional route context.','claim_ids':['IR020']},{'arc_id':'arc-06','source_state':'Institution investigated for an insider connection.','strategic_action':'Becomes central to the diagram investigation through named members.','claim_ids':['IR023']}]},
 {'entity_id':'faction:thuy-yen','latest_source_backed_state':'Sect whose disaster is reconnected to the Dali crisis and Du Long thread.','stages':[{'arc_id':'arc-00','source_state':'Sect affected by the relic-triggered disaster.','strategic_action':'Suffers the opening disaster.','claim_ids':['IR002']},{'arc_id':'arc-04','source_state':'Sect represented in the southwest regional material.','strategic_action':'Connects La Tuyet and Du Long material.','claim_ids':['IR020']},{'arc_id':'arc-09','source_state':'Sect disaster becomes part of the Dali crisis context.','strategic_action':'Its earlier disaster is carried into the regional conflict.','claim_ids':['IR006']}]},
]

RELATIONSHIPS=[
 {'relationship_id':'relationship:player-to-bach-thu-lam','source_entity_id':'character:game-player','target_entity_id':'character:bach-thu-lam','relationship_type':'CARETAKER_MISSION_AUTHORITY','initial_state':'The player is cared for and onboarded by Bach Thu Lam.','changes':[{'arc_id':'arc-07','change':'She remains the principal Nghia Quan mission authority.','claim_ids':['IR004']}],'latest_state':'Recurring caretaker and mission authority; exact kinship is not established.','claim_ids':['IR004','IR021']},
 {'relationship_id':'relationship:bach-thu-lam-to-player','source_entity_id':'character:bach-thu-lam','target_entity_id':'character:game-player','relationship_type':'CARETAKER_INFORMATION_HOLDER','initial_state':'Bach Thu Lam cares for the player and withholds complicated parent information.','changes':[],'latest_state':'Caretaker and information intermediary; full knowledge extent is unknown.','claim_ids':['IR004','IR021']},
 {'relationship_id':'relationship:player-to-parents','source_entity_id':'character:game-player','target_entity_id':'character:biological-parents','relationship_type':'KINSHIP','initial_state':'The player is the unnamed biological child.','changes':[{'arc_id':'arc-12','change':'The player encounters the parents in an illusion.','claim_ids':['IR011']}],'latest_state':'Biological relation confirmed; names and exact fate unknown.','claim_ids':['IR011','IR021']},
 {'relationship_id':'relationship:nghia-quan-to-player','source_entity_id':'faction:nghia-quan','target_entity_id':'character:game-player','relationship_type':'COMMAND_SERVICE','initial_state':'Nghia Quan receives the player through Bach Thu Lam.','changes':[{'arc_id':'arc-10','change':'The player serves in a Nghia Quan-linked northern intelligence mission.','claim_ids':['IR007']}],'latest_state':'Player-aligned mission organization.','claim_ids':['IR004','IR007']},
 {'relationship_id':'relationship:ly-hau-to-gia-vuong','source_entity_id':'character:ly-hau','target_entity_id':'character:gia-vuong','relationship_type':'POLITICAL_OPPOSITION','initial_state':'Ly Hau intervenes against the succession outcome protected by the player.','changes':[{'arc_id':'arc-06','change':'The intervention is countered and Gia Vuong takes the throne.','claim_ids':['IR022']}],'latest_state':'Intervention defeated in the promoted succession chain.','claim_ids':['IR022']},
 {'relationship_id':'relationship:gia-vuong-to-nam-tong','source_entity_id':'character:gia-vuong','target_entity_id':'faction:nam-tong','relationship_type':'RULERSHIP','initial_state':'Claimant located and protected during the succession crisis.','changes':[{'arc_id':'arc-06','change':'Takes the throne at the end of the succession phase.','claim_ids':['IR022']}],'latest_state':'Source-backed ruler outcome for the promoted phase.','claim_ids':['IR022']},
 {'relationship_id':'relationship:ngo-hi-to-nam-tong','source_entity_id':'character:ngo-hi','target_entity_id':'faction:nam-tong','relationship_type':'ALLEGIANCE_TO_TREASON','initial_state':'Southern Song-linked figure in early regional material.','changes':[{'arc_id':'arc-12','change':'Later first-party evidence identifies his treason in the 1205 campaign.','claim_ids':['IR010','IR020']}],'latest_state':'Treason actor in the Northern Expedition conflict.','claim_ids':['IR010','IR020']},
 {'relationship_id':'relationship:nhat-pham-to-nghia-quan','source_entity_id':'faction:nhat-pham-duong','target_entity_id':'faction:nghia-quan','relationship_type':'ENMITY_ATTACK','initial_state':'Nhat Pham Duong participates in the cross-faction pursuit.','changes':[{'arc_id':'arc-06','change':'The promoted chain records an attack on Nghia Quan.','claim_ids':['IR025']}],'latest_state':'Adversarial at the post-50 recovery phase.','claim_ids':['IR024','IR025']},
 {'relationship_id':'relationship:han-thac-tru-to-nam-tong','source_entity_id':'character:han-thac-tru','target_entity_id':'faction:nam-tong','relationship_type':'POLITICAL_COMMAND','initial_state':'Political leader under pressure in the northern-war context.','changes':[{'arc_id':'arc-11','change':'Chooses Northern Expedition.','claim_ids':['IR009']}],'latest_state':'Decision-maker directing the state toward the campaign.','claim_ids':['IR009']},
 {'relationship_id':'relationship:duong-khuyet-to-duong-mon','source_entity_id':'character:duong-khuyet','target_entity_id':'faction:duong-mon','relationship_type':'SECT_AFFILIATION','initial_state':'Duong Khuyet is Duong Mon-linked in the diagram investigation.','changes':[],'latest_state':'Named sect-linked participant in the promoted investigation.','claim_ids':['IR023']},
 {'relationship_id':'relationship:hoan-nhan-to-kim','source_entity_id':'character:hoan-nhan-tuong','target_entity_id':'faction:kim','relationship_type':'POLITICAL_AFFILIATION','initial_state':'Hoan Nhan Tuong is a Jin-linked actor.','changes':[],'latest_state':'Appears in both the treasure conflict and northern mission contexts.','claim_ids':['IR007','IR025']},
]

KNOWLEDGE_EVENTS=[
 {'knowledge_event_id':'knowledge:bach-parent-information','entity_id':'character:bach-thu-lam','prior_status':'UNKNOWN','new_status':'KNOWS','information':'Some complicated information about the player parents; exact extent is not established.','source_event':'Bach Thu Lam withholds details in the recovered origin chain.','arc_id':'arc-01','thread_ids':['thread:player-origin'],'mystery_ids':['mystery:player-parents'],'claim_ids':['IR021']},
 {'knowledge_event_id':'knowledge:player-parent-question','entity_id':'character:game-player','prior_status':'UNKNOWN','new_status':'KNOWS','information':'Bach Thu Lam is withholding complicated information about the parents.','source_event':'Opening origin-chain disclosure.','arc_id':'arc-01','thread_ids':['thread:player-origin'],'mystery_ids':['mystery:player-parents'],'claim_ids':['IR021']},
 {'knowledge_event_id':'knowledge:player-succession-threat','entity_id':'character:game-player','prior_status':'UNKNOWN','new_status':'KNOWS','information':'Gia Vuong must be located and protected against Ly Hau intervention.','source_event':'Level 49-58 succession sequence.','arc_id':'arc-06','thread_ids':['thread:post50-cross-narrative','thread:southern-song-war'],'mystery_ids':[],'claim_ids':['IR022']},
 {'knowledge_event_id':'knowledge:player-du-long-theft','entity_id':'character:game-player','prior_status':'SUSPECTS','new_status':'KNOWS','information':'The Du Long diagram investigation culminates in a recorded relic theft at Diem Thuong.','source_event':'Level 58-69 investigation sequence.','arc_id':'arc-06','thread_ids':['thread:du-long-relic','thread:post50-cross-narrative'],'mystery_ids':['mystery:du-long-diagram-theft'],'claim_ids':['IR023']},
 {'knowledge_event_id':'knowledge:player-ngo-hi-leak','entity_id':'character:game-player','prior_status':'UNKNOWN','new_status':'KNOWS','information':'An Ngo Hi information leak leads into the cross-faction pursuit.','source_event':'Level 69-79 pursuit sequence.','arc_id':'arc-06','thread_ids':['thread:ngo-hi-status','thread:post50-cross-narrative'],'mystery_ids':['mystery:ngo-hi-status','mystery:du-long-diagram-theft'],'claim_ids':['IR024']},
 {'knowledge_event_id':'knowledge:player-northern-mission','entity_id':'character:game-player','prior_status':'UNKNOWN','new_status':'KNOWS','information':'Mission-relevant northern intelligence involving Doan Tieu Vu, Gia Luat So Tai and Hoan Nhan Tuong; image-only detail is not expanded.','source_event':'Level-120 northern mission.','arc_id':'arc-10','thread_ids':['thread:northern-war','thread:nghia-quan-service'],'mystery_ids':[],'claim_ids':['IR007']},
 {'knowledge_event_id':'knowledge:player-ngo-hi-treason','entity_id':'character:game-player','prior_status':'KNOWS','new_status':'KNOWS','information':'Ngo Hi is a treason actor in the 1205 Northern Expedition conflict.','source_event':'Linh Bich campaign reveal.','arc_id':'arc-12','thread_ids':['thread:ngo-hi-status','thread:southern-song-war'],'mystery_ids':['mystery:ngo-hi-status'],'claim_ids':['IR010']},
 {'knowledge_event_id':'knowledge:player-parent-illusion','entity_id':'character:game-player','prior_status':'KNOWS','new_status':'KNOWS','information':'The encountered figures are the biological parents; their names, lineage and exact fate remain unknown.','source_event':'Official Linh Bich dream/illusion page.','arc_id':'arc-12','thread_ids':['thread:player-origin'],'mystery_ids':['mystery:player-parents'],'claim_ids':['IR011']},
]

def load_json(path:Path):return json.loads(path.read_text(encoding='utf-8'))
def load_jsonl(path:Path):return [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line]
def write_json(path:Path,value):path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def sha(path:Path):return hashlib.sha256(path.read_bytes()).hexdigest()
def git_head():return subprocess.run(['git','rev-parse','HEAD'],cwd=ROOT,text=True,capture_output=True,check=True).stdout.strip()
def assert_git_commit(commit):subprocess.run(['git','cat-file','-e',f'{commit}^{{commit}}'],cwd=ROOT,text=True,capture_output=True,check=True)
def generated_meta():return {'schema_version':SCHEMA_VERSION,'generator':GENERATOR,'generated_at_utc':datetime.now(timezone.utc).isoformat()}
def clean_text(value):return re.sub(r'<[^>]+>','',value or '').strip()
def record_source(record):return [{key:row.get(key) for key in ('source_id','evidence_class','path','sha256','locator','edition') if row.get(key) not in (None,'')} for row in record.get('source_records',[])]
def compact_evidence(evidence):return {key:evidence.get(key) for key in ('source_family','support_type','evidence_class','path','url','sha256','response_sha256','locator','record_key','citation_id') if evidence.get(key) not in (None,'')}
def claim_projection(claim):return {'claim_id':claim['claim_id'],'claim':claim['claim'],'status':claim['status'],'centrality':claim['centrality'],'narrative_impact':claim['narrative_impact'],'evidence':[compact_evidence(row) for row in claim['evidence']]}
def canon_entity_id(entity_id):return ENTITY_ID_CANONICAL.get(entity_id,entity_id)

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
 generation_base_commit=git_head();assert_git_commit(SOURCE_EVIDENCE_COMMIT);source_commit=SOURCE_EVIDENCE_COMMIT
 concordance=load_json(ROOT/'research'/'reconciliation'/'lore-concordance.json')
 release=load_json(ROOT/'generated'/'release'/'release-manifest.json')
 validation=load_json(ROOT/'generated'/'reports'/'release-validation-report.json')
 confidence=load_json(ROOT/'research'/'confidence-report.json')
 unresolved=load_json(ROOT/'research'/'unresolved-questions.json')['entries']
 claims=load_jsonl(ROOT/'research'/'reconciliation'/'internet-research-claims.jsonl');claims_by_id={row['claim_id']:row for row in claims}
 dossier_index=load_json(ROOT/'research'/'reconstruction'/'game-story-dossiers'/'index.json')
 assert_preconditions(concordance,release,validation)

 claim_item_ids=defaultdict(list)
 for entity_id,(claim_ids,_) in ITEM_SPECS.items():
  for claim_id in claim_ids:claim_item_ids[claim_id].append(entity_id)
 claim_location_ids=defaultdict(list)
 for entity_id,_,_,_,claim_ids,_ in LOCATION_SPECS:
  for claim_id in claim_ids:claim_location_ids[claim_id].append(entity_id)
 claim_sect_ids=defaultdict(list)
 for faction_id,claim_ids in SECT_CLAIMS.items():
  for claim_id in claim_ids:claim_sect_ids[claim_id].append(f'sect:{faction_id}')

 thread_ids={row['thread_id'] for row in PLOT_THREADS};mystery_ids={row['mystery_id'] for row in MYSTERIES}
 claim_threads=defaultdict(list);arc_threads=defaultdict(list);entity_threads=defaultdict(list)
 for thread in PLOT_THREADS:
  for claim_id in thread['claim_ids']:claim_threads[claim_id].append(thread['thread_id'])
  for entity_id in thread['participant_entity_ids']:entity_threads[canon_entity_id(entity_id)].append(thread['thread_id'])
  stages=[thread['first_setup'],*thread['developments'],*thread.get('reversals_or_reframes',[])]
  if thread.get('payoff'):stages.append(thread['payoff'])
  for stage in stages:
   if stage.get('arc_id') and thread['thread_id'] not in arc_threads[stage['arc_id']]:arc_threads[stage['arc_id']].append(thread['thread_id'])
 arc_mysteries=defaultdict(list);thread_mysteries=defaultdict(list)
 for mystery in MYSTERIES:
  for thread_id in mystery['thread_ids']:thread_mysteries[thread_id].append(mystery['mystery_id'])
  for phase in mystery['phases']:
   if mystery['mystery_id'] not in arc_mysteries[phase['arc_id']]:arc_mysteries[phase['arc_id']].append(mystery['mystery_id'])

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
  principal_entity_ids=[canon_entity_id(value) for value in ARC_ENTITIES.get(arc_id,[])]
  section_fields={'premise':'premise_claim_ids','characters_and_factions':'character_and_faction_claim_ids','evidenced_goals_and_motives':'goal_and_motive_claim_ids','player_learns':'player_learns_claim_ids','reveals':'reveal_claim_ids','climax_and_resolution':'climax_resolution_claim_ids','political_and_wulin_consequences':'consequence_claim_ids','important_named_references':'important_named_reference_claim_ids','evidence_limits':'evidence_limit_claim_ids'}
  story_bible_sections={label:[claim_projection(claims_by_id[claim_id]) for claim_id in dossier.get(field,[])] for label,field in section_fields.items()}
  ordered_source_events=[event|{'resolved_claim':claim_projection(claims_by_id[event['claim_id']])} for event in dossier.get('ordered_events',[])]
  important_item_ids=sorted({entity_id for claim_id in referenced for entity_id in claim_item_ids[claim_id]});important_location_ids=sorted({entity_id for claim_id in referenced for entity_id in claim_location_ids[claim_id]});important_sect_ids=sorted({entity_id for claim_id in referenced for entity_id in claim_sect_ids[claim_id]})
  projected={**dossier,'handoff_projection_version':SCHEMA_VERSION,'source_dossier':{'path':jxlab.rel(source_path),'sha256':sha(source_path)},'resolved_claims':resolved,'story_bible_sections':story_bible_sections,'ordered_source_events':ordered_source_events,'principal_entity_ids':principal_entity_ids,'important_item_ids':important_item_ids,'important_location_ids':important_location_ids,'important_sect_ids':important_sect_ids,'important_martial_ids':[],'active_plot_thread_ids':sorted(arc_threads[arc_id]),'mystery_payoff_ids':sorted(arc_mysteries[arc_id]),'material_contradiction_status':'NONE_UNRESOLVED','source_story_bible_boundary':'Source-only reconstruction; no novel adaptation, scene, episode or protagonist decision.'}
  destination=OUT/'game-story'/'dossiers'/f'{arc_id}.json';write_json(destination,projected);projected_dossiers.append(destination)
  arc_rows.append({'order':position,'arc_id':arc_id,'title':dossier['title'],'aliases':[],'chronology_or_level_range':dossier['chronology_or_level_range'],'branch_or_convergence_role':'BRANCH' if arc_id in {'arc-02','arc-03','arc-04'} else ('CONVERGENCE' if arc_id in {'arc-05','arc-06'} else 'LINEAR_OR_CONTEXT'),'dossier_path':destination.relative_to(OUT).as_posix(),'principal_entity_ids':principal_entity_ids,'claim_ids':referenced,'status':'PROMOTED_SOURCE_CANON','confidence':'MIXED_PROMOTABLE','central_unresolved_count':len(dossier.get('central_unknown_ids',[])),'active_plot_thread_ids':sorted(arc_threads[arc_id]),'mystery_reveal_ids':sorted(arc_mysteries[arc_id]),'important_item_ids':important_item_ids,'important_location_ids':important_location_ids,'important_sect_ids':important_sect_ids,'important_martial_ids':[]})
  chronology.extend([f"## {position}. {dossier['title']}",f"- Stable arc ID: `{arc_id}`",f"- Chronology/level: {dossier['chronology_or_level_range']}",f"- Source dossier: `{destination.relative_to(OUT).as_posix()}`",'- Premise claims: '+(', '.join(f'`{value}`' for value in dossier.get('premise_claim_ids',[])) or 'none'),'- Player-learning claims: '+(', '.join(f'`{value}`' for value in dossier.get('player_learns_claim_ids',[])) or 'none'),'- Reveal/climax claims: '+(', '.join(f'`{value}`' for value in [*dossier.get('reveal_claim_ids',[]),*dossier.get('climax_resolution_claim_ids',[])]) or 'none'),'- Outcome/consequence claims: '+(', '.join(f'`{value}`' for value in dossier.get('consequence_claim_ids',[])) or 'none'),'- Plot threads: '+(', '.join(f'`{value}`' for value in sorted(arc_threads[arc_id])) or 'none'),'- Mystery/payoff records: '+(', '.join(f'`{value}`' for value in sorted(arc_mysteries[arc_id])) or 'none')])
  for event in dossier.get('ordered_events',[]):
   claim=claims_by_id[event['claim_id']];chronology.append(f"- `{claim['claim_id']}` [{claim['status']}]: {claim['claim']}")
  if dossier.get('central_unknown_ids'):chronology.append('- Tolerated unknowns: '+', '.join(f"`{value}`" for value in dossier['central_unknown_ids']))
  chronology.append('')
 (OUT/'game-story'/'master-chronology.md').parent.mkdir(parents=True,exist_ok=True)
 (OUT/'game-story'/'master-chronology.md').write_text('\n'.join(chronology),encoding='utf-8')
 write_json(OUT/'game-story'/'arc-index.json',{**generated_meta(),'promotion_status':'NOVEL_PROMOTION_READY','arc_count':len(arc_rows),'arcs':arc_rows})

 thread_rows=[]
 for thread in PLOT_THREADS:thread_rows.append(thread|{'participant_entity_ids':[canon_entity_id(value) for value in thread['participant_entity_ids']],'claim_evidence':[claim_projection(claims_by_id[claim_id]) for claim_id in thread['claim_ids']]})
 write_json(OUT/'game-story'/'plot-thread-index.json',{**generated_meta(),'selection_policy':'Only persisted source threads spanning multiple promoted beats/arcs or carrying load-bearing strategic meaning.','thread_count':len(thread_rows),'threads':thread_rows})
 mystery_rows=[]
 for mystery in MYSTERIES:mystery_rows.append(mystery|{'claim_evidence':[claim_projection(claims_by_id[claim_id]) for claim_id in mystery['claim_ids']]})
 write_json(OUT/'game-story'/'mystery-payoff-map.json',{**generated_meta(),'phase_types':['SETUP','CLUE','SUSPICION','REVEAL','PAYOFF','RESIDUE'],'selection_policy':'Only source-backed timing-sensitive questions; absence of a payoff remains explicit.','mystery_count':len(mystery_rows),'mysteries':mystery_rows})

 causal_nodes=[{**claim_projection(claim),'arc_ids':claim['arc_ids']} for claim in claims]
 causal_edges=[]
 for index,(source,target,relation,status) in enumerate(CAUSAL_EDGES,1):
  related_threads=sorted(set(claim_threads[source])&set(claim_threads[target]))
  causal_edges.append({'edge_id':f'causal:{index:02d}','source_claim_id':source,'target_claim_id':target,'relationship':relation,'status':status,'edge_basis':'DIRECT_OR_CROSS_SOURCE_PROMOTED_RECONSTRUCTION','source_arc_ids':claims_by_id[source]['arc_ids'],'target_arc_ids':claims_by_id[target]['arc_ids'],'related_plot_thread_ids':related_threads,'dossier_paths':sorted({f"game-story/dossiers/{arc_id}.json" for arc_id in [*claims_by_id[source]['arc_ids'],*claims_by_id[target]['arc_ids']] if arc_id in {row['arc_id'] for row in arc_rows}}),'evidence_claim_ids':[source,target]})
 write_json(OUT/'game-story'/'causal-spine.json',{**generated_meta(),'promotion_status':'NOVEL_PROMOTION_READY','scope':'Only promoted claim nodes and explicitly curated evidence-supported transitions; absent bridges remain absent.','nodes':causal_nodes,'edges':causal_edges})

 character_rows=[]
 for spec in CHARACTERS:
  raw=[]
  for name in spec['lookup_names']:raw.extend(npc_by_name.get(name,[]))
  trajectory=next((row for row in CHARACTER_TRAJECTORIES if row['entity_id']==spec['entity_id']),None)
  trajectory_path=f"characters/trajectories/{spec['entity_id'].split(':',1)[1]}.json" if trajectory else None
  related_thread_ids=sorted(entity_threads[spec['entity_id']]);related_mystery_ids=sorted({mystery_id for thread_id in related_thread_ids for mystery_id in thread_mysteries[thread_id]})
  character_rows.append({key:value for key,value in spec.items() if key not in {'lookup_names','relationships'}}|{'first_relevant_arc_id':spec['arc_ids'][0],'major_relevant_arc_ids':spec['arc_ids'],'latest_relevant_arc_id':spec['arc_ids'][-1],'trajectory_path':trajectory_path,'related_plot_thread_ids':related_thread_ids,'related_mystery_reveal_ids':related_mystery_ids,'known_martial_associations':[],'source_record_keys':[row['record_key'] for row in raw[:12]],'source_records':[source for row in raw[:12] for source in record_source(row)],'claim_evidence':[claim_projection(claims_by_id[claim_id]) for claim_id in spec['claim_ids']]})
 for trajectory in CHARACTER_TRAJECTORIES:
  spec=next(row for row in CHARACTERS if row['entity_id']==trajectory['entity_id'])
  claim_ids=list(dict.fromkeys(claim_id for stage in trajectory['stages'] for claim_id in stage['claim_ids']))
  write_json(OUT/'characters'/'trajectories'/f"{trajectory['entity_id'].split(':',1)[1]}.json",{**generated_meta(),**trajectory,'canonical_name':spec['vi'],'affiliations':spec['affiliations'],'related_plot_thread_ids':sorted(entity_threads[trajectory['entity_id']]),'related_mystery_reveal_ids':sorted({mystery_id for thread_id in entity_threads[trajectory['entity_id']] for mystery_id in thread_mysteries[thread_id]}),'claim_evidence':[claim_projection(claims_by_id[claim_id]) for claim_id in claim_ids],'source_trajectory_boundary':'No inferred inner psychology, romance, redemption or novel-only arc.'})
 write_json(OUT/'characters'/'character-index.json',{**generated_meta(),'selection_policy':'Only recurring or load-bearing promoted-story characters; traits are not inferred.','count':len(character_rows),'trajectory_count':len(CHARACTER_TRAJECTORIES),'characters':character_rows})

 faction_rows=[]
 for spec in FACTIONS:
  trajectory=next((row for row in FACTION_TRAJECTORIES if row['entity_id']==spec['entity_id']),None)
  trajectory_path=f"factions/trajectories/{spec['entity_id'].split(':',1)[1]}.json" if trajectory else None
  canonical_entity_id=canon_entity_id(spec['entity_id']);related_thread_ids=sorted(entity_threads[canonical_entity_id])
  faction_rows.append(spec|{'entity_id':canonical_entity_id,'trajectory_path':trajectory_path,'related_arc_ids':sorted({arc_id for claim_id in spec['claim_ids'] for arc_id in claims_by_id[claim_id]['arc_ids']}),'related_plot_thread_ids':related_thread_ids,'allies_enemies_rivals':'See relationships/source-relationship-map.json; no relation is inferred from co-occurrence.','claim_evidence':[claim_projection(claims_by_id[claim_id]) for claim_id in spec['claim_ids']]})
 for trajectory in FACTION_TRAJECTORIES:
  spec=next(row for row in FACTIONS if row['entity_id']==trajectory['entity_id'])
  claim_ids=list(dict.fromkeys(claim_id for stage in trajectory['stages'] for claim_id in stage['claim_ids']))
  write_json(OUT/'factions'/'trajectories'/f"{trajectory['entity_id'].split(':',1)[1]}.json",{**generated_meta(),**trajectory,'entity_id':canon_entity_id(trajectory['entity_id']),'canonical_name':spec['vi'],'institutional_role':spec['role'],'related_plot_thread_ids':sorted(entity_threads[canon_entity_id(trajectory['entity_id'])]),'claim_evidence':[claim_projection(claims_by_id[claim_id]) for claim_id in claim_ids],'source_trajectory_boundary':'Institutional source trajectory only; no invented strategy or motive.'})
 write_json(OUT/'factions'/'faction-index.json',{**generated_meta(),'selection_policy':'Only organizations or polities with a promoted-story role.','count':len(faction_rows),'trajectory_count':len(FACTION_TRAJECTORIES),'factions':faction_rows})

 relationship_rows=[]
 for relationship in RELATIONSHIPS:relationship_rows.append(relationship|{'source_entity_id':canon_entity_id(relationship['source_entity_id']),'target_entity_id':canon_entity_id(relationship['target_entity_id']),'claim_evidence':[claim_projection(claims_by_id[claim_id]) for claim_id in relationship['claim_ids']]})
 write_json(OUT/'relationships'/'source-relationship-map.json',{**generated_meta(),'selection_policy':'Directional, load-bearing source relationships only; co-occurrence is never sufficient.','relationship_count':len(relationship_rows),'relationships':relationship_rows})
 knowledge_rows=[]
 for event in KNOWLEDGE_EVENTS:knowledge_rows.append(event|{'claim_evidence':[claim_projection(claims_by_id[claim_id]) for claim_id in event['claim_ids']]})
 write_json(OUT/'knowledge'/'source-knowledge-timeline.json',{**generated_meta(),'allowed_statuses':['KNOWS','BELIEVES','SUSPECTS','HEARD_RUMOR','MISINFORMED','UNKNOWN'],'selection_policy':'Only source-backed knowledge changes material to causality, mystery, allegiance or reveal timing.','event_count':len(knowledge_rows),'events':knowledge_rows})

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
 merged_names={}
 for row in name_rows:
  current=merged_names.setdefault(row['entity_id'],{'entity_id':row['entity_id'],'cn':row['cn'],'vi':row['vi'],'variants':[],'claim_ids':[],'source_record_keys':[]})
  for key in ('variants','claim_ids','source_record_keys'):
   current[key]=list(dict.fromkeys([*current[key],*row.get(key,[])]))
 merged_aliases={}
 for row in alias_rows:
  current=merged_aliases.setdefault(row['entity_id'],{'entity_id':row['entity_id'],'canonical':row['canonical'],'aliases':[],'types':[]})
  current['aliases']=list(dict.fromkeys([*current['aliases'],*filter(None,row.get('aliases',[]))]));current['types']=list(dict.fromkeys([*current['types'],row['type']]))
 name_rows=list(merged_names.values());alias_rows=list(merged_aliases.values())
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
  task_map.append({'source_record_key':family['record_key'],'source_id_decimal':family['task_id'],'source_name':family['name'],'record_kind':'task','arc_id':'arc-06','beat_claim_ids':[phase['claim_id']],'plot_thread_ids':['thread:post50-cross-narrative'],'narrative_order':family['narrative_order'],'level_gate_range':[family['min_level_gate'],family['max_level_gate']],'id_reuse_hazard':'ID_REUSE_VARIANT','standalone_semantic_content_excluded':True,'mapping_basis':'validated wrapper-inline level gates and managed order; standalone same-ID content excluded','source_records':family['source_records']})
 write_json(OUT/'concordance'/'task-story-map.json',{**generated_meta(),'warning':'Task identifiers support forensic lookup; they do not define novel structure. ID_REUSE_VARIANT entries retain wrapper-inline evidence and exclude unrelated standalone semantics.','count':len(task_map),'id_reuse_variant_count':sum(1 for row in task_map if row.get('id_reuse_hazard')=='ID_REUSE_VARIANT'),'entries':task_map})

 central=[row|{'promotion_safety':'Coherent adaptation remains possible because the uncertainty is explicitly bounded and no promoted claim depends on an invented answer.'} for row in unresolved if row.get('centrality')=='CENTRAL_TOLERABLE']
 noncentral=[row for row in unresolved if row.get('centrality')=='NON_CENTRAL']
 write_json(OUT/'unresolved'/'central-tolerable.json',{**generated_meta(),'count':len(central),'entries':central})
 write_json(OUT/'unresolved'/'non-central.json',{**generated_meta(),'count':len(noncentral),'entries':noncentral})
 write_json(OUT/'unresolved'/'material-conflicts.json',{**generated_meta(),'count':0,'entries':[],'note':'No unresolved MATERIAL narrative conflict exists at handoff generation time.'})

 relevant_paths=[ROOT/'generated'/'release'/'release-manifest.json',ROOT/'generated'/'reports'/'release-validation-report.json',ROOT/'research'/'reconciliation'/'lore-concordance.json',ROOT/'research'/'reconstruction'/'game-story-dossiers'/'index.json',ROOT/'research'/'confidence-report.json',ROOT/'research'/'unresolved-questions.json']
 source_classes=sorted({evidence.get('evidence_class') for claim in claims for evidence in claim['evidence'] if evidence.get('evidence_class')}|{'RAW_SERVER','RAW_CLIENT'})
 provenance={**generated_meta(),'source_repository':'anhdaijka/jx-source-lab','source_lab_commit':source_commit,'handoff_generation_base_commit':generation_base_commit,'research_release':{'version':release['release_version'],'status':release['release_status'],'promotion':release['novel_promotion']},'reconciliation_artifacts':[{'path':jxlab.rel(path),'sha256':sha(path)} for path in relevant_paths],'source_classes_represented':source_classes,'known_story_relevant_limitations':[row['question'] for row in central],'persisted_user_canon_decisions':[],'build_version_policy':'Exact client/server build/version identity is metadata only and is not a promotion requirement unless it changes a MATERIAL story interpretation.','lookup_convention':'Resolve IR claim IDs in research/reconciliation/internet-research-claims.jsonl; arc IDs in research/reconstruction/game-story-dossiers/; entity and source record keys in generated/records/. Thread, mystery, relationship and knowledge IDs are source-side handoff projections whose claim_evidence points back to those artifacts.','new_broad_source_research_performed':False,'raw_payload_policy':'Raw client/server files, PAKs, binaries, archives, private-input packages and bulk extracted payloads are excluded; provenance references remain textual.'}
 write_json(OUT/'provenance.json',provenance)
 confidence_summary={**generated_meta(),'promotion_status':'NOVEL_PROMOTION_READY','promotion_gates':concordance['promotion_gates'],'claim_status_counts':concordance['claim_status_counts'],'promoted_story_dossiers':len(projected_dossiers),'unresolved_counts':{'CENTRAL_BLOCKER':0,'CENTRAL_TOLERABLE':len(central),'NON_CENTRAL':len(noncentral),'UNRESOLVED_MATERIAL_CONFLICT':0},'interpretation_boundary':'Promotable source-canon only; no adaptation, episode structure or prose decision is included.'}
 write_json(OUT/'confidence-summary.json',confidence_summary)

 files=[]
 for path in sorted(p for p in OUT.rglob('*') if p.is_file() and p.name!='handoff-manifest.json'):
  files.append({'path':path.relative_to(OUT).as_posix(),'sha256':sha(path),'bytes':path.stat().st_size})
 manifest={**generated_meta(),'handoff_status':'NOVEL_HANDOFF_READY','source_repository':'anhdaijka/jx-source-lab','source_lab_commit':source_commit,'handoff_generation_base_commit':generation_base_commit,'canon_target':'LATEST_COHERENT_KIEM_THE_LORE','promotion_status':'NOVEL_PROMOTION_READY','promotion_gates':concordance['promotion_gates'],'promoted_main_story_arc_count':len(projected_dossiers),'promoted_important_character_count':len(character_rows),'promoted_character_trajectory_count':len(CHARACTER_TRAJECTORIES),'promoted_important_faction_count':len(faction_rows),'promoted_faction_trajectory_count':len(FACTION_TRAJECTORIES),'promoted_plot_thread_count':len(PLOT_THREADS),'promoted_mystery_payoff_count':len(MYSTERIES),'source_relationship_count':len(RELATIONSHIPS),'source_knowledge_event_count':len(KNOWLEDGE_EVENTS),'unresolved_counts':{'CENTRAL_BLOCKER':0,'CENTRAL_TOLERABLE':len(central),'NON_CENTRAL':len(noncentral),'UNRESOLVED_MATERIAL_CONFLICT':0},'raw_proprietary_payloads_excluded':True,'one_way_import_contract':True,'runtime_dependency_on_lab':False,'files':files,'manifest_self_hash_note':'The manifest cannot recursively hash itself; every payload artifact is hashed above.'}
 write_json(OUT/'handoff-manifest.json',manifest)
 return {'status':'NOVEL_HANDOFF_READY','source_lab_commit':source_commit,'generation_base_commit':generation_base_commit,'files':len(files)+1,'bytes':sum(row['bytes'] for row in files)+(OUT/'handoff-manifest.json').stat().st_size,'dossiers':len(projected_dossiers),'plot_threads':len(PLOT_THREADS),'mysteries':len(MYSTERIES),'character_trajectories':len(CHARACTER_TRAJECTORIES),'faction_trajectories':len(FACTION_TRAJECTORIES),'central_tolerable':len(central),'non_central':len(noncentral)}

if __name__=='__main__':print(json.dumps(build(),ensure_ascii=False,indent=2))
