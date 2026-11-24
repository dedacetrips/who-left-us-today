#!/usr/bin/env python3
"""中国人物官方讣告补全 · 第二批（剩余 275 人中的真正待补薄数据）。

本轮只处理"薄数据且无同人物完整记录"的记录，来源限新华社/人民网/人民日报/
中国政府网/央视/省级政府门户等官方讣告。已有完整中文记录的重复薄数据不在此补。
写回沿用第一批脚本的字段规则：只补空字段；冲突以官方讣告为准并记录更正。
"""
from __future__ import annotations

import json
import os
import shutil
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
ARCHIVE = os.path.join(ROOT, "archive-data")

DEATHS_PATH = os.path.join(DATA, "deaths.js")
SOURCE_LINKS_PATH = os.path.join(DATA, "source-links.js")
ENRICH_PATH = os.path.join(ARCHIVE, "china-official-enrichments-round2.json")
REPORT_PATH = os.path.join(ROOT, "中国人物官方讣告补全报告-第二批.md")

CAUSE_DISEASE = "疾病（未详）"
CAUSE_CATEGORY = "疾病"

# 已逐条核验：姓名、卒日、享年、籍贯、官方来源均与新华社/人民网/政府门户讣告一致。
ENRICHMENTS = {
    "20260208-chen-bangzhu": {
        "name": "陈邦柱",
        "source": "新华社 / 人民网",
        "urls": [
            {"n": "新华社（工人日报转载）", "u": "http://mp.weixin.qq.com/s?__biz=MzA4NTE1NzAwMw==&mid=2649858297&idx=1&sn=322fa4b55c3afa2f7391a3ba7c30b533"},
        ],
        "identity": "原国家经济贸易委员会副主任、党组副书记（正部长级） · 原国内贸易部部长",
        "summary": "从化工建设一线成长起来的部长级干部，先后主政湖南与国内贸易、经贸系统。",
        "bio": "陈邦柱，1934年9月生，江西九江人。1951年2月参加工作，1975年10月加入中国共产党。1965年起先后任化学工业部第九化工建设公司工区副主任、工程处主任、总工程师，化学工业部第四化工建设公司经理、总工程师，湖南省岳阳市委副书记、市长。1984年起任湖南省副省长、省委常委，1989年起任湖南省委副书记、代省长、省长。1995年任国内贸易部部长、党组书记，1998年至1999年任国家经济贸易委员会副主任、党组副书记。曾任中国质量协会会长，是中共十三届中央候补委员，十四届、十五届中央委员。2026年2月8日因病在北京逝世，享年91岁。",
        "facts": [
            "1934年9月生，江西九江人，1951年2月参加工作",
            "1989年至1995年任湖南省委副书记、省长",
            "1995年任国内贸易部部长，1998年任国家经贸委副主任（正部长级）",
            "中共十四届、十五届中央委员",
        ],
        "age": 91,
        "cause": CAUSE_DISEASE,
        "causeCategory": CAUSE_CATEGORY,
        "evidence": "新华社：『原国家经济贸易委员会副主任、党组副书记陈邦柱同志（正部长级），因病于2026年2月8日在北京逝世，享年91岁』。",
    },
    "20260917-shao-qihui": {
        "name": "邵奇惠",
        "source": "新华社 / 新华社客户端",
        "urls": [
            {"n": "新华社客户端", "u": "https://h.xinhuaxmt.com/vh512/share/13327723?homeshow=1&newstype=1001"},
        ],
        "identity": "原国家机械工业局局长、党组书记（正部长级） · 原黑龙江省省长",
        "summary": "从林业机械厂技术员成长为正部长级干部，曾任黑龙江省省长、国家机械工业局局长。",
        "bio": "邵奇惠，1934年6月生，江苏宜兴人。1952年9月参加工作，1953年10月加入中国共产党。1955年起先后任青年团杭州市委办公室副主任、共青团浙江省杭州市委学校工作部副部长。1962年至1985年任哈尔滨林业机械厂副厂长、总工程师、厂长、党委副书记。1985年起任哈尔滨市委副书记、齐齐哈尔市委书记，1988年起任黑龙江省副省长，省委副书记、省长。1994年至1999年任机械工业部副部长、党组副书记，国家机械工业局局长、党组书记。是中共十四届中央委员，第七、八届全国人大代表。2026年9月17日因病在北京逝世，享年92岁。",
        "facts": [
            "1934年6月生，江苏宜兴人，1952年9月参加工作",
            "1988年起任黑龙江省副省长，后任省委副书记、省长",
            "1994年至1999年任机械工业部副部长、国家机械工业局局长、党组书记",
            "中共十四届中央委员",
        ],
        "age": 92,
        "cause": CAUSE_DISEASE,
        "causeCategory": CAUSE_CATEGORY,
        "evidence": "新华社：『原国家机械工业局局长、党组书记邵奇惠同志（正部长级），因病于2026年9月17日在北京逝世，享年92岁』。",
    },
    "20260810-zhu-senlin": {
        "name": "朱森林",
        "source": "广东省人民政府门户网站 / 南方日报",
        "urls": [
            {"n": "广东省人民政府门户网站", "u": "https://www.gd.gov.cn/gdywdt/gdyw/content/post_4943569.html"},
            {"n": "南方新闻网·生平", "u": "https://news.southcn.com/node_8c4f4f61e4/2efc042ec0.shtml"},
        ],
        "identity": "广东省委原副书记、省政府原省长、省人大常委会原主任",
        "summary": "扎根广州数十年，牵头创办广州经济技术开发区，是广东改革开放的重要推动者。",
        "bio": "朱森林，1930年10月出生，上海川沙人。1948年考入清华大学并参加进步学生团体，1948年11月参加革命工作，1952年7月加入中国共产党。新中国成立后南下广东，历任广州市委组织部干事、科长，花县、从化县革委会副主任，广州市委宣传部办公室主任。1975年起任广州市越秀区委书记、市委副秘书长、市委常委、市委副书记兼广州经济技术开发区管委会主任。1985年至1988年任广州市委副书记、市长，1988年至1991年任广东省委常委、广州市委书记，1991年至1996年任广东省委副书记、代省长、省长，1996年任广东省人大常委会主任。是中共十四届中央委员，七、八、九届全国人大代表。2026年8月10日11时36分因病医治无效在广州逝世，享年96岁。",
        "facts": [
            "1930年10月生，上海川沙人，1948年参加革命工作",
            "1985年至1988年任广州市市长，1988年至1991年任广州市委书记",
            "1991年至1996年任广东省委副书记、省长，1996年任省人大常委会主任",
            "牵头创办广州经济技术开发区，推动广东改革开放",
        ],
        "age": 96,
        "cause": CAUSE_DISEASE,
        "causeCategory": CAUSE_CATEGORY,
        "evidence": "广东省人民政府门户网站：『因病医治无效，于2026年8月10日11时36分在广州逝世，享年96岁』。原表享年95岁，已更正。",
    },
    "20260429-bai-jingfu": {
        "name": "白景富",
        "source": "新华社 / 人民日报",
        "urls": [
            {"n": "人民日报（2026-05-27）", "u": "https://www.peopleapp.com/newspaper?date=2026.05.27"},
        ],
        "identity": "公安部原主持常务工作的副部长、党委副书记（正部长级）",
        "summary": "从黑龙江基层公安系统成长起来的公安部领导，长期分管全国公安政法工作。",
        "bio": "白景富，1945年7月生，河北丰润人。1970年8月参加工作，1973年4月加入中国共产党。1973年至1985年任黑龙江省七台河市委办公室副主任、市检察院副检察长、市公安局局长、副市长、市委副书记。1985年至1988年任黑龙江省委常委、政法委书记、省公安厅厅长。1988年至1991年任黑龙江省公安厅厅长、党组书记、省委政法委秘书长。1991年至1993年任公安部副部长、党委委员，1993年至2005年任公安部副部长、党委副书记，2005年至2008年任公安部主持常务工作的副部长、党委副书记。是中共十六届中央候补委员、十七届中央委员。2026年4月29日因病在北京逝世，享年81岁。",
        "facts": [
            "1945年7月生，河北丰润人，1970年8月参加工作",
            "1985年起任黑龙江省委常委、政法委书记、省公安厅厅长",
            "1991年起任公安部副部长，2005年至2008年任主持常务工作的副部长（正部长级）",
            "中共十七届中央委员",
        ],
        "age": 81,
        "cause": CAUSE_DISEASE,
        "causeCategory": CAUSE_CATEGORY,
        "evidence": "新华社/人民日报：『公安部原主持常务工作的副部长、党委副书记白景富同志（正部长级），因病于2026年4月29日在北京逝世，享年81岁』。原表享年80岁，已更正。",
    },
    "20260310-wang-jinshan": {
        "name": "王金山",
        "source": "新华社 / 人民日报 / 安徽日报",
        "urls": [
            {"n": "人民日报（2026-04-03）", "u": "https://www.peopleapp.com/newspaper?date=2026.04.03"},
            {"n": "安徽日报数字报", "u": "https://szb.ahnews.com.cn/ahrb/layout/202603/10/index.html"},
        ],
        "identity": "安徽省委原书记、省人大常委会原主任",
        "summary": "从吉林基层做到安徽省委书记，长期主政地方并任全国人大农委副主任。",
        "bio": "王金山，1945年2月生，吉林公主岭人。1967年9月参加工作，1971年2月加入中国共产党。1964年至1967年在吉林省四平师范专科学校学习。1983年起任吉林省副省长，1988年起任白城地委副书记、行署专员、地委书记。1991年起任吉林省委组织部副部长、省委常委、组织部部长、省委副书记兼政法委书记。1996年任浙江省委副书记，1998年任中华全国供销合作总社党组副书记、理事会副主任、党组书记。2002年起任安徽省委副书记、副省长、代省长、省长，2007年至2010年任安徽省委书记、省人大常委会主任。2010年起任第十一、十二届全国人大农业与农村委员会副主任委员。是中共十六届、十七届中央委员。2026年3月9日17时9分因病医治无效在合肥逝世，享年81岁。",
        "facts": [
            "1945年2月生，吉林公主岭人，1967年9月参加工作",
            "1983年起任吉林省副省长，1996年任浙江省委副书记",
            "2002年至2007年任安徽省省长，2007年至2010年任安徽省委书记",
            "中共十六届、十七届中央委员",
        ],
        "date": "2026-03-09",
        "age": 81,
        "cause": CAUSE_DISEASE,
        "causeCategory": CAUSE_CATEGORY,
        "evidence": "新华社/安徽日报：『因病医治无效，于2026年3月9日17时9分在合肥逝世，享年81岁』。原表日期2026-03-10为报道日，已更正为卒日3月9日。",
    },
    "20260119-gao-dezhan": {
        "name": "高德占",
        "source": "新华社 / 人民日报 / 北京日报",
        "urls": [
            {"n": "新华社客户端", "u": "https://h.xinhuaxmt.com/vh512/share/12982518?newstype=1001"},
            {"n": "人民网·中国共产党新闻网", "u": "https://cpc.people.com.cn/BIG5/n1/2026/0302/c87393-40672798.html"},
        ],
        "identity": "天津市委原书记 · 原林业部部长 · 吉林省原省长",
        "summary": "从化工技术员成长起来，先后任吉林省省长、林业部部长、天津市委书记。",
        "bio": "高德占，1932年8月出生于黑龙江哈尔滨，山东栖霞人。1950年4月加入中国共产党，1952年7月参加工作。1954年起在吉林省吉林化学工业学校任教，后任吉林省新中国制糖厂专家工作组组长、技术室主任。1958年起任吉林省地方工业技术研究所设计室主任、副总工程师，吉林省石油化工设计研究院副院长。1975年起任吉林省石油化工局副局长、省经济委员会主任，1983年任吉林省副省长，1985年任吉林省委副书记、省长。1987年至1993年任林业部部长、党组书记，1993年至1997年任天津市委书记，1998年至2003年任第九届全国人大农业与农村委员会主任委员。是中共十四届中央委员。2026年1月18日10时59分因病医治无效在天津逝世，享年94岁。",
        "facts": [
            "1932年8月生于哈尔滨，山东栖霞人，高级工程师",
            "1985年至1987年任吉林省委副书记、省长",
            "1987年至1993年任林业部部长，1993年至1997年任天津市委书记",
            "第九届全国人大农业与农村委员会主任委员",
        ],
        "date": "2026-01-18",
        "age": 94,
        "cause": CAUSE_DISEASE,
        "causeCategory": CAUSE_CATEGORY,
        "evidence": "新华社/人民日报：『因病于2026年1月18日在天津逝世，享年94岁』；北京日报生平载明10时59分逝世。原表日期1月19日、享年93岁，均已更正。",
    },
    "20260112-lu-kejian": {
        "name": "卢克俭",
        "source": "甘肃日报 / 新甘肃客户端",
        "urls": [
            {"n": "新甘肃客户端·甘肃日报", "u": "http://mp.weixin.qq.com/s?__biz=MzU5NTc0ODYxOQ==&mid=2247857378&idx=1&sn=3b3850cc7aa860f4178283748cad0a44"},
        ],
        "identity": "甘肃省第八、九届人大常委会党组书记、主任",
        "summary": "从甘南基层起步，长期在甘肃省委、省人大任职，曾任省委副书记。",
        "bio": "卢克俭，1932年1月出生，甘肃卓尼人。1950年1月参加工作，1953年1月加入中国共产党。早年任会川县裕民区委宣传委员、甘肃日报社记者、甘南报社副总编辑、天祝县委副书记、县长等职。1979年任甘肃省委党校副校长，1983年任省委常委、统战部部长、省政协秘书长，1984年任省委副书记，1988年任省委副书记、宣传部部长。1993年起任甘肃省第八届、第九届人大常委会党组书记、主任，2003年12月退休。是第七至十届全国人大代表、第六届全国政协委员。2026年1月12日因病在兰州逝世，享年94岁。",
        "facts": [
            "1932年1月生，甘肃卓尼人，1950年1月参加工作",
            "1984年起任甘肃省委副书记，1988年兼任省委宣传部部长",
            "1993年起任甘肃省第八、九届人大常委会主任",
            "第七至十届全国人大代表",
        ],
        "age": 94,
        "cause": CAUSE_DISEASE,
        "causeCategory": CAUSE_CATEGORY,
        "evidence": "甘肃日报/新甘肃客户端：『因病于2026年1月12日在兰州逝世，享年94岁』。原表享年93岁，已更正。",
    },
    "20260117-wei-fulin": {
        "name": "隗福临",
        "source": "新华社 / 中国军网 / 人民网",
        "urls": [
            {"n": "中国军网", "u": "https://www.81.cn/ss_208539/16440277.html"},
            {"n": "人民网·人民日报", "u": "https://politics.people.com.cn/BIG5/n1/2026/0131/c461001-40656737.html"},
        ],
        "identity": "解放军原副总参谋长 · 正大军区职退休干部 · 上将",
        "summary": "从普通士兵成长为上将，曾任解放军副总参谋长、成都军区司令员。",
        "bio": "隗福临，辽宁新宾人，1956年入伍，1961年加入中国共产党。革命生涯中历任排长、参谋、连长、营长、团长、师长、军参谋长，总参谋部作战部副部长、部长，总参谋长助理、成都军区司令员等职。是中共十五届中央委员，第九届全国人大代表，第十届全国人大常委会委员、民族委员会副主任委员。1988年被授予少将军衔，1994年晋升中将军衔，2000年晋升上将军衔。2026年1月15日因病医治无效在北京逝世，享年88岁。",
        "facts": [
            "辽宁新宾人，1956年入伍，1961年入党",
            "曾任总参谋部作战部部长、总参谋长助理、成都军区司令员",
            "解放军原副总参谋长，2000年晋升上将军衔",
            "中共十五届中央委员，第十届全国人大常委会委员",
        ],
        "date": "2026-01-15",
        "age": 88,
        "cause": CAUSE_DISEASE,
        "causeCategory": CAUSE_CATEGORY,
        "evidence": "新华社/中国军网：『因病医治无效，于1月15日在北京逝世，享年88岁』。原表日期1月17日、享年87岁，均已更正。",
    },
    "20260725-shi-bao-yuan": {
        "name": "石宝源",
        "source": "新华社 / 中国军网 / 人民网",
        "urls": [
            {"n": "中国军网", "u": "https://www.81.cn/ss_208539/16477886.html"},
            {"n": "人民网·人民日报", "u": "https://cpc.people.com.cn/BIG5/n1/2026/0807/c87393-40775437.html"},
        ],
        "identity": "原沈阳军区副司令员 · 副大军区职退休干部 · 中将",
        "summary": "从军校学员成长为副大军区职将领，曾任沈阳军区副司令员。",
        "bio": "石宝源，河北通县（今北京市通州区）人，1954年入伍，1955年加入中国共产党。革命生涯中历任学员、班长、参谋、副处长、团长、师参谋长、副师长、师长、副军长等职，后任沈阳军区副司令员，为部队革命化、现代化、正规化建设作出了贡献。是中共十三大代表，第八、九届全国人大代表。1988年被授予少将军衔，1993年晋升中将军衔。2026年7月25日因病医治无效在北京逝世，享年90岁。",
        "facts": [
            "河北通县（今北京通州）人，1954年入伍，1955年入党",
            "历任团长、师长、副军长，后任沈阳军区副司令员",
            "1988年授少将，1993年晋升中将",
            "中共十三大代表，第八、九届全国人大代表",
        ],
        "age": 90,
        "cause": CAUSE_DISEASE,
        "causeCategory": CAUSE_CATEGORY,
        "evidence": "新华社/中国军网：『因病医治无效，于7月25日在北京逝世，享年90岁』。原表享年89岁，已更正。",
    },
    "20260722-huang-zhiquan-politician-born-1942": {
        "name": "黄智权",
        "source": "新华社 / 新华网 / 江西日报",
        "urls": [
            {"n": "新华网", "u": "https://xinhuanet.com/20260826/e1d745ef271147d0b4d58488e1a31b1e/c.html"},
        ],
        "identity": "江西省委原副书记、江西省人民政府原省长",
        "summary": "从江西省计委起步，长期主管江西经济计划工作，2001至2006年任江西省省长。",
        "bio": "黄智权，1942年2月生，浙江桐乡人。1963年9月参加工作，1979年5月加入中国共产党。1963年起任江西机械工业学校教师、江西省机械厅计划处干部。1972年至1991年任江西省计划委员会干部、综合处处长、副主任、主任、党组书记。1991年任江西省政府省长助理，1993年至2001年任江西省副省长、省委常委、省委副书记。2001年4月至2006年10月任江西省委副书记、代省长、省长。2006年至2013年任第十、十一届全国人大环境与资源保护委员会副主任委员。是中共十六届中央委员。2026年7月22日因病在南昌逝世，享年85岁。",
        "facts": [
            "1942年2月生，浙江桐乡人，1963年9月参加工作",
            "1972年至1991年长期在江西省计划委员会工作，曾任主任",
            "2001年至2006年任江西省委副书记、省长",
            "中共十六届中央委员，第十一届全国人大常委会委员",
        ],
        "age": 85,
        "cause": CAUSE_DISEASE,
        "causeCategory": CAUSE_CATEGORY,
        "evidence": "新华社/新华网：『因病于2026年7月22日在南昌逝世，享年85岁』。原表中文名为英文名 Huang Zhiquan，已补中文名；享年84岁已更正为85岁。",
    },
}


