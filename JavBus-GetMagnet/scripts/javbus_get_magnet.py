#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
JavBus-GetMagnet scraper (stdlib only — no pip installs needed).

Given an actress star id (e.g. 138y) or a single video code (e.g. SNOS-313),
scrape javbus.com for the works, one torrent magnet link each (resolution rule:
smallest 1080p, else smallest 720p), and the cover image of every work.

Output — folder mode (default):
  <actress>/
    covers/<CODE>.jpg   one cover per work
    magnets.txt         番号 | 标题 | 大小 | 磁力
    data.json           machine-readable dataset (incl. cover file names)
    index.html          self-contained showcase page (cards + table view)

Usage:
  python javbus_get_magnet.py --name 河北彩花                 # folder ./河北彩花/
  python javbus_get_magnet.py --star 138y --outdir D:/my/dir  # folder in a custom place
  python javbus_get_magnet.py --code SNOS-313 --out list.txt  # legacy: single text file
  python javbus_get_magnet.py --star 138y --res 720 --delay 0.5

The first run must clear JavBus's age gate (a 2-step: "I'm 18" + a 5-question
Chinese driving-test quiz). This script auto-answers the quiz from a bundled
answer bank and persists the resulting session cookies so subsequent runs
skip the gate entirely. If a quiz question is not in the bank, it prints the
questions and prompts for answers (or exits code 3 with --no-interactive).
"""
import sys, os, re, json, time, random, base64, shutil, html as htmllib, argparse, threading, webbrowser
import urllib.request, urllib.parse, urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed
from http.cookiejar import MozillaCookieJar
from urllib.request import build_opener, HTTPCookieProcessor, Request
from datetime import date

BASE = "https://www.javbus.com"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_COOKIES = os.path.normpath(os.path.join(HERE, "..", "cookies.txt"))

# ---------------------------------------------------------------------------
# Driving-test quiz answer bank:  distinctive question substring -> correct option text.
# Matching is by substring and compared against the rendered option text, so it is
# robust to option-letter shuffling.  Not every gate question is listed; the solve
# loop retries with a fresh random set of 5 until it draws only bank-known ones.
QUIZ_BANK = {
    "当事人有以下哪种行为，要承担交通事故全部责任": "发生事故后故意损坏、伪造现场、毁灭证据的",
    "记载的驾驶人信息发生变化的要在多长时间内申请换证": "30日",
    "造成致人轻伤以上或者死亡的交通事故后逃逸": "12分",
    "实习期内驾驶人驾驶机动车上高速公路行驶": "需要持有相应或者更高准驾车型驾驶证三年以上的驾驶人陪同",
    "逾期不参加审验仍然驾驶机动车": "200元以上500元以下",
    "在高速公路上倒车的，一次记几分": "12分",
    "隐瞒有关情况或提供虚假材料申请": "1年",
    "行经人行横道，不按规定减速": "3分",
    "超过机动车驾驶证有效期一年以上未换证被注销，但未超过二年": "参加道路交通安全法律、法规和相关知识考试合格后",
    "年龄在70周岁以上的驾驶人多长时间要提交一次身体条件证明": "每1年",
    "初次申领机动车驾驶证，可以申请以下哪种准驾车型": "普通三轮摩托车",
    "机动车驾驶人户籍迁出原车辆管理所": "迁入地",
    "在考试过程中有贿赂.舞弊行为的，申请人在多少年内": "1年",
    "机动车购买后尚未注册登记，需要临时上道路行驶": "临时行驶车号牌",
    "申请人存在以下哪种行为，在一年内不得再次申领": "在考试过程中有舞弊行为",
    "申请轻型牵引挂车准驾车型的，年龄不得超过": "70周岁",
    "在高速公路或城市快速路上不按规定车道行驶的，一次记几分": "9分",
    "驾驶证有效期满前多长时间申请换证": "90日内",
    "驾驶机动车发生交通事故后当事人故意破坏、伪造现场、毁灭证据": "全部责任",
    "请他人代为接受交通违法行为处罚和记分并支付经济利益": "三，五",
}

# ---------------------------------------------------------------------------
# Showcase page template. Placeholders (replaced with str.replace, not format):
#   __TITLE__  page <title> + h1 (HTML-escaped)
#   __SUB__    subtitle fragment (star id / code + scrape date)
#   __DATA_JSON__  JSON array of works:
#     {code, series, title, date, size (site label), gb (number), res, magnet, cover (file or null)}
#   __COVERS_B64__  JSON object {code: base64(cover bytes)} — embedded so the 建目录
#     button can write cover files from file://, where fetch of local files is blocked
#   __ACTRESS__     JSON string — the label (actress name, or the code in --code mode);
#     建目录 creates <root>/<actress>/<番号 作品名>/封面
# Everything else is computed client-side from DATA. Covers live in covers/
# next to the page, so the file works from file:// with no server.
PAGE_TEMPLATE = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>__TITLE__ · 作品磁力清单</title>
<style>
  :root {
    color-scheme: light;
    --page: #f9f9f7;
    --surface-1: #fcfcfb;
    --text-primary: #0b0b0b;
    --text-secondary: #52514e;
    --text-muted: #898781;
    --grid: #e1e0d9;
    --baseline: #c3c2b7;
    --border: rgba(11,11,11,0.10);
    --chip: rgba(11,11,11,0.04);
  }
  @media (prefers-color-scheme: dark) {
    :root:where(:not([data-theme="light"])) {
      color-scheme: dark;
      --page: #0d0d0d;
      --surface-1: #1a1a19;
      --text-primary: #ffffff;
      --text-secondary: #c3c2b7;
      --text-muted: #898781;
      --grid: #2c2c2a;
      --baseline: #383835;
      --border: rgba(255,255,255,0.10);
      --chip: rgba(255,255,255,0.05);
    }
  }
  :root[data-theme="dark"] {
    color-scheme: dark;
    --page: #0d0d0d;
    --surface-1: #1a1a19;
    --text-primary: #ffffff;
    --text-secondary: #c3c2b7;
    --text-muted: #898781;
    --grid: #2c2c2a;
    --baseline: #383835;
    --border: rgba(255,255,255,0.10);
    --chip: rgba(255,255,255,0.05);
  }
  * { box-sizing: border-box; }
  /* the view toggle flips the `hidden` attribute; author display rules (.items{display:grid})
     would otherwise override the UA [hidden]{display:none} rule */
  [hidden] { display: none !important; }
  body {
    margin: 0;
    background: var(--page);
    color: var(--text-primary);
    font-family: system-ui, -apple-system, "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif;
    line-height: 1.5;
  }
  .wrap { max-width: 1100px; margin: 0 auto; padding: 32px 20px 64px; }

  header.page { display: flex; align-items: flex-end; justify-content: space-between; gap: 16px; margin-bottom: 20px; }
  h1 { font-size: 28px; font-weight: 700; margin: 0 0 4px; letter-spacing: 0.2px; }
  .sub { color: var(--text-secondary); font-size: 14px; }
  .sub .dim { color: var(--text-muted); }
  button.theme-btn {
    border: 1px solid var(--border); background: var(--surface-1); color: var(--text-secondary);
    font-size: 13px; padding: 7px 12px; border-radius: 8px; cursor: pointer; white-space: nowrap;
  }
  button.theme-btn:hover { color: var(--text-primary); }

  .card { background: var(--surface-1); border: 1px solid var(--border); border-radius: 12px; padding: 20px; margin-bottom: 16px; }
  .card h2 { font-size: 16px; font-weight: 600; margin: 0 0 2px; }
  .card .cap { font-size: 13px; color: var(--text-secondary); margin: 0 0 16px; }

  .filters { display: flex; flex-wrap: wrap; align-items: center; gap: 8px; margin: 4px 0 14px; }
  .view-toggle { display: inline-flex; border: 1px solid var(--border); border-radius: 8px; overflow: hidden; }
  .view-toggle button { border: 0; background: transparent; color: var(--text-secondary); font-size: 12.5px; padding: 6px 12px; cursor: pointer; }
  .view-toggle button.active { background: var(--chip); color: var(--text-primary); font-weight: 600; }
  .view-toggle .lbl { color: var(--text-muted); font-size: 12px; align-self: stretch; display: inline-flex; align-items: center; padding-left: 10px; }
  .search { border: 1px solid var(--border); background: var(--page); color: var(--text-primary); border-radius: 8px; padding: 7px 12px; font-size: 13px; width: 200px; outline: none; }
  .search:focus { border-color: var(--text-muted); }
  .filters .spacer { flex: 1; }
  .copyall { border: 1px solid var(--border); background: var(--surface-1); color: var(--text-secondary); border-radius: 8px; padding: 6px 11px; font-size: 12.5px; cursor: pointer; white-space: nowrap; }
  .copyall:hover { color: var(--text-primary); }
  .copyall:disabled { opacity: 0.55; cursor: default; }
  #refresh { min-width: 76px; text-align: center; }
  .right-group { display: flex; align-items: center; gap: 8px; flex-wrap: nowrap; }

  .items { display: grid; grid-template-columns: repeat(4, 1fr); gap: 14px; }
  .items.c1 { grid-template-columns: repeat(1, 1fr); }
  .items.c2 { grid-template-columns: repeat(2, 1fr); }
  .items.c3 { grid-template-columns: repeat(3, 1fr); }
  .items.c5 { grid-template-columns: repeat(5, 1fr); }
  .item { background: var(--surface-1); border: 1px solid var(--border); border-radius: 10px; overflow: hidden; display: flex; flex-direction: column; }
  .item-img { position: relative; aspect-ratio: 3 / 2; background: linear-gradient(135deg, var(--chip), var(--grid)); cursor: zoom-in; overflow: hidden; }
  .item-img img { width: 100%; height: 100%; object-fit: cover; display: block; }
  .item-img.noimg::after { content: attr(data-code); position: absolute; inset: 0; display: flex; align-items: center; justify-content: center; color: var(--text-muted); font-weight: 600; font-size: 14px; letter-spacing: 1px; }
  .item-body { padding: 10px 12px 12px; display: flex; flex-direction: column; gap: 6px; flex: 1; }
  .item-code { font-size: 13px; font-weight: 600; display: flex; align-items: center; gap: 6px; font-variant-numeric: tabular-nums; }
  .item-code .sz { margin-left: auto; color: var(--text-muted); font-weight: 500; font-size: 12px; }
  .item-title { font-size: 12.5px; color: var(--text-secondary); line-height: 1.4; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; min-height: 3.5em; }
  .item-foot { display: flex; align-items: center; flex-wrap: wrap; gap: 8px; margin-top: auto; }
  .item-date { font-size: 11.5px; color: var(--text-muted); font-variant-numeric: tabular-nums; }
  .nomag { font-size: 11.5px; color: var(--text-muted); }
  button.savebtn { border: 1px solid var(--border); background: var(--surface-1); color: var(--text-secondary); border-radius: 7px; padding: 4px 9px; font-size: 12px; cursor: pointer; }
  button.savebtn:hover { color: var(--text-primary); }
  button.savebtn:disabled { opacity: 0.45; cursor: default; }
  button.savebtn.ok { color: var(--text-secondary); border-color: var(--text-muted); }
  .item-foot .savebtn { margin-left: auto; }

  .table-wrap { overflow-x: auto; }
  table { width: 100%; border-collapse: collapse; min-width: 720px; }
  thead th { text-align: left; font-size: 12px; font-weight: 600; color: var(--text-muted); padding: 8px 10px; border-bottom: 1px solid var(--baseline); white-space: nowrap; }
  thead th.sortable { cursor: pointer; user-select: none; }
  thead th.sortable:hover { color: var(--text-primary); }
  thead th .arr { font-size: 10px; margin-left: 4px; color: var(--text-primary); }
  tbody td { padding: 9px 10px; border-bottom: 1px solid var(--grid); font-size: 13.5px; vertical-align: top; }
  tbody tr:hover td { background: var(--chip); }
  td.code { white-space: nowrap; font-weight: 600; font-variant-numeric: tabular-nums; }
  td.title { color: var(--text-secondary); }
  td.date { white-space: nowrap; color: var(--text-secondary); font-variant-numeric: tabular-nums; }
  td.size { white-space: nowrap; text-align: right; font-variant-numeric: tabular-nums; color: var(--text-secondary); }
  td.act { white-space: nowrap; text-align: right; }
  button.copy { border: 1px solid var(--border); background: var(--surface-1); color: var(--text-secondary); border-radius: 7px; padding: 4px 9px; font-size: 12px; cursor: pointer; }
  button.copy:hover { color: var(--text-primary); }
  button.copy.ok { color: var(--text-secondary); border-color: var(--text-muted); }
  .empty { padding: 28px 10px; text-align: center; color: var(--text-muted); font-size: 13.5px; }
  .count-note { font-size: 12.5px; color: var(--text-muted); margin-top: 10px; }

  #lb { position: fixed; inset: 0; z-index: 100; display: none; align-items: center; justify-content: center; }
  #lb.open { display: flex; }
  .lb-back { position: absolute; inset: 0; background: rgba(0,0,0,0.72); }
  .lb-box { position: relative; max-width: min(86vw, 780px); background: var(--surface-1); border: 1px solid var(--border); border-radius: 12px; overflow: hidden; }
  .lb-box img { width: 100%; display: block; max-height: 64vh; object-fit: contain; background: var(--page); }
  .lb-cap { padding: 12px 14px; font-size: 13px; color: var(--text-secondary); }
  .lb-cap b { color: var(--text-primary); }
  .lb-cap .copy { margin-left: 10px; }
  .lb-cap .savebtn { margin-left: 10px; }
  .lb-close { position: absolute; top: 6px; right: 6px; border: 0; background: var(--chip); color: var(--text-primary); border-radius: 8px; width: 30px; height: 30px; font-size: 16px; cursor: pointer; line-height: 1; }

  footer { font-size: 12.5px; color: var(--text-muted); margin-top: 4px; }

  #toast { position: fixed; left: 50%; bottom: 28px; transform: translateX(-50%); z-index: 120;
    background: var(--text-primary); color: var(--page); font-size: 13px; padding: 9px 16px;
    border-radius: 9px; max-width: 86vw; opacity: 0; pointer-events: none; transition: opacity 0.18s; }
  #toast.show { opacity: 0.95; }

  @media (max-width: 720px) {
    header.page { flex-direction: column; align-items: flex-start; }
    .items { grid-template-columns: repeat(2, 1fr); }
    .items.c1 { grid-template-columns: 1fr; }
  }
</style>
</head>
<body>
<div class="wrap">
  <header class="page">
    <div>
      <h1>__TITLE__</h1>
      <div class="sub">__SUB__</div>
    </div>
    <button class="theme-btn" id="themeToggle" title="切换浅色 / 深色">☾ 深色</button>
  </header>

  <section class="card">
    <h2>作品列表</h2>
    <p class="cap">每部已按「最小 1080P」规则挑选磁力 · 点击封面可放大</p>
    <div class="filters" id="filters"></div>
    <div id="grid" class="items"></div>
    <div id="tableCard" class="table-wrap" hidden>
      <table>
        <thead>
          <tr>
            <th class="sortable" id="th-code" tabindex="0" role="columnheader" aria-sort="none">番号<span class="arr"></span></th>
            <th>标题</th>
            <th class="sortable" id="th-date" role="columnheader" aria-sort="descending">发行日期<span class="arr">▼</span></th>
            <th class="sortable" id="th-size" role="columnheader" aria-sort="none" style="text-align:right">大小<span class="arr"></span></th>
            <th></th>
          </tr>
        </thead>
        <tbody id="tbody"></tbody>
      </table>
    </div>
    <div class="count-note" id="countNote"></div>
  </section>

  <footer>
    数据来源 JavBus · 每部作品选取最小 1080P 磁力（无 1080P 时回退 720P）
  </footer>
</div>

<div id="lb" role="dialog" aria-modal="true" aria-label="封面大图">
  <div class="lb-back" id="lbBack"></div>
  <figure class="lb-box" style="margin:0">
    <img id="lbImg" alt="封面大图">
    <div class="lb-cap"><span id="lbCap"></span><button class="copy" id="lbCopy">复制磁力</button><button class="savebtn" id="lbSave">建目录</button></div>
    <button class="lb-close" id="lbClose" aria-label="关闭">×</button>
  </figure>
</div>

<div id="toast" role="status"></div>

<script>
const DATA = __DATA_JSON__;
const COVERS_B64 = __COVERS_B64__;
const ACTRESS = __ACTRESS__;

const fmtGb = v => v == null ? '–' : v >= 10 ? v.toFixed(1) : v.toFixed(2);
const sizeTxt = d => d.gb == null ? '–' : fmtGb(d.gb) + ' GB';
const esc = s => s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');

/* ---- filters + views ---- */
const state = { q: '', key: 'date', dir: -1, view: 'cards', cols: 4 };
const grid = document.getElementById('grid');
const tableCard = document.getElementById('tableCard');
const tbody = document.getElementById('tbody');

document.getElementById('filters').innerHTML =
  '<span class="view-toggle"><button class="vt active" data-v="cards">卡片</button><button class="vt" data-v="table">表格</button></span>' +
  '<span class="view-toggle" id="colToggle" title="封面卡片列数 · 列数越小封面越大"><span class="lbl">列数</span>' +
  [1, 2, 3, 4, 5].map(n => '<button class="colbtn' + (n === 4 ? ' active' : '') + '" data-c="' + n + '">' + n + '</button>').join('') +
  '</span>' +
  '<input class="search" id="q" placeholder="搜索番号 / 标题…" aria-label="搜索">' +
  '<span class="spacer"></span>' +
  '<span class="right-group">' +
  '<button class="copyall" id="refresh" title="最小校验：先只抓作品列表对比番号；有新增才抓取新作品，更新资源库后自动刷新页面（需 --serve 本地服务）">获取更新</button>' +
  '<button class="copyall" id="saveDir" title="选择封面保存的本地目录（存封面 / 建目录 按钮的根目录）">保存目录：未设置</button>' +
  '<button class="copyall" id="saveAll" title="为当前显示的所有作品批量创建「女优名/番号 作品名」文件夹并写入封面图">一键建目录</button>' +
  '<button class="copyall" id="copyAll">复制全部磁力</button>' +
  '</span>';
const colToggle = document.getElementById('colToggle');

document.getElementById('q').addEventListener('input', e => { state.q = e.target.value.trim().toLowerCase(); render(); });
document.getElementById('filters').addEventListener('click', e => {
  const vt = e.target.closest('.vt');
  if (vt) {
    document.querySelectorAll('.vt').forEach(b => b.classList.toggle('active', b === vt));
    state.view = vt.dataset.v;
    grid.hidden = state.view !== 'cards';
    tableCard.hidden = state.view !== 'table';
    colToggle.hidden = state.view !== 'cards';
    return;
  }
  const cb = e.target.closest('#colToggle .colbtn');
  if (cb) {
    colToggle.querySelectorAll('.colbtn').forEach(b => b.classList.toggle('active', b === cb));
    state.cols = +cb.dataset.c;
    grid.className = 'items c' + state.cols;
    return;
  }
  if (e.target.closest('#saveDir')) { pickSaveRoot(); return; }
  if (e.target.closest('#saveAll')) { saveAllWorks(); return; }
  if (e.target.closest('#refresh')) { refreshData(); return; }
  if (e.target.closest('#copyAll')) copyAll();
});

const codeNum = c => parseInt(c.split('-')[1], 10) || 0;
function visibleRows() {
  let rows = DATA.filter(d =>
    !state.q || d.code.toLowerCase().includes(state.q) || d.title.toLowerCase().includes(state.q)
  );
  if (state.key === 'date') rows = rows.slice().sort((a, b) => (a.date < b.date ? -1 : a.date > b.date ? 1 : 0) * state.dir);
  if (state.key === 'code') rows = rows.slice().sort((a, b) => (codeNum(a.code) - codeNum(b.code)) * state.dir);
  if (state.key === 'size') rows = rows.slice().sort((a, b) => ((a.gb ?? -1) - (b.gb ?? -1)) * state.dir);
  return rows;
}
function render() {
  const rows = visibleRows();
  grid.innerHTML = rows.map(d =>
    '<div class="item">' +
      '<div class="item-img' + (d.cover ? '' : ' noimg') + '" data-code="' + d.code + '" title="点开放大">' +
        (d.cover ? '<img src="covers/' + d.cover + '" alt="' + d.code + '" loading="lazy">' : '') +
      '</div>' +
      '<div class="item-body">' +
        '<div class="item-code">' + d.code + '<span class="sz">' + sizeTxt(d) + '</span></div>' +
        '<div class="item-title">' + esc(d.title) + '</div>' +
        '<div class="item-foot"><span class="item-date">' + (d.date || '–') + '</span>' +
        saveBtn(d) +
        (d.magnet ? '<button class="copy" data-m="' + esc(d.magnet) + '">复制磁力</button>' : '<span class="nomag">无磁力</span>') +
        '</div>' +
      '</div>' +
    '</div>'
  ).join('') || '<div class="empty" style="grid-column:1/-1">没有匹配的作品</div>';
  tbody.innerHTML = rows.length ? rows.map(d =>
    '<tr><td class="code">' + d.code + '</td>' +
    '<td class="title">' + esc(d.title) + '</td>' +
    '<td class="date">' + (d.date || '–') + '</td>' +
    '<td class="size">' + sizeTxt(d) + '</td>' +
    '<td class="act">' + saveBtn(d) + (d.magnet ? '<button class="copy" data-m="' + esc(d.magnet) + '">复制磁力</button>' : '<span class="nomag">–</span>') + '</td></tr>'
  ).join('') : '<tr><td colspan="5"><div class="empty">没有匹配的作品</div></td></tr>';
  const gb = rows.reduce((t, d) => t + (d.gb || 0), 0);
  document.getElementById('countNote').textContent =
    '显示 ' + rows.length + ' / ' + DATA.length + ' 部 · 合计 ' + fmtGb(gb) + ' GB';
  const all = document.getElementById('copyAll');
  const withMag = rows.filter(d => d.magnet).length;
  all.textContent = '复制全部磁力（' + withMag + '）';
  all.dataset.n = withMag;
  const sa = document.getElementById('saveAll');
  if (!savingAll) sa.textContent = '一键建目录（' + rows.filter(d => d.cover).length + '）';
}
/* cover load failures -> show the 番号 placeholder */
grid.addEventListener('error', e => {
  if (e.target.tagName === 'IMG') {
    const box = e.target.closest('.item-img');
    e.target.remove();
    if (box) box.classList.add('noimg');
  }
}, true);

/* copy (row / card buttons) */
async function copyText(t) {
  try { await navigator.clipboard.writeText(t); }
  catch (_) {
    const ta = document.createElement('textarea');
    ta.value = t; document.body.appendChild(ta); ta.select();
    document.execCommand('copy'); ta.remove();
  }
}
async function flash(btn, msg) {
  const old = btn.textContent;
  btn.classList.add('ok'); btn.textContent = msg || '已复制 ✓';
  setTimeout(() => { btn.classList.remove('ok'); btn.textContent = old; }, 1500);
}
grid.addEventListener('click', e => {
  const sv = e.target.closest('button.savebtn');
  if (sv) { saveWorkCover(sv.dataset.code, sv); return; }
  const btn = e.target.closest('button.copy');
  if (btn) { copyText(btn.dataset.m); flash(btn); return; }
  const im = e.target.closest('.item-img');
  if (im) openLb(im.dataset.code);
});
tbody.addEventListener('click', e => {
  const sv = e.target.closest('button.savebtn');
  if (sv) { saveWorkCover(sv.dataset.code, sv); return; }
  const btn = e.target.closest('button.copy');
  if (btn) { copyText(btn.dataset.m); flash(btn); }
});
async function copyAll() {
  const rows = visibleRows().filter(d => d.magnet);
  if (!rows.length) return;
  const btn = document.getElementById('copyAll');
  await copyText(rows.map(d => d.magnet).join('\n'));
  btn.textContent = '已复制 ' + rows.length + ' 条 ✓';
  setTimeout(() => {
    const n = document.getElementById('copyAll').dataset.n;
    document.getElementById('copyAll').textContent = '复制全部磁力（' + n + '）';
  }, 1500);
}

/* save cover: create "<番号> - <作品名>/" under the configured local directory and
   write the cover image into it (File System Access API — Chrome / Edge) */
/* "already created" state: probe the save root for existing work folders and
   mirror the result onto the 建目录 buttons (已创建 ✓). Browsers can't watch the
   disk, so the scan runs on load / root change / window refocus — enough to stay
   in step while the user creates or deletes folders in Explorer. */
const createdSet = new Set();
let scannedFor = null, scanning = false;
const sanitizeName = s => s.replace(/[\\/:*?"<>|]/g, '_').replace(/\s+/g, ' ').trim().slice(0, 120);
const ACTRESS_DIR = sanitizeName(ACTRESS || '未命名');
const folderNameOf = d => sanitizeName(d.code + ' ' + (d.title || ''));
function applyCreatedState() {
  for (const btn of document.querySelectorAll('button.savebtn')) {
    const done = createdSet.has(btn.dataset.code);
    btn.classList.toggle('ok', done);
    if (btn.textContent !== (done ? '已创建 ✓' : '建目录')) btn.textContent = done ? '已创建 ✓' : '建目录';
  }
}
async function maybeScan(force) {
  if (!saveRoot || scanning) return;
  if (!force && scannedFor === saveRoot) return;
  let p = 'prompt';
  try { p = await saveRoot.queryPermission({ mode: 'readwrite' }); } catch (_) { return; }
  if (p !== 'granted') return;
  scanning = true;
  const found = [];
  let parent = null;
  try { parent = await saveRoot.getDirectoryHandle(ACTRESS_DIR, { create: false }); }
  catch (_) { /* actress level not created yet -> nothing is done */ }
  if (parent) {
    for (const d of DATA) {
      if (!d.cover) continue;
      try { await parent.getDirectoryHandle(folderNameOf(d), { create: false }); found.push(d.code); }
      catch (_) { /* folder not created yet */ }
    }
  }
  scanning = false;
  scannedFor = saveRoot;
  createdSet.clear();
  found.forEach(c => createdSet.add(c));
  applyCreatedState();
}
window.addEventListener('focus', () => maybeScan(true));
function saveBtn(d) {
  const done = createdSet.has(d.code);
  return '<button class="savebtn' + (done ? ' ok' : '') + '" data-code="' + d.code + '"' +
    (d.cover ? '' : ' disabled title="该作品没有封面图"') +
    ' title="在保存目录下创建「' + esc(ACTRESS_DIR + '\\' + folderNameOf(d)) + '」文件夹并写入封面图">' +
    (done ? '已创建 ✓' : '建目录') + '</button>';
}
let toastTimer;
function toast(msg) {
  const t = document.getElementById('toast');
  t.textContent = msg;
  t.classList.add('show');
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => t.classList.remove('show'), 2600);
}
let saveRoot = null; // FileSystemDirectoryHandle of the configured root
async function idbOpen() {
  return new Promise((res, rej) => {
    const req = indexedDB.open('javbus-page', 1);
    req.onupgradeneeded = () => req.result.createObjectStore('kv');
    req.onsuccess = () => res(req.result);
    req.onerror = () => rej(req.error);
  });
}
async function idbGet(key) {
  const db = await idbOpen();
  return new Promise((res, rej) => {
    const r = db.transaction('kv', 'readonly').objectStore('kv').get(key);
    r.onsuccess = () => res(r.result);
    r.onerror = () => rej(r.error);
  });
}
async function idbSet(key, val) {
  const db = await idbOpen();
  return new Promise((res, rej) => {
    const t = db.transaction('kv', 'readwrite');
    t.objectStore('kv').put(val, key);
    t.oncomplete = () => res();
    t.onerror = () => rej(t.error);
  });
}
function updateSaveLabel() {
  document.getElementById('saveDir').textContent =
    saveRoot ? '保存目录：' + saveRoot.name : '保存目录：未设置';
}
async function pickSaveRoot() {
  if (!('showDirectoryPicker' in window)) {
    toast('需要 Chrome / Edge 浏览器才能创建本地目录（File System Access API）');
    return;
  }
  try { saveRoot = await showDirectoryPicker({ mode: 'readwrite' }); } catch (_) { return; }
  try { await idbSet('saveRoot', saveRoot); } catch (_) {}
  updateSaveLabel();
  maybeScan(true);
  toast('已设置保存目录：' + saveRoot.name);
}
async function ensureRoot() {
  if (!saveRoot) {
    try { const h = await idbGet('saveRoot'); if (h) saveRoot = h; } catch (_) {}
  }
  if (saveRoot) {
    let p = 'prompt';
    try { p = await saveRoot.queryPermission({ mode: 'readwrite' }); } catch (_) {}
    if (p !== 'granted') {
      try { p = await saveRoot.requestPermission({ mode: 'readwrite' }); } catch (_) { p = 'denied'; }
    }
    if (p === 'granted') return saveRoot;
    saveRoot = null;
    if (p === 'denied') { toast('保存目录权限被拒绝 — 请点击「保存目录」重新选择'); return null; }
  }
  try {
    saveRoot = await showDirectoryPicker({ mode: 'readwrite' });
  } catch (_) { toast('已取消选择保存目录'); return null; }
  try { await idbSet('saveRoot', saveRoot); } catch (_) {}
  updateSaveLabel();
  return saveRoot;
}
async function fetchCoverBlob(d) {
  try {
    const r = await fetch('covers/' + d.cover);
    if (r.ok) return await r.blob();
  } catch (_) { /* file:// 下 fetch 被禁 → 用页面内嵌的 base64 封面 */ }
  const b64 = (typeof COVERS_B64 !== 'undefined' ? COVERS_B64 : {})[d.code];
  if (b64) {
    const bin = atob(b64);
    const bytes = new Uint8Array(bin.length);
    for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
    return new Blob([bytes], { type: b64.slice(0, 8) === 'iVBORw0K' ? 'image/png' : 'image/jpeg' });
  }
  throw new Error('封面字节不可用 — 请用 skill 重新生成页面（含内嵌封面）');
}
async function saveWorkCover(code, btn) {
  const d = DATA.find(x => x.code === code);
  if (!d) return;
  if (!d.cover) { toast('该作品没有封面图'); return; }
  if (!('showDirectoryPicker' in window)) {
    toast('需要 Chrome / Edge 浏览器才能创建本地目录（File System Access API）');
    return;
  }
  const old = btn.textContent;
  btn.disabled = true; btn.textContent = '创建中…';
  try {
    const root = await ensureRoot();
    if (!root) { btn.textContent = old; return; }
    maybeScan(false);
    const workName = folderNameOf(d);
    // create-if-missing at every level: existing folders are just walked into
    const actressDir = await root.getDirectoryHandle(ACTRESS_DIR, { create: true });
    const dir = await actressDir.getDirectoryHandle(workName, { create: true });
    const blob = await fetchCoverBlob(d);
    const ext = (d.cover.split('.').pop() || 'jpg').toLowerCase();
    const fh = await dir.getFileHandle('封面.' + ext, { create: true });
    const w = await fh.createWritable();
    await w.write(blob);
    await w.close();
    createdSet.add(code);
    btn.classList.add('ok');
    btn.textContent = '已创建 ✓';
    toast('已创建 ' + root.name + '\\' + ACTRESS_DIR + '\\' + workName + '\\封面.' + ext);
  } catch (err) {
    console.warn(err);
    btn.textContent = old;
    toast('创建失败：' + ((err && err.message) || err));
  } finally {
    btn.disabled = false;
  }
}

/* 获取更新: asks the --serve local server to check JavBus. The server does the
   minimal check first (listing pages only, 番号 diff); per-work requests happen
   only when there are new works, then the library files are rewritten and the
   page reloads. Unavailable from file:// — there is no server to call. */
async function refreshData() {
  if (location.protocol.indexOf('http') !== 0) {
    toast('获取更新需要经本地服务打开页面：python javbus_get_magnet.py --serve <本文件夹>');
    return;
  }
  const btn = document.getElementById('refresh');
  if (btn.disabled) return;
  btn.disabled = true;
  const old = btn.textContent;
  try {
    btn.textContent = '更新中…';
    const r = await fetch('api/refresh', { method: 'POST' });
    const j = await r.json().catch(() => ({}));
    if (!r.ok) throw new Error((j && j.error) || ('HTTP ' + r.status));
    if (j.updated) {
      btn.textContent = '已更新 ✓';
      toast('已更新：新增 ' + j.added + ' 部（' + j.codes.join('、') + '），正在刷新页面…');
      setTimeout(() => location.reload(), 1500);
      return;
    }
    toast('没有新作品' + (j.works ? '（共 ' + j.works + ' 部）' : '') + (j.note ? '：' + j.note : ''));
    setTimeout(() => { btn.textContent = old; }, 1500);
  } catch (e) {
    toast('更新失败：' + ((e && e.message) || e));
    setTimeout(() => { btn.textContent = old; }, 1500);
  } finally {
    btn.disabled = false;
  }
}

/* one-click batch: build every currently visible work's folder + cover.
   Runs sequentially (per-work FSA writes are cheap; parallel createWritable
   on one directory risks write conflicts), with live progress on the button
   and each card flipping to 已创建 ✓ as it lands. */
let savingAll = false;
async function saveAllWorks() {
  if (savingAll) return;
  const rows = visibleRows().filter(d => d.cover);
  if (!rows.length) { toast('当前显示的作品里没有带封面的，没法建目录'); return; }
  if (!('showDirectoryPicker' in window)) {
    toast('需要 Chrome / Edge 浏览器才能创建本地目录（File System Access API）');
    return;
  }
  const btn = document.getElementById('saveAll');
  savingAll = true;
  btn.disabled = true;
  const perBtns = Array.from(document.querySelectorAll('button.savebtn'));
  perBtns.forEach(b => { b.disabled = true; });
  let ok = 0, fail = 0;
  try {
    const root = await ensureRoot();
    if (!root) return;
    const actressDir = await root.getDirectoryHandle(ACTRESS_DIR, { create: true });
    for (let i = 0; i < rows.length; i++) {
      const d = rows[i];
      btn.textContent = '创建中 ' + (i + 1) + '/' + rows.length + '…';
      try {
        const dir = await actressDir.getDirectoryHandle(folderNameOf(d), { create: true });
        const blob = await fetchCoverBlob(d);
        const ext = (d.cover.split('.').pop() || 'jpg').toLowerCase();
        const fh = await dir.getFileHandle('封面.' + ext, { create: true });
        const w = await fh.createWritable();
        await w.write(blob);
        await w.close();
        createdSet.add(d.code);
        ok++;
      } catch (e) {
        console.warn(e);
        fail++;
      }
      applyCreatedState();
    }
    btn.textContent = '✓ 已创建 ' + ok + (fail ? '（' + fail + ' 失败）' : '');
    toast('完成：' + root.name + '\\' + ACTRESS_DIR + ' — ' + ok + ' 个目录已创建' + (fail ? '，' + fail + ' 个失败' : ''));
    setTimeout(() => { render(); }, 1600);
  } finally {
    savingAll = false;
    btn.disabled = false;
    perBtns.forEach(b => { b.disabled = false; });
    applyCreatedState();
  }
}

/* lightbox */
const lb = document.getElementById('lb');
function openLb(code) {
  const d = DATA.find(x => x.code === code);
  if (!d) return;
  const img = document.getElementById('lbImg');
  if (d.cover) { img.src = 'covers/' + d.cover; img.style.display = 'block'; } else { img.style.display = 'none'; }
  document.getElementById('lbCap').innerHTML = '<b>' + d.code + '</b> · ' + sizeTxt(d) + ' · ' + esc(d.title);
  const cp = document.getElementById('lbCopy');
  cp.hidden = !d.magnet;
  cp.dataset.m = d.magnet;
  const sp = document.getElementById('lbSave');
  sp.dataset.code = d.code;
  sp.disabled = !d.cover;
  const done = createdSet.has(d.code);
  sp.classList.toggle('ok', done);
  sp.textContent = done ? '已创建 ✓' : '建目录';
  lb.classList.add('open');
}
document.getElementById('lbCopy').addEventListener('click', e => {
  copyText(e.target.dataset.m); flash(e.target);
});
document.getElementById('lbSave').addEventListener('click', e => {
  if (e.target.disabled) return;
  saveWorkCover(e.target.dataset.code, e.target);
});
function closeLb() { lb.classList.remove('open'); }
document.getElementById('lbClose').addEventListener('click', closeLb);
document.getElementById('lbBack').addEventListener('click', closeLb);
document.addEventListener('keydown', e => { if (e.key === 'Escape') closeLb(); });

/* sort headers */
function bindSort(id, key) {
  const th = document.getElementById(id);
  const toggle = () => {
    if (state.key === key) state.dir = -state.dir; else { state.key = key; state.dir = 1; }
    for (const k of ['code', 'date', 'size']) {
      const el = document.getElementById('th-' + k);
      el.querySelector('.arr').textContent = state.key === k ? (state.dir === 1 ? '▲' : '▼') : '';
      el.setAttribute('aria-sort', state.key === k ? (state.dir === 1 ? 'ascending' : 'descending') : 'none');
    }
    render();
  };
  th.addEventListener('click', toggle);
  th.addEventListener('keydown', e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); toggle(); } });
}
bindSort('th-code', 'code');
bindSort('th-date', 'date');
bindSort('th-size', 'size');

/* theme toggle */
const root = document.documentElement;
const tbtn = document.getElementById('themeToggle');
function applyThemeIcon() {
  const dark = root.getAttribute('data-theme') === 'dark' ||
    (!root.hasAttribute('data-theme') && matchMedia('(prefers-color-scheme: dark)').matches);
  tbtn.textContent = dark ? '☀ 浅色' : '☾ 深色';
}
tbtn.addEventListener('click', () => {
  const cur = root.getAttribute('data-theme');
  const isDark = cur === 'dark' || (!cur && matchMedia('(prefers-color-scheme: dark)').matches);
  root.setAttribute('data-theme', isDark ? 'light' : 'dark');
  applyThemeIcon();
});
applyThemeIcon();

/* restore the remembered save directory (persisted in IndexedDB) so reopening
   the page shows/uses the previous configuration */
async function restoreSaveRoot() {
  try {
    const h = await idbGet('saveRoot');
    if (!h || typeof h.queryPermission !== 'function') return;
    let p = 'prompt';
    try { p = await h.queryPermission({ mode: 'readwrite' }); } catch (_) {}
    saveRoot = h;
    updateSaveLabel();
    if (p === 'granted') maybeScan(true);
  } catch (_) {}
}
restoreSaveRoot();

render();
</script>
</body>
</html>
"""


