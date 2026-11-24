#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""维基链接候选批量生成（并发版）：为无 wikipedia 的记录查询 DBpedia 候选。

- 不直接写主数据，输出 archive-data/wiki-candidates.json
- 每条记录保存：候选实体列表（label/uri/type）、匹配级别、是否唯一精确
- ThreadPool 并发 + 本地缓存，约 15-20 分钟完成 9597 条
"""
import json, re, sys, time, os, requests, difflib, threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from wikilink_match import clean_name, first, norm_label, lookup

BASE=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
H={'User-Agent':'MementoWeb/1.0 (data enrichment)'}

def is_person_candidate(doc):
    types=' '.join(doc.get('type') or []) if isinstance(doc,dict) else ''
    uri=first(doc.get('resource'))
    bad_type=any(t in types for t in ['/Album','/Film','/Book','/Event','/Place',
                                       '/Organisation','/Company','/Species','/Animal'])
    tail=uri.split('/')[-1]
    bad_uri=(tail.startswith('List_of_') or tail.startswith('Category:') or
             'disambiguation' in tail.lower() or re.match(r'^\d{4}',tail))
    return not bad_type and not bad_uri

def classify(name, docs):
    persons=[d for d in docs if is_person_candidate(d)]
    if not persons: return 'C',None,'无候选',[]
    q=norm_label(name)
    exact=[d for d in persons if norm_label(first(d.get('label')))==q]
    cands=[{'label':norm_label(first(d.get('label'))),
            'uri':first(d.get('resource')).split('/')[-1],
            'types':[t.split('/')[-1] for t in (d.get('type') or [])][:3]}
           for d in persons]
    if len(persons)==1 and len(exact)==1:
        return 'A',exact[0],'唯一精确匹配',cands
    if len(exact)==1:
        return 'B' if len(persons)<=3 else 'C',exact[0],f'唯一精确(共{len(persons)}候选)',cands
    if len(exact)>1:
        return 'C',None,f'多个精确匹配({len(exact)})',cands
    similar=[d for d in persons if difflib.SequenceMatcher(None,q,norm_label(first(d.get('label')))).ratio()>=0.88]
    if len(similar)==1 and len(persons)==1:
        return 'B',similar[0],'唯一相似匹配',cands
    return 'C',None,f'无精确/多相似({len(persons)}候选)',cands

def process_one(item):
    id_,name=item
    docs=lookup(name)
    if not docs:
        return id_,{'name':'','level':'C','reason':'无返回','candidates':[]}
    level,doc,reason,cands=classify(name,docs)
    rec={'level':level,'reason':reason,'candidates':cands}
    if doc:
        rec['bestUri']=first(doc.get('resource')).split('/')[-1]
        rec['bestLabel']=norm_label(first(doc.get('label')))
    return id_,rec

def main():
    s=open(os.path.join(BASE,'data','deaths.js'),encoding='utf-8').read()
    a=json.loads(s[s.index('['):s.rindex(']')+1])
    targets=[(x['id'],clean_name(x['nameOrig'])) for x in a
             if not x.get('wikipedia') and x.get('nameOrig')]
    name_by_id={x['id']:x['name'] for x in a}
    orig_by_id={x['id']:x['nameOrig'] for x in a}
    print('待处理:',len(targets),'条')
    results={}; stats={}; done=0; t0=time.time()
    with ThreadPoolExecutor(max_workers=12) as ex:
        futs={ex.submit(process_one,t):t for t in targets}
        for fut in as_completed(futs):
            id_,rec=fut.result()
            rec['name']=name_by_id.get(id_,''); rec['orig']=orig_by_id.get(id_,'')
            results[id_]=rec
            lv=rec['level']; stats[lv]=stats.get(lv,0)+1
            done+=1
            if done%500==0:
                el=time.time()-t0
                print(f'  {done}/{len(targets)} | {el/60:.1f}min | {stats}')
    out=os.path.join(BASE,'archive-data','wiki-candidates.json')
    json.dump({'results':results,'stats':stats,'generated':time.strftime('%Y-%m-%d %H:%M')},
              open(out,'w',encoding='utf-8'),ensure_ascii=False,indent=2)
    print('\n完成:',stats,'耗时',round((time.time()-t0)/60,1),'分钟')

if __name__=='__main__': main()
