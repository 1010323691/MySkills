# -*- coding: utf-8 -*-
"""
把 CHM（Microsoft HTML Help）文件转换成常规 txt。

用法：
    python convert_chm_to_txt.py <输入.chm> <输出目录>

自动识别 CHM 内部结构并分别处理：
  A. 网页阅读器式（常见电子书）：js/page.js 有章节表 pages[N]=['文件名','章节名','页号','卷名',...]，
     章节文件是 GBK 的 document.write("HTML") 脚本
     -> 全书.txt（按卷/章顺序合并）+ 目录.txt + chapters/（每章一个）+ images/（封面）
  B. 标准 HTML Help：一批 .htm/.html 页面
     -> 保留原相对路径，每页输出一个 .txt（去 script/style、去标签）
  C. 纯文本打包：.txt + 图片
     -> 重新编码为 UTF-8（带 BOM），保留相对路径

输出文本统一 utf-8-sig（带 BOM），Windows 记事本 / Word 可直接显示中文。
"""
import os, re, sys, shutil, subprocess, tempfile
from html.parser import HTMLParser


def find_seven_zip():
    candidates = [r'C:/Program Files/7-Zip/7z.exe',
                  r'C:/Program Files (x86)/7-Zip/7z.exe']
    which = shutil.which('7z') or shutil.which('7z.exe')
    for c in ([which] if which else []) + candidates:
        if c and os.path.exists(c):
            return c
    return None


