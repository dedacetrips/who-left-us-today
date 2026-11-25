#!/usr/bin/env python3
"""核验 2026 主表姓名字段污染：从 identity/id 可靠还原纯净姓名。
保守策略：只改明确污染的记录，逐条输出前后对照供审核。"""
import json, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEATHS = ROOT / 'data' / 'deaths.js'

def load(path):
    s = path.read_text(encoding='utf-8')
    return json.JSONDecoder().raw_decode(s[s.index('{'):])[0]

def unescape(s):
    import html
    return html.unescape(s).strip()

# 身份/机构词：若 identity 首段含这些词，说明首段不是纯人名，需进一步处理
IDENTITY_WORDS = re.compile(
    r'\b(politician|actor|actress|singer|writer|artist|author|journalist|professor|'
    r'doctor|general|minister|senator|mayor|governor|ambassador|judge|president|'
    r'ceo|founder|director|coach|player|athlete|lawyer|engineer|scientist|'
    r'architect|historian|activist|died|was|is|he|she|who|of|and|at|from|as)\b',
    re.I)

def clean_first(first):
    """清洗 identity 首段：去掉 Killing of 前缀、HTML 实体已解。"""
    first = re.sub(r'^Killing of\s+', '', first.strip(), flags=re.I)
    return first.strip()

def extract_name(row, I):
    """返回 (clean_name, reason) 或 (None, None) 表示无需修改。"""
    name = str(row[I['name']] or '').strip()
    ident = unescape(str(row[I['identity']] or ''))
    rid = str(row[I['id']] or '')
    is_a = bool(re.match(r'^.+?\sdead,', name, re.I))
    is_b = name.count(',') >= 2 and not is_a
    if not (is_a or is_b):
        return None, None

    # 优先：identity 首段（dead-people 格式 "Name, description" 中 Name 即纯人名）
    first = clean_first(ident.split(',')[0])
    if first and len(first) < 80 and not IDENTITY_WORDS.search(first):
        return first, ('A类:identity首段' if is_a else 'B类:identity首段')

    # identity 为 "X died on/in..." 句式 → 取 died 前（排除含从句的）
    m = re.match(r'^(.+?)\s+died\s+(?:on|in|from|after|of|at|by)\b', ident, re.I)
    if m and len(m.group(1).strip()) < 80 and not re.search(r'\b(who|which|that)\b', m.group(1), re.I):
        return clean_first(m.group(1).strip()), 'B类:identity-died前'

    # identity 首段含身份词，但 name 首段是纯人名（与 identity 首段起点一致）
    nfirst = name.split(',')[0].strip()
    if ifirst_is := clean_first(ident.split(',')[0]):
        if nfirst.lower().startswith(ifirst_is.lower()[:15]) and not IDENTITY_WORDS.search(nfirst):
            return nfirst, 'B类:name首段'

    # 兜底：id 的 slug 段
    slug = rid.split('-', 1)[1] if '-' in rid else ''
    slug_name = slug.replace('-', ' ').title()
    if slug_name and len(slug_name) < 50 and not re.search(r'\d', slug_name):
        return slug_name, 'B类:id-slug'

    return None, None

def main():
    d = load(DEATHS)
    cols, rows = d['cols'], d['rows']
    I = {k: i for i, k in enumerate(cols)}
    changes = []
    for r in rows:
        clean, reason = extract_name(r, I)
        if clean and clean != str(r[I['name']] or ''):
            changes.append((r, clean, reason))

    print(f'待修复: {len(changes)} 条\n')
    from collections import Counter
    print('分类:', dict(Counter(x[2] for x in changes)), '\n')
    for r, clean, reason in changes:
        print(f"[{reason}]")
        print(f"  旧 name    : {r[I['name']]}")
        print(f"  新 name    : {clean}")
        print(f"  nameOrig旧 : {str(r[I['nameOrig']] or '')[:70]}")

    if '--apply' not in sys.argv:
        print('\n(预览模式，未写入。加 --apply 执行)')
        return

    # 执行修改
    for r, clean, reason in changes:
        r[I['name']] = clean
        r[I['nameOrig']] = clean
    # 保持原排序不变
    jd = lambda o: json.dumps(o, ensure_ascii=False, separators=(',', ':'))
    DEATHS.write_text(
        '// 人物数据：每天离世的世界名人讣告档案（列式压缩）\n'
        + f'window.DEATHS_DATA = {jd({"cols": cols, "rows": rows})};\n',
        encoding='utf-8')
    print(f'\n已写入 {len(changes)} 条修复')

if __name__ == '__main__':
    main()
