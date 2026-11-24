#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成死因规范字典表：中文名 / 英文名 / 归纳描述 / 大类 / 出现次数。

数据源：全表 + 精选表的规范化死因，extra.json 的 causeOriginal，CAUSE 翻译表。
输出：archive-data/死因规范字典.json 与 .csv / .md
"""
import json, glob, os, collections, csv, importlib.util

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
spec = importlib.util.spec_from_file_location('r', os.path.join(BASE,'scripts','reshape_full_table.py'))
r = importlib.util.module_from_spec(spec); spec.loader.exec_module(r)

# 人工指定的规范英文名（修正自动挑选的歧义项）
EN_OVERRIDE = {
    '枪击':'Gunshot', '遇刺':'Assassination', '溺水':'Drowning',
    '袭击':'Attack', '心脏病发作':'Heart Attack', '中风':'Stroke',
    '腹痛':'Colic', '跌倒':'Fall', '未公开':'Unknown',
}

# 标题式大小写：实词首字母大写，虚词小写，缩写保持大写
MINOR = {'and','from','of','the','a','an','in','to','for','with','by','after'}
KEEP_UPPER = {'ALS','COPD','COVID-19','COVID','DNA','RNA','AIDS','BASE'}
def title_en(s):
    words = s.split()
    out=[]
    for i,w in enumerate(words):
        up=w.upper()
        if up in KEEP_UPPER: out.append(up)
        elif w.lower() in MINOR and i>0: out.append(w.lower())
        elif "'" in w: out.append(w[0].upper()+w[1:])  # Parkinson's
        elif '-' in w: out.append('-'.join(p[0].upper()+p[1:] for p in w.split('-')))
        else: out.append(w[0].upper()+w[1:].lower() if w else w)
    return ' '.join(out)

# 为每个规范中文名挑选标准英文名（优先标题式写法）
def pick_en(cn, ens):
    if cn in EN_OVERRIDE: return EN_OVERRIDE[cn]
    ens = [e for e in ens if e]
    if not ens: return ''
    seen = {}
    for e in ens:
        k = e.lower()
        if k not in seen or (e[0:1].isupper() and not seen[k][0:1].isupper()):
            seen[k] = e
    uniq = list(seen.values())
    uniq.sort(key=lambda e: (not e[0:1].isupper(), len(e)))
    return title_en(uniq[0])

# 归纳描述：按死因子类给出简明说明
DESC = {
'癌症':'各类恶性肿瘤的统称，未指明具体器官',
'心脏病发作':'心肌缺血导致的急性心脏事件（心肌梗死）',
'交通事故':'道路车辆碰撞等交通意外',
'枪击':'枪械射击造成的伤亡',
'中风':'脑部供血中断或血管破裂导致的急性脑损伤',
'心脏骤停':'心脏突然停止有效搏动',
'心力衰竭':'心脏泵血功能严重衰退',
'空袭':'空中军事打击造成的伤亡',
'疾病（未详）':'记载为疾病但未说明具体病名',
'肺炎':'肺部实变的感染性疾病',
'自杀':'自主结束生命',
'阿尔茨海默病':'老年痴呆的最常见类型，神经退行性疾病',
'注射死刑':'以药物注射方式执行死刑',
'肌萎缩侧索硬化症':'运动神经元退行性疾病，俗称渐冻症',
'跌倒':'摔倒造成的伤害',
'帕金森病':'中枢神经系统退行性疾病，以震颤和运动迟缓为特征',
'肺癌':'肺组织恶性肿瘤',
'胰腺癌':'胰腺恶性肿瘤，恶性程度高',
'脑出血':'脑实质内血管破裂出血',
'前列腺癌':'前列腺恶性肿瘤',
'心脏病':'心脏疾病的统称，未指明具体类型',
'溺水':'淹没于水中导致的窒息死亡',
'痴呆':'认知功能进行性衰退综合征',
'白血病':'造血系统的恶性肿瘤，俗称血癌',
'脑癌':'脑部恶性肿瘤',
'多器官衰竭':'两个以上器官功能同时衰竭',
'直升机失事':'直升机坠毁事故',
'路易体痴呆':'以路易小体为特征的神经退行性痴呆',
'刺伤':'锐器刺戳造成的伤亡',
'安乐死':'出于减轻痛苦目的经许可结束生命',
'淋巴瘤':'淋巴系统恶性肿瘤',
'肺纤维化':'肺组织瘢痕化导致呼吸功能衰竭',
'胶质母细胞瘤':'最常见的恶性脑肿瘤',
'遇害':'被他人杀害',
'吸入性肺炎':'吸入异物或呕吐物引发的肺部感染',
'处决':'依法执行死刑',
'心肺骤停':'心脏与呼吸功能同时停止',
'战争':'战争行动中死亡',
'新冠病毒感染':'新型冠状病毒（COVID-19）感染',
'未公开':'死因未对外公布',
'痴呆与帕金森病':'痴呆与帕金森病共病',
'空难':'民用或军用航空器坠毁事故',
'肾病':'肾脏疾病的统称',
'肾衰竭':'肾脏功能严重丧失',
'脑膜炎':'脑膜炎症，多由感染引起',
'腹痛':'腹部疼痛，原表记为 colic（绞痛）',
'谋杀':'被他人蓄意杀害',
'遇刺':'遭暗杀身亡',
'住宅火灾':'住宅失火造成的伤亡',
'协助自杀':'在他人协助下结束生命',
'呼吸衰竭':'肺部气体交换功能严重障碍',
'哮喘发作':'支气管哮喘急性发作',
'器官衰竭':'器官功能衰竭',
'地震':'地震灾害造成的伤亡',
'多发性硬化':'中枢神经系统脱髓鞘疾病',
'头部受伤':'头部创伤',
'子宫内膜癌':'子宫内膜恶性肿瘤',
'心肾疾病':'心脏与肾脏疾病共病',
'心脏手术并发症':'心脏手术引发的并发症',
'慢性阻塞性肺病':'慢性阻塞性肺疾病（COPD）',
'手术并发症':'手术引发的并发症',
'术后并发症':'手术后发生的并发症',
'消化道出血':'胃肠道出血',
'火车事故':'铁路列车事故',
'糖尿病':'血糖代谢紊乱疾病',
'结肠癌':'结肠恶性肿瘤',
'肠癌':'肠道恶性肿瘤',
'肺病':'肺部疾病的统称',
'肺部感染':'肺组织感染',
'肾癌':'肾脏恶性肿瘤',
'脑损伤':'脑部创伤',
'血管性痴呆':'脑血管病变导致的痴呆',
'赛车事故':'赛车运动中的碰撞事故',
'跌倒并发症':'跌倒后引发的并发症',
'运动神经元病':'运动神经元退行性疾病',
'间皮瘤':'多见于胸膜的恶性肿瘤',
'阵亡':'军事行动中作战死亡',
'乙型肝炎':'乙型病毒性肝炎',
'乳腺癌':'乳腺恶性肿瘤',
'公交车事故':'公交车交通事故',
'副肿瘤性天疱疮':'与肿瘤相关的自身免疫性皮肤病',
'动力伞坠毁':'动力伞飞行事故',
'动脉粥样硬化性心血管病':'动脉粥样硬化导致的心血管疾病',
'医学并发症':'医疗过程中的并发症',
'吸入烟雾':'火灾中吸入有毒烟雾',
'唾液腺癌':'唾液腺恶性肿瘤',
'喉癌':'喉部恶性肿瘤',
'地雷':'地雷爆炸造成的伤亡',
'坦克炮火':'坦克炮击造成的伤亡',
'多器官衰竭与肺炎':'多器官衰竭合并肺炎',
'尤文肉瘤':'常见于儿童的骨与软组织恶性肿瘤',
'尿路感染':'泌尿系统感染',
'帕金森病、痴呆与跌倒':'帕金森病合并痴呆及跌倒',
'帕金森病痴呆与跌倒':'帕金森病痴呆合并跌倒',
'并发症':'并发症，未指明具体类型',
'心肺肾疾病':'心、肺、肾多器官疾病',
'心脏动脉瘤':'心脏壁局部膨出',
'心脏手术':'心脏手术相关死亡',
'心脏缺陷':'先天性或后天性心脏结构异常',
'心衰与慢阻肺':'心力衰竭合并慢性阻塞性肺病',
'心衰与肾病':'心力衰竭合并肾脏疾病',
'急性呼吸衰竭':'突发的严重呼吸功能衰竭',
'急性髓系白血病':'急性骨髓性白血病',
'意外酒精中毒':'意外摄入过量酒精中毒',
'感染性休克':'严重感染导致的休克',
'慢阻肺并发症':'慢性阻塞性肺病引发的并发症',
'摩托车事故':'摩托车交通事故',
'支气管肺炎':'支气管肺组织的感染',
'极限跳伞事故':'BASE 跳伞运动事故',
'枪战':'交火中中弹死亡',
'横纹肌肉瘤':'横纹肌来源的恶性肿瘤',
'武装袭击':'武装分子袭击造成的伤亡',
'殴打致死':'被殴打致死',
'流感':'流行性感冒',
'火灾':'火灾造成的伤亡',
'痴呆并发症':'痴呆引发的并发症',
'痴呆相关并发症':'与痴呆相关的并发症',
'癫痫发作':'癫痫持续或急性发作',
'皮肤癌':'皮肤恶性肿瘤',
'皮质基底节综合征':'罕见的神经退行性疾病',
'直升机事故':'直升机飞行事故',
'直肠癌':'直肠恶性肿瘤',
'短暂患病':'短期疾病后去世',
'糖尿病与心脏病':'糖尿病合并心脏病',
'糖尿病与肺癌':'糖尿病合并肺癌',
'糖尿病并发症':'糖尿病引发的并发症',
'结直肠癌':'结肠与直肠恶性肿瘤',
'肉瘤':'间叶组织恶性肿瘤',
'肝病':'肝脏疾病的统称',
'肝癌':'肝脏恶性肿瘤',
'肝细胞癌':'肝细胞来源的恶性肿瘤',
'肝衰竭':'肝脏功能严重丧失',
'肠梗阻':'肠道内容物通过受阻',
'股骨骨折':'股骨骨折引发的并发症',
'肩部骨折':'肩部骨折引发的并发症',
'肺气肿':'肺泡壁破坏导致的慢性肺病',
'肺炎与前列腺癌':'肺炎合并前列腺癌',
'胃癌':'胃部恶性肿瘤',
'胆管癌':'胆管恶性肿瘤',
'胸腔积液':'胸膜腔液体积聚',
'胸部感染':'胸腔部位感染',
'脊髓损伤':'脊髓创伤',
'脑动脉瘤':'脑动脉局部扩张破裂',
'脑梗死':'脑组织缺血性坏死',
'腹膜炎':'腹膜炎症',
'膝关节手术':'膝关节手术相关死亡',
'自然死亡':'无明确疾病的自然死亡',
'自行车事故':'自行车交通事故',
'船只相撞':'船舶碰撞事故',
'药物成瘾':'药物滥用成瘾',
'袭击':'遭袭击身亡',
'袭击伤':'袭击造成的创伤',
'警方执法事件':'与警方执法相关的死亡',
'误食':'误食有毒有害物质',
'败血症':'病原体入血导致的全身感染',
'跌倒致头部受伤':'跌倒造成头部创伤',
'进行性核上性麻痹':'罕见的神经退行性疾病',
'雪崩':'雪崩灾害造成的伤亡',
'食管癌':'食管恶性肿瘤',
'骨癌':'骨骼恶性肿瘤',
'骨髓瘤':'浆细胞恶性肿瘤',
}

def main():
    extra = json.load(open(os.path.join(BASE,'archive-data','extra.json'),encoding='utf-8'))
    info = collections.defaultdict(lambda:{'en':collections.Counter(),'cat':collections.Counter(),'n':0})
    def feed(x):
        c=x.get('causeOfDeath')
        if not c: return
        d=info[c]; d['n']+=1
        cat=x.get('causeCategory')
        if cat: d['cat'][cat]+=1
        e=extra.get(x['id'],{}).get('causeOriginal')
        if e: d['en'][e]+=1
    for f in sorted(glob.glob(os.path.join(BASE,'archive-data','20*.js'))):
        s=open(f,encoding='utf-8').read()
        for x in json.loads(s[s.index('['):s.rindex(']')+1]): feed(x)
    s=open(os.path.join(BASE,'data','deaths.js'),encoding='utf-8').read()
    for x in json.loads(s[s.index('['):s.rindex(']')+1]): feed(x)
    # CAUSE 表补充英文
    en2cn=collections.defaultdict(set)
    for e,cn in r.CAUSE.items(): en2cn[cn].add(e)
    rows=[]
    for cn,d in info.items():
        ens=set(d['en']) | en2cn.get(cn,set())
        en=pick_en(cn, ens)
        cat=d['cat'].most_common(1)[0][0] if d['cat'] else '疾病'
        desc=DESC.get(cn, '')
        if not desc: print('缺描述:', cn)
        rows.append({'name':cn,'en':en,'category':cat,'desc':desc,'count':d['n'],
                     'aliases':sorted(ens)})
    rows.sort(key=lambda x:(-x['count'], x['name']))
    out=os.path.join(BASE,'archive-data','死因规范字典.json')
    json.dump(rows, open(out,'w',encoding='utf-8'), ensure_ascii=False, indent=2)
    # CSV
    with open(os.path.join(BASE,'archive-data','死因规范字典.csv'),'w',encoding='utf-8-sig',newline='') as f:
        w=csv.writer(f); w.writerow(['中文名','英文名','大类','归纳描述','出现次数','别名/原始标签'])
        for x in rows: w.writerow([x['name'],x['en'],x['category'],x['desc'],x['count'],' / '.join(x['aliases'])])
    # Markdown
    with open(os.path.join(BASE,'archive-data','死因规范字典.md'),'w',encoding='utf-8') as f:
        f.write('# 死因规范字典表\n\n')
        f.write('共 %d 种规范死因。中文名为统一后的标准写法，英文名为原表标准标签，归纳描述说明死因类型，大类用于统计分组。\n\n' % len(rows))
        f.write('| 中文名 | 英文名 | 大类 | 归纳描述 | 条数 |\n|---|---|---|---|---:|\n')
        for x in rows:
            f.write('| %s | %s | %s | %s | %d |\n'%(x['name'],x['en'],x['category'],x['desc'],x['count']))
    print('生成字典:', len(rows), '条, 缺描述:', sum(1 for x in rows if not x['desc']))

if __name__=='__main__': main()
