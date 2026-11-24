#!/usr/bin/env python3
"""
融合脚本：给线上精选表 deaths.js 增加 causeOfDeath（死因）和 wikipedia（维基链接）字段

死因来源优先级：
  1. 全表 cd 字段（英文标签 -> 中文）
  2. 线上 bio / 讣告原文 / facts 中严格句式提取
  3. 无则 null

维基链接来源优先级：
  1. 全表 w 字段
  2. 线上 source 字段中的 URL（维基百科域名）

输出：直接更新 data/deaths.js（先备份到 /tmp/deaths-backup.js）
"""
import json, re, subprocess, os, shutil, warnings
warnings.filterwarnings('ignore')

ROOT = '/workspace/memento-web'
DEATHS = os.path.join(ROOT, 'data/deaths.js')
OBITS = os.path.join(ROOT, 'data/obits.js')

# 英文死因 -> 中文
CAUSE_ZH = {
    'cancer':'癌症','brain cancer':'脑癌','lung cancer':'肺癌','prostate cancer':'前列腺癌',
    'breast cancer':'乳腺癌','liver cancer':'肝癌','stomach cancer':'胃癌','pancreatic cancer':'胰腺癌',
    'meningitis':'脑膜炎','heart attack':'心脏病发作','heart failure':'心力衰竭',
    'cardiac arrest':'心脏骤停','stroke':'中风','traffic collision':'交通事故',
    'shot':'枪击','pneumonia':'肺炎','complications from surgery':'手术并发症',
    'alzheimer’s disease':'阿尔茨海默病',"alzheimer's disease":'阿尔茨海默病',
}

D = (r'(?:肺癌|肝癌|胃癌|肠癌|乳腺癌|前列腺癌|胰腺癌|脑癌|骨癌|血癌|白血病|淋巴瘤|'
     r'心脏病|心力衰竭|心脏衰竭|心脏骤停|心梗|心肌梗死|中风|脑溢血|脑卒中|脑梗死|'
     r'肺炎|感染|败血症|胰腺炎|肺纤维化|阿尔茨海默病?|路易体痴呆|痴呆|帕金森病?|'
     r'渐冻症|肌萎缩侧索硬化|抑郁症|多器官衰竭|呼吸衰竭|肾衰竭|肝衰竭|癌症|恶性肿瘤|'
     r'车祸|枪击|自杀|中毒|手术并发症)')
PATTERNS = [
    re.compile(rf'死因(?:为|是|证明书列)?\s*[:：]?\s*({D})'),
    re.compile(rf'因\s*({D})[^。；\n]{{0,15}}?(?:去世|逝世|离世|病逝|不治|死亡|去世)'),
    re.compile(rf'({D})[^。；\n]{{0,10}}?(?:去世|逝世|离世|病逝|不治|死亡)'),
]

def extract_cause(texts):
    for t in texts:
        if not t: continue
        for pat in PATTERNS:
            for m in pat.finditer(t):
                c = m.group(1)
                pre = t[max(0, m.start()-25):m.start()]
                if re.search(r'丈夫|妻子|儿子|女儿|幼子|父亲|母亲|遗孀|\d{4}\s*年因', pre):
                    continue
                return c
    return None

def norm(s):
    return (s or '').lower().replace(r'[\s\-\'\u2019\.\u00b7\u30fb・\(\)（）]','')
def norm2(s):
    return re.sub(r'[\s\-\'\u2019\.\u00b7\u30fb・\(\)（）]','',(s or '').lower()).strip()

def main():
    # 读取线上数据
    js = "global.window={};require('%s');require('%s');console.log(JSON.stringify({d:window.DEATHS_DATA,o:window.OBITS}))" % (DEATHS, OBITS)
    dd = json.loads(subprocess.check_output(['node','-e',js], text=True))
    A, O = dd['d'], dd['o']

    # 读取全表
    global_win = {}
    for y in range(2013, 2027):
        txt = open(os.path.join(ROOT, 'archive-data', f'{y}.js'), encoding='utf-8').read()
        arr = json.loads(txt.split('=',1)[1].strip().rstrip(';'))
        global_win[y] = arr

    # 建立全表索引：id / 中文名 / 原名 / 日期+原名
    by = {'id':{}, 'name':{}, 'date_name':{}}
    for y, arr in global_win.items():
        for x in arr:
            by['id'][x['id']] = x
            for k in [norm2(x.get('n')), norm2(x.get('no'))]:
                if k and k not in by['name']: by['name'][k] = x
            key = x['d'] + '|' + norm2(x.get('no') or x.get('n'))
            if key not in by['date_name']: by['date_name'][key] = x

    def find_match(x):
        if x['id'] in by['id']: return by['id'][x['id']]
        key = x['date'] + '|' + norm2(x.get('nameOrig') or x['name'])
        if key in by['date_name']: return by['date_name'][key]
        for k in [norm2(x['name']), norm2(x.get('nameOrig'))]:
            if k in by['name']: return by['name'][k]
        return None

    shutil.copy(DEATHS, '/tmp/deaths-backup.js')

    cause_stat = {'from_full':0, 'from_text':0, 'empty':0}
    wiki_stat = {'from_full':0, 'from_source':0, 'empty':0}
    matched = 0

    for x in A:
        m = find_match(x)
        if m: matched += 1

        # ── 死因 ──
        cause = None
        if m and m.get('cd'):
            label = str(m['cd'].get('label') or '').strip()
            cause = CAUSE_ZH.get(label.lower(), label) or None
            if cause: cause_stat['from_full'] += 1
        if not cause:
            o = O.get(x['id'], {})
            texts = [x.get('bio'), o.get('text')] + list(x.get('facts') or [])
            cause = extract_cause(texts)
            if cause: cause_stat['from_text'] += 1
        if not cause: cause_stat['empty'] += 1
        x['causeOfDeath'] = cause

        # ── 维基链接 ──
        wiki = None
        if m and m.get('w'): wiki = m['w']
        if not wiki:
            src = str(x.get('source') or '')
            mt = re.search(r'https?://[^\s，,；;）)]*wikipedia\.org[^\s，,；;）)]*', src, re.I)
            if mt:
                wiki = mt.group(0)
                wiki_stat['from_source'] += 1
            else:
                wiki_stat['empty'] += 1
        else:
            wiki_stat['from_full'] += 1
        x['wikipedia'] = wiki

    # 写回 deaths.js
    with open(DEATHS, 'w', encoding='utf-8') as fp:
        fp.write('// 人物数据：每天离世的世界名人讣告档案\n')
        fp.write('window.DEATHS_DATA = ')
        json.dump(A, fp, ensure_ascii=False, separators=(',',':'))
        fp.write(';\n')

    print('线上记录:', len(A), '| 全表匹配到:', matched)
    print('死因:', cause_stat)
    print('维基:', wiki_stat)
    print('备份: /tmp/deaths-backup.js')
    # 样例
    for x in A[:3]: print(' ', x['name'], '|', x['causeOfDeath'], '|', x['wikipedia'])

if __name__ == '__main__':
    main()