def extract_chm(chm_path):
    seven_zip = find_seven_zip()
    if not seven_zip:
        raise SystemExit('未找到 7-Zip，请先安装: winget install 7zip.7zip -e --silent --disable-interactivity')
    tmp = tempfile.mkdtemp(prefix='chm_')
    try:
        r = subprocess.run([seven_zip, 'x', '-y', chm_path, '-o' + tmp],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        shutil.rmtree(tmp, ignore_errors=True)
        raise
    # 7z 退出码: 0=OK, 1=warning（内容已解出）, >=2=fatal
    if r.returncode >= 2:
        shutil.rmtree(tmp, ignore_errors=True)
        raise SystemExit('7z 解包失败（退出码 %d）: %s' % (r.returncode, chm_path))
    return tmp


IMAGE_EXTS = ('.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp')


def walk_files(root, exts):
    res = []
    for dirpath, _, files in os.walk(root):
        for f in files:
            if f.lower().endswith(exts):
                res.append(os.path.join(dirpath, f))
    return sorted(res)


def decode_bytes(raw):
    for enc in ('utf-8-sig', 'gb18030'):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode('gb18030', errors='replace')


class Txt(HTMLParser):
    """HTML -> 纯文本：块级标签变行，script/style 跳过，其余标签去除。"""
    BLOCK = ('p', 'br', 'div', 'table', 'tr', 'li', 'ul', 'ol', 'dl', 'dt', 'dd',
             'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'hr', 'pre', 'blockquote')

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.out = []
        self.skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in ('script', 'style'):
            self.skip += 1
            return
        if not self.skip and tag in self.BLOCK:
            self.out.append('\n')

    def handle_endtag(self, tag):
        if tag in ('script', 'style'):
            self.skip = max(0, self.skip - 1)
            return
        if not self.skip and tag in self.BLOCK:
            self.out.append('\n')

    def handle_data(self, data):
        if not self.skip:
            self.out.append(data)


def clean_html(html):
    p = Txt()
    p.feed(html)
    p.close()
    text = ''.join(p.out).replace('\xa0', ' ')
    lines = [ln.strip() for ln in text.split('\n')]
    return '\n'.join(ln for ln in lines if ln)


def extract_write_payloads(js_text):
    """提取所有 document.write 的字符串参数（此类文件无转义反斜杠，已验证）。"""
    parts, i = [], 0
    while True:
        i = js_text.find('document.write', i)
        if i < 0:
            break
        k = js_text.find('(', i)
        if k < 0:
            break
        if k + 1 >= len(js_text):
            break
        q = js_text[k+1]
        if q not in ('"', "'"):
            i += 1
            continue
        m = js_text.find(q, k+2)
        if m < 0:
            break
        parts.append(js_text[k+2:m])
        i = m + 1
    return ''.join(parts)


def chapter_to_text(path):
    """章节文件 -> 纯文本：document.write 脚本 / HTML 页面 / 纯文本 自适应。"""
    text = decode_bytes(open(path, 'rb').read())
    if 'document.write' in text:
        return clean_html(extract_write_payloads(text))
    if re.search(r'<\s*(html|body|p|div|table|br)\b', text, re.I):
        return clean_html(text)
    return text.strip()


def parse_pages(js_path):
    """从 js/page.js 解析出有序的 (文件名, 章节名, 卷名) 列表。"""
    js = decode_bytes(open(js_path, 'rb').read())
    entries = []
    for m in re.finditer(r"pages\[\d+\]\s*=\s*\[", js):
        j = js.find('];', m.end())
        if j < 0:
            continue
        body = js[m.end():j]
        # 手动拆分单引号字段（HTML 属性里含单引号，看其后字符判断字段结束）
        parts, k = [], 0
        while k < len(body):
            if body[k] == "'":
                k += 1
                start = k
                while k < len(body):
                    if body[k] == "'":
                        after = body[k+1:k+2]
                        if after in ('', ',', ')'):
                            break
                        if after == "'":
                            k += 1
                            continue
                    k += 1
                parts.append(body[start:k])
                k += 1
            else:
                k += 1
        if len(parts) < 2:
            continue
        fname, title = parts[0], parts[1]
        volume = parts[3] if len(parts) > 3 and not parts[3].startswith('<') else None
        entries.append((fname, title, volume))
    return entries


def find_pages_js(tmp):
    for js in walk_files(tmp, ('.js',)):
        if re.search(r'pages\[\d+\]\s*=\s*\[',
                     decode_bytes(open(js, 'rb').read())):
            return js
    return None


def find_book_title(tmp):
    for htm in walk_files(tmp, ('.htm', '.html')):
        t = decode_bytes(open(htm, 'rb').read())
        m = re.search(r"titletop'>.*?class='hide'>([^<]*)<", t, re.S)
        if m and m.group(1).strip():
            return m.group(1).strip()
    return None


def write_text(path, text):
    d = os.path.dirname(path)
    if d:
        os.makedirs(d, exist_ok=True)
    with open(path, 'w', encoding='utf-8-sig', newline='\n') as f:
        f.write(text)


def convert_reader(tmp, out, pages_js):
    entries = parse_pages(pages_js)
    by_name = {}
    for p in walk_files(tmp, ('.txt', '.htm', '.html')):
        by_name.setdefault(os.path.splitext(os.path.basename(p))[0], p)
    missing = [e[0] for e in entries if e[0] not in by_name]

    chm_stem = os.path.basename(out)
    title = find_book_title(tmp) or chm_stem
    os.makedirs(os.path.join(out, 'chapters'), exist_ok=True)
    merged = [title, '=' * 30, '']
    toc = [title, '']
    cur_vol = None
    for fname, chap, vol in entries:
        p = by_name.get(fname)
        if p is None:
            continue
        txt = chapter_to_text(p)
        write_text(os.path.join(out, 'chapters', fname + '.txt'), txt + '\n')
        body = txt
        if chap and txt.split('\n')[0].strip() == chap:
            body = '\n'.join(txt.split('\n')[1:])
        if vol and vol != cur_vol:
            merged += ['', '########## ' + vol + ' ##########', '']
            toc.append(vol)
            cur_vol = vol
        merged += ['--- ' + chap + ' ---', body, '']
        toc.append('  ' + chap)
    write_text(os.path.join(out, '全书.txt'), '\n'.join(merged))
    write_text(os.path.join(out, '目录.txt'), '\n'.join(toc) + '\n')
    # 封面/插图只取章节文件所在目录，避免混入阅读器 UI 图片
    first_src = next((by_name[e[0]] for e in entries if e[0] in by_name), None)
    if first_src is not None:
        copy_images(tmp, out, os.path.dirname(first_src))
    print('结构: 网页阅读器式 | 书名: %s | 章节: %d | 缺文件: %s'
          % (title, len(entries), missing or '无'))


def convert_html(tmp, out, html_files):
    n = 0
    used = {}
    for p in html_files:
        rel = os.path.relpath(p, tmp)
        base = os.path.splitext(rel)[0]
        idx = used.get(base, 0)
        used[base] = idx + 1
        # 同一路径下 .htm/.html 同名时加序号，避免后者覆盖前者
        suffix = '' if idx == 0 else '_%d' % (idx + 1)
        dest = os.path.join(out, base + suffix + '.txt')
        text = clean_html(decode_bytes(open(p, 'rb').read()))
        if text:
            write_text(dest, text + '\n')
            n += 1
    print('结构: 标准 HTML Help | 转换页面: %d' % n)


def convert_plain(tmp, out, txt_files):
    n = 0
    for p in txt_files:
        rel = os.path.relpath(p, tmp)
        write_text(os.path.join(out, rel), decode_bytes(open(p, 'rb').read()).strip() + '\n')
        n += 1
    print('结构: 纯文本打包 | 文件: %d' % n)


def copy_images(tmp, out, src=None):
    n = 0
    for p in walk_files(src or tmp, IMAGE_EXTS):
        rel = os.path.relpath(p, src or tmp)
        dest = os.path.join(out, 'images', rel)
        d = os.path.dirname(dest)
        if d:
            os.makedirs(d, exist_ok=True)
        shutil.copy2(p, dest)
        n += 1
    if n:
        print('图片: %d（已存到 images/，保留相对路径）' % n)


def main():
    if len(sys.argv) != 3:
        raise SystemExit('用法: python convert_chm_to_txt.py <输入.chm> <输出目录>')
    chm_path, out = sys.argv[1], sys.argv[2]
    tmp = extract_chm(chm_path)
    try:
        os.makedirs(out, exist_ok=True)
        pages_js = find_pages_js(tmp)
        html_files = walk_files(tmp, ('.htm', '.html'))
        txt_files = walk_files(tmp, ('.txt',))
        if pages_js:
            convert_reader(tmp, out, pages_js)
        elif html_files:
            convert_html(tmp, out, html_files)
            copy_images(tmp, out)
        elif txt_files:
            convert_plain(tmp, out, txt_files)
            copy_images(tmp, out)
        else:
            print('未识别的结构，内容原样保留（请人工检查）')
        print('完成:', out)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == '__main__':
    main()
