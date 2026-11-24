#!/usr/bin/env python3
"""
人物全表清洗脚本
输入：人物全表_116817人.xlsx
输出：archive-data/ 下 14 个年度 JS 分片 + 元数据 + 国家/领域映射

清洗规则：
1. 国家/地区统一映射为中文；台湾、香港、澳门一律写作 中国台湾 / 中国香港 / 中国澳门
2. 领域标签从 4606 种收敛到 11 个中文领域
3. 年龄 -1 / 异常值置 null
4. 中文名优先，缺失时为 ''
5. 输出分片：window.ARCHIVE_2013 = [...] 等，供页面按年懒加载
"""
import openpyxl, json, re, os, collections, sys

SRC = '/root/uploads/1795504916120856186-人物全表_116817人.xlsx'
OUT = '/workspace/memento-web/archive-data'

# ── 国家/地区映射（108 种）────────────────────────────────
COUNTRY = {
    'America':'美国','Britain':'英国','England':'英国','Scotland':'英国','Wales':'英国',
    'India':'印度','France':'法国','Canada':'加拿大','Italy':'意大利','Germany':'德国',
    'Russia':'俄罗斯','Australia':'澳大利亚','Spain':'西班牙','Brazil':'巴西','Poland':'波兰',
    'the Netherlands':'荷兰','Ireland':'爱尔兰','New Zealand':'新西兰','China':'中国',
    'Taiwan':'中国台湾','Hong Kong':'中国香港','Macao':'中国澳门','Macau':'中国澳门',
    'Norway':'挪威','Czechia':'捷克','Mexico':'墨西哥','Ukraine':'乌克兰','Argentina':'阿根廷',
    'Sweden':'瑞典','Hungary':'匈牙利','Belgium':'比利时','Israel':'以色列','South Africa':'南非',
    'Indonesia':'印度尼西亚','Romania':'罗马尼亚','Austria':'奥地利','Japan':'日本',
    'the Philippines':'菲律宾','Nigeria':'尼日利亚','Greece':'希腊','Switzerland':'瑞士',
    'Bangladesh':'孟加拉国','Turkey':'土耳其','Finland':'芬兰','South Korea':'韩国',
    'Serbia':'塞尔维亚','Portugal':'葡萄牙','Chile':'智利','Denmark':'丹麦','Colombia':'哥伦比亚',
    'Egypt':'埃及','Malaysia':'马来西亚','Cuba':'古巴','Croatia':'克罗地亚','Bulgaria':'保加利亚',
    'Peru':'秘鲁','Estonia':'爱沙尼亚','Ghana':'加纳','Iran':'伊朗','Moldova':'摩尔多瓦',
    'Uruguay':'乌拉圭','Kenya':'肯尼亚','Pakistan':'巴基斯坦','Palestine':'巴勒斯坦',
    'Lebanon':'黎巴嫩','Thailand':'泰国','Iraq':'伊拉克','Belarus':'白俄罗斯','Tunisia':'突尼斯',
    'Latvia':'拉脱维亚','Syria':'叙利亚','Slovenia':'斯洛文尼亚','Cameroon':'喀麦隆',
    'Bosnia':'波黑','Saudi Arabia':'沙特阿拉伯','Sri Lanka':'斯里兰卡','Iceland':'冰岛',
    'Bolivia':'玻利维亚','Jordan':'约旦','Azerbaijan':'阿塞拜疆','Costa Rica':'哥斯达黎加',
    'Togo':'多哥','Tanzania':'坦桑尼亚','Fiji':'斐济','Madagascar':'马达加斯加',
    'North Korea':'朝鲜','Mauritania':'毛里塔尼亚','Suriname':'苏里南',
    'Trinidad and Tobago':'特立尼达和多巴哥','Georgia':'格鲁吉亚','Kyrgyzstan':'吉尔吉斯斯坦',
    'Guyana':'圭亚那','Oman':'阿曼','Morocco':'摩洛哥','Nepal':'尼泊尔','Senegal':'塞内加尔',
    'Mali':'马里','Myanmar':'缅甸','Vietnam':'越南','Rwanda':'卢旺达','Sudan':'苏丹',
    'Panama':'巴拿马','Ethiopia':'埃塞俄比亚','Mozambique':'莫桑比克','Malta':'马耳他',
    'Afghanistan':'阿富汗','Albania':'阿尔巴尼亚','Dominican Republic':'多米尼加',
    'Armenia':'亚美尼亚','Algeria':'阿尔及利亚',
}

