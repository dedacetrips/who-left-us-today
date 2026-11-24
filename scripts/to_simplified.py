#!/usr/bin/env python3
"""
统一将全表中文名转为简体中文
- 使用 zhconv (zh-cn) 转换所有显示名 n 中的繁体/日文旧字体
- 清理 1 条 DBpedia 歧义标签（案件名误作人名）恢复为原名
- 显示名 no（原文名）保持不变
"""
import json, glob, re, os, warnings
warnings.filterwarnings('ignore')
from zhconv import convert

DATA = '/workspace/memento-web/archive-data'
CN = re.compile(r'[\u4e00-\u9fff]')

# DBpedia 歧义标签：id -> 恢复为原名（英文名）
REVERT = {
    '20130221-kaoru-kobayashi': 'Kaoru Kobayashi',
}

def main():
    total = 0
    changed = 0
    reverted = 0
    for p in sorted(glob.glob(os.path.join(DATA, '*.js'))):
        txt = open(p, encoding='utf-8').read()
        head, body = txt.split('=', 1)
        arr = json.loads(body.strip().rstrip(';'))
        c = 0
        for rec in arr:
            total += 1
            # 清理歧义标签
            if rec['id'] in REVERT and rec.get('n') != REVERT[rec['id']]:
                rec['n'] = REVERT[rec['id']]
                rec.pop('ns', None)  # 移除补全标记
                reverted += 1
                c += 1
            # 简繁转换（仅中文名）
            if CN.search(rec.get('n', '')):
                simp = convert(rec['n'], 'zh-cn')
                if simp != rec['n']:
                    rec['n'] = simp
                    changed += 1
                    c += 1
        if c:
            with open(p, 'w', encoding='utf-8') as fp:
                fp.write(head + '= ')
                json.dump(arr, fp, ensure_ascii=False, separators=(',', ':'))
                fp.write(';\n')
            print(os.path.basename(p), '更新', c, '条')
    print('总记录:', total, '| 转简体:', changed, '| 清理歧义:', reverted)

if __name__ == '__main__':
    main()
