# -*- coding: utf-8 -*-
"""
生成 archive.html（历史档案页）

- 直接复用 index.html 的整段 <style>，保证列表卡片/时间轴/抽屉视觉与主站像素级一致
- 只追加少量历史页专属样式（年份切换条、精简说明）
- 页面逻辑写在模板里，不依赖构建产物

用法: python3.11 scripts/build_archive_html.py
"""
import os

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INDEX = os.path.join(BASE, 'index.html')
OUT = os.path.join(BASE, 'archive.html')

# 抽取主站 CSS
s = open(INDEX, encoding='utf-8').read()
a = s.find('<style>'); b = s.find('</style>', a) + len('</style>')
BASE_CSS = s[a:b]

EXTRA_CSS = """
<style>
/* ── 历史页专属 ── */
.archive-banner{
  border:1px solid var(--line-2);padding:12px 14px;margin-top:22px;
  font-size:12.5px;color:var(--ink-2);line-height:1.75;background:var(--paper-2);
}
.archive-banner b{color:var(--ink);font-weight:600}
a.back{color:var(--ink);text-decoration:none;border-bottom:1px solid var(--line-2)}
a.back:hover{border-color:var(--ink)}
/* ── 左侧年份时间轴（桌面）/ 顶部横滑（移动） ── */
.archive-layout{display:flex;gap:26px;align-items:flex-start;margin-top:6px}
.year-rail{
  width:118px;flex:0 0 118px;position:sticky;top:84px;
  max-height:calc(100vh - 108px);overflow-y:auto;
  padding:4px 0 10px;scrollbar-width:none;-ms-overflow-style:none;
}
.year-rail::-webkit-scrollbar{display:none}
.year-list{position:relative;display:flex;flex-direction:column;gap:14px}
.year-list::before{
  content:"";position:absolute;left:4px;top:7px;bottom:7px;
  border-left:1px dashed var(--line-2);
}
.year-item{
  position:relative;display:flex;align-items:center;gap:8px;
  text-decoration:none;color:var(--ink-3);font-family:var(--mono);
  font-size:12px;line-height:1;padding:1px 0;transition:color .18s;
}
.year-item .dot{
  width:9px;height:9px;flex:0 0 9px;border-radius:50%;
  border:1px solid var(--line-2);background:var(--paper);
  position:relative;z-index:1;transition:.18s;
}
.year-item .n{font-size:9px;opacity:.5;margin-left:auto}
.year-item:hover{color:var(--ink)}
.year-item:hover .dot{border-color:var(--ink)}
.year-item.on{color:var(--ink);font-weight:600}
.year-item.on .dot{background:var(--ink);border-color:var(--ink)}
.year-item[aria-current="page"] .y{text-decoration:underline;text-underline-offset:3px}
.archive-main{flex:1;min-width:0}
@media (max-width:900px){
  .archive-layout{display:block}
  .year-rail{position:static;width:auto;max-height:none;overflow:visible;padding:0;margin-bottom:10px}
  .year-list{
    flex-direction:row;overflow-x:auto;gap:7px;padding-bottom:12px;
    border-bottom:1px solid var(--line);scrollbar-width:none;-ms-overflow-style:none;
  }
  .year-list::-webkit-scrollbar{display:none}
  .year-list::before{display:none}
  .year-item{
    flex:0 0 auto;border:1px solid var(--line-2);padding:7px 12px;
    border-radius:2px;gap:6px;white-space:nowrap;
  }
  .year-item .dot{display:none}
  .year-item .n{margin-left:2px}
  .year-item.on{border-color:var(--ink)}
}
.year-meta{
  display:flex;align-items:baseline;justify-content:space-between;
  padding:20px 0 4px;
}
.year-meta .ym-t{font-family:var(--serif);font-size:22px;letter-spacing:.04em}
.year-meta .ym-s{font-size:11px;letter-spacing:.14em;color:var(--ink-4)}
.loading-year{padding:60px 0;text-align:center;color:var(--ink-3);font-size:13px}
.card-role.archive-role{color:var(--ink-2)}
.no-result{padding:60px 0;text-align:center;color:var(--ink-3)}
.no-result .big{font-family:var(--serif);font-size:40px;color:var(--line-2);line-height:1}
.no-result p{font-size:13px;line-height:1.8;margin-top:12px}
/* ── Hero 小字叙述 + 署名 ── */
.hero-statement{
  font-family:var(--serif);font-size:14px;line-height:1.9;
  color:var(--ink-2);margin:0 0 8px;max-width:62ch;letter-spacing:.01em;
}
.hero-sign{
  font-family:var(--serif);font-size:12px;color:var(--ink-3);
  text-align:right;letter-spacing:.06em;margin:0 0 2px;max-width:62ch;
}
</style>
"""

