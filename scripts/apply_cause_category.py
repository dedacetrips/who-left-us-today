#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""以「死因规范字典.json」为唯一权威来源，为全量表与精选表建立/重建死因大类字段。

- 字段：causeCategory，位置紧跟 causeOfDeath
- 数值：严格按字典表 中文名 -> 大类 映射；无死因者置 null
- 可重复运行；字典表调整后重跑即可全量同步
"""
import json, glob, os, collections

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DICT = os.path.join(BASE, 'archive-data', '死因规范字典.json')

def load_map():
    rows = json.load(open(DICT, encoding='utf-8'))
    return {x['name']: x['category'] for x in rows}

def process(path, cmap):
    s = open(path, encoding='utf-8').read()
    arr = json.loads(s[s.index('['):s.rindex(']')+1])
    head = s[:s.index('[')]
    changed = 0
    for x in arr:
        cause = x.get('causeOfDeath')
        cat = cmap.get(cause) if cause else None
        if cause and cat is None:
            raise ValueError(f'字典表缺少死因映射: {cause} (id={x.get("id")})')
        if x.get('causeCategory') != cat:
            changed += 1
        x['causeCategory'] = cat
    # 规范字段顺序：causeCategory 紧跟 causeOfDeath
    ordered = []
    for x in arr:
        d = {}
        for k, v in x.items():
            if k == 'causeCategory':
                continue
            d[k] = v
            if k == 'causeOfDeath':
                d['causeCategory'] = x['causeCategory']
        ordered.append(d)
    open(path, 'w', encoding='utf-8').write(
        head + json.dumps(ordered, ensure_ascii=False, separators=(',', ':')) + ';\n')
    return len(arr), changed

def main():
    cmap = load_map()
    print(f'字典表映射: {len(cmap)} 种死因 -> {sorted(set(cmap.values()))}')
    total = 0; total_changed = 0
    for f in sorted(glob.glob(os.path.join(BASE, 'archive-data', '20*.js'))):
        n, c = process(f, cmap)
        total += n; total_changed += c
    n, c = process(os.path.join(BASE, 'data', 'deaths.js'), cmap)
    print(f'全表: {total} 条, 重填大类 {total_changed} 条')
    print(f'精选表: {n} 条, 重填大类 {c} 条')

if __name__ == '__main__':
    main()
