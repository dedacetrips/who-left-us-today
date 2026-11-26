#!/usr/bin/env python3
"""按月批量拉取 dead-people.com 2026 年文章正文，按 slug 缓存为本地 JSON。
用于：数据源噪音识别 + 死因/国别/年龄/简介的可靠补全。
带磁盘缓存：已抓取的月份直接复用，失败分片可重跑。
"""
import json, time, urllib.request, urllib.parse, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / 'archive-data' / 'deadpeople-2026-fulltext.json'
API = 'https://www.dead-people.com/wp-json/wp/v2/posts'
UA = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

# 按月分块（左闭右开）
MONTHS = [(m, m + 1) for m in range(1, 13)]


def fetch_page(after, before, page, retry=4):
    q = {
        'after': after, 'before': before,
        'per_page': 100, 'page': page,
        '_fields': 'slug,date,link,content',
        'orderby': 'date', 'order': 'asc',
    }
    url = API + '?' + urllib.parse.urlencode(q)
    for i in range(retry):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=35) as resp:
                data = json.load(resp)
                pages = int(resp.headers.get('X-WP-TotalPages', '1'))
            return data, pages
        except Exception as e:
            sys.stderr.write(f'  retry {i+1}/{retry} page={page}: {type(e).__name__} {e}\n')
            if i < retry - 1:
                time.sleep(2 * (i + 1))
    return None, None


def main():
    store = {}
    if CACHE.exists():
        store = json.loads(CACHE.read_text(encoding='utf-8'))
        print(f'已有缓存 {len(store)} 条')

    for m, m2 in MONTHS:
        if m2 > 12:
            after = f'2026-12-01T00:00:00'; before = f'2027-01-01T00:00:00'
        else:
            after = f'2026-{m:02d}-01T00:00:00'; before = f'2026-{m2:02d}-01T00:00:00'
        print(f'\n=== 2026-{m:02d} ===')
        data, pages = fetch_page(after, before, 1)
        if data is None:
            print('  首屏失败，跳过该月'); continue
        print(f'  共 {pages} 页')
        got = list(data)
        for p in range(2, pages + 1):
            d, _ = fetch_page(after, before, p)
            if d is None:
                print(f'  第 {p} 页失败，跳过'); continue
            got.extend(d)
        for post in got:
            slug = post.get('slug')
            if not slug:
                continue
            html = (post.get('content') or {}).get('rendered', '')
            store[slug] = {'d': post.get('date', ''), 'l': post.get('link', ''), 'h': html}
        print(f'  本月拉取 {len(got)} 条，缓存累计 {len(store)}')
        CACHE.write_text(json.dumps(store, ensure_ascii=False), encoding='utf-8')

    print(f'\n完成：缓存 {len(store)} 条 -> {CACHE}')


if __name__ == '__main__':
    main()