HTML = r'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover">
<meta name="theme-color" content="#000000">
<title>今天谁离开了我们</title>
<link rel="icon" href="data:image/svg+xml;base64,PHN2ZyB2aWV3Qm94PSIwIDAgMTAwIDEwMCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIiBhcmlhLWhpZGRlbj0idHJ1ZSI+PHBhdGggZD0iTTUwLjAwLDU5LjUwIEw0OS4xOSw2MC4yNCBMNDguNzUsNjAuOTcgTDQ4LjM5LDYxLjcxIEw0OC4wOCw2Mi40NSBMNDcuODEsNjMuMTggTDQ3LjU2LDYzLjkyIEw0Ny4zMyw2NC42NSBMNDcuMTMsNjUuMzkgTDQ2Ljk0LDY2LjEyIEw0Ni43Nyw2Ni44NSBMNDYuNjEsNjcuNTggTDQ2LjQ2LDY4LjMxIEw0Ni4zMiw2OS4wNCBMNDYuMTksNjkuNzcgTDQ0Ljk5LDc3LjY3IEM0My4zMiw4My44MiAzOS4wMSw4OC44OSAzMy41NSw5Mi4wNiBDNDMuNDksOTUuNjggNTYuNTEsOTUuNjggNjYuNDUsOTIuMDYgQzYwLjk5LDg4Ljg5IDU2LjY4LDgzLjgyIDU1LjAxLDc3LjY3IEw1My44Miw3MC40OSBDNTMuNDQsNjguMjMgNTIuNDgsNjUuOTkgNTEuMDIsNjMuOTkgTDQ4LjI1LDYwLjI0IEM0OC44Myw1OS45NyA0OS41Nyw1OS43MyA1MC4wMCw1OS41MCBaIiBmaWxsPSIjZmZmIi8+PC9zdmc+">
__BASE_CSS__
__EXTRA_CSS__
</head>
<body>
<div class="mourn-band"></div>

<header class="topbar">
  <div class="brand">
    <div class="brand-mark"><svg viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg" aria-hidden="true"><path d="M50 60 L30 92 Q50 98 70 92 Z" fill="#fff"/></svg></div>
    <div class="brand-name">今天谁离开了我们</div>
  </div>
  <div class="topbar-spacer"></div>
</header>

