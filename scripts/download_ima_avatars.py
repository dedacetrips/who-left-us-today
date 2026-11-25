#!/usr/bin/env python3
"""从 IMA 知识库「冥冥之中」的 03_人物头像 文件夹下载头像。

背景：网页版项目最初只下载了 21 张头像，但 IMA 知识库中保存着完整的 254 张
（与 data/deaths.js 里的 portrait 路径 100% 对应）。IMA 的 get_media_info
接口有每日调用配额，配额耗尽后返回 code=220021「资料获取次数已达上限，
请明天再尝试」。本脚本支持断点续传：只下载 assets/portraits/ 中尚缺的文件，
配额耗尽时安全退出，明天重跑即可继续。

用法：
    python3 scripts/download_ima_avatars.py
"""
import json
import os
import subprocess
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

from PIL import Image
import io

SKILL_DIR = "/root/.codebuddy/skills/skill_2121227538835656704"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "assets/portraits")
CACHE = os.path.join(ROOT, "archive-data/ima-avatar-list.json")
KB = "ima_kb_1lqLyFB6"
FOLDER = "folder_7529017490042774"


def ima_api(endpoint, body):
    out = subprocess.run(
        ["node", "ima_api.cjs", endpoint, json.dumps(body, ensure_ascii=False)],
        capture_output=True, text=True, cwd=SKILL_DIR,
    ).stdout
    try:
        return json.loads(out)
    except Exception:
        return {}


def fetch_avatar_list():
    """拉取头像文件夹全部条目（分页），带本地缓存。"""
    if os.path.exists(CACHE):
        return json.load(open(CACHE, encoding="utf-8"))
    items, cursor = [], ""
    for _ in range(20):
        d = ima_api("openapi/wiki/v1/get_knowledge_list", {
            "knowledge_base_id": KB, "folder_id": FOLDER,
            "cursor": cursor, "limit": 50,
        })
        if d.get("code") != 0:
            break
        data = d["data"]
        items.extend(data.get("knowledge_list", []))
        if data.get("is_end"):
            break
        cursor = data.get("next_cursor", "")
        if not cursor:
            break
    json.dump(items, open(CACHE, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    return items


def get_url_info(mid):
    d = ima_api("openapi/wiki/v1/get_media_info", {"media_id": mid})
    if d.get("code") == 220021:
        return "QUOTA"
    if d.get("code") == 0:
        info = (d.get("data") or {}).get("url_info") or {}
        if info.get("url"):
            return info
    return None


def download(item):
    name = item["title"]
    info = get_url_info(item["media_id"])
    if info == "QUOTA":
        return (name, "QUOTA", "")
    if not info:
        return (name, "INFO_FAIL", "")
    try:
        req = urllib.request.Request(info["url"], headers=info.get("headers") or {})
        with urllib.request.urlopen(req, timeout=40) as r:
            data = r.read()
        im = Image.open(io.BytesIO(data))
        if im.format != "WEBP" or im.size != (192, 192):
            return (name, "BAD_FORMAT", f"{im.format}{im.size}")
        with open(os.path.join(OUT, name), "wb") as f:
            f.write(data)
        return (name, "OK", str(len(data)))
    except Exception as e:
        return (name, "DL_FAIL", str(e)[:80])


def main():
    os.makedirs(OUT, exist_ok=True)
    items = fetch_avatar_list()
    local = set(os.listdir(OUT))
    missing = [x for x in items if x["title"] not in local]
    total_webp = sum(1 for x in items if x["title"].lower().endswith(".webp"))
    print(f"IMA 头像总数 {total_webp}，本地已有 {len(local)}，待下载 {len(missing)}")

    ok = quota = 0
    fails = []
    with ThreadPoolExecutor(max_workers=6) as ex:
        futs = [ex.submit(download, x) for x in missing]
        for i, f in enumerate(as_completed(futs), 1):
            name, status, detail = f.result()
            if status == "OK":
                ok += 1
            elif status == "QUOTA":
                quota += 1
            else:
                fails.append((name, status, detail))
            if i % 25 == 0 or i == len(missing):
                print(f"  进度 {i}/{len(missing)}  成功 {ok}  配额受限 {quota}", flush=True)

    local_now = len([f for f in os.listdir(OUT) if f.lower().endswith(".webp")])
    print(f"\n本轮成功 {ok}；配额受限 {quota}；其他失败 {len(fails)}")
    print(f"本地头像现有 {local_now}/{total_webp} 张")
    if quota:
        print("IMA 每日配额已耗尽，明天重新运行本脚本即可续传剩余文件。")
    for name, status, detail in fails[:20]:
        print(f"  FAIL {name} {status} {detail}")


if __name__ == "__main__":
    main()
