# -*- coding: utf-8 -*-
"""Verified site adapters for movie-magnet-hunt. All patterns proven 2026-10-07.

Sites:
  sidhub.cc   catalog + PT magnet redirects  (search: /s/<kw>/)
  fanhaolou.com  global magnet index          (search: /search/<hex>-<page>-id.html)
  6vw.cc      6V movie blog, old posts        (ZBLOG POST search, gb18030)

Non-negotiable rules baked in here (do not remove):
  * sidhub needs Referer: https://sidhub.cc/ on movie/link pages or you get 403.
  * Non-ASCII query strings must be percent-encoded before urllib sees them
    (urllib raises UnicodeEncodeError otherwise).
  * quote_from_bytes() returns STR in py3 -> .encode('ascii') before byte concat.
  * 6vw.cc ZBLOG search: tbname MUST be 'Article' and show='title,smalltext',
    body encoded gb18030. (tbname=blog returns "没有搜索到" for everything.)
  * Be polite: global 0.3s delay between all requests.
"""
import urllib.request, urllib.parse, re, time, base64

UA = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36'}
DELAY = 0.3
_last = [0.0]


def _fix_url(url):
    """urllib rejects non-ASCII in URLs; percent-encode the query part."""
    if all(ord(c) < 128 for c in url):
        return url
    base, _, query = url.partition('?')
    if not query:
        return url
    return base + '?' + urllib.parse.quote(query, safe='=&%')


def get(url, referer=None, data=None, encoding='utf-8'):
    t = time.time()
    wait = DELAY - (t - _last[0])
    if wait > 0:
        time.sleep(wait)
    _last[0] = time.time()
    hdrs = dict(UA)
    if referer:
        hdrs['Referer'] = referer
    if data is not None:
        hdrs['Content-Type'] = 'application/x-www-form-urlencoded'
    url = _fix_url(url)
    req = urllib.request.Request(url, data=data, headers=hdrs)
    raw = urllib.request.urlopen(req, timeout=30).read()
    return raw.decode(encoding, 'ignore')


# ---------------- sidhub.cc ----------------

def sidhub_search(kw):
    """Search /s/<kw>/ -> list of cover dicts (title, url, douban_url, meta line).
    NOTE: sidhub's index is PARTIAL - a valid movie can have zero results.
    Callers must try multiple keyword variants before concluding "not indexed"."""
    h = get('https://sidhub.cc/s/' + urllib.parse.quote(kw) + '/', referer='https://sidhub.cc/')
    covers = []
    for m in re.finditer(r'<div class="cover">\s*<a[^>]*title="([^"]*)"[^>]*href="(/movies/\d+/)"[^>]*>.*?</a>\s*<ul>(.*?)</ul>', h, re.S):
        title, url, body = m.groups()
        li = re.findall(r'<li>(.*?)</li>', body, re.S)
        covers.append({
            'title': title,
            'url': 'https://sidhub.cc' + url,
            'meta_line': re.sub(r'<[^>]+>', '', li[0]).strip() if li else '',  # "2015 / 电影 / 日本 / 日语 / 主演…"
            'douban_url': (re.search(r'(https://movie\.douban\.com/subject/\d+/)', body) or [None, None])[1] if body else None,
        })
    return covers


def sidhub_movie(url):
    """Movie page -> {title, douban_url, meta{}, seeds[{name,size,feat,date,url}]}."""
    h = get(url, referer='https://sidhub.cc/')
    title = re.search(r'<title>(.*?) - SeedHub', h)
    seeds = []
    for m in re.finditer(r'<li>\s*<a[^>]*title="([^"]*)"[^>]*href="(/link_start/\?seed_id=\d+[^"]*)"[^>]*>.*?</a>\s*/\s*<code class="size">([^<]*)</code>(.*?)</li>', h, re.S):
        name, href, size, tail = m.groups()
        seeds.append({
            'name': name,
            'size': size.strip(),
            'feat': ' '.join(re.findall(r'code class="seed-feature">([^<]+)<', tail)),
            'date': (re.search(r'create-time[^>]*>([^<]+)<', tail) or [None, None])[1] or '',
            'url': 'https://sidhub.cc' + href,
        })
    meta = {}
    for k in ('上 映', '上映日期', '年 代', '地 区'):
        m = re.search(k + r'\s*([^<\n]{1,40})', h)
        if m:
            meta[k.strip()] = m.group(1).strip()
    _d = re.search(r'(https://movie\.douban\.com/subject/\d+/)', h)
    return {
        'title': title.group(1) if title else '',
        'douban_url': _d.group(1) if _d else None,
        'meta': meta,
        'seeds': seeds,
    }


