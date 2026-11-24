#!/usr/bin/env python3
"""审计精选表中"同一姓名+卒日"的重复记录，输出去重建议清单（不删数据）。

重复多为：精选表手工补全的中文记录（id 含中文/数字序号）与全表导入的自动薄数据（拼音id）并存。
建议保留信息更完整的记录，薄数据仅在其含独有字段（如 nameOrig/官方来源）时合并后删除。
"""
from __future__ import annotations

import collections
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
DEATHS_PATH = os.path.join(DATA, "deaths.js")
OUT = os.path.join(ROOT, "archive-data", "duplicate-audit.json")
REPORT = os.path.join(ROOT, "重复记录审计与去重建议.md")


def completeness(x: dict) -> int:
    return sum(bool(x.get(k)) for k in ("summary", "bio", "facts", "source", "causeOfDeath", "portrait", "obit", "nameOrig"))


def main():
    t = open(DEATHS_PATH, encoding="utf-8").read()
    data = json.loads(t[t.index("=") + 1:].strip().rstrip(";"))
    g = collections.defaultdict(list)
    for x in data:
        g[(x["name"], x["date"])].append(x)
    dups = {k: v for k, v in g.items() if len(v) > 1}

    groups = []
    for (name, date), v in dups.items():
        v = sorted(v, key=completeness, reverse=True)
        keep, *drops = v
        groups.append({
            "name": name, "date": date,
            "keep": {"id": keep["id"], "score": completeness(keep), "source": keep.get("source"),
                     "hasBio": bool(keep.get("bio"))},
            "drop": [{"id": d["id"], "score": completeness(d), "source": d.get("source"),
                      "hasBio": bool(d.get("bio")),
                      "uniqueFields": [f for f in ("nameOrig", "source", "causeOfDeath", "portrait", "wikipedia")
                                       if d.get(f) and not keep.get(f)]} for d in drops],
        })
    groups.sort(key=lambda x: (-x["keep"]["score"], x["name"]))

    json.dump({"totalGroups": len(groups), "groups": groups}, open(OUT, "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)

    lines = [
        "# 重复记录审计与去重建议",
        "",
        f"> 审计时间：{ __import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S') }（未改动主数据）",
        "",
        f"共发现 **{len(groups)}** 组「同一姓名 + 同一卒日」重复，涉及 **{sum(1 + len(g['drop']) for g in groups)}** 条记录。",
        "多数为精选表手工补全的中文记录与全表导入的拼音 id 自动薄数据并存。",
        "",
        "## 去重原则",
        "",
        "1. 保留信息分更高（summary/bio/facts/source/死因等）的记录，通常是中文 id 或数字序号 id。",
        "2. 删除薄数据前，若其含保留记录没有的 `nameOrig`/官方 `source`/`causeOfDeath`，先合并到保留记录。",
        "3. 港澳台重名（如两个刘兆铭）需人工确认是否同一人后再合并。",
        "",
        "## 建议删除的薄数据（前 40 组）",
        "",
        "| 姓名 | 卒日 | 保留 id（分） | 建议删除 id（分） | 待合并独有字段 |",
        "|---|---|---|---|---|",
    ]
    for g in groups[:40]:
        for d in g["drop"]:
            lines.append(f"| {g['name']} | {g['date']} | {g['keep']['id']}（{g['keep']['score']}） | {d['id']}（{d['score']}） | {'、'.join(d['uniqueFields']) or '—'} |")
    lines += ["", f"> 完整 {len(groups)} 组见 `archive-data/duplicate-audit.json`。本审计未删除任何记录。"]
    open(REPORT, "w", encoding="utf-8").write("\n".join(lines) + "\n")
    print(f"groups={len(groups)} report={REPORT}")


if __name__ == "__main__":
    main()