<main class="wrap">
  <section class="hero">
    <p class="hero-kicker">WHO LEFT US . TODAY</p>
    <p class="hero-statement">伊壁鸠鲁说："死亡对我们而言，什么也不是——我们存在时，它尚未到来；它到来时，我们已不在。"可我们依然记下每一个名字。因为死亡或许与逝者无关，却与留下来的人有关：记住他们，是我们对待生命的方式。</p>
    <p class="hero-sign">——冥冥之中团队</p>
    <p class="hero-sub" id="heroSub"></p>
  </section>

  <section class="stats">
    <div class="stat"><span class="stat-n" id="sTotal">—</span><span class="stat-l" id="sTotalLabel">—</span></div>
    <div class="stat"><span class="stat-n" id="sAvg">—</span><span class="stat-l" id="sAvgLabel">—</span></div>
  </section>

  <div class="archive-layout">
    <aside class="year-rail" aria-label="年份导航">
      <nav class="year-list" id="yearList"></nav>
    </aside>

    <div class="archive-main">
      <div class="toolbar" style="top:69px">
        <div class="chips" id="chips"></div>
        <div class="search-row">
          <label class="search-box">
            <svg viewBox="0 0 24 24"><circle cx="11" cy="11" r="6.5"/><path d="M16 16l4.5 4.5" stroke-linecap="round"/></svg>
            <input type="search" id="searchInput" placeholder="在当前年份搜索姓名、国家地区或身份…" autocomplete="off">
          </label>
        </div>
        <div class="result-row"><span class="result-count" id="resultCount"></span></div>
      </div>

      <div class="year-meta">
        <div class="ym-t" id="yearTitle">—</div>
        <div class="ym-s" id="yearRange">—</div>
      </div>

      <div class="timeline" id="timeline">
        <div class="loading-year">正在加载档案…</div>
      </div>

      <div class="load-more" id="loadMore" role="button" tabindex="0" aria-label="加载更多">
        <span class="load-spin"></span>加载更多 <span class="load-num"></span>
      </div>
    </div>
  </div>

  <footer class="foot">
    <p>逝世日期以逝者本国媒体或家属、供职机构公布的信息为准；死因仅在公开披露时记录。所有文字为编辑整理，不作商业用途。</p>
    <p class="foot-org">本网站由对生命及死亡教育感兴趣的伙伴组成的去中心化团队冥冥之中（MingMingStudio）负责运营与管理。</p>
    <div class="sign">WHO LEFT US .TODAY — 记住你终将离去</div>
  </footer>
</main>

<div class="overlay" id="overlay"></div>
<div class="sheet" id="sheet" role="dialog" aria-modal="true" aria-labelledby="sheetName" tabindex="-1">
  <div class="sheet-grip"><i></i><button class="sheet-close" id="sheetClose" aria-label="关闭">✕</button></div>
  <div class="sheet-inner" id="sheetInner"></div>
</div>

<button class="to-top" id="toTop" aria-label="回到顶部">↑</button>

<script src="archive-data/archive-index.js"></script>
<script>
/* ═══════════ 历史档案页 ═══════════
   数据：archive-data/YYYY.js（window.ARCHIVE_YYYY 对象数组），一次加载一年。
   索引：archive-data/archive-index.js（window.ARCHIVE_INDEX），首屏即可渲染左侧年份轴与统计。
*/
const IDX = window.ARCHIVE_INDEX || {years:[], total:0, fieldOrder:[]};
const $ = s => document.querySelector(s);
const pad = n => String(n).padStart(2,"0");
const WEEK = ["星期日","星期一","星期二","星期三","星期四","星期五","星期六"];
const parseD = s => { const [y,m,d] = s.split("-").map(Number); return new Date(y, m-1, d); };
const fmtDot = s => { const dt = parseD(s); return `${pad(dt.getMonth()+1)}.${pad(dt.getDate())}`; };
const fmtCn  = s => { const dt = parseD(s); return `${dt.getFullYear()} 年 ${dt.getMonth()+1} 月 ${dt.getDate()} 日`; };

let curYear = null;          // 当前年份字符串
let RAW = [];                // 当前年份原始数据
let DATA = [];               // 当前年份映射后数据
let PORTRAITS = {};          // 姓名 -> 头像路径（仅 2026 有）
let activeField = "全部";
let keyword = "";
let currentList = [], renderedCount = 0, lastDate = null, lastDayEl = null, lastMonth = null, monthCounts = {};
let suppressLoad = false, loading = false;
const PAGE_SIZE = 50;

/* 头像加载失败兜底：回退成姓名首字方块（与主站一致） */
document.addEventListener("error", (e) => {
  const img = e.target;
  if (!img || img.tagName !== "IMG") return;
  const box = img.parentElement;
  if (!box || !box.classList.contains("has-face")) return;
  const name = img.getAttribute("alt") || "";
  box.classList.remove("has-face");
  img.remove();
  box.textContent = name.replace(/·/g, "").slice(0, 1) || "?";
}, true);

/* ── 首屏统计 ── */
const yMin = IDX.years[IDX.years.length-1]?.year || "";
const yMax = IDX.years[0]?.year || "";
$("#heroSub").textContent = `${yMin} — ${yMax}　·　共 ${IDX.total.toLocaleString("zh-CN")} 位`;

