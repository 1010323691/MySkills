---
name: JavBus-GetMagnet
description: Scrape JavBus (javbus.com) magnet links + cover images for an actress (by star id, e.g. 138y, or by name, e.g. 瀬戸環奈) or a single video code (e.g. SNOS-313). Auto-clears the age-verification gate, picks the smallest 1080p per work (720p if no 1080p exists), downloads each work's cover, and writes a self-contained showcase webpage with live-update support. Output is a folder: covers/ + magnets.txt + data.json + index.html + 启动页面.bat (double-click launcher: local --serve server + opens the page, where the 获取更新 button can check JavBus for new works). Use when the user asks for JavBus magnet links, download links, 番号 lists, covers, or video file sizes.
---

# JavBus-GetMagnet

Get magnet links **and cover images** for a JavBus actress or a single video, with
the age-verification gate handled automatically and the "smallest 1080p, else 720p"
rule applied.

## Usage

```bash
# All works for an actress, by star id (the id after /star/ in the URL)
python <skill>/scripts/javbus_get_magnet.py --star 138y

# All works for an actress, by name (resolved to a star id via the site search)
python <skill>/scripts/javbus_get_magnet.py --name 河北彩花

# A single video by code
python <skill>/scripts/javbus_get_magnet.py --code SNOS-313

# Serve an existing dataset folder with live-update support
python <skill>/scripts/javbus_get_magnet.py --serve D:\path\to\河北彩花   # → http://localhost:<port>/
```

`--star`, `--name`, `--code`, and `--serve` are mutually exclusive — give exactly one.
`--serve` serves an existing folder (must contain data.json) plus `POST /api/refresh`:
the page's 获取更新 button uses it to check for new works (listing pages only for the
minimal check; new works are scraped only when there are some) and reloads the page
after the library files are rewritten.

**Default output is a folder** `./<name or star id>/` (the `--name` spelling is used
when given):

```
河北彩花/
  covers/            one cover image per work, named <番号>.jpg
  magnets.txt        番号 | 标题 | 大小 | 磁力  (one line per work)
  data.json          machine-readable dataset (incl. cover file names, gb sizes)
  index.html         self-contained showcase page — cards + table view, open in a browser
  启动页面.bat        double-click: starts the --serve local server (auto port) and opens
                     the page in the default browser — the 获取更新 button works from it
```

The page needs nothing but its own folder (covers are referenced relatively), so it
works from `file://` — no server. But file:// has no 获取更新; for live updates use
启动页面.bat (or `--serve`).

Useful flags:
- `--outdir DIR` — folder mode in a custom location.
- `--serve DIR` — serve an existing dataset folder (static files + 获取更新 API) instead
  of scraping; the page opened from it can check JavBus for new works live.
- `--port N` — port for `--serve` (default: OS-assigned; the chosen URL is printed).
- `--open` — with `--serve`: also open the page in the default browser (what the
  in-folder 启动页面.bat does).
- `--root DIR` — download root: after the run, also create `<root>/<女优名>/<番号 作品名>/封面.<ext>`
  for every work (same naming rule as the page's 建目录 button). DIR is remembered in
  `save-root.json` (next to the script); later runs without `--root` reuse it — the
  disk-based, always-persistent equivalent of the page's 保存目录 config.
- `--out FILE` — legacy: write only a single text file (no covers, no page).
- `--res 1080|720` — preferred resolution (default `1080`; falls back to the other).
- `--max-pages N` — how many star pages to crawl (default 10, ≈300 works at ~30/page).
- `--workers N` — concurrent per-work scrapers (default 8).
- `--rate R` — global request-rate cap in req/s across ALL workers (default 4.0). The
  old serial pace (~2.5 req/s) was safe; unthrottled 8-way bursts (~15–20 req/s) trip
  the site's HTTP 429, so workers run under a global throttle. 429/503 responses
  back off (3s/6s/12s) and retry, so an aggressive `--rate` self-corrects instead of
  producing NO_GID rows — it just finishes slower. Raise it (e.g. `--rate 8`) if the
  site tolerates it.
- `--delay SECONDS` — politeness delay between a single work's own requests (default 0.4).
- `--cookies FILE` — cookie jar path (default `<skill>/cookies.txt`); the age gate is
  only solved once and reused across runs.
- `--no-interactive` — don't prompt for quiz answers; exit code 3 if the gate can't be
  auto-cleared.

`magnets.txt` is one line per work: `番号 | 标题 | 大小 (分辨率) | magnet:?xt=...&dn=...`.
A work that failed (unreadable video page / no magnets) still gets a line with
`NO_GID` or `no magnets` in the 大小 column and `-` as the magnet.
`data.json` holds the same plus `date`, numeric `gb`, `res`, and the `cover` file name
(null for failed works — the page template is null-safe).

## How it works (the pipeline)

1. **Age gate (one-time, cookie-persisted).** JavBus blocks anonymous access with a
   two-stage gate: (a) confirm "adult" → `age=verified` cookie, (b) a 5-question
   randomized Chinese driving-test quiz → `dv=1` cookie. All 20 possible quiz
   questions and their correct answers are built into `QUIZ_BANK`, so the gate is
   cleared automatically and the cookies cached in `cookies.txt`. Later runs skip it.
2. **Name → star id (only for `--name`).** `GET /search/{name}` serves that actress's
   video list (it 404s when the name has no match), but the star id isn't on that page —
   so the script reads the first video's page to get `/star/{id}`, then continues as if
   it were given `--star`.
3. **Catalog.** `GET /star/{id}/1..N` (~30 works/page) → 番号 + 标题 + date. The loop
   stops when a page 404s (past the last page) or returns no works.
4. **Per-work magnets + cover.** Magnets are **not** in the video page's HTML — they're
   loaded via AJAX. So for each work: `GET /{code}` to read `var gid / img / uc` from
   the inline `<script>`, call
   `GET /ajax/uncledatoolsbyajax.php?gid=..&lang=zh&img=..&uc=..&floor=<rand>` with
   `X-Requested-With: XMLHttpRequest` and a `Referer` back to the video page, then
   **download the cover** from `img` (e.g. `/pics/cover/cjvp_b.jpg`) as raw bytes to
   `covers/<番号>.jpg`.
5. **Parse & pick.** Dedupe each magnet (each appears 6×/row), read the size and the
   resolution from the magnet's `dn=` name (name keywords win over the "高清" tag, which
   is unreliable), then select the smallest 1080p (or 720p if none).
