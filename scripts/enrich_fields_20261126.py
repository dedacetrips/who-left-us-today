#!/usr/bin/env python3
"""补齐字段（2026-11-26）：死因 / 国别 / 年龄 / 中文简介
原则：只从 dead-people.com 正文或 identity 的明确表述提取，宁缺毋滥。
- 死因：正文明确句式 + 死因字典别名匹配，不猜测、不外推
- 国别/年龄：正文明确 nationality / aged N
- 简介：identity 的「姓名, <角色>」按英中角色词典翻译，只覆盖可可靠翻译的模式
生成审核清单 JSON；--apply 时写主表（不触碰已填字段）。
"""
import re, json, sys, html, shutil
from pathlib import Path
from datetime import datetime
from collections import Counter

ROOT = Path(__file__).resolve().parent.parent
DEATHS = ROOT / 'data' / 'deaths.js'
FT = ROOT / 'archive-data' / 'deadpeople-2026-fulltext.json'
DIC = ROOT / 'archive-data' / '死因规范字典.json'
OUT = ROOT / 'archive-data' / 'enrich-fields-20261126.json'

# ---------- 工具 ----------
def load_col(f):
    s = f.read_text(encoding='utf-8')
    d = json.loads(re.search(r'window\.\w+\s*=\s*(\{.*)', s, re.S).group(1).rstrip().rstrip(';'))
    return d['cols'], d['rows']

def plain(h):
    t = re.sub(r'<script.*?</script>|<style.*?</style>', ' ', h or '', flags=re.S | re.I)
    t = re.sub(r'<[^>]+>', ' ', t)
    return re.sub(r'\s+', ' ', html.unescape(t)).strip()

# ---------- 死因 ----------
def build_cause_map():
    dic = json.loads(DIC.read_text(encoding='utf-8'))
    amap = {}
    for x in dic:
        for a in x['aliases']:
            amap[a.lower().strip()] = (x['name'], x['category'])
    # 补充同义（字典未覆盖但语义确定）
    extra = {
        'lung cancer': ('肺癌','疾病'), 'pancreatic cancer': ('胰腺癌','疾病'),
        'liver cancer': ('肝癌','疾病'), 'esophageal cancer': ('食管癌','疾病'),
        'colon cancer': ('结肠癌','疾病'), 'blood cancer': ('白血病','疾病'),
        'brain cancer': ('脑癌','疾病'), 'bone cancer': ('骨癌','疾病'),
        'skin cancer': ('皮肤癌','疾病'), 'prostate cancer': ('前列腺癌','疾病'),
        'breast cancer': ('乳腺癌','疾病'), 'stomach cancer': ('胃癌','疾病'),
        'kidney cancer': ('肾癌','疾病'), 'throat cancer': ('喉癌','疾病'),
        'ovarian cancer': ('卵巢癌','疾病'), 'bladder cancer': ('膀胱癌','疾病'),
        'colorectal cancer': ('结直肠癌','疾病'), 'bile duct cancer': ('胆管癌','疾病'),
        'multiple myeloma': ('多发性骨髓瘤','疾病'), 'myeloma': ('多发性骨髓瘤','疾病'),
        'heart disease': ('心脏病','疾病'), 'coronary artery disease': ('冠心病','疾病'),
        'respiratory failure': ('呼吸衰竭','疾病'), 'renal failure': ('肾衰竭','疾病'),
        'kidney failure': ('肾衰竭','疾病'), 'liver failure': ('肝衰竭','疾病'),
        'multi-organ failure': ('多器官衰竭','疾病'), 'organ failure': ('器官衰竭','疾病'),
        'complications of surgery': ('手术并发症','疾病'),
        'traffic collision': ('交通事故','意外事故'), 'road accident': ('交通事故','意外事故'),
        'motorcycle accident': ('摩托车事故','意外事故'), 'bicycle accident': ('自行车事故','意外事故'),
        'plane crash': ('空难','意外事故'), 'helicopter crash': ('直升机失事','意外事故'),
        'aircraft crash': ('空难','意外事故'), 'boat accident': ('船只事故','意外事故'),
        'accidental fall': ('跌倒','意外事故'), 'fall': ('跌倒','意外事故'),
        'drowning': ('溺水','意外事故'), 'fire': ('火灾','意外事故'),
        'carbon monoxide poisoning': ('一氧化碳中毒','意外事故'),
        'gunshot wound': ('枪击','暴力冲突'), 'gunshot wounds': ('枪击','暴力冲突'),
        'stabbing': ('刀刺伤','暴力冲突'), 'airstrike': ('空袭','暴力冲突'),
        'drug overdose': ('药物过量','意外事故'), 'overdose': ('药物过量','意外事故'),
        'assassination': ('遇刺','暴力冲突'), 'execution': ('处决','暴力冲突'),
        'lethal injection': ('注射死刑','暴力冲突'),
    }
    for k, v in extra.items():
        amap.setdefault(k, v)
    return amap

