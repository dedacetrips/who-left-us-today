#!/usr/bin/env python3
"""批量检索中国人物官方讣告线索（搜狗），落盘为 JSON 供人工核验。

只负责"找线索"，不写回主数据。输出包含每条查询的标题/链接/摘要，
由 enrich_china_official.py 的 ENRICHMENTS 人工核验后决定是否写入。
"""
from __future__ import annotations

import html
import json
import os
import re
import time

import requests

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ARCHIVE = os.path.join(ROOT, "archive-data")
OUT = os.path.join(ARCHIVE, "china-official-search.json")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36",
    "Accept-Language": "zh-CN,zh;q=0.9",
}

OFFICIAL_HINTS = [
    "news.cn", "xinhuanet.com", "xinhuaxmt.com", "people.com.cn", "peopleapp.com",
    "gov.cn", "cctv.com", "cctv.cn", "chinanews.com.cn", "cnr.cn", "gmw.cn",
    "cas.cn", "cae.cn", "gov.cn", "81.cn", "mod.gov.cn",
]


def strip_tags(s: str) -> str:
    s = re.sub(r"<[^>]+>", "", s)
    return html.unescape(s).strip()


def fetch(query: str, tries: int = 5):
    for _ in range(tries):
        try:
            r = requests.get("https://www.sogou.com/web", params={"query": query}, headers=HEADERS, timeout=20)
            if "vrwrap" in r.text and len(r.text) > 50000:
                return r.text
        except Exception:
            pass
        time.sleep(0.5)
    return ""


def parse(text: str):
    out = []
    # 搜狗结果块
    for block in re.split(r'<div class="vrwrap"', text)[1:]:
        seg = block[:20000]
        m = re.search(r'<h3[^>]*>(.*?)</h3>', seg, re.S)
        title = strip_tags(m.group(1)) if m else ""
        m = re.search(r'<a[^>]*href="([^"]+)"[^>]*>(.*?)</a>', seg, re.S)
        href = html.unescape(m.group(1)) if m else ""
        if href.startswith("/link?url="):
            href = "https://www.sogou.com" + href
        m = re.search(r'<div class="text-layout">(.*?)</div>', seg, re.S) or re.search(r'<p class="str-text-info">(.*?)</p>', seg, re.S)
        snippet = strip_tags(m.group(1)) if m else ""
        if not title and not snippet:
            continue
        official = any(h in href for h in OFFICIAL_HINTS) or any(h in snippet for h in ["新华社", "人民日报", "央视", "中国政府网"])
        out.append({"title": title, "url": href, "snippet": snippet[:1500], "official": official})
        if len(out) >= 8:
            break
    return out


def main():
    deaths_path = os.path.join(ROOT, "data", "deaths.js")
    t = open(deaths_path, encoding="utf-8").read()
    data = json.loads(t[t.index("=") + 1:].strip().rstrip(";"))
    done = {
        "20261107-yan-zhen","20261028-liu-yandong","20260812-zhu-rongji","20260304-song-ping",
        "20260531-gu-songfen","20260812-wang-xiji","20261009-lou-yulie","2026-01-14-024",
        "20260125-liao-xilong","2026-01-18-032","20260924-you-benchang","20261007-peng-yu",
        "20260811-guo-lanying","20260828-li-weikang","20260825-zheng-fengrong",
    }
    targets = []
    for x in data:
        if x["id"] in done or "中国" not in (x.get("country") or ""):
            continue
        if x.get("summary") and x.get("bio") and x.get("facts"):
            continue
        ident = (x.get("identity") or "").lower()
        name = x.get("name", "")
        # 只检索：中文名，且大陆身份词，或 country 仅"中国"
        cn = bool(re.search(r"[\u4e00-\u9fff]", name))
        c = (x.get("country") or "").strip()
        if c == "中国" and any(k in ident for k in ["politician", "general", "academic", "scientist", "engineer", "soldier", "governor", "minister", "physician", "jurist", "professor", "writer", "poet", "artist", "actor", "singer", "composer"]):
            targets.append(x)
        elif cn and c == "中国":
            targets.append(x)

    results = []
    for i, x in enumerate(targets):
        q = f'"{x["name"]}" 逝世 讣告 2026 新华社'
        txt = fetch(q)
        hits = parse(txt)
        results.append({
            "id": x["id"], "name": x["name"], "date": x.get("date"), "age": x.get("age"),
            "identity": x.get("identity"), "country": x.get("country"), "query": q,
            "hits": hits,
        })
        print(f"[{i+1}/{len(targets)}] {x['name']}: {len(hits)} hits, {sum(1 for h in hits if h['official'])} official")
        time.sleep(0.2)

    with open(OUT, "w", encoding="utf-8") as f:
        json.dump({"total": len(results), "results": results}, f, ensure_ascii=False, indent=2)
    print("saved", OUT)


if __name__ == "__main__":
    main()