# ---------------------------------------------------------------------------
class JavBus:
    def __init__(self, cookie_file=DEFAULT_COOKIES, delay=0.4, rate=4.0):
        self.delay = delay
        # Global pacing: at most `rate` request starts per second across ALL
        # worker threads — this is what lets --workers > 1 run without tripping
        # the site's 429 limit. 429/503 responses additionally back off & retry.
        self.rate = max(0.1, rate)
        self._throttle_lock = threading.Lock()
        self._last_req = 0.0
        self.cj = MozillaCookieJar(cookie_file)
        if os.path.exists(cookie_file):
            try:
                self.cj.load(ignore_discard=True, ignore_expires=True)
            except Exception as e:
                print(f"[warn] could not load cookies from {cookie_file}: {e}", file=sys.stderr)
        # mtime of the jar as last read/written by THIS process — save() refuses to
        # clobber a jar another process (e.g. a running --serve) saved since then.
        self._jar_mtime = os.path.getmtime(cookie_file) if os.path.exists(cookie_file) else 0.0
        self.op = build_opener(HTTPCookieProcessor(self.cj))
        self.op.addheaders = [("User-Agent", UA)]

    def _throttle(self):
        """Global pacing: space request starts >= 1/rate seconds apart across all threads."""
        with self._throttle_lock:
            wait = self._last_req + 1.0 / self.rate - time.monotonic()
            if wait > 0:
                time.sleep(wait)
            self._last_req = time.monotonic()

    def _open(self, r):
        """Open a request with global pacing + 429/503 backoff. Backoff makes an
        aggressive --rate self-correcting instead of fatal (a 429 pauses ~3/6/12s
        and retries, so the run always completes, just at the site's real pace)."""
        for attempt in range(4):
            self._throttle()
            try:
                return self.op.open(r, timeout=40)
            except urllib.error.HTTPError as e:
                if e.code in (429, 503) and attempt < 3:
                    time.sleep(3 * (2 ** attempt))
                    continue
                raise

    def _req(self, url, data=None, headers=None, referer=None):
        h = {}
        if referer:
            h["Referer"] = referer
        if headers:
            h.update(headers)
        body = urllib.parse.urlencode(data).encode() if data else None
        r = Request(url, data=body, headers=h)
        with self._open(r) as resp:
            return resp.read().decode("utf-8", "replace")

    def get(self, url, referer=None, headers=None):
        return self._req(url, data=None, headers=headers, referer=referer)

    def post(self, url, data, referer=None):
        return self._req(url, data=data, referer=referer)

    def raw_get(self, url, referer=None):
        """Fetch a URL as raw bytes (images). get() utf-8 decodes and would
        corrupt binary payloads, so this bypasses the text path."""
        h = {}
        if referer:
            h["Referer"] = referer
        r = Request(url, headers=h)
        with self._open(r) as resp:
            return resp.read()

    def save(self):
        """Persist the jar (temp + replace) and never clobber a jar another
        process — e.g. a long-running --serve sharing the default cookies.txt —
        persisted in the meantime: an unconditional write would roll back the
        other's fresh session and force a redundant gate re-solve next run."""
        path = self.cj.filename
        tmp = f"{path}.save-{os.getpid()}-tmp"
        try:
            self.cj.save(tmp, ignore_discard=True, ignore_expires=True)
            if os.path.exists(path):
                cur_mtime = os.path.getmtime(path)
                if cur_mtime > self._jar_mtime:
                    with open(path, "rb") as f:
                        on_disk = f.read()
                    with open(tmp, "rb") as f:
                        ours = f.read()
                    if on_disk != ours:
                        # another process saved a different session — keep theirs
                        self._jar_mtime = cur_mtime
                        return
            os.replace(tmp, path)
            self._jar_mtime = os.path.getmtime(path)
        except Exception as e:
            print(f"[warn] could not save cookies: {e}", file=sys.stderr)
        finally:
            if os.path.exists(tmp):
                try:
                    os.remove(tmp)
                except OSError:
                    pass

    # -- auth --------------------------------------------------------------
    def _cookie(self, name):
        for c in self.cj:
            if c.name == name:
                return c.value
        return None

    def _looks_like_gate(self, html):
        return ("userAnswers" in html) or ("所在地區年齡檢測" in html) or ("driver-verify" in html)

    def parse_quiz(self, html):
        qs = []
        for m in re.finditer(r'<label for="answer">(.*?)</label>', html, re.S):
            blk = m.group(1)
            before = re.split(r'<br', blk, maxsplit=1)[0]
            qtext = re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', '', before)).strip()
            idm = re.search(r'name="userAnswers\[(\d+)]"', blk)
            opts = {}
            for om in re.finditer(r'value="([A-D])">\s*([A-D])\.\s*([^<]*?)<br', blk):
                opts[om.group(1)] = om.group(3).strip()
            if qtext or opts:
                qs.append({"id": idm.group(1) if idm else str(len(qs)), "q": qtext, "opts": opts})
        return qs

    def answer(self, q):
        for key, opttext in QUIZ_BANK.items():
            if key in q["q"]:
                for L, txt in q["opts"].items():
                    if opttext in txt or txt in opttext:
                        return L
        return None

    def ensure_auth(self, target, interactive=True):
        """Make sure we have a working session. Returns (ok, questions)."""
        try:
            probe = self.get(target)
        except urllib.error.HTTPError as e:
            if e.code != 404:
                raise
            # The target 404s (e.g. an unknown name in --name mode) — reaching it at
            # all means we are past the age gate; the caller handles the miss.
            return True, []
        if not self._looks_like_gate(probe):
            return True, []
        ref = urllib.parse.quote(target, safe="")
        # step 1: "I'm an adult" checkbox confirm
        try:
            self.post(f"{BASE}/doc/driver-verify?referer={ref}", {"Submit": "确认"}, referer=target)
        except Exception:
            pass
        # step 2: driving quiz (may need retries on a fresh random set)
        for attempt in range(12):
            page = self.get(f"{BASE}/doc/driver-verify?referer={ref}", referer=target)
            qs = self.parse_quiz(page)
            if not qs:
                return True, []
            ans = {q["id"]: self.answer(q) for q in qs}
            missing = [q for q in qs if ans[q["id"]] is None]
            if missing:
                if not interactive:
                    return False, qs
                ans = self.prompt_answers(qs)
            data = {"submit": "question"}
            for q in qs:
                data[f"userAnswers[{q['id']}]"] = ans[q["id"]]
            try:
                self.post(f"{BASE}/doc/driver-verify.php?referer={ref}", data, referer=target)
            except Exception:
                pass
            if self._cookie("dv") or self._cookie("age"):
                # confirm by re-probing the target (a 404 target is fine too)
                try:
                    still_gate = self._looks_like_gate(self.get(target))
                except urllib.error.HTTPError:
                    still_gate = False
                if not still_gate:
                    self.save()
                    return True, []
            time.sleep(self.delay)
        return False, qs

    def prompt_answers(self, qs):
        print("\n[age gate] Please answer these driving-test questions (A/B/C/D each):", file=sys.stderr)
        ans = {}
        for i, q in enumerate(qs, 1):
            print(f"\n  Q{i}. {q['q']}", file=sys.stderr)
            for L in ("A", "B", "C", "D"):
                if L in q["opts"]:
                    print(f"      {L}. {q['opts'][L]}", file=sys.stderr)
            while True:
                try:
                    a = input(f"  Q{i} answer> ").strip().upper()
                except EOFError:
                    print("\n[age gate] stdin closed — cannot answer interactively", file=sys.stderr)
                    sys.exit(3)
                if a in q["opts"]:
                    ans[q["id"]] = a
                    break
                print("   (enter A, B, C or D)", file=sys.stderr)
        return ans

    # -- catalog -----------------------------------------------------------
    def parse_star(self, html):
        works = []
        # The label part of a 番号 may contain digits (e.g. 3DSVR-1928). Re-releases
        # are listed with a "_YYYY-MM-DD" suffix on the same code; strip it to the base 番号.
        for m in re.finditer(
                r'class="movie-box" href="https://www\.javbus\.com/([A-Z0-9]+-\d+)(_\d{4}-\d{2}-\d{2})?"[^>]*>(.*?)</a>',
                html, re.S):
            code, blk = m.group(1), m.group(3)
            tm = re.search(r'<img [^>]*title="([^"]*)"', blk)
            title = htmllib.unescape(tm.group(1)).strip() if tm else ""
            dm = re.search(r'<date>\s*[A-Z0-9]+-\d+\s*</date>\s*/\s*<date>\s*([\d\-]+)\s*</date>', blk)
            works.append({
                "code": code, "title": title,
                "date": dm.group(1) if dm else "",
            })
        return works

    def catalog(self, star, max_pages=10):
        out, seen = [], set()
        for p in range(1, max_pages + 1):
            html = None
            for attempt in range(3):
                try:
                    html = self.get(f"{BASE}/star/{star}/{p}")
                    break
                except urllib.error.HTTPError as e:
                    if e.code == 404:
                        # Past the last page (or a transient blip): retry briefly, then stop.
                        time.sleep(self.delay)
                        continue
                    raise
            if html is None:
                break  # persistent 404: no more pages
            works = self.parse_star(html)
            if not works:
                break
            for w in works:
                if w["code"] not in seen:
                    seen.add(w["code"])
                    out.append(w)
            time.sleep(self.delay)
        return out

    # -- name -> star id ---------------------------------------------------
    def resolve_star(self, name):
        """Resolve an actress name to a star id via the site search.

        `GET /search/{name}` serves that actress's video list (404 if no match);
        the star id itself isn't on that page, so we read it off the first
        video's page. Returns the star id, or None if the name can't be resolved.
        """
        url = f"{BASE}/search/{urllib.parse.quote(name, safe='')}&type=&parent=ce"
        html = None
        for _ in range(3):
            try:
                html = self.get(url, referer=BASE)
                break
            except urllib.error.HTTPError as e:
                if e.code == 404:
                    return None  # the search 404s when a name has no match
                time.sleep(self.delay)
        if not html:
            return None
        codes = []
        for c in re.findall(r'href="https://www\.javbus\.com/([A-Z0-9]+-\d+)"', html):
            if c not in codes:
                codes.append(c)
        if not codes:
            return None
        time.sleep(self.delay)
        # The first listed video may be delisted — try a few before giving up.
        for code in codes[:5]:
            try:
                html = self.get(f"{BASE}/{code}")
            except Exception as e:
                print(f"  [warn] {code}: video page failed ({e})", file=sys.stderr)
                continue
            m = re.search(r"/star/([a-z0-9]+)", html)
            if m:
                return m.group(1)
            time.sleep(self.delay)
        return None

    # -- magnets -----------------------------------------------------------
    def video_meta(self, code):
        try:
            html = self.get(f"{BASE}/{code}")
        except Exception as e:
            # Network timeouts / SSL hiccups included: one bad work must not kill
            # the whole crawl — the catalog carries on and the page shows NO_GID.
            print(f"  [warn] {code}: video page failed ({e})", file=sys.stderr)
            return None, None, "0", code
        g = re.search(r'var gid = (\d+)', html)
        i = re.search(r"var img = '([^']*)'", html)
        u = re.search(r'var uc = (\d+)', html)
        title_m = re.search(r'<title>([^<]*?)\s*[-–]', html)
        title = htmllib.unescape(title_m.group(1)).strip() if title_m else code
        return (g.group(1) if g else None, i.group(1) if i else None,
                u.group(1) if u else "0", title)

    def fetch_magnets(self, code, gid, img, uc):
        url = (f"{BASE}/ajax/uncledatoolsbyajax.php?gid={gid}&lang=zh"
               f"&img={urllib.parse.quote(img or '', safe='')}&uc={uc}"
               f"&floor={random.randint(100, 999)}")
        try:
            html = self.get(url, referer=f"{BASE}/{code}",
                            headers={"X-Requested-With": "XMLHttpRequest"})
        except Exception as e:
            print(f"  [warn] {code}: magnet ajax failed ({e})", file=sys.stderr)
            return []
        rows, seen = [], set()
        for chunk in html.split("<tr")[1:]:
            mm = re.search(r'href="(magnet:[^"]+)"', chunk)
            if not mm:
                continue
            mag = mm.group(1)
            if mag in seen:
                continue
            seen.add(mag)
            sm = re.search(r'(\d+(?:\.\d+)?)\s*(GB|MB|TB)', chunk)
            size, mb = None, None
            if sm:
                val = float(sm.group(1))
                mb = val * {"GB": 1024, "MB": 1, "TB": 1048576}[sm.group(2)]
                size = f"{sm.group(1)}{sm.group(2)}"
            rows.append({"mag": mag, "size": size, "mb": mb, "hd": "包含高清HD" in chunk})
        return rows

    @staticmethod
    def _classify(mag, hd):
        # Match only against the human-readable name(s) (dn=/tr=/dl=) — the
        # 32-hex-char btih hash can contain substrings like "720" and would
        # otherwise pollute the classification. 1080 is checked before 720.
        names = re.findall(r'(?:dn|tr|dl)=([^&]*)', mag)
        name = urllib.parse.unquote(" ".join(names)) if names else mag
        if re.search(r'4[Kk]|2160', name):
            return "4K"
        if re.search(r'(?i)\b1080|FHD', name):
            return "1080p"
        if re.search(r'\b720', name):
            return "720p"
        return "1080p" if hd else "720p"

    def select(self, rows, prefer):
        b1080, b720 = [], []
        for r in rows:
            if r["mb"] is None:
                continue
            res = self._classify(r["mag"], r["hd"])
            (b1080 if res == "1080p" else b720).append(r)
        pool = (b720 or b1080) if prefer == "720" else (b1080 or b720)
        if not pool:
            sized = [r for r in rows if r["mb"] is not None]
            pool = sized
        if not pool:
            return None, None, None, None
        best = min(pool, key=lambda r: r["mb"])
        res = self._classify(best["mag"], best["hd"])
        if res not in ("1080p", "720p"):
            res = "4K/other"
        return best["size"], res, best["mag"], best["mb"]

    # -- covers -------------------------------------------------------------
    def download_cover(self, code, img, covers_dir):
        """Download the video's cover (the `img` var, e.g. /pics/cover/xxxx_b.jpg)
        to covers_dir/<CODE>.<ext>. Skips files already downloaded.
        Returns the file name, or None."""
        if not img:
            return None
        ext = os.path.splitext(img)[1] or ".jpg"
        fn = f"{code}{ext}"
        path = os.path.join(covers_dir, fn)
        if os.path.exists(path) and os.path.getsize(path) > 0:
            return fn
        try:
            data = self.raw_get(f"{BASE}{img}", referer=f"{BASE}/{code}")
        except Exception as e:
            print(f"  [warn] {code}: cover download failed ({e})", file=sys.stderr)
            return None
        if len(data) < 100 or (not data.startswith(b"\xff\xd8") and not data.startswith(b"\x89PNG")):
            print(f"  [warn] {code}: cover is not an image (got {len(data)} bytes)", file=sys.stderr)
            return None
        with open(path, "wb") as f:
            f.write(data)
        return fn