# 死因句式：仅在这些明确结构内提取
CAUSE_PATTERNS = [
    re.compile(r'\bdied\s+(?:on\s+[^,.]*,?\s*)?of\s+((?:[a-z\u2019\'-]+\s+){0,4}[a-z\u2019\'-]+)', re.I),
    re.compile(r'\bdied\s+(?:on\s+[^,.]*,?\s*)?from\s+((?:[a-z\u2019\'-]+\s+){0,4}[a-z\u2019\'-]+)', re.I),
    re.compile(r'\bfrom\s+complications\s+(?:of|from|following)\s+((?:[a-z\u2019\'-]+\s+){0,4}[a-z\u2019\'-]+)', re.I),
    re.compile(r'\bafter\s+(?:a\s+)?(?:battle|fight)\s+with\s+((?:[a-z\u2019\'-]+\s+){0,4}[a-z\u2019\'-]+)', re.I),
    re.compile(r'\bsuccumbed\s+to\s+((?:[a-z\u2019\'-]+\s+){0,4}[a-z\u2019\'-]+)', re.I),
    re.compile(r'\bcause\s+of\s+death\s+(?:was|is)\s+((?:[a-z\u2019\'-]+\s+){0,4}[a-z\u2019\'-]+)', re.I),
]
# 噪声词：命中则跳过（避免 "died of natural causes" 之外的误配，或日期/地名）
SKIP_PHRASE = re.compile(r'\b(on|in|at|november|december|january|february|march|april|may|june|july|august|september|october|aged|age|years|old|york|london|paris|hospital|home|city|county|district)\b', re.I)
VAGUE = {'complications','complication','illness','disease','causes','natural causes','injuries','wounds','conditions'}

def extract_cause(text, amap):
    head = text[:1200]
    phrases = []
    for p in CAUSE_PATTERNS:
        for m in p.finditer(head):
            phrases.append(m.group(1).lower())
    aliases = sorted(amap.keys(), key=len, reverse=True)
    best = None
    for ph in phrases:
        ph = re.sub(r'\s+', ' ', ph).strip()
        # 先整短语匹配，再逐别名匹配
        candidates = []
        if ph in amap:
            candidates.append(ph)
        for a in aliases:
            if a not in VAGUE and re.search(r'\b' + re.escape(a) + r'\b', ph):
                candidates.append(a)
        # 取最长别名（最具体）
        for a in sorted(set(candidates), key=len, reverse=True):
            if a in VAGUE:
                continue
            best = amap[a]
            return best + (a, ph)
    return None

