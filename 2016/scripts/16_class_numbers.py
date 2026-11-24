#!/usr/bin/env python3
"""
Count records by class number and publication year for the classes needed to add the grey countries of the
Europe map: PH (Finno-Ugrian literature: Finnish, Estonian, Hungarian), PA (Greek literature), DF (Greece) and DR (Balkans).

Usage:  python3 16_class_numbers.py <parts_dir> <out_json> [n_workers]
Writes: <out_json> (e.g. class_numbers.json): {"source": ..., "classes": {"PH:2001": {"1975": n}, ...}}
Keys are the class letters and the whole-number part of the class number ("PH:2001" covers PH2001 to PH2001.99).
The groups (which numbers are Finland, Estonia, Hungary, Greece, Serbia, Croatia ...) are assigned afterwards from
the Library of Congress classification outline, so no range is guessed here.
Same record rules as 13_world.py: first 050 $a else 090 $a, pub_year = 008/07-10 in 1400..2020.
"""
import gzip, re, sys, os, glob, json, importlib.util
from collections import Counter, defaultdict
from multiprocessing import Pool
HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location('ex01', os.path.join(HERE, '01_extract_marc_2016.py'))
ex = importlib.util.module_from_spec(spec); spec.loader.exec_module(ex)
RT = ex.RT
WANT = ('PH', 'PA', 'DF', 'DR')

def process(path):
    cnt = Counter(); buf = b''
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
                    if cls not in WANT: continue
                    ym = re.match(rb'\d{4}', (f008 or b'')[7:11])
                    if not ym: continue
                    y = int(ym.group())
                    if not 1400 <= y <= 2020: continue
                    m = re.match(r'\s*' + cls + r'\s*(\d+)', cn, re.I)
                    cnt[(cls + ':' + (m.group(1) if m else 'other'), y)] += 1
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
    json.dump({'source': 'LC MARC 2016, records with a call number and a publication year', 'classes': d}, open(out, 'w'))
    print('records:', sum(tot.values()), 'class numbers:', len(d))
