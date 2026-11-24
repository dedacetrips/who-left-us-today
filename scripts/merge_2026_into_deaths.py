#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""将全量表 2026 年数据合并进精选表 data/deaths.js。

规则：
- 以 id 为唯一键；精选表已有记录优先保留（内容更丰富）
- 全表 2026 年中不在精选表的记录补入
- 字段结构保持与线上一致（19 字段），顺序不变
- 结果按 date 降序、同日按 id 升序排列
"""
import json, os

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
P_DEATHS = os.path.join(BASE, 'data', 'deaths.js')
P_2026 = os.path.join(BASE, 'archive-data', '2026.js')

def load(path):
    s = open(path, encoding='utf-8').read()
    head = s[:s.index('[')]
    arr = json.loads(s[s.index('['):s.rindex(']')+1])
    return head, arr

def main():
    h1, online = load(P_DEATHS)
    h2, y26 = load(P_2026)
    fields = list(online[0].keys())
    assert fields == list(y26[0].keys()), '字段结构不一致'
    on_ids = {x['id'] for x in online}
    # 精选表优先，全表只补不存在的
    merged = list(online)
    added = [x for x in y26 if x['id'] not in on_ids]
    merged.extend(added)
    # 规范字段顺序 + 排序
    normalized = []
    for x in merged:
        normalized.append({k: x.get(k) for k in fields})
    normalized.sort(key=lambda x: (x['date'], x['id']), reverse=True)
    # 降序日期，同日 id 升序（用负号技巧改为分别处理）
    normalized.sort(key=lambda x: x['id'])
    normalized.sort(key=lambda x: x['date'], reverse=True)
    open(P_DEATHS, 'w', encoding='utf-8').write(
        h1 + json.dumps(normalized, ensure_ascii=False, separators=(',', ':')) + ';\n')
    print(f'精选表原有: {len(online)}')
    print(f'全表2026补入: {len(added)}')
    print(f'重叠跳过: {len(y26)-len(added)}')
    print(f'合并后总数: {len(normalized)}')
    print(f'日期范围: {normalized[-1]["date"]} ~ {normalized[0]["date"]}')

if __name__ == '__main__':
    main()
