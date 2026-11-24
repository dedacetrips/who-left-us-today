#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成前端懒加载的来源链接文件 data/source-links.js。

从 extra.json 的 sourceUrls 提取 id -> [{n:显示名, u:URL}]，
前端详情页打开时按需加载，把来源文本渲染成可点击链接。
"""
import json, os, collections, re

BASE=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ex=json.load(open(os.path.join(BASE,'archive-data','extra.json'),encoding='utf-8'))
# 精选表（source 含中文人工来源）优先：这些记录保留纯文本，不渲染 URL 链接，
# 避免人工来源与原始表 URL 描述不同而误导读者。
s=open(os.path.join(BASE,'data','deaths.js'),encoding='utf-8').read()
deaths=json.loads(s[s.index('['):s.rindex(']')+1])
skip_ids={str(x['id']) for x in deaths
          if re.search(r'[\u4e00-\u9fa5]', str(x.get('source') or ''))}
links={}
for id_,v in ex.items():
    if id_ in skip_ids: continue
    su=v.get('sourceUrls')
    if not su: continue
    seen=set(); items=[]
    for b in su:
        url=b.get('url',''); pub=b.get('publisher','')
        if not url or url in seen: continue
        seen.add(url)
        items.append({'n':pub,'u':url})
    if items: links[id_]=items

out='window.SOURCE_LINKS = '+json.dumps(links,ensure_ascii=False,separators=(',',':'))+';\n'
path=os.path.join(BASE,'data','source-links.js')
open(path,'w',encoding='utf-8').write(out)
print('生成', len(links), '条来源链接, 文件大小:', round(len(out.encode())/1024,1),'KB')
