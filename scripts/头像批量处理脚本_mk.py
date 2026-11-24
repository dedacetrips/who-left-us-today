#!/usr/bin/env python3
"""批量把线稿 PNG 处理成头像 webp 并写入 deaths.js
用法: python3 mk.py <组号,如 g41> '<JSON: {"姓名":"线稿路径"} >'
"""
import sys, json, os, shutil
import numpy as np, cv2
from PIL import Image, ImageFilter, ImageDraw, ImageFont

WS = "/sandbox/workspace/今天谁离开了我们"
group = sys.argv[1]
src = json.loads(sys.argv[2])


def prep(p, thr=32, work=768):
    g = np.array(Image.open(p).convert("L").filter(ImageFilter.MedianFilter(3))).astype(np.int16)
    a = (np.where(g > thr, 255, 0)).astype(np.uint8)
    ys, xs = np.where(a > 127)
    x0, x1, y0, y1 = xs.min(), xs.max(), ys.min(), ys.max()
    side = int(max(x1 - x0, y1 - y0) * 1.10)
    cx, cy = (x0 + x1) // 2, (y0 + y1) // 2
    box = (cx - side // 2, cy - side // 2, cx + side // 2, cy + side // 2)
    return np.array(Image.fromarray(a).crop(box).resize((work, work), Image.LANCZOS))


def finish(base, dil, work=768):
    m = cv2.dilate(base.copy(), np.ones((dil, dil), np.uint8)) if dil else base.copy()
    m = np.array(Image.fromarray(m).filter(ImageFilter.GaussianBlur(work / 768 * 1.2)))
    r = np.zeros((work, work, 4), np.uint8)
    r[..., :3] = 255
    r[..., 3] = m
    return Image.fromarray(r)


head, tail = open(f"{WS}/data/deaths.js", encoding="utf-8").read().split("window.DEATHS_DATA = ", 1)
D = json.loads(tail.rstrip().rstrip(";"))
idof = {x["name"]: x["id"] for x in D}

outdir = f"{WS}/_test/line/{group}"
os.makedirs(outdir, exist_ok=True)
res = []
for name, p in src.items():
    if name not in idof:
        print(f"!! 找不到姓名 {name}")
        continue
    base = prep(p)
    best = None
    for d in range(0, 34, 2):
        img = finish(base, d)
        sm = img.resize((192, 192), Image.LANCZOS)
        a = np.array(sm)[..., 3]
        solid = (a > 200).mean() * 100
        cov = (a > 10).mean() * 100
        if best is None or abs(solid - 14) < best[0]:
            best = (abs(solid - 14), d, cov, solid, sm, img)
    _, d, cov, solid, sm, big = best
    iid = idof[name]
    out = f"{outdir}/{iid}.webp"
    sm.save(out, "WEBP", quality=90, method=6)
    shutil.copy(out, f"{WS}/assets/portraits/{iid}.webp")
    for x in D:
        if x["id"] == iid:
            x["portrait"] = f"assets/portraits/{iid}.webp"
            x.pop("portraitStatus", None)
    kb = os.path.getsize(out) / 1024
    res.append((name, iid, d, cov, solid, kb, big))
    print(f"{name:<10} dil={d:<2} 覆盖{cov:5.1f}% 实线{solid:5.1f}% {kb:4.1f}KB")

open(f"{WS}/data/deaths.js", "w", encoding="utf-8").write(
    head + "window.DEATHS_DATA = " + json.dumps(D, ensure_ascii=False, indent=1) + ";\n")

F = ImageFont.truetype("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc", 14, index=2)
n = len(res)
cw, ch = 250, 380
c = Image.new("RGBA", (max(2, n) * cw + 40, ch + 60), (0, 0, 0, 255))
dr = ImageDraw.Draw(c)
for i, (name, iid, _, _, _, _, big) in enumerate(res):
    x = 20 + i * cw
    c.alpha_composite(big.resize((232, 232), Image.LANCZOS), (x, 30))
    c.alpha_composite(Image.open(f"{outdir}/{iid}.webp").resize((80, 80), Image.LANCZOS), (x + 76, 285))
    dr.text((x + 66, 372), name, font=F, fill=(140, 140, 140))
prev = f"{WS}/_test/line/{group}_preview.png"
c.convert("RGB").save(prev, quality=94)
print("预览:", prev)

tot = sum(1 for x in D if x.get("portrait"))
cn = sum(1 for x in D if x.get("portrait") and x["country"].startswith("中国"))
intl = sum(1 for x in D if x.get("portrait") and not x["country"].startswith("中国"))
print(f"全站 {tot}/{len(D)} | 中国 {cn} | 国际 {intl}")