# ── 领域映射：英文标签 → 11 个中文领域 ─────────────────
FIELD_MAP = {
    # 科技
    'scientists':'科技','engineers':'科技','inventors':'科技','tech':'科技',
    'computer scientists':'科技','astronomers':'科技','physicists':'科技','chemists':'科技',
    'mathematicians':'科技','biologists':'科技','architects':'科技',
    # 文艺
    'actors':'文艺','actresses':'文艺','artists':'文艺','musicians':'文艺','writers':'文艺',
    'singers':'文艺','painters':'文艺','sculptors':'文艺','poets':'文艺','authors':'文艺',
    'composers':'文艺','dancers':'文艺','photographers':'文艺','designers':'文艺',
    'film directors':'文艺','novelists':'文艺','actor':'文艺','actress':'文艺',
    'musician':'文艺','writer':'文艺','singer':'文艺','artist':'文艺','poet':'文艺',
    'author':'文艺','businessman':'商业',
    # 影视
    'film actors':'影视','television actors':'影视','directors':'影视',
    'film producers':'影视','screenwriters':'影视','voice actors':'影视',
    # 军政
    'politicians':'军政','politician':'军政','military':'军政','generals':'军政',
    'presidents':'军政','prime ministers':'军政','monarchs':'军政','diplomats':'军政',
    'american politician':'军政','indian politician':'军政','civil servants':'军政',
    # 社科
    'lawyers':'社科','lawyer':'社科','judges':'社科','economists':'社科',
    'philosophers':'社科','historians':'社科','sociologists':'社科','educators':'社科',
    'activists':'社科','criminologists':'社科',
    # 体育
    'athletes':'体育','sports':'体育','footballers':'体育','baseball players':'体育',
    'basketball players':'体育','olympians':'体育','boxers':'体育','racing drivers':'体育',
    'golfers':'体育','tennis players':'体育','swimmers':'体育','coaches':'体育',
    'english footballer':'体育','american football player':'体育','american baseball player':'体育',
    'australian footballer':'体育',
    # 医药
    'doctors':'医药','physicians':'医药','surgeons':'医药','nurses':'医药',
    'pharmacists':'医药','medical researchers':'医药','dentists':'医药',
    # 商业
    'businesspeople':'商业','entrepreneurs':'商业','businessmen':'商业','businesswomen':'商业',
    'executives':'商业','investors':'商业','bankers':'商业',
    # 传媒
    'journalists':'传媒','journalist':'传媒','broadcasters':'传媒','editors':'传媒',
    'publishers':'传媒','news anchors':'传媒',
    # 宗教
    'religious leaders':'宗教','clergy':'宗教','priests':'宗教','rabbis':'宗教',
    'imams':'宗教','pastors':'宗教','theologians':'宗教',
    # 其他
    'other':'其他','criminals':'其他','unknown':'其他',
}

FIELD_ORDER = ['科技','文艺','影视','军政','社科','体育','医药','商业','传媒','宗教','其他']

def map_country(raw):
    if not raw: return ''
    parts = [p.strip() for p in str(raw).split(';') if p.strip()]
    out = []
    for p in parts:
        # 强制规范：台港澳
        if p in ('Taiwan','taiwan','台湾','Taiwanese'):
            name = '中国台湾'
        elif p in ('Hong Kong','hongkong','HongKong','香港','HK'):
            name = '中国香港'
        elif p in ('Macao','Macau','macau','澳门','Macao SAR'):
            name = '中国澳门'
        else:
            name = COUNTRY.get(p, p)  # 未映射保留英文原名
        if name not in out: out.append(name)
    return ';'.join(out)

# 长尾标签关键词规则（按优先级匹配，解决 4576 种长尾英文标签）
KEYWORD_RULES = [
    (('politician','senator','diplomat','minister','president','prime minister','monarch','king','queen','emperor','governor','mayor','civil servant','bureaucrat','general','military','soldier','admiral','commander'), '军政'),
    (('footballer','basketball','baseball','soccer','athlete','olympian','boxer','racing driver','golfer','tennis','swimmer','wrestler','hockey player','cricketer','cyclist','skier','fencer','judoka','farmer'), '体育'),
    (('actor','actress','musician','singer','writer','novelist','poet','artist','painter','sculptor','composer','dancer','photographer','designer','author','painting','film director'), '文艺'),
    (('director','producer','screenwriter','film','television','tv ','voice actor','cinematographer'), '影视'),
    (('scientist','engineer','inventor','professor','academic','astronomer','physicist','chemist','mathematician','biologist','architect','researcher','scholar','teacher'), '科技'),
    (('doctor','physician','surgeon','nurse','pharmacist','dentist','medical','pediatrician','cardiologist'), '医药'),
    (('journalist','broadcaster','editor','publisher','news anchor','columnist','reporter','commentator'), '传媒'),
    (('lawyer','judge','economist','philosopher','historian','sociologist','educator','activist','criminologist','clergyman','theologian'), '社科'),
    (('business','entrepreneur','executive','investor','banker','CEO','founder','industrialist'), '商业'),
    (('priest','rabbi','imam','pastor','bishop','cardinal','religious','clergy','monk','nun'), '宗教'),
    (('criminal','murderer','convicted','execution','terrorist','heart attack','traffic collision','cancer','stroke','cardiac arrest','lung cancer'), '其他'),
]

def classify_tag(t):
    if t in FIELD_MAP: return FIELD_MAP[t]
    for keys, field in KEYWORD_RULES:
        if any(k in t for k in keys): return field
    return None