6. **Assemble the folder.** `magnets.txt` (human-readable), `data.json` (machine
   readable, with `gb` sizes and cover file names), and `index.html` (generated from a
   built-in template embedded in the script: a cover-card grid with a 1–5 column toggle
   (fewer columns = bigger covers), search / sort / magnet copy / lightbox and a table
   view — every card shows cover, 番号 + size, title and a foot row (发行日期 +
   复制磁力 button), default-sorted by 发行日期 newest first (the date column is also
   click-sortable); each card / table row / lightbox also has a 建目录 button next to
   复制磁力: it creates `<女优名>/<番号 作品名>/` under the user-configured local root —
   any level that already exists is simply walked into — and writes the cover image
   into the leaf as `封面.<ext>` (bytes come from fetch over http, or from the
   base64 covers embedded in the page — so it works from file:// too; folder names
   sanitize Windows-illegal chars, capped at 120 chars; re-clicks are idempotent).
   Next to 保存目录 in the filter bar, the 一键建目录 button batch-creates every
   currently visible work's folder + cover in one click: it runs sequentially,
   shows 「创建中 x/y」progress on itself, flips each card/table row to 已创建 ✓ as
   it lands, and ends with a toast tallying success/failure; per-work 建目录
   buttons are disabled for the duration. It honors the active search filter — the
   label counts visible works with covers — so filtering to a subset then clicking
   builds only that subset.
   The 获取更新 button (right of 复制全部磁力) does a live update against JavBus:
   the server first fetches only the listing pages and diffs 番号s (the minimal
   check — if nothing changed, NO per-work requests happen); only when there are
   new works does it scrape exactly those (magnets + cover), prepend them to
   data.json / magnets.txt / index.html (and the remembered --root library), then
   the page reloads itself. It requires the page to be opened via the --serve
   server (over http) — from file:// it toasts the --serve command instead.
   The root is picked with the 保存目录 button in the filter bar — the chosen directory
   handle is persisted in IndexedDB and restored on page load (the label shows the
   remembered directory; a stored handle re-asks permission with one click on first
   use). Buttons flip to 已创建 ✓ when the work's folder already exists on disk — the
   root is probed on load / root change / window refocus (browsers can't watch the
   filesystem, so the state is refreshed on those events, not continuously); the data
   is embedded as JSON and covers are referenced relatively, so the folder is
   self-contained and works from `file://`; the folder also contains 启动页面.bat —
   double-clicking it starts --serve (auto port, so two datasets can run at once)
   and opens the page in the default browser; the series prefix of the 番号 is the only
   series signal shown on the page).

## Pitfalls already handled (don't re-discover)

- **Magnet links aren't in the raw page HTML.** Scraping `#magnet-table` from the
  video page gives an empty table; you must hit the `uncledatoolsbyajax.php` endpoint.
- **Covers live at the `img` var, not a `/photos/` gallery.** The video page's inline
  `var img = '/pics/cover/xxxx_b.jpg'` IS the cover (800×538 landscape). The
  `/photos/…` gallery system usually returns nothing for current works — don't go
  hunting there.
- **Covers are binary — fetch raw bytes.** The text `get()` helper utf-8 decodes
  responses and corrupts JPEGs; the script uses a separate `raw_get()` and checks the
  JPEG/PNG magic bytes before writing.
- **Cookies are a hard requirement.** `PHPSESSID + age=verified + dv=1` together, or
  you're back at the gate. They're persisted in `cookies.txt`; saves go through
  temp+replace and never clobber a jar another process (a running --serve and the
  CLI can share one jar) wrote in between — the other process's session is kept.
