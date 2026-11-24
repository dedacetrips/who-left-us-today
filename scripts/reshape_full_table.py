#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""按线上精选表 data/deaths.js 的字段结构与命名，重新整理全量数据。

输入：archive-data/{2013..2026}.js（缩写字段 d/n/no/c/a/f/i/w/s/cd/ns）
输出：同名文件原地重建为完整字段名，与线上 DEATHS_DATA 对齐。
额外信息（中文名来源 ns、死因 status 与英文原文）另存 archive-data/extra.json。
"""
import json, glob, os, re, collections

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(BASE, 'archive-data')
TMP = os.path.join(BASE, 'archive-data.tmp')

# 与线上精选表完全一致的字段顺序
FIELDS = [
    'id','date','name','nameOrig','country','age','fields','identity',
    'summary','bio','facts','obit','portrait','source','region','verified',
    'causeOfDeath','wikipedia',
]

def norm(s):
    s = (s or '').strip().lower().replace('’', "'").replace('–', '-')
    return re.sub(r'\s+', ' ', s)

# 死因英译中（覆盖全表 208 种归一化标签）
CAUSE = {
'accidental alcohol poisoning':'意外酒精中毒','accidental ingestion':'误食',
'acute myeloid leukemia':'急性髓系白血病','acute respiratory failure':'急性呼吸衰竭',
'aircraft accident':'空难','airstrike':'空袭','airstrike injuries':'空袭伤','airstrikes':'空袭',
'als':'肌萎缩侧索硬化症',"alzheimer's":'阿尔茨海默病',"alzheimer's disease":'阿尔茨海默病',
'amyotrophic lateral sclerosis':'肌萎缩侧索硬化症','armed attack':'武装袭击',
'aspiration pneumonia':'吸入性肺炎','assassinated':'遇刺身亡','assassination':'遇刺',
'assisted suicide':'协助自杀','asthma attack':'哮喘发作',
'atherosclerotic cardiovascular disease':'动脉粥样硬化性心血管病','attack injuries':'袭击伤',
'avalanche':'雪崩','base jumping accident':'极限跳伞事故','beating':'殴打致死',
'bicycle accident':'自行车事故','bile duct cancer':'胆管癌','blood cancer':'血癌',
'boat collision':'船只相撞','bone cancer':'骨癌','bowel cancer':'肠癌','brain cancer':'脑癌',
'brain hemorrhage':'脑出血','brain injuries':'脑损伤','brain injury':'脑损伤',
'brain tumour':'脑肿瘤','breast cancer':'乳腺癌','brief illness':'短暂患病',
'bronchopneumonia':'支气管肺炎','bus accident':'公交车事故','cancer':'癌症',
'car accident':'车祸','car collision':'车祸','car crash':'车祸','cardiac arrest':'心脏骤停',
'cardiorespiratory arrest':'心肺骤停','cerebral aneurysm':'脑动脉瘤',
'cerebral haemorrhage':'脑出血','cerebral hemorrhage':'脑出血','cerebral infarction':'脑梗死',
'chest infection':'胸部感染','chronic obstructive pulmonary disease':'慢性阻塞性肺病',
'colic':'腹痛','colon cancer':'结肠癌','colorectal cancer':'结直肠癌','complications':'并发症',
'complications after surgery':'术后并发症','complications from a fall':'跌倒并发症',
'complications from copd':'慢阻肺并发症','complications from dementia':'痴呆并发症',
'complications from heart surgery':'心脏手术并发症','complications from surgery':'术后并发症',
'copd':'慢性阻塞性肺病','corticobasal syndrome':'皮质基底节综合征','covid-19':'新冠病毒感染',
'dementia':'痴呆',"dementia and parkinson's disease":'痴呆与帕金森病',
'dementia with lewy bodies':'路易体痴呆','dementia-related complications':'痴呆相关并发症',
'diabetes':'糖尿病','diabetes and heart disease':'糖尿病与心脏病',
'diabetes and lung cancer':'糖尿病与肺癌','diabetes complications':'糖尿病并发症',
'drone attack':'无人机袭击','drone strike':'无人机空袭','drowned':'溺亡','drowning':'溺水',
'drug addiction':'药物成瘾','earthquake':'地震','earthquakes':'地震','emphysema':'肺气肿',
'endometrial cancer':'子宫内膜癌','epileptic seizure':'癫痫发作','esophageal cancer':'食管癌',
'euthanasia':'安乐死','euthanized':'安乐死','ewing sarcoma':'尤文肉瘤','execution':'处决',
'fall':'跌倒','fall injuries':'跌伤','femur fracture':'股骨骨折','fire':'火灾',
'fractured shoulder':'肩部骨折','gastrointestinal bleeding':'消化道出血',
'gastrointestinal hemorrhage':'消化道出血','glioblastoma':'胶质母细胞瘤','gunfight':'枪战',
'gunshot':'枪击','head injury':'头部受伤','head injury from a fall':'跌倒致头部受伤',
'heart and kidney disease':'心肾疾病','heart and kidney issues':'心肾问题',
'heart aneurysm':'心脏动脉瘤','heart attack':'心脏病发作','heart defect':'心脏缺陷',
'heart disease':'心脏病','heart failure':'心力衰竭','heart failure and copd':'心衰与慢阻肺',
'heart failure and kidney disease':'心衰与肾病','heart problems':'心脏问题',
'heart surgery':'心脏手术','heart surgery complications':'心脏手术并发症',
'heart, lung and kidney disease':'心肺肾疾病','helicopter accident':'直升机事故',
'helicopter crash':'直升机失事','hepatitis b':'乙型肝炎','hepatocellular carcinoma':'肝细胞癌',
'house fire':'住宅火灾','illness':'疾病','influenza':'流感','intestinal blockage':'肠梗阻',
'intracerebral hemorrhage':'脑内出血','israeli airstrike':'以色列空袭',
'israeli strikes':'以色列空袭','israeli-united states strikes':'以美联合空袭',
'kidney cancer':'肾癌','kidney disease':'肾病','kidney failure':'肾衰竭','killed':'遇害',
'killed in action':'阵亡','killed in operation':'行动中身亡','knee surgery':'膝关节手术',
'landmine':'地雷','laryngeal cancer':'喉癌','lethal injection':'注射死刑','leukaemia':'白血病',
'leukemia':'白血病','lewy body dementia':'路易体痴呆','liver cancer':'肝癌',
'liver disease':'肝病','liver failure':'肝衰竭','long illness':'长期疾病','lung cancer':'肺癌',
'lung disease':'肺病','lung infection':'肺部感染','lymphoma':'淋巴瘤',
'medical complications':'医学并发症','meningitis':'脑膜炎','mesothelioma':'间皮瘤',
'motor neuron disease':'运动神经元病','motorcycle accident':'摩托车事故',
'multiple organ failure':'多器官衰竭','multiple organ failure and pneumonia':'多器官衰竭与肺炎',
'multiple sclerosis':'多发性硬化','murder':'谋杀','myeloma':'骨髓瘤','natural causes':'自然死亡',
'organ failure':'器官衰竭','pancreatic cancer':'胰腺癌','paramotor crash':'动力伞坠毁',
'paraneoplastic pemphigus':'副肿瘤性天疱疮',"parkinson's disease":'帕金森病',
"parkinson's disease dementia and a fall":'帕金森病痴呆与跌倒',
"parkinson's disease, dementia and fall":'帕金森病、痴呆与跌倒','peritonitis':'腹膜炎',
'plane crash':'空难','pleural effusion':'胸腔积液','pneumonia':'肺炎',
'pneumonia and prostate cancer':'肺炎与前列腺癌','police encounter':'警方执法事件',
'progressive supranuclear palsy':'进行性核上性麻痹','prolonged illness':'久病',
'prostate cancer':'前列腺癌','pulmonary fibrosis':'肺纤维化','racing collision':'赛车事故',
'racing incident':'赛车事故','rectal cancer':'直肠癌','renal cancer':'肾癌',
'respiratory failure':'呼吸衰竭','rhabdomyosarcoma':'横纹肌肉瘤',
'salivary gland cancer':'唾液腺癌','sarcoma':'肉瘤','school shooting':'校园枪击',
'sepsis':'败血症','septic shock':'感染性休克','severe illness':'重病','shooting':'枪击',
'short illness':'短期疾病','shot':'枪击','shot dead':'枪击身亡','skin cancer':'皮肤癌',
'smoke inhalation':'吸入烟雾','spinal injury':'脊髓损伤','stabbed':'刺伤','stabbing':'刺伤',
'stomach cancer':'胃癌','strike':'袭击','stroke':'中风','sturz':'跌倒','suicide':'自杀',
'suicide by gunshot':'开枪自杀','surgery complications':'手术并发症','tank fire':'坦克炮火',
'traffic accident':'交通事故','traffic collision':'交通事故','train crash':'火车事故',
'unknown':'死因未公开','urinary tract infection':'尿路感染','vascular dementia':'血管性痴呆',
'war':'战争',
}

def translate_cause(label):
    if not label: return None
    n = norm(label)
    if n in CAUSE: return CAUSE[n]
    # 兜底：X cancer / X disease 结构
    m = re.match(r'^(.+) cancer$', n)
    if m: return m.group(1).capitalize() + '癌'
    m = re.match(r'^(.+) disease$', n)
    if m: return m.group(1).capitalize() + '病'
    return label  # 保留原文，不臆测

def convert(x):
    cd = x.get('cd')
    cause, cause_status, cause_orig = None, None, None
    if cd and isinstance(cd, dict):
        cause_orig = cd.get('label')
        cause = translate_cause(cause_orig)
        cause_status = cd.get('status')
    rec = {
        'id': x['id'], 'date': x['d'], 'name': x['n'], 'nameOrig': x['no'],
        'country': x['c'], 'age': x['a'], 'fields': x['f'], 'identity': x['i'],
        'summary': '', 'bio': '', 'facts': [], 'obit': None, 'portrait': None,
        'source': x['s'] or '', 'region': '', 'verified': 'auto',
        'causeOfDeath': cause, 'wikipedia': x.get('w') or None,
    }
    extra = {}
    if x.get('ns'): extra['nameSource'] = x['ns']
    if cause_status: extra['causeStatus'] = cause_status
    if cause_orig: extra['causeOriginal'] = cause_orig
    return rec, (extra or None)

def main():
    os.makedirs(TMP, exist_ok=True)
    total = 0
    extras = {}
    year_counts = {}
    unmapped = collections.Counter()
    for path in sorted(glob.glob(os.path.join(SRC, '20*.js'))):
        year = os.path.basename(path)[:-3]
        s = open(path, encoding='utf-8').read()
        arr = json.loads(s[s.index('['):s.rindex(']')+1])
        out, cnt = [], 0
        for x in arr:
            rec, extra = convert(x)
            assert list(rec.keys()) == FIELDS, f'字段顺序不符: {rec.keys()}'
            out.append(rec)
            if extra: extras[rec['id']] = extra
            if rec['causeOfDeath'] and rec.get('id') and any(
                k in rec['causeOfDeath'] for k in ['Cancer','disease','attack','failure']
            ) and rec['causeOfDeath'][0].isascii():
                unmapped[rec['causeOfDeath']] += 1
        payload = f'// {year} 年逝世人物（全量，字段结构与线上精选表一致）\nwindow.ARCHIVE_{year} = ' + \
                  json.dumps(out, ensure_ascii=False, separators=(',',':')) + ';\n'
        with open(os.path.join(TMP, f'{year}.js'), 'w', encoding='utf-8') as f:
            f.write(payload)
        total += len(out); year_counts[year] = len(out)
        print(f'  {year}: {len(out)} 条')
    with open(os.path.join(TMP, 'extra.json'), 'w', encoding='utf-8') as f:
        json.dump(extras, f, ensure_ascii=False, separators=(',',':'))
    meta_path = os.path.join(SRC, 'meta.json')
    meta = json.load(open(meta_path, encoding='utf-8'))
    meta['schema'] = {
        'variable': 'window.ARCHIVE_YYYY',
        'fields': FIELDS,
        'note': '字段结构与 data/deaths.js 的 window.DEATHS_DATA 完全一致；'
                '全表不含深度内容，summary/bio 为空字符串，facts 为空数组，'
                'obit/portrait 为 null，verified=auto。',
        'extra': 'archive-data/extra.json 按 id 保存中文名来源与死因原始信息',
    }
    meta['total'] = total
    with open(os.path.join(TMP, 'meta.json'), 'w', encoding='utf-8') as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    # 校验通过后替换
    assert total == meta.get('total', total) == 116817, f'总数异常: {total}'
    for name in os.listdir(TMP):
        os.replace(os.path.join(TMP, name), os.path.join(SRC, name))
    os.rmdir(TMP)
    print(f'\n完成：{total} 条，字段 {len(FIELDS)} 个，死因未映射 {sum(unmapped.values())} 条')
    if unmapped: print('未映射样例:', unmapped.most_common(10))
    print('年份分布:', year_counts)

if __name__ == '__main__':
    main()
