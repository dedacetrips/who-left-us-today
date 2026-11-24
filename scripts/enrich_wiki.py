#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""维基链接补全（正式）：为无 wikipedia 的记录生成候选文件。

规则（基于基准集98.1%准确率验证）：
- A级：唯一 Person 候选 + label 精确匹配 → 自动写入
- B级：唯一 Person 候选 + label 包含/高相似 → 自动写入
- C级：多 Person 候选 / 非 Person / 低相似 → 待审，不自动写入
- 输出 archive-data/wiki-candidates.json，不直接改主数据
"""
import json, re, sys, time, os, requests, difflib
from wikilink_match import clean_name, first, norm_label, lookup, match_quality

BASE=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
H={'User-Agent':'MementoWeb/1.0 (data enrichment)'}

def sparql_deathdate(uri):
    """查 DBpedia 实体的 deathDate（年份），用于多候选消歧。"""
    q=f'SELECT ?d WHERE {{ <{uri}> <http://dbpedia.org/ontology/deathDate> ?d }} LIMIT 1'
    try:
        r=requests.get('https://dbpedia.org/sparql',params={'query':q,'format':'json'},headers=H,timeout=20)
        if r.status_code==200:
            b=r.json()['results']['bindings']
            if b: return b[0]['d']['value'][:4]
    except Exception: pass
    return None

def is_person_candidate(doc):
    """判断是否可能是人物实体。DBpedia 很多人物的 type 为空，
    因此用排除法：显式非人物类型/资源直接排除，其余视为可能人物。"""
    types=' '.join(doc.get('type') or []) if isinstance(doc,dict) else ''
    uri=first(doc.get('resource'))
    # 显式非人物类型
    bad_type=any(t in types for t in ['/Album','/Film','/Book','/Event','/Place',
                                       '/Organisation','/Company','/Species','/Animal'])
    # 资源名特征：列表、分类、消歧页、纯年份/数字
    tail=uri.split('/')[-1]
    bad_uri=(tail.startswith('List_of_') or tail.startswith('Category:') or
             'disambiguation' in tail.lower() or re.match(r'^\d{4}',tail))
    return not bad_type and not bad_uri

def classify(name, docs):
    """返回 (level, doc, reason, need_date_check)。"""
    persons=[d for d in docs if is_person_candidate(d)]
    if not persons: return 'C',None,'无非人物候选',False
    q=norm_label(name)
    exact=[d for d in persons if norm_label(first(d.get('label')))==q]
    if len(exact)==1:
        # 唯一精确匹配：若存在多个候选，需日期消歧
        return 'A',exact[0],'唯一精确匹配',len(persons)>1
    if len(exact)>1:
        return 'C',None,f'多个精确匹配({len(exact)})',False
    # 包含/相似匹配
    cand=[]
    for d in persons:
        lab=norm_label(first(d.get('label')))
        if (q and lab and (q in lab or lab in q)) or difflib.SequenceMatcher(None,q,lab).ratio()>=0.88:
            cand.append(d)
    if len(cand)==1: return 'B',cand[0],'唯一包含/相似匹配',len(persons)>1
    if len(cand)>1: return 'C',None,f'多个相似匹配({len(cand)})',False
    return 'C',None,'无合格匹配',False

def main():
    s=open(os.path.join(BASE,'data','deaths.js'),encoding='utf-8').read()
    a=json.loads(s[s.index('['):s.rindex(']')+1])
    targets=[x for x in a if not x.get('wikipedia') and x.get('nameOrig')]
    print('待补维基链接:', len(targets), '条')
    auto={}; review={}; stats={'A':0,'B':0,'C':0,'date_reject':0}
    for i,x in enumerate(targets):
        name=clean_name(x['nameOrig'])
        docs=lookup(name)
        if not docs:
            stats['C']+=1; time.sleep(0.25); continue
        level,doc,reason,need_date=classify(name,docs)
        if level=='C':
            stats['C']+=1
            if len(review)<200:
                review[x['id']]={'name':x['name'],'orig':x['nameOrig'],'reason':reason,
                                 'candidates':[norm_label(first(d.get('label'))) for d in docs[:5]]}
            time.sleep(0.25); continue
        uri=first(doc.get('resource'))
        # 多候选时做日期校验
        if need_date:
            dd=sparql_deathdate(uri)
            rec_year=x['date'][:4]
            if dd and abs(int(dd)-int(rec_year))>1:
                stats['date_reject']+=1
                if len(review)<200:
                    review[x['id']]={'name':x['name'],'orig':x['nameOrig'],
                                     'reason':f'日期不符(候选{dd} vs 记录{rec_year})',
                                     'candidates':[norm_label(first(d.get('label'))) for d in docs[:5]]}
                time.sleep(0.25); continue
        wiki='https://en.wikipedia.org/wiki/'+uri.split('/')[-1]
        auto[x['id']]={'name':x['name'],'orig':x['nameOrig'],'wikipedia':wiki,
                       'level':level,'reason':reason,'label':norm_label(first(doc.get('label')))}
        stats[level]+=1
        if (i+1)%200==0: print(f'  已处理 {i+1}/{len(targets)} | A{stats["A"]} B{stats["B"]} C{stats["C"]}')
        time.sleep(0.25)
    out=os.path.join(BASE,'archive-data','wiki-candidates.json')
    json.dump({'auto':auto,'review':review,'stats':stats},open(out,'w',encoding='utf-8'),
              ensure_ascii=False,indent=2)
    print('\n完成:',stats,'| 自动候选',len(auto),'| 待审',len(review))

if __name__=='__main__': main()
