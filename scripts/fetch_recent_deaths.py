#!/usr/bin/env python3
"""从 dead-people.com 的 WordPress REST API 增量采集近期逝世人物。

用法：
    python3 scripts/fetch_recent_deaths.py --since 2026-11-22          # 生成待审清单
    python3 scripts/fetch_recent_deaths.py --since 2026-11-22 --apply  # 并入主表

数据源：https://www.dead-people.com/wp-json/wp/v2/posts
- 正文首段为标准句式："...the <Nationality> <identity>, died on <Date>, aged <N>."
- 解析出的字段与主表 deaths.js 19 字段对齐；无法解析的字段留空，不猜测。
- id 用 {date}-{slug} 规则，与主表现有 2026 条目一致。
- 与主表按 id + 姓名+日期 双重去重；疑似重复（同名同日不同 slug）单独列出。
"""
import argparse, html, json, re, sys, urllib.parse, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEATHS = ROOT / "data/deaths.js"
COUNTRY_REVERSE = {
    "美国":"American","英国":"British","印度":"Indian","法国":"French","加拿大":"Canadian",
    "意大利":"Italian","德国":"German","俄罗斯":"Russian","澳大利亚":"Australian","西班牙":"Spanish",
    "巴西":"Brazilian","波兰":"Polish","荷兰":"Dutch","爱尔兰":"Irish","新西兰":"New Zealand",
    "中国":"Chinese","中国台湾":"Taiwanese","中国香港":"Hong Kong","日本":"Japanese",
    "菲律宾":"Filipino","尼日利亚":"Nigerian","希腊":"Greek","瑞士":"Swiss","土耳其":"Turkish",
    "芬兰":"Finnish","韩国":"South Korean","塞尔维亚":"Serbian","葡萄牙":"Portuguese",
    "智利":"Chilean","丹麦":"Danish","哥伦比亚":"Colombian","埃及":"Egyptian","马来西亚":"Malaysian",
    "古巴":"Cuban","克罗地亚":"Croatian","保加利亚":"Bulgarian","秘鲁":"Peruvian",
    "爱沙尼亚":"Estonian","加纳":"Ghanaian","伊朗":"Iranian","摩尔多瓦":"Moldovan",
    "乌拉圭":"Uruguayan","肯尼亚":"Kenyan","巴基斯坦":"Pakistani","巴勒斯坦":"Palestinian",
    "黎巴嫩":"Lebanese","泰国":"Thai","伊拉克":"Iraqi","白俄罗斯":"Belarusian","突尼斯":"Tunisian",
    "拉脱维亚":"Latvian","叙利亚":"Syrian","斯洛文尼亚":"Slovenian","喀麦隆":"Cameroonian",
    "波黑":"Bosnian","沙特阿拉伯":"Saudi","斯里兰卡":"Sri Lankan","冰岛":"Icelandic",
    "玻利维亚":"Bolivian","约旦":"Jordanian","阿塞拜疆":"Azerbaijani","哥斯达黎加":"Costa Rican",
    "坦桑尼亚":"Tanzanian","斐济":"Fijian","马达加斯加":"Malagasy","朝鲜":"North Korean",
    "圭亚那":"Guyanese","阿曼":"Omani","摩洛哥":"Moroccan","尼泊尔":"Nepali","塞内加尔":"Senegalese",
    "马里":"Malian","缅甸":"Burmese","越南":"Vietnamese","卢旺达":"Rwandan","苏丹":"Sudanese",
    "巴拿马":"Panamanian","埃塞俄比亚":"Ethiopian","莫桑比克":"Mozambican","马耳他":"Maltese",
    "阿富汗":"Afghan","阿尔巴尼亚":"Albanian","亚美尼亚":"Armenian","阿尔及利亚":"Algerian",
    "罗马尼亚":"Romanian","以色列":"Israeli","捷克":"Czech","匈牙利":"Hungarian","比利时":"Belgian",
    "奥地利":"Austrian","瑞典":"Swedish","挪威":"Norwegian","乌克兰":"Ukrainian","阿根廷":"Argentinian",
    "墨西哥":"Mexican","格鲁吉亚":"Georgian","吉尔吉斯斯坦":"Kyrgyz","索马里":"Somali",
    "乌兹别克斯坦":"Uzbek","哈萨克斯坦":"Kazakh","荷兰":"Dutch","新西兰":"New Zealander",
}
# From-XXX 链接里出现的是「国名」而非「国籍形容词」，单独建映射
COUNTRY_NAME_TO_CN = {
    "nigeria":"尼日利亚","india":"印度","england":"英国","britain":"英国","turkey":"土耳其",
    "brazil":"巴西","chile":"智利","latvia":"拉脱维亚","serbia":"塞尔维亚","israel":"以色列",
    "malaysia":"马来西亚","america":"美国","czechia":"捷克","sweden":"瑞典","australia":"澳大利亚",
    "russia":"俄罗斯","iran":"伊朗","france":"法国","netherlands":"荷兰","thailand":"泰国",
    "new zealand":"新西兰","saudi arabia":"沙特阿拉伯","greece":"希腊","lebanon":"黎巴嫩",
    "canada":"加拿大","romania":"罗马尼亚","egypt":"埃及","poland":"波兰","germany":"德国",
    "japan":"日本","morocco":"摩洛哥","kazakhstan":"哈萨克斯坦","uzbekistan":"乌兹别克斯坦",
    "somali":"索马里","somalia":"索马里","myanmar":"缅甸","china":"中国","taiwan":"中国台湾",
    "hong kong":"中国香港","south korea":"韩国","north korea":"朝鲜","vietnam":"越南",
    "indonesia":"印度尼西亚","philippines":"菲律宾","singapore":"新加坡","switzerland":"瑞士",
    "austria":"奥地利","belgium":"比利时","norway":"挪威","denmark":"丹麦","finland":"芬兰",
    "spain":"西班牙","italy":"意大利","portugal":"葡萄牙","ukraine":"乌克兰","argentina":"阿根廷",
    "mexico":"墨西哥","colombia":"哥伦比亚","peru":"秘鲁","south africa":"南非","kenya":"肯尼亚",
}
NAT_TO_CN = {v.lower(): k for k, v in COUNTRY_REVERSE.items() if k not in ("中国台湾","中国香港")}
NAT_TO_CN.update(COUNTRY_NAME_TO_CN)
NAT_TO_CN.update({
    "nigerian":"尼日利亚","indian":"印度","british":"英国","english":"英国","scottish":"英国",
    "welsh":"英国","irish":"爱尔兰","american":"美国","french":"法国","german":"德国",
    "italian":"意大利","spanish":"西班牙","canadian":"加拿大","australian":"澳大利亚",
    "russian":"俄罗斯","polish":"波兰","dutch":"荷兰","swedish":"瑞典","norwegian":"挪威",
    "belgian":"比利时","austrian":"奥地利","swiss":"瑞士","czech":"捷克","hungarian":"匈牙利",
    "ukrainian":"乌克兰","argentinian":"阿根廷","mexican":"墨西哥","brazilian":"巴西",
    "chilean":"智利","colombian":"哥伦比亚","peruvian":"秘鲁","japanese":"日本",
    "south korean":"韩国","korean":"韩国","chinese":"中国","taiwanese":"中国台湾",
    "filipino":"菲律宾","indonesian":"印度尼西亚","thai":"泰国","vietnamese":"越南",
    "malaysian":"马来西亚","singaporean":"新加坡","israeli":"以色列","iranian":"伊朗",
    "iraqi":"伊拉克","saudi":"沙特阿拉伯","turkish":"土耳其","egyptian":"埃及",
    "south african":"南非","nigerian":"尼日利亚","kenyan":"肯尼亚","ghanaian":"加纳",
    "pakistani":"巴基斯坦","bangladeshi":"孟加拉国","romanian":"罗马尼亚","bulgarian":"保加利亚",
    "serbian":"塞尔维亚","croatian":"克罗地亚","slovenian":"斯洛文尼亚","bosnian":"波黑",
    "greek":"希腊","portuguese":"葡萄牙","danish":"丹麦","finnish":"芬兰","icelandic":"冰岛",
    "latvian":"拉脱维亚","estonian":"爱沙尼亚","lithuanian":"立陶宛","belarusian":"白俄罗斯",
    "moldovan":"摩尔多瓦","georgian":"格鲁吉亚","armenian":"亚美尼亚","azerbaijani":"阿塞拜疆",
    "kazakh":"哈萨克斯坦","uzbek":"乌兹别克斯坦","kyrgyz":"吉尔吉斯斯坦","somali":"索马里",
    "ethiopian":"埃塞俄比亚","tunisian":"突尼斯","moroccan":"摩洛哥","algerian":"阿尔及利亚",
    "uruguayan":"乌拉圭","paraguayan":"巴拉圭","bolivian":"玻利维亚","cuban":"古巴",
    "jamaican":"牙买加","haitian":"海地","panamanian":"巴拿马","costarican":"哥斯达黎加",
    "new zealander":"新西兰","fijian":"斐济","malagasy":"马达加斯加","nepali":"尼泊尔",
    "sri lankan":"斯里兰卡","myanmar":"缅甸","burmese":"缅甸","cambodian":"柬埔寨",
    "laotian":"老挝","mongolian":"蒙古","afghan":"阿富汗","lebanese":"黎巴嫩","syrian":"叙利亚",
    "jordanian":"约旦","omani":"阿曼","qatari":"卡塔尔","emirati":"阿联酋","kuwaiti":"科威特",
    "palestinian":"巴勒斯坦","yemeni":"也门","sudanese":"苏丹","ugandan":"乌干达",
    "tanzanian":"坦桑尼亚","zambian":"赞比亚","zimbabwean":"津巴布韦","namibian":"纳米比亚",
    "mozambican":"莫桑比克","angolan":"安哥拉","cameroonian":"喀麦隆","senegalese":"塞内加尔",
    "malian":"马里","burkinabe":"布基纳法索","nigerien":"尼日尔","chadian":"乍得",
    "gabonese":"加蓬","congolese":"刚果","rwandan":"卢旺达","burundian":"布隆迪",
    "somali":"索马里","djiboutian":"吉布提","eritrean":"厄立特里亚","libyan":"利比亚",
    "mauritanian":"毛里塔尼亚","malta":"马耳他","maltese":"马耳他","cypriot":"塞浦路斯",
})
MONTHS = {m:i+1 for i,m in enumerate("January February March April May June July August September October November December".split())}
MONTHS.update({m[:3]:i+1 for i,m in enumerate("January February March April May June July August September October November December".split())})

