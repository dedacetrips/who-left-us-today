# -*- coding: utf-8 -*-
"""
2013–2025 历史归档数据清洗（保守、分层、可回滚）

分层策略：
  A层 确定性字段修复（默认纳入 --apply）：
    A1 HTML 实体 decode（name / nameOrig / identity）
    A2 identity 纯数字 / 数字+符号 / 姓名后缀 → 清空（这类值是把年龄或后缀误当身份）
  B层 非人类实体移除（赛马 / 动物）：严格规则生成候选，人工核对后写入显式 id 清单
  C层 标记待核（只记清单，不改数据）：事件名误作人名、URL slug 型姓名、超长姓名

用法：
  python3.11 scripts/clean_history.py                 # dry-run：只生成报告，不动数据
  python3.11 scripts/clean_history.py --apply         # 应用 A 层 + B 层已确认清单
  python3.11 scripts/clean_history.py --apply-a-only  # 只应用 A 层

备份目录：archive-data/history-backup-20261126-093835/
"""
import argparse
import datetime
import glob
import html
import json
import os
import re
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ARC = os.path.join(BASE, 'archive-data')
YEAR_FILES = sorted(
    f for f in glob.glob(os.path.join(ARC, '20[0-2][0-9].js'))
    if not os.path.basename(f).startswith('2026')
)
REPORT = os.path.join(ARC, 'history-clean-report-20261126.json')
CONFIRMED_FILE = os.path.join(ARC, 'history-nonhuman-confirmed-20261126.json')

# ---------- 规则 ----------
ENT = re.compile(r'&(?:#\d+|#x[0-9a-fA-F]+|[a-zA-Z]+);')
NUMERIC_ONLY = re.compile(r'^\d+$')
NUM_SYM_ONLY = re.compile(r'^[\d\-\?\u200e~+]+$')          # 94?, 11+, ~40, 8-9
NAME_SUFFIX = re.compile(r'^(?:Jr|Sr|II|III|IV|V)$', re.I)   # 姓名后缀被误当身份
KEEP_AGE_HINT = re.compile(r'^\d+s$', re.I)                  # 60s/70s 保留为年龄线索

# 动物物种词（去括号后判定，避免作品名误伤）
ANIMAL_WORD = re.compile(
    r'\b(racehorse|thoroughbred|standardbred|horse|stallion|mare|filly|gelding|colt|pony|donkey|mule'
    r'|dog|cat|kitten|puppy|elephant|lion|tiger|bear|gorilla|chimpanzee|monkey|penguin|goat|sheep|lamb'
    r'|pig|boar|hog|cow|bull|calf|camel|llama|alpaca|rabbit|greyhound|hound|hippopotamus|rhinoceros'
    r'|buffalo|deer|elk|moose|zebra|giraffe|kangaroo|koala|panda|leopard|cheetah|wolf|fox)\b', re.I)
# 人类职业 / 关系词：出现则说明 identity 描述的是人
HUMAN_ROLE = re.compile(
    r'jockey|trainer|breeder|owner|rider|driver|manager|walker|musher|wrangler|broadcaster|announcer|commentator'
    r'|racer|handler|boxer|fighter|wrestler|wrestling|referee|stuntman|inspiration|sled|jockey|teacher'
    r'|artist|cartoonist|comics|writer|author|journalist|photographer|sculptor|painter|designer|architect'
    r'|politician|actor|actress|singer|musician|drummer|guitarist|rapper|coach|president|founder'
    r'|executive|businessman|magnate|veterinarian|surgeon|doctor|scientist|researcher|professor'
    r'|engineer|farmer|historian|chief|attorney|lawyer|ventriloquist|director|playwright|producer'
    r'|wife|husband|daughter|son|mother|father|brother|sister|friend|spokesman|priest|prelate|cleric'
    r'|killed|murdered|died|victim|king|queen|nobleman|noblewoman|aristocrat|mascot', re.I)

EVENT = re.compile(
    r'crash|earthquake|explosion|attacks?|tsunami|ambush|flood|massacre|shooting|siege|bombing'
    r'|airforce|air force|war\b|battle|epidemic|outbreak|derail|collision|stampede|helicopter'
    r'|plane|missile|strike|disaster|collision|people killed', re.I)
SLUG = re.compile(r'https?|www|\.com|\.html|/[a-z]{3,}\d{6,}|20\d{6}-http', re.I)

