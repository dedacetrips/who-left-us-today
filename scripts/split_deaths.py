#!/usr/bin/env python3
"""把 data/deaths.js 按物理顺序切成首屏分片 + 后台分片。

保守方案：严格取原表前 PREVIEW_N 条作为首屏数据，不重排、不筛选。
- data/deaths-preview.js : window.DEATHS_DATA  {cols, rows[:50]} + window.DEATHS_META
- data/deaths-rest.js     : window.DEATHS_REST {rows: rows[50:]}
- 原 deaths.js 保留备份，文件名带时间戳。

校验：行数守恒、字段数守恒、meta 与 index.html 统计算法一致。
"""
import json
import math
import shutil
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
SRC = DATA / "deaths.js"
PREVIEW = DATA / "deaths-preview.js"
REST = DATA / "deaths-rest.js"
PREVIEW_N = 50
FIELD_ORDER = ["科技", "文艺", "影视", "军政", "社科", "体育", "医药", "商业", "传媒", "宗教", "其他"]


def load_json_after(s: str, marker: str):
    """从 marker 之后的第一个 { 开始，用 raw_decode 精确取一个对象，忽略后续赋值。"""
    start = s.index(marker) + len(marker)
    brace = s.index("{", start)
    obj, _ = json.JSONDecoder().raw_decode(s, brace)
    return obj


def load_columnar(path: Path):
    s = path.read_text(encoding="utf-8")
    d = load_json_after(s, "window.DEATHS_DATA")
    if not isinstance(d, dict) or "cols" not in d or "rows" not in d:
        raise ValueError(f"{path} 不是预期的列式结构 {{cols, rows}}")
    return d["cols"], d["rows"]


def jdump(obj) -> str:
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"))


def main():
    cols, rows = load_columnar(SRC)
    if len(rows) <= PREVIEW_N:
        raise ValueError(f"数据仅 {len(rows)} 条，不足以切出 {PREVIEW_N} 条首屏分片")

    i = {name: n for n, name in enumerate(cols)}
    head, tail = rows[:PREVIEW_N], rows[PREVIEW_N:]

    # 全量统计：与 index.html 的 DATA.reduce((a,b)=>a+b.age,0)/DATA.length 保持一致
    ages = [(r[i["age"]] or 0) for r in rows]
    avg_age = math.floor(sum(ages) / len(ages) + 0.5)  # JS Math.round 语义
    dates = [r[i["date"]] for r in rows]
    fc = Counter()
    for r in rows:
        for f in (r[i["fields"]] or []):
            fc[f] += 1
    meta = {
        "total": len(rows),
        "avgAge": avg_age,
        "dateMin": min(dates),
        "dateMax": max(dates),
        "fieldCounts": {k: fc[k] for k in FIELD_ORDER if fc[k]},
    }

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup = DATA / f"deaths.before-split-{stamp}.js"
    shutil.copy2(SRC, backup)

    PREVIEW.write_text(
        "// 首屏分片：原表物理前 50 条，字段完整，与后台分片同源。\n"
        f"window.DEATHS_DATA = {jdump({'cols': cols, 'rows': head})};\n"
        f"window.DEATHS_META = {jdump(meta)};\n",
        encoding="utf-8",
    )
    REST.write_text(
        "// 后台分片：原表第 51 条起。cols 与首屏分片一致，不重复存储。\n"
        f"window.DEATHS_REST = {jdump({'rows': tail})};\n",
        encoding="utf-8",
    )

    # 校验守恒
    assert len(head) + len(tail) == len(rows), "行数不守恒"
    assert all(len(r) == len(cols) for r in head + tail), "字段数不守恒"
    c2, r2 = load_columnar(PREVIEW)
    assert c2 == cols and r2 == head, "preview 回读不一致"
    rs = REST.read_text(encoding="utf-8")
    tail2 = load_json_after(rs, "window.DEATHS_REST")["rows"]
    assert tail2 == tail, "rest 回读不一致"
    assert head + tail == rows, "拼合后与原表不一致"

    print(f"原表备份     : {backup.name}")
    print(f"首屏分片     : {PREVIEW.name}  {len(head)} 条  {PREVIEW.stat().st_size:,} B")
    print(f"后台分片     : {REST.name}  {len(tail)} 条  {REST.stat().st_size:,} B")
    print(f"原表         : {len(rows)} 条  {SRC.stat().st_size:,} B")
    print(f"meta         : {jdump(meta)}")
    print("校验通过：行数守恒 / 字段守恒 / 拼合后与原表逐字节一致")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"失败: {e}", file=sys.stderr)
        sys.exit(1)
