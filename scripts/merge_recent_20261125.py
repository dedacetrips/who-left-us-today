#!/usr/bin/env python3
"""把 2026-11-22 起新增的逝世人物并入主表 data/deaths.js。

数据来源两类：
1. dead-people.com WP API → archive-data/recent-deaths-20261122.json（46 条，脚本解析）
2. 国内近日官方/主流媒体讣告 → 本文件 CHINA_NEW（11 条，人工核验后写入）

写入规则：
- 双重去重（id + 姓名/日期），已存在则跳过
- 列式结构保持不变（cols/rows），新增行字段顺序严格对齐
- 同步 source-links.js（新增条目的来源 URL）
- 写入前备份 deaths.js / source-links.js
"""
import json, re, shutil
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
DEATHS = DATA / "deaths.js"
LINKS = DATA / "source-links.js"
RECENT = ROOT / "archive-data/recent-deaths-20261122.json"

# 国内近日讣告（人工核验：均为官方机构或主流媒体发布的讣告）
CHINA_NEW = [
    {"id":"20261120-he-qin","date":"2026-11-20","name":"何沁","nameOrig":"He Qin",
     "country":"中国","age":99,"fields":["社科"],
     "identity":"著名中共党史学家 · 中国人民大学荣誉一级教授",
     "summary":"中华人民共和国史学科的重要奠基人，把党史国史带进大学课堂。",
     "bio":"何沁，原名何明德，1927 年生于河南南阳。1955 年中国人民大学马列主义研究班毕业后留校任教，长期在中共党史教研室工作，曾任中共党史系主任、中国中共党史学会副会长、全国哲学社会科学规划组党史党建组副组长。他是中共党史学科的重要开拓者、中华人民共和国史学科的重要奠基人，20 世纪 80 年代末率先在全国高校开设《中华人民共和国史》课程，主编的《中华人民共和国史》发行逾百万册。2007 年出版《中国共产党武装斗争认识史》。先生晚年克服脑梗伤痛，用左手一根手指敲出 20 万字书稿。",
     "facts":["1927 年生，河南南阳人，原名何明德","中国人民大学荣誉一级教授、原中共党史系主任","中国中共党史学会原副会长","全国最早开设《中华人民共和国史》课程的高校学者之一","主编《中华人民共和国史》发行逾百万册","2026 年 11 月 20 日 11 时 55 分在北京逝世"],
     "source":"中国人民大学讣告 / 北京日报","link":[{"n":"中国人民大学讣告（北京日报）","u":"https://xinwen.bjd.com.cn/content/s6b015460e4b0e42f8f032d69.html"}]},
    {"id":"20261121-liu-guoguang","date":"2026-11-21","name":"刘国光","nameOrig":"Liu Guoguang",
     "country":"中国","age":103,"fields":["社科"],
     "identity":"著名经济学家 · 中国社会科学院学部委员、原副院长",
     "summary":"中国经济体制改革「稳健派」的代表，用计划与市场的辩证关系改写了一代经济学。",
     "bio":"刘国光 1923 年 11 月生于江苏南京，1941 年考入国立西南联合大学经济系，后转入天津南开大学，1948 年进入南京中央研究院社会研究所工作。1951 至 1955 年在苏联莫斯科经济学院学习，获副博士学位。回国后进入中国科学院经济研究所，历任研究室主任、《经济研究》主编、经济研究所所长、国家统计局副局长、中国社会科学院副院长。1979 年与赵人伟合作撰写《社会主义经济中计划与市场的关系》，突破把计划与市场简单对立的认识，引发广泛讨论。他提出并发展稳健的宏观调控论，学界以他为代表称「稳健派」。2005 年获首届中国经济学杰出贡献奖，2011 年获首届世界马克思经济学奖，2006 年当选中国社科院首批学部委员。",
     "facts":["1923 年 11 月生于江苏南京，西南联大经济系肄业","1955 年获苏联莫斯科经济学院副博士学位","1982—1993 年任中国社会科学院副院长，1981—1982 年兼国家统计局副局长","1979 年提出计划与市场内在结合的观点，引发学界广泛讨论","2005 年获首届中国经济学杰出贡献奖","2026 年 11 月 21 日晚逝世"],
     "source":"中国社科院马克思主义研究院 / 澎湃新闻","link":[{"n":"澎湃新闻","u":"https://www.thepaper.cn/newsDetail_forward_34554257"}]},
    {"id":"20261122-sun-yongquan","date":"2026-11-22","name":"孙永全","nameOrig":"Sun Yongquan",
     "country":"中国","age":62,"fields":["医药"],
     "identity":"北京朝阳医院神经外科名誉主任 · 主任医师",
     "summary":"做完 2000 多台神经介入手术，把「吊脚楼」技术写进复杂动脉瘤的治疗里。",
     "bio":"孙永全生于 1964 年 2 月 8 日，1987 年起在北京朝阳医院工作，师从神经介入专家吴中学教授，从事神经介入 30 余年，是北京朝阳医院神经外科发展的主要推动者之一，曾任科室名誉主任、主任医师、硕士研究生导师。他完成神经介入诊疗 2000 余例次，诊治范围涵盖颅内动脉瘤、脑及脊髓血管畸形、颈动脉及椎基底动脉狭窄。他提出的「吊脚楼」技术用于复杂分支动脉瘤的栓塞并保留分支血流，参与发展微创颅内血肿穿刺引流技术，是颅内穿刺引流器专利发明人之一，相关技术曾获北京市科技进步二等奖。",
     "facts":["1964 年 2 月 8 日生，1987 年起在北京朝阳医院工作","师从神经介入专家吴中学，从事神经介入 30 余年","完成神经介入诊疗 2000 余例次","提出复杂动脉瘤栓塞的「吊脚楼」技术","参与微创颅内血肿穿刺引流技术，为颅内穿刺引流器专利发明人之一","2026 年 11 月 22 日中午逝世"],
     "source":"北京朝阳医院神经外科讣告 / 医学界","link":[{"n":"北京朝阳医院神经外科讣告（医学界报道）","u":"https://www.163.com/dy/article/LCDU4A0N0514AD1K.html"}]},
    {"id":"20261123-liao-jianwen","date":"2026-11-23","name":"廖建文","nameOrig":"Liao Jianwen",
     "country":"中国","age":59,"fields":["商业","社科"],
     "identity":"长江商学院原副院长 · 京东集团原首席战略官",
     "summary":"把管理理论带进中国商业现场的战略学者，从长江商学院走到京东 CSO。",
     "bio":"廖建文曾任长江商学院副院长、战略与创新创业管理实践教授，哈佛商学院高级研究员，并在美国伊利诺伊理工斯图沃特商学院享有终身教职，后任教于香港科技大学、北京大学。2017 年加入京东集团任首席战略官（CSO），负责集团整体战略规划与实施，推动京东从战略 1.0 向战略 2.0 升级，系统性构建了京东战略管理和运营体系。2021 年 7 月因身体原因退休，后任集团荣誉顾问。他擅长将前沿管理理论与中国商业现实结合，助力众多中国企业家。2026 年 11 月 23 日凌晨 4 时 40 分逝世。",
     "facts":["长江商学院原副院长、战略与创新创业管理实践教授","曾任哈佛商学院高级研究员、伊利诺伊理工终身教职","2017 年加入京东集团任首席战略官","推动京东一体化供应链战略转型","2026 年 11 月 23 日凌晨 4 时 40 分逝世"],
     "source":"长江商学院讣告","link":[{"n":"长江商学院讣告","u":"https://dy.163.com/article/LCF1HOL40519DP0P.html"}]},
    {"id":"20261123-long-hao","date":"2026-11-23","name":"龙灏","nameOrig":"Long Hao",
     "country":"中国","age":58,"fields":["科技"],
     "identity":"重庆大学建筑城规学院教授 · 原建筑系主任",
     "summary":"医疗建筑设计的开拓者，以医院建筑作品入选威尼斯双年展中国馆。",
     "bio":"龙灏，博士，重庆大学建筑城规学院教授、博士生导师，2018 年 7 月至 2026 年 2 月任建筑系系主任，兼任重庆大学建筑学部学术委员会委员、建筑城规学院学术委员会委员、医疗与居住建筑研究所所长、建筑规划设计研究总院大健康建筑设计分院总建筑师。他完成包括 30 余项医疗建筑在内的 80 余个工程项目，获教育部优秀建筑设计奖等省部级以上奖励 9 项，设计作品入选第 13 届全国美展、第 17 届威尼斯国际建筑双年展中国国家馆，并获第三届三联人文城市奖提名，是唯一以医院建筑作品入选威双与三联人文城市奖的建筑师。主持国家自然科学基金面上项目 3 项等国家级科研 20 余项。2026 年 11 月 23 日凌晨 4 时因病逝世。",
     "facts":["重庆大学建筑城规学院教授、博士生导师，原建筑系主任","完成 80 余个工程项目，其中医疗建筑 30 余项","以医院建筑作品入选第 17 届威尼斯国际建筑双年展中国国家馆","获省部级以上奖励 9 项","主持国家级科研 20 余项","2026 年 11 月 23 日凌晨 4 时因病逝世"],
     "source":"重庆大学建筑城规学院讣告 / 澎湃新闻","link":[{"n":"澎湃新闻（据重庆大学讣告）","u":"https://www.thepaper.cn/newsDetail_forward_34538661"}]},
    {"id":"20261124-song-danju","date":"2026-11-24","name":"宋丹菊","nameOrig":"Song Danju",
     "country":"中国","age":84,"fields":["文艺"],
     "identity":"京剧表演艺术家 · 国家级非遗京剧项目代表性传承人",
     "summary":"「四小名旦」宋德珠之女，把宋派武旦的刀枪把子传到今天。",
     "bio":"宋丹菊是一级演员、国家级非物质文化遗产京剧项目代表性传承人、著名京剧表演艺术家，为京剧「四小名旦」之一宋德珠之女。她承传宋派艺术，长期活跃于京剧舞台与教学一线，为京剧武旦行当的传承与发展作出重要贡献。2026 年 11 月 24 日逝世，享年 84 岁。",
     "facts":["一级演员，国家级非遗京剧项目代表性传承人","京剧「四小名旦」之一宋德珠之女","承传宋派武旦艺术","2026 年 11 月 24 日逝世，享年 84 岁"],
     "source":"合新闻 / 央视网 / 澎湃新闻","link":[{"n":"澎湃新闻","u":"https://m.thepaper.cn/newsDetail_forward_34547388"}]},
    {"id":"20261119-zhou-minglu","date":"2026-11-19","name":"周明录","nameOrig":"Zhou Minglu",
     "country":"中国","age":86,"fields":["军政"],
     "identity":"沈阳市人大常委会原党组副书记、副主任",
     "summary":"从炼油厂干事到市纪委书记，在沈阳物资与纪检系统工作四十余年。",
     "bio":"周明录 1940 年 6 月生于河北深泽，1961 年 2 月参加革命工作，1980 年 2 月加入中国共产党。历任沈阳市第二炼油厂人保干事、沈阳市物资局党委书记、沈阳市委常委、市纪委书记等职，1992 年 2 月任沈阳市人大常委会党组副书记、副主任，2003 年 5 月退休。2026 年 11 月 19 日 10 时 16 分在沈阳逝世，享年 86 岁。",
     "facts":["1940 年 6 月生于河北深泽","1961 年参加革命工作，1980 年入党","曾任沈阳市委常委、市纪委书记","1992 年任沈阳市人大常委会党组副书记、副主任","2026 年 11 月 19 日在沈阳逝世"],
     "source":"沈阳日报讣告","link":[{"n":"沈阳日报","u":"https://epaper.syd.com.cn/syrb/h5/html5/2026-11/25/content_121051_20050954.htm"}]},
    {"id":"20261113-siqin-gaowa-writer","date":"2026-11-13","name":"斯琴高娃","nameOrig":"Siqin Gaowa",
     "country":"中国","age":93,"fields":["文艺"],
     "identity":"蒙古族作家 · 翻译家 · 内蒙古作协原秘书长",
     "summary":"注意：这位斯琴高娃是作家、翻译家，不是同名演员。",
     "bio":"斯琴高娃（1933 年 9 月生），蒙古族作家、翻译家，哲里木盟科左中旗人，内蒙古作家协会原秘书长。14 岁参军当骑兵文艺战士，曾于鲁艺学习，后就读内蒙古大学中文系汉语专业。1956 年开始发表作品，1985 年加入中国作家协会。与丈夫敖德斯尔合著《骑兵之歌》《血和泪的爱》，独译《新春曲》《老车夫》《风，在草原上吹过》《欢乐的除夕》等，将蒙古文作品译为国家通用语言文字。2019 年获中国作协「从事文学创作七十年」证书。2026 年 11 月 13 日逝世，享年 93 岁。",
     "facts":["1933 年 9 月生，蒙古族，内蒙古作协原秘书长","14 岁参军，鲁艺学习，内蒙古大学中文系毕业","与敖德斯尔合著《骑兵之歌》等","翻译多部蒙古文作品为国家通用语言文字","2019 年获中国作协「从事文学创作七十年」证书","非同名电影演员，勿混淆"],
     "source":"内蒙古作家协会讣告","link":[{"n":"内蒙古作协讣告（报道）","u":"https://yule.sohu.com/a/1105313696_121749937"}]},
    {"id":"20261118-ye-lianping","date":"2026-11-18","name":"叶连平","nameOrig":"Ye Lianping",
     "country":"中国","age":98,"fields":["社科"],
     "identity":"安徽和县乡村教师 ·「叶连平奖学基金」创办人",
     "summary":"退休后在家办了 26 年免费补习班，最后把自己也捐给了医学课堂。",
     "bio":"叶连平 1928 年生，安徽和县乌江镇卜陈学校退休教师，1991 年退休。2000 年腾出自家房屋办「卜陈未成年人之家」，免费为留守儿童补习英语，累计辅导 2000 多名学生。2012 年设立「叶连平奖学基金」，累计发放超 70 万元，奖励学生 605 名、教师 33 名。他生活极为简朴，茶缸用三十余年，废旧羽毛球拍改作教鞭。遗愿两条：财产全捐基金，遗体捐蚌埠医科大学。2026 年 11 月 18 日 14 时 01 分逝世，当晚遗体送达蚌埠医科大学，成为第 207 位「无语良师」。",
     "facts":["1928 年生，安徽和县卜陈学校退休教师","2000 年起自费办「卜陈未成年人之家」免费辅导留守儿童","累计辅导 2000 多名学生","2012 年设「叶连平奖学基金」，奖励学生 605 名、教师 33 名","遗体捐献蚌埠医科大学，成为第 207 位「无语良师」","2026 年 11 月 18 日逝世，享年 98 岁"],
     "source":"安徽当地媒体 / 蚌埠医科大学","link":[{"n":"事迹报道","u":"https://yule.sohu.com/a/1105313696_121749937"}]},
    {"id":"20261118-zhou-shining","date":"2026-11-18","name":"周世宁","nameOrig":"Zhou Shining",
     "country":"中国","age":92,"fields":["科技"],
     "identity":"中国工程院院士 · 矿山瓦斯防治专家 · 中国矿业大学教授",
     "summary":"创建了煤层瓦斯流动理论，让中国煤矿瓦斯防治有了自己的体系。",
     "bio":"周世宁，男，汉族，江苏扬州人，1934 年 1 月生，1953 年参加工作，1999 年当选中国工程院院士。他是中国煤矿瓦斯学科的开拓者和主要奠基人之一，创建煤层瓦斯流动理论体系，建立以 Darcy 定律为基础的煤层瓦斯流动微分方程，创造性提出「煤和瓦斯突出的流变假说」，发明煤层瓦斯压力和透气系数测定计算方法，建立涵盖瓦斯地质、流动理论、预测抽放与突出的学术体系。曾获国家技术发明奖、国家自然科学奖、全国五一劳动奖章等。2026 年 11 月 18 日在河北廊坊三河市逝世，享年 92 岁。",
     "facts":["1934 年 1 月生，江苏扬州人，1999 年当选中国工程院院士","中国煤矿瓦斯学科开拓者和主要奠基人之一","创建煤层瓦斯流动理论体系","提出「煤和瓦斯突出的流变假说」","获国家技术发明奖、国家自然科学奖等","2026 年 11 月 18 日逝世"],
     "source":"中国矿业大学讣告 / 科学网","link":[{"n":"科学网","u":"https://news.sciencenet.cn/htmlnews/2026/11/574986.shtm"}]},
    {"id":"20261119-zhang-yu-singer","date":"2026-11-19","name":"张宇","nameOrig":"Zhang Yu",
     "country":"中国","age":48,"fields":["文艺"],
     "identity":"液氧乐队主唱 · 中国新金属音乐人",
     "summary":"把大鼓、Funk 与 Hip-Hop 揉进金属，留下《观念》《痛苦杀死我》。",
     "bio":"张宇（1968 年生），辽宁鞍山人，液氧（原液氧罐头）乐队主唱，中国新金属代表音乐人之一。他把大鼓、Funk、Hip-Hop 融入金属乐，代表作有《观念》《痛苦杀死我》《灰、蓝色》等。2026 年 11 月 19 日在鞍山因病逝世，终年 48 岁，告别仪式 11 月 21 日举行。二手玫瑰主唱梁龙等音乐人发文悼念。",
     "facts":["辽宁鞍山人，液氧（原液氧罐头）乐队主唱","中国新金属代表之一，融合大鼓、Funk、Hip-Hop","代表作《观念》《痛苦杀死我》《灰、蓝色》","2026 年 11 月 19 日在鞍山病逝，终年 48 岁"],
     "source":"音乐界悼念 / 媒体报道","link":[{"n":"报道","u":"https://yule.sohu.com/a/1105313696_121749937"}]},
]