def map_fields(raw):
    if not raw: return []
    tags = [t.strip().lower() for t in str(raw).split(';') if t.strip()]
    out = []
    for t in tags:
        mapped = classify_tag(t)
        if mapped and mapped not in out: out.append(mapped)
    # 兜底：未命中任何标签 → 其他
    if not out and tags: out = ['其他']
    # 保持固定顺序
    return [f for f in FIELD_ORDER if f in out]

def clean_age(v):
    try:
        a = int(v)
        return a if 0 <= a <= 120 else None
    except (ValueError, TypeError):
        return None

def clean_cause(raw):
    if not raw: return None
    try:
        obj = json.loads(str(raw))
        label = str(obj.get('label') or '').strip()
        status = str(obj.get('status') or '').strip()
        return {'label':label,'status':status} if label or status else None
    except Exception:
        return None

def main():
    os.makedirs(OUT, exist_ok=True)
    wb = openpyxl.load_workbook(SRC, read_only=True, data_only=True)
    ws = wb['人物全表']
    rows = ws.iter_rows(values_only=True)
    hdr = next(rows)
    ix = {h:i for i,h in enumerate(hdr)}

    by_year = collections.defaultdict(list)
    stats = collections.Counter()
    country_seen = collections.Counter()
    field_seen = collections.Counter()

    for r in rows:
        ident = str(r[ix['id']] or '')
        date = str(r[ix['date']] or '')
        if not ident or not re.fullmatch(r'\d{4}-\d{2}-\d{2}', date):
            stats['dropped_invalid'] += 1
            continue
        country = map_country(r[ix['country']])
        fields = map_fields(r[ix['fields']])
        age = clean_age(r[ix['age']])
        cn_name = str(r[ix['name']] or '').strip()
        orig = str(r[ix['nameOrig']] or '').strip()
        display = cn_name or orig
        if not display:
            stats['no_name'] += 1
            display = ident
        rec = {
            'id': ident,
            'd': date,
            'n': display,
            'no': orig,
            'c': country,
            'a': age,
            'f': fields,
            'i': str(r[ix['identity']] or '').strip(),
            'w': str(r[ix['wikipediaUrl']] or '').strip(),
            's': str(r[ix['source']] or '').strip(),
            'cd': clean_cause(r[ix['causeOfDeath']]),
        }
        if cn_name: stats['has_cn_name'] += 1
        if age is None: stats['age_null'] += 1
        if country:
            for c in country.split(';'): country_seen[c] += 1
        for f in fields: field_seen[f] += 1
        by_year[date[:4]].append(rec)
        stats['total'] += 1

    # 按日期倒序（与现有站点一致）
    for y in by_year:
        by_year[y].sort(key=lambda x: x['d'], reverse=True)

    # 输出年度分片
    manifest = []
    for y in sorted(by_year):
        fname = f'{y}.js'
        with open(os.path.join(OUT, fname), 'w', encoding='utf-8') as fp:
            fp.write(f'window.ARCHIVE_{y} = ')
            json.dump(by_year[y], fp, ensure_ascii=False, separators=(',',':'))
            fp.write(';\n')
        size = os.path.getsize(os.path.join(OUT, fname))
        manifest.append({'year':int(y),'file':fname,'count':len(by_year[y]),'bytes':size})
        stats[f'file_{y}'] = size

    # 元数据
    meta = {
        'total': stats['total'],
        'years': sorted(by_year.keys()),
        'countryMap': COUNTRY,
        'fieldOrder': FIELD_ORDER,
        'fieldMap': FIELD_MAP,
        'stats': {
            'has_cn_name': stats['has_cn_name'],
            'age_null': stats['age_null'],
            'no_name': stats['no_name'],
            'dropped_invalid': stats['dropped_invalid'],
        },
        'countryCounts': dict(country_seen.most_common()),
        'fieldCounts': dict(field_seen.most_common()),
    }
    with open(os.path.join(OUT,'meta.json'),'w',encoding='utf-8') as fp:
        json.dump(meta, fp, ensure_ascii=False, indent=2)

    print('=== 清洗结果 ===')
    print('总记录:', stats['total'], '| 丢弃无效:', stats['dropped_invalid'])
    print('有中文名:', stats['has_cn_name'], '| 年龄置空:', stats['age_null'], '| 无名回退:', stats['no_name'])
    print('国家(中文)种类:', len(country_seen), '| 领域种类:', len(field_seen))
    print('中国台湾:', country_seen['中国台湾'], '| 中国香港:', country_seen['中国香港'], '| 中国澳门:', country_seen['中国澳门'])
    print('领域分布:', dict(field_seen.most_common()))
    print('\n=== 年度分片 ===')
    for m in manifest:
        print(f"{m['year']}  {m['count']:6d} 条  {m['bytes']/1024:7.1f} KB  {m['file']}")
    print('总大小 MB:', round(sum(m['bytes'] for m in manifest)/1024/1024,2))

if __name__ == '__main__':
    main()
