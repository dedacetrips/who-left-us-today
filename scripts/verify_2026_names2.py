#!/usr/bin/env python3
"""核验 2026 主表姓名字段污染第二轮：
name = 英文名 + 国籍词 + 身份/死因串，identity 首段是纯人名前缀。
保守策略：只在 identity 首段是 name 的严格前缀、且其后紧跟国籍词时修复。"""
import json, re, sys, html
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEATHS = ROOT / 'data' / 'deaths.js'

def load(path):
    s = path.read_text(encoding='utf-8')
    return json.JSONDecoder().raw_decode(s[s.index('{'):])[0]

NATION = (r'American|British|English|Scottish|Welsh|Irish|Indian|Japanese|Chinese|French|German|'
 r'Canadian|Australian|Russian|Italian|Spanish|Korean|Filipino|Indonesian|Vietnamese|Thai|'
 r'Singaporean|Malaysian|Pakistani|Bangladeshi|Nepalese|Afghan|Iranian|Iraqi|Israeli|'
 r'Palestinian|Lebanese|Syrian|Turkish|Greek|Polish|Swedish|Norwegian|Danish|Finnish|Dutch|'
 r'Belgian|Swiss|Austrian|Portuguese|Croatian|Serbian|Ukrainian|Romanian|Hungarian|Czech|'
 r'Slovak|Bulgarian|Georgian|Armenian|Kazakh|Uzbek|Mongolian|Burmese|Cambodian|Algerian|'
 r'Moroccan|Egyptian|Tunisian|Libyan|Sudanese|Ethiopian|Somali|Kenyan|Ugandan|Tanzanian|'
 r'Zimbabwean|Ghanaian|Nigerian|South African|Chilean|Argentinian|Colombian|Peruvian|'
 r'Venezuelan|Brazilian|Mexican|Cuban|Fijian|Mozambican|Angolan|Zambian|Namibian|Rwandan|'
 r'Jamaican|Haitian|Lithuanian|Latvian|Estonian|Slovenian|Bosnian|Moldovan|Belarusian|'
 r'Sri Lankan|Papua New Guinean|I-Kiribati|Samoan|Tongan|Moldovan|Kyrgyz|Tajik|Uzbek')
IDW = (r'politician|actor|actress|singer|writer|artist|author|journalist|professor|doctor|'
 r'general|minister|senator|mayor|governor|ambassador|judge|president|ceo|founder|director|'
 r'coach|player|athlete|lawyer|engineer|scientist|architect|historian|activist|novelist|'
 r'poet|guitarist|drummer|bishop|economist|photographer|designer|composer|producer|'
 r'businessman|model|officer|researcher|teacher|rector|principal|screenwriter|filmmaker|'
 r'broadcaster|columnist|critic|curator|diplomat|administrator|executive|consultant|'
 r'scholar|investor|banker|comedian|blogger|youtuber|activist|civil servant|footballer|'
 r'cricketer|judoka|wrestler|boxer|swimmer|golfer|chess|rugby|hockey|basketball|'
 r'self-employed|retired|former|known|best|who|served')

def extract(row, I):
    name = str(row[I['name']] or '').strip()
    # 仅处理英文/拉丁字母开头的 name
    if not re.match(r'^[A-Za-zÀ-ÿ]', name):
        return None
    # 必须含 "国籍词 ... 身份词" 结构
    if not re.search(rf'\b({NATION})\b.*?\b({IDW})\b', name, re.I):
        return None
    ident = html.unescape(str(row[I['identity']] or ''))
    first = re.sub(r'^Killing of\s+', '', ident.split(',')[0].strip(), flags=re.I)
    if not first or len(first) > 60 or len(first.split()) < 2:
        return None
    # identity 首段必须是 name 的严格前缀（大小写不敏感）
    if not name.lower().startswith(first.lower()):
        return None
    rest = name[len(first):].strip()
    # 剩余部分必须以国籍词开头（防止误切名字内部）
    if not re.match(rf'^({NATION})\b', rest, re.I):
        return None
    return first

def main():
    d = load(DEATHS)
    cols, rows = d['cols'], d['rows']
    I = {k: i for i, k in enumerate(cols)}
    changes = []
    for r in rows:
        clean = extract(r, I)
        if clean and clean != str(r[I['name']] or ''):
            changes.append((r, clean))

    print(f'待修复: {len(changes)} 条\n')
    for r, clean in changes[:40]:
        print(f"  {str(r[I['name']])[:72]}")
        print(f"    → {clean}")
    if len(changes) > 40:
        print(f'  ... 另 {len(changes)-40} 条')

    if '--apply' not in sys.argv:
        print('\n(预览模式，未写入。加 --apply 执行)')
        return
    for r, clean in changes:
        r[I['name']] = clean
        r[I['nameOrig']] = clean
    jd = lambda o: json.dumps(o, ensure_ascii=False, separators=(',', ':'))
    DEATHS.write_text(
        '// 人物数据：每天离世的世界名人讣告档案（列式压缩）\n'
        + f'window.DEATHS_DATA = {jd({"cols": cols, "rows": rows})};\n',
        encoding='utf-8')
    print(f'\n已写入 {len(changes)} 条修复')

if __name__ == '__main__':
    main()
