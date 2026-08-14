#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, os, time, tomllib
from pathlib import Path
from collections import Counter, defaultdict

ROOT=Path(__file__).resolve().parents[1]
with (ROOT/'lab.toml').open('rb') as f: CFG=tomllib.load(f)
REPORT_DIR=ROOT/CFG['outputs']['reports']; REPORT_DIR.mkdir(parents=True,exist_ok=True)

def rel(p):
    try:return p.relative_to(ROOT).as_posix()
    except ValueError:return str(p)

def sha256_file(path,chunk=1024*1024):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(chunk),b''):h.update(b)
    return h.hexdigest()

def probe_encoding(path,max_bytes):
    try:data=path.read_bytes()[:max_bytes]
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
    payload={'generated_at_unix':time.time(),'hashes_included':do_hash,'file_count':len(records),'roots':{k:{'files':rootc[k],'bytes':rootb[k]} for k in rootc},'extension_counts':dict(extc.most_common()),'text_probe_counts':dict(txtc),'files':records}
    (REPORT_DIR/'source-inventory.json').write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding='utf-8')
    tree=[{'path':r['path'],'size':r['size'],'ext':r['extension'],'text_like':r['text_like'],'encoding':r['encoding_probe']} for r in records]
    (REPORT_DIR/'source-tree-index.json').write_text(json.dumps(tree,ensure_ascii=False,indent=2),encoding='utf-8')
    lines=['# Source Inventory','',f'- Files: **{len(records):,}**',f'- Hashes included: **{do_hash}**','','## Roots','']
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
            try:text=p.read_bytes()[:max_probe].decode(enc,errors='replace')
            except Exception:continue
            low=text.lower(); hits=[n for n in needles if n in low]
            if hits:
                samples=[]
                for i,line in enumerate(text.splitlines(),1):
                    if any(n in line.lower() for n in hits):
                        samples.append({'line':i,'text':line[:500]})
                        if len(samples)>=12:break
                refs.append({'source_root':sid,'path':rel(p),'encoding':enc,'hits':hits,'samples':samples})
    (REPORT_DIR/'pak-reference-report.json').write_text(json.dumps({'archives':archives,'code_text_references':refs},ensure_ascii=False,indent=2),encoding='utf-8')
    lines=['# PAK / Archive Reference Report','','## Archive files','']
    lines += [f"- `{a['path']}` — {a['size']:,} bytes; header `{a['header_hex']}`" for a in archives] or ['- None found.']
    lines += ['','## Candidate loader/code references','']
    if refs:
        for r in refs[:300]:
            lines += [f"### `{r['path']}`",'Hits: '+', '.join(r['hits'])]
            lines += [f"- L{s['line']}: `{s['text']}`" for s in r['samples']]+['']
    else:lines+=['- No obvious references found.']
    (REPORT_DIR/'pak-reference-report.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
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
            try:text=p.read_bytes()[:max_probe].decode(enc,errors='replace')
            except Exception:continue
            hay=(rel(p)+'\n'+text[:50000]).lower()
            for b,terms in keys.items():
                if any(t.lower() in hay for t in terms) and len(buckets[b])<limit:
                    buckets[b].append({'source_root':sid,'path':rel(p),'encoding':enc,'size':p.stat().st_size})
    (REPORT_DIR/'text-candidates.json').write_text(json.dumps(buckets,ensure_ascii=False,indent=2),encoding='utf-8')
    lines=['# Candidate Data Sources','']
    for b in keys:
        lines += [f'## {b}','']+[f"- `{r['path']}` ({r['encoding']}, {r['size']:,} bytes)" for r in buckets[b]]+[''] if buckets[b] else [f'## {b}','','- No candidates yet.','']
    content='\n'.join(lines)+'\n';(REPORT_DIR/'text-candidates.md').write_text(content,encoding='utf-8');(REPORT_DIR/'candidate-data-sources.md').write_text(content,encoding='utf-8')
    print('Wrote candidate source reports.')

def bootstrap(args):
    inventory(args);find_pak_refs(args);text_candidates(args);print('Bootstrap reports complete.')

def main():
    ap=argparse.ArgumentParser(description='JX Source Lab read-only utilities');sub=ap.add_subparsers(dest='command',required=True)
    p=sub.add_parser('inventory');p.add_argument('--hash',action='store_true');p.set_defaults(func=inventory)
    p=sub.add_parser('find-pak-refs');p.add_argument('--hash',action='store_true');p.set_defaults(func=find_pak_refs)
    p=sub.add_parser('text-candidates');p.set_defaults(func=text_candidates,hash=False)
    p=sub.add_parser('bootstrap');p.add_argument('--hash',action='store_true');p.set_defaults(func=bootstrap)
    a=ap.parse_args();a.func(a)
if __name__=='__main__':main()
