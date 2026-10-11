# -*- coding: utf-8 -*-
"""movie-magnet-hunt: normalize a raw movie list via TMDB (api.themoviedb.org/3).

Takes raw titles (any language, user-typed, possibly non-canonical, with or
without embedded years) and produces a movies.json DRAFT for hunt.py:
canonical CN / original / EN titles, year, country, full 'names' list and
per-site 'keywords' - exactly the fields hunt.py's homonym hard-filter needs.
Top cast (from /credits) is included to help the agent pick the right work
when a search is ambiguous (same-title film vs series, different years).

Credentials (system environment variables - NEVER hardcode or print them):
  TMDB_API_KEY    API key: legacy (works as ?api_key=) or new-style (Bearer)
  TMDB_API_TOKEN  current API token (Authorization: Bearer)
Auth modes are tried in order: token Bearer -> key ?api_key= -> key Bearer;
a 401 (expired JWT, new-style key sent as api_key=) advances to the next.
For the verified endpoint chain and per-field pitfalls (search/multi en-US ->
movie/tv details zh-CN with origin_country -> credits), see the
"TMDB API 使用链路" section of SKILL.md - every field note there is tested.

Usage:
  python -X utf8 tmdb_normalize.py --titles raw_titles.txt --out movies.json
  python -X utf8 tmdb_normalize.py --list raw.json --out movies.json
  python -X utf8 tmdb_normalize.py --list raw.json     (agent pre-picked the
        work from an ambiguous candidate list: entries carry 'tmdb_id' +
        'cn' + 'type' + 'en'; year/country/names/keywords/cast are filled in)

Input lines (--titles): one title per line; '#' starts a comment; a (2018) or
  (2018年) year hint at the end of a line is stripped and used to filter
  candidates. The script NEVER guesses: a title auto-approves only when it
  EXACTLY matches (normalized) one of the work's zh/en/original titles, so
  both multi-candidate searches AND unique-but-fuzzy matches (复仇(2018) ->
  果戈里·复仇) come back as 'ambiguous' for the agent to resolve by
  re-querying with a more specific title (usually the original-language
  title + the (year) hint).

Output entry (movies.json draft, consumed by hunt.py):
  {"no": 1, "cn": ..., "year": ..., "country": ..., "type": "movie",
   "names": [cn, original, en, ...],
   "keywords": {"sidhub": [...], "fhl": [...], "vw": ...},
   "tmdb_id": 441591, "top_cast": ["..."], "tmdb_source": "tmdb"}
Entries that could not be normalized carry "tmdb_source": "manual" and are
left out of the draft - fill them in by hand (SKILL.md step 1 fallback).

--out merge: if the --out file already holds a draft (JSON array of entries),
entries with the same 'no' are replaced and the rest kept, so the second
(ambiguous-fill) run does not wipe the first run's ok entries. "no" values
must be unique integers; the script rejects missing/non-integer ones.

Requests: 1 search + (for each ok entry) 1 details + 1 credits. ~36 for a
12-title list - far below TMDB rate limits, keep the 0.3s courtesy pace.
"""
import argparse, json, os, re, sys, urllib.error, urllib.parse, urllib.request

UA = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36'}
BASE = 'https://api.themoviedb.org/3'
# production_countries ISO -> Chinese, for hunt.py's 'country' field and for
# sidhub cover-meta country matching (meta lines read like "2015 / 电影 / 日本").
COUNTRY_ZH = {
    'US': '美国', 'GB': '英国', 'FR': '法国', 'DE': '德国', 'IT': '意大利', 'ES': '西班牙',
    'CA': '加拿大', 'MX': '墨西哥', 'BR': '巴西', 'AR': '阿根廷',
    'JP': '日本', 'KR': '韩国', 'CN': '中国大陆', 'HK': '中国香港', 'TW': '中国台湾',
    'IN': '印度', 'TH': '泰国', 'MY': '马来西亚', 'SG': '新加坡', 'AU': '澳大利亚',
    'NL': '荷兰', 'BE': '比利时', 'SE': '瑞典', 'DK': '丹麦', 'NO': '挪威',
    'FI': '芬兰', 'IE': '爱尔兰', 'CH': '瑞士', 'AT': '奥地利', 'TR': '土耳其',
    'IL': '以色列', 'EG': '埃及', 'ZA': '南非', 'RU': '俄罗斯',
}

