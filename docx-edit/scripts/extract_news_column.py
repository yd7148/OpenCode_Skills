#!/usr/bin/env python3
"""
Extract a specific column (by keyword) out of .docx tables into Markdown.

Built for the SiC weekly-report docx family, where the content lives in the
last column of a table that SPANS PAGES -- Word repeats the header row on every
page and truncates sentences mid-way into separate <w:tr> rows. This script
re-joins those broken sentences.

Reusable beyond that family: pass --marker (row must contain this text),
--header (row is a header row if it contains this), and --col (last | N).

Usage (Windows: PATH 'python' may be a Microsoft Store stub that fails silently --
resolve the real interpreter first):
  py -3 extract_news_column.py -i "<project>\\01-REF\\docx" -o "<project>\\01-REF\\md"

  # if the 'py' launcher is unavailable, use the full path:
  #   <USERPROFILE>\\AppData\\Local\\Programs\\Python\\Python313\\python.exe

No third-party packages required (zipfile + xml.etree only).
"""
import argparse
import glob
import os
import re
import sys
import zipfile
import xml.etree.ElementTree as ET

sys.stdout.reconfigure(encoding='utf-8')

W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'

# Default marker text. If a document's heading uses different wording,
# override it with -m/--marker (rows that match nothing yield EMPTY output).
DEFAULTS = dict(
    marker='SiC相關新聞與市場消息',
    header='執行結果及說明',
)

# header-column words used to recognise a header row when --header is generic
TOPIC_HDRS = ('研開項目', '題目', '案號', '項次', '序號')

# paragraphs that merely repeat row metadata / the project name
NOISE = re.compile(
    r'^(SiC相關新聞與市場消息|項次|案號\(技術資料編號\)|'
    r'工作日期\(?立案日期/預完日\)?|研開項目|負責人|執行結果及說明)$')

HEAD = re.compile(r'^[一二三四五六七八九十]+\s*[.．、,，:：]\s*')
ANALYSIS = re.compile(r'^\s*解\s*析\s*[:：]?\s*')
ENDCH = set('。！？!?：:；;」"’\'）)】]')


def para_text(p):
    parts = []
    for n in p.iter():
        if n.tag == W + 't' and n.text:
            parts.append(n.text)
        elif n.tag == W + 'tab':
            parts.append(' ')
        elif n.tag in (W + 'br', W + 'cr'):
            parts.append('\n')
    return ''.join(parts)


def norm(s):
    s = s.replace('\u3000', ' ').replace('\xa0', ' ')
    return re.sub(r'[ \t]+', ' ', s).strip()


def cell_text(tc):
    return norm(''.join(para_text(p) for p in tc.findall(W + 'p')))


def cell_paras(tc):
    return [t for t in (norm(para_text(p)) for p in tc.findall(W + 'p')) if t]


def is_header_row(texts, header):
    j = ''.join(texts)
    return header in j and any(h in j for h in TOPIC_HDRS)


def pick_col_index(cells, col):
    if col in (None, 'last', -1):
        return len(cells) - 1
    return int(col)


def extract(path, marker=None, header=None, col='last'):
    marker = DEFAULTS['marker'] if marker is None else marker
    header = DEFAULTS['header'] if header is None else header
    with zipfile.ZipFile(path) as z:
        root = ET.fromstring(z.read('word/document.xml'))
    idx = pick_col_index(None, col) if col not in ('last', None) else None
    paras = []
    for tbl in root.iter(W + 'tbl'):
        rows = tbl.findall(W + 'tr')
        for tr in rows:
            cells = tr.findall(W + 'tc')
            if not cells:
                continue
            texts = [cell_text(c) for c in cells]
            if is_header_row(texts, header):
                continue
            if marker and not any(marker in t for t in texts):
                continue
            ci = len(cells) - 1 if idx is None else min(idx, len(cells) - 1)
            for t in cell_paras(cells[ci]):
                if not NOISE.match(t):
                    paras.append(t)
    return paras


def merge(paras):
    """Re-join paragraphs split by a page/row break mid-sentence."""
    res = []
    for t in paras:
        if not res:
            res.append(t)
            continue
        prev = res[-1]
        new_block = bool(HEAD.match(t) or ANALYSIS.match(t))
        prev_incomplete = prev[-1] not in ENDCH
        if new_block or not prev_incomplete:
            res.append(t)
        else:
            res[-1] = prev + t
    return res


def to_md(title, paras, numbered=True):
    md = ['# ' + title, '']
    n = 0
    for t in paras:
        m = ANALYSIS.match(t)
        if m:
            md += ['## 解析', '']
            rest = t[m.end():].strip()
            if rest:
                md += [rest, '']
            continue
        h = HEAD.match(t) if numbered else None
        if h:
            n += 1
            md += ['## %d. %s' % (n, t[h.end():].strip().rstrip('：: ')), '']
            continue
        if t:
            md += [t, '']
    return re.sub(r'\n{3,}', '\n\n', '\n'.join(md)).rstrip() + '\n'


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('-i', '--indir', required=True, help='directory of .docx')
    ap.add_argument('-o', '--outdir', required=True, help='output directory for .md')
    ap.add_argument('-g', '--glob', default='*.docx', help='input glob (default *.docx)')
    ap.add_argument('-m', '--marker', default=DEFAULTS['marker'],
                    help='row must contain this text to be kept')
    ap.add_argument('-H', '--header', default=DEFAULTS['header'],
                    help='text marking a header row to be skipped')
    ap.add_argument('-c', '--col', default='last',
                    help="column to extract: 'last' (default) or 0-based index")
    ap.add_argument('--no-numbers', action='store_true',
                    help='do not turn 一./二. into markdown headings')
    a = ap.parse_args()

    os.makedirs(a.outdir, exist_ok=True)
    files = sorted(glob.glob(os.path.join(a.indir, a.glob)))
    if not files:
        print('no input files in %s' % a.indir)
        return 1
    made = empty = 0
    for f in files:
        try:
            paras = merge(extract(f, a.marker, a.header, a.col))
            if not paras:
                print('EMPTY %s' % os.path.basename(f))
                empty += 1
                continue
            title = os.path.splitext(os.path.basename(f))[0]
            out = os.path.join(a.outdir, title + '.md')
            with open(out, 'w', encoding='utf-8', newline='\n') as fh:
                fh.write(to_md(title, paras, numbered=not a.no_numbers))
            made += 1
            print('OK    %-8d %s' % (os.path.getsize(out), title))
        except Exception as e:
            print('FAIL  %s -> %r' % (os.path.basename(f), e))
    print('\nconverted %d, empty %d, total %d' % (made, empty, len(files)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
