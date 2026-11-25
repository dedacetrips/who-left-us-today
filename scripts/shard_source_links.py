#!/usr/bin/env python3
"""把 data/source-links.js 按 id 哈希切成 16 个分片，供前端按需加载。

背景：source-links.js 有 758KB / 4922 条，打开任意详情都需全量下载。
分片后按 id 取模定位到单片（约 47KB），只加载该片即可。

设计：
- 哈希函数用 FNV-1a 32 位，前端 JS 同款实现，保证 id → 片号一致
- 分片格式：window.SOURCE_LINKS = window.SOURCE_LINKS || {};
             window.SOURCE_LINKS[id] = [...];  （逐条赋值，避免大对象字面量）
- 原 data/source-links.js 保留为主数据源（前端不再直接引用）
- 校验：所有 key 恰好落在一片，拼合后与原文件逐键一致
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
SRC = DATA / "source-links.js"
OUTDIR = DATA / "source-links"
SHARDS = 16

def fnv1a(s: str, mod: int) -> int:
    h = 0x811c9dc5
    for ch in s.encode("utf-8"):
        h ^= ch
        h = (h * 0x01000193) & 0xffffffff
    return h % mod

def jdump(obj):
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"))

def main():
    s = SRC.read_text(encoding="utf-8")
    links = json.loads(s[s.index("{"):s.rindex("}")+1])
    OUTDIR.mkdir(exist_ok=True)

    buckets = [[] for _ in range(SHARDS)]
    for k in sorted(links):
        buckets[fnv1a(k, SHARDS)].append(k)

    total_bytes = 0
    for i, keys in enumerate(buckets):
        lines = ["window.SOURCE_LINKS = window.SOURCE_LINKS || {};"]
        for k in keys:
            lines.append(f"window.SOURCE_LINKS[{jdump(k)}] = {jdump(links[k])};")
        out = "\n".join(lines) + "\n"
        (OUTDIR / f"s{i}.js").write_text(out, encoding="utf-8")
        total_bytes += len(out.encode("utf-8"))

    # 校验：逐键比对
    got = {}
    for i in range(SHARDS):
        txt = (OUTDIR / f"s{i}.js").read_text(encoding="utf-8")
        import re
        for m in re.finditer(r"window\.SOURCE_LINKS\[(\"[^\"]*\")\] = (.+);", txt):
            k = json.loads(m.group(1)); v = json.loads(m.group(2))
            assert fnv1a(k, SHARDS) == i, f"{k} 落错分片"
            got[k] = v
    assert got == links, "拼合后与原文件不一致"
    assert sum(len(b) for b in buckets) == len(links), "条数不守恒"

    print(f"原文件: {len(s.encode('utf-8')):,} 字节 / {len(links)} 条")
    print(f"分片数: {SHARDS} | 分片总字节: {total_bytes:,}")
    print(f"各片条数: {[len(b) for b in buckets]}")
    print(f"单片最大: {max((OUTDIR/f's{i}.js').stat().st_size for i in range(SHARDS)):,} 字节")
    print("校验通过：条数守恒 / 落片正确 / 拼合后与原文件逐键一致")

if __name__ == "__main__":
    main()
