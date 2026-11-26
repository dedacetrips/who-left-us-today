#!/usr/bin/env python3
"""数据源噪音处理（2026-11-26）
保守策略：只移除主语明确为非人类实体（赛马、动物、树、乐队本身）或
姓名被乐队名污染且无法还原真实姓名的条目。人类（骑师、驯马师、乐队成员）一律保留。
生成审核清单 JSON，--apply 时才写主表。
"""
import re, json, sys, shutil
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parent.parent
DEATHS = ROOT / 'data' / 'deaths.js'
FT = ROOT / 'archive-data' / 'deadpeople-2026-fulltext.json'
OUT = ROOT / 'archive-data' / 'noise-removal-20261126.json'


def load_col(f):
    s = f.read_text(encoding='utf-8')
    d = json.loads(re.search(r'window\.\w+\s*=\s*(\{.*)', s, re.S).group(1).rstrip().rstrip(';'))
    return d['cols'], d['rows']


def plain(h):
    t = re.sub(r'<script.*?</script>|<style.*?</style>', ' ', h or '', flags=re.S | re.I)
    t = re.sub(r'<[^>]+>', ' ', t)
    return re.sub(r'\s+', ' ', __import__('html').unescape(t)).strip()


# 人类职业词——出现则说明主语是人，保留
HUMAN = re.compile(
    r'jockey|trainer|owner|breeder|rider|drummer|guitarist|bassist|vocalist|singer'
    r'|keyboardist|musician|pianist|manager|songwriter|rapper|conductor|composer'
    r'|violinist|saxophonist|producer|film scorer', re.I)
# 非人类实体——主语即动物/赛马/树/乐队团体本身
ANIMAL = re.compile(r'\bracehorse\b|\bthoroughbred\b|\bstandardbred\b|hippopotamus|\bthe horse\b', re.I)
BAND = re.compile(
    r'\b(?:rock|pop|rap|reggae|funk|metalcore|punk|grindcore|indie|garage|ethno-pop|post-hardcore|symphonic)\s*(?:music\s*)?band\b'
    r'|\bmusic band\b|\bmusical band\b|\breggae group\b|\bgroup founded\b|\bband from\b|\bband based\b'
    r'|\bband formed\b|\bthe band\b', re.I)
TREE = re.compile(r'\boak\b|\btree\b', re.I)

# 明确的非人类实体 id（人工复核：主语本身是马/河马/树/乐队团体）
EXPLICIT_NONHUMAN = {
    # 河马
    '20261119-fiona-hippopotamus': '动物：辛辛那提动物园河马 Fiona',
    # 树
    '20260617-major-oak': '植物：舍伍德森林橡树 Major Oak',
    # 赛马（主语是马本身，非骑师/驯马师）
    '20261112-zee-zee-top': '赛马', '20261109-ballabriggs': '赛马',
    '20261020-early-voting': '赛马', '20261016-medaglia-doro-horse': '赛马',
    '20261011-toms-detat': '赛马', '20261002-roy-h': '赛马',
    '20260923-first-dude-horse': '赛马', '20260922-hurricane-fly': '赛马',
    '20260907-admire-moon': '赛马', '20260901-galopin-des-champs': '赛马',
    '20260823-nakayama-festa': '赛马', '20260818-varenne': '赛马',
    '20260817-orientate': '赛马', '20260808-big-bucks': '赛马',
    '20260808-girvin': '赛马', '20260807-immortal-verse': '赛马',
    '20260802-tsurumaru-tsuyoshi': '赛马', '20260730-magic-weisner': '赛马',
    '20260728-ghanaati': '赛马', '20260705-bayern-horse': '赛马',
    '20260703-motivator-horse': '赛马', '20260619-savabeel': '赛马',
    '20260508-auroras-encore': '赛马', '20260418-noble-yeats': '赛马',
    '20260415-frosted': '赛马', '20260324-western-dreamer': '赛马',
    '20260313-envoi-allen': '赛马', '20260311-serenas-song': '赛马',
    '20260303-mujahid-horse': '赛马', '20260228-makybe-diva': '赛马',
    '20260219-reliable-man': '赛马', '20260217-blue-prize': '赛马',
    '20260206-afleet-alex': '赛马', '20260122-eldaafer': '赛马',
    '20260120-daiwa-major': '赛马', '20260110-distorted-humor': '赛马',
    # 乐队团体本身（主语是乐队，不是成员）
    '20260520-denyse-lepage': '乐队团体本身（Lime）',
    '20260518-peter-archer': '乐队团体本身（Crow）',
    '20260331-krec-rap-band': '乐队团体本身（KREC）',
    '20260327-boysetsfire': '乐队团体本身（BoySetsFire）',
    '20260317-eurogliders': '乐队团体本身（Eurogliders）',
    '20260312-holograf': '乐队团体本身（Holograf）',
    '20260307-goblin-band': '乐队团体本身（Goblin）',
    '20260307-god-bless': '乐队团体本身（God Bless）',
    '20260302-max-webster': '乐队团体本身（Max Webster）',
    '20260302-morlocks-swedish-band': '乐队团体本身（Morlocks）',
    '20260225-ariel-russian-band': '乐队团体本身（Ariel）',
    '20260221-buranovskiye-babushki': '乐队团体本身（Buranovskiye Babushki）',
    '20260220-shortparis': '乐队团体本身（Shortparis）',
    '20260214-we-all-together': '乐队团体本身（We All Together）',
    '20260202-slave-band': '乐队团体本身（Slave）',
    '20260308-herbs-band': '乐队团体本身（Herbs）',
}