_creds_cache = [None]


def creds():
    """(token, api_key) from the environment, resolved once."""
    if _creds_cache[0] is None:
        _creds_cache[0] = (os.environ.get('TMDB_API_TOKEN') or None,
                           os.environ.get('TMDB_API_KEY') or None)
    return _creds_cache[0]


def _api(path, params):
    """GET a TMDB v3 endpoint, JSON-decoded. Auth modes are tried in order:
    token as Bearer, then key as ?api_key= (legacy), then key as Bearer
    (new-style keys). A 401 means the mode is rejected (expired JWT, or a
    new-style key sent as api_key=), so the next mode is tried. Other
    non-2xx raise RuntimeError with the status + TMDB's own message."""
    token, key = creds()
    modes = []
    if token:
        modes.append(('Bearer ' + token, {}))
    if key:
        modes.append((None, {'api_key': key}))
        modes.append(('Bearer ' + key, {}))
    if not modes:
        raise RuntimeError('no TMDB credentials: set TMDB_API_KEY and/or TMDB_API_TOKEN')
    last = None
    for auth, extra in modes:
        p = dict(params, **extra)
        hdrs = dict(UA)
        if auth:
            hdrs['Authorization'] = auth
        url = BASE + path + '?' + urllib.parse.urlencode(p)
        if not all(ord(c) < 128 for c in url):
            base, _, q = url.partition('?')
            url = base + '?' + urllib.parse.quote(q, safe='=&%')
        req = urllib.request.Request(url, headers=hdrs)
        try:
            raw = urllib.request.urlopen(req, timeout=30).read()
            return json.loads(raw.decode('utf-8'))
        except urllib.error.HTTPError as e:
            body = e.read().decode('utf-8', 'ignore')[:200]
            last = 'TMDB %s -> %s %s: %s' % (path, e.code, e.reason, body)
            if e.code != 401:
                raise RuntimeError(last)
        except (OSError, json.JSONDecodeError) as e:
            # network-layer failures (DNS/refused, ssl.SSLError, socket.timeout
            # on all Python versions, corrupt body): surface as RuntimeError so
            # callers' error paths apply; HTTPError (an OSError subclass) is
            # handled above first
            raise RuntimeError('TMDB %s request failed: %r' % (path, e))
    raise RuntimeError(last)


def _pick(d, keys):
    for k in keys:
        v = d.get(k)
        if v:
            return v
    return None


def _year_of(d):
    date = _pick(d, ('release_date', 'first_air_date')) or ''
    m = re.match(r'(19\d{2}|20\d{2})', date)
    return int(m.group(1)) if m else None


def _country_zh(d):
    # search results carry iso_code, /<id> details carry name only
    pc = d.get('production_countries') or []
    if not pc:
        return ''
    first = pc[0]
    return COUNTRY_ZH.get(first.get('iso_code'), first.get('name', ''))


def _names(cn, original, en):
    """All distinct canonical spellings, longest first (hunt.py matches
    longest-first; the CN title stays in the list for Chinese-only releases)."""
    seen, out = set(), []
    for t in (cn, original, en):
        t = (t or '').strip()
        if t and t.lower() not in seen:
            seen.add(t.lower())
            out.append(t)
    return sorted(out, key=len, reverse=True)


def _keywords(cn, original, en, year):
    """Per SKILL.md step 1: sidhub = 中文 → 原语言 → 官方英文; fhl = 最长具体名
    (官方英文/原语言) + 中文片名 (both required, many releases match only one);
    vw = 中文片名 + 年份 (year helps disambiguate same-title old posts)."""
    cn, original, en = (cn or '').strip(), (original or '').strip(), (en or '').strip()
    s = list(dict.fromkeys(t for t in (cn, original, en) if t))
    kw = {'sidhub': s[:3]}
    specific = [t for t in (en, original) if t]
    longest = max(specific, key=len) if specific else cn
    kw['fhl'] = [longest] + ([cn] if cn and cn != longest else [])
    vw = cn or longest
    if year:
        vw += str(year)
    kw['vw'] = vw
    return kw


