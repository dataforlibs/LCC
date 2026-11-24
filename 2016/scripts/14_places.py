#!/usr/bin/env python3
"""
Count records by place of publication and publication year.

Usage:  python3 14_places.py <parts_dir> <out_json> [n_workers]
Writes: <out_json> (e.g. places_numbers.json)

Place of publication is the MARC country code in 008/15-17 (for example "nyu" New York, "enk" England,
"xxk" United Kingdom, "onc" Ontario, "gw" Germany). Raw codes are written; they are grouped into
countries when the page is built, because US states, Canadian provinces, Australian states and the
four UK nations each have their own code.

Same rules as 01_extract_marc_2016.py: the record needs a valid LC class (first 050 $a, else 090 $a)
and pub_year = 008/07-10 in 1400..2020. Output: {"source": ..., "codes": {"nyu": {"1975": n}}}.
Records without a call number are skipped, so the totals match the catalog analysed in the paper.
"""
import gzip, re, sys, os, glob, json, importlib.util
from collections import Counter, defaultdict
from multiprocessing import Pool

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location('ex01', os.path.join(HERE, '01_extract_marc_2016.py'))
ex = importlib.util.module_from_spec(spec); spec.loader.exec_module(ex)
RT = ex.RT

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
                    if not cn or not f008 or len(f008) < 18 or not ex.valid_class(cn): continue
                    ym = re.match(rb'\d{4}', f008[7:11])
                    if not ym: continue
                    y = int(ym.group())
                    if not 1400 <= y <= 2020: continue
                    code = f008[15:18].decode('ascii', 'ignore').strip().lower()
                    if not code or code in ('|||', 'xx') or not code.isalpha(): code = 'unknown'
                    cnt[(code, y)] += 1
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
    json.dump({'source': 'LC MARC 2016, records with a call number and a publication year; code = 008/15-17',
               'codes': d}, open(out, 'w'))
    print('records:', sum(tot.values()), 'codes:', len(d))
