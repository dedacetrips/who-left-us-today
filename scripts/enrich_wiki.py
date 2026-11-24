#!/usr/bin/env python3
"""
用 DBpedia Lookup 给线上精选表补充维基百科链接
- 查询名优先级：nameOrig（英文名）> name（中文名）
- 只接受 typeName 含 Person 的结果
- 置信度：exact（标签==查询名）> qualified（标签主体==查询名，带括号消歧）
- 输出：更新 data/deaths.js 的 wikipedia 字段
"""
import json, subprocess, requests, urllib.parse, re, html, time, os

ROOT = '/workspace/memento-web'
DEATHS = os.path.join(ROOT, 'data/deaths.js')
UA = {'User-Agent': 'WorkBuddy/1.0 (wiki enrichment)'}

def clean(s):
    return re.sub(r'</?B>', '', html.unescape(str(s))).strip()

def lookup(name):
    url = 'https://lookup.dbpedia.org/api/search?query=' + urllib.parse.quote(name) + '&maxResults=5&format=json'
    try:
        r = requests.get(url, headers=UA, timeout=25)
        if r.status_code != 200: return []
        out = []
        for doc in r.json().get('docs', []):
            types = doc.get('typeName', [])
            uri = doc.get('resource', [''])[0]
            lab = clean(doc.get('label', [''])[0])
            if 'Person' in types and uri and 'dbpedia.org/resource/' in uri:
                out.append((lab, uri))
        return out
    except Exception:
        return []

def match(label, query):
    q = clean(query).lower()
    l = clean(label).lower()
    if l == q: return 'exact'
    # 带括号消歧：Dan Hicks (singer) -> Dan Hicks
    base = re.sub(r'\s*\([^)]+\)$', '', l).strip()
    if base == q: return 'qualified'
    return None

def main():
    js = "global.window={};require('%s');console.log(JSON.stringify(window.DEATHS_DATA))" % DEATHS
    A = json.loads(subprocess.check_output(['node','-e',js], text=True))

    stats = {'exact':0, 'qualified':0, 'existing':0, 'none':0}
    for i, x in enumerate(A):
        if x.get('wikipedia'):
            stats['existing'] += 1
            continue
        queries = []
        if x.get('nameOrig'): queries.append(x['nameOrig'])
        if not queries and x.get('name'): queries.append(x['name'])
        # 中文名若含斜杠（如「黄正利 / 황정리 / Hwang Jang Lee」）取最后英文段
        if queries and '/' in queries[0]:
            parts = [p.strip() for p in queries[0].split('/')]
            en = [p for p in parts if re.search(r'[A-Za-z]{3}', p)]
            if en: queries.insert(0, en[-1])
        found = None
        for q in queries[:2]:
            res = lookup(q)
            for lab, uri in res:
                conf = match(lab, q)
                if conf:
                    title = uri.split('/resource/')[-1]
                    found = ('https://en.wikipedia.org/wiki/' + urllib.parse.quote(title), conf)
                    break
            if found: break
            time.sleep(0.15)
        if found:
            x['wikipedia'] = found[0]
            x['wikipediaConf'] = found[1]
            stats[found[1]] += 1
        else:
            stats['none'] += 1
        if (i+1) % 25 == 0:
            print('进度', i+1, '/', len(A), stats, flush=True)

    with open(DEATHS, 'w', encoding='utf-8') as fp:
        fp.write('// 人物数据：每天离世的世界名人讣告档案\n')
        fp.write('window.DEATHS_DATA = ')
        json.dump(A, fp, ensure_ascii=False, separators=(',', ':'))
        fp.write(';\n')
    print('最终:', stats)
    print('有维基总数:', sum(1 for x in A if x.get('wikipedia')))

if __name__ == '__main__':
    main()