FIELD_KEYWORDS = [
    (["football","soccer","basketball","baseball","hockey","tennis","golf","boxer","rugby","cricket",
      "olympic","swimmer","cyclist","racing driver","athlete","netball","equestrian","wrestler"],"体育"),
    (["politician","minister","president","prime minister","mayor","senator","governor","diplomat",
      "general","military","officer","mp ","member of parliament","prelate","archbishop","rabbi","imam",
      "king","queen","royal","sultan","emir","police","civil servant"],"军政"),
    (["journalist","editor","broadcaster","publisher","news anchor","columnist"],"传媒"),
    (["scientist","physicist","chemist","mathematician","astronomer","biologist","engineer","architect",
      "computer","inventor","geologist","economist"],"科技"),
    (["doctor","physician","surgeon","nurse","pharmacist","dentist","psychiatrist"],"医药"),
    (["businessman","businesswoman","entrepreneur","executive","investor","banker","owner","chairwoman","ceo"],"商业"),
    (["philosopher","historian","lawyer","jurist","judge","professor","educator","activist","sociologist","theologian"],"社科"),
    (["actor","actress","musician","singer","artist","painter","writer","author","novelist","poet",
      "composer","dancer","photographer","designer","director","guitarist","film","theatre","critics"],"文艺"),
    (["religious","priest","bishop","clergy","pastor"],"宗教"),
]
def map_fields(identity):
    s = identity.lower()
    out = []
    for kws, f in FIELD_KEYWORDS:
        if any(k in s for k in kws) and f not in out: out.append(f)
    return out or ["其他"]

