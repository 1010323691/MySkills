# -*- coding: utf-8 -*-
"""movie-magnet-hunt: find magnets for a list of movies across sidhub/fanhaolou/6vw.

Usage:
  python -X utf8 hunt.py --list movies.json --outdir run [--per-movie 1]
                         [--top 3] [--priority subs|res] [--fhl-pages 2]

movies.json:
  [
    {"no": 1, "cn": "闪烁的爱情", "year": 2015, "country": "日本",
     "keywords": {"sidhub": ["闪烁的爱情", "Strobe Edge"],
                  "fhl": ["Strobe Edge", "Strobe.Edge"],
                  "vw": "闪烁的爱情"},
     "type": "movie"}
  ]

Outputs into --outdir:
  results/<no>.json   full per-movie detail (candidates, picks, magnets, warnings)
  资源清单.md          human report
  magnets.txt         the final answer: one (or --per-movie N) magnet per movie
  summary on stdout:  one line per movie (status | pick name | size)

Exit code: 0 normally; 1 if any movie ends with zero magnets AND --strict.
"""
import argparse, json, os, re, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sites

# ---------------- scoring rules (the decision rules, enforced in code) ----------------

RES_ORDER = [('2160', 3), ('1440', 2), ('1080', 2), ('1280', 1), ('720', 1),
             ('960', 0), ('864', 0), ('480', 0), ('640', 0)]
SUBS_CN = ['中字', '中文字幕', '内封中字', '简繁', '中英双字', '中日双字', '中日双',
           'CHS', 'Chi_Jap', 'CHI_JPN', '国语中字', '国语配音', '双语']
SUBS_NONE = ['无字', 'no-sub', 'nosub', '无字幕']
SUBS_ORIG = ['JAPANESE', 'KOREAN', '日字', '韩字', '日韓', 'Japanese']
ANIME_RE = re.compile(r's\d{1,2}\s*e\d{1,3}|ep\d{2,3}|oad|ova|season|第.{0,4}话', re.I)

def res_tier(name):
    n = name.lower()
    for k, v in RES_ORDER:
        if k in n:
            return v
    return 0

def subs_tier(name):
    if any(k.lower() in name.lower() for k in SUBS_NONE):
        return 0
    if any(k in name for k in SUBS_CN) or any(k.lower() in name.lower() for k in ['chs', 'chi_jap']):
        return 2
    if any(k in name for k in SUBS_ORIG):
        return 1
    return 1  # unknown: treat as "not guaranteed Chinese" but not worse than original

def recency_score(date):
    """sidhub 'YYYY-MM-DD …' or fhl relative age -> 0..2"""
    if not date:
        return 0
    m = re.search(r'(20\d\d)', date)
    if m:
        y = int(m.group(1))
        return 2 if y >= 2026 else (1 if y >= 2025 else 0)
    if '天' in date:
        return 2
    if '周' in date:
        return 1
    return 0

def size_gb(name, size):
    s = (size or '') + ' ' + (name or '')
    m = re.search(r'(\d+(?:\.\d+)?)\s*(TB|GB|G|MB|M|KB)\b', s, re.I)
    if not m:
        return 999.0
    v = float(m.group(1))
    return v * {'TB': 1024, 'GB': 1, 'G': 1, 'MB': 0.001, 'M': 0.001, 'KB': 0.000001}[m.group(2).upper()]

def year_ok(name, movie):
    """True unless the release name states a 4-digit year different from the expected one."""
    y = movie.get('year')
    if not y:
        return True
    m = re.search(r'(19\d{2}|20\d{2})', name)
    return not m or int(m.group(1)) == y


def score(cand, movie, priority):
    r, s, rc = cand['res'], cand['subs'], cand['rec']
    y = year_ok(cand['name'], movie)
    if priority == 'res':
        key = (y, r, s == 2, rc, -cand['gb'])
    else:  # 'subs'
        key = (y, s == 2, r, rc, -cand['gb'])
    cand['score'] = key
    return key