# ---------- 国别 / 年龄 ----------
NAT = [
 ('South Sudanese','南苏丹'),('North Korean','朝鲜'),('South Korean','韩国'),('Central African','中非'),
 ('New Zealander','新西兰'),('Papua New Guinean','巴布亚新几内亚'),('Sri Lankan','斯里兰卡'),
 ('East Timorese','东帝汶'),('Hong Konger','中国香港'),('Bahraini','巴林'),('Qatari','卡塔尔'),
 ('Emirati','阿联酋'),('Saudi','沙特'),('Kuwaiti','科威特'),('Omani','阿曼'),('Yemeni','也门'),
 ('Jordanian','约旦'),('Icelandic','冰岛'),('Luxembourgish','卢森堡'),
 ('American','美国'),('British','英国'),('English','英国'),('Scottish','英国'),('Welsh','英国'),
 ('Irish','爱尔兰'),('Indian','印度'),('Japanese','日本'),('Chinese','中国'),('French','法国'),
 ('German','德国'),('Canadian','加拿大'),('Australian','澳大利亚'),('Russian','俄罗斯'),
 ('Italian','意大利'),('Spanish','西班牙'),('Filipino','菲律宾'),('Filipina','菲律宾'),
 ('Indonesian','印度尼西亚'),('Vietnamese','越南'),('Thai','泰国'),('Singaporean','新加坡'),
 ('Malaysian','马来西亚'),('Pakistani','巴基斯坦'),('Bangladeshi','孟加拉国'),('Nepalese','尼泊尔'),
 ('Afghan','阿富汗'),('Iranian','伊朗'),('Iraqi','伊拉克'),('Israeli','以色列'),('Palestinian','巴勒斯坦'),
 ('Lebanese','黎巴嫩'),('Syrian','叙利亚'),('Turkish','土耳其'),('Greek','希腊'),('Polish','波兰'),
 ('Swedish','瑞典'),('Norwegian','挪威'),('Danish','丹麦'),('Finnish','芬兰'),('Dutch','荷兰'),
 ('Belgian','比利时'),('Swiss','瑞士'),('Austrian','奥地利'),('Portuguese','葡萄牙'),
 ('Croatian','克罗地亚'),('Serbian','塞尔维亚'),('Ukrainian','乌克兰'),('Romanian','罗马尼亚'),
 ('Hungarian','匈牙利'),('Czech','捷克'),('Slovak','斯洛伐克'),('Bulgarian','保加利亚'),
 ('Georgian','格鲁吉亚'),('Armenian','亚美尼亚'),('Kazakh','哈萨克斯坦'),('Uzbek','乌兹别克斯坦'),
 ('Kyrgyz','吉尔吉斯斯坦'),('Tajik','塔吉克斯坦'),('Mongolian','蒙古'),('Burmese','缅甸'),
 ('Cambodian','柬埔寨'),('Algerian','阿尔及利亚'),('Moroccan','摩洛哥'),('Egyptian','埃及'),
 ('Tunisian','突尼斯'),('Libyan','利比亚'),('Sudanese','苏丹'),('Ethiopian','埃塞俄比亚'),
 ('Somali','索马里'),('Kenyan','肯尼亚'),('Ugandan','乌干达'),('Tanzanian','坦桑尼亚'),
 ('Zimbabwean','津巴布韦'),('Ghanaian','加纳'),('Nigerian','尼日利亚'),('South African','南非'),
 ('Chilean','智利'),('Argentinian','阿根廷'),('Colombian','哥伦比亚'),('Peruvian','秘鲁'),
 ('Venezuelan','委内瑞拉'),('Brazilian','巴西'),('Mexican','墨西哥'),('Cuban','古巴'),
 ('Fijian','斐济'),('Mozambican','莫桑比克'),('Angolan','安哥拉'),('Zambian','赞比亚'),
 ('Namibian','纳米比亚'),('Rwandan','卢旺达'),('Jamaican','牙买加'),('Haitian','海地'),
 ('Lithuanian','立陶宛'),('Latvian','拉脱维亚'),('Estonian','爱沙尼亚'),('Slovenian','斯洛文尼亚'),
 ('Bosnian','波黑'),('Moldovan','摩尔多瓦'),('Belarusian','白俄罗斯'),('Azerbaijani','阿塞拜疆'),
 ('Maldivian','马尔代夫'),('Bhutanese','不丹'),('Laotian','老挝'),('Ivorian','科特迪瓦'),
 ('Senegalese','塞内加尔'),('Cameroonian','喀麦隆'),('Gabonese','加蓬'),('Sierra Leonean','塞拉利昂'),
 ('Liberian','利比里亚'),('Togolese','多哥'),('Beninese','贝宁'),('Malian','马里'),
 ('Chadian','乍得'),('Guinean','几内亚'),('Congolese','刚果'),('Gambian','冈比亚'),
 ('Eritrean','厄立特里亚'),('Seychellois','塞舌尔'),('Mauritian','毛里求斯'),('Samoan','萨摩亚'),
 ('Tongan','汤加'),('Vanuatuan','瓦努阿图'),('Barbadian','巴巴多斯'),('Bahamian','巴哈马'),
 ('Belizean','伯利兹'),('Guyanese','圭亚那'),('Surinamese','苏里南'),('Paraguayan','巴拉圭'),
 ('Uruguayan','乌拉圭'),('Bolivian','玻利维亚'),('Ecuadorian','厄瓜多尔'),('Guatemalan','危地马拉'),
 ('Salvadoran','萨尔瓦多'),('Honduran','洪都拉斯'),('Nicaraguan','尼加拉瓜'),
 ('Costa Rican','哥斯达黎加'),('Panamanian','巴拿马'),('Dominican','多米尼加'),
 ('Puerto Rican','波多黎各'),('Taiwanese','中国台湾'),('Macanese','中国澳门'),
 ('Maltese','马耳他'),('Cypriot','塞浦路斯'),('Montenegrin','黑山'),('Macedonian','北马其顿'),
 ('Albanian','阿尔巴尼亚'),('Kosovar','科索沃'),('Swazi','斯威士兰'),('Lesothoan','莱索托'),
]
NAT_PAT = re.compile(r'\b(' + '|'.join(re.escape(w) for w, _ in sorted(NAT, key=lambda x: -len(x[0]))) + r')\b', re.I)
NAT_MAP = {w.lower(): c for w, c in NAT}
AGE_PAT = re.compile(r'\baged\s+(\d{1,3})\b|\bat\s+(?:the\s+)?age\s+of\s+(\d{1,3})\b|\bwas\s+(\d{1,3})\b', re.I)