def load_confirmed_ids():
    """读取人工核对后确认移除的非人类实体 id 清单"""
    if not os.path.exists(CONFIRMED_FILE):
        return set()
    d = json.load(open(CONFIRMED_FILE, encoding='utf-8'))
    return set(d.get('ids', []))


CONFIRMED_NONHUMAN_IDS = load_confirmed_ids()

# C 层：合法的长姓名特征（贵族头衔 / 复姓），不误判
NOBLE = re.compile(r'\b(?:Baron|Duke|Duchess|Count|Countess|Earl|Marquess|Marquis|Viscount|Lord|Lady|Sir|Princess|Prince)\b', re.I)


def load_year(path):
    s = open(path, encoding='utf-8').read()
    i = s.find('[')
    arr, end = json.JSONDecoder().raw_decode(s[i:])
    header = s[:i]
    tail = s[i + end:]
    return arr, header, tail


def save_year(path, arr, header, tail):
    body = json.dumps(arr, ensure_ascii=False, separators=(',', ':'))
    with open(path, 'w', encoding='utf-8') as f:
        f.write(header + body + tail)


def unescape_fields(r):
    """A1: 解码 HTML 实体，返回改动详情"""
    changes = {}
    for k in ('name', 'nameOrig', 'identity'):
        v = r.get(k)
        if isinstance(v, str) and ENT.search(v):
            nv = html.unescape(v)
            if nv != v:
                changes[k] = (v, nv)
    return changes


def should_clear_identity(v):
    """A2: 判定 identity 是否为噪音值"""
    if not isinstance(v, str):
        return False
    t = v.strip()
    if not t:
        return False
    if KEEP_AGE_HINT.match(t):         # 60s 等保留
        return False
    if NUMERIC_ONLY.match(t) or NUM_SYM_ONLY.match(t) or NAME_SUFFIX.match(t):
        return True
    if t in ('-', '?', '??', '???', '--', '—', 'N/A', 'n/a', 'unknown'):
        return True
    return False


