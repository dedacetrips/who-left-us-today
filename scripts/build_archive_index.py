# -*- coding: utf-8 -*-
"""生成历史归档年度索引 archive-data/archive-index.js（元信息，供 archive.html 首屏用）"""
import glob
import json
import os
from collections import Counter

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ARC = os.path.join(BASE, 'archive-data')
OUT = os.path.join(ARC, 'archive-index.js')

files = sorted(f for f in glob.glob(os.path.join(ARC, '20[0-2][0-9].js'))
               if 'backup' not in f and 'preview' not in f)

years = []
for f in files:
    s = open(f, encoding='utf-8').read()
    i = s.find('[')
    arr = json.JSONDecoder().raw_decode(s[i:])[0]
    year = os.path.basename(f)[:4]
    dates = sorted(r.get('date', '') for r in arr)
    fields = Counter()
    ages = []
    countries = Counter()
    for r in arr:
        fields.update(r.get('fields', []) or [])
        countries[r.get('country', '')] += 1
        a = r.get('age')
        if isinstance(a, (int, float)) and a > 0:
            ages.append(a)
    years.append({
        'year': year,
        'count': len(arr),
        'file': f'archive-data/{year}.js',
        'var': f'ARCHIVE_{year}',
        'dateMin': dates[0] if dates else '',
        'dateMax': dates[-1] if dates else '',
        'avgAge': round(sum(ages) / len(ages)) if ages else 0,
        'fields': dict(fields),
        'topCountries': dict(countries.most_common(8)),
    })
    print(f"{year}: {len(arr)} 条, {dates[0]}~{dates[-1]}, 平均{round(sum(ages)/len(ages)) if ages else 0}岁")

# 年份降序：当年在前（2026, 2025, 2024 …）
years.reverse()

total = sum(y['count'] for y in years)
obj = {
    'total': total,
    'years': years,
    'fieldOrder': ['科技', '文艺', '影视', '军政', '社科', '体育', '医药', '商业', '传媒', '宗教', '其他'],
}
with open(OUT, 'w', encoding='utf-8') as f:
    f.write('window.ARCHIVE_INDEX = ' + json.dumps(obj, ensure_ascii=False, separators=(',', ':')) + ';\n')
print(f'\n总条数: {total}')
print(f'索引已写入: {os.path.relpath(OUT, BASE)} ({os.path.getsize(OUT)} B)')