def search(title, year=None):
    """search/multi (language=en-US: canonical EN titles) -> up to 5
    candidates, movie before tv, year-hint mismatches and low popularity
    last. Query matches titles in any language. Each item: {type, tmdb_id,
    en, original, year, country} - 'country' may be '' (search/multi often
    omits production_countries); the authoritative country comes from
    details() via origin_country."""
    out = _api('/search/multi', {'query': title, 'language': 'en-US'})
    cands = []
    for r in out.get('results', []):
        t = r.get('media_type')
        if t not in ('movie', 'tv'):
            continue
        cands.append({
            'type': t,
            'tmdb_id': r.get('id'),
            'en': r.get('title') or r.get('name') or '',
            'original': r.get('original_title') or r.get('original_name') or '',
            'year': _year_of(r),
            'country': _country_zh(r),
            '_pop': float(r.get('popularity') or 0),
        })

    def key(c):
        wrong_year = bool(year) and c['year'] is not None and c['year'] != year
        return (c['type'] != 'movie', wrong_year, -c['_pop'])

    cands.sort(key=key)
    return [{k: v for k, v in c.items() if k != '_pop'} for c in cands[:5]]


def details(work):
    """/{movie|tv}/<id> (zh-CN: localized CN title) plus /credits (zh-CN:
    top 5 cast). Returns {'cn','original','year','country','cast'}; cast is
    [] if the credits call fails (non-fatal)."""
    d = _api('/%s/%s' % (work['type'], work['tmdb_id']), {'language': 'zh-CN'})
    cast = []
    try:
        cd = _api('/%s/%s/credits' % (work['type'], work['tmdb_id']), {'language': 'zh-CN'})
        cast = [c['name'] for c in cd.get('cast', [])[:5] if c.get('name')]
    except Exception:
        pass
    # production_countries names are English-only (no iso_code); origin_country
    # carries the ISO code - map it to Chinese for the country field
    oc = d.get('origin_country') or []
    country = COUNTRY_ZH.get(oc[0], '') if oc else _country_zh(d)
    return {'cn': (d.get('title') or d.get('name') or '').strip(),
            'original': (d.get('original_title') or d.get('original_name') or '').strip(),
            'year': _year_of(d) or work.get('year'),
            'country': country,
            'cast': cast}


def _entry(no, query, work, d):
    """The hunt.py entry from a chosen work (search row) + its details."""
    cn = d['cn'] or query  # no zh translation on TMDB -> keep the user's wording
    original = work.get('original') or d['original']
    e = {
        'no': no,
        'cn': cn,
        'year': d['year'],
        'country': d['country'],
        'type': work['type'],
        'names': _names(cn, original, work.get('en')),
        'keywords': _keywords(cn, original, work.get('en'), d['year']),
        'tmdb_id': work['tmdb_id'],
        'top_cast': d['cast'],
        'tmdb_source': 'tmdb',
    }
    return e


def _parse_title_line(line):
    """Strip a trailing (2018) / (2018年) year hint -> (title, year-or-None)."""
    m = re.search(r'[\(（](19\d{2}|20\d{2})\s*年?[\)）]\s*$', line)
    year = int(m.group(1)) if m else None
    return (line[:m.start()].strip() if m else line), year


def _norm_title(s):
    """Casefold; keep letters/digits/CJK only, for title identity checks."""
    return re.sub(r'[^0-9a-z一-鿿가-힣а-яА-Я]', '', (s or '').lower())


def _query_match(query, work, cn):
    """Exact identity (normalized) between the user's query and one of the
    work's known titles (zh / en / original). TMDB search is FUZZY: 复仇(2018)
    fuzzy-matches 果戈里·复仇 and would be auto-approved as a unique candidate
    - that is a different film. Only an exact title match may auto-approve."""
    q = _norm_title(query)
    return bool(q) and any(q == _norm_title(t) for t in (work.get('en'), work.get('original'), cn) if t)