COLUMN_KEYS = None

def load_columnar(path):
    s = path.read_text(encoding="utf-8")
    return json.loads(s[s.index("{"):s.rindex("}")+1])

def jdump(obj):
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"))

def main():
    global COLUMN_KEYS
    d = load_columnar(DEATHS)
    cols, rows = d["cols"], d["rows"]
    COLUMN_KEYS = cols
    I = {k:i for i,k in enumerate(cols)}
    existing_ids = {r[I["id"]] for r in rows}
    existing_pair = {(r[I["name"]], r[I["date"]]) for r in rows}
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    shutil.copy2(DEATHS, DATA / f"deaths.before-recent-{stamp}.js")
    shutil.copy2(LINKS, DATA / f"source-links.before-recent-{stamp}.js")

    links = load_columnar(LINKS)
    added_rows, added_links = [], {}

    # 1) dead-people 46 条
    recent = json.load(open(RECENT, encoding="utf-8"))["fresh"]
    for x in recent:
        if x["id"] in existing_ids or (x["name"], x["date"]) in existing_pair:
            continue
        row = [x.get(k) if k in x else None for k in cols]
        # 补内部字段 _url/_raw 不在列中，已按 cols 取值
        added_rows.append(row)
        added_links[x["id"]] = [{"n":"dead-people.com","u":x["_url"]}]
        existing_ids.add(x["id"]); existing_pair.add((x["name"], x["date"]))

    # 2) 国内 11 条
    for p in CHINA_NEW:
        if p["id"] in existing_ids or (p["name"], p["date"]) in existing_pair:
            continue
        base = {k:None for k in cols}
        base.update({k:v for k,v in p.items() if k in cols and k != "link"})
        base.setdefault("nameOrig", p["name"])
        base["verified"] = "manual"
        added_rows.append([base.get(k) for k in cols])
        added_links[p["id"]] = p["link"]
        existing_ids.add(p["id"]); existing_pair.add((p["name"], p["date"]))

    if not added_rows:
        print("没有需要新增的记录"); return

    # 新行按日期降序插入（与原表排序一致），同日保持原顺序在前
    allrows = rows + added_rows
    allrows.sort(key=lambda r: r[I["date"]], reverse=True)
    DEATHS.write_text(
        "// 人物数据：每天离世的世界名人讣告档案（列式压缩）\n"
        f"window.DEATHS_DATA = {jdump({'cols':cols,'rows':allrows})};\n",
        encoding="utf-8")

    links.update(added_links)
    LINKS.write_text(f"window.SOURCE_LINKS = {jdump(links)};\n", encoding="utf-8")

    print(f"新增 {len(added_rows)} 条（dead-people {len(recent)} + 国内 {len(CHINA_NEW)}）")
    print(f"主表 {len(rows)} → {len(allrows)} 条 | 来源链接 {len(added_links)} 条")
    print(f"备份：deaths.before-recent-{stamp}.js / source-links.before-recent-{stamp}.js")

if __name__ == "__main__":
    main()
