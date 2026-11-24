#!/usr/bin/env python3
"""精选表去重合并。

判定为同一人的规则：name 相同 + 卒日相差<=3天 + 年龄差<=2 岁；
明确的不同人（同名不同职业/年龄）列入白名单排除。

合并规则：
1. 保留信息分最高的记录（summary/bio/facts/source/causeOfDeath/portrait/obit/nameOrig 计分）；
   同分时优先中文 id / 数字序号 id，其次拼音 id。
2. 被删记录的独有字段（保留记录为空者）合并进保留记录。
3. 日期/年龄以保留记录为准（完整版通常为官方讣告更正后的值）。
4. source 取保留记录；若保留为空而删除记录有值，则合并该来源。
5. source-links：被删 id 的链接并入保留 id（按 URL 去重），删除被删 id 键。
6. nameOrig：保留记录为空时取删除记录的英文名。
"""
from __future__ import annotations

import collections
import datetime
import json
import os
import shutil

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
ARCHIVE = os.path.join(ROOT, "archive-data")
DEATHS_PATH = os.path.join(DATA, "deaths.js")
SOURCE_LINKS_PATH = os.path.join(DATA, "source-links.js")
REPORT = os.path.join(ROOT, "去重合并报告.md")
AUDIT = os.path.join(ARCHIVE, "dedupe-merge-audit.json")

# 明确的不同人（同名，但身份/年龄差异明显），不合并
DIFFERENT = {
    "Petr Zeman", "Brian Smith", "John Anderson", "Michael Wright",
    "Ihor Zvarych", "David Andrews", "Tamás Horváth",
}
# 年龄差>2 但已人工确认同一人（如汉斯·赫尔曼：同为德国赛车手、同日卒）
FORCE_MERGE = {"汉斯·赫尔曼"}
SCORE_FIELDS = ["summary", "bio", "facts", "source", "causeOfDeath", "portrait", "obit", "nameOrig"]
MERGE_FIELDS = ["nameOrig", "identity", "summary", "bio", "facts", "source",
                "causeOfDeath", "causeCategory", "wikipedia", "portrait", "obit", "age", "date", "region", "verified"]


def pd(s):
    try:
        return datetime.date.fromisoformat(s)
    except Exception:
        return None


def score(x: dict) -> int:
    return sum(bool(x.get(k)) for k in SCORE_FIELDS)


def id_rank(mid: str) -> int:
    # 中文 id / 数字序号 id 优先于拼音 id
    if re_has_cn(mid):
        return 3
    if "-0" in mid or re_digits_tail(mid):
        return 2
    return 1


def re_has_cn(s: str) -> bool:
    return any("\u4e00" <= c <= "\u9fff" for c in s)


def re_digits_tail(s: str) -> bool:
    tail = s.split("-")[-1]
    return tail.isdigit()


def same_person(group: list[dict], name: str = "") -> bool:
    if len(group) < 2:
        return False
    if name in FORCE_MERGE:
        dates_f = [pd(x["date"]) for x in group]
        if None not in dates_f and (max(dates_f) - min(dates_f)).days <= 3:
            return True
    dates = [pd(x["date"]) for x in group]
    if None in dates:
        if len(set(x["date"] for x in group)) > 1:
            return False
    elif (max(dates) - min(dates)).days > 3:
        return False
    ages = [x.get("age") for x in group if x.get("age") is not None]
    if ages and (max(ages) - min(ages)) > 2:
        return False
    return True


def load_js(path):
    t = open(path, encoding="utf-8").read()
    return json.loads(t[t.index("=") + 1:].strip().rstrip(";"))