/* ── 左侧年份时间轴 ── */
const yearList = $("#yearList");
function renderYears(){
  yearList.innerHTML = IDX.years.map(y => {
    const compact = y.count >= 1000 ? (y.count/1000).toFixed(1) + "k" : String(y.count);
    const on = y.year === curYear;
    return `<a class="year-item ${on?'on':''}" href="#y${y.year}" data-y="${y.year}"
      ${on?'aria-current="page"':''} title="${y.year} 年 · ${y.count.toLocaleString('zh-CN')} 条">
      <span class="dot"></span><span class="y">${y.year}</span><span class="n">${compact}</span>
    </a>`;
  }).join("");
}
yearList.addEventListener("click", e => {
  const b = e.target.closest(".year-item");
  if (!b) return;
  e.preventDefault();
  const y = b.dataset.y;
  if (y === curYear) return;
  history.pushState(null, "", "#y" + y);
  loadYear(y, true);
});
window.addEventListener("popstate", () => {
  const m = location.hash.match(/^#y(\d{4})$/);
  const target = (m && IDX.years.some(y => y.year === m[1]))
    ? m[1]
    : (IDX.years[0] || {}).year;
  if (target && target !== curYear) loadYear(target, true);
});

/* ── 加载某年 ── */
let scrollMode = "top";
function loadYear(year, fromUser){
  const meta = IDX.years.find(y => y.year === year);
  if (!meta || loading) return;
  scrollMode = fromUser ? "list" : "top";
  curYear = year;
  loading = true;
  renderYears();
  activeField = "全部"; keyword = "";
  $("#searchInput").value = "";
  $("#yearTitle").textContent = year + " 年";
  $("#yearRange").textContent = `${meta.count.toLocaleString('zh-CN')} 位 · 平均 ${meta.avgAge} 岁`;
  $("#sTotal").innerHTML = meta.count.toLocaleString("zh-CN") + '<small>位</small>';
  $("#sTotalLabel").textContent = year + "年逝者数";
  $("#sAvg").innerHTML = meta.avgAge + '<small>岁</small>';
  $("#sAvgLabel").textContent = year + "年平均享年";
  $("#timeline").innerHTML = `<div class="loading-year">正在加载 ${year} 年档案（${meta.count.toLocaleString('zh-CN')} 条）…</div>`;
  $("#chips").innerHTML = "";
  $("#resultCount").textContent = "";

  // 已加载过则直接用缓存
  const varName = meta.var;
  if (window[varName]) { finishLoad(window[varName], meta); return; }

  const sc = document.createElement("script");
  const timer = setTimeout(() => { if (!window[varName]) sc.onerror && sc.onerror(); }, 20000);
  sc.src = meta.file;
  sc.onload = () => {
    clearTimeout(timer);
    if (!window[varName]) { sc.remove(); sc.onerror && sc.onerror(); return; }
    finishLoad(window[varName], meta);
  };
  sc.onerror = () => {
    clearTimeout(timer); sc.remove();
    $("#timeline").innerHTML = `<div class="no-result"><div class="big">†</div><p>${year} 年档案加载失败，请检查网络后重试。</p></div>`;
    loading = false;
  };
  document.head.appendChild(sc);
}

function finishLoad(arr, meta){
  RAW = arr;
  DATA = arr.map(x => ({
    d: x.date, n: x.name, o: x.nameOrig || "", age: x.age || 0, c: x.country || "",
    f: x.fields || [], r: x.identity || "", id: x.id,
    s: x.summary || "", bio: x.bio || "", facts: x.facts || [],
    obit: x.obit || null, portrait: x.portrait || null,
    src: x.source || "", wiki: x.wikipedia || null,
    cause: x.causeOfDeath || null, causeCat: x.causeCategory || null
  }));
  PORTRAITS = {};
  DATA.forEach(x => { if (x.portrait) PORTRAITS[x.n] = x.portrait; });
  loading = false;
  renderChips();
  render({mode: scrollMode});
  scrollMode = "top";
}

/* ── 筛选器 ── */
function allFields(){
  const fc = IDX.years.find(y => y.year === curYear).fields || {};
  return (IDX.fieldOrder || []).filter(f => fc[f]);
}
function renderChips(){
  const fc = IDX.years.find(y => y.year === curYear).fields || {};
  const items = [{k:"全部", n:IDX.years.find(y=>y.year===curYear).count}].concat(
    allFields().map(f => ({k:f, n:fc[f]||0}))
  );
  $("#chips").innerHTML = items.map(({k,n}) => `
    <button class="chip ${k===activeField?'on':''}" data-k="${k}">${k}<span class="num">${n}</span></button>
  `).join("");
}
$("#chips").addEventListener("click", e => {
  const b = e.target.closest(".chip");
  if (!b) return;
  activeField = b.dataset.k; renderChips(); render();
});
$("#searchInput").addEventListener("input", e => {
  keyword = e.target.value.trim().toLowerCase();
  if (keyword && activeField !== "全部"){ activeField = "全部"; renderChips(); }
  render();
});

function match(x){
  if (activeField !== "全部" && !x.f.includes(activeField)) return false;
  if (!keyword) return true;
  return [x.n, x.o, x.c, x.r, x.f.join(" ")].join(" ").toLowerCase().includes(keyword);
}

/* ── 渲染时间轴 ── */
const timelineEl = $("#timeline");
function resultText(){
  return currentList.length === DATA.length
    ? `${currentList.length.toLocaleString('zh-CN')} 条记录 · 已显示 ${renderedCount}`
    : `${currentList.length.toLocaleString('zh-CN')} / ${DATA.length.toLocaleString('zh-CN')} 条 · 已显示 ${renderedCount}`;
}
function applyScroll(opt){
  if (!opt || opt.mode !== "list"){ window.scrollTo(0, 0); return; }
  // 等时间轴 DOM 插入完成后再滚动，否则 smooth 动画会被布局重绘打断
  requestAnimationFrame(() => {
    const layout = document.querySelector(".archive-layout");
    const top = layout ? layout.getBoundingClientRect().top + window.scrollY - 78 : 0;
    window.scrollTo({top: Math.max(0, top), behavior: "smooth"});
  });
}
function render(opt){
  currentList = DATA.filter(match);
  renderedCount = 0; lastDate = null; lastDayEl = null; lastMonth = null; monthCounts = {};
  timelineEl.innerHTML = "";
  suppressLoad = true;
  setTimeout(() => { suppressLoad = false; }, 250);
  $("#resultCount").textContent = resultText();
  if (!currentList.length){
    timelineEl.innerHTML = `<div class="no-result"><div class="big">†</div><p>没有找到符合条件的人。<br>试试换个关键词，或点回「全部」。</p></div>`;
    updateLoadMore(); applyScroll(opt); return;
  }
  appendBatch();
  applyScroll(opt);
}

function appendBatch(){
  if (renderedCount >= currentList.length){ updateLoadMore(); return; }
  const batch = currentList.slice(renderedCount, renderedCount + PAGE_SIZE);
  const byDate = {};
  batch.forEach(x => { (byDate[x.d] = byDate[x.d] || []).push(x); });
  const ds = Object.keys(byDate).sort().reverse();
  ds.forEach(d => {
    const items = byDate[d];
    if (d === lastDate && lastDayEl){
      const cards = lastDayEl.querySelector(".cards");
      cards.insertAdjacentHTML("beforeend", items.map(cardHTML).join(""));
      bindCards(cards, cards.querySelectorAll(".card").length - items.length);
      lastDayEl.querySelector(".day-count").textContent = cards.querySelectorAll(".card").length + " 位";
    } else {
      const m = d.slice(0,7);
      if (m !== lastMonth){
        const mm = +m.split("-")[1];
        timelineEl.insertAdjacentHTML("beforeend", `
          <div class="month-head">
            <span class="month-num">${mm} 月</span>
            <span class="month-cnt" data-month="${m}">0 位</span>
          </div>`);
        lastMonth = m; monthCounts[m] = 0;
      }
      const dt = parseD(d);
      timelineEl.insertAdjacentHTML("beforeend", `
        <section class="day">
          <header class="day-head">
            <div class="day-num">${fmtDot(d)}</div>
            <div class="day-week">${WEEK[dt.getDay()]}</div>
            <div class="day-count">${items.length} 位</div>
          </header>
          <div class="cards">${items.map(x => cardHTML(x)).join("")}</div>
        </section>`);
      lastDayEl = timelineEl.lastElementChild;
      bindCards(lastDayEl.querySelector(".cards"), 0);
      lastDate = d;
    }
    monthCounts[lastMonth] = (monthCounts[lastMonth] || 0) + items.length;
    const mh = timelineEl.querySelector(`.month-cnt[data-month="${lastMonth}"]`);
    if (mh) mh.textContent = monthCounts[lastMonth] + " 位";
  });
  renderedCount += batch.length;
  $("#resultCount").textContent = resultText();
  updateLoadMore();
}

function bindCards(container, fromIdx){
  const els = container.querySelectorAll(".card");
  for (let i = fromIdx; i < els.length; i++){
    const el = els[i];
    el.style.animationDelay = Math.min((i-fromIdx)*20, 220) + "ms";
    el.addEventListener("click", () => openSheet(+el.dataset.idx));
    el.addEventListener("keydown", e => {
      if (e.key === "Enter" || e.key === " "){ e.preventDefault(); openSheet(+el.dataset.idx); }
    });
  }
}

function updateLoadMore(){
  const el = $("#loadMore");
  if (!el) return;
  if (renderedCount >= currentList.length){
    el.innerHTML = `<span class="load-done">已显示全部 ${renderedCount} 位</span>`;
    el.classList.add("done");
  } else {
    el.innerHTML = `加载更多 <span class="load-num">（已显示 ${renderedCount} / ${currentList.length.toLocaleString('zh-CN')}）</span>`;
    el.classList.remove("done");
  }
}

const loadMoreEl = $("#loadMore");
if (loadMoreEl){
  const io = new IntersectionObserver(entries => {
    if (entries[0].isIntersecting && !suppressLoad && renderedCount < currentList.length) appendBatch();
  }, { rootMargin: "300px" });
  io.observe(loadMoreEl);
  loadMoreEl.addEventListener("click", () => {
    if (renderedCount < currentList.length) appendBatch();
  });
}

function escHtml(s){ return String(s||"").replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])); }
function mdInline(s){ return escHtml(s).replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>"); }

/* ── 讣告原文（详情打开时按需加载，与主站一致） ── */
const OBITS_FILE = "data/obits.js";
let obitsLoading = false, obitsQueue = [];
function loadObits(cb){
  if (window.OBITS){ cb(); return; }
  obitsQueue.push(cb);
  if (obitsLoading) return;
  obitsLoading = true;
  const s = document.createElement("script");
  const timer = setTimeout(() => { if (!window.OBITS) s.onerror && s.onerror(); }, 12000);
  s.src = OBITS_FILE;
  s.onload = () => {
    clearTimeout(timer);
    if (!window.OBITS){ s.remove(); s.onerror && s.onerror(); return; }
    obitsLoading = false; const q = obitsQueue; obitsQueue = []; q.forEach(f => f());
  };
  s.onerror = () => {
    clearTimeout(timer); s.remove();
    obitsLoading = false; const q = obitsQueue; obitsQueue = [];
    const btn = $("#obitBtn .obit-btn-t");
    if (btn) btn.textContent = "讣告加载失败，点击重试";
  };
  document.head.appendChild(s);
}
function obitHTML(o){
  if (o.level === "无公开讣告"){
    const m = (o.text||"").match(/\*\*说明\*\*：([^\n]+)/);
    return `<p class="obit-none">未检索到公开讣告。${m ? mdInline(m[1].trim()) : ""}</p>`;
  }
  const lines = (o.text||"").split(/\n+/).map(s => s.trim()).filter(Boolean);
  let out = "", list = [];
  const flush = () => {
    if (list.length){ out += `<ul class="obit-list">${list.map(x => `<li>${mdInline(x)}</li>`).join("")}</ul>`; list = []; }
  };
  lines.forEach(s => {
    const li = s.match(/^[-•]\s+(.+)$/);
    if (li) list.push(li[1]);
    else { flush(); out += `<p>${mdInline(s)}</p>`; }
  });
  flush();
  return `<div class="obit-body">${out}</div>${o.source ? `<div class="obit-src">来源：${escHtml(o.source)}</div>` : ""}`;
}
function bindObit(x){
  const btn = $("#obitBtn"), wrap = $("#obitWrap"), inner = $("#obitInner");
  if (!btn || !wrap || !inner) return;
  const label = btn.querySelector(".obit-btn-t"), lv = btn.querySelector(".obit-btn-lv");
  btn.addEventListener("click", () => {
    if (wrap.classList.contains("open")){
      wrap.classList.remove("open"); btn.dataset.state = "closed";
      label.textContent = inner.dataset.lv === "C" ? "讣告情况" : "阅读讣告原文";
      return;
    }
    if (inner.dataset.ready === "1"){
      wrap.classList.add("open"); btn.dataset.state = "open";
      label.textContent = inner.dataset.lv === "C" ? "收起" : "收起讣告";
      return;
    }
    label.textContent = "加载中…";
    loadObits(() => {
      const o = window.OBITS && window.OBITS[x.id];
      if (!o){ label.textContent = "讣告暂不可用"; return; }
      inner.innerHTML = obitHTML(o);
      inner.dataset.ready = "1";
      inner.dataset.lv = o.level === "无公开讣告" ? "C" : "AB";
      lv.textContent = o.level;
      wrap.classList.add("open"); btn.dataset.state = "open";
      label.textContent = inner.dataset.lv === "C" ? "收起" : "收起讣告";
    });
  });
}

function cardHTML(x){
  const idx = DATA.indexOf(x);
  const mono = escHtml(x.n.replace(/·/g,"").slice(0,1) || "?");
  const face = PORTRAITS[x.n]
    ? `<div class="mono has-face"><img src="${escHtml(PORTRAITS[x.n])}" alt="${escHtml(x.n)}" loading="lazy" decoding="async"></div>`
    : `<div class="mono">${mono}</div>`;
  return `
    <article class="card" data-idx="${idx}" tabindex="0" role="button" aria-label="查看 ${escHtml(x.n)}">
      ${face}
      <div class="card-main">
        <div class="card-name-row">
          <h3 class="card-name">${escHtml(x.n)}</h3>
          <span class="card-age">${x.age ? x.age + " 岁" : ""}</span>
        </div>
        <div class="card-orig">${escHtml(x.o)}</div>
        <div class="card-role archive-role">${escHtml(x.r)}</div>
        <div class="card-tags">
          ${x.f.map(f => `<span class="tag primary">${escHtml(f)}</span>`).join("")}
          ${x.c ? `<span class="tag">${escHtml(x.c)}</span>` : ""}
        </div>
      </div>
      <div class="card-arrow">→</div>
    </article>`;
}

/* ── 详情抽屉 ── */
const overlay = $("#overlay"), sheet = $("#sheet"), sheetInner = $("#sheetInner");
let curIdx = -1, lastFocused = null;
function openSheet(idx){
  const x = DATA[idx];
  if (!x) return;
  if (curIdx === -1) lastFocused = document.activeElement;
  curIdx = idx;
  const dt = parseD(x.d);
  const causeHtml = x.cause
    ? `${escHtml(x.cause)}${x.causeCat ? `<span class="fact-cat">${escHtml(x.causeCat)}</span>` : ""}`
    : `<span class="fact-none">未详</span>`;
  const headFace = PORTRAITS[x.n]
    ? `<div class="sheet-mono has-face"><img src="${escHtml(PORTRAITS[x.n])}" alt="${escHtml(x.n)}"></div>`
    : `<div class="sheet-mono">${escHtml(x.n.replace(/·/g,"").slice(0,1) || "?")}</div>`;
  const bioHtml = x.bio ? `<p class="sheet-bio">${escHtml(x.bio)}</p>` : "";
  const factsHtml = (x.facts && x.facts.length)
    ? `<div class="sheet-sec-title">生平要点</div><ul class="fact-list">${x.facts.map(f => `<li>${escHtml(f)}</li>`).join("")}</ul>`
    : "";
  const obitHtml = x.obit ? `
    <button class="obit-btn" id="obitBtn" data-state="closed">
      <span class="obit-btn-t">阅读讣告原文</span>
      <span class="obit-btn-r"><span class="obit-btn-lv"></span><span class="obit-btn-arrow">▾</span></span>
    </button>
    <div class="obit-wrap" id="obitWrap"><div class="obit-inner" id="obitInner"></div></div>` : "";
  sheetInner.innerHTML = `
    <div class="sheet-head">
      ${headFace}
      <div style="min-width:0">
        <h2 class="sheet-h1" id="sheetName">${escHtml(x.n)}</h2>
        <div class="sheet-orig">${escHtml(x.o)}</div>
        <div class="sheet-role">${escHtml(x.r)}</div>
      </div>
    </div>
    <div class="sheet-facts">
      <div class="fact"><span class="fact-k">卒日</span><span class="fact-v">${dt.getMonth()+1}.${dt.getDate()}</span></div>
      <div class="fact"><span class="fact-k">享年</span><span class="fact-v">${x.age ? x.age + " 岁" : "未详"}</span></div>
      <div class="fact"><span class="fact-k">国家地区</span><span class="fact-v">${escHtml(x.c || "未详")}</span></div>
      <div class="fact"><span class="fact-k">死因</span><span class="fact-v">${causeHtml}</span></div>
    </div>
    ${bioHtml}
    ${factsHtml}
    ${obitHtml}
    <div class="sheet-src">资料来源：
      ${x.src ? `<a class="src-link" href="${escHtml(x.src)}" target="_blank" rel="noopener noreferrer">${escHtml(x.src.replace(/^https?:\/\//,"").replace(/\/$/,""))} ↗</a>` : `<span class="fact-none">未标注</span>`}
      <br>逝世日期：${fmtCn(x.d)}（${WEEK[dt.getDay()]}）
      ${x.wiki ? `<br>维基百科：<a class="wiki-link" href="${escHtml(x.wiki)}" target="_blank" rel="noopener noreferrer">查看条目 ↗</a>` : ""}
    </div>
    <div class="sheet-nav">
      <button class="nav-btn" id="prevBtn" ${curIdx<=0?"disabled":""}>← 前一位</button>
      <button class="nav-btn" id="nextBtn" ${curIdx>=DATA.length-1?"disabled":""}>后一位 →</button>
    </div>`;
  overlay.classList.add("show");
  sheet.classList.add("show");
  document.body.style.overflow = "hidden";
  sheet.scrollTop = 0;
  sheet.focus({ preventScroll: true });
  $("#prevBtn").onclick = () => openSheet(curIdx-1);
  $("#nextBtn").onclick = () => openSheet(curIdx+1);
  bindObit(x);
}
function closeSheet(){
  overlay.classList.remove("show");
  sheet.classList.remove("show");
  document.body.style.overflow = "";
  if (lastFocused && lastFocused.focus) lastFocused.focus({ preventScroll: true });
}
$("#sheetClose").onclick = closeSheet;
overlay.addEventListener("click", closeSheet);
document.addEventListener("keydown", e => { if (e.key === "Escape") closeSheet(); });

/* ── 回到顶部 ── */
const toTop = $("#toTop");
window.addEventListener("scroll", () => {
  toTop.classList.toggle("show", window.scrollY > 600);
}, {passive:true});
toTop.onclick = () => window.scrollTo({top:0, behavior:"smooth"});

/* ── 启动：优先读 URL hash，否则默认最新年份 ── */
const hm = location.hash.match(/^#y(\d{4})$/);
const startYear = (hm && IDX.years.some(y => y.year === hm[1]))
  ? hm[1]
  : (IDX.years[0] || {}).year;
loadYear(startYear);
</script>
</body>
</html>
'''

out = HTML.replace('__BASE_CSS__', BASE_CSS).replace('__EXTRA_CSS__', EXTRA_CSS)
with open(OUT, 'w', encoding='utf-8') as f:
    f.write(out)
print(f'已生成 {os.path.basename(OUT)} ({len(out)} 字符)')
print('复用主站 CSS:', len(BASE_CSS), '字符')
