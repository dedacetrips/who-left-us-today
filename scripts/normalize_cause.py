#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""死因规范化：统一同义术语 + 新增死因大类 causeCategory。

处理 data/deaths.js（精选表）与 archive-data/20*.js（全表），
两者字段结构保持一致：在 causeOfDeath 后插入 causeCategory。
规范化前的中文表述存入 extra.json 的 causeRaw 字段。
"""
import json, glob, os, collections

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 完全同义 / 俗称 → 规范术语
SYNONYM = {
    '渐冻症': '肌萎缩侧索硬化症',
    '脑溢血': '脑出血',
    '脑内出血': '脑出血',
    '心梗': '心脏病发作',
    '心脏衰竭': '心力衰竭',
    '血癌': '白血病',
    '车祸': '交通事故',
    '枪击身亡': '枪击',
    '遇刺身亡': '遇刺',
    '溺亡': '溺水',
    '跌伤': '跌倒',
    '开枪自杀': '自杀',
    '空袭伤': '空袭',
    '以色列空袭': '空袭',
    '以美联合空袭': '空袭',
    '无人机空袭': '空袭',
    '无人机袭击': '空袭',
    '校园枪击': '枪击',
    '行动中身亡': '阵亡',
    '心脏问题': '心脏病',
    '心肾问题': '心肾疾病',
    '脑肿瘤': '脑癌',
    '死因未公开': '未公开',
    'unknown': '未公开',
}

# 笼统死因表述 → 统一为「疾病（未详）」
VAQUE = {'疾病','长期疾病','久病','短期疾病','重病','严重疾病','illness'}

# 主要疾病关键词：复合死因（如「帕金森病、痴呆与跌倒」）含这些词时优先按疾病归类
DISEASE_PRIMARY = ['癌','肿瘤','白血病','淋巴瘤','骨髓瘤','肉瘤','心脏病','心衰','心力',
    '心脏','中风','脑出血','脑梗死','痴呆','阿尔茨海默','帕金森','路易体','多发性硬化',
    '运动神经元','肌萎缩','渐冻','肺炎','肺纤维化','肺气肿','慢阻肺','慢性阻塞','肺病',
    '呼吸衰竭','肾衰竭','肾病','肝衰竭','肝病','糖尿病','脑膜炎','败血症','感染性休克',
    '流感','乙肝','乙型肝炎','新冠','器官衰竭','多器官','并发症','自然死亡']

# 大类分类（按顺序匹配，命中即止；疾病优先以避免复合死因误分）
CATEGORY_RULES = [
    ('自杀', ['自杀','安乐死']),
    ('未公开', ['未公开','未知']),
    ('疾病', DISEASE_PRIMARY + ['腹部','肠梗阻','腹膜炎','胸腔积液','动脉粥样',
              '癫痫','哮喘','腹痛','痛风','血液','骨髓','疫病','疾病','患病','手术','膝关节']),
    ('暴力冲突', ['枪击','枪战','谋杀','遇害','遇刺','刺伤','殴打','空袭','战争',
                  '阵亡','行动中','无人机','坦克','地雷','武装','袭击','处决',
                  '注射死刑','警方','枪杀']),
    ('意外事故', ['事故','车祸','交通','空难','失事','坠毁','跌倒','跌','溺水',
                  '溺','火灾','地震','雪崩','中毒','误食','药物成瘾','头部受伤',
                  '脑损伤','脊髓损伤','骨折','撞','吸入烟雾','燃烧','爆炸']),
]

def normalize(cause):
    if not cause: return None, None
    c = SYNONYM.get(cause, cause)
    if c in VAQUE: return '疾病（未详）', '疾病'
    for cat, kws in CATEGORY_RULES:
        if any(k in c for k in kws):
            return c, cat
    return c, '疾病'  # 兜底归入疾病

def process_file(path, varname=None):
    s = open(path, encoding='utf-8').read()
    if varname:
        arr = json.loads(s[s.index('['):s.rindex(']')+1])
    else:
        arr = json.loads(s[s.index('['):s.rindex(']')+1])
    stats = collections.Counter()
    raws = {}
    for x in arr:
        old = x.get('causeOfDeath')
        if old:
            new, cat = normalize(old)
            if new != old: raws[x['id']] = old
            x['causeOfDeath'] = new
            x['causeCategory'] = cat
            stats[cat] += 1
        else:
            x['causeCategory'] = None
    # 保证字段顺序：causeCategory 紧跟 causeOfDeath
    ordered = []
    for x in arr:
        d = {}
        for k, v in x.items():
            d[k] = v
            if k == 'causeOfDeath':
                d['causeCategory'] = x['causeCategory']
        ordered.append(d)
    if varname:
        head = s[:s.index('[')]
        out = head + json.dumps(ordered, ensure_ascii=False, separators=(',',':')) + ';\n'
    else:
        out = s[:s.index('[')] + json.dumps(ordered, ensure_ascii=False, separators=(',',':')) + ';\n'
    open(path, 'w', encoding='utf-8').write(out)
    return stats, raws, len(arr)

def main():
    all_stats = collections.Counter(); all_raws = {}
    # 精选表
    st, rw, n = process_file(os.path.join(BASE,'data','deaths.js'))
    print('精选表 %d 条:' % n, dict(st), '| 术语变更 %d' % len(rw))
    all_stats += st; all_raws.update(rw)
    # 全表
    for f in sorted(glob.glob(os.path.join(BASE,'archive-data','20*.js'))):
        st, rw, n = process_file(f)
        all_stats += st; all_raws.update(rw)
    print('\n全表 + 精选合计分类:', dict(all_stats))
    print('术语变更总数:', len(all_raws))
    for k,v in list(all_raws.items())[:20]: print('  ', v, '->', k)
    # extra.json 补 causeRaw
    ep = os.path.join(BASE,'archive-data','extra.json')
    extra = json.load(open(ep,encoding='utf-8'))
    for id_, raw in all_raws.items():
        extra.setdefault(id_, {})['causeRaw'] = raw
    json.dump(extra, open(ep,'w',encoding='utf-8'), ensure_ascii=False, separators=(',',':'))

if __name__ == '__main__':
    main()
