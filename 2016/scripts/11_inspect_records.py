#!/usr/bin/env python3
"""
List the actual MARC records behind a count: a class (DK or PG), a publication-year range, and optionally a
class-number range. Writes a CSV with title, author, imprint, call number, place code, cataloging source and
record id, and prints counts by place of publication (008/15-17) and cataloging agency (040 $a).

Usage (from LCC/2016):
  python3 scripts/11_inspect_records.py <parts_dir> <out_csv> <CLASS> <year_from> <year_to> [num_from num_to] [n_workers]
Examples:
  python3 scripts/11_inspect_records.py <parts_dir> early_dk.csv DK 1400 1699
  python3 scripts/11_inspect_records.py <parts_dir> polish_pg_1976_80.csv PG 1976 1980 6001 7446
  python3 scripts/11_inspect_records.py <parts_dir> poland_dk_1973_75.csv DK 1973 1975 4010 4800
Same rules as 01/10 (first 050 $a else 090 $a; publication year = 008/07-10).
"""
import gzip, re, sys, os, glob, csv, importlib.util
from collections import Counter
from multiprocessing import Pool

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location('ex01', os.path.join(HERE, '01_extract_marc_2016.py'))
ex = importlib.util.module_from_spec(spec); spec.loader.exec_module(ex)
RT = ex.RT

def fields(rec):
    base = int(rec[12:17]); out = {}
    d = rec[24:base - 1]
    for i in range(0, len(d) - 11, 12):
        tag = d[i:i + 3].decode('ascii', 'replace'); ln = int(d[i + 3:i + 7]); st = int(d[i + 7:i + 12])
        out.setdefault(tag, []).append(rec[base + st:base + st + ln])
    return out

def subs(raw, codes):
    res = {}
    for part in raw.split(b'\x1f')[1:]:
        c = part[:1].decode('ascii', 'replace')
        if c in codes and c not in res: res[c] = part[1:].rstrip(b'\x1e').decode('utf-8', 'replace').strip(' /:,;.')
    return res

def first(fs, tag, codes):
    return subs(fs[tag][0], codes) if tag in fs else {}

def tagtxt(fs, tag):
    return ' | '.join(' '.join(p[:1].decode('ascii', 'replace') + p[1:].decode('utf-8', 'replace') for p in raw.rstrip(b'\x1e').split(b'\x1f')[1:]) for raw in fs.get(tag, []))[:120]

CFG = {}
def process(path):
    cls, y0, y1, lo, hi = CFG['cls'], CFG['y0'], CFG['y1'], CFG['lo'], CFG['hi']
    rows = []; buf = b''
    with gzip.open(path, 'rb') as f:
        while True:
            ch = f.read(1 << 24); buf += ch
            parts = buf.split(RT); buf = parts.pop()
            if not ch and len(buf) > 24: parts.append(buf); buf = b''
            for r in parts:
                if len(r) <= 24: continue
                try:
                    cn, f008 = ex.call_number(r)
                    if not cn or ex.valid_class(cn) != cls: continue
                    ym = re.match(rb'\d{4}', (f008 or b'')[7:11])
                    if not ym: continue
                    y = int(ym.group())
                    if not y0 <= y <= y1: continue
                    m = re.match(r'\s*' + cls + r'\s*(\d+(?:\.\d+)?)', cn.decode('utf-8', 'replace') if isinstance(cn, bytes) else cn, re.I)
                    if not m: continue
                    n = float(m.group(1))
                    if lo is not None and not lo <= n <= hi: continue
                    fs = fields(r)
                    t = first(fs, '245', 'abc'); a = first(fs, '100', 'a') or first(fs, '110', 'a')
                    imp = first(fs, '260', 'abc') or first(fs, '264', 'abc')
                    cn_s = first(fs, '050', 'ab') or first(fs, '090', 'ab')
                    rows.append([y, ' '.join(cn_s.values()), a.get('a', ''), ' '.join(t.values()), imp.get('a', ''), imp.get('b', ''), imp.get('c', ''),
                                 (f008 or b'')[15:18].decode('ascii', 'replace').strip(), first(fs, '040', 'a').get('a', ''),
                                 fs['001'][0].decode('ascii', 'replace').strip('\x1e') if '001' in fs else '',
                                 chr(r[17]), chr(r[18]), tagtxt(fs, '042'), tagtxt(fs, '906'), tagtxt(fs, '955'), tagtxt(fs, '985'), tagtxt(fs, '010')])
                except Exception: pass
            if not ch: break
    return rows

def init(c): CFG.update(c)

if __name__ == '__main__':
    a = sys.argv[1:]
    parts_dir, out, cls, y0, y1 = a[0], a[1], a[2].upper(), int(a[3]), int(a[4])
    rest = a[5:]; lo = hi = None
    if len(rest) >= 2: lo, hi = float(rest[0]), float(rest[1]); rest = rest[2:]
    nw = int(rest[0]) if rest else 2
    cfg = {'cls': cls, 'y0': y0, 'y1': y1, 'lo': lo, 'hi': hi}
    files = sorted(glob.glob(os.path.join(parts_dir, '*.gz')))
    allrows = []
    with Pool(nw, initializer=init, initargs=(cfg,)) as pool:
        for i, rows in enumerate(pool.imap_unordered(process, files), 1):
            allrows += rows; print(i, '/', len(files), len(allrows), flush=True)
    allrows.sort(key=lambda r: (r[0], r[1]))
    with open(out, 'w', newline='', encoding='utf-8') as o:
        w = csv.writer(o); w.writerow(['year', 'call_number', 'author', 'title', 'place', 'publisher', 'imprint_date', 'country_008', 'cataloging_agency_040a', 'record_id', 'leader_encoding_level', 'leader_desc_form', 'f042', 'f906', 'f955', 'f985', 'f010']); w.writerows(allrows)
    print('records:', len(allrows), '->', out)
    for name, idx in (('place of publication (008/15-17)', 7), ('cataloging agency (040 $a)', 8), ('encoding level (leader/17)', 10), ('field 042', 12), ('field 906', 13)):
        print('\nBy', name); [print(' ', k or '(blank)', n) for k, n in Counter(r[idx] for r in allrows).most_common(12)]
    print('\nBy year'); [print(' ', k, n) for k, n in sorted(Counter(r[0] for r in allrows).items())] if y1 - y0 < 30 else None
    if len(allrows) <= 60:
        print('\nRecords:'); [print(' ', r[0], r[1], '|', r[2], '|', r[3][:90], '|', r[4], r[6]) for r in allrows]
