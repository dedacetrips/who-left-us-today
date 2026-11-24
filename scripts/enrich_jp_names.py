#!/usr/bin/env python3
"""
根据 DBpedia 补全人物中文名
- 目标：清洗后分片中「国家含日本」且「显示名无中文」的记录
- 数据源：DBpedia 直读 JSON（en.wikipedia.org/wiki/<Title> -> rdfs:label）
- 优先级：zh/zh-cn/zh-hans 标签 > ja 标签（日文汉字，日本人名可直接用）
- 输出：name-enrichments.json（id -> 补全名），并写回年度分片
"""
import json, requests, urllib.parse, re, time, os, sys, concurrent.futures, threading

ROOT = '/workspace/memento-web'
DATA = os.path.join(ROOT, 'archive-data')
SRC_XLSX = '/root/uploads/1795504916120856186-人物全表_116817人.xlsx'
CN = re.compile(r'[\u4e00-\u9fff]')

# 日文假名（纯假名不算可用中文名）检测
KANA = re.compile(r'[\u3040-\u30ff]')

UA = {'User-Agent': 'WorkBuddy/1.0 (archive name enrichment; contact: local)'}


def is_usable(name):
    """判断 DBpedia 标签是否可作为中文显示名"""
    if not name or not CN.search(name):
        return False
    # 纯假名（如 かしぶち哲郎 含假名但也有汉字，可用；すまけい 全假名，不合适）
    if KANA.search(name):
        Han = len(CN.findall(name))
        kana = len(KANA.findall(name))
        if Han < kana:  # 假名多于汉字，跳过
            return False
    return True


def get_labels(title):
    """从 DBpedia 取标签，返回 (zh, ja)"""
    if not title:
        return None, None
    api = 'https://dbpedia.org/data/' + urllib.parse.quote(title, safe='') + '.json'
    for attempt in range(3):
        try:
            r = requests.get(api, headers=UA, timeout=30)
            if r.status_code == 404:
                return None, None
            if r.status_code != 200:
                time.sleep(1 + attempt)
                continue
            d = r.json()
            key = 'http://dbpedia.org/resource/' + title
            labels = d.get(key, {}).get('http://www.w3.org/2000/01/rdf-schema#label', [])
            zh = ja = None
            for x in labels:
                lang, val = x.get('lang'), x.get('value', '')
                if lang in ('zh', 'zh-cn', 'zh-hans') and not zh:
                    zh = val
                elif lang == 'ja' and not ja:
                    ja = val
            return zh, ja
        except Exception:
            time.sleep(1 + attempt)
    return None, None


def main():
    # 读取原始 xlsx 的 wikipediaUrl（清洗分片里的 w 字段已有）
    years = list(range(2013, 2027))
    store = {}
    for y in years:
        with open(os.path.join(DATA, f'{y}.js'), encoding='utf-8') as fp:
            txt = fp.read()
        # 去掉前缀和结尾分号
        js = txt.split('=', 1)[1].strip().rstrip(';')
        store[y] = json.loads(js)

    targets = []
    for y, arr in store.items():
        for rec in arr:
            jp = '日本' in rec.get('c', '').split(';')
            has_cn = bool(CN.search(rec.get('n', '')))
            if jp and not has_cn:
                title = ''
                if rec.get('w'):
                    m = re.search(r'/wiki/(.+)$', rec['w'])
                    if m:
                        title = urllib.parse.unquote(m.group(1))
                targets.append((y, rec['id'], rec.get('no', rec['n']), title))

    print(f'目标记录: {len(targets)}，其中有维基链接: {sum(1 for t in targets if t[3])}')

    results = {}
    lock = threading.Lock()
    done = [0]

    def work(t):
        y, rid, name, title = t
        zh, ja = get_labels(title)
        chosen = None
        source = None
        if is_usable(zh):
            chosen, source = zh, 'zh'
        elif is_usable(ja):
            chosen, source = ja, 'ja'
        with lock:
            done[0] += 1
            if chosen:
                results[rid] = {'name': chosen, 'source': source, 'orig': name}
            if done[0] % 25 == 0:
                print(f'  进度 {done[0]}/{len(targets)}，已补全 {len(results)}', flush=True)

    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as ex:
        list(ex.map(work, targets))

    print(f'补全成功: {len(results)} / {len(targets)}')

    # 写回分片
    for y, arr in store.items():
        changed = 0
        for rec in arr:
            hit = results.get(rec['id'])
            if hit:
                rec['n'] = hit['name']
                rec['ns'] = hit['source']  # 标记补全来源
                changed += 1
        with open(os.path.join(DATA, f'{y}.js'), 'w', encoding='utf-8') as fp:
            fp.write(f'window.ARCHIVE_{y} = ')
            json.dump(arr, fp, ensure_ascii=False, separators=(',', ':'))
            fp.write(';\n')
        print(f'  {y}.js 更新 {changed} 条')

    # 保存补全清单
    out = os.path.join(DATA, 'name-enrichments.json')
    with open(out, 'w', encoding='utf-8') as fp:
        json.dump(results, fp, ensure_ascii=False, indent=2)
    print('补全清单:', out, os.path.getsize(out), 'bytes')


if __name__ == '__main__':
    main()
