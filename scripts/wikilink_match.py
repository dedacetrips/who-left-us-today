#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""维基链接补全：DBpedia Lookup 匹配 + 严格校验。

支持 --test 模式：用已有108条维基链接作基准集，统计命中率与准确率。
正式模式：为无维基链接的记录生成候选文件，不直接写主数据。
"""
import json, re, sys, time, os, requests, difflib

BASE=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
H={'User-Agent':'MementoWeb/1.0 (data enrichment)'}
API='https://lookup.dbpedia.org/api/search'

def first(v):
    if isinstance(v,list): return v[0] if v else ''
    return v or ''

def clean_name(n):
    """清洗 nameOrig：去掉 / 后身份描述、逗号颠倒、括号注释。"""
    n=str(n or '').strip()
    n=n.split('/')[0].strip()          # "山崎 正昭 / Masaaki Yamazaki" → 取第一段
    n=re.sub(r'\s*\([^)]*\)','',n)      # 去括号注释
    n=re.sub(r'\s+',' ',n).strip()
    # "姓, 名" → "名 姓"
    if ',' in n:
        parts=[p.strip() for p in n.split(',')]
        if len(parts)==2: n=parts[1]+' '+parts[0]
    return n

def lookup(name, max_results=5):
    try:
        r=requests.get(API,params={'query':name,'format':'json','maxResults':max_results},
                       headers=H,timeout=25)
        if r.status_code!=200: return []
        return r.json().get('docs',[])
    except Exception:
        return []

def norm_label(s):
    s=re.sub(r'<[^>]+>','',str(s)).lower()
    s=re.sub(r'[^a-z0-9\u4e00-\u9fa5 ]','',s)
    return re.sub(r'\s+',' ',s).strip()

def match_quality(query, doc):
    """返回 (是否接受, 置信度A/B/C, 依据)。只接受 Person 类实体。"""
    types=' '.join(doc.get('type') or [])
    if 'ontology/Person' not in types:
        return False,'C','非人物实体'
    label=norm_label(first(doc.get('label')))
    q=norm_label(query)
    if not label or not q: return False,'C','空标签'
    # 精确匹配
    if label==q: return True,'A','label精确匹配'
    # 包含匹配（如 Richard Sterban vs richard sterban）
    if q in label or label in q: return True,'B','label包含匹配'
    # 编辑距离（短名字放宽）
    ratio=difflib.SequenceMatcher(None,q,label).ratio()
    if ratio>=0.88 and min(len(q),len(label))>=6: return True,'B',f'相似{ratio:.2f}'
    return False,'C',f'不相似{ratio:.2f}'

def expected_uri(wikipedia):
    """从已有维基链接提取预期的 DBpedia resource 名（用于基准对照）。"""
    if not wikipedia: return ''
    m=re.search(r'/wiki/([^#]+)',str(wikipedia))
    if not m: return ''
    from urllib.parse import unquote
    return unquote(m.group(1)).replace(' ','_')

def test():
    s=open(os.path.join(BASE,'data','deaths.js'),encoding='utf-8').read()
    a=json.loads(s[s.index('['):s.rindex(']')+1])
    gold=[x for x in a if x.get('wikipedia')]
    hit=0; correct=0; total=len(gold); samples=[]
    for i,x in enumerate(gold):
        name=clean_name(x['nameOrig'])
        docs=lookup(name)
        if not docs:
            if len(samples)<8: samples.append((x['name'],name,'无返回'))
            time.sleep(0.4); continue
        # 取最佳匹配
        best=None
        for d in docs:
            ok,conf,why=match_quality(name,d)
            if ok and conf=='A': best=(d,conf,why); break
        if not best:
            for d in docs:
                ok,conf,why=match_quality(name,d)
                if ok: best=(d,conf,why); break
        if not best:
            if len(samples)<8: samples.append((x['name'],name,'无合格匹配:'+str([norm_label(first(d.get('label'))) for d in docs[:2]])))
            time.sleep(0.4); continue
        hit+=1
        d,conf,why=best
        uri=first(d.get('resource')).split('/')[-1]
        exp=expected_uri(x['wikipedia'])
        is_correct=(uri.lower()==exp.lower())
        if is_correct: correct+=1
        elif len(samples)<12: samples.append((x['name'],name,f'匹配{uri} 期望{exp}'))
        time.sleep(0.4)
    print(f'基准集 {total} 条 | 命中 {hit} ({hit/total*100:.1f}%) | 准确 {correct} | 命中内准确率 {correct/hit*100:.1f}%')
    print('\n未命中/误配样例:')
    for s in samples: print('  ',s)

if __name__=='__main__':
    if '--test' in sys.argv: test()