- **Quiz question IDs are random** (`userAnswers[N]`, N varies each load) and a single
  wrong answer regenerates the whole set — the script reads the questions dynamically
  and loops until it's through.
- **Resolution: trust the `dn=` name, not the "高清" tag.** Classify by `4K/2160`,
  `720`, `1080/FHD` in the magnet string; only fall back to the tag.
- **Dedupe before counting** — each magnet repeats 6× within its row.
- **The catalog lists duplicates.** A star page can repeat a work, and re-releases show
  up as a date-suffixed href (`SDJS-363_2026-04-27`). The script normalizes every 番号
  to its base code and dedupes across pages, so each work appears exactly once.
- **番号 labels can start with a digit** (e.g. `3DSVR-1928`). The parser allows
  `[A-Z0-9]` in the label, not just letters.
- **Re-runs are incremental for covers.** Already-downloaded `covers/<番号>.jpg` files
  are skipped, so you can resume a partial run cheaply.
- **Windows:** run with `python` (not `python3`, which is a broken WindowsApps stub),
  and pass **absolute** Windows paths for any files shared between steps.
- **建目录 / 保存目录 need Chromium's File System Access API.** `showDirectoryPicker`
  exists only in Chrome/Edge — Firefox/Safari get a toast and everything else on the
  page keeps working. Cover bytes for the write come from `fetch()` when served over
  http(s), and from a **base64 copy embedded in the page** (`__COVERS_B64__`) otherwise —
  that is what makes it work from `file://`, where Chrome blocks both fetch of local
  files and canvas export of them (don't reach for a canvas fallback; it is
  guaranteed-tainted there). The embedding makes index.html roughly the size of the
  covers/ folder + 33% (e.g. 99 covers → ~20 MB); fine for local use. Note: a
  double-clicked `file://` page runs under an opaque per-load origin, so the IndexedDB
  handle may not survive a re-open — the button then re-asks with one picker click, and
  the guaranteed-persistent route is the CLI `--root DIR` (remembered in `save-root.json`).
- **获取更新 needs the --serve server.** The button POSTs to `/api/refresh` on the page's
  own origin, so it only works when the page is opened from `python … --serve <folder>`
  (http). A double-clicked file:// page is detected by the page itself (protocol
  check) and toasts the --serve command; a plain `python -m http.server` folder has
  no such endpoint, so the POST just 404s (the page toasts 「更新失败：HTTP 404」 —
  see Troubleshooting). Refresh is single-flight (a second click while one runs gets
  409) and re-reads data.json every time; if data.json changes while a refresh is
  running (e.g. a full CLI re-scrape finishes in between), the refresh aborts with
  an error instead of clobbering the newer library — retry once the other run is
  done.

## Troubleshooting

- **Exit code 3 / "Could not clear the age gate":** the quiz bank didn't match (the site
  changed its questions). Run without `--no-interactive`, answer the printed questions,
  or delete `cookies.txt` to force a fresh solve.
- **Exit code 4 / "No actress found for name":** the `--name` search returned no videos —
  the name is likely wrong or not on JavBus. The search matches JavBus's own spelling,
  so use the exact name (e.g. 瀬戸環奈, not romaji). The site's search 404s on a
  no-match, which is how the script tells "not found" from a real page.
- **Japanese name passed on the command line:** the script reads it fine, but a Windows
  console in a non-UTF-8 codepage can mangle the argument. If resolution fails for a
  name you're sure of, set `chcp 65001` first, or hand the script the star id via
  `--star` instead.
- **`NO_GID` on a line:** that video page failed to load (usually transient); re-run —
  the other works are unaffected.
- **A line says `no magnets`:** the work genuinely has no magnets on the site right now.
  On the page such works still appear (size `–`, `无磁力` instead of the copy button) —
  the template is null-safe, so one bad work never blanks the rest.
- **A card shows the 番号 instead of a cover:** that cover failed to download (or the
  site never had one); the page degrades gracefully and the table view still carries
  everything. Re-run to retry just the missing covers.
- **获取更新 toasts 「需要经本地服务打开页面」 or fails with HTTP 404:** the page is not
  being served by --serve (file:// or a plain http.server). Re-open it via
  `python <skill>/scripts/javbus_get_magnet.py --serve <该文件夹> --port N`.
- **获取更新 toasts 「没有新作品（共 N 部）：作品列表抓取失败，请稍后重试」:** the listing
  fetch came back empty (transient site issue or expired cookie) — the page does
  NOT treat that as "no updates" and leaves the library untouched; retry, or delete
  `cookies.txt` and re-run serve to re-clear the gate.
- **Slow / risk of rate-limiting:** raise `--delay` (e.g. `--delay 0.8`) and/or lower
  `--workers` (e.g. `--workers 3`) for large crawls — covers add one request per work.
- **Stale cookie:** if results look empty or the gate reappears, delete `cookies.txt`
  and re-run.