def is_nonhuman(idt):
    """B层: 严格判定 identity 是否为非人类实体"""
    if not isinstance(idt, str):
        return False
    # 去括号内容（作品名 / 地点名，如 The Curse of the Cat People、Baia Mare）
    # 注意：数据里存在大量被截断的括号（如 "... (Buffalo Bills" 无右括号），
    # 先把未闭合括号及其后内容整段截掉，避免 Buffalo/Cat 等词误伤人类条目
    core = idt
    p = core.find('(')
    if p >= 0 and core.find(')', p) < 0:
        core = core[:p]
    core = re.sub(r'\([^)]*\)', ' ', core)
    core = re.sub(r'\[[^\]]*\]', ' ', core)
    if HUMAN_ROLE.search(core):        # 出现人类职业 → 判定为人
        return False
    return bool(ANIMAL_WORD.search(core))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--apply', action='store_true', help='应用 A 层 + B 层已确认清单')
    ap.add_argument('--apply-a-only', action='store_true', help='只应用 A 层')
    ap.add_argument('--print-candidates', action='store_true', help='打印 B/C 层完整候选')
    args = ap.parse_args()

    a1_rows, a2_rows = [], []
    b_cand, c_event, c_slug, c_long = [], [], [], []
    total = 0
    file_data = {}

    for path in YEAR_FILES:
        arr, header, tail = load_year(path)
        year = os.path.basename(path)[:4]
        file_data[path] = (arr, header, tail)
        total += len(arr)
        for r in arr:
            ch = unescape_fields(r)
            if ch:
                a1_rows.append({'id': r['id'], 'year': year, 'changes': ch})
            idt = r.get('identity', '')
            if should_clear_identity(idt):
                a2_rows.append({'id': r['id'], 'year': year, 'name': r.get('name'), 'identity': idt, 'age': r.get('age')})
            if is_nonhuman(idt):
                b_cand.append({'id': r['id'], 'year': year, 'name': r.get('name'), 'identity': idt,
                               'confirmed': r['id'] in CONFIRMED_NONHUMAN_IDS})
            nm = str(r.get('name', ''))
            if re.match(r'^\d', nm):
                c_event.append({'id': r['id'], 'year': year, 'name': nm, 'identity': idt}) if EVENT.search(nm) else c_slug.append(
                    {'id': r['id'], 'year': year, 'name': nm, 'identity': idt})
            elif SLUG.search(nm):
                c_slug.append({'id': r['id'], 'year': year, 'name': nm, 'identity': idt})
            if len(nm) > 45 and not NOBLE.search(nm):
                c_long.append({'id': r['id'], 'year': year, 'name': nm, 'identity': idt})

    print(f'总条数: {total}')
    print(f'[A1] HTML实体污染: {len(a1_rows)}')
    print(f'[A2] identity噪音值: {len(a2_rows)}')
    print(f'[B ] 非人类实体候选: {len(b_cand)} (已确认 {sum(1 for x in b_cand if x["confirmed"])} 条)')
    print(f'[C1] 事件名误作人名: {len(c_event)}')
    print(f'[C2] URL/slug 型姓名: {len(c_slug)} (含数字开头但非事件)')
    print(f'[C3] 超长姓名(非贵族头衔): {len(c_long)}')

    if args.print_candidates:
        print('\n=== B 层候选（须人工核对后填入 CONFIRMED_NONHUMAN_IDS）===')
        for x in b_cand:
            print(f"  {'✔' if x['confirmed'] else ' '} [{x['year']}] {x['id']:42s} | {x['name'][:26]:26s} | {x['identity'][:50]}")
        print('\n=== C1 事件名 ===')
        for x in c_event:
            print(f"  [{x['year']}] {x['name'][:52]:52s} | {str(x['identity'])[:36]}")
        print('\n=== C2 slug/数字开头(非事件) ===')
        for x in c_slug:
            print(f"  [{x['year']}] {x['name'][:52]:52s} | {str(x['identity'])[:36]}")
        print('\n=== C3 超长姓名(非贵族) ===')
        for x in c_long:
            print(f"  [{x['year']}] {x['name'][:70]}")

    report = {
        'generated_at': datetime.datetime.now().isoformat(timespec='seconds'),
        'source_files': [os.path.basename(p) for p in YEAR_FILES],
        'backup_dir': 'archive-data/history-backup-20261126-093835/',
        'total_rows': total,
        'layers': {
            'A1_html_entity': {'count': len(a1_rows), 'action': 'unescape', 'sample': a1_rows[:10]},
            'A2_identity_noise': {'count': len(a2_rows), 'action': 'clear_identity', 'sample': a2_rows[:10]},
            'B_nonhuman': {'count': len(b_cand), 'confirmed': sum(1 for x in b_cand if x['confirmed']),
                           'action': 'remove_if_confirmed', 'candidates': b_cand},
            'C1_event_as_name': {'count': len(c_event), 'action': 'review_only', 'rows': c_event},
            'C2_slug_name': {'count': len(c_slug), 'action': 'review_only', 'rows': c_slug},
            'C3_long_name': {'count': len(c_long), 'action': 'review_only_no_noble', 'rows': c_long},
        },
        'applied': False,
    }
    with open(REPORT, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f'\n报告已写入: {os.path.relpath(REPORT, BASE)}')

    if not (args.apply or args.apply_a_only):
        print('DRY-RUN：未修改任何年度数据文件。')
        return

    remove_ids = set(CONFIRMED_NONHUMAN_IDS) if args.apply else set()
    changed_files = 0
    n_a1 = n_a2 = n_b = 0
    for path, (arr, header, tail) in file_data.items():
        newarr = []
        dirty = False
        for r in arr:
            rid = r.get('id')
            if rid in remove_ids:
                dirty = True
                n_b += 1
                continue
            ch = unescape_fields(r)
            if ch:
                for k, (_, nv) in ch.items():
                    r[k] = nv
                n_a1 += 1
                dirty = True
            if should_clear_identity(r.get('identity', '')):
                r['identity'] = ''
                n_a2 += 1
                dirty = True
            newarr.append(r)
        if dirty:
            save_year(path, newarr, header, tail)
            changed_files += 1
            print(f'  写入 {os.path.basename(path)}: {len(arr)} -> {len(newarr)}')

    report['applied'] = True
    report['applied_summary'] = {'a1_unescaped': n_a1, 'a2_identity_cleared': n_a2,
                                 'b_nonhuman_removed': n_b, 'files_changed': changed_files,
                                 'applied_at': datetime.datetime.now().isoformat(timespec='seconds')}
    with open(REPORT, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f'\n应用完成: A1={n_a1}  A2={n_a2}  B={n_b}  文件={changed_files}')


if __name__ == '__main__':
    main()
