#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""完善 2026 年数据的来源字段：从原始 Excel 被丢弃的 sources 列回填。

- 数据源：原始 Excel 的 sources 列（JSON: publisher/url/title/source_type）
- 规则：
  * 精选表原有 source 一律保留（精选优先）
  * 按官方权威度对 publisher 分级，多来源时取最高级别
  * 同级别最多保留 3 个来源，用 " / " 连接
  * URL 明细另存 archive-data/source-urls.json
- 同步范围：精选表 data/deaths.js + 全表 archive-data/2026.js
"""
import openpyxl, json, os, re, collections

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
XLSX = '/root/uploads/1795504916120856186-人物全表_116817人.xlsx'

# 来源权威度分级：数字越小越优先
# tier1 官方/政府/通讯社/顶级权威媒体
TIER1_PAT = re.compile(
    r'(gov\.uk|\.gov\.|\bgov\b|白宫|外交部|国防部|政府|官方|gov\.cn|'
    r'\bap\b|ap news|apnews|reuters|路透|afp|法新|bbc|cnn|nbc|cbs|abc news|'
    r'\bnpr\b|新华社|xinhua|中央社|cna\.com\.tw|nhk|共同社|kyodo|'
    r'olympedia|olympics\.com|fifa\.com|who\.int|un\.org|nasa\.gov|'
    r'catholic-hierarchy|vatican|osservatoreromano|'
    r'the new york times|nytimes|washington post|washingtonpost|'
    r'the guardian|theguardian|financial times|ft\.com|economist)', re.I)

# tier2 主流媒体 / 知名讣告平台 / 行业数据库
TIER2_PAT = re.compile(
    r'(legacy|dignitymemorial|obituary|讣告|tributes|memorial|'
    r'people|variety|deadline|hollywood reporter|hollywoodreporter|'
    r'the times|thetimes|telegraph|independent|mirror|usa today|usatoday|'
    r'forbes|bloomberg|wsj|wall street journal|time\.com|newsweek|'
    r'lemonde|le figaro|lefigaro|elpais|elmundo|repubblica|corriere|spiegel|'
    r'cbc|radio-canada|abc\.net\.au|nzherald|stuff\.co\.nz|thehindu|'
    r'indianexpress|hindustantimes|timesofindia|globo|uol\.com|lanacion|'
    r'infobae|clarin|oricon|asahi|mainichi|nikkei|sponichi|nhk\.or\.jp|'
    r'billboard|rolling stone|entertainment weekly|sports illustrated|'
    r'espn|skysports|racingpost|baseball-almanac|nba\.com|nfl\.com|'
    r'page six|echovita|rip\.ie|irishtimes|rte\.ie|nyt|washington)', re.I)

# tier4 需降级：八卦/小报/论坛/聚合/UGC
TIER_LOW_PAT = re.compile(
    r'(tmz|dailymail|daily mail|freerepublic|order-order|breitbart|'
    r'yahoo|aol|huffpost|gossip|perezhilton|'
    r'reddit|4chan|quora|medium\.com|blogspot|wordpress\.com|'
    r'facebook|twitter|instagram|tiktok|'
    r'thebiglead|thethings|listverse|slippedisc|theuconnblog|'
    r'slashdot|gossiplanka)', re.I)

def tier(pub):
    if not pub: return 9
    if TIER1_PAT.search(pub): return 1
    if TIER2_PAT.search(pub): return 2
    if TIER_LOW_PAT.search(pub): return 4
    return 3  # 未识别的各国媒体：默认一般媒体，不降级

def norm_pub(p):
    p = re.sub(r'^www\.', '', p, flags=re.I)
    p = re.sub(r'\.(com|org|net|co\.uk|com\.tw)$', '', p, flags=re.I)
    return p.strip()

def load_sources():
    wb = openpyxl.load_workbook(XLSX, read_only=True, data_only=True)
    ws = wb.active
    data = {}
    for r in ws.iter_rows(min_row=2, values_only=True):
        date = str(r[1]) if r[1] else ''
        if not date.startswith('2026'): continue
        v = r[19]
        if v is None or str(v).strip() in ('','[]','null'): continue
        try: arr = json.loads(v)
        except: continue
        items = []
        for s in arr:
            if not isinstance(s, dict): continue
            pub = s.get('publisher')
            if not pub: continue
            items.append({'publisher': pub, 'url': s.get('url') or '',
                          'title': s.get('title') or '', 'tier': tier(pub)})
        if items: data[str(r[0])] = items
    return data

def pick_sources(items, limit=3):
    # 去重（按规范化 publisher + url）
    seen=set(); uniq=[]
    for it in items:
        k=(norm_pub(it['publisher']).lower(), it['url'])
        if k in seen: continue
        seen.add(k); uniq.append(it)
    uniq.sort(key=lambda x:(x['tier'], x['publisher'].lower()))
    top = uniq[0]['tier']
    # 只取最高档位内的来源，最多 limit 个
    best = [x for x in uniq if x['tier']==top][:limit]
    # 规范化显示名
    names=[]
    for x in best:
        n=norm_pub(x['publisher'])
        if n and n not in names: names.append(n)
    return ' / '.join(names) if names else '', best

def process(path, srcmap, extra):
    s=open(path,encoding='utf-8').read()
    arr=json.loads(s[s.index('['):s.rindex(']')+1])
    head=s[:s.index('[')]
    filled=0; skipped=0; stats=collections.Counter()
    for x in arr:
        id_=str(x['id'])
        if x.get('source') and str(x['source']).strip():
            skipped+=1; continue
        items=srcmap.get(id_)
        if not items: continue
        text,best=pick_sources(items)
        if text:
            x['source']=text; filled+=1
            stats[best[0]['tier']]+=1
            extra.setdefault(id_,{})['sourceUrls']=[
                {'publisher':b['publisher'],'url':b['url'],'title':b['title']} for b in best]
    open(path,'w',encoding='utf-8').write(head+json.dumps(arr,ensure_ascii=False,separators=(',',':'))+';\n')
    return filled, skipped, stats

def main():
    print('读取原始 Excel sources 列...')
    srcmap=load_sources()
    print('原始带来源记录:', len(srcmap))
    ep=os.path.join(BASE,'archive-data','extra.json')
    extra=json.load(open(ep,encoding='utf-8'))
    for v in extra.values(): v.pop('sourceUrls',None)  # 清理旧数据
    for rel in ['data/deaths.js','archive-data/2026.js']:
        path=os.path.join(BASE,rel)
        f,sk,stats=process(path,srcmap,extra)
        print(f'{rel}: 填入 {f} 条, 保留原有跳过 {sk} 条, 档位分布 {dict(stats)}')
    json.dump(extra,open(os.path.join(BASE,'archive-data','extra.json'),'w',encoding='utf-8'),
              ensure_ascii=False,separators=(',',':'))
    print('source-urls 已写入 extra.json')

if __name__=='__main__': main()
