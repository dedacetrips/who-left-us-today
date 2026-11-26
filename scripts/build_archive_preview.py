# -*- coding: utf-8 -*-
"""
生成自包含预览版 archive-preview.html

把 archive-index.js 与 13 个年度数据文件全部内联进单个 HTML，
不依赖本地 HTTP 服务，直接在预览面板/浏览器打开即可看到真实数据。

用法: python3.11 scripts/build_archive_preview.py
"""
import os

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(BASE, 'archive.html')
IDX = os.path.join(BASE, 'archive-data', 'archive-index.js')
OUT = os.path.join(BASE, 'archive-preview.html')

s = open(SRC, encoding='utf-8').read()

# 1) 内联年度索引
needle = '<script src="archive-data/archive-index.js"></script>'
assert needle in s, '未找到索引脚本标签'
idx = open(IDX, encoding='utf-8').read()
s = s.replace(needle, '<!-- 内联索引 -->\n<script>\n' + idx + '\n</script>')

# 2) 在页面主脚本之前内联全部年度数据
years = list(range(2013, 2027))
blocks = []
for y in years:
    p = os.path.join(BASE, 'archive-data', f'{y}.js')
    blocks.append(f'<!-- 内联 {y} -->\n<script>\n' + open(p, encoding='utf-8').read() + '\n</script>')

marker = '<script>\n/* ═══════════ 历史档案页 ═══════════'
assert marker in s, '未找到主脚本标记'
s = s.replace(marker, '\n'.join(blocks) + '\n\n' + marker)

with open(OUT, 'w', encoding='utf-8') as f:
    f.write(s)

print(f'已生成 {os.path.basename(OUT)}')
print(f'文件大小: {os.path.getsize(OUT) / 1024 / 1024:.2f} MB')
print(f'内联年度: {years[0]}–{years[-1]} 共 {len(years)} 年')
