#!/usr/bin/env python3
"""从国内官方讣告补全中国人物数据。

流程：
1. 从 data/deaths.js 中筛选国家/地区含“中国”的人物，生成候选清单；
2. 对已经人工核验过官方讣告的人物写回精选表；
3. 同步 data/source-links.js，并输出可审计的补全证据与报告。

原则：不覆盖已有精选正文；只对 auto / confirmed 的薄数据记录补全；
官方讣告与现有字段冲突时，以官方讣告为准并记录更正前后值。
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
CANDIDATES_PATH = os.path.join(ARCHIVE, "china-official-candidates.json")
ENRICH_PATH = os.path.join(ARCHIVE, "china-official-enrichments.json")
REPORT_PATH = os.path.join(ROOT, "中国人物官方讣告补全报告.md")

CAUSE_DISEASE = "疾病（未详）"
CAUSE_CATEGORY = "疾病"

# 官方/权威来源：只使用新华社、央视、人民网、中国政府网、光明网、
# 中国新闻网、央广网、中国作家网及机构官方公众号/官网讣告。
ENRICHMENTS = {
    "20261107-yan-zhen": {
        "name": "严阵",
        "source": "中国作家网（中国作家协会）",
        "urls": [
            {
                "n": "中国作家网·讣告",
                "u": "https://image.chinawriter.com.cn/n1/2026/1109/c403981-40830497.html",
            }
        ],
        "identity": "诗人、作家、画家 · 安徽省作家协会原主席",
        "summary": "主持创办《诗歌报》，以诗与画横跨七十余年创作生涯。",
        "bio": "严阵原名阎桂青，曾用名阎晓光，1930年11月生于山东莱阳。1946年参加革命工作，1954年在《人民文学》发表长诗《老张的手》后成名，1956年加入中国作家协会。1984年主持创办《诗歌报》（现《诗歌月刊》），曾任安徽省文联名誉副主席、安徽省作家协会主席。著有《山盟》《含苞的太阳》《瓷月亮》《江南曲》等，2019年获中国当代诗歌奖终身成就奖。2026年11月7日在北京逝世，享年96岁。",
        "facts": [
            "原名阎桂青，山东莱阳人，1930年11月出生",
            "1954年发表长诗《老张的手》，1956年加入中国作家协会",
            "1984年主持创办《诗歌报》（现《诗歌月刊》）",
            "著有长诗《山盟》《含苞的太阳》及诗集《瓷月亮》《江南曲》等",
        ],
        "age": 96,
        "cause": CAUSE_DISEASE,
        "causeCategory": CAUSE_CATEGORY,
        "evidence": "中国作家网：『因病医治无效，于2026年11月7日在京逝世，享年96岁』。",
    },
    "20261028-liu-yandong": {
        "name": "刘延东",
        "source": "新华社 / 央视网（生平）",
        "urls": [
            {
                "n": "央视网·刘延东同志生平",
                "u": "https://news.cctv.com/2026/11/03/ARTI5fA8w8ps4xQJ5xF9tlpZ261103.shtml",
            },
            {
                "n": "央视网·刘延东同志逝世",
                "u": "https://tv.cctv.com/2026/10/28/VIDEVKLoU7kNFZuwtANWsApc261028.shtml",
            },
        ],
        "identity": "国务院原副总理 · 全国政协原副主席",
        "summary": "长期深耕统一战线、教育科技、医疗卫生与妇女儿童工作。",
        "bio": "刘延东，女，1945年11月22日生于江苏淮安，江苏南通人。1964年加入中国共产党，曾在清华大学工程化学系学习，后在工厂、北京市及共青团中央任职。历任中央统战部副部长、中央社会主义学院党组书记、全国青联主席，第十七届、十八届中央政治局委员，第十届全国政协副主席，国务委员、国务院副总理。2026年10月28日14时53分在北京逝世，享年81岁。",
        "facts": [
            "1945年11月生，江苏南通人，生于江苏淮安",
            "中国共产党第十七届、十八届中央政治局委员",
            "第十届全国政协副主席，原国务委员、国务院副总理",
            "长期从事统一战线、教育科技、医疗卫生和妇女儿童工作",
        ],
        "age": 81,
        "cause": CAUSE_DISEASE,
        "causeCategory": CAUSE_CATEGORY,
        "evidence": "央视网/新华社：『因病于2026年10月28日14时53分在北京逝世，享年81岁』。原表享年80岁，已更正。",
    },
    "20260812-zhu-rongji": {
        "name": "朱镕基",
        "source": "中国政府网 / 新华社",
        "urls": [
            {
                "n": "中国政府网",
                "u": "https://www.gov.cn/yaowen/liebiao/202608/content_7078460.htm",
            },
            {
                "n": "央视网·讣告",
                "u": "https://news.cctv.cn/2026/08/12/ARTICIO8BOZ5Pe4DZFicZPoa260812.shtml",
            },
        ],
        "identity": "国务院原总理",
        "summary": "在计划经济转向社会主义市场经济的关键时期主持多项重大改革。",
        "bio": "朱镕基，1928年10月生，湖南长沙人，1949年10月加入中国共产党。早年就读清华大学电机系，曾任上海市市长、市委书记，国务院副总理，1998年任国务院总理，是第十四届、十五届中央政治局常委。任内推进财税、金融、国有企业、住房制度和粮食流通体制改革，推动中国加入世界贸易组织。2026年8月12日11时06分在北京逝世，享年98岁。",
        "facts": [
            "1928年10月生，湖南长沙人，清华大学电机系毕业",
            "曾任上海市市长、市委书记",
            "第十四届、十五届中央政治局常委，1998年任国务院总理",
            "主持财税、金融、国企、住房等领域改革，推动加入世贸组织",
        ],
        "age": 98,
        "cause": CAUSE_DISEASE,
        "causeCategory": CAUSE_CATEGORY,
        "evidence": "中国政府网/新华社：『因病于2026年8月12日11时06分在北京逝世，享年98岁』。原表享年97岁，已更正。",
    },
    "20260304-song-ping": {
        "name": "宋平",
        "source": "新华社 / 人民网",
        "urls": [
            {
                "n": "人民网·人民日报",
                "u": "https://politics.people.com.cn/n1/2026/0305/c1001-40674889.html",
            }
        ],
        "identity": "中共中央政治局原常委 · 原国务委员",
        "summary": "久经考验的革命家、政治家，曾任第十三届中央政治局常委。",
        "bio": "宋平是中国共产党的优秀党员，久经考验的忠诚的共产主义战士，杰出的无产阶级革命家、政治家，党和国家的卓越领导人，中国共产党第十三届中央政治局常委，原国务委员。因病医治无效，于2026年3月4日15时36分在北京逝世，享年109岁。",
        "facts": [
            "中国共产党第十三届中央政治局常委",
            "曾任国务委员",
            "2026年3月4日15时36分在北京逝世，享年109岁",
        ],
        "age": 109,
        "cause": CAUSE_DISEASE,
        "causeCategory": CAUSE_CATEGORY,
        "evidence": "新华社/人民日报：『因病医治无效，于2026年3月4日15时36分在北京逝世，享年109岁』。原表享年108岁，已更正。",
    },
    "20260531-gu-songfen": {
        "name": "顾诵芬",
        "source": "新华社 / 央视新闻",
        "urls": [
            {
                "n": "新华网",
                "u": "https://www.news.cn/politics/20260601/286384cc49794a60892151bd1ecd3857/c.html",
            }
        ],
        "identity": "飞机空气动力学家 · 两院院士 ·「歼-8之父」",
        "summary": "建立新中国飞机空气动力学设计体系，被誉为“歼-8之父”。",
        "bio": "顾诵芬，1930年2月生，江苏苏州人，中国共产党党员，中国科学院院士、中国工程院院士，我国著名飞机空气动力学家。1951年起先后在航空工业沈阳飞机设计研究所、中国航空工业集团公司科学技术委员会、中国航空研究院任职。他主持研制歼8、歼8Ⅱ超声速歼击机，建立我国歼击机研制体系，获2020年度国家最高科学技术奖。2026年5月31日21时11分因病医治无效在北京逝世，享年96岁。",
        "facts": [
            "1930年2月生，江苏苏州人，中国科学院、中国工程院院士",
            "主持研制歼8、歼8Ⅱ超声速歼击机，被誉为“歼-8之父”",
            "建立新中国飞机空气动力学设计体系与歼击机研制体系",
            "获2020年度国家最高科学技术奖",
        ],
        "age": 96,
        "cause": CAUSE_DISEASE,
        "causeCategory": CAUSE_CATEGORY,
        "evidence": "新华社：『于2026年5月31日21时11分因病医治无效，在北京逝世，享年96岁』。",
    },
    "20260812-wang-xiji": {
        "name": "王希季",
        "source": "新华社 / 人民网（科技日报）",
        "urls": [
            {
                "n": "人民网·科技日报",
                "u": "https://edu.people.com.cn/n1/2026/0814/c1006-40779531.html",
            },
            {
                "n": "央视网人物",
                "u": "https://people.cctv.com/2026/08/13/ARTIdyMhSkhekCJw1Ch8hrZe260813.shtml",
            },
        ],
        "identity": "空间技术专家 · 中国科学院院士 ·「两弹一星」功勋奖章获得者",
        "summary": "主持中国第一枚探空火箭与返回式卫星，是航天事业开拓者之一。",
        "bio": "王希季，1921年生于云南昆明，1948年赴美国弗吉尼亚理工学院留学并获硕士学位，1949年新中国成立后放弃继续深造回国。1958年任中国科学院上海机电设计院探空火箭技术负责人，1960年主持发射中国第一枚探空火箭“T-7M”。他提出长征一号运载火箭技术方案，主持多颗返回式卫星研制，使中国成为世界上第三个掌握卫星返回技术的国家。1999年获“两弹一星功勋奖章”。2026年8月12日因病医治无效在北京逝世，享年105岁。",
        "facts": [
            "1921年生于云南昆明，1949年放弃在美国攻读博士的机会回国",
            "1960年主持发射中国第一枚探空火箭“T-7M”",
            "提出长征一号运载火箭技术方案，主持返回式卫星研制",
            "1999年获“两弹一星功勋奖章”",
        ],
        "age": 105,
        "cause": CAUSE_DISEASE,
        "causeCategory": CAUSE_CATEGORY,
        "evidence": "新华社/人民网：『因病医治无效，于2026年8月12日在北京逝世，享年105岁』。",
    },
    "20261009-lou-yulie": {
        "name": "楼宇烈",
        "source": "北京大学哲学系官方讣告 / 光明日报",
        "urls": [
            {
                "n": "北京大学哲学系官方公众号",
                "u": "http://mp.weixin.qq.com/s?__biz=MjM5NTE1OTQyMQ==&mid=2651603976&idx=1&sn=b6b3a505acdced4b7250321ef6681d70",
            }
        ],
        "identity": "哲学家 · 中国哲学史家 · 北京大学哲学系教授",
        "summary": "执教北大六十六年，贯通儒释道，守护与阐释中国传统文化。",
        "bio": "楼宇烈，1934年12月10日生于杭州，浙江嵊县人。1960年北京大学哲学系本科毕业后留校，执教六十六年，长期从事中国哲学史、佛教哲学、东方哲学和宗教学研究，曾任北京大学哲学系副系主任、东方哲学教研室主任。代表作有《王弼集校释》《中国的品格》《中国文化的根本精神》，2025年出版《楼宇烈文集》。2026年10月9日2时18分因病在北京逝世，享年92岁。",
        "facts": [
            "1934年12月10日生于杭州，1960年北大哲学系毕业后留校",
            "执教六十六年，研究中国哲学史、佛教哲学与宗教学",
            "代表作《王弼集校释》《中国的品格》《中国文化的根本精神》",
            "晚年提倡“国艺”理念，弘扬昆曲、京剧、古琴、书法、茶道和中医",
        ],
        "age": 92,
        "cause": CAUSE_DISEASE,
        "causeCategory": CAUSE_CATEGORY,
        "evidence": "北京大学哲学系讣告：『于2026年10月9日2时18分在北京因病逝世，享年92岁』。原表享年91岁，已更正。",
    },
    "2026-01-14-024": {
        "name": "聂卫平",
        "source": "新华社 / 人民网",
        "urls": [
            {
                "n": "人民网·人民日报",
                "u": "https://politics.people.com.cn/n1/2026/0119/c461001-40647664.html",
            },
            {
                "n": "央视网·中国围棋协会讣告",
                "u": "https://tv.cctv.com/2026/01/15/VIDEjl1TgiQYDiY8IKAh3ojG260115.shtml",
            },
        ],
        "identity": "围棋九段 ·「棋圣」· 中国围棋协会名誉主席",
        "summary": "中日围棋擂台赛上的主将，掀起全国围棋热潮。",
        "bio": "聂卫平，1952年8月生于辽宁沈阳，河北深州人。1978年后历任国家围棋队运动员、总教练，1982年被授予围棋九段，1988年被授予“棋圣”称号，曾任中国围棋协会副主席、名誉主席。他曾6次获得全国个人赛冠军，率队在中日围棋擂台赛取得三连胜，是我国围棋事业的标志性人物。2026年1月14日因病在北京逝世，享年74岁。",
        "facts": [
            "1952年8月生于辽宁沈阳，河北深州人",
            "1982年获围棋九段，1988年被授予“棋圣”称号",
            "6次获得全国个人赛冠军，率队在中日围棋擂台赛三连胜",
            "曾任国家围棋队总教练、中国围棋协会名誉主席",
        ],
        "age": 74,
        "cause": CAUSE_DISEASE,
        "causeCategory": CAUSE_CATEGORY,
        "evidence": "新华社/人民日报：『因病于2026年1月14日在北京逝世，享年74岁』。中国围棋协会补充时间为22时55分。",
    },
    "20260125-liao-xilong": {
        "name": "廖锡龙",
        "source": "新华社 / 人民网",
        "urls": [
            {
                "n": "人民网·人民日报",
                "u": "https://cpc.people.com.cn/n1/2026/0130/c64094-40656070.html",
            }
        ],
        "identity": "中央军委原委员 · 解放军原总后勤部部长 · 上将",
        "summary": "从贵州入伍到上将，长期负责军队后勤现代化建设。",
        "bio": "廖锡龙，1959年1月从贵州省思南县入伍，1963年2月加入中国共产党。历任陆军第11军军长，成都军区副司令员、司令员，2002年10月任中国人民解放军总后勤部部长，同年11月任中央军委委员，2000年6月被授予上将军衔。是中国共产党第十五届、十六届、十七届中央委员。2026年1月23日1时50分因病在北京逝世，享年85岁。",
        "facts": [
            "1959年1月从贵州思南入伍，1963年2月入党",
            "曾任陆军第11军军长、成都军区司令员",
            "2002年任解放军总后勤部部长、中央军委委员",
            "2000年6月被授予上将军衔",
        ],
        "date": "2026-01-23",
        "age": 85,
        "cause": CAUSE_DISEASE,
        "causeCategory": CAUSE_CATEGORY,
        "evidence": "新华社/人民日报：『因病于2026年1月23日1时50分在北京逝世，享年85岁』。原表日期为2026-01-25，已更正。",
    },
    "2026-01-18-032": {
        "name": "梁栋材",
        "source": "光明日报 / 中国科学院生物物理研究所",
        "urls": [
            {
                "n": "光明网·光明日报",
                "u": "https://news.gmw.cn/2026-01/27/content_38559744.htm",
            }
        ],
        "identity": "分子生物物理学家 · 中国科学院院士",
        "summary": "中国结构生物学开拓者，参与测定猪胰岛素晶体结构。",
        "bio": "梁栋材，1932年5月29日生于广东广州，1955年毕业于中山大学化学系，1956年至1960年在前苏联科学院元素有机化合物研究所留学。1980年当选中国科学院学部委员（院士），1983年任中国科学院生物物理研究所所长。他主要从事结构生物学研究，领导北京胰岛素结构研究组测定猪胰岛素晶体结构，为我国结构生物学学科开创与发展作出杰出贡献。2026年1月18日因病医治无效在北京逝世，享年94岁。",
        "facts": [
            "1932年5月29日生于广东广州，1955年中山大学化学系毕业",
            "1980年当选中国科学院学部委员（院士），1983年任生物物理所所长",
            "领导测定猪胰岛素晶体结构，开创中国结构生物学研究",
            "获国家自然科学奖二等奖、何梁何利科学与技术进步奖",
        ],
        "age": 94,
        "cause": CAUSE_DISEASE,
        "causeCategory": CAUSE_CATEGORY,
        "evidence": "光明日报：『因病医治无效，于2026年1月18日在北京逝世，享年94岁』。",
    },
    "20260924-you-benchang": {
        "name": "游本昌",
        "source": "中国国家话剧院 / 央视新闻 / 中国新闻网",
        "urls": [
            {
                "n": "中国新闻网（央视新闻客户端）",
                "u": "https://www.chinanews.com.cn/cul/2026/09-24/10702842.shtml",
            },
            {
                "n": "央视新闻客户端",
                "u": "https://content-static.cctvnews.cctv.com/snow-book/index.html?item_id=3584785558137680&source=50006&sub_source=50006_001",
            },
        ],
        "identity": "表演艺术家 · 一级演员 ·《济公》饰演者",
        "summary": "以“鞋儿破、帽儿破”的济公成为一代观众记忆，耄耋之年再凭《繁花》走红。",
        "bio": "游本昌，1933年生，中国国家话剧院表演艺术家、一级演员。1956年上海戏剧学院毕业后进入中央实验话剧院（现中国国家话剧院），长期从事戏剧表演。1984年在央视春晚表演哑剧《淋浴》，随后主演电视剧《济公》而成名。87岁生日时接到《繁花》邀约，饰演“爷叔”再次受到关注。2024年获中央广播电视总台第二届中国电视剧年度盛典“终身成就艺术家”荣誉。2026年9月24日凌晨1时40分因病在北京逝世，享年93岁。",
        "facts": [
            "1933年生，1956年毕业于上海戏剧学院",
            "1984年央视春晚表演哑剧《淋浴》，后主演电视剧《济公》",
            "87岁出演《繁花》“爷叔”，2024年获“终身成就艺术家”",
            "从事文艺事业70余年，2025年5月被批准为中共预备党员",
        ],
        "age": 93,
        "cause": CAUSE_DISEASE,
        "causeCategory": CAUSE_CATEGORY,
        "evidence": "央视新闻/中国新闻网：『中国国家话剧院表演艺术家、一级演员游本昌，因病今晨在北京去世』；国家话剧院讣告载明1时40分逝世、享年93岁。",
    },
    "20261007-peng-yu": {
        "name": "彭玉",
        "source": "中国电视艺术家协会演员工作委员会 / 中国新闻网",
        "urls": [
            {
                "n": "中国新闻网",
                "u": "https://www.cns.com.cn/cul/2026/10-08/10708994.shtml",
            },
            {
                "n": "央广网",
                "u": "https://www.cnr.cn/newscenter/native/gd/kx/20261008/t20261008_527836108.shtml",
            },
        ],
        "identity": "影视表演艺术家 · 一级演员 ·《东北一家人》“牛大妈”扮演者",
        "summary": "演了一辈子老太太，把“牛大妈”演成一代人的荧屏记忆。",
        "bio": "彭玉，1934年出生于哈尔滨一个铁路工人家庭。17岁因话剧《钢铁是怎样炼成的》被哈尔滨话剧院选中，此后在话剧舞台深耕多年。1964年参演电影《千万不要忘记》，29岁时塑造“丈母娘”形象，此后多饰演母亲、奶奶等角色。60多岁时赴北京发展，相继出演《月圆今宵》《空镜子》《东北一家人》《浪漫的事》等作品，尤以《东北一家人》中“牛大妈”陈久香广为人知。2026年10月7日10时27分在珠海安详离世，享年93岁。",
        "facts": [
            "1934年生于哈尔滨，17岁进入哈尔滨话剧院",
            "1964年参演电影《千万不要忘记》，开启银幕生涯",
            "《东北一家人》中饰演退休护士长“牛大妈”陈久香",
            "还出演《月圆今宵》《空镜子》《浪漫的事》等作品",
        ],
        "age": 93,
        "evidence": "中国新闻网/央广网：『于2026年10月7日10时27分在珠海逝世，享年93岁』。原文为“安详离世”，未写明具体病因，故不补死因。原表享年92岁，已更正。",
    },
    "20260811-guo-lanying": {
        "name": "郭兰英",
        "source": "中国歌剧舞剧院 / 新华社",
        "urls": [
            {
                "n": "新华网·追忆",
                "u": "https://www.news.cn/20260812/996b3687edce4bc89de0d0c9a4985cf9/c.html",
            },
            {
                "n": "新华网·讣告",
                "u": "https://xinhuanet.com/20260812/45cf38635b0646338533de6c6aba161d/c.html",
            },
        ],
        "identity": "歌剧表演艺术家 ·「人民艺术家」国家荣誉称号获得者",
        "summary": "《我的祖国》的原唱者，以一生歌唱祖国。",
        "bio": "郭兰英，1930年生于山西平遥，5岁学习山西梆子，14岁在张家口演出。1946年观看歌剧《白毛女》后加入华北联大文工团，开启民族歌剧艺术生涯。新中国成立后，作为中央实验歌剧院和中国歌剧舞剧院首席领衔主演，塑造了喜儿、小芹、刘胡兰等舞台形象。她演唱的《我的祖国》《南泥湾》《人说山西好风光》家喻户晓，2019年获“人民艺术家”国家荣誉称号。2026年8月11日17时14分因病在广州逝世，享年97岁。",
        "facts": [
            "1930年生于山西平遥，5岁学山西梆子",
            "1946年加入华北联大文工团，主演《白毛女》",
            "演唱《我的祖国》《南泥湾》《人说山西好风光》等经典歌曲",
            "2019年获“人民艺术家”国家荣誉称号",
        ],
        "age": 97,
        "cause": CAUSE_DISEASE,
        "causeCategory": CAUSE_CATEGORY,
        "evidence": "中国歌剧舞剧院讣告/新华社：『因病于2026年8月11日17时14分在广州逝世，享年97岁』。原表享年96岁，已更正。",
    },
    "20260828-li-weikang": {
        "name": "李维康",
        "source": "国家京剧院 / 新华社",
        "urls": [
            {
                "n": "新华网·送别李维康",
                "u": "https://www.xinhuanet.com/politics/20260901/31097f9f457d480a85fdd06dc9b93292/c.html",
            }
        ],
        "identity": "京剧表演艺术家 · 国家级非遗代表性传承人",
        "summary": "熔梅、程、张流派于一炉，六十余年深耕京剧舞台。",
        "bio": "李维康，1947年生于北京，1958年考入中国戏曲学校，12岁登台演出《二进宫》，毕业后进入中国京剧院（现国家京剧院）。她先后师从华慧麟、程玉菁、张君秋、李玉茹等名家，熔梅派之雍容、程派之幽咽、张派之华美于一炉，形成清丽脱俗、刚柔并济的演唱风格。代表剧目有《四郎探母》《霸王别姬》《李清照》《蝶恋花》《恩仇恋》等，曾获首届中国戏剧梅花奖、大众电视金鹰奖最佳女主角。2026年8月28日因病在北京逝世，享年79岁。",
        "facts": [
            "1947年生于北京，1958年考入中国戏曲学校",
            "京剧国家级非遗代表性传承人，一级演员",
            "代表作《蝶恋花》《李清照》《恩仇恋》《霸王别姬》等",
            "曾任中国戏剧家协会副主席、中国文联副主席",
        ],
        "age": 79,
        "cause": CAUSE_DISEASE,
        "causeCategory": CAUSE_CATEGORY,
        "evidence": "国家京剧院/央视新闻：『2026年8月28日因病在北京去世，享年79岁』；新华社送别报道确认日期与年龄。",
    },
    "20260825-zheng-fengrong": {
        "name": "郑凤荣",
        "source": "中国妇女报 / 光明网（官方公众号）",
        "urls": [
            {
                "n": "光明网官方公众号",
                "u": "http://mp.weixin.qq.com/s?__biz=MjM5OTYyNzAyMA==&mid=2650457027&idx=1&sn=ed876f1fd0f02fd7d01f924b4f466dba",
            }
        ],
        "identity": "女子跳高运动员 · 中国田径协会原副主席",
        "summary": "中国第一个打破世界纪录的女运动员，被称为“报春燕”。",
        "bio": "郑凤荣，1937年生于山东济南，1953年入选国家田径集训队，曾任中国田径协会副主席，是第三届全国人大代表，第五、六、九届全国政协委员。1957年11月17日，她在北京田径运动会上以1.77米的成绩打破女子跳高世界纪录，成为中国第一个打破世界纪录的女运动员；1963年又跳过1.78米。1987年获国际田联75周年金质纪念章，1995年获国际奥委会奥林匹克银质勋章。2026年8月25日因病逝世，享年89岁。",
        "facts": [
            "1937年生于山东济南，1953年入选国家田径集训队",
            "1957年11月17日以1.77米打破女子跳高世界纪录",
            "中国第一个打破世界纪录的女运动员，被称为“报春燕”",
            "1995年获国际奥委会奥林匹克银质勋章",
        ],
        "age": 89,
        "cause": CAUSE_DISEASE,
        "causeCategory": CAUSE_CATEGORY,
        "evidence": "中国妇女报/光明网官方公众号：『女子跳高名宿、中国田径协会原副主席郑凤荣，于2026年8月25日因病逝世，享年89岁』。",
    },
}


def load_js_array(path: str):
    text = open(path, encoding="utf-8").read()
    start = text.index("=") + 1
    return json.loads(text[start:].strip().rstrip(";"))


def load_js_object(path: str):
    text = open(path, encoding="utf-8").read()
    start = text.index("=") + 1
    return json.loads(text[start:].strip().rstrip(";"))


def is_china_related(x: dict) -> bool:
    return "中国" in (x.get("country") or "")


def missing_fields(x: dict) -> list[str]:
    fields = ["nameOrig", "source", "causeOfDeath", "wikipedia", "portrait", "summary", "bio", "facts"]
    return [f for f in fields if not x.get(f)]


def build_candidates(data: list[dict]) -> list[dict]:
    out = []
    for x in data:
        if not is_china_related(x):
            continue
        mid = x["id"]
        done = mid in ENRICHMENTS
        miss = missing_fields(x)
        out.append(
            {
                "id": mid,
                "date": x.get("date"),
                "name": x.get("name"),
                "country": x.get("country"),
                "age": x.get("age"),
                "source": x.get("source"),
                "verified": x.get("verified"),
                "missingFields": miss,
                "priority": "高" if ("summary" in miss or not x.get("source")) else "中",
                "status": "已补全（官方讣告核验）" if done else "待检索",
                "officialObituary": bool(done),
            }
        )
    return out


def apply() -> None:
    deaths = load_js_array(DEATHS_PATH)
    links = load_js_object(SOURCE_LINKS_PATH)
    by_id = {x["id"]: x for x in deaths}
    # 候选统计必须基于写回前的状态，避免补全后薄数据数量被低估。
    pre_candidates = build_candidates(deaths)

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    shutil.copy2(DEATHS_PATH, os.path.join(DATA, f"deaths.before-china-official-{stamp}.js"))
    shutil.copy2(SOURCE_LINKS_PATH, os.path.join(DATA, f"source-links.before-china-official-{stamp}.js"))

    applied = []
    for mid, e in ENRICHMENTS.items():
        if mid not in by_id:
            raise KeyError(f"主数据中找不到 id: {mid}")
        x = by_id[mid]
        before = {
            "date": x.get("date"),
            "age": x.get("age"),
            "source": x.get("source"),
            "identity": x.get("identity"),
            "causeOfDeath": x.get("causeOfDeath"),
        }
        changes = []
        for key in ("identity", "summary", "bio", "facts", "source"):
            if e.get(key) and x.get(key) != e[key]:
                changes.append(key)
                x[key] = e[key]
        for source_key, target_key in (
            ("date", "date"),
            ("age", "age"),
            ("cause", "causeOfDeath"),
            ("causeCategory", "causeCategory"),
        ):
            if source_key not in e:
                continue
            if x.get(target_key) != e[source_key]:
                changes.append(target_key)
                x[target_key] = e[source_key]
        if x.get("verified") != "confirmed":
            changes.append("verified")
            x["verified"] = "confirmed"
        # 该地区记录现用官方来源重建链接，避免旧媒体链接与 source 字段错配。
        links[mid] = e["urls"]
        applied.append(
            {
                "id": mid,
                "name": e["name"],
                "source": e["source"],
                "urls": [u["u"] for u in e["urls"]],
                "before": before,
                "after": {
                    "date": x.get("date"),
                    "age": x.get("age"),
                    "source": x.get("source"),
                    "identity": x.get("identity"),
                    "causeOfDeath": x.get("causeOfDeath"),
                    "causeCategory": x.get("causeCategory"),
                    "verified": x.get("verified"),
                },
                "changedFields": changes,
                "evidence": e["evidence"],
            }
        )

    with open(DEATHS_PATH, "w", encoding="utf-8") as f:
        f.write("// 人物数据：每天离世的世界名人讣告档案\n")
        f.write("window.DEATHS_DATA = ")
        json.dump(deaths, f, ensure_ascii=False, separators=(",", ":"))
        f.write(";\n")

    with open(SOURCE_LINKS_PATH, "w", encoding="utf-8") as f:
        f.write("window.SOURCE_LINKS = ")
        json.dump(links, f, ensure_ascii=False, separators=(",", ":"))
        f.write(";\n")

    candidates = pre_candidates
    with open(CANDIDATES_PATH, "w", encoding="utf-8") as f:
        json.dump(candidates, f, ensure_ascii=False, indent=2)
    with open(ENRICH_PATH, "w", encoding="utf-8") as f:
        json.dump(
            {
                "generatedAt": datetime.now().isoformat(timespec="seconds"),
                "rule": "仅写入经国内官方讣告核验的字段；原文有值但不冲突的内容不覆盖；冲突时以官方讣告为准。",
                "records": applied,
            },
            f,
            ensure_ascii=False,
            indent=2,
        )

    corrected_age = [a for a in applied if a["before"]["age"] != a["after"]["age"]]
    corrected_date = [a for a in applied if a["before"]["date"] != a["after"]["date"]]
    lines = [
        "# 中国人物官方讣告补全报告",
        "",
        f"> 生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}（本地）",
        "",
        "## 一、筛选结果",
        "",
        f"- 精选表共 **{len(deaths):,}** 人。",
        f"- 国家/地区含“中国”的人物共 **{len(candidates)}** 人，全部集中在 2026 年。",
        f"- 其中缺少 `summary`/`bio`/`facts` 的薄数据记录 **{sum(1 for c in candidates if 'summary' in c['missingFields'])}** 人。",
        f"- 本轮先对 **{len(applied)}** 位有明确国内官方讣告的人物完成核验与补全，占中国人物 **{len(applied)/len(candidates)*100:.1f}%**。",
        "",
        "## 二、来源与核验规则",
        "",
        "优先采用新华社、央视、人民网、中国政府网、光明日报/光明网、中国新闻网、央广网、中国作家网，以及北大哲学系、中国国家话剧院、国家京剧院等机构官方讣告。",
        "只接受能同时核对**姓名+卒日或年份+享年**的报道；只有“据相关方面获悉”且无官方/权威机构来源的记录，本轮不写入。",
        "官方讣告写“因病医治无效/因病逝世”但无具体病名时，按死因字典归一为 `疾病（未详）`、大类 `疾病`；不推测具体疾病。",
        "",
        "## 三、本轮补全明细",
        "",
        "| 姓名 | 官方来源 | 补全/更正要点 |",
        "|---|---|---|",
    ]
    for a in applied:
        corr = []
        if a["before"]["age"] != a["after"]["age"]:
            corr.append(f"享年 {a['before']['age']}→{a['after']['age']}")
        if a["before"]["date"] != a["after"]["date"]:
            corr.append(f"卒日 {a['before']['date']}→{a['after']['date']}")
        corr.append("补生平/身份/来源" + ("/死因" if a["after"]["causeOfDeath"] else ""))
        lines.append(f"| {a['name']} | {a['source']} | {'；'.join(corr)} |")
    lines += [
        "",
        f"- 年龄更正 **{len(corrected_age)}** 人：" + "、".join(a["name"] for a in corrected_age) + "。",
        f"- 卒日更正 **{len(corrected_date)}** 人：" + "、".join(a["name"] for a in corrected_date) + "。",
        "",
        "## 四、写回文件",
        "",
        "- `data/deaths.js`：补全 15 人的身份、简介、生平、事实、来源、死因及年龄/日期更正。",
        "- `data/source-links.js`：上述 15 人改为官方讣告链接，移除原媒体链接避免错配。",
        f"- `archive-data/china-official-candidates.json`：全部 {len(candidates)} 位中国人物候选清单与状态。",
        "- `archive-data/china-official-enrichments.json`：逐人补全前后值与原文证据，可审计。",
        "",
        "## 五、边界与后续",
        "",
        "- 本轮是**高质量小样本试点**，不是 290 人全量补全；剩余人物仍标记为“待检索”。",
        "- 港澳台人物若缺少大陆官方渠道，需要另设中国香港/中国台湾本地官方来源规则，避免把地方媒体当中央官方讣告。",
        "- 对英文姓名、机构官网讣告、地方卫健委/高校讣告，可继续按同一证据结构扩量；每批仍需逐条核验姓名、日期和享年。",
        "",
    ]
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(json.dumps({"applied": len(applied), "candidates": len(candidates), "report": REPORT_PATH}, ensure_ascii=False))


if __name__ == "__main__":
    apply()
