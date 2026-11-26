# -*- coding: utf-8 -*-
"""
修复历史归档中 name 字段被写成「姓名 + 身份描述整句」的污染

策略（保守）：
  - 从 identity 首句提取真实姓名，或从 name 中按身份描述词截断
  - 只改 name + nameOrig（两者原本相同，同步修复）
  - 事件名 / 职位名 / 合法贵族全名 → 不自动改，归入待核

用法：
  python3.11 scripts/fix_title_pollution.py                 # dry-run
  python3.11 scripts/fix_title_pollution.py --apply         # 应用
"""
import argparse
import datetime
import glob
import html
import json
import os
import re

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ARC = os.path.join(BASE, 'archive-data')
YEAR_FILES = sorted(f for f in glob.glob(os.path.join(ARC, '20[0-2][0-9].js'))
                    if not os.path.basename(f).startswith('2026'))
REPORT = os.path.join(ARC, 'history-title-fix-20261126.json')

# 身份描述词（出现在 name 中即为污染标志，也作为截断点）
IDENTITY_WORDS = re.compile(
    r'\b(?:politician|actor|actress|footballer|swimmer|musician|singer|songwriter|writer|author|journalist'
    r'|basketball|baseball|soccer|golfer|boxer|coach|manager|director|producer|businessman|executive'
    r'|minister|senator|governor|mayor|diplomat|general|officer|police|cleric|bishop|priest|rabbi'
    r'|scientist|professor|doctor|physician|surgeon|engineer|artist|painter|photographer|architect'
    r'|historian|economist|academic|educator|teacher|lawyer|attorney|judge|activist|advocate'
    r'|model|dancer|rapper|guitarist|drummer|bassist|pianist|violinist|composer|conductor'
    r'|veteran|sailor|soldier|astronaut|chef|farmer|rose breeder|horticulturist|lobbyist'
    r'|Olympic|champion|medalist|MP\b|MLA\b|MSP\b|CEO\b|co-founder|member of the House|House of Rep)'
    r'\b', re.I)
CAUSE_WORDS = re.compile(r'\b(?:died|death|cancer|heart attack|stroke|complications|shot|killed|suicide|accident|illness|disease|after a|due to|following)\b', re.I)

# 明确排除：事件名 / 职位名 / 贵族头衔（合法全名）
EVENT_NAME = re.compile(r'^Killing of\b|^20\d{2}\s|^Trump\b|^death of\b')
OFFICE_NAME = re.compile(r'^(?:The\s+)?(?:mayor|president|prime minister|governor|senator|minister|chief|commissioner|sheriff)\s+of\b', re.I)
NOBLE_NAME = re.compile(r',\s*(?:Baron|Duke|Duchess|Count|Countess|Earl|Marquess|Marquis|Viscount|Viscountess|Lord|Lady|Sir)\b', re.I)


def parse(path):
    s = open(path, encoding='utf-8').read(); i = s.find('[')
    arr, end = json.JSONDecoder().raw_decode(s[i:])
    return arr, s[:i], s[i + end:]


def save(path, arr, header, tail):
    with open(path, 'w', encoding='utf-8') as f:
        f.write(header + json.dumps(arr, ensure_ascii=False, separators=(',', ':')) + tail)


