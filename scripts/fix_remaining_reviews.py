# -*- coding: utf-8 -*-
"""
处理标题化污染修复后剩余的 4 条待核记录（人工逐条核对结论）

  - derek-foster-baron-...        : 保留（合法贵族全名，name 正确）
  - mayor-of-frosinone            : 移除（职位条目噪音，identity 无真实死者姓名）
  - killing-of-monique-and-spencer-tepe   : name → Monique Tepe（identity 明确，牙医 37 岁）
  - killing-of-monique-and-spencer-tepe-2 : name → Monique Tepe（identity 明确，幼教 39 岁，
                                            与上条年龄/职业冲突，疑似案件另一受害者，标注待核）

用法：
  python3.11 scripts/fix_remaining_reviews.py            # dry-run
  python3.11 scripts/fix_remaining_reviews.py --apply    # 应用
"""
import argparse
import datetime
import glob
import json
import os

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ARC = os.path.join(BASE, 'archive-data')
YEAR_FILES = sorted(f for f in glob.glob(os.path.join(ARC, '20[0-2][0-9].js'))
                    if not os.path.basename(f).startswith('2026'))
REPORT = os.path.join(ARC, 'history-review4-fix-20261126.json')

DECISIONS = {
    '20190106-derek-foster-baron-foster-of-bishop-auckland': {
        'action': 'keep',
        'reason': '合法贵族全名（Derek Foster, Baron Foster of Bishop Auckland），name 正确，identity 仅简短但有效',
    },
    '20220531-mayor-of-frosinone': {
        'action': 'remove',
        'reason': '职位条目被当人名；identity 全文未给出死者真实姓名（仅提到下一任市长），无法修正为有效人物记录',
    },
    '20251230-killing-of-monique-and-spencer-tepe': {
        'action': 'rename',
        'new_name': 'Monique Tepe',
        'reason': '案件标题被当 name；identity 明确死者 Monique Tepe（美国牙医，37 岁）',
    },
    '20251230-killing-of-monique-and-spencer-tepe-2': {
        'action': 'rename',
        'new_name': 'Monique Tepe',
        'reason': '案件标题被当 name；identity 明确 Monique Tepe（幼教，39 岁）。与上条年龄/职业冲突，'
                  '疑似同一枪击案另一受害者（丈夫 Spencer Tepe）被混抓，标注待核',
        'flag': '身份冲突：与上条同为 Monique Tepe 但年龄 39 vs 37、职业幼教 vs 牙医，建议核对是否应改为 Spencer Tepe 或去重',
    },
}


def parse(path):
    s = open(path, encoding='utf-8').read(); i = s.find('[')
    arr, end = json.JSONDecoder().raw_decode(s[i:])
    return arr, s[:i], s[i + end:]


def save(path, arr, header, tail):
    with open(path, 'w', encoding='utf-8') as f:
        f.write(header + json.dumps(arr, ensure_ascii=False, separators=(',', ':')) + tail)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--apply', action='store_true')
    args = ap.parse_args()

    found = {}
    for path in YEAR_FILES:
        arr, _, _ = parse(path)
        for r in arr:
            if r['id'] in DECISIONS:
                found[r['id']] = {'year': os.path.basename(path)[:4], 'name': r.get('name'),
                                  'nameOrig': r.get('nameOrig'), 'age': r.get('age'),
                                  'identity': str(r.get('identity', ''))[:100]}

    print('=== 4 条待核处理决定 ===')
    for rid, dec in DECISIONS.items():
        f = found.get(rid)
        print(f"\n[{f['year'] if f else '??'}] {rid}")
        print(f"  当前 name: {f['name'] if f else '未找到'}")
        print(f"  动作: {dec['action']}" + (f" -> {dec['new_name']}" if dec['action'] == 'rename' else ''))
        print(f"  理由: {dec['reason']}")
        if dec.get('flag'):
            print(f"  ⚠ {dec['flag']}")
    missing = set(DECISIONS) - set(found)
    if missing:
        print(f'\n警告：未找到 {len(missing)} 条 id: {missing}')

    report = {
        'generated_at': datetime.datetime.now().isoformat(timespec='seconds'),
        'description': '标题化污染修复后剩余 4 条待核记录的人工核对结论',
        'decisions': DECISIONS,
        'found': found,
        'applied': False,
    }
    with open(REPORT, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f'\n报告: {os.path.relpath(REPORT, BASE)}')

    if not args.apply:
        print('DRY-RUN：未修改数据。')
        return

    remove_ids = {rid for rid, d in DECISIONS.items() if d['action'] == 'remove'}
    rename_map = {rid: d['new_name'] for rid, d in DECISIONS.items() if d['action'] == 'rename'}
    changed_files = 0
    for path in YEAR_FILES:
        arr, header, tail = parse(path)
        dirty = False
        newarr = []
        for r in arr:
            rid = r['id']
            if rid in remove_ids:
                dirty = True
                continue
            if rid in rename_map:
                r['name'] = rename_map[rid]
                r['nameOrig'] = rename_map[rid]
                dirty = True
            newarr.append(r)
        if dirty:
            save(path, newarr, header, tail)
            changed_files += 1
            print(f'  写入 {os.path.basename(path)}: {len(arr)} -> {len(newarr)}')
    report['applied'] = True
    report['applied_at'] = datetime.datetime.now().isoformat(timespec='seconds')
    with open(REPORT, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f'\n应用完成: 移除 {len(remove_ids)} 条, 改名 {len(rename_map)} 条, 涉及 {changed_files} 个文件')


if __name__ == '__main__':
    main()