def apply():
    deaths = load_js(DEATHS_PATH)
    links = load_js(SOURCE_LINKS_PATH)
    byname = collections.defaultdict(list)
    for x in deaths:
        byname[x["name"]].append(x)

    merge_groups = []
    for name, group in byname.items():
        if name in DIFFERENT or not same_person(group, name):
            continue
        merge_groups.append((name, group))

    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    shutil.copy2(DEATHS_PATH, os.path.join(DATA, f"deaths.before-dedupe-{stamp}.js"))
    shutil.copy2(SOURCE_LINKS_PATH, os.path.join(DATA, f"source-links.before-dedupe-{stamp}.js"))

    remove_ids = set()
    audit = []
    for name, group in merge_groups:
        ranked = sorted(group, key=lambda x: (score(x), id_rank(x["id"])), reverse=True)
        keep = ranked[0]
        drops = ranked[1:]
        merged = {}
        for d in drops:
            # 保留记录的 source 若为泛化的“维基百科逝世列表”，而被删记录有更具体的
            # 官方/媒体/机构来源，则以具体来源替换（第一批官方讣告补全即属此情况）。
            ks = (keep.get("source") or "").lower()
            ds = d.get("source") or ""
            if ds and ("维基百科" in ks or "wikipedia" in ks) and "维基百科" not in ds:
                keep["source"] = ds
                merged.setdefault("source", []).append(d["id"])
            for f in MERGE_FIELDS:
                if d.get(f) and not keep.get(f):
                    keep[f] = d[f]
                    merged.setdefault(f, []).append(d["id"])
            # 来源链接并入保留 id
            for item in links.pop(d["id"], []):
                u = item.get("u")
                if u and not any(e.get("u") == u for e in links.setdefault(keep["id"], [])):
                    links[keep["id"]].append(item)
            remove_ids.add(d["id"])
        audit.append({
            "name": name,
            "keep": {"id": keep["id"], "score": score(keep), "date": keep.get("date"), "age": keep.get("age")},
            "removed": [{"id": d["id"], "score": score(d), "date": d.get("date"), "age": d.get("age")} for d in drops],
            "mergedFields": merged,
        })

    new_deaths = [x for x in deaths if x["id"] not in remove_ids]
    # source-links 不应残留已删 id（防御性清理）
    for mid in list(links):
        if mid in remove_ids:
            del links[mid]

    with open(DEATHS_PATH, "w", encoding="utf-8") as f:
        f.write("// 人物数据：每天离世的世界名人讣告档案\n")
        f.write("window.DEATHS_DATA = ")
        json.dump(new_deaths, f, ensure_ascii=False, separators=(",", ":"))
        f.write(";\n")
    with open(SOURCE_LINKS_PATH, "w", encoding="utf-8") as f:
        f.write("window.SOURCE_LINKS = ")
        json.dump(links, f, ensure_ascii=False, separators=(",", ":"))
        f.write(";\n")

    json.dump({"before": len(deaths), "after": len(new_deaths), "groups": len(audit),
               "removedRecords": len(remove_ids), "records": audit},
              open(AUDIT, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

    field_counts = collections.Counter()
    for a in audit:
        for f in a["mergedFields"]:
            field_counts[f] += 1
    corrected = [a for a in audit if a["mergedFields"]]
    lines = [
        "# 去重合并报告",
        "",
        f"> 生成时间：{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}（未推 GitHub）",
        "",
        "## 合并结果",
        "",
        f"- 主数据：**{len(deaths):,} → {len(new_deaths):,}** 条，减少 **{len(remove_ids)}** 条。",
        f"- 合并重复组：**{len(audit)}** 组（name 相同 + 卒日≤3天 + 年龄差≤2岁）。",
        f"- 明确的不同人（同名但职业/年龄不同）**{len(DIFFERENT)}** 组保留不合并：{'、'.join(sorted(DIFFERENT))}。",
        f"- 保留记录的信息分：优先内容完整（生平/事实/来源/死因齐全），同分取中文 id 或数字序号 id。",
        f"- 合并独有字段：{', '.join(f'{k} {v}处' for k, v in field_counts.most_common()) or '无'}。",
        f"- source-links：被删记录链接并入保留记录（按 URL 去重），无孤儿键。",
        "",
        "## 字段合并说明",
        "",
        "- `nameOrig`：保留记录无英文名时，取被删记录的英文名（如刘延东 Liu Yandong）。",
        "- `causeOfDeath`/`causeCategory`：官方讣告补全的死因在被删薄数据上时，合并到保留记录。",
        "- 日期、年龄以保留记录（通常为官方讣告更正值）为准；被删记录的不同口径不覆盖。",
        "",
        "## 有字段合并的组（前 30）",
        "",
        "| 姓名 | 保留 id | 删除 id | 合并字段 |",
        "|---|---|---|---|",
    ]
    for a in corrected[:30]:
        merged = "、".join(f"{k}←{','.join(ids)}" for k, ids in a["mergedFields"].items())
        lines.append(f"| {a['name']} | {a['keep']['id']} | {', '.join(d['id'] for d in a['removed'])} | {merged} |")
    lines += ["", f"> 全部 {len(audit)} 组合并明细见 `archive-data/dedupe-merge-audit.json`。",
              f"> 合并前快照：`data/deaths.before-dedupe-{stamp}.js` / `source-links.before-dedupe-{stamp}.js`。"]
    open(REPORT, "w", encoding="utf-8").write("\n".join(lines) + "\n")
    print(f"merged {len(audit)} groups, deaths {len(deaths)}->{len(new_deaths)}, report={REPORT}")


if __name__ == "__main__":
    apply()