# ---------------- per-movie pipeline ----------------

def gather(movie):
    kw = movie['keywords']
    cands, warnings = [], []
    no = movie['no']
    # --- sidhub ---
    covers, seen = [], set()
    for k in kw.get('sidhub', []):
        try:
            for c in sites.sidhub_search(k):
                if c['url'] not in seen:
                    seen.add(c['url'])
                    c['kw'] = k
                    covers.append(c)
        except Exception as e:
            warnings.append('sidhub search %r failed: %r' % (k, e))
    if not covers:
        warnings.append('sidhub: not indexed under any keyword')
    else:
        cn = movie.get('cn', '')
        def cover_rank(c):
            t, meta = c['title'], c.get('meta_line', '')
            s = (cn.split('(')[0] in t) * 3 + (c['kw'] in t) * 2
            if movie.get('country') and movie['country'] in meta:
                s += 2
            if movie.get('year') and str(movie['year']) in meta:
                s += 2
            return s
        covers.sort(key=cover_rank, reverse=True)
        for c in covers[:3]:
            try:
                info = sites.sidhub_movie(c['url'])
            except Exception as e:
                warnings.append('sidhub movie page %s failed: %r' % (c['url'], e))
                continue
            if info['title'] and cn and cn.split('(')[0] not in info['title'] and c['kw'] not in info['title']:
                continue  # wrong movie (same-name) - skip, don't pollute candidates
            movie_douban = info.get('douban_url')
            for s in info['seeds']:
                cands.append({
                    'no': no, 'src': 'sidhub', 'name': s['name'], 'size': s['size'],
                    'gb': size_gb(s['name'], s['size']), 'date': s['date'],
                    'rec': recency_score(s['date']), 'page': s['url'],
                    'douban': movie_douban, 'cover': c,
                })
    # --- fanhaolou ---
    fseen = set()
    for k in kw.get('fhl', []):
        try:
            for it in sites.fhl_search(k, pages=int(os.environ.get('FHL_PAGES', '2'))):
                if it['url'] in fseen:
                    continue
                fseen.add(it['url'])
                low = it['title'].lower()
                anime = movie.get('type') == 'movie' and bool(ANIME_RE.search(it['title']))
                cands.append({
                    'no': no, 'src': 'fanhaolou', 'name': it['title'], 'size': it['size'],
                    'gb': size_gb(it['title'], it['size']), 'age': it['age'],
                    'rec': recency_score(it['age']), 'page': it['url'],
                    'anime_suspect': anime,
                })
        except Exception as e:
            warnings.append('fanhaolou search %r failed: %r' % (k, e))
    # --- 6vw (record only) ---
    try:
        res = sites.vw_search(kw.get('vw', '')) if kw.get('vw') else []
        if res:
            art = sites.vw_article(res[0][0])
            movie['vw'] = {'result': res[:5], 'article': art}
            for p in art.get('pans', []):
                cands.append({'no': no, 'src': '6vw', 'name': p, 'size': '', 'gb': 999.0,
                              'rec': 0, 'page': 'https://www.6vw.cc' + res[0][0], 'stale_pan': True})
        else:
            movie['vw'] = {'result': []}
    except Exception as e:
        warnings.append('6vw search failed: %r' % e)
    return cands, warnings

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--list', required=True)
    ap.add_argument('--outdir', default='hunt_out')
    ap.add_argument('--per-movie', type=int, default=1, help='magnets per movie in magnets.txt')
    ap.add_argument('--top', type=int, default=3, help='candidates per movie for which we fetch real magnets')
    ap.add_argument('--priority', default='subs', choices=['subs', 'res'])
    ap.add_argument('--strict', action='store_true')
    a = ap.parse_args()
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass
    movies = json.load(open(a.list, encoding='utf-8'))
    os.makedirs(os.path.join(a.outdir, 'results'), exist_ok=True)

    md = ['# 资源清单（movie-magnet-hunt 生成）', '',
          '# 筛选优先级：' + ('字幕优先（1080p 中文字幕优先）' if a.priority == 'subs' else '分辨率优先')]
    mtxt = []
    empty = 0
    for movie in movies:
        no, cn = movie['no'], movie.get('cn', '?')
        cands, warnings = gather(movie)
        # tag & score
        for c in cands:
            c['res'] = res_tier(c['name'])
            c['subs'] = subs_tier(c['name'])
        # relevance guard: same-title different movie (anime vs film, 2021 vs 2018) demoted
        for c in cands:
            if c.get('anime_suspect'):
                c['score'] = (0, 0, 0, 0, 0)
            else:
                score(c, movie, a.priority)
        cands = [c for c in cands if c.get('score') is not None]
        cands.sort(key=lambda c: c['score'], reverse=True)
        picks = cands[:a.top]
        # fetch real magnets for picks
        for p in picks:
            try:
                if p['src'] == 'sidhub':
                    m = sites.sidhub_magnet(p['page'])
                elif p['src'] == 'fanhaolou':
                    m = sites.fhl_magnet(p['page'])
                else:
                    continue
                p['magnet'] = m['magnet']
                p['full_title'] = m.get('full_title')
                if p['magnet'] and movie.get('year'):
                    ys = str(movie['year'])
                    if ys not in (p['name'] + ' ' + (p.get('full_title') or '')):
                        p['warning'] = 'year %s not in release name - verify manually' % ys
            except Exception as e:
                p['magnet_error'] = repr(e)
                warnings.append('magnet fetch failed for %s: %r' % (p['name'][:40], e))
        good = [p for p in picks if p.get('magnet') and re.match(r'magnet:\?xt=urn:btih:[0-9a-f]{40}', p['magnet'])]
        if not good:
            empty += 1
        json.dump({'movie': movie, 'picks': picks, 'all_candidates': cands[:25], 'warnings': warnings},
                  open(os.path.join(a.outdir, 'results', '%02d.json' % no), 'w', encoding='utf-8'),
                  ensure_ascii=False, indent=1)
        # report lines
        md.append('## %s. %s%s' % (no, cn, ('（%s，%s）' % (movie['year'], movie['country'])) if movie.get('year') else ''))
        for p in picks:
            tag = ('1080p' if p['res'] == 2 else '2160p' if p['res'] == 3 else str(p['res'])) + ' / ' + \
                  ('中字' if p['subs'] == 2 else '日/韩/原字?' if p['subs'] == 1 else '无字')
            md.append('- [%s] %s  %s（%s）' % (p['src'], p['name'][:90], tag, p['size']))
            if p.get('magnet'):
                md.append('  `magnet` ' + p['magnet'])
            md.append('  来源页: ' + p['page'])
            for w in [p.get('warning'), p.get('magnet_error')]:
                if w:
                    md.append('  ⚠ ' + w)
        if movie.get('vw', {}).get('article', {}).get('pans'):
            md.append('- 6V 旧网盘链接（大概率失效，仅记录）: ' + ' | '.join(movie['vw']['article']['pans'][:3]))
        if warnings:
            md.append('警告: ' + '；'.join(warnings[:4]))
        md.append('')
        # magnets.txt: top --per-movie GOOD picks
        for p in good[:a.per_movie]:
            mtxt.append('# %s %s (%s)' % (no, cn, p['src']))
            mtxt.append(p['magnet'])
        print('%02d %-16s %s' % (no, cn,
              ('OK | ' + good[0]['name'][:50] + ' | ' + good[0]['size']) if good
              else 'NO MAGNET (see results/%02d.json)' % no))
    open(os.path.join(a.outdir, '资源清单.md'), 'w', encoding='utf-8').write('\n'.join(md))
    open(os.path.join(a.outdir, 'magnets.txt'), 'w', encoding='utf-8').write('\n'.join(mtxt) + '\n')
    print('done: %d movies, %d without magnets -> %s' % (len(movies), empty, a.outdir))
    if empty and a.strict:
        sys.exit(1)

if __name__ == '__main__':
    main()