def extract_from_identity(idt):
    """从 identity 首句提取真实姓名"""
    idt = html.unescape(idt).strip()
    # "David Smith, an Australian politician and ..."
    m = re.match(r'^([A-Z][\w\u00c0-\u024f\.\'\-\u2019 ]{2,40}?),\s+(?:a|an|the)\s+', idt)
    if m:
        return m.group(1).strip()
    # "Godiya Akwashiki, Nigerian politician ..." —— 国别形容词开头无冠词
    m = re.match(r'^([A-Z][\w\u00c0-\u024f\.\'\-\u2019 ]{2,40}?),\s+(?:Nigerian|American|British|Canadian|Australian|Indian|Pakistani|Nepali|Chinese|Japanese|Korean|Filipino|Ghanaian|Kenyan|South African|Nigerian|Ugandan|Zimbabwean|Iranian|Iraqi|Syrian|Lebanese|Israeli|Palestinian|Romanian|Polish|Turkish|Egyptian|Moroccan|Brazilian|Mexican|Antiguan|Fijian|Samoan|Tongan)\s+', idt)
    if m:
        return m.group(1).strip()
    # "Peter Terry died on April 10, 2026."
    m = re.match(r'^([A-Z][\w\u00c0-\u024f\.\'\-\u2019 ]{2,40}?)\s+(?:died|was|is|passed away|succumbed)\b', idt)
    if m:
        return m.group(1).strip()
    # "Sir Gerald Watt, Antiguan politician"
    m = re.match(r'^((?:Sir|Lord|Lady|Dame|Dr|Prof)\s+[A-Z][\w\u00c0-\u024f\.\'\-\u2019 ]{2,40}?),', idt)
    if m:
        return m.group(1).strip()
    return None