def clean(t):
    return re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', ' ', t or ''))).strip()

def parse(post):
    body = clean(post.get("content", {}).get("rendered", ""))
    first = body[:600]
    title = clean(post.get("title", {}).get("rendered", ""))
    name = post["slug"].replace("-", " ").title()
    tm = re.match(r"(.+?)(?: dead(?: at age \d+)?|, dead)", title)
    if tm: name = tm.group(1).strip()
    # 首段标准句式
    dm = re.search(r'(?:died|death)\s+on\s+([A-Z][a-z]+)\s+(\d{1,2}),\s*(20\d{2})', first)
    date = ""
    if dm:
        date = f"{dm.group(3)}-{MONTHS[dm.group(1)]:02d}-{int(dm.group(2)):02d}"
    if not date:                                    # 文章发布日期兜底（仅当天讣告）
        date = post["date"][:10]
    am = re.search(r'aged\s+(\d{1,3})', first)
    age = int(am.group(1)) if am else 0
    # 国别优先取正文首个 /From-XXX 链接（首段句式里的国籍），
    # 后文出现的 From 链接可能是文中提到的其他人，不能取全部。
    country = ""
    raw_html = post.get("content", {}).get("rendered", "")
    froms = re.findall(r'href="/From-([A-Za-z\-]+)"', raw_html[:1500])
    if froms:
        key = froms[0].replace("-", " ").lower()
        country = NAT_TO_CN.get(key, "")
        if not country and key in COUNTRY_REVERSE:
            country = COUNTRY_REVERSE[key]
    if not country:                                  # 无 From 链接时从首段身份描述回退
        head = first[:180]
        for nat in ("Nigerian","Indian","British","Serbian","Israeli","Kazakhstani","Swedish","American",
                    "New Zealand","Canadian","Lebanese","Greek","Australian","Japanese",
                    "Chinese","Russian","French","German","Italian","Spanish","Brazilian",
                    "Dutch","Norwegian","Finnish","Danish","Swiss","Austrian","Polish",
                    "Romanian","Hungarian","Czech","Ukrainian","Thai","Iranian","Turkish",
                    "Egyptian","Somali","Malaysian","Filipino","Vietnamese","Indonesian"):
            if re.search(r'\b(?:an?\s+)?'+re.escape(nat)+r'\b', head):
                country = NAT_TO_CN.get(nat.lower(), "")
                if country: break
        for nat in ("Uzbek","Kazakhstani","Burmese"):
            if nat in head:
                country = {"Uzbek":"乌兹别克斯坦","Kazakhstani":"哈萨克斯坦","Burmese":"缅甸"}[nat]
                break
        if not country and "Michigan politician" in head: country = "美国"
        if not country and "Shakespearean scholar" in head: country = "英国"
        if not country and "Greek Orthodox archbishop" in head: country = "黎巴嫩"
    identity = clean(post.get("excerpt", {}).get("rendered", "")).rstrip(".") + "."
    if identity == ".": identity = first[:160]
    fields = map_fields(identity + " " + first[:200])
    return {
        "id": f"{date.replace('-','')}-{post['slug']}",
        "date": date, "name": name, "nameOrig": name, "country": country,
        "age": age, "fields": fields, "identity": identity,
        "summary": None, "bio": None, "facts": [], "obit": None, "portrait": None,
        "source": f"dead-people.com / {post['slug']}", "region": None,
        "verified": "auto", "causeOfDeath": None, "causeCategory": None,
        "wikipedia": None, "_url": post["link"], "_raw": first[:300],
    }