def extract_nat_age(text):
    head = text[:400]
    nat = None
    m = NAT_PAT.search(head)
    if m:
        nat = NAT_MAP.get(m.group(1).lower())
    age = None
    for a in AGE_PAT.finditer(head[:300]):
        v = next(g for g in a.groups() if g)
        n = int(v)
        if 15 <= n <= 115:
            age = n; break
    return nat, age

# ---------- 中文简介（保守翻译） ----------
ROLE_DICT = {
    # 需要先于通用词匹配的复合词
    'australian rules footballer':'澳式足球运动员',
    'american football player':'美式橄榄球运动员',
    'american footballer':'美式橄榄球运动员',
    'canadian football player':'加拿大式橄榄球运动员',
    'rugby league player':'橄榄球联盟球员',
    'association footballer':'足球运动员',
    'political scientist':'政治学家',
    'industrial designer':'工业设计师',
    'classical dancer':'古典舞蹈家',
    'islamic scholar':'伊斯兰学者',
    'army general':'陆军将军',
    'football referee':'足球裁判',
    'acting coach':'表演指导',
    'voice actress':'配音女演员',
    'radio broadcaster':'电台播音员',
    'district judge':'地区法官',
    'politician':'政治人物','former politician':'前政治人物','statesman':'政治家',
    'actor':'演员','actress':'女演员','film actor':'电影演员','television actor':'电视演员',
    'voice actor':'配音演员','singer':'歌手','singer-songwriter':'创作歌手','songwriter':'词曲作者',
    'musician':'音乐人','guitarist':'吉他手','bassist':'贝斯手','drummer':'鼓手','pianist':'钢琴家',
    'violinist':'小提琴家','composer':'作曲家','conductor':'指挥家','rapper':'说唱歌手',
    'footballer':'足球运动员','football player':'足球运动员','soccer player':'足球运动员',
    'basketball player':'篮球运动员','baseball player':'棒球运动员','ice hockey player':'冰球运动员',
    'tennis player':'网球运动员','cricketer':'板球运动员','rugby union player':'橄榄球运动员',
    'golfer':'高尔夫球手','boxer':'拳击手','wrestler':'摔角手','cyclist':'自行车手',
    'swimmer':'游泳运动员','athlete':'运动员','Olympic athlete':'奥运选手','jockey':'骑师',
    'race walker':'竞走运动员','ski player':'滑雪运动员','judoka':'柔道运动员',
    'writer':'作家','novelist':'小说家','poet':'诗人','journalist':'记者','author':'作家',
    'historian':'历史学家','biographer':'传记作家','essayist':'散文家','playwright':'剧作家',
    'screenwriter':'编剧','cartoonist':'漫画家','photographer':'摄影师','editor':'编辑',
    'painter':'画家','artist':'艺术家','sculptor':'雕塑家','architect':'建筑师','designer':'设计师',
    'fashion designer':'时装设计师','graphic designer':'平面设计师',
    'scientist':'科学家','physicist':'物理学家','chemist':'化学家','biologist':'生物学家',
    'geneticist':'遗传学家','virologist':'病毒学家','immunologist':'免疫学家','astronomer':'天文学家',
    'mathematician':'数学家','geologist':'地质学家','economist':'经济学家','sociologist':'社会学家',
    'psychologist':'心理学家','philosopher':'哲学家','professor':'教授','academic':'学者',
    'researcher':'研究员','engineer':'工程师','doctor':'医生','physician':'医生','surgeon':'外科医生',
    'nurse':'护士','dentist':'牙医','veterinarian':'兽医','lawyer':'律师','judge':'法官',
    'diplomat':'外交官','civil servant':'公务员','businessman':'商人','businesswoman':'女商人',
    'entrepreneur':'企业家','CEO':'首席执行官','banker':'银行家','investor':'投资人',
    'activist':'社会活动家','environmentalist':'环保人士','human rights activist':'人权活动家',
    'clergyman':'神职人员','prelate':'主教','priest':'神父','bishop':'主教','cardinal':'枢机主教',
    'rabbi':'拉比','imam':'伊玛目','theologian':'神学家','saint':'圣人',
    'general':'将军','admiral':'海军上将','soldier':'军人','police officer':'警察',
    'farmer':'农民','fisherman':'渔民','chef':'厨师','baker':'面包师',
    'model':'模特','fashion model':'时装模特','dancer':'舞蹈家','choreographer':'编舞',
    'film director':'电影导演','director':'导演','producer':'制片人','film producer':'电影制片人',
    'TV presenter':'电视主持人','radio host':'电台主持人','broadcaster':'播音员','news anchor':'新闻主播',
    'comedian':'喜剧演员','magician':'魔术师','ventriloquist':'腹语师','puppeteer':'木偶师',
    'teacher':'教师','schoolteacher':'教师','principal':'校长','coach':'教练','manager':'经理',
    'sports executive':'体育管理者','referee':'裁判','athletics coach':'田径教练',
    'zoologist':'动物学家','ornithologist':'鸟类学家','botanist':'植物学家','oceanographer':'海洋学家',
    'meteorologist':'气象学家','seismologist':'地震学家','archaeologist':'考古学家',
    'linguist':'语言学家','translator':'翻译家','critic':'评论家','film critic':'影评人',
    'art critic':'艺术评论家','music critic':'乐评人','columnist':'专栏作家',
}
# 角色组合词（用于更细粒度）
ROLE_SUFFIX = [w for w in sorted(ROLE_DICT, key=len, reverse=True)]