def normalize(no, query, year=None):
    """One title -> {'status': 'ok'|'ambiguous'|'not_found'|'error', ...}.
    'ok' carries the ready entry; 'ambiguous'/'not_found'/'error' leave the
    entry out of the draft (tmdb_source=manual, fill by hand or re-query)."""
    try:
        cands = search(query, year)
    except RuntimeError as e:
        return {'no': no, 'query': query, 'status': 'error', 'error': str(e),
                'tmdb_source': 'manual'}
    if not cands:
        return {'no': no, 'query': query, 'status': 'not_found', 'candidates': [],
                'tmdb_source': 'manual'}
    if year:
        exact = [c for c in cands if c['year'] == year]
        if exact:
            cands = exact
    if len(cands) == 1:
        w = cands[0]
        try:
            d = details(w)
        except RuntimeError as e:
            return {'no': no, 'query': query, 'status': 'error',
                    'error': 'details fetch failed: %s' % e, 'tmdb_source': 'manual'}
        if _query_match(query, w, d['cn']):
            return {'no': no, 'query': query, 'status': 'ok',
                    'entry': _entry(no, query, w, d)}
        return {'no': no, 'query': query, 'status': 'ambiguous',
                'candidates': cands,
                'note': 'the only candidate does not EXACTLY match the query '
                        '(TMDB fuzzy match - likely a different film). Check the '
                        'user\'s intent, re-query with the original-language '
                        'title, or fill in via --list with this tmdb_id after '
                        'verifying',
                'tmdb_source': 'manual'}
    return {'no': no, 'query': query, 'status': 'ambiguous',
            'candidates': cands,
            'note': 're-query with a more specific title (original-language title + (year) hint); '
                    'do not guess between candidates',
            'tmdb_source': 'manual'}


def fill_entry(movie):
    """Agent pre-picked the work: entry has tmdb_id + cn (+ optional 'en'
    copied from the ambiguous candidate list) - fill year/country/names/
    keywords/top_cast from details()."""
    out = dict(movie)
    tmdb_id = movie.get('tmdb_id')
    if not tmdb_id:
        # an entry that cannot be filled must not reach hunt.py as "ok"
        out['tmdb_error'] = 'entry has no usable "tmdb_id" (got %r)' % (tmdb_id,)
        return out
    try:
        d = details({'type': movie.get('type', 'movie'), 'tmdb_id': tmdb_id})
    except RuntimeError as e:
        out['tmdb_error'] = str(e)
        return out
    # a re-sent entry may carry a stale tmdb_error from an earlier failed
    # fill; a successful fill must not be masked by it
    out.pop('tmdb_error', None)
    cn = (out.get('cn') or d['cn'] or d['original']).strip()
    en = (movie.get('en') or '').strip() or d['original']
    out['names'] = _names(cn, d['original'], en)
    out['keywords'] = _keywords(cn, d['original'], en, d['year'])
    out['year'] = d['year']
    out['country'] = d['country']
    out['top_cast'] = d['cast']
    out['tmdb_source'] = 'tmdb'
    return out