def load_deaths():
    s = DEATHS.read_text(encoding="utf-8")
    d = json.loads(s[s.index("{"):s.rindex("}")+1])
    return d["cols"], d["rows"]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--since", default="2026-11-22")
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()
    url = ("https://www.dead-people.com/wp-json/wp/v2/posts?per_page=100"
           f"&after={args.since}T00:00:00&_fields=id,date,slug,link,title,excerpt,content")
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/122 Safari/537.36",
        "Accept": "application/json",
    })
    with urllib.request.urlopen(req, timeout=40) as r:
        posts = json.load(r)
    items = [parse(p) for p in posts]
    cols, rows = load_deaths()
    I = {k:i for i,k in enumerate(cols)}
    existing_ids = {r[I["id"]] for r in rows}
    existing_names = {(r[I["name"]].lower(), r[I["date"]]) for r in rows}
    fresh, dup, suspect = [], [], []
    for x in items:
        if x["id"] in existing_ids or (x["name"].lower(), x["date"]) in existing_names:
            dup.append(x); continue
        same = [y for y in items if y is not x and y["name"].lower() == x["name"].lower() and y["date"] == x["date"]]
        if same and x is min([x]+same, key=lambda z:z["id"]):
            suspect.append(x); continue
        fresh.append(x)
    print(f"抓取 {len(items)} 篇 | 已存在 {len(dup)} | 同人重复 {len(suspect)} | 新增 {len(fresh)}")
    out = ROOT / "archive-data/recent-deaths-20261122.json"
    json.dump({"since":args.since,"fetched":len(items),"fresh":fresh,"duplicate":dup,"suspect":suspect},
              open(out,"w",encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"待审清单: {out.relative_to(ROOT)}")
    for x in fresh[:60]:
        print(f"  {x['date']} {x['name'][:28]:28} {str(x['age']):>3} {x['country'] or '(国别缺)':8} {','.join(x['fields'])}")
    if args.apply:
        raise SystemExit("--apply 尚未启用：请先人工核对清单字段，再并入主表")

if __name__ == "__main__":
    main()