def summarize(identity, name):
    """从 identity 的 'Name, <role>.' 生成中文简介；只处理可可靠翻译者。"""
    ident = identity or ''
    # 取第一个逗号后的角色描述（去掉 died 后的内容）
    m = re.match(r'^[^,]+,\s*(.*?)(?:\.\s|$| died| died on| who died)', ident, re.I)
    if not m:
        return None
    desc = m.group(1).strip(' .')
    if not desc or len(desc) > 90:
        return None
    low = desc.lower()
    if 'public figure' in low or 'no further details' in low:
        return None
    # 国别（保留在 desc 上用于复合词判定；匹配时先处理含国别限定词的项目）
    nat = NAT_PAT.search(desc)
    nat_cn = NAT_MAP.get(nat.group(1).lower()) if nat else None
    nat_word = nat.group(1) if nat else None
    # 足球/橄榄球歧义：先对原短语做整体判定（不含国别前缀，避免重复）
    sport_root = None
    dl = desc.lower()
    if 'australian rules football' in dl:
        sport_root = '澳式足球'
    elif 'canadian football' in dl:
        sport_root = '加拿大式橄榄球'
    elif 'american football' in dl or 'gridiron' in dl:
        sport_root = '美式橄榄球'
    elif 'rugby league' in dl:
        sport_root = '橄榄球联盟'
    elif 'rugby union' in dl:
        sport_root = '橄榄球'
    # 澳式足球/加拿大式已含国别，避免叠加前缀
    if sport_root in ('澳式足球', '加拿大式橄榄球'):
        nat_cn = None
    # 移除国别词
    rest = NAT_PAT.sub('', desc, count=1).strip(' ,')
    rest = re.sub(r'^(?:a|an|the)\s+', '', rest, flags=re.I).strip(' .')
    if not rest:
        return None
    # 角色翻译：按词典逐词解析「A and B」结构
    parts = re.split(r'\s+and\s+', rest, flags=re.I)
    roles = []
    for part in parts:
        part = part.strip(' .')
        if not part:
            continue
        p = part.lower()
        # 歧义运动：按具体角色（教练/管理者/球员）生成
        if sport_root and re.search(r'football|gridiron', p):
            if re.search(r'\bcoach\b', p):
                roles.append(sport_root + '教练')
            elif re.search(r'\b(executive|administrator|general manager|manager)\b', p):
                roles.append(sport_root + '管理者')
            else:
                roles.append(sport_root + ('球员' if sport_root in ('澳式足球','加拿大式橄榄球','橄榄球联盟') else '运动员'))
            continue
        # 精确匹配
        if p in ROLE_DICT:
            roles.append(ROLE_DICT[p]); continue
        # 后缀匹配（长词优先）
        hit = None
        for w in ROLE_SUFFIX:
            if re.search(r'\b' + re.escape(w) + r'\b', p):
                hit = ROLE_DICT[w]; break
        if hit:
            roles.append(hit)
        else:
            return None  # 不可靠，放弃
    if not roles:
        return None
    # 去重保序
    seen = set(); uniq = []
    for r in roles:
        if r not in seen: seen.add(r); uniq.append(r)
    role_cn = '、'.join(uniq)
    return f'{nat_cn}{role_cn}' if nat_cn else role_cn


