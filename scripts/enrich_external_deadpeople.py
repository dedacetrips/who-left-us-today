#!/usr/bin/env python3
"""通过外部数据（dead-people.com 完整正文）核验补全 2026 数据的国别与年龄。
保守策略：只从正文明确表述提取，生成审核清单，不直接写主表。
"""
import json, re, html, time, urllib.request, urllib.parse
from pathlib import Path
from collections import Counter

ROOT = Path(__file__).resolve().parent.parent
DEATHS = ROOT / 'data' / 'deaths.js'
OUT = ROOT / 'archive-data' / 'external-verify-20261126.json'
API = 'https://www.dead-people.com/wp-json/wp/v2/posts'
UA = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

# 国别映射（复合在前）
NAT = [
 ('South Sudanese','南苏丹'),('North Korean','朝鲜'),('South Korean','韩国'),('Central African','中非'),
 ('New Zealander','新西兰'),('Papua New Guinean','巴布亚新几内亚'),('Sri Lankan','斯里兰卡'),
 ('East Timorese','东帝汶'),('Hong Konger','中国香港'),('New Zealand','新西兰'),('Bahraini','巴林'),
 ('Qatari','卡塔尔'),('Emirati','阿联酋'),('Saudi','沙特'),('Kuwaiti','科威特'),('Omani','阿曼'),
 ('Yemeni','也门'),('Jordanian','约旦'),('Icelandic','冰岛'),('Luxembourgish','卢森堡'),
 ('American','美国'),('British','英国'),('English','英国'),('Scottish','英国'),('Welsh','英国'),
 ('Irish','爱尔兰'),('Indian','印度'),('Japanese','日本'),('Chinese','中国'),('French','法国'),
 ('German','德国'),('Canadian','加拿大'),('Australian','澳大利亚'),('Russian','俄罗斯'),
 ('Italian','意大利'),('Spanish','西班牙'),('Korean','韩国'),('Filipino','菲律宾'),
 ('Filipina','菲律宾'),('Indonesian','印度尼西亚'),('Vietnamese','越南'),('Thai','泰国'),
 ('Singaporean','新加坡'),('Malaysian','马来西亚'),('Pakistani','巴基斯坦'),('Bangladeshi','孟加拉国'),
 ('Nepalese','尼泊尔'),('Afghan','阿富汗'),('Iranian','伊朗'),('Iraqi','伊拉克'),('Israeli','以色列'),
 ('Palestinian','巴勒斯坦'),('Lebanese','黎巴嫩'),('Syrian','叙利亚'),('Turkish','土耳其'),
 ('Greek','希腊'),('Polish','波兰'),('Swedish','瑞典'),('Norwegian','挪威'),('Danish','丹麦'),
 ('Finnish','芬兰'),('Dutch','荷兰'),('Belgian','比利时'),('Swiss','瑞士'),('Austrian','奥地利'),
 ('Portuguese','葡萄牙'),('Croatian','克罗地亚'),('Serbian','塞尔维亚'),('Ukrainian','乌克兰'),
 ('Romanian','罗马尼亚'),('Hungarian','匈牙利'),('Czech','捷克'),('Slovak','斯洛伐克'),
 ('Bulgarian','保加利亚'),('Georgian','格鲁吉亚'),('Armenian','亚美尼亚'),('Kazakh','哈萨克斯坦'),
 ('Uzbek','乌兹别克斯坦'),('Kyrgyz','吉尔吉斯斯坦'),('Tajik','塔吉克斯坦'),('Mongolian','蒙古'),
 ('Burmese','缅甸'),('Cambodian','柬埔寨'),('Algerian','阿尔及利亚'),('Moroccan','摩洛哥'),
 ('Egyptian','埃及'),('Tunisian','突尼斯'),('Libyan','利比亚'),('Sudanese','苏丹'),
 ('Ethiopian','埃塞俄比亚'),('Somali','索马里'),('Kenyan','肯尼亚'),('Ugandan','乌干达'),
 ('Tanzanian','坦桑尼亚'),('Zimbabwean','津巴布韦'),('Ghanaian','加纳'),('Nigerian','尼日利亚'),
 ('South African','南非'),('Chilean','智利'),('Argentinian','阿根廷'),('Colombian','哥伦比亚'),
 ('Peruvian','秘鲁'),('Venezuelan','委内瑞拉'),('Brazilian','巴西'),('Mexican','墨西哥'),
 ('Cuban','古巴'),('Fijian','斐济'),('Mozambican','莫桑比克'),('Angolan','安哥拉'),
 ('Zambian','赞比亚'),('Namibian','纳米比亚'),('Rwandan','卢旺达'),('Jamaican','牙买加'),
 ('Haitian','海地'),('Lithuanian','立陶宛'),('Latvian','拉脱维亚'),('Estonian','爱沙尼亚'),
 ('Slovenian','斯洛文尼亚'),('Bosnian','波黑'),('Moldovan','摩尔多瓦'),('Belarusian','白俄罗斯'),
 ('Azerbaijani','阿塞拜疆'),('Maldivian','马尔代夫'),('Bhutanese','不丹'),('Laotian','老挝'),
 ('Ivorian','科特迪瓦'),('Senegalese','塞内加尔'),('Cameroonian','喀麦隆'),('Gabonese','加蓬'),
 ('Sierra Leonean','塞拉利昂'),('Liberian','利比里亚'),('Togolese','多哥'),('Beninese','贝宁'),
 ('Burkinabe','布基纳法索'),('Malian','马里'),('Nigerien','尼日尔'),('Chadian','乍得'),
 ('Guinean','几内亚'),('Congolese','刚果'),('Gambian','冈比亚'),('Eritrean','厄立特里亚'),
 ('Seychellois','塞舌尔'),('Mauritian','毛里求斯'),('Samoan','萨摩亚'),('Tongan','汤加'),
 ('I-Kiribati','基里巴斯'),('Vanuatuan','瓦努阿图'),('Barbadian','巴巴多斯'),
 ('Bahamian','巴哈马'),('Belizean','伯利兹'),('Guyanese','圭亚那'),('Surinamese','苏里南'),
 ('Paraguayan','巴拉圭'),('Uruguayan','乌拉圭'),('Bolivian','玻利维亚'),('Ecuadorian','厄瓜多尔'),
 ('Guatemalan','危地马拉'),('Salvadoran','萨尔瓦多'),('Honduran','洪都拉斯'),
 ('Nicaraguan','尼加拉瓜'),('Costa Rican','哥斯达黎加'),('Panamanian','巴拿马'),
 ('Dominican','多米尼加'),('Puerto Rican','波多黎各'),('Taiwanese','中国台湾'),('Macanese','中国澳门'),
 ('Maltese','马耳他'),('Cypriot','塞浦路斯'),('Montenegrin','黑山'),('Macedonian','北马其顿'),
 ('Albanian','阿尔巴尼亚'),('Kosovar','科索沃'),('Swazi','斯威士兰'),('Lesothoan','莱索托'),
]
NAT_PAT = re.compile(r'\b(' + '|'.join(re.escape(w) for w, _ in sorted(NAT, key=lambda x: -len(x[0]))) + r')\b', re.I)
# 美国州名线索（an Iowa legislator → 美国）
US_STATES = r'Iowa|California|Texas|Florida|New York|Ohio|Michigan|Illinois|Georgia|Virginia|Tennessee|Massachusetts|Colorado|Washington|Arizona|Indiana|Maryland|Wisconsin|Missouri|Minnesota|New Jersey|North Carolina|South Carolina|Alabama|Louisiana|Kentucky|Oregon|Oklahoma|Connecticut|Utah|Nevada|Kansas|Arkansas|Mississippi|Nebraska|Idaho|Montana|Rhode Island|Hawaii|Alaska|Maine|New Hampshire|Vermont|Delaware|West Virginia|Wyoming|South Dakota|North Dakota|New Mexico'
US_PAT = re.compile(r'\b(' + US_STATES + r')\b', re.I)