def sidhub_magnet(seed_url):
    """link_start page embeds the magnet as base64:  const data = "<b64>";  decode it."""
    h = get(seed_url, referer='https://sidhub.cc/')
    m = re.search(r'const data = "([A-Za-z0-9+/=]+)"', h)
    magnet = base64.b64decode(m.group(1)).decode('utf-8', 'ignore') if m else None
    return {'magnet': magnet, 'full_title': (re.search(r'<title>(.*?) - SeedHub', h) or [None, None])[1]}


# ---------------- fanhaolou.com ----------------

def fhl_search(kw, pages=2):
    """Keyword search. Accepts ANY language (Chinese/Japanese/Korean/English):
    the keyword is UTF-8-hex encoded into the URL (identical to plain hex for
    pure-ASCII words). Substring match, 10 items/page.
    Chinese keywords are NOT redundant: many releases (e.g. Chinese-release
    groups) are findable ONLY by the Chinese/native title. Returns
    [{title,size,age,seeds,url,files}].
    WARNING: the 'files' (flist) on search pages frequently belong to a NEIGHBORING
    torrent - never use flist to assert a torrent's contents; verify via the item
    title / magnet dn or the detail page."""
    items = []
    for p in range(1, pages + 1):
        h = get('https://www.fanhaolou.com/search/' + kw.encode('utf-8').hex() + '-%d-id.html' % p)
        if len(h) < 3000 and '没有找到' in h:
            break
        for m in re.finditer(r"<dl class='item'>.*?<a href='(/hash/[0-9a-f]+\.html)'[^>]*>(.*?)</a>.*?<dd class='attr'>(.*?)</dd>.*?<dd class='flist'>(.*?)</dd>", h, re.S):
            url, title, attr, files = m.groups()
            g = lambda pat: (re.search(pat, attr) or [None, None])[1]
            items.append({
                'title': re.sub(r'<[^>]+>', '', title).strip(),
                'size': g(r'文件大小:<b>([^<]+)</b>') or '',
                'age': g(r'收录时间:<b>([^<]+)</b>') or '',
                'seeds': g(r'做种:<b>([^<]+)</b>') or '',
                'url': 'https://www.fanhaolou.com' + url,
                'files': [re.sub(r'<[^>]+>', '', f).strip() for f in re.findall(r"<li>(.*?)</li>", files, re.S)],
            })
    return items


def fhl_magnet(hash_url):
    """Hash detail page contains the magnet directly in an <a href>. No file list
    is shown there either - the listing title IS the torrent name."""
    h = get(hash_url, referer='https://www.fanhaolou.com/')
    m = re.search(r"href='(magnet:\?[^']+)'", h) or re.search(r'href="(magnet:\?[^"]+)"', h)
    title = (re.search(r'name="description" content="([^"]*)的番号', h) or [None, None])[1]
    return {'magnet': m.group(1) if m else None, 'full_title': title}


# ---------------- 6vw.cc (6V, the active mirror of 6vdyy.com) ----------------

def vw_search(kw):
    """ZBLOG search. Params MUST be show=title,smalltext & tempid=1 & tbname=Article,
    body gb18030. Returns [(article_path, title)]. Fuzzy match over titles."""
    body = (b'keyboard=' + urllib.parse.quote_from_bytes(kw.encode('gb18030')).encode('ascii')
            + b'&show=title,smalltext&tempid=1&tbname=Article')
    h = get('https://www.6vw.cc/e/search/index.php', referer='https://www.6vw.cc/',
            data=body, encoding='gb18030')
    return [(u, t.strip()) for u, t in re.findall(r'href="(/[a-z0-9]+/[0-9-]+/[0-9]+\.html)"[^>]*>([^<]{3,60})', h)]


def vw_article(path):
    """Old 6V posts contain Baidu/pan links that are almost always dead for
    pre-2023 movies. Use for RECORDING only, never as the primary result."""
    h = get('https://www.6vw.cc' + path, referer='https://www.6vw.cc/', encoding='gb18030')
    meta = {}
    for k in ('译 名', '片 名', '年 代', '地 区', '语 言', '字 幕'):
        m = re.search(k + r'\s*([^<\n]{1,60})', h)
        if m:
            meta[k] = m.group(1).strip()
    return {
        'meta': meta,
        'magnets': sorted(set(re.findall(r'magnet:\?[^"<\s]+', h)))[:6],
        'pans': sorted(set(re.findall(r'https?://[^\s<"]*(?:pan\.baidu|quark\.cn|alipan|115\.com|lanzou|123pan|weiyun|189)[^\s<"]*', h)))[:6],
        'file_names': re.findall(r'<a[^>]*>([^<]*\.(?:mkv|mp4|avi|rmvb|mov)[^<]*)</a>', h)[:8],
    }