def extract_from_name(nm, full_name=None):
    """从 name 中按身份描述词截断，取姓名部分。
    若有 identity 提取的正式名，用其姓氏定位截断位置（避免保留 American/Canadian 等国别词）。"""
    nm = html.unescape(nm).strip()
    # 贵族头衔合法全名，不动
    if NOBLE_NAME.search(nm):
        return None
    # 找身份描述词的起始位置
    m = IDENTITY_WORDS.search(nm) or CAUSE_WORDS.search(nm)
    if not m:
        return None
    head = nm[:m.start()].strip().rstrip(',')
    # 清理尾部年龄 "Morris "B.B." Dickerson, 71, "
    head = re.sub(r',\s*\d{1,3}\s*,?\s*$', '', head).strip().rstrip(',').strip()
    head = re.sub(r'^The\s+', '', head)
    # 用正式名的姓氏精确定位：name 里保留到姓氏为止，扔掉后面的国别/修饰词
    if full_name:
        surname = re.sub(r'[^\w\u00c0-\u024f]', '', full_name.split()[-1].lower())
        words = head.split()
        for i, w in enumerate(words):
            if re.sub(r'[^\w\u00c0-\u024f]', '', w.lower()) == surname:
                head = ' '.join(words[:i + 1])
                break
    else:
        # 无正式名时：用国别/族裔形容词作为姓名与身份的分界
        NAT = re.compile(
            r'^(?:American|British|Canadian|Australian|Irish|Scottish|English|German|French|Italian'
            r'|Spanish|Dutch|Swedish|Norwegian|Danish|Finnish|Polish|Russian|Ukrainian|Turkish'
            r'|Indian|Pakistani|Bangladeshi|Sri Lankan|Nepali|Chinese|Japanese|Korean|Vietnamese'
            r'|Filipino|Indonesian|Malaysian|Singaporean|Thai|Nigerian|Ghanaian|Kenyan|South African'
            r'|Egyptian|Moroccan|Algerian|Tunisian|Brazilian|Argentinian|Chilean|Mexican|Cuban'
            r'|New Zealand|South African|Antiguan|Iranian|Iraqi|Syrian|Lebanese|Israeli|Palestinian'
            r'|Romanian|Hungarian|Czech|Slovak|Greek|Portuguese|Austrian|Swiss|Belgian|Welsh)\b', re.I)
        words = head.split()
        for i, w in enumerate(words):
            if NAT.match(w):
                head = ' '.join(words[:i])
                break
        # 再去掉残留的逗号+年龄
        head = re.sub(r',\s*\d{1,3}.*$', '', head).strip().rstrip(',').strip()
    if not head or len(head) > 45:
        return None
    return head


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--apply', action='store_true')
    args = ap.parse_args()

    fixes = []      # 确认可修复
    reviews = []    # 待核
    total = 0

    for path in YEAR_FILES:
        arr, header, tail = parse(path)
        year = os.path.basename(path)[:4]
        total += len(arr)
        for r in arr:
            nm = html.unescape(str(r.get('name', '')))
            idt = str(r.get('identity', ''))
            if len(nm) < 30 or not (IDENTITY_WORDS.search(nm) or CAUSE_WORDS.search(nm)):
                continue
            # 排除事件名、职位名、贵族全名
            if EVENT_NAME.search(nm) or OFFICE_NAME.search(nm) or NOBLE_NAME.search(nm):
                reviews.append({'id': r['id'], 'year': year, 'name': nm, 'identity': idt,
                                'reason': '事件名/职位名/贵族全名，需人工判断'})
                continue
            real = extract_from_identity(idt)
            src = 'identity'
            if not real:
                real = extract_from_name(nm)
                src = 'name截断'
            if not real:
                reviews.append({'id': r['id'], 'year': year, 'name': nm, 'identity': idt,
                                'reason': '无法自动提取真实姓名'})
                continue
            # 校验：提取值应是 name 的前缀（大小写/标点宽松匹配）
            nm_key = re.sub(r'[\s\.\'\-\u2019,]', '', nm.lower())
            real_key = re.sub(r'[\s\.\'\-\u2019,]', '', real.lower())
            is_prefix = nm_key.startswith(real_key)
            # 若 identity 给出的是更完整正式名（name 用常用名），改用 name 截断的常用名
            if not is_prefix and src == 'identity':
                alt = extract_from_name(nm, full_name=real)
                if alt:
                    real, src = alt, 'name截断(保留常用名)'
                    real_key = re.sub(r'[\s\.\'\-\u2019,]', '', real.lower())
                    is_prefix = nm_key.startswith(real_key)
            fixes.append({'id': r['id'], 'year': year, 'old_name': nm, 'new_name': real,
                          'source': src, 'prefix_ok': is_prefix, 'identity': idt[:120]})

    print(f'总条数: {total}')
    print(f'可修复: {len(fixes)}')
    print(f'  其中 identity 提取: {sum(1 for x in fixes if x["source"]=="identity")}')
    print(f'  其中 name 截断: {sum(1 for x in fixes if "name截断" in x["source"])}')
    print(f'  前缀校验通过: {sum(1 for x in fixes if x["prefix_ok"])}')
    print(f'待核（不改）: {len(reviews)}')
    for x in reviews:
        print(f"  [{x['year']}] {x['id']:40s} | {x['name'][:55]} | {x['reason']}")

    print('\n=== 可修复明细 ===')
    for x in fixes:
        print(f" [{x['year']}] {x['id']:42s}")
        print(f"    {x['old_name'][:70]}")
        print(f" -> {x['new_name']}  ({x['source']}, 前缀{'✓' if x['prefix_ok'] else '✗'})")

    report = {
        'generated_at': datetime.datetime.now().isoformat(timespec='seconds'),
        'description': '修复 name 字段「姓名+身份描述整句」污染，只改 name/nameOrig',
        'total_rows': total,
        'fix_count': len(fixes),
        'review_count': len(reviews),
        'fixes': fixes,
        'reviews': reviews,
        'applied': False,
    }
    with open(REPORT, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f'\n报告: {os.path.relpath(REPORT, BASE)}')

    if not args.apply:
        print('DRY-RUN：未修改数据。')
        return

    fixmap = {}
    for x in fixes:
        fixmap.setdefault(x['year'], {})[x['id']] = x['new_name']
    changed = 0
    for path in YEAR_FILES:
        year = os.path.basename(path)[:4]
        if year not in fixmap:
            continue
        arr, header, tail = parse(path)
        dirty = False
        for r in arr:
            if r['id'] in fixmap[year]:
                new = fixmap[year][r['id']]
                if r.get('name') != new or r.get('nameOrig') != new:
                    r['name'] = new
                    r['nameOrig'] = new
                    dirty = True
        if dirty:
            save(path, arr, header, tail)
            changed += 1
            print(f'  写入 {year}.js: {len(fixmap[year])} 条')
    report['applied'] = True
    report['applied_at'] = datetime.datetime.now().isoformat(timespec='seconds')
    with open(REPORT, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f'\n应用完成: {len(fixes)} 条，涉及 {changed} 个文件')


if __name__ == '__main__':
    main()