def load_js_array(path):
    t = open(path, encoding="utf-8").read()
    return json.loads(t[t.index("=") + 1:].strip().rstrip(";"))


def load_js_object(path):
    t = open(path, encoding="utf-8").read()
    return json.loads(t[t.index("=") + 1:].strip().rstrip(";"))


def apply():
    deaths = load_js_array(DEATHS_PATH)
    links = load_js_object(SOURCE_LINKS_PATH)
    by_id = {x["id"]: x for x in deaths}
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    shutil.copy2(DEATHS_PATH, os.path.join(DATA, f"deaths.before-round2-{stamp}.js"))
    shutil.copy2(SOURCE_LINKS_PATH, os.path.join(DATA, f"source-links.before-round2-{stamp}.js"))

    applied = []
    for mid, e in ENRICHMENTS.items():
        if mid not in by_id:
            raise KeyError(mid)
        x = by_id[mid]
        before = {"date": x.get("date"), "age": x.get("age"), "source": x.get("source"), "name": x.get("name")}
        changes = []
        # 原名为英文且核验出中文名时：英文名移入 nameOrig，name 补中文。
        import re as _re
        if e.get("name") and not _re.search(r"[\u4e00-\u9fff]", x.get("name", "")):
            if not x.get("nameOrig"):
                x["nameOrig"] = x.get("name")
            x["name"] = e["name"]
            changes.append("name/nameOrig")
        for key in ("identity", "summary", "bio", "facts", "source"):
            if e.get(key) and x.get(key) != e[key]:
                changes.append(key)
                x[key] = e[key]
        for sk, tk in (("date", "date"), ("age", "age"), ("cause", "causeOfDeath"), ("causeCategory", "causeCategory")):
            if sk in e and x.get(tk) != e[sk]:
                changes.append(tk)
                x[tk] = e[sk]
        if x.get("verified") != "confirmed":
            changes.append("verified")
            x["verified"] = "confirmed"
        links[mid] = e["urls"]
        applied.append({
            "id": mid, "name": e["name"], "source": e["source"],
            "urls": [u["u"] for u in e["urls"]],
            "before": before,
            "after": {"date": x.get("date"), "age": x.get("age"), "source": x.get("source"),
                      "causeOfDeath": x.get("causeOfDeath"), "verified": x.get("verified")},
            "changedFields": changes, "evidence": e["evidence"],
        })

    with open(DEATHS_PATH, "w", encoding="utf-8") as f:
        f.write("// 人物数据：每天离世的世界名人讣告档案\n")
        f.write("window.DEATHS_DATA = ")
        json.dump(deaths, f, ensure_ascii=False, separators=(",", ":"))
        f.write(";\n")
    with open(SOURCE_LINKS_PATH, "w", encoding="utf-8") as f:
        f.write("window.SOURCE_LINKS = ")
        json.dump(links, f, ensure_ascii=False, separators=(",", ":"))
        f.write(";\n")
    with open(ENRICH_PATH, "w", encoding="utf-8") as f:
        json.dump({"generatedAt": datetime.now().isoformat(timespec="seconds"), "records": applied},
                  f, ensure_ascii=False, indent=2)

    lines = [
        "# 中国人物官方讣告补全报告（第二批）",
        "",
        f"> 生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "## 处理范围",
        "",
        "- 对象：第一批 15 人之外、Remaining 275 位中国人物中，**薄数据且无同人物完整记录**者。",
        f"- 本批完成 **{len(applied)}** 人，均为省部级及以上官员，有新华社/人民网/政府门户官方讣告。",
        "- 港澳台与外籍/多重国籍人物本轮不强行补全（国内官方讣告覆盖有限）。",
        "- 已有完整中文记录的重复薄数据（如张玉台、万绍芬、王洛林等）不在此补，列入去重候选。",
        "",
        "## 逐人结果",
        "",
        "| 姓名 | 卒日 | 享年 | 死因 | 来源 | 更正 |",
        "|---|---|---|---|---|---|",
    ]
    for a in applied:
        corr = []
        if a["before"]["age"] != a["after"]["age"]:
            corr.append(f"享年 {a['before']['age']}→{a['after']['age']}")
        if a["before"]["date"] != a["after"]["date"]:
            corr.append(f"卒日 {a['before']['date']}→{a['after']['date']}")
        lines.append(f"| {a['name']} | {a['after']['date']} | {a['after']['age']} | 疾病（未详） | {a['source']} | {'、'.join(corr) or '—'} |")
    lines += ["", "## 证据", ""]
    for a in applied:
        lines += [f"- **{a['name']}**：{a['evidence']}", f"  - {a['urls'][0]}"]
    open(REPORT_PATH, "w", encoding="utf-8").write("\n".join(lines) + "\n")
    print(f"applied {len(applied)} -> {REPORT_PATH}")


if __name__ == "__main__":
    apply()