# ---------------------------------------------------------------------------
# Save-root ("建目录" target) persistence — the disk-based equivalent of the page
# button, for workflows where the browser's per-origin storage can't survive
# re-opening a file:// page.
def sanitize_folder_name(name, cap=120):
    """Mirror the page's folderNameOf: strip Windows-illegal chars, one space
    between runs, cap the length so path limits are respected."""
    name = re.sub(r'[\\/:*?"<>|]', '_', name)
    name = re.sub(r'\s+', ' ', name).strip(' .')
    return name[:cap] or "未命名"

def save_root_file():
    return os.path.normpath(os.path.join(HERE, "..", "save-root.json"))

def load_remembered_root():
    try:
        with open(save_root_file(), encoding="utf-8") as f:
            return json.load(f).get("root") or None
    except Exception:
        return None

def remember_root(root):
    try:
        with open(save_root_file(), "w", encoding="utf-8") as f:
            json.dump({"root": root}, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[warn] could not remember save root: {e}", file=sys.stderr)

def save_covers_to_root(dataset, covers_dir, root, label):
    """Create <root>/<女优名>/<番号 作品名>/封面.<ext> for every work, same naming
    rule as the page's 建目录 button (create-if-missing at each level). Returns the
    number of folders written."""
    os.makedirs(root, exist_ok=True)
    actress_dir = os.path.join(root, sanitize_folder_name(label))
    n = 0
    for d in dataset:
        if not d["cover"]:
            continue
        src = os.path.join(covers_dir, d["cover"])
        if not os.path.exists(src):
            continue
        folder = os.path.join(actress_dir, sanitize_folder_name(d["code"] + " " + (d["title"] or "")))
        os.makedirs(folder, exist_ok=True)
        ext = os.path.splitext(d["cover"])[1] or ".jpg"
        shutil.copy2(src, os.path.join(folder, "封面" + ext))
        n += 1
    return n


# ---------------------------------------------------------------------------
# Per-work pipeline (runs on worker threads).
def process_work(jb, w, covers_dir, prefer):
    """One work end-to-end: video page -> magnet ajax -> select -> cover.
    Returns (dataset_entry, magnets.txt line, status). Network hiccups on one
    work never abort the crawl: they degrade to a NO_GID / no-magnets row."""
    gid, img, uc, _t = jb.video_meta(w["code"])
    time.sleep(jb.delay)
    if not gid:
        d = {"code": w["code"], "series": w["code"].split("-")[0],
             "title": w["title"], "date": w["date"], "size": None,
             "gb": None, "res": None, "magnet": None, "cover": None}
        return d, f"{w['code']} | {w['title']} | NO_GID | -", f"{w['code']}: NO_GID"
    rows = jb.fetch_magnets(w["code"], gid, img, uc)
    size, res, mag, mb = jb.select(rows, prefer)
    cover = None
    if covers_dir and img:
        cover = jb.download_cover(w["code"], img, covers_dir)
    if not mag:
        line = f"{w['code']} | {w['title']} | no magnets | -"
        status = f"{w['code']}: no magnets"
    else:
        line = f"{w['code']} | {w['title']} | {size} ({res}) | {mag}"
        status = f"{w['code']}: {size} ({res})"
    d = {"code": w["code"], "series": w["code"].split("-")[0],
         "title": w["title"], "date": w["date"], "size": size,
         "gb": round(mb / 1024, 3) if mb else None, "res": res,
         "magnet": mag, "cover": cover}
    return d, line, status


def _atomic_write(path, text, encoding="utf-8", newline=None):
    """Write via temp file + os.replace so readers (the --serve static handler,
    a browser mid-fetch of index.html) never see a half-written file."""
    tmp = f"{path}.tmp-{os.getpid()}"
    try:
        with open(tmp, "w", encoding=encoding, newline=newline) as f:
            f.write(text)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            try:
                os.remove(tmp)
            except OSError:
                pass


def write_txt(path, label, works_n, res, lines):
    text = (f"JavBus magnet list — {label} — {works_n} works\n"
            f"Rule: smallest {res}p, else smallest other. Columns: 番号 | 标题 | 大小 | 磁力\n"
            + "=" * 60 + "\n"
            + "".join(ln + "\n" for ln in lines))
    _atomic_write(path, text)


def scrape_works(jb, works, covers_dir, res, workers):
    """Run the per-work pool over `works` (concurrent, globally rate-limited).
    Returns results re-ordered to input order as
    (dataset_entry, magnets.txt line, status) tuples."""
    results = {}
    done = 0
    lock = threading.Lock()

    def task(w):
        nonlocal done
        try:
            r = process_work(jb, w, covers_dir, res)
        except Exception as e:
            print(f"  [warn] {w['code']}: {e}", file=sys.stderr)
            r = ({"code": w["code"], "series": w["code"].split("-")[0],
                  "title": w["title"], "date": w["date"], "size": None,
                  "gb": None, "res": None, "magnet": None, "cover": None},
                 f"{w['code']} | {w['title']} | NO_GID | -", f"{w['code']}: error ({e})")
        with lock:
            done += 1
            n = done
        results[w["code"]] = r
        print(f"  [{n}/{len(works)}] {r[2]}")

    with ThreadPoolExecutor(max_workers=max(1, workers)) as ex:
        futs = [ex.submit(task, w) for w in works]
        for f in futs:
            f.result()
    return [results[w["code"]] for w in works]


def write_dataset(folder, label, star_id, scraped_at, res, dataset, covers_dir):
    """(Re)write data.json + index.html (covers base64-embedded) for a full
    dataset — used by both the initial scrape and live refreshes."""
    payload = json.dumps({
        "actress": {"label": label, "star": star_id, "scraped_at": scraped_at,
                    "rule": f"smallest {res}p, else smallest other",
                    "res": res,
                    "count": len(dataset),
                    "total_gb": round(sum(d["gb"] or 0 for d in dataset), 2)},
        "works": dataset,
    }, ensure_ascii=False, indent=2)
    _atomic_write(os.path.join(folder, "data.json"), payload)
    star_txt = (f'<span class="dim">star {star_id}</span>' if star_id
                else f'<span class="dim">{htmllib.escape(label)}</span>')
    # Base64-embed every cover so the page's 建目录 button can write cover files
    # from file://, where the browser blocks fetch/canvas reads of local files.
    covers_b64 = {}
    for d in dataset:
        if d["cover"]:
            cpath = os.path.join(covers_dir, d["cover"])
            if os.path.exists(cpath):
                with open(cpath, "rb") as cf:
                    covers_b64[d["code"]] = base64.b64encode(cf.read()).decode("ascii")
    page = (PAGE_TEMPLATE
            .replace("__DATA_JSON__", json.dumps(dataset, ensure_ascii=False).replace("</", "<\\/"))
            .replace("__COVERS_B64__", json.dumps(covers_b64))
            .replace("__ACTRESS__", json.dumps(label, ensure_ascii=False).replace("</", "<\\/"))
            .replace("__TITLE__", htmllib.escape(label))
            .replace("__SUB__", f"JavBus {star_txt} · 抓取日期 {scraped_at}"))
    _atomic_write(os.path.join(folder, "index.html"), page, newline="\n")


def refresh_library(folder, jb, max_pages=10, workers=8):
    """Minimal-check update: fetch ONLY the cheap listing pages, diff 番号s
    against data.json, and scrape only the new works (if any). On updates it
    rewrites data.json / magnets.txt / index.html in place. Returns a status
    dict for the page."""
    dj = os.path.join(folder, "data.json")
    with open(dj, "rb") as f:
        dj_before = f.read()  # snapshot — re-checked before writing back (below)
    data = json.loads(dj_before)
    star_id = data["actress"].get("star")
    if not star_id:
        raise RuntimeError("no star id in data.json — updates only work for actress datasets")
    res = data["actress"].get("res") or "1080"
    label = data["actress"]["label"]
    existing = data["works"]
    have = {d["code"] for d in existing}
    cat = jb.catalog(star_id, max_pages)
    if not cat:
        return {"updated": False, "works": len(existing), "note": "作品列表抓取失败，请稍后重试"}
    new_w = [w for w in cat if w["code"] not in have]
    if not new_w:
        return {"updated": False, "works": len(existing)}
    print(f"\n{label}: {len(new_w)} new work(s): {[w['code'] for w in new_w]}")
    covers_dir = os.path.join(folder, "covers")
    os.makedirs(covers_dir, exist_ok=True)
    scraped = scrape_works(jb, new_w, covers_dir, res, workers)
    # If another program (e.g. a full CLI re-scrape) rewrote data.json while we
    # were fetching, abort instead of clobbering the newer library.
    with open(dj, "rb") as f:
        if f.read() != dj_before:
            raise RuntimeError("资源库在刷新期间被其他程序修改（data.json 已变化），请重试")
    new_ds = [r[0] for r in scraped]
    dataset = new_ds + existing  # catalog order: newest first
    today = date.today().isoformat()
    with open(os.path.join(folder, "magnets.txt"), encoding="utf-8") as f:
        old_lines = {}
        for ln in f.read().splitlines():
            if " | " in ln:
                old_lines[ln.split(" | ", 1)[0]] = ln
    new_lines = {r[0]["code"]: r[1] for r in scraped}
    lines = [new_lines.get(d["code"]) or old_lines.get(d["code"])
             or f"{d['code']} | {d['title']} | NO_GID | -" for d in dataset]
    write_txt(os.path.join(folder, "magnets.txt"), label, len(dataset), res, lines)
    write_dataset(folder, label, star_id, today, res, dataset, covers_dir)
    jb.save()
    root = load_remembered_root()
    if root:
        save_covers_to_root(new_ds, covers_dir, root, label)
    return {"updated": True, "added": len(new_ds), "works": len(dataset),
            "codes": [d["code"] for d in new_ds]}


def write_launcher(folder):
    """Write 启动页面.bat into a dataset folder: double-click it to start the
    --serve local server (auto port) and open the page in the default browser.
    Written GBK+CRLF so the console-native codepage parses it correctly."""
    lines = [
        "@echo off",
        "rem JavBus-GetMagnet 资源库：本地服务方式打开页面（「获取更新」按钮可用）",
        "rem 停止服务：关闭本窗口（或按 Ctrl+C）",
        "set \"DIR=%~dp0\"",
        'if "%DIR:~-1%"=="\\" set "DIR=%DIR:~0,-1%"',
        f'python "{os.path.abspath(__file__)}" --serve "%DIR%" --open',
        "echo.",
        "pause",
    ]
    _atomic_write(os.path.join(folder, "启动页面.bat"), "\n".join(lines) + "\n",
                  encoding="gbk", newline="\r\n")


def serve_dir(folder, port, cookies, workers, rate, delay, max_pages, no_interactive, open_browser=False):
    """Serve a dataset folder (static files) plus POST /api/refresh — the page's
    获取更新 button. Only listing pages are fetched for the minimal check; new
    works are scraped only when there actually are some, then the library files
    are rewritten and the page reloads itself."""
    import http.server
    folder = os.path.abspath(folder).rstrip("\\/")
    dj = os.path.join(folder, "data.json")
    if not os.path.exists(dj):
        print(f"no data.json in {folder} — run the scrape first", file=sys.stderr)
        sys.exit(1)
    with open(dj, encoding="utf-8") as f:
        star_id = json.load(f)["actress"].get("star")
    jb = JavBus(cookie_file=cookies, delay=delay, rate=rate)
    if star_id:
        ok, qs = jb.ensure_auth(f"{BASE}/star/{star_id}", interactive=not no_interactive)
        if not ok:
            print("\nCould not clear the age gate automatically.", file=sys.stderr)
            for q in qs:
                print(f"  {q['q']}  ->  " + " / ".join(f"{L}.{t}" for L, t in sorted(q['opts'].items())), file=sys.stderr)
            sys.exit(3)
    refresh_lock = threading.Lock()

    class Handler(http.server.BaseHTTPRequestHandler):
        def _send(self, code, body, ctype):
            if isinstance(body, str):
                body = body.encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _json(self, code, obj):
            self._send(code, json.dumps(obj, ensure_ascii=False), "application/json; charset=utf-8")

        def do_GET(self):
            path = urllib.parse.urlsplit(self.path).path
            if path == "/api/status":
                try:
                    with open(dj, encoding="utf-8") as f:
                        d = json.load(f)
                except Exception:
                    return self._json(503, {"error": "data.json 正在被写入，请稍后重试"})
                return self._json(200, {"label": d["actress"]["label"], "star": d["actress"].get("star"),
                                        "works": d["actress"].get("count"), "scraped_at": d["actress"].get("scraped_at")})
            if path == "/":
                path = "/index.html"
            fp = os.path.normpath(os.path.join(folder, path.lstrip("/").replace("/", os.sep)))
            if not (fp == folder or fp.startswith(folder + os.sep)) or not os.path.isfile(fp):
                return self._send(404, "not found", "text/plain; charset=utf-8")
            ext = os.path.splitext(fp)[1].lower()
            ctype = {".html": "text/html; charset=utf-8", ".json": "application/json; charset=utf-8",
                     ".txt": "text/plain; charset=utf-8", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
                     ".png": "image/png", ".css": "text/css; charset=utf-8"}.get(ext, "application/octet-stream")
            with open(fp, "rb") as f:
                return self._send(200, f.read(), ctype)

        def do_POST(self):
            if urllib.parse.urlsplit(self.path).path != "/api/refresh":
                return self._json(404, {"error": "not found"})
            if not star_id:
                return self._json(400, {"error": "该资源库没有 star id，无法检查更新"})
            if not refresh_lock.acquire(blocking=False):
                return self._json(409, {"error": "另一次更新正在进行中"})
            try:
                r = refresh_library(folder, jb, max_pages, workers)
                return self._json(200, r)
            except Exception as e:
                print(f"[refresh error] {e}", file=sys.stderr)
                return self._json(500, {"error": str(e)})
            finally:
                refresh_lock.release()

        def log_message(self, fmt, *args):
            print("  " + (fmt % args))

    server = http.server.ThreadingHTTPServer(("127.0.0.1", port), Handler)
    url = f"http://localhost:{server.server_address[1]}/"
    # flush=True: when stdout is redirected to a file (the launcher bat polls
    # for the URL line), block buffering would keep it invisible for minutes.
    print(f"Serving {folder} at {url}  (Ctrl+C to stop)", flush=True)
    print(f"URL: {url}", flush=True)
    if open_browser:
        webbrowser.open(url)
    if not star_id:
        print("  note: dataset has no star id — 获取更新 will be unavailable")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


def main():
    # GBK (chcp 936) consoles can't print e.g. 瀬戸環奈 — force UTF-8 output.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass
    ap = argparse.ArgumentParser(description="Scrape JavBus magnet links + covers for an actress or a code.")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--star", help="actress star id, e.g. 138y")
    g.add_argument("--name", help="actress name, e.g. 瀬戸環奈 (resolved to a star id via the site search)")
    g.add_argument("--code", help="a single video code, e.g. SNOS-313")
    g.add_argument("--serve", metavar="DIR",
                   help="serve an existing dataset folder (with data.json) + the 获取更新 API; "
                        "open http://localhost:PORT/ in a browser")
    ap.add_argument("--port", type=int, default=0, help="port for --serve (default: OS-assigned)")
    ap.add_argument("--open", action="store_true",
                    help="with --serve: also open the page in the default browser")
    ap.add_argument("--outdir", help="folder mode output dir (default: ./<actress name or star id>)")
    ap.add_argument("--root", help="download root dir: after the run, create <root>/<女优名>/<番号 作品名>/封面 "
                    "for each work (remembered in save-root.json; later runs without --root reuse it)")
    ap.add_argument("--out", help="legacy: write only a single text file (no covers / no web page)")
    ap.add_argument("--res", choices=["1080", "720"], default="1080",
                    help="preferred resolution (default 1080; falls back to the other)")
    ap.add_argument("--max-pages", type=int, default=10, help="max star pages to crawl")
    ap.add_argument("--workers", type=int, default=8,
                    help="concurrent per-work scrapers (default 8; each worker is still paced by --delay)")
    ap.add_argument("--rate", type=float, default=4.0,
                    help="global request-rate cap in requests/second across all workers (default 4.0; "
                         "429 responses trigger automatic backoff+retry)")
    ap.add_argument("--delay", type=float, default=0.4,
                    help="seconds between a single work's own requests (default 0.4)")
    ap.add_argument("--cookies", default=DEFAULT_COOKIES, help="cookie file for session persistence")
    ap.add_argument("--no-interactive", action="store_true",
                    help="do not prompt for quiz answers; exit 3 if the gate can't be auto-cleared")
    a = ap.parse_args()

    if a.serve:
        serve_dir(a.serve, a.port, a.cookies, a.workers, a.rate, a.delay, a.max_pages,
                  a.no_interactive, a.open)
        return

    jb = JavBus(cookie_file=a.cookies, delay=a.delay, rate=a.rate)
    if a.star:
        target = f"{BASE}/star/{a.star}"
    elif a.name:
        target = f"{BASE}/search/{urllib.parse.quote(a.name, safe='')}"
    else:
        target = f"{BASE}/{a.code}"
    ok, qs = jb.ensure_auth(target, interactive=not a.no_interactive)
    if not ok:
        print("\nCould not clear the age gate automatically.", file=sys.stderr)
        print("Complete it in a browser (or answer the quiz) then re-run; "
              f"cookies are stored at {a.cookies} and reused next time.", file=sys.stderr)
        for q in qs:
            print(f"  {q['q']}  ->  " + " / ".join(f"{L}.{t}" for L, t in sorted(q['opts'].items())), file=sys.stderr)
        sys.exit(3)

    star_id = a.star
    if a.name:
        star_id = jb.resolve_star(a.name)
        if not star_id:
            print(f"No actress found for name: {a.name}", file=sys.stderr)
            sys.exit(4)
        print(f"Resolved '{a.name}' -> star {star_id}")
    multi = bool(star_id)  # star or name mode: we crawl a whole catalog
    if multi:
        works = jb.catalog(star_id, a.max_pages)
        label = (a.name or star_id)
    else:
        works = [{"code": a.code, "title": a.code, "date": ""}]
        label = a.code

    # output mode: --out means legacy single-file; otherwise a folder
    folder = None
    covers_dir = None
    if a.out:
        out_path = a.out
    else:
        folder = a.outdir or os.path.join(os.getcwd(), label)
        covers_dir = os.path.join(folder, "covers")
        os.makedirs(covers_dir, exist_ok=True)
        out_path = os.path.join(folder, "magnets.txt")

    lines = []
    dataset = []
    print(f"\n{label}: {len(works)} work(s)")
    # Per-work scraping runs on a worker pool (see scrape_works); results come
    # back in catalog order, so output files match the old serial run.
    for d, line, _status in scrape_works(jb, works, covers_dir, a.res, a.workers):
        dataset.append(d)
        lines.append(line)

    write_txt(out_path, label, len(works), a.res, lines)
    print(f"\nWrote {len(lines)} line(s) to {out_path}")

    if folder:
        write_dataset(folder, label, star_id, date.today().isoformat(), a.res, dataset, covers_dir)
        write_launcher(folder)
        n_covers = sum(1 for d in dataset if d["cover"])
        print(f"Folder: {folder}")
        print(f"  covers: {n_covers}/{len(dataset)} in {covers_dir}")
        print(f"  page:   {os.path.join(folder, 'index.html')}")
        root = a.root or load_remembered_root()
        if a.root:
            remember_root(a.root)
        if root:
            n_saved = save_covers_to_root(dataset, covers_dir, root, label)
            print(f"  saved:  {n_saved}/{len(dataset)} cover folders under {root}{os.sep}{label}")
    jb.save()


if __name__ == "__main__":
    main()