def main():
    ap = argparse.ArgumentParser(description='normalize a movie list via TMDB for hunt.py')
    ap.add_argument('--titles', help='raw title list file, one title per line, optional (year) hint')
    ap.add_argument('--list', help='JSON list: raw strings to normalize, or agent-built entries with tmdb_id to fill in')
    ap.add_argument('--out', help='write the ready movies.json draft here (default: stdout only)')
    a = ap.parse_args()
    if not a.titles and not a.list:
        ap.error('either --titles or --list is required')
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

    items = []  # (no, query, year, entry-or-None)
    if a.list:
        try:
            raw = json.load(open(a.list, encoding='utf-8'))
        except (OSError, json.JSONDecodeError) as ex:
            sys.exit('--list file %s unreadable or not valid JSON: %r' % (a.list, ex))
        if not isinstance(raw, list):
            sys.exit('--list JSON must be an array of titles or entries')
        for i, m in enumerate(raw, 1):
            if isinstance(m, str):
                q, year = _parse_title_line(m.strip())
                if q:
                    items.append((i, q, year, None))
            else:
                no = m.get('no', i)
                try:
                    no = int(no)
                except (TypeError, ValueError):
                    sys.exit('entry %d has a non-integer "no": %r' % (i, m.get('no')))
                q = m.get('query') or m.get('cn') or m.get('original') or ''
                y = m.get('year_hint')
                entry = m if 'tmdb_id' in m else None
                items.append((no, q, y, entry))
    else:
        try:
            f = open(a.titles, encoding='utf-8')
        except OSError as ex:
            sys.exit('--titles file %s unreadable: %r' % (a.titles, ex))
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            line, year = _parse_title_line(line)
            if line:
                items.append((len(items) + 1, line, year, None))

    results, entries = [], []
    for no, query, year, entry in items:
        if entry is not None:
            e = fill_entry(entry)
            e.setdefault('no', no)
            if e.get('tmdb_error'):
                # an incomplete entry (no keywords/names) must not reach hunt.py
                results.append({'no': no, 'query': query, 'status': 'error',
                                'error': e.pop('tmdb_error'), 'entry': e,
                                'tmdb_source': 'manual'})
                print('%02d %-24s ERROR: fill failed: %s' % (no, query, results[-1]['error']))
            else:
                entries.append(e)
                results.append({'no': no, 'query': query, 'status': 'ok', 'entry': e,
                                'note': 'entry filled from agent-built draft'})
                print('%02d %-24s ok   (filled from entry %s)' % (no, query, e['tmdb_id']))
        else:
            r = normalize(no, query, year)
            r['no'] = no
            results.append(r)
            if r['status'] == 'ok':
                e = r['entry']
                entries.append(e)
                print('%02d %-24s ok   %s (%s, %s)' % (no, query, e['cn'], e['year'] or '?', e['country'] or '?'))
            elif r['status'] == 'ambiguous':
                print('%02d %-24s AMBIGUOUS (%d candidates, see JSON)' % (no, query, len(r['candidates'])))
            elif r['status'] == 'not_found':
                print('%02d %-24s NOT_FOUND' % (no, query))
            else:
                print('%02d %-24s ERROR: %s' % (no, query, r['error']))
    payload = json.dumps({'results': results, 'movies': entries}, ensure_ascii=False, indent=1)
    print()
    print(payload)
    if a.out:
        # a draft file from an earlier run: merge by 'no' (same 'no' replaced,
        # other entries kept) so the ambiguous-fill second run does not wipe it
        if os.path.exists(a.out):
            old, err = None, None
            try:
                old = json.load(open(a.out, encoding='utf-8'))
            except (OSError, json.JSONDecodeError) as ex:
                err = ex
            if err is not None:
                print('WARNING: existing %s could not be read/parsed (%r); overwriting it'
                      % (a.out, err), file=sys.stderr)
            elif isinstance(old, list) and old:
                drop = {e.get('no') for e in entries if isinstance(e, dict)}
                kept = [e for e in old if isinstance(e, dict) and e.get('no') not in drop]
                non_dict = [e for e in old if not isinstance(e, dict)]
                if non_dict:
                    print('WARNING: %d non-dict entr%s in existing %s dropped during merge'
                          % (len(non_dict), 'y' if len(non_dict) == 1 else 'ies', a.out),
                          file=sys.stderr)
                entries = kept + entries
                entries.sort(key=lambda e: (e.get('no') is None, e.get('no')))
                print('merged: %d entr%s kept from existing %s' %
                      (len(kept), 'y' if len(kept) == 1 else 'ies', a.out), file=sys.stderr)
            elif not isinstance(old, list):
                print('WARNING: existing %s is not a JSON array of entries; overwriting it'
                      % a.out, file=sys.stderr)
        open(a.out, 'w', encoding='utf-8').write(json.dumps(entries, ensure_ascii=False, indent=1))
        print('draft written -> %s (%d of %d entries ready; fill ambiguous/not_found by hand)'
              % (a.out, len(entries), len(results)), file=sys.stderr)
    bad = [r for r in results if r['status'] != 'ok']
    if bad:
        sys.stderr.write('%d of %d entries need manual handling\n' % (len(bad), len(results)))


if __name__ == '__main__':
    main()