def main():
    apply = '--apply' in sys.argv
    cols, rows = load_col(DEATHS)
    idx = {c: i for i, c in enumerate(cols)}
    ft = json.loads(FT.read_text(encoding='utf-8'))
    amap = build_cause_map()

    add_cause = {}; add_nat = {}; add_age = {}; add_sum = {}
    for r in rows:
        rid = r[idx['id']]
        slug = re.sub(r'^\d{8}-', '', rid)
        v = ft.get(slug)
        text = plain(v['h']) if v else ''
        ident = r[idx['identity']] or ''

        # 死因
        if not r[idx['causeOfDeath']] and text:
            res = extract_cause(text, amap)
            if res:
                add_cause[rid] = {'cause': res[0], 'cat': res[1], 'alias': res[2], 'phrase': res[3]}
        # 国别 / 年龄
        if text and (not r[idx['country']] or not r[idx['age']]):
            nat, age = extract_nat_age(text)
            if nat and not r[idx['country']]:
                add_nat[rid] = nat
            if age and not r[idx['age']]:
                add_age[rid] = age
        # 简介
        if not r[idx['summary']]:
            s = summarize(ident, r[idx['name']])
            if s:
                add_sum[rid] = s

    report = {
        'generated': datetime.now().isoformat(),
        'total': len(rows),
        'add_cause': len(add_cause), 'add_nat': len(add_nat),
        'add_age': len(add_age), 'add_summary': len(add_sum),
        'cause_samples': dict(list(add_cause.items())[:20]),
        'summary_samples': dict(list(add_sum.items())[:20]),
        'cause_detail': add_cause,
        'nat_detail': add_nat, 'age_detail': add_age, 'summary_detail': add_sum,
    }
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'拟补：死因 {len(add_cause)}，国别 {len(add_nat)}，年龄 {len(add_age)}，简介 {len(add_sum)}')
    print('死因样例:', [(k, v['cause']) for k, v in list(add_cause.items())[:8]])
    print('简介样例:', list(add_sum.items())[:8])
    print('清单:', OUT)

    if apply:
        ts = datetime.now().strftime('%Y%m%d-%H%M%S')
        bak = DEATHS.parent / f'deaths.before-enrich-{ts}.js'
        shutil.copy2(DEATHS, bak)
        n = 0
        for r in rows:
            rid = r[idx['id']]
            if rid in add_cause:
                r[idx['causeOfDeath']] = add_cause[rid]['cause']
                r[idx['causeCategory']] = add_cause[rid]['cat']; n += 1
            if rid in add_nat:
                r[idx['country']] = add_nat[rid]; n += 1
            if rid in add_age:
                r[idx['age']] = add_age[rid]; n += 1
            if rid in add_sum:
                r[idx['summary']] = add_sum[rid]; n += 1
        content = '// 人物数据：每天离世的世界名人讣告档案（列式压缩）\nwindow.DEATHS_DATA = ' + \
            json.dumps({'cols': cols, 'rows': rows}, ensure_ascii=False) + ';\n'
        DEATHS.write_text(content, encoding='utf-8')
        print(f'写入完成：{n} 处字段更新；备份 {bak.name}')


if __name__ == '__main__':
    main()
