#!/usr/bin/env python3
"""把 deaths.js 从「对象数组」转成「列式压缩」格式，减小体积约一半。

原格式: window.DEATHS_DATA = [{id:...,date:...}, ...]   —— 每个对象重复 19 个键名
新格式: window.DEATHS_DATA = {cols:["id","date",...], rows:[[...],[...]]}  —— 键名只存一次

前端 index.html 里有还原函数把 rows 转回对象数组，对展示逻辑完全透明。
本脚本可重复运行：已是新格式时直接跳过。
"""
import json
import os
import shutil
import sys
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATH = os.path.join(ROOT, "data", "deaths.js")


def main():
    s = open(PATH, encoding="utf-8").read()
    head, body = s.split("=", 1)
    payload = body.strip().rstrip(";")

    # 已是新格式
    if payload.lstrip().startswith("{"):
        print("已是列式格式，跳过")
        return

    data = json.loads(payload)
    if not isinstance(data, list) or not data:
        print("数据为空或格式异常，终止")
        sys.exit(1)

    cols = list(data[0].keys())
    # 确保所有记录字段一致，不一致则补 None
    rows = []
    for x in data:
        row = []
        for c in cols:
            v = x.get(c)
            row.append(v if v != "" else None)  # 空串转 None，前端 || 回退更省
        rows.append(row)

    new_payload = json.dumps(
        {"cols": cols, "rows": rows}, ensure_ascii=False, separators=(",", ":")
    )
    new_content = head + "= " + new_payload + ";\n"

    # 备份
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup = PATH.replace(".js", f".before-compact-{stamp}.js")
    shutil.copy2(PATH, backup)

    old_size = len(s.encode("utf-8"))
    new_size = len(new_content.encode("utf-8"))
    open(PATH, "w", encoding="utf-8").write(new_content)

    print(f"记录 {len(data)}，字段 {len(cols)}")
    print(f"体积 {old_size/1024/1024:.2f}MB → {new_size/1024/1024:.2f}MB "
          f"(省 {(1-new_size/old_size)*100:.1f}%)")
    print(f"备份: {backup}")


if __name__ == "__main__":
    main()