# 姓名被乐队名污染、正文无法还原真实姓名的条目（人名缺失，不可靠）
POLLUTED_NAME = {
    '20260322-the-pillows': '姓名为乐队名 The Pillows，正文未给出成员姓名',
    '20260312-blood-duster': '姓名为乐队名 Blood Duster，正文未给出成员姓名',
    '20260227-olympic-band': '姓名为乐队名 Olympic，正文未给出成员姓名',
    '20260215-we-the-people-band': '姓名为乐队名 We the People，正文未给出成员姓名',
    '20260214-manchester-orchestra': '姓名为乐队名 Manchester Orchestra，正文未给出成员姓名',
    '20260214-merauder': '姓名为乐队名 Merauder，正文未给出成员姓名',
    '20260312-chaos-uk': '姓名为乐队名 Chaos UK，正文未给出成员姓名',
    '20260320-los-piojos': '姓名为乐队名 Los Piojos，正文未给出成员姓名',
}

# 姓名/身份字段被污染成整句（噪音，需还原或移除）
# 这类在 previous round 已清洗 1344 条，这里只处理仍残留的整句式姓名
def polluted_name(name):
    return bool(re.search(r'\b(racehorse|thoroughbred|standardbred|public figure|euthanized)\b', name, re.I))


def main():
    apply = '--apply' in sys.argv
    cols, rows = load_col(DEATHS)
    idx = {c: i for i, c in enumerate(cols)}
    ft = json.loads(FT.read_text(encoding='utf-8'))
    by_id = {r[idx['id']]: r for r in rows}

    remove = {}
    for rid, reason in EXPLICIT_NONHUMAN.items():
        if rid in by_id:
            remove[rid] = {'reason': reason, 'name': by_id[rid][idx['name']], 'date': by_id[rid][idx['date']]}
    for rid, reason in POLLUTED_NAME.items():
        if rid in by_id and rid not in remove:
            remove[rid] = {'reason': reason, 'name': by_id[rid][idx['name']], 'date': by_id[rid][idx['date']]}

    # 附加：identity 中姓名残留整句式污染（如 "Frosted American Thoroughbred racehorse, euthanized"）
    for r in rows:
        rid = r[idx['id']]
        if rid in remove:
            continue
        nm = r[idx['name']] or ''
        if polluted_name(nm):
            # 只有在正文确认是非人类时才移除
            slug = re.sub(r'^\d{8}-', '', rid)
            v = ft.get(slug)
            text = plain(v['h'])[:260] if v else (r[idx['identity']] or '')
            if ANIMAL.search(text) and not HUMAN.search(text):
                remove[rid] = {'reason': f'姓名污染且正文确认为非人类：{nm[:60]}', 'name': nm, 'date': r[idx['date']]}

    report = {
        'generated': datetime.now().isoformat(),
        'total_before': len(rows),
        'remove_count': len(remove),
        'remove': remove,
        'categories': {},
    }
    for rid, info in remove.items():
        cat = info['reason'].split('：')[0]
        # 归一化分类
        cat2 = '赛马' if '赛马' in info['reason'] else ('动物' if '动物' in info['reason'] else ('植物' if '植物' in info['reason'] else ('乐队/团体' if '乐队' in info['reason'] else '姓名污染')))
        report['categories'][cat2] = report['categories'].get(cat2, 0) + 1

    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'拟移除 {len(remove)} 条：{report["categories"]}')
    print('清单:', OUT)
    for rid, info in sorted(remove.items()):
        print(' ', rid, '|', info['name'][:28], '|', info['reason'][:70])

    if apply:
        ts = datetime.now().strftime('%Y%m%d-%H%M%S')
        bak = DEATHS.parent / f'deaths.before-noise-{ts}.js'
        shutil.copy2(DEATHS, bak)
        newrows = [r for r in rows if r[idx['id']] not in remove]
        content = '// 人物数据：每天离世的世界名人讣告档案（列式压缩）\nwindow.DEATHS_DATA = ' + \
            json.dumps({'cols': cols, 'rows': newrows}, ensure_ascii=False) + ';\n'
        DEATHS.write_text(content, encoding='utf-8')
        # 同步清理 source-links
        SL = ROOT / 'data' / 'source-links.js'
        if SL.exists():
            s = SL.read_text(encoding='utf-8')
            sl = json.loads(re.search(r'window\.SOURCE_LINKS\s*=\s*(\{.*)', s, re.S).group(1).rstrip().rstrip(';'))
            before = len(sl)
            sl2 = {k: v for k, v in sl.items() if k not in remove}
            SL.write_text('window.SOURCE_LINKS = ' + json.dumps(sl2, ensure_ascii=False) + ';\n', encoding='utf-8')
            print(f'source-links: {before} -> {len(sl2)}')
        print(f'主表: {len(rows)} -> {len(newrows)}；备份 {bak.name}')


if __name__ == '__main__':
    main()