def load(path):
    s = path.read_text(encoding='utf-8')
    return json.JSONDecoder().raw_decode(s[s.index('{'):])[0]

def fetch(slug, retry=3):
    url = API + '?' + urllib.parse.urlencode({'slug': slug, '_fields': 'slug,content,date,link', 'per_page': 1})
    for i in range(retry):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=30) as resp:
                d = json.load(resp)
                return d[0] if d else None
        except Exception:
            if i < retry - 1:
                time.sleep(1.5 * (i + 1))
    return None

def plain(html_text):
    t = html.unescape(re.sub(r'<[^>]+>', ' ', html_text or ''))
    return re.sub(r'\s+', ' ', t).strip()

def extract(text):
    """返回 (age, country, evidence_age, evidence_country)"""
    age = None; ev_age = ''
    m = re.search(r'\baged\s+(\d{1,3})\b', text, re.I)
    if not m:
        m = re.search(r'\bat the age of\s+(\d{1,3})\b', text, re.I)
    if m:
        a = int(m.group(1))
        if 1 <= a <= 120:
            age = a; ev_age = m.group(0)
    country = None; ev_country = ''
    # 只从正文前 300 字提取（首段是本人介绍，后文可能是其他人）
    head = text[:300]
    # 去 "X-born Y" 修饰
    head2 = re.sub(r'\b(' + '|'.join(re.escape(w) for w, _ in NAT) + r')-born\s+', '', head, flags=re.I)
    m = NAT_PAT.search(head2)
    if m:
        country = next(cc for w, cc in NAT if w.lower() == m.group(1).lower())
        ev_country = head2[max(0, m.start()-30):m.end()+40].strip()
    elif US_PAT.search(head):
        country = '美国'
        ev_country = head[max(0, US_PAT.search(head).start()-30):US_PAT.search(head).end()+40].strip()
    return age, country, ev_age, ev_country

