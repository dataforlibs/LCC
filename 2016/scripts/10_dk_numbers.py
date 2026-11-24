#!/usr/bin/env python3
"""
Count DK and PG records by class number and publication year, to compare Ukraine (DK508, PG3801-3987)
with the rest of the Slavic holdings.

Usage:  python3 10_dk_numbers.py <parts_dir> <out_json> [n_workers]
Writes: <out_json> (default name expected by slavic_collections.html: dk_numbers.json)

Same rules as 01_extract_marc_2016.py (first 050 $a else 090 $a, pub_year = 008/07-10 in 1400..2020).
Only records whose class is DK or PG are kept. Each record is counted under a named group: a country for DK
(Ukraine = DK508-508.95, Belarus = DK507, Kazakhstan = DK901-909.5, ...) and a language for PG
(Russian = PG2001-2826 + PG2900-3698, Ukrainian = PG3801-3987, ...). The ranges are in DK_GROUPS / PG_GROUPS below.
Output keys look like "DK:Ukraine", "PG:Polish"; anything outside a listed range is "DK:other" / "PG:other".
"""
import gzip, re, sys, os, glob, json, importlib.util
from collections import Counter, defaultdict
from multiprocessing import Pool

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location('ex01', os.path.join(HERE, '01_extract_marc_2016.py'))
ex = importlib.util.module_from_spec(spec); spec.loader.exec_module(ex)
RT = ex.RT

# Ranges from the LC classification outlines (DK, PG). Numbers are compared as floats, so
# DK509 (Southern Soviet Union) and DK509.1-509.95 (Moldova) can be told apart.
DK_GROUPS = [
    (1, 499.99, 'Russia / USSR general (DK1-499)'),
    (500, 502.99, 'Regional and Baltic general (DK500-502)'),
    (503, 503.99, 'Estonia'), (504, 504.99, 'Latvia'), (505, 505.99, 'Lithuania'),
    (507, 507.99, 'Belarus'), (508, 508.99, 'Ukraine'),
    (509, 509.0999, 'Southern Soviet Union (DK509)'), (509.1, 509.99, 'Moldova'),
    (510, 651.99, 'Russia (Federation) (DK510-651)'),
    (670, 679.99, 'Georgia'), (680, 689.99, 'Armenia'), (690, 699.99, 'Azerbaijan'),
    (751, 781.99, 'Siberia'), (845, 860.99, 'Soviet Central Asia (general)'),
    (901, 909.99, 'Kazakhstan'), (911, 919.99, 'Kyrgyzstan'), (921, 929.99, 'Tajikistan'),
    (931, 939.99, 'Turkmenistan'), (941, 949.99, 'Uzbekistan'),
    (4010, 4800.99, 'Poland (DK4010-4800)'),
]
PG_GROUPS = [
    (1, 799.99, 'Slavic general and Church Slavic (PG1-799)'),
    (801, 1146.99, 'Bulgarian'), (1151, 1199.99, 'Macedonian'), (1201, 1749.99, 'Serbo-Croatian'),
    (1801, 1962.99, 'Slovenian'),
    (2001, 2826.99, 'Russian'), (2830, 2847.99, 'Belarusian'), (2900, 3698.99, 'Russian'),
    (3801, 3987.99, 'Ukrainian'), (3990, 3990.99, 'Carpatho-Rusyn'),
    (4001, 5146.99, 'Czech'), (5201, 5546.99, 'Slovak'), (5631, 5689.99, 'Sorbian'),
    (6001, 7446.99, 'Polish'), (7900, 7925.99, 'Lechitic dialects'),
    (8501, 8772.99, 'Lithuanian'), (8801, 9146.99, 'Latvian'), (9501, 9665.99, 'Albanian'),
]

def key_for(cn, cls):
    m = re.match(r"\s*" + cls + r"\s*(\d+(?:\.\d+)?)", cn, re.I)
    if not m: return None
    n = float(m.group(1))
    for lo, hi, name in (DK_GROUPS if cls == 'DK' else PG_GROUPS):
        if lo <= n <= hi: return cls + ':' + name
    return cls + ':other'

def process(path):
    cnt = Counter(); buf = b''; seen = 0
    with gzip.open(path, 'rb') as f:
        while True:
            ch = f.read(1 << 24); buf += ch
            parts = buf.split(RT); buf = parts.pop()
            if not ch and len(buf) > 24: parts.append(buf); buf = b''
            for r in parts:
                if len(r) <= 24: continue
                try:
                    cn, f008 = ex.call_number(r)
                    cls = ex.valid_class(cn) if cn else None
                    if cls not in ('DK', 'PG'): continue
                    ym = re.match(rb'\d{4}', (f008 or b'')[7:11])
                    if not ym: continue
                    y = int(ym.group())
                    if not 1400 <= y <= 2020: continue
                    k = key_for(cn, cls)
                    if k: cnt[(k, y)] += 1
                except Exception: pass
            if not ch: break
    return os.path.basename(path), cnt

if __name__ == '__main__':
    parts_dir, out = sys.argv[1], sys.argv[2]; nw = int(sys.argv[3]) if len(sys.argv) > 3 else 2
    files = sorted(glob.glob(os.path.join(parts_dir, '*.gz')))
    tot = Counter()
    with Pool(nw) as pool:
        for name, c in pool.imap_unordered(process, files):
            tot.update(c); print(name, sum(c.values()), flush=True)
    d = defaultdict(dict)
    for (k, y), n in tot.items(): d[k][str(y)] = n
    json.dump({'source': 'LC MARC 2016, DK records with a publication year', 'classes': d}, open(out, 'w'))
    print('DK+PG records:', sum(tot.values()), 'class numbers:', len(d))