def main():
    d = load(DEATHS)
    cols, rows = d['cols'], d['rows']
    I = {k: i for i, k in enumerate(cols)}
    needs = {}
    for x in rows:
        miss_c = not x[I['country']]
        miss_a = not x[I['age']] or not isinstance(x[I['age']], int)
        if miss_c or miss_a:
            needs[x[I['id']]] = {'name': x[I['name']], 'date': x[I['date']],
                                 'miss_c': miss_c, 'miss_a': miss_a,
                                 'old_c': x[I['country']], 'old_a': x[I['age']]}
    print(f'需核验 {len(needs)} 条')

    results = {}
    for idx, (iid, info) in enumerate(needs.items(), 1):
        slug = iid.split('-', 1)[1] if '-' in iid else ''
        post = fetch(slug)
        if post:
            text = plain(post['content']['rendered'])
            age, country, ev_age, ev_country = extract(text)
            results[iid] = {**info, 'found': True, 'new_age': age, 'new_country': country,
                            'ev_age': ev_age, 'ev_country': ev_country, 'text_head': text[:400],
                            'link': post.get('link', '')}
        else:
            results[iid] = {**info, 'found': False}
        if idx % 50 == 0 or idx == len(needs):
            print(f'  进度 {idx}/{len(needs)}', flush=True)

    found = sum(1 for v in results.values() if v['found'])
    age_ok = sum(1 for v in results.values() if v.get('new_age') and v['miss_a'])
    ctry_ok = sum(1 for v in results.values() if v.get('new_country') and v['miss_c'])
    print(f'\n找到文章 {found} | 可补年龄 {age_ok} | 可补国别 {ctry_ok}')
    OUT.write_text(json.dumps(results, ensure_ascii=False, indent=1), encoding='utf-8')
    print(f'审核清单: {OUT}')

if __name__ == '__main__':
    main()
